#!/usr/bin/env python3
"""STRUTHIO ONE SLIM · the 16.5 mm case.

    python3 slim_cad.py            writes stl/*.stl (printed parts) and refs/*.stl (bought parts, for checks and renders)

The SLIM keeps the ONE's outline, face panel, keys and controls (one_cad.py, imported) and rebuilds the depth:

  0.0  - 1.0   face panel (1.0 mm acrylic, unchanged)
  1.0  - 1.5   0.5 mm shell rim over the glass border (the glass sits in a pocket in the 1.6 mm face)
  1.5  - 14.1  Waveshare: glass front to the top of its J8 socket (Waveshare 3D model: 12.6 mm)
  14.1 - 14.9  ONE SLIM board, 0.8 mm, lying ON the J8 socket: 8 bare header pins go 3.0 mm into it
  14.9 - 15.0  clearance
  15.0 - 16.5  back wall, 1.5 mm

Behind the Waveshare (its back parts stand at most 9.5 mm behind the glass, Waveshare 3D model) there is a
3.7 mm deep bay: a 3.0 mm LiPo (302535, 250 mAh; a 303450, about 500 mAh, fits the same bay) and a
15 x 11 x 2.5 mm speaker (Same Sky CMS-151125-078SP). The Waveshare is screwed to the back shell through three
of its own M2 standoffs (SMTSO-M2X4 in the 3D model), and the shells meet in a tongue-and-groove joint.

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
Z_ONE = Z_SOCK                        # the board's front face lies on the socket
PIN_INSERT = 3.0                      # bare pins into the socket (a standard header's short tail is 3.0 mm)
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
SPK = dict(x0=-18.5, x1=-3.5, y0=-21.5, y1=-10.5, t=2.5)   # CMS-151125-078SP, 15 x 11 x 2.5, against the back wall
# the cell lead: along under the bay's bottom edge, then down to J2 (the ONE board's battery socket)
LEAD = dict(x0=-2.0, x1=10.5, y0=-33.0, y1=BAY['y0'], z0=Z_GLASS + WS_PARTS + 0.1, z1=ZIN)
LEAD_ALONG = dict(x0=-14.4, x1=10.5, y0=-9.0, y1=BAY['y0'] - 0.4, z0=Z_GLASS + WS_PARTS + 0.1, z1=ZIN)
SPK_LEAD = dict(x0=-23.5, x1=-20.0, y0=-17.0, y1=10.6, z0=Z_GLASS + WS_PARTS + 0.1, z1=ZIN)    # speaker lead up to J9

# screws: all M2 countersunk (ISO 10642 / DIN 965), heads flush with the back
CSK_D, CSK_HOLE = 4.0, 2.3
WS_SCREWS = [(x, y) for x, y in o.standoffs() if not (x > 0 and y < o.BCY)]   # three standoffs; the 4th is under the ONE strip
WS_SCREW_L = 6.0
LOWER_SCREW_L = 8.0
PILOT_D = o.PILOT_D

# the ONE SLIM's header pins (J8 numbering): BAT, GND x2, DART L/R, LEFT/RIGHT WING, PWR
PINS = (1, 3, 4, 5, 7, 16, 18, 24)

def pin_xy(n):
    """J8 pin n in the case frame: odd pins on the row nearer the edge (one_cad.HDR_ROW_X)"""
    k = (n - 1) // 2
    return (o.HDR_ROW_X[1] if n % 2 else o.HDR_ROW_X[0], o.HDR_PIN1_Y - 2.54 * k)

def setup():
    """point one_cad's shared helpers (skins, caps, switch, board outline) at the SLIM stack"""
    for k, v in dict(DEPTH=DEPTH, BACK_WALL=BACK_WALL, FRONT_SKIN=FRONT_SKIN, Z_GLASS=Z_GLASS, Z_BACK=Z_BACK,
                     Z_ONE=Z_ONE, ONE_T=ONE_T, Z_SPLIT=Z_SPLIT, USB_Z=USB_Z, RB=RB, K=RB).items():
        setattr(o, k, v)
    o._CACHE.clear()
setup()

def ring2d(a, b):
    """the band between a and b mm in from the outer surface"""
    out = body2d()
    return out.offset(-a, mf.JoinType.Round) - out.offset(-b, mf.JoinType.Round)

def joint_keepout():
    """where the joint's land, groove and tongue stop: the power switch, its knob slot, the edge-key pin holes, USB-C"""
    body, knob, _ = o.psw_box()
    b = body.bounding_box()
    k = box(b[0] - 0.4, b[3] + 0.4, b[1] - 0.4, b[4] + 0.4, -1, DEPTH + 1)
    return k + shared_cuts()

# =========================================================================================================
def shared_cuts():
    """openings that cross the split line"""
    c = box(-6.4, 6.4, o.BCY + o.BH / 2 - 7.0, o.Y_TOP + 2, USB_Z - 3.5, USB_Z + 3.5)          # USB-C plug
    for y in o.SIDE_KEYS_Y.values():                                                           # pin holes onto the edge keys
        c += box(-o.UPPER_W / 2 - 2, -26.6, y - 0.8, y + 0.8, Z_GLASS + SIDE_SWITCH_Z[0] - 0.1, Z_GLASS + SIDE_SWITCH_Z[1] + 0.1)
    zc = Z_ONE - o.PSW_H / 2                                                                   # power slider
    c += box(-o.LOWER_W / 2 - 3, -o.LOWER_W / 2 + 6, o.PSW_Y - o.PSW_KNOB / 2 - o.PSW_TRAVEL / 2 - 0.4,
             o.PSW_Y + o.PSW_KNOB / 2 + o.PSW_TRAVEL / 2 + 0.4, min(zc - o.PSW_KNOB / 2 - 0.3, Z_SPLIT - 0.5), zc + o.PSW_KNOB / 2 + 0.3)
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
    cut += shared_cuts()
    cut += prism(ring2d(*GROOVE), Z_SPLIT - GROOVE_DEPTH, Z_SPLIT + 0.1)                     # the groove
    return shell - cut

def csk(x, y):
    """countersink for an M2 flat head, flush with the back face, plus its clearance hole"""
    h = (CSK_D - CSK_HOLE) / 2
    cone = M.cylinder(h + 0.01, CSK_HOLE / 2, CSK_D / 2 + 0.01, 48).translate([x, y, DEPTH - h])
    return cone + cyl_z(CSK_D + 0.02, x, y, DEPTH - 0.001, DEPTH + 1) + cyl_z(CSK_HOLE, x, y, Z_ONE - 0.5, DEPTH + 1)

def one_pads():
    """bosses from the back wall onto the ONE SLIM's back: behind every switch, round the strip, at J2"""
    pts = list(o.switch_xy().values()) + [(18.3, 22.0), (27.8, 20.0), (18.3, 0.0), (27.8, -6.0), (18.3, -24.0), (2.0, -44.0), (-20.0, -44.0)]
    return pts

# through-hole leads of the slide switch and the battery socket, trimmed flush (pcb/slim/out/tht_leads.txt)
THT_LEADS = [(-24.486, -45.3), (-24.486, -50.0), (-24.486, -54.7), (2.0, -38.0), (2.0, -36.0)]

def pin_pockets():
    """relief in the back wall over the soldered pin tips and trimmed leads (0.5 mm deep)"""
    c = M()
    for x, y in [pin_xy(n) for n in PINS] + THT_LEADS:
        c += box(x - 1.3, x + 1.3, y - 1.3, y + 1.3, ZIN - 0.05, ZIN + 0.5)
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
    add += tongue()
    shell = shell + (add ^ (inner + tongue()))
    cut = shared_cuts() + pin_pockets()
    for x, y in WS_SCREWS + o.LOWER_SCREWS: cut += csk(x, y)
    for i in range(6):                                                                                      # speaker grille
        x = s['x0'] + 2.0 + i * (w - 4.0) / 5
        cut += prism(rrect(1.2, h - 3.0, 0.6, x, cy), ZIN - 0.1, DEPTH + 1)
    return shell - cut

def tongue():
    return prism(ring2d(*TONGUE), Z_SPLIT - TONGUE_LEN, Z_SPLIT + 0.01) - joint_keepout()

# ---- caps: the ONE's, with stems for the SLIM's switch height ---------------------------------------------
def wing_cap(side):
    return o.wing_cap(side)

def rocker_cap():
    return o.rocker_cap()

# ---- reference volumes ------------------------------------------------------------------------------------------
def ref_waveshare():
    """glass and module, its board, the low parts, the tall parts and the standoffs (Waveshare 3D model)"""
    g = Z_GLASS
    m = prism(board2d(), g, g + 4.4)                                            # glass + LCD (full outline)
    m += box(-26.68, 26.68, -26.19, 56.74, g + 4.4, g + 8.4)                     # LCD body and its flex
    m += box(-27.26, 27.26, -25.23, 52.79, g + 5.9, g + WS_PARTS)               # board + low parts
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

def ref_pins():
    m = M()
    for n in PINS:
        x, y = pin_xy(n); m += box(x - 0.32, x + 0.32, y - 0.32, y + 0.32, Z_ONE - PIN_INSERT, Z_ONE + ONE_T + 0.05)
    return m

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
SPACER_T = 1.1          # print and fit only if YOUR board's J8 top is 11.5 mm behind the glass, not 12.6 (measure it)

def pin_jig():
    """sets the bare pins: the ONE SLIM lies face down on it, the header's long side goes through the board into
    these 3.0 mm blind holes, so after soldering every pin stands exactly PIN_INSERT out of the board's front"""
    xs = [pin_xy(n)[0] for n in PINS]; ys = [pin_xy(n)[1] for n in PINS]
    x0, x1, y0, y1 = min(xs) - 3.5, max(xs) + 3.5, min(ys) - 3.5, max(ys) + 3.5
    jig = box(x0, x1, y0, y1, 0, 2.0 + PIN_INSERT)
    for n in PINS:
        x, y = pin_xy(n); jig -= cyl_z(1.15, x, y, 2.0, 2.0 + PIN_INSERT + 1, 24)
    return jig

def pin_spacer():
    """1.1 mm plate with the pin holes: lies on J8 under the ONE SLIM (and on the jig while soldering) when J8's
    top is 11.5 mm behind the glass instead of the 12.6 the case is drawn for"""
    xs = [pin_xy(n)[0] for n in PINS]; ys = [pin_xy(n)[1] for n in PINS]
    p = box(min(xs) - 1.6, max(xs) + 1.6, min(ys) - 1.6, max(ys) + 1.6, 0, SPACER_T)
    for n in PINS:
        x, y = pin_xy(n); p -= cyl_z(1.15, x, y, -1, 2, 24)
    return p

PARTS = {
    'slim_front': front_shell, 'slim_back': back_shell,
    'slim_wing_left': lambda: wing_cap(-1), 'slim_wing_right': lambda: wing_cap(1), 'slim_rocker': rocker_cap,
    'slim_pin_jig': pin_jig, 'slim_pin_spacer': pin_spacer,
}
REFS = {
    'ref_panel': o.face_panel, 'ref_glyphs': o.ref_glyphs, 'ref_foam': ref_foam, 'ref_waveshare': ref_waveshare,
    'ref_one': one_board, 'ref_battery': ref_battery, 'ref_speaker': ref_speaker, 'ref_screws': ref_screws,
    'ref_switches': lambda: o.ref_switches() + o.psw_box()[0] + o.psw_box()[1] + o.ref_ph_socket() + ref_pins() + o.ref_smd(),
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
