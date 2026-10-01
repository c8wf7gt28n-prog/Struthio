// STRUTHIO HANDHELD · asset pack loader: points the panel renderer's
// textures and HUD layers into a mapped pack (no copies).
#include "struthio_pak.h"
#include <stdio.h>
#include <string.h>

static uint32_t rd32(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }

const st_pak_entry_t *st_pak_find(const uint8_t *pak, const char *name) {
    if (!pak || memcmp(pak, "STRPAK01", 8)) return NULL;
    uint32_t n = rd32(pak + 8);
    const st_pak_entry_t *e = (const st_pak_entry_t *)(pak + 12);
    for (uint32_t i = 0; i < n; i++)
        if (!strncmp(e[i].name, name, sizeof e[i].name)) return &e[i];
    return NULL;
}

// which HUD slot a layer name fills (names from tools/reference/hud_capture.mjs)
static st_hud_layer_t *hud_slot(st_hud_assets_t *hud, const char *n) {
    int a, b, c;
    char v;
    if (sscanf(n, "score_%d_%d", &a, &b) == 2) return a >= 0 && a < 6 && b >= 0 && b < 10 ? &hud->score[a][b] : NULL;
    if (sscanf(n, "round_%d_%d", &a, &b) == 2) return a >= 0 && a < 2 && b >= 0 && b < 10 ? &hud->round[a][b] : NULL;
    if (sscanf(n, "kills2_%c_%d_%d", &v, &b, &c) == 3) return (v == 'a' || v == 'b') && b >= 0 && b < 2 && c >= 0 && c < 10 ? &hud->kills2[v - 'a'][b][c] : NULL;
    if (sscanf(n, "kills3_%c_%d_%d", &v, &b, &c) == 3) return (v == 'a' || v == 'b') && b >= 0 && b < 3 && c >= 0 && c < 10 ? &hud->kills3[v - 'a'][b][c] : NULL;
    if (sscanf(n, "swords_%c_%d", &v, &a) == 2) return v == 'a' || v == 'b' ? &hud->swords[v - 'a'][a == 3] : NULL;
    if (!strncmp(n, "ring_", 5) && (n[5] == 'a' || n[5] == 'b') && strstr(n, "_due")) return &hud->ring[n[5] - 'a'][7];
    if (sscanf(n, "ring_%c_%d", &v, &a) == 2) return (v == 'a' || v == 'b') && a >= 0 && a < 7 ? &hud->ring[v - 'a'][a] : NULL;
    if (sscanf(n, "static_%c", &v) == 1) return v == 'a' || v == 'b' ? &hud->statics[v - 'a'] : NULL;
    if (sscanf(n, "joust_b_%d", &a) == 1) return a >= 0 && a < 12 ? &hud->joust_b[a] : NULL;
    if (sscanf(n, "joust_i_%d", &a) == 1) return a >= 0 && a < 12 ? &hud->joust_i[a] : NULL;
    if (!strcmp(n, "toast_extra")) return &hud->toast_extra;
    if (!strcmp(n, "toast_gold")) return &hud->toast_gold;
    if (!strcmp(n, "toast_paused")) return &hud->toast_paused;
    if (sscanf(n, "toast_clear_%d", &a) == 1) return a >= 0 && a < ST_HUD_ROUNDS ? &hud->toast_clear[a] : NULL;
    if (sscanf(n, "toast_clean_%d", &a) == 1) return a >= 0 && a < ST_HUD_ROUNDS ? &hud->toast_clean[a] : NULL;
    return NULL;
}

bool st_pak_open(const uint8_t *pak, size_t size, st_panel_textures_t *tx, st_hud_assets_t *hud, char *err, size_t cap) {
    if (size < 12 || memcmp(pak, "STRPAK01", 8)) { snprintf(err, cap, "not an asset pack"); return false; }
    uint32_t n = rd32(pak + 8);
    if (12 + (size_t)n * sizeof(st_pak_entry_t) > size) { snprintf(err, cap, "truncated directory"); return false; }
    const st_pak_entry_t *e = (const st_pak_entry_t *)(pak + 12);
    for (uint32_t i = 0; i < n; i++)
        if ((size_t)e[i].offset + e[i].size > size) { snprintf(err, cap, "entry %.24s out of range", e[i].name); return false; }
    static const char *const TEX[] = {"world_rear", "world_near", "bird_ink6", "bird_ink1", "bird_ink2", "bird_ink3", "atlas", "atlas_hi", "globe_map", "chrome"};
    st_tex_t *const dst[] = {&tx->world_rear, &tx->world_near, &tx->bird[0], &tx->bird[1], &tx->bird[2], &tx->bird[3], &tx->atlas, &tx->atlas_hi, &tx->globe_map, NULL};
    for (size_t k = 0; k < sizeof TEX / sizeof TEX[0]; k++) {
        const st_pak_entry_t *t = st_pak_find(pak, TEX[k]);
        if (!t) { snprintf(err, cap, "missing %s", TEX[k]); return false; }
        if (dst[k]) *dst[k] = (st_tex_t){t->w, t->h, t->format, pak + t->offset};
        else hud->chrome = pak + t->offset;
    }
    const st_pak_entry_t *lut = st_pak_find(pak, "globe_lut"), *gp = st_pak_find(pak, "globe_params");
    if (!lut || !gp || gp->size != sizeof tx->globe_params) { snprintf(err, cap, "missing the moon tables"); return false; }
    tx->globe_lut = (const uint16_t *)(const void *)(pak + lut->offset);
    tx->globe_x0 = lut->x; tx->globe_y0 = lut->y; tx->globe_w = lut->w; tx->globe_h = lut->h;
    memcpy(tx->globe_params, pak + gp->offset, sizeof tx->globe_params);
    int layers = 0;
    for (uint32_t i = 0; i < n; i++) {
        if (e[i].format != ST_HUD_RLE) continue;
        char name[25];
        memcpy(name, e[i].name, 24); name[24] = 0;
        st_hud_layer_t *l = hud_slot(hud, name);
        if (!l) continue;
        *l = (st_hud_layer_t){e[i].x, e[i].y, (int16_t)e[i].w, (int16_t)e[i].h, pak + e[i].offset, 1, NULL};
        layers++;
    }
    // layers coded against a base layer: the base's slot (its pixels are run-coded too,
    // so a copy run reads the base layer decoded alongside)
    for (uint32_t i = 0; i < n; i++) {
        unsigned b = e[i].pad[0] | e[i].pad[1] << 8;
        if (e[i].format != ST_HUD_RLE || !b) continue;
        if (b - 1 >= n) { snprintf(err, cap, "%.24s: bad base", e[i].name); return false; }
        char name[25], bname[25];
        memcpy(name, e[i].name, 24); name[24] = 0;
        memcpy(bname, e[b - 1].name, 24); bname[24] = 0;
        st_hud_layer_t *l = hud_slot(hud, name), *bl = hud_slot(hud, bname);
        if (l && bl) l->base = bl;
    }
    if (!layers) { snprintf(err, cap, "no HUD layers"); return false; }
    return true;
}
