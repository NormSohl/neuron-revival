# Launcher: original Neuron software on a modern x86 Linux PC

1. Build the disk partitions: `python3 -I tools/build_disk.py Neuron80GB-OS15.tib work`
2. Build the chroot: `sudo launcher/build_chroot.sh work neuron-root`
3. Run with the real panel on a USB-serial adapter (check signal levels first!):
   `sudo launcher/run_neuron.sh neuron-root /dev/ttyUSB0`
   Audio plays live through `aplay` (ALSA). For PipeWire use:
   `sudo launcher/run_neuron.sh neuron-root /dev/ttyUSB0 pw-cat -p --format s32 --rate 44100 --channels 2 -`
4. Without hardware: vpanel/live1.py runs the virtual panel on a pseudo-terminal and records to a WAV.

Tested 2026-11-15 in Claude's cloud workspace with the virtual panel and a real-time stand-in sound card:
start-up to "Sound 0 / Symbiont" in about 7 s, live audio peaking around -8 dBFS.
Latency is set by the pipe (4 KB, about 23 ms) and the player buffer (20 ms); a native JACK/PipeWire
client inside the stand-in library would cut that further.
