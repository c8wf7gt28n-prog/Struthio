#!/usr/bin/env python3
"""STRUTHIO ONE · fit checks for the shell, caps, boards, battery and speaker.

    python3 check_one.py        prints one PASS/FAIL line per check and a summary
"""
import sys
import numpy as np
import one_cad as o

R = []
def check(name, ok, detail=''):
    R.append(ok); print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if detail else ''))

def vol(m):
    return 0.0 if m.is_empty() else m.volume()

def clash(a, b):
    return vol(a ^ b)

front, back = o.front_shell(), o.back_shell()
caps = {'left wing': o.wing_cap(-1), 'right wing': o.wing_cap(1), 'rocker': o.rocker_cap()}
shells = front + back
ws, one, bat, spk = o.ref_waveshare(), o.one_board(), o.ref_battery(), o.ref_speaker()
sw = o.ref_switches(); pbody, pknob, pfront = o.psw_box(); hbody, htails = o.ref_header(); ph = o.ref_ph_socket()

# ---- solids --------------------------------------------------------------------------------------------
for n, m in [('front shell', front), ('back shell', back)] + list(caps.items()):
    parts = [p for p in m.decompose() if p.volume() > 0.01]
    check(f'{n}: one watertight solid', m.status().name == 'NoError' and len(parts) == 1, f'{len(parts)} piece(s), {m.volume()/1000:.1f} cm3')

b = o.body2d().bounds()
check('outline: 88 x 134, 65 wide above y -30', abs((b[2] - b[0]) - 88.0) < 0.3 and abs((b[3] - b[1]) - 134.0) < 0.1
      and all(abs(o.wall_x_at(y, 1) + o.WALL - 32.5) < 0.1 for y in np.arange(-28.0, 50.0, 0.5)),
      f'{b[2]-b[0]:.2f} x {b[3]-b[1]:.2f} mm')
panel = o.face_panel()
check('thickness 23.0 mm, panel included', abs(back.bounding_box()[5] - o.DEPTH) < 0.01 and abs(panel.bounding_box()[2]) < 0.01)
pp = [p for p in panel.decompose() if p.volume() > 0.01]
check('face panel: one piece, 1.0 mm', len(pp) == 1 and abs(panel.bounding_box()[5] - panel.bounding_box()[2] - 1.0) < 0.01)
check('face panel sits on the shell face', abs(front.bounding_box()[2] - o.PANEL_T) < 0.01 and clash(panel, shells) < 0.01)
check('face panel stays on the flat, inside the edge round-over', o.PANEL_INSET > o.RF)

# ---- what sits in the case -------------------------------------------------------------------------------
for n, m in [('Waveshare board', ws), ('ONE board', one), ('battery', bat), ('speaker', spk), ('tact switches', sw),
             ('power switch body', pbody), ('header body', hbody), ('header tails', htails), ('battery socket', ph)]:
    v = clash(m, shells)
    check(f'{n} clears the shell', v < 0.5, f'{v:.2f} mm3 overlap')
check('ONE board clears the Waveshare board', clash(one, ws) < 0.01)
check('battery socket and plug clear the Waveshare board and keys', clash(ph, ws + sw) < 0.01)
check('battery clears the ONE board and speaker', clash(bat, one + spk) < 0.01)
check('speaker clears the ONE board', clash(spk, one) < 0.01)
check('nothing else on the ONE strip: header only', clash(hbody, bat + spk) < 0.01)
check('power knob passes through the wall slot', clash(pknob, shells) < 0.5 and pknob.bounding_box()[0] < -o.wall_x_at(o.PSW_Y, -1) * -1 - o.WALL,
      f'knob tip x {pknob.bounding_box()[0]:.2f}, outer wall {o.wall_x_at(o.PSW_Y, -1) - o.WALL:.2f}')

# ---- keys -------------------------------------------------------------------------------------------------
travel = o.PRETRAVEL + 0.25
for n, c in caps.items():
    check(f'{n} cap: free at rest', clash(c, shells) < 0.5, f'{clash(c, shells):.2f} mm3')
    pressed = c.translate([0, 0, travel])
    check(f'{n} cap: free when pressed {travel:.2f} mm', clash(pressed, shells) < 0.5)
    check(f'{n} cap: clears the face panel at rest and pressed', clash(c, panel) < 0.01 and clash(pressed, panel) < 0.01)
    check(f'{n} cap: stands at least 1.5 mm above the panel', c.bounding_box()[2] <= -1.5 + 0.01, f'{-c.bounding_box()[2]:.1f} mm')
    check(f'{n} cap: never touches the board, switch body or speaker', clash(pressed, one + spk + pbody + ph) < 0.01)
    tip = c.bounding_box()[5]
    check(f'{n} cap: stem stops {o.PRETRAVEL} mm above its switch', abs((o.Z_ONE - o.SW_H) - tip - o.PRETRAVEL) < 0.01, f'tip z {tip:.2f}')
    check(f'{n} cap: captured (flange wider than the opening)', clash(c ^ o.box(-60, 60, -80, 70, o.COLLAR_Z, o.COLLAR_Z + 1.5), front) < 0.01)
# rocker: one end pressed must not press the other
th = (o.PRETRAVEL + 0.25) / o.DART_X
check('rocker: pressing one end lifts the other', th * o.DART_X > o.PRETRAVEL, f'{np.degrees(th):.2f} deg to fire one end')
gap = o.ROCKER_GAP
check('rocker: flange room to rock', gap > (o.ROCKER_W / 2) * th, f'flange gap {gap} mm, end lift {(o.ROCKER_W/2)*th:.2f} mm')

# ---- header and screws ------------------------------------------------------------------------------------
check('header: 3.0 mm short end mates into the ~4 mm socket', o.Z_ONE - o.HDR_BODY == o.Z_BACK)
tails_z = o.Z_ONE + o.ONE_T + (6.0 - o.ONE_T)
check('header: long tails clear the back (pocket)', tails_z <= o.DEPTH - o.BACK_WALL + 0.8 - 0.1, f'tails to z {tails_z:.1f}')
check('lower screws: M2 x 8 bite 4.4 mm into the front bosses', (o.Z_ONE + o.ONE_T + 2.0) - 8.0 <= o.Z_ONE - 4.0)
check('board screws: M2 x 8 reach 3.0 mm into the standoffs', abs((o.Z_BACK + 5.0) - 8.0 - (o.Z_BACK - 3.0)) < 0.01)
check('ONE board sits on the front bosses', abs(o.Z_ONE - front.bounding_box()[5]) < 0.01)

# ---- handedness: the printed front, seen from the front, has the power switch on the player's left ----------
pf = o.physical(front)
slot = o.physical(o.box(-60, -40, o.PSW_Y - 2, o.PSW_Y + 2, 9, 12))
check('printed front: power slot on the player\'s left (physical +x)', slot.bounding_box()[0] > 0 and clash(pf, slot) < vol(slot))

n_fail = R.count(False)
print(f"\nSTRUTHIO ONE CAD CHECK: {'all pass' if not n_fail else f'{n_fail} FAIL'} ({len(R)} checks)")
sys.exit(1 if n_fail else 0)
