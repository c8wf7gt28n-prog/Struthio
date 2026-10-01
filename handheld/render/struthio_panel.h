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

enum { ST_GAME_X = 17, ST_GAME_Y = 51, ST_GAME_W = 286, ST_GAME_H = 429 };

// Texture formats in the asset pack (little-endian RGB565).
enum {
    ST_TEX_565 = 1,      // 2 bytes: RGB565, opaque
    ST_TEX_565A8 = 2,    // 3 bytes: RGB565, alpha
    ST_TEX_REAR = 3,     // 4 bytes: RGB565, lit (0..255), moon disk << 7 | star coverage (0..127)
    ST_TEX_NEAR = 4,     // 4 bytes: RGB565, alpha, gold << 4 | cyan (glint weights, 0..15)
    ST_TEX_RGBA = 0,     // 4 bytes: RGBA8, straight alpha
    ST_HUD_RLE = 5,      // HUD layer, premultiplied RGBA8 runs (see struthio_pak.h)
    ST_RAW = 6,
};
typedef struct { int w, h; uint8_t format; const uint8_t *p; } st_tex_t;

typedef struct {
    st_tex_t world_rear, world_near;     // panel density, ambience attributes baked
    st_tex_t bird[4];                    // inks 6 (player), 1, 2, 3 (rivals), panel density
    st_tex_t atlas;                      // panel density (island palette baked in)
    st_tex_t atlas_hi;                   // full resolution, atlas x 1536.., y 0..568 (glyphs, swatches)
    st_tex_t globe_map;                  // the turning moon's longitude map, filtered (565)
    const uint16_t *globe_lut;           // per moon-disk rear texel: row in globe_map, longitude (0..65535)
    int globe_x0, globe_y0, globe_w, globe_h;   // the disk's bounding box in rear texels
    float globe_params[4];               // centre x, centre y (full-res plate), radius, radians per tick
    bool bilinear;                       // sample the panel-density textures bilinearly (4 reads, ~+2.5 dB, softer)
} st_panel_textures_t;

// ---- HUD ------------------------------------------------------------------------------
typedef struct st_hud_layer {
    int16_t x, y, w, h;
    const uint8_t *p;                    // premultiplied RGBA8, raw or run-length coded (struthio_pak.h)
    uint8_t rle;
    const struct st_hud_layer *base;     // run-coded against this layer (same size), or NULL
} st_hud_layer_t;
enum { ST_HUD_ROUNDS = 100 };
typedef struct {
    const uint8_t *chrome;                // 320 x 480 RGB565 (opaque)
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

// The whole panel, band by band, top to bottom (one core, static workspace).
void st_panel_render(const st_panel_textures_t *tx, const st_hud_assets_t *hud_a, const st_hud_t *hud, const st_panel_luts_t *luts,
                     const st_quads_t *q, const st_frame_params_t *fp, st_band_fn out, void *ctx);
// Workspace for one renderer: a band of colour and depth, its RGB565 lines.
// line is what out receives; on the device it must be DMA-capable memory.
typedef struct {
    uint8_t rgb[ST_BAND_ROWS][ST_PANEL_W][3];
    uint16_t depth[ST_BAND_ROWS][ST_GAME_W];
    uint8_t hud_row[ST_PANEL_W][4];
    uint16_t *line;                       // ST_BAND_ROWS * ST_PANEL_W
    uint16_t line_store[ST_BAND_ROWS * ST_PANEL_W];
} st_panel_work_t;
// Bands first, first + stride, ... (band k = rows 16k..16k+15): two cores render
// the even and the odd bands of one frame, each with its own workspace.
// w->line may point at w->line_store or at DMA memory the caller owns.
void st_panel_render_bands(const st_panel_textures_t *tx, const st_hud_assets_t *hud_a, const st_hud_t *hud, const st_panel_luts_t *luts,
                           const st_quads_t *q, const st_frame_params_t *fp, int first, int stride, st_panel_work_t *w,
                           st_band_fn out, void *ctx);
enum { ST_PANEL_BANDS = (ST_PANEL_H + ST_BAND_ROWS - 1) / ST_BAND_ROWS };

#ifdef __cplusplus
}
#endif
