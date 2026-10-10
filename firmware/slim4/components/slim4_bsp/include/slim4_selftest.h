#pragma once
/* SLIM4 hardware self-test (firmware R11, R12): checks a newly assembled board for manufacturing faults at every boot.
 *
 * The decisions (what a set of readings means) live in slim4_selftest_logic.c, which has no ESP-IDF dependency and
 * is covered by the host tests in tests/host. The measurements live in slim4_selftest.c (GPIO, chip identity, power)
 * and slim4_board.c (the panel probe over DSI). Every check adds one line to a report: PASS, FAIL or INFO. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum {
    SLIM4_ST_PASS = 0,
    SLIM4_ST_FAIL,
    SLIM4_ST_INFO,
} slim4_st_verdict_t;

#define SLIM4_ST_MAX_ITEMS 48

typedef struct {
    char id[16];                 /* short name of the check, e.g. BTN_LEFT */
    slim4_st_verdict_t verdict;
    char brief[36];              /* screen text, at most 35 characters: upper case, digits, space . / - : only */
    char detail[360];            /* serial text: what was measured and what to look at */
} slim4_st_item_t;

typedef struct {
    slim4_st_item_t items[SLIM4_ST_MAX_ITEMS];
    uint8_t count;
    uint8_t pass, fail, info;
    bool overflow;               /* more checks than items: the summary counts them, the list stops */
} slim4_st_report_t;

void slim4_st_report_init(slim4_st_report_t *rep);
void slim4_st_add(slim4_st_report_t *rep, const char *id, slim4_st_verdict_t verdict, const char *brief,
                  const char *detail_fmt, ...) __attribute__((format(printf, 5, 6)));
const char *slim4_st_verdict_name(slim4_st_verdict_t verdict);

/* ---- GPIO nets ------------------------------------------------------------------------------------------- */

typedef enum {
    SLIM4_PULL_UP_10K,
    SLIM4_PULL_UP_100K,
    SLIM4_PULL_DOWN_10K,
    SLIM4_PULL_DOWN_100K,
    SLIM4_PULL_NONE,
} slim4_pull_t;

typedef enum {
    SLIM4_ROLE_SWITCH,   /* switch to GND: low = pressed */
    SLIM4_ROLE_STATUS,   /* open-drain output of another chip: may be asserted (low) */
    SLIM4_ROLE_PASSIVE,  /* the resistor and inputs of other chips only */
    SLIM4_ROLE_SIGNAL,   /* no pull on the board (I2S): short test only */
    SLIM4_ROLE_ANALOG,   /* BAT_ADC: driven in the short test, never read as a logic level */
    SLIM4_ROLE_UNUSED,   /* U1 pad with no net, beside a tested net: short test only */
} slim4_pin_role_t;

typedef struct {
    uint8_t gpio;
    uint8_t pad;            /* U1 package pad (QFN-104) */
    const char *net;
    slim4_pull_t pull;
    slim4_pin_role_t role;
    const char *pull_part;  /* the board's pull resistor, e.g. "R111 10k" (NULL: none) */
    const char *load;       /* what else is on the net, e.g. "SW1" or "U10 BQ24074 PGOOD" */
    bool drive_ok;          /* the self-test may drive it high and low for microseconds */
    bool capacitor;         /* 100 nF on the net (PWR_WAKE C601, BAT_ADC C603): driven for 1 ms, not 50 us */
    bool rc_timed;          /* PWR_WAKE: the 10 k / 100 nF rise time is measured */
} slim4_pin_desc_t;

extern const slim4_pin_desc_t SLIM4_ST_PINS[];
extern const size_t SLIM4_ST_PIN_COUNT;
#define SLIM4_ST_MAX_PINS 32

/* Level of a pull-up net is 1 at rest, of a pull-down net 0; -1 for nets without a pull. */
int slim4_st_rest_level(const slim4_pin_desc_t *pin);
/* Pins whose board pull resistor is checked (switches, status lines, passive nets). */
bool slim4_st_has_pull_check(const slim4_pin_desc_t *pin);
/* Whether U1's pull may be turned against the board's pull (10 k nets, never toward a charger EN pin's active level). */
bool slim4_st_opposite_allowed(const slim4_pin_desc_t *pin);

/* Readings of one pull check; -1 where a step did not run. */
typedef struct {
    int8_t same;       /* internal pull on, the same way as the board's pull */
    int8_t opposite;   /* internal pull on, against the board's 10 k pull (10 k nets only) */
    int8_t released;   /* driven to the opposite level, then released with no internal pull */
    int32_t rise_us;   /* PWR_WAKE: release from low to reading high, -1 not run, INT32_MAX never */
} slim4_pull_reading_t;

typedef enum {
    SLIM4_PULL_OK,
    SLIM4_PULL_HELD,          /* held at the other level: switch pressed, status asserted, or a short to a rail */
    SLIM4_PULL_FLOATING,      /* no pull reaches U1's pad: pad not soldered, resistor missing or open */
    SLIM4_PULL_WEAK,          /* the pull is there but loses to U1's 45 k internal pull: wrong (higher) value */
    SLIM4_PULL_RC_FAST,       /* PWR_WAKE rises too fast: the 100 nF capacitor is missing */
    SLIM4_PULL_RC_SLOW,       /* PWR_WAKE rises too slowly: extra capacitance or leakage on the net */
} slim4_pull_result_t;

/* PWR_WAKE rise-time window (us) for 10 k and 100 nF (X5R/X7R tolerance and DC bias, input threshold 35-65 %). */
#define SLIM4_ST_RC_MIN_US 200
#define SLIM4_ST_RC_MAX_US 3000

slim4_pull_result_t slim4_st_classify_pull(const slim4_pin_desc_t *pin, const slim4_pull_reading_t *r);
slim4_st_verdict_t slim4_st_report_pull(slim4_st_report_t *rep, const slim4_pin_desc_t *pin,
                                        const slim4_pull_reading_t *r);

/* Short scan between all nets in SLIM4_ST_PINS: each pin that may be driven is driven high and then low for
 * microseconds while every other pin is read. A pin that follows the driven pin is joined to it. */
typedef struct {
    int8_t baseline[SLIM4_ST_MAX_PINS];                        /* level at rest; -1 = not read */
    int8_t when_high[SLIM4_ST_MAX_PINS][SLIM4_ST_MAX_PINS];    /* [driven][read]; -1 = not run */
    int8_t when_low[SLIM4_ST_MAX_PINS][SLIM4_ST_MAX_PINS];
    int8_t readback_high[SLIM4_ST_MAX_PINS];                   /* the driven pin's own level; -1 = not run */
    int8_t readback_low[SLIM4_ST_MAX_PINS];
} slim4_short_scan_t;

/* Whether pin i is read as a victim and how it may be driven, given its pull-check result (SLIM4_PULL_OK for pins
 * without a pull check) and its level at rest. */
bool slim4_st_is_victim(const slim4_pin_desc_t *pin, slim4_pull_result_t pull);
void slim4_st_drive_plan(const slim4_pin_desc_t *pin, slim4_pull_result_t pull, int8_t baseline,
                         bool *drive_high, bool *drive_low);
void slim4_st_scan_init(slim4_short_scan_t *scan);
/* links[a][b] = pin b followed pin a. Returns the number of links. */
size_t slim4_st_find_links(size_t n, const slim4_short_scan_t *scan, bool links[SLIM4_ST_MAX_PINS][SLIM4_ST_MAX_PINS]);
/* Whether the scan could have seen a short between pins a and b (either one driven, the other read). */
bool slim4_st_pair_covered(const slim4_short_scan_t *scan, size_t a, size_t b);
/* Adds SHORTS (and DRIVE lines for pins that could not be driven to a level) from two scans: a link seen in both
 * scans is a short (FAIL), in one only intermittent (FAIL, marked so). */
void slim4_st_report_shorts(slim4_st_report_t *rep, size_t n, const slim4_short_scan_t *scan1,
                            const slim4_short_scan_t *scan2);

/* ---- Chip, memory, reset --------------------------------------------------------------------------------- */

#define SLIM4_ST_PSRAM_BYTES   (32u * 1024u * 1024u)   /* ESP32-P4NRW32X: 32 MiB in the package */
#define SLIM4_ST_FLASH_ID      0xEF4020u               /* U2 W25Q512JVEIQ: Winbond, SPI, 512 Mbit */
#define SLIM4_ST_FLASH_BYTES   (64u * 1024u * 1024u)

void slim4_st_judge_chip(slim4_st_report_t *rep, unsigned revision /* major * 100 + minor */);
void slim4_st_judge_psram(slim4_st_report_t *rep, size_t psram_bytes);
void slim4_st_judge_flash(slim4_st_report_t *rep, bool id_ok, uint32_t flash_id, bool size_ok, uint32_t flash_bytes);
void slim4_st_judge_reset(slim4_st_report_t *rep, bool brownout, const char *reason_name);

/* ---- Display --------------------------------------------------------------------------------------------- */

typedef struct {
    bool attempted;          /* the DSI bus and panel reset came up, so the probe ran */
    bool answered;           /* every write was acknowledged and every read answered on lane 0 */
    const char *stopped_at;  /* the probe step, or the display bring-up stage, that did not complete; NULL if none */
    uint8_t id[3];           /* ILI9881C page 1 registers 0x00..0x02 */
    bool repeat_ok;          /* the second read of register 0x00 gave the same value */
    uint32_t int_st0_before, int_st1_before;  /* DSI host error flags before the probe (display bring-up) */
    uint32_t int_st0_first, int_st1_first;    /* after the first exchange (can include power-up leftovers) */
    uint32_t int_st0, int_st1;                /* after the second exchange: the ones judged */
} slim4_panel_probe_t;

#define SLIM4_ST_PANEL_ID0 0x98
#define SLIM4_ST_PANEL_ID1 0x81

/* Whether the display bring-up may continue (the panel answered): otherwise the ILI9881C driver's own reads, which
 * wait without a time limit, would hang the boot. */
bool slim4_st_panel_usable(const slim4_panel_probe_t *probe);
void slim4_st_judge_panel(slim4_st_report_t *rep, const slim4_panel_probe_t *probe);
void slim4_st_judge_vsync(slim4_st_report_t *rep, bool display_ready, uint32_t vsync_hz);

/* ---- Power ----------------------------------------------------------------------------------------------- */

typedef struct {
    bool ready;              /* the power service started */
    bool usb_host_seen;      /* USB start-of-frame packets arrive: a USB host is attached */
    bool pgood_low;          /* BQ24074 reports a valid input */
    bool charging;
    uint8_t usb_current;     /* slim4_usb_current_t */
    uint16_t battery_mv;
    bool battery_fault;
    bool battery_approx;
    int16_t die_c;
} slim4_st_power_t;

void slim4_st_judge_power(slim4_st_report_t *rep, const slim4_st_power_t *p);

/* ---- Radio (PCB R28+) ------------------------------------------------------------------------------------ */

#include "slim4_radio.h"
/* One RADIO line from slim4_radio_probe(): PASS (every joint the probe can see works), FAIL (which line or part to
 * look at), or INFO "NOT FITTED" (nothing answers: a board without U15 or R701). Never blocks the boot. */
void slim4_st_judge_radio(slim4_st_report_t *rep, const slim4_radio_probe_t *p);

/* ---- ESP-IDF side (slim4_selftest.c) -------------------------------------------------------------------- */

/* Pull checks and short scan of the GPIO nets. Run before slim4_platform_init(): it reconfigures the pins and
 * leaves them as after reset (inputs, board pulls only). */
void slim4_selftest_pins(slim4_st_report_t *rep);
/* Chip, memory, reset, panel probe, power and frame rate. Run after slim4_platform_init(). */
void slim4_selftest_after_init(slim4_st_report_t *rep, bool display_ready);
/* Prints every line as "SELFTEST <verdict> <id>: <detail>" and a summary line. */
void slim4_selftest_log(const slim4_st_report_t *rep);
/* Prints the lines from index `first` on, without the summary (to log part of the report as soon as it exists). */
void slim4_selftest_log_lines(const slim4_st_report_t *rep, uint8_t first);
/* The last report, for the diagnostic screen (NULL before the self-test ran). */
const slim4_st_report_t *slim4_selftest_last(void);
