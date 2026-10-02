#!/usr/bin/env bash
# STRUTHIO HANDHELD · exports the A1.5 print files, outlines, previews and the
# sticker art, then runs the fit checks. Needs OpenSCAD 2021.01+ (renders need
# a display; xvfb-run is used when there is none) and Python trimesh/shapely.
#   handheld/cad/a15/export_a15.sh
set -euo pipefail
cd "$(dirname "$0")"
SRC=STRUTHIO15.scad
mkdir -p stl svg renders
for p in front back mat; do openscad -q -o "stl/struthio_a15_$p.stl" -D "part=\"$p\"" "$SRC" & done
openscad -q -o svg/struthio_a15_front_sticker.svg -D 'part="sticker"' "$SRC" &
openscad -q -o svg/cp1_outline.svg -D 'part="cp1_outline"' "$SRC" &
openscad -q -o svg/cm1_outline.svg -D 'part="mat_outline"' "$SRC" &
openscad -q -o svg/keys_outline.svg -D 'part="keys_outline"' "$SRC" &
mkdir -p dxf
for p in cp1_outline mat_outline keys_outline; do openscad -q -o "dxf/$p.dxf" -D "part=\"$p\"" "$SRC"; done
wait
X=""; [ -z "${DISPLAY:-}" ] && command -v xvfb-run >/dev/null && X="xvfb-run -a"
r() { $X openscad -q --colorscheme=Tomorrow --imgsize="$3" --projection=o --viewall --autocenter --camera="$2" -o "renders/$1.png" "views/$1.scad"; }
r front        0,0,300,0,0,0          1400,2000
r front_inside 0,0,300,0,0,0          1400,2000
r internals    0,0,300,0,0,0          1400,2000
r rear         0,0,300,0,0,0          1400,2000
ra() { $X openscad -q --colorscheme=Tomorrow --imgsize="$3" --projection=p --viewall --autocenter --camera="$2" -o "renders/$1.png" "views/$1.scad"; }
ra cutaway         -260,-160,150,0,0,0   1600,1300
ra front_angle     110,-160,260,0,0,0    1300,1700
ra internals_angle -90,-170,260,0,0,0    1300,1700
if command -v node >/dev/null && node -e "import('/opt/node22/lib/node_modules/playwright/index.mjs')" 2>/dev/null; then
  python3 art/make_sticker.py && node art/render_sticker.mjs
  FRONT=renders/front.png python3 art/compose_front.py
else
  echo "SKIP: sticker art and composed front (Node + Playwright not found)"
fi
python3 check_a15.py
