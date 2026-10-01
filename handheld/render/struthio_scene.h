// STRUTHIO HANDHELD · the scene builder: a port of the browser's
// arcade/src/render/scene.mjs (+ ring-fx emit, props, bird-animation, camera,
// and the session's feel / popup / banner handling). Every frame it produces
// the same list of textured quads the browser hands its WebGPU renderer; the
// host test proves the lists equal the browser's on every tick of the goldens.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "struthio_core.h"

#ifdef __cplusplus
extern "C" {
#endif

// One instanced quad, exactly the browser's {x,y,w,h,sx,sy,sw,sh,z,flags}:
// destination in logical px (256x384), source in texels of the texture the
// material names (atlas 2048^2, bird sheet 1536x1152, world 1536x2304).
typedef struct {
    double x, y, w, h, sx, sy, sw, sh, z;
    uint8_t flags;              // material: 0 atlas, 2..7 bird ink, 8 world, 10 player, 11 island
} st_quad_t;

enum { ST_MAT_ATLAS = 0, ST_MAT_WORLD = 8, ST_MAT_PLAYER = 10, ST_MAT_ISLAND = 11 };
enum { ST_MAX_QUADS = 4096 };
enum { ST_PANEL_W = 320, ST_PANEL_H = 480 };     // the handheld panel, portrait

// ---- generated tables (render/struthio_scene_data.c) ------------------------------
typedef struct { const char *name; int16_t x, y; } st_swatch_t;
typedef struct { int16_t x, y, cols, cell_w, cell_h, rows, glyph_w, glyph_h; } st_modern_font_t;
typedef struct { const char *id; int16_t x, y, w, h, cap_top, top_decor; } st_island_master_t;
typedef struct {
    uint8_t master, mirror, ground;
    double depth;
    uint8_t has_slot;
    int16_t slot[6];            // x, y, w, h, decorY, decorH
} st_island_plan_t;
enum { ST_SWATCH_COUNT = 41, ST_FONT_COUNT = 51, ST_ISLAND_MASTER_COUNT = 10 };
extern const st_swatch_t ST_SWATCHES[ST_SWATCH_COUNT];
extern const char ST_FONT_CHARS[ST_FONT_COUNT];
extern const st_modern_font_t ST_MODERN_FONT;
extern const int ST_ISLANDS_ORIGIN[2];
extern const st_island_master_t ST_ISLAND_MASTERS[ST_ISLAND_MASTER_COUNT];
extern const st_island_plan_t ST_ISLAND_PLANS[ST_TOWER_PLATFORMS];

// ---- session-side presentation state (arcade/src/app/session.mjs, feel.mjs) ----
typedef enum { ST_FEEL_NONE, ST_FEEL_FLAP, ST_FEEL_LAND, ST_FEEL_RING, ST_FEEL_RING_GREEN, ST_FEEL_CLASH,
               ST_FEEL_JOUST_WIN, ST_FEEL_DEATH } st_feel_kind_t;
typedef enum { ST_SPACE_WORLD, ST_SPACE_PLAYER_CENTER, ST_SPACE_PLAYER_FEET } st_feel_space_t;
typedef struct {
    uint8_t kind, space;
    int32_t start, until, shake_until, priority;
    double strength;
    int32_t x, y;
} st_feel_t;
typedef struct {
    bool active;
    uint8_t kind, space;
    int32_t age;
    double life, impact;
    int32_t jolt_x, jolt_y, x, y;
} st_feel_sample_t;

enum { ST_TONE_WHITE, ST_TONE_CYAN, ST_TONE_LAVA, ST_TONE_GOLD, ST_TONE_DIM };
typedef struct { char text[16]; uint8_t tone; int32_t x, y, tick; bool big; } st_popup_t;

typedef struct {
    // bird-animation.mjs: one record per key (actor id; -1 is the player)
    struct bird_motion {
        int32_t key;
        bool used;
        int32_t tick, x, vx, vy, facing;
        bool grounded, hurt;
        double run_phase, launch_at, drop_at, land_at, turn_at, flap_at, hurt_at, bank_at;
        int32_t frame;
    } motion[160];
    // the ring intro memo (scene.ringIntro): key = round * 2 + gold
    struct { int32_t key, tick; } ring_intro[40];
    int n_ring_intro;
    // session presentation
    st_feel_t feel;
    st_popup_t popups[12];
    int n_popups;
    char banner[48];
    int32_t banner_until;
    int32_t render_tick;
    double moon_phase;
} st_scene_t;

typedef struct {
    st_quad_t q[ST_MAX_QUADS];
    int n;
} st_quads_t;

// The game-over card's information (session recordRun).
typedef struct { int32_t final_score, round, best_score; bool is_new; bool valid; } st_gameover_info_t;

void st_scene_init(st_scene_t *sc);
// The session's reaction to one tick's events (feel, popups, banners). Call
// after st_step() with the state before the step's player position and the
// round's rings as they were before the step.
typedef struct { int32_t player_x, player_y; bool was_grounded; int32_t round_before, ring_set_before; } st_pre_tick_t;
st_pre_tick_t st_scene_pre_tick(const st_state_t *s);
void st_scene_on_events(st_scene_t *sc, const st_state_t *s, const st_events_t *ev, const st_pre_tick_t *pre);

// Builds one frame (advances render_tick and the moon). camera_top comes from
// st_camera_resolve(). items: the GAME OVER menu items (browser: NEW RUN, TITLE).
typedef struct { const char *const *items; int n_items, index; st_gameover_info_t info; } st_menu_t;
void st_scene_build(st_scene_t *sc, const st_state_t *s, int32_t camera_top, const st_menu_t *menu, st_quads_t *out);
st_feel_sample_t st_feel_sample(const st_feel_t *feel, int32_t tick);

// The browser tower camera (arcade/src/render/camera.mjs TowerCamera).
typedef struct { bool have; double top; int32_t last_tick; } st_camera_t;
void st_camera_reset(st_camera_t *c);
int32_t st_camera_resolve(st_camera_t *c, const st_state_t *s);   // returns cameraTop

// The browser's per-tick hash of an instance list (reference.mjs fnvInts).
uint32_t st_quads_hash(const st_quads_t *qs);

// Post effects the session passes with each frame.
double st_scene_impact(const st_scene_t *sc, const st_state_t *s);

#ifdef __cplusplus
}
#endif
