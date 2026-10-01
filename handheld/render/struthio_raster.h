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

// The browser's canvas is 768x1152 (3x). Shown smaller with image-rendering:
// pixelated, each screen pixel is the nearest canvas pixel. A grid maps every
// output pixel to the canvas pixel it shows, so the C renderer evaluates
// exactly those pixels: at w x h = 768 x 1152 it is the canvas itself; at the
// handheld's 286 x 429 it is what the browser shows in a 320 x 480 window.
typedef struct {
    int w, h;            // output pixels
    int vw, vh;          // canvas pixels (768 x 1152)
    int16_t *vx, *vy;    // output column / row -> canvas column / row
    int16_t *ox, *oy;    // canvas column / row -> nearest output column / row (post halo taps)
} st_grid_t;
// Builds a grid for w x h (vx, vy: w and h entries; ox, oy: vw and vh entries).
void st_grid_init(st_grid_t *g, int w, int h, int vw, int vh, int16_t *vx, int16_t *vy, int16_t *ox, int16_t *oy);

// Draws quads into scene (RGBA8, g->w x g->h), clearing it first. depth: w*h floats.
void st_raster_scene(uint8_t *scene, float *depth, const st_grid_t *g, const st_quads_t *q, const st_textures_t *tex,
                     const st_frame_params_t *fp);
// The post pass in canvas coordinates: scene -> out (both RGBA8, g->w x g->h).
// scratch: 2 * ceil(vw/4) * ceil(vh/4) * 3 floats for quality 2.
void st_raster_post(const uint8_t *scene, uint8_t *out, const st_grid_t *g, const st_frame_params_t *fp, float *scratch);

// Per-texel colour functions of the sprite pass (exposed for asset baking).
void st_bird_ink(const float in[3], int ink, float phase, float jouster, float out[3]);
void st_island_palette(const float in[3], float out[3]);
void st_grade_arcade(const float in[3], float out[3]);
void st_tone(const float in[3], float out[3]);     // exposure 1.8, white 1.6

#ifdef __cplusplus
}
#endif
