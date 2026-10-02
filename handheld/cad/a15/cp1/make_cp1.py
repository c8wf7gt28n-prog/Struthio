#!/usr/bin/env python3
"""STRUTHIO HANDHELD · STRUTHIO-CP1, the A1.5 control PCB, as manufacturing files.

Two layers, 1.0 mm FR-4, ENIG. The outline is the A1.5 CAD's own
(../svg/cp1_outline.svg from STRUTHIO15.scad). Front: four interdigitated
contact pads (7.0 mm) for the CM1 6 mm carbon pills and the GND net. Back:
the four signal traces to a 5-pad wire row (GND, LEFT, DART L, DART R, RIGHT).
Nets: LEFT -> GPIO17, RIGHT -> GPIO18, DART L -> GPIO21, DART R -> GPIO38,
GND -> board GND (all active low with the ESP32's internal pull-ups).

Writes gerbers/ (RS-274X: F_Cu, B_Cu, F_Mask, B_Mask, B_Silk, Edge_Cuts;
Excellon PTH + NPTH), cp1_gerbers.zip, cp1_layers.png, and runs a design-rule
check (clearances, widths, edge distance) on the generated copper.
    python3 cad/a15/cp1/make_cp1.py
"""
import os, re, sys, zipfile
from shapely.geometry import Polygon, Point, LineString, box, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity

HERE = os.path.dirname(os.path.abspath(__file__))
SCAD = os.path.join(HERE, '..', 'STRUTHIO15.scad')
OUT = os.path.join(HERE, 'gerbers')
os.makedirs(OUT, exist_ok=True)

# ---- parameters from the CAD ---------------------------------------------------------------
P = {}
for line in open(SCAD).read().splitlines():
    for stmt in line.split('//')[0].split(';'):
        m = re.match(r'\s*([A-Z][A-Z0-9_]*)\s*=\s*(.+)$', stmt)
        if m:
            try: P[m.group(1)] = eval(m.group(2), {'__builtins__': {}}, P)
            except Exception: pass

def svg_rings(path):
    t = open(path).read()
    rings = []
    for d in re.findall(r'<path d="([^"]*)"', t, re.S):
        for sub in re.split(r'M', d)[1:]:
            pts = [tuple(map(float, q.split(','))) for q in re.findall(r'-?[\d.]+,-?[\d.]+', sub)]
            if len(pts) > 2: rings.append(Polygon([(x, -y) for x, y in pts]).buffer(0))
    return sorted(rings, key=lambda p: -p.area)

rings = svg_rings(os.path.join(HERE, '..', 'svg', 'cp1_outline.svg'))
outer = rings[0]
npth = [r for r in rings[1:] if r.area < 10]                 # carrier heat-stake pin holes
cutouts = [r for r in rings[1:] if r.area >= 10]             # speaker window (and any other large hole)
board = outer
for c in cutouts: board = board.difference(c)
for h in npth: board = board.difference(h)

# ---- design rules -------------------------------------------------------------------------------
TRACE = 0.40          # signal trace width
GND_TRACE = 0.50
CLEAR = 0.25          # copper to copper, different nets (fab minimum is ~0.1)
EDGE = 0.40           # copper to board edge / holes
FINGER, PITCH = 0.30, 0.60
PAD_R, RING_IN = 3.5, 3.1
VIA_D, VIA_PAD = 0.40, 0.80
CONN_D, CONN_PAD, CONN_PITCH = 1.00, 1.80, 2.54
CONN_Y = -36.2
CONN_X0 = -22.0
NETS = ['GND', 'LEFT', 'DART_L', 'DART_R', 'RIGHT']          # wire row, left to right
CONN = {n: (CONN_X0 + i * CONN_PITCH, CONN_Y) for i, n in enumerate(NETS)}

BX, BY, RY, DP = P['BTN_X'], P['BTN_Y'], P['ROCKER_Y'], P['DART_PITCH']
PADS = {   # name: (centre, signal side: -1 = signal comb on the left)
    'LEFT':   ((-BX, BY), -1),
    'RIGHT':  ((BX, BY), +1),
    'DART_L': ((-DP / 2, RY), -1),
    'DART_R': ((DP / 2, RY), +1),
}

def comb(c, sig_side):
    """interdigitated contact: (signal copper, GND copper) inside a 7.0 mm circle"""
    cx, cy = c
    disc = Point(c).buffer(PAD_R, 128)
    ring = disc.difference(Point(c).buffer(RING_IN, 128))
    left = box(cx - 10, cy - 10, cx - 0.15, cy + 10)
    right = box(cx + 0.15, cy - 10, cx + 10, cy + 10)
    sig_half, gnd_half = (ring.intersection(left), ring.intersection(right)) if sig_side < 0 else (ring.intersection(right), ring.intersection(left))
    sig, gnd = [sig_half], [gnd_half]
    for k in range(-4, 5):
        y = cy + k * PITCH
        # the finger's far corner stays CLEAR inside the other comb's ring (radial distance)
        dx = ((RING_IN - CLEAR - 0.02) ** 2 - (abs(k * PITCH) + FINGER / 2) ** 2) ** 0.5
        mine_sig = (k % 2 == 0)
        own = sig_side if mine_sig else -sig_side           # which side the finger's comb is on
        x_from = cx + own * (PAD_R - 0.1)
        x_to = cx - own * dx
        f = box(min(x_from, x_to), y - FINGER / 2, max(x_from, x_to), y + FINGER / 2).intersection(disc)
        (sig if mine_sig else gnd).append(f)
    return unary_union(sig), unary_union(gnd)

def seg(points, w):
    return LineString(points).buffer(w / 2, cap_style=1, join_style=1)

front = {n: [] for n in NETS}
back = {n: [] for n in NETS}
vias = []          # (x, y, net)
for name, (c, side) in PADS.items():
    s, g = comb(c, side)
    front[name].append(s); front['GND'].append(g)
    vx = c[0] + side * (PAD_R + 0.8)
    vias.append((vx, c[1], name))
    front[name].append(seg([(c[0] + side * (PAD_R - 0.2), c[1]), (vx, c[1])], TRACE))

# back-layer signal routes (via -> wire pad), checked below
L, DL, DR, R = (CONN[n][0] for n in ('LEFT', 'DART_L', 'DART_R', 'RIGHT'))
vx = {n: v[0] for v in vias for n in [v[2]]}
routes = {
    'LEFT':   [(vx['LEFT'], BY), (vx['LEFT'], -41.4), (L, -41.4), (L, CONN_Y)],
    'DART_L': [(vx['DART_L'], RY), (vx['DART_L'], -40.4), (DL, -40.4), (DL, CONN_Y)],
    'DART_R': [(vx['DART_R'], RY), (vx['DART_R'], -39.3), (DR, -39.3), (DR, CONN_Y)],
    'RIGHT':  [(vx['RIGHT'], BY), (vx['RIGHT'], -38.3), (R, -38.3), (R, CONN_Y)],
}
for n, pts in routes.items(): back[n].append(seg(pts, TRACE))
# front GND bus: wire pad -> down the left -> across below the speaker window -> up the right,
# with stubs into each pad's GND comb
gx = 18.6; gy = -56.0
G = CONN['GND']
front['GND'].append(seg([G, (G[0], -37.6), (-gx, -39.6), (-gx, gy), (gx, gy), (gx, BY + PITCH)], GND_TRACE))
for name, (c, side) in PADS.items():
    if name in ('LEFT', 'RIGHT'):
        yy = c[1] + PITCH                 # enter along a GND finger (k = 1), ending on the GND ring
        front['GND'].append(seg([(-gx if c[0] < 0 else gx, yy), (c[0] - side * (PAD_R - 0.1), yy)], GND_TRACE))
    else:
        x = c[0] - side * 2.5
        front['GND'].append(seg([(x, gy), (x, c[1] + 2.45 - 0.2)], GND_TRACE))
# pads and vias on both layers
for x, y, n in vias:
    for layer in (front, back): layer[n].append(Point(x, y).buffer(VIA_PAD / 2, 32))
for n, (x, y) in CONN.items():
    for layer in (front, back): layer[n].append(Point(x, y).buffer(CONN_PAD / 2, 32))
front = {n: unary_union(v) for n, v in front.items()}
back = {n: unary_union(v) for n, v in back.items()}

# ---- design-rule check ---------------------------------------------------------------------------
fails = []
def check(ok, what):
    print(('PASS  ' if ok else 'FAIL  ') + what)
    if not ok: fails.append(what)
for lname, layer in (('front', front), ('back', back)):
    names = list(layer)
    pairs = [(layer[a].distance(layer[b]), a, b) for i, a in enumerate(names) for b in names[i + 1:] if not layer[a].is_empty and not layer[b].is_empty]
    worst, wa, wb = min(pairs)
    if worst < CLEAR:
        from shapely.ops import nearest_points
        print('   closest', wa, wb, [(round(q.x, 2), round(q.y, 2)) for q in nearest_points(layer[wa], layer[wb])])
    check(worst >= CLEAR - 1e-6, f'{lname}: {worst:.3f} mm minimum copper clearance between nets (>= {CLEAR})')
    allcu = unary_union(list(layer.values()))
    inside = board.buffer(-EDGE)
    out = allcu.difference(inside)
    check(out.area < 1e-4, f'{lname}: all copper >= {EDGE} mm inside the board edge, window and pin holes')
    for n, g in layer.items():
        parts = list(getattr(g, 'geoms', [g]))
        if lname == 'front' and n == 'GND': check(len(parts) == 1, f'front GND is one connected copper area ({len(parts)})')
for n in ('LEFT', 'RIGHT', 'DART_L', 'DART_R'):
    f = list(getattr(front[n], 'geoms', [front[n]])); b = list(getattr(back[n], 'geoms', [back[n]]))
    check(len(f) == 2 and len(b) == 1, f'{n}: pad comb + via on the front, one trace via -> wire pad on the back')
for name, (c, side) in PADS.items():
    pill = Point(c).buffer(P['PILL_D'] / 2)
    s = front[name].intersection(pill).area; g = front['GND'].intersection(pill).area
    check(s > 4 and g > 4, f'{name}: a 6 mm pill bridges signal ({s:.1f} mm2) and GND ({g:.1f} mm2) copper')
check(abs(PADS['DART_R'][0][0] - PADS['DART_L'][0][0] - 24.0) < 1e-9, 'DART pad centres 24.0 mm apart (locked)')
for x, y, n in vias:
    check(board.buffer(-EDGE).contains(Point(x, y).buffer(VIA_PAD / 2)), f'via {n} at ({x:.1f}, {y:.1f}) inside the board')

# ---- gerbers -------------------------------------------------------------------------------------------
def fmt(v): return f'{int(round(v * 1e6)):d}'
def header(name, polarity_comment):
    return ['G04 STRUTHIO-CP1 A1.5 ' + name + '*', '%FSLAX46Y46*%', '%MOMM*%', '%LPD*%', 'G01*', '%ADD10C,0.100000*%', 'G04 ' + polarity_comment + '*']
def region(ring):
    pts = list(ring.coords)
    out = ['G36*', f'X{fmt(pts[0][0])}Y{fmt(pts[0][1])}D02*']
    out += [f'X{fmt(x)}Y{fmt(y)}D01*' for x, y in pts[1:]]
    return out + ['G37*']
def regions(geom):
    out = []
    for p in getattr(geom, 'geoms', [geom]):
        if p.is_empty: continue
        out += ['%LPD*%'] + region(p.exterior)
        for i in p.interiors: out += ['%LPC*%'] + region(i)
    return out + ['%LPD*%']
def write(name, lines):
    with open(os.path.join(OUT, name), 'w') as f: f.write('\n'.join(lines + ['M02*']) + '\n')

mask_open = 0.10
F_CU = unary_union(list(front.values())); B_CU = unary_union(list(back.values()))
write('STRUTHIO-CP1-F_Cu.gtl', header('F_Cu', 'front copper: contact combs, GND bus') + regions(F_CU))
write('STRUTHIO-CP1-B_Cu.gbl', header('B_Cu', 'back copper: signal traces, wire pads') + regions(B_CU))
f_mask = unary_union([Point(c).buffer(PAD_R + mask_open, 128) for c, _ in PADS.values()] + [Point(p).buffer(CONN_PAD / 2 + mask_open, 32) for p in CONN.values()])
b_mask = unary_union([Point(p).buffer(CONN_PAD / 2 + mask_open, 32) for p in CONN.values()])
write('STRUTHIO-CP1-F_Mask.gts', header('F_Mask', 'openings: contacts (ENIG) and wire pads') + regions(f_mask))
write('STRUTHIO-CP1-B_Mask.gbs', header('B_Mask', 'openings: wire pads') + regions(b_mask))
edge = header('Edge_Cuts', 'board outline, speaker window, post notches') + ['D10*']
for r in [outer.exterior] + [c.exterior for c in cutouts]:
    pts = list(r.coords)
    edge += [f'X{fmt(pts[0][0])}Y{fmt(pts[0][1])}D02*'] + [f'X{fmt(x)}Y{fmt(y)}D01*' for x, y in pts[1:]]
write('STRUTHIO-CP1-Edge_Cuts.gm1', edge)

# silkscreen (back): stroke font for the labels, drawn as 0.15 mm lines
STROKES = {  # 5x7 grid strokes, unit 1 = 0.25 mm
    'A': [[(0,0),(0,5),(2,7),(4,5),(4,0)],[(0,3),(4,3)]], 'C': [[(4,1),(3,0),(1,0),(0,1),(0,6),(1,7),(3,7),(4,6)]],
    'D': [[(0,0),(0,7),(3,7),(4,6),(4,1),(3,0),(0,0)]], 'E': [[(4,0),(0,0),(0,7),(4,7)],[(0,3.5),(3,3.5)]],
    'G': [[(4,6),(3,7),(1,7),(0,6),(0,1),(1,0),(3,0),(4,1),(4,3),(2,3)]], 'H': [[(0,0),(0,7)],[(4,0),(4,7)],[(0,3.5),(4,3.5)]],
    'I': [[(1,0),(3,0)],[(2,0),(2,7)],[(1,7),(3,7)]], 'L': [[(0,7),(0,0),(4,0)]], 'N': [[(0,0),(0,7),(4,0),(4,7)]],
    'O': [[(1,0),(3,0),(4,1),(4,6),(3,7),(1,7),(0,6),(0,1),(1,0)]], 'P': [[(0,0),(0,7),(3,7),(4,6),(4,4),(3,3),(0,3)]],
    'R': [[(0,0),(0,7),(3,7),(4,6),(4,4),(3,3),(0,3)],[(2,3),(4,0)]], 'S': [[(0,1),(1,0),(3,0),(4,1),(4,3),(0,4),(0,6),(1,7),(3,7),(4,6)]],
    'T': [[(0,7),(4,7)],[(2,7),(2,0)]], 'U': [[(0,7),(0,1),(1,0),(3,0),(4,1),(4,7)]], 'F': [[(4,7),(0,7),(0,0)],[(0,3.5),(3,3.5)]],
    'G1': [], '1': [[(1,6),(2,7),(2,0)],[(1,0),(3,0)]], '5': [[(4,7),(0,7),(0,4),(3,4),(4,3),(4,1),(3,0),(0,0)]],
    '0': [[(1,0),(3,0),(4,1),(4,6),(3,7),(1,7),(0,6),(0,1),(1,0)],[(0,1),(4,6)]], '.': [[(2,0),(2,0.4)]],
    '-': [[(1,3.5),(3,3.5)]], ' ': [], 'M': [[(0,0),(0,7),(2,4),(4,7),(4,0)]], 'B': [[(0,0),(0,7),(3,7),(4,6),(4,4.5),(3,3.5),(0,3.5)],[(3,3.5),(4,2.5),(4,1),(3,0),(0,0)]],
    'K': [[(0,0),(0,7)],[(4,7),(0,3),(4,0)]], 'V': [[(0,7),(2,0),(4,7)]], 'W': [[(0,7),(1,0),(2,4),(3,0),(4,7)]], 'Y': [[(0,7),(2,4),(4,7)],[(2,4),(2,0)]],
    'X': [[(0,0),(4,7)],[(0,7),(4,0)]], '4': [[(3,0),(3,7),(0,2),(4,2)]], '3': [[(0,6),(1,7),(3,7),(4,6),(4,4.5),(3,3.5),(4,2.5),(4,1),(3,0),(1,0),(0,1)],[(1.5,3.5),(3,3.5)]],
    '2': [[(0,6),(1,7),(3,7),(4,6),(4,4),(0,0),(4,0)]], '7': [[(0,7),(4,7),(1,0)]], '8': [[(1,3.5),(0,4.5),(0,6),(1,7),(3,7),(4,6),(4,4.5),(3,3.5),(1,3.5),(0,2.5),(0,1),(1,0),(3,0),(4,1),(4,2.5),(3,3.5)]],
    '9': [[(4,4),(1,4),(0,5),(0,6),(1,7),(3,7),(4,6),(4,1),(3,0),(1,0)]], '6': [[(4,6),(3,7),(1,7),(0,6),(0,1),(1,0),(3,0),(4,1),(4,3),(3,4),(0,4)]],
}
def text_lines(s, x, y, h=1.2, mirror=True):
    """strokes for text; mirrored because the back layer is viewed from behind"""
    u = h / 7; out = []; cx = x
    for ch in s:
        for st in STROKES.get(ch, []):
            pts = [((cx + px * u) * (-1 if mirror else 1), y + py * u) for px, py in st]
            out.append(pts)
        cx += 6 * u
    return out
def width_of(s, h=1.2): return len(s) * 6 * h / 7
silk = []   # laid out in BACK-VIEW coordinates (x' = -x), then mirrored onto the board
title = 'STRUTHIO-CP1 A1.5'
silk += text_lines(title, -width_of(title) / 2, -61.6, mirror=False)
sub = '1.0 FR4 ENIG'
silk += text_lines(sub, -width_of(sub, 1.0) / 2, -63.6, 1.0, mirror=False)
for n, (x, y) in CONN.items():
    lab = {'GND': 'G', 'LEFT': 'L', 'DART_L': 'DL', 'DART_R': 'DR', 'RIGHT': 'R'}[n]
    silk += text_lines(lab, -x - width_of(lab, 0.9) / 2, y + 1.1, 0.9, mirror=False)
silk_geom = unary_union([LineString(l).buffer(0.075) for l in silk if len(l) > 1])
silk_geom = affinity.scale(silk_geom, -1, 1, origin=(0, 0))      # back-side text reads correctly from behind
silk_geom = silk_geom.difference(unary_union([b_mask.buffer(0.15)])).intersection(board.buffer(-0.3))
write('STRUTHIO-CP1-B_Silk.gbo', header('B_Silk', 'back legend') + regions(silk_geom))

# drills (Excellon, mm)
def drill(name, groups, plated):
    lines = ['M48', '; STRUTHIO-CP1 A1.5 ' + ('PTH' if plated else 'NPTH'), 'FMAT,2', 'METRIC,TZ']
    lines += [f'T{i + 1}C{d:.3f}' for i, (d, _) in enumerate(groups)] + ['%', 'G05']
    for i, (d, pts) in enumerate(groups):
        lines.append(f'T{i + 1}')
        lines += [f'X{x:.3f}Y{y:.3f}' for x, y in pts]
    lines.append('M30')
    open(os.path.join(OUT, name), 'w').write('\n'.join(lines) + '\n')
drill('STRUTHIO-CP1-PTH.drl', [(VIA_D, [(x, y) for x, y, _ in vias]), (CONN_D, list(CONN.values()))], True)
drill('STRUTHIO-CP1-NPTH.drl', [(2 * (h.area / 3.14159) ** 0.5, [(h.centroid.x, h.centroid.y)]) for h in npth], False)

# netlist / readme for the fab
open(os.path.join(OUT, 'README.txt'), 'w').write(f'''STRUTHIO-CP1 (A1.5 control PCB), generated by cad/a15/cp1/make_cp1.py from STRUTHIO15.scad
Board: 2 layers, FR-4, 1.0 mm, 1 oz copper, ENIG finish (contact pads), green or black solder mask, white legend (back).
Outline: Edge_Cuts (includes the 13.0 mm speaker window and the two lower post notches).
Size: {outer.bounds[2]-outer.bounds[0]:.2f} x {outer.bounds[3]-outer.bounds[1]:.2f} mm.
Min trace 0.40 mm, min finger 0.30 mm, min space 0.25 mm (combs: 0.30 / 0.30), vias 0.40 / 0.80 mm, wire pads 1.0 / 1.8 mm.
Front: four interdigitated contacts, 7.0 mm, for 6.0 mm carbon pills (CM1). Keep the contacts clean: ENIG, no HASL, no silk on the front.
Back: wire pads, left to right: {', '.join(NETS)} (2.54 mm pitch).
Nets: LEFT -> ESP32 GPIO17, RIGHT -> GPIO18, DART_L -> GPIO21, DART_R -> GPIO38, GND -> board GND.
NPTH: 2 x {2 * (npth[0].area / 3.14159) ** 0.5:.2f} mm for the carrier heat-stake pins.
''')
with zipfile.ZipFile(os.path.join(HERE, 'cp1_gerbers.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(OUT)): z.write(os.path.join(OUT, f), f)

# ---- preview ------------------------------------------------------------------------------------------
try:
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath
    def patch(ax, g, **kw):
        for p in getattr(g, 'geoms', [g]):
            if p.is_empty: continue
            verts, codes = [], []
            for r in [p.exterior, *p.interiors]:
                c = list(r.coords); verts += c; codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
            ax.add_patch(PathPatch(MPath(verts, codes), **kw))
    fig, axs = plt.subplots(1, 2, figsize=(16, 7))
    for ax, (title_, cu, mask, mirror) in zip(axs, (('FRONT (contacts, faces the CM1 mat)', F_CU, f_mask, False), ('BACK (seen from behind)', B_CU, b_mask, True))):
        T = (lambda g: affinity.scale(g, -1, 1, origin=(0, 0))) if mirror else (lambda g: g)
        patch(ax, T(board), facecolor='#1d5c35', edgecolor='k', lw=1)
        patch(ax, T(cu), facecolor='#c9a227', edgecolor='none', alpha=0.9)
        patch(ax, T(mask.intersection(cu)), facecolor='#f2d16b', edgecolor='none')
        if mirror: patch(ax, T(silk_geom), facecolor='white', edgecolor='none')
        for x, y, _ in vias: patch(ax, T(Point(x, y).buffer(VIA_D / 2)), facecolor='k')
        for x, y in CONN.values(): patch(ax, T(Point(x, y).buffer(CONN_D / 2)), facecolor='k')
        for h in npth: patch(ax, T(h), facecolor='white', edgecolor='k')
        ax.set_title(title_); ax.set_aspect('equal'); ax.autoscale(); ax.axis('off')
    plt.suptitle(f'STRUTHIO-CP1 (A1.5)  {outer.bounds[2]-outer.bounds[0]:.1f} x {outer.bounds[3]-outer.bounds[1]:.1f} mm, 1.0 mm FR-4, ENIG')
    plt.savefig(os.path.join(HERE, 'cp1_layers.png'), dpi=110, bbox_inches='tight')
except ImportError:
    print('SKIP: preview (no matplotlib)')
print('CP1 DRC: ' + ('all pass' if not fails else f'{len(fails)} failure(s)'))
sys.exit(1 if fails else 0)
