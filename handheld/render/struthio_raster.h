// STRUTHIO HANDHELD · software rasterizer for the browser's quad lists: a port
// of arcade/src/render/renderer.mjs (the WGSL sprite pass and its materials,
// and the post pass: tone curve, Arcade grade, bloom, scanlines, vignette).
//
// This is the float reference implementation, run at any scale: at 3x
// (768x1152) it is compared with the WebGPU frames the browser renders; at
// 1.25x it draws the 320x480 panel picture. GPU behaviour reproduced: quads
// cover the pixels whose centres fall inside them, textures are sampled
// nearest at (src + uv * (size - 1) + 0.5), depth test less-equal with depth
// writes, fragments with alpha < 1/255 discarded, premultiplied
// one / one-minus-src-alpha blending into an 8-bit target after every quad.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "struthio_scene.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct { int w, h; const uint8_t *p; } st_rgba_t;      // straight-alpha RGBA8

typedef struct {
    st_rgba_t atlas;     // 2048 x 2048 (islands baked)
    st_rgba_t world;     // 1536 x 2304: rear plate | near plate (depth graded)
    st_rgba_t bird;      // 1536 x 1152 jouster sheet (dark outline dropped, rims marked)
    st_rgba_t globe;     // 1536 x 768 turning-moon longitude map
    float globe_params[4];   // centre x, centre y, radius (negative: colour mode), radians per tick
} st_textures_t;

typedef struct {
    float tick;          // render tick
    float ambient_tick;  // drives the world / island ambience (0 = reduced motion)
    float moon_phase;    // 0..1, the globe's turn
    float beat;          // music beat 0..1 (0 without music)
    float motion;        // 1, or 0 under reduced motion
    float cyan, lava, violet, impact, bloom_beat;   // post pulse inputs
    int quality;         // 0: tone + grade; 1: + halo + scanlines + vignette; 2: + quarter-res bloom
    float horizon;       // ARCADE_REAR_HORIZON (1682)
} st_frame_params_t;

void st_frame_params_default(st_frame_params_t *p, int32_t render_tick, double moon_phase, double impact);

// Draws quads into scene (RGBA8, w = 256*scale, h = 384*scale), clearing it
// first. depth must hold w*h floats.
void st_raster_scene(uint8_t *scene, float *depth, int w, int h, const st_quads_t *q, const st_textures_t *tex,
                     const st_frame_params_t *fp);
// The post pass: scene -> out (both RGBA8, same size). scratch: at least
// 2 * ceil(w/4) * ceil(h/4) * 3 floats for quality 2.
void st_raster_post(const uint8_t *scene, uint8_t *out, int w, int h, int logical_h, const st_frame_params_t *fp, float *scratch);

// Per-texel colour functions of the sprite pass (exposed for asset baking).
void st_bird_ink(const float in[3], int ink, float phase, float jouster, float out[3]);
void st_island_palette(const float in[3], float out[3]);
void st_grade_arcade(const float in[3], float out[3]);
void st_tone(const float in[3], float out[3]);     // exposure 1.8, white 1.6

#ifdef __cplusplus
}
#endif
