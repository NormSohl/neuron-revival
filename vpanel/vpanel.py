"""Virtual Neuron front panel: talks to the Neuron software over a serial socket.
Decodes main-LCD writes (0x4E+n line 1, 0x5E+n line 2) and logs every other [CMD][VALUE]."""
import socket, time, sys, threading, json
class VPanel:
    def __init__(self, path):
        self.s=socket.socket(socket.AF_UNIX); self.s.connect(path)
        self.lcd=[[' ']*16,[' ']*16]; self.regs={}; self.log=[]; self.raw=bytearray()
        self.pending=None; self.lock=threading.Lock()
        threading.Thread(target=self._rx,daemon=True).start()
    def _rx(self):
        while True:
            b=self.s.recv(4096)
            if not b: break
            with self.lock:
                self.raw+=b
                for x in b: self._byte(x)
    def _byte(self,x):
        if self.pending is None:
            if x==0xFD or x>=0xFA and x!=0xFC: self.log.append((x,None)); return
            self.pending=x; return
        c,self.pending=self.pending,None
        if 0x4E<=c<=0x5D: self.lcd[0][c-0x4E]=chr(x) if 32<=x<127 else '?'
        elif 0x5E<=c<=0x6D: self.lcd[1][c-0x5E]=chr(x) if 32<=x<127 else '?'
        else: self.regs[c]=x; self.log.append((c,x))
    def screen(self): return '|'+''.join(self.lcd[0])+'|\n|'+''.join(self.lcd[1])+'|'
    def send(self,*bs): self.s.send(bytes(bs))
    def press(self,id_,down=1,up=0,dt=0.05):
        self.send(id_,down); time.sleep(dt)
        if up is not None: self.send(id_,up); time.sleep(dt)
