# PCB R24 — reference only

The R24 board as delivered in package R29: `SLIM4_R24.kicad_pcb`, its project, `fp-lib-table`, the local `SLIM4.pretty` library (with R301–R306), the studio layer JSON, KiCad's DRC report (0 / 0 / 0) and the release gates (`RELEASE_GATES_R24.md`, renamed from `RELEASE_GATES.md`). Superseded by PCB R25 in `LAYERS/01_PCB/` after the R24 deep audit (DSI matched end to end, In2 ground under the In3 DSI runs, In2 planes at U1 corrected, stackup and ENIG in the board file; same pins, ports and outline).

Two statements in R24's documents were wrong and are corrected in R25's: the DSI matching (P = N within 0.01 mm, ≤ 8 ps in a pair, ≤ 39 ps clock to data) held only from the 0 Ω links to J1, not from U1's pads (full paths 377–460 ps), and U1's 3V3 vias under the In2 1V1 area were islands, not plane connections.

It is kept because `LAYERS/01_PCB/R25_FROM_R24/build_r25.sh` rebuilds R25 from it, edit by edit. The R24 edits themselves (`R24_FROM_R23/`) and their notes stay with the current board in `LAYERS/01_PCB/README_PCB_LAYER.md`.
