/* Host test of the self-test decisions in components/slim4_bsp/slim4_selftest_logic.c (compiled in, no ESP-IDF).
 * Build and run: sh tests/host/run.sh. A simulated board (each net's pull resistor, open pads, wrong values, held
 * switches, solder bridges) produces the readings the GPIO steps in slim4_selftest.c would take, in the same order;
 * each case checks what the self-test reports. Not a substitute for running it on a board. */
#include <ctype.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include "slim4_pins.h"
#include "../../components/slim4_bsp/slim4_selftest_logic.c"

#define N SLIM4_ST_PIN_COUNT

/* ---- simulated board ---- */
typedef struct {
    bool open_pad[SLIM4_ST_MAX_PINS];      /* U1 pad not soldered: the pin sees nothing of the net */
    bool no_resistor[SLIM4_ST_MAX_PINS];   /* pull resistor missing */
    bool weak[SLIM4_ST_MAX_PINS];          /* 100 k fitted where 10 k belongs */
    int held[SLIM4_ST_MAX_PINS];           /* -1 free; 0/1 held there by a switch, chip or rail short */
    int group[SLIM4_ST_MAX_PINS];          /* nets joined by a bridge share a group */
    int32_t rise_us;                       /* PWR_WAKE rise time with the pull and capacitor */
} sim_t;

static size_t idx(const char *net)
{
    for (size_t i = 0; i < N; ++i) {
        if (!strcmp(SLIM4_ST_PINS[i].net, net)) return i;
    }
    printf("no pin %s\n", net);
    return 0;
}

static void sim_good(sim_t *s)
{
    memset(s, 0, sizeof(*s));
    for (size_t i = 0; i < N; ++i) {
        s->held[i] = -1;
        s->group[i] = (int)i;
    }
    s->rise_us = 700;
}

static void bridge(sim_t *s, const char *a, const char *b)
{
    s->group[idx(b)] = s->group[idx(a)];
}

/* Level the net settles to with U1's pull `upull` (-1 none, 0 down, 1 up) and nothing driven. */
static int net_level(const sim_t *s, size_t i, int upull)
{
    if (s->held[i] >= 0) return s->held[i];
    const int rest = slim4_st_rest_level(&SLIM4_ST_PINS[i]);
    if (s->open_pad[i] || s->no_resistor[i] || rest < 0) return upull;   /* -1: keeps what it had (caller) */
    if (upull >= 0 && upull != rest) {
        const bool strong = SLIM4_ST_PINS[i].pull == SLIM4_PULL_UP_10K || SLIM4_ST_PINS[i].pull == SLIM4_PULL_DOWN_10K;
        return (strong && !s->weak[i]) ? rest : upull;                  /* 10 k beats 45 k; 100 k does not */
    }
    return rest;
}

/* slim4_selftest.c pull_check(), step for step. */
static slim4_pull_reading_t sim_pull_check(const sim_t *s, size_t i)
{
    const slim4_pin_desc_t *p = &SLIM4_ST_PINS[i];
    slim4_pull_reading_t r = {.same = -1, .opposite = -1, .released = -1, .rise_us = -1};
    const int rest = slim4_st_rest_level(p);
    r.same = (int8_t)net_level(s, i, rest);
    if (r.same != rest) return r;
    if (slim4_st_opposite_allowed(p)) r.opposite = (int8_t)net_level(s, i, !rest);
    if (p->drive_ok) {
        const int after = net_level(s, i, -1);
        r.released = (int8_t)(after < 0 ? !rest : after);   /* a pin with nothing pulling keeps the driven level */
        if (p->rc_timed) r.rise_us = r.released == rest ? s->rise_us : INT32_MAX;
    }
    return r;
}

/* slim4_selftest.c short_scan(): the driven pin forces its whole group, unless something holds the group. */
static void sim_scan(const sim_t *s, const slim4_pull_result_t pull[], slim4_short_scan_t *scan, bool skip_bridges)
{
    slim4_st_scan_init(scan);
    int rest_at[SLIM4_ST_MAX_PINS];
    for (size_t i = 0; i < N; ++i) {
        const int rest = slim4_st_rest_level(&SLIM4_ST_PINS[i]);
        int lvl = net_level(s, i, rest >= 0 ? rest : 0);
        if (lvl < 0) lvl = 0;
        for (size_t j = 0; j < N && !skip_bridges; ++j) {
            if (j != i && s->group[j] == s->group[i] && s->held[j] >= 0) lvl = s->held[j];
        }
        rest_at[i] = lvl;
        scan->baseline[i] = slim4_st_is_victim(&SLIM4_ST_PINS[i], pull[i]) ? (int8_t)lvl : -1;
    }
    for (size_t a = 0; a < N; ++a) {
        bool hi, lo;
        slim4_st_drive_plan(&SLIM4_ST_PINS[a], pull[a], scan->baseline[a], &hi, &lo);
        for (int level = 1; level >= 0; --level) {
            if ((level && !hi) || (!level && !lo)) continue;
            int forced = level;
            if (!s->open_pad[a]) {
                if (s->held[a] >= 0) forced = s->held[a];
                for (size_t j = 0; j < N && !skip_bridges; ++j) {
                    if (s->group[j] == s->group[a] && s->held[j] >= 0) forced = s->held[j];
                }
            }
            for (size_t v = 0; v < N; ++v) {
                if (v == a || scan->baseline[v] < 0) continue;
                const bool joined = !skip_bridges && !s->open_pad[a] && !s->open_pad[v] && s->group[v] == s->group[a];
                (level ? scan->when_high : scan->when_low)[a][v] = (int8_t)(joined ? forced : rest_at[v]);
            }
            (level ? scan->readback_high : scan->readback_low)[a] = (int8_t)forced;
        }
    }
}

static slim4_st_report_t rep;
static slim4_pull_result_t pull_res[SLIM4_ST_MAX_PINS];
static slim4_short_scan_t scans[2];

/* Runs the whole GPIO self-test on the simulated board. second_scan_clean: the bridge shows in one scan only. */
static void run_pins(const sim_t *s, bool second_scan_clean)
{
    slim4_st_report_init(&rep);
    for (size_t i = 0; i < N; ++i) {
        const slim4_pin_desc_t *p = &SLIM4_ST_PINS[i];
        if (!slim4_st_has_pull_check(p)) { pull_res[i] = SLIM4_PULL_OK; continue; }
        const slim4_pull_reading_t r = sim_pull_check(s, i);
        pull_res[i] = slim4_st_classify_pull(p, &r);
        (void)slim4_st_report_pull(&rep, p, &r);
    }
    sim_scan(s, pull_res, &scans[0], false);
    sim_scan(s, pull_res, &scans[1], second_scan_clean);
    slim4_st_report_shorts(&rep, N, &scans[0], &scans[1]);
}

static const slim4_st_item_t *item(const char *id, const char *brief_part)
{
    for (uint8_t i = 0; i < rep.count; ++i) {
        if (!strcmp(rep.items[i].id, id) && (!brief_part || strstr(rep.items[i].brief, brief_part))) {
            return &rep.items[i];
        }
    }
    return NULL;
}

static bool verdict_is(const char *id, slim4_st_verdict_t v)
{
    const slim4_st_item_t *it = item(id, NULL);
    return it && it->verdict == v;
}

static int s_fail, s_pass;
static void check(const char *name, bool ok)
{
    printf("%s  %s\n", ok ? "PASS" : "FAIL", name);
    if (ok) ++s_pass; else ++s_fail;
}

static bool screen_text_ok(void)
{
    for (uint8_t i = 0; i < rep.count; ++i) {
        const char *b = rep.items[i].brief;
        if (strlen(b) > 35 || strlen(rep.items[i].id) > 14) return false;
        for (const char *c = b; *c; ++c) {
            if (!(isupper((unsigned char)*c) || isdigit((unsigned char)*c) || strchr(" ./-:_", *c))) {
                printf("    bad screen character '%c' in \"%s\"\n", *c, b);
                return false;
            }
        }
    }
    return true;
}

int main(void)
{
    sim_t s;

    /* the pin table against the firmware's pin map and the package */
    bool unique = true, pins_match = true;
    for (size_t i = 0; i < N; ++i) {
        for (size_t j = i + 1; j < N; ++j) {
            if (SLIM4_ST_PINS[i].gpio == SLIM4_ST_PINS[j].gpio || SLIM4_ST_PINS[i].pad == SLIM4_ST_PINS[j].pad) unique = false;
        }
    }
    const struct { const char *net; int gpio; } map[] = {
        {"BTN_LEFT", SLIM4_GPIO_BTN_LEFT}, {"BTN_RIGHT", SLIM4_GPIO_BTN_RIGHT}, {"DART_LEFT", SLIM4_GPIO_DART_LEFT},
        {"DART_RIGHT", SLIM4_GPIO_DART_RIGHT}, {"PWR_WAKE", SLIM4_GPIO_PWR_WAKE}, {"BOOT_STRAP", SLIM4_GPIO_BOOT_BTN},
        {"I2S_BCLK", SLIM4_GPIO_I2S_BCLK}, {"I2S_LRCLK", SLIM4_GPIO_I2S_LRCLK}, {"I2S_DOUT", SLIM4_GPIO_I2S_DOUT},
        {"AUDIO_SD_CTRL", SLIM4_GPIO_AUDIO_SD_CTRL}, {"BACKLIGHT_PWM", SLIM4_GPIO_BACKLIGHT_PWM},
        {"LCD_RESET_GATE", SLIM4_GPIO_LCD_RESET_GATE}, {"CHG_STATUS", SLIM4_GPIO_CHG_STATUS},
        {"PGOOD_STATUS", SLIM4_GPIO_PGOOD_STATUS}, {"USB_CURR_OUT1", SLIM4_GPIO_USB_CURR_OUT1},
        {"USB_CURR_OUT2", SLIM4_GPIO_USB_CURR_OUT2}, {"BQ_EN1", SLIM4_GPIO_BQ_EN1}, {"BQ_EN2", SLIM4_GPIO_BQ_EN2},
        {"BAT_ADC", SLIM4_GPIO_BAT_ADC},
    };
    for (size_t k = 0; k < sizeof(map) / sizeof(map[0]); ++k) {
        if (SLIM4_ST_PINS[idx(map[k].net)].gpio != map[k].gpio) pins_match = false;
    }
    check("pin table: every GPIO and pad once, the 19 board nets on slim4_pins.h's GPIOs", unique && pins_match && N <= SLIM4_ST_MAX_PINS);
    check("pin table: the charger-mode pins BQ_EN1/BQ_EN2 are never driven",
          !SLIM4_ST_PINS[idx("BQ_EN1")].drive_ok && !SLIM4_ST_PINS[idx("BQ_EN2")].drive_ok);

    check("pin table: the nets with 100 nF (PWR_WAKE C601, BAT_ADC C603) get the long drive, and only they",
          SLIM4_ST_PINS[idx("PWR_WAKE")].capacitor && SLIM4_ST_PINS[idx("BAT_ADC")].capacitor &&
          !SLIM4_ST_PINS[idx("BTN_LEFT")].capacitor && !SLIM4_ST_PINS[idx("LCD_RESET_GATE")].capacitor);

    /* a good board */
    sim_good(&s);
    run_pins(&s, false);
    check("good board: every pull check PASS", rep.fail == 0 && verdict_is("BTN_LEFT", SLIM4_ST_PASS) &&
          verdict_is("BQ_EN2", SLIM4_ST_PASS) && verdict_is("LCD_RESET_GATE", SLIM4_ST_PASS) &&
          verdict_is("PWR_WAKE", SLIM4_ST_PASS) && verdict_is("BACKLIGHT_PWM", SLIM4_ST_PASS));
    check("good board: SHORTS PASS, all 19 neighbouring pad pairs tested", verdict_is("SHORTS", SLIM4_ST_PASS) &&
          item("SHORTS", "19 OF 19") != NULL);
    check("good board: screen lines fit (35 characters, drawable)", screen_text_ok());

    /* charger outputs asserted (USB plugged in, charging) */
    sim_good(&s);
    s.held[idx("PGOOD_STATUS")] = 0;
    s.held[idx("CHG_STATUS")] = 0;
    run_pins(&s, false);
    check("PGOOD and CHG asserted: INFO, not FAIL; no short", verdict_is("PGOOD_STATUS", SLIM4_ST_INFO) &&
          verdict_is("CHG_STATUS", SLIM4_ST_INFO) && rep.fail == 0 && verdict_is("SHORTS", SLIM4_ST_PASS));
    check("PGOOD asserted: its neighbour GPIO45 still tests the pad pair", item("SHORTS", "19 OF 19") != NULL);

    /* solder bridges on U1 */
    sim_good(&s);
    bridge(&s, "BTN_LEFT", "BTN_RIGHT");
    run_pins(&s, false);
    check("bridge pads 1-2: SHORT BTN_LEFT - BTN_RIGHT", item("SHORT", "BTN_LEFT - BTN_RIGHT") != NULL &&
          strstr(item("SHORT", NULL)->detail, "both scans") && strstr(item("SHORT", NULL)->detail, "neighbouring pads"));
    check("bridge pads 1-2: the pull checks still pass (same pull on both nets)", verdict_is("BTN_LEFT", SLIM4_ST_PASS));
    sim_good(&s);
    bridge(&s, "I2S_DOUT", "AUDIO_SD_CTRL");
    run_pins(&s, false);
    check("bridge pads 7-8 (no pull - pull-down): SHORT found", item("SHORT", "I2S_DOUT - AUDIO_SD_CTRL") != NULL);
    sim_good(&s);
    bridge(&s, "BQ_EN1", "GPIO14");
    run_pins(&s, false);
    check("bridge BQ_EN1 (never driven) to unused GPIO14: SHORT found from GPIO14", item("SHORT", "BQ_EN1 - GPIO14") != NULL);
    sim_good(&s);
    bridge(&s, "GPIO45", "BQ_EN2");
    run_pins(&s, false);
    check("bridge unused GPIO45 to BQ_EN2: SHORT found", item("SHORT", "GPIO45 - BQ_EN2") != NULL);
    sim_good(&s);
    bridge(&s, "PWR_WAKE", "BTN_LEFT");
    run_pins(&s, false);
    check("bridge pads 104-1 (corner): SHORT found, called neighbouring", item("SHORT", "BTN_LEFT - PWR_WAKE") != NULL &&
          strstr(item("SHORT", NULL)->detail, "neighbouring pads"));
    sim_good(&s);
    bridge(&s, "BAT_ADC", "USB_CURR_OUT2");
    run_pins(&s, false);
    check("bridge BAT_ADC (driven, never read) to USB_CURR_OUT2: SHORT found", item("SHORT", "BAT_ADC - USB_CURR_OUT2") != NULL);
    sim_good(&s);
    bridge(&s, "DART_LEFT", "DART_RIGHT");
    run_pins(&s, true);
    check("bridge seen in one scan of two: SHORT, marked intermittent", item("SHORT", "DART_LEFT - DART_RIGHT") != NULL &&
          strstr(item("SHORT", NULL)->detail, "intermittent"));

    sim_good(&s);
    bridge(&s, "CHG_STATUS", "LCD_RESET_GATE");
    run_pins(&s, true);
    check("link with CHG (a status output) in one scan only: INFO LINK_ONCE, not FAIL", item("LINK_ONCE", NULL) &&
          verdict_is("LINK_ONCE", SLIM4_ST_INFO) && item("SHORT", NULL) == NULL);
    sim_good(&s);
    bridge(&s, "CHG_STATUS", "LCD_RESET_GATE");
    run_pins(&s, false);
    check("link with CHG in both scans: SHORT FAIL", item("SHORT", "LCD_RESET_GATE - CHG_STATUS") != NULL);

    /* open joints and missing or wrong parts */
    sim_good(&s);
    s.open_pad[idx("BTN_RIGHT")] = true;
    run_pins(&s, false);
    check("U1 pad 2 open: BTN_RIGHT FAIL, OPEN - PAD 2 OR R112", item("BTN_RIGHT", "OPEN - PAD 2 OR R112") &&
          verdict_is("BTN_RIGHT", SLIM4_ST_FAIL));
    check("U1 pad 2 open: no false short", item("SHORT", NULL) == NULL && item("DRIVE", NULL) == NULL);
    sim_good(&s);
    s.no_resistor[idx("LCD_RESET_GATE")] = true;
    run_pins(&s, false);
    check("R308 (100 k) missing: LCD_RESET_GATE OPEN", item("LCD_RESET_GATE", "OPEN - PAD 11 OR R308") != NULL);
    sim_good(&s);
    s.no_resistor[idx("BACKLIGHT_PWM")] = true;
    run_pins(&s, false);
    check("R422 (100 k pull-down) missing: BACKLIGHT_PWM OPEN", item("BACKLIGHT_PWM", "OPEN") != NULL);
    sim_good(&s);
    s.weak[idx("BTN_LEFT")] = true;
    run_pins(&s, false);
    check("100 k fitted at R111: BTN_LEFT WEAK PULL - R111 NOT 10K", item("BTN_LEFT", "WEAK PULL - R111 NOT 10K") != NULL);
    sim_good(&s);
    s.weak[idx("BQ_EN1")] = true;
    run_pins(&s, false);
    check("100 k fitted at R603 (BQ_EN1, never driven): FAIL", verdict_is("BQ_EN1", SLIM4_ST_FAIL));
    sim_good(&s);
    s.no_resistor[idx("BQ_EN2")] = true;
    run_pins(&s, false);
    check("R604 missing (BQ_EN2): not testable without risking charger suspend; PASS says so",
          verdict_is("BQ_EN2", SLIM4_ST_PASS) && strstr(item("BQ_EN2", NULL)->detail, "suspend the charger"));
    check("BQ_EN2 is never pulled toward its active level; BQ_EN1 still is checked against U1's pull",
          !slim4_st_opposite_allowed(&SLIM4_ST_PINS[idx("BQ_EN2")]) && slim4_st_opposite_allowed(&SLIM4_ST_PINS[idx("BQ_EN1")]));
    sim_good(&s);
    s.open_pad[idx("USB_CURR_OUT1")] = true;
    run_pins(&s, false);
    check("U1 pad 84 open (TUSB320 OUT1): FAIL", verdict_is("USB_CURR_OUT1", SLIM4_ST_FAIL));

    sim_good(&s);
    s.open_pad[idx("BQ_EN1")] = true;
    run_pins(&s, false);
    check("BQ_EN1 pad open (never driven, not readable): both its pad pairs untested, SHORTS INFO not PASS, BQ_EN1 FAIL",
          verdict_is("SHORTS", SLIM4_ST_INFO) && item("SHORTS", "17 OF 19") && verdict_is("BQ_EN1", SLIM4_ST_FAIL));
    slim4_st_report_init(&rep);
    slim4_st_scan_init(&scans[0]);
    slim4_st_scan_init(&scans[1]);
    scans[0].readback_high[idx("CHG_STATUS")] = 0;   /* U10 pulled CHG low during one scan only */
    scans[1].readback_high[idx("CHG_STATUS")] = 1;
    slim4_st_report_shorts(&rep, N, &scans[0], &scans[1]);
    check("CHG read low while driven high in one scan of two: DRIVE_ONCE INFO, no DRIVE FAIL",
          verdict_is("DRIVE_ONCE", SLIM4_ST_INFO) && item("DRIVE", NULL) == NULL);
    scans[1].readback_high[idx("CHG_STATUS")] = 0;
    slim4_st_report_init(&rep);
    slim4_st_report_shorts(&rep, N, &scans[0], &scans[1]);
    check("CHG cannot be driven high in both scans: DRIVE FAIL", verdict_is("DRIVE", SLIM4_ST_FAIL));

    /* PWR_WAKE: R110 10 k with C601 100 nF */
    sim_good(&s);
    s.rise_us = 15;
    run_pins(&s, false);
    check("C601 missing (rises in 15 us): PWR_WAKE FAIL, C601", item("PWR_WAKE", "C601 MISSING") != NULL);
    sim_good(&s);
    s.rise_us = 5600;
    run_pins(&s, false);
    check("PWR_WAKE rises in 5.6 ms (CHIP_PU's 1 uF joined): FAIL, too slowly", item("PWR_WAKE", "TOO SLOWLY") != NULL);
    sim_good(&s);
    s.rise_us = 690;
    run_pins(&s, false);
    check("PWR_WAKE rises in 0.69 ms: PASS, shows 0.69 MS", item("PWR_WAKE", "0.69 MS") && verdict_is("PWR_WAKE", SLIM4_ST_PASS));

    /* held nets */
    sim_good(&s);
    s.held[idx("DART_LEFT")] = 0;
    run_pins(&s, false);
    check("SW3 held down (or DART_LEFT to GND): FAIL HELD LOW, never driven high",
          item("DART_LEFT", "HELD LOW") && scans[0].readback_high[idx("DART_LEFT")] == -1);
    sim_good(&s);
    s.held[idx("BACKLIGHT_PWM")] = 1;
    run_pins(&s, false);
    check("BACKLIGHT_PWM shorted to 3V3 (pad 9): FAIL HELD HIGH - SHORT TO 3V3, never driven low",
          item("BACKLIGHT_PWM", "HELD HIGH - SHORT TO 3V3") && scans[0].readback_low[idx("BACKLIGHT_PWM")] == -1);
    sim_good(&s);
    s.held[idx("GPIO12")] = 0;
    run_pins(&s, false);
    check("unused GPIO12 shorted to GND: DRIVE FAIL, cannot be driven high", item("DRIVE", "DRIVEN HIGH") != NULL);
    sim_good(&s);
    s.held[idx("GPIO18")] = 1;
    run_pins(&s, false);
    check("unused GPIO18 shorted to 3V3: DRIVE FAIL, cannot be driven low", item("DRIVE", "DRIVEN LOW") != NULL);
    sim_good(&s);
    bridge(&s, "CHG_STATUS", "GPIO12");
    s.held[idx("CHG_STATUS")] = 0;
    run_pins(&s, false);
    check("GPIO12 bridged to CHG while U10 asserts it: reported (DRIVE or SHORT), CHG INFO",
          (item("DRIVE", NULL) || item("SHORT", NULL)) && verdict_is("CHG_STATUS", SLIM4_ST_INFO));
    check("faults: screen lines fit (35 characters, drawable)", screen_text_ok());

    /* chip, memory, reset */
    slim4_st_report_init(&rep);
    slim4_st_judge_chip(&rep, 301);
    check("chip v3.1: PASS", verdict_is("CHIP", SLIM4_ST_PASS) && item("CHIP", "V3.1"));
    slim4_st_report_init(&rep);
    slim4_st_judge_chip(&rep, 300);
    check("chip v3.0: PASS, notes v3.1 preferred", verdict_is("CHIP", SLIM4_ST_PASS) && strstr(rep.items[0].detail, "v3.1 preferred"));
    slim4_st_report_init(&rep);
    slim4_st_judge_chip(&rep, 101);
    check("chip v1.1: FAIL", verdict_is("CHIP", SLIM4_ST_FAIL));
    slim4_st_report_init(&rep);
    slim4_st_judge_psram(&rep, 32u << 20);
    slim4_st_judge_flash(&rep, true, 0xEF4020, true, 64u << 20);
    check("32 MiB PSRAM, W25Q512JV 64 MiB: PASS", verdict_is("PSRAM", SLIM4_ST_PASS) && verdict_is("FLASH", SLIM4_ST_PASS));
    slim4_st_report_init(&rep);
    slim4_st_judge_psram(&rep, 16u << 20);
    slim4_st_judge_flash(&rep, true, 0xEF4019, true, 32u << 20);
    check("16 MiB PSRAM, W25Q256 (EF4019): both FAIL", verdict_is("PSRAM", SLIM4_ST_FAIL) &&
          item("FLASH", "FLASH ID EF4019") && verdict_is("FLASH", SLIM4_ST_FAIL));
    slim4_st_report_init(&rep);
    slim4_st_judge_flash(&rep, true, 0xEF4020, true, 32u << 20);
    slim4_st_judge_reset(&rep, true, "BROWNOUT");
    check("flash ID right, size wrong: FAIL; brownout reset: FAIL", verdict_is("FLASH", SLIM4_ST_FAIL) &&
          verdict_is("RESET", SLIM4_ST_FAIL));
    slim4_st_report_init(&rep);
    slim4_st_judge_reset(&rep, false, "POWER-ON");
    check("power-on reset: INFO", verdict_is("RESET", SLIM4_ST_INFO));

    /* display */
    slim4_panel_probe_t pr = {0};
    slim4_st_report_init(&rep);
    pr.stopped_at = "MIPI D-PHY 2.5 V rail";
    slim4_st_judge_panel(&rep, &pr);
    check("probe not attempted: FAIL, panel not usable", verdict_is("PANEL", SLIM4_ST_FAIL) && !slim4_st_panel_usable(&pr));
    slim4_st_report_init(&rep);
    pr.attempted = true;
    pr.stopped_at = "ID read (no answer after the bus turnaround on lane 0)";
    slim4_st_judge_panel(&rep, &pr);
    check("no answer on lane 0: FAIL NO ANSWER, bring-up stops (not usable)", item("PANEL", "NO ANSWER") &&
          !slim4_st_panel_usable(&pr) && rep.count == 1);
    slim4_st_report_init(&rep);
    pr.int_st0 = 1u << 10;                   /* the panel sent an error report (checksum) instead of the data */
    slim4_st_judge_panel(&rep, &pr);
    check("no data but an error report: NO ANSWER lists the panel's checksum error", item("PANEL", "NO ANSWER") &&
          strstr(item("PANEL", NULL)->detail, "checksum error"));
    slim4_st_report_init(&rep);
    pr = (slim4_panel_probe_t){.attempted = true, .answered = true, .repeat_ok = true, .id = {0x98, 0x81, 0x0C}};
    slim4_st_judge_panel(&rep, &pr);
    check("ID 98 81 0C, no flags: PANEL PASS, DSI_LANE0 PASS, usable", verdict_is("PANEL", SLIM4_ST_PASS) &&
          verdict_is("DSI_LANE0", SLIM4_ST_PASS) && slim4_st_panel_usable(&pr));
    slim4_st_report_init(&rep);
    pr.id[2] = 0x1C;
    slim4_st_judge_panel(&rep, &pr);
    check("ID 98 81 1C (datasheet) and 98 81 5C (Espressif's log): PANEL PASS, version byte shown",
          verdict_is("PANEL", SLIM4_ST_PASS) && item("PANEL", "98 81 1C"));
    slim4_st_report_init(&rep);
    pr.id[1] = 0x80;
    pr.int_st0 = 1u << 7;                    /* the panel reports contention */
    slim4_st_judge_panel(&rep, &pr);
    check("ID 98 80 1C and a contention report: PANEL FAIL, DSI_LANE0 FAIL naming contention",
          verdict_is("PANEL", SLIM4_ST_FAIL) && verdict_is("DSI_LANE0", SLIM4_ST_FAIL) &&
          strstr(item("DSI_LANE0", NULL)->detail, "contention"));
    slim4_st_report_init(&rep);
    pr = (slim4_panel_probe_t){.attempted = true, .answered = true, .repeat_ok = true, .id = {0x98, 0x81, 0x0C}, .int_st0 = 1u << 19};
    slim4_st_judge_panel(&rep, &pr);
    check("D-PHY ErrContentionLP0: DSI_LANE0 FAIL", verdict_is("DSI_LANE0", SLIM4_ST_FAIL) &&
          strstr(item("DSI_LANE0", NULL)->detail, "ErrContentionLP0"));
    slim4_st_report_init(&rep);
    pr = (slim4_panel_probe_t){.attempted = true, .answered = true, .repeat_ok = true, .id = {0x98, 0x81, 0x0C}, .int_st1 = 1u << 8};
    slim4_st_judge_panel(&rep, &pr);
    check("host command FIFO error: FAIL as a firmware fault", item("DSI_LANE0", "FIFO") && verdict_is("DSI_LANE0", SLIM4_ST_FAIL));
    slim4_st_report_init(&rep);
    pr = (slim4_panel_probe_t){.attempted = true, .answered = true, .repeat_ok = true, .id = {0x98, 0x81, 0x0C},
                               .stopped_at = "DMA2D framebuffer copy path"};
    slim4_st_judge_panel(&rep, &pr);
    check("panel answered, bring-up failed later: DISPLAY FAIL with the stage", verdict_is("DISPLAY", SLIM4_ST_FAIL) &&
          strstr(item("DISPLAY", NULL)->detail, "DMA2D"));
    slim4_st_report_init(&rep);
    pr = (slim4_panel_probe_t){.attempted = true, .answered = true, .repeat_ok = true, .id = {0x98, 0x81, 0x0C},
                               .int_st0_first = 1u << 0};   /* SoT error left over from power-up, then clean */
    slim4_st_judge_panel(&rep, &pr);
    check("error bit in the first exchange only (power-up leftover): DSI_LANE0 PASS, first exchange shown",
          verdict_is("DSI_LANE0", SLIM4_ST_PASS) && strstr(item("DSI_LANE0", NULL)->detail, "int_st0=00000001"));
    slim4_st_report_init(&rep);
    pr.repeat_ok = false;
    slim4_st_judge_panel(&rep, &pr);
    check("register 0x00 reads back differently the second time: DSI_LANE0 FAIL", verdict_is("DSI_LANE0", SLIM4_ST_FAIL) &&
          strstr(item("DSI_LANE0", NULL)->detail, "read back differently"));
    slim4_st_report_init(&rep);
    slim4_st_judge_vsync(&rep, true, 59);
    slim4_st_judge_vsync(&rep, false, 0);
    check("59 frames a second: VIDEO INFO (look at the bars); no display: no VIDEO line",
          verdict_is("VIDEO", SLIM4_ST_INFO) && rep.count == 1);
    slim4_st_report_init(&rep);
    slim4_st_judge_vsync(&rep, true, 0);
    check("display up but no frames: VIDEO FAIL", verdict_is("VIDEO", SLIM4_ST_FAIL));

    /* power */
    slim4_st_power_t pw = {.ready = true, .usb_host_seen = true, .pgood_low = true, .usb_current = 1, .battery_mv = 4100};
    slim4_st_report_init(&rep);
    slim4_st_judge_power(&rep, &pw);
    check("USB host and PGOOD: USB_INPUT PASS, battery INFO", verdict_is("USB_INPUT", SLIM4_ST_PASS) &&
          verdict_is("BATTERY", SLIM4_ST_INFO) && rep.fail == 0);
    pw.pgood_low = false;
    slim4_st_report_init(&rep);
    slim4_st_judge_power(&rep, &pw);
    check("USB host without PGOOD: USB_INPUT FAIL naming J2 and U10", verdict_is("USB_INPUT", SLIM4_ST_FAIL) &&
          strstr(item("USB_INPUT", NULL)->detail, "J2") && strstr(item("USB_INPUT", NULL)->detail, "U10"));
    pw.usb_host_seen = false;
    pw.battery_fault = true;
    slim4_st_report_init(&rep);
    slim4_st_judge_power(&rep, &pw);
    check("no USB host: USB_INPUT INFO; battery fault: BATTERY FAIL", verdict_is("USB_INPUT", SLIM4_ST_INFO) &&
          verdict_is("BATTERY", SLIM4_ST_FAIL));
    pw.ready = false;
    slim4_st_report_init(&rep);
    slim4_st_judge_power(&rep, &pw);
    check("power service down: POWER FAIL only", verdict_is("POWER", SLIM4_ST_FAIL) && rep.count == 1);
    check("chip, display, power: screen lines fit", screen_text_ok());

    /* the report itself */
    slim4_st_report_init(&rep);
    for (int i = 0; i < SLIM4_ST_MAX_ITEMS + 12; ++i) slim4_st_add(&rep, "X", (slim4_st_verdict_t)(i % 3), "B", "d%d", i);
    check("report overflow: list stops at the limit, counts include every check",
          rep.count == SLIM4_ST_MAX_ITEMS && rep.overflow && rep.pass + rep.fail + rep.info == SLIM4_ST_MAX_ITEMS + 12);

    printf("\n%d passed, %d failed\n", s_pass, s_fail);
    return s_fail ? 1 : 0;
}
