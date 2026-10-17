/* ARC-1 R10 -- host tests of the D213 GPU driver core against the bit-exact 45F GPU model (fpga45/tools/gpu_ref.c,
 * GPU_REF_LIB) and an independent float reference renderer.
 *   D01..D04 clipping: inside, behind the camera, near-plane crossing, guard band
 *   D05 scene: textured rotating cube + a textured floor that passes behind the camera (near-plane clipping),
 *       320x240, rendered tile by tile through the model; compared with a float renderer pixel by pixel:
 *       every pixel away from triangle edges and texel boundaries must match exactly
 *   D06 binning: the binned frame equals the frame with every triangle sent to every tile
 *   D07 per-frame cost figures for the benchmark (words, samples, texel fetches)
 *   D08 production job plan: one bounded, independently replayable request per tile
 * HOST_TESTED. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "r10_gpu.h"

void gpu_ref_init(void);
long gpu_ref_exec(const uint16_t *w, long n, const uint16_t **out);
long long gpu_ref_samples(void);
long long gpu_ref_texels(void);

static int g_fail, g_checks;
#define CHECK(c) do { g_checks++; if (!(c)) { g_fail++; printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)

#define W 320
#define H 240
static uint16_t tex[64 * 64];
static uint16_t fb_gpu[W * H], fb_ref[W * H], fb_all[W * H];
static int ref_id[W * H];
static float ref_u[W * H], ref_v[W * H];

static gpu_cv cv(float x, float y, float z, float w, float u, float v) { gpu_cv c; c.x = x; c.y = y; c.z = z; c.w = w; c.u = u; c.v = v; return c; }

/* ---- camera ---- */
static gpu_cv project(const float e[3], float u, float v)
{
    const float f = 1.0f / tanf(0.5f * 1.0471976f), aspect = (float)W / H, zn = 0.1f, zf = 30.0f;
    return cv(f / aspect * e[0], f * e[1], (zf + zn) / (zn - zf) * e[2] + 2 * zf * zn / (zn - zf), -e[2], u, v);
}

typedef struct { gpu_cv v[3]; } ctri;
static ctri scene[64];
static int nscene;
static void add_quad(const float p[4][3], float us, float vs)
{
    gpu_cv a = project(p[0], 0, 0), b = project(p[1], us, 0), c = project(p[2], us, vs), d = project(p[3], 0, vs);
    scene[nscene].v[0] = a; scene[nscene].v[1] = b; scene[nscene].v[2] = c; nscene++;
    scene[nscene].v[0] = a; scene[nscene].v[1] = c; scene[nscene].v[2] = d; nscene++;
}
static void build_scene(float angle)
{
    static const int face[6][4] = { {0,1,2,3}, {5,4,7,6}, {4,0,3,7}, {1,5,6,2}, {3,2,6,7}, {4,5,1,0} };
    float cvx[8][3], ca = cosf(angle), sa = sinf(angle), cb = cosf(0.6f * angle), sb = sinf(0.6f * angle);
    int i, k;
    nscene = 0;
    for (i = 0; i < 8; i++) {
        float x = (i & 1) ^ ((i >> 1) & 1) ? 0.9f : -0.9f, y = (i & 2) ? 0.9f : -0.9f, z = (i & 4) ? -0.9f : 0.9f;
        float x1 = ca * x + sa * z, z1 = -sa * x + ca * z, y1 = cb * y - sb * z1, z2 = sb * y + cb * z1;
        cvx[i][0] = x1 + 0.2f; cvx[i][1] = y1 + 0.1f; cvx[i][2] = z2 - 4.0f;
    }
    for (k = 0; k < 6; k++) {
        float q[4][3];
        for (i = 0; i < 4; i++) memcpy(q[i], cvx[face[k][i]], sizeof q[i]);
        add_quad(q, 64, 64);
    }
    {   /* floor from behind the camera (z = +2) to far away (z = -20): crosses the near plane */
        float fl[4][3] = { { -6, -1.4f, 2 }, { 6, -1.4f, 2 }, { 6, -1.4f, -20 }, { -6, -1.4f, -20 } };
        add_quad(fl, 64 * 6, 64 * 11);
    }
}

/* ---- float reference renderer (from the float clipped polygon; same pipeline: z test <, nearest texel) ---- */
static uint16_t tex_at(float u, float v)
{
    int tu = (int)floorf(u) & 63, tv = (int)floorf(v) & 63;
    return tex[tv * 64 + tu];
}
static void ref_render(const gpu_view *vp)
{
    static float zbuf[W * H];
    int t, i, k, px, py;
    for (i = 0; i < W * H; i++) { fb_ref[i] = 0x0010; zbuf[i] = 2.0f; ref_id[i] = -1; }
    for (t = 0; t < nscene; t++) {
        gpu_cv p[10];
        float sx[10], sy[10], zz[10], iw[10];
        int n = gpu_clip(vp, scene[t].v, p);
        for (i = 0; i < n; i++) {
            iw[i] = 1.0f / p[i].w; sx[i] = (p[i].x * iw[i] * 0.5f + 0.5f) * W; sy[i] = (0.5f - p[i].y * iw[i] * 0.5f) * H;
            zz[i] = p[i].z * iw[i] * 0.5f + 0.5f;
        }
        for (k = 1; k + 1 < n; k++) {
            int a = 0, b = k, c = k + 1;
            double A = (double)(sx[b] - sx[a]) * (sy[c] - sy[a]) - (double)(sx[c] - sx[a]) * (sy[b] - sy[a]);
            if (fabs(A) < 1e-9) continue;
            for (py = 0; py < H; py++) for (px = 0; px < W; px++) {
                double x = px + 0.5, y = py + 0.5;
                double l1 = ((x - sx[a]) * (sy[c] - sy[a]) - (sx[c] - sx[a]) * (y - sy[a])) / A;
                double l2 = ((sx[b] - sx[a]) * (y - sy[a]) - (x - sx[a]) * (sy[b] - sy[a])) / A;
                double l0 = 1 - l1 - l2, z, Q, u, v;
                if (l0 < 0 || l1 < 0 || l2 < 0) continue;
                z = l0 * zz[a] + l1 * zz[b] + l2 * zz[c];
                if (z >= zbuf[py * W + px]) continue;
                Q = l0 * iw[a] + l1 * iw[b] + l2 * iw[c];
                u = (l0 * iw[a] * p[a].u + l1 * iw[b] * p[b].u + l2 * iw[c] * p[c].u) / Q;
                v = (l0 * iw[a] * p[a].v + l1 * iw[b] * p[b].v + l2 * iw[c] * p[c].v) / Q;
                zbuf[py * W + px] = (float)z;
                fb_ref[py * W + px] = tex_at((float)u, (float)v);
                ref_id[py * W + px] = t * 16 + k; ref_u[py * W + px] = (float)u; ref_v[py * W + px] = (float)v;
            }
        }
    }
}

/* ---- driver -> model, tiles stitched into a framebuffer ---- */
static long long last_samples, last_texels;
static long render_gpu(const gpu_view *vp, uint16_t *fb, int all_tris, long *words)
{
    static gpu_stri st[16 * GPU_CLIP_MAX];
    gpu_state states[1];
    gpu_buf b = { 0, 0, 0 };
    const uint16_t *out;
    long n, o, tiles = 0;
    int t, ns = 0, i;
    memset(states, 0, sizeof states);
    states[0].reg[GPU_R_TEX_BASE] = 0x4000; states[0].reg[GPU_R_TEX_CFG] = 6 | 6 << 4;
    states[0].reg[GPU_R_MODE] = GPU_M_ZTEST | GPU_M_ZWRITE;
    for (t = 0; t < nscene; t++) ns += gpu_setup_tri(vp, scene[t].v, 0, 0, st + ns);
    gpu_emit_upload(&b, 0x4000, tex, 64 * 64);
    gpu_emit_frame(&b, vp, st, ns, states, 0x0010, 0xFFFF, all_tris);
    gpu_ref_init();
    n = gpu_ref_exec(b.w, b.n, &out);
    for (o = 0; o + (long)GPU_TILE_WORDS <= n; o += GPU_TILE_WORDS, tiles++) {
        int tx = out[o + 1], ty = out[o + 2];
        for (i = 0; i < 1024; i++) if (ty + i / 32 < H) fb[(ty + i / 32) * W + tx + i % 32] = out[o + 3 + i];   /* 240 = 7.5 tiles */
    }
    last_samples = gpu_ref_samples(); last_texels = gpu_ref_texels();
    *words = b.n;
    free(b.w);
    return tiles;
}

int main(void)
{
    gpu_view vp;
    gpu_cv out[10];
    int i, n, x, y;
    gpu_view_default(&vp, W, H);
    for (y = 0; y < 64; y++) for (x = 0; x < 64; x++)
        tex[y * 64 + x] = (uint16_t)((((x >> 3) ^ (y >> 3)) & 1) ? (x / 2) << 11 | (y) << 5 | 31 : (31 - x / 2) << 11 | (63 - y) << 5);

    /* D01 inside: unchanged */
    { gpu_cv t[3] = { cv(0, 0, 0, 2, 0, 0), cv(1, 0, 0, 2, 1, 0), cv(0, 1, 0, 2, 0, 1) };
      n = gpu_clip(&vp, t, out); CHECK(n == 3 && out[1].x == 1 && out[2].v == 1); }
    /* D02 behind the camera */
    { gpu_cv t[3] = { cv(0, 0, 0, -1, 0, 0), cv(1, 0, 0, -2, 0, 0), cv(0, 1, 0, -0.5f, 0, 0) };
      CHECK(gpu_clip(&vp, t, out) == 0); }
    /* D03 near-plane crossing: one vertex behind -> quad, all w >= near */
    { gpu_cv t[3] = { cv(0, 0, 0, -1, 0, 0), cv(1, 0, 0.5f, 3, 10, 0), cv(0, 1, 0.5f, 3, 0, 10) };
      int ok = 1; n = gpu_clip(&vp, t, out);
      for (i = 0; i < n; i++) ok &= out[i].w >= vp.near_w - 1e-5f;
      CHECK(n == 4 && ok); }
    /* D04 guard band: a huge triangle stays inside the 12.4 range */
    { gpu_cv t[3] = { cv(-500, -500, 0, 1, 0, 0), cv(500, -500, 0, 1, 0, 0), cv(0, 500, 0, 1, 0, 0) };
      gpu_stri s[GPU_CLIP_MAX]; int nt = gpu_setup_tri(&vp, t, 0, 0, s), ok = nt > 0, k;
      for (i = 0; i < nt; i++) for (k = 0; k < 3; k++)
          ok &= s[i].v[k].x > -(int)(vp.guard_px + 2) * 16 && s[i].v[k].x < (W + (int)vp.guard_px + 2) * 16 &&
                s[i].v[k].y > -(int)(vp.guard_px + 2) * 16 && s[i].v[k].y < (H + (int)vp.guard_px + 2) * 16;
      CHECK(ok); }
    printf("TEST gpu_clip done fails=%d\n", g_fail);

    /* D05/D06/D07 scene, several angles */
    for (int f = 0; f < 4; f++) {
        long words, words_all, tiles;
        int mism = 0, interior = 0, covered = 0;
        build_scene(0.35f + 0.8f * f);
        tiles = render_gpu(&vp, fb_gpu, 0, &words);
        {
            long long s0 = last_samples, t0 = last_texels;
            render_gpu(&vp, fb_all, 1, &words_all);
            CHECK(memcmp(fb_gpu, fb_all, sizeof fb_gpu) == 0);           /* D06 binning loses nothing */
            last_samples = s0; last_texels = t0;
        }
        ref_render(&vp);
        for (y = 0; y < H; y++) for (x = 0; x < W; x++) {
            int p = y * W + x, edge = 0;
            if (ref_id[p] >= 0) covered++;
            if (fb_gpu[p] == fb_ref[p]) continue;
            mism++;
            for (int dy = -1; dy <= 1; dy++) for (int dx = -1; dx <= 1; dx++) {
                int xx = x + dx, yy = y + dy;
                if (xx < 0 || yy < 0 || xx >= W || yy >= H || ref_id[yy * W + xx] != ref_id[p]) edge = 1;
            }
            if (!edge && ref_id[p] >= 0) {
                /* error budget in texels: vertex snap to 1/16 px (<= 1/32 px x local texel density), u/v rounding to
                 * 1/16 texel (1/32), perspective truncation (1/16) -> exclusion zone around texel boundaries */
                float du = fabsf(ref_u[p + 1] - ref_u[p - 1]) * 0.5f + fabsf(ref_u[p + W] - ref_u[p - W]) * 0.5f;
                float dv = fabsf(ref_v[p + 1] - ref_v[p - 1]) * 0.5f + fabsf(ref_v[p + W] - ref_v[p - W]) * 0.5f;
                float tu = 1.0f / 32 + 1.0f / 16 + du / 32, tv = 1.0f / 32 + 1.0f / 16 + dv / 32;
                float fu = ref_u[p] - floorf(ref_u[p]), fv = ref_v[p] - floorf(ref_v[p]);
                if (fu > tu && fu < 1 - tu && fv > tv && fv < 1 - tv) {
                    interior++;
                    if (getenv("GPU_DIAG") && interior <= 6) printf("DIAG px %d,%d scene tri %d: gpu %04x ref %04x ref uv %.3f %.3f\n",
                        x, y, ref_id[p] / 16, fb_gpu[p], fb_ref[p], ref_u[p], ref_v[p]);
                }
            }
        }
        printf("INFO frame %d: %d scene tris, %ld tiles, %ld job words (%.1f KB), %lld samples, %lld texel fetches; "
               "pixels differing from the float reference %d of %d covered (%.2f %%), interior %d\n",
               f, nscene, tiles, words, words * 2 / 1024.0, last_samples, last_texels, mism, covered,
               100.0 * mism / (covered ? covered : 1), interior);
        CHECK(tiles == (W / 32) * ((H + 31) / 32));
        CHECK(covered > W * H / 3);
        CHECK(interior == 0);
        CHECK(mism * 100 < covered * 5);
    }

    /* D08: transport-sized tile requests render identically to the compact legacy stream. */
    {
        gpu_stri st[16 * GPU_CLIP_MAX];
        gpu_state states[1];
        gpu_job_span jobs[80];
        gpu_buf compact = { 0, 0, 0 }, packetized = { 0, 0, 0 };
        const uint16_t *out_a, *out_b;
        long na, nb, max_words = 0;
        int ns = 0, nj, j;
        memset(states, 0, sizeof states);
        states[0].reg[GPU_R_TEX_BASE] = 0x4000; states[0].reg[GPU_R_TEX_CFG] = 6 | 6 << 4;
        states[0].reg[GPU_R_MODE] = GPU_M_ZTEST | GPU_M_ZWRITE;
        build_scene(1.1f);
        for (i = 0; i < nscene; i++) ns += gpu_setup_tri(&vp, scene[i].v, 0, 0, st + ns);
        gpu_emit_upload(&compact, 0x4000, tex, 64 * 64);
        gpu_emit_frame(&compact, &vp, st, ns, states, 0x0010, 0xFFFF, 0);
        gpu_emit_upload(&packetized, 0x4000, tex, 64 * 64);
        nj = gpu_emit_frame_jobs(&packetized, &vp, st, ns, states, 0x0010, 0xFFFF, 0,
                                 jobs, 80, 4096);
        CHECK(nj == 80);
        for (j = 0; j < nj; j++) {
            CHECK(packetized.w[jobs[j].first_word] == GPU_TILE_BEGIN);
            CHECK(packetized.w[jobs[j].first_word + jobs[j].word_count - 1] == GPU_TILE_END);
            CHECK(jobs[j].word_count <= 4096);
            if (jobs[j].word_count > max_words) max_words = jobs[j].word_count;
        }
        gpu_ref_init(); na = gpu_ref_exec(compact.w, compact.n, &out_a);
        {
            uint16_t *copy = malloc((size_t)na * sizeof *copy);
            CHECK(copy != 0);
            if (copy) memcpy(copy, out_a, (size_t)na * sizeof *copy);
            gpu_ref_init(); nb = gpu_ref_exec(packetized.w, packetized.n, &out_b);
            CHECK(na == nb && copy && memcmp(copy, out_b, (size_t)na * sizeof *copy) == 0);
            free(copy);
        }
        printf("INFO packet plan: %d independent tile jobs, max %ld words (%.1f KB), %.1f %% replay-state overhead\n",
               nj, max_words, max_words * 2 / 1024.0,
               100.0 * (packetized.n - compact.n) / (compact.n ? compact.n : 1));
        CHECK(gpu_emit_frame_jobs(&packetized, &vp, st, ns, states, 0, 0xFFFF, 0,
                                  jobs, 79, 4096) == GPU_JOBS_NO_SPACE);
        CHECK(gpu_emit_frame_jobs(&packetized, &vp, st, ns, states, 0, 0xFFFF, 0,
                                  jobs, 80, 8) == GPU_JOBS_TOO_LARGE);
        free(compact.w); free(packetized.w);
    }
    printf("TEST gpu_scene done fails=%d\n", g_fail);
    printf("%d checks, %d failed\n", g_checks, g_fail);
    printf(g_fail ? "GPU_DRIVER_TEST_FAIL\n" : "GPU_DRIVER_TEST_PASS\n");
    return g_fail != 0;
}
