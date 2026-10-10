#pragma once
#include <stdint.h>
#include "esp_lcd_ili9881c.h"

/* Crystalfontz CFAF7201280A0-050TN: 5 in 720 x 1280 IPS, ILI9881C, driven on 2 MIPI-DSI lanes.
 * Timing from the vendor's Linux mode: 78 MHz pixel clock, H 720 + FP 120 / SW 2 / BP 80,
 * V 1280 + FP 60 / SW 2 / BP 90 -> 59.1 Hz. RGB565 on 2 lanes needs 624 Mbit/s per lane; the bus runs 1000. */
#define SLIM4_PANEL_H_RES 720
#define SLIM4_PANEL_V_RES 1280
#define SLIM4_PANEL_DSI_LANES 2
#define SLIM4_PANEL_LANE_MBPS 1000
#define SLIM4_PANEL_PIXEL_MHZ 78
/* Fast profile (above): Espressif's 2-lane setting, above the ILI9881C datasheet's limits; chosen with the console's
 * `display fast`. Safe profile (the default): RGB565 on 2 lanes at 60 MHz needs 480 Mbit/s per lane; 560 stays inside
 * the 2-lane limit (566 Mbit/s for 16-bit pixels). */
#define SLIM4_PANEL_SAFE_LANE_MBPS 560
#define SLIM4_PANEL_SAFE_PIXEL_MHZ 60
#define SLIM4_PANEL_DPI_CONFIG(fmt) {                    \
        .dpi_clk_src = MIPI_DSI_DPI_CLK_SRC_DEFAULT,     \
        .dpi_clock_freq_mhz = SLIM4_PANEL_PIXEL_MHZ,     \
        .virtual_channel = 0,                            \
        .in_color_format = (fmt),                        \
        .num_fbs = 1,                                    \
        .video_timing = {                                \
            .h_size = SLIM4_PANEL_H_RES,                 \
            .v_size = SLIM4_PANEL_V_RES,                 \
            .hsync_back_porch = 80,                      \
            .hsync_pulse_width = 2,                      \
            .hsync_front_porch = 120,                    \
            .vsync_back_porch = 90,                      \
            .vsync_pulse_width = 2,                      \
            .vsync_front_porch = 60,                     \
        },                                               \
    }

const ili9881c_lcd_init_cmd_t *slim4_panel_cfaf_init(uint16_t *count);
