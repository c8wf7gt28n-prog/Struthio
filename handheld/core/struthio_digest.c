// STRUTHIO HANDHELD · canonical JSON + SHA-256, byte-identical to the browser's
// arcade/src/core/canonical.mjs digest(). Used to prove the port (every tick's
// digest equals the browser's) and, in debug builds, on the device itself.
// The writer streams into a buffer and/or a SHA-256 context: no heap.
#include "struthio_core.h"
#include <stdio.h>
#include <string.h>

// ---- SHA-256 (FIPS 180-4) ----------------------------------------------------------
typedef struct { uint32_t h[8]; uint64_t len; uint8_t buf[64]; size_t n; } sha256_t;
static const uint32_t K256[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
};
#define ROR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))
static void sha_block(sha256_t *c, const uint8_t *p) {
    uint32_t w[64];
    for (int i = 0; i < 16; i++) w[i] = (uint32_t)p[4 * i] << 24 | (uint32_t)p[4 * i + 1] << 16 | (uint32_t)p[4 * i + 2] << 8 | p[4 * i + 3];
    for (int i = 16; i < 64; i++) {
        uint32_t s0 = ROR(w[i - 15], 7) ^ ROR(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = ROR(w[i - 2], 17) ^ ROR(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    uint32_t a = c->h[0], b = c->h[1], cc = c->h[2], d = c->h[3], e = c->h[4], f = c->h[5], g = c->h[6], h = c->h[7];
    for (int i = 0; i < 64; i++) {
        uint32_t t1 = h + (ROR(e, 6) ^ ROR(e, 11) ^ ROR(e, 25)) + ((e & f) ^ (~e & g)) + K256[i] + w[i];
        uint32_t t2 = (ROR(a, 2) ^ ROR(a, 13) ^ ROR(a, 22)) + ((a & b) ^ (a & cc) ^ (b & cc));
        h = g; g = f; f = e; e = d + t1; d = cc; cc = b; b = a; a = t1 + t2;
    }
    c->h[0] += a; c->h[1] += b; c->h[2] += cc; c->h[3] += d; c->h[4] += e; c->h[5] += f; c->h[6] += g; c->h[7] += h;
}
static void sha_init(sha256_t *c) {
    static const uint32_t H0[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    memcpy(c->h, H0, sizeof H0); c->len = 0; c->n = 0;
}
static void sha_update(sha256_t *c, const void *data, size_t len) {
    const uint8_t *p = (const uint8_t *)data;
    c->len += len;
    while (len) {
        size_t take = 64 - c->n < len ? 64 - c->n : len;
        memcpy(c->buf + c->n, p, take);
        c->n += take; p += take; len -= take;
        if (c->n == 64) { sha_block(c, c->buf); c->n = 0; }
    }
}
static void sha_final_hex(sha256_t *c, char hex[65]) {
    uint64_t bits = c->len * 8;
    uint8_t pad = 0x80, zero = 0, lenb[8];
    sha_update(c, &pad, 1);
    while (c->n != 56) sha_update(c, &zero, 1);
    for (int i = 0; i < 8; i++) lenb[i] = (uint8_t)(bits >> (56 - 8 * i));
    sha_update(c, lenb, 8);
    static const char *const D = "0123456789abcdef";
    for (int i = 0; i < 8; i++) for (int j = 0; j < 4; j++) {
        uint8_t byte = (uint8_t)(c->h[i] >> (24 - 8 * j));
        hex[i * 8 + j * 2] = D[byte >> 4]; hex[i * 8 + j * 2 + 1] = D[byte & 15];
    }
    hex[64] = 0;
}

// ---- canonical writer -----------------------------------------------------------------
typedef struct { char *buf; size_t cap, len; sha256_t *sha; bool overflow; } wr_t;
static void put(wr_t *w, const char *s, size_t n) {
    if (w->sha) sha_update(w->sha, s, n);
    if (w->buf) {
        if (w->len + n + 1 > w->cap) w->overflow = true;
        else memcpy(w->buf + w->len, s, n);
    }
    w->len += n;
}
static void puts_(wr_t *w, const char *s) { put(w, s, strlen(s)); }
static void put_int(wr_t *w, int64_t v) { char t[24]; int n = snprintf(t, sizeof t, "%lld", (long long)v); put(w, t, (size_t)n); }
static void put_str(wr_t *w, const char *s) { put(w, "\"", 1); puts_(w, s); put(w, "\"", 1); }   // ids are plain ASCII
static void put_bool(wr_t *w, bool b) { puts_(w, b ? "true" : "false"); }

// An object is written with its keys in JS default sort order (UTF-16 code
// units; all keys here are ASCII, so strcmp order).
typedef void (*field_fn)(wr_t *w, const void *ctx, int which);
static void put_object(wr_t *w, const char *const *keys, int n, field_fn fn, const void *ctx) {
    int order[24];
    for (int i = 0; i < n; i++) order[i] = i;
    for (int i = 1; i < n; i++) {
        int k = order[i], j = i - 1;
        while (j >= 0 && strcmp(keys[order[j]], keys[k]) > 0) { order[j + 1] = order[j]; j--; }
        order[j + 1] = k;
    }
    put(w, "{", 1);
    for (int i = 0; i < n; i++) {
        if (i) put(w, ",", 1);
        put_str(w, keys[order[i]]);
        put(w, ":", 1);
        fn(w, ctx, order[i]);
    }
    put(w, "}", 1);
}

static const char *const SHELL[] = {"ATTRACT", "PLAY", "PAUSE", "GAMEOVER"};
static const char *const LAVA[] = {"SAFE", "SINK", "RESCUED"};
static const char *const KIND[] = {"RIVAL", "RIDER", "EGG"};
static const char *const CLS[] = {"BOUNDER", "HUNTER", "SHADOW"};
static const char *const GHOST[] = {"BLINKY", "PINKY", "INKY", "CLYDE"};
static const char *const LC[] = {"SPAWNING", "MOUNTED", "DISMOUNTED", "EGG", "HATCHING", "REMOUNTING", "REMOVED"};
static const char *const MOTION[] = {"STATIC", "DRIFT_X_SOFT", "BOB_Y_SOFT"};

static const char *const PLAYER_KEYS[] = {"x", "y", "vx", "vy", "groundedPlatformId", "facing", "wing", "flapCooldown",
                                          "footingTicks", "lavaPhase", "lavaTicks", "invulnerableTicks"};
static void player_field(wr_t *w, const void *ctx, int k) {
    const st_player_t *p = (const st_player_t *)ctx;
    switch (k) {
    case 0: put_int(w, p->x); break;
    case 1: put_int(w, p->y); break;
    case 2: put_int(w, p->vx); break;
    case 3: put_int(w, p->vy); break;
    case 4: if (p->grounded == ST_NO_PLATFORM) puts_(w, "null"); else put_str(w, ST_TOWER[p->grounded].id); break;
    case 5: put_int(w, p->facing); break;
    case 6: put_int(w, p->wing); break;
    case 7: put_int(w, p->flap_cooldown); break;
    case 8: put_int(w, p->footing_ticks); break;
    case 9: put_str(w, LAVA[p->lava_phase]); break;
    case 10: put_int(w, p->lava_ticks); break;
    case 11: put_int(w, p->invulnerable_ticks); break;
    }
}
static const char *const ACTOR_KEYS[] = {"id", "kind", "class", "ghost", "tier", "lifecycle", "x", "y", "vx", "vy",
                                         "facing", "phase", "timer", "rngDraws", "joustAwarded"};
static void actor_field(wr_t *w, const void *ctx, int k) {
    const st_actor_t *a = (const st_actor_t *)ctx;
    switch (k) {
    case 0: put_int(w, a->id); break;
    case 1: put_str(w, KIND[a->kind]); break;
    case 2: put_str(w, CLS[a->cls]); break;
    case 3: put_str(w, GHOST[a->ghost]); break;
    case 4: put_int(w, a->tier); break;
    case 5: put_str(w, LC[a->lifecycle]); break;
    case 6: put_int(w, a->x); break;
    case 7: put_int(w, a->y); break;
    case 8: put_int(w, a->vx); break;
    case 9: put_int(w, a->vy); break;
    case 10: put_int(w, a->facing); break;
    case 11: put_int(w, a->phase); break;
    case 12: put_int(w, a->timer); break;
    case 13: put_int(w, a->rng_draws); break;
    case 14: put_bool(w, a->joust_awarded); break;
    }
}
static const char *const PLATFORM_KEYS[] = {"id", "phase", "tick", "rect", "collidable"};
static void platform_field(wr_t *w, const void *ctx, int k) {
    const st_platform_t *p = (const st_platform_t *)ctx;
    switch (k) {
    case 0: put_str(w, ST_TOWER[p->id].id); break;
    case 1: put_str(w, MOTION[p->phase]); break;
    case 2: put_int(w, p->tick); break;
    case 3:
        put(w, "[", 1);
        for (int i = 0; i < 4; i++) { if (i) put(w, ",", 1); put_int(w, p->rect[i]); }
        put(w, "]", 1);
        break;
    case 4: put_bool(w, p->collidable); break;
    }
}
static const char *const SIM_KEYS[] = {"tick", "shell", "nextActorId", "eventSerial", "score", "lives"};
static void sim_field(wr_t *w, const void *ctx, int k) {
    const st_state_t *s = (const st_state_t *)ctx;
    switch (k) {
    case 0: put_int(w, s->sim.tick); break;
    case 1: put_str(w, SHELL[s->sim.shell]); break;
    case 2: put_int(w, s->sim.next_actor_id); break;
    case 3: put_int(w, s->sim.event_serial); break;
    case 4: put_int(w, s->sim.score); break;
    case 5: put_int(w, s->sim.lives); break;
    }
}
static const char *const RNG_KEYS[] = {"gameplayState"};
static void rng_field(wr_t *w, const void *ctx, int k) { (void)k; put_int(w, ((const st_state_t *)ctx)->rng); }
static const char *const TOWER_KEYS[] = {"round", "ringMask", "kills", "check", "go", "hold", "cooldown", "mercy"};
static void tower_field(wr_t *w, const void *ctx, int k) {
    const st_tower_t *t = &((const st_state_t *)ctx)->tower;
    switch (k) {
    case 0: put_int(w, t->round); break;
    case 1: put_int(w, t->ring_mask); break;
    case 2: put_int(w, t->kills); break;
    case 3: put_int(w, t->check); break;
    case 4: put_bool(w, t->go); break;
    case 5: put_int(w, t->hold); break;
    case 6: put_int(w, t->cooldown); break;
    case 7: put_int(w, t->mercy); break;
    }
}
static const char *const RUN_KEYS[] = {"eggChain", "clean", "deaths", "lifeBands"};
static void run_field(wr_t *w, const void *ctx, int k) {
    const st_state_t *s = (const st_state_t *)ctx;
    switch (k) {
    case 0: put_int(w, s->run.egg_chain); break;
    case 1: put_bool(w, s->run.clean); break;
    case 2: put_int(w, s->run.deaths); break;
    case 3: put_int(w, s->run.life_bands); break;
    }
}
static const char *const WORLD_KEYS[] = {"lavaY", "platforms"};
static void world_field(wr_t *w, const void *ctx, int k) {
    const st_state_t *s = (const st_state_t *)ctx;
    if (k == 0) { put_int(w, s->world.lava_y); return; }
    put(w, "[", 1);
    for (int i = 0; i < s->world.n_platforms; i++) {
        if (i) put(w, ",", 1);
        put_object(w, PLATFORM_KEYS, 5, platform_field, &s->world.platforms[i]);
    }
    put(w, "]", 1);
}
static const char *const STATE_KEYS[] = {"version", "sim", "rng", "player", "actors", "world", "tower", "run"};
static void state_field(wr_t *w, const void *ctx, int k) {
    const st_state_t *s = (const st_state_t *)ctx;
    switch (k) {
    case 0: put_int(w, 1); break;
    case 1: put_object(w, SIM_KEYS, 6, sim_field, s); break;
    case 2: put_object(w, RNG_KEYS, 1, rng_field, s); break;
    case 3: put_object(w, PLAYER_KEYS, 12, player_field, &s->player); break;
    case 4:
        put(w, "[", 1);
        for (int i = 0; i < s->n_actors; i++) {
            if (i) put(w, ",", 1);
            put_object(w, ACTOR_KEYS, 15, actor_field, &s->actors[i]);
        }
        put(w, "]", 1);
        break;
    case 5: put_object(w, WORLD_KEYS, 2, world_field, s); break;
    case 6: put_object(w, TOWER_KEYS, 8, tower_field, s); break;
    case 7: put_object(w, RUN_KEYS, 4, run_field, s); break;
    }
}
static void event_field(wr_t *w, const void *ctx, int k) {
    const st_event_t *e = (const st_event_t *)ctx;
    if (k == e->n) { put_str(w, st_event_name((st_event_type_t)e->type)); return; }
    if (k == e->n + 1) { put_int(w, e->serial); return; }
    const st_field_t *f = &e->f[k];
    if (f->kind == ST_F_INT) put_int(w, f->i);
    else if (f->kind == ST_F_BOOL) put_bool(w, f->i != 0);
    else put_str(w, f->s);
}
static void put_event(wr_t *w, const st_event_t *e) {
    const char *keys[ST_MAX_EVENT_FIELDS + 2];
    for (int i = 0; i < e->n; i++) keys[i] = e->f[i].key;
    keys[e->n] = "type";
    keys[e->n + 1] = "serial";
    put_object(w, keys, e->n + 2, event_field, e);
}
typedef struct { const st_state_t *s; const st_events_t *ev; } tick_ctx_t;
static const char *const TICK_KEYS[] = {"state", "events"};
static void tick_field(wr_t *w, const void *ctx, int k) {
    const tick_ctx_t *t = (const tick_ctx_t *)ctx;
    if (k == 0) { put_object(w, STATE_KEYS, 8, state_field, t->s); return; }
    put(w, "[", 1);
    for (int i = 0; i < t->ev->n; i++) { if (i) put(w, ",", 1); put_event(w, &t->ev->e[i]); }
    put(w, "]", 1);
}

int st_canonical_tick(const st_state_t *s, const st_events_t *ev, char *buf, size_t cap) {
    wr_t w = {buf, cap, 0, NULL, false};
    tick_ctx_t t = {s, ev};
    put_object(&w, TICK_KEYS, 2, tick_field, &t);
    if (w.overflow || !buf) return -1;
    buf[w.len] = 0;
    return (int)w.len;
}
void st_tick_digest(const st_state_t *s, const st_events_t *ev, char hex[65]) {
    sha256_t c;
    sha_init(&c);
    wr_t w = {NULL, 0, 0, &c, false};
    tick_ctx_t t = {s, ev};
    put_object(&w, TICK_KEYS, 2, tick_field, &t);
    sha_final_hex(&c, hex);
}
void st_state_digest(const st_state_t *s, char hex[65]) {
    sha256_t c;
    sha_init(&c);
    wr_t w = {NULL, 0, 0, &c, false};
    put_object(&w, STATE_KEYS, 8, state_field, s);
    sha_final_hex(&c, hex);
}
void st_chain_init(uint32_t seed, char hex[65]) {
    char json[64];
    int n = snprintf(json, sizeof json, "{\"game\":\"STRUTHIO-ARCADE\",\"seed\":%lu}", (unsigned long)(seed ? seed : 0x6d2b79f5u));
    sha256_t c;
    sha_init(&c);
    sha_update(&c, json, (size_t)n);
    sha_final_hex(&c, hex);
}
void st_chain_link(const char prev[65], const char tick[65], char out[65]) {
    sha256_t c;
    sha_init(&c);
    sha_update(&c, "{\"prev\":\"", 9);
    sha_update(&c, prev, 64);
    sha_update(&c, "\",\"tick\":\"", 10);
    sha_update(&c, tick, 64);
    sha_update(&c, "\"}", 2);
    sha_final_hex(&c, out);
}
