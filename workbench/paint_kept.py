"""Graphite 1.0 F2b · Drawings kept as pictures: the left tree's paint under load.

PLAN_1.0.md, F2b: "Move the rest off the window's thread: ... the left tree's paint under load."

A painting cannot leave the window's thread (Qt paints there), so what can be kept is the work: on a desk that glows the
tree's words carry a faint light of their own, drawn as sixteen copies of each row's words around it (two radii, eight
directions) at every paint of every row. The tree repaints as it breathes and as her work moves the current row, and with
64 rows that was the window's longest wait in the Graphite and Kasandra looks once her other reads stopped waiting.

  halo(painter, box, font, words, align, colour, strength)   the same sixteen copies, drawn once into a picture for these
      words, this font, this box and this strength (in steps of 1/400, finer than the eye can tell), then laid down; the
      pictures are kept for the last MOST rows drawn.

Nothing here changes what is drawn, only that it is drawn once.
"""
from __future__ import annotations

import collections
import math

MOST = 600
STEPS = 400
DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1), (-0.7, -0.7), (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7))
RADII = ((2.4, 0.55), (1.3, 1.0))
PAD = 4
_kept = collections.OrderedDict()


def halo(painter, box, font, words, align, colour, strength):
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QPainter, QPixmap
    device = painter.device()
    dpr = device.devicePixelRatioF() if device is not None else 1.0
    step = round(max(0.0, strength) * STEPS)
    w, h = max(1, math.ceil(box.width())), max(1, math.ceil(box.height()))
    key = (words, font.key(), w, h, int(align), QColor(colour).rgba(), step, dpr)
    picture = _kept.get(key)
    if picture is None:
        picture = QPixmap(math.ceil((w + 2 * PAD) * dpr), math.ceil((h + 2 * PAD) * dpr))
        picture.setDevicePixelRatio(dpr);picture.fill(Qt.transparent)
        p = QPainter(picture)
        try:
            p.setFont(font);p.setRenderHint(QPainter.TextAntialiasing)
            ink = QColor(colour);place = QRectF(PAD, PAD, box.width(), box.height())
            for radius, share in RADII:
                ink.setAlphaF(min(0.3, step / STEPS * share));p.setPen(ink)
                for dx, dy in DIRECTIONS:p.drawText(place.translated(dx * radius, dy * radius), int(align), words)
        finally:
            p.end()
        _kept[key] = picture
        if len(_kept) > MOST:_kept.popitem(last=False)
    else:
        _kept.move_to_end(key)
    painter.drawPixmap(QPointF(box.x() - PAD, box.y() - PAD), picture)
