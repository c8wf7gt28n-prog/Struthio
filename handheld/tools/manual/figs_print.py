#!/usr/bin/env python3
"""STRUTHIO HANDHELD · figures for the print edition of the build manual.

    python3 tools/manual/figs_print.py OUT_DIR STUDIO_DIR

STUDIO_DIR holds the studio renders (tools/visuals/render.mjs): hero, back,
side, exploded (+ exploded.labels.json), ivory, graphite, cyan.
The terminal pictures are drawn from the real menu and doctor text
(tools/launcher/STRUTHIO.bat, tools/struthio_doctor.py output).
"""
import json, os, re, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
OUT, STUDIO = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], OUT]
import figs12 as F12
from figs12 import F, NAVY, GOLD, GOLD_D, CYAN, RED, GREEN, GREY, LIGHT, INK, WHITE, AMBER, canvas, text, box, arrow, title, save

HERE = os.path.dirname(os.path.abspath(__file__))
HH = os.path.normpath(os.path.join(HERE, '..', '..'))
PHASE = {'computer': (222, 235, 247), 'bench': (226, 239, 218), 'parts': (255, 242, 204), 'handheld': (234, 226, 244)}

# ---- the build path: gates as one strip ------------------------------------------------------------
def fig_path():
    gates = [('computer', '0', 'Desktop\nchecks', 'GOLDEN\nREPLAY'), ('bench', '1', 'Stock\nexample', 'board\nalive'),
             ('bench', '2', 'GREYBOX\nboot', 'flat\npicture'), ('bench', '3', 'Two wing\nswitches', 'counts +1'),
             ('bench', '4', 'Service\nmode', 'GOLDEN\nPASS'), ('bench', '5', 'FULL ART\nflash', 'real\npicture'),
             ('bench', '6', 'Play a\nround', 'bench\nPASS'), ('bench', '7', 'Speaker\n+ sound', 'AUDIO OK\nMUSIC OK'),
             ('parts', '8', 'Order CP1\nquote CM1', 'parts in\nhand'), ('handheld', '9', 'Print +\nfit', 'no pinch\nno preload'),
             ('handheld', '10', 'Battery +\nassembly', 'handheld\nPASS')]
    W, H = 2400, 560
    im, d = canvas(W, H)
    title(d, W, 'The build path: eleven gates, one at a time', 'do not start a gate until the one before it passes')
    n = len(gates); gw = (W - 80) / n
    for i, (ph, num, what, ok) in enumerate(gates):
        x0 = 40 + i * gw; x1 = x0 + gw - 18
        box(d, (x0, 150, x1, 470), fill=PHASE[ph], outline=NAVY, width=3, r=16)
        text(d, ((x0 + x1) / 2, 185), num, 44, NAVY, True, 'mm')
        d.multiline_text(((x0 + x1) / 2, 280), what, font=F(26, True), fill=INK, anchor='mm', align='center', spacing=4)
        d.line([(x0 + 18, 345), (x1 - 18, 345)], fill=(180, 180, 180), width=2)
        d.multiline_text(((x0 + x1) / 2, 405), ok, font=F(22), fill=GREEN, anchor='mm', align='center', spacing=2)
        if i < n - 1: arrow(d, (x1 + 1, 310), (x1 + 17, 310), width=4, head=12)
    for k, (ph, lab) in enumerate((('computer', 'computer'), ('bench', 'bench build (USB power)'), ('parts', 'custom parts'), ('handheld', 'the handheld'))):
        x = 60 + k * 520
        box(d, (x, 500, x + 40, 530), fill=PHASE[ph], outline=NAVY, width=2, r=6)
        text(d, (x + 56, 515), lab, 26, INK, False, 'lm')
    save(im, 'p01_path.png')

# ---- troubleshooting flowchart ------------------------------------------------------------------------
def fig_flow():
    steps = [('Does the board power from USB-C?', 'USB data cable only. No battery, no speaker.', 'NO POWER', 'Another cable / port; a charge-only cable shows nothing. Check the board for damage.'),
             ('Does the stock Waveshare example work?', 'This is the known-good baseline.', 'VENDOR EXAMPLE FAILS', 'Not a STRUTHIO problem yet: cable, port, ESP-IDF install, board.'),
             ('Does the GREYBOX test boot?', 'Menu option 4 (STRUTHIO_ART=greybox).', 'GREYBOX FAILS', 'Read the first error in the log (Step 5 table). Dark screen: backlight, TCA9554.'),
             ('Do the controls count in service mode?', 'Each press: +1, DOWN only while held.', 'CONTROLS FAIL', 'Meter the switch, the wire, the header pin, GND. Camera connector empty?'),
             ('Does service mode say GOLDEN PASS?', 'climb.trace, 10,011 ticks, on the device.', 'GOLDEN FAIL', 'Copy the log line; run the desktop checks. Do not edit the game.'),
             ('Does FULL ART show the real picture?', 'Menu option 5 (STRUTHIO_ART=full).', 'STILL GREYBOX', 'Boot line says greybox? "assets:" errors? Run the doctor (option 1).'),
             ('Is the picture steady, band-order 0?', 'Watch the log for 10 minutes of play.', 'TEARING / SHIFT', 'Note "transfer timeout" lines; report with the log. Do not edit the art.'),
             ('Is the sound clean at volume 1-2?', 'Service mode AUDIO OK + MUSIC OK.', 'NO / BAD SOUND', 'Vendor audio example; speaker header; volume not 0; nothing rubbing.'),
             ('Does it all survive the shell?', 'Fit coupon first, then the full print.', 'WORKS ON THE BENCH ONLY', 'Pinched wire, preloaded key, screen pressure, short to a screw.')]
    W = 1800; row = 150; H = 160 + row * len(steps) + 120
    im, d = canvas(W, H)
    title(d, W, 'Troubleshooting flow: go down until a question says NO', 'then fix only that, and start again from the top of the failed step')
    for i, (q, sub, bad, fix) in enumerate(steps):
        y = 150 + i * row
        box(d, (360, y, 1180, y + 110), fill=(232, 241, 250), outline=NAVY, width=3, r=14)
        text(d, (380, y + 18), f'{i + 1}. {q}', 30, INK, True)
        text(d, (380, y + 66), sub, 23, GREY)
        if i < len(steps) - 1: arrow(d, (770, y + 112), (770, y + row - 4), width=4, head=14)
        text(d, (720, y + 128), 'YES', 20, GREEN, True, 'ra')
        arrow(d, (1182, y + 55), (1240, y + 55), fill=RED, width=4, head=14)
        text(d, (1211, y + 28), 'NO', 20, RED, True, 'ma')
        box(d, (1244, y, 1770, y + 110), fill=(253, 235, 233), outline=RED, width=3, r=14)
        text(d, (1260, y + 14), bad, 24, RED, True)
        words, lines, cur = fix.split(), [], ''
        for w_ in words:
            if len(cur) + len(w_) > 44: lines.append(cur); cur = w_
            else: cur = (cur + ' ' + w_).strip()
        lines.append(cur)
        d.multiline_text((1260, y + 48), '\n'.join(lines[:2]), font=F(21), fill=INK, spacing=4)
    y = 150 + len(steps) * row
    box(d, (360, y, 1180, y + 70), fill=(226, 239, 218), outline=GREEN, width=3, r=14)
    text(d, (770, y + 35), 'All YES: the handheld passes. Fill in Shop Sheet C.', 28, GREEN, True, 'mm')
    d.multiline_text((40, 170), 'Rules:\n\n1. Change one\n   thing at a time.\n\n2. Go back to the\n   last gate that\n   passed.\n\n3. Write it down\n   (Shop Sheet E).\n\n4. Never fix\n   hardware by\n   editing the game.',
                     font=F(25), fill=NAVY, spacing=6)
    save(im, 'p02_flow.png')

# ---- terminal pictures ------------------------------------------------------------------------------
def terminal(lines, name, title_bar, cols=78, colours=None):
    fs = 26; lh = 34
    W = int(cols * fs * 0.61) + 60; H = 90 + lh * len(lines) + 30
    im = Image.new('RGB', (W, H), (12, 12, 12)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 50), fill=(228, 228, 228))
    for k, c in enumerate(((237, 106, 94), (245, 191, 79), (98, 197, 84))):
        d.ellipse((18 + 30 * k, 15, 38 + 30 * k, 35), fill=c)
    d.text((W // 2, 25), title_bar, font=F(22), fill=(60, 60, 60), anchor='mm')
    for i, ln in enumerate(lines):
        col = (204, 204, 204)
        for pat, c in (colours or {}).items():
            if re.search(pat, ln): col = c; break
        d.text((30, 70 + lh * i), ln, font=F(fs, mono=True), fill=col)
    save(im, name)

def fig_menu():
    bat = open(os.path.join(HH, 'tools', 'launcher', 'STRUTHIO.bat')).read()
    a = bat.index(':menu'); b = bat.index('set "CH="', a)
    lines = []
    for ln in bat[a:b].splitlines():
        m = re.match(r'echo (.*)$', ln.strip())
        if m: lines.append(m.group(1))
        elif ln.strip().startswith('if defined IDF_OK'): lines.append('   ESP-IDF : ready')
        elif ln.strip().startswith('if defined PORT'): lines.append('   Board   : COM5')
    lines.append('  Choose: _')
    terminal(lines, 'p03_menu.png', 'ESP-IDF 5.5 CMD - STRUTHIO.bat', 74,
             {r'STRUTHIO HANDHELD': (255, 214, 102), r'ready|COM5': (120, 220, 120), r'^\s+[0-9DMF]  ': (220, 220, 220)})

def fig_doctor():
    lines = ['C:\\struthio> python handheld\\tools\\struthio_doctor.py', 'STRUTHIO HANDHELD · setup doctor',
             'Windows 11 · package: C:\\struthio', '',
             'PASS  package complete: 168 files match SHA256SUMS.txt',
             'PASS  struthio.pak: 8.3 MB fits the assets partition (9.0 MB)',
             'PASS  struthio_music.ima: 1.8 MB fits the music partition (2.9 MB)',
             'PASS  package path is safe: C:\\struthio', 'PASS  Python 3.11.9', 'PASS  ESP-IDF v5.5.5',
             'INFO  firmware not set up yet (normal before the first build)',
             '      -> menu option "Build" runs: idf.py set-target esp32s3',
             'PASS  board found on COM5 (USB JTAG/serial debug unit)',
             'INFO  WSL found: desktop checks can run (menu option D)', '',
             'ALL GOOD: you can build and flash']
    terminal(lines, 'p04_doctor.png', 'ESP-IDF 5.5 CMD - setup doctor (example output)', 72,
             {r'^PASS': (120, 220, 120), r'^FAIL': (240, 110, 100), r'^WARN': (245, 200, 90), r'^INFO|->': (140, 190, 240), r'ALL GOOD': (255, 214, 102)})

# ---- studio renders --------------------------------------------------------------------------------
def trim(im, pad=40, bg=None):
    from PIL import ImageChops
    bg = bg or im.getpixel((2, 2))
    box_ = ImageChops.difference(im.convert('RGB'), Image.new('RGB', im.size, bg)).getbbox()
    if not box_: return im
    x0, y0, x1, y1 = box_
    return im.crop((max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)))

def fig_studio():
    S = lambda n: Image.open(os.path.join(STUDIO, n + '.png')).convert('RGB')
    S('hero').save(os.path.join(OUT, 'p10_hero.png'))
    # front + back pair
    a, b = S('hero'), S('back')
    pair = Image.new('RGB', (a.width + b.width, max(a.height, b.height)), a.getpixel((2, 2)))
    pair.paste(a, (0, 0)); pair.paste(b, (a.width, 0)); save(pair, 'p11_front_back.png')
    # colour options with captions
    ims = [S(n) for n in ('hero', 'ivory', 'graphite', 'cyan')]
    names = ['NAVY / GOLD', 'IVORY / GOLD', 'GRAPHITE / RED', 'TEAL / GOLD']
    w, h = ims[0].width // 2, ims[0].height // 2
    sheet = Image.new('RGB', (w * 4, h + 70), (12, 18, 26)); d = ImageDraw.Draw(sheet)
    for k, (im, nm) in enumerate(zip(ims, names)):
        sheet.paste(im.resize((w, h), Image.LANCZOS), (k * w, 0))
        d.text((k * w + w // 2, h + 35), nm, font=F(30, True), fill=(230, 230, 230), anchor='mm')
    save(sheet, 'p12_colours.png')
    # exploded view with callouts
    ex = S('exploded'); lab = json.load(open(os.path.join(STUDIO, 'exploded.labels.json')))
    names = {'lens': 'clear lens 1.0-1.5 mm', 'sticker': 'laminated art sticker', 'front': 'front shell (PETG / ASA)',
             'mat': 'STRUTHIO-CM1 silicone keys', 'cp1': 'STRUTHIO-CP1 control PCB', 'speaker': 'PUI AS02808MR-R speaker',
             'board': 'Waveshare ESP32-S3-Touch-LCD-3.5B', 'switch': 'E-Switch 500SSP1S1M7QEA', 'battery': 'THOR-503450 1000 mAh',
             'back': 'back shell + 4 x M2 x 10 screws'}
    W2, H2 = ex.width, ex.height
    canvas_ = Image.new('RGB', (W2, H2), ex.getpixel((2, 2))); canvas_.paste(ex, (0, 0)); d = ImageDraw.Draw(canvas_)
    pts = sorted([(lab[k][0], lab[k][1], k) for k in names if k in lab])
    mid = sum(p[0] for p in pts) / len(pts)
    cols = [([p for p in pts if p[0] < mid], 'left'), ([p for p in pts if p[0] >= mid], 'right')]
    for items, side in cols:
        items = sorted(items, key=lambda t: t[1])
        n = len(items); top, bot = 140, H2 - 140
        for i, (x, y, k) in enumerate(items):
            ty = top + (bot - top) * (i + 0.5) / n
            t = names[k]; tw = d.textlength(t, font=F(30, True))
            tx = 40 if side == 'left' else W2 - 40 - tw
            ax = tx + tw + 14 if side == 'left' else tx - 14
            d.line([(x, y), (ax, ty + 20)], fill=(255, 214, 102), width=3)
            d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=(255, 214, 102))
            d.rounded_rectangle((tx - 12, ty - 4, tx + tw + 12, ty + 44), 10, fill=(12, 22, 34), outline=(255, 214, 102), width=2)
            d.text((tx, ty), t, font=F(30, True), fill=(240, 240, 240))
    save(canvas_, 'p13_exploded.png')

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    fig_path(); fig_flow(); fig_menu(); fig_doctor(); fig_studio()
