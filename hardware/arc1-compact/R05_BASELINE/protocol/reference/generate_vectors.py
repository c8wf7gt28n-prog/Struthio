"""Generate committed vectors using only the Python reference and stdlib.

Run from any directory: python3 protocol/reference/generate_vectors.py
No C implementation or compiled library is read or invoked.
"""

import json
from pathlib import Path
import struct
import zlib

from codec import HEADER, HELLO, JOB, RESULT, STATUS, encode


def malformed(*, magic=b"ARC1", version=1, packet_type=HELLO, flags=0,
              payload=b"", payload_length=None, header_length=20, epoch=1, sequence=0):
    """Build deliberate violations independently of encode's input validation."""
    if payload_length is None:
        payload_length = len(payload)
    body = HEADER.pack(magic, version, packet_type, flags, payload_length, header_length, epoch, sequence) + payload
    return body + struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF)


def vectors():
    valid = []
    for name, packet_type, epoch, sequence, payload in (
        ("hello_epoch_one", HELLO, 1, 0, b""),
        ("hello_max_epoch", HELLO, 0xFFFFFFFF, 0, b""),
        ("job_one_byte", JOB, 1, 1, b"\x00"),
        ("job_endian_probe", JOB, 0x12345678, 0x90ABCDEF, bytes(range(16))),
        ("job_max_payload", JOB, 0xFFFFFFFF, 0xFFFFFFFF, bytes(range(256)) * 16),
        ("status_unbound_epoch", STATUS, 0, 0, bytes(8)),
        ("status_bound_epoch", STATUS, 0x12345678, 0x90ABCDEF, bytes.fromhex("0102030480ff7f00")),
        ("result_empty", RESULT, 1, 1, b""),
        ("result_max_payload", RESULT, 0x10203040, 0x50607080, bytes(reversed(range(256))) * 16),
    ):
        valid.append({"name": name, "valid": True, "type": packet_type,
                      "epoch": epoch, "sequence": sequence, "payload_hex": payload.hex(),
                      "frame_hex": encode(packet_type, epoch, sequence, payload).hex()})
    hello = encode(HELLO, 1, 0)
    bad_crc = hello[:-1] + bytes((hello[-1] ^ 1,))
    invalid_specs = (
        ("empty", b"", "truncated"),
        ("truncated_header", hello[:19], "truncated"),
        ("missing_crc", hello[:-4], "truncated"),
        ("truncated_crc", hello[:-1], "truncated"),
        ("trailing_byte", hello + b"\x00", "length"),
        ("concatenated_frames", hello + hello, "length"),
        ("bad_crc", bad_crc, "checksum"),
        ("bad_magic", malformed(magic=b"arc1"), "magic"),
        ("bad_version", malformed(version=2), "version"),
        ("reserved_flags", malformed(flags=1), "flags"),
        ("big_endian_flags_probe", malformed(flags=0x100), "flags"),
        ("short_header_length", malformed(header_length=19), "header_length"),
        ("long_header_length", malformed(header_length=21), "header_length"),
        ("unknown_type", malformed(packet_type=0xFF), "type"),
        ("zero_type", malformed(packet_type=0), "type"),
        ("hello_zero_epoch", malformed(epoch=0), "shape"),
        ("hello_nonzero_sequence", malformed(sequence=1), "shape"),
        ("hello_payload", malformed(payload=b"x"), "shape"),
        ("job_empty", malformed(packet_type=JOB, sequence=1), "shape"),
        ("job_zero_epoch", malformed(packet_type=JOB, payload=b"x", epoch=0, sequence=1), "shape"),
        ("job_zero_sequence", malformed(packet_type=JOB, payload=b"x"), "shape"),
        ("status_short", malformed(packet_type=STATUS, payload=bytes(7)), "shape"),
        ("status_long", malformed(packet_type=STATUS, payload=bytes(9)), "shape"),
        ("result_zero_epoch", malformed(packet_type=RESULT, epoch=0, sequence=1), "shape"),
        ("result_zero_sequence", malformed(packet_type=RESULT), "shape"),
        ("declared_payload_over_limit", malformed(packet_type=JOB, payload_length=4097, sequence=1), "bound"),
        ("actual_payload_over_limit", malformed(packet_type=JOB, payload=bytes(4097), sequence=1), "bound"),
        ("declared_payload_truncated", malformed(packet_type=JOB, payload_length=2, payload=b"x", sequence=1), "length"),
        ("undeclared_payload", malformed(packet_type=RESULT, payload_length=0, payload=b"x", sequence=1), "length"),
    )
    invalid = [{"name": name, "valid": False, "reason_category": reason, "frame_hex": frame.hex()}
               for name, frame, reason in invalid_specs]
    return {"schema": "arc1-wire-golden-vectors-v1", "wire_version": 1,
            "generator": "reference/generate_vectors.py; Python struct and zlib only; no C execution",
            "crc_check": {"ascii": "123456789", "crc32_hex": "cbf43926"},
            "vectors": valid + invalid}


if __name__ == "__main__":
    target = Path(__file__).with_name("golden_vectors.json")
    target.write_text(json.dumps(vectors(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {target.name}")
