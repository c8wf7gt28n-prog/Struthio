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

step "wing buttons: unit tests + DART trial report"
make -s -C firmware/host_test run

step "firmware: type-check against the ESP-IDF host shim"
make -s -C firmware/host_test compile

printf '\nALL HANDHELD CHECKS PASS\n'
