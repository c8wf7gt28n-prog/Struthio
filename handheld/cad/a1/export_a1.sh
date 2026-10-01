#!/usr/bin/env bash
# STRUTHIO HANDHELD · exports the A1 (A0.8.3) print files and preview renders,
# then runs the fit checks. Needs OpenSCAD (2021.01+); renders need a display
# (xvfb-run is used when there is none).
#   handheld/cad/a1/export_a1.sh
set -euo pipefail
cd "$(dirname "$0")"
SRC=STRUTHIO083.scad
mkdir -p stl svg renders
for p in front back left_button right_button; do
  openscad -q -o "stl/struthio_a083_$p.stl" -D "part=\"$p\"" "$SRC" &
done
openscad -q -o svg/struthio_a083_front_sticker.svg -D 'part="sticker"' "$SRC" &
wait
X=""; [ -z "${DISPLAY:-}" ] && command -v xvfb-run >/dev/null && X="xvfb-run -a"
r() { $X openscad -q --colorscheme=Tomorrow --imgsize=1400,1100 --projection=o --viewall --autocenter --camera="$2" -o "renders/$1.png" "views/$1.scad"; }
r front    0,0,300,0,0,0
r assembly 150,-190,230,0,0,0
r rear     0,0,300,0,0,0
r section  300,0,0,0,0,0
python3 sheet_a1.py
python3 check_a1.py
