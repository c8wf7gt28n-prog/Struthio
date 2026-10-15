# Compact scene/job transport — proposed ABI v1

This directory contains portable C framing, incremental parsing and receiver session
logic, plus an independent standard-library Python wire reference. It is working
host software, not an F133 firmware image, SPI HAL, FPGA endpoint or hardware test.
The ABI is an implementation proposal for Compact; no Tabletop memory/storage
topology is imported.

From this directory:

```sh
make test
make sanitize
```

`make all` builds `build/libarc1_protocol.so` for host integration and the C test
executable. The C API is [include/arc1_protocol.h](include/arc1_protocol.h); it uses
fixed storage and no heap allocation, platform I/O or OS calls. The core requires
only integer types and C library memory operations. The Makefile/shared-library
target is for the current POSIX host; the C source can be compiled separately into
embedded firmware. No firmware toolchain/linker/startup is supplied here.

Read [WIRE_ABI.md](WIRE_ABI.md) before integrating. The application JOB and RESULT
payloads are deliberately separate from framing. The C decoder returns a borrowed
payload view; consume or copy it before changing its input buffer. Parser callbacks
must consume/copy before return and must not re-enter the same parser. Session
operations require one serialized owner.

Only `ARC1_STATUS_ACCEPTED` permits one application dispatch. Call
`arc1_session_complete` after the accepted operation has finished and any result
needed for replay has been retained by the application. Duplicate requests never
authorize another execution. The session stores original request bytes, not result
bytes: the application must replay retained outputs or explicitly report that a
completed result is unavailable. It must not silently re-execute an evicted result.

Generic frame validation checks STATUS length, while `arc1_read_status` performs
typed status/credit validation. Call both when receiving STATUS. Credits are absolute
snapshots, not increments. The host/physical HAL must associate ordered responses,
bound waits and drive SPI clocks; this library implements none of those I/O duties.

The independent [Python reference](reference/README.md) supplies committed valid and
invalid vectors and differential tests. [TEST_REPORT.md](TEST_REPORT.md) records
executed checks and limits. Sanitizer tests disable LeakSanitizer by default because
this execution environment runs under ptrace; AddressSanitizer and
UndefinedBehaviorSanitizer remain enabled. The core/test use no heap allocation.
On a compatible host, `make sanitize SANITIZER_OPTIONS=detect_leaks=1` opts into
LeakSanitizer; no leak-scan pass is claimed here.
