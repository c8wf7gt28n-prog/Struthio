# ARC-1 R10 -- ECP5-45F graphics FPGA, step 1 (R10 7.1 items 2-3): flat triangle tile rasterizer core.
# Host transport: D213 GMAC0 RGMII (decision D1, DECISIONS.md) -> r10_raster_top = R8.5-C RGMII endpoint (from
# ../fpga12/rtl, unchanged) + r10_raster_engine (RJOB/RRES frames). PBUS slave not built (pad conflict, gate report).
# Evidence: HOST_TESTED (C model) + RTL_SIMULATED (bit-exact) + OPEN_TOOLCHAIN_ROUTED (pin-locked CABGA381).
OUT ?= build
.PHONY: all ref sim sim45 seeds build45 seeds45 clean
all: ref sim seeds sim45 seeds45
$(OUT)/raster_ref: tools/raster_ref.c
	mkdir -p $(OUT)
	cc -std=c11 -O2 -Wall -Wextra -Werror -o $@ $< -lm
ref: $(OUT)/raster_ref
	mkdir -p $(OUT)/vec
	$(abspath $(OUT))/raster_ref $(OUT)/vec | tee $(OUT)/raster_ref.log; grep -q RASTER_REF_PASS $(OUT)/raster_ref.log
sim: ref
	iverilog -g2012 -s tb_r10_raster -Ptb_r10_raster.VEC='"$(OUT)/vec"' -o $(OUT)/tb_raster.vvp tb/tb_r10_raster.sv rtl/r10_raster.sv
	vvp -n $(OUT)/tb_raster.vvp > $(OUT)/sim_raster.log 2>&1; rc=$$?; grep -E '^(INFO|TB_ERROR|R10_RASTER)' $(OUT)/sim_raster.log; \
	  test $$rc -eq 0 && grep -q '^R10_RASTER_TB_PASS$$' $(OUT)/sim_raster.log
$(OUT)/raster.json: rtl/r10_raster.sv
	mkdir -p $(OUT)
	yosys -q -l $(OUT)/yosys_raster.log -p 'read_verilog -sv rtl/r10_raster.sv; synth_ecp5 -abc9 -top r10_raster -json $@; stat' > /dev/null
seeds: $(OUT)/raster.json
	printf 'FREQUENCY PORT "clk" 80.000000 MHZ ;\n' > $(OUT)/core_80.lpf
	for s in 1 2 3 4 5; do nextpnr-ecp5 --45k --package CABGA381 --speed 6 --json $< --lpf $(OUT)/core_80.lpf \
	  --lpf-allow-unconstrained --seed $$s --log $(OUT)/pnr_raster_$$s.log > /dev/null 2>&1; \
	  echo "seed $$s: $$(grep 'Max frequency' $(OUT)/pnr_raster_$$s.log | tail -1 | sed 's/.*: //')"; done | tee $(OUT)/seeds.log
	grep -E "TRELLIS_COMB|DP16KD|MULT18X18D" $(OUT)/pnr_raster_1.log | head -3 | tee -a $(OUT)/seeds.log
	! grep -q FAIL $(OUT)/seeds.log
F12 := ../fpga12
TOPRTL := rtl/r10_raster_top.sv rtl/r10_raster_engine.sv rtl/r10_raster.sv $(F12)/rtl/eth_link.sv \
  $(F12)/rtl/eth_tx_pump.sv $(F12)/rtl/rgmii_rx.sv $(F12)/rtl/rgmii_tx.sv
sim45: ref
	iverilog -g2012 -s tb_r10_45f -Ptb_r10_45f.VEC='"$(OUT)/vec"' -o $(OUT)/tb_45f.vvp tb/tb_r10_45f.sv $(TOPRTL) \
	  $(F12)/sim/arc1_ecp5_pll_sim.v $(F12)/sim/arc1_eth_pll_sim.v $(F12)/sim/ecp5_ddr_sim.v
	vvp -n $(OUT)/tb_45f.vvp > $(OUT)/sim_45f.log 2>&1; rc=$$?; grep -E '^(INFO|TEST|TB_ERROR|R10_45F)' $(OUT)/sim_45f.log; \
	  test $$rc -eq 0 && grep -q '^R10_45F_TB_PASS$$' $(OUT)/sim_45f.log
$(OUT)/r10_45f.json: $(TOPRTL)
	mkdir -p $(OUT)
	yosys -q -l $(OUT)/yosys_45f.log -p 'read_verilog -sv $(TOPRTL) $(F12)/rtl/arc1_ecp5_pll.v $(F12)/rtl/arc1_eth_pll.v; synth_ecp5 -abc9 -top r10_raster_top -json $@; stat' > /dev/null
build45: $(OUT)/r10_45f.json
seeds45: $(OUT)/r10_45f.json
	for s in 1 2 3 4 5; do nextpnr-ecp5 --45k --package CABGA381 --speed 6 --json $< --lpf constraints/r10_45f.lpf \
	  --seed $$s --report $(OUT)/pnr_45f_$$s.json --log $(OUT)/pnr_45f_$$s.log > /dev/null 2>&1 || echo "seed $$s: PNR_FAIL"; \
	  grep -E "Max frequency for clock" $(OUT)/pnr_45f_$$s.log | tail -3 | sed "s/^/seed $$s: /"; done | tee $(OUT)/seeds_45f.log
	grep -E "TRELLIS_COMB|DP16KD|MULT18X18D|EHXPLLL" $(OUT)/pnr_45f_1.log | head -4 | tee -a $(OUT)/seeds_45f.log
	! grep -qE "FAIL" $(OUT)/seeds_45f.log
clean:
	rm -rf $(OUT)
