"""Minimal U-Boot RISC-V eGON image tooling; no target capacity is assumed.

This profile uses the 96-byte SPL v0.1 header, 512-byte padding, no DT/FEL
metadata and exactly one image. The caller must supply a qualified load limit.
Format validity does not establish executable code, authenticity or board boot.
"""
from __future__ import annotations

import struct

HEADER_BYTES = 96
BLOCK_BYTES = 512
STAMP = 0x5F0A6C39
JUMP = 0x0600006F  # JAL x0, +96, as emitted by upstream sunxi_egon.c.
HOST_RESOURCE_LIMIT = 16 * 1024 * 1024  # Tool resource policy, NOT F133 SRAM size.


class ImageError(ValueError):
    pass


def _limit(max_image_bytes):
    if (type(max_image_bytes) is not int or
            not BLOCK_BYTES <= max_image_bytes <= HOST_RESOURCE_LIMIT):
        raise ImageError("load limit must be 512..16777216 bytes (host tool ceiling)")


def checksum(image):
    """Sum LE words with the ROM stamp substituted for the checksum field."""
    if len(image) < HEADER_BYTES or len(image) % 4:
        raise ImageError("checksum requires a complete word-aligned image")
    total = 0
    for offset in range(0, len(image), 4):
        total += STAMP if offset == 12 else struct.unpack_from("<I", image, offset)[0]
    return total & 0xFFFFFFFF


def inspect(image, *, max_image_bytes):
    _limit(max_image_bytes)
    if not isinstance(image, bytes):
        raise ImageError("immutable image bytes required")
    if len(image) < HEADER_BYTES:
        raise ImageError("truncated header")
    if image[4:12] != b"eGON.BT0":
        raise ImageError("bad eGON magic")
    if struct.unpack_from("<I", image)[0] != JUMP:
        raise ImageError("expected RISC-V jump to byte 96")
    stored, length = struct.unpack_from("<II", image, 12)
    if length < BLOCK_BYTES or length % BLOCK_BYTES or length != len(image):
        raise ImageError("invalid length, truncation or trailing bytes")
    if length > max_image_bytes:
        raise ImageError("image exceeds caller load limit")
    if image[20:24] != b"SPL\x01" or any(image[24:HEADER_BYTES]):
        raise ImageError("unsupported SPL metadata for minimal profile")
    if checksum(image) != stored:
        raise ImageError("checksum mismatch")
    return dict(profile="riscv-egon-spl01-minimal", image_bytes=length,
                header_bytes=HEADER_BYTES, entry_offset=HEADER_BYTES,
                checksum=stored, caller_load_limit=max_image_bytes,
                executable_qualified=False, board_boot_qualified=False)


def pack(payload, *, max_image_bytes):
    _limit(max_image_bytes)
    if not isinstance(payload, bytes) or not payload:
        raise ImageError("non-empty immutable payload bytes required")
    size = ((HEADER_BYTES + len(payload) + BLOCK_BYTES - 1) // BLOCK_BYTES) * BLOCK_BYTES
    if size > max_image_bytes:
        raise ImageError("padded image exceeds caller load limit")
    image = bytearray(size)
    struct.pack_into("<I8sII4s", image, 0, JUMP, b"eGON.BT0", STAMP, size, b"SPL\x01")
    image[HEADER_BYTES:HEADER_BYTES + len(payload)] = payload
    struct.pack_into("<I", image, 12, checksum(image))
    result = bytes(image)
    inspect(result, max_image_bytes=max_image_bytes)
    return result
