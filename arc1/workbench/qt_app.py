"""ARC-1 Workbench R08 — Qt 6 experimental desktop shell.

Human UI uses PySide6; the original R07 command/agent/host backend is reused.
No physical board detection, NOR writing, or real-time game hardware is claimed.
Qt execution must be qualified on native Windows 11 before replacing Tk R07.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import tempfile

from PySide6.QtCore import QProcess, QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QFont, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QDockWidget, QFileDialog, QFileSystemModel, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QMainWindow, QMenu, QMessageBox,
    QPlainTextEdit, QPushButton, QSizePolicy, QSplitter, QStatusBar, QTabWidget, QToolBar,
    QTreeView, QVBoxLayout, QWidget,
)

from .bootlogic import BootModel
from .cartridge import CartridgeError, inspect_cartridge, package_game, simulate_stream
from .launcher import HostLauncher, LauncherError, games_on_shelf, prepare
from .qt_theme import QSS
from .qt_contract import editable_file, verify_drop
from .output_router import OutputRouter

ROOT = Path(__file__).resolve().parents[1]
EDIT_EXT = {'.c', '.h', '.s', '.py', '.md', '.json', '.txt', '.ld', '.cmd', '.sh', '.yaml', '.yml'}
ACTIONS = {
    'Build F133 link-stage': ['firmware', 'image', '--target', 'f133'],
    'Build D213 link-stage': ['firmware', 'image', '--target', 'd213'],
    'Build both link-stages': ['firmware', 'image', '--target', 'all'],
    'Firmware tests': ['firmware', 'test'],
    'Build host game': ['build', 'examples/hello_arc1'],
    'Game tests': ['test', 'examples/hello_arc1'],
    'Check hardware manifest': ['hw', 'inspect'],
    'Brand verification': ['brand'],
    'System check': ['doctor'],
}




class DropShelf(QListWidget):
    """Explorer/Finder-style external drag-to-copy, never a silent overwrite."""
    def __init__(self, parent, import_cb):
        super().__init__(parent)
        self.import_cb = import_cb
        self.setAcceptDrops(True)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if len(urls) == 1 and urls[0].isLocalFile() and urls[0].toLocalFile().lower().endswith('.arc1cart'):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if len(urls) != 1 or not urls[0].isLocalFile():
            event.ignore(); return
        self.import_cb(Path(urls[0].toLocalFile()))
        event.acceptProposedAction()


class WorkbenchQt(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ARC-1 Workbench R09 — Qt engineering preview')
        self.resize(1480, 920)
        self.setMinimumSize(980, 610)
        self.setDockNestingEnabled(True)
        self.setAcceptDrops(False)
        self.settings = QSettings('ARC Concern', 'ARC-1 Workbench Qt Preview')
        self.documents = {}
        self.router = OutputRouter()
        self.current_sim = HostLauncher(ROOT)
        self.boot = BootModel()
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(ROOT))
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_process)
        self.process.finished.connect(self._process_finished)
        self.command_name = ''
        self.launch_last_state = None
        self._construct_central()
        self._construct_docks()
        self._construct_actions()
        self._construct_toolbar()
        self._construct_menus()
        self._construct_status()
        self.refresh_shelf()
        self.refresh_boot()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_sim)
        self.timer.start(140)
        self.open_source(ROOT/'firmware'/'stage'/'f133_stage.c')
        self._restore_layout()

    def _construct_central(self):
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.setCentralWidget(self.tabs)

    def _dock(self, title, name, widget, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(name)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def _construct_docks(self):
        self.file_model = QFileSystemModel(self)
        self.file_model.setRootPath(str(ROOT))
        self.file_model.setReadOnly(True)
        self.tree = QTreeView()
        self.tree.setModel(self.file_model)
        self.tree.setRootIndex(self.file_model.index(str(ROOT)))
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        for col in (1, 2, 3):
            self.tree.hideColumn(col)
        self.tree.doubleClicked.connect(self._tree_activated)
        self.file_dock = self._dock('PROJECT FILES', 'FilesDock', self.tree, Qt.LeftDockWidgetArea)
        self.file_dock.setMinimumWidth(155)
        self.file_dock.resize(245, 550)

        # Bottom dock is collapsible (F10) and opens on demand for build activity.
        self.output_tabs = QTabWidget()
        self.output_tabs.setObjectName('OutputTabs')
        self.output = QPlainTextEdit()
        self.output.setObjectName('console')
        self.output.setReadOnly(True)
        self.output.document().setMaximumBlockCount(6000)
        self.output.setFont(QFont('Consolas', 9))
        self.output.setPlainText('ARC-1 Workbench R09 / PC HOST\n'
                                 'COMPILER OUTPUT ONLY · BOARD OFFLINE\n')
        self.build_view = QPlainTextEdit()
        self.build_view.setReadOnly(True)
        self.build_view.setObjectName('console')
        self.build_view.setPlainText('No build has been run in this session.')
        self.problem_view = QPlainTextEdit()
        self.problem_view.setObjectName('problems')
        self.problem_view.setReadOnly(True)
        self.problem_view.setPlainText('No build diagnostics yet. Run a build to analyze compiler messages.')
        self.debug_view = QPlainTextEdit()
        self.debug_view.setReadOnly(True)
        self.debug_view.setPlainText('Host simulation debugger: see the Cartridge pane for game execution.\n'
            'Hardware registers, breakpoints and device traces are NOT connected.')
        self.agent_view = QPlainTextEdit()
        self.agent_view.setReadOnly(True)
        self.agent_view.setPlainText('AI agents use: python arc1 agent\n\n'
            'The separate JSON-lines API does not yet publish shared live activity into this window.\n'
            'No agent activity is fabricated here. See docs/AGENT_INTERFACE_R07.md.')
        for title, widget in [('Console',self.output), ('Build Output',self.build_view), ('Problems',self.problem_view),
                              ('Debug',self.debug_view), ('Agent Activity',self.agent_view)]:
            self.output_tabs.addTab(widget,title)
        self.console_dock = self._dock('OUTPUT · F10', 'ConsoleDock', self.output_tabs, Qt.BottomDockWidgetArea)
        self.console_dock.setMinimumHeight(65)
        self.console_dock.resize(800, 155)

        inspector = QWidget()
        iv = QVBoxLayout(inspector)
        iv.setContentsMargins(8, 8, 8, 8)
        iv.setSpacing(7)
        self.lcd = QLabel('ARC-1 START\nHOST SIM ONLY')
        self.lcd.setObjectName('lcd')
        self.lcd.setAlignment(Qt.AlignCenter)
        self.evidence = QLabel('BOARD OFFLINE')
        self.evidence.setObjectName('evidence')
        self.evidence.setAlignment(Qt.AlignCenter)
        self.inspector = QPlainTextEdit()
        self.inspector.setObjectName('inspector')
        self.inspector.setReadOnly(True)
        self.inspector.setFont(QFont('Consolas', 9))
        iv.addWidget(self.lcd)
        iv.addWidget(self.evidence)
        iv.addWidget(self.inspector, 1)
        advance = QPushButton('Advance host diagnostic')
        advance.clicked.connect(self.advance_boot)
        reset = QPushButton('Reset diagnostic')
        reset.clicked.connect(self.reset_boot)
        iv.addWidget(advance)
        iv.addWidget(reset)
        self.inspector_dock = self._dock('INSPECTOR · LCD', 'InspectorDock', inspector, Qt.RightDockWidgetArea)
        self.inspector_dock.setMinimumWidth(200)
        self.inspector_dock.resize(260, 400)

        shelf_widget = QWidget()
        sv = QVBoxLayout(shelf_widget)
        sv.setContentsMargins(7, 7, 7, 7)
        sv.setSpacing(5)
        self.shelf = DropShelf(self, self.import_cartridge)
        sv.addWidget(QLabel('Verified cartridges · drag a .arc1cart here'))
        sv.addWidget(self.shelf, 1)
        self.shelf.itemDoubleClicked.connect(lambda _: self.inspect_selected())
        self.preview = QLabel('Frame preview appears after host launch')
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(105)
        self.preview.setStyleSheet('background:#1c2024; color:#bcbdbd; border:1px solid #5b4d42;')
        sv.addWidget(self.preview)
        row = QHBoxLayout()
        for label, cb in [('Inspect', self.inspect_selected), ('Run host', self.launch_selected), ('Stop', self.stop_sim)]:
            b = QPushButton(label)
            b.clicked.connect(cb)
            row.addWidget(b)
        sv.addLayout(row)
        self.game_dock = self._dock('GAME CARTRIDGE · HOST', 'CartridgeDock', shelf_widget, Qt.RightDockWidgetArea)
        self.tabifyDockWidget(self.inspector_dock, self.game_dock)
        self.inspector_dock.raise_()

    def _action(self, text, callback, shortcut=None, checkable=False):
        a = QAction(text, self)
        a.triggered.connect(callback)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
            a.setShortcutContext(Qt.ApplicationShortcut)
        a.setCheckable(checkable)
        return a

    def _construct_actions(self):
        self.a_open = self._action('Open file…', self.open_dialog, 'Ctrl+O')
        self.a_save = self._action('Save', self.save_source, 'Ctrl+S')
        self.a_saveall = self._action('Save all', self.save_all, 'Ctrl+Shift+S')
        self.a_find = self._action('Find…', self.find_text, 'Ctrl+F')
        self.a_replace = self._action('Replace…', self.replace_text, 'Ctrl+H')
        self.a_quick = self._action('Quick open…', self.quick_open, 'Ctrl+P')
        self.a_commands = self._action('Command palette…', self.command_palette, 'Ctrl+Shift+P')
        self.a_build = self._action('Build link-stage F133+D213', lambda: self.run_cmd('Build both link-stages'), 'F5')
        self.a_test = self._action('Run firmware tests', lambda: self.run_cmd('Firmware tests'), 'F7')
        self.a_host = self._action('Build host game', lambda: self.run_cmd('Build host game'))
        self.a_launch = self._action('Launch host simulation', self.launch_selected, 'F6')
        self.a_stop = self._action('Stop host simulation', self.stop_sim)
        self.a_package = self._action('Package local example cartridge', self.package_example)
        self.a_import = self._action('Import cartridge…', self.import_dialog)
        self.a_inspect = self._action('Inspect selected cartridge', self.inspect_selected)
        self.a_stream = self._action('Model cartridge streaming', self.stream_selected)
        self.a_output = self._action('Show / hide output panel', self.toggle_output, 'F10')
        self.a_problems = self._action('Problems', self.show_problems)
        self.a_help = self._action('About & limitations', self.show_about, 'F1')
        self.a_code = self._action('Code workspace', lambda: self.workspace('Code'))
        self.a_cart = self._action('Cartridge workspace', lambda: self.workspace('Cartridge'))
        self.a_debug = self._action('Debug workspace', lambda: self.workspace('Debug'))

    def _construct_toolbar(self):
        toolbar = QToolBar('Actions', self)
        toolbar.setObjectName('MainToolbar')
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(15,15))
        self.addToolBar(toolbar)
        self.tool = toolbar
        brand = QLabel()
        brand.setObjectName('brandLabel')
        logo = QPixmap(str(ROOT/'workbench'/'logo_compact.png'))
        if not logo.isNull():
            brand.setPixmap(logo.scaledToHeight(30, Qt.SmoothTransformation))
        else:
            brand.setText('ARC-1')
        toolbar.addWidget(brand)
        label = QLabel('  WORKBENCH  |  R09 QT PREVIEW    ')
        label.setStyleSheet('color:#e8e0d8; font-weight:600; letter-spacing:1px;')
        toolbar.addWidget(label)
        toolbar.addSeparator()
        for a in (self.a_open, self.a_save, self.a_build, self.a_test, self.a_launch):
            toolbar.addAction(a)
        toolbar.addSeparator()
        toolbar.addAction(self.a_commands)
        toolbar.addAction(self.a_output)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        offline = QLabel('HOST ONLY  ·  HARDWARE OFFLINE')
        offline.setObjectName('evidence')
        toolbar.addWidget(offline)

    def _construct_menus(self):
        menubar = self.menuBar()
        for name, actions in (
            ('File', [self.a_open, self.a_quick, self.a_save, self.a_saveall]),
            ('Edit', [self.a_find, self.a_replace]),
            ('Build', [self.a_build, self.a_test, self.a_host]),
            ('Cartridge', [self.a_package, self.a_import, self.a_inspect, self.a_stream, self.a_launch, self.a_stop]),
            ('View', [self.a_code, self.a_cart, self.a_debug, self.a_output, self.a_problems]),
            ('Tools', [self.a_commands]),
            ('Help', [self.a_help]),
        ):
            menu = menubar.addMenu(name)
            for action in actions:
                menu.addAction(action)
        view = next((menu for menu in menubar.findChildren(QMenu) if menu.title() == 'View'), None)
        if view:
            view.addSeparator()
            for dock in (self.file_dock,self.inspector_dock,self.game_dock,self.console_dock):
                view.addAction(dock.toggleViewAction())

    def _construct_status(self):
        bar = QStatusBar(self)
        self.setStatusBar(bar)
        self.status = QLabel('READY  ·  RISC-V LINK TESTS ARE NON-BOOTABLE')
        bar.addWidget(self.status, 1)
        bar.addPermanentWidget(QLabel('F133 · D213 · 12F · 45F'))

    def _rooted(self, path):
        return editable_file(path, ROOT)

    def _tree_activated(self, index):
        path = Path(self.file_model.filePath(index))
        if path.is_file():
            try:self.open_source(path)
            except (ValueError, OSError, UnicodeError) as e:
                self._message('File unavailable', str(e), error=True)

    def current_editor(self):
        editor = self.tabs.currentWidget()
        return editor if isinstance(editor, QPlainTextEdit) else None

    def open_source(self, path):
        path = self._rooted(Path(path))
        if path in self.documents:
            self.tabs.setCurrentWidget(self.documents[path]); return
        data = path.read_text(encoding='utf-8')
        editor = QPlainTextEdit()
        editor.setObjectName('sourceEditor')
        editor.setFont(QFont('Consolas', 10))
        editor.setTabStopDistance(32)
        editor.setPlainText(data)
        editor.document().setModified(False)
        editor.document().modificationChanged.connect(lambda dirty, p=path: self._update_tab(p, dirty))
        index = self.tabs.addTab(editor, path.name)
        self.tabs.setTabToolTip(index, str(path.relative_to(ROOT)))
        self.tabs.setCurrentIndex(index)
        self.documents[path] = editor
        self.status.setText('EDITING  ·  '+str(path.relative_to(ROOT)))

    def _path_for_editor(self, editor):
        return next((p for p, e in self.documents.items() if e is editor), None)

    def _update_tab(self, path, dirty):
        editor = self.documents.get(path)
        if editor is not None:
            index = self.tabs.indexOf(editor)
            if index >= 0:
                self.tabs.setTabText(index, ('● ' if dirty else '')+path.name)

    def _close_tab(self, index):
        widget=self.tabs.widget(index)
        if widget is None:return True
        if not self._confirm_save(widget):return False
        path=self._path_for_editor(widget)
        if path:self.documents.pop(path, None)
        self.tabs.removeTab(index)
        widget.deleteLater()
        return True

    def _confirm_save(self, editor):
        if not editor.document().isModified():return True
        answer = QMessageBox.question(self, 'Unsaved source', 'Save changes before closing?',
                       QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Cancel:return False
        if answer == QMessageBox.Save:return self.save_source(editor)
        return True

    def save_source(self, editor=None):
        editor = editor or self.current_editor()
        path = self._path_for_editor(editor)
        if not path:return False
        try:
            self._rooted(path)
            # Atomic replacement; refuses symlinks and leaves recoverable original on failure.
            fd, name = tempfile.mkstemp(prefix='.arc1-edit-', dir=path.parent)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
                    handle.write(editor.toPlainText())
                os.replace(name, path)
            finally:
                if os.path.exists(name): os.unlink(name)
            editor.document().setModified(False)
            self.status.setText('SAVED  ·  '+str(path.relative_to(ROOT)))
            return True
        except (OSError, ValueError) as e:
            self._message('Save failed', str(e), error=True)
            return False

    def save_all(self):
        return all(self.save_source(editor) for editor in self.documents.values() if editor.document().isModified())

    def open_dialog(self):
        filename, _ = QFileDialog.getOpenFileName(self,'Open ARC-1 source',str(ROOT), 'Source files (*.c *.h *.s *.py *.json *.md *.ld *.txt);;All files (*)')
        if filename:
            try:self.open_source(Path(filename))
            except (OSError, ValueError, UnicodeError) as e:self._message('Cannot open',str(e),error=True)

    def quick_open(self):
        candidates=[]
        for base in ('firmware','sdk','workbench','examples','docs','tests'):
            for file in (ROOT/base).rglob('*'):
                if len(candidates)>=1300:break
                if file.is_file() and file.suffix.lower() in EDIT_EXT and not file.is_symlink() and 'build' not in file.parts and '__pycache__' not in file.parts:
                    candidates.append(str(file.relative_to(ROOT)))
        choice, ok=QInputDialog.getItem(self,'Quick Open','Choose a project file',sorted(candidates),0,True)
        if ok and choice:
            match=ROOT/choice
            try:self.open_source(match)
            except (ValueError,OSError) as e:self._message('Cannot open',str(e),error=True)

    def find_text(self):
        editor=self.current_editor()
        if editor is None:return
        word,ok=QInputDialog.getText(self,'Find in source','Find text:')
        if ok and word and not editor.find(word):
            cursor=editor.textCursor();cursor.movePosition(cursor.Start);editor.setTextCursor(cursor)
            if not editor.find(word):self.status.setText('FIND  ·  No matches')

    def replace_text(self):
        editor=self.current_editor()
        if editor is None:return
        needle,ok=QInputDialog.getText(self,'Replace in file','Search for:')
        if not ok or not needle:return
        replacement,ok=QInputDialog.getText(self,'Replace in file','Replace with:')
        if not ok:return
        old=editor.toPlainText()
        count=old.count(needle)
        if not count:return
        answer=QMessageBox.question(self,'Replace all',f'Replace {count} occurrence(s) in this document?',QMessageBox.Yes|QMessageBox.No)
        if answer == QMessageBox.Yes:editor.setPlainText(old.replace(needle,replacement))

    def command_palette(self):
        choices=list(ACTIONS) + ['Open file','Save','Quick Open','Cartridge shelf','Inspect cartridge','Code workspace','Cartridge workspace','Debug workspace']
        selection,ok=QInputDialog.getItem(self,'Workbench commands','Command:',choices,0,True)
        if not ok:return
        if selection in ACTIONS:self.run_cmd(selection)
        elif selection=='Open file':self.open_dialog()
        elif selection=='Save':self.save_source()
        elif selection=='Quick Open':self.quick_open()
        elif selection=='Cartridge shelf':self.game_dock.raise_()
        elif selection=='Inspect cartridge':self.inspect_selected()
        elif selection.endswith('workspace'):self.workspace(selection.split(' ')[0])

    def toggle_output(self):
        self.console_dock.setVisible(not self.console_dock.isVisible())

    def show_problems(self):
        self.console_dock.show()
        self.output_tabs.setCurrentWidget(self.problem_view)

    def run_cmd(self, name):
        if name not in ACTIONS:return
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self._message('Build already running','Wait for the current build/test to finish.');return
        if not self.save_all():return
        self.command_name=name
        self.router.start(name)
        command=ACTIONS[name]
        self.output.appendPlainText('\nARC1> '+ ' '.join(command))
        self.console_dock.show()
        self.output_tabs.setCurrentWidget(self.build_view)
        self.build_view.setPlainText('Running: '+name)
        self.process.start(sys.executable,[str(ROOT/'arc1'),*command])
        self.status.setText('RUNNING  ·  '+name)

    def _read_process(self):
        data=bytes(self.process.readAllStandardOutput()).decode('utf-8',errors='replace')
        if data:
            self.router.append(data)
            self.output.insertPlainText(data)
            self.output.ensureCursorVisible()

    def _process_finished(self, code, status):
        self._read_process()
        good=(code==0 and status==QProcess.ExitStatus.NormalExit)
        self.router.finish(code if good else (code or 1))
        self.build_view.setPlainText(self.router.raw+'\n'+('PASS' if good else 'FAILED')+f' (exit {code})')
        self.problem_view.setPlainText(self.router.summary())
        self.output.appendPlainText(('PASS' if good else 'FAILED / INCOMPLETE') + f'  (exit {code})\n')
        if not good:self.show_problems()
        self.status.setText(self.command_name + ('  ·  PASS' if good else '  ·  INCOMPLETE'))

    def refresh_shelf(self):
        self.shelf.clear()
        for record in games_on_shelf(ROOT):
            text=('✓ ' if record.get('valid') else '! ')+record['name']+'  ·  '+record.get('version','invalid')
            self.shelf.addItem(text)
            self.shelf.item(self.shelf.count()-1).setData(Qt.UserRole,record)

    def _selected_cart(self):
        item=self.shelf.currentItem()
        if item is None:
            if self.shelf.count()==0:raise CartridgeError('No cartridge in the shelf')
            item=self.shelf.item(0);self.shelf.setCurrentItem(item)
        record=item.data(Qt.UserRole)
        if not record['valid']:raise CartridgeError(record.get('error','Invalid cartridge'))
        return record['path']

    def inspect_selected(self):
        try:
            r=inspect_cartridge(ROOT/self._selected_cart())
            self.inspector.setPlainText(f"CARTRIDGE / VERIFIED HOST ARCHIVE\n\nName: {r['name']}\nVersion: {r['game_version']}\nAssets: {r['asset_count']}\nBytes: {r['asset_bytes']}\nSHA256: {r['cartridge_sha256']}\n\nNO ARC-1 EXECUTABLE INCLUDED\nNO USB HARDWARE TEST")
            self.inspector_dock.raise_()
        except (CartridgeError,OSError) as e:self._message('Cartridge invalid',str(e),error=True)

    def package_example(self):
        try:
            r=package_game(ROOT/'examples'/'hello_arc1',ROOT/'cartridges'/'hello_arc1.arc1cart')
            self.refresh_shelf()
            self.output.appendPlainText('HOST CARTRIDGE PACKAGED: '+r['name'])
        except (CartridgeError,OSError) as e:self._message('Package failed',str(e),error=True)

    def import_dialog(self):
        filename,_=QFileDialog.getOpenFileName(self,'Import a verified cartridge',str(Path.home()),'ARC-1 cartridges (*.arc1cart)')
        if filename:self.import_cartridge(Path(filename))

    def import_cartridge(self, path):
        try:
            result=verify_drop(path)
            destination=(ROOT/'cartridges'/Path(path).name)
            if destination.resolve()==Path(path).resolve():return
            if destination.exists():
                result_dialog=QMessageBox.question(self,'Replace cartridge?',f'{destination.name} already exists. Replace it?',QMessageBox.Yes|QMessageBox.No)
                if result_dialog!=QMessageBox.Yes:return
            else:
                result_dialog=QMessageBox.question(self,'Import verified cartridge?',f"Copy {result['name']} into the local cartridge shelf?",QMessageBox.Yes|QMessageBox.No)
                if result_dialog!=QMessageBox.Yes:return
            destination.parent.mkdir(exist_ok=True)
            fd,tmp=tempfile.mkstemp(prefix='.arc1-qt-import-',dir=destination.parent)
            try:
                with os.fdopen(fd,'wb') as out,Path(path).open('rb') as source:shutil.copyfileobj(source,out)
                if inspect_cartridge(Path(tmp))['cartridge_sha256']!=result['cartridge_sha256']:
                    raise CartridgeError('Imported copy differs from original')
                os.replace(tmp,destination)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
            self.refresh_shelf()
        except (OSError,CartridgeError) as e:self._message('Import rejected',str(e),error=True)

    def stream_selected(self):
        try:
            r=simulate_stream(ROOT/self._selected_cart())
            self.output.appendPlainText('\nHOST VIRTUAL USB STREAMING MODEL\n'+\
                f"Frames: {r['frames']} / Stalls: {r['simulated_stall_frames']} / " +\
                f"Physical USB tested: {r['physical_usb_tested']}\n")
            self.console_dock.show()
        except (CartridgeError,OSError) as e:self._message('Simulation failed',str(e),error=True)

    def launch_selected(self):
        try:
            self.save_all()
            cart=self._selected_cart()
            self.current_sim.start(cart,frames=120)
            self.game_dock.show();self.game_dock.raise_()
            self.preview.setText('HOST SIMULATION RUNNING…')
            self.status.setText('RUNNING LOCAL HOST GAME · NOT ARC-1 HARDWARE')
            self.launch_last_state=None
        except (CartridgeError,LauncherError,OSError) as e:self._message('Cannot launch host game',str(e),error=True)

    def _poll_sim(self):
        state=self.current_sim.status()
        new=state['state']
        if new==self.launch_last_state:return
        self.launch_last_state=new
        if new in ('COMPLETED','FAILED','STOPPED'):
            self.status.setText('HOST SIM · '+new)
            self.debug_view.setPlainText('HOST SIMULATION · '+new+'\n\n'+str(state.get('result',{}))+'\n\nNO PHYSICAL DEVICE TELEMETRY')
            result=state.get('result',{})
            if new=='COMPLETED':
                previews=result.get('preview_frames',[])
                if previews:
                    pix=QPixmap(str(ROOT/previews[len(previews)//2]))
                    if not pix.isNull():
                        self.preview.setPixmap(pix.scaled(360,225,Qt.KeepAspectRatio,Qt.SmoothTransformation))
                self.output.appendPlainText('\nHOST SIM COMPLETE — '+str(result.get('code'))+'\n')
            else:
                self.preview.setText('Host simulation '+new.lower())
                self.output.appendPlainText('HOST SIM '+new+': '+str(result.get('code')))

    def stop_sim(self):
        state=self.current_sim.stop()
        self.status.setText('HOST SIM STOP REQUESTED' if state.get('stopped') else 'NO ACTIVE HOST SIM')

    def advance_boot(self):
        for stage in ('f133','nor','d213','fpga12','fpga45','ready'):
            if stage not in self.boot.history:
                try:self.boot.mark(stage)
                except ValueError as e:self._message('Cannot advance simulated boot',str(e),error=True)
                break
        self.refresh_boot()

    def reset_boot(self):
        self.boot=BootModel();self.refresh_boot()

    def refresh_boot(self):
        snapshot=self.boot.snapshot()
        self.lcd.setText('\n'.join(snapshot['lcd_rows']))
        self.inspector.setPlainText('BOOT DIAGNOSTICS / HOST MODEL ONLY\n\n'+\
            'Stage: '+snapshot['stage']+'\nChecks: '+', '.join(snapshot['history'])+\
            '\n\nThe actual F133, D213 and FPGA status are UNKNOWN.\n'+\
            'No physical device is connected or tested.')

    def workspace(self, name):
        if name=='Code':
            self.file_dock.show();self.console_dock.hide();self.inspector_dock.hide();self.game_dock.hide()
        elif name=='Cartridge':
            self.file_dock.show();self.game_dock.show();self.game_dock.raise_();self.console_dock.show()
        else:
            self.file_dock.show();self.inspector_dock.show();self.inspector_dock.raise_();self.console_dock.show()
        self.status.setText('WORKSPACE  ·  '+name)
        self.settings.setValue('preferred_workspace',name)

    def _restore_layout(self):
        geometry=self.settings.value('geometry')
        if geometry:self.restoreGeometry(geometry)
        state=self.settings.value('dock_state')
        if state:self.restoreState(state)
        else:self.workspace('Code')

    def _message(self,title,body,error=False):
        if error:QMessageBox.warning(self,title,body)
        else:QMessageBox.information(self,title,body)

    def show_about(self):
        self._message('ARC-1 Workbench R09',
            'Qt 6 R09 prototype with compact professional orange Aqua controls.\n\n'
            'Source editing, R07 SDK commands, verified host cartridge inspection and host game preview are integrated.\n'
            'F133 and D213 ELF/BIN files are NOT BOOTABLE. FPGA hardware, USB and LCD are NOT TESTED.\n'
            'No physical flash or deployment operation is implemented.\n\n'
            'AI agents continue to use the unchanged JSON-lines `python arc1 agent` interface.')

    def closeEvent(self,event):
        for editor in list(self.documents.values()):
            if not self._confirm_save(editor):
                event.ignore();return
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.terminate()
            self.process.waitForFinished(2000)
        self.current_sim.stop()
        self.settings.setValue('geometry',self.saveGeometry())
        self.settings.setValue('dock_state',self.saveState())
        event.accept()


def main():
    app=QApplication(sys.argv)
    app.setApplicationName('ARC-1 Workbench')
    app.setOrganizationName('ARC Concern')
    app.setStyle('Fusion')
    app.setStyleSheet(QSS)
    window=WorkbenchQt();window.show()
    return app.exec()

if __name__=='__main__':
    raise SystemExit(main())
