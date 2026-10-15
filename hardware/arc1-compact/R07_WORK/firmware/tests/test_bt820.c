/* ARC-1 Compact R07: BT820 host protocol tests (byte-exact wire frames,
 * memory-map validation, host-command rules, boot, command FIFO, faults).
 * HOST_TESTED against tests/mocks.c; the mock encodes AN086/DS_BT820 rules,
 * it is not the silicon. */
#include <string.h>

#include "bt820_gfx.h"
#include "bt820_regs.h"
#include "check.h"
#include "mocks.h"

static mock_bt820 g_m;
typedef struct { int reset_level; int reset_edges; uint64_t slept_ms; } plat_state;
static plat_state g_p;
static void p_reset(void *c, int lvl) { plat_state *p = (plat_state *)c; if (lvl != p->reset_level) p->reset_edges++; p->reset_level = lvl; }
static void p_delay(void *c, uint32_t ms) { ((plat_state *)c)->slept_ms += ms; g_m.now_us += 1000u * ms; }

static void fresh(bt820_dev *d, bt820_gfx *g) {
    arc1_spi_hal h = mbt_hal(&g_m);
    bt820_platform pl = {&g_p, p_reset, p_delay};
    mbt_init(&g_m);
    memset(&g_p, 0, sizeof g_p); g_p.reset_level = 1;
    CHECK(bt820_init(d, &h, 64, 128u << 20) == BT820_OK);
    if (g) CHECK(bt820_gfx_init(g, d, &pl, 1000) == BT820_GFX_OK);
}

static void booted(bt820_dev *d, bt820_gfx *g) {
    bt820_boot_cfg c;
    bt820_boot_report r;
    fresh(d, g);
    bt820_boot_cfg_default(&c);
    CHECK(bt820_boot(g, &c, &r) == BT820_GFX_OK);
}

static void test_wire_frames(void) {
    bt820_dev d; bt820_gfx g;
    uint32_t v = 0;
    booted(&d, &g);
    /* RAM_CMD write at 0x7F000000: FF 00 00 00 + LE word (R06 refused this) */
    CHECK(bt820_wr32(&d, BT820_RAM_CMD, 0x11223344u) == BT820_OK);
    {
        static const uint8_t want[8] = {0xFF, 0x00, 0x00, 0x00, 0x44, 0x33, 0x22, 0x11};
        CHECK(g_m.last_write.len == 8 && memcmp(g_m.last_write.bytes, want, 8) == 0);
        CHECK(g_m.ram_cmd[0] == 0x44 && g_m.ram_cmd[3] == 0x11);
    }
    /* REG_CMD_WRITE (core region 1) and REG_SYS_CFG (system region) framing */
    CHECK(bt820_wr32(&d, BT820_REG_PWM_DUTY, 0x80u) == BT820_OK);
    { static const uint8_t want[4] = {0xFF, 0x00, 0x61, 0x2C}; CHECK(memcmp(g_m.last_write.bytes, want, 4) == 0); }
    CHECK(bt820_wr32(&d, BT820_REG_SYS_CFG, 0u) == BT820_OK);
    { static const uint8_t want[4] = {0xFF, 0x80, 0x04, 0x20}; CHECK(memcmp(g_m.last_write.bytes, want, 4) == 0); }
    CHECK(bt820_wr32(&d, BT820_REG_CMDB_WRITE, BT820_CMD_DLSTART) == BT820_OK);
    { static const uint8_t want[4] = {0xFF, 0x01, 0x00, 0x00}; CHECK(memcmp(g_m.last_write.bytes, want, 4) == 0); }
    /* RAM_DL and RAM_G */
    CHECK(bt820_wr32(&d, BT820_RAM_DL, BT820_DL_DISPLAY) == BT820_OK);
    CHECK(bt820_wr32(&d, 0x00012344u, 0xCAFEF00Du) == BT820_OK);
    { static const uint8_t want[8] = {0x80, 0x01, 0x23, 0x44, 0x0D, 0xF0, 0xFE, 0xCA}; CHECK(memcmp(g_m.last_write.bytes, want, 8) == 0); }
    CHECK(bt820_read32(&d, 0x00012344u, &v) == BT820_OK && v == 0xCAFEF00Du);
    CHECK(bt820_read32(&d, BT820_REG_ID, &v) == BT820_OK && (v & 0xFFu) == 0x7Cu);
    CHECK(g_m.n_violations == 0);               /* none of these was taken for a host command */
    CHECK(g_m.n_cmds == 5);                     /* only the 5 boot configuration commands */
}

static void test_map_validation(void) {
    bt820_dev d;
    uint8_t b[8] = {0};
    fresh(&d, NULL);
    CHECK(bt820_span_valid(&d, BT820_RAM_CMD, 0x4000u));
    CHECK(!bt820_span_valid(&d, BT820_RAM_CMD + 0x3FFCu, 8));     /* crosses region end */
    CHECK(!bt820_span_valid(&d, 0x7F00C000u, 4));                 /* gap after RAM_DL */
    CHECK(!bt820_span_valid(&d, 0x7FE00000u, 4));                 /* host-command shadow, reserved */
    CHECK(!bt820_span_valid(&d, 0x7FEB0000u, 4));
    CHECK(!bt820_span_valid(&d, 0x7F800900u, 4));                 /* after REG_I2S */
    CHECK(!bt820_span_valid(&d, 0x7F010004u, 4));                 /* REG_CMDB_WRITE is one word */
    CHECK(bt820_span_valid(&d, (128u << 20) - 2621440u - 4u, 4)); /* last usable RAM_G word */
    CHECK(!bt820_span_valid(&d, (128u << 20) - 2621440u, 4));     /* reserved top 2.5 MiB */
    CHECK(!bt820_span_valid(&d, 0x00000102u, 4));                 /* unaligned */
    CHECK(!bt820_span_valid(&d, 0x00000100u, 6));
    CHECK(bt820_write(&d, 0x7FE00000u, b, 4) == BT820_ERR_ARG);
    CHECK(bt820_read(&d, 0x7F00C000u, b, 4) == BT820_ERR_ARG);
    CHECK(g_m.n_writes == 0 && g_m.n_reads == 0);                 /* rejected before the bus */
    CHECK(bt820_init(&d, &d.hal, 64, 1024u) == BT820_ERR_ARG);    /* RAM_G smaller than reserved area */
}

static void test_host_commands(void) {
    bt820_dev d;
    static const uint8_t codes[9] = {0xE0, 0xE1, 0xE2, 0xE4, 0xE6, 0xE7, 0xE8, 0xE9, 0xEB};
    fresh(&d, NULL);
    for (int i = 0; i < 9; i++) {
        int cfg = (codes[i] == 0xE4 || codes[i] == 0xE6 || codes[i] == 0xE8 || codes[i] == 0xE9 || codes[i] == 0xEB);
        bt820_note_hw_reset(&d);
        CHECK(bt820_host_command(&d, codes[i], cfg ? 0x5Au : 0u) == BT820_OK);
        CHECK(g_m.cmd_log[g_m.n_cmd_log - 1][0] == 0xFF && g_m.cmd_log[g_m.n_cmd_log - 1][1] == codes[i] &&
              g_m.cmd_log[g_m.n_cmd_log - 1][2] == (cfg ? 0x5A : 0) && g_m.cmd_log[g_m.n_cmd_log - 1][3] == 0 &&
              g_m.cmd_log[g_m.n_cmd_log - 1][4] == 0);
    }
    CHECK(bt820_host_command(&d, 0xE3u, 0) == BT820_ERR_ARG);     /* not in Table 3 */
    CHECK(bt820_host_command(&d, 0x00u, 0) == BT820_ERR_ARG);
    CHECK(bt820_host_command(&d, BT820_HC_SLEEP, 1) == BT820_ERR_ARG);  /* power cmds carry 0 */
    CHECK(bt820_host_active(&d) == BT820_OK && d.power == BT820_PWR_ACTIVE);
    CHECK(bt820_host_command(&d, BT820_HC_SETSYSCLKDIV, 0x17) == BT820_ERR_STATE);
    CHECK(bt820_host_command(&d, BT820_HC_STANDBY, 0) == BT820_OK && d.power == BT820_PWR_STANDBY);
    CHECK(bt820_host_command(&d, BT820_HC_SETSYSCLKDIV, 0x17) == BT820_OK);   /* low-power again */
    d.mode = BT820_BUS_QUAD;
    CHECK(bt820_host_command(&d, BT820_HC_SLEEP, 0) == BT820_ERR_MODE);
    CHECK(bt820_host_active(&d) == BT820_ERR_MODE);
    CHECK(g_m.n_violations == 0);
}

static void test_boot(void) {
    bt820_dev d; bt820_gfx g;
    bt820_boot_cfg c; bt820_boot_report r;
    static const uint8_t seq[6][5] = {{0xFF, 0xE9, 0xC1, 0, 0}, {0xFF, 0xE8, 0x80, 0, 0}, {0xFF, 0xEB, 0x08, 0, 0},
                                      {0xFF, 0xE9, 0xC0, 0, 0}, {0xFF, 0xE6, 0x17, 0, 0}, {0, 0, 0, 0, 0}};
    fresh(&d, &g);
    bt820_boot_cfg_default(&c);
    CHECK(bt820_boot(&g, &c, &r) == BT820_GFX_OK);
    CHECK(g_m.n_cmd_log == 6);
    for (int i = 0; i < 6; i++) CHECK(memcmp(g_m.cmd_log[i], seq[i], 5) == 0);   /* AN086 2.5 order */
    CHECK(g_p.reset_edges == 2 && g_p.reset_level == 1);
    CHECK(r.boot_status == BT820_BOOT_STATUS_RUN && r.chip_id == BT820_CHIP_ID_BT820B && (r.reg_id & 0xFF) == 0x7C);
    CHECK(r.polls_used == 3 && g_p.slept_ms >= 41u);
    CHECK(g_m.n_violations == 0);
    /* failure signatures */
    fresh(&d, &g); g_m.never_boots = 1;
    CHECK(bt820_boot(&g, &c, &r) == BT820_GFX_ERR_BOOT_TIMEOUT && r.polls_used == c.boot_polls);
    fresh(&d, &g); g_m.wrong_chip_id = 1;
    CHECK(bt820_boot(&g, &c, &r) == BT820_GFX_ERR_CHIP_ID && r.chip_id == 0x08150100u);
    fresh(&d, &g); g_m.never_valid = 1;
    CHECK(bt820_boot(&g, &c, &r) == BT820_GFX_ERR_BUS && r.bus_error == BT820_ERR_TIMEOUT);
    fresh(&d, &g); g_m.regs_r1[0] = 0x00u;
    CHECK(bt820_boot(&g, &c, &r) == BT820_GFX_ERR_REG_ID);
    fresh(&d, &g); g_m.regs_r1[0x88 / 4] = 1u;                     /* coprocessor held in reset */
    CHECK(bt820_boot(&g, &c, &r) == BT820_GFX_ERR_ENGINES);
}

static void test_fifo(void) {
    bt820_dev d; bt820_gfx g;
    static uint32_t many[5000];
    bt820_timing t;
    booted(&d, &g);
    CHECK(bt820_test_frame(&g, 0x10, 0x20, 0x30) == BT820_GFX_OK);
    CHECK(g_m.swaps == 1 && g_m.finishes == 1 && g_m.last_dl_len == 3);
    CHECK(g_m.last_dl[0] == BT820_DL_CLEAR_COLOR_RGB(0x10, 0x20, 0x30) && g_m.last_dl[1] == BT820_DL_CLEAR(1, 1, 1) &&
          g_m.last_dl[2] == BT820_DL_DISPLAY);
    CHECK(g_m.regs_r1[0x14C / 4] == g.wp);                      /* REG_CMD_READ caught up */
    /* 5000 words = 20000 bytes: wraps the 16 KiB ring */
    many[0] = BT820_CMD_DLSTART;
    for (int i = 1; i < 4999; i++) many[i] = BT820_DL_CLEAR_COLOR_RGB(i & 0xFF, 0, 0);
    many[4999] = BT820_CMD_SWAP;
    CHECK(bt820_cmd(&g, many, 5000) == BT820_GFX_OK && bt820_cmd_wait_idle(&g) == BT820_GFX_OK);
    CHECK(g_m.swaps == 2 && g_m.dl_len == 4096u);               /* mock DL capacity saturates */
    CHECK(g.words_sent == 6u + 5000u);
    /* scan-out configuration lands in the right registers */
    bt820_timing_candidate_1024x600(&t);
    CHECK(bt820_scanout_start(&g, &t) == BT820_GFX_OK);
    CHECK(g_m.regs_r1[0x8C / 4] == 1280 && g_m.regs_r1[0x94 / 4] == 1024 && g_m.regs_r1[0xA0 / 4] == 625 &&
          g_m.regs_r1[0xA8 / 4] == 600 && g_m.regs_r1[0x600 / 4] == 1 && g_m.regs_r1[0x5F8 / 4] == BT820_SWAPCHAIN_0);
    CHECK(g_m.regs_lvdstx[0] == BT820_LVDS_CH0_EN && g_m.rendertargets == 1);
    t.hsize = 1300;                                             /* hsize >= hcycle */
    CHECK(bt820_scanout_start(&g, &t) == BT820_GFX_ERR_ARG);
    CHECK(g_m.n_violations == 0);
    /* coprocessor fault and stall */
    booted(&d, &g); g_m.copro_fault_on_swap = 1;
    CHECK(bt820_test_frame(&g, 0, 0, 0) == BT820_GFX_ERR_COPRO_FAULT);
    booted(&d, &g); g_m.copro_stall = 1;
    CHECK(bt820_test_frame(&g, 0, 0, 0) == BT820_GFX_ERR_FIFO_TIMEOUT);
    booted(&d, &g); g_m.copro_stall = 1;
    for (int i = 0; i < 4096; i++) many[i] = 0x02000000u;       /* fill the ring without consumption */
    CHECK(bt820_cmd(&g, many, 4096) == BT820_GFX_ERR_FIFO_TIMEOUT);   /* only 4095 words fit */
}

void run_bt820_tests(void) {
    test_wire_frames();
    test_map_validation();
    test_host_commands();
    test_boot();
    test_fifo();
}
