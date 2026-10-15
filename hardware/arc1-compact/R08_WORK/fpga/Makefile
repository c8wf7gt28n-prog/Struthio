# ARC-1 Compact R08 T35 RTL: lint, system simulation, open-source synthesis estimate.
# RTL_SIMULATED / OPEN_SOURCE_SYNTH_ESTIMATE only. NATIVE_EDA_NOT_RUN (Efinity: see efinity/).
IVERILOG ?= iverilog
VVP      ?= vvp
VERILATOR?= verilator
YOSYS    ?= yosys
PYTHON   ?= python3
OUT      ?= build
R05      ?= ../../R05_BASELINE
R06F     ?= ../../R06_WORK/fpga
R07P     ?= ../../R07_WORK/fpga/psram_r07

RTL = rtl/arc1_t35_top_r08.sv rtl/psram_power_guard.sv rtl/mbx_regs_r08.sv \
      $(R06F)/mailbox/rtl/mbx_spi_slave.sv $(R06F)/mailbox/rtl/mbx_loopback.sv $(R06F)/mailbox/rtl/psram_bist.sv \
      $(R06F)/psram/rtl/psram_user_port.sv $(R06F)/psram/rtl/psram_qspi_core.sv
TB  = tb/tb_top_r08.sv $(R07P)/aps6404l_model_r07.sv

.PHONY: all lint sim synth-efx clean
all: lint sim synth-efx

$(OUT)/golden_frames.svh: $(R06F)/top/tools/golden_to_memh.py $(R05)/protocol/reference/golden_vectors.json
	mkdir -p $(OUT)
	$(PYTHON) -I $(R06F)/top/tools/golden_to_memh.py $(R05)/protocol/reference/golden_vectors.json $(OUT)

lint:
	mkdir -p $(OUT)
	$(VERILATOR) --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM \
	  --top-module arc1_t35_top_r08 $(RTL) > $(OUT)/lint_top_r08.log 2>&1; rc=$$?; cat $(OUT)/lint_top_r08.log; exit $$rc

sim: $(OUT)/golden_frames.svh
	$(IVERILOG) -g2012 -I $(OUT) -s tb_top_r08 -o $(OUT)/tb_top_r08.vvp -Ptb_top_r08.GOLD_DIR='"$(OUT)"' $(TB) $(RTL)
	$(VVP) -n $(OUT)/tb_top_r08.vvp > $(OUT)/sim_top_r08.log 2>&1; rc=$$?; \
	  grep -E '^(TEST|INFO|SUMMARY|TB_ERROR|MODEL_VIOLATION|TOP_R08)' $(OUT)/sim_top_r08.log; \
	  test $$rc -eq 0 && grep -q '^TOP_R08_TB_PASS$$' $(OUT)/sim_top_r08.log

synth-efx:
	mkdir -p $(OUT)
	$(YOSYS) -q -l $(OUT)/synth_top_r08_efx.log -p 'read_verilog -sv $(RTL); synth_efinix -top arc1_t35_top_r08; stat' > /dev/null
	grep -E 'EFX_|Number of cells' $(OUT)/synth_top_r08_efx.log | tail -8

clean:
	rm -rf $(OUT)
