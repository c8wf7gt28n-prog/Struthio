// STRUTHIO HANDHELD · panel renderer check (host).
// Replays a golden trace through the C sim, scene builder and the panel
// renderer (the device's band renderer: the asset pack, HUD layers, LUT post), renders whole 320x480 frames at chosen ticks, and
// measures the game picture against the browser's own WebGPU frame (quality
// 0) area-filtered from 768x1152 down to 286x429.
//   [BILINEAR=1] panel_check [--png outdir] trace tick...
//   panel_check --hud    the HUD from the pack vs the browser's DOM HUD (hud_capture.mjs truths)
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "struthio_core.h"
#include "struthio_pak.h"
#include "struthio_panel.h"
#include "struthio_replay.h"
#include "struthio_scene.h"
#include "struthio_hud_heart.h"

static const char *REF = "../build/reference", *PAK = "../build/assets/struthio.pak";
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
static st_hud_assets_t hud;

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
        {   // the device splits each frame between two cores: even and odd bands must give the same frame
            static uint16_t single[ST_PANEL_W * ST_PANEL_H];
            static st_panel_work_t w0, w1;
            memcpy(single, frame565, sizeof single);
            st_panel_render_bands(&c->tx, &hud, &c->hud, &c->luts, &c->q, &fp, 1, 2, &w1, band, NULL);
            st_panel_render_bands(&c->tx, &hud, &c->hud, &c->luts, &c->q, &fp, 0, 2, &w0, band, NULL);
            if (memcmp(single, frame565, sizeof single)) { printf("  %s t%ld: two-core band split differs from one pass\n", c->name, t); c->fails++; }
        }
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
// The two truth frames hud_capture.mjs renders with the DOM (hud.json "truths").
static int hud_truths(const st_panel_textures_t *tx, st_panel_luts_t *luts) {
    static const struct { int32_t score, round, rings, kills, lives; bool due; int toast; } T[2] = {
        {12340, 3, 4, 17, 2, false, 7}, {98765, 12, 6, 204, 11, true, -1}};
    int fails = 0;
    for (int n = 0; n < 2; n++) {
        st_hud_t h;
        memset(&h, 0, sizeof h);
        h.score = T[n].score; h.round = T[n].round; h.rings = T[n].rings; h.kills = T[n].kills; h.lives = T[n].lives; h.due = T[n].due;
        h.toast = T[n].toast > 0 ? &hud.toast_clear[T[n].toast] : &hud.toast_gold;
        h.toast_opacity = 1; h.due_brightness = 1; h.opacity = 1;
        st_quads_t q;
        q.n = 0;
        st_frame_params_t fp;
        st_frame_params_default(&fp, 0, 0, 0);
        st_panel_render(tx, &hud, &h, luts, &q, &fp, band, NULL);
        char p[512];
        snprintf(p, sizeof p, "%s/hud/truth_%d.rgba", REF, n);
        uint8_t *truth = slurp(p, NULL);
        if (!truth) { fprintf(stderr, "missing %s\n", p); return 1; }
        const int top = 81;                      // the bar and the toast, above the game picture's content
        double se = 0;
        int worst = 0;
        for (int i = 0; i < ST_PANEL_W * top; i++) {
            int x = i % ST_PANEL_W, y = i / ST_PANEL_W;
            if (y >= ST_GAME_Y && x >= ST_GAME_X && x < ST_GAME_X + ST_GAME_W) continue;      // the game picture (toast lower part included)
            if (x >= ST_HEART_X0 && x < ST_HEART_X1 && y >= ST_HEART_Y0 && y < ST_HEART_Y1) continue;   // the heart (handheld only)
            uint16_t v = frame565[i];
            int c[3] = {((v >> 11) * 255 + 15) / 31, (((v >> 5) & 63) * 255 + 31) / 63, ((v & 31) * 255 + 15) / 31};
            for (int ch = 0; ch < 3; ch++) { int d = c[ch] - truth[i * 4 + ch]; se += d * d; if (abs(d) > worst) worst = abs(d); }
        }
        double psnr = 10 * log10(255.0 * 255.0 / (se / (ST_PANEL_W * top * 3.0) + 1e-12));
        printf("  HUD truth %d (score %d, lives %d%s): PSNR %.1f dB, worst %d (RGB565 panel)\n", n, T[n].score, T[n].lives, T[n].due ? ", gold due" : "", psnr, worst);
        if (psnr < 34) fails++;
        free(truth);
    }
    return fails;
}
int main(int argc, char **argv) {
    int a = 1;
    const char *png = NULL;
    bool hud_only = argc > 1 && !strcmp(argv[1], "--hud");
    if (a + 1 < argc && !strcmp(argv[a], "--png")) { png = argv[a + 1]; a += 2; }
    if (a >= argc && !hud_only) { fprintf(stderr, "usage: panel_check [--png dir] trace tick...\n"); return 2; }
    static ctx_t c;
    memset(&c, 0, sizeof c);
    size_t pak_size;
    uint8_t *pak = slurp(PAK, &pak_size);
    char err[96];
    if (!pak) { fprintf(stderr, "missing %s (make -C handheld/host pak)\n", PAK); return 2; }
    if (!st_pak_open(pak, pak_size, &c.tx, &hud, err, sizeof err)) { fprintf(stderr, "%s: %s\n", PAK, err); return 2; }
    c.tx.bilinear = getenv("BILINEAR") && *getenv("BILINEAR") && *getenv("BILINEAR") != '0';
    st_panel_luts_init(&c.luts);
    if (hud_only) {
        int f = hud_truths(&c.tx, &c.luts);
        printf(f ? "HUD CHECK: %d truth(s) below 34 dB\n" : "HUD CHECK: pack layers recompose the browser HUD\n", f);
        return f ? 1 : 0;
    }
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
    if (c.frames) printf("  host: %.1f ms per 320x480 panel frame (host, one core)\n", 1000 * c.secs / c.frames);
    printf(c.fails ? "PANEL CHECK: %d frame(s) below 24 dB\n" : "PANEL CHECK: all frames >= 24 dB\n", c.fails);
    return c.fails ? 1 : 0;
}
