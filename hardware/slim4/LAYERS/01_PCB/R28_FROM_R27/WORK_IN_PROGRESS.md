# R28 (radio) — work in progress, not a release

This folder holds the R27 -> R28 edits for the peer-to-peer radio while they are being built. The released board is
still `../SLIM4_R27.kicad_pcb`; nothing in the package reads this folder yet.

The radio is U15, a RAKwireless RAK3172-SiP (RAK3172-SIP-9-SM-NI: STM32WLE5 LoRa/FSK, 12 x 12 mm LGA-73, RUI3 AT
firmware on UART2). It needs four U1 lines (UART TX / RX, NRST, BOOT0 on GPIO39 / 40 / 41 / 50, pads 80 / 81 / 82 /
93), the most U1's free pads can escape. A bare SX1262 needs about ten and was ruled out: the router showed U1's
pocket holds only about five escapes.

State:
- `r28_radio_parts.py` (edit 45) places U15 west of U1 on the back with the parts of RAKwireless's RAK3272-SiP
  reference: L701 15 uH for the internal DC-DC, beads E701-E703 (VDDSMPS, VDDRF, VDDPA), decoupling C711-C723,
  NRST R703 / C726, BOOT0 R702, the RF pi network C724 (DNP) / R704 0 ohm / C725 (DNP), J701 U.FL, the supply
  link R701 0 ohm from 3V3_SYS, and C701 bulk. It also adds a B.Cu ground zone with via-in-pad under the SiP and an
  In3 RADIO_3V3 pour. It runs clean on a copy of R27, and two runs give the same board item for item. The
  parts-only DRC shows only the library warnings that the export step clears, plus the four unrouted signals.
- `radio_router.py` routes the four signals; its output `r28_radio_routes.json` is what edit 46 draws.
- Firmware (R13 driver, self-test, console) names the SiP pins and builds clean.
