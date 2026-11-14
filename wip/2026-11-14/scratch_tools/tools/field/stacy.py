"""Orchestrator's probe of STACY AS THE ASSISTANT: the real Graphite window on a disposable copy of the restored After Hours 07 workspace,
with the project's usual holds (no worker launch, no job submission, no provider request, no session or power command,
no child process). Opens the Field by its menu action, walks it by keyboard, opens a record with Enter, comes back."""
import json, os, sys, tempfile, shutil, subprocess
from pathlib import Path
from unittest.mock import patch
S = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad')
PROGRAM = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve(); W, H = int(sys.argv[3]), int(sys.argv[4]); CASE = len(sys.argv) < 6 or sys.argv[5] != 'empty'
RUN = Path(tempfile.mkdtemp(prefix='run-', dir=str(S / 'tools/field/run'))); HOME = RUN / 'home'; HOME.mkdir()
if CASE:
    shutil.copytree(S / 'work/demo/After_Hours_07', RUN / 'ws'); shutil.copytree(S / 'work/demo/After_Hours_07-profile', RUN / 'prof')
SCREEN = RUN / 'screen.json'
SCREEN.write_text(json.dumps({'screens': [{'name': 'shot', 'x': 0, 'y': 0, 'width': W, 'height': H, 'logicalDpi': 96, 'logicalBaseDpi': 96, 'dpr': 1.0}]}))
os.environ.update(PYTHONDONTWRITEBYTECODE='1', QT_QPA_PLATFORM='offscreen:configfile=' + str(SCREEN), ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
                  HOME=str(HOME), ARC1_WORKBENCH_CONFIG_HOME=str(RUN / ('prof' if CASE else 'profile')), ARC_LEDGER_CONCERN=str(HOME / 'Concern'))
if CASE: os.environ['ARC_LEDGER_WORKSPACE'] = str(RUN / 'ws')
os.environ.pop('ARC_LEDGER_XSESSION', None)
os.chdir(RUN); sys.path.insert(0, str(PROGRAM)); sys.dont_write_bytecode = True
from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import QMessageBox
from PySide6.QtTest import QTest
from workbench.qt_app import make_app, WorkbenchWindow
from workbench import locations, clip, session_power
from workbench.engineering_kernel import Kernel
from workbench.session import Session
patch.object(clip, '_request', side_effect=AssertionError('No provider request')).start()
patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')).start()
patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')).start()
patch.object(session_power, 'system', side_effect=OSError('no login session (held)')).start()
patch.object(QMessageBox, 'question', return_value=QMessageBox.No).start()
app = make_app([])
if CASE: root = RUN / 'ws'; session = Session(RUN / 'prof/session.json', root)
else: root = locations.office(HOME / 'Concern' / 'Office'); session = Session(RUN / 'profile/session.json', root)
w = WorkbenchWindow(root, session, restore=False)
import platform; platform.processor()
patch.object(subprocess, 'Popen', side_effect=OSError('No process start (held)')).start()
patch.object(os, 'system', side_effect=AssertionError('No shell command')).start()
patch.object(QProcess, 'startDetached', side_effect=AssertionError('No detached program')).start()
def settle(ms=50, n=6):
    for name in ('agenda_runner', 'study_idle'):
        obj = getattr(w, name, None)
        if obj and hasattr(obj, 'timer'): obj.timer.stop()
    for _ in range(n): app.processEvents(); QTest.qWait(ms)
def align(times=3):
    bar = getattr(w, 'type_bar', None)
    for _ in range(times):
        if bar is not None: bar.align()
        settle(25, 3)
def save(name):
    align(); assert w.grab().save(str(OUT / name), 'PNG'); print('saved', name)
def where(tag):
    cur = w.central_stack.currentWidget(); tab = w.tabs.currentWidget()
    print('%-28s centre=%s field=%s home=%s title=%r tab=%s' % (tag, type(cur).__name__, w._field_active, w._home_active, w.windowTitle(), type(tab).__name__ if tab else None))
tag = '%dx%d' % (W, H)
from workbench import boss_qt, context_menu
w.resize(W, H); w.show(); w.activateWindow(); settle(); align()
face = w.shell2.face; bar = w.type_bar
def bubbles():
    return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def last_words(card):
    from PySide6.QtWidgets import QLabel
    return [l.text().replace('​', '')[:150] for l in card.findChildren(QLabel)]
# 1. her face and name in Talk, in each desk-art mode
w.shell2.show_slate_face(); settle(); align()
for mode in ('illustrated', 'ascii', 'clean'):
    boss_qt.choose_art(w, mode); settle(10, 3)
    print('%-11s face shown: %-5s size %dx%d | name: %r | line under it: %r | accessible: %r' % (mode, face.portrait.isVisible(), face.portrait.width(), face.portrait.height(), face.signature.text(), face.model.text(), face.portrait.accessibleName()))
    save('Graphite_Stacy_01_Talk_%s_%s.png' % (mode, tag))
boss_qt.choose_art(w, 'illustrated'); settle(10, 3)
# 2. not in the Field, no model: the old honest words, in her voice
w.shell2.ask('hello'); settle(); print('plain question, no Field:', last_words(bubbles()[-1])[:2])
# 3. in the Field: Ask Stacy about a calculation from its menu, finish the question in the line, Enter
w.a_field.trigger(); settle(); v = w.field_page.view
calc = next(o for o in v.field.objects if o.kind == 'calculation'); v.field.select(calc.id); v.update(); settle(5, 2)
target = context_menu.find_field(w, v, v.sheet_rect(calc.id).center().toPoint()) if hasattr(context_menu, 'find_field') else None
entries = context_menu.field_entries(w, target) if target is not None else []
ask = next(e for e in entries if e.key == 'field:ask'); print('menu word:', ask.label)
ask.run() if hasattr(ask, 'run') else ask.action()
settle(); print('line after choosing it: %r | target: %s | Field in front: %s' % (bar.box.text(), getattr(bar, 'target', None), w._field_active))
QTest.keyClicks(bar.box, 'what went into this?'); QTest.keyClick(bar.box, Qt.Key_Return); settle(80, 6)
card = bubbles()[-1]; words = last_words(card)
print('Field still in front: %s | right pane on Talk: %s | answered in staC: %s | ran: %s' % (w._field_active, w.console_pages.currentWidget() is face, getattr(card, 'stac', None) == calc.stac, getattr(card, 'answered', None)))
for line in words: print('   |', line)
save('Graphite_Stacy_02_Answers_In_staC_%s.png' % tag)
# 4. the selected sheet is "what is open": a question typed with no menu at all
finding = next(o for o in v.field.objects if o.kind == 'finding'); v.field.select(finding.id); v.update(); settle(5, 2)
w.shell2.ask('why do we believe this?'); settle(80, 6); card = bubbles()[-1]
print('typed with a finding selected: answered in staC: %s | ran: %s | Field in front: %s' % (getattr(card, 'stac', None) == finding.stac, getattr(card, 'answered', None), w._field_active))
for line in last_words(card)[:4]: print('   |', line)
save('Graphite_Stacy_03_Finding_%s.png' % tag)
# 5. the keyboard: Esc in the strip gives it back to the Field
bar.box.setFocus(); settle(5, 2); QTest.keyClick(bar.box, Qt.Key_Escape); settle(10, 2); print('after Esc in the strip, keyboard in:', type(app.focusWidget()).__name__)
w._closing = True; print('DONE')
