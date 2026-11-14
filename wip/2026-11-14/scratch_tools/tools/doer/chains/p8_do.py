exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/common.py').read())
from pathlib import Path
from PySide6.QtWidgets import QPushButton, QLabel
from workbench import field_do
from workbench.field_do import Step, call as line_call, op as op_line, steps_for
face = w.shell2.face
def cards(n=1):
    out = [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
    return out[-n:]
def words(card): return ' / '.join(l.text().replace('​', '')[:240].replace('\n', ' ⏎ ') for l in card.findChildren(QLabel)[:8])
print('=========== A. field_do.call: one parser for both kinds of line')
for line in ('documents.list | pick documents | count', '@files:stock.csv | rows', 'explain documents.list', 'desk | find sheet',
             '/files.write {"path": "notes/a.txt", "text": "hello"}', '/agenda.view', '/files.write path=notes/a.txt text=hello', '/nonexistent.op {}', 'make me a sandwich'):
    try: print('   %-58s -> %s' % (line, line_call(line)))
    except Exception as e: print('   %-58s -> RAISES %s: %s' % (line, type(e).__name__, e))
print('\n=========== B. steps_for every object of the Field')
w.a_field.trigger(); settle(); v = w.field_page.view
for o in v.field.objects:
    steps = steps_for(k, p, o, v.field)
    print('\n%s “%s” state=%r' % (o.kind, o.title, o.state))
    for i, s in enumerate(steps): print('   %d [%s/%s] %s\n        %s%s' % (i + 1, s.kind, s.scope, s.words, s.line[:230], ('\n        why: ' + s.why) if s.why else ''))
print('\n=========== C. SlateFace.stage: any operation line staged for one Run, with a callback')
got = {}
step = Step('Write a note', 'write', op_line('files.write', path='notes/staged.txt', text='staged by a card\n'), 'a new file in Files/notes', 'execute')
card = face.stage('a probe', step, done=lambda ok, result: got.update(ok=ok, result=result)); settle(30, 3)
print('   card:', words(card)); print('   buttons:', [b.text() for b in card.findChildren(QPushButton)], '| card.ran =', card.ran)
print('   file before Run:', (Path(k.root) / 'Files/notes/staged.txt').exists())
card.run.click(); settle(40, 4)
print('   after Run: button %r | card.ran=%s | callback got ok=%s result=%s' % (card.run.text(), card.ran, got.get('ok'), short(got.get('result'), 300)))
print('   card now:', words(card)); print('   file after Run:', (Path(k.root) / 'Files/notes/staged.txt').exists())
card.run.setEnabled(True); card.run.click(); settle(20, 2); print('   a second click does nothing: ran=%s, text=%r' % (card.ran, card.run.text()))
print('\n-- a refusal through the same card')
got.clear(); step = Step('Decide a proposal that is not there', 'write', op_line('files.decide', id='0' * 32, apply=True), '', 'approve')
card = face.stage('a probe', step, done=lambda ok, result: got.update(ok=ok, result=result)); settle(20, 2); card.run.click(); settle(40, 4)
print('   after Run: button %r | callback %s | card: %s' % (card.run.text(), got, words(card)[-260:]))
print('\n-- a staC line on a stage card, and a malformed line')
got.clear(); card = face.stage('a probe', Step('Count the documents', 'write', 'documents.list | pick documents | count'), done=lambda ok, result: got.update(ok=ok, result=result)); settle(20, 2); card.run.click(); settle(40, 4)
print('   staC on a stage card: button %r | callback %s' % (card.run.text(), short(got, 300)))
try:
    got.clear(); card = face.stage('a probe', Step('Bad line', 'write', '/files.write path=notes/x.txt'), done=lambda ok, result: got.update(ok=ok, result=result)); settle(20, 2); card.run.click(); settle(40, 4)
    print('   name=value form on a stage card: button %r | callback %s | %s' % (card.run.text(), got, words(card)[-200:]))
except Exception as e: print('   name=value form RAISES %s: %s' % (type(e).__name__, e))
print('\n=========== D. the keyboard path: D on a sheet, a digit takes a step')
page = w.field_page
calc = next(o for o in v.field.objects if o.kind == 'finding'); v.field.select(calc.id); v.update(); settle(5, 2)
before = face.lines.count()
QTest.keyClick(v, Qt.Key_D); settle(60, 4)
print('   D on %r -> steps offered: %s' % (calc.title[:40], [(s.words, s.kind) for s in page.steps]))
print('   Talk:', words(cards(1)[0])[:500])
QTest.keyClick(v, Qt.Key_1); settle(60, 4); print('   digit 1 ->', words(cards(1)[0])[:400])
n = next((i for i, s in enumerate(page.steps) if s.kind == 'write'), None)
if n is not None:
    QTest.keyClick(v, getattr(Qt, 'Key_%d' % (n + 1))); settle(60, 4); c = cards(1)[0]
    print('   digit %d (a write) -> staged: %s | has Run: %s' % (n + 1, words(c)[:400], hasattr(c, 'run')))
    c.run.click(); settle(80, 5); print('   after Run:', c.run.text(), '|', words(c)[-200:])
print('   journal tail:')
import sqlite3, json as _j
db = sqlite3.connect(str(k.root / '.ledger/engineering.sqlite3'))
for seq, payload in db.execute('SELECT seq,payload FROM activity_journal ORDER BY seq DESC LIMIT 6').fetchall()[::-1]:
    e = _j.loads(payload); print('      seq=%s %s %s %s' % (seq, e.get('operation'), e.get('state'), e.get('origin')))
print('   audit columns:', [c[1] for c in db.execute('PRAGMA table_info(audit)')], '| last:', db.execute('SELECT * FROM audit ORDER BY rowid DESC LIMIT 2').fetchall())
