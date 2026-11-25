"""Build a bootable raw disk of the Neuron from Neotrope's Neuron80GB-OS15.tib.
Usage: python3 -I build_disk.py Neuron80GB-OS15.tib workdir
Needs: python3, e2fsprogs (debugfs), ~10 GB free (outputs are sparse)."""
import os, subprocess, sys, struct
tib, wd = sys.argv[1], sys.argv[2]; os.makedirs(wd, exist_ok=True)
here=os.path.dirname(os.path.abspath(__file__))
S=os.path.join(wd,'stream.bin'); I=os.path.join(wd,'stream.idx')
if not os.path.exists(S):
    subprocess.run([sys.executable,'-I',os.path.join(here,'tib_inflate.py'),tib,S,I],check=True)
# partition 1 (root, used-blocks-only) starts at stream offset 32508; partition 5 (/var, raw) at 237458960
p1=os.path.join(wd,'p1.img'); p5=os.path.join(wd,'p5.img')
subprocess.run([sys.executable,'-I',os.path.join(here,'rebuild_ext.py'),S,'32508',p1],check=True)
subprocess.run(['dd','if='+S,'of='+p5,'iflag=skip_bytes','skip=237458960','bs=4M','conv=sparse','status=none'],check=True)
m=open(S,'rb'); m.seek(4); mbr=m.read(512)
SEC=512; total=2120580+154175805
d=open(os.path.join(wd,'disk.raw'),'wb'); d.truncate(total*SEC); d.seek(0); d.write(mbr)
for name,lba in ((p1,1),(p5,2120581)):
    src=open(name,'rb'); d.seek(lba*SEC)
    while True:
        b=src.read(1<<22)
        if not b: break
        if b.count(0)==len(b): d.seek(len(b),1)
        else: d.write(b)
ebr=bytearray(512); ebr[446:462]=bytes([0,0,0,0,0x83,0,0,0])+struct.pack('<II',1,154175805-1); ebr[510:512]=b'\x55\xaa'
d.seek(2120580*SEC); d.write(ebr); d.close(); print('disk.raw ready in',wd)
