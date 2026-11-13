#!/bin/sh
# Rebuild the R26 board from the R25 board: R25 -> R26 edits, each in its own pcbnew process (KiCad 7.0.x,
# python3 with pcbnew, kicad-footprints 7.0.x installed in /usr/share/kicad/footprints).
#   sh build_r26.sh <path to a copy of REFERENCES/PCB_R25/SLIM4_R25.kicad_pcb renamed SLIM4_R26.kicad_pcb, beside copies of that
#   folder's SLIM4.pretty, fp-lib-table and SLIM4_R25.kicad_pro (renamed SLIM4_R26.kicad_pro)>
# The DSI geometry comes from r26_dsi_routes.json (written offline by dsi_pair_router.py and dsi_geometry.py, see
# those scripts); the build itself only reads it. No footprint changes, so the board's library copies stay as they are.
set -e
S=$(cd "$(dirname "$0")" && pwd); B=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
edit() { python3 "$S/run_edit.py" "$B" "$S/$1.py" 2>&1 | grep -v leak || true; }
edit r26_clear                                                         # 31 clear the DSI area, move slow nets out of it
edit r26_dsi_route                                                     # 32 DSI as coupled pairs, matched, skew-compensated
edit r26_dsi_ref                                                       # 33 In2 ground under the In3 DSI sections
edit r26_nets                                                          # 34 reconnect the slow nets lifted by edit 31
python3 "$S/r26_meta.py" "$B" 2026-10-09                               # 35 title block R26, stackup 2116 0.1088 mm
(cd "$(dirname "$B")" && python3 "$S/fill_drc.py" "$B")                # zone refill + KiCad DRC
