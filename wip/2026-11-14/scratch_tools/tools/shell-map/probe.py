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

if FACTS:
    from workbench.project_context import detached
    print('detached(root):', detached(w.root), '| root:', w.root.name, '| has shell2:', hasattr(w, 'shell2'))
    stack_report('after build')
    print('home_page:', type(w.home_page).__name__, '| _empty_home_page:', type(getattr(w, '_empty_home_page', None)).__name__,
          '| finder:', type(getattr(w, 'finder', None)).__name__)
    page = w.show_start(); settle()
    stack_report('after show_start')
    print('show_start returned:', type(page).__name__, '| page.today:', type(getattr(page, 'today', None)).__name__,
          '| page.today.art:', type(getattr(getattr(page, 'today', None), 'art', None)).__name__,
          '| home_page:', type(w.home_page).__name__, '| _empty_home_page:', type(getattr(w, '_empty_home_page', None)).__name__,
          '| finder is page:', getattr(w, 'finder', None) is page, '| page.place:', getattr(page, 'place', None))
    w.resume_workspace(); settle()
    stack_report('after resume_workspace')
    print('tabs:', [(type(w.tabs.widget(i)).__name__, w.tabs.tabText(i)) for i in range(w.tabs.count())])
    print('centre layout order:', [(type(w.center_layout.itemAt(i).widget()).__name__, w.center_layout.itemAt(i).widget().objectName(),
                                    w.center_layout.itemAt(i).widget().isVisible()) for i in range(w.center_layout.count()) if w.center_layout.itemAt(i).widget()])
    print('session desk_art:', w.session.state.get('desk_art', '(unset -> illustrated)'), '| reading_profile.reduce_motion:', w.reading_profile.get('reduce_motion'),
          '| ui_pt:', w.reading_profile.get('ui_pt'))
    fams = set(QFontDatabase.families())
    print('fonts present:', {n: (n in fams) for n in ('IBM Plex Mono', 'IBM Plex Sans', 'DejaVu Sans Mono')})
    # menus
    print('menu_groups:', {k: m.title() for k, m in w.menu_groups.items()})
    from workbench.menus2 import direct_actions
    print('Work (File) rows:', [a.text() for a in w.menu_groups['File'].actions() if not a.isSeparator()])
    print('Arrange (Options) rows:', [a.text() for a in w.menu_groups['Options'].actions() if not a.isSeparator()])
    top = w.shell2.top
    print('top bar words:', top.more_menus.text(), '|', top.programs.text(), '|', type(top.system).__name__, repr(top.system.text()))
    top.fill_more_menus(); print('Work▾ popup holds:', [a.text() for a in top.more_menus.menu().actions()])
    # shortcuts
    rows = {}
    for a in w.findChildren(QAction):
        for s in a.shortcuts():
            k = s.toString()
            if k: rows.setdefault(k, []).append('A:' + a.text().replace('&', '').split('\t')[0])
    for s in w.findChildren(QShortcut):
        k = s.key().toString()
        if k: rows.setdefault(k, []).append('S:' + (type(s.parent()).__name__))
    def order(k): return (k.count('+'), k)
    for k in sorted(rows, key=order): print('  KEY %-18s %s' % (k, ' ; '.join(sorted(set(rows[k])))))
    # typed command
    box = top.box
    for q in ('today', 'files', 'full screen', 'reset window'):
        print('commands(%r):' % q, [(l, h) for l, h, f in box.commands(q)][:6])
    print('len(host.actions()):', len(w.actions()))

# ---- mount proof -------------------------------------------------------------------------------------------------
page = Placeholder(w)
w.central_stack.addWidget(page)                      # (b1) add
if w._home_active: w._close_start()                  # leave Home first so its saved dock state is restored once
w.central_stack.setCurrentWidget(page)               # (b2) bring to front
w.context_bar.hide(); w.doc_info.hide()              # what show_start hides for a full-surface page
w.setWindowTitle('Field — Graphite'); page.setFocus(); settle(); align()
stack_report('page in front')
print('page geometry in window:', page.mapTo(w, page.rect().topLeft()).toTuple(), page.size().toTuple(), '| visible:', page.isVisible(),
      '| nav_dock w:', w.nav_dock.width(), w.nav_dock.isVisible(), '| sim_dock w:', w.sim_dock.width(), w.sim_dock.isVisible())
save(w, 'Probe_centre_page_%dx%d.png' % (W, H))
save(page, 'Probe_centre_page_only_%dx%d.png' % (W, H))
if FACTS:
    # does an ordinary "open a room" route bring the workspace back while _home_active is False?
    w._close_start(); settle(20, 2); stack_report('after _close_start (flag False)')
    w.show_files() if hasattr(w, 'show_files') else None; settle(); stack_report('after show_files (flag False)')
    w.central_stack.setCurrentWidget(page); settle(20, 2)
    w.show_start(); settle(); stack_report('after show_start over page')
    w.central_stack.setCurrentWidget(page); settle(20, 2); stack_report('page over Home (flag True)')
    w._close_start(); settle(); stack_report('after _close_start (flag True)')
    # as a tab instead
    w.tabs.addTab(page, page.title()); w.tabs.setCurrentWidget(page); settle(); align()
    stack_report('page as a tab'); print('tab bar visible:', w.tabs.tabBar().isVisible(), '| doc_info:', w.doc_info.text())
    save(w, 'Probe_tab_page_%dx%d.png' % (W, H))
w._closing = True
print('DONE')
