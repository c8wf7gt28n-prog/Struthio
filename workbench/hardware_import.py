"""Arc Ledger hardware handoff adapter. Read-only, hash-bound, Qt independent.

Contracts supply navigation metadata, never executable command strings.
Source consistency is distinct from engineering correctness and board evidence.
"""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
from .project_services import project_path

BASE = 'hardware/compact-arc1/R10_WORK/'
P11 = BASE + 'closure_p11_struthio/'
MANIFEST = 'project/imports/hardware11/CUMULATIVE_MANIFEST.json'


def read(root, relative):
    p = project_path(root, relative)
    if p.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('Import metadata exceeds 16 MiB')
    return json.loads(p.read_text(encoding='utf-8'))


def check_hashes(root, hashes, prefix='', recorded=None):
    """MATCH, or SUPERSEDED when every difference has its exact current bytes recorded by a later pass
    (see recorded_digests), or STALE_OR_MISSING. 'mismatches' lists only unexplained differences."""
    mismatches = []
    superseded = []
    for relative, expected in hashes.items():
        name = prefix + relative
        try:
            p = project_path(root, name)
            actual = hashlib.sha256(p.read_bytes()).hexdigest()
        except (OSError, ValueError):
            actual = None
        if actual != expected:
            by = (recorded or {}).get(name, {}).get(actual if actual is not None else 'archived:' + expected)
            if by:
                superseded.append({'path': name, 'by': by})
            else:
                mismatches.append(name)
    state = 'STALE_OR_MISSING' if mismatches else 'SUPERSEDED' if superseded else 'MATCH'
    return {'state': state, 'checked': len(hashes), 'mismatches': mismatches, 'superseded': superseded}


def recorded_digests(root):
    """Exact file digests recorded after the import: every pass record's artifacts, files a supersession register
    lists as moved to an archive ('archived:<sha256>' keys), and the newest pass baseline inventory
    (passes/*/INVENTORY.csv from tools/source_identity.py). Maps path -> {sha256: record}. A file that differs from
    the import but equals a recorded digest was changed by a recorded pass; anything else is drift."""
    root = Path(root)
    out = {}
    for record in sorted(root.glob('passes/*/pass.json')):
        try:
            artifacts = json.loads(record.read_text(encoding='utf-8')).get('artifacts', [])
        except (OSError, ValueError):
            continue
        for a in artifacts:
            if isinstance(a, dict) and a.get('path') and a.get('sha256'):
                out.setdefault(a['path'], {})[a['sha256']] = record.parent.name
    for register in sorted(root.glob('passes/*/supersession.json')):
        try:
            archived = json.loads(register.read_text(encoding='utf-8')).get('archived', [])
        except (OSError, ValueError):
            continue
        for a in archived:
            out.setdefault(a['path'], {})['archived:' + a['sha256']] = register.parent.name + ' archived: ' + a['archive']
    inventories = sorted(root.glob('passes/*/INVENTORY.csv'),
                         key=lambda p: int(''.join(c for c in p.parent.name if c.isdigit()) or 0))
    if inventories:
        newest = inventories[-1]
        with newest.open(newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                out.setdefault(row['path'], {}).setdefault(row['sha256'], newest.parent.name + ' baseline inventory')
    return out


def descriptor(root):
    data = read(root, P11 + 'P11_WORKBENCH_IMPORT_CONTRACT.json')
    if data.get('schema') != 'arc1-r10-p11-struthio-workbench-integration/v1':
        raise ValueError('Unsupported cartridge import contract')
    if data.get('project_root') != P11.rstrip('/'):
        raise ValueError('Unexpected cartridge root')
    if data.get('physical_programming_allowed') is not False:
        raise ValueError('Import must not enable physical programming')
    for key in ('reference_source_path', 'c_port_path'):
        p = project_path(root, data[key])
        if not p.resolve().is_relative_to(project_path(root, P11).resolve()):
            raise ValueError('Cartridge path escapes its import')
    for capability in data.get('capabilities', []):
        if 'file' in capability:
            p = project_path(root, P11 + capability['file'])
            if not p.resolve().is_relative_to(project_path(root, P11).resolve()):
                raise ValueError('Capability path escapes its import')
    return data


def inspect(root):
    manifest = read(root, MANIFEST)
    payload = {k.removeprefix('ARC1_Workbench_R10/'): v
               for k, v in manifest['payload_sha256'].items()}
    p8 = read(root, BASE + 'closure_p8/P8_CROSSPROBE_INDEX.json')
    p9 = read(root, BASE + 'closure_p9/P9_FIRMWARE_TARGETS.json')
    p10 = read(root, BASE + 'closure_p10/P10_INTERCONNECT_INVENTORY.json')
    p11 = descriptor(root)
    fingerprints = read(root, P11 + p11['source_fingerprint_path'])
    rows = [
        dict(id='payload', title='Hardware P1–P11 payload', evidence='IMPORT INTEGRITY',
             path=MANIFEST, **check_hashes(root, payload, recorded=recorded_digests(root))),
        dict(id='p8', title='P8 electrical cross-probe', evidence='SOURCE CONSISTENCY',
             path=BASE+'closure_p8/P8_CROSSPROBE_INDEX.json', **check_hashes(root, p8['source_hashes_sha256'])),
        dict(id='p9', title='P9 firmware / boot / memory', evidence='SOURCE PLAN',
             path=BASE+'closure_p9/P9_FIRMWARE_TARGETS.json', **check_hashes(root, p9['source_snapshot_sha256'], BASE)),
        dict(id='p10', title='P10 interconnect inventory', evidence='SOURCE AUDIT / HOST FIXTURE',
             path=BASE+'closure_p10/P10_INTERCONNECT_INVENTORY.json', **check_hashes(root, p10['source_sha256'], BASE)),
        dict(id='p11', title='STRUTHIO 1.8.0 original reference', evidence='BYTE VERIFIED JS SOURCE',
             path=P11+'STRUTHIO_PORT_STATUS.json', **check_hashes(root, fingerprints['files'], P11+'reference/')),
    ]
    return {'schema':'arc-ledger.hardware-import/1', 'product':'Arc Ledger', 'version':'1.1',
            'rows':rows, 'all_sources_match':all(r['state']=='MATCH' for r in rows),
            'all_sources_current':all(r['state'] in ('MATCH','SUPERSEDED') for r in rows),
            'hardware_release':'HOLD', 'physical_programming_allowed':False,
            'full_gameplay_parity':False, 'cartridge':{'project':p11['project'], 'version':p11['version']},
            'components':len(p8['components']), 'firmware_targets':len(p9['targets']),
            'links':len(p10['links']), 'reference_files':len(fingerprints['files']),
            'limits':['Source hashes do not validate electrical correctness.',
                      'C port is a partial host bootstrap; no native console binary.',
                      'Imported host counters are not silicon telemetry.']}


def components(root):
    relative=BASE+'closure_p8/P8_CROSSPROBE_INDEX.json'
    manifest=read(root,MANIFEST)
    expected=manifest['payload_sha256']['ARC1_Workbench_R10/'+relative]
    if check_hashes(root,{relative:expected},recorded=recorded_digests(root))['state'] not in ('MATCH','SUPERSEDED'):
        raise ValueError('P8 index changed since import and no later pass records it. Reconcile it before cross-probing.')
    data = read(root, relative)
    if check_hashes(root, data['source_hashes_sha256'])['state'] != 'MATCH':
        raise ValueError('P8 source index is stale. Reconcile source versions before cross-probing.')
    return data['components']


def protected_reference(root, path):
    try:
        Path(path).resolve().relative_to((Path(root)/P11/'reference').resolve())
        return True
    except ValueError:
        return False
