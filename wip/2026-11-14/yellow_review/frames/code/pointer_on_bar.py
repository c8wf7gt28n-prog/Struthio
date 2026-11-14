# The desk's pointer (workbench/pointer.drawn) composited SourceOver, as the window system lays a cursor, on the burnt-yellow
# bar, the highlight fill, her ground and the cyan hover fill; count green pixels (HSL hue 70-170, sat >= 0.25).
import sys, os, colorsys
sys.path.insert(0, sys.argv[1]); OUT = sys.argv[2]
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QColor
from PySide6.QtCore import Qt
app = QGuiApplication([])
from workbench import boss_theme as t, pointer
print('appearance', t.APPEARANCE, 'READY', t.READY, 'glow', t.glow())
grounds = {'BAR': t.BAR, 'AMBER_SOFT': t.AMBER_SOFT, 'GROUND': t.GROUND, 'TEAL_SOFT': t.TEAL_SOFT}
for shape, sname in ((Qt.ArrowCursor, 'arrow'), (Qt.PointingHandCursor, 'hand')):
    for glow in (True, False):
        pix, hx, hy = pointer.drawn(shape, glow, 1.0)
        for gname, g in grounds.items():
            img = QImage(pix.width(), pix.height(), QImage.Format_RGB32);img.fill(QColor(g))
            p = QPainter(img);p.drawPixmap(0, 0, pix);p.end()
            n = 0;worst = None
            for y in range(img.height()):
                for x in range(img.width()):
                    c = QColor(img.pixel(x, y));h, l, s = colorsys.rgb_to_hls(c.redF(), c.greenF(), c.blueF())
                    if 70 <= h * 360 <= 170 and s >= 0.25 and 0.08 < l < 0.95:
                        n += 1
                        if worst is None or s > worst[1]:worst = ((c.red(), c.green(), c.blue()), s, h * 360)
            print('%-6s glow=%-5s on %-10s %s  green px %3d  %s' % (sname, glow, gname, g, n, ('most saturated %s sat %.2f hue %.0f' % worst) if worst else ''))
            if glow and gname in ('BAR', 'AMBER_SOFT') and sname == 'arrow':
                img.scaled(img.width() * 8, img.height() * 8, Qt.IgnoreAspectRatio, Qt.FastTransformation).save(os.path.join(OUT, 'pointer_%s_on_%s_x8.png' % (sname, gname)))
