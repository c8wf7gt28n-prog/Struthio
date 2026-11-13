# PCB R22 — reference only

The R22 board as delivered in package R27: `SLIM4_R22.kicad_pcb`, its project, `fp-lib-table`, the local `SLIM4.pretty` library, the studio layer JSON, KiCad's DRC report (0 / 0 / 0) and the release gates (`RELEASE_GATES_R22.md`, renamed from `RELEASE_GATES.md`). Superseded by PCB R23 in `LAYERS/01_PCB/`.

It is kept because `LAYERS/01_PCB/R23_FROM_R22/build_r23.sh` rebuilds R23 from it, edit by edit. The R22 electrical and land-pattern review stays with the current board (`LAYERS/01_PCB/ELECTRICAL_REVIEW_R22.md`): it still covers every part R23 did not change.
