"""STRUTHIO SLIM4 CASE R12 + ACRYLIC R2, on PCB R27 (package R32; the case was converged on R21 in R26).

R12/R2 = R11/R1 plus the R26 decisions (DECISIONS_R26.md): 0.10 mm radial lap clearance with a
0.10 mm tape seat, a 0.10 mm display tape frame (LCD 0.10 mm further back), 0.10 mm radial DART
trunnion clearance, and a face film inset 0.20 mm from the case edge with one vent window per speaker.

Shared datum (unchanged from R25): millimetres, R21 PCB XY (X right, Y down from the
board's top edge region, as in KiCad), board bottom at Z=0, +Z toward the device front.

Nothing here edits the PCB. The board outline, footprint positions and heights are
read from LAYERS/01_PCB/SLIM4_R27_PCB_LAYER.json and CHECKS/COMPONENT_ENVELOPES_R27.json,
and every case/acrylic feature is placed against them. R23 to R27 keep R21's outline, thickness and
switch positions, so the R12 parameters are unchanged; the harness reserves follow the R23-R27
J3/J4/J5 positions (R24 to R27 moved no connector). The LCD parameters are still the R3/HOTHMI envelope: the case was set aside
by the owner for R23-R27 (5 in Crystalfontz panel, its tail folded once behind it into a top-contact J1
on the board front), and its pass is open (CHECKS/R32_CONVERGENCE_REPORT.md). R23 shortened the
battery window to 38 x 53.5 mm, so the cell envelope is 34 x 50 x 7 (503450 / 703450), 1.5 mm below
the window's top edge and 2.0 mm clear of its bottom edge for the leads.

Run:  python LAYERS/02_CASE/build_r12.py      (builds and prints a short summary)
The export script and the convergence checker import this file with runpy.
"""
from pathlib import Path
import json, math
import cadquery as cq
from shapely.geometry import Polygon, Point, box, LineString
from shapely.ops import unary_union
from shapely import affinity

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PCB = json.loads((ROOT / 'LAYERS/01_PCB/SLIM4_R27_PCB_LAYER.json').read_text())
ENV = json.loads((ROOT / 'CHECKS/COMPONENT_ENVELOPES_R27.json').read_text())

# ---------------------------------------------------------------------------
# Parameters. Most R12 dimensions live here and the checker reads the same dict.
# Exceptions, edited further down: the support/clamp post positions, the R10
# silhouette control points, and the FPC/harness route and ledge geometry.
# ---------------------------------------------------------------------------
P = dict(
    revision_case='R12', revision_acrylic='R2', package='R32',
    pcb_t=PCB['board']['thickness'],                 # 1.2, from the board file (R10 modelled 1.6)
    wall=2.0,                                        # minimum structural wall / plate / floor
    board_to_wall_clearance=0.3,
    # Front stack (R10 values kept where they were consistent)
    plate_z0=5.65, plate_t=2.0, film_t=0.20, relief=0.5, cap_rise=1.5,
    # LCD module (HOTHMI 4.7 in, 540 x 960 at 0.1076 mm): R3 top-inactive assumption retained
    lcd=(60.3, 111.4, 1.75), lcd_top_y=2.21, lcd_z0=5.10,          # R12: 0.10 further back for the display tape frame
    lcd_tape=0.10,                                   # one die-cut double-sided frame bonds module to ledge and lens
    active=(58.104, 103.296), active_top_inactive=1.79,
    screen_opening=(58.8, 104.0), screen_r=2.5,
    lens=(59.2, 104.4, 0.7), lens_r=2.5, lens_rebate=(59.4, 104.6), lens_rebate_r=2.6,
    lcd_pocket_w=60.5, lcd_pocket_top_gap=0.1, lcd_fpc_bend=0.6,   # pocket runs 0.6 past the module for the FPC bend
    # Flap (arcade) controls on SW1/SW2
    flap_centers=((-40.75, 102.0), (40.75, 102.0)),
    flap_hole_d=17.0, flap_cap_d=16.0, bezel_od=18.0,
    cap_recess_d=12.6, cap_nub_d=1.4, cap_flange_d=17.8, cap_flange_t=0.8,   # full ring: no rotation-dependent tabs
    cap_leg_r=7.15, cap_leg_d=1.2,
    # Actuation stack against Omron D2LS (FP 3.5, OP 3.2 above the board top)
    pregap=0.15, ot_design=0.15,
    # DART rocker on SW3/SW4 (switch row Y = 119.296)
    dart_y=119.296, dart_cy=119.80, dart_sw_x=16.0,   # pill centre 0.504 below the fixed switch row
    dart_hole=(50.0, 7.0), dart_hole_r=3.4,
    dart_cap=(49.0, 6.5), dart_cap_r=3.15, dart_surround=(52.0, 9.0), dart_surround_r=4.4,
    dart_nub_d=1.4, dart_leg_x=23.0, dart_leg_d=1.2,
    dart_pivot_z=5.05, dart_trunnion_d=1.0, dart_trunnion_clear=0.10,   # R12: radial running clearance (was 0.05)
    dart_boss=(2.0, 1.4), dart_boss_z0=4.30,   # R12: 0.15 web under the wider bore (was 4.45)
    dart_keel=(2.0, 4.55),
    # Film (ACRYLIC R2)
    film_clear=0.2,                                  # radial clearance around raised bezels
    film_edge_inset=0.20,                            # R2: film edge 0.20 inside the case edge (die-cut tolerance)
    film_stack=(('clear optical PET, hard-coat face', 0.175), ('optically clear adhesive', 0.025)),   # R2: sums to film_t
    film_vent_r=0.3,                                 # R2: one rounded vent window per speaker (r ≤ 0.39 keeps the 0.1 grille margin)
    # Rear shell
    floor_inner_z=-3.7,                              # L2 (3.5 mm) + 0.2 clearance sets the floor
    lap=1.0,                                         # front-skirt / rear-lip lap joint height
    lap_clear=0.10,                                  # R12: radial clearance between skirt and lip
    lap_tape=0.10,                                   # R12: tape seat between lip top and plate underside
    # Battery: 703450-class pouch with PCM, in the R21 board window (38 x 56)
    battery=(34.0, 50.0, 7.0), battery_center=(0.0, 43.5), battery_pad=0.2,
    # Speakers: Same Sky CMS-18138A-SP (18 x 13 x 2.5, 500 Hz) front-firing
    speaker=(18.0, 13.0, 2.5), speaker_center_x=38.3, speaker_center_y=125.6,
    speaker_gasket=0.25, chamber_wall=1.0, chamber_clear=0.2,
    grille_slot=(12.0, 0.8), grille_pitch=1.9,
    # USB-C overmold relief (USB-IF plug overmold max 12.35 x 6.5)
    usb_pocket=(12.6, 6.6), usb_pocket_r=1.6,
    # Rear service access
    power_pin_d=2.4, power_hole_d=2.8, power_collar_d=4.0, power_gap=0.10, power_proud=0.30,
    pinhole_d=1.2,
    # FPC route reserve as R12 drew it for an extension FPC (from R23 the panel tail folds behind the panel into J1 on the
    # board front, so the reserve now ends at the board's back face; the case pass replaces it)
    fpc_w=10.5, fpc_clear=0.5,
    # Saddle at the bottom centre: lift reduced 4.5 -> 4.0 mm so the FPC can wrap the board tab
    saddle_center_y=131.3,
    post_d_rear=2.4, post_d_front=2.0,
)
Z_BOARD_TOP = P['pcb_t']
Z_PLATE_TOP = P['plate_z0'] + P['plate_t']           # 7.65
Z_FILM_TOP = Z_PLATE_TOP + P['film_t']               # 7.85
Z_RELIEF_TOP = Z_FILM_TOP + P['relief']              # 8.35
Z_CAP_TOP = Z_FILM_TOP + P['cap_rise']               # 9.35
Z_FLOOR_OUT = P['floor_inner_z'] - P['wall']         # -5.70
Z_LAP = P['plate_z0'] - P['lap']                     # 4.65

D2LS = ENV['by_value']['D2LS-21']
Z_FP = Z_BOARD_TOP + D2LS['free_position_mm']        # 4.70
Z_OP = Z_BOARD_TOP + D2LS['operating_position_mm']   # 4.40
Z_SW_BODY_TOP = Z_BOARD_TOP + D2LS['height_mm']      # 4.20
STROKE = P['pregap'] + (D2LS['free_position_mm'] - D2LS['operating_position_mm']) + P['ot_design']  # 0.60
Z_NUB = Z_FP + P['pregap']                           # 4.85

LCD_W, LCD_H, LCD_T = P['lcd']
LCD_CY = P['lcd_top_y'] + LCD_H / 2                  # 57.91
ACTIVE_CY = P['lcd_top_y'] + P['active_top_inactive'] + P['active'][1] / 2   # 55.648

# ---------------------------------------------------------------------------
# 2D helpers
# ---------------------------------------------------------------------------
def cubic(p0, p1, p2, p3, n=24):
    pts = []
    for i in range(1, n + 1):
        t = i / n; u = 1 - t
        pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
                    u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return pts

def rrect(cx, cy, w, h, r, res=16):
    return box(cx - w/2 + r, cy - h/2 + r, cx + w/2 - r, cy + h/2 - r).buffer(r, resolution=res) if r > 0 else box(cx-w/2, cy-h/2, cx+w/2, cy+h/2)

def disc(cx, cy, d, res=48):
    return Point(cx, cy).buffer(d / 2, resolution=res)

def sector(cx, cy, r0, r1, a_deg, span_deg, res=12):
    a0 = math.radians(a_deg - span_deg / 2); a1 = math.radians(a_deg + span_deg / 2)
    outer = [(cx + r1*math.cos(a0 + (a1-a0)*i/res), cy + r1*math.sin(a0 + (a1-a0)*i/res)) for i in range(res+1)]
    inner = [(cx + r0*math.cos(a1 - (a1-a0)*i/res), cy + r0*math.sin(a1 - (a1-a0)*i/res)) for i in range(res+1)]
    return Polygon(outer + inner)

def clean(g):
    return g.buffer(0)

# ---------------------------------------------------------------------------
# Board (read only)
# ---------------------------------------------------------------------------
BOARD_OUTER = Polygon(PCB['board']['outer'])
BOARD_HOLES = [Polygon(h) for h in PCB['board'].get('holes', [])]
BOARD = Polygon(PCB['board']['outer'], [h for h in PCB['board'].get('holes', [])])
WINDOW = BOARD_HOLES[0]                              # battery window, x +-19, y 17..70.5 (R23-R27)

def part_height(p):
    e = ENV['by_value'].get(p['value'])
    if e:
        return e['height_mm']
    for prefix, h in ENV['by_value_prefix'].items():
        if p['value'].startswith(prefix):
            return h['height_mm']
    return p['z']

def part_footprint(p):
    w, h = p['w'], p['h']
    g = box(-w/2, -h/2, w/2, h/2)
    g = affinity.rotate(g, p.get('rot', 0), origin=(0, 0))
    return affinity.translate(g, p['x'], p['y'])

# ---------------------------------------------------------------------------
# Exterior outline R11
# R10 silhouette kept, but it must contain the R21 board with a 2.0 mm wall plus
# 0.3 mm clearance and the LCD module with a 2.0 mm wall plus 0.2 mm. R10 failed
# both (board reached the outer surface at the shoulders, Y 70-89; LCD top edge sat
# on Y=0). The bounding envelope stays 104.0 x 135.3.
# ---------------------------------------------------------------------------
def r10_right_half(saddle_y):
    right = [(0, 0), (27, 0)]
    right += cubic((27, 0), (31, 0), (33, 2), (33, 7))
    right += [(33, 70)]
    right += cubic((33, 70), (33, 72.5), (32.8, 74), (32.8, 76))
    right += cubic((32.8, 76), (32.8, 83), (52, 85), (52, 96), n=32)
    right += cubic((52, 96), (52, 104), (51.5, 108), (51.5, 112), n=16)
    right += cubic((51.5, 112), (51.5, 117), (49.8, 119.0), (49.8, 123), n=20)
    right += cubic((49.8, 123), (49.8, 127), (51.5, 128.5), (52, 132), n=18)
    right += cubic((52, 132), (51.5, 134.3), (47, 135.3), (41, 135.3), n=16)
    right += cubic((41, 135.3), (30, 135.3), (12, saddle_y), (0, saddle_y), n=28)
    return right

def mirrored(right):
    pts = right + [(-x, y) for x, y in reversed(right[1:-1])]
    return list(dict.fromkeys((round(x, 5), round(y, 5)) for x, y in pts))

R10_OUTLINE = Polygon(mirrored(r10_right_half(130.8)))
_base = Polygon(mirrored(r10_right_half(P['saddle_center_y'])))
_need_board = BOARD_OUTER.buffer(P['wall'] + P['board_to_wall_clearance'] + 0.05, resolution=24)
_lcd_box = box(-LCD_W/2, P['lcd_top_y'], LCD_W/2, P['lcd_top_y'] + LCD_H)
_need_lcd = _lcd_box.buffer(P['wall'] + 0.25, resolution=24)
_envelope = box(-52.0, 0.0, 52.0, 135.3)
_u = unary_union([_base, _need_board, _need_lcd]).intersection(_envelope)
# Morphological closing smooths the joins into the R10 curves without moving the
# surfaces that already cleared the board.
_u = _u.buffer(3.0, resolution=24).buffer(-3.0, resolution=24).intersection(_envelope)
_u = _u.simplify(0.02)
OUTLINE_POLY = Polygon([(round(x, 4), round(y, 4)) for x, y in _u.exterior.coords])
OUTLINE = list(OUTLINE_POLY.exterior.coords)[:-1]
INNER_POLY = OUTLINE_POLY.buffer(-P['wall'], resolution=12).simplify(0.005)      # interior cavity
LIP_POLY = OUTLINE_POLY.buffer(-P['wall'] / 2, resolution=12).simplify(0.005)    # lap joint split line

# ---------------------------------------------------------------------------
# CadQuery helpers
# ---------------------------------------------------------------------------
def _ring(coords):
    pts = list(coords)
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    return [(float(x), float(y)) for x, y in pts]

def prism(geom, z0, z1):
    """Extrude a shapely Polygon/MultiPolygon (holes allowed) between z0 and z1."""
    geoms = list(getattr(geom, 'geoms', [geom]))
    solid = None
    for g in geoms:
        if g.is_empty or g.area < 1e-6:
            continue
        wp = cq.Workplane('XY').polyline(_ring(g.exterior.coords)).close()
        for hole in g.interiors:
            wp = wp.polyline(_ring(hole.coords)).close()
        s = wp.extrude(z1 - z0).translate((0, 0, z0))
        solid = s if solid is None else solid.union(s)
    return solid

def cyl(cx, cy, d, z0, z1):
    return cq.Workplane('XY').center(cx, cy).circle(d / 2).extrude(z1 - z0).translate((0, 0, z0))

def rbox(cx, cy, w, h, z0, z1, r=0.0):
    s = cq.Workplane('XY').box(w, h, z1 - z0, centered=(True, True, False))
    if r > 0:
        s = s.edges('|Z').fillet(min(r, w/2 - 1e-3, h/2 - 1e-3))
    return s.translate((cx, cy, z0))

# ---------------------------------------------------------------------------
# Derived positions
# ---------------------------------------------------------------------------
SPK_W, SPK_H, SPK_T = P['speaker']
SPK_CENTERS = [(-P['speaker_center_x'], P['speaker_center_y']), (P['speaker_center_x'], P['speaker_center_y'])]
Z_SPK_FRONT = P['plate_z0'] - P['speaker_gasket']    # 5.40
Z_SPK_BACK = Z_SPK_FRONT - SPK_T                     # 2.90
GRILLE_YS = [P['speaker_center_y'] + k * P['grille_pitch'] for k in (-1, 0, 1)]

BAT_W, BAT_H, BAT_T = P['battery']
Z_BAT0 = P['floor_inner_z'] + P['battery_pad']       # -3.5
Z_BAT1 = Z_BAT0 + BAT_T                              # 3.5

USB = next(p for p in PCB['parts'] if p['ref'] == 'J2')
USB_ENV = ENV['by_value']['USB4105-GF-A-120']
USB_ZC = -USB_ENV['height_mm'] / 2                    # receptacle on the back side

SW = {p['ref']: p for p in PCB['parts']}
J1 = SW['J1']

THETA_DART = STROKE / P['dart_sw_x']                  # rocker angle at the hard stop (rad)

# ---------------------------------------------------------------------------
# 2D features shared by the front shell and the film
# ---------------------------------------------------------------------------
SCREEN_OPENING = rrect(0, ACTIVE_CY, *P['screen_opening'], P['screen_r'])
LENS_REBATE = rrect(0, ACTIVE_CY, *P['lens_rebate'], P['lens_rebate_r'])
LCD_POCKET = box(-P['lcd_pocket_w']/2, P['lcd_top_y'] - P['lcd_pocket_top_gap'], P['lcd_pocket_w']/2, P['lcd_top_y'] + LCD_H + P['lcd_fpc_bend'])
FLAP_HOLES = [disc(x, y, P['flap_hole_d'], 64) for x, y in P['flap_centers']]
BEZELS = [disc(x, y, P['bezel_od'], 64).difference(disc(x, y, P['flap_hole_d'], 64)) for x, y in P['flap_centers']]
DART_HOLE = rrect(0, P['dart_cy'], *P['dart_hole'], P['dart_hole_r'], 12)
DART_SURROUND = rrect(0, P['dart_cy'], *P['dart_surround'], P['dart_surround_r'], 12).difference(DART_HOLE)
GRILLE = [rrect(sx, gy, *P['grille_slot'], P['grille_slot'][1]/2 - 0.01, 6) for sx, _ in SPK_CENTERS for gy in GRILLE_YS]
FILM_FLAP_CUTS = [disc(x, y, P['bezel_od'] + 2*P['film_clear'], 64) for x, y in P['flap_centers']]
FILM_DART_CUT = rrect(0, P['dart_cy'], P['dart_surround'][0] + 2*P['film_clear'], P['dart_surround'][1] + 2*P['film_clear'], P['dart_surround_r'] + P['film_clear'], 12)
# R2: one vent window per speaker spanning its three grille slots (0.1 margin), instead of six 1.0 mm slots.
FILM_VENT_SIZE = (P['grille_slot'][0] + 0.2, (GRILLE_YS[-1] - GRILLE_YS[0]) + P['grille_slot'][1] + 0.2)
FILM_VENTS = [rrect(sx, (GRILLE_YS[0] + GRILLE_YS[-1]) / 2, *FILM_VENT_SIZE, P['film_vent_r'], 6) for sx, _ in SPK_CENTERS]
FILM_OUTLINE = OUTLINE_POLY.buffer(-P['film_edge_inset'], resolution=16).simplify(0.005)
FILM_POLY = clean(FILM_OUTLINE.difference(unary_union(FILM_FLAP_CUTS + [FILM_DART_CUT] + FILM_VENTS)))

# Speaker chambers: speaker + clearance + wall, clipped by the outer wall's inner face.
def chamber_geoms(cx, cy):
    inner = rrect(cx, cy, SPK_W + 2*P['chamber_clear'], SPK_H + 2*P['chamber_clear'], 0.6)
    outer = rrect(cx, cy, SPK_W + 2*(P['chamber_clear'] + P['chamber_wall']), SPK_H + 2*(P['chamber_clear'] + P['chamber_wall']), 1.2)
    inner = inner.intersection(INNER_POLY)
    ring = outer.difference(inner).intersection(INNER_POLY.buffer(0.01))
    return inner, ring

# ---------------------------------------------------------------------------
# Board support / clamp points: fixed positions, frozen so the geometry is
# deterministic. Check I1 in CHECKS/convergence_check.py verifies that each lands on
# bare board (no pad within the post radius + 0.3 mm on the contacted side), and I4
# lists any via under a post or stop leg.
# ---------------------------------------------------------------------------
CLAMP_POSTS = [  # front post + rear post at the same XY: the board is clamped here
    (-33.5, 84.0), (33.5, 84.0),        # shoulders
    (-38.0, 114.0), (38.0, 114.0),      # below the flap caps
    (-15.0, 126.0), (24.5, 126.0),      # bottom tab, clear of the FPC run
]
REAR_ONLY_POSTS = [  # rear-shell supports on bare board areas of the back side
    (-40.75, 96.0), (40.75, 96.0), (-40.75, 108.0), (40.75, 108.0),   # back SW1 / SW2
    (-24.0, 119.3), (24.25, 119.3),                                    # back SW3 / SW4 and the DART stop legs
    (-24.0, 10.0), (-26.0, 40.0), (-26.0, 54.0), (21.5, 60.0),
    (-21.5, 76.0), (21.5, 76.0), (-10.0, 100.0),
]
REAR_POSTS = CLAMP_POSTS + REAR_ONLY_POSTS
FRONT_POSTS = list(CLAMP_POSTS)

def _sw_center(ref):
    p = SW[ref]
    return p['x'], p['y']

# ---------------------------------------------------------------------------
# Solids
# ---------------------------------------------------------------------------
PARTS = []   # dicts: name, solid, layer, sub, group, color, kind ('static'|'moving'|'purchased'|'reserve')

def add(name, solid, layer, sub, group, color, kind='static', note=''):
    PARTS.append(dict(name=name, solid=solid, layer=layer, sub=sub, group=group, color=color, kind=kind, note=note))
    return solid

# ---- FRONT SHELL ----
# Openings are cut with true arcs (the shapely copies above are for 2D checks).
zc0, zc1 = P['plate_z0'] - 0.05, Z_RELIEF_TOP + 0.05
front = prism(OUTLINE_POLY, P['plate_z0'], Z_PLATE_TOP)
# Raised molded relief is part of the shell; the film is cut around it.
for x, y in P['flap_centers']:
    front = front.union(cyl(x, y, P['bezel_od'], Z_PLATE_TOP - 0.01, Z_RELIEF_TOP))
front = front.union(rbox(0, P['dart_cy'], *P['dart_surround'], Z_PLATE_TOP - 0.01, Z_RELIEF_TOP, P['dart_surround_r']))
front = front.cut(rbox(0, ACTIVE_CY, *P['screen_opening'], zc0, zc1, P['screen_r']))
front = front.cut(rbox(0, ACTIVE_CY, *P['lens_rebate'], Z_PLATE_TOP - P['lens'][2], zc1, P['lens_rebate_r']))
lp = LCD_POCKET.bounds
front = front.cut(rbox((lp[0] + lp[2]) / 2, (lp[1] + lp[3]) / 2, lp[2] - lp[0], lp[3] - lp[1], zc0, Z_PLATE_TOP - P['lens'][2]))
for x, y in P['flap_centers']:
    front = front.cut(cyl(x, y, P['flap_hole_d'], zc0, zc1))
front = front.cut(rbox(0, P['dart_cy'], *P['dart_hole'], zc0, zc1, P['dart_hole_r']))
for sx, _ in SPK_CENTERS:
    for gy in GRILLE_YS:
        front = front.cut(rbox(sx, gy, *P['grille_slot'], zc0, zc1, P['grille_slot'][1] / 2 - 0.01))
# Outer skirt of the lap joint (R12: half the radial clearance taken from each side of the split line).
front = front.union(prism(OUTLINE_POLY.difference(LIP_POLY.buffer(P['lap_clear'] / 2, resolution=12)), Z_LAP, P['plate_z0'] + 0.01))
# DART pivot bosses with trunnion bores.
bw, bt = P['dart_boss']
cap_half = P['dart_cap'][1] / 2
for sgn in (-1, 1):
    y_in = P['dart_cy'] + sgn * (cap_half + 0.1)
    y_out = y_in + sgn * bt
    yc = (y_in + y_out) / 2
    boss = rbox(0, yc, bw, bt, P['dart_boss_z0'], P['plate_z0'] + 0.01)
    bore = (cq.Workplane('XZ').center(0, P['dart_pivot_z']).circle(P['dart_trunnion_d'] / 2 + P['dart_trunnion_clear'])
            .extrude(bt + 0.2, both=True).translate((0, yc, 0)))
    front = front.union(boss.cut(bore))
# Front clamp posts.
for x, y in FRONT_POSTS:
    front = front.union(cyl(x, y, P['post_d_front'], Z_BOARD_TOP, P['plate_z0'] + 0.01))
add('FRONT SHELL R12 · PLATE, RELIEF, LAP SKIRT, DART PIVOTS', front, 'CASE', 'front_shell', 'shell', '#193c59')

# ---- REAR SHELL ----
rear = prism(OUTLINE_POLY, Z_FLOOR_OUT, P['floor_inner_z'])                       # floor
rear = rear.union(prism(OUTLINE_POLY.difference(INNER_POLY), P['floor_inner_z'] - 0.01, Z_LAP))  # wall
LIP_RING = LIP_POLY.buffer(-P['lap_clear'] / 2, resolution=12).difference(INNER_POLY)
rear = rear.union(prism(LIP_RING, Z_LAP - 0.01, P['plate_z0'] - P['lap_tape']))   # lap lip; tape seat above it
# Speaker chambers (ring walls up to the plate underside) and speaker ledges.
CHAMBERS = []
for cx, cy in SPK_CENTERS:
    inner, ring = chamber_geoms(cx, cy)
    CHAMBERS.append((cx, cy, inner))
    rear = rear.union(prism(ring, P['floor_inner_z'] - 0.01, P['plate_z0']))
    for dx in (-1, 1):
        for dy in (-1, 1):
            lx = cx + dx * (SPK_W/2 - 0.6); ly = cy + dy * (SPK_H/2 - 0.6)
            ledge = rbox(lx, ly, 1.6, 1.6, P['floor_inner_z'] - 0.01, Z_SPK_BACK).intersect(prism(inner, P['floor_inner_z'] - 0.02, Z_SPK_BACK))
            rear = rear.union(ledge)
# Board support posts.
for x, y in REAR_POSTS:
    rear = rear.union(cyl(x, y, P['post_d_rear'], P['floor_inner_z'] - 0.01, 0.0))
# USB-C overmold relief through the top wall into the floor edge.
uw, uh = P['usb_pocket']
usb_y1 = USB_ENV['mating_face_y_mm']
usb_cut = (cq.Workplane('XZ').center(0, USB_ZC).rect(uw, uh).extrude(-(usb_y1 + 0.5))
           .edges('|Y').fillet(P['usb_pocket_r']).translate((0, -0.5, 0)))
rear = rear.cut(usb_cut)
# Service access: power plunger bore and pinholes for RESET / BOOT.
pw = SW['SW5']
rear = rear.cut(cyl(pw['x'], pw['y'], P['power_hole_d'], Z_FLOOR_OUT - 0.1, P['floor_inner_z'] + 0.1))
for ref in ('SW6', 'SW7'):
    q = SW[ref]
    rear = rear.cut(cyl(q['x'], q['y'], P['pinhole_d'], Z_FLOOR_OUT - 0.1, P['floor_inner_z'] + 0.1))
# Speaker wire feedthroughs (sealed with RTV at assembly).
FEED = []
for (cx, cy), conn in zip(SPK_CENTERS, ('J4', 'J5')):
    j = SW[conn]
    fy = cy - SPK_H/2 - P['chamber_clear'] - P['chamber_wall'] / 2
    FEED.append((j['x'], fy))
    rear = rear.cut(rbox(j['x'], fy, 1.2, P['chamber_wall'] + 0.4, -2.2, -1.0))
add('REAR SHELL R12 · FLOOR, WALLS, CHAMBERS, SUPPORTS', rear, 'CASE', 'rear_shell', 'rear', '#16324b')

# ---- SCREEN STACK ----
lcd = rbox(0, LCD_CY, LCD_W, LCD_H, P['lcd_z0'], P['lcd_z0'] + LCD_T)
add('HOTHMI 4.7" LCD MODULE ENVELOPE · TOP AT Y 2.21', lcd, 'CASE', 'screen', 'display', '#59636b', 'purchased')
lens = rbox(0, ACTIVE_CY, P['lens'][0], P['lens'][1], Z_PLATE_TOP - P['lens'][2], Z_PLATE_TOP, P['lens_r'])
add('PROTECTIVE LENS · 59.2 × 104.4 × 0.70 COVER GLASS', lens, 'CASE', 'screen', 'lens', '#72c8d2', 'purchased')
# R12: one 0.10 mm die-cut double-sided frame on the module front: its outer band bonds the module to
# the plate ledge, its inner 0.5 mm strip carries the lens border. Window = active area + 0.05 per side.
TAPE_WINDOW = (P['active'][0] + 0.1, P['active'][1] + 0.1)
Z_LCD_TOP = P['lcd_z0'] + LCD_T
tape = rbox(0, LCD_CY, LCD_W, LCD_H, Z_LCD_TOP, Z_LCD_TOP + P['lcd_tape']).cut(
    rbox(0, ACTIVE_CY, *TAPE_WINDOW, Z_LCD_TOP - 0.05, Z_LCD_TOP + P['lcd_tape'] + 0.05))
add('DISPLAY TAPE FRAME 0.10 · MODULE TO LEDGE AND LENS', tape, 'CASE', 'screen', 'display', '#c8b98a', 'purchased')

# ---- FLAP CAPS (moving) ----
def flap_cap(cx, cy):
    crown = cyl(cx, cy, P['flap_cap_d'], Z_NUB, Z_CAP_TOP)
    crown = crown.cut(cyl(cx, cy, P['cap_recess_d'], Z_NUB - 0.01, Z_NUB + 0.6))
    crown = crown.union(cyl(cx, cy, P['cap_nub_d'], Z_NUB, Z_NUB + 0.61))
    # Retention flange under the plate: its top face is the up-stop against the plate.
    flange = cyl(cx, cy, P['cap_flange_d'], P['plate_z0'] - P['cap_flange_t'], P['plate_z0'])
    crown = crown.union(flange.cut(cyl(cx, cy, P['cap_recess_d'], P['plate_z0'] - P['cap_flange_t'] - 0.01, P['plate_z0'] + 0.01)))
    for a in (45, 135, 225, 315):
        lx = cx + P['cap_leg_r'] * math.cos(math.radians(a)); ly = cy + P['cap_leg_r'] * math.sin(math.radians(a))
        crown = crown.union(cyl(lx, ly, P['cap_leg_d'], Z_BOARD_TOP + STROKE, Z_NUB + 0.01))
    return crown

for (cx, cy), lbl, ref in zip(P['flap_centers'], ('L', 'R'), ('SW1', 'SW2')):
    add(f'16 MM FLAP CAP {lbl} · ACTUATES {ref}', flap_cap(cx, cy), 'CASE', 'controls', 'controls', '#f08b23', 'moving')

# ---- DART ROCKER (moving) ----
def dart_rocker():
    cw, ch = P['dart_cap']
    body = rbox(0, P['dart_cy'], cw, ch, Z_NUB + 0.6, Z_CAP_TOP, P['dart_cap_r'])
    kw, kz0 = P['dart_keel']
    body = body.union(rbox(0, P['dart_cy'], kw, ch, kz0, Z_NUB + 0.61))
    tr = (cq.Workplane('XZ').center(0, P['dart_pivot_z']).circle(P['dart_trunnion_d'] / 2)
          .extrude(cap_half + P['dart_boss'][1] + 0.1 - 0.01, both=True).translate((0, P['dart_cy'], 0)))
    body = body.union(tr)
    for sx in (-1, 1):
        body = body.union(cyl(sx * P['dart_sw_x'], P['dart_y'], P['dart_nub_d'], Z_NUB, Z_NUB + 0.61))
        leg_z = Z_BOARD_TOP + (P['dart_leg_x'] + P['dart_leg_d'] / 2) * THETA_DART   # outer edge lands first
        body = body.union(cyl(sx * P['dart_leg_x'], P['dart_y'], P['dart_leg_d'], leg_z, Z_NUB + 0.61))
    return body

add('DART ROCKER · PIVOT X=0, ACTUATES SW3 / SW4', dart_rocker(), 'CASE', 'controls', 'controls', '#f08b23', 'moving')

# ---- POWER PLUNGER (moving, rear) ----
z_tip = -ENV['by_value']['B3U-1000P']['height_mm'] - P['power_gap']
plunger = cyl(pw['x'], pw['y'], P['power_pin_d'], Z_FLOOR_OUT - P['power_proud'], z_tip)
plunger = plunger.union(cyl(pw['x'], pw['y'], P['power_collar_d'], P['floor_inner_z'], P['floor_inner_z'] + 0.5))
add('POWER PLUNGER · ACTUATES SW5 PWR_WAKE', plunger, 'CASE', 'controls', 'controls', '#f08b23', 'moving')

# ---- INTERNALS: purchased envelopes and reserves ----
battery = rbox(*P['battery_center'], BAT_W, BAT_H, Z_BAT0, Z_BAT1, 1.0)
add('LIPO 703450-CLASS ENVELOPE · 34 × 50 × 7.0 IN BOARD WINDOW', battery, 'CASE', 'internals', 'battery', '#c9a227', 'purchased')
pad = rbox(*P['battery_center'], BAT_W, BAT_H, P['floor_inner_z'], Z_BAT0, 1.0)
add('BATTERY FOAM PAD 0.20', pad, 'CASE', 'internals', 'battery', '#6b5a1e', 'purchased')
# R12: lap tape ring (0.10 thick, 0.05 narrower than the lip on each side) between lip top and plate underside.
LAP_TAPE = LIP_POLY.buffer(-P['lap_clear'] / 2 - 0.05, resolution=12).difference(INNER_POLY.buffer(0.05, resolution=12))
add('LAP TAPE RING 0.10 · REAR LIP TO FRONT PLATE', prism(LAP_TAPE, P['plate_z0'] - P['lap_tape'], P['plate_z0']), 'CASE', 'internals', 'rear', '#c8b98a', 'purchased')
for (cx, cy), lbl in zip(SPK_CENTERS, ('L', 'R')):
    spk = rbox(cx, cy, SPK_W, SPK_H, Z_SPK_BACK, Z_SPK_FRONT, 1.5)
    add(f'SPEAKER {lbl} · SAME SKY CMS-18138A-SP 18 × 13 × 2.5', spk, 'CASE', 'internals', 'speakers', '#8c9aa6', 'purchased')
    gasket = rbox(cx, cy, SPK_W, SPK_H, Z_SPK_FRONT, P['plate_z0'], 1.5).cut(rbox(cx, cy, SPK_W - 3.0, SPK_H - 3.0, Z_SPK_FRONT - 0.1, P['plate_z0'] + 0.1, 0.8))
    add(f'SPEAKER {lbl} FRONT GASKET 0.25', gasket, 'CASE', 'internals', 'speakers', '#3b4650', 'purchased')

# FPC extension route reserve (flat cable + 0.5 mm tolerance band).
fw = P['fpc_w'] + 2 * P['fpc_clear']
lcd_bot = P['lcd_top_y'] + LCD_H
Y_DESCENT = 102.5
Y_TAB = max(y for x, y in PCB['board']['outer'] if abs(x) <= 26.01)    # 128.0
FPC_SEGMENTS = [
    # R12: the module sits 0.10 further back, so the fold and the run under it drop 0.10 as well.
    ('fold around LCD bottom edge', (-fw/2, lcd_bot, fw/2, lcd_bot + P['lcd_fpc_bend'] - 0.1, 4.65, 6.75)),
    ('run under LCD module', (-fw/2, Y_DESCENT, fw/2, lcd_bot + P['lcd_fpc_bend'] - 0.1, 4.65, 5.05)),
    ('S-bend down to board', (-fw/2, Y_DESCENT - 1.6, fw/2, Y_DESCENT + 0.4, 1.25, 5.05)),
    ('run on board front, between DART switches', (-fw/2, Y_DESCENT - 1.6, fw/2, Y_TAB, 1.25, 1.75)),
    ('wrap around board tab edge', (-fw/2, Y_TAB, fw/2, Y_TAB + 0.95, -1.35, 1.75)),
    ('return on board back', (-fw/2, 117.0, fw/2, Y_TAB + 0.95, -1.35, -0.6)),
]
fpc = None
for _, (x0, y0, x1, y1, z0, z1) in FPC_SEGMENTS:
    b = rbox((x0+x1)/2, (y0+y1)/2, x1-x0, y1-y0, z0, z1)
    fpc = b if fpc is None else fpc.union(b)
add('FPC EXTENSION ROUTE RESERVE · PANEL TO J1', fpc, 'CASE', 'internals', 'routes', '#d8b45a', 'reserve')

# Harness reserves: battery to J3, speakers to J4 / J5.
j3 = SW['J3']
j3_fp = part_footprint(j3)
win_x0, win_y0, win_x1, win_y1 = WINDOW.bounds
bat_end = P['battery_center'][1] + BAT_H / 2
# Leads leave the cell's PCM end into the 2 mm window gap, run to the window's left
# edge, then pass under the board to J3 (back side).
bat_lead = rbox((win_x0 + 0.4 - 10.0) / 2 - 0.0, (bat_end + win_y1) / 2, (-10.0) - (win_x0 + 0.4), win_y1 - bat_end - 0.3, -2.6, -0.4)
bat_lead = bat_lead.union(rbox((j3_fp.bounds[2] + win_x0 + 0.4) / 2, (j3['y'] - 1.0 + win_y1 - 0.15) / 2,
                               (win_x0 + 0.4) - j3_fp.bounds[2], (win_y1 - 0.15) - (j3['y'] - 1.0), -2.6, -0.4))
add('BATTERY LEAD RESERVE · TO J3', bat_lead, 'CASE', 'internals', 'routes', '#b07a2a', 'reserve')
for (cx, cy), conn, (fx, fy) in zip(SPK_CENTERS, ('J4', 'J5'), FEED):
    j = SW[conn]
    jy1 = part_footprint(j).bounds[3]
    run = rbox(fx, (jy1 + fy + 1.1) / 2, 1.0, (fy + 1.1) - jy1, -2.1, -1.1)
    riser = rbox(fx, fy + 1.1, 1.0, 1.0, -2.1, Z_SPK_BACK)
    add(f'SPEAKER LEAD RESERVE · TO {conn}', run.union(riser), 'CASE', 'internals', 'routes', '#b07a2a', 'reserve')

# ---- ACRYLIC R2 ----
film = prism(FILM_OUTLINE, Z_PLATE_TOP, Z_FILM_TOP)
fz0, fz1 = Z_PLATE_TOP - 0.05, Z_FILM_TOP + 0.05
for x, y in P['flap_centers']:
    film = film.cut(cyl(x, y, P['bezel_od'] + 2 * P['film_clear'], fz0, fz1))
film = film.cut(rbox(0, P['dart_cy'], P['dart_surround'][0] + 2 * P['film_clear'], P['dart_surround'][1] + 2 * P['film_clear'], fz0, fz1, P['dart_surround_r'] + P['film_clear']))
for sx, _ in SPK_CENTERS:
    film = film.cut(rbox(sx, (GRILLE_YS[0] + GRILLE_YS[-1]) / 2, *FILM_VENT_SIZE, fz0, fz1, P['film_vent_r']))
add('CLEAR FACE FILM R2 · 0.175 PET + 0.025 OCA', film, 'ACRYLIC', 'film', 'acrylic', '#a8e6ef', 'static')


def summary():
    s = dict(
        outline_bbox=[round(v, 3) for v in OUTLINE_POLY.bounds],
        outline_area_mm2=round(OUTLINE_POLY.area, 2),
        r10_outline_area_mm2=round(R10_OUTLINE.area, 2),
        lcd_center_y=LCD_CY, active_center_y=ACTIVE_CY,
        z_floor_out=Z_FLOOR_OUT, z_film_top=Z_FILM_TOP, z_cap_top=Z_CAP_TOP,
        body_thickness=round(Z_FILM_TOP - Z_FLOOR_OUT, 3),
        thickness_with_caps=round(Z_CAP_TOP - Z_FLOOR_OUT, 3),
        stroke=STROKE, dart_theta_deg=round(math.degrees(THETA_DART), 3),
        parts=[p['name'] for p in PARTS],
    )
    return s


if __name__ == '__main__':
    print(json.dumps(summary(), indent=2))
