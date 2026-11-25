import sys,numpy as np,struct,math,wave
from scipy.signal import resample_poly
from fractions import Fraction
def read_wav(fn):
    d=open(fn,'rb').read(); p=12; fmt=None
    while p<len(d):
        cid=d[p:p+4]; n=struct.unpack('<I',d[p+4:p+8])[0]; body=d[p+8:p+8+n]
        if cid==b'fmt ': tag,ch,sr,_,_,bits=struct.unpack('<HHIIHH',body[:16]); fmt=(tag,ch,sr,bits)
        if cid==b'data': data=body
        p+=8+n+(n&1)
    tag,ch,sr,bits=fmt
    if bits==24:
        a=np.frombuffer(data[:len(data)//3*3],dtype=np.uint8).reshape(-1,3); x=(a[:,0].astype(np.int32)|(a[:,1].astype(np.int32)<<8)|(a[:,2].astype(np.int32)<<16)); x=np.where(x>=1<<23,x-(1<<24),x)/2**23
    elif bits==16: x=np.frombuffer(data,dtype='<i2')/32768
    elif bits==32 and tag==3: x=np.frombuffer(data,dtype='<f4').astype(float)
    else: x=np.frombuffer(data,dtype='<i4')/2**31
    return x.reshape(-1,ch).mean(1),sr,fmt
def ext80(x):
    e=int(math.floor(math.log2(x))); m=int(x/2**e*2**63); return struct.pack('>HQ',e+16383,m)
x,sr,fmt=read_wav(sys.argv[1])
if sr!=44100: fr=Fraction(44100,sr); x=resample_poly(x,fr.numerator,fr.denominator)
# trim leading silence, keep 5 ms pre-roll; trim tail below -70 dB
e=np.abs(x); th=e.max()*10**(-50/20); s0=max(0,int(np.argmax(e>th))-220); last=len(x)-int(np.argmax(e[::-1]>e.max()*10**(-70/20)))
x=x[s0:last]; x=x/np.abs(x).max()*0.92
s=np.round(x*32767).astype('>i2'); data=s.tobytes(); N=len(s)
comm=struct.pack('>hIh',1,N,16)+ext80(44100); ssnd=struct.pack('>II',0,0)+data
body=b'AIFF'+b'COMM'+struct.pack('>I',len(comm))+comm+b'SSND'+struct.pack('>I',len(ssnd))+ssnd
open(sys.argv[2],'wb').write(b'FORM'+struct.pack('>I',len(body))+body)
print(sys.argv[2],fmt,f'{N/44100:.2f}s')
