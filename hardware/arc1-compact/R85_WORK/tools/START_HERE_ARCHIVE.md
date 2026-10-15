# ARC1_R08_ENGINEERING_SOURCE: start here

ARC-1 Compact **PASS 8 (R08)**, including the **NOR-boot corrective handoff v1.0**. Status: **HOLD / PARTIAL**.
**Not approved for fabrication. Nothing in this archive has been tested on hardware.**

1. `R08_WORK/STATUS_R08.md`: outcome against acceptance gates G1–G9 and corrective gates G0–G8, commands, results, blockers.
2. `R08_WORK/RISK_REGISTER_R08.md` and `R08_WORK/docs/R09_LAYOUT_AND_RELEASE_PLAN.md`: what is open and the explicit R09 plan.
3. `R08_WORK/cad/ARC1_R08.kicad_pro`: **native KiCad 9 hierarchical schematic** (open in KiCad ≥ 8; ERC report `cad/ERC.txt`,
   netlist `cad/NETLIST.xml`, plot `cad/ARC1_R08_schematic.pdf`). The schematic is generated from `cad/gen/design.py`;
   change the source and regenerate.
4. `R08_WORK/fpga/efinity/RUN_EFINITY_LOCALLY.md`: the owner must run Efinity (NATIVE_EDA_NOT_RUN here) before the PCB pin freeze.
5. Dossiers in `R08_WORK/docs/`: BOOT_TRACE_DOSSIER, NOR_BOOT_AND_FLASH (flash image), RECOVERY_DOSSIER (USB0/FEL, clip),
   POWER_TREE_AND_RESET (power + audio), PSRAM_POWER_R08, INTERCONNECT_MATRIX_R08, ENGINEERING_CHANGE_R08,
   SCHEMATIC_CROSSCHECK, MANUFACTURING_AND_BGA_PLAN, SLIM4_REUSE_DECISIONS.csv, FIRST_ARTICLE_DEBUG, VENDOR_OPEN_ITEMS, PANEL_INTERFACE_R09.
6. `R08_WORK/evidence/`: the exact runner output (one log per step, `summary.json`, hashes).
7. `R07_PRESERVED/ARC1_R07_SOURCE_ORIGINAL.zip`: the frozen R07 source, unchanged (digest in `DIGEST.txt`).

Re-run everything: unzip R07_PRESERVED, place `R08_WORK/` beside `R05_BASELINE/ R06_WORK/ R07_WORK/` inside
`arc1-compact/` (or use the git repo), then from `arc1-compact/` run `python3 R08_WORK/tools/run_r08_checks.py`.
The git-based frozen-tree check needs the repository (commit 1262c1a).

Verify this archive: `sha256sum -c MANIFEST_SHA256.txt` (in this folder).
