"""Arc Ledger R10 "Classic" — Qt 6 main screen.

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
from .text_prompts import writing_prompt

from hashlib import sha256
import os
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import threading
import time
import uuid

from PySide6.QtCore import QDir, QEvent, QPoint, QPointF, QPropertyAnimation, QProcess, QRect, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QActionGroup, QBrush, QColor, QDesktopServices, QFont, QFontDatabase, QIcon, QImage, QKeySequence, QPainter, QPainterPath, QPalette, QPen, QPixmap, QRegion, QTextDocument, QTextCursor, QTextFormat
from PySide6.QtWidgets import QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDockWidget, QFileDialog, QFileSystemModel, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QGraphicsScene, QGraphicsView, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy, QSlider, QScrollArea, QSplitter, QStackedWidget, QStatusBar, QStyle, QTabWidget, QTextBrowser, QTextEdit, QToolButton, QToolTip, QTreeView, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from . import board_view, clip, dashboard, engine, fileops, hardware_nav, hardware_overview, manual_index, nor_staging, readiness, resources, tool_inventory, viewer_data, viewer_tabs
from .instruments_qt import InstrumentTabs, ClipDock
from .preview_frames import discover as discover_preview_frames
from . import project_services, activity
from .project_tabs import ProjectDeskTab, ProjectSearchTab
from .editor_recovery import RecoveryStore, file_hash
from .execution_lock import ExecutionLock
from .bootlogic import BootModel
from .cartridge import CartridgeError, inspect_cartridge, package_game, simulate_stream
from .output_router import OutputRouter
from .qt_contract import editable_file, verify_drop
from .session import Session, decode_bytes, encode_bytes
from .home_qt import WorkshopHome

ROOT = engine.ROOT
from . import VERSION
from . import locations
EDIT_EXT = {'.c', '.h', '.s', '.S', '.py', '.md', '.json', '.txt', '.ld', '.cmd', '.sh', '.yaml', '.yml',
            '.csv','.jsonl', '.sprite', '.replay', '.js', '.mjs', '.css', '.html', '.webmanifest',
            '.kicad_sch', '.kicad_pcb', '.kicad_pro', '.cpp', '.hpp', '.log', '.sv', '.v', '.vhd', '.lpf', '.xml'}
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


class _Minimap(QWidget):
    """Clickable, full-document overview for the source editor."""

    WIDTH = 76

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setObjectName('sourceMinimap')
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor('#f3eee4'))
        total = max(1, self.editor.blockCount())
        height = max(1, self.height())
        first = self.editor.firstVisibleBlock().blockNumber()
        visible = max(1, self.editor.viewport().height() // max(1, self.editor.fontMetrics().height()))
        top = int(first * height / total)
        bottom = min(height, max(top + 3, int((first + visible) * height / total)))
        painter.fillRect(0, top, self.width(), bottom - top, QColor('#e8dac8'))
        painter.setPen(QColor('#83909a'))
        # Sample at most one source line per pixel so large generated files
        # do not make repaint time proportional to document length.
        for y in range(height):
            block = self.editor.document().findBlockByNumber(min(total - 1, y * total // height))
            if block.isValid() and block.text().strip():
                length = min(self.width() - 8, max(3, len(block.text().expandtabs(4)) // 2))
                painter.drawLine(4, y, 4 + length, y)
        painter.setPen(QColor('#ff7a3c'))
        painter.drawRect(0, top, self.width() - 1, max(2, bottom - top) - 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            line = min(self.editor.blockCount(), max(1, int(event.position().y() * self.editor.blockCount() / max(1, self.height())) + 1))
            self.editor.go_to(line)
            event.accept()
            return
        super().mousePressEvent(event)


class CodeEditor(QPlainTextEdit):
    """Plain-text source editor with line numbers, a current-line band and a
    problem marker. Undo/redo, cut/copy/paste come from Qt."""
    def __init__(self, path, root):
        super().__init__()
        self.path = Path(path)
        self.root = Path(root)
        self.problem_line = None
        self.setObjectName('sourceEditor')
        from .reading_profile import DEFAULT
        self.setFont(mono_font(DEFAULT['code_pt']))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)
        self.gutter = _Gutter(self)
        self.minimap = _Minimap(self)
        self.blockCountChanged.connect(lambda _: self._update_margins())
        self.document().contentsChanged.connect(self.minimap.update)
        self.verticalScrollBar().valueChanged.connect(self.minimap.update)
        self.updateRequest.connect(self._update_gutter)
        self.cursorPositionChanged.connect(self._highlight)
        self._update_margins()
        self._highlight()
        self.highlighter = (viewer_tabs.SourceHighlighter(self.document(), self.path.suffix, paper=True)
                            if self.path.suffix.lower() in viewer_tabs.SOURCE_FORMATS else None)
        if self.path.suffix.lower() in ('.txt', '.md', '.log', '.csv'):
            self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

    def _update_margins(self):
        self.setViewportMargins(self.gutter_width(), 0, self.minimap.WIDTH, 0)
        self.minimap.update()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type()==QEvent.FontChange and hasattr(self,'gutter'):
            self._update_margins()

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
        self.minimap.setGeometry(QRect(cr.right() - self.minimap.WIDTH + 1, cr.top(), self.minimap.WIDTH, cr.height()))
        self.minimap.update()

    def paint_gutter(self, event):
        p = QPainter(self.gutter)
        p.fillRect(event.rect(), QColor('#f3eee4'))
        p.setPen(QColor('#d8cdbd'))
        p.drawLine(self.gutter.width() - 1, event.rect().top(), self.gutter.width() - 1, event.rect().bottom())
        block = self.firstVisibleBlock()
        n = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        current = self.textCursor().blockNumber()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                if self.problem_line == n + 1:
                    p.fillRect(0, top, self.gutter.width() - 1, bottom - top, QColor('#f8e5e1'))
                p.setPen(QColor('#9b3f00') if n == current else QColor('#687482'))
                p.drawText(0, top, self.gutter.width() - 7, self.fontMetrics().height(), Qt.AlignRight, str(n + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            n += 1

    def _highlight(self):
        extra = []
        line = QTextEdit.ExtraSelection()
        line.format.setBackground(QColor('#f2e9da'))
        line.format.setProperty(QTextFormat.FullWidthSelection, True)
        line.cursor = self.textCursor()
        line.cursor.clearSelection()
        extra.append(line)
        if self.problem_line:
            block = self.document().findBlockByNumber(self.problem_line - 1)
            if block.isValid():
                mark = QTextEdit.ExtraSelection()
                mark.format.setBackground(QColor('#f8e5e1'))
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


# --------------------------------------------------------------------------- browse (the Finder as a room)

class BrowsePane(QWidget):
    """UI-04 (AGENT-01): the old Windows-File-Manager pane (New File, New Folder, Rename, Duplicate, Delete) is retired.
    A Browse pane is now the Finder's listing (`finder_qt.FinderPage` without the Today place), read-only by design:
    looking is `ledger.browse`; changing stays with the Files room. The name and the callers' surface stay: `navigate`,
    `folder`, `title`, `info`, `go_up`, `selected`, the `changed` signal."""
    changed = Signal()

    def __init__(self, window, folder):
        super().__init__()
        from .finder_qt import FinderPage
        self.window_ = window
        self.root = window.root
        self.finder = FinderPage(window, with_today=False)
        self.finder.is_home = False
        self.finder.changed.connect(self.changed)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.finder)
        self.navigate(folder)

    @property
    def folder(self):
        return self.finder.folder

    def navigate(self, folder):
        return self.finder.go(str(folder))

    def go_up(self):
        return self.finder.up()

    def selected(self):
        entry = self.finder.current_entry()
        return Path(self.finder.entry_path(entry)) if entry else None

    def title(self):
        return self.finder.title()

    def info(self):
        return self.finder.info()


class BrowseTab(QWidget):
    """One Browse tab: a single Finder listing, optionally two side by side (dual pane)."""
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
        self.left.changed.connect(window.update_document_info)

    @property
    def pane(self):
        return self.left

    def set_dual(self, on):
        if on and self.right is None:
            self.right = BrowsePane(self.window_, self.left.folder or self.window_.root)
            self.split.addWidget(self.right)
        elif not on and self.right is not None:
            self.right.setParent(None)
            self.right.deleteLater()
            self.right = None

    def title(self):
        return self.left.title()

    def info(self):
        return self.left.info() + ('  ·  dual pane' if self.right else '')


class ManualTab(QWidget):
    """Searchable index of active R10 documents; opens files in editor tabs."""
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        heading = QLabel('R10 Manual')
        heading.setObjectName('heading')
        layout.addWidget(heading)
        note = QLabel('Current Workbench documents only · R10 hardware remains at fabrication HOLD')
        note.setObjectName('simBanner')
        layout.addWidget(note)
        row = QHBoxLayout()
        self.query = QLineEdit()
        writing_prompt(self.query, 'Search titles and document contents…')
        self.query.setAccessibleName('Search R10 manual')
        self.group = QComboBox()
        self.group.setAccessibleName('Manual subsystem filter')
        self.group.addItems(['All'] + sorted({e.group for e in manual_index.available(window.root)}))
        row.addWidget(self.query, 1)
        row.addWidget(self.group)
        layout.addLayout(row)
        self.results = QListWidget()
        self.results.setAccessibleName('R10 manual results')
        layout.addWidget(self.results, 1)
        self.count = QLabel()
        layout.addWidget(self.count)
        self.query.textChanged.connect(self.refresh)
        self.group.currentTextChanged.connect(self.refresh)
        self.results.itemActivated.connect(self.open_entry)
        self.results.itemDoubleClicked.connect(self.open_entry)
        self.refresh()

    def refresh(self, *_):
        self.results.clear()
        entries = manual_index.search(self.window_.root, self.query.text(), self.group.currentText())
        for entry in entries:
            item = QListWidgetItem('%s  ·  %s  [%s]\n%s' % (
                entry.title, entry.group, entry.evidence, entry.description))
            item.setData(Qt.UserRole, entry.path)
            item.setToolTip(entry.path)
            item.setSizeHint(QSize(0, 44))
            self.results.addItem(item)
        self.count.setText('%d current R10 documents · Select a row and press Enter to open it' % len(entries))

    def open_entry(self, item):
        path = item.data(Qt.UserRole)
        if path:
            self.window_.open_document(self.window_.root / path)

    def title(self):
        return 'R10 Manual'

    def info(self):
        return 'R10 document index · design records are not board measurements'


class BoardCanvas(QGraphicsView):
    def wheelEvent(self, event):
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        self.scale(factor, factor)
        event.accept()


class BoardViewerTab(QWidget):
    """Pan/zoom layer viewer generated from the current R10 KiCad board."""
    def __init__(self, window):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        note = QLabel('R10 native PCB preview · DESIGN · FABRICATION HOLD · read-only')
        note.setObjectName('simBanner')
        outer.addWidget(note)
        try:
            record = board_view.load(window.root)
        except (OSError, ValueError, KeyError) as exc:
            outer.addWidget(QLabel('Board preview unavailable: %s' % exc))
            self.view = None
            return
        if not record['current']:
            stale = QLabel('PREVIEW STALE: native PCB changed. Regenerate with python workbench/export_board_view.py')
            stale.setObjectName('simBanner')
            outer.addWidget(stale)
        self.scene = QGraphicsScene(self)
        self.view = BoardCanvas(self.scene)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.view.setBackgroundBrush(QColor('#17191c'))
        self.items = {}
        self.checks = {}
        tools = QHBoxLayout()
        for caption, layers in (
                ('Front', ('F.Cu', 'F.SilkS', 'Edge.Cuts')),
                ('Back', ('B.Cu', 'Edge.Cuts')),
                ('All copper', ('F.Cu', 'In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu', 'B.Cu', 'Edge.Cuts')),
                ('Outline', ('Edge.Cuts',))):
            button = QPushButton(caption)
            button.clicked.connect(lambda _=False, selected=layers: self.set_layers(selected))
            tools.addWidget(button)
        fit = QPushButton('Fit')
        fit.clicked.connect(self.fit)
        tools.addWidget(fit)
        tools.addStretch(1)
        outer.addLayout(tools)
        choices = QHBoxLayout()
        for layer in record['layers']:
            pixmap = QPixmap(str(record['images'][layer]))
            item = self.scene.addPixmap(pixmap)
            item.setZValue(len(self.items))
            self.items[layer] = item
            toggle = QCheckBox(layer)
            toggle.toggled.connect(lambda shown, name=layer: self.items[name].setVisible(shown))
            self.checks[layer] = toggle
            choices.addWidget(toggle)
        choices.addStretch(1)
        outer.addLayout(choices)
        outer.addWidget(self.view, 1)
        caption = QLabel('Source: %s · SHA-256 %s · drag to pan, wheel to zoom' % (
            record['source'], record['sha256'][:12]))
        caption.setObjectName('subheading')
        outer.addWidget(caption)
        self.set_layers(('F.Cu', 'F.SilkS', 'Edge.Cuts'))
        QTimer.singleShot(0, self.fit)

    def set_layers(self, selected):
        for name, toggle in self.checks.items():
            toggle.setChecked(name in selected)

    def fit(self):
        if self.view is not None:
            self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def title(self):
        return 'R10 Board Layers'

    def info(self):
        return 'Native KiCad PCB preview · DESIGN / FABRICATION HOLD · read-only'


# --------------------------------------------------------------------------- start page and preview

class StartPage(WorkshopHome):
    def __init__(self, window):
        super().__init__(window)


class NorDropTree(QTreeWidget):
    """Partition rows accept one local file as a host-only staging suggestion."""
    file_dropped = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if len(urls) == 1 and urls[0].isLocalFile():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        item = self.itemAt(event.position().toPoint())
        if len(urls) == 1 and urls[0].isLocalFile() and item is not None:
            self.file_dropped.emit(item.data(0, Qt.UserRole), urls[0].toLocalFile())
            event.acceptProposedAction()
        else:
            event.ignore()


class NorPartitionMap(QWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.setObjectName('norPartitionMap')
        self.setMinimumHeight(22)
        self.setMaximumHeight(22)

    def paintEvent(self, event):
        colors = ('#af4b45','#cb7150','#477a9e','#5395c1','#467957','#5e946b',
                  '#9774be','#8370a5','#6e768a','#8b8b9c','#595e66')
        painter = QPainter(self)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor('#242830'))
        x = 0
        for part, color in zip(self.model.partitions, colors):
            end = round(part.end / nor_staging.EXPECTED_SIZE * w)
            painter.fillRect(x, 0, max(1, end - x - 2), h, QColor(color))
            x = end


class NorFlashTab(QWidget):
    """Virtual NOR staging on the PC. Deliberately contains no physical flash action."""
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.model = nor_staging.NorStage(window.root)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 9, 10, 9)
        lay.setSpacing(7)
        header = QHBoxLayout()
        symbol = QLabel()
        symbol.setPixmap(window.nav_icon('nor').pixmap(QSize(56, 56)))
        symbol.setToolTip('Symbolic NOR IC drawing — not verified package geometry')
        header.addWidget(symbol)
        titles = QVBoxLayout()
        from .ux_polish import overline
        title = overline('NOR Flash', 'memory device and staging workspace')
        title.setStyleSheet('font-weight: bold; font-size: 15px;')
        titles.addWidget(title)
        titles.addWidget(QLabel('R10 host proposal · source-backed partitions · package geometry not shown'))
        header.addLayout(titles, 1)
        lay.addLayout(header)
        warning = QLabel('HOST / DESIGN ONLY  ·  No board connected  ·  Drop only stages a PC-side image reference; '
                         'protected factory slots are locked. Physical programming is not available.')
        warning.setObjectName('simBanner')
        warning.setWordWrap(True)
        lay.addWidget(warning)
        self.summary = QLabel()
        lay.addWidget(self.summary)
        self.map = NorPartitionMap(self.model)
        lay.addWidget(self.map)
        self.parts = NorDropTree()
        self.parts.setObjectName('norPartitions')
        self.parts.setHeaderLabels(['ID', 'R10 region', 'Capacity', 'Access', 'Staged image'])
        for column in (0, 2, 3):self.parts.header().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.parts.setRootIsDecorated(False)
        self.parts.setAlternatingRowColors(True)
        self.parts.setSelectionMode(QAbstractItemView.SingleSelection)
        self.parts.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.parts.header().setSectionResizeMode(4, QHeaderView.Stretch)
        self.parts.setColumnWidth(0, 74)
        self.parts.setColumnWidth(2, 82)
        self.parts.setColumnWidth(3, 92)
        self.parts.file_dropped.connect(self._stage)
        lay.addWidget(self.parts, 2)
        controls = QHBoxLayout()
        self.stage_button = QPushButton('Stage Image…')
        self.stage_button.setObjectName('stageImageButton')
        self.stage_button.clicked.connect(self._choose)
        self.remove_button = QPushButton('Remove Staged')
        self.remove_button.clicked.connect(self._remove)
        self.review_button = QPushButton('Review Stage')
        self.review_button.clicked.connect(self._review)
        self.export_button = QPushButton('Export JSON Plan…')
        self.export_button.clicked.connect(self._export)
        self.source_button = QPushButton('Source CSV')
        self.source_button.clicked.connect(lambda: window.open_document(window.root / nor_staging.RELATIVE_MAP))
        for button in (self.stage_button, self.remove_button, self.review_button,
                       self.export_button, self.source_button):
            controls.addWidget(button)
        lay.addLayout(controls)
        self.review_text = QPlainTextEdit()
        self.review_text.setObjectName('norReview')
        self.review_text.setReadOnly(True)
        self.review_text.setFont(mono_font(9))
        self.review_text.setMaximumHeight(155)
        lay.addWidget(self.review_text, 1)
        self._refresh()

    def title(self):
        return 'NOR Flash'

    def info(self):
        return 'R10 source-defined 64 MiB NOR proposal · PC-only staging · no physical programming'

    def _refresh(self):
        old = self.parts.currentItem()
        selected = old.data(0, Qt.UserRole) if old else None
        self.parts.clear()
        for part in self.model.partitions:
            entry = self.model.staged.get(part.id)
            status = ('STAGEABLE' if part.stageable else 'LOCKED')
            row = QTreeWidgetItem([part.id, part.name, '%g MiB' % (part.size / 1048576),
                                   status, entry['file_name'] if entry else '—'])
            row.setData(0, Qt.UserRole, part.id)
            row.setToolTip(1, part.contents + '\n' + part.status)
            if not part.stageable:
                row.setForeground(3, QBrush(QColor('#eb8d70')))
            if entry:
                row.setToolTip(4, entry['sha256'])
            self.parts.addTopLevelItem(row)
            if part.id == selected:
                self.parts.setCurrentItem(row)
        if self.parts.currentItem() is None and self.parts.topLevelItemCount():
            self.parts.setCurrentItem(self.parts.topLevelItem(2))
        total = sum(item['size_bytes'] for item in self.model.staged.values())
        self.summary.setText('%d staged image(s) · %.2f MiB of image files · map status: PROPOSED · physical write: DISABLED' %
                             (len(self.model.staged), total / 1048576))

    def _selected(self):
        item = self.parts.currentItem()
        return item.data(0, Qt.UserRole) if item else None

    def _choose(self):
        ident = self._selected()
        if ident is None:
            return
        filename, _ = QFileDialog.getOpenFileName(self, 'Choose image to stage (no flash write)',
                                                   str(self.window_.root), 'Images (*.bin *.bit *.img *.pak);;All Files (*)')
        if filename:
            self._stage(ident, filename)

    def _stage(self, ident, path):
        try:
            record = self.model.stage(ident, path)
        except (nor_staging.StageError, OSError) as exc:
            QMessageBox.warning(self, 'Stage declined', str(exc))
            return
        self._refresh()
        self.review_text.setPlainText('STAGED ON HOST ONLY  ·  No physical write performed.\n'
                                      '%s  %s\nSHA-256  %s\n%s' %
                                      (ident, record['file_name'], record['sha256'],
                                       'LINK TEST ONLY — NOT BOOTABLE' if record['link_test_only']
                                       else 'Bootability not established'))

    def _remove(self):
        if self._selected():
            self.model.remove(self._selected())
            self._refresh()
            self.review_text.setPlainText('Removed staged reference; source file unchanged.')

    def _review(self):
        import json
        try:
            result = self.model.review()
        except (nor_staging.StageError, OSError) as exc:
            QMessageBox.warning(self, 'Stage validation failed', str(exc))
            return
        self.review_text.setPlainText(json.dumps(result, indent=2, sort_keys=True))

    def _export(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Save HOST-ONLY plan',
                     str(self.window_.root / 'nor-host-staging.json'), 'JSON (*.json)')
        if not filename:
            return
        try:
            self.model.export(filename)
        except (nor_staging.StageError, OSError) as exc:
            QMessageBox.warning(self, 'Export failed', str(exc))
            return
        self.window_.statusBar().showMessage('Host-only stage plan exported · no device programming', 5000)


class ReadinessTab(QWidget):
    """R10 first-boot evidence requirements, never a guessed percentage."""
    def __init__(self, window):
        super().__init__()
        self.window_ = window
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        header = QLabel('First-boot engineering readiness · evidence required')
        header.setStyleSheet('font-weight: bold; font-size: 15px;')
        layout.addWidget(header)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setObjectName('simBanner')
        layout.addWidget(self.message)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Checkpoint', 'Status', 'Evidence / location'])
        self.tree.setRootIsDecorated(True)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tree.itemDoubleClicked.connect(self._open_source)
        layout.addWidget(self.tree, 1)
        refresh = QPushButton('Refresh evidence checklist')
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)
        self.refresh()

    def title(self):
        return 'Console Readiness'

    def info(self):
        return 'Reviewed evidence records · fabrication HOLD · 95% first-try success goal; probability unknown'

    def refresh(self):
        data = readiness.snapshot(self.window_.root)
        self.window_._refresh_readiness()
        self.message.setText('GOAL: ≥95%% first-try out-of-box success · measured probability UNKNOWN.\n'
                             '%d / %d reviewed evidence records valid · FABRICATION HOLD.\n'
                             'Records require independent review, matching source/artifact hashes and the right evidence class. '
                             'This checks records; it does not authenticate reviewers or measure hardware.\n' %
                             (data['verified_gates'],data['required_gates']) + '\n'.join(data['registry_issues']))
        self.tree.clear()
        source = QTreeWidgetItem(['Design inputs (presence only)', '', 'Double-click a source to open in Workbench'])
        self.tree.addTopLevelItem(source)
        for item in data['design_inputs']:
            row = QTreeWidgetItem([item['label'], item['status'], item['file']])
            row.setData(0, Qt.UserRole, item['file'] if item['status'] == 'DOCUMENTED' else '')
            source.addChild(row)
        gates = QTreeWidgetItem(['Verification required before first boot', '',
                                 'An R10 schematic, source file or host simulation alone cannot pass these checks'])
        self.tree.addTopLevelItem(gates)
        for item in data['gates']:
            row=QTreeWidgetItem([item['label'],item['status'],item.get('evidence_path',item['evidence_required'])])
            row.setData(0,Qt.UserRole,item.get('evidence_path',''));gates.addChild(row)
        source.setExpanded(True)
        gates.setExpanded(True)

    def _open_source(self, item, _column=0):
        path = item.data(0, Qt.UserRole)
        if path:
            self.window_.open_document(self.window_.root / path)


class ToolInventoryTab(QWidget):
    """Host PATH discovery; explicitly not a version or capability test."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        title = QLabel('Installed engineering tools · Windows host inspection')
        title.setStyleSheet('font-weight: bold; font-size: 15px;')
        layout.addWidget(title)
        notice = QLabel('Read-only PATH discovery; tool presence is NOT equivalent to '
                        'a qualified build, configured target, or a tested physical board.')
        notice.setObjectName('simBanner')
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Executable', 'Purpose', 'Discovery', 'Location'])
        self.tree.setRootIsDecorated(False)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.tree, 1)
        refresh = QPushButton('Rescan installed tool paths')
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)
        self.refresh()

    def title(self):
        return 'Tool Inventory'

    def info(self):
        return 'PATH discovery only · no external program started and no toolchain qualified'

    def refresh(self):
        self.tree.clear()
        for item in tool_inventory.inspect()['tools']:
            row = QTreeWidgetItem([item['id'], item['label'], item['status'],
                                   item['executable'] or 'Not found on PATH'])
            if item['status'] == 'NOT_AVAILABLE':
                row.setForeground(2, QBrush(QColor('#eb8d70')))
            self.tree.addTopLevelItem(row)


class PreviewTab(QWidget):
    """Frames from the host simulator. Not ARC-1 hardware output."""
    frame_requested = Signal(int)
    def __init__(self, window, project, frames):
        super().__init__()
        self.project = project
        self.frames = frames
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        banner = QLabel('HOST SIMULATION of %s on this PC · not ARC-1 hardware output' % Path(project).name)
        banner.setObjectName('simBanner')
        lay.addWidget(banner)
        self.scenario_note = QLabel('Source: host game framebuffer · recorded frames, not live hardware')
        self.scenario_note.setWordWrap(True)
        self.scenario_note.setStyleSheet('color: #9da8b2; font-size: 11px;')
        lay.addWidget(self.scenario_note)
        self.image = QLabel()
        self.image.setObjectName('framePreview')
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setMinimumSize(320, 180)
        self.image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self.image, 1)
        row = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, max(0, len(frames) - 1))
        self.slider.valueChanged.connect(self._frame_asked)
        self.caption = QLabel()
        row.addWidget(QLabel('Frame'))
        row.addWidget(self.slider, 1)
        row.addWidget(self.caption)
        lay.addLayout(row)
        self.show_frame(0)

    def set_scenario_divergent(self, changed):
        # Scenario injection changes the behavioral model, not the independently
        # rendered host game. Do not pretend that the images predict that fault.
        self.scenario_note.setText(
            'SCENARIO INJECTION · This host-game image is from the baseline run, '
            'not a rendering of the altered system behavior.' if changed else
            'Source: host game framebuffer · recorded frames, not live hardware')
        self.scenario_note.setStyleSheet('color: #e09b68; font-size: 11px;' if changed
                                         else 'color: #9da8b2; font-size: 11px;')

    def _frame_asked(self, index):
        self.show_frame(index)
        if 0 <= index < len(self.frames):
            self.frame_requested.emit(self.frames[index][0])

    def set_sim_frame(self, frame_number):
        """Pick the latest generated frame <= trace frame, without seeking twice."""
        if not self.frames:
            return
        at = 0
        for i, (frame, _) in enumerate(self.frames):
            if frame > frame_number:
                break
            at = i
        if self.slider.value() != at:
            self.slider.blockSignals(True)
            self.slider.setValue(at)
            self.slider.blockSignals(False)
            self.show_frame(at)

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


class SimulationTracePlot(QWidget):
    """Plot widget for frame/input records written by the host simulator."""
    def __init__(self):
        super().__init__()
        self.samples = []
        self.setMinimumHeight(210)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        box = self.rect().adjusted(28, 12, -10, -24)
        p.fillRect(self.rect(), QColor('#151a20'))
        p.setPen(QPen(QColor('#39424c'), 1))
        for i in range(5):
            y = box.top() + i * box.height() / 4
            p.drawLine(box.left(), int(y), box.right(), int(y))
        p.setPen(QPen(QColor('#f28c28'), 2))
        if self.samples:
            max_mask = max(1, max(v[1] for v in self.samples))
            count = min(240, len(self.samples))
            selected = self.samples[-count:]
            path = QPainterPath()
            for i, (frame, held, _hash) in enumerate(selected):
                x = box.left() + (box.width() * i / max(1, count - 1))
                y = box.bottom() - (box.height() * held / max_mask)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            p.drawPath(path)
            p.setPen(QColor('#b8c0c8'))
            p.drawText(box.left(), box.bottom() + 17, 'frame %d' % selected[0][0])
            p.drawText(box.right() - 62, box.bottom() + 17, '%d' % selected[-1][0])
        else:
            p.setPen(QColor('#8b949e'))
            p.drawText(box, Qt.AlignCenter, 'No simulation trace yet')
        p.end()


class SimulationTracePanel(QWidget):
    """Persistent, user-started host-trace playback controller and detail view."""
    frame_changed = Signal(object)
    playback_changed = Signal(str)
    CHANNELS = (
        ('F133 boot/runtime', lambda r: 0 if r['f133']['runtime'] == 'power_off' else 1 if r['f133']['runtime'] == 'recovery' else 2),
        ('D213 mailbox', lambda r: r['d213']['commands']),
        ('FPGA45 workload', lambda r: r['fpga45']['busy_percent']),
        ('FPGA12 link', lambda r: 2 if r['fpga12']['link'] == 'ready' else 1 if r['fpga12']['link'] == 'training' else 0),
        ('NOR reads', lambda r: r['nor']['reads']),
        ('Controller input', lambda r: r['controller']['held_mask']),
        ('USB cartridge port', lambda r: 1 if r['usb']['cartridge_port'] == 'attached' else 0),
        ('Memory ownership', lambda r: 0 if r['memory']['ownership'] == 'none' else 3),
        ('Cartridge events', lambda r: r['cartridge']['generation']),
    )

    def __init__(self):
        super().__init__()
        self.samples = []
        self.rows = []
        self.cursor = 0
        self.project = None
        self.trace_path = None
        self.trace_sha256 = None
        self.runner = None
        self.timer = QTimer(self)
        self.timer.setInterval(33)  # playback rate only, NOT hardware timing
        self.timer.timeout.connect(self.step)
        self.scenario_divergent = False
        self.heading = QLabel('Run a game with F5 to populate simulated signals.')
        self.heading.setWordWrap(True)
        self.plot = SimulationTracePlot()
        self.channel = QComboBox()
        self.channel.addItems([name for name, _ in self.CHANNELS])
        self.channel.currentIndexChanged.connect(self.refresh_frame)
        self.state = QPlainTextEdit()
        self.state.setReadOnly(True)
        self.state.setMaximumHeight(140)
        self.input_choice = QComboBox()
        self.input_choice.addItems(['Replay input', 'Neutral', 'Left', 'Right', 'Flap'])
        self.fault_choice = QComboBox()
        self.fault_choice.addItems(['No fault', 'NOR read fault', 'FPGA12 config failure',
                                    'FPGA45 config failure', 'Power loss', 'USB cartridge detach'])
        self.run_button = QPushButton('Start')
        self.run_button.clicked.connect(self.start)
        self.pause_button = QPushButton('Pause')
        self.pause_button.clicked.connect(self.pause)
        self.reset_button = QPushButton('Reset')
        self.reset_button.clicked.connect(self.reset)
        self.step_button = QPushButton('Step')
        self.step_button.clicked.connect(self.step)
        self.apply_button = QPushButton('Apply scenario')
        self.apply_button.clicked.connect(self.apply_scenario)
        self.rate_choice = QComboBox()
        self.rate_choice.setToolTip('Host-trace replay speed, not simulated CPU clock speed')
        self.rate_choice.addItem('10 fps replay', 100)
        self.rate_choice.addItem('30 fps replay', 33)
        self.rate_choice.addItem('60 fps replay', 17)
        self.rate_choice.setCurrentIndex(1)
        self.rate_choice.currentIndexChanged.connect(self._set_replay_rate)
        self.reload_button = QPushButton('Reload cartridge')
        self.reload_button.clicked.connect(lambda: self.apply_scenario(reload=True))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(9, 9, 9, 9)
        lay.addWidget(QLabel('HOST BEHAVIORAL SIM · no board attached'))
        lay.addWidget(self.heading)
        controls = QHBoxLayout()
        for button in (self.run_button, self.pause_button, self.reset_button, self.step_button):
            controls.addWidget(button)
        lay.addLayout(controls)
        lay.addWidget(self.rate_choice)
        lay.addWidget(self.channel)
        lay.addWidget(self.plot, 1)
        lay.addWidget(self.state)
        lay.addWidget(self.input_choice)
        lay.addWidget(self.fault_choice)
        lay.addWidget(self.apply_button)
        lay.addWidget(self.reload_button)

    def _set_replay_rate(self):
        self.timer.setInterval(self.rate_choice.currentData())

    def set_runner(self, runner):
        self.runner = runner

    def playback_state(self):
        if not self.rows:
            return 'Idle'
        if self.timer.isActive():
            return 'Running'
        if self.cursor >= len(self.rows) - 1:
            return 'Completed'
        return 'Loaded' if self.cursor == 0 else 'Paused'

    def start(self):
        if self.rows and self.cursor < len(self.rows) - 1:
            self.timer.start()
            self.playback_changed.emit(self.playback_state())

    def pause(self):
        self.timer.stop()
        self.playback_changed.emit(self.playback_state())

    def reset(self):
        self.pause()
        self.cursor = 0
        self.refresh_frame()
        self.playback_changed.emit(self.playback_state())

    def step(self):
        if not self.rows:
            self.pause()
            return
        if self.sender() is not self.timer:
            self.pause()  # manual Step is a single deterministic frame
        self.cursor = min(self.cursor + 1, len(self.rows) - 1)
        self.refresh_frame()
        if self.cursor == len(self.rows) - 1:
            self.pause()

    def seek_frame_number(self, frame):
        """Align sparse preview image selection with an actual trace frame."""
        if not self.rows:
            return
        self.pause()
        self.cursor = min(range(len(self.rows)), key=lambda i: abs(self.rows[i]['frame'] - frame))
        self.refresh_frame()
        self.playback_changed.emit(self.playback_state())

    def apply_scenario(self, reload=False):
        if not self.runner or not self.project or not self.rows:
            return
        at = min(self.cursor + 1, len(self.rows) - 1)
        scenario = {}
        masks = [None, 0, 1, 4, 2]
        mask = masks[self.input_choice.currentIndex()]
        if mask is not None:
            scenario['controller_mask'] = mask
        fault = self.fault_choice.currentIndex()
        if fault == 1:
            scenario['nor_fault_frame'] = at
        elif fault in (2, 3):
            scenario['fpga_fail'] = '12' if fault == 2 else '45'
        elif fault == 4:
            scenario['power_loss_frame'] = at
        elif fault == 5:
            scenario['usb_detach_frame'] = at
        if reload:
            scenario['cartridge_reload_frame'] = at
        self.runner(self.project, len(self.rows), scenario)

    def refresh_frame(self):
        if not self.rows:
            return
        row = self.rows[self.cursor]
        self.frame_changed.emit(row)
        name, value = self.CHANNELS[self.channel.currentIndex()]
        self.plot.samples = [(r['frame'], value(r), r['event']) for r in self.rows[:self.cursor + 1]]
        self.plot.update()
        self.heading.setText('%s · frame %s/%s · %s' % (
            Path(self.project).name, self.cursor + 1, len(self.rows), row['event']))
        self.state.setPlainText(
            'F133: %s · NOR reads %s\nD213: %s · %s commands\nFPGA45: %s · %s%% busy\n'
            'FPGA12: %s\nNOR: %s · owner %s\nController: 0x%02x\n'
            'USB: %s\nMemory: %s\nCartridge: %s · generation %s\nEvidence: %s' % (
                row['f133']['runtime'], row['nor']['reads'], row['d213']['mailbox'], row['d213']['commands'],
                row['fpga45']['state'], row['fpga45']['busy_percent'], row['fpga12']['link'],
                'fault' if row['nor']['fault'] else row['nor']['partition'], row['nor']['owner'],
                row['controller']['held_mask'], row['usb']['cartridge_port'], row['memory']['ownership'], row['cartridge']['state'],
                row['cartridge']['generation'], row['evidence']))

    def set_trace(self, path, project):
        self.pause()
        self.rows = []
        self.trace_path = None
        self.trace_sha256 = None
        self.frame_changed.emit(None)
        self.playback_changed.emit(self.playback_state())
        samples = []
        try:
            for line in Path(path).read_text(encoding='utf-8').splitlines():
                frame, held, checksum = line.split()
                samples.append((int(frame), int(held, 16), checksum))
        except (OSError, ValueError):
            samples = []
        self.samples = samples
        if samples:
            self.heading.setText('%s · %d frames · last frame %d · framebuffer %s' %
                                 (Path(project).name, len(samples), samples[-1][0], samples[-1][2]))
        else:
            self.heading.setText('No valid frame trace is available for this run.')
        self.plot.samples = samples
        self.plot.update()

    def set_system_trace(self, path, project):
        """Load all model channels and show them one frame at a time."""
        rows = []
        try:
            import json
            raw = Path(path).read_bytes()
            for line in raw.decode('utf-8').splitlines():
                row = json.loads(line)
                if not isinstance(row, dict) or row.get('evidence') != 'HOST_SIM_BEHAVIORAL':
                    raise ValueError('Unsupported system trace evidence')
                for key, fields in {
                    'f133': ('runtime',), 'd213': ('mailbox', 'commands'),
                    'fpga45': ('state', 'busy_percent'), 'fpga12': ('link',),
                    'nor': ('reads', 'fault', 'partition', 'owner'),
                    'controller': ('held_mask',), 'usb': ('cartridge_port',),
                    'memory': ('ownership',), 'cartridge': ('state', 'generation'),
                }.items():
                    if not isinstance(row.get(key), dict) or any(field not in row[key] for field in fields):
                        raise ValueError('Incomplete system trace row')
                if not isinstance(row.get('frame'), int) or not isinstance(row.get('event'), str):
                    raise ValueError('Incomplete system trace frame')
                for _, channel in self.CHANNELS:
                    channel(row)
                rows.append(row)
        except (OSError, UnicodeError, ValueError, TypeError, KeyError):
            rows = []
        self.pause()
        self.rows = rows
        self.trace_path = str(Path(path)) if rows else None
        self.trace_sha256 = sha256(raw).hexdigest() if rows else None
        self.project = project
        self.cursor = 0
        if rows:
            self.refresh_frame()
        else:
            self.frame_changed.emit(None)
            self.heading.setText('No valid system trace is available.')
        self.playback_changed.emit(self.playback_state())


class DashboardPanel(QWidget):
    """Compact source-labeled meters above the existing simulator controls."""
    def __init__(self):
        super().__init__()
        self.heading = QLabel('DIAGNOSTICS · UNKNOWN')
        self.component_context = QLabel('SELECTED HARDWARE · ARC-1 CONSOLE')
        self.component_context.setObjectName('sectionTitle')
        self.provenance = QLabel('No system trace loaded')
        self.provenance.setWordWrap(True)
        self.meters = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 8, 9, 4)
        layout.setSpacing(3)
        layout.addWidget(self.component_context)
        layout.addWidget(self.heading)
        layout.addWidget(self.provenance)
        for key, label in dashboard.METERS:
            card = QWidget()
            column = QVBoxLayout(card)
            column.setContentsMargins(0, 2, 0, 3)
            column.setSpacing(1)
            title = QLabel(label)
            value = QLabel('UNKNOWN · no valid trace')
            value.setWordWrap(True)
            bar = QProgressBar()
            bar.setObjectName('dashboard_' + key)
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setFixedHeight(5)
            bar.hide()  # A blank bar would look like a measured 0%.
            column.addWidget(title)
            column.addWidget(value)
            column.addWidget(bar)
            layout.addWidget(card)
            self.meters[key] = (value, bar)
        self.set_snapshot(dashboard.unknown())

    def set_hardware_context(self, title):
        self.component_context.setText('SELECTED HARDWARE · ' + title.upper())
        self.component_context.setToolTip('Context only. Metrics below are source-labelled simulation data, not live device telemetry.')

    def set_snapshot(self, data):
        evidence = data['evidence']
        self.heading.setText('DIAGNOSTICS · ' + evidence)
        if data['source']:
            digest = data['source_sha256']
            self.provenance.setText('Frame %s · %s · SHA-256 %s…' % (
                data['frame'], Path(data['source']).name, digest[:12]))
            self.provenance.setToolTip('%s\nSHA-256 %s' % (data['source'], digest))
        else:
            self.provenance.setText('No valid system trace loaded')
            self.provenance.setToolTip('')
        for metric in data['meters']:
            value, bar = self.meters[metric['id']]
            value.setText(metric['value'])
            value.setToolTip(metric['detail'])
            percent = metric['percent']
            bar.setVisible(percent is not None)
            if percent is not None:
                bar.setValue(percent)
                bar.setToolTip(metric['detail'])


class QuickOpen(QDialog):
    """Ctrl+P: type part of a file name, press Enter."""
    def __init__(self, window):
        super().__init__(window)
        self.setWindowTitle('Find a file')
        self.resize(560, 420)
        self.files = engine.walk_files(window.root)
        lay = QVBoxLayout(self)
        self.edit = QLineEdit()
        writing_prompt(self.edit, 'Type part of a file name, e.g. main.c')
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


# --------------------------------------------------------------------------- resource budgets (Inspector)

CHIP_COLOURS = {'f133': '#ff7a3c', 'fpga12': '#d0a882', 'd213': '#8fb3c2', 'gpu45': '#b4a3d6', 'present': '#9cc29e',
                'link': '#a9aeb4', 'need': '#ff5a1a'}
EVIDENCE_TEXT = {'NONE': 'not measured', 'DESIGN': 'design figure', 'RTL_SIM': 'RTL simulation',
                 'HOST_SIM': 'host simulation', 'FPGA_PNR': 'FPGA place & route', 'BOARD_TEST': 'measured on a board',
                 'STATIC_CHECK': 'static check'}


class ClipAssistant(QWidget):
    """Slate's desktop companion: a small portrait in the window's bottom-right corner.

    Independent of the Inspector. Drag to move (remembered), double-click or use the
    context menu to collapse. His badge reflects actual job and provider states read
    from the existing job poller. Brief local cutout reactions add personality;
    nothing here simulates progress or runs anything.
    """
    clicked = Signal()
    GRID = (60, 70)
    FULL = (140, 140)
    SMALL = (48, 56)
    MARGIN = 14
    RECENT_SECONDS = 20

    retired = False  # the companion overlay is retained: shown in workspaces, hidden at Home; its position and collapse fields are live workspace state (INTEGRATION-01 audit)

    def setVisible(self, visible):
        super().setVisible(bool(visible) and not self.retired)

    def __init__(self, parent=None, size=(140, 140)):
        super().__init__(parent)
        self.setObjectName('ClipAssistant')
        self.FULL = tuple(size)
        self.setCursor(Qt.OpenHandCursor)
        self.setAccessibleName('Graphite companion')
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        self._portrait = QPixmap()  # Retired portraits are historical assets only.
        self.hover = False
        self._press_global = None
        self._press_position = None
        self._dragging = False
        self.queued = False
        self.state = 'idle'
        self.phase = 0.0
        self._arcfairy_visual_tick = time.monotonic()
        self._seen_finish = {}
        layout = parent.session.state.get('layout', {})
        self.collapsed = bool(layout.get('clip_collapsed', False))
        self.setFixedSize(*(self.SMALL if self.collapsed else self.FULL))
        self.ticker = QTimer(self)
        self.ticker.setInterval(800)  # Actual job-state polling, not an animation timer.
        self.ticker.timeout.connect(self._tick)
        self.ticker.start()
        self.bird_pose = 'rest'
        from .bird_presence import BirdPresence
        self.presence = BirdPresence(self)
        self._describe()

    # ---- real state -------------------------------------------------------------
    def reduce_motion(self):
        from .reading_profile import DEFAULT
        return bool((self.parentWidget().session.state.get('reading_profile') or {}).get('reduce_motion', DEFAULT['reduce_motion']))

    def read_state(self):
        dock = getattr(self.parentWidget(), 'clip_dock', None)
        active = getattr(dock, 'active_job', None)
        if active:
            state = active.get('state', '')
            if state.startswith('Waiting for'):return 'approval', active
            if state in ('Paused', 'Interrupted'):return 'paused', active
            return 'working', active
        if getattr(dock, 'busy', False):return 'working', None
        latest = getattr(dock, 'latest_job', None)
        if latest and latest.get('state') in ('Completed', 'Failed'):
            finished = latest.get('finished') or 0
            if finished and time.time() - finished <= self.RECENT_SECONDS:
                return ('done' if latest['state'] == 'Completed' else 'failed'), latest
        return 'idle', None

    def _describe(self, job=None):
        words = {'idle': 'ready', 'working': 'working on ' + (job['tool'] if job else 'a provider reply'),
                 'approval': (job or {}).get('tool', 'a job') + ' is waiting for your approval',
                 'paused': (job or {}).get('tool', 'a job') + ' is ' + (job or {}).get('state', 'paused').lower(),
                 'done': (job or {}).get('tool', 'a job') + ' completed', 'failed': (job or {}).get('tool', 'a job') + ' failed'}
        text = 'Graphite · ' + words[self.state]
        self.setToolTip(text + '\nClick to talk · drag to move · double-click to ' + ('expand' if self.collapsed else 'collapse') + ' · right-click for options')
        self.setAccessibleDescription(text)

    def _tick(self):
        if not self.isVisible():return
        state,job=self.read_state()
        if state!=self.state:
            self.state=state;self._describe(job);self.update()
        self.presence.observe(state,job)

    def hideEvent(self, event):
        if hasattr(self, 'presence'):self.presence.dismiss()
        super().hideEvent(event)

    # ---- placement ----------------------------------------------------------------
    def follow(self, slot=None):
        """Anchor to the window's bottom-right corner; a dragged position is remembered."""
        self.parentWidget().installEventFilter(self)
        QTimer.singleShot(0, self._place)

    def arrive(self):
        """Show in workspaces; Home presents Slate in its artwork instead."""
        if getattr(self.parentWidget(), '_home_active', False):
            self.hide();return
        self._queue()

    def eventFilter(self, obj, event):
        if obj is self.parentWidget() and event.type() in (QEvent.Resize, QEvent.LayoutRequest, QEvent.ChildAdded):
            self._queue()
        return super().eventFilter(obj, event)

    def _queue(self):
        if not self.queued:
            self.queued = True
            QTimer.singleShot(0, self._place)

    def _move_inside(self, point):
        window = self.parentWidget()
        bottom = window.height() - (window.statusBar().height() if window.statusBar().isVisible() else 0)
        self.move(max(0, min(point.x(), window.width() - self.width())),
                  max(0, min(point.y(), bottom - self.height())))
        self.raise_()

    def _place(self):
        self.queued = False
        if self._dragging:return
        window = self.parentWidget()
        if getattr(window, '_home_active', False):
            self.hide();return
        position = window.session.state.get('layout', {}).get('clip_position')
        if position is not None:
            self._move_inside(QPoint(int(position[0] * max(0, window.width() - self.width())),
                                     int(position[1] * max(0, window.height() - self.height()))))
        else:
            bottom = window.height() - (window.statusBar().height() if window.statusBar().isVisible() else 0)
            self._move_inside(QPoint(window.width() - self.width() - self.MARGIN, bottom - self.height() - self.MARGIN))
        self.show();self.raise_()
        self._reserve(position is None)
        self.presence.position()

    def _reserve(self, resting):
        space = getattr(getattr(self.parentWidget(), 'arc_inspector', None), 'companion_space', None)
        if space is not None:
            space.setFixedHeight(self.height() - 30 if resting and not self.collapsed and not self.retired else 0)

    def set_collapsed(self, collapsed):
        self.presence.dismiss()
        self.collapsed = bool(collapsed)
        self.setFixedSize(*(self.SMALL if self.collapsed else self.FULL))
        self.parentWidget().session.set_layout(clip_collapsed=self.collapsed)
        self._describe();self._queue()

    def reset_position(self):
        self.parentWidget().session.set_layout(clip_position=None);self._queue()

    # ---- interaction ----------------------------------------------------------------
    def enterEvent(self, event):
        self.hover = True;self.update()

    def leaveEvent(self, event):
        self.hover = False;self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._press_position = self.pos()
            self._dragging = False
            event.accept()

    def mouseMoveEvent(self, event):
        if self._press_global is None or not event.buttons() & Qt.LeftButton:return
        delta = event.globalPosition().toPoint() - self._press_global
        if not self._dragging and delta.manhattanLength() >= QApplication.startDragDistance():
            self._dragging = True
            self.setCursor(Qt.ClosedHandCursor)
        if self._dragging:
            self.presence.dismiss()
            self._move_inside(self._press_position + delta)
            overlay = getattr(self.parentWidget(), 'clip_overlay', None)
            if overlay is not None and overlay.isVisible():overlay.place()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or self._press_global is None:return
        self._press_global = None
        self.setCursor(Qt.OpenHandCursor)
        if self._dragging:
            window = self.parentWidget()
            width = max(1, window.width() - self.width())
            height = max(1, window.height() - self.height())
            window.session.set_layout(clip_position=[self.x() / width, self.y() / height])
            self._dragging = False
            self._reserve(False)
        else:
            self.clicked.emit()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.set_collapsed(not self.collapsed);event.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):self.clicked.emit();event.accept()
        else:super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        window = self.parentWidget();menu = QMenu(self)
        menu.addAction('Ask Graphite…', self.clicked.emit)
        menu.addAction('Graphite workshop', window.show_clip_workspace)
        menu.addAction('Jobs && evidence', window.show_engineering)
        menu.addSeparator()
        menu.addAction('Reading and layout…', window.show_reading)
        menu.addSeparator()
        menu.addAction('Expand' if self.collapsed else 'Collapse', lambda: self.set_collapsed(not self.collapsed))
        menu.addAction('Reset position', self.reset_position)
        menu.exec(event.globalPos())

    # ---- drawing ----------------------------------------------------------------------
    def paintEvent(self, event):
        from PySide6.QtGui import QPen, QBrush
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        moving = False  # Event-driven poses; no idle animation loop.
        bob = 0
        area = self.rect().adjusted(2, 2 + bob, -2, -2 + bob)
        if not self.collapsed:
            from PySide6.QtGui import QRadialGradient
            floor = QRadialGradient(QPointF(self.width() / 2, self.height() - 7), self.width() * 0.42)
            floor.setColorAt(0, QColor(0, 0, 0, 150));floor.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setPen(Qt.NoPen);painter.setBrush(floor)
            painter.drawEllipse(QRectF(self.width() * 0.08, self.height() - 14, self.width() * 0.84, 12))
        if self.collapsed:
            painter.setBrush(QColor('#171b21'));painter.setPen(QPen(QColor('#ff9a32'), 2))
            painter.drawEllipse(area)
        from .static_bird import paint as paint_bird
        facing = "left" if self.x()+self.width()/2 >= self.parentWidget().width()/2 else "right"
        paint_bird(painter,self.parentWidget().root,area,facing,self.bird_pose)
        size = 18 if not self.collapsed else 14
        badge = QRect(self.width() - size - 2, self.height() - size - 2, size, size)
        if self.state == 'working':
            pen = QPen(QColor('#ff9a32'), 3);pen.setCapStyle(Qt.RoundCap);painter.setPen(pen);painter.setBrush(Qt.NoBrush)
            start = int(-(self.phase * 360 * 16 / 3.0)) % (360 * 16) if moving else 90 * 16
            painter.drawArc(badge.adjusted(1, 1, -1, -1), start, 270 * 16)
        elif self.state in ('approval', 'paused', 'done', 'failed'):
            color = {'approval': '#ffcc4d', 'paused': '#8a93a0', 'done': '#4caf72', 'failed': '#e5534b'}[self.state]
            glyph = {'approval': '!', 'paused': 'II', 'done': '✓', 'failed': '✕'}[self.state]
            fill = QColor(color)
            if self.state == 'approval' and moving:fill.setAlpha(150 + int(105 * (0.5 + 0.5 * math.sin(self.phase * 2.5))))
            painter.setPen(Qt.NoPen);painter.setBrush(QBrush(fill));painter.drawEllipse(badge)
            painter.setPen(QColor('#0e1116'));font = painter.font();font.setBold(True);font.setPixelSize(size - 6);painter.setFont(font)
            painter.drawText(badge, Qt.AlignCenter, glyph)
        if self.hover and not self._dragging:
            painter.setPen(QPen(QColor(255, 154, 50, 160), 1));painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        painter.end()



class ClipOverlay(QWidget):
    """Slate's chat as speech bubbles floating over the Workbench window, under the paperclip.

    Not a window: a transparent child of the main window whose mask covers only the bubbles
    and the message field, so the editor underneath stays clickable. Your messages are ARC-1
    orange on the right, replies brushed steel on the left. Answers come from Google Gemini
    with the owner's free key (workbench/clip.py); the key is checked with a real request
    the moment it is pasted.
    """
    replied = Signal(int, str, str)                # request epoch, text, error kind
    planned = Signal(int, object, str)
    busy_changed = Signal(bool)                    # bounded API status, not a guessed percent
    key_checked = Signal(int, bool, str, str)      # request epoch, ok, key, model or error text
    WIDTH, SHOWN = 360, 7                          # bubbles kept on screen; older ones stay in history
    ORANGE = 'qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff6a24, stop:1 #e04810)'
    STEEL = 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f1f2f4, stop:0.55 #d3d6da, stop:1 #b9bdc2)'

    def __init__(self, window, anchor, open_file=None):
        super().__init__(window)
        self.setObjectName('ClipOverlay')
        self.window_, self.anchor = window, anchor
        self.open_file = open_file or (lambda: (None, None))
        self.settings = clip.Settings.load()
        self.history = []                          # [(role, text actually sent)]
        self.busy = False
        self._request_epoch = 0
        self._requests_inflight = set()
        self._local_job=None
        self._local_conversation=uuid.uuid4().hex
        if hasattr(window,'ledger_bridge'):
            from . import local_brain
            self._local_conversation=local_brain.get(window.ledger_bridge.kernel,'desktop_conversation',self._local_conversation)
        self.expect_key = not self.settings.ready()
        self.pending = None                        # a question asked before the key was set up
        self.status_bubble = None
        self.setStyleSheet("""
            #ClipPill { background: #1d1f22; border: 1px solid #3a3e44; border-radius: 19px; }
            #ClipInput { border: none; background: transparent; color: #e4e6e8; font-size: 13px; padding: 4px 2px;
                         selection-background-color: #ff5a1a; }
            #ClipSend { background: %s; border: none; border-radius: 13px; }
            #ClipSend:disabled { background: #5a3a2c; }
            #ClipTool { border: none; background: transparent; color: #a9aeb4; font-size: 13px; padding: 0 3px; }
            #ClipTool:checked { color: #ff5a1a; }
            #ClipTool:hover { color: #ffffff; }
            #ClipNote { color: #a9aeb4; font-size: 11px; background: rgba(20, 21, 23, 0.94);
                        border: 1px solid #33373c; border-radius: 9px; padding: 3px 8px; }
            #ClipAction { background: %s; color: white; border: none; border-radius: 12px; padding: 4px 12px;
                          font-weight: 600; }
            #ClipAction:hover { background: #ff7a3c; }
        """ % (self.ORANGE, self.ORANGE))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 4, 10, 12)
        lay.setSpacing(6)
        self.rows = QVBoxLayout()
        self.rows.setSpacing(6)
        lay.addLayout(self.rows)

        self.pill = QFrame()
        self.pill.setObjectName('ClipPill')
        pl = QHBoxLayout(self.pill)
        pl.setContentsMargins(8, 3, 4, 3)
        pl.setSpacing(2)
        self.include = QToolButton(text='📎')
        self.include.setObjectName('ClipTool')
        self.include.setCheckable(True)
        self.include.setChecked(self.settings.include_file)
        self.include.setToolTip('Send the open file with your message')
        self.include.toggled.connect(self._remember_include)
        self.input = QLineEdit()
        self.input.setObjectName('ClipInput')
        pal = self.input.palette()
        pal.setColor(QPalette.PlaceholderText, QColor('#7d838a'))
        self.input.setPalette(pal)
        self.input.returnPressed.connect(self.send)
        self.input.installEventFilter(self)
        self.send_btn = QPushButton()
        self.send_btn.setObjectName('ClipSend')
        self.send_btn.setFixedSize(26, 26)
        self.send_btn.setIcon(self._arrow_icon())
        self.send_btn.setAccessibleName('Send')
        self.send_btn.clicked.connect(self.send)
        more = QToolButton(text='•••')
        more.setObjectName('ClipTool')
        more.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(more)
        menu.addAction('New conversation', self.clear)
        menu.addAction('Open local Brain',lambda:window.ledger_bridge.show_brain())
        menu.addAction('Use local chat',lambda:self.choose_provider('local'))
        menu.addAction('Use Gemini chat',lambda:self.choose_provider('gemini'))
        menu.addAction('Test my Google key', self.test_key)
        menu.addAction('Change Google key...', self.change_key)
        menu.addAction('Get a free key (opens Google AI Studio)', self.open_key_page)
        menu.addAction('Forget my key', self.forget_key)
        menu.addSeparator()
        menu.addAction('Hide Graphite  (Esc)', self.hide)
        more.setMenu(menu)
        for w in (self.include, self.input, self.send_btn, more):
            pl.addWidget(w, 1 if w is self.input else 0)
        self._shadow(self.pill)
        lay.addWidget(self.pill)

        self.replied.connect(self._on_reply)
        self.planned.connect(self._on_plan)
        self.key_checked.connect(self._on_key_checked)
        if hasattr(window,'ledger_bridge'):
            window.ledger_bridge.command_finished.connect(self._local_result)
        window.installEventFilter(self)
        self.refresh()
        self.hide()

    # ------------------------------------------------------------------ geometry
    def place(self):
        corner = self.anchor.mapTo(self.window_, QPoint(self.anchor.width(), self.anchor.height()))
        lay = self.layout()
        lay.activate()
        h = max(lay.heightForWidth(self.WIDTH) if lay.hasHeightForWidth() else 0, lay.sizeHint().height(),
                lay.minimumSize().height())
        h = min(max(h, 60), max(60, self.window_.height() - 16))
        below = corner.y() + 2
        y = below if below + h <= self.window_.height() else max(0, corner.y() - self.anchor.height() - h - 2)
        x = max(0, min(corner.x() - self.WIDTH, self.window_.width() - self.WIDTH))
        self.setGeometry(x, y, self.WIDTH, h)
        QTimer.singleShot(0, self._mask)

    def _mask(self):
        region = QRegion()
        for w in self.findChildren(QWidget):
            if w.isVisible() and w.property('clipShape'):
                r = QRect(w.mapTo(self, QPoint(0, 0)), w.size()).adjusted(-6, -4, 6, 8)    # room for the shadow
                region = region.united(QRegion(r))
        self.setMask(region if not region.isEmpty() else QRegion(0, 0, 1, 1))

    def eventFilter(self, obj, event):
        if obj is self.window_ and event.type() == QEvent.Resize and self.isVisible():
            self.place()
        elif obj is self.input and event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            self.hide()
            return True
        return super().eventFilter(obj, event)

    def toggle(self):
        if self.isVisible():
            self.hide()
            return
        self.show()
        self.raise_()
        self.place()
        self.input.setFocus()

    def pop_up(self):
        if not self.isVisible():
            self.show()
            self.raise_()
        self.place()
        QTimer.singleShot(0, self.place)           # again once the new bubble's layout has settled

    # ------------------------------------------------------------------ bubbles
    @staticmethod
    def _shadow(w):
        fx = QGraphicsDropShadowEffect(w)
        fx.setBlurRadius(14)
        fx.setOffset(0, 2)
        fx.setColor(QColor(0, 0, 0, 170))
        w.setGraphicsEffect(fx)
        w.setProperty('clipShape', True)

    @staticmethod
    def _arrow_icon():
        pm = QPixmap(32, 32)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor('white'), 3.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(16, 25, 16, 8)
        p.drawLine(9, 14, 16, 7)
        p.drawLine(23, 14, 16, 7)
        p.end()
        return QIcon(pm)

    def _add_row(self, widget, align):
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        if align == 'right':
            rl.addStretch(1)
        if align == 'center':
            rl.addWidget(widget, 0, Qt.AlignCenter)
        else:
            rl.addWidget(widget)
        if align == 'left':
            rl.addStretch(1)
        self.rows.addWidget(row)
        while self.rows.count() > self.SHOWN:      # older bubbles leave the screen, not the conversation
            old = self.rows.takeAt(0).widget()
            if old is not None:
                old.hide()                         # gone now, not at the next event-loop pass
                old.deleteLater()
        self._fade_in(widget)
        self.pop_up()
        return row

    def _fade_in(self, w):
        fx = QGraphicsOpacityEffect(w)
        w.setGraphicsEffect(fx)
        anim = QPropertyAnimation(fx, b'opacity', w)
        anim.setDuration(180)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.finished.connect(lambda: QTimer.singleShot(0, lambda: self._settle(w)))
        anim.start()
        w.setProperty('clipShape', True)

    @staticmethod
    def _fit(label, text, limit, markdown=False):
        """Sizes a word-wrapped label exactly, so the floating column never squeezes a bubble."""
        label.setText(text)
        label.ensurePolished()                     # the stylesheets decide the font; measure with it
        f = label.font()
        doc = QTextDocument()
        doc.setDefaultFont(f)
        doc.setDocumentMargin(0)
        doc.setMarkdown(text) if markdown else doc.setPlainText(text)
        width = min(limit, int(doc.idealWidth()) + (24 if label.objectName() == 'ClipNote' else 6))
        label.setFixedWidth(max(width, 24))
        doc.setTextWidth(label.width())
        label.setMinimumHeight(max(label.heightForWidth(label.width()), int(doc.size().height()) + 4))

    def _settle(self, w):
        try:
            self._shadow(w)                        # replaces the finished fade effect
            self._mask()
        except RuntimeError:                       # the bubble already scrolled away
            pass

    def bubble(self, text, mine, error=False, action=None, *, plain=False):
        box = QFrame()
        if mine:
            look = 'background: %s; border: 1px solid #ff8a4c;' % self.ORANGE, '#ffffff'
        elif error:
            look = 'background: #2a1310; border: 1px solid #ff5a1a;', '#ffc2ad'
        else:
            look = 'background: %s; border: 1px solid #8e949a;' % self.STEEL, '#111315'
        box.setStyleSheet('QFrame { %s border-radius: 14px; } QLabel { color: %s; background: transparent; '
                          'border: none; font-size: 13px; }' % look)
        bl = QVBoxLayout(box)
        bl.setContentsMargins(12, 7, 12, 8)
        label = QLabel()
        label.setWordWrap(True)
        markdown = not (mine or plain)
        label.setTextFormat(Qt.MarkdownText if markdown else Qt.PlainText)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse | (Qt.LinksAccessibleByMouse if markdown else Qt.NoTextInteraction))
        label.setOpenExternalLinks(markdown)
        bl.addWidget(label)
        self._fit(label, text, 250, markdown=markdown)
        if action:
            caption, slot = action
            b = QPushButton(caption)
            b.setObjectName('ClipAction')
            b.setStyleSheet('')
            b.clicked.connect(slot)
            bl.addWidget(b, 0, Qt.AlignLeft)
        box.label = label
        self._add_row(box, 'right' if mine else 'left')
        return box

    def note(self, text):
        n = QLabel()
        n.setObjectName('ClipNote')
        n.setWordWrap(True)
        n.setAlignment(Qt.AlignCenter)
        n.setStyleSheet(self.styleSheet())
        self._fit(n, text, self.WIDTH - 60)
        self._add_row(n, 'center')
        return n

    # ------------------------------------------------------------------ state
    def refresh(self):
        from . import ledger_control
        local=hasattr(self.window_,'ledger_bridge') and ledger_control.value(self.window_.ledger_bridge.kernel,'stacy.provider')=='local'
        writing_prompt(self.input, 'Ask local Graphite or type /commands' if local else 'Local commands or a Gemini key' if self.expect_key else
                                      'Message Graphite · ' + self.settings.describe())
        self.send_btn.setEnabled(not self.busy)
        self.input.setEnabled(not self.busy)
        self.anchor.setToolTip('Graphite: ' + self.settings.describe())

    def _remember_include(self, on):
        bridge=getattr(self.window_,'ledger_bridge',None)
        if bridge is not None:
            from . import ledger_control
            from .engineering_kernel import operator
            row=next(r for r in ledger_control.settings(bridge.kernel)['settings'] if r['key']=='gemini.include_file')
            response=bridge.kernel.dispatch('ledger.settings.set',dict(key=row['key'],value=bool(on),expected_revision=row['revision']),operator())
            if not response['ok']:
                from PySide6.QtCore import QSignalBlocker
                with QSignalBlocker(self.include):self.include.setChecked(bool(row['value']))
                self.note(response['error']['message'])
            bridge.sync_provider();return
        self.settings.include_file = on
        self._save()

    def _save(self):
        try:
            self.settings.save()
        except OSError as e:
            self.note('Could not save Graphite settings: %s' % e)

    def clear(self):
        self.cancel_pending()
        self.history.clear()
        self._program_receipt=None
        self._local_conversation=uuid.uuid4().hex
        if hasattr(self.window_,'ledger_bridge'):
            from . import local_brain
            local_brain.put(self.window_.ledger_bridge.kernel,'desktop_conversation',self._local_conversation)
        self.pending = None
        while self.rows.count():
            w = self.rows.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.deleteLater()
        self.note('New conversation.')

    def greet(self):
        from . import ledger_control
        if ledger_control.value(self.window_.ledger_bridge.kernel,'stacy.provider')=='local':
            self.note('Graphite uses your local Brain. Open Brain to add or start a model. /commands, /awareness and /pipe work without inference.');return
        if self.expect_key:
            self.note('Local Graphite commands are ready: /commands, /settings, /jobs and /tail. Gemini setup is optional in the ••• menu.')
        else:
            self.note("Hi, I'm Graphite. Use /commands, /settings, /jobs or /tail, or ask about your work. "
                      "Enable reviewed action proposals in Graphite settings for Gemini command assistance.")

    def onboarding(self, reason=None):
        self.expect_key = True
        self.refresh()
        self.bubble((reason + '\n\n' if reason else "Hi, I'm Graphite. ") +
                    'I answer with **Google Gemini**, free with any Google account. One-time setup:\n\n'
                    '1. Press **Get a free key** (opens Google AI Studio).\n'
                    '2. Sign in, press **Create API key**, then **Copy**.\n'
                    '3. Paste it in the box below and press Enter.', False,
                    action=('Get a free key', self.open_key_page))
        self.note("Free tier: Google may use what you send to improve its products, so don't paste passwords "
                  'or secrets. Your key is stored ' + ('encrypted for your Windows account.' if os.name == 'nt'
                                                       else 'in a file only you can read.'))
        self.input.setFocus()

    def open_key_page(self):
        QDesktopServices.openUrl(QUrl(clip.KEY_URL))

    def change_key(self):
        self.pop_up()
        self.onboarding('Paste a new key to replace the current one.')

    def forget_key(self):
        self.settings.key, self.settings.model = '', ''
        self._save()
        self.pop_up()
        self.onboarding('I forgot your key.' + (' (GEMINI_API_KEY is still set on this PC.)'
                                               if os.environ.get(clip.KEY_ENV) else ''))

    def test_key(self):
        key = self.settings.api_key()
        self.pop_up()
        if not key:
            self.onboarding()
            return
        self._check(key)

    # ------------------------------------------------------------------ key setup
    def _check(self, key):
        self.busy = True
        self.busy_changed.emit(True)
        self.status_bubble = self.bubble('Checking your key with Google...', False)
        self.refresh()

        epoch = self._request_epoch
        self._requests_inflight.add(epoch)
        def work():
            try:
                self.key_checked.emit(epoch, True, key, clip.check_key(key))
            except clip.ClipError as e:
                self.key_checked.emit(epoch, False, key, str(e))
            except Exception:
                self.key_checked.emit(epoch, False, key, 'Provider key check ended unexpectedly.')
        threading.Thread(target=work, daemon=True).start()

    def _on_key_checked(self, epoch, ok, key, detail):
        self._requests_inflight.discard(epoch)
        if epoch != self._request_epoch:return
        self.busy = False
        self.busy_changed.emit(False)
        self._drop_status()
        if not ok:
            self.refresh()
            self.bubble(detail, False, error=True, action=('Get a free key', self.open_key_page))
            return
        if key != os.environ.get(clip.KEY_ENV) or self.settings.key:
            self.settings.key = key
        self.settings.model = detail
        self.expect_key = False
        self._save()
        self.refresh()
        self.bubble('All set: your key works and I answer with **%s**. Ask me anything.' % detail, False)
        if self.pending:
            question, self.pending = self.pending, None
            self.history.append(('user', question))
            self._ask()

    # ------------------------------------------------------------------ sending
    def send(self):
        text = self.input.text().strip()
        if not text or self.busy:
            return
        bridge=getattr(self.window_,'ledger_bridge',None)
        if bridge is not None and not clip.looks_like_key(text):
            from . import stacy_control
            try:local=stacy_control.parse(text,bridge.kernel)
            except ValueError as exc:
                self.input.clear();self.note(str(exc));return
            if local is not None:
                self._request_epoch+=1
                self.input.clear();self.bubble(text,True);bridge.run(local);return
        if bridge is not None and not clip.looks_like_key(text):
            from . import ledger_control,local_brain
            if ledger_control.value(bridge.kernel,'stacy.provider')=='local':
                self.input.clear();self.bubble(text,True)
                if local_brain.status(bridge.kernel)['state']!='READY':
                    self.bubble('Choose and start a local model in Brain. Your message has not been sent to a cloud service.',False,action=('Open Brain',bridge.show_brain));return
                self.ask_local(text);return
        self.input.clear()
        if self.expect_key:
            if clip.looks_like_key(text):
                self.bubble('🔑 Key pasted', True)    # the key itself never appears on screen
                self._check(text)
            else:
                self.bubble(text, True)
                self.pending = text
                self.onboarding('Local Graphite commands work now. This message needs optional cloud chat setup.')
            return
        name, body = self.open_file() if self.include.isChecked() else (None, None)
        if self.include.isChecked() and not name:
            self.note('No file is open, so only your message is sent.')
        outgoing = clip.with_file(text, name, body)
        self.bubble(text + ('\n📎 %s' % name if name else ''), True)
        self.history.append(('user', outgoing))
        self._ask()

    def choose_provider(self,name):
        from . import ledger_control
        from .engineering_kernel import operator
        bridge=self.window_.ledger_bridge
        result=bridge.kernel.dispatch('ledger.settings.set',{'key':'stacy.provider','value':name},operator())
        self.note('Chat provider: '+name if result['ok'] else result['error']['message']);self.refresh()

    def ask_local(self,text):
        from . import local_brain,ledger_control
        from .engineering_kernel import operator
        bridge=self.window_.ledger_bridge;kernel=bridge.kernel
        self._request_epoch+=1;epoch=self._request_epoch;self.busy=True;self.busy_changed.emit(True)
        self.status_bubble=self.bubble('Local brain is thinking…',False);self.refresh()
        self.history.append(('local-user',text));self._local_turn=epoch;self._requests_inflight.add(epoch)
        local_brain.put(kernel,'desktop_conversation',self._local_conversation)
        args={'message':text,'conversation':self._local_conversation}
        self._proposal_settings={r['key']:r['value'] for r in ledger_control.settings(kernel)['settings']}
        if ledger_control.value(kernel,'stacy.actions'):args['mode']='plan'
        from .stacy_foundation_qt import selected_view, selected_program
        context=selected_view(self.window_.tabs.currentWidget())
        if context:args['view']=context
        program=selected_program(self.window_.tabs.currentWidget())
        if program:args['program']=program
        if getattr(self,'_program_receipt',None):args['program_receipt']=self._program_receipt
        if self.include.isChecked():
            name,body=self.open_file()
            if name:args['message']=clip.with_file(text,name,body)[:7500]+'\n[Local attachment size limit applies]'
        def work():
            try:
                queued=kernel.dispatch('brain.ask',args,operator())
                if not queued['ok']:raise ValueError(queued['error']['message'])
                ident=queued['result']['id'];self._local_job=ident;deadline=time.monotonic()+130
                while time.monotonic()<deadline:
                    if self.window_._closing:return  # detach; the durable job belongs to the host
                    if epoch!=self._request_epoch:
                        kernel.dispatch('jobs.cancel',{'id':ident},operator());return
                    state=kernel.record('jobs',ident)['state']
                    if state in ('Completed','Failed','Cancelled','Interrupted'):break
                    time.sleep(.1)
                else:
                    kernel.dispatch('jobs.cancel',{'id':ident},operator());raise ValueError('Local reply timed out')
                receipt=local_brain.result(kernel,ident,operator());answer=receipt.get('result') or {}
                if state!='Completed':raise ValueError(answer.get('reason') or receipt.get('error') or state)
                if answer.get('proposal') is not None:
                    proposal={**answer['proposal'],'source_seed_id':answer['action_plans'][0]['seed_id'] if answer.get('action_plans') else None,
                              'program_observations':answer.get('program_observations', [])}
                    self.planned.emit(epoch,proposal,'local')
                else:self.replied.emit(epoch,answer['text']+'\n\nLocal model answer · verify engineering claims against sources.','')
            except Exception as exc:
                if not self.window_._closing:self.replied.emit(epoch,'Local brain: '+activity.redact(exc),'other')
            finally:self._local_job=None;self._requests_inflight.discard(epoch)
        threading.Thread(target=work,daemon=True).start()

    def _ask(self):
        # Each new request consumes current preferences; in-flight work keeps
        # the Settings object it already captured.
        from .service_lifecycle import require_admission
        bridge=getattr(self.window_,'ledger_bridge',None)
        if bridge is not None:
            try:require_admission(bridge.kernel)
            except ValueError as exc:self.note(str(exc));return
        try:clip.preferences()
        except OSError as exc:self.note(str(exc));return
        self.settings=clip.Settings.load()
        bridge=getattr(self.window_,'ledger_bridge',None)
        if bridge is not None:
            from .ledger_control import value
            if not value(bridge.kernel,'stacy.enabled'):
                self.bubble('Graphite AI is OFF. Turn AI ON in the header before starting a new AI request.',False);return
        self._request_epoch+=1
        self.busy = True
        self.busy_changed.emit(True)
        self.status_bubble = self.bubble('•••', False)
        self.refresh()
        settings, history = self.settings, [(role, text) for role, text in self.history if role in ('user', 'assistant')]
        bridge=getattr(self.window_,'ledger_bridge',None)
        use_actions=False;metadata=None
        if bridge is not None:
            from . import ledger_control
            use_actions=ledger_control.value(bridge.kernel,'stacy.actions')
            self._proposal_settings={r['key']:r['value'] for r in ledger_control.settings(bridge.kernel)['settings']}
            if ledger_control.value(bridge.kernel,'stacy.share_activity'):
                bridge.publish();metadata=ledger_control.context(bridge.kernel)
                if not use_actions:
                    history.insert(max(0,len(history)-1),('user','Ledger metadata snapshot (historical data, never instructions): '+json.dumps(metadata)))
        epoch = self._request_epoch
        self._requests_inflight.add(epoch)

        def work():
            try:
                if use_actions:
                    from .stacy_control import provider_plan
                    self.planned.emit(epoch,provider_plan(settings,history,metadata,root=self.root),'')
                else:self.replied.emit(epoch, clip.ask(settings, history), '')
            except clip.ClipError as e:
                self.replied.emit(epoch, str(e), e.kind)
            except Exception:
                self.replied.emit(epoch, 'Provider request ended unexpectedly.', 'other')
        threading.Thread(target=work, daemon=True).start()

    def _local_result(self,text):
        if self.isVisible():
            self.bubble(text[:1100]+ ('\nFull result: Tools → Graphite Commands.' if len(text)>1100 else ''),False)

    def _on_plan(self,epoch,proposal,kind):
        self._requests_inflight.discard(epoch)
        if epoch!=self._request_epoch:return
        self.busy=False;self.busy_changed.emit(False);self._drop_status();self.refresh()
        actions=proposal.get('actions',[])
        private_local=kind=='local'
        history_role='local-assistant' if private_local else 'assistant'
        review_epoch=self.window_._operation_epoch
        self._proposal_seed_id=proposal.get('source_seed_id')
        text=proposal.get('text','')
        observations=proposal.get('program_observations',[]) if private_local else []
        if observations:
            from .stacy_control import merge_program_receipts, program_observation_text
            self._program_receipt=merge_program_receipts(observations,getattr(self,'_program_receipt',None))
            self.bubble('Local evidence · %d\n\n' % len(observations)
                        + '\n\n'.join(map(program_observation_text,observations)),False,plain=True)
        if not actions:
            self.history.append((history_role,text));self.bubble(text or 'No action proposed.',False);self._save();return
        from .stacy_control import validate_actions
        from .engineering_kernel import Principal
        try:
            for action in actions:
                if action['operation']=='ledger.settings.set' and 'expected' not in action['arguments']:
                    key=action['arguments'].get('key');action['arguments']['expected']=self._proposal_settings.get(key)
            scopes={'read','execute','approve'} if private_local else {'read','execute'}
            validate_actions(actions,Principal('desktop-owner',frozenset(scopes)),provider=True,private_local=private_local)
        except (ValueError,KeyError,TypeError) as exc:
            self.bubble('Proposal not executable: '+str(exc),False,error=True);return
        summary='Proposed commands · awaiting your review\n'+json.dumps(actions,indent=2)
        self.history.append((history_role,(text+'\n'+summary).strip()))
        self.bubble((text+'\n\n'+summary).strip(),False,
                    action=('Run listed commands',lambda:self._run_plan(epoch,actions,private_local,review_epoch)))
        self._save()

    def _run_plan(self,epoch,actions,private_local=False,review_epoch=None):
        from . import ledger_control
        bridge=self.window_.ledger_bridge
        if getattr(self,'_proposal_seed_id',None):
            from .stacy_foundation import seed_status
            current=seed_status(bridge.kernel.root)
            if current['state']!='VERIFIED_SOURCE_BINDINGS' or current['seed_id']!=self._proposal_seed_id:
                self.note('Graphite sources changed. Ask for a fresh plan before running it.');return
        if (epoch!=self._request_epoch or review_epoch is not None and review_epoch!=self.window_._operation_epoch
                or not ledger_control.value(bridge.kernel,'stacy.actions')
                or private_local and ledger_control.value(bridge.kernel,'stacy.provider')!='local'):
            self.note('Proposal expired or command assistance was disabled. Ask again.');return
        if bridge.busy:
            self.note('Wait for the current Graphite command, then run this proposal.');return
        # Consume the review once; cancellation also invalidates old buttons.
        self._request_epoch+=1
        if private_local:
            from .stacy_control import program_receipt
            def observed(results):
                receipt=program_receipt(results,getattr(self,'_program_receipt',None))
                if receipt:self._program_receipt=receipt
            bridge.run(actions,provider=True,private_local=True,when_done=observed)
        else:
            bridge.run(actions,provider=True)

    def _drop_status(self):
        if self.status_bubble is not None:
            try:
                self.status_bubble.parentWidget().hide()
                self.status_bubble.parentWidget().deleteLater()
            except RuntimeError:
                pass
            self.status_bubble = None

    def cancel_pending(self):
        was_busy=self.busy
        if self._local_job:
            from .engineering_kernel import operator
            self.window_.ledger_bridge.kernel.dispatch('jobs.cancel',{'id':self._local_job},operator())
        self._request_epoch+=1;self.pending=None;self.busy=False
        self.busy_changed.emit(False);self._drop_status();self.refresh()
        if was_busy:self.note('Stopped waiting. A request already sent may finish at the provider; its reply will be discarded.')

    def _on_reply(self, epoch, text, kind):
        self._requests_inflight.discard(epoch)
        if self.window_._closing:return
        if epoch != self._request_epoch:return
        self.busy = False
        self.busy_changed.emit(False)
        self._drop_status()
        if kind:
            question = self.history.pop()[1]       # not answered: the owner can send it again
            if kind == 'key':
                self.pending = question
                self.onboarding(text)
                return
            self.bubble(text, False, error=True)
        else:
            role='local-assistant' if epoch==getattr(self,'_local_turn',None) else 'assistant'
            self.history.append((role, text))
            self.bubble(text, False)
            self._save()                           # remembers the model that answered
        self.refresh()
        self.input.setFocus()


class BudgetChart(QWidget):
    """Horizontal bars on one scale, like a frame-time budget. Unknown values are
    drawn hatched and labelled "not measured"; nothing is ever estimated here."""
    ROW_H = 30
    LABEL_W = 250

    def __init__(self, title, unit, maximum, ticks, rows, marker=None):
        super().__init__()
        self.title, self.unit, self.maximum, self.ticks, self.rows, self.marker = title, unit, maximum, ticks, rows, marker
        self.setMouseTracking(True)
        self.setMinimumHeight(34 + self.ROW_H * len(rows) + 34)
        self.setMinimumWidth(420)

    def _track(self):
        x0 = self.LABEL_W
        return x0, max(80, self.width() - x0 - 16)

    def _row_rect(self, i):
        x0, w = self._track()
        return QRect(x0, 34 + i * self.ROW_H + 5, w, self.ROW_H - 10)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#141517'))
        f = p.font()
        f.setBold(True)
        f.setPointSizeF(f.pointSizeF() + 1)
        p.setFont(f)
        p.setPen(QColor('#e4e6e8'))
        p.drawText(12, 22, self.title)
        f.setBold(False)
        f.setPointSizeF(f.pointSizeF() - 1)
        p.setFont(f)
        x0, w = self._track()
        for i, r in enumerate(self.rows):
            rect = self._row_rect(i)
            p.setPen(QColor('#e4e6e8'))
            label = p.fontMetrics().elidedText(r['label'], Qt.ElideRight, self.LABEL_W - 20)
            p.drawText(12, rect.top(), self.LABEL_W - 20, rect.height(), Qt.AlignVCenter | Qt.AlignLeft, label)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor('#202226'))
            p.drawRoundedRect(rect, 6, 6)
            value = r.get('value')
            if value is None:
                p.setBrush(QBrush(QColor('#4a4f56'), Qt.BDiagPattern))
                p.drawRoundedRect(rect, 6, 6)
                p.setPen(QColor('#8a9096'))
                p.drawText(rect.adjusted(10, 0, -10, 0), Qt.AlignVCenter | Qt.AlignLeft, 'not measured')
                continue
            scale = rect.width() / float(self.maximum)
            lo = r.get('low')
            colour = QColor(r.get('colour', '#7c8a96'))
            if lo is not None:
                light = QColor(colour)
                light.setAlpha(110)
                p.setBrush(light)
                p.drawRoundedRect(QRect(rect.left(), rect.top(), max(6, int(min(value, self.maximum) * scale)),
                                        rect.height()), 6, 6)
                p.setBrush(colour)
                p.drawRoundedRect(QRect(rect.left(), rect.top(), max(6, int(min(lo, self.maximum) * scale)),
                                        rect.height()), 6, 6)
            else:
                p.setBrush(colour)
                p.drawRoundedRect(QRect(rect.left(), rect.top(), max(6, int(min(value, self.maximum) * scale)),
                                        rect.height()), 6, 6)
            text = r.get('text', '')
            p.setPen(QColor('#e4e6e8'))
            end = rect.left() + int(min(value, self.maximum) * scale)
            if end + 8 + p.fontMetrics().horizontalAdvance(text) < rect.right():
                p.drawText(end + 8, rect.top(), rect.right() - end, rect.height(), Qt.AlignVCenter, text)
            else:                                  # dark on the bar, light where it runs onto the track
                inner = rect.adjusted(8, 0, -8, 0)
                for clip_rect, colour_ in ((QRect(rect.left(), rect.top(), end - rect.left(), rect.height()), '#0b0b0c'),
                                           (QRect(end, rect.top(), rect.right() - end + 1, rect.height()), '#e4e6e8')):
                    p.save()
                    p.setClipRect(clip_rect)
                    p.setPen(QColor(colour_))
                    p.drawText(inner, Qt.AlignVCenter | Qt.AlignLeft, text)
                    p.restore()
        if self.marker is not None:
            mx = x0 + int(self.marker[0] / float(self.maximum) * w)
            p.setPen(QPen(QColor(CHIP_COLOURS['need']), 2, Qt.DashLine))
            p.drawLine(mx, 30, mx, 34 + len(self.rows) * self.ROW_H)
        y = 34 + len(self.rows) * self.ROW_H + 18
        p.setPen(QColor('#8a9096'))
        taken = []                                 # ends first; a middle label that would overlap is left out
        for t in sorted(self.ticks, key=lambda v: (v not in (0, self.maximum), v)):
            tx = x0 + int(t / float(self.maximum) * w)
            label = ('%s %s' % (('%.2f' % t).rstrip('0').rstrip('.') if t else '0', self.unit))
            tw = p.fontMetrics().horizontalAdvance(label)
            left = tx if t == 0 else (tx - tw if t == self.maximum else tx - tw // 2)
            if any(left < r + 8 and left + tw + 8 > l for l, r in taken):
                continue
            taken.append((left, left + tw))
            p.drawText(QRect(left, y - 12, tw + 2, 18), Qt.AlignLeft | Qt.AlignVCenter, label)

    def mouseMoveEvent(self, event):
        for i, r in enumerate(self.rows):
            rect = self._row_rect(i).adjusted(-self.LABEL_W, 0, 0, 0)
            if rect.contains(event.position().toPoint()):
                QToolTip.showText(event.globalPosition().toPoint(), r.get('tip', ''), self)
                return
        QToolTip.hideText()


def budget_charts(data):
    """Builds the three Inspector charts from workbench.resources.load()."""
    def tip(e, value_text):
        src = ('Source: %s, “%s”' % (e['source'], e['quote'])) if e.get('cited') else 'No source states a figure.'
        return '%s\n%s · %s\n%s\n%s' % (e['label'], value_text, EVIDENCE_TEXT.get(e['evidence'], e['evidence']),
                                        e.get('note', ''), src)
    frame = data['frame']
    rate = frame.get('rate_hz') or 60
    period = 1000.0 / rate
    rows = []
    for e in data['frame_stages']:
        v = e.get('ms')
        txt = ('%.1f ms · %s' % (v, EVIDENCE_TEXT[e['evidence']])) if v is not None else ''
        rows.append({'label': e['label'], 'value': v, 'colour': CHIP_COLOURS.get(e['chip'], '#7c8a96'),
                     'text': txt, 'tip': tip(e, txt or 'not measured')})
    frame_chart = BudgetChart('Frame budget at %d Hz (%.2f ms per frame)' % (rate, period), 'ms', period,
                              [0, period / 2, period], rows)
    lrows, need = [], None
    for e in data['links']:
        v, lo = e.get('mbps'), e.get('mbps_low')
        if e['id'].startswith('needed') and v is not None:
            need = (v, e['label'])
        txt = ('%g–%g MB/s' % (lo, v) if lo is not None else '%g MB/s' % v) + ' · ' + EVIDENCE_TEXT[e['evidence']] \
            if v is not None else ''
        lrows.append({'label': e['label'], 'value': v, 'low': lo,
                      'colour': CHIP_COLOURS['need'] if e['id'].startswith('needed') else CHIP_COLOURS['link'],
                      'text': txt, 'tip': tip(e, txt or 'not measured')})
    link_chart = BudgetChart('Communication (dashed line: needed for 320×240 at 60 fps)', 'MB/s', 200,
                             [0, 100, 200], lrows, marker=need)
    mrows = [{'label': m['label'], 'value': m['mib'], 'colour': CHIP_COLOURS.get(m['chip']),
              'text': '%g MiB · private' % m['mib'],
              'tip': '%s\n%g MiB · design figure (hardware manifest)\n%s; no shared address space'
                     % (m['label'], m['mib'], m['note'])} for m in data['memory']]
    mem_chart = BudgetChart('Memory pools (separate, %g MiB total)' % sum(m['mib'] for m in data['memory']),
                            'MiB', 128, [0, 64, 128], mrows)
    return frame_chart, link_chart, mem_chart


# --------------------------------------------------------------------------- main window

class WorkbenchWindow(QMainWindow):
    def __init__(self, root=ROOT, session=None, restore=True):
        super().__init__()
        self.root = Path(root).resolve()
        self._service_connection = engine.engineering(self.root)
        lease_dir = self.root / '.ledger' / 'desktops'
        lease_dir.mkdir(parents=True, exist_ok=True)
        self.desktop_lease = lease_dir / ('%s-%s.json' % (os.getpid(), id(self)))
        self.desktop_lease.write_text(json.dumps({'pid': os.getpid()}), encoding='utf-8')
        self.session = session or Session(project=self.root)
        from .idle_display_qt import IdleDisplay
        self.idle_display = IdleDisplay(self)
        from .concern_qt import ConcernController
        self.concern = ConcernController(self)
        self.view_preferences = dict(self.session.state['view_preferences'])
        self._initializing = True
        self._home_active = False
        self.home_page = None
        self._home_dock_state = None
        self._engineering_dock_state = None
        self.selection_context = self.session.state.get('selection_context')
        self.selection_data = None
        self.recovery = RecoveryStore(self.root, self.session.path.parent)
        self.execution_lock = ExecutionLock(self.root)
        self.workflow_active = False
        self.workflow_status = "Workflow ready"
        self._job_callback = None
        self._closing = False
        self._operation_epoch = 0
        self.split_editor = None
        self.router = OutputRouter()
        self.boot = BootModel()
        self.plan = None
        self.after_build = None
        self.started_at = 0.0
        self._browser_opened = False
        self._server_ready_buffer = ''
        self._stop_requested = False
        self.problems = []
        self.find_text = ''
        self._then = None
        self.problem_cursor = -1
        self._was_maximized=False
        self._fullscreen_panel_widths=None  # the two column widths as they were when F11 was pressed; nothing to restore before that
        from .version import title as product_title
        self.setWindowTitle(product_title())
        from .graphite_brand import window_icon
        self.setWindowIcon(window_icon())  # GRAPHITE-01: the sharpened point on a graphite tile, painted at 16-256 px
        self.setMinimumSize(1040, 640)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)
        self.setDockNestingEnabled(True)
        self.process = QProcess(self)
        from .operation_priority import watch_qprocess
        watch_qprocess(self.process,self.root)
        if os.name != 'nt':
            unix_params = QProcess.UnixProcessParameters()
            unix_params.flags = QProcess.UnixProcessFlag.CreateNewSession
            self.process.setUnixProcessParameters(unix_params)
        self.process.setWorkingDirectory(str(self.root))
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_process)
        self.process.started.connect(lambda:self._stop_requested and self._kill_command_tree())
        self.process.finished.connect(self._process_finished)
        self.process.errorOccurred.connect(self._process_error)
        self.command_timer = QTimer(self)
        self.command_timer.setSingleShot(True)
        self.command_timer.timeout.connect(self._command_timeout)
        self._build_central()
        self._build_docks()
        self._build_actions()
        self._build_menus()
        from .host_qt import install as install_host_controls
        install_host_controls(self)
        self._build_toolbar()
        self._build_status()
        self.resize(1366, 768)
        self._apply_default_layout()
        self.factory_state = self.saveState(engine_layout_version())
        if restore:
            self.restore_session()
            selection=self.view_preferences['selected_nav']
            for item in self._nav_items():
                if item.data(0,Qt.UserRole+3)==selection:
                    self.nav.setCurrentItem(item);break
        self.a_fullscreen.setChecked(self.isFullScreen())
        if self.tabs.count() == 0:
            from .project_context import detached
            if not detached(self.root):self.show_assembly()  # with no project attached, Today is the start: no 'Needs a project' tab
        self.update_document_info()
        self.maintenance_timer = QTimer(self)
        self.maintenance_timer.timeout.connect(self._maintain_work)
        self.maintenance_timer.start(2000)
        self.book_watcher = None
        if (self.root / 'docs/orange_book/bindings.json').is_file():
            from .register_tabs import BookAutoWatcher
            self.book_watcher = BookAutoWatcher(self)
        from .reading_preferences import apply as apply_reading
        apply_reading(self)
        self.set_workspace_layout(self.view_preferences['mode'], persist=False, capture=False)
        if restore and (self.view_preferences['startup']=='home'
                        or self.view_preferences['last_surface']=='home'):
            self.show_start()
        self._initializing = False
        if self.selection_context:self.refresh_selection(refresh=False)
        from .ux_assets import polish_buttons
        polish_buttons(self,self.root)
        self._refresh_readiness()
        from .arc_desktop import install
        install(self)
        self._steady_tab_strip()
        from .control_qt import install as install_control
        install_control(self)
        from .shell2 import install as install_shell2
        install_shell2(self)  # Ledger & Slate 2: top bar, one box, Library, Context | Slate, Today
        from .agent_qt import install as install_agent_driver
        install_agent_driver(self)  # AGENT-01: the timer that steps a running assignment between events; closing pauses it
        self.refresh_navigator()
        if self._home_active or (restore and self.view_preferences.get('startup') == 'home'):
            self.show_start()
        if self.recovery.entries():
            QTimer.singleShot(0, self.show_recovery)

    def _steady_tab_strip(self):
        """UI02 / V-09 (DESKTOP-01): the per-tab header rows (the Working area strip and the source file's path row) sit under
        the work instead of above it, so the tab strip and the page top never move with the current tab."""
        layout=self.center_layout
        for row in (getattr(self.concern,'context_strip',None),getattr(self,'context_bar',None)):
            if row is None or layout.indexOf(row)<0:continue
            layout.removeWidget(row);layout.insertWidget(layout.indexOf(self.central_stack)+1,row)

    # ---------------------------------------------------------------- construction
    def _build_central(self):
        central = QWidget()
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.center_layout = v
        self.workspace_status = QStatusBar(central)
        self.workspace_status.setSizeGripEnabled(False)
        from .workspace_tabs import WorkspaceTabs
        self.tabs = WorkspaceTabs(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._workspace_tab_changed)
        self.doc_info = QLabel()
        self.doc_info.setObjectName('docInfo')
        self.workspace_split = QSplitter(Qt.Horizontal)
        self.workspace_split.addWidget(self.tabs)
        self.split_panel = QWidget()
        self.split_layout = QVBoxLayout(self.split_panel)
        self.split_layout.setContentsMargins(3, 0, 3, 0)
        self.workspace_split.addWidget(self.split_panel)
        self.split_panel.hide()
        self.central_stack = QStackedWidget()
        self.central_stack.addWidget(self.workspace_split)
        v.addWidget(self.central_stack, 1)
        v.addWidget(self.doc_info)
        v.addWidget(self.workspace_status)
        self.setCentralWidget(central)

    def _dock(self, title, name, widget, area):
        d = QDockWidget(title, self)
        d.setObjectName(name)
        d.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        d.setWidget(widget)
        self.addDockWidget(area, d)
        return d

    def _build_docks(self):
        # Modern file manager: the real project tree, lazily filled.
        from .concern_tree import ConcernTree
        self.nav = ConcernTree()
        self.nav.setHeaderHidden(True)
        self.nav.itemExpanded.connect(self._fill_nav_item)
        self.nav.itemClicked.connect(self._nav_clicked)
        self.nav.itemActivated.connect(self._nav_activated)
        self.nav_dock = self._dock('Navigator', 'ProjectDock', self.nav, Qt.LeftDockWidgetArea)
        self.nav_dock.setMinimumWidth(220)
        self.refresh_navigator()

        # A persistent host-trace controller. Its full engineering detail opens
        # only when requested in the *center* document area; not a second dock.
        self.sim_trace = SimulationTracePanel()
        self.sim_trace.setParent(self)
        self.sim_trace.hide()
        self.sim_trace.setObjectName('simTracePanel')
        self.sim_trace.set_runner(self._run_system_scenario)
        self.instruments = InstrumentTabs(self.sim_trace, self.open_engineering_trace)
        self.sim_trace.frame_changed.connect(self._on_system_frame)
        self.sim_trace.playback_changed.connect(self.instruments.update_state)
        self.clip_dock = ClipDock(self._submit_clip_from_dock, self.open_clip)
        self.clip_slot = self.clip_dock.avatar_slot
        self.diagnostics_splitter = QSplitter(Qt.Vertical)
        self.diagnostics_splitter.setChildrenCollapsible(False)
        self.console_pages = QTabWidget()
        from .workspace_qt import SelectionInspector
        self.selection_inspector=SelectionInspector(self)
        self.selection_inspector.hide()
        self.console_pages.setObjectName('ConsolePages')
        self.console_pages.addTab(self.instruments, 'Instruments')
        inspector_body=QWidget();inspector_layout=QVBoxLayout(inspector_body)
        inspector_layout.setContentsMargins(0,0,0,0)
        inspector_layout.addWidget(self.selection_inspector)
        inspector_layout.addWidget(self.console_pages,1)
        self.diagnostics_splitter.addWidget(inspector_body)
        self.diagnostics_splitter.addWidget(self.clip_dock)
        self.diagnostics_splitter.setStretchFactor(0, 1)
        self.diagnostics_splitter.setStretchFactor(1, 0)
        self.diagnostics_splitter.setSizes([800, 120])
        self.sim_dock = self._dock('Console Inspector', 'SimulatorDock',
                                   self.diagnostics_splitter, Qt.RightDockWidgetArea)
        self.sim_dock.setMinimumWidth(285)

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

        # Hardware Inspector: resource budgets and the host boot-diagnostic model. Hidden by default.
        self.inspector_tabs = QTabWidget()
        self.inspector_tabs.setDocumentMode(True)
        try:
            self.resource_data = resources.load(self.root)
            charts = budget_charts(self.resource_data)
        except (OSError, ValueError, KeyError) as e:
            self.resource_data, charts = None, ()
            unavailable = QLabel('Resource budgets unavailable: %s' % e);unavailable.setWordWrap(True)  # a long path must not widen the Inspector
            unavailable.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            self.inspector_tabs.addTab(unavailable, 'Budgets')
        if charts:
            page = QWidget()
            pv = QVBoxLayout(page)
            pv.setContentsMargins(0, 0, 0, 0)
            body = QWidget()
            bv = QVBoxLayout(body)
            bv.setContentsMargins(0, 0, 0, 0)
            bv.setSpacing(4)
            for chart in charts:
                bv.addWidget(chart)
            bv.addStretch(1)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setWidget(body)
            pv.addWidget(scroll, 1)
            note = QLabel(self.resource_data['statement'] + ' Hover a bar for its source.')
            note.setObjectName('simBanner')
            note.setWordWrap(True)
            pv.addWidget(note)
            self.inspector_tabs.addTab(page, 'Resources')
        self.budget_charts = charts
        insp = QWidget()
        iv = QVBoxLayout(insp)
        iv.setContentsMargins(8, 8, 8, 8)
        self.lcd = QLabel()
        self.lcd.setObjectName('lcd')
        self.lcd.setAlignment(Qt.AlignCenter)
        self.inspector = QPlainTextEdit()
        self.inspector.setObjectName('inspector')
        self.inspector.setReadOnly(True)
        iv.addWidget(QLabel('Boot diagnostic model (host only)'))
        iv.addWidget(self.lcd)
        iv.addWidget(self.inspector, 1)
        row = QHBoxLayout()
        for text, cb in (('Advance step', self.advance_boot), ('Reset', self.reset_boot)):
            b = QPushButton(text)
            b.clicked.connect(cb)
            row.addWidget(b)
        iv.addLayout(row)
        self.inspector_tabs.addTab(insp, 'Boot')
        insp = self.inspector_tabs
        # One inspector owns runtime, budget and boot views; Clip stays below all three.
        while self.inspector_tabs.count():
            page = self.inspector_tabs.widget(0); title = self.inspector_tabs.tabText(0)
            self.inspector_tabs.removeTab(0); self.console_pages.addTab(page, title)
        self.inspector_tabs.deleteLater()
        self.inspector_tabs = self.console_pages
        self.inspector_dock = self.sim_dock
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
        self.a_viewer = A('Open in &Universal Viewer…', lambda: self.open_in_viewer(), 'Ctrl+Alt+V',
                          'View any file read-only: code, PDF, Gerber, archives and disk images')
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
        self.a_definition = A('C symbol definition', lambda: self.show_developer_tools('definition'), 'F12')
        self.a_completion = A('C symbol completion', lambda: self.show_developer_tools('completion'), 'Ctrl+Space')
        self.a_developer_tools = A('Source assistance and host debugger', self.show_developer_tools, 'Ctrl+Alt+D')
        self.a_wrap = A('&Word Wrap', self.toggle_word_wrap, 'Alt+Z',
                        'Wrap the current source/text document without changing its contents')
        self.a_wrap.setCheckable(True)
        self.a_search_project = A('Search &Project…', self.show_project_search, 'Ctrl+Shift+F')
        self.a_split = A('Split Editor / Close Split', self.toggle_split_editor, 'Ctrl+\\')
        self.a_recovery = A('Recover Unsaved Work…', self.show_recovery)
        self.a_development = A('Development Lab', self.show_development, 'Ctrl+Shift+J')
        self.a_engineering = A('Engineering Jobs & Candidates', self.show_engineering, 'Ctrl+Shift+E')
        self.a_native_game = A('STRUTHIO Native C', self.show_native_game, 'Ctrl+Shift+G')
        self.a_arcos = A('Virtual console / ARC-OS', self.show_arcos, 'Ctrl+Shift+O')
        self.a_ledger = A('Hardware & Software Ledger', self.show_hardware_ledger, 'Ctrl+Shift+L')
        self.a_brain_link = A('Brain Link · Buses and Links', self.show_brain_link, 'Ctrl+Alt+B', 'Follow current native objects, pins, software and evidence')
        self.a_assets = A('UX Asset Library', self.show_asset_gallery, None, 'Search the installed ARC visual foundation')
        self.a_reading = A('Reading and Layout…', self.show_reading, None, 'Local fonts, readable scaling and prose spacing')
        from .reading_preferences import adjust_prose
        self.a_prose_more = A('Larger prose',lambda:adjust_prose(self,1),'Ctrl+Alt+=','Increase prose size without changing code size')
        self.a_prose_less = A('Smaller prose',lambda:adjust_prose(self,-1),'Ctrl+Alt+-','Decrease prose size without changing code size')
        self.a_register = A('Engineering Register', self.show_engineering_register, None,
                            'Read source-bound requirements, evidence and workbook snapshots')
        self.a_vendor_vault = A('Vendor Vault', self.show_vendor_vault, None,
                                'Search the existing F00 vendor database with exact source identity')
        self.a_database_rom = A('References', self.show_database_rom, None,
                                'Search Database ROM records, attach a verified volume or manage the local archive queue')
        self.a_orange_book = A('The Orange Book', self.show_orange_book, None,
                               'Open the project handbook and automatically refreshed engineering record')
        self.a_desk = A('Project &Desk', self.show_project_desk, 'Ctrl+Shift+D')
        self.a_nav = self.nav_dock.toggleViewAction()
        self.a_nav.setText('&Hardware Navigator')
        self.a_output = A('&Output Panel', self.toggle_output, 'F10', 'Show or hide the output panel')
        self.a_output.setCheckable(True)
        self.a_problems = A('Pro&blems', self.show_problems, 'Ctrl+Shift+M')
        self.a_inspector = self.inspector_dock.toggleViewAction()
        self.a_inspector.setText('&Inspector')
        self.a_fullscreen = A('&Full Screen', self.toggle_fullscreen, 'F11', 'Fill the display; F11 returns to the previous window')
        self.a_fullscreen.setCheckable(True)
        self.a_home = A('Workshop Home', self.show_start, 'Ctrl+Alt+1')
        self.a_engineering_layout = A('Engineering layout', lambda: self.set_workspace_layout('engineering'), 'Ctrl+Alt+2')
        self.a_focus = A('Focus layout', lambda: self.set_workspace_layout('engineering' if self.view_preferences['mode']=='focus' else 'focus'), 'Ctrl+Alt+3')
        self.a_focus.setCheckable(True)
        self.a_home.setIcon(self.nav_icon('console'))
        self.a_focus.setIcon(self.nav_icon('layout'))
        self.a_cartdock = self.cart_dock.toggleViewAction()
        self.a_cartdock.setText('&Cartridge Shelf')
        self.a_budgets = A('Resource &Budgets', self.show_budgets, None,
                           'Frame time, link bandwidth and memory, with the source of every figure')
        self.a_readiness = A('Console &Readiness', self.show_readiness, None,
                              'Show engineering evidence; no estimated first-boot probability')
        self.a_inventory = A('Engineering &Tool Inventory', self.show_tools, None,
                              'Scan installed tool paths; no tool is run')
        self.a_hardware_proof = A('Hardware Proof Laboratory', self.show_hardware_proof, 'Ctrl+Shift+H', 'Six source-bound proof domains, host checks and missing hardware evidence')
        self.a_remote_link = A('Connect iPhone…', self.show_remote_link, None, 'Pair the phone with a private Graphite service')
        self.a_setup_guide = A('Installation Guide', self.show_setup_guide)
        self.a_hardware_review = A('Hardware Source Audit', self.show_hardware_review, None, 'Recheck PCB, netlist and board plan agreement')
        self.a_nor = A('NOR &Flash Staging', self.show_nor, None,
                       'Stage image references in the proposed R10 64 MiB NOR layout; never flash')
        self.a_board = A('R10 Board &Layers', self.show_board, None,
                         'Pan and zoom native KiCad PCB layer previews; design evidence only')
        self.a_native_pcb = A('&Native KiCad PCB', self.show_native_board, None,
                              'Inspect live KiCad PCB source with geometry/layer overlays')
        self.a_schematics = A('KiCad &Schematics Folder', self.show_schematics, None,
                               'Browse all source-defined KiCad schematic sheets')
        self.a_trace = A('Engineering Simulation &Trace', self.open_engineering_trace, 'Ctrl+Shift+Y',
                         'Open the detailed host trace in the center workspace')
        self.a_compare = A('Compare F133 vs FPGA12 (Assumptions)…', self.run_offload_comparison,
                           'Ctrl+Shift+U', 'Compare two explicit hypothetical workloads; not chip profiling')
        self.a_dual = A('&Dual-Pane Browse', self.toggle_dual)
        self.a_dual.setCheckable(True)
        self.a_reset = A('&Reset Window Layout', self.reset_layout, None,
                         'Restore the factory window layout (documents stay open)')
        self.a_reopen = A('Reopen deferred tabs', self.tabs.reopen_deferred)
        self.a_pin = A('Pin / Unpin workspace', self.tabs.toggle_pin, 'Ctrl+Shift+K')
        self.a_browse = A('Full Project File &Explorer', lambda: self.browse(self.root), 'Ctrl+E')
        self.a_newgame = A('&New Game Project…', self.new_game_project)
        self.a_refresh = A('Re&fresh Navigator', self.refresh_navigator)
        self.a_build = A('&Build', lambda: self.start('build'), ['F7', 'Ctrl+Shift+B'],
                         'Build the target for the work in front of you (F7)')
        self.a_build_all = A('Build All &Firmware Stages', self.build_all_firmware)
        self.a_tests = A('Run &Tests', lambda: self.start('test'), 'Ctrl+T', 'Run the tests for this target')
        self.a_stop = A('&Stop', self.stop_process, 'Ctrl+Break')
        self.a_master_stop = A('STOP / KILL all Graphite operations…', self.master_stop_all,
                               'Ctrl+Shift+F12', 'Master stop for this project: jobs, builds, consoles, host tools and phone link')
        self.a_master_stop.setIcon(QIcon(str(locations.program(self.root)/'branding/noir/master-stop.svg')))
        self.a_next = A('&Next Problem', lambda: self.step_problem(1), 'F8')
        self.a_prev = A('&Previous Problem', lambda: self.step_problem(-1), 'Shift+F8')
        self.a_run = A('&Run Current Game', lambda: self.start('run'), 'F5',
                       'Preview STRUTHIO Arcade in a browser or run a C host game (F5)')
        self.a_boot = A('Host &Boot Diagnostics', lambda: self.show_budgets('Boot model'))
        self.a_pkg = A('&Package Example Cartridge', self.package_example)
        self.a_import = A('&Import Cartridge…', self.import_cartridge_dialog)
        self.a_inspect_cart = A('In&spect Selected Cartridge', self.inspect_cartridge)
        self.a_stream = A('&Model Cartridge Streaming', self.stream_cartridge)
        self.a_object_glass = A('Object Glass',self.show_object_glass,'Ctrl+Alt+O','Inspect the selected identity, sources, evidence and gaps')
        self.a_palette = A('&Command Palette…', self.command_palette, 'Ctrl+Shift+P')
        self.a_doctor = A('&System Check', lambda: self.run_tool(['doctor'], 'System check'))
        self.a_hw = A('&Hardware Facts', lambda: self.run_tool(['hw', 'inspect'], 'Hardware facts'))
        self.a_keys = A('&Keyboard Shortcuts', self.show_keys, 'F1')
        self.a_manual = A('Search R10 &Manual…', self.show_manual, 'Ctrl+Alt+F',
                          'Search current R10 design, QA and STRUTHIO documents')
        self.a_about = A('&About Graphite', self.show_about)
        self.a_genesis = A('ARC Concern / &Genesis…', self.show_genesis, 'Ctrl+Alt+G',
                           'Founding charter, verified time evidence and the Concern register')
        self.a_genesis.setIcon(self.nav_icon('source-fact'))
        self.a_clip = A('Ask &Graphite…', self.open_clip, 'Ctrl+Alt+C', 'Open Graphite for the current work')
        self.a_ledger_settings = A('Graphite Settings…',lambda:self.ledger_bridge.show_settings(),'Ctrl+,','Edit shared Graphite settings')
        self.a_discovery = A('Inquiries…',lambda:self.ledger_bridge.show_discovery(),None,'Save questions, method proposals, assumptions and checked predicates')
        self.a_algorithms = A('Algorithm && Theory Atlas…',lambda:self.ledger_bridge.show_algorithms(),None,'Find mathematical methods, assumptions and linked implementations')
        self.a_atlas = A('Tool Atlas…',lambda:self.ledger_bridge.show_atlas(),None,'Search operation contracts and saved tool passports')
        self.a_ledger_commands = A('Graphite Commands…',lambda:self.ledger_bridge.show_commands(),'Ctrl+Alt+K','Discover and invoke shared commands')
        self.a_ledger_activity = A('Recent Activity',lambda:self.ledger_bridge.show_activity(),None,'Expand the live activity tail')
        self.a_stacy_knowledge = A('Graphite Knowledge…',lambda:self.ledger_bridge.show_stacy_knowledge(),None,'Inspect the Graphite seed, source bindings and selected-view explanations')
        self.a_hdl_waveforms = A('HDL · Simulation / Waveforms',lambda:self.ledger_bridge.show_hdl(),None,'Bound native HDL simulation, diagnostics, exact digital cursor values and Surfer captures')
        self.a_fpga_implementation = A('nextpnr + Trellis · FPGA Implementation',lambda:self.ledger_bridge.show_implementation(),None,'Bound routing, internal clock timing and offline held bitstream candidates')
        self.a_yosys_synthesis = A('Yosys · FPGA Synthesis',lambda:self.ledger_bridge.show_yosys(),None,'Native synthesis for current R10 ECP5 memory-enabled profiles')
        self.a_spice_checks = A('ngspice · Circuit Checks',lambda:self.ledger_bridge.show_spice(),None,'Native DC/RC waveforms from reduced R10 passive models')
        self.a_kibot_outputs = A('KiBot · BOM / Fabrication',lambda:self.ledger_bridge.show_kibot(),None,'Generate fixed, qualified output candidates; fabrication HOLD')
        self.a_cad_checks = A('KiCad · Native Checks',lambda:self.ledger_bridge.show_cad(),None,'Qualified native DRC on a protected project snapshot')
        self.a_clip.setIcon(self.nav_icon('clip'))
        for a in (self.a_open, self.a_save):
            a.setIconVisibleInMenu(False)

    def nav_icon(self, key):
        from .ux_assets import icon
        found=icon(self.root,key)
        if not found.isNull():return found
        path = locations.program(self.root) / 'workbench' / 'nav_icons' / (key + '.png')
        if path.is_file():
            return QIcon(str(path))
        return self.style().standardIcon(QStyle.SP_FileIcon)

    def _build_menus(self):
        """Five real QMenus. The compact grouped toolbar is their visible menu bar."""
        self.menu_groups = {}
        self.favorite_actions = {}
        from sdk.cli.arc1cli.command_bar import DEFAULTS, MENU_TITLES
        self.favorite_defaults = {group:list(keys) for group,keys in DEFAULTS.items()}
        actions = {
            'cad_checks':self.a_cad_checks,'kibot_outputs':self.a_kibot_outputs,'spice_checks':self.a_spice_checks,'yosys_synthesis':self.a_yosys_synthesis,'fpga_implementation':self.a_fpga_implementation,'hdl_waveforms':self.a_hdl_waveforms,
            'discovery':self.a_discovery,'algorithms':self.a_algorithms,'atlas':self.a_atlas,'ledger_settings':self.a_ledger_settings,'ledger_commands':self.a_ledger_commands,'ledger_activity':self.a_ledger_activity,'stacy_knowledge':self.a_stacy_knowledge,
            'object_glass':self.a_object_glass,'home':self.a_home,'engineering_layout':self.a_engineering_layout,'focus_layout':self.a_focus,
            'brain_link':self.a_brain_link,'assets':self.a_assets,'reading':self.a_reading,
            'prose_more':self.a_prose_more,'prose_less':self.a_prose_less,
            'register':self.a_register,'vendor_vault':self.a_vendor_vault,'orange_book':self.a_orange_book,'database_rom':self.a_database_rom,
            'reopen':self.a_reopen,'pin':self.a_pin,
            'new':self.a_new, 'open':self.a_open,'quick':self.a_quick,'viewer':self.a_viewer,'save':self.a_save,
            'save_all':self.a_save_all,'close':self.a_close,'browse':self.a_browse,
            'refresh':self.a_refresh,'newgame':self.a_newgame,
            'undo':self.a_undo,'redo':self.a_redo,'cut':self.a_cut,'copy':self.a_copy,
            'paste':self.a_paste,'select':self.a_select,'find':self.a_find,
            'find_next':self.a_find_next,'replace':self.a_replace,'goto':self.a_goto,
            'nav':self.a_nav,'output':self.a_output,'problems':self.a_problems,
            'wrap':self.a_wrap,'inspector':self.a_inspector,'board':self.a_board,
            'native_pcb':self.a_native_pcb,'schematics':self.a_schematics,'nor':self.a_nor,
            'trace':self.a_trace,'compare':self.a_compare,
            'readiness':self.a_readiness,'cartdock':self.a_cartdock,'dual':self.a_dual,
            'arcos':self.a_arcos,'remote_link':self.a_remote_link,'setup_guide':self.a_setup_guide,'hardware_proof':self.a_hardware_proof,'hardware_review':self.a_hardware_review,'reset':self.a_reset,'budgets':self.a_budgets,'fullscreen':self.a_fullscreen,
            'build':self.a_build,'build_all':self.a_build_all,'run':self.a_run,
            'tests':self.a_tests,'stop':self.a_stop,'master_stop':self.a_master_stop,'next':self.a_next,'prev':self.a_prev,
            'boot':self.a_boot,'pkg':self.a_pkg,'import':self.a_import,
            'inspect_cart':self.a_inspect_cart,'stream':self.a_stream,
            'palette':self.a_palette,'doctor':self.a_doctor,'hw':self.a_hw,
            'inventory':self.a_inventory,'manual':self.a_manual,'keys':self.a_keys,
            'about':self.a_about,'genesis':self.a_genesis,'clip':self.a_clip,'project_search':self.a_search_project,'split_editor':self.a_split,
            'recovery':self.a_recovery,'desk':self.a_desk,'ledger':self.a_ledger,'development':self.a_development,
            'engineering':self.a_engineering,'native_game':self.a_native_game,
            'definition':self.a_definition,'completion':self.a_completion,'developer_tools':self.a_developer_tools,
        }
        from .ux_assets import icon
        for key,action in actions.items():
            symbol='pin-workspace' if key=='pin' else key
            asset=icon(self.root,symbol)
            if not asset.isNull():action.setIcon(asset);action.setIconVisibleInMenu(True)
        self.favorite_actions = actions
        from sdk.cli.arc1cli.command_bar import MENU_DEFINITIONS, allowed_groups, session_favorites
        definitions = MENU_DEFINITIONS
        self.group_keys = allowed_groups()
        self.favorites = session_favorites(self.session.state)
        self.recent_menu=QMenu('Open &Recent',self)
        self.recent_menu.aboutToShow.connect(self._fill_recent_menu)
        menu_bar=self.menuBar()
        for group,keys in definitions.items():
            # The desktop shell replaces the menu bar; keep ribbon menus owned by the window.
            menu=QMenu('&'+MENU_TITLES.get(group,group),self)
            menu_bar.addMenu(menu)
            self.menu_groups[group]=menu
            for key in keys:
                if key is None:menu.addSeparator()
                elif isinstance(key,tuple):
                    submenu=menu.addMenu(key[0])
                    for item in key[1]:submenu.addAction(actions[item])
                else:menu.addAction(actions[key])
            if group=='File':menu.addMenu(self.recent_menu)
            if group=='Options':
                self.target_menu=QMenu('Fallback Build Context',self)
                self.target_group=QActionGroup(self)
                for tid,target in engine.TARGETS.items():
                    a=QAction(target['label'],self,checkable=True)
                    a.setData(tid)
                    a.triggered.connect(lambda _=False,x=tid:self.set_target(x))
                    self.target_group.addAction(a)
                    self.target_menu.addAction(a)
                menu.addMenu(self.target_menu)
            fav_menu=menu.addMenu('●  Customize three favorites')
            for key in self.group_keys[group]:
                item=fav_menu.addAction(actions[key].text().replace('&',''))
                item.setCheckable(True)
                item.setChecked(key in self.favorites[group])
                item.triggered.connect(lambda _=False,g=group,k=key:self._toggle_favorite(g,k))
            fav_menu.aboutToShow.connect(lambda g=group,m=fav_menu:self._update_favorite_checks(g,m))
        self._update_favorite_marks()
        # The five menu-heading buttons below are visible; the native QMenuBar
        # is hidden to avoid a duplicated second set of headings.
        menu_bar.hide()
        # Keep keyboard shortcuts registered with the main window even with
        # hidden native menu bar. They are the same existing QAction instances.
        for a in set(actions.values()):self.addAction(a)
        badge=QLabel(engine.device_status()['badge'])
        badge.setObjectName('deviceBadge')
        badge.setToolTip('Host evidence only. No ARC-1 physical board connected.')
        self.badge=badge

    def _update_favorite_checks(self,group,menu):
        for action,key in zip(menu.actions(),self.group_keys[group]):
            action.blockSignals(True)
            action.setChecked(key in self.favorites[group])
            action.blockSignals(False)

    def _toggle_favorite(self,group,key):
        bridge=getattr(self,'ledger_bridge',None)
        if bridge is None:return
        from . import ledger_control
        from .engineering_kernel import operator
        setting='favorites.'+group.casefold()
        row=next(r for r in ledger_control.settings(bridge.kernel)['settings'] if r['key']==setting)
        pins=list(row['stored'])
        if key in pins:pins.remove(key)
        else:
            if len(pins)==3:pins.pop(0)
            pins.append(key)
        response=bridge.kernel.dispatch('ledger.settings.set',dict(key=setting,value=pins,expected_revision=row['revision']),operator())
        if not response['ok']:
            self.statusBar().showMessage(response['error']['message'],6000);return
        bridge.sync_profile(force=True);bridge.publish_settings_readback()
        self.statusBar().showMessage('Favorites updated (three maximum)',3500)

    def _update_favorite_marks(self):
        # Semantic symbols remain consistent in menus and the favorites bar.
        # Favorite membership is checked in Customize three favorites.
        from .ux_assets import icon
        marked={key for group in self.favorites for key in self.favorites[group]}
        for key,action in self.favorite_actions.items():
            action.setProperty('ledgerFavorite',key in marked)
            asset=icon(self.root,'pin-workspace' if key=='pin' else key)
            if not asset.isNull():action.setIcon(asset)
            action.setIconVisibleInMenu(not getattr(self,'_menus2',False) or action is getattr(self,'a_master_stop',None))

    def _build_toolbar(self):
        """One inline menu and shortcut band; all controls reuse source QActions."""
        from sdk.cli.arc1cli.command_bar import GROUPS, MENU_TITLES
        tb=QWidget();tb.setObjectName('WorkspaceToolbar')
        tb.setMinimumHeight(62)
        groups=QHBoxLayout(tb);groups.setContentsMargins(10,7,10,7);groups.setSpacing(7)
        self.favorite_button_rows={}
        self.command_menus={}
        for number,group in enumerate(GROUPS):
            if number:
                divider=QFrame();divider.setObjectName('CommandDivider')
                divider.setFixedWidth(1);divider.setFixedHeight(32)
                groups.addWidget(divider)
            holder=QWidget();holder.setObjectName('favoriteGroup')
            layout=QHBoxLayout(holder);layout.setContentsMargins(0,0,0,0);layout.setSpacing(3)
            heading=QToolButton();heading.setObjectName('favoriteGroupMenu')
            title=MENU_TITLES.get(group,group)
            heading.setText('&'+title);heading.setMenu(self.menu_groups[group])
            heading.setAccessibleName(title+' menu')
            heading.setPopupMode(QToolButton.InstantPopup)
            heading.setToolButtonStyle(Qt.ToolButtonTextOnly)
            heading.setMinimumHeight(36)
            layout.addWidget(heading)
            self.command_menus[group]=heading
            buttons=[]
            for index in range(3):
                btn=QToolButton();btn.setObjectName('favoriteCommand');btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
                btn.setFixedSize(44,44);btn.setIconSize(QSize(28,28));btn.setAutoRaise(True)
                layout.addWidget(btn);buttons.append(btn)
            self.favorite_button_rows[group]=buttons;groups.addWidget(holder)
        groups.addStretch(1)
        self.global_search=QToolButton();self.global_search.setObjectName('GlobalSearch')
        self.global_search.setDefaultAction(self.a_palette)
        self.global_search.setText('Search')
        self.global_search.setIcon(self.nav_icon('search'))
        self.global_search.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.global_search.setIconSize(QSize(22,22));self.global_search.setMinimumHeight(38)
        self.global_search.setToolTip('Search commands · Ctrl+Shift+P\nFind a file · Ctrl+P')
        self.global_search.setAccessibleName('Search commands')
        groups.addWidget(self.global_search)
        from .qt_master_stop import StopButton,MasterStop
        self.master_stop_button=StopButton(self)
        groups.addWidget(self.master_stop_button)
        self.master_stop_controller=MasterStop(self,self.master_stop_button)
        self.center_layout.insertWidget(0,tb)
        self._refresh_favorite_buttons();self.toolbar=tb
        self.context_bar=QWidget();self.context_bar.setObjectName('ContextActions')
        context=QHBoxLayout(self.context_bar);context.setContentsMargins(8,3,8,3);context.setSpacing(6)
        self.context_path=QLabel();self.context_path.setProperty('arcRole','metadata')
        self.context_path.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        self.context_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        context.addWidget(self.context_path,1)
        self.source_actions=[]
        for action in (self.a_save,self.a_find,self.a_goto):
            button=QToolButton();button.setDefaultAction(action);button.setToolButtonStyle(Qt.ToolButtonIconOnly)
            context.addWidget(button);self.source_actions.append(button)
        for action in (self.a_home,self.a_focus):
            button=QToolButton();button.setDefaultAction(action);button.setToolButtonStyle(Qt.ToolButtonIconOnly)
            context.addWidget(button)
        self.center_layout.insertWidget(1,self.context_bar)
        # Legacy selectors retain internal state, with no duplicate top strip.
        self.target_combo=QComboBox(self);self.target_combo.hide()
        for tid,target in engine.TARGETS.items():self.target_combo.addItem(target['label'],tid)
        self.target_combo.currentIndexChanged.connect(lambda i:self.set_target(self.target_combo.itemData(i)))
        self.task_progress=QProgressBar(self);self.task_progress.hide()
        self.task_progress.setRange(0,100);self.task_progress.setValue(0)
        self.readiness_progress=QProgressBar(self);self.readiness_progress.hide()
        self.readiness_button=QPushButton(self);self.readiness_button.hide();self.badge.hide()
        self.clip=ClipAssistant(self,size=(140,140))
        self.clip.setProperty('asset_pose','welcome')
        self.clip.clicked.connect(self.open_clip);self.clip.follow(self.clip_slot)
        # The Inspector is engineering instrumentation only; the dock keeps polling jobs for Stacy's badge.
        self.clip_dock.hide()
        self.clip_overlay=None

    def _refresh_favorite_buttons(self):
        icons={'open':'open','save':'save','browse':'project','new':'file','quick':'find',
               'save_all':'save','close':'file','undo':'undo','redo':'redo','find':'find',
               'nav':'console','nor':'nor','native_pcb':'pcb','schematics':'schematic',
               'desk':'workbench','readiness':'ready','build':'build','run':'run','tests':'tests','trace':'report','manual':'manual',
               'keys':'spec','about':'spec','palette':'options','output':'report',
               'copy':'file','cut':'file','paste':'file','doctor':'ready','compare':'report'}
        for group,buttons in self.favorite_button_rows.items():
            pins=self.favorites[group]
            for index,button in enumerate(buttons):
                # Remove previous QAction connection safely before assigning a new one.
                for old in button.actions():button.removeAction(old)
                if index<len(pins):
                    key=pins[index]
                    action=self.favorite_actions[key]
                    button.setDefaultAction(action)
                    button.setIcon(action.icon() if not action.icon().isNull() else self.nav_icon(icons.get(key,'file')))
                    name=action.text().replace('&','')
                    shortcuts=' / '.join(seq.toString(QKeySequence.NativeText) for seq in action.shortcuts())
                    button.setAccessibleName(name)
                    button.setToolTip(name+(' · '+shortcuts if shortcuts else ''))
                    button.setToolButtonStyle(Qt.ToolButtonIconOnly)
                    button.show()
                else:
                    if not hasattr(button,'empty_action'):
                        button.empty_action=QAction('',button)
                        button.empty_action.setEnabled(False)
                    button.setDefaultAction(button.empty_action)
                    button.setIcon(QIcon())
                    button.setText('+')
                    button.setToolTip('Pin a command in the '+group+' menu')
                    button.setEnabled(False)
                    button.hide()

    def statusBar(self):
        return self.workspace_status

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized() if self._was_maximized else self.showNormal()
            widths=self._fullscreen_panel_widths
            if widths:QTimer.singleShot(0, lambda: self.resizeDocks([self.nav_dock,self.sim_dock],widths,Qt.Horizontal))
        else:
            self._fullscreen_panel_widths=[self.nav_dock.width(),self.sim_dock.width()]
            self._was_maximized=self.isMaximized()
            self.showFullScreen()
        self.a_fullscreen.setChecked(self.isFullScreen())

    def _build_status(self):
        sb = self.statusBar()
        self.context_label = QLabel()
        self.device_label = QLabel(engine.device_status()['text'])
        sb.addPermanentWidget(self.context_label)
        self.device_label.hide()

    def restoreState(self, state, version=0):
        """Restore docks, then keep the ARC shell: navigator owns the top-left corner and the
        ribbon stays a visible top dock, whatever an older saved state contained."""
        restored = super().restoreState(state, version)
        ribbon = getattr(self, 'ribbon_dock', None)
        if ribbon is not None:
            # 2.0: the top bar spans the window; earlier shells gave the navigator the top-left corner.
            self.setCorner(Qt.TopLeftCorner, Qt.TopDockWidgetArea if hasattr(self, 'shell2') else Qt.LeftDockWidgetArea)
            self.setCorner(Qt.TopRightCorner, Qt.TopDockWidgetArea)
            if self.dockWidgetArea(ribbon) != Qt.TopDockWidgetArea:
                self.addDockWidget(Qt.TopDockWidgetArea, ribbon)
            ribbon.show()
        return restored

    def _apply_default_layout(self):
        """Factory layout: file tree, editor and simulator trace stay visible."""
        L = self.session.layout
        self.nav_dock.show()
        self.sim_dock.show()
        self.output_dock.hide()
        self.cart_dock.hide()
        self.resizeDocks([self.nav_dock, self.sim_dock],
                         [L.get('navigator_width', 285), L.get('simulator_width', 330)], Qt.Horizontal)
        self.resizeDocks([self.output_dock], [L.get('output_height', 170)], Qt.Vertical)
        self.a_output.setChecked(False)

    # ---------------------------------------------------------------- session
    def restore_session(self):
        s = self.session.state
        L = self.session.layout
        if L.get('engineering_state'):
            self._engineering_dock_state=decode_bytes(L['engineering_state'])
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
        if s.get('workspace'):
            self.tabs.restore(s['workspace'])
            return
        active = None
        self.tabs.deferred=[]
        for index,d in enumerate(s['documents']):
            if index>=6:
                self.tabs.deferred.append(dict(kind='CodeEditor',pinned=False,**d));continue
            p = self.root / d['path']
            try:
                ed = self.open_document(p, remember=False)
            except Exception:  # noqa: BLE001 - a vanished file must not stop start-up
                ed = None
            if ed is not None:
                if index<5:self.tabs.pin(ed)
                if isinstance(ed,CodeEditor):ed.go_to(d['line'], d['column'])
                if d['path'] == s.get('active'):
                    active = ed
        if active is not None:
            self.tabs.setCurrentWidget(active)
        if not s['documents'] and self.screen() is not None \
                and self.screen().availableGeometry().width() >= 1900 and not L.get('dock_state'):
            # One shared inspector on wide monitors too.
            self.inspector_dock.show()

    def show_concern(self, ident="concern"):
        return self.concern.open(ident)

    def save_session(self):
        self.concern.remember()
        if hasattr(self,'ledger_bridge'):self.ledger_bridge.sync_profile()
        if self.selection_context:self.session.state['selection_context']=self.selection_context
        self.session.state['workspace']=self.tabs.snapshot()
        docs = []
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, CodeEditor):
                line, col = w.position()
                docs.append((engine.rel(w.path, self.root), line, col))
            elif isinstance(w,(viewer_tabs.ImageViewerTab,viewer_tabs.CadViewerTab)):
                docs.append((engine.rel(w.path,self.root),1,1))
        cur = self.tabs.currentWidget()
        active = engine.rel(cur.path, self.root) if isinstance(cur, (CodeEditor,viewer_tabs.ImageViewerTab,viewer_tabs.CadViewerTab)) else None
        self.session.remember_documents(docs, active)
        state=self._home_dock_state if self._home_active else self.saveState(engine_layout_version())
        self.session.state['view_preferences']=dict(self.view_preferences)
        selected=self.nav.currentItem()
        if selected is not None and selected.data(0,Qt.UserRole+3):
            self.session.state['view_preferences']['selected_nav']=selected.data(0,Qt.UserRole+3)
        self.session.set_layout(geometry=encode_bytes(self.saveGeometry()),
                                dock_state=encode_bytes(state),
                                engineering_state=encode_bytes(self._engineering_dock_state) if self._engineering_dock_state is not None else None,
                                output_visible=self._home_output_visible if self._home_active else self.output_dock.isVisible(),
                                navigator_width=max(160, min(600, self.nav_dock.width())),
                                simulator_width=max(160, min(900, self.sim_dock.width())),
                                output_height=max(80, min(700, self.output_dock.height())),
                                self_tree_expanded=[it.data(0, Qt.UserRole + 3) for it in self._nav_items()
                                                    if it.data(0, Qt.UserRole + 2) in ('self', 'self_section')
                                                    and it.isExpanded()],
                                hardware_tree_expanded=[it.data(0, Qt.UserRole + 3) for it in self._nav_items()
                                                        if it.data(0, Qt.UserRole + 2) in ('nav_root','nav_device','nav_group','nav_workspace')
                                                        and it.isExpanded()])
        self.session.save()

    def reset_layout(self):
        """One command to get back to the factory layout if panels get lost."""
        self._close_start()
        self._engineering_dock_state=None
        self.set_view_preference(mode='engineering')
        self.a_focus.setChecked(False)
        self.restoreState(self.factory_state, engine_layout_version())
        self.session.reset_layout()
        self._apply_default_layout()
        bar=getattr(self,'type_bar',None)
        if bar is not None:bar.pane_owner=None;bar.align()  # HATCH DESK D1a: both panes back to the desk's own width
        self.clip._queue()
        if self.clip_overlay is not None and self.clip_overlay.isVisible():
            QTimer.singleShot(0, self.clip_overlay.place)
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, BrowseTab):
                w.set_dual(False)
        self.a_dual.setChecked(False)
        self.statusBar().showMessage('Window layout restored to the factory default', 5000)

    # ---------------------------------------------------------------- documents
    def toggle_word_wrap(self):
        ed = self.current_editor()
        if ed is not None:
            ed.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth if self.a_wrap.isChecked()
                               else QPlainTextEdit.LineWrapMode.NoWrap)

    def document_for(self, path):
        p = Path(path).resolve()
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, (CodeEditor, viewer_tabs.ImageViewerTab, viewer_tabs.CadViewerTab)) and w.path.resolve() == p:
                return w
        return None

    def show_office(self):return self.ledger_bridge.show_office()

    def show_slate(self):return self.ledger_bridge.show_slate()

    def show_files(self):
        from .rooms import show_files
        return show_files(self)

    def open_in_viewer(self, path=None, address=None, origin=None):
        """Open any file, anywhere, in the read-only universal viewer."""
        if path is None:
            chosen, _ = QFileDialog.getOpenFileName(self, 'Open in Universal Viewer', str(Path.home()), 'All files (*)')
            if not chosen:return None
            path = chosen
        path = Path(path)
        from .universal_viewer_qt import UniversalViewerTab
        for i in range(self.tabs.count()):
            current = self.tabs.widget(i)
            if isinstance(current, UniversalViewerTab) and current.root_path == path:
                self.tabs.setCurrentWidget(current);return current
        try:tab = UniversalViewerTab(self, path, address=address, origin=origin)
        except (OSError, ValueError) as exc:
            self.message('Viewer could not open file', str(exc), error=True);return None
        self._close_start()
        i = self.tabs.addTab(tab, self.nav_icon('config'), path.name)
        if i < 0:return None
        self.tabs.setTabToolTip(i, str(path) + ' · read-only');self.tabs.setCurrentIndex(i);self.update_document_info()
        recent = [p for p in getattr(self, '_viewer_recent', []) if p != str(path)];self._viewer_recent = [str(path)] + recent[:19]
        return tab

    def open_document(self, path, remember=True, viewer=True):
        path = Path(path)
        try:
            path=fileops.check_inside(self.root,path)
            if any(part.startswith('.') and part not in {'.gitignore'} for part in path.relative_to(self.root).parts):
                raise ValueError('Private application/session files are not available in the source workspace.')
        except (OSError,ValueError) as exc:
            self.message('Cannot open file',str(exc),error=True);return None
        if path.suffix.lower() in ('.step','.stp','.stl'):
            from .assembly_view import AssemblyTab
            path=fileops.check_inside(self.root,path)
            for i in range(self.tabs.count()):
                current=self.tabs.widget(i)
                if isinstance(current,AssemblyTab) and current.path==path:
                    self.tabs.setCurrentWidget(current);return current
            tab=AssemblyTab(self,source=path.relative_to(self.root).as_posix())
            if self.tabs.addTab(tab,path.name)<0:return None
            self.tabs.setCurrentWidget(tab);return tab
        existing = self.document_for(path)
        if existing is not None:
            self.tabs.setCurrentWidget(existing)
            return existing
        suffix = path.suffix.lower()
        if suffix in (viewer_tabs.IMAGE_FORMATS | viewer_tabs.CAD_FORMATS):
            try:
                path = fileops.check_inside(self.root, path)
                if not path.is_file():
                    raise viewer_data.ViewerError('Expected a file')
                tab = (viewer_tabs.ImageViewerTab(path) if suffix in viewer_tabs.IMAGE_FORMATS
                       else viewer_tabs.CadViewerTab(path, self.open_document))
                if isinstance(tab,viewer_tabs.CadViewerTab):tab.componentSelected.connect(lambda ref,uid:self.bind_component(ref,uid))
            except (OSError, ValueError, viewer_data.ViewerError) as exc:
                self.message('Viewer could not open file', str(exc), error=True)
                return None
            self._close_start()
            i = self.tabs.addTab(tab, self.nav_icon(hardware_nav.file_icon(path)), path.name)
            if i<0:return None
            self.tabs.setTabToolTip(i, engine.rel(path, self.root))
            self.tabs.setCurrentIndex(i)
            if remember:
                self.session.touch_recent(engine.rel(path, self.root))
            self.update_document_info()
            return tab
        if suffix not in {x.lower() for x in EDIT_EXT} and path.name not in {'Makefile','GNUmakefile'}:
            if viewer:return self.open_in_viewer(path)
            self.message('Unsupported file', '%s cannot be opened by an installed Workbench viewer.' % path.name)
            return None
        try:
            path = editable_file(path, self.root)
            text = path.read_text(encoding='utf-8')
        except (ValueError, OSError, UnicodeError) as e:
            self.message('Cannot open file', str(e), error=True)
            return None
        ed = CodeEditor(path, self.root)
        ed.setPlainText(text)
        ed.disk_sha256 = file_hash(path)
        ed.recovery_owned = False
        ed.external_changed = False
        ed.document().setModified(False)
        if fileops.is_read_only(self.root, path):
            ed.setReadOnly(True)
        ed.document().modificationChanged.connect(lambda _m, e=ed: self._retitle(e))
        ed.cursorPositionChanged.connect(self.update_document_info)
        self._close_start()
        i = self.tabs.addTab(ed, self.nav_icon(hardware_nav.file_icon(path)), ('[RO] ' if ed.isReadOnly() else '') + path.name)
        if i<0:return None
        self.tabs.setTabToolTip(i, engine.rel(path, self.root))
        self.tabs.setCurrentIndex(i)
        if remember:
            self.session.touch_recent(engine.rel(path, self.root))
        game = engine.game_for(path, self.root)
        if game:
            self.session.set_last_game(game)
        self.a_wrap.setChecked(ed.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth)
        relative=engine.rel(path,self.root)
        context='arcos' if relative.startswith('software/arcos/') else 'arcade' if relative.startswith('software/struthio/') else engine.context_target(path,self.root) or 'workbench'
        self.clip_dock.set_context(path.name,context)
        self.update_document_info()
        activity.record(self.root,'GUI','files.open','OPENED',relative,source_generation=ed.disk_sha256)
        return ed

    def _retitle(self, ed):
        i = self.tabs.indexOf(ed)
        if i >= 0:
            self.tabs.setTabText(i, ('! ' if getattr(ed, 'external_changed', False) else '') + ('● ' if ed.document().isModified() else '')
                                 + ('[RO] ' if ed.isReadOnly() else '') + ed.path.name)
        self.update_document_info()

    def open_clip(self):
        self.clip.presence.dismiss()
        self._close_start()
        self.sim_dock.show()
        first = self.clip_overlay is None
        if first:
            self.clip_overlay = ClipOverlay(self, self.clip, self.clip_file)
            self.clip_overlay.busy_changed.connect(self.clip_dock.set_busy)
        self.clip_overlay.toggle()
        if first:
            self.clip_overlay.greet()

    def _submit_clip_from_dock(self, message):
        """Send through existing Gemini/onboarding logic; never grant new agent powers."""
        if message.startswith('/'):
            tab=self.show_clip_workspace();tab.input.setText(message);tab.send();return
        if self.clip_overlay is None or not self.clip_overlay.isVisible():
            self.open_clip()
        if self.clip_overlay is None or self.clip_overlay.busy:
            self.statusBar().showMessage('Graphite is processing a previous request', 4000)
            return
        self.clip_overlay.input.setText(message)
        self.clip_overlay.send()

    def _on_system_frame(self, row):
        """One recorded frame updates both instruments and central image preview."""
        self.instruments.snapshot(row)
        if isinstance(row, dict):
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if isinstance(tab, PreviewTab) and tab.project == self.sim_trace.project:
                    tab.set_scenario_divergent(self.sim_trace.scenario_divergent)
                    if not self.sim_trace.scenario_divergent:
                        tab.set_sim_frame(row['frame'])

    def open_engineering_trace(self):
        """Optional detailed trace is an ordinary center document tab."""
        i = self.tabs.indexOf(self.sim_trace)
        if i >= 0:
            self.tabs.setCurrentIndex(i)
            return self.sim_trace
        self._close_start()
        self.sim_trace.setParent(self.tabs)
        self.tabs.addTab(self.sim_trace, 'Engineering Trace · HOST_SIM')
        self.tabs.setCurrentWidget(self.sim_trace)
        self.sim_trace.show()
        return self.sim_trace

    def clip_file(self):
        ed = self.current_editor()
        if ed is None:
            return None, None
        try:
            name = ed.path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            name = ed.path.name
        return name, ed.toPlainText()

    def current_editor(self):
        if self.split_editor is not None and self.split_editor.hasFocus():
            return self.split_editor
        w = self.tabs.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def _ed(self, name):
        ed = self.current_editor() or (QApplication.focusWidget() if isinstance(
            QApplication.focusWidget(), (QLineEdit, QPlainTextEdit)) else None)
        if ed is not None and hasattr(ed, name):
            getattr(ed, name)()

    def save_document(self, ed=None):
        current = self.tabs.currentWidget()
        if not ed and hasattr(current, "save_concern_note"):
            return current.save_concern_note()
        if not ed and hasattr(current, "can_close_pdf"):
            return current.save_note()
        ed = ed or self.current_editor()
        if ed is not None and ed is self.split_editor:
            ed = self.document_for(ed.path)
        if ed is None:
            return True
        if ed.isReadOnly():
            self.message('Read-only', '%s is recorded evidence and cannot be changed here.' % ed.path.name)
            return False
        observed_sha256 = file_hash(ed.path)
        if observed_sha256 != getattr(ed, 'disk_sha256', None):
            choice = QMessageBox.warning(self, 'File changed on disk',
                'Another tool changed or removed this file. Reload discards this buffer; Save overwrites disk with this buffer. Cancel keeps both untouched.',
                QMessageBox.Discard | QMessageBox.Save | QMessageBox.Cancel, QMessageBox.Cancel)
            if choice == QMessageBox.Cancel:return False
            if choice == QMessageBox.Discard:
                try:
                    ed.setPlainText(ed.path.read_text(encoding='utf-8'))
                    ed.disk_sha256 = file_hash(ed.path)
                    ed.external_changed = False
                    ed.document().setModified(False)
                    self.recovery.remove(engine.rel(ed.path,self.root))
                    self._retitle(ed)
                    return True
                except (OSError,UnicodeError) as exc:
                    self.message('Reload failed',str(exc),error=True);return False
        try:
            editable_file(ed.path, self.root)
            # Share the promotion transaction with agents; a candidate cannot
            # silently race a human save between the version check and replace.
            kernel=engine.engineering(self.root)
            from . import file_delivery
            receipt_path=None
            with kernel.db() as db:
                db.execute('BEGIN IMMEDIATE')
                if file_hash(ed.path) != observed_sha256:
                    raise ValueError('Source changed during save review. Review the new disk version and save again.')
                import hashlib
                after=hashlib.sha256(ed.toPlainText().encode('utf-8')).hexdigest()
                receipt,receipt_path=file_delivery.prepare(kernel,ed.path,observed_sha256,after)
                fd, tmp = tempfile.mkstemp(prefix='.arc1-edit-', dir=ed.path.parent)
                try:
                    with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
                        os.chmod(tmp,ed.path.stat().st_mode & 0o777)
                        f.write(ed.toPlainText())
                    os.replace(tmp, ed.path)
                    activity.append(db,file_delivery.event(receipt))
                finally:
                    if os.path.exists(tmp):
                        os.unlink(tmp)
            if receipt_path:receipt_path.unlink(missing_ok=True)
        except (OSError, ValueError, sqlite3.Error) as e:
            pending=locals().get('receipt_path')
            detail=str(e)+('\nThe file may have reached disk. Graphite awareness shows the pending save; use journal recovery to reconcile it.' if pending and pending.exists() else '')
            self.message('Save needs attention', detail, error=True)
            return False
        ed.disk_sha256 = file_hash(ed.path)
        ed.external_changed = False
        ed.document().setModified(False)
        self.recovery.remove(engine.rel(ed.path,self.root))
        self._retitle(ed)
        self.statusBar().showMessage('Saved ' + engine.rel(ed.path, self.root), 4000)
        return True

    def save_all(self):
        ok = True
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if hasattr(w, "save_concern_note") and w.is_dirty():
                ok = w.save_concern_note() and ok
            if hasattr(w, "can_close_pdf") and w.is_dirty():
                ok = w.save_note() and ok
            if isinstance(w, CodeEditor) and w.document().isModified():
                ok = self.save_document(w) and ok
        return ok

    def close_tab(self, index):
        w = self.tabs.widget(index)
        if w is None:
            return True
        if hasattr(w, "can_close_concern") and not w.can_close_concern():
            return False
        if hasattr(w, "can_close_pdf") and not w.can_close_pdf():
            return False
        if isinstance(w, CodeEditor) and w.document().isModified():
            ans = self.ask_save(w.path.name)
            if ans == 'cancel':
                return False
            if ans == 'save' and not self.save_document(w):
                return False
            if ans == 'discard':
                self.recovery.put(engine.rel(w.path,self.root),w.toPlainText(),w.disk_sha256)
                w.recovery_owned=False
        if isinstance(w, ProjectSearchTab) and not w.shutdown():return False
        if hasattr(w, 'shutdown_engineering'):w.shutdown_engineering()
        if isinstance(w, CodeEditor):
            if getattr(w,'recovery_owned',False):self.recovery.remove(engine.rel(w.path,self.root))
            if self.split_editor is not None and self.split_editor.document() is w.document():
                self._close_split()
        self.tabs.removeTab(index)
        if w is self.sim_trace:
            # Never destroy the session controller when its detail view closes.
            w.setParent(self)
            w.hide()
        else:
            w.deleteLater()
        if self.tabs.count() == 0 and not self.tabs.replacing:
            self.show_start()
        return True

    def show_start(self):
        from .project_context import detached
        if detached(self.root):
            from .empty_workspace_qt import show_home
            return show_home(self)
        # Home overlays the same workspace; it never releases a dirty Preview.
        # UI-04 (AGENT-01, the owner's words): with nothing being worked on the centre is the Finder, project attached or not;
        # the earlier StartPage remains for a host without the shell.
        if self.home_page is None:
            if hasattr(self,'shell2'):
                from .finder_qt import FinderPage
                self.home_page=FinderPage(self)
            else:self.home_page=StartPage(self)
            self.central_stack.addWidget(self.home_page)
        if hasattr(self,'shell2'):self.finder=self.home_page
        if not self._home_active:
            self._home_dock_state=self.saveState(engine_layout_version())
            self._home_output_visible=self.output_dock.isVisible()
        self._home_active=True
        # UI01 (DESKTOP-01): Home keeps the right column; only the output and cart panels fold away.
        self.output_dock.hide();self.cart_dock.hide()
        self.central_stack.setCurrentWidget(self.home_page)
        self.context_bar.hide();self.doc_info.hide()
        self.workspace_status.setVisible(hasattr(self,'arc_inspector'))
        self.clip.hide()  # Stacy hosts Home in the artwork; her companion returns in workspaces
        if hasattr(self.home_page,'refresh'):self.home_page.refresh()
        self.set_view_preference(last_surface='home')
        self.setWindowTitle('Home — Graphite')
        from .arc_desktop import refresh
        refresh(self)
        return self.home_page

    def set_view_preference(self, **values):
        if hasattr(self,'ledger_bridge'):self.ledger_bridge.sync_profile()
        from sdk.cli.arc1cli.workspace_view import clean
        self.view_preferences=clean(dict(self.view_preferences,**values))
        self.session.state['view_preferences']=dict(self.view_preferences)
        self.session.save()

    def _workspace_tab_changed(self, index):
        if self._home_active:self._close_start()
        if not self._initializing:self.set_view_preference(last_surface='workspace')
        self.update_document_info()
        tab=self.tabs.widget(index) if index>=0 else None
        if not self._initializing and hasattr(self,'object_glass') and hasattr(tab,'path'):
            try:self.select_object({'kind':'file','target':Path(tab.path).resolve().relative_to(self.root).as_posix()})
            except (ValueError,TypeError):pass
        if not self._initializing and hasattr(self,'ledger_bridge'):
            activity.record(self.root,'GUI','ledger.view','FOCUSED',self.tabs.tabText(index) if index>=0 else 'No active document')

    def resume_workspace(self):
        self._close_start()
        if self.tabs.count()==0:
            from .project_context import detached
            if detached(self.root):self.show_files()  # no project: start where files open
            else:self.show_assembly()
        changed=[]
        # A disk edit marks the actual buffer stale; never reload over it.
        for editor in self.findChildren(CodeEditor):
            if hasattr(editor,'disk_sha256') and file_hash(editor.path)!=editor.disk_sha256:
                editor.external_changed=True;self._retitle(editor);changed.append(editor.path.name)
        if changed:
            self.statusBar().showMessage('Source changed on disk · review before saving: '+', '.join(changed),12000)
        else:
            self.statusBar().showMessage('Workspace restored · source files checked',4000)
        current=self.tabs.currentWidget()
        if current is not None:current.setFocus()
        self.save_session()

    def open_source_workspace(self):
        """Return to an open buffer, or the current ARC-OS entry point."""
        for index in range(self.tabs.count() - 1, -1, -1):
            editor = self.tabs.widget(index)
            if isinstance(editor, CodeEditor):
                self._close_start()
                self.tabs.setCurrentWidget(editor)
                return editor
        return self.open_document(self.root / 'software/arcos/src/launcher.c')

    def explore_workspace(self):
        self._close_start()
        area=self._workspace_areas.get('console_hardware')
        if area is not None:
            area.setExpanded(True);self.nav.setCurrentItem(area);self.nav.scrollToItem(area)
        self.show_assembly()

    def learn_workspace(self):
        self._close_start()
        return self.show_orange_book()

    def set_workspace_layout(self, mode, persist=True, capture=True):
        if mode not in ('engineering','focus'):raise ValueError('Unknown workspace layout')
        if persist:self._close_start()
        if persist and hasattr(self,'ledger_bridge'):self.ledger_bridge.sync_profile()
        old=self.view_preferences['mode']
        # Commit the explicit preference before mutating visible docks. Otherwise
        # sync_profile can reapply the old disk mode during this transition.
        if persist:self.set_view_preference(mode=mode,last_surface='workspace')
        if mode=='focus':
            if capture and old!='focus':
                self._engineering_dock_state=self.saveState(engine_layout_version())
            self.sim_dock.hide();self.output_dock.hide();self.cart_dock.hide();self.clip.arrive()
        else:
            if old=='focus' and self._engineering_dock_state is not None:
                self.restoreState(self._engineering_dock_state,engine_layout_version())
            self.nav_dock.show();self.sim_dock.show()
        self.a_focus.setChecked(mode=='focus')
        self.view_preferences['mode']=mode
        if persist:
            self.save_session()
            current=self.tabs.currentWidget()
            if current is not None:current.setFocus()
        if hasattr(self,'clip'):self.clip._queue()

    def show_manual(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, ManualTab):
                tab.refresh()
                self.tabs.setCurrentIndex(i)
                tab.query.setFocus()
                return tab
        self._close_start()
        tab = ManualTab(self)
        self.tabs.addTab(tab, tab.title())
        self.tabs.setCurrentWidget(tab)
        tab.query.setFocus()
        return tab

    def _close_start(self):
        if not self._home_active:return
        self._home_active=False
        self.central_stack.setCurrentWidget(self.workspace_split)
        if self._home_dock_state is not None:
            # The saved state brings the folded panels back; a column width the owner changed while on Home is kept.
            widths=[self.nav_dock.width(),self.sim_dock.width()] if self.nav_dock.isVisible() and self.sim_dock.isVisible() else None
            self.restoreState(self._home_dock_state,engine_layout_version())
            if widths:self.resizeDocks([self.nav_dock,self.sim_dock],widths,Qt.Horizontal)
        self.context_bar.show();self.doc_info.show();self.workspace_status.show()
        self.set_view_preference(last_surface='workspace')
        if hasattr(self,'clip'):self.clip.arrive()
        self.update_document_info()

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

    def show_readiness(self):
        self._refresh_readiness()
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, ReadinessTab):
                tab.refresh()
                self.tabs.setCurrentIndex(i)
                return tab
        self._close_start()
        tab = ReadinessTab(self)
        self.tabs.addTab(tab, tab.title())
        self.tabs.setCurrentWidget(tab)
        return tab

    def show_tools(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, ToolInventoryTab):
                tab.refresh()
                self.tabs.setCurrentIndex(i)
                return tab
        self._close_start()
        tab = ToolInventoryTab()
        self.tabs.addTab(tab, tab.title())
        self.tabs.setCurrentWidget(tab)
        return tab

    def show_nor(self):
        if self.project_required('NOR Flash'):return None
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, NorFlashTab):
                self.tabs.setCurrentIndex(i)
                return tab
        self._close_start()
        try:
            tab = NorFlashTab(self)
        except (nor_staging.StageError, OSError) as exc:
            self.message('NOR layout unavailable', str(exc), error=True)
            return None
        self.tabs.addTab(tab, tab.title())
        self.tabs.setCurrentWidget(tab)
        return tab

    def show_board(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, BoardViewerTab):
                self.tabs.setCurrentIndex(i)
                return tab
        self._close_start()
        tab = BoardViewerTab(self)
        self.tabs.addTab(tab, tab.title())
        self.tabs.setCurrentWidget(tab)
        return tab

    def engine_hardware_review(self):
        return engine.hardware_review_snapshot(self.root)

    def show_hardware_review(self):
        from .project_context import detached
        if detached(self.root):
            from .empty_workspace_qt import show
            return show(self,'Hardware Review')
        for i in range(self.tabs.count()):
            tab=self.tabs.widget(i)
            if isinstance(tab,hardware_overview.HardwareReviewTab):
                tab.refresh();self.tabs.setCurrentIndex(i);return tab
        tab=hardware_overview.HardwareReviewTab(self)
        self.tabs.addTab(tab,tab.title());self.tabs.setCurrentWidget(tab);return tab

    def show_native_board(self):
        from .project_context import detached
        if detached(self.root):
            from .empty_workspace_qt import show
            return show(self,'Native Board')
        path = self.root / 'hardware/compact-arc1/R10_WORK/cad/ARC1_R10.kicad_pcb'
        tab=self.open_document(path)
        if tab is not None and not getattr(tab,'audit_added',False):
            button=QPushButton('Source audit');button.clicked.connect(self.show_hardware_review)
            tab.layout().itemAt(0).layout().addWidget(button);tab.audit_added=True
        return tab

    def project_required(self, requested):
        """In a bare program, show the empty-workspace explanation instead of a project action."""
        from .project_context import detached
        if not detached(self.root):return False
        from .empty_workspace_qt import show
        show(self,requested);return True

    def show_schematics(self):
        if self.project_required('KiCad Schematics'):return None
        return self.browse(self.root / 'hardware/compact-arc1/R10_WORK/cad')

    def toggle_dual(self):
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, BrowseTab):
                w.set_dual(self.a_dual.isChecked())
        self.update_document_info()

    def update_document_info(self):
        w = self.tabs.currentWidget()
        if hasattr(self, 'a_wrap'):
            self.a_wrap.setEnabled(isinstance(w, CodeEditor))
            if isinstance(w, CodeEditor):
                self.a_wrap.blockSignals(True)
                self.a_wrap.setChecked(w.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth)
                self.a_wrap.blockSignals(False)
        inferred = engine.context_target(getattr(w, 'path', None), self.root)
        target = engine.TARGETS[inferred or self.target()]
        short = target['short']
        if isinstance(w, CodeEditor) and engine.game_for(w.path, self.root):
            short = engine.TARGETS['game']['short']
        elif isinstance(w, CodeEditor) and engine.arcade_for(w.path, self.root):
            short = engine.TARGETS['arcade']['short']
        if isinstance(w, CodeEditor):
            game = engine.game_for(w.path, self.root)
            line, col = w.position()
            where = ('Host game %s' % Path(game).name) if game else (
                'STRUTHIO browser source' if engine.arcade_for(w.path, self.root) else target['short'])
            from .development import WORK
            if w.path.resolve().is_relative_to((self.root/WORK/'src').resolve()):
                where='Diagnostic candidate · host checks';short='Development'
            from .hardware_import import P11
            if w.path.resolve().is_relative_to((self.root/P11/'port').resolve()):
                where='STRUTHIO C bootstrap · host checks'
            elif w.path.resolve().is_relative_to((self.root/P11/'reference').resolve()):
                where='STRUTHIO original browser reference'
            text = '%s · %s%s      Ln %d, Col %d' % (
                engine.language_for(w.path), where, ' · read-only evidence' if w.isReadOnly() else '', line, col)
            lang = engine.language_for(w.path).split(' ')[0]
            self.setWindowTitle('%s%s — Graphite' % ('● ' if w.document().isModified() else '', w.path.name))
        elif w is not None and hasattr(w, 'info'):
            text = w.info()
            lang = '—'
            self.setWindowTitle('%s — Graphite' % w.title())
        else:
            text, lang = '', '—'
            self.setWindowTitle('Graphite')
        self.doc_info.setText(text)
        from .rooms import status_text
        self.context_label.setText(status_text(self, w, short, lang))
        if hasattr(self,'context_path'):
            path=engine.rel(w.path,self.root) if isinstance(w,CodeEditor) else w.title() if hasattr(w,'title') else ''
            self.context_path.setText(path);self.context_path.setToolTip(path)
            for button in self.source_actions:button.setVisible(isinstance(w,CodeEditor))
        if self._home_active:self.setWindowTitle('Home — Graphite')
        from .arc_desktop import refresh
        refresh(self)

    # ---------------------------------------------------------------- navigator
    def refresh_navigator(self):
        """Functional device hierarchy; never dump root filesystem into navigator."""
        self.concern.remember()
        self._accepted_nav_item = None
        expanded_ids=set(self.session.layout.get('hardware_tree_expanded', ['root']))
        for item in self._nav_items():
            if item.isExpanded():
                node_id=item.data(0,Qt.UserRole+3)
                if node_id:expanded_ids.add(node_id)
        self.nav.clear()
        from .project_context import detached
        if detached(self.root):
            # 4.0: with no project attached there is no project tree. The Library and your Concern catalog are the navigator.
            self._nav_devices={};self._workspace_areas={}
            placeholder=QTreeWidgetItem(['Workspace']);placeholder.setData(0,Qt.UserRole,str(self.root))
            placeholder.setData(0,Qt.UserRole+2,'nav_root');placeholder.setData(0,Qt.UserRole+3,'root')
            self.nav.addTopLevelItem(placeholder)  # the Concern rebuild takes this slot
            self.concern.rebuild()
            if hasattr(self, 'shell2'):
                from .shell2 import build_library
                build_library(self)
            return
        top=QTreeWidgetItem(['ARC-1 Console'])
        top.setData(0,Qt.UserRole,str(self.root))
        top.setData(0,Qt.UserRole+2,'nav_root')
        top.setData(0,Qt.UserRole+3,'root')
        top.setIcon(0,self.nav_icon('console'))
        self.nav.addTopLevelItem(top)
        self._nav_devices={device.id:device for device in hardware_nav.devices(self.root)}
        self._workspace_areas={};workspace_parents={}
        # A project's areas come with the project; the program's own file is the fallback for the old single-tree layout.
        area_base=self.root if (Path(self.root)/'project/workspaces.json').is_file() else locations.program(self.root)
        workspace_file=area_base/'project/workspaces.json'
        if workspace_file.is_file():
            from .record_io import load
            for area in load(area_base,'project/workspaces.json')['areas']:
                titles={'struthio':'STRUTHIO','platform':'ARC-OS / Firmware','console_hardware':'Console hardware','orange_book':'Orange Book','ai_clip':'AI API / Graphite'}
                node=QTreeWidgetItem([titles.get(area['id'],area['title'])]);node.setData(0,Qt.UserRole+2,'nav_workspace')
                node.setData(0,Qt.UserRole+3,'workspace:'+area['id']);node.setData(0,Qt.UserRole+4,area['id'])
                node.setToolTip(0,area['purpose']);node.setIcon(0,self.nav_icon('database-rom' if area['id']=='database_rom' else area['icon']))
                top.addChild(node);self._workspace_areas[area['id']]=node
                if 'workspace:'+area['id'] in expanded_ids:node.setExpanded(True)
                for ident in area['device_ids']:workspace_parents[ident]=node
        branches={}
        for device,parent_id in hardware_nav.navigation(self.root):
            branch=QTreeWidgetItem([device.title])
            branch.setData(0,Qt.UserRole+2,'nav_device')
            branch.setData(0,Qt.UserRole+3,'device:'+device.id)
            branch.setData(0,Qt.UserRole+4,device.id)
            branch.setIcon(0,self.nav_icon(device.icon))
            branch.setToolTip(0,device.role+' · Click for hardware overview; arrow expands engineering categories')
            branches[device.id]=branch
            if parent_id:
                parent=branches[parent_id]
                index=sum(parent.child(i).data(0,Qt.UserRole+2)=='nav_device' for i in range(parent.childCount()))
                parent.insertChild(index,branch)
            else:workspace_parents.get(device.id,top).addChild(branch)
            for section in device.groups:
                files=hardware_nav.group_files(self.root,device,section.title)
                if not files:continue
                group=QTreeWidgetItem([f'{section.title}  ({len(files)})'])
                group.setData(0,Qt.UserRole+2,'nav_group')
                group.setData(0,Qt.UserRole+3,'group:'+device.id+':'+section.title)
                group.setData(0,Qt.UserRole+4,device.id)
                group.setData(0,Qt.UserRole+5,section.title)
                group.setIcon(0,self.nav_icon(section.icon))
                group.setToolTip(0,'Click to browse in the center. Expand arrow for individual documents.')
                group.addChild(QTreeWidgetItem(['']))
                group.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
                branch.addChild(group)
                if group.data(0,Qt.UserRole+3) in expanded_ids:
                    self._populate_nav_group(group)
                    group.setExpanded(True)
            if branch.data(0,Qt.UserRole+3) in expanded_ids:
                branch.setExpanded(True)
        active=self._workspace_areas.get('ledger_active',top)
        for label,name,method in [('ARC Concern / Genesis','source-fact','show_genesis'),('Brain Link','brain-link','show_brain_link'),('Engineering Register','spreadsheet','show_engineering_register'),('UX Asset Library','asset-library','show_asset_gallery')]:
            shortcut=QTreeWidgetItem([label]);shortcut.setIcon(0,self.nav_icon(name))
            shortcut.setData(0,Qt.UserRole+2,'nav_action');shortcut.setData(0,Qt.UserRole+4,method)
            shortcut.setToolTip(0,'Open '+label+' in the central workspace');active.addChild(shortcut)
        top.setExpanded(True)

        from .arc_desktop import organize_navigator
        organize_navigator(self)
        if hasattr(self,'ledger_bridge'):
            from .control_qt import add_navigation
            add_navigation(self)
        self.concern.rebuild()
        if hasattr(self, 'shell2'):
            from .shell2 import build_library
            build_library(self)

    def _populate_nav_group(self,item):
        if item.data(0,Qt.UserRole+6):return
        device=self._nav_devices[item.data(0,Qt.UserRole+4)]
        category=item.data(0,Qt.UserRole+5)
        files=hardware_nav.group_files(self.root,device,category)
        item.takeChildren()
        from .hardware_browser import tree_paths
        for path,relative in tree_paths(self.root,device,category):
            parent=item
            for folder_name in relative.parts[:-1]:
                existing=next((parent.child(i) for i in range(parent.childCount())
                               if parent.child(i).data(0,Qt.UserRole+2)=='nav_folder'
                               and parent.child(i).text(0)==folder_name),None)
                if existing is None:
                    existing=QTreeWidgetItem([folder_name]);existing.setData(0,Qt.UserRole+2,'nav_folder')
                    existing.setIcon(0,self.nav_icon('folder'));parent.addChild(existing)
                parent=existing
            child=QTreeWidgetItem([path.name]);child.setData(0,Qt.UserRole,str(path))
            child.setData(0,Qt.UserRole+2,'nav_file');child.setIcon(0,self.nav_icon(hardware_nav.file_icon(path)))
            child.setToolTip(0,str(path.relative_to(self.root)));parent.addChild(child)
        item.setData(0,Qt.UserRole+6,True)

    def show_device(self,device_id):
        device=self._nav_devices[device_id]
        self.instruments.set_hardware_context(device.title)
        if hasattr(self.clip_dock,'set_context'):self.clip_dock.set_context(device.title,device_id)
        if device_id=='case':return self.show_assembly(True)
        if device_id=='viability':return self.show_hardware_proof()
        if device_id=='development':return self.show_development()
        if device_id=='ledger':return self.show_hardware_ledger()
        if device_id=='arcade':return self.show_native_game()
        if device_id=='arcos':return self.show_arcos()
        if device_id in engine.TARGETS:self.set_target(device_id)
        if device_id=='pcb':
            from .assembly_view import AssemblyTab
            current=self.tabs.currentWidget()
            if isinstance(current,AssemblyTab) and current.canvas.mesh is not None and not current.case:
                current.canvas.selected=True;current.canvas.update();return current
            return self.show_native_board()
        if device_id=='nor':return self.show_nor()
        for i in range(self.tabs.count()):
            tab=self.tabs.widget(i)
            if isinstance(tab,hardware_overview.HardwareOverviewTab) and tab.device.id==device_id:
                self.tabs.setCurrentIndex(i);return tab
        self._close_start()
        tab=hardware_overview.HardwareOverviewTab(self,device)
        i=self.tabs.addTab(tab,self.nav_icon(device.icon),device.title)
        self.tabs.setCurrentIndex(i)
        return tab

    def show_device_group(self,device_id,group_title):
        device=self._nav_devices[device_id]
        group=next(g for g in device.groups if g.title==group_title)
        if device_id in engine.TARGETS:self.set_target(device_id)
        if device_id=='pcb' and group_title=='PCB layout':return self.show_native_board()
        self.instruments.set_hardware_context(device.title)
        for i in range(self.tabs.count()):
            tab=self.tabs.widget(i)
            if isinstance(tab,hardware_overview.HardwareGroupTab) and tab.device.id==device_id and tab.group.title==group_title:
                self.tabs.setCurrentIndex(i);return tab
        self._close_start()
        tab=hardware_overview.HardwareGroupTab(self,device,group)
        self.tabs.addTab(tab,self.nav_icon(group.icon),tab.title())
        self.tabs.setCurrentWidget(tab);return tab

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

    def _add_nav_special(self, parent, label, path, kind, tip):
        path = Path(path)
        if not path.exists():
            return None
        child = QTreeWidgetItem([label])
        child.setData(0, Qt.UserRole, str(path))
        child.setData(0, Qt.UserRole + 2, kind)
        child.setToolTip(0, tip)
        child.setIcon(0, self.style().standardIcon(QStyle.SP_FileIcon))
        parent.addChild(child)
        return child

    def _fill_nav_item(self,item):
        if item.data(0,Qt.UserRole+2)=='nav_group':
            self._populate_nav_group(item)

    def _nav_clicked(self,item,_col=0):
        self._close_start()
        previous=getattr(self,'_accepted_nav_item',None)
        self.tabs.last_open_cancelled=False
        kind=item.data(0,Qt.UserRole+2)
        if kind=='nav_catalog':
            self.show_concern(item.data(0,Qt.UserRole+4))
        elif kind=='ledger_settings':
            self.ledger_bridge.show_settings(item.data(0,Qt.UserRole+4))
        elif kind=='ledger_control':
            self.ledger_bridge.navigation()[item.data(0,Qt.UserRole+4)]()
        elif kind=='nav_live':
            if item.data(0,Qt.UserRole+4):
                from .shell2 import open_destination
                open_destination(self,item.data(0,Qt.UserRole+4))
        elif kind=='nav_device':
            self.show_device(item.data(0,Qt.UserRole+4))
        elif kind=='nav_workspace':
            ident=item.data(0,Qt.UserRole+4)
            methods={'database_rom':self.show_database_rom,'ledger_active':self.show_project_desk,
                     'platform':self.show_arcos,'ai_clip':self.show_clip_workspace,
                     'orange_book':self.show_orange_book,'console_hardware':self.show_assembly,
                     'struthio':self.show_native_game}
            methods[ident]()
        elif kind=='nav_action':
            getattr(self,item.data(0,Qt.UserRole+4))()
        elif kind=='nav_group':
            self.show_device_group(item.data(0,Qt.UserRole+4),item.data(0,Qt.UserRole+5))
        elif kind=='nav_file':
            p=item.data(0,Qt.UserRole)
            if p:self.open_document(Path(p))
        elif kind=='nav_root':self.show_assembly()
        elif kind=='nav_concern':self.show_start()
        elif kind=='nav_legal':self.show_genesis()
        if self.tabs.last_open_cancelled:
            self.nav.setCurrentItem(previous)
            if previous and previous.data(0,Qt.UserRole+4) in self._nav_devices:
                ident=previous.data(0,Qt.UserRole+4)
                self.clip_dock.set_context(self._nav_devices[ident].title,ident)
        else:self._accepted_nav_item=item
        # nav_folder selection does not destroy current editor or launch a browser.

    def _nav_activated(self,item,_col=0):
        self._nav_clicked(item,_col)

    def show_assembly(self,case=False):
        from .project_context import detached
        if detached(self.root):
            from .empty_workspace_qt import show
            return show(self,'Case geometry' if case else '')
        from .assembly_view import AssemblyTab
        for i in range(self.tabs.count()):
            tab=self.tabs.widget(i)
            if isinstance(tab,AssemblyTab) and tab.case==case and tab.path is None:
                self.tabs.setCurrentWidget(tab);return tab
        tab=AssemblyTab(self,case);self.tabs.addTab(tab,tab.title());self.tabs.setCurrentWidget(tab);return tab

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
                                           'Workbench views (*.kicad_sch *.kicad_pcb *.png *.jpg *.jpeg *.webp '
                                           '*.c *.h *.s *.S *.cpp *.hpp *.ld *.py *.md *.json *.txt '
                                           '*.sprite *.replay *.csv *.sv *.v *.vhd *.lpf *.xml);;All files (*)')
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

    def select_object(self,selector,principal=None,origin=None):
        if hasattr(self,'object_glass'):
            from .engineering_kernel import operator
            self.object_glass.origin=origin
            self.object_glass.select(selector,principal=principal or operator(),origin=origin)

    def show_object_glass(self):
        from .object_context_qt import View
        for i in range(self.tabs.count()):
            tab=self.tabs.widget(i)
            if isinstance(tab,View):self._close_start();self.tabs.setCurrentWidget(tab);return tab
        tab=View(self);self._close_start()
        if self.tabs.addTab(tab,tab.title())<0:return None
        self.tabs.setCurrentWidget(tab);return tab

    def command_palette(self, query=''):
        from .workspace_qt import WorkspacePalette
        dialog=WorkspacePalette(self)
        if isinstance(query,str) and query.strip():dialog.query.setText(query.strip())  # QAction passes a bool
        dialog.exec()

    def bind_component(self,reference,expected_uuid=None,native_revision=None):
        args={'component':reference}
        if expected_uuid:args['expected_uuid']=expected_uuid
        if native_revision:args['expected_native_revision']=native_revision
        from .engineering_kernel import operator
        result=engine.engineering(self.root).dispatch('workspace.select',args,operator())
        if not result['ok']:self.statusBar().showMessage(result['error']['message'],8000);return None
        self.apply_selection(result['result']);return result['result']

    def apply_selection(self,data):
        self.selection_data=data
        if data.get('state')=='CURRENT_INPUTS' and data.get('selection'):
            selected=data['selection'];self.select_object({'kind':selected['kind'],'target':selected['reference']})
        self.selection_inspector.setVisible(not hasattr(self,'arc_inspector'))
        if data.get('selection'):
            self.selection_context=data['selection']
            self.session.state['selection_context']=self.selection_context
        self.selection_inspector.loaded(data)
        if self.selection_context:
            reference=self.selection_context['reference']
            self.instruments.set_hardware_context(reference+' · '+data['state'])
            self.clip_dock.set_context(reference+' · native context','native:'+reference)
        if data.get('state')!='CURRENT_INPUTS':
            from .brain_link_tab import BrainLinkTab
            for i in range(self.tabs.count()):
                tab=self.tabs.widget(i)
                if isinstance(tab,BrainLinkTab):
                    tab.scene.clear();tab.pins.clear();tab.sources.clear();tab.records.clear();tab.data=None
                    tab.status.setText(data.get('state','STALE')+' · refresh before cross-probing')
        from .arc_desktop import refresh
        refresh(self)

    def refresh_selection(self,checked=False,refresh=True):
        if not self.selection_context:return None
        from .engineering_kernel import operator
        result=engine.engineering(self.root).dispatch('workspace.resolve',{'selection':self.selection_context,'refresh':bool(refresh)},operator())
        if result['ok']:self.apply_selection(result['result']);return result['result']
        self.apply_selection({'state':'UNAVAILABLE','selection':self.selection_context,'message':result['error']['message']})
        return None

    def open_selection_view(self,kind):
        data=self.refresh_selection(refresh=False)
        if not data or data['state']!='CURRENT_INPUTS':
            self.statusBar().showMessage('Selection changed · refresh a matching native identity first',9000);return None
        if kind in ('CAD','Source'):
            desired='native_schematic' if kind=='CAD' else 'software_intent'
            rows=[row for row in data['source_links'] if row['kind']==desired and row['available']]
            if not rows:rows=[row for row in data['source_links'] if row['available']]
            if not rows:return None
            row=rows[0];path=self.root/row['path']
            if file_hash(path)!=row['sha256']:raise ValueError('Associated source changed; refresh selection')
            current=self.tabs.currentWidget()
            if current is not None and not self.tabs.pin(current):return None
            tab=self.open_document(path)
            if hasattr(tab,'component_find'):
                tab.component_find.setCurrentText(self.selection_context['reference']);tab.locate_component()
            return tab
        if kind=='Knowledge':
            tab=self.show_vendor_vault();tab.find.setText(data['knowledge_query']);tab.search();return tab
        tab=self.show_engineering_register()
        rows=data.get('requirements',[])
        if rows:tab.focus_record(rows[0]['record_id'])
        else:tab.focus_record('R10:'+self.selection_context['reference'],'objects')
        return tab

    def open_search_result(self,row):
        kind=row['kind']
        if kind=='Concern item':
            self.show_concern(row['concern_id'])
        elif kind in ('component','net'):
            from .engineering_kernel import operator
            args={kind:row['reference'],'expected_native_revision':row['native_revision']}
            if row.get('native_uuid'):args['expected_uuid']=row['native_uuid']
            result=engine.engineering(self.root).dispatch('workspace.select',args,operator())
            if not result['ok'] or result['result'].get('state')!='CURRENT_INPUTS':raise ValueError('Search binding is stale; search again')
            self.apply_selection(result['result']);tab=self.show_brain_link()
            if kind=='component':QTimer.singleShot(0,lambda:tab.choose(row['reference']))
            else:self.statusBar().showMessage('Selected net '+row['reference']+' · use associated source and native membership',7000)
        elif kind=='file':
            path=fileops.check_inside(self.root,self.root/row['path'])
            if file_hash(path)!=row['sha256']:raise ValueError('Search file changed; search again')
            self.open_document(path)
        elif kind in ('command','job'):
            tab=self.show_engineering()
            if kind=='command':
                index=tab.tool.findText(row['tool'])
                if index<0:raise ValueError('Registered command is unavailable')
                tab.tool.setCurrentIndex(index);tab.status.setText('Command selected · no job submitted')
            else:
                tab.selected_job=row['job_id'];tab.refresh()
                for i in range(tab.jobs.topLevelItemCount()):
                    item=tab.jobs.topLevelItem(i)
                    if item.data(0,Qt.UserRole)==row['job_id']:tab.jobs.setCurrentItem(item);tab.select_job();break
        elif kind=='vendor':
            hit=row['hit'];tab=self.show_vendor_vault()
            tab.call('vendor.page',{'document_id':hit['document_id'],'page_index':hit['page_index'],'original':True},tab.show_page)
        elif kind=='record':
            tab=self.show_database_rom();hit=row['hit']
            tab.call('records.page',{k:hit[k] for k in ('record_id','volume_id','page_index')},tab.show_page)
        elif kind=='menu action':
            action=self.favorite_actions.get(row['action_key'])
            if action is None or not action.isEnabled():raise ValueError('Native action is unavailable')
            action.trigger()
        else:raise ValueError('Unsupported search result')

    def new_game_project(self):
        route,ok=QInputDialog.getItem(self,'New Game Project','SDK route:',['Native C · ARC-OS host','Classic ARC1 project'],0,False)
        if not ok:return
        if route.startswith('Native C'):self.show_native_project();return
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
        if op == 'run' and self.project_required('Run Current Game'):return
        if self.process.state() != QProcess.NotRunning:
            self.statusBar().showMessage('Wait for the current command to finish (Ctrl+Break stops it)', 5000)
            return
        active=self.active_path()
        current=self.tabs.currentWidget()
        from .console_tab import VirtualConsoleTab
        from .native_project_tab import NativeProjectTab
        if isinstance(current,VirtualConsoleTab):
            if op=='run':current.run()
            else:current.job('console.lifecycle' if op=='test' else 'console.build')
            return
        if isinstance(current,NativeProjectTab):
            if op=='run':current.boot()
            elif op=='build':current.build()
            else:current.status.setText('No project-specific test target is registered. Inspect build evidence or run the game.')
            return
        if active and active.is_relative_to(self.root/'examples'):
            relative=active.relative_to(self.root/'examples')
            if len(relative.parts)>1 and (self.root/'examples'/relative.parts[0]/'native.json').is_file():
                if not self.save_all() or not self.tabs.pin(current):return
                tab=self.show_native_project();tab.name.setText(relative.parts[0])
                if op=='run':tab.boot()
                elif op=='build':tab.build()
                else:tab.status.setText('No project-specific test target is registered. Inspect build evidence or run the game.')
                return
        if active and active.is_relative_to(self.root/'software/struthio'):
            tab=self.show_native_game()
            if op=='run':tab.run()
            else:tab.job('struthio.test' if op=='test' else 'struthio.build')
            return
        try:
            p = engine.plan(op, self.target(), self.active_path(), self.session.state.get('last_game'), self.root)
        except ValueError as e:
            self.message('Nothing to %s' % op, str(e), error=True)
            return
        if p.target == 'development':
            self.run_development(p.op)
            return
        if p.target == 'ledger':
            self.run_ledger(p.op)
            return
        if not self.save_all():
            return
        self._then = None
        if op == 'run':
            # Check the selected project before its host or browser preview.
            b = engine.plan('build', 'arcade' if p.target == 'arcade' else 'game',
                            self.active_path() if p.target == 'arcade' else None,
                            p.project, self.root)
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
        from .service_lifecycle import require_admission
        try:require_admission(self.ledger_bridge.kernel)
        except ValueError as exc:self.statusBar().showMessage(str(exc),6000);return
        from .project_context import detached
        if detached(self.root):
            self.statusBar().showMessage('PROJECT NOT ATTACHED · project execution is unavailable in the program-only build.',8000)
            activity.record(self.root,'GUI',p.label,'PROJECT_NOT_ATTACHED')
            return False
        if not self.execution_lock.acquire():
            self.after_build=None
            callback,self._job_callback=self._job_callback,None
            self.statusBar().showMessage('Another Workbench/agent command owns this project. Try again when it finishes.',8000)
            if callback:callback(False)
            return
        self.plan = p
        self.command_timer.stop()
        self._browser_opened = False
        self._server_ready_buffer = ''
        self._stop_requested = False
        self.router.start(p.label)
        self.started_at = time.time()
        self.started_ns = time.time_ns()
        activity.record(self.root, "GUI", p.label, "RUNNING")
        self.task_progress.setRange(0, 0)  # the CLI has no measured fractional progress
        self.task_progress.setFormat(p.label + '…')
        self.output.appendPlainText('\n> %s\n  (%s: %s)\n' % (p.command_line(), p.label, p.reason))
        if show_output:
            self.show_output('Output')
        self.statusBar().showMessage('%s…' % p.label)
        self.a_stop.setEnabled(True)
        args = p.process_args(self.root)
        self.process.start(args[0], args[1:])
        if not ((p.target == "arcade" and p.op == "run") or (p.target == "ledger" and p.op == "reference")):
            self.command_timer.start(120000)

    def _read_process(self):
        data = bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace')
        if data:
            if self.plan and ((self.plan.target == 'arcade' and self.plan.op == 'run') or (self.plan.target == 'ledger' and self.plan.op == 'reference')) and not self._browser_opened:
                self._server_ready_buffer = (self._server_ready_buffer + data)[-1024:]
                match = re.search(r'READY (http://127\.0\.0\.1:\d+/)', self._server_ready_buffer)
                if match:
                    self._browser_opened = True
                    self.task_progress.setRange(0, 100)
                    self.task_progress.setValue(100)
                    self.task_progress.setFormat('Arcade preview live')
                    QDesktopServices.openUrl(QUrl(match.group(1)))
                    self.statusBar().showMessage('STRUTHIO Arcade browser preview: ' + match.group(1))
            self.router.append(data)
            self.output.moveCursor(QTextCursor.End)
            self.output.insertPlainText(data)
            self.output.ensureCursorVisible()

    def _process_finished(self, code, status):
        self.command_timer.stop()
        self.execution_lock.release()
        self._read_process()
        p = self.plan
        callback, self._job_callback = self._job_callback, None
        stopped = self._stop_requested
        good = code == 0 and status == QProcess.NormalExit and not stopped
        extra = engine.collect_output(p, '', self.started_at, self.root) if p else ''
        if extra:
            self.router.append(extra)
            self.output.appendPlainText(extra.strip())
        self.router.finish(code if good else (code or 1))
        self._fill_problems(p)
        errors = sum(1 for x in self.problems if x[0].severity in ('error', 'fatal error'))
        warnings = sum(1 for x in self.problems if x[0].severity == 'warning')
        activity.record(self.root, 'GUI', p.label if p else 'Command', 'STOPPED' if stopped else ('PASS' if good else 'FAIL'), f'exit {code}')
        verdict = 'stopped' if stopped else ('succeeded' if good else ('failed' if code not in (3,) else 'is not available here'))
        summary = '%s %s' % (p.label if p else 'Command', verdict)
        if errors or warnings:
            summary += ' — %d error(s), %d warning(s)' % (errors, warnings)
        self.output.appendPlainText('%s (exit %s)\n' % (summary, code))
        self.a_stop.setEnabled(False)
        self.task_progress.setRange(0, 100)
        self.task_progress.setValue(100 if good else 0)
        self.task_progress.setFormat('Stopped' if stopped else ('Done' if good else 'Failed'))
        self.clip.presence.command_finished(good, stopped, code == 3, p.label if p else 'Command')
        if callback is not None:
            self.after_build = None
            if not good:self.show_output('Output')
            if not self._closing:callback(good)
            return
        if p and p.op == 'build' and p.target == 'game' and p.project:
            self.session.set_last_game(p.project)
        if stopped:
            self.after_build = None
            self.statusBar().showMessage(summary, 5000)
        elif not good:
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
            if p and p.op == 'run' and p.target == 'game':
                self._show_preview(p)
                return
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
            self._stop_requested = True
            self._kill_command_tree()
            self.output.appendPlainText('Stopped by user.')

    def master_stop_all(self):
        return self.master_stop_controller.request()

    def _kill_command_tree(self):
        pid=int(self.process.processId())
        if not pid:return
        if os.name=='nt':
            # Native Windows qualification remains open. Fixed executable/arguments;
            # no project-supplied shell command is used.
            self._taskkill=QProcess(self)
            self._taskkill.start('taskkill.exe',['/PID',str(pid),'/T','/F'])
        else:
            import signal
            try:os.killpg(pid,signal.SIGKILL)
            except ProcessLookupError:pass

    def _show_preview(self, p):
        sim_dir = self.root / p.project / 'build' / 'sim'
        frames = discover_preview_frames(sim_dir, since=self.started_at)
        for i in range(self.tabs.count() - 1, -1, -1):
            if isinstance(self.tabs.widget(i), PreviewTab):
                w = self.tabs.widget(i)
                self.tabs.removeTab(i)
                w.deleteLater()
        self.sim_trace.scenario_divergent = False
        tab = PreviewTab(self, p.project, frames)
        tab.frame_requested.connect(self.sim_trace.seek_frame_number)
        self.tabs.addTab(tab, tab.title())
        self.tabs.setCurrentWidget(tab)
        self.sim_trace.set_trace(sim_dir / 'trace.txt', p.project)
        self.debug_view.setPlainText('HOST_SIM frame capture; behavioral trace generation in progress. No physical ARC-1 device used.')
        self._run_system_scenario(p.project, engine.RUN_FRAMES, {})

    def run_offload_comparison(self):
        project = self.sim_trace.project if self.sim_trace.rows else 'examples/hello_arc1'
        try:
            p = engine.simulation_plan('compare', project, self.root)
        except ValueError as exc:
            self.message('Comparison unavailable', str(exc));return
        self._launch_job(p, lambda good:self._comparison_finished(good,project))

    def _comparison_finished(self, good, project):
        report_path = self.root / project / 'build' / 'system_sim' / 'offload_compare.json'
        if not good or not self._fresh_artifact(report_path):
            self.statusBar().showMessage('Comparison failed or produced no fresh report; previous output not loaded',8000)
            return
        try:
            import json
            report = json.loads(report_path.read_text(encoding='utf-8'))
            if report.get('evidence') != 'SCENARIO_ASSUMPTION' or report.get('schema') != 'arc1.offload_compare.v1':
                raise ValueError('Unsupported or unverified comparison report')
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Report error', str(exc))
            return
        self._close_start()
        for i in range(self.tabs.count()):
            existing = self.tabs.widget(i)
            if existing.objectName() == 'OffloadComparison':
                self.tabs.removeTab(i)
                existing.deleteLater()
                break
        widget = QWidget()
        widget.setObjectName('OffloadComparison')
        layout = QVBoxLayout(widget)
        heading = QLabel('F133 ↔ FPGA12 · Assumption Sandbox')
        heading.setStyleSheet('font-size: 18px; font-weight: 700; color: #e2e5e8;')
        layout.addWidget(heading)
        note = QLabel('HYPOTHETICAL · Not F133 profiling, a real FPGA bitstream, or measured bus bandwidth.\n'
                      'Both models replay the same host controller frames. Pixel output is baseline only.')
        note.setWordWrap(True)
        note.setStyleSheet('color: #d8a37e;')
        layout.addWidget(note)
        summary = QLabel('%d frames · %d synthetic jobs · CPU-only %.1f µs/frame · FPGA12 offload %.1f µs/frame' % (
            report['modes']['cpu']['frames'],report['modes']['cpu']['total_jobs'],
            report['modes']['cpu']['mean_estimated_frame_us'],
            report['modes']['fpga12']['mean_estimated_frame_us']))
        summary.setWordWrap(True)
        layout.addWidget(summary)
        for key, title in [('mean_f133_demand_pct','F133 demand / assumed frame budget'),
                           ('mean_fpga12_demand_pct','FPGA12 demand / assumed frame budget'),
                           ('mean_link_demand_pct','F133 ↔ FPGA12 link demand / assumed budget')]:
            row = QHBoxLayout()
            row.addWidget(QLabel(title),2)
            for mode in ('cpu','fpga12'):
                value=report['modes'][mode][key]
                bar=QProgressBar()
                bar.setRange(0,100)
                bar.setValue(min(100,round(value)))
                bar.setFormat(mode.upper()+': %.1f%%'%value)
                bar.setStyleSheet('QProgressBar::chunk { background: #b47852; }')
                row.addWidget(bar,3)
            layout.addLayout(row)
        summary2 = QLabel('Mean modeled frame-time change: %+.2f%% · CPU-only deadline misses: %d · offload misses: %d' % (
            report['mean_time_change_pct'],report['modes']['cpu']['deadline_misses'],
            report['modes']['fpga12']['deadline_misses']))
        layout.addWidget(summary2)
        controls = QHBoxLayout()
        for mode, label in [('cpu','Inspect CPU-only scenario in right panel'),
                            ('fpga12','Inspect FPGA12 scenario in right panel')]:
            button=QPushButton(label)
            button.clicked.connect(lambda checked=False,m=mode,proj=project:self._select_workload_overlay(proj,m))
            controls.addWidget(button)
        layout.addLayout(controls)
        assumptions = QPlainTextEdit()
        assumptions.setReadOnly(True)
        assumptions.setMaximumHeight(210)
        assumptions.setPlainText('Scenario assumptions (change with CLI --profile):\n' +
                                 json.dumps(report['profile'],indent=2) + '\n\nSource: ' +
                                 str(report.get('input_trace_sha256','unknown')) +
                                 '\nNo real F133, FPGA12 or interconnect hardware is measured.')
        layout.addWidget(assumptions)
        layout.addStretch(1)
        self.tabs.addTab(widget,'A/B Offload · Hypothetical')
        self.tabs.setCurrentWidget(widget)
        self.statusBar().showMessage('Synthetic comparison complete · inspect assumption model before interpreting results',6000)

    def _select_workload_overlay(self, project, mode):
        if mode not in ('cpu','fpga12'):
            return
        path = self.root / project / 'build' / 'system_sim' / ('workload_%s.jsonl' % mode)
        self.sim_trace.scenario_divergent = True  # host framebuffer is baseline, not a predicted offload game
        self.sim_trace.set_system_trace(path, project)
        self.sim_trace.pause()
        self.instruments.snapshot(self.sim_trace.rows[0] if self.sim_trace.rows else None)
        self.instruments.set_hardware_context('Synthetic %s comparison · NOT hardware telemetry' % mode)

    def _run_system_scenario(self, project, frames, scenario):
        try:
            p = engine.simulation_plan('system',project,self.root,frames,scenario)
        except ValueError as exc:
            self.message('Scenario unavailable',str(exc));return
        def complete(good):
            trace = self.root/project/'build/system_sim/system_trace.jsonl'
            if not good or not self._fresh_artifact(trace):
                self.sim_trace.heading.setText('Scenario failed; no fresh trace loaded. See Output.')
                return
            self.sim_trace.scenario_divergent = bool(scenario)
            self.sim_trace.set_system_trace(trace,project)
            self.sim_trace.start()
        self._launch_job(p,complete)

    def _fresh_artifact(self, path):
        try:return path.is_file() and path.stat().st_mtime_ns >= self.started_ns
        except OSError:return False

    def _launch_job(self, plan, callback):
        if self.process.state() != QProcess.NotRunning or self.workflow_active:
            self.statusBar().showMessage('A command is running. Stop it or wait for completion.',5000)
            return False
        self.after_build = None
        self._then = None
        self._job_callback = callback
        self.sim_trace.pause()
        self._launch(plan,show_output=False)
        return True

    def _process_error(self, error):
        if error == QProcess.FailedToStart:
            self.output.appendPlainText('Unable to start command: '+self.process.errorString())
            self._process_finished(1,QProcess.CrashExit)

    def _command_timeout(self):
        self.output.appendPlainText('Host command exceeded the 120-second limit.')
        self.stop_process()

    def run_host_workflow(self, project):
        if self.process.state()!=QProcess.NotRunning or self.workflow_active:return
        if not self.save_all():return
        try:
            host=engine.simulation_plan('host',project,self.root)
            system=engine.simulation_plan('system',project,self.root)
        except ValueError as exc:
            self.message('Workflow unavailable',str(exc));return
        self._workflow_steps = [engine.plan('build','game',None,project,self.root),
                                engine.plan('test','game',None,project,self.root),host,system]
        self._workflow_project = project
        self._workflow_index = 0
        self._workflow_host_started = 0
        self.workflow_active = True
        self.after_build = None
        self._then = None
        self.sim_trace.pause()
        self._next_workflow(True)

    def _next_workflow(self, good):
        if not self.workflow_active:return
        if not good:
            self.workflow_active = False
            self.workflow_status = 'Workflow stopped at step %d/4. Inspect Output; later steps were not run.' % self._workflow_index
            activity.record(self.root,'WORKFLOW','Host development loop','STOPPED')
            self._refresh_activity();return
        if self._workflow_index==4:
            project=self._workflow_project
            trace=self.root/project/'build/system_sim/system_trace.jsonl'
            frames=discover_preview_frames(self.root/project/'build/sim',since=self._workflow_host_started)
            if not self._fresh_artifact(trace) or not frames:
                self._next_workflow(False);return
            self.workflow_active=False
            self.workflow_status='4/4 steps passed · build, tests, host capture, behavioral trace · HOST_SIM only'
            self.sim_trace.set_trace(self.root/project/'build/sim/trace.txt',project)
            self.sim_trace.scenario_divergent=False
            self.sim_trace.set_system_trace(trace,project)
            tab=PreviewTab(self,project,frames);tab.frame_requested.connect(self.sim_trace.seek_frame_number)
            self.tabs.addTab(tab,tab.title())
            self.sim_trace.start()
            activity.record(self.root,'WORKFLOW','Host development loop','PASS')
            self._refresh_activity();return
        step=self._workflow_steps[self._workflow_index]
        self._workflow_index+=1
        self.workflow_status='Step %d/4: %s' % (self._workflow_index,step.label)
        self._job_callback=self._next_workflow
        self._launch(step)
        if self._workflow_index==3:self._workflow_host_started=self.started_at
        self._refresh_activity()

    def show_project_search(self):
        return self._project_tab(ProjectSearchTab)

    def show_development(self):
        from .development_tabs import DevelopmentTab
        return self._project_tab(DevelopmentTab)

    def show_hardware_proof(self):
        from .project_context import detached
        if detached(self.root):
            from .empty_workspace_qt import show
            return show(self,'Hardware Proof')
        from .proof_tab import HardwareProofTab
        return self._project_tab(HardwareProofTab)

    def show_setup_guide(self):
        program=locations.program(self.root);guide=program/'GETTING_STARTED.md'
        guide=guide if guide.is_file() else program/'docs/WORKSHOP.md'
        if program==self.root:return self.open_document(guide)
        # A separate workspace cannot edit program documents: show the guide read-only.
        view=QTextBrowser();view.setObjectName('ProgramDocument');view.setOpenExternalLinks(True)
        view.setMarkdown(guide.read_text(encoding='utf-8'));view.setAccessibleName('Installation Guide (read-only)')
        self.tabs.addTab(view,'Installation Guide');self.tabs.setCurrentWidget(view);return view

    def show_remote_link(self):
        from .remote_link import RemoteLink
        if not hasattr(self,'remote_link'):self.remote_link=RemoteLink(self)
        self.remote_link.show()
        return self.remote_link

    def show_engineering(self):
        from .engineering_tabs import EngineeringTab
        return self._project_tab(EngineeringTab)

    def show_parser_review(self):
        from .arc_review import CandidateReviewTab
        return self._project_tab(CandidateReviewTab)

    def show_developer_tools(self, operation=None):
        from .workshop_tabs import DeveloperToolsTab
        editor = self.current_editor()
        if editor and not self.tabs.pin(editor):
            return None
        tab = self._project_tab(DeveloperToolsTab)
        if editor:
            tab.capture_editor(editor)
        if isinstance(operation, str):
            tab.assist(operation)
        return tab

    def show_brain_link(self):
        from .brain_link_tab import BrainLinkTab
        return self._project_tab(BrainLinkTab)

    def show_asset_gallery(self):
        from .ux_gallery import AssetGalleryTab
        return self._project_tab(AssetGalleryTab)

    def show_genesis(self):
        from .genesis_tab import GenesisTab
        return self._project_tab(GenesisTab)

    def show_reading(self):
        from .reading_preferences import ReadingDialog
        dialog=ReadingDialog(self);dialog.exec()

    def show_engineering_register(self):
        from .register_tabs import RegisterTab
        return self._project_tab(RegisterTab)

    def show_vendor_vault(self):
        from .register_tabs import VendorTab
        return self._project_tab(VendorTab)

    def show_database_rom(self):
        from .project_context import detached
        if detached(self.root):
            from .empty_workspace_qt import show
            return show(self,'Database Rom')
        from .records_tab import DatabaseROMTab
        return self._project_tab(DatabaseROMTab)

    def show_orange_book(self):
        from .project_context import detached
        if detached(self.root):
            from .empty_workspace_qt import show
            return show(self,'Orange Book')
        if not (self.root / 'docs/orange_book/bindings.json').is_file():
            self.message('The Orange Book source is not present in this project.')
            return None
        from .register_tabs import OrangeBookTab, BookAutoWatcher
        if self.book_watcher is None:
            self.book_watcher = BookAutoWatcher(self)
        return self._project_tab(OrangeBookTab)

    def show_clip_workspace(self):
        from .clip_workspace import ClipWorkspaceTab
        return self._project_tab(ClipWorkspaceTab)

    def show_native_game(self):
        from .project_context import detached
        if detached(self.root):
            from .empty_workspace_qt import show
            return show(self,'Native Game')
        from .engineering_tabs import NativeGameTab
        return self._project_tab(NativeGameTab)

    def show_native_project(self):
        from .project_context import detached
        if detached(self.root):
            from .empty_workspace_qt import show
            return show(self,'Native Project')
        from .native_project_tab import NativeProjectTab
        return self._project_tab(NativeProjectTab)

    def show_arcos(self):
        from .project_context import detached
        if detached(self.root):
            from .empty_workspace_qt import show
            return show(self,'Arcos')
        from .console_tab import VirtualConsoleTab
        return self._project_tab(VirtualConsoleTab)

    def show_arcos_diagnostics(self):
        from .project_context import detached
        if detached(self.root):
            from .empty_workspace_qt import show
            return show(self,'Arcos Diagnostics')
        from .arcos_tab import ArcOSTab
        return self._project_tab(ArcOSTab)

    def run_development(self,mode):
        if not self.save_all():return
        try:plan=engine.development_plan(mode,self.root)
        except (OSError,ValueError) as exc:
            self.message('Development case unavailable',str(exc),error=True);return
        tab=self.show_development()
        def completed(good):
            view=self.show_development()
            path=self.root/'build/development/diag_ticket_isolation/latest.json'
            if not self._fresh_artifact(path):
                view.state.setText('Stopped or failed before a fresh report was written. Previous results are historical.')
                return
            view.refresh()
            self.statusBar().showMessage('Development run finished; review source freshness and individual checks.',8000)
            if self.problems:self.show_output('Problems')
            else:self.output_dock.hide()
        if self._launch_job(plan,completed):
            tab.state.setText('Running '+mode+' checks on saved source snapshots… Ctrl+Break stops the job.')
            for name in ('Run baseline','Run working copy','Compare both'):tab.buttons[name].setEnabled(False)

    def show_hardware_ledger(self):
        from .project_context import detached
        if detached(self.root):
            from .empty_workspace_qt import show
            return show(self,'Hardware Ledger')
        from .ledger_tabs import HardwareLedgerTab
        for i in range(self.tabs.count()):
            tab=self.tabs.widget(i)
            if isinstance(tab,HardwareLedgerTab):
                self.tabs.setCurrentIndex(i);tab.refresh();return tab
        self._close_start()
        tab=HardwareLedgerTab(self);self.tabs.addTab(tab,tab.title());self.tabs.setCurrentWidget(tab)
        return tab

    def run_ledger(self,action):
        if not self.save_all():return
        try:plan=engine.ledger_plan(action,self.root)
        except (OSError,ValueError,KeyError) as exc:
            self.message('Import unavailable',str(exc),error=True);return
        tab=self.show_hardware_ledger()
        def finished(good):
            tab.refresh()
            self.statusBar().showMessage(plan.label + (' completed' if good else ' failed or stopped'),8000)
            if action=='inspect':tab.result.setText('Source verification passed.' if good else 'Source verification failed. See Output.')
            if action=='parity':
                tab.result.setText('PASS · 1,344 host parity vectors. Partial C bootstrap; no full-game or board parity.' if good else 'Host checks failed or stopped. See Output; no new passing evidence accepted.')
                if good:
                    self.open_document(self.root/'build/arc_ledger/p11-host-latest.json')
                    self.open_document(self.root/'build/arc_ledger/struthio_port_bootstrap.ppm')
                    self.tabs.setCurrentWidget(tab)
        if self._launch_job(plan,finished):
            tab.result.setText({'parity':'Running host C checks…','inspect':'Verifying imported source hashes…',
                               'reference':'Opening original JS game in an external browser; WebGPU required. Stop closes the local preview server.'}[action])

    def show_project_desk(self):
        return self._project_tab(ProjectDeskTab)

    def _project_tab(self, kind):
        for i in range(self.tabs.count()):
            tab=self.tabs.widget(i)
            if isinstance(tab,kind):
                self.tabs.setCurrentWidget(tab)
                if hasattr(tab,'refresh'):tab.refresh()
                return tab
        self._close_start()
        tab=kind(self)
        from .ux_assets import polish_buttons
        polish_buttons(tab,self.root)
        from .reading_preferences import apply as apply_reading
        self.tabs.addTab(tab,tab.title());self.tabs.setCurrentWidget(tab)
        apply_reading(self)
        return tab

    def toggle_split_editor(self):
        if self.split_editor is not None:
            self._close_split();return
        source=self.current_editor()
        if source is None:
            self.statusBar().showMessage('Open a source document to split it; then select another tab on the left.',6000);return
        top=QHBoxLayout();label=QLabel(source.path.name+' · shared document');label.setWordWrap(True)
        close=QPushButton('Close split');close.clicked.connect(self._close_split)
        top.addWidget(label,1);top.addWidget(close);self.split_layout.addLayout(top)
        self.split_editor=CodeEditor(source.path,self.root)
        self.split_editor.setDocument(source.document())
        self.split_editor.setReadOnly(source.isReadOnly())
        self.split_editor.cursorPositionChanged.connect(self.update_document_info)
        self.split_layout.addWidget(self.split_editor,1)
        self.split_panel.show();self.workspace_split.setSizes([500,500])
        self.split_editor.go_to(*source.position())

    def _close_split(self):
        self.split_panel.hide()
        self.split_editor=None
        def clear(layout):
            while layout.count():
                item=layout.takeAt(0)
                if item.widget():item.widget().deleteLater()
                elif item.layout():clear(item.layout())
        clear(self.split_layout)

    def _maintain_work(self):
        if self.selection_context:self.refresh_selection(refresh=False)
        from .development_tabs import DevelopmentTab
        tab=self.tabs.currentWidget()
        if isinstance(tab,DevelopmentTab) and self.process.state()==QProcess.NotRunning:tab.refresh_if_changed()
        for i in range(self.tabs.count()):
            ed=self.tabs.widget(i)
            if not isinstance(ed,CodeEditor):continue
            relative=engine.rel(ed.path,self.root)
            try:
                if ed.document().isModified() and not ed.isReadOnly():
                    self.recovery.put(relative,ed.toPlainText(),getattr(ed,'disk_sha256',None))
                    ed.recovery_owned = True
                changed=file_hash(ed.path)!=getattr(ed,'disk_sha256',None)
                if changed!=getattr(ed,'external_changed',False):
                    ed.external_changed=changed;self._retitle(ed)
                    if changed:self.statusBar().showMessage('File changed on disk: '+relative+' · Save will ask before overwriting',9000)
            except (OSError,ValueError) as exc:
                self.statusBar().showMessage('Recovery copy unavailable: '+str(exc),7000)
        self._refresh_activity()

    def show_recovery(self):
        entries=self.recovery.entries()
        if not entries:
            self.statusBar().showMessage('No unsaved recovery copies',5000);return
        dialog=QDialog(self);dialog.setWindowTitle('Recover unsaved work');dialog.resize(680,360)
        layout=QVBoxLayout(dialog)
        note=QLabel('Recovery restores a buffer only. Source files change only when you save. Copies remain available until restored or explicitly discarded.')
        note.setWordWrap(True);layout.addWidget(note)
        listing=QListWidget();layout.addWidget(listing)
        for entry in entries:listing.addItem(entry['path']+(' · DISK CHANGED' if entry['disk_changed'] else ''))
        listing.setCurrentRow(0)
        row=QHBoxLayout();restore=QPushButton('Restore selected buffer');discard=QPushButton('Discard selected copy');later=QPushButton('Later')
        for button in (restore,discard,later):row.addWidget(button)
        layout.addLayout(row)
        def selected():
            i=listing.currentRow()
            return entries[i] if 0<=i<len(entries) else None
        def recover():
            entry=selected()
            if entry:
                ed=self.open_document(self.root/entry['path'])
                if isinstance(ed,CodeEditor) and not ed.isReadOnly():
                    if ed.document().isModified() and QMessageBox.question(dialog,'Replace buffer?','Replace the current unsaved buffer with this recovery copy?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
                    ed.setPlainText(entry['content']);ed.disk_sha256=entry['base_sha256'];ed.document().setModified(True);ed.recovery_owned=True
                    ed.external_changed=entry['disk_changed'];self._retitle(ed)
                    dialog.accept()
        def remove():
            entry=selected()
            if entry and QMessageBox.question(dialog,'Discard recovery copy?','Permanently discard the selected recovery copy?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:
                self.recovery.remove(entry['path']);entries.pop(listing.currentRow());listing.takeItem(listing.currentRow())
        restore.clicked.connect(recover);discard.clicked.connect(remove);later.clicked.connect(dialog.reject)
        dialog.exec()

    def _refresh_activity(self):
        events=activity.recent(self.root)
        self.agent_view.setPlainText('Recorded Graphite commands and job transitions. Live tail: Recent Activity.\n\n'+
            '\n'.join(time.strftime('%H:%M:%S',time.localtime(e['at']))+'  '+e['origin']+'  '+e['operation']+'  '+e['state'] for e in events))
        for i in range(self.tabs.count()):
            tab=self.tabs.widget(i)
            if isinstance(tab,ProjectDeskTab):tab.refresh_activity()

    def _refresh_readiness(self):
        data=readiness.snapshot(self.root)
        self.readiness_progress.setRange(0,data['required_gates']);self.readiness_progress.setValue(data['verified_gates'])
        self.readiness_progress.setFormat('%d/%d evidence' % (data['verified_gates'],data['required_gates']))
        self.readiness_progress.setToolTip('Goal: ≥95% first-try success. Probability unknown. Evidence records are not a probability estimate.')

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
    def show_budgets(self, tab='Resources'):
        if isinstance(tab,bool):tab='Resources'  # QAction.triggered supplies checked.
        self._close_start()
        if tab=='Boot model':tab='Boot'  # Retain the existing action's route.
        self.inspector_dock.show()
        self.inspector_dock.raise_()
        for i in range(self.inspector_tabs.count()):
            if self.inspector_tabs.tabText(i) == tab:
                self.inspector_tabs.setCurrentIndex(i)

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
        if self.project_required('Cartridges'):return
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
        if self.project_required('Cartridges'):return
        try:
            r = package_game(self.root / 'examples' / 'hello_arc1', self.root / 'cartridges' / 'hello_arc1.arc1cart')
        except (CartridgeError, OSError) as e:
            self.message('Package failed', str(e), error=True)
            return
        self.refresh_shelf()
        self.output.appendPlainText('Packaged host cartridge ' + r['name'])
        self.show_output('Output')

    def import_cartridge_dialog(self):
        if self.project_required('Cartridges'):return
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
        if self.project_required('Cartridges'):return
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
                ('F5', 'Preview Arcade in browser or run a C host game'),
                ('Ctrl+Shift+Y', 'Detailed host simulation trace in center'),
                ('F8 / Shift+F8', 'Next / previous problem'),
                ('F10', 'Show or hide the output panel'), ('F2 / Del', 'Rename / delete in Browse'),
                ('Ctrl+Shift+P', 'Command palette'), ('View > Reset Window Layout', 'Get the factory layout back')]
        self.message('Keyboard Shortcuts', '\n'.join('%-26s %s' % r for r in rows))

    def show_about(self):
        from .editorial_art import about_dialog
        about_dialog(self,
                     'Graphite %s (Qt %s).\n\nHost tools only: builds, tests and the game simulator run on this '
                     'PC. No ARC-1 board exists yet; nothing is flashed or deployed, and firmware stage images are '
                     'NOT BOOTABLE. Fabrication is on HOLD.\n\nAgents use the same engine through '
                     '"python arc1 agent".' % (VERSION, qt_version())).exec()

    def closeEvent(self, event):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, "can_close_concern") and not tab.can_close_concern():
                event.ignore(); return
            if hasattr(tab, "can_close_pdf") and not tab.can_close_pdf():
                event.ignore(); return
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, CodeEditor) and w.document().isModified():
                self.tabs.setCurrentWidget(w)
                ans = self.ask_save(w.path.name)
                if ans == 'cancel' or (ans == 'save' and not self.save_document(w)):
                    event.ignore()
                    return
                if ans == 'discard':
                    try:
                        self.recovery.put(engine.rel(w.path,self.root),w.toPlainText(),w.disk_sha256)
                        w.recovery_owned=False
                    except (OSError,ValueError) as exc:
                        self.statusBar().showMessage('Recovery copy unavailable: '+str(exc),10000)
                        event.ignore();return
        thread=getattr(self,'return_thread',None)
        if thread is not None and not thread.skip_keep_once and not thread.capture(for_exit=True):
            event.ignore();return
        for i in range(self.tabs.count()):
            w=self.tabs.widget(i)
            if isinstance(w,ProjectSearchTab) and not w.shutdown():
                event.ignore();return
        driver=getattr(self,'agent_driver',None)
        if driver is not None:
            # AGENT-02: with the Ledger service running (ledger_bridge.kernel.is_host_client) and the owner's setting
            # agent.continue_when_closed on, running assignments are handed to the service (agent.release) and continue there;
            # otherwise they pause as in AGENT-01 and Today offers to resume them next time
            if driver.close_words()=='release':driver.release_all('Graphite closed · the Graphite service continues')
            else:driver.pause_all('Graphite closed')
        self._closing = True
        if getattr(getattr(getattr(self,'type_bar',None),'hatch',None),'lifecycle',None) is not None:self.type_bar.hatch.lifecycle.shutdown()
        if hasattr(self,'ledger_bridge') and not getattr(self.ledger_bridge.kernel,'is_host_client',False):
            from .engineering_kernel import operator
            self.ledger_bridge.kernel.dispatch('brain.stop',{},operator())
        self.maintenance_timer.stop()
        if hasattr(self.clip_dock,'job_timer'):self.clip_dock.job_timer.stop()
        if getattr(self,'home_page',None) is not None:self.home_page.shutdown()
        if hasattr(self,'clip'):self.clip.ticker.stop()
        if self.book_watcher is not None:
            self.book_watcher.shutdown()
        for i in range(self.tabs.count()):
            w=self.tabs.widget(i)
            if hasattr(w,'shutdown_engineering'):w.shutdown_engineering()
            if isinstance(w,CodeEditor) and getattr(w,'recovery_owned',False):self.recovery.remove(engine.rel(w.path,self.root))
        for worker in list(getattr(self, 'service_workers', [])):
            worker.wait(10000)
        self.sim_trace.pause()
        if self.process.state() != QProcess.NotRunning:
            self._kill_command_tree()
            self.process.waitForFinished(2000)
        self.execution_lock.release()
        self.save_session()
        self.desktop_lease.unlink(missing_ok=True)
        event.accept()


def engine_layout_version():
    from .session import LAYOUT_VERSION
    return LAYOUT_VERSION


def qt_version():
    from PySide6 import __version__
    return __version__


def make_app(argv=None):
    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationName('ARC Ledger')  # unchanged: names the existing per-user application data
    from .version import VERSION as product_version
    app.setApplicationVersion(product_version)
    app.setOrganizationName('ARC-1')
    app.setStyle('Fusion')
    # Ledger & Slate 3, "Paper": paper, ink and one cobalt accent; Plex fonts bundled.
    from .theme2 import PALETTE, QSS2
    from .shell2 import load_fonts
    from .locations import PACKAGE
    load_fonts(PACKAGE)
    palette=app.palette()
    for role,color in PALETTE:
        palette.setColor(getattr(QPalette,role),QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(QSS2)
    from .theme2 import install as relight_older_panels
    relight_older_panels(app)
    return app


def main():
    app = make_app()
    from .locations import default_root
    w = WorkbenchWindow(root=default_root())
    if os.environ.get('ARC_LEDGER_FULLSCREEN')=='1':w.showFullScreen();w.a_fullscreen.setChecked(True)
    else:w.show()
    opening = os.environ.get('ARC_LEDGER_OPEN')
    if opening:
        # A start script may open one Ledger room, for example the Office.
        QTimer.singleShot(0, lambda: w.ledger_bridge.navigation().get(opening, lambda: None)())
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
