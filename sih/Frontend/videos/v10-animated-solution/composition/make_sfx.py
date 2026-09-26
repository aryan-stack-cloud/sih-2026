"""Deterministic, restrained scan and transition sounds for v10."""
from pathlib import Path
import numpy as np
import wave

sr=24000
duration=119
mix=np.zeros(sr*duration,dtype=np.float64)

def add(start,signal):
    p=int(start*sr)
    if p>=len(mix): return
    n=min(len(signal),len(mix)-p)
    mix[p:p+n]+=signal[:n]

def thump(at):
    t=np.arange(int(.46*sr))/sr
    f=62+95*np.exp(-t*19)
    sound=np.sin(2*np.pi*f*t)*np.exp(-t*11)
    add(at,.12*sound)

def chirp(at,high=True):
    t=np.arange(int(.28*sr))/sr
    start,end=(660,1040) if high else (580,280)
    phase=2*np.pi*(start*t+(end-start)/(2*.28)*t*t)
    sound=np.sin(phase)*np.sin(np.pi*np.minimum(t/.28,1))**2
    add(at,.055*sound)

for at in [0,8,24,34,45,57,67,77,89,101,110]: thump(at+.05)
for at in [2.3,26.2,28.6,31.0]: chirp(at,False)
for at in [10.1,13.2,16.3,35.2,37.4,39.6,41.8,50.0,83.0,94.2]: chirp(at,True)
mix=np.tanh(mix)
pcm=np.int16(np.clip(mix,-1,1)*32767)
out=Path(__file__).parent/'assets'/'audio'/'sfx.wav'
with wave.open(str(out),'wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(pcm.tobytes())
print(out)
