from PySide6.QtWidgets import QApplication
w.a_field.trigger(); settle(); v = w.field_page.view
o = next(o for o in v.field.objects if o.title == '07 Bench readings'); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(200, 6)
b = w.tabs.field_button; c = b.parentWidget()
print('field button:', b.geometry(), '| pin button:', w.tabs.pin_button.geometry(), '| corner:', c.geometry(), '| tab bar:', w.tabs.tabBar().geometry(), '| corner hint:', c.sizeHint(), '| button hint:', b.sizeHint(), b.minimumSizeHint())
save('Graphite_Mouse_00_Back_Button_%s.png' % tag)
