#!/usr/bin/env python3
"""R26 single-net router (offline tool; its result, r26_nets.json, is what edit 34 applies).

    python net_router.py <board after edit 32> <out.json>

Reconnects the slow nets edit 31 lifted out of the DSI area: each connection in CONNECT joins two anchors (a pad
centre or a point on copper left in place) with one track of the net's width on F.Cu, In3.Cu or B.Cu, changing layer
through 0.45/0.2 mm vias. A* on a 0.05 mm grid over clearance fields built from all other copper (the new DSI pairs
included, kept 0.3 mm away); deterministic. Needs pcbnew (KiCad 7.0.x), numpy, scipy, matplotlib.
"""
import sys, json, math, heapq
sys.path.append('/usr/lib/python3/dist-packages')
import numpy as np
import pcbnew
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import dsi_pair_router as R

STEP = 0.05
CLR, CLR_DSI, EDGE = 0.12, 0.30, 0.30
VIA_D = 0.45
LAYERS = ('F.Cu', 'In3.Cu', 'B.Cu')
# net: width, list of (from anchor, to anchor); an anchor is (x, y, layer) - layer None for a through via or pad on
# every layer, or the pad's own layer.
CONNECT = {
    'PGOOD_STATUS': (0.152, [((0.699, 76.951, 'F.Cu'), (10.225, 75.537, 'In3.Cu'))]),
    'PWR_WAKE':     (0.152, [((4.575, 78.825, None), (8.603, 75.741, 'In3.Cu'))]),
    'BTN_LEFT':     (0.152, [((5.46, 79.337, None), (-0.027, 99.719, None))]),
    'USB_CURR_OUT2': (0.1, [((4.125, 85.225, None), (-8.4, 75.3, 'F.Cu'))]),
}
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def use_region(box, res):
    """Point the shared field code at this net's search box (fields cover only the box)."""
    R.X0, R.Y0, R.X1, R.Y1, R.RES = box[0] - 1, box[1] - 1, box[2] + 1, box[3] + 1, res
    R.NX, R.NY = int(round((R.X1 - R.X0) / res)) + 1, int(round((R.Y1 - R.Y0) / res)) + 1


def fields(b, net, dsi, done):
    """Clearance fields for routing `net`: the board's copper, the DSI pairs grown to the pair clearance, and the
    connections routed before this one (done: list of (net, width, segments, vias))."""
    F, E = R.base_fields(b, {net})
    for dn, w, segs, vias in done:
        if dn == net: continue
        for lay, pts in segs:
            if lay in F:
                for p, q in zip(pts, pts[1:]): F[lay].capsule(tuple(p), tuple(q), w / 2)
        for v in vias:
            for l in F: F[l].circle(v[0], v[1], VIA_D / 2)
    # the DSI pairs (now routed) get the pair clearance: grow their copper
    for t in b.GetTracks():
        if t.GetNetname() not in dsi: continue
        if t.Type() == pcbnew.PCB_VIA_T:
            for l in F: F[l].circle(R.mm(t.GetPosition().x), R.mm(t.GetPosition().y), VIA_D / 2 + CLR_DSI - CLR)
        else:
            l = t.GetLayerName()
            if l in F: F[l].capsule((R.mm(t.GetStart().x), R.mm(t.GetStart().y)), (R.mm(t.GetEnd().x), R.mm(t.GetEnd().y)),
                                    R.mm(t.GetWidth()) / 2 + CLR_DSI - CLR)
    for l in F: F[l].finish()
    return F, E


def route(F, E, w, a, c, box):
    step = STEP if (box[2] - box[0]) * (box[3] - box[1]) < 2500 else 0.1
    """A* from anchor a to anchor c; state (i, j, layer). 8-neighbour moves, 0.3 mm penalty per bend (on the fly),
    via = layer change at the same cell (cost 1.5) where a via fits."""
    x0, y0, x1, y1 = box
    ni, nj = int((y1 - y0) / step) + 1, int((x1 - x0) / step) + 1
    P = lambda i, j: (x0 + j * step, y0 + i * step)
    need = w / 2 + CLR
    okc, vok = {}, {}

    def ok(i, j, l):
        k = (i, j, l)
        if k not in okc:
            x, y = P(i, j)
            okc[k] = 0 <= i < ni and 0 <= j < nj and F[LAYERS[l]].d(x, y) >= need and E.d(x, y) >= w / 2 + EDGE
        return okc[k]

    def via_ok(i, j):
        if (i, j) not in vok:
            x, y = P(i, j)
            vok[(i, j)] = E.d(x, y) >= VIA_D / 2 + EDGE and all(F[l].d(x, y) >= VIA_D / 2 + CLR for l in F)
        return vok[(i, j)]

    cell = lambda p: (int(round((p[1] - y0) / step)), int(round((p[0] - x0) / step)))
    si, sj = cell(a); gi, gj = cell(c)
    starts = [LAYERS.index(a[2])] if a[2] else [0, 1, 2]
    goals = {LAYERS.index(c[2])} if c[2] else {0, 1, 2}
    openq = []; g = {}; came = {}
    for l in starts:
        s = (si, sj, l, -1); g[s] = 0; came[s] = None; heapq.heappush(openq, (0, 0, s))
    h = lambda i, j: math.hypot(i - gi, j - gj) * step
    n = 0
    while openq:
        f, gc, s = heapq.heappop(openq)
        if gc > g.get(s, 1e9) + 1e-9: continue
        i, j, l, d = s; n += 1
        if (i, j) == (gi, gj) and l in goals:
            path = []; cur = s
            while cur: path.append(cur); cur = came[cur]
            return (path[::-1], step), n
        if n > 4_000_000: break
        nxt = []
        for k, (dx, dy) in enumerate(DIRS):
            if d >= 0 and min((k - d) % 8, (d - k) % 8) > 2: continue   # no turns sharper than 90 degrees
            if ok(i + dy, j + dx, l) or (i + dy, j + dx) == (gi, gj):
                c_ = math.hypot(dx, dy) * step + (0.3 if d >= 0 and k != d else 0)
                nxt.append(((i + dy, j + dx, l, k), c_))
        if via_ok(i, j) or (i, j) in ((si, sj), (gi, gj)):
            for l2 in range(3):
                if l2 != l and ok(i, j, l2): nxt.append(((i, j, l2, d), 1.5))
        for ns, c_ in nxt:
            ng = gc + c_
            if ng < g.get(ns, 1e9) - 1e-9:
                g[ns] = ng; came[ns] = s; heapq.heappush(openq, (ng + h(ns[0], ns[1]), ng, ns))
    return None, n


def to_geometry(path_step, box):
    path, step = path_step
    x0, y0 = box[0], box[1]
    P = lambda st: (round(x0 + st[1] * step, 3), round(y0 + st[0] * step, 3))
    segs, vias = [], []
    run = [path[0]]
    for a, c in zip(path, path[1:]):
        if c[2] != a[2]:
            vias.append(P(a)); segs.append((LAYERS[a[2]], [P(s) for s in run])); run = [c]
        else:
            run.append(c)
    segs.append((LAYERS[run[0][2]], [P(s) for s in run]))
    out = []
    step_dir = lambda p, q: (round((q[0] - p[0]) / max(abs(q[0] - p[0]), abs(q[1] - p[1]))),
                             round((q[1] - p[1]) / max(abs(q[0] - p[0]), abs(q[1] - p[1]))))
    for lay, pts in segs:      # keep corners only (where the grid step changes direction)
        if len(pts) < 2: continue
        k = [pts[0]]
        for p, q, r in zip(pts, pts[1:], pts[2:]):
            if step_dir(p, q) != step_dir(q, r): k.append(q)
        k.append(pts[-1]); out.append((lay, k))
    return out, vias


def main():
    board, out = sys.argv[1], sys.argv[2]
    b = pcbnew.LoadBoard(board)
    dsi = {p[k] for p in R.BREAKOUT.values() for k in ('P', 'N')}
    res = {}; done = []
    for net, (w, conns) in CONNECT.items():
        res[net] = []
        for a, c in conns:
            box = (max(min(a[0], c[0]) - 14, -51), max(min(a[1], c[1]) - 14, 1), min(max(a[0], c[0]) + 14, 51), min(max(a[1], c[1]) + 14, 130))
            use_region(box, 0.025)
            F, E = fields(b, net, dsi, done)
            path, n = route(F, E, w, a, c, box)
            if not path:
                print(f'{net}: {a} -> {c}: NO ROUTE ({n} states)'); res[net].append(None); continue
            segs, vias = to_geometry(path, box)
            L = sum(math.dist(p, q) for _, pts in segs for p, q in zip(pts, pts[1:]))
            print(f'{net}: {a} -> {c}: {L:.1f} mm, {len(vias)} vias, {n} states', flush=True)
            res[net].append(dict(width=w, segments=segs, vias=vias)); done.append((net, w, segs, vias))
    json.dump(res, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
