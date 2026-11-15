#!/usr/bin/env python3
"""Sample-clock error and wander from one steady 1 kHz transmission (gen.py tone ... 1000 -3 12).
  clock.py IQ.cf32 RX.wav
The RSP1 capture gives the sending card's playback clock; the receiving card's audio carries playback and capture
together, so capture is the difference. Rates in ppm against the RSP1; wander is the worst peak-to-peak timing
excursion in any 1.5 s window after taking out that window's own average rate (what a per-burst rate correction leaves).
"""
import sys, wave
import numpy as np
F = 1000.0

def track(sig, fs, lo):
    """Phase of the 1 kHz tone every 10 ms over the steady part: times (s from tone start) and phase (rad)."""
    t = np.arange(len(sig)) / fs; z = sig * np.exp(-2j * np.pi * F * t); n = int(fs * 0.01)
    z = z[:len(z) // n * n].reshape(-1, n).mean(1); a = np.abs(z)
    on = np.flatnonzero(a > lo * np.percentile(a, 95)); i0, i1 = on[0] + 100, on[-1] - 50   # 1 s in, 0.5 s before the end
    return (np.arange(i0, i1) - on[0]) * 0.01, np.unwrap(np.angle(z[i0:i1]))

def stats(tt, ph):
    p = np.polyfit(tt, ph, 1); W = 150; worst = 0
    for i in range(0, len(ph) - W, 25):
        q = np.polyfit(tt[i:i + W], ph[i:i + W], 1); worst = max(worst, np.ptp(ph[i:i + W] - np.polyval(q, tt[i:i + W])))
    return p[0] / (2 * np.pi * F) * 1e6, np.std(ph - np.polyval(p, tt)), worst / (2 * np.pi * F) * 1e6

iqf, wavf = sys.argv[1:3]
FS, OFF, DEC = 192000, 60e3, 4; fs = FS // DEC
x = np.fromfile(iqf, dtype=np.complex64); t = np.arange(len(x)) / FS
k = np.arange(255) - 127; h = np.sinc(2 * 8000 / FS * k) * np.blackman(255); h /= h.sum()
y = np.convolve(x * np.exp(-2j * np.pi * OFF * t).astype(np.complex64), h, 'same')[::DEC]
d = np.angle(y[1:] * np.conj(y[:-1])) * fs / (2 * np.pi)
p = np.abs(y) ** 2; blk = fs // 20; pb = p[:len(p) // blk * blk].reshape(-1, blk).mean(1); on = np.flatnonzero(pb > 10 * np.percentile(pb, 5))
d = d[on[0] * blk:on[-1] * blk]                                    # keyed part only: noise outside it would swamp the tone search
w = wave.open(wavf); a = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float) / 32768
r = np.sqrt((a[:len(a) // 480 * 480].reshape(-1, 480) ** 2).mean(1)); q = np.flatnonzero(r < 10 ** (-24 / 20))   # carrier up: quieter than open channel
a = a[q[0] * 480:q[-1] * 480]
t1, p1 = track(d, fs, 0.5); t2, p2 = track(a, 48000, 0.5)
n = min(len(p1), len(p2)); t1, p1, p2 = t1[:n], p1[:n], p2[:n]
dac = stats(t1, p1); both = stats(t1, p2); adc = stats(t1, p1 - p2)   # received tone = sent rate / capture rate
us = lambda v: f"{v:5.1f} us ({v * 1e-6 * 2 * np.pi * 8000:.1f} rad at 8 kHz)"
print(f"{n / 100:.1f} s of tone")
if len(sys.argv) > 3:   # timing residual every 0.25 s, microseconds: playback | capture
    for nm, ph in (("playback", p1), ("capture ", p1 - p2)):
        r_ = ph - np.polyval(np.polyfit(t1, ph, 1), t1); print(nm, ' '.join(f"{v / (2 * np.pi * F) * 1e6:+.0f}" for v in r_[::25]))
print(f"playback (sending card):  {dac[0]:+7.1f} ppm, wander in 1.5 s {us(dac[2])}")
print(f"capture (receiving card): {adc[0]:+7.1f} ppm, wander in 1.5 s {us(adc[2])}")
print(f"end to end:               {both[0]:+7.1f} ppm, wander in 1.5 s {us(both[2])}")
