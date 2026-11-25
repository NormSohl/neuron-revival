import numpy as np,sys
exec(open('ana2.py').read().split('src=load_aif')[0])
def env(x,w=44): return np.sqrt(np.convolve(x**2,np.ones(w)/w,'same'))
def bands(x,n=1024,hop=220):
    f=np.fft.rfftfreq(n,1/sr); edges=100*2**(np.arange(0,8.01,1/3)); B=[]
    for s in range(0,len(x)-n,hop):
        F=np.abs(np.fft.rfft(x[s:s+n]*np.hanning(n)))**2
        B.append([F[(f>=edges[i])&(f<edges[i+1])].sum() for i in range(len(edges)-1)])
    return 10*np.log10(np.array(B)+1e-12)
names=sys.argv[1:]
for s in names:
    src=load_aif(f'real/{s}.aif'); es=env(src); s0=int(np.argmax(es>0.05*es.max())); src=src[max(0,s0-220):]; es=env(src)
    L=min(len(src),int(0.6*sr)); ref=20*np.log10(es[:L]/es.max()+1e-9); Bs=bands(src[:L]); top=Bs.max()
    print(f'{s}:')
    for v in ('std','512'):
        x=load_raw(f'/tmp/N_{s}_{v}.raw'); e=env(x); t0=int(np.argmax(e>0.05*e.max()))-220
        best=None
        for lag in range(-1500,1500,4):
            a=t0+lag; seg=20*np.log10(e[a:a+L]/e[t0:t0+L+3000].max()+1e-9); m=ref>-45
            err=np.sqrt(np.mean((seg[m]-ref[m])**2))
            if best is None or err<best[0]: best=(err,lag)
        err,lag=best; xx=x[t0+lag:t0+lag+L]
        Bx=bands(xx); Bx+= (Bs.max()-Bx.max()); m=Bs>top-50
        spec=np.sqrt(np.mean((np.clip(Bx,top-60,None)[m]-np.clip(Bs,top-60,None)[m])**2))
        e40=lambda r: np.argmax(r[np.argmax(r):]<-30)/sr*1000
        print(f'   {v}: envelope err {err:5.2f} dB   spectro-temporal err {spec:5.2f} dB   t(-30dB) {e40(20*np.log10(env(xx)/env(xx).max()+1e-9)):6.1f} ms (src {e40(ref):6.1f})')
