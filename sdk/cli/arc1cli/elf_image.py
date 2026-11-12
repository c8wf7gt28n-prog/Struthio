"""Strict bounded ELF64/RISC-V load-plan inspection; no board map defaults.

Only static ET_EXEC images with separate read/execute and read/write PT_LOAD
segments are supported. This checks geometry, never silicon compatibility.
"""
import struct

MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_SEGMENTS = 64


def inspect(data, *, allowed_regions):
    if not isinstance(data, bytes) or not 64 <= len(data) <= MAX_FILE_BYTES:
        raise ValueError('ELF size/type outside host inspection bounds')
    regions = []
    for base, size in allowed_regions:
        if not isinstance(base, int) or not isinstance(size, int) or base < 0 or size <= 0 or base + size > 1 << 64:
            raise ValueError('Invalid caller memory region')
        regions.append((base, base + size))
    if not regions or len(regions) > 64:
        raise ValueError('Explicit bounded allowed regions required')
    h = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    ident, kind, machine, version, entry, phoff, shoff, flags, ehsize, phsize, count, *_ = h
    if ident[:7] != b'\x7fELF\x02\x01\x01' or kind != 2 or machine != 243 or version != 1:
        raise ValueError('Expected static little-endian ELF64 RISC-V executable')
    # Current experiment emits soft-float, non-RVC base ISA. Other profiles must
    # be reviewed rather than quietly treated as the same ISA/ABI.
    if flags != 0 or ehsize != 64 or phsize != 56 or not 1 <= count <= MAX_SEGMENTS:
        raise ValueError('Unsupported flags or program-header layout')
    if phoff < 64 or phoff + count * phsize > len(data):
        raise ValueError('Program header outside file')
    loads = []
    for i in range(count):
        ptype, access, off, va, pa, filesz, memsz, align = struct.unpack_from('<IIQQQQQQ', data, phoff + i * phsize)
        if ptype in (2, 3):
            raise ValueError('Dynamic loader/interpreter unsupported')
        if ptype != 1:
            if ptype not in (0, 0x70000003, 0x6474e551):
                raise ValueError('Unsupported program-header type')
            continue
        if va != pa or not memsz or filesz > memsz or off + filesz > len(data) or pa + memsz > 1 << 64:
            raise ValueError('Invalid load extent or relocation requirement')
        if access not in (4, 5, 6) or align == 0 or align & (align - 1) or (pa - off) % align:
            raise ValueError('Invalid load permissions/alignment')
        if not any(lo <= pa and pa + memsz <= hi for lo, hi in regions):
            raise ValueError('Load outside caller memory regions')
        if any(pa < s['address'] + s['memory_bytes'] and s['address'] < pa + memsz for s in loads):
            raise ValueError('Overlapping load segments')
        loads.append(dict(address=pa, file_offset=off, file_bytes=filesz, memory_bytes=memsz, flags=access))
    if not any(s['flags'] == 5 and s['address'] <= entry and entry + 4 <= s['address'] + s['file_bytes'] for s in loads) or entry & 3:
        raise ValueError('Entry is not an aligned file-backed instruction')
    return dict(schema='arc1.elf-load-plan/1', entry=entry, segments=loads,
                isa_abi_profile='ELF64 RISC-V soft-float non-RVC; instruction subset not decoded',
                target_image_qualified=False, board_boot_qualified=False)
