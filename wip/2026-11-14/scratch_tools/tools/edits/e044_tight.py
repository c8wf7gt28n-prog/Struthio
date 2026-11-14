import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'field_qt.py', [
('''    def _reading_rect(self, body):
        s = self.scale();wide = min(body.width() - 2 * 20 * s, 940 * s)
        return QRectF(body.left() + (body.width() - wide) / 2, body.top() + 14 * s, wide, self.height() - body.top() - 28 * s)
''', '''    def _tight(self, body):
        """A large reading size on a small screen: the page gives up its margins and its staC line so the writing keeps room."""
        s = self.scale()
        return body.width() < 700 * s or self.height() - body.top() < 520 * s

    def _reading_rect(self, body):
        s = self.scale();edge = (6 if self._tight(body) else 20) * s;top = (6 if self._tight(body) else 14) * s
        wide = min(body.width() - 2 * edge, 940 * s)
        return QRectF(body.left() + (body.width() - wide) / 2, body.top() + top, wide, self.height() - body.top() - 2 * top)
'''),
('''        s = self.scale();r = self._reading_rect(body);pad = 26 * s;read = self.reading
''', '''        s = self.scale();r = self._reading_rect(body);tight = self._tight(body);pad = (14 if tight else 26) * s;read = self.reading
'''),
('''        title_font = self.sans(19);fm_title = QFontMetricsF(title_font);y = r.top() + pad + fm_title.ascent()
        p.setFont(title_font);p.setPen(QColor(t.TEXT));p.drawText(QPointF(r.left() + pad, y), fm_title.elidedText(read['title'], Qt.ElideRight, r.width() - 2 * pad))
        top = y + fm_title.descent() + 12 * s
''', '''        title_font = self.sans(17 if tight else 19);fm_title = QFontMetricsF(title_font);y = r.top() + pad + fm_title.ascent()
        p.setFont(title_font);p.setPen(QColor(t.TEXT))
        heading = self._flow(read['title'], fm_title, r.width() - 2 * pad)       # a long name takes a second line before it is cut
        if len(heading) > 2:heading = [heading[0], fm_title.elidedText(' '.join(heading[1:]), Qt.ElideRight, r.width() - 2 * pad)]
        for index, line in enumerate(heading):
            if index:y += fm_title.height()
            p.drawText(QPointF(r.left() + pad, y), line)
        top = y + fm_title.descent() + (8 if tight else 12) * s
'''),
('''        fm_foot = QFontMetricsF(self.mono(12));foot_h = (fm_foot.height() + 10 * s) * (2 if read['code'] else 1) + 8 * s
''', '''        code = '' if tight else read['code']      # when room is short the line that read it gives way to the writing; S still has it for a sheet
        fm_foot = QFontMetricsF(self.mono(12));foot_h = (fm_foot.height() + 10 * s) * (2 if code else 1) + 8 * s
'''),
('''        if read['code']:
            p.setPen(QColor(t.FAINT));p.drawText(QPointF(r.left() + pad, base - fm_foot.height() - 6 * s), fm_foot.elidedText('staC  ' + read['code'], Qt.ElideRight, r.width() - 2 * pad))
''', '''        if code:
            p.setPen(QColor(t.FAINT));p.drawText(QPointF(r.left() + pad, base - fm_foot.height() - 6 * s), fm_foot.elidedText('staC  ' + code, Qt.ElideRight, r.width() - 2 * pad))
''')])
print('ok')
