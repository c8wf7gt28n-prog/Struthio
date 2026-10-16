# ARC-1 R10 -- LFE5U-12F support FPGA: lint, RGMII unit TB, system TB, open-toolchain P&R on the 12F die.
# TQFP144 is not in Project Trellis: P&R uses timing/r10_12f_proxy256.lpf (same PIO sites via caBGA256 balls).
# Evidence: RTL_SIMULATED + OPEN_TOOLCHAIN_ROUTED (proxy package). Not on silicon.
OUT  ?= build
SEED ?= 1
R85C ?= ../../R85C_WORK
RTL  = rtl/accel_engine.sv rtl/accel_fir.sv rtl/arc1_transform_ecp5.sv rtl/eth_link.sv rtl/eth_tx_pump.sv \
       rtl/rgmii_rx.sv rtl/rgmii_tx.sv rtl/r10_support_top.sv
SIMM = sim/arc1_ecp5_pll_sim.v sim/arc1_eth_pll_sim.v sim/ecp5_ddr_sim.v
SYNM = rtl/arc1_ecp5_pll.v rtl/arc1_eth_pll.v
LPF  = timing/r10_12f_proxy256.lpf
.PHONY: all lint rgmii vectors sim build seeds report clean lint_mem sim_mem build_mem seeds_mem
all: lint rgmii sim build seeds report lint_mem sim_mem seeds_mem

lint:
	mkdir -p $(OUT)
	verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-TIMESCALEMOD --timing \
	  --top-module r10_support_top $(RTL) $(SIMM) > $(OUT)/lint.log 2>&1; rc=$$?; cat $(OUT)/lint.log; exit $$rc

rgmii:
	mkdir -p $(OUT)
	iverilog -g2012 -s tb_rgmii -o $(OUT)/tb_rgmii.vvp tb/tb_rgmii.sv rtl/rgmii_rx.sv rtl/rgmii_tx.sv rtl/eth_tx_pump.sv sim/ecp5_ddr_sim.v
	vvp -n $(OUT)/tb_rgmii.vvp > $(OUT)/sim_rgmii.log 2>&1; rc=$$?; tail -2 $(OUT)/sim_rgmii.log; \
	  test $$rc -eq 0 && grep -q '^RGMII_TB_PASS$$' $(OUT)/sim_rgmii.log

# AJOB reference vectors from the R8.5-C C driver/reference (firmware/tools/ajob_vectors.c)
vectors:
	$(MAKE) -C $(R85C)/fpga_ecp5 build/ajob/ajob_cases.svh > /dev/null
	mkdir -p $(OUT)/ajob && cp $(R85C)/fpga_ecp5/build/ajob/ajob_cases.svh $(R85C)/fpga_ecp5/build/ajob/ajob_*_req.memh \
	  $(R85C)/fpga_ecp5/build/ajob/ajob_*_resp.memh $(OUT)/ajob/

sim: vectors
	iverilog -g2012 -I $(OUT)/ajob -s tb_r10_support -o $(OUT)/tb_r10.vvp -Ptb_r10_support.AJOB_DIR='"$(OUT)/ajob"' \
	  tb/tb_r10_support.sv $(RTL) $(SIMM)
	vvp -n $(OUT)/tb_r10.vvp > $(OUT)/sim_r10.log 2>&1; rc=$$?; grep -E '^(TEST|INFO|TB_ERROR|R10_12F)' $(OUT)/sim_r10.log; \
	  test $$rc -eq 0 && grep -q '^R10_12F_TB_PASS$$' $(OUT)/sim_r10.log

$(OUT)/r10_12f.json: $(RTL) $(SYNM)
	mkdir -p $(OUT)
	yosys -q -l $(OUT)/yosys.log -p 'read_verilog -sv $(RTL) $(SYNM); synth_ecp5 -top r10_support_top -json $@; stat' > /dev/null

build: $(OUT)/r10_12f.json
	for sp in 6 7; do nextpnr-ecp5 --12k --package CABGA256 --speed $$sp --json $< --lpf $(LPF) --seed $(SEED) \
	  --textcfg $(OUT)/r10_12f_s$$sp.config --report $(OUT)/nextpnr_s$$sp.json --log $(OUT)/nextpnr_s$$sp.log > /dev/null 2>&1 \
	  || { echo "P&R FAIL speed $$sp"; exit 1; }; done
	ecppack --compress --input $(OUT)/r10_12f_s7.config --bit $(OUT)/r10_12f_s7.bit
	sha256sum $(OUT)/r10_12f_s7.bit > $(OUT)/r10_12f_s7.bit.sha256

seeds: $(OUT)/r10_12f.json
	for sp in 6 7; do for s in 1 2 3 4 5; do nextpnr-ecp5 --12k --package CABGA256 --speed $$sp --json $< --lpf $(LPF) \
	  --seed $$s --log $(OUT)/seed_s$${sp}_$$s.log > /dev/null 2>&1; done; done; true

report:
	python3 -I timing/r10_12f_report.py $(OUT) timing/R10_12F_FIT_TIMING.md timing/R10_12F_FIT_TIMING.json

# ---- memory variant (ARC1_MEMORY_R10 s2.4): 4 MiB QSPI PSRAM; pins from hardware/gen_flash_pinmux.py ----
RTLM = $(filter-out rtl/r10_support_top.sv,$(RTL)) rtl/r10_support_mem_top.sv rtl/r10_mem_engine.sv \
       rtl/psram_user_port.sv rtl/psram_qspi_core.sv rtl/psram_bist.sv
LPFM = $(OUT)/r10_12f_mem_proxy256.lpf
lint_mem:
	mkdir -p $(OUT)
	verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-TIMESCALEMOD --timing \
	  --top-module r10_support_mem_top $(RTLM) $(SIMM) > $(OUT)/lint_mem.log 2>&1; rc=$$?; cat $(OUT)/lint_mem.log; exit $$rc
sim_mem: vectors
	iverilog -g2012 -I $(OUT)/ajob -s tb_r10_support_mem -o $(OUT)/tb_r10_mem.vvp -Ptb_r10_support_mem.AJOB_DIR='"$(OUT)/ajob"' \
	  tb/tb_r10_support_mem.sv $(RTLM) $(SIMM) sim/aps6404l_model_r07.sv
	vvp -n $(OUT)/tb_r10_mem.vvp > $(OUT)/sim_r10_mem.log 2>&1; rc=$$?; grep -E '^(TEST|INFO|TB_ERROR|MODEL_VIOLATION|R10_12F)' $(OUT)/sim_r10_mem.log; \
	  test $$rc -eq 0 && grep -q '^R10_12F_MEM_TB_PASS$$' $(OUT)/sim_r10_mem.log
$(LPFM): $(LPF) ../hardware/lpf/r10_12f_mem_proxy256.lpf
	mkdir -p $(OUT)
	cat $^ > $@
$(OUT)/r10_12f_mem.json: $(RTLM) $(SYNM)
	mkdir -p $(OUT)
	yosys -q -l $(OUT)/yosys_mem.log -p 'read_verilog -sv $(RTLM) $(SYNM); synth_ecp5 -abc9 -top r10_support_mem_top -json $@; stat' > /dev/null
build_mem: $(OUT)/r10_12f_mem.json $(LPFM)
seeds_mem: $(OUT)/r10_12f_mem.json $(LPFM)
	for sp in 6 7; do for s in 1 2 3 4 5; do nextpnr-ecp5 --12k --package CABGA256 --speed $$sp --json $< --lpf $(LPFM) \
	  --seed $$s --log $(OUT)/mem_seed_s$${sp}_$$s.log > /dev/null 2>&1 || echo "speed $$sp seed $$s: PNR_FAIL"; \
	  grep -E "Max frequency for clock" $(OUT)/mem_seed_s$${sp}_$$s.log | tail -4 | sed "s/^/speed $$sp seed $$s: /"; done; done | tee $(OUT)/seeds_mem.log
	grep -E "TRELLIS_COMB|DP16KD|MULT18X18D|EHXPLLL" $(OUT)/mem_seed_s6_1.log | head -4 | tee -a $(OUT)/seeds_mem.log
	! grep -qE "FAIL" $(OUT)/seeds_mem.log
clean:
	rm -rf $(OUT)
