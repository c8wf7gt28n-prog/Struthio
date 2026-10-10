# PCB R26 — reference only

The R26 board as delivered in package R31: `SLIM4_R26.kicad_pcb`, its project, `fp-lib-table`, the local `SLIM4.pretty` library (as in R26), the studio layer JSON, KiCad's DRC report (0 / 0 / 0) and the release gates (`RELEASE_GATES_R26.md`, copied from `RELEASE_GATES.md`). Superseded by PCB R27 in `LAYERS/01_PCB/` after the pre-order review of R26 (`CHECKS/PREORDER_REVIEW_R26/`), which found no design error but three margin weaknesses round the processor and five smaller ones.

What R27 changes from R26: 27 more ground vias in U1's exposed pad (4 → 31), each joined to the pad's copper; 10 µF at U1's core pins (C138, C139); a second 1 µF 50 V on the backlight boost output (C140); D2 60 V (STPS1L60ZFY); the charger's TS resistor R424 beside U10 (BQ_TS 88 mm → 5 mm); 22 Ω USB series resistors (R401, R402); silkscreen labels on the back. The core regulator's feedback route stays, checked over unbroken ground. Same outline, ports, connector positions and GPIOs; the DSI pairs are untouched (the DSI report is the same line for line).

It is kept because `LAYERS/01_PCB/R27_FROM_R26/build_r27.sh` rebuilds R27 from it, edit by edit.
