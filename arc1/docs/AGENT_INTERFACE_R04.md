# ARC-1 Workbench — Agent Interface v1

This is the **second user interface**, intended for AI coding agents and automation, distinct from the human-oriented Windows File Manager/Word 6 interface. Both manipulate the same ARC-1 project tree and invoke the same `arc1` build/test CLI. No UI coordinate automation or network service is necessary.

## Start on Windows 11

```
py -3 arc1 agent
```

The process listens to JSON objects, one per line on stdin, and returns one JSON object per line on stdout. The transport is **stdio**, not HTTP or a Windows COM port. stdout contains only protocol replies. Exit by closing stdin. Example:

```
{"id":1,"method":"hello"}
{"id":2,"method":"files.list","params":{"path":"firmware/stage"}}
{"id":3,"method":"files.read","params":{"path":"firmware/stage/f133_stage.c"}}
{"id":4,"method":"build.both"}
{"id":5,"method":"test.firmware"}
{"id":6,"method":"status"}
```

Response: `{"id":1,"ok":true,"result":{...}}`. Errors: `{"id":1,"ok":false,"error":{"message":"..."}}`. There is no arbitrary command execution, no physical flash command, and no autonomous permissions escalation.

## Source edits

By default the endpoint is **read-only** for source writes. To opt in explicitly:

```
py -3 arc1 agent --allow-writes
```

Read the file first to obtain `sha256`, then call `files.write` with its complete replacement `content` and `expected_sha256`. A mismatched SHA prevents clobbering a concurrent human edit. Source edits are restricted to existing text files under selected SDK, firmware, example and Workbench directories. Binary files, outside paths, symlinks, and whole-hardware-source rewrites are refused. The operator controls whether to launch a write-enabled process.

## API inventory

`hello`, `capabilities`, `status`, `files.list`, `files.read`, `files.write`, `build.f133`, `build.d213`, `build.both`, `build.lcd`, `test.firmware`, `test.game`, `build.game`, `inspect.hardware`, `inspect.brand`, `doctor`, `boot.simulate`.

`boot.simulate` accepts `{"events":["f133","nor","d213","fpga12","fpga45","ready"]}` and returns a host-only LCD snapshot. Inputs must meet prerequisites, and no physical hardware is involved.

The build tools generate non-bootable freestanding RISC-V link-stage binaries. Responses preserve underlying SDK evidence labels. Future expansions should add explicit version negotiation, transaction logs, machine-readable diagnostics, finer-grained capabilities, concurrency locks, signed artifact identity and a separately authorized real-device adapter **after** bring-up validation. Never infer hardware readiness from successful host builds.

## R06 agent extension

`cartridge.package`: package fixed `examples/hello_arc1` into the local cartridges shelf; requires `--allow-writes`.

`cartridge.inspect`: optional `params.path`, default `cartridges/hello_arc1.arc1cart`. Restricted to `cartridges/`.

`cartridge.stream`: optional `params.path`, plus `frames`, `bandwidth_mib_s`, `latency_ms`, `chunk_bytes`, `prefetch_frames`, `consumption_bytes_per_frame`. Returns a deterministic model with `physical_usb_tested=false` and `sustained_60fps_proven=false`.
