# ARC-1 Compact R06 PSRAM controller: RTL simulation, lint, generic synthesis.
# Evidence produced here is RTL_SIMULATED / generic-synthesis only, never
# NATIVE_EDA_VERIFIED (that requires Efinity for T35F400C3).
IVERILOG ?= iverilog
VVP      ?= vvp
VERILATOR?= verilator
YOSYS    ?= yosys
OUT      ?= build

RTL   = rtl/psram_user_port.sv rtl/psram_qspi_core.sv
TB    = tb/tb_psram.sv tb/aps6404l_model.sv

# name : MCLK_HZ CLK_DIV UCLK_PS TCEM_NS SEED
#  C1: SCLK 20 MHz, user clock 50 MHz (faster than mclk)
#  C2: SCLK 40 MHz, user clock 33.3 MHz (slower than mclk)
#  C3: SCLK 12.5 MHz, user clock 100 MHz, extended-grade tCEM 3 us
CFG_C1 = 40000000 1 20000 8000 1
CFG_C2 = 80000000 1 30000 8000 7
CFG_C3 = 50000000 2 10000 3000 11

CONFIGS = C1 C2 C3
.PHONY: all sim lint synth synth-efx clean $(addprefix sim-,$(CONFIGS)) mutants
all: lint sim synth synth-efx mutants

$(OUT):
	mkdir -p $(OUT)

define SIMRULE
sim-$(1): | $(OUT)
	$(IVERILOG) -g2012 -DPSRAM_CORE_EXPOSE_PARAMS -s tb_psram -o $(OUT)/tb_$(1).vvp \
	  -Ptb_psram.MCLK_HZ=$(word 1,$(CFG_$(1))) -Ptb_psram.CLK_DIV=$(word 2,$(CFG_$(1))) \
	  -Ptb_psram.UCLK_PS=$(word 3,$(CFG_$(1))) -Ptb_psram.TCEM_NS=$(word 4,$(CFG_$(1))) \
	  -Ptb_psram.SEED=$(word 5,$(CFG_$(1))) -Ptb_psram.CFG='"$(1)"' $(TB) $(RTL)
	$(VVP) -n $(OUT)/tb_$(1).vvp > $(OUT)/sim_$(1).log 2>&1; rc=$$$$?; tail -3 $(OUT)/sim_$(1).log; \
	  test $$$$rc -eq 0 && grep -q '^PSRAM_TB_PASS cfg=$(1)$$$$' $(OUT)/sim_$(1).log && \
	  ! grep -q 'TB_ERROR\|MODEL_VIOLATION' $(OUT)/sim_$(1).log
endef
$(foreach c,$(CONFIGS),$(eval $(call SIMRULE,$(c))))

sim: $(addprefix sim-,$(CONFIGS))

lint: | $(OUT)
	$(VERILATOR) --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM \
	  --top-module psram_user_port $(RTL) > $(OUT)/lint.log 2>&1; rc=$$?; cat $(OUT)/lint.log; exit $$rc

# Technology-independent Yosys synthesis: proves the RTL is synthesizable
# and gives a generic cell count. NOT a T35 fit, NOT timing.
synth: | $(OUT)
	$(YOSYS) -q -l $(OUT)/synth.log -p 'read_verilog -sv $(RTL); chparam -set MCLK_HZ 40000000 -set CLK_DIV 1 psram_user_port; synth -top psram_user_port -flatten; stat' > /dev/null
	grep -A40 'Printing statistics' $(OUT)/synth.log | head -60

# Open-source Yosys `synth_efinix` mapping to Trion-style primitives
# (EFX_LUT4/EFX_FF/EFX_RAM_5K). A resource ESTIMATE only: not Efinity, no
# placement, no timing, no IO. Label: OPEN_SOURCE_SYNTH_ESTIMATE.
synth-efx: | $(OUT)
	$(YOSYS) -q -l $(OUT)/synth_efx.log -p 'read_verilog -sv $(RTL); chparam -set MCLK_HZ 40000000 -set CLK_DIV 1 psram_user_port; synth_efinix -top psram_user_port; stat' > /dev/null
	grep -E 'EFX_|Number of cells' $(OUT)/synth_efx.log | tail -6

# Mutation checks: each deliberately broken controller must FAIL the bench.
MUTANTS = MUTANT_NO_PAGE_SPLIT MUTANT_NO_TURNAROUND MUTANT_SKIP_RESET MUTANT_SAMPLE_EARLY
mutants: | $(OUT)
	@for m in $(MUTANTS); do \
	  $(IVERILOG) -g2012 -D$$m -s tb_psram -o $(OUT)/mut_$$m.vvp -Ptb_psram.N_RANDOM=20 \
	    -Ptb_psram.CFG='"'$$m'"' $(TB) $(RTL) || exit 1; \
	  timeout 600 $(VVP) -n $(OUT)/mut_$$m.vvp > $(OUT)/mut_$$m.log 2>&1; \
	  if grep -q '^PSRAM_TB_PASS' $(OUT)/mut_$$m.log; then echo "MUTANT_SURVIVED $$m"; exit 1; \
	  else echo "MUTANT_KILLED $$m"; fi; \
	done

clean:
	rm -rf $(OUT)
