# R28 (radio) — work in progress, not a release

This folder holds the R27 -> R28 edits for the peer-to-peer radio (U15 Seeed Wio-SX1262) while they are being
built. The released board is still `../SLIM4_R27.kicad_pcb`; nothing in the package reads this folder yet.

State:
- `r28_radio_parts.py` (edit 45) places U15 west of U1 on the back, R701/C701/C702, the module's B.Cu ground zone
  and stitching vias; it runs clean on a copy of R27 (all clearances asserted).
- `radio_router.py` does not yet route all eight signals: U1's free west-side pads (GPIO28-33) are enclosed by
  R27's existing escapes. The pin assignment in edit 45 will change to pads that escape (north row: GPIO39-41,
  GPIO53/54 route under the current rules). `r28_radio_routes.json` does not exist yet, so `build_r28.sh` cannot
  run to the end.
- The firmware pin defines wait for the final pin assignment.
