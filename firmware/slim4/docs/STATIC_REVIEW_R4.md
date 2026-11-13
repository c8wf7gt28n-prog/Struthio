# R22 firmware static review — R4

## Completed in source

- The R22 GPIO mapping is checked against the exported PCB pad/net map for all four active-low controls, three I²S lines, shared amplifier control, backlight, LCD reset gate, and UART0.
- The partition CSV is checked for duplicates, 4 KiB boundaries, 64 KiB app boundaries, overlap, capacity bounds, factory recovery, both OTA slots, and exact 64 MiB coverage.
- Input sampling debounces for 5 ms. The game API advances at fixed 60 Hz, caps catch-up work, delivers press/release edges once per pump, and copies caller-owned game metadata.
- Audio calls copy PCM into a bounded queue; multiple producers are serialized. A worker owns the I²S lifecycle and both amplifiers remain shut down while idle.
- OTA writes target only the next OTA app partition. A software boot check either confirms a pending candidate or requests rollback. The factory image is excluded.
- The display starts with a `STARTING` stamp. The final stamp says `VERIFIED` only after software checks pass; serial logs report degraded service mode otherwise.

## Validation performed here

- `python3 tools/validate_layout.py` — PASS (8 partitions; 64 MiB covered, no overlaps, app alignment and recovery/A/B roles valid).
- `python3 tools/check_pinmap.py` — PASS (12 expected signal routes).
- Python syntax compilation for both validation scripts — PASS.
- ESP-IDF build — NOT RUN; `idf.py` and the ESP32-P4 toolchain are unavailable in this workspace.
- Hardware behavior — NOT TESTED; board manufacture is pending.

## Still needed before treating this as production firmware

- Build with ESP-IDF 6.1 and resolve any component/API or sdkconfig errors.
- Verify the actual P4 board configuration, flash size, PSRAM mode, partition-table bootloader compatibility, and system image fit.
- Exercise panel initialization, ribbon behavior, control polarity, I²S channel separation, amp shutdown behavior, and power integrity on assembled hardware.
- Add authenticated update transport and recovery/service entry. The current update writer has no signature verification or USB receiver.
- Add a launcher/game package loader. Current code exposes the game API but does not load games from the `games` partition.
- Add a deliberate manufacturing-time test mode and retain boot logs plus panel/audio measurements for each board.
