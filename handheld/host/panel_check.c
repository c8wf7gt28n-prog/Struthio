// STRUTHIO HANDHELD · panel renderer check (host).
// Replays a golden trace through the C sim, scene builder and the panel
// renderer (the device's band renderer: baked panel-density textures, HUD
// layers, LUT post), renders whole 320x480 frames at chosen ticks, and
// measures the game picture against the browser's own WebGPU frame (quality
// 0) area-filtered from 768x1152 down to 286x429.
//   [BILINEAR=1] panel_check [--png outdir] trace tick...
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "struthio_core.h"
#include "struthio_panel.h"
#include "struthio_replay.h"
#include "struthio_scene.h"

static const char *REF = "../build/reference", *BAKE = "../build/bake";
static void *slurp(const char *path, size_t *size) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    void *d = malloc((size_t)n);
    if (fread(d, 1, (size_t)n, f) != (size_t)n) { fclose(f); free(d); return NULL; }
    fclose(f);
    if (size) *size = (size_t)n;
    return d;
}
static st_tex_t load_tex(const char *name) {
    char p[512]; snprintf(p, sizeof p, "%s/%s.tex", BAKE, name);
    uint8_t *d = slurp(p, NULL);
    if (!d) { fprintf(stderr, "missing %s (run build/bake_textures)\n", p); exit(2); }
    st_tex_t t = {(int)((uint32_t *)d)[0], (int)((uint32_t *)d)[1], d + 8};
    return t;
}
// ---- HUD assets from tools/reference/hud_capture.mjs ---------------------------------------
static st_hud_assets_t hud;
static st_hud_layer_t *slot_for(const char *n) {
    int a, b, c;
    char v;
    if (sscanf(n, "score_%d_%d", &a, &b) == 2) return &hud.score[a][b];
    if (sscanf(n, "round_%d_%d", &a, &b) == 2) return &hud.round[a][b];
    if (sscanf(n, "kills2_%c_%d_%d", &v, &b, &c) == 3) return &hud.kills2[v - 'a'][b][c];
    if (sscanf(n, "kills3_%c_%d_%d", &v, &b, &c) == 3) return &hud.kills3[v - 'a'][b][c];
    if (sscanf(n, "swords_%c_%d", &v, &a) == 2) return &hud.swords[v - 'a'][a == 3];
    if (!strncmp(n, "ring_", 5) && strstr(n, "_due")) return &hud.ring[n[5] - 'a'][7];
    if (sscanf(n, "ring_%c_%d", &v, &a) == 2) return &hud.ring[v - 'a'][a];
    if (sscanf(n, "static_%c", &v) == 1) return &hud.statics[v - 'a'];
    if (sscanf(n, "joust_b_%d", &a) == 1) return &hud.joust_b[a];
    if (sscanf(n, "joust_i_%d", &a) == 1) return &hud.joust_i[a];
    if (!strcmp(n, "toast_extra")) return &hud.toast_extra;
    if (!strcmp(n, "toast_gold")) return &hud.toast_gold;
    if (!strcmp(n, "toast_paused")) return &hud.toast_paused;
    if (sscanf(n, "toast_clear_%d", &a) == 1 && a < ST_HUD_ROUNDS) return &hud.toast_clear[a];
    if (sscanf(n, "toast_clean_%d", &a) == 1 && a < ST_HUD_ROUNDS) return &hud.toast_clean[a];
    return NULL;
}
static void load_hud(void) {
    char p[512];
    snprintf(p, sizeof p, "%s/hud/chrome.rgba", REF);
    hud.chrome = slurp(p, NULL);
    snprintf(p, sizeof p, "%s/hud/hud.json", REF);
    char *j = slurp(p, NULL);
    if (!j || !hud.chrome) { fprintf(stderr, "missing HUD capture (tools/reference/hud_capture.mjs)\n"); exit(2); }
    int n = 0;
    for (char *s = strstr(j, "\"name\": \""); s; s = strstr(s + 1, "\"name\": \"")) {
        char name[64]; int x, y, w, h;
        if (sscanf(s, "\"name\": \"%63[^\"]\", \"x\": %d, \"y\": %d, \"w\": %d, \"h\": %d", name, &x, &y, &w, &h) != 5) continue;
        st_hud_layer_t *l = slot_for(name);
        if (!l || !w) continue;
        snprintf(p, sizeof p, "%s/hud/%s.rgba", REF, name);
        l->x = (int16_t)x; l->y = (int16_t)y; l->w = (int16_t)w; l->h = (int16_t)h; l->p = slurp(p, NULL);
        n++;
    }
    printf("HUD: chrome + %d layers\n", n);
}

// ---- the check ---------------------------------------------------------------------------
static uint16_t frame565[ST_PANEL_W * ST_PANEL_H];
static void band(void *ctx, int y0, int rows, const uint16_t *px) { (void)ctx; memcpy(frame565 + y0 * ST_PANEL_W, px, (size_t)rows * ST_PANEL_W * 2); }
typedef struct {
    st_scene_t sc; st_camera_t cam; st_pre_tick_t pre; st_quads_t q; st_gameover_info_t info; st_hud_t hud;
    st_panel_textures_t tx; st_panel_luts_t luts;
    long *ticks; int nt; const char *name, *png; int fails; double secs; int frames;
} ctx_t;
static void pre(void *c_, long t, const st_state_t *s) { (void)t; ((ctx_t *)c_)->pre = st_scene_pre_tick(s); }
static void area_ref(const uint8_t *ref, uint8_t *out) {      // 768x1152 -> 286x429, box over the footprint
    const double fx = 768.0 / ST_GAME_W, fy = 1152.0 / ST_GAME_H;
    for (int y = 0; y < ST_GAME_H; y++) for (int x = 0; x < ST_GAME_W; x++) {
        double x0 = x * fx, x1 = (x + 1) * fx, y0 = y * fy, y1 = (y + 1) * fy, acc[3] = {0, 0, 0}, wt = 0;
        for (int sy = (int)y0; sy < (int)ceil(y1); sy++) {
            double wy = fmin(y1, sy + 1) - fmax(y0, sy);
            for (int sx = (int)x0; sx < (int)ceil(x1); sx++) {
                double w = (fmin(x1, sx + 1) - fmax(x0, sx)) * wy;
                const uint8_t *p = ref + ((size_t)sy * 768 + sx) * 4;
                for (int c = 0; c < 3; c++) acc[c] += p[c] * w;
                wt += w;
            }
        }
        for (int c = 0; c < 3; c++) out[(y * ST_GAME_W + x) * 3 + c] = (uint8_t)floor(acc[c] / wt + 0.5);
    }
}
static void write_png_rgb(const char *path, const uint8_t *rgb, int w, int h);
static void post(void *c_, long t, const st_state_t *s, const st_events_t *ev) {
    ctx_t *c = c_;
    st_scene_on_events(&c->sc, s, ev, &c->pre);
    for (int i = 0; i < ev->n; i++)
        if (ev->e[i].type == ST_EV_GAMEOVER) c->info = (st_gameover_info_t){s->sim.score, s->tower.round, s->sim.score, s->sim.score > 0, true};
    static const char *const ITEMS[2] = {"NEW RUN", "TITLE"};
    st_menu_t menu = {ITEMS, 2, 0, c->info};
    st_scene_build(&c->sc, s, st_camera_resolve(&c->cam, s), &menu, &c->q);
    if (t == 0) st_hud_reset(&c->hud, c->sc.render_tick);
    st_hud_update(&c->hud, &hud, s, &c->sc);
    for (int k = 0; k < c->nt; k++) {
        if (c->ticks[k] != t) continue;
        st_frame_params_t fp;
        st_frame_params_default(&fp, c->sc.render_tick, c->sc.moon_phase, st_scene_impact(&c->sc, s));
        fp.quality = 0;
        static uint8_t rgb[ST_PANEL_W * ST_PANEL_H * 3], game[ST_PANEL_W * ST_PANEL_H * 3], refa[ST_GAME_W * ST_GAME_H * 3];
        // the game picture alone (the HUD and toasts are page elements, not in the WebGPU frame)
        c->luts.skip_post = getenv("SCENE") != NULL;
        st_panel_render(&c->tx, NULL, &c->hud, &c->luts, &c->q, &fp, band, NULL);
        c->luts.skip_post = false;
        for (int i = 0; i < ST_PANEL_W * ST_PANEL_H; i++) {
            uint16_t v = frame565[i];
            game[i * 3] = (uint8_t)(((v >> 11) * 255 + 15) / 31); game[i * 3 + 1] = (uint8_t)((((v >> 5) & 63) * 255 + 31) / 63); game[i * 3 + 2] = (uint8_t)(((v & 31) * 255 + 15) / 31);
        }
        clock_t c0 = clock();
        st_panel_render(&c->tx, &hud, &c->hud, &c->luts, &c->q, &fp, band, NULL);
        c->secs += (double)(clock() - c0) / CLOCKS_PER_SEC; c->frames++;
        for (int i = 0; i < ST_PANEL_W * ST_PANEL_H; i++) {
            uint16_t v = frame565[i];
            rgb[i * 3] = (uint8_t)(((v >> 11) * 255 + 15) / 31); rgb[i * 3 + 1] = (uint8_t)((((v >> 5) & 63) * 255 + 31) / 63); rgb[i * 3 + 2] = (uint8_t)(((v & 31) * 255 + 15) / 31);
        }
        char p[512];
        snprintf(p, sizeof p, getenv("SCENE") ? "%s/%s_%ld_scene.rgba" : "%s/%s_%ld_q0.rgba", REF, c->name, t);
        uint8_t *ref = slurp(p, NULL);
        if (ref) {
            area_ref(ref, refa);
            double se = 0, ae = 0;
            for (int y = 0; y < ST_GAME_H; y++) for (int x = 0; x < ST_GAME_W; x++) for (int ch = 0; ch < 3; ch++) {
                int d = game[((y + ST_GAME_Y) * ST_PANEL_W + x + ST_GAME_X) * 3 + ch] - refa[(y * ST_GAME_W + x) * 3 + ch];
                se += d * d; ae += abs(d);
            }
            double n = ST_GAME_W * ST_GAME_H * 3.0, psnr = 10 * log10(255.0 * 255.0 / (se / n + 1e-12));
            printf("  %s t%-6ld game picture vs browser (area-filtered, q0): PSNR %5.1f dB  mean |d| %5.2f\n", c->name, t, psnr, ae / n);
            if (psnr < 24) c->fails++;
            if (getenv("DIFFMAP") && c->png) {
                static uint8_t dm[ST_GAME_W * 3 * ST_GAME_H * 3];
                for (int y = 0; y < ST_GAME_H; y++) for (int x = 0; x < ST_GAME_W; x++) {
                    int m = 0;
                    for (int ch = 0; ch < 3; ch++) {
                        int cv = game[((y + ST_GAME_Y) * ST_PANEL_W + x + ST_GAME_X) * 3 + ch], rv = refa[(y * ST_GAME_W + x) * 3 + ch];
                        dm[(y * ST_GAME_W * 3 + x) * 3 + ch] = (uint8_t)cv;
                        dm[(y * ST_GAME_W * 3 + x + ST_GAME_W) * 3 + ch] = (uint8_t)rv;
                        if (abs(cv - rv) > m) m = abs(cv - rv);
                    }
                    uint8_t *o = &dm[(y * ST_GAME_W * 3 + x + 2 * ST_GAME_W) * 3];
                    o[0] = (uint8_t)(m * 4 > 255 ? 255 : m * 4); o[1] = o[2] = 0;
                }
                snprintf(p, sizeof p, "%s/diff_%s_%ld.png", c->png, c->name, t);
                write_png_rgb(p, dm, ST_GAME_W * 3, ST_GAME_H);
            }
            free(ref);
        }
        if (c->png) {
            snprintf(p, sizeof p, "%s/panel_%s_%ld.png", c->png, c->name, t);
            write_png_rgb(p, rgb, ST_PANEL_W, ST_PANEL_H);
            if (ref || 1) {
                // side by side: C panel | browser (area-filtered) in the same frame
                static uint8_t both[ST_PANEL_W * 2 * ST_PANEL_H * 3];
                for (int y = 0; y < ST_PANEL_H; y++) for (int x = 0; x < ST_PANEL_W; x++) for (int ch = 0; ch < 3; ch++) {
                    uint8_t v = rgb[(y * ST_PANEL_W + x) * 3 + ch];
                    both[(y * ST_PANEL_W * 2 + x) * 3 + ch] = v;
                    bool game = y >= ST_GAME_Y && y < ST_GAME_Y + ST_GAME_H && x >= ST_GAME_X && x < ST_GAME_X + ST_GAME_W;
                    both[(y * ST_PANEL_W * 2 + x + ST_PANEL_W) * 3 + ch] = game ? refa[((y - ST_GAME_Y) * ST_GAME_W + x - ST_GAME_X) * 3 + ch] : v;
                }
                snprintf(p, sizeof p, "%s/panel_vs_%s_%ld.png", c->png, c->name, t);
                write_png_rgb(p, both, ST_PANEL_W * 2, ST_PANEL_H);
            }
        }
    }
}
// ---- PNG (stored deflate) --------------------------------------------------------------------
static uint32_t crc_table[256];
static uint32_t crc(uint32_t c, const uint8_t *b, size_t n) { c = ~c; while (n--) c = crc_table[(c ^ *b++) & 255] ^ (c >> 8); return ~c; }
static void be32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16); p[2] = (uint8_t)(v >> 8); p[3] = (uint8_t)v; }
static void chunk(FILE *f, const char *type, const uint8_t *data, uint32_t len) {
    uint8_t h[8]; be32(h, len); memcpy(h + 4, type, 4); fwrite(h, 1, 8, f);
    if (len) fwrite(data, 1, len, f);
    uint32_t c = crc(0, (const uint8_t *)type, 4); c = crc(c, data, len);
    uint8_t t[4]; be32(t, c); fwrite(t, 1, 4, f);
}
static void write_png_rgb(const char *path, const uint8_t *rgb, int w, int h) {
    if (!crc_table[1]) for (uint32_t n = 0; n < 256; n++) { uint32_t c = n; for (int k = 0; k < 8; k++) c = c & 1 ? 0xedb88320u ^ (c >> 1) : c >> 1; crc_table[n] = c; }
    FILE *f = fopen(path, "wb");
    if (!f) return;
    static const uint8_t sig[8] = {137, 80, 78, 71, 13, 10, 26, 10};
    fwrite(sig, 1, 8, f);
    uint8_t ihdr[13]; be32(ihdr, (uint32_t)w); be32(ihdr + 4, (uint32_t)h); ihdr[8] = 8; ihdr[9] = 2; ihdr[10] = ihdr[11] = ihdr[12] = 0;
    chunk(f, "IHDR", ihdr, 13);
    size_t raw_len = (size_t)h * (w * 3 + 1);
    uint8_t *raw = malloc(raw_len);
    for (int y = 0; y < h; y++) { raw[y * (w * 3 + 1)] = 0; memcpy(raw + y * (w * 3 + 1) + 1, rgb + (size_t)y * w * 3, (size_t)w * 3); }
    size_t blocks = (raw_len + 65534) / 65535, zl = 2 + raw_len + blocks * 5 + 4;
    uint8_t *z = malloc(zl), *o = z;
    *o++ = 0x78; *o++ = 0x01;
    uint32_t a = 1, b = 0;
    for (size_t i = 0; i < raw_len; i++) { a = (a + raw[i]) % 65521; b = (b + a) % 65521; }
    for (size_t off = 0; off < raw_len; off += 65535) {
        size_t n = raw_len - off < 65535 ? raw_len - off : 65535;
        *o++ = off + n == raw_len; *o++ = (uint8_t)n; *o++ = (uint8_t)(n >> 8); *o++ = (uint8_t)~n; *o++ = (uint8_t)(~n >> 8);
        memcpy(o, raw + off, n); o += n;
    }
    be32(o, (b << 16) | a); o += 4;
    chunk(f, "IDAT", z, (uint32_t)(o - z));
    chunk(f, "IEND", NULL, 0);
    fclose(f); free(raw); free(z);
}
int main(int argc, char **argv) {
    int a = 1;
    const char *png = NULL;
    if (a + 1 < argc && !strcmp(argv[a], "--png")) { png = argv[a + 1]; a += 2; }
    if (a >= argc) { fprintf(stderr, "usage: panel_check [--png dir] trace tick...\n"); return 2; }
    static ctx_t c;
    memset(&c, 0, sizeof c);
    c.tx.world_rear = load_tex("world_rear"); c.tx.world_near = load_tex("world_near");
    c.tx.bird[0] = load_tex("bird_ink6"); c.tx.bird[1] = load_tex("bird_ink1"); c.tx.bird[2] = load_tex("bird_ink2"); c.tx.bird[3] = load_tex("bird_ink3");
    c.tx.atlas = load_tex("atlas"); c.tx.atlas_hi = load_tex("atlas_hi");
    st_tex_t g = load_tex("globe");
    c.tx.globe.globe = (st_rgba_t){g.w, g.h, g.p};
    c.tx.globe.globe_params[0] = 608; c.tx.globe.globe_params[1] = 254; c.tx.globe.globe_params[2] = -118; c.tx.globe.globe_params[3] = 0.0020943951f;
    load_hud();
    c.tx.bilinear = getenv("BILINEAR") && *getenv("BILINEAR") && *getenv("BILINEAR") != '0';
    st_panel_luts_init(&c.luts);
    const char *trace = argv[a++];
    const char *base = strrchr(trace, '/') ? strrchr(trace, '/') + 1 : trace;
    static char name[64];
    snprintf(name, sizeof name, "%.*s", (int)(strlen(base) - 6), base);
    c.name = name; c.png = png;
    c.nt = argc - a;
    c.ticks = calloc((size_t)c.nt, sizeof(long));
    for (int i = 0; i < c.nt; i++) c.ticks[i] = strtol(argv[a + i], NULL, 10);
    st_scene_init(&c.sc);
    st_camera_reset(&c.cam);
    size_t size;
    uint8_t *data = slurp(trace, &size);
    st_replay_hooks_t hooks = {&c, pre, post};
    st_replay_result_t r;
    st_replay(data, size, false, &hooks, &r);
    if (c.frames) printf("  host: %.1f ms per 320x480 panel frame (float reference path, one core)\n", 1000 * c.secs / c.frames);
    printf(c.fails ? "PANEL CHECK: %d frame(s) below 24 dB\n" : "PANEL CHECK: all frames >= 24 dB\n", c.fails);
    return c.fails ? 1 : 0;
}
