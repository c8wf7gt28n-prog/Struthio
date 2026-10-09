#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "slim4_types.h"
#include "slim4_selftest.h"

slim4_status_t slim4_board_init(void);
void slim4_board_show_boot_result(bool software_verified);
/* The self-test page: one row per check, then colour bars and 1-pixel gratings for the video lanes. */
slim4_status_t slim4_board_show_selftest(const slim4_st_report_t *rep);
/* Result of the bounded panel probe run during the display bring-up. */
void slim4_board_panel_probe(slim4_panel_probe_t *out);
slim4_status_t slim4_board_render_diagnostic(uint32_t buttons, const uint32_t press_counts[4],
                                              uint32_t frame_index,
                                              uint32_t measured_fps, uint32_t measured_vsync_hz,
                                              uint32_t max_render_us,
                                              uint32_t late_frames, uint8_t color_phase);
uint32_t slim4_board_get_vsync_count(void);
slim4_status_t slim4_board_read_buttons(uint32_t *buttons);
slim4_status_t slim4_board_display_acquire(slim4_surface_t *out);
slim4_status_t slim4_board_display_present(const slim4_surface_t *surface);
slim4_status_t slim4_board_audio_set_volume(uint8_t volume);
slim4_status_t slim4_board_audio_write(const int16_t *stereo, size_t frames, uint32_t sample_rate);
slim4_status_t slim4_board_save_read(const char *name_space, const char *key, void *dst,
                                     size_t *inout_len);
slim4_status_t slim4_board_save_write(const char *name_space, const char *key, const void *src, size_t len);
