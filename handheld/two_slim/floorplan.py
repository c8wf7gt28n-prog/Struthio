#!/usr/bin/env python3
"""STRUTHIO TWO SLIM · floorplan: the board outline inside the ONE SLIM's case, and where every big part goes.

    python3 floorplan.py       checks every area sits on the board and nothing overlaps on its side,
                               then draws out/floorplan.png (front side and back side, from the front)

Frame: the case frame of cad/one/one_cad.py (x right seen from the front, y up, mm). The face, the buttons and the
screen stay where they are on the ONE SLIM, so the face panel art fits unchanged.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'cad', 'one')); sys.path.insert(0, os.path.join(HERE, '..', 'cad', 'slim'))
import manifold3d as mf
import slim_cad as S
o = S.o

EDGE_GAP = 0.5                                   # board edge to the case's inside wall
BOARD_T = 0.8
SCREEN_C = (0.0, o.BCY)                          # panel centre (the ONE SLIM's screen centre)
GLASS = (o.BW, o.BH)                             # 61.0 x 92.44 (Waveshare 3D model: JHD0350A007V1 glass)

def board2d():
    """the board: the case's inside, EDGE_GAP in, the two corner screw holes cut out"""
    b = o.body2d().offset(-o.WALL - EDGE_GAP, mf.JoinType.Round)
    for x, y in o.LOWER_SCREWS: b = b - o.circle(2.4, x, y)
    return b

def rect(cx, cy, w, h): return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

# areas: name -> (side, (x0, y0, x1, y1), colour, note). side: 'F' front (toward the screen) or 'B' back.
sx, sy = SCREEN_C
AREAS = {
    'panel glass (on the front)': ('F', rect(sx, sy, *GLASS), '#9fc3e6', 'taped to the board; JHD0350A007V1 or equal'),
    'FPC slot': ('F', rect(0, sy - 41.5, 24.0, 2.0), '#ffffff', 'the ribbon goes through to the back, where the Waveshare wraps it'),
    'SW1 LEFT wing': ('F', rect(*o.switch_xy()['LEFT'], 7.0, 7.0), '#e0b040', 'TS-1187A'),
    'SW2 RIGHT wing': ('F', rect(*o.switch_xy()['RIGHT'], 7.0, 7.0), '#e0b040', ''),
    'SW3 DART L': ('F', rect(*o.switch_xy()['DART_L'], 7.0, 7.0), '#e0b040', ''),
    'SW4 DART R': ('F', rect(*o.switch_xy()['DART_R'], 7.0, 7.0), '#e0b040', ''),
    'J1 panel FPC socket': ('B', rect(0, sy - 12.3, 25.0, 5.5), '#d9534f', 'where the Waveshare has it (3D model): the ribbon length fits'),
    'FPC run (keep flat, no parts)': ('B', rect(0, sy - 27.5, 25.0, 24.5), '#f6dcdc', 'the ribbon lies here, slot to socket'),
    'battery 303450 (3.0 x 34 x 52)': ('B', (-23.5, 6.0, 28.5, 40.0), '#b9c2cc', 'lying across, on foam tape, behind the panel'),
    'U1 ESP32-S3-WROOM-1': ('B', rect(0, -55.0, 18.0, 25.5), '#3d8bff', 'antenna at the bottom edge'),
    'antenna keep-out': ('B', rect(0, -64.45, 18.0, 6.6), '#cfe3ff', 'no copper, both layers'),
    'J2 USB-C': ('B', rect(0, 58.0, 9.0, 7.4), '#555555', 'top edge, where the SLIM\'s opening is'),
    'power: U2 AXP2101, L5, L6, caps, J3 battery, Q2': ('B', (6.0, 41.0, 29.5, 54.0), '#7fbf7f', 'above the battery, beside USB-C'),
    'audio: U3 ES8311, U4 NS4150B, J4 speaker': ('B', (-29.0, -25.0, -14.0, 4.0), '#c39bd3', 'left, below the battery'),
    'U5 TCA9554 + panel parts (Q1, IM resistors)': ('B', (14.0, -25.0, 29.0, 4.0), '#f0ad4e', 'beside the socket'),
    'side keys: POWER, RESET, BOOT': ('B', (-29.9, 18.5, -24.5, 42.0), '#e0b040', 'side-push at the left edge, the SLIM\'s heights'),
}

def check():
    from itertools import combinations
    bd = board2d(); bad = []
    for name, (side, (x0, y0, x1, y1), *_r) in AREAS.items():
        if name.startswith('panel glass'): continue                        # the glass is bigger than the board: it sits in front
        r = o.CS.square([x1 - x0, y1 - y0]).translate([x0, y0])
        if (r - bd).area() > 0.5: bad.append(f'{name}: {(r - bd).area():.1f} mm2 off the board')
    for (a, (sa, ra, *_)), (b, (sb, rb, *_)) in combinations(AREAS.items(), 2):
        if sa != sb or 'glass' in a or 'glass' in b: continue
        if 'keep-out' in a + b and 'U1' in a + b: continue
        if 'FPC slot' in a + b: continue
        ox = min(ra[2], rb[2]) - max(ra[0], rb[0]); oy = min(ra[3], rb[3]) - max(ra[1], rb[1])
        if ox > 0.01 and oy > 0.01: bad.append(f'{a} overlaps {b}')
    return bad

def draw(path):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Rectangle
    fig, axs = plt.subplots(1, 2, figsize=(14, 13))
    case = max(o.body2d().to_polygons(), key=len); bd = board2d().to_polygons()
    for ax, side, title in ((axs[0], 'F', 'FRONT side (toward the screen), seen from the front'),
                            (axs[1], 'B', 'BACK side, seen through the board from the front')):
        ax.add_patch(Polygon(case, closed=True, fill=False, ec='#444', lw=1.5, ls='--'))
        for poly in bd: ax.add_patch(Polygon(poly, closed=True, fc='#2f7d4a' if side == 'B' else '#3a8f57', ec='k', lw=1, alpha=0.35))
        for name, (s, (x0, y0, x1, y1), col, note) in AREAS.items():
            if s != side: continue
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=col, ec='k', lw=0.8, alpha=0.85 if 'glass' not in name else 0.35))
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, name.replace(': ', ':\n').replace(', ', ',\n') if (x1 - x0) < 30 else name,
                    ha='center', va='center', fontsize=7 if (x1 - x0) < 20 else 8)
        for x, y in o.LOWER_SCREWS: ax.add_patch(plt.Circle((x, y), 1.2, fc='white', ec='k'))
        ax.set_xlim(-40, 40); ax.set_ylim(-75, 67); ax.set_aspect('equal'); ax.set_title(title, fontsize=11)
        ax.grid(True, lw=0.3, alpha=0.5)
    fig.suptitle(f'STRUTHIO TWO SLIM floorplan v0.1 (diagram, mm, case frame) · board {BOARD_T} mm, case outline dashed', fontsize=13)
    fig.tight_layout(); fig.savefig(path, dpi=110); print('wrote', path)

if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    b = board2d().bounds()
    print(f'board {b[2] - b[0]:.1f} x {b[3] - b[1]:.1f} mm, {board2d().area() / 100:.1f} cm2')
    problems = check()
    print('\n'.join(problems) if problems else 'floorplan: every area on the board, nothing overlaps on its side')
    draw(os.path.join(HERE, 'out', 'floorplan.png'))
