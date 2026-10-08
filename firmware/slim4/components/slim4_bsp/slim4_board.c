#include "slim4_board.h"

#include <stdbool.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/i2s_std.h"
#include "driver/ledc.h"
#include "esp_err.h"
#include "esp_heap_caps.h"
#include "esp_ldo_regulator.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_mipi_dsi.h"
#include "esp_lcd_ili9881c.h"
#include "slim4_panel_cfaf.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "slim4_pins.h"
#include "slim4_power.h"

#define SLIM4_LCD_WIDTH  720
#define SLIM4_LCD_HEIGHT 1280
#define SLIM4_LCD_BPP    2
#define SLIM4_LCD_BYTES  (SLIM4_LCD_WIDTH * SLIM4_LCD_HEIGHT * SLIM4_LCD_BPP)
#define SLIM4_BL_DUTY_MAX ((1u << 12) - 1u)
#define SLIM4_AUDIO_CHUNK_FRAMES 256u
#define SLIM4_AUDIO_QUEUE_LENGTH 16u
#define SLIM4_AUDIO_MAX_QUEUED_FRAMES (SLIM4_AUDIO_CHUNK_FRAMES * SLIM4_AUDIO_QUEUE_LENGTH)

typedef struct {
    uint32_t sample_rate;
    uint16_t frames;
    int16_t samples[SLIM4_AUDIO_CHUNK_FRAMES * 2];
} slim4_audio_chunk_t;

static const char *TAG = "slim4_bsp";
static bool s_gpio_ready;
static bool s_nvs_ready;
static bool s_display_ready;
static bool s_i2s_ready;
static bool s_i2s_running;
static uint8_t s_audio_volume = 35;
static uint32_t s_i2s_sample_rate;
static uint16_t *s_framebuffer;
static int16_t s_audio_scaled[SLIM4_AUDIO_CHUNK_FRAMES * 2];
static slim4_audio_chunk_t s_audio_enqueue_chunk;
static QueueHandle_t s_audio_queue;
static SemaphoreHandle_t s_audio_enqueue_mutex;
static SemaphoreHandle_t s_dpi_transfer_done;
static TaskHandle_t s_audio_task;
static i2s_chan_handle_t s_i2s_tx;
static esp_lcd_dsi_bus_handle_t s_dsi_bus;
static esp_lcd_panel_io_handle_t s_dbi_io;
static esp_lcd_panel_handle_t s_panel;
static esp_ldo_channel_handle_t s_mipi_ldo;
static const char *s_display_stage = "not started";
static const char *AUDIO_TAG = "slim4_audio";
static uint32_t s_button_stable;
static uint32_t s_button_candidate;
static int64_t s_button_candidate_since_us;
static bool s_button_sampler_started;
static portMUX_TYPE s_vsync_lock = portMUX_INITIALIZER_UNLOCKED;
static uint32_t s_panel_vsync_count;

#define SLIM4_BUTTON_DEBOUNCE_US 5000

static uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b)
{
    return (uint16_t)(((r & 0xF8u) << 8) | ((g & 0xFCu) << 3) | (b >> 3));
}

static void fill_rect(int x, int y, int w, int h, uint16_t color)
{
    if (!s_framebuffer || w <= 0 || h <= 0) return;
    if (x < 0) { w += x; x = 0; }
    if (y < 0) { h += y; y = 0; }
    if (x + w > SLIM4_LCD_WIDTH) w = SLIM4_LCD_WIDTH - x;
    if (y + h > SLIM4_LCD_HEIGHT) h = SLIM4_LCD_HEIGHT - y;
    for (int row = y; row < y + h; ++row) {
        uint16_t *dst = s_framebuffer + row * SLIM4_LCD_WIDTH + x;
        for (int col = 0; col < w; ++col) dst[col] = color;
    }
}

/* Compact 5x7 uppercase font for the boot identity. */
static const uint8_t *glyph(char c)
{
    static const uint8_t blank[7] = {0};
    static const uint8_t A[7] = {14,17,17,31,17,17,17};
    static const uint8_t B[7] = {30,17,17,30,17,17,30};
    static const uint8_t C[7] = {14,17,16,16,16,17,14};
    static const uint8_t D[7] = {30,17,17,17,17,17,30};
    static const uint8_t E[7] = {31,16,16,30,16,16,31};
    static const uint8_t F[7] = {31,16,16,30,16,16,16};
    static const uint8_t G[7] = {14,17,16,23,17,17,15};
    static const uint8_t H[7] = {17,17,17,31,17,17,17};
    static const uint8_t I[7] = {14,4,4,4,4,4,14};
    static const uint8_t J[7] = {7,2,2,2,18,18,12};
    static const uint8_t K[7] = {17,18,20,24,20,18,17};
    static const uint8_t L[7] = {16,16,16,16,16,16,31};
    static const uint8_t M[7] = {17,27,21,21,17,17,17};
    static const uint8_t N[7] = {17,25,21,19,17,17,17};
    static const uint8_t O[7] = {14,17,17,17,17,17,14};
    static const uint8_t P[7] = {30,17,17,30,16,16,16};
    static const uint8_t Q[7] = {14,17,17,17,21,18,13};
    static const uint8_t R[7] = {30,17,17,30,20,18,17};
    static const uint8_t S[7] = {15,16,16,14,1,1,30};
    static const uint8_t T[7] = {31,4,4,4,4,4,4};
    static const uint8_t U[7] = {17,17,17,17,17,17,14};
    static const uint8_t V[7] = {17,17,17,17,17,10,4};
    static const uint8_t W[7] = {17,17,17,21,21,21,10};
    static const uint8_t X[7] = {17,17,10,4,10,17,17};
    static const uint8_t Y[7] = {17,17,10,4,4,4,4};
    static const uint8_t Z[7] = {31,1,2,4,8,16,31};
    static const uint8_t D0[7] = {14,17,19,21,25,17,14};
    static const uint8_t D1[7] = {4,12,4,4,4,4,14};
    static const uint8_t D2[7] = {14,17,1,2,4,8,31};
    static const uint8_t D3[7] = {30,1,1,14,1,1,30};
    static const uint8_t D4[7] = {2,6,10,18,31,2,2};
    static const uint8_t D5[7] = {31,16,16,30,1,1,30};
    static const uint8_t D6[7] = {14,16,16,30,17,17,14};
    static const uint8_t D7[7] = {31,1,2,4,8,8,8};
    static const uint8_t D8[7] = {14,17,17,14,17,17,14};
    static const uint8_t D9[7] = {14,17,17,15,1,1,14};
    static const uint8_t slash[7] = {1,2,2,4,8,8,16};
    static const uint8_t period[7] = {0,0,0,0,0,12,12};
    switch (c) {
    case 'A': return A; case 'B': return B; case 'C': return C; case 'D': return D;
    case 'E': return E; case 'F': return F; case 'G': return G; case 'H': return H;
    case 'I': return I; case 'J': return J; case 'K': return K; case 'L': return L;
    case 'M': return M; case 'N': return N; case 'O': return O; case 'P': return P;
    case 'Q': return Q; case 'R': return R; case 'S': return S; case 'T': return T;
    case 'U': return U; case 'V': return V; case 'W': return W; case 'X': return X;
    case 'Y': return Y; case 'Z': return Z; case '0': return D0; case '1': return D1;
    case '2': return D2; case '3': return D3; case '4': return D4; case '5': return D5;
    case '6': return D6; case '7': return D7; case '8': return D8; case '9': return D9;
    case '/': return slash; case '.': return period; case ' ': return blank; default: return blank;
    }
}

static void draw_text_centered(const char *text, int y, int scale, uint16_t color)
{
    if (!text || scale < 1) return;
    const size_t length = strlen(text);
    const int advance = 6 * scale;
    const int width = length ? (int)length * advance - scale : 0;
    int x = (SLIM4_LCD_WIDTH - width) / 2;
    for (size_t i = 0; i < length; ++i) {
        const uint8_t *rows = glyph(text[i]);
        for (int row = 0; row < 7; ++row) {
            for (int col = 0; col < 5; ++col) {
                if (rows[row] & (1u << (4 - col))) {
                    fill_rect(x + col * scale, y + row * scale, scale, scale, color);
                }
            }
        }
        x += advance;
    }
}

static void draw_text_at(const char *text, int x, int y, int scale, uint16_t color)
{
    if (!text || scale < 1) return;
    const int advance = 6 * scale;
    for (const char *p = text; *p; ++p) {
        const uint8_t *rows = glyph(*p);
        for (int row = 0; row < 7; ++row) {
            for (int col = 0; col < 5; ++col) {
                if (rows[row] & (1u << (4 - col))) {
                    fill_rect(x + col * scale, y + row * scale, scale, scale, color);
                }
            }
        }
        x += advance;
    }
}

static bool panel_vsync_callback(esp_lcd_panel_handle_t panel,
                                 esp_lcd_dpi_panel_event_data_t *event_data,
                                 void *user_context)
{
    (void)panel;
    (void)event_data;
    (void)user_context;
    portENTER_CRITICAL_ISR(&s_vsync_lock);
    ++s_panel_vsync_count;
    portEXIT_CRITICAL_ISR(&s_vsync_lock);
    return false;
}

static bool panel_color_trans_done_callback(esp_lcd_panel_handle_t panel,
                                            esp_lcd_dpi_panel_event_data_t *event_data,
                                            void *user_context)
{
    (void)panel;
    (void)event_data;
    BaseType_t higher_priority_task_woken = pdFALSE;
    if (user_context) {
        (void)xSemaphoreGiveFromISR((SemaphoreHandle_t)user_context,
                                    &higher_priority_task_woken);
    }
    return higher_priority_task_woken == pdTRUE;
}

static esp_err_t panel_draw_bitmap_wait(const void *pixels)
{
    if (!s_panel || !pixels || !s_dpi_transfer_done) return ESP_ERR_INVALID_STATE;
    while (xSemaphoreTake(s_dpi_transfer_done, 0) == pdTRUE) {}
    esp_err_t err = esp_lcd_panel_draw_bitmap(s_panel, 0, 0, SLIM4_LCD_WIDTH,
                                               SLIM4_LCD_HEIGHT, pixels);
    if (err != ESP_OK) return err;
    if (xSemaphoreTake(s_dpi_transfer_done, pdMS_TO_TICKS(100)) != pdTRUE) {
        return ESP_ERR_TIMEOUT;
    }
    return ESP_OK;
}

uint32_t slim4_board_get_vsync_count(void)
{
    uint32_t count;
    portENTER_CRITICAL(&s_vsync_lock);
    count = s_panel_vsync_count;
    portEXIT_CRITICAL(&s_vsync_lock);
    return count;
}

static void draw_button_indicator(int x, int y, const char *label, bool pressed,
                                  uint16_t active_color, uint16_t text_color,
                                  uint32_t press_count)
{
    const uint16_t tile = pressed ? active_color : rgb565(20, 34, 52);
    fill_rect(x, y, 190, 114, tile);
    fill_rect(x, y, 190, 3, active_color);
    fill_rect(x, y + 111, 190, 3, active_color);
    fill_rect(x, y, 3, 114, active_color);
    fill_rect(x + 187, y, 3, 114, active_color);
    const uint16_t label_color = pressed ? rgb565(7, 19, 34) : text_color;
    draw_text_at(label, x + (190 - (int)strlen(label) * 12) / 2, y + 34, 2, label_color);
    char count_text[16];
    (void)snprintf(count_text, sizeof(count_text), "COUNT %03lu", (unsigned long)(press_count % 1000u));
    draw_text_at(count_text, x + (190 - (int)strlen(count_text) * 6) / 2, y + 78, 1, label_color);
}

slim4_status_t slim4_board_render_diagnostic(uint32_t buttons, const uint32_t press_counts[4],
                                              uint32_t frame_index,
                                              uint32_t measured_fps, uint32_t measured_vsync_hz,
                                              uint32_t max_render_us,
                                              uint32_t late_frames, uint8_t color_phase)
{
    if (!s_display_ready || !s_framebuffer) return SLIM4_ERR_NOT_READY;
    if (!press_counts) return SLIM4_ERR_INVALID_ARG;

    static const uint16_t palette[] = {
        0x08A4, /* midnight blue */
        0x112A, /* indigo */
        0x024C, /* deep teal */
        0x8124, /* dark red */
        0x5028, /* violet */
    };
    const uint16_t background = palette[color_phase % (sizeof(palette) / sizeof(palette[0]))];
    const uint16_t ivory = rgb565(240, 244, 245);
    const uint16_t cyan = rgb565(45, 210, 230);
    const uint16_t gold = rgb565(255, 188, 57);
    const uint16_t orange = rgb565(255, 126, 28);
    const uint16_t red = rgb565(255, 72, 74);

    fill_rect(0, 0, SLIM4_LCD_WIDTH, SLIM4_LCD_HEIGHT, background);
    fill_rect(20, 20, SLIM4_LCD_WIDTH - 40, 4, cyan);
    fill_rect(20, SLIM4_LCD_HEIGHT - 24, SLIM4_LCD_WIDTH - 40, 4, cyan);
    fill_rect(20, 20, 4, SLIM4_LCD_HEIGHT - 40, cyan);
    fill_rect(SLIM4_LCD_WIDTH - 24, 20, 4, SLIM4_LCD_HEIGHT - 40, cyan);

    draw_text_centered("STRUTHIO / SLIM4", 90, 2, cyan);
    draw_text_centered("R23 HARDWARE TEST", 135, 4, ivory);
    draw_text_centered("PRESS EACH CONTROL / LISTEN", 205, 2, cyan);

    draw_button_indicator(110, 340, "FLAP LEFT", (buttons & (1u << 0)) != 0,
                          orange, ivory, press_counts[0]);
    draw_button_indicator(420, 340, "FLAP RIGHT", (buttons & (1u << 1)) != 0,
                          orange, ivory, press_counts[1]);
    draw_button_indicator(110, 510, "DART LEFT", (buttons & (1u << 2)) != 0,
                          gold, ivory, press_counts[2]);
    draw_button_indicator(420, 510, "DART RIGHT", (buttons & (1u << 3)) != 0,
                          gold, ivory, press_counts[3]);

    /* A moving bar makes panel updates visibly live even when no button is held. */
    const int sweep_x = 36 + (int)((frame_index * 11u) % (SLIM4_LCD_WIDTH - 72));
    fill_rect(sweep_x, 720, 12, 150, (frame_index & 1u) ? cyan : ivory);
    fill_rect(36, 710, SLIM4_LCD_WIDTH - 72, 2, cyan);
    fill_rect(36, 878, SLIM4_LCD_WIDTH - 72, 2, cyan);

    char line[32];
    slim4_power_state_t power;
    if (slim4_power_read(&power) == SLIM4_OK) {
        (void)snprintf(line, sizeof(line), "BAT %04u MV %03u PCT", power.battery_mv, power.battery_percent);
        draw_text_at(line, 56, 900, 3, power.battery_low ? red : (power.battery_percent < 15 ? orange : ivory));
        static const char *const usb_names[] = {"NONE", "500MA", "1.5A", "3A"};
        (void)snprintf(line, sizeof(line), "USB %s %s", power.usb_power ? usb_names[power.usb_current] : "OFF",
                       power.charge_suspended ? "HOT" : (power.charging ? "CHARGING" : ""));
        draw_text_at(line, 360, 1000, 2, power.charging ? cyan : ivory);
    }
    (void)snprintf(line, sizeof(line), "FPS %02lu", (unsigned long)measured_fps);
    const uint16_t frame_rate_color = measured_fps == 0 ? gold :
        (measured_fps >= 58 && measured_fps <= 62 ? cyan : red);
    draw_text_at(line, 56, 950, 3, frame_rate_color);
    (void)snprintf(line, sizeof(line), "VSYNC %02lu", (unsigned long)measured_vsync_hz);
    const uint16_t vsync_color = measured_vsync_hz == 0 ? gold :
        (measured_vsync_hz >= 58 && measured_vsync_hz <= 62 ? cyan : red);
    draw_text_at(line, 56, 1000, 3, vsync_color);
    (void)snprintf(line, sizeof(line), "FRAME %06lu", (unsigned long)frame_index);
    draw_text_at(line, 56, 1050, 3, ivory);
    (void)snprintf(line, sizeof(line), "RENDER US %05lu", (unsigned long)max_render_us);
    draw_text_at(line, 56, 1100, 3, ivory);
    (void)snprintf(line, sizeof(line), "LATE %04lu", (unsigned long)late_frames);
    draw_text_at(line, 56, 1150, 3, late_frames ? red : gold);
    draw_text_centered("R.A. PEDDYCOART", 1210, 2, ivory);

    const esp_err_t err = panel_draw_bitmap_wait(s_framebuffer);
    return err == ESP_OK ? SLIM4_OK : SLIM4_ERR_IO;
}

static void draw_boot_stamp(void)
{
    const uint16_t navy = rgb565(7, 19, 34);
    const uint16_t cyan = rgb565(45, 210, 230);
    const uint16_t gold = rgb565(255, 188, 57);
    const uint16_t ivory = rgb565(240, 244, 245);
    fill_rect(0, 0, SLIM4_LCD_WIDTH, SLIM4_LCD_HEIGHT, navy);
    fill_rect(24, 24, SLIM4_LCD_WIDTH - 48, 3, cyan);
    fill_rect(24, SLIM4_LCD_HEIGHT - 27, SLIM4_LCD_WIDTH - 48, 3, cyan);
    fill_rect(24, 24, 3, SLIM4_LCD_HEIGHT - 48, cyan);
    fill_rect(SLIM4_LCD_WIDTH - 27, 24, 3, SLIM4_LCD_HEIGHT - 48, cyan);
    draw_text_centered("STRUTHIO", 385, 9, gold);
    draw_text_centered("SLIM4 / R23", 515, 4, ivory);
    fill_rect(180, 590, SLIM4_LCD_WIDTH - 360, 2, cyan);
    draw_text_centered("SYSTEM BOOT", 640, 4, cyan);
    draw_text_centered("INITIALIZING", 705, 2, ivory);
    draw_text_centered("R.A. PEDDYCOART", 1130, 2, ivory);
    draw_text_centered("STARTING", 1190, 2, gold);
}

void slim4_board_show_boot_result(bool software_verified)
{
    if (!s_display_ready) return;
    fill_rect(24, 1110, SLIM4_LCD_WIDTH - 48, 140, rgb565(7, 19, 34));
    const uint16_t ivory = rgb565(240, 244, 245);
    const uint16_t result = software_verified ? rgb565(45, 210, 230) : rgb565(255, 188, 57);
    draw_text_centered("R.A. PEDDYCOART", 1130, 2, ivory);
    draw_text_centered(software_verified ? "VERIFIED" : "SERVICE MODE", 1190, 2, result);
    const esp_err_t err = panel_draw_bitmap_wait(s_framebuffer);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "boot-result stamp transfer failed: %s", esp_err_to_name(err));
    }
}

static esp_err_t init_backlight(void)
{
    const ledc_timer_config_t timer = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = LEDC_TIMER_12_BIT,
        .timer_num = LEDC_TIMER_0,
        .freq_hz = 20000,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    esp_err_t err = ledc_timer_config(&timer);
    if (err != ESP_OK) return err;
    const ledc_channel_config_t channel = {
        .gpio_num = SLIM4_GPIO_BACKLIGHT_PWM,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = LEDC_CHANNEL_0,
        .timer_sel = LEDC_TIMER_0,
        .duty = 0,
        .hpoint = 0,
        .flags.output_invert = 0,
    };
    return ledc_channel_config(&channel);
}

static esp_err_t init_audio(uint32_t sample_rate)
{
    i2s_chan_config_t channel_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER);
    channel_cfg.dma_desc_num = 6;
    channel_cfg.dma_frame_num = 256;
    esp_err_t err = i2s_new_channel(&channel_cfg, &s_i2s_tx, NULL);
    if (err != ESP_OK) return err;

    i2s_std_config_t std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(sample_rate),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = SLIM4_GPIO_I2S_BCLK,
            .ws = SLIM4_GPIO_I2S_LRCLK,
            .dout = SLIM4_GPIO_I2S_DOUT,
            .din = I2S_GPIO_UNUSED,
            .invert_flags = { .mclk_inv = false, .bclk_inv = false, .ws_inv = false },
        },
    };
    err = i2s_channel_init_std_mode(s_i2s_tx, &std_cfg);
    if (err != ESP_OK) {
        i2s_del_channel(s_i2s_tx);
        s_i2s_tx = NULL;
        return err;
    }
    s_i2s_sample_rate = sample_rate;
    s_i2s_ready = true;
    ESP_LOGI(AUDIO_TAG, "stereo I2S configured at %lu Hz; clocks remain stopped until audio is requested",
             (unsigned long)sample_rate);
    return ESP_OK;
}

static esp_err_t start_audio_clock(void)
{
    if (s_i2s_running) return gpio_set_level(SLIM4_GPIO_AUDIO_SD_CTRL, 1);
    esp_err_t err = gpio_set_level(SLIM4_GPIO_AUDIO_SD_CTRL, 1);
    if (err != ESP_OK) return err;
    /* Let both MAX98357A devices leave shutdown before BCLK/LRCLK start. */
    vTaskDelay(pdMS_TO_TICKS(1));
    err = i2s_channel_enable(s_i2s_tx);
    if (err != ESP_OK) {
        (void)gpio_set_level(SLIM4_GPIO_AUDIO_SD_CTRL, 0);
        return err;
    }
    s_i2s_running = true;
    return ESP_OK;
}

static void stop_audio_clock(void)
{
    (void)gpio_set_level(SLIM4_GPIO_AUDIO_SD_CTRL, 0);
    if (s_i2s_running) {
        if (i2s_channel_disable(s_i2s_tx) == ESP_OK) s_i2s_running = false;
    }
}

static esp_err_t configure_audio_rate(uint32_t sample_rate)
{
    if (!s_i2s_ready) return init_audio(sample_rate);
    if (sample_rate == s_i2s_sample_rate) return ESP_OK;

    stop_audio_clock();
    i2s_std_clk_config_t clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(sample_rate);
    esp_err_t err = i2s_channel_reconfig_std_clock(s_i2s_tx, &clk_cfg);
    if (err == ESP_OK) s_i2s_sample_rate = sample_rate;
    return err;
}

static void audio_worker(void *arg)
{
    (void)arg;
    for (;;) {
        const uint32_t notifications = ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(20));
        if (s_audio_volume == 0) {
            (void)xQueueReset(s_audio_queue);
            stop_audio_clock();
            continue;
        }

        bool processed_chunk = false;
        slim4_audio_chunk_t chunk;
        while (s_audio_volume != 0 && xQueueReceive(s_audio_queue, &chunk, 0) == pdTRUE) {
            processed_chunk = true;
            esp_err_t err = configure_audio_rate(chunk.sample_rate);
            if (err == ESP_OK) err = start_audio_clock();
            if (err != ESP_OK) {
                ESP_LOGE(AUDIO_TAG, "audio start failed: %s", esp_err_to_name(err));
                stop_audio_clock();
                continue;
            }

            const uint8_t volume = s_audio_volume;
            for (size_t i = 0; i < (size_t)chunk.frames * 2; ++i) {
                s_audio_scaled[i] = (int16_t)((int32_t)chunk.samples[i] * volume / 100);
            }
            size_t bytes_written = 0;
            const size_t bytes_to_write = (size_t)chunk.frames * 2 * sizeof(int16_t);
            err = i2s_channel_write(s_i2s_tx, s_audio_scaled, bytes_to_write,
                                    &bytes_written, pdMS_TO_TICKS(1000));
            if (err != ESP_OK || bytes_written != bytes_to_write) {
                ESP_LOGE(AUDIO_TAG, "I2S write failed: %s (%u/%u bytes)", esp_err_to_name(err),
                         (unsigned)bytes_written, (unsigned)bytes_to_write);
                stop_audio_clock();
            }
        }
        if (!processed_chunk && notifications == 0) stop_audio_clock();
    }
}

static esp_err_t set_backlight(uint32_t percent)
{
    if (percent > 100) percent = 100;
    uint32_t duty = (SLIM4_BL_DUTY_MAX * percent) / 100;
    esp_err_t err = ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, duty);
    if (err != ESP_OK) return err;
    return ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
}

static esp_err_t init_display(void)
{
    esp_err_t err;
    s_display_stage = "MIPI D-PHY 2.5 V rail";
    const esp_ldo_channel_config_t ldo_cfg = {
        .chan_id = 3, /* LDO_VO3 supplies the P4 MIPI D-PHY rail on this design */
        .voltage_mv = 2500,
        .voltage_stable_delay_us = 500,
    };
    err = esp_ldo_acquire_channel(&ldo_cfg, &s_mipi_ldo);
    if (err != ESP_OK) return err;

    s_display_stage = "LCD reset gate";
    gpio_config_t reset_gate = {
        .pin_bit_mask = 1ULL << SLIM4_GPIO_LCD_RESET_GATE,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    err = gpio_config(&reset_gate);
    if (err != ESP_OK) return err;
    /* Q1 inverts this gate: high asserts LCD_RESX low, low releases reset. */
    err = gpio_set_level(SLIM4_GPIO_LCD_RESET_GATE, 1);
    if (err != ESP_OK) return err;
    vTaskDelay(pdMS_TO_TICKS(10));

    s_display_stage = "backlight PWM";
    err = init_backlight();
    if (err != ESP_OK) return err;

    s_display_stage = "two-lane DSI bus";
    esp_lcd_dsi_bus_config_t bus_cfg = ILI9881C_PANEL_BUS_DSI_2CH_CONFIG();
    bus_cfg.lane_bit_rate_mbps = SLIM4_PANEL_LANE_MBPS;
    err = esp_lcd_new_dsi_bus(&bus_cfg, &s_dsi_bus);
    if (err != ESP_OK) return err;

    s_display_stage = "DBI command channel";
    esp_lcd_dbi_io_config_t dbi_cfg = ILI9881C_PANEL_IO_DBI_CONFIG();
    err = esp_lcd_new_panel_io_dbi(s_dsi_bus, &dbi_cfg, &s_dbi_io);
    if (err != ESP_OK) return err;

    s_display_stage = "ILI9881C panel driver (Crystalfontz CFAF7201280A0-050TN)";
    const esp_lcd_dpi_panel_config_t dpi_cfg = SLIM4_PANEL_DPI_CONFIG(LCD_COLOR_FMT_RGB565);
    uint16_t init_count = 0;
    const ili9881c_lcd_init_cmd_t *init_cmds = slim4_panel_cfaf_init(&init_count);
    ili9881c_vendor_config_t vendor_cfg = {
        .init_cmds = init_cmds,
        .init_cmds_size = init_count,
        .mipi_config = {
            .dsi_bus = s_dsi_bus,
            .dpi_config = &dpi_cfg,
            .lane_num = SLIM4_PANEL_DSI_LANES,
        },
    };
    const esp_lcd_panel_dev_config_t panel_cfg = {
        .reset_gpio_num = -1, /* Reset is controlled through the Q1 gate. */
        .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_RGB,
        .bits_per_pixel = 16,
        .vendor_config = &vendor_cfg,
    };
    err = esp_lcd_new_panel_ili9881c(s_dbi_io, &panel_cfg, &s_panel);
    if (err != ESP_OK) return err;

    s_dpi_transfer_done = xSemaphoreCreateBinary();
    if (!s_dpi_transfer_done) return ESP_ERR_NO_MEM;

    s_display_stage = "DPI VSYNC monitor";
    const esp_lcd_dpi_panel_event_callbacks_t dpi_callbacks = {
        .on_color_trans_done = panel_color_trans_done_callback,
        .on_vsync = panel_vsync_callback,
    };
    err = esp_lcd_dpi_panel_register_event_callbacks(s_panel, &dpi_callbacks,
                                                      s_dpi_transfer_done);
    if (err != ESP_OK) return err;

    s_display_stage = "DMA2D framebuffer copy path";
    err = esp_lcd_dpi_panel_enable_dma2d(s_panel);
    if (err != ESP_OK) return err;

    s_display_stage = "panel reset release";
    err = gpio_set_level(SLIM4_GPIO_LCD_RESET_GATE, 0);
    if (err != ESP_OK) return err;
    vTaskDelay(pdMS_TO_TICKS(120));
    s_display_stage = "panel initialization commands";
    err = esp_lcd_panel_init(s_panel);
    if (err != ESP_OK) return err;
    s_display_stage = "panel display-on command";
    err = esp_lcd_panel_disp_on_off(s_panel, true);
    if (err != ESP_OK) return err;

    s_display_stage = "PSRAM framebuffer allocation";
    s_framebuffer = heap_caps_malloc(SLIM4_LCD_BYTES, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!s_framebuffer) return ESP_ERR_NO_MEM;
    draw_boot_stamp();
    s_display_stage = "boot stamp transfer";
    err = panel_draw_bitmap_wait(s_framebuffer);
    if (err != ESP_OK) return err;
    s_display_stage = "backlight enable";
    err = set_backlight(45);
    if (err != ESP_OK) return err;

    s_display_ready = true;
    ESP_LOGI(TAG, "ILI9881C two-lane DSI initialized: 720x1280 RGB565, 78 MHz pixel clock (59 Hz)");
    ESP_LOGI(TAG, "STRUTHIO SLIM4 boot stamp sent to panel");
    return ESP_OK;
}

void slim4_board_prepare_power_off(void)
{
    stop_audio_clock();
    if (s_display_ready) {
        (void)set_backlight(0);
        (void)esp_lcd_panel_disp_on_off(s_panel, false);
    }
    /* Hold the panel in reset; in deep sleep the board's pull-ups and pull-downs keep the panel in reset,
     * the backlight off and the amplifiers shut down. */
    (void)gpio_set_level(SLIM4_GPIO_LCD_RESET_GATE, 1);
}

slim4_status_t slim4_board_init(void)
{
    s_button_stable = 0;
    s_button_candidate = 0;
    s_button_candidate_since_us = 0;
    s_button_sampler_started = false;
    esp_err_t err = nvs_flash_init();
    if (err == ESP_OK) {
        s_nvs_ready = true;
        ESP_LOGI(TAG, "save storage: NVS initialized");
    } else {
        ESP_LOGW(TAG, "NVS unavailable (%s); continuing without save storage", esp_err_to_name(err));
    }

    const gpio_config_t buttons = {
        .pin_bit_mask = (1ULL << SLIM4_GPIO_BTN_LEFT) |
                        (1ULL << SLIM4_GPIO_BTN_RIGHT) |
                        (1ULL << SLIM4_GPIO_DART_LEFT) |
                        (1ULL << SLIM4_GPIO_DART_RIGHT),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE, /* the board provides external 10 kΩ pull-ups */
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    err = gpio_config(&buttons);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "button GPIO config: %s", esp_err_to_name(err));
        return SLIM4_ERR_IO;
    }

    const gpio_config_t audio_enable = {
        .pin_bit_mask = 1ULL << SLIM4_GPIO_AUDIO_SD_CTRL,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    err = gpio_config(&audio_enable);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "audio shutdown GPIO config: %s", esp_err_to_name(err));
        return SLIM4_ERR_IO;
    }
    err = gpio_set_level(SLIM4_GPIO_AUDIO_SD_CTRL, 0);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "audio shutdown level: %s", esp_err_to_name(err));
        return SLIM4_ERR_IO;
    }
    s_audio_queue = xQueueCreate(SLIM4_AUDIO_QUEUE_LENGTH, sizeof(slim4_audio_chunk_t));
    s_audio_enqueue_mutex = xSemaphoreCreateMutex();
    if (!s_audio_queue || !s_audio_enqueue_mutex ||
        xTaskCreate(audio_worker, "slim4_audio", 4096, NULL, 5, &s_audio_task) != pdPASS) {
        if (s_audio_queue) vQueueDelete(s_audio_queue);
        if (s_audio_enqueue_mutex) vSemaphoreDelete(s_audio_enqueue_mutex);
        s_audio_queue = NULL;
        s_audio_enqueue_mutex = NULL;
        s_audio_task = NULL;
        ESP_LOGW(TAG, "audio worker unavailable; PCM API will report not-ready");
    }
    if (slim4_power_init() != SLIM4_OK) {
        ESP_LOGW(TAG, "power service unavailable: no battery readings or power button");
    }
    s_gpio_ready = true;
    ESP_LOGI(TAG, "gameplay inputs ready on GPIO1..GPIO4 (active low)");

    err = init_display();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "display failed at %s: %s; continuing with serial diagnostics",
                 s_display_stage, esp_err_to_name(err));
        return SLIM4_OK;
    }
    return SLIM4_OK;
}

slim4_status_t slim4_board_read_buttons(uint32_t *buttons)
{
    if (!buttons) return SLIM4_ERR_INVALID_ARG;
    if (!s_gpio_ready) return SLIM4_ERR_NOT_READY;
    uint32_t raw = 0;
    if (gpio_get_level(SLIM4_GPIO_BTN_LEFT) == 0) raw |= 1u << 0;
    if (gpio_get_level(SLIM4_GPIO_BTN_RIGHT) == 0) raw |= 1u << 1;
    if (gpio_get_level(SLIM4_GPIO_DART_LEFT) == 0) raw |= 1u << 2;
    if (gpio_get_level(SLIM4_GPIO_DART_RIGHT) == 0) raw |= 1u << 3;
    const int64_t now_us = esp_timer_get_time();
    if (!s_button_sampler_started) {
        s_button_candidate = raw;
        s_button_candidate_since_us = now_us;
        s_button_sampler_started = true;
    } else if (raw != s_button_candidate) {
        s_button_candidate = raw;
        s_button_candidate_since_us = now_us;
    } else if (raw != s_button_stable &&
               now_us - s_button_candidate_since_us >= SLIM4_BUTTON_DEBOUNCE_US) {
        s_button_stable = raw;
    }
    *buttons = s_button_stable;
    return SLIM4_OK;
}

slim4_status_t slim4_board_display_acquire(slim4_surface_t *out)
{
    if (!out) return SLIM4_ERR_INVALID_ARG;
    if (!s_display_ready) return SLIM4_ERR_NOT_READY;
    *out = (slim4_surface_t){
        .width = SLIM4_LCD_WIDTH,
        .height = SLIM4_LCD_HEIGHT,
        .stride_bytes = SLIM4_LCD_WIDTH * SLIM4_LCD_BPP,
        .pixels_rgb565 = s_framebuffer,
    };
    return SLIM4_OK;
}

slim4_status_t slim4_board_display_present(const slim4_surface_t *surface)
{
    if (!surface || !surface->pixels_rgb565) return SLIM4_ERR_INVALID_ARG;
    if (!s_display_ready || surface->pixels_rgb565 != s_framebuffer) return SLIM4_ERR_NOT_READY;
    esp_err_t err = panel_draw_bitmap_wait(s_framebuffer);
    return err == ESP_OK ? SLIM4_OK : SLIM4_ERR_IO;
}

slim4_status_t slim4_board_audio_set_volume(uint8_t volume)
{
    if (volume > 100) return SLIM4_ERR_INVALID_ARG;
    if (!s_audio_queue || !s_audio_task || !s_audio_enqueue_mutex) return SLIM4_ERR_NOT_READY;
    s_audio_volume = volume;
    if (volume == 0) {
        if (xSemaphoreTake(s_audio_enqueue_mutex, portMAX_DELAY) != pdTRUE) return SLIM4_ERR_IO;
        (void)xQueueReset(s_audio_queue);
        xSemaphoreGive(s_audio_enqueue_mutex);
        xTaskNotifyGive(s_audio_task);
    }
    return SLIM4_OK;
}

slim4_status_t slim4_board_audio_write(const int16_t *stereo, size_t frames, uint32_t rate)
{
    if ((!stereo && frames) || rate < 8000 || rate > 96000) return SLIM4_ERR_INVALID_ARG;
    if (frames == 0) return SLIM4_OK;
    if (!s_audio_queue || !s_audio_task || !s_audio_enqueue_mutex) return SLIM4_ERR_NOT_READY;
    if (frames > SLIM4_AUDIO_MAX_QUEUED_FRAMES) return SLIM4_ERR_INVALID_ARG;
    const size_t chunks = (frames + SLIM4_AUDIO_CHUNK_FRAMES - 1) / SLIM4_AUDIO_CHUNK_FRAMES;
    if (xSemaphoreTake(s_audio_enqueue_mutex, portMAX_DELAY) != pdTRUE) return SLIM4_ERR_IO;
    if (uxQueueSpacesAvailable(s_audio_queue) < chunks) {
        xSemaphoreGive(s_audio_enqueue_mutex);
        return SLIM4_ERR_NOT_READY;
    }

    size_t offset = 0;
    while (offset < frames) {
        size_t count = frames - offset;
        if (count > SLIM4_AUDIO_CHUNK_FRAMES) count = SLIM4_AUDIO_CHUNK_FRAMES;
        s_audio_enqueue_chunk.sample_rate = rate;
        s_audio_enqueue_chunk.frames = (uint16_t)count;
        memcpy(s_audio_enqueue_chunk.samples, stereo + offset * 2, count * 2 * sizeof(int16_t));
        if (xQueueSend(s_audio_queue, &s_audio_enqueue_chunk, 0) != pdTRUE) {
            xSemaphoreGive(s_audio_enqueue_mutex);
            return SLIM4_ERR_IO;
        }
        offset += count;
    }
    xSemaphoreGive(s_audio_enqueue_mutex);
    xTaskNotifyGive(s_audio_task);
    return SLIM4_OK;
}

slim4_status_t slim4_board_save_read(const char *name_space, const char *key, void *dst, size_t *len)
{
    if (!name_space || !key || !len) return SLIM4_ERR_INVALID_ARG;
    if (!s_nvs_ready) return SLIM4_ERR_NOT_READY;
    nvs_handle_t handle;
    if (nvs_open(name_space, NVS_READONLY, &handle) != ESP_OK) return SLIM4_ERR_IO;
    esp_err_t err = nvs_get_blob(handle, key, dst, len);
    nvs_close(handle);
    return err == ESP_OK ? SLIM4_OK : SLIM4_ERR_IO;
}

slim4_status_t slim4_board_save_write(const char *name_space, const char *key, const void *src, size_t len)
{
    if (!name_space || !key || (!src && len)) return SLIM4_ERR_INVALID_ARG;
    if (!s_nvs_ready) return SLIM4_ERR_NOT_READY;
    nvs_handle_t handle;
    if (nvs_open(name_space, NVS_READWRITE, &handle) != ESP_OK) return SLIM4_ERR_IO;
    esp_err_t err = nvs_set_blob(handle, key, src, len);
    if (err == ESP_OK) err = nvs_commit(handle);
    nvs_close(handle);
    return err == ESP_OK ? SLIM4_OK : SLIM4_ERR_IO;
}
