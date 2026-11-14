"""GGUF fixtures made from the owner's real model header, without the 20 GB of weights.

The owner's model is Qwen3.6-35B-A3B Q4_K_M (20,542,732,576 bytes). Its header (metadata, chat template and
tensor table) was read once from the first 32 MiB of the real file and saved as data/qwen35moe_header.json.
The tokenizer arrays (about a quarter of a million entries) are left out there; only their lengths are kept.

`build(path, variant)` writes a valid GGUF from that header with a short tokenizer, then extends the file with a
sparse truncate, so it takes about 56 KiB of disk. Every variant but one is extended to the real file's size,
20,542,732,576 bytes. The exception is 'truncated', which by design stops one byte short of where its last tensor's
data ends: 20,531,799,903 bytes, because the short tokenizer puts the fixture's data section at byte 56,672 instead
of the real file's 10,989,344. Variants bend one thing each: bad magic, truncated data, unsupported architecture,
unsupported tensor type, no chat template. "Changed after registration" is done by `change_after_registration`.

`bounded_identity` stands in for Graphite's full-file SHA-256 during simulation runs; it hashes the size, the
first 16 MiB and the last 1 MiB, so a 20 GB sparse file is never read in full.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEADER_JSON = HERE / 'data' / 'qwen35moe_header.json'
OWNER_FILE = {'name': 'Qwen3.6-35B-A3B-Q4_K_M.gguf', 'bytes': 20_542_732_576,
              'sha256': 'f4ffe03c9139e6a905a5d346f77d9fabdd179367c3280dfd005d1e75ca5ed8c8'}
VARIANTS = ('valid', 'bad_magic', 'truncated', 'unsupported_architecture', 'unsupported_tensor_type',
            'no_chat_template')
SCALAR = {0: 'B', 1: 'b', 2: 'H', 3: 'h', 4: 'I', 5: 'i', 6: 'f', 7: '?', 10: 'Q', 11: 'q', 12: 'd'}
STRING, ARRAY = 8, 9
KEEP_ARRAY_LIMIT = 4096          # non-tokenizer arrays up to this length are kept whole
SHORT_TOKENS = 16                # the fixture's tokenizer length
HEAD_BYTES = 16 * 1024 * 1024
TAIL_BYTES = 1024 * 1024


# ---------------------------------------------------------------- reading the real header (done once)

class _Reader:
    def __init__(self, raw):
        self.raw = raw
        self.at = 0

    def take(self, n):
        if self.at + n > len(self.raw):
            raise ValueError('header extends past the bytes supplied')
        chunk = self.raw[self.at:self.at + n]
        self.at += n
        return chunk

    def num(self, code):
        return struct.unpack('<' + code, self.take(struct.calcsize(code)))[0]

    def text(self):
        return self.take(self.num('Q')).decode('utf-8')


def extract(head_path, source=None):
    """Read metadata and the tensor table from the first bytes of a GGUF file into a JSON-ready dict."""
    raw = Path(head_path).read_bytes()
    r = _Reader(raw)
    if r.take(4) != b'GGUF':
        raise ValueError('not a GGUF header')
    version = r.num('I')
    tensor_count = r.num('Q')
    key_count = r.num('Q')
    metadata = []
    for _ in range(key_count):
        key = r.text()
        kind = r.num('I')
        if kind in SCALAR:
            metadata.append({'key': key, 'type': kind, 'value': r.num(SCALAR[kind])})
        elif kind == STRING:
            metadata.append({'key': key, 'type': kind, 'value': r.text()})
        elif kind == ARRAY:
            sub = r.num('I')
            count = r.num('Q')
            values = []
            for _ in range(count):
                values.append(r.text() if sub == STRING else r.num(SCALAR[sub]))
            entry = {'key': key, 'type': kind, 'array_type': sub, 'count': count}
            if key.startswith('tokenizer.') or count > KEEP_ARRAY_LIMIT:
                entry['dropped'] = True
            else:
                entry['values'] = values
            metadata.append(entry)
        else:
            raise ValueError('unknown metadata type %d' % kind)
    tensors = []
    for _ in range(tensor_count):
        name = r.text()
        dims = [r.num('Q') for _ in range(r.num('I'))]
        tensors.append({'name': name, 'dims': dims, 'type': r.num('I'), 'offset': r.num('Q')})
    alignment = next((m['value'] for m in metadata if m['key'] == 'general.alignment'), 32)
    header_end = r.at
    data_offset = (header_end + alignment - 1) // alignment * alignment
    return {'schema': 'graphite.campaign.gguf-header/1',
            'source': source or {}, 'version': version, 'alignment': alignment,
            'header_end': header_end, 'data_offset': data_offset,
            'declared_size': (source or {}).get('bytes'),
            'note': 'Tokenizer arrays are dropped (count kept). Tensor offsets are relative to the data section.',
            'metadata': metadata, 'tensors': tensors}


def load_header():
    return json.loads(HEADER_JSON.read_text())


# ---------------------------------------------------------------- writing a fixture

def _string(value):
    raw = value.encode('utf-8')
    return struct.pack('<Q', len(raw)) + raw


def _short_array(entry):
    """A short stand-in for a dropped tokenizer array, of the same element type."""
    sub = entry['array_type']
    if sub == STRING:
        if entry['key'].endswith('merges'):
            values = ['t %d' % i for i in range(SHORT_TOKENS // 2)]
        else:
            values = ['<t%d>' % i for i in range(SHORT_TOKENS)]
        body = b''.join(_string(v) for v in values)
    else:
        values = [1] * SHORT_TOKENS
        body = b''.join(struct.pack('<' + SCALAR[sub], v) for v in values)
    return struct.pack('<IQ', sub, len(values)) + body


def _value(entry):
    kind = entry['type']
    if kind in SCALAR:
        return struct.pack('<' + SCALAR[kind], entry['value'])
    if kind == STRING:
        return _string(entry['value'])
    if entry.get('dropped'):
        return _short_array(entry)
    sub = entry['array_type']
    if sub == STRING:
        body = b''.join(_string(v) for v in entry['values'])
    else:
        body = b''.join(struct.pack('<' + SCALAR[sub], v) for v in entry['values'])
    return struct.pack('<IQ', sub, len(entry['values'])) + body


def _tensor_bytes(tensor):
    from sdk.cli.arc1cli.gguf_inspect import TYPES   # the inspector's own block table
    kind = TYPES.get(tensor['type'])
    if not kind:
        return 0
    count = 1
    for d in tensor['dims']:
        count *= d
    return count // kind[1] * kind[2]


def build(path, variant='valid', header=None):
    """Write the fixture for `variant` at `path` (a .gguf name) and return what was written."""
    if variant not in VARIANTS:
        raise ValueError('unknown GGUF fixture variant: ' + variant)
    header = json.loads(json.dumps(header or load_header()))
    metadata = header['metadata']
    tensors = header['tensors']
    if variant == 'unsupported_architecture':
        for m in metadata:
            if m['key'] == 'general.architecture':
                m['value'] = 'mamba'
    if variant == 'no_chat_template':
        metadata = [m for m in metadata if m['key'] != 'tokenizer.chat_template']
    if variant == 'unsupported_tensor_type':
        tensors[0]['type'] = 39
    out = bytearray()
    out += b'GGUX' if variant == 'bad_magic' else b'GGUF'
    out += struct.pack('<IQQ', header['version'], len(tensors), len(metadata))
    for m in metadata:
        out += _string(m['key']) + struct.pack('<I', m['type']) + _value(m)
    for t in tensors:
        out += _string(t['name']) + struct.pack('<I', len(t['dims']))
        out += b''.join(struct.pack('<Q', d) for d in t['dims'])
        out += struct.pack('<IQ', t['type'], t['offset'])
    alignment = header['alignment']
    data_offset = (len(out) + alignment - 1) // alignment * alignment
    out += b'\0' * (data_offset - len(out))
    ends = [data_offset + t['offset'] + _tensor_bytes(t) for t in tensors]
    size = header['declared_size']
    if variant == 'truncated':
        size = max(ends) - 1          # one byte short of the last tensor's end
    if size < max(ends):
        size = size if variant == 'truncated' else max(ends)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as stream:
        stream.write(out)
        stream.truncate(size)         # sparse: the tensor data is a hole, not written zeros
    return {'path': str(path), 'variant': variant, 'apparent_bytes': size, 'header_bytes': len(out),
            'data_offset': data_offset, 'disk_bytes': disk_bytes(path), 'tensor_count': len(tensors),
            'header_sha256': hashlib.sha256(bytes(out)).hexdigest()}


def change_after_registration(path, data_offset):
    """Change one byte at the start of the tensor data: a real change a full SHA-256 would catch."""
    with Path(path).open('r+b') as stream:
        stream.seek(data_offset)
        old = stream.read(1)
        stream.seek(data_offset)
        stream.write(bytes([(old[0] if old else 0) ^ 0xFF]))


def disk_bytes(path):
    """Blocks actually allocated on disk (what `du` reports), as bytes."""
    return os.stat(path).st_blocks * 512


def bounded_identity(path, cancelled=lambda: False):
    """Simulation stand-in for gguf_inspect.identity: size + first 16 MiB + last 1 MiB, never 20 GB."""
    path = Path(path)
    if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('MODEL_LOCATION_CHANGED_OR_LINKED')
    before = path.stat()
    digest = hashlib.sha256(str(before.st_size).encode())
    with path.open('rb') as stream:
        digest.update(stream.read(HEAD_BYTES))
        stream.seek(max(0, before.st_size - TAIL_BYTES))
        digest.update(stream.read(TAIL_BYTES))
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('MODEL_CHANGED_DURING_INSPECTION')
    return {'name': path.name, 'bytes': after.st_size, 'sha256': digest.hexdigest()}


BOUNDED_READ_BYTES = HEAD_BYTES + TAIL_BYTES


if __name__ == '__main__':      # one-time extraction: python3 -m tools.campaign_lib.gguf_fixture <head.gguf>
    import sys
    data = extract(sys.argv[1], source=dict(OWNER_FILE, header_bytes_read=os.path.getsize(sys.argv[1]),
                                              origin='first 32 MiB of the owner\'s file, read from the publisher'))
    HEADER_JSON.parent.mkdir(parents=True, exist_ok=True)
    HEADER_JSON.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({k: data[k] for k in ('version', 'alignment', 'header_end', 'data_offset')}),
          len(data['metadata']), 'keys', len(data['tensors']), 'tensors')
