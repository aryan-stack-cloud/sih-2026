"""Deterministic restrained electronic underscore for the solution chapter."""
from pathlib import Path
import wave
import numpy as np

sr=24000
duration=119
t=np.arange(sr*duration,dtype=np.float64)/sr
sound=np.zeros_like(t)
chords=[(82.41,123.47,164.81),(87.31,130.81,174.61),(73.42,110.0,146.83),(82.41,123.47,164.81)]
for section in range(8):
    a=section*16; b=min(duration,(section+1)*16)
    sel=(t>=a)&(t<b)
    lt=t[sel]-a
    fade=np.minimum(1,np.minimum(lt/2,(b-t[sel])/2))
    chord=chords[section%len(chords)]
    pad=sum(np.sin(2*np.pi*f*t[sel]+0.08*np.sin(2*np.pi*.07*t[sel])) for f in chord)/3
    sub=np.sin(2*np.pi*(chord[0]/2)*t[sel])
    sound[sel]+=(.092*pad+.045*sub)*fade
for beat in np.arange(2,duration,1.0):
    pos=int(beat*sr); n=min(int(.17*sr),len(sound)-pos)
    if n<=0: continue
    tt=np.arange(n)/sr
    ping=(np.sin(2*np.pi*(550+350*np.exp(-tt*22))*tt)*np.exp(-tt*25))*.022
    sound[pos:pos+n]+=ping
sound*=np.minimum(1,t/1.5)*np.minimum(1,(duration-t)/3)
sound=np.tanh(sound*1.3)
pcm=np.int16(np.clip(sound,-1,1)*32767)
out=Path(__file__).parent/'assets'/'audio'/'score.wav'
out.parent.mkdir(parents=True,exist_ok=True)
with wave.open(str(out),'wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(pcm.tobytes())
print(out)

