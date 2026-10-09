#include "slim4_board.h"

#include <ctype.h>
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
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "hal/mipi_dsi_host_ll.h"
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
#include "slim4_selftest.h"

#define SLIM4_LCD_WIDTH  720
#define SLIM4_LCD_HEIGHT 1280
#define SLIM4_LCD_BPP    2
#define SLIM4_LCD_BYTES  (SLIM4_LCD_WIDTH * SLIM4_LCD_HEIGHT * SLIM4_LCD_BPP)
#define SLIM4_BL_FREQ_HZ 20000u
#define SLIM4_BL_RES_BITS 11u
#define SLIM4_BL_DUTY_MAX ((1u << SLIM4_BL_RES_BITS) - 1u)
/* LEDC's divider is 80 MHz x 256 / (freq x 2^bits) and must exceed 255 (ESP-IDF ledc.c LEDC_IS_DIV_INVALID).
 * 20 kHz at 12 bits gives 250: rejected, and through R11 that failure stopped the whole display bring-up. */
_Static_assert((80000000ull * 256u) / ((uint64_t)SLIM4_BL_FREQ_HZ << SLIM4_BL_RES_BITS) > 255u,
               "backlight PWM frequency and resolution exceed the LEDC clock");
#define SLIM4_AUDIO_CHUNK_FRAMES 256u
#define SLIM4_AUDIO_QUEUE_LENGTH 16u
#define SLIM4_AUDIO_MAX_QUEUED_FRAMES (SLIM4_AUDIO_CHUNK_FRAMES * SLIM4_AUDIO_QUEUE_LENGTH)
#define SLIM4_AUDIO_DMA_DESC 6u
#define SLIM4_AUDIO_DMA_FRAMES 256u   /* 6 x 256 frames in DMA: 32 ms at 48 kHz still to play after the last write */

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
static volatile bool s_audio_power_mute;   /* set by the power policy (slim4_power.c): no budget for audio */
static inline uint8_t audio_volume_now(void) { return s_audio_power_mute ? 0 : s_audio_volume; }
static uint32_t s_i2s_sample_rate;
static int64_t s_audio_last_write_us;   /* when the last chunk went into the DMA buffers */
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
static slim4_display_profile_t s_display_profile;
static SemaphoreHandle_t s_display_lock;   /* one drawer at a time: the main loop or the console */
#define SLIM4_DISPLAY_INIT_LIMIT_MS 8000   /* normal bring-up takes well under 1 s plus the 120 ms reset wait */
static SemaphoreHandle_t s_display_done;
static volatile bool s_display_abandoned;
static esp_err_t s_display_init_err = ESP_FAIL;
static const char *s_display_stage = "not started";
static const char *AUDIO_TAG = "slim4_audio";
static uint32_t s_button_stable;
static uint32_t s_button_candidate;
static int64_t s_button_candidate_since_us;
static bool s_button_sampler_started;
static portMUX_TYPE s_vsync_lock = portMUX_INITIALIZER_UNLOCKED;
static uint32_t s_panel_vsync_count;

#define SLIM4_BUTTON_DEBOUNCE_US 5000

static bool display_lock(void);
static void display_unlock(void);

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
    static const uint8_t dash[7] = {0,0,0,31,0,0,0};
    static const uint8_t colon[7] = {0,12,12,0,12,12,0};
    c = (char)toupper((unsigned char)c);
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
    case '/': return slash; case '.': return period; case '-': return dash; case ':': return colon;
    case ' ': return blank; default: return blank;
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

static slim4_status_t render_diagnostic_locked(uint32_t buttons, const uint32_t press_counts[4],
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
    draw_text_centered("R26 HARDWARE TEST", 135, 4, ivory);
    draw_text_centered("PRESS EACH CONTROL / LISTEN", 205, 2, cyan);
    const slim4_st_report_t *st = slim4_selftest_last();
    if (st) {
        char summary[56];
        (void)snprintf(summary, sizeof(summary), "SELF TEST: %u FAIL %u PASS %u INFO - BOOT: DETAILS",
                       st->fail, st->pass, st->info);
        draw_text_centered(summary, 250, 2, st->fail ? red : cyan);
    }

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
        if (power.battery_fault) {
            draw_text_at("BATTERY REVERSED - UNPLUG", 56, 900, 3, red);
        } else {
            (void)snprintf(line, sizeof(line), "BAT %04u MV %03u PCT", power.battery_mv, power.battery_percent);
            draw_text_at(line, 56, 900, 3, power.battery_low ? red : (power.battery_percent < 15 ? orange : ivory));
        }
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

slim4_status_t slim4_board_render_diagnostic(uint32_t buttons, const uint32_t press_counts[4],
                                              uint32_t frame_index,
                                              uint32_t measured_fps, uint32_t measured_vsync_hz,
                                              uint32_t max_render_us,
                                              uint32_t late_frames, uint8_t color_phase)
{
    if (!display_lock()) return SLIM4_ERR_NOT_READY;
    const slim4_status_t st = render_diagnostic_locked(buttons, press_counts, frame_index, measured_fps, measured_vsync_hz, max_render_us, late_frames, color_phase);
    display_unlock();
    return st;
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
    draw_text_centered("SLIM4 / R26", 515, 4, ivory);
    fill_rect(180, 590, SLIM4_LCD_WIDTH - 360, 2, cyan);
    draw_text_centered("SYSTEM BOOT", 640, 4, cyan);
    draw_text_centered("INITIALIZING", 705, 2, ivory);
    draw_text_centered("R.A. PEDDYCOART", 1130, 2, ivory);
    draw_text_centered("STARTING", 1190, 2, gold);
}

static void show_boot_result_locked(bool software_verified)
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

void slim4_board_show_boot_result(bool software_verified)
{
    if (!display_lock()) return;
    show_boot_result_locked(software_verified);
    display_unlock();
}

static slim4_status_t show_selftest_locked(const slim4_st_report_t *rep)
{
    if (!s_display_ready || !s_framebuffer) return SLIM4_ERR_NOT_READY;
    if (!rep) return SLIM4_ERR_INVALID_ARG;
    const uint16_t navy = rgb565(7, 19, 34);
    const uint16_t ivory = rgb565(240, 244, 245);
    const uint16_t cyan = rgb565(45, 210, 230);
    const uint16_t gold = rgb565(255, 188, 57);
    const uint16_t red = rgb565(255, 72, 74);
    const uint16_t white = rgb565(255, 255, 255);
    const uint16_t black = rgb565(0, 0, 0);
    fill_rect(0, 0, SLIM4_LCD_WIDTH, SLIM4_LCD_HEIGHT, navy);
    fill_rect(20, 20, SLIM4_LCD_WIDTH - 40, 4, cyan);
    fill_rect(20, SLIM4_LCD_HEIGHT - 24, SLIM4_LCD_WIDTH - 40, 4, cyan);
    fill_rect(20, 20, 4, SLIM4_LCD_HEIGHT - 40, cyan);
    fill_rect(SLIM4_LCD_WIDTH - 24, 20, 4, SLIM4_LCD_HEIGHT - 40, cyan);

    draw_text_centered("SELF TEST", 44, 4, ivory);
    draw_text_centered("STRUTHIO SLIM4 / PCB R26 / FIRMWARE R11", 90, 2, cyan);
    char line[48];
    (void)snprintf(line, sizeof(line), "%u FAIL  %u PASS  %u INFO", rep->fail, rep->pass, rep->info);
    draw_text_centered(line, 122, 3, rep->fail ? red : cyan);

    /* One row per check: verdict, check name, what was found (at most 35 characters, so it ends inside the frame). */
    const int top = 170, bottom = 1074;
    const int pitch = rep->count ? ((bottom - top) / rep->count < 30 ? (bottom - top) / rep->count : 30) : 30;
    for (uint8_t i = 0; i < rep->count; ++i) {
        const slim4_st_item_t *it = &rep->items[i];
        const int y = top + i * pitch;
        const uint16_t tag = it->verdict == SLIM4_ST_FAIL ? red : (it->verdict == SLIM4_ST_INFO ? gold : cyan);
        draw_text_at(slim4_st_verdict_name(it->verdict), 32, y, 2, tag);
        draw_text_at(it->id, 88, y, 2, ivory);
        draw_text_at(it->brief, 264, y, 2, it->verdict == SLIM4_ST_FAIL ? red : ivory);
    }
    draw_text_centered("ANY CONTROL: CONTINUE   BOOT: SHOW AGAIN", 1088, 2, gold);

    /* Video check for CLK and D1, which carry video only: full-saturation bars and 1-pixel gratings toggle every
     * bit of the RGB565 stream; a marginal lane shows sparkles, shifted rows or wrong colours here first. */
    static const uint8_t bars[8][3] = {
        {255, 255, 255}, {255, 255, 0}, {0, 255, 255}, {0, 255, 0},
        {255, 0, 255}, {255, 0, 0}, {0, 0, 255}, {0, 0, 0},
    };
    const int bar_w = (SLIM4_LCD_WIDTH - 72) / 8;
    for (int b = 0; b < 8; ++b) {
        fill_rect(36 + b * bar_w, 1112, bar_w, 50, rgb565(bars[b][0], bars[b][1], bars[b][2]));
    }
    for (int x = 36; x < 36 + 8 * bar_w; ++x) fill_rect(x, 1166, 1, 28, (x & 1) ? white : black);
    for (int y = 1198; y < 1226; ++y) fill_rect(36, y, 8 * bar_w, 1, (y & 1) ? white : black);
    draw_text_centered("BARS AND LINES MUST BE CLEAN", 1232, 2, ivory);

    const esp_err_t err = panel_draw_bitmap_wait(s_framebuffer);
    return err == ESP_OK ? SLIM4_OK : SLIM4_ERR_IO;
}

slim4_status_t slim4_board_show_selftest(const slim4_st_report_t *rep)
{
    if (!display_lock()) return SLIM4_ERR_NOT_READY;
    const slim4_status_t st = show_selftest_locked(rep);
    display_unlock();
    return st;
}

static slim4_status_t show_pattern_locked(slim4_pattern_t pattern)
{
    if (!s_display_ready || !s_framebuffer) return SLIM4_ERR_NOT_READY;
    static const uint8_t bars[8][3] = {
        {255, 255, 255}, {255, 255, 0}, {0, 255, 255}, {0, 255, 0},
        {255, 0, 255}, {255, 0, 0}, {0, 0, 255}, {0, 0, 0},
    };
    switch (pattern) {
    case SLIM4_PATTERN_WHITE: fill_rect(0, 0, SLIM4_LCD_WIDTH, SLIM4_LCD_HEIGHT, rgb565(255, 255, 255)); break;
    case SLIM4_PATTERN_BLACK: fill_rect(0, 0, SLIM4_LCD_WIDTH, SLIM4_LCD_HEIGHT, 0); break;
    case SLIM4_PATTERN_RED: fill_rect(0, 0, SLIM4_LCD_WIDTH, SLIM4_LCD_HEIGHT, rgb565(255, 0, 0)); break;
    case SLIM4_PATTERN_GREEN: fill_rect(0, 0, SLIM4_LCD_WIDTH, SLIM4_LCD_HEIGHT, rgb565(0, 255, 0)); break;
    case SLIM4_PATTERN_BLUE: fill_rect(0, 0, SLIM4_LCD_WIDTH, SLIM4_LCD_HEIGHT, rgb565(0, 0, 255)); break;
    case SLIM4_PATTERN_BARS:
        for (int b = 0; b < 8; ++b) {
            fill_rect(b * SLIM4_LCD_WIDTH / 8, 0, SLIM4_LCD_WIDTH / 8 + 1, SLIM4_LCD_HEIGHT,
                      rgb565(bars[b][0], bars[b][1], bars[b][2]));
        }
        break;
    case SLIM4_PATTERN_CHECKER:   /* 1-pixel checkerboard: every pixel toggles every bit against its neighbours */
        for (int y = 0; y < SLIM4_LCD_HEIGHT; ++y) {
            uint16_t *row = s_framebuffer + y * SLIM4_LCD_WIDTH;
            for (int x = 0; x < SLIM4_LCD_WIDTH; ++x) row[x] = ((x ^ y) & 1) ? 0xFFFFu : 0x0000u;
        }
        break;
    case SLIM4_PATTERN_GRADIENT:  /* red, green, blue and grey ramps: every level of each channel */
        for (int y = 0; y < SLIM4_LCD_HEIGHT; ++y) {
            const int band = y * 4 / SLIM4_LCD_HEIGHT;
            uint16_t *row = s_framebuffer + y * SLIM4_LCD_WIDTH;
            for (int x = 0; x < SLIM4_LCD_WIDTH; ++x) {
                const uint8_t v = (uint8_t)(x * 255 / (SLIM4_LCD_WIDTH - 1));
                row[x] = band == 0 ? rgb565(v, 0, 0) : band == 1 ? rgb565(0, v, 0) : band == 2 ? rgb565(0, 0, v)
                                                                                     : rgb565(v, v, v);
            }
        }
        break;
    default: return SLIM4_ERR_INVALID_ARG;
    }
    return panel_draw_bitmap_wait(s_framebuffer) == ESP_OK ? SLIM4_OK : SLIM4_ERR_IO;
}

slim4_status_t slim4_board_show_pattern(slim4_pattern_t pattern)
{
    if (!display_lock()) return SLIM4_ERR_NOT_READY;
    const slim4_status_t st = show_pattern_locked(pattern);
    display_unlock();
    return st;
}

static esp_err_t init_backlight(void)
{
    const ledc_timer_config_t timer = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = (ledc_timer_bit_t)SLIM4_BL_RES_BITS,
        .timer_num = LEDC_TIMER_0,
        .freq_hz = SLIM4_BL_FREQ_HZ,
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
    channel_cfg.dma_desc_num = SLIM4_AUDIO_DMA_DESC;
    channel_cfg.dma_frame_num = SLIM4_AUDIO_DMA_FRAMES;
    /* Send silence once the queue runs dry; otherwise the DMA repeats its last buffers (a buzz in every gap). */
    channel_cfg.auto_clear_after_cb = true;
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
        if (audio_volume_now() == 0) {
            (void)xQueueReset(s_audio_queue);
            stop_audio_clock();
            continue;
        }

        bool processed_chunk = false;
        slim4_audio_chunk_t chunk;
        while (audio_volume_now() != 0 && xQueueReceive(s_audio_queue, &chunk, 0) == pdTRUE) {
            processed_chunk = true;
            esp_err_t err = configure_audio_rate(chunk.sample_rate);
            if (err == ESP_OK) err = start_audio_clock();
            if (err != ESP_OK) {
                ESP_LOGE(AUDIO_TAG, "audio start failed: %s", esp_err_to_name(err));
                stop_audio_clock();
                continue;
            }

            const uint8_t volume = audio_volume_now();
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
            s_audio_last_write_us = esp_timer_get_time();
        }
        /* Stop the clocks and shut the amplifiers down only after what is already in DMA has played, plus 10 ms:
         * stopping at once cut the end off every sound (a click). */
        if (!processed_chunk && notifications == 0 && s_i2s_running && s_i2s_sample_rate) {
            const int64_t drain_us = (int64_t)SLIM4_AUDIO_DMA_DESC * SLIM4_AUDIO_DMA_FRAMES * 1000000 /
                                     s_i2s_sample_rate + 10000;
            if (esp_timer_get_time() - s_audio_last_write_us >= drain_us) stop_audio_clock();
        }
    }
}

static uint32_t s_backlight_request;               /* level asked for, before the power cap */
static uint8_t s_backlight_cap = 100;             /* set by the power policy (slim4_power.c) */
static bool s_backlight_ready;
static bool s_backlight_failed;

static esp_err_t set_backlight(uint32_t percent)
{
    if (percent > 100) percent = 100;
    s_backlight_request = percent;
    if (!s_backlight_ready) return ESP_OK;
    if (percent > s_backlight_cap) percent = s_backlight_cap;
    uint32_t duty = (SLIM4_BL_DUTY_MAX * percent) / 100;
    esp_err_t err = ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, duty);
    if (err != ESP_OK) return err;
    return ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
}

slim4_status_t slim4_board_set_backlight(uint8_t percent)
{
    if (percent > 100) return SLIM4_ERR_INVALID_ARG;
    /* Only with a panel that answered: with no LED load the boost runs up to its 37-39 V open-LED limit. */
    if (!s_backlight_ready || !s_display_ready) return SLIM4_ERR_NOT_READY;
    return set_backlight(percent) == ESP_OK ? SLIM4_OK : SLIM4_ERR_IO;
}

uint8_t slim4_board_backlight_cap(void)
{
    return s_backlight_cap;
}

void slim4_board_backlight_cap_changed(uint8_t cap_percent)
{
    s_backlight_cap = cap_percent > 100 ? 100 : cap_percent;
    if (s_backlight_ready) (void)set_backlight(s_backlight_request);
}

/* ---- Panel probe (self-test) ----------------------------------------------------------------------------
 * Before the ILI9881C driver starts, read the controller's ID over DSI lane 0 with every wait bounded. The driver
 * reads the same ID itself, but ESP-IDF's DSI read and the acknowledge after each command wait without a time limit
 * (the host's timeouts are off): a panel that does not answer (FPC not seated, an open D0 line, no panel supply)
 * would hang the boot in a watchdog reset loop. The probe uses the host's registers directly, exactly as ESP-IDF's
 * HAL does (mipi_dsi_hal.c: DCS long write, set maximum return size, DCS read), only with time limits. Low-power
 * mode drives D0_P and D0_N separately, so an answer shows both lines of lane 0 work, in both directions. */
#define PROBE_TIMEOUT_US 20000
static slim4_panel_probe_t s_probe = {.stopped_at = "display bring-up not started"};

static bool probe_wait(bool (*done)(void))
{
    const int64_t t0 = esp_timer_get_time();
    while (!done()) {
        if (esp_timer_get_time() - t0 >= PROBE_TIMEOUT_US) return false;
        esp_rom_delay_us(5);
    }
    return true;
}

static bool probe_cmd_room(void) { return !mipi_dsi_host_ll_gen_is_cmd_fifo_full(&MIPI_DSI_HOST); }
static bool probe_pld_room(void) { return !mipi_dsi_host_ll_gen_is_write_fifo_full(&MIPI_DSI_HOST); }

/* Everything sent, no read pending, lane 0 back in stop state and driven by the host (after a bus turnaround the
 * panel hands lane 0 back only once it has answered). */
static bool probe_idle(void)
{
    return MIPI_DSI_HOST.cmd_pkt_status.gen_cmd_empty && MIPI_DSI_HOST.cmd_pkt_status.gen_pld_w_empty &&
           MIPI_DSI_HOST.cmd_pkt_status.gen_buff_cmd_empty && !MIPI_DSI_HOST.cmd_pkt_status.gen_rd_cmd_busy &&
           MIPI_DSI_HOST.phy_status.phy_stopstate0lane && !MIPI_DSI_HOST.phy_status.phy_direction;
}

/* Idle for 50 us without a break: between a packet's end and the bus turnaround for its acknowledge, lane 0 is in
 * stop state for a moment, and a single look could take that for the end of the exchange. */
static bool probe_wait_idle(void)
{
    const int64_t t0 = esp_timer_get_time();
    int stable = 0;
    while (stable < 10) {
        stable = probe_idle() ? stable + 1 : 0;
        if (esp_timer_get_time() - t0 >= PROBE_TIMEOUT_US) return false;
        esp_rom_delay_us(5);
    }
    return true;
}

static bool probe_answer_ready(void)
{
    return !MIPI_DSI_HOST.cmd_pkt_status.gen_rd_cmd_busy && !mipi_dsi_host_ll_gen_is_read_fifo_empty(&MIPI_DSI_HOST);
}

static void probe_drain_read_fifo(void)
{
    for (int i = 0; i < 64 && !mipi_dsi_host_ll_gen_is_read_fifo_empty(&MIPI_DSI_HOST); ++i) {
        (void)mipi_dsi_host_ll_gen_read_payload_fifo(&MIPI_DSI_HOST);
    }
}

/* ILI9881C page select: DCS long write FF 98 81 <page> on virtual channel 0. */
static bool probe_select_page(uint8_t page)
{
    const uint32_t payload = 0xFFu | (0x98u << 8) | (0x81u << 16) | ((uint32_t)page << 24);
    if (!probe_wait(probe_pld_room)) return false;
    mipi_dsi_host_ll_gen_write_payload_fifo(&MIPI_DSI_HOST, payload);
    if (!probe_wait(probe_cmd_room)) return false;
    mipi_dsi_host_ll_gen_set_packet_header(&MIPI_DSI_HOST, 0, MIPI_DSI_DT_DCS_LONG_WRITE, 0, 4);
    return probe_wait_idle();
}

static bool probe_read_register(uint8_t reg, uint8_t *value)
{
    if (!probe_wait(probe_cmd_room)) return false;
    mipi_dsi_host_ll_gen_set_packet_header(&MIPI_DSI_HOST, 0, MIPI_DSI_DT_SET_MAXIMUM_RETURN_PKT, 0, 1);
    if (!probe_wait_idle()) return false;
    mipi_dsi_host_ll_enable_bta(&MIPI_DSI_HOST, true);
    mipi_dsi_host_ll_gen_set_rx_vcid(&MIPI_DSI_HOST, 0);
    probe_drain_read_fifo();
    mipi_dsi_host_ll_gen_set_packet_header(&MIPI_DSI_HOST, 0, MIPI_DSI_DT_DCS_READ_0, 0, reg);
    if (!probe_wait(probe_answer_ready)) return false;
    *value = (uint8_t)(mipi_dsi_host_ll_gen_read_payload_fifo(&MIPI_DSI_HOST) & 0xFFu);
    probe_drain_read_fifo();
    return probe_wait_idle();
}

/* Two exchanges: the first after reset (page 1, the three ID registers), then a second (ID again, page 0). The
 * panel clears its error bits once it has reported them, so the second exchange's flags are new errors only; the
 * first's can include what the panel saw while it powered up. */
static void probe_panel(void)
{
    s_probe.attempted = true;
    s_probe.answered = false;
    s_probe.int_st0_before = MIPI_DSI_HOST.int_st0.val;   /* reading clears them */
    s_probe.int_st1_before = MIPI_DSI_HOST.int_st1.val;
    uint8_t again = 0;
    if (!probe_select_page(1)) {
        s_probe.stopped_at = "page select write (the host could not send on lane 0)";
    } else if (!probe_read_register(0x00, &s_probe.id[0]) || !probe_read_register(0x01, &s_probe.id[1]) ||
               !probe_read_register(0x02, &s_probe.id[2])) {
        s_probe.stopped_at = "ID read (no answer after the bus turnaround on lane 0)";
    } else {
        s_probe.int_st0_first = MIPI_DSI_HOST.int_st0.val;
        s_probe.int_st1_first = MIPI_DSI_HOST.int_st1.val;
        if (!probe_read_register(0x00, &again)) {
            s_probe.stopped_at = "second ID read (no answer after the bus turnaround on lane 0)";
        } else if (!probe_select_page(0)) {
            s_probe.stopped_at = "page 0 write (no acknowledge on lane 0)";
        } else {
            s_probe.answered = true;
            s_probe.repeat_ok = again == s_probe.id[0];
            s_probe.stopped_at = NULL;
        }
    }
    s_probe.int_st0 = MIPI_DSI_HOST.int_st0.val;
    s_probe.int_st1 = MIPI_DSI_HOST.int_st1.val;
    ESP_LOGI(TAG, "panel probe: %s, ID %02X %02X %02X, host flags %08lX/%08lX",
             s_probe.answered ? "answered" : s_probe.stopped_at, s_probe.id[0], s_probe.id[1], s_probe.id[2],
             (unsigned long)s_probe.int_st0, (unsigned long)s_probe.int_st1);
}

void slim4_board_panel_probe(slim4_panel_probe_t *out)
{
    if (out) *out = s_probe;
}

#define PROFILE_NS "slim4_sys"
#define PROFILE_KEY "dsi_profile"

slim4_display_profile_t slim4_board_display_profile(void)
{
    uint8_t v = SLIM4_DISPLAY_NORMAL;
    nvs_handle_t h;
    if (s_nvs_ready && nvs_open(PROFILE_NS, NVS_READONLY, &h) == ESP_OK) {
        (void)nvs_get_u8(h, PROFILE_KEY, &v);
        nvs_close(h);
    }
    return v == SLIM4_DISPLAY_SAFE ? SLIM4_DISPLAY_SAFE : SLIM4_DISPLAY_NORMAL;
}

slim4_status_t slim4_board_set_display_profile(slim4_display_profile_t profile)
{
    if (profile != SLIM4_DISPLAY_NORMAL && profile != SLIM4_DISPLAY_SAFE) return SLIM4_ERR_INVALID_ARG;
    if (!s_nvs_ready) return SLIM4_ERR_NOT_READY;
    nvs_handle_t h;
    if (nvs_open(PROFILE_NS, NVS_READWRITE, &h) != ESP_OK) return SLIM4_ERR_IO;
    esp_err_t err = nvs_set_u8(h, PROFILE_KEY, (uint8_t)profile);
    if (err == ESP_OK) err = nvs_commit(h);
    nvs_close(h);
    return err == ESP_OK ? SLIM4_OK : SLIM4_ERR_IO;
}

bool slim4_board_backlight_failed(void)
{
    return s_backlight_failed;
}

static bool display_lock(void)
{
    return s_display_lock && xSemaphoreTake(s_display_lock, pdMS_TO_TICKS(500)) == pdTRUE;
}

static void display_unlock(void)
{
    xSemaphoreGive(s_display_lock);
}

static esp_err_t init_display(void)
{
    esp_err_t err;
    ESP_LOGI(TAG, "display bring-up: D-PHY rail, reset, backlight PWM, DSI bus, probe, panel init");
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
    /* Q1 inverts this gate: high asserts LCD_RESX low, low releases reset. The level goes in before the output is
     * enabled, so reset is never released for an instant. */
    err = gpio_set_level(SLIM4_GPIO_LCD_RESET_GATE, 1);
    if (err != ESP_OK) return err;
    err = gpio_config(&reset_gate);
    if (err != ESP_OK) return err;
    vTaskDelay(pdMS_TO_TICKS(10));

    s_display_stage = "backlight PWM";
    err = init_backlight();
    if (err == ESP_OK) {
        s_backlight_ready = true;
    } else {
        /* Not fatal: the panel can still be probed and driven; the screen stays dark without its backlight. */
        s_backlight_failed = true;
        ESP_LOGE(TAG, "backlight PWM setup failed: %s; continuing with the panel", esp_err_to_name(err));
    }

    s_display_stage = "two-lane DSI bus (D-PHY PLL lock, lanes to stop state)";
    ESP_LOGI(TAG, "display: %s", s_display_stage);
    s_display_profile = slim4_board_display_profile();
    esp_lcd_dsi_bus_config_t bus_cfg = ILI9881C_PANEL_BUS_DSI_2CH_CONFIG();
    bus_cfg.lane_bit_rate_mbps = s_display_profile == SLIM4_DISPLAY_SAFE ? SLIM4_PANEL_SAFE_LANE_MBPS
                                                                         : SLIM4_PANEL_LANE_MBPS;
    ESP_LOGI(TAG, "display profile %s: %lu Mbit/s per lane, %u MHz pixel clock",
             s_display_profile == SLIM4_DISPLAY_SAFE ? "safe" : "normal", (unsigned long)bus_cfg.lane_bit_rate_mbps,
             s_display_profile == SLIM4_DISPLAY_SAFE ? SLIM4_PANEL_SAFE_PIXEL_MHZ : SLIM4_PANEL_PIXEL_MHZ);
    err = esp_lcd_new_dsi_bus(&bus_cfg, &s_dsi_bus);
    if (err != ESP_OK) return err;
    if (s_display_abandoned) return ESP_ERR_TIMEOUT;   /* the PHY came up after the boot gave up on it */

    s_display_stage = "DBI command channel";
    esp_lcd_dbi_io_config_t dbi_cfg = ILI9881C_PANEL_IO_DBI_CONFIG();
    err = esp_lcd_new_panel_io_dbi(s_dsi_bus, &dbi_cfg, &s_dbi_io);
    if (err != ESP_OK) return err;

    s_display_stage = "ILI9881C panel driver (Crystalfontz CFAF7201280A0-050TN)";
    esp_lcd_dpi_panel_config_t dpi_cfg = SLIM4_PANEL_DPI_CONFIG(LCD_COLOR_FMT_RGB565);
    if (s_display_profile == SLIM4_DISPLAY_SAFE) dpi_cfg.dpi_clock_freq_mhz = SLIM4_PANEL_SAFE_PIXEL_MHZ;
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
    s_display_lock = xSemaphoreCreateMutex();
    if (!s_display_lock) return ESP_ERR_NO_MEM;

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
    s_display_stage = "panel probe on DSI lane 0";
    probe_panel();
    if (!slim4_st_panel_usable(&s_probe)) return ESP_ERR_NOT_FOUND;
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

    if (s_display_abandoned) return ESP_ERR_TIMEOUT;   /* too late: the boot went on without the display */
    s_display_ready = true;
    ESP_LOGI(TAG, "ILI9881C two-lane DSI initialized: 720x1280 RGB565, %s profile (about %d Hz)",
             s_display_profile == SLIM4_DISPLAY_SAFE ? "safe" : "normal",
             s_display_profile == SLIM4_DISPLAY_SAFE ? 45 : 59);
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


static void display_init_task(void *arg)
{
    (void)arg;
    s_display_init_err = init_display();
    xSemaphoreGive(s_display_done);
    vTaskDelete(NULL);
}

slim4_status_t slim4_board_init(void)
{
    s_button_stable = 0;
    s_button_candidate = 0;
    s_button_candidate_since_us = 0;
    s_button_sampler_started = false;
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS %s: erasing the nvs partition", esp_err_to_name(err));
        err = nvs_flash_erase();
        if (err == ESP_OK) err = nvs_flash_init();
    }
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

    /* The display comes up in its own task with a time limit: ESP-IDF's DSI bus setup waits without limit for the
     * D-PHY PLL to lock and the lanes to stop, which never happens with VDDO_MIPI_2V5 missing (U1 pads 41/73). */
    s_display_done = xSemaphoreCreateBinary();
    if (!s_display_done ||
        xTaskCreate(display_init_task, "slim4_disp_init", 8192, NULL, uxTaskPriorityGet(NULL), NULL) != pdPASS) {
        s_probe.stopped_at = "display init task (no memory)";
        ESP_LOGE(TAG, "display init task could not start");
        return SLIM4_OK;
    }
    if (xSemaphoreTake(s_display_done, pdMS_TO_TICKS(SLIM4_DISPLAY_INIT_LIMIT_MS)) != pdTRUE) {
        s_display_abandoned = true;
        s_probe.stopped_at = s_display_stage;
        ESP_LOGE(TAG, "display bring-up still at '%s' after %d ms: abandoned; continuing with serial diagnostics",
                 s_display_stage, SLIM4_DISPLAY_INIT_LIMIT_MS);
        return SLIM4_OK;
    }
    if (s_display_init_err != ESP_OK) {
        /* Keep the probe's own reason when the panel did not answer; otherwise record the failed stage. */
        if (!s_probe.attempted || s_probe.answered) s_probe.stopped_at = s_display_stage;
        ESP_LOGE(TAG, "display failed at %s: %s; continuing with serial diagnostics",
                 s_display_stage, esp_err_to_name(s_display_init_err));
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

static slim4_status_t display_present_locked(const slim4_surface_t *surface)
{
    if (!surface || !surface->pixels_rgb565) return SLIM4_ERR_INVALID_ARG;
    if (!s_display_ready || surface->pixels_rgb565 != s_framebuffer) return SLIM4_ERR_NOT_READY;
    esp_err_t err = panel_draw_bitmap_wait(s_framebuffer);
    return err == ESP_OK ? SLIM4_OK : SLIM4_ERR_IO;
}

slim4_status_t slim4_board_display_present(const slim4_surface_t *surface)
{
    if (!display_lock()) return SLIM4_ERR_NOT_READY;
    const slim4_status_t st = display_present_locked(surface);
    display_unlock();
    return st;
}

void slim4_board_audio_power_mute(bool mute)
{
    s_audio_power_mute = mute;
    /* The worker drops queued audio and puts both amplifiers into shutdown (SD_MODE low) on its next pass. */
    if (mute && s_audio_task) xTaskNotifyGive(s_audio_task);
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
    /* The MAX98357A supports 8, 16, 32, 44.1, 48, 88.2 and 96 kHz only (11.025-24 kHz are not supported). */
    if ((!stereo && frames) || !(rate == 8000 || rate == 16000 || rate == 32000 || rate == 44100 ||
                                 rate == 48000 || rate == 88200 || rate == 96000)) {
        return SLIM4_ERR_INVALID_ARG;
    }
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
