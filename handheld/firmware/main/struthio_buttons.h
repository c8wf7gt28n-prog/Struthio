// STRUTHIO HANDHELD · two physical wing buttons -> the input normalizer.
//
// Sampled at 1 kHz from GPIO17 (LEFT) / GPIO18 (RIGHT), active low. Each
// switch is debounced (8 ms stable); the debounced press is stamped with the
// raw edge time, so the 100 ms chord window measures real thumb timing. A
// press is a new wing "pointer" in the normalizer: it flaps at once, the
// opposite wing inside 100 ms makes it STRAIGHT, and holding steers.
//
// DART has no physical gesture yet (the browser uses a downward flick). Two
// trials can be A/B tested on the bench, switchable in service mode:
//   A  HOLD      hold one wing alone for 230 ms
//   B  TAP-HOLD  release a wing and press it again within 220 ms, hold 60 ms
//   C  BOTH-HOLD hold both wings for 200 ms: dart forward (the facing side)
// Measured against the golden bots' press timelines (host_test), A and B fire
// tens of unwanted darts a minute because steering IS holding a wing and a
// flap while steering IS a quick re-press. C uses the one idle gesture: both
// wings held after the straight-up chord.
// The handheld adds a two-end silicone DART rocker (GPIO21 DART LEFT, GPIO38 DART
// RIGHT, active low): each debounced press of an end is one directional dart.
// ROCKER ONLY (trial OFF) is the default: both wings mean straight up, never a dart.
// The wing trials stay for bench boards without a rocker (select C in service mode).
// Portable C: no ESP-IDF headers, host-tested in firmware/host_test.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "struthio_input.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum { ST_DART_TRIAL_A_HOLD = 0, ST_DART_TRIAL_B_TAP_HOLD = 1, ST_DART_TRIAL_C_BOTH_HOLD = 2, ST_DART_OFF = 3 } st_dart_trial_t;
enum {
    ST_BTN_DEBOUNCE_MS = 8,
    ST_DART_HOLD_MS = 230,          // trial A
    ST_DART_TAP_GAP_MS = 220,       // trial B: release -> re-press
    ST_DART_TAP_HOLD_MS = 60,       // trial B: then hold
    ST_DART_BOTH_HOLD_MS = 200,     // trial C
    ST_SERVICE_HOLD_MS = 650,       // both wings at power-on
};

typedef struct {
    st_norm_t *norm;
    uint8_t trial;                  // st_dart_trial_t
    bool candidate[2], stable[2];
    uint32_t candidate_since[2];
    uint32_t press_at[2], release_at[2];
    bool released_once[2], tap_armed[2], darted[2];
    uint32_t presses[2], darts;     // counters for service mode
    bool rocker_candidate[2], rocker_stable[2];   // DART LEFT, DART RIGHT
    uint32_t rocker_since[2], rocker_presses[2];
    uint32_t both_since;
    bool both_timing, both_darted;
} st_buttons_t;

void st_buttons_init(st_buttons_t *b, st_norm_t *norm, st_dart_trial_t trial, uint32_t now_ms);
// One sample of both raw switch levels (true = pressed). Call at ~1 kHz.
void st_buttons_sample(st_buttons_t *b, bool left, bool right, uint32_t now_ms);
bool st_buttons_held(const st_buttons_t *b, st_side_t side);
// One sample of the DART rocker's two contacts (true = pressed), same rate.
void st_buttons_sample_rocker(st_buttons_t *b, bool dart_left, bool dart_right, uint32_t now_ms);
bool st_buttons_rocker_held(const st_buttons_t *b, st_side_t side);
// True once both wings have been held together for ST_SERVICE_HOLD_MS.
bool st_buttons_service_requested(const st_buttons_t *b, uint32_t now_ms);
const char *st_dart_trial_name(st_dart_trial_t t);

#ifdef __cplusplus
}
#endif
