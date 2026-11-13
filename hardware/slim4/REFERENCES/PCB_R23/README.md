# PCB R23 — reference only

The R23 board as delivered in package R28: `SLIM4_R23.kicad_pcb`, its project, `fp-lib-table`, the local `SLIM4.pretty` library, the studio layer JSON, KiCad's DRC report (0 / 0 / 0) and the release gates (`RELEASE_GATES_R23.md`, renamed from `RELEASE_GATES.md`). Superseded by PCB R24 after the second hardware review (power layout; same pins, ports and outline), itself kept in `REFERENCES/PCB_R24/` and superseded by PCB R25 in `LAYERS/01_PCB/`.

It is kept because `LAYERS/01_PCB/R24_FROM_R23/build_r24.sh` rebuilds R24 from it, edit by edit. The R23 edits themselves (`R23_FROM_R22/`) and its notes stay with the current board in `LAYERS/01_PCB/README_PCB_LAYER.md`.
