# Bench tools

The scripts the factsheet's figures come from. They run from any machine that can ssh to both Pis as `pi@radio1` (top radio 19925369, board 20000002, and the RSP1) and `pi@radio2` (bottom radio 19925328, board 20000005). The Python files live in `~/tait-pair` on each Pi (copy them there after editing); Python 3 with numpy, `aplay`/`arecord`, and `rx_sdr` with the SDRplay driver on radio1.

| File | Runs on | What it does |
|---|---|---|
| `bench.sh` | control machine | Shell functions that drive both Pis. Source it. |
| `gen.py` | Pi | Writes a test WAV: tone, level ladder, frequency sweep or multitone. |
| `play.py` | Pi | Keys the radio through the CM108 and plays a WAV. Always unkeys. |
| `iqan.py` | radio1 | Reads an RSP1 capture: deviation ladder, deviation from sideband amplitudes, deviation of modem bursts. |
| `wavan.py` | Pi | Reads a receive-audio recording: open-channel level, ladder levels and SINAD, noise floor under a carrier. |
| `clock.py` | radio1 | Playback and capture clock error and wander from one 1 kHz transmission. |
| `sweepan.py` | radio1 | Transmit and receive frequency response from a sweep (expects `sw-TAG.cf32`, `sw-TAG.wav` and `sweep-schedule.json` in `~/tait-pair`). |
| `mtone.py` | Pi | `mtone.py an FILE`: per-band signal quality of a multitone recording (WAV or RSP1 capture). |
| `kisstest.py` | radio1 | Sends N AX.25 UI frames into one KISS port and counts byte-identical arrivals at another. |
| `cm108ee.py`, `cm108eew.py` | Pi | Read and write the CM108B EEPROM over HID. |
| `99-tait-cm108.rules` | Pi | udev rules: ALSA card `Tait<serial>` and `/dev/tait-ptt-<serial>`, so names survive re-enumeration. |

## Typical runs

```sh
source tools/bench.sh

# Tone tests need the sound cards, so stop the modems first.
modems stop

# Deviation ladder from the top radio; RSP1 capture on radio1, receive audio on the other radio's Pi.
shot top lad-top 13 ladder
ssh pi@radio1 'cd tait-pair && python3 iqan.py ladder lad-top.cf32'      # transmit deviation per step
ssh pi@radio2 'cd tait-pair && python3 wavan.py idle lad-top.wav && python3 wavan.py ladder lad-top.wav && python3 wavan.py floor lad-top.wav'

# Deviation cross-check with no demodulator: 8 s of 1 kHz at full scale, read off the sidebands.
shot bot bes-bot 8 tone 1000 0 8
ssh pi@radio1 'cd tait-pair && python3 iqan.py bessel bes-bot.cf32 1000'

# Clocks: 12 s of 1 kHz at -3 dBFS. clock.py wants the capture and the far end's recording side by side on radio1.
shot bot clk-b2t 12 tone 1000 -3 12
ssh pi@radio1 'cd tait-pair && python3 clock.py clk-b2t.cf32 clk-b2t.wav'
shot top clk-t2b 12 tone 1000 -3 12
scp pi@radio2:tait-pair/clk-t2b.wav /tmp/ && scp /tmp/clk-t2b.wav pi@radio1:tait-pair/
ssh pi@radio1 'cd tait-pair && python3 clock.py clk-t2b.cf32 clk-t2b.wav'

# Multitone signal quality at -12 dBFS rms.
shot top mt-top 7 mtone -12
ssh pi@radio2 'cd tait-pair && python3 mtone.py an mt-top.wav'

# Modem tests.
modems start
mode ofdm-fm-8k              # both stations onto one preset
frames 20 1024 6 0 -3        # 20 frames of 1024 B each way, at drive 0 and -3 dB, 6 interleaved rounds
sdr burst 30 & sleep 5; ssh pi@radio1 'python3 tait-pair/kisstest.py 127.0.0.1:8115 radio2:8105 10 1024 20'; wait
ssh pi@radio1 'cd tait-pair && python3 iqan.py burst burst.cf32'          # what the burst really deviates to
```

## Things that will catch you out

- **The test tones need the sound card to themselves.** `modems stop` first, `modems start` after.
- **Frame counts move with time more than with anything you change.** Always interleave the settings you are comparing, over several rounds, and never compare runs taken minutes apart.
- **Run the RSP1 only when you need it.** It shares radio1's USB bus with the top board.
- `frames` restores the drive to 0 dB when it finishes; if you interrupt it, run `drive top 0; drive bot 0`.
- `kisstest.py` sets KISS persistence 255, slot 10 ms, TXDELAY 50 ms and TXTAIL 50 ms on both ports before every run.
- Radio1 cannot ssh to radio2, but it can reach radio2's KISS port, which is why `kisstest.py` runs there.
- The RSP1 is uncalibrated: it reads both carriers about 180 Hz high. Its gain is `GAIN=IFGR=30,RFGR=0` by default; check the capture's peak is under 1.0 if you raise it.
