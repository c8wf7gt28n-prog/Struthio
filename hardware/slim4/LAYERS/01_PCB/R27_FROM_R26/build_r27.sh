#!/bin/sh
# Rebuild the R27 board from the R26 board: R26 -> R27 edits, each in its own pcbnew process (KiCad 7.0.x, python3
# with pcbnew, kicad-footprints 7.0.x installed in /usr/share/kicad/footprints).
#   sh build_r27.sh <path to a copy of REFERENCES/PCB_R26/SLIM4_R26.kicad_pcb renamed SLIM4_R27.kicad_pcb, beside
#   copies of that folder's SLIM4.pretty, fp-lib-table and SLIM4_R26.kicad_pro (renamed SLIM4_R27.kicad_pro)>
# The edits answer the pre-order review of R26 (CHECKS/PREORDER_REVIEW_R26). New parts come from KiCad's library
# (Capacitor_SMD, Resistor_SMD); r27_export_lib.py then writes the board's library copies (SLIM4.pretty beside the
# board) for the added and changed footprints.
set -e
S=$(cd "$(dirname "$0")" && pwd); B=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
edit() { python3 "$S/run_edit.py" "$B" "$S/$1.py" 2>&1 | grep -v leak || true; }
edit r27_u1_ground                                                     # 36 ground vias under U1's exposed pad
edit r27_core_bulk                                                     # 37 10 uF at U1's core pins (C138, C139)
edit r27_backlight                                                     # 39-40 C140 beside C309; D2 60 V
edit r27_ts                                                            # 41 R424 near U10
edit r27_usb                                                           # 42 R401/R402 22 ohm
edit r27_silk                                                          # 43 silkscreen labels
python3 "$S/r27_meta.py" "$B" 2026-10-10                               # 44 title block R27
python3 "$S/r27_export_lib.py" "$B" "$(dirname "$B")/SLIM4.pretty" C138 C139 C140 R424 R401 R402 D2
(cd "$(dirname "$B")" && python3 "$S/fill_drc.py" "$B")                # zone refill + KiCad DRC
P="$S/PLANE_CHECK_R27.txt"                                             # ground under FB_DCDC / EN_DCDC (review M1)
python3 "$S/r27_plane_check.py" "$B" > "$P" 2>&1 || { cat "$P"; exit 1; }; cat "$P"
