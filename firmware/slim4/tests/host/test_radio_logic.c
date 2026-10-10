/* Host test of the radio decisions (firmware R13): components/slim4_bsp/slim4_radio_logic.c (RF plan, TX power cap,
 * RUI3 AT reply parsing and command strings, ping packets) and slim4_st_judge_radio() in slim4_selftest_logic.c (what
 * a probe of the RAK3172 means), compiled in with no ESP-IDF. Build and run: sh tests/host/run.sh. Not a substitute
 * for running the probe and a two-board ping on real boards. */
#include <stdio.h>
#include <string.h>
#include "../../components/slim4_bsp/slim4_radio_logic.c"
#include "../../components/slim4_bsp/slim4_selftest_logic.c"

static int fails, checks;
#define CHECK(c, ...) do { ++checks; if (!(c)) { ++fails; printf("FAIL %s:%d ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

static slim4_radio_probe_t good(void)
{
    slim4_radio_probe_t p;
    memset(&p, 0, sizeof(p));
    p.uart_ready = true; p.rx_low_in_reset = true; p.rx_high_after = true; p.answered = true; p.answer_ms = 320;
    snprintf(p.version, sizeof(p.version), "RUI_4.0.6_RAK3172-E"); p.nwm = 0;
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
    CHECK(slim4_radio_freq_ok(SLIM4_RADIO_FREQ_HZ, SLIM4_RADIO_BW_HZ), "default channel allowed");
    CHECK(!slim4_radio_freq_ok(920000000u, 500000u), "920 MHz is Y1's 23rd harmonic");
    CHECK(!slim4_radio_freq_ok(919000000u, 500000u), "919 MHz within 1.25 MHz of 920");
    CHECK(slim4_radio_freq_ok(918500000u, 500000u), "918.5 MHz: its edge, 918.75, is 1.25 MHz from 920");
    CHECK(!slim4_radio_freq_ok(927500000u, 500000u), "927.5: near the 32 MHz reference's 29th harmonic, 928 MHz");
    CHECK(!slim4_radio_freq_ok(902100000u, 500000u), "channel must sit inside 902-928");
    CHECK(slim4_radio_freq_ok(903000000u, 500000u), "903 MHz allowed");
    CHECK(!slim4_radio_freq_ok(868000000u, 125000u), "868 MHz is outside the US band");
    /* TX power cap */
    slim4_power_state_t ps;
    memset(&ps, 0, sizeof(ps)); ps.usb_power = true;
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
    /* AT replies */
    slim4_at_line_t at;
    slim4_at_parse("OK", &at);                      CHECK(at.kind == SLIM4_AT_OK, "OK");
    slim4_at_parse("AT_PARAM_ERROR", &at);          CHECK(at.kind == SLIM4_AT_ERROR, "param error");
    slim4_at_parse("AT_BUSY_ERROR", &at);           CHECK(at.kind == SLIM4_AT_ERROR, "busy error");
    slim4_at_parse("AT_COMMAND_NOT_FOUND", &at);    CHECK(at.kind == SLIM4_AT_ERROR, "unknown command");
    slim4_at_parse("+EVT:TXP2P DONE", &at);         CHECK(at.kind == SLIM4_AT_TX_DONE, "tx done");
    slim4_at_parse("+EVT:RXP2P RECEIVE TIMEOUT", &at); CHECK(at.kind == SLIM4_AT_RX_TIMEOUT, "rx timeout");
    slim4_at_parse("+EVT:RXP2P:-97:6:53503407A1B2C3D4", &at);
    CHECK(at.kind == SLIM4_AT_RX && at.rssi == -97 && at.snr == 6 && at.len == 8 && at.payload[0] == 'S' &&
          at.payload[7] == 0xD4, "rx event: rssi %d snr %d len %u", at.rssi, at.snr, at.len);
    slim4_at_parse("+EVT:RXP2P:-120:-11:0a0B", &at);
    CHECK(at.kind == SLIM4_AT_RX && at.rssi == -120 && at.snr == -11 && at.len == 2 && at.payload[1] == 0x0B, "negative snr, mixed case");
    slim4_at_parse("+EVT:RXP2P:-97:6:5350G", &at);  CHECK(at.kind != SLIM4_AT_RX, "bad hex is not a packet");
    slim4_at_parse("+EVT:RXP2P:-97:6:535", &at);    CHECK(at.kind != SLIM4_AT_RX, "odd digit count is not a packet");
    slim4_at_parse("AT+VER=RUI_4.0.6_RAK3172-E", &at); CHECK(at.kind == SLIM4_AT_VALUE, "query answer");
    slim4_at_parse("", &at);                        CHECK(at.kind == SLIM4_AT_NONE, "empty line");
    /* command strings */
    char buf[64];
    CHECK(slim4_at_p2p_settings(buf, sizeof(buf), 915000000u, 7, 500000u, 14) && !strcmp(buf, "AT+P2P=915000000:7:500:0:8:14"),
          "P2P settings '%s'", buf);
    const uint8_t pk[3] = {0x53, 0x00, 0xFF};
    CHECK(slim4_at_psend(buf, sizeof(buf), pk, 3) && !strcmp(buf, "AT+PSEND=5300FF"), "psend '%s'", buf);
    CHECK(!slim4_at_psend(buf, 12, pk, 3), "psend refuses a short buffer");
    /* ping packets */
    slim4_radio_ping_t a = {.reply = false, .seq = 7, .sender = 0xA1B2C3D4u}, b;
    uint8_t pkt[SLIM4_RADIO_PING_LEN];
    slim4_radio_ping_encode(&a, pkt);
    CHECK(slim4_radio_ping_decode(pkt, sizeof(pkt), &b) && !b.reply && b.seq == 7 && b.sender == 0xA1B2C3D4u, "ping round trip");
    slim4_radio_ping_t r = {.reply = true, .seq = 9, .sender = 0x01020304u, .rssi_heard = -97};
    slim4_radio_ping_encode(&r, pkt);
    CHECK(slim4_radio_ping_decode(pkt, sizeof(pkt), &b) && b.reply && b.seq == 9 && b.rssi_heard == -97, "reply round trip");
    CHECK(!slim4_radio_ping_decode(pkt, 7, &b), "short packet refused");
    pkt[0] = 'X';
    CHECK(!slim4_radio_ping_decode(pkt, sizeof(pkt), &b), "foreign packet refused");
    /* a ping survives the trip through AT+PSEND hex and +EVT:RXP2P parsing */
    slim4_radio_ping_encode(&a, pkt);
    CHECK(slim4_at_psend(buf, sizeof(buf), pkt, sizeof(pkt)), "psend of a ping");
    char ev[80];
    snprintf(ev, sizeof(ev), "+EVT:RXP2P:-80:9:%s", buf + 9);
    slim4_at_parse(ev, &at);
    CHECK(at.kind == SLIM4_AT_RX && slim4_radio_ping_decode(at.payload, at.len, &b) && b.seq == 7, "ping through AT text");
    /* self-test judgement */
    slim4_radio_probe_t p = good();
    expect(&p, SLIM4_ST_PASS, "RADIO RAK3172 OK", "good module");
    memset(&p, 0, sizeof(p)); p.uart_ready = true; p.nwm = -1;
    expect(&p, SLIM4_ST_INFO, "RADIO NOT FITTED", "no module: nothing drives the line");
    p = good(); p.uart_ready = false;
    expect(&p, SLIM4_ST_FAIL, "RADIO UART SETUP FAILED", "UART driver fault");
    p = good(); p.answered = false; p.version[0] = '\0';
    expect(&p, SLIM4_ST_FAIL, "RADIO NO ANSWER TO AT", "TX line open or BOOT0 high");
    p = good(); p.rx_low_in_reset = false;
    expect(&p, SLIM4_ST_FAIL, "RADIO RESET NOT SEEN", "NRST open");
    p = good(); p.version[0] = '\0'; p.nwm = 1;
    expect(&p, SLIM4_ST_PASS, "RADIO RAK3172 OK", "answers, no version, LoRaWAN mode");
    if (fails) { printf("%d of %d radio checks failed\n", fails, checks); return 1; }
    printf("radio logic: %d checks passed\n", checks);
    return 0;
}
