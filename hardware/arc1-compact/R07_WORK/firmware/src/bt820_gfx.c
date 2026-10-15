/* ARC-1 Compact R07 -- BT820 bring-up and command FIFO (see header). */
#include "bt820_gfx.h"

#include <string.h>

#include "bt820_regs.h"

void bt820_boot_cfg_default(bt820_boot_cfg *c) {
    c->bootcfg = 0x80u;        /* DDR only; touch/audio/watchdog off (AN086 default) */
    c->ddrtype = 0x08u;        /* DDR3L, 1 Gbit, 1333 MT/s (AN086 Table 5 default) */
    c->sysclkdiv = 0x17u;      /* 72 MHz (AN086 Code Snippet 1) */
    c->boot_polls = 100u;      /* EveApps uses 100 x 10 ms */
}

void bt820_timing_candidate_1024x600(bt820_timing *t) {
    /* R05_BASELINE/display/compact_display.json: 1280 x 625 at 48 MHz, back
     * porch printed including sync. EVE mapping: sync at 0, active starts at
     * the back-porch end. INTERPRETATION_STATUS: requires panel confirmation. */
    memset(t, 0, sizeof(*t));
    t->hcycle = 1280; t->hsync0 = 0; t->hsync1 = 16; t->hoffset = 160; t->hsize = 1024;
    t->vcycle = 625;  t->vsync0 = 0; t->vsync1 = 1;  t->voffset = 23;  t->vsize = 600;
    t->pclk_pol = 0;
    t->so_mode = BT820_SO_ONE_PIXEL_SINGLE_LVDS;   /* R05 bt_so_mode_candidate 0 */
    t->lvds_txclkdiv = 5;                          /* R05 txclkdiv */
    t->sc0_ptr0 = 36u << 20;                       /* EveApps SC0_PTR0_STARTADDR */
    t->sc0_ptr1 = 45u << 20;                       /* EveApps SC0_PTR1_STARTADDR */
}

int bt820_gfx_init(bt820_gfx *g, bt820_dev *dev, const bt820_platform *plat, uint32_t fifo_polls) {
    if (!g || !dev || !plat || !plat->set_reset || !plat->delay_ms || fifo_polls == 0u) return BT820_GFX_ERR_ARG;
    memset(g, 0, sizeof(*g));
    g->dev = dev;
    g->plat = *plat;
    g->fifo_polls = fifo_polls;
    return BT820_GFX_OK;
}

#define BUS(expr) do { int rc_ = (expr); if (rc_) { if (r) r->bus_error = rc_; return (r ? (r->result = BT820_GFX_ERR_BUS) : BT820_GFX_ERR_BUS); } } while (0)

int bt820_boot(bt820_gfx *g, const bt820_boot_cfg *c, bt820_boot_report *r) {
    bt820_boot_report local;
    uint32_t i;
    if (!g || !c) return BT820_GFX_ERR_ARG;
    if (!r) r = &local;
    memset(r, 0, sizeof(*r));
    /* 1. full chip reset through RST_N (AN086 2.5 step 1; 1 ms as in the guide) */
    g->plat.set_reset(g->plat.ctx, 0);
    g->plat.delay_ms(g->plat.ctx, 1);
    g->plat.set_reset(g->plat.ctx, 1);
    bt820_note_hw_reset(g->dev);
    /* 2. configuration host commands, valid only in the low-power state */
    BUS(bt820_host_command(g->dev, BT820_HC_BOOTCFGEN, 0xC1u));
    BUS(bt820_host_command(g->dev, BT820_HC_SETBOOTCFG, c->bootcfg));
    BUS(bt820_host_command(g->dev, BT820_HC_SETDDRTYPE, c->ddrtype));
    BUS(bt820_host_command(g->dev, BT820_HC_BOOTCFGEN, 0xC0u));
    BUS(bt820_host_command(g->dev, BT820_HC_SETSYSCLKDIV, c->sysclkdiv));
    /* 3. ACTIVE, 4. wait for boot status */
    BUS(bt820_host_active(g->dev));
    g->plat.delay_ms(g->plat.ctx, 40);
    for (i = 0; i < c->boot_polls; i++) {
        BUS(bt820_read32(g->dev, BT820_REG_BOOT_STATUS, &r->boot_status));
        r->polls_used = i + 1u;
        if (r->boot_status == BT820_BOOT_STATUS_RUN) break;
        g->plat.delay_ms(g->plat.ctx, 10);
    }
    if (r->boot_status != BT820_BOOT_STATUS_RUN) return r->result = BT820_GFX_ERR_BOOT_TIMEOUT;
    BUS(bt820_read32(g->dev, BT820_REG_CHIP_ID, &r->chip_id));
    if (r->chip_id != BT820_CHIP_ID_BT820B) return r->result = BT820_GFX_ERR_CHIP_ID;
    BUS(bt820_read32(g->dev, BT820_REG_ID, &r->reg_id));
    if ((r->reg_id & 0xFFu) != BT820_REG_ID_VALUE) return r->result = BT820_GFX_ERR_REG_ID;
    for (i = 0; i < 100u; i++) {
        BUS(bt820_read32(g->dev, BT820_REG_CPURESET, &r->cpureset));
        if ((r->cpureset & 7u) == 0u) break;
        g->plat.delay_ms(g->plat.ctx, 20);
    }
    if (r->cpureset & 7u) return r->result = BT820_GFX_ERR_ENGINES;
    /* coprocessor FIFO pointers start equal after reset */
    {
        uint32_t wp = 0;
        BUS(bt820_read32(g->dev, BT820_REG_CMD_WRITE, &wp));
        g->wp = wp & (BT820_RAM_CMD_SIZE - 1u);
    }
    return r->result = BT820_GFX_OK;
}

static int read_rp(bt820_gfx *g, uint32_t *rp) {
    int rc = bt820_read32(g->dev, BT820_REG_CMD_READ, rp);
    if (rc) return BT820_GFX_ERR_BUS;
    *rp &= 0x3FFFu;
    return (*rp == BT820_CMD_FAULT) ? BT820_GFX_ERR_COPRO_FAULT : BT820_GFX_OK;
}

int bt820_cmd(bt820_gfx *g, const uint32_t *words, size_t count) {
    size_t done = 0;
    if (!g || !words || count == 0u) return BT820_GFX_ERR_ARG;
    while (done < count) {
        uint32_t rp = 0, free_b, polls = 0;
        size_t chunk, until_wrap;
        int rc;
        for (;;) {
            rc = read_rp(g, &rp);
            if (rc) return rc;
            free_b = (rp - g->wp - 4u) & (BT820_RAM_CMD_SIZE - 1u);   /* one word kept empty */
            if (free_b >= 4u) break;
            if (++polls >= g->fifo_polls) return BT820_GFX_ERR_FIFO_TIMEOUT;
        }
        chunk = free_b / 4u;
        if (chunk > count - done) chunk = count - done;
        until_wrap = (BT820_RAM_CMD_SIZE - g->wp) / 4u;
#ifdef MUTANT_NO_WRAP
        (void)until_wrap;                                       /* verification mutant */
#else
        if (chunk > until_wrap) chunk = until_wrap;
#endif
        if (bt820_write32(g->dev, BT820_RAM_CMD + g->wp, words + done, chunk)) return BT820_GFX_ERR_BUS;
        g->wp = (g->wp + 4u * (uint32_t)chunk) & (BT820_RAM_CMD_SIZE - 1u);
        if (bt820_wr32(g->dev, BT820_REG_CMD_WRITE, g->wp)) return BT820_GFX_ERR_BUS;
        done += chunk;
        g->words_sent += chunk;
    }
    return BT820_GFX_OK;
}

int bt820_cmd_wait_idle(bt820_gfx *g) {
    uint32_t rp = 0, polls = 0;
    int rc;
    if (!g) return BT820_GFX_ERR_ARG;
    for (;;) {
        rc = read_rp(g, &rp);
        if (rc) return rc;
        if (rp == g->wp) return BT820_GFX_OK;
        if (++polls >= g->fifo_polls) return BT820_GFX_ERR_FIFO_TIMEOUT;
    }
}

int bt820_scanout_start(bt820_gfx *g, const bt820_timing *t) {
    const struct { uint32_t reg, val; } seq[] = {
        /* video timing (AN086 2.14 step 1; EveApps EVE_Util_config order) */
        {BT820_REG_HCYCLE, t->hcycle}, {BT820_REG_HOFFSET, t->hoffset},
        {BT820_REG_HSYNC0, t->hsync0}, {BT820_REG_HSYNC1, t->hsync1},
        {BT820_REG_VCYCLE, t->vcycle}, {BT820_REG_VOFFSET, t->voffset},
        {BT820_REG_VSYNC0, t->vsync0}, {BT820_REG_VSYNC1, t->vsync1},
        {BT820_REG_PCLK_POL, t->pclk_pol}, {BT820_REG_HSIZE, t->hsize}, {BT820_REG_VSIZE, t->vsize},
        {BT820_REG_DISP, 1u},
        /* LVDS TX (EveApps Display_Config: cps 0, lock 0x180, cks 2 if div<=4 else 1, ns 7) */
        {BT820_REG_LVDSTX_PLLCFG, BT820_LVDSTX_PLLCFG(0u, 0x180u, (t->lvds_txclkdiv > 4u) ? 1u : 2u, 7u, t->lvds_txclkdiv)},
        {BT820_REG_LVDSTX_EN, BT820_LVDS_CH0_EN},
        /* swap chain 0 (AN086 2.14 steps 2-4) */
        {BT820_REG_SC0_SIZE, 2u}, {BT820_REG_SC0_PTR0, t->sc0_ptr0}, {BT820_REG_SC0_PTR1, t->sc0_ptr1},
        {BT820_REG_SO_MODE, t->so_mode}, {BT820_REG_SO_SOURCE, BT820_SWAPCHAIN_0},
        {BT820_REG_SO_FORMAT, BT820_FMT_RGB8}, {BT820_REG_SO_EN, 1u},
    };
    size_t i;
    if (!g || !t || t->hsize >= t->hcycle || t->vsize >= t->vcycle || t->hsize > 2047u || t->vsize > 2047u)
        return BT820_GFX_ERR_ARG;
    for (i = 0; i < sizeof seq / sizeof seq[0]; i++)
        if (bt820_wr32(g->dev, seq[i].reg, seq[i].val)) return BT820_GFX_ERR_BUS;
    {   /* render target = swap chain 0 (EveApps scanout_swapping) */
        const uint32_t rt[4] = {BT820_CMD_RENDERTARGET, BT820_SWAPCHAIN_0,
                                (uint32_t)BT820_FMT_RGB8 | ((uint32_t)t->hsize << 16), (uint32_t)t->vsize};
        int rc = bt820_cmd(g, rt, 4);
        if (rc) return rc;
    }
    return bt820_cmd_wait_idle(g);
}

int bt820_test_frame(bt820_gfx *g, uint8_t r, uint8_t gr, uint8_t b) {
    uint32_t w[6];
    int rc;
    w[0] = BT820_CMD_DLSTART;
    w[1] = BT820_DL_CLEAR_COLOR_RGB(r, gr, b);
    w[2] = BT820_DL_CLEAR(1, 1, 1);
    w[3] = BT820_DL_DISPLAY;
    w[4] = BT820_CMD_SWAP;
    w[5] = BT820_CMD_GRAPHICSFINISH;
    rc = bt820_cmd(g, w, 6);
    return rc ? rc : bt820_cmd_wait_idle(g);
}

const char *bt820_gfx_error_string(int err) {
    switch (err) {
    case BT820_GFX_OK: return "ok";
    case BT820_GFX_ERR_BUS: return "SPI/host-layer error (see bus_error)";
    case BT820_GFX_ERR_BOOT_TIMEOUT: return "REG_BOOT_STATUS never reached 0x522E2E2E";
    case BT820_GFX_ERR_CHIP_ID: return "REG_CHIP_ID is not 0x08200100 (BT820B)";
    case BT820_GFX_ERR_REG_ID: return "REG_ID is not 0x7C";
    case BT820_GFX_ERR_ENGINES: return "REG_CPURESET did not clear";
    case BT820_GFX_ERR_COPRO_FAULT: return "coprocessor fault (REG_CMD_READ = 0x3FFF)";
    case BT820_GFX_ERR_FIFO_TIMEOUT: return "coprocessor did not consume the command FIFO";
    case BT820_GFX_ERR_ARG: return "invalid argument";
    default: return "unknown";
    }
}
