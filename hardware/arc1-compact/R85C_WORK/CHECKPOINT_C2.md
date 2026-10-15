# ARC-1 Compact R8.5-C — checkpoint after C2 (RGMII FPGA side)

Option C (re-architect the link, resident-state workloads) with the link switched to RGMII
(F133 EMAC PG0–PG12 ↔ ECP5 bank 0). Single-bit SPI (R06 slave) stays for configuration and control;
the quad-SPI slave and CB3Q3125 bus switch are dropped. Base: R85_WORK frozen at 8636e38 (R85_BASE_COMMIT.txt).

Everything below is RTL simulation or open-toolchain routing. Nothing has run on silicon.

| Item | Result | Evidence label | Log in this ZIP |
|---|---|---|---|
| RGMII RX/TX MACs, eth_link glue + job-source arbiter, sys-domain TX pump + async FIFO | Written | — | `fpga_ecp5/rtl/` |
| RGMII unit TB (`make rgmii`) | PASS; 15 RX/TX/pump mutants all caught | RTL_SIMULATED | `evidence/sim_rgmii.log` |
| System TB (`make sim`): AJOB cases 0–13 over SPI, 0–10 and 14–19 over RGMII, byte-exact vs C reference; bad frames, SPI/Ethernet arbitration, abort over RGMII, R08 power scenarios | PASS (`TOP_ECP5_TB_PASS`, `AJOB_RTL_CHECK_PASS`) | RTL_SIMULATED | `evidence/sim_ecp5_top.log`, `evidence/ajob_rtl_check.log` |
| R05 transform oracle TB, resident FIR TB | PASS | RTL_SIMULATED | `evidence/transform_r05tb.log`, `evidence/sim_accel_fir.log` |
| Verilator lint | clean | — | `evidence/lint_ecp5.log` |
| Routed timing, seeds 1–5 | All PASS: sys_clk 80.2–85.7 MHz (80 req), eth_txclk 136–149 (125), rgmii_rxc 141–169 (125) | OPEN_TOOLCHAIN_ROUTED | `evidence/SEEDS_SUMMARY.txt`, `evidence/nextpnr.log` |
| Bitstream (seed 1) | sha256 087cb5a25518b90ece9036e8fb44550680c12ba76bb869d170c0e84403c212be, byte-identical rebuild | OPEN_TOOLCHAIN_ROUTED | `evidence/BUILD_REPORT.md`, `evidence/repro.log`, `evidence/arc1_ecp5.bit` |

RGMII simulated round trips: about 3.1 µs for a small transform job, 351 µs for a 735-sample FIR block (mostly engine compute).

## Open items (not done)
- RGMII balls come from the hand-written `fpga_ecp5/constraints/arc1_ecp5_r85c_provisional.lpf` (ASSUMPTION); C3 must move them into `board/r85_board_plan.json` and the generator.
- RGMII pad-level timing budget and F133 ETXDC/ERXDC delay settings: NOT_RUN (C3).
- ECP5 IDDRX1F/ODDRX1F simulation models are an assumption (RK-ECP5-DDR-SEM): confirm against Lattice TN-02035.
- sys_clk margin is lower than in R8.5 (84.7–88.8 MHz then); seed 1 has 0.3 %.
- P3 PG-glitch test now uses a pulse spanning one 40 MHz sampling edge; detection is guaranteed only for PG low ≥ 25 ns.
  Commit 13cebcb's message wrongly says P3 is still open; d69a71c corrects it.
- Pending: C3 board (pins, series resistors, buttons, ERC, LPF, timing budget), C4 firmware (Ethernet link, EMAC mock,
  fault tests), C5 benchmark rerun + docs + runner + full ZIP.

## Reproduce
`cd fpga_ecp5 && make lint transform fir rgmii sim report repro seeds` (needs the sibling R05_BASELINE, R06_WORK, R07_WORK
trees from the repository; tool versions in `evidence/TOOL_VERSIONS.txt`).
