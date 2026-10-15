#!/usr/bin/env python3
"""Minimal RV64IM instruction-set simulator (no compressed, no CSR beyond ecall) used ONLY to count dynamic
instructions of benchmark kernels compiled with riscv64-unknown-elf-gcc -march=rv64im. It is not a cycle model:
cycles = instructions x CPI, where CPI for the F133 C906 core is an ASSUMPTION carried in the benchmark report.
Self-test: tools/bench/iss_selftest (compiled C checks with known results) must pass before counts are used.
Usage: rv64im_iss.py ELF [entry-args...]  -> prints JSON {exit, instret, counters}"""
import json
import struct
import sys

M64 = (1 << 64) - 1


def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def s64(v):
    return sx(v, 64)


class ISS:
    def __init__(self, elf, mem_size=16 << 20):
        self.mem = bytearray(mem_size)
        self.x = [0] * 32
        self.pc = self.load(elf)
        self.instret = 0
        self.kind = {"mul": 0, "div": 0, "load": 0, "store": 0, "branch": 0}

    def load(self, path):
        d = open(path, "rb").read()
        assert d[:4] == b"\x7fELF" and d[4] == 2, "ELF64 expected"
        entry, phoff = struct.unpack_from("<QQ", d, 24)
        phentsize, phnum = struct.unpack_from("<HH", d, 54)
        for i in range(phnum):
            p_type, _, p_off, p_vaddr, _, p_filesz, p_memsz, _ = struct.unpack_from("<IIQQQQQQ", d, phoff + i * phentsize)
            if p_type == 1:
                self.mem[p_vaddr:p_vaddr + p_filesz] = d[p_off:p_off + p_filesz]
                self.mem[p_vaddr + p_filesz:p_vaddr + p_memsz] = bytes(p_memsz - p_filesz)
        # symbols (for marker functions)
        shoff, = struct.unpack_from("<Q", d, 40)
        shentsize, shnum, shstrndx = struct.unpack_from("<HHH", d, 58)
        secs = [struct.unpack_from("<IIQQQQIIQQ", d, shoff + i * shentsize) for i in range(shnum)]
        self.sym = {}
        for s in secs:
            if s[1] == 2:                                   # SHT_SYMTAB
                strtab = secs[s[6]]
                for k in range(s[5] // 24):
                    nm, info, other, shndx, val, size = struct.unpack_from("<IBBHQQ", d, s[4] + k * 24)
                    e = d.index(b"\0", strtab[4] + nm)
                    self.sym[d[strtab[4] + nm:e].decode()] = val
        return entry

    def ld(self, a, n, signed):
        v = int.from_bytes(self.mem[a:a + n], "little", signed=signed)
        return v & M64

    def st(self, a, n, v):
        self.mem[a:a + n] = (v & ((1 << (8 * n)) - 1)).to_bytes(n, "little")

    def run(self, max_instr=200_000_000):
        x, mem = self.x, self.mem
        pc = self.pc
        n = 0
        mark = self.sym.get("bench_mark", -1)
        self.marks = []
        while n < max_instr:
            if pc == mark:
                self.marks.append((x[10] & 0xFFFFFFFF, n))
            ins = int.from_bytes(mem[pc:pc + 4], "little")
            op = ins & 0x7F
            rd = (ins >> 7) & 31
            f3 = (ins >> 12) & 7
            rs1 = (ins >> 15) & 31
            rs2 = (ins >> 20) & 31
            f7 = ins >> 25
            a, b = x[rs1], x[rs2]
            npc = pc + 4
            r = None
            n += 1
            if op == 0x13 or op == 0x1B:                    # OP-IMM(-32)
                imm = sx(ins >> 20, 12)
                sh = (ins >> 20) & (0x3F if op == 0x13 else 0x1F)
                if op == 0x13:
                    if f3 == 0: r = a + imm
                    elif f3 == 2: r = int(s64(a) < imm)
                    elif f3 == 3: r = int(a < (imm & M64))
                    elif f3 == 4: r = a ^ (imm & M64)
                    elif f3 == 6: r = a | (imm & M64)
                    elif f3 == 7: r = a & (imm & M64)
                    elif f3 == 1: r = a << sh
                    elif f3 == 5: r = (s64(a) >> sh) if (ins >> 30) & 1 else (a >> sh)
                else:
                    a32 = a & 0xFFFFFFFF
                    if f3 == 0: r = sx(a + imm, 32)
                    elif f3 == 1: r = sx(a32 << sh, 32)
                    elif f3 == 5: r = (sx(a32, 32) >> sh) if (ins >> 30) & 1 else sx(a32 >> sh, 32)
            elif op == 0x33 or op == 0x3B:                  # OP(-32)
                w = op == 0x3B
                if w:
                    a, b = sx(a, 32) & M64, sx(b, 32) & M64
                if f7 == 1:
                    sa, sb = s64(a), s64(b)
                    if w:
                        sa, sb, ua, ub = sx(a, 32), sx(b, 32), a & 0xFFFFFFFF, b & 0xFFFFFFFF
                    else:
                        ua, ub = a, b
                    if f3 == 0: r = sa * sb; self.kind["mul"] += 1
                    elif f3 == 1: r = (sa * sb) >> 64; self.kind["mul"] += 1
                    elif f3 == 2: r = (sa * ub) >> 64; self.kind["mul"] += 1
                    elif f3 == 3: r = (ua * ub) >> 64; self.kind["mul"] += 1
                    else:
                        self.kind["div"] += 1
                        bits = 32 if w else 64
                        mn = -(1 << (bits - 1))
                        if f3 in (4, 6):
                            if sb == 0:
                                q, rm = -1, sa
                            elif sa == mn and sb == -1:
                                q, rm = mn, 0
                            else:
                                q = abs(sa) // abs(sb)
                                if (sa < 0) != (sb < 0):
                                    q = -q
                                rm = sa - sb * q
                            r = q if f3 == 4 else rm
                        elif f3 == 5: r = (1 << bits) - 1 if ub == 0 else ua // ub
                        elif f3 == 7: r = ua if ub == 0 else ua % ub
                    if w and r is not None: r = sx(r, 32)
                else:
                    sh = b & (0x1F if w else 0x3F)
                    if f3 == 0: r = (a - b) if f7 == 0x20 else (a + b)
                    elif f3 == 1: r = a << sh
                    elif f3 == 2: r = int(s64(a) < s64(b))
                    elif f3 == 3: r = int(a < b)
                    elif f3 == 4: r = a ^ b
                    elif f3 == 5:
                        if w: r = (sx(a, 32) >> sh) if f7 == 0x20 else ((a & 0xFFFFFFFF) >> sh)
                        else: r = (s64(a) >> sh) if f7 == 0x20 else (a >> sh)
                    elif f3 == 6: r = a | b
                    elif f3 == 7: r = a & b
                    if w: r = sx(r, 32)
            elif op == 0x37: r = sx(ins & 0xFFFFF000, 32)
            elif op == 0x17: r = pc + sx(ins & 0xFFFFF000, 32)
            elif op == 0x6F:
                imm = sx(((ins >> 31) << 20) | (((ins >> 12) & 0xFF) << 12) | (((ins >> 20) & 1) << 11) | (((ins >> 21) & 0x3FF) << 1), 21)
                r = pc + 4; npc = pc + imm
            elif op == 0x67:
                r = pc + 4; npc = (a + sx(ins >> 20, 12)) & ~1 & M64
            elif op == 0x63:
                self.kind["branch"] += 1
                imm = sx(((ins >> 31) << 12) | (((ins >> 7) & 1) << 11) | (((ins >> 25) & 0x3F) << 5) | (((ins >> 8) & 0xF) << 1), 13)
                c = {0: a == b, 1: a != b, 4: s64(a) < s64(b), 5: s64(a) >= s64(b), 6: a < b, 7: a >= b}[f3]
                if c: npc = pc + imm
            elif op == 0x03:
                self.kind["load"] += 1
                ad = (a + sx(ins >> 20, 12)) & M64
                r = self.ld(ad, (1, 2, 4, 8, 1, 2, 4)[f3], f3 < 4)
            elif op == 0x23:
                self.kind["store"] += 1
                ad = (a + sx(((ins >> 25) << 5) | ((ins >> 7) & 31), 12)) & M64
                self.st(ad, (1, 2, 4, 8)[f3], b)
            elif op == 0x0F:
                pass
            elif op == 0x73:
                if ins == 0x00000073:                       # ecall: a7=93 exit(a0)
                    self.instret += n
                    return x[10] & 0xFFFFFFFF
                raise RuntimeError(f"unsupported SYSTEM {ins:08x} at {pc:x}")
            else:
                raise RuntimeError(f"unsupported opcode {ins:08x} at {pc:x}")
            if r is not None and rd:
                x[rd] = r & M64
            pc = npc
        raise RuntimeError("instruction limit")


if __name__ == "__main__":
    s = ISS(sys.argv[1])
    code = s.run()
    rs = s.sym.get("result_sum")
    sums = [s.ld(rs + 4 * i, 4, False) for i in range(int(sys.argv[2]) if len(sys.argv) > 2 else 4)] if rs is not None else []
    print(json.dumps({"exit": code, "instret": s.instret, **s.kind, "marks": s.marks, "result_sum": sums}))
