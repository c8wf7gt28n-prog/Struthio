#!/usr/bin/env python3
"""STRUTHIO · frames -> looping GIF (holds the first and last frame).   python3 make_gif.py FRAME_DIR OUT.gif"""
import glob, sys
from PIL import Image
frames = [Image.open(f).convert('RGB') for f in sorted(glob.glob(sys.argv[1] + '/frame_*.png'))]
seq = frames + frames[::-1][1:-1]
dur = [1400] + [90] * (len(frames) - 2) + [1600] + [70] * (len(frames) - 2)
pal = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f in seq]
pal[0].save(sys.argv[2], save_all=True, append_images=pal[1:], duration=dur[:len(pal)], loop=0, optimize=True)
print('wrote', sys.argv[2], len(pal), 'frames')
