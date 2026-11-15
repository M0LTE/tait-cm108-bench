# Tait TM8110 + tait-cm108: bench factsheet

What we know so far about a pair of Tait TM8110 radios fitted with the [packethacking/tait-cm108](https://github.com/packethacking/tait-cm108) internal options board, measured on the bench on 14 and 15 November 2026. Facts and figures only; how we got them is not recorded here.

**Headline:**

1. **Set the CM108B's "MIC PLL Adjust" EEPROM bit on every board.** As shipped, the capture clock runs about 520 ppm away from the playback clock, which breaks OFDM completely and is invisible to everything else. One EEPROM word fixes it: see [CM108B sample clock](#cm108b-sample-clock-set-mic-pll-adjust).
2. **Change R11 from 3k3 to 2k0.** With the transmit tap on T12 (which we want, so levels carry across wide and narrow channels) the board's output divider limits full-scale deviation to about 62% of the channel maximum, and on ofdm-fm 3 dB of drive is worth a great deal. See [Hardware change: decision](#hardware-change-decision).
3. Otherwise the boards work as built: both ways, linear, matched to within 0.4 dB, flat audio from 30 Hz to about 5 kHz.

## The bench

| | |
|---|---|
| Radios | 2 x Tait TM8110 (TMAB12-B100): serial 19925328 on firmware QMA1F 02.19.00.03, codeplug database 0095; serial 19925369 on 02.18.00.00, database 0094 |
| Interface | tait-cm108 board on each radio's internal options connector, USB to a Raspberry Pi |
| Channel | 146.500 MHz, power Very Low (1 W). Narrow (12.5 kHz) for the tone and level measurements, Wide (25 kHz) for the frequency response and ofdm-fm |
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

## Audio frequency response

Measured on Wide, T12 and R2, with a 40-tone sweep from 30 Hz to 12 kHz at -10 dBFS (about 1 kHz peak deviation). **Transmit** is the deviation measured off air with the RSP1, so it covers the sending CM108B, the board's output network and the radio's modulator. **Receive** is the receiving card's audio with the transmit response taken out, so it covers the receiving radio, the board's input network and the CM108B input. All figures relative to 1 kHz. Full data in [data/sw-top2bot.json](data/sw-top2bot.json) and [data/sw-bot2top.json](data/sw-bot2top.json).

| Frequency | Transmit, radio 19925369 | Transmit, radio 19925328 | Receive, radio 19925328 | Receive, radio 19925369 |
|---|---|---|---|---|
| 30 Hz | -0.2 dB | -0.0 dB | -0.0 dB | -0.0 dB |
| 48 Hz | -0.1 dB | +0.1 dB | -0.0 dB | -0.0 dB |
| 103 Hz | -0.0 dB | +0.2 dB | +0.0 dB | +0.0 dB |
| 301 Hz | +0.1 dB | +0.2 dB | +0.0 dB | +0.0 dB |
| 1.0 kHz | 0 dB | 0 dB | 0 dB | 0 dB |
| 2.2 kHz | -0.1 dB | -0.0 dB | +0.0 dB | -0.0 dB |
| 3.0 kHz | -0.1 dB | -0.1 dB | +0.1 dB | -0.1 dB |
| 4.1 kHz | -0.2 dB | -0.2 dB | -0.1 dB | -0.3 dB |
| 4.8 kHz | -0.3 dB | -0.2 dB | -0.4 dB | -0.6 dB |
| 5.6 kHz | -0.4 dB | -0.3 dB | -1.2 dB | -1.4 dB |
| 6.5 kHz | -0.5 dB | -0.5 dB | -2.8 dB | -3.0 dB |
| 7.6 kHz | -0.7 dB | -0.7 dB | -5.7 dB | -5.9 dB |
| 8.8 kHz | -1.1 dB | -1.0 dB | -10.5 dB | -10.6 dB |
| 10.3 kHz | -1.6 dB | -1.5 dB | -19.3 dB | -19.3 dB |
| 12.0 kHz | -2.4 dB | -2.4 dB | -37.7 dB | -37.8 dB |

- **Transmit is flat within 0.5 dB from 30 Hz to 6.5 kHz** and only 2.4 dB down at 12 kHz. No pre-emphasis (as expected for T12) and no low-frequency limit down to 30 Hz, which is good news for 9600 and C4FSK.
- **Receive is flat within 0.1 dB from 30 Hz to 4 kHz, then rolls off: -3 dB at about 6.6 kHz, -6 dB at 7.6 kHz, -10 dB at 8.8 kHz.** The roll-off is in the radio: the board's input network and the CM108B input are flat well past 20 kHz. It costs the top carriers of `ofdm-fm-8k` (which reaches 8 kHz) about 6 dB.
- **The two radios match within 0.3 dB** everywhere, in both directions.

## Noise, spurs and signal quality across the band

**Noise floor** (unchanged within 0.5 dB between mains and battery power) under an unmodulated carrier (receive audio, CM108 input at -12 dB) is about -110 dBFS/Hz below 100 Hz, -105 dBFS/Hz from 100 Hz to 1 kHz, -109 dBFS/Hz from 1 to 3 kHz and -104 to -105 dBFS/Hz from 4 to 8 kHz, the same on both receivers. Against a tone at 1 kHz peak deviation that is 43 to 56 dB in a 100 Hz bandwidth across 30 Hz to 8 kHz.

**Spurs:**

- **Radio 19925328's receiver has a tone at about 3.89 kHz** (drifting 3882 to 3902 Hz), 26 dB above the noise around it: about -76 dBFS, the equivalent of 9 Hz of deviation. It is not on the other radio's transmission (checked with the RSP1) and not caused by the RSP1. The other receiver does not have it. Source not yet found (radio or board). It is not the programming lead that was in that radio's mic socket, nor the power supply: it is unchanged with the lead unplugged and with the radios on battery (-78 dBFS/Hz at its peak either way).
- **Radio 19925328's transmitter carried a 100 Hz buzz on mains power** with harmonics to about 2.7 kHz: 5 to 7 Hz peak deviation per harmonic, 14 Hz rms in total (11.8 Hz rms with the mic-socket programming lead unplugged). **On battery it falls to 6 Hz rms**, about the measurement floor and level with the other radio (4.4 Hz rms), so it came from the mains supply. Residual FM between 300 Hz and 3 kHz also fell on battery: 23 to 17 Hz rms on that radio, 18 to 12 Hz rms on the other.
- Both receivers show small tones near 1 kHz and 4 kHz, about 10 dB above the noise, probably USB frame-rate pickup on the boards. Minor.

**Signal quality with an OFDM-like signal** (84 tones from 211 Hz to 8 kHz, random phases, gaps between them; tone power against what fills the gaps, at the receiving card). Both directions measured within 1 to 2 dB of each other:

| Drive (rms) | 0.2 to 1 kHz | 1 to 2 kHz | 2 to 3 kHz | 4 to 5 kHz | 5 to 6 kHz | 7 to 8 kHz |
|---|---|---|---|---|---|---|
| -12 dBFS | 39 to 40 dB | 38 dB | 33 to 35 dB | 29 to 30 dB | 27 to 28 dB | 24 to 25 dB |
| -18 dBFS | 34 to 35 dB | 39 dB | 37 dB | 32 to 33 dB | 31 dB | 27 to 28 dB |

Quality falls steadily with frequency, by about 15 dB across the band, and improves at the top when the drive is lowered, so distortion as well as noise is setting it. This is the budget an OFDM modem has to work within on this bench.

## ofdm-fm

pdn-soundmodem 0.108.0, one instance per radio on the same Raspberry Pi, both radios on Wide. Carrier sense from each radio's own CCDI RSSI (busy above -110 dBm). KISS channel access set by the test harness before every run on both stations: **persistence 255, slot time 10 ms, TXDELAY 50 ms, TXTAIL 50 ms**, so no random back-off. Frames are AX.25 UI, counted byte-identical at the far KISS port.

**Before MIC PLL Adjust** nothing decoded live in either direction, on any preset including `ofdm-fm-narrow`. Offline decoding of a recording got 1 frame in 3, at 11 to 15 dB SNR.

**After MIC PLL Adjust:**

| Preset, frame size | Bottom to top | Top to bottom |
|---|---|---|
| `ofdm-fm-narrow`, 256 B | 10/10, 2.0 kbit/s | 10/10, 2.0 kbit/s |
| `ofdm-fm-8k`, 1024 B | 10/10, 16.1 kbit/s | 10/10, 16.0 kbit/s |
| `ofdm-fm-8k-r78`, 1900 B, full drive | 57/60 | 20/60 |
| `ofdm-fm-8k-r78`, 1900 B, drive 3 dB lower | 53/60 | 2/60 |

(The r78 rows are three alternating runs of 20 frames at each drive, interleaved.)

- `ofdm-fm-8k` works at the rate the earlier ofdm-fm bench reported (17.5 kbit/s at 1024 B, with about 2.4 dB more deviation than this bench has).
- `ofdm-fm-8k-r78` is right at the edge here, which makes it a sensitive test: **3 dB less drive took one direction from 20/60 to 2/60** and the other from 57/60 to 53/60.
- **The two directions are not equal at the margin.** Top to bottom (received by radio 19925328) is consistently weaker. Tone tests, frequency response and the multitone test above are all symmetric, so the difference is something those do not see. Candidates: the 3.89 kHz spur in that receiver (though notching it out offline made decoding worse, not better, because the notch costs more carriers than the spur does), and the receiving CM108B's clock wandering within a burst (below).
- **Clock wander after the change:** the capture clocks lock to the USB timing on average but wander by about plus or minus 50 ppm over half-second spans, on both boards, which over a 1.5 s burst is about 1.2 to 1.4 rad of phase at 8 kHz. Straight after a board is powered up it is much worse (swings of several hundred ppm for some minutes), so let a board settle before testing.

## CM108B sample clock: set MIC PLL Adjust

**This is the most important finding so far, and it needs no hardware change.**

As shipped, each board's CM108B plays back locked to the host's USB timing, but its capture (ADC) clock runs free. Measured against the RSP1 (whose own error is about 1 ppm, from the Tait carriers), with a 1 kHz tone through the radios:

| | Playback (DAC) | Capture (ADC), as shipped | Capture (ADC), MIC PLL Adjust on |
|---|---|---|---|
| Board 20000002 | -135 ppm | +380 to +393 ppm | -135 to -144 ppm |
| Board 20000005 | -135 ppm | +353 to +391 ppm | -134 to -137 ppm |

The playback figure is the Raspberry Pi's USB clock. As shipped, every link between two of these boards therefore carries a fixed **mismatch of about 520 ppm** between the sending card's DAC and the receiving card's ADC. That is invisible to AFSK, tone tests and level measurements, but it is fatal to OFDM: across a 0.9 s burst it is 22 samples of drift. On this bench, ofdm-fm decoded nothing live and 1 frame in 3 offline before the change.

With bit 4 of EEPROM word 0x2B ("MIC PLL Adjust") set, the capture clock locks to the USB timing too, and both directions decode every frame (see [ofdm-fm](#ofdm-fm)). On two boards on the same host the mismatch is then zero; on two different hosts it is the difference between their USB clocks, typically tens of ppm.

- The change is one EEPROM word: **0x2B from 7A02 to 7A12**. Both bench boards now carry it.
- It takes effect only after a power-cycle of the board (unplug and replug the USB). A USB reset is not enough.
- For the first minute or so after power-up the capture clock is still settling (0.48 rad of phase wander on a 10 s tone, against about 0.1 rad once settled).
- Recommended for every tait-cm108 board, and worth programming into the EEPROM at manufacture.

## CM108B EEPROM

Both boards' EEPROMs read identically apart from the serial number ([data/eeprom-board-20000002.txt](data/eeprom-board-20000002.txt), [data/eeprom-board-20000005.txt](data/eeprom-board-20000005.txt) are as shipped; 64 words from address 0x00). The only change made is the MIC PLL Adjust bit above.

| Item | Value |
|---|---|
| VID:PID | 0D8C:0012 |
| Product / manufacturer / serial | "TaitCM108" / "M9TWM" / board serial |
| Mic input high-pass filter | **off** (good for 9600 and other low-frequency modes) |
| Mic boost | **off** (boost mode field set to 12 dB but not enabled) |
| MIC PLL Adjust | **off as shipped; turn it on** (word 0x2B bit 4) |
| DAC (output) volume range | -37 dB to 0 dB |
| ADC (input) volume range | -12 dB to +23 dB |

Reading and writing the EEPROM goes over the CM108B's HID interface, the same one that carries PTT: an output report `[0x80, lo, hi, 0x80|addr]` reads a word (it comes back in input report bytes 1 and 2) and `[0x80, lo, hi, 0xC0|addr]` writes one. The scripts used are in [tools/](tools/).

**The EEPROM cannot add transmit level.** The CM108B's output volume control is an attenuator, 0 dB at most, and full-scale output is already about 1 V rms into 10 kohm. Extra deviation has to come from the board's output divider or the tap point.

Start-up mixer levels are best set on the host. On Linux, set output 0 dB, input as wanted, AGC off, then `sudo alsactl store` so they are restored whenever the card re-enumerates (otherwise the output came back at -20 dB).

## Two hosts

From 15 November the bottom radio (19925328, board 20000005) is on its own Raspberry Pi 4 (radio2, no undervoltage reported: `vcgencmd get_throttled` 0x0), and the top radio stays on radio1. Same pdn-soundmodem 0.108.0 configuration on each.

**USB clocks of the two Pis**, measured as above (playback against the RSP1, and capture through the radios), three runs each way:

| | Playback (DAC) | Capture (ADC) |
|---|---|---|
| radio1 (board 20000002) | -135 to -138 ppm | -134 to -138 ppm |
| radio2 (board 20000005) | -130 ppm | -130 to -131 ppm |

So with MIC PLL Adjust on, each card runs on its own host's USB clock, both directions, and this pair of hosts is only **about 5 ppm apart**. That is luck: it says nothing about other pairs of computers.

**ofdm-fm across the two hosts** (`ofdm-fm-8k`, 1024 B frames, 10 per run): bottom to top 4, 8 and 8 of 10; top to bottom 9, 9 and 9 of 10. Slightly below the single-host 10/10.

**Tolerance to clock mismatch, measured offline:** 20 real `ofdm-fm-8k` bursts (1024 B) recorded from radio2 at radio1's card, resampled by a chosen offset with sox (`speed`), and decoded with `pdn-soundmodem --wav`. The unaltered recording was already marginal (7/20), which makes it a sensitive test:

| Offset | -300 | -200 | -100 | -50 | -25 | 0 | +25 | +50 | +100 | +200 | +300 ppm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Frames decoded of 20 | 2 | 3 | 6 | 10 | 9 | 7 | 8 | 9 | 9 | 6 | 2 |

Within about plus or minus 100 ppm the count stays within the run-to-run spread; beyond that it falls, and at 300 ppm almost nothing decodes. Two hosts 100 to 200 ppm apart are ordinary, so station-side rate correction (pdn-soundmodem #809) is worth having.

## Hardware change: decision

**Decision: change R11 from 3k3 to 2k0 on both boards.**

The output path is CM108B line out, C29, then a divider of R11 (series, 3k3) and R12 (shunt, 1k), then C30 into the radio's AUD_TAP_IN. That divides by 4.3. On T12 it lands full scale at about 62% of the channel maximum (1.54 kHz on Narrow, 3.1 kHz on Wide, average of the two boards), and the sound card has nothing left to give.

Changing **R11** alone moves the ceiling (figures scaled from the measurements above, T12):

| R11 | Divider | Full scale, Narrow | Share of maximum | Full scale, Wide |
|---|---|---|---|---|
| 3k3 (fitted) | /4.3 | 1.54 kHz | 62% | 3.08 kHz |
| 2k2 | /3.2 | 2.07 kHz | 83% | 4.14 kHz |
| **2k0** | **/3.0** | **2.21 kHz** | **88%** | **4.41 kHz** |
| 1k8 | /2.8 | 2.37 kHz | 95% | 4.73 kHz |

Why:

- **Deviation is what sets the link quality here.** The receiver is fully quieted, so post-detection SNR goes up with deviation (shown by the tone tests and the multitone test).
- **For ofdm-fm, 3 dB of drive is decisive at the margin**: dropping the drive 3 dB on `ofdm-fm-8k-r78` took one direction from 20/60 to 2/60 frames. R11 = 2k0 adds 3.1 dB at full scale, the same step the other way.
- **Software cannot do it**: the CM108B output is at its 0 dB maximum and the EEPROM cannot raise it.
- **T13 is not an alternative for ofdm-fm**, which runs on Wide: T13 would give 2.44 kHz there, less than T12 does now.
- **Why not more**: T12 has no limiter, so the audio level is the only guard against over-deviating. 2k0 keeps a sine at full scale at 88% of the class and leaves about 1 dB of margin, which covers the 0.4 dB between the two boards. OFDM's peaks are bounded by the DAC's full scale, so they also stay under 88%. 1k8 would leave too little.
- With 2k0 the load on the CM108B line output is 3 kohm, between the 10 kohm and 32 ohm loads it is specified for, and the coupling corners stay below 6 Hz.

After the change, re-measure full-scale deviation on each radio (the table is a scaling, not a measurement), then repeat the r78 test above. The earlier ofdm-fm bench made the equivalent change (to 82% of class) and measured about 7 dB of link SNR from it, so the gain should be clear.

## Open questions

- Why the 19925328 receive direction is weaker at the ofdm-fm margin.
- Source of the 3.89 kHz spur in 19925328's receiver (radio or board; swapping the boards between radios would tell).
- Source of the -36 dBc third harmonic on receive.
- **Sample-clock offset between stations on different computers.** MIC PLL Adjust locks each card to its own host's USB clock, so the mismatch between two stations becomes the difference between their hosts' clocks. This Pi's is -135 ppm; two hosts 100 to 200 ppm apart are ordinary. pdn-soundmodem's ofdm-fm already corrects a sample-clock tilt per burst, but its own notes record dense constellations struggling at 100 ppm and failing at 200 ppm. The single-carrier modems track clock error to 500 ppm or more. Not yet tested with two hosts.
- Whether the CM108B's capture clock wander after MIC PLL Adjust (about plus or minus 50 ppm) limits the denser OFDM presets.
- Best CM108 input gain for the modems.
