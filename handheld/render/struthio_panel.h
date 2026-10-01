// STRUTHIO HANDHELD · the panel renderer: the whole 320x480 screen as the
// browser shows the game in a 320x480 window (arcade page layout, touch deck
// replaced by the physical wings): the frame, the live HUD bar and its
// toasts (captured from Chromium), and the game picture (286x429 at 17,51)
// drawn from the scene builder's quads.
//
// The game picture targets the browser's full 768x1152 canvas filtered down
// to 286x429: textures are area-filtered to panel density offline (bake
// step), sampled nearest, shaded with the same material code as the reference
// rasterizer, then tone + Arcade grade (quality 0) through lookup tables.
// Rendering is band by band straight into the panel's RGB565 line buffer: no
// framebuffer.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "struthio_raster.h"
#include "struthio_scene.h"

#ifdef __cplusplus
extern "C" {
#endif

enum { ST_PANEL_W = 320, ST_PANEL_H = 480, ST_GAME_X = 17, ST_GAME_Y = 51, ST_GAME_W = 286, ST_GAME_H = 429 };

typedef struct { int w, h; const uint8_t *p; } st_tex_t;        // RGBA8, straight alpha

typedef struct {
    st_tex_t world_rear, world_near;     // panel density
    st_tex_t bird[4];                    // inks 6 (player), 1, 2, 3 (rivals), panel density
    st_tex_t atlas;                      // panel density (island palette baked in)
    st_tex_t atlas_hi;                   // full resolution, atlas x 1536.., y 0..568 (glyphs, swatches)
    st_textures_t globe;                 // only .globe and .globe_params are used
    bool bilinear;                       // sample the panel-density textures bilinearly (4 reads, ~+2.5 dB, softer)
} st_panel_textures_t;

// ---- HUD ------------------------------------------------------------------------------
typedef struct { int16_t x, y, w, h; const uint8_t *p; } st_hud_layer_t;   // premultiplied RGBA8
enum { ST_HUD_ROUNDS = 100 };
typedef struct {
    const uint8_t *chrome;                // 320 x 480 RGBA8 (opaque)
    st_hud_layer_t statics[2];            // [variant] dividers, R, J label (a: lives 11, b: other)
    st_hud_layer_t score[6][10], round[2][10];
    st_hud_layer_t kills2[2][2][10], kills3[2][3][10], swords[2][2];   // [variant][...]
    st_hud_layer_t ring[2][8];            // [variant][0..6, 7 = gold due]
    st_hud_layer_t joust_b[12], joust_i[12];
    st_hud_layer_t toast_extra, toast_gold, toast_paused, toast_clear[ST_HUD_ROUNDS], toast_clean[ST_HUD_ROUNDS];
} st_hud_assets_t;

// hud.mjs hudModel plus the CSS behaviour: toast fade (160 ms), the gold-ring
// pulse (1.2 s ease-in-out to brightness 1.35), the bar's fade-in (140 ms).
typedef struct {
    int32_t score, round, rings, kills, lives;
    bool due, paused;
    const st_hud_layer_t *toast;          // the toast shown or fading out
    float toast_opacity, due_brightness, opacity;
    // animation memory
    int32_t due_since, live_since;
    const st_hud_layer_t *last_toast;
} st_hud_t;
void st_hud_reset(st_hud_t *h, int32_t render_tick);
void st_hud_update(st_hud_t *h, const st_hud_assets_t *a, const st_state_t *s, const st_scene_t *sc);

// ---- the frame ------------------------------------------------------------------------
typedef struct {
    uint16_t tone[3][256];                // per channel, 8-bit scene -> 0..65535 toned
    uint16_t grade[65536];                // toned RGB565 -> graded RGB565
    bool ready;
    bool skip_post;                       // diagnostics: leave the scene un-toned
} st_panel_luts_t;
void st_panel_luts_init(st_panel_luts_t *l);

typedef void (*st_band_fn)(void *ctx, int y0, int rows, const uint16_t *rgb565);   // 320 x rows, native byte order
enum { ST_BAND_ROWS = 16 };

void st_panel_render(const st_panel_textures_t *tx, const st_hud_assets_t *hud_a, const st_hud_t *hud, const st_panel_luts_t *luts,
                     const st_quads_t *q, const st_frame_params_t *fp, st_band_fn out, void *ctx);

#ifdef __cplusplus
}
#endif
