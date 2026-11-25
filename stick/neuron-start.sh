#!/bin/bash
# Start the Neuron: data partition, settings, panel port, audio device, then the original engine.
set -u
log(){ echo "[neuron] $*" | tee /dev/console; }
mountpoint -q /data || mount LABEL=NEURONDATA /data || { log "NEURONDATA partition not found"; exit 1; }
mkdir -p /cfg; mountpoint -q /cfg || mount -o umask=000 LABEL=NEURONCFG /cfg 2>/dev/null
CONF=/cfg/neuron.conf; [ -f "$CONF" ] || CONF=/data/neuron.conf
PANEL_DEV=auto; ALSA_DEV=auto; ENGINE=neuron; DEDICATED=1
[ -f "$CONF" ] && . <(tr -d '\r' < "$CONF")
[ -f /cfg/neuron-local.sh ] && . <(tr -d '\r' < /cfg/neuron-local.sh)   # optional local additions or small updates
for a in $(cat /proc/cmdline); do case $a in neuron.panel=*) PANEL_DEV=${a#*=};; neuron.audio=*) ALSA_DEV=${a#*=};; neuron.engine=*) ENGINE=${a#*=};; esac; done
C=/opt/neuron/chroot
mountpoint -q $C/home/neuron || mount --bind /data/neuron $C/home/neuron
# Panel: the engine always talks to the panel relay; the relay passes everything on to the real
# panel (if one is connected), the web panel and the text panel.
REAL=""
if [ "$PANEL_DEV" = auto ]; then
  for i in $(seq 1 10); do REAL=$(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null | head -1); [ -n "$REAL" ] && break
    [ $i = 1 ] && log "looking for a USB-serial adapter (panel)..."; sleep 1; done
  [ -z "$REAL" ] && log "no USB-serial adapter: on-screen panel only"
elif [ "$PANEL_DEV" != virtual ]; then REAL=$PANEL_DEV; fi
mkdir -p /run/neuron; echo "REAL_PANEL=$REAL" > /run/neuron/relay.env; rm -f /run/neuron/vpanel.pty
systemctl restart neuron-relay.service
for i in $(seq 1 40); do [ -s /run/neuron/vpanel.pty ] && break; sleep 0.5; done
PANEL_DEV=$(cat /run/neuron/vpanel.pty 2>/dev/null) || { log "panel relay did not start"; exit 1; }
# Screen: full-screen web panel (KIOSK=1), else the text keyboard panel
if [ "${KIOSK:-1}" = 1 ] && [ ! -e /run/neuron/kiosk-gave-up ]; then
  for c in /sys/class/drm/card[0-9]; do k=${c##*/}
    printf 'Section "Device"\n  Identifier "k"\n  Driver "modesetting"\n  Option "kmsdev" "/dev/dri/%s"\n  Option "AccelMethod" "none"\nEndSection\n' $k > /etc/X11/kiosk-$k.conf
  done
  systemctl start neuron-kiosk.service
  # watchdog: if the web panel keeps failing (no usable graphics), fall back to the text panel
  ( for i in $(seq 1 36); do sleep 10
      n=$(systemctl show -p NRestarts --value neuron-kiosk.service)
      if [ "${n:-0}" -ge 10 ]; then touch /run/neuron/kiosk-gave-up; systemctl stop neuron-kiosk.service
        systemctl start neuron-keyboard-panel.service; log "web panel could not start: using the text panel"; break; fi
    done ) &
else systemctl start neuron-keyboard-panel.service; fi
if [ "$ALSA_DEV" = auto ]; then
  for i in $(seq 1 10); do ls /proc/asound/card*/id >/dev/null 2>&1 && break; sleep 1; done
  CARD=""; for d in /proc/asound/card[0-9]*; do [ -e "$d/usbid" ] && { CARD=$(cat $d/id); break; }; done
  [ -z "$CARD" ] && CARD=$(cat /proc/asound/card0/id 2>/dev/null)
  ALSA_DEV="plughw:CARD=${CARD:-0},DEV=0"
fi
# Sound: raise every mixer on every card (Linux starts them low or muted)
for c in /proc/asound/card[0-9]*; do n=${c##*card}
  for ctl in Master PCM Speaker Headphone Front 'Line Out' Digital; do amixer -q -c "$n" sset "$ctl" 100% unmute 2>/dev/null; done
done
log "panel ${REAL:-on-screen only} (relay $PANEL_DEV), web panel on screen$(IP=$(hostname -I 2>/dev/null | cut -d" " -f1); [ -n "$IP" ] && echo " and at http://$IP:8080"), audio $ALSA_DEV, engine $ENGINE, dedicated $DEDICATED"
export ALSA_DEV ENGINE DEDICATED
exec /opt/neuron/launcher/run_neuron.sh $C "$PANEL_DEV"
