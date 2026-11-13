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
#define BATTERY_LOW_PERIODS   4               /* 2 s below BATTERY_EMPTY_MV, so a load step does not switch off */
#define CHARGE_HOT_C          75              /* suspend charging above this die temperature */
#define CHARGE_COOL_C         65              /* resume below this */
#define SUSPEND_MIN_MV        3600u           /* enter (and stay in) a suspend only above this: the cell carries the system */
#define POLICY_PERIOD_US      (500 * 1000)
/* Leaving a USB suspend restarts the BQ24074's safety timers (datasheet 9.3.5.6), so a device that keeps getting hot
 * would get a new 4-6 h fast-charge window after every heat suspend. The firmware therefore counts charge time over
 * the whole USB session; once a suspend has restarted the charger's timer and the count reaches the timer's longest
 * window, charging stops (USB suspend) until the cell falls to SUSPEND_MIN_MV (a new charge, as the charger's own
 * recharge would start) or USB is unplugged. */
#define CHARGE_TOTAL_US       (6LL * 3600 * 1000 * 1000)

/* Backlight cap on a 500 mA USB source with no charge cycle running (no cell known to supplement).
 * BQ24074 USB500 input limit 450 mA min, OUT 4.4 V: 1.98 W. 3.3 V rail at Espressif's 380 mA design provision
 * plus 44 mA panel logic, through the TPS63070 at 90 %: 1.55 W. That leaves 0.43 W; through the TPS61165 at
 * 80 % into a 24.2 V string that is 14 mA, 19 % of the 74 mA full scale. 15 % (11 mA, 0.34 W) keeps 4 % margin. */
#define BL_CAP_USB500_PERCENT 15u
/* The cap lifts on 500 mA USB only for a cell that can supplement: charging, no rail fault, a valid reading at or
 * above CELL_OK_MV for CELL_OK_PERIODS (2 s); it returns below CELL_OK_RELEASE_MV, when charging stops, on a fault
 * or when the reading fails. CHG low alone is not enough: it is also low in pre-charge (cell below 3.0 V). */
#define CELL_OK_MV            3500u
#define CELL_OK_RELEASE_MV    3400u
#define CELL_OK_PERIODS       4
/* Audio on the same source: after the 3.3 V rail and the capped backlight, 1.98 - 1.55 - 0.34 = 0.09 W remain. Two
 * MAX98357A at 12 dB gain from SYS_RAW draw about 21 mW idle between them and can clip at full scale into 4 ohm, so no
 * volume setting can be shown to fit: while the backlight cap is on, the amplifiers are held in shutdown (muted). */
#define BATTERY_FAULT_MV      1500u           /* below the charger's 1.8 V short-circuit check: no cell can be there */
#define BATTERY_FAULT_PERIODS 3               /* 1.5 s */

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
static uint8_t s_fault_count;
static uint8_t s_low_count;
static uint8_t s_cell_ok_count;
static bool s_cell_ok;
static bool s_adc_valid;              /* the last battery reading succeeded */
static bool s_adc_warned;
static bool s_approx_warned;
static int64_t s_last_policy_us;      /* 0 before the first pass */
static int64_t s_charge_us;           /* charge time (CHG low, not suspended) in this USB session */
static bool s_timer_restarted;        /* a firmware suspend has restarted the charger's safety timer in this session */

static uint8_t count_up(uint8_t n) { return n < 255 ? n + 1 : 255; }

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
    s_adc_valid = false;
    if (!s_adc) return 0;
    int sum_mv = 0, n = 0;
    for (int i = 0; i < 8; ++i) {
        int raw = 0, mv = 0;
        if (adc_oneshot_read(s_adc, s_adc_channel, &raw) != ESP_OK) continue;
        if (s_adc_cali) {
            if (adc_cali_raw_to_voltage(s_adc_cali, raw, &mv) != ESP_OK) continue;
        } else {
            mv = raw * 3300 / 4095;   /* uncalibrated: for display only (battery_approx), never for a decision */
        }
        sum_mv += mv;
        ++n;
    }
    if (n == 0) return 0;
    s_adc_valid = true;
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
    /* Only a calibrated reading drives a decision. Without the eFuse calibration the raw conversion can be off by
     * more than the margins below (3.3 V switch-off, 3.5/3.6 V cell checks), so it is shown but treated as no reading. */
    s_state.battery_approx = s_adc_valid && !s_adc_cali;
    const bool adc = s_adc_valid && s_adc_cali;
    const uint16_t mv = s_state.battery_mv;
    if (s_state.battery_approx && !s_approx_warned) {
        s_approx_warned = true;
        ESP_LOGW(TAG, "battery reading uncalibrated (about %u mV): shown only; treated as no reading for power decisions", mv);
    }
    if (!adc && !s_adc_warned) {
        s_adc_warned = true;
        ESP_LOGW(TAG, "no usable battery reading: no low-battery switch-off (the pack's protection board still cuts off), "
                      "backlight held to %u %% and audio muted on 500 mA USB, no charge suspend", (unsigned)BL_CAP_USB500_PERCENT);
    }

    /* A reversed (or shorted) pack on USB holds BAT_PLUS near Q2's threshold (0.5-1.3 V): the charger stays in its
     * short-circuit check (4-11 mA). No cell or a good cell never sits there for 1.5 s. */
    s_fault_count = (s_state.usb_power && adc && mv < BATTERY_FAULT_MV) ? count_up(s_fault_count) : 0;
    const bool fault = s_fault_count >= BATTERY_FAULT_PERIODS;
    if (fault && !s_state.battery_fault) {
        ESP_LOGE(TAG, "battery rail %u mV on USB: pack reversed or shorted - unplug it", mv);
    }
    s_state.battery_fault = fault;

    /* A cell that can carry the system: see CELL_OK_MV. */
    const bool cell_now = s_state.charging && !fault && adc;
    if (cell_now && mv >= CELL_OK_MV) {
        s_cell_ok_count = count_up(s_cell_ok_count);
        if (s_cell_ok_count >= CELL_OK_PERIODS) s_cell_ok = true;
    } else if (!cell_now || mv < CELL_OK_RELEASE_MV) {
        s_cell_ok_count = 0;
        s_cell_ok = false;
    }

    /* Charge time in this USB session (CHARGE_TOTAL_US). */
    const int64_t now = esp_timer_get_time();
    const int64_t dt = s_last_policy_us ? now - s_last_policy_us : 0;
    s_last_policy_us = now;
    if (!s_state.usb_power) {
        s_charge_us = 0;
        s_timer_restarted = false;
    } else if (s_state.charging && !s_state.charge_suspended) {
        s_charge_us += dt;
    }

    /* The BQ24074's CE pin is tied low, so the only way to stop charging is USB suspend (EN2/EN1 = 1/1), which also
     * takes the system off USB. Enter it only with a qualified cell above SUSPEND_MIN_MV: for heat, or when the
     * session's charge time is spent. Leave it when the die has cooled (a heat suspend), the cell falls below
     * SUSPEND_MIN_MV, the reading fails or USB goes away. */
    const bool time_spent = s_timer_restarted && s_charge_us >= CHARGE_TOTAL_US;
    if (!s_state.charge_suspended) {
        const bool hot = s_state.chip_temp_c > CHARGE_HOT_C;
        if ((hot || time_spent) && s_state.usb_power && s_cell_ok && mv >= SUSPEND_MIN_MV) {
            s_state.charge_suspended = true;
            s_state.charge_time_limit = time_spent;
            if (time_spent) {
                ESP_LOGW(TAG, "%u min of charging across suspends: charging stopped until the cell is down to %u mV "
                              "or USB is unplugged (system on the cell, %u mV)",
                         (unsigned)(s_charge_us / 60000000), (unsigned)SUSPEND_MIN_MV, mv);
            } else {
                ESP_LOGW(TAG, "die at %d C: charging suspended (system on the cell, %u mV)", s_state.chip_temp_c, mv);
            }
        }
    } else if ((!s_state.charge_time_limit && s_state.chip_temp_c < CHARGE_COOL_C) || !adc || mv < SUSPEND_MIN_MV ||
               !s_state.usb_power) {
        s_state.charge_suspended = false;
        if (s_state.charge_time_limit) {
            s_charge_us = 0;              /* a new charge with a fresh timer of the charger's own */
            s_timer_restarted = false;
        } else {
            s_timer_restarted = s_state.usb_power;
        }
        s_state.charge_time_limit = false;
        ESP_LOGI(TAG, "die at %d C, cell %u mV: charging resumed", s_state.chip_temp_c, mv);
    }
    const bool high = s_state.usb_current == SLIM4_USB_1A5 || s_state.usb_current == SLIM4_USB_3A0;
    set_charger_mode(s_state.charge_suspended, high);

    /* Without USB power the reading is the cell under load: below the threshold for 2 s, switch off. */
    s_low_count = (adc && !s_state.usb_power && mv < BATTERY_EMPTY_MV) ? count_up(s_low_count) : 0;
    s_state.battery_low = s_low_count >= BATTERY_LOW_PERIODS;

    /* On USB below 1 A (500 mA, or suspended) only a qualified cell lifts the cap; during a suspend the cap also
     * cuts heat. */
    const uint8_t cap = (s_state.usb_power && s_state.input_limit_ma < 1000 && !(s_cell_ok && !s_state.charge_suspended))
                            ? BL_CAP_USB500_PERCENT : 100;
    if (cap != s_state.backlight_cap_percent) {
        s_state.backlight_cap_percent = cap;
        ESP_LOGI(TAG, "backlight limited to %u %% (%s)", cap,
                 cap < 100 ? "USB below 1 A, no qualified cell" : "battery, qualified cell or 1.5/3 A USB-C");
        slim4_board_backlight_cap_changed(cap);
    }
    const bool mute = cap < 100;
    if (mute != s_state.audio_muted) {
        s_state.audio_muted = mute;
        ESP_LOGI(TAG, "audio %s", mute ? "muted (USB below 1 A, no qualified cell)" : "enabled");
        slim4_board_audio_power_mute(mute);
    }
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
    ESP_LOGI(TAG, "battery %u mV (%u %%), usb=%d charging=%d limit=%u mA, backlight cap %u %%, die %d C",
             s_state.battery_mv, s_state.battery_percent, s_state.usb_power, s_state.charging,
             s_state.input_limit_ma, s_state.backlight_cap_percent, s_state.chip_temp_c);
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
    /* A qualified empty cell switches off whatever the button is doing. */
    if (s_state.battery_low) return true;
    const bool down = gpio_get_level(SLIM4_GPIO_PWR_WAKE) == 0;
    if (!down) {
        s_button_armed = true;
        s_button_down_since = 0;
        return false;
    }
    if (!s_button_armed) return false;
    if (s_button_down_since == 0) s_button_down_since = now;
    return now - s_button_down_since >= POWER_HOLD_US;
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
