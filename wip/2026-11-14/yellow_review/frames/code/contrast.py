# For each full frame: regions of the bar fill (#e2a72e) and of the highlight fill (#5a3f0c): the ink inside them (the pixel
# farthest in luminance from the fill, in rows that are mostly fill) and its contrast with the fill; plus hue range of the
# burnt-yellow family (hue 20-60, sat>=0.4).
import sys, os, json
import numpy as np
from PIL import Image
def lum(c):
    c = np.asarray(c, float) / 255; c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]
def cr(a, b):
    la, lb = lum(a), lum(b); hi, lo = max(la, lb), min(la, lb); return (hi + 0.05) / (lo + 0.05)
for Dd in sys.argv[1:]:
    out = {}
    for f in sorted(os.listdir(Dd)):
        if not f.endswith('.png') or 'x' in f.split('_')[1]: continue
        a = np.asarray(Image.open(os.path.join(Dd, f)).convert('RGB')).astype(int)
        res = []
        for name, fill in (('bar', (226, 167, 46)), ('hl', (90, 63, 12))):
            m = (a == fill).all(2)
            if m.sum() < 200: continue
            ys, xs = np.nonzero(m)
            # rows where fill is at least 40 px wide; inside the fill's x-span on those rows, take non-fill pixels
            rows = np.unique(ys); best = None; worst_text = None; cnt = 0
            for y in rows:
                xr = xs[ys == y]
                if len(xr) < 40: continue
                seg = a[y, xr.min():xr.max() + 1]
                nf = seg[~(seg == fill).all(1)]
                if len(nf) == 0: continue
                d = np.abs(lum(nf) - lum(np.array(fill)))
                p = nf[d.argmax()]; c = cr(p, fill); cnt += 1
                if best is None or c > best[0]: best = (c, tuple(int(v) for v in p))
            if best: res.append('%s ink %s %.2f:1' % (name, best[1], best[0]))
        if res: print('%-46s %s' % (f, ' | '.join(res)))
