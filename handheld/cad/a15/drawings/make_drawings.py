#!/usr/bin/env python3
"""STRUTHIO HANDHELD · manufacturer drawings for A1.5, from the CAD's own numbers:
  STRUTHIO-CM1_drawing.pdf  conductive-silicone mat (for a keypad molder's quote)
  STRUTHIO-CP1_drawing.pdf  control PCB (with cad/a15/cp1/cp1_gerbers.zip)
  a15_face_layout.png       the front-face layout, for the build manual
Datum: the speaker-window centre (handheld x 0, y WINDOW_Y). Units mm.
    python3 cad/a15/drawings/make_drawings.py
"""
import os, re
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, PathPatch
from matplotlib.path import Path as MPath
from shapely.geometry import Polygon, Point
from shapely import affinity

HERE = os.path.dirname(os.path.abspath(__file__))
A15 = os.path.join(HERE, '..')
P = {}
for line in open(os.path.join(A15, 'STRUTHIO15.scad')).read().splitlines():
    for stmt in line.split('//')[0].split(';'):
        m = re.match(r'\s*([A-Z][A-Z0-9_]*)\s*=\s*(.+)$', stmt)
        if m:
            try: P[m.group(1)] = eval(m.group(2), {'__builtins__': {}}, P)
            except Exception: pass
OX, OY = P['SPKR_X'], P['WINDOW_Y']                 # datum
def svg_rings(name):
    t = open(os.path.join(A15, 'svg', name)).read()
    out = []
    for d in re.findall(r'<path d="([^"]*)"', t, re.S):
        for sub in re.split(r'M', d)[1:]:
            pts = [tuple(map(float, q.split(','))) for q in re.findall(r'-?[\d.]+,-?[\d.]+', sub)]
            if len(pts) > 2: out.append(affinity.translate(Polygon([(x, -y) for x, y in pts]).buffer(0), -OX, -OY))
    return sorted(out, key=lambda p: -p.area)
cp1 = svg_rings('cp1_outline.svg')
mat = svg_rings('mat_outline.svg')
keys = svg_rings('keys_outline.svg')

NAVY, GOLD, GREY = '#102838', '#E2A93F', '#777777'
def outline(ax, poly, **kw):
    x, y = poly.exterior.xy; ax.plot(x, y, **kw)
    for r in poly.interiors: x, y = r.xy; ax.plot(x, y, **kw)
def fill(ax, poly, **kw):
    verts, codes = [], []
    for r in [poly.exterior, *poly.interiors]:
        c = list(r.coords); verts += c; codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), **kw))
def dim(ax, p0, p1, off, text=None, fs=7):
    """linear dimension between p0 and p1, offset perpendicular by off"""
    import numpy as np
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = p1 - p0; n = np.array([-d[1], d[0]]) / (np.hypot(*d) or 1)
    a, b = p0 + n * off, p1 + n * off
    for p, q in ((p0, a), (p1, b)): ax.plot([p[0], q[0] + n[0] * 0.8 * np.sign(off)], [p[1], q[1] + n[1] * 0.8 * np.sign(off)], color=GREY, lw=0.4)
    ax.annotate('', a, b, arrowprops=dict(arrowstyle='<->', lw=0.6, color='k', shrinkA=0, shrinkB=0))
    m = (a + b) / 2 + n * 1.0 * np.sign(off)
    ang = np.degrees(np.arctan2(d[1], d[0]))
    if ang > 90 or ang < -90: ang += 180
    ax.text(m[0], m[1], text or f'{np.hypot(*d):.2f}', fontsize=fs, ha='center', va='center', rotation=ang)
def title_block(fig, title, sub, number, notes):
    fig.text(0.02, 0.975, title, fontsize=15, weight='bold', va='top', color=NAVY)
    fig.text(0.02, 0.945, sub, fontsize=9, va='top', color='#333')
    tb = fig.add_axes([0.70, 0.015, 0.29, 0.10]); tb.axis('off')
    tb.add_patch(Rectangle((0, 0), 1, 1, fill=False, lw=1, transform=tb.transAxes))
    rows = [('PART', number), ('PROJECT', 'STRUTHIO handheld, A1.5 (Build Manual 1.5 lock)'), ('SOURCE', 'cad/a15/STRUTHIO15.scad, checked by check_a15.py'),
            ('UNITS', 'mm; datum = speaker-window centre; general tol. +-0.15'), ('OWNER', 'R.A. Peddycoart')]
    for i, (k, v) in enumerate(rows):
        tb.text(0.02, 0.86 - i * 0.19, k, fontsize=6.5, weight='bold', transform=tb.transAxes)
        tb.text(0.20, 0.86 - i * 0.19, v, fontsize=6.5, transform=tb.transAxes)
    nb = fig.add_axes([0.70, 0.13, 0.29, 0.80]); nb.axis('off')
    y = 0.99
    for head, lines in notes:
        nb.text(0, y, head, fontsize=8, weight='bold', va='top', color=NAVY); y -= 0.028
        for l in lines:
            nb.text(0.01, y, l, fontsize=6.6, va='top', wrap=True); y -= 0.024
        y -= 0.012

# ---- shared numbers (datum-relative) ----------------------------------------------------------
wing = [(-P['BTN_X'] - OX, P['BTN_Y'] - OY), (P['BTN_X'] - OX, P['BTN_Y'] - OY)]
rock = (0 - OX, P['ROCKER_Y'] - OY)
dart = [(-P['DART_PITCH'] / 2 - OX, P['ROCKER_Y'] - OY), (P['DART_PITCH'] / 2 - OX, P['ROCKER_Y'] - OY)]
pins = [(x - OX, y - OY) for x, y in P['CP1_PIN_XY']]
posts = [(-P['SCREW_X'] - OX, P['SCREW_Y_BOT'] - OY), (P['SCREW_X'] - OX, P['SCREW_Y_BOT'] - OY)]
CP1Z = P['CP1_Z']
wing_h = CP1Z + P['WING_PROUD']           # key top above the CP1 face
rock_h = CP1Z + P['ROCKER_PROUD']
flange0 = CP1Z - (P['FRONT_T'] + P['KEY_FLANGE_T'])
flange1 = CP1Z - P['FRONT_T']

# ============================================================================================
# CM1
# ============================================================================================
fig = plt.figure(figsize=(16.54, 11.69))           # A3 landscape
title_block(fig, 'STRUTHIO-CM1  conductive-silicone control mat', 'one-piece compression-moulded keypad: LEFT WING, RIGHT WING, two-end DART rocker; 4 carbon pills',
            'STRUTHIO-CM1 rev A1.5', [
    ('MATERIAL / FINISH', ['VMQ silicone rubber, 50 Shore A nominal (+-5 for first-sample tuning only)',
                           'Colour: STRUTHIO gold, ref. #E2A93F (approve on first samples)', 'Key tops matte; no printing']),
    ('CONTACTS', ['4 conductive carbon pills, dia 6.0 x ~0.5, flush in the plunger faces',
                  'Contact resistance <= 100 ohm (on ENIG interdigitated pads, STRUTHIO-CP1)',
                  'Pill centres: wings (+-24.00, +1.00); DART (+-12.00, -14.20): 24.00 apart (LOCKED)']),
    ('FEEL TARGETS (LOCKED)', ['WINGS: travel 1.5, peak actuation 125 g, snap ratio 45-55 %',
                               'DART ENDS: travel 1.3, peak actuation 150 g, snap ratio 40-50 %',
                               'Rocker pivots on the opposite end flange; centre stop nub ends 1.10',
                               'above the PCB: a flat press stops before either pill (no double dart)',
                               'Skirt geometry is the moulder\'s, to meet the targets: report force-',
                               'travel curves for 5 keys of the first samples']),
    ('HEIGHTS (from the PCB face = mat underside)', [f'Web thickness {P["WEB_T"]:.1f}; web lies flat on the PCB',
        f'Wing key top {wing_h:.1f}; rocker top {rock_h:.1f}', f'Key flange {flange0:.1f} to {flange1:.1f} (captured behind the 3.0 shell face)',
        f'Wing pill face {P["WING_TRAVEL"]:.1f}; DART pill faces {P["ROCKER_TRAVEL"]:.1f}; centre nub {P["ROCKER_STOP_TRAVEL"]:.1f}',
        f'Shell holes = key outline + {P["KEY_CLEAR"]:.2f}; flange = outline + {P["KEY_FLANGE"]:.2f}']),
    ('FILES', ['dxf/keys_outline.dxf (key tops), dxf/mat_outline.dxf (web)', 'stl/struthio_a15_mat.stl (3D reference, handheld coordinates)',
               'Handheld coordinates = drawing + (0, -47.0)']),
    ('INSPECTION', ['First article: outline +-0.10 on key tops, +-0.15 elsewhere; pill position +-0.15',
                    'Force / travel / snap per key; contact resistance per pill; 10 x full-face press:',
                    'no sticking, rebound < 100 ms']),
])
ax = fig.add_axes([0.03, 0.30, 0.66, 0.62])
web = mat[0]
for h in mat[1:]: web = web.difference(h)
fill(ax, web, facecolor='#f6e3b8', edgecolor=GOLD, lw=0.8)
for k in keys: fill(ax, k, facecolor=GOLD, edgecolor='#8a6418', lw=0.8)
for c in wing + dart: outline(ax, Point(c).buffer(3.0), color='k', lw=0.6, ls='--')
outline(ax, Point(rock).buffer(1.5), color='k', lw=0.5, ls=':')
for c in wing + dart + [rock] + pins: ax.plot(*c, '+', color='k', ms=5, mew=0.6)
ax.plot(0, 0, 'o', ms=4, mfc='none', mec='r'); ax.text(0.6, 0.8, 'DATUM 0,0\n(window centre)', fontsize=6.5, color='r')
b = web.bounds
dim(ax, (b[0], b[1]), (b[2], b[1]), -4.5, f'{b[2]-b[0]:.2f}')
dim(ax, (b[2], b[1]), (b[2], b[3]), -9, f'{b[3]-b[1]:.2f}')
dim(ax, wing[0], wing[1], 13.0, f'{wing[1][0]-wing[0][0]:.2f}  wing pills')
dim(ax, dart[0], dart[1], -6.5, f'{dart[1][0]-dart[0][0]:.2f}  DART pills (LOCKED)')
dim(ax, (rock[0] - 22, rock[1] + 4.5), (rock[0] + 22, rock[1] + 4.5), 2.2, '44.00 rocker (LOCKED)')
dim(ax, (rock[0] + 22, rock[1] - 4.5), (rock[0] + 22, rock[1] + 4.5), -3.5, '9.00')
wk = [k for k in keys if k.centroid.x > 5][0].bounds
dim(ax, (wk[0], wk[3]), (wk[2], wk[3]), 2.5, f'{wk[2]-wk[0]:.2f} wing')
dim(ax, (wk[2], wk[1]), (wk[2], wk[3]), -3.0, f'{wk[3]-wk[1]:.2f}')
dim(ax, (0, 0), (0, rock[1]), -27, f'{-rock[1]:.2f}')
ax.text(-6.5, 7.6, f'window dia {P["WINDOW_D"]:.1f} (open)', fontsize=6.5)
for c in pins: ax.text(c[0] + 1.3, c[1] + 0.6, 'dia 2.2\nheat-stake pin', fontsize=5.5)
ax.set_aspect('equal'); ax.set_xlim(-45, 45); ax.set_ylim(-26, 17); ax.axis('off')
ax.set_title('TOP VIEW (player side)  -  key tops gold, web pale, pills dashed', fontsize=9, loc='left')
# section A-A through a wing pill, B-B through the rocker
def section(ax, title, half_w, top, travel, extra=None):
    w = half_w
    ax.add_patch(Rectangle((-30, -0.4), 60, 0.4, color='#1d5c35'))
    ax.text(-29.5, -1.3, 'PCB face (CP1)', fontsize=6)
    ax.add_patch(Rectangle((-30, 0), 30 - w - 2.0, P['WEB_T'], color='#f6e3b8', ec=GOLD))
    ax.add_patch(Rectangle((w + 2.0, 0), 30 - w - 2.0, P['WEB_T'], color='#f6e3b8', ec=GOLD))
    ax.plot([-w - 2.0, -w - 1.0, -w - 0.2], [P['WEB_T'], flange0, flange0], color=GOLD, lw=1.2)
    ax.plot([w + 2.0, w + 1.0, w + 0.2], [P['WEB_T'], flange0, flange0], color=GOLD, lw=1.2)
    ax.add_patch(Rectangle((-w - P['KEY_FLANGE'], flange0), 2 * (w + P['KEY_FLANGE']), P['KEY_FLANGE_T'], color=GOLD))
    ax.add_patch(Rectangle((-w, flange1), 2 * w, top - flange1, color=GOLD))
    ax.add_patch(Rectangle((-30, flange1), 30 - w - P['KEY_CLEAR'], P['FRONT_T'], color=NAVY, alpha=0.35))
    ax.add_patch(Rectangle((w + P['KEY_CLEAR'], flange1), 30 - w - P['KEY_CLEAR'], P['FRONT_T'], color=NAVY, alpha=0.35))
    ax.text(w + 4, flange1 + 1.2, 'shell face 3.0 (ref.)', fontsize=6)
    for x in (extra or [0]):
        ax.add_patch(Rectangle((x - 3.5, travel), 7.0, flange0 - travel, color=GOLD))
        ax.add_patch(Rectangle((x - 3.0, travel), 6.0, 0.5, color='k'))
        dim(ax, (x + 3.6, 0), (x + 3.6, travel), -0.8, f'{travel:.1f}', fs=6)
    dim(ax, (-w, 0), (-w, top), 3.5 if w < 15 else 2.5, f'{top:.1f}', fs=6.5)
    ax.set_aspect('equal'); ax.set_xlim(-30, 30); ax.set_ylim(-2, top + 1.5); ax.axis('off')
    ax.set_title(title, fontsize=8, loc='left')
section(fig.add_axes([0.03, 0.08, 0.32, 0.17]), 'SECTION A-A  wing key through its pill (true scale)', 7.0, wing_h, P['WING_TRAVEL'])
axb = fig.add_axes([0.36, 0.08, 0.33, 0.17])
section(axb, 'SECTION B-B  DART rocker through both pills + centre stop (true scale)', 22.0, rock_h, P['ROCKER_TRAVEL'], extra=[-12, 12])
axb.add_patch(Rectangle((-1.5, P['ROCKER_STOP_TRAVEL']), 3.0, flange0 - P['ROCKER_STOP_TRAVEL'], color='#8a6418'))
axb.text(-1.5, P['ROCKER_STOP_TRAVEL'] - 0.9, f'stop {P["ROCKER_STOP_TRAVEL"]:.1f}', fontsize=6)
fig.savefig(os.path.join(HERE, 'STRUTHIO-CM1_drawing.pdf')); fig.savefig(os.path.join(HERE, 'STRUTHIO-CM1_drawing.png'), dpi=110)
plt.close(fig)

# ============================================================================================
# CP1
# ============================================================================================
fig = plt.figure(figsize=(16.54, 11.69))
board = cp1[0]
for h in cp1[1:]: board = board.difference(h)
bb = board.bounds
title_block(fig, 'STRUTHIO-CP1  control PCB', 'two-layer contact board under STRUTHIO-CM1: four interdigitated pads, GND bus, 5-wire pad row',
            'STRUTHIO-CP1 rev A1.5', [
    ('BOARD', ['FR-4, 2 layers, 1.0 mm, 1 oz copper', 'Finish ENIG (contacts must be gold, no HASL)', 'Solder mask both sides; white legend on the back only',
               f'Size {bb[2]-bb[0]:.2f} x {bb[3]-bb[1]:.2f}; outline, window and notches in Edge_Cuts']),
    ('CONTACTS (front)', ['4 interdigitated pads dia 7.0, fingers 0.30 / gaps 0.30', 'Centres = CM1 pill centres; DART pads 24.00 apart (LOCKED)',
                          'Mask opening = pad + 0.10; keep contacts clean (no flux, no silk)']),
    ('NETS -> ESP32-S3 (Waveshare 3.5B)', ['LEFT  -> GPIO17 (LEFT WING)', 'RIGHT -> GPIO18 (RIGHT WING)', 'DART_L -> GPIO21 (DART LEFT)', 'DART_R -> GPIO38 (DART RIGHT)',
                                          'GND   -> board GND (common)', 'All active low; internal pull-ups in firmware v0.12']),
    ('WIRE PADS (back)', ['5 x plated dia 1.0 / pad 1.8, 2.54 pitch, left to right (front view):', 'GND, LEFT, DART_L, DART_R, RIGHT', '~24 AWG: W1 white L, W2 blue R, W3 yellow DL, W4 orange DR, W5 black GND']),
    ('MECHANICAL', ['2 x NPTH dia 2.2: carrier heat-stake pins', 'Notches R3.3 clear the lower case-screw posts', f'Window dia {P["WINDOW_D"]:.1f}: speaker path (CP1 is part of the baffle; seal ring on the back)',
                    'PUI speaker gasket seats on the back face around the window']),
    ('FILES', ['cad/a15/cp1/cp1_gerbers.zip (Gerber RS-274X + Excellon, DRC checked)', 'cad/a15/dxf/cp1_outline.dxf', 'Regenerate: python3 cad/a15/cp1/make_cp1.py']),
])
ax = fig.add_axes([0.03, 0.36, 0.66, 0.56])
fill(ax, board, facecolor='#1d5c35', edgecolor='k', lw=0.8)
for c in wing + dart: fill(ax, Point(c).buffer(3.5), facecolor='#f2d16b', edgecolor='#8a6418', lw=0.5)
for c in pins: ax.plot(*c, '+', color='w', ms=6, mew=0.6)
ax.plot(0, 0, 'o', ms=4, mfc='none', mec='r'); ax.text(0.8, 0.8, 'DATUM 0,0', fontsize=6.5, color='r')
dim(ax, (bb[0], bb[1]), (bb[2], bb[1]), -4.0, f'{bb[2]-bb[0]:.2f}')
dim(ax, (bb[2], bb[1]), (bb[2], bb[3]), -4.0, f'{bb[3]-bb[1]:.2f}')
dim(ax, wing[0], wing[1], 9.5, f'{wing[1][0]-wing[0][0]:.2f}')
dim(ax, dart[0], dart[1], -9.5, '24.00 DART (LOCKED)')
dim(ax, pins[0], pins[1], 2.5, f'{pins[1][0]-pins[0][0]:.2f} pins')
dim(ax, posts[0], posts[1], -3.5, f'{posts[1][0]-posts[0][0]:.2f} post notches')
dim(ax, (0, 0), (0, dart[0][1]), -16, f'{-dart[0][1]:.2f}')
dim(ax, (wing[1][0] + 4, 0), (wing[1][0] + 4, wing[1][1]), -2, f'{wing[1][1]:.2f}')
for c, n in zip(wing + dart, ('LEFT', 'RIGHT', 'DART_L', 'DART_R')): ax.text(c[0], c[1] - 4.8, n, fontsize=7, ha='center', color='w')
ax.set_aspect('equal'); ax.set_xlim(-46, 46); ax.set_ylim(-25, 16); ax.axis('off')
ax.set_title('FRONT VIEW (contact side, faces the mat)', fontsize=9, loc='left')
img = plt.imread(os.path.join(A15, 'cp1', 'cp1_layers.png'))
ai = fig.add_axes([0.03, 0.03, 0.66, 0.30]); ai.imshow(img); ai.axis('off')
fig.savefig(os.path.join(HERE, 'STRUTHIO-CP1_drawing.pdf')); fig.savefig(os.path.join(HERE, 'STRUTHIO-CP1_drawing.png'), dpi=110)
plt.close(fig)

# ============================================================================================
# face layout for the manual (handheld coordinates)
# ============================================================================================
fig, ax = plt.subplots(figsize=(11, 7.5))
def hh(p): return affinity.translate(p, OX, OY)
st = svg_rings('struthio_a15_front_sticker.svg')
fill(ax, hh(st[0]), facecolor='#0b1a28', edgecolor='none')
for k in keys: fill(ax, hh(k), facecolor=GOLD, edgecolor='#8a6418', lw=0.8)
for h in st[1:]:
    if h.area < 30: fill(ax, hh(h), facecolor='#444', edgecolor='none')
outline(ax, Point(P['SPKR_X'], P['SPKR_Y']).buffer(14.0), color='#5aa9e6', lw=1, ls='--')
for c in wing + dart: outline(ax, hh(Point(c).buffer(3.0)), color='w', lw=0.6, ls=':')
ax.plot([-30.5, 30.5, 30.5, -30.5], [-32.44, -32.44, -27, -27], color='#999', lw=0.8, ls='--')
ax.text(0, -30.3, 'Waveshare board ends here (y -32.44)', ha='center', fontsize=7, color='#bbb')
ax.annotate('', (-P['DART_PITCH']/2, P['ROCKER_Y'] - 7.2), (P['DART_PITCH']/2, P['ROCKER_Y'] - 7.2), arrowprops=dict(arrowstyle='<->', color='w', lw=0.8))
ax.text(0, P['ROCKER_Y'] - 8.6, 'DART contacts 24.0', ha='center', color='w', fontsize=7.5)
for (x, y), lab in zip([(-P['BTN_X'], P['BTN_Y']), (P['BTN_X'], P['BTN_Y']), (0, P['ROCKER_Y'])], ['LEFT WING  GPIO17', 'RIGHT WING  GPIO18', 'DART ROCKER  GPIO21 | GPIO38']):
    ax.text(x, y + (11.0 if 'WING' in lab else -1.0) if 'WING' in lab else y, lab, ha='center', va='center', fontsize=8, color='k' if 'DART' in lab else 'w', weight='bold')
ax.text(P['SPKR_X'] - 9.5, P['SPKR_Y'] + 15.2, 'PUI speaker outline (behind CP1)', color='#5aa9e6', fontsize=7)
ax.set_aspect('equal'); ax.set_xlim(-46, 46); ax.set_ylim(-71, -26); ax.axis('off')
ax.set_title('A1.5 control face (mm, handheld coordinates): 28 x 18.5 silicone wings, 44 x 9 DART rocker, grille over the speaker window', fontsize=9)
fig.savefig(os.path.join(HERE, 'a15_face_layout.png'), dpi=150, bbox_inches='tight')
print('wrote CM1 / CP1 drawings and a15_face_layout.png')
