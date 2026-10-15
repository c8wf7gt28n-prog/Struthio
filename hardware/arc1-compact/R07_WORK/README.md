# ARC-1 Compact: R07 work area (PASS 7)

Start with `R07_STATUS.md`. R05 and R06 remain frozen; R07 reruns their suites as regression.

```
python3 R07_WORK/tools/run_r07_checks.py            # everything incl. full R06 regression, ~6 min
python3 R07_WORK/tools/run_r07_checks.py --skip-r06 # R07 steps only, ~1.5 min
```
Extra tools beyond R06: `gcc-riscv64-unknown-elf`, `u-boot-tools` (mkimage).

| Path | Content | Evidence |
|---|---|---|
| `R07_STATUS.md` | outcome, commands/results, blockers, no-fabrication statement | — |
| `CHANGELOG.md`, `RISK_REGISTER.md`, `EVIDENCE_LEDGER.json` | changes, risks with owners, per-claim evidence ledger | — |
| `firmware/` | BT820 host layer (0x7F fix), boot/FIFO/scan-out, T35 mailbox client, offload with CPU fallback, mocks, tests, mutants, R06 probe | HOST-TESTED |
| `f133_boot/` | F133 bare-metal eGON bring-up image | BUILD-ONLY |
| `board/` | rev R07 pin/voltage/boot-strap plan + checker + generated `PIN_MAP_R07.md` | PLANNING-CALCULATED |
| `analysis/` | PSRAM power-up/DC worst-case script | PLANNING-CALCULATED |
| `fpga/psram_r07/` | PSRAM fault scenarios and extra clock ratios (R06 RTL unchanged) | RTL-SIMULATED |
| `docs/` | BT820_HOST_PROTOCOL, F133_BOOT_PIN_POLICY, MN820_POWER_ERRATA, PSRAM_POWER_AND_IO, VENDOR_QUESTIONS, BENCH_BRINGUP_PLAN, SOURCES_R07 | — |
| `evidence/` | run logs, reports, F133 image, manifests (`LATEST.txt`) | — |

Efinity results are absent (NATIVE_EDA_NOT_RUN). The T35 project inputs remain in
`R06_WORK/fpga/efinity/`. The FPGA RTL is unchanged in R07.
