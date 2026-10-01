// STRUTHIO HANDHELD · scene builder. A line-for-line port of the browser's
// arcade/src/render/scene.mjs and what it calls (ring-fx.mjs emitters, props
// sources, bird-animation.mjs, camera.mjs, feel.mjs) plus the session's event
// reactions (arcade/src/app/session.mjs stepGameWith). Doubles throughout, in
// the same operation order as the JavaScript, so the quads come out equal.
#include "struthio_scene.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const double JS_PI = 3.141592653589793;   // Math.PI

// ---- helpers -----------------------------------------------------------------------
static double js_round(double v) { return floor(v + 0.5); }                 // Math.round
static double dmin(double a, double b) { return a < b ? a : b; }
static double dmax(double a, double b) { return a > b ? a : b; }
static double clampd(double v, double lo, double hi) { return dmax(lo, dmin(hi, v)); }
static int32_t floor_div(int32_t v, int32_t d) { int32_t q = v / d, r = v % d; return (r != 0 && ((r < 0) != (d < 0))) ? q - 1 : q; }
static int32_t to_px(int32_t v) { return floor_div(v, 256); }
static int64_t wrap_shift(int64_t dx) {
    int64_t c0 = dx < 0 ? -dx : dx, cm = dx - 65536 < 0 ? -(dx - 65536) : dx - 65536, cp = dx + 65536 < 0 ? -(dx + 65536) : dx + 65536;
    int64_t best = 0, ba = c0;
    if (cm < ba) { best = -65536; ba = cm; }
    if (cp < ba) best = 65536;
    return best;
}
static int64_t wrapped_delta(int64_t from, int64_t to) { int64_t dx = to - from; return dx + wrap_shift(dx); }

enum { WORLD_SCALE = 3, WORLD_PLATE_W = 768 };
static const double Z_WORLD = 0.9, Z_PLATFORM = 0.76, Z_RING = 0.68, Z_EGG = 0.6, Z_ACTOR = 0.5, Z_PLAYER = 0.4,
                    Z_OVERLAY = 0.1, Z_TOP = 0.05;
static const double DECOR_Z = .004;

// ---- the quad list ---------------------------------------------------------------------
static st_quads_t *g_q;
static void add(double x, double y, double w, double h, double sx, double sy, double sw, double sh, double z, int flags) {
    if (g_q->n >= ST_MAX_QUADS) return;
    st_quad_t *q = &g_q->q[g_q->n++];
    q->x = x; q->y = y; q->w = w; q->h = h; q->sx = sx; q->sy = sy; q->sw = sw; q->sh = sh; q->z = z; q->flags = (uint8_t)flags;
}
static const st_swatch_t *swatch_named(const char *name) {
    for (int i = 0; i < ST_SWATCH_COUNT; i++) if (strcmp(ST_SWATCHES[i].name, name) == 0) return &ST_SWATCHES[i];
    for (int i = 0; i < ST_SWATCH_COUNT; i++) if (strcmp(ST_SWATCHES[i].name, "white") == 0) return &ST_SWATCHES[i];
    return &ST_SWATCHES[0];
}
static void swatch(const char *name, double x, double y, double w, double h, double z) {
    const st_swatch_t *s = swatch_named(name);
    add(x, y, w, h, s->x + 1, s->y + 1, 1, 1, z, 0);
}
static int font_index(char ch) {
    for (int i = 0; i < ST_FONT_COUNT; i++) if (ST_FONT_CHARS[i] == ch) return i;
    return -1;
}
static double text(const char *str, double x, double y, double z, int scale, int tone) {
    double cx = x;
    const st_modern_font_t *f = &ST_MODERN_FONT;
    for (const char *p = str; *p; p++) {
        char ch = (*p >= 'a' && *p <= 'z') ? (char)(*p - 32) : *p;
        int i = font_index(ch);
        if (i < 0) { i = font_index('?'); if (i < 0) i = font_index(' '); }
        if (i >= 0 && ch != ' ')
            add(cx, y, 5 * scale, 7 * scale, f->x + (i % f->cols) * f->cell_w + 1,
                f->y + tone * f->rows * f->cell_h + (i / f->cols) * f->cell_h, f->glyph_w, f->glyph_h, z, 0);
        cx += 6 * scale;
    }
    return cx;
}
static void text_centered(const char *str, double y, double z, int scale, double cx, int tone) {
    double w = dmax(0, (double)strlen(str) * 6 * scale - scale);
    text(str, floor(cx - w / 2), y, z, scale, tone);
}
// toLocaleString('en-US') for a non-negative integer: thousands separators.
static void fmt(char *out, size_t cap, int64_t n) {
    char tmp[32];
    snprintf(tmp, sizeof tmp, "%lld", (long long)(n < 0 ? 0 : n));
    int len = (int)strlen(tmp), o = 0;
    for (int i = 0; i < len && o + 2 < (int)cap; i++) {
        out[o++] = tmp[i];
        if ((len - i - 1) % 3 == 0 && i != len - 1) out[o++] = ',';
    }
    out[o] = 0;
}

// ---- camera (camera.mjs) -------------------------------------------------------------
enum { SCALE_Y = 2, SPAN = 336, ANCHOR = 25, CAM_BOTTOM = SPAN, CAM_TOP = -7 * SPAN, DZ0 = 150, DZ1 = 290, KEEP0 = 40,
       KEEP1 = 376, SUMMIT_HOLD = 330 };
static int32_t feet_of(const st_state_t *s) { return (to_px(s->player.y) + ANCHOR) * SCALE_Y; }
void st_camera_reset(st_camera_t *c) { c->have = false; c->top = 0; c->last_tick = 0; }
int32_t st_camera_resolve(st_camera_t *c, const st_state_t *s) {
    int32_t feet = feet_of(s);
    double target = clampd(feet - js_round((DZ0 + DZ1) / 2.0), CAM_TOP, CAM_BOTTOM);
    bool hidden = s->player.invulnerable_ticks > ST_SHIMMER_TICKS;
    bool first = !c->have;
    if (!c->have) { c->top = target; c->have = true; }
    double desired = c->top;
    if (hidden) desired = target;
    else if (feet - desired < DZ0) desired = feet - DZ0;
    else if (feet - desired > DZ1) desired = feet - DZ1;
    if (!hidden && feet - CAM_TOP < SUMMIT_HOLD) desired = CAM_TOP;
    desired = clampd(desired, CAM_TOP, CAM_BOTTOM);
    int32_t elapsed = first ? 0 : s->sim.tick - c->last_tick;
    if (elapsed < 0) elapsed = 0;
    if (elapsed > 5) elapsed = 5;
    c->last_tick = s->sim.tick;
    for (int i = 0; i < elapsed; i++) {
        double delta = desired - c->top;
        if (delta == 0) break;
        double step = dmax(2, dmin(40, ceil(fabs(delta) * .16)));
        c->top += (delta > 0 ? 1 : -1) * dmin(fabs(delta), step);
    }
    if (!hidden) c->top = clampd(c->top, feet - KEEP1, feet - KEEP0);
    c->top = clampd(c->top, CAM_TOP, CAM_BOTTOM);
    return (int32_t)js_round(c->top);
}
static double project_y(int32_t camera_top, double local_y) { return local_y * SCALE_Y - camera_top; }
static double project_anchored_y(int32_t camera_top, double local_top, double anchor) {
    return (local_top + anchor) * SCALE_Y - camera_top - anchor;
}

// ---- sprites (sprites.mjs) ---------------------------------------------------------------
enum { CELL = 96, FRAMES = 192 };
static const int RANGE[17][2] = {
    {0, 7}, {8, 31}, {32, 43}, {44, 53}, {54, 63}, {64, 73}, {74, 83}, {84, 93}, {94, 113},
    {114, 123}, {124, 133}, {134, 149}, {150, 161}, {162, 171}, {172, 177}, {178, 185}, {186, 191},
};
enum { R_NEUTRAL, R_FLAP, R_IMPULSE, R_GLIDE, R_CLIMB, R_DESCENT, R_BANK_LEFT, R_BANK_RIGHT, R_RUN, R_TAKEOFF, R_LANDING,
       R_AIR_TRANSITION, R_GROUND_AIR, R_DART, R_HIT, R_DEATH, R_VERTICAL_ASCENT };
static void sprite(int row, int frame, double x, double y, int facing, double z, int flags) {
    int n = ((frame % FRAMES) + FRAMES) % FRAMES;
    double sx = (n % 16) * CELL, sy = (n / 16) * CELL;
    int material = flags ? flags : 2 + row;
    if (facing < 0) add(x, y, 32, 32, sx + CELL, sy, -CELL, CELL, z, material);
    else add(x, y, 32, 32, sx, sy, CELL, CELL, z, material);
}
static void draw_mount(int row, int frame, double x, double y, int facing, double z, int material) {
    static const int SHIFT[3] = {0, -256, 256};
    for (int k = 0; k < 3; k++) {
        double xx = x + SHIFT[k] - 1, yy = y - 4;
        if (xx > -32 && xx < 256) sprite(row, frame, xx, yy, facing, z, material);
    }
}

// ---- bird animation (bird-animation.mjs) -----------------------------------------------------
static int pose(int range, double phase) {
    int lo = RANGE[range][0], len = RANGE[range][1] - RANGE[range][0] + 1;
    double k = floor(clampd(phase, 0, .999999) * len);
    return lo + (int)clampd(k, 0, len - 1);
}
static double wrapped_pixels(double dx) { return dx > 128 ? dx - 256 : dx < -128 ? dx + 256 : dx; }
typedef struct {
    int32_t tick, x, vx, vy, facing;
    bool grounded, has_footing;
    int32_t footing_ticks, flap_age;
    double landing_gap;
    bool hurt, tumble, threat, joust;
} motion_in_t;
static struct bird_motion *motion_find(st_scene_t *sc, int32_t key) {
    for (int i = 0; i < 160; i++) if (sc->motion[i].used && sc->motion[i].key == key) return &sc->motion[i];
    return NULL;
}
static void motion_forget(st_scene_t *sc, int32_t key) { struct bird_motion *m = motion_find(sc, key); if (m) m->used = false; }
static int motion_count(st_scene_t *sc) { int n = 0; for (int i = 0; i < 160; i++) n += sc->motion[i].used; return n; }
static int bird_sample(st_scene_t *sc, int32_t key, bool numeric_key, const motion_in_t *in) {
    struct bird_motion *m = motion_find(sc, key);
    int32_t tick = in->tick;
    if (m && m->tick == tick) return m->frame;
    if (!m || tick < m->tick || tick - m->tick > 120) {
        if (!m) {
            for (int i = 0; i < 160; i++) if (!sc->motion[i].used) { m = &sc->motion[i]; break; }
            if (!m) m = &sc->motion[0];
        }
        memset(m, 0, sizeof *m);
        m->used = true; m->key = key; m->tick = tick; m->x = in->x; m->vx = in->vx; m->vy = in->vy; m->facing = in->facing;
        m->grounded = in->grounded; m->run_phase = 0;
        m->launch_at = m->drop_at = m->land_at = m->turn_at = m->flap_at = m->hurt_at = m->bank_at = -INFINITY;
        m->hurt = false; m->frame = RANGE[R_NEUTRAL][0];
        if (in->grounded && in->has_footing && in->footing_ticks > 0 && in->footing_ticks <= 10) m->land_at = tick - in->footing_ticks + 1;
    }
    int32_t dt = tick - m->tick > 0 ? tick - m->tick : 0;
    double new_flap_at = in->flap_age >= 0 ? (double)(tick - in->flap_age) : -INFINITY;
    bool new_flap = new_flap_at > m->flap_at;
    if (new_flap) m->flap_at = new_flap_at;
    if (dt > 0) {
        if (m->grounded && !in->grounded) { if (in->vy < 0 || new_flap) m->launch_at = tick; else m->drop_at = tick; }
        if (!m->grounded && in->grounded) m->land_at = tick;
        if (in->facing != m->facing) m->turn_at = tick;
        if (in->grounded && m->grounded) m->run_phase += fabs(wrapped_pixels((double)(in->x - m->x) / 256)) / 4;
        if (!in->grounded && !new_flap) {
            if (fabs((double)(in->vx - m->vx)) / dt >= 10 || in->facing != m->facing) m->bank_at = tick;
        }
    }
    if (in->hurt && !m->hurt) m->hurt_at = tick;
#define AGE(f) ((double)tick - m->f)
    double beat_age = AGE(flap_at);
    int frame;
    double vx = in->vx, vy = in->vy;
    if (in->tumble) frame = pose(R_DEATH, (tick % 24) / 24.0);
    else if (AGE(hurt_at) < 12) frame = pose(R_HIT, AGE(hurt_at) / 12);
    else if (in->grounded) {
        if (AGE(land_at) < 10) frame = pose(R_LANDING, AGE(land_at) / 10);
        else if (AGE(turn_at) < 6) frame = pose(R_GROUND_AIR, AGE(turn_at) / 6);
        else if (fabs(vx) > 20) frame = pose(R_RUN, fmod(m->run_phase / 20, 1));
        else if (in->threat) frame = pose(R_NEUTRAL, .25 + (tick % 12) / 48.0);
        else frame = pose(R_NEUTRAL, ((tick + (numeric_key ? key * 17 : 0)) % 96) / 96.0);
    } else if (vy < -360 && fabs(vx) < 140) frame = pose(R_VERTICAL_ASCENT, (tick % 18) / 18.0);
    else if (AGE(launch_at) < 10 && m->flap_at <= m->launch_at) frame = pose(R_TAKEOFF, AGE(launch_at) / 10);
    else if (AGE(drop_at) < 8 && m->flap_at < m->drop_at) frame = pose(R_GROUND_AIR, AGE(drop_at) / 8);
    else if (beat_age < 4) frame = pose(R_IMPULSE, beat_age / 4);
    else if (beat_age < 12) frame = pose(R_FLAP, (beat_age - 4) / 8);
    else if (beat_age < 18) frame = pose(R_AIR_TRANSITION, (beat_age - 12) / 6);
    else if (in->landing_gap < 30 && vy > 0) frame = pose(R_LANDING, 1 - in->landing_gap / 30);
    else if (vy >= 650) frame = pose(R_DART, fmod((double)tick - dmax(m->flap_at, 0), 10) / 10);
    else if (in->joust) frame = pose(R_DART, fabs(vx) > 180 ? .8 : .25);
    else if (AGE(bank_at) < 10 && fabs(vx) > 60) frame = pose(vx < 0 ? R_BANK_LEFT : R_BANK_RIGHT, AGE(bank_at) / 10);
    else if (vy < -90) frame = pose(R_CLIMB, clampd((-vy - 90) / 600, 0, 1));
    else if (vy > 150) frame = pose(R_DESCENT, clampd((vy - 150) / 550, 0, 1));
    else frame = pose(R_GLIDE, (tick % 40) / 40.0);
#undef AGE
    m->tick = tick; m->x = in->x; m->vx = in->vx; m->vy = in->vy; m->facing = in->facing; m->grounded = in->grounded;
    m->hurt = in->hurt; m->frame = frame;
    if (motion_count(sc) > 128)
        for (int i = 0; i < 160; i++) if (sc->motion[i].used && tick - sc->motion[i].tick > 300) sc->motion[i].used = false;
    return frame;
}

// ---- landing gap / joust alignment (scene.mjs) ---------------------------------------------
static bool overlaps_xd(double l, double r, double pl, double pr) {
    static const double S[3] = {0, -65536, 65536};
    for (int i = 0; i < 3; i++) if (l + S[i] < pr && r + S[i] > pl) return true;
    return false;
}
static double bird_landing_gap(int32_t ex, int32_t ey, int32_t evx, int32_t evy, const st_state_t *s) {
    if (evy <= 0) return INFINITY;
    double feet = ey / 256.0 + ST_BIRD_BOX.b, nearest = INFINITY;
    for (int i = 0; i < s->world.n_platforms; i++) {
        const st_platform_t *p = &s->world.platforms[i];
        if (!p->collidable) continue;
        double gap = p->rect[1] - feet;
        if (gap < 0 || gap >= 30) continue;
        double lead = dmin(12, gap / dmax(.25, evy / 256.0));
        double x = ex + evx * lead;
        if (overlaps_xd(x + ST_BIRD_BOX.l * 256, x + ST_BIRD_BOX.r * 256, p->rect[0] * 256.0, (p->rect[0] + p->rect[2]) * 256.0))
            nearest = dmin(nearest, gap);
    }
    return nearest;
}
static bool joust_aligned(int32_t ex, int32_t ey, int32_t efacing, int32_t tx, int32_t ty) {
    int64_t dx = wrapped_delta(ex, tx), dy = (int64_t)ty - ey;
    return (dx < 0 ? -dx : dx) < 40 * 256 && dx * efacing > 0 && dy >= 0 && dy < 30 * 256;
}
static int16_t standing(const st_state_t *s, int32_t x, int32_t y) {
    int64_t b = (int64_t)y + ST_BIRD_BOX.b * 256, l = (int64_t)x + ST_BIRD_BOX.l * 256, r = (int64_t)x + ST_BIRD_BOX.r * 256;
    int best = -1;
    for (int i = 0; i < s->world.n_platforms; i++) {
        const st_platform_t *p = &s->world.platforms[i];
        if (!p->collidable) continue;
        if (b == (int64_t)p->rect[1] * 256 && overlaps_xd((double)l, (double)r, p->rect[0] * 256.0, (p->rect[0] + p->rect[2]) * 256.0) &&
            (best < 0 || p->id < best)) best = p->id;
    }
    return (int16_t)best;
}

// ---- ring effects (ring-fx.mjs emitters) ------------------------------------------------------
enum { RING_OX = 0, RING_OY = 904, BAND_PX = 72, HALO_PX = 96, SHOCK_PX = 96, SPARK_PX = 15 };
enum { BAND_Y = RING_OY, HALO_Y = RING_OY + BAND_PX * 2, SHOCK_Y = HALO_Y + HALO_PX, SPARK_Y = SHOCK_Y + SHOCK_PX };
static int clamp_int(double n, int lo, int hi) { int v = (int)n; return v < lo ? lo : v > hi ? hi : v; }
static void band_src(int kind, double frame, double *x, double *y) {
    int f = (int)frame; *x = RING_OX + ((f % 10) + 10) % 10 * BAND_PX; *y = BAND_Y + kind * BAND_PX;
}
static void halo_src(int kind, double f, double *x, double *y) { *x = RING_OX + (kind * 4 + clamp_int(f, 0, 3)) * HALO_PX; *y = HALO_Y; }
static void shock_src(int kind, double f, double *x, double *y) { *x = RING_OX + (kind * 4 + clamp_int(f, 0, 3)) * SHOCK_PX; *y = SHOCK_Y; }
static void spark_src(int kind, double f, double *x, double *y) { *x = RING_OX + (kind * 3 + clamp_int(f, 0, 2)) * 16; *y = SPARK_Y; }
static void quad(double cx, double cy, double size, double sx, double sy, double src_px, double z) {
    add(cx - size / 2, cy - size / 2, size, size, sx, sy, src_px, src_px, z, 0);
}
static double ease_out_back(double t) { const double k = 1.9; double u = t - 1; return 1 + (k + 1) * u * u * u + k * u * u; }
static void emit_live_ring(int kind, double cx, double cy, int32_t tick, double age, double z) {
    double intro = age < 22 ? age / 22 : 1;
    double scale = intro >= 1 ? 1 : dmax(.08, ease_out_back(dmin(1, intro * 1.35)));
    static const int BREATH[8] = {0, 1, 2, 3, 3, 2, 1, 0};
    int breath = BREATH[(tick >> 3) & 7];
    double sx, sy;
    halo_src(kind, intro < 1 ? 3 : breath, &sx, &sy);
    quad(cx, cy, 32 * dmax(scale, .4), sx, sy, HALO_PX, z + .006);
    band_src(kind, floor(tick / 3.0), &sx, &sy);
    quad(cx, cy, 24 * scale, sx, sy, BAND_PX, z);
    if (intro < 1) {
        double k = intro;
        shock_src(kind, dmin(3, floor(k * 4)), &sx, &sy);
        quad(cx, cy, 80 - 52 * k, sx, sy, SHOCK_PX, z - .004);
        for (int i = 0; i < 4; i++) {
            double a = i * JS_PI / 2 + JS_PI / 4 + tick * .02;
            double r = 30 * (1 - k) + 11;
            spark_src(kind, 2 - dmin(2, floor(k * 3)), &sx, &sy);
            quad(cx + cos(a) * r, cy + sin(a) * r, 5, sx, sy, SPARK_PX, z - .005);
        }
        return;
    }
    static const int SIZE[4] = {0, 1, 2, 1};
    for (int i = 0; i < 3; i++) {
        double a = tick * .045 + i * (JS_PI * 2 / 3);
        bool front = sin(a) > 0;
        int size = SIZE[((tick >> 2) + i * 2) & 3];
        spark_src(kind, size, &sx, &sy);
        quad(cx + cos(a) * 14.5, cy + sin(a) * 14.5, 4 + size * 1.5, sx, sy, SPARK_PX, front ? z - .005 : z + .003);
    }
}
static void emit_ring_burst(int kind, double cx, double cy, int32_t age, double z) {
    if (age >= 22) return;
    double t = age / 22.0, ease = 1 - (1 - t) * (1 - t), sx, sy;
    if (age < 7) { band_src(kind, age, &sx, &sy); quad(cx, cy, 24 + age * 3.2, sx, sy, BAND_PX, z - .002); }
    shock_src(kind, dmin(3, floor(t * 4)), &sx, &sy);
    quad(cx, cy, 30 + ease * 62, sx, sy, SHOCK_PX, z - .003);
    if (age > 3) {
        double t2 = (age - 3) / (double)(22 - 3);
        shock_src(kind, dmin(3, 1 + floor(t2 * 3)), &sx, &sy);
        quad(cx, cy, 26 + (1 - (1 - t2) * (1 - t2)) * 40, sx, sy, SHOCK_PX, z - .0035);
    }
    int size = age < 7 ? 2 : age < 14 ? 1 : 0;
    for (int i = 0; i < 8; i++) {
        double a = i * JS_PI / 4 + ((i & 1) ? .2 : 0);
        double r = 10 + ease * ((i & 1) ? 30 : 38);
        spark_src(kind, size, &sx, &sy);
        quad(cx + cos(a) * r, cy + sin(a) * r, 4 + size * 2, sx, sy, SPARK_PX, z - .004);
    }
}
static double ring_age(st_scene_t *sc, int32_t key, int32_t tick) {
    int found = -1;
    for (int i = 0; i < sc->n_ring_intro; i++) if (sc->ring_intro[i].key == key) { found = i; break; }
    if (found < 0) {
        if (sc->n_ring_intro > 32) sc->n_ring_intro = 0;
        found = sc->n_ring_intro++;
        sc->ring_intro[found].key = key;
        sc->ring_intro[found].tick = tick;
    }
    int32_t age = tick - sc->ring_intro[found].tick;
    return age < 0 ? INFINITY : age;
}

// ---- props (props.mjs) ------------------------------------------------------------------------
enum { PX0 = 1024, PY0 = 392, EGG_CELL = 36, SHIMMER_CELL = 96, SHIMMER_Y = PY0 + 224 };
enum { EGG_INTACT, EGG_CRACK1, EGG_CRACK2, EGG_OPEN, EGG_TILT_L, EGG_TILT_R };
static double egg_sx(int f) { return PX0 + f * EGG_CELL; }

// ---- islands (scene.mjs drawPlatform / islands.mjs islandGeometry) ----------------------------
enum { CAP_ROWS = 22 };
static void draw_island_master(const st_island_plan_t *plan, double x, double y, double width, double depth, bool mirror,
                               bool use_slot) {
    const st_island_master_t *m = &ST_ISLAND_MASTERS[plan->master];
    const int ox = ST_ISLANDS_ORIGIN[0], oy = ST_ISLANDS_ORIGIN[1];
    if (use_slot) {
        int rows = m->h - m->cap_top;
        double H = dmax(2, js_round(plan->depth * 3)), g_depth = H / 3;
        double capH = dmax(1, js_round(dmin(7, g_depth * .5) * 3));
        (void)capH; (void)rows;
        double decorH = m->top_decor ? dmax(1, js_round(m->top_decor * width / m->w * 3)) : 0, decor_depth = decorH / 3;
        const int16_t *s = plan->slot;
        if (s[5]) add(x, y - decor_depth, width, decor_depth, s[0], s[4], s[2], s[5], Z_PLATFORM + DECOR_Z, ST_MAT_ISLAND);
        add(x, y, width, g_depth, s[0], s[1], s[2], s[3], Z_PLATFORM, ST_MAT_ISLAND);
        swatch("kingdomGoldLight", x, y, width, 1.0 / 3, Z_PLATFORM - .012);
        return;
    }
    int rows = m->h - m->cap_top;
    double sx = width / m->w;
    double cap_depth = dmin(7, depth * .5);
    double src_x = ox + m->x + (mirror ? m->w : 0), src_w = mirror ? -m->w : m->w;
    if (m->top_decor) {
        double decor_depth = m->top_decor * sx;
        add(x, y - decor_depth, width, decor_depth, src_x, oy + m->y + m->cap_top - m->top_decor, src_w, m->top_decor, Z_PLATFORM + DECOR_Z, ST_MAT_ISLAND);
    }
    add(x, y, width, cap_depth, src_x, oy + m->y + m->cap_top, src_w, CAP_ROWS, Z_PLATFORM, ST_MAT_ISLAND);
    add(x, y + cap_depth, width, depth - cap_depth, src_x, oy + m->y + m->cap_top + CAP_ROWS, src_w, rows - CAP_ROWS, Z_PLATFORM, ST_MAT_ISLAND);
    swatch("kingdomGoldLight", x, y, width, 1.0 / 3, Z_PLATFORM - .012);
}
static void draw_platform(const st_platform_t *p, int32_t camera_top) {
    double x = p->rect[0], width = p->rect[2];
    double screen_y = project_y(camera_top, p->rect[1]);
    if (screen_y > 400 || screen_y < -130) return;
    const st_island_plan_t *plan = &ST_ISLAND_PLANS[p->id];
    if (plan->ground) {
        const st_island_master_t *m = &ST_ISLAND_MASTERS[plan->master];
        if (m->top_decor) {
            for (int shift = -256; shift <= 256; shift += 256) {
                double dx = x + shift;
                if (dx + width <= 0 || dx >= 256) continue;
                draw_island_master(plan, dx, screen_y, width, 38, false, false);
            }
            return;
        }
        for (int shift = -256; shift <= 256; shift += 256)
            for (int bay = 0; bay * 64 < width; bay++) {
                double dx = x + shift + bay * 64, w = dmin(64, width - bay * 64);
                if (dx + w <= 0 || dx >= 256) continue;
                draw_island_master(plan, dx, screen_y, w, 38, (bay & 1) != 0, false);
            }
        return;
    }
    for (int shift = -256; shift <= 256; shift += 256) {
        double dx = x + shift;
        if (dx + width <= 0 || dx >= 256) continue;
        draw_island_master(plan, dx, screen_y, width, plan->depth, plan->mirror, plan->has_slot);
    }
}

// ---- feel (feel.mjs) --------------------------------------------------------------------------
static void trigger_feel(st_feel_t *f, int kind, int32_t tick, int32_t duration, int32_t shake, double strength,
                         int32_t priority, int32_t x, int32_t y, int space) {
    if (f->start == tick && f->priority > priority) return;
    f->kind = (uint8_t)kind; f->start = tick; f->until = tick + duration; f->shake_until = tick + shake;
    f->strength = strength; f->priority = priority; f->x = x; f->y = y; f->space = (uint8_t)space;
}
st_feel_sample_t st_feel_sample(const st_feel_t *f, int32_t tick) {
    st_feel_sample_t o;
    memset(&o, 0, sizeof o);
    if (tick >= f->until) return o;
    int32_t span = f->until - f->start > 1 ? f->until - f->start : 1;
    int32_t age = tick - f->start > 0 ? tick - f->start : 0;
    double life = dmax(0, 1 - (double)age / span);
    if (tick < f->shake_until) {
        static const int PAT[6][2] = {{1, 0}, {-1, 1}, {0, -1}, {1, 1}, {-1, 0}, {0, 1}};
        int amp = f->strength >= 1.2 && age < 3 ? 2 : 1;
        o.jolt_x = PAT[age % 6][0] * amp;
        o.jolt_y = PAT[age % 6][1] * amp;
    }
    o.active = true; o.kind = f->kind; o.age = age; o.life = life; o.impact = life * f->strength;
    o.x = f->x; o.y = f->y; o.space = f->space;
    return o;
}
static void feel_swatch(const char *tone, double x, double y, double w, double h) {
    double z = Z_PLAYER - .015;
    static const int SH[3] = {-256, 0, 256};
    for (int i = 0; i < 3; i++) {
        double sx = x + SH[i];
        if (sx + w > 0 && sx < 256 && y + h > 0 && y < 384) swatch(tone, sx, y, w, h, z);
    }
}
static void draw_feel_feedback(const st_feel_sample_t *f, int32_t camera_top) {
    if (!f->active) return;
    double player_top = f->space == ST_SPACE_WORLD ? 0 : project_anchored_y(camera_top, f->y, 25);
    double cx = js_round(f->x + f->jolt_x);
    double cy = js_round((f->space == ST_SPACE_WORLD ? project_y(camera_top, f->y)
                                                     : player_top + (f->space == ST_SPACE_PLAYER_FEET ? 25 : 13)) + f->jolt_y);
    int age = f->age;
    if (f->kind == ST_FEEL_LAND) {
        double spread = 4 + age * 2, w = dmax(2, 7 - age);
        feel_swatch(age < 2 ? "cyanLight" : "cyanDeep", cx - spread, cy, w, 1);
        feel_swatch(age < 2 ? "cyan" : "cyanWhisper", cx + spread - w, cy, w, 1);
        if (age < 4) { feel_swatch("goldLight", cx - 2, cy - 1, 1, 1); feel_swatch("goldLight", cx + 2, cy - 1, 1, 1); }
        return;
    }
    if (f->kind == ST_FEEL_FLAP) {
        double spread = 3 + age;
        feel_swatch("cyanLight", cx - spread, cy + 6 + age, 2, 1);
        feel_swatch("cyan", cx + spread - 1, cy + 5 + age, 2, 1);
        return;
    }
    if (f->kind == ST_FEEL_RING || f->kind == ST_FEEL_RING_GREEN) {
        emit_ring_burst(f->kind == ST_FEEL_RING_GREEN ? 1 : 0, cx, cy, age, Z_RING - .02);
        return;
    }
    bool winning = f->kind == ST_FEEL_JOUST_WIN, death = f->kind == ST_FEEL_DEATH;
    const char *primary = death ? "lavaHot" : winning ? "goldLight" : "chromeLight";
    const char *secondary = death ? "ember" : winning ? "cyanLight" : "cyan";
    double reach = 4 + age * (death ? 2 : 1), len = dmax(1, 5 - (age >> 1));
    feel_swatch(primary, cx - reach, cy, len, 1);
    feel_swatch(primary, cx + reach - len, cy, len, 1);
    feel_swatch(secondary, cx, cy - reach, 1, len);
    feel_swatch(secondary, cx, cy + reach - len, 1, len);
    if (age < 6) {
        feel_swatch(secondary, cx - reach + 2, cy - reach + 2, 2, 1);
        feel_swatch(secondary, cx + reach - 3, cy + reach - 2, 2, 1);
    }
}

// ---- session event reactions (session.mjs stepGameWith) -----------------------------------------
st_pre_tick_t st_scene_pre_tick(const st_state_t *s) {
    st_pre_tick_t p = {s->player.x, s->player.y, s->player.grounded != ST_NO_PLATFORM, s->tower.round, st_ring_set_for_round(s->tower.round)};
    return p;
}
static void push_popup(st_scene_t *sc, const char *text_, int tone, int32_t x, int32_t y, bool big) {
    if (sc->n_popups == 12) { memmove(&sc->popups[0], &sc->popups[1], sizeof sc->popups[0] * 11); sc->n_popups = 11; }
    st_popup_t *p = &sc->popups[sc->n_popups++];
    snprintf(p->text, sizeof p->text, "%s", text_);
    p->tone = (uint8_t)tone; p->x = x; p->y = y; p->tick = sc->render_tick; p->big = big;
    // the browser pushes then shifts when longer than 12; same result
}
static int32_t fi_(const st_event_t *e, const char *k) { const st_field_t *f = st_event_field(e, k); return f ? f->i : 0; }
static const char *fs_(const st_event_t *e, const char *k) { const st_field_t *f = st_event_field(e, k); return f && f->kind == ST_F_STR ? f->s : ""; }
void st_scene_on_events(st_scene_t *sc, const st_state_t *s, const st_events_t *ev, const st_pre_tick_t *pre) {
    int32_t rt = sc->render_tick;
    int32_t player_x = to_px(s->player.x) + 14, player_top = to_px(s->player.y);
    const st_ring_t *rings_before = ST_RING_SET[pre->ring_set_before];
    bool death = false;
    for (int i = 0; i < ev->n; i++) {
        const st_event_t *e = &ev->e[i];
        char t[48];
        switch (e->type) {
        case ST_EV_EXTRA_LIFE: snprintf(sc->banner, sizeof sc->banner, "EXTRA JOUST MARK"); sc->banner_until = rt + 100; break;
        case ST_EV_GOLD_RING_OPEN: snprintf(sc->banner, sizeof sc->banner, "6/6 \xC2\xB7 THE GOLD RING IS AT THE MOON"); sc->banner_until = rt + 150; break;
        case ST_EV_ROUND_CLEAR:
            snprintf(sc->banner, sizeof sc->banner, "ROUND %d CLEAR%s", (int)fi_(e, "round"), fi_(e, "clean") ? " \xC2\xB7 NO LOSSES" : "");
            sc->banner_until = rt + 150;
            break;
        case ST_EV_TOWER_BLAST:
            if (fi_(e, "amount")) { snprintf(t, sizeof t, "%d", (int)fi_(e, "amount")); push_popup(sc, t, ST_TONE_GOLD, to_px(fi_(e, "x")) + 14, to_px(fi_(e, "y")) + 4, false); }
            break;
        case ST_EV_SCORE_AWARD: {
            const char *kind = fs_(e, "kind");
            int tone = strcmp(kind, "EGG") == 0 ? ST_TONE_GOLD : strcmp(kind, "JOUST") == 0 ? ST_TONE_WHITE : strcmp(kind, "RING") == 0 ? ST_TONE_CYAN : -1;
            if (tone < 0) break;
            snprintf(t, sizeof t, "%d", (int)fi_(e, "amount"));
            if (strcmp(kind, "RING") == 0) {
                const st_ring_t *r = &rings_before[fi_(e, "order") - 1];
                push_popup(sc, t, tone, r->x, r->y - 14, false);
            } else push_popup(sc, t, tone, player_x, player_top + 4, strcmp(kind, "EGG") == 0 && fi_(e, "chain") >= 4);
            break;
        }
        case ST_EV_FLAP: trigger_feel(&sc->feel, ST_FEEL_FLAP, rt, 5, 0, .32, 1, player_x, player_top, ST_SPACE_PLAYER_CENTER); break;
        case ST_EV_RING: {
            bool gold = st_event_field(e, "gold") != NULL;
            const st_ring_t *r = gold ? &ST_GOLD_RING : NULL;
            if (!gold) {
                const char *id = fs_(e, "ringId");
                for (int k = 0; k < ST_RINGS_PER_SET; k++) { char rid[8]; snprintf(rid, sizeof rid, "TWR_R%d", k + 1); if (!strcmp(rid, id)) r = &rings_before[k]; }
            }
            trigger_feel(&sc->feel, gold ? ST_FEEL_RING_GREEN : ST_FEEL_RING, rt, 22, 0, .92, 3, r ? r->x : player_x, r ? r->y : player_top,
                         r ? ST_SPACE_WORLD : ST_SPACE_PLAYER_CENTER);
            break;
        }
        case ST_EV_JOUST_CLASH:
            if (fi_(e, "a") == 0 || fi_(e, "b") == 0) trigger_feel(&sc->feel, ST_FEEL_CLASH, rt, 8, 5, .9, 4, player_x, player_top, ST_SPACE_PLAYER_CENTER);
            break;
        case ST_EV_JOUST_WIN: trigger_feel(&sc->feel, ST_FEEL_JOUST_WIN, rt, 14, 8, 1.35, 5, player_x, player_top, ST_SPACE_PLAYER_CENTER); break;
        case ST_EV_PLAYER_DEATH:
            death = true;
            trigger_feel(&sc->feel, ST_FEEL_DEATH, rt, 18, 11, 1.45, 6, to_px(pre->player_x) + 14, to_px(pre->player_y), ST_SPACE_PLAYER_CENTER);
            break;
        default: break;
        }
    }
    if (!pre->was_grounded && s->player.grounded != ST_NO_PLATFORM && !death)
        trigger_feel(&sc->feel, ST_FEEL_LAND, rt, 7, 3, .58, 2, player_x, player_top, ST_SPACE_PLAYER_FEET);
}

// ---- overlays (scene.mjs buildOverlays) ------------------------------------------------------------
static void draw_chevron(double cx, double cy, int dir, const char *colour, double z) {
    for (int i = 0; i < 7; i++) {
        double x = dir < 0 ? cx + abs(i - 3) : cx - abs(i - 3);
        swatch(colour, x, cy - 3 + i, 2, 1, z);
    }
}
static void build_overlays(const st_scene_t *sc, const st_state_t *s, const st_menu_t *menu) {
    char t[64], n[32];
    int32_t rt = sc->render_tick;
    if (s->sim.shell == ST_SHELL_PLAY) {
        if (s->tower.hold > 0) {
            swatch("shade", 20, 156, 216, 44, Z_OVERLAY + .02);
            snprintf(t, sizeof t, "ROUND %d CLEAR", (int)s->tower.round);
            text_centered(t, 164, Z_OVERLAY, 2, 128, ST_TONE_GOLD);
            text_centered("EVERY RIVAL DESTROYED", 188, Z_OVERLAY, 1, 128, ST_TONE_WHITE);
        } else if (!s->tower.go) {
            swatch("shade", 24, 150, 208, 66, Z_OVERLAY + .02);
            snprintf(t, sizeof t, "ROUND %d", (int)s->tower.round);
            text_centered(t, 160, Z_OVERLAY, 3, 128, ST_TONE_GOLD);
            text_centered("FIND 6 RINGS", 192, Z_OVERLAY, 1, 128, ST_TONE_WHITE);
            text_centered("THEN THE GOLD RING AT THE MOON", 204, Z_OVERLAY, 1, 128, ST_TONE_CYAN);
        } else if (s->player.invulnerable_ticks > ST_SHIMMER_TICKS) text_centered("READY", 182, Z_OVERLAY, 2, 128, ST_TONE_CYAN);
    }
    if (s->sim.shell == ST_SHELL_PAUSE) {
        swatch("shade", 0, 0, 256, 384, Z_TOP + 0.01);
        text_centered("PAUSED", 164, Z_TOP, 2, 128, ST_TONE_CYAN);
        text_centered("BOTH WINGS TO RESUME", 191, Z_TOP, 1, 128, ST_TONE_WHITE);
        fmt(n, sizeof n, s->sim.score);
        snprintf(t, sizeof t, "SCORE %s", n);
        text_centered(t, 210, Z_TOP, 1, 128, ST_TONE_GOLD);
    }
    if (s->sim.shell == ST_SHELL_GAMEOVER) {
        swatch("shade", 0, 0, 256, 384, Z_TOP + 0.01);
        text_centered("GAME OVER", 150, Z_TOP, 2, 128, ST_TONE_LAVA);
        fmt(n, sizeof n, s->sim.score);
        snprintf(t, sizeof t, "FINAL %s", n);
        text_centered(t, 118, Z_TOP, 1, 128, ST_TONE_WHITE);
        const st_gameover_info_t *info = &menu->info;
        if (info->valid && info->is_new) { if ((rt >> 4) & 1) text_centered("NEW HIGH SCORE", 130, Z_TOP, 1, 128, ST_TONE_GOLD); }
        else if (info->valid && info->best_score) { fmt(n, sizeof n, info->best_score); snprintf(t, sizeof t, "HI %s", n); text_centered(t, 130, Z_TOP, 1, 128, ST_TONE_DIM); }
        if (info->valid && info->round) { snprintf(t, sizeof t, "REACHED ROUND %d", (int)info->round); text_centered(t, 240, Z_TOP, 1, 128, ST_TONE_CYAN); }
        for (int i = 0; i < menu->n_items; i++) {
            double y = 180 + i * 16;
            bool on = i == menu->index;
            if (on) {
                swatch("shade", 64, y - 4, 128, 15, Z_TOP + .005);
                swatch("cyanDark", 64, y - 4, 128, 1, Z_TOP + .004);
                swatch("cyanDark", 64, y + 10, 128, 1, Z_TOP + .004);
                int blink = (rt >> 4) & 1;
                draw_chevron(75 + blink, y + 3, 1, "gold", Z_TOP);
                draw_chevron(179 - blink, y + 3, -1, "gold", Z_TOP);
            }
            text_centered(menu->items[i], y, Z_TOP, 1, 128, on ? ST_TONE_WHITE : ST_TONE_DIM);
        }
        text_centered(menu->n_items > 1 ? "WINGS CHOOSE  BOTH SELECTS" : "BOTH WINGS CONTINUE", 222, Z_TOP, 1, 128, ST_TONE_DIM);
    }
}
static void draw_score_popups(const st_scene_t *sc, int32_t camera_top) {
    int32_t now = sc->render_tick;
    for (int i = 0; i < sc->n_popups; i++) {
        const st_popup_t *p = &sc->popups[i];
        int32_t age = now - p->tick;
        if (age < 0 || age > 48) continue;
        if (age > 48 * .7 && (age & 1)) continue;
        double y = js_round(project_y(camera_top, p->y) - age * 0.3);
        if (y < 4 || y > 370) continue;
        text_centered(p->text, y, Z_OVERLAY + .01, p->big ? 2 : 1, dmax(14, dmin(242, p->x)), p->tone);
    }
}

// ---- the frame ------------------------------------------------------------------------------------
void st_scene_init(st_scene_t *sc) {
    memset(sc, 0, sizeof *sc);
    sc->feel.start = -1; sc->feel.until = -1; sc->feel.shake_until = -1; sc->feel.x = 128; sc->feel.y = 192;
    sc->banner_until = -1;
}
double st_scene_impact(const st_scene_t *sc, const st_state_t *s) {
    (void)s;
    st_feel_sample_t f = st_feel_sample(&sc->feel, sc->render_tick);
    return dmax(sc->banner_until > sc->render_tick ? 1 : 0, f.impact);
}
static int actor_stroke(const st_actor_t *a) {
    int flap_cd = (a->phase >> 3) & 15;
    static const int PERIOD[3] = {10, 8, 8};
    return flap_cd > 0 ? PERIOD[a->cls] - flap_cd : -1;
}
void st_scene_build(st_scene_t *sc, const st_state_t *s, int32_t camera_top, const st_menu_t *menu, st_quads_t *out) {
    out->n = 0;
    g_q = out;
    sc->render_tick += 1;
    sc->moon_phase = fmod(sc->moon_phase + 1.0 / (50 * 60), 1);
    if (s->sim.shell == ST_SHELL_ATTRACT) return;
    int32_t rt = sc->render_tick;
    // world plates
    double progress = clampd((double)(CAM_BOTTOM - camera_top) / (CAM_BOTTOM - CAM_TOP), 0, 1);
    double rest = 1 - progress;
    add(0, 0, 256, 384, 0, js_round(rest * 384 * WORLD_SCALE), 256 * WORLD_SCALE, 384 * WORLD_SCALE, Z_WORLD + 0.02, ST_MAT_WORLD);
    add(0, 0, 256, 384, WORLD_PLATE_W, js_round(rest * 512 * WORLD_SCALE), 256 * WORLD_SCALE, 256 * WORLD_SCALE, Z_WORLD, ST_MAT_WORLD);
    // islands
    for (int i = 0; i < s->world.n_platforms; i++) draw_platform(&s->world.platforms[i], camera_top);
    // rings
    {
        int set = st_ring_set_for_round(s->tower.round);
        int32_t mask = s->tower.ring_mask;
        double age = ring_age(sc, s->tower.round * 2, rt);
        for (int i = 0; i < ST_RINGS_PER_SET; i++) {
            const st_ring_t *r = &ST_RING_SET[set][i];
            if (mask & (1 << i)) continue;
            double cy = project_y(camera_top, r->y);
            if (cy < -20 || cy > 404) continue;
            emit_live_ring(0, r->x, cy, rt + (i + 1) * 9, age, Z_RING);
        }
        if ((mask & 63) == 63 && !(mask & 64)) {
            double cy = project_y(camera_top, ST_GOLD_RING.y);
            if (cy > -20 && cy < 404) emit_live_ring(1, ST_GOLD_RING.x, cy, rt, ring_age(sc, s->tower.round * 2 + 1, rt), Z_RING);
        }
    }
    // actors
    for (int i = 0; i < s->n_actors; i++) {
        const st_actor_t *a = &s->actors[i];
        if (a->lifecycle == ST_LC_REMOVED) continue;
        double x = to_px(a->x), y = project_anchored_y(camera_top, to_px(a->y), 25);
        if (a->lifecycle == ST_LC_SPAWNING || a->lifecycle == ST_LC_REMOUNTING) {
            int f = ((rt >> 2) + a->id) & 3;
            if (a->timer > 8 || (rt & 2)) add(x, y - 4, 32, 32, PX0 + (f & 3) * SHIMMER_CELL, SHIMMER_Y, SHIMMER_CELL, SHIMMER_CELL, Z_ACTOR, 0);
            continue;
        }
        if (a->lifecycle == ST_LC_HATCHING) {
            double k = 1 - clampd(a->timer / 60.0, 0, 1);
            add(x + 8.5, y + 13.5, 12, 12, egg_sx(EGG_OPEN), PY0, EGG_CELL, EGG_CELL, Z_EGG, 0);
            if (k > .45 && ((rt >> 1) & 1)) swatch("ringLight", x + 13, y + 15.5 - k * 2, 2, 2, Z_EGG - .005);
            continue;
        }
        if (a->lifecycle == ST_LC_EGG) {
            int32_t t = a->timer;
            int f = t > 240 ? EGG_INTACT : t > 120 ? EGG_CRACK1 : EGG_CRACK2;
            if (t <= 60 && ((rt >> 2) & 3) != 0) f = ((rt >> 3) & 1) ? EGG_TILT_L : EGG_TILT_R;
            add(x + 8.5, y + 13.5, 12, 12, egg_sx(f), PY0, EGG_CELL, EGG_CELL, Z_EGG, 0);
            continue;
        }
        if (a->lifecycle == ST_LC_DISMOUNTED) {
            int f = (((rt >> 2) + a->id) & 1) ? EGG_TILT_L : EGG_TILT_R;
            add(x + 8.5, y + 12.5, 12, 12, egg_sx(f), PY0, EGG_CELL, EGG_CELL, Z_ACTOR, 0);
            continue;
        }
        int row = 1 + a->cls;
        motion_in_t in = {s->sim.tick, a->x, a->vx, a->vy, a->facing, standing(s, a->x, a->y) >= 0, false, 0, actor_stroke(a),
                          bird_landing_gap(a->x, a->y, a->vx, a->vy, s), false, false, false,
                          joust_aligned(a->x, a->y, a->facing, s->player.x, s->player.y)};
        int frame = bird_sample(sc, a->id, true, &in);
        draw_mount(row, frame, x, y, a->facing, Z_ACTOR, 0);
    }
    // player
    st_feel_sample_t feel = st_feel_sample(&sc->feel, rt);
    const st_player_t *p = &s->player;
    if (p->invulnerable_ticks > ST_SHIMMER_TICKS) motion_forget(sc, -1);
    else {
        double x = to_px(p->x), y = project_anchored_y(camera_top, to_px(p->y), 25);
        bool joust = false;
        for (int i = 0; i < s->n_actors; i++)
            if (s->actors[i].lifecycle == ST_LC_MOUNTED && joust_aligned(p->x, p->y, p->facing, s->actors[i].x, s->actors[i].y)) { joust = true; break; }
        motion_in_t in = {s->sim.tick, p->x, p->vx, p->vy, p->facing, p->grounded != ST_NO_PLATFORM, true, p->footing_ticks,
                          p->flap_cooldown > 0 ? 7 - p->flap_cooldown : -1, bird_landing_gap(p->x, p->y, p->vx, p->vy, s),
                          feel.active && feel.kind == ST_FEEL_CLASH, p->lava_phase == ST_LAVA_SINK, false, joust};
        int frame = bird_sample(sc, -1, false, &in);
        if (!(p->invulnerable_ticks > 0 && (s->sim.tick & 2))) draw_mount(0, frame, x, y, p->facing, Z_PLAYER, ST_MAT_PLAYER);
    }
    // jolt
    if (feel.active && (feel.jolt_x || feel.jolt_y))
        for (int i = 0; i < out->n; i++)
            if (out->q[i].z >= Z_PLAYER && out->q[i].z < Z_WORLD) { out->q[i].x += feel.jolt_x; out->q[i].y += feel.jolt_y; }
    draw_feel_feedback(&feel, camera_top);
    draw_score_popups(sc, camera_top);
    build_overlays(sc, s, menu);
}

uint32_t st_quads_hash(const st_quads_t *qs) {
    uint32_t h = 0x811c9dc5u;
#define MIX(v) do { uint32_t v_ = (uint32_t)(v); for (int k_ = 0; k_ < 4; k_++) { h ^= (v_ >> (8 * k_)) & 255; h *= 0x01000193u; } } while (0)
#define Q(v) ((int32_t)(int64_t)floor((v) * 4096 + 0.5))
    MIX(qs->n);
    for (int i = 0; i < qs->n; i++) {
        const st_quad_t *q = &qs->q[i];
        MIX(Q(q->x)); MIX(Q(q->y)); MIX(Q(q->w)); MIX(Q(q->h)); MIX(Q(q->sx)); MIX(Q(q->sy)); MIX(Q(q->sw)); MIX(Q(q->sh)); MIX(Q(q->z)); MIX(q->flags);
    }
#undef MIX
#undef Q
    return h;
}
