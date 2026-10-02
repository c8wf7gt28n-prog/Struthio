# A0 bring-up checklist

Before the board arrives: `handheld/run_tests.sh` must pass.

Also before the board: `firmware/idf_check/idf_check.sh` compiles the firmware against the real
ESP-IDF 5.5.5 headers and board drivers (run_tests.sh runs it).

## Electrical bench first
- [ ] Run Waveshare factory / ESP-IDF display example before modifying firmware.
- [ ] Confirm the exact board revision in hand; compare its schematic with `firmware/main/board_pins.h`.
- [ ] Leave the camera connector EMPTY: the wings use the camera's VSYNC/HREF pins (GPIO17/18).
- [x] Panel (AXS15231B over QSPI), TCA9554 LCD reset, AXP2101 rails and backlight are already ported from
      the vendor example into `board_waveshare_35b.c` / `board_pmu.cpp`. Expect to debug them, not write them.
- [ ] First flash: the log shows `AXP2101 id ...`, `AXS15231B 320x480 QSPI at 40 MHz`, and the greybox picture appears.
      If the screen stays dark, check the TCA9554 reset pulse and the backlight duty first.
- [ ] Every 300 frames the log prints `band-order N`; it must stay 0. Non-zero means bands reached the panel
      out of order (see board.h); `host/band_order_test` shows why.
- [ ] `idf.py build flash monitor`; confirm USB flashing and serial logging.
- [ ] Hold both wings at power-on: service mode. Record **GOLDEN PASS**, sim µs/tick,
      digest µs/tick and panel ms/frame from the screen or the log.
- [ ] Confirm GPIO17 and GPIO18 read HIGH idle / LOW pressed with display active
      (service mode shows live wing states and press counts).
- [ ] Confirm two-button chord at the 100 ms window (a straight-up flap in play).
- [ ] Thumb-test DART trials C (default), A and B (LEFT in service mode cycles them).
      Lock one only after real play.
- [ ] If 40-line bands misbehave on the AXS15231B, try full-frame writes; record which works.
- [ ] Confirm 30 fps sustained display path; attempt 60 fps second.
- [ ] Speaker on the header. Service mode: "AUDIO OK  MUSIC OK"; the round-clear sting plays after
      the checks. Hold LEFT 1 s to step the volume (starts at 2 of 4); a chime plays.
- [ ] In play: flap, ring, joust, egg and death sounds over the music; the music ducks on rings.
      Note the log's `audio <us>` (budget 5333 us) and whether `render` time changed.

## Mechanical fit
- [ ] Print front shell only; test LCD opening and board width.
- [ ] Print one wing cap + switch support; tune `SWITCH_PCB_PLANE_Z`.
- [ ] Print rear shell; verify board support pads do not touch fragile components.
- [ ] Check battery reference volume with dummy block before inserting a real cell.
- [ ] Check USB-C extension bend radius and plug removal.
- [ ] Verify PWR access without exposing BOOT as a normal player button.

## Prototype A0 pass condition
**Power -> direct game start -> complete a playable round using only the two physical wing buttons.**
No touchscreen is required for normal play.
