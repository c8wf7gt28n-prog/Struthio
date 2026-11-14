exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/common.py').read())
from pathlib import Path
from PySide6.QtWidgets import QPushButton
from workbench.context_menu import operation_line, inspect_in_line
bar = w.type_bar; box = bar.box; con = w.console; face = w.shell2.face
def attempt(tag, pre=None, wait=False):
    pr2 = k.dispatch('files.propose', {'path': 'notes/%s.txt' % tag, 'text': 'x\n', 'why': tag}, p)['result']
    if pre: pre()
    line = operation_line('files.decide', {'id': pr2['proposal'], 'apply': True})
    inspect_in_line(w, line)
    if wait: settle(20, 3)
    pop = box.popup
    print('\n[%s] before Enter: focus=%s popup visible=%s current=%r' % (tag, box.hasFocus(), pop.isVisible(), pop.list.currentItem().text()[:40] if pop.list.currentItem() else None))
    QTest.keyClick(box, Qt.Key_Return); settle(40, 4)
    print('[%s] after 1st Enter: pending=%s box=%r' % (tag, bool(con.pending_approval), box.text()[:30]))
    QTest.keyClick(box, Qt.Key_Return); settle(40, 4)
    print('[%s] after 2nd Enter: file exists: %s' % (tag, (Path(k.root) / ('Files/notes/%s.txt' % tag)).exists()))
attempt('nowait')
def card_first():
    card = face.proposal_card({'operation': 'language.run', 'arguments': {'text': 'documents.list | pick documents | count'}}); face.add(card); settle(20, 3)
    next(b for b in card.findChildren(QPushButton) if b.text() == 'Edit').click(); settle(10, 2); box.clear()
    next(b for b in card.findChildren(QPushButton) if b.text() == 'Run').click(); settle(40, 4)
attempt('aftercard', card_first)
attempt('aftercard_wait', card_first, wait=True)
