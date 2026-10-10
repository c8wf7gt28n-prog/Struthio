#!/usr/bin/env python3
"""R28 radio router (offline tool; its result, r28_radio_routes.json, is what edit 46 applies).

    python radio_router.py <board after edit 45> <out.json>

Routes the eight radio signals from the U1 pads edit 45 gave them to the pads of U15 (the Wio-SX1262 module): one
0.152 mm track per net on F.Cu, In3.Cu or B.Cu, changing layer through 0.45/0.2 mm vias. The search is net_router.py's
(R26): A* over clearance fields built from all other copper, 0.12 mm from other nets. In addition it keeps
  - 0.30 mm from the nets a fast edge must not couple into: the 40 MHz crystal (XTAL_*), the core regulator's feedback
    and enable (FB_DCDC, EN_DCDC), CHIP_PU and the MIPI-DSI pairs (tracks and pads; at U1's own pads, which sit
    0.35 mm apart, the board's 0.12 mm);
  - vias 0.60 mm from FB_DCDC and EN_DCDC copper on every layer, so no via antipad opens the ground under them
    (r27_plane_check.py);
  - out from under the module body on every layer (Seeed's layout rule: only ground under the module).
Each route starts on the outer half of its pads (U1 pads 0.65 mm long, module pads 2.2 mm), so a track never runs
inside U1's pad ring or under the module. Deterministic. Needs pcbnew (KiCad 7.0.x), numpy, scipy, matplotlib.
"""
import sys, os, json, math
sys.path.append('/usr/lib/python3/dist-packages')
import numpy as np
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'R26_FROM_R25'))
import dsi_pair_router as R
import net_router as N

import os as _os
W = float(_os.environ.get('RR_W', 0.152))
CLR_NECK = float(_os.environ.get('RR_NECK', 0.12))   # clearance within NECK (U1's pad ring and 0.8 mm round it)
NECK = (-5.7, 78.3, 5.7, 89.7)
QUIET, QUIET_CLR = ('XTAL_N_SOC', 'XTAL_P_SOC', 'XTAL_N', 'XTAL_P', 'FB_DCDC', 'EN_DCDC', 'CHIP_PU'), 0.30
PLANE_NETS, PLANE_VIA = ('FB_DCDC', 'EN_DCDC'), float(_os.environ.get('RR_PV', 0.25))
# net: (U1 pad, U15 pad), in routing order: the six on U1's west side, then the two that go round the module's north
NETS = {'RADIO_RF_SW': ('64', '1'), 'RADIO_MISO': ('63', '2'), 'RADIO_MOSI': ('61', '3'), 'RADIO_SCK': ('60', '4'),
        'RADIO_NRST': ('58', '5'), 'RADIO_NSS': ('57', '6'), 'RADIO_DIO1': ('80', '12'), 'RADIO_BUSY': ('81', '11')}


def outer(p, centre, frac):
    """A point on pad p, `frac` of its half-length from its centre towards the side away from `centre`."""
    x, y = R.mm(p.GetPosition().x), R.mm(p.GetPosition().y)
    sx, sy = R.mm(p.GetBoundingBox().GetWidth()), R.mm(p.GetBoundingBox().GetHeight())
    if sx > sy: x += math.copysign(frac * sx / 2, x - centre[0])
    else: y += math.copysign(frac * sy / 2, y - centre[1])
    return (round(x / 0.025) * 0.025, round(y / 0.025) * 0.025, 'B.Cu')


def main():
    board, out = sys.argv[1], sys.argv[2]
    b = pcbnew.LoadBoard(board)
    u1, u15 = b.FindFootprintByReference('U1'), b.FindFootprintByReference('U15')
    c1 = (R.mm(u1.GetPosition().x), R.mm(u1.GetPosition().y)); c15 = (R.mm(u15.GetPosition().x), R.mm(u15.GetPosition().y))
    pads = lambda f: {p.GetNumber(): p for p in f.Pads()}
    P1, P15 = pads(u1), pads(u15)
    body = u15.GetBoundingBox(False, False)        # body: the fab rectangle (pads stick out on two sides)
    for s in u15.GraphicalItems():
        if s.GetLayerName() in ('B.Fab', 'F.Fab') and s.GetShape() == pcbnew.SHAPE_T_RECT: body = s.GetBoundingBox()
    BODY = (R.mm(body.GetLeft()), R.mm(body.GetTop()), R.mm(body.GetRight()), R.mm(body.GetBottom()))
    dsi = {p[k] for p in R.BREAKOUT.values() for k in ('P', 'N')}
    res = {}; done = []
    for net, (a1, a15) in NETS.items():
        p1, p15 = P1[a1], P15[a15]
        assert p1.GetNetname() == net and p15.GetNetname() == net, (net, p1.GetNetname(), p15.GetNetname())
        a, c = outer(p1, c1, 0.4), outer(p15, c15, 0.6)
        box = (max(min(a[0], c[0]) - 6, -51), max(min(a[1], c[1]) - 6, 1), min(max(a[0], c[0]) + 6, 51), min(max(a[1], c[1]) + 6, 130))
        N.use_region(box, 0.025)
        F, E = N.fields(b, net, dsi, done)
        for l in F:                                   # re-open the fields to add this router's own keep-outs
            m = F[l].mask
            for t in b.GetTracks():
                nn = t.GetNetname()
                if (nn in QUIET and t.Type() != pcbnew.PCB_VIA_T and t.GetLayerName() == l
                        and not all(in_neck(R.mm(p_.x), R.mm(p_.y)) for p_ in (t.GetStart(), t.GetEnd()))):
                    F[l].capsule((R.mm(t.GetStart().x), R.mm(t.GetStart().y)), (R.mm(t.GetEnd().x), R.mm(t.GetEnd().y)),
                                 R.mm(t.GetWidth()) / 2 + QUIET_CLR - N.CLR)
            for f in b.GetFootprints():
                for q in f.Pads():
                    if q.GetNetname() in QUIET and q.IsOnLayer(b.GetLayerID(l)) and f.GetReference() != 'U1':
                        sp = q.GetEffectivePolygon()
                        for k in range(sp.OutlineCount()):
                            pts = R.pts_of(sp, k)
                            for p_, q_ in zip(pts, pts[1:] + pts[:1]): F[l].capsule(p_, q_, QUIET_CLR - N.CLR)
            for q in (p1, p15):                       # dsi_pair_router.base_fields blocks the routed net's own pads (it
                if not q.IsOnLayer(b.GetLayerID(l)): continue   # was written for the DSI pairs): open them again
                sp = q.GetEffectivePolygon()
                for k in range(sp.OutlineCount()): unpaint(m, R.pts_of(sp, k))
            i0, j0 = R.fidx(BODY[0], BODY[1]); i1, j1 = R.fidx(BODY[2], BODY[3])
            m[max(i0, 0):max(i1 + 1, 0), max(j0, 0):max(j1 + 1, 0)] = True
            F[l].finish()
        # vias away from the regulator's feedback and enable copper (all layers)
        V = R.Field()
        for t in b.GetTracks():
            if t.GetNetname() in PLANE_NETS and t.Type() != pcbnew.PCB_VIA_T:
                V.capsule((R.mm(t.GetStart().x), R.mm(t.GetStart().y)), (R.mm(t.GetEnd().x), R.mm(t.GetEnd().y)), R.mm(t.GetWidth()) / 2)
            elif t.GetNetname() in PLANE_NETS:
                V.circle(R.mm(t.GetPosition().x), R.mm(t.GetPosition().y), R.mm(t.GetWidth()) / 2)
        V.finish()
        path, n = route(F, E, W, a, c, box, V)
        if not path:
            print(f'{net}: {a} -> {c}: NO ROUTE ({n} states)'); res[net] = None; continue
        segs, vias = N.to_geometry(path, box)
        Lm = sum(math.dist(p, q) for _, pts in segs for p, q in zip(pts, pts[1:]))
        print(f'{net}: U1.{a1} {a[:2]} -> U15.{a15} {c[:2]}: {Lm:.1f} mm, {len(vias)} vias, {n} states', flush=True)
        res[net] = dict(width=W, segments=segs, vias=vias); done.append((net, W, segs, vias))
    json.dump(res, open(out, 'w'), indent=1)


def in_neck(x, y): return NECK[0] <= x <= NECK[2] and NECK[1] <= y <= NECK[3]


def unpaint(mask, pts):
    """Clear the field cells inside polygon pts (a pad of the net being routed)."""
    from matplotlib.path import Path as MPath
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    i0, j0 = R.fidx(min(xs), min(ys)); i1, j1 = R.fidx(max(xs), max(ys))
    i0, j0, i1, j1 = max(i0, 0), max(j0, 0), min(i1 + 1, R.NY), min(j1 + 1, R.NX)
    if i0 >= i1 or j0 >= j1: return
    yy, xx = np.mgrid[i0:i1, j0:j1]
    ins = MPath(pts).contains_points(np.c_[(R.X0 + xx * R.RES).ravel(), (R.Y0 + yy * R.RES).ravel()]).reshape(i1 - i0, j1 - j0)
    mask[i0:i1, j0:j1] &= ~ins


def route(F, E, w, a, c, box, V):
    """net_router.route, with vias also 0.60 mm from FB_DCDC / EN_DCDC copper (V) and never on a pad."""
    import heapq
    step = N.STEP
    x0, y0, x1, y1 = box
    ni, nj = int((y1 - y0) / step) + 1, int((x1 - x0) / step) + 1
    P = lambda i, j: (x0 + j * step, y0 + i * step)
    need_n, need_o = w / 2 + CLR_NECK, w / 2 + N.CLR
    okc, vok = {}, {}
    LAY = N.LAYERS

    def ok(i, j, l):
        k = (i, j, l)
        if k not in okc:
            x, y = P(i, j)
            okc[k] = (0 <= i < ni and 0 <= j < nj and F[LAY[l]].d(x, y) >= (need_n if in_neck(x, y) else need_o)
                      and E.d(x, y) >= w / 2 + N.EDGE)
        return okc[k]

    def via_ok(i, j):
        if (i, j) not in vok:
            x, y = P(i, j)
            vok[(i, j)] = (E.d(x, y) >= N.VIA_D / 2 + N.EDGE and all(F[l].d(x, y) >= N.VIA_D / 2 + N.CLR for l in F)
                           and V.d(x, y) >= N.VIA_D / 2 + PLANE_VIA)
        return vok[(i, j)]

    cell = lambda p: (int(round((p[1] - y0) / step)), int(round((p[0] - x0) / step)))
    si, sj = cell(a); gi, gj = cell(c)
    starts = [LAY.index(a[2])] if a[2] else [0, 1, 2]
    goals = {LAY.index(c[2])} if c[2] else {0, 1, 2}
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
        if n > 6_000_000: break
        nxt = []
        for k, (dx, dy) in enumerate(N.DIRS):
            if d >= 0 and min((k - d) % 8, (d - k) % 8) > 2: continue   # no turns sharper than 90 degrees
            if ok(i + dy, j + dx, l) or (i + dy, j + dx) == (gi, gj):
                c_ = math.hypot(dx, dy) * step + (0.3 if d >= 0 and k != d else 0)
                nxt.append(((i + dy, j + dx, l, k), c_))
        if via_ok(i, j):
            for l2 in range(3):
                if l2 != l and ok(i, j, l2): nxt.append(((i, j, l2, d), 1.5))
        for ns, c_ in nxt:
            ng = gc + c_
            if ng < g.get(ns, 1e9) - 1e-9:
                g[ns] = ng; came[ns] = s; heapq.heappush(openq, (ng + h(ns[0], ns[1]), ng, ns))
    return None, n


if __name__ == '__main__':
    main()
