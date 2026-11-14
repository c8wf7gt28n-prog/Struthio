exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/common.py').read())
import os, time
from pathlib import Path
from PySide6.QtWidgets import QPushButton, QLabel
face = w.shell2.face; bar = w.type_bar; box = bar.box; con = w.console
def cards(n=1):
    out = [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
    return out[-n:]
def words(card): return ' / '.join(l.text().replace('​', '')[:220].replace('\n', ' ⏎ ') for l in card.findChildren(QLabel)[:6])
print('=========== A. SlateFace.proposal_card: stage an operation for one click')
for action in ({'operation': 'files.write', 'arguments': {'path': 'notes/from-card.txt', 'text': 'hello from a card'}},
               {'operation': 'language.run', 'arguments': {'text': 'documents.list | pick documents | count'}},
               {'operation': 'agenda.add', 'arguments': {'title': 'card item', 'program': 'documents.list | pick documents | count'}}):
    card = face.proposal_card(action); face.add(card); settle(20, 3)
    labels = [l.text() for l in card.findChildren(QLabel)]; btns = card.findChildren(QPushButton)
    print('\ncard for', action['operation'], '| labels:', [t[:120] for t in labels], '| buttons:', [b.text() for b in btns])
    next(b for b in btns if b.text() == 'Edit').click(); settle(10, 2); print('   Edit puts in the line:', repr(box.text())); box.clear()
    run = next(b for b in btns if b.text() == 'Run'); run.click(); settle(40, 4)
    print('   after Run: button says %r enabled=%s' % (run.text(), run.isEnabled()))
    print('   Talk bubble:', words(cards(1)[0])[:500])
print('file written by the card:', (Path(k.root) / 'Files/notes/from-card.txt').exists())
print('matrix rows now:', [(r['outcome'], r['operation'], r['program'][:70], r['intent']) for r in k.dispatch('matrix.list', {'limit': 5}, p)['result']['rows']])
print('\n-- an approve-scope action on a card (files.decide): does one click run it?')
pr = L('files.propose', {'path': 'notes/proposed.txt', 'text': 'proposed text\n', 'why': 'a probe proposal'})
L('files.proposals', {})
print('   agenda waiting:', [(r['kind'], r['title'], r.get('reason')) for r in k.dispatch('agenda.view', {}, p)['result']['waiting']])
card = face.proposal_card({'operation': 'files.decide', 'arguments': {'id': pr['proposal'], 'apply': True}}); face.add(card); settle(20, 3)
print('   card labels:', [l.text()[:140] for l in card.findChildren(QLabel)])
next(b for b in card.findChildren(QPushButton) if b.text() == 'Run').click(); settle(40, 4)
print('   Talk bubble:', words(cards(1)[0])[:400]); print('   file exists:', (Path(k.root) / 'Files/notes/proposed.txt').exists(), '| proposals left:', k.dispatch('files.proposals', {}, p)['result'])
print('\n-- the same with the writing strip: operation_line + inspect_in_line, then Enter, Enter')
from workbench.context_menu import operation_line, inspect_in_line
pr2 = L('files.propose', {'path': 'notes/proposed2.txt', 'text': 'second\n', 'why': 'second probe'})
line = operation_line('files.decide', {'id': pr2['proposal'], 'apply': True}); print('   operation_line ->', line)
print('   inspect_in_line returned', repr(inspect_in_line(w, line)), '| status said:', getattr(w, '_context_said', None))
QTest.keyClick(box, Qt.Key_Return); settle(40, 4); print('   after 1st Enter: pending=%r box=%r' % (con.pending_approval, box.text()))
print('   console|', [l for l in con.output.toPlainText().splitlines() if l.strip()][-1][:200])
QTest.keyClick(box, Qt.Key_Return); settle(40, 4); print('   after 2nd Enter: pending=%r box=%r' % (con.pending_approval, box.text()))
print('   console|', [l for l in con.output.toPlainText().splitlines() if l.strip()][-4:])
print('   file exists:', (Path(k.root) / 'Files/notes/proposed2.txt').exists())
print('\n=========== B. Agenda: a program kept, run, and a second that waits for the first')
L('files.write', {'path': 'stock.csv', 'text': 'Part,Required,Available,Unit\nR1,10,4,pcs\nC4,5,9,pcs\nU2,3,0,pcs\n'}, quiet=True)
a1 = L('agenda.add', {'title': 'Step 1: shortages', 'program': '@files:stock.csv | rows | add Short = Required - Available | where Short over 0 | select Part,Short'}, n=260)
a2 = L('agenda.add', {'title': 'Step 2: count them', 'program': '@files:stock.csv | rows | add Short = Required - Available | where Short over 0 | count', 'when': {'after': a1['id']}}, n=260)
for i in range(4):
    r = L('agenda.run_next', {}, n=300)
v = k.dispatch('agenda.view', {}, p)['result']
for row in v['done']: print('   DONE row: %s | state=%s | outcome=%r | rounds_used=%s | last_digest=%s' % (row['title'], row['state'], (row['outcome'] or '')[:200], row['rounds_used'], (row['last_digest'] or '')[:12]))
print('   next:', [(r.get('title'), r.get('state')) for r in v['next']], '| later:', [(r['title'], r['state']) for r in v['later']])
L('agenda.resume', {'id': a1['id']}, 'can a DONE item be queued again?')
L('agenda.accept', {'id': a1['id']}, 'or accepted again?')
print('\n-- a watch (repeats), and a write program refused by the read-only runner')
wt = L('agenda.add', {'title': 'watch shortages', 'program': '@files:stock.csv | rows | where Available under 1 | select Part', 'watch': True, 'nice': 'normal'}, n=300)
L('agenda.run_next', {})
L('files.write', {'path': 'stock.csv', 'text': 'Part,Required,Available,Unit\nR1,10,0,pcs\nC4,5,9,pcs\nU2,3,0,pcs\n'}, quiet=True)
with k.db() as db: db.execute('UPDATE agenda_items SET due=?, state=? WHERE id=?', (time.time() - 1, 'NEXT', wt['id']))   # (probe only) make it due now
L('agenda.run_next', {})
v = k.dispatch('agenda.view', {}, p)['result']
print('   waiting:', [(r['kind'], r['title'][:60], (r.get('reason') or '')[:160]) for r in v['waiting']])
print('   later:', [(r['title'], r['state'], (r['outcome'] or '')[:120]) for r in v['later']])
bad = L('agenda.add', {'title': 'a write on the agenda', 'program': 'files.write {"path":"notes/x.txt","text":"y"}'}, n=200)
L('agenda.run_next', {})
v = k.dispatch('agenda.view', {}, p)['result']; print('   done:', [(r['title'], r['state'], (r['outcome'] or '')[:160]) for r in v['done'][:2]])
bad2 = L('agenda.add', {'title': 'an operation line on the agenda', 'program': '/files.write {"path":"notes/x.txt","text":"y"}'}, n=200)
L('agenda.run_next', {})
v = k.dispatch('agenda.view', {}, p)['result']; print('   done:', [(r['title'], r['state'], (r['outcome'] or '')[:160]) for r in v['done'][:1]])
