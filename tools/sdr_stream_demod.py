#!/usr/bin/env python3
"""FM-demodulate an RSP1 IQ stream as it arrives, so a capture can run for as long as wanted without the IQ ever
touching the disk.
  rx_sdr -d driver=sdrplay -f 146440000 -s 192000 -g IFGR=50,RFGR=0 -F CF32 - | sdr_stream_demod.py CARRIER_HZ OUT.wav
CARRIER_HZ is where the wanted carrier sits above the tuned frequency (the tuning offset plus the RSP1's own
crystal error). OUT.wav is 48 kHz 16-bit, 20 kHz of deviation full scale. OUT.wav.json records the wall-clock time
of the first sample and, every ten seconds, how many samples had arrived, so a dropped block shows as a step."""
import sys, time, json, wave
import numpy as np
FS = 192000; DEC = 4
shift = float(sys.argv[1]); out = sys.argv[2]
taps = 129; k = np.arange(taps) - taps // 2
h = (np.sinc(2 * 16000 / FS * k) * 2 * 16000 / FS * np.hamming(taps)).astype(np.float32)
w = wave.open(out, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(FS // DEC)
tail = np.zeros(taps - 1, np.complex64); prev = np.complex64(1); n = 0; skip = 0; marks = []; t0 = None
block = FS
while True:
    raw = sys.stdin.buffer.read(block * 8)
    if len(raw) < 8: break
    x = np.frombuffer(raw[:len(raw) // 8 * 8], dtype=np.complex64)
    if t0 is None: t0 = time.time() - len(x) / FS
    ph = (-2 * np.pi * shift / FS) * (n + np.arange(len(x)))
    x = (x * np.exp(1j * ph)).astype(np.complex64)
    y = np.convolve(np.concatenate([tail, x]), h, "valid"); tail = x[-(taps - 1):] if len(x) >= taps - 1 else np.concatenate([tail, x])[-(taps - 1):]
    y = y[skip::DEC]; skip = (skip - len(x)) % DEC
    z = np.concatenate([[prev], y]); prev = y[-1] if len(y) else prev
    d = np.angle(z[1:] * np.conj(z[:-1])) * (FS / DEC) / (2 * np.pi)
    w.writeframes(np.clip(d / 20000 * 32767, -32767, 32767).astype("<i2").tobytes())
    n += len(x)
    if n // (10 * FS) > len(marks):
        marks.append([n, time.time()])
        json.dump({"t0": t0, "fs": FS // DEC, "shift": shift, "marks": marks}, open(out + ".json", "w"))
w.close()
json.dump({"t0": t0, "fs": FS // DEC, "shift": shift, "marks": marks, "samples_in": n}, open(out + ".json", "w"))
