#!/usr/bin/env python3
"""STRUTHIO · the ONE and the ONE SLIM from the side, same scale, labelled with their real thicknesses.

    python3 side_by_side.py RENDERS_SLIM_DIR      (reads one_side.png and slim_side.png, writes one_vs_slim_side.png)
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'cad', 'one'))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'cad', 'slim'))
import slim_cad                                    # sets one_cad up for the SLIM: read the ONE's depth first
ONE_DEPTH = 23.0                                   # one_cad.DEPTH before slim_cad.setup()
SLIM_DEPTH = slim_cad.DEPTH

def main(d):
    a, b = Image.open(os.path.join(d, 'one_side.png')).convert('RGB'), Image.open(os.path.join(d, 'slim_side.png')).convert('RGB')
    W, H = 1000, 1170
    out = Image.new('RGB', (W, H), (13, 22, 32))
    out.paste(a, (0, 1170 - 1100 - 30)); out.paste(b, (500, 1170 - 1100 - 30))
    dr = ImageDraw.Draw(out)
    f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
    s = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    dr.text((60, 20), f'ONE  {ONE_DEPTH:.1f} mm', font=f, fill=(240, 240, 240))
    dr.text((540, 20), f'ONE SLIM  {SLIM_DEPTH:.1f} mm', font=f, fill=(255, 168, 60))
    dr.text((20, H - 30), "from the 3D model, same scale, seen from the player's left", font=s, fill=(160, 170, 180))
    out.save(os.path.join(d, 'one_vs_slim_side.png'))
    print('wrote one_vs_slim_side.png')

if __name__ == '__main__':
    main(sys.argv[1])
