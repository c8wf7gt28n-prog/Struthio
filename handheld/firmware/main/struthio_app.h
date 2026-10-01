// STRUTHIO HANDHELD · what main.c shares with service.c.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "struthio_buttons.h"
#include "struthio_input.h"

typedef struct {
    uint64_t ticks;
    uint32_t game_over_tick;
    uint32_t sim_us_last, sim_us_max;
    uint32_t render_us, present_us, frames;
    uint32_t missed_deadlines;
} app_stats_t;
extern app_stats_t g_stats;

uint32_t app_now_ms(void);
bool app_pin_pressed(int pin);
int32_t app_load_i32(const char *key, int32_t fallback);
void app_save_i32(const char *key, int32_t v);
uint8_t *app_framebuffer(void);
bool app_display_ok(void);
void app_present(const uint8_t *fb);

// Hidden service mode (both wings at power-on). Never returns: power-cycle to play.
void service_mode_run(st_buttons_t *buttons, st_norm_t *norm);
