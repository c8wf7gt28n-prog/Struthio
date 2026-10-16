/* ARC-1 R10 -- bit-exact reference model of the ECP5-45F tile rasterizer (fpga45/rtl/r10_raster.sv) and test-vector
 * generator. R10 spec 7.1 steps 2-3: flat-colour triangles, signed edge functions, top-left fill rule, tile-local
 * 16-bit Z buffer (less-than test). HOST_TESTED; the RTL is compared against this model word for word.
 *
 * Job stream: 16-bit words.
 *   TILE_BEGIN 0x0001, tile_x (pixels, multiple of 32, 0..2016), tile_y (0..2016), clear_rgb565, clear_z -> clears
 *   TRI        0x0002, x0, y0, x1, y1, x2, y2 (signed 12.4 fixed point), z0, z1, z2 (u16), rgb565
 *   TILE_END   0x0003                                                                       -> emits the tile:
 *              0x5449 ('TI'), tile_x, tile_y, 1024 colour words (row-major), crc_lo, crc_hi (CRC-32 of the colour
 *              words as little-endian bytes)
 * Geometry: pixel (px, py) is sampled at its centre (16*px + 8, 16*py + 8) in 1/16-pixel units. With
 *   A = (x1-x0)(y2-y0) - (x2-x0)(y1-y0); A < 0 swaps v1/v2; A == 0 draws nothing.
 *   E_i for edge (a -> b) opposite vertex i: E = (xb-xa)(py-ya) - (yb-ya)(px-xa); inside: E > 0, or E == 0 and the
 *   edge is top-left: dy < 0 || (dy == 0 && dx > 0).
 * Depth: plane z = z0 + gx (sx-x0) + gy (sy-y0), gx = sat32(trunc((nx << 16) / A)), gy = sat32(trunc((ny << 16) / A)),
 *   nx = dz1*dy2 - dz2*dy1, ny = dz2*dx1 - dz1*dx2 (dx/dy relative to v0, after the swap); per sample
 *   zq = (z0 << 16) + gx*(sx-x0) + gy*(sy-y0) (exact integer), z = clamp(zq >> 16, 0, 65535) (arithmetic shift).
 *   Write if z < zbuf. Bounding box clamped to the tile; scan is row-major, 1 sample per clock in the RTL.
 * Usage: raster_ref <outdir> [seed] -> jobs.memh, expect.memh, cases.txt; also runs the shared-edge coverage check. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TS 32

static uint16_t col[TS * TS], zb[TS * TS];
static int tile_x, tile_y;
static long long cyc_scan;

static uint32_t crc32_bytes(uint32_t c, const uint8_t *p, size_t n)
{
    size_t i;
    int k;
    c = ~c;
    for (i = 0; i < n; i++) {
        c ^= p[i];
        for (k = 0; k < 8; k++) c = (c & 1u) ? (c >> 1) ^ 0xEDB88320u : (c >> 1);
    }
    return ~c;
}

static int64_t div_trunc(int64_t a, int64_t b) { return a / b; }   /* C99: truncation toward zero */
static int64_t sat32(int64_t v) { return v > 2147483647LL ? 2147483647LL : v < -2147483648LL ? -2147483648LL : v; }

typedef struct { int32_t x, y; uint16_t z; } vtx;

/* rasterise one triangle into the current tile; cover (optional) counts writes per pixel */
static void tri(vtx v0, vtx v1, vtx v2, uint16_t rgb, int *cover)
{
    int64_t A, nx, ny, gx, gy;
    int32_t bx0, by0, bx1, by1, px, py, i;
    vtx t;
    int tl[3];
    int32_t ax[3], ay[3], bx[3], by[3];
    A = (int64_t)(v1.x - v0.x) * (v2.y - v0.y) - (int64_t)(v2.x - v0.x) * (v1.y - v0.y);
    if (A == 0) return;
    if (A < 0) { t = v1; v1 = v2; v2 = t; A = -A; }
    {
        int64_t dx1 = v1.x - v0.x, dy1 = v1.y - v0.y, dx2 = v2.x - v0.x, dy2 = v2.y - v0.y;
        int64_t dz1 = (int64_t)v1.z - v0.z, dz2 = (int64_t)v2.z - v0.z;
        nx = dz1 * dy2 - dz2 * dy1;
        ny = dz2 * dx1 - dz1 * dx2;
        gx = sat32(div_trunc(nx * 65536, A));      /* slivers: gradient saturated to 32 bits (RTL identical) */
        gy = sat32(div_trunc(ny * 65536, A));
    }
    /* edges opposite v0, v1, v2: (v1->v2), (v2->v0), (v0->v1) */
    ax[0] = v1.x; ay[0] = v1.y; bx[0] = v2.x; by[0] = v2.y;
    ax[1] = v2.x; ay[1] = v2.y; bx[1] = v0.x; by[1] = v0.y;
    ax[2] = v0.x; ay[2] = v0.y; bx[2] = v1.x; by[2] = v1.y;
    for (i = 0; i < 3; i++) {
        int32_t dx = bx[i] - ax[i], dy = by[i] - ay[i];
        tl[i] = dy < 0 || (dy == 0 && dx > 0);
    }
    /* bounding box in pixels (samples at 16p+8), clamped to the tile */
    {
        int32_t mnx = v0.x, mxx = v0.x, mny = v0.y, mxy = v0.y;
        if (v1.x < mnx) mnx = v1.x;
        if (v2.x < mnx) mnx = v2.x;
        if (v1.x > mxx) mxx = v1.x;
        if (v2.x > mxx) mxx = v2.x;
        if (v1.y < mny) mny = v1.y;
        if (v2.y < mny) mny = v2.y;
        if (v1.y > mxy) mxy = v1.y;
        if (v2.y > mxy) mxy = v2.y;
        bx0 = (mnx - 8 + 15) >> 4; bx1 = (mxx - 8) >> 4;     /* first/last pixel whose centre can be inside */
        by0 = (mny - 8 + 15) >> 4; by1 = (mxy - 8) >> 4;
        if (bx0 < tile_x) bx0 = tile_x;
        if (by0 < tile_y) by0 = tile_y;
        if (bx1 > tile_x + TS - 1) bx1 = tile_x + TS - 1;
        if (by1 > tile_y + TS - 1) by1 = tile_y + TS - 1;
    }
    if (bx0 > bx1 || by0 > by1) return;
    cyc_scan += (long long)(bx1 - bx0 + 1) * (by1 - by0 + 1);
    for (py = by0; py <= by1; py++)
        for (px = bx0; px <= bx1; px++) {
            int32_t sx = 16 * px + 8, sy = 16 * py + 8;
            int in = 1;
            for (i = 0; i < 3; i++) {
                int64_t e = (int64_t)(bx[i] - ax[i]) * (sy - ay[i]) - (int64_t)(by[i] - ay[i]) * (sx - ax[i]);
                if (!(e > 0 || (e == 0 && tl[i]))) in = 0;
            }
            if (!in) continue;
            {
                int64_t zq = ((int64_t)v0.z << 16) + gx * (sx - v0.x) + gy * (sy - v0.y);
                int64_t z = zq >> 16;
                int a = (py - tile_y) * TS + (px - tile_x);
                if (z < 0) z = 0;
                if (z > 65535) z = 65535;
                if (cover) cover[a]++;
                if ((uint16_t)z < zb[a]) { zb[a] = (uint16_t)z; col[a] = rgb; }
            }
        }
}

static uint32_t rng = 12345;
static uint32_t rnd(void) { rng = rng * 1664525u + 1013904223u; return rng >> 8; }

static FILE *fj, *fe;
static long nj, ne;
static void jw(uint16_t w) { fprintf(fj, "%04x\n", w); nj++; }
static void ew(uint16_t w) { fprintf(fe, "%04x\n", w); ne++; }

static void emit_tile(void)
{
    uint8_t b[TS * TS * 2];
    uint32_t c;
    int i;
    ew(0x5449); ew((uint16_t)tile_x); ew((uint16_t)tile_y);
    for (i = 0; i < TS * TS; i++) { ew(col[i]); b[2 * i] = (uint8_t)col[i]; b[2 * i + 1] = (uint8_t)(col[i] >> 8); }
    c = crc32_bytes(0, b, sizeof b);
    ew((uint16_t)c); ew((uint16_t)(c >> 16));
}

static void begin(int tx, int ty, uint16_t cc, uint16_t cz)
{
    int i;
    tile_x = tx; tile_y = ty;
    for (i = 0; i < TS * TS; i++) { col[i] = cc; zb[i] = cz; }
    jw(1); jw((uint16_t)tx); jw((uint16_t)ty); jw(cc); jw(cz);
}

static void job_tri(vtx a, vtx b, vtx c, uint16_t rgb)
{
    jw(2); jw((uint16_t)a.x); jw((uint16_t)a.y); jw((uint16_t)b.x); jw((uint16_t)b.y); jw((uint16_t)c.x); jw((uint16_t)c.y);
    jw(a.z); jw(b.z); jw(c.z); jw(rgb);
    tri(a, b, c, rgb, NULL);
}

static vtx rv(int tx, int ty, int spread)
{
    vtx v;
    v.x = (int32_t)(tx * 16 + (int)(rnd() % (unsigned)(32 * 16 + 2 * spread)) - spread);
    v.y = (int32_t)(ty * 16 + (int)(rnd() % (unsigned)(32 * 16 + 2 * spread)) - spread);
    v.z = (uint16_t)(rnd() & 0xFFFF);
    return v;
}

/* shared-edge rule check: a fan of triangles around a centre and a split quad must cover each inside pixel exactly
 * once (no gaps, no double writes) */
static int coverage_check(void)
{
    static int cover[TS * TS];
    int i, bad = 0, n;
    vtx c = { 16 * 16 + 3, 16 * 16 + 5, 100 };
    tile_x = 0; tile_y = 0;
    for (n = 0; n < 200; n++) {
        int k, K = 3 + (int)(rnd() % 9);
        vtx p[16];
        memset(cover, 0, sizeof cover);
        for (i = 0; i < TS * TS; i++) zb[i] = 0xFFFF;
        c.x = (int32_t)(8 * 16 + rnd() % (16 * 16)); c.y = (int32_t)(8 * 16 + rnd() % (16 * 16));
        for (k = 0; k < K; k++) {                    /* convex fan with integer, half-pixel and exact-centre vertices */
            double ang = 6.283185307 * k / K;
            int r = 100 + (int)(rnd() % 120);
            p[k].x = c.x + (int32_t)(r * __builtin_cos(ang)); p[k].y = c.y + (int32_t)(r * __builtin_sin(ang));
            if (rnd() & 1) { p[k].x = (p[k].x & ~15) | 8; }   /* put vertices on sample centres too */
            p[k].z = 50;
        }
        for (k = 0; k < K; k++) tri(c, p[k], p[(k + 1) % K], 0x1234, cover);
        for (i = 0; i < TS * TS; i++) if (cover[i] > 1) bad++;
        /* gaps: a pixel inside the fan polygon (centre test against the convex hull) must be covered once */
        for (i = 0; i < TS * TS; i++) {
            int32_t sx = 16 * (i % TS) + 8, sy = 16 * (i / TS) + 8, inside = 1, k2;
            for (k2 = 0; k2 < K; k2++) {
                vtx a = p[k2], b = p[(k2 + 1) % K];
                int64_t e = (int64_t)(b.x - a.x) * (sy - a.y) - (int64_t)(b.y - a.y) * (sx - a.x);
                if (e <= 0) inside = 0;                 /* strictly inside the hull (hull edges themselves skipped) */
            }
            if (inside && cover[i] != 1) bad++;
        }
    }
    return bad;
}

int main(int argc, char **argv)
{
    char p[512];
    int t, k, ntiles = 0, ntris = 0, bad;
    if (argc < 2) { fprintf(stderr, "usage: raster_ref outdir [seed]\n"); return 2; }
    if (argc > 2) rng = (uint32_t)strtoul(argv[2], NULL, 0);
    bad = coverage_check();
    printf("coverage check (fans of 3..11 triangles, 200 runs): %d violations\n", bad);
    snprintf(p, sizeof p, "%s/jobs.memh", argv[1]); fj = fopen(p, "w");
    snprintf(p, sizeof p, "%s/expect.memh", argv[1]); fe = fopen(p, "w");
    if (!fj || !fe) { perror("open"); return 2; }
    cyc_scan = 0;
    /* directed tiles */
    begin(0, 0, 0x0000, 0xFFFF);                           /* one triangle, z test vs cleared depth */
    { vtx a = { 2 * 16, 2 * 16, 1000 }, b = { 30 * 16, 4 * 16, 2000 }, c = { 10 * 16, 29 * 16, 3000 }; job_tri(a, b, c, 0xF800); ntris++; }
    jw(3); emit_tile(); ntiles++;
    begin(32, 0, 0x001F, 0xFFFF);                          /* two overlapping triangles: nearer one wins */
    { vtx a = { 32 * 16, 0, 5000 }, b = { 64 * 16, 0, 5000 }, c = { 48 * 16, 32 * 16, 5000 }; job_tri(a, b, c, 0x07E0); ntris++; }
    { vtx a = { 40 * 16, 0, 3000 }, b = { 60 * 16, 20 * 16, 9000 }, c = { 34 * 16, 30 * 16, 100 }; job_tri(a, b, c, 0xFFE0); ntris++; }
    jw(3); emit_tile(); ntiles++;
    begin(64, 32, 0x0841, 0x8000);                         /* split quad: shared diagonal, exactly-once coverage */
    { vtx a = { 66 * 16 + 8, 34 * 16 + 8, 100 }, b = { 94 * 16 + 8, 36 * 16 + 8, 100 }, c = { 92 * 16 + 8, 62 * 16 + 8, 100 },
          d = { 68 * 16 + 8, 60 * 16 + 8, 100 };
      job_tri(a, b, c, 0x1111); job_tri(a, c, d, 0x2222); ntris += 2; }
    jw(3); emit_tile(); ntiles++;
    begin(0, 32, 0x0000, 0xFFFF);                          /* degenerate + clockwise + out-of-tile triangles */
    { vtx a = { 5 * 16, 40 * 16, 1 }, b = { 20 * 16, 40 * 16, 1 }, c = { 35 * 16, 40 * 16, 1 }; job_tri(a, b, c, 0xFFFF); ntris++; }
    { vtx a = { 2 * 16, 34 * 16, 70 }, b = { 3 * 16, 62 * 16, 80 }, c = { 30 * 16, 50 * 16, 60 }; job_tri(a, b, c, 0xABCD); ntris++; }
    { vtx a = { 200 * 16, 200 * 16, 1 }, b = { 220 * 16, 200 * 16, 1 }, c = { 210 * 16, 230 * 16, 1 }; job_tri(a, b, c, 0x1357); ntris++; }
    { vtx a = { -100 * 16, 20 * 16, 9 }, b = { 100 * 16, 40 * 16, 9 }, c = { -50 * 16, 120 * 16, 9 }; job_tri(a, b, c, 0x2468); ntris++; }
    jw(3); emit_tile(); ntiles++;
    begin(96, 64, 0x0000, 0xFFFF);                         /* equal depth: strict less-than keeps the first */
    { vtx a = { 97 * 16, 65 * 16, 7777 }, b = { 126 * 16, 66 * 16, 7777 }, c = { 100 * 16, 94 * 16, 7777 }; job_tri(a, b, c, 0x07E0); ntris++; }
    { vtx a = { 99 * 16, 64 * 16, 7777 }, b = { 127 * 16, 90 * 16, 7777 }, c = { 98 * 16, 95 * 16, 7777 }; job_tri(a, b, c, 0xF81F); ntris++; }
    jw(3); emit_tile(); ntiles++;
    begin(2016, 2016, 0x0000, 0xFFFF);                     /* coordinate limits: tile at 2016, vertices near +-2048 px */
    { vtx a = { -32760, -32760, 0 }, b = { 32760, 32000, 65535 }, c = { 31000, 32767, 30000 }; job_tri(a, b, c, 0x7BEF); ntris++; }
    { vtx a = { 32767, -32768, 100 }, b = { 32767, 32767, 200 }, c = { -32768, 32767, 50000 }; job_tri(a, b, c, 0x39E7); ntris++; }
    jw(3); emit_tile(); ntiles++;
    /* random tiles */
    for (t = 0; t < 12; t++) {
        int tx = 32 * (int)(rnd() % 10), ty = 32 * (int)(rnd() % 8), n = 1 + (int)(rnd() % 8);
        begin(tx, ty, (uint16_t)rnd(), (uint16_t)(0x8000 | rnd()));
        for (k = 0; k < n; k++) { vtx a = rv(tx, ty, 160), b = rv(tx, ty, 160), c = rv(tx, ty, 160); job_tri(a, b, c, (uint16_t)rnd()); ntris++; }
        jw(3); emit_tile(); ntiles++;
    }
    fclose(fj); fclose(fe);
    snprintf(p, sizeof p, "%s/cases.txt", argv[1]); fj = fopen(p, "w");
    fprintf(fj, "%d tiles %d triangles %ld job words %ld expected words %lld scanned samples\n", ntiles, ntris, nj, ne, cyc_scan);
    fclose(fj);
    printf("%d tiles, %d triangles, %ld job words, %ld expected words, %lld scanned samples\n", ntiles, ntris, nj, ne, cyc_scan);
    printf(bad ? "RASTER_REF_FAIL\n" : "RASTER_REF_PASS\n");
    return bad ? 1 : 0;
}
