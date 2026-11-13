#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "slim4_types.h"

#ifdef __cplusplus
extern "C" {
#endif

#define SLIM4_API_VERSION_MAJOR 1u
#define SLIM4_API_VERSION_MINOR 0u
#define SLIM4_FRAME_HZ 60u

typedef enum {
    SLIM4_BUTTON_FLAP_L = 1u << 0,
    SLIM4_BUTTON_FLAP_R = 1u << 1,
    SLIM4_BUTTON_DART_L = 1u << 2,
    SLIM4_BUTTON_DART_R = 1u << 3,
} slim4_button_t;

typedef struct {
    uint32_t down;
    uint32_t pressed;
    uint32_t released;
    uint64_t timestamp_us;
} slim4_input_state_t;

typedef struct {
    uint64_t frame_index;
    uint64_t elapsed_us;
    uint32_t delta_us;
} slim4_frame_time_t;

typedef struct {
    uint32_t struct_size;
    const char *game_id;
    const char *version;
    slim4_status_t (*start)(void);
    void (*update)(const slim4_input_state_t *, const slim4_frame_time_t *);
    void (*render)(slim4_surface_t *);
    void (*pause)(void);
    void (*resume)(void);
    void (*stop)(void);
} slim4_game_descriptor_t;

slim4_status_t slim4_platform_init(void);
void slim4_platform_pump(void);
uint64_t slim4_time_us(void);
slim4_status_t slim4_input_read(slim4_input_state_t *out);
slim4_status_t slim4_display_acquire(slim4_surface_t *out);
slim4_status_t slim4_display_present(const slim4_surface_t *surface);
slim4_status_t slim4_audio_set_master_volume(uint8_t volume_0_100);
/* Copies interleaved L,R signed-16 PCM into the audio queue; caller memory may be reused on return. */
slim4_status_t slim4_audio_play_pcm_s16(const int16_t *stereo_samples, size_t frames, uint32_t sample_rate);
slim4_status_t slim4_save_read(const char *key, void *dst, size_t *inout_len);
slim4_status_t slim4_save_write(const char *key, const void *src, size_t len);
slim4_status_t slim4_game_start(const slim4_game_descriptor_t *game);
void slim4_game_pause(void);
void slim4_game_resume(void);
void slim4_game_stop(void);

#ifdef __cplusplus
}
#endif
