# STRUTHIO SLIM4 R21 — engineering review hold

**NOT FOR FABRICATION OR ASSEMBLY.** This folder is the editable R21 KiCad review source. It is included so the visualization and source PCB stay together.

## What was checked

- Native KiCad DRC report: 0 violations, 0 unconnected pads, 0 footprint errors (see `NATIVE_KICAD_DRC.txt`). This is a draft-rule result, not manufacturer acceptance.
- PCB has 165 footprints, 587 pads, 117 nets, 2,675 routed track segments and 269 vias.
- PCB outline is approximately 99.2 × 125.0 mm; thickness 1.2 mm.

## Required before fabrication

1. Review the full editable schematic and run ERC; confirm it represents the R21 netlist and intended circuitry.
2. Validate ESP32-P4 power/boot/USB and flash circuits against current vendor references; complete a power-tree and current/thermal review.
3. Validate high-speed MIPI-DSI and USB routing with exact panel/connector stackups, controlled impedance, pair matching and return-path review. DRC does not verify signal integrity or impedance.
4. Confirm every footprint, land pattern, polarity, orientation and assembly-side choice against selected orderable JLCPCB parts and assembly capabilities.
5. Resolve exact panel FPC pinout, display, battery connector/protection, speaker harness and arcade-switch mounting/interface. Confirm case, brackets, keepouts, acoustic cavities and physical fit against real supplier drawings.
6. Run final production DRC using the selected board house rules; inspect Gerbers/drill outputs and assembly files (BOM, CPL) before ordering.
7. Update firmware for R21 GPIO remaps: USB_CURR_OUT1 GPIO43, PGOOD_STATUS GPIO44, BQ_EN2 GPIO46.

The R21 board is a routing checkpoint. Do not upload its Gerbers or order assembly until these gates are resolved and a separately reviewed release is approved.
