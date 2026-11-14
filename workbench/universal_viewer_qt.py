"""The universal viewer tab in the center panel: open any file read-only.

Archives and disk images open as trees; double-click a member to open it in
the same viewer, so you can walk from a disk image into a ZIP into a C file.
Nothing is mounted, run or changed. "Save a copy" writes only where you choose.
"""
from pathlib import Path
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QFileDialog, QGraphicsScene, QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget
from . import universal_view as uv


def _mono():
    from .boss_theme import MONO
    return MONO
from .viewer_tabs import SourceHighlighter, ZoomCanvas

LAYER_COLORS = {'Top copper': '#d0703a', 'Bottom copper': '#3a7bd0', 'Inner copper': '#b0a040', 'Top silkscreen': '#f2f2f2',
                'Bottom silkscreen': '#c8c8f0', 'Top solder mask': '#2f8f4f', 'Bottom solder mask': '#2f6f8f', 'Top paste': '#a0a0a0',
                'Bottom paste': '#808080', 'Board outline': '#e8d44d', 'Drill': '#101216', 'Layer': '#c06090'}
KIND_LABELS = {'text': 'Text', 'code': 'Source code', 'markdown': 'Markdown', 'json': 'JSON', 'csv': 'Table (CSV)', 'pdf': 'PDF', 'image': 'Image',
               'document': 'Office document', 'zip': 'ZIP archive', 'tar': 'TAR archive', 'gzip': 'gzip', 'bzip2': 'bzip2', 'xz': 'xz',
               'fat': 'FAT disk image', 'disk': 'Whole-disk image', 'ntfs': 'NTFS disk image', 'ext': 'Linux ext disk image', 'iso': 'ISO disc image',
               'archive7z': '7z / RAR archive', 'exfat': 'exFAT disk image', 'elf': 'ELF program', 'sqlite': 'SQLite database', 'gerber': 'Gerber layer',
               'excellon': 'Drill file', 'step': 'STEP model', 'stl': 'STL model', 'kicad': 'KiCad file', 'binary': 'Unidentified binary'}
from .view_modules import LABELS as _MODULE_LABELS  # noqa: E402
KIND_LABELS.update(_MODULE_LABELS)
AFTER_CORE = {'Adjust'}


class UniversalViewerTab(QWidget):
    def __init__(self, host, path, address=None, origin=None):
        super().__init__()
        self.host = host;self.root_path = Path(path);self.stack = [];self.address = address;self.origin = origin
        self.setAcceptDrops(True);self.setObjectName('ItemView')
        outer = QVBoxLayout(self);outer.setContentsMargins(20, 12, 20, 8);outer.setSpacing(8)
        # The item header every open item shares: where it came from · what it is · its staC address · Ask about this.
        self.crumbs = QLabel();self.crumbs.setWordWrap(True);self.crumbs.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.crumbs.setStyleSheet('color:#6c675e');outer.addWidget(self.crumbs)
        self.item_toolbar = QWidget()
        top = QHBoxLayout(self.item_toolbar);top.setContentsMargins(0, 0, 0, 0);top.setSpacing(10)
        self.back = QPushButton('◀');self.back.setToolTip('Back to the containing archive');self.back.setAccessibleName('Back to the containing archive');self.back.clicked.connect(self.go_back);top.addWidget(self.back)
        self.heading = QLabel();self.heading.setObjectName('ItemTitle');top.addWidget(self.heading)
        self.kind_chip = QLabel();self.kind_chip.setObjectName('KindChip');top.addWidget(self.kind_chip)
        self.address_chip = QPushButton();self.address_chip.setObjectName('AddressChip');self.address_chip.setToolTip('Address · click to copy')
        self.address_chip.clicked.connect(self.copy_address);top.addWidget(self.address_chip)
        top.addStretch(1)
        self.ask_button = QPushButton('Ask about this');self.ask_button.setProperty('arcButton', 'warm');self.ask_button.clicked.connect(self.ask_about);top.addWidget(self.ask_button)
        self.investigate_button = QPushButton('Investigate');self.investigate_button.setToolTip('Start an investigation with this file as its first source')
        self.investigate_button.clicked.connect(self.investigate);top.addWidget(self.investigate_button)
        self.receive_button = QPushButton('Receive into Office');self.receive_button.setToolTip('Receive this file into the Office: revive, catalog and read it.')
        self.receive_button.clicked.connect(self.receive);top.addWidget(self.receive_button)
        self.save_button = QPushButton('Save a copy…');self.save_button.clicked.connect(self.save_copy);top.addWidget(self.save_button)
        self.native_button = QPushButton('Open in Graphite');self.native_button.clicked.connect(self.open_native);top.addWidget(self.native_button)
        # 0.8.3 review: at 1366 the row's buttons were cut mid-word ("Ask about th", "Receive int") and its least width
        # narrowed the whole desk (both panes, her hologram, the band's words). The row now never sets a least width: the
        # actions that fit its width show, in their order, and the rest wait behind More… (fold_actions).
        from PySide6.QtWidgets import QMenu, QSizePolicy
        self.actions_row = (self.ask_button, self.investigate_button, self.receive_button, self.save_button, self.native_button)
        for b in self.actions_row:b.setProperty('wanted', True)
        self.more_button = QPushButton('More…');self.more_button.setAccessibleName('More actions for this file')
        self.more_menu = QMenu(self.more_button);self.more_button.setMenu(self.more_menu);top.addWidget(self.more_button);self.more_button.hide()
        self.item_toolbar.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);self.item_toolbar.installEventFilter(self)
        outer.addWidget(self.item_toolbar)
        self.notice = QLabel();self.notice.setWordWrap(True);self.notice.setStyleSheet('color:#504d46');outer.addWidget(self.notice)
        self.pages = QTabWidget();self.pages.setAccessibleName('Ways to view this file');outer.addWidget(self.pages, 1)
        self.footer = QLabel('Read-only. Nothing is mounted, run or changed.')
        self.footer.setStyleSheet('color:#6c675e');outer.addWidget(self.footer)
        self.worksheet = None
        self.pages.currentChanged.connect(self.active_page_changed)
        self.push(uv.Source.file(path), self.root_path.name)

    def title(self):return self.root_path.name

    def eventFilter(self, watched, event):
        from PySide6.QtCore import QEvent
        if watched is getattr(self, 'item_toolbar', None) and event.type() == QEvent.Resize:self.fold_actions()
        return super().eventFilter(watched, event)

    def fold_actions(self):
        """The header's actions that fit its width now, in their order; the rest behind More… (one menu line each)."""
        bar = getattr(self, 'item_toolbar', None)
        if bar is None:return
        gap = bar.layout().spacing()
        fixed = sum(w.sizeHint().width() + gap for w in (self.back, self.heading, self.kind_chip, self.address_chip) if not w.isHidden())
        wanted = [b for b in self.actions_row if b.property('wanted')];widths = [b.sizeHint().width() + gap for b in wanted]
        room = bar.width() - fixed;shown = len(wanted)
        if sum(widths) > room:
            room -= self.more_button.sizeHint().width() + gap;shown = used = 0
            while shown < len(wanted) and used + widths[shown] <= room:used += widths[shown];shown += 1
        for b in self.actions_row:
            want = b in wanted and wanted.index(b) < shown
            if b.isHidden() == want:b.setVisible(want)
        self.more_menu.clear()
        for b in wanted[shown:]:self.more_menu.addAction(b.text(), b.click)
        if self.more_button.isHidden() == (shown < len(wanted)):self.more_button.setVisible(shown < len(wanted))

    def inspector(self):
        view = getattr(self, 'view', None) or {}
        sections = [('Kind', KIND_LABELS.get(view.get('kind'), view.get('kind', ''))), ('Where', '  ›  '.join(l for _, l, _ in self.stack))]
        sections += [(k, str(v)) for k, v in view.get('summary', [])[:8]]
        if view.get('notice'):sections.append(('Note', view['notice']))
        if view.get('sha256'):sections.append(('SHA-256', view['sha256'][:32] + '…'))
        from .shell2 import Note
        sections.append(('Read-only', Note('Nothing is mounted, run or changed.')))  # a reassurance you may skip: the script
        return 'Viewer · ' + view.get('name', self.root_path.name), sections

    def info(self):return 'Universal viewer · ' + (KIND_LABELS.get(self.view.get('kind'), '') if hasattr(self, 'view') else '') + ' · read-only'

    # Navigation -----------------------------------------------------------

    def push(self, source, label):
        try:view = uv.describe(source)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, 'Cannot open', str(exc));return
        self.stack.append((source, label, view));self.show_view()

    def go_back(self):
        if len(self.stack) > 1:self.stack.pop();self.show_view()

    def reload_source(self, *, returning=None):
        try:
            path = returning.workbook_path() if returning is not None else self.root_path
            before = path.stat() if returning is not None else None
            source = uv.Source.file(path)
            view = uv.describe(source)
            if before is not None:
                after = path.stat()
                fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
                if any(getattr(before, field) != getattr(after, field) for field in fields):
                    raise ValueError('The workbook changed while it was being read. Choose Return to sheet again.')
        except (ValueError, OSError) as exc:
            self.host.statusBar().showMessage(str(exc), 8000)
            return
        if returning is not None and view.get('sha256') == returning.digest:
            returning.finish_handoff()
            self.host.statusBar().showMessage('Workbook revision confirmed.', 8000)
            return
        sheet = returning.active_sheet if returning is not None else None
        self.stack = [(source, self.root_path.name, view)]
        self.show_view()
        if returning is not None and self.worksheet is not None:
            choice = self.worksheet.sheet_choice
            index = choice.findData(sheet)
            if index >= 0:
                choice.setCurrentIndex(index)
            self.host.statusBar().showMessage('Saved workbook reloaded. Select rows for this revision.', 8000)

    def active_page_changed(self, *_):
        compact = self.worksheet is not None and self.pages.currentWidget() is self.worksheet
        self.item_toolbar.setVisible(not compact)
        self.crumbs.setVisible(not compact)
        self.notice.setVisible(not compact and bool(self.notice.text()))
        self.footer.setVisible(not compact)
        self.pages.tabBar().setVisible(not compact)
        shell = getattr(self.host, 'shell2', None)
        if shell is not None:
            shell.sync_worksheet()

    def show_view(self):
        source, label, view = self.stack[-1];self.source, self.view = source, view
        self.back.setEnabled(len(self.stack) > 1)
        trail = [l for _, l, _ in self.stack]
        if self.origin:trail[0] = self.origin
        self.crumbs.setText('  ›  '.join(trail))
        self.heading.setText(view['name']);self.kind_chip.setText(KIND_LABELS.get(view['kind'], view['kind']))
        top_level = len(self.stack) == 1
        self.address_chip.setVisible(bool(self.address and top_level));self.address_chip.setText('@' + (self.address or '')[:22] + ('…' if self.address and len(self.address) > 22 else ''))
        self.notice.setText(view.get('notice') or '');self.notice.setVisible(bool(view.get('notice')))
        top = len(self.stack) == 1
        self.receive_button.setProperty('wanted', top and not self.address);self.save_button.setProperty('wanted', not top)
        self.native_button.setProperty('wanted', top and self.native_target() is not None);self.fold_actions()
        self.worksheet = None
        self.pages.blockSignals(True)
        self.active_page_changed()
        while self.pages.count():
            widget = self.pages.widget(0);self.pages.removeTab(0);widget.deleteLater()
        if top:
            from .sheet_workbench_qt import make
            self.worksheet = make(self)
            if self.worksheet is not None:self.pages.addTab(self.worksheet, 'Worksheet')
        for title, build in self.page_builders(view):
            try:self.pages.addTab(build(), title)
            except (ValueError, OSError) as exc:
                self.pages.addTab(QLabel('This view could not be drawn: ' + str(exc)), title)
        self.pages.addTab(self.details_page(view), 'Details')
        self.pages.blockSignals(False)
        self.active_page_changed()
        inspector = getattr(self.host, 'arc_inspector', None)
        if inspector is not None and self.host.tabs.currentWidget() is self:inspector.refresh()
        if hasattr(self.host, 'update_document_info'):
            try:self.host.update_document_info()
            except Exception:pass

    def page_builders(self, view):
        from .view_modules import pages as module_pages
        found = module_pages(self, view)
        pages = [p for p in found if p[0] not in AFTER_CORE]  # a module's own view comes first: the reading, the sheet, the model, the drawing, the player
        if view.get('tree') is not None:pages.append(('Contents', self.tree_page))
        if view.get('gerber'):pages.append(('Board view', self.gerber_page))
        if view.get('pdf'):pages.append(('Pages', self.pdf_page))
        if view.get('image'):pages.append(('Image', self.image_page))
        if view.get('table'):pages.append(('Table', self.table_page))
        if view.get('text') is not None:pages.append(('Text', self.text_page))
        pages += [p for p in found if p[0] in AFTER_CORE]  # tools that work on what the core page shows (Adjust after Image)
        pages.append(('Hex', self.hex_page))
        return pages

    # Pages ----------------------------------------------------------------

    def details_page(self, view):
        rows = [('Kind', KIND_LABELS.get(view['kind'], view['kind']))] + list(view['summary']) + [('SHA-256', view.get('sha256') or '')]
        table = QTableWidget(len(rows), 2);table.setHorizontalHeaderLabels(['', '']);table.verticalHeader().hide();table.horizontalHeader().hide()
        for i, (k, v) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(k));table.setItem(i, 1, QTableWidgetItem(str(v)))
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch);table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAccessibleName('File details');return table

    def text_page(self):
        editor = QPlainTextEdit();editor.setReadOnly(True);editor.setAccessibleName('File text');editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        font = QFont(_mono());font.setStyleHint(QFont.Monospace);editor.setFont(font)
        editor.setPlainText(self.view['text'])
        if self.view['kind'] in ('code', 'json', 'sqlite'):
            editor._highlighter = SourceHighlighter(editor.document(), uv.Path(self.view['name']).suffix or '.c')
        return editor

    def hex_page(self):
        editor = QPlainTextEdit();editor.setReadOnly(True);editor.setAccessibleName('File bytes in hexadecimal')
        font = QFont(_mono());font.setStyleHint(QFont.Monospace);editor.setFont(font)
        def fill():
            if not editor.toPlainText():
                raw = self.source.read(0, uv.MAX_HEX)
                editor.setPlainText(uv.hexdump(raw) + ('\n… first %s of %s shown' % (uv.human(len(raw)), uv.human(self.source.size)) if self.source.size > len(raw) else ''))
        QTimer.singleShot(0, fill);return editor

    def table_page(self):
        data = self.view['table'];table = QTableWidget(len(data['rows']), len(data['columns']))
        table.setHorizontalHeaderLabels([str(c) for c in data['columns']]);table.setEditTriggers(QTableWidget.NoEditTriggers)
        for r, row in enumerate(data['rows']):
            for c, value in enumerate(row):table.setItem(r, c, QTableWidgetItem(str(value)))
        table.setAccessibleName('File table');return table

    def tree_page(self):
        page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(0, 0, 0, 0)
        tree = QTreeWidget();tree.setHeaderLabels(['Name', 'Size', 'Note']);tree.setColumnWidth(0, 360);tree.setColumnWidth(1, 110);tree.setAccessibleName('Contents')
        folders = {}
        def folder(path):
            if not path:return tree.invisibleRootItem()
            if path not in folders:
                parent, _, leaf = path.rpartition('/')
                item = QTreeWidgetItem([leaf, '', '']);folder(parent).addChild(item);folders[path] = item
            return folders[path]
        for e in self.view['tree']:
            parent, _, leaf = e['path'].rpartition('/')
            if e['directory']:
                item = folder(e['path'])
                if e.get('note'):item.setText(2, e['note'])
                continue
            item = QTreeWidgetItem([leaf, uv.human(e['size']) if e['size'] >= 0 else '', e.get('note', '')]);item.setData(0, Qt.UserRole, e['path'])
            folder(parent).addChild(item)
        if len(self.view['tree']) < 400:tree.expandAll()
        tree.itemActivated.connect(lambda item, column:self.open_member(item.data(0, Qt.UserRole)))
        box.addWidget(tree, 1)
        row = QHBoxLayout();open_button = QPushButton('Open selected');open_button.clicked.connect(lambda:self.open_member(tree.currentItem().data(0, Qt.UserRole) if tree.currentItem() else None))
        row.addWidget(open_button)
        gerbers = [e['path'] for e in self.view['tree'] if not e['directory'] and Path(e['path']).suffix.lower() in ('.gbr', '.ger', '.gtl', '.gbl', '.gto', '.gbo', '.gts', '.gbs', '.gko', '.gm1', '.drl', '.xln')]
        if len(gerbers) > 1:
            board = QPushButton('Show all %d Gerber and drill layers as one board' % len(gerbers));board.clicked.connect(lambda:self.open_board(gerbers));row.addWidget(board)
        row.addStretch(1);box.addLayout(row)
        return page

    def open_member(self, path):
        if not path:return
        try:child = uv.member(self.source, path)
        except (ValueError, OSError, KeyError) as exc:
            QMessageBox.warning(self, 'Cannot open', str(exc));return
        self.push(child, path)

    def open_board(self, paths):
        try:
            sources = [uv.member(self.source, p) for p in paths]
            view = {'schema': 'arc.universal-view/1', 'name': 'Board · %d layers' % len(paths), 'kind': 'gerber', 'size': sum(s.size for s in sources),
                    'sha256': None, 'summary': [('Layers', ', '.join(Path(p).name for p in paths))], 'notice': None, 'gerber': uv.board(sources)}
        except (ValueError, OSError, KeyError) as exc:
            QMessageBox.warning(self, 'Cannot draw the board', str(exc));return
        self.stack.append((self.source, 'Board view', view));self.show_view()

    def gerber_page(self):
        data = self.view['gerber'];page = QWidget();box = QHBoxLayout(page);box.setContentsMargins(0, 0, 0, 0)
        scene = QGraphicsScene(page);canvas = ZoomCanvas(scene);canvas.setAccessibleName('Board drawing');items = []
        layers = QListWidget();layers.setMaximumWidth(220);layers.setAccessibleName('Layers')
        for layer in data['layers']:
            group = self.draw_layer(scene, layer);items.append(group)
            entry = QListWidgetItem(layer['role'] + ' · ' + Path(layer['name']).name);entry.setFlags(entry.flags() | Qt.ItemIsUserCheckable)
            label_color = '#e8e8e8' if layer['role'] == 'Drill' else LAYER_COLORS.get(layer['role'], '#c06090')
            entry.setCheckState(Qt.Checked);entry.setForeground(QBrush(QColor(label_color)));layers.addItem(entry)
        layers.itemChanged.connect(lambda entry:items[layers.row(entry)].setVisible(entry.checkState() == Qt.Checked))
        canvas.scale(1, -1)  # Gerber Y points up
        box.addWidget(layers);box.addWidget(canvas, 1);self.fit_when_shown(canvas)
        return page

    def fit_when_shown(self, canvas):
        """Fit once the canvas has its real size, and again whenever its page is shown."""
        def fit():
            if canvas.isVisible() and canvas.viewport().width() > 50:
                bounds = canvas.scene().itemsBoundingRect()
                if not bounds.isValid() or bounds.isEmpty():return
                margin = max(bounds.width(), bounds.height()) * 0.04  # proportional: boards are in millimetres, images in pixels
                flip = canvas.transform().m22() < 0
                canvas.fitInView(bounds.adjusted(-margin, -margin, margin, margin), Qt.AspectRatioMode.KeepAspectRatio)
                if flip and canvas.transform().m22() > 0:canvas.scale(1, -1)
        for delay in (50, 250):QTimer.singleShot(delay, fit)
        self.pages.currentChanged.connect(lambda index:QTimer.singleShot(30, fit))

    @staticmethod
    def draw_layer(scene, layer):
        color = QColor(LAYER_COLORS.get(layer['role'], '#c06090'));group = scene.createItemGroup([])
        clear = QColor('#101216')
        def brush(polarity):return QBrush(color if polarity != 'C' else clear)
        for x1, y1, x2, y2, width, polarity in layer['lines']:
            pen = QPen(color if polarity != 'C' else clear, max(width, 0.01));pen.setCapStyle(Qt.RoundCap)
            group.addToGroup(scene.addLine(x1, y1, x2, y2, pen))
        for x, y, (shape, params), polarity in layer['flashes']:
            w = params[0] if params else 0.5;h = params[1] if len(params) > 1 else w
            if shape == 'R':item = scene.addRect(QRectF(x - w / 2, y - h / 2, w, h), QPen(Qt.NoPen), brush(polarity))
            elif shape == 'O':
                path = QPainterPath();r = min(w, h) / 2;path.addRoundedRect(QRectF(x - w / 2, y - h / 2, w, h), r, r)
                item = scene.addPath(path, QPen(Qt.NoPen), brush(polarity))
            else:item = scene.addEllipse(QRectF(x - w / 2, y - w / 2, w, w), QPen(Qt.NoPen), brush(polarity))
            group.addToGroup(item)
        for points, polarity in layer['regions']:
            group.addToGroup(scene.addPolygon(QPolygonF([QPointF(px, py) for px, py in points]), QPen(Qt.NoPen), brush(polarity)))
        for x, y, diameter in layer.get('holes', []):
            group.addToGroup(scene.addEllipse(QRectF(x - diameter / 2, y - diameter / 2, diameter, diameter), QPen(QColor('#e8e8e8'), 0.03), QBrush(clear)))
        return group

    def pdf_page(self):
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtPdfWidgets import QPdfView
        self._pdf = QPdfDocument(self)
        if self.source.path is not None:self._pdf.load(str(self.source.path))
        else:
            self._pdf_bytes = QByteArray(self.source.read());self._pdf_buffer = QBuffer(self._pdf_bytes);self._pdf_buffer.open(QIODevice.ReadOnly)
            self._pdf.load(self._pdf_buffer)
        view = QPdfView();view.setDocument(self._pdf);view.setPageMode(QPdfView.PageMode.MultiPage);view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        view.setAccessibleName('PDF pages');return view

    def image_page(self):
        pix = QPixmap()
        if not pix.loadFromData(self.source.read()) or pix.width() * pix.height() > 64_000_000:raise ValueError('This image could not be decoded')
        scene = QGraphicsScene(self);scene.addPixmap(pix);canvas = ZoomCanvas(scene);canvas.setAccessibleName('Image')
        self.fit_when_shown(canvas);return canvas

    # Actions --------------------------------------------------------------

    def native_target(self):
        """The Ledger tool that can also open this file, when it is in the workspace."""
        kind = self.stack[0][2]['kind'] if self.stack else None
        root = getattr(self.host, 'root', None)
        if root is None or kind not in ('kicad', 'stl', 'step', 'code', 'text', 'markdown', 'json', 'csv', 'document'):return None
        try:self.root_path.resolve().relative_to(Path(root).resolve())
        except ValueError:return None
        return self.root_path

    def open_native(self):
        target = self.native_target()
        if target is not None:self.host.open_document(target, viewer=False)

    def receive(self):
        bridge = getattr(self.host, 'ledger_bridge', None)
        if bridge is None:return
        office = bridge.navigation()['office']()
        office.receive(str(self.root_path))

    def copy_address(self):
        if self.address:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText('@' + self.address);self.notice.setText('Copied @' + self.address);self.notice.setVisible(True)

    def investigate(self):
        from .investigations_qt import investigate
        return investigate(self.host, self.address, self.root_path.name)

    def ask_about(self):
        shell = getattr(self.host, 'shell2', None)
        if shell is None:return
        what = self.view.get('name', self.root_path.name) + (' (@' + self.address + ')' if self.address else '')
        shell.show_slate_face();shell.face.input.setText('About ' + what + ': ');shell.face.input.setFocus()

    def save_copy(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Save a copy', str(Path.home() / self.view['name']))
        if not path:return
        target = Path(path)
        if target.exists():
            QMessageBox.warning(self, 'Save a copy', 'Choose a new file name; existing files are not replaced.');return
        target.write_bytes(self.source.read())
        self.notice.setText('Saved a copy to ' + str(target));self.notice.setVisible(True)

    # Drop a file onto the viewer to open it here ------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1 and event.mimeData().urls()[0].isLocalFile():event.acceptProposedAction()

    def dropEvent(self, event):
        path = Path(event.mimeData().urls()[0].toLocalFile())
        if path.is_file():
            self.root_path = path;self.stack = [];self.push(uv.Source.file(path), path.name);event.acceptProposedAction()
