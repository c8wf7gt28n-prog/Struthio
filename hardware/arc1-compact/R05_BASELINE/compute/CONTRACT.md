# Proposed compute contract v1

This is a rectangle transform/culling primitive for the selected Compact CPU/FPGA
split. It is implemented in portable C11 and synthesizable SystemVerilog. It is
not a BT820 driver, inverse bitmap-matrix converter, perspective renderer, SPI
PHY, FPGA board project or proof of acceleration.

## Math and visibility

All four rectangle bounds and six affine coefficients are signed 32-bit Q16.16.
Bounds describe a **closed** local rectangle; zero-area rectangles are legal.
Evaluate all four corners with the following equations in exact integer units:

```
acc_x = m00*x + m01*y + m02*65536
acc_y = m10*x + m11*y + m12*65536
```

Products and translation are summed **before** rounding. Round each accumulator
once by dividing by 65536 to the nearest integer, with exact half ties away from
zero; then saturate to [-2147483648, 2147483647]. The resulting coordinates are
still signed Q16.16, not integer pixel positions. RTL uses a signed 66-bit sum.
C uses checked int64 additions and a proven saturation shortcut if they overflow:
an overflowing two-product sum has magnitude at least 2^63, while the translation
has magnitude at most 2^47; their final result must still saturate at output.
Neither implementation discards the low bits of each product before summing.

Return componentwise min/max of the four rounded/saturated corners. Set:

- Bit 0 `VISIBLE`: AABB intersects the closed viewport [0,width] × [0,height].
- Bit 1 `SATURATED`: at least one transformed coordinate exceeded output range
  after rounding and was clamped.
- Bit 2 `INVALID`: inverted x/y bounds, or zero viewport width/height. Return zero
  bounds, only INVALID set, and the unchanged tag.

Viewport width/height are unsigned 16-bit **integer pixel** dimensions, 1–65535.
Comparison uses wider arithmetic, so dimensions above 32767 do not wrap negative.
Boundary-touching boxes deliberately remain visible. This conservative culler
can return false positives for rotated/sheared rectangles and for clamped or
subpixel bounds; a visible result is not a promise that a pixel will be drawn.
Monotonic round/clamp and closed boundaries avoid rounding an intersecting exact
AABB into a false rejection. This is broad-phase culling, not polygon clipping.

## C interface and transport boundary

`arc1_transform.h` exposes `arc1_transform_rectangle` and `arc1_transform_batch`.
Pointers must address valid objects; input/output arrays must not overlap. Count
zero permits null pointers and performs no accesses. The implementation has no
allocation, global mutable state, floating point, signed overflow or negative
shift dependency. Native C job/result layouts are compile-time checked at 48/24
bytes. Host byte order is not a wire format: serialize each integer explicitly.

Job field order: xmin,ymin,xmax,ymax,m00,m01,m02,m10,m11,m12 (ten i32), viewport
width,height (two u16), tag (u32). Result: tag(u32), minx,miny,maxx,maxy (four i32),
flags(u32). Flags bits 31:3 are zero. The root project owns any batch packet header,
CRC/framing, SPI/IRQ engine and address-window/epoch protocol.

## RTL cycle contract

`rtl/arc1_transform.sv` has synchronous active-high reset and ready/valid ports.
Input acceptance occurs only on a rising edge with in_valid && in_ready. The
producer must hold valid and every input field while stalled. All job fields are
latched at acceptance; changes after acceptance do not affect that transaction.

One transaction is in flight. The arithmetic evaluates x then y for corners
(xmin,ymin), (xmax,ymin), (xmin,ymax), (xmax,ymax): eight calculation cycles after
acceptance. out_valid asserts after the eighth calculation edge; it can first be
consumed at the following rising edge. Invalid inputs produce a result immediately
after their acceptance edge. An output transfers only on out_valid && out_ready;
all output fields and valid remain stable while stalled. An old output can retire
on the same edge a new job is accepted. Reset cancels work and held output, clears
valid, and has priority over both handshakes. The system must account for canceled
jobs through its own reset/epoch contract.

Two 32×32 products are described in the reused datapath; actual multiplier
inference, device resource fit, clock rate, throughput and power remain unknown
until synthesis/placement/timing and measurement. The testbench clock is an
arbitrary simulation clock, not a selected FPGA operating frequency.

## Reproducible verification

Run `make check-c` for strict-warning C builds, an undefined-behavior-sanitized C
vector runner and scalar/batch ctypes comparisons. Python's independent oracle
uses unbounded integers, with 15 hand-checked edge cases plus seeded random full
range, gameplay-sized, tie/near-limit and invalid cases (1165 total). The generator
does not call the C or RTL implementation. Native C layout checks are included.

Run `make check-hdl IVERILOG=/path/to/iverilog VVP=/path/to/vvp` when Icarus is
available. Its scoreboard uses the independent oracle vectors; it checks exact
results/order, input/output hold behavior, input gaps, random/forced output stalls,
simultaneous retirement/acceptance, and reset during computation and while a result
is held. A watchdog and result accounting reject dropped/duplicate transactions.
The actual executed outcomes belong in VERIFICATION.md; commands listed here are
instructions, not evidence that a tool ran.
