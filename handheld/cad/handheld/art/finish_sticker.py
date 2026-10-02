#!/usr/bin/env python3
# STRUTHIO HANDHELD · makes the sticker print files print at true size: embeds
# 600 dpi in the PNGs (without it most programs assume 72 or 96 dpi and print
# it 6-8x too big) and writes an exact-size PDF, the safest file to print.
import os
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
DPI = 600
for name in ('sticker_front_print', 'sticker_front_proof'):
    png = os.path.join(HERE, name + '.png')
    im = Image.open(png).convert('RGB')
    dpi = DPI if name.endswith('print') else DPI // 2      # the proof is rendered at half resolution
    im.save(png, dpi=(dpi, dpi))
    if name.endswith('print'):
        im.save(os.path.join(HERE, name + '.pdf'), resolution=dpi)
        print(f'{name}: {im.width} x {im.height} px at {dpi} dpi = {im.width / dpi * 25.4:.1f} x {im.height / dpi * 25.4:.1f} mm (PNG + PDF)')
