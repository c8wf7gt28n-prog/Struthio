/* Host stand-ins for the ESP-IDF calls slim4_power.c makes. The test sets GPIO levels, the battery voltage, the
 * die temperature and the clock; the policy code under test is the unmodified source file. */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

typedef int esp_err_t;
#define ESP_OK 0
#define ESP_FAIL -1
#define ESP_LOGE(tag, ...) host_log('E', __VA_ARGS__)
#define ESP_LOGW(tag, ...) host_log('W', __VA_ARGS__)
#define ESP_LOGI(tag, ...) host_log('I', __VA_ARGS__)
#ifndef BIT
#define BIT(n) (1ULL << (n))
#endif
#define pdMS_TO_TICKS(ms) (ms)

typedef enum { GPIO_MODE_INPUT, GPIO_MODE_OUTPUT } gpio_mode_t;
enum { GPIO_PULLUP_DISABLE = 0, GPIO_PULLDOWN_DISABLE = 0, GPIO_INTR_DISABLE = 0 };
typedef int gpio_num_t;
typedef struct { uint64_t pin_bit_mask; int mode, pull_up_en, pull_down_en, intr_type; } gpio_config_t;
#define GPIO_NUM_0 0
#define GPIO_NUM_1 1
#define GPIO_NUM_2 2
#define GPIO_NUM_3 3
#define GPIO_NUM_4 4
#define GPIO_NUM_5 5
#define GPIO_NUM_6 6
#define GPIO_NUM_7 7
#define GPIO_NUM_8 8
#define GPIO_NUM_9 9
#define GPIO_NUM_10 10
#define GPIO_NUM_11 11
#define GPIO_NUM_13 13
#define GPIO_NUM_16 16
#define GPIO_NUM_17 17
#define GPIO_NUM_35 35
#define GPIO_NUM_43 43
#define GPIO_NUM_44 44
#define GPIO_NUM_46 46

typedef int adc_unit_t;
typedef int adc_channel_t;
typedef void *adc_oneshot_unit_handle_t;
typedef void *adc_cali_handle_t;
typedef void *temperature_sensor_handle_t;
#define ADC_ATTEN_DB_12 3
#define ADC_BITWIDTH_DEFAULT 0
typedef struct { int unit_id; } adc_oneshot_unit_init_cfg_t;
typedef struct { int atten, bitwidth; } adc_oneshot_chan_cfg_t;
typedef struct { int unit_id, chan, atten, bitwidth; } adc_cali_curve_fitting_config_t;
typedef struct { int lo, hi; } temperature_sensor_config_t;
#define TEMPERATURE_SENSOR_CONFIG_DEFAULT(a, b) {(a), (b)}
#define ESP_SLEEP_WAKEUP_EXT1 3
#define ESP_EXT1_WAKEUP_ANY_LOW 0

/* the simulated board */
extern int host_gpio[64];
extern int host_battery_mv;     /* voltage on BAT_PLUS */
extern bool host_adc_fails;     /* every ADC read fails */
extern float host_die_c;
extern int64_t host_now_us;
extern bool host_quiet;
void host_log(char level, const char *fmt, ...);

static inline int gpio_get_level(int n) { return host_gpio[n]; }
static inline esp_err_t gpio_set_level(int n, int v) { host_gpio[n] = v; return ESP_OK; }
static inline esp_err_t gpio_config(const gpio_config_t *c) { (void)c; return ESP_OK; }
static inline esp_err_t adc_oneshot_io_to_channel(int io, adc_unit_t *u, adc_channel_t *c) { (void)io; *u = 0; *c = 0; return ESP_OK; }
static inline esp_err_t adc_oneshot_new_unit(const adc_oneshot_unit_init_cfg_t *c, adc_oneshot_unit_handle_t *h) { (void)c; *h = (void *)1; return ESP_OK; }
static inline esp_err_t adc_oneshot_config_channel(adc_oneshot_unit_handle_t h, adc_channel_t c, const adc_oneshot_chan_cfg_t *x) { (void)h; (void)c; (void)x; return ESP_OK; }
static inline esp_err_t adc_cali_create_scheme_curve_fitting(const adc_cali_curve_fitting_config_t *c, adc_cali_handle_t *h) { (void)c; *h = (void *)1; return ESP_OK; }
/* raw = pin millivolts: BAT_PLUS x 33 k / 133 k */
static inline esp_err_t adc_oneshot_read(adc_oneshot_unit_handle_t h, adc_channel_t c, int *raw) { (void)h; (void)c; if (host_adc_fails) return ESP_FAIL; *raw = host_battery_mv * 33 / 133; return ESP_OK; }
static inline esp_err_t adc_cali_raw_to_voltage(adc_cali_handle_t h, int raw, int *mv) { (void)h; *mv = raw; return ESP_OK; }
static inline esp_err_t temperature_sensor_install(const temperature_sensor_config_t *c, temperature_sensor_handle_t *h) { (void)c; *h = (void *)1; return ESP_OK; }
static inline esp_err_t temperature_sensor_enable(temperature_sensor_handle_t h) { (void)h; return ESP_OK; }
static inline esp_err_t temperature_sensor_get_celsius(temperature_sensor_handle_t h, float *t) { (void)h; *t = host_die_c; return ESP_OK; }
static inline int64_t esp_timer_get_time(void) { return host_now_us; }
static inline uint64_t esp_sleep_get_wakeup_causes(void) { return 0; }
static inline esp_err_t esp_sleep_enable_ext1_wakeup_io(uint64_t m, int l) { (void)m; (void)l; return ESP_OK; }
static inline void esp_deep_sleep_start(void) {}
static inline void vTaskDelay(int ticks) { host_now_us += (int64_t)ticks * 1000; }
