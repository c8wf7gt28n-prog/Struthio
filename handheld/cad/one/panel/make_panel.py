#!/usr/bin/env python3
"""STRUTHIO ONE · the face panel: one 1.0 mm clear acrylic piece, laser-cut, with the art
printed on its BACK. It is the lens over the screen, the front art and the key wells in one.

The art is the game's own (arcade/assets/art): the STRUTHIO logo and stripes and the yellow/red picture
frame from the box art, then the game's scene under the screen (islands and moon over the stars, the city
skyline, the grid) with orange/blue rings round the wing buttons and the dart bay and a BOTH badge.
The screen window is left unprinted (clear).

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
from PIL import Image, ImageChops, ImageDraw, ImageFilter

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

# controller background, behind the buttons (BG below; PANEL_BG=grid|rain|islands|stripes overrides it)
BG = os.environ.get('PANEL_BG', 'scene')
rng = np.random.default_rng(7)                                   # fixed seed: the same art every run
BG_W = 88.0
s = BG_W / rear.width                                            # mm per px: the game background drawn 88 mm wide

def stars_layer():
    """the game's star field (the sky part of background-rear), no skyline"""
    sky = rear.crop((0, 420, rear.width, 1400))                  # below the moon
    sc = sky.resize((round(L(BG_W)), round(L(sky.height * s))), Image.LANCZOS)
    lay = Image.new('RGB', (W, H), INK_BLACK)
    for top in (-22.0, -22.0 - sky.height * s):
        lay.paste(sc, tuple(round(v) for v in px(-BG_W / 2, top)))
    return lay

def bg_grid():
    HORIZON_PX, HORIZON_Y = 1690, -40.0
    sc = rear.resize((round(L(BG_W)), round(L(rear.height * s))), Image.LANCZOS)
    lay = Image.new('RGB', (W, H), INK_BLACK); lay.paste(sc, tuple(round(v) for v in px(-BG_W / 2, HORIZON_Y + HORIZON_PX * s)))
    return lay

def bg_rain():
    """black with rising pixel streaks in the buttons' blue and orange (the BOTH badge's style)"""
    lay = Image.new('RGB', (W, H), INK_BLACK); dl = ImageDraw.Draw(lay)
    q = 0.38                                                     # one pixel, mm
    cols = [(36, 104, 214)] * 5 + [(90, 170, 255)] * 3 + [(246, 150, 32)] * 2
    for _ in range(120):
        x = round(rng.uniform(-37, 37) / q) * q
        y_top = rng.uniform(-70, -30); n = int(rng.integers(3, 16)); c = cols[int(rng.integers(len(cols)))]
        for k in range(n):
            if rng.random() < 0.28: continue                     # broken, dashed streaks
            y = y_top - k * q * 1.6; fade = 1 - k / (n + 1)
            col = tuple(int(v * (0.35 + 0.65 * fade)) for v in c)
            dl.rectangle([*px(x, y), *px(x + q * 0.8, y - q)], fill=col)
    return lay

def bg_islands():
    """the star field with the game's own floating islands drifting round the buttons"""
    lay = stars_layer()
    sheet = Image.open(os.path.join(ART, 'islands.webp')).convert('RGBA')
    def put(box, cx, cy, w):
        im = sheet.crop(box); h = w * im.height / im.width
        im = im.resize((round(L(w)), round(L(h))), Image.LANCZOS)
        x, y = px(cx - w / 2, cy + h / 2); lay.paste(im, (round(x), round(y)), im)
    put((0, 240, 705, 480), 0, -64.5, 70.0)                     # the long island along the bottom edge
    put((1200, 0, 1440, 240), -31.0, -37.0, 9.0)
    put((1060, 290, 1220, 400), 30.5, -36.5, 8.0)
    put((1550, 290, 1700, 400), -31.5, -54.0, 6.5)
    put((1400, 290, 1530, 400), 31.5, -54.5, 6.0)
    return lay

def bg_stripes():
    """stars, with the box art's stripes along the bottom: the third stripe band of the face"""
    lay = stars_layer()
    st = hero.crop((22, 140, 112, 296)).resize((round(L(BG_W)), round(L(5.4))), Image.LANCZOS)
    lay.paste(st, tuple(round(v) for v in px(-BG_W / 2, -60.6)))
    dl = ImageDraw.Draw(lay)
    dl.rectangle([*px(-BG_W / 2, -66.0), *px(BG_W / 2, -80)], fill=INK_BLACK)
    return lay

def bg_scene():
    """the game itself under the screen: floating islands and the moon over the stars, a low city skyline on the
    horizon behind the buttons, the glowing grid and its reflections below (all from the game's own art)"""
    lay = stars_layer()
    sw = 74.0; ss = sw / rear.width; HZ = -40.5                  # drawn 74 mm wide, horizon at y -40.5
    grid = rear.crop((0, 1672, rear.width, rear.height))
    grid = grid.resize((round(L(sw)), round(L(grid.height * ss))), Image.LANCZOS)
    lay.paste(grid, tuple(round(v) for v in px(-sw / 2, HZ)))
    HZ_PX = 1672                                                 # the horizon row in background-rear
    sky = rear.crop((0, 1530, rear.width, HZ_PX))                # the side spires, kept low: 6.5 mm
    sky = sky.resize((round(L(sw)), round(L(6.5))), Image.LANCZOS)
    hole = Image.new('L', sky.size, 255)                         # minus the centre, where the castle stands whole
    ImageDraw.Draw(hole).rectangle([sky.width // 2 - L(5.5), 0, sky.width // 2 + L(5.5), sky.height], fill=0)
    sky = Image.composite(sky, Image.new('RGB', sky.size, (0, 0, 0)), hole.filter(ImageFilter.GaussianBlur(L(1.2))))
    x, y = px(-sw / 2, HZ + 6.5); box = (round(x), round(y), round(x) + sky.width, round(y) + sky.height)
    lay.paste(ImageChops.lighter(lay.crop(box), sky), box[:2])
    ch = 15.0; cw = ch * 190 / (HZ_PX - 1290) * 1.5             # the central castle: whole, tip just under the frame
    castle = rear.crop((289, 1290, 479, HZ_PX)).resize((round(L(cw)), round(L(ch))), Image.LANCZOS)
    fade = Image.new('L', castle.size, 0)
    ImageDraw.Draw(fade).rectangle([L(1.6), 0, castle.width - L(1.6), castle.height], fill=255)
    castle = Image.composite(castle, Image.new('RGB', castle.size, (0, 0, 0)), fade.filter(ImageFilter.GaussianBlur(L(0.8))))
    x, y = px(-cw / 2, HZ + ch); box = (round(x), round(y), round(x) + castle.width, round(y) + castle.height)
    lay.paste(ImageChops.lighter(lay.crop(box), castle), box[:2])
    moon = rear.crop((470, 110, 750, 390))
    mw = 6.4; moon = moon.resize((round(L(mw)), round(L(mw))), Image.LANCZOS)
    x, y = px(9.5 - mw / 2, -29.0 + mw / 2)
    box = (round(x), round(y), round(x) + moon.width, round(y) + moon.height)
    lay.paste(ImageChops.lighter(lay.crop(box), moon), box[:2])
    sheet = Image.open(os.path.join(ART, 'islands.webp')).convert('RGBA')
    for (sx, sy, sw_, sh), cx, cy, w in (((661, 0, 173, 219), -24.0, -29.6, 6.0), ((168, 0, 160, 205), -6.5, -30.4, 4.6),
                                         ((1388, 0, 268, 262), 24.5, -29.4, 6.6)):
        im = sheet.crop((sx, sy, sx + sw_, sy + sh)); h = w * im.height / im.width
        im = im.resize((round(L(w)), round(L(h))), Image.LANCZOS)
        x, y = px(cx - w / 2, cy + h / 2); lay.paste(im, (round(x), round(y)), im)
    return lay

SHOW_STRIP = os.environ.get('PANEL_STRIP') == '1'                # the HOME VIDEO GAME strip (off: the scene starts at the frame)
FADE_Y = -32.6 if SHOW_STRIP else o.BCY - WIN_H / 2 - FRAME[-1][0] - 0.3
lay = {'scene': bg_scene, 'grid': bg_grid, 'rain': bg_rain, 'islands': bg_islands, 'stripes': bg_stripes}[BG]()
ramp = Image.new('L', (1, H))
for j in range(H):
    y = Y1 - j / PX
    ramp.putpixel((0, j), int(255 * np.clip(((FADE_Y) - y) / 1.6, 0, 1)))
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
if SHOW_STRIP:
  TEXT = hero.crop((165, 1368, 776, 1493)); text_h = 5.6; text_w = text_h * TEXT.width / TEXT.height
  text_cy = win_bot - frame_out - 0.8 - text_h / 2
  TS_L, TS_R = hero.crop((22, 1368, 150, 1493)), hero.crop((792, 1368, 920, 1493))
  seg = half_w + BLEED - text_w / 2 + 0.5
  paste_fit(art, TS_L, -half_w - BLEED + seg / 2, text_cy, w_mm=seg, h_mm=text_h)
  paste_fit(art, TS_R, half_w + BLEED - seg / 2, text_cy, w_mm=seg, h_mm=text_h)
  paste_fit(art, TEXT, 0, text_cy, h_mm=text_h, feather=0.4)

# the wing buttons: an orange ring and a thin blue ring round each well, ticks on the outer side
ORANGE, BLUE, SKY = (246, 150, 32), (36, 104, 214), (90, 170, 255)
d = ImageDraw.Draw(art)
def ring(cx, cy, r0, r1, col):
    d.ellipse([*px(cx - r1, cy + r1), *px(cx + r1, cy - r1)], fill=col)
    d.ellipse([*px(cx - r0, cy + r0), *px(cx + r0, cy - r0)], fill=INK_BLACK)
def bar(x0, y0, x1, y1, col):
    a, b = px(x0, y1), px(x1, y0); d.rectangle([a, b], fill=col)
rw = o.BTN_D / 2 + o.WELL                                        # the well edge (the acrylic's cut)
ty = o.WING_Y + 3.4 - 4.6 - 1.0                                  # BOTH baseline (top of the word)
halo = Image.new('L', (W, H), 0); dh = ImageDraw.Draw(halo)      # dark field behind the rings and the BOTH badge
for sd in (-1, 1):
    cx, cy = sd * o.WING_X, o.WING_Y; R = rw + 2.2
    dh.ellipse([*px(cx - R, cy + R), *px(cx + R, cy - R)], fill=235)
dh.rounded_rectangle([*px(-5.2, o.WING_Y + 7.4), *px(5.2, ty - 2.3 - 2.4)], radius=L(1.5), fill=235)
halo = halo.filter(ImageFilter.GaussianBlur(L(1.2)))
art = Image.composite(Image.new('RGB', (W, H), INK_BLACK), art, halo)
d = ImageDraw.Draw(art)
for sd in (-1, 1):
    cx, cy = sd * o.WING_X, o.WING_Y
    ring(cx, cy, rw + 1.35, rw + 1.6, BLUE)
    ring(cx, cy, rw + 0.35, rw + 1.1, ORANGE)
    for k, (t0, t1) in enumerate(((rw + 1.9, rw + 2.6), (rw + 2.9, rw + 3.2))):              # outer ticks
        x0, x1 = (cx + sd * t0, cx + sd * t1) if sd > 0 else (cx + sd * t1, cx + sd * t0)
        bar(x0, cy - 0.22, x1, cy + 0.22, ORANGE if k == 0 else BLUE)
    for yy in (-0.9, 0.9):
        x0, x1 = sorted((cx + sd * (rw + 1.9), cx + sd * (rw + 2.4)))
        bar(x0, cy + yy - 0.15, x1, cy + yy + 0.15, BLUE)
# the dart rocker's bay: the same orange and blue outline, following the cut
def bay(t):
    return o.rocker2d(o.WELL + t) + o.rrect(o.ROCKER_W + 2 * (o.WELL + t), 40.0, 0.0, 0, o.ROCKER_Y - 20.0)
def fill(cs, col):
    for pg in cs.to_polygons(): d.polygon([px(x, y) for x, y in pg], fill=col)
fill(bay(1.6), BLUE); fill(bay(1.35), INK_BLACK); fill(bay(1.1), ORANGE); fill(bay(0.35), INK_BLACK)

# BOTH: straight up. A pixel arrow with streaks, the word, a dashed rule
ax, ay = 0.0, o.WING_Y + 3.4
head = [(-2.6, 0.0), (0.0, 3.2), (2.6, 0.0), (0.7, 0.55), (0.7, -4.6), (-0.7, -4.6), (-0.7, 0.55)]
d.polygon([px(ax + x, ay + y) for x, y in head], fill=BLUE)
d.polygon([px(ax + x * 0.62, ay + 0.35 + y * 0.62) for x, y in head[:3]], fill=SKY)
for x, h in ((-1.6, 2.4), (-2.3, 1.4), (1.6, 2.4), (2.3, 1.4), (-1.15, 3.4), (1.15, 3.4)):   # streaks under the head
    bar(ax + x - 0.12, ay - 0.4 - h, ax + x + 0.12, ay - 0.4, BLUE if abs(x) > 2 else SKY)
from PIL import ImageFont
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
cap = 2.3                                                        # cap height, mm
f = ImageFont.truetype(FONT, round(L(cap) / 0.73))
tw = d.textlength('BOTH', font=f)
ty = ay - 4.6 - 1.0
x0, y0 = px(ax, ty)
d.text((x0 - tw / 2, y0), 'BOTH', font=f, fill=ORANGE)
for x0 in np.arange(-5.4, 5.4, 1.2):
    bar(x0, ty - cap - 1.25, x0 + 0.8, ty - cap - 1.0, ORANGE)
bar(-0.12, ty - cap - 1.9, 0.12, ty - cap - 0.4, SKY)

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
    if os.environ.get('PANEL_PREVIEW'): return                  # preview runs never touch the deliverables
    if os.environ.get('PANEL_PREVIEW'): return                  # preview runs never touch the deliverables
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
if os.environ.get('PANEL_PREVIEW'):
    proof.crop((0, int(H * 0.62), W, H)).resize((W // 3, (H - int(H * 0.62)) // 3), Image.LANCZOS).save(os.environ['PANEL_PREVIEW']); sys.exit(0)
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
