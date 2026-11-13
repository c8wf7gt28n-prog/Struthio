# R22 firmware static review — R5 diagnostics

## Diagnostic behavior

- A periodic 16,667 µs ESP timer drives full RGB565 redraws at a 60 Hz target while the firmware polls debounced controls between display ticks.
- Every newly pressed button increments its own counter, lights its screen indicator, changes the stamp color, and queues a 50 ms triangle-wave test tone on the matching logical audio channel.
- The audio worker is set to 20% digital volume for diagnostic tones; a successful queue only means software accepted the samples.
- A sweep bar visibly moves every frame. The screen and serial output report firmware render submissions per second, render/submit call duration, and late frames.
- ESP-IDF's DPI-panel DMA2D draw-bitmap hook is enabled for the full-frame copy path.
- The draw path waits for the DPI driver's color-transfer-complete callback before the diagnostic reuses its source framebuffer.
- The LCD DPI driver's `on_vsync` callback counts controller VSYNC events; the screen reports this separately from software draw FPS.
- The screen colors 58–62 FPS/VSYNC cyan, out-of-range readings red, and zero gold during measurement startup.
- The firmware remains a board diagnostic and platform API; no operating system layer, launcher, or game loader is added.

## Claims and limits

- Draw FPS is render submissions counted by firmware. VSYNC is counted from the ESP32-P4 DPI controller event and does not optically verify that the panel glass is displaying correctly.
- Render duration includes framebuffer painting and waiting for the DMA2D source-copy completion; it is not a CPU utilization benchmark or a panel VSYNC wait.
- Button state, counts, and debounce are software observations from GPIO reads. Physical switch feel and electrical noise need hardware checks.
- Speaker tones are generated and queued on one channel at a time for a single-side press. Firmware cannot confirm a connected speaker or acoustic output without listening or external measurement.
- Display, channel separation, backlight, power integrity, and actual 60 Hz refresh require manufactured hardware.

## Checks

- `python3 tools/validate_layout.py` — PASS.
- `python3 tools/check_pinmap.py` — PASS.
- ESP-IDF build — NOT RUN (`idf.py` and the ESP32-P4 toolchain are unavailable here).
- Hardware tests — NOT RUN (R22 board is not manufactured).

## Remaining platform work

- Build with the selected ESP-IDF version and confirm all component/API settings.
- Validate the P4, 64 MiB flash, PSRAM, display ribbon/panel, controls, audio routing, and battery/power behavior on hardware.
- Implement authenticated USB update/recovery and a game package launcher/loader before treating the firmware as a complete console platform.
