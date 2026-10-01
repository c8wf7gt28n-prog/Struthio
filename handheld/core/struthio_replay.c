// STRUTHIO HANDHELD · golden trace replay. See struthio_replay.h and
// handheld/tools/golden_export.mjs for the trace format.
#include "struthio_replay.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "struthio_input.h"

static const char *find_key(const char *h, size_t hl, const char *key, char *pat, size_t cap) {
    snprintf(pat, cap, "\"%s\":", key);
    size_t n = strlen(pat);
    for (size_t i = 0; i + n <= hl; i++) if (memcmp(h + i, pat, n) == 0) return h + i + n;
    return NULL;
}
static long hnum(const char *h, size_t hl, const char *key) {
    char pat[48];
    const char *p = find_key(h, hl, key, pat, sizeof pat);
    return p ? strtol(p, NULL, 10) : 0;
}
static bool hbool(const char *h, size_t hl, const char *key) {
    char pat[48];
    const char *p = find_key(h, hl, key, pat, sizeof pat);
    return p && strncmp(p, "true", 4) == 0;
}
static void hstr(const char *h, size_t hl, const char *key, char *out, size_t cap) {
    char pat[48];
    const char *p = find_key(h, hl, key, pat, sizeof pat);
    out[0] = 0;
    if (!p || *p != '"') return;
    p++;
    size_t i = 0;
    while (p < h + hl && *p != '"' && i + 1 < cap) out[i++] = *p++;
    out[i] = 0;
}
static uint8_t encode_frame(const st_input_t *f) {
    return (uint8_t)((f->left ? 1 : 0) | (f->right ? 2 : 0) | (f->flap_edge ? 4 : 0) | (f->chord_edge ? 8 : 0) |
                     (f->dart_edge ? 16 : 0) | (f->dart_side == ST_SIDE_RIGHT ? 32 : 0) | ((f->flap_edge ? f->flap_kind : 0) << 6));
}
static st_input_t decode_frame(uint8_t b) {
    st_input_t f;
    memset(&f, 0, sizeof f);
    f.left = b & 1; f.right = (b >> 1) & 1; f.flap_edge = (b >> 2) & 1; f.chord_edge = (b >> 3) & 1;
    f.dart_edge = (b >> 4) & 1;
    f.dart_side = f.dart_edge ? ((b & 32) ? ST_SIDE_RIGHT : ST_SIDE_LEFT) : ST_SIDE_NONE;
    f.flap_kind = (st_flap_kind_t)(b >> 6);
    return f;
}
static void fail(st_replay_result_t *o, long t, const char *why) {
    if (o->first_bad_tick < 0) { o->first_bad_tick = t; snprintf(o->why, sizeof o->why, "t%ld: %s", t, why); }
}

// Static so the device needs no large stack for a replay.
static st_state_t g_s;
static st_events_t g_ev;
static st_norm_t g_norm;

bool st_replay(const uint8_t *data, size_t size, bool verify, const st_replay_hooks_t *hooks, st_replay_result_t *o) {
    st_replay_tick_fn cb = hooks ? hooks->post : NULL;
    void *ctx = hooks ? hooks->ctx : NULL;
    memset(o, 0, sizeof *o);
    o->first_bad_tick = -1;
    if (size < 12 || memcmp(data, "STRGOLD1", 8) != 0) { fail(o, 0, "not a golden trace"); return false; }
    uint32_t hl = data[8] | data[9] << 8 | data[10] << 16 | (uint32_t)data[11] << 24;
    if (12 + (size_t)hl > size) { fail(o, 0, "truncated header"); return false; }
    const char *h = (const char *)data + 12;
    char want_chain[65], want_state[65];
    hstr(h, hl, "name", o->name, sizeof o->name);
    hstr(h, hl, "chain", want_chain, sizeof want_chain);
    hstr(h, hl, "stateDigest", want_state, sizeof want_state);
    uint32_t seed = (uint32_t)hnum(h, hl, "seed");
    o->ticks = hnum(h, hl, "ticks");
    bool raw = hbool(h, hl, "raw"), lives_floor = hbool(h, hl, "livesFloor"), shield = hbool(h, hl, "shield");

    st_state_init(&g_s, seed);
    g_s.tower.round = (int32_t)hnum(h, hl, "startRound");
    st_start_run(&g_s, &g_ev);
    st_norm_init(&g_norm);
    st_norm_set_mode(&g_norm, ST_MODE_PLAY);
    char dig[65];
    st_chain_init(seed, o->chain);
    const uint8_t *p = data + 12 + hl, *end = data + size;
    long t = 0;
    for (; t < o->ticks; t++) {
        if (p >= end) { fail(o, t, "trace data ends early"); break; }
        if (lives_floor && g_s.sim.lives < 3) g_s.sim.lives = 3;
        if (shield && g_s.player.invulnerable_ticks < 2) g_s.player.invulnerable_ticks = 2;
        uint32_t base = (uint32_t)((t * 1000) / 60);
        int nops = *p++;
        if (p + nops * 2 + 10 > end) { fail(o, t, "trace data ends early"); break; }
        for (int i = 0; i < nops; i++, p += 2) {
            uint32_t now = base + p[0];
            switch (p[1]) {
            case 1: st_norm_wing_down(&g_norm, ST_SIDE_LEFT, now); break;
            case 2: st_norm_wing_up(&g_norm, ST_SIDE_LEFT); break;
            case 3: st_norm_wing_down(&g_norm, ST_SIDE_RIGHT, now); break;
            case 4: st_norm_wing_up(&g_norm, ST_SIDE_RIGHT); break;
            case 5: st_norm_dart(&g_norm, ST_SIDE_LEFT); break;
            case 6: st_norm_dart(&g_norm, ST_SIDE_RIGHT); break;
            case 7: st_norm_cleanup(&g_norm); break;
            }
        }
        bool want_accept = (*p & 1) != 0, sideless_dart = (*p & 2) != 0;
        p++;
        uint8_t want_frame = *p++;
        const uint8_t *want_digest = p;
        p += 8;
        st_input_t in;
        if (raw) {
            in = decode_frame(want_frame);
            if (sideless_dart) in.dart_side = ST_SIDE_NONE;
        }
        else {
            bool accept = st_can_accept_buffered_flap(&g_s);
            char why[64];
            if (accept != want_accept) { snprintf(why, sizeof why, "acceptFlap %d, browser %d", accept, want_accept); fail(o, t, why); break; }
            in = st_norm_frame(&g_norm, accept);
            uint8_t got = encode_frame(&in);
            if (got != want_frame) { snprintf(why, sizeof why, "frame 0x%02x, browser 0x%02x", got, want_frame); fail(o, t, why); break; }
        }
        if (hooks && hooks->pre) hooks->pre(ctx, t, &g_s);
        st_step(&g_s, &in, &g_ev);
        for (int i = 0; i < g_ev.n; i++) o->event_counts[g_ev.e[i].type]++;
        if (verify) {
            st_tick_digest(&g_s, &g_ev, dig);
            char want_hex[17];
            for (int i = 0; i < 8; i++) snprintf(want_hex + 2 * i, 3, "%02x", want_digest[i]);
            if (strncmp(dig, want_hex, 16) != 0) {
                char why[64];
                snprintf(why, sizeof why, "digest %.16s, browser %s", dig, want_hex);
                fail(o, t, why);
                if (cb) cb(ctx, t, &g_s, &g_ev);
                t++;
                break;
            }
            st_chain_link(o->chain, dig, o->chain);
        }
        if (cb) cb(ctx, t, &g_s, &g_ev);
    }
    o->ran = t;
    o->score = g_s.sim.score;
    o->round = g_s.tower.round;
    if (verify && o->first_bad_tick < 0) {
        char state[65];
        st_state_digest(&g_s, state);
        o->chain_ok = strcmp(o->chain, want_chain) == 0;
        o->state_ok = strcmp(state, want_state) == 0;
        if (!o->chain_ok) fail(o, t, "digest chain differs");
        else if (!o->state_ok) fail(o, t, "final state digest differs");
    }
    return o->first_bad_tick < 0 && o->ran == o->ticks;
}
