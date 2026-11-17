# Tait TM8110 + tait-cm108: bench factsheet

What a bench of two Tait TM8110 radios with the [packethacking/tait-cm108](https://github.com/packethacking/tait-cm108) internal options board shows about that combination, for anyone setting one up or building modems for it. Measured November 2026. The scripts are in [tools/](tools/), with a how-to in [tools/README.md](tools/README.md); raw data is in [data/](data/).

**Headline:**

1. **Set the CM108B's "MIC PLL Adjust" EEPROM bit on every board.** As shipped, its capture clock runs about 520 ppm away from its playback clock, which is invisible to tones and AFSK but stops ofdm-fm decoding entirely. One EEPROM word fixes it. See [Sample clock](#cm108b-sample-clock).
2. **Fit R11 = 2k0 (not 3k3).** With the transmit tap on T12, the as-built divider limits full-scale deviation to 62% of the channel maximum; 2k0 gives 88 to 90%. On the densest ofdm-fm preset that doubled the frames delivered. See [Output level: R11](#output-level-r11).
3. **Use R2 and T12.** Both are levelled by the radio to the channel width, so one set of levels serves Narrow and Wide.
4. Otherwise the board works as built: linear, two boards matched within 0.4 dB, audio flat from 30 Hz to about 5 kHz.

## Test setup

| | |
|---|---|
| Radios | Tait TM8110 (TMAB12-B100), firmware 2.18 and 2.19, codeplug databases 0094 and 0095 |
| Interface | tait-cm108 board on each radio's internal options connector, USB to a Raspberry Pi 4, one Pi per radio |
| Channel | 146.500 MHz, Very Low power (1 W), Wide (25 kHz) unless stated |
| RF path | 112 dB of attenuation between the radios (5 W 6 dB pads at each radio, low-power pads between), about -80 dBm at each receiver |
| Modem | pdn-soundmodem 0.108.0, one instance per radio |
| Deviation measured with | SDRplay RSP1, FM-demodulated in software; cross-checked against the FM sideband amplitudes of a steady tone (agree within 0.2%) |

Each board appears on USB as a hub carrying a CM108B sound card, a CP2102N "TaitInterface" serial port (the radio's internal serial port, IOP_TXD/RXD) and a CP2102N "TaitProgramming" port.

**Pin the device names.** Linux numbers sound cards and hidraw nodes in the order they appear, so a board that re-enumerates can come back under another name and its modem cannot find it. [tools/99-tait-cm108.rules](tools/99-tait-cm108.rules) names each board by its USB serial number (ALSA card `Tait<serial>`, PTT `/dev/tait-ptt-<serial>`); point the modem configuration at those names.

**Lessons about the bench itself:**

- **At -80 dBm the receivers are not fully quieted above 1 kHz.** Taking 3.5 dB out of the path (an SDR tee) raised receive noise above 1 kHz by 2 to 3 dB and cost the margin preset most of its frames. Keep the path loss fixed between anything you compare.
- **An SDR on a tee is a good deviation meter** (48 dB in-channel signal to noise) but **cannot verify an attenuator chain**: with a 1 W transmitter nearby it picks the signal up by other routes at roughly 60 dB below the transmitter, so readings stop falling once the wanted signal is weaker than that. Check pad chains with the radios' own RSSI instead.
- **SMA joints can pass DC and not RF.** A continuity check across a pad chain proves nothing about attenuation; a joint that is not fully mated can lose 15 dB. Check end-to-end RF level against the sum of the pads.
- **ofdm-fm frame counts move from minute to minute** with nothing changed (`ofdm-fm-8k` has swung between 60% and 100% within the hour). Compare settings only in interleaved rounds, at least four rounds of 20 frames each way.

## Codeplug

Start from the radio's default codeplug, apply the `pdn-internal` profile from [tait-codeplug](https://github.com/M0LTE/tait-codeplug), set the transmit tap to T12, and set the channel (frequency, width, power) for the setup. The bench's field list is in [data/codeplug-bench.txt](data/codeplug-bench.txt) and its change from default in [data/codeplug-bench.diff](data/codeplug-bench.diff).

| Setting | Value | Why |
|---|---|---|
| Data port | Internal Options, Command mode at power-up, 28800 baud | CCDI control and telemetry (RSSI etc.) over the board's TaitInterface port |
| PTT | IOP_GPIO1 = External PTT 1, active low; EPTT1 transmits Data from Audio Tap In | the board's PTT transistor (CM108 GPIO3) pulls IOP_GPIO1 low |
| Rx tap out | **R2**, type D (split), unmuted except on PTT | after the deviation normaliser, so receive level does not depend on channel width; flat, unsquelched discriminator audio |
| Tx tap in | **T12** | before the deviation scaler, so deviation scales with channel width |
| AUX_GPI1 | Unassigned | so only the board can key the radio |
| Tx timer | 250 s | the default 60 s cuts long transmissions |

Tap points, from Tait's diagram and confirmed by measurement:

- **T12** sits between the limiter/3 kHz low-pass and the deviation scaler. The radio scales it to the channel, so a level set on Narrow is right on Wide (measured: Wide is exactly 6.0 dB above Narrow). It bypasses the limiter, low-pass and pre-emphasis, so **nothing in the radio stops over-deviation**: the audio level is the only guard.
- **T13** is after the scaler: the same audio gives the same kHz on any width. It is 3.8 dB more sensitive than T12 on Narrow. **With R11 = 2k0, T13 would over-deviate a Narrow channel at full scale** (about 3.5 kHz against the 2.5 kHz maximum), so do not use T13 with the modified board.
- **R2** is after the normaliser but before the 3 kHz low-pass, 300 Hz high-pass and de-emphasis, so wide-band and low-frequency content reach the modem. Tait warn that R1, R2 or R4 with tap type C (bypass) plus subaudible signalling makes the mute misbehave; type D with no subaudible avoids it.

## Programming the radios

- Codeplug programming only works through the **front panel mic socket** with a programming lead. The internal options connector has one serial pair and no programming lines, and the radio never gives the programming handshake on it. The board's "TaitProgramming" port does not respond.
- When the data port is not Mic, the mic socket programs without a power-cycle.
- The internal port obeys the CCDI `^` (reset) character. A tool that retries `^` while waiting for a programming banner holds the radio in a reboot loop.
- A radio from elsewhere can arrive on any channel at High power. Program Very Low and the bench channel before it is ever keyed into a pad chain.
- tait-codeplug: `patch <port> profile` crashes in 0.15.x; it is fixed on main ([#24](https://github.com/M0LTE/tait-codeplug/pull/24)), which also adds `write <port> <file>` for writing a prepared codeplug in one go ([#25](https://github.com/M0LTE/tait-codeplug/pull/25)), not yet in a release.

## Transmit

**Deviation against sound card level**, T12, Wide, 1 kHz tone, CM108B output at 0 dB (its maximum), R11 = 2k0, two boards:

| Sound card level | Deviation | Share of the 5 kHz maximum |
|---|---|---|
| -20 dBFS | 0.44 to 0.45 kHz | 9% |
| -10 dBFS | 1.39 to 1.42 kHz | 28% |
| -6 dBFS | 2.20 to 2.26 kHz | 45% |
| -3 dBFS | 3.11 to 3.19 kHz | 63% |
| 0 dBFS | **4.39 to 4.50 kHz** | **88 to 90%** |

On Narrow every figure is half (T12 scales), so full scale is about 2.2 kHz of the 2.5 kHz maximum.

- **Linear:** every 3 to 6 dB step lands within 0.01 to 0.05 dB of what was sent.
- **Clean:** second plus third harmonic -56 dBc at full scale; residual FM about 12 to 30 Hz rms.
- **Matched:** boards within 0.4 dB of each other.
- **What a real ofdm-fm burst deviates to:** measured before the change at 0.69 kHz rms with 2.65 kHz peaks (crest factor 11.7 dB, peaks at 87% of a full-scale sample); scaled to R11 = 2k0, about 1.0 kHz rms and 3.8 kHz peak. The sine figure is the ceiling; the burst is what the link runs on.
- **Supply:** a radio on a noisy mains supply showed a 100 Hz buzz on its transmitted carrier (14 Hz rms of deviation), gone on battery. Worth checking the residual FM of a quiet carrier on any new setup.

## Receive

Receiving radio on R2, CM108B input at -12 dB (its minimum), AGC off.

| | |
|---|---|
| Open channel, no carrier | -19 to -21 dBFS rms, peaks -11 to -12 dBFS (unsquelched discriminator noise) |
| 1 kHz tone at 1 kHz peak deviation | -35.6 dBFS rms on Wide, -29.6 dBFS rms on Narrow |
| Same share of the channel's maximum | same level on Narrow and Wide (R2 normalises) |
| Linearity | received level tracks transmitted level within 0.1 dB |

SINAD (300 Hz to 3 kHz) against deviation, 1 kHz tone, Wide, -80 dBm:

| Deviation | 0.31 kHz | 0.61 kHz | 0.97 kHz | 1.53 kHz | 2.16 kHz | 3.06 kHz |
|---|---|---|---|---|---|---|
| SINAD | 28 dB | 34 dB | 37 to 38 dB | **40 dB** | 39 to 40 dB | 37 to 38 dB |

- **Below about 1.5 kHz of deviation, more deviation means better SINAD, dB for dB.**
- **Above that, receive-side distortion takes over:** the third harmonic in the received audio rises from below -45 dBc to -34 dBc at 3 kHz, while the transmitted signal is clean. On a strong signal, extra deviation does not make a tone cleaner; on a weak one, where noise is the limit, it does.
- **Leave the CM108B input gain at -12 dB.** With it 10 dB higher, signal, noise and SINAD all move together, so the sound card's own noise is irrelevant, and the open-channel noise peaks reach -1.4 dBFS.

## Audio frequency response

Wide, T12 and R2, 40-tone sweep 30 Hz to 12 kHz at about 1 kHz of deviation, relative to 1 kHz. **Transmit** is the deviation off air (sending CM108B, board output network, radio modulator). **Receive** is the receiving card's audio with the transmit response removed (receiving radio, board input network, CM108B input). Both radios and both boards agree within 0.3 dB; full data in [data/](data/).

| Frequency | 30 Hz | 100 Hz | 300 Hz | 1 kHz | 3 kHz | 4.1 kHz | 4.8 kHz | 5.6 kHz | 6.5 kHz | 7.6 kHz | 8.8 kHz | 10.3 kHz | 12 kHz |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Transmit | -0.2 to 0.0 | 0.0 to +0.2 | +0.1 to +0.2 | 0 | -0.1 | -0.2 | -0.3 | -0.4 | -0.5 | -0.7 | -1.1 | -1.6 | -2.4 dB |
| Receive | 0.0 | 0.0 | 0.0 | 0 | 0.0 | -0.1 to -0.3 | -0.4 to -0.6 | -1.2 to -1.4 | -2.8 to -3.0 | -5.7 to -5.9 | -10.5 | -19.3 | -37.7 dB |

- **Transmit is flat within 0.5 dB from 30 Hz to 6.5 kHz**: no pre-emphasis and no low-frequency limit, which suits 9600 and C4FSK.
- **Receive is flat to 4 kHz, -3 dB at about 6.6 kHz, -6 dB at 7.6 kHz.** The roll-off is the radio's (the board's input network has no corner below 100 kHz, and a different CM108 interface measured the same shape). It costs the top carriers of `ofdm-fm-8k` about 6 dB. Measured on Wide; Narrow's IF filter will roll off sooner.

## Noise and signal quality across the band

**Noise floor** under an unmodulated carrier at -80 dBm (receive audio, input at -12 dB): about -110 dBFS/Hz below 100 Hz, -105 dBFS/Hz from 100 Hz to 1 kHz, -109 dBFS/Hz from 1 to 3 kHz, -104 to -105 dBFS/Hz from 4 to 8 kHz. Against a tone at 1 kHz of deviation on Wide that is 43 to 56 dB in 100 Hz across the band. Small tones near 1 kHz and 4 kHz about 10 dB above the floor are probably USB frame-rate pickup on the board.

**Signal quality with an OFDM-like signal** (84 tones from 211 Hz to 8 kHz with gaps between them; tone power against what fills the gaps), R11 = 3k3 levels:

| Drive (rms) | 0.2 to 1 kHz | 1 to 2 kHz | 2 to 3 kHz | 4 to 5 kHz | 5 to 6 kHz | 7 to 8 kHz |
|---|---|---|---|---|---|---|
| -12 dBFS | 39 to 40 dB | 38 dB | 33 to 35 dB | 29 to 30 dB | 27 to 28 dB | 24 to 25 dB |
| -18 dBFS | 34 to 35 dB | 39 dB | 37 dB | 32 to 33 dB | 31 dB | 27 to 28 dB |

Quality falls about 15 dB across the band, and above 1 kHz lower drive is cleaner, so distortion as well as noise sets it at these levels. -12 dBFS rms is where an `ofdm-fm-8k` burst sits. The method understates distortion (third-order products land on the tones, not in the gaps); treat the figures as upper bounds.

## CM108B sample clock

As shipped, the CM108B plays back locked to the host's USB timing but its capture clock runs free:

| | Playback (DAC) | Capture (ADC), as shipped | Capture (ADC), MIC PLL Adjust on |
|---|---|---|---|
| Rate against a 1 ppm reference | the host's USB clock (-130 and -135 ppm on two Pi 4s) | +353 to +393 ppm | the host's USB clock, within about 10 ppm |

So as shipped, every link between two of these boards carries a fixed **mismatch of about 520 ppm**: 22 samples of drift across a 0.9 s burst. Tones, levels and AFSK do not notice; ofdm-fm decodes nothing.

- **The fix:** EEPROM word **0x2B from 7A02 to 7A12** (bit 4, "MIC PLL Adjust"). The capture clock then follows the USB timing, and the mismatch between two stations is the difference between their hosts' USB clocks.
- It takes effect only after the board is power-cycled (unplug and replug). A USB reset is not enough.
- For some minutes after power-up the capture clock settles, with swings of several hundred ppm. Let a board settle before testing.
- **It trades a fixed error for a moving one.** Worst timing excursion within any 1.5 s, after removing that stretch's own average rate:

| | As shipped | MIC PLL Adjust on |
|---|---|---|
| Playback clock | 23 to 24 microseconds (one-sample steps about once a second, following USB frames) | 21 to 26 microseconds |
| Capture clock | 7 to 11 microseconds | **33 to 61 microseconds** (hunts 20 to 40 microseconds either way) |

  40 microseconds is 2 radians of phase at 8 kHz. Whether this wander limits the dense presets is not established. A free-running capture clock with software resampling by the measured offset is the alternative ([pdn-soundmodem #809](https://github.com/packet-net/pdn-soundmodem/issues/809)).

**Between different computers**, the mismatch is the difference between their USB clocks. Two Pi 4s here were 3 to 15 ppm apart, which is luck; 100 to 200 ppm is ordinary. Tolerance measured offline, by resampling 20 real `ofdm-fm-8k` bursts (an already marginal set, 7/20 unaltered) and decoding them with `pdn-soundmodem --wav`:

| Offset | -300 | -200 | -100 | -50 | 0 | +50 | +100 | +200 | +300 ppm |
|---|---|---|---|---|---|---|---|---|---|
| Decoded of 20 | 2 | 3 | 6 | 10 | 7 | 9 | 9 | 6 | 2 |

Flat within the run-to-run spread to about plus or minus 100 ppm, failing beyond. The single-carrier modems track 500 ppm or more.

## CM108B EEPROM

As shipped ([data/](data/) has the dumps):

| Item | Value |
|---|---|
| VID:PID | 0D8C:0012 |
| Product / manufacturer / serial | "TaitCM108" / "M9TWM" / board serial |
| Mic input high-pass filter | **off** (good for 9600 and other low-frequency modes) |
| Mic boost | **off** |
| MIC PLL Adjust | **off as shipped; turn it on** (word 0x2B bit 4) |
| DAC (output) volume range | -36 to 0 dB in 1 dB steps (ALSA), muting below |
| ADC (input) volume range | -12 to +23 dB |

The EEPROM is read and written over the CM108B's HID interface, the same one that carries PTT: output report `[0x80, lo, hi, 0x80|addr]` reads a word (returned in input report bytes 1 and 2), `[0x80, lo, hi, 0xC0|addr]` writes one. Scripts in [tools/](tools/).

**The EEPROM cannot add transmit level**: the output volume control is an attenuator, 0 dB at most, and full-scale output is already about 1 V rms.

**Start-up mixer levels**: set output 0 dB, input -12 dB, AGC off, then `sudo alsactl store` (after installing the udev rules, since the stored state is keyed by card name); otherwise a re-enumerated card comes back at -20 dB output. pdn-soundmodem also sets all three at start-up when its configuration has an `alsa.mixer` section.

## Output level: R11

The output path is CM108B line out, C29, a divider of R11 (series) and R12 (shunt, 1k), then C30 into the radio's AUD_TAP_IN.

| R11 | Divider | Full scale, Wide (T12) | Share of maximum |
|---|---|---|---|
| 3k3 (as built) | /4.3 | 3.06 kHz (measured) | 62% |
| 2k2 | /3.2 | 4.11 kHz | 83% |
| **2k0 (recommended)** | **/3.0** | **4.39 to 4.50 kHz (measured)** | **88 to 90%** |
| 1k8 | /2.8 | 4.70 kHz | 95% |

- **Why change it:** the receiver is quieted, so recovered signal to noise rises with deviation, and software cannot raise the level (the CM108B is at its 0 dB maximum and the EEPROM cannot help).
- **Why 2k0 and not more:** T12 has no limiter, so the audio level is the only guard against over-deviating. 2k0 keeps a full-scale sine at 88 to 90% and leaves about 1 dB of margin for board-to-board spread; OFDM peaks are bounded by the DAC's full scale, so they stay under it too. 1k8 leaves too little.
- With 2k0 the CM108B line output drives 3 kohm, between the 10 kohm and 32 ohm loads it is specified for; coupling corners stay below 6 Hz.
- **Measured after the change:** +3.2 dB on both boards, within 2% of the prediction, still linear and clean.

## ofdm-fm results

pdn-soundmodem 0.108.0, one station per Pi, Wide, path at -80 dBm, MIC PLL Adjust on, R11 = 2k0. KISS channel access set before every run on both stations: **persistence 255, slot time 10 ms, TXDELAY 50 ms, TXTAIL 50 ms**, so no random back-off. Carrier sense from each radio's CCDI RSSI (busy above -110 dBm). Frames are AX.25 UI, counted byte-identical at the far KISS port. Interleaved rounds of 20 frames each way; "-3 dB" is the old (R11 = 3k3) full-scale level.

| Preset, frame | Full drive | -3 dB |
|---|---|---|
| `ofdm-fm-8k`, 1024 B | 77/80 | 80/80 |
| `ofdm-fm-8k-r78`, 1900 B | **66/80** | **34/80** |

- **The extra 3 dB of deviation from R11 = 2k0 doubles what the margin preset delivers.** The same effect appeared in every drive comparison on this bench, before and after the change.
- `ofdm-fm-8k` has margin either way and runs at about 16.7 kbit/s at 1024 B; `ofdm-fm-8k-r78` reaches 23 to 24 kbit/s at 1900 B when frames arrive.
- **The two directions are not always equal at the margin**, and a weak direction can swing from 8/20 to 20/20 between rounds. Tone, response and multitone tests are symmetric, so the cause is something they do not see.
- Before MIC PLL Adjust, nothing decoded on any preset, including `ofdm-fm-narrow`.
- **The modem reports nothing about a burst it fails to decode**, and no signal-to-noise figure for ofdm-fm frames, so delivered counts are the only live measure.

## Open questions

- Why `ofdm-fm-8k` delivery comes and goes over minutes with nothing changed. Seeing failed bursts is the first thing needed.
- Why one direction can be weaker at the ofdm-fm margin when every analogue measurement is symmetric.
- Whether the capture clock's wander after MIC PLL Adjust limits the dense presets, and whether a free-running clock with software resampling would do better.
- Why lower drive gives a cleaner multitone above 1 kHz but worse `ofdm-fm-8k-r78` delivery.
- Clock offsets between other computers, and station-side rate correction (pdn-soundmodem #809).
- The receive response and signal quality on Narrow, and the burst deviation after R11 = 2k0, have not been measured directly.
