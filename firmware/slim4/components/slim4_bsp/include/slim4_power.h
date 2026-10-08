#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "slim4_types.h"

typedef enum {
    SLIM4_USB_NONE = 0,      /* nothing attached (or not reported) */
    SLIM4_USB_DEFAULT,       /* USB default current, 500 mA */
    SLIM4_USB_1A5,           /* USB-C 1.5 A */
    SLIM4_USB_3A0,           /* USB-C 3.0 A */
} slim4_usb_current_t;

typedef struct {
    uint16_t battery_mv;      /* 0 if the ADC is unavailable */
    uint8_t battery_percent;  /* rough open-circuit estimate, 0-100 */
    bool battery_low;         /* below the shutdown threshold */
    bool usb_power;           /* charger reports a valid input (PGOOD) */
    bool charging;            /* charger reports a charge cycle (CHG) */
    slim4_usb_current_t usb_current;
    uint16_t input_limit_ma;  /* charger input limit the firmware selected */
    int16_t chip_temp_c;      /* ESP32-P4 die temperature */
    bool charge_suspended;    /* firmware suspended charging (die too hot) */
} slim4_power_state_t;

/* Configures the power button, battery ADC, charger and USB-C status pins. */
slim4_status_t slim4_power_init(void);
/* Call about every 10 ms: samples the power button and updates the charger policy.
 * Returns true once the power button has been held for the power-off time. */
bool slim4_power_poll(void);
slim4_status_t slim4_power_read(slim4_power_state_t *out);
/* Turns the display, backlight and amplifiers off and enters deep sleep.
 * The power button (GPIO0, active low) wakes the board, which then boots normally. */
void slim4_power_off(void);
/* True when this boot was a wake from deep sleep by the power button. */
bool slim4_power_woke_by_button(void);
