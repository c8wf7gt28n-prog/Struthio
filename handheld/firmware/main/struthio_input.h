#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "struthio_rules_snapshot.h"

typedef enum {
    STRUTHIO_FLAP_NONE = 0,
    STRUTHIO_FLAP_LEFT,
    STRUTHIO_FLAP_RIGHT,
    STRUTHIO_FLAP_STRAIGHT,
} struthio_flap_kind_t;

typedef enum {
    STRUTHIO_DART_NONE = 0,
    STRUTHIO_DART_LEFT,
    STRUTHIO_DART_RIGHT,
} struthio_dart_side_t;

typedef struct {
    bool left_held;
    bool right_held;
    bool flap_edge;
    struthio_flap_kind_t flap_kind;
    bool chord_edge;
    bool dart_edge;
    struthio_dart_side_t dart_side;
} struthio_input_frame_t;

typedef struct {
    // debounce state
    bool raw[2];
    bool candidate[2];
    bool stable[2];
    uint32_t candidate_since_ms[2];

    uint32_t press_ms[2];
    bool dart_sent[2];
    bool chord_latched;

    // one-shot event queue collapsed for the next 60 Hz simulation frame
    bool queued_flap;
    struthio_flap_kind_t queued_flap_kind;
    bool queued_chord;
    bool queued_dart;
    struthio_dart_side_t queued_dart_side;

    // service-mode boot detector
    uint32_t both_boot_since_ms;
    bool service_mode_requested;
} struthio_input_mapper_t;

void struthio_input_init(struthio_input_mapper_t *m, uint32_t now_ms);
void struthio_input_sample(struthio_input_mapper_t *m, bool left_pressed, bool right_pressed, uint32_t now_ms, bool boot_phase);
struthio_input_frame_t struthio_input_consume_frame(struthio_input_mapper_t *m);
bool struthio_input_service_mode_requested(const struthio_input_mapper_t *m);

// Tunable A0 constants. These mirror current STRUTHIO behavior where practical.
enum {
    STRUTHIO_DEBOUNCE_MS = 8,
    STRUTHIO_DART_HOLD_MS = 230,
    STRUTHIO_SERVICE_HOLD_MS = 650,
};
