bar = w.type_bar; console = w.console
def strip(text):
    bar.set_target('slate', focus=False); bar.box.setFocus(); bar.box.setText(text); settle(10, 2); bar.refresh_context(); settle(5, 2)
    QTest.keyClick(bar.box, Qt.Key_Return, Qt.ControlModifier); settle(80, 4)
w.a_field.trigger(); settle(); v = w.field_page.view
if hasattr(console, 'set_size'): console.set_size(1)
strip('word waits = field.read | pick waiting | select kind,title,state'); strip('word doubts = field.doubt | pick rows | where verdict=doubt | select title,about'); strip('doubts'); strip('words')
bar.box.setText('waits | count'); settle(10, 2); bar.refresh_context(); settle(20, 3)
save('Graphite_Words_01_Your_Own_Words_%s.png' % tag)
