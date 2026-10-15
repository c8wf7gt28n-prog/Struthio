"""Independent wire-reference, golden-vector and C differential checks."""

import ctypes
import json
from pathlib import Path
import random
import struct
import sys
import unittest
import zlib


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))
import codec as reference  # noqa: E402
import generate_vectors  # noqa: E402


VECTORS = json.loads((ROOT / "reference" / "golden_vectors.json").read_text(encoding="utf-8"))
LIBRARY = ROOT / "build" / "libarc1_protocol.so"


def sample_packets(count=512):
    rng = random.Random(0xA1C12026)
    boundaries = [0, 1, 7, 8, 9, 255, 256, 4095, 4096]
    for index in range(count):
        packet_type = rng.choice(sorted(reference.TYPES))
        epoch = rng.randrange(1, 1 << 32)
        sequence = rng.randrange(1, 1 << 32)
        length = boundaries[index % len(boundaries)] if index < 90 else rng.randrange(4097)
        if packet_type == reference.HELLO:
            sequence, length = 0, 0
        elif packet_type == reference.STATUS:
            epoch = rng.randrange(1 << 32)
            sequence = rng.randrange(1 << 32)
            length = 8
        elif packet_type == reference.JOB:
            length = max(1, length)
        payload = bytes(rng.randrange(256) for _ in range(length))
        yield reference.Packet(packet_type, epoch, sequence, payload)


class ReferenceTests(unittest.TestCase):
    def test_crc_standard_check(self):
        self.assertEqual(zlib.crc32(b"123456789"), 0xCBF43926)

    def test_header_layout(self):
        self.assertEqual(reference.HEADER.size, 20)
        self.assertEqual(reference.encode(reference.HELLO, 1, 0)[:20],
                         bytes.fromhex("4152433101010000000014000100000000000000"))

    def test_golden_vectors_are_reproducible(self):
        self.assertEqual(VECTORS, generate_vectors.vectors())

    def test_golden_vectors(self):
        for vector in VECTORS["vectors"]:
            with self.subTest(vector=vector["name"]):
                frame = bytes.fromhex(vector["frame_hex"])
                if vector["valid"]:
                    packet = reference.Packet(vector["type"], vector["epoch"], vector["sequence"],
                                              bytes.fromhex(vector["payload_hex"]))
                    self.assertEqual(reference.decode(frame), packet)
                    self.assertEqual(reference.encode(packet.type, packet.epoch, packet.sequence, packet.payload), frame)
                else:
                    with self.assertRaises(reference.ProtocolError):
                        reference.decode(frame)

    def test_deterministic_random_roundtrip(self):
        for packet in sample_packets():
            self.assertEqual(reference.decode(reference.encode(packet.type, packet.epoch,
                                                               packet.sequence, packet.payload)), packet)

    def test_encoder_semantic_rejections(self):
        invalid = [
            (reference.HELLO, 0, 0, b""), (reference.HELLO, 1, 1, b""),
            (reference.HELLO, 1, 0, b"x"), (reference.JOB, 1, 1, b""),
            (reference.JOB, 0, 1, b"x"), (reference.JOB, 1, 0, b"x"),
            (reference.JOB, 1, 1, bytes(4097)), (reference.STATUS, 0, 0, bytes(7)),
            (reference.STATUS, 0, 0, bytes(9)), (reference.RESULT, 0, 1, b""),
            (reference.RESULT, 1, 0, b""), (0xFF, 1, 0, b""),
        ]
        for args in invalid:
            with self.subTest(args=args[:3], length=len(args[3])):
                with self.assertRaises(reference.ProtocolError):
                    reference.encode(*args)
        for value in [-1, 1 << 32, True, 1.5]:
            with self.subTest(epoch=value):
                with self.assertRaises(reference.ProtocolError):
                    reference.encode(reference.HELLO, value, 0)

    def test_all_max_frame_prefixes_rejected(self):
        frame = reference.encode(reference.JOB, 1, 1, bytes(range(256)) * 16)
        self.assertEqual(len(frame), 4120)
        for length in range(len(frame)):
            with self.subTest(length=length):
                with self.assertRaises(reference.ProtocolError):
                    reference.decode(frame[:length])


class CPacket(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint8), ("epoch", ctypes.c_uint32),
                ("sequence", ctypes.c_uint32), ("payload", ctypes.POINTER(ctypes.c_uint8)),
                ("payload_length", ctypes.c_size_t)]


@unittest.skipUnless(LIBRARY.is_file(), "build protocol/build/libarc1_protocol.so for C differential checks")
class CReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = ctypes.CDLL(str(LIBRARY))
        uint8_pointer = ctypes.POINTER(ctypes.c_uint8)
        cls.library.arc1_encode.argtypes = [ctypes.c_uint8, ctypes.c_uint32, ctypes.c_uint32,
                                           uint8_pointer, ctypes.c_size_t, uint8_pointer,
                                           ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        cls.library.arc1_encode.restype = ctypes.c_int
        cls.library.arc1_decode.argtypes = [uint8_pointer, ctypes.c_size_t, ctypes.POINTER(CPacket)]
        cls.library.arc1_decode.restype = ctypes.c_int

    def c_encode(self, packet, capacity=4120):
        source = (ctypes.c_uint8 * len(packet.payload)).from_buffer_copy(packet.payload)
        output = (ctypes.c_uint8 * max(capacity, 1))()
        output_length = ctypes.c_size_t(0)
        status = self.library.arc1_encode(packet.type, packet.epoch, packet.sequence, source,
                                          len(packet.payload), output, capacity, ctypes.byref(output_length))
        return status, bytes(output[:output_length.value]) if status == 0 else b""

    def c_decode(self, frame):
        source = (ctypes.c_uint8 * len(frame)).from_buffer_copy(frame)
        output = CPacket()
        status = self.library.arc1_decode(source, len(frame), ctypes.byref(output))
        if status != 0:
            return status, None
        self.assertLessEqual(output.payload_length, 4096)
        return status, reference.Packet(output.type, output.epoch, output.sequence,
                                        ctypes.string_at(output.payload, output.payload_length))

    def assert_decode_agrees(self, frame):
        try:
            expected = reference.decode(frame)
        except reference.ProtocolError:
            status, _ = self.c_decode(frame)
            self.assertNotEqual(status, 0)
        else:
            status, packet = self.c_decode(frame)
            self.assertEqual(status, 0)
            self.assertEqual(packet, expected)

    def test_c_golden_vectors(self):
        for vector in VECTORS["vectors"]:
            with self.subTest(vector=vector["name"]):
                frame = bytes.fromhex(vector["frame_hex"])
                self.assert_decode_agrees(frame)
                if vector["valid"]:
                    expected = reference.decode(frame)
                    status, actual = self.c_encode(expected)
                    self.assertEqual(status, 0)
                    self.assertEqual(actual, frame)

    def test_c_deterministic_random_roundtrip(self):
        for index, packet in enumerate(sample_packets(1024)):
            with self.subTest(index=index, packet_type=packet.type, length=len(packet.payload)):
                frame = reference.encode(packet.type, packet.epoch, packet.sequence, packet.payload)
                status, actual = self.c_encode(packet)
                self.assertEqual(status, 0)
                self.assertEqual(actual, frame)
                self.assert_decode_agrees(frame)

    def test_c_capacity_boundaries(self):
        for packet in sample_packets(36):
            expected = reference.encode(packet.type, packet.epoch, packet.sequence, packet.payload)
            for capacity in sorted(set((0, 1, 19, 20, 23, len(expected) - 1, len(expected), len(expected) + 1))):
                with self.subTest(packet_type=packet.type, length=len(packet.payload), capacity=capacity):
                    status, actual = self.c_encode(packet, capacity)
                    if capacity < len(expected):
                        self.assertNotEqual(status, 0)
                    else:
                        self.assertEqual(status, 0)
                        self.assertEqual(actual, expected)

    def test_c_semantic_encode_rejections(self):
        for vector in VECTORS["vectors"]:
            if vector.get("reason_category") not in ("shape", "type", "bound"):
                continue
            frame = bytes.fromhex(vector["frame_hex"])
            if len(frame) < 24:
                continue
            _, _, packet_type, _, _, _, epoch, sequence = reference.HEADER.unpack_from(frame)
            # A declared-over-limit vector has a small actual payload; validate
            # the declared length in decode tests, not via this encode call.
            if vector["name"] == "declared_payload_over_limit":
                continue
            with self.subTest(vector=vector["name"]):
                status, _ = self.c_encode(reference.Packet(packet_type, epoch, sequence, frame[20:-4]))
                self.assertNotEqual(status, 0)

    def test_c_every_max_frame_truncation(self):
        frame = reference.encode(reference.JOB, 1, 1, bytes(range(256)) * 16)
        for length in range(len(frame)):
            with self.subTest(length=length):
                status, _ = self.c_decode(frame[:length])
                self.assertNotEqual(status, 0)

    def test_c_mutations_and_trailing_bytes(self):
        rng = random.Random(0xC32A1C1)
        for index, packet in enumerate(sample_packets(128)):
            frame = reference.encode(packet.type, packet.epoch, packet.sequence, packet.payload)
            for _ in range(8):
                position = rng.randrange(len(frame))
                changed = bytearray(frame)
                changed[position] ^= 1 << rng.randrange(8)
                with self.subTest(index=index, position=position):
                    self.assert_decode_agrees(bytes(changed))
            self.assert_decode_agrees(frame + b"\x00")
            self.assert_decode_agrees(frame + frame)

    def test_c_reserved_header_fields_with_valid_crc(self):
        baseline = reference.encode(reference.RESULT, 1, 1, b"payload")
        for offset, replacement in ((4, 0), (4, 2), (5, 0), (5, 0x82),
                                    (6, 1), (7, 0x80), (10, 19), (10, 21), (11, 1)):
            changed = bytearray(baseline[:-4])
            changed[offset] = replacement
            frame = bytes(changed) + struct.pack("<I", zlib.crc32(changed) & 0xFFFFFFFF)
            with self.subTest(offset=offset, replacement=replacement):
                self.assert_decode_agrees(frame)


if __name__ == "__main__":
    unittest.main()
