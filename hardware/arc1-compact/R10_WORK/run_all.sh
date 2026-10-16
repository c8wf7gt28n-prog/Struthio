#!/bin/sh
# ARC-1 R10 -- runs every R10 check in this tree and records exit statuses in qa/RUN_ALL.log.
# Needs: python3, cc, iverilog/vvp, verilator, yosys, nextpnr-ecp5. P&R targets take ~35 min in total.
cd "$(dirname "$0")" || exit 2
LOG=qa/RUN_ALL.log
: > "$LOG"
fail=0
step() { d=$1; shift; printf '== %s: %s\n' "$d" "$*" | tee -a "$LOG"
         (cd "$d" && "$@") >> "$LOG" 2>&1; rc=$?; printf '   exit %d\n' "$rc" | tee -a "$LOG"; [ "$rc" -eq 0 ] || fail=1; }
step architecture python3 gen_interface_matrix.py
step memory python3 gen_nor_partition.py
step hardware python3 gen_flash_pinmux.py
step fpga12 make lint rgmii sim build seeds report
step fpga12 make lint_mem sim_mem seeds_mem
step fpga45 make ref sim seeds sim45 seeds45
step fpga45 make sdram sdram_mutants sdram_corners sim45_mem seeds45_mem gpu_ref gpu_mutants
step f133/graphics_link make all
step firmware/f133_bootloader make all
step d213/gpu_driver make all
step fpga12/adaptive make all
step cad python3 gen/design.py
step . python3 cad/check/crosscheck_r10.py . cad/check/CROSSCHECK_R10.json
step . python3 cad/check/pin_review.py .
step . python3 cad/check/pin_function_matrix.py .
step cad python3 gen/gen_kicad.py
step cad python3 pcb/gen_pcb.py ..
step . git diff --exit-code -- architecture/R10_interface_matrix.csv architecture/R10_PINMUX_CONFLICTS.md \
  memory/R10_nor_partition.csv firmware/f133_bootloader/include/r10_nor_layout.h hardware/R10_flash_pinmux.csv hardware/lpf
[ "$fail" -eq 0 ] && echo R10_RUN_ALL_PASS | tee -a "$LOG" || echo R10_RUN_ALL_FAIL | tee -a "$LOG"
exit "$fail"
