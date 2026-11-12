"""Read-only source audit and physical CAD observations. No electrical changes.

Reuses the imported P8 cross-probe checker without invoking its report writer.
Numbers below are native-file observations, not new authoritative chip facts.
"""
from hashlib import sha256
import json
from pathlib import Path
import runpy
from . import viewer_data as cad

BASE = Path('hardware/compact-arc1/R10_WORK')
REFS = {'f133': 'U18', 'd213': 'U20', 'fpga45': 'U35', 'fpga12': 'U40', 'nor': 'U19'}


def inspect(root):
    root = Path(root).resolve()
    checker = root / BASE / 'closure_p8/crossprobe.py'
    index, _ = runpy.run_path(str(checker))['create_index'](root)
    saved = json.loads((root / BASE / 'closure_p8/P8_VERIFICATION.json').read_text())
    current = index['source_hashes_sha256']
    stale = [p for p, digest in current.items() if saved.get('source_hashes_sha256', {}).get(p) != digest]
    findings = dict(index['findings'])
    # Archived DRC has a hash/date but no binding to a particular PCB hash.
    # Never represent it as a newly executed KiCad check.
    return {'schema': 'arc-ledger.hardware-review/1', 'evidence': 'STATIC_CHECK',
            'status': 'SOURCE_MISMATCH' if findings['errors'] else 'SOURCE_CONSISTENT',
            'fabrication': 'HOLD', 'counts': index['counts'], 'findings': findings,
            'p8_evidence_fresh': not stale, 'stale_sources': stale,
            'archived_drc': index['archived_native_drc'], 'drc_executed': False,
            'source_hashes_sha256': current,
            'checker_sha256': sha256(checker.read_bytes()).hexdigest(),
            'limitations': index['limitations'] + ['Archived DRC is not bound to the current PCB hash. No board tests performed.']}


def component(root, device_id):
    ref = REFS.get(device_id)
    if not ref:
        return None
    path = Path(root) / BASE / 'cad/ARC1_R10.kicad_pcb'
    document = cad.read(path, 'kicad_pcb')
    for footprint in cad.parts(document, 'footprint'):
        if cad.prop(footprint, 'Reference') == ref:
            pads = []
            for pad in cad.parts(footprint, 'pad'):
                at = cad.xy(cad.one(pad, 'at'))
                size = cad.xy(cad.one(pad, 'size'))
                pads.append({'number': cad.val(pad), 'at': at, 'size': size,
                             'angle': cad.number(cad.one(pad, 'at'), 3), 'shape': cad.val(pad, 3)})
            return {'ref': ref, 'value': cad.prop(footprint, 'Value'),
                    'footprint': cad.val(footprint), 'anchor_mm': cad.xy(cad.one(footprint, 'at')),
                    'rotation_deg': cad.number(cad.one(footprint, 'at'), 3),
                    'layer': cad.val(cad.one(footprint, 'layer')), 'pads': pads,
                    'source': str(BASE / 'cad/ARC1_R10.kicad_pcb'),
                    'sha256': sha256(path.read_bytes()).hexdigest()}
    return None
