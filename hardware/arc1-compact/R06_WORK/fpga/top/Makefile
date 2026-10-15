# ARC-1 Compact R06 T35 top level: system RTL simulation, lint, synthesis estimate.
# RTL_SIMULATED / OPEN_SOURCE_SYNTH_ESTIMATE only. NATIVE_EDA_NOT_RUN.
IVERILOG ?= iverilog
VVP      ?= vvp
VERILATOR?= verilator
YOSYS    ?= yosys
PYTHON   ?= python3
OUT      ?= build
R05      ?= ../../../R05_BASELINE

RTL = arc1_t35_top.sv ../mailbox/rtl/mbx_spi_slave.sv ../mailbox/rtl/mbx_regs.sv \
      ../mailbox/rtl/mbx_loopback.sv ../mailbox/rtl/psram_bist.sv \
      ../psram/rtl/psram_user_port.sv ../psram/rtl/psram_qspi_core.sv
TB  = tb/tb_top.sv ../psram/tb/aps6404l_model.sv

.PHONY: all sim lint synth-efx clean
all: lint sim synth-efx

$(OUT)/golden_frames.svh: tools/golden_to_memh.py $(R05)/protocol/reference/golden_vectors.json
	mkdir -p $(OUT)
	$(PYTHON) -I tools/golden_to_memh.py $(R05)/protocol/reference/golden_vectors.json $(OUT)

sim: $(OUT)/golden_frames.svh
	$(IVERILOG) -g2012 -I $(OUT) -s tb_top -o $(OUT)/tb_top.vvp -Ptb_top.GOLD_DIR='"$(OUT)"' $(TB) $(RTL)
	$(VVP) -n $(OUT)/tb_top.vvp > $(OUT)/sim_top.log 2>&1; rc=$$?; grep -E '^(TEST|INFO|SUMMARY|TB_ERROR|MODEL_VIOLATION|TOP_TB)' $(OUT)/sim_top.log; \
	  test $$rc -eq 0 && grep -q '^TOP_TB_PASS$$' $(OUT)/sim_top.log

lint:
	mkdir -p $(OUT)
	$(VERILATOR) --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM \
	  --top-module arc1_t35_top $(RTL) > $(OUT)/lint_top.log 2>&1; rc=$$?; cat $(OUT)/lint_top.log; exit $$rc

synth-efx:
	mkdir -p $(OUT)
	$(YOSYS) -q -l $(OUT)/synth_top_efx.log -p 'read_verilog -sv $(RTL); synth_efinix -top arc1_t35_top; stat' > /dev/null
	grep -E 'EFX_|Number of cells' $(OUT)/synth_top_efx.log | tail -8

clean:
	rm -rf $(OUT)
