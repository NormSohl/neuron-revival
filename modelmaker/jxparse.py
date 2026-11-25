import sys,re
d=open(sys.argv[1],'rb').read(); out=sys.argv[2]
mag=bytes((ord('J')+(i*3)//2) for i in range(15))
for m in re.finditer(re.escape(mag),d):
    o=m.start(); t=chr(d[o+15]); n=int.from_bytes(d[o+0x18:o+0x1c],'little')
    print(hex(o),t,n)
    raw=d[o+0x1c:o+0x1c+n]
    dec=bytes(((b^(i&0xff))+0x9c)&0xff for i,b in enumerate(raw))
    open(f'{out}/rec_{o:x}_{t}.bin','wb').write(dec); open(f'{out}/rec_{o:x}_{t}.raw','wb').write(raw)
