// STRUTHIO HANDHELD · a host-only stand-in for the ESP-IDF 5.x declarations
// main/ uses, so `make -C firmware/host_test compile` type-checks the firmware
// without the Xtensa toolchain. It proves our code is self-consistent against
// these signatures; it does NOT replace a real `idf.py build`.
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_ERR_NVS_NO_FREE_PAGES 0x110d
#define ESP_ERR_NVS_NEW_VERSION_FOUND 0x1110
#define ESP_ERROR_CHECK(x) do { esp_err_t err_ = (x); (void)err_; } while (0)
// FreeRTOS
typedef uint32_t TickType_t;
typedef int BaseType_t;
typedef unsigned UBaseType_t;
typedef void *TaskHandle_t;
typedef void (*TaskFunction_t)(void *);
typedef struct { volatile uint32_t owner; uint32_t count; } portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED {0, 0}
#define portMAX_DELAY ((TickType_t)0xffffffffUL)
#define pdTRUE 1
#define pdMS_TO_TICKS(ms) ((TickType_t)(ms))
#define configASSERT(x) do { if (!(x)) for (;;) {} } while (0)
void vPortEnterCritical(portMUX_TYPE *m);
void vPortExitCritical(portMUX_TYPE *m);
#define portENTER_CRITICAL(m) vPortEnterCritical(m)
#define portEXIT_CRITICAL(m) vPortExitCritical(m)
void vTaskDelay(const TickType_t ticks);
BaseType_t xTaskCreatePinnedToCore(TaskFunction_t fn, const char *name, const uint32_t stack, void *arg, UBaseType_t prio, TaskHandle_t *out, const BaseType_t core);
uint32_t ulTaskNotifyTake(BaseType_t clear, TickType_t wait);
#define xTaskNotifyGive(t) xTaskGenericNotify_shim(t)
BaseType_t xTaskGenericNotify_shim(TaskHandle_t t);
typedef void *SemaphoreHandle_t;
SemaphoreHandle_t xSemaphoreCreateMutex(void);
SemaphoreHandle_t xSemaphoreCreateBinary(void);
BaseType_t xSemaphoreTake(SemaphoreHandle_t s, TickType_t wait);
BaseType_t xSemaphoreGive(SemaphoreHandle_t s);
// partitions
typedef enum { ESP_PARTITION_TYPE_APP = 0, ESP_PARTITION_TYPE_DATA = 1 } esp_partition_type_t;
typedef int esp_partition_subtype_t;
typedef struct { esp_partition_type_t type; esp_partition_subtype_t subtype; uint32_t address, size; char label[17]; } esp_partition_t;
typedef enum { ESP_PARTITION_MMAP_DATA = 0, ESP_PARTITION_MMAP_INST = 1 } esp_partition_mmap_memory_t;
typedef uint32_t esp_partition_mmap_handle_t;
const esp_partition_t *esp_partition_find_first(esp_partition_type_t type, esp_partition_subtype_t subtype, const char *label);
esp_err_t esp_partition_mmap(const esp_partition_t *p, size_t offset, size_t size, esp_partition_mmap_memory_t memory,
                             const void **out_ptr, esp_partition_mmap_handle_t *out_handle);
// GPIO
typedef int gpio_num_t;
typedef enum { GPIO_MODE_INPUT = 1 } gpio_mode_t;
typedef enum { GPIO_PULLUP_DISABLE = 0, GPIO_PULLUP_ENABLE = 1 } gpio_pullup_t;
typedef enum { GPIO_PULLDOWN_DISABLE = 0, GPIO_PULLDOWN_ENABLE = 1 } gpio_pulldown_t;
typedef enum { GPIO_INTR_DISABLE = 0 } gpio_int_type_t;
typedef struct { uint64_t pin_bit_mask; gpio_mode_t mode; gpio_pullup_t pull_up_en; gpio_pulldown_t pull_down_en; gpio_int_type_t intr_type; } gpio_config_t;
esp_err_t gpio_config(const gpio_config_t *cfg);
int gpio_get_level(gpio_num_t pin);
// heap caps
#define MALLOC_CAP_DMA (1 << 3)
#define MALLOC_CAP_8BIT (1 << 2)
#define MALLOC_CAP_SPIRAM (1 << 10)
#define MALLOC_CAP_INTERNAL (1 << 11)
void *heap_caps_malloc(size_t size, uint32_t caps);
size_t heap_caps_get_free_size(uint32_t caps);
// log
#define ESP_LOGI(tag, fmt, ...) esp_log_shim(tag, fmt, ##__VA_ARGS__)
#define ESP_LOGW(tag, fmt, ...) esp_log_shim(tag, fmt, ##__VA_ARGS__)
void esp_log_shim(const char *tag, const char *fmt, ...) __attribute__((format(printf, 2, 3)));
// misc
uint32_t esp_random(void);
esp_err_t esp_task_wdt_add(TaskHandle_t task);
esp_err_t esp_task_wdt_reset(void);
int64_t esp_timer_get_time(void);
typedef enum { ESP_RST_UNKNOWN = 0 } esp_reset_reason_t;
esp_reset_reason_t esp_reset_reason(void);
// NVS
typedef uint32_t nvs_handle_t;
typedef enum { NVS_READONLY, NVS_READWRITE } nvs_open_mode_t;
esp_err_t nvs_flash_init(void);
esp_err_t nvs_flash_erase(void);
esp_err_t nvs_open(const char *ns, nvs_open_mode_t mode, nvs_handle_t *out);
esp_err_t nvs_get_i32(nvs_handle_t h, const char *key, int32_t *out);
esp_err_t nvs_set_i32(nvs_handle_t h, const char *key, int32_t v);
esp_err_t nvs_commit(nvs_handle_t h);
void nvs_close(nvs_handle_t h);
// esp_lcd
typedef struct esp_lcd_panel_t *esp_lcd_panel_handle_t;
esp_err_t esp_lcd_panel_draw_bitmap(esp_lcd_panel_handle_t panel, int x_start, int y_start, int x_end, int y_end, const void *color_data);
