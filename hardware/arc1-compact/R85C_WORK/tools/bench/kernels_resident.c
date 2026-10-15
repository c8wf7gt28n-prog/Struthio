/* ARC-1 Compact R8.5-C -- resident-state / high-intensity CPU kernels for the link study (ISS instruction counts).
 * Each models work whose large state could live in FPGA EBR/PSRAM, so only small inputs/results cross the link:
 *   reverb  : 1024-tap Q15 FIR (convolution reverb), 735 samples/frame (44.1 kHz / 60), mono
 *   coll512 : all-pairs AABB test of 512 objects (130 816 pairs) -- what a brute-force FPGA engine would do
 *   collgrid: the same 512 objects with a uniform-grid broad phase on the CPU (the fair CPU baseline)
 *   physics : 512 particles x 8 substeps per frame (gravity, drag, bounds)
 *   raycast : 64 rays x <= 256 DDA steps on a 64x64 tile map (line of sight / pseudo-3D column casting)
 * Native and ISS builds must agree on every checksum. */
#include <stdint.h>

#define NS 735
#define NT 1024
#define NO 512
#define NP 512
#define NSUB 8
#define NR 64
#define MAPN 64

volatile uint32_t result_sum[8];
static int16_t smp[NS + NT], ir[NT], outs[NS];
static int32_t x0[NO], y0[NO], x1[NO], y1[NO];
static int32_t px[NP], py[NP], vx[NP], vy[NP];
static uint8_t map[MAPN * MAPN];
static uint16_t cell_head[16 * 16], cell_next[NO];
static uint32_t seed = 7;

__attribute__((noinline)) void bench_mark(uint32_t id) { __asm__ volatile("" ::"r"(id) : "memory"); }
static uint32_t rnd(void) { seed = seed * 1103515245u + 12345u; return seed >> 8; }

static void setup(void)
{
    int i;
    for (i = 0; i < NS + NT; i++) smp[i] = (int16_t)(rnd() & 0xFFFF);
    for (i = 0; i < NT; i++) ir[i] = (int16_t)(((int32_t)(rnd() & 0x3FF) - 512) >> (i >> 8));
    for (i = 0; i < NO; i++) { x0[i] = (int32_t)(rnd() % 496); y0[i] = (int32_t)(rnd() % 496); x1[i] = x0[i] + 12; y1[i] = y0[i] + 12; }
    for (i = 0; i < NP; i++) { px[i] = (int32_t)(rnd() % 320) << 16; py[i] = (int32_t)(rnd() % 240) << 16;
                               vx[i] = (int32_t)(rnd() % 65536) - 32768; vy[i] = (int32_t)(rnd() % 65536) - 32768; }
    for (i = 0; i < MAPN * MAPN; i++) map[i] = (uint8_t)((rnd() & 15) == 0);
}

static uint32_t k_reverb(void)
{
    uint32_t s = 0;
    int i, t;
    for (i = 0; i < NS; i++) {
        int32_t acc = 0;
        for (t = 0; t < NT; t++) acc += (int32_t)smp[i + t] * ir[t];
        acc >>= 15;
        if (acc > 32767) acc = 32767;
        if (acc < -32768) acc = -32768;
        outs[i] = (int16_t)acc;
        s += (uint32_t)(uint16_t)outs[i];
    }
    return s;
}

static uint32_t k_coll512(void)
{
    uint32_t c = 0;
    int i, k;
    for (i = 0; i < NO; i++)
        for (k = i + 1; k < NO; k++)
            c += (x0[i] < x1[k]) & (x0[k] < x1[i]) & (y0[i] < y1[k]) & (y0[k] < y1[i]);
    return c;
}

static uint32_t k_collgrid(void)               /* 16x16 grid of 32-px cells over 512x512; objects are 12 px */
{
    uint32_t c = 0;
    int i, cx, cy, dx, dy;
    for (i = 0; i < 256; i++) cell_head[i] = 0xFFFF;
    for (i = 0; i < NO; i++) {
        int cell = (y0[i] >> 5) * 16 + (x0[i] >> 5);
        cell_next[i] = cell_head[cell];
        cell_head[cell] = (uint16_t)i;
    }
    for (i = 0; i < NO; i++) {
        cx = x0[i] >> 5; cy = y0[i] >> 5;
        for (dy = -1; dy <= 1; dy++)
            for (dx = -1; dx <= 1; dx++) {
                int nx = cx + dx, ny = cy + dy;
                uint16_t k;
                if (nx < 0 || ny < 0 || nx > 15 || ny > 15) continue;
                for (k = cell_head[ny * 16 + nx]; k != 0xFFFF; k = cell_next[k])
                    if (k > i) c += (x0[i] < x1[k]) & (x0[k] < x1[i]) & (y0[i] < y1[k]) & (y0[k] < y1[i]);
            }
    }
    return c;
}

static uint32_t k_physics(void)
{
    uint32_t s = 0;
    int i, n;
    for (n = 0; n < NSUB; n++)
        for (i = 0; i < NP; i++) {
            vy[i] += 136;                           /* g/(60*8) */
            vx[i] -= vx[i] >> 7; vy[i] -= vy[i] >> 7;
            px[i] += vx[i] >> 3; py[i] += vy[i] >> 3;
            if (px[i] < 0 || px[i] > (320 << 16)) { vx[i] = -vx[i]; px[i] += vx[i] >> 2; }
            if (py[i] > (240 << 16)) { vy[i] = -(vy[i] - (vy[i] >> 3)); py[i] = 240 << 16; }
        }
    for (i = 0; i < NP; i++) s += (uint32_t)(px[i] ^ py[i]);
    return s;
}

static uint32_t k_raycast(void)                 /* fixed-point DDA, 16.16, returns summed hit distances */
{
    uint32_t s = 0;
    int r;
    for (r = 0; r < NR; r++) {
        int32_t x = 32 << 16, y = 32 << 16;
        int32_t dx = (int32_t)((r * 2048) - 65536), dy = 40000 - (r * 600);
        int step;
        for (step = 0; step < 256; step++) {
            x += dx >> 2; y += dy >> 2;
            if (x < 0 || y < 0 || x >= (MAPN << 16) || y >= (MAPN << 16)) break;
            if (map[(y >> 16) * MAPN + (x >> 16)]) break;
        }
        s += (uint32_t)step;
    }
    return s;
}

int bench_main(void)
{
    setup();
    bench_mark(10); result_sum[0] = k_reverb();   bench_mark(11);
    bench_mark(20); result_sum[1] = k_coll512();  bench_mark(21);
    bench_mark(30); result_sum[2] = k_collgrid(); bench_mark(31);
    bench_mark(40); result_sum[3] = k_physics();  bench_mark(41);
    bench_mark(50); result_sum[4] = k_raycast();  bench_mark(51);
    return 0;
}

#ifdef NATIVE
#include <stdio.h>
int main(void)
{
    bench_main();
    printf("%u %u %u %u %u\n", result_sum[0], result_sum[1], result_sum[2], result_sum[3], result_sum[4]);
    return 0;
}
#endif
