"""STRUTHIO HANDHELD · terminal screenshots for the manual.

Draws captured terminal text (real output, saved by capture_screens.sh) in a
plain terminal window, colours it the way ESP-IDF's monitor and the setup
doctor do, and adds numbered call-outs that the manual's captions explain.

    from termshot import shot
    shot('out.png', 'ESP-IDF terminal  ~/struthio', lines, marks={3: 1, 7: 2})

lines: strings. A line starting with '$ ' is a typed command (prompt drawn).
marks: {line index: call-out number} or {line index: (number, colour)}.
"""
import re
from PIL import Image, ImageDraw, ImageFont

MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
MONO_B = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
SANS_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
SANS = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

BG, FG, DIM = (24, 27, 33), (214, 218, 224), (128, 134, 145)
GREEN, YELLOW, RED, CYAN, BLUE = (108, 201, 120), (229, 192, 90), (235, 105, 100), (102, 196, 214), (110, 160, 240)
GOLD = (240, 176, 40)
MARK = {'gold': GOLD, 'green': GREEN, 'red': RED, 'cyan': CYAN}


def colour_spans(ln):
    """[(text, colour, bold)] for one output line"""
    if re.match(r'^[IWE] \(\d+\)', ln) or re.match(r'^[IWE] [A-Za-z]', ln):
        return [(ln, {'I': GREEN, 'W': YELLOW, 'E': RED}[ln[0]], False)]
    m = re.match(r'^(PASS|FAIL|WARN|INFO)(\s.*)$', ln)
    if m:
        c = {'PASS': GREEN, 'FAIL': RED, 'WARN': YELLOW, 'INFO': CYAN}[m.group(1)]
        return [(m.group(1), c, True), (m.group(2), FG, False)]
    if ln.startswith('  · · ·'):
        return [(ln, (92, 98, 110), False)]
    if ln.lstrip().startswith('->'):
        return [(ln, DIM, False)]
    if ln.startswith(('GOLDEN REPLAY:', 'Hash of data verified', 'Project build complete', '0 FAIL', 'Done')):
        return [(ln, GREEN, True)]
    if re.search(r'\bFAIL(ED)?\b|ERROR|fatal error', ln):
        return [(ln, RED, False)]
    if ln.startswith(('WARNING', 'NOTE')):
        return [(ln, YELLOW, False)]
    if ln.startswith(('esptool', 'Connecting', 'Chip type', 'Connected to')):
        return [(ln, CYAN, False)]
    return [(ln, FG, False)]


def shot(out, title, lines, marks=None, cols=None, prompt='maker@bench:~/struthio$', scale=2, max_cols=104):
    marks = marks or {}
    cols = cols or min(max_cols, max(len(l) + (len(prompt) + 1 if l.startswith('$ ') else 0) for l in lines) + 1)
    fs = 13 * scale
    f, fb = ImageFont.truetype(MONO, fs), ImageFont.truetype(MONO_B, fs)
    cw = f.getlength('M'); lh = int(fs * 1.42)
    pad, bar = 14 * scale, 30 * scale
    gutter = (34 * scale) if marks else 0
    W = int(pad * 2 + cw * cols + gutter); H = bar + pad * 2 + lh * len(lines)
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im, 'RGBA')
    # window bar: neutral, no operating-system branding
    d.rectangle([0, 0, W, bar], fill=(44, 48, 56))
    for i, c in enumerate([(120, 124, 132)] * 3):
        d.ellipse([pad + i * 18 * scale, bar / 2 - 5 * scale, pad + i * 18 * scale + 10 * scale, bar / 2 + 5 * scale], fill=c)
    tf = ImageFont.truetype(SANS, 12 * scale)
    d.text((W / 2, bar / 2), title, font=tf, fill=(200, 204, 212), anchor='mm')
    def clip(s, n):
        return s if len(s) <= n else s[:n - 1] + '…'
    for i, ln in enumerate(lines):
        y = bar + pad + i * lh
        if i in marks:
            num, colname = marks[i] if isinstance(marks[i], tuple) else (marks[i], 'gold')
            c = MARK[colname]
            d.rectangle([pad - 5 * scale, y - 2 * scale, W - gutter - pad + 5 * scale, y + lh - 3 * scale], fill=c + (38,), outline=c + (255,), width=scale)
            cx, cy, r = W - gutter / 2 - 3 * scale, y + lh / 2 - 2 * scale, 10 * scale
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
            d.text((cx, cy), str(num), font=ImageFont.truetype(SANS_B, 12 * scale), fill=(20, 20, 20), anchor='mm')
        x = pad
        if ln.startswith('$ '):
            d.text((x, y), prompt, font=fb, fill=GREEN); x += cw * (len(prompt) + 1)
            d.text((x, y), clip(ln[2:], cols - len(prompt) - 1), font=fb, fill=(255, 255, 255))
            continue
        used = 0
        for text, c, bold in colour_spans(ln):
            t = clip(text, cols - used)
            if not t: break
            d.text((x, y), t, font=fb if bold else f, fill=c)
            x += cw * len(t); used += len(t)
            if t.endswith('…'): break
    im.save(out, optimize=True)
    return out
