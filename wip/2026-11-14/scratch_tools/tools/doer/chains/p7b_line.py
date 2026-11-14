exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/common.py').read())
from pathlib import Path
from workbench.context_menu import operation_line, inspect_in_line
bar = w.type_bar; box = bar.box; con = w.console
print('same box:', box is w.shell2.top.box)
pr2 = L('files.propose', {'path': 'notes/proposed2.txt', 'text': 'second\n', 'why': 'second probe'})
line = operation_line('files.decide', {'id': pr2['proposal'], 'apply': True})
inspect_in_line(w, line); settle(20, 3)
pop = box.popup
print('box text=%r focus=%s popup visible=%s rows=%s current=%r' % (box.text(), box.hasFocus(), pop.isVisible(), pop.list.count(), pop.list.currentItem().text() if pop.list.currentItem() else None))
print('console_page:', box.console_page(box.text()), '| type_target:', w.type_target)
QTest.keyClick(box, Qt.Key_Return); settle(40, 4)
print('after 1st Enter: pending=%r box=%r console.mode=%s' % (con.pending_approval, box.text(), con.mode))
print('   console|', [l for l in con.output.toPlainText().splitlines() if l.strip()][-2:])
QTest.keyClick(box, Qt.Key_Return); settle(40, 4)
print('after 2nd Enter: pending=%r box=%r' % (con.pending_approval, box.text()))
print('   console|', [l[:160] for l in con.output.toPlainText().splitlines() if l.strip()][-3:])
print('   file exists:', (Path(k.root) / 'Files/notes/proposed2.txt').exists())
