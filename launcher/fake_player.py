"""Stand-in for a sound card: reads S16_LE stereo 44.1 kHz from stdin at real-time speed, saves a WAV."""
import sys,time,wave
out=wave.open(sys.argv[1],'wb'); out.setnchannels(2); out.setsampwidth(4); out.setframerate(44100)
blk=441*8; t0=time.time(); n=0
try:
    while True:
        b=sys.stdin.buffer.read(blk)
        if not b: break
        out.writeframes(b); n+=len(b)//8
        d=t0+n/44100-time.time()
        if d>0: time.sleep(d)
finally: out.close()
