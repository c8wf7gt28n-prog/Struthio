"""Shell-map probe: build the Graphite window offscreen in a disposable home (same holds as tools/desk_review.py),
report the centre/menus/shortcuts facts, mount a placeholder page in the centre and grab the window.
usage: probe.py PROGRAM OUT W H [facts]"""
import json, os, sys, tempfile, subprocess
from pathlib import Path
from unittest.mock import patch
PROGRAM = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve(); W, H = int(sys.argv[3]), int(sys.argv[4])
FACTS = len(sys.argv) > 5
RUN = Path(tempfile.mkdtemp(prefix='graphite-probe-')); HOME = RUN / 'home'; HOME.mkdir()
SCREEN = RUN / 'screen.json'
SCREEN.write_text(json.dumps({'screens': [{'name': 'probe', 'x': 0, 'y': 0, 'width': W, 'height': H, 'logicalDpi': 96, 'logicalBaseDpi': 96, 'dpr': 1.0}]}))
os.environ.update(QT_QPA_PLATFORM='offscreen:configfile=' + str(SCREEN), ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
                  HOME=str(HOME), ARC1_WORKBENCH_CONFIG_HOME=str(RUN / 'profile'), ARC_LEDGER_CONCERN=str(HOME / 'Concern'))
os.environ.pop('ARC_LEDGER_XSESSION', None)
os.chdir(RUN); sys.path.insert(0, str(PROGRAM)); sys.dont_write_bytecode = True
from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QAction, QColor, QFont, QFontDatabase, QPainter, QShortcut
from PySide6.QtWidgets import QMessageBox, QWidget
from PySide6.QtTest import QTest
from workbench.qt_app import make_app, WorkbenchWindow
from workbench import locations, clip, session_power, boss_theme as t
from workbench.engineering_kernel import Kernel
from workbench.session import Session
def held_power(request):
    raise OSError('no login session (held)')
patch.object(clip, '_request', side_effect=AssertionError('No provider request')).start()
patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')).start()
patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')).start()
patch.object(session_power, 'system', side_effect=held_power).start()
patch.object(QMessageBox, 'question', return_value=QMessageBox.No).start()
app = make_app([]); root = locations.office(HOME / 'Concern' / 'Office'); session = Session(RUN / 'profile/session.json', root)
w = WorkbenchWindow(root, session, restore=False)
import platform; platform.processor()
patch.object(subprocess, 'Popen', side_effect=AssertionError('No process start')).start()
patch.object(os, 'system', side_effect=AssertionError('No shell command')).start()
patch.object(QProcess, 'startDetached', side_effect=AssertionError('No detached program')).start()
def settle(ms=60, n=6):
    for name in ('agenda_runner', 'study_idle'):
        obj = getattr(w, name, None)
        if obj and hasattr(obj, 'timer'): obj.timer.stop()
    for _ in range(n): app.processEvents(); QTest.qWait(ms)
def align(times=3):
    bar = getattr(w, 'type_bar', None)
    for _ in range(times):
        if bar is not None: bar.align()
        settle(25, 3)
def save(widget, name):
    assert widget.grab().save(str(OUT / name), 'PNG'); print('saved', OUT / name, widget.width(), 'x', widget.height())
w.resize(W, H); w.show(); settle(); align()

def stack_report(tag):
    s = w.central_stack
    print(tag, '| stack:', [type(s.widget(i)).__name__ for i in range(s.count())], '| current:', type(s.currentWidget()).__name__,
          '| _home_active:', w._home_active, '| title:', w.windowTitle())

class Placeholder(QWidget):
    """A trivial centre page: one line of text painted on the desk ground."""
    def __init__(self, host):
        super().__init__(); self.host = host; self.setObjectName('FieldProbe'); self.setProperty('paperFunctionalInk', True)
        self.setFocusPolicy(Qt.StrongFocus); self.setAccessibleName('Field probe page')
    def title(self): return 'Field'
    def info(self): return 'Field · probe page'
    def paintEvent(self, event):
        p = QPainter(self); p.fillRect(self.rect(), QColor(t.TERMINAL_GROUND))
        f = QFont('IBM Plex Mono'); f.setPixelSize(18); p.setFont(f); p.setPen(QColor(t.AMBER_TEXT))
        p.drawText(24, 40, '[ FIELD PROBE ]  centre page %d x %d  mounted in central_stack' % (self.width(), self.height()))
        p.setPen(QColor(t.LINE_STRONG)); p.drawRect(self.rect().adjusted(0, 0, -1, -1)); p.end()


# ---- in-memory recipe: one Work-menu action with a key, also reachable by typing (nothing in the tree is edited) ----
from workbench import menus2
page = Placeholder(w); w.central_stack.addWidget(page); shown = []
def show_field():
    if w._home_active: w._close_start()
    w.central_stack.setCurrentWidget(page); w.context_bar.hide(); w.doc_info.hide(); w.setWindowTitle('Field — Graphite'); page.setFocus(); shown.append(1)
def leave_field():
    if w.central_stack.currentWidget() is page: w.central_stack.setCurrentWidget(w.workspace_split); w.update_document_info()
a = QAction('Field', w); a.setShortcut('F6'); a.setToolTip('Open the field (F6)'); a.triggered.connect(lambda checked=False: show_field()); w.addAction(a); w.a_field = a
work = w.menu_groups['File']
work.addAction(a); print('1 added straight to the QMenu -> in Work:', a in work.actions())
menus2.rebuild(w); print('2 after menus2.rebuild -> in Work:', a in work.actions(), '(rebuild empties every group and refills it from its lists)')
# the list-driven route, emulated: the key in menus2.FILE and the action where rebuild looks keys up
w.favorite_actions['field'] = a; old = list(menus2.FILE); menus2.FILE.insert(menus2.FILE.index('@recent') + 1, 'field')
menus2.rebuild(w); menus2.rebuild(w)
rows = [x.text().split('\t')[0].replace('&', '') for x in work.actions() if not x.isSeparator()]
print('3 key in menus2.FILE + action in the lookup -> in Work:', a in work.actions(), '| position', rows.index('Field'), 'of', len(rows), '| rows:', rows)
print('4 typed: OneBox.commands("field") ->', [(l, h) for l, h, f in w.shell2.top.box.commands('field')])
w.activateWindow(); w.tabs.setFocus(); settle(20, 2)
QTest.keyClick(w, Qt.Key_F6); settle(30, 3)
print('5 F6 pressed -> triggered:', bool(shown), '| centre current:', type(w.central_stack.currentWidget()).__name__, '| ambiguous shortcuts:', [x.text() for x in w.findChildren(QAction) if x is not a and any(s.toString() == 'F6' for s in x.shortcuts())])
hint, fn = [(h, f) for l, h, f in w.shell2.top.box.commands('field') if l == 'Field'][0]
leave_field(); settle(20, 2); print('6 left ->', type(w.central_stack.currentWidget()).__name__, '| title:', w.windowTitle())
fn(); settle(20, 2); print('7 typed command run -> centre current:', type(w.central_stack.currentWidget()).__name__, '| hint shown beside it:', hint)
# auto-return when something opens a tab: tabs.currentChanged fires only when the current tab changes
w.tabs.currentChanged.connect(lambda i: leave_field())
before = w.tabs.currentIndex(); w.show_files(); settle(20, 2)
print('8 show_files with Files already current -> index changed:', before != w.tabs.currentIndex(), '| centre current:', type(w.central_stack.currentWidget()).__name__)
from workbench.shell2 import open_destination
open_destination(w, 'library:all'); settle(40, 3)
print('9 a NEW tab opened (Library) with currentChanged hooked -> centre current:', type(w.central_stack.currentWidget()).__name__, '| tabs:', [w.tabs.tabText(i) for i in range(w.tabs.count())])
menus2.FILE[:] = old; w.favorite_actions.pop('field', None)
w._closing = True; print('DONE')
