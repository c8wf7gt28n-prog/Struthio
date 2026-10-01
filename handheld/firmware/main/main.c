/*
 * STRUTHIO ESP32-S3 Handheld - Prototype A0 firmware.
 *
 * POWER ON -> STRUTHIO STARTS -> two physical wing buttons play a full round.
 *
 *  - input task   1 kHz, core 0: GPIO17/18 -> debounce -> input normalizer
 *  - game task    60 Hz fixed, core 1: frame -> st_step (the bit-exact port of
 *                 STRUTHIO ARCADE 1.8.0) -> events -> snapshot every 2nd tick
 *  - render task  core 0: newest snapshot -> greybox renderer -> 320x480 panel
 *                 in 40-line bands. It may drop frames; it never slows the game.
 *  - both wings held at power-on -> service mode (diagnostics, on-device golden
 *    replay, panel benchmark, DART trial selection)
 *
 * Persistence: high score + DART trial in NVS, written from the render task,
 * never inside a game tick. The task watchdog resets a hung game back into play.
 */
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_random.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "board.h"
#include "struthio_app.h"
#include "struthio_buttons.h"
#include "struthio_core.h"
#include "struthio_greybox.h"
#include "struthio_input.h"

#define STRUTHIO_GPIO_LEFT_WING   17
#define STRUTHIO_GPIO_RIGHT_WING  18
#define STRUTHIO_BUTTON_ACTIVE_LEVEL 0     // normally-open switch to GND, pull-up on

static const char *TAG = "STRUTHIO";

// ---- shared state ---------------------------------------------------------------------
static portMUX_TYPE g_input_mux = portMUX_INITIALIZER_UNLOCKED;
static portMUX_TYPE g_snap_mux = portMUX_INITIALIZER_UNLOCKED;
static st_norm_t g_norm;                    // guarded by g_input_mux
static st_buttons_t g_buttons;              // guarded by g_input_mux
static st_state_t g_state;                  // game task only
static st_events_t g_events;                // game task only
static st_state_t g_snapshot;               // guarded by g_snap_mux
static uint32_t g_snapshot_frame;
static const char *g_banner;
static uint32_t g_banner_until;
static TaskHandle_t g_render_task;
static int32_t g_high_score;
static volatile bool g_high_score_dirty;
static bool g_display_ok;

app_stats_t g_stats;

uint32_t app_now_ms(void) { return (uint32_t)(esp_timer_get_time() / 1000ULL); }
bool app_pin_pressed(int pin) { return gpio_get_level((gpio_num_t)pin) == STRUTHIO_BUTTON_ACTIVE_LEVEL; }

static void init_wing_gpio(void) {
    gpio_config_t cfg = {
        .pin_bit_mask = (1ULL << STRUTHIO_GPIO_LEFT_WING) | (1ULL << STRUTHIO_GPIO_RIGHT_WING),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&cfg));
}

// ---- persistence (NVS) ---------------------------------------------------------------------
static void nvs_init_or_erase(void) {
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
}
int32_t app_load_i32(const char *key, int32_t fallback) {
    nvs_handle_t h;
    int32_t v = fallback;
    if (nvs_open("struthio", NVS_READONLY, &h) == ESP_OK) {
        if (nvs_get_i32(h, key, &v) != ESP_OK) v = fallback;
        nvs_close(h);
    }
    return v;
}
void app_save_i32(const char *key, int32_t v) {
    nvs_handle_t h;
    if (nvs_open("struthio", NVS_READWRITE, &h) != ESP_OK) return;
    if (nvs_set_i32(h, key, v) == ESP_OK) nvs_commit(h);
    nvs_close(h);
}

// ---- display ------------------------------------------------------------------------------
static uint8_t *g_fb;                       // 256 x 384 indexed
static uint16_t *g_band;                    // 320 x 40 RGB565, DMA-capable

void app_present(const uint8_t *fb) {
    if (!g_display_ok) return;
    for (int y0 = 0; y0 < BOARD_LCD_H; y0 += BOARD_BAND_LINES) {
        for (int i = 0; i < BOARD_BAND_LINES; i++) st_present_line(fb, y0 + i, g_band + i * BOARD_LCD_W, true);
        board_display_lines(y0, BOARD_BAND_LINES, g_band);
    }
}
uint8_t *app_framebuffer(void) { return g_fb; }
bool app_display_ok(void) { return g_display_ok; }

// ---- input task: 1 kHz --------------------------------------------------------------------
static void input_task(void *arg) {
    (void)arg;
    for (;;) {
        bool l = app_pin_pressed(STRUTHIO_GPIO_LEFT_WING), r = app_pin_pressed(STRUTHIO_GPIO_RIGHT_WING);
        uint32_t now = app_now_ms();
        portENTER_CRITICAL(&g_input_mux);
        st_buttons_sample(&g_buttons, l, r, now);
        portEXIT_CRITICAL(&g_input_mux);
        vTaskDelay(1);                       // CONFIG_FREERTOS_HZ=1000
    }
}

// ---- game task: fixed 60 Hz ------------------------------------------------------------------
static void new_run(void) {
    uint32_t seed = esp_random();
    st_state_init(&g_state, seed ? seed : 1);
    st_start_run(&g_state, &g_events);
    portENTER_CRITICAL(&g_input_mux);
    st_norm_set_mode(&g_norm, ST_MODE_PLAY);
    st_norm_cleanup(&g_norm);
    portEXIT_CRITICAL(&g_input_mux);
    ESP_LOGI(TAG, "NEW RUN seed %lu", (unsigned long)seed);
}
static void on_events(const st_events_t *ev) {
    for (int i = 0; i < ev->n; i++) {
        const st_event_t *e = &ev->e[i];
        board_audio_cue((st_event_type_t)e->type);
        switch (e->type) {
        case ST_EV_PLAYER_DEATH:
        case ST_EV_GAMEOVER:
            portENTER_CRITICAL(&g_input_mux);
            st_norm_cleanup(&g_norm);         // as the browser session does
            portEXIT_CRITICAL(&g_input_mux);
            if (e->type == ST_EV_GAMEOVER) {
                g_stats.game_over_tick = (uint32_t)g_stats.ticks;
                if (g_state.sim.score > g_high_score) { g_high_score = g_state.sim.score; g_high_score_dirty = true; }
                ESP_LOGI(TAG, "GAME OVER score %ld (best %ld)", (long)g_state.sim.score, (long)g_high_score);
            }
            break;
        case ST_EV_GOLD_RING_OPEN: g_banner = "6/6 - THE GOLD RING IS AT THE MOON"; g_banner_until = g_stats.ticks + 150; break;
        case ST_EV_EXTRA_LIFE: g_banner = "EXTRA JOUST MARK"; g_banner_until = g_stats.ticks + 100; break;
        case ST_EV_ROUND_CLEAR: ESP_LOGI(TAG, "ROUND %ld CLEAR score %ld", (long)g_state.tower.round, (long)g_state.sim.score); break;
        default: break;
        }
    }
}
enum { RESTART_GUARD_TICKS = 60 };
static void game_tick(void) {
    st_input_t in;
    portENTER_CRITICAL(&g_input_mux);
    in = st_norm_frame(&g_norm, st_can_accept_buffered_flap(&g_state));
    portEXIT_CRITICAL(&g_input_mux);
    if (g_state.sim.shell == ST_SHELL_GAMEOVER) {
        // Either wing starts a fresh run after a short guard (no START button).
        if (in.flap_edge && g_stats.ticks - g_stats.game_over_tick > RESTART_GUARD_TICKS) new_run();
    } else {
        int64_t t0 = esp_timer_get_time();
        st_step(&g_state, &in, &g_events);
        uint32_t us = (uint32_t)(esp_timer_get_time() - t0);
        g_stats.sim_us_last = us;
        if (us > g_stats.sim_us_max) g_stats.sim_us_max = us;
        on_events(&g_events);
    }
    g_stats.ticks++;
    if ((g_stats.ticks & 1) == 0) {          // 30 fps snapshots for the renderer
        portENTER_CRITICAL(&g_snap_mux);
        memcpy(&g_snapshot, &g_state, sizeof g_state);
        g_snapshot_frame = (uint32_t)g_stats.ticks;
        portEXIT_CRITICAL(&g_snap_mux);
        if (g_render_task) xTaskNotifyGive(g_render_task);
    }
}
static void game_task(void *arg) {
    (void)arg;
    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
    // Rational microsecond schedule: 16,666 / 16,667 us steps averaging exactly 60 Hz.
    int64_t epoch = esp_timer_get_time();
    uint64_t index = 0;
    for (;;) {
        int64_t next = epoch + (int64_t)((index * 1000000ULL) / 60ULL);
        int64_t now = esp_timer_get_time();
        if (now < next) {
            int64_t wait_ms = (next - now) / 1000;
            vTaskDelay(wait_ms > 1 ? (TickType_t)(wait_ms - 1) : 1);
            continue;
        }
        if (now - next > 4 * (1000000LL / 60)) {   // debugger stall: no catch-up burst
            g_stats.missed_deadlines++;
            epoch = now; index = 0;
        }
        game_tick();
        esp_task_wdt_reset();
        index++;
    }
}

// ---- render task ---------------------------------------------------------------------------
static void render_task(void *arg) {
    (void)arg;
    static st_state_t snap;
    st_camera_t cam;
    st_camera_reset(&cam);
    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
    for (;;) {
        ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(500));
        esp_task_wdt_reset();
        uint32_t frame;
        portENTER_CRITICAL(&g_snap_mux);
        memcpy(&snap, &g_snapshot, sizeof snap);
        frame = g_snapshot_frame;
        portEXIT_CRITICAL(&g_snap_mux);
        if (snap.sim.shell == ST_SHELL_ATTRACT) continue;
        if (snap.sim.tick < 2) st_camera_reset(&cam);
        st_view_t view = {st_camera_resolve(&cam, &snap), frame, g_high_score, frame < g_banner_until ? g_banner : NULL};
        int64_t t0 = esp_timer_get_time();
        st_render(g_fb, &snap, &view);
        int64_t t1 = esp_timer_get_time();
        app_present(g_fb);
        int64_t t2 = esp_timer_get_time();
        g_stats.render_us = (uint32_t)(t1 - t0);
        g_stats.present_us = (uint32_t)(t2 - t1);
        g_stats.frames++;
        if (g_high_score_dirty) { g_high_score_dirty = false; app_save_i32("best", g_high_score); }
        if ((g_stats.frames % 300) == 0)
            ESP_LOGI(TAG, "tick %llu sim %lu us (max %lu) render %lu us present %lu us missed %lu",
                     (unsigned long long)g_stats.ticks, (unsigned long)g_stats.sim_us_last, (unsigned long)g_stats.sim_us_max,
                     (unsigned long)g_stats.render_us, (unsigned long)g_stats.present_us, (unsigned long)g_stats.missed_deadlines);
    }
}

// ---- boot ---------------------------------------------------------------------------------
void app_main(void) {
    ESP_LOGI(TAG, "STRUTHIO Prototype A0 boot (core: STRUTHIO ARCADE 1.8.0 port)");
    init_wing_gpio();
    nvs_init_or_erase();
    st_dart_trial_t trial = (st_dart_trial_t)app_load_i32("dart", ST_DART_TRIAL_C_BOTH_HOLD);
    if (trial > ST_DART_OFF) trial = ST_DART_TRIAL_C_BOTH_HOLD;
    g_high_score = app_load_i32("best", 0);
    st_norm_init(&g_norm);
    st_buttons_init(&g_buttons, &g_norm, trial, app_now_ms());

    g_fb = heap_caps_malloc(ST_FB_W * ST_FB_H, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (!g_fb) g_fb = heap_caps_malloc(ST_FB_W * ST_FB_H, MALLOC_CAP_SPIRAM);
    g_band = heap_caps_malloc(BOARD_LCD_W * BOARD_BAND_LINES * sizeof(uint16_t), MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    configASSERT(g_fb && g_band);

    board_power_init();
    g_display_ok = board_display_init();

    // Hidden service mode: hold BOTH wings while powering on (650 ms within an 800 ms guard).
    uint32_t guard = app_now_ms();
    while ((uint32_t)(app_now_ms() - guard) < 800) {
        st_buttons_sample(&g_buttons, app_pin_pressed(STRUTHIO_GPIO_LEFT_WING), app_pin_pressed(STRUTHIO_GPIO_RIGHT_WING), app_now_ms());
        if (st_buttons_service_requested(&g_buttons, app_now_ms())) {
            service_mode_run(&g_buttons, &g_norm);   // never returns
        }
        vTaskDelay(1);
    }
    st_norm_init(&g_norm);                    // discard boot-guard presses
    st_buttons_init(&g_buttons, &g_norm, trial, app_now_ms());
    board_audio_init();
    board_backlight(100);
    new_run();
    ESP_LOGI(TAG, "DART trial %s, best %ld, display %s", st_dart_trial_name(trial), (long)g_high_score, g_display_ok ? "ok" : "headless");

    xTaskCreatePinnedToCore(input_task, "wings", 3072, NULL, 10, NULL, 0);
    xTaskCreatePinnedToCore(render_task, "render", 6144, NULL, 5, &g_render_task, 0);
    xTaskCreatePinnedToCore(game_task, "game", 8192, NULL, 9, NULL, 1);
}
