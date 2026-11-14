# The first journey: "start a Godot project called Lander". The files under her hand, the room's read, Undo, the open step.
import shutil, subprocess
from PySide6.QtWidgets import QLabel, QPushButton
from workbench import stacy_hand, stacy_start, program_build, files_service as _fs
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face; ok = True
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=30): return [l.text().replace('​', '')[:260].replace('\n', ' / ') for l in card.findChildren(QLabel)][:n]
def has(path): return bool(k.dispatch('files.get', {'path': path}, p).get('ok'))
root = _fs.root(k)
print('her hand:', stacy_hand.level(w), '| Godot here:', stacy_start.godot_tool())
# 1. Do and show: the project is made at once
before = len(cards()); w.shell2.ask('start a Godot project called Lander'); settle(600, 8); new = cards()[before:]
plan = next(c for c in new if hasattr(c, 'plan')); after = new[-1]
files = sorted(f.name for f in (root / 'Lander').iterdir()) if (root / 'Lander').is_dir() else []
print('1. asked “start a Godot project called Lander” ->', said(plan, 1)[0][:150]); print('   in Files/Lander:', files, '| Undo on the card:', plan.findChild(QPushButton, 'StagedUndo') is not None)
print('   she said:', said(after, 2)[0][:330]); print('   ways in:', [l.text()[:0] or __import__('re').sub('<[^>]+>', '', l.text()) for l in after.findChildren(QLabel)][-1][:120])
ok &= files == ['START_HERE.md', 'main.gd', 'main.tscn', 'project.godot'] and plan.findChild(QPushButton, 'StagedUndo') is not None and 'reads it as the project “Lander”' in said(after, 2)[0]
trail = stacy_hand.trail(w.session.state); print('   her trail:', [(e['words'], e['state'], bool(e['undo'])) for e in trail[:2]]); ok &= len(trail) == 1 and trail[0]['undo'].startswith('/files.trash')
links = next(l for l in reversed(after.findChildren(QLabel)) if getattr(l, '_actions', None) and 'script' in l._actions); tabs_before = w.tabs.count()
links._actions['script'][1](); settle(500, 6); opened = w.tabs.currentWidget()
print('   “Read main.gd here” -> a view opened:', w.tabs.count() > tabs_before or type(opened).__name__, '|', type(opened).__name__, '|', str(getattr(opened, 'root_path', ''))[-20:]); ok &= str(getattr(opened, 'root_path', '')).endswith('Lander/main.gd')
save('Start_00_Made_%s.png' % tag)
engine = shutil.which('godot3-server') or shutil.which('godot3')
if engine and stacy_start.godot_tool()['major'] == 3:
    out = subprocess.run([engine, '--path', str(root / 'Lander'), '-s', '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/godot_try/probe3.gd'], capture_output=True, text=True, timeout=120)
    lines = [l for l in (out.stdout + out.stderr).splitlines() if 'PROBE' in l or 'ERROR' in l]; print('   the files Graphite wrote, run in the real Godot 3 engine:', lines[:3]); ok &= any('Lander: it runs' in l for l in lines) and not any('ERROR' in l for l in lines)
else: print('   no Godot 3 engine on this machine to run the files in')
# 2. the same name again is refused; Undo moves the folder to the Trash
w.shell2.ask('start a Godot project called Lander'); settle(300, 5); print('2. asked again ->', said(cards()[-1], 1)[0][:120]); ok &= 'already' in said(cards()[-1], 1)[0]
QTest.mouseClick(plan.findChild(QPushButton, 'StagedUndo'), Qt.LeftButton); settle(400, 6); trash = [x['original'] for x in k.dispatch('files.trash_list', {}, p)['result']['trash']]
print('   Undo -> in Files:', has('Lander'), '| in the Trash:', trash[:2], '| she said:', said(plan, 40)[-1][:90]); ok &= not has('Lander') and 'Lander' in trash
# 2b. what another reader found (0.7.0): a courtesy is not part of the name; a reserved name is refused; the Undo leaves a project the owner has worked in
if hasattr(stacy_start, 'reserved'):
    w.shell2.ask('start a Godot project called Kite, please'); settle(600, 8); kite = next(c_ for c_ in reversed(cards()) if hasattr(c_, 'plan'))
    print('2b. “… called Kite, please” -> folders:', [n_ for n_ in ('Kite', 'Kite, please') if has(n_)]); ok &= has('Kite/project.godot') and not has('Kite, please')
    w.shell2.ask('start a Godot project called Exports'); settle(300, 5); print('   “… called Exports” ->', said(cards()[-1], 1)[0][:90], '| made:', has('Exports')); ok &= not has('Exports') and 'keeps' in said(cards()[-1], 1)[0]
    (root / 'Kite' / 'player.gd').write_text('extends Node2D\n', encoding='utf-8')
    QTest.mouseClick(kite.findChild(QPushButton, 'StagedUndo'), Qt.LeftButton); settle(400, 6)
    print('   the owner adds a script, then Undo ->', repr(kite.findChild(QPushButton, 'StagedUndo').text()), '| project still in Files:', has('Kite/player.gd'), '|', said(kite, 40)[-1][:120]); ok &= has('Kite/player.gd') and kite.findChild(QPushButton, 'StagedUndo').text() == 'Not undone'
# 3. with Godot on the computer: the open step waits at Do and show, and is hers with a free hand
started = []
real_tool, real_start, real_gt = program_build._tool, program_build._start, stacy_start.godot_tool
program_build._tool = lambda room: {'name': 'Godot', 'available': True, 'executable': '/usr/bin/godot3'}
program_build._start = lambda command, cwd: started.append(command) or 4242
stacy_start.godot_tool = lambda *a, **kw: {'available': True, 'command': 'godot3', 'executable': '/usr/bin/godot3', 'major': 3}
try:
    w.shell2.ask('get me started on a project in Godot called Rail Runner'); settle(600, 8); c = cards()[-1]; approve = c.findChild(QPushButton, 'StagedRun')
    print('3. Godot present, hand at Do and show ->', said(c, 1)[0][:150], '| Approve shown:', approve is not None and approve.isVisible(), '| started yet:', started); ok &= approve is not None and approve.isVisible() and not started
    QTest.mouseClick(approve, Qt.LeftButton); settle(400, 6); print('   pressed Approve -> Godot asked to start with:', [str(x).replace(str(root), 'Files') for x in started[-1]] if started else None); ok &= bool(started) and started[-1][0] == '/usr/bin/godot3' and '--editor' in started[-1]
    stacy_hand.choose(w, 'free'); face.show_hand(); n = len(started); w.shell2.ask('start a Godot project called Free Flight'); settle(600, 8)
    print('   hand free -> made:', has('Free Flight/project.godot'), '| Godot asked to start by herself:', len(started) == n + 1); ok &= has('Free Flight/project.godot') and len(started) == n + 1
    opened = said(cards()[-1], 12); print('   and she said:', [s_ for s_ in opened if s_.startswith('Done')][:1], '| a line about Undo on opening a program:', any('no exact Undo' in s_ for s_ in opened)); ok &= any(s_.startswith('Done: its own window was started') for s_ in opened) and not any('no exact Undo' in s_ for s_ in opened)
    save('Start_01_Open_In_Godot_%s.png' % tag)
    # 4. Ask first: nothing is made until Approve
    stacy_hand.choose(w, 'ask'); face.show_hand(); before = len(cards()); w.shell2.ask('make me a Godot game called Slow Start'); settle(400, 6); c = next(c_ for c_ in cards()[before:] if hasattr(c_, 'plan')); run = c.findChild(QPushButton, 'PlanRun')
    print('4. hand at Ask first ->', said(c, 1)[0][-90:], '| made yet:', has('Slow Start'), '| button:', run.text()); ok &= not has('Slow Start') and run.isVisible()
    QTest.mouseClick(run, Qt.LeftButton); settle(600, 8); print('   pressed it -> made:', has('Slow Start/project.godot'), '| an Undo on what you approved yourself:', c.findChild(QPushButton, 'StagedUndo') is not None); ok &= has('Slow Start/project.godot')
finally:
    program_build._tool, program_build._start, stacy_start.godot_tool = real_tool, real_start, real_gt
print('the Godot room looks for:', [c_ for c_ in ('godot4', 'godot', 'godot3')], '| its own read of availability here:', program_build._tool('godot'))
print('START PROBE', 'PASS' if ok else 'FAIL')
print('DONE')
