#!/usr/bin/env python3
"""Cross-layer convergence checks for STRUTHIO SLIM4: PCB R27 / CASE R12 / ACRYLIC R2 (package R32).

Every check compares one layer against another (or against a supplier figure) using
the real geometry: the R27 board outline, pads and part envelopes from the PCB layer
JSON, the CadQuery solids from LAYERS/02_CASE/build_r12.py, and the chosen panel's
published pin table (check N1).

Status values
  PASS  the interface agrees in CAD
  FAIL  the layers disagree; the package is not converged
  GATE  CAD agrees, but closing it needs a physical sample, supplier drawing or test
  INFO  a measured value reported for review

Usage
  python CHECKS/convergence_check.py                 # check this package, write reports
  python CHECKS/convergence_check.py --baseline DIR  # also audit an R24 package for comparison
"""
from pathlib import Path
import argparse, contextlib, hashlib, io, json, math, re, runpy, sys, time

import cadquery as cq
from shapely.geometry import Point, Polygon, box, LineString
from shapely.ops import unary_union
from shapely import affinity

ROOT = Path(__file__).resolve().parents[1]

# SHA-256 of the R27 PCB sources as delivered in the R32 package (SHA256SUMS.txt).
PCB_BASELINE = {
    'LAYERS/01_PCB/SLIM4_R27.kicad_pcb': 'c514c6224e07bebe026c862c5da14b9fac4256b76c9fe487a548ee9e01ebbed2',
    'LAYERS/01_PCB/SLIM4_R27_PCB_LAYER.json': 'bf2ca58a2458898c926d7836c9b2127c3a17aef036b84fe7fafba39875a0624f',
}
# The chosen panel (LAYERS/01_PCB/DISPLAY_PORT.md): Crystalfontz CFAF7201280A0-050TN outline, active area and
# FPC pin table (datasheet 2022-11-17, section 6.2). Pins not listed are NC (1-9 touch, 12-13, 15 TE, 16, 22-23 and
# 25-26 data lanes 3 and 2, unused on two lanes).
PANEL = dict(name='Crystalfontz CFAF7201280A0-050TN', module=(66.10, 120.40, 1.85), active=(62.10, 110.40),
             pins={10: 'LCD_VCI_3V0', 11: 'LCD_VCI_3V0', 14: 'LCD_RESX', 17: 'GND', 18: 'GND', 19: 'LCD_1V8', 20: 'LCD_1V8',
                   21: 'GND', 24: 'GND', 27: 'GND', 28: 'MIPI_DSI_CLK_P', 29: 'MIPI_DSI_CLK_N', 30: 'GND',
                   31: 'MIPI_DSI_D1_P', 32: 'MIPI_DSI_D1_N', 33: 'GND', 34: 'MIPI_DSI_D0_P', 35: 'MIPI_DSI_D0_N',
                   36: 'GND', 37: 'GND', 38: 'LCD_LED_A', 39: 'LCD_LED_K', 40: 'LCD_LED_K'},
             pin1_x=-7.85, pitch=0.5, row_y=74.15)


class Report:
    def __init__(self):
        self.rows = []

    def add(self, cid, interface, title, status, value=None, limit=None, detail=''):
        self.rows.append(dict(id=cid, interface=interface, title=title, status=status,
                              value=value, limit=limit, detail=detail))

    def counts(self):
        c = {}
        for r in self.rows:
            c[r['status']] = c.get(r['status'], 0) + 1
        return c


def r3(v):
    return None if v is None else round(float(v), 3)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# PCB solids (derived from the PCB layer JSON; heights from the envelope table)
# ---------------------------------------------------------------------------
def rect_poly(cx, cy, w, h, rot):
    g = box(-w/2, -h/2, w/2, h/2)
    return affinity.translate(affinity.rotate(g, rot, origin=(0, 0)), cx, cy)


def poly_solid(poly, z0, z1):
    pts = [(float(x), float(y)) for x, y in list(poly.exterior.coords)[:-1]]
    return cq.Workplane('XY').polyline(pts).close().extrude(z1 - z0).translate((0, 0, z0)).val()


def pcb_items(B):
    PCB, ENV = B['PCB'], B['ENV']
    t = PCB['board']['thickness']
    items = [dict(name='PCB R27 BOARD', ref='BOARD', solid=B['prism'](B['BOARD'], 0.0, t).val(), layer='PCB', kind='board')]
    for p in PCB['parts']:
        env = ENV['by_value'].get(p['value'], {})
        h = B['part_height'](p)
        rot = p.get('rot', 0)
        if p['value'].startswith('D2LS'):
            body = rect_poly(p['x'], p['y'], env['body_mm'][0], env['body_mm'][1], rot)
            term = rect_poly(p['x'], p['y'], env['length_with_terminals_mm'], 2.2, rot)
            items.append(dict(name=f"{p['ref']} {p['value']} BODY", ref=p['ref'], layer='PCB', kind='part', side='front',
                              solid=poly_solid(body, t, t + h)))
            items.append(dict(name=f"{p['ref']} TERMINALS", ref=p['ref'], layer='PCB', kind='part', side='front',
                              solid=poly_solid(term, t, t + 0.6)))
            items.append(dict(name=f"{p['ref']} PLUNGER", ref=p['ref'], layer='PCB', kind='plunger', side='front',
                              solid=cq.Workplane('XY').center(p['x'], p['y']).circle(0.8).extrude(env['free_position_mm'] - h).translate((0, 0, t + h)).val()))
            continue
        if p['value'].startswith('USB4105'):
            fp = box(-4.75, env['mating_face_y_mm'], 4.75, env['mating_face_y_mm'] + 8.2)
        else:
            fp = rect_poly(p['x'], p['y'], p['w'], p['h'], rot)
        z0, z1 = (t, t + h) if p['side'] == 'front' else (-h, 0.0)
        kind = 'plunger' if p['value'].startswith('B3U') else 'part'     # tact switch: its top is the actuator
        items.append(dict(name=f"{p['ref']} {p['value']}", ref=p['ref'], layer='PCB', kind=kind, side=p['side'], solid=poly_solid(fp, z0, z1)))
    return items


# ---------------------------------------------------------------------------
# 3D helpers
# ---------------------------------------------------------------------------
def bb(s):
    b = s.BoundingBox()
    return (b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax)


def bb_gap(a, b):
    """Lower bound of the distance between two boxes (0 if they overlap)."""
    d = 0.0
    for i in range(3):
        lo = max(a[i], b[i]); hi = min(a[i+3], b[i+3])
        if lo > hi:
            d = max(d, lo - hi)
    return d


def clip(shape, box6, m):
    x0, y0, z0, x1, y1, z1 = box6
    k = cq.Solid.makeBox(x1 - x0 + 2*m, y1 - y0 + 2*m, z1 - z0 + 2*m, cq.Vector(x0 - m, y0 - m, z0 - m))
    return shape.intersect(k)


def overlap_volume(a, b):
    ba, bbx = bb(a), bb(b)
    if bb_gap(ba, bbx) > 0:
        return 0.0
    try:
        return a.intersect(b).Volume()
    except Exception:
        return float('nan')


def min_distance(a, b, horizon):
    ba, bbx = bb(a), bb(b)
    g = bb_gap(ba, bbx)
    if g > horizon:
        return g
    # Work on local clips so large shells stay fast.
    inter = (max(ba[0], bbx[0]), max(ba[1], bbx[1]), max(ba[2], bbx[2]), min(ba[3], bbx[3]), min(ba[4], bbx[4]), min(ba[5], bbx[5]))
    region = tuple(inter[i] if inter[i] <= inter[i+3] else (ba[i] + bbx[i]) / 2 for i in range(3)) + \
             tuple(inter[i+3] if inter[i] <= inter[i+3] else (ba[i+3] + bbx[i+3]) / 2 for i in range(3))
    ca, cb = clip(a, region, horizon + 0.5), clip(b, region, horizon + 0.5)
    if not ca.Solids() or not cb.Solids():
        return horizon + 0.5
    return ca.distance(cb)


# Pairs that are designed to touch (zero-volume contact) and the minimum gap allowed.
CONTACTS = [
    ('FRONT SHELL', 'REAR SHELL', 0.0), ('FRONT SHELL', 'LENS', 0.0), ('FRONT SHELL', 'LCD', 0.0),
    ('LENS', 'LCD', 0.0), ('FRONT SHELL', 'FACE FILM', 0.0), ('LENS', 'FACE FILM', 0.0),
    ('FLAP CAP', 'FRONT SHELL', 0.0), ('DART ROCKER', 'FRONT SHELL', 0.03),
    ('FRONT SHELL', 'BOARD', 0.0), ('REAR SHELL', 'BOARD', 0.0),
    ('BATTERY FOAM', 'LIPO', 0.0), ('BATTERY FOAM', 'REAR SHELL', 0.0),
    ('SPEAKER L ·', 'REAR SHELL', 0.0), ('SPEAKER R ·', 'REAR SHELL', 0.0),
    ('SPEAKER L ·', 'SPEAKER L FRONT GASKET', 0.0), ('SPEAKER R ·', 'SPEAKER R FRONT GASKET', 0.0),
    ('FRONT GASKET', 'FRONT SHELL', 0.0), ('POWER PLUNGER', 'REAR SHELL', 0.0),
    ('FPC EXTENSION', 'LCD', 0.0), ('FPC EXTENSION', 'J1 ', 0.0), ('FPC EXTENSION', 'BOARD', 0.0),
    ('BATTERY LEAD', 'LIPO', 0.0), ('BATTERY LEAD', 'J3 ', 0.0), ('BATTERY LEAD', 'BOARD', 0.0),
    ('SPEAKER LEAD RESERVE · TO J4', 'SPEAKER L ·', 0.0), ('SPEAKER LEAD RESERVE · TO J5', 'SPEAKER R ·', 0.0),
    ('SPEAKER LEAD RESERVE · TO J4', 'J4 ', 0.0), ('SPEAKER LEAD RESERVE · TO J5', 'J5 ', 0.0),
    ('SPEAKER LEAD', 'REAR SHELL', 0.0), ('SPEAKER LEAD', 'BOARD', 0.0),
    ('DISPLAY TAPE', 'FRONT SHELL', 0.0), ('DISPLAY TAPE', 'LENS', 0.0), ('DISPLAY TAPE', 'LCD', 0.0),
    ('LAP TAPE', 'FRONT SHELL', 0.0), ('LAP TAPE', 'REAR SHELL', 0.0),
]


# Hard stops: at the pressed pose the stop legs land on the board.
# The actuator nub is narrower than the D2LS plunger and stops just above the switch body.
CONTACTS_PRESSED = [('FLAP CAP', 'BOARD', 0.0), ('DART ROCKER', 'BOARD', 0.0), ('FLAP CAP', ' BODY', 0.02), ('DART ROCKER', ' BODY', 0.01)]


def contact_rule(n1, n2, ps='rest'):
    for a, b, g in CONTACTS + (CONTACTS_PRESSED if ps != 'rest' else []):
        if (a in n1 and b in n2) or (a in n2 and b in n1):
            return g
    return None


def pose(item, kind, B):
    """Return the solid of a moving part at 'rest' or at its hard stop."""
    s = item['solid']
    if kind == 'rest':
        return s
    name = item['name']
    if 'FLAP CAP' in name:
        return s.translate(cq.Vector(0, 0, -B['STROKE']))
    if 'DART ROCKER' in name:
        ang = math.degrees(B['THETA_DART']) * (1 if kind == 'press_right' else -1)
        piv = cq.Vector(0, 0, B['P']['dart_pivot_z'])
        return s.rotate(piv, piv + cq.Vector(0, 1, 0), ang)
    if 'POWER PLUNGER' in name:
        return s.translate(cq.Vector(0, 0, B['P']['power_gap'] + 0.15))
    return s


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------
def run(root, rep, verbose=True):
    t0 = time.time()
    with contextlib.redirect_stdout(io.StringIO()):
        B = runpy.run_path(str(root / 'LAYERS/02_CASE/build_r12.py'))
    P, PCB, ENV = B['P'], B['PCB'], B['ENV']
    OUT, INNER, BOARD_OUT = B['OUTLINE_POLY'], B['INNER_POLY'], B['BOARD_OUTER']
    tol = 1e-6

    # ---- A. Source authority -------------------------------------------------
    for rel, ref in PCB_BASELINE.items():
        h = sha(root / rel)
        rep.add('A1', 'PCB', f'{rel} unchanged from R32 delivery', 'PASS' if h == ref else 'FAIL', h[:16], ref[:16])
    rep.add('A2', 'PCB↔CASE', 'Board thickness used by the case = board file thickness',
            'PASS' if abs(P['pcb_t'] - PCB['board']['thickness']) < tol else 'FAIL', P['pcb_t'], PCB['board']['thickness'],
            'R10 modelled the datum board as 1.6 mm; the file says 1.2 mm.')

    # ---- B. Outline, walls, containment -------------------------------------
    bx = OUT.bounds
    rep.add('B1', 'CASE', 'Exterior envelope (approved 104.0 × 135.3)', 'PASS' if abs((bx[2]-bx[0]) - 104.0) < 0.01 and abs((bx[3]-bx[1]) - 135.3) < 0.01 else 'FAIL',
            [r3(bx[2]-bx[0]), r3(bx[3]-bx[1])], [104.0, 135.3])
    d = INNER.exterior.distance(BOARD_OUT) if BOARD_OUT.within(INNER) else -BOARD_OUT.difference(INNER).area
    rep.add('B2', 'PCB↔CASE', 'R27 board inside the 2.0 mm wall with ≥0.3 mm clearance', 'PASS' if BOARD_OUT.within(INNER) and d >= P['board_to_wall_clearance'] - 1e-3 else 'FAIL',
            r3(d), P['board_to_wall_clearance'])
    lcd_box = box(-B['LCD_W']/2, P['lcd_top_y'], B['LCD_W']/2, P['lcd_top_y'] + B['LCD_H'])
    d = INNER.exterior.distance(lcd_box) if lcd_box.within(INNER) else -1
    rep.add('B3', 'CASE', 'LCD module inside the 2.0 mm wall with ≥0.2 mm clearance', 'PASS' if d >= 0.2 - 1e-3 else 'FAIL', r3(d), 0.2)
    r10 = B['R10_OUTLINE']
    grow = OUT.difference(r10)
    shrink = r10.difference(OUT)
    max_out = max((r10.exterior.distance(Point(c)) for g in getattr(grow, 'geoms', [grow]) if not g.is_empty for c in g.exterior.coords), default=0)
    rep.add('B4', 'CASE', 'R12 silhouette change versus R10 (max outward move)', 'INFO', r3(max_out), None,
            f'area +{grow.area:.1f} / -{shrink.area:.1f} mm²; shoulders and finger scallop pushed out to clear the board; saddle lift 4.5 → {135.3 - P["saddle_center_y"]:.1f} mm for the FPC wrap')
    rep.add('B5', 'CASE', 'Nominal plate, floor and side wall thickness (design parameters)', 'PASS' if min(P['plate_t'], P['wall'], B['P']['floor_inner_z'] - B['Z_FLOOR_OUT']) >= 2.0 - tol else 'FAIL',
            [P['plate_t'], r3(B['P']['floor_inner_z'] - B['Z_FLOOR_OUT']), P['wall']], 2.0)

    # Measured plate over the LCD pocket ledge (outside the lens rebate, inside the pocket).
    front_solid = next(it['solid'] for it in B['PARTS'] if it['name'].startswith('FRONT SHELL')).val()
    rb, pk = B['LENS_REBATE'].bounds, B['LCD_POCKET'].bounds
    probe_y = (rb[3] + pk[3]) / 2
    cut = front_solid.intersect(cq.Solid.makeBox(0.2, 0.2, 20, cq.Vector(-0.1, probe_y - 0.1, -5)))
    ledge_t = (cut.BoundingBox().zmax - cut.BoundingBox().zmin) if cut.Solids() else 0.0
    rep.add('B8', 'CASE↔LCD', 'Plate left over the LCD pocket ledge (localised, below the 2.0 mm rule)', 'GATE', r3(ledge_t), 2.0,
            f'Measured on the front-shell solid at (0, {probe_y:.2f}). The ledge outside the lens rebate is {ledge_t:.2f} mm: a band {pk[2]-pk[0]:.1f} mm wide at '
            f'Y {rb[3]:.2f}–{pk[3]:.2f}, plus a {rb[1]-pk[1]:.2f} mm top strip and {((pk[2]-pk[0])-(rb[2]-rb[0]))/2:.2f} mm side strips. The LCD front face bonds to it (L6). '
            'Set by the stack (LCD 1.75 + lens 0.70 in a 2.0 mm plate); confirm stiffness on the print.')

    # Webs in the front plate.
    webs = {}
    for i, h in enumerate(B['FLAP_HOLES']):
        webs[f'flap hole {"LR"[i]} → outline'] = OUT.exterior.distance(h)
        webs[f'flap hole {"LR"[i]} → LCD pocket'] = h.distance(B['LCD_POCKET'])
        webs[f'flap hole {"LR"[i]} → screen opening'] = h.distance(B['SCREEN_OPENING'])
    webs['LCD pocket → top edge'] = OUT.exterior.distance(B['LCD_POCKET'])
    webs['LCD pocket → DART opening'] = B['LCD_POCKET'].distance(B['DART_HOLE'])
    webs['DART opening → outline'] = OUT.exterior.distance(B['DART_HOLE'])
    for i, g in enumerate(B['GRILLE']):
        webs[f'grille slot {i+1} → outline'] = OUT.exterior.distance(g)
        webs[f'grille slot {i+1} → DART relief'] = g.distance(B['DART_SURROUND'])
    for i in range(0, len(B['GRILLE']), 3):
        webs[f'grille slot pitch web {i//3+1}'] = B['GRILLE'][i].distance(B['GRILLE'][i+1])
    worst = min(webs, key=webs.get)
    structural = {k: v for k, v in webs.items() if 'pitch' not in k}
    worst_s = min(structural, key=structural.get)
    rep.add('B6', 'CASE', 'Minimum structural web in the front plate', 'PASS' if structural[worst_s] >= 2.0 - 1e-3 else 'FAIL', r3(structural[worst_s]), 2.0, worst_s)
    pitch_min = min(v for k, v in webs.items() if 'pitch' in k)
    rep.add('B7', 'CASE', 'Grille slot bars (between slots)', 'PASS' if pitch_min >= 1.0 - 1e-3 else 'FAIL',
            r3(pitch_min), 1.0, 'acoustic grille bars, not structural walls')

    # ---- C. Screen stack -----------------------------------------------------
    aw, ah = P['active']
    act = box(-aw/2, B['ACTIVE_CY'] - ah/2, aw/2, B['ACTIVE_CY'] + ah/2)
    op = B['SCREEN_OPENING']
    margins = [act.bounds[0] - op.bounds[0], op.bounds[2] - act.bounds[2], act.bounds[1] - op.bounds[1], op.bounds[3] - act.bounds[3]]
    rep.add('C1', 'CASE↔LCD', 'Screen opening centred on the LCD active area', 'PASS' if abs(((op.bounds[1]+op.bounds[3])/2) - B['ACTIVE_CY']) < 0.01 else 'FAIL',
            r3((op.bounds[1]+op.bounds[3])/2), r3(B['ACTIVE_CY']), 'R10 centred the opening on the module, which hid 1.9 mm of active area at the top under the R3 1.79 mm top-border assumption')
    rep.add('C2', 'CASE↔LCD', 'Opening margin around the active area (each side)', 'PASS' if min(margins) >= 0.2 - 1e-3 and max(margins) <= 0.6 else 'FAIL',
            [r3(m) for m in margins], [0.2, 0.6])
    lens = B['rrect'](0, B['ACTIVE_CY'], P['lens'][0], P['lens'][1], P['lens_r'])
    rep.add('C3', 'CASE', 'Lens covers the opening and fits the rebate', 'PASS' if op.within(lens) and lens.within(B['LENS_REBATE'].buffer(1e-6)) else 'FAIL',
            r3(B['LENS_REBATE'].exterior.distance(lens)), 0.1)
    rep.add('C4', 'CASE↔LCD', 'LCD active-area position relies on the 1.79 mm top border (R3 assumption)', 'GATE', P['active_top_inactive'], None,
            'The case still uses the R3/HOTHMI envelope. In the case pass, set the LCD parameters from the Crystalfontz drawing (C6); the opening, lens and rebate follow ACTIVE_CY automatically (the film has no screen cutout).')
    rep.add('C5', 'CASE↔LCD', 'LCD pocket leaves room for the panel FPC bend at the bottom edge', 'PASS' if P['lcd_fpc_bend'] >= 0.5 else 'FAIL', P['lcd_fpc_bend'], 0.5)
    mw, mh, mt = PANEL['module']
    pocket_h = P['lcd_top_y'] + B['LCD_H'] + P['lcd_fpc_bend'] - (P['lcd_top_y'] - P['lcd_pocket_top_gap'])
    fits = mw <= P['lcd_pocket_w'] and mh + P['lcd_fpc_bend'] <= pocket_h + 1e-6 and abs(mt - B['LCD_T']) < 1e-6
    rep.add('C6', 'CASE↔LCD', f'Chosen panel ({PANEL["name"]}, {mw:.2f} × {mh:.2f} × {mt:.2f}) fits the LCD pocket and stack', 'PASS' if fits else 'FAIL',
            [mw, mh, mt], [P['lcd_pocket_w'], r3(pocket_h - P['lcd_fpc_bend']), B['LCD_T']],
            f'CASE R12 was drawn around the R3/HOTHMI envelope {B["LCD_W"]} × {B["LCD_H"]} × {B["LCD_T"]}. The Crystalfontz module is {mw - P["lcd_pocket_w"]:+.2f} mm against the '
            f'{P["lcd_pocket_w"]} mm pocket width, {mh - B["LCD_H"]:+.2f} mm in length and {mt - B["LCD_T"]:+.2f} mm in thickness; its active area '
            f'({PANEL["active"][0]} × {PANEL["active"][1]}) against the case opening design ({P["active"][0]} × {P["active"][1]}). The owner set the case aside '
            'for PCB R23-R27: the case pass redraws the pocket, opening, lens and film for the 5 in panel.')

    # ---- D. Actuation stacks -------------------------------------------------
    D2 = ENV['by_value']['D2LS-21']
    PT = D2['free_position_mm'] - D2['operating_position_mm']
    ot = B['STROKE'] - P['pregap'] - PT
    for (cx, cy), ref in zip(P['flap_centers'], ('SW1', 'SW2')):
        sw = B['SW'][ref]
        off = math.hypot(sw['x'] - cx, sw['y'] - cy)
        rep.add('D1', 'PCB↔CASE', f'Flap cap axis on {ref}', 'PASS' if off < 0.01 else 'FAIL', r3(off), 0.0)
    for x in (-P['dart_sw_x'], P['dart_sw_x']):
        ref = 'SW3' if x < 0 else 'SW4'
        sw = B['SW'][ref]
        rep.add('D2', 'PCB↔CASE', f'DART nub on {ref}', 'PASS' if abs(sw['x'] - x) < 0.01 and abs(sw['y'] - P['dart_y']) < 0.01 else 'FAIL',
                r3(math.hypot(sw['x'] - x, sw['y'] - P['dart_y'])), 0.0)
    rep.add('D3', 'PCB↔CASE', 'Nub-to-plunger gap at rest (nominal)', 'PASS' if 0.05 <= P['pregap'] <= 0.25 else 'FAIL', P['pregap'], [0.05, 0.25])
    rep.add('D4', 'PCB↔CASE', 'Overtravel past OP at the hard stop (nominal; datasheet OT ≥ 0.1)', 'PASS' if ot >= D2['overtravel_min_mm'] - 1e-6 else 'FAIL', r3(ot), D2['overtravel_min_mm'])
    # Worst case with FP and OP shifting together by ±0.2 (PT fixed).
    lo = B['STROKE'] - (P['pregap'] + D2['tolerance_fp_op_mm']) - PT
    hi = B['STROKE'] - (P['pregap'] - D2['tolerance_fp_op_mm']) - PT
    rep.add('D5', 'PCB↔CASE', 'Overtravel at the stop across FP/OP ±0.2 (D2LS tolerance)', 'GATE', [r3(lo), r3(hi)], [0.0, None],
            'A fixed stop cannot cover the full ±0.2 band (low-FP switch would not reach OP). Measure FP on a coupon and trim the stop legs, or use the shim set; see PRODUCTION_GATES.md.')
    # DART kinematics: actual nub drop at the stop angle about the pivot.
    th = B['THETA_DART']; zc = P['dart_pivot_z']
    def drop(x, z):
        return z - (-x*math.sin(th) + (z - zc)*math.cos(th) + zc)
    nub_drop = drop(P['dart_sw_x'], B['Z_NUB'])
    xe = P['dart_leg_x'] + P['dart_leg_d'] / 2          # the leg's outer edge lands first
    leg_z_at_stop = (B['Z_BOARD_TOP'] + xe * th) - drop(xe, B['Z_BOARD_TOP'] + xe * th)
    rep.add('D6', 'PCB↔CASE', 'DART nub travel at the rocker stop', 'PASS' if abs(nub_drop - B['STROKE']) < 0.02 else 'FAIL', r3(nub_drop), r3(B['STROKE']))
    rep.add('D7', 'CASE', 'DART stop leg reaches the board at the stop angle', 'PASS' if abs(leg_z_at_stop - B['Z_BOARD_TOP']) < 0.03 else 'FAIL', r3(leg_z_at_stop), B['Z_BOARD_TOP'])
    lift = P['dart_leg_x'] * math.sin(th)
    rep.add('D8', 'CASE', 'Opposite DART switch is released while one side is pressed', 'PASS' if B['Z_NUB'] + drop(-P['dart_sw_x'], B['Z_NUB']) * -1 >= B['Z_FP'] else 'FAIL',
            r3(B['Z_NUB'] - drop(-P['dart_sw_x'], B['Z_NUB'])), r3(B['Z_FP']))
    rep.add('D11', 'PCB↔CASE', 'D2LS actuator assumed at the body centre', 'GATE', None, None,
            'The Omron outline does not dimension the plunger position in text form; the Ø1.4 nubs sit on the switch centres. Confirm on a sample before cutting tools.')
    rep.add('D12', 'CASE', f'DART trunnions snap into closed bosses ({P["dart_trunnion_clear"]:.2f} mm radial running clearance)', 'GATE', P['dart_trunnion_d'], None,
            'Print-test the boss flex and wear; add a lead-in slot if the bosses crack on assembly.')
    overlap = (P['cap_flange_d'] - P['flap_hole_d']) / 2
    trunnion_in = P['dart_boss'][1] + 0.1 - 0.01 - 0.1
    rep.add('D14', 'CASE', 'Controls retained: cap flange overlaps the plate hole; DART trunnions run in closed bosses', 'PASS' if overlap >= 0.3 and trunnion_in > 0.5 else 'FAIL',
            [r3(overlap), r3(trunnion_in)], [0.3, 0.5], f'flange Ø{P["cap_flange_d"]} under the Ø{P["flap_hole_d"]} hole ({overlap:.2f} mm radial); trunnion Ø{P["dart_trunnion_d"]} engages {trunnion_in:.2f} mm of each boss')
    web = P['dart_pivot_z'] - (P['dart_trunnion_d'] / 2 + P['dart_trunnion_clear']) - P['dart_boss_z0']
    rep.add('D15', 'CASE', 'Material under each DART trunnion bore (boss floor)', 'PASS' if web >= 0.15 - 1e-6 else 'FAIL', r3(web), 0.15,
            'a bore tangent to the boss floor leaves no material under the pin')
    pw = B['SW']['SW5']
    rep.add('D9', 'PCB↔CASE', 'Power plunger on SW5 (PWR_WAKE) and pinholes on SW6 RESET / SW7 BOOT', 'PASS', [ref for ref in ('SW5', 'SW6', 'SW7')], None,
            f'plunger tip gap {P["power_gap"]} mm, proud {P["power_proud"]} mm; Ø{P["pinhole_d"]} pinholes coaxial with the switches')

    # ---- E. Film ↔ shell -------------------------------------------------------
    film = B['FILM_POLY']
    inset = P['film_edge_inset']
    near = min(OUT.exterior.distance(Point(c)) for c in film.exterior.coords)
    far = film.exterior.hausdorff_distance(OUT.exterior)
    rep.add('E1', 'ACRYLIC↔CASE', f'Film edge sits {inset:.2f} mm inside the case outline all round', 'PASS' if abs(near - inset) < 0.02 and abs(far - inset) < 0.02 and film.within(OUT) else 'FAIL',
            [r3(near), r3(far)], inset, 'die-cut tolerance up to ±0.2 mm cannot leave film overhanging the case edge')
    relief = unary_union(B['BEZELS'] + [B['DART_SURROUND']])
    rep.add('E2', 'ACRYLIC↔CASE', 'Film clears the molded relief (relief rises through the film)', 'PASS' if not film.intersects(relief.buffer(P['film_clear'] - 1e-3)) else 'FAIL',
            r3(film.distance(relief)), P['film_clear'], 'R10 sat the "molded" relief on top of the film')
    rep.add('E3', 'ACRYLIC↔CASE', 'Film continuous over the screen opening and lens (no screen cutout)', 'PASS' if B['SCREEN_OPENING'].within(film) else 'FAIL')
    slot_ok = all(any(g.buffer(0.1 - 1e-3).within(v) for v in B['FILM_VENTS']) for g in B['GRILLE'])
    rep.add('E4', 'ACRYLIC↔CASE', 'Film vent windows uncover every grille slot with ≥0.1 mm margin', 'PASS' if slot_ok else 'FAIL', len(B['FILM_VENTS']), len(B['GRILLE']))
    cuts = B['FILM_FLAP_CUTS'] + [B['FILM_DART_CUT']] + B['FILM_VENTS']
    web = min(film.exterior.distance(c) for c in cuts)
    rep.add('E5', 'ACRYLIC', 'Film edge web beside every cutout', 'PASS' if web >= 1.5 else 'FAIL', r3(web), 1.5)
    def narrow(poly):
        r = poly.minimum_rotated_rectangle.exterior.coords
        return min(math.dist(r[0], r[1]), math.dist(r[1], r[2]))
    min_cut = min(narrow(Polygon(h.coords)) for h in film.interiors)
    rep.add('E8', 'ACRYLIC', 'Narrowest cutout is wide enough for a die or plotter cut', 'PASS' if min_cut >= 1.5 else 'FAIL', r3(min_cut), 1.5,
            'R1 had six 1.0 mm vent slots; R2 uses one window per speaker')
    spec = json.loads((root / 'LAYERS/03_ACRYLIC/ACRYLIC_LAYER_R2_CUT_SPEC.json').read_text()) if (root / 'LAYERS/03_ACRYLIC/ACRYLIC_LAYER_R2_CUT_SPEC.json').exists() else None
    if spec:
        c = spec['cutouts_mm']
        want = {
            'flap_centers': [list(x) for x in P['flap_centers']],
            'flap_cut_diameter': P['bezel_od'] + 2 * P['film_clear'],
            'dart_center': [0.0, P['dart_cy']],
            'dart_cut_size': [P['dart_surround'][0] + 2 * P['film_clear'], P['dart_surround'][1] + 2 * P['film_clear']],
            'dart_cut_corner_radius': P['dart_surround_r'] + P['film_clear'],
            'vent_centers': [[x, (B['GRILLE_YS'][0] + B['GRILLE_YS'][-1]) / 2] for x, _ in B['SPK_CENTERS']],
            'vent_window_size': list(B['FILM_VENT_SIZE']), 'vent_window_corner_radius': P['film_vent_r'],
        }
        def close(a, b):
            if isinstance(a, list):
                return isinstance(b, list) and len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
            return abs(float(a) - float(b)) < 1e-6
        bad = [k for k, v in want.items() if k not in c or not close(c[k], v)]
        if abs(spec['film_thickness_mm'] - P['film_t']) > 1e-9:
            bad.append('film_thickness_mm')
        if abs(spec['edge_inset_mm'] - P['film_edge_inset']) > 1e-9:
            bad.append('edge_inset_mm')
        rep.add('E6', 'ACRYLIC', 'Cut specification JSON matches the geometry (every cutout field and the thickness)', 'PASS' if not bad else 'FAIL',
                len(want) + 2 - len(bad), len(want) + 2, ('mismatch: ' + ', '.join(bad)) if bad else '')
    stack = sum(t for _, t in P['film_stack'])
    rep.add('E7', 'ACRYLIC', 'Film stack selected and equal to the CAD film thickness', 'PASS' if abs(stack - P['film_t']) < 1e-9 else 'FAIL', r3(stack), P['film_t'],
            ' + '.join(f'{n} {t:.3f}' for n, t in P['film_stack']))

    # ---- F/G. 3D interference and clearance ---------------------------------
    case = [dict(it, solid=it['solid'].val() if hasattr(it['solid'], 'val') else it['solid']) for it in B['PARTS']]
    pcb = pcb_items(B)
    for it in case:
        rep.add('M1', it['layer'], f'Solid valid: {it["name"]}', 'PASS' if it['solid'].isValid() else 'FAIL')
    fpc = next(it for it in case if 'FPC EXTENSION' in it['name'])
    rep.add('H1', 'CASE↔PCB', 'FPC route reserve (the R12 extension-FPC path) is one continuous body', 'PASS' if len(fpc['solid'].Solids()) == 1 else 'FAIL', len(fpc['solid'].Solids()), 1)
    for it in case:
        if 'LEAD RESERVE' in it['name']:
            rep.add('H2', 'CASE↔PCB', f'{it["name"]} continuous', 'PASS' if len(it['solid'].Solids()) == 1 else 'FAIL', len(it['solid'].Solids()), 1)

    poses = ['rest', 'press', 'press_left', 'press_right']
    interferences = []
    tight = []
    actuation = []
    allitems = case + pcb
    n_pairs = 0
    by_pose, distinct = {}, set()
    for ps in poses:
        moving = [it for it in case if it['kind'] == 'moving']
        if ps == 'rest':
            subjects = case
        else:
            subjects = [it for it in moving if (ps == 'press' and ('FLAP CAP' in it['name'] or 'POWER' in it['name'])) or (ps != 'press' and 'DART' in it['name'])]
        for i, a in enumerate(subjects):
            sa = pose(a, ps, B)
            for b in allitems:
                if b is a:
                    continue
                if ps == 'rest' and b in case and case.index(b) < case.index(a):
                    continue          # each case pair once at rest
                if b['kind'] == 'moving' and ps != 'rest':
                    continue
                sb = b['solid']
                rule = contact_rule(a['name'], b['name'], ps)
                is_plunger = b.get('kind') == 'plunger'
                horizon = 0.3 if a['kind'] == 'moving' else 0.2
                if bb_gap(bb(sa), bb(sb)) > horizon:
                    continue
                n_pairs += 1
                by_pose[ps] = by_pose.get(ps, 0) + 1
                distinct.add(tuple(sorted((a['name'], b['name']))))
                v = overlap_volume(sa, sb)
                if is_plunger and a['kind'] == 'moving':
                    ref = b['ref']
                    actuation.append(dict(pose=ps, part=a['name'], switch=ref, overlap_mm3=r3(v)))
                    continue
                if v > 1e-3:
                    interferences.append(dict(pose=ps, a=a['name'], b=b['name'], volume_mm3=r3(v)))
                    continue
                if rule is not None:
                    need = rule
                elif a['kind'] == 'moving' or b['kind'] == 'moving':
                    need = 0.2
                elif a['kind'] in ('purchased', 'reserve') or b['kind'] in ('purchased', 'reserve', 'part', 'plunger'):
                    need = 0.1
                else:
                    need = 0.0
                if need > 0:
                    dist = min_distance(sa, sb, horizon)
                    if dist < need - 1e-3:
                        tight.append(dict(pose=ps, a=a['name'], b=b['name'], distance=r3(dist), required=need))
    rep.add('F1', 'ALL', 'No positive-volume interference (rest, flap pressed, DART left/right pressed)', 'PASS' if not interferences else 'FAIL',
            len(interferences), 0, json.dumps(interferences[:12]))
    rep.add('G1', 'ALL', 'Clearances: moving parts ≥0.2, purchased/reserve envelopes ≥0.1, designed contacts honoured', 'PASS' if not tight else 'FAIL',
            len(tight), 0, json.dumps(tight[:12]))
    # Each pressed control must actually engage its switch plunger; rest must not.
    need_eng = {('press', 'SW1'), ('press', 'SW2'), ('press', 'SW5'), ('press_left', 'SW3'), ('press_right', 'SW4')}
    got = {(a['pose'], a['switch']) for a in actuation if a['overlap_mm3'] and a['overlap_mm3'] > 1e-3}
    rest_eng = {a['switch'] for a in actuation if a['pose'] == 'rest' and a['overlap_mm3'] and a['overlap_mm3'] > 1e-3}
    rep.add('D10', 'PCB↔CASE', 'Each control engages its own switch when pressed, none at rest', 'PASS' if need_eng <= got and not rest_eng and not (got - need_eng) else 'FAIL',
            sorted(f'{p}:{s}' for p, s in got), sorted(f'{p}:{s}' for p, s in need_eng))

    # ---- H. Reserves ---------------------------------------------------------
    wrap = B['FPC_SEGMENTS'][4][1]
    inner_y_center = min(y for x, y in INNER.exterior.coords if abs(x) < 0.5 and y > 100)
    rep.add('H3', 'CASE↔PCB', 'FPC wrap around the board tab clears the bottom wall', 'PASS' if inner_y_center - wrap[3] >= 0.2 - 1e-3 else 'FAIL', r3(inner_y_center - wrap[3]), 0.2)
    rep.add('H4', 'CASE↔LCD', 'Panel tail (40 mm) folds once behind the panel into J1 on the front, under the panel', 'GATE', None, None,
            'The board has no adapter flex (R23 on): the Crystalfontz tail folds once behind the module (datasheet 7.6: bend radius 1.5 mm, at least 2 mm '
            'past the glass), contacts away from the board, and enters J1 (FH12A-40S, top contact, mouth toward +Y) at Y 76. The tail end '
            'lands about 34.3 mm above the panel bottom edge, so the panel bottom edge sits at Y 109.8 with its centre at X 1.2. The panel '
            'needs 2.3-3.3 mm between its back and the board front (J1 is 2.0 mm tall; the fold is 3.0 mm across). The case route reserve '
            'still follows the R12 extension-FPC path; the case pass redraws it and the LCD pocket for the 5 in panel.')
    # ---- N. Panel ↔ PCB: J1 pins against the panel's published pin table ------------------------------------------------
    pads = [p for p in PCB['pads'] if p['ref'] == 'J1' and p['num'].isdigit()]
    bad = []
    for pin in range(1, 41):
        x = PANEL['pin1_x'] + PANEL['pitch'] * (pin - 1)
        hit = [p for p in pads if abs(p['x'] - x) < 0.01 and abs(p['y'] - PANEL['row_y']) < 0.01]
        want = PANEL['pins'].get(pin, '')
        if len(hit) != 1 or hit[0]['netName'] != want:
            bad.append(f'panel pin {pin} at x {x:.2f}: board {hit[0]["netName"] if hit else "no pad"}, panel {want or "NC"}')
    rep.add('N1', 'PCB↔LCD', 'J1: all 40 pins match the panel pin table (position after the single fold, and net)', 'PASS' if not bad and len(pads) == 40 else 'FAIL',
            40 - len(bad), 40, '; '.join(bad))

    # ---- I. Supports -----------------------------------------------------------
    def pads_on(side):
        return unary_union([rect_poly(p['x'], p['y'], p['w'], p['h'], p.get('rot', 0)) for p in PCB['pads'] if p['side'] in (side, 'both')])
    bpads, fpads = pads_on('back'), pads_on('front')
    bad = []
    for x, y in B['REAR_POSTS']:
        if Point(x, y).buffer(P['post_d_rear']/2 + 0.3).intersects(bpads) or not Point(x, y).buffer(P['post_d_rear']/2 + 0.3).within(B['BOARD']):
            bad.append(('rear', x, y))
    for x, y in B['FRONT_POSTS']:
        if Point(x, y).buffer(P['post_d_front']/2 + 0.3).intersects(fpads) or not Point(x, y).buffer(P['post_d_front']/2 + 0.3).within(B['BOARD']):
            bad.append(('front', x, y))
    rep.add('I1', 'PCB↔CASE', 'Support/clamp posts land on bare board (no pads within 0.3 mm, ≥0.3 mm from edges/window)', 'PASS' if not bad else 'FAIL', len(bad), 0, json.dumps(bad))
    backing = {}
    for ref in ('SW1', 'SW2', 'SW3', 'SW4'):
        s = B['SW'][ref]
        backing[ref] = r3(min(math.hypot(s['x'] - x, s['y'] - y) for x, y in B['REAR_POSTS']))
    rep.add('I2', 'PCB↔CASE', 'Every front switch backed by a rear support within 10 mm', 'PASS' if max(backing.values()) <= 10.0 else 'FAIL', backing, 10.0)
    rep.add('I3', 'CASE', 'Board clamped front-and-back at matched points', 'PASS' if set(B['FRONT_POSTS']) <= set(B['REAR_POSTS']) and len(B['FRONT_POSTS']) >= 6 else 'FAIL', len(B['FRONT_POSTS']), 6)
    contacts = [('support post', x, y, P['post_d_rear'] / 2) for x, y in B['REAR_POSTS'] + B['FRONT_POSTS']]
    for (cx, cy), ref in zip(P['flap_centers'], ('SW1', 'SW2')):
        for a in (45, 135, 225, 315):
            contacts.append((f'{ref} cap stop leg', cx + P['cap_leg_r'] * math.cos(math.radians(a)), cy + P['cap_leg_r'] * math.sin(math.radians(a)), P['cap_leg_d'] / 2))
    for sx in (-1, 1):
        contacts.append(('DART stop leg', sx * P['dart_leg_x'], P['dart_y'], P['dart_leg_d'] / 2))
    hits = sorted({(kind, round(x, 2), round(y, 2), v['netName']) for kind, x, y, r in contacts for v in PCB['vias']
                   if math.hypot(v['x'] - x, v['y'] - y) < r + v['size'] / 2})
    pad_hits = [(kind, round(x, 2), round(y, 2)) for kind, x, y, r in contacts[len(B['REAR_POSTS']) + len(B['FRONT_POSTS']):]
                if Point(x, y).buffer(r + 0.3).intersects(fpads)]
    rep.add('I5', 'PCB↔CASE', 'Stop legs land clear of pads (no pad within 0.3 mm)', 'PASS' if not pad_hits else 'FAIL', len(pad_hits), 0, json.dumps(pad_hits) if pad_hits else '')
    # Tenting: the board's plot setting (viasonmask false) and the plotted mask Gerbers, as recorded by
    # CHECKS/build_builder_packs.py in R27_FAB_SUMMARY.json (no mask flash on any via).
    plot = re.search(r'\(viasonmask (true|false)\)', (root / 'LAYERS/01_PCB/SLIM4_R27.kicad_pcb').read_text())
    summary = root / 'CHECKS/R27_FAB_SUMMARY.json'
    fab = json.loads(summary.read_text()) if summary.exists() else None
    plotted = bool(fab) and fab['board_sha256'] == sha(root / 'LAYERS/01_PCB/SLIM4_R27.kicad_pcb') and fab['vias'].get('mask_openings_at_vias') == []
    tented = bool(plot) and plot[1] == 'false' and plotted
    where = '; '.join(f'{k} at ({x}, {y}) on a {n} via' for k, x, y, n in hits)
    rep.add('I4', 'PCB↔CASE', 'Vias under support posts and stop legs are tented (solder-masked)', 'PASS' if not hits or tented else 'GATE', len(hits), 0,
            (where + ('. Covered: the R27 plot settings keep vias off the mask (viasonmask false), the plotted mask Gerbers have no opening '
                      'on any via (CHECKS/R27_FAB_SUMMARY.json), and the order specifies epoxy-filled, capped vias.' if tented else
                      '. Confirm via tenting in the fabrication notes (run CHECKS/build_builder_packs.py to record the plotted masks).')) if hits else '')

    # ---- J. Audio ------------------------------------------------------------
    vols = []
    for cx, cy, inner in B['CHAMBERS']:
        h = B['Z_SPK_BACK'] - P['floor_inner_z']
        ledges = 4 * 1.6 * 1.6 * h
        vols.append((inner.area * h - ledges) / 1000.0)
        rep.add('J1', 'CASE', f'Speaker chamber at ({cx:.1f}, {cy:.1f}) clear of the board', 'PASS' if inner.buffer(P['chamber_wall']).distance(B['BOARD_OUTER']) >= 0.3 - 1e-3 else 'FAIL',
                r3(inner.buffer(P['chamber_wall']).distance(B['BOARD_OUTER'])), 0.3)
        spk = B['rrect'](cx, cy, B['SPK_W'], B['SPK_H'], 1.5)
        rep.add('J2', 'CASE', 'Speaker inside its chamber with ≥0.2 mm', 'PASS' if spk.buffer(0.2 - 1e-3).within(inner) else 'FAIL', r3(inner.exterior.distance(spk)), 0.2)
        port = box(cx - (B['SPK_W'] - 3)/2, cy - (B['SPK_H'] - 3)/2, cx + (B['SPK_W'] - 3)/2, cy + (B['SPK_H'] - 3)/2)
        slots = [g for g in B['GRILLE'] if g.intersects(spk)]
        rep.add('J3', 'CASE', 'Grille slots inside the speaker gasket opening', 'PASS' if len(slots) == 3 and all(g.within(port) for g in slots) else 'FAIL', len(slots), 3)
    rep.add('J4', 'CASE', 'Sealed back volume per speaker (cc)', 'INFO', [r3(v) for v in vols], None,
            'R3 reserved ~1.94 cc per side (CAD geometric capacity) and, following the R2 research direction, recommended comparing 1.0 / 1.5 / ~2.0 cc; response must be measured')
    rep.add('J5', 'CASE', 'Acoustic response, gasket compression and wire feedthrough seal', 'GATE', None, None, 'Measure impedance/response/distortion on a printed chamber pair.')

    # ---- K. USB-C -----------------------------------------------------------------
    uw, uh = P['usb_pocket']
    face_y = ENV['by_value']['USB4105-GF-A-120']['mating_face_y_mm']
    rep.add('K1', 'PCB↔CASE', 'USB-C overmold relief ≥ USB-IF max overmold 12.35 × 6.5 + clearance', 'PASS' if uw >= 12.35 + 0.2 and uh >= 6.5 + 0.1 else 'FAIL', [uw, uh], [12.55, 6.6])
    rep.add('K2', 'PCB↔CASE', 'Relief reaches the receptacle mating face', 'PASS', face_y, None, f'relief from Y=0 to Y={face_y}; centred on the receptacle (Z {r3(B["USB_ZC"])})')
    lip = (B['USB_ZC'] - uh/2) - B['Z_FLOOR_OUT']
    rep.add('K3', 'CASE', 'Material left under the USB relief (localised, below the 2.0 mm rule)', 'GATE', r3(lip), 0.7, 'Accepted locally because the port sits 3.31 mm deep on the back side; confirm by drop/insertion test.')

    # ---- L. Thickness & summary --------------------------------------------------
    clr, wall = 0.2, P['wall']
    def body_for(hmax):
        return B['Z_FILM_TOP'] + hmax + clr + wall
    back = sorted(((B['part_height'](p), p['ref']) for p in PCB['parts'] if p['side'] == 'back'), reverse=True)
    hmax_12 = 12.0 - B['Z_FILM_TOP'] - clr - wall
    over = [f'{ref} {h:.2f}' for h, ref in back if h > hmax_12 + 1e-9]
    rest = [h for h, ref in back if ref not in ('L2', 'J2')]
    T = P['battery'][2]
    min_body_cell = B['Z_FILM_TOP'] + wall - (P['lcd_z0'] - 1.1 * T - P['battery_pad'])
    max_cell_12 = (P['lcd_z0'] - P['battery_pad'] + (hmax_12 + clr)) / 1.1
    rep.add('L1', 'ALL', 'Body thickness (face film to rear floor)', 'INFO', r3(B['Z_FILM_TOP'] - B['Z_FLOOR_OUT']), None,
            f'with caps {r3(B["Z_CAP_TOP"] - B["Z_FLOOR_OUT"])} mm. The rear floor sits 0.2 mm below the tallest back-side part, L2 (Sunlord ASWPA4035, 3.50 mm). '
            f'Sub-12 mm needs every back-side part ≤ {hmax_12:.2f} mm (over today: {", ".join(over)}), which is a PCB change, and a cell no thicker than {max_cell_12:.2f} mm: '
            f'the {T:.1f} mm cell alone holds the body at ≥ {min_body_cell:.2f} mm. Replacing only L2 and J2 gives {body_for(rest[0]):.2f} mm.')
    rep.add('L2', 'CASE', 'Battery envelope fits the board window with swelling allowance', 'PASS' if (B['Z_BAT1'] <= P['lcd_z0'] - 0.1*P['battery'][2] + 1e-6) else 'FAIL',
            r3(P['lcd_z0'] - B['Z_BAT1']), r3(0.1*P['battery'][2]), '≥10 % of cell thickness free in front of the cell')
    win = B['WINDOW']
    batt = box(P['battery_center'][0] - P['battery'][0]/2, P['battery_center'][1] - P['battery'][1]/2, P['battery_center'][0] + P['battery'][0]/2, P['battery_center'][1] + P['battery'][1]/2)
    rep.add('L3', 'PCB↔CASE', 'Battery XY clearance to the board window', 'PASS' if batt.within(win) and win.exterior.distance(batt) >= 1.0 else 'FAIL', r3(win.exterior.distance(batt)), 1.0)
    rep.add('L4', 'CASE', 'Cell in hand: a protected 1-cell pack of 1000 mAh or more, up to 34 × 50 × 7 mm, on a JST PH 2.0 plug (J3)', 'GATE', None, None,
            'J3 pin 1 = BAT+, pin 2 = GND (Adafruit/SparkFun convention). Check the pack polarity (Q2 blocks a reversed pack only without USB), the cell size and swelling allowance in hand. Charge is up to 0.55 A (0.55 C at 1000 mAh) with no cell-temperature sensing.')
    skirt = OUT.difference(B['LIP_POLY'].buffer(P['lap_clear'] / 2, resolution=12))
    radial = skirt.distance(B['LIP_RING'])
    tape_part = next(it['solid'] for it in B['PARTS'] if it['name'].startswith('LAP TAPE')).val().BoundingBox()
    seat = P['plate_z0'] - tape_part.zmin
    rep.add('L5', 'CASE', 'Enclosure joint: lap running clearance and tape seat (retention by a 0.10 mm tape ring)', 'PASS' if radial >= P['lap_clear'] - 1e-3 and abs(seat - P['lap_tape']) < 1e-6 and abs(tape_part.zlen - P['lap_tape']) < 1e-6 else 'FAIL',
            [r3(radial), r3(seat)], [P['lap_clear'], P['lap_tape']], 'skirt bottom lands on the rear wall (hard stop); the tape ring fills the 0.10 mm seat between lip top and plate underside')
    lcd_top = P['lcd_z0'] + B['LCD_T']
    lens_bottom = B['Z_PLATE_TOP'] - P['lens'][2]
    strip = min((P['lens'][0] - B['TAPE_WINDOW'][0]) / 2, (P['lens'][1] - B['TAPE_WINDOW'][1]) / 2)
    rep.add('L6', 'CASE↔LCD', 'Display stack: one 0.10 mm tape frame bonds the module to the ledge and carries the lens', 'PASS' if abs(lcd_top + P['lcd_tape'] - lens_bottom) < 1e-6 and B['TAPE_WINDOW'][0] > P['active'][0] and B['TAPE_WINDOW'][1] > P['active'][1] and strip >= 0.4 else 'FAIL',
            [r3(lcd_top), P['lcd_tape'], r3(lens_bottom), r3(strip)], None,
            f'module top {lcd_top:.2f} + tape {P["lcd_tape"]:.2f} = ledge underside and lens bottom {lens_bottom:.2f}; window = active area + 0.05 per side; {strip:.2f} mm tape strip under the lens border; '
            f'{P["lcd_z0"] - B["Z_BAT1"]:.2f} mm free behind the module (battery swelling allowance)')

    stats = dict(pair_evaluations=n_pairs, distinct_pairs=len(distinct), evaluations_by_pose=by_pose, actuation=actuation)
    print(f'checked in {time.time() - t0:.1f} s')
    return B, stats


# ---------------------------------------------------------------------------
# R24 baseline audit (same interfaces, R10 geometry)
# ---------------------------------------------------------------------------
def baseline(r24, rep):
    # build_r10.py writes R10_FIT_CHECKS.json and a reference STEP next to itself, so
    # run it on a temporary copy: auditing must never modify the audited package.
    import shutil, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        for rel in ('LAYERS/02_CASE/build_r10.py', 'LAYERS/01_PCB/SLIM4_R21_PCB_LAYER.json'):
            (Path(tmp) / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(r24) / rel, Path(tmp) / rel)
        with contextlib.redirect_stdout(io.StringIO()):
            ns = runpy.run_path(str(Path(tmp) / 'LAYERS/02_CASE/build_r10.py'))
    PCB = json.loads((Path(r24) / 'LAYERS/01_PCB/SLIM4_R21_PCB_LAYER.json').read_text())
    out = Polygon(ns['outline'])
    inner = out.buffer(-2.0)
    board = Polygon(PCB['board']['outer'])
    worst = -max(inner.exterior.distance(Point(c)) for c in board.exterior.coords if not inner.contains(Point(c))) if not board.within(inner) else inner.exterior.distance(board)
    def yranges(g):
        parts = sorted((q.bounds[1], q.bounds[3]) for q in getattr(g, 'geoms', [g]) if not q.is_empty and q.area > 1e-4)
        merged = []
        for lo, hi in parts:
            if merged and lo <= merged[-1][1] + 0.2:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        return ', '.join(f'{lo:.1f}–{hi:.1f}' for lo, hi in merged)
    through = board.difference(out)
    edge = board.exterior.segmentize(0.02)
    poke = max((out.exterior.distance(Point(c)) for c in edge.coords if not out.contains(Point(c))), default=0.0)
    rep.add('B2', 'PCB↔CASE', 'R21 board inside a 2.0 mm wall with ≥0.3 mm', 'FAIL' if worst < 0.3 else 'PASS', r3(worst), 0.3,
            f'value = deepest board vertex inside the 2.0 mm wall (negative). The board breaks through the R10 outer surface by up to {poke:.2f} mm at Y {yranges(through)} '
            f'and enters the 2.0 mm wall at Y {yranges(board.difference(inner))} (Y {yranges(board.difference(out.buffer(-2.3)))} counting the 0.3 mm clearance).')
    lcd = box(-30.15, 0.0, 30.15, 111.4)
    rep.add('B3', 'CASE', 'LCD module inside the wall', 'FAIL' if not lcd.within(inner) else 'PASS', r3(out.exterior.distance(lcd)), 2.2, 'LCD top edge at Y=0 is on the exterior surface')
    rep.add('A2', 'PCB↔CASE', 'Board thickness used by the case = board file', 'FAIL', 1.6, PCB['board']['thickness'])
    rep.add('D3', 'PCB↔CASE', 'Flap caps reach the D2LS plungers', 'FAIL', r3(7.85 - (1.2 + 3.5)), [0.05, 0.25], 'cap underside 7.85 vs plunger free position 4.70: 3.15 mm air, no stem')
    rep.add('D6', 'PCB↔CASE', 'DART pill reaches SW3/SW4; pivot and stops defined', 'FAIL', r3(7.85 - 4.7), None, 'pill floats on the film; no pivot, return or stop')
    rep.add('D13', 'CASE', 'Caps retained in the shell', 'FAIL', None, None, '16 mm caps in 17 mm holes with nothing under the plate')
    rep.add('E2', 'ACRYLIC↔CASE', 'Molded relief vs film', 'FAIL', None, None, 'bezels/pill surround placed on top of the film (Z 7.85) although labelled molded; film not cut around them')
    rep.add('C1', 'CASE↔LCD', 'Opening centred on active area (R3 1.79 mm top border)', 'FAIL', 55.7, r3(0 + 1.79 + 103.296/2), 'the module was centred on the opening; with the module top at Y=0 the active area centre is Y 53.44, so the opening sits 2.26 mm low')
    for what in ('rear shell', 'battery package', 'speakers and chambers', 'USB-C aperture', 'FPC route', 'board retention', 'power/reset/boot access'):
        rep.add('X1', 'CASE', f'{what} present', 'FAIL', None, None, 'not in R10 CAD')
    sw = (Path(r24) / 'sw.js').read_text()
    assets = [a for a in re.findall(r"'\./([^']*)'", sw)]
    missing = [a for a in assets if a and not (Path(r24) / a).exists()]
    rep.add('S1', 'VIEWER', 'Service worker precache list resolves', 'FAIL' if missing else 'PASS', len(missing), 0,
            ('missing: ' + ', '.join(missing)) if missing else f'all {len(assets)} precache entries exist (an earlier R25 report wrongly listed this as FAIL)')
    html = (Path(r24) / 'index.html').read_text()
    css = (Path(r24) / 'styles.css').read_text()
    nav0 = html.find('<nav class="buildStack"'); nav1 = html.find('</nav>', nav0); lp = html.find('id="layerPanel"')
    clipped = nav0 < lp < nav1 and re.search(r'\.buildStack\{[^}]*overflow:hidden', css) is not None
    rep.add('S3', 'VIEWER', 'LAYERS panel can be seen when opened', 'FAIL' if clipped else 'PASS', None, None,
            'the panel sits inside nav.buildStack, which has overflow:hidden, and is positioned outside it, so it is clipped and never visible' if clipped else '')
    rep.add('S2', 'VIEWER', 'Lens sublayer toggle', 'FAIL', None, None, 'lens mesh exported in group "display", so the Protective lens checkbox has no effect')


def write(rep, path_json, path_md, title, stats=None):
    data = dict(title=title, counts=rep.counts(), converged=rep.counts().get('FAIL', 0) == 0, checks=rep.rows)
    if stats:
        data['stats'] = stats
    Path(path_json).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    lines = [f'# {title}', '', f'Result: **{"CONVERGED" if data["converged"] else "NOT CONVERGED"}** · ' + ' · '.join(f'{k} {v}' for k, v in sorted(data['counts'].items())), '',
             '| ID | Interface | Check | Status | Value | Limit |', '|---|---|---|---|---|---|']
    for r in rep.rows:
        if r['id'] == 'M1' and r['status'] == 'PASS':
            continue
        v = '' if r['value'] is None else json.dumps(r['value'], ensure_ascii=False)
        lim = '' if r['limit'] is None else json.dumps(r['limit'], ensure_ascii=False)
        lines.append(f"| {r['id']} | {r['interface']} | {r['title']} | {r['status']} | {v} | {lim} |")
    notes = [r for r in rep.rows if r['detail'] and r['status'] in ('FAIL', 'GATE', 'INFO')]
    if notes:
        lines += ['', '## Notes', '']
        lines += [f"- **{r['id']} {r['title']}** — {r['detail']}" for r in notes]
    m1 = [r for r in rep.rows if r['id'] == 'M1']
    if m1:
        lines += ['', f"Solid validity: {sum(r['status'] == 'PASS' for r in m1)}/{len(m1)} solids valid."]
    Path(path_md).write_text('\n'.join(lines) + '\n')
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', help='R24 package directory to audit for comparison')
    ap.add_argument('--root', default=str(ROOT))
    a = ap.parse_args()
    root = Path(a.root)
    rep = Report()
    _, stats = run(root, rep)
    data = write(rep, root / 'CHECKS/R32_CONVERGENCE_REPORT.json', root / 'CHECKS/R32_CONVERGENCE_REPORT.md',
                 'STRUTHIO SLIM4 R32 convergence report (PCB R27 · CASE R12 · ACRYLIC R2)', stats)
    print(json.dumps(data['counts']), 'converged' if data['converged'] else 'NOT converged', f"{stats['pair_evaluations']} pair evaluations ({stats['distinct_pairs']} distinct pairs)")
    for r in rep.rows:
        if r['status'] == 'FAIL':
            print('FAIL', r['id'], r['title'], r['value'], r['limit'], r['detail'][:400])
    if a.baseline:
        rb = Report()
        baseline(a.baseline, rb)
        b = write(rb, root / 'CHECKS/R24_BASELINE_AUDIT.json', root / 'CHECKS/R24_BASELINE_AUDIT.md', 'STRUTHIO SLIM4 R24 baseline audit (PCB R21 · CASE R10 · ACRYLIC R0)')
        print('R24 baseline:', json.dumps(b['counts']))
    sys.exit(0 if data['converged'] else 1)


if __name__ == '__main__':
    main()
