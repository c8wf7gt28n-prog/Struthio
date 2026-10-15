# R09 plan: layout, panel and closure of the R08 open items (explicit next steps)

R09 starts from the R08 native sources. **Edit `cad/gen/design.py` and regenerate**; do not hand-edit generated sheets
unless the generator is retired deliberately, which must be recorded in the CHANGELOG. Re-run
`python3 R08_WORK/tools/run_r08_checks.py` after every change.

## R09 intake: open issues with owner, gate and exact next validation

| # | Item | Owner | Gate | Next validation |
|---|---|---|---|---|
| 1 | Panel model, LVDS mapping, FFC connector, LCD supply, backlight driver (PANEL_INTERFACE_R09.md) | owner + Claude | G4 rerun | schematic + ERC + cross-check + budget, before any routing is called finished |
| 2 | USB power policy: ≥ 1.5 A Type-C requirement vs battery adoption (RK-USB-BUDGET) | **owner decision** | G7 | revised budget incl. backlight; BQ24074/TPS63070 SLIM4 candidate if a battery is chosen |
| 3 | Native Efinity compile (RUN_EFINITY_LOCALLY.md) | owner PC | **G5** | timing report with WNS ≥ 0 at sys 80 / PSRAM 40 MHz; pinout report diff = 0 |
| 4 | Vendor letters V1–V12 (VENDOR_OPEN_ITEMS.md) | owner sends | G1/G2/G7 | written answers filed in `vendor/` |
| 5 | Footprints: F133 EP, T35 FBGA400, DF40 receptacle, MAX98357A EP, the three SLIM4 copies, every STD_LIB IC land pattern vs its datasheet | Claude + independent reviewer | G4 | footprint review table with drawing references; IPC-7351 check |
| 6 | 3V3 supervisor dead band (RK-3V3-SUP) and the 1V2 low-corner 14 mV margin | Claude | G7 | choose 1 % regulators or accept, with the decision recorded |
| 7 | NOR / PSRAM VOH under load (RK-NOR-VOH, V5/V6) | Claude | G2 | IBIS-based DC check |
| 8 | NOR write-protect BP code for the lower 1 MiB; the loader (DRAM init) and the system image | firmware | G6 | host tests + measured image sizes into NOR_BOOT_AND_FLASH.md §3 |
| 9 | Exact MPNs + LCSC/stock for all TBD lines (sourcing/BOM_CANDIDATES.csv) | Claude + owner | G7 | BOM with stock snapshot date |
| 10 | Enclosure / PCB outline / button positions | owner | — | mechanical drawing |
| 11 | Schematic readability: R08 sheets are machine-placed (every pin carries a global net label; no drawn wires). For review, either improve the generator's placement (decoupling next to its IC, grouped functional blocks) or freeze the generator and hand-tidy in KiCad (record which) | Claude | G4 | independent reviewer can follow every sheet in the PDF |

## Layout work (R09)

1. Create `ARC1_R09.kicad_pcb` from the netlist (KiCad 9 "Update PCB from Schematic").
2. Stackup per MANUFACTURING_AND_BGA_PLAN.md §1, confirmed with JLCPCB's impedance calculator (LVDS 100 Ω diff, USB 90 Ω).
3. Placement priorities:
   - F133 + NOR + SPI0 isolation buffers within 25 mm;
   - MN820 receptacle at the panel side;
   - T35 + PSRAM + U26 together;
   - regulators at the USB edge.
4. Run `kicad-cli pcb drc` (native) until it reports 0 errors; length-match report; then Gerber/drill/BOM/CPL export.
5. SI/PI: IBIS simulation of SPI1 (30 MHz), PSRAM QSPI (20 MHz SCLK) and SPI0; PDN impedance for VDD_CORE and 1V2_T35.

## Release (R10, independent)

Independent audit of the schematic, layout, DRC, BOM and evidence before the first JLCPCB order. R08 and R09 do not approve fabrication.
