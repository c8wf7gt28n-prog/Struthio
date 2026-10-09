#!/usr/bin/env python3
"""R26 DSI pair router (offline tool; its result, r26_dsi_routes.json, is what edit 32 applies, so the board build does
not depend on this script).

    python dsi_pair_router.py <board after edit 31> <out.json> [pair order, e.g. D1,D0,CLK]

Needs pcbnew (KiCad 7.0.x) with numpy, scipy and matplotlib. It routes the three MIPI-DSI pairs from U1 to J1 as
coupled pairs, every line taking the same layers and the same number of vias as its partner:

  U1 pads (B.Cu) -> short breakout -> via pair -> In3.Cu (stripline, 0.10 mm / 0.18 mm gap) -> via pair -> F.Cu
  (microstrip, 0.127 mm / 0.18 mm gap) -> J1 pads.

The breakouts at U1 are fixed (BREAKOUT): U1 orders the pins D0_N D0_P CLK_P CLK_N D1_N D1_P on a 0.35 mm pitch, too
tight for three via pairs side by side, so D0's via pair sits just inside the pad row and CLK's and D1's step south.
All three enter J1 from the south. U1 orders CLK P-N but D0 and D1 N-P, while J1 orders all three P-N; CLK's In3
section therefore leaves its via pair northward (its B.Cu stubs run south to the vias, In3 turns back), which keeps
every pair's P on the left of its direction of travel from U1 to J1 with no polarity twist and no extra via.

Between the breakouts and J1 the pair centreline is found by A* on a 0.1 mm grid over clearance fields built from the
board's copper; the In3 -> F.Cu via pair is a 1.2 mm straight macro move whose via row (P, N and a ground via each side
where they fit) must clear every layer. Deterministic.
"""
import sys, json, math, heapq
sys.path.append('/usr/lib/python3/dist-packages')
import numpy as np
from scipy import ndimage
import pcbnew
from matplotlib.path import Path as MPath

GEO = {'F.Cu': (0.127, 0.18), 'B.Cu': (0.127, 0.18), 'In3.Cu': (0.10, 0.18)}   # width, gap per layer
HALF = {l: (w + g) / 2 + w / 2 for l, (w, g) in GEO.items()}                     # half width of the pair copper
CLR, CLR_DSI, EDGE = 0.12, 0.30, 0.30
VIA_D, VIA_P = 0.45, 0.55
RES, STEP = 0.025, 0.1
X0, Y0, X1, Y1 = -12.0, 66.0, 26.0, 104.0
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
N_ = lambda d: (-d[1], d[0])  # left normal in board coordinates (Y down): for d = south (0, 1) it points west

# Fixed breakouts. Each line: list of (layer, [points]) for B.Cu stubs and the In3 taper; vias; then the In3 start state
# (pair centre, direction) the router continues from. P is on the side 'pside' of the centreline (+1 = along N_(d)).
BREAKOUT = {
    'D0': dict(P='MIPI_DSI_D0_P', N='MIPI_DSI_D0_N',
               vias={'N': (-0.275, 88.15), 'P': (0.275, 88.15)},
               stubs={'N': [('B.Cu', [(-0.175, 88.875), (-0.275, 88.15)])],
                      'P': [('B.Cu', [(0.175, 88.875), (0.275, 88.15)])]},
               start=(0.0, 88.7), sdir=(0, 1)),
    'CLK': dict(P='MIPI_DSI_CLK_P', N='MIPI_DSI_CLK_N',
                vias={'P': (0.6, 89.85), 'N': (1.15, 89.85)},
                stubs={'P': [('B.Cu', [(0.525, 88.875), (0.525, 89.45), (0.6, 89.85)])],
                       'N': [('B.Cu', [(0.875, 88.875), (0.875, 89.25), (1.15, 89.6), (1.15, 89.85)])]},
                start=(0.9, 89.3), sdir=(0, -1)),
    'D1': dict(P='MIPI_DSI_D1_P', N='MIPI_DSI_D1_N',
               vias={'N': (1.3, 90.6), 'P': (1.85, 90.6)},
               stubs={'N': [('B.Cu', [(1.225, 88.875), (1.225, 89.2), (1.55, 89.525), (1.55, 90.2), (1.3, 90.6)])],
                      'P': [('B.Cu', [(1.575, 88.875), (1.575, 89.1), (1.85, 89.375), (1.85, 90.6)])]},
               start=(1.6, 91.1), sdir=(0, 1)),
}
GOAL = {   # pair centre and heading where the J1 entry stub starts; pad pitch 0.5
    'CLK': dict(at=(5.9, 75.9), dir=(0, -1), pads={'P': (5.65, 74.15), 'N': (6.15, 74.15)}),
    'D1':  dict(at=(7.4, 75.9), dir=(0, -1), pads={'P': (7.15, 74.15), 'N': (7.65, 74.15)}),
    'D0':  dict(at=(8.9, 75.9), dir=(0, -1), pads={'P': (8.65, 74.15), 'N': (9.15, 74.15)}),
}

mm = pcbnew.ToMM
NX, NY = int(round((X1 - X0) / RES)) + 1, int(round((Y1 - Y0) / RES)) + 1


def fidx(x, y): return int(round((y - Y0) / RES)), int(round((x - X0) / RES))


class Field:
    def __init__(self): self.mask = np.zeros((NY, NX), bool)

    def _box(self, x0, y0, x1, y1):
        i0, j0 = fidx(x0, y0); i1, j1 = fidx(x1, y1)
        return max(i0, 0), max(j0, 0), min(i1 + 1, NY), min(j1 + 1, NX)

    def circle(self, x, y, r):
        i0, j0, i1, j1 = self._box(x - r, y - r, x + r, y + r)
        if i0 >= i1 or j0 >= j1: return
        yy, xx = np.mgrid[i0:i1, j0:j1]
        self.mask[i0:i1, j0:j1] |= (X0 + xx * RES - x) ** 2 + (Y0 + yy * RES - y) ** 2 <= r * r

    def capsule(self, a, c, r):
        i0, j0, i1, j1 = self._box(min(a[0], c[0]) - r, min(a[1], c[1]) - r, max(a[0], c[0]) + r, max(a[1], c[1]) + r)
        if i0 >= i1 or j0 >= j1: return
        yy, xx = np.mgrid[i0:i1, j0:j1]; px, py = X0 + xx * RES, Y0 + yy * RES
        dx, dy = c[0] - a[0], c[1] - a[1]; L2 = dx * dx + dy * dy
        t = np.clip(((px - a[0]) * dx + (py - a[1]) * dy) / L2, 0, 1) if L2 > 0 else 0
        self.mask[i0:i1, j0:j1] |= (px - a[0] - t * dx) ** 2 + (py - a[1] - t * dy) ** 2 <= r * r

    def poly(self, pts, outside=False):
        path = MPath(pts)
        if outside:
            yy, xx = np.mgrid[0:NY, 0:NX]
            ins = path.contains_points(np.c_[(X0 + xx * RES).ravel(), (Y0 + yy * RES).ravel()]).reshape(NY, NX)
            self.mask |= ~ins; return
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        i0, j0, i1, j1 = self._box(min(xs), min(ys), max(xs), max(ys))
        if i0 >= i1 or j0 >= j1: return
        yy, xx = np.mgrid[i0:i1, j0:j1]
        self.mask[i0:i1, j0:j1] |= path.contains_points(np.c_[(X0 + xx * RES).ravel(), (Y0 + yy * RES).ravel()]).reshape(i1 - i0, j1 - j0)

    def finish(self): self.dist = ndimage.distance_transform_edt(~self.mask) * RES - RES / 2

    def d(self, x, y):
        i, j = fidx(x, y)
        return float(self.dist[i, j]) if 0 <= i < NY and 0 <= j < NX else -1.0


def pts_of(sps, k, hole=None):
    o = sps.Outline(k) if hole is None else sps.Hole(k, hole)
    return [(mm(o.CPoint(i).x), mm(o.CPoint(i).y)) for i in range(o.PointCount())]


def base_fields(b, skip):
    layers = ('F.Cu', 'B.Cu', 'In3.Cu')
    F = {l: Field() for l in layers}; lid = {l: b.GetLayerID(l) for l in layers}
    for t in b.GetTracks():
        if t.GetNetname() in skip: continue
        if t.Type() == pcbnew.PCB_VIA_T:
            for l in layers: F[l].circle(mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetWidth()) / 2)
            continue
        for l in layers:
            if t.GetLayer() == lid[l]:
                F[l].capsule((mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y)), mm(t.GetWidth()) / 2)
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() in skip: continue
            for l in layers:
                if not p.IsOnLayer(lid[l]): continue
                sp = p.GetEffectivePolygon()
                for k in range(sp.OutlineCount()): F[l].poly(pts_of(sp, k))
                if p.GetDrillSizeX() > 0: F[l].circle(mm(p.GetPosition().x), mm(p.GetPosition().y), mm(p.GetDrillSizeX()) / 2 + 0.15)
    for f in b.GetFootprints():                      # the DSI pads themselves (U1, J1) block every other route
        for p in f.Pads():
            if p.GetNetname() not in skip: continue
            for l in layers:
                if p.IsOnLayer(lid[l]):
                    sp = p.GetEffectivePolygon()
                    for k in range(sp.OutlineCount()): F[l].poly(pts_of(sp, k))
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname() in skip or z.GetNetname() == 'GND': continue
        for l in layers:
            if z.IsOnLayer(lid[l]):
                fp = z.GetFilledPolysList(lid[l])
                for k in range(fp.OutlineCount()): F[l].poly(pts_of(fp, k))
    edge = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(edge)
    E = Field(); E.poly(pts_of(edge, 0), outside=True)
    for h in range(edge.HoleCount(0)): E.poly(pts_of(edge, 0, h))
    E.finish()
    return F, E


def add_pair_obstacles(F, geo, grow=CLR_DSI - CLR):
    """Copper of another pair (tracks per layer, vias), grown so the board clearance check becomes the pair-to-pair one
    (breakouts: grow 0, the plain board clearance)."""
    for lay, a, c, w in geo['tracks']:
        F[lay].capsule(a, c, w / 2 + grow)
    for v in geo['vias']:
        for l in F: F[l].circle(v[0], v[1], VIA_D / 2 + grow)


class Search:
    def __init__(self, F, E): self.F, self.E = F, E

    def ok(self, layer, x, y):
        return self.F[layer].d(x, y) >= HALF[layer] + CLR and self.E.d(x, y) >= HALF[layer] + EDGE

    def via_row(self, x, y, d, flanks):
        n = N_(unit(d)); ks = (-1.5, -0.5, 0.5, 1.5) if flanks else (-0.5, 0.5)
        for k in ks:
            vx, vy = x + n[0] * k * VIA_P, y + n[1] * k * VIA_P
            if self.E.d(vx, vy) < VIA_D / 2 + EDGE: return False
            for l in self.F:
                if self.F[l].d(vx, vy) < VIA_D / 2 + CLR: return False
        return True

    def route(self, start, sdir, goal, gdir, soft=None, hist=None, pres=0.0):
        """soft[li], hist[li]: coarse (STEP) arrays for In3 (0) and F.Cu (1); a step into a cell costs its length times
        (1 + hist) plus pres where another pair's copper would come too close (negotiated congestion)."""
        layers = ('In3.Cu', 'F.Cu')
        P = lambda i, j: (X0 + j * STEP, Y0 + i * STEP)
        si, sj = int(round((start[1] - Y0) / STEP)), int(round((start[0] - X0) / STEP))
        gi, gj = int(round((goal[1] - Y0) / STEP)), int(round((goal[0] - X0) / STEP))
        okc = {}
        via_soft = None if soft is None else np.maximum(soft[0], soft[1])

        def ok(i, j, li):
            k = (i, j, li)
            if k not in okc: okc[k] = self.ok(layers[li], *P(i, j))
            return okc[k]
        s0 = (si, sj, DIRS.index(sdir), 0)
        h = lambda i, j: math.hypot(i - gi, j - gj) * STEP
        openq = [(h(si, sj), 0.0, s0)]; came = {s0: None}; g = {s0: 0.0}; via = {}
        n = 0
        while openq:
            f, gc, s = heapq.heappop(openq)
            if gc > g.get(s, 1e9) + 1e-9: continue
            n += 1
            if n > 3_000_000: break
            i, j, di, li = s
            if (i, j) == (gi, gj) and DIRS[di] == gdir and li == 1:
                path = []; cur = s
                while cur: path.append(cur); cur = came[cur]
                return path[::-1], via, n
            dx, dy = DIRS[di]; sl = math.hypot(dx, dy) * STEP
            cand = []
            if ok(i + dy, j + dx, li): cand.append(((i + dy, j + dx, di, li), sl, None))
            for t in (-1, 1):
                nd = (di + t) % 8; ex, ey = DIRS[nd]; ci, cj, good = i, j, True
                for _ in range(3):
                    ci, cj = ci + ey, cj + ex
                    if not ok(ci, cj, li): good = False; break
                if good: cand.append(((ci, cj, nd, li), 3 * math.hypot(ex, ey) * STEP + 0.6, None))
            if li == 0:
                ns = int(round(1.2 / sl)); half = ns // 2; ci, cj, good = i, j, True
                for k in range(1, ns + 1):
                    ci, cj = ci + dy, cj + dx
                    if not ok(ci, cj, 0 if k < half else 1): good = False; break
                mx, my = P(i + dy * half, j + dx * half)
                if good:
                    for flanks, cost in ((True, 2.0), (False, 6.0)):
                        if self.via_row(mx, my, (dx, dy), flanks):
                            cand.append(((ci, cj, di, 1), ns * sl + cost, (round(mx, 3), round(my, 3), flanks))); break
            for ns_, c, v in cand:
                if soft is not None:
                    a_i, a_j, a_l = ns_[0], ns_[1], ns_[3]
                    c = c * (1 + hist[a_l][a_i, a_j]) + pres * soft[a_l][a_i, a_j]
                    if v: c += pres * via_soft[a_i, a_j]
                ng = gc + c
                if ng < g.get(ns_, 1e9) - 1e-9:
                    g[ns_] = ng; came[ns_] = s
                    if v: via[ns_] = v
                    else: via.pop(ns_, None)
                    heapq.heappush(openq, (ng + h(ns_[0], ns_[1]), ng, ns_))
        return None, None, n


def unit(d):
    L = math.hypot(*d); return (d[0] / L, d[1] / L)


def corners(path):
    """Grid path -> list of (x, y, layer index) corners; the via macro keeps its direction."""
    X = lambda st: (round(X0 + st[1] * STEP, 3), round(Y0 + st[0] * STEP, 3))
    out = [(*X(path[0]), path[0][3])]
    for a, c in zip(path, path[1:]):
        if c[2] != a[2] or c[3] != a[3]: out.append((*X(a), a[3]))
    out.append((*X(path[-1]), path[-1][3]))
    clean = [out[0]]
    for p in out[1:]:
        if (p[0], p[1]) != (clean[-1][0], clean[-1][1]) or p[2] != clean[-1][2]: clean.append(p)
    return clean


def pair_copper(name, pts, vrow):
    """Centreline segments per layer and via-row positions of a routed pair."""
    tr = []
    for a, c in zip(pts, pts[1:]):
        lay = ('In3.Cu', 'F.Cu')[c[2]] if a[2] == c[2] else 'F.Cu'
        tr.append((lay, a[:2], c[:2]))
    vx, vy, fl = vrow
    a, c = next((a, c) for a, c in zip(pts, pts[1:]) if a[2] != c[2])
    nrm = N_(unit((c[0] - a[0], c[1] - a[1])))
    row = [(vx + nrm[0] * k * VIA_P, vy + nrm[1] * k * VIA_P) for k in ((-1.5, -0.5, 0.5, 1.5) if fl else (-0.5, 0.5))]
    return tr, row


def soft_mask(others):
    """Coarse cells where this pair's centreline would come closer than CLR_DSI to the other pairs' copper, per layer
    (0 In3, 1 F.Cu)."""
    ny, nx = int(round((Y1 - Y0) / STEP)) + 1, int(round((X1 - X0) / STEP)) + 1
    yy, xx = np.mgrid[0:ny, 0:nx]; px, py = X0 + xx * STEP, Y0 + yy * STEP
    out = [np.zeros((ny, nx), float), np.zeros((ny, nx), float)]
    for tr, row in others:
        for lay, a, c in tr:
            li = 0 if lay == 'In3.Cu' else 1
            r = HALF[lay] * 2 + CLR_DSI
            lo_i, hi_i = int((min(a[1], c[1]) - r - Y0) / STEP) - 1, int((max(a[1], c[1]) + r - Y0) / STEP) + 2
            lo_j, hi_j = int((min(a[0], c[0]) - r - X0) / STEP) - 1, int((max(a[0], c[0]) + r - X0) / STEP) + 2
            sl = (slice(max(lo_i, 0), hi_i), slice(max(lo_j, 0), hi_j))
            X, Y = px[sl], py[sl]; dx, dy = c[0] - a[0], c[1] - a[1]; L2 = dx * dx + dy * dy
            t = np.clip(((X - a[0]) * dx + (Y - a[1]) * dy) / L2, 0, 1) if L2 > 0 else 0
            out[li][sl] += ((X - a[0] - t * dx) ** 2 + (Y - a[1] - t * dy) ** 2 < r * r)
        for v in row:
            for li, lay in enumerate(('In3.Cu', 'F.Cu')):
                r = VIA_D / 2 + HALF[lay] + CLR_DSI
                out[li] += ((px - v[0]) ** 2 + (py - v[1]) ** 2 < r * r)
    return [np.minimum(o, 1.0) for o in out]


def main():
    board, out = sys.argv[1], sys.argv[2]
    order = sys.argv[3].split(',') if len(sys.argv) > 3 else ['D0', 'D1', 'CLK']
    rounds = int(sys.argv[4]) if len(sys.argv) > 4 else 40
    b = pcbnew.LoadBoard(board)
    dsi = {p[k] for p in BREAKOUT.values() for k in ('P', 'N')}
    F0, E = base_fields(b, dsi)
    fixed = {}
    for name, bo in BREAKOUT.items():
        tr = [(lay, a, c, GEO[lay][0]) for side in ('P', 'N') for lay, pts in bo['stubs'][side] for a, c in zip(pts, pts[1:])]
        fixed[name] = dict(tracks=tr, vias=list(bo['vias'].values()))
    searches = {}
    for name in order:   # hard obstacles: board copper, the other pairs' breakouts, own breakout vias
        F = {l: Field() for l in F0}
        for l in F: F[l].mask = F0[l].mask.copy()
        for other, geo in fixed.items():
            if other != name: add_pair_obstacles(F, geo, 0.0)
            else:
                for v in geo['vias']:
                    for l in F: F[l].circle(v[0], v[1], VIA_D / 2)
        for other in BREAKOUT:   # the other pairs' J1 entries stay free
            if other == name: continue
            ga, gd = GOAL[other]['at'], GOAL[other]['dir']
            F['F.Cu'].capsule((ga[0] - gd[0] * 0.8, ga[1] - gd[1] * 0.8), (ga[0] + gd[0] * 1.2, ga[1] + gd[1] * 1.2), HALF['F.Cu'] + CLR_DSI - CLR)
        for l in F: F[l].finish()
        searches[name] = Search(F, E)
    ny, nx = int(round((Y1 - Y0) / STEP)) + 1, int(round((X1 - X0) / STEP)) + 1
    hist = {n: [np.zeros((ny, nx)), np.zeros((ny, nx))] for n in order}
    cur = {}; pres = 0.5
    for it in range(rounds):
        conflicts = 0
        for name in order:
            others = [cur[o][:2] for o in order if o != name and o in cur]
            soft = soft_mask(others)
            bo, go = BREAKOUT[name], GOAL[name]
            path, vias, n = searches[name].route(bo['start'], bo['sdir'], go['at'], go['dir'], soft, hist[name], pres)
            if not path:
                print(f'round {it}: {name} NO ROUTE ({n} states)', flush=True); return
            pts = corners(path); vrow = [v for st, v in vias.items() if st in set(path)][0]
            cur[name] = pair_copper(name, pts, vrow) + (pts, vrow)
            # cells of this path that conflict with the others
            bad = 0
            for st in path:
                if soft[st[3]][st[0], st[1]] > 0:
                    bad += 1; hist[name][st[3]][st[0], st[1]] += 0.4
            conflicts += bad
        lens = {nm: round(sum(math.dist(a[:2], c[:2]) for a, c in zip(cur[nm][2], cur[nm][2][1:])), 2) for nm in order}
        print(f'round {it}: conflict cells {conflicts}, pres {pres:.2f}, lengths {lens}', flush=True)
        if conflicts == 0: break
        pres *= 1.5
    result = {}
    for name in order:
        tr, row, pts, vrow = cur[name]
        result[name] = dict(corners=[[p[0], p[1], ('In3.Cu', 'F.Cu')[p[2]]] for p in pts], via=list(vrow))
    json.dump(dict(geo=GEO, breakout=BREAKOUT, goal=GOAL, order=order, converged=conflicts == 0, pairs=result),
              open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
