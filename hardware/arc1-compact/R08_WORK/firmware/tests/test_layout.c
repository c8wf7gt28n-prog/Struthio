/* Host tests: flash layout, image check, journal, A/B boot selection (HOST_TESTED). */
#include <stdlib.h>
#include <string.h>
#include "check.h"
#include "crc32.h"
#include "flash_layout.h"
#include "nor_mock.h"

static nor_mock m; static arc1_spi_hal h; static nor_dev d;

static void setup(void)
{
    nor_mock_init(&m, FL_SIZE, 0xEF, 0x40, 0x19); nor_mock_hal(&m, &h);
    memset(&d, 0, sizeof d);
    CHECK(nor_init(&d, &h) == NOR_OK);
}

static uint8_t *make_img(uint32_t payload, uint16_t kind, uint32_t version, uint32_t *total)
{
    uint8_t *b = (uint8_t *)malloc(payload + 64u);
    fl_img_hdr hd;
    uint32_t i;
    for (i = 0; i < payload; i++) b[64 + i] = (uint8_t)(i * 7u + version);
    memset(&hd, 0, sizeof hd);
    hd.magic = FL_IMG_MAGIC; hd.hdr_version = 1; hd.kind = kind; hd.img_len = payload;
    hd.img_crc32 = arc1_crc32(0, b + 64, payload); hd.load_addr = 0x40000000u; hd.entry = 0x40000000u;
    hd.version = version;
    fl_hdr_finalise(&hd);
    /* serialise exactly like the driver reads it */
    {
        uint8_t *p = b;
        uint32_t v[] = { hd.magic };
        (void)v;
        p[0] = (uint8_t)hd.magic; p[1] = (uint8_t)(hd.magic >> 8); p[2] = (uint8_t)(hd.magic >> 16); p[3] = (uint8_t)(hd.magic >> 24);
        p[4] = 1; p[5] = 0; p[6] = (uint8_t)kind; p[7] = (uint8_t)(kind >> 8);
        for (i = 0; i < 4; i++) {
            p[8 + i] = (uint8_t)(hd.img_len >> (8 * i)); p[12 + i] = (uint8_t)(hd.img_crc32 >> (8 * i));
            p[16 + i] = (uint8_t)(hd.load_addr >> (8 * i)); p[20 + i] = (uint8_t)(hd.entry >> (8 * i));
            p[24 + i] = (uint8_t)(hd.version >> (8 * i)); p[56 + i] = 0; p[60 + i] = (uint8_t)(hd.hdr_crc32 >> (8 * i));
        }
        memset(p + 28, 0, 28);
    }
    *total = payload + 64u;
    return b;
}

static void t_layout(void)
{
    unsigned i;
    CHECK(fl_layout_check(FL_SIZE) == 0);
    CHECK(fl_layout_check(0x01000000u) != 0);   /* a 16 MiB part cannot hold this map */
    CHECK(FL_SLOT_B >= 0x01000000u && FL_SLOT_A + FL_SLOT_LEN <= 0x01000000u);
    for (i = 0; i < fl_region_count; i++) CHECK(fl_regions[i].len > 0);
}

static void t_ab_cycle(void)
{
    enum fl_boot_target t;
    uint32_t n1, n2, n3;
    uint8_t *i1, *i2, *i3;
    fl_journal j;
    setup();
    /* blank flash: nothing to boot -> FL_BOOT_NONE (board then needs FEL/clip) */
    CHECK(fl_boot_select(&d, &t) == NOR_OK && t == FL_BOOT_NONE);
    /* recovery only */
    i1 = make_img(5000, 2, 1, &n1);
    CHECK(nor_write_verified(&d, FL_RECOVERY, i1, n1) == NOR_OK);
    CHECK(fl_boot_select(&d, &t) == NOR_OK && t == FL_BOOT_RECOVERY);
    free(i1);
    /* factory image into slot A via the update path (A is "active" but empty: update goes to B) */
    i1 = make_img(70000, 1, 10, &n1);
    CHECK(fl_install_update(&d, i1, n1) == NOR_OK);
    CHECK(m.upper_half_touched);                     /* slot B lives above 16 MiB */
    CHECK(fl_boot_select(&d, &t) == NOR_OK && t == FL_BOOT_SLOT_B);
    CHECK(fl_confirm_running(&d, FL_BOOT_SLOT_B) == NOR_OK);
    CHECK(fl_journal_load(&d, &j) == NOR_OK && j.active == 1 && j.trial == 0xFF);
    CHECK(fl_boot_select(&d, &t) == NOR_OK && t == FL_BOOT_SLOT_B);
    /* update to v11 -> slot A, trial, never confirmed: 3 attempts then fall back to B */
    i2 = make_img(90000, 1, 11, &n2);
    CHECK(fl_install_update(&d, i2, n2) == NOR_OK);
    CHECK(fl_boot_select(&d, &t) == NOR_OK && t == FL_BOOT_SLOT_A);
    CHECK(fl_boot_select(&d, &t) == NOR_OK && t == FL_BOOT_SLOT_A);
    CHECK(fl_boot_select(&d, &t) == NOR_OK && t == FL_BOOT_SLOT_A);
    CHECK(fl_boot_select(&d, &t) == NOR_OK && t == FL_BOOT_SLOT_B);   /* rollback */
    CHECK(fl_journal_load(&d, &j) == NOR_OK && (j.bad_mask & 1u) && j.trial == 0xFF && j.active == 1);
    CHECK(fl_confirm_running(&d, FL_BOOT_SLOT_A) == NOR_ERR_STATE);    /* cannot confirm a failed slot */
    /* v12 into A again, this time confirmed */
    i3 = make_img(1000, 1, 12, &n3);
    CHECK(fl_install_update(&d, i3, n3) == NOR_OK);
    CHECK(fl_boot_select(&d, &t) == NOR_OK && t == FL_BOOT_SLOT_A);
    CHECK(fl_confirm_running(&d, FL_BOOT_SLOT_A) == NOR_OK);
    CHECK(fl_journal_load(&d, &j) == NOR_OK && j.active == 0 && !(j.bad_mask & 1u));
    /* corrupt active slot payload: boot falls to the other valid slot as a trial */
    {
        uint8_t z = 0x00;
        CHECK(nor_program(&d, FL_SLOT_A + 64u + 100u, &z, 1) == NOR_OK);
    }
    CHECK(fl_image_check(&d, FL_SLOT_A, FL_SLOT_LEN, 1, NULL) == FL_IMG_BAD_CRC);
    CHECK(fl_boot_select(&d, &t) == NOR_OK && t == FL_BOOT_SLOT_B);
    CHECK(nor_mock_brom_read_ok(&m));
    free(i1); free(i2); free(i3);
    nor_mock_free(&m);
}

static void t_journal_power_fail(void)
{
    fl_journal j;
    int k;
    setup();
    /* fill well past one sector (128 records) to exercise the ping-pong */
    for (k = 0; k < 300; k++) {
        CHECK(fl_journal_load(&d, &j) == NOR_OK);
        j.trials_left = (uint8_t)(k & 0xFF);
        CHECK(fl_journal_store(&d, &j) == NOR_OK);
    }
    CHECK(fl_journal_load(&d, &j) == NOR_OK && j.seq == 300u && j.trials_left == (uint8_t)(299 & 0xFF));
    /* torn record write: newest stays the previous one */
    m.power_cut_after_bytes = 9;
    j.trials_left = 0x55;
    CHECK(fl_journal_store(&d, &j) == NOR_ERR_VERIFY);
    CHECK(fl_journal_load(&d, &j) == NOR_OK && j.seq == 300u);
    /* image header with good magic but bad header CRC is rejected */
    {
        uint32_t n; uint8_t *im = make_img(100, 1, 1, &n);
        im[24] ^= 1;   /* version byte changed after CRC */
        CHECK(nor_write_verified(&d, FL_SLOT_A, im, n) == NOR_OK);
        CHECK(fl_image_check(&d, FL_SLOT_A, FL_SLOT_LEN, 1, NULL) == FL_IMG_BAD_HDR_CRC);
        im[24] ^= 1;
        im[8] = 0xFF; im[9] = 0xFF; im[10] = 0xFF; im[11] = 0x7F;   /* absurd length (CRC fixed below) */
        {
            uint32_t c = arc1_crc32(0, im, 60);
            im[60] = (uint8_t)c; im[61] = (uint8_t)(c >> 8); im[62] = (uint8_t)(c >> 16); im[63] = (uint8_t)(c >> 24);
        }
        CHECK(nor_write_verified(&d, FL_SLOT_A, im, n) == NOR_OK);
        CHECK(fl_image_check(&d, FL_SLOT_A, FL_SLOT_LEN, 1, NULL) == FL_IMG_BAD_LEN);
        free(im);
    }
    nor_mock_free(&m);
}

void run_layout_tests(void)
{
    t_layout();
    t_ab_cycle();
    t_journal_power_fail();
}
