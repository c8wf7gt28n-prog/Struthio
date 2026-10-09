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
    uint8_t backlight_cap_percent; /* highest backlight level the power source can carry */
    bool battery_fault;       /* USB valid but the battery rail stays below 1.5 V: pack reversed or shorted */
    bool battery_approx;      /* ADC uncalibrated: battery_mv is approximate and drives no power decision */
    bool audio_muted;         /* amplifiers held off: USB below 1 A and no qualified cell (no budget for audio) */
} slim4_power_state_t;

/* Configures the power button, battery ADC, charger and USB-C status pins. */
slim4_status_t slim4_power_init(void);
/* Call about every 10 ms: samples the power button and updates the charger policy.
 * Returns true once the power button has been held for the power-off time. */
bool slim4_power_poll(void);
slim4_status_t slim4_power_read(slim4_power_state_t *out);
/* Implemented in slim4_board.c: re-applies the backlight with the power policy's cap. */
void slim4_board_backlight_cap_changed(uint8_t cap_percent);
/* Implemented in slim4_board.c: holds the amplifiers in shutdown while the power policy mutes audio. */
void slim4_board_audio_power_mute(bool mute);
/* Turns the display, backlight and amplifiers off and enters deep sleep.
 * The power button (GPIO0, active low) wakes the board, which then boots normally. */
void slim4_power_off(void);
/* True when this boot was a wake from deep sleep by the power button. */
bool slim4_power_woke_by_button(void);
