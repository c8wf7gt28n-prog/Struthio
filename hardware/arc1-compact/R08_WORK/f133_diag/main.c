/* ARC-1 Compact R08 -- F133 diagnostic boot image (BUILD-ONLY: never executed on silicon).
 *
 * Intended to be the boot0 in the 32 MiB NOR (offset 0, BOOT-SEL 00) or, for the
 * first article, loaded over USB FEL into SRAM. It separates the failure classes
 * the R08 handoff asks for, each with a printed signature:
 *   S0 CPU/boot: banner, BOOT_SEL pad status (expect 00), eFuse select, fast-boot
 *   S1 power:    USB-C advertised current (TUSB320 OUT1/OUT2), VBUS sense
 *   S2 NOR:      JEDEC/SFDP probe, 3-byte mode check, eGON magic at 0, upper-half
 *                read (16 MiB+), A/B/recovery image headers (READ-ONLY: no journal write)
 *   S3 BT820:    boot + REG_CHIP_ID/REG_ID + scan-out + test frame (R07 host-tested driver)
 *   S4 T35:      power on (1V2 -> PG -> 3V3_T35), release CRESET_N, wait CDONE
 *   S5 mailbox:  enable SPI0 isolation, read MAGIC/VERSION; PSRAM power request,
 *                POWER_ON/READY, BIST; CPU fallback is reported, never fatal
 * Pin numbers come from include/board_pins_r08.h, generated from the schematic. */
#include <stddef.h>
#include <stdint.h>

#include "board_pins_r08.h"
#include "bt820_gfx.h"
#include "bt820_regs.h"
#include "f133_regs.h"
#include "flash_layout.h"
#include "spi_nor.h"

void *memset(void *d, int c, size_t n) { uint8_t *p = d; while (n--) *p++ = (uint8_t)c; return d; }
void *memcpy(void *d, const void *s, size_t n) { uint8_t *p = d; const uint8_t *q = s; while (n--) *p++ = *q++; return d; }
int memcmp(const void *a, const void *b, size_t n)
{
    const uint8_t *x = a, *y = b;
    for (; n; n--, x++, y++) if (*x != *y) return *x < *y ? -1 : 1;
    return 0;
}

/* ---------------- time (mcycle, assumed <= 1.2 GHz: delays only get longer) ---------------- */
static uint64_t cycles(void) { uint64_t c; __asm__ volatile("csrr %0, mcycle" : "=r"(c)); return c; }
#define ASSUMED_MAX_HZ 1200000000ull
static void delay_us(uint32_t us)
{
    uint64_t t0 = cycles(), n = (ASSUMED_MAX_HZ / 1000000ull) * us;
    while (cycles() - t0 < n) { }
}
static uint64_t now_us(void *ctx) { (void)ctx; return cycles() / (ASSUMED_MAX_HZ / 1000000ull); }

/* ---------------- GPIO by board pin id ---------------- */
#define PPORT(p) ((p) / 32u)
#define PIDX(p)  ((p) % 32u)
static void gpio_func(uint32_t pin, uint32_t fn)
{
    uint32_t a = GPIO_CFG(PPORT(pin), PIDX(pin) / 8u), sh = (PIDX(pin) % 8u) * 4u;
    REG32(a) = (REG32(a) & ~(0xFu << sh)) | ((fn & 0xFu) << sh);
}
static void gpio_set(uint32_t pin, int v)
{
    uint32_t a = GPIO_DAT(PPORT(pin));
    REG32(a) = v ? (REG32(a) | (1u << PIDX(pin))) : (REG32(a) & ~(1u << PIDX(pin)));
}
static int gpio_get(uint32_t pin) { return (int)((REG32(GPIO_DAT(PPORT(pin))) >> PIDX(pin)) & 1u); }
static void gpio_out(uint32_t pin, int v) { gpio_set(pin, v); gpio_func(pin, 1); }
static void gpio_in(uint32_t pin) { gpio_func(pin, 0); }

/* ---------------- UART0 (PE2/PE3 F6) ---------------- */
static void uart_init(void)
{
    gpio_func(PIN_UART0_TX, 6);
    gpio_func(PIN_UART0_RX, 6);
    REG32(CCU_UART_BGR) |= (1u << 0);
    REG32(CCU_UART_BGR) |= (1u << 16);
    REG32(UART0_BASE + UART_LCR) = 0x83u;
    REG32(UART0_BASE + UART_DLL) = 13u;       /* 24 MHz / (16*13) = 115384 baud */
    REG32(UART0_BASE + UART_DLH) = 0u;
    REG32(UART0_BASE + UART_LCR) = 0x03u;
    REG32(UART0_BASE + UART_FCR) = 0x07u;
}
static void putc_(char c)
{
    while (!(REG32(UART0_BASE + UART_LSR) & (1u << 5))) { }
    REG32(UART0_BASE + UART_THR) = (uint32_t)(uint8_t)c;
}
static void puts_(const char *s) { while (*s) { if (*s == '\n') putc_('\r'); putc_(*s++); } }
static void puthex(uint32_t v)
{
    static const char h[] = "0123456789abcdef";
    puts_("0x");
    for (int i = 7; i >= 0; i--) putc_(h[(v >> (4 * i)) & 0xFu]);
}
static void kv(const char *k, uint32_t v) { puts_(k); puthex(v); puts_("\n"); }

/* ---------------- shared SPI engine (SPI0 and SPI1 have the same register map) ---------------- */
typedef struct { uint32_t base; uint32_t cs_gpio; int use_gpio_cs; } spi_port;

static void spi_init(uint32_t base, uint32_t clkreg, uint32_t bgr_bit)
{
    REG32(CCU_SPI_BGR) |= (1u << bgr_bit);
    REG32(CCU_SPI_BGR) |= (1u << (bgr_bit + 16u));
    REG32(clkreg) = (1u << 31) | (0u << 24) | (0u << 8) | 2u;   /* HOSC/3 = 8 MHz */
    REG32(base + SPI_GCR) = (1u << 31);
    while (REG32(base + SPI_GCR) & (1u << 31)) { }
    REG32(base + SPI_GCR) = (1u << 7) | (1u << 1) | 1u;          /* TP_EN, master, enable */
    REG32(base + SPI_TCR) = (1u << 13) | (1u << 7) | (1u << 6) | (1u << 2);   /* mode 0, SW CS high */
    REG32(base + SPI_FCR) = (1u << 31) | (1u << 15);
}
static void spi_select(void *ctx, int asserted)
{
    spi_port *p = (spi_port *)ctx;
    if (p->use_gpio_cs) {
        gpio_set(p->cs_gpio, !asserted);
    } else {
        uint32_t t = REG32(p->base + SPI_TCR);
        REG32(p->base + SPI_TCR) = asserted ? (t & ~(1u << 7)) : (t | (1u << 7));
    }
    if (!asserted) delay_us(1);
}
static int spi_transfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t n)
{
    spi_port *p = (spi_port *)ctx;
    while (n) {
        uint32_t k = n > 64u ? 64u : (uint32_t)n, i;
        uint64_t t0;
        REG32(p->base + SPI_MBC) = k;
        REG32(p->base + SPI_MTC) = k;
        REG32(p->base + SPI_BCC) = k;
        for (i = 0; i < k; i++) REG8(p->base + SPI_TXD) = tx ? tx[i] : 0u;
        REG32(p->base + SPI_ISR) = 0xFFFFFFFFu;
        REG32(p->base + SPI_TCR) |= (1u << 31);
        t0 = cycles();
        while (!(REG32(p->base + SPI_ISR) & (1u << 12))) {
            if (cycles() - t0 > ASSUMED_MAX_HZ) return -1;
        }
        for (i = 0; i < k; i++) {
            uint8_t b = REG8(p->base + SPI_RXD);
            if (rx) rx[i] = b;
        }
        if (tx) tx += k;
        if (rx) rx += k;
        n -= k;
    }
    return 0;
}

static spi_port g_spi0_nor = { SPI0_BASE, 0, 0 };
static spi_port g_spi0_t35 = { SPI0_BASE, PIN_T35_SS_N_F, 1 };
static spi_port g_spi1_bt = { SPI1_BASE, 0, 0 };

/* ---------------- results ---------------- */
enum { R_OK = 0, R_FAIL = 1, R_SKIP = 2 };
static const char *rs(int r) { return r == R_OK ? "OK" : r == R_FAIL ? "FAIL" : "SKIP"; }

/* S2 */
static nor_dev g_nor;
static int stage_nor(void)
{
    arc1_spi_hal hal = { &g_spi0_nor, spi_select, spi_transfer, now_us };
    uint8_t b[16], sr3 = 0xFF;
    int rc, ok = 1;
    fl_journal j;
    static const char *const st[] = { "OK", "BLANK", "BAD_MAGIC", "BAD_HDR_CRC", "BAD_LEN", "BAD_CRC", "IO" };
    gpio_out(PIN_T35_BUS_EN_N, 1);          /* T35 isolation buffers OFF while the NOR is used */
    gpio_out(PIN_T35_SS_N_F, 1);
    for (uint32_t p = PIN_SPI0_CLK_F; p <= PIN_SPI0_MISO; p++) gpio_func(p, 2);
    spi_init(SPI0_BASE, CCU_SPI0_CLK, 0);
    memset(&g_nor, 0, sizeof g_nor);
    rc = nor_init(&g_nor, &hal);
    kv("S2 nor_init            = ", (uint32_t)rc);
    kv("   JEDEC mfr/dev        = ", ((uint32_t)g_nor.info.mfr << 16) | g_nor.info.dev);
    kv("   size bytes           = ", g_nor.info.size_bytes);
    kv("   SFDP ok/addr-bytes   = ", ((uint32_t)g_nor.info.sfdp_ok << 8) | (uint32_t)g_nor.info.sfdp_addr_bytes);
    kv("   strategy             = ", (uint32_t)g_nor.info.strategy);
    kv("   found 4B / EAR!=0    = ", ((uint32_t)g_nor.info.found_in_4b_mode << 8) | (uint32_t)g_nor.info.found_ear_nonzero);
    if (rc) return R_FAIL;
    (void)nor_read_sr3(&g_nor, &sr3);
    kv("   SR3 (ADS b0, ADP b1) = ", sr3);
    if (nor_read(&g_nor, 0, b, 16) == NOR_OK) {
        kv("   boot0 +4 'eGON'      = ", (uint32_t)b[4] | ((uint32_t)b[5] << 8) | ((uint32_t)b[6] << 16) | ((uint32_t)b[7] << 24));
        if (memcmp(b + 4, "eGON.BT0", 8) != 0) { puts_("   WARN boot0 magic absent (running from FEL?)\n"); }
    } else ok = 0;
    if (nor_read(&g_nor, FL_TESTBLOCK, b, 16) == NOR_OK) kv("   upper-half word      = ", (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24));
    else ok = 0;
    kv("   layout check         = ", (uint32_t)fl_layout_check(g_nor.info.size_bytes));
    if (fl_journal_load(&g_nor, &j) == NOR_OK) {
        kv("   journal seq          = ", j.seq);
        kv("   active/trial/left    = ", ((uint32_t)j.active << 16) | ((uint32_t)j.trial << 8) | j.trials_left);
    }
    puts_("   slot A: "); puts_(st[fl_image_check(&g_nor, FL_SLOT_A, FL_SLOT_LEN, 1, NULL)]); puts_("\n");
    puts_("   slot B: "); puts_(st[fl_image_check(&g_nor, FL_SLOT_B, FL_SLOT_LEN, 1, NULL)]); puts_("\n");
    puts_("   recovery: "); puts_(st[fl_image_check(&g_nor, FL_RECOVERY, FL_RECOVERY_LEN, 2, NULL)]); puts_("\n");
    if (nor_prepare_reboot(&g_nor) != NOR_OK) ok = 0;   /* leave it as the boot ROM expects */
    return ok ? R_OK : R_FAIL;
}

/* S3 */
static void bt_reset(void *ctx, int level) { (void)ctx; gpio_set(PIN_BT_RST_N_F, level); }
static void bt_delay(void *ctx, uint32_t ms) { (void)ctx; while (ms--) delay_us(1000); }
static bt820_dev g_dev;
static bt820_gfx g_gfx;
static int stage_bt820(void)
{
    arc1_spi_hal hal = { &g_spi1_bt, spi_select, spi_transfer, now_us };
    bt820_platform plat = { 0, bt_reset, bt_delay };
    bt820_boot_cfg cfg;
    bt820_boot_report rep;
    bt820_timing tim;
    int rc;
    gpio_out(PIN_MN_PWR_EN, 1);                         /* module supply on (also the board default) */
    gpio_out(PIN_BT_RST_N_F, 0);
    gpio_in(PIN_BT_INT_N);
    gpio_func(PIN_BT_SS_N, 4); gpio_func(PIN_BT_SCK_F, 4); gpio_func(PIN_BT_MOSI_F, 4); gpio_func(PIN_BT_MISO, 4);
    spi_init(SPI1_BASE, CCU_SPI1_CLK, 1);
    if (bt820_init(&g_dev, &hal, 64, 128u << 20) || bt820_gfx_init(&g_gfx, &g_dev, &plat, 100000)) return R_FAIL;
    bt820_boot_cfg_default(&cfg);
    rc = bt820_boot(&g_gfx, &cfg, &rep);
    kv("S3 bt820_boot          = ", (uint32_t)rc);
    kv("   REG_BOOT_STATUS      = ", rep.boot_status);
    kv("   REG_CHIP_ID          = ", rep.chip_id);
    kv("   REG_ID               = ", rep.reg_id);
    puts_("   "); puts_(bt820_gfx_error_string(rc)); puts_("\n");
    if (rc != BT820_GFX_OK) return R_FAIL;
    bt820_timing_candidate_1024x600(&tim);             /* CANDIDATE: panel is an R09 decision */
    kv("   scanout_start        = ", (uint32_t)bt820_scanout_start(&g_gfx, &tim));
    kv("   test_frame           = ", (uint32_t)bt820_test_frame(&g_gfx, 0x00, 0x40, 0xC0));
    return R_OK;
}

/* S4 */
static int stage_t35_config(void)
{
    uint32_t t;
    gpio_out(PIN_PSRAM_PWR_REQ, 0);
    gpio_out(PIN_T35_CRESET_N_F, 0);
    gpio_in(PIN_T35_CDONE);
    gpio_out(PIN_T35_PWR_EN, 1);                       /* 1V2 -> PG -> 3V3_T35 (hardware sequenced) */
    delay_us(20000);
    gpio_set(PIN_T35_CRESET_N_F, 1);                   /* active configuration from the T35 SPI flash */
    for (t = 0; t < 2000 && !gpio_get(PIN_T35_CDONE); t++) delay_us(1000);
    kv("S4 CDONE after ms      = ", t);
    if (!gpio_get(PIN_T35_CDONE)) {
        puts_("   T35 not configured: CPU fallback for all accelerator jobs\n");
        gpio_set(PIN_T35_CRESET_N_F, 0);
        gpio_set(PIN_T35_PWR_EN, 0);
        return R_FAIL;
    }
    delay_us(2000);                                     /* > CDONE_DLY RC delay and tUSER */
    return R_OK;
}

/* S5: AMBX mailbox over the isolated SPI0 (read 0x0B a1 a0 dummy ..., write 0x02 a1 a0 ...) */
static arc1_spi_hal g_t35hal = { &g_spi0_t35, spi_select, spi_transfer, now_us };
static int mbx_read(uint16_t a, uint8_t *d, size_t n)
{
    uint8_t h[4] = { 0x0B, (uint8_t)(a >> 8), (uint8_t)a, 0 };
    int rc;
    spi_select(&g_spi0_t35, 1);
    rc = spi_transfer(&g_spi0_t35, h, NULL, 4);
    if (!rc) rc = spi_transfer(&g_spi0_t35, NULL, d, n);
    spi_select(&g_spi0_t35, 0);
    return rc;
}
static int mbx_write(uint16_t a, const uint8_t *d, size_t n)
{
    uint8_t h[3] = { 0x02, (uint8_t)(a >> 8), (uint8_t)a };
    int rc;
    spi_select(&g_spi0_t35, 1);
    rc = spi_transfer(&g_spi0_t35, h, NULL, 3);
    if (!rc) rc = spi_transfer(&g_spi0_t35, d, NULL, n);
    spi_select(&g_spi0_t35, 0);
    return rc;
}
static uint16_t mbx_status(void) { uint8_t s[2] = { 0, 0 }; (void)mbx_read(0x0008, s, 2); return (uint16_t)(s[0] | (s[1] << 8)); }
static int stage_mailbox_psram(int *psram)
{
    uint8_t id[8], c;
    uint16_t st = 0;
    uint32_t t;
    (void)g_t35hal;
    *psram = R_SKIP;
    gpio_out(PIN_SPI0_CS0_N, 1); gpio_func(PIN_SPI0_CS0_N, 1);   /* NOR CS# held high by GPIO while the T35 is selected */
    gpio_out(PIN_T35_SS_N_F, 1);
    gpio_out(PIN_T35_BUS_EN_N, 0);                              /* isolation buffers ON */
    if (mbx_read(0x0000, id, 8)) return R_FAIL;
    kv("S5 MAGIC               = ", (uint32_t)id[0] << 24 | (uint32_t)id[1] << 16 | (uint32_t)id[2] << 8 | id[3]);
    kv("   VERSION/CAPS         = ", (uint32_t)(id[4] | (id[5] << 8)) << 16 | (uint32_t)(id[6] | (id[7] << 8)));
    if (id[0] != 'A' || id[1] != 'M' || id[2] != 'B' || id[3] != 'X') {
        gpio_set(PIN_T35_BUS_EN_N, 1);
        return R_FAIL;
    }
    gpio_set(PIN_PSRAM_PWR_REQ, 1);                             /* EN = REQ & CDONE_DLY */
    for (t = 0; t < 500; t++) { st = mbx_status(); if ((st & (1u << 11)) && (st & 0x6u)) break; delay_us(1000); }
    kv("   STATUS after power   = ", st);
    kv("   PSRAM_PG pin         = ", (uint32_t)gpio_get(PIN_PSRAM_PG));
    if (!(st & (1u << 11))) { puts_("   PSRAM power never good: check U12/U13/U14, CDONE_DLY\n"); *psram = R_FAIL; }
    else if (st & (1u << 2)) { kv("   PSRAM init error     = ", (st >> 9) & 3u); *psram = R_FAIL; }
    else {
        c = 0x08;                                                /* BIST_START */
        (void)mbx_write(0x000C, &c, 1);
        for (t = 0; t < 5000; t++) { st = mbx_status(); if (!(st & (1u << 6)) && (st & 0x180u)) break; delay_us(1000); }
        kv("   BIST STATUS          = ", st);
        *psram = (st & (1u << 7)) && !(st & (1u << 8)) ? R_OK : R_FAIL;
    }
    gpio_set(PIN_T35_BUS_EN_N, 1);                              /* back to isolated */
    gpio_func(PIN_SPI0_CS0_N, 2);
    return R_OK;
}

int main(void)
{
    int r_nor, r_bt, r_cfg = R_SKIP, r_mbx = R_SKIP, r_ps = R_SKIP;
    uart_init();
    puts_("\nARC-1 Compact R08 F133 diagnostic image (BUILD-ONLY until run on hardware)\n");
    kv("S0 VER_REG             = ", REG32(SYSCFG_VER));
    kv("   BOOT_SEL_PAD[12:11]  = ", (REG32(SYSCFG_VER) >> 11) & 3u);     /* expect 0 (BOOT-SEL 00) */
    kv("   eFuse boot select    = ", REG32(SID_BOOTSEL));
    kv("   RTC fast boot        = ", REG32(RTC_FASTBOOT));
    gpio_in(PIN_USB_CUR_OUT1); gpio_in(PIN_USB_CUR_OUT2); gpio_in(PIN_VBUS_SENSE);
    kv("S1 USB OUT1/OUT2/VBUS  = ", ((uint32_t)gpio_get(PIN_USB_CUR_OUT1) << 8) | ((uint32_t)gpio_get(PIN_USB_CUR_OUT2) << 4) |
                                     (uint32_t)gpio_get(PIN_VBUS_SENSE));
    r_nor = stage_nor();
    r_bt = stage_bt820();
    r_cfg = stage_t35_config();
    if (r_cfg == R_OK) r_mbx = stage_mailbox_psram(&r_ps);
    puts_("DIAG SUMMARY cpu=OK nor="); puts_(rs(r_nor));
    puts_(" bt820="); puts_(rs(r_bt));
    puts_(" t35cfg="); puts_(rs(r_cfg));
    puts_(" mailbox="); puts_(rs(r_mbx));
    puts_(" psram="); puts_(rs(r_ps));
    puts_("\n(graphics never depends on t35/psram; a lit screen photo is required before any display claim)\n");
    gpio_out(PIN_LED_STATUS, r_bt == R_OK);
    gpio_out(PIN_LED_ERROR, r_nor != R_OK || r_bt != R_OK);
    return 0;
}
