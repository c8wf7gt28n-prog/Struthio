// STRUTHIO HANDHELD · game sound: the port of STRUTHIO ARCADE 1.8.0's audio.
//
//   sta_mixer_*      arcade/src/audio/synth.mjs (the worklet Mixer): voices,
//                    envelopes, waves, one-pole filter, glide, voice stealing,
//                    DC block, ceiling. Checked against the JS Mixer sample by
//                    sample on the desktop (host/audio_check).
//   sta_conductor_*  arcade/src/audio/conductor.mjs: game events -> notes, with
//                    priorities, minimum gaps, pitch jitter and beat quantize.
//   sta_music_*      the soundtrack loop (arcade/assets/audio/*.mp3) as 24 kHz
//                    mono IMA ADPCM (host/make_music), played x2 to 48 kHz.
//   sta_audio_*      everything after: the session.mjs graph (SFX node gain,
//                    master gain, a compressor shaped like the browser's
//                    DynamicsCompressor), the music at its element gain with
//                    the session.mjs ducks, and a final clip to int16.
// Tables come from audio/struthio_audio_data.h (tools/gen_audio.mjs).
// Portable C11, no heap, float only (the ESP32-S3 FPU is single precision).
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "struthio_core.h"

#ifdef __cplusplus
extern "C" {
#endif

enum { STA_RATE = 48000, STA_BLOCK = 128, STA_MAX_NOTES = 32 };

// ---- synth (synth.mjs Mixer) ------------------------------------------------------
typedef struct {
    uint8_t voice, priority, protected_note, done;
    uint32_t start, gate_end;                 // frames
    int32_t attack;
    float kd, kr, sustain, gain, coef;        // per-frame decay / release multipliers
    float d, r, release_from, filter, noise_value;
    uint64_t phase, noise_phase, inc, inc0;   // phase: 2^56 = one cycle
    int8_t glide;
    bool decaying, releasing;
} sta_note_t;
typedef struct {
    sta_note_t notes[STA_MAX_NOTES];
    int n;
    uint32_t frame;
    uint32_t noise;
    float dc_in, dc_out;
} sta_mixer_t;
void sta_mixer_init(sta_mixer_t *m);
// noteOn: false when the pools are full of higher-priority or protected notes.
bool sta_mixer_note_on(sta_mixer_t *m, int voice, int midi, int len_frames, uint32_t at, int priority, bool protected_note);
// Renders n frames (the browser renders 128 at a time; finished notes are
// dropped at the end of each call, as there).
void sta_mixer_render(sta_mixer_t *m, int16_t *out, int n);

// ---- conductor (conductor.mjs) ----------------------------------------------------
typedef struct {
    double eighth, beat;                      // seconds
    double last_at[16];
    uint32_t rng;                             // jitter (the browser uses Math.random)
    bool jitter;
    uint32_t scheduled, dropped;
} sta_conductor_t;
void sta_conductor_init(sta_conductor_t *c, uint32_t seed, bool jitter);
// One game event at audio time now_s (seconds since the conductor started).
void sta_conductor_event(sta_conductor_t *c, sta_mixer_t *m, int event_type, double now_s);

// ---- music (IMA ADPCM loop) -------------------------------------------------------
// File: "STMU", u16 version 1, u16 channels 1, u32 rate (24000), u32 samples,
// i16 predictor and u8 step index before the first code, u8 0, then one 4-bit
// code per sample, low nibble first. The loop restarts from that state.
typedef struct {
    const uint8_t *data;
    uint32_t samples, pos;
    int32_t pred0, pred;
    int idx0, idx;
    int16_t cur, next;
    bool half, ok;
} sta_music_t;
bool sta_music_open(sta_music_t *mu, const uint8_t *file, size_t size);
// Next 48 kHz sample (linear x2 from 24 kHz), looping.
int16_t sta_music_next(sta_music_t *mu);

// ---- the whole output ---------------------------------------------------------------
typedef struct {
    sta_mixer_t mixer;
    sta_conductor_t conductor;
    sta_music_t music;
    bool sfx_on, music_on;
    float duck, duck_target;                  // music ducking (session.mjs)
    uint32_t duck_until;
    float env_db, makeup;                     // compressor
    int16_t block[STA_BLOCK];
    uint32_t peak_clips;
} sta_audio_t;
void sta_audio_init(sta_audio_t *a, const uint8_t *music, size_t music_size, uint32_t seed);
// A game event (from st_step's event list); call between renders.
void sta_audio_event(sta_audio_t *a, const st_event_t *e);
// n frames of 48 kHz mono int16 (n a multiple of STA_BLOCK).
void sta_audio_render(sta_audio_t *a, int16_t *out, int n);

#ifdef __cplusplus
}
#endif
