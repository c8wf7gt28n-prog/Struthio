// STRUTHIO HANDHELD · rasterizer check (host).
// Replays a golden trace through the C sim + scene builder to the ticks the
// reference capture rendered with the browser's WebGPU renderer, rasterizes
// them with the C rasterizer at 3x (768x1152) and compares, pixel for pixel,
// the scene buffer (before post) and the final frames at quality 0 and 2.
//   raster_check [--png outdir] trace tick...
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "struthio_core.h"
#include "struthio_raster.h"
#include "struthio_replay.h"
#include "struthio_scene.h"

enum { W = 768, H = 1152 };
static const char *REF = "../build/reference";
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
static st_rgba_t tex(const char *name, int w, int h) {
    char p[256]; snprintf(p, sizeof p, "%s/textures/%s.rgba", REF, name);
    size_t n = 0; st_rgba_t t = {w, h, slurp(p, &n)};
    if (!t.p || n != (size_t)w * h * 4) { fprintf(stderr, "missing %s (run capture.mjs --textures)\n", p); exit(2); }
    return t;
}
typedef struct { double mae, psnr, over8; long n; } diff_t;
static diff_t compare(const uint8_t *a, const uint8_t *b) {
    double se = 0, ae = 0; long over = 0;
    for (long i = 0; i < (long)W * H; i++) {
        int m = 0;
        for (int c = 0; c < 3; c++) { int d = a[i * 4 + c] - b[i * 4 + c]; se += d * d; ae += abs(d); if (abs(d) > m) m = abs(d); }
        if (m > 8) over++;
    }
    diff_t r = {ae / (W * H * 3.0), 10 * log10(255.0 * 255.0 / (se / (W * H * 3.0) + 1e-12)), 100.0 * over / (W * H), W * H};
    return r;
}
typedef struct {
    st_scene_t sc; st_camera_t cam; st_pre_tick_t pre; st_quads_t q; st_gameover_info_t info;
    long *ticks; int nt; const char *name, *png; st_textures_t tx; int fails;
} ctx_t;
static void pre(void *c_, long t, const st_state_t *s) { (void)t; ((ctx_t *)c_)->pre = st_scene_pre_tick(s); }
static void write_rgba(const char *path, const uint8_t *p) { FILE *f = fopen(path, "wb"); if (f) { fwrite(p, 1, (size_t)W * H * 4, f); fclose(f); } }
static void post(void *c_, long t, const st_state_t *s, const st_events_t *ev) {
    ctx_t *c = c_;
    st_scene_on_events(&c->sc, s, ev, &c->pre);
    for (int i = 0; i < ev->n; i++)
        if (ev->e[i].type == ST_EV_GAMEOVER) c->info = (st_gameover_info_t){s->sim.score, s->tower.round, s->sim.score, s->sim.score > 0, true};
    static const char *const ITEMS[2] = {"NEW RUN", "TITLE"};
    st_menu_t menu = {ITEMS, 2, 0, c->info};
    st_scene_build(&c->sc, s, st_camera_resolve(&c->cam, s), &menu, &c->q);
    for (int k = 0; k < c->nt; k++) {
        if (c->ticks[k] != t) continue;
        static uint8_t scene[W * H * 4], out[W * H * 4];
        static float depth[W * H], scratch[2 * 192 * 288 * 3];
        st_frame_params_t fp;
        st_frame_params_default(&fp, c->sc.render_tick, c->sc.moon_phase, st_scene_impact(&c->sc, s));
        st_raster_scene(scene, depth, W, H, &c->q, &c->tx, &fp);
        char p[512];
        snprintf(p, sizeof p, "%s/%s_%ld_scene.rgba", REF, c->name, t);
        uint8_t *ref = slurp(p, NULL);
        if (!ref) { printf("  t%ld: no reference frame (capture.mjs --frames)\n", t); continue; }
        diff_t d = compare(scene, ref);
        printf("  %s t%-6ld scene  : PSNR %5.1f dB  mean |d| %5.2f  pixels off >8: %5.2f%%\n", c->name, t, d.psnr, d.mae, d.over8);
        if (d.psnr < 30) c->fails++;
        if (c->png) { snprintf(p, sizeof p, "%s/%s_%ld_c_scene.rgba", c->png, c->name, t); write_rgba(p, scene); }
        free(ref);
        for (int qv = 0; qv <= 2; qv += 2) {
            fp.quality = qv;
            st_raster_post(scene, out, W, H, 384, &fp, scratch);
            snprintf(p, sizeof p, "%s/%s_%ld_q%d.rgba", REF, c->name, t, qv);
            ref = slurp(p, NULL);
            if (!ref) continue;
            d = compare(out, ref);
            printf("  %s t%-6ld final q%d: PSNR %5.1f dB  mean |d| %5.2f  pixels off >8: %5.2f%%\n", c->name, t, qv, d.psnr, d.mae, d.over8);
            if (d.psnr < 30) c->fails++;
            if (c->png) { snprintf(p, sizeof p, "%s/%s_%ld_c_q%d.rgba", c->png, c->name, t, qv); write_rgba(p, out); }
            free(ref);
        }
    }
}
int main(int argc, char **argv) {
    int a = 1;
    const char *png = NULL;
    if (a + 1 < argc && !strcmp(argv[a], "--png")) { png = argv[a + 1]; a += 2; }
    if (a >= argc) { fprintf(stderr, "usage: raster_check [--png dir] trace tick...\n"); return 2; }
    static ctx_t c;
    memset(&c, 0, sizeof c);
    c.tx.atlas = tex("atlas", 2048, 2048);
    c.tx.world = tex("world", 1536, 2304);
    c.tx.bird = tex("bird", 1536, 1152);
    c.tx.globe = tex("globe", 1536, 768);
    c.tx.globe_params[0] = 608; c.tx.globe_params[1] = 254; c.tx.globe_params[2] = -118; c.tx.globe_params[3] = 0.0020943951f;
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
    printf(c.fails ? "RASTER CHECK: %d comparison(s) below 30 dB\n" : "RASTER CHECK: all comparisons >= 30 dB\n", c.fails);
    return c.fails ? 1 : 0;
}
