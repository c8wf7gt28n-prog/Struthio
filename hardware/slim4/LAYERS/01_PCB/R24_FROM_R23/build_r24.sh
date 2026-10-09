#!/bin/sh
# Rebuild the R24 board from the R23 board: R23 -> R24 edits, each in its own pcbnew process (KiCad 7.0.x,
# python3 with pcbnew, kicad-footprints 7.0.x installed in /usr/share/kicad/footprints).
#   sh build_r24.sh <path to a copy of REFERENCES/PCB_R23/SLIM4_R23.kicad_pcb renamed SLIM4_R24.kicad_pcb, beside copies of that
#   folder's SLIM4.pretty, fp-lib-table and SLIM4_R23.kicad_pro (renamed SLIM4_R24.kicad_pro)>
set -e
S=$(cd "$(dirname "$0")" && pwd); B=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
edit() { python3 "$S/run_edit.py" "$B" "$S/$1.py" 2>&1 | grep -v leak || true; }
edit r24_planes                                                        # 16 In2 BAT_PLUS and SYS_RAW planes
edit r24_rails                                                         # 17 thin battery/system rails removed
edit r24_charger                                                       # 18 charger: thermal vias, wider VBUS, TMR open
edit r24_u4                                                            # 19 3.3 V buck-boost layout
edit r24_u3                                                            # 20 1.1 V buck layout
edit r24_u7                                                            # 21 backlight boost rebuilt east
edit r24_amps                                                          # 22 amplifier bulk capacitors
edit r24_dsi                                                           # 23 DSI return vias
edit r24_widen                                                         # 24 redundant battery run; widen power and ground
python3 "$S/r24_lib_sync.py" "$B" "$(dirname "$B")/SLIM4.pretty" 2>&1 | grep -v leak || true
(cd "$(dirname "$B")" && python3 "$S/fill_drc.py" "$B")                # zone refill + KiCad DRC
