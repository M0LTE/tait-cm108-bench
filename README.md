# Tait TM8110 + tait-cm108: bench factsheet

What we know so far about a pair of Tait TM8110 radios fitted with the [packethacking/tait-cm108](https://github.com/packethacking/tait-cm108) internal options board, measured on the bench on 14 November 2026. Facts and figures only; how we got them is not recorded here.

**Headline:** the boards work as built, both ways, cleanly and linearly. With the transmit tap on T12 (which we want, so levels carry across wide and narrow channels) the board's output divider limits full-scale deviation to about 62% of the channel maximum. A one-resistor change to R11 fixes that: see [Recommended hardware change](#recommended-hardware-change).

## The bench

| | |
|---|---|
| Radios | 2 x Tait TM8110 (TMAB12-B100): serial 19925328 on firmware QMA1F 02.19.00.03, codeplug database 0095; serial 19925369 on 02.18.00.00, database 0094 |
| Interface | tait-cm108 board on each radio's internal options connector, USB to a Raspberry Pi |
| Channel | 146.500 MHz, Narrow (12.5 kHz), power Very Low (1 W) |
| RF path | radio, 6 dB (5 W) pad, 100 dB pad, 6 dB (5 W) pad, radio: 112 dB in total |
| Signal at the receiver | -80.5 dBm (radio's own RSSI), against an idle floor of about -128 dBm |
| Deviation measured with | SDRplay RSP1 on a stubby antenna near the radios, FM-demodulated in software (about 36 dB SNR in channel) |

Each board appears on USB as a hub with three devices: a CM108B sound card ("TaitCM108"), a CP2102N "TaitInterface" serial port (the radio's internal serial port, IOP_TXD/RXD), and a CP2102N "TaitProgramming" serial port. Board serial numbers are 20000002 and 20000005.

## Codeplug

Start from the radio's default codeplug and apply the `pdn-internal` profile from [tait-codeplug](https://github.com/M0LTE/tait-codeplug), then set the transmit tap to T12. Channels, frequencies and power are left alone. The full field list is in [data/codeplug-bench.txt](data/codeplug-bench.txt) and the change from default in [data/codeplug-bench.diff](data/codeplug-bench.diff).

| Setting | Value | Why |
|---|---|---|
| Data port | Internal Options, Command mode at power-up, 28800 baud | CCDI control and telemetry (RSSI etc.) over the board's TaitInterface port |
| PTT | IOP_GPIO1 = External PTT 1, active low; EPTT1 transmits Data from Audio Tap In | the board's PTT transistor (CM108 GPIO3) pulls IOP_GPIO1 low |
| Rx tap out | **R2**, type D (split), unmuted except on PTT | after the PSD normaliser, so receive level does not depend on channel width; flat, unsquelched discriminator audio |
| Tx tap in | **T12** | before the PSD scaler, so deviation scales with channel width |
| AUX_GPI1 | Unassigned | so only the board can key the radio |
| Tx timer | 250 s | the default 60 s would cut long transmissions |
| F1 key | Squelch Override | operator convenience |

Notes on taps, from Tait's tap point diagram and confirmed by measurement below:

- **T12** sits between the limiter/3 kHz LPF and the PSD scaler. The radio scales it to the channel, so a level set on narrow is right on wide. It bypasses the limiter, low-pass filter and pre-emphasis, so **nothing in the radio stops over-deviation**: the audio level is the only guard.
- **T13** is after the PSD scaler. The same audio gives the same kHz on any channel width, so a level correct on narrow is half deviation on wide.
- **R2** is after the PSD normaliser but before the 3 kHz LPF, 300 Hz HPF and de-emphasis. Wide-band and low-frequency content reach the modem. Tait warn that R1, R2 or R4 with tap type C (bypass) plus subaudible signalling makes the mute misbehave; type D with no subaudible avoids it.

## Programming the radios

- Codeplug programming only works through the **front panel mic socket** with a programming lead. The internal options connector has one serial pair and no programming lines, and the radio never gives the programming handshake on it. The boards' "TaitProgramming" serial ports did not respond to anything.
- When the data port is **not** Mic (as here), the mic socket programs without a power-cycle.
- The internal port does obey the CCDI `^` (reset) character. Do not send it repeatedly: a tool that retries `^` while waiting for a programming banner holds the radio in a reboot loop.
- tait-codeplug 0.15.0's `patch <port> profile <name>` is broken (it treats "profile" as a field name, and crashes when a profile adds a record). Applying the profile to a saved `.m8p` with `set` and writing that works.
- CCDI at 28800 baud on the internal port works; the radios answer `tait-cli <port> info`.

## Transmit: deviation versus sound card level

1 kHz tone, CM108 output volume at 0 dB (its maximum), peak deviation measured off air.

**T12, Narrow (current configuration):**

| Sound card level | Radio 19925369 | Radio 19925328 |
|---|---|---|
| -20 dBFS | 0.16 kHz | 0.15 kHz |
| -14 dBFS | 0.31 kHz | 0.30 kHz |
| -10 dBFS | 0.50 kHz | 0.48 kHz |
| -6 dBFS | 0.78 kHz | 0.76 kHz |
| -3 dBFS | 1.11 kHz | 1.07 kHz |
| 0 dBFS | **1.57 kHz** | **1.51 kHz** |

**Tap and channel width compared** (radio 19925369):

| Configuration | Full scale (0 dBFS) | Share of channel maximum |
|---|---|---|
| T12, Narrow | 1.57 kHz | 63% of 2.5 kHz |
| T12, Wide | 3.13 kHz | 63% of 5 kHz |
| T13, Narrow | 2.44 kHz | 97% of 2.5 kHz |
| T13, Wide | 2.44 kHz (unscaled, not measured) | 49% of 5 kHz |

- **Linear:** deviation follows level to within 0.05 dB over the whole range, on both radios.
- **T12 Wide is exactly twice T12 Narrow** (6.0 dB), as the tap position predicts.
- **T13 is 3.8 dB more sensitive than T12** on a narrow channel.
- **Clean:** second plus third harmonic -47 dBc at full scale on Narrow, -52 dBc on Wide. Residual FM about 30 Hz rms.
- **Matched:** the two radio and board pairs are within 0.4 dB of each other.
- Carriers were within 10 Hz of each other (absolute frequency not measured; the RSP1 was not calibrated).

## Receive

Receiving radio on R2, CM108 input at -12 dB (its minimum), AGC off.

| | |
|---|---|
| Open channel, no carrier | about -19 dBFS rms, peaks about -11 dBFS (unsquelched discriminator noise) |
| 1 kHz tone at 1 kHz peak deviation | about -29.6 dBFS rms |
| Linearity | received level tracks transmitted level within 0.1 dB from 0.16 to 1.57 kHz deviation |
| SINAD (300 Hz to 3 kHz) | 22 dB at 0.16 kHz deviation rising to about 38 dB at 1.5 kHz |
| Harmonics in received audio | third harmonic about -36 dBc at the top of the ladder |

- At -80 dBm the receiver is fully quieted, so SINAD is limited by deviation, not signal strength: more deviation buys more SINAD. This is another reason to want more transmit headroom.
- The -36 dBc third harmonic is not in the transmitted signal (which is -47 dBc), so it arises on the receive side: the radio's R2 output, the board's input divider (R5/R10) or the CM108 input. The CM108's mic boost is off (see below), so it is not that. Not yet investigated; harmless for modems.
- There is headroom to raise the CM108 input gain by a few dB before open-channel noise peaks approach clipping.

## CM108B EEPROM

Both boards' EEPROMs read identically apart from the serial number ([data/eeprom-board-20000002.txt](data/eeprom-board-20000002.txt), [data/eeprom-board-20000005.txt](data/eeprom-board-20000005.txt); 64 words from address 0x00).

| Item | Value |
|---|---|
| VID:PID | 0D8C:0012 |
| Product / manufacturer / serial | "TaitCM108" / "M9TWM" / board serial |
| Mic input high-pass filter | **off** (good for 9600 and other low-frequency modes) |
| Mic boost | **off** (boost mode field set to 12 dB but not enabled) |
| DAC (output) volume range | -37 dB to 0 dB |
| ADC (input) volume range | -12 dB to +23 dB |

**The EEPROM cannot add transmit level.** The CM108B's output volume control is an attenuator, 0 dB at most, and full-scale output is already about 1 V rms into 10 kohm. Extra deviation has to come from the board's output divider or the tap point. Nothing in the EEPROM needs changing.

Start-up mixer levels are best set on the host. On Linux, set output 0 dB, input as wanted, AGC off, then `sudo alsactl store` so they are restored whenever the card re-enumerates (otherwise the output came back at -20 dB).

## Recommended hardware change

The output path is CM108B line out, C29, then a divider of R11 (series, 3k3) and R12 (shunt, 1k), then C30 into the radio's AUD_TAP_IN. That divides by 4.3. On T12 it lands full scale at about 62% of the channel maximum (1.54 kHz on Narrow, average of the two boards), and the sound card has nothing left to give.

Changing **R11** alone moves the ceiling (figures scaled from the measurements above, T12):

| R11 | Divider | Full scale, Narrow | Share of maximum | Full scale, Wide |
|---|---|---|---|---|
| 3k3 (fitted) | /4.3 | 1.54 kHz | 62% | 3.08 kHz |
| 2k2 | /3.2 | 2.07 kHz | 83% | 4.14 kHz |
| **2k0** | **/3.0** | **2.21 kHz** | **88%** | **4.41 kHz** |
| 1k8 | /2.8 | 2.37 kHz | 95% | 4.73 kHz |

**Recommendation: R11 = 2k0** (0805, 1%). It gives about 3.1 dB more deviation and leaves about 1 dB margin at full scale. That margin matters on T12, because the radio has no limiter in that path and the sound card level is the only protection against over-deviating. The two boards differ by about 0.4 dB, so 1k8 would leave too little. With 2k0 the load on the CM108B line output is 3 kohm, between the 10 kohm and 32 ohm loads it is specified for, and the coupling corners stay below 6 Hz.

The alternative without a soldering iron is T13, which reaches 97% on Narrow, but only on a single channel width: on Wide it would be 49%. If both radios stay on one channel width forever, T13 is a valid choice; T12 plus R11 = 2k0 is right for anything else.

After the change, re-measure full-scale deviation on each radio; the table above is a scaling, not a measurement.

## Open questions

- Source of the -36 dBc third harmonic on receive.
- Low-frequency response end to end (relevant to 9600 and C4FSK).
- Best CM108 input gain for the modems.
