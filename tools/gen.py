#!/usr/bin/env python3
"""Write a 48 kHz mono test WAV.
  gen.py tone   OUT HZ DBFS SECONDS
  gen.py ladder OUT              1 kHz at -20 -14 -10 -6 -3 0 dBFS, 2 s each
  gen.py sweep  OUT DBFS         40 tones 30 Hz to 12 kHz, 1 kHz reference before and after; schedule in OUT.json
  gen.py mtone  OUT RMS_DBFS     84 tones 211 Hz to 8 kHz with empty bins between them, 6 s
"""
import json, sys, wave
import numpy as np
FS = 48000
LADDER = [-20, -14, -10, -6, -3, 0]
MT_N, MT_BINS = 2048, np.arange(9, 342, 4)

def ramp(x, secs=0.005):
    r = int(secs * FS); x[:r] *= np.linspace(0, 1, r); x[-r:] *= np.linspace(1, 0, r); return x

def tone(f, dbfs, secs):
    t = np.arange(int(FS * secs)) / FS
    return ramp(10 ** (dbfs / 20) * np.sin(2 * np.pi * f * t))

def write(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(FS)
        w.writeframes(np.round(np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())

def sweep_schedule():
    freqs = [int(f) for f in np.round(np.geomspace(30, 12000, 40))]
    return [["silence", 0, 2.0], ["tone", 1000, 1.0]] + [["tone", f, 0.6] for f in freqs] + [["tone", 1000, 1.0], ["silence", 0, 0.3]]

if __name__ == '__main__':
    kind, out = sys.argv[1], sys.argv[2]
    if kind == 'tone':
        x = tone(float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]))
    elif kind == 'ladder':
        x = np.concatenate([tone(1000, d, 2.0) for d in LADDER])
    elif kind == 'sweep':
        sched = sweep_schedule(); dbfs = float(sys.argv[3])
        x = np.concatenate([tone(f, dbfs, d) if k == 'tone' else np.zeros(int(FS * d)) for k, f, d in sched])
        json.dump(sched, open(out + '.json', 'w'))
    elif kind == 'mtone':
        rng = np.random.default_rng(1); ph = rng.uniform(0, 2 * np.pi, len(MT_BINS))
        t = np.arange(MT_N) / FS
        p = sum(np.cos(2 * np.pi * b * FS / MT_N * t + q) for b, q in zip(MT_BINS, ph))
        p *= 10 ** (float(sys.argv[3]) / 20) / np.sqrt(np.mean(p ** 2))
        x = ramp(np.tile(np.clip(p, -1, 1), int(6.0 * FS / MT_N)))
    else:
        sys.exit(__doc__)
    write(out, x)
