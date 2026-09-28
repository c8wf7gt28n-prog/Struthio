# STRUTHIO ESP32-S3 Prototype A0 firmware scaffold

This is a **bring-up scaffold**, not a finished port of the WebGPU game.

What is implemented now:
- A0 pin lock: GPIO17 = LEFT, GPIO18 = RIGHT, active-low to GND.
- 8 ms software debounce.
- Existing 100 ms opposite-wing chord window.
- Immediate first-wing flap; later chord can issue STRAIGHT correction just like the browser input path.
- Initial hold-to-DART experiment at 230 ms.
- hidden service-mode request by holding BOTH at boot for 650 ms.
- direct boot to `game_start_new_run()` after hardware initialization.
- fixed 60 Hz simulation loop with initial 30 fps render cadence.
- host-side tests for the input mapper.

## Host-test the control state machine
```bash
cd host_test
make run
```

## ESP-IDF integration path
1. Install ESP-IDF using Espressif's supported installer.
2. First build/flash Waveshare's ESP-IDF example for the exact 3.5B revision and prove the display/audio/power hardware works.
3. Create a clean ESP-IDF application and copy this `main/` directory into it.
4. Replace the `board_display_init`, `board_audio_init`, and `game_render` stubs with the tested Waveshare code/BSP calls.
5. Only then begin transplanting the deterministic STRUTHIO simulation modules into portable C/C++.

This repository intentionally does not vendor-copy Waveshare code. Their public repo and current examples should remain the upstream hardware reference.
