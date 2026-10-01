// STRUTHIO HANDHELD · Waveshare ESP32-S3-Touch-LCD-3.5B adapter.
//
// STATUS: panel/power/audio init are deliberately not written from memory.
// Copy them from Waveshare's ESP-IDF example for the board revision in hand
// (docs/A0_BRINGUP_CHECKLIST.md, step 1): the example creates the AXS15231B
// esp_lcd panel over QSPI and powers the AXP2101 rails and backlight. Assign
// its panel handle to g_panel below and board_display_lines() works as is.
// Until then the firmware still boots, runs the game headless at 60 Hz and
// logs over USB, and service mode still runs the on-device golden replay.
#include "board.h"
#include "esp_lcd_panel_ops.h"
#include "esp_log.h"

static const char *TAG = "board";
static esp_lcd_panel_handle_t g_panel;         // set by the vendor init code

bool board_power_init(void) {
    // TODO(A0 bring-up): AXP2101 rails + backlight from the Waveshare example.
    ESP_LOGW(TAG, "power init: vendor code not wired yet");
    return true;
}
bool board_display_init(void) {
    // TODO(A0 bring-up): AXS15231B QSPI panel from the Waveshare example; set g_panel.
    ESP_LOGW(TAG, "display init: vendor code not wired yet (running headless)");
    return g_panel != NULL;
}
void board_display_lines(int y0, int n, const uint16_t *buf) {
    if (!g_panel) return;
    // esp_lcd_panel_draw_bitmap queues the transfer; the vendor example's
    // color-trans-done callback must be hooked to make this blocking (or the
    // renderer must ping-pong two band buffers). Measure both at bring-up.
    esp_lcd_panel_draw_bitmap(g_panel, 0, y0, BOARD_LCD_W, y0 + n, buf);
}
void board_backlight(uint8_t percent) { (void)percent; }
bool board_audio_init(void) {
    // TODO(A0 audio phase): ES8311 over I2C + I2S, NS4150B enable; low gain first.
    return false;
}
void board_audio_cue(st_event_type_t event) { (void)event; }
