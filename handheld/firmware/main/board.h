// STRUTHIO HANDHELD · board adapter. Everything specific to the Waveshare
// ESP32-S3-Touch-LCD-3.5B lives behind these calls, in board_waveshare_35b.c.
// Power and display follow Waveshare's own ESP-IDF example (pins, init order,
// panel init commands); see board_waveshare_35b.c. The game, renderer and
// buttons never touch the hardware.
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
// ORDER CONTRACT: on the AXS15231B over QSPI there is no row address. A band
// at y0 == 0 starts a frame (RAMWR); every other band continues where the last
// one stopped (RAMWRC). So each frame must be sent top to bottom, full width,
// with no gaps. Calls that break the order are counted, not drawn
// (board_display_order_errors).
void board_display_lines(int y0, int n, const uint16_t *buf);
uint32_t board_display_order_errors(void);
void board_backlight(uint8_t percent);
// The same, as a smooth fade over ms (the LEDC hardware fades it; returns at once).
void board_backlight_fade(uint8_t percent, int ms);
// Turn the picture 180 degrees (the case may hold the board either way up).
void board_display_flip(bool flip);
// Battery and charger state from the AXP2101.
typedef struct { bool battery_present, charging, vbus_present; uint16_t battery_mv; int battery_percent; } board_power_t;
bool board_power_read(board_power_t *out);
void board_power_off(void);
// Which handheld this board sits in, set once at boot:
//   ONE (23 mm): slide switch + power-on pulse on PWR (header pin 24) -> a long press must never mean "off";
//                1000 mAh cell -> 200 mA charge.
//   ONE SLIM (22.2 mm): no switch; the Waveshare's own PWR key is the power button -> press 0.5 s: on,
//                hold 4 s: off; the same 1000 mAh cell -> 200 mA charge (rev S4; S2/S3 had 250 mAh).
void board_power_model(bool slide_switch);
// ONE SLIM: true once after each short press of the power button (the AXP2101's PKEY short-press flag).
bool board_power_key_pressed(void);
// ES8311 codec + NS4150B amplifier, mono speaker: 48 kHz, 16-bit, one channel.
bool board_audio_init(void);
// Queues n samples for the I2S DMA; blocks while the DMA buffers are full
// (that wait paces the audio task). An underrun plays silence.
void board_audio_write(const int16_t *pcm, int n);
// Codec output volume, 0 (muted) to 100.
void board_audio_volume(int percent);

#ifdef __cplusplus
}
#endif
