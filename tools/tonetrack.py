#!/usr/bin/env python3
"""Follow one tone in a recording of receive audio under a bare carrier, second by second.
  tonetrack.py FILE LO_HZ HI_HZ     prints the strongest tone between LO and HI for each second the receiver is quieted
(-- where it is not, ? where nothing stands 12 dB clear). The receive tone in these radios moves with temperature."""
import sys, wave, numpy as np
fn, lo, hi = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
w = wave.open(fn); a = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float) / 32768
FS = 48000; N = 48000; win = np.hanning(N); f = np.fft.rfftfreq(N, 1 / FS); m = (f >= lo) & (f <= hi); out = []
for i in range(0, len(a) - N + 1, N):
    P = np.abs(np.fft.rfft(a[i:i + N] * win)) ** 2 * 2 / np.sum(win ** 2) / FS
    band = 10 * np.log10(np.median(P[(f > 2000) & (f < 6000)]) + 1e-30)
    if not (-121 < band < -99): out.append("  --"); continue
    k = np.flatnonzero(m)[np.argmax(P[m])]
    out.append(f"{f[k]:.0f}" if 10 * np.log10(P[k] / np.median(P[m])) > 12 else "   ?")
print(" ".join(out))
