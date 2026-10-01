// STRUTHIO HANDHELD · board adapter. Everything specific to the Waveshare
// ESP32-S3-Touch-LCD-3.5B lives behind these calls, in board_waveshare_35b.c.
// Bring-up rule (A0 checklist): get Waveshare's own ESP-IDF example running on
// the exact board revision first, then move its panel / power / audio init
// into that file. The game, renderer and buttons never touch the hardware.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "struthio_core.h"

#ifdef __cplusplus
extern "C" {
#endif

enum { BOARD_LCD_W = 320, BOARD_LCD_H = 480, BOARD_BAND_LINES = 40 };

// Power (AXP2101) and backlight. Returns false if the board is not ready.
bool board_power_init(void);
// AXS15231B QSPI panel, portrait 320 x 480. Returns false until wired.
bool board_display_init(void);
// Sends lines [y0, y0 + n) of RGB565 (high byte first). Blocks until the
// buffer may be reused. buf must be DMA-capable internal RAM.
void board_display_lines(int y0, int n, const uint16_t *buf);
void board_backlight(uint8_t percent);
// ES8311 codec + NS4150B amplifier, mono speaker. Cues are fire-and-forget.
bool board_audio_init(void);
void board_audio_cue(st_event_type_t event);

#ifdef __cplusplus
}
#endif
