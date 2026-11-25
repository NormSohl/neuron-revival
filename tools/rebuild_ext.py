# Rebuild an ext2/3 partition stored as "used blocks only" (in block order) in a stream.
import struct, sys, mmap
src, base, dst = sys.argv[1], int(sys.argv[2]), sys.argv[3]
f=open(src,'rb'); m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
sb=m[base+1024:base+2048]
ic,bc,rb,fb,fi,first,logbs=struct.unpack('<7I',sb[:28]); bs=1024<<logbs
bpg,fpg,ipg=struct.unpack('<3I',sb[32:44])
ngroups=(bc-first+bpg-1)//bpg
print('blocks',bc,'bs',bs,'bpg',bpg,'groups',ngroups,'free',fb)
gdt_blk=first+1
def sblk(rank): return m[base+rank*bs:base+(rank+1)*bs]
gdt=sblk(gdt_blk)  # group 0 metadata is all used => rank==block
groups=[struct.unpack('<3I',gdt[32*g:32*g+12]) for g in range(ngroups)]
used_before=0; mapping=[]   # rank of first block of each group
bitmaps=[]
def skipped(g,gstart):  # backup sb/gdt blocks are not stored by the imager
    return set(range(gstart, groups[g][0])) if g>0 else set()
for g,(bb,ib,it) in enumerate(groups):
    gstart=first+g*bpg
    rank=used_before+(bb-gstart)-len(skipped(g,gstart))
    bm=sblk(rank)
    n=min(bpg,bc-gstart)
    bits=[(bm[i>>3]>>(i&7))&1 for i in range(n)]
    sk=skipped(g,gstart)
    for b in sk: bits[b-gstart]=0
    bitmaps.append(bits); used_before+=sum(bits)
total_used=used_before
print('used blocks',total_used,'expected',bc-fb, 'stream bytes',total_used*bs)
out=open(dst,'wb'); out.truncate(bc*bs)
rank=0
for g,bits in enumerate(bitmaps):
    gstart=first+g*bpg
    for i,b in enumerate(bits):
        if b:
            out.seek((gstart+i)*bs); out.write(sblk(rank)); rank+=1
for g in range(1,ngroups):
    gstart=first+g*bpg
    for k,b in enumerate(sorted(skipped(g,gstart))):
        out.seek(b*bs); out.write(sblk(k))   # copy primary sb / gdt as backups
if first==1: out.seek(0); out.write(m[base:base+1024])
print('done')
