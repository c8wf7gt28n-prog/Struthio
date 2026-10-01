// STRUTHIO HANDHELD · portable C11 port of the STRUTHIO ARCADE 1.8.0 simulation.
//
// Authority: arcade/src/sim/*.mjs, arcade/src/core/{fixed,rng}.mjs and the sim /
// scoring / lifecycle sections of arcade/src/data/rules.mjs. This is a platform
// port, not a rewrite: every stage runs in the same order with the same integer
// arithmetic, and the host replay test proves each tick's canonical state digest
// equals the browser's (handheld/golden/*.trace).
//
// No allocation, no floating point in stored state, no platform headers. The
// only doubles are the tower's altitude-band comparisons, which the JS authority
// also does in IEEE double and which C reproduces exactly.
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum { ST_SUB = 256, ST_WRAP = 256 * 256, ST_LOGICAL_W = 256, ST_LOGICAL_H = 384, ST_TICK_HZ = 60 };
enum { ST_MAX_ACTORS = 24, ST_MAX_EVENTS = 96, ST_MAX_EVENT_FIELDS = 6, ST_NO_PLATFORM = -1 };

typedef enum { ST_SHELL_ATTRACT, ST_SHELL_PLAY, ST_SHELL_PAUSE, ST_SHELL_GAMEOVER } st_shell_t;
typedef enum { ST_LAVA_SAFE, ST_LAVA_SINK, ST_LAVA_RESCUED } st_lava_phase_t;
typedef enum { ST_KIND_RIVAL, ST_KIND_RIDER, ST_KIND_EGG } st_actor_kind_t;
typedef enum { ST_CLASS_BOUNDER, ST_CLASS_HUNTER, ST_CLASS_SHADOW } st_class_t;
typedef enum { ST_GHOST_BLINKY, ST_GHOST_PINKY, ST_GHOST_INKY, ST_GHOST_CLYDE } st_ghost_t;
typedef enum {
    ST_LC_SPAWNING, ST_LC_MOUNTED, ST_LC_DISMOUNTED, ST_LC_EGG, ST_LC_HATCHING, ST_LC_REMOUNTING, ST_LC_REMOVED
} st_lifecycle_t;
typedef enum { ST_MOTION_STATIC, ST_MOTION_DRIFT_X_SOFT, ST_MOTION_BOB_Y_SOFT } st_motion_t;

// Flap kinds as carried by an input frame. NONE with flap_edge set is the
// browser's null flapKind, which the sim names LEGACY.
typedef enum { ST_FLAP_NONE = 0, ST_FLAP_LEFT = 1, ST_FLAP_RIGHT = 2, ST_FLAP_STRAIGHT = 3 } st_flap_kind_t;
typedef enum { ST_SIDE_NONE = 0, ST_SIDE_LEFT = 1, ST_SIDE_RIGHT = 2 } st_side_t;

// One 60 Hz input frame: the browser InputNormalizer.frame() shape.
typedef struct {
    bool left, right;
    bool flap_edge;
    st_flap_kind_t flap_kind;
    bool chord_edge;
    bool dart_edge;
    st_side_t dart_side;
} st_input_t;

typedef struct {
    int32_t x, y, vx, vy;
    int16_t grounded;           // platform index, ST_NO_PLATFORM when airborne
    int8_t facing;
    int16_t wing, flap_cooldown;
    int32_t footing_ticks;
    uint8_t lava_phase;         // st_lava_phase_t
    int32_t lava_ticks, invulnerable_ticks;
} st_player_t;

typedef struct {
    int32_t id;
    uint8_t kind, cls, ghost, lifecycle;
    int8_t tier, facing;
    int32_t x, y, vx, vy;
    int32_t phase, timer, rng_draws;
    bool joust_awarded;
} st_actor_t;

typedef struct {
    int16_t id;                 // index into the tower's platform table
    uint8_t phase;              // st_motion_t
    int32_t tick;
    int32_t rect[4];            // logical px: x, y, w, h
    bool collidable;
} st_platform_t;

typedef struct {
    int32_t round, ring_mask, kills, check;
    bool go;
    int32_t hold, cooldown, mercy;
} st_tower_t;

enum { ST_TOWER_PLATFORMS = 43 };

typedef struct {
    struct { int32_t tick; uint8_t shell; int32_t next_actor_id, event_serial, score, lives; } sim;
    uint32_t rng;
    st_player_t player;
    int32_t n_actors;
    st_actor_t actors[ST_MAX_ACTORS];
    struct { int32_t lava_y; int32_t n_platforms; st_platform_t platforms[ST_TOWER_PLATFORMS]; } world;
    st_tower_t tower;
    struct { int32_t egg_chain; bool clean; int32_t deaths, life_bands; } run;
} st_state_t;

// ---- events -------------------------------------------------------------------
typedef enum {
    ST_EV_ARENA_ACTIVATE, ST_EV_TOWER_GO, ST_EV_FLAP, ST_EV_FLAP_CHORD, ST_EV_DART,
    ST_EV_LAVA_RESCUE, ST_EV_LAVA_CONTACT, ST_EV_PLAYER_DEATH, ST_EV_JOUST_CLASH, ST_EV_JOUST_WIN,
    ST_EV_SCORE_AWARD, ST_EV_EXTRA_LIFE, ST_EV_EGG, ST_EV_MOUNT, ST_EV_HATCH, ST_EV_REMOUNT,
    ST_EV_DESPAWN, ST_EV_SPAWN, ST_EV_RING, ST_EV_GOLD_RING_OPEN, ST_EV_TOWER_BLAST, ST_EV_ROUND_CLEAR,
    ST_EV_CHECKPOINT_REQUEST, ST_EV_ROUND_START, ST_EV_TOWER_CHECK, ST_EV_GAMEOVER, ST_EV_RESPAWN_SCHEDULED,
    ST_EV_COUNT
} st_event_type_t;

typedef enum { ST_F_INT, ST_F_STR, ST_F_BOOL } st_field_kind_t;
typedef struct {
    const char *key;
    uint8_t kind;               // st_field_kind_t
    int32_t i;                  // INT and BOOL
    const char *s;              // STR (static string)
} st_field_t;

typedef struct {
    uint8_t type;               // st_event_type_t
    uint8_t n;
    int32_t serial;
    st_field_t f[ST_MAX_EVENT_FIELDS];
} st_event_t;

typedef struct {
    int32_t n;
    st_event_t e[ST_MAX_EVENTS];
} st_events_t;

const char *st_event_name(st_event_type_t t);
// Looks a field up by key; returns NULL when the event does not carry it.
const st_field_t *st_event_field(const st_event_t *e, const char *key);

// ---- simulation ---------------------------------------------------------------
// newState(seed): ATTRACT shell, empty world, 11 lives.
void st_state_init(st_state_t *s, uint32_t seed);
// startRun(): PLAY shell, tower built. Its ARENA_ACTIVATE event is not part of a
// tick digest (the browser Game prepends it to the first tick with serial 0).
void st_start_run(st_state_t *s, st_events_t *out);
// stepTick(): one deterministic 60 Hz tick. Events carry their serials.
void st_step(st_state_t *s, const st_input_t *in, st_events_t *out);

// Session helper from arcade/src/app/session.mjs: whether a buffered flap may
// be released into this tick.
bool st_can_accept_buffered_flap(const st_state_t *s);

// ---- the tower (read-only data for renderers) ----------------------------------
typedef struct {
    const char *id;
    int16_t x, y, w, h;
    uint8_t motion;             // st_motion_t
    int16_t amplitude, period, phase_offset;
    uint8_t look;               // island art 1..9 (STD_01..STD_09), 0 for GROUND
    bool mirror;
} st_tower_platform_t;

typedef struct { int16_t x, y, radius; } st_ring_t;

extern const st_tower_platform_t ST_TOWER[ST_TOWER_PLATFORMS];
enum { ST_RING_SETS = 10, ST_RINGS_PER_SET = 6 };
extern const st_ring_t ST_RING_SET[ST_RING_SETS][ST_RINGS_PER_SET];
extern const st_ring_t ST_GOLD_RING;
enum { ST_TOWER_TOP = 360 - 8 * 192, ST_TOWER_GROUND = 336, ST_TOWER_BOTTOM = 360, ST_TOWER_PLAY_TOP = ST_TOWER_TOP + 20 };
// The ring set the current round uses (towerRules(round).ringSet).
int st_ring_set_for_round(int32_t round);

// Hit boxes in logical px offsets from the entity origin.
typedef struct { int8_t l, r, t, b; } st_box_t;
extern const st_box_t ST_BIRD_BOX, ST_RIDER_BOX, ST_EGG_BOX;
enum { ST_SHIMMER_TICKS = 150, ST_RESPAWN_HIDDEN_TICKS = 84 };

// ---- digests (port validation; debug builds) ----------------------------------
// Canonical JSON of {state, events}, byte-identical to the browser's
// canonical(). Returns the length written (excluding NUL), or -1 if cap is too
// small. Needs no heap.
int st_canonical_tick(const st_state_t *s, const st_events_t *ev, char *buf, size_t cap);
// SHA-256 hex of the canonical tick: the browser's stepTick().digest.
void st_tick_digest(const st_state_t *s, const st_events_t *ev, char hex[65]);
// The Game digest chain: chain0 = digest({seed, game}); chain' = digest({prev, tick}).
void st_chain_init(uint32_t seed, char hex[65]);
void st_chain_link(const char prev[65], const char tick[65], char out[65]);
// digest(payload): the browser Game.stateDigest().
void st_state_digest(const st_state_t *s, char hex[65]);

#ifdef __cplusplus
}
#endif
