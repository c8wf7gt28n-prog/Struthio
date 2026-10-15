"""Independent, standard-library ARC1 proposed wire-format reference.

This is a host software model. It does not implement or verify SPI, FPGA RTL,
firmware boot, display transport, or any hardware behavior.
"""

from dataclasses import dataclass
import struct
import zlib


MAGIC = b"ARC1"
VERSION = 1
HEADER = struct.Struct("<4sBBHHHII")
CHECKSUM = struct.Struct("<I")
HEADER_LENGTH = 20
MAX_PAYLOAD_LENGTH = 4096
HELLO = 0x01
JOB = 0x10
STATUS = 0x80
RESULT = 0x81
TYPES = frozenset((HELLO, JOB, STATUS, RESULT))


class ProtocolError(ValueError):
    """A packet does not satisfy the proposed wire contract."""


@dataclass(frozen=True)
class Packet:
    type: int
    epoch: int
    sequence: int
    payload: bytes


def _unsigned(name: str, value: int, bits: int) -> None:
    if type(value) is not int or not 0 <= value < (1 << bits):
        raise ProtocolError(f"{name} must be an unsigned {bits}-bit integer")


def _shape(packet_type: int, epoch: int, sequence: int, payload_length: int) -> None:
    _unsigned("type", packet_type, 8)
    _unsigned("epoch", epoch, 32)
    _unsigned("sequence", sequence, 32)
    if packet_type not in TYPES:
        raise ProtocolError("unknown packet type")
    if not 0 <= payload_length <= MAX_PAYLOAD_LENGTH:
        raise ProtocolError("payload exceeds the 4096-byte bound")
    if packet_type == HELLO:
        if payload_length != 0 or sequence != 0 or epoch == 0:
            raise ProtocolError("HELLO requires an empty payload, nonzero epoch and sequence zero")
    elif packet_type == STATUS:
        if payload_length != 8:
            raise ProtocolError("STATUS requires exactly eight payload bytes")
    else:
        if epoch == 0 or sequence == 0:
            raise ProtocolError("JOB and RESULT require nonzero epoch and sequence")
        if packet_type == JOB and payload_length == 0:
            raise ProtocolError("JOB requires a nonempty payload")


def encode(packet_type: int, epoch: int, sequence: int, payload: bytes = b"") -> bytes:
    """Encode one complete frame with a little-endian CRC32/ISO-HDLC trailer."""
    if not isinstance(payload, (bytes, bytearray, memoryview)):
        raise TypeError("payload must be bytes-like")
    payload = bytes(payload)
    _shape(packet_type, epoch, sequence, len(payload))
    header = HEADER.pack(MAGIC, VERSION, packet_type, 0, len(payload), HEADER_LENGTH, epoch, sequence)
    body = header + payload
    return body + CHECKSUM.pack(zlib.crc32(body) & 0xFFFFFFFF)


def decode(data: bytes) -> Packet:
    """Decode exactly one frame; reject prefixes, concatenation and trailing bytes."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("frame must be bytes-like")
    data = bytes(data)
    if len(data) < HEADER_LENGTH + CHECKSUM.size:
        raise ProtocolError("truncated header or checksum")
    magic, version, packet_type, flags, payload_length, header_length, epoch, sequence = HEADER.unpack_from(data)
    if magic != MAGIC:
        raise ProtocolError("bad magic")
    if version != VERSION:
        raise ProtocolError("unsupported version")
    if flags != 0:
        raise ProtocolError("reserved flags must be zero")
    if header_length != HEADER_LENGTH:
        raise ProtocolError("header length must be twenty bytes")
    _shape(packet_type, epoch, sequence, payload_length)
    if len(data) != HEADER_LENGTH + payload_length + CHECKSUM.size:
        raise ProtocolError("frame length does not match the declared payload length")
    expected_crc = CHECKSUM.unpack_from(data, len(data) - CHECKSUM.size)[0]
    if zlib.crc32(data[:-CHECKSUM.size]) & 0xFFFFFFFF != expected_crc:
        raise ProtocolError("CRC mismatch")
    return Packet(packet_type, epoch, sequence, data[HEADER_LENGTH:-CHECKSUM.size])
