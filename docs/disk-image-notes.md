# Disk image findings (2026-11-15)

Source: Neotrope's Neuron80GB-OS15.rar (sha256 078e2f0c...a5e25) → Neuron80GB-OS15.tib (Acronis True Image 9, 2,362,286,080 bytes).

Provenance (checked 2026-11-23): byte-for-byte identical (same sha256, `cmp` clean) to `Neuron80GB-OS15.rar` on the <NEURON> File Vault, http://neuron.audiodsp.net/Neuron80GB-OS15.rar (Last-Modified 21 Mar 2009; the vault credits the Acronis 9 image to Christopher Simmons, so "Neotrope" is probably his forum name). Only one version exists; no second copy kept.

## How the image was opened (no Acronis needed)
- The .tib is a sequence of zlib streams, 256 KiB of output each, with small headers between them (`tools/tib_inflate.py`).
- Chunk 1 holds the MBR (GRUB) and a header; partition 1 data starts at stream offset 32508.
- Partition 1 (root, hda1) is stored as used blocks only, in block order, with the backup superblock/GDT blocks in later groups left out. `tools/rebuild_ext.py` rebuilds it from the block bitmaps. Readable with debugfs; e2fsck still reports errors. Checked 2026-11-23: these are NOT the journal (inode 8, blocks 424-4525 in group 0, intact). They are the last block group, group 4 (blocks 131072-132535, inodes 53121-66400). Groups 0-3 rebuild exactly (bitmap counts match the group descriptors), but group 4 is stored out of the order the script assumes: its block and inode bitmaps sit at stream rank 56057/56058, 56 blocks earlier than computed, and after 60 inode-table blocks about 30 blocks of file data are interleaved before the table continues. So about 800 inodes in group 4 read as garbage. What lives there: terminfo entries, parts of /usr/lib/perl5 and /usr/lib/python2.2, ncurses HTML docs, keymaps and some kernel modules; nothing the Neuron program needs (it is on /var, partition 5, which is stored raw and opens cleanly). Not fixed: rebuild_ext.py would need to place group 4 by content.
- Partition 5 (hda5, mounted at /var; holds /home/neuron) is stored raw, sector by sector, from stream offset 237,458,960 to the end. Opens cleanly.

## The synth program
- `/var/home/neuron/bin/neuron`: ELF 32-bit i386, dynamically linked, stripped, 1,116,488 bytes, dated 8 Feb 2004.
- Libraries: libpthread, libasound.so.2 (ALSA), libstdc++.so.5, libm, libgcc_s, libc. No other Hartmann libraries: the DSP engine is built into this one file ("Now starting the DSP Core - Engine version").
- Real-time setup: mlockall, SCHED priorities via pthread, setitimer, /proc/sys/kernel/lowlatency.

## Front panel interface: SERIAL, not parallel
- Class `PanelHndlr` opens `SerialDrv` on **/dev/ttyS0 (COM1) at 115200 baud** (0x1c200 in the code), using termios.
- At start-up it sends bytes 0x00, 0xFF, 0xFD, 0xFD, ... to the panel.
- So the small cable from the panel most likely goes to the motherboard's COM1 header (the hints PDF shows an RS232 connector next to VGA). Needs a look to confirm.
- Consequence: the panel needs only a 115200-baud serial port (UART), at 3.3/5 V or RS-232 levels; check which before connecting anything. Any modern PC (USB-serial adapter) or an RP2040 can talk to it.

## Audio and MIDI: standard ALSA
- Audio: `snd_pcm_open("hw:0,0")`, mmap writes, 6 channels for 5.1. Card 0 = `snd-ice1712` (Envy24 / TerraTec EWS).
- MIDI: ALSA rawmidi.
- No direct port I/O (no ioperm/inb/outb). So audio and MIDI can be redirected to any ALSA device by configuration, e.g. an asoundrc that points hw:0,0 to a USB interface, or a VM sound card.

## Boot chain
- Kernel 2.4.19-gentoo-r7 (bzImage, built 18 Oct 2002), GRUB, devfs. Runlevel 3 = "neuron".
- `/etc/init.d/neuron` → `conf.d/neuron.start` touches `/mnt/.init.d/neuron-run`; `/sbin/neuron-safe` (a watchdog, started elsewhere) runs the program while that file exists.
- Stock ALSA 0.9-era modules in /lib/modules/2.4.19-gentoo-r7.

## Next
1. Confirm the panel cable goes to COM1 and measure signal levels.
2. Disassemble PanelHndlr / SerialDrv to decode the panel protocol (messages in and out, LED/LCD commands).
3. Boot test: run the root + /var partitions in QEMU with a virtual serial port and an emulated sound card.
