"""Evidence-preserving view model for the v0.5 Workbench diagnostics dock.

The behavioral system trace supplies states, event counts and one explicitly
modeled FPGA workload percentage. It does not measure CPU, RAM, bus or NOR
utilization, so those meters never invent a percentage.
"""
from __future__ import annotations

import re

METERS = (
    ('cpu', 'CPU · F133'),
    ('memory', 'Memory'),
    ('bus', 'Bus · D213 mailbox'),
    ('fpga', 'FPGA45'),
    ('nor', 'NOR Flash'),
)
_SHA256 = re.compile(r'^[0-9a-f]{64}$')


def unknown():
    return {'evidence': 'UNKNOWN', 'frame': None, 'source': None, 'source_sha256': None,
            'meters': [{'id': key, 'label': label, 'value': 'UNKNOWN · no valid trace',
                        'detail': 'No source-backed utilization measurement', 'percent': None}
                       for key, label in METERS]}


def _text(value):
    return value if isinstance(value, str) and value and len(value) <= 64 else None


def _count(value):
    return value if type(value) is int and 0 <= value <= 1_000_000 else None


def snapshot(row, source=None, source_sha256=None):
    """Project one trace row into five honest meters; malformed input is unknown."""
    if (not isinstance(row, dict) or row.get('evidence') != 'HOST_SIM_BEHAVIORAL'
            or not isinstance(source, str) or not source
            or not isinstance(source_sha256, str) or not _SHA256.fullmatch(source_sha256)):
        return unknown()
    frame = _count(row.get('frame'))
    if frame is None:
        return unknown()
    meters = unknown()['meters']
    cpu = row.get('f133') if isinstance(row.get('f133'), dict) else {}
    runtime = _text(cpu.get('runtime'))
    if runtime:
        meters[0].update(value=runtime, detail='HOST_SIM · modeled runtime state')
    memory = row.get('memory') if isinstance(row.get('memory'), dict) else {}
    owner = _text(memory.get('ownership'))
    if owner:
        meters[1].update(value='Owner: ' + owner, detail='HOST_SIM · modeled ownership, not RAM use')
    d213 = row.get('d213') if isinstance(row.get('d213'), dict) else {}
    commands = _count(d213.get('commands'))
    if commands is not None:
        meters[2].update(value=f'{commands} modeled commands / frame',
                         detail='HOST_SIM · event count, not measured bandwidth')
    fpga = row.get('fpga45') if isinstance(row.get('fpga45'), dict) else {}
    busy = fpga.get('busy_percent')
    if type(busy) is int and 0 <= busy <= 100:
        meters[3].update(value=f'{busy}% modeled workload',
                         detail='HOST_SIM · behavioral model percentage, not silicon utilization',
                         percent=busy)
    nor = row.get('nor') if isinstance(row.get('nor'), dict) else {}
    reads = _count(nor.get('reads'))
    if reads is not None:
        meters[4].update(value=f'{reads} modeled reads / frame',
                         detail='HOST_SIM · event count, not measured flash throughput')
    return {'evidence': 'HOST_SIM_BEHAVIORAL', 'frame': frame, 'source': source,
            'source_sha256': source_sha256, 'meters': meters}
