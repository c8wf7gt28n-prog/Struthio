# A0 bring-up checklist

## Electrical bench first
- [ ] Run Waveshare factory / ESP-IDF display example before modifying firmware.
- [ ] Confirm exact board revision in hand.
- [ ] Confirm USB flashing and serial logging.
- [ ] Confirm GPIO17 and GPIO18 read HIGH idle / LOW pressed with display active.
- [ ] Confirm two-button chord test at 100 ms window.
- [ ] Confirm hold-to-DART test at initial 230 ms threshold.
- [ ] Measure full-screen RGB565 transfer time at 320x480.
- [ ] Confirm 30 fps sustained display path; attempt 60 fps second.
- [ ] Confirm audio on low gain using 8-ohm speaker.

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
