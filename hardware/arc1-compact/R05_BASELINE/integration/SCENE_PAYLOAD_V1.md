# Transform-job application payload v1 — proposed software ABI

This payload sits inside the separately documented ARC1 transport JOB/RESULT.
It is not a BT820 command stream, SPI PHY or final game ABI. Multi-byte fields
are explicitly little-endian; native C structs are never copied onto the wire.

JOB starts with four u16 values: version = 1, kind = 1 (rectangle transform/cull),
count = 1..85, reserved = 0. Each 48-byte record contains xmin/ymin/xmax/ymax,
m00/m01/m02/m10/m11/m12 (ten signed i32 Q16.16 values), viewport width/height
(two u16 integer pixels), then tag (u32). Exact length is 8 + 48 * count.

RESULT starts with four u16 values: version = 1, kind = 1, count, application status.
Each 24-byte record is tag (u32), minx/miny/maxx/maxy (signed i32 Q16.16), flags (u32).
Flags: visible = 1, saturated = 2, invalid geometry = 4. Status 0 means successful
application decoding; individual invalid rectangles are reported in flags.
Statuses 1/2/3 mean malformed payload/unsupported application version/unknown
kind. Status 4 means a completed job's cached result is unavailable. Error
statuses have count 0. Results are conservative bounds, not BT inverse sampling
coefficients; use the compute contract for exact rounding and culling rules.

The software endpoint stores an output before releasing the transport credit.
Completed duplicates replay a retained output and never re-execute. Cache loss
returns status 4. A new accepted epoch clears application cache; same-epoch HELLO
does not. The model retains eight outputs, matching the transport retention
window. The future asynchronous firmware/RTL must implement equivalent ownership,
capacity, result retention and fault behavior; the synchronous model does not
prove those hardware properties.

The deterministic integration scene has 256 objects, 64 quarter-turn transforms,
218 conservative visible bounds and 38 culled bounds. Four jobs carry 85/85/85/1
objects. Steady traffic is 12,416 request bytes and 6,528 response bytes per scene,
including two status frames per batch, excluding HELLO/retries. At 60 scenes/s this
is 1.13664 MB/s calculated payload/framing traffic, or 6.3147 ms of serialized bits at
24 MHz single-bit SPI before gaps or other work. Neither actual SPI throughput nor
game/render frame rate was measured. This scene transforms bounds only; it does
not draw pixels, four parallax layers or run STRUTHIO.

Build the C libraries with `make -C protocol all` and `make -C compute all`.
Run `python3 integration/pipeline.py` for the JSON report and
`python3 -m unittest discover -s integration -p 'test_pipeline.py' -v` for the
cross-component checks.
