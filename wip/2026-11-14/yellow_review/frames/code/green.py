# green.py DIR... : per full frame (not crops), pixels with HSL hue 70-170, sat>=0.25, light 0.08-0.92; and where
import sys, os
import numpy as np
from PIL import Image
def hsl(a):
    a = a / 255.0; mx = a.max(2); mn = a.min(2); l = (mx + mn) / 2; d = mx - mn
    s = np.where(d == 0, 0, d / (1 - np.abs(2 * l - 1) + 1e-9))
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.zeros_like(mx)
    m = d > 0
    hr = ((g - b) / (d + 1e-9)) % 6; hg = (b - r) / (d + 1e-9) + 2; hb = (r - g) / (d + 1e-9) + 4
    h = np.where(mx == r, hr, np.where(mx == g, hg, hb)) * 60
    return np.where(m, h, 0), s, l
for D in sys.argv[1:]:
    tot = 0
    for f in sorted(os.listdir(D)):
        if not f.endswith('.png') or 'x' in f.split('_')[1]: continue
        a = np.asarray(Image.open(os.path.join(D, f)).convert('RGB')).astype(float)
        h, s, l = hsl(a)
        g = (h >= 70) & (h <= 170) & (s >= 0.25) & (l > 0.08) & (l < 0.92)
        n = int(g.sum()); tot += n
        if n:
            ys, xs = np.nonzero(g)
            # cluster coarse
            cells = {}
            for y, x in zip(ys, xs): cells[(x // 64 * 64, y // 64 * 64)] = cells.get((x // 64 * 64, y // 64 * 64), 0) + 1
            top = sorted(cells.items(), key=lambda kv: -kv[1])[:6]
            print('%-44s %6d  %s' % (f, n, ' '.join('(%d,%d:%d)' % (k[0], k[1], v) for k, v in top)))
    print('TOTAL', D.split('/')[-1], tot)
