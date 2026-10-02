# Game sound on the handheld

STRUTHIO ARCADE 1.8.0 makes its sound in two parts, and the handheld now has both:

| Browser | Handheld | Proof |
| --- | --- | --- |
| Sound effects: `arcade/src/audio/conductor.mjs` (game events -> notes: priorities, minimum gaps, pitch jitter, beat quantize) and `synth.mjs` (the AudioWorklet mixer: 7 voices, envelopes, noise / sine / triangle / pulse, one-pole filter, glide, voice stealing, DC block, ceiling) | `audio/struthio_audio.c`: `sta_conductor_*`, `sta_mixer_*`. Voices, SFX table, priorities, quantize and the music ducks are generated into `audio/struthio_audio_data.h` by `tools/gen_audio.mjs` | `run_tests.sh`: the C game's events from all five golden traces (8,031 notes, 21 minutes) through the C and the browser's own conductor + mixer: **SNR 76-77 dB, max difference 2 LSB** |
| Music: `assets/audio/tarmac-at-midnight-loop.mp3` (160.0 s, 44.1 kHz stereo, 160 kb/s, 3.2 MB), an HTML audio element at volume 0.56, ducked on rings, jousts, deaths and round clears (`session.mjs`) | `build/assets/struthio_music.ima`: 24 kHz mono IMA ADPCM, 1.92 MB, exactly 3,840,000 samples (80 bars at 120 BPM), looped without a seam; played x2 to 48 kHz at gain 0.56 with the same ducks | `host/make_music` reports the coding SNR (28.0 dB, normal for 4-bit ADPCM); `run_tests.sh` re-encodes it and checks the file is byte-identical |
| WebAudio graph: SFX node 0.68 -> master 0.92 -> DynamicsCompressor (-12 dB, knee 12, ratio 8, 3 ms / 250 ms) | the same gains; a compressor with the same parameters and WebAudio's automatic makeup gain, **approximated** (not the Chromium algorithm) | by ear on the bench |

`host/audio_check --wav golden/mortal.trace build/assets/struthio_music.ima out.wav 60`
writes what the handheld will play during that trace (SFX + music + output stage).

## Why it fits

| | Size | Where |
| --- | --- | --- |
| Synth + conductor + music decoder | a few KB of code, 4 KB state | `struthio` component, internal RAM |
| Soundtrack | 1.92 MB | new `music` partition (2.9 MB) |
| Asset pack | 8.26 MB | `assets` partition, now 9 MB (was 11 MB; 0.8 MB spare) |

The 16 MB flash is now: bootloader + table, nvs 24 KB, phy 4 KB, factory app 4 MB
(0x10000), assets 9 MB (0x410000), music 2.9 MB (0xD10000), ending exactly at 16 MB.
An MP3 decoder was not used: the MP3 is 3.2 MB and decoding it would cost CPU
on a chip that is already drawing the screen on both cores. ADPCM costs a few
instructions per sample.

## On the device

- `audio` task, core 0, priority 8 (above the renderer, below the 1 kHz wings):
  takes the game's events from a queue, renders 256 frames (5.33 ms) with
  `sta_audio_render`, and writes them to the ES8311 through `esp_codec_dev`
  (`board_audio_write`). The I2S DMA holds 4 x 256 frames; its wait paces the
  task, and an underrun plays silence. The game task never waits for sound:
  a full queue drops the sound, not the tick.
- The periodic log line now ends `audio <us> us (max <us>) per 5333`: the time
  to render 5.33 ms of sound. Not measured yet on the ESP32-S3.
- Volume: five levels (0 = off, 1-4 = codec 45/60/72/85 %), default 2, saved in
  NVS. Service mode: hold LEFT for 1 s to step it; a ring chime plays. The
  percentages are a starting point: tune them on the bench with the real speaker.
- Board: ES8311 at I2C 0x18 (`ES8311_CODEC_DEFAULT_ADDR` 0x30 in 8-bit form),
  I2S MCLK 44, BCLK 13, LRCK 15, DOUT 16, 48 kHz, 16-bit, MCLK 256 x fs, no PA
  enable pin: all as Waveshare's `bsp_es8311.c`, playback only.

## Not the same as the browser

- Pitch jitter uses the device's own random numbers (the browser uses
  `Math.random`), so a flap is not always the identical pitch. The checks turn
  jitter off on both sides.
- The browser plays stereo (both channels equal); the handheld has one speaker.
- The compressor is approximated (above). The music is ADPCM, not the MP3.
- The browser's music waits for the first touch (autoplay rules); the handheld
  plays from boot.
