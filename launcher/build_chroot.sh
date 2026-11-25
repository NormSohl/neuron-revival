#!/bin/bash
# Build the chroot from the partition images made by tools/build_disk.py (p1.img = root, p5.img = /var).
#   sudo ./build_chroot.sh WORKDIR CHROOT
set -euo pipefail
W=$1; R=$2; mkdir -p "$R/home" "$R/proc" "$R/tmp" "$R/var/tmp" "$R/mnt/.init.d"
for d in bin lib usr etc sbin dev; do debugfs -R "rdump /$d $R" "$W/p1.img" >/dev/null 2>&1; done
debugfs -R "rdump /home/neuron $R/home" "$W/p5.img" >/dev/null 2>&1
echo "chroot ready in $R"
