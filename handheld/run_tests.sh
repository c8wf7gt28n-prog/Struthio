#!/usr/bin/env bash
# STRUTHIO HANDHELD · every check that does not need the board.
#   handheld/run_tests.sh
set -euo pipefail
cd "$(dirname "$0")"
step() { printf '\n== %s\n' "$*"; }

step "port authority: arcade sources unchanged since the port"
node tools/port_authority.mjs --check

step "generated C (tower table, rulebook header) matches the arcade"
node tools/gen_tower.mjs >/dev/null
node tools/gen_rules.mjs >/dev/null
if git rev-parse --git-dir >/dev/null 2>&1 && ! git diff --quiet -- core/struthio_tower.c core/struthio_rules.h; then
  echo "FAIL: regenerated core/struthio_tower.c or core/struthio_rules.h differ; review and commit them"; exit 1
fi
echo "PASS: generated sources are current"

step "golden traces: re-recorded from the browser authority, byte for byte"
node tools/golden_export.mjs --check | grep -E '^(SAME|DIFF)'

step "C core: bit-exact replay of every golden trace"
make -s -C host test

step "graphics: generated scene data (glyphs, swatches, island plans) matches the arcade"
node tools/gen_scene_data.mjs >/dev/null
if git rev-parse --git-dir >/dev/null 2>&1 && ! git diff --quiet -- render/struthio_scene_data.c; then
  echo "FAIL: regenerated render/struthio_scene_data.c differs; review and commit it"; exit 1
fi
echo "PASS: render/struthio_scene_data.c is current"

step "graphics: the device's decomposed ambience equals the shader's"
make -s -C host build/amb_test build/scene_check build/raster_check build/panel_check build/make_pak build/band_order_test
host/build/amb_test | tail -1

step "firmware: two-core band hand-off vs the AXS15231B QSPI write model"
host/build/band_order_test 200 | tail -1

# The rest compares against the browser's own WebGPU output and DOM HUD,
# captured with headless Chromium (tools/reference/capture.mjs --frames
# --textures, tools/reference/hud_capture.mjs) into build/reference.
REF_FRAMES="mortal:0,299,1479,2239,2809,2849,7399,8999,14142 climb:40,3000,6000 late:500,5000 duel:1200,9000 raw:700,15000"
if [ -f build/reference/mortal.ihash ] && [ -f build/reference/textures/world.rgba ] && [ -f build/reference/hud/hud.json ]; then
  step "graphics: C scene builder vs the browser's instance lists, every tick"
  (cd host && ./build/scene_check ../golden/*.trace) | tail -1

  step "graphics: C rasterizer vs WebGPU frames (3x canvas, quality 0 and 2)"
  for spec in $REF_FRAMES; do (cd host && ./build/raster_check "../golden/${spec%%:*}.trace" $(echo "${spec#*:}" | tr , " ")) | tail -1; done

  step "graphics: device asset pack + panel renderer vs the browser at 320x480"
  (cd host && ./build/make_pak ../build/reference ../build/assets/struthio.pak) | tail -1
  (cd host && ./build/panel_check --hud) | tail -1
  for spec in $REF_FRAMES; do (cd host && ./build/panel_check "../golden/${spec%%:*}.trace" $(echo "${spec#*:}" | tr , " ")) | tail -1; done
else
  step "graphics: SKIP browser comparisons (no build/reference; run tools/reference/capture.mjs --frames --textures and hud_capture.mjs)"
fi

step "wing buttons: unit tests + DART trial report"
make -s -C firmware/host_test run

step "firmware: type-check against the ESP-IDF host shim"
make -s -C firmware/host_test compile

step "firmware: compile against the real ESP-IDF 5.5.5 headers and board drivers"
if python3 -c "import kconfgen" 2>/dev/null && [ -d /usr/include/newlib ] && { [ -d build/idf_check/esp-idf ] || git ls-remote -q https://github.com/espressif/esp-idf.git v5.5.5 >/dev/null 2>&1; }; then
  firmware/idf_check/idf_check.sh | tail -1
else
  echo "SKIP: real-header check (needs pip esp-idf-kconfig, apt libnewlib-dev and git access to github.com)"
fi

printf '\nALL HANDHELD CHECKS PASS\n'
