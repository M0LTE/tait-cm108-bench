# Write ONE CM108B EEPROM word after checking its current value, then read it back.
import os, select, sys, time
dev, addr, expect, new = sys.argv[1], int(sys.argv[2],16), int(sys.argv[3],16), int(sys.argv[4],16)
fd = os.open(dev, os.O_RDWR)
def drain():
    while select.select([fd], [], [], 0.02)[0]: os.read(fd, 64)
def rd(a):
    drain(); os.write(fd, bytes([0, 0x80, 0, 0, 0x80 | a]))
    if not select.select([fd], [], [], 0.5)[0]: return None
    b = os.read(fd, 64); return b[1] | (b[2] << 8)
cur = rd(addr)
if cur != expect:
    print(f"refusing: word {addr:02X} is {cur} not {expect:04X}"); sys.exit(2)
drain(); os.write(fd, bytes([0, 0x80, new & 0xFF, new >> 8, 0xC0 | addr])); time.sleep(0.1)
back = rd(addr)
os.write(fd, bytes([0, 0, 0, 0x04, 0]))   # back to GPIO mode, PTT low
os.close(fd)
print(f"word {addr:02X}: {cur:04X} -> wrote {new:04X}, reads back {back:04X}")
