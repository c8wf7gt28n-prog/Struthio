/* Host tests: microSD game library and saves with a mock card (HOST_TESTED). */
#include <stdlib.h>
#include <string.h>
#include "check.h"
#include "crc32.h"
#include "game_lib.h"

#define NF 12
typedef struct mfile { char name[64]; uint8_t data[9000]; uint64_t len; int used; } mfile;
typedef struct mcard { int present, mount_rc, list_io_err, write_budget; mfile f[NF]; } mcard;

static mfile *find(mcard *c, const char *n)
{
    int i;
    for (i = 0; i < NF; i++) if (c->f[i].used && strcmp(c->f[i].name, n) == 0) return &c->f[i];
    return NULL;
}
static mfile *create(mcard *c, const char *n)
{
    int i;
    mfile *f = find(c, n);
    if (f) return f;
    for (i = 0; i < NF; i++) if (!c->f[i].used) { memset(&c->f[i], 0, sizeof c->f[i]); c->f[i].used = 1; strcpy(c->f[i].name, n); return &c->f[i]; }
    return NULL;
}
static int c_present(void *x) { return ((mcard *)x)->present; }
static int c_mount(void *x) { return ((mcard *)x)->mount_rc; }
static int c_list(void *x, unsigned idx, char *name, size_t cap)
{
    mcard *c = (mcard *)x; unsigned k = 0; int i;
    if (c->list_io_err) return -1;
    for (i = 0; i < NF; i++) if (c->f[i].used) { if (k == idx) { strncpy(name, c->f[i].name, cap); return 1; } k++; }
    return 0;
}
static int c_size(void *x, const char *n, uint64_t *sz) { mfile *f = find((mcard *)x, n); if (!f) return -1; *sz = f->len; return 0; }
static int c_read(void *x, const char *n, uint64_t off, void *buf, size_t len)
{
    mcard *c = (mcard *)x; mfile *f = find(c, n); size_t k;
    if (!c->present) return -2;
    if (!f) return -1;
    if (off >= f->len) return 0;
    k = (size_t)(f->len - off) < len ? (size_t)(f->len - off) : len;
    memcpy(buf, f->data + off, k);
    return (int)k;
}
static int c_write(void *x, const char *n, uint64_t off, const void *buf, size_t len)
{
    mcard *c = (mcard *)x; mfile *f; size_t k = len;
    if (!c->present) return -2;
    f = create(c, n);
    if (!f || off + len > sizeof f->data) return -1;
    if (c->write_budget >= 0) {               /* card pulled / power lost mid-write */
        if ((int)k > c->write_budget) k = (size_t)c->write_budget;
        c->write_budget -= (int)k;
        if (c->write_budget == 0) c->present = 0;
    }
    memcpy(f->data + off, buf, k);
    if (off + k > f->len) f->len = off + k;
    return (int)k;
}

static mcard card;
static lib_card_ops ops = { &card, c_present, c_mount, c_list, c_size, c_read, c_write };

static void add_pkg(const char *file, const char *id, const char *title, uint32_t minfw, uint32_t plen, int corrupt)
{
    mfile *f = create(&card, file);
    uint32_t i;
    for (i = 0; i < plen; i++) f->data[A1GP_HDR_LEN + i] = (uint8_t)(i ^ 0x5A);
    a1gp_build(f->data, id, title, minfw, plen, arc1_crc32(0, f->data + A1GP_HDR_LEN, plen));
    f->len = A1GP_HDR_LEN + plen;
    if (corrupt == 1) f->data[A1GP_HDR_LEN + 3] ^= 0xFF;     /* payload */
    if (corrupt == 2) f->data[30] ^= 0x01;                   /* header byte -> header CRC */
    if (corrupt == 3) f->len -= 5;                            /* truncated download */
}

static void t_scan(void)
{
    lib_entry e[8]; unsigned n, i; int seen_ok = 0;
    memset(&card, 0, sizeof card); card.write_budget = -1;
    CHECK(lib_scan(&ops, 100, e, 8, &n) == LIB_NO_CARD && n == 0);   /* absent card: normal */
    card.present = 1; card.mount_rc = -1;
    CHECK(lib_scan(&ops, 100, e, 8, &n) == LIB_UNSUPPORTED_FS);
    card.mount_rc = -2;
    CHECK(lib_scan(&ops, 100, e, 8, &n) == LIB_IO_ERROR);
    card.mount_rc = 0;
    CHECK(lib_scan(&ops, 100, e, 8, &n) == LIB_CARD_OK && n == 0);   /* empty card */
    add_pkg("good.a1gp", "ostrich_run", "Ostrich Run", 90, 3000, 0);
    add_pkg("payload.a1gp", "bad_payload", "Bad payload", 90, 2000, 1);
    add_pkg("hdr.a1gp", "bad_hdr", "Bad header", 90, 2000, 2);
    add_pkg("trunc.a1gp", "trunc", "Truncated", 90, 2000, 3);
    add_pkg("future.a1gp", "future", "Needs newer FW", 200, 100, 0);
    { mfile *f = create(&card, "readme.txt"); f->len = 5; }
    CHECK(lib_scan(&ops, 100, e, 8, &n) == LIB_CARD_OK && n == 5);
    for (i = 0; i < n; i++) {
        if (strcmp(e[i].file, "good.a1gp") == 0) { CHECK(e[i].status == A1GP_OK && strcmp(e[i].info.title, "Ostrich Run") == 0);
            CHECK(lib_verify_payload(&ops, &e[i]) == A1GP_OK); seen_ok = 1; }
        if (strcmp(e[i].file, "payload.a1gp") == 0) { CHECK(e[i].status == A1GP_OK); CHECK(lib_verify_payload(&ops, &e[i]) == A1GP_BAD_PAYLOAD_CRC); }
        if (strcmp(e[i].file, "hdr.a1gp") == 0) CHECK(e[i].status == A1GP_BAD_HDR_CRC);
        if (strcmp(e[i].file, "trunc.a1gp") == 0) CHECK(e[i].status == A1GP_BAD_PAYLOAD_LEN);
        if (strcmp(e[i].file, "future.a1gp") == 0) CHECK(e[i].status == A1GP_NEEDS_NEWER_FW);
    }
    CHECK(seen_ok);
    card.list_io_err = 1;
    CHECK(lib_scan(&ops, 100, e, 8, &n) == LIB_IO_ERROR);
    card.list_io_err = 0;
    /* hostile header fields: non-terminated title, bad id chars, nonzero reserved */
    {
        uint8_t hd[A1GP_HDR_LEN]; a1gp_info inf;
        a1gp_build(hd, "ok_id", "t", 1, 10, 0);
        CHECK(a1gp_parse(hd, sizeof hd, 1, A1GP_HDR_LEN + 10, &inf) == A1GP_OK);
        CHECK(a1gp_parse(hd, 100, 1, A1GP_HDR_LEN + 10, &inf) == A1GP_TRUNCATED);
        memset(hd + 24, 'A', 48);
        { uint32_t c = arc1_crc32(0, hd, 124); hd[124] = (uint8_t)c; hd[125] = (uint8_t)(c >> 8); hd[126] = (uint8_t)(c >> 16); hd[127] = (uint8_t)(c >> 24); }
        CHECK(a1gp_parse(hd, sizeof hd, 1, A1GP_HDR_LEN + 10, &inf) == A1GP_BAD_FIELD);
        a1gp_build(hd, "../etc", "t", 1, 10, 0);
        CHECK(a1gp_parse(hd, sizeof hd, 1, A1GP_HDR_LEN + 10, &inf) == A1GP_BAD_FIELD);
        a1gp_build(hd, "x", "t", 1, 10, 0); hd[100] = 1;
        { uint32_t c = arc1_crc32(0, hd, 124); hd[124] = (uint8_t)c; hd[125] = (uint8_t)(c >> 8); hd[126] = (uint8_t)(c >> 16); hd[127] = (uint8_t)(c >> 24); }
        CHECK(a1gp_parse(hd, sizeof hd, 1, A1GP_HDR_LEN + 10, &inf) == A1GP_BAD_FIELD);
    }
}

static void t_saves(void)
{
    uint8_t a[300], b[300], r[400]; uint32_t len = 0, seq = 0; int k;
    memset(&card, 0, sizeof card); card.present = 1; card.write_budget = -1;
    for (k = 0; k < 300; k++) { a[k] = (uint8_t)k; b[k] = (uint8_t)(255 - k); }
    CHECK(save_load(&ops, "ostrich_run", r, sizeof r, &len, &seq) == SAVE_NONE);
    CHECK(save_commit(&ops, "ostrich_run", a, 300) == SAVE_OK);
    CHECK(save_load(&ops, "ostrich_run", r, sizeof r, &len, &seq) == SAVE_OK && len == 300 && seq == 1 && memcmp(r, a, 300) == 0);
    CHECK(save_commit(&ops, "ostrich_run", b, 200) == SAVE_OK);
    CHECK(save_load(&ops, "ostrich_run", r, sizeof r, &len, &seq) == SAVE_OK && len == 200 && seq == 2 && memcmp(r, b, 200) == 0);
    /* card pulled after 50 bytes of the next save: previous save survives intact */
    card.write_budget = 50;
    CHECK(save_commit(&ops, "ostrich_run", a, 300) == SAVE_IO);
    card.present = 1; card.write_budget = -1;
    CHECK(save_load(&ops, "ostrich_run", r, sizeof r, &len, &seq) == SAVE_OK && seq == 2 && len == 200 && memcmp(r, b, 200) == 0);
    /* pulled after the data but before the header */
    card.write_budget = 300;
    CHECK(save_commit(&ops, "ostrich_run", a, 300) == SAVE_IO);
    card.present = 1; card.write_budget = -1;
    CHECK(save_load(&ops, "ostrich_run", r, sizeof r, &len, &seq) == SAVE_OK && seq == 2);
    /* then a good save continues the sequence */
    CHECK(save_commit(&ops, "ostrich_run", a, 300) == SAVE_OK);
    CHECK(save_load(&ops, "ostrich_run", r, sizeof r, &len, &seq) == SAVE_OK && seq == 3 && memcmp(r, a, 300) == 0);
    CHECK(save_commit(&ops, "ostrich_run", a, SAVE_MAX + 1u) == SAVE_TOO_BIG);
    card.present = 0;
    CHECK(save_commit(&ops, "ostrich_run", a, 10) == SAVE_NO_CARD);
}

void run_library_tests(void)
{
    t_scan();
    t_saves();
}
