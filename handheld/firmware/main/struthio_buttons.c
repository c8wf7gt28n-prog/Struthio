// STRUTHIO HANDHELD · wing buttons. See struthio_buttons.h.
#include "struthio_buttons.h"
#include <string.h>

static st_side_t side_of(int i) { return i == 0 ? ST_SIDE_LEFT : ST_SIDE_RIGHT; }

void st_buttons_init(st_buttons_t *b, st_norm_t *norm, st_dart_trial_t trial, uint32_t now_ms) {
    memset(b, 0, sizeof *b);
    b->norm = norm;
    b->trial = (uint8_t)trial;
    b->candidate_since[0] = b->candidate_since[1] = now_ms;
    b->rocker_since[0] = b->rocker_since[1] = now_ms;
}
const char *st_dart_trial_name(st_dart_trial_t t) {
    return t == ST_DART_TRIAL_A_HOLD ? "A HOLD" : t == ST_DART_TRIAL_B_TAP_HOLD ? "B TAP-HOLD"
         : t == ST_DART_TRIAL_C_BOTH_HOLD ? "C BOTH-HOLD" : "ROCKER ONLY";
}
static void on_press(st_buttons_t *b, int i, uint32_t edge_ms) {
    b->press_at[i] = edge_ms;
    b->darted[i] = false;
    b->tap_armed[i] = b->released_once[i] && (uint32_t)(edge_ms - b->release_at[i]) <= ST_DART_TAP_GAP_MS;
    b->presses[i]++;
    if (b->norm) st_norm_wing_down(b->norm, side_of(i), edge_ms);
}
static void on_release(st_buttons_t *b, int i, uint32_t edge_ms) {
    b->release_at[i] = edge_ms;
    b->released_once[i] = true;
    b->tap_armed[i] = false;
    if (b->norm) st_norm_wing_up(b->norm, side_of(i));
}
void st_buttons_sample(st_buttons_t *b, bool left, bool right, uint32_t now_ms) {
    const bool raw[2] = {left, right};
    for (int i = 0; i < 2; i++) {
        if (raw[i] != b->candidate[i]) { b->candidate[i] = raw[i]; b->candidate_since[i] = now_ms; }
        if (b->candidate[i] != b->stable[i] && (uint32_t)(now_ms - b->candidate_since[i]) >= ST_BTN_DEBOUNCE_MS) {
            b->stable[i] = b->candidate[i];
            if (b->stable[i]) on_press(b, i, b->candidate_since[i]);
            else on_release(b, i, b->candidate_since[i]);
        }
    }
    if (b->stable[0] && b->stable[1]) {
        if (!b->both_timing) { b->both_timing = true; b->both_darted = false; b->both_since = now_ms; }
    } else b->both_timing = false;
    if (b->trial == ST_DART_TRIAL_C_BOTH_HOLD) {
        if (b->both_timing && !b->both_darted && (uint32_t)(now_ms - b->both_since) >= ST_DART_BOTH_HOLD_MS) {
            b->both_darted = true;
            b->darts++;
            if (b->norm) st_norm_dart(b->norm, ST_SIDE_NONE);      // the sim darts toward facing
        }
        return;
    }
    for (int i = 0; i < 2; i++) {
        if (!b->stable[i] || b->darted[i]) continue;
        uint32_t held = now_ms - b->press_at[i];
        bool fire = false;
        if (b->trial == ST_DART_TRIAL_A_HOLD) fire = !b->stable[i ^ 1] && held >= ST_DART_HOLD_MS;
        else if (b->trial == ST_DART_TRIAL_B_TAP_HOLD) fire = b->tap_armed[i] && held >= ST_DART_TAP_HOLD_MS;
        if (fire) {
            b->darted[i] = true;
            b->darts++;
            if (b->norm) st_norm_dart(b->norm, side_of(i));
        }
    }
}
void st_buttons_sample_rocker(st_buttons_t *b, bool dart_left, bool dart_right, uint32_t now_ms) {
    const bool raw[2] = {dart_left, dart_right};
    for (int i = 0; i < 2; i++) {
        if (raw[i] != b->rocker_candidate[i]) { b->rocker_candidate[i] = raw[i]; b->rocker_since[i] = now_ms; }
        if (b->rocker_candidate[i] != b->rocker_stable[i] && (uint32_t)(now_ms - b->rocker_since[i]) >= ST_BTN_DEBOUNCE_MS) {
            b->rocker_stable[i] = b->rocker_candidate[i];
            if (b->rocker_stable[i]) {
                b->rocker_presses[i]++;
                b->darts++;
                if (b->norm) st_norm_dart_button(b->norm, side_of(i));
            }
        }
    }
}
bool st_buttons_rocker_held(const st_buttons_t *b, st_side_t side) { return b->rocker_stable[side == ST_SIDE_RIGHT ? 1 : 0]; }
bool st_buttons_held(const st_buttons_t *b, st_side_t side) { return b->stable[side == ST_SIDE_RIGHT ? 1 : 0]; }
bool st_buttons_service_requested(const st_buttons_t *b, uint32_t now_ms) {
    return b->both_timing && (uint32_t)(now_ms - b->both_since) >= ST_SERVICE_HOLD_MS;
}
