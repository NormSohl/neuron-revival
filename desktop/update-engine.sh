#!/bin/bash
# Install engine-side changes from this repo onto the ThinkPad (run as root, e.g. sudo bash update-engine.sh).
# Builds the 32-bit shims against the Neuron's own glibc, then copies the launcher, shims and root helper
# into /opt/neuron. Leaves the Neuron program and NeuronDB untouched. Needs gcc-multilib.
set -euo pipefail
HERE=$(dirname "$(realpath "$0")"); REPO=$(dirname "$HERE"); O=/opt/neuron
dpkg -s gcc-multilib >/dev/null 2>&1 || apt-get install -y -qq gcc-multilib
B=$(mktemp -d); cp "$REPO"/shim/*.c "$REPO"/shim/build.sh "$B"/; sh "$B/build.sh" $O/chroot
install -d $O/shim $O/launcher
install -o root -g root -m 644 "$B"/libasound_live32.so "$B"/libnort.so "$B"/libnolock.so "$REPO"/shim/meminfo24 $O/shim/
install -o root -g root -m 755 "$REPO/launcher/run_neuron.sh" $O/launcher/run_neuron.sh
install -o root -g root -m 755 "$HERE/neuron-engine" /usr/local/sbin/neuron-engine
rm -rf "$B"; echo "UPDATE_OK: restart with: systemctl --user restart neuron-headless"
