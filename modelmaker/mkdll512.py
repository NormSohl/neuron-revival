# Patch MODELmaker 1.2 NASAnalysis.dll for true 512-sample analysis frames.
# usage: python3 mkdll512.py NASAnalysis.dll NASAnalysis_512.dll   (then set sphere +0x3c = 1)
import sys,struct,pefile
p=pefile.PE(sys.argv[1]); b=p.OPTIONAL_HEADER.ImageBase; d=bytearray(p.__data__)
off=lambda va: p.get_offset_from_rva(va-b)
o=off(0x1001353c); assert d[o:o+4]==b'\0'*4; d[o:o+4]=struct.pack('<f',512.0)        # new constant in .rdata slack
for va in (0x10003a04,0x10003c10,0x10003ca2):                                          # frame count + loop points: /1024 -> /512
    o=off(va); assert d[o:o+6]==bytes.fromhex('d835ac5c0110'); d[o+2:o+6]=struct.pack('<I',0x1001353c)
o=off(0x1000a3f5)                                                                      # hop = window/2 -> window/4 (1024 -> 512 samples per call)
assert d[o:o+27]==bytes.fromhex('898424044300003d00000080839c2404430000ffd1bc2404430000')
d[o:o+27]=bytes.fromhex('c1f80289842404430000')+b'\x90'*17
open(sys.argv[2],'wb').write(d)
