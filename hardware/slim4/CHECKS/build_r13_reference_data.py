#!/usr/bin/env python3
"""Write case-r13-data.js: the R13 symmetric-controls prototype (REFERENCES/CASE_R13_CONTROLS_PROTOTYPE/STL) as a
studio reference layer, off by default and labelled PROTOTYPE.

    python3 -B CHECKS/build_r13_reference_data.py

The STLs are read as they are (binary STL, mm, the shared SLIM4 datum) with the same per-triangle shading as the
CASE layer (LAYERS/02_CASE/export_layer_formats.py). Each mesh is checked closed before it is written. Nothing in
the package is changed.
"""
from pathlib import Path
import collections, json, math, struct

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'REFERENCES/CASE_R13_CONTROLS_PROTOTYPE/STL'
OUT = ROOT / 'case-r13-data.js'
PARTS = [('R13_SYMMETRIC_L.stl', 'R13 FLAP CAP L · PROTOTYPE · ACTUATES SW1'),
         ('R13_SYMMETRIC_R.stl', 'R13 FLAP CAP R · PROTOTYPE · ACTUATES SW2'),
         ('R13_SYMMETRIC_DART.stl', 'R13 DART ROCKER · PROTOTYPE · ACTUATES SW3 / SW4')]


def read(path):
    d = path.read_bytes()
    n = struct.unpack_from('<I', d, 80)[0]
    assert len(d) == 84 + 50 * n, f'{path.name}: not a binary STL'
    rows, edges = [], collections.Counter()
    for i in range(n):
        a = struct.unpack_from('<12f', d, 84 + 50 * i)
        p = [[round(a[j], 3), round(a[j + 1], 3), round(a[j + 2], 3)] for j in (3, 6, 9)]
        u = [p[1][k] - p[0][k] for k in range(3)]
        v = [p[2][k] - p[0][k] for k in range(3)]
        nrm = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        rows.append({'p': p, 's': round(0.72 + 0.28 * abs(nrm[2]) / (math.sqrt(sum(k * k for k in nrm)) or 1), 3)})
        r = [tuple(round(t, 4) for t in a[j:j + 3]) for j in (3, 6, 9)]
        for j in range(3):
            edges[tuple(sorted((r[j], r[(j + 1) % 3])))] += 1
    assert all(c == 2 for c in edges.values()), f'{path.name}: mesh is not closed'
    return rows


def main():
    parts = [{'name': name, 'group': 'r13', 'color': '#d36bd8', 'opacity': 0.92, 'triangles': read(SRC / f)} for f, name in PARTS]
    data = {'layer': 'CASE', 'revision': 'R13 controls prototype', 'status': 'reference only: visible caps and rocker mirror-symmetric '
            'about X = +1.2; shell, guides, retention and travel not designed; not print-ready',
            'source': 'REFERENCES/CASE_R13_CONTROLS_PROTOTYPE (supplied with the Stru-dio 0.6.0 workspace)', 'units': 'mm', 'parts': parts}
    OUT.write_text('window.STRUTHIO_CASE_R13=' + json.dumps(data, separators=(',', ':')) + ';\n')
    print(f"case-r13-data.js: {len(parts)} meshes, {sum(len(p['triangles']) for p in parts)} triangles, {OUT.stat().st_size:,} bytes")


if __name__ == '__main__':
    main()
