#!/bin/bash
# Full-screen web panel: Xorg + Firefox, run as user kiosk on tty1.
# Each start uses one setting from a list and moves on when a try dies within 30 s:
#   1. Xorg's own choice of graphics chip, browser drawing in software (GPU drawing gave a white page)
#   (no second variant)
#   3+. one chip at a time (connected screen first), no acceleration at all
# Everything is logged to the stick's NEURONCFG drive (kiosk-log.txt), readable on Windows/Mac.
F=/tmp/kiosk-fails; n=$(cat $F 2>/dev/null || echo 0)
LOG=/cfg/kiosk-log.txt; [ -w /cfg ] || LOG=/tmp/kiosk-log.txt
[ "$n" = 0 ] && : > "$LOG"
exec >>"$LOG" 2>&1

tries=("auto soft")
for c in /sys/class/drm/card[0-9]; do grep -qx connected $c-*/status 2>/dev/null && tries+=("${c##*/} soft"); done
for c in /sys/class/drm/card[0-9]; do grep -qx connected $c-*/status 2>/dev/null || tries+=("${c##*/} soft"); done
t=${tries[$n]:-${tries[-1]}}; card=${t% *}; mode=${t#* }
echo "=== $(date) try $((n+1))/${#tries[@]}: chip=$card drawing=$mode"
for c in /sys/class/drm/card[0-9]; do echo "  ${c##*/}: vendor $(cat $c/device/vendor 2>/dev/null) driver $(basename "$(readlink $c/device/driver)") boot_vga=$(cat $c/device/boot_vga 2>/dev/null) screens: $(cat $c-*/status 2>/dev/null | tr '\n' ' ')"; done

CFG=""; [ "$card" != auto ] && CFG="-config kiosk-$card.conf"
t0=$(date +%s)
xinit /opt/neuron/kiosk-x.sh "$mode" -- /usr/lib/xorg/Xorg :0 vt1 -keeptty -nolisten tcp -logfile /tmp/Xorg.0.log $CFG
rc=$?
echo "=== exited rc=$rc after $(( $(date +%s) - t0 )) s"; grep -E "\(EE\)|\(WW\) .*(fail|not)" /tmp/Xorg.0.log | head -15
[ $(( $(date +%s) - t0 )) -lt 30 ] && echo $((n + 1)) > $F
exit $rc
