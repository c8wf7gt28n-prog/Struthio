// STRUTHIO HANDHELD · hidden service mode (both wings held at power-on).
//
// Screen + USB log:
//   - build, reset reason, PSRAM / internal heap
//   - live wing states, debounced press counts, darts fired, DART trial
//   - ON-DEVICE GOLDEN REPLAY: the embedded climb.trace (10,011 ticks) through
//     the C core with every tick's SHA-256 digest checked against the browser,
//     then again without digests to time the bare simulation per tick
//     (both include a 1-tick yield every 256 ticks, so they slightly over-report)
//   - panel benchmark: full 320x480 presents, ms per frame
// LEFT tap: next DART trial (saved).  RIGHT tap: run the replay + benchmark again.
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
    st_replay(climb_trace_start, size, false, &hooks, &r);
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
    run_checks();
    uint8_t *fb = app_framebuffer();
    uint32_t frame = 0;
    for (;;) {
        st_buttons_sample(b, app_pin_pressed(17), app_pin_pressed(18), app_now_ms());
        st_input_t f = st_norm_frame(norm, true);
        if (f.flap_edge && f.flap_kind == ST_FLAP_LEFT) {
            st_dart_trial_t t = (st_dart_trial_t)((b->trial + 1) % (ST_DART_OFF + 1));
            b->trial = (uint8_t)t;
            app_save_i32("dart", t);
            ESP_LOGI(TAG, "DART trial -> %s", st_dart_trial_name(t));
        } else if (f.flap_edge && f.flap_kind == ST_FLAP_RIGHT) run_checks();
        if (app_display_ok() && (frame++ % 8) == 0) {
            char t[48];
            memset(fb, STR_PAL_INK, ST_FB_W * ST_FB_H);
            st_draw_text(fb, 8, 8, "STRUTHIO SERVICE", STR_PAL_GOLD_LIGHT, 2);
            st_draw_text(fb, 8, 30, "A0 / CORE 1.8.0 PORT / " __DATE__, STR_PAL_GOLD, 1);
            snprintf(t, sizeof t, "RESET %d  PSRAM %uK  RAM %uK", (int)esp_reset_reason(),
                     (unsigned)(heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024), (unsigned)(heap_caps_get_free_size(MALLOC_CAP_INTERNAL) / 1024));
            st_draw_text(fb, 8, 48, t, STR_PAL_IVORY, 1);
            snprintf(t, sizeof t, "LEFT %s %lu   RIGHT %s %lu", st_buttons_held(b, ST_SIDE_LEFT) ? "DOWN" : "UP  ", (unsigned long)b->presses[0],
                     st_buttons_held(b, ST_SIDE_RIGHT) ? "DOWN" : "UP  ", (unsigned long)b->presses[1]);
            st_draw_text(fb, 8, 72, t, STR_PAL_CYAN_LIGHT, 1);
            snprintf(t, sizeof t, "DART %s  FIRED %lu", st_dart_trial_name((st_dart_trial_t)b->trial), (unsigned long)b->darts);
            st_draw_text(fb, 8, 84, t, STR_PAL_CYAN_LIGHT, 1);
            st_draw_text(fb, 8, 108, g_replay_line[0], strstr(g_replay_line[0], "PASS") ? STR_PAL_GREEN : STR_PAL_LAVA_HOT, 1);
            st_draw_text(fb, 8, 120, g_replay_line[1], STR_PAL_IVORY, 1);
            st_draw_text(fb, 8, 132, g_bench_line, STR_PAL_IVORY, 1);
            st_draw_text(fb, 8, 160, "LEFT: NEXT DART TRIAL", STR_PAL_IVORY_DARK, 1);
            st_draw_text(fb, 8, 172, "RIGHT: RUN CHECKS AGAIN", STR_PAL_IVORY_DARK, 1);
            st_draw_text(fb, 8, 184, "POWER-CYCLE TO PLAY", STR_PAL_IVORY_DARK, 1);
            app_present(fb);
        }
        vTaskDelay(1);
    }
}
