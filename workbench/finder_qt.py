"""The Finder (HATCH AGENT-01, UI-04): Home is a Finder window in the Macintosh shape, hosted in the centre of the unchanged frame.

The owner's words: "the empty workspace, if nothing is being worked on, is essentially our Finder window or our Explorer
of files on the computer, but mostly done in the Macintosh format. So we have always information in the workspace."

  Places      Today (the existing TodayPage, unchanged) · Files · Ingress · Egress · Workspace · Program · each storage mount.
              The left column is the sidebar: what the owner selects there decides what the centre shows (the hooks in
              navigation_qt, machine_qt and cabinet_qt call `show_place`, only while Home is active).
  Toolbar     back · forward · the place's name · Icons | List | Columns · Hidden · Preview · Places ▾
  Views       one listing model filled from `ledger.browse` through the Kernel (never os.listdir in a widget), shown as a
              List (Name · Date Modified · Size · Kind, sortable, folders first), Icons (tiles with the kind word) or
              Columns (Miller columns; the preview is the last column). At most 500 entries, then a line offering 2000.
  Preview     kind glyph or a bounded image thumbnail (longest side 512), name, kind, size, modified and created; for
              text under 64 KB the first forty lines, read-only. The pane reads the file head itself; it writes nothing.
  Path bar    at the bottom, clickable segments (Mac puts it there); then the status line:
              "23 items · 118 GB available on this disk · observed from this computer".
  Keyboard    Enter opens (editor for text inside the workspace, viewer otherwise; folders descend), Backspace or Alt Up
              goes up, Space shows or hides the preview, Alt Left / Alt Right back and forward, typing selects by name.
  Narrow      (GRAPHITE-01, G-B) every word stays whole: the toolbar keeps its words while they fit and folds the least-used
              ones into ⋯ (Hidden, then Places, then Preview, then the three views); the place name elides last, whole in its
              tooltip; the List folds Kind, then Date Modified, then Size (the preview pane shows all three); the path bar
              folds its leading folders into … . Nothing scrolls sideways but the Columns view and a text preview's lines.

Nothing here creates, renames, moves or deletes: those remain the Files room's own operations, and the context menu says
"Change it in Files" where that applies. History lives in memory; the last place and view are written to the session
state under 'finder'. Colours are the page's graphite, pencil yellow and eraser pink; nothing new.
"""
from __future__ import annotations
from .assistant_identity import named
import os
import time
from pathlib import Path
from PySide6.QtCore import QEvent, QObject, QPointF, QSize, Qt, QRect, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QImageReader, QPainter, QPen, QPixmap, QPolygonF, QGuiApplication
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem, QMenu,
                               QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSplitter, QStackedWidget, QStyle, QStyledItemDelegate,
                               QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
from .boss_theme import CUE as AMBER      # 0.8.3: its drawn icons are not highlights
from .shell2 import CARD, ERASER_MARK, FAINT, LINE, LINE_STRONG, QUIET, RAISED, TEXT, TodayPage, kind_of, mono_font, role, sentence
from .engineering_kernel import operator
from .files_qt import size_words, when
from . import machine_overview

TODAY = 'today'
VIEWS = ('icons', 'list', 'columns')
VIEW_WORDS = {'icons': 'Icons', 'list': 'List', 'columns': 'Columns'}
DEFAULT_LIMIT, MORE_LIMIT = 500, 2000
PREVIEW_TEXT_BYTES, PREVIEW_LINES, THUMB_SIDE = 64 * 1024, 40, 512
ENTRY = Qt.UserRole + 11
COLUMN_WIDTH = 236
MAX_COLUMNS = 8
FOLD_ORDER = ('hidden', 'places', 'preview', 'views')  # the least-used toolbar words fold into ⋯ first
LIST_FOLD = (3, 1, 2)                                  # then the List's Kind, Date Modified, Size (the preview shows all three)
NAME_ROOM = 150                                        # the List's Name keeps at least this much room (at 14 pt)
LIST_WIDTHS = {1: 120, 2: 100, 3: 180}                 # Date Modified, Size, Kind at 14 pt; scaled with the interface, as NAME_ROOM is
FOLD_WORDS = {'hidden':'Hidden', 'places':'Places', 'preview':'Preview', 'views':'Icons · List · Columns'}
TEXT_SUFFIXES = {'.txt', '.md', '.markdown', '.rst', '.csv', '.tsv', '.json', '.yaml', '.yml', '.toml', '.ini', '.xml', '.html', '.htm', '.log', '.sh', '.py',
                 '.c', '.h', '.cpp', '.hpp', '.cc', '.js', '.ts', '.rs', '.go', '.java', '.cs', '.v', '.sv', '.vhd', '.s', '.asm', '.ld', '.sql', '.lua', '.cfg', '.conf', '.find'}
KIND_WORDS = {'.txt': 'Plain text', '.md': 'Markdown text', '.markdown': 'Markdown text', '.pdf': 'PDF document', '.docx': 'Word document', '.doc': 'Word document',
              '.odt': 'Text document', '.rtf': 'Rich text', '.pptx': 'Presentation', '.xlsx': 'Spreadsheet', '.ods': 'Spreadsheet', '.csv': 'Comma-separated values',
              '.tsv': 'Tab-separated values', '.html': 'Web page', '.htm': 'Web page', '.json': 'JSON data', '.yaml': 'YAML data', '.yml': 'YAML data', '.toml': 'TOML data',
              '.ini': 'Settings text', '.xml': 'XML data', '.py': 'Python source', '.c': 'C source', '.h': 'C header', '.cpp': 'C++ source', '.hpp': 'C++ header',
              '.js': 'JavaScript source', '.ts': 'TypeScript source', '.rs': 'Rust source', '.go': 'Go source', '.sh': 'Shell script', '.sql': 'SQL text',
              '.png': 'PNG image', '.jpg': 'JPEG image', '.jpeg': 'JPEG image', '.gif': 'GIF image', '.bmp': 'Bitmap image', '.webp': 'WebP image', '.svg': 'SVG drawing',
              '.zip': 'ZIP archive', '.tar': 'Tar archive', '.gz': 'Compressed file', '.tgz': 'Compressed archive', '.xz': 'Compressed file', '.7z': '7-Zip archive',
              '.img': 'Disk image', '.iso': 'Disc image', '.sqlite': 'SQLite database', '.db': 'Database', '.gbr': 'Gerber layer', '.kicad_pcb': 'KiCad board',
              '.kicad_sch': 'KiCad schematic', '.step': 'STEP model', '.stp': 'STEP model', '.stl': 'STL mesh', '.gguf': 'Model weights', '.pill': 'Pill'}
FAMILY_WORDS = {'documents': 'Document', 'code': 'Source code', 'boards': 'Board or CAD file', 'images': 'Image', 'containers': 'Archive or disk image', 'other': 'File'}
_GLYPHS = {}


def kind_word(entry):
    """The Kind column in words: Folder, Link, or the file's kind by its name."""
    kind = entry.get('kind')
    if kind == 'folder':return 'Folder'
    if kind == 'link':return 'Link'
    if kind == 'other':return 'Other'
    suffix = Path(entry.get('name', '')).suffix.lower()
    if suffix in KIND_WORDS:return KIND_WORDS[suffix]
    family = kind_of(entry.get('name', ''))
    if family == 'other' and suffix:return suffix[1:].upper()[:8] + ' file'
    return FAMILY_WORDS.get(family, 'File')


def glyph_kind(entry):
    if entry.get('kind') in ('folder', 'link', 'other'):return entry['kind']
    return 'image' if kind_of(entry.get('name', '')) == 'images' else 'file'


def glyph(kind, size=20):
    """A drawn kind glyph in graphite with a pencil-yellow folder; cached by kind and size. No icon files, no new colours."""
    key = (kind, size)
    if key in _GLYPHS:return _GLYPHS[key]
    pixmap = QPixmap(size, size);pixmap.fill(Qt.transparent);p = QPainter(pixmap);p.setRenderHint(QPainter.Antialiasing);s = size / 20.0
    pen = QPen(QColor(LINE_STRONG), max(1.0, 1.1 * s));pen.setJoinStyle(Qt.RoundJoin);p.setPen(pen)
    if kind == 'folder':
        p.setBrush(QColor(AMBER));p.drawRoundedRect(2 * s, 5 * s, 16 * s, 12 * s, 2 * s, 2 * s)
        p.drawRoundedRect(2 * s, 3.5 * s, 7 * s, 4 * s, 1.5 * s, 1.5 * s)
    else:
        p.setBrush(QColor(CARD));p.drawPolygon(QPolygonF([QPointF(x * s, y * s) for x, y in ((4, 2), (12, 2), (16, 6), (16, 18), (4, 18))]))
        p.drawLine(12 * s, 2 * s, 12 * s, 6 * s);p.drawLine(12 * s, 6 * s, 16 * s, 6 * s)
        if kind == 'image':
            p.setBrush(QColor(AMBER));p.drawEllipse(6.5 * s, 8 * s, 3 * s, 3 * s);p.drawLine(5 * s, 16 * s, 9 * s, 11.5 * s);p.drawLine(9 * s, 11.5 * s, 11.5 * s, 14 * s);p.drawLine(11.5 * s, 14 * s, 15 * s, 10 * s)
        elif kind == 'link':
            p.setPen(QPen(QColor(ERASER_MARK), max(1.0, 1.4 * s)));p.drawLine(7 * s, 14 * s, 13 * s, 8 * s);p.drawLine(9.5 * s, 8 * s, 13 * s, 8 * s);p.drawLine(13 * s, 8 * s, 13 * s, 11.5 * s)
        elif kind == 'other':
            p.drawLine(7 * s, 12 * s, 13 * s, 12 * s)
        else:
            for y in (9, 12, 15):p.drawLine(7 * s, y * s, 13 * s, y * s)
    p.end();_GLYPHS[key] = pixmap;return pixmap


def bold_room(button):
    """A checked push button is drawn at weight 600 (theme2) but sized at 400: keep room for the bold word, so a chosen view
    or filter is never clipped. Measured with the polished font (the style sheet's size), so call it again after a restyle."""
    button.ensurePolished();font = QFont(button.font());font.setWeight(QFont.DemiBold);plain = button.fontMetrics().horizontalAdvance(button.text())
    need = button.sizeHint().width() + QFontMetrics(font).horizontalAdvance(button.text()) - plain
    if button.minimumWidth() != need:button.setMinimumWidth(need)


class BoldRoom(QObject):
    """bold_room again whenever the button's font or style changes (the interface size), for checked words outside the Finder."""

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):bold_room(watched)
        return False


def keep_bold_room(*buttons):
    for b in buttons:b.installEventFilter(BoldRoom(b));bold_room(b)


def space_words(count):
    """118 GB, 9.5 GB, 512 MB: the status line's disk words (decimal, as a disk is sold)."""
    if count is None:return 'space not observed'
    value = float(count)
    for unit in ('bytes', 'kB', 'MB', 'GB', 'TB'):
        if value < 1000 or unit == 'TB':return ('%d %s' % (value, unit)) if unit == 'bytes' else (('%.1f %s' if value < 10 else '%.0f %s') % (value, unit))
        value /= 1000


def inside(path, base):
    try:return Path(path).resolve().is_relative_to(Path(base).resolve())
    except (OSError, ValueError, RuntimeError):return False


def looks_textual(path, size):
    """Text under the preview bound: by name, or by a sniff of the first bytes (no NUL, decodable)."""
    if size is None or size > PREVIEW_TEXT_BYTES:return False
    if Path(path).suffix.lower() in TEXT_SUFFIXES:return True
    try:
        with open(path, 'rb') as handle:head = handle.read(4096)
    except OSError:return False
    if b'\0' in head:return False
    try:head.decode('utf-8');return True
    except UnicodeDecodeError:return False


class FinderItem(QTreeWidgetItem):
    """A List row that sorts folders first whatever the column or direction, names naturally, sizes and dates by value."""

    def __lt__(self, other):
        tree = self.treeWidget();column = tree.sortColumn() if tree else 0
        descending = tree is not None and tree.header().sortIndicatorOrder() == Qt.DescendingOrder
        a, b = self.data(0, ENTRY) or {}, other.data(0, ENTRY) or {}
        fa, fb = a.get('kind') == 'folder', b.get('kind') == 'folder'
        if fa != fb:return (not fa) if descending else fa
        keys = {0: lambda e:(machine_overview.natural(e.get('name', '')), e.get('name', '')), 1: lambda e:(e.get('modified') or 0.0),
                2: lambda e:(e.get('bytes') if e.get('bytes') is not None else -1), 3: lambda e:(kind_word(e).casefold(), machine_overview.natural(e.get('name', '')))}
        key = keys.get(column, keys[0]);return key(a) < key(b)


class TileDelegate(QStyledItemDelegate):
    """Icons view: the glyph, the name on up to two lines, and the kind word beneath in the quiet graphite."""

    def __init__(self, parent, scale=1.0):
        super().__init__(parent);self.scale = scale

    def paint(self, painter, option, index):
        entry = index.data(ENTRY) or {};rect = option.rect;painter.save();painter.setRenderHint(QPainter.Antialiasing)
        if option.state & QStyle.State_Selected:
            painter.setPen(Qt.NoPen);painter.setBrush(QColor(AMBER));painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), 8, 8)
        elif option.state & QStyle.State_MouseOver:
            painter.setPen(Qt.NoPen);painter.setBrush(QColor(RAISED));painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), 8, 8)
        side = round(56 * self.scale);pix = glyph(glyph_kind(entry), side)
        painter.drawPixmap(rect.center().x() - side // 2, rect.top() + round(12 * self.scale), pix)
        font = QFont(option.font);painter.setFont(font);metrics = painter.fontMetrics();painter.setPen(QColor(TEXT))
        text_top = rect.top() + round(12 * self.scale) + side + 6;width = rect.width() - 12
        name = entry.get('name', index.data() or '');lines = []
        while name and len(lines) < 2:
            if metrics.horizontalAdvance(name) <= width or len(lines) == 1:
                lines.append(metrics.elidedText(name, Qt.ElideMiddle, width));break
            cut = len(name)
            while cut > 1 and metrics.horizontalAdvance(name[:cut]) > width:cut -= 1
            lines.append(name[:cut]);name = name[cut:]
        for i, line in enumerate(lines):
            painter.drawText(QRect(rect.left() + 6, text_top + i * metrics.height(), width, metrics.height()), Qt.AlignHCenter | Qt.AlignTop, line)
        small = QFont(option.font);small.setPointSizeF(max(8.0, option.font.pointSizeF() * 0.85));painter.setFont(small);painter.setPen(QColor(QUIET))
        painter.drawText(QRect(rect.left() + 6, text_top + len(lines) * metrics.height() + 2, width, painter.fontMetrics().height()), Qt.AlignHCenter | Qt.AlignTop,
                         painter.fontMetrics().elidedText(kind_word(entry), Qt.ElideRight, width))
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(round(150 * self.scale), round(140 * self.scale))


class PreviewPane(QFrame):
    """What is selected: glyph or thumbnail, name, kind, size, modified and created, the first lines of a text. Reads only."""

    def __init__(self, page):
        super().__init__();self.page = page;self.setObjectName('FinderPreview');self.setProperty('paperFunctionalInk', True);self.current = None
        self.setMinimumWidth(220);self.setMaximumWidth(360);self.setStyleSheet('QFrame#FinderPreview {border-left:1px solid %s;}' % LINE)
        box = QVBoxLayout(self);box.setContentsMargins(18, 16, 18, 12);box.setSpacing(8)
        self.picture = QLabel();self.picture.setAlignment(Qt.AlignCenter);self.picture.setMinimumHeight(120);self.picture.setAccessibleName('Preview picture');box.addWidget(self.picture)
        self.name = role(QLabel(), 'card');self.name.setWordWrap(True);self.name.setTextInteractionFlags(Qt.TextSelectableByMouse);box.addWidget(self.name)
        self.facts = QLabel();self.facts.setWordWrap(True);self.facts.setStyleSheet('color:%s' % QUIET);self.facts.setTextInteractionFlags(Qt.TextSelectableByMouse);box.addWidget(self.facts)
        self.text = QPlainTextEdit();self.text.setReadOnly(True);self.text.setFont(mono_font(13));self.text.setAccessibleName('First lines of the file, read-only')
        self.text.setLineWrapMode(QPlainTextEdit.NoWrap);self.text.setStyleSheet('QPlainTextEdit {background:%s;color:%s;border:1px solid %s;border-radius:8px;}' % (CARD, TEXT, LINE));box.addWidget(self.text, 1)
        self.text.hide();box.addStretch(0);self.note = QLabel();self.note.setWordWrap(True);self.note.setStyleSheet('color:%s' % FAINT);box.addWidget(self.note)
        self.image_size = None;self.text_lines = 0

    def show_nothing(self, words='Nothing selected'):
        self.current = None;self.picture.clear();self.name.setText(words);self.facts.setText('');self.text.hide();self.text.clear();self.note.setText('');self.image_size = None;self.text_lines = 0

    def show_folder(self, path, listing=None):
        """A folder: how many items and how much space on its disk (one bounded ledger.browse when none is at hand)."""
        self.current = path;value = listing if listing is not None and listing.get('path') == str(path) else self.page.read_folder(path, limit=1)
        self.picture.setPixmap(glyph('folder', 96));self.name.setText(Path(path).name or str(path));self.image_size = None;self.text_lines = 0
        if value is None:self.facts.setText('Folder · could not be read');self.note.setText(self.page.last_error or '')
        else:
            self.facts.setText('Folder · %d item%s · %s available on this disk' % (value['count'], '' if value['count'] == 1 else 's', space_words(value['free_bytes'])))
            self.note.setText('Observed from this computer · nothing opened or written')
        self.text.hide();self.text.clear()

    def show_entry(self, path, entry):
        self.current = path;name = entry.get('name') or Path(path).name;kind = entry.get('kind')
        if kind == 'folder':self.show_folder(path);return
        self.name.setText(name);lines = [kind_word(entry) + (' · symbolic link' if kind == 'link' else '')]
        try:st = os.lstat(path)
        except OSError:st = None
        size = entry.get('bytes') if entry.get('bytes') is not None else (st.st_size if st else None)
        if size is not None:lines.append('Size: %s (%s bytes)' % (size_words(size), format(size, ',')))
        if st is not None:
            lines.append('Modified: ' + time.strftime('%d %b %Y %H:%M', time.localtime(st.st_mtime)))
            born = getattr(st, 'st_birthtime', None)
            lines.append(('Created: ' + time.strftime('%d %b %Y %H:%M', time.localtime(born))) if born else ('Changed: ' + time.strftime('%d %b %Y %H:%M', time.localtime(st.st_ctime)) + ' · creation time not recorded by this filesystem'))
        if kind == 'link':
            try:lines.append('Points to: ' + os.readlink(path))
            except OSError:lines.append('Points to: unreadable')
        self.image_size = None;self.text_lines = 0;self.text.hide();self.text.clear();shown = False
        if kind == 'file' and kind_of(name) == 'images':
            reader = QImageReader(str(path));size_px = reader.size()
            if size_px.isValid() and size_px.width() > 0 and size_px.height() > 0:
                self.image_size = (size_px.width(), size_px.height());lines.append('Picture: %d × %d pixels' % self.image_size)
                longest = max(size_px.width(), size_px.height())
                if longest > THUMB_SIDE:reader.setScaledSize(size_px * (THUMB_SIDE / longest))
                image = reader.read()
                if not image.isNull():
                    pix = QPixmap.fromImage(image);width = max(120, self.width() - 40)
                    self.picture.setPixmap(pix.scaled(QSize(width, 220), Qt.KeepAspectRatio, Qt.SmoothTransformation));shown = True
        if kind == 'file' and not shown and looks_textual(path, size):
            try:
                with open(path, 'rb') as handle:head = handle.read(PREVIEW_TEXT_BYTES)
                text_lines = head.decode('utf-8', errors='replace').splitlines()[:PREVIEW_LINES]
                self.text.setPlainText('\n'.join(text_lines));self.text.show();self.text_lines = len(text_lines)
                lines.append('First %d line%s shown · read-only' % (len(text_lines), '' if len(text_lines) == 1 else 's'))
            except OSError:lines.append('The first lines could not be read')
        if not shown:self.picture.setPixmap(glyph(glyph_kind(entry), 96))
        self.facts.setText('\n'.join(lines));self.note.setText('Read from this computer · nothing written')


class ColumnsView(QScrollArea):
    """Miller columns: each folder a list; choosing a folder opens the next column to the right; the preview is the last."""

    def __init__(self, page):
        super().__init__();self.page = page;self.setWidgetResizable(True);self.setFrameShape(QFrame.NoFrame);self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.inner = QWidget();self.row = QHBoxLayout(self.inner);self.row.setContentsMargins(0, 0, 0, 0);self.row.setSpacing(0)
        self.row.addStretch(1);self.setWidget(self.inner);self.columns = [];self.setAccessibleName('Finder columns')

    def clear(self):
        for _, widget in self.columns:
            self.row.removeWidget(widget);widget.deleteLater()
        self.columns = []

    def add_column(self, path, listing, select=None):
        widget = QListWidget();widget.setObjectName('FinderColumn');widget.setFixedWidth(COLUMN_WIDTH);widget.setUniformItemSizes(True)
        widget.setStyleSheet('QListWidget#FinderColumn {border-right:1px solid %s;}' % LINE);widget.setAccessibleName('Column: ' + (Path(path).name or str(path)))
        widget.setSelectionMode(QAbstractItemView.SingleSelection);widget.setEditTriggers(QAbstractItemView.NoEditTriggers);widget.setIconSize(QSize(18, 18))
        for entry in (listing or {}).get('entries', []):
            item = QListWidgetItem(QIcon(glyph(glyph_kind(entry), 18)), entry['name'] + ('  ›' if entry['kind'] == 'folder' else ''));item.setData(ENTRY, entry);widget.addItem(item)
        if listing is None:
            item = QListWidgetItem(self.page.last_error or 'This folder could not be read');item.setFlags(Qt.NoItemFlags);widget.addItem(item)
        # G-B: a long name elides in the middle inside its column (whole in its tooltip); a column never scrolls sideways.
        widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);widget.setTextElideMode(Qt.ElideMiddle)
        tall = widget.sizeHintForRow(0) if widget.count() else 0
        for i in range(widget.count()):
            item = widget.item(i);item.setSizeHint(QSize(1, tall));item.setToolTip(item.text().rstrip(' ›'))  # as wide as the column, not the name
        index = len(self.columns);self.row.insertWidget(index, widget);self.columns.append((path, widget))
        widget.installEventFilter(self.page.keys);widget.setContextMenuPolicy(Qt.CustomContextMenu)
        widget.customContextMenuRequested.connect(lambda point, w=widget:self.page.context_menu(w, point))
        widget.itemDoubleClicked.connect(lambda item:self.page.open_entry(item.data(ENTRY)) if item.data(ENTRY) else None)
        widget.currentItemChanged.connect(lambda current, previous, k=index:self.page.column_selected(k, current.data(ENTRY) if current else None))
        if select:
            for i in range(widget.count()):
                if (widget.item(i).data(ENTRY) or {}).get('name') == select:
                    widget.blockSignals(True);widget.setCurrentRow(i);widget.blockSignals(False);break
        return widget

    def truncate(self, keep):
        while len(self.columns) > keep:
            _, widget = self.columns.pop();self.row.removeWidget(widget);widget.deleteLater()

    def last(self):return self.columns[-1][1] if self.columns else None


class Keys(QObject):
    """The Mac keys on every view: Enter opens, Backspace / Alt Up goes up, Space toggles the preview, Alt Left / Right history."""

    def __init__(self, page):super().__init__(page);self.page = page

    def eventFilter(self, watched, event):
        if event.type() == QEvent.KeyPress:
            key, mods = event.key(), event.modifiers()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                entry = self.page.current_entry(watched)
                if entry:self.page.open_entry(entry);return True
            if key == Qt.Key_Backspace or (key == Qt.Key_Up and mods & Qt.AltModifier):self.page.up();return True
            if key == Qt.Key_Space:self.page.toggle_preview();return True
            if key == Qt.Key_Left and mods & Qt.AltModifier:self.page.back();return True
            if key == Qt.Key_Right and mods & Qt.AltModifier:self.page.forward();return True
        return False


class FinderPage(QWidget):
    """Home: the Finder window, with Today as its first place (`today` is the TodayPage, unchanged in content)."""
    changed = Signal()

    def __init__(self, host, today=None, with_today=True):
        super().__init__();self.host = host;self.setObjectName('FinderPage');self.with_today = with_today
        self.history = [];self.index = -1;self.place = None;self.listing = None;self.entries = [];self.view = 'list';self.hidden = False;self.limit = DEFAULT_LIMIT
        self.last_error = None;self.loading = False;self.columns_root = None;self.is_home = with_today;self._restoring = True
        self.keys = Keys(self)
        outer = QVBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0);outer.setSpacing(0)
        # Toolbar ----------------------------------------------------------------------------------------------------------
        bar = QWidget();bar.setObjectName('FinderBar');row = QHBoxLayout(bar);row.setContentsMargins(28, 12, 28, 6);row.setSpacing(10)
        self.back_button = QToolButton();self.back_button.setText('‹');self.back_button.setAccessibleName('Back');self.back_button.setToolTip('Back');self.back_button.clicked.connect(self.back)
        self.forward_button = QToolButton();self.forward_button.setText('›');self.forward_button.setAccessibleName('Forward');self.forward_button.setToolTip('Forward');self.forward_button.clicked.connect(self.forward)
        for b in (self.back_button, self.forward_button):b.setCursor(Qt.PointingHandCursor);b.setMinimumWidth(30);row.addWidget(b)
        self.up_button = QToolButton();self.up_button.setText('↑');self.up_button.setAccessibleName('Enclosing folder');self.up_button.setToolTip('Enclosing folder');self.up_button.clicked.connect(self.up);row.addWidget(self.up_button)
        self.name = role(QLabel('Today'), 'item');self.name.setAccessibleName('Place');row.addWidget(self.name, 1);self.title = 'Today'
        self.name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)  # the name takes the room left; fit_bar elides it last
        self.view_buttons = {}
        for key in VIEWS:
            b = QPushButton(VIEW_WORDS[key]);b.setCheckable(True);b.setProperty('arcButton', 'segment');b.setCursor(Qt.PointingHandCursor);b.setAccessibleName('View as ' + VIEW_WORDS[key])
            b.clicked.connect(lambda checked=False, key=key:self.set_view(key));self.view_buttons[key] = b;row.addWidget(b)
        self.hidden_button = QPushButton('Hidden');self.hidden_button.setCheckable(True);self.hidden_button.setProperty('arcButton', 'filter');self.hidden_button.setToolTip('Show the files whose names begin with a dot')
        self.hidden_button.setAccessibleName('Show hidden files');self.hidden_button.clicked.connect(lambda checked:self.set_hidden(checked));row.addWidget(self.hidden_button)
        self.preview_button = QPushButton('Preview');self.preview_button.setCheckable(True);self.preview_button.setProperty('arcButton', 'filter');self.preview_button.setToolTip('Show or hide the preview (Space)')
        self.preview_button.setAccessibleName('Show preview');self.preview_button.clicked.connect(lambda checked:self.set_preview(checked));row.addWidget(self.preview_button)
        self.places_button = QPushButton('Places ▾');self.places_button.setProperty('arcButton', 'quiet');self.places_button.setCursor(Qt.PointingHandCursor);self.places_button.setAccessibleName('Places')
        self.places_button.setToolTip('Today · Files · Ingress · Egress · Workspace · Program · each storage mount');self.places_button.clicked.connect(self.places_menu);row.addWidget(self.places_button)
        # G-B: under its width the toolbar folds its least-used words into ⋯ (the same choices, as menu rows) instead of clipping them.
        self.more_button = QToolButton();self.more_button.setText('⋯');self.more_button.setAccessibleName('More Finder choices');self.more_button.setCursor(Qt.PointingHandCursor)
        self.more_button.setPopupMode(QToolButton.InstantPopup);self.more_button.setMenu(QMenu(self.more_button));self.more_button.menu().aboutToShow.connect(self.fill_more)
        self.more_button.hide();row.addWidget(self.more_button);self.folded = ()
        self.bar = bar;bar.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);bar.installEventFilter(self)  # the bar never widens the centre
        outer.addWidget(bar)
        # Body: Today, or the listing beside the preview ---------------------------------------------------------------------
        self.stack = QStackedWidget();outer.addWidget(self.stack, 1)
        self.today = None
        if with_today:
            self.today = today if isinstance(today, TodayPage) else TodayPage(host);self.stack.addWidget(self.today)
        self.browser = QWidget();body = QVBoxLayout(self.browser);body.setContentsMargins(0, 0, 0, 0);body.setSpacing(0);self.stack.addWidget(self.browser)
        self.split = QSplitter(Qt.Horizontal);self.split.setChildrenCollapsible(False);self.split.setHandleWidth(1);body.addWidget(self.split, 1)
        self.views = QStackedWidget();self.split.addWidget(self.views)
        self.list = QTreeWidget();self.list.setObjectName('FinderList');self.list.setHeaderLabels(['Name', 'Date Modified', 'Size', 'Kind']);self.list.setRootIsDecorated(False)
        self.list.setAccessibleName('Finder list');self.list.setSelectionMode(QAbstractItemView.SingleSelection);self.list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.list.setSortingEnabled(True);self.list.sortByColumn(0, Qt.AscendingOrder);self.list.setIconSize(QSize(20, 20));self.list.setAlternatingRowColors(False);self.list.setUniformRowHeights(True)
        header = self.list.header();header.setStretchLastSection(False);header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in LIST_WIDTHS:header.setSectionResizeMode(column, QHeaderView.Interactive)
        self.list_widths = {};self.dragged = set();self.list_scale = None;self.scale_columns();header.sectionResized.connect(self.column_resized)  # what fit_columns folds by
        self.list.setStyleSheet('QTreeWidget#FinderList {padding-left:16px;}');self.list.installEventFilter(self)  # resized: fit_columns
        self.icons = QListWidget();self.icons.setObjectName('FinderIcons');self.icons.setViewMode(QListWidget.IconMode);self.icons.setResizeMode(QListWidget.Adjust);self.icons.setMovement(QListWidget.Static)
        self.icons.setSelectionMode(QAbstractItemView.SingleSelection);self.icons.setEditTriggers(QAbstractItemView.NoEditTriggers);self.icons.setAccessibleName('Finder icons');self.icons.setSpacing(6)
        self.icons.setMouseTracking(True);self.icons.setStyleSheet('QListWidget#FinderIcons {padding:12px 20px;}');self.tiles = TileDelegate(self.icons, self.scale());self.icons.setItemDelegate(self.tiles)
        self.icons.setGridSize(self.tiles.sizeHint(None, None))
        self.columns = ColumnsView(self)
        for widget in (self.icons, self.list, self.columns):self.views.addWidget(widget)
        for view in (self.list, self.icons):
            view.installEventFilter(self.keys);view.setContextMenuPolicy(Qt.CustomContextMenu);view.customContextMenuRequested.connect(lambda point, v=view:self.context_menu(v, point))
        self.list.itemDoubleClicked.connect(lambda item, column:self.open_entry(item.data(0, ENTRY)));self.list.currentItemChanged.connect(lambda current, previous:self.selected(current.data(0, ENTRY) if current else None))
        self.icons.itemDoubleClicked.connect(lambda item:self.open_entry(item.data(ENTRY)));self.icons.currentItemChanged.connect(lambda current, previous:self.selected(current.data(ENTRY) if current else None))
        self.preview = PreviewPane(self);self.split.setStretchFactor(0, 1)
        # G-B: in a short window the pane scrolls down rather than drawing its words over each other; never sideways.
        self.preview_scroll = QScrollArea();self.preview_scroll.setWidgetResizable(True);self.preview_scroll.setFrameShape(QFrame.NoFrame);self.preview_scroll.setWidget(self.preview)
        self.preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.preview_scroll.setMinimumWidth(220);self.preview_scroll.setMaximumWidth(360)
        self.split.addWidget(self.preview_scroll);self.split.setStretchFactor(1, 0)
        # Path bar and status line at the foot (Mac puts them there) -----------------------------------------------------------
        foot = QWidget();foot.setObjectName('FinderFoot');col = QVBoxLayout(foot);col.setContentsMargins(28, 6, 28, 10);col.setSpacing(4)
        self.path_bar = QWidget();self.path_bar.setAccessibleName('Path');self.path_row = QHBoxLayout(self.path_bar);self.path_row.setContentsMargins(0, 0, 0, 0);self.path_row.setSpacing(4);col.addWidget(self.path_bar)
        self.path_bar.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);self.path_bar.installEventFilter(self)  # deep paths fold their leading folders into …
        self.status = QLabel();self.status.setStyleSheet('color:%s' % QUIET);self.status.setWordWrap(True);self.status.setAccessibleName('Finder status');col.addWidget(self.status)
        self.truncated_line = QLabel();self.truncated_line.setWordWrap(True);self.truncated_line.hide();col.addWidget(self.truncated_line)
        body.addWidget(foot)
        # Saved choices ----------------------------------------------------------------------------------------------------------
        saved = (host.session.state.get('finder') or {}) if self.is_home else {}
        self.preview_visible = bool(saved.get('preview', True));self.hidden = bool(saved.get('hidden', False))
        self.set_view(saved.get('view') if saved.get('view') in VIEWS else 'list', remember=False)
        self.preview_scroll.setVisible(self.preview_visible);self.preview_button.setChecked(self.preview_visible);self.hidden_button.setChecked(self.hidden)
        first = saved.get('place') if isinstance(saved.get('place'), str) else TODAY
        if first != TODAY and not os.path.isdir(first):first = TODAY
        self.go(first if with_today or first != TODAY else None)
        self._restoring = False

    # ------------------------------------------------------------------ small facts
    def scale(self):return float((getattr(self.host, 'reading_profile', None) or {}).get('ui_pt', 14.0)) / 14.0

    def kernel(self):return getattr(getattr(self.host, 'ledger_bridge', None), 'kernel', None)

    def read_folder(self, path, limit=None, hidden=None):
        """The one listing route: ledger.browse through the Kernel, with the read principal. None and `last_error` on refusal."""
        kernel = self.kernel()
        if kernel is None:self.last_error = 'The Kernel is not available yet';return None
        args = {'path': str(path), 'all': self.hidden if hidden is None else bool(hidden), 'limit': int(limit or self.limit)}
        try:response = kernel.dispatch('ledger.browse', args, operator())
        except Exception as exc:  # the Finder shows words, never a traceback
            self.last_error = str(exc);return None
        if not response.get('ok'):self.last_error = response['error']['message'];return None
        self.last_error = None;return response['result']

    def places(self):
        """(label, place) pairs: Today, Files, Ingress, Egress, Workspace, Program, then each storage mount (observed through ledger.machine)."""
        out = [('Today', TODAY)] if self.with_today else []
        kernel = self.kernel();root = getattr(self.host, 'root', None)
        from . import locations
        try:
            from . import files_service
            files = files_service.root(kernel, create=False) if kernel is not None else None
        except Exception:files = None
        if files is not None:out.append(('Files', str(files)))
        inbox = None
        if kernel is not None:
            try:
                response = kernel.dispatch('receiving.status', {}, operator());inbox = response['result'].get('inbox') if response.get('ok') else None
            except Exception:inbox = None
        if not inbox and root is not None:
            try:inbox = str(locations.ingress(root))
            except Exception:inbox = None
        if inbox:out.append(('Ingress', str(inbox)))
        if files is not None:
            from . import files_service
            out.append(('Egress', str(Path(files) / files_service.EXPORTS)))
        if root is not None:out.append(('Workspace', str(root)))
        try:out.append(('Program', str(locations.program(root))))
        except Exception:pass
        if kernel is not None:
            try:
                response = kernel.dispatch('ledger.machine', {'section': 'storage'}, operator())
                if response.get('ok'):
                    for section in response['result']['sections']:
                        for item in section['items']:
                            if item['id'].startswith('storage:mount:') and item['values'].get('mountpoint'):
                                out.append((item['values']['mountpoint'], item['values']['mountpoint']))
            except Exception:pass
        seen = set();unique = []
        for label, place in out:
            if place in seen:continue
            seen.add(place);unique.append((label, place))
        return unique

    def place_name(self, place=None):
        place = self.place if place is None else place
        if place == TODAY:return 'Today'
        if place is None:return ''
        for label, known in self.places():
            if known == place:return label
        return Path(place).name or str(place)

    @property
    def folder(self):return None if self.place in (None, TODAY) else Path(self.place)

    def files_root(self):
        kernel = self.kernel()
        if kernel is None:return None
        try:
            from . import files_service
            return files_service.root(kernel, create=False)
        except Exception:return None

    # ------------------------------------------------------------------ navigation
    def go(self, place, push=True):
        """Show a place: 'today' or an absolute folder. History is kept in memory; the place is remembered in the session."""
        if place is None:return False
        if place != TODAY:
            place = os.path.normpath(str(place))
            if not os.path.isabs(place):return False
        if push:
            del self.history[self.index + 1:];self.history.append(place);self.index = len(self.history) - 1
        self.place = place;self.listing = None;self.entries = []
        if place == TODAY:
            if self.today is not None:self.stack.setCurrentWidget(self.today)
        else:
            self.stack.setCurrentWidget(self.browser);self.load()
        self.set_title(self.place_name());self.refresh_buttons();self.fill_path_bar();self.remember();self.changed.emit()
        return True

    def show_place(self, place):
        """The left column's hook: a place only while Home is active (never steal the centre from an open document)."""
        if self.is_home and not getattr(self.host, '_home_active', False):return False
        if place == 'files':place = self.files_root()
        if place is None:return False
        if place != TODAY and not os.path.isdir(str(place)):return False
        if place == self.place:return True
        return self.go(place)

    def back(self):
        if self.index <= 0:return False
        self.index -= 1;return self.go(self.history[self.index], push=False)

    def forward(self):
        if self.index >= len(self.history) - 1:return False
        self.index += 1;return self.go(self.history[self.index], push=False)

    def up(self):
        if self.place in (None, TODAY):return False
        parent = (self.listing or {}).get('parent') if self.listing else os.path.dirname(self.place)
        if not parent or parent == self.place:return False
        name = Path(self.place).name;ok = self.go(parent)
        if ok:self.select_name(name)
        return ok

    def refresh_buttons(self):
        self.back_button.setEnabled(self.index > 0);self.forward_button.setEnabled(self.index < len(self.history) - 1)
        self.up_button.setEnabled(self.place not in (None, TODAY) and bool(os.path.dirname(self.place or '') and os.path.dirname(self.place) != self.place))
        for key, b in self.view_buttons.items():b.setChecked(key == self.view)
        on = self.place not in (None, TODAY)
        for b in (self.hidden_button, self.preview_button):b.setEnabled(on)
        for b in self.view_buttons.values():b.setEnabled(on)

    def remember(self):
        if not self.is_home or self._restoring or getattr(self.host, '_closing', False):return
        try:
            self.host.session.state['finder'] = {'place': self.place or TODAY, 'view': self.view, 'preview': bool(self.preview_visible), 'hidden': bool(self.hidden)}
            self.host.session.save()
        except (OSError, AttributeError, RuntimeError):pass

    def places_menu(self):
        menu = self.fill_places(QMenu(self))
        menu.exec(self.places_button.mapToGlobal(self.places_button.rect().bottomLeft()))

    def fill_places(self, menu):
        for label, place in self.places():
            action = menu.addAction(label);action.setCheckable(True);action.setChecked(place == self.place)
            action.triggered.connect(lambda checked=False, place=place:self.go(place))
        return menu

    # ------------------------------------------------------------------ narrow widths (G-B): fold, never clip or scroll sideways
    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Resize, QEvent.LayoutRequest, QEvent.FontChange, QEvent.StyleChange):
            fit = {getattr(self, 'bar', None):self.fit_bar, getattr(self, 'list', None):self.fit_columns, getattr(self, 'path_bar', None):self.fit_path}.get(watched)
            if fit is not None:fit()
        return False

    def set_title(self, words):
        self.title = words;self.fit_bar()

    def fit_bar(self):
        """Keep the toolbar's words whole: fold the least-used ones into ⋯ while the row is wider than the bar, then elide
        the place name (whole in its tooltip). Measured from the words' own size hints, so a larger interface folds sooner."""
        bar = getattr(self, 'bar', None)
        if bar is None:return
        row = bar.layout();m = row.contentsMargins();room = bar.width() - m.left() - m.right()
        groups = {'views':list(self.view_buttons.values()), 'hidden':[self.hidden_button], 'preview':[self.preview_button], 'places':[self.places_button]}
        name_need = self.name.fontMetrics().horizontalAdvance(self.title) + 4
        for b in self.view_buttons.values():bold_room(b)
        for b in (self.hidden_button, self.preview_button):bold_room(b)
        def need(folded, name=name_need):
            shown = [self.back_button, self.forward_button, self.up_button] + [b for key in groups if key not in folded for b in groups[key]] + ([self.more_button] if folded else [])
            return sum(max(b.sizeHint().width(), b.minimumWidth()) for b in shown) + name + row.spacing() * len(shown)
        folded = ()
        for key in FOLD_ORDER:
            if need(folded) <= room:break
            folded += (key,)
        for key, buttons in groups.items():
            for b in buttons:
                if b.isHidden() != (key in folded):b.setVisible(key not in folded)
        if self.more_button.isHidden() != (not folded):self.more_button.setVisible(bool(folded))
        self.folded = folded;self.more_button.setToolTip(('More: ' + ' · '.join(FOLD_WORDS[k] for k in folded)) if folded else '')
        left = room - need(folded, 0)
        shown = self.title if name_need <= left else self.name.fontMetrics().elidedText(self.title, Qt.ElideRight, max(0, left - 4))
        if self.name.text() != shown:self.name.setText(shown)
        self.name.setToolTip(self.title if shown != self.title else '')

    def fill_more(self):
        """⋯: the folded words as menu rows, in the toolbar's own order, enabled and checked as their buttons are."""
        menu = self.more_button.menu();menu.clear()
        if 'views' in self.folded:
            for key in VIEWS:
                action = menu.addAction('View as ' + VIEW_WORDS[key]);action.setCheckable(True);action.setChecked(self.view == key)
                action.setEnabled(self.view_buttons[key].isEnabled());action.triggered.connect(lambda checked=False, key=key:self.set_view(key))
            menu.addSeparator()
        for key, words, on, act in (('hidden', 'Show hidden files', self.hidden, self.set_hidden), ('preview', 'Show preview (Space)', self.preview_visible, self.set_preview)):
            if key in self.folded:
                button = self.hidden_button if key == 'hidden' else self.preview_button
                action = menu.addAction(words);action.setCheckable(True);action.setChecked(bool(on));action.setEnabled(button.isEnabled())
                action.triggered.connect(lambda checked=False, act=act:act(checked))
        if 'places' in self.folded:self.fill_places(menu.addMenu('Places'))

    def fit_columns(self):
        """The List never scrolls sideways: Kind, then Date Modified, then Size fold while Name would have under its room."""
        self.scale_columns();header = self.list.header();room = self.list.viewport().width() - round(NAME_ROOM * self.scale())
        widths = self.list_widths;hidden = []
        for column in LIST_FOLD:
            if sum(widths[c] for c in (1, 2, 3) if c not in hidden) <= room:break
            hidden.append(column)
        for column in (1, 2, 3):
            if header.isSectionHidden(column) != (column in hidden):self.list.setColumnHidden(column, column in hidden)

    def scale_columns(self):
        """The List's default widths follow the interface size (at 18 pt 'Date Modified' and '08 Aug 2026' need more than
        120 px); a column the owner has dragged keeps the owner's width."""
        scale = self.scale()
        if scale == self.list_scale:return
        self.list_scale = scale;self.sizing = True
        try:
            for column, width in LIST_WIDTHS.items():
                if column not in self.dragged:self.list_widths[column] = round(width * scale);self.list.setColumnWidth(column, self.list_widths[column])
        finally:self.sizing = False

    def column_resized(self, column, old, new):
        if column in self.list_widths and old > 0 and new > 0 and not getattr(self, 'sizing', False) and not self.list.header().isSectionHidden(column):
            self.list_widths[column] = new;self.dragged.add(column)  # the owner's drag is kept, at every interface size

    def fit_path(self):
        """Deep paths keep the folders nearest the place whole and fold the leading ones into … (a menu of those folders); a
        last folder name wider than the whole bar elides in the middle (whole in its tooltip and in path_words)."""
        row = self.path_row;items = [row.itemAt(i).widget() for i in range(row.count())]
        more = next((w for w in items if isinstance(w, QToolButton)), None);words = [w for w in items if isinstance(w, QPushButton)]
        if more is None or not words:return
        gap = row.spacing();seps = [None] + [row.itemAt(row.indexOf(b) - 1).widget() for b in words[1:]]
        def wide(b):  # the word's width with its whole name, whatever it shows now
            metrics = b.fontMetrics();return b.sizeHint().width() - metrics.horizontalAdvance(b.text()) + metrics.horizontalAdvance(b.property('whole') or b.text())
        def need(first):
            return ((more.sizeHint().width() + gap) if first else 0) + sum(wide(words[i]) + gap for i in range(first, len(words))) + sum(seps[i].sizeHint().width() + gap for i in range(first + 1, len(words)))
        first = 0
        while first < len(words) - 1 and need(first) > self.path_bar.width():first += 1
        for i, b in enumerate(words):
            if b.isHidden() != (i < first):b.setVisible(i >= first)
            if seps[i] is not None and seps[i].isHidden() != (i <= first):seps[i].setVisible(i > first)
        if more.isHidden() != (not first):more.setVisible(bool(first))
        last = words[-1];whole = last.property('whole') or last.text();over = need(first) - self.path_bar.width();metrics = last.fontMetrics()
        shown = whole if over <= 0 else metrics.elidedText(whole, Qt.ElideMiddle, max(0, metrics.horizontalAdvance(whole) - over))
        if last.text() != shown:last.setText(shown)
        menu = more.menu();menu.clear()
        for b in words[:first]:menu.addAction(b.toolTip()).triggered.connect(lambda checked=False, target=b.toolTip():self.go(target))

    # ------------------------------------------------------------------ the listing
    def load(self):
        if self.place in (None, TODAY):return
        self.loading = True
        try:
            self.listing = self.read_folder(self.place);self.entries = list(self.listing['entries']) if self.listing else []
            self.fill_list();self.fill_icons()
            if self.view == 'columns':self.fill_columns()
            self.fill_status()
            if self.listing is None:self.preview.show_nothing(self.last_error or 'This folder could not be read')
            else:self.preview.show_folder(self.place, self.listing)
        finally:self.loading = False

    def reload(self):
        name = (self.current_entry() or {}).get('name');self.load()
        if name:self.select_name(name)

    def fill_list(self):
        self.list.setSortingEnabled(False);self.list.clear()
        for entry in self.entries:
            item = FinderItem([entry['name'], when(entry['modified']) if entry.get('modified') else '', '' if entry['kind'] == 'folder' else (size_words(entry['bytes']) if entry.get('bytes') is not None else '—'), kind_word(entry)])
            item.setData(0, ENTRY, entry);item.setIcon(0, QIcon(glyph(glyph_kind(entry), 20)));item.setToolTip(0, os.path.join(self.place, entry['name']))
            if not entry.get('readable', True):item.setForeground(0, QColor(QUIET));item.setToolTip(0, item.toolTip(0) + ' · cannot be read')
            for column in (1, 2):item.setTextAlignment(column, Qt.AlignRight | Qt.AlignVCenter)
            for column in (1, 2, 3):item.setForeground(column, QColor(QUIET))
            self.list.addTopLevelItem(item)
        self.list.setSortingEnabled(True);self.list.sortItems(self.list.sortColumn(), self.list.header().sortIndicatorOrder())

    def fill_icons(self):
        self.icons.clear()
        for entry in self.entries:
            item = QListWidgetItem(entry['name']);item.setData(ENTRY, entry);item.setToolTip(entry['name'] + ' · ' + kind_word(entry));self.icons.addItem(item)

    def chain_for(self, path):
        """The columns from the nearest named place (or the path itself) down to the path, at most MAX_COLUMNS deep."""
        path = os.path.normpath(path);root = None
        for label, place in self.places():
            if place == TODAY:continue
            if (path == place or path.startswith(place.rstrip(os.sep) + os.sep)) and (root is None or len(place) > len(root)):root = place
        if root is None:root = path
        chain = [path]
        while chain[0] != root and os.path.dirname(chain[0]) != chain[0] and len(chain) < MAX_COLUMNS:chain.insert(0, os.path.dirname(chain[0]))
        return chain[-MAX_COLUMNS:]

    def fill_columns(self):
        if self.place in (None, TODAY):return
        chain = self.chain_for(self.place);self.columns.clear();self.columns_root = chain[0]
        for i, folder in enumerate(chain):
            listing = self.listing if folder == self.place else self.read_folder(folder)
            self.columns.add_column(folder, listing, select=Path(chain[i + 1]).name if i + 1 < len(chain) else None)
        self.columns.horizontalScrollBar().setValue(self.columns.horizontalScrollBar().maximum())

    def column_selected(self, index, entry):
        if self.loading or entry is None:return
        folder, _ = self.columns.columns[index];path = os.path.join(folder, entry['name'])
        self.columns.truncate(index + 1)
        if entry['kind'] == 'folder':
            # Descend without rebuilding the columns to the left: the chosen folder becomes the place and the next column.
            del self.history[self.index + 1:];self.history.append(path);self.index = len(self.history) - 1
            self.place = path;self.listing = self.read_folder(path);self.entries = list(self.listing['entries']) if self.listing else []
            self.loading = True
            try:self.fill_list();self.fill_icons();self.columns.add_column(path, self.listing)
            finally:self.loading = False
            self.fill_status();self.preview.show_folder(path, self.listing);self.set_title(self.place_name());self.refresh_buttons();self.fill_path_bar();self.remember();self.changed.emit()
            self.columns.horizontalScrollBar().setValue(self.columns.horizontalScrollBar().maximum())
        else:self.preview.show_entry(path, entry)

    def fill_status(self):
        value = self.listing
        if value is None:
            self.status.setText(self.last_error or 'This folder could not be read');self.truncated_line.hide();return
        shown = len(value['entries']);count = value['count']
        words = ('%s item%s' % (format(count, ','), '' if count == 1 else 's')) if not value['truncated'] else ('%s of %s items shown' % (format(shown, ','), format(count, ',')))
        self.status.setText(words + ' · %s available on this disk · observed from this computer' % space_words(value['free_bytes']))
        if value['truncated'] and self.limit < MORE_LIMIT:
            sentence('The list stops at %d to stay quick; {more}.' % shown, {'more': ('show up to %d' % MORE_LIMIT, self.show_more)}, self.truncated_line);self.truncated_line.show()
        elif value['truncated']:
            self.truncated_line.setText('The list stops at %d; the folder holds %s. Narrow it in Files or in a terminal of your own.' % (shown, format(count, ',')));self.truncated_line.show()
        else:self.truncated_line.hide()

    def show_more(self):
        self.limit = MORE_LIMIT;self.reload()

    def fill_path_bar(self):
        while self.path_row.count():
            item = self.path_row.takeAt(0)
            if item.widget():item.widget().deleteLater()
        if self.place in (None, TODAY):
            self.path_bar.hide();self.status.setText('');self.truncated_line.hide();return
        self.path_bar.show();parts = Path(self.place).parts;so_far = ''
        more = QToolButton();more.setText('…');more.setAccessibleName('Enclosing folders');more.setToolTip('The folders above, folded to keep the path whole')
        more.setPopupMode(QToolButton.InstantPopup);more.setMenu(QMenu(more));more.setCursor(Qt.PointingHandCursor);more.hide();self.path_row.addWidget(more)
        for i, part in enumerate(parts):
            so_far = part if i == 0 else os.path.join(so_far, part)
            if i:
                sep = QLabel('›');sep.setStyleSheet('color:%s' % FAINT);self.path_row.addWidget(sep)
            word = QPushButton(part if part != os.sep else '/');word.setFlat(True);word.setProperty('arcButton', 'link');word.setCursor(Qt.PointingHandCursor)
            word.setAccessibleName('Go to ' + so_far);word.setToolTip(so_far);word.setProperty('whole', word.text());word.clicked.connect(lambda checked=False, target=so_far:self.go(target))
            if i == len(parts) - 1:word.setStyleSheet('font-weight:600;')
            self.path_row.addWidget(word)
        self.path_row.addStretch(1);self.fit_path()

    def path_words(self):
        return [self.path_row.itemAt(i).widget().property('whole') or self.path_row.itemAt(i).widget().text() for i in range(self.path_row.count()) if isinstance(self.path_row.itemAt(i).widget(), QPushButton)]

    # ------------------------------------------------------------------ views and selection
    def set_view(self, name, remember=True):
        if name not in VIEWS:return
        self.view = name;self.views.setCurrentWidget({'list': self.list, 'icons': self.icons, 'columns': self.columns}[name])
        if name == 'columns' and self.place not in (None, TODAY) and not self._restoring:self.fill_columns()
        for key, b in self.view_buttons.items():b.setChecked(key == name)
        if remember:self.remember()

    def set_hidden(self, on):
        self.hidden = bool(on);self.hidden_button.setChecked(self.hidden);self.reload();self.remember()

    def set_preview(self, on):
        self.preview_visible = bool(on);self.preview_scroll.setVisible(self.preview_visible);self.preview_button.setChecked(self.preview_visible);self.remember()

    def toggle_preview(self):self.set_preview(not self.preview_visible)

    def current_entry(self, widget=None):
        widget = widget or {'list': self.list, 'icons': self.icons, 'columns': self.columns.last()}[self.view]
        if widget is None:return None
        item = widget.currentItem()
        if item is None:return None
        return item.data(0, ENTRY) if isinstance(widget, QTreeWidget) else item.data(ENTRY)

    def names(self, view=None):
        """The names the current view shows, in its order (the three views share one listing)."""
        view = view or self.view
        if view == 'list':return [self.list.topLevelItem(i).data(0, ENTRY)['name'] for i in range(self.list.topLevelItemCount())]
        if view == 'icons':return [self.icons.item(i).data(ENTRY)['name'] for i in range(self.icons.count())]
        last = self.columns.last()
        return [last.item(i).data(ENTRY)['name'] for i in range(last.count()) if last.item(i).data(ENTRY)] if last is not None else []

    def select_name(self, name):
        """Select an entry by name in every view; the preview follows."""
        found = False
        for i in range(self.list.topLevelItemCount()):
            if self.list.topLevelItem(i).data(0, ENTRY)['name'] == name:self.list.setCurrentItem(self.list.topLevelItem(i));found = True;break
        for i in range(self.icons.count()):
            if self.icons.item(i).data(ENTRY)['name'] == name:self.icons.setCurrentItem(self.icons.item(i));break
        last = self.columns.last()
        if last is not None:
            for i in range(last.count()):
                if (last.item(i).data(ENTRY) or {}).get('name') == name:
                    last.blockSignals(True);last.setCurrentItem(last.item(i));last.blockSignals(False);break
        if found:self.selected(self.current_entry(self.list))
        return found

    def selected(self, entry):
        if self.loading or self.place in (None, TODAY):return
        if entry is None:self.preview.show_folder(self.place, self.listing);return
        self.preview.show_entry(os.path.join(self.place, entry['name']), entry)

    def entry_path(self, entry):return os.path.join(self.place, entry['name']) if self.place not in (None, TODAY) else None

    # ------------------------------------------------------------------ opening (navigation only; nothing changes a file)
    def open_entry(self, entry):
        if not entry or self.place in (None, TODAY):return None
        path = self.entry_path(entry)
        if entry['kind'] == 'folder':return self.go(path)
        if entry['kind'] == 'link':
            target = os.path.realpath(path)
            if os.path.isdir(target):return self.go(target)
            return self.host.open_in_viewer(target) if os.path.exists(target) else self.say('The link points to nothing that can be opened: ' + target)
        return self.open_file(path)

    def open_file(self, path):
        """Editor for a text inside the workspace (the editor's own rule), the viewer for everything else and for any path outside."""
        root = getattr(self.host, 'root', None)
        if root is not None and inside(path, root):return self.host.open_document(Path(path))
        return self.host.open_in_viewer(Path(path))

    def say(self, words):
        self.status.setText(words);return None

    def show_in_files(self, path):
        files = self.files_root()
        if files is None or not inside(path, files):return None
        rel = Path(path).resolve().relative_to(Path(files).resolve()).as_posix()
        from .files_qt import show
        tab = show(self.host, rel.rpartition('/')[0]);tab.select_path(rel) if hasattr(tab, 'select_path') else None;return tab

    def ask_slate(self, path):
        shell = getattr(self.host, 'shell2', None)
        if shell is not None:shell.ask('Tell me about this file: ' + str(path))

    def copy_path(self, path):
        QGuiApplication.clipboard().setText(str(path));self.say('Copied: ' + str(path))

    def menu_for(self, entry):
        """The context menu's words: open, look, show, copy, ask. Nothing here creates, renames, moves or deletes."""
        menu = QMenu(self);path = self.entry_path(entry)
        if path is None:return menu
        menu.addAction('Open').triggered.connect(lambda:self.open_entry(entry))
        if entry['kind'] != 'folder':menu.addAction('Open in viewer').triggered.connect(lambda:self.host.open_in_viewer(Path(path)))
        files = self.files_root()
        if files is not None and inside(path, files) and Path(path).resolve() != Path(files).resolve():
            menu.addAction('Show in Files').triggered.connect(lambda:self.show_in_files(path))
        menu.addAction('Copy path').triggered.connect(lambda:self.copy_path(path))
        menu.addAction(named('Ask Stacy about this ') + ('folder' if entry['kind'] == 'folder' else 'file')).triggered.connect(lambda:self.ask_slate(path))
        menu.addSeparator()
        if files is not None and inside(path, files):
            menu.addAction('Change it in Files').triggered.connect(lambda:self.show_in_files(path))
        else:
            note = menu.addAction('Nothing changes here · Files keeps its own changes');note.setEnabled(False)
        return menu

    def context_menu(self, widget, point):
        """HATCH DESK D4: the right-click menu (workbench/context_menu.py) for the entry under the pointer: menu_for's words, folded
        (open, look, show, copy, ask; Change it in Files), with the staC and the capabilities for a file in Files; on the folder's
        empty place, View as, hidden files and the preview."""
        from .context_menu import open_at
        return open_at(self.host, widget.viewport(), point)

    # ------------------------------------------------------------------ as a tab (the retired Browse pane's callers)
    def navigate(self, folder):return self.go(str(folder))

    def go_up(self):return self.up()

    def title(self):return 'Finder: ' + (self.place_name() or 'Today')

    def info(self):
        if self.place in (None, TODAY):return 'Finder · Today'
        return 'Finder · %s · %s' % (self.place, self.status.text().split(' · ')[0] if self.status.text() else 'reading')
