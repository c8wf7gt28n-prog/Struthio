"""Hardware resource budgets for the Inspector (frame time, link bandwidth, memory).

Qt-free, shared by the Qt Inspector and the agent interface (`inspect.resources`).
Numbers come from hardware/budgets/r10_resources.json and the hardware manifest.
Each number must quote text that really occurs in its cited source file; if the
quote is not found the number is dropped (CITATION MISSING), so the chart can
never show a figure the R10 documents do not state. Unknown stays unknown.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUDGET = ROOT / 'hardware' / 'budgets' / 'r10_resources.json'
MANIFEST = ROOT / 'hardware' / 'manifests' / 'arc1-r10.hw.json'
SCHEMA = 'arc1.resource-budget/1'
CHIP_NAMES = {'f133': 'F133', 'd213': 'D213', 'gpu45': '45F', 'fpga12': '12F'}
MEMORY_NAMES = {'f133_ddr2': 'DDR2 (in package)', 'd213_ddr3': 'DDR3 (in package)', 'gpu45_sdram': 'SDR SDRAM',
                'fpga12_psram': 'QSPI PSRAM'}
EVIDENCE = ('NONE', 'DESIGN', 'STATIC_CHECK', 'HOST_SIM', 'RTL_SIM', 'FPGA_PNR', 'BOARD_TEST')


def _sources(root):
    man = json.loads((Path(root) / MANIFEST.relative_to(ROOT)).read_text(encoding='utf-8'))
    out = {}
    for s in man.get('sources', []):
        try:
            out[s['id']] = (Path(root) / s['path']).read_text(encoding='utf-8', errors='replace')
        except (OSError, KeyError):
            out[s.get('id')] = None
    return man, out


def _verify(entry, texts, value_keys):
    """Copies entry; if its quote is absent from its source, the numbers are removed."""
    e = dict(entry)
    e['cited'] = None
    src, quote = e.get('source'), e.get('quote')
    if src is None:
        e['cited'] = False
    else:
        text = texts.get(src)
        e['cited'] = bool(text and quote and quote in text)
    has_value = any(e.get(k) is not None for k in value_keys)
    if has_value and not e['cited']:
        for k in value_keys:
            e[k] = None
        e['evidence'] = 'NONE'
        e['note'] = 'CITATION MISSING: the quoted text was not found in %s' % src
    if e.get('evidence') not in EVIDENCE:
        e['evidence'] = 'NONE'
    return e


def load(root=ROOT):
    root = Path(root)
    data = json.loads((root / BUDGET.relative_to(ROOT)).read_text(encoding='utf-8'))
    if data.get('schema') != SCHEMA:
        raise ValueError('unexpected resource budget schema')
    man, texts = _sources(root)
    frame = _verify(data['frame'], texts, ('period_ms',))
    stages = [_verify(s, texts, ('ms',)) for s in data['frame_stages']]
    links = [_verify(l, texts, ('mbps', 'mbps_low')) for l in data['links']]
    memory = [{'id': m['id'], 'label': '%s %s' % (CHIP_NAMES.get(c['id'], c['id']), MEMORY_NAMES.get(m['id'], m['type'])),
               'chip': c['id'], 'mib': m['capacity_bytes'] / 1048576, 'evidence': 'DESIGN',
               'shared': m['shared_address_space'], 'note': 'Private to %s' % c['id']}
              for c in man['chips'] for m in c['memory']]
    return {'frame': frame, 'frame_stages': stages, 'links': links, 'memory': memory,
            'statement': 'Bars start at zero: the order and overlap of these stages on a real console are not '
                         'known. Grey hatching means not measured. No figure here comes from ARC-1 hardware.'}
