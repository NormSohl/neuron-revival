#!/bin/bash
# Install the Neuron on an Ubuntu 26.04 LTS computer (tested from scratch on 26.04.1; 24.04 only in a container),
# for the user who runs it with sudo.
#   sudo bash ~/neuron/desktop/install.sh IMAGE [AUDIO_DEV]
# IMAGE      the Neuron disk image: Neuron80GB-OS15.rar, the .tib inside it, or a folder holding
#            p1.img and p5.img from tools/build_disk.py; or  keep  to reuse an existing /opt/neuron/chroot
#            (for an update, or a small disk: unpacking the image needs about 10 GB free)
# AUDIO_DEV  ALSA device for the Neuron's sound, e.g. plughw:M4 (default auto = the first USB audio
#            interface that can play). USB audio becomes the Neuron's alone: PipeWire is kept off all USB
#            audio devices, so desktop sounds use the computer's built-in speakers and headphone jack.
#
# Result: the Neuron's 2002 environment in /opt/neuron, its library (NeuronDB) in ~/neuron-run/data,
# the engine starting at boot with the real panel on a USB-serial adapter, the dashboard at
# http://<this computer>.local:8080/ and the on-screen panel at :8080/panel, plus a "Neuron" app icon.
# Safe to run again: an existing NeuronDB (your saved sounds) is never overwritten, and the audio output and
# buffer chosen earlier (dashboard, set-audio, set-buffer) are kept unless AUDIO_DEV is given.
# The Neuron's software belongs to its makers: keep what this builds for your own instrument.
set -euo pipefail
[ "$(id -u)" = 0 ] && [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != root ] || { echo "run as: sudo bash $0 IMAGE"; exit 1; }
SRC=${1:?usage: sudo bash install.sh IMAGE|keep [AUDIO_DEV]}; AUDIO=${2:-}
if [ "$SRC" = keep ]; then KEEP=1; else KEEP=; SRC=$(realpath -e "$SRC"); fi
USR=$SUDO_USER; UH=$(getent passwd "$USR" | cut -d: -f6); UID_=$(id -u "$USR")
HERE=$(dirname "$(realpath "$0")"); REPO=$(dirname "$HERE"); O=/opt/neuron
NR=$UH/neuron-run; DATA=$NR/data/neuron; W=${NEURON_WORK:-$NR/work}   # NEURON_WORK: unpack elsewhere (needs ~10 GB)
say(){ printf '\n== %s\n' "$*"; }
# The engine binds the NeuronDB, /dev/null, /dev/zero and the panel port into the chroot. None may stay
# bound while the chroot is deleted, chowned or chmodded (that would reach the host's /dev/null or the NeuronDB).
chroot_mounts(){ findmnt -rn -o TARGET | grep -E "^$O/chroot(/|$)" || true; }
unmount_chroot(){ chroot_mounts | sort -r | while read -r m; do umount "$m" || umount -l "$m"; done
  [ -z "$(chroot_mounts)" ] || { echo "still mounted in $O/chroot:"; chroot_mounts; exit 1; }; }
as_user(){ runuser -u "$USR" -- env XDG_RUNTIME_DIR=/run/user/$UID_ DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$UID_/bus "$@"; }

# The user services and app icon run the repo from ~/neuron
if [ "$REPO" != "$UH/neuron" ]; then
  [ -e "$UH/neuron" ] && { echo "~/neuron exists and is not this repo ($REPO); move one of them"; exit 1; }
  ln -s "$REPO" "$UH/neuron"; chown -h "$USR:" "$UH/neuron"
fi

say "Packages"
UNAR=unar; [ -n "$KEEP" ] && UNAR=
apt-get install -y -qq $UNAR python3 python3-aiohttp e2fsprogs gcc-multilib alsa-utils >/dev/null
apt-get clean

say "Stopping the Neuron"
[ -S /run/user/$UID_/bus ] && as_user systemctl --user stop neuron-headless.service 2>/dev/null || true
[ -x /usr/local/sbin/neuron-engine ] && /usr/local/sbin/neuron-engine stop || true
unmount_chroot

if [ -n "$KEEP" ]; then
  say "Keeping the Neuron's environment in $O/chroot"
  [ -d $O/chroot/lib ] || { echo "no existing $O/chroot to keep"; exit 1; }
  [ -d "$DATA/NeuronDB" ] || { echo "no NeuronDB in $DATA; install from the disk image instead"; exit 1; }
  chown -R "$USR:" "$NR"
else
say "Unpack the disk image"
if [ -d "$SRC" ]; then P=$SRC
else
  rm -rf "$W"; mkdir -p "$W"; T=$SRC
  case "$SRC" in *.rar) unar -q -o "$W" "$SRC"; T=$(ls "$W"/*.tib | head -1);; esac
  python3 -I "$REPO/tools/build_disk.py" "$T" "$W"; P=$W
fi
[ -f "$P/p1.img" ] && [ -f "$P/p5.img" ] || { echo "no p1.img/p5.img in $P"; exit 1; }

say "The Neuron's environment in $O/chroot"
rm -rf $O/chroot.new; bash "$REPO/launcher/build_chroot.sh" "$P" $O/chroot.new
if [ -d "$DATA/NeuronDB" ]; then echo "keeping your existing NeuronDB in $DATA"
else mkdir -p "$DATA"; cp -a $O/chroot.new/home/neuron/. "$DATA/"; fi
unmount_chroot
rm -rf $O/chroot.new/home/neuron/*; rm -rf $O/chroot; mv $O/chroot.new $O/chroot
chown -R "$USR:" "$NR"
fi

say "Settings, engine helper, shims and launcher"
mkdir -p /etc/neuron
# Keep an earlier install's choices (set-audio / set-buffer, or the dashboard) unless AUDIO_DEV was given now.
CF=/etc/neuron/neuron.conf; old(){ [ -f $CF ] || return 0; sed -n "s/^$1=\\([A-Za-z0-9:=,_-]*\\)$/\\1/p" $CF | tail -1; }
[ -n "$AUDIO" ] || AUDIO=$(old AUDIO_DEV); [ -n "$AUDIO" ] || AUDIO=auto
BUF=$(old AUDIO_BUFFER_MS); [[ $BUF =~ ^[0-9]{1,2}$ ]] && [ "$BUF" -ge 2 ] && [ "$BUF" -le 40 ] || BUF=5
T=$(mktemp /etc/neuron/.conf.XXXXXX)
printf 'NEURON_USER=%s\nAUDIO_DEV=%s\nAUDIO_BUFFER_MS=%s\n' "$USR" "$AUDIO" "$BUF" > "$T"; chmod 644 "$T"; mv "$T" $CF
bash "$HERE/update-engine.sh"
unmount_chroot
chown -R root:root $O; chmod -R go-w $O
echo "$USR ALL=(root) NOPASSWD: /usr/local/sbin/neuron-engine" > /tmp/neuron.sudoers
visudo -cqf /tmp/neuron.sudoers && install -o root -g root -m 440 /tmp/neuron.sudoers /etc/sudoers.d/neuron
rm -f /tmp/neuron.sudoers

say "Panel adapter, sound access, start at boot"
mkdir -p /etc/udev/rules.d
echo 'ACTION=="add", SUBSYSTEM=="usb-serial", DRIVER=="ftdi_sio", ATTR{latency_timer}="1"' > /etc/udev/rules.d/99-neuron-ftdi.rules
udevadm control --reload 2>/dev/null || true
usermod -aG audio,dialout "$USR"
loginctl enable-linger "$USR" 2>/dev/null || true
U=$UH/.config/systemd/user; mkdir -p "$U"; ln -sf "$UH/neuron/desktop/systemd/neuron-headless.service" "$U/"
A=$UH/.local/share/applications; mkdir -p "$A"; sed "s|@HOME@/|$UH/|g" "$HERE/neuron.desktop" > "$A/neuron.desktop"
chown -R "$USR:" "$UH/.config/systemd" "$UH/.local/share/applications"
if [ -S /run/user/$UID_/bus ]; then
  as_user systemctl --user daemon-reload; as_user systemctl --user enable neuron-headless.service
  as_user bash "$HERE/motu-exclusive.sh" 'alsa_card.usb-*' || echo "could not set the PipeWire rule; run desktop/motu-exclusive.sh 'alsa_card.usb-*' after logging in"
else echo "no user session running: after logging in, run  systemctl --user enable --now neuron-headless"; fi

rm -rf "$W"
say "Done"
echo "Reboot, or start it now with:  systemctl --user start neuron-headless"
echo "Dashboard: http://$(hostname).local:8080/   On-screen panel: http://$(hostname).local:8080/panel"
echo "First start: the Neuron asks for its serial number (on the bottom of the case) on the panel's keypad."
