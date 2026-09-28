# STRUTHIO Prototype A0 validation report

Validation date: 2026-09-28

## Completed off-board checks
- Portable C two-button input mapper compiled with `-std=c11 -Wall -Wextra -Werror -O2`.
- Host test result: `PASS: STRUTHIO A0 input mapper host tests`.
- A0 mapper covers: 8 ms debounce, immediate directional flap, 100 ms opposite-wing chord correction, one-shot 230 ms hold-to-DART experiment, and 650 ms BOTH-at-boot service request.
- ESP-IDF scaffold protects shared input sample/consume state with a FreeRTOS critical section.
- Simulation scheduler uses a rational microsecond cadence averaging exactly 60 ticks/second; the first renderer target remains 30 fps.
- Front shell, rear shell, LEFT cap, and RIGHT cap STLs were regenerated from the included OpenSCAD source.
- After normal STL vertex welding, all four exported STLs validate as watertight, single connected solids.
- Rear internal posts/pads/rails were deliberately overlapped into the rear wall to eliminate floating print islands.
- Front speaker slots were shortened so no isolated plastic strip remains between the wing openings.
- Package includes a SHA-256 manifest.

## Deliberately not claimed yet
These require the physical Waveshare board / switches / battery / speaker:
- ESP-IDF compile and flash against the exact 3.5B hardware revision in hand.
- Real GPIO17/GPIO18 conflict test with display/audio/storage active.
- AXS15231B QSPI sustained 30/60 fps benchmark.
- Physical board fit, glass clearance, button travel and switch feel.
- USB-C panel-extension part, insertion geometry and bend radius.
- Audio loudness/acoustic volume.
- Battery charge/runtime/thermal behavior.
- Full STRUTHIO 1.6 deterministic core equivalence on ESP32-S3.

A0 passes only when: **POWER ON -> STRUTHIO STARTS -> A PLAYABLE ROUND IS COMPLETED USING ONLY THE TWO PHYSICAL BUTTONS.**
