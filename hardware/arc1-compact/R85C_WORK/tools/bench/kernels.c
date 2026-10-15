/* ARC-1 Compact R8.5 -- CPU-side benchmark kernels (F133 C906 instruction counts via rv64im_iss.py).
 * Representative ARC-1 60 Hz work (change order 5.3): 2D transform (the R05 contract, real code), AABB collision
 * batch (brute force pairs), particle update (Q16.16 Euler + bounds), DSP stress (32-tap int16 FIR).
 * The same file compiles natively; both builds must print/store identical checksums (ISS self-check). */
#include <stdint.h>
#include "arc1_transform.h"

#define NJ 170
#define NB 128
#define NP 512
#define NS 256
#define NT 32

volatile uint32_t result_sum[8];
static arc1_transform_job jobs[NJ];
static arc1_transform_result res[NJ];
static int32_t bx0[NB], by0[NB], bx1[NB], by1[NB];
static int32_t px[NP], py[NP], vx[NP], vy[NP];
static int16_t smp[NS + NT], coef[NT], out16[NS];
static uint32_t seed = 1;

__attribute__((noinline)) void bench_mark(uint32_t id) { __asm__ volatile("" ::"r"(id) : "memory"); }
static uint32_t rnd(void) { seed = seed * 1103515245u + 12345u; return seed >> 8; }

static void setup(void)
{
    int i;
    for (i = 0; i < NJ; i++) {
        arc1_transform_job j = { (int32_t)(rnd() % 400) * 65536, (int32_t)(rnd() % 300) * 65536, 0, 0,
                                 46341, -46341, (int32_t)(rnd() % 64) * 65536, 46341, 46341, 0, 320, 240, (uint32_t)i };
        j.xmax = j.xmin + 16 * 65536; j.ymax = j.ymin + 16 * 65536;
        jobs[i] = j;
    }
    for (i = 0; i < NB; i++) { bx0[i] = (int32_t)(rnd() % 320) << 16; by0[i] = (int32_t)(rnd() % 240) << 16;
                               bx1[i] = bx0[i] + (16 << 16); by1[i] = by0[i] + (16 << 16); }
    for (i = 0; i < NP; i++) { px[i] = (int32_t)(rnd() % 320) << 16; py[i] = (int32_t)(rnd() % 240) << 16;
                               vx[i] = (int32_t)(rnd() % 131072) - 65536; vy[i] = (int32_t)(rnd() % 131072) - 65536; }
    for (i = 0; i < NS + NT; i++) smp[i] = (int16_t)(rnd() & 0xFFFF);
    for (i = 0; i < NT; i++) coef[i] = (int16_t)((rnd() & 0x3FF) - 512);
}

static uint32_t k_transform(int n)
{
    uint32_t s = 0;
    int i;
    for (i = 0; i < n; i++) { arc1_transform_rectangle(&jobs[i], &res[i]); s += (uint32_t)res[i].minx ^ res[i].flags; }
    return s;
}

static uint32_t k_collide(int n)               /* all pairs among n boxes; returns overlap count */
{
    uint32_t c = 0;
    int i, k;
    for (i = 0; i < n; i++)
        for (k = i + 1; k < n; k++)
            c += (bx0[i] < bx1[k]) & (bx0[k] < bx1[i]) & (by0[i] < by1[k]) & (by0[k] < by1[i]);
    return c;
}

static uint32_t k_particles(int n)             /* one 60 Hz step: v += g, p += v, bounce at the screen edges */
{
    uint32_t s = 0;
    int i;
    for (i = 0; i < n; i++) {
        vy[i] += 1092;                          /* g/60 in Q16.16 */
        px[i] += vx[i]; py[i] += vy[i];
        if (px[i] < 0 || px[i] > (320 << 16)) { vx[i] = -vx[i]; px[i] += 2 * vx[i]; }
        if (py[i] > (240 << 16)) { vy[i] = -(vy[i] - (vy[i] >> 3)); py[i] = 240 << 16; }
        s += (uint32_t)(px[i] ^ py[i]);
    }
    return s;
}

static uint32_t k_fir(int n)                   /* 32-tap FIR, Q15, saturating */
{
    uint32_t s = 0;
    int i, t;
    for (i = 0; i < n; i++) {
        int32_t acc = 0;
        for (t = 0; t < NT; t++) acc += (int32_t)smp[i + t] * coef[t];
        acc >>= 15;
        if (acc > 32767) acc = 32767;
        if (acc < -32768) acc = -32768;
        out16[i] = (int16_t)acc;
        s += (uint32_t)(uint16_t)out16[i];
    }
    return s;
}

int bench_main(void)
{
    setup();
    bench_mark(10); result_sum[0] = k_transform(NJ);   bench_mark(11);
    bench_mark(20); result_sum[1] = k_collide(NB);     bench_mark(21);
    bench_mark(30); result_sum[2] = k_particles(NP);   bench_mark(31);
    bench_mark(40); result_sum[3] = k_fir(NS);         bench_mark(41);
    return 0;
}

#ifdef NATIVE
#include <stdio.h>
int main(void)
{
    bench_main();
    printf("%u %u %u %u\n", result_sum[0], result_sum[1], result_sum[2], result_sum[3]);
    return 0;
}
#endif
