/* ARC-1 Compact R08 -- microSD game library (HOST_TESTED). */
#include "game_lib.h"
#include "crc32.h"
#include <string.h>

static uint32_t le32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }
static void put32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24); }

/* header layout: 0 magic, 4 fmt u16 (1), 6 hdr_len u16 (128), 8 id[16], 24 title[48],
 * 72 min_fw, 76 payload_len, 80 payload_crc32, 84 flags, 88..123 reserved (0), 124 hdr_crc32 */
static int id_char_ok(char ch)
{
    return (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9') || ch == '_' || ch == '-';
}

int a1gp_parse(const uint8_t *h, size_t n, uint32_t fw_version, uint64_t file_size, a1gp_info *out)
{
    size_t i, idlen = 0, tlen = 0;
    a1gp_info inf;
    if (n < A1GP_HDR_LEN || file_size < A1GP_HDR_LEN) return A1GP_TRUNCATED;
    if (le32(h) != A1GP_MAGIC) return A1GP_BAD_MAGIC;
    if ((h[4] | (h[5] << 8)) != 1 || (h[6] | (h[7] << 8)) != A1GP_HDR_LEN) return A1GP_UNSUPPORTED_VERSION;
    if (arc1_crc32(0, h, 124) != le32(h + 124)) return A1GP_BAD_HDR_CRC;
    memset(&inf, 0, sizeof inf);
    while (idlen < 16 && h[8 + idlen]) idlen++;
    if (idlen == 0) return A1GP_BAD_FIELD;
    for (i = 0; i < 16; i++) {
        if (i < idlen) { if (!id_char_ok((char)h[8 + i])) return A1GP_BAD_FIELD; }
        else if (h[8 + i] != 0) return A1GP_BAD_FIELD;     /* NUL padding only */
    }
    while (tlen < 48 && h[24 + tlen]) tlen++;
    if (tlen == 48) return A1GP_BAD_FIELD;                /* must be NUL-terminated inside the field */
    for (i = 0; i < tlen; i++) if (h[24 + i] < 0x20 || h[24 + i] == 0x7F) return A1GP_BAD_FIELD;
    for (i = 88; i < 124; i++) if (h[i]) return A1GP_BAD_FIELD;
    memcpy(inf.game_id, h + 8, idlen);
    memcpy(inf.title, h + 24, tlen);
    inf.min_fw = le32(h + 72); inf.payload_len = le32(h + 76); inf.payload_crc32 = le32(h + 80); inf.flags = le32(h + 84);
    if (inf.flags != 0) return A1GP_BAD_FIELD;            /* no flags defined in format 1 */
    if (inf.min_fw > fw_version) return A1GP_NEEDS_NEWER_FW;
    if (inf.payload_len == 0 || (uint64_t)inf.payload_len + A1GP_HDR_LEN != file_size) return A1GP_BAD_PAYLOAD_LEN;
    if (out) *out = inf;
    return A1GP_OK;
}

void a1gp_build(uint8_t h[A1GP_HDR_LEN], const char *id, const char *title, uint32_t min_fw,
                uint32_t payload_len, uint32_t payload_crc32)
{
    size_t l;
    memset(h, 0, A1GP_HDR_LEN);
    put32(h, A1GP_MAGIC); h[4] = 1; h[6] = (uint8_t)A1GP_HDR_LEN;
    l = strlen(id); if (l > 16) l = 16; memcpy(h + 8, id, l);
    l = strlen(title); if (l > 47) l = 47; memcpy(h + 24, title, l);
    put32(h + 72, min_fw); put32(h + 76, payload_len); put32(h + 80, payload_crc32);
    put32(h + 124, arc1_crc32(0, h, 124));
}

static int has_suffix(const char *s, const char *suf)
{
    size_t a = strlen(s), b = strlen(suf);
    return a > b && strcmp(s + a - b, suf) == 0;
}

enum lib_card_state lib_scan(const lib_card_ops *c, uint32_t fw_version, lib_entry *e, unsigned max, unsigned *count)
{
    unsigned idx = 0;
    int m;
    *count = 0;
    if (!c->present(c->ctx)) return LIB_NO_CARD;
    m = c->mount(c->ctx);
    if (m == -1) return LIB_UNSUPPORTED_FS;
    if (m != 0) return LIB_IO_ERROR;
    for (;;) {
        char name[64];
        uint8_t h[A1GP_HDR_LEN];
        uint64_t sz = 0;
        int r;
        memset(name, 0, sizeof name);
        r = c->list(c->ctx, idx++, name, sizeof name - 1);
        if (r < 0) return LIB_IO_ERROR;
        if (r == 0) break;
        name[sizeof name - 1] = 0;
        if (!has_suffix(name, ".a1gp")) continue;
        if (*count >= max) break;
        memset(&e[*count], 0, sizeof e[*count]);
        memcpy(e[*count].file, name, sizeof name);
        if (c->size(c->ctx, name, &sz) != 0) { e[*count].status = A1GP_IO; (*count)++; continue; }
        r = c->read(c->ctx, name, 0, h, sizeof h);
        if (r < 0) { e[*count].status = A1GP_IO; (*count)++; continue; }
        e[*count].status = a1gp_parse(h, (size_t)r, fw_version, sz, &e[*count].info);
        (*count)++;
    }
    return LIB_CARD_OK;
}

int lib_verify_payload(const lib_card_ops *c, const lib_entry *e)
{
    uint8_t b[512];
    uint64_t off = 0;
    uint32_t crc = 0;
    if (e->status != A1GP_OK) return e->status;
    while (off < e->info.payload_len) {
        size_t want = (size_t)((e->info.payload_len - off) < sizeof b ? (e->info.payload_len - off) : sizeof b);
        int r = c->read(c->ctx, e->file, A1GP_HDR_LEN + off, b, want);
        if (r != (int)want) return A1GP_IO;
        crc = arc1_crc32(crc, b, want);
        off += want;
    }
    return crc == e->info.payload_crc32 ? A1GP_OK : A1GP_BAD_PAYLOAD_CRC;
}

/* save record: 0 magic, 4 seq, 8 len, 12 data_crc, 16 hdr_crc (over 0..15), 20.. data */
static void save_name(char *out, const char *game_id, int slot)
{
    size_t l = strlen(game_id);
    if (l > 16) l = 16;
    memcpy(out, "saves/", 6);
    memcpy(out + 6, game_id, l);
    memcpy(out + 6 + l, slot ? ".s1" : ".s0", 4);
}

static int read_slot(const lib_card_ops *c, const char *game_id, int slot, uint8_t *buf, uint32_t *len, uint32_t *seq)
{
    char nm[32];
    uint8_t h[20];
    uint32_t l;
    save_name(nm, game_id, slot);
    if (c->read(c->ctx, nm, 0, h, 20) != 20) return 0;
    if (le32(h) != SAVE_MAGIC || arc1_crc32(0, h, 16) != le32(h + 16)) return 0;
    l = le32(h + 8);
    if (l > SAVE_MAX) return 0;
    if (buf) {
        if (c->read(c->ctx, nm, 20, buf, l) != (int)l) return 0;
        if (arc1_crc32(0, buf, l) != le32(h + 12)) return 0;
    }
    *len = l; *seq = le32(h + 4);
    return 1;
}

static uint8_t g_save_tmp[SAVE_MAX];

int save_load(const lib_card_ops *c, const char *game_id, void *data, uint32_t cap, uint32_t *len, uint32_t *seq)
{
    uint32_t l[2] = { 0, 0 }, s[2] = { 0, 0 };
    int ok[2], best;
    if (!c->present(c->ctx)) return SAVE_NO_CARD;
    ok[0] = read_slot(c, game_id, 0, g_save_tmp, &l[0], &s[0]);
    ok[1] = read_slot(c, game_id, 1, g_save_tmp, &l[1], &s[1]);
    if (!ok[0] && !ok[1]) return SAVE_NONE;
    best = (ok[1] && (!ok[0] || s[1] > s[0])) ? 1 : 0;
    if (!read_slot(c, game_id, best, g_save_tmp, &l[best], &s[best])) return SAVE_IO;
    if (l[best] > cap) return SAVE_TOO_BIG;
    memcpy(data, g_save_tmp, l[best]);
    *len = l[best]; *seq = s[best];
    return SAVE_OK;
}

int save_commit(const lib_card_ops *c, const char *game_id, const void *data, uint32_t len)
{
    uint32_t l[2] = { 0, 0 }, s[2] = { 0, 0 }, ls, ss;
    int ok[2], target;
    char nm[32];
    uint8_t h[20];
    if (len > SAVE_MAX) return SAVE_TOO_BIG;
    if (!c->present(c->ctx)) return SAVE_NO_CARD;
    ok[0] = read_slot(c, game_id, 0, g_save_tmp, &l[0], &s[0]);
    ok[1] = read_slot(c, game_id, 1, g_save_tmp, &l[1], &s[1]);
    if (ok[0] && ok[1]) target = s[0] > s[1] ? 1 : 0;      /* overwrite the older */
    else if (ok[0]) target = 1;
    else target = 0;
    put32(h, SAVE_MAGIC);
    put32(h + 4, ((ok[0] && s[0] > s[1]) || !ok[1] ? s[0] : s[1]) + 1u);
    put32(h + 8, len);
    put32(h + 12, arc1_crc32(0, data, len));
    put32(h + 16, arc1_crc32(0, h, 16));
    save_name(nm, game_id, target);
    /* data first, header last: a torn write leaves an invalid header, never a
     * valid header over partial data (the data CRC catches the rest) */
    if (c->write(c->ctx, nm, 20, data, len) != (int)len) return SAVE_IO;
    if (c->write(c->ctx, nm, 0, h, 20) != 20) return SAVE_IO;
    if (!read_slot(c, game_id, target, g_save_tmp, &ls, &ss)) return SAVE_IO;
    if (ls != len || memcmp(g_save_tmp, data, len) != 0) return SAVE_IO;
    return SAVE_OK;
}
