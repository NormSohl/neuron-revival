# The Neuron on an Ubuntu computer

Turns an ordinary PC or laptop with **Ubuntu 26.04 LTS** into the Neuron's computer: the original engine starts at
boot, drives the real front panel through a USB-to-RS-232 (FTDI) adapter and plays through a USB audio interface.
Tested on a ThinkPad (i7-3537U) with a MOTU M4, installed from scratch by following these steps.

## Install

```sh
git clone https://github.com/NormSohl/neuron-revival.git ~/neuron
sudo bash ~/neuron/desktop/install.sh ~/Downloads/Neuron80GB-OS15.rar
```

- `IMAGE` is the Neuron disk image (the `.rar`, the `.tib` inside it, or a folder with `p1.img` and `p5.img` from
  `tools/build_disk.py`), or `keep` to reuse an already-built `/opt/neuron/chroot` (for updates).
- Unpacking needs about 10 GB free. On a small disk: `sudo NEURON_WORK=/some/other/disk bash ~/neuron/desktop/install.sh …`
- An optional second argument names the ALSA device (e.g. `plughw:M4`); the default is the first USB audio
  interface that can play.
- Safe to run again: an existing NeuronDB (your saved sounds) is never overwritten.

Then reboot. The first start asks for your Neuron's serial number on the panel's keypad (it's on the bottom of the case).

## What it sets up

- `/opt/neuron/chroot`: the Neuron's 2002 system, root-owned, with the shims from `shim/`.
- `~/neuron-run/data/neuron`: the NeuronDB (models, sounds, globals), owned by you, bind-mounted into the chroot.
- `/usr/local/sbin/neuron-engine` (`neuron-engine` here): the root side. A sudo rule lets the installing user run
  only this, without a password. It checks its arguments, runs the engine in PERF mode as the transient systemd
  unit `neuron-engine` (`journalctl -u neuron-engine`), and plays straight to the USB interface through ALSA.
  Settings in `/etc/neuron/neuron.conf`.
- `neuron-engine set-buffer MS` (2-40, default 5) changes the output buffer; raise it if you hear dropouts.
  `neuron-engine set-audio auto|plughw:CARD=<id>,DEV=0` picks the output (the dashboard does this too).
- `systemd/neuron-headless.service`: a user service that starts the panel bridge (`stick/relay.py`) and the engine
  at boot, with or without a screen.
- `neuron-desktop.sh [stop]` and `neuron.desktop`: an app icon that opens the on-screen panel full screen
  (right-click → Stop the Neuron).
- `motu-exclusive.sh`: keeps PipeWire off USB audio, so the Neuron has the interface to itself and desktop sounds
  use the built-in speakers.
- `update-engine.sh`: reinstalls the root-side pieces after changes in this repo (the installer runs it).
- `headless-setup.sh` (optional): runs a laptop with its lid closed: SSH server, lid switch ignored, sleep masked.

The dashboard is at `http://<computer>.local:8080/` (output meters, Master Volume, audio output) and the on-screen
panel at `/panel`, from any phone, tablet or computer on the same network.

## Tips

- An FTDI adapter's latency timer is set to 1 ms by the installer's udev rule; other USB-serial chips may lag.
- Wi-Fi drivers can stall a whole machine for milliseconds at a time (Broadcom `wl` did, every two minutes); if
  dropouts come in a regular rhythm, try with Wi-Fi off and use Ethernet.
