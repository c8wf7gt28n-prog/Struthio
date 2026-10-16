# R10 improvement pass — 2026-10-16

This pass improves deployability without changing the frozen R10 topology or claiming unavailable RTL/hardware
evidence.

## 45F GPU submission path

`d213/gpu_driver` now has `gpu_emit_frame_jobs()`, a production-oriented frame planner layered beside the unchanged
compact `gpu_emit_frame()` API. It emits one `TILE_BEGIN..TILE_END` span per transport request, records exact offsets,
lengths, tile coordinates and triangle counts, rejects insufficient manifest space or an oversized job atomically,
and re-establishes registers in every tile job so a request is independently replayable after loss/reset.

On the existing 320x240 cube/floor benchmark: 80 jobs; maximum job 322 words / 644 bytes; independent state costs
18.8% more words than the compact in-process stream. Both streams render bit-identical through `gpu_ref.c`. This is
HOST_TESTED, not D213 GMAC hardware evidence. It does not turn the C-model v1 texture pipeline into RTL; that remains
the major 45F implementation task.

## 12F adaptive mechanics role

`fpga12/adaptive` adds ABI 1.0 and a bit-exact, freestanding C fallback for a 128-body, 16-layer AABB broad-phase job.
The result is a symmetric collision bit matrix; the F133 remains authoritative and performs narrow phase/gameplay.
At maximum size, the request payload is 2,568 bytes, the response matrix is 2,048 bytes, and 8,128 unordered pairs are
examined. Tests cover exact half-open edge behavior, layer filtering, invalid boxes, full matrix symmetry, deterministic
random cross-checking, sanitizers, freestanding compilation, and a killed inclusive-edge mutant.

This is HOST_TESTED reference/ABI/fallback only. A compact RTL pair comparator, mailbox packing, simulation, synthesis,
and P&R are still required before the 12F can execute the job.

## Authority and repeatability

Root `START_HERE.md` and `CLAUDE.md` now identify R10 as current instead of incorrectly directing a new engineer into
R06. `run_host_checks.sh` runs the portable checks available with Python and a C compiler. `run_all.sh` also includes
the new mechanics suite but still requires the complete FPGA toolchain.

## Evidence boundary and next work

- HOST_TESTED: interface/NOR/pinmux generators; C GPU model; D213 GPU driver and packet planner; graphics link; F133
  bootloader; adaptive mechanics fallback/ABI.
- NOT_RUN in this environment: Icarus/Verilator RTL simulation, Yosys synthesis, nextpnr/Trellis P&R, Lattice native
  TQFP144 flow, D213 SDK build, boards and instrumentation.
- Next 45F step: implement ABI-v1 texture/perspective state in RTL, beginning with texture fetch/cache and SDRAM
  arbitration; compare every tile against `gpu_ref.c` before timing work.
- Next 12F step: implement and simulate the AABB pair iterator and matrix packer, integrate opcode `0x0030`, then prove
  it fits beside the memory variant. Do not remove the F133 fallback.
- Fabrication remains HOLD.
