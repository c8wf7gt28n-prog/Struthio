#pragma once
#include <stdbool.h>

/* Bring-up console on the USB-C port (USB-Serial-JTAG): `help` lists the commands. */
void slim4_console_start(void);
/* True while a console command holds the screen (a test pattern or the self-test page). */
bool slim4_console_display_hold(void);
