/* ARC-1 Compact R06 host tests: BT820 host layer, T35 mailbox client,
 * optional accelerator dispatch with CPU fallback, and the graceful
 * degradation property (BT820 command stream identical with or without the
 * FPGA). HOST_TESTED against mocks; no silicon, no F133 build. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "accel_dispatch.h"
#include "bt820_host.h"
#include "mocks.h"
#include "t35_link.h"

static int g_fail = 0, g_checks = 0;
#define CHECK(c) do { g_checks++; if (!(c)) { g_fail++; printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)

static mock_bt820 g_bt;
static mock_t35 g_t35;

/* ------------------------------------------------------------------ */
static void test_bt820_encoding(void) {
    bt820_dev d;
    arc1_spi_hal h = mbt_hal(&g_bt);
    uint8_t w[8] = {1, 2, 3, 4, 5, 6, 7, 8}, r[8];
    uint32_t v = 0, words[3] = {0x11223344u, 0xA5A5A5A5u, 0u};
    mbt_init(&g_bt);
    CHECK(bt820_init(&d, &h, 64) == BT820_OK);
    CHECK(bt820_write(&d, 0x00012344u, w, 8) == BT820_OK);
    CHECK(g_bt.last_hdr[0] == 0x80 && g_bt.last_hdr[1] == 0x01 && g_bt.last_hdr[2] == 0x23 && g_bt.last_hdr[3] == 0x44);
    CHECK(memcmp(&g_bt.ram[0x12344], w, 8) == 0);
    CHECK(g_bt.cs == 0);
    for (uint32_t lat = 0; lat <= 20; lat++) {         /* data-valid polling */
        g_bt.poll_latency = lat;
        memset(r, 0, sizeof r);
        CHECK(bt820_read(&d, 0x00012344u, r, 8) == BT820_OK);
        CHECK(memcmp(r, w, 8) == 0);
        CHECK(d.last_poll_bytes == lat + 1u);
        CHECK(g_bt.last_hdr[0] == 0x00);               /* read: MSB of Addr3 is 0 */
    }
    g_bt.poll_latency = 0;
    CHECK(bt820_write32(&d, 0x100u, words, 3) == BT820_OK);
    CHECK(g_bt.ram[0x100] == 0x44 && g_bt.ram[0x103] == 0x11);   /* little endian (ASSUMPTION) */
    CHECK(bt820_read32(&d, 0x104u, &v) == BT820_OK && v == 0xA5A5A5A5u);
    CHECK(bt820_read32(&d, 0x00200000u, &v) == BT820_ERR_ILLEGAL_ADDR && v == BT820_ILLEGAL_WORD);
}

static void test_bt820_errors(void) {
    bt820_dev d;
    arc1_spi_hal h = mbt_hal(&g_bt);
    uint8_t b[8] = {0};
    mbt_init(&g_bt);
    CHECK(bt820_init(&d, &h, 16) == BT820_OK);
    CHECK(bt820_write(&d, 0x102u, b, 4) == BT820_ERR_ARG);          /* unaligned */
    CHECK(bt820_write(&d, 0x100u, b, 6) == BT820_ERR_ARG);          /* not a word multiple */
    CHECK(bt820_read(&d, 0x100u, b, 0) == BT820_ERR_ARG);
    CHECK(bt820_read(&d, 0x80000000u, b, 4) == BT820_ERR_ARG);      /* beyond 31-bit space */
    CHECK(bt820_read(&d, 0x7FFFFFFCu, b, 8) == BT820_ERR_ARG);      /* wraps */
    CHECK(bt820_write(&d, 0x7F000000u, b, 4) == BT820_ERR_ARG);     /* 0xFF prefix ambiguity */
    CHECK(g_bt.n_writes == 0 && g_bt.n_reads == 0);                 /* nothing reached the bus */
    g_bt.never_valid = 1;
    CHECK(bt820_read(&d, 0x100u, b, 4) == BT820_ERR_TIMEOUT);
    CHECK(d.last_poll_bytes == 16u && g_bt.cs == 0);                /* CS# released on timeout */
    g_bt.never_valid = 0;
    CHECK(bt820_host_command(&d, 0x44u, 0x02u) == BT820_OK);
    CHECK(g_bt.n_cmds == 1 && g_bt.last_cmd[0] == 0x44 && g_bt.last_cmd[1] == 0x02 && g_bt.last_cmd[2] == 0x00);
    CHECK(bt820_host_active(&d) == BT820_OK && g_bt.n_active == 1);
    d.mode = BT820_BUS_QUAD;
    CHECK(bt820_host_command(&d, 0x44u, 0x02u) == BT820_ERR_MODE);
    CHECK(bt820_host_active(&d) == BT820_ERR_MODE);
}

/* ------------------------------------------------------------------ */
static void test_t35_link(void) {
    t35_link l;
    arc1_spi_hal h = mt35_hal(&g_t35);
    uint8_t req[300], resp[8192];
    size_t rl = 0;
    uint16_t st = 0;
    size_t i;
    mt35_init(&g_t35, ENG_LOOPBACK);
    CHECK(t35_init(&l, &h, 20000) == T35_OK);
    g_t35.present = 0;                                   /* FPGA absent: bus reads 0xFF */
    CHECK(t35_probe(&l) == T35_NOT_READY);
    CHECK(t35_status(&l, &st) == T35_NOT_READY);
    CHECK(t35_exchange(&l, req, 10, resp, sizeof resp, &rl) == T35_NOT_READY);
    g_t35.present = 1;
    CHECK(t35_probe(&l) == T35_OK);
    for (i = 0; i < sizeof req; i++) req[i] = (uint8_t)(i * 7u + 3u);
    CHECK(t35_exchange(&l, req, sizeof req, resp, sizeof resp, &rl) == T35_OK);
    CHECK(rl == sizeof req && memcmp(req, resp, rl) == 0);
    /* a dropped job leaves JOB_PENDING: the next doorbell must be refused */
    mt35_init(&g_t35, ENG_DROP);
    CHECK(t35_exchange(&l, req, sizeof req, resp, sizeof resp, &rl) == T35_TIMEOUT);
    CHECK(t35_exchange(&l, req, sizeof req, resp, sizeof resp, &rl) == T35_BUSY);
    CHECK(t35_exchange(&l, req, 0, resp, sizeof resp, &rl) == T35_ARG);
}

/* ------------------------------------------------------------------ */
/* SYNTHETIC scene: 256 rectangles, quarter-turn rotations, translations,
 * some deliberately off-screen. Not STRUTHIO content. */
#define NOBJ 256u
static arc1_transform_job g_jobs[NOBJ];
static void make_scene(uint32_t frame) {
    static const int32_t rot[4][4] = {{65536, 0, 0, 65536}, {0, -65536, 65536, 0},
                                      {-65536, 0, 0, -65536}, {0, 65536, -65536, 0}};
    for (uint32_t i = 0; i < NOBJ; i++) {
        arc1_transform_job *j = &g_jobs[i];
        const int32_t *m = rot[(i + frame) & 3u];
        int32_t x = (int32_t)((i * 37u + frame * 5u) % 1400u) - 200;
        int32_t y = (int32_t)((i * 53u + frame * 3u) % 900u) - 150;
        j->xmin = -16 * 65536; j->ymin = -12 * 65536; j->xmax = 16 * 65536; j->ymax = 12 * 65536;
        j->m00 = m[0]; j->m01 = m[1]; j->m10 = m[2]; j->m11 = m[3];
        j->m02 = x * 65536; j->m12 = y * 65536;
        j->viewport_width = 1024; j->viewport_height = 600;
        j->tag = i;
    }
}

/* compute one frame (optional FPGA), then emit a SYNTHETIC draw stream to the
 * BT820 mock. The addresses/words are placeholders, not the BT820 memory map. */
static int run_frame(accel_ctx *a, bt820_dev *bt, uint32_t frame, arc1_transform_result *out_all) {
    uint32_t words[4], k = 0;
    size_t off = 0;
    make_scene(frame);
    while (off < NOBJ) {
        size_t n = NOBJ - off > ACCEL_MAX_BATCH ? ACCEL_MAX_BATCH : NOBJ - off;
        (void)accel_transform_batch(a, &g_jobs[off], n, &out_all[off]);
        off += n;
    }
    for (uint32_t i = 0; i < NOBJ; i++) {
        if (!(out_all[i].flags & ARC1_TRANSFORM_VISIBLE)) continue;
        words[0] = out_all[i].tag; words[1] = (uint32_t)out_all[i].minx;
        words[2] = (uint32_t)out_all[i].miny; words[3] = out_all[i].flags;
        if (bt820_write32(bt, 0x00010000u + 16u * k, words, 4)) return -1;
        k++;
    }
    words[0] = k; words[1] = frame;
    return bt820_write32(bt, 0x00000F00u, words, 2);   /* synthetic "frame done" word */
}

static arc1_transform_result g_ref[NOBJ], g_got[NOBJ];

static uint32_t run_mode(int with_link, mt35_engine e, int enabled, accel_ctx *a_out, int verify) {
    bt820_dev bt;
    t35_link l;
    accel_ctx a;
    arc1_spi_hal hb = mbt_hal(&g_bt), ht = mt35_hal(&g_t35);
    mbt_init(&g_bt);
    mt35_init(&g_t35, e);
    (void)bt820_init(&bt, &hb, 64);
    (void)t35_init(&l, &ht, 20000);
    accel_init(&a, with_link ? &l : NULL, enabled);
    a.verify = verify;
    for (uint32_t f = 0; f < 3; f++) {
        CHECK(run_frame(&a, &bt, f, g_got) == 0);
        make_scene(f);
        arc1_transform_batch(g_jobs, g_ref, NOBJ);
        CHECK(memcmp(g_ref, g_got, sizeof g_ref) == 0);     /* results always equal the CPU reference */
    }
    if (a_out) *a_out = a;
    return g_bt.trace_hash;
}

static void test_degradation(void) {
    accel_ctx a;
    uint32_t ref_hash, h;
    static const struct { mt35_engine e; accel_fallback why; const char *name; } faults[] = {
        {ENG_LOOPBACK, ACCEL_FB_SESSION, "transport loopback (R06 RTL engine)"},
        {ENG_DROP, ACCEL_FB_TIMEOUT, "never answers"},
        {ENG_SLOW, ACCEL_FB_TIMEOUT, "late answer"},
        {ENG_CORRUPT_CRC, ACCEL_FB_FRAME, "corrupted RESULT CRC"},
        {ENG_WRONG_TAG, ACCEL_FB_RESULT, "wrong tag"},
        {ENG_APP_ERROR, ACCEL_FB_RESULT, "application error status"},
        {ENG_RESET_ON_JOB, ACCEL_FB_NOT_READY, "FPGA reset mid-job"},
        {ENG_NO_DONE, ACCEL_FB_SESSION, "missing DONE status"},
    };
    ref_hash = run_mode(0, ENG_SW_ACCEL, 0, &a, 0);           /* CPU only, no FPGA fitted */
    CHECK(a.fpga_batches == 0 && a.reasons[ACCEL_FB_DISABLED] == 12);
    printf("INFO cpu_only bt820_trace=%08x writes=%llu\n", ref_hash, (unsigned long long)g_bt.n_writes);

    h = run_mode(1, ENG_SW_ACCEL, 1, &a, 1);                  /* healthy accelerator (+verify) */
    CHECK(h == ref_hash);
    CHECK(a.fpga_batches == 12 && a.cpu_batches == 0 && a.epoch == 1u && a.next_sequence == 13u);
    printf("INFO sw_accel fpga_batches=%llu bt820_trace=%08x\n", (unsigned long long)a.fpga_batches, h);

    h = run_mode(1, ENG_SW_ACCEL, 0, &a, 0);                  /* FPGA fitted but disabled */
    CHECK(h == ref_hash && a.fpga_batches == 0);

    g_t35.present = 0;
    for (size_t i = 0; i < sizeof faults / sizeof faults[0]; i++) {
        h = run_mode(1, faults[i].e, 1, &a, 0);
        CHECK(h == ref_hash);                                 /* BT820 stream unaffected */
        CHECK(a.fpga_batches == 0 && a.cpu_batches == 12);
        CHECK(a.reasons[faults[i].why] >= 1);
        printf("INFO fault=%-40s fallback=%s x%llu bt820_trace=%08x\n", faults[i].name,
               accel_fallback_string(faults[i].why), (unsigned long long)a.reasons[faults[i].why], h);
    }

    /* absent FPGA (no answer on the bus at all) */
    {
        bt820_dev bt; t35_link l; arc1_spi_hal hb = mbt_hal(&g_bt), ht = mt35_hal(&g_t35);
        mbt_init(&g_bt); mt35_init(&g_t35, ENG_SW_ACCEL); g_t35.present = 0;
        (void)bt820_init(&bt, &hb, 64); (void)t35_init(&l, &ht, 20000);
        accel_init(&a, &l, 1);
        for (uint32_t f = 0; f < 3; f++) CHECK(run_frame(&a, &bt, f, g_got) == 0);
        CHECK(g_bt.trace_hash == ref_hash && a.reasons[ACCEL_FB_NOT_READY] == 12);
    }

    /* recovery: a fault, then a healthy engine -> new HELLO with a larger epoch */
    {
        t35_link l; arc1_spi_hal ht = mt35_hal(&g_t35);
        mt35_init(&g_t35, ENG_CORRUPT_CRC);
        (void)t35_init(&l, &ht, 20000);
        accel_init(&a, &l, 1);
        make_scene(0);
        CHECK(accel_transform_batch(&a, g_jobs, 85, g_got) == ACCEL_FB_FRAME);
        CHECK(a.epoch == 1u && !a.session_ok);
        g_t35.engine = ENG_SW_ACCEL;
        CHECK(accel_transform_batch(&a, g_jobs, 85, g_got) == ACCEL_FB_NONE);
        CHECK(a.epoch == 2u && a.session_ok);
        arc1_transform_batch(g_jobs, g_ref, 85);
        CHECK(memcmp(g_ref, g_got, 85 * sizeof g_got[0]) == 0);
    }

    /* a well-formed but numerically wrong answer is only caught by verify mode */
    {
        t35_link l; arc1_spi_hal ht = mt35_hal(&g_t35);
        mt35_init(&g_t35, ENG_WRONG_VALUE);
        (void)t35_init(&l, &ht, 20000);
        accel_init(&a, &l, 1);
        make_scene(1);
        a.verify = 1;
        CHECK(accel_transform_batch(&a, g_jobs, 85, g_got) == ACCEL_FB_VERIFY);
        arc1_transform_batch(g_jobs, g_ref, 85);
        CHECK(memcmp(g_ref, g_got, 85 * sizeof g_got[0]) == 0);
        a.verify = 0;
        CHECK(accel_transform_batch(&a, g_jobs, 85, g_got) == ACCEL_FB_NONE);
        CHECK(memcmp(g_ref, g_got, 85 * sizeof g_got[0]) != 0);   /* documented limitation */
    }
}

static void test_payload_codec(void) {
    static uint8_t buf[4096];
    arc1_transform_result r[2];
    make_scene(0);
    CHECK(accel_pack_jobs(g_jobs, 85, buf, sizeof buf) == 4088u);    /* R05 capacity arithmetic */
    CHECK(accel_pack_jobs(g_jobs, 86, buf, sizeof buf) == 0u);
    CHECK(accel_pack_jobs(g_jobs, 0, buf, sizeof buf) == 0u);
    memset(buf, 0, 8 + 48);
    buf[0] = 1; buf[2] = 1; buf[4] = 2;                              /* header claims 2 records */
    CHECK(accel_unpack_results(buf, 8 + 24, 2, r) != 0);             /* length mismatch */
    buf[4] = 1;
    buf[8 + 20] = 8;                                                 /* undefined flag bit */
    CHECK(accel_unpack_results(buf, 8 + 24, 1, r) != 0);
    buf[8 + 20] = 1;
    CHECK(accel_unpack_results(buf, 8 + 24, 1, r) == 0 && r[0].flags == 1u);
}

int main(void) {
    test_bt820_encoding();
    test_bt820_errors();
    test_t35_link();
    test_payload_codec();
    test_degradation();
    printf("%s firmware host tests: %d checks, %d failures (HOST_TESTED with mocks; no silicon)\n",
           g_fail ? "FAIL" : "PASS", g_checks, g_fail);
    return g_fail ? 1 : 0;
}
