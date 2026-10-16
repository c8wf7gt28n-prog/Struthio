# D213 GMAC0 ↔ 45F RGMII job link — driver and test plan (replaces the PBUS plan, decision D1)

Status: 45F side **RTL_SIMULATED + OPEN_TOOLCHAIN_ROUTED** (`fpga45/`); D213 side **NOT_RUN** (no driver code, no
hardware). Gate R10-E.

## Wire protocol (implemented in `fpga45/rtl/r10_raster_engine.sv`, tested by `fpga45/tb/tb_r10_45f.sv`)
Raw Ethernet, EtherType 0x88B5, no PHY, no IP — the R8.5-C framing (`R85C_WORK/firmware/include/eth_link.h`):
`dst | src | 0x88B5 | len16 | payload`. The 45F replies to the requester's MAC.
- Request `RJOB`: version 1, opcode (1 RASTER, 2/3 RASTER_HALF0/1, 0x10 STATUS), count (16-bit words), seq,
  CRC-32 of the payload. RASTER payload = raster job words (`fpga45/tools/raster_ref.c` format); at most one
  TILE_END per request. HALF0 carries the tile's jobs and returns 'TI', x, y + rows 0–15 (515 words); HALF1 carries
  the single word TILE_END, which re-emits the same tile, and returns rows 16–31 + CRC (514 words).
- Response `RRES`: status (0 OK, 1 BAD_LENGTH, 2 BAD_VERSION, 3 BAD_OPCODE, 4 PAYLOAD_CRC — nothing drawn,
  5 TRUNCATED_COMMAND — job ended inside a command, that command dropped, 7 OUTPUT_OVERFLOW / not exactly one tile
  for opcodes 2/3), output word count, seq, CRC-32 of the output. A tile = 1029 words ('TI', x, y, 1024 RGB565,
  CRC lo/hi).
- Anything not starting with `RJOB` is looped back unchanged (delay calibration, as `el_calibrate` on the F133).

## Driver requirements
1. **Frame size.** A whole-tile response (opcode 1) is a 2092-byte frame, above the 1518-byte standard maximum.
   D21x GMAC accepts up to 10 240-byte frames with Jumbo Enable (MAC reg 0x0020 bit 4; DOCUMENTED in the D21x user
   manual MAC page and Luban-Lite aic_mac_reg.h; the vendor driver default is 1524 B, so the driver must set JE). The engine therefore also offers half tiles (opcodes 2/3):
   largest frame **1066 bytes** including FCS (RTL_SIMULATED, all 18 tiles exact) — kept as the fallback.
2. **DMA descriptors and coherence.** C906 data cache vs GMAC DMA: TX buffers cleaned (write-back) before the
   descriptor is handed to DMA; RX buffers invalidated before the CPU reads them, or both rings placed in an uncached
   window. Whether the D213 interconnect is DMA-coherent is **UNVERIFIED**; assume not.
3. **One job in flight** (the 45F endpoint holds one frame; a frame arriving while busy is dropped and counted).
   Pipelining two tiles needs a second 45F buffer — future RTL.
4. **IRQ/timeout.** RX-complete IRQ wakes the renderer; per-job timeout 2 ms (≫ 120 µs simulated round trip);
   retry the same seq up to 3×; a stale RRES (old seq) is discarded and counted; after 3 consecutive failed jobs
   the renderer marks 3D down and draws the scene with GE-only 2D (R10 §3.1 fallback).
5. **RGMII delays.** The 45F transmits clock-aligned (no internal delay); the D213 adds the RX clock delay:
   SYSCFG GMAC0_CFG (0x1800_0410) RXDLY_SEL [22:18] / TXDLY_SEL [16:12], 32 steps of 170 ps (0–5.3 ns), clock invert
   bits 17/23 (DOCUMENTED: Luban-Lite hal_syscfg.c + SDK MAC guide). Calibrate by loopback sweep as on the F133 — the
   pad-level budget (`R85C_WORK/docs/RGMII_LINK_R85C.md` method; 45F GDDRX1 figures DOCUMENTED, DS-02012 Table 3.22).
6. **Pin mux.** PE0–PE15 to GMAC0 only after the 45F reports DONE; until then IO-disable (mirrors the F133 PG rule).

## Tests (to run on hardware; the first column mirrors the RTL TB where one exists)
| ID | Test | Pass criterion | RTL TB equivalent |
|---|---|---|---|
| G-E01 | Loopback sweep over GMAC delay settings | widest error-free window, centre chosen | `r10g_loopback` |
| G-E02 | All tiles of the C-model job stream | every RRES word == `expect.memh`; CRC OK | `r10g_tiles_rgmii` (18 tiles PASS) |
| G-E03 | Corrupted payload | status 4, next tile still exact | yes |
| G-E04 | Bad opcode / length | status 3 / 1 | yes |
| G-E05 | STATUS counters | rx_ok/tx match driver counters | yes |
| G-E06 | Lost response (cable glitch injected via 45F test mode or IRQ mask) | retry, no duplicate draw | — |
| G-E07 | Sustained 75 tiles × 60 fps for 10 min | no timeout; tail latency recorded | — |
| G-E08 | 45F unconfigured | renderer falls back to 2D within one frame | — |

## Throughput budget (R10 §5.1 minimum: 320×240 RGB565 at 60 Hz)
- Pixels needed: 75 tiles/frame × 2058 B = 154 KB/frame → 9.26 MB/s at 60 Hz (DERIVED).
- Wire: 2092-byte frame + 8 preamble + 12 IFG = 2112 B at 125 MB/s = 16.9 µs/tile (DERIVED).
- 45F simulated round trip, one tile in flight: 18 tiles in 2155 µs = **119.7 µs/tile average** (RTL_SIMULATED,
  includes clear 12.8 µs and tile output at 4 clocks/word ≈ 51 µs); 75 tiles ≈ **9.0 ms/frame** of the 16.7 ms
  budget **before** D213 driver, cache maintenance and IRQ latency (NOT_RUN). The 45F output path (4 clocks/word)
  is the largest fixed cost and is the first optimisation if G-E07 misses.
- With half tiles (standard frames): 18 tiles in 3123 µs = **173.5 µs/tile** (RTL_SIMULATED; extra round trip and
  the tile is emitted twice) → 75 tiles ≈ **13.0 ms/frame** of 16.7 ms before D213 costs. Too tight to count on:
  if jumbo frames are unavailable, the next RTL step is a tile output path faster than 2 clocks/word and a second
  tile buffer so the next tile draws while the current one is returned.
