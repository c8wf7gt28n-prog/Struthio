// STRUTHIO HANDHELD · golden trace replay (portable: host test and on-device
// service mode). Replays a handheld/golden/*.trace button timeline through the
// C input normalizer and simulation and checks every frame and tick digest
// against the browser authority.
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "struthio_core.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    char name[32];
    long ticks;               // ticks in the trace
    long ran;                 // ticks replayed
    long first_bad_tick;      // -1 when everything matched
    char why[96];             // first mismatch, human readable
    char chain[65];
    bool chain_ok, state_ok;
    int32_t score, round;
    long event_counts[ST_EV_COUNT];
} st_replay_result_t;

// Optional hooks: pre runs before each tick's step, post after it (render,
// dump or time it).
typedef void (*st_replay_tick_fn)(void *ctx, long tick, const st_state_t *s, const st_events_t *ev);
typedef void (*st_replay_pre_fn)(void *ctx, long tick, const st_state_t *s);
typedef struct { void *ctx; st_replay_pre_fn pre; st_replay_tick_fn post; } st_replay_hooks_t;

// verify_digests: false skips the per-tick SHA-256 (fast simulation timing).
// hooks may be NULL. Returns true when the whole trace matched.
bool st_replay(const uint8_t *data, size_t size, bool verify_digests, const st_replay_hooks_t *hooks, st_replay_result_t *out);

#ifdef __cplusplus
}
#endif
