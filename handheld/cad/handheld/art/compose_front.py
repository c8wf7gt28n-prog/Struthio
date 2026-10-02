#!/usr/bin/env python3
# STRUTHIO HANDHELD · the front as the player sees it: the CAD front
# render (../renders/front.png), the front art sticker cut to its template, and
# a real frame from the C panel renderer in the screen opening, all placed by
# the model's own millimetre coordinates. Writes ../renders/struthio_front_art.png.
import os, re
from PIL import Image, ImageChops, ImageDraw
from shapely.geometry import Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
R = lambda *p: os.path.join(HERE, *p)
# the body's true extents, from the exported outline (svg y = -model y)
_ob = open(R('..', 'svg', 'body_outline.svg')).read()
_pts = [tuple(map(float, q.split(','))) for q in re.findall(r'-?[\d.]+,-?[\d.]+', re.search(r'<path d="([^"]*)"', _ob, re.S).group(1))]
BODY_W = max(x for x, y in _pts) - min(x for x, y in _pts)
BODY_TOP, BODY_BOT = -min(y for x, y in _pts), -max(y for x, y in _pts)
BODY_H = BODY_TOP - BODY_BOT
LCD_W, LCD_H, LCD_Y, OVERLAP = 48.96, 73.44, 13.78, 0.55
SCREEN = R('screen_frame.png')     # a real 320 x 480 frame from the C panel renderer (mortal trace, tick 2809)

render = Image.open(os.environ.get('FRONT') or R('..', 'renders', 'front.png')).convert('RGB')
bg = Image.new('RGB', render.size, render.getpixel((2, 2)))
x0, y0, x1, y1 = ImageChops.difference(render, bg).getbbox()          # the body outline
sx, sy = (x1 - x0) / BODY_W, (y1 - y0) / BODY_H
px = lambda x, y_model: (x0 + (x + BODY_W / 2) * sx, y0 + (BODY_TOP - y_model) * sy)

# the sticker: template outline minus its holes (svg y = -model y), art from the print PNG
svg = open(R('..', 'svg', 'struthio_sticker_cut.svg')).read()
d = re.search(r'<path d="([^"]*)"', svg, re.S).group(1)
rings = sorted((Polygon([tuple(map(float, p.split(','))) for p in re.findall(r'-?[\d.]+,-?[\d.]+', sub)]).buffer(0)
                for sub in re.split(r'M', d)[1:]), key=lambda p: -p.area)
outer, holes = rings[0], rings[1:]
mask = Image.new('L', render.size, 0)
dm = ImageDraw.Draw(mask)
dm.polygon([px(x, -y) for x, y in outer.exterior.coords], fill=255)
for h in holes: dm.polygon([px(x, -y) for x, y in h.exterior.coords], fill=0)
art = Image.open(R('sticker_front_print.png')).convert('RGB')
bx0, by0, bx1, by1 = outer.buffer(1.5, join_style=2).bounds           # the print PNG covers the bleed box
left, top = px(bx0, -by0)
art = art.resize((round((bx1 - bx0) * sx), round((by1 - by0) * sy)), Image.LANCZOS)
layer = Image.new('RGB', render.size); layer.paste(art, (round(left), round(top)))
out = Image.composite(layer, render, mask)

# the screen: the C renderer's frame over the active area, seen through the opening
scr = Image.open(SCREEN).convert('RGB')
a0, a1 = px(-LCD_W / 2, LCD_Y + LCD_H / 2), px(LCD_W / 2, LCD_Y - LCD_H / 2)
scr = scr.resize((round(a1[0] - a0[0]), round(a1[1] - a0[1])), Image.LANCZOS)
o0, o1 = px(-LCD_W / 2 + OVERLAP, LCD_Y + LCD_H / 2 - OVERLAP), px(LCD_W / 2 - OVERLAP, LCD_Y - LCD_H / 2 + OVERLAP)
win = Image.new('L', out.size, 0)
ImageDraw.Draw(win).rounded_rectangle([o0, o1], radius=1.6 * sx, fill=255)
layer = Image.new('RGB', out.size); layer.paste(scr, (round(a0[0]), round(a0[1])))
out = Image.composite(layer, out, win)
out = out.crop((max(0, x0 - 60), max(0, y0 - 60), min(out.width, x1 + 60), min(out.height, y1 + 60)))
out.save(R('..', 'renders', 'struthio_front_art.png'), optimize=True)
print('renders/struthio_front_art.png', out.size, f'{sx:.2f} px/mm')
