# R12 — fixes from the pre-order review, USB console, PCB R27

Five independent reviews of PCB R26 and firmware R11 before the first boards were ordered (`hardware/slim4/CHECKS/PREORDER_REVIEW_R26/`). The firmware review found three faults that would have stopped every board's display; R12 fixes them and everything else the reviews raised for the firmware. Version 0.11.0. No pin changed: PCB R27 adds parts and ground vias only, and `tools/check_pinmap.py` passes 19/19 on it.

Faults that would have shown on every board:
- **Backlight PWM.** 20 kHz at 12 bits needs an 81.92 MHz timer clock: ESP-IDF's LEDC divider check rejects it (divider 250, at least 256 needed), and that error stopped the whole display bring-up, so every screen would have stayed dark. Now 11 bits (divider 500), a compile-time check on the divider, and a backlight failure no longer stops the panel bring-up (the self-test reports BACKLIGHT FAIL).
- **Panel ID.** The self-test accepted 98 81 0C only; the datasheet gives 98 81 1C and Espressif's logs 5C, so a good panel would have read PANEL FAIL. Now 98 81 xx, with the version byte reported.
- **Unbounded DSI waits.** ESP-IDF's DSI bus setup waits without a limit for the D-PHY PLL and the lanes' stop state, so a board with no VDDO_MIPI_2V5 would have hung at boot. The display bring-up now runs in its own task with an 8 s limit; the boot goes on and the log names the stage.

Display:
- **Safe DSI profile, now the default.** 2 lanes at 1000 Mbit/s are 1.77 times the ILI9881C datasheet's 2-lane limit for RGB565 (566 Mbit/s). It is Espressif's own setting and works on their panel, but it is outside the specification, so a new board starts at 560 Mbit/s a lane and a 60 MHz pixel clock (about 45 Hz). `display fast` on the console selects 1000 Mbit/s and 78 MHz (59 Hz) for the next boot; keep it only if the test patterns stay clean.
- A display mutex keeps the console, the self-test page and the main loop from drawing at once. The panel reset gate's level is set before its output is enabled. The backlight comes on only for a panel that answered.

Bring-up console (`main/slim4_console.c`, `docs/FIRST_BOOT.md` *Console*):
- On the USB-C port: `info`, `report`, `page`, `gpio`, `power`, `panel`, `bl`, `pattern white|black|red|green|blue|bars|checker|gradient`, `diag`, `display safe|fast`, `tone left|right|both`, `vol`, `sleep`, `reboot`. It starts right after the GPIO checks, so it answers even when a later stage stopped.
- USB-Serial-JTAG is now the primary console, so the bootloader's lines reach the USB-C port too (UART0's pins reach nothing on the board). With no terminal attached, output is dropped rather than waited for.

Power:
- **Charge time across heat suspends** (power review M7). Leaving a USB suspend restarts the BQ24074's safety timer (datasheet 9.3.5.6), so a board that kept getting hot would get a new 4–6 h charge window after every heat suspend. The firmware now counts charge time over the USB session; once a suspend has restarted the timer and charging has run 6 h in all, it stops charging until the cell is down to 3.6 V or USB is unplugged. 9 new host cases, hours of simulated charging.
- BQ_EN2 is never pulled toward its active level during the self-test (that could put the charger into USB suspend).

Self-test and others:
- SHORTS passes only when every neighbouring pad pair was covered (otherwise INFO). A status output that switches during one scan of two is INFO, not FAIL. Longer detail lines; the GPIO results are logged at once.
- NVS is erased and re-initialised once if it will not open. The OTA image is confirmed before the self-test page. The diagnostic display gives up after 60 failed frames in a row, not on the first.
- Audio keeps its clocks until the DMA has drained, sends silence when the queue is empty, and accepts only the MAX98357A's sample rates (8–96 kHz).
- The boot log and screens say PCB R27 and firmware R12.

ESP-IDF v6.1, esp32p4: full clean build with no warnings. Host tests: 51 power-policy and 65 self-test cases, all passing. Not yet run on hardware.
