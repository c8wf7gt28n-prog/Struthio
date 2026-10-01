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
typedef st_panel_work_t band_t;

// HUD layers are premultiplied RGBA8, raw or run-length coded per row
// (struthio_pak.h): a token t, t >> 6 = 0: (t & 63) + 1 literal pixels follow;
// 2: that many transparent pixels; 3: that many pixels as in the base layer.
// Decodes one row into out (w pixels; NULL just advances); returns the next row.
static const uint8_t *rle_row(const uint8_t *src, int w, uint8_t (*out)[4]) {
    for (int x = 0; x < w;) {
        uint8_t t = *src++;
        int n = (t & 63) + 1, k = t >> 6;
        if (out) {
            if (k == 0) memcpy(out[x], src, (size_t)n * 4);
            else if (k == 2) memset(out[x], 0, (size_t)n * 4);
        }
        if (k == 0) src += n * 4;
        x += n;
    }
    return src;
}
static void layer_over(band_t *b, int y0, int rows, const st_hud_layer_t *l, float opacity, float bright) {
    if (!l || !l->p || !l->w || opacity <= 0) return;
    int ly0 = l->y > y0 ? l->y : y0, ly1 = l->y + l->h < y0 + rows ? l->y + l->h : y0 + rows;
    if (ly0 >= ly1) return;
    uint8_t (*px)[4] = b->hud_row;
    const uint8_t *src = l->p, *bsrc = l->base ? l->base->p : NULL;
    if (l->rle) for (int y = l->y; y < ly0; y++) { src = rle_row(src, l->w, NULL); if (bsrc) bsrc = rle_row(bsrc, l->w, NULL); }
    else src += (size_t)(ly0 - l->y) * l->w * 4;
    for (int y = ly0; y < ly1; y++) {
        if (l->rle) {
            if (bsrc) bsrc = rle_row(bsrc, l->w, px);     // the base row first; copy runs keep it
            src = rle_row(src, l->w, px);
        } else { memcpy(px, src, (size_t)l->w * 4); src += (size_t)l->w * 4; }
        uint8_t (*dst)[3] = b->rgb[y - y0];
        for (int x = 0; x < l->w; x++) {
            const uint8_t *q = px[x];
            int x_ = l->x + x;
            if (!q[3] || x_ < 0 || x_ >= ST_PANEL_W) continue;
            float a = q[3] / 255.0f * opacity, ia = 1.0f - a;
            for (int c = 0; c < 3; c++) dst[x_][c] = u8f(q[c] / 255.0f * opacity * bright + dst[x_][c] / 255.0f * ia);
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

// One texel as RGBA8 (plus the attribute bytes of the world plates).
static inline void texel(const st_tex_t *t, int x, int y, uint8_t o[4], uint8_t attr[2]) {
    x = x < 0 ? 0 : x >= t->w ? t->w - 1 : x;
    y = y < 0 ? 0 : y >= t->h ? t->h - 1 : y;
    size_t i = (size_t)y * t->w + x;
    const uint8_t *p;
    uint16_t c;
    switch (t->format) {
    case ST_TEX_565: p = t->p + i * 2; c = (uint16_t)(p[0] | p[1] << 8); o[3] = 255; break;
    case ST_TEX_565A8: p = t->p + i * 3; c = (uint16_t)(p[0] | p[1] << 8); o[3] = p[2]; break;
    case ST_TEX_REAR: p = t->p + i * 4; c = (uint16_t)(p[0] | p[1] << 8); o[3] = 255; attr[0] = p[2]; attr[1] = p[3]; break;
    case ST_TEX_NEAR: p = t->p + i * 4; c = (uint16_t)(p[0] | p[1] << 8); o[3] = p[2]; attr[0] = p[3]; break;
    default: p = t->p + i * 4; memcpy(o, p, 4); return;
    }
    o[0] = (uint8_t)(((c >> 11) * 255 + 15) / 31);
    o[1] = (uint8_t)((((c >> 5) & 63) * 255 + 31) / 63);
    o[2] = (uint8_t)(((c & 31) * 255 + 15) / 31);
}
static void draw_quads(band_t *b, int y0, int rows, const st_panel_textures_t *tx, const st_quads_t *q, const st_frame_params_t *fp,
                       const st_amb_frame_t *af) {
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
        const bool rear = world && t == &tx->world_rear;
        const float spin = fp->moon_phase - floorf(fp->moon_phase);
        for (int py = py0; py < py1; py++) {
            float cy = (py + 0.5f) * ky;
            float v = (cy - y0l) * inv_h;
            float ty = ssy + v * ssh + 0.5f;
            int iy = (int)floorf((ty - oy) * scale);
            st_amb_row_t arow;
            if (world) st_amb_row(af, ty, rear, &arow);
            uint8_t (*row)[3] = b->rgb[py + ST_GAME_Y - y0];
            uint16_t *drow = b->depth[py + ST_GAME_Y - y0];
            for (int px = px0; px < px1; px++) {
                if (z > drow[px]) continue;
                float u = ((px + 0.5f) * kx - x0) * inv_w;
                float txf = ssx + u * ssw + 0.5f;
                float c[3], a;
                uint8_t s4[4], attr[2] = {0, 0};
                if (tx->bilinear && scale < 1.0f) {
                    // premultiplied bilinear at the footprint centre (attributes from the nearest texel)
                    float fx = (txf - ox) * scale - 0.5f, fy = (ty - oy) * scale - 0.5f;
                    int ix0 = (int)floorf(fx), iy0 = (int)floorf(fy);
                    float wx = fx - ix0, wy = fy - iy0, acc[4] = {0, 0, 0, 0};
                    for (int j = 0; j < 2; j++) for (int i = 0; i < 2; i++) {
                        uint8_t q4[4], qa[2];
                        texel(t, ix0 + i, iy0 + j, q4, qa);
                        float w = (i ? wx : 1 - wx) * (j ? wy : 1 - wy), sa = q4[3] / 255.0f * w;
                        acc[0] += q4[0] / 255.0f * sa; acc[1] += q4[1] / 255.0f * sa; acc[2] += q4[2] / 255.0f * sa; acc[3] += sa;
                    }
                    if (acc[3] < 0.0039f) continue;
                    a = acc[3]; c[0] = acc[0] / a; c[1] = acc[1] / a; c[2] = acc[2] / a;
                    if (world) texel(t, (int)floorf((txf - ox) * scale), iy, s4, attr);
                } else {
                    texel(t, (int)floorf((txf - ox) * scale), iy, s4, attr);
                    if (s4[3] == 0) continue;
                    c[0] = s4[0] / 255.0f; c[1] = s4[1] / 255.0f; c[2] = s4[2] / 255.0f; a = s4[3] / 255.0f;
                }
                if (world) {
                    int ix = (int)floorf((txf - ox) * scale);
                    if (rear && (attr[1] & 128) && tx->globe_lut) {
                        // the turning moon (colour mode): this texel's latitude row and longitude
                        int gx = ix - tx->globe_x0, gy = iy - tx->globe_y0;
                        if (gx >= 0 && gy >= 0 && gx < tx->globe_w && gy < tx->globe_h) {
                            const uint16_t *e = tx->globe_lut + ((size_t)gy * tx->globe_w + gx) * 2;
                            float u = e[1] / 65536.0f - spin;
                            u -= floorf(u);
                            uint8_t g4[4], ga[2];
                            texel(&tx->globe_map, (int)(u * tx->globe_map.w) % tx->globe_map.w, e[0], g4, ga);
                            c[0] = g4[0] / 255.0f; c[1] = g4[1] / 255.0f; c[2] = g4[2] / 255.0f;
                        }
                    } else {
                        st_amb_texel_t at = {0};
                        at.rear = rear;
                        if (rear) { at.lit = attr[0] / 255.0f; at.star = (attr[1] & 127) != 0; at.star_w = (attr[1] & 127) / 127.0f; }
                        else { at.gold = (attr[0] >> 4) / 15.0f; at.cyan = (attr[0] & 15) / 15.0f; }
                        float streak, g = st_amb_gain(af, &arow, &at, txf, ty, &streak);
                        c[0] = c[0] * g + streak * 0.85f; c[1] = c[1] * g + streak * 0.92f; c[2] = c[2] * g + streak;
                    }
                }
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
    static st_panel_work_t work;
    st_panel_render_bands(tx, hud_a, hud, luts, q, fp, 0, 1, &work, out, ctx);
}
void st_panel_render_bands(const st_panel_textures_t *tx, const st_hud_assets_t *hud_a, const st_hud_t *hud, const st_panel_luts_t *luts,
                           const st_quads_t *q, const st_frame_params_t *fp, int first, int stride, st_panel_work_t *w,
                           st_band_fn out, void *ctx) {
    band_t *bp = w;
    uint16_t *line = w->line ? w->line : w->line_store;
    const uint8_t clear[3] = {u8f(0.027f), u8f(0.075f), u8f(0.122f)};
    st_amb_frame_t af;
    st_textures_t gp;
    memset(&gp, 0, sizeof gp);
    memcpy(gp.globe_params, tx->globe_params, sizeof gp.globe_params);
    st_amb_frame(&af, fp, &gp);
    for (int y0 = first * ST_BAND_ROWS; y0 < ST_PANEL_H; y0 += stride * ST_BAND_ROWS) {
        int rows = ST_PANEL_H - y0 < ST_BAND_ROWS ? ST_PANEL_H - y0 : ST_BAND_ROWS;
        // the frame, and the game area cleared
        for (int r = 0; r < rows; r++) {
            int y = y0 + r;
            bool game_row = y >= ST_GAME_Y && y < ST_GAME_Y + ST_GAME_H;
            for (int x = 0; x < ST_PANEL_W; x++) {
                bool game = game_row && x >= ST_GAME_X && x < ST_GAME_X + ST_GAME_W;
                if (game) memcpy(bp->rgb[r][x], clear, 3);
                else if (hud_a && hud_a->chrome) {
                    const uint8_t *cp = hud_a->chrome + ((size_t)y * ST_PANEL_W + x) * 2;
                    uint16_t c = (uint16_t)(cp[0] | cp[1] << 8);
                    bp->rgb[r][x][0] = (uint8_t)(((c >> 11) * 255 + 15) / 31);
                    bp->rgb[r][x][1] = (uint8_t)((((c >> 5) & 63) * 255 + 31) / 63);
                    bp->rgb[r][x][2] = (uint8_t)(((c & 31) * 255 + 15) / 31);
                }
                else memset(bp->rgb[r][x], 0, 3);
            }
            for (int x = 0; x < ST_GAME_W; x++) bp->depth[r][x] = 65535;
        }
        draw_quads(bp, y0, rows, tx, q, fp, &af);
        // post (quality 0): tone per channel, then the Arcade grade on the panel's RGB565
        for (int r = 0; r < rows && !luts->skip_post; r++) {
            int y = y0 + r;
            if (y < ST_GAME_Y || y >= ST_GAME_Y + ST_GAME_H) continue;
            for (int x = ST_GAME_X; x < ST_GAME_X + ST_GAME_W; x++) {
                uint8_t *p = bp->rgb[r][x];
                uint32_t tr = luts->tone[0][p[0]], tg = luts->tone[1][p[1]], tb = luts->tone[2][p[2]];
                uint16_t i565 = (uint16_t)((((tr * 31 + 32767) / 65535) << 11) | (((tg * 63 + 32767) / 65535) << 5) | ((tb * 31 + 32767) / 65535));
                uint16_t o = luts->grade[i565];
                p[0] = (uint8_t)(((o >> 11) * 255 + 15) / 31);
                p[1] = (uint8_t)((((o >> 5) & 63) * 255 + 31) / 63);
                p[2] = (uint8_t)(((o & 31) * 255 + 15) / 31);
            }
        }
        hud_over(bp, y0, rows, hud_a, hud);
        for (int r = 0; r < rows; r++) for (int x = 0; x < ST_PANEL_W; x++) {
            const uint8_t *p = bp->rgb[r][x];
            line[r * ST_PANEL_W + x] = (uint16_t)(((p[0] * 31 + 127) / 255) << 11 | ((p[1] * 63 + 127) / 255) << 5 | ((p[2] * 31 + 127) / 255));
        }
        out(ctx, y0, rows, line);
    }
}
