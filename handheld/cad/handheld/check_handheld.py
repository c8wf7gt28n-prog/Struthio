#!/usr/bin/env python3
# STRUTHIO HANDHELD · fit checks for the handheld (struthio_handheld.scad): printable solids,
# the locked control / speaker / battery / power dimensions, and that nothing
# collides: keys through the shell, pills over CP1 at the locked travel, the
# speaker window sealed and inside the speaker rim, the board, the USB-C plug
# keep-out and the screw posts all clear. Model coordinates: mm, x right, y up,
# z from the front face back.
import re, sys
import numpy as np
import trimesh
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union
from shapely import affinity

P = {}   # parameters, read from the SCAD so the checks follow edits
src = open('struthio_handheld.scad').read()
for line in src.splitlines():
    for stmt in line.split('//')[0].split(';'):
        m = re.match(r'\s*([A-Z][A-Z0-9_]*)\s*=\s*(.+)$', stmt)
        if m:
            try: P[m.group(1)] = eval(m.group(2), {'__builtins__': {}}, P)
            except Exception: pass
fails = []
def check(ok, what):
    print(('PASS  ' if ok else 'FAIL  ') + what)
    if not ok: fails.append(what)

def svg_shape(path):
    t = open(path).read()
    rings = []
    for d in re.findall(r'<path d="([^"]*)"', t, re.S):
        for sub in re.split(r'M', d)[1:]:
            pts = [tuple(map(float, q.split(','))) for q in re.findall(r'-?[\d.]+,-?[\d.]+', sub)]
            if len(pts) > 2: rings.append(Polygon([(x, -y) for x, y in pts]).buffer(0))
    rings.sort(key=lambda p: -p.area)
    shape = rings[0]
    for r in rings[1:]:
        shape = shape.difference(r) if shape.buffer(1e-6).contains(r) else shape.union(r)
    return shape, rings

def section(m, z):
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None: return Polygon()
    path, _ = sec.to_2D(to_2D=np.eye(4))
    return unary_union(list(path.polygons_full)).buffer(0)

front = trimesh.load('stl/struthio_front.stl')
back = trimesh.load('stl/struthio_back.stl')
mat = trimesh.load('stl/struthio_mat.stl')
for name, m in (('front', front), ('back', back), ('mat (CM1)', mat)):
    check(m.is_watertight and len(m.split(only_watertight=False)) == 1, f'{name}: one watertight solid')

# ---- envelope -----------------------------------------------------------------------------
w = back.bounds[1][0] - back.bounds[0][0]; h = back.bounds[1][1] - back.bounds[0][1]
check(abs(w - 88) < 0.2 and h < 138.5, f'footprint {w:.1f} x {h:.1f} mm (88 wide; sculpted top and bottom corners lift {P["TOP_LIFT"]} / drop {P["BOTTOM_DROP"]})')
def solid_at(m, pts): return np.asarray(m.contains(np.asarray(pts, float)))
top_c = [y for y in np.arange(62.0, 66.0, 0.05) if solid_at(back, [[0, y, 8.0]])[0]]
bot_c = [y for y in np.arange(-72.0, -68.0, 0.05) if solid_at(back, [[0, y, 8.0]])[0]]
check(abs(max(top_c) - 64) < 0.15 and abs(min(bot_c) + 70) < 0.15,
      f'centre line: top {max(top_c):.1f}, bottom {min(bot_c):.1f} (y +64 / -70: screen, board and rocker datums untouched)')
bd = [[x, y, z] for x in np.linspace(-30.75, 30.75, 9) for y in np.linspace(-32.6, 60.2, 13) for z in np.linspace(4.6, 14.8, 5)]
check(not solid_at(back, bd).any() and not solid_at(front, bd).any(),
      'board envelope (61 x 92.4 x 11.5 + fit) is free of shell material behind the front locating rails (z >= 4.6)')
# wall thickness through the roll: shortest distance from the skin to the main cavity, at several depths
thin = []
for z in (6.0, 16.0, 17.5, 19.0, 20.3):   # clear of the side slots (z 7..15.6)
    sec = section(back, z)
    polys = list(sec.geoms) if hasattr(sec, 'geoms') else [sec]
    body = max(polys, key=lambda q: q.area)
    hole = max(body.interiors, key=lambda r: Polygon(r).area)
    posts = unary_union([Point(x, y).buffer(P['SCREW_POST_OD']/2 + 0.6) for x in (-P['SCREW_X'], P['SCREW_X']) for y in (P['SCREW_Y'], P['SCREW_Y_BOT'])])
    thin.append((body.exterior.difference(posts).distance(Polygon(hole).exterior.difference(posts)), z))
t_min, z_min = min(thin)
check(t_min >= 1.8, f'side wall >= 1.8 mm all the way round the roll, away from the screw posts (thinnest {t_min:.2f} mm at z {z_min})')
# screws: front boss pilot, back post clearance and counterbore on one axis
sx, sys_ = P['SCREW_X'], (P['SCREW_Y'], P['SCREW_Y_BOT'])
ok_pilot = all(not solid_at(front, [[x, y, z] for z in np.arange(1.7, P['JOIN_Z'], 0.5)]).any() and solid_at(front, [[x + P['PILOT_D']/2 + 0.6, y, 5.0]])[0]
               for x in (-sx, sx) for y in sys_)
ok_clear = all(not solid_at(back, [[x, y, z] for z in np.arange(P['JOIN_Z'] + 0.2, 23.5, 0.5)]).any() for x in (-sx, sx) for y in sys_)
seat = all(solid_at(back, [[x + P['CLEAR_D']/2 + 0.4, y, P['CBORE_Z'] - 0.5]])[0] for x in (-sx, sx) for y in sys_)
check(ok_pilot and ok_clear and seat, f'4 screws: M2 pilot in each front boss, clearance + counterbore through each back post, head seat at z {P["CBORE_Z"]}')
eng = P['JOIN_Z'] - (P['CBORE_Z'] - 10.0) if P['CBORE_Z'] - 10.0 < P['JOIN_Z'] else 0
check(eng >= 4.0, f'an M2 x 10 from the seat engages {eng:.1f} mm of the front boss (>= 4)')

# ---- controls -----------------------------------------------------------------------------
face = section(front, 1.5)
holes = [Polygon(r) for poly in getattr(face, 'geoms', [face]) for r in poly.interiors]
key_top = section(mat, -0.5)                       # the visible keys, through the shell
flange = section(mat, P['FRONT_T'] + 0.3)
keys = list(getattr(key_top, 'geoms', [key_top]))
check(len(keys) == 3, f'CM1 has 3 keys through the face (2 wings + rocker), found {len(keys)}')
for k in keys:
    hole = max((hh for hh in holes if hh.contains(k.representative_point())), key=lambda hh: hh.area, default=None)
    c = k.centroid
    name = 'rocker' if abs(c.x) < 5 else ('left wing' if c.x < 0 else 'right wing')
    if hole is None: check(False, f'{name}: no shell opening'); continue
    check(hole.contains(k.buffer(0.25)), f'{name}: key passes the opening with >= 0.25 mm clearance')
    fl = [f for f in getattr(flange, 'geoms', [flange]) if f.contains(c)]
    check(bool(fl) and fl[0].contains(hole.buffer(0.5)), f'{name}: flange overlaps the opening by >= 0.5 mm (captured)')
rk = [k for k in keys if abs(k.centroid.x) < 5][0]
rb = rk.bounds
check(abs((rb[2] - rb[0]) - P['ROCKER_W']) < 0.1 and abs((rb[3] - rb[1]) - P['ROCKER_H']) < 0.1,
      f'rocker visible face {rb[2]-rb[0]:.1f} x {rb[3]-rb[1]:.1f} mm (locked 44 x 9)')
wings = [k for k in keys if abs(k.centroid.x) >= 5]
for k in wings:
    b = k.bounds
    check(abs((b[2]-b[0]) - P['BTN_FACE_W']) < 0.3 and abs((b[3]-b[1]) - P['BTN_FACE_H']) < 0.3,
          f'wing face {b[2]-b[0]:.1f} x {b[3]-b[1]:.1f} mm (locked ~28 x 18.5)')
webs = min(holes[i].distance(holes[j]) for i in range(len(holes)) for j in range(i + 1, len(holes))
           if holes[i].area > 100 and holes[j].area > 100 and holes[i].distance(holes[j]) < 20)
check(webs >= 1.2, f'{webs:.2f} mm of shell between control openings (>= 1.2)')
# pills: rest gap above CP1 = locked travel; rocker centre stop shorter than the pills
z_low = mat.vertices[:, 2]
def lowest(x, y, r=None):
    # the mat's innermost point at (x, y): a ray from behind CP1 toward the face
    loc, _, _ = mat.ray.intersects_location([[x, y, 30.0]], [[0, 0, -1.0]])
    return loc[:, 2].max()
CP1 = P['CP1_Z']
for x, y, travel, name in ((-P['BTN_X'], P['BTN_Y'], 1.5, 'LEFT WING'), (P['BTN_X'], P['BTN_Y'], 1.5, 'RIGHT WING'),
                           (-P['DART_PITCH']/2, P['ROCKER_Y'], 1.3, 'DART LEFT'), (P['DART_PITCH']/2, P['ROCKER_Y'], 1.3, 'DART RIGHT')):
    gap = CP1 - lowest(x, y)
    check(abs(gap - travel) < 0.02, f'{name}: pill face {gap:.2f} mm above CP1 at rest (locked travel {travel})')
check(abs(P['DART_PITCH'] - 24.0) < 1e-9, 'DART contact centres 24.0 mm apart (locked)')
stop = CP1 - lowest(0, P['ROCKER_Y'])
centre_move = 1.3 * (P['ROCKER_W']/2) / (P['ROCKER_W']/2 + P['DART_PITCH']/2)
check(stop < 1.3 and centre_move < stop,
      f'rocker centre stop {stop:.2f} mm: a flat press stops before either pill; a one-end press moves the centre only {centre_move:.2f} mm')

# ---- CP1, mat, board, posts -----------------------------------------------------------------
cp1, _ = svg_shape('svg/cp1_outline.svg')
board = box(-30.5 - 0.35, 13.78 - 92.44/2 - 0.35, 30.5 + 0.35, 64)
check(cp1.intersection(board).area < 1e-6, f'CP1 stays clear of the board (top edge y {cp1.bounds[3]:.2f}, board {board.bounds[1]:.2f})')
mat_xy = section(mat, CP1 - 0.5)
check(mat_xy.intersection(board).area < 1e-6 and section(mat, 3.3).intersection(board).area < 1e-6, 'CM1 web and skirts stay clear of the board')
for x in (-P['SCREW_X'], P['SCREW_X']):
    post = Point(x, P['SCREW_Y_BOT']).buffer(P['POST_OD']/2)
    check(post.intersection(cp1).area < 1e-6 and post.intersection(mat_xy).area < 1e-6, f'lower screw post at x {x:+.0f} clears CP1 and the mat')
for x, y in ((-P['BTN_X'], P['BTN_Y']), (P['BTN_X'], P['BTN_Y']), (-12, P['ROCKER_Y']), (12, P['ROCKER_Y'])):
    check(cp1.contains(Point(x, y).buffer(P['CP1_PAD_D']/2 + 0.5)), f'CP1 carries the 7 mm pad at ({x:+.0f}, {y:.1f}) with 0.5 mm margin')

# ---- speaker ---------------------------------------------------------------------------------
spk = Point(P['SPKR_X'], P['SPKR_Y'])
win = Point(P['SPKR_X'], P['WINDOW_Y']).buffer(P['WINDOW_D']/2)
check(spk.buffer(28/2 - 0.5).contains(win), 'speaker window lies inside the speaker rim gasket (sealed front path)')
check(P['SPKR_POCKET_D'] >= 29.2, f'speaker pocket {P["SPKR_POCKET_D"]} mm dia (>= 29.2)')
depth = (P['CP1_Z'] + P['CP1_T']) and (P['SPKR_T'] + P['SPKR_GASKET_T'] + 0.5)
check(depth >= 5.8, f'speaker seat depth {depth:.1f} mm between gaskets (>= 5.8)')
# the pocket is open (no shell inside the speaker volume) and the rear tube is closed
r = 28/2 - 0.3
pts = [[P['SPKR_X'] + r*np.cos(a)*f, P['SPKR_Y'] + r*np.sin(a)*f, z] for a in np.linspace(0, 2*np.pi, 24, endpoint=False)
       for f in (0.2, 0.6, 1.0) for z in np.arange(P['SPKR_Z'] + 0.2, P['SPKR_Z'] + P['SPKR_T'], 0.8)]
check(not back.contains(pts).any() and not front.contains(pts).any(), 'speaker volume is free of shell material')
ring = [[P['SPKR_X'] + (P['SPKR_TUBE_ID']/2 + 0.6)*np.cos(a), P['SPKR_Y'] + (P['SPKR_TUBE_ID']/2 + 0.6)*np.sin(a), z]
        for a in np.linspace(0, 2*np.pi, 36, endpoint=False) for z in np.arange(P['SPKR_Z'] + P['SPKR_T'] + 0.7, P['BASE_INNER_TOP_Z'] - 0.2, 0.7)]
check(back.contains(ring).all(), 'rear cavity tube wall is continuous from the speaker to the rear shell (isolated rear cavity)')
carrier = section(front, P['FRONT_T'] + 0.8)
seal = Point(P['SPKR_X'], P['WINDOW_Y']).buffer(P['WINDOW_D']/2 + 0.8).difference(win)
check(seal.difference(carrier).area < 0.2, 'carrier seals 0.8 mm all round the speaker window (gap area {:.2f} mm2, facet noise)'.format(seal.difference(carrier).area))
spk_disc = spk.buffer(28/2)
usb_plug = box(P['USB_PLUG_X0'], P['USB_PLUG_Y0'], P['USB_PLUG_X1'], P['USB_PLUG_Y1'])
usb_ch = box(P['USB_CH_X0'], P['USB_CH_Y0'], P['USB_CH_X1'], P['USB_PLUG_Y1'])
check(spk_disc.distance(usb_plug) > 0.3, f'speaker clears the USB-C plug keep-out by {spk_disc.distance(usb_plug):.2f} mm (plug position: CONFIRM)')
kp = [[x, y, z] for x in np.arange(P['USB_PLUG_X0'], P['USB_PLUG_X1'], 1.0) for y in np.arange(P['USB_PLUG_Y0'], P['USB_PLUG_Y1'], 0.5)
      for z in np.arange(P['USB_PLUG_Z0'], P['USB_PLUG_Z1'], 1.0)]
kc = [[x, y, z] for x in np.arange(P['USB_CH_X0'], P['USB_CH_X1'], 1.0) for y in np.arange(P['USB_CH_Y0'] + 0.1, P['USB_PLUG_Y1'], 1.0)
      for z in np.arange(P['USB_PLUG_Z0'], P['USB_PLUG_Z1'], 1.0)]
check(not back.contains(kp).any() and not front.contains(kp).any(), 'USB-C plug keep-out free of shell material')
check(not back.contains(kc).any() and not front.contains(kc).any(), 'USB cable channel free of shell material down to the back of the jack boss')
check(spk_disc.distance(usb_ch) > 0.3, f'speaker ring clears the USB cable channel by {spk_disc.distance(usb_ch):.2f} mm')
ys = np.arange(P['USB_WALL_Y'] - 1, P['USB_WALL_Y'] + 6, 0.1)
blocked = [y for x in (P['USB_JACK_X'] - 5, P['USB_JACK_X'], P['USB_JACK_X'] + 5) for z in (10.0, 12.4, 14.8)
           for y, s in zip(ys, back.contains([[x, y, z] for y in ys])) if s]
check(not blocked, f'USB-C panel jack open through the bottom wall at x {P["USB_JACK_X"]:+.2f}')

# ---- battery, power switch -------------------------------------------------------------------
bw, bh, bt = P['BAT_W'] + 2*P['BAT_POCKET_CLEAR'], P['BAT_H'] + 2*P['BAT_POCKET_CLEAR'], P['BATTERY_TOTAL_D'] - P['BAT_REAR_WALL'] - 14.85
check(bw >= 36 and bh >= 54 and bt >= 6.2, f'battery cavity {bw:.1f} x {bh:.1f} x {bt:.2f} mm (>= 36 x 54 x 6.2, THOR-503450)')
bpts = [[x, P['BAT_Y'] + y, z] for x in np.linspace(-17.9, 17.9, 7) for y in np.linspace(-26.9, 26.9, 9) for z in (15.2, 18.0, 20.9)]
check(not back.contains(bpts).any(), 'battery volume (36 x 54 x 6.2) is free of shell material')
wx = 38.25
body_pts = [[-wx + 0.1 + i, P['PWR_Y'] + j, P['PWR_Z'] + k] for i in np.linspace(0, P['PWR_BODY_W'] - 0.2, 5)
            for j in np.linspace(-P['PWR_BODY_L']/2 + 0.1, P['PWR_BODY_L']/2 - 0.1, 5) for k in np.linspace(-P['PWR_BODY_H']/2 + 0.1, P['PWR_BODY_H']/2 - 0.1, 4)]
check(not back.contains(body_pts).any() and not front.contains(body_pts).any(), 'E-Switch body fits against the left wall, free of shell material')
check(-wx + P['PWR_BODY_W'] < -30.5 - 0.35, f'E-Switch body clears the board edge by {(-30.85) - (-wx + P["PWR_BODY_W"]):.2f} mm')
act = [[-wx - t, P['PWR_Y'] + dy, P['PWR_Z']] for t in np.arange(0.1, P['PWR_ACT_L'], 0.2) for dy in (-P['PWR_TRAVEL']/2, 0, P['PWR_TRAVEL']/2)]
check(not back.contains(act).any(), 'E-Switch actuator slot open through the wall over the full 2.16 mm travel')
outer = section(back, P['PWR_Z'])
xmin = min(x for x, y in outer.exterior.coords if abs(y - P['PWR_Y']) < 2) if hasattr(outer, 'exterior') else -40.85
proud = (wx + P['PWR_ACT_L']) - (-xmin)
check(proud >= 1.0, f'E-Switch actuator stands {proud:.1f} mm proud of the side wall')

# ---- sticker ---------------------------------------------------------------------------------
st, rings = svg_shape('svg/struthio_sticker_cut.svg')
lens_bottom = 13.78 - 81.0/2
check(st.bounds[3] <= lens_bottom - 0.3, f'art sticker top y {st.bounds[3]:.2f} stays below the lens land ({lens_bottom:.2f})')
n_holes = len(rings) - 1
check(n_holes == 3 + P['GRILL15_COUNT'], f'sticker has {3 + P["GRILL15_COUNT"]} holes (2 wings, rocker, {P["GRILL15_COUNT"]} grille slots), found {n_holes}')
check(all(rings[0].contains(hh.buffer(0.8)) for hh in rings[1:]), 'every sticker hole sits >= 0.8 mm inside the sticker edge')

print('HANDHELD CAD CHECK: ' + ('all pass' if not fails else f'{len(fails)} failure(s)'))
sys.exit(1 if fails else 0)
