# R5 — interactive hardware diagnostics

- Replaced the idle bring-up loop with a simple 60 Hz target diagnostic screen; the full RGB565 frame is repainted and submitted on every display tick.
- Enabled ESP-IDF's DPI-panel DMA2D draw-bitmap hook for the full-frame copy path.
- Waited for the DPI color-transfer-complete callback before reusing the source framebuffer, avoiding a DMA read/write race.
- Registered the DPI VSYNC callback; the screen and serial log distinguish measured controller VSYNC rate from software draw submissions.
- Button presses change the stamp background color, light the matching control indicator, increment its on-screen counter, and remain visible in serial transition logs.
- Each control queues a 50 ms triangle-wave test tone to its corresponding left/right audio channel; left/right dart controls use a different pitch from flap controls.
- Screen reports measured firmware frame submissions per second, DPI VSYNC events per second, maximum render-and-submit call time, frame number, and late-frame count.
- FPS and VSYNC readings in the 58–62 range are cyan; values outside that range turn red while initial zero readings stay gold.
- Capped test tones to 20% digital volume and mapped flap/dart presses to 880/660 Hz on the corresponding stereo side.
- Boot software verification now also checks that the audio worker is available before confirming a pending OTA image.
- Kept this as a small firmware diagnostic mode; no OS shell, launcher, or game loader was added.

## Measurement limits

Draw FPS is calculated from diagnostic render attempts. VSYNC is counted from the ESP32-P4 DPI controller event callback; it verifies the controller's timing events, not optical output from the panel. Render/submit time is the elapsed firmware call duration, not CPU utilization. Tone queue success does not prove that a physical speaker is connected or audible. Visual and acoustic confirmation require the manufactured device.
