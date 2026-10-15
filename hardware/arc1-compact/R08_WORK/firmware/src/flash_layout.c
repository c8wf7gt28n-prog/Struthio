/* ARC-1 Compact R08 -- flash layout, image check, boot journal (HOST_TESTED). */
#include "flash_layout.h"
#include "crc32.h"
#include <string.h>

const fl_region fl_regions[] = {
    { "BOOT",     FL_BOOT,     FL_BOOT_LEN },
    { "JOURNAL",  FL_JOURNAL,  FL_JOURNAL_LEN },
    { "SETTINGS", FL_SETTINGS, FL_SETTINGS_LEN },
    { "RECOVERY", FL_RECOVERY, FL_RECOVERY_LEN },
    { "ASSETS",   FL_ASSETS,   FL_ASSETS_LEN },
    { "SLOT_A",   FL_SLOT_A,   FL_SLOT_LEN },
    { "SLOT_B",   FL_SLOT_B,   FL_SLOT_LEN },
    { "SPARE",    FL_SPARE,    FL_SPARE_LEN },
};
const unsigned fl_region_count = sizeof fl_regions / sizeof fl_regions[0];

int fl_layout_check(uint32_t device_size)
{
    unsigned i;
    uint32_t next = 0;
    for (i = 0; i < fl_region_count; i++) {
        const fl_region *r = &fl_regions[i];
        if (r->base != next) return -1;                       /* gap or overlap */
        if (r->base % 0x10000u || r->len % 0x10000u || r->len == 0) return -2;
        if ((uint64_t)r->base + r->len > device_size) return -3;
        next = r->base + r->len;
    }
    if (next != device_size) return -4;                       /* whole device accounted */
    if (FL_SLOT_B != 0x01000000u) return -5;                  /* slot B deliberately exercises the upper half */
    return 0;
}

static uint32_t le32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }
static uint16_t le16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static void put32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24); }
static void put16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }

static void hdr_to_bytes(const fl_img_hdr *h, uint8_t b[64])
{
    put32(b, h->magic); put16(b + 4, h->hdr_version); put16(b + 6, h->kind);
    put32(b + 8, h->img_len); put32(b + 12, h->img_crc32); put32(b + 16, h->load_addr);
    put32(b + 20, h->entry); put32(b + 24, h->version); memcpy(b + 28, h->build_id, 28);
    put32(b + 56, 0); put32(b + 60, h->hdr_crc32);
}

void fl_hdr_finalise(fl_img_hdr *h)
{
    uint8_t b[64];
    h->hdr_crc32 = 0;
    hdr_to_bytes(h, b);
    h->hdr_crc32 = arc1_crc32(0, b, 60);
}

int fl_image_check(nor_dev *d, uint32_t base, uint32_t slot_len, uint16_t kind, fl_img_hdr *out)
{
    uint8_t b[256];
    fl_img_hdr h;
    uint32_t crc = 0, off;
    int i, blank = 1;
    if (nor_read(d, base, b, 64) != NOR_OK) return FL_IMG_IO;
    for (i = 0; i < 64; i++) if (b[i] != 0xFF) blank = 0;
    if (blank) return FL_IMG_BLANK;
    memset(&h, 0, sizeof h);
    h.magic = le32(b); h.hdr_version = le16(b + 4); h.kind = le16(b + 6); h.img_len = le32(b + 8);
    h.img_crc32 = le32(b + 12); h.load_addr = le32(b + 16); h.entry = le32(b + 20); h.version = le32(b + 24);
    memcpy(h.build_id, b + 28, 28); h.hdr_crc32 = le32(b + 60);
    if (h.magic != FL_IMG_MAGIC || h.hdr_version != 1 || h.kind != kind) return FL_IMG_BAD_MAGIC;
    if (arc1_crc32(0, b, 60) != h.hdr_crc32) return FL_IMG_BAD_HDR_CRC;
    if (h.img_len == 0 || h.img_len > slot_len - 64u) return FL_IMG_BAD_LEN;
    for (off = 0; off < h.img_len; ) {
        uint32_t c = h.img_len - off < sizeof b ? h.img_len - off : (uint32_t)sizeof b;
        if (nor_read(d, base + 64u + off, b, c) != NOR_OK) return FL_IMG_IO;
        crc = arc1_crc32(crc, b, c);
        off += c;
    }
    if (crc != h.img_crc32) return FL_IMG_BAD_CRC;
    if (out) *out = h;
    return FL_IMG_OK;
}

/* ---------------- journal ---------------- */
#define JR_SIZE 32u
#define JR_PER_SECTOR (4096u / JR_SIZE)

static void jr_bytes(const fl_journal *j, uint8_t b[32])
{
    memset(b, 0, 32);
    put32(b, j->magic); put32(b + 4, j->seq);
    b[8] = j->active; b[9] = j->trial; b[10] = j->trials_left; b[11] = j->bad_mask;
    put32(b + 28, j->crc32);
}

static int jr_parse(const uint8_t b[32], fl_journal *j)
{
    memset(j, 0, sizeof *j);
    j->magic = le32(b); j->seq = le32(b + 4);
    j->active = b[8]; j->trial = b[9]; j->trials_left = b[10]; j->bad_mask = b[11];
    j->crc32 = le32(b + 28);
    return j->magic == FL_JR_MAGIC && arc1_crc32(0, b, 28) == j->crc32 && j->active <= 1 &&
           (j->trial == 0xFF || j->trial <= 1);
}

/* scan: newest valid record, its sector, and the first blank record index per sector */
static int jr_scan(nor_dev *d, fl_journal *best, int *best_sec, unsigned free_idx[2])
{
    uint8_t b[32];
    int s, found = 0;
    unsigned k;
    for (s = 0; s < 2; s++) {
        free_idx[s] = JR_PER_SECTOR;
        for (k = 0; k < JR_PER_SECTOR; k++) {
            fl_journal j;
            int blank = 1, i;
            if (nor_read(d, FL_JOURNAL + (uint32_t)s * 4096u + k * JR_SIZE, b, JR_SIZE) != NOR_OK) return -1;
            for (i = 0; i < 32; i++) if (b[i] != 0xFF) blank = 0;
            if (blank) { if (free_idx[s] == JR_PER_SECTOR) free_idx[s] = k; continue; }
            if (jr_parse(b, &j) && (!found || j.seq > best->seq)) { *best = j; *best_sec = s; found = 1; }
        }
    }
    return found;
}

int fl_journal_load(nor_dev *d, fl_journal *j)
{
    unsigned fr[2];
    int sec = 0, f = jr_scan(d, j, &sec, fr);
    if (f < 0) return NOR_ERR_IO;
    if (!f) {   /* factory state: slot A active, nothing under trial */
        memset(j, 0, sizeof *j);
        j->magic = FL_JR_MAGIC; j->seq = 0; j->active = 0; j->trial = 0xFF;
    }
    return NOR_OK;
}

int fl_journal_store(nor_dev *d, fl_journal *j)
{
    fl_journal cur;
    unsigned fr[2];
    int sec = 0, f, rc;
    uint8_t b[32];
    uint32_t addr;
    f = jr_scan(d, &cur, &sec, fr);
    if (f < 0) return NOR_ERR_IO;
    j->magic = FL_JR_MAGIC;
    j->seq = (f ? cur.seq : 0u) + 1u;
    j->crc32 = 0;
    jr_bytes(j, b);
    j->crc32 = arc1_crc32(0, b, 28);
    jr_bytes(j, b);
    if (!f) { sec = 0; if (fr[0] == JR_PER_SECTOR) { if ((rc = nor_erase_sector(d, FL_JOURNAL)) != NOR_OK) return rc; fr[0] = 0; } }
    if (f && fr[sec] == JR_PER_SECTOR) {
        /* active sector full: start the other one. The newest record stays in
         * the full sector until the first record in the new sector is written. */
        int other = 1 - sec;
        if ((rc = nor_erase_sector(d, FL_JOURNAL + (uint32_t)other * 4096u)) != NOR_OK) return rc;
        sec = other; fr[sec] = 0;
    }
    addr = FL_JOURNAL + (uint32_t)sec * 4096u + fr[sec] * JR_SIZE;
    rc = nor_program(d, addr, b, JR_SIZE);
    if (rc) return rc;
    {
        uint8_t r[32];
        if ((rc = nor_read(d, addr, r, 32)) != NOR_OK) return rc;
        if (memcmp(r, b, 32) != 0) return NOR_ERR_VERIFY;
    }
    return NOR_OK;
}

static uint32_t slot_base(int s) { return s ? FL_SLOT_B : FL_SLOT_A; }

int fl_boot_select(nor_dev *d, enum fl_boot_target *target)
{
    fl_journal j;
    int rc, valid[2], s;
    if ((rc = fl_journal_load(d, &j)) != NOR_OK) return rc;
    for (s = 0; s < 2; s++)
        valid[s] = fl_image_check(d, slot_base(s), FL_SLOT_LEN, 1, NULL) == FL_IMG_OK && !(j.bad_mask & (1u << s));
    if (j.trial != 0xFF) {
        s = j.trial;
        if (valid[s] && j.trials_left > 0) {
            j.trials_left--;                     /* consume an attempt BEFORE jumping */
            if ((rc = fl_journal_store(d, &j)) != NOR_OK) return rc;
            *target = (enum fl_boot_target)s;
            return NOR_OK;
        }
        j.bad_mask |= (uint8_t)(1u << s);        /* trial exhausted or image invalid */
        j.trial = 0xFF;
        if ((rc = fl_journal_store(d, &j)) != NOR_OK) return rc;
        valid[s] = 0;
    }
    if (valid[j.active]) { *target = (enum fl_boot_target)j.active; return NOR_OK; }
    s = 1 - j.active;
    if (valid[s]) {   /* unconfirmed image in the other slot: run it as a trial */
        j.trial = (uint8_t)s; j.trials_left = 2;
        if ((rc = fl_journal_store(d, &j)) != NOR_OK) return rc;
        *target = (enum fl_boot_target)s;
        return NOR_OK;
    }
    *target = fl_image_check(d, FL_RECOVERY, FL_RECOVERY_LEN, 2, NULL) == FL_IMG_OK ? FL_BOOT_RECOVERY : FL_BOOT_NONE;
    return NOR_OK;
}

int fl_install_update(nor_dev *d, const uint8_t *img, uint32_t len)
{
    fl_journal j;
    int rc, s;
    if (len < 64 || len > FL_SLOT_LEN) return NOR_ERR_RANGE;
    if ((rc = fl_journal_load(d, &j)) != NOR_OK) return rc;
    s = 1 - j.active;
    if (j.trial == s) {                 /* disarm before the slot is erased */
        j.trial = 0xFF;
        if ((rc = fl_journal_store(d, &j)) != NOR_OK) return rc;
    }
    if ((rc = nor_write_verified(d, slot_base(s), img, len)) != NOR_OK) return rc;
    if (fl_image_check(d, slot_base(s), FL_SLOT_LEN, 1, NULL) != FL_IMG_OK) return NOR_ERR_VERIFY;
    j.trial = (uint8_t)s; j.trials_left = 3; j.bad_mask &= (uint8_t)~(1u << s);
    return fl_journal_store(d, &j);
}

int fl_confirm_running(nor_dev *d, enum fl_boot_target running)
{
    fl_journal j;
    int rc;
    if ((rc = fl_journal_load(d, &j)) != NOR_OK) return rc;
    if (running > FL_BOOT_SLOT_B) return NOR_ERR_STATE;
    if (j.trial != (uint8_t)running) return (j.active == (uint8_t)running) ? NOR_OK : NOR_ERR_STATE;
    j.active = (uint8_t)running; j.trial = 0xFF;
    return fl_journal_store(d, &j);
}
