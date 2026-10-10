#!/usr/bin/env python3
"""R28 radio router (offline tool; its result, r28_radio_routes.json, is what edit 46 applies).

    python radio_router.py <board after edit 45> <out.json>

Routes the eight radio signals from the U1 pads edit 45 gave them to the pads of U15 (the Wio-SX1262 module): one
0.10 mm track per net on F.Cu, In3.Cu or B.Cu, changing layer through the board's 0.45/0.2 mm vias.

Why a negotiated router: U1's free pads sit in a 0.35 mm pad row whose escape lane, between the pads and R27's
decoupling parts, holds only a few vias. Routing the nets one after another lets the first ones take the lane. Here
all eight are routed together with negotiated congestion (PathFinder, McMurchie and Ebeling 1995): every pass routes
each net by A* against the board's copper (hard) and the other radio nets (a cost that grows each pass, plus a
history cost where nets kept colliding), until no two radio nets conflict.

Rules (all hard, against R27 copper):
  - 0.12 mm from other copper; 0.10 mm (the board's design rule) inside U1's pad ring and 0.8 mm round it, where the
    pads are 0.35 mm apart;
  - 0.30 mm from the nets a fast edge must not couple into: the 40 MHz crystal (XTAL_*), the core regulator's
    feedback and enable (FB_DCDC, EN_DCDC), CHIP_PU, and the MIPI-DSI pairs (inside U1's pad ring the board rule);
  - vias 0.25 mm (copper to copper) from FB_DCDC and EN_DCDC tracks, so no via antipad (via + 0.15 mm) reaches the
    ground under them (r28_plane_check.py checks the result);
  - no via on a pad; nothing under the module body on any layer (Seeed's layout rule: only ground under it);
  - radio nets 0.12 mm apart (track to track, track to via, via to via).
Each route starts on the outer half of its pads (U1 pads 0.65 mm long, module pads 2.2 mm). Grid 0.05 mm, fields
0.025 mm; deterministic. Needs pcbnew (KiCad 7.0.x), numpy, scipy, matplotlib.
"""
import sys, os, json, math, heapq
sys.path.append('/usr/lib/python3/dist-packages')
import numpy as np
from scipy import ndimage
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'R26_FROM_R25'))
import dsi_pair_router as R

W = 0.10                     # track width
CLR, CLR_NECK, EDGE = 0.12, 0.10, 0.30
NECK = (-5.7, 78.3, 5.7, 89.7)
VIA_D = 0.45
QUIET, QUIET_CLR = ('XTAL_N_SOC', 'XTAL_P_SOC', 'XTAL_N', 'XTAL_P', 'FB_DCDC', 'EN_DCDC', 'CHIP_PU'), 0.30
CLR_DSI = 0.30
PLANE_NETS, PLANE_VIA = ('FB_DCDC', 'EN_DCDC'), 0.25
LAYERS = ('F.Cu', 'In3.Cu', 'B.Cu')
STEP = 0.05
BOX = (-33.0, 70.0, 6.0, 98.0)        # the routing region: U1's north side, the module and the land round it
if os.environ.get('RR_BOX'): BOX = tuple(float(v) for v in os.environ['RR_BOX'].split(','))
# net: (U1 pad, U15 pad); pin assignment in r28_radio_parts.py
NETS = {'RADIO_UART_TX': ('80', '30'), 'RADIO_UART_RX': ('81', '29'), 'RADIO_NRST': ('82', '44'), 'RADIO_BOOT0': ('93', '43')}
if os.environ.get('RR_NETS'):                              # experiments: another assignment, "NET:u1pad:u15pad,..."
    NETS = {a: (b_, c_) for a, b_, c_ in (x.split(':') for x in os.environ['RR_NETS'].split(','))}
for _n in os.environ.get('RR_DROP', '').split(','):       # experiments: leave nets out
    NETS.pop(_n, None)
# R27 nets whose stretch next to U1 is routed again together with the radio (function unchanged: same pad, same far
# end; all three are slow status/control lines whose pull resistors the self-test checks). net: (U1 pad, the point
# where the kept copper continues, its layer (None: a via, any layer), box: every item of the net touching it is
# replaced)
REROUTE = {}                          # R28 moves no R27 copper (the RAK3172 needs only four lines)
REROUTE_STUDY = {'USB_CURR_OUT1': ('84', (-16.65, 74.0), None, (-16.6, 74.1, -2.0, 79.2)),
                 'PGOOD_STATUS': ('86', (4.5, 75.79), None, (-2.5, 75.5, 4.4, 79.2)),
                 'BQ_EN2': ('88', (5.0, 74.7), 'B.Cu', (-1.5, 74.6, 4.95, 79.2))}
if os.environ.get('RR_REROUTE') is not None:
    REROUTE = {k: v for k, v in REROUTE_STUDY.items() if k in os.environ['RR_REROUTE'].split(',')}
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
SEP = W + CLR + 0.02                  # radio track centre to radio track centre (grid margin 0.02)
SEP_TV = VIA_D / 2 + W / 2 + CLR + 0.02
SEP_VV = VIA_D + CLR + 0.02
mm = R.mm


def in_neck(x, y): return NECK[0] <= x <= NECK[2] and NECK[1] <= y <= NECK[3]


def outer(p, centre, frac):
    """A point on pad p, `frac` of its half-length from its centre towards the side away from `centre`."""
    x, y = mm(p.GetPosition().x), mm(p.GetPosition().y)
    sx, sy = mm(p.GetBoundingBox().GetWidth()), mm(p.GetBoundingBox().GetHeight())
    if sx > sy: x += math.copysign(frac * sx / 2, x - centre[0])
    else: y += math.copysign(frac * sy / 2, y - centre[1])
    return (round(x / STEP) * STEP, round(y / STEP) * STEP)


def poly_cells(mask, pts, value):
    """Set the field cells inside polygon pts (fields at R.RES) to value."""
    from matplotlib.path import Path as MPath
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    i0, j0 = R.fidx(min(xs), min(ys)); i1, j1 = R.fidx(max(xs), max(ys))
    i0, j0, i1, j1 = max(i0, 0), max(j0, 0), min(i1 + 1, R.NY), min(j1 + 1, R.NX)
    if i0 >= i1 or j0 >= j1: return
    yy, xx = np.mgrid[i0:i1, j0:j1]
    ins = MPath(pts).contains_points(np.c_[(R.X0 + xx * R.RES).ravel(), (R.Y0 + yy * R.RES).ravel()]).reshape(i1 - i0, j1 - j0)
    if value: mask[i0:i1, j0:j1] |= ins
    else: mask[i0:i1, j0:j1] &= ~ins


class Board:
    """Hard obstacles on the routing grid: for each net, ok[l] (track centre allowed) and vok (via allowed)."""

    def __init__(self, b):
        self.b = b
        x0, y0, x1, y1 = BOX
        R.X0, R.Y0, R.X1, R.Y1, R.RES = x0 - 1, y0 - 1, x1 + 1, y1 + 1, 0.025
        R.NX, R.NY = int(round((R.X1 - R.X0) / R.RES)) + 1, int(round((R.Y1 - R.Y0) / R.RES)) + 1
        self.ni, self.nj = int(round((y1 - y0) / STEP)) + 1, int(round((x1 - x0) / STEP)) + 1
        yy, xx = np.mgrid[0:self.ni, 0:self.nj]
        self.gx, self.gy = x0 + xx * STEP, y0 + yy * STEP
        self.fi = np.clip(np.round((self.gy - R.Y0) / R.RES).astype(int), 0, R.NY - 1)
        self.fj = np.clip(np.round((self.gx - R.X0) / R.RES).astype(int), 0, R.NX - 1)
        self.neck = (self.gx >= NECK[0]) & (self.gx <= NECK[2]) & (self.gy >= NECK[1]) & (self.gy <= NECK[3])
        radio = set(NETS) | set(REROUTE)
        soft = {n for n in os.environ.get('RR_SOFT', '').split(',') if n}   # experiments: nets treated as absent
        F, E = R.base_fields(b, radio | soft)
        # the kept copper of the re-routed nets: an obstacle for every other net
        self.kept, self.removed = {}, {}
        for nn, (_, cut, _cl, rb) in REROUTE.items():
            km = {l: np.zeros((R.NY, R.NX), bool) for l in LAYERS}
            rem = []
            for t in b.GetTracks():
                if t.GetNetname() != nn: continue
                pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
                inside = any(rb[0] <= mm(p.x) <= rb[2] and rb[1] <= mm(p.y) <= rb[3] for p in pts)
                if inside:
                    rem.append(('via', round(mm(t.GetPosition().x), 4), round(mm(t.GetPosition().y), 4)) if t.Type() == pcbnew.PCB_VIA_T
                               else (t.GetLayerName(), round(mm(t.GetStart().x), 4), round(mm(t.GetStart().y), 4),
                                     round(mm(t.GetEnd().x), 4), round(mm(t.GetEnd().y), 4)))
                    continue
                fl = R.Field()
                if t.Type() == pcbnew.PCB_VIA_T:
                    fl.circle(mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetWidth()) / 2)
                    for l in LAYERS: km[l] |= fl.mask
                elif t.GetLayerName() in km:
                    fl.capsule((mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y)), mm(t.GetWidth()) / 2)
                    km[t.GetLayerName()] |= fl.mask
            self.kept[nn], self.removed[nn] = km, rem            # every radio pad is an obstacle here; a net's own are reopened below
        for nn in NETS:                           # the radio nets' copper edit 45 already drew (stubs, pull-up / pull-down
            km = {l: np.zeros((R.NY, R.NX), bool) for l in LAYERS}       # joins): kept, an obstacle for the other nets
            for t in b.GetTracks():
                if t.GetNetname() != nn: continue
                fl = R.Field()
                if t.Type() == pcbnew.PCB_VIA_T:
                    fl.circle(mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetWidth()) / 2)
                    for l in LAYERS: km[l] |= fl.mask
                elif t.GetLayerName() in km:
                    fl.capsule((mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y)), mm(t.GetWidth()) / 2)
                    km[t.GetLayerName()] |= fl.mask
            self.kept[nn] = km
        lid = {l: b.GetLayerID(l) for l in LAYERS}
        dsi = {p[k] for p in R.BREAKOUT.values() for k in ('P', 'N')}
        for t in b.GetTracks():                   # grown keep-outs: DSI pairs and the quiet nets (outside the neck)
            nn = t.GetNetname()
            if nn not in dsi and nn not in QUIET: continue
            grow = (CLR_DSI if nn in dsi else QUIET_CLR) - CLR
            if t.Type() == pcbnew.PCB_VIA_T:
                if nn in dsi:
                    for l in F: F[l].circle(mm(t.GetPosition().x), mm(t.GetPosition().y), VIA_D / 2 + grow)
                continue
            a, c = (mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y))
            if in_neck(*a) and in_neck(*c): continue
            l = t.GetLayerName()
            if l in F: F[l].capsule(a, c, mm(t.GetWidth()) / 2 + grow)
        for f in b.GetFootprints():
            if f.GetReference() == 'U1': continue
            for q in f.Pads():
                if q.GetNetname() not in QUIET: continue
                for l in LAYERS:
                    if not q.IsOnLayer(lid[l]): continue
                    sp = q.GetEffectivePolygon()
                    for k in range(sp.OutlineCount()):
                        pts = R.pts_of(sp, k)
                        for p_, q_ in zip(pts, pts[1:] + pts[:1]): F[l].capsule(p_, q_, QUIET_CLR - CLR)
        u15 = b.FindFootprintByReference('U15')
        for s in u15.GraphicalItems():
            if s.GetLayerName() == 'B.Fab' and s.GetShape() == pcbnew.SHAPE_T_RECT:
                bb = s.GetBoundingBox()
                self.body = (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))
        for l in ('B.Cu',):                       # the module body: no B.Cu copper but its ground (In4 shields the rest)
            poly_cells(F[l].mask, [(self.body[0], self.body[1]), (self.body[2], self.body[1]), (self.body[2], self.body[3]),
                                   (self.body[0], self.body[3])], True)
        self.F, self.E = F, E
        V = R.Field()
        for t in b.GetTracks():
            if t.GetNetname() in PLANE_NETS and t.Type() != pcbnew.PCB_VIA_T:
                V.capsule((mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y)), mm(t.GetWidth()) / 2)
        V.finish(); E.finish() if not hasattr(E, 'dist') else None
        E_ = E.dist[self.fi, self.fj]
        self.vplane = V.dist[self.fi, self.fj] >= VIA_D / 2 + PLANE_VIA
        self.edge_t, self.edge_v = E_ >= W / 2 + EDGE, E_ >= VIA_D / 2 + EDGE
        self.pads = {}
        for f in b.GetFootprints():
            for q in f.Pads():
                if q.GetNetname() in radio: self.pads.setdefault(q.GetNetname(), []).append(q)
        pm = np.zeros((R.NY, R.NX), bool)       # every radio pad (no via on a pad)
        for qs in self.pads.values():
            for q in qs:
                sp = q.GetEffectivePolygon()
                for k in range(sp.OutlineCount()): poly_cells(pm, R.pts_of(sp, k), True)
        self.on_pad = ndimage.binary_dilation(pm, iterations=int(VIA_D / 2 / R.RES) + 1)[self.fi, self.fj]

    def net_masks(self, net):
        """ok[l] and vok for one net: the board's copper with this net's own pads open."""
        ok, dist = [], {}
        for l in LAYERS:
            m = self.F[l].mask.copy()
            for o, km in self.kept.items():
                if o != net: m |= km[l]
            for q in self.pads[net]:
                if q.IsOnLayer(self.b.GetLayerID(l)):
                    sp = q.GetEffectivePolygon()
                    for k in range(sp.OutlineCount()): poly_cells(m, R.pts_of(sp, k), False)
            d = (ndimage.distance_transform_edt(~m) * R.RES - R.RES / 2)[self.fi, self.fj]
            dist[l] = d
            need = np.where(self.neck, W / 2 + CLR_NECK, W / 2 + CLR)
            ok.append((d >= need) & self.edge_t)
        vok = self.edge_v & self.vplane & ~self.on_pad
        for l in LAYERS: vok &= dist[l] >= VIA_D / 2 + CLR
        return ok, vok

    def cell(self, p): return (int(round((p[1] - BOX[1]) / STEP)), int(round((p[0] - BOX[0]) / STEP)))

    def xy(self, i, j): return (round(BOX[0] + j * STEP, 3), round(BOX[1] + i * STEP, 3))


def astar(G, ok, vok, a, c, cost_t, cost_v, goal_layers=(2,)):
    """A* over (i, j, layer, heading); start and goal on B.Cu (both pads are back-side pads). cost_t[l] and cost_v
    are the congestion costs of a track cell / via cell (0 where free). Bends cost 0.3 mm, vias 1.5 mm."""
    si, sj = G.cell(a); gi, gj = G.cell(c)
    LB = 2
    start = (si, sj, LB, -1)
    g = {start: 0.0}; came = {start: None}
    openq = [(0.0, 0.0, start)]
    h = lambda i, j: math.hypot(i - gi, j - gj) * STEP
    ni, nj = G.ni, G.nj
    n = 0
    while openq:
        f, gc, s = heapq.heappop(openq)
        if gc > g.get(s, 1e18) + 1e-9: continue
        i, j, l, d = s; n += 1
        if (i, j) == (gi, gj) and l in goal_layers:
            path = []; cur = s
            while cur: path.append(cur); cur = came[cur]
            return path[::-1], n
        if n > 4_000_000: break
        okl, ct = ok[l], cost_t[l]
        for k, (dx, dy) in enumerate(DIRS):
            if d >= 0 and min((k - d) % 8, (d - k) % 8) > 2: continue          # no turn sharper than 90 degrees
            i2, j2 = i + dy, j + dx
            if not (0 <= i2 < ni and 0 <= j2 < nj): continue
            if not okl[i2, j2] and (i2, j2) != (gi, gj): continue
            c_ = math.hypot(dx, dy) * STEP * (1 + ct[i2, j2]) + (0.3 if d >= 0 and k != d else 0)
            ns = (i2, j2, l, k); ng = gc + c_
            if ng < g.get(ns, 1e18) - 1e-9:
                g[ns] = ng; came[ns] = s; heapq.heappush(openq, (ng + h(i2, j2), ng, ns))
        if vok[i, j]:
            for l2 in range(3):
                if l2 != l and ok[l2][i, j]:
                    ns = (i, j, l2, d); ng = gc + 1.5 + cost_v[i, j]
                    if ng < g.get(ns, 1e18) - 1e-9:
                        g[ns] = ng; came[ns] = s; heapq.heappush(openq, (ng + h(i, j), ng, ns))
    return None, n


def footprint(G, path):
    """Grid cells of a path: track centre cells per layer (the straight runs between grid steps), via cells."""
    T = [np.zeros((G.ni, G.nj), bool) for _ in LAYERS]; V = np.zeros((G.ni, G.nj), bool)
    prev = None
    for (i, j, l, d) in path:
        T[l][i, j] = True
        if prev and prev[2] != l: V[i, j] = True
        prev = (i, j, l)
    return T, V


def conflict_fields(G, fps):
    """Distance (mm) from each cell to the nearest track centre (per layer) and via of the footprints fps."""
    T = [np.zeros((G.ni, G.nj), bool) for _ in LAYERS]; V = np.zeros((G.ni, G.nj), bool)
    for t, v in fps:
        for l in range(3): T[l] |= t[l]
        V |= v
    dT = [ndimage.distance_transform_edt(~t) * STEP if t.any() else np.full((G.ni, G.nj), 1e9) for t in T]
    dV = ndimage.distance_transform_edt(~V) * STEP if V.any() else np.full((G.ni, G.nj), 1e9)
    return dT, dV


def conflicts(fp, dT, dV):
    """Cells of footprint fp that break the radio-to-radio spacing against fields dT, dV."""
    t, v = fp
    bad = [t[l] & ((dT[l] < SEP) | (dV < SEP_TV)) for l in range(3)]
    badv = v & ((dV < SEP_VV) | np.logical_or.reduce([dT[l] < SEP_TV for l in range(3)]))
    return bad, badv


def to_geometry(G, path):
    segs, vias = [], []
    run = [path[0]]
    for a, c in zip(path, path[1:]):
        if c[2] != a[2]:
            vias.append(G.xy(a[0], a[1])); segs.append((LAYERS[a[2]], [G.xy(s[0], s[1]) for s in run])); run = [c]
        else:
            run.append(c)
    segs.append((LAYERS[run[0][2]], [G.xy(s[0], s[1]) for s in run]))
    out = []
    sd = lambda p, q: (round((q[0] - p[0]) / max(abs(q[0] - p[0]), abs(q[1] - p[1]))),
                       round((q[1] - p[1]) / max(abs(q[0] - p[0]), abs(q[1] - p[1]))))
    for lay, pts in segs:
        if len(pts) < 2: continue
        k = [pts[0]]
        for p, q, r in zip(pts, pts[1:], pts[2:]):
            if sd(p, q) != sd(q, r): k.append(q)
        k.append(pts[-1]); out.append((lay, k))
    return out, vias


def main():
    board, out = sys.argv[1], sys.argv[2]
    b = pcbnew.LoadBoard(board)
    G = Board(b)
    u1, u15 = b.FindFootprintByReference('U1'), b.FindFootprintByReference('U15')
    c1 = (mm(u1.GetPosition().x), mm(u1.GetPosition().y)); c15 = (mm(u15.GetPosition().x), mm(u15.GetPosition().y))
    P1 = {p.GetNumber(): p for p in u1.Pads()}; P15 = {p.GetNumber(): p for p in u15.Pads()}
    ends, masks, goal_l = {}, {}, {}
    for net, (a1, a15) in NETS.items():
        assert P1[a1].GetNetname() == net and P15[a15].GetNetname() == net, net
        ends[net] = (outer(P1[a1], c1, 0.4), outer(P15[a15], c15, 0.6)); goal_l[net] = (2,)
        masks[net] = G.net_masks(net)
    for net, (a1, cut, cl, _) in REROUTE.items():
        assert P1[a1].GetNetname() == net, net
        ends[net] = (outer(P1[a1], c1, 0.4), (round(cut[0] / STEP) * STEP, round(cut[1] / STEP) * STEP))
        goal_l[net] = (0, 1, 2) if cl is None else (LAYERS.index(cl),)
        masks[net] = G.net_masks(net)
    ALL = list(NETS) + list(REROUTE)
    hist_t = [np.zeros((G.ni, G.nj)) for _ in LAYERS]; hist_v = np.zeros((G.ni, G.nj))
    paths, fps = {}, {}
    pres, total = 0.5, None
    for it in range(1, int(os.environ.get('RR_PASSES', 40)) + 1):
        for net in ALL:
            dT, dV = conflict_fields(G, [fps[o] for o in ALL if o != net and o in fps])
            near_v = np.logical_or.reduce([dT[l] < SEP_TV for l in range(3)])
            cost_t = [hist_t[l] + pres * 20 * ((dT[l] < SEP) | (dV < SEP_TV)) for l in range(3)]
            cost_v = 10 * hist_v + pres * 20 * ((dV < SEP_VV) | near_v)
            ok, vok = masks[net]
            path, n = astar(G, ok, vok, *ends[net], cost_t, cost_v, goal_l[net])
            if path is None:
                print(f'{net}: NO ROUTE even alone against the board ({n} states)'); sys.exit(2)
            paths[net] = path; fps[net] = footprint(G, path)
        total = 0; where = []
        for net in ALL:
            dT, dV = conflict_fields(G, [fps[o] for o in ALL if o != net])
            bad, badv = conflicts(fps[net], dT, dV)
            nb = sum(int(x.sum()) for x in bad) + int(badv.sum())
            total += nb
            for l in range(3):
                for i, j in zip(*np.nonzero(bad[l])): where.append((net, LAYERS[l], *G.xy(i, j)))
            for i, j in zip(*np.nonzero(badv)): where.append((net, 'via', *G.xy(i, j)))
            for l in range(3): hist_t[l][ndimage.binary_dilation(bad[l], iterations=3)] += 0.3
            hist_v[ndimage.binary_dilation(badv, iterations=6)] += 0.3
        print(f'pass {it}: {total} conflicting cells (present factor {pres:.2f})', flush=True)
        if total == 0: break
        pres *= 1.5
    res = {}
    for net in ALL:
        segs, vias = to_geometry(G, paths[net])
        L = sum(math.dist(p, q) for _, pts in segs for p, q in zip(pts, pts[1:]))
        if net in NETS:
            print(f'{net}: U1.{NETS[net][0]} -> U15.{NETS[net][1]}: {L:.1f} mm, {len(vias)} vias')
            res[net] = dict(width=W, segments=segs, vias=vias)
        else:
            print(f'{net} (re-routed): U1.{REROUTE[net][0]} -> via {REROUTE[net][1]}: {L:.1f} mm, {len(vias)} vias, '
                  f'replaces {len(G.removed[net])} items')
            res[net] = dict(width=W, segments=segs, vias=vias, remove=G.removed[net])
    if total: res['_conflicts'] = where
    json.dump(res, open(out, 'w'), indent=1)
    if total: print(f'UNRESOLVED: {total} conflicting cells'); sys.exit(1)


if __name__ == '__main__':
    main()
