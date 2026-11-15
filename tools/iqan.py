#!/usr/bin/env python3
"""Analyse an RSP1 capture (CF32, 192 kHz, tuned 60 kHz below the channel) of one of the radios.
  iqan.py ladder FILE          deviation of each step of gen.py's ladder, by FM demodulation
  iqan.py bessel FILE [HZ]     deviation of a steady tone from its sideband amplitudes (no demodulator involved)
  iqan.py burst  FILE          rms and peak deviation of each keyed, modulated burst (for modem transmissions)
"""
import sys
import numpy as np
OFF, FS, DEC = 60e3, 192000, 4
fs = FS // DEC
LADDER = [-20, -14, -10, -6, -3, 0]

def lowpass(x, cutoff, rate, taps=255):
    k = np.arange(taps) - (taps - 1) / 2; h = np.sinc(2 * cutoff / rate * k) * np.blackman(taps); h /= h.sum()
    return np.convolve(x, h, 'same')

def load(fn, half_bw):
    """Channel at complex baseband, 48 kHz, low-passed to +/- half_bw; plus 50 ms power blocks and the keyed blocks."""
    x = np.fromfile(fn, dtype=np.complex64); t = np.arange(len(x)) / FS
    y = lowpass(x * np.exp(-2j * np.pi * OFF * t).astype(np.complex64), half_bw, FS)[::DEC]
    p = np.abs(y) ** 2; blk = fs // 20; nb = len(p) // blk
    pb = 10 * np.log10(p[:nb * blk].reshape(nb, blk).mean(1) + 1e-20)
    floor = np.percentile(pb, 5); on = pb > floor + 10
    return y, pb, on, blk, floor

def demod(y):
    return np.angle(y[1:] * np.conj(y[:-1])) * fs / (2 * np.pi)

def fit_tone(s, f):
    tt = np.arange(len(s)) / fs
    A = np.vstack([np.sin(2 * np.pi * f * tt), np.cos(2 * np.pi * f * tt), np.ones_like(tt)]).T
    c, *_ = np.linalg.lstsq(A, s, rcond=None); return np.hypot(c[0], c[1]), s - A @ c

def bessel_j(n, x):
    tau = np.linspace(0, np.pi, 4001); return np.trapezoid(np.cos(n * tau - x * np.sin(tau)), tau) / np.pi

def runs(mask):
    out, st = [], None
    for i, v in enumerate(mask):
        if v and st is None: st = i
        if not v and st is not None: out.append((st, i)); st = None
    if st is not None: out.append((st, len(mask)))
    return out

def ladder(fn):
    y, pb, on, blk, floor = load(fn, 9000); idx = np.flatnonzero(on); ks, ke = idx[0] * blk, idx[-1] * blk
    fi = demod(y); d = fi - np.median(fi[ks + int(0.1 * fs):ks + int(0.4 * fs)])
    w = int(0.02 * fs); amps = [fit_tone(d[i:i + w], 1000)[0] for i in range(ks, ke, w)]
    start = ks + next(i for i, a in enumerate(amps) if a > 100 and i * w / fs > 0.3) * w
    print(f"in-channel SNR {np.median(pb[on]) - floor:.1f} dB")
    prev = None
    for i, st in enumerate(LADDER):
        s = d[start + int((i * 2 + 0.4) * fs):][:int(1.2 * fs)]; n = int(0.1 * fs)
        sl = [fit_tone(s[j:j + n], 1000) for j in range(0, len(s) - n + 1, n)]
        pk = np.mean([q[0] for q in sl]); res = np.concatenate([q[1] for q in sl])
        X = np.abs(np.fft.rfft(s * np.hanning(len(s)))); f = np.fft.rfftfreq(len(s), 1 / fs)
        lv = lambda fr: np.sqrt((X[(f > fr - 20) & (f < fr + 20)] ** 2).sum())
        thd = 20 * np.log10(np.hypot(lv(2000), lv(3000)) / lv(1000))
        step = '' if prev is None else f"  step {20 * np.log10(pk / prev):5.2f} dB (sent {st - LADDER[i - 1]})"
        print(f"{st:4d} dBFS  {pk / 1000:6.3f} kHz peak  residual {np.std(res):4.0f} Hz rms  H2+H3 {thd:5.1f} dBc{step}")
        prev = pk

def bessel(fn, ftone=1000.0):
    y, pb, on, blk, floor = load(fn, 20000); idx = np.flatnonzero(on); ks, ke = idx[0] * blk, idx[-1] * blk
    seg = y[ks + int(1.5 * fs):ke - int(0.7 * fs)]; fi = demod(seg)
    fc = np.mean(fi); n = int(0.1 * fs); pk_demod = np.mean([fit_tone(fi[j:j + n] - fc, ftone)[0] for j in range(0, len(fi) - n, n)])
    N = len(seg); X = np.abs(np.fft.fft(seg * np.hanning(N))) ** 2; f = np.fft.fftfreq(N, 1 / fs)
    ks_ = np.arange(-6, 7)
    P = np.array([X[np.abs(f - (fc + k * ftone)) < 25].sum() for k in ks_]); a = np.sqrt(P / P.sum())
    betas = np.arange(0.05, 8, 0.001); best = None
    for b in betas:
        j = np.abs([bessel_j(abs(int(k)), b) for k in ks_]); j /= np.sqrt((j ** 2).sum())
        e = ((a - j) ** 2).sum()
        if best is None or e < best[0]: best = (e, b)
    print(f"{len(seg) / fs:.1f} s of tone at {ftone:.0f} Hz, carrier {fc:+.0f} Hz")
    print(f"sideband fit: modulation index {best[1]:.3f} -> {best[1] * ftone / 1000:.3f} kHz peak (fit error {np.sqrt(best[0]):.4f})")
    print(f"demodulator:  {pk_demod / 1000:.3f} kHz peak")
    print("line amplitudes, carrier and +/-1..6: " + ' '.join(f"{v:.3f}" for v in a[6:]) + " | " + ' '.join(f"{v:.3f}" for v in a[5::-1]))

def burst(fn):
    y, pb, on, blk, floor = load(fn, 20000)
    fi = lowpass(demod(y), 9000, fs)
    print(f"in-channel SNR {np.median(pb[on]) - floor:.1f} dB; deviation low-passed at 9 kHz after demodulation")
    allr = []
    for a, b in runs(on):
        if b - a < 6: continue
        s = fi[a * blk + int(0.05 * fs):b * blk - int(0.05 * fs)]
        w = int(0.01 * fs); r = np.array([np.std(s[i:i + w]) for i in range(0, len(s) - w, w)])
        mod = np.flatnonzero(r > 300)   # an unmodulated carrier reads 50 to 150 Hz rms here
        if len(mod) < 5: print(f"  keyed {(b - a) * 0.05:5.2f} s, no modulation ({np.median(r):.0f} Hz rms)"); continue
        m = s[mod[0] * w:(mod[-1] + 1) * w]; m = m - np.mean(m)
        rms, pk, p999 = np.std(m), np.abs(m).max(), np.percentile(np.abs(m), 99.9)
        allr.append((rms, pk, p999))
        print(f"  keyed {(b - a) * 0.05:5.2f} s, modulated {len(m) / fs:5.2f} s: {rms:5.0f} Hz rms, peak {pk:5.0f} Hz, 99.9% under {p999:5.0f} Hz, crest {20 * np.log10(pk / rms):4.1f} dB")
    if allr:
        r = np.array(allr); print(f"{len(r)} bursts: median {np.median(r[:, 0]):.0f} Hz rms, median peak {np.median(r[:, 1]):.0f} Hz, highest peak {r[:, 1].max():.0f} Hz")

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 2 else ''
    if cmd == 'ladder': ladder(sys.argv[2])
    elif cmd == 'bessel': bessel(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1000.0)
    elif cmd == 'burst': burst(sys.argv[2])
    else: sys.exit(__doc__)
