# sheet.py OUT LABEL:FILE ... : stack images vertically with labels
import sys
from PIL import Image, ImageDraw
out = sys.argv[1]; items = [a.split('=', 1) for a in sys.argv[2:]]
ims = [(l, Image.open(f).convert('RGB')) for l, f in items]
W = max(i.width for _, i in ims); H = sum(i.height + 18 for _, i in ims)
sheet = Image.new('RGB', (W, H), (40, 40, 40)); d = ImageDraw.Draw(sheet); y = 0
for l, i in ims:
    d.text((4, y + 3), l, fill=(255, 255, 255)); y += 18; sheet.paste(i, (0, y)); y += i.height
sheet.save(out); print(out, sheet.size)
