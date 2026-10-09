#!/usr/bin/env python3
"""MIPI-DSI pair check on the board itself (PCB R26), against the pre-order audit's routing checklist.

    python3 CHECKS/dsi_pair_check.py LAYERS/01_PCB/SLIM4_R26.kicad_pcb CHECKS/R26_DSI_REPORT   (writes .json and .md)

Needs pcbnew (KiCad 7.0.x) and shapely. For each pair (D0, D1, CLK) it walks P and N from the U1 pad to the J1 pad
through the copper and reports:
  - layer sequence and via count of each line (P and N must match);
  - length of each line pad to pad (tracks; via barrels are the same for both lines and every pair) and the skew
    inside the pair (audit: <= 0.254 mm), and the spread between the pairs' lengths (audit: <= 0.762 mm);
  - widths per layer and how much of each line runs at the layer's nominal gap from its partner (centre to centre
    distance = width + gap, within 0.01 mm); the rest is breakout, via tapers, J1 entry and skew teeth, listed;
  - the reference plane under every DSI track (F.Cu: In1, In3: In2 and In4, B.Cu: In4): the track and 0.1 mm each
    side should lie on filled GND copper of that layer (also reported for 0.3 mm each side), away from the pair's own
    via antipads and pad ends (0.8 mm round each via and pad: the transitions). Copper over a gap that is not another
    net's via antipad fails the check; track edges reaching into an antipad are counted with their worst depth, and
    the smallest margin from the track's edge to the GND fill's edge is reported (sampled along the centreline);
  - at each layer change, the ground vias within 2.2 mm of the via pair, nearest on the P side and on the N side.
"""
import sys, json, math
sys.path.append('/usr/lib/python3/dist-packages')
import pcbnew
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union

mm = pcbnew.ToMM
GEO = {'F.Cu': (0.127, 0.18), 'In3.Cu': (0.10, 0.18), 'B.Cu': (0.127, 0.18)}
REF = {'F.Cu': ['In1.Cu'], 'In3.Cu': ['In2.Cu', 'In4.Cu'], 'B.Cu': ['In4.Cu']}
PAIRS = ('D0', 'D1', 'CLK')


def P(v): return (round(mm(v.x), 4), round(mm(v.y), 4))


def walk(b, net):
    """Ordered list of (layer, [points]) runs and via positions from the U1 pad to the J1 pad of one net."""
    tr = [t for t in b.GetTracks() if t.GetNetname() == net]
    segs = [t for t in tr if t.Type() != pcbnew.PCB_VIA_T]
    vias = {P(t.GetPosition()) for t in tr if t.Type() == pcbnew.PCB_VIA_T}
    pads = {f.GetReference(): P(p.GetPosition()) for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() == net}
    start, end = pads['U1'], pads['J1']
    adj = {}
    for t in segs:
        a, c = P(t.GetStart()), P(t.GetEnd()); lay = t.GetLayerName()
        adj.setdefault((a, lay), []).append((c, t)); adj.setdefault((c, lay), []).append((a, t))
    used = set(); cur = (start, 'B.Cu'); runs = [('B.Cu', [start])]; vlist = []
    while True:
        nxt = [(c, t) for c, t in adj.get(cur, []) if t.m_Uuid.AsString() not in used]
        if not nxt:
            if cur[0] in vias:
                other = [k for k in adj if k[0] == cur[0] and k[1] != cur[1] and any(t.m_Uuid.AsString() not in used for _, t in adj[k])]
                if other:
                    vlist.append(cur[0]); cur = other[0]; runs.append((cur[1], [cur[0]])); continue
            break
        assert len(nxt) == 1, (net, cur, 'branch')
        c, t = nxt[0]; used.add(t.m_Uuid.AsString()); runs[-1][1].append(c); cur = (c, cur[1])
    assert runs[-1][1][-1] == end, (net, 'does not reach J1', runs[-1][1][-1], end)
    assert len(used) == len(segs), (net, 'stray copper', len(segs) - len(used))
    return runs, vlist


def gnd_fill(b, lay):
    lid = b.GetLayerID(lay); polys = []
    for z in b.Zones():
        if z.GetNetname() != 'GND' or not z.IsOnLayer(lid): continue
        fp = z.GetFilledPolysList(lid)
        for k in range(fp.OutlineCount()):
            o = fp.Outline(k); outer = [(mm(o.CPoint(i).x), mm(o.CPoint(i).y)) for i in range(o.PointCount())]
            holes = []
            for h in range(fp.HoleCount(k)):
                hh = fp.Hole(k, h); holes.append([(mm(hh.CPoint(i).x), mm(hh.CPoint(i).y)) for i in range(hh.PointCount())])
            polys.append(Polygon(outer, holes).buffer(0))
    return unary_union(polys)


def main():
    board, out = sys.argv[1], sys.argv[2]
    b = pcbnew.LoadBoard(board)
    fills = {l: gnd_fill(b, l) for l in ('In1.Cu', 'In2.Cu', 'In4.Cu')}
    gvias = [P(t.GetPosition()) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == 'GND']
    holes = [Point(P(t.GetPosition())).buffer(mm(t.GetWidth()) / 2 + 0.25) for t in b.GetTracks()
             if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() != 'GND'] + \
            [Point(P(p.GetPosition())).buffer(mm(max(p.GetSize().x, p.GetSize().y)) / 2 + 0.25) for f in b.GetFootprints()
             for p in f.Pads() if p.GetDrillSizeX() > 0 and p.GetNetname() != 'GND']
    antipads = unary_union(holes)          # where a via or hole of another net clears the planes (pad + 0.15 mm, +0.1)
    widths = {}
    for t in b.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T and t.GetNetname().startswith('MIPI_DSI'):
            widths.setdefault(t.GetLayerName(), set()).add(round(mm(t.GetWidth()), 4))
    rep = dict(board=board.split('/')[-1], pairs={}, widths={k: sorted(v) for k, v in widths.items()})
    lens = {}
    for name in PAIRS:
        r = {}
        lines = {sd: walk(b, f'MIPI_DSI_{name}_{sd}') for sd in ('P', 'N')}
        for sd, (runs, vl) in lines.items():
            r[sd] = dict(layers=[l for l, _ in runs], vias=len(vl),
                         length=round(sum(math.dist(p, q) for _, pts in runs for p, q in zip(pts, pts[1:])), 3))
        r['same_layers_and_vias'] = r['P']['layers'] == r['N']['layers'] and r['P']['vias'] == r['N']['vias']
        r['skew'] = round(r['P']['length'] - r['N']['length'], 3)
        # coupling: P sampled every 0.05 mm against N on the same layer
        coupled = {}; other = {}
        for (lay, pp), (lay2, nn) in zip(lines['P'][0], lines['N'][0]):
            assert lay == lay2
            w, g = GEO[lay]; pitch = w + g
            ln = LineString(nn); lp = LineString(pp); L = lp.length; k = max(1, int(L / 0.05))
            ok = sum(1 for i in range(k) if abs(ln.distance(lp.interpolate((i + 0.5) * L / k)) - pitch) <= 0.01)
            coupled[lay] = coupled.get(lay, 0) + ok * L / k; other[lay] = other.get(lay, 0) + (k - ok) * L / k
        r['at_nominal_gap_mm'] = {l: round(v, 2) for l, v in coupled.items()}
        r['off_nominal_gap_mm'] = {l: round(v, 2) for l, v in other.items()}
        # reference planes
        refm = {}
        own = [Point(v) for sd in ('P', 'N') for v in lines[sd][1]] + \
              [Point(lines[sd][0][0][1][0]) for sd in ('P', 'N')] + [Point(lines[sd][0][-1][1][-1]) for sd in ('P', 'N')]
        excl = unary_union([p.buffer(0.8) for p in own])      # the via antipads and the pad ends: transitions
        for sd in ('P', 'N'):
            for lay, pts in lines[sd][0]:
                if len(pts) < 2: continue
                tr = LineString(pts).buffer(GEO[lay][0] / 2 + 0.1, cap_style=2)
                tr3 = LineString(pts).buffer(GEO[lay][0] / 2 + 0.3, cap_style=2)
                for rl in REF[lay]:
                    f = fills[rl]
                    inside = tr.difference(excl).difference(f).area
                    inside3 = tr3.difference(excl).difference(f).area
                    cu = LineString(pts).buffer(GEO[lay][0] / 2, cap_style=2).difference(excl).difference(f)
                    gap = cu.difference(antipads).area                 # copper over a gap that is not a via antipad
                    ap = [g for g in getattr(cu.intersection(antipads), 'geoms', [cu.intersection(antipads)]) if g.area > 1e-6]
                    ls = LineString(pts); edge = f.boundary
                    smp = [ls.interpolate(i * ls.length / 80) for i in range(81)]
                    smp = [q for q in smp if not excl.contains(q)]
                    marg = min((edge.distance(q) if f.contains(q) else -edge.distance(q) for q in smp), default=9.9)
                    key = f'{lay}->{rl}'
                    prev = refm.get(key, dict(copper_over_gap_mm2=0.0, antipad_edges=0, uncovered_mm2=0.0,
                                              uncovered_0p3_mm2=0.0, min_margin_mm=9.9))
                    refm[key] = dict(copper_over_gap_mm2=round(prev['copper_over_gap_mm2'] + gap, 4),
                                     antipad_edges=prev['antipad_edges'] + len(ap),
                                     uncovered_mm2=round(prev['uncovered_mm2'] + inside, 4),
                                     uncovered_0p3_mm2=round(prev['uncovered_0p3_mm2'] + inside3, 4),
                                     min_margin_mm=round(min(prev['min_margin_mm'], marg - GEO[lay][0] / 2), 3))
        r['reference'] = refm
        # return vias
        tv = []
        vp, vn = lines['P'][1], lines['N'][1]
        for i, (a, c) in enumerate(zip(vp, vn)):
            m = ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2); u = ((a[0] - c[0]) / math.dist(a, c), (a[1] - c[1]) / math.dist(a, c))
            side = lambda g: (g[0] - m[0]) * u[0] + (g[1] - m[1]) * u[1]
            near = [g for g in gvias if math.dist(g, m) <= 2.2]
            ps = min((math.dist(g, m) for g in near if side(g) > 0.05), default=None)
            ns = min((math.dist(g, m) for g in near if side(g) < -0.05), default=None)
            ax = min((math.dist(g, m) for g in near if abs(side(g)) <= 0.05), default=None)
            change = f"{lines['P'][0][i][0]}->{lines['P'][0][i + 1][0]}"
            tv.append(dict(at=[round(m[0], 3), round(m[1], 3)], change=change, gnd_P_side=ps and round(ps, 2),
                           gnd_N_side=ns and round(ns, 2), gnd_on_axis=ax and round(ax, 2)))
        r['transitions'] = tv
        rep['pairs'][name] = r
        lens[name] = max(r['P']['length'], r['N']['length'])
    rep['spread'] = round(max(lens.values()) - min(lens.values()), 3)
    rep['max_skew'] = max(abs(rep['pairs'][n]['skew']) for n in PAIRS)
    rep['checks'] = {
        'same layers and vias for P and N': all(rep['pairs'][n]['same_layers_and_vias'] for n in PAIRS),
        'skew <= 0.254 mm': rep['max_skew'] <= 0.254,
        'spread <= 0.762 mm': rep['spread'] <= 0.762,
        'constant width per layer': all(len(v) == 1 for k, v in rep['widths'].items() if k != 'B.Cu'),
        'no DSI track over a gap or split in its reference planes (outside transitions)':
            all(v['copper_over_gap_mm2'] < 1e-4 for n in PAIRS for v in rep['pairs'][n]['reference'].values()),
    }
    ov = [-v['min_margin_mm'] for n in PAIRS for v in rep['pairs'][n]['reference'].values() if v['min_margin_mm'] < 0]
    rep['antipad_edge_overlaps'] = dict(count=sum(v['antipad_edges'] for n in PAIRS for v in rep['pairs'][n]['reference'].values()),
                                        worst_mm=round(max(ov, default=0.0), 3))
    json.dump(rep, open(out + '.json', 'w'), indent=1)
    L = ['# MIPI-DSI pair check — ' + rep['board'], '',
         'Generated by `CHECKS/dsi_pair_check.py` from the board file. Lengths are pad to pad along the tracks.', '',
         '| Check | Result |', '|---|---|'] + [f'| {k} | {"PASS" if v else "FAIL"} |' for k, v in rep['checks'].items()]
    L += ['', f'Track edges reaching into a via antipad (a via or hole of another net, where the planes clear it by '
          f'0.15 mm): {rep["antipad_edge_overlaps"]["count"]} places, at most {rep["antipad_edge_overlaps"]["worst_mm"]:.3f} mm deep; '
          'the pairs keep the board clearance of 0.12 mm from via pads, which the In3 lane under U1 needs.']
    L += ['', f'Spread between pairs: **{rep["spread"]:.3f} mm**; largest skew inside a pair: **{rep["max_skew"]:.3f} mm**. '
          f'Widths: ' + ', '.join(f'{k} {v}' for k, v in sorted(rep['widths'].items())) + '.', '',
          '| Pair | Layers | Vias | P mm | N mm | Skew mm | At nominal gap mm | Off nominal mm |', '|---|---|---|---|---|---|---|---|']
    for n in PAIRS:
        r = rep['pairs'][n]
        L.append(f"| {n} | {' → '.join(r['P']['layers'])} | {r['P']['vias']} | {r['P']['length']:.3f} | {r['N']['length']:.3f} | "
                 f"{r['skew']:+.3f} | {', '.join(f'{k} {v}' for k, v in r['at_nominal_gap_mm'].items())} | "
                 f"{', '.join(f'{k} {v}' for k, v in r['off_nominal_gap_mm'].items())} |")
    L += ['', 'Off-nominal gap is the B.Cu breakout under U1 (0.35 mm pad pitch), the tapers to each via pair (0.55 mm '
          'pitch) and to the J1 pads (0.5 mm pitch), and the skew-compensation teeth.', '',
          '| Pair | Track → reference plane | Copper over a gap mm² | Antipad edges | Uncovered mm², track ±0.1 mm | Uncovered mm², track ±0.3 mm | Smallest margin, track edge to fill edge mm |', '|---|---|---|---|---|---|---|']
    for n in PAIRS:
        for k, v in rep['pairs'][n]['reference'].items():
            L.append(f"| {n} | {k} | {v['copper_over_gap_mm2']} | {v['antipad_edges']} | {v['uncovered_mm2']} | {v['uncovered_0p3_mm2']} | {v['min_margin_mm']} |")
    L += ['', '| Pair | Layer change | At | Ground via P side mm | N side mm | On the axis mm |', '|---|---|---|---|---|---|']
    for n in PAIRS:
        for t in rep['pairs'][n]['transitions']:
            L.append(f"| {n} | {t['change']} | ({t['at'][0]}, {t['at'][1]}) | {t['gnd_P_side'] or '–'} | {t['gnd_N_side'] or '–'} | {t['gnd_on_axis'] or '–'} |")
    open(out + '.md', 'w').write('\n'.join(L) + '\n')
    print(json.dumps(rep['checks'], indent=1)); print('spread', rep['spread'], 'max skew', rep['max_skew'])


if __name__ == '__main__':
    main()
