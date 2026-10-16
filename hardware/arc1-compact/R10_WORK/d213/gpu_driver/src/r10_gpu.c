/* ARC-1 R10 -- D213-side GPU driver core (see include/r10_gpu.h). HOST_TESTED only. */
#include "r10_gpu.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

void gpu_view_default(gpu_view *vp, int width, int height)
{
    vp->width = width; vp->height = height; vp->near_w = 0.05f; vp->guard_px = 1000.0f;
}

/* plane i: distance = a.(x, y, z, w) >= 0 */
static float dist(const gpu_view *vp, int i, const gpu_cv *p)
{
    float kx = 1.0f + 2.0f * vp->guard_px / (float)vp->width, ky = 1.0f + 2.0f * vp->guard_px / (float)vp->height;
    switch (i) {
    case 0: return p->w - vp->near_w;          /* near */
    case 1: return p->w - p->z;                /* far: z <= w */
    case 2: return p->w + p->z;                /* z >= -w */
    case 3: return kx * p->w - p->x;           /* guard band */
    case 4: return kx * p->w + p->x;
    case 5: return ky * p->w - p->y;
    default: return ky * p->w + p->y;
    }
}
static gpu_cv lerp(const gpu_cv *a, const gpu_cv *b, float t)
{
    gpu_cv r;
    r.x = a->x + (b->x - a->x) * t; r.y = a->y + (b->y - a->y) * t; r.z = a->z + (b->z - a->z) * t;
    r.w = a->w + (b->w - a->w) * t; r.u = a->u + (b->u - a->u) * t; r.v = a->v + (b->v - a->v) * t;
    return r;
}

int gpu_clip(const gpu_view *vp, const gpu_cv in[3], gpu_cv out[10])
{
    gpu_cv buf[2][10];
    int n = 3, i, k, cur = 0;
    memcpy(buf[0], in, 3 * sizeof *in);
    for (i = 0; i < 7 && n > 0; i++) {
        gpu_cv *src = buf[cur], *dst = buf[1 - cur];
        int m = 0;
        for (k = 0; k < n; k++) {
            const gpu_cv *a = &src[k], *b = &src[(k + 1) % n];
            float da = dist(vp, i, a), db = dist(vp, i, b);
            if (da >= 0) dst[m++] = *a;
            if ((da >= 0) != (db >= 0) && m < 10) dst[m++] = lerp(a, b, da / (da - db));
        }
        n = m < 3 ? 0 : m; cur = 1 - cur;
    }
    if (n) memcpy(out, buf[cur], (size_t)n * sizeof *out);
    return n;
}

static int16_t fx(float v) { float s = roundf(v * 16.0f); return (int16_t)(s > 32767.0f ? 32767 : s < -32768.0f ? -32768 : s); }

static gpu_sv proj(const gpu_view *vp, const gpu_cv *p, float wmin)
{
    gpu_sv r;
    float iw = 1.0f / p->w, sx = (p->x * iw * 0.5f + 0.5f) * (float)vp->width;
    float sy = (0.5f - p->y * iw * 0.5f) * (float)vp->height, zn = p->z * iw * 0.5f + 0.5f;
    float q = 65535.0f * wmin / p->w;
    r.x = fx(sx); r.y = fx(sy);
    r.z = (uint16_t)(zn <= 0 ? 0 : zn >= 1 ? 65535 : lroundf(zn * 65535.0f));
    r.q = (uint16_t)(q < 1 ? 1 : q > 65535 ? 65535 : lroundf(q));
    r.u = fx(p->u); r.v = fx(p->v);
    return r;
}

/* q is 16 bits scaled to the nearest vertex of each triangle: a far vertex with w = R * w_min keeps 16 - log2(R) bits.
 * Triangles with w_max / w_min > GPU_W_RATIO are split at the midpoint of their longest clip-space edge (linear in clip
 * space, so the split is exact) until every piece keeps at least 13 bits of q. */
#ifndef GPU_W_RATIO
#define GPU_W_RATIO 8.0f
#endif
static int emit_split(const gpu_view *vp, const gpu_cv *a, const gpu_cv *b, const gpu_cv *c, uint16_t rgb, uint8_t state,
                      gpu_stri *out, int room, int depth)
{
    const gpu_cv *v[3] = { a, b, c };
    float wmin = a->w, wmax = a->w;
    int i, k;
    for (i = 1; i < 3; i++) { if (v[i]->w < wmin) wmin = v[i]->w; if (v[i]->w > wmax) wmax = v[i]->w; }
    if (room <= 0) return 0;
    if (wmax > GPU_W_RATIO * wmin && depth < 6 && room >= 2) {
        float best = -1;
        int e = 0;
        gpu_cv m;
        for (i = 0; i < 3; i++) {                              /* longest edge in w (where q varies most) */
            float d = fabsf(v[i]->w - v[(i + 1) % 3]->w);
            if (d > best) { best = d; e = i; }
        }
        m = lerp(v[e], v[(e + 1) % 3], 0.5f);
        k = emit_split(vp, v[e], &m, v[(e + 2) % 3], rgb, state, out, room / 2, depth + 1);
        return k + emit_split(vp, &m, v[(e + 1) % 3], v[(e + 2) % 3], rgb, state, out + k, room - k, depth + 1);
    }
    out->v[0] = proj(vp, a, wmin); out->v[1] = proj(vp, b, wmin); out->v[2] = proj(vp, c, wmin);
    out->rgb = rgb; out->state = state;
    return 1;
}

int gpu_setup_tri(const gpu_view *vp, const gpu_cv in[3], uint16_t rgb, uint8_t state, gpu_stri out[GPU_CLIP_MAX])
{
    gpu_cv p[10];
    int n = gpu_clip(vp, in, p), i, nt = 0;
    for (i = 1; i + 1 < n && nt < GPU_CLIP_MAX; i++)
        nt += emit_split(vp, &p[0], &p[i], &p[i + 1], rgb, state, out + nt, GPU_CLIP_MAX - nt, 0);
    return nt;
}

void gpu_buf_reset(gpu_buf *b) { b->n = 0; }
void gpu_emit(gpu_buf *b, uint16_t w)
{
    if (b->n == b->cap) { b->cap = b->cap ? 2 * b->cap : 65536; b->w = realloc(b->w, (size_t)b->cap * 2); }
    b->w[b->n++] = w;
}
void gpu_emit_upload(gpu_buf *b, uint32_t addr, const uint16_t *data, long n)
{
    long o = 0, k;
    while (o < n) {
        long m = n - o > (long)GPU_UPLOAD_MAX ? (long)GPU_UPLOAD_MAX : n - o;
        gpu_emit(b, GPU_UPLOAD_TEX); gpu_emit(b, (uint16_t)(addr + (uint32_t)o)); gpu_emit(b, (uint16_t)((addr + (uint32_t)o) >> 16));
        gpu_emit(b, (uint16_t)m);
        for (k = 0; k < m; k++) gpu_emit(b, data[o + k]);
        o += m;
    }
}
void gpu_emit_palette(gpu_buf *b, const uint16_t pal[256])
{
    int i;
    gpu_emit(b, GPU_UPLOAD_PAL); gpu_emit(b, 0); gpu_emit(b, 256);
    for (i = 0; i < 256; i++) gpu_emit(b, pal[i]);
}

static void bbox(const gpu_stri *t, int *x0, int *y0, int *x1, int *y1)
{
    int i, mnx = t->v[0].x, mxx = mnx, mny = t->v[0].y, mxy = mny;
    for (i = 1; i < 3; i++) {
        if (t->v[i].x < mnx) mnx = t->v[i].x;
        if (t->v[i].x > mxx) mxx = t->v[i].x;
        if (t->v[i].y < mny) mny = t->v[i].y;
        if (t->v[i].y > mxy) mxy = t->v[i].y;
    }
    *x0 = (mnx - 8 + 15) >> 4; *x1 = (mxx - 8) >> 4; *y0 = (mny - 8 + 15) >> 4; *y1 = (mxy - 8) >> 4;
}

long gpu_emit_frame(gpu_buf *b, const gpu_view *vp, const gpu_stri *t, int n, const gpu_state *states,
                    uint16_t clear_rgb, uint16_t clear_z, int all_tris)
{
    uint32_t held[GPU_R_COUNT];
    int held_valid = 0, tx, ty, i, r;
    long start = b->n;
    for (ty = 0; ty < vp->height; ty += 32)
        for (tx = 0; tx < vp->width; tx += 32) {
            gpu_emit(b, GPU_TILE_BEGIN); gpu_emit(b, (uint16_t)tx); gpu_emit(b, (uint16_t)ty);
            gpu_emit(b, clear_rgb); gpu_emit(b, clear_z);
            for (i = 0; i < n; i++) {
                int x0, y0, x1, y1, k;
                const gpu_state *st = &states[t[i].state];
                bbox(&t[i], &x0, &y0, &x1, &y1);
                if (!all_tris && (x1 < tx || x0 > tx + 31 || y1 < ty || y0 > ty + 31 || x0 > x1 || y0 > y1)) continue;
                for (r = 0; r < (int)GPU_R_COUNT; r++)
                    if (!held_valid || held[r] != st->reg[r]) {
                        gpu_emit(b, GPU_SET_REG); gpu_emit(b, (uint16_t)r);
                        gpu_emit(b, (uint16_t)st->reg[r]); gpu_emit(b, (uint16_t)(st->reg[r] >> 16));
                        held[r] = st->reg[r];
                    }
                held_valid = 1;
                gpu_emit(b, GPU_TRI_TEX);
                for (k = 0; k < 3; k++) {
                    const gpu_sv *v = &t[i].v[k];
                    gpu_emit(b, (uint16_t)v->x); gpu_emit(b, (uint16_t)v->y); gpu_emit(b, v->z); gpu_emit(b, v->q);
                    gpu_emit(b, (uint16_t)v->u); gpu_emit(b, (uint16_t)v->v);
                }
                gpu_emit(b, t[i].rgb);
            }
            gpu_emit(b, GPU_TILE_END);
        }
    return b->n - start;
}
