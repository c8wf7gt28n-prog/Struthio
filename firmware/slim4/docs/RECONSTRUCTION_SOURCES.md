# R22 reconstruction evidence

> **R22 evidence, kept for reference.** PCB R23 keeps every GPIO listed here; its display port, panel and connectors changed (`hardware/slim4/LAYERS/01_PCB/README_PCB_LAYER.md`). The panel question below is settled in R23: the Crystalfontz CFAF7201280A0-050TN's own tail plugs into J1, checked pin for pin. `tools/check_pinmap.py` checks the firmware against the R23 board.

- R22 native PCB: `KICAD_SOURCE/SLIM4_R22.kicad_pcb` from the supplied PCB order project. It stores footprint pad numbers and their board net assignments.
- R22 part choices and values: `SLIM4_R22_BOM.csv` from the supplied PCB order project.
- ESP32-P4 package pin names and GPIO mappings: Espressif ESP32-P4 Series Datasheet, Pin Overview: https://documentation.espressif.com/esp32-p4_datasheet_en.html
- R22 LCD connector: FH12-20S-0.5SH, 20 contacts, 0.5 mm pitch.
- Public Startek KD047HDFID001 product page currently lists 31 pins and 0.6 mm pitch: https://www.startek-lcd.com/product/detail?id=1961

The last two bullets conflict. Treat the panel plug as unresolved until the exact customer-supplied panel drawing/ribbon definition confirms connector contact count, pitch, pin order, and flex orientation. The reconstructed files describe R22 PCB-side connectivity; they do not declare that a particular panel tail mates with J1.
