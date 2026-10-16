/* ARC-1 R10 -- bit-exact reference model of the 45F GPU, command ABI v1 (abi/r10_gpu_abi.h, abi/R10_GPU_ABI.md).
 * The model is an INTERPRETER of the job-word stream, so the same code checks the RTL, the D213 driver and its own
 * generated vectors. v0 commands keep the exact semantics of tools/raster_ref.c (checked: `gpu_ref run` on the v0
 * vectors must reproduce raster_ref's expect.memh word for word).
 *
 * Arithmetic (all integer, defined here and in R10_GPU_ABI.md):
 *   edges / bounding box / top-left rule / sample positions: identical to v0.
 *   attributes Z = z, UQ = u*q, VQ = v*q, Q = q per vertex; plane gradient g = sat40(trunc((n << 16) / A)),
 *   per-sample value a = ((a0 << 16) + gx*(sx - x0) + gy*(sy - y0)) >> 16 (arithmetic shift, exact int64).
 *   perspective: qs = clamp(Q, 1, 65535); us = trunc(UQ / qs), vs = trunc(VQ / qs) (12.4 texel units);
 *   texel = us >> 4 (floor); repeat: & (W-1); clamp: [0, W-1].
 *   colour pipeline in 8 bits per channel (565 -> 888 by bit replication): texel or flat colour, colour key,
 *   modulate (c * (m + 1)) >> 8, fog (c*(32-f) + fog*f) >> 5, blend with the tile colour, quantise to 565 with an
 *   optional 4x4 Bayer offset.
 * Usage: gpu_ref gen <outdir>      -> jobs.memh, expect.memh, cases.txt, and the self-checks
 *        gpu_ref run <jobs> <out>  -> interpret any job stream (v0 or v1), write the expected output words
 * HOST_TESTED. */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../abi/r10_gpu_abi.h"

#define TS 32
#define SDRAM_WORDS (1u << 24)

static uint16_t col[TS * TS], zb[TS * TS];
static int tile_x, tile_y;
static uint32_t reg[GPU_R_COUNT];
static uint16_t pal[256];
static uint16_t *sdram;
static long long st_samples, st_tris, st_texels, st_bad_cmd;

/* debug capture for the perspective self-check: texel-space coordinates of the last TRI_TEX, per tile pixel */
static int dbg_on;
static int32_t dbg_u[TS * TS], dbg_v[TS * TS];
static uint8_t dbg_hit[TS * TS];

static uint32_t crc32_bytes(uint32_t c, const uint8_t *p, size_t n)
{
    size_t i; int k;
    c = ~c;
    for (i = 0; i < n; i++) { c ^= p[i]; for (k = 0; k < 8; k++) c = (c & 1u) ? (c >> 1) ^ 0xEDB88320u : (c >> 1); }
    return ~c;
}
static int64_t sat32(int64_t v) { return v > 2147483647LL ? 2147483647LL : v < -2147483648LL ? -2147483648LL : v; }

typedef struct { int32_t x, y; uint16_t z, q; int16_t u, v; } vtx;

/* ---------------- shared setup ---------------- */
typedef struct {
    vtx v0, v1, v2;
    int64_t A;
    int tl[3];
    int32_t ax[3], ay[3], bx[3], by[3];
    int32_t bx0, by0, bx1, by1;
} setup_t;

static int setup(setup_t *s, vtx v0, vtx v1, vtx v2)
{
    vtx t;
    int i;
    s->A = (int64_t)(v1.x - v0.x) * (v2.y - v0.y) - (int64_t)(v2.x - v0.x) * (v1.y - v0.y);
    if (s->A == 0) return 0;
    if (s->A < 0) { t = v1; v1 = v2; v2 = t; s->A = -s->A; }
    s->v0 = v0; s->v1 = v1; s->v2 = v2;
    s->ax[0] = v1.x; s->ay[0] = v1.y; s->bx[0] = v2.x; s->by[0] = v2.y;
    s->ax[1] = v2.x; s->ay[1] = v2.y; s->bx[1] = v0.x; s->by[1] = v0.y;
    s->ax[2] = v0.x; s->ay[2] = v0.y; s->bx[2] = v1.x; s->by[2] = v1.y;
    for (i = 0; i < 3; i++) {
        int32_t dx = s->bx[i] - s->ax[i], dy = s->by[i] - s->ay[i];
        s->tl[i] = dy < 0 || (dy == 0 && dx > 0);
    }
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
        s->bx0 = (mnx - 8 + 15) >> 4; s->bx1 = (mxx - 8) >> 4;
        s->by0 = (mny - 8 + 15) >> 4; s->by1 = (mxy - 8) >> 4;
        if (s->bx0 < tile_x) s->bx0 = tile_x;
        if (s->by0 < tile_y) s->by0 = tile_y;
        if (s->bx1 > tile_x + TS - 1) s->bx1 = tile_x + TS - 1;
        if (s->by1 > tile_y + TS - 1) s->by1 = tile_y + TS - 1;
    }
    return s->bx0 <= s->bx1 && s->by0 <= s->by1;
}
static int inside(const setup_t *s, int32_t sx, int32_t sy)
{
    int i;
    for (i = 0; i < 3; i++) {
        int64_t e = (int64_t)(s->bx[i] - s->ax[i]) * (sy - s->ay[i]) - (int64_t)(s->by[i] - s->ay[i]) * (sx - s->ax[i]);
        if (!(e > 0 || (e == 0 && s->tl[i]))) return 0;
    }
    return 1;
}
/* plane gradients of an attribute with values a0, a1, a2 at v0, v1, v2 (after the swap) */
static void grad(const setup_t *s, int64_t a0, int64_t a1, int64_t a2, int satbits40, int64_t *gx, int64_t *gy)
{
    int64_t dx1 = s->v1.x - s->v0.x, dy1 = s->v1.y - s->v0.y, dx2 = s->v2.x - s->v0.x, dy2 = s->v2.y - s->v0.y;
    int64_t d1 = a1 - a0, d2 = a2 - a0;
    /* |d| < 2^32 and |dx|,|dy| < 2^17: products < 2^49, n*65536 < 2^66 -> use __int128 for the exact quotient */
    __int128 nx = (__int128)d1 * dy2 - (__int128)d2 * dy1;
    __int128 ny = (__int128)d2 * dx1 - (__int128)d1 * dx2;
    __int128 qx = (nx * 65536) / s->A, qy = (ny * 65536) / s->A;
    if (satbits40) {
        const __int128 m = ((__int128)1 << 39) - 1;
        *gx = (int64_t)(qx > m ? m : qx < -m - 1 ? -m - 1 : qx);
        *gy = (int64_t)(qy > m ? m : qy < -m - 1 ? -m - 1 : qy);
    } else {
        *gx = sat32((int64_t)(qx > INT64_MAX ? INT64_MAX : qx < INT64_MIN ? INT64_MIN : qx));
        *gy = sat32((int64_t)(qy > INT64_MAX ? INT64_MAX : qy < INT64_MIN ? INT64_MIN : qy));
    }
}
static int64_t interp(int64_t a0, int64_t gx, int64_t gy, int32_t dx, int32_t dy)
{
    return ((a0 << 16) + gx * dx + gy * dy) >> 16;     /* exact: |terms| < 2^57 */
}

/* ---------------- v0 flat triangle (exact raster_ref semantics) ---------------- */
static void tri_flat(vtx v0, vtx v1, vtx v2, uint16_t rgb)
{
    setup_t s;
    int64_t gx, gy;
    int32_t px, py;
    if (!setup(&s, v0, v1, v2)) { st_tris++; return; }
    st_tris++;
    grad(&s, s.v0.z, s.v1.z, s.v2.z, 0, &gx, &gy);
    st_samples += (long long)(s.bx1 - s.bx0 + 1) * (s.by1 - s.by0 + 1);
    for (py = s.by0; py <= s.by1; py++)
        for (px = s.bx0; px <= s.bx1; px++) {
            int32_t sx = 16 * px + 8, sy = 16 * py + 8;
            int a = (py - tile_y) * TS + (px - tile_x);
            int64_t z;
            if (!inside(&s, sx, sy)) continue;
            z = interp(s.v0.z, gx, gy, sx - s.v0.x, sy - s.v0.y);
            if (z < 0) z = 0;
            if (z > 65535) z = 65535;
            if ((uint16_t)z < zb[a]) { zb[a] = (uint16_t)z; col[a] = rgb; }
        }
}

/* ---------------- v1 colour pipeline ---------------- */
static const uint8_t bayer4[4][4] = { { 0, 8, 2, 10 }, { 12, 4, 14, 6 }, { 3, 11, 1, 9 }, { 15, 7, 13, 5 } };
static void to888(uint16_t c, int o[3])
{
    int r = c >> 11, g = (c >> 5) & 63, b = c & 31;
    o[0] = (r << 3) | (r >> 2); o[1] = (g << 2) | (g >> 4); o[2] = (b << 3) | (b >> 2);
}
static uint16_t to565(const int c[3], int dither, int px, int py)
{
    int r, g, b;
    if (dither) {
#ifdef MUTANT_GPU_NO_DITHER
        int d = 0;
        (void)px; (void)py;
#else
        int d = bayer4[py & 3][px & 3];
#endif
        r = (c[0] + (d >> 1)) >> 3; g = (c[1] + (d >> 2)) >> 2; b = (c[2] + (d >> 1)) >> 3;
        if (r > 31) r = 31;
        if (g > 63) g = 63;
        if (b > 31) b = 31;
    } else { r = c[0] >> 3; g = c[1] >> 2; b = c[2] >> 3; }
    return (uint16_t)(r << 11 | g << 5 | b);
}
static uint16_t texel_fetch(int32_t us, int32_t vs)
{
    uint32_t cfg = reg[GPU_R_TEX_CFG];
    int lw = (int)(cfg & 15u), lh = (int)((cfg >> 4) & 15u), fmt = (int)((cfg >> 8) & 3u);
    int32_t W = 1 << lw, H = 1 << lh, tu = us >> 4, tv = vs >> 4;
    uint32_t idx, word;
    if (cfg & (1u << 10)) { tu = tu < 0 ? 0 : tu >= W ? W - 1 : tu; } else tu &= W - 1;
    if (cfg & (1u << 11)) { tv = tv < 0 ? 0 : tv >= H ? H - 1 : tv; } else tv &= H - 1;
    idx = ((uint32_t)tv << lw) + (uint32_t)tu;
    st_texels++;
    if (fmt == GPU_FMT_RGB565) return sdram[(reg[GPU_R_TEX_BASE] + idx) & (SDRAM_WORDS - 1)];
    word = sdram[(reg[GPU_R_TEX_BASE] + (idx >> 1)) & (SDRAM_WORDS - 1)];
    return pal[(idx & 1u) ? (word >> 8) : (word & 0xFFu)];
}

static void tri_tex(vtx v0, vtx v1, vtx v2, uint16_t rgb)
{
    setup_t s;
    int64_t gzx, gzy, gux, guy, gvx, gvy, gqx, gqy, u0, u1, u2, w0, w1, w2;
    int32_t px, py;
    uint32_t mode = reg[GPU_R_MODE], cfg = reg[GPU_R_TEX_CFG];
    int fmt = (int)((cfg >> 8) & 3u), a = (int)(reg[GPU_R_ALPHA] & 63u);
    int sx0 = (int)(reg[GPU_R_SCISSOR_X] & 0xFFFFu), sx1 = (int)(reg[GPU_R_SCISSOR_X] >> 16);
    int sy0 = (int)(reg[GPU_R_SCISSOR_Y] & 0xFFFFu), sy1 = (int)(reg[GPU_R_SCISSOR_Y] >> 16);
    int fogc[3], mc[3];
    if (a > 32) a = 32;
    to888((uint16_t)reg[GPU_R_FOG_COLOR], fogc);
    to888(rgb, mc);
    st_tris++;
    if (!setup(&s, v0, v1, v2)) return;
    grad(&s, s.v0.z, s.v1.z, s.v2.z, 0, &gzx, &gzy);
    u0 = (int64_t)s.v0.u * s.v0.q; u1 = (int64_t)s.v1.u * s.v1.q; u2 = (int64_t)s.v2.u * s.v2.q;
    grad(&s, u0, u1, u2, 1, &gux, &guy);
    w0 = (int64_t)s.v0.v * s.v0.q; w1 = (int64_t)s.v1.v * s.v1.q; w2 = (int64_t)s.v2.v * s.v2.q;
    grad(&s, w0, w1, w2, 1, &gvx, &gvy);
    grad(&s, s.v0.q, s.v1.q, s.v2.q, 1, &gqx, &gqy);
    st_samples += (long long)(s.bx1 - s.bx0 + 1) * (s.by1 - s.by0 + 1);
    for (py = s.by0; py <= s.by1; py++)
        for (px = s.bx0; px <= s.bx1; px++) {
            int32_t sx = 16 * px + 8, sy = 16 * py + 8, dx = sx - s.v0.x, dy = sy - s.v0.y;
            int ai = (py - tile_y) * TS + (px - tile_x);
            int64_t z, q, uq, vq;
            int32_t us = 0, vs = 0;
            int c[3], d[3], k;
            uint16_t src;
            if (!inside(&s, sx, sy)) continue;
            if ((mode & GPU_M_SCISSOR) && (px < sx0 || px > sx1 || py < sy0 || py > sy1)) continue;
            z = interp(s.v0.z, gzx, gzy, dx, dy);
            if (z < 0) z = 0;
            if (z > 65535) z = 65535;
            if ((mode & GPU_M_ZTEST) && !((uint16_t)z < zb[ai])) continue;
            if (fmt != GPU_FMT_NONE) {
                q = interp(s.v0.q, gqx, gqy, dx, dy);
                if (q < 1) q = 1;
                if (q > 65535) q = 65535;
                uq = interp(u0, gux, guy, dx, dy);
                vq = interp(w0, gvx, gvy, dx, dy);
#ifdef MUTANT_GPU_AFFINE
                us = (int32_t)interp(s.v0.u, gux >> 16, guy >> 16, dx, dy); vs = (int32_t)interp(s.v0.v, gvx >> 16, gvy >> 16, dx, dy);
                (void)uq; (void)vq;
#else
                us = (int32_t)sat32(uq / q); vs = (int32_t)sat32(vq / q);
#endif
                if (dbg_on) { dbg_u[ai] = us; dbg_v[ai] = vs; dbg_hit[ai] = 1; }
                src = texel_fetch(us, vs);
                if ((mode & GPU_M_KEY) && src == (uint16_t)reg[GPU_R_COLOR_KEY]) continue;
                to888(src, c);
                if (mode & GPU_M_MODULATE) for (k = 0; k < 3; k++) c[k] = (c[k] * (mc[k] + 1)) >> 8;
            } else for (k = 0; k < 3; k++) c[k] = mc[k];
            if (mode & GPU_M_FOG) {
                int64_t f = (((int64_t)z - (int64_t)(reg[GPU_R_FOG] & 0xFFFFu)) * (int64_t)(reg[GPU_R_FOG] >> 16)) >> 16;
                if (f < 0) f = 0;
                if (f > 32) f = 32;
                for (k = 0; k < 3; k++) c[k] = (int)((c[k] * (32 - f) + fogc[k] * f) >> 5);
            }
            to888(col[ai], d);
            switch (mode & GPU_M_BLEND_MASK) {
#ifdef MUTANT_GPU_ALPHA_SWAP
            case GPU_M_BLEND_ALPHA: for (k = 0; k < 3; k++) c[k] = (c[k] * (32 - a) + d[k] * a) >> 5; break;
#else
            case GPU_M_BLEND_ALPHA: for (k = 0; k < 3; k++) c[k] = (c[k] * a + d[k] * (32 - a)) >> 5; break;
#endif
            case GPU_M_BLEND_ADD:   for (k = 0; k < 3; k++) { c[k] += d[k]; if (c[k] > 255) c[k] = 255; } break;
            default: break;
            }
            col[ai] = to565(c, (mode & GPU_M_DITHER) != 0, px, py);
            if (mode & GPU_M_ZWRITE) zb[ai] = (uint16_t)z;
        }
}

/* ---------------- interpreter ---------------- */
static uint16_t *out_w; static long out_n, out_cap;
static void ow(uint16_t w) { if (out_n == out_cap) { out_cap = out_cap ? 2 * out_cap : 65536; out_w = realloc(out_w, (size_t)out_cap * 2); } out_w[out_n++] = w; }
static void emit_tile(void)
{
    uint8_t b[TS * TS * 2];
    uint32_t c;
    int i;
    ow(GPU_TILE_MAGIC); ow((uint16_t)tile_x); ow((uint16_t)tile_y);
    for (i = 0; i < TS * TS; i++) { ow(col[i]); b[2 * i] = (uint8_t)col[i]; b[2 * i + 1] = (uint8_t)(col[i] >> 8); }
    c = crc32_bytes(0, b, sizeof b);
    ow((uint16_t)c); ow((uint16_t)(c >> 16));
}
static vtx rd_vtx_flat(const uint16_t *w) { vtx v; memset(&v, 0, sizeof v); v.x = (int16_t)w[0]; v.y = (int16_t)w[1]; return v; }
/* returns words consumed, 0 = truncated (stops interpretation) */
static long exec1(const uint16_t *w, long n)
{
    long k, m;
    switch (w[0]) {
    case GPU_TILE_BEGIN:
        if (n < 5) return 0;
        tile_x = w[1]; tile_y = w[2];
        for (k = 0; k < TS * TS; k++) { col[k] = w[3]; zb[k] = w[4]; }
        return 5;
    case GPU_TRI_FLAT: {
        vtx a, b, c;
        if (n < 11) return 0;
        a = rd_vtx_flat(w + 1); b = rd_vtx_flat(w + 3); c = rd_vtx_flat(w + 5);
        a.z = w[7]; b.z = w[8]; c.z = w[9];
        tri_flat(a, b, c, w[10]);
        return 11; }
    case GPU_TILE_END: emit_tile(); return 1;
    case GPU_SET_REG:
        if (n < 4) return 0;
        if (w[1] < GPU_R_COUNT) reg[w[1]] = (uint32_t)w[2] | (uint32_t)w[3] << 16; else st_bad_cmd++;
        return 4;
    case GPU_TRI_TEX: {
        vtx v[3];
        int i;
        if (n < (long)GPU_TRI_TEX_WORDS) return 0;
        for (i = 0; i < 3; i++) {
            const uint16_t *p = w + 1 + 6 * i;
            v[i].x = (int16_t)p[0]; v[i].y = (int16_t)p[1]; v[i].z = p[2]; v[i].q = p[3]; v[i].u = (int16_t)p[4]; v[i].v = (int16_t)p[5];
        }
        tri_tex(v[0], v[1], v[2], w[19]);
        return GPU_TRI_TEX_WORDS; }
    case GPU_UPLOAD_TEX: {
        uint32_t addr;
        if (n < 4) return 0;
        addr = (uint32_t)w[1] | (uint32_t)w[2] << 16; m = w[3];
        if (m > (long)GPU_UPLOAD_MAX || n < 4 + m) return 0;
        for (k = 0; k < m; k++) sdram[(addr + (uint32_t)k) & (SDRAM_WORDS - 1)] = w[4 + k];
        return 4 + m; }
    case GPU_UPLOAD_PAL:
        if (n < 3) return 0;
        m = w[2];
        if (n < 3 + m || w[1] + m > 256) return 0;
        for (k = 0; k < m; k++) pal[w[1] + k] = w[3 + k];
        return 3 + m;
    default:
        st_bad_cmd++;
        return 1;
    }
}
static void exec_stream(const uint16_t *w, long n)
{
    long p = 0, c;
    while (p < n && (c = exec1(w + p, n - p)) > 0) p += c;
}
static void reset_state(void)
{
    memset(reg, 0, sizeof reg); memset(pal, 0, sizeof pal); memset(sdram, 0, (size_t)SDRAM_WORDS * 2);
    st_samples = st_tris = st_texels = st_bad_cmd = 0; out_n = 0;
}

/* ---------------- stream builder ---------------- */
static uint16_t *jb; static long jn, jcap;
static void jw(uint32_t w) { if (jn == jcap) { jcap = jcap ? 2 * jcap : 65536; jb = realloc(jb, (size_t)jcap * 2); } jb[jn++] = (uint16_t)w; }
static void j_reg(unsigned r, uint32_t v) { jw(GPU_SET_REG); jw(r); jw(v & 0xFFFFu); jw(v >> 16); }
static void j_begin(int tx, int ty, uint16_t cc, uint16_t cz) { jw(GPU_TILE_BEGIN); jw((uint32_t)tx); jw((uint32_t)ty); jw(cc); jw(cz); }
static void j_end(void) { jw(GPU_TILE_END); }
static void j_tri(const vtx *a, const vtx *b, const vtx *c, uint16_t rgb)
{
    const vtx *v[3] = { a, b, c };
    int i;
    jw(GPU_TRI_TEX);
    for (i = 0; i < 3; i++) { jw((uint16_t)v[i]->x); jw((uint16_t)v[i]->y); jw(v[i]->z); jw(v[i]->q); jw((uint16_t)v[i]->u); jw((uint16_t)v[i]->v); }
    jw(rgb);
}
static void j_upload(uint32_t addr, const uint16_t *d, long n)
{
    long k, o = 0;
    while (o < n) {
        long m = n - o > (long)GPU_UPLOAD_MAX ? (long)GPU_UPLOAD_MAX : n - o;
        jw(GPU_UPLOAD_TEX); jw((addr + (uint32_t)o) & 0xFFFFu); jw((addr + (uint32_t)o) >> 16); jw((uint32_t)m);
        for (k = 0; k < m; k++) jw(d[o + k]);
        o += m;
    }
}
static vtx V(double px, double py, int z, double w, double tu, double tv)
{
    vtx v;
    v.x = (int32_t)lround(px * 16); v.y = (int32_t)lround(py * 16); v.z = (uint16_t)z;
    v.q = (uint16_t)lround(65535.0 / w); v.u = (int16_t)lround(tu * 16); v.v = (int16_t)lround(tv * 16);
    return v;
}

static uint32_t rng = 777;
static uint32_t rnd(void) { rng = rng * 1664525u + 1013904223u; return rng >> 8; }

/* ---------------- self-checks ---------------- */
static int fails;
#define SC(c, msg) do { if (!(c)) { fails++; printf("SELFCHECK_FAIL %s\n", msg); } } while (0)

/* run one tile through the interpreter and return its colours */
static void run_tile_stream(void) { out_n = 0; exec_stream(jb, jn); jn = 0; }

static void selfchecks(void)
{
    static uint16_t tex[64 * 64], tex8[32 * 32 / 2];
    int i, x, y, n = 0;
    double sumerr = 0, maxerr = 0;
    for (y = 0; y < 64; y++) for (x = 0; x < 64; x++) tex[y * 64 + x] = (uint16_t)(((x * 4) >> 3) << 11 | ((y * 4) >> 2) << 5 | (((x ^ y) & 8) ? 31 : 0));
    for (i = 0; i < 32 * 32 / 2; i++) tex8[i] = (uint16_t)((2 * i) & 0xFF) | (uint16_t)(((2 * i + 1) & 0xFF) << 8);
    reset_state();
    j_upload(0x1000, tex, 64 * 64);
    j_upload(0x3000, tex8, 32 * 32 / 2);
    run_tile_stream();
    SC(sdram[0x1000 + 65] == tex[65] && sdram[0x3000 + 3] == tex8[3], "upload");

    /* perspective: a quad receding in depth (w 1..4), u/v compared with a double-precision reference */
    j_reg(GPU_R_TEX_BASE, 0x1000); j_reg(GPU_R_TEX_CFG, 6 | 6 << 4); j_reg(GPU_R_MODE, GPU_M_ZTEST | GPU_M_ZWRITE);
    j_begin(0, 0, 0, 0xFFFF);
    {
        vtx a = V(1.3, 2.1, 100, 1.0, 0, 0), b = V(30.7, 3.4, 400, 4.0, 63, 0), c = V(4.2, 29.6, 250, 2.0, 0, 63);
        double ax = a.x / 16.0, ay = a.y / 16.0, bxx = b.x / 16.0, byy = b.y / 16.0, cx = c.x / 16.0, cy = c.y / 16.0;
        double qa = a.q, qb = b.q, qc = c.q;
        j_tri(&a, &b, &c, 0); j_end();
        dbg_on = 1; memset(dbg_hit, 0, sizeof dbg_hit);
        run_tile_stream();
        dbg_on = 0;
        for (i = 0; i < TS * TS; i++) if (dbg_hit[i]) {
            double sx = (i % TS) + 0.5, sy = (i / TS) + 0.5, den = (bxx - ax) * (cy - ay) - (cx - ax) * (byy - ay);
            double l1 = ((sx - ax) * (cy - ay) - (cx - ax) * (sy - ay)) / den, l2 = ((bxx - ax) * (sy - ay) - (sx - ax) * (byy - ay)) / den;
            double l0 = 1 - l1 - l2, Q = l0 * qa + l1 * qb + l2 * qc;
            double u = (l0 * qa * a.u + l1 * qb * b.u + l2 * qc * c.u) / Q, v = (l0 * qa * a.v + l1 * qb * b.v + l2 * qc * c.v) / Q;
            double eu = fabs(u - dbg_u[i]), ev = fabs(v - dbg_v[i]);
            if (eu > maxerr) maxerr = eu;
            if (ev > maxerr) maxerr = ev;
            sumerr += fabs(u - dbg_u[i]) + fabs(v - dbg_v[i]); n += 2;
        }
    }
    printf("perspective check: %d samples, max |error| %.3f/16 texel, mean %.3f/16 texel\n", n / 2, maxerr, n ? sumerr / n : 0.0);
    SC(n > 200 && maxerr < 2.0, "perspective-correct u/v within 2/16 texel of the double reference");

    /* colour key: key texels leave the clear colour; alpha 32 == replace; alpha 0 == untouched; additive saturates */
    {
        uint16_t key = sdram[0x1000 + 9 * 64 + 9];
        int same = 0, total = 0, kept = 0;
        vtx a = V(0, 0, 10, 1, 0, 0), b = V(32, 0, 10, 1, 32, 0), c = V(0, 32, 10, 1, 0, 32), d = V(32, 32, 10, 1, 32, 32);
        uint16_t ref[TS * TS];
        j_reg(GPU_R_MODE, 0); j_begin(0, 0, 0x1234, 0xFFFF); j_tri(&a, &b, &c, 0); j_tri(&b, &d, &c, 0); j_end();
        run_tile_stream(); memcpy(ref, out_w + 3, sizeof ref);
        j_reg(GPU_R_MODE, GPU_M_KEY); j_reg(GPU_R_COLOR_KEY, key);
        j_begin(0, 0, 0x1234, 0xFFFF); j_tri(&a, &b, &c, 0); j_tri(&b, &d, &c, 0); j_end();
        run_tile_stream();
        for (i = 0; i < TS * TS; i++) { total++; if (ref[i] == key) { if (out_w[3 + i] == 0x1234) kept++; } else if (out_w[3 + i] == ref[i]) same++; }
        SC(kept > 0 && kept + same == total, "colour key: key texels transparent, others unchanged");
        j_reg(GPU_R_MODE, GPU_M_BLEND_ALPHA); j_reg(GPU_R_ALPHA, 32);
        j_begin(0, 0, 0x1234, 0xFFFF); j_tri(&a, &b, &c, 0); j_tri(&b, &d, &c, 0); j_end(); run_tile_stream();
        SC(memcmp(out_w + 3, ref, sizeof ref) == 0, "alpha 32 == replace");
        j_reg(GPU_R_ALPHA, 0);
        j_begin(0, 0, 0x1234, 0xFFFF); j_tri(&a, &b, &c, 0); j_tri(&b, &d, &c, 0); j_end(); run_tile_stream();
        for (i = 0, same = 0; i < TS * TS; i++) same += out_w[3 + i] == 0x1234;
        SC(same == TS * TS, "alpha 0 leaves the tile");
        j_reg(GPU_R_MODE, GPU_M_BLEND_ADD); j_reg(GPU_R_TEX_CFG, GPU_FMT_NONE << 8);
        j_begin(0, 0, 0xFFFF, 0xFFFF); j_tri(&a, &b, &c, 0x0841); j_end(); run_tile_stream();
        for (i = 0, same = 0; i < TS * TS; i++) same += out_w[3 + i] == 0xFFFF;
        SC(same == TS * TS, "additive blend saturates");
    }
    /* fog endpoints, scissor, I8 palette */
    {
        vtx a = V(0, 0, 1000, 1, 0, 0), b = V(64, 0, 1000, 1, 0, 0), c = V(0, 64, 1000, 1, 0, 0);
        int okf = 1, oks = 1, okp = 1;
        j_reg(GPU_R_TEX_CFG, GPU_FMT_NONE << 8); j_reg(GPU_R_FOG_COLOR, 0x07E0);
        j_reg(GPU_R_MODE, GPU_M_FOG); j_reg(GPU_R_FOG, 2000u | 1000u << 16);              /* z 1000 < start: no fog */
        j_begin(0, 0, 0, 0xFFFF); j_tri(&a, &b, &c, 0xF800); j_end(); run_tile_stream();
        for (i = 0; i < TS * TS; i++) okf &= out_w[3 + i] == 0xF800;
        j_reg(GPU_R_FOG, 0u | 0xFFFFu << 16);                                               /* saturated: all fog */
        j_begin(0, 0, 0, 0xFFFF); j_tri(&a, &b, &c, 0xF800); j_end(); run_tile_stream();
        for (i = 0; i < TS * TS; i++) okf &= out_w[3 + i] == 0x07E0;
        SC(okf, "fog endpoints");
        j_reg(GPU_R_MODE, GPU_M_SCISSOR); j_reg(GPU_R_SCISSOR_X, 5u | 9u << 16); j_reg(GPU_R_SCISSOR_Y, 20u | 20u << 16);
        j_begin(0, 0, 0, 0xFFFF); j_tri(&a, &b, &c, 0xF800); j_end(); run_tile_stream();
        for (i = 0; i < TS * TS; i++) { int px = i % TS, py = i / TS, in = px >= 5 && px <= 9 && py == 20; oks &= out_w[3 + i] == (in ? 0xF800 : 0); }
        SC(oks, "scissor");
        for (i = 0; i < 256; i++) pal[i] = 0;
        { uint16_t p2[256]; for (i = 0; i < 256; i++) p2[i] = (uint16_t)(i * 257u);
          jw(GPU_UPLOAD_PAL); jw(0); jw(256); for (i = 0; i < 256; i++) jw(p2[i]); }
        j_reg(GPU_R_MODE, 0); j_reg(GPU_R_TEX_BASE, 0x3000); j_reg(GPU_R_TEX_CFG, 5 | 5 << 4 | GPU_FMT_I8 << 8);
        { vtx e = V(0, 0, 9, 1, 0, 0), f = V(64, 0, 9, 1, 64, 0), g = V(0, 64, 9, 1, 0, 64);
          j_begin(0, 0, 0, 0xFFFF); j_tri(&e, &f, &g, 0); j_end(); run_tile_stream(); }
        for (i = 0; i < TS * TS; i++) { int idx = ((i / TS) * 32 + i % TS) & 0xFF; okp &= out_w[3 + i] == (uint16_t)(idx * 257u); }
        SC(okp, "I8 palette lookup");
    }
    /* dither: a flat mid-grey that is not representable averages to the 8-bit value */
    {
        vtx a = V(0, 0, 9, 1, 0, 0), b = V(64, 0, 9, 1, 0, 0), c = V(0, 64, 9, 1, 0, 0);
        long sum = 0;
        j_reg(GPU_R_TEX_CFG, GPU_FMT_NONE << 8); j_reg(GPU_R_MODE, GPU_M_DITHER | GPU_M_BLEND_ALPHA); j_reg(GPU_R_ALPHA, 16);
        j_begin(0, 0, 0x0000, 0xFFFF); j_tri(&a, &b, &c, 0x8410); j_end(); run_tile_stream();
        for (i = 0; i < TS * TS; i++) sum += out_w[3 + i] >> 11;
        /* source 0x8410 -> r8 = 132, blended 50 % with 0 -> 66 -> 66/8 = 8.25 levels: dithered mean must be ~8.25 */
        SC(sum > 8 * TS * TS && sum < 9 * TS * TS, "dither average between levels");
        printf("dither check: mean red level %.3f (ideal 8.25)\n", (double)sum / (TS * TS));
    }
}

/* ---------------- vector generation ---------------- */
static int gen(const char *dir)
{
    static uint16_t tex[128 * 128], tex8[64 * 64 / 2], p2[256];
    char p[512];
    FILE *f;
    long k;
    int t, i, ntiles = 0, ntri = 0;
    for (i = 0; i < 128 * 128; i++) tex[i] = (uint16_t)(rnd() & 0xFFFF);
    for (i = 0; i < 64 * 64 / 2; i++) tex8[i] = (uint16_t)rnd();
    for (i = 0; i < 256; i++) p2[i] = (uint16_t)rnd();
    reset_state(); jn = 0;
    j_upload(0x020000, tex, 128 * 128);
    j_upload(0x100000, tex8, 64 * 64 / 2);
    jw(GPU_UPLOAD_PAL); jw(0); jw(256); for (i = 0; i < 256; i++) jw(p2[i]);
    for (t = 0; t < 24; t++) {
        int tx = 32 * (int)(rnd() % 20), ty = 32 * (int)(rnd() % 15), n = 1 + (int)(rnd() % 6);
        uint32_t mode = rnd() & 0x1FF;
        int fmt = (int)(rnd() % 3); if (fmt == 2) fmt = GPU_FMT_NONE;
        j_reg(GPU_R_MODE, mode);
        j_reg(GPU_R_TEX_BASE, fmt == GPU_FMT_I8 ? 0x100000 : 0x020000);
        j_reg(GPU_R_TEX_CFG, (fmt == GPU_FMT_I8 ? (6u | 6u << 4) : (7u | 7u << 4)) | (uint32_t)fmt << 8 | (rnd() & 3u) << 10);
        j_reg(GPU_R_ALPHA, rnd() % 33); j_reg(GPU_R_FOG_COLOR, rnd() & 0xFFFF); j_reg(GPU_R_FOG, (rnd() & 0xFFFF) | (rnd() & 0x3FF) << 16);
        j_reg(GPU_R_SCISSOR_X, (uint32_t)(tx + (int)(rnd() % 8)) | (uint32_t)(tx + 24 + (int)(rnd() % 8)) << 16);
        j_reg(GPU_R_SCISSOR_Y, (uint32_t)(ty + (int)(rnd() % 8)) | (uint32_t)(ty + 24 + (int)(rnd() % 8)) << 16);
        j_reg(GPU_R_COLOR_KEY, tex[rnd() % (128 * 128)]);
        j_begin(tx, ty, (uint16_t)rnd(), (uint16_t)(0x8000 | rnd()));
        for (k = 0; k < n; k++) {
            vtx v[3];
            for (i = 0; i < 3; i++) {
                double w = 1.0 + (rnd() % 7000) / 1000.0;
                v[i] = V(tx - 10 + (rnd() % 520) / 10.0, ty - 10 + (rnd() % 520) / 10.0, (int)(rnd() & 0xFFFF), w,
                         (int)(rnd() % 600) - 300, (int)(rnd() % 600) - 300);
            }
            j_tri(&v[0], &v[1], &v[2], (uint16_t)rnd()); ntri++;
        }
        if (rnd() & 1) {                                           /* mix in a v0 flat triangle */
            jw(GPU_TRI_FLAT); for (i = 0; i < 6; i++) jw((uint16_t)((i & 1 ? ty : tx) * 16 + (int)(rnd() % 600) - 50));
            jw(rnd()); jw(rnd()); jw(rnd()); jw(rnd()); ntri++;
        }
        j_end(); ntiles++;
    }
    out_n = 0; exec_stream(jb, jn);
    snprintf(p, sizeof p, "%s/gpu_jobs.memh", dir); f = fopen(p, "w"); if (!f) return 2;
    for (k = 0; k < jn; k++) fprintf(f, "%04x\n", jb[k]);
    fclose(f);
    snprintf(p, sizeof p, "%s/gpu_expect.memh", dir); f = fopen(p, "w"); if (!f) return 2;
    for (k = 0; k < out_n; k++) fprintf(f, "%04x\n", out_w[k]);
    fclose(f);
    snprintf(p, sizeof p, "%s/gpu_cases.txt", dir); f = fopen(p, "w");
    fprintf(f, "%d tiles %d triangles %ld job words %ld expected words %lld samples %lld texels\n", ntiles, ntri, jn, out_n, st_samples, st_texels);
    fclose(f);
    printf("vectors: %d tiles, %d triangles, %ld job words, %ld expected words, %lld samples, %lld texel fetches\n",
           ntiles, ntri, jn, out_n, st_samples, st_texels);
    return out_n == (long)ntiles * (long)GPU_TILE_WORDS ? 0 : 1;
}

static long read_memh(const char *path, uint16_t **w)
{
    FILE *f = fopen(path, "r");
    unsigned v;
    long n = 0, cap = 65536;
    if (!f) return -1;
    *w = malloc((size_t)cap * 2);
    while (fscanf(f, "%x", &v) == 1) { if (n == cap) { cap *= 2; *w = realloc(*w, (size_t)cap * 2); } (*w)[n++] = (uint16_t)v; }
    fclose(f);
    return n;
}

/* ---- library API (GPU_REF_LIB): interpret a stream, get the output words ---- */
void gpu_ref_init(void) { if (!sdram) sdram = calloc(SDRAM_WORDS, 2); reset_state(); }
long gpu_ref_exec(const uint16_t *w, long n, const uint16_t **out) { out_n = 0; exec_stream(w, n); *out = out_w; return out_n; }
long long gpu_ref_samples(void) { return st_samples; }
long long gpu_ref_texels(void) { return st_texels; }

#ifndef GPU_REF_LIB
int main(int argc, char **argv)
{
    sdram = calloc(SDRAM_WORDS, 2);
    if (argc >= 4 && strcmp(argv[1], "run") == 0) {
        uint16_t *w;
        long n = read_memh(argv[2], &w), k;
        FILE *f;
        if (n < 0) { perror(argv[2]); return 2; }
        reset_state(); exec_stream(w, n);
        f = fopen(argv[3], "w");
        for (k = 0; k < out_n; k++) fprintf(f, "%04x\n", out_w[k]);
        fclose(f);
        printf("interpreted %ld words -> %ld output words, %lld triangles, %lld bad commands\n", n, out_n, st_tris, st_bad_cmd);
        return 0;
    }
    if (argc >= 3 && strcmp(argv[1], "gen") == 0) {
        int rc;
        selfchecks();
        rc = gen(argv[2]);
        printf(fails || rc ? "GPU_REF_FAIL\n" : "GPU_REF_PASS\n");
        return fails || rc;
    }
    fprintf(stderr, "usage: gpu_ref gen <dir> | gpu_ref run <jobs.memh> <out.memh>\n");
    return 2;
}
#endif
