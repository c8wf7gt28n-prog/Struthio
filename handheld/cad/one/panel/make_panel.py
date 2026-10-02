#!/usr/bin/env python3
"""STRUTHIO ONE · the face panel: one 1.0 mm clear acrylic piece, laser-cut, with the art
printed on its BACK. It is the lens over the screen, the front art and the key wells in one.

The art is the game's own (arcade/assets/art): the STRUTHIO logo and the HOME VIDEO GAME strip
from the box art, the box art's yellow/red picture frame round the screen, and the skyline and
grid from the game background behind the controls. The screen window is left unprinted (clear).

    python3 make_panel.py        writes, in this folder:
      one_panel_cut.dxf / .svg       cut lines (outline + 3 key cut-outs), mm, seen from the front
      one_panel_print.png            art as seen from the front, 600 dpi, 1 mm bleed, window transparent
      one_panel_print_MIRRORED.png   the same, mirrored: what is printed on the back of the panel
      one_panel_white.png            white underprint mask (black = white ink), mirrored like the print
      one_panel_proof.png            art with the cut lines and the clear window marked
    and, for the studio renders, ../../../build/one_sticker/sticker.png + sticker.json
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import one_cad as o

ART = os.path.join(HERE, '..', '..', '..', '..', 'arcade', 'assets', 'art')
DPI = 600
PX = DPI / 25.4                                     # px per mm
BLEED = 1.0
# screen window (clear): the visible width 47.86, centred on the active area
WIN_W, WIN_H, WIN_R = 47.86, o.AA_H - 1.10, 1.6
FRAME = [(1.0, None), (1.9, (246, 178, 27)), (2.35, (215, 38, 30))]     # black gap, yellow, red (from the box art)
INK_BLACK = (10, 11, 14)

# ---- geometry ----------------------------------------------------------------------------------------------
rings = [np.asarray(r, float) for r in o.panel2d().to_polygons()]
areas = [0.5 * np.sum(r[:, 0] * np.roll(r[:, 1], -1) - np.roll(r[:, 0], -1) * r[:, 1]) for r in rings]
outer = rings[int(np.argmax(np.abs(areas)))]
holes = [r for r, a in zip(rings, areas) if r is not outer]
X0, Y0 = outer[:, 0].min() - BLEED, outer[:, 1].min() - BLEED
X1, Y1 = outer[:, 0].max() + BLEED, outer[:, 1].max() + BLEED
W, H = round((X1 - X0) * PX), round((Y1 - Y0) * PX)
px = lambda x, y: ((x - X0) * PX, (Y1 - y) * PX)    # front view: x right, y up
L = lambda mm: mm * PX

def mask_poly(ring, grow=0.0):
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).polygon([px(x, y) for x, y in ring], fill=255)
    if grow:
        k = int(L(abs(grow)) * 2) | 1
        m = m.filter(ImageFilter.MaxFilter(k) if grow > 0 else ImageFilter.MinFilter(k))
    return m

def rrect_box(cx, cy, w, h):
    a, b = px(cx - w / 2, cy + h / 2), px(cx + w / 2, cy - h / 2)
    return [a, b]

def paste_fit(canvas, img, cx, cy, w_mm=None, h_mm=None, feather=0.0):
    """paste img centred at (cx, cy) mm, scaled to w_mm or h_mm, edges feathered into the canvas"""
    if w_mm is None: w_mm = h_mm * img.width / img.height
    if h_mm is None: h_mm = w_mm * img.height / img.width
    im = img.convert('RGB').resize((round(L(w_mm)), round(L(h_mm))), Image.LANCZOS)
    a = Image.new('L', im.size, 255)
    if feather:
        f = int(L(feather)); a = Image.new('L', im.size, 0)
        ImageDraw.Draw(a).rectangle([f, f, im.width - f, im.height - f], fill=255)
        a = a.filter(ImageFilter.GaussianBlur(f / 2))
    x, y = px(cx - w_mm / 2, cy + h_mm / 2)
    canvas.paste(im, (round(x), round(y)), a)

# ---- art ---------------------------------------------------------------------------------------------------
hero = Image.open(os.path.join(ART, 'hero-art.webp')).convert('RGB')         # 941 x 1672 box art
rear = Image.open(os.path.join(ART, 'background-rear.webp')).convert('RGB')  # 768 x 2304 sky, skyline, grid
art = Image.new('RGB', (W, H), INK_BLACK)

win_top = o.BCY + WIN_H / 2; win_bot = o.BCY - WIN_H / 2
frame_out = FRAME[-1][0]
panel_top = outer[:, 1].max(); half_w = o.UPPER_W / 2 - o.PANEL_INSET

# controller: the game's skyline and grid, horizon just above the wings, fading in from the black
s = o.LOWER_W / rear.width                       # mm per px: the background spans the full 88 mm
HORIZON_PX, HORIZON_Y = 1690, -40.0
top_y = HORIZON_Y + HORIZON_PX * s
sc = rear.resize((round(L(o.LOWER_W)), round(L(rear.height * s))), Image.LANCZOS)
lay = Image.new('RGB', (W, H), INK_BLACK); lay.paste(sc, tuple(round(v) for v in px(-o.LOWER_W / 2, top_y)))
ramp = Image.new('L', (1, H))
for j in range(H):
    y = Y1 - j / PX
    ramp.putpixel((0, j), int(255 * np.clip((-32.6 - y) / 3.0, 0, 1)))
art = Image.composite(lay, art, ramp.resize((W, H)))

# top band: the logo from the box art, its stripes carried out to the panel edges
band_cy = (panel_top + win_top + frame_out) / 2
LOGO = hero.crop((85, 95, 856, 348)); logo_h = 8.6; logo_w = logo_h * LOGO.width / LOGO.height
STRIPE_L, STRIPE_R = hero.crop((22, 140, 112, 296)), hero.crop((836, 140, 920, 296))
st_h = logo_h * (296 - 140) / LOGO.height; st_cy = band_cy + logo_h / 2 - logo_h * (140 - 95 + (296 - 140) / 2) / LOGO.height
seg = half_w + BLEED - logo_w / 2 + 2.0
paste_fit(art, STRIPE_L, -half_w - BLEED + seg / 2, st_cy, w_mm=seg, h_mm=st_h)
paste_fit(art, STRIPE_R, half_w + BLEED - seg / 2, st_cy, w_mm=seg, h_mm=st_h)
paste_fit(art, LOGO, 0, band_cy, h_mm=logo_h, feather=0.5)

# below the screen: HOME VIDEO GAME / ARCADE ADVENTURE, stripes to the edges
TEXT = hero.crop((165, 1368, 776, 1493)); text_h = 7.6; text_w = text_h * TEXT.width / TEXT.height
text_cy = win_bot - frame_out - 1.1 - text_h / 2
TS_L, TS_R = hero.crop((22, 1368, 150, 1493)), hero.crop((792, 1368, 920, 1493))
seg = half_w + BLEED - text_w / 2 + 0.5
paste_fit(art, TS_L, -half_w - BLEED + seg / 2, text_cy, w_mm=seg, h_mm=text_h)
paste_fit(art, TS_R, half_w + BLEED - seg / 2, text_cy, w_mm=seg, h_mm=text_h)
paste_fit(art, TEXT, 0, text_cy, h_mm=text_h, feather=0.4)

# the box art's picture frame round the screen
d = ImageDraw.Draw(art)
for off, col in reversed(FRAME):
    if col: d.rounded_rectangle(rrect_box(0, o.BCY, WIN_W + 2 * off, WIN_H + 2 * off), radius=L(WIN_R + off), fill=col)
    else: d.rounded_rectangle(rrect_box(0, o.BCY, WIN_W + 2 * off, WIN_H + 2 * off), radius=L(WIN_R + off), fill=INK_BLACK)
# (the window itself is made clear by the alpha below)

# ---- masks and files ---------------------------------------------------------------------------------------
window = Image.new('L', (W, H), 0)
ImageDraw.Draw(window).rounded_rectangle(rrect_box(0, o.BCY, WIN_W, WIN_H), radius=L(WIN_R), fill=255)
ink = mask_poly(outer, BLEED)                                     # print area: outline + bleed ...
for h in holes: ink.paste(0, (0, 0), mask_poly(h, -BLEED))        # ... and into the cut-outs by the bleed
ink.paste(0, (0, 0), window)                                      # never in the window
cut = mask_poly(outer)
for h in holes: cut.paste(0, (0, 0), mask_poly(h))
cut.paste(0, (0, 0), window)

def save(img, name):
    img.save(os.path.join(HERE, name), dpi=(DPI, DPI), optimize=True); print('wrote', name, img.size)

pr = art.convert('RGBA'); pr.putalpha(ink)
save(pr, 'one_panel_print.png')
save(pr.transpose(Image.FLIP_LEFT_RIGHT), 'one_panel_print_MIRRORED.png')
save(Image.eval(ink, lambda v: 255 - v).transpose(Image.FLIP_LEFT_RIGHT).convert('L'), 'one_panel_white.png')

# proof: art clipped to the cut, on grey, with the cut lines and the window outline
proof = Image.new('RGB', (W, H), (205, 208, 212)); proof.paste(art, (0, 0), cut)
dp = ImageDraw.Draw(proof)
for r in [outer] + holes: dp.line([px(x, y) for x, y in np.vstack([r, r[:1]])], fill=(236, 0, 140), width=5)
dp.rounded_rectangle(rrect_box(0, o.BCY, WIN_W, WIN_H), radius=L(WIN_R), outline=(0, 170, 255), width=5)
proof.resize((W // 3, H // 3), Image.LANCZOS).save(os.path.join(HERE, 'one_panel_proof.png'), optimize=True)
print('wrote one_panel_proof.png')

# cut files ----------------------------------------------------------------------------------------------------
def dxf(path, rs):
    out = ['0', 'SECTION', '2', 'HEADER', '9', '$INSUNITS', '70', '4', '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES']
    for r in rs:
        out += ['0', 'POLYLINE', '8', 'CUT', '66', '1', '70', '1']
        for x, y in r: out += ['0', 'VERTEX', '8', 'CUT', '10', f'{x:.4f}', '20', f'{y:.4f}']
        out += ['0', 'SEQEND']
    out += ['0', 'ENDSEC', '0', 'EOF']
    open(path, 'w').write('\n'.join(out) + '\n')

def svg(path, rs):
    w, h = X1 - X0, Y1 - Y0
    paths = ''.join(f'<path d="M {" L ".join(f"{x - X0:.3f},{Y1 - y:.3f}" for x, y in r)} Z"/>' for r in rs)
    open(path, 'w').write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}mm" height="{h:.3f}mm" viewBox="0 0 {w:.3f} {h:.3f}">'
                          f'<g fill="none" stroke="#ff0000" stroke-width="0.1">{paths}</g></svg>\n')

dxf(os.path.join(HERE, 'one_panel_cut.dxf'), [outer] + holes)
svg(os.path.join(HERE, 'one_panel_cut.svg'), [outer] + holes)
bw, bh = np.ptp(outer[:, 0]), np.ptp(outer[:, 1])
print(f'wrote one_panel_cut.dxf/.svg  panel {bw:.2f} x {bh:.2f} mm, {len(holes)} cut-outs')

# studio sticker (render only): the art clipped exactly, transparent in the window and cut-outs
st = os.path.join(HERE, '..', '..', '..', 'build', 'one_sticker'); os.makedirs(st, exist_ok=True)
tex = art.convert('RGBA'); tex.putalpha(cut); tex = tex.resize((W // 2, H // 2), Image.LANCZOS)
tex.save(os.path.join(st, 'sticker.png'))
json.dump({'w': X1 - X0, 'h': Y1 - Y0, 'cx': (X0 + X1) / 2, 'cy': (Y0 + Y1) / 2}, open(os.path.join(st, 'sticker.json'), 'w'))
