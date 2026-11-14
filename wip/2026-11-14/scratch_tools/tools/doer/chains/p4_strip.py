exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/common.py').read())
import sqlite3
bar = w.type_bar; box = bar.box; con = w.console; face = w.shell2.face

def journal_head():
    r = k.dispatch('ledger.journal.status', {}, p); return r['result']['head']
def journal_since(seq):
    db = sqlite3.connect(str(k.root / '.ledger/engineering.sqlite3'))
    cols = [c[1] for c in db.execute('PRAGMA table_info(activity_journal)')]
    rows = db.execute('SELECT * FROM activity_journal WHERE seq>? ORDER BY seq', (seq,)).fetchall(); db.close()
    return cols, rows
def tail(n=6):
    lines = [l for l in con.output.toPlainText().replace('​', '').splitlines() if l.strip()]
    return lines[-n:]
def talk(n=2):
    out = []
    from PySide6.QtWidgets import QLabel
    cards = [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
    for c in cards[-n:]:
        out.append(' / '.join(l.text().replace('​', '')[:160].replace('\n', ' ⏎ ') for l in c.findChildren(QLabel)[:4]))
    return out
def strip(text, ctrl=False, note=''):
    head = journal_head()
    bar.set_target('slate', focus=True); box.setFocus(); box.setText(text); settle(10, 2)
    kind = bar.context_text
    QTest.keyClick(box, Qt.Key_Return, Qt.ControlModifier if ctrl else Qt.NoModifier); settle(40, 4)
    print('\n>>> %s %r   %s' % ('Ctrl+Enter' if ctrl else 'Enter', text, note))
    print('    strip said before the key: %r | console page now: %s | size: %s | pending_approval: %r | box now: %r' % (kind, con.mode, con.size_level, con.pending_approval, box.text()))
    for l in tail(5): print('    console| ' + l[:230])
    for l in talk(2): print('    talk   | ' + l[:300])
    cols, rows = journal_since(head)
    for r in rows:
        e = json.loads(dict(zip(cols, r))['payload']); print('    journal| seq=%s %s' % (r[0], {kk: vv for kk, vv in e.items() if kk in ('operation','state','origin','detail','correlation_id') and vv not in (None, '')}))
    return rows
cols, _ = journal_since(10**9); print('journal columns:', cols)
print('scopes:', {o: CAPABILITIES[o] for o in ('documents.list', 'files.write', 'files.trash', 'agenda.add', 'agenda.cancel', 'files.propose', 'stac.export') if o in CAPABILITIES})
strip('documents.list | pick documents | select title,words', ctrl=True, note='typed staC, Ctrl+Enter')
strip('explain documents.list | pick documents | select title,words', ctrl=True, note='explain, Ctrl+Enter')
strip('files.write {"path":"x.txt","text":"y"}', ctrl=True, note='a write as staC, Ctrl+Enter')
strip('/documents.list', note='read-scope operation line, Enter')
strip('/files.write {"path":"notes/a.txt","text":"hello"}', note='execute-scope operation line (json form), Enter')
strip('/files.write path=notes/b.txt text="hello b"', note='execute-scope, name=value form')
a = k.dispatch('agenda.add', {'title': 'probe item', 'program': 'documents.list | pick documents | count'}, p)['result']
print('agenda item', a['id'], a['state'])
strip('/agenda.cancel {"id":"%s","reason":"probe"}' % a['id'], note='approve-scope operation line: FIRST Enter')
print('    (box holds the pending line; pressing Enter again)')
head = journal_head()
QTest.keyClick(box, Qt.Key_Return); settle(40, 4)
print('>>> second Enter: pending_approval=%r box=%r' % (con.pending_approval, box.text()))
for l in tail(4): print('    console| ' + l[:230])
cols, rows = journal_since(head)
for r in rows:
    e = json.loads(dict(zip(cols, r))['payload']); print('    journal| seq=%s %s' % (r[0], {kk: vv for kk, vv in e.items() if kk in ('operation','state','origin','detail','correlation_id') and vv not in (None, '')}))
print('agenda item now:', [ (i['id'][:8], i['state'], i['reason']) for i in k.dispatch('agenda.view', {}, p)['result']['done']])
strip('/agenda.cancel {"id":"%s"}' % a['id'], note='approve again, then CHANGE the line before second Enter')
box.setText(box.text() + ' '); box.textEdited.emit(box.text()); settle(10, 2)
print('    after editing: pending_approval=%r' % (con.pending_approval,))
strip('/nonexistent.op', note='unknown operation')
strip('/files.write path=', note='bad argument')
strip('/documents.get id=nothex', note='schema refusal')
strip('/help files.write', note='help')
strip('/ops agenda', note='ops')
strip('what is in the bench readings?', note='plain words, Enter (no model)')
strip('documents.list | pick documents | count', note='typed staC with plain Enter (not Ctrl)')
