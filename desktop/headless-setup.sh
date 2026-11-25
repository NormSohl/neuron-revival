#!/bin/bash
# One-time root setup to run a laptop as a headless Neuron, lid closed: SSH server, lid switch ignored, sleep masked.
#   sudo bash ~/neuron/desktop/headless-setup.sh
# Safe to run twice. Does NOT restart logind (that can end the desktop session): the lid setting takes
# effect at the next reboot; masking sleep makes closing the lid harmless right away.
# Does NOT turn off SSH password logins: do that yourself once your own SSH key works.
set -uo pipefail
USR=${SUDO_USER:?run with sudo}
say(){ printf '\n== %s\n' "$*"; }

say "Free disk space before"; df -h / | tail -1
apt-get clean
snap list --all 2>/dev/null | awk '/disabled/{print $1, $3}' | while read -r n r; do snap remove "$n" --revision="$r"; done

say "Install SSH server, tmux (avahi already present)"
apt-get install -y -qq openssh-server avahi-daemon tmux && apt-get clean
systemctl enable --now ssh avahi-daemon

say "Lid: ignore (from next reboot)"
mkdir -p /etc/systemd/logind.conf.d
printf '[Login]\nHandleLidSwitch=ignore\nHandleLidSwitchExternalPower=ignore\nHandleLidSwitchDocked=ignore\n' \
  > /etc/systemd/logind.conf.d/neuron-lid.conf

say "Never suspend"
systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target

say "User services run at boot with nobody logged in; sound device access without a desktop login"
loginctl enable-linger "$USR"
usermod -aG audio "$USR"

say "FTDI serial adapter: 1 ms receive delay (real panel)"
echo 'ACTION=="add", SUBSYSTEM=="usb-serial", DRIVER=="ftdi_sio", ATTR{latency_timer}="1"' \
  > /etc/udev/rules.d/99-neuron-ftdi.rules
udevadm control --reload

say "Firewall"
if ufw status | grep -q 'Status: active'; then
  NET=$(ip -4 route | awk '/proto kernel/ && !/docker|lxd/ {print $1; exit}')
  ufw allow from "$NET" to any port 22 proto tcp; ufw allow from "$NET" to any port 8080 proto tcp
else echo "ufw is off: SSH (22) and the web panel (8080) are open on the LAN"; fi

say "Battery charge limits"
if command -v tlp-stat >/dev/null; then tlp-stat -b | grep -iE 'charge_control|threshold|not supported' | head
else echo "tlp not installed (skipped; install tlp if you want battery charge limits)"; fi

say "Result"
systemctl is-enabled sleep.target; systemctl is-active ssh; loginctl show-user "$USR" -p Linger
hostname; ip -4 addr show | awk '/inet / && !/127.0.0.1/ {print $2}'
df -h / | tail -1
echo HEADLESS_SETUP_OK
