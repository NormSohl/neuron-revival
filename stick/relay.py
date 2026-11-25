#!/usr/bin/env python3
"""Neuron panel relay and web panel server.

The engine's panel serial port is a pseudo-terminal owned by this program. Everything the engine
sends (LEDs, main LCD, section displays) is kept as panel state and passed on to every panel:
  - web pages (WebSocket /ws): the dashboard at / and the virtual panel at /panel, on this PC's
    screen, an iPad, a tablet...
Output meters: the engine's sound shim writes levels to NEURON_LEVELS; /ws/levels streams them.
  - raw panel-protocol clients on /run/neuron/panel.sock (e.g. the text keyboard panel)
  - optionally the real Neuron panel on a serial port (REAL_PANEL=/dev/ttyUSB0)
Web pages can also listen to the sound (WebSocket /audio): while anyone listens, pw-record captures what
this PC plays (the default output's monitor) and the raw 16-bit 44.1 kHz stereo is sent in ~20 ms chunks.
Input from all of them is merged and sent to the engine as whole 2-byte messages.
"""
import asyncio, os, pty, tty, termios, json, sys, time, re, glob, shlex

PORT = int(os.environ.get('WEB_PORT', '8080'))
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
RUN = os.environ.get('NEURON_RUN', '/run/neuron'); os.makedirs(RUN, exist_ok=True)   # NEURON_RUN: desktop use without root
REAL = os.environ.get('REAL_PANEL', '')
LEVELS = os.environ.get('NEURON_LEVELS', '/opt/neuron/chroot/var/tmp/neuron_levels')
# audio output picker (installed Ubuntu setup only: it needs the root helper neuron-engine)
ASOUND = os.environ.get('NEURON_ASOUND', '/proc/asound')
ENGINE = os.environ.get('NEURON_ENGINE', '/usr/local/sbin/neuron-engine')
SUDO = shlex.split(os.environ.get('NEURON_SUDO', 'sudo -n'))
CONF = os.environ.get('NEURON_CONF', '/etc/neuron/neuron.conf')

from aiohttp import web

regs = [0] * 256          # panel output registers as last sent by the engine
web_clients = set()
raw_clients = set()       # asyncio StreamWriters
level_clients = set()     # dashboard meter WebSockets
master_vol = None         # last Master Volume the engine showed on its LCD (neuron.globals is only saved now and then)
changed = {}              # reg -> value, pending broadcast
real_fd = None
real_missing_logged = False
real_logged = 0           # bytes from the real panel already echoed to the log

# ---------------------------------------------------------------- engine side (pty)
master, slave = pty.openpty(); tty.setraw(master); tty.setraw(slave)
spath = os.ttyname(slave)
with open(RUN + '/vpanel.pty.tmp', 'w') as f: f.write(spath)
os.replace(RUN + '/vpanel.pty.tmp', RUN + '/vpanel.pty')

class Parser:
    """Splits a byte stream into ('msg', id, value) and ('ctl', byte) items."""
    def __init__(self, fc_tail): self.pend = None; self.skip = 0; self.fc_tail = fc_tail
    def feed(self, data):
        out = []
        for x in data:
            if self.skip: self.skip -= 1; continue
            if self.pend is None:
                if x >= 0xFA:
                    out.append(('ctl', x))
                    if x == 0xFC and self.fc_tail: self.skip = 4
                    continue
                self.pend = x; continue
            out.append(('msg', self.pend, x)); self.pend = None
        return out

from_engine = Parser(fc_tail=True)     # host sends 0xFC + 4 test bytes
from_real = Parser(fc_tail=False)

def to_engine(b):
    try: os.write(master, bytes(b))
    except OSError: pass

def engine_readable():
    try: data = os.read(master, 4096)
    except OSError: return
    if real_fd is not None:
        try: os.write(real_fd, data)
        except OSError: pass
    for w in list(raw_clients):
        try: w.write(data)
        except Exception: raw_clients.discard(w)
    lcd_dirty = False
    for item in from_engine.feed(data):
        if item[0] == 'msg':
            _, r, v = item
            if regs[r] != v or r not in changed:
                regs[r] = v; changed[r] = v
                if 0x4E <= r <= 0x6D: lcd_dirty = True
        elif item[1] == 0xFD:
            changed[-1] = 1                       # engine (re)started its panel link
    if lcd_dirty: track_volume()

def track_volume():
    """The engine shows 'Volume: N' on the main LCD while Master Vol changes; remember N."""
    global master_vol
    txt = ''.join(chr(c - 0x80 if 0xB0 <= c <= 0xB9 else c) if 32 <= (c - 0x80 if 0xB0 <= c <= 0xB9 else c) < 127 else ' '
                  for c in regs[0x4E:0x6E])
    m = re.search(r'vol(?:ume)?\s*:?\s*(\d{1,3})', txt, re.I)
    if m and int(m.group(1)) <= 127: master_vol = int(m.group(1))

# ---------------------------------------------------------------- real panel (optional)
def open_real():
    global real_fd
    if not REAL: return
    try:
        fd = os.open(REAL, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        a = termios.tcgetattr(fd); tty.setraw(fd)
        a = termios.tcgetattr(fd)
        a[4] = a[5] = termios.B115200; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        termios.tcsetattr(fd, termios.TCSANOW, a)
        real_fd = fd
        asyncio.get_event_loop().add_reader(fd, real_readable)
        print('real panel on', REAL, flush=True)
    except OSError as e:
        global real_missing_logged
        if not real_missing_logged: print('real panel not available:', e, flush=True)
        real_missing_logged = True

def close_real(why):
    global real_fd, real_missing_logged
    if real_fd is None: return
    asyncio.get_event_loop().remove_reader(real_fd)
    try: os.close(real_fd)
    except OSError: pass
    real_fd = None; real_missing_logged = False
    print('real panel lost:', why, flush=True)

async def real_watch_loop():
    """Headless boot: the USB serial adapter may appear late, or be unplugged and plugged back in."""
    while True:
        await asyncio.sleep(2)
        if real_fd is None: open_real()

def real_readable():
    try: data = os.read(real_fd, 4096)
    except OSError as e: close_real(e); return
    if not data: close_real('end of file'); return
    global real_logged
    if real_logged < 64:                      # first bytes from the real panel, for bring-up
        print('from real panel:', data[:64 - real_logged].hex(' '), flush=True); real_logged += len(data)
    tap = os.path.exists(TAP_FLAG)
    for item in from_real.feed(data):
        if tap: tap_log(item)
        if item[0] == 'msg': to_engine([item[1], item[2]])
        else: to_engine([item[1]])

# Control-by-control testing: while RUN/tap exists, every message from the real panel is appended to
# RUN/panel-input.log as "HH:MM:SS.mmm ID VALUE" (hex). touch / rm the flag; no restart needed.
TAP_FLAG = RUN + '/tap'; TAP_LOG = RUN + '/panel-input.log'
def tap_log(item):
    t = time.time(); s = time.strftime('%H:%M:%S', time.localtime(t)) + '.%03d' % (int(t * 1000) % 1000)
    line = s + ' ' + ' '.join('%02x' % b for b in item[1:]) + '\n'
    try:
        with open(TAP_LOG, 'a') as f: f.write(line)
    except OSError: pass

# ---------------------------------------------------------------- hello / keep-alive
async def hello_loop():
    """Without a real panel, someone must say "panel ready" (0xFD) so the engine sends its UI."""
    while True:
        await asyncio.sleep(2)
        if real_fd is None and not any(regs[0x4E:0x5E]):
            to_engine([0xFD])

# ---------------------------------------------------------------- broadcast
async def broadcast_loop():
    while True:
        await asyncio.sleep(0.02)
        if not changed: continue
        restart = changed.pop(-1, None)
        upd = [[r, v] for r, v in changed.items()]; changed.clear()
        msg = json.dumps({'r': upd} if not restart else {'r': upd, 'restart': 1})
        for ws in list(web_clients):
            try: await ws.send_str(msg)
            except Exception: web_clients.discard(ws)

# ---------------------------------------------------------------- web
async def ws_handler(request):
    ws = web.WebSocketResponse(heartbeat=20); await ws.prepare(request)
    web_clients.add(ws)
    await ws.send_str(json.dumps({'all': regs, 'globals': read_globals(), 'vol': master_vol}))
    try:
        async for m in ws:
            if m.type != web.WSMsgType.TEXT: continue
            try: d = json.loads(m.data)
            except ValueError: continue
            for i, v in d.get('m', []):
                if 0 <= i < 0xFA and 0 <= v < 0xFA: to_engine([i, v])
    finally:
        web_clients.discard(ws)
    return ws

def read_globals():
    g = {}
    for p in (os.environ.get('NEURON_GLOBALS', ''), '/opt/neuron/chroot/home/neuron/NeuronDB/neuron.globals', '/data/neuron/NeuronDB/neuron.globals'):
        try:
            for line in open(p):
                k, _, v = line.strip().partition('\t')
                if v.lstrip('-').isdigit(): g[k] = int(v)
            break
        except OSError: continue
    return g

async def index(request): return web.FileResponse(os.path.join(WEB, 'dashboard.html'))
async def panel(request): return web.FileResponse(os.path.join(WEB, 'index.html'))

# ---------------------------------------------------------------- audio output picker
def audio_cards():
    """USB audio devices that can play: [{'dev', 'id', 'name'}], in card order."""
    names = {}
    try:
        lines = open(ASOUND + '/cards').read().splitlines()
        for i, l in enumerate(lines):
            m = re.match(r'\s*(\d+) \[(\S+)\s*\]: .*? - (.*)$', l)
            if m:
                long = lines[i + 1].strip() if i + 1 < len(lines) else ''
                names[m.group(2)] = (long.split(' at usb-')[0] or m.group(3)).strip()
    except OSError: pass
    out = []
    for d in sorted(glob.glob(ASOUND + '/card[0-9]*'), key=lambda s: int(re.sub(r'\D', '', s) or 0)):
        if not os.path.exists(d + '/usbid') or not glob.glob(d + '/pcm*p'): continue
        try: cid = open(d + '/id').read().strip()
        except OSError: continue
        out.append({'dev': 'plughw:CARD=%s,DEV=0' % cid, 'id': cid, 'name': names.get(cid, cid)})
    return out

def audio_setting():
    try:
        for l in open(CONF):
            if l.startswith('AUDIO_DEV='): return l.strip().split('=', 1)[1]
    except OSError: pass
    return 'auto'

async def audio_get(request):
    cards = audio_cards(); cur = audio_setting()
    in_use = cards[0]['dev'] if cur == 'auto' and cards else (cur if cur != 'auto' else None)
    return web.json_response({'setting': cur, 'in_use': in_use, 'cards': cards,
                              'can_set': os.access(ENGINE, os.X_OK)})

async def run(*cmd):
    p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    out, _ = await p.communicate(); return p.returncode, out.decode(errors='replace').strip()

async def audio_set(request):
    if not os.access(ENGINE, os.X_OK): return web.json_response({'ok': False, 'msg': 'not available on this setup'}, status=400)
    try: dev = (await request.json()).get('dev', '')
    except ValueError: dev = ''
    if dev != 'auto' and dev not in [c['dev'] for c in audio_cards()]:
        return web.json_response({'ok': False, 'msg': 'unknown device'}, status=400)
    rc, msg = await run(*SUDO, ENGINE, 'set-audio', dev)
    if rc: return web.json_response({'ok': False, 'msg': msg}, status=500)
    await run(*SUDO, ENGINE, 'stop')                                   # restart the engine on the new output
    rc, msg2 = await run(*SUDO, ENGINE, 'start', spath)
    print('audio output ->', dev, '(engine restart rc=%d)' % rc, flush=True)
    return web.json_response({'ok': rc == 0, 'msg': msg if rc == 0 else msg2})

# ---------------------------------------------------------------- output meters
async def levels_ws(request):
    ws = web.WebSocketResponse(heartbeat=20); await ws.prepare(request)
    level_clients.add(ws)
    try:
        async for _ in ws: pass
    finally:
        level_clients.discard(ws)
    return ws

async def levels_loop():
    """~30 times a second: read the shim's latest levels and send them to the dashboards."""
    last = None
    while True:
        await asyncio.sleep(0.033)
        if not level_clients: continue
        try:
            st = os.stat(LEVELS)
            with open(LEVELS) as f: line = f.readline()
            v = [float(x) for x in line.split()[:4]]
        except (OSError, ValueError): v, st = None, None
        stamp = st.st_mtime_ns if st else None
        live = v is not None and len(v) == 4 and stamp is not None and time.time() - st.st_mtime < 0.5
        if stamp == last and live: continue
        last = stamp
        msg = json.dumps({'lv': v if live else None})
        for ws in list(level_clients):
            try: await ws.send_str(msg)
            except Exception: level_clients.discard(ws)

# ---------------------------------------------------------------- sound to remote pages (iPad)
AUDIO_CHUNK = 882 * 4                 # 20 ms of s16 stereo at 44.1 kHz
audio_clients = set()
audio_task = None

async def audio_pump():
    """Runs pw-record while anyone listens; restarts it if it dies."""
    while audio_clients:
        try:
            proc = await asyncio.create_subprocess_exec(
                'pw-record', '-P', '{ stream.capture.sink = true node.name = neuron-web-audio }',
                '--format', 's16', '--rate', '44100', '--channels', '2', '--latency', '10ms', '-',
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        except OSError as e:
            print('web audio: cannot start pw-record:', e, flush=True); return
        print('web audio: capture started', flush=True)
        try:
            while audio_clients:
                data = await proc.stdout.readexactly(AUDIO_CHUNK)
                for ws in list(audio_clients):
                    if ws.closed: audio_clients.discard(ws); continue
                    try: await ws.send_bytes(data)
                    except Exception: audio_clients.discard(ws)
        except (asyncio.IncompleteReadError, ConnectionError):
            await asyncio.sleep(1)
        finally:
            if proc.returncode is None:
                proc.terminate()
                try: await asyncio.wait_for(proc.wait(), 2)
                except asyncio.TimeoutError: proc.kill()
    print('web audio: capture stopped', flush=True)

async def audio_handler(request):
    global audio_task
    ws = web.WebSocketResponse(heartbeat=20); await ws.prepare(request)
    audio_clients.add(ws)
    if audio_task is None or audio_task.done(): audio_task = asyncio.create_task(audio_pump())
    try:
        async for m in ws: pass
    finally:
        audio_clients.discard(ws)
    return ws


# ---------------------------------------------------------------- raw socket clients
async def raw_client(reader, writer):
    writer.write(bytes(b for r in range(0xFA) if regs[r] < 0xFA for b in (r, regs[r])))   # current state
    raw_clients.add(writer)
    p = Parser(fc_tail=False)
    try:
        while True:
            data = await reader.read(4096)
            if not data: break
            for item in p.feed(data):
                if item[0] == 'msg': to_engine([item[1], item[2]])
                else: to_engine([item[1]])
    finally:
        raw_clients.discard(writer)

async def main():
    loop = asyncio.get_event_loop()
    loop.add_reader(master, engine_readable)
    open_real()
    sock = RUN + '/panel.sock'
    if os.path.exists(sock): os.unlink(sock)
    await asyncio.start_unix_server(raw_client, path=sock); os.chmod(sock, 0o666)
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_get('/panel', panel)
    app.router.add_get('/ws', ws_handler)
    app.router.add_get('/ws/levels', levels_ws)
    app.router.add_get('/api/audio', audio_get)
    app.router.add_post('/api/audio', audio_set)
    app.router.add_get('/audio', audio_handler)
    app.router.add_static('/static/', WEB)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()
    print(f'relay ready: engine pty {spath}, web on port {PORT}', flush=True)
    asyncio.create_task(hello_loop())
    asyncio.create_task(levels_loop())
    if REAL: asyncio.create_task(real_watch_loop())
    await broadcast_loop()

asyncio.run(main())
