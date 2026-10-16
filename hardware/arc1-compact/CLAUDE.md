# ARC-1 Compact — current engineering instruction (R10)

`R10_WORK/` is current and supersedes the earlier R05/R06/R07/R08/R8.5 direction wherever they conflict. Preserve
older trees as immutable historical/reference evidence; place new architecture work in `R10_WORK/` and test it there.

## Frozen R10 topology

- F133-B + 64 MiB in-package DDR2: system/game authority and fallback path.
- D213ECV + 128 MiB DDR3: display/2D engine and 45F command preparation.
- ECP5-45F + 32 MiB x16 SDR SDRAM: optional tile GPU, linked to D213 GMAC0 by RGMII.
- ECP5-12F + 4 MiB QSPI PSRAM: optional adaptive coprocessor; it never owns game state.
- One central 64 MiB NOR with the generated R10 partition map.
- Change order rev 1.1 (owner handoff, `R10_WORK/spec/ARC1_R10_Handoff_rev1.1.docx`; decisions D8-D11): exactly four
  exterior connectors (rear USB-C power/recovery + HDMI, front 2x USB-A behind a USB2422 hub on F133 USB0), no
  exterior switches, HDMI with embedded audio (ADV7513, F133 I2S2 audio). Amended by D12: five exterior connectors
  (rear USB-C + HDMI, front 2x USB-A controllers, top USB-A game cartridge via a USB2514B hub); no eMMC, games run
  from the cartridge drive.

Exact decisions and reversal costs are in `R10_WORK/DECISIONS.md`. Do not reintroduce R06's BT820/T35 topology or the
older prohibition on a fourth programmable device. Do not change the transport, device package, or ownership model
without a versioned decision and updated tests.

## Engineering rules

1. F133 game state and D213 display fallback must survive either FPGA being blank or unavailable.
2. Keep GPU ABI changes versioned. Preserve v0 flat-triangle semantics while extending v1.
3. Treat the D213 as responsible for transforms, clipping, viewport mapping, tile binning, and request scheduling.
4. Treat 45F SDRAM contents as private GPU memory, not a shared CPU RAM pool.
5. 12F jobs must be bounded, optional, timeout-safe, and have an F133 software fallback with identical semantics.
6. Preserve evidence labels: HOST_TESTED, RTL_SIMULATED, OPEN_TOOLCHAIN_ROUTED, NATIVE_EDA_VERIFIED,
   PROTOTYPE_MEASURED, BLOCKED, and NOT_RUN. Never promote one label into another.
7. Lattice TQFP144 pin-locked P&R and all prototype electrical/throughput results remain NOT_RUN until actually run.
8. Fabrication remains HOLD until the open gates in `R10_WORK/qa/` are closed.

After a pass, record changed files, commands, exit status, unavailable tools, and remaining gates. Prefer code plus
tests over prose-only planning. `R10_WORK/run_host_checks.sh` is the portable host baseline; `run_all.sh` adds RTL and
P&R and therefore requires the complete FPGA toolchain.
