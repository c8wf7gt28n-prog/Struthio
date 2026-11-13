# R4 static-debug pass

- Fixed the main poll interval so the frame pump can actually reach 60 Hz; added fixed simulation steps with bounded catch-up.
- Added 5 ms switch debounce, one-shot edge delivery during catch-up, safe copied game descriptors, pause/resume and per-game save namespaces.
- Moved PCM writes off the game loop into a bounded audio queue and worker; default digital volume is 35%, amps remain off when idle, and amp enable precedes I²S clocks.
- Added a transport-neutral A/B update writer that preserves the factory recovery image and a first-boot rollback check for display/input initialization.
- Strengthened partition checks to verify 64 KiB application alignment, factory recovery plus OTA A/B slots, 64 MiB coverage and no overlap.
- Fixed the static partition validator's project-root and tuple-comparison bugs so it checks the actual CSV and can pass valid R22 layouts.
- Added an honest boot-result stamp (`STARTING`, then software `VERIFIED` or `SERVICE MODE`) and serial readiness summary.
- Serialized concurrent audio producers and mute-time queue clearing with a mutex to protect queued PCM data.
- Updated game API, first-boot and system update documentation.

## Validation boundary

The host-side partition and pin-map checks pass. ZIP integrity passes. ESP-IDF compilation and hardware checks have not run: `idf.py` is unavailable in this environment and the board has not been manufactured. USB update transport, launcher/game loader and image authentication remain future work.
