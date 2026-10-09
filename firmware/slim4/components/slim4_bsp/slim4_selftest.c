/* SLIM4 self-test, ESP-IDF side: the GPIO measurements, chip identity, memory, reset reason and power readings.
 * The panel probe runs inside the display bring-up (slim4_board.c). What the readings mean is decided in
 * slim4_selftest_logic.c.
 *
 * Every GPIO step is safe for the board as built and as faulted: pins are driven only at U1's weakest drive
 * strength, for microseconds (PWR_WAKE: a few milliseconds, like a short press of SW5), never against a net that
 * something else holds, and never on BQ_EN1/BQ_EN2 (the charger's input-limit pins). */
#include "slim4_selftest.h"

#include <limits.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/usb_serial_jtag.h"
#include "esp_chip_info.h"
#include "esp_flash.h"
#include "esp_log.h"
#include "esp_psram.h"
#include "esp_rom_sys.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "slim4_board.h"
#include "slim4_power.h"

static const char *TAG = "slim4_selftest";
static const slim4_st_report_t *s_last;
static slim4_pull_result_t s_pull[SLIM4_ST_MAX_PINS];
static slim4_short_scan_t s_scan[2];

#define RELEASE_WAIT_US     5000000   /* time given to let go of the controls before the checks */
#define SETTLE_10K_US       1000      /* a 10 k or 45 k pull into the pad and trace capacitance: well under 1 us */
#define SETTLE_RC_US        10000     /* PWR_WAKE: R110 10 k with C601 100 nF, tau 1 ms */
#define PRECHARGE_US        20
#define PRECHARGE_RC_US     3000      /* discharge C601 through the pin */
#define RELEASED_READ_US    200       /* R308 100 k into Q1's gate (50 pF): tau 5 us */
#define RC_LIMIT_US         20000
#define DRIVE_SETTLE_US     50
#define DRIVE_SETTLE_RC_US  1000      /* 100 nF at the weakest drive (about 5 mA): 3.3 V in under 0.1 ms */
#define CAP_RECOVER_US      30000     /* C603 back to the battery divider's level: 25 k x 100 nF, 12 tau */
#define RECOVER_LIMIT_US    20000

static void wait_us(uint32_t us)
{
    if (us >= 2000) vTaskDelay(pdMS_TO_TICKS((us + 999) / 1000));
    else esp_rom_delay_us(us);
}

static gpio_num_t gpio_of(size_t i)
{
    return (gpio_num_t)SLIM4_ST_PINS[i].gpio;
}

static void set_input(gpio_num_t g, gpio_pull_mode_t pull)
{
    (void)gpio_set_direction(g, GPIO_MODE_INPUT);
    (void)gpio_set_pull_mode(g, pull);
}

/* Drive a level: the output register first, then the output enable, so the pin never shows the other level. */
static void drive(gpio_num_t g, int level)
{
    (void)gpio_set_level(g, level);
    (void)gpio_set_direction(g, GPIO_MODE_INPUT_OUTPUT);
}

static gpio_pull_mode_t pull_toward(int level)
{
    return level ? GPIO_PULLUP_ONLY : GPIO_PULLDOWN_ONLY;
}

static void configure_pins(void)
{
    for (size_t i = 0; i < SLIM4_ST_PIN_COUNT; ++i) {
        const gpio_config_t cfg = {
            .pin_bit_mask = 1ULL << gpio_of(i),
            .mode = GPIO_MODE_INPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        (void)gpio_config(&cfg);   /* also takes GPIO0 back from the LP domain after a deep-sleep wake */
        (void)gpio_set_drive_capability(gpio_of(i), GPIO_DRIVE_CAP_0);
    }
}

/* The pins as after reset: inputs with the board's pulls only. Pads with no pull on the board (I2S, unused) get
 * ESP-IDF's reset state. */
static void restore_pins(void)
{
    for (size_t i = 0; i < SLIM4_ST_PIN_COUNT; ++i) {
        const slim4_pin_desc_t *p = &SLIM4_ST_PINS[i];
        if (p->role == SLIM4_ROLE_SIGNAL || p->role == SLIM4_ROLE_UNUSED) {
            (void)gpio_reset_pin(gpio_of(i));
        } else {
            set_input(gpio_of(i), GPIO_FLOATING);
        }
        (void)gpio_set_drive_capability(gpio_of(i), GPIO_DRIVE_CAP_DEFAULT);
    }
}

/* A control held at boot (the wake press on SW5, a thumb on a flap) would read as a fault: wait for release. */
static void wait_for_release(void)
{
    for (size_t i = 0; i < SLIM4_ST_PIN_COUNT; ++i) {
        if (SLIM4_ST_PINS[i].role == SLIM4_ROLE_SWITCH) set_input(gpio_of(i), GPIO_PULLUP_ONLY);
    }
    wait_us(SETTLE_RC_US);
    const int64_t start = esp_timer_get_time();
    bool told = false;
    for (;;) {
        bool any_low = false;
        for (size_t i = 0; i < SLIM4_ST_PIN_COUNT; ++i) {
            if (SLIM4_ST_PINS[i].role == SLIM4_ROLE_SWITCH && gpio_get_level(gpio_of(i)) == 0) any_low = true;
        }
        if (!any_low || esp_timer_get_time() - start >= RELEASE_WAIT_US) break;
        if (!told) {
            ESP_LOGW(TAG, "release every control: the self-test reads the buttons' pull-ups");
            told = true;
        }
        vTaskDelay(pdMS_TO_TICKS(20));
    }
    for (size_t i = 0; i < SLIM4_ST_PIN_COUNT; ++i) {
        if (SLIM4_ST_PINS[i].role == SLIM4_ROLE_SWITCH) set_input(gpio_of(i), GPIO_FLOATING);
    }
}

static slim4_pull_reading_t pull_check(const slim4_pin_desc_t *p)
{
    slim4_pull_reading_t r = {.same = -1, .opposite = -1, .released = -1, .rise_us = -1};
    const gpio_num_t g = (gpio_num_t)p->gpio;
    const int rest = slim4_st_rest_level(p);
    const uint32_t settle = p->rc_timed ? SETTLE_RC_US : SETTLE_10K_US;

    set_input(g, pull_toward(rest));
    wait_us(settle);
    r.same = (int8_t)gpio_get_level(g);
    if (r.same != rest) {
        set_input(g, GPIO_FLOATING);
        return r;   /* held by something on the board: never drive against it */
    }
    if (slim4_st_opposite_allowed(p)) {
        set_input(g, pull_toward(!rest));
        wait_us(settle);
        r.opposite = (int8_t)gpio_get_level(g);
    }
    set_input(g, GPIO_FLOATING);
    if (p->drive_ok) {
        drive(g, !rest);
        wait_us(p->rc_timed ? PRECHARGE_RC_US : PRECHARGE_US);
        if (p->rc_timed) {
            const int64_t t0 = esp_timer_get_time();
            (void)gpio_set_direction(g, GPIO_MODE_INPUT);
            int32_t rise = INT32_MAX;
            for (;;) {
                const int64_t dt = esp_timer_get_time() - t0;
                if (gpio_get_level(g) == rest) {
                    rise = (int32_t)dt;
                    break;
                }
                if (dt >= RC_LIMIT_US) break;
                esp_rom_delay_us(5);
            }
            r.rise_us = rise;
            r.released = (int8_t)gpio_get_level(g);
            wait_us(SETTLE_RC_US);
        } else {
            (void)gpio_set_direction(g, GPIO_MODE_INPUT);
            esp_rom_delay_us(RELEASED_READ_US);
            r.released = (int8_t)gpio_get_level(g);
        }
    }
    if (p->role == SLIM4_ROLE_STATUS && r.released >= 0 && r.released != rest) {
        /* A status output can switch on during the check (U10's CHG toggles while it looks for a cell): look again
         * with U1's pull. Asserted now means it was the chip, not an open pad. */
        set_input(g, pull_toward(rest));
        wait_us(settle);
        const int8_t now = (int8_t)gpio_get_level(g);
        if (now != rest) r.same = now;
    }
    set_input(g, GPIO_FLOATING);
    return r;
}

/* Waits until every victim reads its rest level again (a short to C601 recharges through 10 k). */
static void wait_victims_settled(const slim4_short_scan_t *scan, size_t n)
{
    const int64_t t0 = esp_timer_get_time();
    for (;;) {
        bool settled = true;
        for (size_t v = 0; v < n && settled; ++v) {
            if (scan->baseline[v] >= 0 && gpio_get_level(gpio_of(v)) != scan->baseline[v]) settled = false;
        }
        if (settled || esp_timer_get_time() - t0 >= RECOVER_LIMIT_US) return;
        esp_rom_delay_us(50);
    }
}

static void short_scan(slim4_short_scan_t *scan, size_t n)
{
    slim4_st_scan_init(scan);
    bool victim[SLIM4_ST_MAX_PINS];
    for (size_t i = 0; i < n; ++i) {
        const slim4_pin_desc_t *p = &SLIM4_ST_PINS[i];
        victim[i] = slim4_st_is_victim(p, s_pull[i]);
        const int rest = slim4_st_rest_level(p);
        /* Each victim rests where its board pull puts it, with U1's pull helping; a pad with no pull on the board
         * rests low on U1's pull-down. BAT_ADC (an analog node) gets no pull. */
        if (p->role == SLIM4_ROLE_ANALOG) set_input(gpio_of(i), GPIO_FLOATING);
        else set_input(gpio_of(i), rest >= 0 ? pull_toward(rest) : GPIO_PULLDOWN_ONLY);
    }
    wait_us(SETTLE_RC_US * 2);
    for (size_t i = 0; i < n; ++i) scan->baseline[i] = victim[i] ? (int8_t)gpio_get_level(gpio_of(i)) : -1;

    for (size_t a = 0; a < n; ++a) {
        const slim4_pin_desc_t *p = &SLIM4_ST_PINS[a];
        bool high = false, low = false;
        slim4_st_drive_plan(p, s_pull[a], scan->baseline[a], &high, &low);
        const uint32_t settle = p->capacitor ? DRIVE_SETTLE_RC_US : DRIVE_SETTLE_US;
        for (int level = 1; level >= 0; --level) {
            if ((level && !high) || (!level && !low)) continue;
            drive(gpio_of(a), level);
            esp_rom_delay_us(settle);
            int8_t *row = level ? scan->when_high[a] : scan->when_low[a];
            for (size_t v = 0; v < n; ++v) {
                if (v != a && scan->baseline[v] >= 0) row[v] = (int8_t)gpio_get_level(gpio_of(v));
            }
            const int8_t self = (int8_t)gpio_get_level(gpio_of(a));
            if (level) scan->readback_high[a] = self;
            else scan->readback_low[a] = self;
            (void)gpio_set_direction(gpio_of(a), GPIO_MODE_INPUT);   /* back to its rest pull */
            wait_victims_settled(scan, n);
        }
    }
}

void slim4_selftest_pins(slim4_st_report_t *rep)
{
    const size_t n = SLIM4_ST_PIN_COUNT;
    if (n > SLIM4_ST_MAX_PINS) {
        slim4_st_add(rep, "PINS", SLIM4_ST_FAIL, "PIN TABLE TOO LARGE", "firmware fault: %u pins, at most %u",
                     (unsigned)n, (unsigned)SLIM4_ST_MAX_PINS);
        return;
    }
    const int64_t t0 = esp_timer_get_time();
    configure_pins();
    wait_for_release();
    for (size_t i = 0; i < n; ++i) {
        const slim4_pin_desc_t *p = &SLIM4_ST_PINS[i];
        if (!slim4_st_has_pull_check(p)) {
            s_pull[i] = SLIM4_PULL_OK;
            continue;
        }
        const slim4_pull_reading_t r = pull_check(p);
        s_pull[i] = slim4_st_classify_pull(p, &r);
        (void)slim4_st_report_pull(rep, p, &r);
    }
    short_scan(&s_scan[0], n);
    short_scan(&s_scan[1], n);
    slim4_st_report_shorts(rep, n, &s_scan[0], &s_scan[1]);
    restore_pins();
    wait_us(CAP_RECOVER_US);
    s_last = rep;   /* the power service's first battery reading follows soon after */
    ESP_LOGI(TAG, "GPIO checks took %lld ms", (long long)((esp_timer_get_time() - t0) / 1000));
}

static const char *reset_name(esp_reset_reason_t r)
{
    switch (r) {
    case ESP_RST_POWERON: return "POWER-ON";
    case ESP_RST_EXT: return "EXTERNAL PIN";
    case ESP_RST_SW: return "SOFTWARE";
    case ESP_RST_PANIC: return "PANIC";
    case ESP_RST_INT_WDT: return "INTERRUPT WATCHDOG";
    case ESP_RST_TASK_WDT: return "TASK WATCHDOG";
    case ESP_RST_WDT: return "WATCHDOG";
    case ESP_RST_DEEPSLEEP: return "DEEP-SLEEP WAKE";
    case ESP_RST_BROWNOUT: return "BROWNOUT";
    case ESP_RST_SDIO: return "SDIO";
    case ESP_RST_USB: return "USB";
    case ESP_RST_JTAG: return "JTAG";
    case ESP_RST_EFUSE: return "EFUSE";
    case ESP_RST_PWR_GLITCH: return "POWER GLITCH";
    case ESP_RST_CPU_LOCKUP: return "CPU LOCKUP";
    default: return "UNKNOWN";
    }
}

void slim4_selftest_after_init(slim4_st_report_t *rep, bool display_ready)
{
    esp_chip_info_t chip;
    esp_chip_info(&chip);
    slim4_st_judge_chip(rep, chip.revision);
    slim4_st_judge_psram(rep, esp_psram_get_size());
    uint32_t flash_id = 0, flash_bytes = 0;
    const bool id_ok = esp_flash_read_id(NULL, &flash_id) == ESP_OK;
    const bool size_ok = esp_flash_get_physical_size(NULL, &flash_bytes) == ESP_OK;
    slim4_st_judge_flash(rep, id_ok, flash_id, size_ok, flash_bytes);
    const esp_reset_reason_t reason = esp_reset_reason();
    slim4_st_judge_reset(rep, reason == ESP_RST_BROWNOUT || reason == ESP_RST_PWR_GLITCH, reset_name(reason));

    slim4_panel_probe_t probe;
    slim4_board_panel_probe(&probe);
    slim4_st_judge_panel(rep, &probe);
    if (slim4_board_backlight_failed()) {
        slim4_st_add(rep, "BACKLIGHT", SLIM4_ST_FAIL, "BACKLIGHT PWM SETUP FAILED", "the LEDC timer for GPIO9 "
                     "(U7 TPS61165 CTRL) could not be set up: a firmware fault; the screen stays dark");
    }
    if (display_ready) {
        const uint32_t c0 = slim4_board_get_vsync_count();
        vTaskDelay(pdMS_TO_TICKS(500));
        const uint32_t c1 = slim4_board_get_vsync_count();
        slim4_st_judge_vsync(rep, true, (c1 - c0) * 2u);
    }

    slim4_power_state_t ps;
    slim4_st_power_t p = {0};
    p.ready = slim4_power_read(&ps) == SLIM4_OK;
    if (p.ready) {
        p.usb_host_seen = usb_serial_jtag_is_connected();
        p.pgood_low = ps.usb_power;
        p.charging = ps.charging;
        p.usb_current = (uint8_t)ps.usb_current;
        p.battery_mv = ps.battery_mv;
        p.battery_fault = ps.battery_fault;
        p.battery_approx = ps.battery_approx;
        p.die_c = ps.chip_temp_c;
    }
    slim4_st_judge_power(rep, &p);
    s_last = rep;
}

void slim4_selftest_log(const slim4_st_report_t *rep)
{
    slim4_selftest_log_lines(rep, 0);
    if (rep->overflow) ESP_LOGW(TAG, "SELFTEST more results than lines: the counts below include them");
    if (rep->fail) {
        ESP_LOGE(TAG, "SELFTEST RESULT: %u FAIL, %u PASS, %u INFO", rep->fail, rep->pass, rep->info);
    } else {
        ESP_LOGI(TAG, "SELFTEST RESULT: no FAIL, %u PASS, %u INFO", rep->pass, rep->info);
    }
}

void slim4_selftest_log_lines(const slim4_st_report_t *rep, uint8_t first)
{
    for (uint8_t i = first; i < rep->count; ++i) {
        const slim4_st_item_t *it = &rep->items[i];
        if (it->verdict == SLIM4_ST_FAIL) {
            ESP_LOGE(TAG, "SELFTEST FAIL %-14s %s: %s", it->id, it->brief, it->detail);
        } else if (it->verdict == SLIM4_ST_INFO) {
            ESP_LOGW(TAG, "SELFTEST INFO %-14s %s: %s", it->id, it->brief, it->detail);
        } else {
            ESP_LOGI(TAG, "SELFTEST PASS %-14s %s: %s", it->id, it->brief, it->detail);
        }
    }
}

const slim4_st_report_t *slim4_selftest_last(void)
{
    return s_last;
}
