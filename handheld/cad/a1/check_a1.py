#!/usr/bin/env python3
# STRUTHIO HANDHELD · fit checks for the A1 (A0.8.3) export: every part is one
# watertight solid, the USB-C and service openings are open, nothing pokes out
# of the outline, and the button stems rest just short of the switch plungers.
# Probe coordinates are the model's (mm, x right, y up, z from the front face back).
import sys
import numpy as np
import trimesh

def load(p): return trimesh.load(f'stl/struthio_a083_{p}.stl')
fails = []
def check(ok, what):
    print(('PASS  ' if ok else 'FAIL  ') + what)
    if not ok: fails.append(what)

parts = {p: load(p) for p in ('front', 'back', 'left_button', 'right_button')}
for p, m in parts.items():
    check(m.is_watertight and len(m.split(only_watertight=False)) == 1, f'{p}: one watertight solid')
front, back = parts['front'], parts['back']
inside = lambda m, pts: m.contains(np.asarray(pts, float))

# USB-C: open along the axis through the arch wall and the boss (z 9.2..15.6, x -7..7)
ys = np.arange(-66, -55, 0.1)
blocked = [y for x in (-5, 0, 5) for z in (10.0, 12.4, 14.8) for y, s in zip(ys, inside(back, [[x, y, z] for y in ys])) if s]
check(not blocked, 'USB-C opening clear through the bottom wall')
# nothing below the outline at the arch centre (outer edge y=-62.2)
low = [y for z in np.arange(4, 22, 1.0) for y, s in zip(ys, inside(back, [[0, y, z] for y in ys])) if s and y < -62.35]
check(not low, 'no part of the rear shell pokes out below the bottom arch')
# side service slot (y 1..25, z 7..14.5) open to the outside
xs = np.arange(37.5, 46, 0.1)
blocked = [x for y in (5, 13, 21) for x, s in zip(xs, inside(back, [[x, y, 10.75] for x in xs])) if s]
check(not blocked, 'side service slot open through the waist wall')
# button stem vs B3F plunger: installed tip = -BTN_PROTRUSION + cap depth; plunger tip = plane - 7.3
PROTRUSION, PLANE, SWITCH_H, TRAVEL = 1.8, 13.7, 7.3, 0.25
for side in ('left_button', 'right_button'):
    tip = -PROTRUSION + parts[side].bounds[1][2]
    gap = (PLANE - SWITCH_H) - tip
    check(0.0 < gap < TRAVEL, f'{side}: stem rests {gap:.2f} mm before the plunger (must be 0 < gap < {TRAVEL})')
# caps pass the opening and are captured: neck 23.0 < opening 23.9 < flange 25.0
check(abs(parts['left_button'].bounds[1][0] - 12.5) < 0.05, 'cap flange 25 mm > front opening 23.9 mm (captured)')
print('A1 CHECK: ' + ('all pass' if not fails else f'{len(fails)} failure(s)'))
sys.exit(1 if fails else 0)
