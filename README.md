# Neuron Revival

Tools and documentation for keeping the **Hartmann Neuron** synthesizer (2003) alive on modern hardware:
a modern x86 PC + SSD + USB audio, driving the Neuron's original front panel and keybed.
The story, with photos and recordings: [Reviving the Hartmann Neuron](https://www.sohl.com/2026/11/17/hartmann-neuron-revival/)
and [the software side](https://www.sohl.com/2026/11/24/hartmann-neuron-software/).

**This repository contains no Hartmann or Prosoniq code.** It runs the Neuron software that is already on
your own instrument's disk (and, for model making, the MODELmaker 1.2 package the community has shared for years).
Everything here is new code written from observing how those programs behave.

## What works
- **One-step install on Ubuntu 26.04 LTS** (`desktop/`): from the disk image to a computer that starts the Neuron at
  boot, with the real panel on a USB-serial adapter and sound on a USB audio interface. See `desktop/README.md`.
- **Panel bridge and web pages** (`stick/relay.py`, `stick/web/`): shares the engine's panel link between the real
  panel, an on-screen Neuron panel in any browser, and a text panel; a dashboard shows output levels and sets
  Master Volume and the audio output.
- **Bootable USB stick** (`stick/build-stick.sh`): the same setup as a live system that needs no install (Ubuntu
  24.04 based; being rebuilt and tested).
- **Disk image → files.** Rebuild the original OS from an Acronis `.tib` backup of the Neuron disk (`tools/`).
- **Run the original engine on modern Linux**, no Neuron motherboard needed (`launcher/`, `shim/`):
  real-time audio at 44.1 kHz, true 24-bit output to any ALSA device (USB interface).
- **Front-panel protocol decoded** — LCD, keys, encoders, sticks, keybed with velocity and aftertouch; every control
  checked on a real panel (`docs/panel-protocol.md`, `docs/panel-id-map.md`). The panel and keybed talk over one 115200-baud serial line (COM1).
- **Virtual front panel** for testing without the instrument (`vpanel/`).
- **Make your own models without an old Mac or Windows XP** (`modelmaker/`): runs MODELmaker 1.2's own analysis
  library headless on Linux. Optional 512-sample frame mode.

## What you need
- Your Neuron's disk image (or the disk), and its serial number (the OS asks for it at first boot).
- A 64-bit PC with Ubuntu 26.04 LTS for the one-step install (other Linux: see the manual quick start below; 32-bit
  userland support, `gcc-multilib`). Root only for the chroot mounts; the engine itself runs as a normal user.
- A USB audio interface, and an FTDI USB-to-RS-232 adapter for the panel cable.
- For model making: `NeuronMM_1_2_PC.zip` (MODELmaker 1.2 for Windows), available from the Neuron owners' Facebook group files.

### Where to find the Neuron files
- **[The &lt;NEURON&gt; File Vault](http://neuron.audiodsp.net/)**, the long-standing community archive (last updated 2009,
  still online in November 2026). It has an Acronis 9 image of the internal hard disk, every Neuron OS update from
  1.0.0 to 1.5.0, the v4 Model Set, the user, hook-up and ModelMaker manuals, and the Technical Hints & Tips manual.
- **The Neuron owners' Facebook group** files, for MODELmaker 1.2 and anything missing from the Vault.

## Quick start (Ubuntu, the main route)
```sh
git clone https://github.com/NormSohl/neuron-revival.git ~/neuron
sudo bash ~/neuron/desktop/install.sh ~/Downloads/Neuron80GB-OS15.rar    # then reboot
```
Details in `desktop/README.md`.

## Manual quick start (engine, any Linux)
```sh
# 1. disk image -> partition images (p1 = root, p5 = /var) -> chroot
python3 tools/build_disk.py Neuron80GB-OS15.tib work/      # uses tib_inflate.py + rebuild_ext.py
sudo launcher/build_chroot.sh work ./chroot                # copies files out with debugfs
# 2. build the audio/timing shims against the Neuron's own old glibc
shim/build.sh ./chroot
# 3. run it: panel on a USB-serial adapter (check levels first!) or the virtual panel
sudo launcher/run_neuron.sh ./chroot /dev/ttyUSB0
```
See `launcher/README.md` and `docs/native-run.md` for details and the **safety notes** (never run the engine as root
with real-time priority on a shared machine).

## Quick start (model making)
```sh
python3 modelmaker/jxparse.py MODELmaker_1_2.exe out/     # unpacks NASAnalysis.dll from the Windows package
gcc -m32 -O1 -o nasmm modelmaker/nasmm.c
python3 modelmaker/towav_aif.py mysound.wav mysound.aif   # -> 44.1 kHz / 16-bit / mono AIFF
NASDLL=out/files/NASAnalysis.dll ./nasmm mysound.aif MyModel 42 2
#   args: complexity depth (default 42 = MODELmaker "8"), Parameter Set 0-9
# copy MyModel.scape/.sphere into NeuronDB/Models/NNN.model/ as 000001.scape/.sphere with a map.script
```
Parameter Sets: 0 Default, 1 Stringed/Bowed, 2 Plucked & Bells, 3 Plucked & Picked, 4 Carpet Shop, 5 Piano etc.,
6 Woodwinds, 7 Extreme Pads, 8 Loop Factory, 9 Multipurpose. Details and test results: `docs/modelmaker-notes.md`.

## Status / help wanted
- Done and in daily use: the engine on a ThinkPad with Ubuntu 26.04, the real panel (every control checked),
  about 24 ms from key press to sound, about 11 ms of it inside the original engine's fixed 256-frame blocks
  (`tools/latency-test.py` measures it with a loopback cable).
- The USB stick is being rebuilt on Ubuntu 24.04 and tested.
- A clean-room replacement engine would remove the last dependency on the original binaries.

## Legal
The Neuron software and MODELmaker belong to their rights holders; they are **not** included or redistributed here.
This project exists to keep instruments that owners already paid for working, i.e. for interoperability.
If you hold the rights and want something changed, please open an issue.

## License
The code and documents in this repository: MIT (see `LICENSE`).
