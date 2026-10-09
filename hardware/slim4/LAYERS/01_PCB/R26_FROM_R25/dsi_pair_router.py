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
                      'P': [('B.Cu', [(1.575, 88.875), (1.575, 89.2), (1.85, 89.475), (1.85, 90.6)])]},
               start=(1.6, 91.1), sdir=(0, 1)),
}
GOAL = {   # pair centre and heading where the J1 entry stub starts; pad pitch 0.5
    'CLK': dict(at=(5.9, 75.9), dir=(0, -1), pads={'P': (5.65, 74.15), 'N': (6.15, 74.15)}),
    'D1':  dict(at=(7.4, 75.9), dir=(0, -1), pads={'P': (7.15, 74.15), 'N': (7.65, 74.15)}),
    'D0':  dict(at=(8.9, 75.9), dir=(0, -1), pads={'P': (8.65, 74.15), 'N': (9.15, 74.15)}),
}

# Corridor assignment (keep-outs per pair: layer, x0, y0, x1, y1). The negotiation below settles clearances but cannot
# untangle a crossing on one layer, so which way round U1 each pair goes is fixed here.
TOPOLOGY = {
    'east_d0': {'D0': [('F.Cu', -12, 76.8, 5.2, 104)],
                'D1': [('F.Cu', 11.0, 66, 26, 104), ('In3.Cu', 11.0, 66, 26, 104)],
                'CLK': [('F.Cu', 11.0, 66, 26, 104), ('In3.Cu', 11.0, 66, 26, 104)]},
    'west_all': {n: [('F.Cu', 11.0, 66, 26, 104), ('In3.Cu', 11.0, 66, 26, 104), ('F.Cu', -12, 66, -3.0, 104),
                     ('In3.Cu', -12, 66, -3.0, 104)] for n in ('D0', 'D1', 'CLK')},
    'clk_west': {'CLK': [('F.Cu', -0.9, 78.6, 26, 104)]},
    'three_ways': {'CLK': [('F.Cu', -0.9, 78.6, 26, 104)],
                   'D0': [('F.Cu', -12, 76.8, 5.2, 104)],
                   'D1': [('F.Cu', 11.0, 66, 26, 104), ('In3.Cu', 11.0, 66, 26, 104)]},
    'three_ways2': {'CLK': [('F.Cu', -0.9, 78.6, 26, 104), ('In3.Cu', 1.7, 86.0, 26, 104)],
                    'D0': [('F.Cu', -12, 76.8, 5.2, 104), ('In3.Cu', -3.0, 88.5, 0.6, 92.0)],
                    'D1': [('F.Cu', 11.0, 66, 26, 104), ('In3.Cu', 11.0, 66, 26, 104), ('F.Cu', -12, 66, -0.9, 104)]},
    'pairs_east': {'D0': [('F.Cu', -12, 76.8, 5.2, 104)], 'D1': [('F.Cu', -12, 76.8, 5.2, 104)]},
    'none': {},
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

    def finish(self): self.dist = (ndimage.distance_transform_edt(~self.mask) * RES - RES / 2).astype(np.float32)

    def d(self, x, y):
        i, j = fidx(x, y)
        return float(self.dist[i, j]) if 0 <= i < NY and 0 <= j < NX else -1.0


def pts_of(sps, k, hole=None):
    o = sps.Outline(k) if hole is None else sps.Hole(k, hole)
    return [(mm(o.CPoint(i).x), mm(o.CPoint(i).y)) for i in range(o.PointCount())]


VIA_GROW = 0.0    # extra pair-to-via clearance (tracks only; via rows use the plain clearance). Kept at 0: the pairs
                  # keep the board's 0.12 mm. Under U1 the D0 In3 lane is 0.02-0.04 mm too narrow for 0.15 mm (the
                  # 0.15 mm antipad edge), so a pair edge can overlap a via antipad in its plane by up to 0.03 mm;
                  # CHECKS/dsi_pair_check.py lists each place. Ground vias have no antipad.


def base_fields(b, skip, via_grow=0.0):
    layers = ('F.Cu', 'B.Cu', 'In3.Cu')
    F = {l: Field() for l in layers}; lid = {l: b.GetLayerID(l) for l in layers}
    for t in b.GetTracks():
        if t.GetNetname() in skip: continue
        if t.Type() == pcbnew.PCB_VIA_T:
            g = 0.0 if t.GetNetname() == 'GND' else via_grow
            for l in layers: F[l].circle(mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetWidth()) / 2 + g)
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
                if p.GetDrillSizeX() > 0: F[l].circle(mm(p.GetPosition().x), mm(p.GetPosition().y),
                                                      max(mm(p.GetDrillSizeX()) / 2 + 0.15, mm(max(p.GetSize().x, p.GetSize().y)) / 2
                                                          + (0.0 if p.GetNetname() == 'GND' else via_grow)))
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


def add_pair_obstacles(F, geo, grow=CLR_DSI - CLR, via_grow=None):
    """Copper of another pair (tracks per layer, vias), grown so the board clearance check becomes the pair-to-pair one
    (breakouts: grow 0, the plain board clearance; their vias still get VIA_GROW for the antipads)."""
    for lay, a, c, w in geo['tracks']:
        F[lay].capsule(a, c, w / 2 + grow)
    for v in geo['vias']:
        for l in F: F[l].circle(v[0], v[1], VIA_D / 2 + max(grow, VIA_GROW if via_grow is None else via_grow))


class Search:
    def __init__(self, F, E, Fv=None):
        # F: clearance fields for the pair's tracks; Fv: the same without VIA_GROW, for placing its via rows (via to via
        # needs only the copper clearance); own: copper points of this pair no via row may near
        self.F, self.E, self.Fv, self.own = F, E, Fv if Fv is not None else F, []

    def ok(self, layer, x, y):
        return self.F[layer].d(x, y) >= HALF[layer] + CLR and self.E.d(x, y) >= HALF[layer] + EDGE

    def via_row(self, x, y, d, flanks):
        n = N_(unit(d)); ks = (-1.5, -0.5, 0.5, 1.5) if flanks else (-0.5, 0.5)
        for k in ks:
            vx, vy = x + n[0] * k * VIA_P, y + n[1] * k * VIA_P
            if self.E.d(vx, vy) < VIA_D / 2 + EDGE: return False
            for lay, (ox, oy) in self.own:
                if math.hypot(vx - ox, vy - oy) < VIA_D / 2 + HALF[lay] + CLR: return False
            for l in self.F:
                if self.Fv[l].d(vx, vy) < VIA_D / 2 + CLR: return False
        return True

    def route(self, starts, goal, gdir, soft=None, hist=None, pres=0.0):
        """starts: list of (x, y, direction, layer index, flip) - flip 1 when P sits on the other side of the direction
        of travel than at J1, so the path must take a hairpin via row. soft[li], hist[li]: coarse (STEP) arrays for In3
        (0) and F.Cu (1); a step into a cell costs its length times (1 + hist) plus pres where another pair's copper
        would come too close (negotiated congestion). State: (i, j, direction, layer, flip)."""
        layers = ('In3.Cu', 'F.Cu')
        P = lambda i, j: (X0 + j * STEP, Y0 + i * STEP)
        gi, gj = int(round((goal[1] - Y0) / STEP)), int(round((goal[0] - X0) / STEP))
        okc = {}
        via_soft = None if soft is None else np.maximum(soft[0], soft[1])

        def ok(i, j, li):
            k = (i, j, li)
            if k not in okc: okc[k] = self.ok(layers[li], *P(i, j))
            return okc[k]
        h = lambda i, j: math.hypot(i - gi, j - gj) * STEP
        openq = []; came = {}; g = {}; via = {}
        for sx, sy, sd, sl, sf in starts:
            s0 = (int(round((sy - Y0) / STEP)), int(round((sx - X0) / STEP)), DIRS.index(sd), sl, sf)
            g[s0] = 0.0; came[s0] = None; heapq.heappush(openq, (h(s0[0], s0[1]), 0.0, s0))
        n = 0
        while openq:
            f, gc, s = heapq.heappop(openq)
            if gc > g.get(s, 1e9) + 1e-9: continue
            n += 1
            if n > 4_000_000: break
            i, j, di, li, fl = s
            if (i, j) == (gi, gj) and DIRS[di] == gdir and li == 1 and fl == 0:
                path = []; cur = s
                while cur: path.append(cur); cur = came[cur]
                return path[::-1], via, n
            dx, dy = DIRS[di]; sl = math.hypot(dx, dy) * STEP
            cand = []
            if ok(i + dy, j + dx, li): cand.append(((i + dy, j + dx, di, li, fl), sl, None))
            for t in (-1, 1):
                nd = (di + t) % 8; ex, ey = DIRS[nd]; ci, cj, good = i, j, True
                for _ in range(3):
                    ci, cj = ci + ey, cj + ex
                    if not ok(ci, cj, li): good = False; break
                if good: cand.append(((ci, cj, nd, li, fl), 3 * math.hypot(ex, ey) * STEP + 0.6, None))
            if li == 0:
                # straight via row: 1.2 mm on, the row in the middle
                ns = int(round(1.2 / sl)); half = ns // 2; ci, cj, good = i, j, True
                for k in range(1, ns + 1):
                    ci, cj = ci + dy, cj + dx
                    if not ok(ci, cj, 0 if k < half else 1): good = False; break
                mx, my = P(i + dy * half, j + dx * half)
                if good:
                    for flanks, cost in ((True, 2.0), (False, 6.0)):
                        if self.via_row(mx, my, (dx, dy), flanks):
                            cand.append(((ci, cj, di, 1, fl), ns * sl + cost, (round(mx, 3), round(my, 3), flanks, 0))); break
                # hairpin via row: the row 0.6 mm on, F.Cu comes back over the In3 run (P and N swap sides)
                hs = int(round(0.6 / sl)); ci, cj, good = i, j, True
                for k in range(1, hs + 1):
                    ci, cj = ci + dy, cj + dx
                    if not (ok(ci, cj, 0) and ok(ci, cj, 1)): good = False; break
                if good and ok(i, j, 1):
                    mx, my = P(ci, cj)
                    for flanks, cost in ((True, 4.0), (False, 8.0)):
                        if self.via_row(mx, my, (dx, dy), flanks):
                            cand.append(((i, j, (di + 4) % 8, 1, 1 - fl), 2 * hs * sl + cost, (round(mx, 3), round(my, 3), flanks, 1))); break
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
    """Grid states -> corner points (x, y); a turn macro keeps its new direction from the corner on."""
    X = lambda st: (round(X0 + st[1] * STEP, 3), round(Y0 + st[0] * STEP, 3))
    out = [X(path[0])]
    for a, c in zip(path, path[1:]):
        if c[2] != a[2]: out.append(X(a))
    out.append(X(path[-1]))
    clean = [out[0]]
    for p in out[1:]:
        if p != clean[-1]: clean.append(p)
    return clean


def start_options(name, F):
    """The four ways out of a breakout via pair: In3 or F.Cu, along either normal of the via axis, 0.55 mm from the
    vias' mid point; flip 1 where P would sit on the other side of the direction of travel than at J1 (only In3 starts
    can mend that, through a hairpin via row)."""
    bo, go = BREAKOUT[name], GOAL[name]
    P, Nv = bo['vias']['P'], bo['vias']['N']
    m = ((P[0] + Nv[0]) / 2, (P[1] + Nv[1]) / 2)
    u = unit((P[0] - Nv[0], P[1] - Nv[1]))
    cross = lambda a, b: a[0] * b[1] - a[1] * b[0]
    gside = cross(go['dir'], (go['pads']['P'][0] - go['at'][0], go['pads']['P'][1] - go['at'][1])) > 0
    opts = []
    for sd in ((-u[1], u[0]), (u[1], -u[0])):
        sd = (int(round(sd[0])), int(round(sd[1])))
        st = (round(round((m[0] + sd[0] * 0.55 - X0) / STEP) * STEP + X0, 3), round(round((m[1] + sd[1] * 0.55 - Y0) / STEP) * STEP + Y0, 3))
        flip = int((cross(sd, (P[0] - m[0], P[1] - m[1])) > 0) != gside)
        for li, lay in enumerate(('In3.Cu', 'F.Cu')):
            if li == 1 and flip: continue
            if F[lay].d(*st) >= HALF[lay] + CLR: opts.append((st[0], st[1], sd, li, flip))
    return m, opts


def route_lines(path, vias, m):
    """A found path -> dict(start, in3 centreline, via row, F.Cu centreline). The In3 line ends at the via row and the
    F.Cu line starts there; a pair that leaves its breakout on F.Cu has no In3 line and no second via row."""
    st0 = path[0]
    start = dict(at=[round(X0 + st0[1] * STEP, 3), round(Y0 + st0[0] * STEP, 3)], dir=list(DIRS[st0[2]]),
                 layer=('In3.Cu', 'F.Cu')[st0[3]], mid=[round(m[0], 4), round(m[1], 4)])
    if st0[3] == 1:
        return dict(start=start, in3=[], via=None, fcu=corners(path))
    k = next(i for i in range(len(path) - 1) if path[i][3] == 0 and path[i + 1][3] == 1)
    v = vias[path[k + 1]]
    return dict(start=start, in3=corners(path[:k + 1]) + [v[:2]], via=list(v), fcu=[v[:2]] + corners(path[k + 1:]))


def via_row(r):
    """Positions of the second via row (P/N in the middle, ground vias outside) of a routed pair."""
    if not r['via']: return []
    vx, vy, fl, hp = r['via']
    a, c = r['in3'][-2], r['in3'][-1]
    n = N_(unit((c[0] - a[0], c[1] - a[1])))
    return [(vx + n[0] * k * VIA_P, vy + n[1] * k * VIA_P) for k in ((-1.5, -0.5, 0.5, 1.5) if fl else (-0.5, 0.5))]


def pair_copper(r):
    """Centreline segments per layer (breakout taper included) and second-row via positions of a routed pair."""
    s = r['start']
    tr = [(s['layer'], tuple(s['mid']), tuple(s['at']))]
    for lay, pts in (('In3.Cu', r['in3']), ('F.Cu', r['fcu'])):
        tr += [(lay, tuple(a), tuple(c)) for a, c in zip(pts, pts[1:])]
    return tr, via_row(r)


def seg_dist(a, b, c, d):
    """Distance between segments ab and cd."""
    def pt(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
        t = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)
    cr = lambda o, p, q: (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    if (cr(a, b, c) * cr(a, b, d) < 0) and (cr(c, d, a) * cr(c, d, b) < 0): return 0.0
    return min(pt(a, c, d), pt(b, c, d), pt(c, a, b), pt(d, a, b))


def self_conflicts(r):
    """Points on a pair's own centreline that come closer than the pair-to-pair clearance to an earlier, non-adjacent
    part of it on the same layer (returned as points on the later part), or to its own via rows (returned as the
    nearest points of that copper, which then keep via rows away). The router does not see its own path."""
    tr, row = pair_copper(r)
    acc = [0.0]
    for _, a, c in tr: acc.append(acc[-1] + math.dist(a, c))
    bad, vbad = [], []
    for j, (lj, cj, dj) in enumerate(tr):
        for i in range(j - 1):
            li, ci, di = tr[i]
            lim = 2 * HALF[lj] + CLR_DSI
            if li != lj or acc[j] - acc[i + 1] < lim: continue      # neighbours along the path (a corner) are fine
            if seg_dist(ci, di, cj, dj) < lim:
                L = math.dist(cj, dj); k = max(1, int(L / 0.05))
                for t in range(k + 1):
                    p = (cj[0] + (dj[0] - cj[0]) * t / k, cj[1] + (dj[1] - cj[1]) * t / k)
                    if seg_dist(ci, di, p, p) < lim: bad.append((lj, p))
    if row:
        vx, vy = r['via'][:2]
        for lj, cj, dj in tr:
            if math.dist(cj, (vx, vy)) < 1e-6 or math.dist(dj, (vx, vy)) < 1e-6: continue
            for v in row:
                if seg_dist(cj, dj, v, v) < VIA_D / 2 + HALF[lj] + CLR:
                    vbad.append((lj, min(((cj[0] + (dj[0] - cj[0]) * t / 20, cj[1] + (dj[1] - cj[1]) * t / 20) for t in range(21)),
                                        key=lambda p: math.dist(p, v))))
    return bad, vbad


def length(r):
    tr, _ = pair_copper(r)
    return sum(math.dist(a, c) for _, a, c in tr)


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
    topo = TOPOLOGY[sys.argv[5] if len(sys.argv) > 5 else 'none']
    b = pcbnew.LoadBoard(board)
    dsi = {p[k] for p in BREAKOUT.values() for k in ('P', 'N')}
    F0, E = base_fields(b, dsi, VIA_GROW)
    Fv0, _ = base_fields(b, dsi, 0.0)
    fixed = {}
    for name, bo in BREAKOUT.items():
        tr = [(lay, a, c, GEO[lay][0]) for side in ('P', 'N') for lay, pts in bo['stubs'][side] for a, c in zip(pts, pts[1:])]
        fixed[name] = dict(tracks=tr, vias=list(bo['vias'].values()))
    searches, starts = {}, {}
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
        for lay, kx0, ky0, kx1, ky1 in topo.get(name, []):
            F[lay].poly([(kx0, ky0), (kx1, ky0), (kx1, ky1), (kx0, ky1)])
        Fv = {l: Field() for l in Fv0}
        for l in Fv: Fv[l].mask = Fv0[l].mask.copy()
        for other, geo in fixed.items():
            if other != name: add_pair_obstacles(Fv, geo, 0.0, 0.0)
            else:
                for v in geo['vias']:
                    for l in Fv: Fv[l].circle(v[0], v[1], VIA_D / 2)
        for l in F: F[l].finish()
        for l in Fv: Fv[l].finish()
        searches[name] = Search(F, E, Fv)
        starts[name] = start_options(name, F)
        print(name, 'starts', [(o[0], o[1], o[2], ('In3', 'F')[o[3]], o[4]) for o in starts[name][1]], flush=True)
    ny, nx = int(round((Y1 - Y0) / STEP)) + 1, int(round((X1 - X0) / STEP)) + 1
    hist = {n: [np.zeros((ny, nx)), np.zeros((ny, nx))] for n in order}
    cur = {}; pres = 0.5
    for it in range(rounds):
        conflicts = 0
        for name in order:
            others = [pair_copper(cur[o]) for o in order if o != name and o in cur]
            soft = soft_mask(others)
            go = GOAL[name]; m, opts = starts[name]
            for attempt in range(8):
                path, vias, n = searches[name].route(opts, go['at'], go['dir'], soft, hist[name], pres)
                if not path:
                    print(f'round {it}: {name} NO ROUTE ({n} states)', flush=True); return
                r = route_lines(path, vias, m)
                bad, vbad = self_conflicts(r)
                if not bad and not vbad: break
                F = searches[name].F
                for lay, p in bad: F[lay].circle(p[0], p[1], 0.03)
                for lay in {l for l, _ in bad}: F[lay].finish()
                searches[name].own += vbad
            else:
                print(f'round {it}: {name} still crosses itself', flush=True); return
            cur[name] = r
            bad = 0          # cells of this path that conflict with the others
            for st in path:
                if soft[st[3]][st[0], st[1]] > 0:
                    bad += 1; hist[name][st[3]][st[0], st[1]] += 0.4
            conflicts += bad
        lens = {nm: round(length(cur[nm]), 2) for nm in order}
        print(f'round {it}: conflict cells {conflicts}, pres {pres:.2f}, lengths {lens}', flush=True)
        if conflicts == 0: break
        pres *= 1.5
    json.dump(dict(geo=GEO, breakout=BREAKOUT, goal=GOAL, order=order, converged=conflicts == 0,
                   pairs={nm: cur[nm] for nm in order}), open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
