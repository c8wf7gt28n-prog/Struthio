// STRUTHIO HANDHELD · greybox renderer.
//
// Draws the simulation into one 256 x 384 8-bit indexed framebuffer (98,304
// bytes) using the rulebook palette, then presents it to the 320 x 480 panel
// as RGB565 one line at a time (exact 5:4 = 1.25x in both axes), so the board
// needs only a 640-byte line buffer per DMA band. Shapes only: islands,
// rings, birds, eggs, riders and the HUD read clearly; converted art comes
// later (asset compiler, phase 5).
//
// Presentation follows the browser tower camera (arcade/src/render/camera.mjs):
// screen y = 2 x sim y - cameraTop; sprites are unscaled and anchored at the feet.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "struthio_core.h"
#include "struthio_scene.h"     // st_camera_t

#ifdef __cplusplus
extern "C" {
#endif

enum { ST_FB_W = 256, ST_FB_H = 384 };    // ST_PANEL_W, ST_PANEL_H: struthio_scene.h


typedef struct {
    int32_t camera_top;
    uint32_t frame;          // render counter (blinks, twinkles)
    int32_t high_score;      // shown on the GAME OVER card
    const char *banner;      // optional one-line banner (NULL for none)
} st_view_t;

void st_render(uint8_t *fb, const st_state_t *s, const st_view_t *v);

// One panel line (0..479) as RGB565. swap_bytes: true for panels that take
// the high byte first over SPI/QSPI (most do, the AXS15231B included).
void st_present_line(const uint8_t *fb, int panel_y, uint16_t out[ST_PANEL_W], bool swap_bytes);

// Text helpers in framebuffer pixels (5x7 rulebook font, 6 px advance).
void st_draw_text(uint8_t *fb, int x, int y, const char *text, uint8_t color, int scale);
int st_text_width(const char *text, int scale);

#ifdef __cplusplus
}
#endif
