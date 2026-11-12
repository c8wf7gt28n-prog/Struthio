"""R10 NOR *virtual* image staging; never programs a physical device.

This module is independent of Qt. Both the user interface and agent interface
consult this one model. Values come from the preserved R10 CSV (PROPOSED), not
from a detected chip. File staging is a read-only reference plus SHA-256; the
planner does not copy, erase, write, or create a flash binary.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

RELATIVE_MAP = Path('hardware/compact-arc1/R10_WORK/memory/R10_nor_partition.csv')
EXPECTED_SIZE = 64 * 1024 * 1024  # the R10 *proposed* design only
LOCKED_IDS = frozenset({'F1BT', 'F1RC', 'C12G', 'C45G'})
RESERVED_IDS = frozenset({'META'})

class StageError(ValueError):
    """A requested host-only stage fails a safety or integrity check."""

@dataclass(frozen=True)
class Partition:
    id: str
    name: str
    start: int
    end: int
    protection: str
    status: str
    contents: str

    @property
    def size(self) -> int:
        return self.end - self.start

    @property
    def stageable(self) -> bool:
        return self.id not in LOCKED_IDS | RESERVED_IDS and self.protection.lower() == 'unlocked'

    def record(self):
        return {'id': self.id, 'name': self.name, 'offset': f'0x{self.start:08X}',
                'end_exclusive': f'0x{self.end:08X}', 'size_bytes': self.size,
                'stageable': self.stageable, 'protection': self.protection,
                'status': self.status, 'contents': self.contents}


def read_layout(root):
    source = Path(root).resolve() / RELATIVE_MAP
    if source.is_symlink() or not source.is_file() or source.stat().st_size > 250_000:
        raise StageError('R10 NOR source CSV unavailable or unsafe')
    try:
        with source.open('r', encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise StageError('Unable to read R10 NOR source: ' + str(exc)) from exc
    if not rows or len(rows) > 64:
        raise StageError('R10 NOR source has no usable partitions')
    partitions = []
    used_ids = set()
    for row in rows:
        try:
            start = int(row['offset'], 0)
            end = int(row['end_exclusive'], 0)
            size = int(row['size_bytes'])
            ident = row['id'].strip()
            status = row['status'].strip()
            protection = row['protection'].strip()
            name = row['partition'].strip()
            contents = row['contents'].strip()
        except (ValueError, KeyError, AttributeError, TypeError) as exc:
            raise StageError('Malformed R10 partition entry') from exc
        if not ident or ident in used_ids or not name or start < 0 or end <= start or end - start != size:
            raise StageError('Duplicate, invalid, or inconsistent R10 partition')
        if 'PROPOSED' not in status.upper():
            raise StageError('Unrecognized R10 evidence status; review source before staging')
        partitions.append(Partition(ident, name, start, end, protection, status, contents))
        used_ids.add(ident)
    partitions.sort(key=lambda x: x.start)
    if partitions[0].start != 0 or partitions[-1].end != EXPECTED_SIZE:
        raise StageError('R10 proposal must cover exactly 64 MiB')
    if any(a.end != b.start for a, b in zip(partitions, partitions[1:])):
        raise StageError('R10 proposal has a gap or overlapping partitions')
    for ident in LOCKED_IDS | RESERVED_IDS:
        if ident not in used_ids:
            raise StageError('Missing required protected/reserved partition: ' + ident)
    return partitions


def hash_image(path, max_bytes):
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        raise StageError('Select a regular image file, not a directory or symlink')
    try:
        size = p.stat().st_size
    except OSError as exc:
        raise StageError('Image cannot be inspected') from exc
    if size <= 0 or size > max_bytes:
        raise StageError('Image must be non-empty and fit the selected partition')
    digest = sha256()
    sample = b''
    try:
        with p.open('rb') as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                if not sample:
                    sample = chunk[:4096]
                digest.update(chunk)
    except OSError as exc:
        raise StageError('Unable to read image') from exc
    if p.stat().st_size != size:
        raise StageError('Image size changed during staging')
    return {'path': str(p.resolve()), 'file_name': p.name, 'size_bytes': size,
            'sha256': digest.hexdigest(), 'link_test_only': b'LINK_TEST_ONLY NOT_BOOTABLE' in sample}


class NorStage:
    """Volatile stage queue. No device methods and no hardware transport."""
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.partitions = read_layout(self.root)
        self.layout_sha256 = sha256((self.root / RELATIVE_MAP).read_bytes()).hexdigest()
        self._by_id = {p.id: p for p in self.partitions}
        self.staged = {}

    def stage(self, partition_id, image_path):
        part = self._by_id.get(partition_id)
        if part is None:
            raise StageError('Unknown partition: ' + str(partition_id))
        if not part.stageable:
            raise StageError('%s is factory-locked or reserved; staging denied' % part.id)
        record = hash_image(image_path, part.size)
        record['partition_id'] = part.id
        record['offset'] = f'0x{part.start:08X}'
        record['partition_capacity'] = part.size
        self.staged[part.id] = record
        return dict(record)

    def remove(self, partition_id):
        self.staged.pop(partition_id, None)

    def review(self):
        if sha256((self.root / RELATIVE_MAP).read_bytes()).hexdigest() != self.layout_sha256:
            raise StageError('R10 partition map changed since this staging session opened')
        entries = []
        for part in self.partitions:
            if part.id not in self.staged:
                continue
            record = dict(self.staged[part.id])
            current = hash_image(record['path'], part.size)
            if current['sha256'] != record['sha256'] or current['size_bytes'] != record['size_bytes']:
                raise StageError('Image changed since staging: ' + record['file_name'])
            record['verified_against_current_file'] = True
            entries.append(record)
        return {
            'schema': 'arc1.nor.host-staging/1',
            'evidence_class': 'DESIGN',
            'source': RELATIVE_MAP.as_posix(),
            'source_sha256': self.layout_sha256,
            'partition_status': 'PROPOSED - NOT BOARD VALIDATED',
            'total_capacity_bytes': EXPECTED_SIZE,
            'physical_device_connected': False,
            'physical_write_enabled': False,
            'flash_approved': False,
            'operations': entries,
            'warning': 'HOST STAGING ONLY. No flash chip accessed, no image bootability confirmed.',
        }

    def export(self, path):
        """Save plan metadata only, to an explicit user-chosen file path."""
        target = Path(path)
        if target.suffix.lower() != '.json':
            raise StageError('Review plan must be a JSON file')
        data = self.review()
        target.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        return target


def inspect(root):
    model = NorStage(root)
    return {'source': RELATIVE_MAP.as_posix(), 'total_capacity_bytes': EXPECTED_SIZE,
            'evidence_class': 'DESIGN', 'map_status': 'PROPOSED',
            'physical_device_connected': False, 'physical_write_enabled': False,
            'partitions': [p.record() for p in model.partitions]}
