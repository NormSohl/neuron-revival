#!/usr/bin/env python3
"""Measure the Neuron's key-to-sound delay with a loopback cable.

Setup (on the ThinkPad, with the Neuron running):
  1. Turn the MOTU's monitor and output knobs down, and the speakers off or low.
  2. Plug a cable from MOTU OUTPUT 1 into MOTU INPUT 1 (line level; set input 1's gain low).
  3. Pick a sound with a sharp attack (a pluck or percussive sound, not a slow pad).
  4. python3 latency-test.py            (options: --trials 20 --note 60 --dev plughw:M4)

What it does: sends a keybed note through the panel bridge (the same message the real keybed
sends), records input 1 of the MOTU, and times how long until the sound arrives. It prints the
median and spread over several notes.

What the number includes: panel bridge -> engine -> audio out -> cable -> audio IN -> this script.
The input side (MOTU's converter, USB, and the 1 ms capture blocks) adds roughly 2-3 ms that a
player never hears, so the real key-to-ear figure is a little lower than the one printed.
It does not include the real keybed's own scan time or the serial cable, about 1 ms.
"""
import argparse, socket, struct, subprocess, sys, threading, time, statistics

ap = argparse.ArgumentParser()
ap.add_argument('--trials', type=int, default=20)
ap.add_argument('--note', type=int, default=60, help='MIDI note number (36-123); 60 = middle C')
ap.add_argument('--vel', type=int, default=30, help='key travel time: smaller = harder (12 hard, 60 soft)')
ap.add_argument('--dev', default='plughw:M4', help='ALSA capture device (the MOTU)')
ap.add_argument('--sock', default='/run/neuron/panel.sock')
ap.add_argument('--hold', type=float, default=0.30, help='seconds the key is held')
ap.add_argument('--gap', type=float, default=0.70, help='seconds of silence between notes')
a = ap.parse_args()
RATE, CHUNK = 44100, 44                      # 44 frames = 1 ms per read

# panel bridge: raw panel-protocol client, exactly like the text keyboard panel
sk = socket.socket(socket.AF_UNIX); sk.connect(a.sock)
def drain():                                  # discard the panel traffic the bridge sends us
    while sk.recv(4096): pass
threading.Thread(target=drain, daemon=True).start()
nid = a.note + 0x37
def note(on): sk.send(bytes([nid, a.vel if on else 0]))

rec = subprocess.Popen(['arecord', '-q', '-D', a.dev, '-f', 'S32_LE', '-c', '1', '-r', str(RATE), '-t', 'raw',
                        '--buffer-time=4000', '--period-time=1000'], stdout=subprocess.PIPE, bufsize=0)
def read_chunk():
    b = b''
    while len(b) < CHUNK * 4:
        d = rec.stdout.read(CHUNK * 4 - len(b))
        if not d: sys.exit('arecord stopped (is the MOTU name right? try: arecord -l)')
        b += d
    return max(abs(x) for x in struct.unpack('<%di' % CHUNK, b)) / 2**31

def wait_quiet(seconds):
    """Read for `seconds`; return the loudest 1 ms chunk seen (the noise floor between notes)."""
    peak, end = 0.0, time.monotonic() + seconds
    while time.monotonic() < end: peak = max(peak, read_chunk())
    return peak

print('settling...'); wait_quiet(1.0)
results = []
try:
    for i in range(a.trials):
        floor = wait_quiet(a.gap)
        thr = max(0.02, floor * 8)              # onset = 8x the noise floor, at least -34 dBFS
        t0 = time.monotonic(); note(True); dt = None
        while time.monotonic() - t0 < a.hold:
            if read_chunk() > thr and dt is None: dt = (time.monotonic() - t0) * 1000
        note(False)
        if dt is None: print(f'{i+1:2d}: no sound detected (floor {floor:.4f}); check cable, gain and sound'); continue
        results.append(dt); print(f'{i+1:2d}: {dt:5.1f} ms')
finally:
    note(False); rec.terminate()
if results:
    print(f'\nkey-to-sound (incl. ~2-3 ms of input path): median {statistics.median(results):.1f} ms, '
          f'min {min(results):.1f}, max {max(results):.1f}, over {len(results)} notes')
    if len(results) > 1: print(f'spread (stdev) {statistics.stdev(results):.1f} ms; a large spread means timing jitter')
