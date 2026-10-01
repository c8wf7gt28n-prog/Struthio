// STRUTHIO HANDHELD · InputNormalizer port (arcade/src/input/input.mjs).
#include "struthio_input.h"
#include <string.h>

static int idx(st_side_t side) { return side == ST_SIDE_RIGHT ? 1 : 0; }
static bool regions_enabled(const st_norm_t *n) { return n->mode == ST_MODE_PLAY || n->mode == ST_MODE_ATTRACT; }

void st_norm_init(st_norm_t *n) { memset(n, 0, sizeof *n); n->mode = ST_MODE_ATTRACT; }

void st_norm_cleanup(st_norm_t *n) {
    n->held[0] = n->held[1] = false;
    n->darted[0] = n->darted[1] = false;
    n->n = 0;
    n->n_darts = 0;
    n->last_valid = false;
    n->flap_wait_ticks = 0;
}
void st_norm_set_mode(st_norm_t *n, st_mode_t mode) {
    if ((uint8_t)mode != n->mode) { n->mode = (uint8_t)mode; st_norm_cleanup(n); }
}
static bool queue_flap(st_norm_t *n, st_flap_kind_t kind, bool chord) {
    if (n->n >= ST_NORM_QUEUE_MAX) return false;
    n->kind[n->n] = (uint8_t)kind;
    n->chord[n->n] = chord;
    n->n++;
    n->flap_wait_ticks = 0;
    return true;
}
static void queue_wing(st_norm_t *n, st_side_t side, uint32_t now) {      // queueWing
    if (n->last_valid && n->last_side != side && (uint32_t)(now - n->last_at_ms) <= ST_NORM_CHORD_WINDOW_MS) {
        st_flap_kind_t last_kind = n->last_side == ST_SIDE_LEFT ? ST_FLAP_LEFT : ST_FLAP_RIGHT;
        if (n->n > 0 && n->kind[n->n - 1] == last_kind && !n->chord[n->n - 1]) {
            n->kind[n->n - 1] = ST_FLAP_STRAIGHT;
            n->chord[n->n - 1] = true;
        } else queue_flap(n, ST_FLAP_STRAIGHT, true);
        n->last_valid = false;
        return;
    }
    n->last_valid = true;
    n->last_side = (uint8_t)side;
    n->last_at_ms = now;
    queue_flap(n, side == ST_SIDE_LEFT ? ST_FLAP_LEFT : ST_FLAP_RIGHT, false);
}
void st_norm_wing_down(st_norm_t *n, st_side_t side, uint32_t now_ms) {   // controlPointerDown -> bindPointer
    int i = idx(side);
    n->held[i] = false;
    n->darted[i] = false;                    // a new pointer has not darted
    if (!regions_enabled(n)) return;
    n->held[i] = true;
    queue_wing(n, side, now_ms);
}
void st_norm_wing_up(st_norm_t *n, st_side_t side) {                     // pointerUp
    n->held[idx(side)] = false;
    n->darted[idx(side)] = false;
}
bool st_norm_dart(st_norm_t *n, st_side_t side) {                        // controlDart -> queueDart
    int i = idx(side);
    if (n->darted[i] || n->n_darts >= ST_NORM_QUEUE_MAX) return false;
    n->darted[i] = true;
    n->dart_queue[n->n_darts++] = (uint8_t)side;
    return true;
}
st_input_t st_norm_frame(st_norm_t *n, bool accept_flap) {
    st_input_t f;
    memset(&f, 0, sizeof f);
    bool l = n->held[0], r = n->held[1], play = n->mode == ST_MODE_PLAY;
    bool have = false;
    st_flap_kind_t kind = ST_FLAP_NONE;
    bool chord = false;
    if (accept_flap) {
        if (n->n > 0) {
            have = true; kind = (st_flap_kind_t)n->kind[0]; chord = n->chord[0];
            for (int i = 1; i < n->n; i++) { n->kind[i - 1] = n->kind[i]; n->chord[i - 1] = n->chord[i]; }
            n->n--;
            n->flap_wait_ticks = 0;
        }
    } else if (n->n > 0) {
        n->flap_wait_ticks += 1;
        if (n->flap_wait_ticks >= ST_NORM_FLAP_BUFFER_TICKS) { n->n = 0; n->flap_wait_ticks = 0; }
    } else n->flap_wait_ticks = 0;
    st_side_t dart = ST_SIDE_NONE;
    if (n->n_darts > 0) {
        dart = (st_side_t)n->dart_queue[0];
        for (int i = 1; i < n->n_darts; i++) n->dart_queue[i - 1] = n->dart_queue[i];
        n->n_darts--;
    }
    f.left = play && l && !r;
    f.right = play && r && !l;
    f.flap_edge = have;
    f.flap_kind = have ? kind : ST_FLAP_NONE;
    f.chord_edge = have && chord;
    f.dart_edge = dart != ST_SIDE_NONE;
    f.dart_side = dart;
    return f;
}
