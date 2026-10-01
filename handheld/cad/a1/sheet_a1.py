#!/usr/bin/env python3
# STRUTHIO HANDHELD · joins the four A1 preview renders into one labelled sheet
# (renders/a083_sheet.png) for the manual.
from PIL import Image, ImageDraw, ImageFont
import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'renders'))
names = [('front', 'FRONT'), ('assembly', 'ASSEMBLY'), ('rear', 'REAR SHELL'), ('section', 'CENTRE SECTION')]
tiles = []
for n, label in names:
    im = Image.open(f'{n}.png').convert('RGB')
    bg = Image.new('RGB', im.size, im.getpixel((2, 2)))
    from PIL import ImageChops
    box = ImageChops.difference(im, bg).getbbox() or (0, 0, *im.size)
    im = im.crop((max(0, box[0] - 30), max(0, box[1] - 30), min(im.width, box[2] + 30), min(im.height, box[3] + 30)))
    im.thumbnail((620, 760))
    tile = Image.new('RGB', (640, 820), (248, 248, 246))
    tile.paste(im, ((640 - im.width) // 2, 40 + (760 - im.height) // 2))
    d = ImageDraw.Draw(tile)
    try: f = ImageFont.truetype('DejaVuSans-Bold.ttf', 26)
    except OSError: f = ImageFont.load_default()
    d.text((20, 10), label, fill=(23, 25, 28), font=f)
    tiles.append(tile)
sheet = Image.new('RGB', (640 * 4 + 30, 820), (255, 255, 255))
for k, t in enumerate(tiles): sheet.paste(t, (k * 650, 0))
sheet.save('a083_sheet.png', optimize=True)
print('renders/a083_sheet.png')
