import sys, wave, numpy as np
# lvl.py WAV START_HHMMSS.ss FROM_HHMMSS TO_HHMMSS : rms dBFS per 0.5 s
f, st, a, b = sys.argv[1:5]
def sec(x): h, m, s = x.split(':'); return int(h)*3600 + int(m)*60 + float(s)
w = wave.open(f); r = w.getframerate(); n = w.getnframes()
t0 = sec(st); s0 = max(0, int((sec(a)-t0)*r)); s1 = min(n, int((sec(b)-t0)*r))
w.setpos(s0); x = np.frombuffer(w.readframes(s1-s0), dtype=np.int16).astype(float)/32768
blk = r//2
out = []
for i in range(0, len(x)-blk+1, blk):
    v = 20*np.log10(np.sqrt(np.mean(x[i:i+blk]**2))+1e-9)
    t = t0 + (s0+i)/r
    out.append(f"{int(t//3600):02d}:{int(t%3600//60):02d}:{t%60:04.1f} {v:6.1f}")
print(f"{n/r:.1f} s total"); print("\n".join(out))
