#!/usr/bin/env python3
"""STRUTHIO HANDHELD · beginner figures for Build Manual 1.2.

Every number drawn here comes from the repository: pins and timings from
firmware/main (board_pins.h, struthio_buttons.h, main.c), the flash map from
firmware/partitions.csv, the band hand-off from main.c / host/band_order_test.c,
the HUD fields from arcade/src/ui/hud.mjs. Generic workshop pictures (meter,
solder joints) carry no project numbers.
    python3 tools/manual/figs12.py OUT_DIR
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else 'figs12'
os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))

FD = '/usr/share/fonts/truetype/dejavu/'
def F(size, bold=False, mono=False):
    name = 'DejaVuSansMono' if mono else 'DejaVuSans'
    if bold: name += '-Bold'
    return ImageFont.truetype(FD + name + '.ttf', size)

NAVY = (16, 40, 56); GOLD = (226, 169, 63); GOLD_D = (150, 104, 20); CYAN = (13, 104, 117)
RED = (185, 30, 24); GREEN = (30, 140, 80); GREY = (120, 120, 120); LIGHT = (236, 240, 244)
INK = (25, 25, 25); WHITE = (255, 255, 255); PAPER = (255, 255, 255); AMBER = (255, 242, 204)

def canvas(w, h):
    im = Image.new('RGB', (w, h), PAPER)
    return im, ImageDraw.Draw(im)

def text(d, xy, s, size=34, fill=INK, bold=False, anchor='la', mono=False):
    d.text(xy, s, font=F(size, bold, mono), fill=fill, anchor=anchor)

def mtext(d, xy, s, size=30, fill=INK, bold=False, anchor='la', spacing=8):
    d.multiline_text(xy, s, font=F(size, bold), fill=fill, anchor=anchor, spacing=spacing,
                     align='center' if anchor[0] == 'm' else 'left')

def box(d, xy, fill=LIGHT, outline=NAVY, width=4, r=18):
    d.rounded_rectangle(xy, r, fill=fill, outline=outline, width=width)

def arrow(d, a, b, fill=NAVY, width=6, head=22):
    import math
    d.line([a, b], fill=fill, width=width)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    p1 = (b[0] - head * math.cos(ang - 0.45), b[1] - head * math.sin(ang - 0.45))
    p2 = (b[0] - head * math.cos(ang + 0.45), b[1] - head * math.sin(ang + 0.45))
    d.polygon([b, p1, p2], fill=fill)

def dashed(d, a, b, fill=GREY, width=4, dash=18):
    import math
    L = math.dist(a, b); n = int(L // dash)
    for i in range(0, n, 2):
        t0, t1 = i / n, min(1, (i + 1) / n)
        d.line([(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)], fill=fill, width=width)

def title(d, w, s, sub=None):
    text(d, (w // 2, 30), s, 44, NAVY, True, 'ma')
    if sub: text(d, (w // 2, 90), sub, 28, GREY, False, 'ma')

def save(im, name):
    p = os.path.join(OUT, name)
    im.save(p, optimize=True)
    print('wrote', p, im.size)

def resistor(d, x, y0, y1, w=26):
    """vertical zig-zag resistor between y0 and y1"""
    n = 6; h = (y1 - y0) / n
    pts = [(x, y0)]
    for i in range(n):
        pts.append((x + (w if i % 2 == 0 else -w), y0 + h * (i + 0.5)))
    pts.append((x, y1))
    d.line(pts, fill=INK, width=5, joint='curve')

def ground(d, x, y):
    d.line([(x, y - 30), (x, y)], fill=INK, width=5)
    for i, hw in enumerate((34, 22, 10)):
        d.line([(x - hw, y + i * 12), (x + hw, y + i * 12)], fill=INK, width=5)

# ---- F1: pull-up and active-low --------------------------------------------------------------
def fig_pullup():
    W, H = 2000, 980
    im, d = canvas(W, H)
    title(d, W, 'How one wing button is read: pull-up resistor + switch to GND',
          'firmware/main/main.c sets GPIO17 / GPIO18 as inputs with the internal pull-up on (STRUTHIO_BUTTON_ACTIVE_LEVEL 0)')
    for k, (ox, pressed) in enumerate(((60, False), (1030, True))):
        box(d, (ox, 150, ox + 910, 940), fill=(250, 250, 250), outline=(200, 200, 200), width=3)
        text(d, (ox + 455, 175), 'RELEASED' if not pressed else 'PRESSED', 40, NAVY, True, 'ma')
        # ESP32 box
        d.rounded_rectangle((ox + 40, 250, ox + 420, 860), 16, outline=CYAN, width=4)
        text(d, (ox + 60, 262), 'inside the ESP32-S3', 26, CYAN, True)
        x = ox + 230
        text(d, (x, 318), '3.3 V', 32, RED, True, 'ma')
        d.line([(x - 50, 360), (x + 50, 360)], fill=RED, width=6)
        d.line([(x, 360), (x, 410)], fill=INK, width=5)
        resistor(d, x, 410, 560)
        text(d, (x + 45, 465), 'pull-up', 26, INK)
        text(d, (x + 45, 497), '(~45 kΩ)', 24, GREY)
        d.line([(x, 560), (x, 640)], fill=INK, width=5)
        d.ellipse((x - 10, 630, x + 10, 650), fill=INK)
        # input reader
        d.line([(x, 640), (x - 120, 640)], fill=INK, width=5)
        d.polygon([(x - 120, 610), (x - 120, 670), (x - 175, 640)], outline=INK, width=4)
        text(d, (ox + 60, 690), 'reads', 24, GREY)
        val = '0 (LOW)' if pressed else '1 (HIGH)'
        text(d, (ox + 60, 722), val, 34, GREEN if pressed else NAVY, True)
        # wire out to header
        d.line([(x, 640), (ox + 600, 640)], fill=INK, width=5)
        d.ellipse((ox + 410, 628, ox + 434, 652), fill=GOLD, outline=INK, width=2)
        text(d, (ox + 440, 588), 'GPIO17', 28, NAVY, True)
        text(d, (ox + 440, 660), 'header pin 16*', 24, GREY)
        # switch
        sx = ox + 700
        d.line([(ox + 600, 640), (sx, 640)], fill=INK, width=5)
        d.line([(sx, 640), (sx, 690)], fill=INK, width=5)
        d.ellipse((sx - 9, 681, sx + 9, 699), fill=INK)
        d.ellipse((sx - 9, 771, sx + 9, 789), fill=INK)
        if pressed:
            d.line([(sx, 690), (sx, 780)], fill=INK, width=6)
        else:
            d.line([(sx, 690), (sx + 55, 770)], fill=INK, width=6)
        text(d, (sx + 70, 700), 'wing switch', 26, INK, True)
        text(d, (sx + 70, 734), 'closed' if pressed else 'open', 26, GREEN if pressed else GREY)
        d.line([(sx, 780), (sx, 830)], fill=INK, width=5)
        ground(d, sx, 860)
        text(d, (sx + 50, 850), 'GND', 28, INK, True)
        if pressed:
            # current path
            for a, b in (((x + 40, 420), (x + 40, 610)), ((sx - 30, 660), (sx - 30, 820))):
                arrow(d, a, b, fill=GOLD_D, width=4, head=16)
            d.multiline_text((ox + 470, 520), 'a tiny current flows;\nthe pin is pulled to 0 V', font=F(24), fill=GOLD_D)
        else:
            d.multiline_text((ox + 470, 520), 'no path to GND:\nthe resistor holds 3.3 V', font=F(24), fill=NAVY)
    text(d, (W // 2, 950), '* header pin numbers are the v0.10 proposal from the published 2x16 pinout image: confirm them on the board in your hand.', 24, GREY, False, 'ma')
    save(im, 'f01_pullup.png')

# ---- F2: multimeter -------------------------------------------------------------------------------
def meter(d, ox, oy, mode, reading):
    box(d, (ox, oy, ox + 300, oy + 470), fill=(250, 196, 40), outline=INK, width=5, r=26)
    d.rectangle((ox + 35, oy + 35, ox + 265, oy + 130), fill=(200, 214, 190), outline=INK, width=3)
    text(d, (ox + 150, oy + 82), reading, 46, INK, True, 'mm', mono=True)
    cx, cy = ox + 150, oy + 260
    d.ellipse((cx - 85, cy - 85, cx + 85, cy + 85), fill=(60, 60, 60), outline=INK, width=4)
    import math
    labels = [('V⎓', -150), ('Ω', -90), ('♪', -30), ('OFF', 90)]
    for lab, ang in labels:
        a = math.radians(ang)
        text(d, (cx + 118 * math.cos(a), cy + 118 * math.sin(a)), lab, 26, INK, True, 'mm')
    a = math.radians(dict((l, g) for l, g in labels)[mode])
    d.line([(cx, cy), (cx + 70 * math.cos(a), cy + 70 * math.sin(a))], fill=WHITE, width=10)
    for i, (lab, col) in enumerate((('COM', INK), ('VΩ', RED))):
        px = ox + 95 + i * 110
        d.ellipse((px - 22, oy + 395, px + 22, oy + 439), fill=col, outline=INK, width=3)
        text(d, (px, oy + 380), lab, 22, INK, True, 'mb')
    return (ox + 95, oy + 439), (ox + 205, oy + 439)

def fig_multimeter():
    W, H = 2000, 1060
    im, d = canvas(W, H)
    title(d, W, 'The three multimeter tests you will use on this build',
          'black lead in COM, red lead in VΩ for all three')
    cols = [
        ('1  CONTINUITY  (♪)', '♪', '0.3Ω ♪', 'Power OFF. Probe both ends of a wire,\nor across a switch while pressing it.\nA beep means connected.',
         'wire'),
        ('2  SHORT CHECK  (♪)', '♪', 'OL', 'Power OFF. Probe 3V3 and GND,\nthen BAT+ and BAT−. NO beep wanted.\nA beep = a short: find it before power.',
         'short'),
        ('3  DC VOLTS  (V⎓)', 'V⎓', '3.95', 'Battery or rail ON. Red on +, black on −.\nA minus sign means the leads (or the\nwiring) are reversed: stop and check.',
         'volts'),
    ]
    for i, (hd, mode, rd, note, kind) in enumerate(cols):
        ox = 40 + i * 650
        box(d, (ox, 140, ox + 620, 1030), fill=(250, 250, 250), outline=(200, 200, 200), width=3)
        text(d, (ox + 310, 165), hd, 34, NAVY, True, 'ma')
        com, vo = meter(d, ox + 40, 230, mode, rd)
        # the item under test
        tx = ox + 420
        if kind == 'wire':
            d.line([(tx - 10, 300), (tx + 150, 620)], fill=(30, 90, 200), width=12)
            a, b = (tx - 10, 300), (tx + 150, 620)
        elif kind == 'short':
            d.rectangle((tx - 30, 280, tx + 160, 640), fill=(0, 90, 60), outline=INK, width=3)
            text(d, (tx + 65, 300), 'board', 22, WHITE, True, 'ma')
            d.ellipse((tx + 10, 380, tx + 50, 420), fill=GOLD); text(d, (tx + 60, 400), '3V3', 24, WHITE, True, 'lm')
            d.ellipse((tx + 10, 520, tx + 50, 560), fill=GOLD); text(d, (tx + 60, 540), 'GND', 24, WHITE, True, 'lm')
            a, b = (tx + 30, 400), (tx + 30, 540)
        else:
            d.rounded_rectangle((tx - 20, 280, tx + 150, 640), 14, fill=(210, 210, 215), outline=INK, width=3)
            text(d, (tx + 65, 300), 'LiPo', 26, INK, True, 'ma')
            text(d, (tx + 65, 335), '(example)', 20, GREY, False, 'ma')
            text(d, (tx + 65, 420), '+', 50, RED, True, 'mm'); text(d, (tx + 65, 560), '−', 50, INK, True, 'mm')
            a, b = (tx + 105, 420), (tx + 105, 560)
        d.line([com, (com[0], 760), (b[0] - 40, 760), b], fill=INK, width=6)
        d.line([vo, (vo[0], 720), (a[0] - 60, 720), a], fill=RED, width=6)
        d.ellipse((a[0] - 9, a[1] - 9, a[0] + 9, a[1] + 9), fill=RED)
        d.ellipse((b[0] - 9, b[1] - 9, b[0] + 9, b[1] + 9), fill=INK)
        d.multiline_text((ox + 30, 820), note, font=F(27), fill=INK, spacing=10)
    save(im, 'f02_multimeter.png')

# ---- F3: solder joints ------------------------------------------------------------------------------
def fig_solder():
    W, H = 2000, 760
    im, d = canvas(W, H)
    title(d, W, 'Solder joints, seen from the side', 'heat the pad and the lead together, then feed solder into the joint, not onto the iron')
    cases = [('GOOD', 'shiny, concave\n"volcano" shape,\nlead outline visible', GREEN, 'good'),
             ('TOO LITTLE', 'gap at the pad:\nadd a little solder\nand reheat', RED, 'thin'),
             ('BLOB', 'ball sitting on top:\nthe pad was not hot;\nreheat, remove excess', RED, 'blob'),
             ('COLD', 'dull, grainy, cracked:\nmoved while cooling;\nreheat until it flows', RED, 'cold'),
             ('BRIDGE', 'solder joins two pads:\na short circuit;\nwick it away', RED, 'bridge')]
    for i, (hd, note, col, kind) in enumerate(cases):
        ox = 30 + i * 392; cx = ox + 180
        box(d, (ox, 140, ox + 370, 740), fill=(250, 250, 250), outline=col, width=4)
        text(d, (cx, 160), hd, 34, col, True, 'ma')
        # board and pad
        by = 420
        d.rectangle((ox + 20, by, ox + 350, by + 40), fill=(0, 110, 70))
        pads = [cx] if kind != 'bridge' else [cx - 70, cx + 70]
        for px in pads:
            d.rectangle((px - 50, by - 8, px + 50, by), fill=(200, 140, 60))
            d.rectangle((px - 6, by - 150, px + 6, by + 80), fill=(150, 150, 150))   # component lead
        S = (205, 205, 210)
        if kind == 'good':
            d.polygon([(cx - 50, by - 8), (cx - 30, by - 25), (cx - 14, by - 60), (cx - 6, by - 90), (cx + 6, by - 90),
                       (cx + 14, by - 60), (cx + 30, by - 25), (cx + 50, by - 8)], fill=S, outline=INK)
            d.rectangle((cx - 6, by - 150, cx + 6, by - 88), fill=(150, 150, 150))
        elif kind == 'thin':
            d.polygon([(cx - 22, by - 8), (cx - 8, by - 30), (cx + 8, by - 30), (cx + 22, by - 8)], fill=S, outline=INK)
        elif kind == 'blob':
            d.ellipse((cx - 55, by - 160, cx + 55, by - 50), fill=S, outline=INK)
            d.rectangle((cx - 6, by - 50, cx + 6, by - 8), fill=(150, 150, 150))
        elif kind == 'cold':
            d.polygon([(cx - 45, by - 8), (cx - 35, by - 40), (cx - 10, by - 70), (cx + 15, by - 62), (cx + 38, by - 35), (cx + 45, by - 8)],
                      fill=(165, 165, 160), outline=INK)
            for k in range(14):
                x = cx - 30 + (k * 37) % 60; y = by - 20 - (k * 23) % 45
                d.point((x, y), fill=INK); d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(120, 120, 120))
            d.line([(cx - 20, by - 50), (cx + 5, by - 30), (cx + 20, by - 40)], fill=INK, width=2)
        else:
            d.polygon([(cx - 120, by - 8), (cx - 90, by - 50), (cx + 90, by - 50), (cx + 120, by - 8)], fill=S, outline=INK)
        d.multiline_text((ox + 25, 520), note, font=F(26), fill=INK, spacing=8)
    save(im, 'f03_solder.png')

# ---- F4: B3F switch board -----------------------------------------------------------------------
def fig_switchboard():
    W, H = 2000, 1120
    im, d = canvas(W, H)
    title(d, W, 'One wing switch board (make two)', 'B3F-4050 on ~18 x 18 mm perfboard: two wires, signal and ground')
    # left: top view
    ox, oy, s = 330, 180, 34       # 34 px per mm
    pb = 18 * s
    d.rectangle((ox, oy, ox + pb, oy + pb), fill=(205, 160, 90), outline=INK, width=3)
    for i in range(7):
        for j in range(7):
            x = ox + 30 + i * (pb - 60) / 6; y = oy + 30 + j * (pb - 60) / 6
            d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(230, 190, 110), outline=(150, 110, 60), width=2)
    cx, cy = ox + pb / 2, oy + pb / 2
    hb = 6 * s
    d.rectangle((cx - hb, cy - hb, cx + hb, cy + hb), fill=(40, 40, 40), outline=INK, width=4)
    d.ellipse((cx - 3.6 * s, cy - 3.6 * s, cx + 3.6 * s, cy + 3.6 * s), fill=(70, 70, 70), outline=(20, 20, 20), width=3)
    d.ellipse((cx - 2.5 * s, cy - 2.5 * s, cx + 2.5 * s, cy + 2.5 * s), fill=(110, 110, 110))
    text(d, (cx, cy), 'B3F', 34, WHITE, True, 'mm')
    legs = {'A': (cx - 6.5 * s / 2 * 1.85, cy - 4.5 * s / 2 * 1.4), 'B': (cx + 6.5 * s / 2 * 1.85, cy - 4.5 * s / 2 * 1.4),
            'C': (cx - 6.5 * s / 2 * 1.85, cy + 4.5 * s / 2 * 1.4), 'D': (cx + 6.5 * s / 2 * 1.85, cy + 4.5 * s / 2 * 1.4)}
    for k, (x, y) in legs.items():
        d.rectangle((x - 14, y - 14, x + 14, y + 14), fill=(190, 190, 190), outline=INK, width=2)
    (ax, ay), (dx_, dy_) = legs['A'], legs['D']
    d.line([(ax, ay), (ax - 230, ay - 60)], fill=(70, 120, 210), width=10)
    d.line([(dx_, dy_), (dx_ + 150, dy_ + 300)], fill=INK, width=10)
    text(d, (ax - 230, ay - 140), 'SIGNAL', 30, (40, 90, 190), True, 'ma')
    text(d, (ax - 230, ay - 100), 'to GPIO17 (LEFT)', 24, INK, False, 'ma')
    text(d, (dx_ + 130, dy_ + 300), 'GND', 30, INK, True, 'ra')
    text(d, (dx_ + 130, dy_ + 340), 'to board GND', 24, INK, False, 'ra')
    text(d, (cx - 100, oy + pb + 150), 'Use two DIAGONALLY OPPOSITE legs.', 30, NAVY, True, 'ma')
    d.multiline_text((ox - 300, oy + pb + 200),
                     'A 4-leg tactile switch has two pairs of legs joined inside.\n'
                     'Diagonal legs are always on different pairs, so they are\n'
                     'the safe choice. Then prove it with the meter (right).',
                     font=F(26), fill=INK, spacing=8)
    # right: continuity check
    rx = 1130
    box(d, (rx, 170, 1950, 1080), fill=(250, 250, 250), outline=(200, 200, 200), width=3)
    text(d, (rx + 410, 190), 'Prove the switch before wiring it', 34, NAVY, True, 'ma')
    rows = [('Meter on ♪, probes on your two wired legs', ''),
            ('Button NOT pressed', 'silent  (OL)'),
            ('Button pressed', 'BEEP'),
            ('Released again', 'silent'),
            ('', ''),
            ('Beeps all the time?', 'legs are a joined pair:'),
            ('', 'move to the diagonal leg'),
            ('Never beeps?', 'reflow the joints, check'),
            ('', 'the leg is through the hole')]
    y = 270
    for a, b in rows:
        text(d, (rx + 40, y), a, 28, INK, a.endswith('?'))
        text(d, (rx + 780, y), b, 28, GREEN if b == 'BEEP' else (RED if 'pair' in b else INK), b == 'BEEP', 'ra')
        y += 58
    d.multiline_text((rx + 40, y + 20), 'Then test again on the board: in service mode\nthe LEFT / RIGHT state must flip UP ↔ DOWN\nand the press count must rise by exactly one.',
                     font=F(26), fill=CYAN, spacing=8)
    save(im, 'f04_switchboard.png')

# ---- F5: timing: press -> flap ------------------------------------------------------------------
def fig_timing():
    W, H = 2000, 1180
    im, d = canvas(W, H)
    title(d, W, 'From thumb to flap: what the firmware does with one press',
          'struthio_buttons.c: sampled every 1 ms, 8 ms debounce, stamped at the raw edge  •  struthio_input: 100 ms chord, 60 Hz game tick')
    x0, x1 = 280, 1940
    ms = lambda t: x0 + (x1 - x0) * t / 140.0       # 0..140 ms
    def lane(y, label, sub=None):
        text(d, (30, y - 22), label, 28, NAVY, True)
        if sub: text(d, (30, y + 12), sub, 22, GREY)
    # ruler
    for t in range(0, 141, 10):
        d.line([(ms(t), 150), (ms(t), 1000)], fill=(235, 235, 235), width=2)
        text(d, (ms(t), 128), f'{t}', 22, GREY, False, 'ma')
    text(d, (x1, 1010), 'milliseconds', 22, GREY, False, 'ra')
    # raw LEFT pin (active low) with bounce at t=10
    y_hi, y_lo = 210, 280
    lane(245, 'LEFT pin', 'GPIO17 (raw)')
    pts = [(ms(0), y_hi), (ms(10), y_hi)]
    b = [(10, y_lo), (10.8, y_hi), (11.6, y_lo), (12.1, y_hi), (12.9, y_lo)]
    for t, y in b: pts += [(ms(t), pts[-1][1]), (ms(t), y)]
    pts += [(ms(95), y_lo), (ms(95), y_hi), (ms(140), y_hi)]
    d.line(pts, fill=INK, width=4)
    text(d, (ms(11.5), y_lo + 10), 'bounce', 22, RED, False, 'ma')
    text(d, (ms(60), y_lo - 40), 'pressed = LOW', 22, GREY, False, 'ma')
    # samples
    lane(360, '1 kHz sample', 'input task, core 0')
    for t in range(0, 141):
        d.line([(ms(t), 345), (ms(t), 375)], fill=CYAN if 10 <= t < 22 else (190, 200, 205), width=2)
    # debounced
    y_hi2, y_lo2 = 440, 510
    lane(475, 'debounced', '8 ms stable')
    d.line([(ms(0), y_hi2), (ms(20.9), y_hi2), (ms(20.9), y_lo2), (ms(103), y_lo2), (ms(103), y_hi2), (ms(140), y_hi2)], fill=INK, width=4)
    d.rectangle((ms(12.9), y_hi2 - 30, ms(20.9), y_hi2 - 6), fill=AMBER, outline=GOLD_D)
    text(d, (ms(16.9), y_hi2 - 62), '8 ms', 22, GOLD_D, True, 'ma')
    dashed(d, (ms(12.9), 290), (ms(12.9), 600), fill=GOLD_D, width=3)
    text(d, (ms(13.5), 560), 'press is time-stamped HERE (last raw edge),\nso the chord window measures your real thumb timing',
         22, GOLD_D) if False else d.multiline_text((ms(14), 540), 'the press is time-stamped HERE (last raw edge),\nso the 100 ms chord window measures real thumb timing',
                                                    font=F(22), fill=GOLD_D, spacing=6)
    # RIGHT pin, pressed at 70 ms -> chord
    lane(670, 'RIGHT pin', 'GPIO18 (debounced)')
    d.line([(ms(0), 640), (ms(70), 640), (ms(70), 705), (ms(100), 705), (ms(100), 640), (ms(140), 640)], fill=INK, width=4)
    d.rectangle((ms(12.9), 740, ms(112.9), 778), fill=(225, 240, 250), outline=CYAN, width=3)
    text(d, (ms(62.9), 759), 'chord window: 100 ms from the LEFT press', 22, CYAN, True, 'mm')
    # game ticks
    lane(850, 'game tick', '60 Hz, core 1')
    t = 0.0
    while t <= 140:
        d.line([(ms(t), 825), (ms(t), 875)], fill=NAVY, width=3); t += 1000 / 60
    text(d, (ms(16.7 * 7), 885), '16.7 ms apart', 22, GREY, False, 'ma')
    # outcomes
    lane(950, 'result')
    d.rounded_rectangle((ms(16.7), 925, ms(66), 980), 10, fill=AMBER, outline=GOLD_D, width=3)
    text(d, (ms(41), 952), 'FLAP LEFT (at once)', 22, INK, True, 'mm')
    d.rounded_rectangle((ms(70), 925, ms(118), 980), 10, fill=(220, 245, 230), outline=GREEN, width=3)
    text(d, (ms(94), 952), 'RIGHT in window: STRAIGHT', 22, INK, True, 'mm')
    d.multiline_text((40, 1040), 'The first press is never held back: the flap goes out on the next tick. If the other wing arrives inside the 100 ms window, the pending flap\n'
                     '(or, if it already fired, a fresh one) becomes STRAIGHT (up). Holding a wing steers. A flap that cannot fire yet waits up to 8 ticks (STR_INPUT_FLAP_BUFFER_TICKS) in the buffer.',
                     font=F(24), fill=INK, spacing=8)
    save(im, 'f05_timing.png')

# ---- F6: flash map ---------------------------------------------------------------------------------
def fig_flash():
    W, H = 2000, 860
    im, d = canvas(W, H)
    title(d, W, 'What lives where in the 16 MB flash chip', 'firmware/partitions.csv (+ the ESP-IDF bootloader and partition table)')
    parts = [('bootloader', 0x0, 0x8000, (180, 180, 180)), ('partition\ntable', 0x8000, 0x1000, (150, 150, 150)),
             ('nvs  24 KB\nhigh score,\nDART trial', 0x9000, 0x6000, GOLD), ('phy 4 KB', 0xF000, 0x1000, (200, 200, 200)),
             ('factory app  4 MB\nthe STRUTHIO firmware\n(idf.py flash)', 0x10000, 0x400000, (120, 170, 210)),
             ('assets  9 MB partition\nstruthio.pak, 8.3 MB used\nmapped, never copied to RAM', 0x410000, 0x900000, (130, 200, 150)),
             ('music 2.9 MB\nsoundtrack 1.9 MB\n(24 kHz ADPCM)', 0xD10000, 0x2F0000, (240, 190, 120))]
    x0, x1, y0, y1 = 60, 1940, 300, 430
    total = 0x1000000
    import math
    # small partitions get a minimum width so they stay readable
    widths = []
    for n, o, s, c in parts:
        widths.append(max(s / total * (x1 - x0), 70))
    k = (x1 - x0) / sum(widths); widths = [w * k for w in widths]
    x = x0
    for (n, o, s, c), w in zip(parts, widths):
        d.rectangle((x, y0, x + w, y1), fill=c, outline=INK, width=3)
        if w > 300:
            d.multiline_text((x + w / 2, (y0 + y1) / 2), n, font=F(28, True), fill=INK, anchor='mm', align='center', spacing=6)
        text(d, (x + 4, y1 + 14), f'0x{o:X}', 20, GREY, False, 'la') if w > 120 or o in (0x10000,) else None
        x += w
    # callouts for the small ones
    small = [(0, 'bootloader'), (1, 'partition table'), (2, 'nvs 24 KB: high score, DART trial, volume'), (3, 'phy 4 KB: radio calibration')]
    xs = [x0]
    for w in widths: xs.append(xs[-1] + w)
    for i, (idx, lab) in enumerate(small):
        cx = (xs[idx] + xs[idx + 1]) / 2
        ty = 190 + (i % 2) * 50 if i < 2 else 520 + (i - 2) * 50
        if i < 2:
            d.line([(cx, y0), (cx, ty + 30)], fill=INK, width=2); text(d, (cx + 10, ty), lab, 24, INK)
        else:
            d.line([(cx, y1), (cx, ty + 12)], fill=INK, width=2); text(d, (cx + 10, ty), lab, 24, INK)
    text(d, (x1, y1 + 44), 'ends at 0x1000000 = 16 MB', 20, GREY, False, 'ra')
    d.multiline_text((60, 660), '•  idf.py flash writes the bootloader, the partition table, the app AND, when\n'
                     '    build/assets/struthio.pak and struthio_music.ima exist, the art and the soundtrack (firmware/CMakeLists.txt).\n'
                     '•  No pack: a CMake warning and the greybox renderer. No soundtrack: a warning, sound effects only.\n'
                     '•  nvs survives re-flashing the app; "idf.py erase-flash" clears it (high score, DART trial and volume reset).',
                     font=F(24), fill=INK, spacing=10)
    save(im, 'f06_flashmap.png')

# ---- F7: cores and bands ---------------------------------------------------------------------------
def fig_cores():
    W, H = 2000, 1230
    im, d = canvas(W, H)
    title(d, W, 'Two CPU cores, one panel: how a frame reaches the screen',
          'firmware/main/main.c  •  the AXS15231B over QSPI has no row address, so bands must arrive top to bottom')
    # lanes
    lanes = [('CORE 0', 170, [('input task  1 kHz', 0, 1, (225, 240, 250)), ('render: EVEN bands 0, 2, 4 … 28', 0, 1, (130, 200, 150))]),
             ('CORE 1', 470, [('game task  60 Hz: st_step + scene + HUD model', 0, 1, (120, 170, 210)), ('render helper: ODD bands 1, 3 … 29', 0, 1, (200, 230, 160))])]
    for name, y, rows in lanes:
        box(d, (40, y, 1180, y + 250), fill=(248, 248, 248), outline=NAVY, width=3)
        text(d, (70, y + 20), name, 34, NAVY, True)
        for i, (lab, a, b, c) in enumerate(rows):
            d.rounded_rectangle((260, y + 25 + i * 110, 1150, y + 115 + i * 110), 12, fill=c, outline=INK, width=2)
            text(d, (705, y + 70 + i * 110), lab, 28, INK, True, 'mm')
    arrow(d, (232, 600), (232, 300), fill=GOLD_D, width=6)
    text(d, (260, 445), 'every 2nd tick the game publishes a frame (\u2264 30 fps); render draws the newest', 22, GOLD_D, False, 'lm')
    # turn token
    box(d, (40, 760, 1180, 1100), fill=AMBER, outline=GOLD_D, width=3)
    text(d, (70, 780), 'The turn rule (g_turn semaphores)', 30, GOLD_D, True)
    d.multiline_text((70, 830),
                     'Each core draws its band into its own buffer, then WAITS for its turn.\n'
                     'Band k may be sent only after band k−1 has been sent.\n'
                     'Band 0 starts a frame (RAMWR); every other band continues at the\n'
                     'panel\'s write pointer (RAMWRC). Out of order = wrong rows on screen.\n'
                     'host/band_order_test: "send whichever is ready" misplaced 4,736 of\n'
                     '6,000 bands; the turn rule misplaced 0. The log counts "band-order".',
                     font=F(25), fill=INK, spacing=8)
    # panel bands
    px, py, bw, bh = 1330, 170, 320, 30
    text(d, (px + bw / 2, py - 10), 'panel 320 x 480', 26, NAVY, True, 'md')
    for k in range(30):
        c = (130, 200, 150) if k % 2 == 0 else (200, 230, 160)
        d.rectangle((px, py + k * bh, px + bw, py + (k + 1) * bh), fill=c, outline=(90, 110, 90), width=1)
        if k < 6 or k > 26:
            text(d, (px + bw / 2, py + k * bh + bh / 2), f'band {k}  (rows {k * 16}–{k * 16 + 15})  core {k % 2}', 17, INK, False, 'mm')
    text(d, (px + bw / 2, py + 16 * bh), '⋮', 30, INK, True, 'mm')
    for k in range(5):
        arrow(d, (px + bw + 30, py + k * bh + 15), (px + bw + 30, py + (k + 1) * bh + 15), fill=GOLD_D, width=3, head=12)
    d.multiline_text((px + bw + 60, py + 20), 'sent in\nthis order,\ntop to\nbottom', font=F(24, True), fill=GOLD_D, spacing=6)
    d.multiline_text((px - 20, py + 30 * bh + 30), '30 bands × 16 rows = 480 rows\nRGB565, 2 bytes per pixel', font=F(24), fill=GREY, spacing=6)
    save(im, 'f07_cores.png')

# ---- F8: golden replay ---------------------------------------------------------------------------
def fig_golden():
    W, H = 2000, 900
    im, d = canvas(W, H)
    title(d, W, 'Why "GOLDEN PASS" means the device plays the real game',
          'the browser game is the reference; the C port must reproduce it bit for bit')
    B = [(60, 170, 520, 400, 'STRUTHIO ARCADE 1.8.0\n(browser, JavaScript)\nplays recorded inputs', (230, 236, 245)),
         (740, 170, 1260, 400, 'golden trace file\ninputs for every tick +\nSHA-256 of the whole\ngame state every tick', AMBER),
         (1480, 170, 1940, 400, 'C core on the desktop\nrun_tests.sh replays\nall 5 traces', (225, 245, 230)),
         (1480, 560, 1940, 820, 'C core ON THE ESP32\nservice mode replays\nclimb.trace (10,011 ticks)', (225, 245, 230))]
    for x0, y0, x1, y1, s, c in B:
        box(d, (x0, y0, x1, y1), fill=c)
        d.multiline_text(((x0 + x1) / 2, (y0 + y1) / 2), s, font=F(30, True), fill=INK, anchor='mm', align='center', spacing=8)
    arrow(d, (520, 285), (740, 285)); text(d, (630, 250), 'records', 24, GREY, False, 'mm')
    arrow(d, (1260, 285), (1480, 285)); text(d, (1370, 250), 'replays', 24, GREY, False, 'mm')
    arrow(d, (1000, 400), (1000, 690), width=6); arrow(d, (1000, 690), (1480, 690))
    text(d, (1010, 520), 'embedded in the firmware', 24, GREY)
    d.multiline_text((60, 480), 'Every tick the C state is hashed with the same\nSHA-256 and compared with the browser\'s hash.\n'
                     'One wrong bit anywhere (a position, a timer,\nthe random seed) changes the hash: FAIL, with\nthe tick number where it went wrong.',
                     font=F(27), fill=INK, spacing=10)
    text(d, (1710, 430), 'GOLDEN REPLAY: all 5 traces bit-exact', 22, GREEN, True, 'ma')
    text(d, (1710, 840), 'screen: GOLDEN PASS 10011 TICKS', 22, GREEN, True, 'ma')
    save(im, 'f08_golden.png')

# ---- F9: HUD, annotated -------------------------------------------------------------------------
def fig_hud():
    src = Image.open(os.path.join(ROOT, 'docs', 'renders', 'panel_vs_browser_2809.png')).convert('RGB')
    frame = src.crop((0, 0, 320, 480))
    k = 3
    W, H = 2000, 1560
    im, d = canvas(W, H)
    title(d, W, 'Reading the game screen (C panel renderer, mortal trace tick 2809)',
          'HUD fields from arcade/src/ui/hud.mjs; the device draws the same layers from the asset pack')
    big = frame.resize((320 * k, 480 * k), Image.NEAREST if False else Image.LANCZOS)
    ox, oy = 40, 130
    im.paste(big, (ox, oy))
    d.rectangle((ox, oy, ox + 320 * k, oy + 480 * k), outline=INK, width=3)
    # callouts: (x on frame, y on frame, label, note)
    calls = [(42, 27, 'SCORE', 'six digits; rolls over\nat 1,000,000'),
             (97, 27, 'ROUND', 'R01, R02 …'),
             (145, 27, 'RINGS', 'collected of 6; at 6/6 the\ngold ring at the moon opens'),
             (222, 27, 'RIVALS DEFEATED', 'this round'),
             (285, 27, 'JOUST MARKS', 'your lives: 11 at the start,\nmax 11; bar = lives left'),
             (243, 147, 'RING', 'fly through it'),
             (228, 182, 'YOU', 'the rider on the ostrich'),
             (155, 345, 'ISLAND', 'land, walk, take off'),
             ]
    lx = 1080
    for i, (fx, fy, lab, note) in enumerate(calls):
        px, py = ox + fx * k, oy + fy * k + (34 if fy < 40 else 0)
        d.ellipse((px - 24, py - 24, px + 24, py + 24), fill=GOLD, outline=INK, width=3)
        text(d, (px, py), str(i + 1), 28, INK, True, 'mm')
        tx, ty = lx, 160 + i * 172
        d.ellipse((tx, ty, tx + 48, ty + 48), fill=GOLD, outline=INK, width=3)
        text(d, (tx + 24, ty + 24), str(i + 1), 28, INK, True, 'mm')
        text(d, (tx + 70, ty + 2), lab, 34, NAVY, True)
        d.multiline_text((tx + 70, ty + 48), note, font=F(26), fill=INK, spacing=6)
    save(im, 'f09_hud.png')

# ---- F10: pipeline ------------------------------------------------------------------------------
def fig_pipeline():
    W, H = 2000, 640
    im, d = canvas(W, H)
    title(d, W, 'How one picture is made on the device', 'core/ → render/ → firmware/  (the same C files are tested on the desktop)')
    steps = [('wing\nbuttons', 'GPIO17/18\n1 kHz', (225, 240, 250)),
             ('simulation', 'st_step\n60 Hz', (120, 170, 210)),
             ('scene builder', 'list of textured\nquads (same as\nthe browser)', (200, 230, 160)),
             ('panel renderer', '16-row bands,\ntextures + HUD\nfrom struthio.pak', (130, 200, 150)),
             ('QSPI\n40 MHz', 'band by band,\ntop to bottom', AMBER),
             ('AXS15231B\npanel', '320 x 480\nRGB565', (230, 230, 230))]
    n = len(steps); bw = 270; gap = (W - 80 - n * bw) / (n - 1)
    for i, (a, b, c) in enumerate(steps):
        x = 40 + i * (bw + gap)
        box(d, (x, 170, x + bw, 330), fill=c)
        d.multiline_text((x + bw / 2, 250), a, font=F(30, True), fill=INK, anchor='mm', align='center', spacing=4)
        d.multiline_text((x + bw / 2, 350), b, font=F(24), fill=GREY, anchor='ma', align='center', spacing=4)
        if i < n - 1: arrow(d, (x + bw + 4, 250), (x + bw + gap - 4, 250), head=18)
    d.multiline_text((40, 520), 'If struthio.pak is missing, the panel renderer is replaced by the greybox renderer (flat palette, no textures): '
                     'the game itself is identical.\nThe game never waits for the screen: if drawing is slow, frames are dropped, never game ticks.',
                     font=F(25), fill=INK, spacing=8)
    save(im, 'f10_pipeline.png')

# ---- F11: bench layout ---------------------------------------------------------------------------
def fig_bench():
    W, H = 2000, 1000
    im, d = canvas(W, H)
    title(d, W, 'The A0 bench: everything the first playable round needs', 'USB power only: no battery, no speaker, no shell, camera connector empty')
    # computer
    box(d, (60, 220, 480, 520), fill=(230, 230, 235)); text(d, (270, 330), 'computer', 34, INK, True, 'mm')
    text(d, (270, 380), 'idf.py monitor', 26, GREY, False, 'mm', mono=True)
    # board
    bx0, by0, bx1, by1 = 820, 160, 1260, 820
    box(d, (bx0, by0, bx1, by1), fill=(30, 40, 50), outline=INK, r=20)
    d.rectangle((bx0 + 40, by0 + 50, bx1 - 40, by1 - 120), fill=(15, 15, 20), outline=(90, 90, 90), width=3)
    d.multiline_text(((bx0 + bx1) / 2, (by0 + by1) / 2 - 170), 'Waveshare\nESP32-S3\nTouch-LCD-3.5B', font=F(30, True), fill=WHITE, anchor='mm', align='center', spacing=6)
    d.rounded_rectangle(((bx0 + bx1) / 2 - 40, by1 - 30, (bx0 + bx1) / 2 + 40, by1 + 6), 8, fill=(170, 170, 170))
    text(d, ((bx0 + bx1) / 2, by1 + 20), 'USB-C', 24, INK, True, 'ma')
    d.line([(270, 520), (270, 900), ((bx0 + bx1) / 2, 900), ((bx0 + bx1) / 2, by1 + 60)], fill=(60, 60, 60), width=10)
    text(d, (560, 910), 'USB-C DATA cable (power + flashing + log)', 26, INK)
    # header
    hx = bx1 - 30
    d.rectangle((hx - 20, by0 + 200, hx + 10, by0 + 500), fill=(20, 20, 20), outline=GOLD, width=2)
    text(d, (hx - 40, by0 + 205), 'expansion header', 22, GOLD, False, 'ra')
    # switches
    for i, (lab, col, gp) in enumerate((('LEFT WING', (240, 240, 240), 'GPIO17'), ('RIGHT WING', (70, 120, 210), 'GPIO18'))):
        sy = 250 + i * 330
        d.rectangle((1560, sy, 1780, sy + 220), fill=(205, 160, 90), outline=INK, width=3)
        d.rectangle((1610, sy + 50, 1730, sy + 170), fill=(40, 40, 40))
        d.ellipse((1635, sy + 75, 1705, sy + 145), fill=(110, 110, 110))
        text(d, (1670, sy - 10), lab, 28, NAVY, True, 'md')
        d.line([(hx + 10, by0 + 240 + i * 60), (1450, by0 + 240 + i * 60), (1450, sy + 70), (1610, sy + 70)], fill=col if i else (200, 200, 200), width=8)
        text(d, (1300, by0 + 205 + i * 60), gp, 22, INK, True)
    d.line([(hx + 10, by0 + 440), (1500, by0 + 440), (1500, 250 + 160), (1610, 410)], fill=INK, width=8)
    d.line([(1520, 410), (1520, 740), (1610, 740)], fill=INK, width=8)
    text(d, (1300, by0 + 450), 'GND', 22, INK, True)
    text(d, (1580, 930), 'three wires: LEFT, RIGHT, shared GND', 26, INK, False, 'ma')
    d.multiline_text((500, 560), 'Leave OFF the bench:\n• the LiPo battery\n• the speaker\n• any camera module\n• the shell', font=F(28), fill=RED, spacing=8)
    save(im, 'f11_bench.png')

# ---- F12: sound path ----------------------------------------------------------------------------
def fig_audio():
    W, H = 2000, 900
    im, d = canvas(W, H)
    title(d, W, 'How the handheld makes its sound', 'audio/struthio_audio.c (the browser\'s conductor + synth, ported and checked sample by sample) \u2192 firmware audio task \u2192 ES8311')
    top = [('game events', 'FLAP, RING, JOUST,\nEGG, HATCH, DEATH,\nGOLD RING, ROUND', (225, 240, 250)),
           ('conductor', 'priority, min gap,\nbeat quantize,\npitch jitter', (200, 230, 160)),
           ('synth', '7 voices: noise,\nsine, triangle,\npulse + filter', (130, 200, 150)),
           ('SFX level', 'x 0.68 x 0.92\ncompressor\n(-12 dB, 8:1)', (120, 170, 210))]
    bw, gap, y = 330, 120, 170
    xs = [40 + i * (bw + gap) for i in range(4)]
    for x, (a, b, c) in zip(xs, top):
        box(d, (x, y, x + bw, y + 130), fill=c)
        text(d, (x + bw / 2, y + 65), a, 32, INK, True, 'mm')
        d.multiline_text((x + bw / 2, y + 145), b, font=F(24), fill=GREY, anchor='ma', align='center', spacing=4)
    for i in range(3): arrow(d, (xs[i] + bw + 6, y + 65), (xs[i + 1] - 6, y + 65))
    # music lane
    my = 520
    box(d, (40, my, 40 + bw, my + 130), fill=AMBER)
    text(d, (40 + bw / 2, my + 65), 'music partition', 30, INK, True, 'mm')
    d.multiline_text((40 + bw / 2, my + 145), '160 s loop, 24 kHz\nIMA ADPCM, 1.9 MB', font=F(24), fill=GREY, anchor='ma', align='center', spacing=4)
    box(d, (xs[1], my, xs[1] + bw, my + 130), fill=(250, 220, 170))
    text(d, (xs[1] + bw / 2, my + 65), 'decode x2', 32, INK, True, 'mm')
    d.multiline_text((xs[1] + bw / 2, my + 145), 'to 48 kHz', font=F(24), fill=GREY, anchor='ma', align='center')
    box(d, (xs[2], my, xs[2] + bw, my + 130), fill=(250, 220, 170))
    text(d, (xs[2] + bw / 2, my + 65), 'x 0.56, ducked', 30, INK, True, 'mm')
    d.multiline_text((xs[2] + bw / 2, my + 145), 'dips on rings, jousts,\ndeaths, round clear', font=F(24), fill=GREY, anchor='ma', align='center', spacing=4)
    arrow(d, (40 + bw + 6, my + 65), (xs[1] - 6, my + 65)); arrow(d, (xs[1] + bw + 6, my + 65), (xs[2] - 6, my + 65))
    # mix + output
    mx = 1870
    d.ellipse((mx - 50, 395, mx + 50, 495), fill=WHITE, outline=NAVY, width=5); text(d, (mx, 445), '+', 60, NAVY, True, 'mm')
    d.line([(xs[3] + bw + 6, y + 65), (mx, y + 65)], fill=NAVY, width=6); arrow(d, (mx, y + 65), (mx, 393))
    arrow(d, (xs[2] + bw + 6, my + 65), (mx - 40, 480))
    out = [('ES8311', 'I2S 48 kHz\n16-bit mono'), ('NS4150B', 'amplifier'), ('speaker', '6\u20138 \u03a9, ~1 W')]
    ox = mx + 120
    for i, (a, b) in enumerate(out):
        bx = ox + i * 0
    # output column on the right edge
    box(d, (1440, 720, 1980, 860), fill=(230, 230, 230))
    text(d, (1710, 760), 'ES8311 \u2192 NS4150B \u2192 speaker', 26, INK, True, 'mm')
    text(d, (1710, 810), 'volume: 5 levels (service mode)', 22, GREY, False, 'mm')
    arrow(d, (mx, 497), (mx, 718))
    text(d, (mx - 20, 600), 'clip, 48 kHz', 22, GREY, False, 'ra')
    save(im, 'f12_audio.png')

if __name__ == '__main__':
    for f in (fig_pullup, fig_multimeter, fig_solder, fig_switchboard, fig_timing, fig_flash, fig_cores, fig_golden, fig_hud, fig_pipeline, fig_bench, fig_audio):
        f()
