# Tait TM8110 + tait-cm108: bench factsheet

What we know so far about a pair of Tait TM8110 radios fitted with the [packethacking/tait-cm108](https://github.com/packethacking/tait-cm108) internal options board, measured on the bench on 14 and 15 November 2026. Facts and figures only. The scripts that produce them are in [tools/](tools/), with a how-to in [tools/README.md](tools/README.md). The main figures were re-measured on 15 November with those scripts as a check; where a re-measurement changed something, the text says so.

**Headline:**

1. **Set the CM108B's "MIC PLL Adjust" EEPROM bit on every board.** As shipped, the capture clock runs about 520 ppm away from the playback clock, and ofdm-fm in pdn-soundmodem 0.108.0 decodes nothing. One EEPROM word removes the offset. It has a cost: the capture clock then wanders about four times more within a burst than it did. See [CM108B sample clock](#cm108b-sample-clock).
2. **Change R11 from 3k3 to 2k0.** With the transmit tap on T12 (which we want, so levels carry across wide and narrow channels) the board's output divider limits full-scale deviation to about 62% of the channel maximum. On the densest ofdm-fm preset 3 dB of drive is worth a great deal, measured twice. See [Hardware change: decision](#hardware-change-decision).
3. Otherwise the boards work as built: both ways, linear, matched to within 0.4 dB, flat audio from 30 Hz to about 5 kHz. Every tone, level and response figure here repeated on re-measurement.
4. **ofdm-fm frame counts on this bench move with time more than with most things you might change.** `ofdm-fm-8k` went from 60% to 100% delivery and back within the hour with nothing touched. Compare settings only in interleaved rounds. See [ofdm-fm](#ofdm-fm).

## The bench

| | |
|---|---|
| Radios | 2 x Tait TM8110 (TMAB12-B100): serial 19925328 on firmware QMA1F 02.19.00.03, codeplug database 0095; serial 19925369 on 02.18.00.00, database 0094 |
| Interface | tait-cm108 board on each radio's internal options connector, USB to a Raspberry Pi 4. One Pi for both until 15 November, then one Pi each (see [Two hosts](#two-hosts)) |
| Channel | 146.500 MHz, power Very Low (1 W). Narrow (12.5 kHz) for the first tone and level measurements on 14 November; **Wide (25 kHz) since**, for everything else, and how both radios are left |
| RF path | radio, 6 dB (5 W) pad, 100 dB pad, 6 dB (5 W) pad, radio: 112 dB in total |
| Signal at the receiver | -80.5 dBm (radio's own RSSI), against an idle floor of about -128 dBm |
| Deviation measured with | SDRplay RSP1 on a stubby antenna near the radios, FM-demodulated in software (28 to 36 dB SNR in channel). Cross-checked on 15 November against the FM sideband amplitudes of a steady tone, which needs no demodulator: the two methods agree within 0.2% |

Each board appears on USB as a hub with three devices: a CM108B sound card ("TaitCM108"), a CP2102N "TaitInterface" serial port (the radio's internal serial port, IOP_TXD/RXD), and a CP2102N "TaitProgramming" serial port. Board serial numbers are 20000002 (on radio 19925369, the "top" radio) and 20000005 (on radio 19925328, the "bottom" radio).

**Device names.** Linux numbers sound cards and hidraw nodes in the order they appear, so a board that re-enumerates can come back under another name (it happened: see [USB drop-out](#usb-drop-out)). Both Pis now carry [tools/99-tait-cm108.rules](tools/99-tait-cm108.rules), which names each board by its serial number: ALSA card `Tait20000002` and PTT `/dev/tait-ptt-20000002`, and likewise for 20000005. The modem configurations use those names.

### RSP1 on a tee (from 13:40 UTC on 15 November)

The RSP1 moved from its stubby antenna to a tee at the midpoint of the attenuator chain, behind a 20 dB pad of its own. Changed nothing else, then re-measured:

| | Off the stubby | On the tee |
|---|---|---|
| Signal at each receiver (radio's RSSI) | -80.5 dBm | **-83.7 and -84.0 dBm** |
| RSP1 signal to noise in the channel | 28 to 36 dB | **48 dB** (gain `IFGR=36,RFGR=0`) |
| Residual on a measured tone | 130 to 160 Hz rms | 17 to 60 Hz rms |
| Full-scale deviation, top / bottom radio | 3.083 / 3.034 kHz | 3.085 / 3.033 kHz |
| Transmit second plus third harmonic at full scale | -48 dBc (noise-limited) | -54 dBc |
| Level of the two radios at the RSP1 | | equal within 0.6 dB |
| Received audio level, full-scale tone | -25.9 dBFS rms | -25.9 dBFS rms |
| Receive noise under a carrier, 300 Hz to 1 kHz | -105 dBFS/Hz | -105 dBFS/Hz |
| Receive noise under a carrier, 1 to 8 kHz | -105 to -110 dBFS/Hz | **2 to 3 dB higher** |
| `ofdm-fm-8k` burst | 0.70 kHz rms, 2.9 kHz peak | 0.69 kHz rms, **2.65 kHz peak** |
| `ofdm-fm-8k-r78`, 1900 B, drive 0 dB | 72/80 and 29/80 | **19/80 and 4/80** |

- **As a measuring point it is much better**, and it agrees with the stubby on everything the stubby could measure. The burst peak is lower because the old figure had the stubby's noise riding on it; 2.65 kHz (53% of the 5 kHz maximum, crest 11.7 dB) is the better number.
- **The tee takes 3.5 dB out of the main path, and that is not free.** Audio noise above 1 kHz rose 2 to 3 dB and the rate 7/8 preset lost most of its frames. So at -80 dBm the receivers are **not** fully quieted above 1 kHz: the upper carriers' noise still follows the RF level. Figures taken before and after the tee are not comparable for the modems until about 3.5 dB of attenuation is taken out elsewhere.

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

**T12, Narrow** (14 November):

| Sound card level | Radio 19925369 | Radio 19925328 |
|---|---|---|
| -20 dBFS | 0.16 kHz | 0.15 kHz |
| -14 dBFS | 0.31 kHz | 0.30 kHz |
| -10 dBFS | 0.50 kHz | 0.48 kHz |
| -6 dBFS | 0.78 kHz | 0.76 kHz |
| -3 dBFS | 1.11 kHz | 1.07 kHz |
| 0 dBFS | **1.57 kHz** | **1.51 kHz** |

**T12, Wide** (15 November, the current configuration):

| Sound card level | Radio 19925369 | Radio 19925328 |
|---|---|---|
| -20 dBFS | 0.31 kHz | 0.31 kHz |
| -14 dBFS | 0.62 kHz | 0.61 kHz |
| -10 dBFS | 0.97 kHz | 0.96 kHz |
| -6 dBFS | 1.54 kHz | 1.52 kHz |
| -3 dBFS | 2.18 kHz | 2.15 kHz |
| 0 dBFS | **3.08 kHz** | **3.03 kHz** |

The sideband method gives 3.09 and 3.04 kHz at 0 dBFS.

**Tap and channel width compared** (radio 19925369, 14 November):

| Configuration | Full scale (0 dBFS) | Share of channel maximum |
|---|---|---|
| T12, Narrow | 1.57 kHz | 63% of 2.5 kHz |
| T12, Wide | 3.13 kHz (3.08 kHz on 15 November) | 63% of 5 kHz |
| T13, Narrow | 2.44 kHz | 97% of 2.5 kHz |
| T13, Wide | 2.44 kHz (unscaled, not measured) | 49% of 5 kHz |

- **Linear:** deviation follows level to within 0.05 dB over the whole range, on both radios.
- **T12 Wide is exactly twice T12 Narrow** (6.0 dB), as the tap position predicts.
- **T13 is 3.8 dB more sensitive than T12** on a narrow channel.
- **Clean:** second plus third harmonic -47 dBc at full scale on Narrow, -48 to -52 dBc on Wide. Residual FM about 30 Hz rms.
- **Matched:** the two radio and board pairs are within 0.4 dB of each other on Narrow and 0.15 dB on Wide.
- **Against Tait's figures:** the board puts about 0.66 V peak to peak on the tap at full scale (1 V rms through the 4.3 divider), so T12 on Wide measures 0.21 V p-p per kHz against Tait's published 0.23, and T13 0.27 against 0.29. Both are 0.6 dB more sensitive than the book.
- Carriers were within 10 Hz of each other, 2 Hz on 15 November (absolute frequency not measured; the RSP1 was not calibrated).

**What a real ofdm-fm burst deviates to** (15 November, Wide, `ofdm-fm-8k`, modem drive at its default, measured off air in both directions): **0.69 kHz rms, peaks of 2.65 kHz (53% of the 5 kHz maximum), crest factor 11.7 dB** (the cleaner measurement on the tee; off the stubby the peak read 2.9 kHz with noise on it). The modem's peaks reach 87% of what a full-scale sample gives (3.06 kHz), and its average sits 12.9 dB below a full-scale sine. Keep this in mind wherever a sine figure is quoted: the sine is the ceiling, the burst is what the link runs on.

## Receive

Receiving radio on R2, CM108 input at -12 dB (its minimum), AGC off. Narrow on 14 November, Wide on 15 November.

| | |
|---|---|
| Open channel, no carrier | -19 to -21 dBFS rms, peaks -11 to -12 dBFS (unsquelched discriminator noise) |
| Full-scale tone from the far board (1.57 kHz on Narrow, 3.06 kHz on Wide) | **-25.9 dBFS rms** on either width |
| 1 kHz tone at 1 kHz peak deviation | -29.6 dBFS rms on Narrow, -35.6 dBFS rms on Wide |
| Linearity | received level tracks transmitted level within 0.1 dB over the whole ladder, both widths |
| Third harmonic in received audio | -34 to -36 dBc at the top of the ladder, both widths |

SINAD (300 Hz to 3 kHz) against deviation, 1 kHz tone:

| Sound card level | Deviation on Wide | SINAD on Wide |
|---|---|---|
| -20 dBFS | 0.31 kHz | 28 dB |
| -14 dBFS | 0.61 kHz | 34 dB |
| -10 dBFS | 0.97 kHz | 37 to 38 dB |
| -6 dBFS | 1.53 kHz | **40 dB** |
| -3 dBFS | 2.16 kHz | 39 to 40 dB |
| 0 dBFS | 3.06 kHz | 37 to 38 dB |

On Narrow it rose all the way up the ladder, from 22 dB at 0.16 kHz to 38 dB at 1.54 kHz.

- **R2 normalises to the channel.** The received level follows the share of the channel's maximum deviation, not the kHz: the same sound card level gives the same received level on Narrow and Wide, and 1 kHz of deviation reads 6 dB lower on Wide than on Narrow.
- **Up to about 1.5 kHz of deviation, more deviation means better SINAD, dB for dB.** At -80 dBm the receiver is quieted enough that the 300 Hz to 3 kHz SINAD barely moves with signal level, but not fully: 3.5 dB less signal raised the noise above 1 kHz by 2 to 3 dB (see [RSP1 on a tee](#rsp1-on-a-tee-from-1340-utc-on-15-november)).
- **Above about 1.5 kHz of deviation, receive-side distortion takes over.** On Wide the SINAD peaks at 40 dB and then falls, as the third harmonic rises from below -45 dBc to -34 dBc at 3 kHz. The harmonic is not in the transmitted signal (which is -48 dBc), so it arises in the receiver. The September ofdm-fm bench (TM8110s through a different CM108 interface) saw the same and put it down to the IF filter clipping the edges of a widely deviated signal. So on a strong signal like this bench's, extra deviation beyond about 1.5 kHz does not make the audio cleaner. On a weak signal, where noise is the limit, it still would.
- **Leave the CM108 input gain at -12 dB.** A full-scale tone from the far end arrives at only -25.9 dBFS rms, but that costs nothing: with the input gain 10 dB higher, signal, noise floor and SINAD all moved by exactly 10 dB, so the sound card's own noise is nowhere near the radio's. At +10 dB the open-channel noise peaks reach -1.4 dBFS, so there is nothing to gain and clipping to lose.

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
- **Receive is flat within 0.1 dB from 30 Hz to 4 kHz, then rolls off: -3 dB at about 6.6 kHz, -6 dB at 7.6 kHz, -10 dB at 8.8 kHz.** The roll-off is the radio's: the board's input network has no corner below 100 kHz by its component values, and the September ofdm-fm bench measured the same shape (-3 dB at 6.3 kHz, -6 dB at 7.4 kHz) through different interface hardware. It costs the top carriers of `ofdm-fm-8k` (which reaches 8 kHz) about 6 dB. Measured on Wide only; a Narrow channel's narrower IF filter will roll off sooner.
- **The two radios match within 0.3 dB** everywhere, in both directions.

## Noise, spurs and signal quality across the band

**Noise floor** (unchanged within 0.5 dB between mains and battery power) under an unmodulated carrier (receive audio, CM108 input at -12 dB) is about -110 dBFS/Hz below 100 Hz, -105 dBFS/Hz from 100 Hz to 1 kHz, -109 dBFS/Hz from 1 to 3 kHz and -104 to -105 dBFS/Hz from 4 to 8 kHz, the same on both receivers. Against a tone at 1 kHz peak deviation on Wide (-35.6 dBFS rms, less the receive roll-off above 4 kHz) that is 43 to 56 dB in a 100 Hz bandwidth across 30 Hz to 8 kHz. Re-measured on 15 November across the two hosts: the same within 2 dB in every band.

**Spurs:**

- **Radio 19925328's receiver has a tone at about 3.89 kHz** (drifting 3882 to 3902 Hz), 26 dB above the noise around it: about -76 dBFS, the equivalent of 9 Hz of deviation. It is not on the other radio's transmission (checked with the RSP1) and not caused by the RSP1. The other receiver does not have it. **It belongs to the radio, not the board**: after the boards swapped radios in the R11 rework it stayed with radio 19925328 (at 4.05 kHz, 23 dB above the noise, 2026-11-17), and radio 19925369 showed none with the board that had been in the spurred radio. It is not the programming lead that was in that radio's mic socket, nor the power supply: it is unchanged with the lead unplugged and with the radios on battery (-78 dBFS/Hz at its peak either way).
- **Radio 19925328's transmitter carried a 100 Hz buzz on mains power** with harmonics to about 2.7 kHz: 5 to 7 Hz peak deviation per harmonic, 14 Hz rms in total (11.8 Hz rms with the mic-socket programming lead unplugged). **On battery it falls to 6 Hz rms**, about the measurement floor and level with the other radio (4.4 Hz rms), so it came from the mains supply. Residual FM between 300 Hz and 3 kHz also fell on battery: 23 to 17 Hz rms on that radio, 18 to 12 Hz rms on the other.
- Both receivers show small tones near 1 kHz and 4 kHz, about 10 dB above the noise, probably USB frame-rate pickup on the boards. Minor.

**Signal quality with an OFDM-like signal** (84 tones from 211 Hz to 8 kHz, random phases, gaps between them; tone power against what fills the gaps, at the receiving card). Both directions measured within 1 to 2 dB of each other:

| Drive (rms) | 0.2 to 1 kHz | 1 to 2 kHz | 2 to 3 kHz | 4 to 5 kHz | 5 to 6 kHz | 7 to 8 kHz |
|---|---|---|---|---|---|---|
| -12 dBFS | 39 to 40 dB | 38 dB | 33 to 35 dB | 29 to 30 dB | 27 to 28 dB | 24 to 25 dB |
| -18 dBFS | 34 to 35 dB | 39 dB | 37 dB | 32 to 33 dB | 31 dB | 27 to 28 dB |

Re-measured on 15 November across the two hosts, every cell within 1.5 dB of this table.

- Quality falls steadily with frequency, by about 15 dB across the band.
- **Lowering the drive 6 dB makes every band above 1 kHz better, by 1 to 4 dB,** and only the band below 1 kHz worse. So above 1 kHz distortion, not noise, sets the quality at these levels.
- -12 dBFS rms is almost exactly where a real `ofdm-fm-8k` burst sits (-12.8 dBFS rms), so the top row is the modem's operating point today.
- The method understates distortion: with tones on every fourth bin, the largest third-order products land on the tones themselves, not in the gaps this measures. Treat the figures as upper bounds.

This is the budget an OFDM modem has to work within on this bench.

## ofdm-fm

pdn-soundmodem 0.108.0, one instance per radio, both radios on Wide. Carrier sense from each radio's own CCDI RSSI (busy above -110 dBm). KISS channel access set by the test harness before every run on both stations: **persistence 255, slot time 10 ms, TXDELAY 50 ms, TXTAIL 50 ms**, so no random back-off. Frames are AX.25 UI, counted byte-identical at the far KISS port. "Drive" is the station's playback level, 0 dB being the sound card's maximum.

### One Pi, night of 14 to 15 November

**Before MIC PLL Adjust** nothing decoded live in either direction, on any preset including `ofdm-fm-narrow`. Offline decoding of a recording got 1 frame in 3.

**After MIC PLL Adjust:**

| Preset, frame size | Bottom to top | Top to bottom |
|---|---|---|
| `ofdm-fm-narrow`, 256 B | 10/10, 2.0 kbit/s | 10/10, 2.0 kbit/s |
| `ofdm-fm-8k`, 1024 B | 10/10, 16.1 kbit/s | 10/10, 16.0 kbit/s |
| `ofdm-fm-8k-r78`, 1900 B, full drive | 57/60 | 20/60 |
| `ofdm-fm-8k-r78`, 1900 B, drive 3 dB lower | 53/60 | 2/60 |

(The r78 rows are three alternating runs of 20 frames at each drive, interleaved.)

### Two Pis, afternoon of 15 November

**`ofdm-fm-8k-r78`, 1900 B, four interleaved rounds of 20 frames:**

| Drive | Bottom to top | Top to bottom |
|---|---|---|
| 0 dB | 72/80 | 29/80 |
| -3 dB | 63/80 | 1/80 |

**`ofdm-fm-8k`, 1024 B, interleaved rounds of 20 frames:**

| Drive | Bottom to top | Top to bottom |
|---|---|---|
| 0 dB | 77/80 | 66/80 |
| -2 dB | 78/80 | 63/80 |
| -4 dB | 71/80 | 51/60 |
| -6 dB | 57/60 | 50/60 |

**The same preset over the same hour, drive 0 dB, nothing changed between runs** (frames of 20):

| Time (UTC) | Bottom to top | Top to bottom |
|---|---|---|
| about 12:07 | 12, 13, 14 | 19, 16, 20 |
| 12:15 to 12:25 | 17, 20 | 19, 20 |
| 12:30 to 12:45 | 20, 20 | 14, 13 |

What this says:

- **On `ofdm-fm-8k-r78` drive matters a great deal, and it repeats.** 3 dB less drive took the weak direction from 29/80 to 1/80 here and from 20/60 to 2/60 the night before. This preset is at the edge on this bench, which makes it the sensitive test.
- **On `ofdm-fm-8k` drive does not matter over a 6 dB range.** Its losses come and go with time instead: a direction can sit at 60 to 70% for some minutes and then deliver everything. The cause is not known. It is not audio dropouts (the modems logged none), not the average clock rate (3 to 15 ppm apart throughout), and not a change in the analogue path (the multitone, level and response figures taken that afternoon match the night before's).
- **These two do not obviously agree with the multitone test,** which says that above 1 kHz less drive gives a cleaner signal. Not reconciled.
- **The two directions are not equal at the margin, and the weakness follows the radios, not the computer.** Top to bottom (received by radio 19925328) is the weak direction on r78 on one Pi and on two. Tone tests, frequency response and the multitone test are all symmetric, so the difference is something those do not see. Candidates: the 3.89 kHz spur in that receiver (though notching it out offline made decoding worse, not better, because the notch costs more carriers than the spur does), and clock wander (below).
- `ofdm-fm-8k` at its best reaches 16.8 kbit/s at 1024 B. The September ofdm-fm bench reported 17.5 kbit/s with about 2.5 dB more deviation.
- **The modem reports nothing about a frame it fails to decode,** and no signal-to-noise figure for the ones it does (the frame log and the metrics carry none for ofdm-fm). Delivered counts are the only live measure, which is why the tables above are all there is.

## CM108B sample clock

**Set MIC PLL Adjust. It is needed for ofdm-fm as the modem stands, and it needs no hardware change. But read the wander table.**

As shipped, each board's CM108B plays back locked to the host's USB timing, but its capture (ADC) clock runs free. Measured against the RSP1 (whose own error is about 1 ppm, from the Tait carriers), with a 1 kHz tone through the radios:

| | Playback (DAC) | Capture (ADC), as shipped | Capture (ADC), MIC PLL Adjust on |
|---|---|---|---|
| Board 20000002 | -135 ppm | +380 to +393 ppm | -134 to -145 ppm |
| Board 20000005 | -135 ppm (-130 on its own Pi) | +353 to +391 ppm | -130 to -137 ppm |

The playback figure is the Raspberry Pi's USB clock. As shipped, every link between two of these boards therefore carries a fixed **mismatch of about 520 ppm** between the sending card's DAC and the receiving card's ADC. That is invisible to AFSK, tone tests and level measurements, but across a 0.9 s burst it is 22 samples of drift, and ofdm-fm decoded nothing live.

With bit 4 of EEPROM word 0x2B ("MIC PLL Adjust") set, the capture clock follows the USB timing too, and ofdm-fm decodes (see [ofdm-fm](#ofdm-fm)). The mismatch is then the difference between the two hosts' USB clocks, 3 to 15 ppm on this pair of Pis.

- The change is one EEPROM word: **0x2B from 7A02 to 7A12**. Both bench boards now carry it.
- It takes effect only after a power-cycle of the board (unplug and replug the USB). A USB reset is not enough.
- For the first minutes after power-up the capture clock is still settling, with swings of several hundred ppm. Let a board settle before testing.

**Wander within a burst.** The averages above hide what the clocks do second by second. From one 1 kHz transmission, the RSP1 gives the sending card's playback timing and the receiving card's audio gives playback and capture together, so the two can be separated. Figures are the worst peak-to-peak timing excursion in any 1.5 s (about one long burst) after removing that stretch's own average rate, which is what a per-burst rate correction leaves behind. One sample at 48 kHz is 21 microseconds; 40 microseconds is 2 radians of phase at 8 kHz.

| | As shipped (4 runs, one Pi) | MIC PLL Adjust on (10 runs, one Pi and two) |
|---|---|---|
| Playback clock, sending card | 23 to 24 microseconds | 21 to 26 microseconds (one run 44) |
| Capture clock, receiving card | 7 to 11 microseconds | **33 to 61 microseconds** |
| End to end | 24 to 26 microseconds | 27 to 52 microseconds |
| Average mismatch, end to end | 516 to 528 ppm | 0 to 15 ppm |

- **The playback clock has always wobbled by one sample.** It steps back and forth about once a second as the chip follows the USB frame timing. MIC PLL Adjust does not affect it.
- **As shipped, the capture clock is steady:** off by a large but fixed amount.
- **With MIC PLL Adjust on, the capture clock hunts,** swinging 20 to 40 microseconds either way over a second or two. It is now the larger of the two wobbles.
- So the fix trades a large fixed error, which software could remove exactly by resampling, for a small moving one, which it cannot remove without tracking it. pdn-soundmodem's ofdm-fm corrects one constant rate per burst (and tries a per-symbol refinement); neither clock behaves like one constant rate. Whether this is what limits the dense presets, or causes the come-and-go losses on `ofdm-fm-8k`, is not established.
- An alternative worth testing: leave the capture clock free-running and have the modem resample by the measured offset (pdn-soundmodem #809 is the place for that discussion).

## CM108B EEPROM

Both boards' EEPROMs read identically apart from the serial number ([data/eeprom-board-20000002.txt](data/eeprom-board-20000002.txt), [data/eeprom-board-20000005.txt](data/eeprom-board-20000005.txt) are as shipped; 64 words from address 0x00). The only change made is the MIC PLL Adjust bit above.

| Item | Value |
|---|---|
| VID:PID | 0D8C:0012 |
| Product / manufacturer / serial | "TaitCM108" / "M9TWM" / board serial |
| Mic input high-pass filter | **off** (good for 9600 and other low-frequency modes) |
| Mic boost | **off** (boost mode field set to 12 dB but not enabled) |
| MIC PLL Adjust | **off as shipped; turn it on** (word 0x2B bit 4) |
| DAC (output) volume range | -37 dB to 0 dB in the EEPROM; ALSA shows -36 dB to 0 dB in 1 dB steps, muting below |
| ADC (input) volume range | -12 dB to +23 dB |

Reading and writing the EEPROM goes over the CM108B's HID interface, the same one that carries PTT: an output report `[0x80, lo, hi, 0x80|addr]` reads a word (it comes back in input report bytes 1 and 2) and `[0x80, lo, hi, 0xC0|addr]` writes one. The scripts used are in [tools/](tools/).

**The EEPROM cannot add transmit level.** The CM108B's output volume control is an attenuator, 0 dB at most, and full-scale output is already about 1 V rms into 10 kohm. Extra deviation has to come from the board's output divider or the tap point.

Start-up mixer levels are best set on the host. On Linux, set output 0 dB, input -12 dB, AGC off, then `sudo alsactl store` so they are restored whenever the card re-enumerates (otherwise the output came back at -20 dB). The stored state is keyed by card name, so store it again after installing the udev rules. pdn-soundmodem also sets all three itself at start-up when its configuration has an `alsa.mixer` section, as the bench stations' do.

## Two hosts

From 15 November the bottom radio (19925328, board 20000005) is on its own Raspberry Pi 4 (radio2, no undervoltage reported: `vcgencmd get_throttled` 0x0), and the top radio stays on radio1, which also carries the RSP1. Same pdn-soundmodem 0.108.0 configuration on each: station `tait-top` on radio1 (KISS port 8115, page 8117) and `tait-bottom` on radio2 (KISS 8105, page 8107), both left on `ofdm-fm-8k`.

**USB clocks of the two Pis**, measured as above (playback against the RSP1, and capture through the radios), three runs each way:

| | Playback (DAC) | Capture (ADC) |
|---|---|---|
| radio1 (board 20000002) | -135 to -138 ppm | -134 to -145 ppm |
| radio2 (board 20000005) | -130 ppm | -130 to -131 ppm |

So with MIC PLL Adjust on, each card runs on its own host's USB clock, both directions, and this pair of hosts is only **3 to 15 ppm apart** (the capture side moves around by several ppm from run to run). That is luck: it says nothing about other pairs of computers.

**ofdm-fm across the two hosts** (`ofdm-fm-8k`, 1024 B frames, 10 per run, late morning): bottom to top 4, 8 and 8 of 10; top to bottom 9, 9 and 9 of 10. The afternoon's longer runs are under [ofdm-fm](#ofdm-fm): delivery came and went with time, so these short runs cannot say whether two hosts are worse than one.

**Tolerance to clock mismatch, measured offline:** 20 real `ofdm-fm-8k` bursts (1024 B) recorded from radio2 at radio1's card, resampled by a chosen offset with sox (`speed`), and decoded with `pdn-soundmodem --wav`. The unaltered recording was already marginal (7/20), which makes it a sensitive test:

| Offset | -300 | -200 | -100 | -50 | -25 | 0 | +25 | +50 | +100 | +200 | +300 ppm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Frames decoded of 20 | 2 | 3 | 6 | 10 | 9 | 7 | 8 | 9 | 9 | 6 | 2 |

Within about plus or minus 100 ppm the count stays within the run-to-run spread; beyond that it falls, and at 300 ppm almost nothing decodes. Two hosts 100 to 200 ppm apart are ordinary, so station-side rate correction (pdn-soundmodem #809) is worth having.

### USB drop-out

Once in about 14 hours of use, at 12:46 UTC on 15 November during a run of transmissions, board 20000002's CM108B alone dropped off the USB bus and came straight back (the board's hub and serial ports stayed up). It returned under a different card name and hidraw number, the station could not find it, and its service restarted in a loop until the names were pinned (see [The bench](#the-bench)). Cause unknown; RF from the radio beside it is the obvious suspect. Radio1's kernel also logs an xHCI "transfer event for disabled endpoint" error each time an audio stream on that board opens or closes, which looks harmless.

## Hardware change: decision

**Decision: change R11 from 3k3 to 2k0 on both boards.** Not yet done as of 15 November.

The output path is CM108B line out, C29, then a divider of R11 (series, 3k3) and R12 (shunt, 1k), then C30 into the radio's AUD_TAP_IN (values checked against the board's schematic). That divides by 4.3. On T12 it lands full scale at about 62% of the channel maximum (1.54 kHz on Narrow, 3.06 kHz on Wide, average of the two boards), and the sound card has nothing left to give.

Changing **R11** alone moves the ceiling (figures scaled from the measurements above, T12):

| R11 | Divider | Full scale, Narrow | Share of maximum | Full scale, Wide | `ofdm-fm-8k` burst on Wide, rms / peak |
|---|---|---|---|---|---|
| 3k3 (fitted) | /4.3 | 1.54 kHz | 62% | 3.06 kHz | 0.69 / 2.65 kHz (measured) |
| 2k2 | /3.2 | 2.07 kHz | 83% | 4.11 kHz | 0.93 / 3.6 kHz |
| **2k0** | **/3.0** | **2.21 kHz** | **88%** | **4.39 kHz** | **0.99 / 3.8 kHz** |
| 1k8 | /2.8 | 2.37 kHz | 95% | 4.70 kHz | 1.06 / 4.1 kHz |

Why:

- **For the densest ofdm-fm preset, 3 dB of drive is decisive at the margin**, measured twice, on one Pi and on two: dropping the drive 3 dB on `ofdm-fm-8k-r78` took the weak direction from 20/60 to 2/60 frames and then from 29/80 to 1/80. R11 = 2k0 adds 3.1 dB at full scale, the same step the other way.
- **Software cannot do it**: the CM108B output is at its 0 dB maximum, the EEPROM cannot raise it, and the modem's bursts already peak at 87% of the sound card's range.
- **T13 is not an alternative for ofdm-fm**, which runs on Wide: T13 would give 2.44 kHz there, less than T12 does now.
- **On a weak signal every mode gains.** Even at -80 dBm the upper audio band's noise follows the RF level. On a real path nearer the noise, recovered audio signal-to-noise goes up dB for dB with deviation, and 62% of the channel is 4 dB given away.
- **Why not more**: T12 has no limiter, so the audio level is the only guard against over-deviating. 2k0 keeps a sine at full scale at 88% of the class and leaves about 1 dB of margin, which covers the 0.4 dB between the two boards. OFDM's peaks are bounded by the DAC's full scale, so they also stay under 88%. 1k8 would leave too little.
- With 2k0 the load on the CM108B line output is 3 kohm, between the 10 kohm and 32 ohm loads it is specified for, and the coupling corners stay below 6 Hz.

What the evidence does not promise:

- **`ofdm-fm-8k` showed no benefit from drive** between -6 and 0 dB, so the change may do nothing for the standard preset.
- **Receive distortion rises with deviation.** A sine above about 1.5 kHz of deviation on Wide gets no cleaner at this signal level, and the multitone test says the band above 1 kHz is already distortion-limited at today's drive. The modem's drive may want re-tuning downward for some presets once the ceiling is higher. The change gives that choice to software; today there is none.
- The September ofdm-fm bench gained about 7 dB of link signal-to-noise from raising deviation, but that was for a 7 dB step (37% to 82% of class), not a 3 dB one.

After the change, re-measure with the scripts in [tools/](tools/): the deviation ladder on each radio (the table is a scaling, not a measurement), the burst deviation, then `ofdm-fm-8k-r78` at drive 0, -3 and -6 dB and `ofdm-fm-8k` at 0 and -6 dB, in interleaved rounds. If the scaling holds, r78 at -3 dB after the change should match r78 at 0 dB before it.

**Done 2026-11-17: R11 is 2k0 on both boards.** Measured on Wide, T12, 1 kHz, deviation with the RSP1. The boards swapped radios in the rework, so these are board 20000005 in radio 19925369 (on radio1) and board 20000002 in radio 19925328 (on radio2):

| Sound card level | Radio 19925369 + board 20000005 | Radio 19925328 + board 20000002 |
|---|---|---|
| -20 dBFS | 0.45 kHz | 0.44 kHz |
| -10 dBFS | 1.42 kHz | 1.39 kHz |
| -6 dBFS | 2.26 kHz | 2.20 kHz |
| -3 dBFS | 3.19 kHz | 3.11 kHz |
| 0 dBFS | **4.50 kHz (90%)** | **4.39 kHz (88%)** |

+3.2 dB on both against 3.13 kHz (63%) before, within 2% of the predicted 4.41 kHz. Still linear (every step within 0.01 dB of what was sent) and clean (second plus third harmonic -56 dBc at full scale). Both EEPROMs kept MIC PLL Adjust (0x2B = 7A12).

First ofdm-fm after the change, two hosts, `ofdm-fm-8k` 1024 B, two interleaved rounds of 20 frames each way: **73 of 80 at full drive, 73 of 80 at -3 dB** (the old full-scale deviation). As expected for that preset, which has margin either way. The r78 and burst-deviation rounds described above are still to do.

## Baseline for ofdm-fm work

What the next round of ofdm-fm development starts from, pdn-soundmodem 0.108.0, two Pis, Wide, R11 still 3k3, receivers at -80.5 dBm (before the RSP1 tee took 3.5 dB out; with the tee in, r78 fell to 19/80 and 4/80):

| | |
|---|---|
| Full-scale sine | 3.06 kHz peak (61% of 5 kHz) |
| `ofdm-fm-8k` burst | 0.69 kHz rms, 2.65 kHz peak, crest 11.7 dB |
| Receive response | flat to 4 kHz, -3 dB at 6.6 kHz, -6 dB at 7.6 kHz |
| Signal quality across the band (multitone at the burst's level) | 39 dB below 2 kHz falling to 25 dB at 8 kHz, as an upper bound |
| Clock mismatch between stations | 3 to 15 ppm average; wander of 27 to 52 microseconds within 1.5 s |
| `ofdm-fm-8k`, 1024 B | 60 to 100% delivered depending on the minute; 16.8 kbit/s when all arrive |
| `ofdm-fm-8k-r78`, 1900 B | 72/80 bottom to top, 29/80 top to bottom |
| `ofdm-fm-8k-r78`, 1900 B, drive -3 dB | 63/80 and 1/80 |

Rules for comparing anything against it: interleave, at least four rounds of 20 frames each way, and re-run the baseline in the same session. A recorded set of bursts for offline decoding (so a change to the modem can be scored without the bench's minute-to-minute swings) has not been made yet; it should be made after the R11 change, since that moves the levels.

## Open questions

- **Why `ofdm-fm-8k` delivery comes and goes over minutes** with nothing changed. The first thing to build is a way to see failed bursts: the modem says nothing about them.
- Why the top to bottom direction (19925369 transmitting, 19925328 receiving) is weaker at the ofdm-fm margin. It follows the radios, not the Pi.
- **Whether clock wander limits the dense presets**, and whether a free-running capture clock with software resampling would do better than MIC PLL Adjust.
- Why lower drive gives a cleaner multitone above 1 kHz but worse `ofdm-fm-8k-r78` delivery.
- Source of the spur inside radio 19925328's receiver (about 3.9 to 4.05 kHz, drifting).
- **Sample-clock offset between stations on other computers.** This pair of Pis happens to be within 15 ppm; 100 to 200 ppm is ordinary, and the offline sweep above says `ofdm-fm-8k` falls away beyond 100 ppm. The single-carrier modems track clock error to 500 ppm or more.
- Why board 20000002's CM108B dropped off USB once.
- T13 on Wide has not been measured (2.44 kHz is the expectation).

Settled since the first version: the third harmonic in received audio is the radio's receiver and grows with deviation; the CM108 input gain is best left at -12 dB.
