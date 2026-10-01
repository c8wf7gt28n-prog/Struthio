// STRUTHIO HANDHELD · Waveshare ESP32-S3-Touch-LCD-3.5B adapter.
//
// Power, panel and backlight follow Waveshare's ESP-IDF example (Apache-2.0),
// repository waveshareteam/ESP32-S3-Touch-LCD-3.5B, commit 840daf2:
// ESP-IDF/01_factory/main/main.cpp (init order, TCA9554 reset pulse) and
// components/esp_bsp/bsp_{i2c,display}.c (pins, AXS15231B init commands,
// LEDC backlight). The panel driver is espressif/esp_lcd_axs15231b; see
// main/idf_component.yml. Pins: board_pins.h. Not yet run on hardware.
//
// The STRUTHIO-specific part is how pixels go out. A band is sent with
// esp_lcd_panel_draw_bitmap, then we wait for the driver's colour-transfer-done
// callback, so the caller can reuse its buffer at once. In QSPI mode the
// AXS15231B gets no row address (driver: RAMWR at y 0, RAMWRC otherwise), so a
// frame must arrive top to bottom with no gaps; the order check below enforces it.
#include "board.h"
#include "board_pins.h"
#include "board_pmu.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "driver/ledc.h"
#include "driver/spi_master.h"
#include "esp_io_expander_tca9554.h"
#include "esp_lcd_axs15231b.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

static const char *TAG = "board";

// ---- pins (board_pins.h has the full map) ----------------------------------------------------
enum {
    PIN_I2C_SDA = 8, PIN_I2C_SCL = 7,
    PIN_LCD_CS = 12, PIN_LCD_SCLK = 5, PIN_LCD_D0 = 1, PIN_LCD_D1 = 2, PIN_LCD_D2 = 3, PIN_LCD_D3 = 4,
    PIN_LCD_BL = 6,
};
#define LCD_SPI_HOST SPI2_HOST
#define LCD_PCLK_HZ (40 * 1000 * 1000)             // vendor value
#define LCD_MAX_LINES 40                            // the largest band anyone sends (greybox: 40, panel renderer: 16)

static i2c_master_bus_handle_t s_i2c;
static esp_io_expander_handle_t s_expander;
static esp_lcd_panel_io_handle_t s_io;
static esp_lcd_panel_handle_t s_panel;
static SemaphoreHandle_t s_trans_done;
static int s_next_y;                                // where the panel's write pointer is
static uint32_t s_order_errors;
static bool s_power_ok;

// AXS15231B init commands, copied from the vendor's bsp_display.c.
static const axs15231b_lcd_init_cmd_t lcd_init_cmds[] = {
    {0xBB, (uint8_t[]){0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x5A, 0xA5}, 8, 0},
    {0xA0, (uint8_t[]){0xC0, 0x10, 0x00, 0x02, 0x00, 0x00, 0x04, 0x3F, 0x20, 0x05, 0x3F, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x00}, 17, 0},
    {0xA2, (uint8_t[]){0x30, 0x3C, 0x24, 0x14, 0xD0, 0x20, 0xFF, 0xE0, 0x40, 0x19, 0x80, 0x80, 0x80, 0x20, 0xf9, 0x10, 0x02, 0xff, 0xff, 0xF0, 0x90, 0x01, 0x32, 0xA0, 0x91, 0xE0, 0x20, 0x7F, 0xFF, 0x00, 0x5A}, 31, 0},
    {0xD0, (uint8_t[]){0xE0, 0x40, 0x51, 0x24, 0x08, 0x05, 0x10, 0x01, 0x20, 0x15, 0x42, 0xC2, 0x22, 0x22, 0xAA, 0x03, 0x10, 0x12, 0x60, 0x14, 0x1E, 0x51, 0x15, 0x00, 0x8A, 0x20, 0x00, 0x03, 0x3A, 0x12}, 30, 0},
    {0xA3, (uint8_t[]){0xA0, 0x06, 0xAa, 0x00, 0x08, 0x02, 0x0A, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x55, 0x55}, 22, 0},
    {0xC1, (uint8_t[]){0x31, 0x04, 0x02, 0x02, 0x71, 0x05, 0x24, 0x55, 0x02, 0x00, 0x41, 0x00, 0x53, 0xFF, 0xFF, 0xFF, 0x4F, 0x52, 0x00, 0x4F, 0x52, 0x00, 0x45, 0x3B, 0x0B, 0x02, 0x0d, 0x00, 0xFF, 0x40}, 30, 0},
    {0xC3, (uint8_t[]){0x00, 0x00, 0x00, 0x50, 0x03, 0x00, 0x00, 0x00, 0x01, 0x80, 0x01}, 11, 0},
    {0xC4, (uint8_t[]){0x00, 0x24, 0x33, 0x80, 0x00, 0xea, 0x64, 0x32, 0xC8, 0x64, 0xC8, 0x32, 0x90, 0x90, 0x11, 0x06, 0xDC, 0xFA, 0x00, 0x00, 0x80, 0xFE, 0x10, 0x10, 0x00, 0x0A, 0x0A, 0x44, 0x50}, 29, 0},
    {0xC5, (uint8_t[]){0x18, 0x00, 0x00, 0x03, 0xFE, 0x3A, 0x4A, 0x20, 0x30, 0x10, 0x88, 0xDE, 0x0D, 0x08, 0x0F, 0x0F, 0x01, 0x3A, 0x4A, 0x20, 0x10, 0x10, 0x00}, 23, 0},
    {0xC6, (uint8_t[]){0x05, 0x0A, 0x05, 0x0A, 0x00, 0xE0, 0x2E, 0x0B, 0x12, 0x22, 0x12, 0x22, 0x01, 0x03, 0x00, 0x3F, 0x6A, 0x18, 0xC8, 0x22}, 20, 0},
    {0xC7, (uint8_t[]){0x50, 0x32, 0x28, 0x00, 0xa2, 0x80, 0x8f, 0x00, 0x80, 0xff, 0x07, 0x11, 0x9c, 0x67, 0xff, 0x24, 0x0c, 0x0d, 0x0e, 0x0f}, 20, 0},
    {0xC9, (uint8_t[]){0x33, 0x44, 0x44, 0x01}, 4, 0},
    {0xCF, (uint8_t[]){0x2C, 0x1E, 0x88, 0x58, 0x13, 0x18, 0x56, 0x18, 0x1E, 0x68, 0x88, 0x00, 0x65, 0x09, 0x22, 0xC4, 0x0C, 0x77, 0x22, 0x44, 0xAA, 0x55, 0x08, 0x08, 0x12, 0xA0, 0x08}, 27, 0},
    {0xD5, (uint8_t[]){0x40, 0x8E, 0x8D, 0x01, 0x35, 0x04, 0x92, 0x74, 0x04, 0x92, 0x74, 0x04, 0x08, 0x6A, 0x04, 0x46, 0x03, 0x03, 0x03, 0x03, 0x82, 0x01, 0x03, 0x00, 0xE0, 0x51, 0xA1, 0x00, 0x00, 0x00}, 30, 0},
    {0xD6, (uint8_t[]){0x10, 0x32, 0x54, 0x76, 0x98, 0xBA, 0xDC, 0xFE, 0x93, 0x00, 0x01, 0x83, 0x07, 0x07, 0x00, 0x07, 0x07, 0x00, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x00, 0x84, 0x00, 0x20, 0x01, 0x00}, 30, 0},
    {0xD7, (uint8_t[]){0x03, 0x01, 0x0b, 0x09, 0x0f, 0x0d, 0x1E, 0x1F, 0x18, 0x1d, 0x1f, 0x19, 0x40, 0x8E, 0x04, 0x00, 0x20, 0xA0, 0x1F}, 19, 0},
    {0xD8, (uint8_t[]){0x02, 0x00, 0x0a, 0x08, 0x0e, 0x0c, 0x1E, 0x1F, 0x18, 0x1d, 0x1f, 0x19}, 12, 0},
    {0xD9, (uint8_t[]){0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F}, 12, 0},
    {0xDD, (uint8_t[]){0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F, 0x1F}, 12, 0},
    {0xDF, (uint8_t[]){0x44, 0x73, 0x4B, 0x69, 0x00, 0x0A, 0x02, 0x90}, 8, 0},
    {0xE0, (uint8_t[]){0x3B, 0x28, 0x10, 0x16, 0x0c, 0x06, 0x11, 0x28, 0x5c, 0x21, 0x0D, 0x35, 0x13, 0x2C, 0x33, 0x28, 0x0D}, 17, 0},
    {0xE1, (uint8_t[]){0x37, 0x28, 0x10, 0x16, 0x0b, 0x06, 0x11, 0x28, 0x5C, 0x21, 0x0D, 0x35, 0x14, 0x2C, 0x33, 0x28, 0x0F}, 17, 0},
    {0xE2, (uint8_t[]){0x3B, 0x07, 0x12, 0x18, 0x0E, 0x0D, 0x17, 0x35, 0x44, 0x32, 0x0C, 0x14, 0x14, 0x36, 0x3A, 0x2F, 0x0D}, 17, 0},
    {0xE3, (uint8_t[]){0x37, 0x07, 0x12, 0x18, 0x0E, 0x0D, 0x17, 0x35, 0x44, 0x32, 0x0C, 0x14, 0x14, 0x36, 0x32, 0x2F, 0x0F}, 17, 0},
    {0xE4, (uint8_t[]){0x3B, 0x07, 0x12, 0x18, 0x0E, 0x0D, 0x17, 0x39, 0x44, 0x2E, 0x0C, 0x14, 0x14, 0x36, 0x3A, 0x2F, 0x0D}, 17, 0},
    {0xE5, (uint8_t[]){0x37, 0x07, 0x12, 0x18, 0x0E, 0x0D, 0x17, 0x39, 0x44, 0x2E, 0x0C, 0x14, 0x14, 0x36, 0x3A, 0x2F, 0x0F}, 17, 0},
    {0xA4, (uint8_t[]){0x85, 0x85, 0x95, 0x82, 0xAF, 0xAA, 0xAA, 0x80, 0x10, 0x30, 0x40, 0x40, 0x20, 0xFF, 0x60, 0x30}, 16, 0},
    {0xA4, (uint8_t[]){0x85, 0x85, 0x95, 0x85}, 4, 0},
    {0xBB, (uint8_t[]){0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, 8, 0},
    {0x13, (uint8_t[]){0x00}, 0, 0},
    {0x11, (uint8_t[]){0x00}, 0, 120},
    {0x2C, (uint8_t[]){0x00, 0x00, 0x00, 0x00}, 4, 0},
};

// ---- power -----------------------------------------------------------------------------------
bool board_power_init(void) {
    i2c_master_bus_config_t bus = {
        .i2c_port = 0,
        .sda_io_num = PIN_I2C_SDA,
        .scl_io_num = PIN_I2C_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = 1,
    };
    if (i2c_new_master_bus(&bus, &s_i2c) != ESP_OK) { ESP_LOGE(TAG, "I2C bus failed"); return false; }
    s_power_ok = board_pmu_init(s_i2c);
    // LCD reset through the TCA9554, EXIO1: low 100 ms, then high 200 ms (vendor sequence).
    if (esp_io_expander_new_i2c_tca9554(s_i2c, ESP_IO_EXPANDER_I2C_TCA9554_ADDRESS_000, &s_expander) == ESP_OK) {
        esp_io_expander_set_dir(s_expander, IO_EXPANDER_PIN_NUM_1, IO_EXPANDER_OUTPUT);
        esp_io_expander_set_level(s_expander, IO_EXPANDER_PIN_NUM_1, 0);
        vTaskDelay(pdMS_TO_TICKS(100));
        esp_io_expander_set_level(s_expander, IO_EXPANDER_PIN_NUM_1, 1);
        vTaskDelay(pdMS_TO_TICKS(200));
    } else {
        ESP_LOGE(TAG, "TCA9554 not found: the LCD stays in reset");
    }
    return s_power_ok;
}
bool board_power_read(board_power_t *out) { return board_pmu_read(out); }
void board_power_off(void) { board_pmu_power_off(); }

// ---- display ---------------------------------------------------------------------------------
static bool IRAM_ATTR on_trans_done(esp_lcd_panel_io_handle_t io, esp_lcd_panel_io_event_data_t *ev, void *ctx) {
    (void)io; (void)ev; (void)ctx;
    BaseType_t woken = pdFALSE;
    xSemaphoreGiveFromISR(s_trans_done, &woken);
    return woken == pdTRUE;
}

bool board_display_init(void) {
    s_trans_done = xSemaphoreCreateBinary();
    if (!s_trans_done) return false;
    spi_bus_config_t bus = {
        .sclk_io_num = PIN_LCD_SCLK,
        .data0_io_num = PIN_LCD_D0,
        .data1_io_num = PIN_LCD_D1,
        .data2_io_num = PIN_LCD_D2,
        .data3_io_num = PIN_LCD_D3,
        .max_transfer_sz = BOARD_LCD_W * LCD_MAX_LINES * 2,
    };
    if (spi_bus_initialize(LCD_SPI_HOST, &bus, SPI_DMA_CH_AUTO) != ESP_OK) { ESP_LOGE(TAG, "SPI bus failed"); return false; }
    esp_lcd_panel_io_spi_config_t io = AXS15231B_PANEL_IO_QSPI_CONFIG(PIN_LCD_CS, on_trans_done, NULL);
    io.pclk_hz = LCD_PCLK_HZ;
    if (esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)LCD_SPI_HOST, &io, &s_io) != ESP_OK) { ESP_LOGE(TAG, "panel IO failed"); return false; }
    axs15231b_vendor_config_t vendor = {
        .init_cmds = lcd_init_cmds,
        .init_cmds_size = sizeof lcd_init_cmds / sizeof lcd_init_cmds[0],
        .flags.use_qspi_interface = 1,
    };
    esp_lcd_panel_dev_config_t dev = {
        .reset_gpio_num = -1,                       // reset is the TCA9554 pulse in board_power_init
        .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_RGB,
        .bits_per_pixel = 16,
        .vendor_config = &vendor,
    };
    if (esp_lcd_new_panel_axs15231b(s_io, &dev, &s_panel) != ESP_OK) { ESP_LOGE(TAG, "AXS15231B failed"); s_panel = NULL; return false; }
    esp_lcd_panel_reset(s_panel);
    esp_lcd_panel_init(s_panel);
    // This driver's disp_on_off(panel, x) sends DISPOFF when x is true, so false means ON (as in the vendor example).
    esp_lcd_panel_disp_on_off(s_panel, false);
    // backlight: LEDC on GPIO6, 10-bit, 5 kHz (vendor values), off until board_backlight()
    ledc_timer_config_t t = { .speed_mode = LEDC_LOW_SPEED_MODE, .timer_num = LEDC_TIMER_0, .duty_resolution = LEDC_TIMER_10_BIT,
                              .freq_hz = 5000, .clk_cfg = LEDC_AUTO_CLK };
    ledc_channel_config_t c = { .speed_mode = LEDC_LOW_SPEED_MODE, .channel = LEDC_CHANNEL_0, .timer_sel = LEDC_TIMER_0,
                                .intr_type = LEDC_INTR_DISABLE, .gpio_num = PIN_LCD_BL, .duty = 0, .hpoint = 0 };
    if (ledc_timer_config(&t) != ESP_OK || ledc_channel_config(&c) != ESP_OK) ESP_LOGW(TAG, "backlight PWM failed");
    s_next_y = 0;
    ESP_LOGI(TAG, "AXS15231B 320x480 QSPI at %d MHz", LCD_PCLK_HZ / 1000000);
    return true;
}

void board_display_lines(int y0, int n, const uint16_t *buf) {
    if (!s_panel || n <= 0) return;
    if (y0 != 0 && y0 != s_next_y) { s_order_errors++; return; }   // would land on the wrong rows
    if (esp_lcd_panel_draw_bitmap(s_panel, 0, y0, BOARD_LCD_W, y0 + n, buf) != ESP_OK) { s_order_errors++; return; }
    // wait for the colour transfer, so the caller may reuse buf (100 ms covers a 25 KB band many times over)
    if (xSemaphoreTake(s_trans_done, pdMS_TO_TICKS(100)) != pdTRUE) ESP_LOGW(TAG, "band at y %d: transfer timeout", y0);
    s_next_y = (y0 + n) % BOARD_LCD_H;
}
uint32_t board_display_order_errors(void) { return s_order_errors; }

void board_backlight(uint8_t percent) {
    if (!s_panel) return;
    if (percent > 100) percent = 100;
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, (uint32_t)percent * 1023u / 100u);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
}

// ---- audio -----------------------------------------------------------------------------------
// ES8311 (I2C 0x18) + NS4150B. Pins in board_pins.h; the vendor example
// (bsp_es8311.c) drives it through espressif/esp_codec_dev. Not wired yet:
// STRUTHIO has no sound assets for the device yet (manual section 14).
bool board_audio_init(void) { return false; }
void board_audio_cue(st_event_type_t event) { (void)event; }
