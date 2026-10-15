# F133 bare-metal bring-up image (R07)

Evidence: **BUILD-ONLY** (compiled, packaged, header checked). **It has never run on an F133.**

* Toolchain: Ubuntu `gcc-riscv64-unknown-elf` 13.2.0, `u-boot-tools` 2025.10 (`mkimage -T sunxi_egon -A riscv`).
* `make` → `build/arc1_r07_f133.egon` (8 KiB eGON.BT0, 5.9 KiB used). `egon_check.py`
  independently verifies the jump (`jal +0x60`), magic, length, checksum and fit in the
  32 KiB SRAM A1.
* SD card: `dd if=arc1_r07_f133.egon of=/dev/sdX bs=1024 seek=8` (sector 16). This presumes
  the BROM reads boot0 from the 8 KiB offset, as on other sunxi SoCs: **ASSUMPTION**, confirm
  on a D1s board.
* The BT820 driver is compiled from the **same** sources the host tests exercise
  (`../firmware/src/bt820_host.c`, `bt820_gfx.c`). Only the HAL in `main.c` is target-specific.

What it does: UART0 banner on PE2/PE3 at 115200 baud. Prints VER_REG[12:11] / FEL[8], SID boot
select and the RTC fast-boot register. Holds the T35 in reset. Boots the BT820 over SPI1 at
8 MHz single mode (AN086 §2.5). Prints REG_BOOT_STATUS / REG_CHIP_ID / REG_ID / REG_CPURESET
with result codes. Starts scan-out with the unconfirmed candidate-panel timing and clears to
blue. Reads REG_FRAMES.

Known gaps (bench stage A of `../docs/BENCH_BRINGUP_PLAN.md` closes them):
* Register addresses come from the D1-H UM, assumed equal on the F133.
* The CPU clock after BROM is unknown. `mcycle` delays assume ≤ 1.2 GHz, so they are long,
  never short.
* No DRAM init. The image runs from SRAM A1 only, which is enough for UART + SPI + BT820
  bring-up.
* SPI1 CS# is driven as a software-owned SS through TCR.SS_LEVEL (UM 9.3.6.2). This must be
  verified on a logic analyser together with the 0x01 polling.
