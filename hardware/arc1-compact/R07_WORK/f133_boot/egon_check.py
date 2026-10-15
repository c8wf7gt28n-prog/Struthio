#!/usr/bin/env python3
"""Independent check of an Allwinner eGON.BT0 boot image produced by
`mkimage -T sunxi_egon -A riscv`: jump instruction, magic, length, checksum.
Checksum rule (sunxi BROM, as implemented in U-Boot tools/sunxi_egon.c): the
32-bit word sum of the whole image, computed with the checksum field set to
the stamp 0x5F0A6C39, equals the stored checksum. Usage: egon_check.py IMG"""
import struct
import sys

d = open(sys.argv[1], "rb").read()
w0 = struct.unpack("<I", d[:4])[0]
off = ((w0 >> 31) & 1) << 20 | ((w0 >> 12) & 0xFF) << 12 | ((w0 >> 20) & 1) << 11 | ((w0 >> 21) & 0x3FF) << 1
ok = True
def chk(name, cond, detail):
    global ok
    ok &= bool(cond)
    print(f"{'PASS' if cond else 'FAIL'} {name}: {detail}")
chk("riscv_jal", (w0 & 0x7F) == 0x6F and off == 0x60, f"word0 {w0:#010x} -> jal +{off:#x}")
chk("magic", d[4:12] == b"eGON.BT0", repr(d[4:12]))
length = struct.unpack("<I", d[16:20])[0]
chk("length", length == len(d) and length % 8192 == 0, f"header {length}, file {len(d)}")
stored = struct.unpack("<I", d[12:16])[0]
words = list(struct.unpack(f"<{len(d)//4}I", d))
words[3] = 0x5F0A6C39
chk("checksum", (sum(words) & 0xFFFFFFFF) == stored, f"stored {stored:#010x}")
chk("fits_sram_a1", len(d.rstrip(b'\0')) <= 32 * 1024, f"{len(d.rstrip(b'\0'))} bytes used of 32768")
print("EGON_OK" if ok else "EGON_BAD")
sys.exit(0 if ok else 1)
