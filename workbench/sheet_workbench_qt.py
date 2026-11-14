"""A file-backed worksheet and a contextual preview for the existing staC chain runner."""
import json
import math
import re
import shutil
from decimal import Decimal
from pathlib import Path, PurePosixPath

from PySide6.QtCore import QAbstractTableModel, QFileSystemWatcher, QModelIndex, QPoint, QProcess, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QMenu,
                               QPushButton, QScrollArea, QSizePolicy, QTableView, QToolButton,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from . import boss_theme as ink, files_service
from .chain_workbench_qt import ChainTray, call
from .context_menu import kernel_of
from .pane_qt import BranchTree

FILE_MARKS = {'csv': '[#]', 'spreadsheet': '[=]', 'pdf': '[P]', 'document': '[=]',
              'text': '[@]', 'markdown': '[*]', 'folder': '[/]', 'image': '[.]', 'code': '[>]'}

SURFACE = """
QTableView#SheetRows, QTableWidget#ChainPreview {
    background: %(GROUND)s; color: %(TEXT)s; gridline-color: %(LINE)s;
    selection-background-color: %(AMBER_SOFT)s; selection-color: %(TEXT)s;
    font-family: "%(MONO)s"; border: 1px solid %(LINE)s; border-radius: 0;
}
QTableView#SheetRows QHeaderView::section, QTableWidget#ChainPreview QHeaderView::section {
    background: %(PANEL)s; color: %(TEXT)s; border: 0; padding: 4px 9px;
    border-right: 1px solid %(LINE)s; border-bottom: 1px solid %(LINE_MID)s;
}
QTableView#SheetRows QHeaderView::section:horizontal {min-height: 38px; font-weight: 600; padding-left: 3px; padding-right: 3px;}
QTableView#SheetRows QHeaderView::section:vertical {padding: 2px 3px;}
QTableView#SheetRows QHeaderView::section:vertical:checked {background: %(AMBER_SOFT)s; color: %(AMBER_EDGE)s;}
QTableView#SheetRows QTableCornerButton::section {background: %(PANEL)s; border: 0;
    border-right: 1px solid %(LINE)s; border-bottom: 1px solid %(LINE_MID)s;}
QTableWidget#ChainPreview QHeaderView::section {background:%(TEAL_SOFT)s;}
QTableView#SheetRows::item, QTableWidget#ChainPreview::item {padding: 0 9px;}
QTableView#SheetRows::item:selected {background:%(AMBER_SOFT)s;border-top:1px solid %(AMBER_EDGE)s;border-bottom:1px solid %(AMBER_EDGE)s;}
QFrame#WorksheetResult {background: %(GROUND)s; border: 1px solid %(LINE)s;}
QFrame#WorksheetTotal {border:1px solid %(TEAL_EDGE)s; background:%(TEAL_SOFT)s;}
QFrame#WorksheetTotal QLabel {font-family:"%(MONO)s";font-weight:600;color:%(READY)s;}
QLabel#WorksheetTitle, QLabel#WorksheetPreviewTitle, QLabel#WorksheetChainTitle {font-family: "%(MONO)s"; font-weight: 600;}
QLabel#WorksheetSelection, QLabel#WorksheetSourceState, QLabel#WorksheetHint {font-family:"%(MONO)s";}
QLabel#WorksheetHint {color:%(QUIET)s; font-size:12px;}
QPushButton#WorksheetChainStep, QPushButton#FullSpreadsheet, QPushButton#WorksheetCommands {
    font-family:"%(MONO)s";background:%(RAISED)s;border:1px solid %(LINE)s;border-radius:0;padding:5px 9px;
}
QPushButton#WorksheetChainStep {font-size:14px; padding:4px 6px;}
QPushButton#WorksheetChainStep:hover, QPushButton#WorksheetChainStep:focus,
QPushButton#FullSpreadsheet:hover, QPushButton#FullSpreadsheet:focus,
QPushButton#WorksheetCommands:hover, QPushButton#WorksheetCommands:focus {border-color:%(AMBER_EDGE)s;}
QPushButton#RunWorksheetChain {background: %(AMBER_EDGE)s; color: %(TERMINAL_GROUND)s;
    border: 1px solid %(AMBER_EDGE)s; font-family: "%(MONO)s"; font-weight:600; border-radius: 0; padding: 5px 10px;}
QPushButton#RunWorksheetChain:hover, QPushButton#RunWorksheetChain:focus {background: %(AMBER_TEXT)s;}
QPushButton#RunWorksheetChain:disabled {background: %(PANEL)s; color: %(QUIET)s; border-color: %(LINE)s;}
""" % vars(ink)


def text(words='', name=''):
    label = QLabel(words)
    label.setObjectName(name)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    return label


def make(viewer):
    if viewer.source.path is None or not viewer.view.get('sha256'):
        return None
    if viewer.view['kind'] not in ('csv', 'spreadsheet') or not (viewer.view.get('table') or viewer.view.get('sheets')):
        return None
    kernel = kernel_of(viewer.host)
    root = files_service.root(kernel, create=False).resolve()
    try:
        rel = viewer.source.path.resolve().relative_to(root).as_posix()
        path = files_service.resolve(kernel, rel)
    except (OSError, ValueError):
        return None
    if path.resolve() != viewer.source.path.resolve():
        return None
    return Worksheet(viewer, path, rel)


class Rows(QAbstractTableModel):
    def __init__(self, rows, parent):
        super().__init__(parent)
        self.rows = rows
        self.fields = list(dict.fromkeys(key for row in rows for key in row))
        self.marked = set()
        self.stock_grid = False

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.fields)

    def data(self, index, role):
        if not index.isValid():
            return None
        value = self.rows[index.row()].get(self.fields[index.column()])
        if role == Qt.DisplayRole:
            return '' if value is None else str(value)
        if role == Qt.TextAlignmentRole:
            if self.stock_grid and (type(value) in (int, float) or self.fields[index.column()].casefold() == 'unit'):
                return Qt.AlignCenter
            return (Qt.AlignRight if type(value) in (int, float) else Qt.AlignLeft) | Qt.AlignVCenter
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.fields[section].replace('_', ' ')
            return '✓' if section in self.marked else str(section + 1)
        if role == Qt.ForegroundRole and orientation == Qt.Vertical and section in self.marked:
            return QColor(ink.AMBER_EDGE)
        if role == Qt.AccessibleTextRole and orientation == Qt.Vertical:
            return f'Row {section + 1}' + (' selected' if section in self.marked else '')
        if role == Qt.TextAlignmentRole and orientation == Qt.Horizontal and self.stock_grid:
            return (Qt.AlignLeft if self.fields[section].casefold() == 'part' else Qt.AlignHCenter) | Qt.AlignVCenter
        return None


class WorksheetGrid(QTableView):
    column_weights = ()

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setHeight(min(430, self.maximumHeight()))
        return hint

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_columns()

    def paintEvent(self, event):
        super().paintEvent(event)
        # Below the actual records, continue the desk's ruler without adding data rows.
        count = self.model().rowCount() if self.model() else 0
        last = count - 1
        start = max(0, self.rowViewportPosition(last) + self.rowHeight(last)) if count else 0
        height = self.viewport().height()
        if start >= height:
            return
        painter = QPainter(self.viewport())
        painter.setPen(QColor(ink.LINE))
        for y in range(start, height, self.verticalHeader().defaultSectionSize()):
            painter.drawLine(0, y, self.viewport().width(), y)
        painter.end()

    def fit_columns(self):
        if not self.column_weights:
            return
        width = self.viewport().width()
        header = self.horizontalHeader()
        edge = 0
        for index, weight in enumerate(self.column_weights):
            next_edge = edge + weight
            header.resizeSection(index, round(width * next_edge / 100) - round(width * edge / 100))
            edge = next_edge


class RowTrace(QWidget):
    """Draw the dashed route in the row gutter and between the live menu and chain."""
    def __init__(self, worksheet):
        super().__init__(worksheet)
        self.work = worksheet
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)

    def paintEvent(self, event):
        tray = self.work.tray
        menu = getattr(self.work, 'row_commands', None)
        menu_open = menu is not None and menu.isVisible()
        chain_open = bool(tray.program) and tray.isVisible()
        if not (menu_open or chain_open):
            return
        grid = self.work.grid
        offset = self.mapFromGlobal(grid.viewport().mapToGlobal(QPoint())).y()
        anchors = [offset + grid.rowViewportPosition(row) + grid.rowHeight(row) // 2 for row in self.work.rows_selected()]
        anchors = [y for y in anchors if offset <= y < offset + grid.viewport().height()]
        if not anchors:
            return
        grid_left = self.mapFromGlobal(grid.mapToGlobal(QPoint())).x()
        rail = grid_left - 19
        branch = None
        if menu_open:
            action = menu.activeAction() or next((a for a in menu.actions() if a.isEnabled() and not a.isSeparator()), None)
            if action is not None:
                branch = self.mapFromGlobal(menu.mapToGlobal(QPoint(0, menu.actionGeometry(action).center().y())))
                if branch.x() <= rail or branch.y() < min(anchors):branch = None
        track = None
        if chain_open:
            track = tray.track
            end = self.mapFromGlobal(track.mapToGlobal(QPoint(round(track.width() * .48), track.track_y)))
            turn = self.mapFromGlobal(tray.mapToGlobal(QPoint())).y() - 14
        painter = QPainter(self)
        colour = QColor(ink.AMBER_EDGE)
        painter.setPen(QPen(colour, 2, Qt.DashLine))
        bottom = max([*anchors, branch.y() if branch else 0, turn if track else 0])
        painter.drawLine(rail, min(anchors), rail, bottom)
        for y in anchors:
            painter.drawLine(rail, y, grid_left, y)
        if branch:
            painter.drawLine(rail, branch.y(), branch.x(), branch.y())
        if track:
            painter.drawLine(rail, turn, end.x(), turn)
            painter.drawLine(end.x(), turn, end.x(), end.y())
        painter.setPen(Qt.NoPen)
        painter.setBrush(colour)
        for y in anchors:
            painter.drawEllipse(QPoint(grid_left, y), 4, 4)
        if branch:painter.drawEllipse(QPoint(rail, branch.y()), 4, 4)
        if track:
            painter.setPen(QPen(colour, 1))
            painter.setBrush(QColor(ink.GROUND))
            for x, y in ((rail, turn - 15), (end.x(), end.y() - 20)):
                painter.drawRect(x - 7, y - 7, 14, 14)
                painter.drawLine(x - 3, y, x + 3, y)
                painter.drawLine(x, y - 3, x, y + 3)
        painter.end()


class Worksheet(QWidget):
    def __init__(self, viewer, path, relative):
        super().__init__(viewer)
        self.viewer, self.host = viewer, viewer.host
        self.path, self.relative, self.digest = path, relative, viewer.view['sha256']
        self.workbook_target = path.resolve()
        self.external_pending = False
        self.stale = False
        self.rollup_unit = None
        self.part_column = None
        self.setObjectName('Worksheet')
        self.setStyleSheet(SURFACE)
        from .boss_qt import PanelInk
        from .shell2 import role

        data = files_service.data_of(viewer.view)
        self.tables = data.get('sheets') or {None: data.get('rows', [])}
        body = QVBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(8)
        head = QHBoxLayout()
        heading = role(text(path.stem, 'WorksheetTitle'), 'title')
        head.addWidget(heading, 1)
        self.views = QToolButton()
        self.views.setText('File views')
        self.views.setPopupMode(QToolButton.InstantPopup)
        self.views.setMenu(QMenu(self.views))
        self.views.menu().aboutToShow.connect(self.fill_views)
        head.addWidget(self.views)
        self.external = QPushButton('[ Full spreadsheet ↗ ]')
        self.external.setObjectName('FullSpreadsheet')
        self.external.setAccessibleName('Open full spreadsheet application')
        self.external.setToolTip('Open this file in the system’s spreadsheet application')
        self.external.clicked.connect(self.open_external)
        head.addWidget(self.external)
        body.addLayout(head)
        sub = QHBoxLayout()
        self.selection = text('', 'WorksheetSelection')
        sub.addWidget(self.selection, 1)
        self.sheet_choice = QComboBox()
        self.sheet_choice.setAccessibleName('Worksheet sheet')
        for name in self.tables:
            self.sheet_choice.addItem(name or 'Table', name)
        self.sheet_choice.setVisible(len(self.tables) > 1)
        sub.addWidget(self.sheet_choice)
        self.commands = QPushButton('Row commands')
        self.commands.setObjectName('WorksheetCommands')
        self.commands.clicked.connect(lambda:self.open_menu(self.menu_anchor(100)))
        sub.addWidget(self.commands)
        body.addLayout(sub)
        work = QWidget(self)
        work_row = QHBoxLayout(work)
        work_row.setContentsMargins(22, 0, 0, 0)
        work_row.setSpacing(0)
        self.trace = RowTrace(self)
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        self.grid = WorksheetGrid()
        self.grid.setObjectName('SheetRows')
        self.grid.setAccessibleName('Worksheet data rows')
        self.grid.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.grid.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.grid.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.grid.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.grid.setContextMenuPolicy(Qt.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self.row_menu)
        self.grid.verticalScrollBar().valueChanged.connect(self.trace.update)
        column.addWidget(self.grid)
        column.addWidget(text('[ Select row numbers for row commands. ]', 'WorksheetHint'))
        column.addStretch(1)
        work_row.addLayout(column, 1)
        body.addWidget(work, 1)
        self.preview = QScrollArea(self)
        self.preview.setFrameShape(QFrame.NoFrame)
        self.preview.setWidgetResizable(True)
        self.preview.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.preview.setAccessibleName('Worksheet preview and source state')
        self.preview.hide()
        face = QWidget()
        face.setStyleSheet(SURFACE)
        self.preview.setWidget(face)
        side = QVBoxLayout(face)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(10)
        card = QFrame()
        card.setObjectName('WorksheetResult')
        result = QVBoxLayout(card)
        result.setSpacing(6)
        self.preview_title = role(text('[#] Chain preview', 'WorksheetPreviewTitle'), 'lead')
        result.addWidget(self.preview_title)
        self.tray = ChainTray(self.host, result_layout=result, format_rows=self.preview_rows)
        body.addWidget(self.tray)
        self.total_bar = QFrame()
        self.total_bar.setObjectName('WorksheetTotal')
        total_row = QHBoxLayout(self.total_bar)
        total_row.setContentsMargins(9, 5, 9, 5)
        self.total_caption = QLabel('Total')
        self.total = text()
        self.total.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        total_row.addWidget(self.total_caption)
        total_row.addWidget(self.total, 1)
        result.insertWidget(result.indexOf(self.tray.status), self.total_bar)
        side.addWidget(card)
        self.art = PanelInk(self.host, 'portrait')
        side.addWidget(self.art)
        self.source_state = text('', 'WorksheetSourceState')
        side.addWidget(self.source_state)
        side.addStretch(1)
        actions = QHBoxLayout()
        talk = QPushButton('Talk')
        talk.clicked.connect(self.host.shell2.show_slate_face)
        actions.addWidget(talk)
        self.reload_button = QPushButton('Reload source')
        self.reload_button.clicked.connect(self.reload_workbook)
        actions.addWidget(self.reload_button)
        side.addLayout(actions)

        self.folder = BranchTree(self)
        self.folder.setStyleSheet(self.folder.styleSheet() + ' QTreeWidget {font-family:"%s";}' % ink.MONO)
        self.folder.setHeaderHidden(True)
        self.folder.setTextElideMode(Qt.ElideMiddle)
        self.folder.setAccessibleName('Files in the worksheet’s folder')
        self.folder.itemActivated.connect(self.open_item)
        self.folder.hide()
        self.workflow = QFrame(self)
        self.workflow.setStyleSheet('QFrame {border-top:1px solid %s;} QLabel {font-family:"%s";border:0;}' % (ink.LINE_MID, ink.MONO))
        progress = QVBoxLayout(self.workflow)
        progress.setContentsMargins(0, 7, 0, 4)
        progress.setSpacing(3)
        progress.addWidget(text('[ TASK PROGRESS ]'))
        self.step_labels = [text() for _ in range(4)]
        for label in self.step_labels:progress.addWidget(label)
        self.cabinet_button = QToolButton(self)
        self.cabinet_button.setCheckable(True)
        self.cabinet_button.setToolTip('Show the complete filing cabinet beside the current worksheet')
        self.cabinet_button.toggled.connect(self.show_cabinet)
        self.margin = QWidget(self)
        margin = QVBoxLayout(self.margin)
        margin.setContentsMargins(0, 0, 0, 0)
        margin.addStretch(1)
        self.bracket = PanelInk(self.host, 'bracket')
        margin.addWidget(self.bracket)
        margin.addStretch(1)
        self.show_cabinet(False)
        for widget in (self.workflow, self.cabinet_button, self.margin):widget.hide()
        self.tray.changed.connect(self.update_preview)
        self.sheet_choice.currentIndexChanged.connect(self.show_rows)
        self.watch = QFileSystemWatcher([str(path)], self)
        self.watch.fileChanged.connect(self.source_changed)
        self.show_rows()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.trace.setGeometry(self.rect())
        self.trace.raise_()
        inset = max(8, round((self.height() - 560) * .21))
        if self.layout().contentsMargins().bottom() != inset:
            self.layout().setContentsMargins(0, 0, 0, inset)
        self.size_grid()
        self.fit_controls()
        self.art.refresh()

    def fit_controls(self):
        compact = self.width() < 550
        self.views.setText('Views' if compact else 'File views')
        self.external.setText('[ Full app ↗ ]' if compact else '[ Full spreadsheet ↗ ]')
        short = {'Selected rows': 'Rows', 'Subtract stock': 'Subtract', 'Keep positive': '> 0', 'New CSV': 'CSV'}
        for index in range(self.tray.chips.count()):
            chip = self.tray.chips.itemAt(index).widget()
            if isinstance(chip, QPushButton):
                title = chip.property('worksheetStepTitle') or chip.text()
                chip.setProperty('worksheetStepTitle', title)
                chip.setText(short.get(title, title) if compact else title)

    def show_cabinet(self, expanded):
        self.cabinet_button.setText('▾ Cabinet' if expanded else '› Cabinet')
        if self.host.shell2.worksheet is self:
            self.host.cabinet_page.tree.setVisible(expanded)
            self.margin.setVisible(not expanded)

    def fill_views(self):
        menu = self.views.menu()
        menu.clear()
        for i in range(self.viewer.pages.count()):
            page = self.viewer.pages.widget(i)
            if page is not self:
                menu.addAction(self.viewer.pages.tabText(i), lambda p=page:self.viewer.pages.setCurrentWidget(p))
        menu.addSeparator()
        menu.addAction('Ask about this file', self.viewer.ask_about)
        menu.addAction('Investigate this file', self.viewer.investigate)
        menu.addAction(self.reload_button.text(), self.reload_workbook)

    def workbook_path(self):
        path = files_service.resolve(kernel_of(self.host), self.relative).resolve()
        if path != self.workbook_target or not path.is_file():
            raise ValueError('The workbook moved. Reopen it from Files.')
        return path

    def open_external(self):
        try:
            path = self.workbook_path()
        except (ValueError, OSError) as exc:
            self.host.statusBar().showMessage(str(exc), 8000)
            return
        calc = shutil.which('libreoffice') or shutil.which('soffice')
        if calc and path.suffix.lower() in ('.ods', '.xlsx'):
            opened, _ = QProcess.startDetached(calc, ['--calc', str(path)], str(path.parent))
        else:
            opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        if not opened:
            self.host.statusBar().showMessage('The system could not open the spreadsheet application.', 8000)
            return
        self.external_pending = True
        self.reload_button.setText('Return to sheet')
        self.reload_button.setToolTip('Read the saved workbook after editing it in the full application')
        self.host.statusBar().showMessage('Spreadsheet requested. Save there, then choose Return to sheet.', 8000)

    def reload_workbook(self):
        self.viewer.reload_source(returning=self if self.external_pending else None)

    def finish_handoff(self):
        self.external_pending = False
        self.reload_button.setText('Reload source')
        self.reload_button.setToolTip('')
        if str(self.path) not in self.watch.files():
            self.watch.addPath(str(self.path))
        if self.stale:
            self.stale = False
            self.selection_changed()

    def refresh_folder(self):
        parent = PurePosixPath(self.relative).parent
        rel = '' if parent == PurePosixPath('.') else str(parent)
        try:
            entries = call(self.host, 'files.list', {'path': rel})['entries']
        except (ValueError, OSError):
            entries = []
        self.folder.clear()
        root = QTreeWidgetItem(self.folder, [parent.name or 'Files'])
        root.setData(0, Qt.UserRole, rel)
        entries = sorted(entries, key=lambda entry:entry['path'] != self.relative)
        for entry in entries[:100]:
            name = entry['name']
            child = QTreeWidgetItem(root, [FILE_MARKS.get(entry['kind'], '[.]') + ' ' + name])
            child.setData(0, Qt.UserRole, entry['path'])
            child.setToolTip(0, name + ' · ' + entry['kind_words'])
            child.setData(0, Qt.AccessibleTextRole, name + ' · ' + entry['kind_words'])
            if entry['path'] == self.relative:
                self.folder.setCurrentItem(child)
        root.setExpanded(True)
        height = max(26, self.folder.fontMetrics().height() + 12)
        self.folder.setFixedHeight(min(7, len(entries) + 1) * height + 2)

    def open_item(self, item, column):
        try:
            path = files_service.resolve(kernel_of(self.host), item.data(0, Qt.UserRole))
            if path.is_dir():
                self.host.browse(path)
            else:
                self.host.open_in_viewer(path)
        except (ValueError, OSError) as exc:
            self.host.statusBar().showMessage(str(exc), 8000)

    def show_rows(self, *_):
        self.active_sheet = self.sheet_choice.currentData()
        old = self.grid.model()
        self.model = Rows(self.tables[self.active_sheet], self.grid)
        self.grid.setModel(self.model)
        if old is not None:
            old.deleteLater()
        header = self.grid.horizontalHeader()
        stock = self.stock_fields()
        self.model.stock_grid = stock is not None and self.model.columnCount() == 4
        self.grid.column_weights = ()
        if self.model.stock_grid:
            weights = dict(zip(stock, (34, 24, 24, 18)))
            self.grid.column_weights = tuple(weights[field] for field in self.model.fields)
            header.setSectionResizeMode(QHeaderView.Fixed)
            self.grid.fit_columns()
        else:
            header.setSectionResizeMode(QHeaderView.Stretch if self.model.columnCount() <= 5 else QHeaderView.Interactive)
        self.size_grid()
        self.grid.selectionModel().selectionChanged.connect(self.selection_changed)
        self.selection_changed()

    def size_grid(self):
        row_height = max(35, self.grid.fontMetrics().height() + 13, min(47, round(self.host.height() * .043)))
        gutter = self.grid.verticalHeader()
        gutter.setDefaultSectionSize(row_height)
        gutter.setFixedWidth(max(32, min(59, round(self.width() * .074))))
        rows = max(3, min(9, (self.height() - 150) // (row_height * 2)))
        header = max(41, self.grid.horizontalHeader().sizeHint().height())
        grid_height = rows * row_height + header + 2
        if self.grid.maximumHeight() != grid_height:
            self.grid.setFixedHeight(grid_height)

    def rows_selected(self):
        return sorted(index.row() for index in self.grid.selectionModel().selectedRows())

    def selection_changed(self, *_):
        selected = self.rows_selected()
        self.model.marked = set(selected)
        if self.model.rowCount():
            self.model.headerDataChanged.emit(Qt.Vertical, 0, self.model.rowCount() - 1)
        self.selection.setText('%d row%s selected' % (len(selected), '' if len(selected) == 1 else 's'))
        self.commands.setEnabled(bool(selected) and not self.stale)
        self.tray.reset('Source changed. Reload the worksheet.' if self.stale else 'Select rows, then choose a row command to prepare a preview.')
        self.bracket.set_available(self.host.shell2.worksheet is self and self.stock_fields() is not None)
        self.trace.update()

    def source_changed(self, *_):
        self.stale = True
        self.selection_changed()

    def stock_fields(self):
        fields = {name.casefold(): name for name in self.model.fields if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,79}', name)}
        if {'required', 'available', 'part', 'unit'} <= fields.keys() and 'shortage' not in fields:
            return tuple(fields[key] for key in ('part', 'required', 'available', 'unit'))
        return None

    def program(self, selection):
        sheet, selected = selection
        if self.stale or self.host.shell2.worksheet is not self or sheet != self.active_sheet or selected != self.rows_selected():
            raise ValueError('The worksheet or selected rows changed. Open the row commands again.')
        if not 1 <= len(selected) <= 200:
            raise ValueError('Select between 1 and 200 rows for a chain.')
        args = {'path': self.relative, 'expected_sha256': self.digest}
        if sheet is not None:
            args['sheet'] = sheet
        literal = json.dumps(args, ensure_ascii=True)
        for char in '<>;$`':
            literal = literal.replace(char, '\\u%04x' % ord(char))
        return 'files.get ' + literal + ' | rows | keep rows ' + ','.join(str(r + 1) for r in selected)

    def menu_anchor(self, x):
        populated = self.grid.horizontalHeader().height() + min(5, self.model.rowCount()) * self.grid.verticalHeader().defaultSectionSize()
        return self.grid.mapToGlobal(QPoint(min(x, max(12, min(58, self.grid.width() - 620))), min(self.grid.height(), populated) + 15))

    def row_menu(self, pos):
        index = self.grid.indexAt(pos)
        if index.isValid() and index.row() not in self.rows_selected():
            self.grid.selectRow(index.row())
        self.open_menu(self.menu_anchor(pos.x()))

    def open_menu(self, point):
        from .chain_menu import desk_style, stock_methods
        selected = self.rows_selected()
        if not selected or self.stale:
            return None
        binding = self.active_sheet, selected
        old = getattr(self, 'row_commands', None)
        if old is not None:
            old.close()
            old.deleteLater()
        menu = QMenu(self)
        menu.setAccessibleName('Worksheet row commands')
        self.row_commands = menu
        desk_style(menu, self.host)
        menu.setStyleSheet(menu.styleSheet() + ('QMenu {border:1px solid %s;} '
            'QMenu::item {padding:6px 21px 6px 13px;} '
            'QMenu::item:selected {border:1px solid %s;background:%s;}' % (ink.LINE_MID, ink.AMBER_EDGE, ink.AMBER_SOFT)))
        menu.hovered.connect(self.trace.update)
        menu.aboutToHide.connect(lambda: QTimer.singleShot(0, self.trace.update))
        count = len(selected)
        menu.addAction(f'[ Selection · {count} {"row" if count == 1 else "rows"} ]').setEnabled(False)
        menu.addSeparator()
        fields = self.stock_fields()
        methods = stock_methods(details=True)
        if fields:
            part, required, available, unit = fields
            calculate = QMenu('Calculate', menu)
            difference = QMenu('Required - available', calculate)
            menu.addMenu(calculate)
            calculate.addAction('[ Calculate ]').setEnabled(False)
            calculate.addSeparator()
            calculate.addMenu(difference)
            difference.addAction('[ Then ]').setEnabled(False)
            difference.addSeparator()
            numeric = all(type(value) in (int, float) and math.isfinite(value)
                          for row in selected for value in (self.model.rows[row].get(required), self.model.rows[row].get(available)))
            difference.setEnabled(numeric)
            difference.setToolTip('Each selected row needs numeric Required and Available values.')
            difference.addAction('Keep positive', lambda:self.stage(binding, fields))
            difference.addAction('Keep all differences', lambda:self.stage(binding, fields, positive=False))
        if fields or methods:
            press = QMenu('Method Press', menu)
            menu.addMenu(press)
            if fields:
                keep_method = press.addAction('Keep shortage method…', lambda:self.shortage_method(binding, fields))
                keep_method.setEnabled(numeric)
            for name, unit_name, saved in methods:
                method = dict(saved, name=name) if saved is not None else None
                action = press.addAction(name, lambda checked=False, u=unit_name, m=method:
                                         self.shortage_method(binding, fields, u, method=m))
                tooltip = 'Expected unit ' + unit_name
                if method:
                    tooltip += ' · Kept from ' + method['source']['sha256'][:10]
                action.setToolTip(tooltip)
            retained = [(name, saved) for name, _, saved in methods if saved is not None]
            if retained:
                history = QMenu('Open saved runs', press)
                press.addMenu(history)
                for name, saved in retained:
                    history.addAction(name, lambda checked=False, m=saved:self.open_method_runs(m))
        menu.addAction('Preview selected rows', lambda:self.stage(binding))
        menu.addAction('Preview the plan', lambda:self.preview_plan(binding))
        menu.addAction('Copy the selection as a line', lambda:self.copy_program(binding))
        menu.addSeparator()
        menu.addAction('Inspect source', self.host.shell2.show_context_face)
        menu.addAction('Open full spreadsheet', self.open_external)
        menu.popup(point)
        self.trace.update()
        return menu

    def open_method_runs(self, method):
        from .chain_menu import method_runs
        from .shell2 import open_destination
        folder = method_runs(method)
        try:
            call(self.host, 'files.list', {'path': folder})
        except (OSError, ValueError) as exc:
            detail = str(exc)
            self.host.statusBar().showMessage(
                'No run receipts saved for this method yet.' if 'FILES_NOT_FOUND' in detail else detail, 8000)
            return
        open_destination(self.host, 'files:' + folder)

    def shortage_method(self, binding, fields, expected=None, *, method=None):
        from .chain_menu import STOCK_ROLES, keep
        try:
            self.program(binding)
            if fields is None:
                raise ValueError('Method needs Part, Required, Available and Unit columns.')
            columns = dict(zip(STOCK_ROLES, fields))
            if method and columns != method['columns']:
                raise ValueError('Method columns changed. Review the saved column names and the selected worksheet.')
            if any(type(value) not in (int, float) or not math.isfinite(value)
                   for row in binding[1] for value in (self.model.rows[row].get(fields[1]),
                                                       self.model.rows[row].get(fields[2]))):
                raise ValueError('Each selected row needs numeric Required and Available values.')
            units = {str(self.model.rows[row].get(fields[3]) or '').strip() for row in binding[1]}
            if len(units) != 1 or '' in units or max(map(len, units)) > 80:
                raise ValueError('Choose rows with one explicit unit for this method.')
            unit = units.pop()
            if expected is not None and unit != expected:
                raise ValueError(f'Method expects {expected} but these rows use {unit}. Review the supplier units.')
            if expected is None:
                keep(self.host, '', stock_unit=unit, stock_basis={
                    'columns': columns,
                    'source': {'path': self.relative, 'sha256': self.digest, 'sheet': binding[0],
                               'rows': [row + 1 for row in binding[1]]},
                })
                return
        except (OSError, ValueError) as exc:
            self.tray.reset(str(exc))
            self.host.shell2.show_worksheet_preview()
            return
        self.stage(binding, fields, method=method)

    def copy_program(self, selected):
        from .context_menu import copy_text
        try:
            copy_text(self.host, self.program(selected), 'Copied selected-row chain')
        except ValueError as exc:
            self.tray.note(str(exc))

    def preview_plan(self, selected):
        from .context_menu import say
        from .shell2 import to_console

        try:
            program = self.program(selected)
        except ValueError as exc:
            say(self.host, str(exc))
            return
        to_console(self.host, 'stac', 'explain ' + program)

    def stage(self, selected, fields=None, positive=True, *, method=None):
        try:
            program = self.program(selected)
        except ValueError as exc:
            self.tray.note(str(exc))
            return
        self.rollup_unit = None
        self.part_column = None
        steps = [(2, 'Selected rows')]
        if fields:
            part, required, available, unit = fields
            program += ' | add Shortage = %s - %s' % (required, available)
            steps.append((3, 'Subtract stock'))
            if positive:
                program += ' | where Shortage over 0'
                steps.append((4, 'Keep positive'))
            program += ' | select %s,Shortage,%s' % (part, unit)
            steps.append((steps[-1][0] + 1, 'New CSV'))
            self.rollup_unit = unit
            self.part_column = part
        self.tray.stage(program, display_labels=steps, method=method)
        self.fit_controls()
        self.tray.preview()
        self.host.shell2.show_worksheet_preview()
        self.trace.update()

    def preview_rows(self, rows):
        if not self.rollup_unit:
            return rows
        return [{'Part': row[self.part_column], 'Shortage': ('%s %s' % (row['Shortage'], row.get(self.rollup_unit, ''))).strip()}
                for row in rows]

    def update_preview(self):
        rows = self.tray.rows
        ready = rows is not None and not self.stale
        unit = self.rollup_unit
        self.preview_title.setText('[#] Shortage sheet' if unit and self.tray.program else '[#] Chain preview')
        total = ''
        mixed = False
        if ready and unit and rows:
            units = {str(row.get(unit) or '').strip() for row in rows}
            if len(units) == 1 and '' not in units:
                value = sum((Decimal(str(row['Shortage'])) for row in rows), Decimal(0))
                total = '%s %s' % (format(value.normalize(), 'f'), next(iter(units)))
            else:
                total = 'Mixed or missing units'
                mixed = True
        self.total.setText(total)
        self.total_caption.setVisible(not mixed)
        self.total.setStyleSheet('color:%s;' % (ink.AMBER_TEXT if mixed else ink.READY))
        self.total_bar.setVisible(bool(total))
        self.art.set_available(ready and self.tray.controls['sheet'].isEnabled())
        self.source_state.setText('[~] Source changed' if self.stale else '[+] Source current' if ready else 'Source · ' + self.path.name)
        self.source_state.setStyleSheet('color:%s;' % (ink.AMBER_TEXT if self.stale else ink.READY if ready else ink.QUIET))
        self.source_state.setToolTip(self.relative + (' · ' + self.active_sheet if self.active_sheet else ''))
        done = (not self.stale, not self.stale and bool(self.rows_selected()), ready, ready and bool(self.tray.saved_receipt))
        current = next((i for i, state in enumerate(done) if not state), len(done))
        for i, (label, action) in enumerate(zip(self.step_labels, (
                'Reload workbook' if self.stale else 'Open workbook', 'Select rows', 'Preview result', 'Save sheet'))):
            mark = '[+]' if done[i] else '[>]' if i == current else '[ ]'
            label.setText(mark + ' ' + action)
            label.setStyleSheet('color:%s;' % (ink.READY if done[i] else ink.AMBER_TEXT if i == current else ink.QUIET))
        self.trace.update()
