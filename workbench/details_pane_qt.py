"""1.1 K0 · the details pane: the selected thing, on call (View ▸ Details pane, Alt+P, as in Windows).

DESIGN_DIRECTION_1.1.md section 2: "The details pane (on call, 320 px): the selected thing: preview, facts, connections."
It stands at the right of the centre, beside whatever the centre shows, and follows the selection in every view: a file or
folder chosen in List or Icons (the Explorer, E1), a tile chosen on the Board (1.0's board). Off at every start.

  preview      a picture's thumbnail (E1's cache), the first lines of a text, else the kind's letters in a box (a shape and
               a word: never colour alone)
  facts        Type, Size, Modified, Where; on the Board, the tile's kind, state, basis and source
  connections  the board's neighbours as rows: ─ recorded, ┄ possible, each with its word; a file's rows come from the
               board's own reading of the desk (Desk.recorded, board_model.possible), never from a guess of the pane's own

It reads; it changes nothing. Its two buttons go somewhere (Open board: the file in the middle of the board, 1.0's Ctrl+B)
or show (Properties, W1's page). The pane sits in central_stack's right margin, so no page is moved or rebuilt. It slides in
over 220 ms (design_tokens.MOTION['panel']) and appears at once under Reduce motion.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QSize, Qt, QTimer, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPalette, QPixmap, QLinearGradient
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)

from . import design_tokens as tokens

WIDTH = tokens.DETAILS['width']
TEXT_SUFFIXES = frozenset(('.txt', '.md', '.csv', '.tsv', '.json', '.log', '.ini', '.conf', '.cfg', '.py', '.sh', '.yaml', '.yml',
                           '.toml', '.xml', '.html', '.css', '.js', '.c', '.h', '.rs', '.tex', '.srt', '.desktop', '.list'))
MOST_ROWS = 12
RECORDED, POSSIBLE = '─', '┄'      # the board's own marks for a recorded and a possible link (proposal_familiar section 4)
EMPTY = 'Nothing is chosen.\n\nChoose a file or folder in List or Icons, or a tile on the Board: its preview, its facts and its connections show here.'


def reduce_motion(host):
    try:
        from .document_qt import profile_of
        return bool(profile_of(host).get('reduce_motion'))
    except Exception:  # noqa: BLE001 - no profile: motion as the tokens say
        return False


def launch_look():
    try:
        from . import boss_theme as bt
        return bt.APPEARANCE if bt.LAUNCH else ''
    except Exception:  # noqa: BLE001
        return ''


def when(seconds):
    t = time.localtime(seconds);now = time.localtime()
    if t.tm_year == now.tm_year and t.tm_yday == now.tm_yday:return 'Today %s' % time.strftime('%H:%M', t)
    return time.strftime('%d %b %Y %H:%M', t)


def tilde(path):
    try:return '~/' + Path(path).resolve().relative_to(Path.home().resolve()).as_posix()
    except (ValueError, OSError):
        return str(path)


# ---- what is chosen, and what is known of it (no Qt widgets: the tests read these) ----------------------------------------------
def chosen(host):
    """('file', path, picked) for the Explorer in front (picked False when nothing is chosen: the folder itself), ('tile', tile,
    board view) for the Board in front, else (None, None, None)."""
    explorer = getattr(host, 'explorer', None)
    if explorer is not None and explorer.in_front():
        path = explorer.current_path() or (explorer.chosen_paths() or [''])[0]
        return ('file', path, True) if path else ('file', explorer.folder, False)
    board = board_view(host)
    if board is not None:
        pane = getattr(host, 'details_pane', None);ident = getattr(pane, 'tile_id', '') if pane is not None else ''
        tile = board.board.get(ident) if ident else None
        tile = tile if tile is not None and tile.id != '…' else board.board.focus
        if tile is not None:return 'tile', tile, board
    return None, None, None


def board_view(host):
    page = getattr(host, 'field_page', None);board = getattr(page, 'board', None)
    try:
        return board if board is not None and board.isVisible() else None
    except RuntimeError:
        return None


def facts_of_file(path):
    """[(word, value)] for a file or folder: Type, Size (or what a folder holds), Modified, Where."""
    from .finder_qt import kind_word
    from .explorer import bytes_words
    p = Path(path)
    try:st = p.stat()
    except OSError as exc:
        return [('Where', tilde(path)), ('Note', exc.strerror or 'not read')]
    folder = p.is_dir()
    rows = [('Type', kind_word({'name': p.name, 'kind': 'folder' if folder else 'file'}))]
    if folder:
        try:count = sum(1 for _ in os.scandir(path))
        except OSError:
            count = None
        rows.append(('Holds', 'not read' if count is None else '%d thing%s' % (count, '' if count == 1 else 's')))
    else:rows.append(('Size', bytes_words(st.st_size)))
    rows.append(('Modified', when(st.st_mtime)));rows.append(('Where', tilde(p.parent) if str(p.parent) != str(p) else '/'))
    return rows


def facts_of_tile(tile):
    rows = [('Kind', tile.kind_word or tile.kind or 'Thing')]
    if tile.state_word:rows.append(('State', tile.state_word))
    if tile.basis:rows.append(('Linked', tile.basis))
    if tile.source:rows.append(('From', tile.source))
    rows.append(('On the board', 'in the middle' if tile.distance == 0 else ('a neighbour' if tile.distance == 1 else 'two steps away')))
    return rows


def said(recorded, words):
    """A link's words, always with its kind's word first (recorded or possible: the word beside the mark)."""
    kind = 'recorded' if recorded else 'possible';words = str(words or '').strip()
    return words if words.lower().startswith(kind) else (kind + (' · ' + words if words else ''))


def connections_of_tile(board, tile):
    """The board's neighbours as rows: (mark, title, words). For the tile in the middle, every neighbour; for a neighbour, its
    wire to the middle."""
    b = board.board;rows = []
    if b.focus is not None and tile.id == b.focus.id:
        for t in b.tiles:
            if t.id == '…' or getattr(t, 'group', False):
                rows.append(('+', t.title, 'grouped'));continue
            rows.append((RECORDED if t.recorded else POSSIBLE, t.title, said(t.recorded, t.basis)))
    elif b.focus is not None:
        w = b.wire(tile.id, b.focus.id)
        if w is not None:rows.append((POSSIBLE if w.dashed else RECORDED, b.focus.title, said(not w.dashed, w.label)))
    return rows[:MOST_ROWS]


def connections_of_file(host, path):
    """(rows, known): a file's links on the board's reading of the desk. known is False when the desk does not hold it (or the
    board has not read the desk), so the pane says so instead of 'none'."""
    living = getattr(host, 'living_nav', None);known = (getattr(living, 'files_by_abs', None) or {}) if living is not None else {}
    ident = known.get(str(path));page = getattr(host, 'field_page', None);board = getattr(page, 'board', None)
    desk = getattr(board, 'desk', None)
    if desk is None and board is not None and ident:
        try:desk = board.make_desk()
        except Exception:  # noqa: BLE001 - no reading: the pane says it is not known
            desk = None
    if not ident or desk is None or ident not in getattr(desk, 'objects', {}):return [], False
    rows = [];seen = set()
    for e in desk.recorded(ident):
        other = e.target if e.source == ident else e.source
        if other in seen:continue
        seen.add(other);obj = desk.objects.get(other)
        rows.append((RECORDED, getattr(obj, 'title', '') or other, 'recorded · ' + (e.label or e.relation)))
    try:
        from .board_model import possible
        for other, e in possible(desk, ident, set(seen)).items():
            if other in seen:continue
            obj = desk.objects.get(other);rows.append((POSSIBLE, getattr(obj, 'title', '') or other, 'possible · ' + (e.label or e.relation)))
    except Exception:  # noqa: BLE001 - the recorded rows stand alone
        pass
    return rows[:MOST_ROWS], True


def text_lines(path, most=12, width=60):
    """The first lines of a text file, or None when it does not read as text."""
    p = Path(path)
    try:
        if p.suffix.lower() not in TEXT_SUFFIXES and p.stat().st_size > 64 * 1024:return None
        with open(p, 'rb') as f:raw = f.read(4096)
    except OSError:
        return None
    if b'\0' in raw:return None
    try:text = raw.decode('utf-8')
    except UnicodeDecodeError:
        return None
    if p.suffix.lower() not in TEXT_SUFFIXES and sum(ch.isprintable() or ch in '\n\t\r' for ch in text) < 0.95 * max(1, len(text)):return None
    return [line.rstrip()[:width] for line in text.splitlines()[:most]]


def kind_letters(name, folder=False):
    if folder:return 'FOLDER'
    suffix = Path(name).suffix[1:].upper()
    return (suffix or 'FILE')[:6]


# ---- the pane -------------------------------------------------------------------------------------------------------------------
class DetailsPane(QFrame):
    def __init__(self, host):
        super().__init__(host.central_stack)
        self.host = host;self.wanted = False;self.tile_id = '';self.shown_for = None;self.anim = None;self.open_width = 0
        self.setObjectName('DetailsPane');self.setAccessibleName('Details: the chosen thing')
        self.setAttribute(Qt.WA_StyledBackground, True);self.setAutoFillBackground(True)
        pad = tokens.DETAILS['pad']
        box = QVBoxLayout(self);box.setContentsMargins(pad, 12, pad - 4, 12);box.setSpacing(6)
        self.caption = QLabel('DETAILS', self);self.caption.setObjectName('DetailsCaption')
        self.title = QLabel(self);self.title.setObjectName('DetailsTitle');self.title.setWordWrap(True)
        self.title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.preview = QLabel(self);self.preview.setObjectName('DetailsPreview');self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setFixedHeight(tokens.DETAILS['preview']);self.preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.facts = QLabel(self);self.facts.setObjectName('DetailsFacts');self.facts.setWordWrap(True);self.facts.setTextFormat(Qt.RichText)
        self.facts.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.links_caption = QLabel('CONNECTIONS', self);self.links_caption.setObjectName('DetailsCaption')
        self.links = QListWidget(self);self.links.setObjectName('DetailsConnections');self.links.setAccessibleName('Connections')
        self.links.setFrameShape(QFrame.NoFrame);self.links.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.links.setWordWrap(True);self.links.itemActivated.connect(self.go_link)
        self.links_note = QLabel(self);self.links_note.setObjectName('DetailsNote');self.links_note.setWordWrap(True)
        buttons = QHBoxLayout();buttons.setContentsMargins(0, 4, 0, 0);buttons.setSpacing(8)
        self.board_button = QPushButton('Open board', self);self.board_button.setProperty('arcButton', 'tool')
        self.board_button.setToolTip('This in the middle of the board, with its neighbours (Ctrl+B)');self.board_button.clicked.connect(self.open_board)
        self.properties_button = QPushButton('Properties', self);self.properties_button.setProperty('arcButton', 'tool')
        self.properties_button.setToolTip('Its properties (Alt+Enter)');self.properties_button.clicked.connect(self.open_properties)
        buttons.addWidget(self.board_button);buttons.addWidget(self.properties_button);buttons.addStretch(1)
        self.empty = QLabel(EMPTY, self);self.empty.setObjectName('DetailsEmpty');self.empty.setWordWrap(True);self.empty.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        for w in (self.caption, self.title, self.preview, self.facts, self.links_caption):box.addWidget(w)
        box.addWidget(self.links);box.addWidget(self.links_note);box.addLayout(buttons);box.addWidget(self.empty);box.addStretch(1)
        self.restyle();self.hide()
        self.again = QTimer(self);self.again.setSingleShot(True);self.again.setInterval(80);self.again.timeout.connect(self.refresh)
        host.central_stack.installEventFilter(self)
        host.central_stack.currentChanged.connect(lambda *_: self.soon())
        self.hooked = set();QTimer.singleShot(0, self.hook)

    # ---- the look: the look's own palette (each look keeps its character); elevation, not glow ---------------------------------
    def restyle(self):
        look = launch_look()
        if look:      # Day and Night: the tokens' own colours
            c = tokens.colours(look);ground, text, quiet, line, plate = c['surface'], c['text'], c['secondary'], c['hairline'], c['window']
        else:         # Graphite and Kasandra: the look's own palette, so each keeps its character
            pal = self.host.palette();ground, text, line, plate = (pal.color(r).name() for r in (QPalette.Base, QPalette.Text, QPalette.Mid, QPalette.Window))
            a, b = QColor(text), QColor(ground)
            quiet = QColor(round(a.red() * .7 + b.red() * .3), round(a.green() * .7 + b.green() * .3), round(a.blue() * .7 + b.blue() * .3)).name()
        self.quiet = quiet;floor = tokens.LEAST_PX
        self.setStyleSheet(
            'QFrame#DetailsPane {background: %(ground)s; color: %(text)s; border: 0; border-left: 1px solid %(line)s;}'
            'QLabel#DetailsCaption {font-size: %(cap)dpx; font-weight: 600; letter-spacing: 0.4px; color: %(quiet)s;}'
            'QLabel#DetailsTitle {font-size: 15px; font-weight: 600; color: %(text)s;}'
            'QLabel#DetailsPreview {border: 1px solid %(line)s; border-radius: %(r)dpx; background: %(plate)s; color: %(text)s;}'
            'QLabel#DetailsFacts, QLabel#DetailsNote, QLabel#DetailsEmpty {font-size: 13px; color: %(text)s;}'
            'QLabel#DetailsNote, QLabel#DetailsEmpty {color: %(quiet)s;}'
            'QListWidget#DetailsConnections {background: transparent; font-size: 13px; color: %(text)s;}'
            'QListWidget#DetailsConnections::item {min-height: 24px; padding: 2px 0;}'
            'QLabel#DetailsPreview[face="lines"] {font-family: "%(mono)s"; font-size: %(cap)dpx; padding: 6px 8px;}'
            'QLabel#DetailsPreview[face="tag"] {font-family: "%(mono)s"; font-size: 22px; font-weight: 600;}'
            % dict(ground=ground, text=text, quiet=quiet, line=line, plate=plate, cap=max(floor, 11), r=tokens.RADIUS['tile'],
                   mono=tokens.FONT['mono']))
        self.mono = QFont(tokens.FONT['mono']);self.mono.setPixelSize(max(floor, 11))

    def paintEvent(self, event):
        super().paintEvent(event)
        if launch_look():      # Day and Night: depth from elevation (a soft shadow falling on the pane's left edge), never a glow
            x, y, blur, alpha, _ = tokens.ELEVATION[1]
            p = QPainter(self);g = QLinearGradient(1, 0, 1 + max(3, blur * 2), 0)
            g.setColorAt(0, QColor(0, 0, 0, alpha));g.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillRect(1, 0, max(3, blur * 2), self.height(), g);p.end()

    # ---- on call ---------------------------------------------------------------------------------------------------------------
    def set_wanted(self, on):
        on = bool(on)
        if on == self.wanted and (self.isVisible() == on):return
        self.wanted = on;a = getattr(self.host, 'a_details', None)
        if a is not None and a.isChecked() != on:a.setChecked(on)
        if self.anim is not None:self.anim.stop();self.anim = None
        target = WIDTH if on else 0
        ms = 0 if reduce_motion(self.host) else tokens.MOTION['panel']
        if on:self.refresh(force=True);self.show();self.raise_()
        if ms <= 0:
            self.set_open(target)
        else:
            self.anim = QVariantAnimation(self);self.anim.setStartValue(self.open_width);self.anim.setEndValue(target)
            self.anim.setDuration(ms);self.anim.setEasingCurve(QEasingCurve.OutCubic)
            self.anim.valueChanged.connect(lambda v: self.set_open(int(v)));self.anim.finished.connect(lambda: self.set_open(target))
            self.anim.start()

    def set_open(self, width):
        self.open_width = width;stack = self.host.central_stack
        stack.setContentsMargins(0, 0, width, 0)
        self.place()
        if width <= 0 and not self.wanted:self.hide()

    def place(self):
        stack = self.host.central_stack;w = self.open_width
        self.setGeometry(stack.width() - w, 0, WIDTH, stack.height())
        if w > 0:self.raise_()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize and obj is self.host.central_stack and self.open_width:self.place()
        return False

    # ---- following the selection -------------------------------------------------------------------------------------------------
    def hook(self):
        """The Explorer's two views and the board say when the choice changes; hooked once each, again if they are made later."""
        explorer = getattr(self.host, 'explorer', None)
        if explorer is not None and 'explorer' not in self.hooked:
            self.hooked.add('explorer')
            for view in (explorer.page.list, explorer.page.icons):view.itemSelectionChanged.connect(self.soon)
            told = explorer.say_foot      # the foot is said after every fill and every choice (a fill chooses with signals held)

            def say_foot(*args, _told=told, **kwargs):
                out = _told(*args, **kwargs);self.soon();return out
            explorer.say_foot = say_foot
        board = getattr(getattr(self.host, 'field_page', None), 'board', None)
        if board is not None and id(board) not in self.hooked:
            self.hooked.add(id(board));board.focused.connect(self.tile_chosen)
            focus_on = board.focus_on      # a new middle by the tree, Back or a link (not only a click on a tile)

            def focused(ident, *args, _focus_on=focus_on, **kwargs):
                out = _focus_on(ident, *args, **kwargs);self.tile_id = '';self.soon();return out
            board.focus_on = focused

    def tile_chosen(self, obj):
        self.tile_id = getattr(obj, 'id', '') or '';self.soon()

    def soon(self):
        if self.wanted:self.again.start()

    def refresh(self, force=False):
        if not self.wanted and not force:return
        self.hook()
        kind, thing, extra = chosen(self.host)
        key = (kind, getattr(thing, 'id', thing), extra if kind == 'file' else None)
        if key == self.shown_for and not force:return
        self.shown_for = key
        if kind == 'file':self.show_file(thing, extra)
        elif kind == 'tile':self.show_tile(thing, extra)
        else:self.show_empty()

    def parts(self, on):
        for w in (self.caption, self.title, self.preview, self.facts, self.links_caption, self.links, self.links_note,
                  self.board_button, self.properties_button):w.setVisible(on)
        self.empty.setVisible(not on)

    def show_empty(self):
        self.parts(False);self.path = ''

    def fill_facts(self, rows):
        from html import escape
        self.facts.setText('<table cellspacing="0" cellpadding="1">%s</table>' % ''.join(
            '<tr><td style="padding-right:10px; color:%s;">%s</td><td>%s</td></tr>' % (self.quiet, escape(k), escape(str(v)))
            for k, v in rows))

    def fill_links(self, rows, note=''):
        self.links.clear()
        for mark, title, words in rows:
            item = QListWidgetItem('%s  %s\n     %s' % (mark, title, words));item.setData(Qt.UserRole, title);self.links.addItem(item)
        self.links.setVisible(bool(rows));self.links_note.setText(note);self.links_note.setVisible(bool(note))
        if rows:      # the rows' own height (no gap under them), up to a third of the pane
            tall = sum(max(self.links.sizeHintForRow(i), 24) for i in range(self.links.count())) + 4
            self.links.setFixedHeight(min(tall, max(120, self.height() // 3)))

    def show_file(self, path, picked):
        self.parts(True);self.path = path;p = Path(path);folder = p.is_dir()
        self.caption.setText('DETAILS' if picked else 'DETAILS · THIS FOLDER')
        self.title.setText(p.name or str(p))
        self.set_preview_file(p, folder)
        self.fill_facts(facts_of_file(path))
        rows, known = connections_of_file(self.host, path)
        if rows:self.fill_links(rows)
        elif known:self.fill_links([], 'No connections are recorded or possible on the desk.')
        else:self.fill_links([], 'Not on the board yet. Open board puts it in the middle, with whatever it is linked to.')
        self.board_button.setVisible(getattr(self.host, 'explorer', None) is not None);self.properties_button.setVisible(True)

    def show_tile(self, tile, board):
        self.parts(True);self.path = '';self.tile = tile
        self.caption.setText('DETAILS · ON THE BOARD')
        self.title.setText(tile.title or tile.id)
        self.set_preview_tag(tile.kind_word or tile.kind or 'THING', tile.state_word)
        self.fill_facts(facts_of_tile(tile))
        rows = connections_of_tile(board, tile)
        self.fill_links(rows, '' if rows else 'Nothing is linked to it on the board.')
        self.board_button.hide();self.properties_button.hide()

    def face(self, which):
        """The preview's face by its look's sheet: 'lines' (a text's first lines, in the mono), 'tag' (the kind's letters), ''."""
        if self.preview.property('face') != which:
            self.preview.setProperty('face', which);self.preview.style().unpolish(self.preview);self.preview.style().polish(self.preview)

    def set_preview_file(self, p, folder):
        self.preview.setPixmap(QPixmap());self.preview.setText('');self.face('')
        from .explorer import is_picture
        if not folder and is_picture(p.name):
            from .explorer_qt import thumbnail
            image = thumbnail(str(p), 256)
            if image is not None:
                self.face('')
                room = QSize(WIDTH - 2 * tokens.DETAILS['pad'] - 6, tokens.DETAILS['preview'] - 6)
                self.preview.setPixmap(QPixmap.fromImage(image).scaled(room, Qt.KeepAspectRatio, Qt.SmoothTransformation));return
        lines = None if folder else text_lines(p)
        if lines:
            self.face('lines');self.preview.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self.preview.setText('\n'.join(lines));return
        self.set_preview_tag(kind_letters(p.name, folder), '')

    def set_preview_tag(self, word, state):
        """The kind's letters in a box: a shape and a word."""
        self.preview.setPixmap(QPixmap());self.preview.setAlignment(Qt.AlignCenter);self.face('tag')
        self.preview.setText('[ %s ]%s' % (str(word).upper()[:12], ('\n' + state) if state else ''))

    # ---- the two buttons and a row -----------------------------------------------------------------------------------------------
    def open_board(self):
        explorer = getattr(self.host, 'explorer', None)
        if explorer is not None and getattr(self, 'path', ''):return explorer.to_board(self.path, 'tree')
        return False

    def open_properties(self):
        if getattr(self, 'path', ''):
            from .windows_keys_qt import show_properties
            return show_properties(self.host, self.path)
        return None

    def go_link(self, item):
        """A row on the Board: that neighbour chosen (the board's own choose, as a click on its tile)."""
        board = board_view(self.host);title = item.data(Qt.UserRole)
        if board is None:return
        tile = next((t for t in board.board.all() if t.title == title), None)
        if tile is not None and tile.id != getattr(board.board.focus, 'id', None):board.choose(tile.id)


class ContextRow(QObject):
    """1.1 K0, chrome: 1.0's context row under the centre (a path and a few buttons, 33 px) is a code tab's; over the Explorer
    or the Field it says nothing the centre bar does not, so it stands only while the tabs are in front."""

    def __init__(self, host):
        super().__init__(host);self.host = host
        bar = getattr(host, 'context_bar', None)
        if bar is not None:bar.installEventFilter(self)
        host.central_stack.currentChanged.connect(lambda *_: self.check())

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show:QTimer.singleShot(0, self.check)
        return False

    def check(self):
        host = self.host;bar = getattr(host, 'context_bar', None)
        try:
            if bar is not None and bar.isVisible() and host.central_stack.currentWidget() is not getattr(host, 'workspace_split', None):bar.hide()
        except RuntimeError:
            pass


def action(host):
    """View ▸ Details pane (Alt+P): made once per window; the pane itself is made the first time it is wanted."""
    a = getattr(host, 'a_details', None)
    if a is None:
        a = host.a_details = QAction('Details pane', host);a.setCheckable(True);a.setShortcut('Alt+P')
        a.setShortcutContext(Qt.WindowShortcut);a.setToolTip('The chosen thing at the right of the centre: preview, facts, connections')
        a.setStatusTip(a.toolTip());host.addAction(a)
        a.toggled.connect(lambda on: pane(host).set_wanted(on))
    return a


def pane(host):
    p = getattr(host, 'details_pane', None)
    if p is None:p = host.details_pane = DetailsPane(host)
    return p


def install(host):
    """shell2's start, after the Explorer: the row in View, the key, the context row's rule. The pane is off."""
    if getattr(host, 'central_stack', None) is None:return None
    action(host)
    if getattr(host, 'k0_context_row', None) is None:host.k0_context_row = ContextRow(host)
    return host.a_details
