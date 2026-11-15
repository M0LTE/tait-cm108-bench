# Multitone MER test. gen: write wav; tx: key + play; an: analyse a wav (card) or cf32 (RSP1).
import numpy as np, sys, wave, subprocess, time
FS = 48000; N = 2048; BINS = np.arange(9, 342, 4)   # tones every 4th bin of a 2048-point FFT, 211 Hz to 8 kHz
def gen(rms_dbfs, secs=6.0):
    rng = np.random.default_rng(1); ph = rng.uniform(0, 2*np.pi, len(BINS))
    t = np.arange(N)/FS; p = sum(np.cos(2*np.pi*b*FS/N*t + q) for b, q in zip(BINS, ph))
    p *= 10**(rms_dbfs/20)/np.sqrt(np.mean(p**2)); p = np.clip(p, -1, 1)
    x = np.tile(p, int(secs*FS/N))
    r = int(0.005*FS); x[:r] *= np.linspace(0, 1, r); x[-r:] *= np.linspace(1, 0, r)
    return x
def mer(sig, fs):
    # rectangular 2-period windows: tones land on bins 2*BINS, empty bins between them
    M = 2*N; segs = [sig[i:i+M] for i in range(0, len(sig)-M, M)]
    P = np.mean([np.abs(np.fft.rfft(s))**2 for s in segs], 0)
    out = []
    for b in BINS:
        tone = P[2*b]; empt = np.mean([P[2*b+j] for j in (-3, -2, -1, 1, 2, 3)])  # neighbours, all empty
        out.append((b*FS/N, 10*np.log10(tone/empt)))
    return out
if sys.argv[1] == 'tx':
    hid, card, lvl = sys.argv[2], sys.argv[3], float(sys.argv[4])
    x = gen(lvl)
    with wave.open('/tmp/mtone.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(FS); w.writeframes((x*32767).astype('<i2').tobytes())
    def ptt(on):
        with open(hid, 'wb', buffering=0) as f: f.write(bytes([0, 0, 0x04 if on else 0, 0x04, 0]))
    try:
        ptt(True); time.sleep(0.5); subprocess.run(['aplay', '-q', '-D', f'plughw:CARD={card},DEV=0', '/tmp/mtone.wav'], timeout=30); time.sleep(0.2)
    finally:
        ptt(False)
else:
    fn = sys.argv[2]
    if fn.endswith('.wav'):
        w = wave.open(fn); a = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float)/32768
        n = 480; r = np.array([np.sqrt(np.mean(a[i:i+n]**2)) for i in range(0, len(a)-n, n)])
        k = np.flatnonzero(20*np.log10(r+1e-9) < -40)[0]*n
        sig = a[k+int(1.0*FS):k+int(5.5*FS)]
    else:
        OFF, SF = 60e3, 192000
        x = np.fromfile(fn, dtype=np.complex64); t = np.arange(len(x))/SF
        y = x*np.exp(-2j*np.pi*OFF*t).astype(np.complex64); L = 255; k = np.arange(L)-(L-1)/2
        h = np.sinc(2*16000/SF*k)*np.blackman(L); h /= h.sum(); y = np.convolve(y, h, 'same')[::4]
        p = np.abs(y)**2; blk = FS//20; nb = len(p)//blk; pb = 10*np.log10(p[:nb*blk].reshape(nb, blk).mean(1)+1e-20)
        key = np.flatnonzero(pb > np.percentile(pb, 10)+15)[0]*blk
        d = np.angle(y[1:]*np.conj(y[:-1]))*FS/(2*np.pi); sig = d[key+int(1.0*FS):key+int(5.5*FS)]
    res = mer(sig, FS); v = np.array([m for _, m in res]); f = np.array([q for q, _ in res])
    bands = [(200, 1000), (1000, 2000), (2000, 3000), (3000, 4000), (4000, 5000), (5000, 6000), (6000, 7000), (7000, 8100)]
    print(fn.split('/')[-1], ' '.join(f"{lo//1000 if lo>=1000 else lo/1000:.1f}-{hi/1000:.0f}k:{np.median(v[(f>=lo)&(f<hi)]):5.1f}" for lo, hi in bands), f" worst {v.min():.1f} at {f[v.argmin()]:.0f} Hz")
