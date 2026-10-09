#!/usr/bin/env python3
"""Export a KiCad board to the studio's PCB layer JSON (the schema of SLIM4_R21_PCB_LAYER.json).

    python3 CHECKS/export_pcb_layer.py <board.kicad_pcb> <reference layer json> <out.json> <revision> <name> <status>

Example (the package's PCB layer):
    python3 CHECKS/export_pcb_layer.py LAYERS/01_PCB/SLIM4_R25.kicad_pcb REFERENCES/PCB_R21/SLIM4_R21_PCB_LAYER.json \
        LAYERS/01_PCB/SLIM4_R25_PCB_LAYER.json R25 "STRUTHIO SLIM4 PCB R25" "Order files ready · U1 stock to confirm"

Geometry comes from the board (pad positions and rotations as pcbnew places them, so back-side parts at
90/270 degrees are right; the R21 layer file had 80 such pads mirrored), and so do the cut-outs (the battery window). The board's outer
outline and part heights (z) come from the reference layer when the outline is unchanged and the part exists there (heights are not in the board file); new parts get
the height of the reference part with the same footprint package, or a per-category default.
"""
import json, math, sys
import pcbnew

CAT = [('SW', 'switch'), ('U', 'ic'), ('J', 'connector'), ('L', 'inductor'), ('D', 'diode'), ('Q', 'transistor'),
       ('C', 'capacitor'), ('R', 'resistor')]
DEFAULT_Z = {'resistor': 0.75, 'capacitor': 0.75, 'connector': 3.0, 'switch': 1.6, 'ic': 1.0, 'diode': 0.6, 'inductor': 1.6}


def r4(v):
    return round(v + 0.0, 4)


def main():
    pcb, refp, out, rev, name, status = sys.argv[1:7]
    ref = json.load(open(refp))
    b = pcbnew.LoadBoard(pcb); mm = pcbnew.ToMM
    zref = {p['ref']: p['z'] for p in ref['parts']}
    zval = {p['value']: p['z'] for p in ref['parts']}
    parts, pads = [], []
    for f in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
        refd = f.GetReference(); back = f.IsFlipped()
        cat = next((c for pfx, c in CAT if refd.startswith(pfx) and refd[len(pfx):].isdigit()), 'other')
        rot = f.GetOrientationDegrees() % 360
        prot = rot - 360 if rot > 180 else rot          # parts in (-180, 180], as in the R21 layer file
        cy = f.GetCourtyard(pcbnew.B_CrtYd if back else pcbnew.F_CrtYd)
        a = -math.radians(rot); cx, cyy = mm(f.GetPosition().x), mm(f.GetPosition().y)
        xs, ys = [], []
        for i in range(cy.OutlineCount()):
            o = cy.Outline(i)
            for k in range(o.PointCount()):
                dx, dy = mm(o.CPoint(k).x) - cx, mm(o.CPoint(k).y) - cyy
                # undo KiCad's rotation (y down, positive angle = counter-clockwise on screen)
                xs.append(dx * math.cos(a) + dy * math.sin(a)); ys.append(-dx * math.sin(a) + dy * math.cos(a))
        w = round(max(xs) - min(xs), 3) if xs else 0; h = round(max(ys) - min(ys), 3) if ys else 0
        z = zref.get(refd, zval.get(f.GetValue(), DEFAULT_Z.get(cat, 1.0)))
        plist = list(f.Pads())
        parts.append({'ref': refd, 'value': f.GetValue(), 'x': r4(cx), 'y': r4(cyy), 'rot': round(prot, 3), 'side': 'back' if back else 'front',
                      'w': w, 'h': h, 'z': z, 'category': cat, 'padCount': len(plist)})
        for p in plist:
            th = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
            pads.append({'ref': refd, 'num': p.GetNumber(), 'x': r4(mm(p.GetPosition().x)), 'y': r4(mm(p.GetPosition().y)),
                         'w': round(mm(p.GetSize().x), 3), 'h': round(mm(p.GetSize().y), 3), 'rot': round(p.GetOrientationDegrees() % 360, 3),
                         'side': 'both' if th else ('back' if p.IsOnLayer(pcbnew.B_Cu) else 'front'), 'net': p.GetNetCode(), 'netName': p.GetNetname()})
    segs, vias = [], []
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            vias.append({'x': r4(mm(t.GetPosition().x)), 'y': r4(mm(t.GetPosition().y)), 'size': round(mm(t.GetWidth()), 3),
                         'drill': round(mm(t.GetDrillValue()), 3), 'net': t.GetNetCode(), 'netName': t.GetNetname()})
        else:
            segs.append({'x1': r4(mm(t.GetStart().x)), 'y1': r4(mm(t.GetStart().y)), 'x2': r4(mm(t.GetEnd().x)), 'y2': r4(mm(t.GetEnd().y)),
                         'w': round(mm(t.GetWidth()), 3), 'layer': b.GetLayerName(t.GetLayer()), 'net': t.GetNetCode(), 'netName': t.GetNetname()})
    nets = {str(c): n.GetNetname() for c, n in b.GetNetsByNetcode().items()}
    bb = b.GetBoardEdgesBoundingBox()
    board = dict(ref['board'])
    assert abs(mm(bb.GetWidth()) - 0.1 - (board['bbox'][2] - board['bbox'][0])) < 0.05, 'board outline changed: export it too'
    ps = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(ps)   # cut-outs from the board (R23 moved the battery window)
    assert ps.OutlineCount() == 1 and ps.Outline(0).PointCount() == len(board['outer']), 'board outline changed: export it too'
    board['holes'] = [[[round(mm(h.CPoint(k).x), 5), round(mm(h.CPoint(k).y), 5)] for k in range(h.PointCount())]
                      for h in (ps.Hole(0, i) for i in range(ps.HoleCount(0)))]
    data = {'name': name, 'source': pcb.split('/')[-1], 'units': 'mm', 'board': board, 'parts': parts, 'pads': pads,
            'segments': segs, 'vias': vias, 'nets': nets,
            'stats': {'parts': len(parts), 'pads': len(pads), 'tracks': len(segs), 'vias': len(vias), 'nets': len(nets),
                      'boardW': ref['stats']['boardW'], 'boardH': ref['stats']['boardH'], 'thickness': board['thickness']},
            'layer': 'PCB', 'revision': rev, 'status': status}
    json.dump(data, open(out, 'w'), separators=(',', ':'))
    print(json.dumps(data['stats']))


if __name__ == '__main__':
    main()
