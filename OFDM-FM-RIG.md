# The OFDM-FM test rig: how to run it

Written 28 November 2026 for whoever picks the work up next. It covers the bench (two radios on two Pis), the tool that drives the modem on it, the machines to build on, and the traps already found. The radio and board facts behind it are in [README.md](README.md); the helper scripts are in [tools/ofdm-fm/](tools/ofdm-fm/).

## What the rig is

Two Tait TM8110 radios joined by coax through attenuators, no antenna. Each has a tait-cm108 board inside (sound card, PTT, control port) and hangs off its own Raspberry Pi (Debian 13 arm64, user `pi`, passwordless sudo, ssh by key from the session machine).

| | radio1 | radio2 |
|---|---|---|
| Host | `pi@radio1` | `pi@radio2` |
| Board serial | 20000005 | 20000002 |
| Radio serial | 19925369 (physically the bottom radio) | 19924394 (physically the top radio) |
| Sound card | `plughw:CARD=Tait20000005,DEV=0` | `plughw:CARD=Tait20000002,DEV=0` |
| PTT | `cm108:/dev/tait-ptt-20000005` | `cm108:/dev/tait-ptt-20000002` |
| Control port (RSSI, carrier) | `/dev/serial/by-id/usb-M9TWM_TaitInterface_20000005-I-if00-port0` | the same with `20000002` |
| Old modem service | `pdn-soundmodem@tait-top` | `pdn-soundmodem@tait-bottom` |
| Bench callsign | `M0LTE-1` | `M0LTE-2` |

- Channel 146.500 MHz, Wide, Very Low power (1 W). Transmit tap T12, receive tap R2, unsquelched: with no carrier the modem hears loud hiss (about -21 dBFS), with a carrier it hears quieting.
- Pad chain: 6 dB, 50 dB, a manual step attenuator (0 to 80 dB), 30 dB, 6 dB. Level at a receiver is about -60.5 dBm minus the attenuator's setting. On 28 November it read -78 dBm both ways (setting about 17.5). Only Tom can turn the knob; read RSSI to learn where it is.
- The names "top" and "bottom" in service and script names are historical and the wrong way round. Name a radio by its Pi.
- radio1 cannot ssh to radio2. Drive both from the session machine.
- The pair is a test rig, not a service. Leave the old modem services stopped. They are still enabled, so a reboot of a Pi starts them and they take the sound card: check first.

## Safety rules

These are Tom's, and absolute.

- Transmit only into the pad chain, at Very Low power (1 W). Never change the radios' power, channel or codeplug. Programming needs Tom's lead in a mic socket: ask him if a codeplug change is truly needed.
- Keep each key-up under 240 s (the radios' transmit timer is 250 s) and leave gaps. The tool's longest key-up is about 15 s (an identification with Morse). If a key-up runs past 30 s, stop and release PTT.
- PTT must always be released. Run anything that can key under `timeout`. Force PTT off on both radios at the start and end of every session and confirm it by RSSI.
- The transmit path has no limiter: never exceed the sound card's full scale, and do not touch the mixer (stored state: PCM 0 dB, Mic -12 dB, AGC off).
- Check which PTT device belongs to which radio, by USB serial, before keying, every session. Use the pinned names above.
- Receive first: start and confirm the listening side before the transmitting side.
- Never loop the `^` command on a control port: it is the radio's reset. Read RSSI only with the one framed `q5064` query (`tools/ofdm-fm/rig.sh rssi`).
- If Tom says he is adjusting something on the bench, do not key until he says he is done.
- The old services' config files on the Pis hold an API key. Never print or copy them.
- Nothing heavy on the Pis, and no builds there.

## A session, start to finish

From the session machine, in `tools/ofdm-fm/`:

```sh
./rig.sh status     # services inactive? no pdn-ofdm left running? PTT devices and cards present?
./rig.sh stop       # only if a service is active
./rig.sh pttoff     # force PTT off both, then read RSSI: both about -124 to -128 dBm
./rig.sh stamp      # new log names for this session
```

RSSI replies look like `q5064 -> b'.j08064-12419F\r.'`: the figure is tenths of dBm, so -124.1 dBm.

Then the runs. Each script starts the listening end first under `timeout`, waits until it is up, runs the other end under `timeout`, samples RSSI and CPU, and waits for both to exit.

```sh
./pingrun.sh s2 r2 r1 3          # radio2 listens, radio1 sends 3 pings
./pingrun.sh s3 r1 r2 5          # the other way
./ax25run.sh s4a r2 r1 2000      # radio2 answers, radio1 calls and fetches 2000 bytes over AX.25
./ax25run.sh s4b r1 r2 2000
./pingrun.sh s5a r2 r1 10 200    # 10 pings of 200 bytes
```

Finish:

```sh
./rig.sh pttoff     # and confirm both RSSI readings are back at the floor
./rig.sh status     # no pdn-ofdm processes, services inactive
```

Logs and recordings land in `~/ofdm-bench/` on each Pi, named `<stamp>-<tag>-<r1|r2>-<what>.log` and `.wav`. Copy the logs back (they are small); leave the recordings on the Pis and list them (they are 2 to 22 MB each). The first session's logs are on the session machine in `/home/tf/ofdm-bench-logs/2026-11-28/`.

`lvl.py WAV START FROM TO` prints the level of a recording every half second, which shows whether a carrier was on the air at a given time (a carrier quiets the hiss).

## The tool

`pdn-ofdm` lives in packet-net/pdn-soundmodem under `tools/Packet.SoundModem.OfdmFmTool/` (its README has the commands). It runs the soundmodem core, the OFDM-FM station and, for `answer` and `call`, packet.net's AX.25 stack, in one process. No KISS, no daemon, no config file.

```
pdn-ofdm listen --device SPEC [--ptt SPEC] --call CALL
pdn-ofdm send   --device SPEC --ptt SPEC --call CALL --to ADDRESS TEXT...
pdn-ofdm ping   --device SPEC --ptt SPEC --call CALL --to ADDRESS [--count N] [--size BYTES]
pdn-ofdm answer --device SPEC --ptt SPEC --call CALL
pdn-ofdm call   --device SPEC --ptt SPEC --call CALL --to CALL [--get BYTES]
common: [--carrier tait:DEVICE] [--detail] [--log FILE] [--record FILE.wav]
```

- Without `--ptt`, `listen` cannot key at all.
- Every line is stamped with UTC time, then the modem's own trace (the library's `docs/trace.md` lists every line). `--detail` adds the measurements and the reasons for each decision; use it on the bench.
- `--record` writes the audio the modem received, 48 kHz mono. It leaves out the station's own transmit time, so a recording is shorter than the run.
- The tool remembers when each callsign and device last identified, under `~/.local/state/pdn-ofdm/` on the Pi, and does not identify again within ten minutes. Delete the file to force a cold start.
- `--carrier tait:<control port>` gives the modem the radio's own carrier indication. It asks the radio once to report carrier changes (a setting held in RAM, the same one the old service sent) and otherwise only listens. Not yet run on the hardware as of 28 November.

### Building and installing it

Never run `dotnet` on the session machine or on a Pi. Build on a build box and copy the result:

```sh
rsync -a --delete --exclude .git --exclude bin --exclude obj --exclude .claude /home/tf/src/pdn-soundmodem/ tf@hyperv-gha:/home/tf/bench-pub/
ssh tf@hyperv-gha 'export DOTNET_ROOT=/usr/lib/dotnet; cd /home/tf/bench-pub && dotnet publish tools/Packet.SoundModem.OfdmFmTool -c Release -r linux-arm64 --self-contained -o out && dotnet build-server shutdown'
# then copy /home/tf/bench-pub/out/ to ~/pdn-ofdm/ on each Pi (through the session machine) and check: ~/pdn-ofdm/pdn-ofdm --help
```

The build boxes are small and shared, and both run CI for pdn-soundmodem. Twice on 28 November too many test runs on `hyperv-gha` (7 GB) made the kernel kill a CI job. Before any build or test run there or on `studybox`: `free -g` shows at least 3 GB available, no other test run is in progress (`pgrep -u tf -fa "dotnet|Tests"`), one process at a time, and `dotnet build-server shutdown` afterwards. Long or memory-hungry runs (the library's gated tier, simulations) go to `studybox` with `-maxThreads 2`, never to `hyperv-gha`. Never stop a process by name pattern.

## What a good run looks like

From the first session (library 0.3.1, -78 dBm):

- From cold: identification burst (about 1.4 s), the callsign in Morse, then the first datagram at 0.25 kbit/s (about 2.2 s). The other station does the same before it answers, so the first ping takes 20 to 28 s.
- The rate climbs over the first few bursts: 29.6, 54.9, then 62.2 kbit/s both ways.
- Later pings: about 3 s round trip.
- Signal figures of 36 to 40 dB on identification bursts and 30 to 33 dB on data.
- A Pi's CPU: 7 to 18 percent of one core idle, 40 to 88 percent of one core in traffic. No "audio lost" lines.
- Every ping answered.

## Known faults and traps

- **False "channel busy" on open-squelch hiss.** With library 0.3.1 both stations often hold off for 19 to 30 s with nothing on air ("Channel busy: a signal is being checked"). It slows round trips and wrecks AX.25 throughput. Being fixed in the library (see the tracking issue in packet-net/pdn-soundmodem); check which library version the tool was built with before reading anything into slow runs.
- **One 30 s stall** with "Channel busy: this station is sending" after the radio had unkeyed (session 1, run s4b). Under investigation with the above.
- **The capture clock wanders for some minutes after a board is plugged in or a Pi boots.** Check `uptime` before trusting a run.
- **A board can drop off USB** (seen once, 15 November). `rig.sh status` shows a missing card.
- **Path loss changes if a pad joint is disturbed.** A 14 dB hole on 17 November was a bad SMA joint. Read RSSI with the far radio keyed before blaming the modem.
- **Background jobs over ssh need `nohup` or they die with the session.** The scripts here avoid the problem by keeping the ssh open.

## Other things on this network that the work uses

- **2 m listening station** (container `airwatch`, `root@10.45.0.87`): listens to 144.800 and the UK packet frequencies through the Reading club's public web receiver, two connections at most, and records how busy and how lossy real channels are. `/opt/airwatch/report` prints the figures; `/opt/airwatch/README.md` explains the rest. It is a guest on someone else's receiver.
- **The 6 m field trial** (packet-net/pdn-soundmodem#917): Reading to Winchester. Neither end's radio is connected yet. Nothing may be transmitted at either site without Tom's say-so.
