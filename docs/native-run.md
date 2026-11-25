# Running the original Neuron software natively on modern Linux (2026-11-15)

Result: the original `neuron` binary (OS 1.5, DSP engine 1.42, 08.02.04) runs on a modern x86-64 Linux
machine in a chroot built from the disk image, driven by the virtual panel, and produces correct, in-tune audio.
First recording: recordings/2026-11-15-first-notes-symbiont.wav.

## Recipe (all files in shim/ and vpanel/)
1. chroot = root partition + /home/neuron from /var (debugfs rdump).
2. Stand-in ALSA library (shim/fakeasound_vm.c -> /opt/shim/libasound.so.2): old 0.9 API; the app opens hw:0,0
   for PCM (10 ch, S32_LE, 44.1 kHz, 256-frame periods) and rawmidi. Audio saved to /var/tmp/neuron_audio.raw
   (10 ch, 16-bit; samples >>16). Timestamps report ~0% load.
3. Fake 2.4-style /proc in the chroot: meminfo (2.4 layout), sys/kernel/lowlatency, acpi/event (FIFO).
4. Panel: a pseudo-terminal bind-mounted as /dev/ttyS0; vpanel_pty.py speaks the panel protocol.
5. **Safe mode (important):** run as a normal user, one CPU core, `ulimit -v`, with shim/libnort.so preloaded
   (fakes mlockall and real-time scheduling). Running as root with real-time priority took the cloud machine down twice.
6. Database folders on the disk have mode drw-r--r-- (no x bit; root ignored it). For a non-root run: chmod 755 all
   directories under NeuronDB, or sounds fail to load ("couldn't get sound file") and the output is silent.
7. Command-line switches: `log` (log to stdout), `sched`, `noinit` (skip init stage).

## Observations
- Start-up to "Sound 0 / Symbiont": about 6 s natively.
- Notes are echoed on MIDI out; velocity came out as 25 for every note (velocity-curve tables to be checked).
- Output on channels 1-2, copy on 9-10 (probably S/PDIF). Level about -30 dBFS at default master volume / velocity 25.
- In QEMU without KVM the engine is far too slow (software floating point); natively it runs in real time.
