exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/common.py').read())
from pathlib import Path
from types import SimpleNamespace
from PySide6.QtWidgets import QLabel
from workbench.field_do import Step, op as op_line, call as line_call
face = w.shell2.face
def words(card): return ' / '.join(l.text().replace('​', '')[:200].replace('\n', ' ⏎ ') for l in card.findChildren(QLabel)[:12])
thing = SimpleNamespace(title='stock.csv')
plan = [(thing, Step('Write the stock table', 'write', op_line('files.write', path='stock.csv', text='Part,Required,Available,Unit\nR1,10,4,pcs\nU2,3,0,pcs\n'), '', 'execute')),
        (thing, Step('Find the short parts', 'read', '@files:stock.csv | rows | add Short = Required - Available | where Short over 0 | select Part,Short')),
        (thing, Step('Keep it on the Agenda', 'write', op_line('agenda.add', title='Short parts', program='@files:stock.csv | rows | add Short = Required - Available | where Short over 0 | count'), '', 'execute'))]
got = {}
card = face.say_plan(plan, done=lambda results: got.update(results=results)); settle(30, 3)
print('card:', words(card)[:700]); print('button:', card.run.text())
card.run.click(); settle(60, 5)
print('after Run: button=%r' % card.run.text())
for line, ok, res in got['results']: print('   %s | ok=%s | %s' % (line[:90], ok, short(res, 260)))
print('rows on the card:', [r.text().replace('​', '')[-60:] for r in card.rows])
print('\n-- a plan whose second step is refused')
plan2 = [(thing, Step('A read', 'read', 'documents.list | pick documents | count')),
         (thing, Step('A refused write', 'write', op_line('files.decide', id='0' * 32, apply=True), '', 'approve')),
         (thing, Step('Never reached', 'write', op_line('files.write', path='notes/never.txt', text='x'), '', 'execute'))]
got.clear(); card = face.say_plan(plan2, done=lambda results: got.update(results=results)); settle(20, 2); card.run.click(); settle(60, 5)
print('after Run: button=%r | results: %s' % (card.run.text(), [(l[:40], ok, short(r, 80)) for l, ok, r in got['results']]), '| never.txt exists:', (Path(k.root) / 'Files/notes/never.txt').exists())
print('\n-- the keyboard path: C checks the desk')
w.a_field.trigger(); settle(); v = w.field_page.view
QTest.keyClick(v, Qt.Key_C); settle(120, 6)
cards = [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
c = cards[-1]; print('   C ->', words(c)[:600]); print('   waiting:', [(o.title, why) for o, why, _ in getattr(c, 'waiting', [])], '| plan:', [(o.title, s.line) for o, s in getattr(c, 'plan', ())])
