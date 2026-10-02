// STRUTHIO HANDHELD · the first power-on check.
//
// Runs at every power-on until it has passed once (NVS "tested"), before the game:
//   - press each of the four buttons once: each turns OK and clicks (the click proves the speaker)
//   - a button already held when the check starts and held for 2 s is reported STUCK (its cap rubs the switch)
//   - ONE SLIM: a short press of the power button turns OK (the power chip reports it)
//   - the battery: found / not found, its voltage, USB and charging
//   - the picture upside down: hold LEFT WING 2 s to turn it (saved)
//   - all four OK: press both wings to play (saved: the check never runs again; service mode's DART RIGHT tap
//     asks for it again)
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "board.h"
#include "board_pins.h"
#include "struthio_app.h"
#include "struthio_greybox.h"
#include "struthio_rules.h"

static const char *TAG = "SELFTEST";
enum { KEYS = 4, HOLD_MS = 2000 };
static const int PIN[KEYS] = {STRUTHIO_GPIO_LEFT_WING, STRUTHIO_GPIO_RIGHT_WING, STRUTHIO_GPIO_DART_LEFT, STRUTHIO_GPIO_DART_RIGHT};
static const char *NAME[KEYS] = {"LEFT WING     ", "RIGHT WING    ", "DART LEFT END ", "DART RIGHT END"};

void selftest_run(st_buttons_t *b, st_norm_t *norm) {
    (void)b; (void)norm;
    ESP_LOGW(TAG, "first power-on check: press each button once, then both wings");
    app_audio_start();
    uint8_t *fb = app_framebuffer();
    bool seen[KEYS] = {0}, was[KEYS], stuck[KEYS] = {0}, from_start[KEYS], used[KEYS] = {0};
    uint32_t down_at[KEYS], now = app_now_ms();
    for (int i = 0; i < KEYS; i++) { was[i] = from_start[i] = app_pin_pressed(PIN[i]); down_at[i] = now; }
    board_power_t pw0;
    bool lit = false, pwr_ok = app_is_one() || !board_power_read(&pw0);   // ONE: the slide switch is the power; no power
                                                                          // chip answering: nothing to test (the screen says)
    for (uint32_t frame = 0;; frame++) {
        now = app_now_ms();
        for (int i = 0; i < KEYS; i++) {
            bool p = app_pin_pressed(PIN[i]);
            if (p && !was[i]) { down_at[i] = now; used[i] = false; from_start[i] = false; }
            if (p && from_start[i] && now - down_at[i] >= HOLD_MS) stuck[i] = true;     // never let go since power-on
            if (p && i == 0 && !from_start[i] && !used[i] && now - down_at[i] >= HOLD_MS) {   // LEFT held: turn the picture
                used[i] = true; app_set_flip(!app_flip()); app_audio_test(ST_EV_RING);
            }
            if (!p && was[i]) {
                if (!used[i] && !stuck[i] && now - down_at[i] < HOLD_MS) { seen[i] = true; app_audio_test(ST_EV_FLAP); }
                stuck[i] = from_start[i] = false;
            }
            was[i] = p;
        }
        if (!pwr_ok && (frame % 16) == 0 && board_power_key_pressed()) { pwr_ok = true; app_audio_test(ST_EV_FLAP); }
        bool all = seen[0] && seen[1] && seen[2] && seen[3] && pwr_ok;
        if (all && was[0] && was[1] && !used[0]) {                                     // both wings: play
            app_save_i32("tested", 1);
            app_audio_test(ST_EV_ROUND_CLEAR);
            ESP_LOGI(TAG, "passed");
            while (app_pin_pressed(PIN[0]) || app_pin_pressed(PIN[1])) vTaskDelay(10);
            return;
        }
        if (app_display_ok() && (frame % 16) == 0) {
            char t[48];
            int y = 10;
            memset(fb, STR_PAL_INK, ST_FB_W * ST_FB_H);
            st_draw_text(fb, 8, y, "STRUTHIO", STR_PAL_GOLD_LIGHT, 2); y += 22;
            st_draw_text(fb, 8, y, "FIRST POWER-ON CHECK", STR_PAL_GOLD, 1); y += 20;
            st_draw_text(fb, 8, y, "PRESS EACH BUTTON ONCE:", STR_PAL_IVORY, 1); y += 14;
            for (int i = 0; i < KEYS; i++) {
                snprintf(t, sizeof t, "%s %s", NAME[i], stuck[i] ? "STUCK DOWN" : seen[i] ? "OK" : "PRESS IT");
                st_draw_text(fb, 16, y, t, stuck[i] ? STR_PAL_LAVA_HOT : seen[i] ? STR_PAL_GREEN : STR_PAL_CYAN_LIGHT, 1); y += 12;
            }
            if (!app_is_one()) {
                snprintf(t, sizeof t, "%s %s", "POWER (SIDE)  ", pwr_ok ? "OK" : "PRESS IT SHORT");
                st_draw_text(fb, 16, y, t, pwr_ok ? STR_PAL_GREEN : STR_PAL_CYAN_LIGHT, 1); y += 12;
            }
            y += 6;
            st_draw_text(fb, 8, y, "EACH PRESS CLICKS: THAT IS THE", STR_PAL_IVORY_DARK, 1); y += 12;
            st_draw_text(fb, 8, y, "SPEAKER. NO CLICK? CHECK ITS PLUG.", STR_PAL_IVORY_DARK, 1); y += 18;
            board_power_t pw;
            bool ok = board_power_read(&pw);
            if (ok && pw.battery_present)
                snprintf(t, sizeof t, "BATTERY %u.%02uV  OK", pw.battery_mv / 1000, (pw.battery_mv % 1000) / 10);
            else snprintf(t, sizeof t, "NO BATTERY: CHECK ITS PLUG");
            st_draw_text(fb, 8, y, t, ok && pw.battery_present ? STR_PAL_GREEN : STR_PAL_LAVA_HOT, 1); y += 12;
            st_draw_text(fb, 8, y, ok && pw.vbus_present ? (pw.charging ? "USB: CHARGING" : "USB: PLUGGED IN") : "USB: NOT PLUGGED IN",
                         STR_PAL_IVORY, 1); y += 18;
            st_draw_text(fb, 8, y, "UPSIDE DOWN? HOLD LEFT WING 2 S.", STR_PAL_IVORY_DARK, 1); y += 12;
            st_draw_text(fb, 8, y, app_is_one() ? "OFF: SLIDE THE SWITCH DOWN." : "OFF: HOLD THE POWER BUTTON 4 S.", STR_PAL_IVORY_DARK, 1); y += 20;
            if (stuck[0] || stuck[1] || stuck[2] || stuck[3]) {
                st_draw_text(fb, 8, y, "A STUCK BUTTON: ITS CAP RUBS.", STR_PAL_LAVA_HOT, 1); y += 12;
                st_draw_text(fb, 8, y, "SEE THE MANUAL: FAULTS.", STR_PAL_LAVA_HOT, 1); y += 12;
            } else if (all) {
                st_draw_text(fb, 8, y, "ALL GOOD!", STR_PAL_GREEN, 2); y += 22;
                st_draw_text(fb, 8, y, "PRESS BOTH WINGS TO PLAY.", STR_PAL_GREEN, 1);
            }
            app_present(fb);
            if (!lit) { app_backlight_on(); lit = true; }
        }
        vTaskDelay(1);
    }
}
