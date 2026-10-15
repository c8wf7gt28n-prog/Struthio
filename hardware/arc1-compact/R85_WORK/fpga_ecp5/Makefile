# ARC-1 Compact R8.5 -- LFE5U-45F-6BG381C accelerator: lint, system simulation with C
# cross-simulation, open-toolchain build (Yosys -> nextpnr-ecp5 -> ecppack).
# Evidence: RTL_SIMULATED + OPEN_TOOLCHAIN_ROUTED (pinned versions: build_scripts/TOOL_VERSIONS.txt).
# Not on silicon.
IVERILOG ?= iverilog
VVP      ?= vvp
VERILATOR?= verilator
YOSYS    ?= yosys
NEXTPNR  ?= nextpnr-ecp5
ECPPACK  ?= ecppack
PYTHON   ?= python3
CC       ?= cc
OUT      ?= build
SEED     ?= 1
R05      ?= ../../R05_BASELINE
R06F     ?= ../../R06_WORK/fpga
R07P     ?= ../../R07_WORK/fpga/psram_r07
FW       ?= ../firmware
LPF      ?= constraints/arc1_ecp5_r85.lpf

RTL_COMMON = rtl/arc1_ecp5_top.sv rtl/accel_engine.sv rtl/arc1_transform_ecp5.sv rtl/mbx_regs_r85.sv rtl/psram_power_guard.sv \
      $(R06F)/mailbox/rtl/mbx_spi_slave.sv $(R06F)/mailbox/rtl/psram_bist.sv \
      $(R06F)/psram/rtl/psram_user_port.sv $(R06F)/psram/rtl/psram_qspi_core.sv
RTL_SYN = $(RTL_COMMON) rtl/arc1_ecp5_pll.v
RTL_SIM = $(RTL_COMMON) sim/arc1_ecp5_pll_sim.v
TB      = tb/tb_ecp5_top.sv $(R07P)/aps6404l_model_r07.sv
WARN    = -std=c11 -O2 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wshadow

.PHONY: all lint transform sim build bit clean
all: lint transform sim bit

$(OUT)/golden_frames.svh: $(R06F)/top/tools/golden_to_memh.py $(R05)/protocol/reference/golden_vectors.json
	mkdir -p $(OUT)
	$(PYTHON) -I $(R06F)/top/tools/golden_to_memh.py $(R05)/protocol/reference/golden_vectors.json $(OUT)

$(OUT)/ajob_vectors: $(FW)/tools/ajob_vectors.c $(FW)/src/accel_job.c $(FW)/src/crc32.c $(R05)/compute/arc1_transform.c
	mkdir -p $(OUT)
	$(CC) $(WARN) -I$(FW)/include -I$(R05)/compute $^ -o $@

$(OUT)/ajob/ajob_cases.svh: $(OUT)/ajob_vectors
	mkdir -p $(OUT)/ajob
	$(abspath $(OUT))/ajob_vectors $(OUT)/ajob > $(OUT)/ajob_vectors.log; rc=$$?; cat $(OUT)/ajob_vectors.log; exit $$rc

lint:
	mkdir -p $(OUT)
	$(VERILATOR) --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-TIMESCALEMOD --timing \
	  --top-module arc1_ecp5_top $(RTL_SIM) > $(OUT)/lint_ecp5.log 2>&1; rc=$$?; cat $(OUT)/lint_ecp5.log; exit $$rc

# unchanged R05 compute testbench (oracle vectors) against the pipelined ECP5 transform
transform:
	mkdir -p $(OUT)/r05tb
	$(PYTHON) -I $(R05)/compute/tests/generate_vectors.py $(OUT)/r05tb/vectors.hex
	$(IVERILOG) -g2012 -s transform_tb -o $(OUT)/r05tb/tb.vvp rtl/arc1_transform_ecp5.sv $(R05)/compute/tests/transform_tb.sv
	$(VVP) -n $(OUT)/r05tb/tb.vvp +VECTORS=$(OUT)/r05tb/vectors.hex > $(OUT)/transform_r05tb.log 2>&1; rc=$$?; \
	  tail -3 $(OUT)/transform_r05tb.log; test $$rc -eq 0 && grep -q PASS $(OUT)/transform_r05tb.log

sim: $(OUT)/golden_frames.svh $(OUT)/ajob/ajob_cases.svh
	$(IVERILOG) -g2012 -I $(OUT) -I $(OUT)/ajob -s tb_ecp5_top -o $(OUT)/tb_ecp5_top.vvp \
	  -Ptb_ecp5_top.GOLD_DIR='"$(OUT)"' -Ptb_ecp5_top.AJOB_DIR='"$(OUT)/ajob"' $(TB) $(RTL_SIM)
	$(VVP) -n $(OUT)/tb_ecp5_top.vvp > $(OUT)/sim_ecp5_top.log 2>&1; rc=$$?; \
	  grep -E '^(TEST|INFO|SUMMARY|TB_ERROR|MODEL_VIOLATION|TOP_ECP5)' $(OUT)/sim_ecp5_top.log; \
	  test $$rc -eq 0 && grep -q '^TOP_ECP5_TB_PASS$$' $(OUT)/sim_ecp5_top.log
	$(abspath $(OUT))/ajob_vectors check $(OUT)/ajob > $(OUT)/ajob_rtl_check.log; rc=$$?; cat $(OUT)/ajob_rtl_check.log; exit $$rc

$(OUT)/arc1_ecp5.json: $(RTL_SYN)
	mkdir -p $(OUT)
	$(YOSYS) -q -l $(OUT)/yosys.log -p 'read_verilog -sv $(RTL_SYN); synth_ecp5 -top arc1_ecp5_top -json $@; stat' > /dev/null

$(OUT)/arc1_ecp5.config: $(OUT)/arc1_ecp5.json $(LPF)
	$(NEXTPNR) --45k --package CABGA381 --speed 6 --json $< --lpf $(LPF) --textcfg $@ --seed $(SEED) \
	  --report $(OUT)/nextpnr_report.json --log $(OUT)/nextpnr.log > /dev/null 2>&1

$(OUT)/arc1_ecp5.bit: $(OUT)/arc1_ecp5.config
	$(ECPPACK) --compress --input $< --bit $@
	sha256sum $@ > $@.sha256

build: $(OUT)/arc1_ecp5.config
bit: $(OUT)/arc1_ecp5.bit
	cat $(OUT)/arc1_ecp5.bit.sha256

clean:
	rm -rf $(OUT)
