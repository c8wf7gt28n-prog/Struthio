# Stacy's hand: the dial; a change asked of her is done at once with Do and show, with one Undo; Ask first waits as before;
# a change the records mark for approval waits at Do and show and is hers at Free hand; Terminal commands that only read are hers.
from PySide6.QtWidgets import QLabel, QPushButton, QApplication
from workbench import stacy_hand
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face; ok = True
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=6): return [l.text().replace('​', '')[:300].replace('\n', ' / ') for l in card.findChildren(QLabel)][:n]
w.a_field.trigger(); settle(); v = w.field_page.view; page = w.field_page
def tile(words): return next(o for o in v.field.objects if words in o.title)
def b4(): return k.dispatch('office.get', {'id': tile('07 Bench readings').target['id']}, p)['result']['document']['sheets'][0]['cells']['B4']['value']
def choose(o): v.field.select(o.id); v._describe(); v.update(); settle(60, 3)
print('a fresh workspace: her hand is', stacy_hand.level(w), '| the words under her name:', repr(face.hand.text()), 'shown', face.hand.isVisible()); ok &= stacy_hand.level(w) == 'show' and face.hand.text() == 'does and shows' and face.hand.isVisible()
save('Hand_00_The_Dial_%s.png' % tag)
# 1. Do and show: asked, done at once, with an Undo
choose(tile('07 Bench readings')); was = b4(); w.shell2.ask('set the startup current to 700'); settle(300, 6); c = cards()[-1]
undo = c.findChild(QPushButton, 'StagedUndo'); approve = c.findChild(QPushButton, 'StagedRun')
print('1. asked “set the startup current to 700” ->', said(c, 1)[0][:110]); print('   she said:', [s for s in said(c, 8) if s.startswith('Done')][:1], '| B4 was', was, 'is', b4(), '| Undo there:', undo is not None, '| Approve shown:', approve.isVisible(), '| the Field waits for:', repr(v.go))
ok &= b4() == '700' and undo is not None and not approve.isVisible() and v.go == ''
print('   calculations now:', [(o.title[:22], o.state) for o in v.field.objects if o.kind == 'calculation'])
trail = stacy_hand.trail(w.session.state); print('   her trail:', [(e['words'][:44], e['state'], bool(e['undo']), e['word']) for e in trail[:2]]); ok &= len(trail) == 1 and trail[0]['state'] == 'done' and trail[0]['word'] == 'set the startup current to 700'
save('Hand_01_Done_With_Undo_%s.png' % tag)
QTest.mouseClick(undo, Qt.LeftButton); settle(300, 6)
print('   pressed Undo -> B4 is', b4(), '| the button says', repr(undo.text()), '| she said:', said(c, 12)[-1][:120], '| trail:', stacy_hand.trail(w.session.state)[0]['state']); ok &= b4() == was and undo.text() == 'Undone' and stacy_hand.trail(w.session.state)[0]['state'] == 'undone'
save('Hand_02_Taken_Back_%s.png' % tag)
# 2. an Undo that can no longer be exact is refused and nothing is touched
choose(tile('07 Bench readings')); w.shell2.ask('set the startup current to 710'); settle(300, 6); c2 = cards()[-1]; undo2 = c2.findChild(QPushButton, 'StagedUndo')
choose(tile('07 Bench readings')); w.shell2.ask('set the startup current to 720'); settle(300, 6)
QTest.mouseClick(undo2, Qt.LeftButton); settle(300, 6); print('2. two changes, then Undo on the first ->', repr(undo2.text()), '| B4 stays', b4(), '|', said(c2, 12)[-1][:130]); ok &= undo2.text() == 'Not undone' and b4() == '720'
c3 = cards()[-1]; QTest.mouseClick(c3.findChild(QPushButton, 'StagedUndo'), Qt.LeftButton); settle(300, 6); print('   Undo on the latest -> B4 is', b4()); ok &= b4() == '710'
# 3. Ask first: as it was
stacy_hand.choose(w, 'ask'); face.show_hand(); choose(tile('07 Bench readings')); w.shell2.ask('set the startup current to 730'); settle(300, 6); c = cards()[-1]; approve = c.findChild(QPushButton, 'StagedRun')
print('3. hand at Ask first:', repr(face.hand.text()), '->', said(c, 1)[0][-60:], '| Approve shown:', approve.isVisible(), '| B4 still', b4(), '| the Field waits for:', repr(v.go)[:50]); ok &= approve.isVisible() and b4() == '710' and v.go != ''
QTest.mouseClick(approve, Qt.LeftButton); settle(300, 6); print('   pressed Approve -> B4 is', b4(), '| an Undo on a change you approved yourself:', c.findChild(QPushButton, 'StagedUndo') is not None); ok &= b4() == '730'
# 4. what the records mark for approval: waits at Do and show, hers at Free hand
stacy_hand.choose(w, 'show'); face.show_hand(); page.refresh(force=True); settle(200, 4); calc = next(o for o in v.field.objects if o.kind == 'calculation' and o.state != 'current'); choose(calc)
from workbench import field_page as fp
steps = fp.do(w, calc); n = next(i for i, s_ in enumerate(page.steps) if s_.kind == 'write'); step = page.steps[n]
print('4. a calculation that waits (%s, %s): step %r, scope %s | its row says it waits: %s' % (calc.title[:24], calc.state, step.words, step.scope, fp._waits(w, step)))
c = fp.take(w, calc, n); settle(300, 6); print('   Do and show ->', said(c, 1)[0][-70:], '| ran:', c.ran); ok &= c.ran is None and 'waits for you' in said(c, 1)[0]
stacy_hand.choose(w, 'free'); face.show_hand(); page.refresh(force=True); settle(200, 4); calc = next(o for o in v.field.objects if o.kind == 'calculation' and o.state != 'current'); choose(calc)
fp.do(w, calc); n = next(i for i, s_ in enumerate(page.steps) if s_.kind == 'write'); c = fp.take(w, calc, n); settle(600, 8)
print('   Free hand (%r) -> ran: %s | %s | calculations now: %s' % (face.hand.text(), c.ran, said(c, 12)[-1][:110], [(o.title[:22], o.state) for o in v.field.objects if o.kind == 'calculation'])); ok &= c.ran is True
settle(900, 8); noticed = [c_ for c_ in cards() if said(c_, 1) and said(c_, 1)[0].startswith('I noticed')]
print('   then, by herself: %s | calculations now: %s' % (said(noticed[-1], 4) if noticed else None, [(o.title[:22], o.state) for o in v.field.objects if o.kind == 'calculation']))
ok &= bool(noticed) and all(o.state == 'current' for o in v.field.objects if o.kind == 'calculation')
save('Hand_03_Free_Hand_%s.png' % tag)
choose(tile('07 Bench readings')); before = len(cards()); w.shell2.ask('set the startup current to 740'); settle(1200, 10)
new = cards()[before:]; print('   Free hand, asked “set the startup current to 740” -> B4', b4(), '| cards since:', [said(c_, 1)[0][:70] for c_ in new if said(c_, 1)], '| calculations:', [(o.title[:28], o.state) for o in v.field.objects if o.kind == 'calculation'])
ok &= b4() == '740' and any(said(c_, 1) and said(c_, 1)[0].startswith('I noticed') for c_ in new) and all(o.state == 'current' for o in v.field.objects if o.kind == 'calculation')
print('   her trail now:', [(e['words'][:50], e['state']) for e in stacy_hand.trail(w.session.state)[:5]])
save('Hand_03b_Noticed_%s.png' % tag)
# 5. the Terminal: a command that only reads is hers; another is put in the line
ran = []
import workbench.shell2 as s2
real = s2.to_console; s2.to_console = lambda host, pg, text: ran.append((pg, text))
try:
    w.shell2.ask('run df -h'); settle(200, 4); a = said(cards()[-1], 2)[0][:110]
    w.shell2.ask('in the terminal: rm -rf old'); settle(200, 4); b = said(cards()[-1], 2)[0][:140]
    w.shell2.ask('run the numbers again'); settle(200, 4)
finally: s2.to_console = real
print('5. “run df -h” ->', ran, '|', a); print('   “in the terminal: rm -rf old” -> typing to', w.type_bar.target, '| the line:', repr(w.type_bar.box.text()), '|', b); ok &= ran == [('shell', 'df -h')] and w.type_bar.target == 'shell' and w.type_bar.box.text() == 'rm -rf old'
w.type_bar.box.clear(); w.type_bar.set_target('slate', focus=False)
# 5b. an artifact made at her word, where the owner's own would be: a folder, a file in it, a page, a note; never over what is there
import json as _json
stacy_hand.choose(w, 'show'); face.show_hand()
def has(path): return bool(k.dispatch('files.get', {'path': path}, p).get('ok'))
from workbench import files_service as _fs
def text_of(path):
    f = _fs.root(k) / path
    return f.read_text(encoding='utf-8') if f.is_file() else None
w.shell2.ask('make a folder called Bracket'); settle(300, 5); c = cards()[-1]
print('5b. “make a folder called Bracket” ->', said(c, 1)[0][:70], '| in Files:', has('Bracket'), '| Undo:', c.findChild(QPushButton, 'StagedUndo') is not None); ok &= has('Bracket') and c.findChild(QPushButton, 'StagedUndo') is not None
w.shell2.ask('write a file called Bracket/plan.txt saying cut the stock first'); settle(300, 5); c2 = cards()[-1]; r2 = text_of('Bracket/plan.txt')
print('   “write a file called Bracket/plan.txt saying cut the stock first” -> in Files:', has('Bracket/plan.txt'), '| it says:', repr(r2)); ok &= has('Bracket/plan.txt') and r2 == 'cut the stock first'
w.shell2.ask('write a file called Bracket/plan.txt saying something else'); settle(300, 5); r3 = text_of('Bracket/plan.txt')
print('   asked to write the same name again ->', said(cards()[-1], 1)[0][:110], '| the file still says the first words:', r3 == 'cut the stock first'); ok &= r3 == 'cut the stock first' and 'already' in said(cards()[-1], 1)[0]
QTest.mouseClick(c2.findChild(QPushButton, 'StagedUndo'), Qt.LeftButton); settle(300, 5); trash = k.dispatch('files.trash_list', {}, p)
print('   Undo on the file -> in Files:', has('Bracket/plan.txt'), '| in the Trash:', [x['original'] for x in (trash.get('result') or {}).get('trash', [])][:3]); ok &= not has('Bracket/plan.txt') and any(x['original'].endswith('plan.txt') for x in (trash.get('result') or {}).get('trash', []))
w.shell2.ask('start a page called Bench plan, saying: Check the rail first.'); settle(400, 6); c4 = cards()[-1]; docs = _json.dumps(k.dispatch('documents.list', {}, p).get('result'))
print('   “start a page called Bench plan …” ->', [s for s in said(c4, 10) if s.startswith(('Done', 'It was refused'))][:1], '| in Documents:', 'Bench plan' in docs, '| on the Field:', any('Bench plan' in o.title for o in v.field.objects), '| Undo offered:', c4.findChild(QPushButton, 'StagedUndo') is not None); ok &= 'Bench plan' in docs
w.shell2.ask('make a note called Rail idea that says try a ferrite'); settle(400, 6); c5 = cards()[-1]; ideas = _json.dumps(k.dispatch('ideas.list', {}, p).get('result'))
print('   “make a note called Rail idea that says try a ferrite” ->', [s for s in said(c5, 10) if s.startswith(('Done', 'It was refused'))][:1], '| in the records:', 'Rail idea' in ideas); ok &= 'Rail idea' in ideas
stacy_hand.choose(w, 'ask'); face.show_hand(); w.shell2.ask('make a folder called Jig'); settle(300, 5); c6 = cards()[-1]; waits_ = c6.findChild(QPushButton, 'StagedRun')
print('   hand at Ask first, “make a folder called Jig” -> made yet:', has('Jig'), '| Approve shown:', waits_.isVisible()); ok &= not has('Jig') and waits_.isVisible()
QTest.mouseClick(waits_, Qt.LeftButton); settle(300, 5); print('   pressed Approve -> made:', has('Jig')); ok &= has('Jig')
# 5c. what other readers found (0.7.0): an Undo runs only while the thing is still as she made it; a busy Terminal is said; an old step word takes nothing
if hasattr(stacy_hand, 'undo_allowed'):
    stacy_hand.choose(w, 'show'); face.show_hand()
    w.shell2.ask('write a file called Bracket/keep.txt saying one'); settle(300, 5); ck = cards()[-1]; (_fs.root(k) / 'Bracket' / 'keep.txt').write_text('one, and two pages of my own', encoding='utf-8')
    QTest.mouseClick(ck.findChild(QPushButton, 'StagedUndo'), Qt.LeftButton); settle(300, 5)
    print('5c. a file she made, then changed by the owner, then Undo ->', repr(ck.findChild(QPushButton, 'StagedUndo').text()), '| still in Files:', has('Bracket/keep.txt'), '|', said(ck, 14)[-1][:110]); ok &= has('Bracket/keep.txt') and ck.findChild(QPushButton, 'StagedUndo').text() == 'Not undone'
    QTest.mouseClick(c.findChild(QPushButton, 'StagedUndo'), Qt.LeftButton); settle(300, 5); print('   Undo on the folder she made, now with the owner’s file in it ->', repr(c.findChild(QPushButton, 'StagedUndo').text()), '| folder still there:', has('Bracket')); ok &= has('Bracket') and c.findChild(QPushButton, 'StagedUndo').text() == 'Not undone'
    choose(tile('07 Bench readings')); n0 = len(cards()); w.shell2.ask('make a folder called Rev 2'); settle(300, 5); print('   with a sheet selected, “make a folder called Rev 2” -> made:', has('Rev 2'), '|', said(cards()[-1], 1)[0][:70]); ok &= has('Rev 2')
    busy = w.console.process; w.console.process = object(); ran_before = len([e for e in stacy_hand.trail(w.session.state) if e['words'].startswith('Ran in the Terminal')])
    try: w.shell2.ask('run df -h'); settle(200, 3); told = said(cards()[-1], 1)[0][:120]
    finally: w.console.process = busy
    ran_after = len([e for e in stacy_hand.trail(w.session.state) if e['words'].startswith('Ran in the Terminal')]); print('   “run df -h” while a command is still running ->', told, '| written in her trail as run:', ran_after > ran_before); ok &= ran_after == ran_before and 'still running' in told
    w.type_bar.box.clear(); w.type_bar.set_target('slate', focus=False)
    calc = next(o for o in v.field.objects if o.kind == 'calculation'); choose(calc); fp.do(w, calc); n1 = len(cards()); got = fp.take(w, calc, 0, line='/not.the.step {}'); settle(200, 3)
    print('   a step word from an older list ->', got, '|', said(cards()[n1], 1)[0][:80] if len(cards()) > n1 else None); ok &= got is None and len(cards()) > n1 and 'from before' in said(cards()[n1], 1)[0]
    if page.view.reading is not None: page.view.close_reading()
stacy_hand.choose(w, 'free'); face.show_hand()
save('Hand_05_Made_At_Her_Word_%s.png' % tag)
# 6. the trail and the list of what always asks, said in Talk
c = face.say_trail(); settle(100, 3); print('6. the trail:', said(c, 3)); c = face.say_always(); settle(100, 3); print('   what always asks:', said(c, 3)[:2])
m = s2.hand_menu(w, face); print('   the menu:', [a.text() for a in m.actions() if not a.isSeparator()], '| checked:', [a.text() for a in m.actions() if a.isChecked()]); ok &= [a.text() for a in m.actions() if a.isChecked()] == ['Free hand']
save('Hand_04_Trail_%s.png' % tag)
print('HAND PROBE', 'PASS' if ok else 'FAIL')
print('DONE')
