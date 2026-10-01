#pragma once
// STRUTHIO HANDHELD · Waveshare ESP32-S3-Touch-LCD-3.5B pin map.
// Source: Waveshare's ESP-IDF example (esp_bsp/*.h, *.c; commit 840daf2). The
// schematic is the authority; recheck against it for the board revision in hand.
//
//   LCD  AXS15231B QSPI (SPI2)  CS 12  SCLK 5  D0 1  D1 2  D2 3  D3 4  BL 6 (LEDC)
//        reset through the TCA9554 I/O expander, EXIO1 (I2C 0x20)
//   I2C  SDA 8  SCL 7: AXP2101 0x34, TCA9554, ES8311, touch, IMU, RTC, camera SCCB
//   I2S  MCLK 44  BCLK 13  LRCK 15  DOUT 16  DIN 14 (ES8311)
//   SD   CMD 10  CLK 11  D0 9
//   CAM  XCLK 38  PCLK 41  VSYNC 17  HREF 18  D 45 47 48 46 42 40 39 21
//   BOOT 0    USB D-/D+ 19/20    UART0 TX 43
//
// THE WINGS USE THE CAMERA'S VSYNC/HREF PINS. GPIO17/18 are only free when no
// camera module is fitted and the camera is never initialised. A0 has no
// camera. Keep the FPC connector empty; the firmware has no camera code.
//
// Spare pins for the slide-switch "signal" wiring or later buttons, with no
// camera fitted: 21, 38, 39, 40, 41, 42, 47, 48. Avoid 45 and 46: they are
// strapping pins. If the SD slot stays empty, 9, 10 and 11 are free too.
// Check on the schematic which of these reach the expansion header.
#define STRUTHIO_GPIO_LEFT_WING   17
#define STRUTHIO_GPIO_RIGHT_WING  18

// Inputs are active-low: a normally-open switch connects the GPIO to GND when pressed.
#define STRUTHIO_BUTTON_ACTIVE_LEVEL 0
