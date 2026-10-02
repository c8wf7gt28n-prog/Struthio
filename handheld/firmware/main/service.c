// STRUTHIO HANDHELD · hidden service mode (both wings held at power-on).
//
// Screen + USB log:
//   - build, reset reason, PSRAM / internal heap
//   - live wing and DART-rocker states, debounced press counts, darts fired, DART trial
//   - ON-DEVICE GOLDEN REPLAY: the embedded climb.trace (10,011 ticks) through
//     the C core with every tick's SHA-256 digest checked against the browser,
//     then again without digests to time the bare simulation per tick
//     (both include a 1-tick yield every 256 ticks, so they slightly over-report)
//   - panel benchmark: full 320x480 presents, ms per frame
//   - sound: codec found, music loop found, volume level
// LEFT tap: next DART trial (saved).  LEFT held 1 s: next volume level (saved;
// plays the ring chime).  RIGHT tap: run the replay + benchmark again (the
// round-clear sting plays when it finishes).
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "struthio_app.h"
#include "struthio_greybox.h"
#include "struthio_replay.h"
#include "struthio_rules.h"

extern const uint8_t climb_trace_start[] __asm__("_binary_climb_trace_start");
extern const uint8_t climb_trace_end[] __asm__("_binary_climb_trace_end");

static const char *TAG = "SERVICE";
static char g_replay_line[2][48];
static char g_bench_line[48];

// The replay runs for seconds: yield now and then so the idle task (and its
// watchdog) keep running.
static void yield_tick(void *ctx, long tick, const st_state_t *s, const st_events_t *ev) {
    (void)ctx; (void)s; (void)ev;
    if ((tick & 255) == 255) vTaskDelay(1);
}
static void run_checks(void) {
    st_replay_result_t r;
    size_t size = (size_t)(climb_trace_end - climb_trace_start);
    int64_t t0 = esp_timer_get_time();
    st_replay_hooks_t hooks = {NULL, NULL, yield_tick};
    bool ok = st_replay(climb_trace_start, size, true, &hooks, &r);
    int64_t t1 = esp_timer_get_time();
    st_replay_result_t timing;   // the timing run skips the digests, so its chain is not the game's
    st_replay(climb_trace_start, size, false, &hooks, &timing);
    int64_t t2 = esp_timer_get_time();
    double us_digest = (double)(t1 - t0) / (r.ran ? r.ran : 1), us_sim = (double)(t2 - t1) / (r.ran ? r.ran : 1);
    snprintf(g_replay_line[0], sizeof g_replay_line[0], "GOLDEN %s %ld TICKS", ok ? "PASS" : "FAIL", r.ran);
    snprintf(g_replay_line[1], sizeof g_replay_line[1], "SIM %.0f US/TICK  +DIGEST %.0f", us_sim, us_digest);
    ESP_LOGI(TAG, "golden replay %s: %s ticks=%ld chain=%.16s %s", r.name, ok ? "PASS" : "FAIL", r.ran, r.chain, ok ? "" : r.why);
    ESP_LOGI(TAG, "simulation %.1f us/tick, with SHA-256 digest %.1f us/tick (budget 16667)", us_sim, us_digest);
    if (app_display_ok()) {
        uint8_t *fb = app_framebuffer();
        memset(fb, STR_PAL_NAVY, ST_FB_W * ST_FB_H);
        int64_t b0 = esp_timer_get_time();
        for (int i = 0; i < 30; i++) { fb[i] = (uint8_t)i; app_present(fb); }
        double ms = (double)(esp_timer_get_time() - b0) / 30000.0;
        snprintf(g_bench_line, sizeof g_bench_line, "PANEL %.1f MS/FRAME %.0f FPS", ms, 1000.0 / ms);
        ESP_LOGI(TAG, "panel: %.2f ms per full 320x480 present (%.1f fps)", ms, 1000.0 / ms);
    } else snprintf(g_bench_line, sizeof g_bench_line, "PANEL NOT WIRED");
}

void service_mode_run(st_buttons_t *b, st_norm_t *norm) {
    ESP_LOGW(TAG, "SERVICE MODE: power-cycle to play");
    // Let go of both wings first so the exit chord is not read as a command.
    while (app_pin_pressed(17) || app_pin_pressed(18)) vTaskDelay(10);
    st_norm_init(norm);
    st_norm_set_mode(norm, ST_MODE_PLAY);
    st_buttons_init(b, norm, (st_dart_trial_t)b->trial, app_now_ms());
    app_audio_start();
    run_checks();
    app_audio_test(ST_EV_ROUND_CLEAR);
    uint8_t *fb = app_framebuffer();
    uint32_t frame = 0;
    // Taps act on release, so a hold can mean something else (LEFT: volume).
    uint32_t down_at[2] = {0, 0};
    bool was[2] = {false, false}, held_used[2] = {false, false};
    for (;;) {
        uint32_t now = app_now_ms();
        st_buttons_sample(b, app_pin_pressed(17), app_pin_pressed(18), now);
        st_buttons_sample_rocker(b, app_pin_pressed(21), app_pin_pressed(38), now);
        (void)st_norm_frame(norm, true);     // keep the normalizer's queue drained
        for (int side = 0; side < 2; side++) {
            bool held = st_buttons_held(b, side == 0 ? ST_SIDE_LEFT : ST_SIDE_RIGHT);
            if (held && !was[side]) { down_at[side] = now; held_used[side] = false; }
            if (held && side == 0 && !held_used[0] && now - down_at[0] >= 1000) {
                held_used[0] = true;
                app_set_volume(app_volume() + 1);
                app_audio_test(ST_EV_RING);
            }
            if (held && side == 1 && !held_used[1] && now - down_at[1] >= 1000) {
                held_used[1] = true;
                app_set_flip(!app_flip());
                app_audio_test(ST_EV_FLAP);
            }
            if (!held && was[side] && !held_used[side]) {
                if (side == 0) {
                    st_dart_trial_t t = (st_dart_trial_t)((b->trial + 1) % (ST_DART_OFF + 1));
                    b->trial = (uint8_t)t;
                    app_save_i32("dart", t);
                    ESP_LOGI(TAG, "DART trial -> %s", st_dart_trial_name(t));
                    app_audio_test(ST_EV_FLAP);
                } else {
                    run_checks();
                    app_audio_test(ST_EV_ROUND_CLEAR);
                }
            }
            was[side] = held;
        }
        if (app_display_ok() && (frame++ % 8) == 0) {
            char t[48];
            memset(fb, STR_PAL_INK, ST_FB_W * ST_FB_H);
            st_draw_text(fb, 8, 8, "STRUTHIO SERVICE", STR_PAL_GOLD_LIGHT, 2);
            st_draw_text(fb, 8, 30, "HANDHELD / CORE 1.8.0 / " __DATE__, STR_PAL_GOLD, 1);
            snprintf(t, sizeof t, "RESET %d  PSRAM %uK  RAM %uK", (int)esp_reset_reason(),
                     (unsigned)(heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024), (unsigned)(heap_caps_get_free_size(MALLOC_CAP_INTERNAL) / 1024));
            st_draw_text(fb, 8, 48, t, STR_PAL_IVORY, 1);
            snprintf(t, sizeof t, "LEFT %s %lu   RIGHT %s %lu", st_buttons_held(b, ST_SIDE_LEFT) ? "DOWN" : "UP  ", (unsigned long)b->presses[0],
                     st_buttons_held(b, ST_SIDE_RIGHT) ? "DOWN" : "UP  ", (unsigned long)b->presses[1]);
            st_draw_text(fb, 8, 72, t, STR_PAL_CYAN_LIGHT, 1);
            snprintf(t, sizeof t, "DART %s  FIRED %lu", st_dart_trial_name((st_dart_trial_t)b->trial), (unsigned long)b->darts);
            st_draw_text(fb, 8, 84, t, STR_PAL_CYAN_LIGHT, 1);
            snprintf(t, sizeof t, "ROCKER L %s %lu   R %s %lu", st_buttons_rocker_held(b, ST_SIDE_LEFT) ? "DOWN" : "UP  ", (unsigned long)b->rocker_presses[0],
                     st_buttons_rocker_held(b, ST_SIDE_RIGHT) ? "DOWN" : "UP  ", (unsigned long)b->rocker_presses[1]);
            st_draw_text(fb, 8, 96, t, STR_PAL_CYAN_LIGHT, 1);
            st_draw_text(fb, 8, 108, g_replay_line[0], strstr(g_replay_line[0], "PASS") ? STR_PAL_GREEN : STR_PAL_LAVA_HOT, 1);
            st_draw_text(fb, 8, 120, g_replay_line[1], STR_PAL_IVORY, 1);
            st_draw_text(fb, 8, 132, g_bench_line, STR_PAL_IVORY, 1);
            snprintf(t, sizeof t, "AUDIO %s  MUSIC %s  VOL %d/%d", app_audio_ok() ? "OK" : "NO CODEC", app_music_ok() ? "OK" : "NONE",
                     app_volume(), APP_VOLUME_LEVELS - 1);
            st_draw_text(fb, 8, 144, t, app_audio_ok() ? STR_PAL_IVORY : STR_PAL_LAVA_HOT, 1);
            st_draw_text(fb, 8, 168, "LEFT TAP: NEXT DART MODE", STR_PAL_IVORY_DARK, 1);
            st_draw_text(fb, 8, 180, "LEFT HOLD 1 S: VOLUME", STR_PAL_IVORY_DARK, 1);
            st_draw_text(fb, 8, 192, "RIGHT TAP: RUN CHECKS AGAIN", STR_PAL_IVORY_DARK, 1);
            st_draw_text(fb, 8, 204, "RIGHT HOLD 1 S: TURN SCREEN 180", STR_PAL_IVORY_DARK, 1);
            st_draw_text(fb, 8, 216, "POWER-CYCLE TO PLAY", STR_PAL_IVORY_DARK, 1);
            app_present(fb);
        }
        vTaskDelay(1);
    }
}
