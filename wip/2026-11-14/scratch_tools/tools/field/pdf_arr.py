w.a_field.trigger(); settle(); v = w.field_page.view
o = next(o for o in v.field.objects if o.title.startswith('07_Bench_Readings.pdf')); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8)
page = w.tabs.currentWidget()
print('arrangement', page._arrangement, '| viewport', page.reader_scroll.viewport().width(), '| page width', page.width(), '| split orientation', page.split.orientation(), '| size', w.width())
page._arrangement = None; page.arrange(); settle(100, 3); print('after arranging again', page._arrangement, page.split.orientation())
