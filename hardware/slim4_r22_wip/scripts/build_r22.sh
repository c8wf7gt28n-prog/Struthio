#!/bin/sh
# Rebuild the R22 board from the R21 board: R21 -> R22 edits, each in its own pcbnew process (KiCad 7.0.x,
# python3 with pcbnew, kicad-footprints 7.0.x installed in /usr/share/kicad/footprints).
#   sh build_r22.sh <path to a copy of SLIM4_R21.kicad_pcb, beside SLIM4_R21.kicad_pro and SLIM4.pretty>
set -e
S=$(cd "$(dirname "$0")" && pwd); B=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
python3 "$S/r22_usb.py" "$B" 2>&1 | grep -v leak || true                 # 1 USB-C -> USB-Serial-JTAG (GPIO24/25)
python3 "$S/r22_fp.py" "$B" 2>&1 | grep -v leak || true                  # 2 land-pattern fixes (library footprints)
for e in r22_sw r22_esd r22_y1 r22_conn; do                               # 3-6 local re-routes
  python3 "$S/run_edit.py" "$B" "$S/$e.py" 2>&1 | grep -v leak || true
done
python3 "$S/r22_lib_sync.py" "$B" "$(dirname "$B")/SLIM4.pretty" 2>&1 | grep -v leak || true
python3 "$S/r22_xtal.py" "$B"                                             # 7 crystal load caps 12 pF
(cd "$(dirname "$B")" && python3 "$S/fill_drc.py" "$B")                   # zone refill + KiCad DRC
