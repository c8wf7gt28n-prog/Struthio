// STRUTHIO HANDHELD · the 60 Hz simulation, ported stage for stage from
// arcade/src/sim/{state,world,physics,ai,step}.mjs and arcade/src/core/{fixed,rng}.mjs.
// Comments name the JS function each block mirrors. Arithmetic that can leave
// 32 bits (squared distances, rational comparisons) is done in int64_t.
#include "struthio_core.h"
#include <string.h>

// ---- rules (arcade/src/data/rules.mjs, sim / scoring / lifecycle) ---------------
enum {
    C_AIR_ACCEL = 15, C_AIR_DRAG = 2, C_FLAP_IMPULSE = 333, C_FLAP_VY_CLAMP = -640, C_GRAVITY = 21,
    C_GROUND_ACCEL = 18, C_GROUND_FRICTION = 14, C_HEAD_BUMP_VY = 196, C_LANCE_BOUNCE_VX = 265,
    C_LANCE_BOUNCE_VY = -111, C_LANCE_TIE_BAND = 512, C_LAVA_INVULNERABLE = 54, C_LAVA_RESCUE_VY = -563,
    C_LAVA_RESCUE_WINDOW = 18, C_LAVA_Y = 352, C_MAX_AIR_SPEED = 444, C_MAX_FALL = 896,
    C_MAX_GROUND_SPEED = 393, C_PLAYER_GRACE = 640, C_SKID_DECEL = 31, C_STALL_HUNT = 1200,
    C_WALL_BOUNCE_NUM = -45, C_WALL_BOUNCE_DEN = 100, C_WING_MAX = 64, C_WING_RECHARGE_ARM = 12,
    C_WING_RECHARGE_INTERVAL = 3,
};
enum {
    S_FIRST_LIFE = 30000, S_LIFE_EVERY = 100000, S_MAX_LIVES = 11, S_RING = 500, S_START_LIVES = 11,
    S_SURVIVAL = 3000, S_JOUST_TIER_STEP = 250,
};
static const int32_t S_EGG_CHAIN[4] = {250, 500, 750, 1000};
static const int32_t S_JOUST_CLASS_BASE[3] = {500, 750, 1000};   // BOUNDER HUNTER SHADOW
enum { L_DISMOUNT_MINIMUM = 30, L_HATCHING = 60, L_REMOUNTING = 90 };

// ---- state.mjs ------------------------------------------------------------------
const st_box_t ST_BIRD_BOX = {8, 21, 14, 25};
const st_box_t ST_RIDER_BOX = {11, 17, 15, 25};
const st_box_t ST_EGG_BOX = {11, 18, 17, 25};
#define LANCE_Y_SUB ((14 - 5) * 256)
enum { FLAP_COOLDOWN_TICKS = 7 };

// ---- fixed.mjs / rng.mjs --------------------------------------------------------
static inline int64_t imax(int64_t a, int64_t b) { return a > b ? a : b; }
static inline int64_t imin(int64_t a, int64_t b) { return a < b ? a : b; }
static inline int64_t iabs(int64_t a) { return a < 0 ? -a : a; }
static inline int64_t clampi(int64_t v, int64_t lo, int64_t hi) { return v < lo ? lo : v > hi ? hi : v; }
static inline int64_t tdiv(int64_t a, int64_t b) { return a / b; }   // C99 truncates toward zero
static inline int64_t modi(int64_t v, int64_t m) { int64_t r = v % m; return r < 0 ? r + m : r; }
static inline int64_t floor_div(int64_t v, int64_t d) {
    int64_t q = v / d, r = v % d;
    return (r != 0 && ((r < 0) != (d < 0))) ? q - 1 : q;
}
static inline int64_t px(int64_t logical) { return logical * ST_SUB; }
static int64_t nearest_wrap_shift(int64_t dx) {
    int64_t c0 = iabs(dx), cm = iabs(dx - ST_WRAP), cp = iabs(dx + ST_WRAP), best = 0, best_abs = c0;
    if (cm < best_abs) { best = -ST_WRAP; best_abs = cm; }
    if (cp < best_abs) { best = ST_WRAP; }
    return best;
}
static inline int64_t wrapped_delta(int64_t from, int64_t to) { int64_t dx = to - from; return dx + nearest_wrap_shift(dx); }
static inline int compare_rational(int64_t an, int64_t ad, int64_t bn, int64_t bd) {
    int64_t l = an * bd, r = bn * ad;
    return l == r ? 0 : l < r ? -1 : 1;
}
static inline int sign(int64_t v) { return v > 0 ? 1 : v < 0 ? -1 : 0; }

#define ZERO_REMAP 0x6d2b79f5u
static uint32_t seed_state(uint32_t seed) { return seed == 0 ? ZERO_REMAP : seed; }
static uint32_t next_u32(uint32_t *state) {
    uint32_t x = *state;
    if (x == 0) x = ZERO_REMAP;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

typedef struct { int64_t l, r, t, b; } box64_t;
static box64_t entity_box(int64_t x, int64_t y, const st_box_t *b) {
    box64_t o = {x + b->l * 256, x + b->r * 256, y + b->t * 256, y + b->b * 256};
    return o;
}

// ---- events ---------------------------------------------------------------------
static const char *const EVENT_NAMES[ST_EV_COUNT] = {
    "ARENA_ACTIVATE", "TOWER_GO", "FLAP", "FLAP_CHORD", "DART", "LAVA_RESCUE", "LAVA_CONTACT", "PLAYER_DEATH",
    "JOUST_CLASH", "JOUST_WIN", "SCORE_AWARD", "EXTRA_LIFE", "EGG", "MOUNT", "HATCH", "REMOUNT", "DESPAWN",
    "SPAWN", "RING", "GOLD_RING_OPEN", "TOWER_BLAST", "ROUND_CLEAR", "CHECKPOINT_REQUEST", "ROUND_START",
    "TOWER_CHECK", "GAMEOVER", "RESPAWN_SCHEDULED",
};
const char *st_event_name(st_event_type_t t) { return (unsigned)t < ST_EV_COUNT ? EVENT_NAMES[t] : "?"; }
const st_field_t *st_event_field(const st_event_t *e, const char *key) {
    for (int i = 0; i < e->n; i++) if (strcmp(e->f[i].key, key) == 0) return &e->f[i];
    return NULL;
}

static st_events_t *g_out;      // the tick's event sink (single-threaded sim)
static st_event_t *ev(st_event_type_t type) {
    st_events_t *o = g_out;
    if (o->n >= ST_MAX_EVENTS) { static st_event_t sink; memset(&sink, 0, sizeof sink); return &sink; }
    st_event_t *e = &o->e[o->n++];
    memset(e, 0, sizeof *e);
    e->type = (uint8_t)type;
    return e;
}
static st_event_t *fi(st_event_t *e, const char *k, int64_t v) {
    if (e->n < ST_MAX_EVENT_FIELDS) e->f[e->n++] = (st_field_t){k, ST_F_INT, (int32_t)v, NULL};
    return e;
}
static st_event_t *fs(st_event_t *e, const char *k, const char *v) {
    if (e->n < ST_MAX_EVENT_FIELDS) e->f[e->n++] = (st_field_t){k, ST_F_STR, 0, v};
    return e;
}
static st_event_t *fb(st_event_t *e, const char *k, bool v) {
    if (e->n < ST_MAX_EVENT_FIELDS) e->f[e->n++] = (st_field_t){k, ST_F_BOOL, v ? 1 : 0, NULL};
    return e;
}
static int count_events(st_event_type_t t) {
    int n = 0;
    for (int i = 0; i < g_out->n; i++) if (g_out->e[i].type == t) n++;
    return n;
}

static const char *const CLASS_NAMES[3] = {"BOUNDER", "HUNTER", "SHADOW"};
static const char *const GHOST_NAMES[4] = {"BLINKY", "PINKY", "INKY", "CLYDE"};
static const char *const SIDE_NAMES[3] = {NULL, "LEFT", "RIGHT"};
static const char *const FLAP_NAMES[4] = {"LEGACY", "LEFT", "RIGHT", "STRAIGHT"};

// ---- tower.mjs --------------------------------------------------------------------
typedef struct {
    int32_t cap, fill_gap, replace_delay, tier_base, egg_ticks, ring_set, clear_bonus;
    double class_shift;
} tower_rules_t;
static tower_rules_t tower_rules(int32_t round) {
    int64_t r = imax(1, round), k = r - 1;
    double shift = 0.12 * (double)k;
    tower_rules_t o = {
        (int32_t)imin(8, 3 + k), (int32_t)imax(40, 90 - 8 * k), (int32_t)imax(60, 240 - 36 * k),
        (int32_t)imin(4, 1 + (k >> 1)), (int32_t)imax(150, 360 - 30 * k), (int32_t)modi(k, ST_RING_SETS),
        (int32_t)imin(15000, 5000 + 1000 * k), shift < 0.5 ? shift : 0.5,
    };
    return o;
}
int st_ring_set_for_round(int32_t round) { return tower_rules(round).ring_set; }
enum { TOWER_ZONE = 288, TOWER_DESPAWN = 300, TOWER_ARRIVAL_NEAR = 220, TOWER_ARRIVAL_FAR = 252,
       TOWER_FIRST_ARRIVAL = 45, ROUND_CLEAR_HOLD = 75, ROUND_SWEEP_TICKS = 60 };
static void tower_spawn_for(int32_t index, int32_t out[2]) {
    const st_tower_platform_t *p = (index >= 0 && index < ST_TOWER_PLATFORMS) ? &ST_TOWER[index] : &ST_TOWER[0];
    if (p == &ST_TOWER[0]) { out[0] = 32; out[1] = ST_TOWER_GROUND - 25; return; }
    out[0] = (int32_t)modi(p->x + (p->w >> 1) - 14, 256);
    out[1] = p->y - 25;
}
static double tower_altitude(int64_t y_px) {
    double a = (double)(ST_TOWER_GROUND - y_px) / (double)(ST_TOWER_GROUND - ST_TOWER_TOP);
    return a < 0 ? 0 : a > 1 ? 1 : a;
}
static int tower_band(int64_t y_px) { double a = tower_altitude(y_px); return a < 1.0 / 3 ? 0 : a < 2.0 / 3 ? 1 : 2; }
static int tower_class_for(int64_t y_px, const tower_rules_t *rr, uint32_t draw) {
    double eff = tower_altitude(y_px) + rr->class_shift;
    int w0, w1;
    if (eff < 1.0 / 3) { w0 = 80; w1 = 20; }
    else if (eff < 2.0 / 3) { w0 = 30; w1 = 55; }
    else if (eff < 1) { w0 = 10; w1 = 45; }
    else { w0 = 0; w1 = 40; }
    uint32_t pick = draw % 100;
    return (int)pick < w0 ? ST_CLASS_BOUNDER : (int)pick < w0 + w1 ? ST_CLASS_HUNTER : ST_CLASS_SHADOW;
}

// The tick's content (towerContent(s) taken at the start of the tick).
typedef struct {
    int32_t spawn[2];
    tower_rules_t rules;
    const st_ring_t *rings;
} content_t;
static content_t tower_content(const st_state_t *s) {
    content_t c;
    tower_spawn_for(s->tower.check, c.spawn);
    c.rules = tower_rules(s->tower.round);
    c.rings = ST_RING_SET[c.rules.ring_set];
    return c;
}

// ---- world.mjs --------------------------------------------------------------------
static int64_t ease(int64_t age, int64_t half) {
    int64_t q = imax(0, imin(256, tdiv(age * 256, half)));
    return tdiv(q * q * (768 - 2 * q), 65536);
}
static void eased_motion(const st_tower_platform_t *m, int64_t tick, int64_t *period_out, int64_t *delta_out) {
    int64_t period = imax(2, m->period);
    int64_t dwell = imax(0, imin((period >> 2) - 1, 0));
    int64_t travel = imax(2, period - dwell * 2), half = imax(1, travel >> 1);
    int64_t u = modi(tick, period), q;
    if (u < dwell) q = 0;
    else if (u < dwell + half) q = ease(u - dwell, half);
    else if (u < dwell + half + dwell) q = 256;
    else q = 256 - ease(u - (dwell + half + dwell), half);
    int64_t amplitude = imax(0, m->amplitude);
    *period_out = period;
    *delta_out = -amplitude + tdiv(amplitude * 2 * q, 256);
}
static void platform_at(int idx, int64_t t, st_platform_t *out) {
    const st_tower_platform_t *p = &ST_TOWER[idx];
    out->id = (int16_t)idx;
    out->collidable = true;
    out->rect[0] = p->x; out->rect[1] = p->y; out->rect[2] = p->w; out->rect[3] = p->h;
    if (p->motion != ST_MOTION_STATIC) {
        int64_t period, delta;
        eased_motion(p, t, &period, &delta);
        out->tick = (int32_t)modi(t, period);
        out->phase = p->motion;
        if (p->motion == ST_MOTION_DRIFT_X_SOFT) out->rect[0] = (int32_t)(p->x + delta);
        else out->rect[1] = (int32_t)(p->y + delta);
        return;
    }
    out->phase = ST_MOTION_STATIC;
    out->tick = 0;
}
static void step_world(st_state_t *s) {
    for (int i = 0; i < s->world.n_platforms; i++) {
        st_platform_t *w = &s->world.platforms[i];
        platform_at(w->id, (int64_t)w->tick + 1, w);
    }
    s->world.lava_y = (int32_t)px(C_LAVA_Y);
}
static void empty_player(st_player_t *p, int32_t x, int32_t y) {
    memset(p, 0, sizeof *p);
    p->x = (int32_t)px(x); p->y = (int32_t)px(y);
    p->grounded = ST_NO_PLATFORM;
    p->facing = 1;
    p->wing = 64;
    p->lava_phase = ST_LAVA_SAFE;
}
static void empty_tower(st_tower_t *t, int32_t round) { memset(t, 0, sizeof *t); t->round = round; }

void st_state_init(st_state_t *s, uint32_t seed) {
    memset(s, 0, sizeof *s);
    s->sim.shell = ST_SHELL_ATTRACT;
    s->sim.next_actor_id = 1;
    s->sim.lives = S_START_LIVES;
    s->rng = seed_state(seed);
    empty_player(&s->player, 32, 311);
    s->world.lava_y = (int32_t)px(C_LAVA_Y);
    empty_tower(&s->tower, 1);
    s->run.clean = true;
}
void st_start_run(st_state_t *s, st_events_t *out) {          // step.mjs startRun + world.mjs activateTower
    out->n = 0;
    g_out = out;
    s->sim.shell = ST_SHELL_PLAY;
    content_t c = tower_content(s);
    s->world.n_platforms = ST_TOWER_PLATFORMS;
    for (int i = 0; i < ST_TOWER_PLATFORMS; i++) platform_at(i, ST_TOWER[i].phase_offset, &s->world.platforms[i]);
    s->world.lava_y = (int32_t)px(C_LAVA_Y);
    s->n_actors = 0;
    int16_t keep_wing = s->player.wing;
    empty_player(&s->player, c.spawn[0], c.spawn[1]);
    s->player.wing = keep_wing;
    s->tower.ring_mask = 0;
    s->tower.cooldown = 0;
    s->run.egg_chain = 0;
    s->run.clean = true;
    fs(ev(ST_EV_ARENA_ACTIVATE), "contentId", "TOWER");
}

// ---- physics.mjs ------------------------------------------------------------------
typedef struct { int32_t x, y, vx, vy; int16_t grounded; } body_t;
typedef struct { int64_t pl, pr, top, bottom; } span_t;
static const int64_t SHIFTS[3] = {0, -ST_WRAP, ST_WRAP};
static bool overlaps_x(int64_t l, int64_t r, int64_t pl, int64_t pr) {
    for (int i = 0; i < 3; i++) if (l + SHIFTS[i] < pr && r + SHIFTS[i] > pl) return true;
    return false;
}
static span_t plat_span(const st_platform_t *p) {
    span_t s = {(int64_t)p->rect[0] * 256, (int64_t)(p->rect[0] + p->rect[2]) * 256,
                (int64_t)p->rect[1] * 256, (int64_t)(p->rect[1] + p->rect[3]) * 256};
    return s;
}
static const st_platform_t *find_platform(const st_state_t *s, int id) {
    for (int i = 0; i < s->world.n_platforms; i++) if (s->world.platforms[i].id == id) return &s->world.platforms[i];
    return NULL;
}
typedef struct { int16_t landed; bool lava, head_bump; } integrate_result_t;
static integrate_result_t integrate(body_t *e, const st_box_t *box, int64_t ax, const st_state_t *world,
                                    bool grounded_opt, int corner_px) {
    integrate_result_t res = {ST_NO_PLATFORM, false, false};
    int64_t max_vx = grounded_opt ? C_MAX_GROUND_SPEED : C_MAX_AIR_SPEED;
    e->vx = (int32_t)clampi(e->vx + ax, -max_vx, max_vx);
    bool was_grounded = e->grounded != ST_NO_PLATFORM;
    if (!was_grounded || e->vy < 0) e->vy = (int32_t)imin(e->vy + C_GRAVITY, C_MAX_FALL);
    else e->vy = 0;
    int64_t old_x = e->x, old_y = e->y;
    box64_t ob = entity_box(old_x, old_y, box);
    int64_t new_x = modi(old_x + e->vx, ST_WRAP), new_y = old_y + e->vy;
    box64_t nb = entity_box(new_x, new_y, box);
    int n = world->world.n_platforms;
    const st_platform_t *plats = world->world.platforms;
    if (was_grounded && e->vy >= 0) {
        const st_platform_t *p = NULL;
        for (int i = 0; i < n; i++) if (plats[i].collidable && plats[i].id == e->grounded) { p = &plats[i]; break; }
        if (p) {
            span_t ps = plat_span(p);
            if (overlaps_x(nb.l, nb.r, ps.pl, ps.pr)) {
                new_y = ps.top - box->b * 256;
                e->vy = 0;
                res.landed = p->id;
            }
        }
    }
    if (res.landed == ST_NO_PLATFORM && e->vy > 0) {
        bool have = false;
        int64_t bnum = 0, bden = 1, btop = 0;
        int bid = 0;
        for (int i = 0; i < n; i++) {
            const st_platform_t *p = &plats[i];
            if (!p->collidable) continue;
            span_t ps = plat_span(p);
            if (ob.b <= ps.top && nb.b >= ps.top) {
                int64_t num = ps.top - ob.b, den = nb.b - ob.b;
                if (den <= 0) continue;
                int64_t xc = old_x + tdiv((int64_t)e->vx * num, den);
                box64_t cb = entity_box(xc, 0, box);
                if (!overlaps_x(cb.l, cb.r, ps.pl, ps.pr)) continue;
                int cmp = have ? compare_rational(num, den, bnum, bden) : 0;
                if (!have || cmp < 0 || (cmp == 0 && p->id < bid)) {
                    have = true; bnum = num; bden = den; bid = p->id; btop = ps.top;
                }
            }
        }
        if (have) { new_y = btop - box->b * 256; e->vy = 0; res.landed = (int16_t)bid; }
    }
    if (res.landed == ST_NO_PLATFORM && e->vy < 0) {
        int64_t corner = (int64_t)corner_px * 256;
        for (int i = 0; i < n; i++) {
            const st_platform_t *p = &plats[i];
            if (!p->collidable) continue;
            span_t ps = plat_span(p);
            if (ob.t >= ps.bottom && nb.t < ps.bottom && overlaps_x(nb.l, nb.r, ps.pl, ps.pr)) {
                if (corner > 0) {
                    int64_t nudge = 0;
                    for (int k = 0; k < 3; k++) {
                        int64_t l = nb.l + SHIFTS[k], r = nb.r + SHIFTS[k];
                        if (!(l < ps.pr && r > ps.pl)) continue;
                        int64_t into_left = r - ps.pl, into_right = ps.pr - l;
                        if (into_left <= corner && into_left <= into_right) nudge = -into_left;
                        else if (into_right <= corner) nudge = into_right;
                        break;
                    }
                    if (nudge != 0) { new_x = modi(new_x + nudge, ST_WRAP); nb = entity_box(new_x, new_y, box); continue; }
                }
                new_y = ps.bottom - box->t * 256; e->vy = C_HEAD_BUMP_VY; res.head_bump = true; break;
            }
        }
    }
    int64_t top_limit = (int64_t)ST_TOWER_PLAY_TOP * 256;      // physicsOf(R): playTop is the moon
    if (entity_box(new_x, new_y, box).t < top_limit) {
        new_y = top_limit - box->t * 256;
        if (e->vy < 0) { e->vy = C_HEAD_BUMP_VY; res.head_bump = true; }
    }
    nb = entity_box(new_x, new_y, box);
    for (int i = 0; i < n; i++) {
        const st_platform_t *p = &plats[i];
        if (!p->collidable) continue;
        span_t ps = plat_span(p);
        if (res.landed == p->id) continue;
        if (nb.b <= ps.top || nb.t >= ps.bottom) continue;
        for (int k = 0; k < 3; k++) {
            int64_t sft = SHIFTS[k], l = nb.l + sft, r = nb.r + sft;
            if (l < ps.pr && r > ps.pl) {
                if (e->vx > 0) new_x = modi(ps.pl - box->r * 256 - sft, ST_WRAP);
                else if (e->vx < 0) new_x = modi(ps.pr - box->l * 256 - sft, ST_WRAP);
                e->vx = (int32_t)tdiv((int64_t)e->vx * C_WALL_BOUNCE_NUM, C_WALL_BOUNCE_DEN);
                nb = entity_box(new_x, new_y, box);
                break;
            }
        }
    }
    e->x = (int32_t)new_x; e->y = (int32_t)new_y;
    e->grounded = res.landed;
    res.lava = entity_box(new_x, new_y, box).b >= world->world.lava_y;
    return res;
}
static bool in_ring(box64_t b, const st_ring_t *ring, int slack_px) {
    int64_t cx = tdiv(b.l + b.r, 2), cy = tdiv(b.t + b.b, 2);
    int64_t rx = (int64_t)ring->x * 256, ry = (int64_t)ring->y * 256;
    int64_t dx = cx - rx;
    dx += nearest_wrap_shift(dx);
    int64_t dy = cy - ry, r = (int64_t)(ring->radius + slack_px) * 256;
    return dx * dx + dy * dy <= r * r;
}
static bool boxes_overlap(box64_t a, box64_t b) {
    if (a.b <= b.t || a.t >= b.b) return false;
    return overlaps_x(a.l, a.r, b.l, b.r);
}
static int16_t standing_platform(int64_t x, int64_t y, const st_box_t *box, const st_platform_t *plats, int n) {
    box64_t b = entity_box(x, y, box);
    int best = ST_NO_PLATFORM;
    for (int i = 0; i < n; i++) {
        const st_platform_t *p = &plats[i];
        if (!p->collidable) continue;
        span_t ps = plat_span(p);
        if (b.b == ps.top && overlaps_x(b.l, b.r, ps.pl, ps.pr) && (best == ST_NO_PLATFORM || p->id < best)) best = p->id;
    }
    return (int16_t)best;
}

// ---- ai.mjs -----------------------------------------------------------------------
#define CENTER_X (128 * 256)
#define CLYDE_RADIUS (72 * 256)
static const int CLASS_WINDOW[3] = {24, 12, 8};
static const int CLASS_FLAP_PERIOD[3] = {10, 8, 8};
typedef struct { int dir; bool flap; } intent_t;
static intent_t rival_intent(st_state_t *s, st_actor_t *a, const int64_t corner[2], bool player_active, int64_t center_y) {
    const st_player_t *p = &s->player;
    int32_t ph = a->phase;
    int window = ph >> 7, flap_cd = (ph >> 3) & 15;
    bool flap_wanted = (ph & 4) != 0;
    int dir = (ph & 3) == 1 ? -1 : (ph & 3) == 2 ? 1 : 0;
    bool stall = a->timer >= C_STALL_HUNT;
    int ghost = stall ? ST_GHOST_BLINKY : a->ghost;
    if (window == 0) {
        uint32_t draw = next_u32(&s->rng);
        a->rng_draws += 1;
        int tier = (int)imax(0, a->tier);
        window = (int)imax(4, CLASS_WINDOW[a->cls] + (5 - tier) * 3);
        if (stall) window = 4;
        int64_t tx, ty;
        if (ghost == ST_GHOST_PINKY) { tx = p->x + 4 * (int64_t)p->vx; ty = p->y + 4 * (int64_t)p->vy; }
        else if (ghost == ST_GHOST_INKY) {
            int64_t lx = p->x + 4 * (int64_t)p->vx, ly = p->y + 4 * (int64_t)p->vy;
            tx = 2 * (int64_t)CENTER_X - lx; ty = 2 * center_y - ly;
        } else if (ghost == ST_GHOST_CLYDE) {
            int64_t dx = wrapped_delta(a->x, p->x), dy = (int64_t)p->y - a->y;
            if (iabs(dx) > CLYDE_RADIUS || iabs(dy) > CLYDE_RADIUS) { tx = p->x; ty = p->y; }
            else { tx = corner[0] * 256; ty = corner[1] * 256; }
        } else { tx = p->x; ty = p->y; }
        int64_t dx = wrapped_delta(a->x, tx);
        dir = dx > 512 ? 1 : dx < -512 ? -1 : 0;
        int64_t lance_gap = (ty + LANCE_Y_SUB) - ((int64_t)a->y + LANCE_Y_SUB);
        int64_t climb = a->cls == ST_CLASS_BOUNDER ? -10 * 256 : a->cls == ST_CLASS_HUNTER ? -2 * 256 : 4 * 256;
        flap_wanted = lance_gap < climb;
        uint32_t r = draw & 15;
        if (a->cls == ST_CLASS_BOUNDER && r == 0) dir = -dir;
        if (a->cls == ST_CLASS_SHADOW && (r & 3) == 0) dir = -dir;
        if (r == 15 && !flap_wanted) flap_wanted = true;
        if ((int)((draw >> 4) % 6) > tier && !stall) dir = 0;
        if (!player_active) { dir = 0; flap_wanted = a->y > center_y; }
        if ((int64_t)a->y + 25 * 256 > (int64_t)s->world.lava_y - 24 * 256) flap_wanted = true;
        flap_cd = 0;
    } else {
        window -= 1;
    }
    bool flap = false;
    if (flap_wanted) {
        if (flap_cd == 0) { flap = true; flap_cd = CLASS_FLAP_PERIOD[a->cls]; } else flap_cd -= 1;
    } else if (flap_cd > 0) flap_cd -= 1;
    a->phase = (window << 7) | ((flap_cd & 15) << 3) | (flap_wanted ? 4 : 0) | (dir == -1 ? 1 : dir == 1 ? 2 : 0);
    intent_t it = {dir, flap};
    return it;
}

// ---- step.mjs ---------------------------------------------------------------------
static bool LIVE(uint8_t lc) {
    return lc == ST_LC_SPAWNING || lc == ST_LC_MOUNTED || lc == ST_LC_REMOUNTING || lc == ST_LC_HATCHING;
}
static bool player_active(const st_state_t *s) { return s->player.invulnerable_ticks <= ST_SHIMMER_TICKS; }
static const st_box_t *actor_box_of(const st_actor_t *a) {
    return a->kind == ST_KIND_RIDER ? &ST_RIDER_BOX : a->kind == ST_KIND_EGG ? &ST_EGG_BOX : &ST_BIRD_BOX;
}
static box64_t actor_box(const st_actor_t *a) { return entity_box(a->x, a->y, actor_box_of(a)); }
static st_actor_t *find_actor(st_state_t *s, int32_t id) {
    for (int i = 0; i < s->n_actors; i++) if (s->actors[i].id == id) return &s->actors[i];
    return NULL;
}
static int bit_count(uint32_t m) { int c = 0; while (m) { c += m & 1; m >>= 1; } return c; }

// Per-tick scratch (the JS s._lifecycle / s._locked / s._deathThisTick / s._pendingGameOver).
enum { REQ_DISMOUNTED, REQ_EGG, REQ_REMOVED };
typedef struct { int32_t id; int to; } lc_req_t;
static struct {
    bool locked, death, pending_game_over;
    int n_req;
    lc_req_t req[ST_MAX_ACTORS * 4];
} T_;
static void push_req(int32_t id, int to) {
    if (T_.n_req < (int)(sizeof T_.req / sizeof T_.req[0])) T_.req[T_.n_req++] = (lc_req_t){id, to};
}

static int64_t add_score(st_state_t *s, int64_t amount, const char *kind, const char *xk1, int64_t xv1,
                         const char *xk2, int64_t xv2, const char *xs_key, const char *xs_val) {
    int64_t value = imax(0, amount);
    if (!value) return 0;
    s->sim.score += (int32_t)value;
    st_event_t *e = fi(fs(ev(ST_EV_SCORE_AWARD), "kind", kind), "amount", value);
    if (xs_key) fs(e, xs_key, xs_val);
    if (xk1) fi(e, xk1, xv1);
    if (xk2) fi(e, xk2, xv2);
    while (s->sim.score >= (s->run.life_bands == 0 ? S_FIRST_LIFE : (int64_t)S_LIFE_EVERY * s->run.life_bands)) {
        s->run.life_bands += 1;
        if (s->sim.lives < S_MAX_LIVES) { s->sim.lives += 1; fi(ev(ST_EV_EXTRA_LIFE), "lives", s->sim.lives); }
    }
    return value;
}
static int64_t joust_value(const st_actor_t *a) {
    return S_JOUST_CLASS_BASE[a->cls] + S_JOUST_TIER_STEP * (imax(1, a->tier) - 1);
}
static int64_t egg_value(int32_t chain) { return S_EGG_CHAIN[imin(chain, 3)]; }

static void player_death(st_state_t *s, const content_t *c, const char *cause) {
    fs(ev(ST_EV_PLAYER_DEATH), "cause", cause);
    s->run.deaths += 1; s->run.egg_chain = 0; s->run.clean = false;
    s->tower.mercy = (int32_t)imin(9, s->tower.mercy + 1);
    s->sim.lives -= 1;
    empty_player(&s->player, c->spawn[0], c->spawn[1]);
    s->player.invulnerable_ticks = ST_RESPAWN_HIDDEN_TICKS + ST_SHIMMER_TICKS;
    if (s->sim.lives <= 0) { s->sim.lives = 0; T_.pending_game_over = true; }
    T_.death = true;
}
static void stage_timers(st_state_t *s) {
    st_player_t *p = &s->player;
    if (p->flap_cooldown > 0) p->flap_cooldown -= 1;
    if (p->invulnerable_ticks > 0) p->invulnerable_ticks -= 1;
    if (p->lava_phase == ST_LAVA_SINK && p->lava_ticks > 0) p->lava_ticks -= 1;
    for (int i = 0; i < s->n_actors; i++) {
        st_actor_t *a = &s->actors[i];
        if (a->lifecycle == ST_LC_MOUNTED) { if (a->timer < 1200) a->timer += 1; }
        else if (a->timer > 0) a->timer -= 1;
    }
}

typedef struct {
    int64_t ax;
    bool flap, chord_correction, dart;
    st_flap_kind_t kind;
    st_side_t dart_side;
} human_intent_t;
static human_intent_t human_intent(st_player_t *p, bool active, const st_input_t *in) {
    human_intent_t o;
    memset(&o, 0, sizeof o);
    if (!active) return o;
    int h = 0;
    if (in->left && !in->right) h = -1; else if (in->right && !in->left) h = 1;
    if (h != 0) p->facing = (int8_t)h;
    bool grounded = p->grounded != ST_NO_PLATFORM;
    int64_t ax = 0;
    if (h != 0) {
        if (grounded && sign(p->vx) == -h && p->vx != 0) ax = h * C_SKID_DECEL;
        else ax = h * (grounded ? C_GROUND_ACCEL : C_AIR_ACCEL);
    } else {
        int64_t d = grounded ? C_GROUND_FRICTION : C_AIR_DRAG;
        ax = p->vx > 0 ? -imin(d, p->vx) : p->vx < 0 ? imin(d, -(int64_t)p->vx) : 0;
    }
    st_flap_kind_t kind = in->flap_edge ? in->flap_kind : ST_FLAP_NONE;
    if (in->flap_edge && p->flap_cooldown == 0 && p->wing > 0) {
        o.flap = true;
        p->wing -= 1;
        p->flap_cooldown = FLAP_COOLDOWN_TICKS;
        p->footing_ticks = 0;
        fs(ev(ST_EV_FLAP), "kind", FLAP_NAMES[kind]);
    } else if (in->flap_edge && in->chord_edge && kind == ST_FLAP_STRAIGHT && p->flap_cooldown > 0) {
        o.flap = true; o.chord_correction = true;
        ev(ST_EV_FLAP_CHORD);
    }
    st_side_t side = in->dart_side != ST_SIDE_NONE ? in->dart_side : (p->facing < 0 ? ST_SIDE_LEFT : ST_SIDE_RIGHT);
    o.dart = in->dart_edge;
    if (o.dart) fs(ev(ST_EV_DART), "side", SIDE_NAMES[side]);
    if (o.flap && kind == ST_FLAP_STRAIGHT) ax = 0;
    o.ax = ax; o.kind = kind; o.dart_side = side;
    return o;
}

enum { CORNER_CORRECT_PX = 4, SINK_NONE = 0, SINK_SINKING, SINK_DEATH };
static int integrate_human(st_state_t *s, const human_intent_t *pi) {
    st_player_t *p = &s->player;
    if (pi->flap) {
        if (pi->kind == ST_FLAP_LEFT || pi->kind == ST_FLAP_RIGHT) {
            int side = pi->kind == ST_FLAP_LEFT ? -1 : 1;
            p->vy = (int32_t)imax((int64_t)p->vy - (C_FLAP_IMPULSE * 82 / 100), C_FLAP_VY_CLAMP);
            p->vx = (int32_t)imax(-C_MAX_AIR_SPEED, imin(C_MAX_AIR_SPEED, (int64_t)p->vx + side * 210));
            p->facing = (int8_t)side;
        } else if (pi->kind == ST_FLAP_STRAIGHT) {
            p->vy = (int32_t)imax((int64_t)p->vy - (pi->chord_correction ? 96 : C_FLAP_IMPULSE), C_FLAP_VY_CLAMP);
            p->vx = 0;
        } else p->vy = (int32_t)imax((int64_t)p->vy - C_FLAP_IMPULSE, C_FLAP_VY_CLAMP);
        p->grounded = ST_NO_PLATFORM;
    }
    if (pi->dart) {
        int side = pi->dart_side == ST_SIDE_LEFT ? -1 : 1;
        const st_actor_t *best = NULL;
        int64_t best_dx = 0, best_key = 0;
        for (int i = 0; i < s->n_actors; i++) {           // dartTargets: mounted rivals
            const st_actor_t *a = &s->actors[i];
            if (a->lifecycle != ST_LC_MOUNTED) continue;
            int64_t dx = wrapped_delta(p->x, a->x), dy = (int64_t)a->y - p->y;
            if (!(dx * side > 0 && iabs(dx) <= 72 * 256 && dy >= 4 * 256 && dy <= 104 * 256 && iabs(dx) <= dy)) continue;
            int64_t key = dy + iabs(dx);
            if (!best || key < best_key || (key == best_key && a->id < best->id)) { best = a; best_dx = dx; best_key = key; }
        }
        p->vy = (int32_t)imax(p->vy, imin(C_MAX_FALL, 704));
        p->vx = best ? (int32_t)imax(-C_MAX_AIR_SPEED, imin(C_MAX_AIR_SPEED, tdiv(best_dx, 12)))
                     : (int32_t)imax(-C_MAX_AIR_SPEED, imin(C_MAX_AIR_SPEED, (int64_t)p->vx + side * 96));
        p->facing = (int8_t)side; p->grounded = ST_NO_PLATFORM; p->footing_ticks = 0;
    }
    if (p->lava_phase == ST_LAVA_SINK) {
        if (pi->flap) {
            p->lava_phase = ST_LAVA_RESCUED; p->vy = C_LAVA_RESCUE_VY;
            p->invulnerable_ticks = (int32_t)imax(p->invulnerable_ticks, C_LAVA_INVULNERABLE);
            p->lava_ticks = 0;
            ev(ST_EV_LAVA_RESCUE);
        } else {
            p->vy = 64; p->y += p->vy; p->vx = 0;
            return p->lava_ticks == 0 ? SINK_DEATH : SINK_SINKING;
        }
    }
    bool was_grounded = p->grounded != ST_NO_PLATFORM;
    body_t b = {p->x, p->y, p->vx, p->vy, p->grounded};
    integrate_result_t r = integrate(&b, &ST_BIRD_BOX, pi->ax, s, was_grounded, CORNER_CORRECT_PX);
    p->x = b.x; p->y = b.y; p->vx = b.vx; p->vy = b.vy; p->grounded = b.grounded;
    if (r.landed != ST_NO_PLATFORM) {
        p->footing_ticks += 1;
        if (p->footing_ticks >= C_WING_RECHARGE_ARM && (p->footing_ticks - C_WING_RECHARGE_ARM) % C_WING_RECHARGE_INTERVAL == 0 &&
            p->wing < C_WING_MAX) p->wing += 1;
    } else p->footing_ticks = 0;
    if (r.lava) {
        if (p->lava_phase == ST_LAVA_SAFE) { p->lava_phase = ST_LAVA_SINK; p->lava_ticks = C_LAVA_RESCUE_WINDOW; ev(ST_EV_LAVA_CONTACT); }
    } else if (p->lava_phase == ST_LAVA_RESCUED) p->lava_phase = ST_LAVA_SAFE;
    return SINK_NONE;
}

// fallSteerVx: riders and eggs steer onto the nearest island below that they
// can still reach before landing.
enum { EGG_EDGE_MARGIN_PX = 5 };
static int32_t fall_steer_vx(const st_state_t *s, const st_actor_t *a, const st_box_t *box) {
    int64_t feet = (int64_t)a->y + box->b * 256, cx = a->x + tdiv((int64_t)(box->l + box->r) * 256, 2);
    bool have = false;
    int64_t btop = 0, bdx = 0, bt = 0;
    for (int i = 0; i < s->world.n_platforms; i++) {
        const st_platform_t *p = &s->world.platforms[i];
        if (!p->collidable) continue;
        int64_t top = (int64_t)p->rect[1] * 256;
        if (top < feet) continue;
        int64_t t = 0, y = 0, v = a->vy;
        while (y < top - feet && t < 400) { v = imin(v + C_GRAVITY, C_MAX_FALL); y += v; t += 1; }
        int64_t margin = imin(EGG_EDGE_MARGIN_PX, p->rect[2] >> 2) * 256;
        int64_t l = (int64_t)p->rect[0] * 256 + margin, r = (int64_t)(p->rect[0] + p->rect[2]) * 256 - margin;
        int64_t to_l = wrapped_delta(cx, l), to_r = wrapped_delta(cx, r);
        bool inside = wrapped_delta(l, cx) >= 0 && wrapped_delta(cx, r) >= 0;
        int64_t dx = inside ? 0 : (iabs(to_l) <= iabs(to_r) ? to_l : to_r);
        if (iabs(dx) > imax(1, t) * C_MAX_AIR_SPEED) continue;
        if (!have || top < btop || (top == btop && iabs(dx) < iabs(bdx))) { have = true; btop = top; bdx = dx; bt = t; }
    }
    if (!have) return a->vx;
    return (int32_t)imax(-C_MAX_AIR_SPEED, imin(C_MAX_AIR_SPEED, tdiv(bdx, imax(1, bt))));
}

static void integrate_all(st_state_t *s, const content_t *c, const human_intent_t *pi, const intent_t *intents) {
    st_player_t *p = &s->player;
    // previousWorld: platform rects before the world steps, and each actor's footing on them.
    int32_t before_rect[ST_TOWER_PLATFORMS][2];
    int16_t before_id[ST_TOWER_PLATFORMS];
    int nplat = s->world.n_platforms;
    for (int i = 0; i < nplat; i++) {
        before_id[i] = s->world.platforms[i].id;
        before_rect[i][0] = s->world.platforms[i].rect[0];
        before_rect[i][1] = s->world.platforms[i].rect[1];
    }
    int16_t footing[ST_MAX_ACTORS];
    for (int i = 0; i < s->n_actors; i++) {
        const st_actor_t *a = &s->actors[i];
        const st_box_t *box = a->lifecycle == ST_LC_MOUNTED ? &ST_BIRD_BOX : a->lifecycle == ST_LC_DISMOUNTED ? &ST_RIDER_BOX
                            : a->lifecycle == ST_LC_EGG ? &ST_EGG_BOX : NULL;
        footing[i] = box ? standing_platform(a->x, a->y, box, s->world.platforms, nplat) : ST_NO_PLATFORM;
    }
    step_world(s);
    // inherit: an entity standing on a moving island moves with it.
#define INHERIT(EX, EY, PID) do { int pid_ = (PID); if (pid_ != ST_NO_PLATFORM) { \
        int bi_ = -1; for (int k_ = 0; k_ < nplat; k_++) if (before_id[k_] == pid_) { bi_ = k_; break; } \
        const st_platform_t *af_ = find_platform(s, pid_); \
        if (bi_ >= 0 && af_ && af_->collidable) { \
            (EX) = (int32_t)modi((int64_t)(EX) + (int64_t)(af_->rect[0] - before_rect[bi_][0]) * 256, 256 * 256); \
            (EY) += (af_->rect[1] - before_rect[bi_][1]) * 256; } } } while (0)
    INHERIT(p->x, p->y, p->grounded);
    for (int i = 0; i < s->n_actors; i++) INHERIT(s->actors[i].x, s->actors[i].y, footing[i]);
#undef INHERIT
    if (player_active(s) && !T_.locked) {
        int sink = integrate_human(s, pi);
        if (sink) { if (sink == SINK_DEATH) player_death(s, c, "LAVA"); return; }
    }
    for (int i = 0; i < s->n_actors; i++) {
        st_actor_t *a = &s->actors[i];
        uint8_t lc = a->lifecycle;
        if (lc == ST_LC_REMOVED || lc == ST_LC_SPAWNING || lc == ST_LC_HATCHING || lc == ST_LC_REMOUNTING) continue;
        if (lc == ST_LC_MOUNTED) {
            intent_t it = intents[i];
            if (it.dir != 0) a->facing = (int8_t)it.dir;
            int16_t g = standing_platform(a->x, a->y, &ST_BIRD_BOX, s->world.platforms, nplat);
            bool grounded = g != ST_NO_PLATFORM;
            int64_t ax = 0;
            if (it.dir != 0) ax = it.dir * (grounded ? C_GROUND_ACCEL : C_AIR_ACCEL);
            else {
                int64_t d = grounded ? C_GROUND_FRICTION : C_AIR_DRAG;
                ax = a->vx > 0 ? -imin(d, a->vx) : a->vx < 0 ? imin(d, -(int64_t)a->vx) : 0;
            }
            if (it.flap) a->vy = (int32_t)imax((int64_t)a->vy - C_FLAP_IMPULSE, C_FLAP_VY_CLAMP);
            body_t e = {a->x, a->y, a->vx, a->vy, g};
            integrate_result_t r = integrate(&e, &ST_BIRD_BOX, ax, s, grounded, 0);
            a->x = e.x; a->y = e.y; a->vx = e.vx; a->vy = e.vy;
            if (r.lava) a->vy = C_LAVA_RESCUE_VY;
        } else if (lc == ST_LC_DISMOUNTED) {
            int16_t g0 = standing_platform(a->x, a->y, &ST_RIDER_BOX, s->world.platforms, nplat);
            if (g0 == ST_NO_PLATFORM) a->vx = fall_steer_vx(s, a, &ST_RIDER_BOX);
            body_t e = {a->x, a->y, a->vx, a->vy, g0};
            int64_t drag = g0 != ST_NO_PLATFORM ? (e.vx > 0 ? -imin(C_AIR_DRAG, e.vx) : e.vx < 0 ? imin(C_AIR_DRAG, -(int64_t)e.vx) : 0) : 0;
            integrate_result_t r = integrate(&e, &ST_RIDER_BOX, drag, s, g0 != ST_NO_PLATFORM, 0);
            a->x = e.x; a->y = e.y; a->vx = e.vx; a->vy = e.vy;
            if (r.lava) push_req(a->id, REQ_REMOVED);
            else if (r.landed != ST_NO_PLATFORM && a->timer == 0) push_req(a->id, REQ_EGG);
        } else if (lc == ST_LC_EGG) {
            int16_t g0 = standing_platform(a->x, a->y, &ST_EGG_BOX, s->world.platforms, nplat);
            body_t e = {a->x, a->y, g0 != ST_NO_PLATFORM ? 0 : fall_steer_vx(s, a, &ST_EGG_BOX), a->vy, g0};
            integrate_result_t r = integrate(&e, &ST_EGG_BOX, 0, s, g0 != ST_NO_PLATFORM, 0);
            a->x = e.x; a->y = e.y; a->vy = e.vy;
            if (r.lava) push_req(a->id, REQ_REMOVED);
        }
    }
}

enum { VERTICAL_VX_SUBPX = 24 };
static bool rising_straight(const st_player_t *p) { return p->vy < 0 && iabs(p->vx) <= VERTICAL_VX_SUBPX; }

static bool contains(const int32_t *xs, int n, int32_t v) {
    for (int i = 0; i < n; i++) if (xs[i] == v) return true;
    return false;
}
static void joust_stage(st_state_t *s, const content_t *c) {
    st_player_t *p = &s->player;
    if (!player_active(s) || T_.locked || T_.death) return;
    box64_t pb = entity_box(p->x, p->y, &ST_BIRD_BOX);
    int32_t pairs[ST_MAX_ACTORS * ST_MAX_ACTORS][2];
    int np = 0;
    for (int i = 0; i < s->n_actors; i++) {
        const st_actor_t *a = &s->actors[i];
        if (a->lifecycle != ST_LC_MOUNTED) continue;
        if (boxes_overlap(pb, actor_box(a))) { pairs[np][0] = 0; pairs[np][1] = a->id; np++; }
    }
    int mounted[ST_MAX_ACTORS], nm = 0;
    for (int i = 0; i < s->n_actors; i++) if (s->actors[i].lifecycle == ST_LC_MOUNTED) mounted[nm++] = i;
    for (int i = 0; i < nm; i++) for (int j = i + 1; j < nm; j++) {
        const st_actor_t *a = &s->actors[mounted[i]], *b = &s->actors[mounted[j]];
        if (boxes_overlap(actor_box(a), actor_box(b))) {
            pairs[np][0] = a->id < b->id ? a->id : b->id;
            pairs[np][1] = a->id < b->id ? b->id : a->id;
            np++;
        }
    }
    // pairs.sort((x,y)=>x[0]-y[0]||x[1]-y[1]) - insertion sort is stable and tiny.
    for (int i = 1; i < np; i++) {
        int32_t k0 = pairs[i][0], k1 = pairs[i][1];
        int j = i - 1;
        while (j >= 0 && (pairs[j][0] > k0 || (pairs[j][0] == k0 && pairs[j][1] > k1))) {
            pairs[j + 1][0] = pairs[j][0]; pairs[j + 1][1] = pairs[j][1]; j--;
        }
        pairs[j + 1][0] = k0; pairs[j + 1][1] = k1;
    }
    int32_t losers[ST_MAX_ACTORS * 2];
    int nl = 0;
    for (int k = 0; k < np; k++) {
        int32_t a_id = pairs[k][0], b_id = pairs[k][1];
        if (contains(losers, nl, a_id) || contains(losers, nl, b_id)) continue;
        st_actor_t *ea_actor = a_id == 0 ? NULL : find_actor(s, a_id);
        st_actor_t *eb = find_actor(s, b_id);
        int32_t *ea_x = ea_actor ? &ea_actor->x : &p->x;
        int32_t *ea_vx = ea_actor ? &ea_actor->vx : &p->vx;
        int32_t *ea_vy = ea_actor ? &ea_actor->vy : &p->vy;
        int64_t dx = wrapped_delta(*ea_x, eb->x);
#define BOUNCE() do { *ea_vx = dx >= 0 ? -C_LANCE_BOUNCE_VX : C_LANCE_BOUNCE_VX; eb->vx = -*ea_vx; \
        *ea_vy = C_LANCE_BOUNCE_VY; eb->vy = C_LANCE_BOUNCE_VY; if (a_id == 0) p->grounded = ST_NO_PLATFORM; } while (0)
        if (a_id != 0) { BOUNCE(); fi(fi(ev(ST_EV_JOUST_CLASH), "a", a_id), "b", b_id); continue; }
        int64_t delta = ((int64_t)p->y + LANCE_Y_SUB) - ((int64_t)eb->y + LANCE_Y_SUB);
        enum { CLASH, RIVAL_LOSES, PLAYER_LOSES } result;
        if (rising_straight(p)) result = RIVAL_LOSES;
        else if (iabs(delta) <= C_LANCE_TIE_BAND) result = CLASH;
        else if (delta > 0) result = delta <= C_LANCE_TIE_BAND + C_PLAYER_GRACE ? CLASH : PLAYER_LOSES;
        else result = RIVAL_LOSES;
        if (result == PLAYER_LOSES && p->invulnerable_ticks > 0) result = CLASH;
        if (result == CLASH) { BOUNCE(); fi(fi(ev(ST_EV_JOUST_CLASH), "a", 0), "b", b_id); }
        else if (result == RIVAL_LOSES) {
            losers[nl++] = b_id;
            fs(fi(ev(ST_EV_JOUST_WIN), "rival", b_id), "cls", CLASS_NAMES[eb->cls]);
            if (!eb->joust_awarded) add_score(s, joust_value(eb), "JOUST", "tier", eb->tier, NULL, 0, "cls", CLASS_NAMES[eb->cls]);
            eb->joust_awarded = true;
            push_req(b_id, REQ_DISMOUNTED);
            BOUNCE();
        } else {
            losers[nl++] = 0;
            player_death(s, c, "JOUST");
            return;
        }
#undef BOUNCE
    }
    if (!T_.death) for (int i = 0; i < s->n_actors; i++) {
        st_actor_t *a = &s->actors[i];
        if (a->lifecycle == ST_LC_EGG && boxes_overlap(entity_box(p->x, p->y, &ST_BIRD_BOX), actor_box(a))) {
            push_req(a->id, REQ_REMOVED);
            fi(fi(ev(ST_EV_EGG), "actor", a->id), "chain", s->run.egg_chain + 1);
            add_score(s, egg_value(s->run.egg_chain), "EGG", "chain", s->run.egg_chain + 1, NULL, 0, NULL, NULL);
            s->run.egg_chain += 1;
        }
    }
}

static void remove_actors_if(st_state_t *s, bool (*drop)(st_state_t *, st_actor_t *)) {
    int w = 0;
    for (int i = 0; i < s->n_actors; i++) {
        if (drop(s, &s->actors[i])) continue;
        if (w != i) s->actors[w] = s->actors[i];
        w++;
    }
    s->n_actors = w;
}
static bool drop_removed(st_state_t *s, st_actor_t *a) { (void)s; return a->lifecycle == ST_LC_REMOVED; }

// arrivalPoint: more than a screen above or below the player, never on screen.
typedef struct { bool ok; int32_t x, y; bool from_above; uint32_t pick; } spot_t;
static spot_t arrival_point(st_state_t *s) {
    spot_t o = {false, 0, 0, false, 0};
    int64_t py = floor_div(s->player.y, 256);
    const int64_t near = TOWER_ARRIVAL_NEAR, far = TOWER_ARRIVAL_FAR, floor_ = ST_TOWER_GROUND - 30;
    bool up = py - far >= ST_TOWER_PLAY_TOP, down = py + far <= floor_;
    if (!up && !down) return o;
    uint32_t rng = s->rng;
    bool from_above = up && (!down || (next_u32(&rng) & 1) == 0);
    int64_t dist = near + (next_u32(&rng) % (uint32_t)(far - near + 1));
    int64_t y = from_above ? py - dist : py + dist;
    int64_t x = -1;
    for (int tries = 0; tries < 6 && x < 0; tries++) {
        int64_t cx = next_u32(&rng) & 255;
        box64_t b = entity_box(px(cx), px(y), &ST_BIRD_BOX);
        bool blocked = false;
        for (int i = 0; i < s->world.n_platforms && !blocked; i++) {
            const st_platform_t *q = &s->world.platforms[i];
            if (!q->collidable) continue;
            int64_t top = (int64_t)(q->rect[1] - 6) * 256, bottom = (int64_t)(q->rect[1] + q->rect[3] + 6) * 256;
            if (b.b <= top || b.t >= bottom) continue;
            for (int k = 0; k < 3; k++) {
                int64_t sh = SHIFTS[k];
                if (b.l + sh < (int64_t)(q->rect[0] + q->rect[2]) * 256 && b.r + sh > (int64_t)q->rect[0] * 256) { blocked = true; break; }
            }
        }
        if (!blocked) x = cx;
    }
    uint32_t pick = next_u32(&rng);
    s->rng = rng;
    if (x < 0) return o;
    o.ok = true; o.x = (int32_t)x; o.y = (int32_t)y; o.from_above = from_above; o.pick = pick;
    return o;
}
static int g_despawn_dropped;
static bool drop_far(st_state_t *s, st_actor_t *a) {
    if (iabs((int64_t)a->y - s->player.y) <= (int64_t)TOWER_DESPAWN * 256) return false;
    if (LIVE(a->lifecycle)) g_despawn_dropped += 1;
    fi(ev(ST_EV_DESPAWN), "actor", a->id);
    return true;
}
static void arrivals(st_state_t *s, const content_t *c) {
    st_tower_t *t = &s->tower;
    const tower_rules_t *rr = &c->rules;
    g_despawn_dropped = 0;
    remove_actors_if(s, drop_far);
    if (g_despawn_dropped) t->cooldown = (int32_t)imax(t->cooldown, rr->fill_gap);
    if (!t->go || t->hold > 0 || T_.locked || !player_active(s)) return;
    if (t->cooldown > 0) { t->cooldown -= 1; return; }
    if (s->n_actors >= imax(2, rr->cap - (t->mercy >= 3 ? 1 : 0))) return;
    spot_t spot = arrival_point(s);
    if (!spot.ok) { t->cooldown = 12; return; }
    int cls = tower_class_for(spot.y, rr, spot.pick);
    int tier = (int)imin(5, rr->tier_base + (tower_band(spot.y) == 2 ? 1 : 0));
    int32_t id = s->sim.next_actor_id;
    s->sim.next_actor_id += 1;
    if (s->n_actors >= ST_MAX_ACTORS) return;   // unreachable: cap <= 8
    st_actor_t *a = &s->actors[s->n_actors++];
    memset(a, 0, sizeof *a);
    a->id = id; a->kind = ST_KIND_RIVAL; a->cls = (uint8_t)cls; a->ghost = (uint8_t)modi(id, 4); a->tier = (int8_t)tier;
    a->lifecycle = ST_LC_MOUNTED; a->x = (int32_t)px(spot.x); a->y = (int32_t)px(spot.y);
    a->vx = 0; a->vy = spot.from_above ? 192 : -320; a->facing = spot.x < 128 ? 1 : -1;
    a->joust_awarded = false;
    t->cooldown = rr->fill_gap;
    fb(fs(fs(fi(ev(ST_EV_SPAWN), "actor", id), "cls", CLASS_NAMES[cls]), "ghost", GHOST_NAMES[a->ghost]), "fromAbove", spot.from_above);
}

static void lifecycle_stage(st_state_t *s, const content_t *c) {
    for (int i = 0; i < s->n_actors; i++) {
        st_actor_t *a = &s->actors[i];
        if (a->timer != 0) continue;
        if (a->lifecycle == ST_LC_SPAWNING) { a->lifecycle = ST_LC_MOUNTED; a->timer = 0; a->phase = 0; fi(ev(ST_EV_MOUNT), "actor", a->id); }
        else if (a->lifecycle == ST_LC_EGG) { a->lifecycle = ST_LC_HATCHING; a->timer = L_HATCHING; fi(ev(ST_EV_HATCH), "actor", a->id); }
        else if (a->lifecycle == ST_LC_HATCHING) { a->lifecycle = ST_LC_REMOUNTING; a->timer = L_REMOUNTING; }
        else if (a->lifecycle == ST_LC_REMOUNTING) {
            a->lifecycle = ST_LC_MOUNTED; a->kind = ST_KIND_RIVAL; a->timer = 0; a->phase = 0; a->vx = 0; a->vy = 0;
            fi(ev(ST_EV_REMOUNT), "actor", a->id);
        }
    }
    for (int k = 0; k < T_.n_req; k++) {
        st_actor_t *a = find_actor(s, T_.req[k].id);
        if (!a || a->lifecycle == ST_LC_REMOVED) continue;
        if (T_.req[k].to == REQ_DISMOUNTED) { a->lifecycle = ST_LC_DISMOUNTED; a->kind = ST_KIND_RIDER; a->timer = L_DISMOUNT_MINIMUM; }
        else if (T_.req[k].to == REQ_EGG) { a->lifecycle = ST_LC_EGG; a->kind = ST_KIND_EGG; a->timer = c->rules.egg_ticks; a->vx = 0; }
        else a->lifecycle = ST_LC_REMOVED;
    }
    T_.n_req = 0;
    remove_actors_if(s, drop_removed);
    arrivals(s, c);
}

static void next_round(st_state_t *s) {
    int32_t kills = s->tower.kills;
    empty_tower(&s->tower, s->tower.round + 1);
    s->tower.kills = kills;
    int32_t sp[2];
    tower_spawn_for(0, sp);
    empty_player(&s->player, sp[0], sp[1]);
    s->player.wing = C_WING_MAX;
    s->player.invulnerable_ticks = ST_RESPAWN_HIDDEN_TICKS + ROUND_SWEEP_TICKS + ST_SHIMMER_TICKS;
    s->n_actors = 0;
    s->run.clean = true; s->run.egg_chain = 0;
    fi(ev(ST_EV_ROUND_START), "round", s->tower.round);
    fs(ev(ST_EV_CHECKPOINT_REQUEST), "reason", "ROUND_START");
}
static void tower_pre(st_state_t *s, const st_input_t *in) {
    st_tower_t *t = &s->tower;
    if (t->hold > 0) {
        T_.locked = true;
        t->hold -= 1;
        if (t->hold == 0) next_round(s);
        return;
    }
    if (!t->go && player_active(s) && (in->flap_edge || in->left || in->right || in->dart_edge)) {
        t->go = true;
        t->cooldown = TOWER_FIRST_ARRIVAL;
        fi(ev(ST_EV_TOWER_GO), "round", t->round);
    }
}

enum { RING_SLACK_PX = 2 };
static void rings(st_state_t *s, const content_t *c) {
    st_tower_t *t = &s->tower;
    const st_player_t *p = &s->player;
    if (!player_active(s) || T_.locked || T_.death || t->hold > 0) return;
    box64_t pb = entity_box(p->x, p->y, &ST_BIRD_BOX);
    static const char *const RING_IDS[6] = {"TWR_R1", "TWR_R2", "TWR_R3", "TWR_R4", "TWR_R5", "TWR_R6"};
    for (int i = 0; i < ST_RINGS_PER_SET; i++) {
        int order = i + 1, bit = 1 << (order - 1);
        if ((t->ring_mask & bit) || !in_ring(pb, &c->rings[i], RING_SLACK_PX)) continue;
        t->ring_mask |= bit;
        t->mercy = 0;
        int count = bit_count((uint32_t)t->ring_mask & 63);
        add_score(s, S_RING, "RING", "order", order, NULL, 0, NULL, NULL);
        fi(fi(fi(fs(ev(ST_EV_RING), "ringId", RING_IDS[i]), "order", order), "count", count), "total", ST_RINGS_PER_SET);
        if (count == ST_RINGS_PER_SET) fi(ev(ST_EV_GOLD_RING_OPEN), "round", t->round);
    }
    if ((t->ring_mask & 63) != 63 || !in_ring(pb, &ST_GOLD_RING, RING_SLACK_PX)) return;
    int blasted = 0;
    for (int i = 0; i < s->n_actors; i++) {
        const st_actor_t *a = &s->actors[i];
        bool armed = LIVE(a->lifecycle);
        int64_t amount = 0;
        if (armed) { blasted += 1; amount = add_score(s, joust_value(a), "BLAST", NULL, 0, NULL, 0, "cls", CLASS_NAMES[a->cls]); }
        fi(fb(fi(fi(fi(ev(ST_EV_TOWER_BLAST), "actor", a->id), "x", a->x), "y", a->y), "armed", armed), "amount", amount);
    }
    t->kills += blasted;
    s->n_actors = 0;
    t->ring_mask |= 64;
    fi(fi(fb(fi(fs(ev(ST_EV_RING), "ringId", "TWR_GOLD"), "order", 7), "gold", true), "count", 6), "total", 6);
    bool clean = s->run.clean;
    if (clean) add_score(s, S_SURVIVAL, "SURVIVAL", NULL, 0, NULL, 0, NULL, NULL);
    add_score(s, c->rules.clear_bonus, "ROUND_CLEAR", "round", t->round, NULL, 0, NULL, NULL);
    fb(fi(fi(ev(ST_EV_ROUND_CLEAR), "round", t->round), "blasted", blasted), "clean", clean);
    t->hold = ROUND_CLEAR_HOLD;
    fs(ev(ST_EV_CHECKPOINT_REQUEST), "reason", "ROUND_CLEAR");
}
static void tower_post(st_state_t *s, const content_t *c) {
    st_tower_t *t = &s->tower;
    const st_player_t *p = &s->player;
    int wins = count_events(ST_EV_JOUST_WIN);
    if (wins) { t->kills += wins; t->cooldown = (int32_t)imax(t->cooldown, c->rules.replace_delay); }
    if (player_active(s) && !T_.death && p->grounded != ST_NO_PLATFORM) {
        int idx = p->grounded;
        if (ST_TOWER[idx].motion == ST_MOTION_STATIC && idx != t->check) {
            t->check = idx;
            fs(ev(ST_EV_TOWER_CHECK), "island", ST_TOWER[idx].id);
        }
    }
}
static void transitions(st_state_t *s) {
    if (T_.pending_game_over) {
        s->sim.shell = ST_SHELL_GAMEOVER;
        ev(ST_EV_GAMEOVER);
        fs(ev(ST_EV_CHECKPOINT_REQUEST), "reason", "GAMEOVER");
        return;
    }
    if (T_.death) { ev(ST_EV_RESPAWN_SCHEDULED); fs(ev(ST_EV_CHECKPOINT_REQUEST), "reason", "DEATH"); }
}

void st_step(st_state_t *s, const st_input_t *in, st_events_t *out) {
    out->n = 0;
    g_out = out;
    memset(&T_, 0, sizeof T_);
    if (s->sim.shell == ST_SHELL_PLAY) {
        content_t c = tower_content(s);
        tower_pre(s, in);
        stage_timers(s);
        human_intent_t pi = human_intent(&s->player, player_active(s) && !T_.locked, in);
        intent_t intents[ST_MAX_ACTORS];
        for (int i = 0; i < s->n_actors; i++) {          // aiIntents
            st_actor_t *a = &s->actors[i];
            intents[i] = (intent_t){0, false};
            if (a->lifecycle != ST_LC_MOUNTED) continue;
            int64_t corner[2] = {a->x < 128 * 256 ? 24 : 232, floor_div(s->player.y, 256) - 70};
            intents[i] = rival_intent(s, a, corner, player_active(s), (int64_t)s->player.y - 40 * 256);
        }
        integrate_all(s, &c, &pi, intents);
        joust_stage(s, &c);
        lifecycle_stage(s, &c);
        rings(s, &c);
        tower_post(s, &c);
        transitions(s);
    }
    for (int i = 0; i < out->n; i++) out->e[i].serial = ++s->sim.event_serial;   // finish()
    s->sim.tick += 1;
}

bool st_can_accept_buffered_flap(const st_state_t *s) {
    if (s->sim.shell != ST_SHELL_PLAY) return true;
    return s->player.flap_cooldown == 0 && s->player.wing > 0 && s->player.invulnerable_ticks <= ST_SHIMMER_TICKS;
}
