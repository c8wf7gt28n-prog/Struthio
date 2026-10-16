# arc1/game.h — semantic contract (ABI 0.2, proposed)

The header is `sdk/include/arc1/game.h`. Only the host reference
implementation exists (`sdk/runtime/host/arc1_host.c`, evidence HOST_SIM).
There is no console mapping yet, so every feature below is "host reference
only". API-001 requires each supported feature to have a host behaviour, a
target mapping and named conformance tests. The target mapping column stays
open until D213/F133 services exist.

| Feature | Host behaviour | Target mapping | Conformance |
|---|---|---|---|
| Lifecycle | `arc1_init` once; then `arc1_running` is non-zero until `--frames` frames were presented | open | `tests/conformance/api_conformance.c` |
| Input | `arc1_input_poll` latches the replay state for the current frame; `held` and `pressed` (edge since previous poll) are stable until the next poll; player ≠ 0 reads 0 | open | conformance, `steer-golden` |
| Frame | `frame_begin(clear)` → draws → `frame_end` presents and increments `arc1_frame_index` | open (D213 composition) | conformance, goldens |
| Draw order | painter's algorithm in call order; clipping at screen edges is not an error | open | conformance, goldens |
| Sprites | ≤ 64 sprites of ≤ 64×64 palette indices; pixels are copied at create; index 0 is transparent; handles live until shutdown | open (D213 service) | conformance |
| Rect fill | clipped, negative size → `ARC1_E_INVALID_ARG` | open | conformance |
| 3D (45F), 12F, audio | `arc1_capability` returns 0 | 45F only through versioned command buffers (API-002) | conformance |

## Errors

Every call returns an `arc1_status`. Lifecycle misuse (drawing outside a
frame, creating sprites mid-frame, a second `arc1_init`) returns
`ARC1_E_STATE`. The host harness then exits with code 70, so misuse cannot
pass a test silently. Out-of-range arguments return `ARC1_E_INVALID_ARG`, an
exhausted limit returns `ARC1_E_NO_CAPACITY`, and a feature that is not
provided returns `ARC1_E_UNSUPPORTED`.

## Screen and palette

320×180 pixels, 8-bit indexed, with the fixed 16-entry palette `arc1-0.2`
(RGB888, index order):

```
000000 1d2b53 7e2553 008751 ab5236 5f574f c2c3c7 fff1e8
ff004d ffa300 ffec27 00e436 29adff 83769c ff77a8 ffccaa
```

The resolution and palette are SDK 0.2 choices for the host model. They are
not measured display properties of ARC-1 hardware.

## Determinism

The API exposes no clock, no floating point and no randomness. The only input
is the replay. The same binary plus the same replay therefore yields the same
trace, a per-frame FNV-1a-64 of the framebuffer. The test suite builds with
gcc and clang and requires identical traces.

## Memory and transport (API-003)

ABI 0.2 has no transfer API. When one is added, it must expose transfer size,
timeout and error, and synchronization. It must not imply that F133, D213, 45F
and 12F share memory.
