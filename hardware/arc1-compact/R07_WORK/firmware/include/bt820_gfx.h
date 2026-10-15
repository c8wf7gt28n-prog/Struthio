/* ARC-1 Compact R07 -- BT820 bring-up and coprocessor command FIFO.
 *
 * Boot follows AN086 section 2.5 / EveApps EVE_Util_bootup: RST_N pulse,
 * BOOTCFGEN(allow) -> SETBOOTCFG -> SETDDRTYPE -> BOOTCFGEN(lock) ->
 * SETSYSCLKDIV -> ACTIVE -> 40 ms -> poll REG_BOOT_STATUS == 0x522E2E2E ->
 * REG_CHIP_ID == 0x08200100 -> REG_ID == 0x7C -> REG_CPURESET == 0.
 * The command FIFO uses RAM_CMD + REG_CMD_WRITE/REG_CMD_READ (AN086 5.x).
 * Scan-out follows AN086 2.14 (video timing, SWAPCHAIN_0, REG_SO_*) and the
 * EveApps Display_Config LVDS sequence; panel values are the R05 candidate
 * plan and are NOT confirmed against the panel (see BT820_HOST_PROTOCOL.md).
 * HOST_TESTED against a mock only; nothing here has lit a display. */
#ifndef BT820_GFX_H
#define BT820_GFX_H
#include "bt820_host.h"

enum bt820_gfx_error {
    BT820_GFX_OK = 0,
    BT820_GFX_ERR_BUS = 10,          /* + underlying bt820_error in detail */
    BT820_GFX_ERR_BOOT_TIMEOUT = 11, /* REG_BOOT_STATUS never 0x522E2E2E */
    BT820_GFX_ERR_CHIP_ID = 12,
    BT820_GFX_ERR_REG_ID = 13,
    BT820_GFX_ERR_ENGINES = 14,      /* REG_CPURESET stays non-zero */
    BT820_GFX_ERR_COPRO_FAULT = 15,  /* REG_CMD_READ == 0x3FFF */
    BT820_GFX_ERR_FIFO_TIMEOUT = 16, /* coprocessor did not consume */
    BT820_GFX_ERR_ARG = 17
};

typedef struct bt820_platform {
    void *ctx;
    void (*set_reset)(void *ctx, int level);   /* RST_N pin (F133 PD16) */
    void (*delay_ms)(void *ctx, uint32_t ms);
} bt820_platform;

typedef struct bt820_boot_cfg {
    uint8_t bootcfg;        /* SETBOOTCFG byte3: b7 DDR, b6 touch, b5 audio, b4 watchdog */
    uint8_t ddrtype;        /* SETDDRTYPE byte3: 0x08 = DDR3L 1 Gbit 1333 MT/s (MN820) */
    uint8_t sysclkdiv;      /* SETSYSCLKDIV byte3: 0x17 = 72 MHz at default PLL */
    uint32_t boot_polls;    /* REG_BOOT_STATUS polls, 10 ms apart */
} bt820_boot_cfg;

typedef struct bt820_boot_report {
    int result;
    int bus_error;
    uint32_t boot_status, chip_id, reg_id, cpureset;
    uint32_t polls_used;
} bt820_boot_report;

typedef struct bt820_timing {           /* EVE raster registers */
    uint16_t hcycle, hoffset, hsize, hsync0, hsync1;
    uint16_t vcycle, voffset, vsize, vsync0, vsync1;
    uint8_t pclk_pol;
    uint8_t so_mode;                    /* BT820_SO_* */
    uint8_t lvds_txclkdiv;              /* LVDSTX_PLLCFG clkdiv field */
    uint32_t sc0_ptr0, sc0_ptr1;        /* swap-chain buffers in RAM_G */
} bt820_timing;

typedef struct bt820_gfx {
    bt820_dev *dev;
    bt820_platform plat;
    uint32_t wp;                        /* host copy of REG_CMD_WRITE */
    uint32_t fifo_polls;                /* max REG_CMD_READ polls when waiting */
    uint64_t words_sent;
} bt820_gfx;

void bt820_boot_cfg_default(bt820_boot_cfg *c);
/* R05 candidate panel NHD-7.0-1024600AF-LSXP plan (UNCONFIRMED) */
void bt820_timing_candidate_1024x600(bt820_timing *t);

int bt820_gfx_init(bt820_gfx *g, bt820_dev *dev, const bt820_platform *plat, uint32_t fifo_polls);
int bt820_boot(bt820_gfx *g, const bt820_boot_cfg *c, bt820_boot_report *r);
int bt820_cmd(bt820_gfx *g, const uint32_t *words, size_t count);   /* append + kick */
int bt820_cmd_wait_idle(bt820_gfx *g);
int bt820_scanout_start(bt820_gfx *g, const bt820_timing *t);
/* CMD_DLSTART, CLEAR_COLOR_RGB, CLEAR(1,1,1), DISPLAY, CMD_SWAP, CMD_GRAPHICSFINISH */
int bt820_test_frame(bt820_gfx *g, uint8_t r, uint8_t gr, uint8_t b);
const char *bt820_gfx_error_string(int err);

#endif
