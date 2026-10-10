# R3 firmware bring-up update

- Added the concrete R22 display path for the assumed 720×1280 ST7703 panel: P4 MIPI D-PHY LDO, two-lane DSI + DBI, reset-gate sequencing, TPS61165 backlight PWM, PSRAM RGB565 canvas, and a visible boot stamp.
- Added stage-specific display failure logs so first-board bring-up reports where initialization stopped.
- Added continuous active-low control transition logs for the four mapped game switches.
- Corrected the frame pump to fixed 60 Hz simulation steps with bounded catch-up, added 5 ms switch debounce, and made game descriptors safe from stack lifetime errors.
- Added per-game NVS save namespaces and key validation.
- Added the transport-neutral A/B image writer and an OTA first-boot self-test/rollback decision. USB transfer transport remains future work.
- Updated the hardware manifest and first-boot instructions to make the ribbon/panel a working assumption while retaining physical qualification as a test.
- Added stereo 16-bit Philips I²S output on the mapped GPIO5/6/7 pins, digital volume scaling (35% default), and deferred amp enable through GPIO8. The R22 resistor ladder selects the independent left/right slots; firmware enables the amps before starting clocks. Verify physical channel identity and safe volume on first hardware.
- Verification run: partition layout and GPIO/pin-map static checks pass. ESP-IDF compilation and board tests are not available in this environment; build with ESP-IDF 6.1 before flashing.
