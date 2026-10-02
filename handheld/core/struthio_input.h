// STRUTHIO HANDHELD · the browser InputNormalizer (arcade/src/input/input.mjs),
// ported for two physical wing buttons. Each wing press is one "pointer": a
// press queues a directional flap at once, the opposite wing inside the 100 ms
// chord window turns the pending flap (or a fresh one) into STRAIGHT, held wings
// steer, and a flap that cannot fire yet waits up to 8 ticks in the buffer.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "struthio_core.h"

#ifdef __cplusplus
extern "C" {
#endif

enum { ST_NORM_QUEUE_MAX = 4, ST_NORM_CHORD_WINDOW_MS = 100, ST_NORM_FLAP_BUFFER_TICKS = 8 };
typedef enum { ST_MODE_ATTRACT, ST_MODE_PLAY, ST_MODE_PAUSE } st_mode_t;

typedef struct {
    uint8_t kind[ST_NORM_QUEUE_MAX];    // st_flap_kind_t
    bool chord[ST_NORM_QUEUE_MAX];
    int n;
    int flap_wait_ticks;
    bool held[2];                        // a live pointer owns the wing (LEFT, RIGHT)
    bool darted[2];                      // that wing's pointer has already darted
    uint8_t dart_queue[ST_NORM_QUEUE_MAX];
    int n_darts;
    bool last_valid;
    uint8_t last_side;                   // st_side_t
    uint32_t last_at_ms;
    uint8_t mode;                        // st_mode_t
} st_norm_t;

void st_norm_init(st_norm_t *n);
void st_norm_set_mode(st_norm_t *n, st_mode_t mode);       // a mode change cleans up
void st_norm_wing_down(st_norm_t *n, st_side_t side, uint32_t now_ms);
void st_norm_wing_up(st_norm_t *n, st_side_t side);
// side NONE (handheld only) darts toward the bird's facing, as the sim does
// for a frame with dartEdge and no dartSide.
bool st_norm_dart(st_norm_t *n, st_side_t side);
// Handheld A1.5: one press of a DART-rocker end. Each press is a fresh pointer
// to the browser's queueDart (one dart, in that direction), so it never
// touches a wing's own once-per-press dart state.
bool st_norm_dart_button(st_norm_t *n, st_side_t side);
void st_norm_cleanup(st_norm_t *n);                        // after a death / game over
// One frame per 60 Hz tick. accept_flap = st_can_accept_buffered_flap(state).
st_input_t st_norm_frame(st_norm_t *n, bool accept_flap);

#ifdef __cplusplus
}
#endif
