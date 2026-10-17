"""ARC-1 Workbench R10 "Classic" — Qt 6 main screen.

Governing rule (owner decision for R10): Workbench behaves like the Windows
File Manager and document editor you already know, and reveals the console
engineering tools only when the task needs them.

Default screen: menu bar, one compact toolbar, a ~236 px project navigator,
the document area and a status bar. Output/Problems, the hardware inspector
and the cartridge shelf start hidden and open when work calls for them.
Every Build/Tests/Run decision comes from workbench.engine, the same engine the
agent interface uses; this window never invents a result the CLI did not give,
and never shows a connected device.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time

from PySide6.QtCore import QDir, QProcess, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QAction, QActionGroup, QColor, QFont, QFontDatabase, QIcon, QImage, QKeySequence,
                           QPainter, QPixmap, QTextCursor, QTextFormat)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDialog, QDialogButtonBox, QDockWidget, QFileDialog,
    QFileSystemModel, QFrame, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QSizePolicy, QSlider,
    QSplitter, QStyle, QTabWidget, QTextEdit, QToolBar, QToolButton, QTreeView, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from . import engine, fileops
from .bootlogic import BootModel
from .cartridge import CartridgeError, inspect_cartridge, package_game, simulate_stream
from .output_router import OutputRouter
from .qt_contract import editable_file, verify_drop
from .qt_theme import QSS
from .session import Session, decode_bytes, encode_bytes

ROOT = engine.ROOT
VERSION = 'R10'
EDIT_EXT = {'.c', '.h', '.s', '.S', '.py', '.md', '.json', '.txt', '.ld', '.cmd', '.sh', '.yaml', '.yml',
            '.csv', '.sprite', '.replay'}
MONO = ['Consolas', 'Cascadia Mono', 'DejaVu Sans Mono', 'Menlo', 'Courier New']


def mono_font(points=10):
    """First installed font from MONO, else the system fixed-pitch font."""
    available = set(QFontDatabase.families())
    f = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    for name in MONO:
        if name in available:
            f = QFont(name)
            break
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setFixedPitch(True)
    f.setPointSizeF(points)
    return f


# --------------------------------------------------------------------------- editor

class _Gutter(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.gutter_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_gutter(event)


class CodeEditor(QPlainTextEdit):
    """Plain-text source editor with line numbers, a current-line band and a
    problem marker. Undo/redo, cut/copy/paste come from Qt."""
    def __init__(self, path, root):
        super().__init__()
        self.path = Path(path)
        self.root = Path(root)
        self.problem_line = None
        self.setObjectName('sourceEditor')
        self.setFont(mono_font(10))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)
        self.gutter = _Gutter(self)
        self.blockCountChanged.connect(lambda _: self.setViewportMargins(self.gutter_width(), 0, 0, 0))
        self.updateRequest.connect(self._update_gutter)
        self.cursorPositionChanged.connect(self._highlight)
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)
        self._highlight()

    def gutter_width(self):
        digits = max(3, len(str(max(1, self.blockCount()))))
        return 14 + self.fontMetrics().horizontalAdvance('9') * digits

    def _update_gutter(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.gutter_width(), cr.height()))

    def paint_gutter(self, event):
        p = QPainter(self.gutter)
        p.fillRect(event.rect(), QColor('#f3f1ec'))
        p.setPen(QColor('#e2ddd5'))
        p.drawLine(self.gutter.width() - 1, event.rect().top(), self.gutter.width() - 1, event.rect().bottom())
        block = self.firstVisibleBlock()
        n = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        current = self.textCursor().blockNumber()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                if self.problem_line == n + 1:
                    p.fillRect(0, top, self.gutter.width() - 1, bottom - top, QColor('#f8cfb5'))
                p.setPen(QColor('#23272b') if n == current else QColor('#9a9c9e'))
                p.drawText(0, top, self.gutter.width() - 7, self.fontMetrics().height(), Qt.AlignRight, str(n + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            n += 1

    def _highlight(self):
        extra = []
        line = QTextEdit.ExtraSelection()
        line.format.setBackground(QColor('#fbf3e7'))
        line.format.setProperty(QTextFormat.FullWidthSelection, True)
        line.cursor = self.textCursor()
        line.cursor.clearSelection()
        extra.append(line)
        if self.problem_line:
            block = self.document().findBlockByNumber(self.problem_line - 1)
            if block.isValid():
                mark = QTextEdit.ExtraSelection()
                mark.format.setBackground(QColor('#fde3d2'))
                mark.format.setProperty(QTextFormat.FullWidthSelection, True)
                mark.cursor = QTextCursor(block)
                extra.append(mark)
        self.setExtraSelections(extra)
        self.gutter.update()

    def go_to(self, line, column=1, problem=False):
        block = self.document().findBlockByNumber(max(0, line - 1))
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.Right, n=max(0, min(column - 1, block.length() - 1)))
        self.setTextCursor(cursor)
        self.problem_line = line if problem else None
        self.centerCursor()
        self._highlight()
        self.setFocus()

    def position(self):
        c = self.textCursor()
        return c.blockNumber() + 1, c.positionInBlock() + 1


# --------------------------------------------------------------------------- browse (File Manager)

class BrowsePane(QWidget):
    """Windows File Manager-style folder listing: name, size, type, modified."""
    open_file = Signal(Path)
    changed = Signal()

    def __init__(self, window, folder):
        super().__init__()
        self.window_ = window
        self.root = window.root
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        bar = QHBoxLayout()
        bar.setContentsMargins(6, 4, 6, 4)
        self.up = QToolButton(text='Up')
        self.up.setIcon(self.style().standardIcon(QStyle.SP_FileDialogToParent))
        self.up.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.up.clicked.connect(self.go_up)
        self.where = QLineEdit()
        self.where.setReadOnly(True)
        self.where.setAccessibleName('Current folder')
        bar.addWidget(self.up)
        bar.addWidget(self.where, 1)
        for text, cb, tip in (('New File', self.new_file, 'Create a file in this folder'),
                              ('New Folder', self.new_folder, 'Create a folder here'),
                              ('Rename', self.rename, 'Rename the selected item (F2)'),
                              ('Duplicate', self.duplicate, 'Copy the selected file next to itself'),
                              ('Delete', self.delete, 'Delete the selected file (Del)')):
            b = QToolButton(text=text)
            b.setToolTip(tip)
            b.clicked.connect(cb)
            bar.addWidget(b)
        v.addLayout(bar)
        self.model = QFileSystemModel(self)
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)
        self.model.setNameFilterDisables(False)
        self.model.setReadOnly(True)
        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setRootIsDecorated(False)
        self.view.setItemsExpandable(False)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(0, Qt.AscendingOrder)
        self.view.setAlternatingRowColors(True)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.doubleClicked.connect(self._activated)
        self.view.activated.connect(self._activated)
        self.view.header().setStretchLastSection(False)
        self.view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        for col, w in ((1, 90), (2, 140), (3, 140)):
            self.view.header().setSectionResizeMode(col, QHeaderView.Interactive)
            self.view.setColumnWidth(col, w)
        v.addWidget(self.view, 1)
        self.folder = None
        self.navigate(folder)

    def navigate(self, folder):
        folder = fileops.check_inside(self.root, folder)
        self.folder = folder
        idx = self.model.setRootPath(str(folder))
        self.view.setRootIndex(idx)
        r = fileops.rel(self.root, folder)
        self.where.setText(('ARC-1 project' if r == '.' else 'ARC-1 project / ' + r.replace('/', ' / '))
                           + ('   (read-only evidence)' if r != '.' and fileops.is_read_only(self.root, folder) else ''))
        self.up.setEnabled(folder != self.root.resolve())
        self.changed.emit()

    def title(self):
        r = fileops.rel(self.root, self.folder)
        return 'Browse: ' + ('project' if r == '.' else Path(r).name)

    def info(self):
        try:
            n = len(fileops.listing(self.root, self.folder))
        except fileops.FileOpError:
            n = 0
        r = fileops.rel(self.root, self.folder)
        return 'Browse · %s · %d items' % ('project root' if r == '.' else r + '/', n)

    def go_up(self):
        if self.folder != self.root.resolve():
            self.navigate(self.folder.parent)

    def selected(self):
        idx = self.view.currentIndex()
        return Path(self.model.filePath(idx)) if idx.isValid() else None

    def _activated(self, index):
        p = Path(self.model.filePath(index))
        if p.is_dir():
            self.navigate(p)
        elif p.is_file():
            self.open_file.emit(p)

    def _ask(self, title, label, text=''):
        value, ok = QInputDialog.getText(self, title, label, text=text)
        return value.strip() if ok else None

    def _run(self, fn, *args):
        try:
            result = fn(*args)
            self.window_.refresh_navigator()
            return result
        except (fileops.FileOpError, OSError) as e:
            self.window_.message('Cannot complete that', str(e), error=True)
            return None

    def new_file(self):
        name = self._ask('New File', 'File name:', 'untitled.c')
        if name:
            p = self._run(fileops.new_file, self.root, self.folder, name)
            if p and p.suffix in EDIT_EXT:
                self.open_file.emit(p)

    def new_folder(self):
        name = self._ask('New Folder', 'Folder name:', 'New folder')
        if name:
            self._run(fileops.new_folder, self.root, self.folder, name)

    def rename(self):
        p = self.selected()
        if p is None:
            return
        if self.window_.document_for(p) is not None:
            self.window_.message('Close it first', '%s is open in the editor. Close it before renaming.' % p.name)
            return
        name = self._ask('Rename', 'New name:', p.name)
        if name and name != p.name:
            self._run(fileops.rename, self.root, p, name)

    def duplicate(self):
        p = self.selected()
        if p is not None:
            self._run(fileops.duplicate, self.root, p)

    def delete(self):
        p = self.selected()
        if p is None or p.is_dir():
            return
        if self.window_.document_for(p) is not None:
            self.window_.message('Close it first', '%s is open in the editor. Close it before deleting.' % p.name)
            return
        if self.window_.confirm('Delete file', 'Delete %s permanently?\n\n%s' % (p.name, fileops.rel(self.root, p))):
            self._run(fileops.delete_file, self.root, p)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F2:
            self.rename()
        elif event.key() == Qt.Key_Delete:
            self.delete()
        elif event.key() == Qt.Key_Backspace:
            self.go_up()
        else:
            super().keyPressEvent(event)


class BrowseTab(QWidget):
    """One Browse tab: a single listing, optionally two side by side (dual pane)."""
    def __init__(self, window, folder):
        super().__init__()
        self.window_ = window
        self.split = QSplitter(Qt.Horizontal)
        self.left = BrowsePane(window, folder)
        self.right = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.split)
        self.split.addWidget(self.left)
        for pane in (self.left,):
            pane.open_file.connect(window.open_document)
            pane.changed.connect(window.update_document_info)

    @property
    def pane(self):
        return self.left

    def set_dual(self, on):
        if on and self.right is None:
            self.right = BrowsePane(self.window_, self.left.folder)
            self.right.open_file.connect(self.window_.open_document)
            self.split.addWidget(self.right)
        elif not on and self.right is not None:
            self.right.setParent(None)
            self.right.deleteLater()
            self.right = None

    def title(self):
        return self.left.title()

    def info(self):
        return self.left.info() + ('  ·  dual pane' if self.right else '')


# --------------------------------------------------------------------------- start page and preview

class StartPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 30, 40, 30)
        head = QLabel('ARC-1 Workbench')
        head.setObjectName('heading')
        sub = QLabel('Project: %s' % window.root)
        sub.setObjectName('subheading')
        sub.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(head)
        outer.addWidget(sub)
        row = QHBoxLayout()
        col1 = QVBoxLayout()
        t = QLabel('Start')
        t.setObjectName('sectionTitle')
        col1.addWidget(t)
        for text, cb in (('Open file…   Ctrl+O', window.open_dialog),
                         ('Find a file…   Ctrl+P', window.quick_open),
                         ('Browse the project folder', lambda: window.browse(window.root)),
                         ('New game project…', window.new_game_project)):
            b = QPushButton(text)
            b.setObjectName('linkButton')
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(cb)
            col1.addWidget(b)
        col1.addStretch(1)
        col2 = QVBoxLayout()
        t2 = QLabel('Recent files')
        t2.setObjectName('sectionTitle')
        col2.addWidget(t2)
        self.recent = QListWidget()
        self.recent.setAccessibleName('Recent files')
        self.recent.itemActivated.connect(self._open_recent)
        self.recent.itemDoubleClicked.connect(self._open_recent)
        col2.addWidget(self.recent, 1)
        row.addLayout(col1, 1)
        row.addSpacing(30)
        row.addLayout(col2, 2)
        outer.addLayout(row, 1)
        note = QLabel('Host tools only. %s. Fabrication HOLD.' % engine.device_status()['text'])
        note.setObjectName('simBanner')
        outer.addWidget(note)
        self.refresh()

    def refresh(self):
        self.recent.clear()
        for r in self.window_.session.state['recent']:
            if (self.window_.root / r).is_file():
                item = QListWidgetItem(r)
                item.setData(Qt.UserRole, r)
                self.recent.addItem(item)
        if self.recent.count() == 0:
            self.recent.addItem(QListWidgetItem('No recent files yet'))

    def _open_recent(self, item):
        r = item.data(Qt.UserRole)
        if r:
            self.window_.open_document(self.window_.root / r)

    def title(self):
        return 'Start'

    def info(self):
        return 'Start page · %s' % engine.device_status()['text']


class PreviewTab(QWidget):
    """Frames from the host simulator. Not ARC-1 hardware output."""
    def __init__(self, window, project, frames):
        super().__init__()
        self.project = project
        self.frames = frames
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        banner = QLabel('HOST SIMULATION of %s on this PC · not ARC-1 hardware output' % Path(project).name)
        banner.setObjectName('simBanner')
        lay.addWidget(banner)
        self.image = QLabel()
        self.image.setObjectName('framePreview')
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setMinimumSize(320, 180)
        self.image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self.image, 1)
        row = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, max(0, len(frames) - 1))
        self.slider.valueChanged.connect(self.show_frame)
        self.caption = QLabel()
        row.addWidget(QLabel('Frame'))
        row.addWidget(self.slider, 1)
        row.addWidget(self.caption)
        lay.addLayout(row)
        self.show_frame(0)

    def show_frame(self, i):
        if not self.frames:
            self.image.setText('The simulator produced no frames.')
            return
        number, path = self.frames[i]
        img = QImage(str(path))
        if img.isNull():
            self.image.setText('Cannot read %s' % path.name)
            return
        self.current = QPixmap.fromImage(img)
        self._scale()
        self.caption.setText('%d  (%d of %d)' % (number, i + 1, len(self.frames)))

    def _scale(self):
        if getattr(self, 'current', None) is None:
            return
        w, h = self.image.width() - 4, self.image.height() - 4
        k = max(1, min(w // self.current.width(), h // self.current.height()))
        self.image.setPixmap(self.current.scaled(self.current.width() * k, self.current.height() * k,
                                                 Qt.KeepAspectRatio, Qt.FastTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._scale()

    def title(self):
        return 'Preview: ' + Path(self.project).name

    def info(self):
        return 'Host simulation · %s · %d frames' % (self.project, len(self.frames))


class QuickOpen(QDialog):
    """Ctrl+P: type part of a file name, press Enter."""
    def __init__(self, window):
        super().__init__(window)
        self.setWindowTitle('Find a file')
        self.resize(560, 420)
        self.files = engine.walk_files(window.root)
        lay = QVBoxLayout(self)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText('Type part of a file name, e.g. main.c')
        self.list = QListWidget()
        lay.addWidget(self.edit)
        lay.addWidget(self.list, 1)
        self.edit.textChanged.connect(self.refresh)
        self.edit.returnPressed.connect(self.accept)
        self.list.itemActivated.connect(lambda _: self.accept())
        self.refresh('')

    def refresh(self, text):
        self.list.clear()
        for f in engine.find_files(text, files=self.files, limit=200):
            self.list.addItem(f)
        if self.list.count():
            self.list.setCurrentRow(0)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Down, Qt.Key_Up) and self.edit.hasFocus():
            self.list.keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def chosen(self):
        item = self.list.currentItem()
        return item.text() if item else None


# --------------------------------------------------------------------------- main window

class WorkbenchWindow(QMainWindow):
    def __init__(self, root=ROOT, session=None, restore=True):
        super().__init__()
        self.root = Path(root).resolve()
        self.session = session or Session(project=self.root)
        self.router = OutputRouter()
        self.boot = BootModel()
        self.plan = None
        self.after_build = None
        self.started_at = 0.0
        self.problems = []
        self.find_text = ''
        self._then = None
        self.problem_cursor = -1
        self.setWindowTitle('ARC-1 Workbench')
        logo = self.root / 'workbench' / 'logo_compact.png'
        if logo.is_file():
            self.setWindowIcon(QIcon(str(logo)))
        self.setMinimumSize(900, 560)
        self.setDockNestingEnabled(True)
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(self.root))
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_process)
        self.process.finished.connect(self._process_finished)
        self._build_central()
        self._build_docks()
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_status()
        self.resize(1366, 768)
        self._apply_default_layout()
        self.factory_state = self.saveState(engine_layout_version())
        if restore:
            self.restore_session()
        if self.tabs.count() == 0:
            self.show_start()
        self.update_document_info()

    # ---------------------------------------------------------------- construction
    def _build_central(self):
        central = QWidget()
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(lambda _: self.update_document_info())
        self.doc_info = QLabel()
        self.doc_info.setObjectName('docInfo')
        v.addWidget(self.tabs, 1)
        v.addWidget(self.doc_info)
        self.setCentralWidget(central)

    def _dock(self, title, name, widget, area):
        d = QDockWidget(title, self)
        d.setObjectName(name)
        d.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        d.setWidget(widget)
        self.addDockWidget(area, d)
        return d

    def _build_docks(self):
        # Project navigator: logical areas of the ARC-1 project, lazily filled.
        self.nav = QTreeWidget()
        self.nav.setHeaderHidden(True)
        self.nav.setAccessibleName('Project navigator')
        self.nav.itemExpanded.connect(self._fill_nav_item)
        self.nav.itemClicked.connect(self._nav_clicked)
        self.nav.itemActivated.connect(self._nav_activated)
        self.nav_dock = self._dock('Project', 'ProjectDock', self.nav, Qt.LeftDockWidgetArea)
        self.refresh_navigator()

        # Output panel: hidden until work needs it (F10).
        self.output_tabs = QTabWidget()
        self.output_tabs.setDocumentMode(True)
        self.output = QPlainTextEdit()
        self.output.setObjectName('outputText')
        self.output.setReadOnly(True)
        self.output.setFont(mono_font(9))
        self.output.document().setMaximumBlockCount(8000)
        self.output.setPlainText('Build and test output appears here.\n')
        self.problem_list = QTreeWidget()
        self.problem_list.setRootIsDecorated(False)
        self.problem_list.setHeaderLabels(['', 'Description', 'File', 'Line'])
        self.problem_list.setAlternatingRowColors(True)
        self.problem_list.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.problem_list.setColumnWidth(0, 70)
        self.problem_list.header().setSectionResizeMode(2, QHeaderView.Interactive)
        self.problem_list.setColumnWidth(2, 180)
        self.problem_list.header().setSectionResizeMode(3, QHeaderView.Interactive)
        self.problem_list.setColumnWidth(3, 60)
        self.problem_list.header().setStretchLastSection(False)
        self.problem_list.itemActivated.connect(self._problem_activated)
        self.problem_list.itemDoubleClicked.connect(self._problem_activated)
        self.debug_view = QPlainTextEdit()
        self.debug_view.setObjectName('outputText')
        self.debug_view.setReadOnly(True)
        self.debug_view.setPlainText('No debugger is connected. There is no ARC-1 device transport; breakpoints, '
                                     'registers and call stacks need a board that does not exist yet.\n'
                                     'Host simulation results appear here after Run (F5).')
        self.agent_view = QPlainTextEdit()
        self.agent_view.setObjectName('outputText')
        self.agent_view.setReadOnly(True)
        self.agent_view.setPlainText('AI agents use the shared engine through:  python arc1 agent\n\n'
                                     'Agent requests run the same build, test and file services as this window, '
                                     'but they are not streamed here yet. Nothing is shown that did not happen.')
        for title, w in (('Output', self.output), ('Problems', self.problem_list), ('Debug', self.debug_view),
                         ('Agent Activity', self.agent_view)):
            self.output_tabs.addTab(w, title)
        self.output_tabs.currentChanged.connect(lambda _: self.session.set_layout(
            output_tab=self.output_tabs.tabText(self.output_tabs.currentIndex())))
        self.output_dock = self._dock('Output   (F10)', 'OutputDock', self.output_tabs, Qt.BottomDockWidgetArea)

        # Hardware inspector (host boot-diagnostic model) and cartridge shelf: hidden by default.
        insp = QWidget()
        iv = QVBoxLayout(insp)
        iv.setContentsMargins(8, 8, 8, 8)
        self.lcd = QLabel()
        self.lcd.setObjectName('lcd')
        self.lcd.setAlignment(Qt.AlignCenter)
        self.inspector = QPlainTextEdit()
        self.inspector.setObjectName('inspector')
        self.inspector.setReadOnly(True)
        self.inspector.setFont(mono_font(9))
        iv.addWidget(QLabel('Boot diagnostic model (host only)'))
        iv.addWidget(self.lcd)
        iv.addWidget(self.inspector, 1)
        row = QHBoxLayout()
        for text, cb in (('Advance step', self.advance_boot), ('Reset', self.reset_boot)):
            b = QPushButton(text)
            b.clicked.connect(cb)
            row.addWidget(b)
        iv.addLayout(row)
        self.inspector_dock = self._dock('Hardware Inspector', 'InspectorDock', insp, Qt.RightDockWidgetArea)
        shelf = QWidget()
        sv = QVBoxLayout(shelf)
        sv.setContentsMargins(8, 8, 8, 8)
        self.shelf = QListWidget()
        self.shelf.itemDoubleClicked.connect(lambda _: self.inspect_cartridge())
        sv.addWidget(QLabel('Verified cartridges (host archives)'))
        sv.addWidget(self.shelf, 1)
        r2 = QHBoxLayout()
        for text, cb in (('Inspect', self.inspect_cartridge), ('Import…', self.import_cartridge_dialog)):
            b = QPushButton(text)
            b.clicked.connect(cb)
            r2.addWidget(b)
        sv.addLayout(r2)
        self.cart_dock = self._dock('Cartridges', 'CartridgeDock', shelf, Qt.RightDockWidgetArea)
        self.tabifyDockWidget(self.inspector_dock, self.cart_dock)
        self.refresh_boot()
        self.refresh_shelf()

    def _act(self, text, cb, shortcut=None, tip=None, icon=None):
        a = QAction(text, self)
        a.triggered.connect(cb)
        if shortcut:
            seqs = shortcut if isinstance(shortcut, (list, tuple)) else [shortcut]
            a.setShortcuts([QKeySequence(s) if isinstance(s, str) else QKeySequence(s) for s in seqs])
        if tip:
            a.setStatusTip(tip)
            a.setToolTip(tip)
        if icon is not None:
            a.setIcon(self.style().standardIcon(icon))
        return a

    def _build_actions(self):
        A = self._act
        self.a_new = A('&New File…', self.new_file, QKeySequence.New, 'Create a file in the selected folder')
        self.a_open = A('&Open…', self.open_dialog, QKeySequence.Open, 'Open a file', QStyle.SP_DialogOpenButton)
        self.a_quick = A('Find a &File…', self.quick_open, 'Ctrl+P', 'Type part of a file name to open it')
        self.a_save = A('&Save', lambda: self.save_document(), QKeySequence.Save, 'Save the current file',
                        QStyle.SP_DialogSaveButton)
        self.a_save_all = A('Save A&ll', self.save_all, 'Ctrl+Shift+S', 'Save every modified file')
        self.a_close = A('&Close', lambda: self.close_tab(self.tabs.currentIndex()), ['Ctrl+W', 'Ctrl+F4'])
        self.a_exit = A('E&xit', self.close, 'Alt+F4')
        self.a_undo = A('&Undo', lambda: self._ed('undo'), QKeySequence.Undo)
        self.a_redo = A('&Redo', lambda: self._ed('redo'), ['Ctrl+Y', 'Ctrl+Shift+Z'])
        self.a_cut = A('Cu&t', lambda: self._ed('cut'), QKeySequence.Cut)
        self.a_copy = A('&Copy', lambda: self._ed('copy'), QKeySequence.Copy)
        self.a_paste = A('&Paste', lambda: self._ed('paste'), QKeySequence.Paste)
        self.a_select = A('Select &All', lambda: self._ed('selectAll'), QKeySequence.SelectAll)
        self.a_find = A('&Find…', self.find, QKeySequence.Find)
        self.a_find_next = A('Find &Next', self.find_next, 'F3')
        self.a_replace = A('&Replace…', self.replace, 'Ctrl+H')
        self.a_goto = A('&Go to Line…', self.go_to_line, 'Ctrl+G')
        self.a_nav = self.nav_dock.toggleViewAction()
        self.a_nav.setText('&Project Navigator')
        self.a_output = A('&Output Panel', self.toggle_output, 'F10', 'Show or hide the output panel')
        self.a_output.setCheckable(True)
        self.a_problems = A('Pro&blems', self.show_problems, 'Ctrl+Shift+M')
        self.a_inspector = self.inspector_dock.toggleViewAction()
        self.a_inspector.setText('Hardware &Inspector')
        self.a_cartdock = self.cart_dock.toggleViewAction()
        self.a_cartdock.setText('&Cartridge Shelf')
        self.a_dual = A('&Dual-Pane Browse', self.toggle_dual)
        self.a_dual.setCheckable(True)
        self.a_reset = A('&Reset Window Layout', self.reset_layout, None,
                         'Restore the factory window layout (documents stay open)')
        self.a_browse = A('&Browse Project Folder', lambda: self.browse(self.root), 'Ctrl+E')
        self.a_newgame = A('&New Game Project…', self.new_game_project)
        self.a_refresh = A('Re&fresh Navigator', self.refresh_navigator)
        self.a_build = A('&Build', lambda: self.start('build'), ['F7', 'Ctrl+Shift+B'],
                         'Build the target for the work in front of you (F7)')
        self.a_build_all = A('Build All &Firmware Stages', self.build_all_firmware)
        self.a_tests = A('Run &Tests', lambda: self.start('test'), 'Ctrl+T', 'Run the tests for this target')
        self.a_stop = A('&Stop', self.stop_process, 'Ctrl+Break')
        self.a_next = A('&Next Problem', lambda: self.step_problem(1), 'F8')
        self.a_prev = A('&Previous Problem', lambda: self.step_problem(-1), 'Shift+F8')
        self.a_run = A('&Run in Host Simulator', lambda: self.start('run'), 'F5',
                       'Build if needed, then run the game in the host simulator (F5)')
        self.a_boot = A('Host &Boot Diagnostics', lambda: (self.inspector_dock.show(), self.inspector_dock.raise_()))
        self.a_pkg = A('&Package Example Cartridge', self.package_example)
        self.a_import = A('&Import Cartridge…', self.import_cartridge_dialog)
        self.a_inspect_cart = A('In&spect Selected Cartridge', self.inspect_cartridge)
        self.a_stream = A('&Model Cartridge Streaming', self.stream_cartridge)
        self.a_palette = A('&Command Palette…', self.command_palette, 'Ctrl+Shift+P')
        self.a_doctor = A('&System Check', lambda: self.run_tool(['doctor'], 'System check'))
        self.a_hw = A('&Hardware Facts', lambda: self.run_tool(['hw', 'inspect'], 'Hardware facts'))
        self.a_keys = A('&Keyboard Shortcuts', self.show_keys, 'F1')
        self.a_about = A('&About ARC-1 Workbench', self.show_about)
        for a in (self.a_open, self.a_save):
            a.setIconVisibleInMenu(False)

    def _build_menus(self):
        mb = self.menuBar()

        def menu(title, items):
            m = mb.addMenu(title)
            for it in items:
                if it is None:
                    m.addSeparator()
                elif isinstance(it, QMenu):
                    m.addMenu(it)
                else:
                    m.addAction(it)
            return m
        self.recent_menu = QMenu('Open &Recent', self)
        self.recent_menu.aboutToShow.connect(self._fill_recent_menu)
        menu('&File', [self.a_new, self.a_open, self.a_quick, self.recent_menu, None, self.a_save, self.a_save_all,
                       None, self.a_close, None, self.a_exit])
        menu('&Edit', [self.a_undo, self.a_redo, None, self.a_cut, self.a_copy, self.a_paste, self.a_select, None,
                       self.a_find, self.a_find_next, self.a_replace, self.a_goto])
        menu('&View', [self.a_nav, self.a_output, self.a_problems, None, self.a_inspector, self.a_cartdock, None,
                       self.a_dual, None, self.a_reset])
        menu('&Project', [self.a_browse, self.a_newgame, None, self.a_refresh])
        self.target_menu = QMenu('&Target', self)
        self.target_group = QActionGroup(self)
        for tid, t in engine.TARGETS.items():
            a = QAction(t['label'], self, checkable=True)
            a.setData(tid)
            a.triggered.connect(lambda _=False, x=tid: self.set_target(x))
            self.target_group.addAction(a)
            self.target_menu.addAction(a)
        menu('&Build', [self.a_build, self.a_tests, self.target_menu, None, self.a_build_all, None, self.a_next,
                        self.a_prev, None, self.a_stop])
        menu('&Debug', [self.a_run, None, self.a_boot])
        menu('&Cartridge', [self.a_pkg, self.a_import, self.a_inspect_cart, self.a_stream, None, self.a_cartdock])
        menu('&Tools', [self.a_palette, None, self.a_doctor, self.a_hw])
        menu('&Help', [self.a_keys, None, self.a_about])
        badge = QLabel(engine.device_status()['badge'])
        badge.setObjectName('deviceBadge')
        badge.setToolTip('Results come from this PC. No ARC-1 board is connected or tested.')
        mb.setCornerWidget(badge, Qt.TopRightCorner)
        self.badge = badge

    def _build_toolbar(self):
        tb = QToolBar('Standard', self)
        tb.setObjectName('StandardToolbar')
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(tb)
        tb.addAction(self.a_open)
        tb.addAction(self.a_save)
        tb.addSeparator()
        build_btn = QToolButton()
        build_btn.setText('Build')
        build_btn.setToolTip('Build (F7)')
        build_btn.setPopupMode(QToolButton.MenuButtonPopup)
        build_btn.setDefaultAction(self.a_build)
        bm = QMenu(build_btn)
        bm.addAction(self.a_build)
        bm.addAction(self.a_build_all)
        bm.addSeparator()
        bm.addMenu(self.target_menu)
        build_btn.setMenu(bm)
        tb.addWidget(build_btn)
        self.run_btn = QToolButton()
        self.run_btn.setDefaultAction(self.a_run)
        self.run_btn.setText('Run')
        tb.addWidget(self.run_btn)
        tests_btn = QToolButton()
        tests_btn.setDefaultAction(self.a_tests)
        tests_btn.setText('Tests')
        tb.addWidget(tests_btn)
        tb.addSeparator()
        tb.addWidget(QLabel(' Target: '))
        self.target_combo = QComboBox()
        self.target_combo.setAccessibleName('Build target')
        for tid, t in engine.TARGETS.items():
            self.target_combo.addItem(t['label'], tid)
        self.target_combo.currentIndexChanged.connect(
            lambda i: self.set_target(self.target_combo.itemData(i)))
        tb.addWidget(self.target_combo)
        self.toolbar = tb

    def _build_status(self):
        sb = self.statusBar()
        self.context_label = QLabel()
        self.device_label = QLabel(engine.device_status()['text'])
        sb.addPermanentWidget(self.context_label)
        sb.addPermanentWidget(self.device_label)

    def _apply_default_layout(self):
        """The factory layout: navigator ~236 px, everything else hidden."""
        L = self.session.layout
        self.nav_dock.show()
        self.output_dock.hide()
        self.inspector_dock.hide()
        self.cart_dock.hide()
        self.resizeDocks([self.nav_dock], [L.get('navigator_width', 236)], Qt.Horizontal)
        self.resizeDocks([self.output_dock], [L.get('output_height', 170)], Qt.Vertical)
        self.a_output.setChecked(False)

    # ---------------------------------------------------------------- session
    def restore_session(self):
        s = self.session.state
        L = self.session.layout
        try:
            if L.get('geometry'):
                self.restoreGeometry(decode_bytes(L['geometry']))
            if L.get('dock_state'):
                self.restoreState(decode_bytes(L['dock_state']), engine_layout_version())
        except (ValueError, TypeError):
            pass
        self.output_dock.setVisible(bool(L.get('output_visible')))
        self.a_output.setChecked(self.output_dock.isVisible())
        tab = L.get('output_tab', 'Output')
        for i in range(self.output_tabs.count()):
            if self.output_tabs.tabText(i) == tab:
                self.output_tabs.setCurrentIndex(i)
        self.set_target(s.get('target') or engine.DEFAULT_TARGET)
        active = None
        for d in s['documents']:
            p = self.root / d['path']
            try:
                ed = self.open_document(p, remember=False)
            except Exception:  # noqa: BLE001 - a vanished file must not stop start-up
                ed = None
            if ed is not None:
                ed.go_to(d['line'], d['column'])
                if d['path'] == s.get('active'):
                    active = ed
        if active is not None:
            self.tabs.setCurrentWidget(active)
        if not s['documents'] and self.screen() is not None \
                and self.screen().availableGeometry().width() >= 1900 and not L.get('dock_state'):
            # Wide monitors show the inspector beside the editor from the start.
            self.inspector_dock.show()

    def save_session(self):
        docs = []
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, CodeEditor):
                line, col = w.position()
                docs.append((engine.rel(w.path, self.root), line, col))
        cur = self.tabs.currentWidget()
        active = engine.rel(cur.path, self.root) if isinstance(cur, CodeEditor) else None
        self.session.remember_documents(docs, active)
        self.session.set_layout(geometry=encode_bytes(self.saveGeometry()),
                                dock_state=encode_bytes(self.saveState(engine_layout_version())),
                                output_visible=self.output_dock.isVisible(),
                                navigator_width=max(160, min(600, self.nav_dock.width())),
                                output_height=max(80, min(700, self.output_dock.height())))
        self.session.save()

    def reset_layout(self):
        """One command to get back to the factory layout if panels get lost."""
        self.restoreState(self.factory_state, engine_layout_version())
        self.session.reset_layout()
        self._apply_default_layout()
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, BrowseTab):
                w.set_dual(False)
        self.a_dual.setChecked(False)
        self.statusBar().showMessage('Window layout restored to the factory default', 5000)

    # ---------------------------------------------------------------- documents
    def document_for(self, path):
        p = Path(path).resolve()
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, CodeEditor) and w.path.resolve() == p:
                return w
        return None

    def open_document(self, path, remember=True):
        path = Path(path)
        existing = self.document_for(path)
        if existing is not None:
            self.tabs.setCurrentWidget(existing)
            return existing
        if path.suffix not in EDIT_EXT:
            self.message('Not a text document', '%s is not a source or text file the editor can open.' % path.name)
            return None
        try:
            path = editable_file(path, self.root)
            text = path.read_text(encoding='utf-8')
        except (ValueError, OSError, UnicodeError) as e:
            self.message('Cannot open file', str(e), error=True)
            return None
        ed = CodeEditor(path, self.root)
        ed.setPlainText(text)
        ed.document().setModified(False)
        if fileops.is_read_only(self.root, path):
            ed.setReadOnly(True)
        ed.document().modificationChanged.connect(lambda _m, e=ed: self._retitle(e))
        ed.cursorPositionChanged.connect(self.update_document_info)
        self._close_start()
        i = self.tabs.addTab(ed, path.name)
        self.tabs.setTabToolTip(i, engine.rel(path, self.root))
        self.tabs.setCurrentIndex(i)
        if remember:
            self.session.touch_recent(engine.rel(path, self.root))
        game = engine.game_for(path, self.root)
        if game:
            self.session.set_last_game(game)
        self.update_document_info()
        return ed

    def _retitle(self, ed):
        i = self.tabs.indexOf(ed)
        if i >= 0:
            self.tabs.setTabText(i, ('● ' if ed.document().isModified() else '') + ed.path.name)
        self.update_document_info()

    def current_editor(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def _ed(self, name):
        ed = self.current_editor() or (QApplication.focusWidget() if isinstance(
            QApplication.focusWidget(), (QLineEdit, QPlainTextEdit)) else None)
        if ed is not None and hasattr(ed, name):
            getattr(ed, name)()

    def save_document(self, ed=None):
        ed = ed or self.current_editor()
        if ed is None:
            return True
        if ed.isReadOnly():
            self.message('Read-only', '%s is recorded evidence and cannot be changed here.' % ed.path.name)
            return False
        try:
            editable_file(ed.path, self.root)
            fd, tmp = tempfile.mkstemp(prefix='.arc1-edit-', dir=ed.path.parent)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
                    f.write(ed.toPlainText())
                os.replace(tmp, ed.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        except (OSError, ValueError) as e:
            self.message('Save failed', str(e), error=True)
            return False
        ed.document().setModified(False)
        self.statusBar().showMessage('Saved ' + engine.rel(ed.path, self.root), 4000)
        return True

    def save_all(self):
        ok = True
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, CodeEditor) and w.document().isModified():
                ok = self.save_document(w) and ok
        return ok

    def close_tab(self, index):
        w = self.tabs.widget(index)
        if w is None:
            return True
        if isinstance(w, CodeEditor) and w.document().isModified():
            ans = self.ask_save(w.path.name)
            if ans == 'cancel':
                return False
            if ans == 'save' and not self.save_document(w):
                return False
        self.tabs.removeTab(index)
        w.deleteLater()
        if self.tabs.count() == 0:
            self.show_start()
        return True

    def show_start(self):
        for i in range(self.tabs.count()):
            if isinstance(self.tabs.widget(i), StartPage):
                self.tabs.setCurrentIndex(i)
                self.tabs.widget(i).refresh()
                return
        page = StartPage(self)
        self.tabs.addTab(page, 'Start')
        self.tabs.setCurrentWidget(page)

    def _close_start(self):
        for i in range(self.tabs.count() - 1, -1, -1):
            if isinstance(self.tabs.widget(i), StartPage):
                w = self.tabs.widget(i)
                self.tabs.removeTab(i)
                w.deleteLater()

    def browse(self, folder):
        """Clicking a folder opens (or reuses) the Browse tab: a File Manager listing."""
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, BrowseTab):
                w.pane.navigate(folder)
                self.tabs.setTabText(i, w.title())
                self.tabs.setCurrentIndex(i)
                return w
        self._close_start()
        tab = BrowseTab(self, folder)
        tab.left.changed.connect(lambda t=tab: self.tabs.setTabText(self.tabs.indexOf(t), t.title()))
        tab.set_dual(self.a_dual.isChecked())
        i = self.tabs.addTab(tab, tab.title())
        self.tabs.setCurrentIndex(i)
        return tab

    def toggle_dual(self):
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, BrowseTab):
                w.set_dual(self.a_dual.isChecked())
        self.update_document_info()

    def update_document_info(self):
        w = self.tabs.currentWidget()
        target = engine.TARGETS[self.target()]
        short = target['short']
        if isinstance(w, CodeEditor) and engine.game_for(w.path, self.root):
            short = engine.TARGETS['game']['short']   # Build will use this game, whatever is selected
        if isinstance(w, CodeEditor):
            game = engine.game_for(w.path, self.root)
            line, col = w.position()
            where = ('Host game %s' % Path(game).name) if game else target['short']
            text = '%s · %s · Simulation target%s      Ln %d, Col %d' % (
                engine.language_for(w.path), where, ' · read-only evidence' if w.isReadOnly() else '', line, col)
            lang = engine.language_for(w.path).split(' ')[0]
            self.setWindowTitle('%s%s — ARC-1 Workbench' % ('● ' if w.document().isModified() else '', w.path.name))
        elif w is not None and hasattr(w, 'info'):
            text = w.info()
            lang = '—'
            self.setWindowTitle('%s — ARC-1 Workbench' % w.title())
        else:
            text, lang = '', '—'
            self.setWindowTitle('ARC-1 Workbench')
        self.doc_info.setText(text)
        self.context_label.setText('ARC-1 · %s · %s · UTF-8' % (short, lang))

    # ---------------------------------------------------------------- navigator
    def refresh_navigator(self):
        expanded = {self._nav_path(it) for it in self._nav_items() if it.isExpanded()}
        self.nav.clear()
        top = QTreeWidgetItem(['ARC-1'])
        top.setData(0, Qt.UserRole, str(self.root))
        top.setToolTip(0, str(self.root))
        self.nav.addTopLevelItem(top)
        for label, folder, tip in engine.NAVIGATOR:
            it = QTreeWidgetItem([label])
            it.setToolTip(0, tip)
            if folder and (self.root / folder).is_dir():
                it.setData(0, Qt.UserRole, str(self.root / folder))
                it.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
                it.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
            else:
                it.setDisabled(True)
            top.addChild(it)
        top.setExpanded(True)
        for it in self._nav_items():
            if self._nav_path(it) in expanded and it is not top:
                it.setExpanded(True)

    def _nav_items(self):
        out = []
        stack = [self.nav.topLevelItem(i) for i in range(self.nav.topLevelItemCount())]
        while stack:
            it = stack.pop()
            out.append(it)
            stack.extend(it.child(i) for i in range(it.childCount()))
        return out

    @staticmethod
    def _nav_path(item):
        return item.data(0, Qt.UserRole)

    def _fill_nav_item(self, item):
        path = self._nav_path(item)
        if not path or item.data(0, Qt.UserRole + 1):
            return
        item.setData(0, Qt.UserRole + 1, True)
        if item.parent() is None:
            return  # the project node lists the logical areas, already present
        try:
            rows = fileops.listing(self.root, path)
        except (fileops.FileOpError, OSError):
            rows = []
        for r in rows:
            if r['name'] in ('build', 'reports'):
                continue
            child = QTreeWidgetItem([r['name']])
            child.setData(0, Qt.UserRole, str(self.root / r['path']))
            child.setToolTip(0, r['path'])
            if r['is_dir']:
                child.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
                child.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
            else:
                child.setIcon(0, self.style().standardIcon(QStyle.SP_FileIcon))
            item.addChild(child)

    def _nav_clicked(self, item, _col=0):
        p = self._nav_path(item)
        if p and Path(p).is_dir():
            self.browse(Path(p))

    def _nav_activated(self, item, _col=0):
        p = self._nav_path(item)
        if p and Path(p).is_file():
            self.open_document(Path(p))

    # ---------------------------------------------------------------- dialogs
    def message(self, title, text, error=False):
        (QMessageBox.warning if error else QMessageBox.information)(self, title, text)

    def confirm(self, title, text):
        return QMessageBox.question(self, title, text, QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No) == QMessageBox.Yes

    def ask_save(self, name):
        ans = QMessageBox.question(self, 'Unsaved changes', 'Save changes to %s?' % name,
                                   QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        return {QMessageBox.Save: 'save', QMessageBox.Discard: 'discard'}.get(ans, 'cancel')

    def open_dialog(self):
        f, _ = QFileDialog.getOpenFileName(self, 'Open', str(self.root),
                                           'Source and text files (*.c *.h *.s *.S *.ld *.py *.md *.json *.txt '
                                           '*.sprite *.replay *.csv);;All files (*)')
        if f:
            self.open_document(Path(f))

    def quick_open(self):
        dlg = QuickOpen(self)
        if dlg.exec() == QDialog.Accepted and dlg.chosen():
            self.open_document(self.root / dlg.chosen())

    def _fill_recent_menu(self):
        self.recent_menu.clear()
        for r in self.session.state['recent']:
            if (self.root / r).is_file():
                a = self.recent_menu.addAction(r)
                a.triggered.connect(lambda _=False, x=r: self.open_document(self.root / x))
        if not self.recent_menu.actions():
            a = self.recent_menu.addAction('(no recent files)')
            a.setEnabled(False)

    def new_file(self):
        folder = self.root / 'firmware'
        w = self.tabs.currentWidget()
        if isinstance(w, BrowseTab):
            folder = w.pane.folder
        elif isinstance(w, CodeEditor):
            folder = w.path.parent
        name, ok = QInputDialog.getText(self, 'New File', 'Create in %s/\nFile name:' % engine.rel(folder, self.root),
                                        text='untitled.c')
        if ok and name.strip():
            try:
                p = fileops.new_file(self.root, folder, name.strip())
            except (fileops.FileOpError, OSError) as e:
                self.message('Cannot create file', str(e), error=True)
                return
            self.refresh_navigator()
            if p.suffix in EDIT_EXT:
                self.open_document(p)

    def find(self):
        ed = self.current_editor()
        if ed is None:
            return
        text, ok = QInputDialog.getText(self, 'Find', 'Find what:', text=ed.textCursor().selectedText() or self.find_text)
        if ok and text:
            self.find_text = text
            self.find_next()

    def find_next(self):
        ed = self.current_editor()
        if ed is None or not self.find_text:
            return
        if not ed.find(self.find_text):
            c = ed.textCursor()
            c.movePosition(QTextCursor.Start)
            ed.setTextCursor(c)
            if not ed.find(self.find_text):
                self.statusBar().showMessage('"%s" was not found' % self.find_text, 4000)

    def replace(self):
        ed = self.current_editor()
        if ed is None or ed.isReadOnly():
            return
        needle, ok = QInputDialog.getText(self, 'Replace', 'Find what:', text=self.find_text)
        if not ok or not needle:
            return
        repl, ok = QInputDialog.getText(self, 'Replace', 'Replace with:')
        if not ok:
            return
        count = ed.toPlainText().count(needle)
        if count and self.confirm('Replace', 'Replace %d occurrence(s) in %s?' % (count, ed.path.name)):
            c = ed.textCursor()
            c.beginEditBlock()        # one Undo step reverts the whole replace
            c.select(QTextCursor.Document)
            c.insertText(ed.toPlainText().replace(needle, repl))
            c.endEditBlock()

    def go_to_line(self):
        ed = self.current_editor()
        if ed is None:
            return
        line, ok = QInputDialog.getInt(self, 'Go to Line', 'Line number (1–%d):' % ed.blockCount(),
                                       ed.position()[0], 1, ed.blockCount())
        if ok:
            ed.go_to(line)

    def command_palette(self):
        actions = [a for a in self.findChildren(QAction) if a.text() and a.isEnabled() and not a.menu()]
        names = sorted({a.text().replace('&', '').rstrip('…') for a in actions})
        choice, ok = QInputDialog.getItem(self, 'Command Palette', 'Command:', names, 0, True)
        if ok:
            for a in actions:
                if a.text().replace('&', '').rstrip('…') == choice:
                    a.trigger()
                    return

    def new_game_project(self):
        name, ok = QInputDialog.getText(self, 'New Game Project',
                                        'Name (lowercase letters, digits, _):', text='mygame')
        if not ok or not name.strip():
            return
        self.run_tool(['new', name.strip(), '--dir', engine.GAMES_DIR], 'New game project',
                      then=lambda good: good and self._opened_new_game(name.strip()))

    def _opened_new_game(self, name):
        self.refresh_navigator()
        main = self.root / engine.GAMES_DIR / name / 'src' / 'main.c'
        if main.is_file():
            self.open_document(main)

    # ---------------------------------------------------------------- targets, build, test, run
    def target(self):
        return self.target_combo.currentData() or engine.DEFAULT_TARGET

    def set_target(self, tid):
        if tid not in engine.TARGETS:
            return
        i = self.target_combo.findData(tid)
        if i >= 0 and self.target_combo.currentIndex() != i:
            self.target_combo.setCurrentIndex(i)
        for a in self.target_group.actions():
            a.setChecked(a.data() == tid)
        self.session.set_target(tid)
        self.update_document_info()

    def active_path(self):
        ed = self.current_editor()
        return ed.path if ed else None

    def start(self, op):
        """Build (F7), Tests (Ctrl+T) or Run (F5) for the work in front of you."""
        if self.process.state() != QProcess.NotRunning:
            self.statusBar().showMessage('Wait for the current command to finish (Ctrl+Break stops it)', 5000)
            return
        try:
            p = engine.plan(op, self.target(), self.active_path(), self.session.state.get('last_game'), self.root)
        except ValueError as e:
            self.message('Nothing to %s' % op, str(e), error=True)
            return
        if not self.save_all():
            return
        self._then = None
        if op == 'run':
            # Run = build that game (the CLI refuses stale builds), then simulate.
            b = engine.plan('build', 'game', None, p.project, self.root)
            self.after_build = p
            self._launch(b)
        else:
            self.after_build = None
            self._launch(p)

    def build_all_firmware(self):
        p = engine.Plan('build', 'f133', list(engine.AGENT_ACTIONS['build.both']), None,
                        'Build all firmware stages', 'Build > Build All Firmware Stages')
        if self.process.state() == QProcess.NotRunning and self.save_all():
            self.after_build = None
            self._launch(p)

    def run_tool(self, argv, label, then=None):
        if self.process.state() != QProcess.NotRunning:
            self.statusBar().showMessage('Wait for the current command to finish', 5000)
            return
        self.after_build = None
        self._then = then
        self._launch(engine.Plan('tool', self.target(), list(argv), None, label, 'requested from the menu'),
                     show_output=True)

    def _launch(self, p, show_output=False):
        self.plan = p
        self.router.start(p.label)
        self.started_at = time.time()
        self.output.appendPlainText('\n> %s\n  (%s: %s)\n' % (p.command_line(), p.label, p.reason))
        if show_output:
            self.show_output('Output')
        self.statusBar().showMessage('%s…' % p.label)
        self.a_stop.setEnabled(True)
        args = p.process_args(self.root)
        self.process.start(args[0], args[1:])

    def _read_process(self):
        data = bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace')
        if data:
            self.router.append(data)
            self.output.moveCursor(QTextCursor.End)
            self.output.insertPlainText(data)
            self.output.ensureCursorVisible()

    def _process_finished(self, code, status):
        self._read_process()
        p = self.plan
        good = code == 0 and status == QProcess.NormalExit
        extra = engine.collect_output(p, '', self.started_at, self.root) if p else ''
        if extra:
            self.router.append(extra)
            self.output.appendPlainText(extra.strip())
        self.router.finish(code if good else (code or 1))
        self._fill_problems(p)
        errors = sum(1 for x in self.problems if x[0].severity in ('error', 'fatal error'))
        warnings = sum(1 for x in self.problems if x[0].severity == 'warning')
        verdict = 'succeeded' if good else ('failed' if code not in (3,) else 'is not available here')
        summary = '%s %s' % (p.label if p else 'Command', verdict)
        if errors or warnings:
            summary += ' — %d error(s), %d warning(s)' % (errors, warnings)
        self.output.appendPlainText('%s (exit %s)\n' % (summary, code))
        self.a_stop.setEnabled(False)
        if p and p.op == 'build' and p.project:
            self.session.set_last_game(p.project)
        if not good:
            self.after_build = None
            self.show_output('Problems' if self.problems else 'Output')
            if errors:
                summary += '   ·   F8 goes to the first error'
            self.statusBar().showMessage(summary)
        else:
            self.statusBar().showMessage(summary, 8000)
            nxt = self.after_build
            self.after_build = None
            if nxt is not None:
                self._launch(nxt)
                return
            if p and p.op == 'run':
                self._show_preview(p)
        then = getattr(self, '_then', None)
        self._then = None
        if then:
            then(good)

    def _fill_problems(self, p):
        self.problem_list.clear()
        self.problems = []
        for prob in self.router.problems:
            path = engine.resolve_problem_path(prob.source, p, self.root)
            self.problems.append((prob, path))
            sev = {'fatal error': 'Error', 'error': 'Error', 'warning': 'Warning'}.get(prob.severity, 'Note')
            shown = engine.rel(path, self.root) if path else prob.source
            item = QTreeWidgetItem([sev, prob.message, Path(shown).name, str(prob.line)])
            item.setToolTip(1, prob.message)
            item.setToolTip(2, shown)
            icon = {'Error': QStyle.SP_MessageBoxCritical, 'Warning': QStyle.SP_MessageBoxWarning}.get(
                sev, QStyle.SP_MessageBoxInformation)
            item.setIcon(0, self.style().standardIcon(icon))
            item.setData(0, Qt.UserRole, len(self.problems) - 1)
            if path is None:
                item.setToolTip(2, '%s (outside the project or not found)' % prob.source)
            self.problem_list.addTopLevelItem(item)
        self.problem_cursor = -1
        idx = self.output_tabs.indexOf(self.problem_list)
        n = len(self.problems)
        self.output_tabs.setTabText(idx, 'Problems (%d)' % n if n else 'Problems')

    def _problem_activated(self, item, _col=0):
        self.go_to_problem(item.data(0, Qt.UserRole))

    def go_to_problem(self, index):
        if not 0 <= index < len(self.problems):
            return False
        prob, path = self.problems[index]
        self.problem_cursor = index
        self.problem_list.setCurrentItem(self.problem_list.topLevelItem(index))
        if path is None:
            self.statusBar().showMessage('Cannot open %s: not found in the project' % prob.source, 6000)
            return False
        ed = self.open_document(path)
        if ed is None:
            return False
        ed.go_to(prob.line, prob.column or 1, problem=True)
        self.statusBar().showMessage('%s: %s' % (prob.severity.capitalize(), prob.message), 10000)
        return True

    def step_problem(self, delta):
        if not self.problems:
            self.statusBar().showMessage('No problems from the last build', 3000)
            return
        start = getattr(self, 'problem_cursor', -1)
        self.go_to_problem((start + delta) % len(self.problems))

    def stop_process(self):
        if self.process.state() != QProcess.NotRunning:
            self.after_build = None
            self.process.kill()
            self.output.appendPlainText('Stopped by user.')

    def _show_preview(self, p):
        frames = []
        sim_dir = self.root / p.project / 'build' / 'sim'
        for n in [int(x) for x in engine.RUN_DUMP.split(',')]:
            f = sim_dir / ('frame_%06d.ppm' % n)
            if f.is_file() and f.stat().st_mtime >= self.started_at - 1:
                frames.append((n, f))
        for i in range(self.tabs.count() - 1, -1, -1):
            if isinstance(self.tabs.widget(i), PreviewTab):
                w = self.tabs.widget(i)
                self.tabs.removeTab(i)
                w.deleteLater()
        tab = PreviewTab(self, p.project, frames)
        self.tabs.addTab(tab, tab.title())
        self.tabs.setCurrentWidget(tab)
        self.debug_view.setPlainText('HOST SIMULATION of %s: %d frames written to %s/build/sim/.\n'
                                     'Evidence class HOST_SIM. No ARC-1 device was used.'
                                     % (p.project, len(frames), p.project))

    # ---------------------------------------------------------------- output panel
    def toggle_output(self):
        self.output_dock.setVisible(not self.output_dock.isVisible())
        self.a_output.setChecked(self.output_dock.isVisible())

    def show_output(self, tab='Output'):
        self.output_dock.show()
        self.a_output.setChecked(True)
        for i in range(self.output_tabs.count()):
            if self.output_tabs.tabText(i).startswith(tab):
                self.output_tabs.setCurrentIndex(i)

    def show_problems(self):
        self.show_output('Problems')

    # ---------------------------------------------------------------- inspector and cartridges (R09 functions)
    def advance_boot(self):
        for stage in ('f133', 'nor', 'd213', 'fpga12', 'fpga45', 'ready'):
            if stage not in self.boot.history:
                try:
                    self.boot.mark(stage)
                except ValueError as e:
                    self.message('Cannot advance the diagnostic model', str(e), error=True)
                break
        self.refresh_boot()

    def reset_boot(self):
        self.boot = BootModel()
        self.refresh_boot()

    def refresh_boot(self):
        snap = self.boot.snapshot()
        self.lcd.setText('\n'.join(snap['lcd_rows']))
        self.inspector.setPlainText('HOST MODEL ONLY\nStage: %s\nChecks: %s\n\nThe real F133, D213 and FPGA state '
                                    'is UNKNOWN: no device is connected.' % (snap['stage'], ', '.join(snap['history'])))

    def refresh_shelf(self):
        from .launcher import games_on_shelf
        self.shelf.clear()
        for rec in games_on_shelf(self.root):
            item = QListWidgetItem(('✓ ' if rec.get('valid') else '! ') + rec['name'] + '  ' + rec.get('version', ''))
            item.setData(Qt.UserRole, rec)
            self.shelf.addItem(item)

    def _selected_cart(self):
        item = self.shelf.currentItem() or (self.shelf.item(0) if self.shelf.count() else None)
        if item is None:
            raise CartridgeError('No cartridge in the shelf')
        rec = item.data(Qt.UserRole)
        if not rec.get('valid'):
            raise CartridgeError(rec.get('error', 'Invalid cartridge'))
        return self.root / rec['path']

    def inspect_cartridge(self):
        try:
            r = inspect_cartridge(self._selected_cart())
        except (CartridgeError, OSError) as e:
            self.message('Cartridge', str(e), error=True)
            return
        self.cart_dock.show()
        self.cart_dock.raise_()
        self.output.appendPlainText('CARTRIDGE %s %s · %d assets · %d bytes · sha256 %s · no executable inside'
                                    % (r['name'], r['game_version'], r['asset_count'], r['asset_bytes'],
                                       r['cartridge_sha256']))
        self.show_output('Output')

    def package_example(self):
        try:
            r = package_game(self.root / 'examples' / 'hello_arc1', self.root / 'cartridges' / 'hello_arc1.arc1cart')
        except (CartridgeError, OSError) as e:
            self.message('Package failed', str(e), error=True)
            return
        self.refresh_shelf()
        self.output.appendPlainText('Packaged host cartridge ' + r['name'])
        self.show_output('Output')

    def import_cartridge_dialog(self):
        f, _ = QFileDialog.getOpenFileName(self, 'Import Cartridge', str(Path.home()), 'ARC-1 cartridges (*.arc1cart)')
        if not f:
            return
        try:
            res = verify_drop(Path(f))
        except (CartridgeError, OSError) as e:
            self.message('Import rejected', str(e), error=True)
            return
        dest = self.root / 'cartridges' / Path(f).name
        if dest.exists() and not self.confirm('Replace cartridge', '%s already exists. Replace it?' % dest.name):
            return
        fd, tmp = tempfile.mkstemp(prefix='.arc1-import-', dir=dest.parent)
        try:
            with os.fdopen(fd, 'wb') as out, open(f, 'rb') as src:
                out.write(src.read())
            if inspect_cartridge(Path(tmp))['cartridge_sha256'] != res['cartridge_sha256']:
                raise CartridgeError('the copy differs from the original')
            os.replace(tmp, dest)
        except (CartridgeError, OSError) as e:
            self.message('Import rejected', str(e), error=True)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        self.refresh_shelf()

    def stream_cartridge(self):
        try:
            r = simulate_stream(self._selected_cart())
        except (CartridgeError, OSError) as e:
            self.message('Streaming model', str(e), error=True)
            return
        self.output.appendPlainText('HOST STREAMING MODEL: %s frames, %s simulated stalls, physical USB tested: %s'
                                    % (r['frames'], r['simulated_stall_frames'], r['physical_usb_tested']))
        self.show_output('Output')

    # ---------------------------------------------------------------- help
    def show_keys(self):
        rows = [('Ctrl+P', 'Find a file'), ('Ctrl+O / Ctrl+S', 'Open / Save'), ('Ctrl+Shift+S', 'Save all'),
                ('Ctrl+F, F3, Ctrl+H', 'Find, find next, replace'), ('Ctrl+G', 'Go to line'),
                ('Ctrl+Z / Ctrl+Y', 'Undo / Redo'), ('Ctrl+E', 'Browse the project folder'),
                ('F7 or Ctrl+Shift+B', 'Build the relevant target'), ('Ctrl+T', 'Run tests'),
                ('F5', 'Run in the host simulator'), ('F8 / Shift+F8', 'Next / previous problem'),
                ('F10', 'Show or hide the output panel'), ('F2 / Del', 'Rename / delete in Browse'),
                ('Ctrl+Shift+P', 'Command palette'), ('View > Reset Window Layout', 'Get the factory layout back')]
        self.message('Keyboard Shortcuts', '\n'.join('%-26s %s' % r for r in rows))

    def show_about(self):
        self.message('About ARC-1 Workbench',
                     'ARC-1 Workbench %s (Qt %s).\n\nHost tools only: builds, tests and the game simulator run on this '
                     'PC. No ARC-1 board exists yet; nothing is flashed or deployed, and firmware stage images are '
                     'NOT BOOTABLE. Fabrication is on HOLD.\n\nAgents use the same engine through '
                     '"python arc1 agent".' % (VERSION, qt_version()))

    def closeEvent(self, event):
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, CodeEditor) and w.document().isModified():
                self.tabs.setCurrentWidget(w)
                ans = self.ask_save(w.path.name)
                if ans == 'cancel' or (ans == 'save' and not self.save_document(w)):
                    event.ignore()
                    return
        if self.process.state() != QProcess.NotRunning:
            self.process.kill()
            self.process.waitForFinished(2000)
        self.save_session()
        event.accept()


def engine_layout_version():
    from .session import LAYOUT_VERSION
    return LAYOUT_VERSION


def qt_version():
    from PySide6 import __version__
    return __version__


def make_app(argv=None):
    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationName('ARC-1 Workbench')
    app.setOrganizationName('ARC-1')
    app.setStyle('Fusion')
    app.setStyleSheet(QSS)
    return app


def main():
    app = make_app()
    w = WorkbenchWindow()
    w.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
