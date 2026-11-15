# Send N AX.25 UI frames of a given size into one KISS port; count byte-identical arrivals on another.
import socket, sys, time, os, select, json
def ep(a):
    h, _, p = a.rpartition(':'); return (h or '127.0.0.1', int(p))
txport, rxport, n, size = ep(sys.argv[1]), ep(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
wait = float(sys.argv[5]) if len(sys.argv) > 5 else 60
FEND, FESC, TFEND, TFESC = 0xC0, 0xDB, 0xDC, 0xDD
def addr(call, ssid, last):
    c = call.ljust(6).encode()
    return bytes(b << 1 for b in c) + bytes([0x60 | (ssid << 1) | (1 if last else 0)])
def esc(b): return b.replace(b'\xdb', b'\xdb\xdd').replace(b'\xc0', b'\xdb\xdc')
def unesc(b): return b.replace(b'\xdb\xdc', b'\xc0').replace(b'\xdb\xdd', b'\xdb')
hdr = addr('M0LTE', 2, False) + addr('M0LTE', 1, True) + b'\x03\xf0'
run = os.urandom(3).hex()
frames = []
for i in range(n):
    tag = f'{run}:{i:04d}:'.encode()
    body = (tag + os.urandom(size)).ljust(size, b'x')[:size]  # payload size bytes
    frames.append(hdr + body)
rx = socket.create_connection(rxport); tx = socket.create_connection(txport)
TXDELAY, P, SLOT, TAIL = 5, 255, 1, 5   # 50 ms, p=255, 10 ms, 50 ms
for sock in (tx, rx):
    for cmd, val in ((1, TXDELAY), (2, P), (3, SLOT), (4, TAIL), (5, 0)):
        sock.sendall(bytes([FEND, cmd, val, FEND]))
time.sleep(0.5)
t0 = time.time()
for f in frames: tx.sendall(bytes([FEND, 0x00]) + esc(f) + bytes([FEND]))
want = {f: i for i, f in enumerate(frames)}; got = {}; buf = b''; last = t0
deadline = t0 + wait
while time.time() < deadline and len(got) < n:
    r, _, _ = select.select([rx], [], [], 0.5)
    if not r: continue
    buf += rx.recv(65536)
    while True:
        a = buf.find(b'\xc0')
        if a < 0: buf = b''; break
        b = buf.find(b'\xc0', a + 1)
        if b < 0: buf = buf[a:]; break
        pkt = unesc(buf[a+1:b]); buf = buf[b:]
        if len(pkt) > 1 and pkt[0] & 0x0F == 0:
            f = pkt[1:]
            if f in want and want[f] not in got: got[want[f]] = time.time(); last = time.time()
dt = last - t0
bits = sum(len(frames[i]) for i in got) * 8
print(json.dumps({"tx": f"{txport[0]}:{txport[1]}", "rx": f"{rxport[0]}:{rxport[1]}", "size": size, "sent": n, "delivered": len(got),
                  "seconds": round(dt, 2), "goodput_kbps": round(bits / dt / 1000, 2) if got else 0}))
