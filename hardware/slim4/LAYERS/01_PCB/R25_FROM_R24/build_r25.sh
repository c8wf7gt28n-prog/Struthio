#!/bin/sh
# Rebuild the R25 board from the R24 board: R24 -> R25 edits, each in its own pcbnew process (KiCad 7.0.x,
# python3 with pcbnew, kicad-footprints 7.0.x installed in /usr/share/kicad/footprints).
#   sh build_r25.sh <path to a copy of REFERENCES/PCB_R24/SLIM4_R24.kicad_pcb renamed SLIM4_R25.kicad_pcb, beside copies of that
#   folder's SLIM4.pretty, fp-lib-table and SLIM4_R24.kicad_pro (renamed SLIM4_R25.kicad_pro)>
set -e
S=$(cd "$(dirname "$0")" && pwd); B=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
edit() { python3 "$S/run_edit.py" "$B" "$S/$1.py" 2>&1 | grep -v leak || true; }
edit r25_dsi_links                                                     # 25 DSI: 0 ohm links R301-R306 removed, direct links
edit r25_dsi_match                                                     # 26 DSI: flight-time matching meanders
edit r25_dsi_return                                                    # 27 DSI: return vias after the relink
edit r25_cpu_feeds                                                     # 28 In2 1V1 area reshaped; U1 plane vias
edit r25_dsi_ref                                                       # 29 In2 ground under the In3 DSI runs; 50 ohm widths
python3 "$S/r25_lib_sync.py" "$B" "$(dirname "$B")/SLIM4.pretty" 2>&1 | grep -v leak || true
python3 "$S/r25_meta.py" "$B" 2026-10-09                               # 30 title block R25, stackup, ENIG
(cd "$(dirname "$B")" && python3 "$S/fill_drc.py" "$B")                # zone refill + KiCad DRC
