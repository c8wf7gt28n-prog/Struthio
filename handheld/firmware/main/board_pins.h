#pragma once

// Waveshare ESP32-S3-Touch-LCD-3.5B Prototype A0 wing inputs.
// Cross-checked against the board's published expansion pinout.
#define STRUTHIO_GPIO_LEFT_WING   17
#define STRUTHIO_GPIO_RIGHT_WING  18

// Inputs are active-low: normally-open switch connects GPIO to GND when pressed.
#define STRUTHIO_BUTTON_ACTIVE_LEVEL 0
