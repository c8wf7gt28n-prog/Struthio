#include "slim4_power.h"

#include "driver/gpio.h"
#include "driver/temperature_sensor.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"
#include "esp_sleep.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "slim4_pins.h"

/* Implemented in slim4_board.c: puts the display and audio into their off state. */
void slim4_board_prepare_power_off(void);

#define POWER_HOLD_US         (2000 * 1000)   /* hold the power button 2 s to switch off */
#define BATTERY_EMPTY_MV      3300u           /* power off below this (cell protection trips near 3.0 V) */
#define CHARGE_HOT_C          75              /* suspend charging above this die temperature */
#define CHARGE_COOL_C         65              /* resume below this */
#define POLICY_PERIOD_US      (500 * 1000)

static const char *TAG = "slim4_power";
static adc_oneshot_unit_handle_t s_adc;
static adc_cali_handle_t s_adc_cali;
static adc_channel_t s_adc_channel;
static temperature_sensor_handle_t s_tsens;
static bool s_ready;
static int64_t s_button_down_since;
static bool s_button_armed;
static int64_t s_next_policy_us;
static slim4_power_state_t s_state;

/* Open-circuit voltage of a LiPo cell at 0, 10, ..., 100 % (mV). Rough under load. */
static const uint16_t OCV_MV[11] = {3300, 3600, 3690, 3740, 3780, 3820, 3870, 3930, 4000, 4080, 4180};

static uint8_t percent_from_mv(uint16_t mv)
{
    if (mv <= OCV_MV[0]) return 0;
    if (mv >= OCV_MV[10]) return 100;
    for (int i = 1; i <= 10; ++i) {
        if (mv < OCV_MV[i]) {
            const uint32_t span = OCV_MV[i] - OCV_MV[i - 1];
            return (uint8_t)((i - 1) * 10 + (uint32_t)(mv - OCV_MV[i - 1]) * 10u / span);
        }
    }
    return 100;
}

static uint16_t read_battery_mv(void)
{
    if (!s_adc) return 0;
    int sum_mv = 0, n = 0;
    for (int i = 0; i < 8; ++i) {
        int raw = 0, mv = 0;
        if (adc_oneshot_read(s_adc, s_adc_channel, &raw) != ESP_OK) continue;
        if (s_adc_cali) {
            if (adc_cali_raw_to_voltage(s_adc_cali, raw, &mv) != ESP_OK) continue;
        } else {
            mv = raw * 3300 / 4095;   /* uncalibrated fallback */
        }
        sum_mv += mv;
        ++n;
    }
    if (n == 0) return 0;
    return (uint16_t)((uint32_t)(sum_mv / n) * SLIM4_BAT_DIVIDER_NUM / SLIM4_BAT_DIVIDER_DEN);
}

static slim4_usb_current_t read_usb_current(void)
{
    const int out1 = gpio_get_level(SLIM4_GPIO_USB_CURR_OUT1);
    const int out2 = gpio_get_level(SLIM4_GPIO_USB_CURR_OUT2);
    if (out1 && out2) return SLIM4_USB_NONE;
    if (out1 && !out2) return SLIM4_USB_DEFAULT;
    if (!out1 && out2) return SLIM4_USB_1A5;
    return SLIM4_USB_3A0;
}

/* BQ24074 input limit: EN2/EN1 = 0/1 500 mA, 1/0 ILIM (about 1.07 A with R415 1.5 k), 1/1 suspend. */
static void set_charger_mode(bool suspend, bool high_current)
{
    const int en2 = (suspend || high_current) ? 1 : 0;
    const int en1 = (suspend || !high_current) ? 1 : 0;
    gpio_set_level(SLIM4_GPIO_BQ_EN2, en2);
    gpio_set_level(SLIM4_GPIO_BQ_EN1, en1);
    s_state.input_limit_ma = suspend ? 0 : (high_current ? 1070 : 500);
}

static void update_policy(void)
{
    s_state.battery_mv = read_battery_mv();
    s_state.battery_percent = percent_from_mv(s_state.battery_mv);
    s_state.usb_power = gpio_get_level(SLIM4_GPIO_PGOOD_STATUS) == 0;
    s_state.charging = gpio_get_level(SLIM4_GPIO_CHG_STATUS) == 0;
    s_state.usb_current = read_usb_current();
    float t = 0;
    if (s_tsens && temperature_sensor_get_celsius(s_tsens, &t) == ESP_OK) s_state.chip_temp_c = (int16_t)t;
    if (!s_state.charge_suspended && s_state.chip_temp_c > CHARGE_HOT_C) {
        s_state.charge_suspended = true;
        ESP_LOGW(TAG, "die at %d C: charging suspended", s_state.chip_temp_c);
    } else if (s_state.charge_suspended && s_state.chip_temp_c < CHARGE_COOL_C) {
        s_state.charge_suspended = false;
        ESP_LOGI(TAG, "die at %d C: charging resumed", s_state.chip_temp_c);
    }
    const bool high = s_state.usb_current == SLIM4_USB_1A5 || s_state.usb_current == SLIM4_USB_3A0;
    set_charger_mode(s_state.charge_suspended, high);
    /* Without USB power the reading is the cell under load: below the threshold, switch off. */
    s_state.battery_low = s_state.battery_mv != 0 && !s_state.usb_power && s_state.battery_mv < BATTERY_EMPTY_MV;
}

slim4_status_t slim4_power_init(void)
{
    const gpio_config_t inputs = {
        .pin_bit_mask = (1ULL << SLIM4_GPIO_PWR_WAKE) | (1ULL << SLIM4_GPIO_CHG_STATUS) |
                        (1ULL << SLIM4_GPIO_PGOOD_STATUS) | (1ULL << SLIM4_GPIO_USB_CURR_OUT1) |
                        (1ULL << SLIM4_GPIO_USB_CURR_OUT2),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,   /* all pulled up on the board */
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    if (gpio_config(&inputs) != ESP_OK) return SLIM4_ERR_IO;
    /* Start at the board's reset defaults (EN2/EN1 = 0/1: 500 mA) before driving them. */
    gpio_set_level(SLIM4_GPIO_BQ_EN1, 1);
    gpio_set_level(SLIM4_GPIO_BQ_EN2, 0);
    const gpio_config_t outputs = {
        .pin_bit_mask = (1ULL << SLIM4_GPIO_BQ_EN1) | (1ULL << SLIM4_GPIO_BQ_EN2),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    if (gpio_config(&outputs) != ESP_OK) return SLIM4_ERR_IO;

    adc_unit_t unit;
    if (adc_oneshot_io_to_channel(SLIM4_GPIO_BAT_ADC, &unit, &s_adc_channel) == ESP_OK) {
        const adc_oneshot_unit_init_cfg_t unit_cfg = {.unit_id = unit};
        const adc_oneshot_chan_cfg_t chan_cfg = {.atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT};
        if (adc_oneshot_new_unit(&unit_cfg, &s_adc) == ESP_OK &&
            adc_oneshot_config_channel(s_adc, s_adc_channel, &chan_cfg) == ESP_OK) {
            const adc_cali_curve_fitting_config_t cali_cfg = {
                .unit_id = unit, .chan = s_adc_channel, .atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT,
            };
            if (adc_cali_create_scheme_curve_fitting(&cali_cfg, &s_adc_cali) != ESP_OK) {
                s_adc_cali = NULL;
                ESP_LOGW(TAG, "ADC calibration unavailable; battery voltage is approximate");
            }
        } else {
            ESP_LOGW(TAG, "battery ADC unavailable");
            s_adc = NULL;
        }
    }
    const temperature_sensor_config_t tcfg = TEMPERATURE_SENSOR_CONFIG_DEFAULT(-10, 80);
    if (temperature_sensor_install(&tcfg, &s_tsens) != ESP_OK || temperature_sensor_enable(s_tsens) != ESP_OK) {
        s_tsens = NULL;
        ESP_LOGW(TAG, "die temperature sensor unavailable");
    }
    /* A button already held at boot (the wake press) must be released before it can switch off. */
    s_button_armed = gpio_get_level(SLIM4_GPIO_PWR_WAKE) != 0;
    s_ready = true;
    update_policy();
    s_next_policy_us = esp_timer_get_time() + POLICY_PERIOD_US;
    ESP_LOGI(TAG, "battery %u mV (%u %%), usb=%d charging=%d limit=%u mA, die %d C",
             s_state.battery_mv, s_state.battery_percent, s_state.usb_power, s_state.charging,
             s_state.input_limit_ma, s_state.chip_temp_c);
    return SLIM4_OK;
}

bool slim4_power_poll(void)
{
    if (!s_ready) return false;
    const int64_t now = esp_timer_get_time();
    if (now >= s_next_policy_us) {
        update_policy();
        s_next_policy_us = now + POLICY_PERIOD_US;
    }
    const bool down = gpio_get_level(SLIM4_GPIO_PWR_WAKE) == 0;
    if (!down) {
        s_button_armed = true;
        s_button_down_since = 0;
        return false;
    }
    if (!s_button_armed) return false;
    if (s_button_down_since == 0) s_button_down_since = now;
    return now - s_button_down_since >= POWER_HOLD_US || s_state.battery_low;
}

slim4_status_t slim4_power_read(slim4_power_state_t *out)
{
    if (!out) return SLIM4_ERR_INVALID_ARG;
    if (!s_ready) return SLIM4_ERR_NOT_READY;
    *out = s_state;
    return SLIM4_OK;
}

bool slim4_power_woke_by_button(void)
{
    return (esp_sleep_get_wakeup_causes() & BIT(ESP_SLEEP_WAKEUP_EXT1)) != 0;
}

void slim4_power_off(void)
{
    ESP_LOGI(TAG, "power off: deep sleep, wake on the power button");
    slim4_board_prepare_power_off();
    /* Wait for the button to be released, so the release does not wake the board at once. */
    while (gpio_get_level(SLIM4_GPIO_PWR_WAKE) == 0) vTaskDelay(pdMS_TO_TICKS(10));
    vTaskDelay(pdMS_TO_TICKS(50));
    esp_sleep_enable_ext1_wakeup_io(1ULL << SLIM4_GPIO_PWR_WAKE, ESP_EXT1_WAKEUP_ANY_LOW);
    esp_deep_sleep_start();
}
