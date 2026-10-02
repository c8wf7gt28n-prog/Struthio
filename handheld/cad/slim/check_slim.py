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
sw = o.ref_switches(); pbody, pknob, _ = o.psw_box(); ph = o.ref_ph_socket(); smd = o.ref_smd()
lead = s.box(*(s.LEAD[k] for k in ('x0', 'x1', 'y0', 'y1', 'z0', 'z1'))) + s.box(*(s.LEAD_ALONG[k] for k in ('x0', 'x1', 'y0', 'y1', 'z0', 'z1')))
slead = s.box(*(s.SPK_LEAD[k] for k in ('x0', 'x1', 'y0', 'y1', 'z0', 'z1')))
panel = o.face_panel()

# ---- solids and the stack ----------------------------------------------------------------------------------
for n, m in [('front shell', front), ('back shell', back)] + list(caps.items()):
    parts = [p for p in m.decompose() if p.volume() > 0.01]
    check(f'{n}: one watertight solid', m.status().name == 'NoError' and len(parts) == 1, f'{len(parts)} piece(s), {m.volume()/1000:.1f} cm3')
check('thickness 16.5 mm, panel included', abs(back.bounding_box()[5] - s.DEPTH) < 0.01 and abs(panel.bounding_box()[2]) < 0.01,
      f'{back.bounding_box()[5]:.2f} mm')
b = o.body2d().bounds()
check('outline unchanged from the ONE: 74 x 136', abs(b[2] - b[0] - 74) < 0.3 and abs(b[3] - b[1] - 136) < 0.1, f'{b[2]-b[0]:.2f} x {b[3]-b[1]:.2f}')
check('face panel sits on the shell face', abs(front.bounding_box()[2] - o.PANEL_T) < 0.01 and clash(panel, shells) < 0.01)
check('stack adds up: panel + rim + Waveshare to its socket + ONE SLIM + 0.1 + back wall = 16.5',
      abs(o.PANEL_T + s.RIM + s.WS_SOCKET + s.ONE_T + 0.1 + s.BACK_WALL - s.DEPTH) < 1e-9)

# ---- walls ("not thin enough to feel cheap") --------------------------------------------------------------
check('back wall 1.5 mm solid (PETG: 4 perimeters / 5+ solid layers)', s.BACK_WALL >= 1.5 and thinnest(back, s.ZIN - 0.2, s.DEPTH + 0.1, (-5.0, -50.0)) >= 1.5 - 0.02,
      f'{thinnest(back, s.ZIN - 0.2, s.DEPTH + 0.1, (-5.0, -50.0)):.2f} mm at the controller zone')
check('back wall over the pin tips and trimmed leads: 1.0 mm (0.5 mm relief)', all(0.98 <= thinnest(back, s.ZIN - 0.2, s.DEPTH + 0.1, xy) <= 1.02 for xy in [s.pin_xy(n) for n in s.PINS] + s.THT_LEADS))
import os as _os
_t = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', 'pcb', 'slim', 'out', 'tht_leads.txt')
if _os.path.exists(_t):
    _leads = [tuple(map(float, l.split()[2:4])) for l in open(_t) if l.strip()]
    check('lead reliefs match the board file (pcb/slim)', all(min(abs(a - c) + abs(b - d) for c, d in s.THT_LEADS) < 0.01 for a, b in _leads))
check('face: 1.6 mm of shell behind the panel round the controls (the ONE had 0.8)', thinnest(front, 0.0, 5.0, (0.0, -66.0)) >= 1.6 - 0.02,
      f'{thinnest(front, 0.0, 5.0, (0.0, -66.0)):.2f} mm')
check('rim over the glass border: 0.5 mm, backed by the glass and covered by the panel', abs(thinnest(front, 0.0, s.Z_GLASS + 0.5, (0.0, o.BCY + o.AA_H / 2 + 3.0)) - s.RIM) < 0.03)
check('side walls 1.75 mm, 2.75 mm through the joint band', o.WALL >= 1.75 and s.LAND >= 1.0)

# ---- tongue and groove -------------------------------------------------------------------------------------
g0, g1 = s.GROOVE; t0, t1 = s.TONGUE
check('joint: tongue 0.8 mm in a 1.0 mm groove, 0.10 mm clearance each side', abs((t0 - g0) - 0.10) < 1e-9 and abs((g1 - t1) - 0.10) < 1e-9)
check('joint: 1.5 mm engagement, 0.1 mm clear at the bottom (the shells close on their faces)', abs(s.GROOVE_DEPTH - s.TONGUE_LEN - 0.1) < 1e-9 and s.TONGUE_LEN >= 1.5)
check('joint: groove lips 0.85 / 0.90 mm thick', g0 >= 0.85 - 1e-9 and (o.WALL + s.LAND) - g1 >= 0.9 - 1e-9)
check('joint: tongue clears the front shell (closed)', clash(s.tongue(), front) < 0.01, f'{clash(s.tongue(), front):.3f} mm3')
_tl = vol(s.tongue()) / ((t1 - t0) * s.TONGUE_LEN)
check('joint: the tongue runs round most of the case (stops only at the switch, USB-C and pin holes)', _tl > 330, f'{_tl:.0f} mm of tongue')
check('joint: shells meet at the split face (no gap, no overlap)', clash(front, back) < 0.01 and abs(front.bounding_box()[5] - s.Z_ONE) < 0.01)

# ---- the Waveshare and the ONE SLIM ---------------------------------------------------------------------
check('Waveshare clears the shells', clash(ws, shells) < 0.5, f'{clash(ws, shells):.2f} mm3')
check('glass sits on the 0.5 mm rim, in a pocket (x/y located by it)', abs(ws.bounding_box()[2] - s.Z_GLASS) < 0.01)
check('ONE SLIM lies on the J8 socket top', abs(s.Z_ONE - (s.Z_GLASS + s.WS_SOCKET)) < 1e-9 and clash(one, ws) < 0.01)
check('ONE SLIM: 0.1 mm under the back wall, pressed down by 11 pads', abs(s.ZIN - (s.Z_ONE + s.ONE_T) - 0.1) < 1e-9 and len(s.one_pads()) >= 11)
check('header pins: 3.0 mm into the socket (a standard header\'s tail length)', abs(s.PIN_INSERT - 3.0) < 1e-9 and clash(pins, shells) < 0.01)
check('ONE SLIM and its parts clear the shells', clash(one + sw + smd + ph, shells) < 0.5, f'{clash(one + sw + smd + ph, shells):.2f} mm3')
check('small parts on the ONE SLIM clear the Waveshare', clash(smd + ph + sw, ws) < 0.01)
check('power switch body clears the Waveshare and shells', clash(pbody, ws + shells) < 0.5)
_kb = pknob.bounding_box()
check('back shell closes over the power knob (slot open at the split)', clash(s.box(_kb[0], _kb[3], _kb[1], _kb[4], s.Z_SPLIT - 0.5, _kb[5]), back) < 0.01)

# ---- battery, speaker, leads ---------------------------------------------------------------------------------
check('battery bay 3.0 x 34 x 52 is free (303450 fits; 302535 in its corner)', clash(bay, ws + one + shells + spk + slead) < 0.5 and clash(bay, lead) < 0.01,
      f'{clash(bay, ws + one + shells):.2f} mm3')
check('battery bay: 0.3 mm above the Waveshare\'s back parts (9.5 mm behind the glass)', abs(s.BAY['z0'] - (s.Z_GLASS + s.WS_PARTS) - 0.3) < 1e-9)
_gap = s.ZIN - (s.BAY['z0'] + s.BAY['t'])
check('foam tape behind the cell: 1.0 mm compressed 20-40 %', 0.2 <= 1 - _gap / s.FOAM_T <= 0.4, f'{_gap:.2f} mm gap')
check('speaker clears the Waveshare, shells, ONE SLIM', clash(spk, ws + shells + one) < 0.01)
check('cell lead: clear channel from the bay to J2', clash(lead, ws + shells + spk + one + sw + smd) < 0.01)
check('speaker lead: clear channel up the left side to J9', clash(slead, ws + shells + bay + one) < 0.01)

# ---- screws ---------------------------------------------------------------------------------------------------
_ws_bite = s.WS_SCREW_L - (s.DEPTH - s.Z_BACK)
check('Waveshare screws: M2 x 6 countersunk into its standoffs, 2.5 mm of thread (standoff 4 mm)', 2.0 <= _ws_bite <= 3.5, f'{_ws_bite:.2f} mm')
_lb = s.LOWER_SCREW_L - (s.DEPTH - s.Z_ONE)
check('lower screws: M2 x 8 countersunk through ONE SLIM into the front bosses, 4-6 mm bite', 4.0 <= _lb <= 6.0, f'{_lb:.2f} mm')
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

# ---- edge keys and USB (from the Waveshare 3D model) ----------------------------------------------------------
check('pin holes line up with the three edge keys (actuators 7.1-9.3 mm behind the glass)',
      all(clash(s.box(-40, -26.6, y - 0.5, y + 0.5, s.Z_GLASS + 7.6, s.Z_GLASS + 8.8), shells) < 0.01 for y in o.SIDE_KEYS_Y.values()))
_u = s.WS_TALL['USB-C']
check('USB-C opening centred on the socket', clash(s.box(-4.0, 4.0, o.BCY + o.BH / 2 - 6.0, o.Y_TOP + 1, s.Z_GLASS + 6.7, s.Z_GLASS + 10.75), shells) < 0.01)

pf = o.physical(front)
slot = o.physical(s.box(-60, -40, o.PSW_Y - 2, o.PSW_Y + 2, 9, 12))
check('printed front: power slot on the player\'s left (physical +x)', slot.bounding_box()[0] > 0 and clash(pf, slot) < vol(slot))

n_fail = R.count(False)
print(f"\nSTRUTHIO ONE SLIM CAD CHECK: {'all pass' if not n_fail else f'{n_fail} FAIL'} ({len(R)} checks)")
sys.exit(1 if n_fail else 0)
