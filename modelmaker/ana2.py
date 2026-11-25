import numpy as np,sys
sr=44100
def load_raw(fn):
    a=np.fromfile(fn,dtype='<i4'); a=a[:len(a)//10*10].reshape(-1,10); return a[:,0]/2**31
def load_aif(fn):
    d=open(fn,'rb').read(); i=d.index(b'SSND'); return np.frombuffer(d[i+16:],dtype='>i2')/32768
def onset(x,th):
    e=np.convolve(np.abs(x),np.ones(64)/64,'same'); return int(np.argmax(e>th*e.max()))
def harm(x,t0,f0,ts=(0.02,0.1,0.3,0.6,1.0,1.4,1.8)):
    rows=[]
    for t in ts:
        s=t0+int(t*sr); n=4096; seg=x[s:s+n]*np.hanning(n); F=np.abs(np.fft.rfft(seg,8*n)); f=np.fft.rfftfreq(8*n,1/sr)
        r=[]
        for h in range(1,13):
            m=(f>h*f0*0.97)&(f<h*f0*1.03); r.append(20*np.log10(F[m].max()+1e-12))
        rows.append(r)
    return np.array(rows)
src=load_aif('peload/pluck220.aif'); 
res={'src':(src,0)}
for nm in sys.argv[1:]:
    x=load_raw(f'/tmp/{nm}.raw'); res[nm]=(x,onset(x,0.05))
ref=None
for nm,(x,t0) in res.items():
    H=harm(x,t0,220.0); H-=H[0,0]
    # broadband envelope dB at times
    e=np.sqrt(np.convolve(x**2,np.ones(441)/441,'same'))
    pk=e[t0:t0+sr//5].max()
    env=[20*np.log10(e[t0+int(t*sr)]/pk+1e-9) for t in (0.01,0.05,0.1,0.3,0.6,1.0,1.4,1.8)]
    att=(np.argmax(e[t0:]>0.9*pk))/sr*1000
    print(f'{nm:7s} attack-to-90% {att:5.1f} ms   env dB @ .01 .05 .1 .3 .6 1 1.4 1.8s:',' '.join(f'{v:6.1f}' for v in env))
    print('        harmonic dB rel h1@20ms (rows t=.02,.1,.3,.6,1,1.4,1.8; cols h1..h12)')
    for r in H: print('        ',' '.join(f'{v:6.1f}' for v in r))
