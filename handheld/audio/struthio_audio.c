// STRUTHIO HANDHELD · game sound. See struthio_audio.h.
#include "struthio_audio.h"
#include <math.h>
#include <string.h>
#include "struthio_audio_data.h"

#define ENV_FLOOR 0.0005f
#define PHASE_BITS 56                        // one cycle = 2^56 (the browser's 2^32 with 24 fraction bits)
#define CYCLE ((uint64_t)1 << PHASE_BITS)
#define NOISE_CLOCK 8

static const uint32_t PULSE_WIDTH[3] = {0x80000000u, 0x40000000u, 0x20000000u};   // PULSE_50, _25, _12_5

// sin(2 pi i / 1024), 1025 entries for interpolation
static float g_sine[1025];
static bool g_sine_ready;
static void sine_init(void) {
    if (g_sine_ready) return;
    for (int i = 0; i <= 1024; i++) g_sine[i] = (float)sin(6.283185307179586 * i / 1024.0);
    g_sine_ready = true;
}
static uint64_t increment(double midi) {
    double cycles = 440.0 * pow(2.0, (midi - 69.0) / 12.0) / (double)STA_SAMPLE_RATE;
    return (uint64_t)llround(cycles * (double)CYCLE);
}
static inline bool before(uint32_t a, uint32_t b) { return (int32_t)(a - b) < 0; }

// ---- mixer ---------------------------------------------------------------------------------
void sta_mixer_init(sta_mixer_t *m) {
    sine_init();
    memset(m, 0, sizeof *m);
    m->noise = 0x6d2b79f5u;
}
static void drop(sta_mixer_t *m, int i) {
    memmove(&m->notes[i], &m->notes[i + 1], (size_t)(m->n - i - 1) * sizeof m->notes[0]);
    m->n--;
}
// synth.mjs makeRoom's cap(): evict the lowest-priority, oldest, unprotected
// note while the list is at its limit. `sustained_only` selects the list.
static bool cap(sta_mixer_t *m, bool sustained_only, int limit, int priority) {
    for (;;) {
        int count = 0, victim = -1;
        for (int i = 0; i < m->n; i++) {
            sta_note_t *n = &m->notes[i];
            if (sustained_only && !(n->sustain > 0)) continue;
            count++;
            if (n->protected_note) continue;
            if (victim < 0 || n->priority < m->notes[victim].priority ||
                (n->priority == m->notes[victim].priority && before(n->start, m->notes[victim].start))) victim = i;
        }
        if (count < limit) return true;
        if (victim < 0 || m->notes[victim].priority > priority) return false;
        drop(m, victim);
    }
}
bool sta_mixer_note_on(sta_mixer_t *m, int voice, int midi, int len_frames, uint32_t at, int priority, bool protected_note) {
    if (voice < 0 || voice >= STA_VOICE_COUNT) return false;
    const sta_voice_t *v = &STA_VOICES[voice];
    sta_note_t n;
    memset(&n, 0, sizeof n);
    n.voice = (uint8_t)voice;
    n.priority = (uint8_t)priority;
    n.protected_note = protected_note;
    n.start = at;
    n.gate_end = at + (uint32_t)(len_frames > 1 ? len_frames : 1);
    n.attack = v->attack > 1 ? v->attack : 1;
    int32_t decay = v->decay > 1 ? v->decay : 1, release = v->release > 1 ? v->release : 1;
    n.kd = (float)exp(-1.0 / decay);
    n.kr = (float)exp(-1.0 / release);
    n.sustain = (float)v->sustain_q15 / 32768.0f;
    n.gain = (float)v->gain_q15 / 32768.0f;
    n.coef = (float)v->coef_q15 / 32768.0f;
    n.inc = n.inc0 = increment(midi);
    n.glide = (int8_t)v->glide;
    // makeRoom: the whole pool, then (for a sustaining voice) the sustained pool
    if (!cap(m, false, STA_TRANSIENT_POOL_CAP, priority)) return false;
    if (n.sustain > 0 && !cap(m, true, STA_SUSTAINED_VOICE_CAP, priority)) return false;
    if (m->n >= STA_MAX_NOTES) return false;
    m->notes[m->n++] = n;
    return true;
}
static inline float envelope(sta_note_t *n, uint32_t f) {
    int32_t t = (int32_t)(f - n->start);
    float level;
    if (t < n->attack) level = (float)t / (float)n->attack;
    else {
        if (!n->decaying) { n->decaying = true; n->d = 1.0f; } else n->d *= n->kd;   // exp(-(t - attack) / decay)
        level = n->sustain + (1.0f - n->sustain) * n->d;
    }
    if (before(f, n->gate_end)) {
        if (t >= n->attack && level < ENV_FLOOR) n->done = 1;
        return level;
    }
    if (!n->releasing) { n->releasing = true; n->release_from = level; n->r = 1.0f; } else n->r *= n->kr;
    float out = n->release_from * n->r;
    if (out < ENV_FLOOR) { n->done = 1; return 0.0f; }
    return out;
}
static inline float wave(sta_mixer_t *m, sta_note_t *n) {
    uint64_t p = n->phase;
    switch (STA_VOICES[n->voice].wave) {
    case STA_WAVE_TRIANGLE: { float saw = (float)(uint32_t)(p >> 24) * (1.0f / 2147483648.0f) - 1.0f; return 2.0f * fabsf(saw) - 1.0f; }
    case STA_WAVE_SAW: return (float)(uint32_t)(p >> 24) * (1.0f / 2147483648.0f) - 1.0f;
    case STA_WAVE_SINE: {
        uint32_t i = (uint32_t)(p >> (PHASE_BITS - 10));
        float frac = (float)((p >> (PHASE_BITS - 26)) & 0xFFFF) * (1.0f / 65536.0f);
        return g_sine[i] + (g_sine[i + 1] - g_sine[i]) * frac;
    }
    case STA_WAVE_XORSHIFT_NOISE: {
        uint64_t next = n->noise_phase + n->inc * NOISE_CLOCK;
        if (next >= CYCLE || n->noise_value == 0.0f) {
            uint32_t x = m->noise;
            x ^= x << 13; x ^= x >> 17; x ^= x << 5;
            m->noise = x;
            n->noise_value = (float)((double)x / 2147483648.0 - 1.0);
        }
        n->noise_phase = next & (CYCLE - 1);
        return n->noise_value;
    }
    default: return (uint32_t)(p >> 24) < PULSE_WIDTH[STA_VOICES[n->voice].wave - STA_WAVE_PULSE_50] ? 1.0f : -1.0f;
    }
}
void sta_mixer_render(sta_mixer_t *m, int16_t *out, int len) {
    const float master = STA_MASTER_GAIN_Q15 / 32768.0f, ceiling = STA_LIMITER_CEILING_Q15 / 32768.0f;
    const float dc_r = STA_DC_BLOCK_R_Q15 / 32768.0f, bus = STA_SFX_GAIN_Q15 / 32768.0f;
    for (int i = 0; i < len; i++) {
        uint32_t f = m->frame + (uint32_t)i;
        float mix = 0.0f;
        for (int k = 0; k < m->n; k++) {
            sta_note_t *n = &m->notes[k];
            if (n->done || before(f, n->start)) continue;
            float env = envelope(n, f);
            if (n->glide && ((f - n->start) & 31) == 0) {
                double span = (double)(n->gate_end - n->start), kk = (double)(f - n->start) / (span > 1 ? span : 1);
                if (kk > 1) kk = 1;
                n->inc = (uint64_t)llround((double)n->inc0 * pow(2.0, n->glide * kk / 12.0));
            }
            float s = wave(m, n);
            n->filter += (s - n->filter) * n->coef;
            s = STA_VOICES[n->voice].filter == STA_FILTER_HP1 ? s - n->filter : n->filter;
            mix += s * env * n->gain * bus;
            n->phase = (n->phase + n->inc) & (CYCLE - 1);
        }
        float y = mix * master;
        float dc = y - m->dc_in + dc_r * m->dc_out;
        m->dc_in = y; m->dc_out = dc; y = dc;
        if (y > ceiling) y = ceiling; else if (y < -ceiling) y = -ceiling;
        out[i] = (int16_t)floorf(y * 32767.0f + 0.5f);       // Math.round
    }
    m->frame += (uint32_t)len;
    for (int k = m->n - 1; k >= 0; k--) if (m->notes[k].done) drop(m, k);
}

// ---- conductor ---------------------------------------------------------------------------------
void sta_conductor_init(sta_conductor_t *c, uint32_t seed, bool jitter) {
    memset(c, 0, sizeof *c);
    double bpm = STA_TRANSPORT_BPM_Q16 / 65536.0;
    c->eighth = 60.0 / bpm / 2.0;
    c->beat = c->eighth * 2.0;
    c->rng = seed ? seed : 0x9e3779b9u;
    c->jitter = jitter;
}
static double random01(sta_conductor_t *c) {
    uint32_t x = c->rng;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    c->rng = x;
    return (double)x / 4294967296.0;
}
void sta_conductor_event(sta_conductor_t *c, sta_mixer_t *m, int event_type, double now_s) {
    int k = sta_sfx_for_event(event_type);
    if (k < 0) return;
    const sta_sfx_t *x = &STA_SFX[k];
    double at = now_s;                                      // the origin is audio time 0
    if (x->quantize == STA_Q_NEXT_EIGHTH) at = ceil(now_s / c->eighth) * c->eighth;
    else if (x->quantize == STA_Q_NEXT_BEAT) at = ceil(now_s / c->beat) * c->beat;
    if (x->min_gap > 0) {
        double last = c->last_at[k] != 0 ? c->last_at[k] : -1;   // lastAt[key]||-1
        if (at - last < x->min_gap) return;
        c->last_at[k] = at;
    }
    int midi = x->midi;
    if (x->jitter && c->jitter) midi += (int)floor((random01(c) * 2 - 1) * x->jitter + 0.5);
    double at_frame = floor(at * STA_SAMPLE_RATE + 0.5);
    uint32_t frame = at_frame > (double)m->frame ? (uint32_t)at_frame : m->frame;
    c->scheduled++;
    if (!sta_mixer_note_on(m, x->voice, midi, (int)floor(x->len * STA_SAMPLE_RATE + 0.5), frame, x->priority, x->protected_note)) c->dropped++;
}

// ---- music ------------------------------------------------------------------------------------------
static const int16_t IMA_STEP[89] = {
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118,
    130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963, 1060,
    1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484,
    7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767};
static const int8_t IMA_INDEX[16] = {-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8};
static inline uint32_t rd32(const uint8_t *p) { return p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }
static int16_t music_decode(sta_music_t *mu) {
    if (mu->pos >= mu->samples) { mu->pos = 0; mu->pred = mu->pred0; mu->idx = mu->idx0; }   // seamless loop
    uint8_t byte = mu->data[mu->pos >> 1];
    int code = (mu->pos & 1) ? byte >> 4 : byte & 15;
    mu->pos++;
    int step = IMA_STEP[mu->idx];
    int diff = step >> 3;
    if (code & 4) diff += step;
    if (code & 2) diff += step >> 1;
    if (code & 1) diff += step >> 2;
    mu->pred += (code & 8) ? -diff : diff;
    if (mu->pred > 32767) mu->pred = 32767; else if (mu->pred < -32768) mu->pred = -32768;
    mu->idx += IMA_INDEX[code];
    if (mu->idx < 0) mu->idx = 0; else if (mu->idx > 88) mu->idx = 88;
    return (int16_t)mu->pred;
}
bool sta_music_open(sta_music_t *mu, const uint8_t *file, size_t size) {
    memset(mu, 0, sizeof *mu);
    if (!file || size < 20 || memcmp(file, "STMU", 4) != 0) return false;
    uint16_t version = (uint16_t)(file[4] | file[5] << 8), channels = (uint16_t)(file[6] | file[7] << 8);
    uint32_t rate = rd32(file + 8), samples = rd32(file + 12);
    if (version != 1 || channels != 1 || rate * 2 != STA_RATE || samples < 2 || 20 + (size_t)(samples + 1) / 2 > size) return false;
    mu->data = file + 20;
    mu->samples = samples;
    mu->pred0 = mu->pred = (int16_t)(file[16] | file[17] << 8);
    mu->idx0 = mu->idx = file[18] > 88 ? 88 : file[18];
    mu->cur = music_decode(mu);
    mu->next = music_decode(mu);
    mu->ok = true;
    return true;
}
int16_t sta_music_next(sta_music_t *mu) {
    if (!mu->ok) return 0;
    if (!mu->half) { mu->half = true; return mu->cur; }
    mu->half = false;
    int16_t mid = (int16_t)(((int32_t)mu->cur + mu->next) / 2);
    mu->cur = mu->next;
    mu->next = music_decode(mu);
    return mid;
}

// ---- output ------------------------------------------------------------------------------------------
// The browser's DynamicsCompressor, approximated: a soft knee from the threshold
// to threshold + knee, the ratio above, attack/release smoothing of the gain
// in dB, and WebAudio's automatic makeup gain, (1 / gain at 0 dBFS)^0.6.
static float curve_db(float x) {
    const float T = STA_COMP_THRESHOLD_DB, K = STA_COMP_KNEE_DB, slope = 1.0f / STA_COMP_RATIO;
    if (x <= T) return x;
    if (x <= T + K) return x + (slope - 1.0f) * (x - T) * (x - T) / (2.0f * K);
    return T + K + (slope - 1.0f) * K / 2.0f + (x - T - K) * slope;
}
void sta_audio_init(sta_audio_t *a, const uint8_t *music, size_t music_size, uint32_t seed) {
    memset(a, 0, sizeof *a);
    sta_mixer_init(&a->mixer);
    sta_conductor_init(&a->conductor, seed, true);
    a->sfx_on = true;
    a->music_on = sta_music_open(&a->music, music, music_size);
    a->duck = a->duck_target = 1.0f;
    a->makeup = powf(10.0f, -curve_db(0.0f) * 0.6f / 20.0f);
    a->env_db = 0.0f;
}
void sta_audio_event(sta_audio_t *a, const st_event_t *e) {
    if (a->sfx_on) sta_conductor_event(&a->conductor, &a->mixer, e->type, (double)a->mixer.frame / STA_SAMPLE_RATE);
    if (!a->music_on) return;
    for (int i = 0; i < STA_DUCK_COUNT; i++) {
        const sta_duck_t *d = &STA_DUCKS[i];
        if (d->event != e->type) continue;
        if (d->player_only) {
            const st_field_t *fa = st_event_field(e, "a"), *fb = st_event_field(e, "b");
            if (!((fa && fa->i == 0) || (fb && fb->i == 0))) continue;
        }
        float depth = d->depth < 0.1f ? 0.1f : d->depth > 1.0f ? 1.0f : d->depth;
        a->duck_target = 1.0f - (1.0f - depth) * 0.5f;
        a->duck_until = a->mixer.frame + (uint32_t)((d->attack + d->hold + d->release) * STA_RATE);
    }
}
void sta_audio_render(sta_audio_t *a, int16_t *out, int n) {
    const float pre = STA_SFX_NODE_GAIN * STA_MASTER_NODE_GAIN / 32768.0f, music_gain = STA_MUSIC_GAIN / 32768.0f;
    const float att = expf(-16.0f / (STA_COMP_ATTACK_S * STA_RATE)), rel = expf(-16.0f / (STA_COMP_RELEASE_S * STA_RATE));
    for (int b = 0; b < n; b += STA_BLOCK) {
        sta_mixer_render(&a->mixer, a->block, STA_BLOCK);
        if (a->duck_target < 1.0f && !before(a->mixer.frame, a->duck_until)) a->duck_target = 1.0f;
        for (int i = 0; i < STA_BLOCK; i += 16) {
            float peak = 0.0f;
            for (int j = 0; j < 16; j++) { float v = fabsf(a->block[i + j] * pre); if (v > peak) peak = v; }
            float x_db = peak > 1e-6f ? 20.0f * log10f(peak) : -120.0f;
            float gr = curve_db(x_db) - x_db;                    // <= 0
            a->env_db = gr < a->env_db ? att * a->env_db + (1 - att) * gr : rel * a->env_db + (1 - rel) * gr;
            float g = powf(10.0f, a->env_db / 20.0f) * a->makeup * pre;
            for (int j = 0; j < 16; j++) {
                float y = a->block[i + j] * g;
                if (a->music_on) {
                    a->duck += (a->duck_target - a->duck) * 0.01f;   // ~2 ms, no click
                    y += sta_music_next(&a->music) * music_gain * a->duck;
                }
                if (y > 1.0f) { y = 1.0f; a->peak_clips++; } else if (y < -1.0f) { y = -1.0f; a->peak_clips++; }
                out[b + i + j] = (int16_t)floorf(y * 32767.0f + 0.5f);
            }
        }
    }
}
