// STRUTHIO HANDHELD · what main.c shares with service.c.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "struthio_buttons.h"
#include "struthio_core.h"
#include "struthio_input.h"

typedef struct {
    uint64_t ticks;
    uint32_t game_over_tick;
    uint32_t sim_us_last, sim_us_max;
    uint32_t scene_us, render_us, present_us, frames;
    uint32_t missed_deadlines;
    uint32_t audio_us, audio_us_max;     // per 256 frames (5,333 us of sound)
} app_stats_t;
extern app_stats_t g_stats;

uint32_t app_now_ms(void);
bool app_pin_pressed(int pin);
int32_t app_load_i32(const char *key, int32_t fallback);
void app_save_i32(const char *key, int32_t v);
uint8_t *app_framebuffer(void);
bool app_display_ok(void);
void app_present(const uint8_t *fb);

// Sound (main.c): codec + audio task, started once (play or service mode).
enum { APP_VOLUME_LEVELS = 5 };              // 0 = off .. 4
bool app_audio_start(void);
bool app_audio_ok(void);
bool app_music_ok(void);
void app_audio_post(const st_event_t *e);
void app_audio_test(int event_type);        // plays that event's sound
int app_volume(void);
void app_set_volume(int level);              // saved in NVS

// Hidden service mode (both wings at power-on). Never returns: power-cycle to play.
void service_mode_run(st_buttons_t *buttons, st_norm_t *norm);
