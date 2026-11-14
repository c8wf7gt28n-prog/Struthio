"""Cut the owner's kp emblem (14 November 2026: "I attached a new kp icon/logo") from its flat navy ground, for the Apps
button and Kasandra's window icon. Build time only: the program shows the files this writes and never runs this.

The owner's file (branding/kasandra/kp_emblem_source.png) is the emblem drawn on a flat ground G = #070221 with four inks:
cream (the letters kp), two pinks (the ostrich) and violet (the trace from the p's stem). Each pixel C is read as one ink F
laid over the ground at some cover a: a = clamp((C - G).(F - G) / |F - G|^2), the ink that explains C with the least
residual wins, and the pixel becomes that ink at that cover, so an edge keeps the ink's own colour and never carries the
navy with it onto another ground. A pixel no single ink explains (a residual over 40, where two inks meet) is kept as it is,
opaque.

    kp_emblem.png         the cut, trimmed to the ink and 8 px round it (737 x 482): the master
    kp_emblem_small.png   the same with the thin pink and violet strokes thickened (a 9 x 9 dilation) and the letters
                          laid back over them exactly: what a 38 px button can still show
    kp_emblem_38.png      the Apps button at 1x (58 x 38), from the small cut
    kp_emblem_76.png      the Apps button at 2x (116 x 76), from the master
    kp_tile.png           the window icon, 256 px: the master on its own navy in a rounded square
    kp_tile_letters.png   the window icon at 16 and 24 px, 64 px: the tile with the letters only

Run with numpy and Pillow (resizing is Lanczos on premultiplied colour, as Pillow does for RGBA):

    python3 -I tools/cut_kp_emblem.py [program root]
"""
import hashlib
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SOURCE_SHA = '94d7bfb3932fd1cdb9c1f499fe4eee011d9e0404ff5cfa071d9a7dbb2eb3afaa'
GROUND = np.array([7, 2, 33.0])
CREAM, PINK, PINK_HOT, VIOLET = (254, 241, 227), (242, 62, 107), (253, 54, 108), (118, 53, 254)
INKS = np.array([CREAM, PINK, PINK_HOT, VIOLET], dtype=np.float64)
PAD = 8


def unmix(rgb):
    """(colour, cover, ink index, mixed) for every pixel: index into INKS, -1 for the ground, 4 for a kept mix."""
    D = rgb - GROUND
    cover = np.zeros(rgb.shape[:2]);residual = np.full(rgb.shape[:2], 1e9);ink = np.full(rgb.shape[:2], -1);colour = np.zeros(rgb.shape)
    for index, F in enumerate(INKS):
        v = F - GROUND;a = np.clip((D @ v) / (v @ v), 0, 1)
        r = np.sqrt(((rgb - (GROUND + a[..., None] * v)) ** 2).sum(-1))
        better = r < residual
        cover[better] = a[better];residual[better] = r[better];colour[better] = F;ink[better] = index
    mixed = (residual > 40) & (np.sqrt((D ** 2).sum(-1)) > 40)
    cover[mixed] = 1.0;colour[mixed] = rgb[mixed];ink[mixed] = 4
    cover[cover < 0.04] = 0.0;cover[cover > 0.97] = 1.0
    ink[cover == 0] = -1
    return colour, cover, ink


def rgba(colour, cover):
    return Image.fromarray(np.dstack([colour, cover * 255]).round().clip(0, 255).astype(np.uint8), 'RGBA')


def tile(art, side, radius, share):
    """art on the emblem's own navy, in a rounded square `side` px with corners of `radius`, `share` of its width."""
    big = side * 4
    mask = Image.new('L', (big, big), 0);ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius * 4, fill=255)
    mask = mask.resize((side, side), Image.LANCZOS)
    out = Image.new('RGBA', (side, side), tuple(int(c) for c in GROUND) + (255,))
    width = round(side * share);height = round(width * art.size[1] / art.size[0])
    out.alpha_composite(art.resize((width, height), Image.LANCZOS), ((side - width) // 2, (side - height) // 2))
    out.putalpha(mask)
    return out


def main(root):
    folder = Path(root) / 'branding' / 'kasandra'
    source = folder / 'kp_emblem_source.png'
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise SystemExit('kp_emblem_source.png is not the owner\'s file; nothing written')
    rgb = np.asarray(Image.open(source).convert('RGB')).astype(np.float64)
    colour, cover, ink = unmix(rgb)
    ys, xs = np.where(cover > 0)
    box = (int(xs.min()) - PAD, int(ys.min()) - PAD, int(xs.max()) + 1 + PAD, int(ys.max()) + 1 + PAD)
    master = rgba(colour, cover).crop(box)
    # the small cut: the ostrich's and the trace's thin strokes made fatter, each in its own ink; the letters (and the
    # kept mixes) laid back over them as they are
    small = Image.new('RGBA', master.size, (0, 0, 0, 0))
    crop = lambda a:a[box[1]:box[3], box[0]:box[2]]
    for indexes, F in (((3,), VIOLET), ((1, 2), PINK)):
        alpha = Image.fromarray((crop(np.where(np.isin(ink, indexes), cover, 0.0)) * 255).round().astype(np.uint8), 'L')
        layer = Image.new('RGBA', master.size, F + (0,));layer.putalpha(alpha.filter(ImageFilter.MaxFilter(9)))
        small.alpha_composite(layer)
    letters = rgba(crop(colour), crop(np.where(np.isin(ink, (0, 4)), cover, 0.0)))
    small.alpha_composite(letters)
    master.save(folder / 'kp_emblem.png', optimize=True)
    small.save(folder / 'kp_emblem_small.png', optimize=True)
    small.resize((58, 38), Image.LANCZOS).save(folder / 'kp_emblem_38.png', optimize=True)
    master.resize((116, 76), Image.LANCZOS).save(folder / 'kp_emblem_76.png', optimize=True)
    tile(master, 256, 56, 0.84).save(folder / 'kp_tile.png', optimize=True)
    only = rgba(crop(colour), crop(np.where(ink == 0, cover, 0.0)))
    only = only.crop(only.getbbox())
    tile(only, 64, 14, 0.78).save(folder / 'kp_tile_letters.png', optimize=True)
    print('source rect', (box[0], box[1], box[2] - box[0], box[3] - box[1]), 'mixed pixels', int((ink == 4).sum()))
    for name in ('kp_emblem.png', 'kp_emblem_small.png', 'kp_emblem_38.png', 'kp_emblem_76.png', 'kp_tile.png', 'kp_tile_letters.png'):
        print('%s · SHA-256 %s' % (name, hashlib.sha256((folder / name).read_bytes()).hexdigest()))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
