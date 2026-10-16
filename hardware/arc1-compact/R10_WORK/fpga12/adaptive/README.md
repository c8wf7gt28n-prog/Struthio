# 12F adaptive mechanics service (ABI 1.0)

Status: **HOST_TESTED reference/fallback; RTL integration is not yet claimed.**

This gives the ECP5-12F a bounded, useful game-mechanics job while preserving the R10 ownership rule: the F133 owns
game state, submits a snapshot, and may run the same C function when the accelerator is absent or busy. The first job
is broad-phase collision for up to 128 axis-aligned bodies with 16 layer bits.

## Wire contract for opcode `0x0030` (`AABB_MATRIX`)

All fields are little-endian. The existing R10 12F request envelope and CRC remain unchanged.

| Request payload | Size |
|---|---:|
| ABI major, ABI minor, body count, flags | 4 x u16 |
| Each body: min_x, min_y, max_x, max_y (signed Q16.16), group, mask | 20 bytes |

The response begins with `count`, `row_stride`, `candidate_pairs`, `filtered_pairs`, and `overlapping_pairs`, followed by
the row-major collision bit matrix described in `include/arc1_mechanics.h`. At 128 bodies the input payload is 2,568
bytes and the matrix is 2,048 bytes, both below the existing 8 KiB request-buffer design point. Boxes use half-open
edges, so merely touching is not a collision. Invalid/empty boxes never collide.

The hardware target is a small iterative comparator: 8,128 unordered pairs at the maximum batch, one pair issued per
clock after body load. This is deliberately a broad-phase result rather than authoritative contact resolution; the
F133 consumes the matrix and performs narrow phase and gameplay decisions.

Run `make all` for the native reference, ASan/UBSan, freestanding compilation, exhaustive matrix invariants, randomized
cross-checks, and a mutation test that proves edge-touch semantics are actually exercised.
