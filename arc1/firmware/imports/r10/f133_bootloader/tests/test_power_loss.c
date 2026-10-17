/* Fault injection against a behavioural board model. No silicon or asynchronous
 * protection claim: a blocking transfer may already have clocked data at fault. */
#include <stdio.h>
#include <string.h>
#include "ecp5_cfg.h"
#include "ecp5_mock.h"
#include "crc32.h"

enum fault {
    NO_FAULT, INIT_WAIT_LOSS, STALE_INITN, PROGRAM_RELEASE_LOSS,
    SELECT_LOSS, ID_HEADER_LOSS, ID_HEADER_TRANSIENT, STATUS_READ_LOSS,
    BURST_LOSS, SOURCE_LOSS, DONE_WAIT_LOSS, PROBE_HOLD_LOSS, CONFIG_CLEANUP_LOSS
};
static ecp5_mock m;
static uint8_t bit[8192];
static ecp5_cfg cfg;
static ecp5_image img;
static enum fault fault;
static unsigned reads, transfers_after_fault, program_releases;
static int injected, saw_good_pg, saw_bad_pg, transient_pending, status_read;
static unsigned checks, failures;

#define CHECK(expr) do { \
    checks++; \
    if (!(expr)) { printf("FAIL line %d: %s\n", __LINE__, #expr); failures++; } \
} while (0)

static void lose_power(void)
{
    injected = 1;
    m.no_vcc_pg = 1;
}

static void fault_set(void *ctx, ecp5_pin p, int v)
{
    mock_gpio.set(ctx, p, v);
    if (p == ECP5_PIN_PROGRAMN && v) {
        program_releases++;
        if (fault == PROGRAM_RELEASE_LOSS && program_releases == 2u) lose_power();
    }
    if (fault == PROBE_HOLD_LOSS && p == ECP5_PIN_PROGRAMN && !v && status_read) lose_power();
    if (fault == CONFIG_CLEANUP_LOSS && p == ECP5_PIN_PROGRAMN && !v && m.bus_en_n) lose_power();
}

static int fault_get(void *ctx, ecp5_pin p)
{
    int v;
    if (fault == STALE_INITN && !injected && p == ECP5_PIN_INITN && m.t_us >= 6000u) {
        lose_power();
        return 1;                     /* stale/high pin must not override bad PG */
    }
    if (fault == DONE_WAIT_LOSS && !injected && p == ECP5_PIN_DONE) {
        lose_power();
        return 0;
    }
    if (p == ECP5_PIN_VCC_PG && transient_pending) {
        transient_pending = 0;
        v = 0;                        /* recovered by the next sample; error must stay latched */
    } else {
        v = mock_gpio.get(ctx, p);
    }
    if (p == ECP5_PIN_VCC_PG) {
        if (v) saw_good_pg = 1;
        else if (saw_good_pg) saw_bad_pg = 1;
    }
    return v;
}

static void fault_delay(void *ctx, uint32_t us)
{
    mock_gpio.delay_us(ctx, us);
    if (fault == INIT_WAIT_LOSS && !injected && m.t_us >= 1500u) lose_power();
}

static void fault_select(void *ctx, int asserted)
{
    mock_spi.select(ctx, asserted);
    if (fault == SELECT_LOSS && asserted && !injected) lose_power();
}

static int fault_transfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t n)
{
    int rc, was_burst = m.burst;
    if (saw_bad_pg) transfers_after_fault++;
    rc = mock_spi.transfer(ctx, tx, rx, n);
    if (!injected && tx && n == 4u && tx[0] == ECP5_CMD_READ_ID) {
        if (fault == ID_HEADER_LOSS) lose_power();
        if (fault == ID_HEADER_TRANSIENT) { injected = 1; transient_pending = 1; }
    }
    if (rx && m.op == ECP5_CMD_LSC_READ_STATUS) {
        status_read = 1;
        if (fault == STATUS_READ_LOSS && !injected) lose_power();
    }
    if (fault == BURST_LOSS && was_burst && n > 4u && !injected) lose_power();
    return rc;
}

static const uint8_t *source_read(void *ctx, uint32_t off, uint32_t n, uint8_t *scratch)
{
    (void)ctx; (void)n; (void)scratch;
    reads++;
    if (fault == SOURCE_LOSS && reads == 2u) lose_power();
    return bit + off;
}

static void reset(enum fault f)
{
    ecp5_gpio_hal io = { &m, fault_set, fault_get, fault_delay };
    arc1_spi_hal spi = { &m, fault_select, fault_transfer, mock_spi.now_us };
    fault = f;
    reads = 0; transfers_after_fault = 0; program_releases = 0;
    injected = 0; saw_good_pg = 0; saw_bad_pg = 0; transient_pending = 0; status_read = 0;
    mock_init(&m, arc1_crc32(0, bit, sizeof bit));
    ecp5_cfg_init(&cfg, &io, &spi);
}

static void check_off(void)
{
    CHECK(!m.ss);
    CHECK(m.bus_en_n);
    CHECK(!m.pwr_en);
    CHECK(!m.programn_drv_low);
    CHECK(!m.psram_req);
    CHECK(transfers_after_fault == 0u);
}

int main(void)
{
    uint32_t id, st;
    ecp5_source src = { source_read, NULL, NULL };
    const enum fault config_faults[] = {
        PROGRAM_RELEASE_LOSS, SELECT_LOSS, ID_HEADER_LOSS, ID_HEADER_TRANSIENT,
        STATUS_READ_LOSS, BURST_LOSS, SOURCE_LOSS, DONE_WAIT_LOSS, CONFIG_CLEANUP_LOSS
    };
    const enum fault power_faults[] = { INIT_WAIT_LOSS, STALE_INITN };
    const enum fault probe_faults[] = { STATUS_READ_LOSS, PROBE_HOLD_LOSS };
    const uint8_t head[] = {0xff, 0x00, 0, 0xff, 0xff, 0xff, 0xbd, 0xb3,
                           0xe2, 0, 0, 0, 0x41, 0x11, 0x20, 0x43};
    size_t i;
    memcpy(bit, head, sizeof head);
    memset(&img, 0, sizeof img);
    img.bit = bit; img.bit_len = sizeof bit; img.idcode = ECP5_IDCODE_LFE5U_45;

    reset(NO_FAULT);
    CHECK(ecp5_configure(&cfg, &img) == ECP5_OK);
    CHECK(m.done && m.pwr_en && !m.ss && !m.bus_en_n);
    reset(NO_FAULT);
    CHECK(ecp5_probe(&cfg, &id, &st) == ECP5_OK);
    CHECK(id == ECP5_IDCODE_LFE5U_45 && st == 0u);
    CHECK(m.pwr_en && m.bus_en_n && m.programn_drv_low && !m.ss);

    reset(NO_FAULT);
    m.no_vcc_pg = 1;
    m.ss = 1;                         /* clean up a previously selected device too */
    CHECK(ecp5_power_up(&cfg) == ECP5_E_POWER);
    CHECK(!m.spi_bytes);
    check_off();
    reset(NO_FAULT);
    m.no_initn = 1;
    CHECK(ecp5_power_up(&cfg) == ECP5_E_INITN_TIMEOUT);
    check_off();
    reset(NO_FAULT);
    m.programn_held = 1;
    CHECK(ecp5_power_up(&cfg) == ECP5_E_PROGRAMN_HELD);
    check_off();

    for (i = 0; i < sizeof power_faults / sizeof power_faults[0]; i++) {
        reset(power_faults[i]);
        CHECK(ecp5_power_up(&cfg) == ECP5_E_POWER);
        CHECK(injected && m.t_us < 10000u && !m.spi_bytes);
        check_off();
    }
    for (i = 0; i < sizeof config_faults / sizeof config_faults[0]; i++) {
        reset(config_faults[i]);
        if (fault == CONFIG_CLEANUP_LOSS) m.spi_io_error_at_byte = 1;
        CHECK(ecp5_configure_stream(&cfg, &img, &src) == ECP5_E_POWER);
        CHECK(injected);
        if (fault == ID_HEADER_LOSS || fault == ID_HEADER_TRANSIENT) CHECK(m.spi_bytes == 4u);
        if (fault == SELECT_LOSS) CHECK(m.spi_bytes == 0u);
        if (fault == BURST_LOSS || fault == SOURCE_LOSS) CHECK(m.burst_len == 4096u);
        if (fault == SOURCE_LOSS) CHECK(reads == 2u);
        if (fault == DONE_WAIT_LOSS) CHECK(m.t_us < 20000u);
        check_off();
    }
    for (i = 0; i < sizeof probe_faults / sizeof probe_faults[0]; i++) {
        reset(probe_faults[i]);
        CHECK(ecp5_probe(&cfg, &id, &st) == ECP5_E_POWER);
        CHECK(injected);
        check_off();
    }

    reset(NO_FAULT);
    m.spi_io_error_at_byte = 1;
    CHECK(ecp5_configure(&cfg, &img) == ECP5_E_IO);
    CHECK(!m.ss && m.bus_en_n && m.pwr_en && m.programn_drv_low);
    reset(NO_FAULT);
    CHECK(ecp5_power_up(&cfg) == ECP5_OK);
    m.no_vcc_pg = 1; m.ss = 1; m.psram_req = 1;
    ecp5_safe(&cfg, 0);                 /* invalid rails override the powered-hold request */
    check_off();
    reset(NO_FAULT);
    cfg.chunk = 0;
    CHECK(ecp5_configure(&cfg, &img) == ECP5_E_ARG);
    CHECK(!m.spi_bytes && !m.pwr_en);
    printf("POWER_LOSS_%s: %u checks, %u failures (behavioural model only)\n",
           failures ? "FAIL" : "PASS", checks, failures);
    return failures ? 1 : 0;
}
