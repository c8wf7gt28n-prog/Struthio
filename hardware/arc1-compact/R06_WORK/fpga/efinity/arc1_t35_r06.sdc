# ARC-1 Compact R06 -- T35F400C3 timing constraints (DRAFT, NATIVE_EDA_NOT_RUN).
# Clock names must match the PLL output names created in the Interface Designer.
# Board delays below are PLACEHOLDER budgets, not extracted from any layout.

create_clock -period 12.500 -name sys_clk    [get_ports {sys_clk}]     ;# 80 MHz (PLL)
create_clock -period 25.000 -name psram_mclk [get_ports {psram_mclk}]  ;# 40 MHz (PLL) -> SCLK 20 MHz

# The two PLL clocks are related, but the RTL crosses only through the
# buffer-ownership handshake in psram_user_port (2-FF synchronisers on the
# toggles; multi-bit data is stable while owned). Treat as asynchronous.
set_clock_groups -asynchronous -group {sys_clk} -group {psram_mclk}

# ---- PSRAM (BANK1C), launched/captured by psram_mclk ----
# SCLK and SIO are both driven from psram_mclk registers. SIO changes on SCLK
# falling edges and read data is captured at the psram_mclk edge that raises
# SCLK, half an SCLK period after the PSRAM launched it (tACLK <= 5.5 ns).
# Budget: board trace 1.0 ns each way (PLACEHOLDER).
set_output_delay -clock psram_mclk -max  3.0 [get_ports {psram_sio_OUT[*] psram_sio_OE[*] psram_ce_n}]
set_output_delay -clock psram_mclk -min -2.0 [get_ports {psram_sio_OUT[*] psram_sio_OE[*] psram_ce_n}]
set_input_delay  -clock psram_mclk -max  7.5 [get_ports {psram_sio_IN[*]}]   ;# tACLK 5.5 + 2 x 1.0 board
set_input_delay  -clock psram_mclk -min  3.5 [get_ports {psram_sio_IN[*]}]   ;# tACLK min 2.0 + 1.5 hold

# ---- F133 SPI0 mailbox (BANK1D) ----
# SCK/SS_N/MOSI are oversampled by sys_clk through 2-FF synchronisers: no
# source-synchronous timing exists; cut the input paths. MISO is launched by
# sys_clk after a detected SCK rise (>= 2 sys clocks of hold at the F133).
set_false_path -from [get_ports {t35_sck_IN t35_ss_n_IN t35_mosi_IN}]
set_false_path -to   [get_ports {t35_miso_OUT t35_miso_OE t35_irq_n_OUT t35_irq_n_OE t35_led0 t35_dbg_tx}]
