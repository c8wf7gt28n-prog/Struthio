// STRUTHIO HANDHELD · game sound on the desktop.
//   audio_check --events trace out.events      the C game's events, one per line: tick NAME a b
//   audio_check --render in.events out.pcm     the C conductor + mixer (s16le, 48 kHz mono)
//   audio_check --wav trace music.ima out.wav seconds
//                                              what the handheld plays: SFX + music + output stage
// tools/audio_reference.mjs renders the same events through the browser's own
// Conductor and Mixer and compares (run_tests.sh). Both sides deliver an event
// before the 128-frame block in which its tick (tick / 60 s) falls, with the
// conductor's clock at the tick time, and pitch jitter off.
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include "struthio_audio.h"
#include "struthio_replay.h"

static uint8_t *slurp(const char *path, size_t *n) {
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(2); }
    fseek(f, 0, SEEK_END); long len = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *p = malloc((size_t)len + 1);
    if (fread(p, 1, (size_t)len, f) != (size_t)len) { perror(path); exit(2); }
    fclose(f);
    *n = (size_t)len;
    return p;
}

// ---- events -------------------------------------------------------------------------------
typedef struct { long tick; int type; int a, b; } ev_t;
typedef struct { ev_t *e; long n, cap; FILE *out; } evlist_t;
static int field(const st_event_t *e, const char *k) { const st_field_t *f = st_event_field(e, k); return f ? (int)f->i : -1; }
static void post(void *ctx, long tick, const st_state_t *s, const st_events_t *ev) {
    (void)s;
    evlist_t *L = ctx;
    for (int i = 0; i < ev->n; i++) {
        const st_event_t *e = &ev->e[i];
        if (L->n == L->cap) { L->cap = L->cap ? L->cap * 2 : 1024; L->e = realloc(L->e, (size_t)L->cap * sizeof *L->e); }
        L->e[L->n++] = (ev_t){tick, e->type, field(e, "a"), field(e, "b")};
        if (L->out) fprintf(L->out, "%ld %s %d %d\n", tick, st_event_name((st_event_type_t)e->type), field(e, "a"), field(e, "b"));
    }
}
static evlist_t replay_events(const char *trace, FILE *out) {
    size_t n; uint8_t *data = slurp(trace, &n);
    evlist_t L = {0}; L.out = out;
    st_replay_hooks_t h = {&L, NULL, post};
    st_replay_result_t r;
    if (!st_replay(data, n, false, &h, &r)) { fprintf(stderr, "%s: replay failed: %s\n", trace, r.why); exit(1); }
    free(data);
    return L;
}
static int type_of(const char *name) {
    for (int t = 0; t < ST_EV_COUNT; t++) if (!strcmp(st_event_name((st_event_type_t)t), name)) return t;
    return -1;
}
static evlist_t read_events(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); exit(2); }
    evlist_t L = {0};
    char name[64]; long tick; int a, b;
    while (fscanf(f, "%ld %63s %d %d", &tick, name, &a, &b) == 4) {
        if (L.n == L.cap) { L.cap = L.cap ? L.cap * 2 : 1024; L.e = realloc(L.e, (size_t)L.cap * sizeof *L.e); }
        L.e[L.n++] = (ev_t){tick, type_of(name), a, b};
    }
    fclose(f);
    return L;
}
static uint32_t tick_frame(long tick) { return (uint32_t)((double)tick / 60.0 * STA_RATE + 0.5); }
static st_event_t as_event(const ev_t *x) {
    st_event_t e; memset(&e, 0, sizeof e);
    e.type = (uint8_t)x->type;
    e.n = 2;
    e.f[0] = (st_field_t){"a", ST_F_INT, x->a, NULL};
    e.f[1] = (st_field_t){"b", ST_F_INT, x->b, NULL};
    return e;
}

static void write_wav(const char *path, const int16_t *pcm, uint32_t n) {
    FILE *f = fopen(path, "wb");
    if (!f) { perror(path); exit(2); }
    uint32_t bytes = n * 2, rate = STA_RATE, byte_rate = rate * 2;
    uint8_t h[44] = {'R','I','F','F',0,0,0,0,'W','A','V','E','f','m','t',' ',16,0,0,0,1,0,1,0,0,0,0,0,0,0,0,0,2,0,16,0,'d','a','t','a',0,0,0,0};
    uint32_t riff = 36 + bytes;
    memcpy(h + 4, &riff, 4); memcpy(h + 24, &rate, 4); memcpy(h + 28, &byte_rate, 4); memcpy(h + 40, &bytes, 4);
    fwrite(h, 1, 44, f); fwrite(pcm, 2, n, f); fclose(f);
}

int main(int argc, char **argv) {
    if (argc == 4 && !strcmp(argv[1], "--events")) {
        FILE *out = fopen(argv[3], "w");
        if (!out) { perror(argv[3]); return 2; }
        evlist_t L = replay_events(argv[2], out);
        fclose(out);
        printf("%s: %ld events\n", argv[2], L.n);
        return 0;
    }
    if (argc == 4 && !strcmp(argv[1], "--render")) {
        evlist_t L = read_events(argv[2]);
        static sta_mixer_t m; static sta_conductor_t c;
        sta_mixer_init(&m); sta_conductor_init(&c, 1, false);
        uint32_t end = L.n ? tick_frame(L.e[L.n - 1].tick) + STA_RATE : STA_RATE;
        FILE *out = fopen(argv[3], "wb");
        int16_t block[STA_BLOCK];
        long k = 0;
        for (uint32_t F = 0; F < end; F += STA_BLOCK) {
            while (k < L.n && tick_frame(L.e[k].tick) < F + STA_BLOCK) {
                if (L.e[k].type >= 0) sta_conductor_event(&c, &m, L.e[k].type, (double)L.e[k].tick / 60.0);
                k++;
            }
            sta_mixer_render(&m, block, STA_BLOCK);
            fwrite(block, 2, STA_BLOCK, out);
        }
        fclose(out);
        printf("rendered %u frames, %u notes scheduled, %u refused\n", end, c.scheduled, c.dropped);
        return 0;
    }
    if (argc == 6 && !strcmp(argv[1], "--wav")) {
        evlist_t L = replay_events(argv[2], NULL);
        size_t mn = 0; uint8_t *music = strcmp(argv[3], "-") ? slurp(argv[3], &mn) : NULL;
        static sta_audio_t a;
        sta_audio_init(&a, music, mn, 1);
        if (music && !a.music_on) { fprintf(stderr, "%s: not a STRUTHIO music file\n", argv[3]); return 1; }
        uint32_t n = (uint32_t)(atof(argv[5]) * STA_RATE) / STA_BLOCK * STA_BLOCK;
        int16_t *pcm = malloc((size_t)n * 2);
        long k = 0;
        for (uint32_t F = 0; F < n; F += STA_BLOCK) {
            while (k < L.n && tick_frame(L.e[k].tick) < F + STA_BLOCK) { st_event_t e = as_event(&L.e[k]); sta_audio_event(&a, &e); k++; }
            sta_audio_render(&a, pcm + F, STA_BLOCK);
        }
        long peak = 0; double sum = 0;
        for (uint32_t i = 0; i < n; i++) { long v = labs(pcm[i]); if (v > peak) peak = v; sum += (double)pcm[i] * pcm[i]; }
        write_wav(argv[4], pcm, n);
        printf("wrote %s: %.1f s, peak %ld, rms %.0f, clipped samples %u, notes %u (refused %u)\n", argv[4], (double)n / STA_RATE,
               peak, sqrt(sum / n), a.peak_clips, a.conductor.scheduled, a.conductor.dropped);
        return 0;
    }
    fprintf(stderr, "usage: audio_check --events trace out | --render events out.pcm | --wav trace music.ima|- out.wav seconds\n");
    return 2;
}
