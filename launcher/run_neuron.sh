#!/bin/bash
# Run the original Hartmann Neuron software on a modern x86 Linux PC.
#   sudo ./run_neuron.sh CHROOT PANEL_DEV [AUDIO_PLAYER...]
# CHROOT     directory built by build_chroot.sh (root fs + /home/neuron from the disk image)
# PANEL_DEV  serial device wired to the Neuron front panel (e.g. /dev/ttyUSB0), or a pty from the virtual panel
# AUDIO_PLAYER command that plays raw S32_LE stereo 44.1 kHz (24 significant bits) from stdin; default:
#            aplay -q -t raw -f S32_LE -c 2 -r 44100 --buffer-time=20000
# Environment options (used only when no AUDIO_PLAYER is given):
#   ALSA_DEV=hw:1,0   output device (default: default)
#   OUT_RATE=96000    resample the engine's 44.1 kHz output to this rate with SoX (very high quality,
#                     about 1% CPU); use this for 48k/96k interfaces. The engine itself stays at 44.1k,
#                     where its pitch, model timing and delay lengths are exactly as designed.
#   ENGINE=neuron_v64 engine binary in /home/neuron/bin (default: neuron). neuron_v64 = a 64-voice build of
#                     the engine, if you have one (not part of this repository); needs a fast CPU core.
#   DEDICATED=1       this PC is a dedicated Neuron: let the engine really use real-time priority and memory
#                     locking (as the original did), on two CPU cores (audio thread + panel/UI thread),
#                     and use a smaller output buffer. Do NOT use on a shared/cloud machine.
#   PERF=1            a shared machine you still want to play (e.g. a laptop that also runs other tools):
#                     real real-time priority (capped by ulimit -r 95, so the kernel's real-time brake still
#                     applies), two CPU cores, the small output buffer, and the CPU in performance mode while
#                     it runs. Memory locking stays faked (libnolock) and the memory cap stays on.
# Safe mode: runs as an unprivileged user on one core; real-time and memory locking are faked (libnort).
set -euo pipefail
R=$(realpath "$1"); PANEL=$2; shift 2
PLAYER=("$@")
if [ ${#PLAYER[@]} -eq 0 ]; then
  if [ -n "${OUT_RATE:-}" ] && [ "$OUT_RATE" != 44100 ]; then
    PLAYER=(sox -q --buffer 1024 -t raw -r 44100 -e signed-integer -b 32 -c 2 - -t alsa "${ALSA_DEV:-default}" rate -h -I "$OUT_RATE")
  else
    BT=20000; RT=(); if [ "${DEDICATED:-0}" = 1 ] || [ "${PERF:-0}" = 1 ]; then BT=6000; RT=(chrt -f 10); fi
    PLAYER=("${RT[@]}" aplay -q -D "${ALSA_DEV:-default}" -t raw -f S32_LE -c 2 -r 44100 --buffer-time=$BT)
  fi
fi
HERE=$(dirname "$(realpath "$0")")
mkdir -p "$R/opt/shim" "$R/var/tmp" "$R/proc/sys/kernel" "$R/proc/acpi" "$R/dev"
# The sound shim rewrites neuron_levels 50 times a second from the audio thread. On disk, that write waits
# for the ext4 journal commit every 5 s, and on a slow SSD the wait made the Twist drop out (2026-11-24).
# In RAM it never waits.
mountpoint -q "$R/var/tmp" || mount -t tmpfs -o size=16m,mode=1777 neuron-tmp "$R/var/tmp"
cp "$HERE/../shim/libasound_live32.so" "$R/opt/shim/libasound.so.2"; cp "$HERE/../shim/libnort.so" "$R/opt/shim/"
[ "${PERF:-0}" = 1 ] && cp "$HERE/../shim/libnolock.so" "$R/opt/shim/"
cp "$HERE/../shim/meminfo24" "$R/proc/meminfo"; echo 0 > "$R/proc/sys/kernel/lowlatency"
[ -p "$R/proc/acpi/event" ] || mkfifo "$R/proc/acpi/event"
chmod 666 "$R/proc/sys/kernel/lowlatency" "$R/proc/acpi/event"; chmod 1777 "$R/var/tmp" "$R/tmp"
find "$R/home/neuron/NeuronDB" -type d -exec chmod 755 {} +; chown -R 1000:1000 "$R/home/neuron" 2>/dev/null || true
for d in null zero; do touch "$R/dev/$d"; mountpoint -q "$R/dev/$d" || mount --bind "/dev/$d" "$R/dev/$d"; done
# USB-serial adapters (FTDI): cut the default 16 ms receive delay to 1 ms so knobs stay responsive
LT=/sys/bus/usb-serial/devices/$(basename "$(realpath "$PANEL")")/latency_timer; [ -w "$LT" ] && echo 1 > "$LT"
touch "$R/dev/ttyS0"; mountpoint -q "$R/dev/ttyS0" && umount "$R/dev/ttyS0"; mount --bind "$PANEL" "$R/dev/ttyS0"; chmod 666 "$PANEL"
FIFO="$R/var/tmp/neuron_audio.fifo"; rm -f "$FIFO"; mkfifo -m 666 "$FIFO"
exec 3<>"$R/proc/acpi/event"                      # keep a writer open so the power-button reader just waits
"${PLAYER[@]}" < "$FIFO" & PLAYER_PID=$!
GOV=()                                            # PERF: CPU in performance mode while the engine runs
if [ "${PERF:-0}" = 1 ]; then for g in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
  [ -w "$g" ] && GOV+=("$g=$(cat "$g")") && echo performance > "$g" 2>/dev/null || true; done; fi
restore_gov(){ local e; for e in "${GOV[@]}"; do echo "${e#*=}" > "${e%%=*}" 2>/dev/null || true; done; }
trap 'kill $PLAYER_PID 2>/dev/null; umount "$R/dev/ttyS0" 2>/dev/null; restore_gov' EXIT
ENGINE=${ENGINE:-neuron}
if [ "${DEDICATED:-0}" = 1 ]; then
  ulimit -r 95; ulimit -l unlimited               # raised as root, inherited by the unprivileged engine
  taskset -c 0,1 chroot --userspec=1000:1000 "$R" /bin/sh -c \
    "cd /home/neuron && LD_LIBRARY_PATH=/opt/shim exec ./$( [ "$ENGINE" = neuron ] && echo neuron || echo bin/$ENGINE ) log"
elif [ "${PERF:-0}" = 1 ]; then
  ulimit -r 95                                     # real-time allowed, still under the kernel's RT brake
  taskset -c 0,1 chroot --userspec=1000:1000 "$R" /bin/sh -c \
    "ulimit -v 1500000; cd /home/neuron && LD_LIBRARY_PATH=/opt/shim LD_PRELOAD=/opt/shim/libnolock.so exec ./$( [ "$ENGINE" = neuron ] && echo neuron || echo bin/$ENGINE ) log"
else
  taskset -c 0 chroot --userspec=1000:1000 "$R" /bin/sh -c \
    "ulimit -v 1500000; cd /home/neuron && LD_LIBRARY_PATH=/opt/shim LD_PRELOAD=/opt/shim/libnort.so exec ./$( [ "$ENGINE" = neuron ] && echo neuron || echo bin/$ENGINE ) log"
fi
