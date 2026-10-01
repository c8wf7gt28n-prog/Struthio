// STRUTHIO HANDHELD · panel renderer. See struthio_panel.h.
#include "struthio_panel.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

static const float S1 = 286.0f / 768.0f;      // panel density / canvas density

static inline float clampf(float x, float lo, float hi) { return x < lo ? lo : x > hi ? hi : x; }
static inline uint8_t u8f(float v) { v = clampf(v, 0, 1); return (uint8_t)(v * 255.0f + 0.5f); }

// ---- lookup tables ------------------------------------------------------------------------
void st_panel_luts_init(st_panel_luts_t *l) {
    for (int c = 0; c < 3; c++) for (int i = 0; i < 256; i++) {
        float in[3] = {0, 0, 0}, o[3];
        in[c] = i / 255.0f;
        st_tone(in, o);
        l->tone[c][i] = (uint16_t)(clampf(o[c], 0, 1) * 65535.0f + 0.5f);
    }
    for (int v = 0; v < 65536; v++) {
        float in[3] = {(v >> 11) / 31.0f, ((v >> 5) & 63) / 63.0f, (v & 31) / 31.0f}, o[3];
        st_grade_arcade(in, o);
        l->grade[v] = (uint16_t)((((int)(clampf(o[0], 0, 1) * 31 + 0.5f)) << 11) | (((int)(clampf(o[1], 0, 1) * 63 + 0.5f)) << 5) | (int)(clampf(o[2], 0, 1) * 31 + 0.5f));
    }
    l->ready = true;
}

// ---- HUD model (hud.mjs) -------------------------------------------------------------------
static int bit_count(uint32_t m) { int c = 0; while (m) { c += m & 1; m >>= 1; } return c; }
void st_hud_reset(st_hud_t *h, int32_t rt) { memset(h, 0, sizeof *h); h->live_since = rt; h->due_since = -1; }
static float bezier_ease_in_out(float x) {             // cubic-bezier(.42, 0, .58, 1)
    float lo = 0, hi = 1, t = x;
    for (int i = 0; i < 24; i++) {
        t = (lo + hi) / 2;
        float bx = 3 * (1 - t) * (1 - t) * t * 0.42f + 3 * (1 - t) * t * t * 0.58f + t * t * t;
        if (bx < x) lo = t; else hi = t;
    }
    return 3 * (1 - t) * t * t + t * t * t;              // y control points 0 and 1
}
void st_hud_update(st_hud_t *h, const st_hud_assets_t *a, const st_state_t *s, const st_scene_t *sc) {
    int32_t rt = sc->render_tick;
    uint32_t mask = (uint32_t)s->tower.ring_mask;
    h->score = s->sim.score;
    h->round = s->tower.round;
    h->rings = bit_count(mask & 63);
    bool due = (mask & 63) == 63 && !(mask & 64);
    if (due && !h->due) h->due_since = rt;
    h->due = due;
    h->kills = s->tower.kills;
    h->lives = s->sim.lives < 0 ? 0 : s->sim.lives > 11 ? 11 : s->sim.lives;
    h->paused = s->sim.shell == ST_SHELL_PAUSE;
    // toast: the session banner, or PAUSED
    const st_hud_layer_t *toast = NULL;
    if (sc->banner_until > rt) {
        int n = 0;
        if (!strcmp(sc->banner, "EXTRA JOUST MARK")) toast = &a->toast_extra;
        else if (!strncmp(sc->banner, "6/6", 3)) toast = &a->toast_gold;
        else if (sscanf(sc->banner, "ROUND %d", &n) == 1 && n > 0 && n < ST_HUD_ROUNDS)
            toast = strstr(sc->banner, "NO LOSSES") ? &a->toast_clean[n] : &a->toast_clear[n];
    }
    if (h->paused) toast = &a->toast_paused;
    // The text changes at once; only opacity transitions (160 ms). When the
    // banner ends the browser empties the text, so the toast goes at once.
    if (toast) {
        if (toast != h->toast) h->toast_opacity = h->toast ? h->toast_opacity : 0;
        h->toast = toast;
        h->toast_opacity = clampf(h->toast_opacity + 1.0f / (0.160f * 60.0f), 0, 1);
    } else { h->toast = NULL; h->toast_opacity = 0; }
    h->opacity = clampf((rt - h->live_since) / (0.140f * 60.0f), 0, 1);
    if (h->due) {
        float p = fmodf((float)(rt - h->due_since), 72.0f) / 72.0f;
        h->due_brightness = p < 0.5f ? 1.0f + 0.35f * bezier_ease_in_out(p * 2) : 1.35f - 0.35f * bezier_ease_in_out(p * 2 - 1);
    } else h->due_brightness = 1.0f;
}

// ---- band compositing -------------------------------------------------------------------------
typedef struct { uint8_t rgb[ST_BAND_ROWS][ST_PANEL_W][3]; uint16_t depth[ST_BAND_ROWS][ST_GAME_W]; } band_t;

static void layer_over(band_t *b, int y0, int rows, const st_hud_layer_t *l, float opacity, float bright) {
    if (!l || !l->p || !l->w || opacity <= 0) return;
    int ly0 = l->y > y0 ? l->y : y0, ly1 = l->y + l->h < y0 + rows ? l->y + l->h : y0 + rows;
    for (int y = ly0; y < ly1; y++) {
        const uint8_t *src = l->p + ((size_t)(y - l->y) * l->w) * 4;
        uint8_t (*dst)[3] = b->rgb[y - y0];
        for (int x = 0; x < l->w; x++, src += 4) {
            int px = l->x + x;
            if (px < 0 || px >= ST_PANEL_W || !src[3]) continue;
            float a = src[3] / 255.0f * opacity, ia = 1.0f - a;
            for (int c = 0; c < 3; c++) {
                float v = src[c] / 255.0f * opacity * bright + dst[px][c] / 255.0f * ia;
                dst[px][c] = u8f(v);
            }
        }
    }
}
static void hud_over(band_t *b, int y0, int rows, const st_hud_assets_t *a, const st_hud_t *h) {
    if (!a) return;
    int v = h->lives == 11 ? 0 : 1;
    float op = h->opacity;
    layer_over(b, y0, rows, &a->statics[v], op, 1);
    int32_t sc = h->score % 1000000;
    for (int i = 5, n = sc; i >= 0; i--, n /= 10) layer_over(b, y0, rows, &a->score[i][n % 10], op, 1);
    int r = h->round > 99 ? 99 : h->round;
    layer_over(b, y0, rows, &a->round[0][r / 10], op, 1);
    layer_over(b, y0, rows, &a->round[1][r % 10], op, 1);
    layer_over(b, y0, rows, &a->ring[v][h->due ? 7 : h->rings], op, h->due ? h->due_brightness : 1);
    int k = h->kills > 999 ? 999 : h->kills;
    if (k > 99) {
        layer_over(b, y0, rows, &a->swords[v][1], op, 1);
        layer_over(b, y0, rows, &a->kills3[v][0][k / 100], op, 1);
        layer_over(b, y0, rows, &a->kills3[v][1][(k / 10) % 10], op, 1);
        layer_over(b, y0, rows, &a->kills3[v][2][k % 10], op, 1);
    } else {
        layer_over(b, y0, rows, &a->swords[v][0], op, 1);
        layer_over(b, y0, rows, &a->kills2[v][0][k / 10], op, 1);
        layer_over(b, y0, rows, &a->kills2[v][1][k % 10], op, 1);
    }
    layer_over(b, y0, rows, &a->joust_b[h->lives], op, 1);
    layer_over(b, y0, rows, &a->joust_i[h->lives], op, 1);
    if (h->toast) layer_over(b, y0, rows, h->toast, h->toast_opacity * op, 1);
}

static inline const uint8_t *tex_at(const st_tex_t *t, int x, int y) {
    x = x < 0 ? 0 : x >= t->w ? t->w - 1 : x;
    y = y < 0 ? 0 : y >= t->h ? t->h - 1 : y;
    return t->p + ((size_t)y * t->w + x) * 4;
}
static void draw_quads(band_t *b, int y0, int rows, const st_panel_textures_t *tx, const st_quads_t *q, const st_frame_params_t *fp) {
    // game rows of this band
    int g0 = y0 - ST_GAME_Y, g1 = y0 + rows - ST_GAME_Y;
    if (g0 < 0) g0 = 0;
    if (g1 > ST_GAME_H) g1 = ST_GAME_H;
    if (g0 >= g1) return;
    const float kx = 256.0f / ST_GAME_W, ky = 384.0f / ST_GAME_H;      // panel px -> logical px
    for (int n = 0; n < q->n; n++) {
        const st_quad_t *it = &q->q[n];
        float dx = (float)it->x, dy = (float)it->y, dw = (float)it->w, dh = (float)it->h;
        float ssx, ssw;
        if (it->sw >= 0) { ssx = (float)it->sx; ssw = it->sw > 1 ? (float)(it->sw - 1) : 0.0f; }
        else { ssx = (float)(it->sx - 1); ssw = (float)(it->sw + 1); }
        float ssy = (float)it->sy, ssh = it->sh > 1 ? (float)(it->sh - 1) : 0.0f;
        float x0 = dx, x1 = dx + dw, y0l = dy, y1l = dy + dh;
        if (x1 < x0) { float t = x0; x0 = x1; x1 = t; }
        if (y1l < y0l) { float t = y0l; y0l = y1l; y1l = t; }
        // game pixels whose centres fall inside
        int px0 = (int)ceilf(x0 / kx - 0.5f), px1 = (int)ceilf(x1 / kx - 0.5f);
        int py0 = (int)ceilf(y0l / ky - 0.5f), py1 = (int)ceilf(y1l / ky - 0.5f);
        if (px0 < 0) px0 = 0;
        if (px1 > ST_GAME_W) px1 = ST_GAME_W;
        if (py0 < g0) py0 = g0;
        if (py1 > g1) py1 = g1;
        if (px0 >= px1 || py0 >= py1) continue;
        uint16_t z = (uint16_t)(clampf((float)it->z, 0, 1) * 65535.0f);
        int mat = it->flags;
        // the texture and its scale from full-resolution texels
        const st_tex_t *t;
        float scale = S1, ox = 0, oy = 0;
        bool world = mat == ST_MAT_WORLD, island = mat == ST_MAT_ISLAND;
        if (world) { if (it->sx >= 768) { t = &tx->world_near; ox = 768; } else t = &tx->world_rear; }
        else if (mat == ST_MAT_PLAYER) t = &tx->bird[0];
        else if (mat >= 3 && mat <= 5) t = &tx->bird[mat - 2];
        else {
            double ratio = fabs(it->sw) / (fabs(it->w) / kx);          // full-res texels per panel px
            bool in_strip = it->sx >= 1536 && it->sx + (it->sw < 0 ? 0 : it->sw) <= 2048 && it->sy + it->sh <= 568;
            if (in_strip && ratio < 2.0) { t = &tx->atlas_hi; scale = 1.0f; ox = 1536; }
            else t = &tx->atlas;
        }
        float inv_w = 1.0f / (x1 - x0), inv_h = 1.0f / (y1l - y0l);
        for (int py = py0; py < py1; py++) {
            float cy = (py + 0.5f) * ky;
            float v = (cy - y0l) * inv_h;
            float ty = ssy + v * ssh + 0.5f;
            int iy = (int)floorf((ty - oy) * scale);
            uint8_t (*row)[3] = b->rgb[py + ST_GAME_Y - y0];
            uint16_t *drow = b->depth[py + ST_GAME_Y - y0];
            for (int px = px0; px < px1; px++) {
                if (z > drow[px]) continue;
                float u = ((px + 0.5f) * kx - x0) * inv_w;
                float txf = ssx + u * ssw + 0.5f;
                float c[3], a;
                if (tx->bilinear && scale < 1.0f) {
                    // premultiplied bilinear at the footprint centre
                    float fx = (txf - ox) * scale - 0.5f, fy = (ty - oy) * scale - 0.5f;
                    int ix0 = (int)floorf(fx), iy0 = (int)floorf(fy);
                    float wx = fx - ix0, wy = fy - iy0, acc[4] = {0, 0, 0, 0};
                    for (int j = 0; j < 2; j++) for (int i = 0; i < 2; i++) {
                        const uint8_t *s = tex_at(t, ix0 + i, iy0 + j);
                        float w = (i ? wx : 1 - wx) * (j ? wy : 1 - wy), sa = s[3] / 255.0f * w;
                        acc[0] += s[0] / 255.0f * sa; acc[1] += s[1] / 255.0f * sa; acc[2] += s[2] / 255.0f * sa; acc[3] += sa;
                    }
                    if (acc[3] < 0.0039f) continue;
                    a = acc[3]; c[0] = acc[0] / a; c[1] = acc[1] / a; c[2] = acc[2] / a;
                } else {
                    const uint8_t *s = tex_at(t, (int)floorf((txf - ox) * scale), iy);
                    if (s[3] == 0) continue;
                    c[0] = s[0] / 255.0f; c[1] = s[1] / 255.0f; c[2] = s[2] / 255.0f; a = s[3] / 255.0f;
                }
                if (world) st_world_shade(c, txf, ty, &tx->globe, fp);
                (void)island;                    // palette baked; the 0-4% music pulse is not reproduced
                drow[px] = z;
                uint8_t *d = row[px + ST_GAME_X];
                float ia = 1.0f - a;
                d[0] = u8f(c[0] * a + d[0] / 255.0f * ia);
                d[1] = u8f(c[1] * a + d[1] / 255.0f * ia);
                d[2] = u8f(c[2] * a + d[2] / 255.0f * ia);
            }
        }
    }
}

void st_panel_render(const st_panel_textures_t *tx, const st_hud_assets_t *hud_a, const st_hud_t *hud, const st_panel_luts_t *luts,
                     const st_quads_t *q, const st_frame_params_t *fp, st_band_fn out, void *ctx) {
    static band_t b;
    static uint16_t line[ST_BAND_ROWS * ST_PANEL_W];
    const uint8_t clear[3] = {u8f(0.027f), u8f(0.075f), u8f(0.122f)};
    for (int y0 = 0; y0 < ST_PANEL_H; y0 += ST_BAND_ROWS) {
        int rows = ST_PANEL_H - y0 < ST_BAND_ROWS ? ST_PANEL_H - y0 : ST_BAND_ROWS;
        // the frame, and the game area cleared
        for (int r = 0; r < rows; r++) {
            int y = y0 + r;
            bool game_row = y >= ST_GAME_Y && y < ST_GAME_Y + ST_GAME_H;
            for (int x = 0; x < ST_PANEL_W; x++) {
                bool game = game_row && x >= ST_GAME_X && x < ST_GAME_X + ST_GAME_W;
                if (game) memcpy(b.rgb[r][x], clear, 3);
                else if (hud_a && hud_a->chrome) memcpy(b.rgb[r][x], hud_a->chrome + ((size_t)y * ST_PANEL_W + x) * 4, 3);
                else memset(b.rgb[r][x], 0, 3);
            }
            for (int x = 0; x < ST_GAME_W; x++) b.depth[r][x] = 65535;
        }
        draw_quads(&b, y0, rows, tx, q, fp);
        // post (quality 0): tone per channel, then the Arcade grade on the panel's RGB565
        for (int r = 0; r < rows && !luts->skip_post; r++) {
            int y = y0 + r;
            if (y < ST_GAME_Y || y >= ST_GAME_Y + ST_GAME_H) continue;
            for (int x = ST_GAME_X; x < ST_GAME_X + ST_GAME_W; x++) {
                uint8_t *p = b.rgb[r][x];
                uint32_t tr = luts->tone[0][p[0]], tg = luts->tone[1][p[1]], tb = luts->tone[2][p[2]];
                uint16_t i565 = (uint16_t)((((tr * 31 + 32767) / 65535) << 11) | (((tg * 63 + 32767) / 65535) << 5) | ((tb * 31 + 32767) / 65535));
                uint16_t o = luts->grade[i565];
                p[0] = (uint8_t)(((o >> 11) * 255 + 15) / 31);
                p[1] = (uint8_t)((((o >> 5) & 63) * 255 + 31) / 63);
                p[2] = (uint8_t)(((o & 31) * 255 + 15) / 31);
            }
        }
        hud_over(&b, y0, rows, hud_a, hud);
        for (int r = 0; r < rows; r++) for (int x = 0; x < ST_PANEL_W; x++) {
            const uint8_t *p = b.rgb[r][x];
            line[r * ST_PANEL_W + x] = (uint16_t)(((p[0] * 31 + 127) / 255) << 11 | ((p[1] * 63 + 127) / 255) << 5 | ((p[2] * 31 + 127) / 255));
        }
        out(ctx, y0, rows, line);
    }
}
