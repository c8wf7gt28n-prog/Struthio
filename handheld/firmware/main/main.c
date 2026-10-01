/*
 * STRUTHIO ESP32-S3 Handheld - Prototype A0 firmware.
 *
 * POWER ON -> STRUTHIO STARTS -> two physical wing buttons play a full round.
 *
 *  - input task   1 kHz, core 0: GPIO17/18 -> debounce -> input normalizer
 *  - game task    60 Hz fixed, core 1: frame -> st_step (the bit-exact port of
 *                 STRUTHIO ARCADE 1.8.0) -> events -> the scene builder (the
 *                 port of the browser's scene.mjs: the same quads, every tick)
 *                 and the HUD model -> a frame published every 2nd tick
 *  - render task  core 0 + its helper on core 1: the newest frame -> the panel
 *                 renderer (render/struthio_panel.c: the browser's picture at
 *                 320x480 from the asset pack mapped out of flash), even bands
 *                 on core 0, odd bands on core 1, 16 lines each straight to the
 *                 panel. It may drop frames; it never slows the game.
 *                 Without an asset pack it falls back to the greybox renderer.
 *  - GAME OVER: both wings held together start a new run (a flap cannot)
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
#include "freertos/semphr.h"
#include "driver/gpio.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_partition.h"
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
#include "struthio_pak.h"
#include "struthio_panel.h"
#include "struthio_scene.h"

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

// ---- the browser's picture: scene + HUD, built by the game task ----------------------------
// Three frame slots: the game task builds into one, the render task reads
// another, the newest complete one waits in the third.
typedef struct {
    st_quads_t quads;
    st_hud_t hud;
    st_frame_params_t fp;
    uint32_t tick;
} frame_slot_t;
static frame_slot_t *g_slots;               // [3], PSRAM
static int g_slot_build = 0, g_slot_ready = -1, g_slot_reading = -1;   // guarded by g_snap_mux
static st_scene_t g_scene;                  // game task only
static st_camera_t g_camera;                // game task only
static st_hud_t g_hud;                      // game task only
static st_gameover_info_t g_over;           // game task only
static bool g_panel_ok;                     // asset pack mapped: the panel renderer runs
static st_panel_textures_t g_tex;
static st_hud_assets_t g_hud_assets;
static st_panel_luts_t *g_luts;
static st_panel_work_t *g_work[2];          // one per core
static SemaphoreHandle_t g_display_lock, g_helper_go, g_helper_done;
static TaskHandle_t g_helper_task;
static const frame_slot_t *g_helper_frame;

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

// The asset pack (host/make_pak) lives in the 'assets' partition and is mapped,
// not copied: textures are read through the flash cache.
static bool map_asset_pack(void) {
    const esp_partition_t *part = esp_partition_find_first(ESP_PARTITION_TYPE_DATA, 0x40, "assets");
    if (!part) { ESP_LOGW(TAG, "no assets partition"); return false; }
    const void *p = NULL;
    esp_partition_mmap_handle_t h;
    if (esp_partition_mmap(part, 0, part->size, ESP_PARTITION_MMAP_DATA, &p, &h) != ESP_OK) { ESP_LOGW(TAG, "assets: mmap failed"); return false; }
    char err[96];
    if (!st_pak_open(p, part->size, &g_tex, &g_hud_assets, err, sizeof err)) {
        ESP_LOGW(TAG, "assets: %s (flash build/assets/struthio.pak; see README)", err);
        return false;
    }
    g_luts = heap_caps_malloc(sizeof *g_luts, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (!g_luts) g_luts = heap_caps_malloc(sizeof *g_luts, MALLOC_CAP_SPIRAM);
    g_slots = heap_caps_malloc(3 * sizeof *g_slots, MALLOC_CAP_SPIRAM);
    for (int k = 0; k < 2; k++) {
        g_work[k] = heap_caps_malloc(sizeof *g_work[k], MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
        if (g_work[k]) g_work[k]->line = heap_caps_malloc(ST_BAND_ROWS * ST_PANEL_W * sizeof(uint16_t), MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    }
    if (!g_luts || !g_slots || !g_work[0] || !g_work[1] || !g_work[0]->line || !g_work[1]->line) { ESP_LOGW(TAG, "assets: out of memory"); return false; }
    st_panel_luts_init(g_luts);
    g_display_lock = xSemaphoreCreateMutex();
    g_helper_go = xSemaphoreCreateBinary();
    g_helper_done = xSemaphoreCreateBinary();
    return g_display_lock && g_helper_go && g_helper_done;
}
// A finished band: to the panel's byte order, then out (one sender at a time).
static void band_out(void *ctx, int y0, int rows, const uint16_t *px) {
    (void)ctx;
    uint16_t *b = (uint16_t *)px;           // the workspace's own DMA line buffer
    for (int i = 0; i < rows * ST_PANEL_W; i++) b[i] = (uint16_t)(b[i] << 8 | b[i] >> 8);
    xSemaphoreTake(g_display_lock, portMAX_DELAY);
    board_display_lines(y0, rows, b);
    xSemaphoreGive(g_display_lock);
}
static void render_bands(const frame_slot_t *f, int core) {
    st_panel_render_bands(&g_tex, &g_hud_assets, &f->hud, g_luts, &f->quads, &f->fp, core, 2, g_work[core], band_out, NULL);
}
// core 1: the odd bands of the frame the render task hands over
static void render_helper_task(void *arg) {
    (void)arg;
    for (;;) {
        xSemaphoreTake(g_helper_go, portMAX_DELAY);
        render_bands(g_helper_frame, 1);
        xSemaphoreGive(g_helper_done);
    }
}
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
    st_scene_init(&g_scene);
    st_camera_reset(&g_camera);
    memset(&g_over, 0, sizeof g_over);
    st_hud_reset(&g_hud, g_scene.render_tick);
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
                bool best = g_state.sim.score > g_high_score;
                if (best) { g_high_score = g_state.sim.score; g_high_score_dirty = true; }
                g_over = (st_gameover_info_t){g_state.sim.score, g_state.tower.round, g_high_score, best, true};
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
// The scene builder runs every tick exactly as the browser session does (its
// feel, popups and animation clocks advance per frame); every 2nd tick's
// result is published for the renderer.
static void build_frame(void) {
    static const char *const ITEMS[2] = {"NEW RUN", "TITLE"};
    st_menu_t menu = {ITEMS, 2, 0, g_over};
    frame_slot_t *f = &g_slots[g_slot_build];
    st_scene_build(&g_scene, &g_state, st_camera_resolve(&g_camera, &g_state), &menu, &f->quads);
    st_hud_update(&g_hud, &g_hud_assets, &g_state, &g_scene);
    f->hud = g_hud;
    st_frame_params_default(&f->fp, g_scene.render_tick, g_scene.moon_phase, st_scene_impact(&g_scene, &g_state));
    f->fp.quality = 0;                       // tone + Arcade grade (the panel has no headroom for bloom)
    f->tick = (uint32_t)g_stats.ticks;
}
static void publish_frame(void) {
    portENTER_CRITICAL(&g_snap_mux);
    g_slot_ready = g_slot_build;
    for (int k = 0; k < 3; k++) if (k != g_slot_ready && k != g_slot_reading) { g_slot_build = k; break; }
    portEXIT_CRITICAL(&g_snap_mux);
}
static void game_tick(void) {
    st_input_t in;
    bool chord;
    portENTER_CRITICAL(&g_input_mux);
    in = st_norm_frame(&g_norm, st_can_accept_buffered_flap(&g_state));
    chord = st_buttons_held(&g_buttons, ST_SIDE_LEFT) && st_buttons_held(&g_buttons, ST_SIDE_RIGHT);
    portEXIT_CRITICAL(&g_input_mux);
    if (g_state.sim.shell == ST_SHELL_GAMEOVER) {
        // NEW RUN: both wings together after a short guard; a lone flap from the
        // last fight cannot skip the result.
        if (chord && g_stats.ticks - g_stats.game_over_tick > RESTART_GUARD_TICKS) new_run();
    } else {
        st_pre_tick_t pre = g_panel_ok ? st_scene_pre_tick(&g_state) : (st_pre_tick_t){0};
        int64_t t0 = esp_timer_get_time();
        st_step(&g_state, &in, &g_events);
        uint32_t us = (uint32_t)(esp_timer_get_time() - t0);
        g_stats.sim_us_last = us;
        if (us > g_stats.sim_us_max) g_stats.sim_us_max = us;
        if (g_panel_ok) st_scene_on_events(&g_scene, &g_state, &g_events, &pre);
        on_events(&g_events);
    }
    if (g_panel_ok) {
        int64_t t0 = esp_timer_get_time();
        build_frame();
        g_stats.scene_us = (uint32_t)(esp_timer_get_time() - t0);
    }
    g_stats.ticks++;
    if ((g_stats.ticks & 1) == 0) {          // 30 fps frames for the renderer
        if (g_panel_ok) publish_frame();
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
static void log_stats(void) {
    if ((g_stats.frames % 300) == 0)
        ESP_LOGI(TAG, "tick %llu sim %lu us (max %lu) scene %lu us render %lu us present %lu us missed %lu",
                 (unsigned long long)g_stats.ticks, (unsigned long)g_stats.sim_us_last, (unsigned long)g_stats.sim_us_max,
                 (unsigned long)g_stats.scene_us, (unsigned long)g_stats.render_us, (unsigned long)g_stats.present_us,
                 (unsigned long)g_stats.missed_deadlines);
}
// The panel renderer: the newest published frame, split between the cores.
static void render_panel_frame(void) {
    int slot;
    portENTER_CRITICAL(&g_snap_mux);
    slot = g_slot_ready;
    g_slot_reading = slot;
    portEXIT_CRITICAL(&g_snap_mux);
    if (slot < 0) return;
    int64_t t0 = esp_timer_get_time();
    g_helper_frame = &g_slots[slot];
    xSemaphoreGive(g_helper_go);
    render_bands(&g_slots[slot], 0);
    xSemaphoreTake(g_helper_done, portMAX_DELAY);
    portENTER_CRITICAL(&g_snap_mux);
    g_slot_reading = -1;
    portEXIT_CRITICAL(&g_snap_mux);
    g_stats.render_us = (uint32_t)(esp_timer_get_time() - t0);   // includes sending: bands go out as they finish
    g_stats.present_us = 0;
    g_stats.frames++;
}
static void render_task(void *arg) {
    (void)arg;
    static st_state_t snap;
    st_camera_t cam;
    st_camera_reset(&cam);
    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
    for (;;) {
        ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(500));
        esp_task_wdt_reset();
        if (g_high_score_dirty) { g_high_score_dirty = false; app_save_i32("best", g_high_score); }
        if (g_panel_ok) { render_panel_frame(); log_stats(); continue; }
        // fallback without an asset pack: the greybox renderer
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
        log_stats();
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
    g_panel_ok = g_display_ok && map_asset_pack();
    new_run();
    ESP_LOGI(TAG, "DART trial %s, best %ld, display %s, renderer %s", st_dart_trial_name(trial), (long)g_high_score,
             g_display_ok ? "ok" : "headless", g_panel_ok ? "panel (asset pack)" : "greybox");

    xTaskCreatePinnedToCore(input_task, "wings", 3072, NULL, 10, NULL, 0);
    xTaskCreatePinnedToCore(render_task, "render", 6144, NULL, 5, &g_render_task, 0);
    xTaskCreatePinnedToCore(game_task, "game", 12288, NULL, 9, NULL, 1);
    if (g_panel_ok) xTaskCreatePinnedToCore(render_helper_task, "render1", 6144, NULL, 4, &g_helper_task, 1);
}
