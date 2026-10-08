#include "slim4_system_update.h"

#include <stdbool.h>

#include "esp_err.h"
#include "esp_ota_ops.h"
#include "esp_partition.h"

static const esp_partition_t *s_target_partition;
static esp_ota_handle_t s_ota_handle;
static size_t s_expected_size;
static size_t s_written_size;
static bool s_update_active;

static void clear_session(void)
{
    s_target_partition = NULL;
    s_ota_handle = 0;
    s_expected_size = 0;
    s_written_size = 0;
    s_update_active = false;
}

slim4_status_t slim4_system_update_begin(size_t image_size)
{
    if (s_update_active || image_size == 0) return SLIM4_ERR_INVALID_ARG;

    const esp_partition_t *target = esp_ota_get_next_update_partition(NULL);
    const esp_partition_t *recovery = esp_partition_find_first(
        ESP_PARTITION_TYPE_APP, ESP_PARTITION_SUBTYPE_APP_FACTORY, NULL);
    if (!target || target == recovery || target->type != ESP_PARTITION_TYPE_APP ||
        target->subtype == ESP_PARTITION_SUBTYPE_APP_FACTORY || image_size > target->size) {
        return SLIM4_ERR_UNSUPPORTED;
    }

    esp_err_t err = esp_ota_begin(target, image_size, &s_ota_handle);
    if (err != ESP_OK) return SLIM4_ERR_IO;

    s_target_partition = target;
    s_expected_size = image_size;
    s_written_size = 0;
    s_update_active = true;
    return SLIM4_OK;
}

slim4_status_t slim4_system_update_write(const void *data, size_t length)
{
    if (!s_update_active) return SLIM4_ERR_NOT_READY;
    if (!data || length == 0 || length > s_expected_size - s_written_size) {
        return SLIM4_ERR_INVALID_ARG;
    }
    const esp_err_t err = esp_ota_write(s_ota_handle, data, length);
    if (err != ESP_OK) return SLIM4_ERR_IO;
    s_written_size += length;
    return SLIM4_OK;
}

slim4_status_t slim4_system_update_finish(void)
{
    if (!s_update_active) return SLIM4_ERR_NOT_READY;
    if (s_written_size != s_expected_size) return SLIM4_ERR_INVALID_ARG;

    const esp_err_t end_err = esp_ota_end(s_ota_handle);
    s_update_active = false;
    s_ota_handle = 0;
    if (end_err != ESP_OK) {
        s_target_partition = NULL;
        return SLIM4_ERR_IO;
    }

    const esp_err_t select_err = esp_ota_set_boot_partition(s_target_partition);
    s_target_partition = NULL;
    s_expected_size = 0;
    s_written_size = 0;
    return select_err == ESP_OK ? SLIM4_OK : SLIM4_ERR_IO;
}

slim4_status_t slim4_system_update_abort(void)
{
    if (!s_update_active) return SLIM4_ERR_NOT_READY;
    const esp_err_t err = esp_ota_abort(s_ota_handle);
    clear_session();
    return err == ESP_OK ? SLIM4_OK : SLIM4_ERR_IO;
}
