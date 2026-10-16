# ARC-1 R10 — 45F GPU command ABI, version 1.0

Normative header: `abi/r10_gpu_abi.h`. Normative arithmetic: `tools/gpu_ref.c` (bit-exact interpreter; any
implementation — RTL, D213 driver emulation — must produce the same output words for the same job stream).
Status: **ABI frozen at 1.0 for the C model; RTL implements v0 only** (flat triangles). Every change to this file
or the header bumps `GPU_ABI_MINOR` (additions) or `GPU_ABI_MAJOR` (incompatible), and the 45F reports both in STATUS.

## Transport
Job words are 16-bit little endian, carried in RJOB frames (`fpga45/rtl/r10_raster_engine.sv`): opcode 1 RASTER
(whole tile), 2/3 RASTER_HALF0/1 (tile in two standard Ethernet frames), 0x10 STATUS. A request may hold any number
of commands but at most one TILE_END. State (registers, palette, SDRAM texture memory) persists across requests
and tiles; only TILE_BEGIN clears the tile colour and depth buffers.

## Commands
| Word 0 | Name | Words | Meaning |
|---|---|---|---|
| 0x0001 | TILE_BEGIN | 5 | tile_x, tile_y (pixels, multiple of 32, 0..2016), clear colour, clear depth |
| 0x0002 | TRI_FLAT | 11 | v0 triangle: x/y ×3 (signed 12.4), z ×3, RGB565. Always z-test (<) + z-write + replace; ignores MODE |
| 0x0003 | TILE_END | 1 | emit 'TI', tile_x, tile_y, 1024 RGB565 (row-major), CRC-32 lo/hi of the colour bytes |
| 0x0010 | SET_REG | 4 | register, value[15:0], value[31:16] |
| 0x0011 | TRI_TEX | 20 | 3 × {x, y (12.4), z (u16), q (u16, 1/w scaled), u, v (signed 12.4 texels)}, RGB565 |
| 0x0012 | UPLOAD_TEX | 4+n | SDRAM word address lo, hi; n (≤ 2048); n data words |
| 0x0013 | UPLOAD_PAL | 3+n | first index, n, n RGB565 entries (on-chip palette, 256 entries) |
Unknown command words are skipped one word at a time and counted (STATUS). A command cut off by the end of a
request is dropped (RJOB status 5 TRUNCATED_COMMAND).

## Registers (all 32-bit, reset 0)
| # | Name | Fields |
|---|---|---|
| 0 | TEX_BASE | SDRAM word address of texel (0,0) |
| 1 | TEX_CFG | [3:0] log2 W, [7:4] log2 H (0..10), [9:8] format 0 RGB565 / 1 I8 (palette) / 3 none, [10] clamp U, [11] clamp V (else repeat) |
| 2 | MODE | b0 Z test, b1 Z write, b3:2 blend (0 replace, 1 constant alpha, 2 additive), b4 colour key, b5 fog, b6 dither, b7 scissor, b8 modulate |
| 3 | ALPHA | 0..32 |
| 4 | FOG_COLOR | RGB565 |
| 5 | FOG | [15:0] start z, [31:16] scale; f = clamp(((z − start) · scale) >> 16, 0, 32) |
| 6 / 7 | SCISSOR_X / Y | first [15:0], last [31:16], inclusive screen pixels |
| 8 | COLOR_KEY | RGB565 texel value treated as transparent |

## Per-fragment pipeline (TRI_TEX), in order
1. Coverage: v0 edge functions, top-left rule, sample at pixel centre, bounding box clamped to the tile.
2. Scissor (if enabled).
3. Depth: z from the v0 plane equation (Q16, gradients saturated to 32 bits); z test if enabled.
4. Texture (format ≠ none): attributes u·q, v·q, q interpolated with Q16 plane equations (gradients saturated to 40
   bits, exact 64-bit evaluation); q clamped to [1, 65535]; u = trunc(uq / q), v = trunc(vq / q) in 12.4; texel =
   floor; repeat (mask) or clamp; fetch RGB565 or I8 → palette. Nearest-neighbour only in 1.0.
5. Colour key: a texel equal to COLOR_KEY discards the fragment (no colour, no depth write).
6. 565 → 888 by bit replication; modulate: c · (m + 1) >> 8 with the triangle colour m.
7. Fog: (c · (32 − f) + fog · f) >> 5.
8. Blend with the tile colour d: replace / (c·a + d·(32 − a)) >> 5 / min(255, c + d).
9. Quantise to 565: truncate, or add the 4×4 Bayer offset (>>1 for 5-bit, >>2 for 6-bit channels) and saturate.
10. Depth write if enabled.

## Host (D213) responsibilities — not done by the GPU
- Transform, lighting, **clipping in clip space** (near plane w > 0 and the ±2048-pixel guard band of the 12.4
  coordinates), viewport mapping, back-face culling if wanted.
- Choosing q: any per-triangle positive scale of 1/w works (perspective correction is scale-invariant per
  triangle); the reference driver uses q_i = 65535 · w_min / w_i.
- Binning triangles to 32×32 tiles and ordering state changes per tile.
Reference implementation of these: `d213/gpu_driver` (HOST_TESTED against this model).

## Evidence
`make gpu_ref gpu_mutants`: self-checks (perspective u/v within 1/16 texel of a double-precision reference; colour
key, alpha 0/32, additive saturation, fog endpoints, scissor, I8 palette, dither mean), v0 regression identical
to `raster_ref`, 24 random tiles / 96 triangles of vectors (`gpu_jobs.memh`, `gpu_expect.memh`), 3/3 mutants
killed. RTL for v1: not built yet.
