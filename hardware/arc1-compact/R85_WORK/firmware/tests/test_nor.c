/* Host tests for the R08 SPI NOR driver (HOST_TESTED, mock only). */
#include <stdlib.h>
#include <string.h>
#include "check.h"
#include "nor_mock.h"
#include "spi_nor.h"

static void fill(uint8_t *b, size_t n, uint32_t seed)
{
    size_t i;
    for (i = 0; i < n; i++) { seed = seed * 1103515245u + 12345u; b[i] = (uint8_t)(seed >> 16); }
}

static void t_probe_and_mode(void)
{
    nor_mock m; arc1_spi_hal h; nor_dev d;
    nor_mock_init(&m, 0x02000000u, 0xEF, 0x40, 0x19); nor_mock_hal(&m, &h);
    memset(&d, 0, sizeof d);
    CHECK(nor_init(&d, &h) == NOR_OK);
    CHECK(d.info.size_bytes == 0x02000000u);
    CHECK(d.info.sfdp_ok && d.info.sfdp_addr_bytes == 1 && d.info.sfdp_density_bits == 0x10000000u);
    CHECK(d.info.strategy == NOR_ADDR_4B_OPCODES);
    CHECK(m.n_resets == 1);
    CHECK(nor_mock_brom_read_ok(&m));          /* driver left 3-byte mode, EAR 0 */
    nor_mock_free(&m);

    /* device found in 4-byte mode with EAR=1 (e.g. left by a foreign tool): repaired */
    nor_mock_init(&m, 0x02000000u, 0xEF, 0x40, 0x19); nor_mock_hal(&m, &h);
    memset(&d, 0, sizeof d);
    m.adp = 0; m.four_byte_mode = 0;
    m.reset_enabled = 0;
    {   /* the software reset at init restores ADP mode; emulate a part where reset is ignored */
        nor_dev d2; memset(&d2, 0, sizeof d2);
        CHECK(nor_init(&d2, &h) == NOR_OK);
        m.four_byte_mode = 1; m.ear = 1;
        CHECK(nor_prepare_reboot(&d2) == NOR_OK);
        CHECK(nor_mock_brom_read_ok(&m));
        CHECK(m.n_ex4b >= 1);
    }
    /* ADP set (would power up in 4-byte mode): refuse, boot ROM risk */
    m.adp = 1;
    memset(&d, 0, sizeof d);
    CHECK(nor_init(&d, &h) == NOR_ERR_STATE);
    nor_mock_free(&m);
}

static void t_id_failures(void)
{
    nor_mock m; arc1_spi_hal h; nor_dev d;
    nor_mock_init(&m, 0x02000000u, 0xEF, 0x40, 0x19); nor_mock_hal(&m, &h);
    m.miso_stuck = 0x00; memset(&d, 0, sizeof d);
    CHECK(nor_init(&d, &h) == NOR_ERR_ID);         /* no device: pulled-down MISO */
    m.miso_stuck = 0xFF; memset(&d, 0, sizeof d);
    CHECK(nor_init(&d, &h) == NOR_ERR_ID);
    m.miso_stuck = -1;
    m.sfdp_density_bits = 0x08000000u;              /* SFDP says 16 MiB, JEDEC says 32 MiB */
    memset(&d, 0, sizeof d);
    CHECK(nor_init(&d, &h) == NOR_ERR_ID);
    nor_mock_free(&m);
    /* unknown 32 MiB part: refused rather than guessed */
    nor_mock_init(&m, 0x02000000u, 0xC2, 0x20, 0x19); nor_mock_hal(&m, &h);
    memset(&d, 0, sizeof d);
    CHECK(nor_init(&d, &h) == NOR_ERR_ID);
    nor_mock_free(&m);
    /* a 16 MiB part needs no 4-byte handling */
    nor_mock_init(&m, 0x01000000u, 0xEF, 0x40, 0x18); nor_mock_hal(&m, &h);
    memset(&d, 0, sizeof d);
    CHECK(nor_init(&d, &h) == NOR_OK && d.info.strategy == NOR_ADDR_3B_ONLY);
    {
        uint8_t b[4];
        CHECK(nor_read(&d, 0x00FFFFFCu, b, 4) == NOR_OK);
        CHECK(nor_read(&d, 0x00FFFFFEu, b, 4) == NOR_ERR_RANGE);
    }
    nor_mock_free(&m);
}

/* Lower and upper half must be distinct storage: the core addressing-trap test. */
static void t_full_capacity(int strategy_ear)
{
    nor_mock m; arc1_spi_hal h; nor_dev d;
    uint8_t *a = (uint8_t *)malloc(8192), *b = (uint8_t *)malloc(8192), *r = (uint8_t *)malloc(8192);
    uint32_t addrs[] = { 0x00000000u, 0x00FFE000u, 0x01000000u, 0x01FFE000u, 0x00800000u, 0x01800000u };
    size_t i;
    nor_mock_init(&m, 0x02000000u, 0xEF, 0x40, 0x19); nor_mock_hal(&m, &h);
    memset(&d, 0, sizeof d);
    if (strategy_ear) { m.has_4b_opcodes = 0; d.force_set = 1; d.force_strategy = NOR_ADDR_EAR; }
    CHECK(nor_init(&d, &h) == NOR_OK);
    for (i = 0; i < sizeof addrs / sizeof addrs[0]; i++) {
        fill(a, 8192, (uint32_t)(i * 77u + 1u));
        CHECK(nor_write_verified(&d, addrs[i], a, 8192) == NOR_OK);
    }
    for (i = 0; i < sizeof addrs / sizeof addrs[0]; i++) {
        fill(b, 8192, (uint32_t)(i * 77u + 1u));
        CHECK(nor_read(&d, addrs[i], r, 8192) == NOR_OK);
        CHECK(memcmp(r, b, 8192) == 0);
    }
    /* a read across the 16 MiB boundary */
    CHECK(nor_read(&d, 0x00FFF000u, r, 8192) == NOR_OK);
    fill(b, 8192, 77u * 1u + 1u);
    CHECK(memcmp(r, b + 4096, 4096) == 0);
    fill(b, 8192, 77u * 2u + 1u);
    CHECK(memcmp(r + 4096, b, 4096) == 0);
    CHECK(m.upper_half_touched);
    CHECK(nor_mock_brom_read_ok(&m));               /* after all that: still boot-ROM compatible */
    CHECK(nor_read(&d, 0x01FFFFFFu, r, 2) == NOR_ERR_RANGE);
    if (strategy_ear) CHECK(m.n_wrear > 0 && m.ear == 0);
    CHECK(m.page_wrap == 0 && m.prog_while_busy == 0 && m.prog_without_wel == 0);
    nor_mock_free(&m); free(a); free(b); free(r);
}

static void t_faults(void)
{
    nor_mock m; arc1_spi_hal h; nor_dev d;
    uint8_t a[300], r[300];
    nor_mock_init(&m, 0x02000000u, 0xEF, 0x40, 0x19); nor_mock_hal(&m, &h);
    memset(&d, 0, sizeof d);
    CHECK(nor_init(&d, &h) == NOR_OK);
    fill(a, sizeof a, 9);
    /* unaligned page start: program must split at the page boundary */
    CHECK(nor_erase_sector(&d, 0x00010000u) == NOR_OK);
    CHECK(nor_program(&d, 0x000100F0u, a, sizeof a) == NOR_OK);
    CHECK(nor_read(&d, 0x000100F0u, r, sizeof r) == NOR_OK && memcmp(a, r, sizeof a) == 0);
    CHECK(m.page_wrap == 0);
    CHECK(nor_erase_sector(&d, 0x00010001u) == NOR_ERR_ALIGN);
    /* stuck busy -> timeout, never an endless loop */
    m.stuck_busy = 1;
    CHECK(nor_erase_sector(&d, 0x00020000u) == NOR_ERR_TIMEOUT);
    m.stuck_busy = 0;
    m.wel = 0;   /* the refused (busy) erase left WEL set, as on the real part */
    /* protection: WEL never sets -> refused, nothing programmed */
    m.wel_never_sets = 1;
    CHECK(nor_program(&d, 0x00020000u, a, 16) == NOR_ERR_PROTECTED);
    m.wel_never_sets = 0;
    /* power cut during program -> verify catches it */
    m.power_cut_after_bytes = 10;
    CHECK(nor_write_verified(&d, 0x00030000u, a, 64) == NOR_ERR_VERIFY);
    /* not initialised */
    { nor_dev z; memset(&z, 0, sizeof z); CHECK(nor_read(&z, 0, r, 1) == NOR_ERR_STATE); }
    nor_mock_free(&m);
}

void run_nor_tests(void)
{
    t_probe_and_mode();
    t_id_failures();
    t_full_capacity(0);
    t_full_capacity(1);
    t_faults();
}
