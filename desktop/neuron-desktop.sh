#!/bin/bash
# Start the Neuron on this desktop: panel relay (as you, from the repo, so edits are live), the original
# engine (root, safe mode, via neuron-engine), and the panel page full screen in Firefox.
# Closing the panel window (Alt+F4) stops everything.   neuron-desktop.sh [stop | headless]
# headless: no Firefox page; runs until the relay stops (used by the neuron-headless user service, which
# sets REAL_PANEL=/dev/ttyUSB0). The dashboard is at http://<hostname>.local:8080/ and the panel page at :8080/panel.
REPO=$(dirname "$(dirname "$(realpath "$0")")"); RUN=/run/user/$(id -u)/neuron
NR=$HOME/neuron-run; LOG=$NR/neuron.log; mkdir -p "$RUN"
stop(){ sudo -n /usr/local/sbin/neuron-engine stop
  [ -f "$RUN/relay.pid" ] && kill "$(cat "$RUN/relay.pid")" 2>/dev/null; rm -f "$RUN/relay.pid"; }
svc(){ [ -z "${INVOCATION_ID:-}" ] && systemctl --user is-active -q neuron-headless; }  # service runs it, we don't
[ "${1:-}" = stop ] && { if svc; then systemctl --user stop neuron-headless; else stop; fi; exit 0; }
if svc; then   # dock icon while the headless service runs: only show the panel, leave the service running
  mkdir -p "$NR/firefox-panel"; exec firefox --new-instance --profile "$NR/firefox-panel" --kiosk http://127.0.0.1:8080/panel
fi
old_relays(){ # our relay.py processes still holding the panel port (e.g. pid file lost)
  for p in $(ss -ltnpH 'sport = :8080' | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u); do
    tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -q "python3 $REPO/stick/relay.py" && echo $p; done; }
if ! { [ -f "$RUN/relay.pid" ] && kill -0 "$(cat "$RUN/relay.pid")" 2>/dev/null; }; then
  for p in $(old_relays); do echo "stopping leftover relay $p" >> "$LOG"; kill $p; done
  for i in $(seq 1 20); do [ -z "$(old_relays)" ] && break; sleep 0.25; done
  rm -f "$RUN/vpanel.pty"; echo "=== $(date) start" >> "$LOG"
  NEURON_RUN=$RUN NEURON_GLOBALS=$NR/data/neuron/NeuronDB/neuron.globals \
    setsid python3 "$REPO/stick/relay.py" >> "$LOG" 2>&1 & echo $! > "$RUN/relay.pid"
  for i in $(seq 1 40); do [ -s "$RUN/vpanel.pty" ] && break; sleep 0.25; done
fi
{ [ -s "$RUN/vpanel.pty" ] && kill -0 "$(cat "$RUN/relay.pid" 2>/dev/null)" 2>/dev/null; } || { echo "Panel relay did not start (see $LOG)" >&2; notify-send "Neuron" "Panel relay did not start (see $LOG)" 2>/dev/null; exit 1; }
sudo -n /usr/local/sbin/neuron-engine start "$(cat "$RUN/vpanel.pty")" >> "$LOG" 2>&1 \
  || { echo "Engine did not start (see $LOG)" >&2; notify-send "Neuron" "Engine did not start (see $LOG)" 2>/dev/null; stop; exit 1; }
if [ "${1:-}" = headless ]; then
  trap 'stop; exit 0' TERM INT
  while kill -0 "$(cat "$RUN/relay.pid" 2>/dev/null)" 2>/dev/null; do sleep 5 & wait $!; done
  stop; exit 1
fi
mkdir -p "$NR/firefox-panel"
firefox --new-instance --profile "$NR/firefox-panel" --kiosk http://127.0.0.1:8080/panel >/dev/null 2>&1
stop
