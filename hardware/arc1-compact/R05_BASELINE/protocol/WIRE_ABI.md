# ARC1 proposed wire ABI v1

State: implemented and tested as portable host software. Physical transport,
F133 firmware, FPGA RTL endpoint, timing and recovery hardware are not implemented
or validated by this directory. Changing the wire layout or semantics requires an
explicit protocol-version decision, not a silently changed decoder.

## Byte layout

All multi-byte integers are unsigned **little endian**. Native C struct layout is
never transmitted. A complete frame is 20 header bytes, 0–4096 payload bytes and a
four-byte CRC: **24–4120 bytes** total.

| Offset | Bytes | Meaning |
|---|---:|---|
| 0 | 4 | ASCII `ARC1` (`41 52 43 31`) |
| 4 | 1 | Version, exactly 1 |
| 5 | 1 | Type, one of the four values below |
| 6 | 2 | Flags, exactly 0; reserved |
| 8 | 2 | Payload length, at most 4096 |
| 10 | 2 | Header length, exactly 20 |
| 12 | 4 | Epoch |
| 16 | 4 | Sequence |
| 20 | length | Payload |
| 20 + length | 4 | CRC32/ISO-HDLC, little endian |

CRC covers **every header byte, including magic, followed by payload**, excluding
the CRC trailer. Polynomial 0x04C11DB7 (reflected implementation 0xEDB88320), reflected
input/output, initial 0xFFFFFFFF and final XOR 0xFFFFFFFF. ASCII `123456789` gives
0xCBF43926. CRC detects corruption; it does not authenticate a sender.

| Type | Value | Envelope constraints |
|---|---:|---|
| HELLO | 0x01 | Nonzero epoch; sequence 0; empty payload |
| JOB | 0x10 | Nonzero epoch and sequence; 1–4096 payload bytes |
| STATUS | 0x80 | Exactly 8 payload bytes; header identifies current receiver epoch and echoes request sequence |
| RESULT | 0x81 | Nonzero epoch and sequence; 0–4096 opaque application-output bytes |

JOB and RESULT payload versions, record formats, numeric limits and validation are
application contracts. The codec does not understand scene commands or treat a valid
CRC as a valid job. An application-invalid accepted job must produce an application
error result and complete, releasing its transport credit. Correcting a job requires
a new sequence; changing bytes under an accepted sequence is a duplicate conflict.

## Status and receiver state

STATUS payload is `status:u16, available_credits:u16, next_sequence:u32`. Credits
are an **absolute snapshot** of free request slots. Capacity is fixed per receiver
session object at initialization, 1–8 slots. No additive credit update is defined.
`next_sequence=0` means either no session exists, or sequence UINT32_MAX has been
accepted and a new epoch is required. Header epoch distinguishes those states.
`arc1_read_status` rejects unknown status codes, credits above 8 and inconsistent
unbound-epoch statuses. A host must also reject credit counts above its negotiated
implementation capacity; explicit capability negotiation is not implemented yet.

| Status | Value | Effect |
|---|---:|---|
| OK | 0 | HELLO accepted or same-epoch HELLO query; no job dispatched |
| ACCEPTED | 1 | Dispatch exactly once; consumes one slot and advances sequence |
| DONE | 2 | Completion releases that slot once |
| DUPLICATE_PENDING | 3 | Same retained request is already pending; no dispatch/credit change |
| DUPLICATE_DONE | 4 | Same retained request already completed; replay retained application result |
| NO_SESSION | 16 | HELLO required |
| EPOCH | 17 | Wrong/stale epoch; no state change |
| SEQUENCE | 18 | Gap/future sequence; no state change |
| NO_CREDIT | 19 | Expected next job cannot currently fit; retry unchanged after completion |
| REPLAY_TOO_OLD | 20 | Old request record evicted; never execute it again |
| DUPLICATE_CONFLICT | 21 | Retained sequence with different original payload bytes |
| BUSY | 22 | New-epoch reset refused while work remains pending |
| SEQUENCE_EXHAUSTED | 23 | New epoch required; sequence never wraps |
| INVALID_REQUEST | 24 | Wrong request type/shape or invalid API arguments |
| UNKNOWN_JOB | 25 | Completion refers to no retained job |

The generic frame codec does not interpret the eight STATUS payload bytes; it only
checks their length. Typed consumers must invoke `arc1_read_status` as well.

1. `HELLO(epoch, seq=0)` starts an inactive receiver with next sequence 1.
2. Same-epoch HELLO is idempotent: it returns current state, even with pending jobs.
   It never resets the queue or recredits work.
3. A strictly **larger** epoch starts a fresh session only after all outstanding
   work has completed/quiesced. A lower epoch is rejected. Epochs do not wrap.
4. JOBs arrive in exact sequence order. Request bytes are copied into fixed receiver
   storage before ACCEPTED. Up to capacity jobs may remain outstanding.
5. Exact retained duplicate payloads return pending/done without execution. Payload
   comparison is byte-for-byte, not only CRC comparison. Completion order may differ
   from acceptance order; each pending job releases one credit at most once.
6. Completed records can be evicted to accept new work; an older sequence can never
   become new work. Results are retained/replayed by the application, not this codec.
7. Acceptance of sequence 0xFFFFFFFF exhausts the sequence space; subsequent new work
   requires a larger epoch after pending jobs finish. Repeated retained final jobs
   still return their duplicate status. Exhausting epoch space requires a documented
   independent receiver reset/recovery procedure, not counter wrap.

Receiver state is volatile. After receiver power/reset, a new HELLO handshake and
application recovery are required; cross-reset exactly-once execution is not claimed.
The library has no force-abort operation: a permanently hung job needs a separately
designed watchdog/reset path. CPU restart, stale physical queues, output retention,
SPI transaction synchronization, capacity negotiation and complete recovery remain
firmware/RTL integration work. No synthetic test establishes those physical paths.

## Decoder and stream behavior

`arc1_decode` accepts exactly one frame; it rejects trailing bytes and concatenation.
It checks fixed fields and length bounds before accessing payload/CRC. Invalid
outputs are cleared, rather than retaining a stale decoded payload pointer. Encoder
lengths use `size_t`, are bounded before arithmetic/casts, and report zero bytes
written on failure. `arc1_encode` supports overlapping payload/output storage.

The optional incremental parser has one fixed 4120-byte buffer. It accepts arbitrary
chunks, including byte-at-a-time input, and synchronously invokes a callback for each
complete valid frame. Invalid headers/CRCs cause a one-byte slide followed by a new
magic search, preserving potentially valid following frames. Magic bytes inside a
valid payload are ordinary payload data. CRC validity is required before delivery.

A plausible corrupted length can hold a partial candidate until enough bytes arrive.
Therefore the physical integration must provide a known transaction boundary or a
separately chosen timeout and call `arc1_parser_finish` to discard incomplete tails.
The library invents no SPI timing limit. Finish returns the discarded byte count;
parser counters report accepted candidates, rejected candidates and discarded bytes,
not measured wire transactions or throughput. Corruption resynchronization is not a
security boundary, and execution must still pass session/application validation.

## Ownership and memory bounds

No pointers or shared-memory addresses travel in this envelope. CPU RAM, T35 DDR
and BT graphics DDR remain separately owned. The session's fixed storage retains up
to eight full request payloads (32 KiB plus metadata); parser storage is about 4 KiB.
Use `sizeof` / `arc1_session_size()` for the host ABI's actual allocation. An FPGA
implementation must budget its own queues and verify timing/resources independently.

Only one owner may mutate a session/parser. API structures use native alignment and
are not a stable binary ABI across compilers; the serialized frame above is the wire
ABI. C input buffers must be valid for the claimed lengths. A session request's
payload must not alias the session's own mutable record storage.

The proposed 85-record, 48-byte application batch plus its 8-byte application header
uses 4088 payload bytes and 4112 wire bytes. This is capacity arithmetic only. No SPI
payload rate, FPGA speedup, frame cadence or hardware latency is measured here.
