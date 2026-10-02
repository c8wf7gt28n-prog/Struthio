#!/usr/bin/env python3
"""STRUTHIO ONE SLIM · the 16.5 mm case.

    python3 slim_cad.py            writes stl/*.stl (printed parts) and refs/*.stl (bought parts, for checks and renders)

The SLIM keeps the ONE's outline, face panel, keys and controls (one_cad.py, imported) and rebuilds the depth:

  0.0  - 1.0   face panel (1.0 mm acrylic, unchanged)
  1.0  - 1.5   0.5 mm shell rim over the glass border (the glass sits in a pocket in the 1.6 mm face)
  1.5  - 14.1  Waveshare: glass front to the top of its J8 socket (Waveshare 3D model: 12.6 mm)
  14.1 - 14.9  ONE SLIM board, 0.8 mm, on the front shell's bosses; 12 bare header pins stand 3.6 mm out of it
               (they go 3.6 mm into J8 if its top is 12.6 mm behind the glass, 2.5 mm if it is 11.5: both work)
  14.9 - 15.0  clearance
  15.0 - 16.5  back wall, 1.5 mm

Behind the Waveshare (its back parts stand at most 9.5 mm behind the glass, Waveshare 3D model) there is a
3.7 mm deep bay: a 3.0 mm LiPo (302535, 250 mAh; a 303450, about 500 mAh, fits the same bay) and a
plug-in cavity speaker (about 15 x 10 x 3.6 mm, 0.3 mm clear of the Waveshare's parts). The Waveshare is screwed to the back shell through three
of its own M2 standoffs (SMTSO-M2X4 in the 3D model), and the shells meet in a tongue-and-groove joint.

Rev S2 (foolproof): no slide switch: a printed plunger in the left wall presses the Waveshare's own PWR key
(press: on, hold 4 s: off); one screw size (5 x M2 x 6 countersunk); the battery socket is surface-mount (no
leads to trim); clips hold the leads; a keyed pin jig (with an 11 mm axle gauge) and a panel jig.

Design frame as one_cad: x right seen from the front, y up, z INTO the case from the front face. STLs are
written physical (mirrored in x), like the ONE's.
"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'one'))
import numpy as np
import manifold3d as mf
import one_cad as o
from one_cad import (M, CS, prism, box, cyl_z, rrect, circle, body2d, board2d, keys2d, write, physical,
                     wing2d, rocker2d)

# ---- the stack ----------------------------------------------------------------------------------------------
DEPTH = 16.5
BACK_WALL = 1.5
FRONT_SKIN = 2.6                      # shell face 1.6 mm behind the 1.0 mm panel (the ONE's was 0.8)
RIM = 0.5                             # shell over the glass border, between panel and glass
Z_GLASS = o.PANEL_T + RIM             # 1.5
WS_STANDOFF = 11.5                    # glass front to the M2 standoff tips (drawing: 11.50 overall)
WS_SOCKET = 12.6                      # glass front to the top of J8 (Waveshare 3D model; confirm with calipers)
WS_PARTS = 9.5                        # glass front to the back of every other part under the battery bay
Z_BACK = Z_GLASS + WS_STANDOFF        # 13.0 standoff tips
Z_SOCK = Z_GLASS + WS_SOCKET          # 14.1 socket top
ONE_T = 0.8
Z_ONE = Z_SOCK                        # the board's front face: on the bosses, level with a 12.6 mm socket top
PIN_OUT = 3.6                         # bare pins stand this far out of the board's front (the jig sets it)
WS_SOCKET_LOW = 11.5                  # the other socket height the build must survive (Waveshare's drawing)
ZIN = DEPTH - BACK_WALL               # 15.0 back wall, inside face
Z_SPLIT = 11.0                        # front shell / back shell
RB = 3.0                              # back edge round (the ONE's 5.0 would pull the inside wall in onto the board)

# tongue and groove, as offsets in from the outer surface (the side walls are 1.75 mm; a 1.0 mm land on the
# inside thickens them to 2.75 mm round the joint)
LAND = 1.0
GROOVE = (0.85, 1.85)                 # in the front shell, 1.0 wide, 1.6 deep
TONGUE = (1.00, 1.70)                 # on the back shell, 0.7 wide: 0.15 mm clearance each side (FDM)
GROOVE_DEPTH, TONGUE_LEN = 1.6, 1.5   # 0.1 mm clear at the bottom: the shells close on their faces, not the tongue

# the Waveshare's own parts that stand tallest (Waveshare 3D model, case frame, glass front = 0), for the checks
WS_TALL = {   # name: (x0, x1, y0, y1, height behind the glass front)
    'J8 header socket': (20.4, 25.6, -6.8, 34.4, 12.6),
    'J9 speaker socket': (-24.5, -19.3, 10.6, 18.3, 10.9),
    'J7 battery socket': (20.7, 25.9, 35.2, 42.9, 10.9),
    'J6 RTC cell socket': (20.8, 26.0, 42.9, 47.2, 10.65),
    'USB-C': (-4.47, 4.47, 46.18, 53.78, 10.75),
}
SIDE_SWITCH_Z = (7.1, 9.3)            # the three edge keys' actuators (behind the glass front)
USB_Z = Z_GLASS + 8.72                # USB-C centre (3D model: 6.69 - 10.75 behind the glass)

# battery bay: 3.0 x 34 x 52 (303450 with its protection board); the 302535 (3.0 x 25 x 38) sits in its
# lower-left corner. Foam tape (1.0 mm, double-sided) on its back holds it to the back shell.
BAY = dict(x0=-18.5, x1=15.5, y0=-7.0, y1=45.0, z0=Z_GLASS + WS_PARTS + 0.3, t=3.0)
CELL = dict(x0=-18.5, x1=6.5, y0=-7.0, y1=31.0)            # 302535 as fitted
FOAM_T = 1.0
# the speaker: a 1 W 8 ohm mini cavity speaker with its own lead and 1.25 mm 2-pin plug, straight into J9 (no
# soldering). Listed 15.2 x 10.2 x 3.6 mm (confirm); its pocket takes 15.3 x 11.0 x 3.7, against the back wall
SPK = dict(x0=-18.8, x1=-3.5, y0=-21.5, y1=-10.5, t=3.7)
# the cell lead: along under the bay's bottom edge, then down between two clips to J2 (the battery socket)
LEAD = dict(x0=2.6, x1=6.4, y0=-33.0, y1=BAY['y0'], z0=Z_GLASS + WS_PARTS + 0.1, z1=ZIN)
LEAD_ALONG = dict(x0=-14.4, x1=10.5, y0=-9.0, y1=BAY['y0'] - 0.4, z0=Z_GLASS + WS_PARTS + 0.1, z1=ZIN)
SPK_LEAD = dict(x0=-23.5, x1=-20.0, y0=-17.0, y1=10.6, z0=Z_GLASS + WS_PARTS + 0.1, z1=ZIN)    # speaker lead up to J9

# screws: all M2 countersunk (ISO 10642 / DIN 965), heads flush with the back
CSK_D, CSK_HOLE = 4.0, 2.3
WS_SCREWS = [(x, y) for x, y in o.standoffs() if not (x > 0 and y < o.BCY)]   # three standoffs; the 4th is under the ONE strip
WS_SCREW_L = 6.0
LOWER_SCREW_L = 6.0                   # one screw for the whole case: M2 x 6 countersunk
PILOT_D = o.PILOT_D

# the ONE SLIM's header pins (J8 numbering), two straight strips cut from any 2.54 mm header:
#   odd row 1-7 (BAT, GND, DART L, DART R) and even row 4-18 (GND ... LEFT WING 16, RIGHT WING 18; the others
#   land on empty pads). Pin 9 stays empty: that is how the firmware knows it is a SLIM.
PINS = (1, 3, 5, 7) + tuple(range(4, 19, 2))
# lead clips: pairs of posts from the back wall, the lead pressed between them
CLIPS = [(1.9, -14.0), (7.1, -14.0), (1.9, -26.0), (7.1, -26.0), (-24.2, 4.0), (-19.3, 4.0)]
# the power button: a printed plunger through the left wall onto the Waveshare's PWR key (its actuator ends
# 26.85 mm left of centre, 7.1-9.3 mm behind the glass: Waveshare 3D model)
PWR_Y = o.SIDE_KEYS_Y['PWR']
PWR_KEY_X = -26.85
PLUNGER = dict(head=(3.0, 2.0), proud=0.8, flange=(5.2, 2.55, 0.8), tip=(1.6, 1.3), gap=0.2, hole=0.2)
# J2: JST S2B-PH-SM4-TB, surface-mount side entry (LCSC C295747): body 7.9 x 7.6, 5.0 tall (confirm), entry to +x
J2_BODY = dict(x0=-1.2, x1=6.4, y0=-41.95, y1=-34.05, h=5.0)
Q1_XY = (-7.0, -38.0)

def pin_xy(n):
    """J8 pin n in the case frame: odd pins on the row nearer the edge (one_cad.HDR_ROW_X)"""
    k = (n - 1) // 2
    return (o.HDR_ROW_X[1] if n % 2 else o.HDR_ROW_X[0], o.HDR_PIN1_Y - 2.54 * k)

# ---- rev S3: the finish --------------------------------------------------------------------------------------
# the face panel sits in a pocket: a 1.0 mm lip all round, 2.6 mm wide (its outer edge is the 2 mm front round),
# so the panel's edge is covered and it lines itself up. The panel is cut 0.2 mm smaller than the pocket.
LIP_POCKET = 2.6
PANEL_CLEAR = 0.2
# the back edge: an elliptical round, 3 mm across the back and 5.5 mm up the side (it was a 3 mm circle): the side
# you see is shorter, so the case looks thinner. The inside follows it at WALL_T, so no wall gets thinner.
EDGE_A, EDGE_B = 3.0, 5.5
WALL_T = 1.6
# the buttons: the wings are dished 0.5 mm, the rocker is domed (its ends 0.5 mm lower than its middle); every top
# edge is rounded 0.5 mm; engravings follow the curved tops, 0.4 mm deep
DISH, DOME_SAG, TOP_ROUND, ENGRAVE = 0.5, 0.5, 0.5, 0.4
ROCKER_TOP = -1.8                     # the rocker's middle, 1.8 mm proud (its ends 1.3)
# the back: engraved 0.35 mm
BACK_TEXT = [('STRUTHIO', 4.2, -43.0), ('R.A. PEDDYCOART', 3.0, -50.5)]
TEXT_DEPTH = 0.35

def profile_out():
    """(r, z) outside, r = out from the core ring (K = EDGE_A in from the outline): the lip's 2 mm front round from
    z = 0, straight sides, then the elliptical back edge"""
    K, RF = EDGE_A, o.RF
    p = [(K - RF + math.sqrt(max(0.0, RF * RF - (RF - z) ** 2)), z) for z in np.linspace(0, RF, 9)]
    cz = DEPTH - EDGE_B
    p += [(K - EDGE_A + EDGE_A * math.cos(t), cz + EDGE_B * math.sin(t)) for t in np.linspace(0, math.pi / 2, 33)[1:]]
    return p

def profile_in():
    """the inside: the side wall WALL in, then the back edge's ellipse offset WALL_T square to it, then the back
    wall's inside face at ZIN"""
    K = EDGE_A; cz = DEPTH - EDGE_B
    p = [(K - o.WALL, FRONT_SKIN)]
    for t in np.linspace(0, math.pi / 2, 65):
        nx, nz = math.cos(t) / EDGE_A, math.sin(t) / EDGE_B
        n = math.hypot(nx, nz)
        r = min(EDGE_A * math.cos(t) - WALL_T * nx / n, K - o.WALL)
        z = min(cz + EDGE_B * math.sin(t) - WALL_T * nz / n, ZIN)
        if z > p[-1][1] + 1e-6: p.append((r, z))
    p.append((p[-1][0], ZIN))
    return p

def setup():
    """point one_cad's shared helpers (skins, caps, switch, board outline) at the SLIM stack"""
    for k, v in dict(DEPTH=DEPTH, BACK_WALL=BACK_WALL, FRONT_SKIN=FRONT_SKIN, Z_GLASS=Z_GLASS, Z_BACK=Z_BACK,
                     Z_ONE=Z_ONE, ONE_T=ONE_T, Z_SPLIT=Z_SPLIT, USB_Z=USB_Z, RB=RB, K=EDGE_A,
                     PANEL_INSET=LIP_POCKET + PANEL_CLEAR, profile_out=profile_out, profile_in=profile_in).items():
        setattr(o, k, v)
    o._CACHE.clear()
setup()

def ring2d(a, b):
    """the band between a and b mm in from the outer surface"""
    out = body2d()
    return out.offset(-a, mf.JoinType.Round) - out.offset(-b, mf.JoinType.Round)

def joint_keepout():
    """where the joint's land, groove and tongue stop: the power button, the edge-key pin holes, USB-C"""
    f = PLUNGER['flange']
    k = box(-o.UPPER_W / 2 - 2, PWR_KEY_X, PWR_Y - f[0] / 2 - 0.6, PWR_Y + f[0] / 2 + 0.6, -1, DEPTH + 1)
    return k + shared_cuts()

PLUNGER_Z = Z_GLASS + 8.2                                   # centre of the actuator (7.1-9.3 behind the glass)
def plunger(press=0.0):
    """the power button, at rest (press = 0) or pushed in by press mm"""
    P = PLUNGER; xo = -o.UPPER_W / 2; xi = xo + o.WALL; z = PLUNGER_Z
    hw, hh = P['head']; fw, fh, ft = P['flange']; tw, th = P['tip']
    m = box(xo - P['proud'], xi, PWR_Y - hw / 2, PWR_Y + hw / 2, z - hh / 2, z + hh / 2)                   # head + shank
    m += box(xi, xi + ft, PWR_Y - fw / 2, PWR_Y + fw / 2, z - fh / 2, z + fh / 2)                         # flange
    m += box(xi + ft, PWR_KEY_X - P['gap'], PWR_Y - tw / 2, PWR_Y + tw / 2, z - th / 2 + 0.25, z + th / 2 + 0.25)   # tip, above the board edge
    return m.translate([press, 0, 0])

def plunger_hole():
    P = PLUNGER; hw, hh = P['head']; c = P['hole']
    return box(-o.UPPER_W / 2 - 2, -o.UPPER_W / 2 + o.WALL + 0.01, PWR_Y - hw / 2 - c, PWR_Y + hw / 2 + c, PLUNGER_Z - hh / 2 - c, PLUNGER_Z + hh / 2 + c)

# =========================================================================================================
def shared_cuts():
    """openings that cross the split line"""
    c = box(-6.4, 6.4, o.BCY + o.BH / 2 - 7.0, o.Y_TOP + 2, USB_Z - 3.5, USB_Z + 3.5)          # USB-C plug
    for k, y in o.SIDE_KEYS_Y.items():                                                         # pin holes onto RST and BOOT
        if k == 'PWR': continue                                                                # (PWR has the plunger)
        c += box(-o.UPPER_W / 2 - 2, -26.6, y - 0.8, y + 0.8, Z_GLASS + SIDE_SWITCH_Z[0] - 0.1, Z_GLASS + SIDE_SWITCH_Z[1] + 0.1)
    return c

def front_shell():
    outer, inner = o.skins()
    shell = (outer ^ box(-100, 100, -100, 100, -1, Z_SPLIT)) - inner
    add = o.key_collars()
    for sx in (-1, 1):                                                  # locate the glass top edge
        add += box(sx * 11 - 1.0, sx * 11 + 1.0, o.BCY + o.BH / 2 + 0.25, o.Y_TOP - 0.5, FRONT_SKIN - 0.01, 9.0)
    for x in (-26.0, -3.0, 26.0):                                       # and its bottom edge
        add += box(x - 1.5, x + 1.5, o.Y_STRAIGHT - 6.0, o.BCY - o.BH / 2 - 0.25, FRONT_SKIN - 0.01, 9.0)
    for x, y in o.LOWER_SCREWS: add += cyl_z(6.0, x, y, FRONT_SKIN - 0.01, Z_ONE)
    for x, y in o.PLATE_POSTS: add += cyl_z(4.0, x, y, FRONT_SKIN - 0.01, Z_ONE)
    add += prism(ring2d(o.WALL - 0.01, o.WALL + LAND), Z_SPLIT - GROOVE_DEPTH - 0.6, Z_SPLIT) - joint_keepout()   # joint land
    shell = shell + (add ^ inner)
    cut = prism(rrect(o.AA_W + 0.2, o.AA_H + 0.2, 1.2, 0, o.BCY), -1, Z_GLASS + 0.05)          # screen window in the rim
    cut += prism(board2d(0.25), Z_GLASS, FRONT_SKIN + 0.05)                                    # glass pocket
    cut += prism(keys2d(o.KEY_CLEAR), -1, o.COLLAR_Z + 0.1)
    cut += o.rocker_axle_hole()
    for x, y in o.LOWER_SCREWS: cut += cyl_z(PILOT_D, x, y, Z_ONE - 6.5, Z_ONE + 0.1)
    cut += shared_cuts() + plunger_hole() + chamfers()
    cut += prism(body2d().offset(-LIP_POCKET, mf.JoinType.Round), -1, o.PANEL_T)              # the panel's pocket
    cut += prism(ring2d(*GROOVE), Z_SPLIT - GROOVE_DEPTH, Z_SPLIT + 0.1)                     # the groove
    cut += prism(ring2d(GROOVE[0] - 0.15, GROOVE[1] + 0.15), Z_SPLIT - 0.3, Z_SPLIT + 0.1)    # its lead-in
    return shell - cut

def csk(x, y):
    """countersink for an M2 flat head, flush with the back face, plus its clearance hole"""
    h = (CSK_D - CSK_HOLE) / 2
    cone = M.cylinder(h + 0.01, CSK_HOLE / 2, CSK_D / 2 + 0.01, 48).translate([x, y, DEPTH - h])
    return cone + cyl_z(CSK_D + 0.02, x, y, DEPTH - 0.001, DEPTH + 1) + cyl_z(CSK_HOLE, x, y, Z_ONE - 0.5, DEPTH + 1)

def one_pads():
    """bosses from the back wall onto the ONE SLIM's back: behind every switch, round the strip, at J2"""
    pts = list(o.switch_xy().values()) + [(18.3, 22.0), (27.8, 20.0), (18.3, 0.0), (27.8, -6.0), (18.3, -24.0), (2.0, -46.0), (-20.0, -44.0)]
    return pts

THT_LEADS = []                       # rev S2: no through-hole parts but the header pins

def pin_pockets():
    """relief in the back wall over the soldered pin tips (0.5 mm deep), one per row"""
    c = M()
    for row in ([n for n in PINS if n % 2], [n for n in PINS if not n % 2]):
        xs = [pin_xy(n)[0] for n in row]; ys = [pin_xy(n)[1] for n in row]
        c += box(min(xs) - 1.3, max(xs) + 1.3, min(ys) - 1.3, max(ys) + 1.3, ZIN - 0.05, ZIN + 0.5)
    return c

def back_shell():
    outer, inner = o.skins()
    shell = (outer ^ box(-100, 100, -100, 100, Z_SPLIT, DEPTH + 1)) - inner
    add = prism(ring2d(o.WALL - 0.01, o.WALL + LAND), Z_SPLIT, Z_SPLIT + 2.0) - joint_keepout()          # joint land
    for x, y in WS_SCREWS: add += cyl_z(5.0, x, y, Z_BACK, ZIN + 0.01)                                       # posts onto the standoffs
    for x, y in o.LOWER_SCREWS: add += cyl_z(6.0, x, y, Z_ONE + ONE_T, ZIN + 0.01)
    for x, y in one_pads(): add += cyl_z(3.5, x, y, Z_ONE + ONE_T, ZIN + 0.01)
    b = BAY; bz = b['z0'] + 1.5                                                                             # battery bay corners
    for x, sx in ((b['x0'], -1), (b['x1'], 1)):
        for y, sy in ((b['y0'], -1), (b['y1'], 1)):
            xa, ya = x + sx * 0.2, y + sy * 0.2
            w = 1.2 if sx < 0 else 0.8                                              # right: 0.2 mm clear of the ONE strip
            add += box(min(xa, xa + sx * w), max(xa, xa + sx * w), min(ya, ya - sy * 4), max(ya, ya - sy * 4), bz, ZIN + 0.01)
            add += box(min(xa, xa - sx * 4), max(xa, xa - sx * 4), min(ya, ya + sy * 1.2), max(ya, ya + sy * 1.2), bz, ZIN + 0.01)
    s = SPK                                                                                                 # speaker lip
    cx, cy, w, h = (s['x0'] + s['x1']) / 2, (s['y0'] + s['y1']) / 2, s['x1'] - s['x0'], s['y1'] - s['y0']
    add += prism(rrect(w + 2.4, h + 2.4, 1.2, cx, cy) - rrect(w + 0.4, h + 0.4, 0.3, cx, cy), ZIN - 1.5, ZIN + 0.01)
    add += box(-22.0, 22.0, 51.0, 53.0, Z_BACK, ZIN + 0.01)                                               # stiffening rib over the USB end
    for x, y in CLIPS: add += cyl_z(1.2, x, y, ZIN - 2.5, ZIN + 0.01, 16)                                  # lead clips
    add += tongue()
    shell = shell + (add ^ (inner + tongue()))
    cut = shared_cuts() + pin_pockets() + chamfers() + back_text()
    for x, y in WS_SCREWS + o.LOWER_SCREWS: cut += csk(x, y)
    for i in range(6):                                                                                      # speaker grille
        x = s['x0'] + 2.0 + i * (w - 4.0) / 5
        cut += prism(rrect(1.2, h - 3.0, 0.6, x, cy), ZIN - 0.1, DEPTH + 1)
    return shell - cut

def tongue():
    t = prism(ring2d(*TONGUE), Z_SPLIT - TONGUE_LEN + 0.3, Z_SPLIT + 0.01)
    t += prism(ring2d(TONGUE[0] + 0.15, TONGUE[1] - 0.15), Z_SPLIT - TONGUE_LEN, Z_SPLIT - TONGUE_LEN + 0.31)   # lead-in
    return t - joint_keepout()

def chamfers():
    """0.5 mm chamfers round the openings in the outside: USB-C, the power button, the two pin holes"""
    c = 0.5
    def frustum(b, axis, outer):
        x0, x1, y0, y1, z0, z1 = b
        if axis == 'y':
            big = box(x0 - c, x1 + c, outer - 0.01, outer + 2, z0 - c, z1 + c); small = box(x0, x1, outer - c - 0.01, outer - c, z0, z1)
        else:
            big = box(outer - 2, outer + 0.01, y0 - c, y1 + c, z0 - c, z1 + c); small = box(outer + c, outer + c + 0.01, y0, y1, z0, z1)
        return M.batch_hull([big, small])
    m = frustum((-6.4, 6.4, 0, 0, USB_Z - 3.5, USB_Z + 3.5), 'y', o.Y_TOP)
    P = PLUNGER; hw, hh = P['head']; h = P['hole']
    m += frustum((0, 0, PWR_Y - hw / 2 - h, PWR_Y + hw / 2 + h, PLUNGER_Z - hh / 2 - h, PLUNGER_Z + hh / 2 + h), 'x', -o.UPPER_W / 2)
    for k in ('RST', 'BOOT'):
        y = o.SIDE_KEYS_Y[k]
        m += frustum((0, 0, y - 0.8, y + 0.8, Z_GLASS + SIDE_SWITCH_Z[0] - 0.1, Z_GLASS + SIDE_SWITCH_Z[1] + 0.1), 'x', -o.UPPER_W / 2)
    return m

# ---- caps: dished wings, a domed rocker, rounded top edges, stems for the SLIM's switch height ----------------
def _sphere_c(side):
    """the wing dish: a sphere in front of the cap, DISH deep in the middle of the flat top"""
    r = o.BTN_D / 2 - TOP_ROUND
    R = (r * r + DISH * DISH) / (2 * DISH)
    return R, (side * o.WING_X, o.WING_Y, -o.WING_PROUD + DISH - R)

def wing_cap(side):
    cx, cy, top, r = side * o.WING_X, o.WING_Y, -o.WING_PROUD, o.BTN_D / 2
    prof = [(0.0, top)] + [(r - TOP_ROUND + TOP_ROUND * math.sin(a), top + TOP_ROUND - TOP_ROUND * math.cos(a)) for a in np.linspace(0, math.pi / 2, 9)]
    prof += [(r, top + TOP_ROUND + 0.1), (0.0, top + TOP_ROUND + 0.1)]
    cap = M.revolve(CS([prof]), 96).translate([cx, cy, 0])                                                     # rounded top
    cap += prism(wing2d(side), top + TOP_ROUND, o.COLLAR_Z) + prism(wing2d(side, o.FLANGE), o.COLLAR_Z, o.COLLAR_Z + 1.0)
    R, c = _sphere_c(side)
    cap -= M.sphere(R, 512).translate(list(c))                                                                 # the dish
    cap -= prism(o.glyph2d(side), top - 1, top + 2) ^ M.sphere(R + ENGRAVE, 512).translate(list(c))            # the wing, 0.4 deep
    cap += o.key_box(side, 0.0, 0.0, FRONT_SKIN + 0.3, o.COLLAR_Z - 0.2)
    cap += cyl_z(4.0, cx, cy, o.COLLAR_Z + 0.5, Z_ONE - o.SW_H - o.PRETRAVEL)
    return cap

def _dome():
    half = o.ROCKER_W / 2
    Rc = (half * half + DOME_SAG * DOME_SAG) / (2 * DOME_SAG)
    return Rc, ROCKER_TOP + Rc

def rocker_cap():
    z0 = o.COLLAR_Z + o.ROCKER_GAP; top = ROCKER_TOP
    cap = prism(rocker2d(), top + TOP_ROUND, z0) + prism(rocker2d(o.FLANGE), z0, z0 + 1.0)
    n = 8
    for i in range(n):                                                                       # rounded top edge, in layers
        h = (i + 0.5) / n * TOP_ROUND
        inset = TOP_ROUND - math.sqrt(max(0.0, TOP_ROUND ** 2 - (TOP_ROUND - h) ** 2))
        cap += prism(rocker2d(-inset), top + i / n * TOP_ROUND - 0.001, top + (i + 1) / n * TOP_ROUND + 0.001)
    Rc, zc = _dome()
    cap = cap ^ s_cyl_y(2 * Rc, zc)                                                              # the dome
    cap -= prism(o.dart_glyph2d(), top - 1, top + 2) - s_cyl_y(2 * (Rc - ENGRAVE), zc)           # the dart, 0.4 deep
    tip = Z_ONE - o.SW_H - o.PRETRAVEL
    for sx in (-1, 1): cap += cyl_z(4.0, sx * o.DART_X, o.ROCKER_Y, z0 + 0.5, tip)
    return cap - o.cyl_y(o.AXLE_D + 0.05, 0, o.AXLE_Z, o.ROCKER_Y - 10, o.ROCKER_Y + 10)

def s_cyl_y(d, zc):
    return o.cyl_y(d, 0, zc, o.ROCKER_Y - 10, o.ROCKER_Y + 10, 8192)

def ref_glyphs():
    """render only: the engraved wings and dart, filled (paint), following the curved tops"""
    g = M()
    for side in (-1, 1):
        R, c = _sphere_c(side)
        g += (prism(o.glyph2d(side), -5, 2) ^ M.sphere(R + ENGRAVE - 0.02, 512).translate(list(c))) - M.sphere(R + 0.02, 512).translate(list(c))
    Rc, zc = _dome()
    g += (prism(o.dart_glyph2d(), -5, 2) ^ s_cyl_y(2 * (Rc - 0.02), zc)) - s_cyl_y(2 * (Rc - ENGRAVE + 0.02), zc)
    return g

def text2d(text, height, cy):
    """engraving text as seen from the BACK (mirrored in the design frame, which looks from the front), centred"""
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    tp = TextPath((0, 0), text, size=height / 0.73, prop=FontProperties(family='DejaVu Sans', weight='bold'))
    polys = [[(float(x), float(y)) for x, y in p] for p in tp.to_polygons() if len(p) > 2]
    cs = CS(polys, mf.FillRule.EvenOdd)
    b = cs.bounds()
    cs = cs.translate([-(b[0] + b[2]) / 2, -(b[1] + b[3]) / 2])
    return cs.mirror([1, 0]).translate([0, cy])

def back_text():
    m = M()
    for t, h, y in BACK_TEXT: m += prism(text2d(t, h, y), DEPTH - TEXT_DEPTH, DEPTH + 1)
    return m

# ---- reference volumes ------------------------------------------------------------------------------------------
def ref_waveshare():
    """glass and module, its board, the low parts, the tall parts and the standoffs (Waveshare 3D model)"""
    g = Z_GLASS
    m = prism(board2d(), g, g + 4.4)                                            # glass + LCD (full outline)
    m += box(-26.68, 26.68, -26.19, 56.74, g + 4.4, g + 8.4)                     # LCD body and its flex
    low = box(-27.26, 27.26, -25.23, 52.79, g + 5.9, g + WS_PARTS)              # board + low parts
    for y in o.SIDE_KEYS_Y.values():                                            # the edge keys are the outermost parts there
        low -= box(-27.3, -26.85, y - 2.3, y + 2.3, g + 7.55, g + WS_PARTS + 0.1)
    m += low
    for x0, x1, y0, y1, h in WS_TALL.values(): m += box(x0, x1, y0, y1, g + 5.9, g + h)
    for y in o.SIDE_KEYS_Y.values(): m += box(-26.85, -23.2, y - 2.3, y + 2.3, g + SIDE_SWITCH_Z[0], g + SIDE_SWITCH_Z[1])
    for x, y in o.standoffs(): m += cyl_z(4.0, x, y, g + 5.9, Z_BACK) - cyl_z(1.6, x, y, g + 7.5, Z_BACK + 0.1)   # M2 standoffs
    return m

def one2d():
    """ONE SLIM outline: the ONE's plate and strip, 0.3 mm further in (clear of the back shell's inner round)"""
    inner = body2d().offset(-o.WALL - 1.5, mf.JoinType.Round)
    plate = inner ^ CS.square([200, o.PLATE_TOP + 100]).translate([-100, -100])
    strip = rrect(o.STRIP_X[1] - o.STRIP_X[0], o.STRIP_TOP - o.PLATE_TOP + 2, 1.0, sum(o.STRIP_X) / 2, (o.STRIP_TOP + o.PLATE_TOP - 2) / 2)
    out = (plate + strip).offset(1.0, mf.JoinType.Round).offset(-1.0, mf.JoinType.Round)
    for x, y in o.LOWER_SCREWS: out = out - circle(o.CLEAR_D, x, y)
    return out

def one_board():
    return prism(one2d(), Z_ONE, Z_ONE + ONE_T)

def one_board_drilled():
    """the board with its 32 J1 holes (1.02 mm), for the jig checks"""
    m = one_board()
    for n in range(1, 33):
        x, y = pin_xy(n); m -= cyl_z(1.02, x, y, Z_ONE - 1, Z_ONE + ONE_T + 1, 16)
    return m

def ref_pins():
    m = M()
    for n in PINS:
        x, y = pin_xy(n); m += box(x - 0.32, x + 0.32, y - 0.32, y + 0.32, Z_ONE - PIN_OUT, Z_ONE + ONE_T + 0.05)
    return m

def ref_parts():
    """the ONE SLIM's front-face parts: four tact switches, J2 with the cell's plug, Q1"""
    j = J2_BODY
    m = o.ref_switches() + box(j['x0'], j['x1'], j['y0'], j['y1'], Z_ONE - j['h'], Z_ONE)
    m += box(j['x1'], j['x1'] + 6.0, j['y0'] + 0.2, j['y1'] - 0.2, Z_ONE - j['h'] + 0.4, Z_ONE - 0.4)       # the cell's plug
    x, y = Q1_XY
    return m + box(x - 1.5, x + 1.5, y - 1.5, y + 1.5, Z_ONE - 1.3, Z_ONE)

def ref_battery(cell=CELL):
    b = BAY; return box(cell['x0'], cell['x1'], cell['y0'], cell['y1'], b['z0'], b['z0'] + b['t'])

def ref_bay():
    b = BAY; return ref_battery(b)

def ref_foam():
    c = CELL; z0 = BAY['z0'] + BAY['t']
    return box(c['x0'] + 2, c['x1'] - 2, c['y0'] + 3, c['y1'] - 3, z0, ZIN - 0.05)

def ref_speaker():
    s = SPK; return box(s['x0'], s['x1'], s['y0'], s['y1'], ZIN - s['t'], ZIN)

def ref_screws():
    m = M()
    for x, y, L in [(x, y, WS_SCREW_L) for x, y in WS_SCREWS] + [(x, y, LOWER_SCREW_L) for x, y in o.LOWER_SCREWS]:
        h = (3.8 - 2.0) / 2
        m += M.cylinder(h, 1.0, 1.9, 32).translate([x, y, DEPTH - h - 0.05]) + cyl_z(2.0, x, y, DEPTH - L - 0.05, DEPTH - h)
    return m

# ---- builder's helpers -----------------------------------------------------------------------------------------
AXLE_LEN = 11.0
def pin_jig():
    """sets the pins, and only fits one way: the ONE SLIM lies face down on it, inside the fence that hugs the strip's
    top end and outer edge; each header strip goes in long side first, through the board, into blind holes
    PIN_OUT deep. Solder, slide the plastic off, snip flush. Also: a slot that cuts the rocker's 1.75 mm filament
    axle to 11 mm (push the filament to the closed end, cut at the open end)."""
    xs = [pin_xy(n)[0] for n in PINS]; ys = [pin_xy(n)[1] for n in PINS]
    x0, x1, y0, y1 = o.STRIP_X[0] + 0.5, o.STRIP_X[1] + 2.2, min(ys) - 4.0, o.STRIP_TOP + 2.2
    z1 = Z_ONE; z0 = z1 - PIN_OUT - 2.0
    jig = box(x0, x1, y0, y1, z0, z1)
    for n in PINS:
        x, y = pin_xy(n); jig -= cyl_z(1.15, x, y, z1 - PIN_OUT, z1 + 1, 24)
    fence = box(o.STRIP_X[1] + 0.2, x1, y0, y1, z1 - 0.01, z1 + 0.6) + box(x0, x1, o.STRIP_TOP + 0.2, y1, z1 - 0.01, z1 + 0.6)
    jig += fence
    for n in (11, 20):                                    # two pegs in empty J1 holes: a board turned over will not sit
        x, y = pin_xy(n); jig += cyl_z(0.85, x, y, z1 - 0.01, z1 + 0.7, 16)
    gauge = box(x1, x1 + 4.0, y0, y0 + AXLE_LEN + 3.0, z0, z1)                                  # the axle gauge
    gauge -= box(x1 + 1.05, x1 + 2.95, y0 + 1.5, y0 + 30, z1 - 1.5, z1 + 1)                  # closed end at y0 + 1.5
    gauge -= box(x1 - 1, x1 + 5, y0 + 1.5 + AXLE_LEN, y0 + 30, z0 - 1, z1 + 1)                 # the block ends at 11 mm
    return jig + gauge

PARTS = {
    'slim_front': front_shell, 'slim_back': back_shell,
    'slim_wing_left': lambda: wing_cap(-1), 'slim_wing_right': lambda: wing_cap(1), 'slim_rocker': rocker_cap,
    'slim_power_button': plunger, 'slim_pin_jig': pin_jig,
}
REFS = {
    'ref_panel': o.face_panel, 'ref_glyphs': ref_glyphs, 'ref_foam': ref_foam, 'ref_waveshare': ref_waveshare,
    'ref_one': one_board, 'ref_battery': ref_battery, 'ref_speaker': ref_speaker, 'ref_screws': ref_screws,
    'ref_switches': lambda: ref_parts() + ref_pins(),
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
