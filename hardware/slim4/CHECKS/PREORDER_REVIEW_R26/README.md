# Pre-order review of PCB R26 and firmware R11 (2026-10-09)

Five independent reviews, each checking every pin of its subsystem against the parts' datasheets and the R26 netlist (`R26_NETLIST.txt`, generated from `LAYERS/01_PCB/SLIM4_R26_PCB_LAYER.json`). Each report has a summary, findings with severity and evidence, an UNSURE list, a VERIFIED OK list and a bring-up probe table; `LAYERS/01_PCB/BRINGUP_PROCEDURE.md` combines the probe tables. The firmware findings were verified against ESP-IDF v6.1 and fixed in commit 1f491cd. Findings marked there as checked are the ones confirmed independently of the reviewer.

| Report | Subsystem | BLOCKER | MAJOR |
|---|---|---|---|
| `POWER_findings.md` | USB-C input, charger, battery, all regulators, reset supervisor | none | none (7 minor) |
| `P4CORE_findings.md` | ESP32-P4 (all 105 pads), flash, crystal, straps | none | 3 layout: core DC-DC 12–21 mm from U1 with a 33 mm FB_DCDC route; no bulk capacitor near the core pins; 4 ground vias under U1's exposed pad (checked: 4 × 0.2 mm) |
| `DISPLAY_findings.md` | J1 and the panel, supplies, reset, backlight, DSI, panel firmware | none | 1 firmware: 1000 Mbit/s exceeds the ILI9881C 2-lane limit (a safe 560 Mbit/s profile added) |
| `AUDIO_IO_findings.md` | MAX98357A ×2, controls, USB data and CC, connectors | none | none (7 minor) |
| `FIRMWARE_findings.md` | all firmware | 3 critical, fixed: the backlight PWM setting stopped the display bring-up on every board (checked against ESP-IDF's LEDC divider rule); too strict a panel ID; unbounded DSI waits | 4, fixed |

Some reports cite paths in the session scratchpad (downloaded datasheets); the sources are linked in each report.
