# CM108B EEPROM dump over hidraw (read only). Access as in AllStar chan_usbradio:
# out report [0x80, d0, d1, 0x80|addr] = read; input report bytes 1,2 = data.
import os, select, sys, time
dev = sys.argv[1]
fd = os.open(dev, os.O_RDWR)
def drain():
    while select.select([fd], [], [], 0.02)[0]: os.read(fd, 64)
def read_word(addr):
    drain()
    os.write(fd, bytes([0x00, 0x80, 0x00, 0x00, 0x80 | (addr & 0x3F)]))
    r, _, _ = select.select([fd], [], [], 0.5)
    if not r: return None
    b = os.read(fd, 64)
    return b[1] | (b[2] << 8)
words = []
for a in range(0x40):
    w = read_word(a); words.append(w)
# restore plain GPIO mode with PTT (GPIO3) low
os.write(fd, bytes([0x00, 0x00, 0x00, 0x04, 0x00])); os.close(fd)
print(dev, ' '.join('----' if w is None else f'{w:04X}' for w in words))
