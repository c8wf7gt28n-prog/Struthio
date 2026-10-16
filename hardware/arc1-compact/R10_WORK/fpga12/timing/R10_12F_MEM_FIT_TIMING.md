# 12F memory variant (4 MiB QSPI PSRAM) — fit and timing

Design: `rtl/r10_support_mem_top.sv` (memoryless `r10_support_top` + `r10_mem_engine` + R06 `psram_user_port` +
R8.5-C `psram_bist`). Pins: `../hardware/lpf/r10_12f_mem_proxy256.lpf` appended to `r10_12f_proxy256.lpf` (same
caBGA256-proxy method as the memoryless build; TQFP144 pin-locked P&R is NOT_RUN, decision D4).
Commands: `make lint_mem sim_mem seeds_mem` (Yosys `synth_ecp5 -abc9`, nextpnr-ecp5 `--12k`, seeds 1–5, speed −6/−7).

| Item | Result | Label |
|---|---|---|
| Lint (Verilator -Wall) | clean | — |
| System TB `R10_12F_MEM_TB_PASS` | 11 reference AJOB cases through the dispatcher, STATUS, FIR-absent, negative frames, PSRAM: BAD_STATE before init, BIST 0 errors, 4096-byte unaligned write/read, corrupted write rejected with memory unchanged, top-of-memory, RANGE, 1 byte, bad lengths; APS6404L model rule violations 0 | RTL_SIMULATED |
| Timing, 10/10 runs | −6: sys 81.6–87.4 MHz (80), PSRAM 92.6–98.6 (40), RGMII TX 132–151 (125), RX 156–180 (125); −7: sys 89.1–101.8 | OPEN_TOOLCHAIN_ROUTED (proxy package) |
| Utilisation vs LFE5U-12F datasheet | LUT4 7209 / 12 288 = 59 % (memoryless 41 %); FF 5473; EBR 10 / 32; MULT18 8 / 28; PLL 2 / 2 | DERIVED |
| End-to-end PSRAM throughput (RGMII request → response) | 4096-byte write 1727 µs (≈ 2.4 MB/s); 4096-byte read 625 µs (≈ 6.5 MB/s) | RTL_SIMULATED |

Notes
- −6 margin on sys_clk is small (worst seed 81.6 MHz for 80 MHz, 2 %); −7 has 11 %+. Decision D3 (−6) stays valid
  but this variant is the one to watch when logic is added.
- Throughput is limited by the R06 controller's per-request handshake and this engine's 3-clock byte reader; fine
  for the memory spec's "infrequent large batches" use (§6.2), not for streaming.
- The PSRAM part (APS3204L family) protocol is assumed APS6404L-compatible: UNVERIFIED until its datasheet is read.
  The BIST overwrites PSRAM bytes 0–16383.
