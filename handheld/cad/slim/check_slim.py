#!/usr/bin/env python3
"""STRUTHIO ONE SLIM · fit checks: the 16.5 mm stack, the joint, the screws, the bays, the keys.

    python3 check_slim.py        prints one PASS/FAIL line per check and a summary
"""
import sys
import numpy as np
import manifold3d as mf
import slim_cad as s
o = s.o

R = []
def check(name, ok, detail=''):
    R.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if detail else ''))

def vol(m):
    return 0.0 if m.is_empty() else m.volume()

def clash(a, b):
    return vol(a ^ b)

def thinnest(m, z0, z1, xy, step=0.05):
    """material thickness along z at point xy between z0 and z1"""
    probe = s.box(xy[0] - 0.05, xy[0] + 0.05, xy[1] - 0.05, xy[1] + 0.05, z0, z1)
    return vol(m ^ probe) / 0.01

front, back = s.front_shell(), s.back_shell()
shells = front + back
caps = {'left wing': s.wing_cap(-1), 'right wing': s.wing_cap(1), 'rocker': s.rocker_cap()}
ws, one, cell, bay, spk = s.ref_waveshare(), s.one_board(), s.ref_battery(), s.ref_bay(), s.ref_speaker()
pins, screws = s.ref_pins(), s.ref_screws()
sw = s.ref_parts(); btn = s.plunger(); clips = sum((s.cyl_z(1.2, x, y, s.ZIN - 2.5, s.ZIN, 16) for x, y in s.CLIPS), s.M())
lead = s.box(*(s.LEAD[k] for k in ('x0', 'x1', 'y0', 'y1', 'z0', 'z1'))) + s.box(*(s.LEAD_ALONG[k] for k in ('x0', 'x1', 'y0', 'y1', 'z0', 'z1')))
slead = s.box(*(s.SPK_LEAD[k] for k in ('x0', 'x1', 'y0', 'y1', 'z0', 'z1')))
panel = o.face_panel()

# ---- solids and the stack ----------------------------------------------------------------------------------
for n, m in [('front shell', front), ('back shell', back)] + list(caps.items()):
    parts = [p for p in m.decompose() if p.volume() > 0.01]
    check(f'{n}: one watertight solid', m.status().name == 'NoError' and len(parts) == 1, f'{len(parts)} piece(s), {m.volume()/1000:.1f} cm3')
import manifold3d as mf
check('thickness 16.5 mm, panel included', abs(back.bounding_box()[5] - s.DEPTH) < 0.01 and abs(panel.bounding_box()[2]) < 0.01,
      f'{back.bounding_box()[5]:.2f} mm')
b = o.body2d().bounds()
check('outline unchanged from the ONE: 74 x 136', abs(b[2] - b[0] - 74) < 0.3 and abs(b[3] - b[1] - 136) < 0.1, f'{b[2]-b[0]:.2f} x {b[3]-b[1]:.2f}')
check('face panel sits in its pocket, flush with the lip', abs(front.bounding_box()[2]) < 0.01 and abs(panel.bounding_box()[2]) < 0.01 and clash(panel, shells) < 0.01)
_gap = (o.body2d().offset(-s.LIP_POCKET, mf.JoinType.Round) - o.panel2d().offset(s.PANEL_CLEAR - 0.01, mf.JoinType.Round)).area()
check('face panel: 0.2 mm clear of the lip all round (drops in, lines itself up)', (o.panel2d().offset(s.PANEL_CLEAR - 0.02, mf.JoinType.Round) - o.body2d().offset(-s.LIP_POCKET, mf.JoinType.Round)).area() < 0.01)
check('lip: 1.0 mm tall, 2.6 mm wide, round on its outside edge', abs(thinnest(front, -0.5, o.PANEL_T, (0.0, -70.6 + 2.3)) - o.PANEL_T) < 0.05,
      f'{thinnest(front, -0.5, o.PANEL_T, (0.0, -70.6 + 2.3)):.2f} mm at the bottom edge')
_p = o.panel2d(); _q = _p.offset(-1.5, mf.JoinType.Round).offset(1.5, mf.JoinType.Round)
check('face panel (resized for the pocket): nothing narrower than 3 mm', _p.area() - _q.area() < 3.0, f'{_p.area() - _q.area():.1f} mm2 narrower')
# walls through the elliptical back edge: every inside point at least WALL_T - 0.05 from the outside
_po = np.array([(r, z) for r, z in s.profile_out()]); _pi = np.array([(r, z) for r, z in s.profile_in()])
def _seg_d(pt, a, b):
    ab = b - a; t = np.clip(np.dot(pt - a, ab) / max(np.dot(ab, ab), 1e-12), 0, 1); return np.linalg.norm(pt - (a + t * ab))
_dense = np.array([_po[i] + (_po[i + 1] - _po[i]) * f for i in range(len(_po) - 1) for f in np.linspace(0, 1, 20)])
_wmin = min(min(_seg_d(q, _dense[i], _dense[i + 1]) for i in range(len(_dense) - 1)) for q in _pi[1:])
check('back edge: an elliptical round (3 x 5.5 mm), walls still 1.5 mm or more all through it', _wmin >= 1.5 - 0.01, f'thinnest {_wmin:.2f} mm')
check('stack adds up: panel + rim + Waveshare to its socket + ONE SLIM + 0.1 + back wall = 16.5',
      abs(o.PANEL_T + s.RIM + s.WS_SOCKET + s.ONE_T + 0.1 + s.BACK_WALL - s.DEPTH) < 1e-9)

# ---- walls ("not thin enough to feel cheap") --------------------------------------------------------------
check('back wall 1.5 mm solid (PETG: 4 perimeters / 5+ solid layers)', s.BACK_WALL >= 1.5 and thinnest(back, s.ZIN - 0.2, s.DEPTH + 0.1, (-5.0, -50.0)) >= 1.5 - 0.02,
      f'{thinnest(back, s.ZIN - 0.2, s.DEPTH + 0.1, (-5.0, -50.0)):.2f} mm at the controller zone')
check('back wall over the pin tips: 1.0 mm (0.5 mm relief)', all(0.98 <= thinnest(back, s.ZIN - 0.2, s.DEPTH + 0.1, s.pin_xy(n)) <= 1.02 for n in s.PINS))
import os as _os
_t = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', 'pcb', 'slim', 'out', 'tht_leads.txt')
check('no through-hole leads to trim on the board (only the header pins)', not s.THT_LEADS and (not _os.path.exists(_t) or not open(_t).read().strip()))
check('face: 1.6 mm of shell behind the panel round the controls (the ONE had 0.8)', thinnest(front, 0.0, 5.0, (0.0, -66.0)) >= 1.6 - 0.02,
      f'{thinnest(front, 0.0, 5.0, (0.0, -66.0)):.2f} mm')
check('rim over the glass border: 0.5 mm, backed by the glass and covered by the panel', abs(thinnest(front, 0.0, s.Z_GLASS + 0.5, (0.0, o.BCY + o.AA_H / 2 + 3.0)) - s.RIM) < 0.03)
check('side walls 1.75 mm, 2.75 mm through the joint band', o.WALL >= 1.75 and s.LAND >= 1.0)

# ---- tongue and groove -------------------------------------------------------------------------------------
g0, g1 = s.GROOVE; t0, t1 = s.TONGUE
check('joint: tongue 0.7 mm in a 1.0 mm groove, 0.15 mm clearance each side (FDM)', abs((t0 - g0) - 0.15) < 1e-9 and abs((g1 - t1) - 0.15) < 1e-9)
check('joint: 1.5 mm engagement, 0.1 mm clear at the bottom (the shells close on their faces)', abs(s.GROOVE_DEPTH - s.TONGUE_LEN - 0.1) < 1e-9 and s.TONGUE_LEN >= 1.5)
check('joint: groove lips 0.85 / 0.90 mm thick', g0 >= 0.85 - 1e-9 and (o.WALL + s.LAND) - g1 >= 0.9 - 1e-9)
check('joint: tongue clears the front shell (closed)', clash(s.tongue(), front) < 0.01, f'{clash(s.tongue(), front):.3f} mm3')
_tl = vol(s.tongue()) / ((t1 - t0) * s.TONGUE_LEN)
check('joint: the tongue runs round most of the case (stops only at the switch, USB-C and pin holes)', _tl > 330, f'{_tl:.0f} mm of tongue')
check('joint: shells meet at the split face (no gap, no overlap)', clash(front, back) < 0.01 and abs(front.bounding_box()[5] - s.Z_ONE) < 0.01)

# ---- the Waveshare and the ONE SLIM ---------------------------------------------------------------------
check('Waveshare clears the shells', clash(ws, shells) < 0.5, f'{clash(ws, shells):.2f} mm3')
check('glass sits on the 0.5 mm rim, in a pocket (x/y located by it)', abs(ws.bounding_box()[2] - s.Z_GLASS) < 0.01)
check('ONE SLIM sits on the front bosses, level with a 12.6 mm socket top', abs(s.Z_ONE - (s.Z_GLASS + s.WS_SOCKET)) < 1e-9 and clash(one, ws) < 0.01)
check('ONE SLIM: 0.1 mm under the back wall, pressed down by 11 pads', abs(s.ZIN - (s.Z_ONE + s.ONE_T) - 0.1) < 1e-9 and len(s.one_pads()) >= 11)
_ins = [s.PIN_OUT - (s.Z_ONE - (s.Z_GLASS + h)) for h in (s.WS_SOCKET, s.WS_SOCKET_LOW)]
check('header pins reach into J8 2.5-3.8 mm whichever height its socket is (12.6 or 11.5 mm)', all(2.5 - 1e-9 <= i <= 3.8 for i in _ins) and clash(pins, shells) < 0.01,
      ' / '.join(f'{i:.1f} mm' for i in _ins))
check('12 pins in two straight strips (odd 1-7, even 4-18); pin 9 empty (the SLIM)', sorted(s.PINS) == sorted((1, 3, 5, 7) + tuple(range(4, 19, 2))) and 9 not in s.PINS)
check('ONE SLIM and its parts (switches, J2 and the cell plug, Q1) clear the shells', clash(one + sw, shells) < 0.5, f'{clash(one + sw, shells):.2f} mm3')
check('ONE SLIM\'s parts clear the Waveshare', clash(sw, ws) < 0.01)

# ---- the power button -------------------------------------------------------------------------------------------
check('power button: free in its hole and clear of the Waveshare at rest', clash(btn, shells + ws) < 0.01, f'{clash(btn, shells + ws):.3f} mm3')
_bb = btn.bounding_box()
check('power button: 0.2 mm from the PWR key at rest, stands 0.8 mm proud of the wall', abs(s.PWR_KEY_X - _bb[3] - 0.2) < 1e-6 and abs(-o.UPPER_W / 2 - _bb[0] - 0.8) < 1e-6)
check('power button: pushed 0.6 mm it presses the key 0.4 mm and still clears the shell', clash(s.plunger(0.6), shells) < 0.01)
check('power button: captured (its flange is bigger than the wall hole, the key is behind it)', s.PLUNGER['flange'][0] > s.PLUNGER['head'][0] + 2 * s.PLUNGER['hole'] and s.PLUNGER['flange'][1] > s.PLUNGER['head'][1] + 2 * s.PLUNGER['hole'])
check('power button: whole in the front shell (fitted before the Waveshare)', btn.bounding_box()[5] < s.Z_SPLIT)

# ---- battery, speaker, leads ---------------------------------------------------------------------------------
check('battery bay 3.0 x 34 x 52 is free (303450 fits; 302535 in its corner)', clash(bay, ws + one + shells + spk + slead) < 0.5 and clash(bay, lead) < 0.01,
      f'{clash(bay, ws + one + shells):.2f} mm3')
check('battery bay: 0.3 mm above the Waveshare\'s back parts (9.5 mm behind the glass)', abs(s.BAY['z0'] - (s.Z_GLASS + s.WS_PARTS) - 0.3) < 1e-9)
_gap = s.ZIN - (s.BAY['z0'] + s.BAY['t'])
check('foam tape behind the cell: 1.0 mm compressed 20-40 %', 0.2 <= 1 - _gap / s.FOAM_T <= 0.4, f'{_gap:.2f} mm gap')
check('speaker clears the Waveshare, shells, ONE SLIM', clash(spk, ws + shells + one) < 0.01)
check('cell lead: clear channel from the bay to J2, between two clips', clash(lead, ws + shells + spk + one + sw) < 0.01)
check('lead clips: clear of the Waveshare, the cell bay and the speaker', clash(clips, ws + bay + spk + one) < 0.01)
check('speaker lead: clear channel up the left side to J9', clash(slead, ws + shells + bay + one) < 0.01)

# ---- screws ---------------------------------------------------------------------------------------------------
_ws_bite = s.WS_SCREW_L - (s.DEPTH - s.Z_BACK)
check('Waveshare screws: M2 x 6 countersunk into its standoffs, 2.5 mm of thread (standoff 4 mm)', 2.0 <= _ws_bite <= 3.5, f'{_ws_bite:.2f} mm')
_lb = s.LOWER_SCREW_L - (s.DEPTH - s.Z_ONE)
check('lower screws: the same M2 x 6 through ONE SLIM into the front bosses, 3-6 mm bite', 3.0 <= _lb <= 6.0 and s.LOWER_SCREW_L == s.WS_SCREW_L, f'{_lb:.2f} mm')
check('screw heads flush, 0.5 mm+ of plastic under the countersink', (s.CSK_D - s.CSK_HOLE) / 2 + 0.5 <= s.DEPTH - s.Z_BACK)
check('posts bear on the standoff tips (clamp the board to the rim)', all(abs(min(p.bounding_box()[2] for p in (back ^ s.cyl_z(4.9, x, y, 0, 20)).decompose()) - s.Z_BACK) < 0.01 for x, y in s.WS_SCREWS))
check('screws clear the Waveshare parts and the battery', clash(screws, bay + spk + one) < 0.01)

# ---- keys (the ONE's caps, stems to the SLIM's switches) -----------------------------------------------------------
travel = o.PRETRAVEL + 0.25
for n, c in caps.items():
    check(f'{n} cap: free at rest and pressed', clash(c, shells) < 0.5 and clash(c.translate([0, 0, travel]), shells) < 0.5)
    tip = c.bounding_box()[5]
    check(f'{n} cap: stem stops {o.PRETRAVEL} mm above its switch', abs((s.Z_ONE - o.SW_H) - tip - o.PRETRAVEL) < 0.01, f'tip z {tip:.2f}')
    check(f'{n} cap: captured, clears panel', clash(c ^ s.box(-60, 60, -80, 70, o.COLLAR_Z, o.COLLAR_Z + 1.5), front) < 0.01 and clash(c, panel) < 0.01)
_wl = caps['left wing']
_mid = thinnest(_wl, -3, 0, (-o.WING_X, o.WING_Y + 3.5)); _rim = thinnest(_wl, -3, 0, (-o.WING_X, o.WING_Y + 6.0))
check('wing caps: dished (the middle sits lower than the rim), rim 1.8 mm proud', _rim - _mid > 0.25 and abs(_wl.bounding_box()[2] + o.WING_PROUD) < 0.02, f'rim {_rim:.2f}, toward the middle {_mid:.2f} mm above z 0')
_rk = caps['rocker']
_c = thinnest(_rk, -3, 0, (6.0, o.ROCKER_Y + 2.5)); _e = thinnest(_rk, -3, 0, (19.0, o.ROCKER_Y - 2.8))
check('rocker: domed (its ends lower than its middle), ends still 1.2 mm proud', _c - _e > 0.25 and _e >= 1.2, f'middle {_c:.2f}, end {_e:.2f} mm proud')

# ---- edge keys and USB (from the Waveshare 3D model) ----------------------------------------------------------
check('pin holes line up with the three edge keys (actuators 7.1-9.3 mm behind the glass)',
      all(clash(s.box(-40, -26.6, y - 0.5, y + 0.5, s.Z_GLASS + 7.6, s.Z_GLASS + 8.8), shells) < 0.01 for y in o.SIDE_KEYS_Y.values()))
_u = s.WS_TALL['USB-C']
check('USB-C opening centred on the socket', clash(s.box(-4.0, 4.0, o.BCY + o.BH / 2 - 6.0, o.Y_TOP + 1, s.Z_GLASS + 6.7, s.Z_GLASS + 10.75), shells) < 0.01)

# ---- builder's jigs -------------------------------------------------------------------------------------------------
check('the name on the back: 0.35 mm deep, 1.1 mm of back wall left under it', abs(s.TEXT_DEPTH - 0.35) < 1e-9 and s.BACK_WALL - s.TEXT_DEPTH >= 1.1 and vol(s.back_text() ^ back) < 0.01)
check('openings chamfered 0.5 mm on the outside (USB-C, power button, pin holes)', vol(s.chamfers() ^ shells) < 0.01)
jig = s.pin_jig()
check('pin jig: holds every pin at PIN_OUT and keeps clear of the board (one way only: fence on the strip end and edge)',
      clash(jig, s.one_board_drilled()) < 0.01 and clash(jig, pins) < 0.01)
_flip = s.one_board_drilled().mirror([1, 0, 0]).translate([o.STRIP_X[0] + o.STRIP_X[1], 0, 0])     # the strip turned over
check('pin jig: a board turned over hits the pegs and cannot sit flat', clash(jig, _flip) > 0.2, f'{clash(jig, _flip):.1f} mm3')

pf = o.physical(front)
slot = o.physical(s.box(-40, -30, s.PWR_Y - 1, s.PWR_Y + 1, s.PLUNGER_Z - 0.8, s.PLUNGER_Z + 0.8))
check('printed front: power button hole on the player\'s left (physical +x)', slot.bounding_box()[0] > 0 and clash(pf, slot) < vol(slot))

# ---- the printed files, as a print service reads them -------------------------------------------------------
import glob as _glob, trimesh as _tm
_bad = []
for _f in sorted(_glob.glob(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'stl', '*.stl'))):
    _m = _tm.load(_f)                                   # vertices merged by position, as slicers and quote sites do
    if not (_m.is_watertight and _m.is_winding_consistent and _m.body_count == 1): _bad.append(_os.path.basename(_f))
check('every STL is one watertight solid once its vertices are merged (quote sites and slicers accept it as is)', not _bad, ', '.join(_bad))

n_fail = R.count(False)
print(f"\nSTRUTHIO ONE SLIM CAD CHECK: {'all pass' if not n_fail else f'{n_fail} FAIL'} ({len(R)} checks)")
sys.exit(1 if n_fail else 0)
