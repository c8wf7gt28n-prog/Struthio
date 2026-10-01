#!/usr/bin/env bash
# STRUTHIO HANDHELD · exports the A1 (A0.8.3) print files and preview renders,
# then runs the fit checks. Needs OpenSCAD (2021.01+); renders need a display
# (xvfb-run is used when there is none).
#   handheld/cad/a1/export_a1.sh
set -euo pipefail
cd "$(dirname "$0")"
SRC=${SRC:-STRUTHIO084.scad}
mkdir -p stl svg renders
for p in front back left_button right_button; do
  openscad -q -o "stl/struthio_a084_$p.stl" -D "part=\"$p\"" "$SRC" &
done
openscad -q -o svg/struthio_a084_front_sticker.svg -D 'part="sticker"' "$SRC" &
wait
X=""; [ -z "${DISPLAY:-}" ] && command -v xvfb-run >/dev/null && X="xvfb-run -a"
r() { $X openscad -q --colorscheme=Tomorrow --imgsize=1400,1100 --projection=o --viewall --autocenter --camera="$2" -o "renders/$1.png" "views/$1.scad"; }
r front    0,0,300,0,0,0
r assembly 150,-190,230,0,0,0
r rear     0,0,300,0,0,0
r wings    0,-60,120,0,0,0
r section  300,0,0,0,0,0
python3 sheet_a1.py
# STRUTHIO art: sticker cut to the exported template, and the player's-view front
# (needs Node + Playwright for the 600 dpi render; skipped if absent)
if command -v node >/dev/null && node -e "import('/opt/node22/lib/node_modules/playwright/index.mjs')" 2>/dev/null; then
  python3 art/make_sticker.py && node art/render_sticker.mjs
  $X openscad -q --colorscheme=Tomorrow --imgsize=1400,1900 --projection=o --viewall --autocenter --camera=0,0,300,0,0,0 -o renders/front_tall.png views/front.scad
  FRONT=renders/front_tall.png python3 art/compose_front.py
else
  echo "SKIP: sticker art and composed front (Node + Playwright not found)"
fi
$X openscad -q --colorscheme=Tomorrow --imgsize=1200,1000 --projection=p --viewall --autocenter --camera=-60,-120,200,0,0,0 -o renders/rear_angle.png views/rear_angle.scad
python3 - <<'PY'
from PIL import Image
a = Image.open('renders/wings.png'); b = Image.open('renders/rear_angle.png')
b = b.resize((round(b.width * a.height / b.height), a.height))
s = Image.new('RGB', (a.width + b.width, a.height), (248, 248, 246)); s.paste(a, (0, 0)); s.paste(b, (a.width, 0))
s.save('renders/a084_identity_details.png', optimize=True)
PY
python3 check_a1.py
