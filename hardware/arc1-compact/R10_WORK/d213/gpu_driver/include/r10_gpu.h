/* ARC-1 R10 -- D213-side GPU driver core (the host duties of fpga45/abi/R10_GPU_ABI.md): clip-space clipping
 * (near plane, far plane, guard band), viewport mapping, per-triangle q = 65535 * w_min / w, fan triangulation,
 * 32x32 tile binning and job-word emission. Pure C (float), no OS. HOST_TESTED against the bit-exact GPU model
 * (fpga45/tools/gpu_ref.c) and a float reference renderer (tests/test_gpu_driver.c). */
#ifndef R10_GPU_H
#define R10_GPU_H
#include <stdint.h>
#include "r10_gpu_abi.h"

typedef struct { float x, y, z, w, u, v; } gpu_cv;             /* clip-space vertex; u, v in texels */
typedef struct { int16_t x, y; uint16_t z, q; int16_t u, v; } gpu_sv;   /* TRI_TEX vertex words */
typedef struct { gpu_sv v[3]; uint16_t rgb; uint8_t state; } gpu_stri;
typedef struct { uint32_t reg[GPU_R_COUNT]; } gpu_state;
typedef struct {
    int width, height;          /* frame in pixels; the last tile row/column may extend past the frame (240 = 7.5 tiles) */
    float near_w;               /* near plane: w >= near_w */
    float guard_px;             /* screen coordinates are kept inside [-guard_px, width/height + guard_px] */
} gpu_view;
typedef struct { uint16_t *w; long n, cap; } gpu_buf;

#define GPU_CLIP_MAX 64         /* clipped fan (<= 8 triangles) after w-ratio splitting (q precision, r10_gpu.c) */

void gpu_view_default(gpu_view *vp, int width, int height);
/* clip a triangle; returns the polygon vertex count (0 = invisible, else 3..10) */
int  gpu_clip(const gpu_view *vp, const gpu_cv in[3], gpu_cv out[10]);
/* clip + project + fan: returns the number of screen triangles written to out (<= GPU_CLIP_MAX) */
int  gpu_setup_tri(const gpu_view *vp, const gpu_cv in[3], uint16_t rgb, uint8_t state, gpu_stri out[GPU_CLIP_MAX]);

void gpu_buf_reset(gpu_buf *b);
void gpu_emit(gpu_buf *b, uint16_t w);
void gpu_emit_upload(gpu_buf *b, uint32_t addr, const uint16_t *data, long n);
void gpu_emit_palette(gpu_buf *b, const uint16_t pal[256]);
/* one frame: for every 32x32 tile (row-major), TILE_BEGIN, the triangles whose bounding box meets the tile (in
 * submission order, SET_REG only where the state differs from what the GPU already holds), TILE_END.
 * all_tris = 1 disables binning (every triangle in every tile: the reference for the binning test). */
long gpu_emit_frame(gpu_buf *b, const gpu_view *vp, const gpu_stri *t, int n, const gpu_state *states,
                    uint16_t clear_rgb, uint16_t clear_z, int all_tris);
#endif
