# ARC-1 Compact R07 PSRAM scenarios against the UNCHANGED R06 controller RTL.
IVERILOG ?= iverilog
VVP      ?= vvp
OUT      ?= build
R06PS    ?= ../../../R06_WORK/fpga/psram
RTL       = $(R06PS)/rtl/psram_user_port.sv $(R06PS)/rtl/psram_qspi_core.sv
.PHONY: all r07 extra-clocks clean
all: r07 extra-clocks
$(OUT):
	mkdir -p $(OUT)
r07: | $(OUT)
	$(IVERILOG) -g2012 -s tb_psram_r07 -o $(OUT)/tb_r07.vvp tb_psram_r07.sv aps6404l_model_r07.sv $(RTL)
	$(VVP) -n $(OUT)/tb_r07.vvp > $(OUT)/sim_r07.log 2>&1; rc=$$?; grep -E '^(TEST|INFO|SUMMARY|TB_ERROR|PSRAM_R07)' $(OUT)/sim_r07.log; \
	  test $$rc -eq 0 && grep -q '^PSRAM_R07_TB_PASS$$' $(OUT)/sim_r07.log
# Clock-ratio variation: the full R06 bench at two additional, non-integer ratios.
#  C4: mclk 66.666 MHz (SCLK 33.3 MHz), uclk 27 MHz.  C5: mclk 100 MHz, CLK_DIV 3 (SCLK 16.7 MHz), uclk 75 MHz.
extra-clocks: | $(OUT)
	$(IVERILOG) -g2012 -s tb_psram -o $(OUT)/c4.vvp -Ptb_psram.MCLK_HZ=66666667 -Ptb_psram.CLK_DIV=1 \
	  -Ptb_psram.UCLK_PS=37037 -Ptb_psram.SEED=23 -Ptb_psram.N_RANDOM=120 -Ptb_psram.CFG='"C4"' \
	  $(R06PS)/tb/tb_psram.sv $(R06PS)/tb/aps6404l_model.sv $(RTL)
	$(IVERILOG) -g2012 -s tb_psram -o $(OUT)/c5.vvp -Ptb_psram.MCLK_HZ=100000000 -Ptb_psram.CLK_DIV=3 \
	  -Ptb_psram.UCLK_PS=13333 -Ptb_psram.SEED=29 -Ptb_psram.N_RANDOM=120 -Ptb_psram.CFG='"C5"' \
	  $(R06PS)/tb/tb_psram.sv $(R06PS)/tb/aps6404l_model.sv $(RTL)
	$(VVP) -n $(OUT)/c4.vvp > $(OUT)/sim_C4.log 2>&1; $(VVP) -n $(OUT)/c5.vvp > $(OUT)/sim_C5.log 2>&1; \
	  grep -h -E '^(SUMMARY|PSRAM_TB|TB_ERROR|MODEL_VIOLATION|psram_qspi_core)' $(OUT)/sim_C4.log $(OUT)/sim_C5.log; \
	  grep -q '^PSRAM_TB_PASS cfg=C4$$' $(OUT)/sim_C4.log && grep -q '^PSRAM_TB_PASS cfg=C5$$' $(OUT)/sim_C5.log
clean:
	rm -rf $(OUT)
