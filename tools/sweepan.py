# Analyse a sweep run: transmit deviation response (RSP1), receive audio response and noise floor (card).
import numpy as np, wave, json, sys
tag = sys.argv[1]; base = '/home/pi/tait-pair/'
sched = json.load(open(base + 'sweep-schedule.json'))
OFF, FS = 60e3, 192000
def tone_amp(s, fs, f):
    n = len(s); w = np.hanning(n); t = np.arange(n)/fs
    best = 0
    for ff in np.arange(f*(1-0.0008), f*(1+0.0008)+0.05, max(0.05, f*0.00004)):
        v = abs(np.sum(s*w*np.exp(-2j*np.pi*ff*t)))*2/np.sum(w); best = max(best, v)
    return best
def onset(sig, fs, start):
    t = np.arange(len(sig))/fs; z = sig*np.exp(-2j*np.pi*1000*t); n = int(0.01*fs)
    env = np.abs(np.convolve(z, np.ones(n)/n, 'same'))
    seg = env[start:start+int(8*fs)]; thr = 0.5*np.percentile(seg, 99)
    return start + np.flatnonzero(seg > thr)[0]
def measure(sig, fs, t1k):
    # schedule time of the reference tone start
    tref = sched[0][2]; out = []; tcur = 0
    for kind, f, d in sched:
        if kind == 'tone':
            a = t1k + int((tcur - tref + 0.1)*fs); b = t1k + int((tcur - tref + d - 0.1)*fs)
            out.append((f, tone_amp(sig[a:b], fs, f)))
        tcur += d
    return out
# --- transmit deviation via RSP1
x = np.fromfile(base + f'sw-{tag}.cf32', dtype=np.complex64); t = np.arange(len(x))/FS
y = x*np.exp(-2j*np.pi*OFF*t).astype(np.complex64)
L = 255; k = np.arange(L)-(L-1)/2; h = np.sinc(2*16000/FS*k)*np.blackman(L); h /= h.sum()
y = np.convolve(y, h, 'same')[::4]; fs = FS//4
p = np.abs(y)**2; blk = fs//20; nb = len(p)//blk; pb = 10*np.log10(p[:nb*blk].reshape(nb, blk).mean(1)+1e-20)
on = np.flatnonzero(pb > np.percentile(pb, 10)+15); key = on[0]*blk
d = np.angle(y[1:]*np.conj(y[:-1]))*fs/(2*np.pi); d -= np.median(d[key+int(0.6*fs):key+int(2.0*fs)])
tx = measure(d, fs, onset(d, fs, key+int(1.0*fs)))
# --- receive audio
w = wave.open(base + f'sw-{tag}.wav'); a = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float)/32768
rkey = None
n = 480; r = np.array([np.sqrt(np.mean(a[i:i+n]**2)) for i in range(0, len(a)-n, n)])
rkey = np.flatnonzero(20*np.log10(r+1e-9) < -40)[0]*n          # carrier quiets the receiver
rx = measure(a, 48000, onset(a, 48000, rkey+int(1.0*48000)))
# noise floor under unmodulated carrier: PSD over the silence segment
ns = a[rkey+int(0.3*48000):rkey+int(1.6*48000)]; N = 8192
segs = [ns[i:i+N]*np.hanning(N) for i in range(0, len(ns)-N, N//4)]
P = np.mean([np.abs(np.fft.rfft(g))**2 for g in segs], 0)*2/np.sum(np.hanning(N)**2)/48000; fP = np.fft.rfftfreq(N, 1/48000)
ref_tx = tx[0][1]; ref_rx = rx[0][1]
print(f"{tag}: 1 kHz reference: {ref_tx:.0f} Hz peak deviation, received {20*np.log10(ref_rx/np.sqrt(2)):.1f} dBFS rms")
print(f"{'Hz':>6} {'tx dev dB':>9} {'rx audio dB':>11} {'rx path dB':>10} {'noise dBFS/Hz':>13} {'tone-noise in 100 Hz':>20}")
rows = []
for (f, dv), (_, ra) in zip(tx[1:-1], rx[1:-1]):
    txdb = 20*np.log10(dv/ref_tx); rxdb = 20*np.log10(ra/ref_rx); m = (fP > f*0.9) & (fP < f*1.1)
    nd = 10*np.log10(np.mean(P[m])); snr = 20*np.log10(ra/np.sqrt(2)) - (nd + 20)
    rows.append(dict(f=int(f), tx_db=round(txdb, 2), rx_audio_db=round(rxdb, 2), rx_path_db=round(rxdb-txdb, 2), noise_dbfs_hz=round(nd, 1), snr_100hz=round(snr, 1)))
    print(f"{f:6d} {txdb:9.2f} {rxdb:11.2f} {rxdb-txdb:10.2f} {nd:13.1f} {snr:20.1f}")
print(f"drift check, final 1 kHz vs first: tx {20*np.log10(tx[-1][1]/ref_tx):+.2f} dB, rx {20*np.log10(rx[-1][1]/ref_rx):+.2f} dB")
json.dump(dict(tag=tag, ref_dev_hz=ref_tx, ref_rx_dbfs=20*np.log10(ref_rx/np.sqrt(2)), rows=rows), open(base + f'sw-{tag}.json', 'w'), indent=1)
