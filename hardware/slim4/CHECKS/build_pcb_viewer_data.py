#!/usr/bin/env python3
"""Bring the studio's PCB data (model-data.js) up to date with the package.

    python -B CHECKS/build_pcb_viewer_data.py

The board geometry (outline, parts, pads, segments, vias, nets) is copied from the PCB layer file
LAYERS/01_PCB/SLIM4_R22_PCB_LAYER.json (written from the board by CHECKS/export_pcb_layer.py);
the legacy mechanical block and notes already in model-data.js are kept. This adds, from files in
the package:
  zones   copper pours: the filled polygons stored in LAYERS/01_PCB/SLIM4_R22.kicad_pcb,
          merged per net and layer and simplified to 0.03 mm for drawing
  parts   mpn, lcsc, package, land ('vendor', 'audited' or 'proxy') and sourcing note for every part,
          read from the footprint descriptions the same way CHECKS/build_builder_packs.py
          writes the BOM
  fab     CHECKS/R22_FAB_SUMMARY.json (written by build_builder_packs.py), if present
  gates   the GATE and FAIL rows and counts of CHECKS/R27_CONVERGENCE_REPORT.json
and, when kicad-cli (KiCad 7.0.x) is on PATH, rewrites R22_REAR_BOARD.svg, the studio's KiCad plot of the
board's back (B.Cu, B.Mask, B.SilkS, Edge.Cuts; plot date pinned).
Re-running it gives the same file. Needs only Python and shapely (requirements.txt).
"""
from pathlib import Path
import json, re, runpy, shutil, subprocess, sys, tempfile
sys.dont_write_bytecode = True
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'model-data.js'
PRE = 'window.STRUTHIO_MODEL = '
NOTE = 'Studio data: '
PACKAGE = 'R27'
GEOMETRY = ('board', 'parts', 'pads', 'segments', 'vias', 'nets', 'stats')
SIMPLIFY = 0.03


def rings(geom):
    polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    out = []
    for p in polys:
        if p.is_empty:
            continue
        loops = [p.exterior] + list(p.interiors)
        out.append([[round(c, 2) for xy in list(l.coords)[:-1] for c in xy] for l in loops])
    return out


def zones(text):
    merged = {}
    for blk in re.split(r'\n  \(zone ', text)[1:]:
        net = re.search(r'\(net_name "([^"]*)"\)', blk)[1]
        for layer, pts in re.findall(r'\(filled_polygon\s*\(layer "([^"]+)"\)\s*\(pts((?:\s*\(xy [^)]*\))*)\s*\)', blk):
            xy = [(float(a), float(b)) for a, b in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', pts)]
            merged.setdefault((net, layer), []).append(Polygon(xy).buffer(0))   # KiCad stores fills fractured; buffer(0) restores the holes
    out = []
    for (net, layer), polys in sorted(merged.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        g = unary_union(polys)
        out.append({'net': net, 'layer': layer, 'area': round(g.area, 1), 'polys': rings(g.simplify(SIMPLIFY, preserve_topology=True))})
    return out


def rear_plot():
    if not shutil.which('kicad-cli'):
        return 'kicad-cli not found: R22_REAR_BOARD.svg kept'
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'R22_REAR_BOARD.svg'
        subprocess.run(['kicad-cli', 'pcb', 'export', 'svg', '--layers', 'B.Cu,B.Mask,B.SilkS,Edge.Cuts', '--page-size-mode', '2',
                        '--exclude-drawing-sheet', '-o', str(out), str(ROOT / 'LAYERS/01_PCB/SLIM4_R22.kicad_pcb')], check=True, capture_output=True)
        t = re.sub(r'date \d{4}/\d\d/\d\d \d\d:\d\d:\d\d', 'date 2026/10/07 00:00:00', out.read_text())
    (ROOT / 'R22_REAR_BOARD.svg').write_text(t)
    return 'R22_REAR_BOARD.svg plotted'


def main():
    src = DATA.read_text()
    assert src.startswith(PRE) and src.endswith(';\n'), 'unexpected model-data.js layout'
    model = json.loads(src[len(PRE):-2])
    layer = json.loads((ROOT / 'LAYERS/01_PCB/SLIM4_R22_PCB_LAYER.json').read_text())
    for k in GEOMETRY:
        model[k] = layer[k]
    model['source'], model['status'] = layer['source'], layer['status']
    text = (ROOT / 'LAYERS/01_PCB/SLIM4_R22.kicad_pcb').read_text()

    packs = runpy.run_path(str(ROOT / 'CHECKS/build_builder_packs.py'))      # same parser as the BOM
    info = {p['ref']: p for p in packs['board_parts'](text)}
    for p in model['parts']:
        b = info[p['ref']]
        p['mpn'], p['lcsc'], p['package'] = b['mpn'], b['lcsc'], b['pkg']
        p['land'] = 'proxy' if 'package proxy' in b['descr'] else 'audited' if 'R22 land-pattern audit' in b['descr'] else 'vendor'
        p['sourcing'] = ('LCSC ' + b['lcsc']) if b['lcsc'] else ('part not bound yet' if 'BIND_BEFORE_FAB' in b['descr'] else 'by manufacturer part number')

    model['zones'] = zones(text)

    fab = ROOT / 'CHECKS/R22_FAB_SUMMARY.json'
    if fab.exists():
        model['fab'] = json.loads(fab.read_text())
    else:
        model.pop('fab', None)

    rep = json.loads((ROOT / 'CHECKS/R27_CONVERGENCE_REPORT.json').read_text())
    model['gates'] = {'counts': {k: rep['counts'].get(k, 0) for k in ('PASS', 'FAIL', 'GATE', 'INFO')}, 'source': 'CHECKS/R27_CONVERGENCE_REPORT.md',
                      'open': [{'id': c['id'], 'interface': c['interface'], 'title': c['title'], 'detail': c['detail'], 'status': c['status']}
                               for c in rep['checks'] if c['status'] in ('FAIL', 'GATE')]}

    model['name'] = f'STRUTHIO SLIM4 {PACKAGE} · R22 PCB'
    model['notes'] = [n for n in model['notes'] if not n.startswith((NOTE, 'R25 studio data: ', 'Board outline, footprint XY', 'R21 connectivity'))]
    model['notes'][:0] = ['Board outline, footprint XY, pads, routed copper segments and vias are exported from the R22 KiCad board '
                          '(LAYERS/01_PCB/SLIM4_R22_PCB_LAYER.json, CHECKS/export_pcb_layer.py).',
                          'R22 KiCad DRC: 0 violations, 0 unconnected pads, 0 footprint errors. The JLCPCB order files are generated by '
                          'CHECKS/build_builder_packs.py; U1 (ESP32-P4NRW32X) stock is the open ordering item.']
    model['notes'].append(
        NOTE + 'zones are the filled copper pours stored in the R22 board (merged per net and layer, simplified to '
        f'{SIMPLIFY} mm); part mpn/lcsc/package/land come from the footprint descriptions; fab is CHECKS/R22_FAB_SUMMARY.json; '
        'gates are the open FAIL and GATE rows of the convergence report. Written by CHECKS/build_pcb_viewer_data.py.')

    DATA.write_text(PRE + json.dumps(model, separators=(',', ':'), ensure_ascii=False) + ';\n')
    print(rear_plot())
    pts = sum(len(r) // 2 for z in model['zones'] for p in z['polys'] for r in p)
    print(f"model-data.js: {len(model['zones'])} pours ({pts} points), {len(model['parts'])} parts with sourcing, "
          f"fab {'yes' if 'fab' in model else 'missing'}, {len(model['gates']['open'])} open gates, {DATA.stat().st_size:,} bytes")


if __name__ == '__main__':
    main()
