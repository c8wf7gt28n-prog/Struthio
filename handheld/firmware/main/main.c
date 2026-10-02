/*
 * STRUTHIO ESP32-S3 Handheld firmware.
 *
 * POWER ON -> STRUTHIO STARTS -> two physical wing buttons play a full round.
 *
 *  - input task   1 kHz, core 0: GPIO17/18 wings + GPIO21/38 DART rocker ->
 *                 debounce -> input normalizer
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
 *  - audio task   core 0, above the renderer: game events -> the port of the
 *                 browser's conductor + synth (SFX) and the soundtrack loop
 *                 from the 'music' partition -> 48 kHz mono -> ES8311
 *                 (audio/struthio_audio.c). Volume level in NVS.
 *  - GAME OVER: both wings held together start a new run (a flap cannot)
 *  - both wings held at power-on -> service mode (diagnostics, on-device golden
 *    replay, panel benchmark, DART trial selection)
 *
 * Persistence: high score, DART trial and volume in NVS, written only on change, written from the render task,
 * never inside a game tick. The task watchdog resets a hung game back into play.
 */
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "freertos/queue.h"
#include "driver/gpio.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_partition.h"
#include "esp_random.h"
#include "esp_rom_sys.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "board.h"
#include "struthio_app.h"
#include "struthio_audio.h"
#include "struthio_buttons.h"
#include "struthio_core.h"
#include "struthio_greybox.h"
#include "struthio_input.h"
#include "struthio_pak.h"
#include "struthio_panel.h"
#include "struthio_scene.h"

#include "board_pins.h"                  // wings on GPIO17/18 (camera VSYNC/HREF: no camera fitted)

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
static SemaphoreHandle_t g_turn[2], g_helper_go, g_helper_done;   // g_turn: whose band goes to the panel next
static TaskHandle_t g_helper_task;
static const frame_slot_t *g_helper_frame;

app_stats_t g_stats;

uint32_t app_now_ms(void) { return (uint32_t)(esp_timer_get_time() / 1000ULL); }
bool app_pin_pressed(int pin) { return gpio_get_level((gpio_num_t)pin) == STRUTHIO_BUTTON_ACTIVE_LEVEL; }

static void init_wing_gpio(void) {
    gpio_config_t cfg = {
        .pin_bit_mask = (1ULL << STRUTHIO_GPIO_LEFT_WING) | (1ULL << STRUTHIO_GPIO_RIGHT_WING) |
                        (1ULL << STRUTHIO_GPIO_DART_LEFT) | (1ULL << STRUTHIO_GPIO_DART_RIGHT),
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
// Hard power (the slide switch cuts BAT+): NVS survives power loss at any
// moment, but a value being written at that instant can be lost. So settings
// are written only when they change, never periodically, and flash writes are
// read back (CONFIG_SPI_FLASH_VERIFY_WRITE).
void app_save_i32(const char *key, int32_t v) {
    nvs_handle_t h;
    if (app_load_i32(key, ~v) == v) return;   // unchanged: no flash write
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
    if (memcmp(p, "STRGREY0", 8) == 0) {   // idf.py -D STRUTHIO_ART=greybox
        ESP_LOGI(TAG, "assets: greybox marker (STRUTHIO_ART=greybox): flat-colour renderer by request");
        return false;
    }
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
    g_turn[0] = xSemaphoreCreateBinary();
    g_turn[1] = xSemaphoreCreateBinary();
    g_helper_go = xSemaphoreCreateBinary();
    g_helper_done = xSemaphoreCreateBinary();
    if (!g_turn[0] || !g_turn[1] || !g_helper_go || !g_helper_done) return false;
    xSemaphoreGive(g_turn[0]);              // band 0 of the first frame goes first
    return true;
}
// A finished band: to the panel's byte order, then out IN ORDER. The AXS15231B
// takes a frame top to bottom with no row address (board.h), so band k waits
// for band k-1. Even bands come from core 0 and odd bands from core 1, so the
// two cores hand the turn back and forth. While one core's band is on the bus,
// the other core is already rendering its next band.
static void band_out(void *ctx, int y0, int rows, const uint16_t *px) {
    (void)ctx;
    uint16_t *b = (uint16_t *)px;           // the workspace's own DMA line buffer
    for (int i = 0; i < rows * ST_PANEL_W; i++) b[i] = (uint16_t)(b[i] << 8 | b[i] >> 8);
    int k = y0 / ST_BAND_ROWS, next = (k + 1) % ST_PANEL_BANDS;
    xSemaphoreTake(g_turn[k & 1], portMAX_DELAY);
    board_display_lines(y0, rows, b);
    xSemaphoreGive(g_turn[next & 1]);
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

// ---- sound ---------------------------------------------------------------------------------
// The game task posts each event (type + the actor ids JOUST_CLASH needs); the
// audio task turns them into notes between 256-frame renders and hands the
// samples to the I2S DMA, whose wait paces it. Volume: 5 levels, codec percent.
typedef struct { uint8_t type; int16_t a, b; } audio_msg_t;
static QueueHandle_t g_audio_q;
static sta_audio_t g_audio;
static bool g_audio_ok, g_music_ok;
static int g_volume = 2;
static const int VOLUME_PERCENT[APP_VOLUME_LEVELS] = {0, 45, 60, 72, 85};   // bench-tune: low first

static const uint8_t *map_music(size_t *size) {
    const esp_partition_t *part = esp_partition_find_first(ESP_PARTITION_TYPE_DATA, 0x41, "music");
    if (!part) { ESP_LOGW(TAG, "no music partition"); return NULL; }
    const void *p = NULL;
    esp_partition_mmap_handle_t h;
    if (esp_partition_mmap(part, 0, part->size, ESP_PARTITION_MMAP_DATA, &p, &h) != ESP_OK) { ESP_LOGW(TAG, "music: mmap failed"); return NULL; }
    *size = part->size;
    return p;
}
static void audio_task(void *arg) {
    (void)arg;
    static int16_t pcm[2 * STA_BLOCK];
    for (;;) {
        audio_msg_t m;
        while (xQueueReceive(g_audio_q, &m, 0) == pdTRUE) {
            st_event_t e = {0};
            e.type = m.type;
            e.n = 2;
            e.f[0] = (st_field_t){"a", ST_F_INT, m.a, NULL};
            e.f[1] = (st_field_t){"b", ST_F_INT, m.b, NULL};
            sta_audio_event(&g_audio, &e);
        }
        int64_t t0 = esp_timer_get_time();
        sta_audio_render(&g_audio, pcm, 2 * STA_BLOCK);
        uint32_t us = (uint32_t)(esp_timer_get_time() - t0);
        g_stats.audio_us = us;
        if (us > g_stats.audio_us_max) g_stats.audio_us_max = us;
        board_audio_write(pcm, 2 * STA_BLOCK);
    }
}
bool app_audio_start(void) {
    if (g_audio_q) return g_audio_ok;
    size_t music_size = 0;
    const uint8_t *music = map_music(&music_size);
    sta_audio_init(&g_audio, music, music_size, esp_random());
    g_music_ok = g_audio.music_on;
    if (music && !g_music_ok) ESP_LOGW(TAG, "music: not a STRUTHIO music file (flash build/assets/struthio_music.ima; see README)");
    g_audio_q = xQueueCreate(32, sizeof(audio_msg_t));
    g_audio_ok = g_audio_q && board_audio_init();
    g_volume = (int)app_load_i32("volume", 2);
    if (g_volume < 0 || g_volume >= APP_VOLUME_LEVELS) g_volume = 2;
    if (g_audio_ok) {
        board_audio_volume(VOLUME_PERCENT[g_volume]);
        xTaskCreatePinnedToCore(audio_task, "audio", 4096, NULL, 8, NULL, 0);
    }
    ESP_LOGI(TAG, "audio %s, music %s, volume %d/%d", g_audio_ok ? "ok" : "OFF", g_music_ok ? "160 s loop" : "none", g_volume, APP_VOLUME_LEVELS - 1);
    return g_audio_ok;
}
void app_audio_post(const st_event_t *e) {
    if (!g_audio_q) return;
    const st_field_t *a = st_event_field(e, "a"), *b = st_event_field(e, "b");
    audio_msg_t m = {e->type, (int16_t)(a ? a->i : -1), (int16_t)(b ? b->i : -1)};
    xQueueSend(g_audio_q, &m, 0);            // full queue: the sound is skipped, the game never waits
}
void app_audio_test(int event_type) { st_event_t e = {0}; e.type = (uint8_t)event_type; app_audio_post(&e); }
int app_volume(void) { return g_volume; }
bool app_flip(void) { return app_load_i32("flip", 0) != 0; }
void app_set_flip(bool flip) {
    board_display_flip(flip);
    app_save_i32("flip", flip ? 1 : 0);
    ESP_LOGI(TAG, "screen %s", flip ? "turned 180" : "normal");
}
void app_set_volume(int level) {
    g_volume = ((level % APP_VOLUME_LEVELS) + APP_VOLUME_LEVELS) % APP_VOLUME_LEVELS;
    board_audio_volume(VOLUME_PERCENT[g_volume]);
    app_save_i32("volume", g_volume);
    ESP_LOGI(TAG, "volume %d/%d", g_volume, APP_VOLUME_LEVELS - 1);
}
bool app_audio_ok(void) { return g_audio_ok; }
bool app_music_ok(void) { return g_music_ok; }

// ---- power: model, brightness, idle dimming, auto-off, low battery ----------------------------------
// The backlight is the biggest load the firmware controls (docs/STRUTHIO_ONE_SLIM.md, run time), so it
// starts at 70 %, drops to a glow after 30 s with no button, and the toy switches itself off after 5 min
// with no button or below 3.30 V (never on USB). Wake it: SLIM, press the power button; ONE, slide the
// switch off and on.
static const uint8_t BRIGHT_PERCENT[APP_BRIGHT_LEVELS] = {30, 50, 70, 100};
static int g_bright = 2;
static bool g_one;                          // true: the 23 mm ONE (slide switch, 1000 mAh); false: ONE SLIM
static volatile uint32_t g_last_input_ms;
static volatile bool g_backlight_on;
enum { IDLE_DIM_MS = 30000, IDLE_OFF_MS = 5 * 60 * 1000, LOW_BATT_MV = 3300, LOW_BATT_SECONDS = 5, DIM_PERCENT = 8 };
int app_brightness(void) { return g_bright; }
void app_set_brightness(int level) {
    g_bright = ((level % APP_BRIGHT_LEVELS) + APP_BRIGHT_LEVELS) % APP_BRIGHT_LEVELS;
    if (g_backlight_on) board_backlight_fade(BRIGHT_PERCENT[g_bright], 150);
    app_save_i32("bright", g_bright);
    ESP_LOGI(TAG, "brightness %d %%", BRIGHT_PERCENT[g_bright]);
}
int app_brightness_percent(void) { return BRIGHT_PERCENT[g_bright]; }
bool app_is_one(void) { return g_one; }
static bool read_model_strap(void) {
    gpio_config_t cfg = { .pin_bit_mask = 1ULL << STRUTHIO_GPIO_MODEL_STRAP, .mode = GPIO_MODE_INPUT,
                          .pull_up_en = GPIO_PULLUP_ENABLE, .pull_down_en = GPIO_PULLDOWN_DISABLE, .intr_type = GPIO_INTR_DISABLE };
    gpio_config(&cfg);
    esp_rom_delay_us(50);
    int low = 0;
    for (int i = 0; i < 8; i++) { low += gpio_get_level((gpio_num_t)STRUTHIO_GPIO_MODEL_STRAP) == 0; esp_rom_delay_us(20); }
    gpio_set_pull_mode((gpio_num_t)STRUTHIO_GPIO_MODEL_STRAP, GPIO_FLOATING);   // a tied pin then draws nothing
    return low == 8;                         // all 8 reads low: the ONE's strap; anything else: SLIM (safe)
}
// the first picture is on the panel: light it (not before, so the panel's power-up noise never shows)
void app_backlight_on(void) {
    if (g_backlight_on) return;
    g_backlight_on = true;
    board_backlight_fade(BRIGHT_PERCENT[g_bright], 300);                 // the picture fades up
    ESP_LOGI(TAG, "first frame lit %lu ms after reset", (unsigned long)app_now_ms());
}
static void power_task(void *arg) {
    (void)arg;
    bool dim = false;
    int low = 0;
    for (uint32_t n = 1;; n++) {
        vTaskDelay(pdMS_TO_TICKS(100));
        if (!g_backlight_on) continue;
        uint32_t idle = app_now_ms() - g_last_input_ms;
        if (!dim && idle >= IDLE_DIM_MS) { dim = true; board_backlight_fade(DIM_PERCENT, 800); }          // a slow dim
        else if (dim && idle < IDLE_DIM_MS) { dim = false; board_backlight_fade(BRIGHT_PERCENT[g_bright], 120); }   // a quick wake
        if (n % 10) continue;                                  // the battery once a second
        board_power_t pw;
        if (!board_power_read(&pw) || pw.vbus_present) { low = 0; continue; }   // on USB: never switch off
        low = (pw.battery_present && pw.battery_mv > 0 && pw.battery_mv < LOW_BATT_MV) ? low + 1 : 0;
        if (idle >= IDLE_OFF_MS || low >= LOW_BATT_SECONDS) {
            ESP_LOGW(TAG, "switching off: %s", low ? "battery low" : "no button for 5 min");
            app_audio_test(ST_EV_RING);                                  // a goodbye chime, then the picture fades out
            board_backlight_fade(0, 400);
            vTaskDelay(pdMS_TO_TICKS(500));
            board_power_off();
        }
    }
}

// ---- input task: 1 kHz --------------------------------------------------------------------
static void input_task(void *arg) {
    (void)arg;
    for (;;) {
        bool l = app_pin_pressed(STRUTHIO_GPIO_LEFT_WING), r = app_pin_pressed(STRUTHIO_GPIO_RIGHT_WING);
        bool dl = app_pin_pressed(STRUTHIO_GPIO_DART_LEFT), dr = app_pin_pressed(STRUTHIO_GPIO_DART_RIGHT);
        uint32_t now = app_now_ms();
        if (l || r || dl || dr) g_last_input_ms = now;
        portENTER_CRITICAL(&g_input_mux);
        st_buttons_sample(&g_buttons, l, r, now);
        st_buttons_sample_rocker(&g_buttons, dl, dr, now);
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
        app_audio_post(e);
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
    // The handheld has no title screen: GAME OVER offers one thing, a new run on
    // both wings, so the menu shows the browser's single-item "BOTH WINGS CONTINUE".
    static const char *const ITEMS[1] = {"NEW RUN"};
    st_menu_t menu = {ITEMS, 1, 0, g_over};
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
        ESP_LOGI(TAG, "tick %llu sim %lu us (max %lu) scene %lu us render %lu us present %lu us missed %lu band-order %lu audio %lu us (max %lu) per 5333",
                 (unsigned long long)g_stats.ticks, (unsigned long)g_stats.sim_us_last, (unsigned long)g_stats.sim_us_max,
                 (unsigned long)g_stats.scene_us, (unsigned long)g_stats.render_us, (unsigned long)g_stats.present_us,
                 (unsigned long)g_stats.missed_deadlines, (unsigned long)board_display_order_errors(),
                 (unsigned long)g_stats.audio_us, (unsigned long)g_stats.audio_us_max);
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
        if (g_panel_ok) { render_panel_frame(); app_backlight_on(); log_stats(); continue; }
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
        app_backlight_on();
        log_stats();
    }
}

// ---- boot ---------------------------------------------------------------------------------
void app_main(void) {
    ESP_LOGI(TAG, "STRUTHIO handheld boot (core: STRUTHIO ARCADE 1.8.0 port)");
    init_wing_gpio();
    nvs_init_or_erase();
    st_dart_trial_t trial = (st_dart_trial_t)app_load_i32("dart", ST_DART_OFF);     // ROCKER ONLY: every ONE has the rocker
    if (trial > ST_DART_OFF) trial = ST_DART_OFF;
    g_high_score = app_load_i32("best", 0);
    st_norm_init(&g_norm);
    st_buttons_init(&g_buttons, &g_norm, trial, app_now_ms());
    g_bright = (int)app_load_i32("bright", 2);
    if (g_bright < 0 || g_bright >= APP_BRIGHT_LEVELS) g_bright = 2;
    g_one = read_model_strap();
    g_last_input_ms = app_now_ms();

    g_fb = heap_caps_malloc(ST_FB_W * ST_FB_H, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
    if (!g_fb) g_fb = heap_caps_malloc(ST_FB_W * ST_FB_H, MALLOC_CAP_SPIRAM);
    g_band = heap_caps_malloc(BOARD_LCD_W * BOARD_BAND_LINES * sizeof(uint16_t), MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    configASSERT(g_fb && g_band);

    board_power_init();
    board_power_model(g_one);
    ESP_LOGI(TAG, "model: %s", g_one ? "ONE (slide switch, 1000 mAh, 200 mA)" : "ONE SLIM (power button, 1000 mAh, 200 mA)");
    g_display_ok = board_display_init();
    if (g_display_ok && app_flip()) board_display_flip(true);

    // Hidden service mode: hold BOTH wings while powering on (650 ms within an 800 ms guard). The guard only
    // runs when a wing is already down, so a normal power-on does not wait for it.
    uint32_t guard = app_now_ms();
    bool wing_down = app_pin_pressed(STRUTHIO_GPIO_LEFT_WING) || app_pin_pressed(STRUTHIO_GPIO_RIGHT_WING);
    while (wing_down && (uint32_t)(app_now_ms() - guard) < 800) {
        st_buttons_sample(&g_buttons, app_pin_pressed(STRUTHIO_GPIO_LEFT_WING), app_pin_pressed(STRUTHIO_GPIO_RIGHT_WING), app_now_ms());
        if (st_buttons_service_requested(&g_buttons, app_now_ms())) {
            service_mode_run(&g_buttons, &g_norm);   // never returns
        }
        vTaskDelay(1);
    }
    if (!app_load_i32("tested", 0)) selftest_run(&g_buttons, &g_norm);   // first power-on: the guided check
    st_norm_init(&g_norm);                    // discard boot-guard presses
    st_buttons_init(&g_buttons, &g_norm, trial, app_now_ms());
    app_audio_start();
    g_panel_ok = g_display_ok && map_asset_pack();
    new_run();
    ESP_LOGI(TAG, "DART trial %s, best %ld, display %s, renderer %s", st_dart_trial_name(trial), (long)g_high_score,
             g_display_ok ? "ok" : "headless", g_panel_ok ? "panel (asset pack)" : "greybox");

    xTaskCreatePinnedToCore(input_task, "wings", 3072, NULL, 10, NULL, 0);
    xTaskCreatePinnedToCore(render_task, "render", 6144, NULL, 5, &g_render_task, 0);
    xTaskCreatePinnedToCore(game_task, "game", 12288, NULL, 9, NULL, 1);
    if (g_panel_ok) xTaskCreatePinnedToCore(render_helper_task, "render1", 6144, NULL, 4, &g_helper_task, 1);
    xTaskCreatePinnedToCore(power_task, "power", 3072, NULL, 3, NULL, 0);
}
