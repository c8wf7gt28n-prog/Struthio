// STRUTHIO HANDHELD · asset pack builder (host). Turns what the browser
// exports (tools/reference: textures at full 3x resolution, the HUD layers
// captured from Chromium) into the one file the device maps from its flash
// 'assets' partition (render/struthio_pak.h):
//   - material colour functions applied at full resolution first (the four
//     bird inks in use, the island palette on the island regions of the atlas)
//   - then area-filtered (premultiplied) to the panel's density: the browser's
//     768x1152 canvas shown at 286x429, s = 286/768
//   - the world plates carry the ambience's per-texel constants (lit, star
//     coverage, glint weights; st_amb_texel averaged over each footprint) and
//     the moon disk flag; the moon gets a latitude/longitude table and a
//     filtered longitude map, so the device turns it without trigonometry
//   - the font and swatch strip of the atlas also kept at full resolution
//     (drawn magnified)
//   - HUD layers run-length coded, the page frame as RGB565
//   make_pak [refdir] [out.pak]
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "struthio_pak.h"
#include "struthio_raster.h"

static const double S = 286.0 / 768.0;
static const float GLOBE[4] = {608, 254, -118, 0.0020943951f};   // renderer.mjs: centre, radius (colour mode), rad/tick
static uint8_t *slurp(const char *path, size_t want, size_t *got) {
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "missing %s (run tools/reference/capture.mjs --textures and hud_capture.mjs)\n", path); exit(2); }
    fseek(f, 0, SEEK_END); size_t n = (size_t)ftell(f); fseek(f, 0, SEEK_SET);
    if (want && n != want) { fprintf(stderr, "%s: %zu bytes, expected %zu\n", path, n, want); exit(2); }
    uint8_t *d = malloc(n + 1);
    if (fread(d, 1, n, f) != n) { fprintf(stderr, "short %s\n", path); exit(2); }
    d[n] = 0;
    fclose(f);
    if (got) *got = n;
    return d;
}

// ---- the pack ----------------------------------------------------------------------------------
enum { MAX_ENTRIES = 1024 };
static st_pak_entry_t entries[MAX_ENTRIES];
static uint8_t *blobs[MAX_ENTRIES];
static int count;
static size_t total;
static void add(const char *name, uint8_t *data, size_t size, int w, int h, int x, int y, int format) {
    if (count == MAX_ENTRIES || strlen(name) >= sizeof entries[0].name) { fprintf(stderr, "pack: cannot add %s\n", name); exit(2); }
    st_pak_entry_t *e = &entries[count];
    memset(e, 0, sizeof *e);
    snprintf(e->name, sizeof e->name, "%s", name);
    e->size = (uint32_t)size; e->w = (uint16_t)w; e->h = (uint16_t)h; e->x = (int16_t)x; e->y = (int16_t)y; e->format = (uint8_t)format;
    blobs[count++] = data;
    total += size;
}
static void write_pak(const char *path) {
    FILE *f = fopen(path, "wb");
    if (!f) { fprintf(stderr, "cannot write %s\n", path); exit(2); }
    uint32_t off = (uint32_t)(12 + count * sizeof(st_pak_entry_t));
    for (int i = 0; i < count; i++) { off = (off + 3) & ~3u; entries[i].offset = off; off += entries[i].size; }
    uint32_t n = (uint32_t)count;
    fwrite("STRPAK01", 1, 8, f); fwrite(&n, 4, 1, f);
    fwrite(entries, sizeof(st_pak_entry_t), (size_t)count, f);
    long pos = ftell(f);
    for (int i = 0; i < count; i++) {
        while ((uint32_t)pos < entries[i].offset) { fputc(0, f); pos++; }
        fwrite(blobs[i], 1, entries[i].size, f); pos += entries[i].size;
    }
    fclose(f);
    printf("%s: %d entries, %.2f MB\n", path, count, pos / 1048576.0);
}

// ---- filtering -----------------------------------------------------------------------------------
// Area filter (box over the exact footprint), premultiplied, to ceil(w*s) x ceil(h*s).
// attr (optional): n float planes per source texel, averaged alpha-weighted into oattr.
static uint8_t *area_filter(const uint8_t *src, int w, int h, double s, int *ow, int *oh, const float *attr, int n, float *oattr) {
    int W = (int)ceil(w * s), H = (int)ceil(h * s);
    uint8_t *o = calloc((size_t)W * H, 4);
    double f = 1.0 / s;
    for (int y = 0; y < H; y++) {
        double y0 = y * f, y1 = (y + 1) * f;
        if (y1 > h) y1 = h;
        for (int x = 0; x < W; x++) {
            double x0 = x * f, x1 = (x + 1) * f;
            if (x1 > w) x1 = w;
            double acc[4] = {0, 0, 0, 0}, at[4] = {0, 0, 0, 0}, wt = 0;
            for (int sy = (int)y0; sy < (int)ceil(y1); sy++) {
                double wy = fmin(y1, sy + 1) - fmax(y0, sy);
                for (int sx = (int)x0; sx < (int)ceil(x1); sx++) {
                    double ww = (fmin(x1, sx + 1) - fmax(x0, sx)) * wy;
                    size_t i = (size_t)sy * w + sx;
                    const uint8_t *p = src + i * 4;
                    double a = p[3] / 255.0;
                    acc[0] += p[0] * a * ww; acc[1] += p[1] * a * ww; acc[2] += p[2] * a * ww; acc[3] += a * ww;
                    for (int k = 0; k < n; k++) at[k] += attr[i * n + k] * a * ww;
                    wt += ww;
                }
            }
            uint8_t *d = o + ((size_t)y * W + x) * 4;
            double a = wt > 0 ? acc[3] / wt : 0;
            if (a > 0) for (int c = 0; c < 3; c++) d[c] = (uint8_t)fmin(255, floor(acc[c] / acc[3] + 0.5));
            d[3] = (uint8_t)floor(a * 255 + 0.5);
            for (int k = 0; k < n; k++) oattr[((size_t)y * W + x) * n + k] = acc[3] > 0 ? (float)(at[k] / acc[3]) : 0.0f;
        }
    }
    *ow = W; *oh = H;
    return o;
}
static uint8_t *crop(const uint8_t *src, int w, int x0, int y0, int cw, int ch) {
    uint8_t *o = malloc((size_t)cw * ch * 4);
    for (int y = 0; y < ch; y++) memcpy(o + (size_t)y * cw * 4, src + ((size_t)(y0 + y) * w + x0) * 4, (size_t)cw * 4);
    return o;
}
static void apply(uint8_t *p, size_t n, int kind, int ink) {
    for (size_t i = 0; i < n; i++) {
        uint8_t *q = p + i * 4;
        if (!q[3]) continue;
        float in[3] = {q[0] / 255.0f, q[1] / 255.0f, q[2] / 255.0f}, o[3];
        if (kind == 0) st_bird_ink(in, ink, 0, 1.0f, o);
        else st_island_palette(in, o);
        for (int c = 0; c < 3; c++) q[c] = (uint8_t)(fminf(1, fmaxf(0, o[c])) * 255.0f + 0.5f);
    }
}

// ---- encodings ---------------------------------------------------------------------------------
static inline uint16_t rgb565(const uint8_t *p) {
    return (uint16_t)(((p[0] * 31 + 127) / 255) << 11 | ((p[1] * 63 + 127) / 255) << 5 | ((p[2] * 31 + 127) / 255));
}
static uint8_t *enc565(const uint8_t *rgba, int w, int h, int bpp, size_t *size) {
    uint8_t *o = calloc((size_t)w * h, (size_t)bpp);
    for (size_t i = 0; i < (size_t)w * h; i++) {
        uint16_t c = rgb565(rgba + i * 4);
        o[i * bpp] = (uint8_t)c; o[i * bpp + 1] = (uint8_t)(c >> 8);
        if (bpp >= 3) o[i * bpp + 2] = rgba[i * 4 + 3];
    }
    *size = (size_t)w * h * bpp;
    return o;
}
static void add_tex(const char *name, const uint8_t *rgba, int w, int h, bool alpha) {
    size_t n;
    uint8_t *d = enc565(rgba, w, h, alpha ? 3 : 2, &n);
    add(name, d, n, w, h, 0, 0, alpha ? ST_TEX_565A8 : ST_TEX_565);
    printf("  %-14s %4d x %4d  %s  %7.0f KB\n", name, w, h, alpha ? "565A8" : "565  ", n / 1024.0);
}
// premultiplied RGBA8 rows, runs of up to 64 pixels: token t, t >> 6 =
//   0: (t & 63) + 1 literal pixels follow;  2: skip (t & 63) + 1 transparent pixels;
//   3: (t & 63) + 1 pixels as in the base layer (same size; toasts that differ only in a number)
static int kind_at(const uint8_t *row, const uint8_t *brow, int x) {
    if (brow && !memcmp(row + x * 4, brow + x * 4, 4)) return row[x * 4 + 3] ? 3 : 2;
    return row[x * 4 + 3] ? 0 : 2;
}
static uint8_t *rle(const uint8_t *p, const uint8_t *base, int w, int h, size_t *size) {
    uint8_t *o = malloc((size_t)w * h * 5 + h), *q = o;
    for (int y = 0; y < h; y++) {
        const uint8_t *row = p + (size_t)y * w * 4, *brow = base ? base + (size_t)y * w * 4 : NULL;
        for (int x = 0; x < w;) {
            int k = kind_at(row, brow, x), n = 1;
            while (x + n < w && n < 64 && kind_at(row, brow, x + n) == k) n++;
            *q++ = (uint8_t)(k << 6 | (n - 1));
            if (!k) { memcpy(q, row + x * 4, (size_t)n * 4); q += n * 4; }
            x += n;
        }
    }
    *size = (size_t)(q - o);
    return o;
}

int main(int argc, char **argv) {
    const char *ref = argc > 1 ? argv[1] : "../build/reference";
    const char *out = argc > 2 ? argv[2] : "../build/assets/struthio.pak";
    char p[512];
    int w, h;
    printf("asset pack (panel density s = 286/768):\n");
    st_frame_params_t fp;
    st_frame_params_default(&fp, 0, 0, 0);
    st_textures_t gt;
    memset(&gt, 0, sizeof gt);
    memcpy(gt.globe_params, GLOBE, sizeof GLOBE);

    // world plates: rear | near, each 768 x 2304, with the ambience constants
    snprintf(p, sizeof p, "%s/textures/world.rgba", ref);
    uint8_t *world = slurp(p, (size_t)1536 * 2304 * 4, NULL);
    const float gr = fabsf(GLOBE[2]);
    int gx0 = (int)floor((GLOBE[0] - gr) * S), gy0 = (int)floor((GLOBE[1] - gr) * S);
    int gx1 = (int)ceil((GLOBE[0] + gr) * S), gy1 = (int)ceil((GLOBE[1] + gr) * S);
    for (int k = 0; k < 2; k++) {
        uint8_t *plate = crop(world, 1536, k * 768, 0, 768, 2304);
        float *attr = malloc((size_t)768 * 2304 * 3 * sizeof(float));
        for (int y = 0; y < 2304; y++) for (int x = 0; x < 768; x++) {
            const uint8_t *q = plate + ((size_t)y * 768 + x) * 4;
            float rgb[3] = {q[0] / 255.0f, q[1] / 255.0f, q[2] / 255.0f};
            st_amb_texel_t t;
            st_amb_texel(rgb, x + 0.5f + k * 768, y + 0.5f, &fp, &gt, &t);
            float *a = attr + ((size_t)y * 768 + x) * 3;
            if (k == 0) { a[0] = t.lit; a[1] = t.star ? 1.0f : 0.0f; a[2] = 0; }
            else { a[0] = t.gold; a[1] = t.cyan; a[2] = 0; }
        }
        float *oattr = malloc((size_t)768 * 2304 * 3 * sizeof(float));
        uint8_t *f = area_filter(plate, 768, 2304, S, &w, &h, attr, 3, oattr);
        uint8_t *d = calloc((size_t)w * h, 4);
        for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) {
            size_t i = (size_t)y * w + x;
            uint16_t c = rgb565(f + i * 4);
            uint8_t *o = d + i * 4;
            o[0] = (uint8_t)c; o[1] = (uint8_t)(c >> 8);
            const float *a = oattr + i * 3;
            if (k == 0) {
                double wx = (x + 0.5) / S - GLOBE[0], wy = (y + 0.5) / S - GLOBE[1];
                bool disk = wx * wx + wy * wy < gr * gr;
                o[2] = (uint8_t)lrintf(fminf(1, a[0]) * 255);
                o[3] = (uint8_t)((disk ? 128 : 0) | lrintf(fminf(1, a[1]) * 127));
            } else {
                o[2] = f[i * 4 + 3];
                o[3] = (uint8_t)(lrintf(fminf(1, a[0]) * 15) << 4 | lrintf(fminf(1, a[1]) * 15));
            }
        }
        add(k ? "world_near" : "world_rear", d, (size_t)w * h * 4, w, h, 0, 0, k ? ST_TEX_NEAR : ST_TEX_REAR);
        printf("  %-14s %4d x %4d  %s  %7.0f KB\n", k ? "world_near" : "world_rear", w, h, k ? "near " : "rear ", w * h * 4 / 1024.0);
        free(plate); free(attr); free(oattr); free(f);
    }

    // the turning moon: longitude map (colour mode: g, b, a are the colour) filtered 4x,
    // and per disk texel its map row and longitude
    snprintf(p, sizeof p, "%s/textures/globe.rgba", ref);
    uint8_t *globe = slurp(p, (size_t)1536 * 768 * 4, NULL);
    for (size_t i = 0; i < (size_t)1536 * 768; i++) { uint8_t *q = globe + i * 4; q[0] = q[1]; q[1] = q[2]; q[2] = q[3]; q[3] = 255; }
    uint8_t *gm = area_filter(globe, 1536, 768, 0.25, &w, &h, NULL, 0, NULL);
    add_tex("globe_map", gm, w, h, false);
    const int mw = w, mh = h;
    (void)mw;
    int lw = gx1 - gx0, lh = gy1 - gy0;
    uint16_t *lut = calloc((size_t)lw * lh * 2, 2);
    for (int y = 0; y < lh; y++) for (int x = 0; x < lw; x++) {
        float wx = (float)((gx0 + x + 0.5) / S), wy = (float)((gy0 + y + 0.5) / S);
        float nx = (wx - GLOBE[0]) / gr, ny = (wy - GLOBE[1]) / gr;
        if (nx * nx + ny * ny >= 1.0f) continue;
        float lat = asinf(fmaxf(-1, fminf(1, ny)));
        float lon = asinf(fmaxf(-1, fminf(1, nx / fmaxf(cosf(lat), 0.0001f))));
        int vy = (int)((lat / 3.14159265358979f + 0.5f) * mh);
        vy = vy < 0 ? 0 : vy > mh - 1 ? mh - 1 : vy;
        float u = lon / 6.28318530717959f + 0.5f;
        lut[((size_t)y * lw + x) * 2] = (uint16_t)vy;
        lut[((size_t)y * lw + x) * 2 + 1] = (uint16_t)lrintf((u - floorf(u)) * 65535.0f);
    }
    add("globe_lut", (uint8_t *)lut, (size_t)lw * lh * 4, lw, lh, gx0, gy0, ST_RAW);
    float *gp = malloc(sizeof GLOBE);
    memcpy(gp, GLOBE, sizeof GLOBE);
    add("globe_params", (uint8_t *)gp, sizeof GLOBE, 4, 1, 0, 0, ST_RAW);

    // bird sheet, one copy per ink in use: player 6, rivals 1..3
    snprintf(p, sizeof p, "%s/textures/bird.rgba", ref);
    uint8_t *bird = slurp(p, (size_t)1536 * 1152 * 4, NULL);
    const int inks[4] = {6, 1, 2, 3};
    for (int k = 0; k < 4; k++) {
        uint8_t *b = malloc((size_t)1536 * 1152 * 4);
        memcpy(b, bird, (size_t)1536 * 1152 * 4);
        apply(b, (size_t)1536 * 1152, 0, inks[k]);
        uint8_t *f = area_filter(b, 1536, 1152, S, &w, &h, NULL, 0, NULL);
        char name[32];
        snprintf(name, sizeof name, "bird_ink%d", inks[k]);
        add_tex(name, f, w, h, true);
        free(b); free(f);
    }
    // atlas: island palette on the island sheet (0,1280 1920x480) and the bake
    // region (0,0 1024x768): only island quads (material 11) sample them.
    snprintf(p, sizeof p, "%s/textures/atlas.rgba", ref);
    uint8_t *atlas = slurp(p, (size_t)2048 * 2048 * 4, NULL);
    for (int y = 0; y < 2048; y++) {
        if (y >= 1280 && y < 1760) apply(atlas + ((size_t)y * 2048) * 4, 1920, 1, 0);
        if (y < 768) apply(atlas + ((size_t)y * 2048) * 4, 1024, 1, 0);
    }
    uint8_t *f = area_filter(atlas, 2048, 2048, S, &w, &h, NULL, 0, NULL);
    add_tex("atlas", f, w, h, true);
    // full-resolution strip for magnified glyphs and swatches: x 1536..2048, y 0..568
    add_tex("atlas_hi", crop(atlas, 2048, 1536, 0, 512, 568), 512, 568, true);

    // HUD: the page frame and the layers (tools/reference/hud_capture.mjs)
    snprintf(p, sizeof p, "%s/hud/chrome.rgba", ref);
    uint8_t *chrome = slurp(p, (size_t)320 * 480 * 4, NULL);
    add_tex("chrome", chrome, 320, 480, false);
    snprintf(p, sizeof p, "%s/hud/hud.json", ref);
    char *j = (char *)slurp(p, 0, NULL);
    size_t raw = 0, packed = 0;
    int layers = 0;
    struct { int w, h, entry; const uint8_t *p; } bases[64];
    int nb = 0;
    for (char *s = strstr(j, "\"name\": \""); s; s = strstr(s + 1, "\"name\": \"")) {
        char name[64]; int x, y, lw2, lh2;
        if (sscanf(s, "\"name\": \"%63[^\"]\",%*[ \n]\"x\": %d,%*[ \n]\"y\": %d,%*[ \n]\"w\": %d,%*[ \n]\"h\": %d", name, &x, &y, &lw2, &lh2) != 5) continue;
        if (!lw2 || !lh2 || !strncmp(name, "truth", 5)) continue;
        snprintf(p, sizeof p, "%s/hud/%s.rgba", ref, name);
        uint8_t *l = slurp(p, (size_t)lw2 * lh2 * 4, NULL);
        // round toasts: the first of each size is the base the others are coded against
        const uint8_t *base = NULL;
        int base_entry = -1;
        if (!strncmp(name, "toast_clea", 10)) {
            for (int b = 0; b < nb; b++) if (bases[b].w == lw2 && bases[b].h == lh2) { base = bases[b].p; base_entry = bases[b].entry; }
            if (!base && nb < 64) { bases[nb].w = lw2; bases[nb].h = lh2; bases[nb].entry = count; bases[nb].p = l; nb++; }
        }
        size_t n;
        uint8_t *r = rle(l, base, lw2, lh2, &n);
        add(name, r, n, lw2, lh2, x, y, ST_HUD_RLE);
        if (base_entry >= 0) { entries[count - 1].pad[0] = (uint8_t)(base_entry + 1); entries[count - 1].pad[1] = (uint8_t)((base_entry + 1) >> 8); }
        raw += (size_t)lw2 * lh2 * 4; packed += n; layers++;
    }
    printf("  HUD           %d layers, %.0f KB raw -> %.0f KB run-length coded\n", layers, raw / 1024.0, packed / 1024.0);
    write_pak(out);
    return 0;
}
