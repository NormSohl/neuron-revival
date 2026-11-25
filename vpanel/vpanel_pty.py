import os, pty, subprocess, threading, time, sys, termios, tty
import os
R=os.environ.get('NEURON_CHROOT','./chroot')
class PtyPanel:
    """Virtual panel on a pseudo-terminal bind-mounted as the chroot's /dev/ttyS0."""
    def __init__(self):
        self.m, s = pty.openpty(); tty.setraw(self.m); tty.setraw(s)
        self.spath = os.ttyname(s); self.s=s
        subprocess.run(['sudo','umount',R+'/dev/ttyS0'],stderr=subprocess.DEVNULL)
        subprocess.run(['sudo','mount','--bind',self.spath,R+'/dev/ttyS0'],check=True)
        subprocess.run(['sudo','chmod','666',self.spath])
        self.lcd=[[' ']*16,[' ']*16]; self.regs={}; self.log=[]; self.raw=bytearray(); self.pending=None
        threading.Thread(target=self._rx,daemon=True).start()
    def _rx(self):
        while True:
            try: b=os.read(self.m,4096)
            except OSError: time.sleep(0.05); continue
            self.raw+=b
            for x in b: self._byte(x)
    def _byte(self,x):
        if self.pending is None:
            if x>=0xFA and x!=0xFC: self.log.append((x,None)); return
            self.pending=x; return
        c,self.pending=self.pending,None
        if 0x4E<=c<=0x5D: self.lcd[0][c-0x4E]=chr(x) if 32<=x<127 else '~'
        elif 0x5E<=c<=0x6D: self.lcd[1][c-0x5E]=chr(x) if 32<=x<127 else '~'
        else: self.regs[c]=x; self.log.append((c,x))
    def screen(self): return '|'+''.join(self.lcd[0])+'| |'+''.join(self.lcd[1])+'|'
    def send(self,*bs): os.write(self.m,bytes(bs))
    def press(self,i,dt=0.08): self.send(i,1); time.sleep(dt); self.send(i,0); time.sleep(dt)
def launch(logpath='/tmp/neuron_stderr.txt', secs=60):
    # SAFE MODE: normal user (no real-time priority possible), one CPU core, 1.5 GB address-space cap,
    # memory locking faked by libnort, hard kill after `secs`.
    cmd=('ulimit -v 1500000; ulimit -l 0; cd /home/neuron && '
         'LD_LIBRARY_PATH=/opt/shim LD_PRELOAD=/opt/shim/libnort.so exec ./neuron log')
    return subprocess.Popen(['sudo','timeout','-s','KILL',str(secs),'taskset','-c','0','nice','-n','19',
                             'chroot','--userspec=1000:1000',R,'/bin/sh','-c',cmd],
                            stdout=open(logpath,'w'),stderr=subprocess.STDOUT)
