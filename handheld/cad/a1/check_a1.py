#!/usr/bin/env python3
# STRUTHIO HANDHELD · fit checks for the A1 (A0.8.4) export: every part is one
# watertight solid, the USB-C and service openings are open, nothing pokes out
# of the outline, and the button stems rest just short of the switch plungers.
# Probe coordinates are the model's (mm, x right, y up, z from the front face back).
import sys
import numpy as np
import trimesh

def load(p): return trimesh.load(f'stl/struthio_a084_{p}.stl')
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
# caps: section the front shell and the caps and compare outlines in the plane
from shapely.geometry import Point
from shapely.ops import unary_union
BTN_X, BTN_Y, NECK_Z, FLANGE_Z = 21.5, -47.5, 2.0, 5.6       # cap-local z: neck, capture flange
def plane(m, z, dx=0.0, dy=0.0):
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    path, _ = sec.to_2D(to_2D=np.eye(4))
    return unary_union([poly for poly in path.polygons_full]).buffer(0)
face = plane(front, 1.5)                                 # through the 3 mm front plate
backer = plane(front, 3.9)                               # through the lower backer plate and collars
holes = [h for poly in getattr(face, 'geoms', [face]) for h in poly.interiors]
from shapely.geometry import Polygon
holes = [Polygon(h) for h in holes]
slots = [h for h in holes if h.area < 20]
for side, name in ((-1, 'left_button'), (1, 'right_button')):
    c = Point(side * BTN_X, BTN_Y)
    hole = max((h for h in holes if h.contains(c)), key=lambda h: h.area)
    from shapely import affinity
    cap = parts[name]
    neck = affinity.translate(plane(cap, NECK_Z), side * BTN_X, BTN_Y)
    flange = affinity.translate(plane(cap, FLANGE_Z), side * BTN_X, BTN_Y)
    check(hole.contains(neck.buffer(0.2)), f'{name}: neck passes the opening with >= 0.2 mm clearance all round')
    check(flange.contains(hole.buffer(0.3)), f'{name}: flange overlaps the opening by >= 0.3 mm all round (captured)')
    check(flange.intersection(backer).area < 0.05, f'{name}: flange clears the backer plate and collar')
    web = min(hole.distance(sl) for sl in slots) if slots else 99
    check(web >= 1.5, f'{name}: {web:.2f} mm of shell between the opening and the speaker grille (>= 1.5)')
# the art sticker: below the lens land (so it never covers the screen), every hole inside it
import re
svgt = open('svg/struthio_a084_front_sticker.svg').read()
dd = re.search(r'<path d="([^"]*)"', svgt, re.S).group(1)
rings = sorted((Polygon([tuple(map(float, q.split(','))) for q in re.findall(r'-?[\d.]+,-?[\d.]+', sub)]).buffer(0)
                for sub in re.split(r'M', dd)[1:]), key=lambda q: -q.area)
LENS_LAND_BOTTOM = 13.78 - 81.0 / 2                       # model y of the lens land's lower edge
top = -rings[0].bounds[1]                                 # svg y is -model y
check(top <= LENS_LAND_BOTTOM - 0.3, f'art sticker top at y {top:.2f} stays below the lens land ({LENS_LAND_BOTTOM:.2f})')
check(len(rings) - 1 == 2 + 4, f'sticker has 6 clean holes (2 wings + 4 grille slots), found {len(rings) - 1}')
check(all(rings[0].contains(h.buffer(0.8)) for h in rings[1:]), 'every sticker hole sits >= 0.8 mm inside the sticker edge')
print('A1 CHECK: ' + ('all pass' if not fails else f'{len(fails)} failure(s)'))
sys.exit(1 if fails else 0)
