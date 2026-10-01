// STRUTHIO HANDHELD · greybox renderer demo (host).
// Replays a golden trace through the C input normalizer + simulation, renders
// chosen ticks with the greybox renderer, presents them through the same
// 320x480 RGB565 line path the panel uses, and writes PNGs.
//   render_demo trace out_prefix tick...      (writes out_prefix_<tick>.png)
//   render_demo --sheet trace out.png tick... (one contact sheet)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "struthio_core.h"
#include "struthio_input.h"
#include "struthio_greybox.h"
#include "struthio_replay.h"

// ---- minimal PNG writer (stored deflate, no dependencies) -----------------------------
static uint32_t crc_table[256];
static void crc_init(void) {
    for (uint32_t n = 0; n < 256; n++) { uint32_t c = n; for (int k = 0; k < 8; k++) c = c & 1 ? 0xedb88320u ^ (c >> 1) : c >> 1; crc_table[n] = c; }
}
static uint32_t crc(uint32_t c, const uint8_t *b, size_t n) { c = ~c; while (n--) c = crc_table[(c ^ *b++) & 255] ^ (c >> 8); return ~c; }
static void be32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16); p[2] = (uint8_t)(v >> 8); p[3] = (uint8_t)v; }
static void chunk(FILE *f, const char *type, const uint8_t *data, uint32_t len) {
    uint8_t h[8]; be32(h, len); memcpy(h + 4, type, 4); fwrite(h, 1, 8, f);
    if (len) fwrite(data, 1, len, f);
    uint32_t c = crc(0, (const uint8_t *)type, 4); c = crc(c, data, len);
    uint8_t t[4]; be32(t, c); fwrite(t, 1, 4, f);
}
static int write_png(const char *path, const uint8_t *rgb, int w, int h) {
    FILE *f = fopen(path, "wb");
    if (!f) return -1;
    static const uint8_t sig[8] = {137, 80, 78, 71, 13, 10, 26, 10};
    fwrite(sig, 1, 8, f);
    uint8_t ihdr[13]; be32(ihdr, (uint32_t)w); be32(ihdr + 4, (uint32_t)h);
    ihdr[8] = 8; ihdr[9] = 2; ihdr[10] = ihdr[11] = ihdr[12] = 0;
    chunk(f, "IHDR", ihdr, 13);
    size_t raw_len = (size_t)h * (w * 3 + 1);
    uint8_t *raw = malloc(raw_len);
    for (int y = 0; y < h; y++) { raw[y * (w * 3 + 1)] = 0; memcpy(raw + y * (w * 3 + 1) + 1, rgb + (size_t)y * w * 3, (size_t)w * 3); }
    size_t blocks = (raw_len + 65534) / 65535;
    size_t z_len = 2 + raw_len + blocks * 5 + 4;
    uint8_t *z = malloc(z_len), *o = z;
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
    free(raw); free(z);
    return fclose(f);
}
// One frame through the panel path: st_present_line -> RGB565 -> RGB888.
static void panel_rgb(const uint8_t *fb, uint8_t *rgb, int stride_px, int ox) {
    uint16_t line[ST_PANEL_W];
    for (int y = 0; y < ST_PANEL_H; y++) {
        st_present_line(fb, y, line, false);
        for (int x = 0; x < ST_PANEL_W; x++) {
            uint16_t c = line[x];
            uint8_t *p = rgb + ((size_t)y * stride_px + ox + x) * 3;
            p[0] = (uint8_t)(((c >> 11) & 31) * 255 / 31); p[1] = (uint8_t)(((c >> 5) & 63) * 255 / 63); p[2] = (uint8_t)((c & 31) * 255 / 31);
        }
    }
}

typedef struct {
    long *shots; int nshots, cols;
    bool sheet; const char *out;
    uint8_t *sheet_rgb; int sw;
    st_camera_t cam;
    const char *banner; long banner_until;
    double render_s; long renders;
} demo_t;
enum { GAP = 8 };
static void on_tick(void *ctx, long t, const st_state_t *s, const st_events_t *ev) {
    demo_t *d = (demo_t *)ctx;
    static uint8_t fb[ST_FB_W * ST_FB_H];
    for (int i = 0; i < ev->n; i++) {
        st_event_type_t type = (st_event_type_t)ev->e[i].type;
        if (getenv("EVENTS") && strstr(getenv("EVENTS"), st_event_name(type))) printf("t%ld %s\n", t, st_event_name(type));
        if (type == ST_EV_GOLD_RING_OPEN) { d->banner = "6/6 - THE GOLD RING IS AT THE MOON"; d->banner_until = t + 150; }
        if (type == ST_EV_EXTRA_LIFE) { d->banner = "EXTRA JOUST MARK"; d->banner_until = t + 100; }
    }
    st_view_t view = {st_camera_resolve(&d->cam, s), (uint32_t)t, 0, t < d->banner_until ? d->banner : NULL};
    for (int k = 0; k < d->nshots; k++) {
        if (d->shots[k] != t) continue;
        clock_t c0 = clock();
        st_render(fb, s, &view);
        d->render_s += (double)(clock() - c0) / CLOCKS_PER_SEC; d->renders++;
        if (d->sheet) {
            panel_rgb(fb, d->sheet_rgb + ((size_t)(GAP + (k / d->cols) * (ST_PANEL_H + GAP)) * d->sw) * 3, d->sw, GAP + (k % d->cols) * (ST_PANEL_W + GAP));
        } else {
            static uint8_t rgb[ST_PANEL_W * ST_PANEL_H * 3];
            panel_rgb(fb, rgb, ST_PANEL_W, 0);
            char path[512]; snprintf(path, sizeof path, "%s_%ld.png", d->out, t);
            write_png(path, rgb, ST_PANEL_W, ST_PANEL_H);
            printf("wrote %s  (round %d, score %d, camera %d)\n", path, s->tower.round, s->sim.score, view.camera_top);
        }
    }
}

int main(int argc, char **argv) {
    bool sheet = argc > 1 && strcmp(argv[1], "--sheet") == 0;
    int a0 = sheet ? 2 : 1;
    if (argc < a0 + 3) { fprintf(stderr, "usage: render_demo [--sheet] trace out tick...\n"); return 2; }
    crc_init();
    FILE *fp = fopen(argv[a0], "rb");
    if (!fp) { perror(argv[a0]); return 1; }
    fseek(fp, 0, SEEK_END); long size = ftell(fp); fseek(fp, 0, SEEK_SET);
    uint8_t *data = malloc((size_t)size);
    if (fread(data, 1, (size_t)size, fp) != (size_t)size) return 1;
    fclose(fp);
    demo_t d;
    memset(&d, 0, sizeof d);
    d.sheet = sheet; d.out = argv[a0 + 1];
    d.nshots = argc - a0 - 2;
    d.shots = calloc((size_t)d.nshots, sizeof(long));
    for (int i = 0; i < d.nshots; i++) d.shots[i] = strtol(argv[a0 + 2 + i], NULL, 10);
    d.cols = d.nshots < 4 ? d.nshots : 4;
    int rows = (d.nshots + d.cols - 1) / d.cols;
    d.sw = d.cols * ST_PANEL_W + (d.cols + 1) * GAP;
    int sh = rows * ST_PANEL_H + (rows + 1) * GAP;
    if (sheet) {
        d.sheet_rgb = malloc((size_t)d.sw * sh * 3);
        for (long i = 0; i < (long)d.sw * sh; i++) { d.sheet_rgb[i * 3] = 24; d.sheet_rgb[i * 3 + 1] = 22; d.sheet_rgb[i * 3 + 2] = 20; }
    }
    st_camera_reset(&d.cam);
    st_replay_result_t r;
    st_replay_hooks_t hooks = {&d, NULL, on_tick};
    st_replay(data, (size_t)size, false, &hooks, &r);
    if (sheet) { write_png(d.out, d.sheet_rgb, d.sw, sh); printf("wrote %s (%d frames)\n", d.out, d.nshots); }
    if (d.renders) printf("host render: %.3f ms/frame average\n", 1000.0 * d.render_s / d.renders);
    return 0;
}
