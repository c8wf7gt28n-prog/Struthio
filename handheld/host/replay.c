// STRUTHIO HANDHELD · golden replay comparator (host).
// Replays each handheld/golden/*.trace button timeline through the C input
// normalizer and C simulation, and checks every frame, every tick digest and
// the final digest chain against the browser authority.
//   replay [--dump TICK out.json] trace...
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "struthio_core.h"
#include "struthio_input.h"

static long json_num(const char *h, const char *key) {
    char pat[64]; snprintf(pat, sizeof pat, "\"%s\":", key);
    const char *p = strstr(h, pat);
    return p ? strtol(p + strlen(pat), NULL, 10) : 0;
}
static bool json_bool(const char *h, const char *key) {
    char pat[64]; snprintf(pat, sizeof pat, "\"%s\":true", key);
    return strstr(h, pat) != NULL;
}
static void json_str(const char *h, const char *key, char *out, size_t cap) {
    char pat[64]; snprintf(pat, sizeof pat, "\"%s\":\"", key);
    const char *p = strstr(h, pat);
    out[0] = 0;
    if (!p) return;
    p += strlen(pat);
    size_t i = 0;
    while (p[i] && p[i] != '"' && i + 1 < cap) { out[i] = p[i]; i++; }
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

static int replay(const char *path, long dump_tick, const char *dump_path) {
    FILE *fp = fopen(path, "rb");
    if (!fp) { perror(path); return 1; }
    fseek(fp, 0, SEEK_END);
    long size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    uint8_t *data = malloc((size_t)size);
    if (fread(data, 1, (size_t)size, fp) != (size_t)size) { fclose(fp); return 1; }
    fclose(fp);
    if (memcmp(data, "STRGOLD1", 8) != 0) { fprintf(stderr, "%s: not a golden trace\n", path); return 1; }
    uint32_t hl = data[8] | data[9] << 8 | data[10] << 16 | (uint32_t)data[11] << 24;
    char *h = calloc(1, hl + 1);
    memcpy(h, data + 12, hl);
    char name[64], want_chain[65], want_state[65];
    json_str(h, "name", name, sizeof name);
    json_str(h, "chain", want_chain, sizeof want_chain);
    json_str(h, "stateDigest", want_state, sizeof want_state);
    uint32_t seed = (uint32_t)json_num(h, "seed");
    long ticks = json_num(h, "ticks"), start_round = json_num(h, "startRound");
    bool raw = json_bool(h, "raw"), lives_floor = json_bool(h, "livesFloor"), shield = json_bool(h, "shield");

    static st_state_t s;
    st_events_t ev;
    st_norm_t norm;
    st_state_init(&s, seed);
    s.tower.round = (int32_t)start_round;
    st_start_run(&s, &ev);
    st_norm_init(&norm);
    st_norm_set_mode(&norm, ST_MODE_PLAY);
    char chain[65], dig[65];
    st_chain_init(seed, chain);

    const uint8_t *p = data + 12 + hl, *end = data + size;
    int bad = 0;
    long t = 0;
    long counts[ST_EV_COUNT] = {0};
    for (; t < ticks && p < end; t++) {
        if (lives_floor && s.sim.lives < 3) s.sim.lives = 3;
        if (shield && s.player.invulnerable_ticks < 2) s.player.invulnerable_ticks = 2;
        uint32_t base = (uint32_t)((t * 1000) / 60);
        int nops = *p++;
        for (int i = 0; i < nops; i++) {
            uint32_t now = base + p[0];
            switch (p[1]) {
            case 1: st_norm_wing_down(&norm, ST_SIDE_LEFT, now); break;
            case 2: st_norm_wing_up(&norm, ST_SIDE_LEFT); break;
            case 3: st_norm_wing_down(&norm, ST_SIDE_RIGHT, now); break;
            case 4: st_norm_wing_up(&norm, ST_SIDE_RIGHT); break;
            case 5: st_norm_dart(&norm, ST_SIDE_LEFT); break;
            case 6: st_norm_dart(&norm, ST_SIDE_RIGHT); break;
            case 7: st_norm_cleanup(&norm); break;
            }
            p += 2;
        }
        bool want_accept = *p++ != 0;
        uint8_t want_frame = *p++;
        const uint8_t *want_digest = p;
        p += 8;
        st_input_t in;
        if (raw) in = decode_frame(want_frame);
        else {
            bool accept = st_can_accept_buffered_flap(&s);
            if (accept != want_accept) { printf("%s t%ld: acceptFlap %d, browser %d\n", name, t, accept, want_accept); if (++bad > 5) break; }
            in = st_norm_frame(&norm, accept);
            uint8_t got = encode_frame(&in);
            if (got != want_frame) { printf("%s t%ld: frame 0x%02x, browser 0x%02x\n", name, t, got, want_frame); if (++bad > 5) break; }
        }
        st_step(&s, &in, &ev);
        for (int i = 0; i < ev.n; i++) counts[ev.e[i].type]++;
        st_tick_digest(&s, &ev, dig);
        char want_hex[17];
        for (int i = 0; i < 8; i++) sprintf(want_hex + 2 * i, "%02x", want_digest[i]);
        if (t == dump_tick && dump_path) {
            static char line[1 << 20];
            int n = st_canonical_tick(&s, &ev, line, sizeof line);
            FILE *o = fopen(dump_path, "w");
            if (o && n >= 0) { fprintf(o, "%s\n", line); fclose(o); }
        }
        if (strncmp(dig, want_hex, 16) != 0) {
            printf("%s t%ld: digest %.16s, browser %s  (dump: --dump %ld)\n", name, t, dig, want_hex, t);
            bad++;
            break;
        }
        st_chain_link(chain, dig, chain);
    }
    char state[65];
    st_state_digest(&s, state);
    if (!bad && t != ticks) { printf("%s: trace ended at %ld of %ld ticks\n", name, t, ticks); bad++; }
    if (!bad && strcmp(chain, want_chain) != 0) { printf("%s: chain %s, browser %s\n", name, chain, want_chain); bad++; }
    if (!bad && strcmp(state, want_state) != 0) { printf("%s: state digest differs\n", name); bad++; }
    printf("%s %-7s %6ld ticks  score %6d  round %2d  deaths %3ld  jousts %3ld  eggs %3ld  darts %3ld  chain %.16s\n",
           bad ? "FAIL" : "PASS", name, t, s.sim.score, s.tower.round, counts[ST_EV_PLAYER_DEATH], counts[ST_EV_JOUST_WIN],
           counts[ST_EV_EGG], counts[ST_EV_DART], chain);
    free(h); free(data);
    return bad ? 1 : 0;
}

int main(int argc, char **argv) {
    long dump_tick = -1;
    const char *dump_path = NULL;
    int fails = 0, files = 0;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--dump") == 0 && i + 2 < argc) { dump_tick = strtol(argv[i + 1], NULL, 10); dump_path = argv[i + 2]; i += 2; continue; }
        fails += replay(argv[i], dump_tick, dump_path);
        files++;
    }
    if (!files) { fprintf(stderr, "usage: replay [--dump TICK out.json] trace...\n"); return 2; }
    printf(fails ? "GOLDEN REPLAY: %d trace(s) FAILED\n" : "GOLDEN REPLAY: all %d traces bit-exact\n", fails ? fails : files);
    return fails ? 1 : 0;
}
