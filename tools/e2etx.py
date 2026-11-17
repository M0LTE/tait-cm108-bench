# Transmit side of the end-to-end tests. Writes a stereo 48 kHz file and plays it on the raw hw device with PTT.
#   e2etx.py sweep|mtone|keyup <hidraw> <card>
# PTT is always dropped in finally. The schedule for 'sweep' is written to e2e-sweep.json.
import numpy as np, subprocess, sys, time, wave, json, threading
kind, hid, card = sys.argv[1], sys.argv[2], sys.argv[3]
FS = 48000
def ramp(x, ms=5):
    r = int(ms*FS/1000); x[:r] *= np.linspace(0, 1, r); x[-r:] *= np.linspace(1, 0, r); return x
def tone(f, d, a): t = np.arange(int(d*FS))/FS; return ramp(a*np.sin(2*np.pi*f*t))
A = 10**(-10/20)
if kind == 'sweep':
    freqs = [int(round(f)) for f in np.geomspace(10, 12000, 100)]
    sched = [("silence", 0, 2.0), ("tone", 1000, 1.0)] + [("tone", f, max(0.35, 12/f)) for f in freqs] + [("tone", 1000, 1.0), ("silence", 0, 0.3)]
    x = np.concatenate([tone(f, d, A) if k == "tone" else np.zeros(int(d*FS)) for k, f, d in sched])
    json.dump(sched, open('e2e-sweep.json', 'w'))
elif kind == 'mtone':
    N = 2048; k = np.arange(1, 513)                                   # 23.4 Hz to 12 kHz, every bin
    ph = -np.pi*k*(k-1)/len(k)                                         # Schroeder phases: low crest factor
    t = np.arange(N)/FS; p = sum(np.cos(2*np.pi*kk*FS/N*t + q) for kk, q in zip(k, ph))
    p *= 10**(-16/20)/np.sqrt(np.mean(p**2))
    np.save('e2e-mtone-ref.npy', np.fft.rfft(p)); x = np.concatenate([np.zeros(int(1.0*FS)), np.tile(p, int(6*FS/N))])
    x[int(1.0*FS):] = ramp(x[int(1.0*FS):])
elif kind == 'keyup':
    x = tone(1000, 8.0, A)
pk = np.abs(x).max(); assert pk < 1.0
st = np.stack([x, x], 1)
with wave.open('/tmp/e2e.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(FS); w.writeframes((st*32767).astype('<i2').tobytes())
def ptt(on):
    with open(hid, 'wb', buffering=0) as f: f.write(bytes([0, 0, 0x04 if on else 0, 0x04, 0]))
try:
    if kind == 'keyup':
        # the tone is already playing when PTT goes on and still playing when it goes off
        p = subprocess.Popen(['aplay', '-q', '-D', f'hw:CARD={card},DEV=0', '/tmp/e2e.wav'])
        time.sleep(2.0); ptt(True); time.sleep(3.0); ptt(False); p.wait(timeout=20)
    else:
        ptt(True); time.sleep(0.5)
        subprocess.run(['aplay', '-q', '-D', f'hw:CARD={card},DEV=0', '/tmp/e2e.wav'], timeout=120, check=True)
        time.sleep(0.2)
finally:
    ptt(False)
