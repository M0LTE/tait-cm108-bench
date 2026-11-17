# Receive-side analysis of the end-to-end tests. e2ean.py sweep|mtone|keyup <rx.wav> <out.json> [sched.json|ref.npy]
import numpy as np, wave, sys, json
kind, fn, out = sys.argv[1], sys.argv[2], sys.argv[3]
FS = 48000
w = wave.open(fn); a = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float)/32768
def rms_db(x, n): return 20*np.log10(np.array([np.sqrt(np.mean(x[i:i+n]**2)) for i in range(0, len(x)-n, n)])+1e-12)
def env(x, f, ms=10):
    t = np.arange(len(x))/FS; n = int(ms*FS/1000)
    return np.abs(np.convolve(x*np.exp(-2j*np.pi*f*t), np.ones(n)/n, 'same'))*2
def quiet_start(x):
    r = rms_db(x, 480); open_ = np.median(r[:30]); q = np.flatnonzero(r < open_-15)
    return q[0]*480 if len(q) else None
def amp_at(x, f):
    n = len(x); win = np.hanning(n); t = np.arange(n)/FS; best = 0
    span = max(0.3, f*3e-5)
    for ff in np.linspace(f-span, f+span, 25):
        best = max(best, abs(np.sum(x*win*np.exp(-2j*np.pi*ff*t)))*2/np.sum(win))
    return best
res = {}
if kind == 'sweep':
    sched = json.load(open(sys.argv[4])); q = quiet_start(a)
    e = env(a, 1000); seg = e[q:q+int(6*FS)]
    ref = q + np.flatnonzero(seg > 0.5*np.percentile(seg, 99))[0]
    tref = sched[0][2]; tcur = 0; rows = []; amps = []
    for k, f, d in sched:
        if k == 'tone':
            m = 0.15*d
            s = a[ref+int((tcur-tref+m)*FS): ref+int((tcur-tref+d-m)*FS)]
            A1 = amp_at(s, f); A2 = amp_at(s, 2*f) if 2*f < 20000 else 0; A3 = amp_at(s, 3*f) if 3*f < 20000 else 0
            amps.append((f, A1, A2, A3))
        tcur += d
    ns = a[q+int(0.3*FS):q+int(1.7*FS)]; N = 8192
    P = np.mean([np.abs(np.fft.rfft(ns[i:i+N]*np.hanning(N)))**2 for i in range(0, len(ns)-N, N//4)], 0)*2/np.sum(np.hanning(N)**2)/FS
    fP = np.fft.rfftfreq(N, 1/FS)
    r0 = amps[0][1]
    for f, A1, A2, A3 in amps[1:-1]:
        m = (fP > f*0.85) & (fP < f*1.15) | (np.abs(fP-f) < 8)
        rows.append(dict(f=f, rel_db=round(20*np.log10(A1/r0), 3), h2_dbc=round(20*np.log10(A2/A1+1e-9), 1) if A2 else None,
                         h3_dbc=round(20*np.log10(A3/A1+1e-9), 1) if A3 else None, noise_dbfs_hz=round(10*np.log10(P[m].mean()), 1)))
    res = dict(ref_1k_dbfs_rms=round(20*np.log10(r0/np.sqrt(2)), 2), drift_db=round(20*np.log10(amps[-1][1]/r0), 3), rows=rows)
elif kind == 'mtone':
    T = np.load(sys.argv[4]); N = 2048; k = np.arange(1, 513)
    q = quiet_start(a); r = rms_db(a[q:], 480); on = q + (np.flatnonzero(r > np.median(r[:20])+15)[0])*480
    s = a[on+int(0.5*FS):on+int(5.5*FS)]; acc = np.zeros(len(k), complex); cnt = 0; fit = (k >= 9) & (k <= 128)
    for i in range(0, len(s)-N, N):
        H = np.fft.rfft(s[i:i+N])[k]/T[k]; ph = np.unwrap(np.angle(H))
        p = np.polyfit(k[fit], ph[fit], 1); acc += H*np.exp(-1j*np.polyval(p, k)); cnt += 1
    H = acc/cnt; ph = np.unwrap(np.angle(H)); f = k*FS/N; i1k = np.argmin(abs(f-1000))
    mag = 20*np.log10(np.abs(H)/np.abs(H[i1k]))
    gd = -np.gradient(ph, 2*np.pi*f)*1e6                      # microseconds, relative to the 211 Hz to 3 kHz fit
    gd_s = np.convolve(gd, np.ones(3)/3, 'same')
    res = dict(windows=cnt, rows=[dict(f=round(float(ff), 1), mag_db=round(float(m), 2), phase_rad=round(float(p), 3), gd_us=round(float(g), 1))
                                  for ff, m, p, g in zip(f, mag, ph, gd_s)])
elif kind == 'keyup':
    hop = 48; n = 192
    X = [np.abs(np.fft.rfft(a[i:i+n]*np.hanning(n)))**2 for i in range(0, len(a)-n, hop)]
    fb = np.fft.rfftfreq(n, 1/FS); hb = (fb > 3000) & (fb < 10000)
    hf = 10*np.log10(np.array([x[hb].sum() for x in X])+1e-20); tt = np.arange(len(hf))*hop/FS + n/2/FS
    e = env(a, 1000, 2); et = e[(tt*FS).astype(int)]
    open_ = np.median(hf[:200]); keyed = np.flatnonzero(hf < open_-15)
    if not len(keyed): res = dict(error='carrier not seen')
    else:
        quiet = np.median(hf[keyed]); mid = (open_+quiet)/2
        c_on = tt[np.flatnonzero(hf < mid)[0]]; c_off = tt[np.flatnonzero(hf < mid)[-1]]
        steady = np.median(et[(tt > c_on+0.5) & (tt < c_off-0.5)])
        # modulation counts as present once the 1 kHz envelope sits within 1 dB of its settled level for 10 ms
        e4 = env(a, 1000, 4); ok = np.abs(20*np.log10(e4/steady+1e-12)) < 1.0
        run = int(0.010*FS); okr = np.convolve(ok.astype(float), np.ones(run), 'valid') >= run
        i0 = int((c_on-0.02)*FS); t_on = (i0 + np.flatnonzero(okr[i0:])[0])/FS
        i1 = int((c_off+0.02)*FS); t_off = (np.flatnonzero(okr[:i1])[-1] + run)/FS
        a10 = a90 = 0.0
        res = dict(carrier_to_modulation_ms=round((t_on-c_on)*1000, 1), modulation_end_to_carrier_drop_ms=round((c_off-t_off)*1000, 1),
                   keyed_ms=round((c_off-c_on)*1000, 1), open_noise_db=round(open_, 1), quieted_db=round(quiet, 1))
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'rows'}))
