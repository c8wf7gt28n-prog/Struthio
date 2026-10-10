# SLIM4 firmware review: R11 + af0771a (USB console), against ESP-IDF v6.1

Reviewed: `firmware/slim4` at commit **af0771a** (R11 commit 8058008 plus the USB bring-up console). Line numbers are af0771a's.
IDF: `~/esp/esp-idf` (v6.1, fff9895c), managed `espressif/esp_lcd_ili9881c` 1.1.0. No file under /home/user/Struthio was modified.
A snapshot of 8058008 is in `scratchpad/review/fwcopy`. Stack-usage output (`-fstack-usage`, the build's own flags) is in `scratchpad/review/su`. The truncation probe is in `scratchpad/review/trunc`. The LEDC divider check is `scratchpad/review/ledc.c`.

## Summary (10 lines)

1. **CRITICAL: the display can never come up.** LEDC at 20 kHz with 12-bit resolution would need an 81.92 MHz source clock. The P4's fastest LEDC clock is PLL_F80M, so `ledc_timer_config` returns ESP_FAIL and `init_display` stops at "backlight PWM", before the DSI bus is created. The firmware then reports a false `PANEL FAIL "NOT PROBED - DSI SETUP FAILED"`.
2. **CRITICAL: false PANEL FAIL on a good panel.** The firmware expects ID 98 81 **0C**. ESP-IDF's own MIPI-DSI example log shows an ILI9881C answering `ID1: 0x98, ID2: 0x81, ID3: 0x5c`.
3. **CRITICAL: boot hang on a board fault.** `esp_lcd_new_dsi_bus` waits for PLL lock and lane stop-state with no time limit, which an open VDDO_MIPI_2V5 joint (U1 pad 41/73) can cause. The hang is silent: no task-watchdog reset, and the GPIO self-test results have not been printed yet because they are logged only after `slim4_platform_init()`.
4. MAJOR: SHORTS reports PASS even when few or no pad pairs could be tested (shown here: "NO SHORTS - 0 OF 19 PAD PAIRS" = PASS).
5. MAJOR: the BQ_EN2 "opposite pull" step puts EN2 at about 0.6 V for 1 ms (10 k down against 45 k up). The BQ24074 only guarantees a low below 0.4 V, and EN1 is high at that moment, so the charger can read USB-suspend. On USB-only power (the documented first power-up) that is a brownout or boot loop.
6. MAJOR (console, af0771a): the console task draws to the shared framebuffer and DMA2D semaphore while the main loop renders. The only guard is a 40 ms sleep. A collision can permanently kill the diagnostic display or freeze a wrong image on screen.
7. The GPIO sequencing cannot damage hardware: 5 mA drive (`fun_drv=0`), never against a held net, EN1/EN2 never driven. LP-pad handling after an EXT1 wake and the drive-strength restore are correct per the IDF source.
8. The DSI probe matches `mipi_dsi_hal.c`'s sequences. It uses the same status bits as IDF, every wait is bounded, and on success it leaves the host as IDF's own read leaves it. Reading INT_ST0/1 to clear them follows the DWC convention, but the IDF headers mark them only "RO" (see UNSURE).
9. Stacks are fine (largest own frame is the audio worker at 1216 B; main-task chains are well under 3584 B with picolibc). Static RAM is about 30 KB. PSRAM cache coherency is handled by the DMA2D backend.
10. Fix order for first boot: LEDC (1 line), ID3 (1 line), a bounded or isolated DSI bring-up plus an early self-test log, EN2's opposite step, SHORTS coverage, and a display mutex for the console.

---

## Findings

### F1. CRITICAL: backlight LEDC timer cannot be configured, so the display bring-up always aborts
- **Where:** `components/slim4_bsp/slim4_board.c:483-489` (`LEDC_TIMER_12_BIT`, `freq_hz = 20000`, `LEDC_AUTO_CLK`), called at `:800` *before* `esp_lcd_new_dsi_bus` (`:807`).
- **IDF evidence:** `soc/esp32p4/include/soc/clk_tree_defs.h:721` gives `#define SOC_LEDC_CLKS {SOC_MOD_CLK_XTAL, SOC_MOD_CLK_PLL_F80M, SOC_MOD_CLK_RC_FAST}`. In `esp_driver_ledc/src/ledc.c:486` the divider is `(((uint64_t) src_clk_freq << LEDC_LL_FRACTIONAL_BITS) + freq_hz * precision / 2) / (freq_hz * precision)`, and `:103` defines `#define LEDC_IS_DIV_INVALID(div) ((div) <= LEDC_LL_FRACTIONAL_MAX || ...)` with `LEDC_LL_FRACTIONAL_MAX = 255`. On failure `:657` jumps to error and `:737` logs "requested frequency %d and duty resolution %d can not be achieved" and returns `ESP_FAIL`.
- **Computed (scratchpad/review/ledc.c):** at 12 bits and 20 kHz, div_param is 250 (80 MHz), 125 (40 MHz) and about 55–63 (RC_FAST). All are invalid. 11-bit on 80 MHz gives 500 (valid); 10-bit gives 1000 (80 MHz) or 500 (40 MHz) (valid).
- **Failure:** every board logs `display failed at backlight PWM: ESP_FAIL`. The screen stays dark. The self-test shows a false `PANEL FAIL NOT PROBED - DSI SETUP FAILED ... at: backlight PWM`, and there is no VIDEO line. `platform_self_test` then sees no surface, giving SERVICE MODE, and any OTA image in PENDING_VERIFY is **rolled back** (`app_main.c:113-129`). The console's `bl` and `pattern` commands answer "display not ready".
- **Fix:** use `LEDC_TIMER_11_BIT` and `SLIM4_BL_DUTY_MAX ((1u<<11)-1)`, or 12-bit at ≤19.5 kHz. Pin `.clk_cfg = LEDC_USE_PLL_DIV_CLK`. Also make a backlight failure non-fatal for the panel bring-up: initialise the backlight after the panel and log it as its own stage.

### F2. CRITICAL (false FAIL): the panel ID check demands ID3 = 0x0C
- **Where:** `include/slim4_selftest.h:155` (`SLIM4_ST_PANEL_ID2 0x0C`) and `slim4_selftest_logic.c:467-475`.
- **IDF evidence:** `examples/peripherals/lcd/mipi_dsi/README.md:73` shows `I (1639) ili9881c: ID1: 0x98, ID2: 0x81, ID3: 0x5c`. That is the same `esp_lcd_ili9881c` driver reading the same page-1 registers 0x00–0x02 that the probe reads.
- **Failure:** a correctly working CFAF panel that reports 98 81 5C (or any vendor-programmed ID3) gets `PANEL FAIL "ID 98 81 5C"` "a different panel or controller". The board is good, and the owner chases a non-fault on the first boards.
- **Fix:** PASS on `id[0]==0x98 && id[1]==0x81` and report ID3 in the text. Or accept {0x0C, 0x5C} and make any other ID3 an INFO line. Confirm the CFAF's ID3 on board 1 and then tighten the check.

### F3. CRITICAL (boot hang): the DSI bus bring-up has unbounded waits that a board fault can trigger, and the self-test log is lost
- **Where:** `slim4_board.c:807` → IDF `esp_lcd/dsi/esp_lcd_mipi_dsi_bus.c:101-106`:
  ```c
  while (!mipi_dsi_phy_ll_is_pll_locked(hal->host)) { vTaskDelay(pdMS_TO_TICKS(1)); }
  while (!mipi_dsi_phy_ll_are_lanes_stopped(hal->host, num_data_lanes)) { vTaskDelay(pdMS_TO_TICKS(1)); }
  ```
  Also `app_main.c:144-157`: GPIO results are printed (`slim4_selftest_log`) only after `slim4_platform_init()` returns.
- **Failure:** the D-PHY PLL is supplied from LDO VO3 through the board net VDDO_MIPI_2V5 (U1 pads 41 and 73, C107/C108/C109/C122). An open joint, missing decoupling or wrong LDO channel can stop the PLL locking or the lanes reaching stop state. The loop yields, so IDLE runs, no task watchdog fires (`app_main` is not subscribed, and `CONFIG_ESP_TASK_WDT_PANIC` is not set), and nothing resets. The board sits forever after `gameplay inputs ready ...` with:
  - a dark screen;
  - no `SELFTEST` lines, even though the GPIO checks already ran;
  - no power-off (the button is polled only in the main loop);
  - no console (`slim4_console_start` is called only at `app_main.c:176`).

  The same applies to the HAL's `while (mipi_dsi_host_ll_gen_is_cmd_fifo_full(...))` busy loops if the panel stops acknowledging partway through `esp_lcd_panel_init` after a successful probe (an intermittent FPC). Those are CPU-busy, and the TWDT only prints.
- **Fix (in order of value):**
  1. Call `slim4_selftest_log()` immediately after `slim4_selftest_pins()` (and again in full later).
  2. Start the console before `slim4_platform_init()`.
  3. Log every `s_display_stage` change as it happens (one `ESP_LOGI` per stage) so the last line printed names the hanging call.
  4. Run `init_display()` in its own task (core 1, priority 1). The main task waits up to about 3 s on a semaphore. On timeout it records `stopped_at = s_display_stage` ("two-lane DSI bus: PLL did not lock - check VDDO_MIPI_2V5, U1 pads 41/73") and continues the boot. Never touch the DSI objects again after a timeout.

### F4. MAJOR (false PASS): SHORTS is PASS whatever the coverage
- **Where:** `slim4_selftest_logic.c:327-338`.
- **Shown:** with every victim baseline at -1 (nothing testable), the report is `SHORTS PASS "NO SHORTS - 0 OF 19 PAD PAIRS"` (scratchpad/review/trunc/t.c).
- **Failure:** a held control, a status output asserted throughout, or a FLOATING net removes pairs from the scan, and the verdict is still PASS. On the first boards, with USB in (PGOOD and CHG asserted) and maybe a thumb on a flap, some neighbouring pairs go untested while the summary says "no FAIL".
- **Fix:** PASS only when `adj_cov == adj`. Otherwise use INFO "SHORTS PARTIAL - n OF 19 PAD PAIRS" with the untested list, which is already built.

### F5. MAJOR: the BQ_EN2 opposite-pull step drives the charger's mode pin into its undefined input band
- **Where:** `slim4_selftest.c:143-147` runs the "opposite" step for every 10 k net, including BQ_EN1 and BQ_EN2 (`slim4_selftest_logic.c:29,39`, drive_ok=false but the pull check still runs).
- **Mechanism:** EN2 has R604 10 k to GND, and U1's internal pull-up (about 45 k, `IO_MUX fun_wpu`) gives about 3.3 V·10/55 ≈ **0.6 V** for `SETTLE_10K_US` = 1 ms. The BQ24074's EN1/EN2 inputs are specified VIL ≤ 0.4 V and VIH ≥ 1.4 V. EN1 rests high (R603 pull-up), so if U10 reads EN2 as 1, EN2/EN1 = 1/1 = **USB suspend**.
- **Failure:** on the documented first power-up (USB only, no cell), a suspend of even about 1 ms can collapse SYS. That gives a brownout reset at every boot (a boot loop), or at best a `RESET FAIL BROWNOUT` on the next boot. Typical CMOS thresholds will usually read 0.6 V as low, so this is a specification violation rather than a certain failure, but nothing is gained by risking it.
- **Fix:** skip the opposite step for BQ_EN1/BQ_EN2 (or for any pin with `drive_ok == false`). Their same-direction check plus the short scan already find open pads.

### F6. MAJOR (af0771a): the console and the main loop share the framebuffer and the DMA2D completion semaphore without a lock
- **Where:** `main/slim4_console.c:137-139` and `:211-213`, where `s_display_hold = true; vTaskDelay(40 ms)` is followed by `slim4_board_show_pattern` or `slim4_board_show_selftest`. Also `app_main.c:249-262` and `slim4_board.c:224-235` (`panel_draw_bitmap_wait` drains the binary semaphore, then waits 100 ms).
- **Failure:** the main loop tests the hold flag only before it starts a frame. A frame already started (CPU fill of 1.8 MB in PSRAM, DMA2D copy, a wait of up to 100 ms) can still be running when the console task (priority 2) starts drawing. Then:
  - (a) both tasks write `s_framebuffer`, and the copied frame mixes the diagnostic screen with the pattern;
  - (b) both tasks wait on one binary semaphore, one completion is consumed by the wrong task, and the other times out. If that is the main loop, `app_main.c:262-266` sets `display_ready = false` and deletes the frame timer **permanently**, killing the diagnostic screen and the BOOT page until reboot;
  - (c) the last copy to finish wins, so the bench sees a frozen diagnostic frame instead of the requested `checker` pattern. That is a misleading visual verdict for the CLK/D1 lane check.

  The same race exists between console `page`/`pattern` and the BOOT-button page (`app_main.c:229`).
- **Fix:** add a display mutex inside slim4_board around "draw into s_framebuffer, then panel_draw_bitmap_wait". Check the hold flag under that mutex in `slim4_board_render_diagnostic`, and drop the 40 ms sleep.

### F7. MAJOR (debuggability): bootloader and early-boot output is invisible on the board
- **Where:** `sdkconfig.defaults` sets `CONFIG_ESP_CONSOLE_UART_DEFAULT=y` with USJ as secondary only. IDF `bootloader_support/src/bootloader_console.c:49-107`: with `CONFIG_ESP_CONSOLE_UART` the second-stage bootloader initialises UART0 only. UART0 (GPIO37/38) reaches only U1 pads 69/70.
- **Failure:** partition, image, flash or eFuse errors in the bootloader, and the app's earliest startup lines, never reach the USB port. A board that stops before `app_main` looks dead. FIRST_BOOT.md admits the bootloader lines are missing but does not mention this consequence.
- **Fix (bring-up build):** set `CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG=y` as primary. Or add test pads for U0TXD/U0RXD on the next PCB revision and note the 2-pin header in FIRST_BOOT.

### F8. MINOR: "DRIVE" and LINK_ONCE asymmetry
- **Where:** `slim4_selftest_logic.c:296-307`.
- **Failure:** a status output (CHG) that asserts during its own 50 µs drive-high window gives `DRIVE FAIL "NET CANNOT BE DRIVEN HIGH"`. The status-pin exception exists only for links.
- **Fix:** report DRIVE on a STATUS pin as INFO unless it appears in both scans.

### F9. MINOR: GPIO10 output glitch when it is configured as an output
- **Where:** `slim4_board.c:792-795`. `gpio_config(OUTPUT)` runs before `gpio_set_level(1)`, and the self-test's last write to GPIO10's output register was 0 (the drive loop ends at level 0, `slim4_selftest.c:221`).
- **Failure:** LCD_RESX is briefly released, for microseconds, while the panel is powered.
- **Fix:** call `gpio_set_level` first, as `slim4_power_init` does for EN1/EN2.

### F10. MINOR: serial detail strings are truncated, losing diagnostics
- **Where:** `slim4_st_item_t.detail[200]` (`slim4_selftest.h:162`).
- **Measured:**
  - PANEL no-answer: 445 chars. The "host flags: ..." tail never reaches the serial line; the raw values survive only in the `panel probe:` ESP_LOGI.
  - DSI_LANE0 with many flags: 336 chars. The raw `int_st0/int_st1` hex is cut off.
  - SHORTS: 267 chars, losing part of the untested pad-pair list.
  - PWR_WAKE RC_SLOW: 229 chars, losing the readings.
- **Fix:** use `detail[384]` (48 items × 184 B, about 9 KB more static RAM), or put the raw values first in each format.

### F11. MINOR: a single DMA2D timeout permanently disables the diagnostic display
- **Where:** `app_main.c:262-266` and `slim4_board.c:231`.
- **Failure:** the DMA2D ISR is not IRAM-safe, so during a flash erase it can be held off. A W25Q512 sector erase is typically 45 ms and can take up to about 400 ms (NVS commit, coredump, OTA write). A 100 ms timeout then turns the screen off for good.
- **Fix:** allow a few consecutive failures before giving up, and use a 250 ms timeout.

### F12. MINOR: `wait_us()` with vTaskDelay is up to 1 tick short
- **Where:** `slim4_selftest.c:46`. `vTaskDelay(N)` at 1 kHz returns after N-1 to N ms.
- **Effect:** `PRECHARGE_RC_US` (3 ms) can be about 2 ms. That is still ample at 5 mA into 100 nF. Settle times have margin. Use `vTaskDelay(N+1)` if exact minimums matter.

### F13. MINOR: power policy, a full cell on 500 mA USB keeps the 15 % backlight cap and audio mute
- **Where:** `slim4_power.c:154` (`cell_now` requires `charging`).
- **Failure:** after charge termination (CHG high) on a laptop port, the backlight is capped at 15 % and the speakers are muted, even though the BQ24074's battery-supplement mode can carry the load. Testers may conclude the speakers are faulty.
- **Fix:** document this, or qualify the cell by voltage alone once a charge has ended.

### F14. MINOR: NVS init does not erase and retry
- **Where:** `slim4_board.c:902`.
- **Failure:** `ESP_ERR_NVS_NO_FREE_PAGES` or `ESP_ERR_NVS_NEW_VERSION_FOUND` leave saves disabled for good.
- **Fix:** the standard `nvs_flash_erase(); nvs_flash_init();` pattern.

### F15. MINOR: OTA confirmation comes after the 10–12 s self-test page
- **Where:** `app_main.c:169`.
- **Failure:** a reset during the page (for example the RESET button) makes the bootloader roll back a good image. The rollback also runs when only the display is missing (an FPC unplugged on the bench).
- **Fix:** mark the image valid right after `slim4_platform_init()` and the software checks. Make display absence a warning, not a rollback, at least during bring-up.

### F16. MINOR: missing pull resistors on chip-loaded nets are not detectable (false PASS)
- **Where:** BACKLIGHT_PWM (R422) and AUDIO_SD_CTRL (R504) pull checks.
- **Failure:** TPS61165 CTRL has an internal pull-down (about 800 k), and each MAX98357A SD_MODE has an internal 100 k pull-down through R501/R502. If R422 or R504 is missing, the net still returns low within 200 µs, so the result is PASS "PULL-DOWN OK".
- **Fix:** word these lines as "net returns low (R422 or the chip's own pull-down)", or shorten the released-read time for those two nets. Not dangerous: the chips' own pulls do the same job.

### F17. MINOR (af0771a console)
- `slim4_console.c:231-235`: `sleep` calls `slim4_power_off()` from the console task while the main loop keeps rendering and polling. It is benign, but stop the frame timer first or post a request to the main loop.
- `slim4_console.c:252`: the console reads `usb_serial_jtag_read_bytes` directly while `stdin` is also routed to the driver. That is fine as long as nothing else reads stdin; keep it so.
- With the driver installed (`usb_serial_jtag_vfs_use_driver`), ISR-context logs (`ESP_DRAM_LOGE` in the DSI bridge underrun ISR, `esp_rom_printf`) bypass the driver's ring buffer and can interleave with it. That is cosmetic.
- The `tone` and `vol` commands at 100 % play a 12000-amplitude triangle (about −8.7 dBFS) for up to 3 s per side, roughly 0.25 W in 4 Ω at 12 dB gain. That is acceptable, but cap `vol` at about 50 for bring-up if the speakers are small.
- The driver's TX buffer is 256 B, so `report` (about 7 KB) relies on the blocking-once, then drop behaviour (`usb_serial_jtag_vfs.c:740-756`). Lines can be dropped if the host is slow. Use `tx_buffer_size = 2048`.

---

## UNSURE

1. **INT_ST0/INT_ST1 clear on read.** IDF never reads them, and `mipi_dsi_host_struct.h` marks every bit "RO". Synopsys DWC MIPI-DSI (Linux `dw_mipi_dsi_clear_err()` reads INT_ST0/1 to clear them) clears on read. If the P4 does not, the "second exchange" flags include power-up leftovers and DSI_LANE0 can FAIL falsely. Check on board 1: read the registers twice in a row (the console `panel` command shows before/first/after).
2. **Panel error report bits.** `PANEL_REPORT_BITS` (all of int_st0[15:0], including bit 8 "ECC single-bit corrected" and the reserved bit 14) make DSI_LANE0 FAIL. The ILI9881C may set some bits routinely, for example for DCS reads of manufacturer registers. Make these INFO until a known-good baseline exists, and FAIL only on D-PHY bits 16–20 and a missing answer.
3. **PSRAM bandwidth in the diagnostic loop.** Each 60 Hz frame does a 1.8 MB CPU fill, a 1.8 MB DMA2D read+write and a 1.8 MB DPI GDMA read. That is roughly 440 MB/s of hex-PSRAM traffic, which may trigger DSI-bridge underruns (IDF: "can't fetch data from external memory fast enough") and corrupt the picture, which could be read as a lane fault. Count underruns (see the hooks below) and redraw only changed regions.
4. **The probe's first page-select write carries no ACK** (bta_en is still 0, as in IDF's own path). The "page select write" stop reason can therefore only detect an LP transmit failure, not an absent panel. This is consistent with the HAL, but the wording overstates it.
5. **P4 internal pull value.** The WEAK/OK split relies on 45 k. An opposite-pull reading of 2.7 V sits just above VIH(min) = 0.75·VDD = 2.475 V, and a 100 k misfit (1.0 V) is in the undefined band. "All 10 k nets WEAK" on board 1 means the threshold assumption is wrong.
6. **PGOOD during USB suspend.** If PGOOD goes high in suspend, the over-temperature suspend exits on the next 0.5 s poll (`!usb_power`) and oscillates.
7. **DMA2D source alignment.** `s_framebuffer` is allocated without `MALLOC_CAP_DMA` or 64-byte alignment (`slim4_board.c:868`). The DMA2D backend syncs it with `UNALIGNED` (`async_color_convert_dma2d.c`), so coherency is fine; use `heap_caps_aligned_alloc(64, ..., MALLOC_CAP_SPIRAM|MALLOC_CAP_DMA)` to be safe.
8. **1000 Mbit/s per lane on the ILI9881C.** Espressif's own `ILI9881C_PANEL_BUS_DSI_2CH_CONFIG` uses 1000, so it is probably fine. If the picture sparkles, try 800 to 900 (the 2-lane RGB565 minimum is 624).

---

## (a) Verified correct

- **GPIO sequencing safety.** Drive is set with `gpio_set_drive_capability(...,GPIO_DRIVE_CAP_0)`; `io_mux_struct.h` gives "fun_drv ... 0:5mA" and `gpio_ll.h:479` sets `IO_MUX.gpio[n].fun_drv`. The output register is written before the output is enabled (`drive()`). The drive plan never drives against HELD or off-baseline nets. EN1/EN2 have `drive_ok=false`. Pulses last 20–50 µs (1–3 ms on the 100 nF nets). TPS61165 CTRL pulses are shorter than t_es_delay and are followed by more than 2.5 ms low, so EasyScale cannot latch. No step can damage a driver.
- **LP pads 0–15.** `GPIO_RTCIO_ARE_INDEPENDENT = 1` on non-ESP32 targets (`gpio.c:39-43`), so pulls and drive go through the digital IO_MUX. `gpio_config` calls `rtc_gpio_deinit` (`gpio.c:406-409`, `rtc_io.c:66-86`).
- **After an EXT1 wake.** IDF releases the hold at startup (`sleep_gpio.c:395-402`, `esp_deep_sleep_wakeup_io_reset`), and `configure_pins()`'s `gpio_config` returns GPIO0 to digital.
- **`gpio_reset_pin` on the I2S and unused pins.** It enables the pull-up and disables input (`gpio.c:496-516`). That is harmless and is what the comment says.
- **Drive restore.** `GPIO_DRIVE_CAP_DEFAULT = 2`, which equals the IO_MUX reset default "fun_drv default: 2".
- **DSI probe.** Packet headers and payloads match `mipi_dsi_hal_host_gen_write_dcs_command` (long DCS write with word count 4), `gen_write_short_packet(MAX_RETURN_PKT, 1)` and `gen_read_short_packet(DCS_READ_0)`, including `enable_bta` and `set_rx_vcid`. Video mode is still off at probe time (enabled only in `dpi_panel_init`, `esp_lcd_panel_dpi.c:469`). `phy_stopstate0lane` is bit 4, the same bit `mipi_dsi_phy_ll_are_lanes_stopped` uses. Every wait is bounded by esp_timer at 20 ms, so the probe cannot hang. On success it leaves page 0, BTA on, rx VC 0 and the read FIFO drained, which is IDF's own post-read state, and the ILI9881C driver's init then works.
- **Panel timing.** The DPI source is PLL_F240M with a divider of 3, giving 80 MHz. The HAL then stretches HFP by 24 so that the refresh rate is 59.05 Hz. VSYNC comes from the bridge interrupt on rev ≥ 3 (`mipi_dsi_brg_ll.h`, `HAL_CONFIG(CHIP_SUPPORT_MIN_REV) >= 300`).
- **ISR safety.** The VSYNC callback (spinlock `_ISR`) and the color-trans-done callback (`xSemaphoreGiveFromISR`) are fine. `CONFIG_LCD_DSI_ISR_CACHE_SAFE` is off, so the callbacks may live in flash.
- **PSRAM coherency.** The DMA2D backend does C2M on the source and C2M+invalidate on the destination (`async_color_convert_dma2d.c`).
- **Judgement logic.** All 60 host cases pass. `list_bits` and the `missing`/`untested` buffers cannot overflow (snprintf-bounded, index checked). Screen briefs fit (35 × 12 px from x=264). Row pitch is at least 18 px for 48 items. The report overflow counts correctly.
- **Chip, PSRAM and flash checks.** `esp_psram_get_size()` is the physical size (`esp_psram_impl_ap_hex.c:509-521`). `esp_flash_get_physical_size` maps the 0x20 capacity byte to 64 MiB (`spi_flash_chip_generic.c:110-115`). The Winbond driver sets the 32 MB-address capability for density ≥ 0x19. The chip revision is decoded as major×100+minor.
- **USB host detection.** `usb_serial_jtag_is_connected()` is live because the connection monitor is linked when the USJ console is enabled (`esp_driver_usb_serial_jtag/CMakeLists.txt:30-33`).
- **TUSB320 decode.** OUT1/OUT2 H/H none, H/L default, L/H 1.5 A, L/L 3 A matches the datasheet table.
- **EXT1 wake.** GPIO0 with ANY_LOW is accepted by `esp_sleep_enable_ext1_wakeup_io` (`sleep_modes.c:2108-2150`). The power-off waits for the button release before sleeping.
- **Stacks.** Own frames: app_main 256 B, judge_panel 336 B, report_shorts 448 B (its big arrays are static), board_init 336 B, audio_worker 1216 B of 4096. With picolibc, the main-task chains stay well under 3584 B. The console task gets 6144 B.
- **Timing and watchdogs.** The longest busy section is the short scans, below about 2 s worst case, under the 5 s TWDT (which is print-only anyway). The probe is at most about 0.6 s.
- **Partitions and flash layout.** App slots end below 16 MiB, the factory app is never an update target, and `slim4_system_update` checks bounds and the session state correctly. The NVS namespace (`g` plus 14 hex digits, 15 chars) and keys of at most 15 chars are within the NVS limits.
- **Audio.** SD_MODE goes high 1 ms before the clocks start and low before they stop. The 2400-frame tone fits in the 4096-frame queue limit, and enqueueing is mutex-protected.
- **Console write path.** The USJ VFS driver path blocks for at most 50 ms once, then drops output (`usb_serial_jtag_vfs.c:740-756`), as the commit says.

## (b) Bring-up debug hooks to add

1. **Early log.** Call `slim4_selftest_log()` right after the GPIO checks, before any driver.
2. **Breadcrumb per stage.** Add an `ESP_LOGI(TAG, "display stage: %s", ...)` at every `s_display_stage` assignment. Store the stage in `RTC_NOINIT` memory and print it on the next boot, so a hang or watchdog reset names its stage.
3. **Start the console first** (before `slim4_platform_init`) and add:
   - `stage`: display stage, probe result, and `MIPI_DSI_HOST.phy_status/cmd_pkt_status/int_st0/1` raw;
   - `dsi`: dump the host and bridge registers;
   - `ldo <mv>`;
   - `probe`: re-run the bounded probe on demand;
   - `pin <n> drive <0|1|z>`: at drive cap 0, refused for 13/46, for meter work;
   - `adc`: raw battery reading;
   - `en <mode>`: explicitly set the charger mode, behind a confirmation;
   - `wdt`: print the stack high-water marks of main, audio, console and esp_timer.
4. **Make USB-Serial-JTAG the primary console for bring-up builds** (F7), or add UART0 test pads.
5. **DSI bridge underrun counter.** Register a tiny ISR hook, or poll `mipi_dsi_brg_ll_get_interrupt_status` from the 1 s stats line, and print `underruns=N` beside fps/vsync.
6. **Display-init timeout task** (F3), with a log line that names VDDO_MIPI_2V5 and U1 pads 41/73 when the PLL never locks.
7. **Self-test modes from the console:**
   - `selftest pins`: re-run the GPIO checks with all drivers stopped (or at least with I2S and LEDC released);
   - `selftest raw`: print the full pull readings and both scan matrices (`when_high/when_low`) so a suspected bridge can be confirmed by hand.
8. **Video-lane soak.** Alternate checker and inverse checker at 60 Hz for N seconds while counting underruns and vsync drift: a lane-margin test for CLK/D1. Add `lanerate <mbps>` (re-init the bus) to find the margin.
9. **Boot-time summary line.** One line with every stage's duration: memtest, GPIO checks, DSI bus, probe, panel init, first frame.
10. **Power log.** Every 5 s on change: raw ADC, the mV figure, CHG, PGOOD, OUT1/OUT2, EN1/EN2 levels as written, cap and mute, with the reason for any cap or mute change.
11. **`CONFIG_ESP_TASK_WDT_PANIC=y` with coredump-to-flash** (already enabled) on bring-up builds, so a busy-loop hang in IDF's DSI HAL leaves a backtrace instead of a silent stall.
