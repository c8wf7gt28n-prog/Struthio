# R07 changelog (relative to R06-draft-1)

`R05_BASELINE/` and `R06_WORK/` are unchanged byte-for-byte. The runner checks the R05/handoff
manifest, and R06 reruns from a scratch copy. All R07 changes live in `R07_WORK/`.

## Fixed
* **R06-BT-0x7F (P0):** `bt820_host` refused every write ≥ 0x7F000000, which blocked the
  command FIFO, registers and display list. It now validates every access against the AN086
  Table 2 memory map plus REG_CMDB_WRITE, refuses reserved space (including the
  0x7FE0–0x7FEB host-command shadow), and allows only AN086 Table 3 host-command codes.
  Configuration commands are refused while ACTIVE. Regression probe against the frozen R06
  code: `make -C R07_WORK/firmware r06-probe`.
* BT820 32-bit byte order: an R06 ASSUMPTION, now **little-endian per the Bridgetek reference
  driver**.

## Added
* `firmware/src/bt820_gfx.c`: AN086 §2.5 boot (RST_N, BOOTCFGEN/SETBOOTCFG/SETDDRTYPE/
  SYSCLKDIV, ACTIVE, BOOT_STATUS/CHIP_ID/REG_ID/CPURESET), command FIFO with wrap, scan-out
  (§2.14 + EveApps LVDS setup), test frame. Includes failure signatures.
* `firmware/include/bt820_regs.h`: addresses traced to AN086 and EveApps.
* Mock BT820 v2: memory map, power state, host-command table, coprocessor execution, fault knobs.
* Tests: 266 checks (R06 suite carried forward, now with real boot + FIFO). Four firmware
  mutants, all killed.
* `board/r07_board_plan.json` (rev R07-draft-1): F133 boot policy (straps 11, 10 kΩ pull-ups),
  T35 CRESET_N 4.7 kΩ pull-down (FPGA held off the strap pins), USB0 reserved for FEL, MN820
  module-level I/O levels, 3V3 rail tightened to 3.20–3.40 V. Six new checker rules with
  negative tests (396 rules, 25 tests).
* `analysis/psram_power_io.py`: worst-case DC analysis of the PSRAM power-up network and levels.
* `fpga/psram_r07/`: PSRAM power-interruption model and scenarios R1–R3 against the unchanged R06
  RTL. Extra clock ratios C4/C5 through the R06 bench.
* `f133_boot/`: bare-metal F133 eGON bring-up image (UART banner, boot-select readout, BT820
  boot via SPI1 using the host-tested driver). Reproducible build plus independent header check.
* Docs: BT820_HOST_PROTOCOL, F133_BOOT_PIN_POLICY, MN820_POWER_ERRATA, PSRAM_POWER_AND_IO,
  VENDOR_QUESTIONS, BENCH_BRINGUP_PLAN, SOURCES_R07. Also RISK_REGISTER and
  EVIDENCE_LEDGER.json.
* `tools/run_r07_checks.py`: one command for all R07 checks plus the full R06 regression.

## Behaviour changes to note
* The T35 no longer self-configures at power-up. The F133 must drive PE8 high (board plan,
  bring-up image).
* 3V3 tolerance tightened from 3.14–3.47 V to 3.20–3.40 V.
