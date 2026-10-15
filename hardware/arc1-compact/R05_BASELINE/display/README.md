# Compact display planning tool

The selected F133/T35/BT820 Compact direction is unchanged. This tool validates a proposed **Newhaven NHD-7.0-1024600AF-LSXP Rev2C** timing model against published ranges, derives the BT clock with exact rational arithmetic, and emits a conditional register worksheet. It does not initialize BT820 or certify display operation.

From the development-package root:

```sh
python display/validate_display.py --output display/planning_report.json
python -m unittest discover -s display/tests -v
```

The Python API is `validate_display(plan: dict) -> dict`. CLI exit 0 means the declared planning arithmetic is valid; exit 1 means invalid input or an invalid plan. `hardware_verified` is always false and `register_writes` is always null. Source-inferred or physical confirmations stay explicit. Reports are JSON; no third-party packages are required.

## Porch correction from R04

The source table's typical values close as `1344 = 1024 + 160 + 160` and `635 = 600 + 23 + 12`. Its minimum totals close the same way. These imply a **back interval that includes the sync pulse**. Visual endpoint/actual-panel confirmation is still open; the linked driver's extracted timing labels and table arithmetic support this interpretation.

Keep 48 MHz and totals 1280 by 625. Use panel-native H pulse/BP/FP **16/160/96**, and V **1/23/2**. Post-sync conventional back porches are **144 pixels/22 lines**. R04's additive 16/160/80 and 1/23/1 must not be copied unchanged as native panel quantities: under the inclusive-back convention they imply totals 1264 by 624. `r04_porch_assumption.json` preserves that failing regression.

The conditional worksheet uses AN097's front-porch-first origin: HSYNC0/1 96/112, HOFFSET256; VSYNC0/1 2/3, VOFFSET25; HCYCLE1280, VCYCLE625, HSIZE1024, VSIZE600. Single-channel one-pixel-per-clock `SO_MODE=0` is the candidate. These are modeled values, not register addresses, opcodes, or a complete ordered initialization script.

Nominal refresh is `48,000,000 / (1280 * 625) = 60`. Real oscillator tolerance, unique-frame cadence and 30/40 ms typical/maximum panel rise-plus-fall response remain physical acceptance work. The tool checks all printed p7 clock, active, total, sync, BP and FP constraints. It checks the reviewed BT width/area alignment and single-channel mode assumptions. It does not establish electrical skew, voltage, jitter, cable mapping or scanout execution.

## Primary sources and open confirmations

- S11: [Newhaven panel specification](https://newhavendisplay.com/content/specs/NHD-7.0-1024600AF-LSXP.pdf), printed pp4–7; timing table p7, drawing Rev2C, revision history through 9 April 2024.
- S13: [Newhaven-linked HX8282-A11 reference](https://support.newhavendisplay.com/hc/en-us/article_attachments/4414530591127), November 2013 preliminary version01, §10.2–10.3, printed pp38–40. Only source facts/derived arithmetic are recorded; the vendor PDF is not redistributed.
- S12: [BT82X programming guide v1.4](https://brtchip.com/wp-content/uploads/2026/09/BRT_AN_086_BT82X-Series-Programming-Guide-1.pdf), clock expression/Table21, scanout definitions/constraints pp56–59 and77. A fresh direct open failed; a companion review inspected available primary extracted text. Original PDF bytes/hashes are not available here.
- S18: [AN097 v1.0](https://brtchip.com/wp-content/uploads/2025/08/BRT_AN_097_Selection-and-Integration-of-LVDS-LCD-Panels-with-VM820C.pdf), §§4.3–4.4, printed pp21–22: conventional porch/register timing origin and channel modes.

Before a hardware attempt: visually confirm the panel timing endpoints and exact revision; review BT silicon/firmware/encoding, reset and power sequence; confirm LVDS slots, differential swing/common-mode, pair polarity, termination, skew and FFC contact orientation; design the 3.3-V panel rail and independent 150-mA nominal backlight current driver. VESA24/SPWG remains a mapping inference. Screen orientation and motion acceptance remain open. This worksheet does not resolve the separate HDMI clock/mapping study.
