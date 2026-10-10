#!/bin/sh
# Rebuild the R28 board from the R27 board: R27 -> R28 edits, each in its own pcbnew process (KiCad 7.0.x, python3
# with pcbnew, kicad-footprints 7.0.x installed in /usr/share/kicad/footprints).
#   sh build_r28.sh <path to a copy of REFERENCES/PCB_R27/SLIM4_R27.kicad_pcb renamed SLIM4_R28.kicad_pcb, beside
#   copies of that folder's SLIM4.pretty, fp-lib-table and SLIM4_R27.kicad_pro (renamed SLIM4_R28.kicad_pro)>
# R28 adds the peer-to-peer radio (U15 RAKwireless RAK3172-SiP, its DC-DC inductor, beads, decoupling, pull-ups, the
# RF pi network and the J701 U.FL socket) and changes nothing R27 had: only U1 pins with no net and empty copper are
# used. The signal geometry comes from r28_radio_routes.json (written offline by radio_router.py on the filled board
# after edit 45); the build itself only reads it.
set -e
S=$(cd "$(dirname "$0")" && pwd); B=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
edit() { python3 "$S/run_edit.py" "$B" "$S/$1.py" 2>&1 | grep -v leak || true; }
edit r28_radio_parts                                                   # 45 U15 and its 26 parts, ground and RADIO_3V3 zones, nets
edit r28_radio_routes                                                  # 46 the four radio signals, U1 to U15
python3 "$S/r28_meta.py" "$B" 2026-10-10                               # 47 title block R28
python3 "$S/r28_export_lib.py" "$B" "$(dirname "$B")/SLIM4.pretty" U15 L701 E701 E702 E703 J701 \
    R701 R702 R703 R704 C701 C711 C712 C713 C714 C715 C716 C717 C718 C719 C720 C721 C722 C723 C724 C725 C726
(cd "$(dirname "$B")" && python3 "$S/fill_drc.py" "$B")                # zone refill + KiCad DRC
P="$S/PLANE_CHECK_R28.txt"                                             # ground under FB_DCDC / EN_DCDC (review M1)
python3 "$S/r28_plane_check.py" "$B" > "$P" 2>&1 || { cat "$P"; exit 1; }; cat "$P"
