#include <stdbool.h>
#include <stdint.h>
#include "esp_app_desc.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include "esp_timer.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "slim4_board.h"
#include "slim4_console.h"
#include "slim4_pins.h"
#include "slim4_power.h"
#include "slim4_selftest.h"
#include "slim4_game_api.h"

static const char *TAG = "slim4";
static TaskHandle_t s_diagnostic_task;
static slim4_st_report_t s_selftest;

#define SLIM4_SELFTEST_PAGE_US 10000000   /* the self-test page stays up 10 s, or until a control is pressed */

#define SLIM4_DIAGNOSTIC_PERIOD_US 16667
#define SLIM4_DIAGNOSTIC_TONE_FRAMES 2400u

static void diagnostic_frame_tick(void *arg)
{
    (void)arg;
    if (s_diagnostic_task) xTaskNotifyGive(s_diagnostic_task);
}

static int16_t triangle_tone_sample(uint32_t sample_index, uint32_t frequency_hz,
                                    int32_t fade_percent)
{
    const uint32_t phase = (uint32_t)((uint64_t)sample_index * frequency_hz % 48000u);
    const int32_t triangle = phase < 24000u
        ? -16000 + (int32_t)(32000u * phase / 24000u)
        : 16000 - (int32_t)(32000u * (phase - 24000u) / 24000u);
    return (int16_t)(triangle * fade_percent / 100);
}

static void queue_button_tone(uint32_t pressed)
{
    static int16_t samples[SLIM4_DIAGNOSTIC_TONE_FRAMES * 2];
    const bool left = (pressed & ((1u << 0) | (1u << 2))) != 0;
    const bool right = (pressed & ((1u << 1) | (1u << 3))) != 0;
    if (!left && !right) return;

    const uint32_t left_hz = (pressed & (1u << 2)) ? 660u : 880u;
    const uint32_t right_hz = (pressed & (1u << 3)) ? 660u : 880u;
    for (uint32_t i = 0; i < SLIM4_DIAGNOSTIC_TONE_FRAMES; ++i) {
        const int32_t fade = (i < 120u) ? (int32_t)i * 100 / 120 :
                             (i > SLIM4_DIAGNOSTIC_TONE_FRAMES - 120u)
                                 ? (int32_t)(SLIM4_DIAGNOSTIC_TONE_FRAMES - i) * 100 / 120
                                 : 100;
        const int16_t left_sample = left ? triangle_tone_sample(i, left_hz, fade) : 0;
        const int16_t right_sample = right ? triangle_tone_sample(i, right_hz, fade) : 0;
        samples[i * 2] = left_sample;
        samples[i * 2 + 1] = right_sample;
    }
    const slim4_status_t status = slim4_audio_play_pcm_s16(
        samples, SLIM4_DIAGNOSTIC_TONE_FRAMES, 48000);
    if (status != SLIM4_OK) {
        ESP_LOGW(TAG, "speaker check tone could not queue: %d", (int)status);
    } else {
        ESP_LOGI(TAG, "speaker test tone queued: %s%s", left ? "LEFT " : "",
                 right ? "RIGHT" : "");
    }
}

static bool platform_self_test(bool *display_ready)
{
    if (display_ready) *display_ready = false;
    slim4_input_state_t input = {0};
    slim4_surface_t surface = {0};
    const slim4_status_t input_status = slim4_input_read(&input);
    const slim4_status_t display_status = slim4_display_acquire(&surface);
    const bool valid_surface = display_status == SLIM4_OK && surface.width == 720 &&
                               surface.height == 1280 && surface.pixels_rgb565 != NULL;
    if (display_ready) *display_ready = valid_surface;
    return input_status == SLIM4_OK && valid_surface;
}

static bool boot_button_down(void)
{
    return gpio_get_level(SLIM4_GPIO_BOOT_BTN) == 0;
}

/* Shows the self-test page until a control is pressed or the time runs out. The page's own check is visual: the
 * colour bars and 1-pixel lines exercise the CLK and D1 lanes, which carry video only. */
static void show_selftest_page(void)
{
    if (slim4_board_show_selftest(&s_selftest) != SLIM4_OK) return;
    ESP_LOGI(TAG, "self-test page shown: any control continues, the BOOT button shows it again later");
    const uint64_t until = slim4_time_us() + SLIM4_SELFTEST_PAGE_US;
    uint32_t buttons = 0;
    /* Let go first (BOOT may still be down when the page is reopened), then wait for a new press. */
    while (slim4_time_us() < until && boot_button_down()) vTaskDelay(pdMS_TO_TICKS(10));
    while (slim4_time_us() < until) {
        if (boot_button_down()) break;
        if (slim4_board_read_buttons(&buttons) == SLIM4_OK && buttons) break;
        slim4_platform_pump();
        vTaskDelay(pdMS_TO_TICKS(10));
    }
    /* Wait for the release so the press does not also count on the diagnostic screen. */
    while (slim4_time_us() < until + 2000000u &&
           (boot_button_down() || (slim4_board_read_buttons(&buttons) == SLIM4_OK && buttons))) {
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

static void finish_ota_boot_check(bool platform_init_ok)
{
    const esp_partition_t *running = esp_ota_get_running_partition();
    if (!running) return;
    esp_ota_img_states_t state;
    const esp_err_t state_err = esp_ota_get_state_partition(running, &state);
    if (state_err != ESP_OK || state != ESP_OTA_IMG_PENDING_VERIFY) return;
    if (!platform_init_ok) {
        ESP_LOGE(TAG, "OTA platform self-test failed; reverting to the previous image");
        const esp_err_t rollback_err = esp_ota_mark_app_invalid_rollback_and_reboot();
        ESP_LOGE(TAG, "OTA rollback request returned: %s", esp_err_to_name(rollback_err));
        return;
    }
    const esp_err_t err = esp_ota_mark_app_valid_cancel_rollback();
    if (err == ESP_OK) ESP_LOGI(TAG, "OTA image passed platform boot checks; rollback canceled");
    else ESP_LOGE(TAG, "could not confirm OTA image: %s", esp_err_to_name(err));
}

void app_main(void)
{
    const esp_app_desc_t *app = esp_app_get_description();
    ESP_LOGI(TAG, "STRUTHIO SLIM4 platform boot");
    ESP_LOGI(TAG, "firmware=%s version=%s", app->project_name, app->version);
    ESP_LOGI(TAG, "target=ESP32-P4 board=SLIM4 PCB R26 api=%u.%u", SLIM4_API_VERSION_MAJOR,
             SLIM4_API_VERSION_MINOR);
    ESP_LOGI(TAG, "bring-up: ILI9881C 720x1280 two-lane display (Crystalfontz CFAF7201280A0-050TN); four active-low controls; %s",
             slim4_power_woke_by_button() ? "woken by the power button" : "cold start");

    /* Hardware self-test, part 1: the GPIO nets, before any driver claims them. */
    slim4_st_report_init(&s_selftest);
    slim4_selftest_pins(&s_selftest);

    slim4_status_t status = slim4_platform_init();
    if (status != SLIM4_OK) {
        ESP_LOGE(TAG, "platform init failed: %d", (int)status);
        slim4_selftest_log(&s_selftest);
        finish_ota_boot_check(false);
        return;
    }
    bool display_ready = false;
    const bool io_verified = platform_self_test(&display_ready);
    /* Part 2: chip, memory, reset, the panel probe, video, power. */
    slim4_selftest_after_init(&s_selftest, display_ready);
    slim4_selftest_log(&s_selftest);
    const slim4_status_t volume_status = slim4_audio_set_master_volume(20);
    const bool software_verified = io_verified && volume_status == SLIM4_OK;
    if (display_ready) {
        slim4_board_show_boot_result(software_verified);
        show_selftest_page();
    }
    if (software_verified) {
        ESP_LOGI(TAG, "SYSTEM READY: controls, RGB565 surface, and audio worker passed software checks");
    } else {
        ESP_LOGW(TAG, "SERVICE MODE: controls, display, or audio service check incomplete; serial diagnostics remain active");
    }
    finish_ota_boot_check(software_verified);
    ESP_LOGI(TAG, "diagnostic mode: 60 Hz display sweep, four live controls, and per-channel speaker tones");
    if (volume_status == SLIM4_OK) {
        ESP_LOGI(TAG, "speaker test tones capped at 20%% digital volume");
    } else {
        ESP_LOGW(TAG, "speaker test unavailable: audio service status %d", (int)volume_status);
    }
    slim4_console_start();
    bool boot_was_down = false;
    uint32_t previous_buttons = 0;
    uint32_t press_counts[4] = {0};
    uint32_t frame_index = 0;
    uint32_t frames_in_window = 0;
    uint32_t measured_fps = 0;
    uint32_t measured_vsync_hz = 0;
    uint32_t last_vsync_count = slim4_board_get_vsync_count();
    uint32_t max_render_us = 0;
    uint32_t late_frames = 0;
    uint8_t color_phase = 0;
    uint64_t stats_window_start_us = slim4_time_us();
    uint64_t fallback_next_frame_us = stats_window_start_us;

    s_diagnostic_task = xTaskGetCurrentTaskHandle();
    esp_timer_handle_t frame_timer = NULL;
    const esp_timer_create_args_t timer_args = {
        .callback = diagnostic_frame_tick,
        .name = "slim4_diag_frame",
        .dispatch_method = ESP_TIMER_TASK,
    };
    esp_err_t timer_err = ESP_OK;
    if (display_ready) {
        timer_err = esp_timer_create(&timer_args, &frame_timer);
        if (timer_err == ESP_OK) {
            timer_err = esp_timer_start_periodic(frame_timer, SLIM4_DIAGNOSTIC_PERIOD_US);
        }
    }
    if (timer_err != ESP_OK) {
        ESP_LOGE(TAG, "60 Hz diagnostic timer unavailable: %s", esp_err_to_name(timer_err));
        if (frame_timer) (void)esp_timer_delete(frame_timer);
        frame_timer = NULL;
    }
    bool diagnostic_render_failed = false;

    for (;;) {
        uint32_t buttons = 0;
        if (slim4_board_read_buttons(&buttons) == SLIM4_OK && buttons != previous_buttons) {
            ESP_LOGI(TAG, "buttons changed: left=%u right=%u dart_left=%u dart_right=%u",
                     (unsigned)((buttons >> 0) & 1u), (unsigned)((buttons >> 1) & 1u),
                     (unsigned)((buttons >> 2) & 1u), (unsigned)((buttons >> 3) & 1u));
            const uint32_t pressed = buttons & ~previous_buttons;
            if (pressed) {
                ++color_phase;
                for (uint32_t bit = 0; bit < 4; ++bit) {
                    if (pressed & (1u << bit)) ++press_counts[bit];
                }
                queue_button_tone(pressed);
            }
            previous_buttons = buttons;
        }
        const bool boot_down = boot_button_down();
        if (boot_down && !boot_was_down && display_ready && !slim4_console_display_hold()) {
            show_selftest_page();
            (void)slim4_board_read_buttons(&previous_buttons);
            (void)ulTaskNotifyTake(pdTRUE, 0);   /* frame ticks queued while the page was up are not late frames */
        }
        boot_was_down = boot_down;
        slim4_platform_pump();
        if (slim4_power_poll()) {
            if (frame_timer) {
                (void)esp_timer_stop(frame_timer);
                (void)esp_timer_delete(frame_timer);
                frame_timer = NULL;
            }
            slim4_power_off();
        }

        const uint32_t frame_notifications = ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(1));
        const uint64_t now_before_render_us = slim4_time_us();
        const bool fallback_frame_due = display_ready && !frame_timer &&
                                        now_before_render_us >= fallback_next_frame_us;
        if (display_ready && slim4_console_display_hold()) {
            /* a console command holds the screen (test pattern or self-test page): draw nothing */
        } else if (display_ready && (frame_notifications > 0 || fallback_frame_due)) {
            const uint64_t render_start_us = slim4_time_us();
            const slim4_status_t render_status = slim4_board_render_diagnostic(
                previous_buttons, press_counts, frame_index, measured_fps, measured_vsync_hz,
                max_render_us,
                late_frames, color_phase);
            const uint64_t render_duration_us = slim4_time_us() - render_start_us;
            if (render_duration_us > max_render_us) {
                max_render_us = render_duration_us > UINT32_MAX ? UINT32_MAX : (uint32_t)render_duration_us;
            }
            if (render_duration_us > SLIM4_DIAGNOSTIC_PERIOD_US || frame_notifications > 1) ++late_frames;
            if (render_status != SLIM4_OK && !diagnostic_render_failed) {
                ESP_LOGE(TAG, "diagnostic display update failed: %d", (int)render_status);
                diagnostic_render_failed = true;
                display_ready = false;
                if (frame_timer) {
                    (void)esp_timer_stop(frame_timer);
                    (void)esp_timer_delete(frame_timer);
                    frame_timer = NULL;
                }
            }
            ++frame_index;
            if (render_status == SLIM4_OK) ++frames_in_window;
            if (!frame_timer) fallback_next_frame_us = render_start_us + SLIM4_DIAGNOSTIC_PERIOD_US;

            const uint64_t now_us = slim4_time_us();
            const uint64_t window_us = now_us - stats_window_start_us;
            if (window_us >= 1000000u) {
                measured_fps = (uint32_t)((uint64_t)frames_in_window * 1000000u / window_us);
                const uint32_t vsync_count = slim4_board_get_vsync_count();
                measured_vsync_hz = (uint32_t)((uint64_t)(vsync_count - last_vsync_count) *
                                               1000000u / window_us);
                last_vsync_count = vsync_count;
                ESP_LOGI(TAG, "diagnostic frames=%lu draw_fps=%lu panel_vsync_hz=%lu max_render_submit_us=%lu late=%lu",
                         (unsigned long)frame_index, (unsigned long)measured_fps,
                         (unsigned long)measured_vsync_hz,
                         (unsigned long)max_render_us, (unsigned long)late_frames);
                frames_in_window = 0;
                max_render_us = 0;
                stats_window_start_us = now_us;
            }
        }
    }
}
