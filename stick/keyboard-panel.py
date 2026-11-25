#!/usr/bin/env python3
"""Neuron text panel on the PC's own keyboard and screen (fallback when the browser panel is not running).

Creates a pseudo-terminal that the Neuron engine uses as its panel serial port, shows the
Neuron's main LCD and Resynator model names on this console, and turns key presses into
panel messages (keybed notes with press and release, sound selection, encoders, keypad).
Keys are read from the Linux input devices, so key releases are seen like on a real keybed.
"""
import os, pty, tty, termios, struct, select, time, glob, fcntl, sys

import socket
RUN = '/run/neuron'
for _ in range(60):                       # the panel relay owns the engine's panel port; connect to it
    try: sk = socket.socket(socket.AF_UNIX); sk.connect(RUN + '/panel.sock'); break
    except OSError: time.sleep(1)
master = sk.fileno()

# ---- panel state -------------------------------------------------------------------------
lcd = [[' '] * 16, [' '] * 16]
regs = {}
pend = None
got_any = False
octave = 0          # shift in octaves from C3
vel_names = ['soft', 'medium', 'hard']; vel_vals = [60, 30, 12]; vel = 1   # key travel time: small = hard
held = {}           # keycode -> panel ID of the sounding note
status = ''

def send(*b): os.write(master, bytes(b))

def rx(data):
    global pend, got_any
    for x in data:
        got_any = True
        if pend is None:
            if x >= 0xFA and x != 0xFC:
                if x == 0xFD: pass
                continue
            pend = x; continue
        c, pend = pend, None
        if 0x4E <= c <= 0x6D and 0xB0 <= x <= 0xB9: x -= 0x80   # highlighted digit (sound picked, not loaded yet)
        if 0x4E <= c <= 0x5D: lcd[0][c - 0x4E] = chr(x) if 32 <= x < 127 else ' '
        elif 0x5E <= c <= 0x6D: lcd[1][c - 0x5E] = chr(x) if 32 <= x < 127 else ' '
        else: regs[c] = x

def name(a, b):
    return ''.join(chr(regs.get(i, 32)) if 32 <= regs.get(i, 32) < 127 else ' ' for i in range(a, b + 1)).strip()

# ---- keyboard map ------------------------------------------------------------------------
# Linux key codes. Two piano rows, tracker style: Z S X D C V G B H N J M , L . ; /  and  Q 2 W 3 E R 5 T 6 Y 7 U I 9 O 0 P
LOWER = [44, 31, 45, 32, 46, 47, 34, 48, 35, 49, 36, 50, 51, 38, 52, 39, 53]
UPPER = [16, 3, 17, 4, 18, 19, 6, 20, 7, 21, 8, 22, 23, 10, 24, 11, 25]
NOTE = {k: i for i, k in enumerate(LOWER)}
NOTE.update({k: 12 + i for i, k in enumerate(UPPER)})
KEYPAD = {82: 0x0A, 79: 0x06, 80: 0x07, 81: 0x08, 75: 0x03, 76: 0x04, 77: 0x05, 71: 0x00, 72: 0x01, 73: 0x02}
KEY_MINUS, KEY_EQUAL, KEY_F5, KEY_F6 = 12, 13, 63, 64
KEY_PGDN, KEY_PGUP, KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN = 109, 104, 105, 106, 103, 108
KEY_ENTER, KEY_KPENTER, KEY_SPACE = 28, 96, 57
KEY_LEFTBRACE, KEY_RIGHTBRACE = 26, 27
KEY_HOME, KEY_END = 102, 107
JOY = {KEY_UP: 8, KEY_DOWN: 1, KEY_LEFT: 0x10, KEY_RIGHT: 2}   # 0x52 bits; Enter = push (4)

def all_notes_off():
    for k, nid in list(held.items()): send(nid, 0)
    held.clear()

def key(code, down):
    global octave, vel, status
    if code in NOTE:
        n = 48 + 12 * octave + NOTE[code]
        if not 36 <= n <= 123: return
        nid = n + 0x37
        if down: held[code] = nid; send(nid, vel_vals[vel])
        elif code in held: send(held.pop(code), 0)
        return
    if not down: return
    if code == KEY_MINUS: all_notes_off(); octave = max(octave - 1, -1)
    elif code == KEY_EQUAL: all_notes_off(); octave = min(octave + 1, 4)
    elif code == KEY_F5: vel = max(vel - 1, 0)
    elif code == KEY_F6: vel = min(vel + 1, 2)
    elif code == KEY_PGUP: send(0x40, 1)                                               # data knob up (next sound on the sound page)
    elif code == KEY_PGDN: send(0x40, 0)                                               # data knob down
    elif code == KEY_HOME: send(0x25, 1); time.sleep(0.05); send(0x25, 0)              # Sound page (a tap: held 2 s = full reset)
    elif code == KEY_END: send(0x0B, 1); time.sleep(0.03); send(0x0B, 0)               # Next Snd
    elif code in JOY: send(0x52, JOY[code]); time.sleep(0.05); send(0x52, 0)      # menu joystick
    elif code == KEY_RIGHTBRACE: send(ord('H'), 1)                                    # master volume up
    elif code == KEY_LEFTBRACE: send(ord('H'), 0)                                     # master volume down
    elif code in (KEY_ENTER, KEY_KPENTER): send(0x52, 4); time.sleep(0.05); send(0x52, 0)
    elif code in KEYPAD: send(KEYPAD[code], 1); time.sleep(0.03); send(KEYPAD[code], 0)
    elif code == KEY_SPACE: all_notes_off()

# ---- input devices -----------------------------------------------------------------------
EVFMT = 'llHHi'; EVSZ = struct.calcsize(EVFMT)
devs = {}
def scan():
    for p in glob.glob('/dev/input/event*'):
        if p in devs.values(): continue
        try:
            name_ = open('/sys/class/input/%s/device/name' % os.path.basename(p)).read().lower()
            caps = open('/sys/class/input/%s/device/capabilities/key' % os.path.basename(p)).read().split()
        except OSError: continue
        if len(caps) < 2 and 'keyboard' not in name_: continue      # skip power buttons etc.
        try: fd = os.open(p, os.O_RDONLY | os.O_NONBLOCK)
        except OSError: continue
        devs[fd] = p

# ---- screen ------------------------------------------------------------------------------
con = sys.stdout
def draw():
    l0, l1 = ''.join(lcd[0]), ''.join(lcd[1])
    r1, r2 = name(0x9D, 0xA4), name(0xC9, 0xD0)
    con.write('\033[H\033[2J')
    con.write('\n   HARTMANN NEURON  -  keyboard panel\n\n')
    con.write('      +------------------+\n')
    con.write('      | %s |\n      | %s |\n' % (l0, l1))
    con.write('      +------------------+\n\n')
    con.write('   Resynator 1: %-12s  Resynator 2: %s\n\n' % (r1 or '-', r2 or '-'))
    con.write('   Octave: C%d   Velocity: %s   Notes held: %d   %s\n\n' % (3 + octave, vel_names[vel], len(held),
              '' if ''.join(lcd[0]).strip() else '(waiting for the engine...)'))
    con.write('   Play:    Z S X D C V B ...  (lower row, from C)    Q 2 W 3 E R ...  (upper row, one octave up)\n')
    con.write('   Octave:  -  and  =          Velocity:  F5 softer, F6 harder        Space: all notes off\n')
    con.write('   Sound:   Home = sound page  PgUp/PgDn = data (sound up/down)     Arrows = menu joystick   Enter = push   [ ] = volume\n')
    con.write('   Keypad:  number-pad digits = Neuron keypad\n')
    con.flush()

# console: no echo, no line buffering
try:
    attrs = termios.tcgetattr(0); attrs[3] &= ~(termios.ECHO | termios.ICANON); termios.tcsetattr(0, termios.TCSANOW, attrs)
except termios.error: pass
con.write('\033[?25l')

last_draw = 0; last_scan = 0; last_hello = 0
while True:
    now = time.time()
    if now - last_scan > 2: scan(); last_scan = now
    r, _, _ = select.select([master, 0] + list(devs), [], [], 0.1)
    for fd in r:
        if fd == master:
            try: rx(os.read(master, 4096))
            except OSError: pass
        elif fd == 0:
            try: os.read(0, 1024)          # swallow typed characters
            except OSError: pass
        else:
            try: data = os.read(fd, EVSZ * 64)
            except OSError: os.close(fd); devs.pop(fd, None); continue
            for i in range(0, len(data) - EVSZ + 1, EVSZ):
                _, _, typ, code, val = struct.unpack(EVFMT, data[i:i + EVSZ])
                if typ == 1 and val in (0, 1): key(code, val == 1)
    if now - last_draw > 0.25: draw(); last_draw = now
