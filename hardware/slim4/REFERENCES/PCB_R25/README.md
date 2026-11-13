# PCB R25 — reference only

The R25 board as delivered in package R30: `SLIM4_R25.kicad_pcb`, its project, `fp-lib-table`, the local `SLIM4.pretty` library (unchanged in R26), the studio layer JSON, KiCad's DRC report (0 / 0 / 0) and the release gates (`RELEASE_GATES_R25.md`, renamed from `RELEASE_GATES.md`). Superseded by PCB R26 in `LAYERS/01_PCB/` after the R30/R25 pre-order audit: the three MIPI-DSI pairs are routed again as coupled pairs (constant width and gap per layer, P and N on the same layers through the same vias, ground vias at the layer changes, uninterrupted ground under every DSI track), and the stackup's centre prepreg is corrected to 0.1088 mm. Same pins, ports, outline and parts.

What the audit found in R25, and R26 answers: R25 matched the six DSI lines by flight time but routed them as single lines, each with its own meanders, layer changes and vias (P and N not always on the same layers), so they were not differential pairs; the stackup listed the 2116 prepreg as 0.1164 mm (JLCPCB lists 0.1088 mm today); and documents called the 1V1_HP rail "1.1 V" where its 499 k / 499 k divider on the TLV62569's 0.6 V reference sets 1.2 V.

It is kept because `LAYERS/01_PCB/R26_FROM_R25/build_r26.sh` rebuilds R26 from it, edit by edit. The R25 edits (`R25_FROM_R24/`) and their notes stay with the current board in `LAYERS/01_PCB/README_PCB_LAYER.md`.
