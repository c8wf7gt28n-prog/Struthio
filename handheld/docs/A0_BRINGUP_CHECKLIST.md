# A0 bring-up checklist

Before the board arrives: `handheld/run_tests.sh` must pass.

## Electrical bench first
- [ ] Run Waveshare factory / ESP-IDF display example before modifying firmware.
- [ ] Confirm exact board revision in hand.
- [ ] Copy the example's panel (AXS15231B QSPI) and power (AXP2101, backlight) init into
      `firmware/main/board_waveshare_35b.c`; set `g_panel`.
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
- [ ] Wire `board_audio_init` / `board_audio_cue` (ES8311 + NS4150B); confirm audio on low
      gain using 8-ohm speaker.

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
