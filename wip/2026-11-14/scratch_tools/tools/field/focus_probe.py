w.a_field.trigger(); settle(); v = w.field_page.view
o = next(o for o in v.field.objects if o.title == '07 Bench readings'); v.field.select(o.id); v._reveal(); v._describe(); v.update(); settle(5, 2)
w.shell2.ask('set B4 to 700'); settle(200, 6); v.repaint(); settle(20, 2)
box = next(b for b, kk, tx, words in v._hot if kk == Qt.Key_G)
print('before the click, keyboard in:', type(app.focusWidget()).__name__)
QTest.mouseClick(v, Qt.LeftButton, pos=box.center().toPoint()); settle(300, 6)
print('after clicking Approve, keyboard in:', type(app.focusWidget()).__name__, '| Field in front:', w._field_active, '| window active:', w.isActiveWindow())
QTest.keyClick(v, Qt.Key_Right); settle(20, 2); print('an arrow still moves:', v.selected().title)
