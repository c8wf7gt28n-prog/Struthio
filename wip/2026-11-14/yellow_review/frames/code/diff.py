# diff.py A_DIR B_DIR : per frame, count differing pixels and the bounding boxes of difference clusters (coarse grid)
import sys, os, re
import numpy as np
from PIL import Image
A, B = sys.argv[1], sys.argv[2]
def key(f): return re.sub(r'_(graphite|kasandra)_\d+x\d+\.png$', '', f)
bf = {key(f): f for f in os.listdir(B) if f.endswith('.png')}
for f in sorted(os.listdir(A)):
    if not f.endswith('.png') or key(f) not in bf: continue
    a = np.asarray(Image.open(os.path.join(A, f)).convert('RGB')).astype(int); b = np.asarray(Image.open(os.path.join(B, bf[key(f)])).convert('RGB')).astype(int)
    if a.shape != b.shape: print(f, 'SHAPE', a.shape, b.shape); continue
    d = np.abs(a - b).sum(2) > 0
    n = int(d.sum())
    if n == 0: print('%-45s 0' % key(f)); continue
    # coarse 32px cells
    H, W = d.shape; cells = []
    for y in range(0, H, 32):
        for x in range(0, W, 32):
            c = int(d[y:y+32, x:x+32].sum())
            if c: cells.append((x, y, c))
    ys, xs = np.nonzero(d)
    print('%-45s %6d px  bbox x%d-%d y%d-%d  cells %s' % (key(f), n, xs.min(), xs.max(), ys.min(), ys.max(), ' '.join('(%d,%d:%d)' % c for c in cells[:14]) + (' ...' if len(cells) > 14 else '')))
