import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'pointer.py', [('''    def eventFilter(self, watched, event):
        kind = event.type()
        if kind in (QEvent.Polish, QEvent.Show, QEvent.CursorChange) and isinstance(watched, QWidget):
''', '''    def eventFilter(self, watched, event):
        kind = event.type()
        if kind == QEvent.Show and isinstance(watched, QWidget) and watched.isWindow() and hasattr(watched, 'session'):
            try:                        # the desk's own window says which art it wears: the Clean desk has no glow
                self.restyle(watched.session.state.get('desk_art', 'illustrated') != 'clean')
            except Exception:  # noqa: BLE001 - a window without that state keeps the glow
                pass
        if kind in (QEvent.Polish, QEvent.Show, QEvent.CursorChange) and isinstance(watched, QWidget):
''')])
edit(W + 'qt_app.py', [('''    from .theme2 import install as relight_older_panels
    relight_older_panels(app)
    return app
''', '''    from .theme2 import install as relight_older_panels
    relight_older_panels(app)
    from .pointer import install as green_pointer      # the pointer in the desk's green, with its glow
    green_pointer(app)
    return app
''')])
edit(W + 'boss_qt.py', [('''    host.session.state['desk_art'] = mode;host.session.save()
''', '''    host.session.state['desk_art'] = mode;host.session.save()
    from . import pointer
    pointer.restyle(mode != 'clean')           # the pointer keeps its green on the Clean desk and drops its glow
''')])
edit(W + 'field_qt.py', [
# what is current glows a little; the Clean desk has no glow
('''    def _mark(self, p, box, state, colour):
        """One mark per state, different in shape and not only in hue: settled a filled square, recheck half filled, open
        hollow, held crossed, waiting a dot inside, failed a cross, cannot be read or reached a dash."""
        p.save();pen = QPen(colour, 1.5);p.setPen(pen);p.setBrush(Qt.NoBrush)
        if state in SETTLED:
            p.setPen(Qt.NoPen);p.setBrush(colour);p.drawRect(box)
''', '''    def _halo(self, p, rect, colour, strength=1.0):
        """A soft glow around a rectangle: three outlines, the widest the faintest. Still, like everything on this surface.
        The Clean desk has none."""
        if not self.texture:return
        s = self.scale();p.save();p.setBrush(Qt.NoBrush)
        for grow, width, alpha in ((7.0, 8.0, 0.05), (4.0, 5.0, 0.09), (1.5, 2.5, 0.17)):
            p.setPen(QPen(ink(colour, min(1.0, alpha * strength)), width * s));p.drawRect(rect.adjusted(-grow * s, -grow * s, grow * s, grow * s))
        p.restore()

    def _mark(self, p, box, state, colour):
        """One mark per state, different in shape and not only in hue: settled a filled square, recheck half filled, open
        hollow, held crossed, waiting a dot inside, failed a cross, cannot be read or reached a dash. What is settled glows
        a little in the desk's green: it is what is live."""
        p.save();pen = QPen(colour, 1.5);p.setPen(pen);p.setBrush(Qt.NoBrush)
        if state in SETTLED:
            if self.texture:
                glow = QRadialGradient(box.center(), box.width() * 2.6);inner = QColor(colour);inner.setAlphaF(min(1.0, colour.alphaF()) * 0.42)
                outer = QColor(colour);outer.setAlphaF(0.0);glow.setColorAt(0.0, inner);glow.setColorAt(1.0, outer)
                p.setPen(Qt.NoPen);p.setBrush(glow);p.drawEllipse(box.center(), box.width() * 2.6, box.width() * 2.6)
            p.setPen(Qt.NoPen);p.setBrush(colour);p.drawRect(box)
'''),
# the sheet under the pointer glows green: the pointer is green, and what it touches answers
('''        p.setBrush(QColor((t.CARD, t.CARD, t.PANEL, t.GROUND)[depth]))       # a sheet recedes by its ground and its edge; its words stay readable
        edge = t.AMBER_EDGE if selected and focus else (t.LINE_STRONG if depth <= 1 else t.LINE)
        p.setPen(QPen(ink(edge, 1.0 if selected else edge_keep + 0.1), 2 if selected else 1));p.drawRect(r)
''', '''        touched = bool(self._hover) and obj.id == self._hover and not selected      # under the pointer: it answers in the pointer's green
        if touched:self._halo(p, r, t.READY, 1.5)
        p.setBrush(QColor((t.CARD, t.CARD, t.PANEL, t.GROUND)[depth]))       # a sheet recedes by its ground and its edge; its words stay readable
        edge = t.AMBER_EDGE if selected and focus else t.READY if touched else (t.LINE_STRONG if depth <= 1 else t.LINE)
        p.setPen(QPen(ink(edge, 1.0 if selected else 0.85 if touched else edge_keep + 0.1), 2 if selected else 1));p.drawRect(r)
'''),
# the wires glow: a live wire carries a faint green light, brighter where it touches what is selected or under the pointer
('''            colour = t.AMBER_EDGE if link.stale else (t.TEXT if touching else t.TEAL_EDGE)
            pen = QPen(ink(colour, strength * (0.95 if link.stale or touching else 0.8)), 1.8 if touching or link.stale else 1.0)
            if link.stale:pen.setStyle(Qt.CustomDashLine);pen.setDashPattern([5, 4])
            p.setBrush(Qt.NoBrush);p.setPen(pen);p.drawPath(path)
''', '''            hovered = bool(self._hover) and self._hover in (link.source, link.target) and self.field.selected not in (link.source, link.target)
            colour = t.AMBER_EDGE if link.stale else t.READY if hovered else (t.TEXT if touching else t.TEAL_EDGE)
            if self.texture and not link.stale:      # the light a live wire carries: under the line, wide and faint
                for width, alpha in ((7.0, 0.035), (4.0, 0.07)):
                    p.setBrush(Qt.NoBrush);p.setPen(QPen(ink(t.READY, alpha * (2.6 if touching else 1.0) * (1.0 if near <= 1 or touching else 0.6)), width * s));p.drawPath(path)
            pen = QPen(ink(colour, strength * (0.95 if link.stale or touching else 0.8)), 1.8 if touching or link.stale else 1.0)
            if link.stale:pen.setStyle(Qt.CustomDashLine);pen.setDashPattern([5, 4])
            p.setBrush(Qt.NoBrush);p.setPen(pen);p.drawPath(path)
'''),
# staC is said in green wherever it is said: the rail, the foot, a page's own line
('''            y += fm.height();p.setPen(QColor(t.QUIET if line.startswith(('|', ' ')) else t.TEXT))
            p.drawText(QPointF(x, y - fm.descent()), fm.elidedText(line, Qt.ElideRight, inner_w))
''', '''            y += fm.height();p.setPen(QColor(t.TEAL_EDGE if line.startswith(('|', ' ')) else t.TEAL_TEXT))      # staC is green wherever it is said
            p.drawText(QPointF(x, y - fm.descent()), fm.elidedText(line, Qt.ElideRight, inner_w))
'''),
('''        if code:
            p.setPen(QColor(t.AMBER_TEXT));p.drawText(QPointF(self.width() - x - code_w, top + h - 14 * s), fm3.elidedText(code, Qt.ElideRight, code_w))
''', '''        if code:
            p.setPen(QColor(t.TEAL_TEXT));p.drawText(QPointF(self.width() - x - code_w, top + h - 14 * s), fm3.elidedText(code, Qt.ElideRight, code_w))
'''),
('''        if code:
            p.setPen(QColor(t.FAINT));p.drawText(QPointF(r.left() + pad, base - fm_foot.height() - 6 * s), fm_foot.elidedText('staC  ' + code, Qt.ElideRight, r.width() - 2 * pad))
''', '''        if code:
            p.setPen(QColor(t.TEAL_EDGE));p.drawText(QPointF(r.left() + pad, base - fm_foot.height() - 6 * s), fm_foot.elidedText('staC  ' + code, Qt.ElideRight, r.width() - 2 * pad))
'''),
# on a page for reading, what holds is said in green
('''        for style, text in read['lines']:
            if style == 'h':
                at += (16 * s if rows else 2 * s)
                rows.append((at + fm_head.ascent(), 0.0, head_font, t.AMBER_TEXT, str(text).upper()));at += fm_head.height() + 6 * s
''', '''        calm = False                           # under a heading that says something holds (or that nothing waits), the marks are green
        for style, text in read['lines']:
            if style == 'h':
                calm = str(text).strip().lower().startswith(('holds', 'nothing'))
                at += (16 * s if rows else 2 * s)
                rows.append((at + fm_head.ascent(), 0.0, head_font, t.READY if calm else t.AMBER_TEXT, str(text).upper()));at += fm_head.height() + 6 * s
'''),
('''                    if style == 'b' and index == 0:rows.append((at + fm.ascent(), 0.0, font, t.AMBER_EDGE, '·'))
''', '''                    if style == 'b' and index == 0:rows.append((at + fm.ascent(), 0.0, font, t.READY if calm else t.AMBER_EDGE, '·'))
'''),
# a key under the pointer answers in green
('''            else:
                total = fm.horizontalAdvance(str(item))
                if x + total > end:break
                p.setPen(QColor(colour));p.drawText(QPointF(x, base), str(item))
                if found is not None:
                    self._hot.append((QRectF(x - 4 * s, base - fm.ascent() - 4 * s, total + 8 * s, fm.height() + 8 * s), found[0], found[1], words[:1].upper() + words[1:] + ' (%s)' % label.strip()))
''', '''            else:
                total = fm.horizontalAdvance(str(item))
                if x + total > end:break
                spot = QRectF(x - 4 * s, base - fm.ascent() - 4 * s, total + 8 * s, fm.height() + 8 * s)
                p.setPen(QColor(t.READY if found is not None and spot.contains(self._mouse) else colour));p.drawText(QPointF(x, base), str(item))
                if found is not None:
                    self._hot.append((spot, found[0], found[1], words[:1].upper() + words[1:] + ' (%s)' % label.strip()))
'''),
('''                box = QRectF(x, base - fm.ascent() - 3 * s, wide, fm.height() + 6 * s)
                p.save();p.setPen(Qt.NoPen);p.setBrush(QColor(t.AMBER_EDGE));p.drawRect(box)
''', '''                box = QRectF(x, base - fm.ascent() - 3 * s, wide, fm.height() + 6 * s)
                if box.contains(self._mouse):self._halo(p, box, t.READY, 1.8)      # under the pointer, the button that approves glows green
                p.save();p.setPen(Qt.NoPen);p.setBrush(QColor(t.AMBER_EDGE));p.drawRect(box)
'''),
('''        self._press = None                  # where a press began: (position, the sheet there, the scroll then)
''', '''        self._press = None                  # where a press began: (position, the sheet there, the scroll then)
        self._mouse = QPointF(-1, -1)       # where the pointer is, so what it is over can answer in its green
'''),
('''        hot = self._hot_at(pos);ident = '' if hot or self.reading is not None else (self._hit(pos) or '')
        self.setCursor(Qt.PointingHandCursor if hot or ident else Qt.ArrowCursor)
        if ident != self._hover:
            self._hover = ident;self.update()
''', '''        hot = self._hot_at(pos);ident = '' if hot or self.reading is not None else (self._hit(pos) or '')
        self.setCursor(Qt.PointingHandCursor if hot or ident else Qt.ArrowCursor)
        over = self._hot_at(self._mouse);self._mouse = QPointF(pos)
        if ident != self._hover or (hot is None) != (over is None) or (hot is not None and over is not None and hot[0] != over[0]):
            self._hover = ident;self.update()
'''),
('''    def leaveEvent(self, event):
        if self._hover:
            self._hover = '';self.update()
''', '''    def leaveEvent(self, event):
        self._mouse = QPointF(-1, -1)
        if self._hover or self._hot:
            self._hover = '';self.update()
''')])
print('ok')
