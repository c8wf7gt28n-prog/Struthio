#!/usr/bin/env python3
"""STRUTHIO ONE SLIM · the build manual (Windows 11), in build order, as one A4 PDF.

    /usr/bin/python3 tools/manual/slim_manual.py OUT.pdf

The same machinery and rules as the ONE's manual (one_manual.py): every picture is labelled screenshot, from the
3D model, diagram or illustration; terminal screenshots only leave lines out (shown as  · · ·).
  - flashing: captures/slim_flash_me.txt is the unedited output of flash_me.sh (FLASH_ME.bat's macOS / Linux twin,
    same steps and messages) run against Espressif's ESP32-S3 emulator in download mode
  - the first power-on check: captures/fw_selftest_example.png, drawn by the firmware's own text code with example
    values (selftest_shot.c); captures/fw_selftest_qemu.png is the real screen from the emulator
  - assembly pictures: docs/renders/slim/steps (tools/visuals/slim_steps.mjs) from the case and board models
  - diagrams: drawn here from cad/slim/slim_cad.py's numbers
"""
import os, sys, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
HH = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HH, 'cad', 'slim'))
import slim_cad as s                      # sets one_cad's numbers to the SLIM's (one_manual's diagrams share them)
import one_manual as M
from one_manual import img, png, fig, svg, txt, flow, step, C, CSS, E
from termshot import shot
o = s.o

CAP = M.CAP
REN = os.path.join(HH, 'docs', 'renders', 'slim')
COMMIT, TODAY = M.COMMIT, M.TODAY

# ======================================================================================================
# diagrams
# ======================================================================================================
def d_overview():
    N = {
        'pcb': (130, 60, 220, 52, 'Order the board\n(JLCPCB, package 3)', 'step'),
        'pan': (370, 60, 220, 52, 'Order the face panel\n(package 2)', 'step'),
        'prt': (610, 60, 220, 52, 'Print the parts\n(package 4)', 'step'),
        'buy': (850, 60, 220, 52, 'Buy the screen board,\ncell, speaker, screws', 'step'),
        'fl': (490, 160, 330, 50, 'Flash: double-click FLASH_ME.bat  ·  Part 4', 'warn'),
        'pr': (490, 240, 330, 50, 'Prepare the board: solder 12 pins  ·  Part 5', 'step'),
        'as': (490, 320, 330, 50, 'Assemble: steps 1-8  ·  Part 6', 'step'),
        'pw': (490, 400, 330, 50, 'Press power: the screen checks itself\nPart 7', 'step'),
        'pn': (490, 480, 330, 46, 'Face panel, with its jig  ·  Part 8', 'step'),
        'go': (490, 555, 200, 44, 'PLAY', 'end'),
    }
    Ed = [('pcb', 'fl', ''), ('pan', 'fl', ''), ('prt', 'fl', ''), ('buy', 'fl', ''), ('fl', 'pr', ''), ('pr', 'as', ''), ('as', 'pw', ''),
          ('pw', 'pn', 'all good'), ('pn', 'go', '')]
    return flow(980, 585, N, Ed)

def d_flash():
    N = {
        'a': (230, 34, 380, 40, 'Double-click FLASH_ME.bat', 'start'),
        'q': (230, 120, 240, 80, 'It ends with\n"DONE"?', 'dec'),
        'ok': (230, 220, 360, 44, 'Unplug: the board is ready to build in', 'end'),
        'f1': (580, 90, 300, 62, '"No board found"?\nAnother USB-C cable (a data one),\nanother USB socket', 'warn'),
        'f2': (580, 185, 300, 62, '"Flashing stopped"?\nDownload mode: hold BOOT,\ntap RESET, release BOOT', 'warn'),
    }
    Ed = [('a', 'q', ''), ('q', 'ok', 'yes'), ('q', 'f1', 'no', 'side'), ('f1', 'f2', ''), ('f2', 'a', '', 'up')]
    return flow(760, 255, N, Ed, size=12)

def d_pins():
    """side view: the jig, the board face down, a header strip going in long side first"""
    S = 22; X = 60
    p = []
    jig_top = 160
    p.append(f'<rect x="{X}" y="{jig_top}" width="{S * 9}" height="{S * (s.PIN_OUT + 2.0)}" fill="#e0b040" stroke="{C["ink"]}"/>')
    for i in range(3):
        hx = X + S * (2 + 2.54 * i)
        p.append(f'<rect x="{hx - S * 0.55}" y="{jig_top}" width="{S * 1.1}" height="{S * s.PIN_OUT}" fill="#fff" stroke="{C["ink"]}" stroke-width=".6"/>')
    p.append(f'<rect x="{X - 10}" y="{jig_top - S * s.ONE_T}" width="{S * 9 + 20}" height="{S * s.ONE_T}" fill="{C["pcb"]}" stroke="{C["ink"]}"/>')
    plastic_y = jig_top - S * s.ONE_T - S * 1.6
    p.append(f'<rect x="{X + S * 0.8}" y="{plastic_y - S * 2.5}" width="{S * 7.5}" height="{S * 2.5}" fill="#222" />')
    for i in range(3):
        hx = X + S * (2 + 2.54 * i)
        p.append(f'<rect x="{hx - S * 0.32}" y="{plastic_y - S * 2.5 - S * 3.0}" width="{S * 0.64}" height="{S * (3.0 + 2.5 + 1.6 + s.ONE_T + s.PIN_OUT)}" fill="#d9b24c" stroke="{C["ink"]}" stroke-width=".6"/>')
    lx = X + S * 9 + 30
    p.append(txt(lx, plastic_y - S * 1.2, '2  header plastic: slide it off\n    after soldering', 13, anchor='start'))
    p.append(txt(lx, plastic_y + S * 0.7, '3  solder here, then snip\n    the pins flush', 13, anchor='start', fill=C['orange'], weight='bold'))
    p.append(txt(lx, jig_top - S * 0.4, '1  the board, FACE DOWN', 13, anchor='start', fill=C['pcb'], weight='bold'))
    p.append(txt(lx, jig_top + S * 2.2, f'the jig: each pin stops\n{s.PIN_OUT} mm out of the board', 13, anchor='start'))
    return svg(620, int(jig_top + S * (s.PIN_OUT + 2.0) + 20), ''.join(p))

def d_power():
    N = {
        'a': (200, 36, 330, 44, 'Press the button on the left side', 'start'),
        'b': (200, 120, 330, 52, 'The screen lights within a second\n(the very first time: hold it until it does)', 'step'),
        'c': (200, 210, 330, 44, 'Play', 'end'),
        'd': (560, 36, 300, 44, 'Hold it 4 s: off', 'step'),
        'e': (560, 120, 300, 62, 'Left alone: dims after 30 s,\noff after 5 min, off below 3.30 V\n(never while on USB)', 'lane'),
    }
    Ed = [('a', 'b', ''), ('b', 'c', '')]
    return flow(760, 245, N, Ed, size=12.5)

def d_controls():
    S = 4.2; X0, Y1 = -42, 67
    f = lambda x, y: ((x - X0) * S, (Y1 - y) * S)
    body = M.outline_path(o.body2d(), f)
    p = [f'<path d="{body}" fill="{C["navy"]}" stroke="{C["ink"]}" stroke-width="2"/>']
    x0, y0 = f(-o.AA_W / 2, o.BCY + o.AA_H / 2); x1, y1 = f(o.AA_W / 2, o.BCY - o.AA_H / 2)
    p.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="6" fill="#05080c" stroke="{C["gold"]}" stroke-width="3"/>')
    p.append(txt((x0 + x1) / 2, (y0 + y1) / 2, 'screen', 16, '#7b8794'))
    for sd in (-1, 1):
        cx, cy = f(sd * o.WING_X, o.WING_Y)
        p.append(f'<circle cx="{cx}" cy="{cy}" r="{o.BTN_D / 2 * S}" fill="#1c222b" stroke="{C["gold"]}" stroke-width="4"/>')
    rx0, ry0 = f(-o.ROCKER_W / 2, o.ROCKER_Y + o.ROCKER_H / 2); rx1, ry1 = f(o.ROCKER_W / 2, o.ROCKER_Y - o.ROCKER_H / 2)
    p.append(f'<rect x="{rx0}" y="{ry0}" width="{rx1 - rx0}" height="{ry1 - ry0}" rx="{o.ROCKER_R * S}" fill="#1c222b" stroke="{C["gold"]}" stroke-width="4"/>')
    bx, by = f(-o.UPPER_W / 2, s.PWR_Y)
    p.append(f'<rect x="{bx - 0.8 * S}" y="{by - 1.5 * S}" width="{0.8 * S}" height="{3 * S}" fill="{C["gold"]}"/>')
    def call(px, py, tx, ty, label, anchor):
        return (f'<path d="M{px},{py} L{tx},{ty}" stroke="{C["ink"]}" stroke-width="1.6"/><circle cx="{px}" cy="{py}" r="4" fill="{C["ink"]}"/>'
                + txt(tx + (8 if anchor == 'start' else -8), ty, label, 13.5, anchor=anchor, weight='bold'))
    W = 1100; ox = 420
    g = [f'<g transform="translate({ox},10)">' + ''.join(p) + '</g>']
    lx, ly = f(-o.WING_X, o.WING_Y); rx, ry = f(o.WING_X, o.WING_Y); kx, ky = f(-o.ROCKER_W / 2 + 4, o.ROCKER_Y); qx, qy = f(o.ROCKER_W / 2 - 4, o.ROCKER_Y)
    ux, uy = f(0, o.Y_TOP)
    g.append(call(ox + lx, 10 + ly, 340, 10 + ly - 40, 'LEFT wing: flap up-left', 'end'))
    g.append(call(ox + rx, 10 + ry, 850, 10 + ry - 40, 'RIGHT wing: flap up-right', 'start'))
    g.append(txt(ox + f(0, 0)[0], 10 + ly - 8, 'both together:\nstraight up', 13, C['blue'], weight='bold'))
    g.append(call(ox + kx, 10 + ky, 340, 10 + ky + 40, 'rocker LEFT end: dart left', 'end'))
    g.append(call(ox + qx, 10 + qy, 850, 10 + qy + 40, 'rocker RIGHT end: dart right', 'start'))
    g.append(call(ox + bx - 0.8 * S, 10 + by, 340, 10 + by, 'POWER: press on, hold 4 s off', 'end'))
    g.append(call(ox + ux, 10 + uy, 700, 10 + uy - 2, 'USB-C: charge + flash', 'start'))
    for name in ('RST', 'BOOT'):
        hx, hy = f(-o.UPPER_W / 2, o.SIDE_KEYS_Y[name])
        g.append(call(ox + hx, 10 + hy, 340, 10 + hy, f'{name} pin hole (re-flashing only)', 'end'))
    return svg(W, int(10 + (Y1 - o.Y_BOTTOM) * S + 20), ''.join(g))

def d_stack():
    rows = [('face panel, acrylic', 0.0, o.PANEL_T, '#d7ebff'), ('shell rim over the glass', o.PANEL_T, s.Z_GLASS, C['navy']),
            ('Waveshare: glass to the top of its J8 socket', s.Z_GLASS, s.Z_SOCK, '#2a2f38'), ('ONE SLIM board', s.Z_ONE, s.Z_ONE + s.ONE_T, C['pcb']),
            ('clearance', s.Z_ONE + s.ONE_T, s.ZIN, '#ffffff'), ('back wall', s.ZIN, s.DEPTH, C['navy'])]
    S = 26; p = []; last = -99
    for lab, z0, z1, fill in rows:
        y0, h = 20 + z0 * S, max((z1 - z0) * S, 2)
        p.append(f'<rect x="40" y="{y0}" width="260" height="{h}" fill="{fill}" stroke="{C["ink"]}" stroke-width=".8"/>')
        ly = max(y0 + h / 2, last + 17); last = ly                          # labels never overlap
        p.append(f'<path d="M300,{y0 + h / 2} L318,{ly}" stroke="{C["grey"]}" stroke-width="1"/>')
        p.append(txt(322, ly, f'{lab}  {z1 - z0:.1f} mm', 13, anchor='start'))
    by0 = 20 + s.BAY['z0'] * S
    p.append(f'<rect x="210" y="{by0}" width="80" height="{s.BAY["t"] * S}" fill="#b9c2cc" stroke="{C["ink"]}"/>')
    p.append(txt(250, by0 + s.BAY['t'] * S / 2, 'cell', 12))
    p.append(txt(170, 20 + s.DEPTH * S + 44, f'total {s.DEPTH} mm', 14, weight='bold'))
    return svg(760, int(20 + s.DEPTH * S + 60), ''.join(p))

def d_back():
    """the back shell from inside, what goes where (cell corner, speaker, leads, clips)"""
    S = 4.2; X0, Y1 = -42, 67
    f = lambda x, y: ((-x - X0) * S, (Y1 - y) * S)              # seen from the back: mirrored
    p = [f'<path d="{M.outline_path(o.body2d(), f)}" fill="#e8edf3" stroke="{C["ink"]}" stroke-width="2"/>']
    def rect(d, fill, lab, tc=C['ink']):
        a = f(d['x0'], d['y1']); b = f(d['x1'], d['y0'])
        x, y, w, h = min(a[0], b[0]), min(a[1], b[1]), abs(b[0] - a[0]), abs(b[1] - a[1])
        p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{C["ink"]}"/>' + txt(x + w / 2, y + h / 2, lab, 12, tc))
    rect(s.BAY, 'none', '')
    rect(s.CELL, '#b9c2cc', 'cell\n(foam tape)\nlead end\ndown')
    rect(s.SPK, '#2a2f38', 'speaker', '#fff')
    for d, col in ((s.LEAD, C['red']), (s.SPK_LEAD, C['blue'])):
        a = f((d['x0'] + d['x1']) / 2, d['y0']); b = f((d['x0'] + d['x1']) / 2, d['y1'])
        p.append(f'<path d="M{a[0]},{a[1]} L{b[0]},{b[1]}" stroke="{col}" stroke-width="4"/>')
    for x, y in s.CLIPS:
        c = f(x, y); p.append(f'<circle cx="{c[0]}" cy="{c[1]}" r="4" fill="{C["gold"]}" stroke="{C["ink"]}"/>')
    W = 760; ox = 30
    g = [f'<g transform="translate({ox},10)">' + ''.join(p) + '</g>']
    g.append(txt(470, 90, 'Seen from inside the back shell,\nUSB-C end at the top.', 13, anchor='start'))
    g.append(txt(470, 150, 'red: the cell lead, under two clips,\ndown to J2 on the board', 13, C['red'], anchor='start'))
    g.append(txt(470, 205, 'blue: the speaker lead, under a clip,\nup to J9 on the Waveshare', 13, C['blue'], anchor='start'))
    g.append(txt(470, 255, 'gold dots: the lead clips', 13, anchor='start'))
    return svg(W, int(10 + (Y1 - o.Y_BOTTOM) * S + 20), ''.join(g))

def d_block():
    N = {
        'bat': (110, 50, 170, 50, 'Cell 250 mAh\n(PH 2.0 plug)', 'step'), 'j2': (110, 140, 170, 40, 'J2 socket', 'step'),
        'q1': (110, 225, 170, 50, 'Q1: reverse-\nbattery guard', 'step'), 'hdr': (380, 225, 220, 50, 'header pin 1 (BAT)\ninto the Waveshare', 'step'),
        'axp': (380, 315, 220, 50, 'Waveshare power chip\n(AXP2101)', 'start'), 'pwr': (650, 315, 200, 50, 'its PWR key\n(the side button)', 'step'),
        'keys': (650, 140, 200, 60, '4 buttons\n(GPIO 17, 18, 21, 38)', 'step'),
    }
    Ed = [('bat', 'j2', ''), ('j2', 'q1', ''), ('q1', 'hdr', ''), ('hdr', 'axp', ''), ('pwr', 'axp', '')]
    return flow(780, 350, N, Ed, size=12)

def flash_shot(out):
    lines = open(os.path.join(CAP, 'slim_flash_me.txt'), encoding='utf-8').read().replace('\r', '').split('\n')
    keep = [l for l in lines if l.strip() and 'VID/PID' not in l and not l.startswith('Writing at') and not l.startswith('NOTE:')]
    want = ['$ ./flash_me.sh', 'STRUTHIO - put the game', '[1/4]', '[2/4]', '[3/4]', '[4/4]', 'Connected to ESP32-S3', "Writing 'struthio.bin'",
            'Hash of data verified', "struthio.pak'", 'Hash of data verified', "struthio_music.ima'", 'Hash of data verified', 'DONE']
    idx, k = [], 0
    for w in want:
        while k < len(keep) and w not in keep[k]: k += 1
        if k < len(keep): idx.append(k); k += 1
    show = []
    for j, i in enumerate(idx):
        if j and i != idx[j - 1] + 1: show.append('  · · ·')
        show.append(keep[i])
    marks = {}
    for i, l in enumerate(show):
        if '[3/4]' in l: marks[i] = (1, 'cyan')
        if 'Hash of data verified' in l: marks[i] = (2, 'green')
        if 'DONE' in l: marks[i] = (3, 'gold')
    shot(out, 'Terminal  ~/struthio (the emulator bench)', show, marks=marks, prompt='maker@bench:~/struthio$', max_cols=100)

# ======================================================================================================
def build(out_pdf):
    with tempfile.TemporaryDirectory() as t:
        fs = os.path.join(t, 'flash.png'); flash_shot(fs)
        st = lambda n: os.path.join(REN, 'steps', n + '.png')
        H = []
        H.append(f'<div class="cover"><div><h1 class="first">STRUTHIO ONE SLIM</h1><div class="sub">Build manual · Windows 11 · every step in build order</div></div>'
                 f'{img(os.path.join(REN, "slim_hero.png"), crop_dark=True, maxh="150mm")}'
                 f'<div style="font-size:9pt;color:#4a5866">16.5 mm thin. One click to flash, one soldering job, one screw size. The handheld checks itself the first time you switch it on.<br>'
                 f'Case rev S3 · board rev S2 · commit {COMMIT} · {TODAY}</div></div>')
        H.append('<h1>Contents</h1><table class="toc">' + ''.join(
            f'<tr><td><b>Part {k}</b></td><td>{x}</td></tr>' for k, x in enumerate([
                'The whole build at a glance', 'What you need', 'Order and make the parts', 'Put the game on the board',
                'Prepare the board (the one soldering job)', 'Assemble (steps 1-8)', 'Switch on: the first power-on check',
                'Fit the face panel', 'How to play', 'If something is wrong', 'How it works'], 1)) + '</table>'
                 '<h2>How to read this manual</h2><p>Do the parts in order. Each step has a picture, what to do, and a green '
                 '<b>✔ check</b>: don\'t go on until it\'s true. Orange boxes are the things that matter most.</p>'
                 '<p>Pictures are labelled: <span class="tag real">screenshot</span> real output of the real firmware and tools, '
                 '<span class="tag">from the 3D model</span> rendered from the exact case and board design (the parts each step adds glow orange), '
                 '<span class="tag">diagram</span> drawn from the design\'s own numbers.</p>'
                 '<p>The packages are referred to by number: <b>1</b> firmware, <b>2</b> face panel, <b>3</b> board (JLCPCB), '
                 '<b>4</b> 3D print, <b>5</b> documents (this manual). The shopping list on its own: <code>STRUTHIO_ORDER</code> in package 5.</p>')
        H.append('<h1>The whole build at a glance</h1><p class="part">Part 1</p>'
                 '<p>Four things are made or bought at the same time. When the screen board arrives you put the game on it, '
                 'solder 12 pins, build, switch on: the handheld checks itself.</p>' + fig(d_overview(), 'The build, start to finish', 'diag')
                 + fig(img(os.path.join(REN, 'slim_exploded.png'), crop_dark=True, maxh='90mm'), 'Everything that goes into it, front to back. The animated version is slim_assembly.gif in package 5', 'render'))
        H.append('<h1>What you need</h1><p class="part">Part 2</p><h2>Buy</h2><table><tr><th>✓</th><th>Qty</th><th>Item</th><th>Exactly what</th></tr>' + ''.join(
            f'<tr><td>☐</td><td>{q}</td><td><b>{a}</b></td><td>{b}</td></tr>' for q, a, b in [
                (1, 'Screen board', '<b>Waveshare ESP32-S3-Touch-LCD-3.5B</b>, the bare board (not "-C").'),
                (1, 'Battery', 'LiPo <b>302535</b>, about 250 mAh, with protection board, <b>JST PH 2.0 mm</b> 2-pin plug.'),
                (1, 'Speaker', 'Mini cavity speaker, <b>1 W 8 Ω</b>, about <b>15 × 10 × 3.6 mm</b>, with its lead and a <b>1.25 mm 2-pin plug</b> (plugs straight in: no soldering).'),
                (5, 'Screws', '<b>M2 × 6 countersunk</b> (flat head). All five the same.'),
                (1, 'Header strip', '2.54 mm male header, single row (you use 12 pins).'),
                (1, 'Foam tape', 'Double-sided, <b>1.0 mm</b> thick, about 20 × 30 mm.'),
                (1, 'USB-C data cable', 'One that carries data (a phone\'s own cable usually does).')]) + '</table>'
                 '<h2>Made for you (Part 3)</h2><table><tr><th>✓</th><th>Item</th><th>From</th></tr>' + ''.join(
            f'<tr><td>☐</td><td><b>{a}</b></td><td>{b}</td></tr>' for a, b in [
                ('ONE SLIM board', 'JLCPCB, assembled, 0.8 mm (package 3)'), ('Face panel', 'an acrylic shop (package 2)'),
                ('7 printed parts', 'your printer or a print service (package 4)')]) + '</table>'
                 '<h2>Tools</h2><ul class="tick"><li>A soldering iron and solder (12 header pins)</li><li>Flush cutters</li>'
                 '<li>A small Phillips screwdriver (PH0)</li><li>A paperclip (only for re-flashing through the case later)</li>'
                 '<li>A Windows 11 computer with internet access</li></ul>')
        bt = os.path.join(HH, 'pcb', 'slim', 'out', 'board_top.png')
        H.append('<h1>Order and make the parts</h1><p class="part">Part 3</p>'
                 '<h2>The ONE SLIM board (package 3, folder ONE_SLIM)</h2><ol>'
                 '<li>On jlcpcb.com upload <code>struthio_one_slim_gerbers.zip</code>. Set <b>PCB Thickness: 0.8 mm</b>.</li>'
                 '<li>Turn on <b>PCB Assembly</b>, top side. Upload <code>BOM_JLCPCB.csv</code> and <code>CPL_JLCPCB.csv</code>: six small parts, all surface-mount.</li>'
                 '<li>In the placement preview, <b>J2</b>\'s opening faces the board\'s <b>right</b> edge (compare with the picture). Rotate in 90° steps if not.</li></ol>'
                 + fig(png(bt, '50%'), 'The board as ordered (top side, seen from the front of the handheld)', 'diag')
                 + '<h2>The face panel (package 2, folder ONE_SLIM)</h2><p>The SLIM\'s own panel files (it sits in a pocket, so it is cut smaller than the ONE\'s). Send an acrylic shop the files and this sentence: <b>1.0 mm clear cast acrylic, cut to the DXF, reverse-printed '
                 '(colour, then white) from the mirrored PNG, window left clear; clear adhesive transfer tape (3M 468MP) laminated on the back, except over the window.</b></p>'
                 + '<h2>The printed parts (package 4, folder ONE_SLIM)</h2><p>Front shell, back shell, two wing buttons, rocker, power button, pin jig. '
                 'PETG (or ASA), 0.2 mm layers, 4 walls, 6 top and bottom layers, 40 % infill. No printer? Upload the STLs to a print service and ask for '
                 '<b>MJF nylon (PA12)</b> or <b>PETG</b>; not resin, which is too brittle for the screws.</p>' + fig(M.d_bed(), 'How the shells and buttons sit on the bed', 'diag'))
        H.append('<h1>Put the game on the board</h1><p class="part">Part 4 · as soon as the screen board arrives, before you build it in</p>'
                 + step('4.1', 'Unzip the firmware package', '', '<p>Right-click <code>STRUTHIO_ONE_1_Firmware_Flashing.zip</code> → <b>Extract All…</b> → <code>C:\\</code> → Extract. '
                        'You get <code>C:\\struthio</code>.</p>', warn='Not inside OneDrive, and no spaces in the path.')
                 + step('4.2', 'Plug the board in', '', '<p>Connect the Waveshare board to the computer with the USB-C <b>data</b> cable. Nothing else is connected to it yet.</p>')
                 + step('4.3', 'Double-click FLASH_ME.bat', '', '<p>In <code>C:\\struthio</code>, double-click <b>FLASH_ME.bat</b>. It installs Python and the flashing tool the '
                        'first time (it may take a few minutes and ask you to allow it), finds the board by itself, writes the game, its pictures and its music, and '
                        'checks every byte.</p>', warn='If Windows says "Windows protected your PC": click <b>More info</b>, then <b>Run anyway</b>. It is a plain text file you can read in Notepad.',
                        check='The window ends with <b>DONE</b>.')
                 + fig(png(fs, '100%'), 'The real output of the same flasher (flash_me.sh, FLASH_ME.bat\'s twin for macOS and Linux, with the same steps and messages), '
                       'run against Espressif\'s ESP32-S3 emulator. <b>1</b> the board found; <b>2</b> each part written and checked; <b>3</b> done. Lines left out are marked · · ·', 'real')
                 + '<h2>If it doesn\'t work</h2>' + fig(d_flash(), 'Flashing problems', 'diag')
                 + '<div class="box"><b>Download mode</b>: hold the board\'s <b>BOOT</b> key, press and release <b>RESET</b>, release BOOT. FLASH_ME asks for it when it needs it. '
                   'In the finished case the two keys are behind the pin holes on the left side (Part 9).</div>')
        H.append('<h1>Prepare the board</h1><p class="part">Part 5 · the one soldering job: 12 header pins</p>'
                 + step('5.1', 'Cut two header strips', '', '<p>From the header strip, cut a strip of <b>4</b> pins and a strip of <b>8</b> pins (snip between pins).</p>')
                 + step('5.2', 'Board face down in the jig', img(st('s05_pins'), crop_dark=True),
                        '<p>Lay the ONE SLIM <b>face down</b> (buttons down) on the printed <b>pin jig</b>, its strip inside the jig\'s fence. Two small pegs go into two holes: '
                        'it only sits flat the right way round.</p>', check='The board lies flat in the jig; the back silkscreen reads "J1: PINS 1-7 ODD + 4-18 EVEN".')
                 + step('5.3', 'Pins in, solder, plastic off, snip', fig(d_pins(), 'Side view of the jig', 'diag'),
                        '<p>Push the 4-pin strip into the outer row\'s top four holes and the 8-pin strip into the inner row (the jig only has holes where pins go), '
                        '<b>long side first</b>, until they stop. Solder each pin on the back. Slide the black plastic off the pins with pliers, then snip every pin flush with the board.</p>',
                        check=f'12 pins stand {s.PIN_OUT} mm out of the front, straight; nothing sticks out at the back.')
                 )
        H.append('<h1>Assemble</h1><p class="part">Part 6 · steps 1-8 · on a soft cloth, nothing needs force</p>'
                 + step(1, 'Wing buttons', img(st('s01_wing_buttons'), crop_dark=True),
                        '<p>From the <b>inside</b> of the front shell, push each round cap into its collar, its key in the slot on the collar\'s outer side.</p>',
                        check='Both caps in, wings upright from the front, each springs back.')
                 + fig(M.d_key(), 'A wing button seen from inside: the key points away from the middle, so it only goes in one way', 'diag')
                 + step(2, 'Rocker', img(st('s02_rocker'), crop_dark=True),
                        '<p>Push the rocker into its collar from the inside. Cut its axle: push 1.75 mm filament into the pin jig\'s slot to the closed end and cut it at the open end '
                        '(exactly 11 mm). Push the axle through the hole in the collar\'s top wall until it stops.</p>', check='The rocker tips both ways and springs back.')
                 + step(3, 'Power button', img(st('s03_power_button'), crop_dark=True),
                        '<p>From the inside, push the small power button through the slot in the <b>left</b> wall (left as you hold the handheld), its wide flange inside.</p>',
                        check='The button stands 0.8 mm out of the side and slides freely.')
                 + step(4, 'Lay in the screen board', img(st('s04_waveshare'), crop_dark=True),
                        '<p>Screen <b>down</b>, <b>USB-C at the top</b>. The glass drops into its pocket in the front shell.</p>',
                        check='It lies flat; the power button\'s tip touches its PWR key; press the button: you feel a click.')
                 + step(5, 'The ONE SLIM', img(st('s06_one_slim'), crop_dark=True),
                        '<p>Pins down, lower the board straight onto the screen board: the pins go into the long black socket (J8) on its right side, and the board rests on the shell\'s posts.</p>',
                        warn='Line the pins up first, then press evenly. If they won\'t go in, look: one pin may be bent.', check='The board sits flat on its posts.')
                 + step(6, 'Back shell: speaker and cell', img(st('s07_back_shell'), crop_dark=True),
                        '<p>Press the speaker into its lip in the back shell, face toward the grille. Stick the foam tape on the cell\'s back and press the cell into the bay\'s corner '
                        '(see the diagram), lead end down. Press each lead under its clips.</p>', check='Speaker in its lip, cell stuck down, leads under their clips.')
                 + fig(d_back(), 'Where things go in the back shell', 'diag')
                 + step(7, 'Plug in', '', '<p>Speaker plug into <b>J9</b> on the screen board (small 2-pin socket at its left edge). Battery plug into <b>J2</b> on the ONE SLIM '
                        '(red wire to <b>+</b>). The plugs only go in one way.</p>', warn='The battery is now connected: the handheld can switch on if you press the power button.',
                        check='Both plugs fully in.')
                 + step(8, 'Close the case', img(st('s08_closed'), crop_dark=True),
                        '<p>Lay the back shell on: its tongue goes into the front shell\'s groove all round. Fit the <b>5 × M2 × 6</b> screws: three go into the screen board\'s '
                        'own metal standoffs, two into the bottom corners. Snug, not tight.</p>',
                        warn='If it doesn\'t close by itself, open it and look: a lead is in the way. Never force it.', check='Closed all round, screw heads flush.'))
        H.append('<h1>Switch on: the first power-on check</h1><p class="part">Part 7</p>'
                 + step(9, 'Press the power button', img(st('s09_first_power'), crop_dark=True),
                        '<p>Press the button on the left side. The very first time, hold it until the screen lights (up to 2 s); after that a short press is enough.</p>',
                        check='The screen lights with STRUTHIO · FIRST POWER-ON CHECK.')
                 + step(10, 'Follow the screen', fig(png(os.path.join(CAP, 'fw_selftest_example.png'), '72%'), 'The check, all done (example values)', 'real'),
                        '<p>Press each wing button, each end of the rocker and the power button <b>once</b>: each turns <b>OK</b> and clicks (the click is the speaker working). '
                        'BATTERY shows the cell. Picture upside down? Hold LEFT 2 s. When everything is OK, press <b>both wings</b>: the game starts.</p>',
                        warn='STUCK DOWN next to a button means its cap rubs: Part 10. NO BATTERY: check the J2 plug.', check='ALL GOOD, then the game.')
                 + fig(d_power(), 'Power from now on', 'diag')
                 + step(11, 'Charge', '', '<p>Plug USB-C in, on or off. The cell charges at 100 mA: about 3 hours from empty.</p>', check='Plugged in, it keeps running and never switches itself off.'))
        H.append('<h1>Fit the face panel</h1><p class="part">Part 8 · last</p>'
                 + step(12, 'Panel into its pocket', img(st('s10_panel'), crop_dark=True),
                        '<p>Peel the panel\'s back liner. Drop it into the pocket in the front of the case: the 1 mm lip all round lines it up, and it only goes in one way '
                        '(the button wells fit their buttons). Press it down from the middle outward. Peel the front film.</p>',
                        check='The panel sits flush with the lip all round; every button moves freely in its well.'))
        H.append('<h1>How to play</h1><p class="part">Part 9</p>' + fig(d_controls(), 'The controls, and what is on the sides', 'diag')
                 + '<div class="two">' + fig(png(os.path.join(CAP, 'fw_play.png'), '70%'), 'The game running', 'real')
                 + '<div><h2>The controls</h2><table><tr><th>Press</th><th>Does</th></tr>'
                   '<tr><td>LEFT wing</td><td>flap up and to the left</td></tr><tr><td>RIGHT wing</td><td>flap up and to the right</td></tr>'
                   '<tr><td>Both together</td><td>flap straight up</td></tr><tr><td>Hold a wing</td><td>steer</td></tr>'
                   '<tr><td>Rocker left / right end</td><td>aim-assisted dart, that way</td></tr>'
                   '<tr><td>Both after GAME OVER</td><td>new run</td></tr>'
                   '<tr><td>Power button</td><td>press: on; hold 4 s: off</td></tr>'
                   '<tr><td>Both held while switching on</td><td>service mode</td></tr></table>'
                   '<h2>Updating the game later</h2><p>Plug USB-C in and double-click FLASH_ME.bat again. If it asks for download mode: a paperclip in the '
                   '<b>BOOT</b> hole, tap <b>RST</b> with another, release BOOT.</p></div></div>')
        H.append('<h1>If something is wrong</h1><p class="part">Part 10</p><table><tr><th>What you see</th><th>What to do</th></tr>' + ''.join(
            f'<tr><td>{a}</td><td>{b}</td></tr>' for a, b in [
                ('Nothing when you press power', 'Hold it 2 s (the very first time). Battery plug in J2, red to +? Plug USB-C in: if it starts on USB, let the cell charge.'),
                ('STUCK DOWN on the check screen', 'That cap\'s stem touches its switch: take the cap out, sand 0.2 mm off the stem tip.'),
                ('A button never turns OK', 'Is the ONE SLIM flat on its posts, every pin in J8? Does the cap move freely?'),
                ('POWER never turns OK', 'Does the power button click its key? Push it in from outside: it must move freely.'),
                ('No click, no sound', 'Speaker plug fully in J9? Speaker face against the grille?'),
                ('NO BATTERY', 'J2 plug fully in? Red to +.'),
                ('Back shell won\'t close', 'A lead is in the way: under its clips? Never force it.'),
                ('Picture upside down', 'On the check screen: hold LEFT 2 s. Later: service mode, hold RIGHT 1 s.'),
                ('Flashing fails', 'Part 4, "If it doesn\'t work".')]) + '</table>')
        H.append('<h1>How it works</h1><p class="part">Part 11</p>' + fig(d_block(), 'The electrics', 'diag')
                 + fig(d_stack(), 'The 16.5 mm stack, front to back (the cell sits behind the screen board\'s low parts, beside the ONE SLIM)', 'diag')
                 + '<h2>Header pins</h2><p>1 BAT · 3, 4 GND · 5 GPIO21 (rocker L) · 7 GPIO38 (rocker R) · 16 GPIO17 (left wing) · 18 GPIO18 (right wing). '
                   'Pin 9 stays empty: that is how the firmware knows it is a SLIM (100 mA charge, power button). The other pins of the even strip land on empty pads.</p>'
                 + '<h2>Things the first builds should confirm</h2><table><tr><th>What</th><th>Designed for</th><th>If different</th></tr>' + ''.join(
                     f'<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>' for a, b, c in [
                         ('J8 socket height', '12.6 or 11.5 mm behind the glass: both work', 'pins go 3.6 or 2.5 mm in'),
                         ('Standoffs threaded M2', 'the 3D model says SMT M2 nuts', 'if a screw won\'t bite, use a slightly longer one'),
                         ('Power button reaches its key', 'tip 0.2 mm from it, 0.6 mm travel', 'a drop of glue + 0.3 mm shim on the tip'),
                         ('302535 size', '3.0 × 25 × 38 mm with its board', 'any 3.0 mm cell up to 34 × 52 mm fits the bay')]) + '</table>'
                 + f'<p style="font-size:8.5pt;color:#6b7783">STRUTHIO ONE SLIM build manual · case rev S3, board rev S2 · commit {COMMIT} · {TODAY}. Made from the design files by tools/manual/slim_manual.py.</p>')
        doc = f'<!doctype html><html><head><meta charset="utf-8"><title>STRUTHIO ONE SLIM build manual</title><style>{CSS}</style></head><body>{"".join(H)}</body></html>'
        hp = os.path.join(t, 'manual.html'); open(hp, 'w', encoding='utf-8').write(doc)
        subprocess.check_call(['node', os.path.join(HH, 'tools', 'package', 'html2pdf.mjs'), hp, out_pdf])

if __name__ == '__main__':
    build(os.path.abspath(sys.argv[1]))
