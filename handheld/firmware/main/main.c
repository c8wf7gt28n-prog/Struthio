/*
 * STRUTHIO ESP32-S3 Handheld - Prototype A0 firmware scaffold
 *
 * Purpose of this scaffold:
 *  - lock GPIO17/GPIO18 physical wing inputs
 *  - direct-to-game boot behavior
 *  - preserve 100 ms chord semantics
 *  - provide hold-to-DART A/B starting point
 *
 * Display/audio functions below are intentionally adapter stubs. Start from the
 * Waveshare ESP-IDF example for the exact board revision and replace these stubs
 * with that tested board-support code before integrating the STRUTHIO C core.
 */

#include <stdbool.h>
#include <stdint.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "board_pins.h"
#include "struthio_input.h"

static const char *TAG = "STRUTHIO_A0";
static struthio_input_mapper_t g_input;
static portMUX_TYPE g_input_mux = portMUX_INITIALIZER_UNLOCKED;

static uint32_t now_ms(void) { return (uint32_t)(esp_timer_get_time() / 1000ULL); }

static bool pin_pressed(gpio_num_t pin)
{
    return gpio_get_level(pin) == STRUTHIO_BUTTON_ACTIVE_LEVEL;
}

static void init_wing_gpio(void)
{
    gpio_config_t cfg = {
        .pin_bit_mask = (1ULL << STRUTHIO_GPIO_LEFT_WING) | (1ULL << STRUTHIO_GPIO_RIGHT_WING),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&cfg));
}

// ---- Board-adapter stubs. Replace with tested Waveshare BSP/example calls. ----
static void board_display_init(void) { ESP_LOGI(TAG, "TODO: initialize Waveshare AXS15231B QSPI display"); }
static void board_audio_init(void)   { ESP_LOGI(TAG, "TODO: initialize ES8311/NS4150B audio path"); }
static void board_show_service(void) { ESP_LOGW(TAG, "SERVICE MODE"); }
static void game_start_new_run(void) { ESP_LOGI(TAG, "NEW RUN: no menu, no touch required"); }
static void game_step_60hz(struthio_input_frame_t in)
{
    // Replace with the ported deterministic STRUTHIO simulation.
    if (in.flap_edge) ESP_LOGI(TAG, "flap=%d chord=%d", (int)in.flap_kind, (int)in.chord_edge);
    if (in.dart_edge) ESP_LOGI(TAG, "dart=%d", (int)in.dart_side);
}
static void game_render(void) { /* display adapter goes here */ }

static void input_task(void *arg)
{
    (void)arg;
    for (;;) {
        const uint32_t t = now_ms();
        portENTER_CRITICAL(&g_input_mux);
        struthio_input_sample(&g_input,
            pin_pressed((gpio_num_t)STRUTHIO_GPIO_LEFT_WING),
            pin_pressed((gpio_num_t)STRUTHIO_GPIO_RIGHT_WING),
            t, false);
        portEXIT_CRITICAL(&g_input_mux);
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "STRUTHIO Prototype A0 boot");
    init_wing_gpio();
    struthio_input_init(&g_input, now_ms());

    board_display_init();

    // Hidden service mode: hold BOTH buttons during boot for ~650 ms.
    const uint32_t guard_start = now_ms();
    while ((uint32_t)(now_ms() - guard_start) < 800) {
        const uint32_t t = now_ms();
        struthio_input_sample(&g_input,
            pin_pressed((gpio_num_t)STRUTHIO_GPIO_LEFT_WING),
            pin_pressed((gpio_num_t)STRUTHIO_GPIO_RIGHT_WING),
            t, true);
        if (struthio_input_service_mode_requested(&g_input)) {
            board_show_service();
            while (true) vTaskDelay(pdMS_TO_TICKS(1000));
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }

    board_audio_init();
    game_start_new_run();

    xTaskCreatePinnedToCore(input_task, "wing_input", 3072, NULL, 8, NULL, 0);

    // Fixed 60 Hz simulation. Use a rational microsecond schedule so the
    // 16,666 / 16,667 us cadence averages exactly 60 ticks per second.
    int64_t epoch_us = esp_timer_get_time();
    uint64_t tick_index = 0;
    int64_t next_tick = epoch_us;
    unsigned render_div = 0;
    for (;;) {
        const int64_t now = esp_timer_get_time();
        if (now >= next_tick) {
            struthio_input_frame_t frame;
            portENTER_CRITICAL(&g_input_mux);
            frame = struthio_input_consume_frame(&g_input);
            portEXIT_CRITICAL(&g_input_mux);

            game_step_60hz(frame);
            // A0 begins at 30 fps rendering: render every other simulation tick.
            if ((render_div++ & 1U) == 0) game_render();

            ++tick_index;
            next_tick = epoch_us + (int64_t)((tick_index * 1000000ULL) / 60ULL);

            // Recover from debugger stalls without running a giant catch-up burst.
            if (now - next_tick > 4 * (1000000LL / 60LL)) {
                epoch_us = now;
                tick_index = 1;
                next_tick = epoch_us + (1000000LL / 60LL);
            }
        } else {
            vTaskDelay(pdMS_TO_TICKS(1));
        }
    }
}
