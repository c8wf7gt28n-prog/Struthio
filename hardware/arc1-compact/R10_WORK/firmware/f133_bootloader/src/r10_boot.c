/* ARC-1 R10 -- F133 bootloader core (see include/r10_boot.h). HOST_TESTED only. */
#include "r10_boot.h"
#include "flash_layout.h"
#include "crc32.h"
#include <string.h>

static const uint8_t k_part[R10C_COUNT][3] = {           /* slot 0, slot 1, fallback (0xFF none) */
    { R10P_F1MA, R10P_F1MB, R10P_F1RC },
    { R10P_D2FA, R10P_D2FB, 0xFF },
    { R10P_C12A, R10P_C12G, 0xFF },
    { R10P_C45A, R10P_C45G, 0xFF },
};
static int is_fpga(enum r10_comp c) { return c == R10C_C12 || c == R10C_C45; }
static uint32_t fpga_idcode(enum r10_comp c) { return c == R10C_C12 ? R10_IDCODE_LFE5U_12 : ECP5_IDCODE_LFE5U_45; }

uint32_t r10_part_base(enum r10_comp c, int slot)
{
    if ((unsigned)c >= R10C_COUNT || slot < 0 || slot > 2 || k_part[c][slot] == 0xFF) return 0;
    return r10_parts[k_part[c][slot]].base;
}
uint32_t r10_part_len(enum r10_comp c, int slot)
{
    if ((unsigned)c >= R10C_COUNT || slot < 0 || slot > 2 || k_part[c][slot] == 0xFF) return 0;
    return r10_parts[k_part[c][slot]].len;
}

int r10_write_allowed(uint32_t addr, uint32_t n)
{
#ifdef MUTANT_BOOT_NO_LOCK
    (void)addr; (void)n; return 1;
#else
    unsigned i;
    if (n == 0) return 0;
    for (i = 0; i < R10P_COUNT; i++) {
        const r10_part_info *p = &r10_parts[i];
        if (addr >= p->base && (uint64_t)addr + n <= (uint64_t)p->base + p->len)
            return !p->locked && i != R10P_META;           /* META only through r10_manifest_store */
    }
    return 0;
#endif
}

int r10_layout_check(void)
{
    unsigned i;
    uint32_t next = 0;
    for (i = 0; i < R10P_COUNT; i++) {
        if (r10_parts[i].base != next || r10_parts[i].len == 0 || r10_parts[i].base % 0x10000u || r10_parts[i].len % 0x10000u)
            return -1;
        next += r10_parts[i].len;
    }
    if (next != R10_NOR_SIZE) return -2;
    if (r10_parts[R10P_F1BT].base + r10_parts[R10P_F1BT].len > 0x01000000u) return -3;   /* boot ROM: 3-byte window */
    if (R10_MF_COPY1 + 0x1000u > r10_parts[R10P_META].len) return -4;
    return 0;
}

/* ---------------- manifest ---------------- */
static void put32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }

void r10_manifest_default(r10_manifest *m)
{
    int i;
    memset(m, 0, sizeof *m);
    for (i = 0; i < R10C_COUNT; i++) m->c[i].trial = 0xFF;
}

static void mf_bytes(const r10_manifest *m, uint8_t b[R10_MF_SIZE])
{
    int i;
    memset(b, 0, R10_MF_SIZE);
    put32(b, R10_MF_MAGIC); b[4] = 1; b[5] = 0;
    put32(b + 8, m->generation);
    for (i = 0; i < R10C_COUNT; i++) {
        uint8_t *q = b + 12 + 12 * i;
        q[0] = m->c[i].active; q[1] = m->c[i].trial; q[2] = m->c[i].trials_left; q[3] = m->c[i].bad_mask;
        put32(q + 4, m->c[i].version[0]); put32(q + 8, m->c[i].version[1]);
    }
    put32(b + 60, arc1_crc32(0, b, 60));
}

static int mf_parse(const uint8_t b[R10_MF_SIZE], r10_manifest *m)
{
    int i;
    if (get32(b) != R10_MF_MAGIC || b[4] != 1 || get32(b + 60) != arc1_crc32(0, b, 60)) return -1;
    m->generation = get32(b + 8);
    for (i = 0; i < R10C_COUNT; i++) {
        const uint8_t *q = b + 12 + 12 * i;
        m->c[i].active = q[0] & 1u; m->c[i].trial = q[1]; m->c[i].trials_left = q[2]; m->c[i].bad_mask = q[3];
        m->c[i].version[0] = get32(q + 4); m->c[i].version[1] = get32(q + 8);
        if (m->c[i].trial != 0xFF && m->c[i].trial > 1) return -1;
    }
    return 0;
}

int r10_manifest_load(r10_boot *b, r10_manifest *m, int *copy)
{
    uint8_t raw[2][R10_MF_SIZE];
    r10_manifest t[2];
    int ok[2], k, best = -1;
    uint32_t meta = r10_parts[R10P_META].base;
    for (k = 0; k < 2; k++) {
        if (nor_read(b->nor, meta + (k ? R10_MF_COPY1 : 0u), raw[k], R10_MF_SIZE) != NOR_OK) return R10_E_NOR;
        ok[k] = mf_parse(raw[k], &t[k]) == 0;
    }
#ifdef MUTANT_BOOT_NO_GEN
    best = ok[0] ? 0 : (ok[1] ? 1 : -1);
#else
    for (k = 0; k < 2; k++)
        if (ok[k] && (best < 0 || t[k].generation > t[best].generation)) best = k;
#endif
    if (best < 0) r10_manifest_default(m); else *m = t[best];
    if (copy) *copy = best;
    return R10_OK;
}

int r10_manifest_store(r10_boot *b, r10_manifest *m)
{
    r10_manifest cur;
    uint8_t rec[R10_MF_SIZE];
    int newest, target;
    if (r10_manifest_load(b, &cur, &newest) != R10_OK) return R10_E_NOR;
#ifdef MUTANT_BOOT_SAME_COPY
    target = newest < 0 ? 0 : newest;
#else
    target = newest == 0 ? 1 : 0;                              /* never touch the newest valid record */
#endif
    m->generation = (newest < 0 ? m->generation : cur.generation) + 1u;
    mf_bytes(m, rec);
    if (nor_write_verified(b->nor, r10_parts[R10P_META].base + (target ? R10_MF_COPY1 : 0u), rec, R10_MF_SIZE) != NOR_OK)
        return R10_E_NOR;
    b->mf_writes++;
    return R10_OK;
}

/* ---------------- images ---------------- */
static int fpga_container_check(r10_boot *b, enum r10_comp c, int slot, ecp5_image *img, uint32_t *total)
{
    uint8_t hdr[ACFG_HDR], buf[1024];
    uint32_t base = r10_part_base(c, slot), len = r10_part_len(c, slot), bit_crc, crc = 0, off;
    ecp5_image tmp;
    if (!base) return R10_E_ARG;
    if (nor_read(b->nor, base, hdr, ACFG_HDR) != NOR_OK) return R10_E_NOR;
    if (ecp5_header_check(hdr, b->fpga_abi, &tmp, &bit_crc) != ECP5_OK) return R10_E_IMAGE;
    if (tmp.idcode != fpga_idcode(c) || (uint64_t)tmp.bit_len + ACFG_HDR > len) return R10_E_IMAGE;
    for (off = 0; off < tmp.bit_len; off += (uint32_t)sizeof buf) {
        uint32_t n = tmp.bit_len - off < sizeof buf ? tmp.bit_len - off : (uint32_t)sizeof buf;
        if (nor_read(b->nor, base + ACFG_HDR + off, buf, n) != NOR_OK) return R10_E_NOR;
        if (off == 0 && ecp5_bit_head_check(buf, n, tmp.idcode) != ECP5_OK) return R10_E_IMAGE;
        crc = arc1_crc32(crc, buf, n);
    }
    if (crc != bit_crc) return R10_E_IMAGE;
    if (img) *img = tmp;
    if (total) *total = tmp.bit_len + ACFG_HDR;
    return R10_OK;
}

int r10_slot_valid(r10_boot *b, enum r10_comp c, int slot)
{
    uint32_t base = r10_part_base(c, slot), len = r10_part_len(c, slot);
    if (!len) return 0;
    if (is_fpga(c)) return fpga_container_check(b, c, slot, NULL, NULL) == R10_OK;
    return fl_image_check(b->nor, base, len,
                          c == R10C_D213 ? R10_IMG_KIND_D213 : (slot == 2 ? R10_IMG_KIND_RESCUE : R10_IMG_KIND_F133),
                          NULL) == FL_IMG_OK;
}

int r10_select(r10_boot *b, enum r10_comp c, enum r10_slot *out)
{
    r10_manifest m;
    r10_comp_state *s;
    int valid[2], k, rc;
    if ((unsigned)c >= R10C_COUNT || !out) return R10_E_ARG;
    if ((rc = r10_manifest_load(b, &m, NULL)) != R10_OK) return rc;
    s = &m.c[c];
    for (k = 0; k < 2; k++) valid[k] = r10_slot_valid(b, c, k) && !(s->bad_mask & (1u << k));
    if (is_fpga(c)) {
        *out = valid[0] ? R10S_0 : (r10_slot_valid(b, c, 1) ? R10S_1 : R10S_NONE);  /* golden ignores bad marks */
        return R10_OK;
    }
    if (s->trial != 0xFF) {
        k = s->trial;
        if (valid[k] && s->trials_left > 0) {
#ifndef MUTANT_BOOT_NO_TRIAL_CONSUME
            s->trials_left--;                                  /* consume BEFORE jumping */
            if ((rc = r10_manifest_store(b, &m)) != R10_OK) return rc;
#endif
            *out = (enum r10_slot)k;
            return R10_OK;
        }
        s->bad_mask |= (uint8_t)(1u << k); s->trial = 0xFF; valid[k] = 0;
        if ((rc = r10_manifest_store(b, &m)) != R10_OK) return rc;
    }
    if (valid[s->active]) { *out = (enum r10_slot)s->active; return R10_OK; }
    k = 1 - s->active;
    if (valid[k]) {                                            /* unconfirmed other slot: run it as a trial */
        s->trial = (uint8_t)k; s->trials_left = R10_TRIALS - 1u;
        if ((rc = r10_manifest_store(b, &m)) != R10_OK) return rc;
        *out = (enum r10_slot)k;
        return R10_OK;
    }
    *out = (c == R10C_F133 && r10_slot_valid(b, c, 2)) ? R10S_FALLBACK : R10S_NONE;
    return R10_OK;
}

int r10_confirm(r10_boot *b, enum r10_comp c, enum r10_slot running)
{
    r10_manifest m;
    int rc;
    if ((unsigned)c >= R10C_COUNT || is_fpga(c) || running > R10S_1) return R10_E_ARG;
    if ((rc = r10_manifest_load(b, &m, NULL)) != R10_OK) return rc;
    if (m.c[c].trial != (uint8_t)running) return m.c[c].active == (uint8_t)running ? R10_OK : R10_E_STATE;
    m.c[c].active = (uint8_t)running; m.c[c].trial = 0xFF;
    return r10_manifest_store(b, &m);
}

int r10_fpga_stage(r10_boot *b, enum r10_comp c, int slot, ecp5_image *img)
{
    uint32_t total;
    int rc;
    if (!is_fpga(c) || slot < 0 || slot > 1 || !img) return R10_E_ARG;
    if ((rc = fpga_container_check(b, c, slot, NULL, &total)) != R10_OK) return rc;
    if (total > b->stage_cap) return R10_E_STAGE;
    if (nor_read(b->nor, r10_part_base(c, slot), b->stage, total) != NOR_OK) return R10_E_NOR;
    /* re-check the staged copy: the NOR may change between the two reads only through a fault */
    if (ecp5_image_check(b->stage, total, b->fpga_abi, img) != ECP5_OK || img->idcode != fpga_idcode(c)) return R10_E_IMAGE;
    return R10_OK;
}

int r10_boot_fpga12(r10_boot *b, ecp5_cfg *cfg, enum r10_slot *used, ecp5_err *last)
{
    r10_manifest m;
    ecp5_image img;
    int slot, rc;
    *used = R10S_NONE; *last = ECP5_OK;
    if ((rc = r10_manifest_load(b, &m, NULL)) != R10_OK) return rc;
    for (slot = 0; slot < 2; slot++) {
        if (slot == 0 && (m.c[R10C_C12].bad_mask & 1u)) continue;
        rc = r10_fpga_stage(b, R10C_C12, slot, &img);
        if (rc == R10_E_IMAGE && slot == 0) {                  /* corrupt application image: persistent mark */
            m.c[R10C_C12].bad_mask |= 1u;
            if (r10_manifest_store(b, &m) != R10_OK) return R10_E_NOR;
        }
        if (rc != R10_OK) continue;
        *last = ecp5_configure(cfg, &img);
        if (*last == ECP5_OK) { *used = (enum r10_slot)slot; return R10_OK; }
        /* a device-side configuration failure may be transient: no persistent mark, golden is tried now */
#ifdef MUTANT_BOOT_NO_GOLDEN
        break;
#endif
    }
    ecp5_safe(cfg, 0);
    return R10_E_FPGA;                                         /* the F133 keeps running without the 12F */
}

uint32_t r10_fpga_size(r10_boot *b, enum r10_comp c, int slot)
{
    uint32_t total = 0;
    if (!is_fpga(c) || slot < 0 || slot > 1) return 0;
    return fpga_container_check(b, c, slot, NULL, &total) == R10_OK ? total : 0;
}

/* ---------------- update ---------------- */
int r10_update_begin(r10_boot *b, enum r10_comp c, r10_update *u)
{
    r10_manifest m;
    int rc, s;
    if ((unsigned)c >= R10C_COUNT || !u) return R10_E_ARG;
    if ((rc = r10_manifest_load(b, &m, NULL)) != R10_OK) return rc;
    s = is_fpga(c) ? 0 : 1 - m.c[c].active;
#ifndef MUTANT_BOOT_NO_DISARM
    if (!is_fpga(c) && m.c[c].trial == (uint8_t)s) {           /* disarm before the slot is erased */
        m.c[c].trial = 0xFF;
        if ((rc = r10_manifest_store(b, &m)) != R10_OK) return rc;
    }
#endif
    if (is_fpga(c) && !(m.c[c].bad_mask & 1u)) {             /* the application slot is about to be invalid */
        m.c[c].bad_mask |= 1u;
        if ((rc = r10_manifest_store(b, &m)) != R10_OK) return rc;
    }
    u->b = b; u->comp = c; u->slot = (uint8_t)s; u->off = 0;
    u->base = r10_part_base(c, s); u->cap = r10_part_len(c, s);
    if (!r10_write_allowed(u->base, u->cap)) return R10_E_LOCKED;
    return R10_OK;
}

int r10_update_write(r10_update *u, const uint8_t *p, uint32_t n)
{
    uint8_t tmp[256];
    uint32_t sec, done;
    if (!u || !u->b || (n && !p) || (uint64_t)u->off + n > u->cap) return R10_E_ARG;
    if (!r10_write_allowed(u->base + u->off, n ? n : 1)) return R10_E_LOCKED;
    for (sec = (u->off + 0xFFFu) & ~0xFFFu; sec < u->off + n; sec += 0x1000u)
        if (nor_erase_sector(u->b->nor, u->base + sec) != NOR_OK) return R10_E_NOR;
    if (n && nor_program(u->b->nor, u->base + u->off, p, n) != NOR_OK) return R10_E_NOR;
    for (done = 0; done < n; done += (uint32_t)sizeof tmp) {
        uint32_t k = n - done < sizeof tmp ? n - done : (uint32_t)sizeof tmp;
        if (nor_read(u->b->nor, u->base + u->off + done, tmp, k) != NOR_OK) return R10_E_NOR;
        if (memcmp(tmp, p + done, k) != 0) return R10_E_NOR;
    }
    u->off += n;
    return R10_OK;
}

int r10_update_commit(r10_update *u, uint32_t version)
{
    r10_manifest m;
    int rc;
    if (!u || !u->b) return R10_E_ARG;
    if (!r10_slot_valid(u->b, u->comp, u->slot)) return R10_E_IMAGE;
    if ((rc = r10_manifest_load(u->b, &m, NULL)) != R10_OK) return rc;
    m.c[u->comp].bad_mask &= (uint8_t)~(1u << u->slot);
    m.c[u->comp].version[u->slot] = version;
    if (!is_fpga(u->comp)) { m.c[u->comp].trial = u->slot; m.c[u->comp].trials_left = R10_TRIALS; }
    return r10_manifest_store(u->b, &m);
}
