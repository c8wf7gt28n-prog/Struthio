# F133 ↔ D213 graphics command link (R10 §12.1 item 7)

Status: protocol layer **HOST_TESTED** (both ends, fault-injection mock); USB transport **NOT_RUN** (no bare-metal
USB stack in this repo, no hardware).

## What is here
- `include/gfx_link.h`, `src/gfx_link.c` — packet format, F133 host side (`gl_hello`, `gl_submit_frame`) and the
  transport-independent D213 device side (`gl_dev_rx`, `gl_dev_tick`). Freestanding C11; no allocation.
- `tests/test_gfx.c` — host and device joined by a USB bulk-pipe mock with fault injection: lost/corrupted
  requests and responses, stale responses, bulk errors, device restart between chunks, device losing assembly
  state, dead link, watchdog.
- `make all` → `test` (45 checks), `sanitize` (ASan/UBSan), `freestanding` (object compile), `mutants` (7 mutants,
  all killed).

## Behaviour
- One request outstanding. Timeout or corrupt reply → resend the **same seq**; the device answers a repeated seq
  from its cached reply without executing again (no double draw).
- Device restart (boot id changes) → HELLO, frame restarted from chunk 0. Device out of order → frame restarted.
- 3 consecutive failed frames → link DOWN: `gl_submit_frame` returns `GL_FALLBACK` without touching USB; the F133
  keeps game logic, audio and input running; HELLO retried every 4th frame.
- D213 side: no completed frame for the watchdog period → `link_lost` once → D213 shows its own 2D diagnostic
  screen (`d213/boot_and_display/PLAN.md` step 5).

## Transport feasibility (USB 2.0 high speed)
| Item | Figure | Label |
|---|---|---|
| Bulk ceiling | 13 × 512-byte packets per 125 µs microframe = 53.2 MB/s | DERIVED (USB 2.0 spec Table 5-10, bulk) |
| Command traffic needed | ≈ 200 objects × 16 B + layers ≈ 4 KB/frame → ≈ 0.25 MB/s at 60 fps | PLANNING_CALCULATED |
| Minimum per exchange | OUT then IN in later microframes: ≥ 2 microframes ≈ 250 µs | DERIVED |
| Achieved with bare-metal stacks | — | NOT_RUN |

The link carries commands, not pixels, so bandwidth is not the risk; **latency per exchange** and **driver
availability** are. Open items:
1. F133 USB1 is a separate EHCI/OHCI host with its own PHY (F133 DS rev 2.3 §2.10, pins 112/113). R8.5-C
   removed its use (decision D-04); R10 reinstates it. A bare-metal EHCI bulk-only host driver is needed — none in
   this repo.
2. D213 USB0 device stack (vendor SDK) — availability in bare-metal form UNVERIFIED.
3. D213 USB0 is also its upgrade/recovery port: on the board, recovery mode (boot-ROM USB) must be selectable
   without the F133 host enumerating it as the graphics device — a strap/button plus the F133 holding VBUS off.
