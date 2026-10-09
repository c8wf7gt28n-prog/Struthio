#!/usr/bin/env python3
"""R26 DSI pair geometry (offline tool; its result, r26_dsi_routes.json, is what edit 32 draws, so the board build
does not depend on this script).

    python dsi_geometry.py <board after edit 31> <routes from dsi_pair_router.py> <out r26_dsi_routes.json>

Turns the routed pair centrelines into the copper of each line and matches the pairs:
  - P and N are the centreline offset by half the pair pitch on each layer (mitred 45 degree corners), joined to the
    breakout vias, to the second via row and to the J1 pads by short tapers (via pitch 0.55 mm, pad pitch 0.5 mm);
  - every pair (its longer line) is brought to the length of the longest by coupled serpentines (both lines bend together, so the bend
    adds no skew): 45 degree chamfers of 0.3 mm, 0.6 mm tops and gaps, so facing parts of one pair stay 0.77 mm
    (about eight dielectric heights) apart. F.Cu runs first, then In3;
  - the shorter line of each pair then gets small 45 degree teeth away from its partner (0.25 mm high at most,
    0.4 mm apart) until P and N are within 0.05 mm, nearest the pair's start where they fit;
  - every centreline is checked against the board copper (0.12 mm), the other pairs (0.30 mm), its own other parts
    and the board edge.
Needs pcbnew (KiCad 7.0.x), numpy, scipy, matplotlib (through dsi_pair_router).
"""
import sys, json, math
sys.path.append('/usr/lib/python3/dist-packages')
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import dsi_pair_router as R

GEO = R.GEO
PITCH = {l: w + g for l, (w, g) in GEO.items()}
TOL = 0.10                   # pair mean length within this of the longest pair
C, T, G = 0.3, 0.6, 0.6      # serpentine chamfer, top, gap between bumps (centreline)
END = 0.5                    # keep bumps this far from a segment's ends (corners)
nrm = R.N_
unit = R.unit


def offset_polyline(pts, s):
    """Offset a polyline of 45-degree-multiple segments by s along the left normal, mitred corners."""
    segs = []
    for a, c in zip(pts, pts[1:]):
        d = unit((c[0] - a[0], c[1] - a[1])); n = nrm(d)
        segs.append(((a[0] + n[0] * s, a[1] + n[1] * s), (c[0] + n[0] * s, c[1] + n[1] * s), d))
    out = [segs[0][0]]
    for (a1, c1, d1), (a2, c2, d2) in zip(segs, segs[1:]):
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-9: out.append(c1); continue
        t = ((a2[0] - a1[0]) * d2[1] - (a2[1] - a1[1]) * d2[0]) / den
        out.append((a1[0] + d1[0] * t, a1[1] + d1[1] * t))
    out.append(segs[-1][1])
    return out


def plen(pts): return sum(math.dist(a, c) for a, c in zip(pts, pts[1:]))


def cross(a, b): return a[0] * b[1] - a[1] * b[0]


def lines(name, r):
    """Copper of one routed pair: {side: [(layer, points)]}, its vias {side: [points]} and ground vias."""
    bo, go = R.BREAKOUT[name], R.GOAL[name]
    s = r['start']; m = tuple(s['mid']); sd = tuple(s['dir'])
    out, vias = {}, {}
    gnd = []
    for side in ('P', 'N'):
        bv = tuple(bo['vias'][side])
        sgn = 1 if cross(sd, (bv[0] - m[0], bv[1] - m[1])) > 0 else -1     # side of this line along the left normal
        parts = [(lay, [tuple(p) for p in pts]) for lay, pts in bo['stubs'][side]]
        vs = [bv]
        first = [tuple(s['at'])] + [tuple(p) for p in (r['in3'] if r['via'] else r['fcu'])[1:]]
        if r['via']:
            vx, vy = r['via'][:2]
            cl = first[:-1]                                   # In3 centreline up to its last corner before the row
            d_in = unit((vx - cl[-1][0], vy - cl[-1][1]))
            a = offset_polyline(cl, sgn * PITCH['In3.Cu'] / 2) if len(cl) > 1 else \
                [(cl[0][0] + nrm(d_in)[0] * sgn * PITCH['In3.Cu'] / 2, cl[0][1] + nrm(d_in)[1] * sgn * PITCH['In3.Cu'] / 2)]
            n_in = nrm(d_in)
            v2 = (round(vx + n_in[0] * sgn * R.VIA_P / 2, 4), round(vy + n_in[1] * sgn * R.VIA_P / 2, 4))
            parts.append(('In3.Cu', [bv] + a + [v2]))
            vs.append(v2)
            fc = [tuple(p) for p in r['fcu']][1:]
            d_out = unit((fc[0][0] - vx, fc[0][1] - vy))
            sgn2 = 1 if cross(d_out, (v2[0] - vx, v2[1] - vy)) > 0 else -1
            f = offset_polyline(fc, sgn2 * PITCH['F.Cu'] / 2)
            fstart = v2
        else:
            sgn2 = sgn
            f = offset_polyline(first, sgn2 * PITCH['F.Cu'] / 2)
            fstart = bv
        pad = tuple(go['pads'][side]); gy = go['at'][1]
        parts.append(('F.Cu', [fstart] + f + [(pad[0], round(gy - 0.35, 4)), pad]))
        # P must reach its J1 pad on the side it started: the offset end and the pad on the same side of the centre
        assert (f[-1][0] - go['at'][0]) * (pad[0] - go['at'][0]) > 0, (name, side, 'pair twisted')
        out[side] = parts; vias[side] = vs
    if r['via'] and r['via'][2]:
        vx, vy = r['via'][:2]
        cl = [tuple(s['at'])] + [tuple(p) for p in r['in3'][1:]]
        n_in = nrm(unit((vx - cl[-2][0], vy - cl[-2][1])))
        gnd = [(round(vx + n_in[0] * k * R.VIA_P, 4), round(vy + n_in[1] * k * R.VIA_P, 4)) for k in (-1.5, 1.5)]
    return out, vias, gnd


def lengths(name, r):
    out, _, _ = lines(name, r)
    return {side: sum(plen(pts) for _, pts in parts) for side, parts in out.items()}


def bump(a, c, t0, side, amp, ch=C):
    """Serpentine bump on segment a->c starting t0 mm from a, towards side (+1 left normal), amplitude amp."""
    d = unit((c[0] - a[0], c[1] - a[1])); n = nrm(d); n = (n[0] * side, n[1] * side)
    P = lambda u, v: (round(a[0] + d[0] * u + n[0] * v, 4), round(a[1] + d[1] * u + n[1] * v, 4))
    u = t0
    pts = [P(u, 0), P(u + ch, ch), P(u + ch, amp - ch), P(u + 2 * ch, amp), P(u + 2 * ch + T, amp),
           P(u + 3 * ch + T, amp - ch), P(u + 3 * ch + T, ch), P(u + 4 * ch + T, 0)]
    return [p for i, p in enumerate(pts) if i == 0 or math.dist(p, pts[i - 1]) > 1e-6]   # amp = 2 ch: no straight legs


def extra(amp, ch=C): return 2 * amp - (8 - 4 * math.sqrt(2)) * ch


class Checker:
    def __init__(self, b):
        """Fields as the router builds them: board copper with VIA_GROW round non-ground vias (F, for tracks) and
        without (Fv, for via rows); the other pairs' breakouts at the plain clearance, the pair's own breakout vias."""
        dsi = {p[k] for p in R.BREAKOUT.values() for k in ('P', 'N')}
        self.F0, self.E = R.base_fields(b, dsi, R.VIA_GROW)
        Fv0, _ = R.base_fields(b, dsi, 0.0)
        self.F, self.Fv = {}, {}
        for name in R.BREAKOUT:
            for base, store, vg in ((self.F0, self.F, None), (Fv0, self.Fv, 0.0)):
                F = {l: R.Field() for l in base}
                for l in F: F[l].mask = base[l].mask.copy()
                for other, bo in R.BREAKOUT.items():
                    tr = [(lay, a, c, GEO[lay][0]) for side in ('P', 'N') for lay, pts in bo['stubs'][side] for a, c in zip(pts, pts[1:])]
                    geo = dict(tracks=tr, vias=list(bo['vias'].values()))
                    if other != name: R.add_pair_obstacles(F, geo, 0.0, vg)
                    else:
                        for v in geo['vias']:
                            for l in F: F[l].circle(v[0], v[1], R.VIA_D / 2)
                for l in F: F[l].finish()
                store[name] = F

    def problems(self, name, r, others):
        """Clearance problems of pair `name` (route r) against the board, the other pairs and itself."""
        F = self.F[name]; probs = []
        tr, row = R.pair_copper(r)
        for lay, a, c in tr[1:]:
            k = max(1, int(math.dist(a, c) / 0.025))
            for i in range(k + 1):
                x, y = a[0] + (c[0] - a[0]) * i / k, a[1] + (c[1] - a[1]) * i / k
                if math.dist((x, y), tuple(r['via'][:2]) if r['via'] else (1e9, 1e9)) < R.VIA_D / 2 + 0.05: continue
                if F[lay].d(x, y) < R.HALF[lay] + R.CLR - 1e-3 or self.E.d(x, y) < R.HALF[lay] + R.EDGE:
                    probs.append(('board', lay, round(x, 3), round(y, 3))); break
        Fv = self.Fv[name]
        for v in row:
            if any(Fv[l].d(*v) < R.VIA_D / 2 + R.CLR - 1e-3 for l in Fv) or self.E.d(*v) < R.VIA_D / 2 + R.EDGE:
                probs.append(('board via', round(v[0], 3), round(v[1], 3)))
        for o, ro in others.items():
            otr, orow = R.pair_copper(ro)
            for lay, a, c in tr:
                for lo, ao, co in otr:
                    if lo == lay and R.seg_dist(a, c, ao, co) < 2 * R.HALF[lay] + R.CLR_DSI - 1e-3:
                        probs.append(('pair', o, lay, a, c))
                for v in orow:
                    if R.seg_dist(a, c, v, v) < R.VIA_D / 2 + R.HALF[lay] + R.CLR_DSI - 1e-3:
                        probs.append(('pair via', o, lay, a, c))
            for v in row:
                for lo, ao, co in otr:
                    if R.seg_dist(ao, co, v, v) < R.VIA_D / 2 + R.HALF[lo] + R.CLR_DSI - 1e-3:
                        probs.append(('via-pair', o, v))
        bad, vbad = R.self_conflicts(r)
        if bad or vbad: probs.append(('self', bad[:2], vbad[:2]))
        return probs


def candidates(r):
    """(key, segment index, a, c, layer) for every straight centreline run long enough for one bump."""
    out = []
    for key, lay in (('fcu', 'F.Cu'), ('in3', 'In3.Cu')):
        pts = r[key]
        for k, (a, c) in enumerate(zip(pts, pts[1:])):
            if key == 'fcu' and k == 0 and r['via']: continue          # the 0.6 mm after the via row
            if key == 'in3' and k == len(pts) - 2: continue            # the 0.6 mm before it
            if key == 'fcu' and k == len(pts) - 2: continue            # the J1 entry
            if math.dist(a, c) >= 2 * END + 4 * C + T: out.append((key, k, tuple(a), tuple(c), lay))
    return out


def with_bump(r, key, k, pts_b):
    q = dict(r); q[key] = r[key][:k + 1] + [list(p) for p in pts_b] + r[key][k + 1:]
    return q


def match(chk, routes):
    lens = {n: lengths(n, r) for n, r in routes.items()}
    mean = lambda n: max(lens[n]['P'], lens[n]['N'])    # the shorter line is brought up to it afterwards
    target = max(mean(n) for n in routes)
    log = []
    for name in sorted(routes, key=mean):
        while target - mean(name) > TOL:
            need = target - mean(name)
            others = {o: routes[o] for o in routes if o != name}
            r = routes[name]; best = None
            for key, k, a, c, lay in candidates(r):
                L = math.dist(a, c)
                amp_need = (need + (8 - 4 * math.sqrt(2)) * C) / 2
                for side in (1, -1):
                    t0 = END
                    while t0 + 4 * C + T <= L - END + 1e-9:
                        for amp in [min(amp_need, A) for A in (5.0, 4.0, 3.2, 2.5, 2.0, 1.6, 1.3, 1.0, 0.8, 0.6)]:
                            ch = C if amp >= 2 * C else amp / 2
                            if amp < 0.2: continue
                            pts_b = bump(a, c, t0, side, amp, ch)
                            q = with_bump(r, key, k, pts_b)
                            if not chk.problems(name, q, others):
                                gain = extra(amp, ch)
                                score = (lay == 'F.Cu', gain)
                                if best is None or score > best[0]: best = (score, q, (key, k, round(t0, 2), side, round(amp, 3)))
                                break
                        if best and best[0][1] >= need - 1e-6 and best[0][0]: break
                        t0 += 0.2
                    if best and best[0][1] >= need - 1e-6 and best[0][0]: break
                if best and best[0][1] >= need - 1e-6 and best[0][0]: break
            if best is None:
                log.append(f'{name}: no room for a serpentine, {need:.2f} mm short'); break
            routes[name] = best[1]; lens[name] = lengths(name, best[1])
            log.append(f'{name}: bump {best[2]} +{best[0][1]:.2f} mm')
    return log


TH, TL, TS, TM = 0.25, 0.2, 0.4, 0.4     # skew tooth height (max), top, spacing, margin from a segment's ends


def closest(p, pts):
    best = (1e9, None)
    for a, c in zip(pts, pts[1:]):
        dx, dy = c[0] - a[0], c[1] - a[1]; L2 = dx * dx + dy * dy
        t = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        q = (a[0] + t * dx, a[1] + t * dy); d = math.dist(p, q)
        if d < best[0]: best = (d, q)
    return best


def compensate(chk, name, parts, others):
    """Bring the shorter line of a pair to its partner's length with outward teeth. parts: {side: [(layer, pts)]};
    others: list of (layer, pts, width) of the other pairs. Returns the new parts and a log line."""
    L = {sd: sum(plen(pts) for _, pts in parts[sd]) for sd in ('P', 'N')}
    sh = 'P' if L['P'] < L['N'] else 'N'; pa = 'N' if sh == 'P' else 'P'
    need = abs(L['P'] - L['N'])
    F, E = chk.F[name], chk.E
    teeth = 0
    for li in range(len(parts[sh])):
        lay, pts = parts[sh][li]
        if lay == 'B.Cu' or need < 0.05: continue
        w = GEO[lay][0]
        partner = next(p for l2, p in parts[pa] if l2 == lay)
        k = 1
        while k < len(pts) - 3 and need >= 0.05:
            a, c = pts[k], pts[k + 1]
            seg = math.dist(a, c)
            d = unit((c[0] - a[0], c[1] - a[1])); n = nrm(d)
            mid = ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
            q = closest(mid, partner)[1]
            out = -1 if (q[0] - mid[0]) * n[0] + (q[1] - mid[1]) * n[1] > 0 else 1
            t0 = TM; placed = False
            while need >= 0.05:
                h = min(TH, need / (2 * (math.sqrt(2) - 1)))
                if h < 0.03: need = 0; break
                if t0 + 2 * h + TL > seg - TM + 1e-9: break
                P_ = lambda u, v: (round(a[0] + d[0] * u + n[0] * out * v, 4), round(a[1] + d[1] * u + n[1] * out * v, 4))
                tooth = [P_(t0, 0), P_(t0 + h, h), P_(t0 + h + TL, h), P_(t0 + 2 * h + TL, 0)]
                good = True
                for (x0, y0), (x1, y1) in zip(tooth, tooth[1:]):
                    for i in range(11):
                        x, y = x0 + (x1 - x0) * i / 10, y0 + (y1 - y0) * i / 10
                        if F[lay].d(x, y) < w / 2 + R.CLR or E.d(x, y) < w / 2 + R.EDGE: good = False
                        for lo, po, wo in others:
                            if lo == lay and closest((x, y), po)[0] < w / 2 + wo / 2 + R.CLR_DSI: good = False
                        for sd2 in ('P', 'N'):
                            for l2, p2 in parts[sd2]:
                                if l2 != lay: continue
                                # the partner and this line's own neighbours are allowed close; anything else 0.3 mm away
                                if sd2 == sh and p2 is pts:
                                    segs = [(p2[j], p2[j + 1]) for j in range(len(p2) - 1) if not (k - 1 <= j <= k + 1)]
                                    lim = w + R.CLR_DSI
                                else:
                                    segs = list(zip(p2, p2[1:])); lim = w + GEO[lay][1] - 1e-3
                                if any(closest((x, y), [s0, s1])[0] < lim for s0, s1 in segs): good = False
                        if not good: break
                    if not good: break
                if good:
                    pts = pts[:k + 1] + tooth + pts[k + 1:]
                    parts[sh][li] = (lay, pts)
                    need -= 2 * h * (math.sqrt(2) - 1); teeth += 1; placed = True
                    k += 4; a = pts[k]; seg = math.dist(a, c); t0 = TS
                else:
                    t0 += 0.1
            k += 1
    L2 = {sd: sum(plen(p) for _, p in parts[sd]) for sd in ('P', 'N')}
    return parts, f'{name}: skew {L["P"] - L["N"]:+.3f} -> {L2["P"] - L2["N"]:+.3f} mm with {teeth} teeth on {sh}'


def main():
    import pcbnew
    board, rin, out = sys.argv[1:4]
    J = json.load(open(rin))
    b = pcbnew.LoadBoard(board)
    chk = Checker(b)
    routes = J['pairs']
    for name, r in routes.items():
        p = chk.problems(name, r, {o: routes[o] for o in routes if o != name})
        print(name, 'routed copper problems:', p[:4] if p else 'none', flush=True)
    log = match(chk, routes)
    print('\n'.join(log), flush=True)
    res = dict(geo=GEO, lines={}, vias={}, gnd_vias=[], report={})
    built = {name: lines(name, r) for name, r in routes.items()}
    for name, r in routes.items():
        p = chk.problems(name, r, {o: routes[o] for o in routes if o != name})
        assert not p, (name, p[:4])
        others = [(lay, pts, GEO[lay][0]) for o, (pp, _, _) in built.items() if o != name for sd in pp for lay, pts in pp[sd]]
        parts, line = compensate(chk, name, built[name][0], others)
        print(line, flush=True)
        built[name] = (parts,) + built[name][1:]
    for name, r in routes.items():
        parts, vias, gnd = built[name]
        bo = R.BREAKOUT[name]
        for side in ('P', 'N'):
            net = bo[side]
            res['lines'][net] = [[lay, [[round(x, 4), round(y, 4)] for x, y in pts], GEO[lay][0]] for lay, pts in parts[side]]
            res['vias'][net] = [list(v) for v in vias[side]]
        res['gnd_vias'] += [list(v) for v in gnd]
        L = {side: sum(plen(pts) for _, pts in parts[side]) for side in ('P', 'N')}
        res['report'][name] = dict(P=round(L['P'], 3), N=round(L['N'], 3), skew=round(L['P'] - L['N'], 3),
                                   layers=[lay for lay, _ in parts['P']], via_row=r['via'])
    means = {n: (v['P'] + v['N']) / 2 for n, v in res['report'].items()}
    res['report']['spread'] = round(max(means.values()) - min(means.values()), 3)
    res['pairs'] = routes
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps(res['report'], indent=1))


if __name__ == '__main__':
    main()
