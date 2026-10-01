#!/usr/bin/env python3
# STRUTHIO HANDHELD · A1 "portable arcade" layout drawing: front and rear, to
# scale in mm. The board, LCD and screw positions come from
# ../struthio_a0_enclosure.scad; the body outline, overlay art, pill row, button
# pads, grille and battery door are the A1 proposal (manual section 11).
# Writes a1_portable_arcade.html (an SVG page that loads the game's own box art
# from arcade/assets/art); render it to PNG with any browser.
import os

HERE = os.path.dirname(os.path.abspath(__file__))
HERO = '../../../arcade/assets/art/hero-art.webp'      # 941 x 1672, the STRUTHIO box art
SCREEN = 'art/screen_mortal_2809.png'                  # the C panel renderer's frame, 320 x 480

# ---- geometry (mm, origin = face centre, y DOWN) -------------------------------------
TOP, BOT = -70.0, 88.0             # A1 body: 158 mm tall (A0: -64..64)
W_TOP, W_BOT = 88.0, 82.0          # tapered sides
LCD_W, LCD_H, LCD_Y = 48.96, 73.44, -13.78            # A0: LCD centre (y up +13.78)
SCREW = [(-37, -55.5), (37, -55.5), (-37, 55.5), (37, 55.5)]
WING = [(-11, 8), (7, 10), (11, -4), (5, -10), (-9, -8), (-12, 0)]   # A0 cap outline, y down
WING_X, WING_Y = 21.5, 51.0        # A1: lowered 3.5 mm from A0 (47.5) to clear the pill row
PAD_R = 13.0
PILL_Y = 30.0
PILLS = [(-28, 'OFF'), (-14, 'SOUND'), (0, 'PAUSE'), (14, 'ON/START')]
CLEAR_X = 28.0
S = 6                               # px per mm
GOLD, CYAN, RED, NAVY, INK = '#E2A93F', '#20C4D7', '#D9643A', '#102838', '#17191C'

def outline():
    """Tapered 'tombstone' body: crowned top, straight tapered sides, scooped bottom."""
    t, b, wt, wb, r = TOP, BOT, W_TOP / 2, W_BOT / 2, 9
    return (f'M {-wt + r} {t + 1.5} Q 0 {t - 2.5} {wt - r} {t + 1.5} '
            f'Q {wt} {t + 2} {wt} {t + r + 1} L {wb} {b - r} Q {wb} {b} {wb - r} {b} '
            f'Q 0 {b - 3} {-wb + r} {b} Q {-wb} {b} {-wb} {b - r} L {-wt} {t + r + 1} Q {-wt} {t + 2} {-wt + r} {t + 1.5} Z')

def txt(x, y, s, size, fill='#E9E7DE', weight=700, anchor='middle', extra=''):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" {extra}>{s}</text>'

def hero(box, src_x0, src_x1, src_cy, clip_id):
    """Places the box art so source columns src_x0..src_x1 fill the box width and
    source row src_cy sits at the box's vertical centre; clipped to the box."""
    x0, y0, x1, y1 = box
    s = (x1 - x0) / (src_x1 - src_x0)
    ix, iy = x0 - src_x0 * s, (y0 + y1) / 2 - src_cy * s
    return (f'<clipPath id="{clip_id}"><rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="2.5"/></clipPath>'
            f'<image href="{HERO}" x="{ix}" y="{iy}" width="{941 * s}" height="{1672 * s}" clip-path="url(#{clip_id})" preserveAspectRatio="none"/>')

def front():
    o = f'<path d="{outline()}" fill="{NAVY}" stroke="#05121C" stroke-width="0.6"/>'
    # marquee: the logo from the box art
    for k, c in enumerate([GOLD, RED, '#B91E18']):
        o += f'<rect x="-40" y="{-63.6 + k * 1.6}" width="80" height="1.0" fill="{c}"/>'
    o += hero((-30.5, -68.6, 30.5, -54.4), 0, 941, 222, 'mq')
    # raised screen bezel and the panel showing a real frame from the C renderer
    o += f'<rect x="{-LCD_W / 2 - 3.2}" y="{LCD_Y - LCD_H / 2 - 3.2}" width="{LCD_W + 6.4}" height="{LCD_H + 6.4}" rx="2.5" fill="#1C2026" stroke="{GOLD}" stroke-width="0.7"/>'
    o += f'<image href="{SCREEN}" x="{-LCD_W / 2}" y="{LCD_Y - LCD_H / 2}" width="{LCD_W}" height="{LCD_H}" preserveAspectRatio="none"/>'
    # control deck: the box-art battle scene behind the controls
    o += hero((-38, 25.5, 38, 77.0), 70, 870, 700, 'deck')
    o += '<rect x="-38" y="25.5" width="76" height="51.5" rx="2.5" fill="#000" opacity="0.18"/>'
    # pill row on a dark strip, labels underneath, ALL CLEAR pinhole at the end
    o += f'<rect x="-36" y="{PILL_Y - 3.6}" width="72" height="9.2" rx="2" fill="#0B0D10" opacity="0.82"/>'
    for x, lab in PILLS:
        o += f'<rect x="{x - 4.6}" y="{PILL_Y - 1.9}" width="9.2" height="3.8" rx="1.9" fill="#D8D6CC" stroke="#000" stroke-width="0.25"/>'
        o += txt(x, PILL_Y + 4.6, lab, 1.75)
    o += f'<circle cx="{CLEAR_X}" cy="{PILL_Y}" r="0.9" fill="#000" stroke="#999" stroke-width="0.3"/>'
    o += txt(CLEAR_X, PILL_Y + 4.6, 'ALL CLEAR', 1.75)
    # wing buttons on round pads
    for side in (-1, 1):
        cx = side * WING_X
        o += f'<circle cx="{cx}" cy="{WING_Y}" r="{PAD_R}" fill="{NAVY}" stroke="{GOLD}" stroke-width="0.8" opacity="0.95"/>'
        pts = ' '.join(f'{cx + (px if side < 0 else -px)},{WING_Y + py}' for px, py in WING)
        o += f'<polygon points="{pts}" fill="{GOLD}" stroke="#7A5A16" stroke-width="0.45"/>'
        o += txt(cx + side * 6, WING_Y + PAD_R + 3.4, 'LEFT WING' if side < 0 else 'RIGHT WING', 2.1, extra='stroke="#000" stroke-width="0.35" paint-order="stroke"')
    # speaker: raised oval with horizontal slots
    o += '<rect x="-13" y="66" width="26" height="9.5" rx="4.75" fill="#1A3445" stroke="#05121C" stroke-width="0.5"/>'
    for k in range(4):
        o += f'<rect x="-9" y="{67.6 + k * 2.0}" width="18" height="0.9" rx="0.45" fill="#05121C"/>'
    # tagline band, in the box art's striped style
    for k, c in enumerate([GOLD, RED, '#B91E18']):
        o += f'<rect x="-36" y="{79.6 + k * 1.1}" width="17" height="0.7" fill="{c}"/><rect x="19" y="{79.6 + k * 1.1}" width="17" height="0.7" fill="{c}"/>'
    o += txt(0, 82.0, 'PORTABLE ARCADE', 3.3, '#FFF6DF', 800)
    o += f'<rect x="-5" y="{BOT - 3.2}" width="10" height="1.6" rx="0.8" fill="#000"/>'   # USB-C
    return o

def rear():
    o = f'<path d="{outline()}" fill="{NAVY}" stroke="#05121C" stroke-width="0.6"/>'
    for x, y in SCREW:
        o += f'<circle cx="{x}" cy="{y}" r="1.6" fill="#05121C" stroke="#5A6E7C" stroke-width="0.3"/>'
    o += f'<circle cx="0" cy="{BOT - 9}" r="1.6" fill="#05121C" stroke="#5A6E7C" stroke-width="0.3"/>'
    o += '<rect x="-24" y="-46" width="48" height="66" rx="3" fill="#163246" stroke="#3E5A6C" stroke-width="0.6"/>'
    o += txt(0, -15, 'BATTERY', 3.2, '#8FA6B5', 800)
    o += txt(0, -10.5, 'door with one captive screw', 2.0, '#8FA6B5', 500)
    o += '<circle cx="0" cy="16.5" r="1.4" fill="#05121C" stroke="#8FA6B5" stroke-width="0.3"/>'
    o += '<rect x="-30" y="31" width="60" height="22" rx="1.6" fill="#E9E7DE"/>'
    o += txt(0, 37.5, 'STRUTHIO  PORTABLE ARCADE', 2.6, INK, 800)
    o += txt(0, 42.0, 'SERVICE: hold both wings while switching on', 1.9, INK, 500)
    o += txt(0, 45.6, 'ALL CLEAR: press the pinhole with a paper clip', 1.9, INK, 500)
    o += txt(0, 49.2, 'Charge: USB-C on the bottom edge', 1.9, INK, 500)
    o += f'<rect x="-5" y="{BOT - 3.2}" width="10" height="1.6" rx="0.8" fill="#000"/>'
    return o

FX, RX, CY = 175, 287, 94            # view centres on the sheet (mm)

def view(cx, title, body):
    return (f'<text x="{cx * S}" y="{14 * S}" class="t">{title}</text>'
            f'<g transform="translate({cx * S},{CY * S}) scale({S})">{body}</g>')

def callouts():
    items = [(-61.5, -30, 'Marquee: the STRUTHIO logo from the game\'s box art'),
             (-30, -27.6, 'Raised screen bezel; clear lens over the 320 x 480 IPS'),
             (PILL_Y, -28, 'Pill row: OFF, SOUND, PAUSE, ON/START, ALL CLEAR pinhole'),
             (44, -33, 'Control deck: box-art battle scene printed under the controls'),
             (WING_Y, -WING_X - 6, 'Wing buttons on round pads (A0 caps)'),
             (70.5, -13, 'Speaker: raised oval with slots'),
             (80.7, -36, 'Tagline band, striped like the box art')]
    o = ''
    for y, fx, lab in items:
        py = (CY + y) * S
        o += f'<line x1="{(FX - 66) * S}" y1="{py}" x2="{(FX + fx) * S}" y2="{py}" class="l"/>'
        o += f'<circle cx="{(FX + fx) * S}" cy="{py}" r="4" fill="#60656C"/>'
        o += f'<text x="{(FX - 68) * S}" y="{py + 5}" class="c" text-anchor="end">{lab}</text>'
    o += f'<text x="{FX * S}" y="{(CY + BOT + 6.5) * S}" class="c" text-anchor="middle">Bottom edge: USB-C (charge / flash)</text>'
    return o

W, H = 336, 202
svg = f'''<!doctype html><html><head><meta charset="utf-8"><style>body{{margin:0}}</style></head><body>
<svg xmlns="http://www.w3.org/2000/svg" width="{W * S}" height="{H * S}" viewBox="0 0 {W * S} {H * S}" font-family="Aptos, Helvetica, Arial, sans-serif">
<style>.t{{font-size:{4.4 * S}px;font-weight:800;fill:{INK};text-anchor:middle}} .c{{font-size:{2.7 * S}px;fill:#2A2D31}} .l{{stroke:#9A9EA5;stroke-width:1.5}}</style>
<rect width="100%" height="100%" fill="#F0EFE7"/>
{view(FX, 'FRONT', front())}{view(RX, 'REAR', rear())}{callouts()}
<text x="{8 * S}" y="{(H - 5) * S}" font-size="{2.7 * S}" fill="#60656C">STRUTHIO A1 "portable arcade", 88 (top) / 82 (bottom) x 158 x 25 mm, to scale. LCD and screw positions from the A0 CAD; the rest is the A1 proposal.</text>
</svg></body></html>'''
out = os.path.join(HERE, 'a1_portable_arcade.html')
open(out, 'w').write(svg)
print(out)
