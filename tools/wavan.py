#!/usr/bin/env python3
"""Analyse a recording of a radio's receive audio (48 kHz mono WAV from the CM108).
  wavan.py idle   FILE [SECONDS]   level of the first SECONDS (default 3): open channel if nothing was keyed yet
  wavan.py ladder FILE             received level, SINAD and harmonics for each step of gen.py's ladder
  wavan.py floor  FILE             noise spectrum under an unmodulated carrier (the quiet part after the receiver quiets)
"""
import sys, wave
import numpy as np
FS = 48000
LADDER = [-20, -14, -10, -6, -3, 0]
db = lambda v: 20 * np.log10(v + 1e-12)

def load(fn):
    w = wave.open(fn); return np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float) / 32768

def fit_tone(s, f):
    tt = np.arange(len(s)) / FS
    A = np.vstack([np.sin(2 * np.pi * f * tt), np.cos(2 * np.pi * f * tt), np.ones_like(tt)]).T
    c, *_ = np.linalg.lstsq(A, s, rcond=None); return np.hypot(c[0], c[1]), s - A @ c

def quieted(a):
    """Sample index where the far carrier first quiets the receiver."""
    n = 480; r = np.array([np.sqrt(np.mean(a[i:i + n] ** 2)) for i in range(0, len(a) - n, n)])
    return np.flatnonzero(db(r) < -40)[0] * n

def idle(fn, secs=3.0):
    s = load(fn)[:int(secs * FS)]
    print(f"first {secs:.0f} s: {db(np.std(s)):.1f} dBFS rms, peak {db(np.abs(s).max()):.1f} dBFS, 99.9% under {db(np.percentile(np.abs(s), 99.9)):.1f} dBFS")

def psd(s, N=8192):
    w = np.hanning(N); segs = [s[i:i + N] * w for i in range(0, len(s) - N, N // 4)]
    return np.fft.rfftfreq(N, 1 / FS), np.mean([np.abs(np.fft.rfft(g)) ** 2 for g in segs], 0) * 2 / np.sum(w ** 2) / FS

def floor(fn):
    a = load(fn); k = quieted(a); s = a[k + int(0.15 * FS):k + int(0.45 * FS)]
    f, P = psd(s, 4096)
    print(f"under carrier, {len(s) / FS:.2f} s: {db(np.std(s)):.1f} dBFS rms")
    for lo, hi in [(30, 100), (100, 300), (300, 1000), (1000, 3000), (3000, 5000), (5000, 8000), (8000, 12000)]:
        print(f"  {lo:5d}-{hi:5d} Hz  {10 * np.log10(np.mean(P[(f >= lo) & (f < hi)])):7.1f} dBFS/Hz")

def ladder(fn):
    a = load(fn); k = quieted(a)
    w = int(0.02 * FS); amps = [fit_tone(a[i:i + w], 1000)[0] for i in range(k, len(a) - w, w)]
    thr = 0.3 * np.percentile(amps[:100], 60) if False else 0.5 * 10 ** ((-55) / 20)
    start = k + next(i for i, v in enumerate(amps) if v > 0.001) * w
    prev = None
    for i, st in enumerate(LADDER):
        s = a[start + int((i * 2 + 0.4) * FS):][:int(1.2 * FS)]; n = int(0.1 * FS)
        pk = np.mean([fit_tone(s[j:j + n], 1000)[0] for j in range(0, len(s) - n + 1, n)])
        X = np.abs(np.fft.rfft(s * np.hanning(len(s)))) ** 2; f = np.fft.rfftfreq(len(s), 1 / FS)
        band = lambda lo, hi: X[(f >= lo) & (f < hi)].sum()
        sig = band(980, 1020); sinad = 10 * np.log10(sig / (band(300, 3000) - sig))
        h = lambda fr: 10 * np.log10(band(fr - 20, fr + 20) / sig)
        step = '' if prev is None else f"  step {db(pk / prev):5.2f} dB (sent {st - LADDER[i - 1]})"
        print(f"{st:4d} dBFS sent  received {db(pk / np.sqrt(2)):6.1f} dBFS rms  SINAD(0.3-3k) {sinad:4.1f} dB  H2 {h(2000):5.1f}  H3 {h(3000):5.1f} dBc{step}")
        prev = pk

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 2 else ''
    if cmd == 'idle': idle(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 3.0)
    elif cmd == 'ladder': ladder(sys.argv[2])
    elif cmd == 'floor': floor(sys.argv[2])
    else: sys.exit(__doc__)
