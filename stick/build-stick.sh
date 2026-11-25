#!/bin/bash
# Build the Neuron USB stick image: an Ubuntu 24.04 LTS live system that boots straight into the
# original Neuron software, with the full-screen panel, the panel bridge and the text-panel fallback.
# Run as root on Ubuntu 24.04 x86-64:
#   sudo stick/build-stick.sh WORK DISK_DIR
# DISK_DIR holds p1.img (root) and p5.img (/var) made by tools/build_disk.py from the OS 1.5 image.
# Optional: ENGINE_V64=/path/to/neuron_v64 adds the 64-voice engine.
# Output: WORK/neuron-stick.img (and .img.xz). Write it to a USB stick of 8 GB or more.
# The image contains Hartmann's software: for your own instrument only, never publish it.
set -euo pipefail
W=$(realpath -m "$1"); IMG=$(realpath "$2"); HERE=$(dirname "$(realpath "$0")"); REPO=$(dirname "$HERE")
L=$REPO/launcher; SH=$REPO/shim; O=rootfs/opt/neuron
[ -f "$IMG/p1.img" ] && [ -f "$IMG/p5.img" ] || { echo "no p1.img/p5.img in $IMG (run tools/build_disk.py first)"; exit 1; }
mkdir -p "$W"; cd "$W"; rm -rf rootfs nchroot iso data shimbuild

apt-get install -y -qq mmdebstrap squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools dosfstools \
  e2fsprogs ubuntu-keyring gcc-multilib curl >/dev/null

# Ubuntu ships Firefox and Chromium only as snaps, which a live stick can't run, so Firefox comes from
# Mozilla's own APT repository. The pin makes it win over Ubuntu's snap-installer package of the same name.
mkdir -p keys; curl -fsSL https://packages.mozilla.org/apt/repo-signing-key.gpg -o keys/mozilla.asc
U=http://archive.ubuntu.com/ubuntu
mmdebstrap --mode=root --variant=minbase \
  --keyring=/usr/share/keyrings/ubuntu-archive-keyring.gpg --keyring="$W/keys/mozilla.asc" \
  --setup-hook='mkdir -p "$1/etc/apt/preferences.d"; printf "Package: *\nPin: origin packages.mozilla.org\nPin-Priority: 1000\n" > "$1/etc/apt/preferences.d/mozilla"' \
  --include=linux-image-generic,live-boot,systemd-sysv,udev,kmod,dbus,libpam-systemd,util-linux,e2fsprogs,usbutils,procps,iproute2,less,nano \
  --include=alsa-utils,python3,python3-aiohttp \
  --include=xserver-xorg-core,xserver-xorg-input-libinput,xinit,x11-xserver-utils,fonts-dejavu-core,ca-certificates,firefox \
  noble rootfs \
  "deb $U noble main universe" "deb $U noble-updates main universe" "deb http://security.ubuntu.com/ubuntu noble-security main universe" \
  "deb https://packages.mozilla.org/apt mozilla main"

# The Neuron's own environment (2002 system + NeuronDB), and our stand-in libraries built against it
bash "$L/build_chroot.sh" "$IMG" nchroot
[ -n "${ENGINE_V64:-}" ] && cp "$ENGINE_V64" nchroot/home/neuron/bin/neuron_v64
mkdir -p shimbuild; cp "$SH"/*.c "$SH"/build.sh shimbuild/; sh shimbuild/build.sh "$W/nchroot"
mkdir -p data/neuron; mv nchroot/home/neuron/* data/neuron/; cp "$HERE/neuron.conf" data/

# /opt/neuron: environment, launcher, shims, panel bridge, web pages, kiosk and start scripts
mkdir -p $O/launcher $O/shim rootfs/data rootfs/cfg
cp -a nchroot $O/chroot
install -m755 "$L/run_neuron.sh" $O/launcher/
cp shimbuild/libasound_live32.so shimbuild/libnort.so shimbuild/libnolock.so "$SH/meminfo24" $O/shim/
cp -r "$HERE/relay.py" "$HERE/web" "$HERE/keyboard-panel.py" $O/
install -m755 "$HERE/neuron-start.sh" "$HERE/kiosk.sh" "$HERE/kiosk-x.sh" $O/
cp "$HERE"/neuron.service "$HERE"/neuron-relay.service "$HERE"/neuron-kiosk.service "$HERE"/neuron-keyboard-panel.service \
   rootfs/etc/systemd/system/
echo 'LABEL=NEURONDATA /data ext4 defaults,nofail,x-systemd.device-timeout=20 0 2' > rootfs/etc/fstab
echo neuron > rootfs/etc/hostname
# kiosk user for the full-screen panel; its systemd unit opens a login session through PAM service "cage"
printf '@include common-account\n@include common-session\n' > rootfs/etc/pam.d/cage
chroot rootfs sh -c 'useradd -m -G video,render,input,tty,audio kiosk; echo root:neuron | chpasswd; systemctl enable neuron.service'

# Live image: kernel + initrd + squashfs, boot menu, then the two extra partitions
mkdir -p iso/live iso/boot/grub
cp rootfs/boot/vmlinuz-* iso/live/vmlinuz; cp rootfs/boot/initrd.img-* iso/live/initrd.img; cp "$HERE/grub.cfg" iso/boot/grub/
mksquashfs rootfs iso/live/filesystem.squashfs -comp xz -e boot -noappend -no-progress
mkfs.ext4 -q -L NEURONDATA -d data data.ext4 3800M                       # sounds, setups, models (survive reboots)
rm -f cfg.vfat; mkfs.vfat -n NEURONCFG -C cfg.vfat 16384 >/dev/null       # settings, editable on Windows/Mac
mcopy -i cfg.vfat "$HERE/neuron.conf" ::/neuron.conf
grub-mkrescue -o neuron-stick.img iso -- -append_partition 3 0x83 data.ext4 -append_partition 4 0x0c cfg.vfat
xz -T0 -6 -kf neuron-stick.img
echo "built $W/neuron-stick.img"
