#!/usr/bin/env python3
"""STRUTHIO ONE · the single build manual (Windows 11), in build order, as one A4 PDF.

    /usr/bin/python3 tools/manual/one_manual.py OUT.pdf

Everything shown is real or drawn from the real design:
  - terminal screenshots: captures/one_flash_prebuilt.txt is the unedited output of the manual's own flash
    command (run against Espressif's ESP32-S3 emulator); lines are only left out, shown as  · · ·
  - game screens: fw_ready.png / fw_play.png are frames from the release firmware in the emulator;
    fw_service_one_example.png is drawn by the firmware's own text code (service_shot.c) with example values
  - assembly pictures: docs/renders/one/steps (tools/visuals/one_steps.mjs) from the case and board models
  - diagrams: drawn here from cad/one/one_cad.py's numbers
  - Windows windows (installer, Device Manager) are drawn illustrations, labelled as such
"""
import base64, html, io, os, subprocess, sys, tempfile, datetime
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
HH = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HH, 'cad', 'one'))
from termshot import shot
import one_cad as o

CAP = os.path.join(HERE, 'captures'); REN = os.path.join(HH, 'docs', 'renders', 'one')
E = html.escape
COMMIT = subprocess.check_output(['git', '-C', HH, 'rev-parse', '--short', 'HEAD']).decode().strip()
TODAY = datetime.date.today().isoformat()

def img(path, w=None, cls='', crop_dark=False, maxh=None):
    im = Image.open(path).convert('RGB')
    if crop_dark:                                             # trim the empty studio background
        bg = im.getpixel((2, 2)); px = im.load(); W, H = im.size
        xs = [x for x in range(0, W, 4) if any(abs(px[x, y][0] - bg[0]) + abs(px[x, y][2] - bg[2]) > 24 for y in range(0, H, 6))]
        ys = [y for y in range(0, H, 4) if any(abs(px[x, y][0] - bg[0]) + abs(px[x, y][2] - bg[2]) > 24 for x in range(0, W, 6))]
        if xs and ys: im = im.crop((max(0, xs[0] - 30), max(0, ys[0] - 30), min(W, xs[-1] + 30), min(H, ys[-1] + 30)))
    if im.width > 1400: im = im.resize((1400, round(im.height * 1400 / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'JPEG', quality=86)
    st = (f'width:{w};' if w else '') + (f'max-height:{maxh};' if maxh else '')
    return f'<img class="{cls}" style="{st}" src="data:image/jpeg;base64,{base64.b64encode(b.getvalue()).decode()}">'

def png(path, w=None, cls=''):
    data = base64.b64encode(open(path, 'rb').read()).decode()
    return f'<img class="{cls}" style="{f"width:{w};" if w else ""}" src="data:image/png;base64,{data}">'

def fig(content, cap, kind=''):
    tag = {'illus': ' <span class="tag">illustration</span>', 'real': ' <span class="tag real">screenshot</span>',
           'render': ' <span class="tag">from the 3D model</span>', 'diag': ' <span class="tag">diagram</span>'}.get(kind, '')
    return f'<figure>{content}<figcaption>{cap}{tag}</figcaption></figure>'

# ======================================================================================================
# SVG helpers
# ======================================================================================================
C = dict(navy='#0d2a4a', ink='#16202b', gold='#f29a1d', orange='#f0882a', blue='#2f74d0', sky='#7fb6ff', green='#2e9d5b',
         red='#d24a3c', grey='#8a96a3', light='#eef2f6', pale='#f7f9fb', pcb='#1f6b3a', amber='#f6c344')

def svg(w, h, body, cls='diag'):
    return (f'<svg class="{cls}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="DejaVu Sans, Arial">'
            '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{C["ink"]}"/></marker></defs>{body}</svg>')

def txt(x, y, s, size=13, fill=None, anchor='middle', weight='normal', lh=1.25):
    lines = s.split('\n'); fill = fill or C['ink']
    y0 = y - (len(lines) - 1) * size * lh / 2
    t = ''.join(f'<tspan x="{x}" y="{y0 + i * size * lh:.1f}">{E(l)}</tspan>' for i, l in enumerate(lines))
    return f'<text font-size="{size}" fill="{fill}" text-anchor="{anchor}" dominant-baseline="middle" font-weight="{weight}">{t}</text>'

STYLE = {'step': ('#ffffff', C['navy']), 'start': (C['navy'], C['navy']), 'end': (C['green'], C['green']),
         'warn': ('#fff4e6', C['orange']), 'bad': ('#fdecea', C['red']), 'dec': ('#eef5ff', C['blue']), 'lane': (C['light'], C['grey'])}

def flow(W, H, nodes, edges, size=12.5):
    """nodes: id -> (cx, cy, w, h, label, style); edges: (a, b, label) or (a, b, label, 'side'|'down'|'up')"""
    out = []
    for a, b, *rest in edges:
        lab = rest[0] if rest else ''; how = rest[1] if len(rest) > 1 else None
        ax, ay, aw, ah = nodes[a][:4]; bx, by, bw, bh = nodes[b][:4]
        if how == 'side' or (how is None and abs(ay - by) < 1):
            sx = ax + (aw / 2 if bx > ax else -aw / 2); ex = bx - (bw / 2 if bx > ax else -bw / 2)
            d = f'M{sx},{ay} L{ex},{by}' if abs(ay - by) < 1 else f'M{sx},{ay} L{(sx + ex) / 2},{ay} L{(sx + ex) / 2},{by} L{ex},{by}'
            lx, ly = (sx + ex) / 2, min(ay, by) - 9
        elif how == 'up':
            d = f'M{ax},{ay - ah / 2} L{ax},{by + bh / 2 + 14} L{bx},{by + bh / 2 + 14} L{bx},{by + bh / 2}'
            lx, ly = (ax + bx) / 2, by + bh / 2 + 6
        else:
            sy = ay + ah / 2; ey = by - bh / 2; my = (sy + ey) / 2
            d = f'M{ax},{sy} L{ax},{my} L{bx},{my} L{bx},{ey}' if abs(ax - bx) > 1 else f'M{ax},{sy} L{bx},{ey}'
            lx, ly = (ax + bx) / 2 + (6 if abs(ax - bx) < 1 else 0), my - 1
        out.append(f'<path d="{d}" fill="none" stroke="{C["ink"]}" stroke-width="1.6" marker-end="url(#ar)"/>')
        if lab: out.append(f'<rect x="{lx - len(lab) * 3.6 - 4}" y="{ly - 9}" width="{len(lab) * 7.2 + 8}" height="17" rx="4" fill="#fff"/>'
                           + txt(lx, ly, lab, 11.5, C['blue'], weight='bold'))
    for k, (cx, cy, w, h, label, st) in nodes.items():
        fillc, line = STYLE[st]
        if st == 'dec':
            out.append(f'<polygon points="{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}" fill="{fillc}" stroke="{line}" stroke-width="2"/>')
        else:
            out.append(f'<rect x="{cx - w / 2}" y="{cy - h / 2}" width="{w}" height="{h}" rx="{h / 2 if st in ("start", "end") else 9}" fill="{fillc}" stroke="{line}" stroke-width="2"/>')
        out.append(txt(cx, cy, label, size, '#fff' if st in ('start', 'end') else C['ink'], weight='bold' if st in ('start', 'end') else 'normal'))
    return svg(W, H, ''.join(out))

def outline_path(cs, f):
    d = ''
    for pg in cs.to_polygons():
        d += 'M' + ' L'.join(f'{f(x, y)[0]:.1f},{f(x, y)[1]:.1f}' for x, y in pg) + ' Z '
    return d

# ======================================================================================================
# diagrams drawn from the design
# ======================================================================================================
def d_overview():
    N = {
        'pcb': (130, 60, 220, 52, 'Order the board\n(JLCPCB, package 3)', 'step'),
        'pan': (370, 60, 220, 52, 'Order the face panel\n(acrylic shop, package 2)', 'step'),
        'prt': (610, 60, 220, 52, 'Print the 5 parts\n(package 4)', 'step'),
        'buy': (850, 60, 220, 52, 'Buy Waveshare board,\nbattery, screws, foam', 'step'),
        'fl': (490, 165, 330, 54, 'Flash the full game onto the Waveshare\n(Windows 11, package 1)  ·  Part 4', 'warn'),
        'as': (490, 255, 330, 50, 'Assemble: steps 1-9  ·  Part 5', 'step'),
        'pw': (490, 340, 330, 50, 'First power + test every control\nsteps 10-13  ·  Part 6', 'step'),
        'pn': (490, 425, 330, 46, 'Stick on the face panel: step 14', 'step'),
        'go': (490, 505, 200, 44, 'PLAY', 'end'),
    }
    Ed = [('pcb', 'fl', ''), ('pan', 'fl', ''), ('prt', 'fl', ''), ('buy', 'fl', ''), ('fl', 'as', ''), ('as', 'pw', ''), ('pw', 'pn', 'all good'), ('pn', 'go', '')]
    return flow(980, 535, N, Ed)

def d_power_on():
    N = {
        'a': (210, 40, 330, 44, 'Slide the switch UP (toward the screen)', 'start'),
        'b': (210, 118, 330, 56, 'Battery → J2 → Q1 (reverse guard)\n→ slide switch → header pin 1 (BAT)', 'step'),
        'c': (210, 205, 330, 56, 'The ONE board holds the PWR key\n(header pin 24) down for ~3-8 s', 'warn'),
        'd': (210, 292, 330, 56, 'The Waveshare power chip (AXP2101)\nconnects the battery and turns on', 'step'),
        'e': (210, 379, 330, 56, 'The ESP32-S3 starts; the firmware\nswitches "long press = off" off', 'step'),
        'f': (210, 458, 330, 44, 'The game: READY', 'end'),
        'n1': (560, 205, 300, 76, 'Why: on battery alone this chip\nwaits for its PWR key before it\nconnects the battery\n(AXP2101 datasheet, 6.5.2)', 'lane'),
        'n2': (560, 379, 300, 62, 'So the long press can never\nswitch it off again: the slide\nswitch is the only on/off', 'lane'),
    }
    Ed = [('a', 'b', ''), ('b', 'c', ''), ('c', 'd', ''), ('d', 'e', ''), ('e', 'f', '')]
    s = flow(730, 490, N, Ed, size=12)
    return s.replace('</svg>', f'<path d="M375,205 L408,205" stroke="{C["grey"]}" stroke-dasharray="4 3"/><path d="M375,379 L408,379" stroke="{C["grey"]}" stroke-dasharray="4 3"/></svg>')

def d_nothing_happens():
    N = {
        's': (300, 34, 300, 40, 'Switch up: the screen stays dark', 'bad'),
        'q1': (300, 112, 230, 78, 'Try the switch\nDOWN instead.\nIt starts?', 'dec'),
        'y1': (620, 112, 260, 50, 'Your switch is ON when down.\nUse it that way: nothing else changes', 'end'),
        'q2': (300, 218, 230, 78, 'Plug USB-C in.\nIt starts?', 'dec'),
        'q3': (300, 330, 230, 78, 'Red wire on the\n+ side of J2?', 'dec'),
        'y3': (620, 330, 260, 58, 'Swap the two wires in the plug\n(step 6). Q1 protected the board', 'warn'),
        'q4': (300, 446, 230, 78, 'Press PWR through\nthe top pin hole 2 s:\nit starts?', 'dec'),
        'y4': (620, 446, 260, 58, 'The power-on pulse isn\'t reaching\npin 24: is the ONE board fully\non its four posts?', 'warn'),
        'y2b': (620, 218, 260, 50, 'Battery flat? Charge with the\nswitch ON (step 13), try again', 'warn'),
        'n4': (300, 548, 300, 50, 'Open the case: check the header\nsits in J8 and nothing is pinched', 'bad'),
    }
    Ed = [('s', 'q1', ''), ('q1', 'y1', 'yes', 'side'), ('q1', 'q2', 'no'), ('q2', 'y2b', 'yes', 'side'), ('q2', 'q3', 'no'),
          ('q3', 'y3', 'no', 'side'), ('q3', 'q4', 'yes'), ('q4', 'y4', 'yes', 'side'), ('q4', 'n4', 'no')]
    return flow(780, 585, N, Ed, size=11.5)

def d_flash_flow():
    N = {
        'a': (230, 34, 360, 40, 'Double-click FLASH_ME.bat (step 4.3)', 'start'),
        'q': (230, 112, 230, 78, 'It ends with\nDONE?', 'dec'),
        'ok': (230, 210, 330, 44, 'Unplug: ready to build in', 'end'),
        'f1': (560, 112, 280, 74, '"Flashing stopped"?\nDownload mode: hold BOOT,\ntap RST, release BOOT', 'warn'),
        'f2': (560, 210, 280, 58, '"No board found"?\nAnother USB-C cable (data),\nanother USB socket', 'warn'),
    }
    Ed = [('a', 'q', ''), ('q', 'ok', 'yes'), ('q', 'f1', 'no', 'side'), ('f1', 'f2', ''), ('f1', 'a', 'then again', 'up')]
    return flow(720, 245, N, Ed, size=12)

def d_controls():
    S = 4.2; X0, Y1 = -42, 67
    f = lambda x, y: ((x - X0) * S, (Y1 - y) * S)
    body = outline_path(o.body2d(), f)
    p = [f'<path d="{body}" fill="{C["navy"]}" stroke="{C["ink"]}" stroke-width="2"/>']
    x0, y0 = f(-o.AA_W / 2, o.BCY + o.AA_H / 2); x1, y1 = f(o.AA_W / 2, o.BCY - o.AA_H / 2)
    p.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="6" fill="#05080c" stroke="{C["gold"]}" stroke-width="3"/>')
    p.append(txt((x0 + x1) / 2, (y0 + y1) / 2, 'screen', 16, '#7b8794'))
    for sd in (-1, 1):
        cx, cy = f(sd * o.WING_X, o.WING_Y)
        p.append(f'<circle cx="{cx}" cy="{cy}" r="{o.BTN_D / 2 * S}" fill="#1c222b" stroke="{C["gold"]}" stroke-width="4"/>')
    rx0, ry0 = f(-o.ROCKER_W / 2, o.ROCKER_Y + o.ROCKER_H / 2); rx1, ry1 = f(o.ROCKER_W / 2, o.ROCKER_Y - o.ROCKER_H / 2)
    p.append(f'<rect x="{rx0}" y="{ry0}" width="{rx1 - rx0}" height="{ry1 - ry0}" rx="{o.ROCKER_R * S}" fill="#1c222b" stroke="{C["gold"]}" stroke-width="4"/>')
    def call(px, py, tx, ty, label, anchor):
        return (f'<path d="M{px},{py} L{tx},{ty}" stroke="{C["ink"]}" stroke-width="1.6"/><circle cx="{px}" cy="{py}" r="4" fill="{C["ink"]}"/>'
                + txt(tx + (8 if anchor == 'start' else -8), ty, label, 13.5, anchor=anchor, weight='bold'))
    W = 1100; ox = 420
    g = [f'<g transform="translate({ox},10)">' + ''.join(p) + '</g>']
    lx, ly = f(-o.WING_X, o.WING_Y); rx, ry = f(o.WING_X, o.WING_Y); kx, ky = f(-o.ROCKER_W / 2 + 4, o.ROCKER_Y); qx, qy = f(o.ROCKER_W / 2 - 4, o.ROCKER_Y)
    sx, sy = f(-o.LOWER_W / 2, o.PSW_Y); ux, uy = f(0, o.Y_TOP)
    g.append(call(ox + lx, 10 + ly, 340, 10 + ly - 40, 'LEFT wing: flap up-left', 'end'))
    g.append(call(ox + rx, 10 + ry, 850, 10 + ry - 40, 'RIGHT wing: flap up-right', 'start'))
    g.append(txt(ox + f(0, 0)[0], 10 + ly - 8, 'both together:\nstraight up', 13, C['blue'], weight='bold'))
    g.append(call(ox + kx, 10 + ky, 340, 10 + ky + 40, 'rocker LEFT end: dart left', 'end'))
    g.append(call(ox + qx, 10 + qy, 850, 10 + qy + 40, 'rocker RIGHT end: dart right', 'start'))
    g.append(call(ox + sx, 10 + sy, 340, 10 + sy - 10, 'power switch: UP = ON', 'end'))
    g.append(call(ox + ux, 10 + uy, 700, 10 + uy - 2, 'USB-C: charge + flash', 'start'))
    for name, dy in (('PWR', 25.0), ('RST', 16.5), ('BOOT', 8.0)):
        hx, hy = f(-o.UPPER_W / 2, o.BCY + dy)
        g.append(call(ox + hx, 10 + hy, 340, 10 + hy, f'{name} pin hole', 'end'))
    return svg(W, int(10 + (Y1 - o.Y_BOTTOM) * S + 20), ''.join(g))

def d_key():
    S = 15; r = o.BTN_D / 2; rw = r + o.KEY_CLEAR; rc = rw + o.COLLAR_T
    cx, cy = 260, 180
    p = [f'<circle cx="{cx}" cy="{cy}" r="{rc * S}" fill="#c9d3de" stroke="{C["navy"]}" stroke-width="2"/>',
         f'<circle cx="{cx}" cy="{cy}" r="{rw * S}" fill="#fff" stroke="{C["navy"]}" stroke-width="2"/>']
    sx0 = cx + (r - 0.6) * S; sx1 = cx + (r + o.KEY_OUT + 0.3) * S; sh = (o.KEY_W / 2 + 0.2) * S
    p.append(f'<rect x="{sx0}" y="{cy - sh}" width="{sx1 - sx0}" height="{2 * sh}" fill="#fff" stroke="{C["navy"]}" stroke-width="2"/>')
    p.append(f'<circle cx="{cx}" cy="{cy}" r="{r * S}" fill="#1c222b"/>')
    kx1 = cx + (r + o.KEY_OUT) * S; kh = o.KEY_W / 2 * S
    p.append(f'<rect x="{cx + (r - 0.6) * S}" y="{cy - kh}" width="{kx1 - cx - (r - 0.6) * S}" height="{2 * kh}" fill="{C["orange"]}"/>')
    for k, ((a, b), lab) in enumerate((((kx1 + 6, cy), 'the key on the cap ...'), ((sx1 + 4, cy + sh + 4), '... sits in the slot\nin the collar'))):
        p.append(f'<path d="M{a},{b} L{560},{110 + k * 120}" stroke="{C["ink"]}"/>' + txt(570, 110 + k * 120, lab, 14, anchor='start', weight='bold'))
    p.append(txt(cx, cy, 'cap', 14, '#fff'))
    return svg(820, 350, ''.join(p)).replace('class="diag"', 'class="diag" style="width:70%"')

def d_header():
    """side view, front at the top: the J8 socket is inside the Waveshare's thickness, its open face at Z_BACK"""
    S = 26; zmin = o.Z_BACK - 6.0; zb, zone = o.Z_BACK, o.Z_ONE
    z = lambda v: 30 + (v - zmin) * S
    p = []
    def rect(x0, x1, z0, z1, fill, label='', tc='#fff', size=13):
        p.append(f'<rect x="{x0}" y="{z(z0)}" width="{x1 - x0}" height="{(z1 - z0) * S}" fill="{fill}" stroke="{C["ink"]}" stroke-width="1"/>')
        if label: p.append(txt((x0 + x1) / 2, z((z0 + z1) / 2), label, size, tc, weight='bold'))
    rect(40, 700, zmin, zb - 4.0, '#5b6672', 'the Waveshare board (screen side up)')
    rect(40, 200, zb - 4.0, zb, '#8a96a3'); rect(420, 700, zb - 4.0, zb, '#8a96a3')
    rect(200, 420, zb - 4.0, zb, '#2b2f36')
    p.append(f'<path d="M150,{z(zb - 2.0)} L205,{z(zb - 2.0)}" stroke="#fff" stroke-width="1.6" marker-end="url(#ar)"/>' + txt(120, z(zb - 2.0), 'J8 socket\n(~4 mm)', 12.5, '#fff', weight='bold'))
    for px in (250, 310, 370):
        p.append(f'<rect x="{px - 4}" y="{z(zb - o.HDR_INSERT)}" width="8" height="{(zone + o.HDR_TAIL - (zb - o.HDR_INSERT)) * S}" fill="{C["amber"]}" stroke="#7a5b10"/>')
    rect(215, 405, zone - o.HDR_BODY, zone, '#111', 'header plastic 2.54')
    rect(40, 700, zone, zone + o.ONE_T, C['pcb'], 'ONE board 1.6')
    p.append(f'<rect x="640" y="{z(zmin)}" width="44" height="{(zone - zmin) * S}" fill="#2a4f7a" opacity=".28"/>')
    p.append(txt(662, z(zb + 1.4), 'front\nshell\npost', 12, C['navy'], weight='bold'))
    def dim(x, a, b, label, side):
        p.append(f'<path d="M{x},{z(a)} L{x},{z(b)}" stroke="{C["red"]}" stroke-width="2.2" marker-end="url(#ar)" marker-start="url(#ar)"/>'
                 + txt(x + (10 if side == 'r' else -10), z((a + b) / 2), label, 13.5, C['red'], anchor='start' if side == 'r' else 'end', weight='bold'))
    dim(440, zb - o.HDR_INSERT, zb, f'pins {o.HDR_INSERT:.1f} mm in', 'r')
    dim(440, zb, zone - o.HDR_BODY, f'gap {zone - o.HDR_BODY - zb:.1f} mm', 'r')
    return svg(740, int(z(zone + o.HDR_TAIL) + 20), ''.join(p)).replace('class="diag"', 'class="diag" style="width:78%"')

def d_battery():
    p = [f'<rect x="60" y="70" width="170" height="120" rx="8" fill="#e9edf1" stroke="{C["ink"]}" stroke-width="2"/>',
         txt(145, 50, 'J2 on the ONE board (white socket)', 13, weight='bold'),
         f'<rect x="80" y="95" width="40" height="30" fill="#c9d3de" stroke="{C["ink"]}"/>', f'<rect x="80" y="135" width="40" height="30" fill="#c9d3de" stroke="{C["ink"]}"/>',
         txt(55, 110, '+', 26, C['red'], weight='bold'), txt(55, 150, '−', 26, C['ink'], weight='bold'),
         f'<rect x="300" y="88" width="120" height="84" rx="6" fill="#fafafa" stroke="{C["ink"]}" stroke-width="2"/>', txt(360, 130, 'plug', 13),
         f'<path d="M420,110 C470,110 480,110 560,110" stroke="{C["red"]}" stroke-width="7" fill="none"/>',
         f'<path d="M420,150 C470,150 480,150 560,150" stroke="#222" stroke-width="7" fill="none"/>',
         txt(575, 110, 'red', 14, C['red'], 'start', 'bold'), txt(575, 150, 'black', 14, C['ink'], 'start', 'bold'),
         f'<path d="M298,130 L238,130" stroke="{C["ink"]}" stroke-width="2" marker-end="url(#ar)"/>', txt(268, 116, 'push in', 12),
         txt(330, 222, 'RED wire on the + side', 15, C['red'], weight='bold')]
    return svg(680, 240, ''.join(p)).replace('class="diag"', 'class="diag" style="width:72%"')

def d_layout():
    """seen from the BACK (as you build it): mirror x of the design frame"""
    S = 4.0; X0, Y1 = -44, 66
    f = lambda x, y: ((-x - X0) * S, (Y1 - y) * S)
    p = [f'<path d="{outline_path(o.body2d(), f)}" fill="#dfe6ee" stroke="{C["ink"]}" stroke-width="2"/>',
         f'<path d="{outline_path(o.board2d(), f)}" fill="#5b6672" stroke="{C["ink"]}"/>',
         f'<path d="{outline_path(o.one2d(), f)}" fill="{C["pcb"]}" stroke="{C["ink"]}" opacity=".95"/>']
    def rect(x0, x1, y0, y1, fill, label, op=1, tc='#fff', dash=False):
        a, b = f(x1, y1); c, d = f(x0, y0)
        p.append(f'<rect x="{min(a, c)}" y="{min(b, d)}" width="{abs(c - a)}" height="{abs(d - b)}" fill="{fill}" opacity="{op}" stroke="{C["ink"]}" '
                 + ('stroke-dasharray="5 4"' if dash else '') + '/>')
        if label: p.append(txt((a + c) / 2, (b + d) / 2, label, 12, tc, weight='bold'))
    B = o.BAT; rect(B['x0'], B['x1'], B['y0'], B['y1'], '#b9c2cc', 'battery\n(lead end\ndown)', tc=C['ink'])
    L = o.LEAD_CHANNEL; rect(L['x0'], L['x1'], L['y0'], L['y1'], C['red'], '', op=.35)
    SB = o.SPK_BAY; rect(SB['x0'], SB['x1'], SB['y0'], SB['y1'], 'none', 'speaker\n(in the back\nshell)', tc=C['navy'], dash=True)
    jx, jy = o.PH_SOCK; rect(jx - 1.5, jx + 6.4, jy - 2.1, jy + 4.1, '#fff', 'J2', tc=C['ink'])
    a = f(L['x0'] + 3, L['y1'] - 4); b = f(jx + 9, jy + 1)
    p.append(f'<path d="M{a[0]},{a[1]} L{a[0]},{b[1] - 30} L{b[0]},{b[1] - 30} L{b[0]},{b[1]}" stroke="{C["red"]}" stroke-width="3.5" fill="none" marker-end="url(#ar)"/>')
    sx, sy = f(-o.LOWER_W / 2 + 4, o.PSW_Y); p.append(txt(sx + 8, sy, 'switch', 12, '#fff', 'start', 'bold'))
    hx, hy = f(sum(o.STRIP_X) / 2, 10); p.append(txt(hx, hy, 'header\nstrip', 11.5, '#fff', weight='bold'))
    W = (44 + 44) * S
    return svg(int(W + 20), int((Y1 - o.Y_BOTTOM) * S + 10), ''.join(p)).replace('class="diag"', 'class="diag" style="width:52%"')

def d_stack():
    S = 18; rows = [(0, o.PANEL_T, '#cfe3ff', 'face panel (acrylic) 1.0'), (o.PANEL_T, o.FRONT_SKIN, C['navy'], 'front shell face 0.8'),
                    (o.Z_GLASS, o.Z_BACK, '#5b6672', 'Waveshare board + screen 11.5'), (o.Z_BACK, o.Z_ONE - o.HDR_BODY, '#fff', 'header pins: gap 2.7'),
                    (o.Z_ONE - o.HDR_BODY, o.Z_ONE, '#111', 'header plastic 2.54'), (o.Z_ONE, o.Z_ONE + o.ONE_T, C['pcb'], 'ONE board 1.6'),
                    (o.Z_ONE + o.ONE_T, o.DEPTH - o.BACK_WALL, '#eef2f6', 'header tails, posts'), (o.DEPTH - o.BACK_WALL, o.DEPTH, C['navy'], 'back shell 1.8')]
    p = []
    for z0, z1, fill, lab in rows:
        p.append(f'<rect x="40" y="{20 + z0 * S}" width="360" height="{(z1 - z0) * S}" fill="{fill}" stroke="{C["ink"]}"/>')
        p.append(txt(415, 20 + (z0 + z1) / 2 * S, lab, 12.5, anchor='start'))
    p.append(f'<path d="M25,20 L25,{20 + o.DEPTH * S}" stroke="{C["red"]}" stroke-width="2" marker-end="url(#ar)" marker-start="url(#ar)"/>' + txt(14, 20 + o.DEPTH / 2 * S, '23 mm', 13, C['red'], weight='bold').replace('<text', '<text transform="rotate(-90 14 %s)"' % (20 + o.DEPTH / 2 * S)))
    p.append(txt(40, 20 + o.DEPTH * S + 24, 'front at the top, back at the bottom (battery and speaker sit beside the strip, in the same depth)', 12, anchor='start'))
    return svg(720, int(20 + o.DEPTH * S + 44), ''.join(p)).replace('class="diag"', 'class="diag" style="width:80%"')

def d_block():
    N = {
        'bat': (95, 70, 150, 50, 'Battery\n1000 mAh LiPo', 'step'), 'j2': (95, 160, 150, 40, 'J2 socket', 'step'),
        'q1': (95, 240, 150, 50, 'Q1 AO3401A\nreverse guard', 'warn'), 'sw': (95, 330, 150, 50, 'Slide switch\nSW5 (ON/OFF)', 'step'),
        'hd': (330, 330, 170, 50, 'Header pin 1\nBAT', 'step'), 'pmu': (560, 330, 190, 56, 'AXP2101\npower chip', 'step'),
        'esp': (560, 205, 190, 56, 'ESP32-S3\n(the game)', 'start'), 'usb': (800, 330, 150, 50, 'USB-C\ncharge / flash', 'step'),
        'pul': (330, 205, 170, 64, 'Power-on pulse\nQ2 C1 R1 D1\n→ pin 24 PWR', 'warn'),
        'btn': (330, 85, 170, 64, '4 buttons\nGPIO 17 18\n21 38', 'step'), 'scr': (800, 205, 150, 50, 'Screen', 'step'),
        'spk': (800, 85, 150, 50, 'Speaker (J9)', 'step'),
    }
    Ed = [('bat', 'j2', ''), ('j2', 'q1', ''), ('q1', 'sw', ''), ('sw', 'hd', '', 'side'), ('hd', 'pmu', '', 'side'), ('usb', 'pmu', '', 'side'),
          ('pmu', 'esp', '', 'up'), ('esp', 'scr', '', 'side'), ('btn', 'esp', '', 'side'), ('pul', 'pmu', '', 'side'), ('esp', 'spk', '', 'side')]
    s = flow(900, 370, N, Ed, size=12)
    return s.replace('</svg>', f'<path d="M180,330 L245,330" stroke="none"/>'
                     + f'<path d="M95,355 L95,368 L330,368 L330,237" stroke="{C["orange"]}" stroke-dasharray="5 4" fill="none" marker-end="url(#ar)"/>'
                     + txt(210, 360, 'switch on starts the pulse', 11, C['orange'], weight='bold') + '</svg>')

def d_panel_layers():
    p = []
    rows = [('clear acrylic 1.0 mm (the front you touch)', '#d7ebff', 54), ('colour print (on its back)', 'url(#rb)', 22), ('white underprint', '#ffffff', 20),
            ('double-sided tape (black areas only)', '#f3e6a0', 16), ('front shell face', C['navy'], 40)]
    y = 30
    defs = '<defs><linearGradient id="rb" x1="0" x2="1"><stop offset="0" stop-color="#f29a1d"/><stop offset=".5" stop-color="#2f74d0"/><stop offset="1" stop-color="#d24a3c"/></linearGradient></defs>'
    for lab, fill, h in rows:
        p.append(f'<rect x="40" y="{y}" width="340" height="{h}" fill="{fill}" stroke="{C["ink"]}"/>' + txt(395, y + h / 2, lab, 15, anchor='start'))
        y += h
    p.append(f'<rect x="160" y="30" width="90" height="{54 + 22 + 20}" fill="#d7ebff" stroke="{C["blue"]}" stroke-dasharray="4 3"/>')
    p.append(txt(205, 78, 'window:\nno ink', 13, C['blue'], weight='bold'))
    return svg(760, y + 20, defs + ''.join(p)).replace('class="diag"', 'class="diag" style="width:80%"')

def d_bed():
    p = []
    def part(x, label, shape, note):
        p.append(f'<rect x="{x}" y="150" width="190" height="8" fill="#9aa3ad"/>')
        p.append(shape)
        p.append(txt(x + 95, 178, label, 13, weight='bold')); p.append(txt(x + 95, 200, note, 11.5, C['grey']))
    part(20, 'front shell', f'<path d="M45,150 L45,105 L60,105 L60,140 L175,140 L175,105 L190,105 L190,150 Z" fill="{C["navy"]}"/>', 'face on the bed')
    part(250, 'back shell', f'<path d="M275,150 L275,100 L290,100 L290,140 L405,140 L405,100 L420,100 L420,150 Z" fill="{C["navy"]}"/>', 'back on the bed')
    part(480, 'wing buttons, rocker', f'<rect x="545" y="128" width="60" height="22" fill="#1c222b"/><rect x="537" y="122" width="76" height="6" fill="#1c222b"/><rect x="566" y="70" width="18" height="52" fill="#1c222b"/>', 'top face on the bed')
    p.append(txt(360, 20, 'Side views, the bed at the bottom. No supports needed.', 13))
    return svg(720, 215, ''.join(p))

def d_win_python():
    p = [f'<rect x="10" y="10" width="560" height="250" rx="8" fill="#fff" stroke="#9aa3ad" stroke-width="2"/>',
         f'<rect x="10" y="10" width="560" height="34" rx="8" fill="#eef2f6"/>', txt(30, 27, 'Install Python 3.x (64-bit)', 13, anchor='start'),
         txt(40, 80, 'Install Now', 18, C['blue'], 'start', 'bold'), txt(40, 106, 'with default settings', 12, C['grey'], 'start'),
         txt(40, 150, 'Customize installation', 14, C['blue'], 'start'),
         f'<rect x="40" y="200" width="20" height="20" fill="{C["blue"]}" rx="3"/>', '<path d="M44,210 l5,6 l8,-11" stroke="#fff" stroke-width="3" fill="none"/>',
         txt(70, 210, 'Use admin privileges when installing py.exe', 12.5, anchor='start'),
         f'<rect x="40" y="228" width="20" height="20" fill="{C["blue"]}" rx="3"/>', '<path d="M44,238 l5,6 l8,-11" stroke="#fff" stroke-width="3" fill="none"/>',
         txt(70, 238, 'Add python.exe to PATH', 13, anchor='start', weight='bold'),
         f'<ellipse cx="170" cy="238" rx="150" ry="18" fill="none" stroke="{C["orange"]}" stroke-width="3"/>',
         f'<path d="M210,80 L330,80" stroke="none"/>', txt(420, 238, '← tick this', 14, C['orange'], 'start', 'bold'),
         f'<path d="M230,80 L300,80" stroke="none"/>', txt(330, 80, '← then click this', 14, C['orange'], 'start', 'bold')]
    return svg(580, 270, ''.join(p))

def d_win_devmgr():
    p = [f'<rect x="10" y="10" width="560" height="230" rx="8" fill="#fff" stroke="#9aa3ad" stroke-width="2"/>',
         f'<rect x="10" y="10" width="560" height="34" rx="8" fill="#eef2f6"/>', txt(30, 27, 'Device Manager', 13, anchor='start')]
    rows = [(0, '▸ Keyboards', False), (0, '▸ Mice and other pointing devices', False), (0, '▸ Monitors', False), (0, '▾ Ports (COM & LPT)', True),
            (1, 'USB Serial Device (COM5)', True), (0, '▸ Processors', False), (0, '▸ Universal Serial Bus controllers', False)]
    for i, (ind, label, hot) in enumerate(rows):
        y = 70 + i * 24
        if hot and ind: p.append(f'<rect x="58" y="{y - 11}" width="245" height="22" fill="#e1efff" stroke="{C["blue"]}"/>')
        p.append(txt(40 + ind * 26, y, label, 13, anchor='start', weight='bold' if hot and ind else 'normal'))
    p.append(txt(320, 166, '← appears when you plug the board in.\n    The number is yours: COM3, COM5, ...', 12.5, C['orange'], 'start', 'bold'))
    return svg(580, 250, ''.join(p))

def d_folders():
    t = ['C:\\struthio\\', '├─ prebuilt\\            ← the game, ready to flash  (you run the command here)',
         '│   ├─ bootloader.bin, partition-table.bin, struthio.bin', '│   └─ flash_args.txt   (addresses and settings for esptool)',
         '├─ handheld\\build\\assets\\   ← the art pack and the soundtrack', '├─ manual\\', '├─ STRUTHIO.bat          (the menu, for building it yourself)', '└─ README_FIRST.txt']
    return '<pre class="tree">' + E('\n'.join(t)) + '</pre>'

# ======================================================================================================
# screenshots
# ======================================================================================================
def flash_shot(out):
    lines = open(os.path.join(CAP, 'one_flash_prebuilt.txt'), encoding='utf-8').read().replace('\r', '').split('\n')
    keep = []
    for l in lines:
        if not l.strip() or 'VID/PID' in l or l.startswith('Writing at') or l.startswith('NOTE:'): continue
        keep.append(l)
    want = ['$ python', 'esptool v', 'Connected to ESP32-S3', 'Chip type', 'Stub flasher running', "Writing 'bootloader.bin'", 'Wrote ', 'Hash of data verified',
            "Writing 'struthio.bin'", 'Wrote ', 'Hash of data verified', "Writing '../handheld/build/assets/struthio.pak'", 'Wrote ', 'Hash of data verified',
            "Writing '../handheld/build/assets/struthio_music.ima'", 'Wrote ', 'Hash of data verified', 'Hard resetting']
    idx, k = [], 0
    for w in want:
        while k < len(keep) and w not in keep[k]: k += 1
        if k < len(keep): idx.append(k); k += 1
    show = []
    for j, i in enumerate(idx):
        if j and i != idx[j - 1] + 1: show.append('  · · ·')
        show.append(keep[i])
    marks = {}
    n = 1
    for i, l in enumerate(show):
        if 'Connected to ESP32-S3' in l: marks[i] = (1, 'cyan')
        if 'Hash of data verified' in l and n < 5: marks[i] = (2, 'green')
    shot(out, 'Terminal — ~/struthio/prebuilt (the emulator bench)', show, marks=marks, prompt='maker@bench:~/struthio/prebuilt$', max_cols=100)

# ======================================================================================================
# the manual
# ======================================================================================================
CSS = """
@page { size: A4; margin: 14mm 14mm 16mm 14mm; }
body { font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 10pt; line-height: 1.45; color: #16202b; margin: 0; }
h1 { font-size: 20pt; color: #0d2a4a; border-bottom: 3px solid #f29a1d; padding-bottom: 4px; margin: 0 0 10px; page-break-before: always; }
h1.first { page-break-before: auto; }
h2 { font-size: 13pt; color: #0d2a4a; margin: 16px 0 6px; page-break-after: avoid; }
p { margin: 5px 0; }
.part { font-size: 9pt; letter-spacing: .12em; color: #f29a1d; font-weight: bold; text-transform: uppercase; margin-top: 0; }
figure { margin: 8px 0 12px; text-align: center; page-break-inside: avoid; }
figure img, figure svg { max-width: 100%; }
figcaption { font-size: 8.6pt; color: #4a5866; margin-top: 3px; }
.tag { font-size: 7pt; background: #eef2f6; color: #4a5866; border-radius: 3px; padding: 1px 5px; margin-left: 4px; text-transform: uppercase; letter-spacing: .05em; }
.tag.real { background: #e4f6ea; color: #23744a; }
svg.diag { width: 100%; height: auto; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 10px; font-size: 9pt; }
th { background: #0d2a4a; color: #fff; text-align: left; padding: 4px 6px; }
td { border-bottom: 1px solid #d7dee6; padding: 4px 6px; vertical-align: top; }
code, .cmd { font-family: 'DejaVu Sans Mono', monospace; }
code { font-size: 8.8pt; background: #eef2f6; padding: 0 3px; border-radius: 3px; }
.cmd { display: block; background: #0f1a26; color: #e8eef5; padding: 8px 10px; border-radius: 6px; font-size: 9pt; margin: 6px 0; white-space: pre-wrap; }
.cmd b { color: #8be28b; font-weight: normal; }
pre.tree { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.8pt; background: #f7f9fb; border: 1px solid #d7dee6; border-radius: 6px; padding: 8px 10px; }
.step { display: flex; gap: 14px; align-items: flex-start; border: 1px solid #d7dee6; border-radius: 10px; padding: 10px 12px; margin: 10px 0; page-break-inside: avoid; }
.step .pic { flex: 0 0 34%; text-align: center; }
.step .pic img { width: 100%; max-height: 78mm; object-fit: contain; border-radius: 8px; }
.step .body { flex: 1; }
.num { display: inline-block; background: #f29a1d; color: #fff; font-weight: bold; border-radius: 50%; width: 26px; height: 26px; line-height: 26px; text-align: center; margin-right: 6px; }
.step h3 { margin: 0 0 6px; font-size: 12pt; color: #0d2a4a; }
.check { background: #e9f7ee; border-left: 4px solid #2e9d5b; padding: 6px 9px; margin: 8px 0; border-radius: 4px; font-size: 9.3pt; }
.warn { background: #fff4e6; border-left: 4px solid #f0882a; padding: 6px 9px; margin: 8px 0; border-radius: 4px; font-size: 9.3pt; }
.box { border: 1px solid #d7dee6; border-radius: 10px; padding: 8px 12px; margin: 8px 0; page-break-inside: avoid; }
ul.tick { list-style: none; padding-left: 4px; } ul.tick li::before { content: '☐  '; color: #0d2a4a; }
.cover { height: 265mm; display: flex; flex-direction: column; justify-content: space-between; text-align: center; }
.cover h1 { border: none; font-size: 40pt; margin: 6mm 0 0; letter-spacing: .02em; page-break-before: auto; }
.cover .sub { font-size: 14pt; color: #f29a1d; font-weight: bold; }
.cover img { max-height: 160mm; margin: 0 auto; }
.toc td { border: none; padding: 2px 6px; font-size: 10.5pt; }
.two { display: flex; gap: 12px; } .two > * { flex: 1; }
"""

def step(n, title, pic, body, check=None, warn=None):
    head = f'<h3><span class="num">{n}</span>{title}</h3>'
    extra = (f'<div class="warn">{warn}</div>' if warn else '') + (f'<div class="check">✔ {check}</div>' if check else '')
    pic_html = f'<div class="pic">{pic}</div>' if pic else ''
    return f'<div class="step">{pic_html}<div class="body">{head}{body}{extra}</div></div>'

def build(out_pdf):
    with tempfile.TemporaryDirectory() as t:
        fs = os.path.join(t, 'flash.png'); flash_shot(fs)
        st = lambda n: os.path.join(REN, 'steps', n + '.png')
        H = []
        # ---- cover --------------------------------------------------------------------------------------
        H.append(f'<div class="cover"><div><h1 class="first">STRUTHIO ONE</h1><div class="sub">Build manual · Windows 11 · every step in build order</div></div>'
                 f'{img(os.path.join(REN, "one_hero.png"), crop_dark=True, maxh="150mm")}'
                 f'<div style="font-size:9pt;color:#4a5866">From ordering the parts to playing: flash the full game, build it, test it.<br>'
                 f'Design locked · commit {COMMIT} · {TODAY}</div></div>')
        # ---- contents + how to read ------------------------------------------------------------------------
        H.append('<h1>Contents</h1><table class="toc">' + ''.join(
            f'<tr><td><b>Part {k}</b></td><td>{s}</td></tr>' for k, s in enumerate([
                'The whole build at a glance', 'What you need', 'Order and make the parts', 'Flash the full game (Windows 11)',
                'Assemble (steps 1-9)', 'First power and test (steps 10-13)', 'Fit the face panel (step 14)', 'How to play', 'If something is wrong',
                'How it works'], 1)) + '</table>'
                 '<h2>How to read this manual</h2><p>Do the parts in order. Each step has a picture, what to do, and a green '
                 '<b>✔ check</b>: don\'t go on until it\'s true. Orange boxes are the things that matter most.</p>'
                 '<p>Pictures are labelled: <span class="tag real">screenshot</span> real output of the real firmware and tools, '
                 '<span class="tag">from the 3D model</span> rendered from the exact case and board design (the parts each step adds glow orange), '
                 '<span class="tag">diagram</span> drawn from the design\'s own numbers, <span class="tag">illustration</span> a drawing of a Windows window to show where to click.</p>'
                 '<p>The six packages you need are referred to by number: <b>1</b> firmware flashing, <b>2</b> face panel print, <b>3</b> PCB (JLCPCB), '
                 '<b>4</b> 3D print, <b>5</b> documents (this manual), plus the full backup.</p>')
        # ---- part 1 -----------------------------------------------------------------------------------------
        H.append('<h1>The whole build at a glance</h1><p class="part">Part 1</p>'
                 '<p>Four things are made or bought at the same time; you flash the game as soon as the Waveshare board arrives, '
                 'then build, test, and finish with the face panel.</p>' + fig(d_overview(), 'The build, start to finish', 'diag')
                 + fig(img(os.path.join(REN, 'one_exploded.png'), crop_dark=True, maxh='95mm'), 'Everything that goes into it, front to back: face panel, front shell, buttons, Waveshare board, battery, ONE board, back shell', 'render'))
        # ---- part 2 -----------------------------------------------------------------------------------------
        H.append('<h1>What you need</h1><p class="part">Part 2</p><h2>Parts</h2><table><tr><th>✓</th><th>Item</th><th>Exactly what</th></tr>' + ''.join(
            f'<tr><td>☐</td><td><b>{a}</b></td><td>{b}</td></tr>' for a, b in [
                ('Waveshare ESP32-S3-Touch-LCD-3.5B', 'The bare board (not the "-C" cased version). Its 6 Ω 1 W speaker comes with it.'),
                ('LiPo battery', 'THOR-503450 (5 × 34 × 52 mm), 1000 mAh, ordered with a <b>JST PH 2.0 mm</b> 2-pin plug and an <b>80-100 mm</b> lead.'),
                ('ONE board', 'From JLCPCB, assembled (Part 3).'),
                ('Face panel', 'Laser-cut, back-printed 1.0 mm acrylic (Part 3).'),
                ('5 printed parts', 'Front shell, back shell, two wing buttons, rocker (Part 3).'),
                ('2 screws', 'M2 × 8 pan head, self-tapping or machine.'),
                ('1.75 mm filament', 'One 11 mm piece: the rocker\'s axle.'),
                ('Foam pad', '3 mm soft foam, about 30 × 45 mm, self-adhesive on one side.'),
                ('Double-sided tape', 'Thin; for the speaker and the face panel (clear transfer tape is best for the panel).'),
                ('USB-C data cable', 'One that carries data, not a charge-only cable.'),
                ('Blue paint pen (optional)', 'To colour the engraved wings and dart.')]) + '</table>'
                 '<h2>Tools</h2><ul class="tick"><li>A small Phillips screwdriver (PH0 or PH1) for the M2 screws</li><li>Scissors, a craft knife</li>'
                 '<li>A needle or pin (only if the battery plug needs its wires swapped)</li><li>A paperclip (the side pin holes, for re-flashing later)</li>'
                 '<li>A Windows 11 computer with internet access</li></ul>')
        # ---- part 3 -----------------------------------------------------------------------------------------
        bt = os.path.join(HH, 'pcb', 'one', 'out', 'board_top.png')
        H.append('<h1>Order and make the parts</h1><p class="part">Part 3</p>'
                 '<h2>The ONE board (package 3, JLCPCB)</h2><ol>'
                 '<li>On jlcpcb.com upload <code>struthio_one_gerbers.zip</code> (rev D): 2 layers, 1.6 mm, any colour.</li>'
                 '<li>Turn on <b>PCB Assembly</b>, top side, <b>Standard</b> PCBA (three parts are through-hole). Upload <code>BOM_JLCPCB.csv</code> and <code>CPL_JLCPCB.csv</code>.</li>'
                 '<li>In the placement preview, compare with the picture below: <b>J1</b> an ordinary header on the strip; <b>J2</b> opening toward the right edge; '
                 '<b>SW5</b> knob off the left edge; <b>Q1, Q2</b> single leg as on the silkscreen; <b>D1</b> band toward the left. Rotate any part that differs in 90° steps.</li></ol>'
                 + fig(png(bt, '52%'), 'The board as ordered (top side, seen from the front of the handheld), with every part\'s place', 'diag')
                 + '<h2>The face panel (package 2)</h2><p>Send the shop the files and this sentence: <b>1.0 mm clear cast acrylic, cut to the DXF, reverse-printed (colour, then white) '
                 'from the mirrored PNG, window left clear.</b> Cheaper: a clear cut panel and the art printed on sticker vinyl, stuck on its back.</p>'
                 + fig(img(os.path.join(HH, 'cad', 'one', 'panel', 'one_panel_proof.png'), maxh='70mm'), 'The proof: cut lines magenta, the clear window blue') + fig(d_panel_layers(), 'What the shop makes, in layers (the window stays clear)', 'diag')
                 + '<h2>The printed parts (package 4)</h2><p>PETG (or ASA), 0.2 mm layers, 4 walls, 6 top and bottom layers, 40 % infill: solid walls. Not PLA (it softens in a hot car). One of each STL. The wing buttons and rocker print engraving-down: keep the first layer neat.</p>'
                 + fig(d_bed(), 'How each part sits on the bed', 'diag'))
        # ---- part 4: flashing ---------------------------------------------------------------------------------
        H.append('<h1>Flash the full game (Windows 11)</h1><p class="part">Part 4 · do this as soon as the Waveshare board arrives, before you build it in</p>'
                 '<p>This puts the whole game on the board: the program, the art pack and the soundtrack. You need nothing but Python and one command. '
                 'The board stays on its own on the desk, connected by USB-C.</p>'
                 + step('4.1', 'Unzip the firmware package', '', '<p>Right-click <code>STRUTHIO_ONE_1_Firmware_Flashing.zip</code> → <b>Extract All…</b> → type <code>C:\\</code> → Extract. '
                        'You now have <code>C:\\struthio</code>:</p>' + d_folders(), warn='Not inside OneDrive, and no spaces in the path: <code>C:\\struthio</code> exactly.')
                 + step('4.2', 'Plug the board in', '', '<p>Connect the Waveshare to the PC with the USB-C <b>data</b> cable.</p>')
                 + step('4.3', 'Double-click FLASH_ME.bat', '', '<p>In <code>C:\\struthio</code>, double-click <b>FLASH_ME.bat</b>. The first time it installs Python and the flashing tool '
                        '(allow it if Windows asks), then finds the board by itself, writes the game, its pictures and its music, and checks every byte.</p>',
                        warn='"Windows protected your PC"? Click <b>More info</b>, then <b>Run anyway</b> (it is a plain text file you can read in Notepad).',
                        check='The window ends with DONE.')
                 + fig(png(fs, '100%'), 'What FLASH_ME runs underneath, by hand: the same esptool command (in <code>C:\\struthio\\prebuilt</code>: '
                       '<code>py -m esptool --chip esp32s3 -p COM5 -b 460800 write-flash @flash_args.txt</code>). <b>1</b> connected; <b>2</b> each part written and checked. '
                       'Captured against Espressif\'s ESP32-S3 emulator, so the port reads <code>socket://localhost:5555</code>; lines left out are marked · · ·', 'real')
                 + step('4.4', 'Start the game', fig(png(os.path.join(CAP, 'fw_ready.png'), '62%'), 'What the board shows: the game waiting at READY', 'real'),
                        '<p>Unplug the board: it\'s ready to build in. (Pressed RST with no buttons fitted, it shows the first power-on check waiting for presses: that\'s correct.)</p>',
                        check='FLASH_ME said DONE.')
                 + '<h2>If flashing doesn\'t work</h2>' + fig(d_flash_flow(), 'Flashing problems', 'diag')
                 + '<div class="box"><b>Download mode</b> (only if it won\'t connect): hold the board\'s <b>BOOT</b> button, press and release <b>RST</b>, release <b>BOOT</b>, then run 4.6 again. '
                   'FLASH_ME looks for the board again by itself. After a later re-flash through the finished case, the same buttons are behind the '
                   'pin holes on the left side (Part 8).</div>'
                 + '<div class="box"><b>Another way:</b> Espressif\'s browser flasher <b>espressif.github.io/esptool-js</b> (Chrome or Edge) does the same: '
                   'add <code>prebuilt\\bootloader.bin</code> at <code>0x0</code>, <code>partition-table.bin</code> at <code>0x8000</code>, <code>struthio.bin</code> at <code>0x10000</code>, '
                   '<code>handheld\\build\\assets\\struthio.pak</code> at <code>0x410000</code>, <code>struthio_music.ima</code> at <code>0xd10000</code>.</div>')
        # ---- part 5: assembly -----------------------------------------------------------------------------------
        H.append('<h1>Assemble</h1><p class="part">Part 5 · steps 1-9 · work on a soft cloth, nothing needs force</p>'
                 + step(1, 'Paint (optional)', fig(img(os.path.join(REN, 'one_front.png'), crop_dark=True), 'The engraved wings and dart, filled blue', 'render'),
                        '<p>Fill the engraved wings and the dart with the blue paint pen. Wipe the top faces clean, let it dry.</p>')
                 + step(2, 'Fit the wing buttons', img(st('step02_wing_buttons'), crop_dark=True),
                        '<p>From the <b>inside</b> of the front shell, push each round cap into its collar with its <b>key</b> (the small tab on its side) in the slot on the collar\'s outer side.</p>',
                        check='Both caps are in, keys in their slots, wings upright from the front. Each one springs back when pressed.')
                 + fig(d_key(), 'Why it only goes in one way: a wing button seen from the inside of the front shell; the key points away from the middle', 'diag')
                 + step(3, 'Fit the rocker', img(st('step03_rocker'), crop_dark=True),
                        '<p>Push the rocker into its collar from the inside. Cut an <b>11 mm</b> piece of 1.75 mm filament and push it through the hole in the collar\'s top wall until it stops.</p>',
                        check='The rocker tips freely both ways and springs back.')
                 + step(4, 'Lay in the Waveshare', img(st('step04_waveshare'), crop_dark=True),
                        '<p>Screen <b>down</b>, <b>USB-C at the top</b> (it lines up with the opening), its PWR/RST/BOOT buttons toward the pin holes on the left. It drops between the ribs.</p>',
                        check='It lies flat and doesn\'t slide.')
                 + step(5, 'Plug on the ONE board', img(st('step05_one_board'), crop_dark=True),
                        '<p>Set the slide switch <b>down (OFF)</b>. Hold the board over the Waveshare, header over the J8 socket, lower it straight and press evenly until it <b>rests on the four posts</b>.</p>',
                        warn='It stops on the posts by itself. Don\'t press harder: the pins are meant to go only 3.3 mm in.', check='The ONE board sits flat on all four posts.')
                 + fig(d_header(), 'How deep the header goes (side view, front at the top). The ONE board rests on the front shell\'s posts, and that sets the depth: the pins go 3.3 mm in and the plastic never touches the socket', 'diag')
                 + step(6, 'Battery', img(st('step06_battery'), crop_dark=True),
                        '<p>Check the plug against the <b>+</b> printed beside J2: <b>red to +</b>. Plug it into J2 from the right. Lay the cell on the Waveshare\'s back left of the strip, '
                        '<b>lead end down</b>, the lead flat in the gap down to the plug.</p>', check='Red wire on +, lead lying flat, nothing pinched.')
                 + fig(d_battery(), 'Battery plug polarity. Plugged the wrong way round it does nothing (Q1 blocks it): swap the two crimp contacts (lift each latch with a needle) and plug in again', 'diag')
                 + fig(d_layout(), 'Where things lie, seen from the back while you build (USB-C at the top). Red: the battery lead, flat on the Waveshare\'s back between the cell and the strip, down to J2', 'diag')
                 + step(7, 'Foam pad', img(st('step07_foam'), crop_dark=True), '<p>Stick the 3 mm foam pad on top of the battery. It presses the battery and the Waveshare forward when the case closes.</p>')
                 + step(8, 'Speaker into the back shell', img(st('step08_speaker'), crop_dark=True),
                        '<p>Tape on the speaker\'s back, stick it in the bay inside the back shell, <b>face toward the grille</b>. Plug its lead into <b>J9</b> on the Waveshare '
                        '(small 2-pin socket at its left edge, beside BOOT). Keep the back shell right beside the case: the lead is short.</p>', check='Speaker in its bay, plug in J9.')
                 + step(9, 'Close the case', img(st('step09_closed'), crop_dark=True),
                        '<p>Put the back shell\'s two top hooks into the slots inside the front shell\'s top edge and swing it down. The power knob slides into its slot, three pegs drop into '
                        'the Waveshare\'s holes. Fit the two M2 × 8 screws at the bottom, <b>snug, not tight</b>.</p>',
                        warn='If it doesn\'t close by itself, open it and look: a lead or the foam is in the way. Never force it.', check='Closed all round, no gap at the seam.'))
        # ---- part 6: power + test --------------------------------------------------------------------------------
        H.append('<h1>First power and test</h1><p class="part">Part 6 · steps 10-13</p>'
                 + step(10, 'Switch on', img(st('step10_first_power'), crop_dark=True),
                        '<p>Slide the switch <b>up</b>. Within a few seconds the screen lights. The first time it shows the <b>first power-on check</b> (next step). Slide it down: off at once.</p>'
                        '<p>Left alone, it dims after 30 s and switches itself off after 5 minutes (slide off and on to wake it).</p>',
                        check='The screen lights. (Nothing? Part 9.)')
                 + fig(d_power_on(), 'What happens when you slide the switch up', 'diag')
                 + step(11, 'The first power-on check', fig(png(os.path.join(CAP, 'fw_selftest_example.png'), '72%'), 'The check, all done (example values, shown on a ONE SLIM: the ONE has no POWER row)', 'real'),
                        '<p>Press each wing button and each rocker end <b>once</b>: each turns <b>OK</b> and clicks (the click is the speaker). <b>BATTERY</b> shows the cell. '
                        'When all four are OK, press <b>both wings</b>: the game starts. The check never runs again.</p>',
                        warn='STUCK DOWN next to a button: its cap rubs (Part 9). NO BATTERY: check the battery plug.', check='ALL GOOD, then the game.')
                 + step(12, 'Picture the wrong way up?', '', '<p>On the check screen, <b>hold LEFT for 2 s</b>. Later, in service mode (both wings held while switching on), <b>hold RIGHT for 1 s</b>. '
                        'Either is saved. The ONE board tells the firmware it is a ONE (header pin 9), so the 1000 mAh battery charges at 200 mA by itself.</p>')
                 + step(13, 'Charge', '', '<p>Plug USB-C in <b>with the switch ON</b>. With the switch OFF the battery is disconnected: USB still runs the game but doesn\'t charge.</p>',
                        check='In service mode BATT says CHARGING and USB.'))
        # ---- part 7: panel -------------------------------------------------------------------------------------------
        H.append('<h1>Fit the face panel</h1><p class="part">Part 7 · step 14, last</p>'
                 + step(14, 'Face panel', img(st('step14_face_panel'), crop_dark=True),
                        '<p>Peel the protective film off the back. Tape on the <b>black areas only</b>. Line the panel up 2.4 mm in from the case's edge all round, the wells over the buttons, '
                        'and press it down from the middle outward. Peel the front film.</p>', check='The panel sits flat with an even border all round; every button moves freely in its well.'))
        # ---- part 8: play ---------------------------------------------------------------------------------------------
        H.append('<h1>How to play</h1><p class="part">Part 8</p>' + fig(d_controls(), 'The controls, and what is on the sides', 'diag')
                 + '<div class="two">' + fig(png(os.path.join(CAP, 'fw_play.png'), '70%'), 'The game running', 'real')
                 + '<div><h2>The controls</h2><table><tr><th>Press</th><th>Does</th></tr>'
                   '<tr><td>LEFT wing</td><td>flap up and to the left</td></tr><tr><td>RIGHT wing</td><td>flap up and to the right</td></tr>'
                   '<tr><td>Both together</td><td>flap straight up</td></tr><tr><td>Hold a wing</td><td>steer</td></tr>'
                   '<tr><td>Rocker left / right end</td><td>aim-assisted dart, that way</td></tr>'
                   '<tr><td>Both held 1 s after GAME OVER</td><td>new run</td></tr>'
                   '<tr><td>Both held while switching on</td><td>service mode</td></tr></table>'
                   '<h2>Updating the game later</h2><p>Same as Part 4 through the USB-C in the top edge; the switch can be on or off. Download mode through the case: '
                   'a paperclip in the <b>BOOT</b> hole, tap <b>RST</b>, release.</p></div></div>')
        # ---- part 9: faults ---------------------------------------------------------------------------------------------
        H.append('<h1>If something is wrong</h1><p class="part">Part 9</p>' + fig(d_nothing_happens(), 'The screen stays dark when you switch on', 'diag')
                 + '<table><tr><th>What you see</th><th>What to do</th></tr>' + ''.join(f'<tr><td>{a}</td><td>{b}</td></tr>' for a, b in [
                     ('STUCK DOWN on the check screen, or a button counts by itself', 'Its stem touches the switch: take the cap out, sand 0.2 mm off the stem tip.'),
                     ('A button doesn\'t count', 'Is the ONE board on all four posts? Does the cap move freely?'),
                     ('No sound', 'Speaker plug in J9? Speaker face against the grille?'),
                     ('Back shell won\'t close', 'A lead or the foam is in the way. Knob in its slot? Never force it.'),
                     ('Picture upside down', 'Service mode, hold RIGHT 1 s.'),
                     ('Flashing fails', 'Part 4, "If flashing doesn\'t work".')]) + '</table>')
        # ---- part 10: how it works -----------------------------------------------------------------------------------------
        H.append('<h1>How it works</h1><p class="part">Part 10</p>' + fig(d_block(), 'The electrics: what the ONE board does', 'diag')
                 + fig(d_stack(), 'The 23 mm stack, front to back', 'diag')
                 + '<div><h2>The ONE board</h2><table><tr><th>Part</th><th>Job</th></tr>' + ''.join(f'<tr><td>{a}</td><td>{b}</td></tr>' for a, b in [
                     ('J1 header', 'into the Waveshare J8: BAT, GND, 4 buttons, PWR, and pin 9 to GND (tells the firmware it is a ONE)'), ('SW1-SW4', 'the wing buttons and rocker ends'),
                     ('SW5', 'the slide switch: a real battery cut'), ('J2', 'the battery plug'), ('Q1', 'reverse-battery guard'),
                     ('Q2, C1, R1, D1', 'power-on pulse on PWR (pin 24)')]) + '</table>'
                 + '<h2>Header pins used</h2><p>1 BAT · 3, 4, 29, 30 GND · 9 GND (model strap) · 5 GPIO21 (rocker L) · 7 GPIO38 (rocker R) · 16 GPIO17 (left wing) · 18 GPIO18 (right wing) · 24 PWR</p></div>'
                 + '<h2>Things to confirm on the first build</h2><table><tr><th>What</th><th>Designed for</th><th>If different</th></tr>' + ''.join(
                     f'<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>' for a, b, c in [
                         ('J8 socket depth', '~4 mm, pins 3.3 mm in', 'pins must hold; a 0.3 mm shim under the posts changes the depth'),
                         ('Waveshare hole size', '≥ 2.2 mm (pegs 1.8)', 'sand the pegs'), ('Speaker size, lead', 'bay 22 × 37 × 7.5 mm, lead ≥ 60 mm', 'any box that fits, with tape'),
                         ('Switch ON direction', 'up', 'use it the other way'), ('USB-C height', 'opening 12.8 × 7.8 mm', 'file it wider'),
                         ('Acrylic thickness', '1.0 ± 0.1 mm', 'the panel may sit a hair proud')]) + '</table>'
                 + f'<p style="font-size:8.5pt;color:#6b7783">STRUTHIO ONE build manual · commit {COMMIT} · {TODAY}. Made from the design files by tools/manual/one_manual.py.</p>')
        doc = f'<!doctype html><html><head><meta charset="utf-8"><title>STRUTHIO ONE build manual</title><style>{CSS}</style></head><body>{"".join(H)}</body></html>'
        hp = os.path.join(t, 'manual.html'); open(hp, 'w', encoding='utf-8').write(doc)
        subprocess.check_call(['node', os.path.join(HH, 'tools', 'package', 'html2pdf.mjs'), hp, out_pdf])

if __name__ == '__main__':
    build(os.path.abspath(sys.argv[1]))
