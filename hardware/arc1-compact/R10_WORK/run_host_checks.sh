#!/bin/sh
# Portable R10 validation: Python + C compiler only. Does not claim RTL, P&R, or hardware evidence.
set -u
cd "$(dirname "$0")" || exit 2
LOG=qa/RUN_HOST_CHECKS.log
: > "$LOG"
fail=0
step() { d=$1; shift; printf '== %s: %s\n' "$d" "$*" | tee -a "$LOG"
         (cd "$d" && "$@") >> "$LOG" 2>&1; rc=$?; printf '   exit %d\n' "$rc" | tee -a "$LOG"; [ "$rc" -eq 0 ] || fail=1; }
step architecture python3 gen_interface_matrix.py
step memory python3 gen_nor_partition.py
step hardware python3 gen_flash_pinmux.py
step hardware python3 check_interconnect.py
step hardware python3 -m unittest -v test_interconnect.py
step fpga45 make gpu_ref gpu_mutants
step f133/graphics_link make all
step firmware/f133_bootloader make all
step d213/gpu_driver make all
step fpga12/adaptive make all
step cad python3 gen/design.py
step . python3 cad/check/crosscheck_r10.py . cad/check/CROSSCHECK_R10.json
step . python3 cad/check/pin_review.py .
step . python3 cad/check/pin_function_matrix.py .
[ "$fail" -eq 0 ] && echo R10_HOST_CHECKS_PASS | tee -a "$LOG" || echo R10_HOST_CHECKS_FAIL | tee -a "$LOG"
exit "$fail"
