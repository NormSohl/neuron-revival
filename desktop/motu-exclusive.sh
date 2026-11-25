#!/bin/bash
# Keep PipeWire off the MOTU M4 so only the Neuron engine (direct ALSA) ever plays through it.
# Run as the desktop user (not root). Desktop sounds then use the laptop's own output.
# Check the MOTU's PipeWire device name first: wpctl status / pw-cli ls Device (device.name).
set -euo pipefail
PAT=${1:-alsa_card.usb-MOTU_M4*}
V=$(wireplumber --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)
if [ "${V%%.*}" = 0 ] && [ "${V#*.}" -lt 5 ] 2>/dev/null; then          # WirePlumber 0.4 (Lua)
  D=~/.config/wireplumber/main.lua.d; mkdir -p "$D"
  printf 'table.insert(alsa_monitor.rules, {\n  matches = {{{ "device.name", "matches", "%s" }}},\n  apply_properties = { ["device.disabled"] = true },\n})\n' "$PAT" > "$D/51-neuron-motu-off.lua"
else                                                                     # WirePlumber 0.5+
  D=~/.config/wireplumber/wireplumber.conf.d; mkdir -p "$D"
  printf 'monitor.alsa.rules = [\n  { matches = [ { device.name = "~%s" } ]\n    actions = { update-props = { device.disabled = true } } }\n]\n' "$PAT" > "$D/51-neuron-motu-off.conf"
fi
systemctl --user restart wireplumber; echo "MOTU disabled in PipeWire (WirePlumber $V). Check: wpctl status"
