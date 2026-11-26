"""Depths in the window (Graphite 1.0 L4): from the board into an object's working view and back, and what happens to the
view when another program saves its file.

    one click, two clicks   One click on a tile, a sheet of the Field or a row of the tree focuses the object (L1, L2; the
                            Field's own sheets too, since this slice). A double click (or Enter, or Open in a menu) opens its
                            working view in the centre through the room's own opener (field_page.open_object, L1's open): a
                            sheet in the Office's grid, a page or a calculation in Documents, a source in the PDF reader, a
                            question in its investigation, a text in the editor, a picture in the image viewer, anything else
                            in the read-only viewer. The board recedes (the centre shows the work) and stays as it was behind.
    Board                   at the left of the breadcrumb bar while a working view is in front: back to the board on the same
                            object, at the zoom and place it had (L1's history: the board entry this view was opened from;
                            Forward comes back to the view). The breadcrumb's folders lead back too (L1).
    the centre bar's end    Save (the bar's own, as always) writes; Save and Return writes and closes the view, then the board;
                            Full program opens the file in its default program (S2's apps.for and apps.open), or for an
                            Office sheet the Office's own reviewed copy for the full office program; Close closes the view
                            and comes back to the board. Closing a view with changes that are not saved asks: Save, Don't save,
                            Cancel. A page that saves itself as it is written (Documents) is saved, never asked about.
    the line                under the centre bar, for the view in front: what happened to its file. A file changed on disk by
                            another program is noticed at once (QFileSystemWatcher on every open file): a view with nothing
                            unsaved is reloaded and the line says so, with the time; a view with unsaved changes is left as it
                            is and the line says the file changed, with Compare (the two side by side, line by line), Keep
                            yours (your next Save writes over the disk's) and Take the one on disk. An Office sheet saved
                            elsewhere (its record's revision moved) is noticed when its view comes to the front or Graphite's
                            window does.
    the full program, back  Graphite remembers the file's digest when the program is started and the program it started;
                            whenever the file's bytes change (the watcher, the program's end, Graphite's window coming to the
                            front again) the new revision is recorded through the Kernel (revisions.record: the Kernel reads
                            the file itself and records only the bytes it was told of; workbench/depths.py), the view is
                            reloaded when it has nothing unsaved, and the board (L2) shows the file's revision and marks for
                            recheck the admitted source that holds its earlier revision and what rests on that source.

Nothing here decides anything for the owner: the program is started on his press, the revision is recorded as the disk has
it, nothing is accepted into Intake, and nothing that is not saved is thrown away without his Don't save or Take the one on
disk (the editor's recovery copy keeps the text he left).
"""
from __future__ import annotations

import time
import weakref
from pathlib import Path

from PySide6.QtCore import QEvent, QFileSystemWatcher, QObject, QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPen, QPixmap, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton,
                               QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from . import boss_theme as bt
from . import depths as dp

KINDS = {'CodeEditor': 'text', 'OfficePanel': 'sheet', 'DocumentsTab': 'page', 'PdfDocumentTab': 'reference', 'InvestigationTab': 'question',
         'ImageViewerTab': 'image', 'UniversalViewerTab': 'viewer'}
KIND_WORDS = {'text': 'text', 'sheet': 'sheet', 'page': 'page', 'reference': 'reference', 'question': 'question', 'image': 'picture',
              'viewer': 'file', 'other': 'view'}
AWAY_MS = 1500                  # how often a program started from a view is looked at while it runs
AWAY_LONGEST = 6 * 3600         # seconds: a program still running after this is not looked at any longer (the watcher still is)
HANDOFF_SECONDS = 4             # a program that ends this soon handed the file to one already running (LibreOffice does)
NARROW = 1000                   # pixels: a centre bar narrower than this shows Full program as its glyph alone (icons chosen)


def alive(ref):
    try:
        widget = ref() if ref is not None else None
        if widget is not None:widget.objectName()
        return widget
    except RuntimeError:
        return None


def clock():
    return time.strftime('%H:%M')


# ---- what a working view is, and what it can do ------------------------------------------------------------------------------
def kind_of(tab):
    if tab is None:return 'other'
    kind = KINDS.get(type(tab).__name__, 'other')
    if kind == 'sheet' and not getattr(tab, 'table', True):return 'page'
    return kind


def version_of(saved):
    """An Office record's version in words (its revision is a digest, not for reading)."""
    version = (saved or {}).get('version')
    return ('version %s' % version) if version is not None else 'a newer version'


def name_of(host, tab):
    if tab is None:return ''
    doc = getattr(tab, 'doc', None)
    if kind_of(tab) in ('sheet', 'page') and isinstance(doc, dict) and doc.get('title'):return str(doc['title'])
    title = getattr(tab, 'centre_title', None)
    if callable(title):
        try:return str(title())
        except Exception:  # noqa: BLE001
            pass
    path = path_of(tab)
    if path is not None:return path.name
    index = host.tabs.indexOf(tab)
    said = host.tabs.tabText(index).replace('&', '') if index >= 0 else 'this'
    return said.removeprefix('Preview · ').lstrip('!● ').rstrip(' •')


def path_of(tab):
    """The file on disk a view shows (a text, a picture, a file in the viewer), or None for a record."""
    kind = kind_of(tab)
    value = getattr(tab, 'path', None) if kind in ('text', 'image') else getattr(tab, 'root_path', None) if kind == 'viewer' else None
    return Path(value) if isinstance(value, (str, Path)) and str(value) else None


def is_dirty(tab):
    if tab is None:return False
    if kind_of(tab) == 'text':
        try:return bool(tab.document().isModified()) and not tab.isReadOnly()
        except RuntimeError:return False
    check = getattr(tab, 'is_dirty', None)
    try:return bool(check()) if callable(check) else False
    except Exception:  # noqa: BLE001 - a view that cannot say has nothing it knows to save
        return False


def saves_itself(tab):
    return bool(getattr(tab, 'saves_itself', False))


def can_save(tab):
    if tab is None:return False
    if kind_of(tab) == 'text':return not tab.isReadOnly()
    return callable(getattr(tab, 'save_concern_note', None)) or hasattr(tab, 'can_close_pdf')


def save(host, tab):
    """Save the view as its own Save does. True when it is saved (or had nothing to save)."""
    if tab is None:return True
    try:
        if kind_of(tab) == 'text':return bool(host.save_document(tab)) if is_dirty(tab) else True
        if callable(getattr(tab, 'save_concern_note', None)):return bool(tab.save_concern_note()) if (is_dirty(tab) or saves_itself(tab)) else True
        if hasattr(tab, 'can_close_pdf'):return bool(tab.save_note()) if is_dirty(tab) else True
    except Exception as exc:  # noqa: BLE001 - said, never taking the window down
        host.statusBar().showMessage('Not saved: %s' % str(exc)[:160], 9000);return False
    return True


def discard(host, tab):
    """Don't save: the view's changes are left out (a text keeps a recovery copy, as closing it always did)."""
    kind = kind_of(tab)
    try:
        if kind == 'text':
            from . import engine
            host.recovery.put(engine.rel(tab.path, host.root), tab.toPlainText(), getattr(tab, 'disk_sha256', None))
            tab.recovery_owned = False;tab.document().setModified(False)
        elif kind in ('sheet', 'page') and hasattr(tab, 'writer') and hasattr(tab, 'set_dirty'):
            from .office_qt import invoke
            try:invoke(host, 'draft.discard', {'id': tab.ident, 'writer': tab.writer})
            except (ValueError, OSError):pass
            tab.set_dirty(False)
        elif hasattr(tab, 'can_close_pdf') and hasattr(tab, 'clear_editor'):
            tab.clear_editor()
    except Exception as exc:  # noqa: BLE001
        host.statusBar().showMessage('The changes could not be left out: %s' % str(exc)[:160], 9000);return False
    return True


def digest_of(tab):
    """The digest of the file as the view holds it."""
    if kind_of(tab) == 'text':return getattr(tab, 'disk_sha256', None)
    return getattr(tab, '_l4_digest', None)


def set_digest(tab, digest):
    if kind_of(tab) == 'text':tab.disk_sha256 = digest
    tab._l4_digest = digest


def reload(host, tab):
    """Read the view's file again (or its record): the view shows what is on disk now. True when it did."""
    kind = kind_of(tab);path = path_of(tab)
    try:
        if kind == 'text':
            from .editor_recovery import file_hash
            text = path.read_text(encoding='utf-8')
            cursor = tab.textCursor().position();v = tab.verticalScrollBar().value();h = tab.horizontalScrollBar().value()
            tab.setPlainText(text)
            c = tab.textCursor();c.setPosition(min(cursor, max(0, tab.document().characterCount() - 1)));tab.setTextCursor(c)
            tab.verticalScrollBar().setValue(v);tab.horizontalScrollBar().setValue(h)
            tab.disk_sha256 = file_hash(path);tab.external_changed = False;tab.document().setModified(False)
            if hasattr(host, '_retitle'):host._retitle(tab)
            return True
        if kind == 'image':
            pix = QPixmap(str(path))
            if pix.isNull():return False
            tab.scene.clear();tab.scene.addPixmap(pix);QTimer.singleShot(0, tab.view.fit);return True
        if kind == 'viewer':
            tab.reload_source();return True
        if kind in ('sheet', 'page') and hasattr(tab, 'load') and hasattr(tab, 'ident'):
            from .office_qt import invoke
            tab.load(invoke(host, 'get', {'id': tab.ident}));return True
    except (OSError, UnicodeError, ValueError) as exc:
        host.statusBar().showMessage('Not read again: %s' % str(exc)[:160], 9000)
    return False


def ask(host, name):
    """Closing a view with changes that are not saved: 'save', 'discard' (Don't save) or 'cancel'."""
    box = QMessageBox(host);box.setIcon(QMessageBox.Warning);box.setWindowTitle('Changes not saved')
    box.setText('Save the changes to “%s” before it closes?' % name)
    box.setInformativeText('Don\'t save leaves them out. Cancel keeps the view open as it is.')
    yes = box.addButton('Save', QMessageBox.AcceptRole);no = box.addButton('Don\'t save', QMessageBox.DestructiveRole)
    box.addButton('Cancel', QMessageBox.RejectRole);box.setDefaultButton(yes)
    box.exec()
    chosen = box.clickedButton()
    return 'save' if chosen is yes else 'discard' if chosen is no else 'cancel'


# ---- the way back to the board -----------------------------------------------------------------------------------------------
def living(host):
    return getattr(host, 'living_nav', None)


def return_target(host, tab):
    """Where the view goes back to: the board entry of the history it was opened from (its focus, zoom and place)."""
    nav = living(host)
    if nav is None:return {'focus': getattr(tab, '_living_oid', '') or '', 'board': {}, 'back': False}
    entries = nav.nav.entries
    at = next((i for i in range(len(entries) - 1, -1, -1) if alive(entries[i].tab) is tab and entries[i].depth in ('work', 'split')), None)
    base = None
    for j in range((at if at is not None else len(entries)) - 1, -1, -1):
        if entries[j].depth == 'board':base = entries[j];break
    focus = getattr(tab, '_living_oid', '') or (base.focus if base is not None else '')
    back = at is not None and at == nav.nav.index and at >= 1 and entries[at - 1] is base and base.focus == focus
    return {'focus': focus, 'board': dict(base.board) if base is not None and base.board else {}, 'back': back,
            'title': (base.title if base is not None and base.focus == focus else '') or nav.title_of(focus)}


def go_back(host, target):
    """Back to the board the view was opened from: Back in the history when that is the entry just before, else a new place
    on the same object with the board as it was seen."""
    nav = living(host)
    from . import board_qt
    if nav is None:
        board_qt.show_board(host, (target or {}).get('focus') or None);return True
    nav.syncing.stop();nav.pending = None
    if target.get('back') and nav.nav.can_back():
        nav.back();return True
    focus = target.get('focus') or ''
    if focus and (nav.files_by_id.get(focus) or nav.board_has(focus)):
        nav.go(focus, 'breadcrumb', 'board', title=target.get('title') or '')
        if target.get('board'):nav.set_board(target['board'])
        return True
    board_qt.show_board(host, focus or None)
    return True


def to_board(host, tab=None):
    """Board: the board on the object of the view in front, as it was seen when the view was opened. The view stays open."""
    tab = tab or host.tabs.currentWidget()
    return go_back(host, return_target(host, tab))


# ---- the window's part ---------------------------------------------------------------------------------------------------------
def board_glyph(colour, px):
    """The Board control's shape: a small tile in the middle of a ring, the board's own picture."""
    pixmap = QPixmap(px, px);pixmap.fill(Qt.transparent)
    p = QPainter(pixmap);p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(colour), max(1.3, px / 12.0));p.setPen(pen);p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(px * 0.08, px * 0.2, px * 0.84, px * 0.6))
    p.setBrush(QColor(colour));p.drawRect(QRectF(px * 0.36, px * 0.38, px * 0.28, px * 0.24))
    p.end()
    return pixmap


class Mark(QWidget):
    """The line's shape, so its meaning never rests on colour alone: a circle with a dot (said, done) or a triangle (look)."""

    def __init__(self, parent):
        super().__init__(parent);self.kind = 'said';self.setFixedSize(18, 18)

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        look = self.kind == 'look';colour = QColor(bt.AMBER_EDGE if look else bt.READY)
        p.setPen(QPen(colour, 1.6));p.setBrush(Qt.NoBrush);r = QRectF(2, 2, self.width() - 4, self.height() - 4)
        if look:
            p.drawLine(QPointF(r.center().x(), r.top()), QPointF(r.right(), r.bottom()));p.drawLine(QPointF(r.right(), r.bottom()), QPointF(r.left(), r.bottom()))
            p.drawLine(QPointF(r.left(), r.bottom()), QPointF(r.center().x(), r.top()))
            p.drawLine(QPointF(r.center().x(), r.top() + r.height() * 0.38), QPointF(r.center().x(), r.top() + r.height() * 0.68))
            p.setBrush(colour);p.drawEllipse(QPointF(r.center().x(), r.top() + r.height() * 0.84), 1.0, 1.0)
        else:
            p.drawEllipse(r);p.setBrush(colour);p.drawEllipse(r.center(), r.width() * 0.18, r.width() * 0.18)
        p.end()


class WorkLine(QFrame):
    """The line under the centre bar: what happened to the file of the view in front, with what can be done about it."""

    def __init__(self, depth):
        super().__init__(depth.host)
        self.depth = depth;self.setObjectName('DepthLine');self.setAccessibleName('What happened to this file')
        row = QHBoxLayout(self);row.setContentsMargins(12, 5, 10, 5);row.setSpacing(8)
        self.mark = Mark(self);row.addWidget(self.mark, 0, Qt.AlignVCenter)
        self.words = QLabel(self);self.words.setObjectName('DepthLineWords');self.words.setWordWrap(True);self.words.setTextFormat(Qt.PlainText)
        self.words.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);row.addWidget(self.words, 1)
        self.buttons = QHBoxLayout();self.buttons.setSpacing(6);row.addLayout(self.buttons)
        self.dismiss = QPushButton('Dismiss', self);self.dismiss.setObjectName('DepthLineButton');self.dismiss.setCursor(Qt.PointingHandCursor)
        self.dismiss.setFocusPolicy(Qt.TabFocus);self.dismiss.setToolTip('Put this line away')
        self.dismiss.clicked.connect(self.put_away);row.addWidget(self.dismiss)
        self.restyle();self.hide()

    def restyle(self):
        self.setStyleSheet(
            'QFrame#DepthLine {background:%s;border:0;border-bottom:1px solid %s;} '
            'QLabel#DepthLineWords {color:%s;background:transparent;} '
            'QPushButton#DepthLineButton {color:%s;background:%s;border:1px solid %s;border-radius:0;padding:2px 10px;} '
            'QPushButton#DepthLineButton:hover {background:%s;border:1px solid %s;color:%s;}' % (
                bt.RAISED, bt.LINE, bt.TEXT, bt.TEXT, bt.PANEL, bt.LINE_STRONG, bt.TEAL_SOFT, bt.TEAL_EDGE, bt.TEAL_TEXT))

    def show_for(self, tab):
        said = getattr(tab, '_l4_line', None) if tab is not None else None
        while self.buttons.count():
            item = self.buttons.takeAt(0)
            if item.widget() is not None:item.widget().deleteLater()
        if not said:
            self.hide();return
        self.mark.kind = said.get('kind', 'said');self.mark.update()
        self.words.setText(said.get('words', ''));self.setAccessibleDescription(said.get('words', ''))
        for label, act in said.get('acts', ()):
            button = QPushButton(label, self);button.setObjectName('DepthLineButton');button.setCursor(Qt.PointingHandCursor)
            button.setFocusPolicy(Qt.TabFocus);button.clicked.connect(lambda _=False, a=act: a());self.buttons.addWidget(button)
        self.show()

    def put_away(self):
        tab = self.depth.host.tabs.currentWidget()
        if tab is not None:tab._l4_line = None
        self.hide()


class Depths(QObject):
    """The window's depths: the Board control, Save and Return, Full program, Close, the line, and the watch on open files."""

    def __init__(self, host):
        super().__init__(host)
        self.host = host;self.away = {};self.changed = set();self.apps = {}
        self.watcher = QFileSystemWatcher(self);self.watcher.fileChanged.connect(self.file_changed)
        self.calm = QTimer(self);self.calm.setSingleShot(True);self.calm.setInterval(250);self.calm.timeout.connect(self.look_changed)
        self.away_timer = QTimer(self);self.away_timer.setInterval(AWAY_MS);self.away_timer.timeout.connect(self.look_away)
        self.board = self.make_board_button()
        self.make_controls()
        self.line = WorkLine(self)
        layout = getattr(host, 'center_layout', None);bar = getattr(host, 'centre_bar', None)
        if layout is not None:
            at = layout.indexOf(bar) + 1 if bar is not None and layout.indexOf(bar) >= 0 else max(0, layout.indexOf(host.central_stack))
            layout.insertWidget(at, self.line)
        host.tabs.currentChanged.connect(lambda _=0: self.sync())
        host.central_stack.currentChanged.connect(lambda _=0: self.sync())
        app = QApplication.instance()
        if app is not None:app.applicationStateChanged.connect(self.app_state)
        self.sync()

    # ---- the parts -------------------------------------------------------------------------------------------------------
    def make_board_button(self):
        nav = living(self.host);crumbs = getattr(nav, 'crumbs', None)
        button = QToolButton(crumbs if crumbs is not None else self.host);button.setObjectName('DepthBoard');button.setText('Board')
        button.setAccessibleName('Board');button.setToolTip('Back to the board: this object in the middle, as the board was when you opened it')
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);button.setCursor(Qt.PointingHandCursor);button.setFocusPolicy(Qt.TabFocus)
        button.clicked.connect(lambda: to_board(self.host))
        s = float((getattr(self.host, 'reading_profile', None) or {}).get('ui_pt', 14.0)) / 14.0
        px = max(14, round(16 * s))
        icon = QIcon();icon.addPixmap(board_glyph(bt.READY, px), QIcon.Normal);icon.addPixmap(board_glyph(bt.TEAL_TEXT, px), QIcon.Active)
        button.setIcon(icon);button.setIconSize(QSize(px, px))
        button.setStyleSheet('QToolButton#DepthBoard {font-family:"%s";font-size:%dpx;color:%s;background:transparent;border:1px solid %s;'
                             'padding:1px 8px 1px 5px;border-radius:2px;} QToolButton#DepthBoard:hover {background:%s;border-color:%s;color:%s;}' % (
                                 bt.FACE, max(12, round(14 * s)), bt.TEXT, bt.LINE_STRONG, bt.TEAL_SOFT, bt.TEAL_EDGE, bt.TEAL_TEXT))
        if crumbs is not None and crumbs.layout() is not None:
            crumbs.layout().insertWidget(0, button);crumbs.layout().insertSpacing(1, 4)
        button.hide()
        return button

    def make_controls(self):
        bar = getattr(self.host, 'centre_bar', None)
        self.save_return = self.full = self.close_button = None
        if bar is None:return
        from .tool_faces import wear
        row = bar.layout().itemAt(0).layout() if bar.layout() is not None and bar.layout().count() else None
        if row is None:return

        def control(words, name, does, glyph=None, said=''):
            button = QPushButton(words);button.setObjectName(name);button.setCursor(Qt.PointingHandCursor)
            button.setFocusPolicy(Qt.TabFocus);button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            if said:button.setAccessibleName(said)
            button.clicked.connect(lambda: (does(), self.sync()))
            return wear(button, glyph) if glyph else button
        self.save_return = control('Save and Return', 'CentreSaveReturn', self.save_and_return)
        self.full = control('Full program', 'CentreFullProgram', self.full_program, 'window', 'Open in the full program')
        self.close_button = control('Close', 'CentreClose', self.close_view, 'close', 'Close this view')
        row.addSpacing(8);row.addWidget(self.save_return);row.addSpacing(8);row.addWidget(self.full);row.addWidget(self.close_button)
        original = bar.sync

        def sync(_original=original):
            _original();self.sync_controls()
        bar.sync = sync
        bar.installEventFilter(self)          # a narrow centre: Full program is its glyph alone, so the name of what is open keeps its room

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Resize and watched is getattr(self.host, 'centre_bar', None):QTimer.singleShot(0, self.sync_controls)
        return False

    def compact(self):
        """Full program as its glyph alone (icons chosen, the centre narrower than NARROW): its name stays in its tip."""
        from . import tool_faces
        bar = getattr(self.host, 'centre_bar', None)
        narrow = bar is not None and bar.width() < NARROW and tool_faces.mode() == 'icons'
        words = '' if narrow else 'Full program'
        if self.full.text() != words:
            self.full.setText(words);tool_faces.fit(self.full)

    # ---- what is in front --------------------------------------------------------------------------------------------------
    def page(self):
        host = self.host
        if getattr(host, '_field_active', False) or getattr(host, '_home_active', False):return None
        if host.central_stack.currentWidget() is not getattr(host, 'workspace_split', None):return None
        return host.tabs.currentWidget()

    def sync(self):
        try:
            page = self.page()
            self.board.setVisible(page is not None)
            self.watch_all()
            self.line.show_for(page)
            self.sync_controls()
            if page is not None and kind_of(page) == 'sheet':QTimer.singleShot(0, lambda t=weakref.ref(page): self.look_record(alive(t)))
        except RuntimeError:      # the window is closing
            pass

    def sync_controls(self):
        page = self.page()
        if self.save_return is None or page is None:return
        try:self.compact()
        except RuntimeError:return
        name = name_of(self.host, page);dirty = is_dirty(page)
        target = return_target(self.host, page);where = 'the board' if target.get('focus') or living(self.host) is not None else 'where you were'
        self.save_return.setEnabled(True)
        self.save_return.setToolTip(('Save “%s” and go back to %s' % (name, where)) if dirty and can_save(page) else
                                    ('Nothing to save: back to %s' % where) if not saves_itself(page) else 'Saved as you write: back to %s' % where)
        path = path_of(page);kind = kind_of(page)
        if path is not None:
            app = self.app_name(path)
            self.full.setEnabled(True)
            self.full.setToolTip('Open in the full program: %s. When it saves, the new revision is recognised here' % app if app else
                                 'Open in the full program: choose the program for this kind of file')
        elif kind == 'sheet':
            self.full.setEnabled(not dirty)
            self.full.setToolTip('Open a reviewed copy in the full office program; its changes come back as a new revision after your review'
                                 if not dirty else 'Save first: the full program is given what is saved')
        else:
            self.full.setEnabled(False);self.full.setToolTip('This view shows a record, not a file: it has no full program')
        self.close_button.setEnabled(True)
        self.close_button.setToolTip('Close this view and go back to %s%s' % (where, '; changes that are not saved are asked about' if dirty and not saves_itself(page) else ''))

    def app_name(self, path):
        key = str(path)
        if key not in self.apps:
            from .apps_qt import kind_of as app_for
            found = app_for(self.host, path)
            default = found.get('default') if isinstance(found, dict) else None
            name = ''
            for app in (found.get('apps') or ()) if isinstance(found, dict) else ():
                if isinstance(app, dict) and app.get('id') == default:name = app.get('name') or '';break
            self.apps[key] = name or (str(default or '').removesuffix('.desktop'))
        return self.apps[key]

    # ---- Save and Return, Close, Full program -----------------------------------------------------------------------------
    def save_and_return(self, tab=None):
        tab = tab or self.page()
        if tab is None:return False
        if (is_dirty(tab) or saves_itself(tab)) and not save(self.host, tab):
            self.say(tab, 'look', 'Not saved, so the view stays open: %s' % (self.host.statusBar().currentMessage() or 'the save was refused.'))
            return False
        return self.close_view(tab)

    def close_view(self, tab=None):
        """Close the view (its changes asked about, through the window's own closing: may_close), then the board it was opened
        from."""
        tab = tab or self.page()
        if tab is None:return False
        index = self.host.tabs.indexOf(tab)
        if index < 0:return False
        tab._l4_return = True
        if not self.host.close_tab(index):
            try:tab._l4_return = False
            except RuntimeError:pass
            return False
        return True

    def may_close(self, tab):
        """A working view of the navigation (or one closed with Close) with changes not saved asks: Save, Don't save, Cancel."""
        if tab is None or not (getattr(tab, '_living_oid', None) or getattr(tab, '_l4_return', False)):return True
        if saves_itself(tab):
            save(self.host, tab);return True
        if not is_dirty(tab):return True
        answer = ask(self.host, name_of(self.host, tab))
        if answer == 'cancel':return False
        if answer == 'save':return save(self.host, tab)
        return discard(self.host, tab)

    def full_program(self, tab=None):
        tab = tab or self.page()
        if tab is None:return None
        kind = kind_of(tab);path = path_of(tab)
        if path is None and kind == 'sheet':return self.office_program(tab)
        if path is None:
            self.say(tab, 'said', 'This view shows a record, not a file: it has no full program.');return None
        if is_dirty(tab):
            self.say(tab, 'look', 'Save first: the full program opens the file as it is on disk, without the changes made here.',
                     [('Save', lambda t=weakref.ref(tab): (save(self.host, alive(t)), self.sync()))]);return None
        from .apps_qt import OpenWithDialog, call, kind_of as app_for
        found = app_for(self.host, path)
        if 'error' in found:
            self.say(tab, 'look', 'No program could be found for it: %s' % found['error']);return None
        try:digest, _ = dp.sha256_of(path)
        except OSError as exc:
            self.say(tab, 'look', 'The file cannot be read: %s' % exc);return None
        set_digest(tab, digest)
        name = '';pids = []
        if found.get('default'):
            try:result = call(self.host, 'apps.open', {'id': found['default'], 'files': [str(path)]})
            except ValueError as exc:
                self.say(tab, 'look', str(exc));return None
            if not result.get('ok'):
                self.say(tab, 'look', result.get('reason') or 'It did not start.');return None
            name = result.get('name') or '';pids = [s['pid'] for s in result.get('started') or () if s.get('ok') and s.get('pid')]
        else:
            OpenWithDialog(self.host, path, found).open()
        self.away[str(path)] = {'digest': digest, 'program': name, 'pids': pids, 'since': time.monotonic_ns(), 'tab': weakref.ref(tab),
                                'ended': not pids, 'recorded': 0, 'state': dp.file_state(path)}
        self.watch(path)
        self.say(tab, 'said', 'Open in %s. Save there and come back: the new revision is recognised and recorded here, and this view shows it.'
                 % (name or 'the program you choose'))
        if pids:self.away_timer.start()
        return self.away[str(path)]

    def office_program(self, tab):
        """An Office sheet's full program: the Office's own reviewed copy (Prepare edit copy, then Open editor, then Review file)."""
        if is_dirty(tab):
            self.say(tab, 'look', 'Save first: the full program is given what is saved.');return None
        last = getattr(tab, 'last_result', None) or {}
        if last.get('mode') == 'edit' and tab.open_editor.isEnabled():
            tab.open_editor.click()
            self.say(tab, 'said', 'The copy is open in the full office program. Save and close it there; then Review file (under More) brings its '
                              'changes back as a new revision of this sheet, and what rests on it waits for a recheck.')
            return 'editor'
        tab.edit_copy.click()
        self.say(tab, 'said', 'A copy for the full office program is being prepared from what is saved. When it is ready, Full program opens it.')
        return 'prepare'

    # ---- the line --------------------------------------------------------------------------------------------------------
    def say(self, tab, kind, words, acts=()):
        if tab is None:return
        tab._l4_line = {'kind': kind, 'words': words, 'acts': list(acts), 'at': clock()}
        if tab is self.page():self.line.show_for(tab)

    # ---- the watch on open files ----------------------------------------------------------------------------------------------
    def watch(self, path):
        key = str(path)
        if Path(key).is_file() and key not in self.watcher.files():self.watcher.addPath(key)

    def watch_all(self):
        """Every open view's file is watched; a file no view shows any longer is not."""
        wanted = set()
        from .split_qt import all_tabs
        for tab in all_tabs(self.host):  # 1.0 L5: the other pane's views are watched too
            path = path_of(tab)
            if path is None:continue
            wanted.add(str(path))
            if digest_of(tab) is None and path.is_file():
                try:set_digest(tab, dp.sha256_of(path)[0])
                except OSError:pass
            if getattr(tab, '_l4_state', None) is None:tab._l4_state = dp.file_state(path)
        watched = set(self.watcher.files())
        if watched - wanted:self.watcher.removePaths(sorted(watched - wanted))
        for key in sorted(wanted - watched):self.watch(key)
        for key in list(self.away):
            if key not in wanted:self.away.pop(key, None)

    def file_changed(self, path):
        self.changed.add(str(path));self.calm.start()

    def look_changed(self):
        paths, self.changed = self.changed, set()
        for key in paths:
            self.watch(key)        # a program that writes a new file over the old one ends the watch on the old: it is taken up again
            from .split_qt import all_tabs
            for tab in all_tabs(self.host):  # 1.0 L5: both panes
                if path_of(tab) is not None and str(path_of(tab)) == key:self.look(tab)

    def look(self, tab, why='watcher'):
        """The view's file now: unchanged, saved by another program (recorded, and the view reloaded or told), or gone."""
        path = path_of(tab)
        if path is None:return None
        if not path.is_file():
            if not getattr(tab, '_l4_gone', False):
                tab._l4_gone = True
                self.say(tab, 'look', '%s is not where it was on disk (%s): moved, renamed or deleted by another program. This view keeps what it shows.' % (path.name, clock()))
            return 'gone'
        tab._l4_gone = False
        state = dp.file_state(path)
        if why != 'force' and state is not None and state == getattr(tab, '_l4_state', None):return None
        try:digest, _ = dp.sha256_of(path)
        except OSError:return None
        tab._l4_state = state
        known = digest_of(tab)
        if digest == known:return None
        away = self.away.get(str(path))
        program = (away or {}).get('program') or ''
        recorded = self.record(tab, path, digest, known, away)
        by = ('in %s' % program) if away and program else 'by another program'
        rec = ''
        if recorded and recorded.get('recorded'):
            rec = ' Revision %d is recorded.' % recorded['revision']
            if recorded.get('earlier_admitted'):rec += ' What rests on its earlier revision, admitted as a source, is marked to recheck on the board.'
        if not is_dirty(tab):
            if reload(self.host, tab):
                set_digest(tab, digest)
                lead = ('Back from %s: ' % program) if away and program else 'Reloaded: '
                self.say(tab, 'said', '%s%s was saved %s at %s, and this view shows it now.%s' % (lead, path.name, by, clock(), rec))
                return 'reloaded'
            return None
        if kind_of(tab) == 'text':
            tab.external_changed = True
            if hasattr(self.host, '_retitle'):self.host._retitle(tab)
        ref = weakref.ref(tab)
        self.say(tab, 'look', '%s was saved %s at %s while you have changes here that are not saved.%s' % (path.name, by, clock(), rec),
                 [('Compare', lambda: self.compare(alive(ref))), ('Keep yours', lambda: self.keep_yours(alive(ref))),
                  ('Take the one on disk', lambda: self.take_disk(alive(ref)))])
        return 'changed'

    def record(self, tab, path, digest, known, away):
        """The new revision through the Kernel (revisions.record): only a file in Files has its revisions recorded."""
        try:
            from .files_service import root
            from .apps_qt import call
            kernel = getattr(getattr(self.host, 'ledger_bridge', None), 'kernel', None)
            if kernel is None:return None
            base = root(kernel).resolve()
            if not path.resolve().is_relative_to(base):return None
            args = {'path': str(path.resolve()), 'expected_sha256': digest, 'how': 'full program' if away else 'outside'}
            if known:args['previous_sha256'] = known
            if away and away.get('program'):args['program'] = away['program'][:120]
            result = call(self.host, 'revisions.record', args)
        except (ValueError, OSError, RuntimeError):
            return None
        if away is not None and result.get('recorded'):away['recorded'] = result['revision']
        nav = living(self.host)
        if nav is not None:QTimer.singleShot(0, nav.read_again)      # the tree and the board read Files again: the same object, its new bytes
        return result

    def compare(self, tab):
        """The view's text beside the disk's, line by line (a sheet: the cells that differ)."""
        if tab is None:return None
        dialog = QDialog(self.host);dialog.setWindowTitle('Compare: %s' % name_of(self.host, tab));dialog.resize(860, 560)
        dialog.setObjectName('DepthCompare')
        box = QVBoxLayout(dialog)
        head = QLabel(dialog);head.setWordWrap(True);box.addWidget(head)
        text = QPlainTextEdit(dialog);text.setReadOnly(True);text.setLineWrapMode(QPlainTextEdit.NoWrap);text.setObjectName('DepthCompareText')
        mono = QFont(bt.MONO);mono.setStyleHint(QFont.Monospace);text.setFont(mono);box.addWidget(text, 1)
        cursor = text.textCursor()
        if kind_of(tab) == 'sheet':
            from .office_qt import invoke
            saved = invoke(self.host, 'get', {'id': tab.ident})
            rows = dp.cells_compare(tab.doc, saved['document'])
            head.setText('Cells that differ: yours (not saved) and the saved one, %s. Nothing is changed by looking.' % version_of(saved))
            for cell, mine, theirs in rows or [('', 'no cell differs', '')]:
                cursor.insertText('%-8s yours: %-30s saved: %s\n' % (cell, mine, theirs))
        else:
            path = path_of(tab)
            try:disk = path.read_text(encoding='utf-8')
            except (OSError, UnicodeError):disk = None
            if disk is None:
                head.setText('The file on disk is not text Graphite can set beside this view: Keep yours or Take the one on disk.')
            else:
                rows = dp.compare(tab.toPlainText() if kind_of(tab) == 'text' else '', disk)
                head.setText('Lines marked − are only in yours (not saved); lines marked + are only on disk now. Nothing is changed by looking.')
                for mark, line in rows or [(' ', 'The two are the same.')]:
                    fmt = QTextCharFormat()
                    if mark == '-':fmt.setForeground(QColor(bt.AMBER_TEXT))
                    elif mark == '+':fmt.setForeground(QColor(bt.TEAL_TEXT))
                    elif mark == '@':fmt.setForeground(QColor(bt.QUIET))
                    cursor.insertText({'-': '−  ', '+': '+  ', '@': '', ' ': '   '}[mark] + line + '\n', fmt)
        text.moveCursor(QTextCursor.Start)
        row = QHBoxLayout();row.addStretch(1)
        ref = weakref.ref(tab)
        for label, act in (('Keep yours', lambda: (dialog.accept(), self.keep_yours(alive(ref)))),
                           ('Take the one on disk', lambda: (dialog.accept(), self.take_disk(alive(ref)))), ('Close', dialog.reject)):
            button = QPushButton(label, dialog);button.clicked.connect(lambda _=False, a=act: a());row.addWidget(button)
        box.addLayout(row)
        dialog.open()
        self._compare = dialog
        return dialog

    def keep_yours(self, tab):
        """Keep the view's changes: the next Save writes them over the file on disk (or the sheet's newer revision)."""
        if tab is None:return
        if kind_of(tab) == 'sheet':
            from .office_qt import invoke
            saved = invoke(self.host, 'get', {'id': tab.ident});tab.base = saved
            self.say(tab, 'said', 'Yours are kept: Save writes them as the next version after %s.' % version_of(saved));return
        path = path_of(tab)
        try:digest, _ = dp.sha256_of(path)
        except OSError:return
        set_digest(tab, digest);tab._l4_state = dp.file_state(path)
        if kind_of(tab) == 'text':
            tab.external_changed = False
            if hasattr(self.host, '_retitle'):self.host._retitle(tab)
        self.say(tab, 'said', 'Yours are kept: Save writes them over the file on disk.')

    def take_disk(self, tab):
        """Take the file as it is on disk: the view's changes are left out (a text keeps a recovery copy of them)."""
        if tab is None:return
        if kind_of(tab) == 'text':
            try:
                from . import engine
                self.host.recovery.put(engine.rel(tab.path, self.host.root), tab.toPlainText(), getattr(tab, 'disk_sha256', None))
            except Exception:  # noqa: BLE001 - the recovery copy is a kindness; taking the disk's is what was asked
                pass
        elif kind_of(tab) == 'sheet':
            discard(self.host, tab)
        if reload(self.host, tab):
            path = path_of(tab)
            if path is not None:
                try:set_digest(tab, dp.sha256_of(path)[0]);tab._l4_state = dp.file_state(path)
                except OSError:pass
            self.say(tab, 'said', 'This view shows the one on disk now (%s).%s' % (clock(), ' Your text is kept as a recovery copy.' if kind_of(tab) == 'text' else ''))

    def look_record(self, tab):
        """An Office sheet saved elsewhere (its record's revision moved): reloaded when nothing is unsaved here, else said."""
        if tab is None or kind_of(tab) != 'sheet' or not hasattr(tab, 'base'):return None
        try:
            from .office_qt import invoke
            saved = invoke(self.host, 'get', {'id': tab.ident})
        except (ValueError, OSError):
            return None
        if saved.get('revision') == (tab.base or {}).get('revision'):return None
        name = name_of(self.host, tab);ref = weakref.ref(tab)
        if not is_dirty(tab):
            tab.load(saved)
            self.say(tab, 'said', 'Reloaded: “%s” was saved elsewhere; this view shows %s now (%s).' % (name, version_of(saved), clock()))
            return 'reloaded'
        if getattr(tab, '_l4_seen_revision', None) == saved.get('revision'):return None
        tab._l4_seen_revision = saved.get('revision')
        self.say(tab, 'look', '“%s” was saved elsewhere (%s) while you have changes here that are not saved.' % (name, version_of(saved)),
                 [('Compare', lambda: self.compare(alive(ref))), ('Keep yours', lambda: self.keep_yours(alive(ref))),
                  ('Take the saved one', lambda: self.take_disk(alive(ref)))])
        return 'changed'

    def look_away(self):
        """A program started from a view: has it saved (the watcher says so too) or ended?"""
        now = time.monotonic_ns();running = False
        for key, away in list(self.away.items()):
            tab = alive(away.get('tab'))
            if tab is None:
                self.away.pop(key, None);continue
            self.look(tab, 'away')
            if away.get('ended'):continue
            from .session_launch import start_time
            live = [pid for pid in away.get('pids') or () if start_time(pid) is not None]
            seconds = (now - away['since']) // 1_000_000_000
            if live and seconds < AWAY_LONGEST:
                running = True;continue
            away['ended'] = True
            if seconds < HANDOFF_SECONDS:continue          # it handed the file to a program already running: the watcher still looks
            if not away.get('recorded'):
                self.say(tab, 'said', 'Back from %s: it was closed without saving a change; %s is as it was.' % (away.get('program') or 'the program', Path(key).name))
        if not running:self.away_timer.stop()

    def app_state(self, state):
        """Graphite's window is in front again (coming back from another program): the view in front is looked at."""
        if state != Qt.ApplicationActive:return
        page = self.page()
        if page is None:return
        if path_of(page) is not None:self.look(page, 'back')
        elif kind_of(page) == 'sheet':self.look_record(page)


# ---- the hooks the window calls ----------------------------------------------------------------------------------------------
def depths_of(host):
    return getattr(host, 'depths', None)


def may_close(host, tab):
    """qt_app.close_tab, first: a working view opened from the board asks Save, Don't save, Cancel."""
    depth = depths_of(host)
    try:return True if depth is None else depth.may_close(tab)
    except RuntimeError:
        return True


def closing(host, tab):
    """qt_app.close_tab, before the tab is taken out: where the view goes back to, when it was the one in front and came from
    the board (or was closed with Close or Save and Return); None otherwise."""
    try:
        if depths_of(host) is None or host.tabs.currentWidget() is not tab:return None
        if getattr(host, '_closing', False) or getattr(host.tabs, 'replacing', False):return None
        if not (getattr(tab, '_living_oid', None) or getattr(tab, '_l4_return', False)):return None
        if getattr(host, '_field_active', False) or getattr(host, '_home_active', False):return None
        from .split_qt import keeps_split
        if keeps_split(host, tab):return None  # 1.0 L5: in the split, the views still open there take its place, not the board
        return return_target(host, tab)
    except RuntimeError:
        return None


def closed(host, target):
    """qt_app.close_tab, after: back to the board (instead of Home when it was the last tab). True when it went back."""
    if target is None:return False
    try:return go_back(host, target)
    except Exception as exc:  # noqa: BLE001 - closing never fails because the way back could not be taken
        host.statusBar().showMessage('The board could not be shown again: %s' % str(exc)[:160], 9000);return False


def install(host):
    if getattr(host, 'depths', None) is not None:return host.depths
    host.depths = Depths(host)
    return host.depths
