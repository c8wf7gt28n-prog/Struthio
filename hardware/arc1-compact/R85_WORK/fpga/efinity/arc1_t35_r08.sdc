# ARC-1 Compact R08 -- T35F400C3 timing constraints (GENERATED, NATIVE_EDA_NOT_RUN).
# PLL output clocks are named without get_ports, as the Interface Designer writes them
# (sources/efinix/efinity_project_format.md s.3.5 item 7). Board delays are PLACEHOLDER budgets.
create_clock -period 40.000 -name osc_25m [get_ports {osc_25m}]
create_clock -period 12.500 sys_clk
create_clock -period 25.000 psram_mclk
# Crossings go only through 2-FF toggle/level synchronisers (psram_user_port, guard_on sync).
set_clock_groups -asynchronous -group {sys_clk} -group {psram_mclk}

# PSRAM (BANK1C): launched/captured by psram_mclk; SCLK 20 MHz (CLK_DIV=1). Board 1.0 ns each way (PLACEHOLDER).
set_output_delay -clock psram_mclk -max  3.0 [get_ports {psram_sio_OUT[*] psram_sio_OE[*] psram_ce_n_OUT psram_ce_n_OE psram_sclk}]
set_output_delay -clock psram_mclk -min -2.0 [get_ports {psram_sio_OUT[*] psram_sio_OE[*] psram_ce_n_OUT psram_ce_n_OE psram_sclk}]
set_input_delay  -clock psram_mclk -max  7.5 [get_ports {psram_sio_IN[*]}]
set_input_delay  -clock psram_mclk -min  3.5 [get_ports {psram_sio_IN[*]}]
# PG / EN are asynchronous and synchronised in psram_power_guard.
set_false_path -from [get_ports {psram_pg_IN psram_pwr_en_IN psram_ce_n_IN}]

# F133 SPI0 mailbox (BANK1D) through the R08 isolation buffers: oversampled by sys_clk.
set_false_path -from [get_ports {t35_sck_IN t35_ss_n_IN t35_mosi_IN t35_miso_IN t35_irq_n_IN t35_dbg_rx}]
set_false_path -to   [get_ports {t35_miso_OUT t35_miso_OE t35_irq_n_OUT t35_irq_n_OE t35_led0 t35_dbg_tx}]
