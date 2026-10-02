#!/usr/bin/env python3
"""STRUTHIO ONE · the handheld built around one plug-in board.

Design frame: x to the right and y up as seen from the FRONT, z into the case
(z = 0 is the front face, z = DEPTH the back face). Units: mm.

What goes in the case, front to back (see docs/STRUTHIO_ONE.md):
  face panel    z 0 .. 1.0         1 mm clear acrylic, art printed on its back (laser-cut, not printed)
  front shell   z 1.0 .. Z_SPLIT   0.8 mm face, screen window, key collars, bosses
  Waveshare     z 1.8 .. 13.3      glass on the front skin, board back + socket at 13.3
  ONE board     z 15.8 .. 17.4     on the 2.5 mm header body, keys and switch on its front
  battery       z 13.5 .. 18.7     on the Waveshare board's back, beside the ONE strip
  speaker       z 15.7 .. 21.2     the Waveshare's own boxed speaker, firing out the back
  back shell    z Z_SPLIT .. 23

    python3 one_cad.py           writes stl/*.stl (printed parts are mirrored: see HANDEDNESS)
"""
import math, os, sys
import numpy as np
import manifold3d as mf
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
CS, M = mf.CrossSection, mf.Manifold

# ---- body ------------------------------------------------------------------------------------------
DEPTH = 23.0            # overall thickness (front face to back face)
UPPER_W = 65.0          # upper body: straight sides from Y_STRAIGHT up
Y_TOP = 64.0            # flat top, soft corners
R_TOP = 9.0
Y_STRAIGHT = -30.0      # the sides are straight from here up
LOWER_W = 74.0          # controller section: a gentle flare from the 65 mm upper body
Y_BOTTOM = -72.0        # lowest point (bottom corners); the bottom edge is gently concave
FILLET_WAIST = 6.0      # concave fillet where the straight sides meet the flare
RF = 2.0                # front edge radius
RB = 5.0                # back edge radius
WALL = 1.75             # side wall (board 61.0 in a 65.0 body)
FRONT_SKIN = 1.8        # front face thickness over the glass
BACK_WALL = 1.8
Z_SPLIT = 12.0          # front shell / back shell
# ---- face panel: one laser-cut 1.0 mm clear acrylic piece, art printed on its back (panel/) ---------------
# It is the front face: lens over the screen, the art round it, and its cut-outs round the keys make
# 1 mm wells. The printed shell face sits PANEL_T back, so the case is still DEPTH thick overall.
PANEL_T = 1.0
PANEL_INSET = RF + 0.4  # panel edge inside the body outline (on the flat, clear of the edge round-over)
WELL = 1.6              # panel cut-out beyond each key cap

# ---- Waveshare ESP32-S3-Touch-LCD-3.5B (docs/HARDWARE_FACTS.md) --------------------------------------
BW, BH, BR = 61.0, 92.44, 6.0          # glass outline
BCY = Y_TOP - 4.0 - BH / 2             # 13.78: board centre (top edge at y 60.0)
Z_GLASS = FRONT_SKIN                   # glass front
Z_BACK = Z_GLASS + 11.5                # 13.3: socket face and standoff tips
AA_W, AA_H = 48.96, 73.44              # active area, centred on the board
HOLE_DX, HOLE_DY = 24.25, 36.0         # M2 standoffs at (±24.25, BCY ± 36.0)
# portrait, USB-C edge up. Seen from the front: header J8 on the right side,
# pin 1 (BAT) at the top, odd pins on the row nearer the edge.
HDR_ROW_X = (21.93, 24.47)             # even row, odd row (measured, ±0.5)
HDR_PIN1_Y = BCY + 19.05
USB_X, USB_Z = 0.0, Z_GLASS + 8.72     # board USB-C: centre (Waveshare 3D model: 6.69-10.75 behind the glass)
SIDE_KEYS_Y = {'PWR': BCY + 25.0, 'RST': BCY + 16.5, 'BOOT': BCY + 8.0}   # on the left edge
SPK_J9 = (-26.0, BCY + 0.4)            # speaker socket (PH1.25) near the left edge

# ---- ONE board -------------------------------------------------------------------------------------
# J1, HCTL PZ254-2-16-Z-8.5 (LCSC C2894977): 6.0 mm mating pins, 2.54 mm plastic, 3.0 mm tail. Mounted the
# standard way (plastic on the ONE board's front face, tail through it), as any assembler fits it. The case
# sets the depth: the ONE board rests on the front shell's bosses, so the pins go HDR_INSERT into the
# Waveshare's ~4 mm J8 socket and the plastic stands clear of the socket.
HDR_MATE, HDR_BODY, HDR_TAIL = 6.0, 2.54, 3.0
HDR_INSERT = 3.3                       # pin depth in the socket (socket ~4.0 deep; +-0.3 board stack tolerance)
Z_ONE = Z_BACK + (HDR_MATE - HDR_INSERT) + HDR_BODY    # 18.54: ONE front face
ONE_T = 1.6
STRIP_X = (16.5, 29.4)                 # strip under the header, down the right side
STRIP_TOP = HDR_PIN1_Y + 3.6           # 36.4
PLATE_TOP = -33.5                      # plate below the Waveshare board (bottom edge -32.44)

# ---- controls (visible geometry frozen from the handheld design) -----------------------------------
WING_X, WING_Y, BTN_D = 18.0, -41.7, 14.0  # flap up-left / up-right, both = straight up: round caps, a wing engraved in each
KEY_OUT, KEY_W = 0.75, 1.6                # anti-turn key on each wing cap (in a slot in its collar)
GLYPH_DEPTH = 0.5                      # engraved wing on the cap top (paint-fill it, or leave it as a shadow)
ROCKER_W, ROCKER_H, ROCKER_R, ROCKER_Y = 44.0, 7.2, 3.0, -59.0
DART_X = 16.0                          # rocker-end switches (under the cap ends)
KEY_CLEAR = 0.45                       # opening around a cap
COLLAR_T, COLLAR_Z = 1.6, 6.0          # guide collar: wall, depth (z FRONT_SKIN .. COLLAR_Z)
WING_PROUD, ROCKER_PROUD = 1.8, 1.5
FLANGE = 1.0                           # cap flange beyond the cap outline
SW_H = 1.5                             # TS-1187A-B-A-B: 5.1 x 5.1 x 1.5, travel 0.25
PRETRAVEL = 0.3                        # stem tip above the switch at rest
AXLE_D, AXLE_Z = 1.75, 3.9             # rocker axle: a piece of 1.75 mm filament
ROCKER_GAP = 0.9                       # rocker flange below the collar at rest (room to rock)

# ---- power switch: G-Switch SS-12D06-G030 (right angle), on the plate's left edge --------------------
PSW_Y = -50.0
PSW_LEN, PSW_DEPTH, PSW_H = 12.7, 6.4, 6.6
PSW_KNOB, PSW_KNOB_OUT, PSW_TRAVEL = 3.9, 3.0, 2.2
# ---- battery and speaker ------------------------------------------------------------------------------
BAT = dict(x0=-21.0, x1=13.0, y0=6.5, y1=58.5, z0=Z_BACK + 0.2, t=5.2)    # THOR-503450 5 x 34 x 52 (+0.2)
PH_SOCK = (2.0, -38.0)
# small parts on the ONE board's front face (pcb/one): Q1 reverse-battery FET in the battery line; Q2, C1, R1, D1
# hold the Waveshare's PWR key (header pin 24) down for a few seconds whenever the slide switch turns on,
# because on battery alone its AXP2101 waits for that key before it connects the battery (datasheet 6.5.2)
SMD_PARTS = {'Q1': (-7.0, -38.0), 'C1': (22.2, -10.0), 'R1': (22.1, -12.0), 'D1': (22.2, -14.0), 'Q2': (22.6, -17.0)}
SMD_H = 1.3
# the battery lead: out of the cell's bottom end, down the Waveshare's back between the speaker and the ONE strip,
# to the plug in J2 (entry facing +x, so the lead leaves the plug toward the right and turns up)
LEAD_CHANNEL = dict(x0=2.0, x1=15.5, y0=-33.0, y1=BAT['y0'], z0=Z_BACK + 0.1, z1=Z_BACK + 2.2)                 # JST S2B-PH-K-S pin 1 on the plate; entry faces right (+x)
# The speaker that comes with the Waveshare: its size is not published. The back shell gives it the whole free
# space (bounded by the battery, the battery lead's channel, the ONE plate and a peg post) as a shallow bay,
# and double-sided tape holds whatever box arrives. SPK is a typical 30 x 20 x 5.6 box drawn in the bay.
SPK_BAY = dict(x0=-21.0, x1=1.0, y0=-31.8, y1=5.6, t=7.5)
SPK = dict(x0=-20.0, x1=0.0, y0=-28.1, y1=1.9, t=5.6)
# ---- screws ---------------------------------------------------------------------------------------------
LOWER_SCREWS = [(-29.5, -62.5), (29.5, -62.5)]
PLATE_POSTS = [(-29.0, -36.5), (29.0, -36.5)]
PILOT_D, CLEAR_D, CBORE_D = 1.7, 2.4, 4.2
SCREW_L, SCREW_HEAD = 8.0, 1.6                # M2 x 8 pan head (ISO 7045: head 1.6 high, 3.8 across)
SCREW_SEAT = DEPTH - SCREW_HEAD - 0.2        # head 0.2 below the back face
HOOK_X, HOOK_W = 19.0, 8.0

# The Waveshare is not screwed: the back shell's posts locate it with pegs in its standoffs (threaded M2 SMT
# standoffs in Waveshare's 3D model, 4 mm tall: the pegs are thin enough for a thread), and a foam pad behind
# the battery presses battery and board against the front shell. (The ONE SLIM screws into them.)
POST_GAP, PEG_D, PEG_LEN = 0.3, 1.4, 1.0   # the Waveshare 3D model shows M2 threaded standoffs (minor dia ~1.57): the peg fits inside the thread
WS_HOLE_D = 2.2                        # M2 clearance hole in the Waveshare board (confirm: 2.2-2.5)
FOAM_T = 3.0                           # foam pad behind the battery (compresses into the gap)

def standoffs():
    return [(sx * HOLE_DX, BCY + sy * HOLE_DY) for sx in (-1, 1) for sy in (1, -1)]

def peg_posts():
    """three of the four holes get a post and peg; the lower-right one sits under the header strip, where the
    header itself holds that corner and the strip's tracks need the room"""
    return [(x, y) for x, y in standoffs() if not (x > 0 and y < BCY)]

# =========================================================================================================
# 2D
# =========================================================================================================
def cr(points, k=16):
    """closed Catmull-Rom spline through points"""
    p = np.asarray(points, float); n = len(p); out = []
    for i in range(n):
        p0, p1, p2, p3 = p[i - 1], p[i], p[(i + 1) % n], p[(i + 2) % n]
        for t in np.linspace(0, 1, k, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)

def poly(pts):
    """CrossSection from one ring, either orientation"""
    pts = [tuple(map(float, q)) for q in pts]
    if _area(pts) < 0: pts = pts[::-1]
    return CS([pts])

def rrect(w, h, r, cx=0.0, cy=0.0, n=24):
    pts = []
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = cx + sx * (w / 2 - r), cy + sy * (h / 2 - r)
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return CS([pts])

def lower_half():
    """right half of the controller section, from the straight side round to the bottom centre"""
    h, H = UPPER_W / 2, LOWER_W / 2
    return [(0.0, Y_STRAIGHT + 16), (16.0, Y_STRAIGHT + 16), (h, Y_STRAIGHT + 16), (h, Y_STRAIGHT + 10), (h, Y_STRAIGHT + 5),
            (h, Y_STRAIGHT), (h + 0.5, Y_STRAIGHT - 2.6), (h + 1.6, Y_STRAIGHT - 5.4), (H - 1.6, -39.0), (H - 0.4, -43.0),
            (H, -48.0), (H, -56.0), (H - 0.5, -65.5), (H - 2.2, -70.4), (H - 7.5, -72.0), (16.0, -71.0), (0.0, -70.6)]

def body2d():
    half = lower_half()                                   # top centre clockwise to the bottom centre
    ring = half + [(-x, y) for x, y in reversed(half[1:-1])]
    lower = poly(cr(ring)) ^ CS.square([200, Y_STRAIGHT + 9 - Y_BOTTOM]).translate([-100, Y_BOTTOM])  # flare only: the spline
    lower = lower + rrect(UPPER_W, 12.0, 0.0, 0, Y_STRAIGHT + 4)        # overshoots at its top corner, the sides are drawn straight
    upper = rrect(UPPER_W, Y_TOP - (Y_STRAIGHT - 6), R_TOP, 0, (Y_TOP + Y_STRAIGHT - 6) / 2)
    b = upper + lower
    b = b.offset(FILLET_WAIST, mf.JoinType.Round).offset(-FILLET_WAIST, mf.JoinType.Round)   # waist fillet
    return b.offset(-3, mf.JoinType.Round).offset(3, mf.JoinType.Round)

def wing2d(side, delta=0.0):
    """wing button outline (side -1 = player's left): a round cap"""
    return circle(BTN_D + 2 * delta, side * WING_X, WING_Y, 96)

def glyph2d(side):
    """the wing engraved in a cap: three feathers, round and full at the outer tip, tapering to a point low
    on the inner side (side -1 = player's left: the wing reaches up and out to the left)"""
    r = BTN_D / 2
    out = CS()
    for base, ctl, tip, wmax in (((0.50, -0.18), (-0.02, 0.02), (-0.54, 0.52), 0.30),
                                 ((0.46, -0.44), (-0.04, -0.28), (-0.50, 0.12), 0.26),
                                 ((0.38, -0.68), (0.00, -0.56), (-0.36, -0.28), 0.21)):
        t = np.linspace(0, 1, 48)[:, None]
        base, tip, ctl = np.array(base), np.array(tip), np.array(ctl)
        sp = (1 - t) ** 2 * base + 2 * (1 - t) * t * ctl + t ** 2 * tip            # spine (quadratic Bezier)
        d = np.gradient(sp, axis=0); d /= np.linalg.norm(d, axis=1)[:, None]
        n = np.c_[-d[:, 1], d[:, 0]]
        w = wmax * np.clip(t[:, 0], 0, 1) ** 0.8 / 2                                  # a point where they meet, full at the tip
        ring = np.vstack([sp + n * w[:, None], (sp - n * w[:, None])[::-1]])
        f = poly(ring) + CS.circle(wmax / 2, 32).translate(list(map(float, tip)))    # round tip
        for pg in f.to_polygons(): out += poly([(-side * x * r + side * WING_X, y * r + WING_Y) for x, y in pg])
    return out

def dart_glyph2d():
    """engraved on the rocker: a double-ended dart through an aiming reticle (press an end: dart that way)"""
    y = ROCKER_Y
    g = circle(5.2, 0, y, 64) - circle(3.8, 0, y, 64) + circle(1.2, 0, y, 32)
    for sx in (-1, 1):
        g += rrect(11.6, 0.9, 0.45, sx * 9.4, y)                                  # shaft
        g += poly([(sx * 19.6, y), (sx * 15.2, y + 2.3), (sx * 16.0, y), (sx * 15.2, y - 2.3)])   # head
    return g

def rocker2d(delta=0.0):
    return rrect(ROCKER_W + 2 * delta, ROCKER_H + 2 * delta, ROCKER_R + delta, 0, ROCKER_Y)

def keys2d(delta):
    return wing2d(-1, delta) + wing2d(1, delta) + rocker2d(delta)

def circle(d, x=0.0, y=0.0, n=48):
    return CS.circle(d / 2, n).translate([x, y])

def panel2d():
    """face panel: the body inset PANEL_INSET, minus the key wells"""
    p = body2d().offset(-PANEL_INSET, mf.JoinType.Round) - keys2d(WELL)
    return p.offset(-0.8, mf.JoinType.Round).offset(0.8, mf.JoinType.Round)       # no slivers or sharp horns

def board2d(d=0.0):
    return rrect(BW + 2 * d, BH + 2 * d, BR + d, 0, BCY)

def one2d():
    """ONE board outline: the plate below the Waveshare board plus the strip up the right side"""
    inner = body2d().offset(-WALL - 1.2, mf.JoinType.Round)       # clear of the back shell's inner round-over
    plate = inner ^ CS.square([200, PLATE_TOP + 100]).translate([-100, -100])
    strip = rrect(STRIP_X[1] - STRIP_X[0], STRIP_TOP - PLATE_TOP + 2, 1.0, sum(STRIP_X) / 2, (STRIP_TOP + PLATE_TOP - 2) / 2)
    o = (plate + strip).offset(1.0, mf.JoinType.Round).offset(-1.0, mf.JoinType.Round)
    for x, y in LOWER_SCREWS: o = o - circle(CLEAR_D, x, y)
    return o

# =========================================================================================================
# 3D helpers
# =========================================================================================================
def prism(cs, z0, z1):
    return M.extrude(cs, z1 - z0).translate([0, 0, z0])

def box(x0, x1, y0, y1, z0, z1):
    return M.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])

def cyl_z(d, x, y, z0, z1, n=48):
    return M.cylinder(z1 - z0, d / 2, d / 2, n).translate([x, y, z0])

def cyl_y(d, x, z, y0, y1, n=32):
    return M.cylinder(y1 - y0, d / 2, d / 2, n).rotate([-90, 0, 0]).translate([x, y0, z])

def cyl_x(d, y, z, x0, x1, n=32):
    return M.cylinder(x1 - x0, d / 2, d / 2, n).rotate([0, 90, 0]).translate([x0, y, z])

def ring_from(cs, step=0.4):
    """outline as one CCW ring resampled every `step` mm, with outward normals"""
    pts = max(cs.to_polygons(), key=lambda p: abs(_area(p)))
    pts = np.asarray(pts, float)
    if _area(pts) < 0: pts = pts[::-1]
    seg = np.linalg.norm(np.roll(pts, -1, 0) - pts, axis=1)
    s = np.concatenate([[0], np.cumsum(seg)]); n = int(s[-1] / step)
    u = np.linspace(0, s[-1], n, endpoint=False); closed = np.vstack([pts, pts[:1]])
    ring = np.c_[np.interp(u, s, closed[:, 0]), np.interp(u, s, closed[:, 1])]
    tan = np.roll(ring, -2, 0) - np.roll(ring, 2, 0); tan /= np.linalg.norm(tan, axis=1)[:, None]
    return ring, np.c_[tan[:, 1], -tan[:, 0]]

def _area(p):
    p = np.asarray(p); return 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])

def loft(ring, normal, prof):
    n = len(ring); verts, faces = [], []
    for r, z in prof: verts.extend(np.c_[ring + r * normal, np.full(n, z)])
    m = len(prof)
    for j in range(m - 1):
        a, b = j * n, (j + 1) * n
        for i in range(n):
            i2 = (i + 1) % n
            faces.append((a + i, a + i2, b + i2)); faces.append((a + i, b + i2, b + i))
    lo, hi = 0, (m - 1) * n
    for t in mf.triangulate([ring + prof[0][0] * normal]): faces.append((lo + t[0], lo + t[2], lo + t[1]))
    for t in mf.triangulate([ring + prof[-1][0] * normal]): faces.append((hi + t[0], hi + t[1], hi + t[2]))
    man = M(mf.Mesh(vert_properties=np.asarray(verts, np.float32), tri_verts=np.asarray(faces, np.uint32)))
    if man.status() != mf.Error.NoError or man.volume() <= 0: sys.exit(f'loft failed: {man.status()}')
    return man

K = RB  # the core outline sits RB inside the body; every station grows it back out
def profile_out():
    p = [(K - RF + math.sqrt(max(0.0, RF * RF - (RF - z) ** 2)), PANEL_T + z) for z in np.linspace(0, RF, 9)]
    p += [(K - RB + RB * math.cos(a), DEPTH - RB + RB * math.sin(a)) for a in np.linspace(0, math.pi / 2, 17)]
    return p

def profile_in():
    rr, rz = RB - WALL, RB - BACK_WALL
    p = [(K - WALL, FRONT_SKIN)]
    p += [(K - RB + rr * math.cos(a), DEPTH - RB + rz * math.sin(a)) for a in np.linspace(0, math.pi / 2, 17)]
    return p

_CACHE = {}
def skins():
    if 'skins' not in _CACHE:
        ring, normal = ring_from(body2d().offset(-K, mf.JoinType.Round))
        _CACHE['skins'] = (loft(ring, normal, profile_out()), loft(ring, normal, profile_in()))
    return _CACHE['skins']

# =========================================================================================================
# parts
# =========================================================================================================
def key_collars():
    opening = keys2d(KEY_CLEAR)
    ring = opening.offset(COLLAR_T, mf.JoinType.Round) - opening
    c = prism(ring, FRONT_SKIN - 0.01, COLLAR_Z)
    for side in (-1, 1):                                                # key slots: the round wing caps cannot turn
        c -= key_box(side, 0.3, 0.2, FRONT_SKIN + 0.01, COLLAR_Z + 0.1)
    return c

def key_box(side, dr, dw, z0, z1):
    """the wing cap's anti-turn key (dr, dw = clearance round it), on the outer side of the cap"""
    r = BTN_D / 2; cx = side * WING_X
    x0, x1 = (cx + side * (r - 0.6), cx + side * (r + KEY_OUT + dr))
    return box(min(x0, x1), max(x0, x1), WING_Y - KEY_W / 2 - dw, WING_Y + KEY_W / 2 + dw, z0, z1)

def rocker_axle_hole():
    y0 = ROCKER_Y - ROCKER_H / 2 - KEY_CLEAR - COLLAR_T + 0.8          # blind in the bottom collar wall
    y1 = ROCKER_Y + ROCKER_H / 2 + KEY_CLEAR + COLLAR_T + 0.5
    return cyl_y(AXLE_D + 0.15, 0, AXLE_Z, y0, y1)

def front_shell():
    outer, inner = skins()
    shell = (outer ^ box(-100, 100, -100, 100, -1, Z_SPLIT)) - inner
    add = key_collars()
    for sx in (-1, 1):                                                  # board locating ribs
        add += box(sx * 11 - 1.0, sx * 11 + 1.0, BCY + BH / 2 + 0.25, Y_TOP - 0.5, FRONT_SKIN - 0.01, 9.0)
    for x in (-26.0, 0.0, 26.0):
        add += box(x - 1.5, x + 1.5, Y_STRAIGHT - 6.0, BCY - BH / 2 - 0.25, FRONT_SKIN - 0.01, 9.0)
    for x, y in LOWER_SCREWS: add += cyl_z(6.0, x, y, FRONT_SKIN - 0.01, Z_ONE)
    for x, y in PLATE_POSTS: add += cyl_z(4.0, x, y, FRONT_SKIN - 0.01, Z_ONE)
    shell = shell + (add ^ inner)
    cut = prism(rrect(AA_W + 0.2, AA_H + 0.2, 1.2, 0, BCY), -1, FRONT_SKIN + 0.05)    # screen window
    cut += prism(keys2d(KEY_CLEAR), -1, COLLAR_Z + 0.1)
    cut += rocker_axle_hole()
    for x, y in LOWER_SCREWS: cut += cyl_z(PILOT_D, x, y, Z_ONE - 6.0, Z_ONE + 0.1)
    cut += shared_cuts()
    for sx in (-1, 1):                                                  # catches for the back shell's hooks
        cut += box(sx * HOOK_X - HOOK_W / 2 - 0.2, sx * HOOK_X + HOOK_W / 2 + 0.2, Y_TOP - BACK_WALL - 0.3, Y_TOP - BACK_WALL + 0.9, 8.8, 10.6)
    return shell - cut

def shared_cuts():
    """openings that cross the split line"""
    c = box(USB_X - 6.4, USB_X + 6.4, BCY + BH / 2 - 0.5, Y_TOP + 2, USB_Z - 3.9, USB_Z + 3.9)      # USB-C plug
    for y in SIDE_KEYS_Y.values():                                                                    # pin holes
        c += box(-UPPER_W / 2 - 2, -26.6, y - 0.8, y + 0.8, Z_GLASS + 7.0, Z_GLASS + 9.4)   # onto the actuators (3D model: 7.1-9.3 behind the glass)
    zc = Z_ONE - PSW_H / 2                                                                            # power slider
    c += box(-LOWER_W / 2 - 3, -LOWER_W / 2 + 6, PSW_Y - PSW_KNOB / 2 - PSW_TRAVEL / 2 - 0.4,
             PSW_Y + PSW_KNOB / 2 + PSW_TRAVEL / 2 + 0.4, min(zc - PSW_KNOB / 2 - 0.3, Z_SPLIT - 0.5), zc + PSW_KNOB / 2 + 0.3)   # open at the split: the back shell closes over the knob
    return c

def wall_x_at(y, side=-1):
    """inner wall x at height y on one side"""
    inner = body2d().offset(-WALL, mf.JoinType.Round)
    probe = inner ^ CS.square([200, 0.02]).translate([-100, y - 0.01])
    b = probe.bounds()
    return b[0] if side < 0 else b[2]

def psw_box():
    """power switch body + knob (the knob side faces the left wall)"""
    xw = max(wall_x_at(PSW_Y + t, -1) for t in np.linspace(-PSW_LEN / 2, PSW_LEN / 2, 9))
    x_front = xw + 0.3                                                   # body face 0.3 inside the wall all along
    z1 = Z_ONE; z0 = z1 - PSW_H; zc = (z0 + z1) / 2
    body = box(x_front, x_front + PSW_DEPTH, PSW_Y - PSW_LEN / 2, PSW_Y + PSW_LEN / 2, z0, z1)
    knob = box(x_front - PSW_KNOB_OUT, x_front, PSW_Y - PSW_KNOB / 2, PSW_Y + PSW_KNOB / 2, zc - PSW_KNOB / 2, zc + PSW_KNOB / 2)
    return body, knob, x_front

def back_shell():
    outer, inner = skins()
    shell = (outer ^ box(-100, 100, -100, 100, Z_SPLIT, DEPTH + 1)) - inner
    add = M()
    zin = DEPTH - BACK_WALL
    for x, y in peg_posts():                                            # posts over the Waveshare's M2 holes:
        add += cyl_z(5.5, x, y, Z_BACK + POST_GAP, zin + 0.01)            # stop just short of its back,
        add += cyl_z(PEG_D, x, y, Z_BACK - PEG_LEN, Z_BACK + POST_GAP + 0.01)   # a peg in each hole locates it
    for x, y in LOWER_SCREWS: add += cyl_z(6.0, x, y, Z_ONE + ONE_T + 0.05, zin + 0.01)
    for x, y in ((18.3, 25.0), (18.3, -20.0)): add += cyl_z(3.5, x, y, Z_ONE + ONE_T + 0.05, zin + 0.01)   # hold the strip
    # battery locators: corners of the bay, from the back down to the battery's back face
    bz = BAT['z0'] + BAT['t'] + 0.3
    for x in (BAT['x0'] - 1.4, BAT['x1'] + 0.2):
        for y in (BAT['y0'] - 1.4, BAT['y1'] + 0.2):
            add += box(x, x + 1.2, y, y + 1.2, bz - 2.0, zin + 0.01)
    # speaker cradle: a frame round the box, the box sits against the back wall
    s = SPK_BAY
    frame = prism(rrect(s['x1'] - s['x0'] + 2.4, s['y1'] - s['y0'] + 2.4, 1.5, (s['x0'] + s['x1']) / 2, (s['y0'] + s['y1']) / 2)
                  - rrect(s['x1'] - s['x0'] + 0.4, s['y1'] - s['y0'] + 0.4, 0.3, (s['x0'] + s['x1']) / 2, (s['y0'] + s['y1']) / 2),
                  zin - 2.0, zin + 0.01)                                # a 2 mm lip round the speaker bay
    add += frame
    for sx in (-1, 1):                                                  # top hooks
        add += box(sx * HOOK_X - HOOK_W / 2, sx * HOOK_X + HOOK_W / 2, Y_TOP - BACK_WALL - 1.2, Y_TOP - BACK_WALL + 0.05, 8.8, Z_SPLIT + 1.0)
        add += box(sx * HOOK_X - HOOK_W / 2 + 0.5, sx * HOOK_X + HOOK_W / 2 - 0.5, Y_TOP - BACK_WALL, Y_TOP - BACK_WALL + 0.7, 9.0, 10.4)
    shell = shell + (add ^ inner) + (add ^ box(-100, 100, Y_TOP - 4, Y_TOP + 1, 8.0, Z_SPLIT + 1))
    cut = shared_cuts()
    for x, y in LOWER_SCREWS:
        cut += cyl_z(CLEAR_D, x, y, Z_ONE, DEPTH + 1) + cyl_z(CBORE_D, x, y, SCREW_SEAT, DEPTH + 1)   # head sunk flush
    cut += box(HDR_ROW_X[0] - 1.6, HDR_ROW_X[1] + 1.6, HDR_PIN1_Y - 15 * 2.54 - 1.6, HDR_PIN1_Y + 1.6, zin - 0.05, zin + 0.8)  # header tails
    for i in range(7):                                                  # speaker grille
        x = s['x0'] + 2.2 + i * (s['x1'] - s['x0'] - 4.4) / 6
        cut += prism(rrect(1.4, s['y1'] - s['y0'] - 4.0, 0.7, x, (s['y0'] + s['y1']) / 2), zin - 0.1, DEPTH + 1)
    return shell - cut

def wing_cap(side):
    w = wing2d(side)
    cap = prism(w, -WING_PROUD, COLLAR_Z) + prism(wing2d(side, FLANGE), COLLAR_Z, COLLAR_Z + 1.0)
    cap -= prism(glyph2d(side), -WING_PROUD - 0.1, -WING_PROUD + GLYPH_DEPTH)
    cap += key_box(side, 0.0, 0.0, FRONT_SKIN + 0.3, COLLAR_Z - 0.2)
    tip = Z_ONE - SW_H - PRETRAVEL
    cap += cyl_z(4.0, side * WING_X, WING_Y, COLLAR_Z + 0.5, tip)
    return cap

def rocker_cap():
    z0 = COLLAR_Z + ROCKER_GAP
    cap = prism(rocker2d(), -ROCKER_PROUD, z0) + prism(rocker2d(FLANGE), z0, z0 + 1.0)
    tip = Z_ONE - SW_H - PRETRAVEL
    for sx in (-1, 1): cap += cyl_z(4.0, sx * DART_X, ROCKER_Y, z0 + 0.5, tip)
    cap -= prism(dart_glyph2d(), -ROCKER_PROUD - 0.1, -ROCKER_PROUD + GLYPH_DEPTH)
    return cap - cyl_y(AXLE_D + 0.05, 0, AXLE_Z, ROCKER_Y - 10, ROCKER_Y + 10)

def ref_glyphs():
    """render only: the engraved wings, filled (paint)"""
    g = sum((prism(glyph2d(s), -WING_PROUD + 0.02, -WING_PROUD + GLYPH_DEPTH) for s in (-1, 1)), M())
    return g + prism(dart_glyph2d(), -ROCKER_PROUD + 0.02, -ROCKER_PROUD + GLYPH_DEPTH)

def ref_foam():
    """render only: the foam pad on the battery, as fitted (compressed into the gap)"""
    b = BAT; z0 = b['z0'] + b['t']
    return box(b['x0'] + 2, b['x1'] - 2, b['y0'] + 3, b['y1'] - 3, z0, DEPTH - BACK_WALL - 0.05)

def face_panel():
    return prism(panel2d(), 0.0, PANEL_T)

def one_board():
    return prism(one2d(), Z_ONE, Z_ONE + ONE_T)

# ---- reference volumes (for checks and renders) --------------------------------------------------------
def ref_waveshare():
    m = prism(board2d(), Z_GLASS, Z_BACK)
    for x, y in standoffs(): m -= cyl_z(WS_HOLE_D, x, y, Z_BACK - 1.6, Z_BACK + 0.1)   # the M2 holes in its PCB
    return m

def ref_battery():
    b = BAT; return box(b['x0'], b['x1'], b['y0'], b['y1'], b['z0'], b['z0'] + b['t'])

def ref_speaker():
    s = SPK; zin = DEPTH - BACK_WALL
    return box(s['x0'], s['x1'], s['y0'], s['y1'], zin - s['t'], zin)

def switch_xy():
    return {'LEFT': (-WING_X, WING_Y), 'RIGHT': (WING_X, WING_Y), 'DART_L': (-DART_X, ROCKER_Y), 'DART_R': (DART_X, ROCKER_Y)}

def ref_switches():
    m = M()
    for x, y in switch_xy().values(): m += box(x - 2.55, x + 2.55, y - 2.55, y + 2.55, Z_ONE - SW_H, Z_ONE)
    return m

def ref_smd():
    m = M()
    for x, y in SMD_PARTS.values(): m += box(x - 1.5, x + 1.5, y - 1.5, y + 1.5, Z_ONE - SMD_H, Z_ONE)
    return m

def ref_header():
    y1 = HDR_PIN1_Y + 1.27; y0 = HDR_PIN1_Y - 15 * 2.54 - 1.27
    body = box(HDR_ROW_X[0] - 1.27, HDR_ROW_X[1] + 1.27, y0, y1, Z_ONE - HDR_BODY, Z_ONE)
    body += box(HDR_ROW_X[0] - 0.4, HDR_ROW_X[1] + 0.4, y0 + 0.9, y1 - 0.9, Z_BACK, Z_ONE - HDR_BODY)   # pins, to the socket face
    tails = box(HDR_ROW_X[0] - 0.4, HDR_ROW_X[1] + 0.4, y0 + 0.9, y1 - 0.9, Z_ONE + ONE_T, Z_ONE + HDR_TAIL)
    return body, tails

def ref_ph_socket(plug=True):
    """S2B-PH-K-S body (rotated 90: pins on a vertical line, pin 2 2 mm above pin 1) and the mated plug"""
    x, y = PH_SOCK
    m = box(x - 1.46, x + 6.36, y - 2.06, y + 4.06, Z_ONE - 6.0, Z_ONE)
    if plug: m += box(x + 6.36, x + 12.5, y - 1.9, y + 3.9, Z_ONE - 5.6, Z_ONE - 0.4)
    return m

# =========================================================================================================
# export
# =========================================================================================================
def physical(man):
    """HANDEDNESS: the design frame (x right seen from the front, z INTO the case) is a
    left-handed view, so the real part is its mirror image in x. Every STL is written
    physical; to look at a part from the front, view it from -z (screen right = -x)."""
    return man.mirror([1, 0, 0])

def write(man, path, keep_all=False):
    man = physical(man).simplify(0.01)
    if not keep_all: man = max(man.decompose(), key=lambda m: m.volume())
    mesh = man.to_mesh()
    trimesh.Trimesh(vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts).export(path)
    return man

PARTS = {
    'one_front': front_shell, 'one_back': back_shell,
    'one_wing_left': lambda: wing_cap(-1), 'one_wing_right': lambda: wing_cap(1), 'one_rocker': rocker_cap,
}

REFS = {
    'ref_panel': face_panel, 'ref_glyphs': ref_glyphs, 'ref_foam': ref_foam, 'ref_waveshare': ref_waveshare, 'ref_one': one_board, 'ref_battery': ref_battery, 'ref_speaker': ref_speaker,
    'ref_switches': lambda: ref_switches() + psw_box()[0] + psw_box()[1] + ref_ph_socket() + ref_header()[0] + ref_smd(),
}

def main(names=None):
    os.makedirs(os.path.join(HERE, 'stl'), exist_ok=True)
    for name, fn in PARTS.items():
        if names and name not in names: continue
        man = write(fn(), os.path.join(HERE, 'stl', name + '.stl'))
        b = man.bounding_box()
        print(f'{name:16s} {man.volume() / 1000:6.1f} cm3  {b[3] - b[0]:6.1f} x {b[4] - b[1]:6.1f} x {b[5] - b[2]:5.1f} mm')
    os.makedirs(os.path.join(HERE, 'refs'), exist_ok=True)
    for name, fn in REFS.items():
        if names and name not in names: continue
        write(fn(), os.path.join(HERE, 'refs', name + '.stl'), keep_all=True)

if __name__ == '__main__':
    main(sys.argv[1:])
