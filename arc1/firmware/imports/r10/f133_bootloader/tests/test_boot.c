/* ARC-1 R10 -- host tests of the F133 bootloader core (r10_boot.c) on the R08 NOR mock (64 MiB, W25Q512JV ID) and the
 * R8.5-C ECP5 sysCONFIG mock (IDCODE set to LFE5U-12). ARC1_MEMORY_R10 s7.1 gates "NOR / F133 boot" (host side),
 * "FPGA configuration" (12F path) and "Recovery" (A/B rollback, erased/bad slot, interrupted update). HOST_TESTED. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "r10_boot.h"
#include "flash_layout.h"
#include "crc32.h"
#include "nor_mock.h"
#include "ecp5_mock.h"

int g_fail, g_checks;
#define CHECK(c) do { g_checks++; if (!(c)) { g_fail++; printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)

static nor_mock m; static arc1_spi_hal h; static nor_dev d; static r10_boot B;
static ecp5_mock M; static ecp5_cfg C;
static uint8_t *stage;

static void setup(void)
{
    if (m.mem) nor_mock_free(&m);
    nor_mock_init(&m, R10_NOR_SIZE, 0xEF, 0x40, 0x20); nor_mock_hal(&m, &h);
    memset(&d, 0, sizeof d);
    CHECK(nor_init(&d, &h) == NOR_OK);
    memset(&B, 0, sizeof B);
    B.nor = &d; B.stage = stage; B.stage_cap = 2u << 20; B.fpga_abi = 3;
}
static void raw_write(uint32_t a, const uint8_t *p, uint32_t n) { CHECK(nor_write_verified(&d, a, p, n) == NOR_OK); }
static void raw_flip(uint32_t a)
{
    uint8_t sec[4096];
    uint32_t s = a & ~0xFFFu;
    CHECK(nor_read(&d, s, sec, sizeof sec) == NOR_OK);
    sec[a - s] ^= 0x01;
    raw_write(s, sec, sizeof sec);
}

static uint8_t *make_img(uint32_t payload, uint16_t kind, uint32_t version, uint32_t *total)
{
    uint8_t *b = malloc(payload + 64u);
    fl_img_hdr hd;
    uint32_t i;
    for (i = 0; i < payload; i++) b[64 + i] = (uint8_t)(i * 7u + version);
    memset(&hd, 0, sizeof hd);
    hd.magic = FL_IMG_MAGIC; hd.hdr_version = 1; hd.kind = kind; hd.img_len = payload;
    hd.img_crc32 = arc1_crc32(0, b + 64, payload); hd.load_addr = 0x40000000u; hd.entry = 0x40000000u; hd.version = version;
    fl_hdr_finalise(&hd);
    memset(b, 0, 64);
    for (i = 0; i < 4; i++) {
        b[0 + i] = (uint8_t)(hd.magic >> (8 * i)); b[8 + i] = (uint8_t)(hd.img_len >> (8 * i));
        b[12 + i] = (uint8_t)(hd.img_crc32 >> (8 * i)); b[16 + i] = (uint8_t)(hd.load_addr >> (8 * i));
        b[20 + i] = (uint8_t)(hd.entry >> (8 * i)); b[24 + i] = (uint8_t)(hd.version >> (8 * i));
        b[60 + i] = (uint8_t)(hd.hdr_crc32 >> (8 * i));
    }
    b[4] = 1; b[6] = (uint8_t)kind; b[7] = (uint8_t)(kind >> 8);
    *total = payload + 64u;
    return b;
}
/* ACFG container around a synthetic bitstream with the ecppack header layout and VERIFY_ID = idcode */
static uint8_t *make_fpga(uint32_t idcode, uint32_t bit_len, uint32_t seed, uint32_t *total, uint32_t *bit_crc)
{
    uint8_t head[] = { 0xFF, 0x00, 'P', 'a', 'r', 't', 0x00, 0xFF, 0xFF, 0xFF, 0xBD, 0xB3, 0xFF, 0xFF, 0xFF, 0xFF, 0x3B, 0, 0, 0,
                       0xE2, 0, 0, 0, 0, 0, 0, 0 };
    uint8_t *bit = malloc(bit_len), *f = malloc(bit_len + ACFG_HDR);
    uint32_t i, x = seed;
    head[24] = (uint8_t)(idcode >> 24); head[25] = (uint8_t)(idcode >> 16); head[26] = (uint8_t)(idcode >> 8); head[27] = (uint8_t)idcode;
    memcpy(bit, head, sizeof head);
    for (i = sizeof head; i < bit_len; i++) { x = x * 1103515245u + 12345u; bit[i] = (uint8_t)(x >> 16); }
    *bit_crc = arc1_crc32(0, bit, bit_len);
    *total = (uint32_t)ecp5_image_build_id(f, bit_len + ACFG_HDR, bit, bit_len, 3, 0, 0, idcode);
    free(bit);
    return f;
}
static int install(enum r10_comp c, const uint8_t *img, uint32_t n, uint32_t version)
{
    r10_update u;
    int rc = r10_update_begin(&B, c, &u);
    uint32_t a = n / 3, bpart = 7;
    if (rc) return rc;
    if ((rc = r10_update_write(&u, img, a)) != R10_OK) return rc;            /* uneven chunks */
    if ((rc = r10_update_write(&u, img + a, bpart)) != R10_OK) return rc;
    if ((rc = r10_update_write(&u, img + a + bpart, n - a - bpart)) != R10_OK) return rc;
    return r10_update_commit(&u, version);
}
static r10_manifest mf(void) { r10_manifest x; r10_manifest_load(&B, &x, NULL); return x; }
static void fpga_cfg_fresh(uint32_t good_crc)
{
    ecp5_gpio_hal io = mock_gpio;
    arc1_spi_hal spi = mock_spi;
    mock_init(&M, good_crc);
    M.idcode = R10_IDCODE_LFE5U_12;
    io.ctx = &M; spi.ctx = &M;
    ecp5_cfg_init(&C, &io, &spi);
}

int main(void)
{
    uint32_t n, n2, crc_app, crc_gold, crc_x;
    uint8_t *img, *img2, *app, *gold, *other;
    enum r10_slot s;
    ecp5_err e;
    r10_manifest x;
    int copy, k;
    stage = malloc(2u << 20);

    /* B01 layout and write permissions */
    setup();
    CHECK(r10_layout_check() == 0);
    CHECK(d.info.size_bytes == R10_NOR_SIZE && d.info.strategy == NOR_ADDR_4B_OPCODES);
    CHECK(!r10_write_allowed(r10_parts[R10P_F1BT].base, 4096) && !r10_write_allowed(r10_parts[R10P_F1RC].base, 4096));
    CHECK(!r10_write_allowed(r10_parts[R10P_C12G].base, 4096) && !r10_write_allowed(r10_parts[R10P_C45G].base, 4096));
    CHECK(!r10_write_allowed(r10_parts[R10P_META].base, 64));
    CHECK(r10_write_allowed(r10_parts[R10P_F1MA].base, 4096) && r10_write_allowed(r10_parts[R10P_D2FB].base, 4096));
    CHECK(!r10_write_allowed(r10_parts[R10P_F1MB].base - 16, 32));               /* spans two partitions */
    printf("TEST boot_layout done fails=%d\n", g_fail);

    /* B02 blank NOR: defaults, nothing to boot; rescue only -> fallback */
    r10_manifest_load(&B, &x, &copy);
    CHECK(copy == -1 && x.generation == 0 && x.c[R10C_F133].trial == 0xFF);
    CHECK(r10_select(&B, R10C_F133, &s) == R10_OK && s == R10S_NONE);
    img = make_img(300000, R10_IMG_KIND_RESCUE, 1, &n);
    raw_write(r10_parts[R10P_F1RC].base, img, n); free(img);                      /* factory programming */
    CHECK(r10_select(&B, R10C_F133, &s) == R10_OK && s == R10S_FALLBACK);
    printf("TEST boot_blank done fails=%d\n", g_fail);

    /* B03 A/B: install into B (trial, 3 attempts), unconfirmed -> rollback to A; confirmed -> active B */
    img = make_img(1000000, R10_IMG_KIND_F133, 1, &n);
    raw_write(r10_parts[R10P_F1MA].base, img, n); free(img);
    CHECK(r10_select(&B, R10C_F133, &s) == R10_OK && s == R10S_0);
    img = make_img(1500000, R10_IMG_KIND_F133, 2, &n);
    CHECK(install(R10C_F133, img, n, 2) == R10_OK);
    x = mf(); CHECK(x.c[R10C_F133].trial == 1 && x.c[R10C_F133].trials_left == 3 && x.c[R10C_F133].version[1] == 2);
    for (k = 0; k < 3; k++) { CHECK(r10_select(&B, R10C_F133, &s) == R10_OK && s == R10S_1); }
    CHECK(mf().c[R10C_F133].trials_left == 0);
    CHECK(r10_select(&B, R10C_F133, &s) == R10_OK && s == R10S_0);                 /* never confirmed: rollback */
    x = mf(); CHECK((x.c[R10C_F133].bad_mask & 2u) && x.c[R10C_F133].trial == 0xFF && x.c[R10C_F133].active == 0);
    CHECK(install(R10C_F133, img, n, 3) == R10_OK);
    CHECK(r10_select(&B, R10C_F133, &s) == R10_OK && s == R10S_1);
    CHECK(r10_confirm(&B, R10C_F133, R10S_1) == R10_OK);
    x = mf(); CHECK(x.c[R10C_F133].active == 1 && x.c[R10C_F133].trial == 0xFF && !(x.c[R10C_F133].bad_mask & 2u));
    k = (int)B.mf_writes;
    CHECK(r10_select(&B, R10C_F133, &s) == R10_OK && s == R10S_1 && (int)B.mf_writes == k);   /* no attempt consumed */
    free(img);
    printf("TEST boot_ab done fails=%d\n", g_fail);

    /* B04 manifest: two copies, newest wins, corrupt newest -> older, power cut during store -> previous kept */
    r10_manifest_load(&B, &x, &copy);
    {
        uint32_t g = x.generation, meta = r10_parts[R10P_META].base;
        r10_manifest y;
        int c2;
        CHECK(r10_manifest_store(&B, &x) == R10_OK);
        r10_manifest_load(&B, &y, &c2);
        CHECK(y.generation == g + 1 && c2 == 1 - copy);
        raw_flip(meta + (c2 ? R10_MF_COPY1 : 0) + 20);                            /* corrupt the newest record */
        r10_manifest_load(&B, &y, &copy);
        CHECK(copy == 1 - c2 && y.generation == g);
        r10_manifest_load(&B, &x, &copy);
        m.power_cut_after_bytes = 20;                                             /* cut while programming the record */
        CHECK(r10_manifest_store(&B, &x) != R10_OK);
        m.power_cut_after_bytes = 0;
        r10_manifest_load(&B, &y, &c2);
        CHECK(c2 == copy && y.generation == g && y.c[R10C_F133].active == 1);     /* previous state intact */
        CHECK(r10_manifest_store(&B, &x) == R10_OK);
        r10_manifest_load(&B, &y, &c2);
        CHECK(y.generation == g + 1);
    }
    printf("TEST boot_manifest done fails=%d\n", g_fail);

    /* B05 interrupted update and trial disarm: active B, update targets A */
    img = make_img(800000, R10_IMG_KIND_F133, 4, &n);
    CHECK(install(R10C_F133, img, n, 4) == R10_OK);                               /* A armed as trial */
    {
        r10_update u;
        CHECK(r10_update_begin(&B, R10C_F133, &u) == R10_OK && u.slot == 0);
        CHECK(mf().c[R10C_F133].trial == 0xFF);                                   /* disarmed before erase */
        CHECK(r10_update_write(&u, img, 200000) == R10_OK);
        m.power_cut_after_bytes = 100;
        CHECK(r10_update_write(&u, img + 200000, 100000) != R10_OK);             /* power cut mid-write */
        m.power_cut_after_bytes = 0;
        CHECK(r10_update_commit(&u, 5) == R10_E_IMAGE);                          /* half-written image refused */
    }
    CHECK(r10_select(&B, R10C_F133, &s) == R10_OK && s == R10S_1);                /* still the confirmed B */
    free(img);
    printf("TEST boot_interrupted done fails=%d\n", g_fail);

    /* B06 D213 images above 16 MiB (D2FA 0x1300000, D2FB 0x2300000); boot ROM view afterwards */
    img = make_img(4000000, R10_IMG_KIND_D213, 1, &n);
    CHECK(install(R10C_D213, img, n, 1) == R10_OK);                               /* active A -> goes to B */
    CHECK(m.upper_half_touched);
    CHECK(r10_select(&B, R10C_D213, &s) == R10_OK && s == R10S_1);
    CHECK(r10_confirm(&B, R10C_D213, R10S_1) == R10_OK);
    img2 = make_img(1000, R10_IMG_KIND_F133, 1, &n2);                             /* wrong kind in D213 slot */
    CHECK(install(R10C_D213, img2, n2, 2) == R10_E_IMAGE);
    CHECK(nor_prepare_reboot(&d) == NOR_OK && nor_mock_brom_read_ok(&m));
    free(img); free(img2);
    printf("TEST boot_d213 done fails=%d\n", g_fail);

    /* B07 12F: golden (factory) + application (update); app corrupt -> golden, app marked bad */
    gold = make_fpga(R10_IDCODE_LFE5U_12, 600913, 11, &n, &crc_gold);
    raw_write(r10_parts[R10P_C12G].base, gold, n);
    app = make_fpga(R10_IDCODE_LFE5U_12, 590000, 22, &n2, &crc_app);
    CHECK(install(R10C_C12, app, n2, 7) == R10_OK);
    CHECK(r10_select(&B, R10C_C12, &s) == R10_OK && s == R10S_0);
    fpga_cfg_fresh(crc_app);
    CHECK(r10_boot_fpga12(&B, &C, &s, &e) == R10_OK && s == R10S_0 && M.done);
    raw_flip(r10_parts[R10P_C12A].base + ACFG_HDR + 5000);
    fpga_cfg_fresh(crc_gold);
    CHECK(r10_boot_fpga12(&B, &C, &s, &e) == R10_OK && s == R10S_1 && M.done);
    CHECK(mf().c[R10C_C12].bad_mask & 1u);
    CHECK(r10_select(&B, R10C_C12, &s) == R10_OK && s == R10S_1);
    CHECK(install(R10C_C12, app, n2, 8) == R10_OK && !(mf().c[R10C_C12].bad_mask & 1u));
    printf("TEST boot_fpga12 done fails=%d\n", g_fail);

    /* B08 device-side failure of the application -> golden this boot, no persistent mark; both fail -> 12F down */
    fpga_cfg_fresh(crc_gold);                                                     /* the mock accepts only golden */
    CHECK(r10_boot_fpga12(&B, &C, &s, &e) == R10_OK && s == R10S_1);
    CHECK(!(mf().c[R10C_C12].bad_mask & 1u));
    fpga_cfg_fresh(0x12345678u);                                                  /* accepts neither */
    CHECK(r10_boot_fpga12(&B, &C, &s, &e) == R10_E_FPGA && s == R10S_NONE && e != ECP5_OK && !M.done);
    other = make_fpga(ECP5_IDCODE_LFE5U_45, 300000, 33, &n2, &crc_x);             /* 45F image in the 12F slot */
    CHECK(install(R10C_C12, other, n2, 9) == R10_E_IMAGE);
    CHECK(mf().c[R10C_C12].bad_mask & 1u);                                        /* begin marked the slot bad */
    fpga_cfg_fresh(crc_gold);
    CHECK(r10_boot_fpga12(&B, &C, &s, &e) == R10_OK && s == R10S_1);
    printf("TEST boot_fpga12_fail done fails=%d\n", g_fail);

    /* B09 45F images (sent to the D213): application, then golden when the application is corrupt */
    raw_write(r10_parts[R10P_C45G].base, other, n2);
    CHECK(r10_select(&B, R10C_C45, &s) == R10_OK && s == R10S_1);                 /* no application yet */
    CHECK(install(R10C_C45, other, n2, 1) == R10_OK);
    CHECK(r10_select(&B, R10C_C45, &s) == R10_OK && s == R10S_0);
    {
        ecp5_image im;
        CHECK(r10_fpga_stage(&B, R10C_C45, 0, &im) == R10_OK && im.idcode == ECP5_IDCODE_LFE5U_45 && im.bit_len == 300000);
        CHECK(r10_fpga_stage(&B, R10C_C12, 0, &im) == R10_E_IMAGE);              /* C12A still holds the 45F image */
    }
    raw_flip(r10_parts[R10P_C45A].base + 40);
    CHECK(r10_select(&B, R10C_C45, &s) == R10_OK && s == R10S_1);
    free(gold); free(app); free(other);
    printf("TEST boot_c45 done fails=%d\n", g_fail);

    printf("%d checks, %d failed\n", g_checks, g_fail);
    printf(g_fail ? "R10_BOOT_TEST_FAIL\n" : "R10_BOOT_TEST_PASS\n");
    nor_mock_free(&m); free(stage);
    return g_fail != 0;
}
