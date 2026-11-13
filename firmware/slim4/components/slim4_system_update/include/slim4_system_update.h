#pragma once

#include <stddef.h>
#include <stdint.h>
#include "slim4_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Transport-neutral A/B system-image writer. The factory recovery image is never selected as a target. */
slim4_status_t slim4_system_update_begin(size_t image_size);
slim4_status_t slim4_system_update_write(const void *data, size_t length);
slim4_status_t slim4_system_update_finish(void);
slim4_status_t slim4_system_update_abort(void);

#ifdef __cplusplus
}
#endif
