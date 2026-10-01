// STRUTHIO HANDHELD · texture baker (host). Turns the textures the browser
// exports (handheld/build/reference/textures, full 3x resolution) into the
// handheld's panel-density textures:
//   - material colour functions applied at full resolution first (the four
//     bird inks in use, the island palette on the island regions of the atlas)
//   - then area-filtered (premultiplied) to the panel's density: the browser's
//     768x1152 canvas shown at 286x429, s = 286/768
//   - the font and swatch region of the atlas also kept at full resolution
//     (they are drawn magnified)
// Output: handheld/build/bake/*.tex - u32 w, u32 h, then RGBA8 straight alpha.
//   bake_textures [refdir] [outdir]
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "struthio_raster.h"

static const double S = 286.0 / 768.0;
static uint8_t *slurp(const char *path, size_t want) {
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "missing %s (run tools/reference/capture.mjs --textures)\n", path); exit(2); }
    uint8_t *d = malloc(want);
    if (fread(d, 1, want, f) != want) { fprintf(stderr, "short %s\n", path); exit(2); }
    fclose(f);
    return d;
}
static void save(const char *dir, const char *name, const uint8_t *p, int w, int h) {
    char path[512];
    snprintf(path, sizeof path, "%s/%s.tex", dir, name);
    FILE *f = fopen(path, "wb");
    uint32_t hd[2] = {(uint32_t)w, (uint32_t)h};
    fwrite(hd, 4, 2, f);
    fwrite(p, 1, (size_t)w * h * 4, f);
    fclose(f);
    printf("  %-14s %4d x %4d\n", name, w, h);
}
// Area filter (box over the exact footprint), premultiplied, to ceil(w*s) x ceil(h*s).
static uint8_t *area_filter(const uint8_t *src, int w, int h, double s, int *ow, int *oh) {
    int W = (int)ceil(w * s), H = (int)ceil(h * s);
    uint8_t *o = calloc((size_t)W * H, 4);
    double f = 1.0 / s;
    for (int y = 0; y < H; y++) {
        double y0 = y * f, y1 = (y + 1) * f;
        if (y1 > h) y1 = h;
        for (int x = 0; x < W; x++) {
            double x0 = x * f, x1 = (x + 1) * f;
            if (x1 > w) x1 = w;
            double acc[4] = {0, 0, 0, 0}, wt = 0;
            for (int sy = (int)y0; sy < (int)ceil(y1); sy++) {
                double wy = fmin(y1, sy + 1) - fmax(y0, sy);
                for (int sx = (int)x0; sx < (int)ceil(x1); sx++) {
                    double ww = (fmin(x1, sx + 1) - fmax(x0, sx)) * wy;
                    const uint8_t *p = src + ((size_t)sy * w + sx) * 4;
                    double a = p[3] / 255.0;
                    acc[0] += p[0] * a * ww; acc[1] += p[1] * a * ww; acc[2] += p[2] * a * ww; acc[3] += a * ww;
                    wt += ww;
                }
            }
            uint8_t *d = o + ((size_t)y * W + x) * 4;
            double a = wt > 0 ? acc[3] / wt : 0;
            if (a > 0) for (int c = 0; c < 3; c++) d[c] = (uint8_t)fmin(255, floor(acc[c] / acc[3] + 0.5));
            d[3] = (uint8_t)floor(a * 255 + 0.5);
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
int main(int argc, char **argv) {
    const char *ref = argc > 1 ? argv[1] : "../build/reference/textures";
    const char *out = argc > 2 ? argv[2] : "../build/bake";
    char p[512];
    int w, h;
    printf("baking panel-density textures (s = 286/768):\n");
    // world plates: rear | near, each 768 x 2304
    snprintf(p, sizeof p, "%s/world.rgba", ref);
    uint8_t *world = slurp(p, (size_t)1536 * 2304 * 4);
    for (int k = 0; k < 2; k++) {
        uint8_t *plate = crop(world, 1536, k * 768, 0, 768, 2304);
        uint8_t *f = area_filter(plate, 768, 2304, S, &w, &h);
        save(out, k ? "world_near" : "world_rear", f, w, h);
        free(plate); free(f);
    }
    // bird sheet, one copy per ink in use: player 6, rivals 1..3 (rows 1..3)
    snprintf(p, sizeof p, "%s/bird.rgba", ref);
    uint8_t *bird = slurp(p, (size_t)1536 * 1152 * 4);
    const int inks[4] = {6, 1, 2, 3};
    for (int k = 0; k < 4; k++) {
        uint8_t *b = malloc((size_t)1536 * 1152 * 4);
        memcpy(b, bird, (size_t)1536 * 1152 * 4);
        apply(b, (size_t)1536 * 1152, 0, inks[k]);
        uint8_t *f = area_filter(b, 1536, 1152, S, &w, &h);
        char name[32];
        snprintf(name, sizeof name, "bird_ink%d", inks[k]);
        save(out, name, f, w, h);
        free(b); free(f);
    }
    // atlas: island palette on the island sheet (0,1280 1920x480) and the bake
    // region (0,0 1024x768): only island quads (material 11) sample them.
    snprintf(p, sizeof p, "%s/atlas.rgba", ref);
    uint8_t *atlas = slurp(p, (size_t)2048 * 2048 * 4);
    for (int y = 0; y < 2048; y++) {
        if (y >= 1280 && y < 1760) apply(atlas + ((size_t)y * 2048) * 4, 1920, 1, 0);
        if (y < 768) apply(atlas + ((size_t)y * 2048) * 4, 1024, 1, 0);
    }
    uint8_t *f = area_filter(atlas, 2048, 2048, S, &w, &h);
    save(out, "atlas", f, w, h);
    free(f);
    // full-resolution atlas strip for magnified glyphs and swatches: x 1536..2048, y 0..568
    uint8_t *strip = crop(atlas, 2048, 1536, 0, 512, 568);
    save(out, "atlas_hi", strip, 512, 568);
    // the turning moon's longitude map
    snprintf(p, sizeof p, "%s/globe.rgba", ref);
    uint8_t *globe = slurp(p, (size_t)1536 * 768 * 4);
    save(out, "globe", globe, 1536, 768);
    return 0;
}
