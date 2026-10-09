/* SLIM4 self-test decisions: what a set of readings means for the board. No ESP-IDF dependency, so the host tests
 * (tests/host/test_selftest_logic.c) run every rule. The nets, pads and parts below are PCB R26's (U1 pad table:
 * tools/u1_pad_nets.json; parts: hardware/slim4/LAYERS/01_PCB/SLIM4_R26_PCB_LAYER.json). */
#include "slim4_selftest.h"

#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

/* GPIO, pad, net, board pull, role, pull resistor, load, drive_ok, capacitor, rc_timed.
 * BQ_EN1/BQ_EN2 are never driven: EN1 low or EN2 high changes the charger's input limit, and both high suspends
 * the USB input. Their pull checks use U1's internal pulls only. The unused pads are the ones beside a tested net
 * whose GPIO number is certain from the package (GPIO12 pad 13, GPIO14/15 pads 15/16, GPIO18 pad 19, GPIO45 pad 87:
 * pads 9, 21 and 85 are supply pads, so GPIO9.. sit one pad up and GPIO44/46 at pads 86/88). */
const slim4_pin_desc_t SLIM4_ST_PINS[] = {
    {1, 1, "BTN_LEFT", SLIM4_PULL_UP_10K, SLIM4_ROLE_SWITCH, "R111 10k", "SW1", true, false, false},
    {2, 2, "BTN_RIGHT", SLIM4_PULL_UP_10K, SLIM4_ROLE_SWITCH, "R112 10k", "SW2", true, false, false},
    {3, 3, "DART_LEFT", SLIM4_PULL_UP_10K, SLIM4_ROLE_SWITCH, "R601 10k", "SW3", true, false, false},
    {4, 4, "DART_RIGHT", SLIM4_PULL_UP_10K, SLIM4_ROLE_SWITCH, "R602 10k", "SW4", true, false, false},
    {5, 5, "I2S_BCLK", SLIM4_PULL_NONE, SLIM4_ROLE_SIGNAL, NULL, "U8/U9 MAX98357A BCLK", true, false, false},
    {6, 6, "I2S_LRCLK", SLIM4_PULL_NONE, SLIM4_ROLE_SIGNAL, NULL, "U8/U9 MAX98357A LRCLK", true, false, false},
    {7, 7, "I2S_DOUT", SLIM4_PULL_NONE, SLIM4_ROLE_SIGNAL, NULL, "U8/U9 MAX98357A DIN", true, false, false},
    {8, 8, "AUDIO_SD_CTRL", SLIM4_PULL_DOWN_100K, SLIM4_ROLE_PASSIVE, "R504 100k", "R501/R502 to U8/U9 SD_MODE", true, false, false},
    {9, 10, "BACKLIGHT_PWM", SLIM4_PULL_DOWN_100K, SLIM4_ROLE_PASSIVE, "R422 100k", "U7 TPS61165 CTRL", true, false, false},
    {10, 11, "LCD_RESET_GATE", SLIM4_PULL_UP_100K, SLIM4_ROLE_PASSIVE, "R308 100k", "Q1 2N7002 gate", true, false, false},
    {11, 12, "CHG_STATUS", SLIM4_PULL_UP_100K, SLIM4_ROLE_STATUS, "R420 100k", "U10 BQ24074 CHG", true, false, false},
    {12, 13, "GPIO12", SLIM4_PULL_NONE, SLIM4_ROLE_UNUSED, NULL, "no net", true, false, false},
    {13, 14, "BQ_EN1", SLIM4_PULL_UP_10K, SLIM4_ROLE_PASSIVE, "R603 10k", "U10 BQ24074 EN1", false, false, false},
    {14, 15, "GPIO14", SLIM4_PULL_NONE, SLIM4_ROLE_UNUSED, NULL, "no net", true, false, false},
    {15, 16, "GPIO15", SLIM4_PULL_NONE, SLIM4_ROLE_UNUSED, NULL, "no net", true, false, false},
    {16, 17, "BAT_ADC", SLIM4_PULL_NONE, SLIM4_ROLE_ANALOG, NULL, "R418 100k / R419 33k, C603", true, true, false},
    {17, 18, "USB_CURR_OUT2", SLIM4_PULL_UP_10K, SLIM4_ROLE_STATUS, "R606 10k", "U13 TUSB320 OUT2", true, false, false},
    {18, 19, "GPIO18", SLIM4_PULL_NONE, SLIM4_ROLE_UNUSED, NULL, "no net", true, false, false},
    {35, 66, "BOOT_STRAP", SLIM4_PULL_UP_10K, SLIM4_ROLE_SWITCH, "R108 10k", "SW7", true, false, false},
    {43, 84, "USB_CURR_OUT1", SLIM4_PULL_UP_10K, SLIM4_ROLE_STATUS, "R605 10k", "U13 TUSB320 OUT1", true, false, false},
    {44, 86, "PGOOD_STATUS", SLIM4_PULL_UP_100K, SLIM4_ROLE_STATUS, "R421 100k", "U10 BQ24074 PGOOD", true, false, false},
    {45, 87, "GPIO45", SLIM4_PULL_NONE, SLIM4_ROLE_UNUSED, NULL, "no net", true, false, false},
    {46, 88, "BQ_EN2", SLIM4_PULL_DOWN_10K, SLIM4_ROLE_PASSIVE, "R604 10k", "U10 BQ24074 EN2", false, false, false},
    {0, 104, "PWR_WAKE", SLIM4_PULL_UP_10K, SLIM4_ROLE_SWITCH, "R110 10k", "C601 100nF, SW5", true, true, true},
};
const size_t SLIM4_ST_PIN_COUNT = sizeof(SLIM4_ST_PINS) / sizeof(SLIM4_ST_PINS[0]);

void slim4_st_report_init(slim4_st_report_t *rep)
{
    memset(rep, 0, sizeof(*rep));
}

const char *slim4_st_verdict_name(slim4_st_verdict_t verdict)
{
    switch (verdict) {
    case SLIM4_ST_PASS: return "PASS";
    case SLIM4_ST_FAIL: return "FAIL";
    default: return "INFO";
    }
}

void slim4_st_add(slim4_st_report_t *rep, const char *id, slim4_st_verdict_t verdict, const char *brief,
                  const char *detail_fmt, ...)
{
    if (verdict == SLIM4_ST_PASS) ++rep->pass;
    else if (verdict == SLIM4_ST_FAIL) ++rep->fail;
    else ++rep->info;
    if (rep->count >= SLIM4_ST_MAX_ITEMS) {
        rep->overflow = true;
        return;
    }
    slim4_st_item_t *it = &rep->items[rep->count++];
    snprintf(it->id, sizeof(it->id), "%s", id);
    it->verdict = verdict;
    snprintf(it->brief, sizeof(it->brief), "%s", brief);
    va_list ap;
    va_start(ap, detail_fmt);
    vsnprintf(it->detail, sizeof(it->detail), detail_fmt, ap);
    va_end(ap);
}

/* ---- GPIO nets ------------------------------------------------------------------------------------------- */

int slim4_st_rest_level(const slim4_pin_desc_t *pin)
{
    switch (pin->pull) {
    case SLIM4_PULL_UP_10K:
    case SLIM4_PULL_UP_100K: return 1;
    case SLIM4_PULL_DOWN_10K:
    case SLIM4_PULL_DOWN_100K: return 0;
    default: return -1;
    }
}

bool slim4_st_opposite_allowed(const slim4_pin_desc_t *pin)
{
    /* U1's pull against a 10 k resistor leaves the net at about 0.6 V or 2.7 V. On a pin the self-test never drives
     * (the charger's EN pins) a pull-down net is not pulled up: 0.6 V is above the BQ24074's 0.4 V EN low limit, and
     * EN2 high with EN1 high suspends the USB input. */
    if (pin->pull != SLIM4_PULL_UP_10K && pin->pull != SLIM4_PULL_DOWN_10K) return false;
    return pin->drive_ok || slim4_st_rest_level(pin) == 1;
}

bool slim4_st_has_pull_check(const slim4_pin_desc_t *pin)
{
    return pin->pull != SLIM4_PULL_NONE &&
           (pin->role == SLIM4_ROLE_SWITCH || pin->role == SLIM4_ROLE_STATUS || pin->role == SLIM4_ROLE_PASSIVE);
}

slim4_pull_result_t slim4_st_classify_pull(const slim4_pin_desc_t *pin, const slim4_pull_reading_t *r)
{
    const int rest = slim4_st_rest_level(pin);
    /* With U1's pull the same way as the board's, only something stronger holds the other level. */
    if (r->same >= 0 && r->same != rest) return SLIM4_PULL_HELD;
    /* Against U1's 45 k pull a 10 k resistor still wins. Losing means no resistor reaches the pad, or a higher
     * value: if the net still returns to its rest level when released, a pull is there, only too weak. */
    if (r->opposite >= 0 && r->opposite != rest) {
        return (r->released >= 0 && r->released == rest) ? SLIM4_PULL_WEAK : SLIM4_PULL_FLOATING;
    }
    /* Released with no pull from U1, a net with its resistor returns to rest within microseconds; an open pad keeps
     * the level it was driven to. */
    if (r->released >= 0 && r->released != rest) return SLIM4_PULL_FLOATING;
    if (pin->rc_timed && r->rise_us >= 0) {
        if (r->rise_us == INT32_MAX) return SLIM4_PULL_FLOATING;
        if (r->rise_us < SLIM4_ST_RC_MIN_US) return SLIM4_PULL_RC_FAST;
        if (r->rise_us > SLIM4_ST_RC_MAX_US) return SLIM4_PULL_RC_SLOW;
    }
    return SLIM4_PULL_OK;
}

/* Length of the part reference at the start of "R111 10k". */
static int ref_len(const char *part)
{
    const char *sp = part ? strchr(part, ' ') : NULL;
    return part ? (sp ? (int)(sp - part) : (int)strlen(part)) : 0;
}

static void readings_text(char *buf, size_t len, const slim4_pull_reading_t *r)
{
    char rise[24] = "";
    if (r->rise_us >= 0 && r->rise_us != INT32_MAX) snprintf(rise, sizeof(rise), " rise=%ldus", (long)r->rise_us);
    else if (r->rise_us == INT32_MAX) snprintf(rise, sizeof(rise), " rise=never");
    snprintf(buf, len, "same=%d opposite=%d released=%d%s", r->same, r->opposite, r->released, rise);
}

slim4_st_verdict_t slim4_st_report_pull(slim4_st_report_t *rep, const slim4_pin_desc_t *pin,
                                        const slim4_pull_reading_t *r)
{
    const slim4_pull_result_t res = slim4_st_classify_pull(pin, r);
    const bool up = slim4_st_rest_level(pin) == 1;
    char got[64];
    readings_text(got, sizeof(got), r);
    char brief[36];
    switch (res) {
    case SLIM4_PULL_OK:
        if (pin->rc_timed && r->rise_us >= 0) {
            /* OK means 200..3000 us, so the milliseconds have one digit */
            snprintf(brief, sizeof(brief), "PULL-UP AND 100NF OK %u.%02u MS", (unsigned)(r->rise_us / 1000) % 10u,
                     (unsigned)((r->rise_us % 1000) / 10) % 100u);
        } else {
            snprintf(brief, sizeof(brief), "%s OK", up ? "PULL-UP" : "PULL-DOWN");
        }
        if (r->opposite < 0 && r->released < 0) {
            slim4_st_add(rep, pin->net, SLIM4_ST_PASS, brief, "GPIO%u pad %u: rests %s as %s sets it; not tested "
                         "against U1's pull (that could suspend the charger), so an open pad or missing %s would read "
                         "the same (%s)", pin->gpio, pin->pad, up ? "high" : "low", pin->pull_part, pin->pull_part, got);
        } else {
            slim4_st_add(rep, pin->net, SLIM4_ST_PASS, brief, "GPIO%u pad %u: %s and pad joint good, %s on the net (%s)",
                         pin->gpio, pin->pad, pin->pull_part, pin->load, got);
        }
        return SLIM4_ST_PASS;
    case SLIM4_PULL_HELD:
        if (pin->role == SLIM4_ROLE_STATUS) {
            slim4_st_add(rep, pin->net, SLIM4_ST_INFO, "LOW - ASSERTED BY ITS CHIP",
                         "GPIO%u pad %u: held low by %s (asserted), so %s and the pad joint are not checked this boot; "
                         "a short to GND would read the same (%s)", pin->gpio, pin->pad, pin->load, pin->pull_part, got);
            return SLIM4_ST_INFO;
        }
        if (pin->role == SLIM4_ROLE_SWITCH) {
            slim4_st_add(rep, pin->net, SLIM4_ST_FAIL, "HELD LOW - PRESSED OR SHORT",
                         "GPIO%u pad %u: reads low with U1's pull-up on: %s pressed or stuck, or the net shorted to GND "
                         "(look at %s and U1 pad %u's neighbours) (%s)", pin->gpio, pin->pad, pin->load, pin->load,
                         pin->pad, got);
            return SLIM4_ST_FAIL;
        }
        slim4_st_add(rep, pin->net, SLIM4_ST_FAIL, up ? "HELD LOW - SHORT TO GND" : "HELD HIGH - SHORT TO 3V3",
                     "GPIO%u pad %u: reads %s with U1's pull the same way as %s: the net is shorted to %s "
                     "(look at U1 pad %u's neighbours and %s) (%s)", pin->gpio, pin->pad, up ? "low" : "high",
                     pin->pull_part, up ? "GND" : "3V3", pin->pad, pin->load, got);
        return SLIM4_ST_FAIL;
    case SLIM4_PULL_FLOATING:
        snprintf(brief, sizeof(brief), "OPEN - PAD %u OR %.*s", pin->pad, ref_len(pin->pull_part), pin->pull_part);
        slim4_st_add(rep, pin->net, SLIM4_ST_FAIL, brief,
                     "GPIO%u pad %u: no %s reaches the pad: U1 pad %u not soldered, or %s missing, open or of a much "
                     "higher value (%s)", pin->gpio, pin->pad, up ? "pull-up" : "pull-down", pin->pad, pin->pull_part,
                     got);
        return SLIM4_ST_FAIL;
    case SLIM4_PULL_WEAK:
        snprintf(brief, sizeof(brief), "WEAK PULL - %.*s NOT 10K", ref_len(pin->pull_part), pin->pull_part);
        slim4_st_add(rep, pin->net, SLIM4_ST_FAIL, brief,
                     "GPIO%u pad %u: the net returns to its rest level but loses to U1's 45 k internal pull: %s is "
                     "not 10 k (a 100 k part fitted?) (%s)", pin->gpio, pin->pad, pin->pull_part, got);
        return SLIM4_ST_FAIL;
    case SLIM4_PULL_RC_FAST:
        slim4_st_add(rep, pin->net, SLIM4_ST_FAIL, "RISES TOO FAST - C601 MISSING",
                     "GPIO%u pad %u: rises in %ld us, expected %d..%d us for R110 10k with C601 100nF: C601 missing "
                     "or open (%s)", pin->gpio, pin->pad, (long)r->rise_us, SLIM4_ST_RC_MIN_US, SLIM4_ST_RC_MAX_US,
                     got);
        return SLIM4_ST_FAIL;
    case SLIM4_PULL_RC_SLOW:
    default:
        slim4_st_add(rep, pin->net, SLIM4_ST_FAIL, "RISES TOO SLOWLY - EXTRA LOAD",
                     "GPIO%u pad %u: rises in %ld us, expected %d..%d us for R110 10k with C601 100nF: a larger "
                     "capacitor, leakage, or a short to another net with a capacitor (CHIP_PU on pad 103 has 1 uF) "
                     "(%s)", pin->gpio, pin->pad, (long)r->rise_us, SLIM4_ST_RC_MIN_US, SLIM4_ST_RC_MAX_US, got);
        return SLIM4_ST_FAIL;
    }
}

bool slim4_st_is_victim(const slim4_pin_desc_t *pin, slim4_pull_result_t pull)
{
    /* BAT_ADC sits near 1 V (a third of the cell): no logic level. A floating pad reads whatever it last held. */
    return pin->role != SLIM4_ROLE_ANALOG && pull != SLIM4_PULL_FLOATING;
}

void slim4_st_drive_plan(const slim4_pin_desc_t *pin, slim4_pull_result_t pull, int8_t baseline,
                         bool *drive_high, bool *drive_low)
{
    *drive_high = false;
    *drive_low = false;
    if (!pin->drive_ok) return;
    const int rest = slim4_st_rest_level(pin);
    /* Never drive against something holding the net: a pressed switch, an asserted status output, a short. */
    const bool held = pull == SLIM4_PULL_HELD || (rest >= 0 && baseline >= 0 && baseline != rest);
    *drive_high = !(held && rest == 1);
    *drive_low = !(held && rest == 0);
}

void slim4_st_scan_init(slim4_short_scan_t *scan)
{
    memset(scan, 0xFF, sizeof(*scan));   /* every entry -1: not run */
}

static bool link_seen(const slim4_short_scan_t *scan, size_t a, size_t v)
{
    if (a == v || scan->baseline[v] < 0) return false;
    const int hi = scan->when_high[a][v], lo = scan->when_low[a][v];
    if (hi >= 0 && lo >= 0) return hi == 1 && lo == 0;
    if (hi >= 0) return scan->baseline[v] == 0 && hi == 1;
    if (lo >= 0) return scan->baseline[v] == 1 && lo == 0;
    return false;
}

static bool covered_one_way(const slim4_short_scan_t *scan, size_t a, size_t v)
{
    if (a == v || scan->baseline[v] < 0) return false;
    const int hi = scan->when_high[a][v], lo = scan->when_low[a][v];
    return (hi >= 0 && lo >= 0) || (hi >= 0 && scan->baseline[v] == 0) || (lo >= 0 && scan->baseline[v] == 1);
}

size_t slim4_st_find_links(size_t n, const slim4_short_scan_t *scan, bool links[SLIM4_ST_MAX_PINS][SLIM4_ST_MAX_PINS])
{
    size_t count = 0;
    for (size_t a = 0; a < n; ++a) {
        for (size_t v = 0; v < n; ++v) {
            links[a][v] = link_seen(scan, a, v);
            if (links[a][v]) ++count;
        }
    }
    return count;
}

bool slim4_st_pair_covered(const slim4_short_scan_t *scan, size_t a, size_t b)
{
    return covered_one_way(scan, a, b) || covered_one_way(scan, b, a);
}

static bool pads_adjacent(unsigned p, unsigned q)
{
    const unsigned lo = p < q ? p : q, hi = p < q ? q : p;
    return hi - lo == 1 || (lo == 1 && hi == 104);   /* QFN-104: pad 104 wraps round to pad 1 */
}

void slim4_st_report_shorts(slim4_st_report_t *rep, size_t n, const slim4_short_scan_t *scan1,
                            const slim4_short_scan_t *scan2)
{
    static bool l1[SLIM4_ST_MAX_PINS][SLIM4_ST_MAX_PINS], l2[SLIM4_ST_MAX_PINS][SLIM4_ST_MAX_PINS];
    (void)slim4_st_find_links(n, scan1, l1);
    (void)slim4_st_find_links(n, scan2, l2);
    unsigned shorts = 0;
    for (size_t a = 0; a < n; ++a) {
        for (size_t b = a + 1; b < n; ++b) {
            const bool s1 = l1[a][b] || l1[b][a], s2 = l2[a][b] || l2[b][a];
            if (!s1 && !s2) continue;
            const slim4_pin_desc_t *pa = &SLIM4_ST_PINS[a], *pb = &SLIM4_ST_PINS[b];
            char brief[36];
            snprintf(brief, sizeof(brief), "%.14s - %.14s", pa->net, pb->net);
            if (!(s1 && s2) && (pa->role == SLIM4_ROLE_STATUS || pb->role == SLIM4_ROLE_STATUS)) {
                /* Seen once, with a chip's status output in the pair: the output may have switched mid-scan. */
                slim4_st_add(rep, "LINK_ONCE", SLIM4_ST_INFO, brief, "%s (pad %u) and %s (pad %u) moved together in one "
                             "scan of two only, and one is a chip's status output, which can switch by itself (U10's "
                             "CHG toggles while it looks for a cell). Reboot: a real short shows in both scans",
                             pa->net, pa->pad, pb->net, pb->pad);
                continue;
            }
            ++shorts;
            slim4_st_add(rep, "SHORT", SLIM4_ST_FAIL, brief,
                         "%s (GPIO%u, U1 pad %u) and %s (GPIO%u, pad %u) are joined: one follows the other when driven, "
                         "%s%s", pa->net, pa->gpio, pa->pad, pb->net, pb->gpio, pb->pad,
                         (s1 && s2) ? "in both scans" : "in one scan of two (intermittent)",
                         pads_adjacent(pa->pad, pb->pad) ? "; neighbouring pads: look for a solder bridge on U1"
                                                         : "; not neighbouring pads: look along both nets");
        }
    }
    unsigned drive_faults = 0;
    for (size_t a = 0; a < n; ++a) {
        const slim4_pin_desc_t *p = &SLIM4_ST_PINS[a];
        const bool hi_bad = scan1->readback_high[a] == 0 || scan2->readback_high[a] == 0;
        const bool lo_bad = scan1->readback_low[a] == 1 || scan2->readback_low[a] == 1;
        if (!hi_bad && !lo_bad) continue;
        const bool both = (scan1->readback_high[a] == 0 && scan2->readback_high[a] == 0) ||
                          (scan1->readback_low[a] == 1 && scan2->readback_low[a] == 1);
        if (!both && p->role == SLIM4_ROLE_STATUS) {
            /* A chip's status output switched on while it was driven (CHG toggles while U10 looks for a cell). */
            slim4_st_add(rep, "DRIVE_ONCE", SLIM4_ST_INFO, "STATUS OUTPUT SWITCHED MID-TEST",
                         "%s (pad %u) read the other level once of two scans while driven: its chip (%s) switched it. "
                         "Reboot: a short shows in both scans", p->net, p->pad, p->load);
            continue;
        }
        ++drive_faults;
        slim4_st_add(rep, "DRIVE", SLIM4_ST_FAIL, hi_bad ? "NET CANNOT BE DRIVEN HIGH" : "NET CANNOT BE DRIVEN LOW",
                     "%s (GPIO%u, U1 pad %u): driven %s it still read %s: the net is shorted to %s or heavily loaded",
                     p->net, p->gpio, p->pad, hi_bad ? "high" : "low", hi_bad ? "low" : "high",
                     hi_bad ? "GND" : "3V3");
    }
    unsigned adj = 0, adj_cov = 0, pairs = 0, pairs_cov = 0;
    char missing[120] = "";
    size_t mlen = 0;
    for (size_t a = 0; a < n; ++a) {
        for (size_t b = a + 1; b < n; ++b) {
            const bool cov = slim4_st_pair_covered(scan1, a, b) && slim4_st_pair_covered(scan2, a, b);
            ++pairs;
            if (cov) ++pairs_cov;
            if (!pads_adjacent(SLIM4_ST_PINS[a].pad, SLIM4_ST_PINS[b].pad)) continue;
            ++adj;
            if (cov) {
                ++adj_cov;
            } else if (mlen < sizeof(missing)) {
                const int w = snprintf(missing + mlen, sizeof(missing) - mlen, "%s%u/%u", mlen ? " " : "",
                                       SLIM4_ST_PINS[a].pad, SLIM4_ST_PINS[b].pad);
                if (w > 0) mlen += (size_t)w;
            }
        }
    }
    if (shorts == 0 && drive_faults == 0) {
        /* A pair is untested when neither net may be driven against the other's rest level (a held or open net, or
         * the two charger-mode nets). Those nets carry their own FAIL or INFO line. */
        char untested[140] = "";
        if (adj_cov < adj) snprintf(untested, sizeof(untested), " (untested pad pairs: %.110s)", missing);
        char brief[36];
        snprintf(brief, sizeof(brief), "NO SHORTS - %u OF %u PAD PAIRS", adj_cov, adj);
        /* PASS only when every neighbouring pad pair was tested; otherwise what was tested is clean, but not all. */
        slim4_st_add(rep, "SHORTS", adj_cov == adj ? SLIM4_ST_PASS : SLIM4_ST_INFO, brief,
                     "%u nets driven high and low in turn, two scans: no net followed another; %u of %u net pairs and "
                     "%u of %u neighbouring U1 pad pairs could be tested%s", (unsigned)n, pairs_cov, pairs, adj_cov,
                     adj, untested);
    }
}

/* ---- Chip, memory, reset --------------------------------------------------------------------------------- */

void slim4_st_judge_chip(slim4_st_report_t *rep, unsigned revision)
{
    const unsigned major = revision / 100, minor = revision % 100;
    char brief[36];
    snprintf(brief, sizeof(brief), "ESP32-P4 V%u.%u", major, minor);
    if (major != 3) {
        slim4_st_add(rep, "CHIP", SLIM4_ST_FAIL, brief, "U1 is chip revision v%u.%u: the board and this firmware need "
                     "v3.x (ESP32-P4NRW32X, v3.1 preferred)", major, minor);
    } else {
        slim4_st_add(rep, "CHIP", SLIM4_ST_PASS, brief, "U1 is chip revision v%u.%u%s", major, minor,
                     minor == 0 ? " (accepted; v3.1 preferred)" : "");
    }
}

void slim4_st_judge_psram(slim4_st_report_t *rep, size_t psram_bytes)
{
    const unsigned mib = (unsigned)(psram_bytes / (1024u * 1024u));
    char brief[36];
    snprintf(brief, sizeof(brief), "PSRAM %u MIB", mib);
    if (psram_bytes == SLIM4_ST_PSRAM_BYTES) {
        slim4_st_add(rep, "PSRAM", SLIM4_ST_PASS, brief, "%u MiB in U1's package, as on an ESP32-P4NRW32X; the boot "
                     "memory test of all of it passed (a failure stops the boot)", mib);
    } else {
        slim4_st_add(rep, "PSRAM", SLIM4_ST_FAIL, brief, "%u MiB found, expected 32 MiB: U1 is not an ESP32-P4NRW32X",
                     mib);
    }
}

void slim4_st_judge_flash(slim4_st_report_t *rep, bool id_ok, uint32_t flash_id, bool size_ok, uint32_t flash_bytes)
{
    char brief[36];
    if (!id_ok || flash_id != SLIM4_ST_FLASH_ID) {
        snprintf(brief, sizeof(brief), "FLASH ID %06lX - EXPECTED EF4020", (unsigned long)(flash_id & 0xFFFFFFu));
        slim4_st_add(rep, "FLASH", SLIM4_ST_FAIL, brief, "U2's JEDEC ID %s%06lX, expected EF4020 (Winbond "
                     "W25Q512JV): wrong part fitted", id_ok ? "" : "could not be read; got ",
                     (unsigned long)(flash_id & 0xFFFFFFu));
        return;
    }
    if (!size_ok || flash_bytes != SLIM4_ST_FLASH_BYTES) {
        snprintf(brief, sizeof(brief), "FLASH %lu MIB - EXPECTED 64", (unsigned long)(flash_bytes / (1024u * 1024u)));
        slim4_st_add(rep, "FLASH", SLIM4_ST_FAIL, brief, "U2 reports %lu MiB, expected 64 MiB (W25Q512JV)",
                     (unsigned long)(flash_bytes / (1024u * 1024u)));
        return;
    }
    slim4_st_add(rep, "FLASH", SLIM4_ST_PASS, "FLASH W25Q512JV 64 MIB", "U2 JEDEC ID EF4020 (Winbond W25Q512JV), "
                 "64 MiB");
}

void slim4_st_judge_reset(slim4_st_report_t *rep, bool brownout, const char *reason_name)
{
    char brief[36];
    snprintf(brief, sizeof(brief), "LAST RESET: %.23s", reason_name);
    if (brownout) {
        slim4_st_add(rep, "RESET", SLIM4_ST_FAIL, brief, "the previous run ended in a %s reset: U1's supply fell "
                     "below its detector's level (USB supply or cable, the 3.3 V regulator, or a load on 3V3_SYS)",
                     reason_name);
    } else {
        slim4_st_add(rep, "RESET", SLIM4_ST_INFO, brief, "reset reason: %s", reason_name);
    }
}

/* ---- Display --------------------------------------------------------------------------------------------- */

bool slim4_st_panel_usable(const slim4_panel_probe_t *probe)
{
    return probe->attempted && probe->answered;
}

static size_t list_bits(char *buf, size_t len, size_t at, uint32_t bits, const char *const *names, unsigned first,
                        unsigned count)
{
    for (unsigned i = 0; i < count; ++i) {
        if (!(bits & (1u << (first + i))) || !names[i]) continue;
        if (at >= len) break;
        const int w = snprintf(buf + at, len - at, "%s%s", at ? ", " : "", names[i]);
        if (w > 0) at += (size_t)w;
    }
    return at < len ? at : len - 1;
}

#define PANEL_REPORT_BITS 0x0000FFFFu   /* int_st0 0..15: the panel's acknowledge-and-error report */
#define DPHY_ERROR_BITS   0x001F0000u   /* int_st0 16..20: D-PHY errors on lane 0 */
#define HOST_RX_BITS      0x0000007Fu   /* int_st1 0..6: timeouts and errors in what the host received */
#define HOST_FIFO_BITS    0x00001F80u   /* int_st1 7..12: host FIFO misuse (firmware) */

void slim4_st_judge_panel(slim4_st_report_t *rep, const slim4_panel_probe_t *probe)
{
    static const char *const panel_bits[16] = {
        "SoT error", "SoT sync error", "EoT sync error", "escape entry error", "LP transmit sync error",
        "peripheral timeout", "false control", "contention", "ECC single-bit (corrected)", "ECC multi-bit",
        "checksum error", "data type not recognised", "VC ID invalid", "invalid length", NULL, "protocol violation",
    };
    static const char *const dphy_bits[5] = {"ErrEsc", "ErrSyncEsc", "ErrControl", "ErrContentionLP0",
                                             "ErrContentionLP1"};
    static const char *const rx_bits[7] = {"HS TX timeout", "LP RX timeout", "ECC single-bit", "ECC multi-bit",
                                           "CRC error", "packet size error", "EoTp error"};
    static const char *const fifo_bits[6] = {"DPI payload write", "command FIFO write", "payload FIFO write",
                                             "payload send", "payload read", "payload receive"};
    const uint32_t st0 = probe->int_st0, st1 = probe->int_st1;
    char flags[160];
    size_t at = 0;
    flags[0] = '\0';
    at = list_bits(flags, sizeof(flags), at, st0, panel_bits, 0, 16);
    at = list_bits(flags, sizeof(flags), at, st0, dphy_bits, 16, 5);
    at = list_bits(flags, sizeof(flags), at, st1, rx_bits, 0, 7);
    at = list_bits(flags, sizeof(flags), at, st1, fifo_bits, 7, 6);
    if (!probe->attempted) {
        slim4_st_add(rep, "PANEL", SLIM4_ST_FAIL, "NOT PROBED - DSI SETUP FAILED", "the display bring-up stopped before "
                     "the panel probe, at: %s", probe->stopped_at ? probe->stopped_at : "unknown step");
        return;
    }
    if (!probe->answered) {
        slim4_st_add(rep, "PANEL", SLIM4_ST_FAIL, "NO ANSWER ON DSI LANE 0", "the panel did not answer at: %s%s%s. "
                     "Look at J1 and the panel FPC (seated, latched), the D0 pair (U1 pads 39/40 to J1), the panel "
                     "supplies, and LCD_RESX (Q1, R308). The display bring-up stopped here so the boot does not hang",
                     probe->stopped_at ? probe->stopped_at : "unknown step", flags[0] ? "; host flags: " : "", flags);
        return;
    }
    if (probe->stopped_at) {
        slim4_st_add(rep, "DISPLAY", SLIM4_ST_FAIL, "BRING-UP FAILED AFTER THE PROBE", "the panel answered the probe, "
                     "then the display bring-up failed at: %s (see the slim4_bsp log line)", probe->stopped_at);
    }
    char brief[36];
    snprintf(brief, sizeof(brief), "ID %02X %02X %02X", probe->id[0], probe->id[1], probe->id[2]);
    /* ILI9881C: 98 81 then a version byte (the datasheet gives 1C; Espressif's own log shows 5C), so only the
     * first two are judged and the third is reported. */
    if (probe->id[0] == SLIM4_ST_PANEL_ID0 && probe->id[1] == SLIM4_ST_PANEL_ID1) {
        snprintf(brief, sizeof(brief), "ILI9881C ANSWERS - ID 98 81 %02X", probe->id[2]);
        slim4_st_add(rep, "PANEL", SLIM4_ST_PASS, brief, "the panel controller answered over DSI lane 0 (low-power "
                     "read: D0_P and D0_N both work) with ID 98 81 %02X, an ILI9881C (version byte %02X)",
                     probe->id[2], probe->id[2]);
    } else {
        slim4_st_add(rep, "PANEL", SLIM4_ST_FAIL, brief, "the panel answered with ID %02X %02X %02X, expected 98 81 xx "
                     "(ILI9881C): a different panel or controller, or garbled low-power data on lane 0",
                     probe->id[0], probe->id[1], probe->id[2]);
    }

    char first[64] = "none";
    if ((probe->int_st0_first | probe->int_st1_first) != 0) {
        snprintf(first, sizeof(first), "int_st0=%08lX int_st1=%08lX", (unsigned long)probe->int_st0_first,
                 (unsigned long)probe->int_st1_first);
    }
    const bool link_errors = (st0 & (PANEL_REPORT_BITS | DPHY_ERROR_BITS)) || (st1 & HOST_RX_BITS);
    if (link_errors || !probe->repeat_ok) {
        slim4_st_add(rep, "DSI_LANE0", SLIM4_ST_FAIL, "ERRORS ON DSI LANE 0", "second exchange: %s%s%s (host "
                     "int_st0=%08lX int_st1=%08lX; first exchange %s). In low-power mode these point at the D0 pair, "
                     "J1 or the FPC", flags, (flags[0] && !probe->repeat_ok) ? "; " : "",
                     probe->repeat_ok ? "" : "register 0x00 read back differently", (unsigned long)st0,
                     (unsigned long)st1, first);
    } else if (st1 & HOST_FIFO_BITS) {
        slim4_st_add(rep, "DSI_LANE0", SLIM4_ST_FAIL, "DSI HOST FIFO ERROR", "the DSI host flagged a FIFO error "
                     "(int_st1=%08lX: %s): a firmware fault, not the board", (unsigned long)st1, flags);
    } else {
        slim4_st_add(rep, "DSI_LANE0", SLIM4_ST_PASS, "LANE 0 CLEAN - NO ERROR FLAGS", "the second exchange (ID read "
                     "again, a write with acknowledge) raised no error flag from the panel or the D-PHY (first "
                     "exchange after reset: %s)", first);
    }
}

void slim4_st_judge_vsync(slim4_st_report_t *rep, bool display_ready, uint32_t vsync_hz)
{
    if (!display_ready) return;   /* the PANEL line says why */
    char brief[36];
    snprintf(brief, sizeof(brief), "%u HZ - LOOK AT BARS AND LINES", (unsigned)(vsync_hz % 1000u));
    if (vsync_hz == 0) {
        slim4_st_add(rep, "VIDEO", SLIM4_ST_FAIL, "NO FRAMES - VIDEO NOT RUNNING", "the DSI host reported no frame in "
                     "half a second after the panel was started");
        return;
    }
    slim4_st_add(rep, "VIDEO", SLIM4_ST_INFO, brief, "the DSI host sends %lu frames a second. CLK and D1 carry video "
                 "only, so look at the screen: the colour bars and 1-pixel lines must be clean, with no sparkles, "
                 "shifted rows or wrong colours", (unsigned long)vsync_hz);
}

/* ---- Power ----------------------------------------------------------------------------------------------- */

void slim4_st_judge_power(slim4_st_report_t *rep, const slim4_st_power_t *p)
{
    if (!p->ready) {
        slim4_st_add(rep, "POWER", SLIM4_ST_FAIL, "POWER SERVICE DID NOT START", "the battery ADC, charger pins or "
                     "die temperature sensor could not be set up (see the slim4_power log lines)");
        return;
    }
    if (p->usb_host_seen && p->pgood_low) {
        slim4_st_add(rep, "USB_INPUT", SLIM4_ST_PASS, "USB HOST AND CHARGER PGOOD", "a USB host is attached and U10 "
                     "BQ24074 reports a valid input (PGOOD low)");
    } else if (p->usb_host_seen) {
        slim4_st_add(rep, "USB_INPUT", SLIM4_ST_FAIL, "USB HOST BUT NO PGOOD", "a USB host is attached but U10 BQ24074 "
                     "does not report a valid input (PGOOD high): look at J2's VBUS pins, the USB_VBUS net to U10 pin 13 "
                     "(D1, C403, C409 shorted?), R421 and U10 itself");
    } else {
        slim4_st_add(rep, "USB_INPUT", SLIM4_ST_INFO, p->pgood_low ? "NO USB HOST - PGOOD LOW" : "NO USB HOST - PGOOD HIGH",
                     "no USB host attached (no start-of-frame packets); U10 PGOOD is %s", p->pgood_low ? "low (input "
                     "valid)" : "high (no valid input)");
    }
    static const char *const cc_names[] = {"NONE", "DEFAULT 500MA", "1.5A", "3A"};
    char brief[36];
    snprintf(brief, sizeof(brief), "USB-C ADVERTISED %s", cc_names[p->usb_current < 4 ? p->usb_current : 0]);
    slim4_st_add(rep, "USB_CC", SLIM4_ST_INFO, brief, "U13 TUSB320 OUT1/OUT2 decode to %s",
                 cc_names[p->usb_current < 4 ? p->usb_current : 0]);
    if (p->battery_fault) {
        slim4_st_add(rep, "BATTERY", SLIM4_ST_FAIL, "BATTERY REVERSED OR SHORTED", "USB is valid but the battery rail "
                     "stays below 1.5 V: unplug the cell; check its polarity at J3 and the battery path");
    } else {
        snprintf(brief, sizeof(brief), "BATTERY RAIL %u MV%s", p->battery_mv, p->battery_approx ? " APPROX" : "");
        slim4_st_add(rep, "BATTERY", SLIM4_ST_INFO, brief, "battery rail %u mV%s; %s. With no cell fitted the charger's "
                     "battery detection makes this reading wander", p->battery_mv,
                     p->battery_approx ? " (ADC uncalibrated: approximate)" : "",
                     p->charging ? "charging" : "not charging");
    }
    snprintf(brief, sizeof(brief), "DIE %d C", p->die_c);
    slim4_st_add(rep, "DIE_TEMP", SLIM4_ST_INFO, brief, "ESP32-P4 die temperature %d C shortly after boot", p->die_c);
}
