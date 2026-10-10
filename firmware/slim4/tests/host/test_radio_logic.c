/* Host test of the radio decisions (firmware R13): components/slim4_bsp/slim4_radio_logic.c (RF plan, TX power cap,
 * ping packets) and slim4_st_judge_radio() in slim4_selftest_logic.c (what a probe of the module means), compiled in
 * with no ESP-IDF. Build and run: sh tests/host/run.sh. Not a substitute for running the probe on a board. */
#include <stdio.h>
#include <string.h>
#include "../../components/slim4_bsp/slim4_radio_logic.c"
#include "../../components/slim4_bsp/slim4_selftest_logic.c"

static int fails;
#define CHECK(c, ...) do { if (!(c)) { ++fails; printf("FAIL %s:%d ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

static slim4_radio_probe_t good(void)
{
    slim4_radio_probe_t p;
    memset(&p, 0, sizeof(p));
    p.spi_ready = true; p.busy_high_in_reset = true; p.busy_released = true; p.busy_us = 3400; p.status = 0x22;
    p.sync[0] = 0x14; p.sync[1] = 0x24; p.readback[0] = 0x5A; p.readback[1] = 0xA5; p.init_done = true;
    p.errors = 0; p.dio1_rose = true; p.dio1_us = 1100; p.irq = 0x0200; p.dio1_cleared = true;
    return p;
}

static const slim4_st_item_t *judge(const slim4_radio_probe_t *p)
{
    static slim4_st_report_t rep;
    slim4_st_report_init(&rep);
    slim4_st_judge_radio(&rep, p);
    return rep.count == 1 ? &rep.items[0] : NULL;
}

static void expect(const slim4_radio_probe_t *p, slim4_st_verdict_t v, const char *brief, const char *why)
{
    const slim4_st_item_t *it = judge(p);
    CHECK(it != NULL, "%s: no line", why);
    if (!it) return;
    CHECK(it->verdict == v, "%s: verdict %s", why, slim4_st_verdict_name(it->verdict));
    CHECK(!strcmp(it->brief, brief), "%s: brief '%s', expected '%s'", why, it->brief, brief);
    CHECK(strlen(it->brief) <= 35, "%s: brief too long", why);
    for (const char *c = it->brief; *c; ++c)
        CHECK((*c >= 'A' && *c <= 'Z') || (*c >= '0' && *c <= '9') || strchr(" ./-:", *c), "%s: brief char '%c'", why, *c);
}

int main(void)
{
    /* RF plan */
    CHECK(slim4_radio_frf(915000000u) == 959447040u, "frf 915 MHz = %lu", (unsigned long)slim4_radio_frf(915000000u));
    CHECK(slim4_radio_frf(32000000u) == (1u << 25), "frf of Fxtal");
    CHECK(slim4_radio_freq_ok(SLIM4_RADIO_FREQ_HZ, SLIM4_RADIO_BW_HZ), "default channel allowed");
    CHECK(!slim4_radio_freq_ok(920000000u, 500000u), "920 MHz is Y1's 23rd harmonic");
    CHECK(!slim4_radio_freq_ok(919000000u, 500000u), "919 MHz within 1.25 MHz of 920");
    CHECK(slim4_radio_freq_ok(918500000u, 500000u), "918.5 MHz: its edge, 918.75, is 1.25 MHz from 920");
    CHECK(slim4_radio_freq_ok(918000000u, 500000u), "918 MHz allowed");
    CHECK(!slim4_radio_freq_ok(927500000u, 500000u), "927.5: near the TCXO's 29th harmonic, 928 MHz");
    CHECK(!slim4_radio_freq_ok(902100000u, 500000u), "channel must sit inside 902-928");
    CHECK(slim4_radio_freq_ok(903000000u, 500000u), "903 MHz allowed");
    CHECK(!slim4_radio_freq_ok(868000000u, 125000u), "868 MHz is outside the US band");
    /* TCXO codes */
    CHECK(slim4_radio_tcxo_code(1800) == 0x02, "1.8 V code");
    CHECK(slim4_radio_tcxo_code(3300) == 0x07, "3.3 V code");
    CHECK(slim4_radio_tcxo_code(2000) == 0xFF, "2.0 V has no code");
    /* TX power cap */
    slim4_power_state_t ps;
    memset(&ps, 0, sizeof(ps));
    ps.usb_power = true; ps.battery_mv = 0;
    CHECK(slim4_radio_tx_cap_dbm(&ps) == 22, "USB: full power");
    memset(&ps, 0, sizeof(ps)); ps.battery_mv = 3900;
    CHECK(slim4_radio_tx_cap_dbm(&ps) == 22, "good cell: full power");
    ps.battery_mv = 3450;
    CHECK(slim4_radio_tx_cap_dbm(&ps) == 14, "low cell: 14 dBm");
    ps.battery_mv = 3900; ps.battery_approx = true;
    CHECK(slim4_radio_tx_cap_dbm(&ps) == 14, "uncalibrated reading: 14 dBm");
    ps.battery_approx = false; ps.battery_low = true;
    CHECK(slim4_radio_tx_cap_dbm(&ps) == SLIM4_RADIO_TX_OFF, "at cut-off: off");
    ps.usb_power = true;
    CHECK(slim4_radio_tx_cap_dbm(&ps) == 22, "cut-off cell with USB: full power");
    CHECK(slim4_radio_tx_cap_dbm(NULL) == 14, "no power state: 14 dBm");
    /* ping packets */
    slim4_radio_ping_t a = {.reply = false, .seq = 7, .sender = 0xA1B2C3D4u}, b;
    uint8_t buf[SLIM4_RADIO_PING_LEN];
    slim4_radio_ping_encode(&a, buf);
    CHECK(slim4_radio_ping_decode(buf, sizeof(buf), &b) && !b.reply && b.seq == 7 && b.sender == 0xA1B2C3D4u, "ping round trip");
    slim4_radio_ping_t r = {.reply = true, .seq = 9, .sender = 0x01020304u, .rssi_heard = -97};
    slim4_radio_ping_encode(&r, buf);
    CHECK(slim4_radio_ping_decode(buf, sizeof(buf), &b) && b.reply && b.seq == 9 && b.rssi_heard == -97, "reply round trip");
    CHECK(!slim4_radio_ping_decode(buf, 7, &b), "short packet refused");
    buf[0] = 'X';
    CHECK(!slim4_radio_ping_decode(buf, sizeof(buf), &b), "foreign packet refused");
    /* self-test judgement */
    slim4_radio_probe_t p = good();
    expect(&p, SLIM4_ST_PASS, "RADIO SX1262 OK", "good module");
    memset(&p, 0, sizeof(p)); p.spi_ready = true; p.busy_released = true;
    expect(&p, SLIM4_ST_INFO, "RADIO NOT FITTED", "no module: everything reads 0");
    p = good(); p.spi_ready = false;
    expect(&p, SLIM4_ST_FAIL, "RADIO SPI SETUP FAILED", "SPI driver fault");
    p = good(); p.busy_released = false;
    expect(&p, SLIM4_ST_FAIL, "RADIO BUSY STUCK HIGH", "BUSY never falls");
    p = good(); p.sync[0] = p.sync[1] = 0;
    expect(&p, SLIM4_ST_FAIL, "RADIO SPI READS ZERO", "MISO open (BUSY works)");
    p = good(); p.sync[0] = p.sync[1] = 0xFF; p.status = 0xFF;
    expect(&p, SLIM4_ST_FAIL, "RADIO MISO STUCK HIGH", "MISO high");
    p = good(); p.sync[0] = 0x14; p.sync[1] = 0x20;
    expect(&p, SLIM4_ST_FAIL, "RADIO SPI READ WRONG", "a bit wrong");
    p = good(); p.readback[0] = 0x14; p.readback[1] = 0x24;
    expect(&p, SLIM4_ST_FAIL, "RADIO SPI WRITE FAILED", "MOSI open");
    p = good(); p.busy_high_in_reset = false;
    expect(&p, SLIM4_ST_FAIL, "RADIO RESET NOT SEEN", "NRST open");
    p = good(); p.init_done = false;
    expect(&p, SLIM4_ST_FAIL, "RADIO CALIBRATION TIMED OUT", "TCXO dead");
    p = good(); p.errors = 0x0020;
    expect(&p, SLIM4_ST_FAIL, "RADIO CHIP ERROR", "XOSC start error");
    const slim4_st_item_t *it = judge(&p);
    CHECK(it && strstr(it->detail, "XOSC_START"), "error named in the detail");
    p = good(); p.dio1_rose = false;
    expect(&p, SLIM4_ST_FAIL, "RADIO DIO1 NO INTERRUPT", "DIO1 open");
    p = good(); p.dio1_cleared = false;
    expect(&p, SLIM4_ST_FAIL, "RADIO DIO1 STUCK HIGH", "DIO1 high");
    if (fails) { printf("%d radio checks failed\n", fails); return 1; }
    printf("radio logic: all checks passed\n");
    return 0;
}
