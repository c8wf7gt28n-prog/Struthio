// STRUTHIO HANDHELD · greybox renderer. See struthio_greybox.h.
#include "struthio_greybox.h"
#include <stdio.h>
#include <string.h>
#include "struthio_rules.h"

// ---- camera (arcade/src/render/camera.mjs TowerCamera) ------------------------------
enum { SCALE_Y = 2, SPAN = 336, ANCHOR_Y = 25, CAM_BOTTOM = SPAN, CAM_TOP = -7 * SPAN, DZ0 = 150, DZ1 = 290,
       KEEP0 = 40, KEEP1 = 376, SUMMIT_HOLD = 330 };
static double clampd(double v, double lo, double hi) { return v < lo ? lo : v > hi ? hi : v; }
static int32_t floor_div256(int32_t v) { return v >= 0 ? v / 256 : -((-v + 255) / 256); }
static int32_t feet_of(const st_state_t *s) { return (floor_div256(s->player.y) + ANCHOR_Y) * SCALE_Y; }

void st_camera_reset(st_camera_t *c) { c->have = false; c->top = 0; c->last_tick = 0; }
int32_t st_camera_resolve(st_camera_t *c, const st_state_t *s) {
    int32_t feet = feet_of(s);
    double target = clampd(feet - (DZ0 + DZ1) / 2, CAM_TOP, CAM_BOTTOM);
    bool hidden = s->player.invulnerable_ticks > ST_SHIMMER_TICKS;
    if (!c->have) { c->top = target; c->have = true; c->last_tick = s->sim.tick; }
    double desired = c->top;
    if (hidden) desired = target;
    else if (feet - desired < DZ0) desired = feet - DZ0;
    else if (feet - desired > DZ1) desired = feet - DZ1;
    if (!hidden && feet - CAM_TOP < SUMMIT_HOLD) desired = CAM_TOP;
    desired = clampd(desired, CAM_TOP, CAM_BOTTOM);
    int32_t elapsed = s->sim.tick - c->last_tick;
    if (elapsed < 0) elapsed = 0;
    if (elapsed > 5) elapsed = 5;
    c->last_tick = s->sim.tick;
    for (int i = 0; i < elapsed; i++) {
        double delta = desired - c->top;
        if (delta == 0) break;
        double ad = delta < 0 ? -delta : delta;
        double step = (double)(int64_t)(ad * .16);
        if (step < ad * .16) step += 1;               // Math.ceil
        if (step < 2) step = 2;
        if (step > 40) step = 40;
        c->top += (delta > 0 ? 1 : -1) * (ad < step ? ad : step);
    }
    if (!hidden) c->top = clampd(c->top, feet - KEEP1, feet - KEEP0);
    c->top = clampd(c->top, CAM_TOP, CAM_BOTTOM);
    double r = c->top;
    return (int32_t)(r >= 0 ? (int64_t)(r + 0.5) : -(int64_t)(-r + 0.5));
}

// ---- primitives -------------------------------------------------------------------------
static void px_(uint8_t *fb, int x, int y, uint8_t c) {
    if ((unsigned)x < ST_FB_W && (unsigned)y < ST_FB_H) fb[y * ST_FB_W + x] = c;
}
static void rect(uint8_t *fb, int x, int y, int w, int h, uint8_t c) {
    int x0 = x < 0 ? 0 : x, y0 = y < 0 ? 0 : y, x1 = x + w > ST_FB_W ? ST_FB_W : x + w, y1 = y + h > ST_FB_H ? ST_FB_H : y + h;
    for (int yy = y0; yy < y1; yy++) memset(fb + yy * ST_FB_W + x0, c, (size_t)(x1 > x0 ? x1 - x0 : 0));
}
// The playfield wraps horizontally: draw at x, x - 256 and x + 256.
static void rect_wrap(uint8_t *fb, int x, int y, int w, int h, uint8_t c) {
    for (int k = -1; k <= 1; k++) rect(fb, x + k * 256, y, w, h, c);
}
static void px_wrap(uint8_t *fb, int x, int y, uint8_t c) { px_(fb, ((x % 256) + 256) % 256, y, c); }
static void circle(uint8_t *fb, int cx, int cy, int r, uint8_t c, bool fill) {
    for (int dy = -r; dy <= r; dy++) for (int dx = -r; dx <= r; dx++) {
        int d = dx * dx + dy * dy;
        if (fill ? d <= r * r : (d <= r * r && d > (r - 2) * (r - 2))) px_wrap(fb, cx + dx, cy + dy, c);
    }
}
static const str_glyph_t *glyph(char ch) {
    if (ch >= 'a' && ch <= 'z') ch = (char)(ch - 32);
    for (int i = 0; i < STR_FONT_GLYPHS; i++) if (STR_FONT_5X7[i].ch == ch) return &STR_FONT_5X7[i];
    return &STR_FONT_5X7[0];                      // ' '
}
int st_text_width(const char *text, int scale) { int n = (int)strlen(text); return n ? (n * 6 - 1) * scale : 0; }
void st_draw_text(uint8_t *fb, int x, int y, const char *text, uint8_t color, int scale) {
    for (; *text; text++, x += 6 * scale) {
        const str_glyph_t *g = glyph(*text);
        for (int row = 0; row < 7; row++) for (int col = 0; col < 5; col++)
            if (g->rows[row] & (16 >> col)) rect(fb, x + col * scale, y + row * scale, scale, scale, color);
    }
}
static void text_shadow(uint8_t *fb, int x, int y, const char *t, uint8_t c, int scale) {
    st_draw_text(fb, x + scale, y + scale, t, STR_PAL_INK, scale);
    st_draw_text(fb, x, y, t, c, scale);
}
static void text_center(uint8_t *fb, int y, const char *t, uint8_t c, int scale) {
    text_shadow(fb, (ST_FB_W - st_text_width(t, scale)) / 2, y, t, c, scale);
}

// ---- scene ------------------------------------------------------------------------------
static int sy(const st_view_t *v, int32_t world_y_px) { return world_y_px * SCALE_Y - v->camera_top; }
static int sprite_top(const st_view_t *v, int32_t y_sub) {         // projectAnchoredY
    return (floor_div256(y_sub) + ANCHOR_Y) * SCALE_Y - v->camera_top - ANCHOR_Y;
}
static uint32_t hash32(uint32_t x) { x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; x ^= x >> 16; return x; }

static void sky(uint8_t *fb, const st_view_t *v) {
    // Three altitude bands, darker toward the moon, with a dither seam between.
    for (int y = 0; y < ST_FB_H; y++) {
        int wy = y + v->camera_top;                   // presentation y (2x sim)
        uint8_t c = wy > -900 ? STR_PAL_NAVY_SOFT : wy > -1700 ? STR_PAL_NAVY : STR_PAL_VOID;
        uint8_t c2 = wy > -900 ? STR_PAL_NAVY : wy > -1700 ? STR_PAL_VOID : STR_PAL_VOID_DEEP;
        int seam = wy > -900 ? -900 : wy > -1700 ? -1700 : -2400;
        bool dither = wy - seam < 24;
        for (int x = 0; x < ST_FB_W; x++) fb[y * ST_FB_W + x] = (dither && ((x + y) & 1)) ? c2 : c;
    }
    // Stars on a half-speed parallax layer.
    int scroll = v->camera_top / 2;
    for (int y = 0; y < ST_FB_H; y++) {
        uint32_t h = hash32((uint32_t)(y + scroll) * 2654435761u);
        if ((h & 7) != 0) continue;
        int x = (int)((h >> 8) % ST_FB_W);
        bool twinkle = ((h >> 20) & 31) == ((v->frame >> 3) & 31);
        px_(fb, x, y, twinkle ? STR_PAL_WHITE : ((h >> 16) & 1 ? STR_PAL_IVORY_DARK : STR_PAL_CHROME_DARK));
    }
}
static void moon(uint8_t *fb, const st_view_t *v) {
    int cx = ST_GOLD_RING.x, cy = sy(v, ST_GOLD_RING.y);
    if (cy < -40 || cy > ST_FB_H + 40) return;
    circle(fb, cx, cy, 30, STR_PAL_IVORY_DARK, true);
    circle(fb, cx, cy, 28, STR_PAL_IVORY, true);
    circle(fb, cx - 9, cy - 6, 6, STR_PAL_IVORY_DARK, true);
    circle(fb, cx + 10, cy + 9, 4, STR_PAL_IVORY_DARK, true);
}
static void lava(uint8_t *fb, const st_state_t *s, const st_view_t *v) {
    int top = sy(v, floor_div256(s->world.lava_y));
    if (top >= ST_FB_H) return;
    for (int y = top < 0 ? 0 : top; y < ST_FB_H; y++) for (int x = 0; x < ST_FB_W; x++) {
        int wave = ((x + (int)(v->frame >> 1)) >> 3) & 1;
        fb[y * ST_FB_W + x] = (y - top) < 2 + wave ? STR_PAL_LAVA_HOT : STR_PAL_LAVA;
    }
}
static void islands(uint8_t *fb, const st_state_t *s, const st_view_t *v) {
    for (int i = 0; i < s->world.n_platforms; i++) {
        const st_platform_t *p = &s->world.platforms[i];
        int x = p->rect[0], w = p->rect[2], top = sy(v, p->rect[1]);
        if (top > ST_FB_H || top + 40 < 0) continue;
        if (p->id == 0) {                              // the grid floor
            int h = p->rect[3] * SCALE_Y;
            rect(fb, 0, top, ST_FB_W, h, STR_PAL_CHROME_DARK);
            rect(fb, 0, top, ST_FB_W, 2, STR_PAL_CHROME_LIGHT);
            for (int gx = 0; gx < ST_FB_W; gx += 16) rect(fb, gx, top + 2, 1, h - 2, STR_PAL_NAVY);
            continue;
        }
        bool moving = ST_TOWER[p->id].motion != ST_MOTION_STATIC;
        // Rock body tapering to a point, then a bright walkable top.
        for (int row = 0; row < 14; row++) {
            int inset = row * row / 8 + row / 2;
            if (inset * 2 >= w) break;
            rect_wrap(fb, x + inset, top + 3 + row, w - inset * 2, 1, row < 4 ? STR_PAL_EARTH_LIGHT : row < 9 ? STR_PAL_EARTH : STR_PAL_EARTH_DARK);
        }
        rect_wrap(fb, x, top, w, 3, moving ? STR_PAL_CYAN_LIGHT : STR_PAL_GOLD_LIGHT);
        rect_wrap(fb, x, top + 2, w, 1, moving ? STR_PAL_CYAN_DARK : STR_PAL_GOLD);
    }
}
static void rings(uint8_t *fb, const st_state_t *s, const st_view_t *v) {
    const st_ring_t *set = ST_RING_SET[st_ring_set_for_round(s->tower.round)];
    for (int i = 0; i < ST_RINGS_PER_SET; i++) {
        if (s->tower.ring_mask & (1 << i)) continue;
        int cy = sy(v, set[i].y);
        if (cy < -16 || cy > ST_FB_H + 16) continue;
        circle(fb, set[i].x, cy, set[i].radius + 1, STR_PAL_RING_DEEP, false);
        circle(fb, set[i].x, cy, set[i].radius, (v->frame >> 4) & 1 ? STR_PAL_RING_LIGHT : STR_PAL_RING, false);
    }
    if (!(s->tower.ring_mask & 64)) {
        bool open = (s->tower.ring_mask & 63) == 63;
        int cy = sy(v, ST_GOLD_RING.y);
        circle(fb, ST_GOLD_RING.x, cy, ST_GOLD_RING.radius, open ? ((v->frame >> 3) & 1 ? STR_PAL_GOLD_LIGHT : STR_PAL_GOLD) : STR_PAL_GOLD_DEEP, false);
    }
}
// A bird + rider in the 28 px sprite cell, facing left or right, with the lance
// at the rulebook's lance height (box top - 5).
static void bird(uint8_t *fb, int x, int top, int facing, uint8_t body, uint8_t rider, bool flap) {
    int f = facing < 0 ? -1 : 1, cx = x + 14;
    rect_wrap(fb, x + 8, top + 16, 14, 6, body);                         // body
    rect_wrap(fb, cx + f * 6 - 2, top + 12, 4, 5, body);                 // neck
    rect_wrap(fb, cx + f * 9 - 1, top + 11, 4, 3, body);                 // head
    px_wrap(fb, cx + f * 12, top + 12, STR_PAL_EMBER);                   // beak
    int wy = flap ? top + 10 : top + 17;
    rect_wrap(fb, cx - f * 4 - 4, wy, 8, flap ? 6 : 3, rider);           // wing
    rect_wrap(fb, cx - 2, top + 22, 1, 3, STR_PAL_OCHRE);                // legs
    rect_wrap(fb, cx + 2, top + 22, 1, 3, STR_PAL_OCHRE);
    rect_wrap(fb, cx - 3, top + 9, 5, 7, rider);                         // rider
    rect_wrap(fb, cx - 2, top + 6, 3, 3, STR_PAL_IVORY);                 // helmet
    for (int i = 0; i < 12; i++) px_wrap(fb, cx + f * (2 + i), top + 9, STR_PAL_CHROME_LIGHT);   // lance
}
static void actors(uint8_t *fb, const st_state_t *s, const st_view_t *v) {
    static const uint8_t CLASS_BODY[3] = {STR_PAL_EMBER, STR_PAL_LAVA_HOT, STR_PAL_CYAN_DARK};
    static const uint8_t CLASS_RIDER[3] = {STR_PAL_OCHRE, STR_PAL_KINGDOM_CRIMSON_LIGHT, STR_PAL_CYAN};
    for (int i = 0; i < s->n_actors; i++) {
        const st_actor_t *a = &s->actors[i];
        int x = floor_div256(a->x), top = sprite_top(v, a->y);
        if (top > ST_FB_H || top + 28 < 0) continue;
        switch (a->lifecycle) {
        case ST_LC_MOUNTED:
        case ST_LC_SPAWNING:
            bird(fb, x, top, a->facing, CLASS_BODY[a->cls], CLASS_RIDER[a->cls], a->vy < -100 && ((v->frame >> 2) & 1));
            break;
        case ST_LC_DISMOUNTED:
            rect_wrap(fb, x + 12, top + 17, 5, 8, CLASS_RIDER[a->cls]);
            rect_wrap(fb, x + 13, top + 14, 3, 3, STR_PAL_IVORY);
            break;
        case ST_LC_EGG:
        case ST_LC_HATCHING:
        case ST_LC_REMOUNTING: {
            bool blink = a->lifecycle != ST_LC_EGG && ((v->frame >> 2) & 1);
            uint8_t c = blink ? STR_PAL_GOLD_LIGHT : STR_PAL_IVORY_LIGHT;
            rect_wrap(fb, x + 12, top + 18, 6, 7, c);
            rect_wrap(fb, x + 11, top + 20, 8, 4, c);
            px_wrap(fb, x + 13, top + 19, STR_PAL_WHITE);
            break;
        }
        default: break;
        }
    }
}
static void player(uint8_t *fb, const st_state_t *s, const st_view_t *v) {
    const st_player_t *p = &s->player;
    if (s->sim.shell == ST_SHELL_GAMEOVER) return;
    if (p->invulnerable_ticks > ST_SHIMMER_TICKS) return;                // hidden before respawn
    if (p->invulnerable_ticks > 0 && ((v->frame >> 2) & 1)) return;      // mercy shimmer
    int x = floor_div256(p->x), top = sprite_top(v, p->y);
    bool flap = p->flap_cooldown > 3;
    bird(fb, x, top, p->facing, STR_PAL_CHROME, STR_PAL_GOLD_LIGHT, flap);
}
static void hud(uint8_t *fb, const st_state_t *s, const st_view_t *v) {
    char t[32];
    rect(fb, 0, 0, ST_FB_W, 20, STR_PAL_INK);
    rect(fb, 0, 20, ST_FB_W, 1, STR_PAL_GOLD_DEEP);
    st_draw_text(fb, 4, 2, "SCORE", STR_PAL_GOLD, 1);
    snprintf(t, sizeof t, "%06ld", (long)s->sim.score);
    st_draw_text(fb, 4, 11, t, STR_PAL_GOLD_LIGHT, 1);
    snprintf(t, sizeof t, "ROUND %ld", (long)s->tower.round);
    st_draw_text(fb, ST_FB_W - 4 - st_text_width(t, 1), 2, t, STR_PAL_GOLD, 1);
    // Joust Marks (lives) as pips, rings taken as six cyan pips + the gold one.
    for (int i = 0; i < s->sim.lives && i < 11; i++) rect(fb, ST_FB_W - 4 - 6 * (i + 1) + 1, 12, 4, 4, STR_PAL_GOLD_LIGHT);
    for (int i = 0; i < 6; i++) rect(fb, 92 + i * 9, 4, 6, 6, (s->tower.ring_mask >> i) & 1 ? STR_PAL_RING_LIGHT : STR_PAL_RING_DEEP);
    rect(fb, 92 + 6 * 9, 4, 6, 6, (s->tower.ring_mask & 64) ? STR_PAL_GOLD_LIGHT : STR_PAL_GOLD_DEEP);
    // Wing (flap stamina) bar.
    rect(fb, 92, 13, 64, 3, STR_PAL_NAVY);
    rect(fb, 92, 13, s->player.wing, 3, s->player.wing < 12 ? STR_PAL_LAVA_HOT : STR_PAL_CYAN);
    (void)v;
}
static void card(uint8_t *fb, int y, int h) {
    rect(fb, 16, y, ST_FB_W - 32, h, STR_PAL_INK);
    rect(fb, 16, y, ST_FB_W - 32, 2, STR_PAL_GOLD);
    rect(fb, 16, y + h - 2, ST_FB_W - 32, 2, STR_PAL_GOLD);
}
static void overlays(uint8_t *fb, const st_state_t *s, const st_view_t *v) {
    char t[40];
    if (s->sim.shell == ST_SHELL_GAMEOVER) {
        card(fb, 132, 104);
        text_center(fb, 146, "GAME OVER", STR_PAL_LAVA_HOT, 3);
        snprintf(t, sizeof t, "SCORE %ld", (long)s->sim.score);
        text_center(fb, 182, t, STR_PAL_GOLD_LIGHT, 1);
        snprintf(t, sizeof t, "BEST %ld", (long)(v->high_score > s->sim.score ? v->high_score : s->sim.score));
        text_center(fb, 194, t, STR_PAL_GOLD, 1);
        if ((v->frame >> 5) & 1) text_center(fb, 214, "PRESS A WING", STR_PAL_IVORY, 1);
        return;
    }
    if (s->tower.hold > 0) {
        card(fb, 150, 44);
        snprintf(t, sizeof t, "ROUND %ld CLEAR", (long)s->tower.round);
        text_center(fb, 160, t, STR_PAL_GOLD_LIGHT, 2);
        if (s->run.clean) text_center(fb, 180, "NO LOSSES", STR_PAL_GREEN, 1);
    } else if (!s->tower.go) {                       // before the first move of a round
        snprintf(t, sizeof t, "ROUND %ld", (long)s->tower.round);
        text_center(fb, 150, t, STR_PAL_GOLD_LIGHT, 2);
        if ((v->frame >> 5) & 1) text_center(fb, 172, "FLAP TO CLIMB", STR_PAL_IVORY, 1);
    } else if (s->player.invulnerable_ticks > ST_SHIMMER_TICKS) {
        text_center(fb, 160, "GET READY", STR_PAL_GOLD_LIGHT, 2);
    }
    if (v->banner) text_center(fb, 28, v->banner, STR_PAL_GOLD_LIGHT, 1);
}

void st_render(uint8_t *fb, const st_state_t *s, const st_view_t *v) {
    sky(fb, v);
    moon(fb, v);
    lava(fb, s, v);
    islands(fb, s, v);
    rings(fb, s, v);
    actors(fb, s, v);
    player(fb, s, v);
    hud(fb, s, v);
    overlays(fb, s, v);
}

// ---- presentation: 256x384 indexed -> 320x480 RGB565 (5:4 nearest) ------------------
void st_present_line(const uint8_t *fb, int panel_y, uint16_t out[ST_PANEL_W], bool swap_bytes) {
    const uint8_t *row = fb + (panel_y * 4 / 5) * ST_FB_W;
    for (int x = 0; x < ST_PANEL_W; x++) {
        uint16_t c = STR_PALETTE_RGB565[row[x * 4 / 5] % STR_PAL_COUNT];
        out[x] = swap_bytes ? (uint16_t)((c >> 8) | (c << 8)) : c;
    }
}
