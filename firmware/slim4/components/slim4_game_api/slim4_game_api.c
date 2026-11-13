#include "slim4_game_api.h"

#include <stdio.h>
#include <string.h>

#include "esp_log.h"
#include "esp_timer.h"
#include "slim4_board.h"

#define SLIM4_NVS_NAME_MAX       16u
#define SLIM4_GAME_ID_MAX        64u
#define SLIM4_GAME_VERSION_MAX   32u
#define SLIM4_FRAME_PERIOD_US    (1000000u / SLIM4_FRAME_HZ)
#define SLIM4_MAX_CATCHUP_STEPS  4u

static const char *TAG = "slim4_api";
static slim4_game_descriptor_t s_game_storage;
static char s_game_id_storage[SLIM4_GAME_ID_MAX];
static char s_game_version_storage[SLIM4_GAME_VERSION_MAX];
static const slim4_game_descriptor_t *s_game;
static bool s_game_paused;
static bool s_display_error_reported;
static uint64_t s_frame;
static uint64_t s_game_generation;
static uint64_t s_last_pump_us;
static uint64_t s_simulated_time_us;
static uint32_t s_frame_accumulator_us;
static uint32_t s_previous_buttons;
static slim4_surface_t s_surface;

static void make_save_namespace(char out[SLIM4_NVS_NAME_MAX])
{
    if (!s_game || !s_game->game_id) {
        (void)snprintf(out, SLIM4_NVS_NAME_MAX, "slim4_sys");
        return;
    }

    /* NVS namespaces are limited to 15 characters; use a stable 56-bit game ID hash. */
    uint64_t hash = 14695981039346656037ull;
    for (const unsigned char *p = (const unsigned char *)s_game->game_id; *p; ++p) {
        hash = (hash ^ *p) * 1099511628211ull;
    }
    (void)snprintf(out, SLIM4_NVS_NAME_MAX, "g%014llx",
                   (unsigned long long)(hash & 0x00ffffffffffffffull));
}

static bool valid_save_key(const char *key)
{
    if (!key || key[0] == '\0' || strnlen(key, SLIM4_NVS_NAME_MAX) >= SLIM4_NVS_NAME_MAX) {
        return false;
    }
    for (const unsigned char *p = (const unsigned char *)key; *p; ++p) {
        const bool alphanumeric = (*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z') ||
                                  (*p >= '0' && *p <= '9');
        if (!alphanumeric && *p != '_' && *p != '-' && *p != '.') return false;
    }
    return true;
}

uint64_t slim4_time_us(void)
{
    return (uint64_t)esp_timer_get_time();
}

slim4_status_t slim4_platform_init(void)
{
    return slim4_board_init();
}

slim4_status_t slim4_input_read(slim4_input_state_t *out)
{
    if (!out) return SLIM4_ERR_INVALID_ARG;

    uint32_t buttons = 0;
    const slim4_status_t status = slim4_board_read_buttons(&buttons);
    if (status != SLIM4_OK) return status;

    out->down = buttons;
    out->pressed = buttons & ~s_previous_buttons;
    out->released = s_previous_buttons & ~buttons;
    out->timestamp_us = slim4_time_us();
    s_previous_buttons = buttons;
    return SLIM4_OK;
}

slim4_status_t slim4_display_acquire(slim4_surface_t *out)
{
    if (!out) return SLIM4_ERR_INVALID_ARG;
    return slim4_board_display_acquire(out);
}

slim4_status_t slim4_display_present(const slim4_surface_t *surface)
{
    return slim4_board_display_present(surface);
}

slim4_status_t slim4_audio_set_master_volume(uint8_t volume)
{
    if (volume > 100) return SLIM4_ERR_INVALID_ARG;
    return slim4_board_audio_set_volume(volume);
}

slim4_status_t slim4_audio_play_pcm_s16(const int16_t *stereo_samples, size_t frames,
                                        uint32_t sample_rate)
{
    if ((!stereo_samples && frames) || sample_rate < 8000 || sample_rate > 96000) {
        return SLIM4_ERR_INVALID_ARG;
    }
    return slim4_board_audio_write(stereo_samples, frames, sample_rate);
}

slim4_status_t slim4_save_read(const char *key, void *dst, size_t *inout_len)
{
    if (!valid_save_key(key) || !inout_len) return SLIM4_ERR_INVALID_ARG;
    char name_space[SLIM4_NVS_NAME_MAX];
    make_save_namespace(name_space);
    return slim4_board_save_read(name_space, key, dst, inout_len);
}

slim4_status_t slim4_save_write(const char *key, const void *src, size_t len)
{
    if (!valid_save_key(key) || (!src && len)) return SLIM4_ERR_INVALID_ARG;
    char name_space[SLIM4_NVS_NAME_MAX];
    make_save_namespace(name_space);
    return slim4_board_save_write(name_space, key, src, len);
}

slim4_status_t slim4_game_start(const slim4_game_descriptor_t *game)
{
    if (!game || game->struct_size < sizeof(*game) || !game->game_id ||
        !game->update || !game->render) {
        return SLIM4_ERR_INVALID_ARG;
    }
    if (strnlen(game->game_id, SLIM4_GAME_ID_MAX) >= SLIM4_GAME_ID_MAX ||
        (game->version && strnlen(game->version, SLIM4_GAME_VERSION_MAX) >= SLIM4_GAME_VERSION_MAX)) {
        return SLIM4_ERR_INVALID_ARG;
    }

    if (s_game) slim4_game_stop();

    s_game_storage = *game;
    (void)snprintf(s_game_id_storage, sizeof(s_game_id_storage), "%s", game->game_id);
    if (game->version) {
        (void)snprintf(s_game_version_storage, sizeof(s_game_version_storage), "%s", game->version);
    } else {
        s_game_version_storage[0] = '\0';
    }
    s_game_storage.game_id = s_game_id_storage;
    s_game_storage.version = game->version ? s_game_version_storage : NULL;
    s_game = &s_game_storage;
    s_game_paused = false;
    s_frame = 0;
    s_previous_buttons = 0;
    s_last_pump_us = slim4_time_us();
    s_simulated_time_us = s_last_pump_us;
    s_frame_accumulator_us = 0;
    s_display_error_reported = false;
    const uint64_t start_generation = ++s_game_generation;

    if (s_game->start) {
        const slim4_status_t status = s_game->start();
        if (status != SLIM4_OK) {
            s_game = NULL;
            ++s_game_generation;
            return status;
        }
    }
    if (!s_game || s_game_generation != start_generation) return SLIM4_ERR_NOT_READY;

    ESP_LOGI(TAG, "game started: %s %s", s_game->game_id,
             s_game->version ? s_game->version : "(unversioned)");
    return SLIM4_OK;
}

void slim4_game_pause(void)
{
    if (!s_game || s_game_paused) return;
    const uint64_t generation = s_game_generation;
    if (s_game->pause) s_game->pause();
    if (!s_game || generation != s_game_generation) return;
    s_game_paused = true;
    s_frame_accumulator_us = 0;
}

void slim4_game_resume(void)
{
    if (!s_game || !s_game_paused) return;
    const uint64_t generation = s_game_generation;
    if (s_game->resume) s_game->resume();
    if (!s_game || generation != s_game_generation) return;
    s_game_paused = false;
    s_last_pump_us = slim4_time_us();
    s_simulated_time_us = s_last_pump_us;
    s_frame_accumulator_us = 0;
}

void slim4_game_stop(void)
{
    if (s_game && s_game->stop) s_game->stop();
    s_game = NULL;
    s_game_paused = false;
    ++s_game_generation;
}

void slim4_platform_pump(void)
{
    if (!s_game || s_game_paused) return;

    const uint64_t now = slim4_time_us();
    const uint64_t elapsed = now - s_last_pump_us;
    s_last_pump_us = now;
    const uint64_t max_elapsed = (uint64_t)SLIM4_FRAME_PERIOD_US * SLIM4_MAX_CATCHUP_STEPS;
    s_frame_accumulator_us += (uint32_t)(elapsed > max_elapsed ? max_elapsed : elapsed);
    if (s_frame_accumulator_us < SLIM4_FRAME_PERIOD_US) return;

    slim4_input_state_t input = {0};
    if (slim4_input_read(&input) != SLIM4_OK) return;
    const uint64_t generation = s_game_generation;
    uint32_t steps = 0;
    while (s_frame_accumulator_us >= SLIM4_FRAME_PERIOD_US && steps < SLIM4_MAX_CATCHUP_STEPS) {
        s_simulated_time_us += SLIM4_FRAME_PERIOD_US;
        const slim4_frame_time_t frame_time = {
            .frame_index = s_frame++,
            .elapsed_us = s_simulated_time_us,
            .delta_us = SLIM4_FRAME_PERIOD_US,
        };
        s_game->update(&input, &frame_time);
        if (!s_game || generation != s_game_generation) return;

        /* Edge events are consumed once, even when this pump catches up multiple steps. */
        input.pressed = 0;
        input.released = 0;
        s_frame_accumulator_us -= SLIM4_FRAME_PERIOD_US;
        ++steps;
    }

    if (slim4_display_acquire(&s_surface) != SLIM4_OK) return;
    s_game->render(&s_surface);
    const slim4_status_t status = slim4_display_present(&s_surface);
    if (status != SLIM4_OK && !s_display_error_reported) {
        ESP_LOGE(TAG, "game frame presentation failed: %d", (int)status);
        s_display_error_reported = true;
    }
}
