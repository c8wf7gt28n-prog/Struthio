#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum {
    SLIM4_OK = 0,
    SLIM4_ERR_NOT_READY,
    SLIM4_ERR_INVALID_ARG,
    SLIM4_ERR_UNSUPPORTED,
    SLIM4_ERR_IO,
} slim4_status_t;

typedef struct {
    uint16_t width;
    uint16_t height;
    uint16_t stride_bytes;
    uint16_t *pixels_rgb565;
} slim4_surface_t;
