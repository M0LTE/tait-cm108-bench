#!/usr/bin/env python3
"""Key a radio through its CM108 (GPIO3) and play a WAV. PTT is always dropped on the way out.
  play.py HIDRAW CARD WAV     e.g. play.py /dev/hidraw1 TaitCM108_1 /tmp/x.wav
The carrier is up 0.5 s before the audio and 0.2 s after it."""
import subprocess, sys, time
hid, card, wav = sys.argv[1:4]
def ptt(on):
    with open(hid, 'wb', buffering=0) as f: f.write(bytes([0, 0, 0x04 if on else 0, 0x04, 0]))
try:
    ptt(True); time.sleep(0.5)
    subprocess.run(['aplay', '-q', '-D', f'plughw:CARD={card},DEV=0', wav], timeout=120, check=True)
    time.sleep(0.2)
finally:
    ptt(False)
