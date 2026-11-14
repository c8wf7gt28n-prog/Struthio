from PySide6.QtGui import QFontMetricsF
w.a_field.trigger(); settle(); v = w.field_page.view; v.setFocus(); settle(); QTest.keyClick(v, Qt.Key_Z); settle(200, 3)
o = next(o for o in v.field.objects if o.title.startswith('07 Bench')); pl = v._placed[o.id]; s = v.scale(); px = 1 / v.zoom
fm = QFontMetricsF(v.sans(12.5 * px)); print('scale', s, 'zoom', v.zoom, 'placed w,h', pl.w, pl.h, '| font px', v.sans(12.5 * px).pixelSize(), '| "07 Bench" wide', fm.horizontalAdvance('07 Bench'), '| line height', fm.height())
pad = 7 * s * px; side = min(22 * s * px, pl.h - 2 * pad); mark = 8 * s * px; room = mark + 5 * s * px
print('pad', pad, 'side', side, 'room', room, '| width for the name', pl.w - pad - (pad + side + 7 * s * px) - room)
