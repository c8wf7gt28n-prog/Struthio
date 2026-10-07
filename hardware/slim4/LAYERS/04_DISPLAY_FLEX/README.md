# DISPLAY FLEX layer — R1: panel tail to the R22 board's J1

One custom 2-layer polyimide flex joins the Startek KD047HDFID001's 31-pin tail to the R22 board's J1.

- **Panel end:** Hirose FH26W-31S-0.3SHW(60), 31 pins at 0.3 mm, assembled by JLCPCB (LCSC C2973806, in stock). It takes a 0.20 mm tail, the thickness Startek's drawing gives for the KD047's tail end, and contacts the tail's underside. Insert the tail with its contacts ("conduct side") facing the flex.
- **J1 end:** 20 gold fingers, 0.30 mm wide at 0.50 mm pitch, on the bottom copper, with a 6 mm stiffener on the top side bringing the end to the 0.30 mm the FH12 needs. Insert into J1 with the fingers facing the board; pin 1 is marked "1".
- **Inside:** the panel pins fan out to 0.5 mm columns, and each signal crosses on the bottom copper in its own row. The 16 used J1 lines (11 signals and 5 grounds) run the length of the cable on the top copper over a bottom-copper ground plane, with the DSI pairs side by side. 0.10 mm tracks, 0.45/0.20 mm vias, KiCad DRC 0 / 0 / 0.

## Status: one table to fill

Everything is fixed except which of the panel's 31 pins carries which signal. Startek gives that only in the full KD047HDFID001 datasheet, which you request on their product page (it asks for your contact details).

When you have it:
1. Fill `panel_pinmap.csv`: for each pin 1–31, the panel's name for it and one role from `GND VCI IOVCC RESX CLKP CLKN D0P D0N D1P D1N LEDA LEDK NC`. Data lanes 2 and 3, TE and touch pins are `NC`; both LED cathodes are `LEDK`.
2. Run `python -B CHECKS/build_builder_packs.py <folder outside the package>` from the package root. Its `4_DISPLAY_FLEX/` folder then holds the flex order. Or, by hand, from this folder:

       python3 generate_flex.py panel_pinmap.csv OUT
       python3 export_flex.py OUT

3. Upload the Gerber zip, BOM and CPL (`OUT/SLIM4_DISPLAY_FLEX_R1_ORDER.zip`) to JLCPCB as a flex PCB with assembly. The README inside lists the options.

The generator refuses a pin map with unfilled rows, so an unfinished file cannot be ordered by accident.

## Preview

`PREVIEW_NOT_FOR_ORDER/` was generated from `panel_pinmap_PREVIEW.csv`, a placeholder pinout typical of 31-pin ST7703 panels. It shows the real shape, size (22.6 × 70 mm) and routing, and its 1:1 PDF lets you test-fit the cable route on printed parts before ordering. **Its pin order is a guess: do not order it.**

## Length

The default is 70 mm (`--length`), the route the case reserves: from where the panel tail ends, past the DART switches, around the board's bottom tab, to J1 on the back. Print the 1:1 template at 100 %, cut it out and route it through the printed case; then set `--length` before ordering. A few millimetres of slack can be folded in.

## Checks

`CHECKS/convergence_check.py` row N1 compares this generator's J1 finger map with the R22 board's J1 pads (position and net, all 20 pins); row H4 tracks the cable route in the case.

## Needs

KiCad 7.0.x (python3 with pcbnew, kicad-cli) and its footprint library in `/usr/share/kicad/footprints`.
