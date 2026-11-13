/* Host test of the power policy in components/slim4_bsp/slim4_power.c (the file itself, compiled against sdk/).
 * Build and run: sh tests/host/run.sh. Each case drives the GPIO levels, battery voltage, die temperature and clock
 * of a simulated board and checks what the policy decides. Not a substitute for measurements on a board. */
#include <stdarg.h>
#include <string.h>
#include "sdk/host_sdk.h"

int host_gpio[64];
int host_battery_mv;
bool host_adc_fails;
bool host_cali_fails;
float host_die_c = 25;
int64_t host_now_us = 1000000;
bool host_quiet = true;
void host_log(char level, const char *fmt, ...)
{
    if (host_quiet) return;
    va_list ap; va_start(ap, fmt); printf("    %c ", level); vprintf(fmt, ap); printf("\n"); va_end(ap);
}

static int s_cap_calls;
static uint8_t s_last_cap;
void slim4_board_prepare_power_off(void) {}
void slim4_board_backlight_cap_changed(uint8_t cap) { ++s_cap_calls; s_last_cap = cap; }
static bool s_board_muted;
void slim4_board_audio_power_mute(bool mute) { s_board_muted = mute; }

#include "../../components/slim4_bsp/slim4_power.c"

enum usb { NO_USB, USB500, USB1A5, USB3A };
static void board(enum usb usb, bool chg, int mv, float die)
{
    host_gpio[SLIM4_GPIO_PGOOD_STATUS] = usb == NO_USB;          /* low = valid input */
    host_gpio[SLIM4_GPIO_CHG_STATUS] = !chg;                     /* low = charging */
    host_gpio[SLIM4_GPIO_USB_CURR_OUT1] = !(usb == USB1A5 || usb == USB3A);
    host_gpio[SLIM4_GPIO_USB_CURR_OUT2] = !(usb == USB500 || usb == USB3A);
    if (usb == NO_USB) host_gpio[SLIM4_GPIO_USB_CURR_OUT1] = host_gpio[SLIM4_GPIO_USB_CURR_OUT2] = 1;
    host_battery_mv = mv;
    host_die_c = die;
}
static void fresh(enum usb usb, bool chg, int mv, float die)
{
    memset(&s_state, 0, sizeof s_state);
    s_fault_count = s_low_count = s_cell_ok_count = 0;
    s_cell_ok = s_adc_warned = s_approx_warned = s_adc_valid = s_ready = false;
    s_board_muted = false;
    s_adc = NULL; s_adc_cali = NULL; s_tsens = NULL;
    s_button_down_since = 0;
    s_last_policy_us = 0; s_charge_us = 0; s_timer_restarted = false;
    host_adc_fails = false;
    host_cali_fails = false;
    host_now_us = 1000000;
    for (int i = 0; i < 64; ++i) host_gpio[i] = 1;
    board(usb, chg, mv, die);
    slim4_power_init();                       /* first policy pass */
}
static void fresh_uncal(enum usb usb, bool chg, int mv, float die)
{
    host_cali_fails = true;                   /* stays set: fresh() clears it only before its init */
    memset(&s_state, 0, sizeof s_state);
    s_fault_count = s_low_count = s_cell_ok_count = 0;
    s_cell_ok = s_adc_warned = s_approx_warned = s_adc_valid = s_ready = false;
    s_board_muted = false;
    s_adc = NULL; s_adc_cali = NULL; s_tsens = NULL;
    s_button_down_since = 0;
    s_last_policy_us = 0; s_charge_us = 0; s_timer_restarted = false;
    host_adc_fails = false;
    host_now_us = 1000000;
    for (int i = 0; i < 64; ++i) host_gpio[i] = 1;
    board(usb, chg, mv, die);
    slim4_power_init();
}
/* fresh() makes the first reading; run(n) makes n more, 0.5 s apart.
 * advance n policy periods, polling every 10 ms like app_main; returns true if any poll asked to switch off */
static bool run(int periods)
{
    bool off = false;
    for (int i = 0; i < periods * 50; ++i) { host_now_us += 10000; off |= slim4_power_poll(); }
    return off;
}

static int s_fail, s_pass;
static void check(const char *name, bool ok)
{
    printf("%s  %s\n", ok ? "PASS" : "FAIL", name);
    if (ok) ++s_pass; else ++s_fail;
}

int main(void)
{
    /* 500 mA USB: the cap and what lifts it */
    fresh(USB500, false, 4200, 25); run(10);
    check("USB 500 mA, not charging: backlight 15 %, input 500 mA", s_state.backlight_cap_percent == 15 && s_state.input_limit_ma == 500);
    fresh(USB500, true, 3800, 25);
    check("USB 500 mA, charging 3.8 V, first pass: cap held until the cell qualifies", s_state.backlight_cap_percent == 15);
    run(4);
    check("USB 500 mA, charging 3.8 V, after 2 s: cap lifted", s_state.backlight_cap_percent == 100);
    board(USB500, true, 3450, 25); run(4);
    check("qualified cell sags to 3.45 V (hysteresis): cap stays lifted", s_state.backlight_cap_percent == 100);
    board(USB500, true, 3350, 25); run(1);
    check("qualified cell below 3.4 V: cap back to 15 %", s_state.backlight_cap_percent == 15);
    board(USB500, true, 3800, 25); run(4); board(USB500, false, 4150, 25); run(1);
    check("charge cycle ends (CHG high): cap back to 15 %", s_state.backlight_cap_percent == 15);
    fresh(USB500, true, 2800, 25); run(10);
    check("USB 500 mA, CHG low, cell 2.8 V (pre-charge): cap stays 15 %", s_state.backlight_cap_percent == 15);
    fresh(USB500, true, 800, 25); run(2);
    check("USB 500 mA, CHG low, rail 0.8 V for 3 readings (1.5 s): battery fault, cap 15 %", s_state.battery_fault && s_state.backlight_cap_percent == 15);
    fresh(USB500, false, 800, 25); run(1);
    check("rail 0.8 V for 2 readings: no fault yet", !s_state.battery_fault);
    fresh(USB1A5, false, 4200, 25); run(2);
    check("USB-C 1.5 A: input 1.07 A, no cap", s_state.input_limit_ma == 1070 && s_state.backlight_cap_percent == 100);
    fresh(USB3A, false, 4200, 25); run(2);
    check("USB-C 3 A: input 1.07 A, no cap", s_state.input_limit_ma == 1070 && s_state.backlight_cap_percent == 100);
    fresh(NO_USB, false, 3900, 25); run(2);
    check("battery only: no cap", s_state.backlight_cap_percent == 100);

    /* low-battery switch-off */
    fresh(NO_USB, false, 3200, 25);
    check("battery 3.2 V, button released, first pass: not yet off", !run(1));
    check("battery 3.2 V for 2 s, button released: switches off", run(3));
    fresh(NO_USB, false, 3200, 25); bool off = run(2); board(NO_USB, false, 3700, 25); off |= run(10);
    check("battery dips to 3.2 V for 1 s, recovers to 3.7 V: stays on", !off);
    fresh(NO_USB, false, 3200, 25); host_gpio[SLIM4_GPIO_PWR_WAKE] = 0;
    check("battery 3.2 V with the button held: switches off after 2 s", run(5));
    fresh(USB500, false, 3200, 25);
    check("3.2 V reading on USB (charger output): no switch-off", !run(10));

    /* failed battery readings */
    fresh(NO_USB, false, 3000, 25); host_adc_fails = true;
    check("ADC fails on battery: no switch-off from a missing reading", !run(10));
    fresh(USB500, true, 3900, 80); host_adc_fails = true; run(10);
    check("ADC fails on USB 500 mA, CHG low, die 80 C: cap 15 %, no suspend",
          s_state.backlight_cap_percent == 15 && !s_state.charge_suspended && s_state.input_limit_ma == 500);

    /* uncalibrated ADC (R9): shown, never used for a decision */
    fresh_uncal(NO_USB, false, 3000, 25);
    check("uncalibrated ADC on battery: reading shown as approximate", s_state.battery_approx && s_state.battery_mv > 0);
    check("uncalibrated ADC, battery 3.0 V for 5 s: no switch-off from it", !run(10));
    fresh_uncal(USB500, true, 3900, 25); run(10);
    check("uncalibrated ADC, USB 500 mA, charging 3.9 V: cell never qualifies, cap 15 %, audio muted",
          s_state.backlight_cap_percent == 15 && s_state.audio_muted && s_board_muted);
    fresh_uncal(USB500, true, 3900, 80); run(10);
    check("uncalibrated ADC, die 80 C: no charge suspend", !s_state.charge_suspended && s_state.input_limit_ma == 500);
    fresh_uncal(USB500, true, 800, 25); run(4);
    check("uncalibrated ADC, rail 0.8 V: no battery-fault decision from it", !s_state.battery_fault);
    fresh(NO_USB, false, 3900, 25);
    check("calibrated ADC: reading not marked approximate", !s_state.battery_approx);

    /* audio mute on a source with no budget for it (R9) */
    fresh(USB500, false, 4200, 25); run(2);
    check("USB 500 mA, no qualified cell: amplifiers muted", s_state.audio_muted && s_board_muted);
    fresh(USB500, true, 3800, 25); run(4);
    check("USB 500 mA, cell qualifies: audio enabled", !s_state.audio_muted && !s_board_muted);
    board(USB500, true, 3350, 25); run(1);
    check("qualified cell drops below 3.4 V: audio muted again", s_state.audio_muted && s_board_muted);
    fresh(USB500, true, 3900, 80); run(4);
    check("charge suspended for heat: audio muted with the backlight cap", s_state.charge_suspended && s_state.audio_muted);
    fresh(USB1A5, false, 4200, 25); run(2);
    check("USB-C 1.5 A: audio enabled", !s_state.audio_muted && !s_board_muted);
    fresh(NO_USB, false, 3900, 25); run(2);
    check("battery only: audio enabled", !s_state.audio_muted && !s_board_muted);
    fresh(USB500, false, 4200, 25); host_adc_fails = true; run(4);
    check("battery reading fails on USB 500 mA: audio muted", s_state.audio_muted);

    /* over-temperature charge suspend (USB suspend: system on the cell) */
    fresh(USB500, true, 3400, 80); run(10);
    check("die 80 C, charging 3.4 V: no suspend (below 3.6 V)", !s_state.charge_suspended && s_state.input_limit_ma == 500);
    fresh(USB500, false, 4200, 80); run(10);
    check("die 80 C, not charging (no cell known): no suspend", !s_state.charge_suspended);
    fresh(USB500, true, 3900, 80); run(4);
    check("die 80 C, charging 3.9 V: suspended once the cell qualifies, cap 15 %",
          s_state.charge_suspended && s_state.input_limit_ma == 0 && s_state.backlight_cap_percent == 15);
    board(USB500, false, 3550, 80); run(1);
    check("suspended, cell under load 3.55 V: resumed", !s_state.charge_suspended && s_state.input_limit_ma == 500);
    fresh(USB500, true, 3900, 80); run(4); board(USB500, false, 3850, 60); run(1);
    check("suspended, die cools to 60 C: resumed", !s_state.charge_suspended);
    fresh(USB500, true, 3900, 80); run(4); board(NO_USB, false, 3850, 80); run(1);
    check("suspended, USB unplugged: suspend ended", !s_state.charge_suspended);
    fresh(USB500, true, 3900, 80); run(4); host_adc_fails = true; board(USB500, false, 3850, 80); run(1);
    check("suspended, battery reading fails: resumed", !s_state.charge_suspended);

    /* charge time across heat suspends: leaving a USB suspend restarts the BQ24074's safety timer */
    fresh(USB500, true, 3900, 25); run(7 * 7200);
    check("charging 7 h with no suspend: no firmware stop (the charger's own timer governs)",
          !s_state.charge_suspended && s_state.input_limit_ma == 500);
    fresh(USB500, true, 3900, 25); run(3 * 7200);
    board(USB500, true, 3900, 80); run(4); board(USB500, true, 3900, 60); run(1);
    check("3 h charging, heat suspend, cooled: resumed", !s_state.charge_suspended && !s_state.charge_time_limit);
    run(2 * 7200 + 7080);
    check("5 h 59 min of charge time across the suspend: still charging", !s_state.charge_suspended);
    run(200);
    check("6 h of charge time across the suspend: charging stopped (USB suspend), marked as the time limit",
          s_state.charge_suspended && s_state.charge_time_limit && s_state.input_limit_ma == 0);
    board(USB500, true, 3900, 25); run(7200);
    check("time limit: a cool die does not resume charging", s_state.charge_suspended);
    board(USB500, true, 3550, 25); run(1);
    check("time limit, cell down to 3.55 V: charging resumed (a new charge)",
          !s_state.charge_suspended && !s_state.charge_time_limit && s_charge_us < 1000000);
    board(USB500, true, 3900, 25); run(7 * 7200);
    check("after the new charge starts, 7 h with no suspend: no firmware stop", !s_state.charge_suspended);
    fresh(USB500, true, 3900, 25); run(3 * 7200);
    board(USB500, true, 3900, 80); run(4); board(USB500, true, 3900, 60); run(1);
    board(NO_USB, false, 3900, 25); run(2); board(USB500, true, 3900, 25); run(4 * 7200);
    check("USB unplugged after a heat suspend: count starts again (4 h on the new session, no stop)",
          !s_state.charge_suspended && !s_timer_restarted);
    fresh(USB500, true, 3900, 25); run(3 * 7200);
    board(USB500, true, 3900, 80); run(4); board(USB500, false, 3900, 60); run(1);
    board(USB500, false, 3900, 25); run(4 * 7200);
    check("not charging (CHG high) after the suspend: no charge time counted, no stop",
          !s_state.charge_suspended && s_charge_us < 4LL * 3600 * 1000000);

    /* power button */
    fresh(NO_USB, false, 3900, 25); host_gpio[SLIM4_GPIO_PWR_WAKE] = 0;
    check("button held 1.0 s: stays on", !run(2));
    check("button held 2.1 s: switches off", run(3));
    fresh(NO_USB, false, 3900, 25); host_gpio[SLIM4_GPIO_PWR_WAKE] = 0; s_button_armed = false;
    check("button still held from the wake press: ignored until released", !run(6));

    printf("\n%d passed, %d failed\n", s_pass, s_fail);
    return s_fail ? 1 : 0;
}
