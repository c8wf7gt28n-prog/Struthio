# R26 edit 32: the three MIPI-DSI pairs, routed as coupled pairs (r26_dsi_routes.json, written by dsi_pair_router.py).
#  Each line: U1 pad (B.Cu) -> breakout stub -> via -> In3.Cu (0.10 mm, 0.18 mm gap: about 100 ohm differential between
#  the In2 ground area of edit 33 and In4) -> via -> F.Cu (0.127 mm, 0.18 mm gap: about 100 ohm over In1) -> J1 pad.
#  P and N take the same layers and the same two vias; the second via pair has a ground via on each side where both fit.
#  The P and N tracks are the pair centreline offset by half the pitch with mitred 45 degree corners; tapers join the
#  0.55 mm via pitch and the 0.5 mm J1 pad pitch. Edit 33 matches the lengths.
exec(open(sys.argv[2]).read())
import json, os
J = json.load(open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'r26_dsi_routes.json')))
GEO = {k: tuple(v) for k, v in J['geo'].items()}
PITCH = {l: w + g for l, (w, g) in GEO.items()}
VIA_P = 0.55
nrm = lambda d: (-d[1], d[0])
unit = lambda d: (d[0] / math.hypot(*d), d[1] / math.hypot(*d))

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

def rnd(p): return (round(p[0], 4), round(p[1], 4))
report = []
for name, r in J['pairs'].items():
    bo = J['breakout'][name]; go = J['goal'][name]
    nP, nN = net(bo['P']), net(bo['N'])
    # breakout stubs and vias
    for side, nt in (('P', nP), ('N', nN)):
        for lay, pts in bo['stubs'][side]: add(lay, pts, nt, GEO[lay][0])
        add_via(*bo['vias'][side], nt)
    corners = [(c[0], c[1]) for c in r['corners']]; lays = [c[2] for c in r['corners']]
    sdir = tuple(bo['sdir']); c0 = tuple(bo['start'])
    n0 = nrm(sdir)
    pside = 1 if (bo['vias']['P'][0] - c0[0]) * n0[0] + (bo['vias']['P'][1] - c0[1]) * n0[1] > 0 else -1
    # split the centreline at the via row (the one segment whose ends are on different layers)
    k = next(i for i in range(len(lays) - 1) if lays[i] != lays[i + 1])
    vx, vy, flanks = r['via']
    d = unit((corners[k + 1][0] - corners[k][0], corners[k + 1][1] - corners[k][1])); n = nrm(d)
    inner = corners[:k + 1]; outer = corners[k + 1:]
    # In3 run: from the start taper to 0.6 mm before the via row; F.Cu run: from 0.6 mm after it
    pre = (vx - d[0] * 0.6, vy - d[1] * 0.6); post = (vx + d[0] * 0.6, vy + d[1] * 0.6)
    in3 = inner + [pre] if math.dist(inner[-1], pre) > 1e-6 else inner
    fcu = [post] + outer if math.dist(outer[0], post) > 1e-6 else outer
    gx, gy = go['at']
    for side, nt in (('P', nP), ('N', nN)):
        sgn = pside if side == 'P' else -pside
        a = offset_polyline(in3, sgn * PITCH['In3.Cu'] / 2)
        f = offset_polyline(fcu, sgn * PITCH['F.Cu'] / 2)
        via = (vx + n[0] * sgn * VIA_P / 2, vy + n[1] * sgn * VIA_P / 2)
        add('In3.Cu', [bo['vias'][side]] + a + [via], nt, GEO['In3.Cu'][0])
        add_via(*rnd(via), nt)
        pad_x = go['pads'][side][0]
        add('F.Cu', [via] + f + [(pad_x, gy - 0.35), go['pads'][side]], nt, GEO['F.Cu'][0])
    if flanks:
        for sgn in (-1, 1): add_via(round(vx + n[0] * sgn * 1.5 * VIA_P, 4), round(vy + n[1] * sgn * 1.5 * VIA_P, 4), net('GND'))
    report.append('%s via row (%.2f, %.2f)%s' % (name, vx, vy, ' with ground vias' if flanks else ''))
print('dsi route: ' + '; '.join(report))
