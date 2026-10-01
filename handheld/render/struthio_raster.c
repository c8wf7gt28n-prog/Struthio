// STRUTHIO HANDHELD · software rasterizer. A port of the WGSL in
// arcade/src/render/renderer.mjs and bird-inks.mjs, in 32-bit float like the
// GPU. See struthio_raster.h.
#include "struthio_raster.h"
#include <math.h>
#include <string.h>

typedef struct { float r, g, b; } v3;
static inline v3 V3(float r, float g, float b) { v3 v = {r, g, b}; return v; }
static inline float clampf(float x, float lo, float hi) { return x < lo ? lo : x > hi ? hi : x; }
static inline float mixf(float a, float b, float t) { return a + (b - a) * t; }
static inline v3 mix3(v3 a, v3 b, float t) { return V3(mixf(a.r, b.r, t), mixf(a.g, b.g, t), mixf(a.b, b.b, t)); }
static inline v3 scale3(v3 a, float k) { return V3(a.r * k, a.g * k, a.b * k); }
static inline v3 clamp3(v3 a) { return V3(clampf(a.r, 0, 1), clampf(a.g, 0, 1), clampf(a.b, 0, 1)); }
static inline float smoothstepf(float e0, float e1, float x) { float t = clampf((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t); }
static inline float stepf(float edge, float x) { return x >= edge ? 1.0f : 0.0f; }
static inline float fractf(float x) { return x - floorf(x); }
static inline float maxf(float a, float b) { return a > b ? a : b; }
static inline float minf(float a, float b) { return a < b ? a : b; }
static inline float max3(v3 c) { return maxf(c.r, maxf(c.g, c.b)); }
static inline float min3(v3 c) { return minf(c.r, minf(c.g, c.b)); }
static inline float wgsl_mod(float x, float y) { return x - y * truncf(x / y); }
static inline float hump(float x) { return 4.0f * x * (1.0f - x); }
static inline float wave1(float x) { float f = fractf(x); return f < 0.5f ? hump(f * 2.0f) : -hump(f * 2.0f - 1.0f); }

// ---- bird inks (bird-inks.mjs) -----------------------------------------------------------
typedef struct { float shadow[3], mid[3], light[3], highlight[3], body[3], body_mix, horn[3], horn_mix; int horn_ramp; float plume[3], rim[3]; } ink_t;
#define C3(a, b, c) {(a) / 255.0f, (b) / 255.0f, (c) / 255.0f}
static const ink_t INKS[7] = {
    {C3(6, 34, 48), C3(14, 132, 166), C3(60, 216, 238), C3(214, 250, 255), C3(238, 244, 250), 0.70f, C3(246, 206, 92), 1.00f, 0, C3(150, 206, 226), C3(120, 246, 255)},
    {C3(28, 14, 9), C3(104, 62, 32), C3(158, 96, 44), C3(214, 162, 110), C3(164, 134, 104), 0.62f, C3(192, 54, 40), 0.95f, 0, C3(150, 106, 66), C3(255, 146, 56)},
    {C3(52, 12, 10), C3(188, 28, 28), C3(232, 70, 44), C3(252, 168, 140), C3(154, 112, 96), 0.62f, C3(240, 142, 40), 0.95f, 0, C3(170, 40, 44), C3(255, 86, 70)},
    {C3(68, 14, 10), C3(224, 104, 16), C3(255, 162, 40), C3(255, 220, 156), C3(182, 144, 108), 0.62f, C3(120, 78, 44), 0.95f, 0, C3(112, 66, 172), C3(224, 128, 255)},
    {C3(58, 22, 10), C3(192, 148, 26), C3(252, 216, 74), C3(255, 246, 196), C3(232, 206, 146), 0.84f, C3(214, 74, 34), 0.90f, 0, C3(190, 136, 36), C3(255, 226, 120)},
    {C3(96, 44, 12), C3(230, 168, 52), C3(255, 226, 110), C3(255, 252, 224), C3(255, 240, 190), 0.92f, C3(236, 110, 40), 0.95f, 0, C3(190, 136, 36), C3(255, 226, 120)},
    {C3(70, 8, 12), C3(196, 30, 40), C3(255, 96, 80), C3(255, 230, 220), C3(240, 246, 255), 0.92f, C3(247, 200, 58), 1.00f, 0, C3(52, 120, 255), C3(95, 176, 255)},
};
static const float PLAYER_GLOW[3] = C3(220, 240, 255);
static const float PLAYER_BLUES[3][2][3] = {{C3(14, 132, 166), C3(60, 216, 238)}, {C3(22, 96, 190), C3(86, 170, 255)}, {C3(58, 74, 196), C3(130, 146, 255)}};
static const float BLUE_CYCLE_RATE = 1.0f / 540, BLUE_CYCLE_TRAVEL = 1.0f / 1400;
static inline v3 L3(const float *a) { return V3(a[0], a[1], a[2]); }
static v3 cycle3(v3 a, v3 b, v3 c, float phase) {
    float u = fractf(phase) * 3.0f, i = floorf(u), f = smoothstepf(0, 1, u - i);
    v3 p = a, q = b;
    if (i > 1.5f) { p = c; q = a; } else if (i > 0.5f) { p = b; q = c; }
    return mix3(p, q, f);
}
static v3 bird_ramp(v3 shadow, v3 mid, v3 light, float t) {
    v3 lowc = mix3(shadow, mid, smoothstepf(0.06f, 0.5f, t));
    v3 highc = mix3(mid, light, smoothstepf(0.5f, 0.95f, t));
    return t < 0.5f ? lowc : highc;
}
void st_bird_ink(const float in[3], int id, float phase, float jouster, float out[3]) {
    const ink_t *k = &INKS[id];
    v3 c = V3(in[0], in[1], in[2]);
    v3 mid = L3(k->mid), light = L3(k->light);
    if (id == 0) {
        mid = cycle3(L3(PLAYER_BLUES[0][0]), L3(PLAYER_BLUES[1][0]), L3(PLAYER_BLUES[2][0]), phase);
        light = cycle3(L3(PLAYER_BLUES[0][1]), L3(PLAYER_BLUES[1][1]), L3(PLAYER_BLUES[2][1]), phase);
    }
    float mx = max3(c), d = mx - min3(c);
    float sat = mx > 0.0001f ? d / maxf(mx, 0.0001f) : 0.0f;
    float dd = maxf(d, 0.00001f);
    float h = ((c.r - c.g) / dd + 4.0f) * 60.0f;
    if (mx == c.g) h = ((c.b - c.r) / dd + 2.0f) * 60.0f;
    if (mx == c.r) h = ((c.g - c.b) / dd) * 60.0f;
    if (h > 180.0f) h = h - 360.0f;
    float wF = (1.0f - smoothstepf(14.0f, 26.0f, fabsf(h))) * smoothstepf(0.30f, 0.55f, sat);
    float horn_hue = smoothstepf(16.0f, 24.0f, h) * (1.0f - smoothstepf(58.0f, 70.0f, h));
    float wH = horn_hue * maxf(smoothstepf(0.40f, 0.55f, c.r - c.b), smoothstepf(0.24f, 0.34f, c.g - c.b)) * (1.0f - wF);
    float body_hue = smoothstepf(12.0f, 20.0f, h) * (1.0f - smoothstepf(62.0f, 72.0f, h));
    float wB = smoothstepf(0.06f, 0.14f, sat) * smoothstepf(0.08f, 0.16f, mx) * body_hue * (1.0f - wF) * (1.0f - wH);
    float L = c.r * 0.2126f + c.g * 0.7152f + c.b * 0.0722f;
    v3 o = c;
    if (k->body_mix > 0.0f) o = mix3(o, clamp3(scale3(L3(k->body), L / 0.80f)), wB * k->body_mix);
    if (k->horn_ramp == 1) o = mix3(o, bird_ramp(L3(k->shadow), mid, light, mx), wH);
    else if (k->horn_mix > 0.0f) o = mix3(o, clamp3(scale3(scale3(L3(k->horn), L / 0.55f), 0.85f)), wH * k->horn_mix);
    v3 feather = mix3(bird_ramp(L3(k->shadow), mid, light, mx), L3(k->highlight), smoothstepf(0.2f, 0.6f, 1.0f - sat) * smoothstepf(0.6f, 1.0f, mx));
    v3 res = mix3(o, feather, wF);
    if (id == 6) res = mix3(res, L3(PLAYER_GLOW), wF * smoothstepf(0.985f, 0.998f, mx) * smoothstepf(0.72f, 0.80f, sat));
    float pl = jouster * stepf(c.r + c.g, 0.002f) * stepf(0.1f, c.b);
    float rm = jouster * stepf(0.9f, c.g) * stepf(c.r, 0.1f) * stepf(c.b, 0.1f);
    res = mix3(mix3(res, scale3(L3(k->plume), 0.40f + 0.95f * c.b), pl), L3(k->rim), rm);
    res = clamp3(res);
    out[0] = res.r; out[1] = res.g; out[2] = res.b;
}

// ---- islands -------------------------------------------------------------------------------
static v3 hsv_pick(float mx, float s, float h) {
    float k0 = wgsl_mod(5.0f + h / 60.0f, 6.0f), k1 = wgsl_mod(3.0f + h / 60.0f, 6.0f), k2 = wgsl_mod(1.0f + h / 60.0f, 6.0f);
    return V3(mx - mx * s * clampf(minf(k0, 4.0f - k0), 0, 1), mx - mx * s * clampf(minf(k1, 4.0f - k1), 0, 1), mx - mx * s * clampf(minf(k2, 4.0f - k2), 0, 1));
}
void st_island_palette(const float in[3], float out[3]) {
    v3 c = V3(in[0], in[1], in[2]);
    float mx = max3(c), d = mx - min3(c);
    if (d < 0.0001f) { out[0] = c.r; out[1] = c.g; out[2] = c.b; return; }
    float h;
    if (mx == c.r) h = (c.g - c.b) / d * 60.0f;
    else if (mx == c.g) h = ((c.b - c.r) / d + 2.0f) * 60.0f;
    else { out[0] = c.r; out[1] = c.g; out[2] = c.b; return; }
    float s = d / mx, lit = smoothstepf(0.10f, 0.20f, mx);
    float wr = smoothstepf(-48.0f, -32.0f, h) * (1.0f - smoothstepf(20.0f, 32.0f, h)) * smoothstepf(0.28f, 0.45f, s) * lit;
    float wy = smoothstepf(34.0f, 42.0f, h) * (1.0f - smoothstepf(66.0f, 76.0f, h)) * smoothstepf(0.25f, 0.40f, s) * lit;
    h = mixf(h, 18.0f, wr) - 8.0f * wy;
    float s2 = s * (1.0f - 0.14f * wr);
    v3 o = hsv_pick(mx, s2, h + 360.0f);
    out[0] = o.r; out[1] = o.g; out[2] = o.b;
}
v3 st_globe_surface_(v3 base, float wx, float wy, const st_textures_t *tx, float spin);
v3 st_arcade_ambient_(v3 base, float wx, float wy, float t, const st_frame_params_t *fp, const st_textures_t *tx);
float st_island_pulse(const float in[3], float t, const st_frame_params_t *fp) {
    float red = (in[0] > 0.55f && in[1] < 0.40f && in[0] > in[2] * 1.4f) ? 1.0f : 0.0f;
    float core = clampf((minf(in[1], in[2]) - in[0] - 0.15f) / 0.35f, 0, 1) * stepf(0.6f, in[2]);
    float amp = fp->motion * (0.04f + 0.08f * fp->beat) * (0.75f + 0.25f * wave1(t * 0.0079577f));
    return 1.0f + amp * maxf(red, core);
}
void st_world_shade(float rgb[3], float wx, float wy, const st_textures_t *tx, const st_frame_params_t *fp) {
    v3 w = V3(rgb[0], rgb[1], rgb[2]);
    w = st_globe_surface_(w, wx, wy, tx, fractf(fp->moon_phase));
    w = st_arcade_ambient_(w, wx, wy, fp->ambient_tick, fp, tx);
    rgb[0] = w.r; rgb[1] = w.g; rgb[2] = w.b;
}
static v3 arcade_island(v3 c, float t, const st_frame_params_t *fp) {
    float in[3] = {c.r, c.g, c.b}, o[3];
    st_island_palette(in, o);
    float red = (c.r > 0.55f && c.g < 0.40f && c.r > c.b * 1.4f) ? 1.0f : 0.0f;
    float core = clampf((minf(c.g, c.b) - c.r - 0.15f) / 0.35f, 0, 1) * stepf(0.6f, c.b);
    float amp = fp->motion * (0.04f + 0.08f * fp->beat) * (0.75f + 0.25f * wave1(t * 0.0079577f));
    return scale3(V3(o[0], o[1], o[2]), 1.0f + amp * maxf(red, core));
}

// ---- world plate: turning moon + ambience ------------------------------------------------------
static float fx_hash(float px, float py) {
    float a = fractf(px * 0.1031f), b = fractf(py * 0.1031f), c = fractf(px * 0.1031f);
    float d = a * (b + 33.33f) + b * (c + 33.33f) + c * (a + 33.33f);
    a += d; b += d; c += d;
    return fractf((a + b) * c);
}
v3 st_globe_surface_(v3 base, float wx, float wy, const st_textures_t *tx, float spin);
v3 st_globe_surface_(v3 base, float wx, float wy, const st_textures_t *tx, float spin) {
    if (wx >= 768.0f) return base;
    const float *g = tx->globe_params;
    float r = fabsf(g[2]);
    float nx = (wx - g[0]) / r, ny = (wy - g[1]) / r;
    if (nx * nx + ny * ny >= 1.0f) return base;
    float lat = asinf(clampf(ny, -1, 1));
    float lon = asinf(clampf(nx / maxf(cosf(lat), 0.0001f), -1, 1));
    int dw = tx->globe.w, dh = tx->globe.h;
    int vy = (int)((lat / 3.14159265358979f + 0.5f) * dh);
    vy = vy < 0 ? 0 : vy > dh - 1 ? dh - 1 : vy;
    int uD = ((int)(fractf(lon / 6.28318530717959f + 0.5f - spin) * dw)) % dw;
    const uint8_t *p = tx->globe.p + ((size_t)vy * dw + uD) * 4;
    if (g[2] < 0) return V3(p[1] / 255.0f, p[2] / 255.0f, p[3] / 255.0f);
    int uL = (int)((lon / 6.28318530717959f + 0.5f) * dw);
    uL = uL < 0 ? 0 : uL > dw - 1 ? dw - 1 : uL;
    const uint8_t *q = tx->globe.p + ((size_t)vy * dw + uL) * 4;
    float detail = p[0] / 255.0f * 4.0f;
    return clamp3(V3(q[1] / 255.0f * detail, q[2] / 255.0f * detail, q[3] / 255.0f * detail));
}
v3 st_arcade_ambient_(v3 base, float wx, float wy, float t, const st_frame_params_t *fp, const st_textures_t *tx);
v3 st_arcade_ambient_(v3 base, float wx, float wy, float t, const st_frame_params_t *fp, const st_textures_t *tx) {
    float hi = max3(base);
    float lit = clampf((hi - 0.16f) * 3.0f, 0, 1);
    float horizon = fp->horizon;
    float rear = stepf(wx, 768.0f - 1.0f), nearm = 1.0f - rear;
    // 1 grid
    float dy = maxf(wy - horizon, 1.0f);
    float gp = hump(fractf(powf(dy, 0.62f) / 12.0f - t / 90.0f));
    float gp2 = gp * gp, gp4 = gp2 * gp2, band = gp4 * gp4 * gp2;
    float floor_mask = rear * stepf(horizon + 2.0f, wy) * smoothstepf(horizon + 4.0f, horizon + 70.0f, wy);
    float grid_gain = floor_mask * band * (0.95f * lit + 0.10f);
    // 2 stars
    float h = fx_hash(floorf(wx * 0.1f), floorf(wy * 0.1f));
    float gx = wx - tx->globe_params[0], gy = wy - tx->globe_params[1], gg = gx * gx + gy * gy;
    float sky = rear * stepf(wy, horizon - 330.0f);
    float star = sky * stepf(0.42f, hi) * stepf(20000.0f, gg) * stepf(h, 0.55f);
    float k = h / 0.55f;
    float tw = wave1(t / ((1.2f + 2.2f * fractf(k * 7.13f)) * 60.0f) + fractf(k * 13.7f));
    float flash = powf(maxf(wave1(t / ((7.0f + 9.0f * fractf(k * 3.7f)) * 60.0f) + fractf(k * 5.1f)), 0.0f), 14.0f);
    float star_gain = star * ((0.25f + 0.35f * k) * tw + 1.2f * flash * stepf(k, 0.3f));
    // 3 city
    float city = rear * stepf(horizon - 540.0f, wy) * stepf(wy, horizon + 6.0f) * lit;
    float cp = hump(fractf((horizon - wy) / 520.0f - t / 200.0f));
    float cp2 = cp * cp, cp4 = cp2 * cp2;
    float city_gain = city * (0.10f * sinf(t * 0.020944f) + 0.85f * cp4 * cp4 * cp4 * cp4);
    // 4 near pillars
    float gold = nearm * clampf((base.r - base.b - 0.20f) * 3.0f, 0, 1) * stepf(base.b, base.g) * stepf(0.35f, hi);
    float gl = hump(fractf(t / 300.0f + wy * 0.0009f + wx * 0.0004f)), gl2 = gl * gl, gl4 = gl2 * gl2;
    float cyan = clampf((minf(base.g, base.b) - base.r - 0.12f) * 3.333f, 0, 1);
    float sn = hump(fractf(t * 0.0020833f + wy * 0.0011111f)), sn2 = sn * sn, sn4 = sn2 * sn2;
    float near_gain = gold * 0.9f * gl4 * gl4 * gl4 + nearm * 0.22f * sn4 * sn4 * sn2 * cyan;
    // 5 shooting star
    float epoch = floorf(t / 450.0f), lt = t - epoch * 450.0f;
    float h1 = fx_hash(epoch, 3.0f), h2 = fx_hash(epoch, 7.0f), h3 = fx_hash(epoch, 11.0f);
    float dxr = h3 > 0.5f ? 1.0f : -1.0f, dyr = 0.42f + 0.3f * h2, dl = sqrtf(dxr * dxr + dyr * dyr);
    dxr /= dl; dyr /= dl;
    float headx = 80.0f + 608.0f * h1 + dxr * 14.0f * lt, heady = 120.0f + 900.0f * h2 + dyr * 14.0f * lt;
    float rx = wx - headx, ry = wy - heady;
    float along = -(rx * dxr + ry * dyr), perp = fabsf(rx * dyr - ry * dxr);
    float tail = 1.0f - clampf(along / 120.0f, 0, 1);
    float streak = sky * stepf(14000.0f, gg) * stepf(fx_hash(epoch, 1.0f), 0.7f) * stepf(0.0f, along) * tail * tail *
                   (1.0f - smoothstepf(0.6f, 2.4f, perp)) * smoothstepf(0.0f, 6.0f, lt) * (1.0f - smoothstepf(38.0f, 50.0f, lt));
    float m = fp->motion, gain = 1.0f + m * (grid_gain + star_gain + city_gain + near_gain);
    return V3(base.r * gain + m * streak * 1.4f * 0.85f, base.g * gain + m * streak * 1.4f * 0.92f, base.b * gain + m * streak * 1.4f);
}

// ---- the ambience, decomposed (see struthio_raster.h) ------------------------------------
void st_amb_texel(const float rgb[3], float wx, float wy, const st_frame_params_t *fp, const st_textures_t *tx, st_amb_texel_t *o) {
    v3 base = V3(rgb[0], rgb[1], rgb[2]);
    float hi = max3(base);
    o->lit = clampf((hi - 0.16f) * 3.0f, 0, 1);
    o->rear = stepf(wx, 768.0f - 1.0f) > 0;
    float horizon = fp->horizon;
    float h = fx_hash(floorf(wx * 0.1f), floorf(wy * 0.1f));
    float gx = wx - tx->globe_params[0], gy = wy - tx->globe_params[1], gg = gx * gx + gy * gy;
    float sky = (o->rear ? 1.0f : 0.0f) * stepf(wy, horizon - 330.0f);
    o->star = sky * stepf(0.42f, hi) * stepf(20000.0f, gg) * stepf(h, 0.55f) > 0;
    o->star_k = h / 0.55f;
    o->star_w = o->star ? 1.0f : 0.0f;
    float nearm = o->rear ? 0.0f : 1.0f;
    o->gold = nearm * clampf((base.r - base.b - 0.20f) * 3.0f, 0, 1) * stepf(base.b, base.g) * stepf(0.35f, hi);
    o->cyan = clampf((minf(base.g, base.b) - base.r - 0.12f) * 3.333f, 0, 1);
}
static float star_term(float k, float t) {
    float tw = wave1(t / ((1.2f + 2.2f * fractf(k * 7.13f)) * 60.0f) + fractf(k * 13.7f));
    float flash = powf(maxf(wave1(t / ((7.0f + 9.0f * fractf(k * 3.7f)) * 60.0f) + fractf(k * 5.1f)), 0.0f), 14.0f);
    return (0.25f + 0.35f * k) * tw + 1.2f * flash * stepf(k, 0.3f);
}
void st_amb_frame(st_amb_frame_t *af, const st_frame_params_t *fp, const st_textures_t *tx) {
    float t = fp->ambient_tick;
    af->t = t; af->m = fp->motion; af->horizon = fp->horizon; af->gx = tx->globe_params[0]; af->gy = tx->globe_params[1];
    float epoch = floorf(t / 450.0f), lt = t - epoch * 450.0f;
    float h1 = fx_hash(epoch, 3.0f), h2 = fx_hash(epoch, 7.0f), h3 = fx_hash(epoch, 11.0f);
    float dxr = h3 > 0.5f ? 1.0f : -1.0f, dyr = 0.42f + 0.3f * h2, dl = sqrtf(dxr * dxr + dyr * dyr);
    af->dx = dxr / dl; af->dy = dyr / dl; af->lt = lt;
    af->hx = 80.0f + 608.0f * h1 + af->dx * 14.0f * lt; af->hy = 120.0f + 900.0f * h2 + af->dy * 14.0f * lt;
    af->streak_on = stepf(fx_hash(epoch, 1.0f), 0.7f) > 0 && lt < 50.0f;
    af->gl_phase_t = t / 300.0f;
}
void st_amb_row(const st_amb_frame_t *af, float wy, bool rear, st_amb_row_t *o) {
    float t = af->t, horizon = af->horizon, r = rear ? 1.0f : 0.0f;
    float dy = maxf(wy - horizon, 1.0f);
    float gp = hump(fractf(powf(dy, 0.62f) / 12.0f - t / 90.0f));
    float gp2 = gp * gp, gp4 = gp2 * gp2, band = gp4 * gp4 * gp2;
    o->grid = r * stepf(horizon + 2.0f, wy) * smoothstepf(horizon + 4.0f, horizon + 70.0f, wy) * band;
    float cp = hump(fractf((horizon - wy) / 520.0f - t / 200.0f)), cp2 = cp * cp, cp4 = cp2 * cp2;
    o->city = r * stepf(horizon - 540.0f, wy) * stepf(wy, horizon + 6.0f) * (0.10f * sinf(t * 0.020944f) + 0.85f * cp4 * cp4 * cp4 * cp4);
    float sn = hump(fractf(t * 0.0020833f + wy * 0.0011111f)), sn2 = sn * sn, sn4 = sn2 * sn2;
    o->sn10 = (1.0f - r) * 0.22f * sn4 * sn4 * sn2;
}
float st_hump12(float x) { float gl = hump(fractf(x)), gl2 = gl * gl, gl4 = gl2 * gl2; return gl4 * gl4 * gl4; }
float st_amb_streak(const st_amb_frame_t *af, float wx, float wy) {
    if (!af->streak_on || wx > 767.0f || wy > af->horizon - 330.0f) return 0;
    float gx = wx - af->gx, gy = wy - af->gy;
    if (gx * gx + gy * gy < 14000.0f) return 0;
    float rx = wx - af->hx, ry = wy - af->hy;
    float along = -(rx * af->dx + ry * af->dy), perp = fabsf(rx * af->dy - ry * af->dx);
    if (along < 0.0f) return 0;
    float tail = 1.0f - clampf(along / 120.0f, 0, 1);
    return tail * tail * (1.0f - smoothstepf(0.6f, 2.4f, perp)) * smoothstepf(0.0f, 6.0f, af->lt) * (1.0f - smoothstepf(38.0f, 50.0f, af->lt));
}
float st_amb_gain(const st_amb_frame_t *af, const st_amb_row_t *row, const st_amb_texel_t *x, float wx, float wy, float *streak) {
    float grid = row->grid * (0.95f * x->lit + 0.10f);
    // stars: the twinkle period depends steeply on the star's hash, so it is
    // recomputed exactly for star texels (a few per cent of the sky)
    float star = 0.0f;
    if (x->star) star = x->star_w * star_term(fx_hash(floorf(wx * 0.1f), floorf(wy * 0.1f)) / 0.55f, af->t);
    float city = row->city * x->lit;
    float nearg = x->gold > 0 ? x->gold * 0.9f * st_hump12(af->gl_phase_t + wy * 0.0009f + wx * 0.0004f) : 0.0f;
    nearg += row->sn10 * x->cyan;
    *streak = af->m * st_amb_streak(af, wx, wy) * 1.4f;
    return 1.0f + af->m * (grid + star + city + nearg);
}

// ---- the sprite pass -----------------------------------------------------------------------------
void st_frame_params_default(st_frame_params_t *p, int32_t render_tick, double moon_phase, double impact) {
    memset(p, 0, sizeof *p);
    p->tick = (float)render_tick; p->ambient_tick = (float)render_tick; p->moon_phase = (float)moon_phase;
    p->beat = 0; p->motion = 1; p->cyan = 1.02f; p->lava = 1.02f; p->violet = 0.96f; p->impact = (float)impact;
    p->bloom_beat = 0; p->quality = 2; p->horizon = 1682.0f;
}
// Nearest sampling as the GPU does it: the varying is the normalised uv
// (texel / size, interpolated in float); the sampler scales back by the size.
static inline const uint8_t *texel_uv(const st_rgba_t *t, float u, float v) {
    int ix = (int)floorf(u * (float)t->w), iy = (int)floorf(v * (float)t->h);
    ix = ix < 0 ? 0 : ix >= t->w ? t->w - 1 : ix;
    iy = iy < 0 ? 0 : iy >= t->h ? t->h - 1 : iy;
    return t->p + ((size_t)iy * t->w + ix) * 4;
}
static inline uint8_t u8(float v) { v = clampf(v, 0, 1); return (uint8_t)(v * 255.0f + 0.5f); }

void st_grid_init(st_grid_t *g, int w, int h, int vw, int vh, int16_t *vx, int16_t *vy, int16_t *ox, int16_t *oy) {
    g->w = w; g->h = h; g->vw = vw; g->vh = vh; g->vx = vx; g->vy = vy; g->ox = ox; g->oy = oy;
    // the browser's nearest scaling: output pixel centre -> canvas pixel
    for (int x = 0; x < w; x++) { int v = (int)floor((x + 0.5) * vw / w); vx[x] = (int16_t)(v < vw ? v : vw - 1); }
    for (int y = 0; y < h; y++) { int v = (int)floor((y + 0.5) * vh / h); vy[y] = (int16_t)(v < vh ? v : vh - 1); }
    for (int v = 0; v < vw; v++) { int x = (int)floor((v + 0.5) * w / vw); ox[v] = (int16_t)(x < w ? x : w - 1); }
    for (int v = 0; v < vh; v++) { int y = (int)floor((v + 0.5) * h / vh); oy[v] = (int16_t)(y < h ? y : h - 1); }
}
// first output index whose canvas centre is >= edge (vx is non-decreasing)
static int first_at_or_after(const int16_t *map, int n, float edge) {
    int lo = 0, hi = n;
    while (lo < hi) { int mid = (lo + hi) / 2; if ((float)map[mid] + 0.5f >= edge) hi = mid; else lo = mid + 1; }
    return lo;
}
void st_raster_scene(uint8_t *scene, float *depth, const st_grid_t *g, const st_quads_t *q, const st_textures_t *tx, const st_frame_params_t *fp) {
    const int W = g->w, H = g->h, VW = g->vw, VH = g->vh;
    // clear: [0.027, 0.075, 0.122, 1], depth 1
    const uint8_t clear[4] = {u8(0.027f), u8(0.075f), u8(0.122f), 255};
    for (int i = 0; i < W * H; i++) { memcpy(scene + (size_t)i * 4, clear, 4); depth[i] = 1.0f; }
    const float spin = fractf(fp->moon_phase);
    for (int n = 0; n < q->n; n++) {
        const st_quad_t *it = &q->q[n];
        // setInstances: float32 instance data, src width/height reduced by one texel
        float dx = (float)it->x, dy = (float)it->y, dw = (float)it->w, dh = (float)it->h;
        float ssx, ssw;
        if (it->sw >= 0) { ssx = (float)it->sx; ssw = it->sw > 1 ? (float)(it->sw - 1) : 0.0f; }
        else { ssx = (float)(it->sx - 1); ssw = (float)(it->sw + 1); }
        float ssy = (float)it->sy, ssh = it->sh > 1 ? (float)(it->sh - 1) : 0.0f;
        float z = clampf((float)it->z, 0, 1);
        int mat = it->flags;
        // canvas-space rect via NDC like the vertex shader
        float x0 = ((dx / 256.0f * 2.0f - 1.0f) + 1.0f) * 0.5f * VW, x1 = (((dx + dw) / 256.0f * 2.0f - 1.0f) + 1.0f) * 0.5f * VW;
        float y0 = (1.0f - (1.0f - dy / 384.0f * 2.0f)) * 0.5f * VH, y1 = (1.0f - (1.0f - (dy + dh) / 384.0f * 2.0f)) * 0.5f * VH;
        if (x1 < x0) { float t = x0; x0 = x1; x1 = t; }
        if (y1 < y0) { float t = y0; y0 = y1; y1 = t; }
        int px0 = first_at_or_after(g->vx, W, x0), px1 = first_at_or_after(g->vx, W, x1);
        int py0 = first_at_or_after(g->vy, H, y0), py1 = first_at_or_after(g->vy, H, y1);
        if (px0 >= px1 || py0 >= py1) continue;
        float inv_w = 1.0f / (x1 - x0), inv_h = 1.0f / (y1 - y0);
        const st_rgba_t *tt = mat == ST_MAT_WORLD ? &tx->world : ((mat >= 2 && mat <= 7) || mat == ST_MAT_PLAYER) ? &tx->bird : &tx->atlas;
        const float itw = 1.0f / (float)tt->w, ith = 1.0f / (float)tt->h;
        // per-corner normalised uv, as the vertex shader writes it
        const float ua = (ssx + 0.5f) * itw, ub = (ssx + ssw + 0.5f) * itw;
        const float va = (ssy + 0.5f) * ith, vb = (ssy + ssh + 0.5f) * ith;
        for (int py = py0; py < py1; py++) {
            float cy = (float)g->vy[py] + 0.5f;
            float v = (cy - y0) * inv_h;
            float vv = va + (vb - va) * v;
            for (int px = px0; px < px1; px++) {
                float *dp = &depth[(size_t)py * W + px];
                if (!(z <= *dp)) continue;
                float u = (((float)g->vx[px] + 0.5f) - x0) * inv_w;
                float uu = ua + (ub - ua) * u;
                const uint8_t *s = texel_uv(tt, uu, vv);
                float c[4];
                if (mat == ST_MAT_WORLD) {
                    v3 w = V3(s[0] / 255.0f, s[1] / 255.0f, s[2] / 255.0f);
                    float wx = uu * (float)tt->w, wy = vv * (float)tt->h;
                    w = st_globe_surface_(w, wx, wy, tx, spin);
                    w = st_arcade_ambient_(w, wx, wy, fp->ambient_tick, fp, tx);
                    c[0] = w.r; c[1] = w.g; c[2] = w.b; c[3] = s[3] / 255.0f;
                } else if ((mat >= 2 && mat <= 7) || mat == ST_MAT_PLAYER) {
                    float in[3] = {s[0] / 255.0f, s[1] / 255.0f, s[2] / 255.0f};
                    float phase = fp->ambient_tick * BLUE_CYCLE_RATE + cy * BLUE_CYCLE_TRAVEL;
                    st_bird_ink(in, mat == ST_MAT_PLAYER ? 6 : mat - 2, phase, 1.0f, c);
                    c[3] = s[3] / 255.0f;
                } else if (mat == ST_MAT_ISLAND) {
                    v3 o = arcade_island(V3(s[0] / 255.0f, s[1] / 255.0f, s[2] / 255.0f), fp->ambient_tick, fp);
                    c[0] = o.r; c[1] = o.g; c[2] = o.b; c[3] = s[3] / 255.0f;
                } else {
                    c[0] = s[0] / 255.0f; c[1] = s[1] / 255.0f; c[2] = s[2] / 255.0f; c[3] = s[3] / 255.0f;
                }
                if (c[3] < 0.0039215686f) continue;
                *dp = z;
                uint8_t *d = scene + ((size_t)py * W + px) * 4;
                float ia = 1.0f - c[3];
                d[0] = u8(c[0] * c[3] + d[0] / 255.0f * ia);
                d[1] = u8(c[1] * c[3] + d[1] / 255.0f * ia);
                d[2] = u8(c[2] * c[3] + d[2] / 255.0f * ia);
                d[3] = u8(c[3] + d[3] / 255.0f * ia);
            }
        }
    }
}

// ---- the post pass ---------------------------------------------------------------------------------
static v3 emission(v3 c, v3 pulse) {
    float hi = max3(c);
    float cyan = (c.b > 0.34f && c.g > 0.27f && c.b > c.r * 1.20f ? hi : 0.0f) * 0.3f;
    float lava = c.r > 0.42f && c.g < 0.48f && c.r > c.g * 1.25f && c.r > c.b * 1.45f ? hi : 0.0f;
    float violet = c.b > 0.35f && c.r > 0.35f && c.g < c.r * 0.78f ? hi : 0.0f;
    return scale3(c, cyan * pulse.r + lava * pulse.g + violet * pulse.b);
}
void st_grade_arcade(const float in[3], float out[3]) {
    float r = in[0], g = in[1], b = in[2];
    float mx = maxf(r, maxf(g, b)), d = mx - minf(r, minf(g, b)), h = 0.0f;
    if (d > 0.00001f) {
        if (mx == r) { h = (g - b) / d; if (h < 0.0f) h += 6.0f; }
        else if (mx == g) h = (b - r) / d + 2.0f;
        else h = (r - g) / d + 4.0f;
    }
    float qx = h * 60.0f, qy = mx > 0.00001f ? d / mx : 0.0f, qz = mx;
    float w = smoothstepf(160.0f, 178.0f, qx) * (1.0f - smoothstepf(228.0f, 245.0f, qx)) * smoothstepf(0.10f, 0.25f, qy);
    qx = mixf(qx, 218.0f, w * 0.85f);
    qy = qy * (1.0f - 0.30f * w) * 0.94f;
    qz = qz * (1.0f - 0.12f * w);
    v3 o = hsv_pick(qz, qy, qx);
    out[0] = o.r; out[1] = o.g; out[2] = o.b;
}
static void tone_raw(const float in[3], float out[3]) {
    for (int i = 0; i < 3; i++) { float x = in[i] * 1.8f; out[i] = x * (1.0f + x / (1.6f * 1.6f)) / (1.0f + x); }
}
void st_tone(const float in[3], float out[3]) {
    tone_raw(in, out);
    for (int i = 0; i < 3; i++) out[i] = clampf(out[i], 0, 1);
}
static v3 pulse_at(const st_frame_params_t *fp, float t, int x, int y) {
    return V3(fp->cyan * (0.84f + 0.16f * sinf(t + (float)(x + y) * 0.018f)), fp->lava * (0.82f + 0.18f * sinf(t * 0.73f + (float)y * 0.025f)),
              fp->violet * (0.84f + 0.16f * sinf(t * 1.13f)));
}
static v3 bilinear(const float *img, int w, int h, float u, float v) {     // u, v normalised, clamp to edge
    float x = u * w - 0.5f, y = v * h - 0.5f;
    int x0 = (int)floorf(x), y0 = (int)floorf(y);
    float fx = x - x0, fy = y - y0;
    v3 acc = V3(0, 0, 0);
    for (int j = 0; j < 2; j++) for (int i = 0; i < 2; i++) {
        int xi = x0 + i, yi = y0 + j;
        xi = xi < 0 ? 0 : xi >= w ? w - 1 : xi;
        yi = yi < 0 ? 0 : yi >= h ? h - 1 : yi;
        float wt = (i ? fx : 1 - fx) * (j ? fy : 1 - fy);
        const float *p = img + ((size_t)yi * w + xi) * 3;
        acc.r += p[0] * wt; acc.g += p[1] * wt; acc.b += p[2] * wt;
    }
    return acc;
}
// The scene as the post pass sees it: canvas pixel (cx, cy) -> the output
// pixel that shows it (identity at full size), clamped like textureLoad.
static inline v3 load_canvas(const uint8_t *s, const st_grid_t *g, int cx, int cy) {
    cx = cx < 0 ? 0 : cx >= g->vw ? g->vw - 1 : cx;
    cy = cy < 0 ? 0 : cy >= g->vh ? g->vh - 1 : cy;
    const uint8_t *p = s + ((size_t)g->oy[cy] * g->w + g->ox[cx]) * 4;
    return V3(p[0] / 255.0f, p[1] / 255.0f, p[2] / 255.0f);
}
void st_raster_post(const uint8_t *scene, uint8_t *out, const st_grid_t *g, const st_frame_params_t *fp, float *scratch) {
    const int W = g->w, H = g->h, VW = g->vw, VH = g->vh;
    uint32_t tk = (uint32_t)fp->ambient_tick;
    float t = (float)(tk & 511u) * 0.012271846f;
    int bw = (VW + 3) / 4, bh = (VH + 3) / 4;
    float *emit = scratch, *glow = scratch + (size_t)bw * bh * 3;
    if (fp->quality > 1) {
        for (int ey = 0; ey < bh; ey++) for (int ex = 0; ex < bw; ex++) {
            int bx = ex * 4, by = ey * 4;
            v3 pulse = pulse_at(fp, t, bx + 2, by + 2);
            v3 e = V3(0, 0, 0);
            for (int y = 0; y < 4; y++) for (int x = 0; x < 4; x++) {
                int sx = bx + x < VW - 1 ? bx + x : VW - 1, sy = by + y < VH - 1 ? by + y : VH - 1;
                v3 c = load_canvas(scene, g, sx, sy);
                float L = c.r * 0.2126f + c.g * 0.7152f + c.b * 0.0722f;
                v3 em = emission(c, pulse);
                float k = smoothstepf(0.40f, 0.90f, L) * 1.0f * (0.85f + 0.15f * pulse.r);
                e.r += em.r + c.r * k; e.g += em.g + c.g * k; e.b += em.b + c.b * k;
            }
            float *o = emit + ((size_t)ey * bw + ex) * 3;
            o[0] = e.r * 0.0625f; o[1] = e.g * 0.0625f; o[2] = e.b * 0.0625f;
        }
        for (int gy = 0; gy < bh; gy++) for (int gx = 0; gx < bw; gx++) {
            float u = (gx + 0.5f) / bw, v = (gy + 0.5f) / bh, pu = 1.0f / bw, pv = 1.0f / bh;
#define TAP(ox_, oy_) bilinear(emit, bw, bh, u + (ox_) * pu, v + (oy_) * pv)
            v3 gsum = V3(0, 0, 0), s;
            const float rad[4] = {1.5f, 3.75f, 8.25f, 16.0f}, wt[4] = {0.028f, 0.014f, 0.007f, 0.0045f};
            for (int k = 0; k < 4; k++) {
                float r = rad[k];
                v3 a = TAP(r, 0), b = TAP(-r, 0), c = TAP(0, r), d = TAP(0, -r);
                gsum.r += (a.r + b.r + c.r + d.r) * wt[k]; gsum.g += (a.g + b.g + c.g + d.g) * wt[k]; gsum.b += (a.b + b.b + c.b + d.b) * wt[k];
            }
            const float dg[2] = {1.25f, 11.3f}, dwt[2] = {0.022f, 0.0045f};
            for (int k = 0; k < 2; k++) {
                float r = dg[k];
                v3 a = TAP(r, r), b = TAP(-r, r), c = TAP(r, -r), d = TAP(-r, -r);
                s = V3(a.r + b.r + c.r + d.r, a.g + b.g + c.g + d.g, a.b + b.b + c.b + d.b);
                gsum.r += s.r * dwt[k]; gsum.g += s.g * dwt[k]; gsum.b += s.b * dwt[k];
            }
#undef TAP
            float *o = glow + ((size_t)gy * bw + gx) * 3;
            o[0] = gsum.r; o[1] = gsum.g; o[2] = gsum.b;
        }
    }
    int scale = (int)floorf((float)VH / 384.0f + 0.5f);
    if (scale < 1) scale = 1;
    for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) {
        int cx = g->vx[x], cy = g->vy[y];
        const uint8_t *src = scene + ((size_t)y * W + x) * 4;
        uint8_t *o = out + ((size_t)y * W + x) * 4;
        v3 c = V3(src[0] / 255.0f, src[1] / 255.0f, src[2] / 255.0f);
        float rgb[3];
        if (fp->quality == 0) {
            float in[3] = {c.r, c.g, c.b}, tn[3];
            st_tone(in, tn);
            st_grade_arcade(tn, rgb);
        } else {
            v3 pulse = pulse_at(fp, t, cx, cy);
            v3 a = emission(load_canvas(scene, g, cx + 2, cy), pulse), b = emission(load_canvas(scene, g, cx - 2, cy), pulse);
            v3 cc = emission(load_canvas(scene, g, cx, cy + 2), pulse), d = emission(load_canvas(scene, g, cx, cy - 2), pulse);
            v3 glw = V3((a.r + b.r + cc.r + d.r) * 0.068f, (a.g + b.g + cc.g + d.g) * 0.068f, (a.b + b.b + cc.b + d.b) * 0.068f);
            float u = (cx + 0.5f) / VW, v = (cy + 0.5f) / VH;
            if (fp->quality > 1) {
                v3 gl = bilinear(glow, bw, bh, u, v);
                glw.r += gl.r * 1.8f; glw.g += gl.g * 1.8f; glw.b += gl.b * 1.8f;
            }
            v3 em = emission(c, pulse);
            float k = 0.10f + fp->impact * 0.10f;
            glw.r += em.r * k; glw.g += em.g * k; glw.b += em.b * k;
            if (fp->quality <= 1) { glw.r += em.r * 0.35f; glw.g += em.g * 0.35f; glw.b += em.b * 0.35f; }
            glw = scale3(glw, 1.0f + 0.6f * fp->bloom_beat);
            float scan = (cy % scale) == scale - 1 ? 0.93f : 1.0f;
            float cu = u * 2.0f - 1.0f, cv = v * 2.0f - 1.0f;
            float vignette = 1.0f - 0.10f * smoothstepf(0.38f, 1.12f, cu * cu + cv * cv);
            float in[3] = {c.r + glw.r, c.g + glw.g, c.b + glw.b}, tn[3];
            tone_raw(in, tn);
            for (int i = 0; i < 3; i++) tn[i] = clampf(tn[i] * scan * vignette, 0, 1);
            st_grade_arcade(tn, rgb);
        }
        o[0] = u8(rgb[0]); o[1] = u8(rgb[1]); o[2] = u8(rgb[2]); o[3] = src[3];
    }
}

// test hook: the undecomposed ambience alone (no globe)
float st_world_test_(const float in[3], float wx, float wy, const st_textures_t *tx, const st_frame_params_t *fp, float out[3]);
float st_world_test_(const float in[3], float wx, float wy, const st_textures_t *tx, const st_frame_params_t *fp, float out[3]) {
    v3 w = st_arcade_ambient_(V3(in[0], in[1], in[2]), wx, wy, fp->ambient_tick, fp, tx);
    out[0] = w.r; out[1] = w.g; out[2] = w.b;
    return 0;
}
