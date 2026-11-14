# how long one paint of the Field takes, whole and for a small region
import time
from PySide6.QtCore import QRect
w.a_field.trigger(); settle(); v = w.field_page.view
def timed(region=None, n=40):
    t0 = time.perf_counter()
    for _ in range(n):
        if region is None: v.repaint()
        else: v.repaint(region)
    return (time.perf_counter() - t0) * 1000.0 / n
print('whole paint ms: %.2f' % timed(), '| a 300x300 region ms: %.2f' % timed(QRect(600, 500, 300, 300)), '| size', v.width(), v.height(), '| things', len(v.field.objects))
