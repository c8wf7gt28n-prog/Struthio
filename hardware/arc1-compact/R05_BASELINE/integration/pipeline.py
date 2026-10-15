"""Host-only codec/session/compute model. This is not SPI or FPGA firmware."""
from __future__ import annotations

import ctypes as C
from collections import OrderedDict
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
HEADER = struct.Struct("<4H")
JOB = struct.Struct("<10i2HI")
RESULT = struct.Struct("<I4iI")
MAX_OBJECTS = (4096 - HEADER.size) // JOB.size


class Packet(C.Structure):
    _fields_ = [("type", C.c_uint8), ("epoch", C.c_uint32),
                ("sequence", C.c_uint32), ("payload", C.POINTER(C.c_uint8)),
                ("payload_length", C.c_size_t)]


class Reply(C.Structure):
    _fields_ = [("status", C.c_uint16), ("credits", C.c_uint16),
                ("next_sequence", C.c_uint32), ("epoch", C.c_uint32),
                ("sequence", C.c_uint32)]


class TransformJob(C.Structure):
    _fields_ = [(n, C.c_int32) for n in
                ("xmin", "ymin", "xmax", "ymax", "m00", "m01", "m02",
                 "m10", "m11", "m12")] + [
                ("viewport_width", C.c_uint16), ("viewport_height", C.c_uint16),
                ("tag", C.c_uint32)]


class TransformResult(C.Structure):
    _fields_ = [("tag", C.c_uint32)] + [(n, C.c_int32) for n in
                ("minx", "miny", "maxx", "maxy")] + [("flags", C.c_uint32)]


class Native:
    def __init__(self):
        self.codec = C.CDLL(str(ROOT / "protocol/build/libarc1_protocol.so"))
        self.compute = C.CDLL(str(ROOT / "compute/build/libarc1_transform.so"))
        self.codec.arc1_encode.argtypes = [C.c_uint8, C.c_uint32, C.c_uint32,
                                          C.c_void_p, C.c_size_t, C.c_void_p,
                                          C.c_size_t, C.POINTER(C.c_size_t)]
        self.codec.arc1_encode.restype = C.c_int
        self.codec.arc1_decode.argtypes = [C.c_void_p, C.c_size_t, C.POINTER(Packet)]
        self.codec.arc1_decode.restype = C.c_int
        self.codec.arc1_session_size.restype = C.c_size_t
        self.codec.arc1_session_init.argtypes = [C.c_void_p, C.c_uint16]
        self.codec.arc1_session_init.restype = C.c_int
        self.codec.arc1_session_request.argtypes = [C.c_void_p, C.POINTER(Packet), C.POINTER(Reply)]
        self.codec.arc1_session_request.restype = C.c_uint16
        self.codec.arc1_session_complete.argtypes = [C.c_void_p, C.c_uint32, C.c_uint32, C.POINTER(Reply)]
        self.codec.arc1_session_complete.restype = C.c_uint16
        self.codec.arc1_status_payload.argtypes = [C.POINTER(Reply), C.c_void_p]
        self.codec.arc1_status_payload.restype = C.c_int
        self.compute.arc1_transform_batch.argtypes = [C.POINTER(TransformJob),
                                                      C.POINTER(TransformResult), C.c_size_t]
        self.compute.arc1_transform_batch.restype = None
        if C.sizeof(TransformJob) != JOB.size or C.sizeof(TransformResult) != RESULT.size:
            raise RuntimeError("Native ABI mismatch: do not copy wire structs")

    def encode(self, kind, epoch, sequence, payload=b""):
        for name, value, maximum in (("kind", kind, 255), ("epoch", epoch, 0xffffffff),
                                     ("sequence", sequence, 0xffffffff)):
            if type(value) is not int or not 0 <= value <= maximum:
                raise ValueError(f"{name} outside its unsigned wire range")
        source = C.create_string_buffer(payload)
        out = C.create_string_buffer(4120)
        written = C.c_size_t()
        error = self.codec.arc1_encode(kind, epoch, sequence, source, len(payload),
                                        out, len(out), C.byref(written))
        if error:
            raise ValueError(f"frame encode error {error}")
        return out.raw[:written.value]

    def decode_raw(self, frame):
        backing = C.create_string_buffer(frame)
        packet = Packet()
        error = self.codec.arc1_decode(backing, len(frame), C.byref(packet))
        if error:
            raise ValueError(f"frame decode error {error}")
        return packet, backing  # backing keeps borrowed payload alive

    def decode(self, frame):
        packet, backing = self.decode_raw(frame)
        return packet.type, packet.epoch, packet.sequence, C.string_at(packet.payload, packet.payload_length)


def pack_jobs(records):
    if not 1 <= len(records) <= MAX_OBJECTS:
        raise ValueError("job count outside 1..85")
    return HEADER.pack(1, 1, len(records), 0) + b"".join(JOB.pack(*r) for r in records)


def unpack_result(payload):
    if len(payload) < HEADER.size:
        raise ValueError("truncated result header")
    version, kind, count, status = HEADER.unpack_from(payload)
    if version != 1 or kind != 1 or count > MAX_OBJECTS or len(payload) != HEADER.size + count * RESULT.size:
        raise ValueError("invalid result shape")
    if status not in (0, 1, 2, 3, 4) or (status and count) or (status == 0 and count == 0):
        raise ValueError("invalid result application status")
    rows = [RESULT.unpack_from(payload, HEADER.size + i * RESULT.size) for i in range(count)]
    if any(row[-1] & ~7 for row in rows):
        raise ValueError("unknown result flag bits")
    return status, rows


class EndpointModel:
    """Synchronous software stand-in for a future firmware/RTL application.

    C session logic handles exactly-once admission. This application retains the
    latest eight outputs, stores before completion, and replays without executing.
    No actual SPI, IRQ, DMA, asynchronous queue or BT820 commands are implemented.
    """
    def __init__(self, native=None):
        self.native = native or Native()
        self.session = C.create_string_buffer(self.native.codec.arc1_session_size())
        if self.native.codec.arc1_session_init(self.session, 8):
            raise RuntimeError("session init failed")
        self.epoch = 0
        self.cache = OrderedDict()
        self.execution_batches = 0
        self.execution_objects = 0

    def _status(self, reply):
        out = C.create_string_buffer(8)
        if self.native.codec.arc1_status_payload(C.byref(reply), out):
            raise RuntimeError("status serialization failed")
        return self.native.encode(0x80, reply.epoch, reply.sequence, out.raw)

    def _execute(self, payload):
        if len(payload) < HEADER.size:
            return HEADER.pack(1, 1, 0, 1)
        version, kind, count, reserved = HEADER.unpack_from(payload)
        if version != 1:
            return HEADER.pack(1, 1, 0, 2)
        if kind != 1:
            return HEADER.pack(1, 1, 0, 3)
        if reserved or not 1 <= count <= MAX_OBJECTS or len(payload) != HEADER.size + count * JOB.size:
            return HEADER.pack(1, 1, 0, 1)
        jobs = (TransformJob * count)()
        results = (TransformResult * count)()
        for i in range(count):
            jobs[i] = TransformJob(*JOB.unpack_from(payload, HEADER.size + i * JOB.size))
        self.native.compute.arc1_transform_batch(jobs, results, count)
        self.execution_batches += 1
        self.execution_objects += count
        return HEADER.pack(1, 1, count, 0) + b"".join(
            RESULT.pack(r.tag, r.minx, r.miny, r.maxx, r.maxy, r.flags) for r in results)

    def process(self, frame):
        packet, backing = self.native.decode_raw(frame)
        reply = Reply()
        status = self.native.codec.arc1_session_request(self.session, C.byref(packet), C.byref(reply))
        responses = [self._status(reply)]
        if packet.type == 1 and status == 0:
            if self.epoch != packet.epoch:
                self.cache.clear()
                self.epoch = packet.epoch
            return responses
        key = packet.epoch, packet.sequence
        if status == 1:  # only ACCEPTED dispatches application work
            payload = self._execute(C.string_at(packet.payload, packet.payload_length))
            result = self.native.encode(0x81, packet.epoch, packet.sequence, payload)
            self.cache[key] = result
            while len(self.cache) > 8:
                self.cache.popitem(last=False)
            responses.append(result)
            if self.native.codec.arc1_session_complete(self.session, packet.epoch, packet.sequence, C.byref(reply)) != 2:
                raise RuntimeError("accepted job completion failed")
            responses.append(self._status(reply))
        elif status == 4:  # duplicate completed job: replay, never recompute
            responses.append(self.cache.get(key) or self.native.encode(
                0x81, packet.epoch, packet.sequence, HEADER.pack(1, 1, 0, 4)))
        return responses


def reference_scene():
    """256 deterministic objects; 64 quarter-turn transforms; known AABBs."""
    q = 65536
    records, expected = [], []
    for i in range(256):
        x, y = (i % 16) * 64, (i // 16) * 36
        if i % 11 == 0:
            x += 1280
        if i % 17 == 0:
            y -= 800
        matrix = (0, -q, (x + 32) * q, q, 0, y * q) if i % 4 == 0 else (q, 0, x * q, 0, q, y * q)
        records.append((0, 0, 32 * q, 32 * q, *matrix, 1024, 600, 1000 + i))
        visible = int(not (i % 11 == 0 or i % 17 == 0))
        expected.append((1000 + i, x * q, y * q, (x + 32) * q, (y + 32) * q, visible))
    return records, expected


def run_scene():
    native = Native()
    endpoint = EndpointModel(native)
    endpoint.process(native.encode(1, 1, 0))
    records, expected = reference_scene()
    results, request_bytes, response_bytes, first_frame = [], 0, 0, None
    sequence = 1
    for offset in range(0, len(records), MAX_OBJECTS):
        frame = native.encode(0x10, 1, sequence, pack_jobs(records[offset:offset + MAX_OBJECTS]))
        if first_frame is None:
            first_frame = frame
        replies = endpoint.process(frame)
        request_bytes += len(frame)
        response_bytes += sum(map(len, replies))
        for response in replies:
            kind, epoch, echoed, payload = native.decode(response)
            if kind == 0x81:
                status, rows = unpack_result(payload)
                if status or epoch != 1 or echoed != sequence:
                    raise RuntimeError("unexpected application result")
                results.extend(rows)
        sequence += 1
    if results != expected:
        raise RuntimeError("scene results disagree with independent known AABBs")
    before = endpoint.execution_batches
    retry = endpoint.process(first_frame)
    assert endpoint.execution_batches == before
    assert unpack_result(native.decode(retry[1])[3])[0] == 0
    return {
        "scope": "HOST_ONLY_C_CODEC_SESSION_AND_C_COMPUTE_REFERENCE",
        "objects": len(results), "transformed_objects": 64,
        "visible": sum(bool(r[-1] & 1) for r in results),
        "culled": sum(not (r[-1] & 1) for r in results),
        "job_batches": endpoint.execution_batches, "duplicate_reexecutions": 0,
        "request_bytes_per_frame": request_bytes,
        "response_bytes_per_frame": response_bytes,
        "total_bytes_per_frame": request_bytes + response_bytes,
        "calculated_60hz_protocol_mb_s": (request_bytes + response_bytes) * 60 / 1e6,
        "calculated_24mhz_single_bit_serial_wire_time_ms": (request_bytes + response_bytes) * 8 / 24e6 * 1000,
        "measured_spi_throughput": None, "measured_game_fps": None,
        "bt820_renderer_implemented": False, "hardware_verified": False,
        "notes": ["HELLO and retries excluded from steady per-frame byte budget.",
                  "Responses include ACCEPTED and DONE STATUS plus RESULT for each batch.",
                  "Calculation excludes transaction gaps, HAL, DMA, asset uploads and scheduling.",
                  "This scene exercises transforms/culling only; it does not draw parallax or pixels."]}


if __name__ == "__main__":
    import json
    print(json.dumps(run_scene(), indent=2))
