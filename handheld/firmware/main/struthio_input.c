#include "struthio_input.h"
#include <string.h>

enum { LEFT = 0, RIGHT = 1 };

static void queue_flap(struthio_input_mapper_t *m, struthio_flap_kind_t kind, bool chord)
{
    // Preserve latest chord correction if multiple edges arrive before the 60 Hz frame consumes them.
    if (!m->queued_flap || chord) {
        m->queued_flap = true;
        m->queued_flap_kind = kind;
        m->queued_chord = chord;
    }
}

static void on_press(struthio_input_mapper_t *m, int side, uint32_t now_ms)
{
    const int other = side ^ 1;
    m->press_ms[side] = now_ms;
    m->dart_sent[side] = false;

    // Current JS behavior: first wing can flap immediately. If the opposite wing
    // arrives within 100 ms, the pending/next event is corrected to STRAIGHT.
    if (m->stable[other] && (uint32_t)(now_ms - m->press_ms[other]) <= STRUTHIO_CHORD_WINDOW_MS) {
        queue_flap(m, STRUTHIO_FLAP_STRAIGHT, true);
        m->chord_latched = true;
        return;
    }

    queue_flap(m, side == LEFT ? STRUTHIO_FLAP_LEFT : STRUTHIO_FLAP_RIGHT, false);
}

static void on_release(struthio_input_mapper_t *m, int side)
{
    m->dart_sent[side] = false;
    if (!m->stable[LEFT] && !m->stable[RIGHT]) {
        m->chord_latched = false;
    }
}

static void debounce_one(struthio_input_mapper_t *m, int side, bool raw_pressed, uint32_t now_ms)
{
    if (raw_pressed != m->candidate[side]) {
        m->candidate[side] = raw_pressed;
        m->candidate_since_ms[side] = now_ms;
    }

    if (m->candidate[side] != m->stable[side] &&
        (uint32_t)(now_ms - m->candidate_since_ms[side]) >= STRUTHIO_DEBOUNCE_MS) {
        m->stable[side] = m->candidate[side];
        if (m->stable[side]) on_press(m, side, now_ms);
        else on_release(m, side);
    }
}

void struthio_input_init(struthio_input_mapper_t *m, uint32_t now_ms)
{
    memset(m, 0, sizeof(*m));
    m->candidate_since_ms[LEFT] = now_ms;
    m->candidate_since_ms[RIGHT] = now_ms;
}

void struthio_input_sample(struthio_input_mapper_t *m, bool left_pressed, bool right_pressed, uint32_t now_ms, bool boot_phase)
{
    m->raw[LEFT] = left_pressed;
    m->raw[RIGHT] = right_pressed;
    debounce_one(m, LEFT, left_pressed, now_ms);
    debounce_one(m, RIGHT, right_pressed, now_ms);

    if (boot_phase) {
        if (m->stable[LEFT] && m->stable[RIGHT]) {
            if (m->both_boot_since_ms == 0) m->both_boot_since_ms = now_ms ? now_ms : 1;
            if ((uint32_t)(now_ms - m->both_boot_since_ms) >= STRUTHIO_SERVICE_HOLD_MS) {
                m->service_mode_requested = true;
            }
        } else {
            m->both_boot_since_ms = 0;
        }
        return;
    }

    // Hold-to-DART A0 mapping. Suppress while both buttons are held/chorded.
    if (m->stable[LEFT] && !m->stable[RIGHT] && !m->dart_sent[LEFT] &&
        (uint32_t)(now_ms - m->press_ms[LEFT]) >= STRUTHIO_DART_HOLD_MS) {
        m->queued_dart = true;
        m->queued_dart_side = STRUTHIO_DART_LEFT;
        m->dart_sent[LEFT] = true;
    }
    if (m->stable[RIGHT] && !m->stable[LEFT] && !m->dart_sent[RIGHT] &&
        (uint32_t)(now_ms - m->press_ms[RIGHT]) >= STRUTHIO_DART_HOLD_MS) {
        m->queued_dart = true;
        m->queued_dart_side = STRUTHIO_DART_RIGHT;
        m->dart_sent[RIGHT] = true;
    }
}

struthio_input_frame_t struthio_input_consume_frame(struthio_input_mapper_t *m)
{
    struthio_input_frame_t out = {
        .left_held = m->stable[LEFT] && !m->stable[RIGHT],
        .right_held = m->stable[RIGHT] && !m->stable[LEFT],
        .flap_edge = m->queued_flap,
        .flap_kind = m->queued_flap ? m->queued_flap_kind : STRUTHIO_FLAP_NONE,
        .chord_edge = m->queued_flap && m->queued_chord,
        .dart_edge = m->queued_dart,
        .dart_side = m->queued_dart ? m->queued_dart_side : STRUTHIO_DART_NONE,
    };
    m->queued_flap = false;
    m->queued_flap_kind = STRUTHIO_FLAP_NONE;
    m->queued_chord = false;
    m->queued_dart = false;
    m->queued_dart_side = STRUTHIO_DART_NONE;
    return out;
}

bool struthio_input_service_mode_requested(const struthio_input_mapper_t *m)
{
    return m->service_mode_requested;
}
