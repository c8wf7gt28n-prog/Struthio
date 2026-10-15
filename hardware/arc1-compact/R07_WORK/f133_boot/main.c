/* ARC-1 Compact R07 -- F133 bare-metal bring-up image (BUILD-ONLY).
 *
 * Purpose: the first program to run on an ARC-1 board (or a D1s-class dev
 * board wired per R07_WORK/board/r07_board_plan.json). It:
 *   1. prints a banner on UART0 (PE2/PE3, 115200 8N1 from the 24 MHz HOSC),
 *   2. reports boot-select pad status, eFuse boot select and fast-boot register,
 *   3. holds the T35 in reset (PE8 low) -- the FPGA is not needed for graphics,
 *   4. boots the BT820 over SPI1 (PD10..PD13, single mode, ~8 MHz) with the
 *      SAME host-tested driver sources (../firmware/src/bt820_host.c, bt820_gfx.c),
 *   5. reads REG_BOOT_STATUS / REG_CHIP_ID / REG_ID, starts scan-out with the
 *      UNCONFIRMED candidate panel timing and draws a solid test frame,
 *   6. prints every result code so a failure has a signature.
 * Nothing here has executed on silicon. Register addresses come from the
 * D1-H User Manual (see f133_regs.h). Delays use mcycle with an assumed
 * 1.2 GHz worst-case CPU clock, so they are >= the requested time if the
 * clock is slower (likely 24 MHz after BROM: delays then run ~50x long). */
#include <stddef.h>
#include <stdint.h>

#include "bt820_gfx.h"
#include "bt820_regs.h"
#include "f133_regs.h"

/* ---- freestanding libc pieces used by the shared driver ---- */
void *memset(void *d, int c, size_t n) { uint8_t *p = d; while (n--) *p++ = (uint8_t)c; return d; }
void *memcpy(void *d, const void *s, size_t n) { uint8_t *p = d; const uint8_t *q = s; while (n--) *p++ = *q++; return d; }

/* ---- time ---- */
static uint64_t cycles(void) { uint64_t c; __asm__ volatile("csrr %0, mcycle" : "=r"(c)); return c; }
#define ASSUMED_MAX_HZ 1200000000ull
static void delay_us(uint32_t us) {
    uint64_t t0 = cycles(), n = (ASSUMED_MAX_HZ / 1000000ull) * us;
    while (cycles() - t0 < n) { }
}
static uint64_t now_us(void *ctx) { (void)ctx; return cycles() / (ASSUMED_MAX_HZ / 1000000ull); }

/* ---- GPIO ---- */
static void gpio_func(uint32_t port, uint32_t pin, uint32_t fn) {
    uint32_t a = GPIO_CFG(port, pin / 8u), sh = (pin % 8u) * 4u;
    REG32(a) = (REG32(a) & ~(0xFu << sh)) | ((fn & 0xFu) << sh);
}
static void gpio_set(uint32_t port, uint32_t pin, int v) {
    uint32_t a = GPIO_DAT(port);
    REG32(a) = v ? (REG32(a) | (1u << pin)) : (REG32(a) & ~(1u << pin));
}

/* ---- UART0 on PE2/PE3 (Function6, board plan) ---- */
static void uart_init(void) {
    gpio_func(PORT_E, 2, 6);
    gpio_func(PORT_E, 3, 6);
    REG32(CCU_UART_BGR) |= (1u << 0);              /* UART0 gating */
    REG32(CCU_UART_BGR) |= (1u << 16);             /* de-assert UART0 reset */
    REG32(UART0_BASE + UART_LCR) = 0x83u;          /* DLAB, 8N1 */
    REG32(UART0_BASE + UART_DLL) = 13u;            /* 24 MHz / (16 * 13) = 115384 baud (+0.16 %) */
    REG32(UART0_BASE + UART_DLH) = 0u;
    REG32(UART0_BASE + UART_LCR) = 0x03u;
    REG32(UART0_BASE + UART_FCR) = 0x07u;          /* enable + reset FIFOs */
}
static void putc_(char c) {
    while (!(REG32(UART0_BASE + UART_LSR) & (1u << 5))) { }   /* THRE */
    REG32(UART0_BASE + UART_THR) = (uint32_t)(uint8_t)c;
}
static void puts_(const char *s) { while (*s) { if (*s == '\n') putc_('\r'); putc_(*s++); } }
static void puthex(uint32_t v) {
    static const char h[] = "0123456789abcdef";
    puts_("0x");
    for (int i = 7; i >= 0; i--) putc_(h[(v >> (4 * i)) & 0xFu]);
}
static void kv(const char *k, uint32_t v) { puts_(k); puthex(v); puts_("\n"); }

/* ---- SPI1 master, PD10 CS / PD11 CLK / PD12 MOSI / PD13 MISO (Function4) ---- */
#define SPI(o) REG32(SPI1_BASE + (o))
static void spi1_init(void) {
    for (uint32_t p = 10; p <= 13; p++) gpio_func(PORT_D, p, 4);
    REG32(CCU_SPI_BGR) |= (1u << 1);               /* SPI1 gating */
    REG32(CCU_SPI_BGR) |= (1u << 17);              /* de-assert SPI1 reset */
    REG32(CCU_SPI1_CLK) = (1u << 31) | (0u << 24) | (0u << 8) | 2u;   /* HOSC/3 = 8 MHz */
    SPI(SPI_GCR) = (1u << 31);                     /* soft reset */
    while (SPI(SPI_GCR) & (1u << 31)) { }
    SPI(SPI_GCR) = (1u << 7) | (1u << 1) | 1u;     /* TP_EN, master, enable */
    /* mode 0, CS active low, software-owned CS held high, normal sample mode (<= 40 MHz) */
    SPI(SPI_TCR) = (1u << 13) | (1u << 7) | (1u << 6) | (1u << 2);
    SPI(SPI_FCR) = (1u << 31) | (1u << 15);        /* reset both FIFOs */
}
static void spi1_select(void *ctx, int asserted) {
    (void)ctx;
    uint32_t t = SPI(SPI_TCR);
    SPI(SPI_TCR) = asserted ? (t & ~(1u << 7)) : (t | (1u << 7));
    if (!asserted) delay_us(1);                    /* >= 2 SCK cycles CS# high (DS 4.5.1) */
}
static int spi1_transfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t n) {
    (void)ctx;
    while (n) {
        uint32_t k = n > 64u ? 64u : (uint32_t)n, i;
        uint64_t t0;
        SPI(SPI_MBC) = k;
        SPI(SPI_MTC) = k;
        SPI(SPI_BCC) = k;                          /* all single mode (STC = k) */
        for (i = 0; i < k; i++) REG8(SPI1_BASE + SPI_TXD) = tx ? tx[i] : 0u;
        SPI(SPI_ISR) = 0xFFFFFFFFu;                /* clear status (W1C) */
        SPI(SPI_TCR) |= (1u << 31);                /* XCH */
        t0 = cycles();
        while (!(SPI(SPI_ISR) & (1u << 12))) {     /* TC */
            if (cycles() - t0 > ASSUMED_MAX_HZ) return -1;   /* >= 1 s */
        }
        for (i = 0; i < k; i++) {
            uint8_t b = REG8(SPI1_BASE + SPI_RXD);
            if (rx) rx[i] = b;
        }
        if (tx) tx += k;
        if (rx) rx += k;
        n -= k;
    }
    return 0;
}

/* ---- BT820 platform ---- */
static void bt_reset(void *ctx, int level) { (void)ctx; gpio_set(PORT_D, 16, level); }
static void bt_delay(void *ctx, uint32_t ms) { (void)ctx; while (ms--) delay_us(1000); }

static bt820_dev g_dev;
static bt820_gfx g_gfx;

int main(void) {
    arc1_spi_hal hal = {0, spi1_select, spi1_transfer, now_us};
    bt820_platform plat = {0, bt_reset, bt_delay};
    bt820_boot_cfg cfg;
    bt820_boot_report rep;
    bt820_timing tim;
    int rc;

    uart_init();
    puts_("\nARC-1 Compact R07 F133 bring-up image (BUILD-ONLY until run on hardware)\n");
    kv("VER_REG 0x03000024   = ", REG32(SYSCFG_VER));
    kv("  BOOT_SEL_PAD[12:11]= ", (REG32(SYSCFG_VER) >> 11) & 3u);
    kv("  FEL_SEL_PAD[8]     = ", (REG32(SYSCFG_VER) >> 8) & 1u);
    kv("SID 0x03006210       = ", REG32(SID_BOOTSEL));
    kv("RTC fast boot        = ", REG32(RTC_FASTBOOT));

    /* T35 held in reset: PE8 output low (board also pulls it low). PE9 = CDONE input. */
    gpio_set(PORT_E, 8, 0);
    gpio_func(PORT_E, 8, 1);
    gpio_func(PORT_E, 9, 0);

    /* BT820 RST_N on PD16 (output), INT_N on PD17 (input) */
    gpio_set(PORT_D, 16, 0);
    gpio_func(PORT_D, 16, 1);
    gpio_func(PORT_D, 17, 0);
    spi1_init();

    if (bt820_init(&g_dev, &hal, 64, 128u << 20) || bt820_gfx_init(&g_gfx, &g_dev, &plat, 100000)) {
        puts_("driver init failed\n");
        return 1;
    }
    bt820_boot_cfg_default(&cfg);
    rc = bt820_boot(&g_gfx, &cfg, &rep);
    kv("bt820_boot result    = ", (uint32_t)rc);
    kv("  bus_error          = ", (uint32_t)rep.bus_error);
    kv("  REG_BOOT_STATUS    = ", rep.boot_status);
    kv("  REG_CHIP_ID        = ", rep.chip_id);
    kv("  REG_ID             = ", rep.reg_id);
    kv("  REG_CPURESET       = ", rep.cpureset);
    kv("  polls              = ", rep.polls_used);
    puts_(bt820_gfx_error_string(rc));
    puts_("\n");
    if (rc != BT820_GFX_OK) return 2;

    bt820_timing_candidate_1024x600(&tim);
    rc = bt820_scanout_start(&g_gfx, &tim);
    kv("scanout_start        = ", (uint32_t)rc);
    rc = bt820_test_frame(&g_gfx, 0x00, 0x40, 0xC0);
    kv("test_frame           = ", (uint32_t)rc);
    {
        uint32_t frames = 0;
        (void)bt820_read32(&g_dev, BT820_REG_FRAMES, &frames);
        kv("REG_FRAMES           = ", frames);
    }
    puts_("done: a lit blue screen is required before any display claim\n");
    return 0;
}
