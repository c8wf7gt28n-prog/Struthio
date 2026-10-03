#!/usr/bin/env python3
"""STRUTHIO · tiles the design-lock views into one labelled sheet.   python3 lock_sheet.py LOCK_DIR OUT.png TITLE"""
import os, sys, re
from PIL import Image, ImageDraw, ImageFont
LABELS = {'01_front': 'Front', '02_back': 'Back', '03_left': 'Left side (power button)', '04_right': 'Right side',
          '05_top': 'Top end (USB-C)', '06_bottom': 'Bottom end', '07_front_left': 'Front, from the left',
          '08_front_right': 'Front, from the right', '09_front_low': 'Front, from below', '10_back_left': 'Back, from the left',
          '11_back_right': 'Back, from the right', '12_edge': 'Edge on', '13_inside': 'Inside: front shell + boards',
          '14_exploded': 'Exploded', '15_graphite': 'Colour: graphite', '16_ivory': 'Colour: ivory', '17_controls': 'Close-up: wings + rocker',
          '18_back_name': 'Close-up: the name on the back', '19_left_keys': 'Close-up: power, RST, BOOT'}
d, out, title = sys.argv[1], sys.argv[2], sys.argv[3]
fs = sorted(f for f in os.listdir(d) if re.match(r'\d\d_.*\.png$', f))
T, cols = 520, 4; rows = (len(fs) + cols - 1) // cols
S = Image.new('RGB', (cols * T, rows * (T + 40) + 70), (13, 22, 32)); dr = ImageDraw.Draw(S)
b = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30)
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
dr.text((20, 18), title, font=b, fill=(255, 168, 60))
for i, n in enumerate(fs):
    x, y = (i % cols) * T, 70 + (i // cols) * (T + 40)
    S.paste(Image.open(os.path.join(d, n)).convert('RGB').resize((T, T), Image.LANCZOS), (x, y))
    dr.text((x + 12, y + T + 8), f'{n[:2]}  {LABELS.get(n[:-4], n[3:-4])}', font=f, fill=(225, 230, 236))
S.save(out); print('wrote', out, S.size)
