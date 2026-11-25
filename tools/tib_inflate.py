import zlib, sys, mmap, re
src, dst, idx = sys.argv[1:4]
f=open(src,'rb'); m=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
out=open(dst,'wb'); ix=open(idx,'w')
p=0; n=0; outpos=0; gaps=0; N=len(m)
pat=re.compile(rb'\x78[\x01\x5e\x9c\xda]')
while p<N:
    mm=pat.search(m,p)
    if not mm: break
    s=mm.start()
    d=zlib.decompressobj()
    try:
        o=d.decompress(m[s:s+2_000_000])
    except zlib.error:
        p=s+1; continue
    if not d.eof or len(o)<512:
        p=s+1; continue
    clen=2_000_000-len(d.unused_data) if len(m[s:s+2_000_000])==2_000_000 else len(m[s:s+2_000_000])-len(d.unused_data)
    if s-p>64: gaps+=1
    ix.write(f"{s} {clen} {outpos} {len(o)} {s-p}\n")
    (out.seek(len(o),1) if o.count(0)==len(o) else out.write(o)); outpos+=len(o); n+=1; p=s+clen
    if n%2000==0: print(n, s, outpos, file=sys.stderr, flush=True)
out.truncate(outpos)
print("chunks",n,"out",outpos,"bigGaps",gaps,"tail",N-p, file=sys.stderr)
