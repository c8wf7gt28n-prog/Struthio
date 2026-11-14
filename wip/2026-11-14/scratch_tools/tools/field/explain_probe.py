bar = w.type_bar; console = w.console
w.a_field.trigger(); settle(); v = w.field_page.view
calc = next(o for o in v.field.objects if o.kind == 'calculation'); v.field.select(calc.id); v._describe(); v.update(); settle(5, 2)
bar.set_target('slate', focus=False); bar.box.setFocus(); bar.box.setText('explain this | count'); settle(10, 2)
QTest.keyClick(bar.box, Qt.Key_Return, Qt.ControlModifier); settle(80, 4)
out = console.output.toPlainText().strip().splitlines(); print('explain this | count ->'); print('\n'.join('   ' + l for l in out[-7:])[:900])
print('box cleared:', repr(bar.box.text()), '| note:', repr(bar.message))
