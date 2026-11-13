# Game module contract

The first runtime links a game module into the system image. `slim4_game_start()` copies the descriptor and its short ID/version strings, so the descriptor itself may be stack allocated. The callbacks run serially from the platform task; a callback should not block for long periods.

## Timing and input

- `update()` runs at a fixed 60 Hz simulation step. If the task falls behind, the runtime performs at most four catch-up steps per pump.
- Input `down`, `pressed` and `released` use the `SLIM4_BUTTON_*` bit values. The board sampler applies 5 ms debounce to the four active-low switches.
- A press/release edge is delivered once even if the runtime performs multiple catch-up updates.
- `pause()` and `resume()` are called through the corresponding platform functions. Resume resets the simulation clock so paused time is not accumulated.

## Display

`render()` receives a 720×1280 RGB565 surface. Pixels are 16-bit values and `stride_bytes` is the row step; use the supplied stride instead of assuming rows are packed. The same surface is reused on later frames, so do not retain it after `render()` returns. `slim4_display_present()` waits for the DMA2D copy-complete callback before returning so the source surface is safe to repaint; that callback does not mean the panel has finished scanning the image.

## Audio

Audio input is interleaved signed 16-bit `L,R` PCM at 8–96 kHz. The platform copies input into a 16-chunk queue (256 stereo frames per chunk, maximum 4096 frames per call), then a dedicated task scales volume and feeds I²S. A successful call means samples were queued, not that playback has finished. The caller may reuse the source buffer after return. Concurrent producers are serialized; a full queue returns `SLIM4_ERR_NOT_READY`, so retry or drop the chunk according to game timing. BSP volume initializes at 35%, and the diagnostic boot app caps it at 20%; a game can set its desired level. Both amplifiers remain shut down until queued audio is processed.

## Save data

Save keys are 1–15 ASCII characters from letters, digits, `_`, `-`, and `.`. Each game ID receives a separate NVS namespace; system settings use `slim4_sys`. NVS capacity is limited, so use compact save blobs and avoid writing every frame.
