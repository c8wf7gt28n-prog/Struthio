#pragma once
#include "driver/gpio.h"

/* SLIM4 board GPIO assignments (PCB R22 and R23 share them). Source of truth:
 * hardware/slim4/LAYERS/01_PCB/FIRMWARE_PINMAP.md, read from the board netlist. */

/* Gameplay controls: 10 k pull-ups on the board, switch to GND (active low). */
#define SLIM4_GPIO_BTN_LEFT       GPIO_NUM_1   /* SW1, left flap */
#define SLIM4_GPIO_BTN_RIGHT      GPIO_NUM_2   /* SW2, right flap */
#define SLIM4_GPIO_DART_LEFT      GPIO_NUM_3   /* SW3, DART rocker left */
#define SLIM4_GPIO_DART_RIGHT     GPIO_NUM_4   /* SW4, DART rocker right */

/* Power button SW5: 10 k pull-up + 100 nF, active low. LP GPIO, used as the deep-sleep wake source. */
#define SLIM4_GPIO_PWR_WAKE       GPIO_NUM_0
/* BOOT button SW7: strapping pin (low at reset = download mode); free to read after boot. */
#define SLIM4_GPIO_BOOT_BTN       GPIO_NUM_35

/* Audio: two MAX98357A, left and right slot of one I2S stream. */
#define SLIM4_GPIO_I2S_BCLK       GPIO_NUM_5
#define SLIM4_GPIO_I2S_LRCLK      GPIO_NUM_6
#define SLIM4_GPIO_I2S_DOUT       GPIO_NUM_7
#define SLIM4_GPIO_AUDIO_SD_CTRL  GPIO_NUM_8   /* high = amplifiers on (100 k pull-down) */

/* Display: TPS61165 backlight PWM (100 k pull-down = off); panel reset through Q1 (high = reset). */
#define SLIM4_GPIO_BACKLIGHT_PWM  GPIO_NUM_9
#define SLIM4_GPIO_LCD_RESET_GATE GPIO_NUM_10

/* Charger BQ24074 and USB-C TUSB320 (open drain, pulled up). */
#define SLIM4_GPIO_CHG_STATUS     GPIO_NUM_11  /* low = charging */
#define SLIM4_GPIO_PGOOD_STATUS   GPIO_NUM_44  /* low = valid USB input */
#define SLIM4_GPIO_USB_CURR_OUT1  GPIO_NUM_43
#define SLIM4_GPIO_USB_CURR_OUT2  GPIO_NUM_17
#define SLIM4_GPIO_BQ_EN1         GPIO_NUM_13  /* 10 k pull-up */
#define SLIM4_GPIO_BQ_EN2         GPIO_NUM_46  /* 10 k pull-down */
#define SLIM4_GPIO_BAT_ADC        GPIO_NUM_16  /* VBAT x 33 k / 133 k */
#define SLIM4_BAT_DIVIDER_NUM     133u
#define SLIM4_BAT_DIVIDER_DEN     33u

/* USB-Serial-JTAG (GPIO24 D-, GPIO25 D+) carries the console: never reconfigure them. */

/* Radio (PCB R28+): U15 RAKwireless RAK3172-SiP (RAK3172-SIP-9-SM-NI: STM32WLE5 in a 12 x 12 mm LGA, LoRa/FSK
 * 902-928 MHz, antenna on J701 U.FL) on U1 pins that had no net before R28. It runs the radio itself and takes AT
 * commands on its UART2 (115200 8N1); powered from 3V3_SYS through R701 (0 ohm). R702 10 k holds BOOT0 low. A board without U15 or R701 leaves these pins open, so the driver checks that
 * the module drives its TX line before it relies on it, and otherwise leaves every radio pin an input. */
#define SLIM4_GPIO_RADIO_UART_TX  GPIO_NUM_39  /* U1 transmits -> U15 pin 30 (UART2_RX) */
#define SLIM4_GPIO_RADIO_UART_RX  GPIO_NUM_40  /* U1 receives  <- U15 pin 29 (UART2_TX) */
#define SLIM4_GPIO_RADIO_NRST     GPIO_NUM_41  /* U15 pin 44, active low (R703 10 k pull-up, C726 100 nF) */
#define SLIM4_GPIO_RADIO_BOOT0    GPIO_NUM_50  /* U15 pin 43, high at reset = STM32 ROM bootloader (R702 pulls low) */
