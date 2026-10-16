# ARC-1 R10 -- ECP5-45F graphics FPGA, step 1 (R10 7.1 items 2-3): flat triangle tile rasterizer core.
# Host transport (PBUS slave vs RGMII) is NOT built yet: owner decision pending (qa/R10_gate_report.md, D213
# PBUS/display pad conflict). The core is transport-independent (16-bit word stream in/out).
# Evidence: HOST_TESTED (C model) + RTL_SIMULATED (bit-exact) + OPEN_TOOLCHAIN_ROUTED (core, unconstrained pins).
OUT ?= build
.PHONY: all ref sim build seeds clean
all: ref sim seeds
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
clean:
	rm -rf $(OUT)
