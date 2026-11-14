import sys, hashlib
import numpy as np
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
print('src sha', hashlib.sha256(open(src,'rb').read()).hexdigest())
print('out sha', hashlib.sha256(open(out,'rb').read()).hexdigest())
s = np.asarray(Image.open(src).convert('RGBA')); o = np.asarray(Image.open(out).convert('RGBA'))
print('src', s.shape, 'out', o.shape)
m = s[..., 3] >= 200; ys, xs = np.nonzero(m)
print('alpha>=200 bbox x%d-%d y%d-%d' % (xs.min(), xs.max(), ys.min(), ys.max()))
crop = s[ys.min():ys.max()+1, xs.min():xs.max()+1].copy(); cm = crop[..., 3] >= 200
exp = np.where(cm[..., None], crop, 0)
print('out == expected clean', exp.shape == o.shape and bool((exp == o).all()))
if exp.shape == o.shape:
    d = (exp != o).any(2); print('differing px', int(d.sum()))
print('out alpha values', np.unique(o[..., 3])[:10], '... count of 0<a<200:', int(((o[...,3] > 0) & (o[...,3] < 200)).sum()))
# alpha 200-254 edge pixels: their colour
edge = (o[..., 3] >= 200) & (o[..., 3] < 255); print('edge px (200..254)', int(edge.sum()), 'of opaque', int((o[...,3]==255).sum()))
