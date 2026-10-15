# Audio architecture note and resource reservation (R06)

Status: **reserved design interface**. Nothing here is implemented or measured. Per
`PRODUCT_VISION_2D_FPGA_AUDIO.md`, audio must not displace the pass-6 graphics and memory work.

## Baseline: F133 owns audio

* **Mixing:** software, on the F133 CPU. Target 16-bit stereo at 48 kHz with about 32 voices.
  These are **targets, not measurements**; there is no mixer code in R06.
* **Output:** the F133 integrated audio codec. Per F133 DS 2.8.1 it has two DAC channels,
  16/20-bit, 8–192 kHz, 100 ± 2 dB SNR (A-weighted) and −85 ± 3 dB THD+N; datasheet figures, not
  board measurements. It has a 128 × 20-bit DAC FIFO with DMA support. Pins: HPOUTL 99,
  HPOUTR 98, HPOUTFB 100, supplied from HPVCC 1.8 V (1.764–1.836 V).
* **Speakers:** HPOUT is a headphone output and must not drive loudspeakers directly. A stereo
  speaker amplifier is **required but not selected**. Its input must accept the HPOUT level. Its
  supply (AMP_VIN), load impedance, power, EMI and grounding are open. Shutdown/mute is wired to
  F133 PE10 (`AMP_SD_N`, 100 kΩ pull-down, so it stays muted until firmware is ready).
* **No extra processor:** no audio DSP, MCU or FPGA audio engine. The T35 stays off the audio
  path (`PRODUCT_VISION` rule).

## Fallback only: external I2S DAC/codec

To be used only if measurements show the onboard DAC is inadequate. The reserved pins are free
in the R06 board plan:

| Signal | F133 pin | Function (Table 4-3) |
|---|---|---|
| I2S2-DOUT0 | PB4 | Function3 |
| I2S2-BCLK | PB5 | Function3 |
| I2S2-LRCK | PB6 | Function3 |
| I2S2-MCLK | PB7 | Function3 |
| TWI0-SDA / SCK (codec control) | PB2 / PB3 | Function4 |

All are in the VCC-IO 3.3 V domain. An external codec moves only the D/A conversion off-chip;
mixing stays on the F133.

## Later acceptance benchmark (not R06/R07 scope)

Music plus overlapping effects while graphics and optional FPGA jobs run. Log mixer CPU %,
buffer underruns, output latency, noise/THD at the speaker and stability. Voice counts or
quality may be claimed only from that measurement.
