"""Graphite 1.0 S2 · The Apps panel and Open with: what is installed, in the window.

The owner's picture: upper right, "Apps" and a circled plus. Apps (the head's Struthio) opens this panel, which is the one
Apps list (the cat's list of 0.7, programs_qt.ProgramsList, kept whole inside it):

  the search line   at the top, where the typing goes as the panel opens: the rows that hold every word typed stay, in
                    every section (an app's name, its generic name, comment, keywords, categories and program; a Graphite
                    room's name and title). Down goes to the first row; the line's own Open opens the first row; a letter
                    typed on a row comes back to the line. Beside it, ⊕: "Add an app to the list".
  Yours             the apps and commands the owner put on the list with ⊕ (apps_catalog.pins), first.
  the installed     the apps from their desktop entries (apps_catalog), grouped under their category's plain words (Office,
  apps              Graphics, ...), A to Z; each with its own icon from the icon theme, or Graphite's glyph for its group
                    when it has none; "in a terminal" for a terminal app; an app that cannot start here is quiet and says
                    why when chosen. Choosing one starts it through the Kernel (apps.open, the owner's principal), in a
                    session of its own (session_launch, 1.0 S1). Its right-click: Open, Open files with it, Keep it on your
                    list (or Take it off), Copy its command.
  Graphite          Graphite's own rooms, A to Z, then Explore the workshop and the game, under their own heading, as
                    they always were (the heading shows when there is anything else in the panel).

Open with (context_entries, a provider of the right-click menu, context_menu.PROVIDERS): on a file in Files, in the Finder,
on a plain file in the left tree (L1's Files drawer), on a FILE tile of the board, and in a reference or document view: "Open
with" lists the apps that take the file's kind (the default first), "Choose another app…" and "Always open <kind> with…"
(OpenWithDialog: the apps for the kind, Show every app, and the box "Always open PDF files with this"). Setting the default is
apps.default (approve scope: only the owner's press; her principal never has approve), written to the owner's own
mimeapps.list and read back before it is said to be done. "Open with its default app" starts the default the same way, and
Files' "Open with this computer's app" now goes through it (open_default).

⊕ in the head (install_head, place_head): beside Apps, "Add an app to the list" (AddDialog: an app on this computer, any
of them, including those its entry keeps out of menus; or a command the owner types, read with Exec's rules: no shell).

Nothing is written but by the owner's press: the panel and the right-click read (apps.list, apps.for are observers).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QContextMenuEvent, QFont, QFontMetricsF, QIcon, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton, QToolButton, QVBoxLayout, QWidget)

from .programs_qt import Caption, Margin, MenuRow, ProgramsList, Rule, caption_font, paint_bar, paint_icon

SEARCH_WORDS = 'Find an app'
ADD_WORDS = 'Add an app to the list'
GRAPHITE_HEADING = 'Graphite'
YOURS_HEADING = 'Yours'
NOTHING = 'No app or room has those words'
TERMINAL_CAPTION = 'in a terminal'
CANNOT_CAPTION = 'cannot start here'      # the word beside an app that cannot start (its quiet ink is never the only sign)
MOST_IN_MENU = 12          # apps listed in the right-click's Open with; the rest are in Choose another app


# ---- the Kernel, as the owner -----------------------------------------------------------------------------------------------
def call(host, op, args=None):
    """A Kernel operation as the owner (operator()): its result, or ValueError with the Kernel's words."""
    from .engineering_kernel import operator
    kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None:raise ValueError("Graphite's Kernel is not running.")
    response = kernel.dispatch(op, args or {}, operator())
    if not response.get('ok'):raise ValueError(str((response.get('error') or {}).get('message') or 'Not done'))
    return response['result']


def say(host, words, ms=9000):
    try:
        if hasattr(host, 'statusBar'):host.statusBar().showMessage(str(words), ms)
    except RuntimeError:pass
    return words


def listing(host):
    """apps.list through the Kernel; the catalogue itself when the Kernel cannot answer (a window without one)."""
    try:return call(host, 'apps.list', {})
    except (ValueError, OSError, RuntimeError):
        from . import apps_catalog
        try:return apps_catalog.listing()
        except (OSError, ValueError):return {'apps': [], 'groups': [], 'pins': []}


def open_app(host, ident, files=(), urls=()):
    """Start an app (or a pinned command) as the owner, with files: the Kernel's words in the status line."""
    if files and not urls:  # 1.0 A1: one file of Files opened in a program is watched: its window named on the board, its saves recorded
        from .app_files_qt import open_with
        done = open_with(host, ident, files)
        if done is not None:return done
    args = {'id': ident}
    if files:args['files'] = [str(Path(f).absolute()) for f in files]
    if urls:args['urls'] = list(urls)
    try:result = call(host, 'apps.open', args)
    except ValueError as exc:return say(host, str(exc))
    return say(host, result.get('reason') or ('Started.' if result.get('ok') else 'It did not start.'))


def set_default(host, mime, ident):
    """The owner chose: open this kind of file with this app from now on (apps.default, read back before it is said)."""
    try:result = call(host, 'apps.default', {'type': mime, 'id': ident})
    except ValueError as exc:say(host, str(exc));return None
    say(host, result.get('words') or '');return result


def kind_of(host, path):
    try:return call(host, 'apps.for', {'path': str(path)})
    except ValueError as exc:return {'error': str(exc)}


def open_with_file(host, path):
    """Open with for one file (the viewer's button): the dialog, or why not."""
    if not path or not Path(path).is_file():return say(host, 'Open with takes a file on this computer.')
    found = kind_of(host, path)
    if 'error' in found:return say(host, found['error'])
    dialog = OpenWithDialog(host, path, found);dialog.open();return dialog


def open_default(host, path):
    """Open a file with its default app (the Kernel's apps.for, then apps.open); with none, Open with. False when the Kernel
    cannot say (the caller falls back to the system's own opener)."""
    found = kind_of(host, path)
    if 'error' in found:return False
    if found.get('default'):open_app(host, found['default'], [path]);return True
    OpenWithDialog(host, path, found).open();return True


# ---- the panel's parts --------------------------------------------------------------------------------------------------------
class Heading(QWidget):
    """A section's words in the panel (Office, Graphics, …, Yours, Graphite): quiet capitals at the rows' word column; not a
    row, never focused."""
    def __init__(self, menu, word, parent=None):
        super().__init__(parent or menu.page);self.menu = menu;self.word = word;self.setFocusPolicy(Qt.NoFocus)
        self.setAccessibleName(word);self.setProperty('appsHeading', True)

    def font_(self):
        font = caption_font(self.menu.m);font.setCapitalization(QFont.AllUppercase);font.setLetterSpacing(QFont.PercentageSpacing, 108)
        return font

    def sizeHint(self):
        import math
        m = self.menu.m;return QSize(0, math.ceil(QFontMetricsF(self.font_()).height()) + m.margin + m.rule // 2)

    def minimumSizeHint(self):return self.sizeHint()

    def paintEvent(self, event):
        from . import boss_theme as t
        m = self.menu.m;p = QPainter(self);p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(self.font_());p.setPen(QColor(t.QUIET))
        p.drawText(QRectF(m.pad + m.icon_col, 0, self.width() - 2 * m.pad - m.icon_col, self.height() - 2), Qt.AlignLeft | Qt.AlignBottom, self.word)
        p.fillRect(QRectF(m.pad, self.height() - 1, self.width() - 2 * m.pad, 1), QColor(t.LINE))
        p.end()


def paint_plus(p, rect, colour, width=1.5):
    """⊕: a circle with a plus, in one line weight."""
    p.save();p.setRenderHint(QPainter.Antialiasing);pen = QPen(QColor(colour), width, Qt.SolidLine, Qt.RoundCap);p.setPen(pen);p.setBrush(Qt.NoBrush)
    side = min(rect.width(), rect.height());r = QRectF(rect.center().x() - side / 2 + width, rect.center().y() - side / 2 + width, side - 2 * width, side - 2 * width)
    p.drawEllipse(r);c = r.center();arm = r.width() * 0.28
    p.drawLine(c.x() - arm, c.y(), c.x() + arm, c.y());p.drawLine(c.x(), c.y() - arm, c.x(), c.y() + arm);p.restore()


class PlusButton(QToolButton):
    """⊕ Add an app to the list: in the panel's search line and in the head beside Apps."""
    def __init__(self, host, parent=None, head=False):
        super().__init__(parent);self.host = host;self.head = head;self.scale = 1.0
        self.setObjectName('AppsAdd' if head else 'AppsPanelAdd');self.setAccessibleName(ADD_WORDS);self.setToolTip(ADD_WORDS)
        self.setCursor(Qt.PointingHandCursor);self.setFocusPolicy(Qt.StrongFocus);self.setAttribute(Qt.WA_Hover, True)
        self.setText('⊕');self.clicked.connect(self.add)

    def add(self):
        menu = self.window()
        if isinstance(menu, AppsPanel):menu.close_menu(restore=False)
        QTimer.singleShot(0, lambda:AddDialog(self.host).open())

    def paintEvent(self, event):
        from . import boss_theme as t
        p = QPainter(self)
        edge = max(2, round(2 * self.scale))
        if self.underMouse() and not self.isDown():
            p.fillRect(self.rect(), QColor(t.TEAL_SOFT))
            if self.head:p.fillRect(0, self.height() - edge, self.width(), edge, QColor(t.READY))
        elif self.hasFocus() or self.isDown():
            p.fillRect(0, self.height() - edge, self.width(), edge, QColor(t.AMBER_EDGE))
        side = min(self.width(), self.height()) * (0.46 if self.head else 0.74)
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        paint_plus(p, rect, t.TEXT if (self.underMouse() or self.hasFocus() or self.head) else t.QUIET, max(1.4, 1.5 * self.scale))
        p.end()


class SearchBar(QWidget):
    """The search line at the panel's top, and ⊕ beside it."""
    def __init__(self, menu):
        super().__init__(menu.page);self.menu = menu;self.setObjectName('AppsSearch')
        lay = QHBoxLayout(self);lay.setSpacing(6)
        self.line = QLineEdit(self);self.line.setObjectName('AppsSearchLine');self.line.setPlaceholderText(SEARCH_WORDS)
        self.line.setAccessibleName(SEARCH_WORDS);self.line.setFocusPolicy(Qt.StrongFocus)
        self.plus = PlusButton(menu.host, self);lay.addWidget(self.line, 1);lay.addWidget(self.plus)
        self.line.textChanged.connect(menu.apply_search);self.restyle()

    def restyle(self):
        from . import boss_theme as t
        from .shell2 import SANS
        from .desk_qt import scaled
        m = self.menu.m;self.layout().setContentsMargins(m.pad, max(2, m.margin // 2), m.pad, m.margin)
        tall = max(m.row, m.line) + scaled(8, m.scale)
        self.plus.setFixedSize(tall, tall);self.plus.scale = m.scale;self.line.setFixedHeight(tall)
        self.line.setStyleSheet('QLineEdit#AppsSearchLine {background:%s;color:%s;border:1px solid %s;border-radius:3px;padding:0 %dpx;'
                                'font-family:"%s";font-size:%dpx;} QLineEdit#AppsSearchLine:focus {border:1px solid %s;}'
                                % (t.RAISED, t.TEXT, t.LINE_STRONG, m.pad // 2, SANS, m.px, t.CUE_EDGE))

    def refont(self):self.restyle()


class AppRow(MenuRow):
    """An installed app (or one the owner put on the list): its own icon (Graphite's glyph for its group when it has none), its
    name, and a caption: in a terminal. Choosing it starts it; one that cannot start here is quiet and says why."""
    def __init__(self, menu, app, parent=None, pin_key=None):
        caption = CANNOT_CAPTION if not app.get('available', True) else TERMINAL_CAPTION if app.get('terminal') else ''
        super().__init__(menu, app['name'], app.get('glyph') or 'window', caption, callback=self.open_it)
        if parent is not None:self.setParent(parent)
        self.app = app;self.pin_key = pin_key;self.picture = None
        icon = app.get('icon_file')
        if icon:
            picture = QIcon(icon)
            if not picture.isNull():self.picture = picture
        self.search_words = ' '.join(str(x) for x in (app.get('name'), app.get('generic'), app.get('comment'), ' '.join(app.get('keywords') or ()),
                                                     ' '.join(app.get('categories') or ()), app.get('group'), Path(app.get('program') or '').name)).casefold()
        lines = [x for x in (app.get('generic'), app.get('comment')) if x and x != app['name']]
        lines.append('Opens %s in a window of its own' % app['name'] + (', in a terminal' if app.get('terminal') else ''))
        if pin_key:lines.append('On your list')
        self.setToolTip('\n'.join(lines));self.set_unavailable('' if app.get('available', True) else (app.get('reason') or 'It cannot start here.'))
        self.setObjectName('AppRow')

    def open_it(self):
        host = self.menu.host
        if self.unavailable:return say(host, self.unavailable)
        return open_app(host, self.app['id'])

    def contextMenuEvent(self, event):
        from . import context_menu as cm
        host = self.menu.host
        target = cm.Target('app', self.app['name'], 'app on this computer', ident=self.app['id'], data={'app': self.app, 'pin': self.pin_key},
                           surface='apps', owner=self.menu, icon=self.app.get('glyph') or 'window')
        cm.open_for(host, target, event.globalPos(), keyboard=event.reason() == QContextMenuEvent.Keyboard);event.accept()

    def paintEvent(self, event):
        from . import boss_theme as t
        m = self.m();p = QPainter(self);p.setRenderHint(QPainter.TextAntialiasing);p.setRenderHint(QPainter.SmoothPixmapTransform)
        lit = self.active()
        if lit:paint_bar(p, self.rect())
        on = self.isEnabled() and not self.unavailable
        ink = QColor((t.ON_BAR if on else t.ON_BAR_QUIET) if lit else (t.TEXT if on else t.QUIET))
        rect = self.icon_rect()
        if self.picture is not None:
            if not on:p.setOpacity(0.45)
            self.picture.paint(p, rect.toRect(), Qt.AlignCenter);p.setOpacity(1.0)
        else:paint_icon(p, rect, self.icon_key or 'window', ink)
        room = self.width() - self.word_x() - m.pad
        if self.caption:room -= self.caption_rect().width() + m.caption_gap
        word = self.fontMetrics().elidedText(self.word, Qt.ElideRight, max(10, int(room)))
        p.setFont(self.font());p.setPen(ink);p.drawText(QRectF(self.word_x(), 0, max(10, room), self.height()), Qt.AlignLeft | Qt.AlignVCenter, word)
        if self.caption:
            p.setFont(caption_font(m, self.script));p.setPen(QColor(t.ON_BAR_QUIET if lit else t.QUIET));p.drawText(self.caption_rect(), Qt.AlignRight | Qt.AlignVCenter, self.caption)
        p.end()


class AppsPanel(ProgramsList):
    """The Apps panel: the search line and ⊕, Yours, the installed apps by category, and Graphite's own rooms (the
    ProgramsList it is, whole: rows_by_key, Explore the workshop, the game, the failed-read row)."""
    def __init__(self, host, anchor, actions, explore_action):
        super().__init__(host, anchor, actions, explore_action)
        self.setAccessibleDescription('The apps on this computer by kind, then Graphite\'s own rooms; typing finds one')
        at = self.box.indexOf(self.caption) + 1
        self.search = SearchBar(self);self.box.insertWidget(at, self.search)
        self.installed = QWidget(self.page);self.installed.setObjectName('AppsInstalled')
        self.installed_box = QVBoxLayout(self.installed);self.installed_box.setContentsMargins(0, 0, 0, 0);self.installed_box.setSpacing(0)
        self.box.insertWidget(at + 1, self.installed)
        self.graphite_heading = Heading(self, GRAPHITE_HEADING);self.box.insertWidget(at + 2, self.graphite_heading)
        self.nothing = Heading(self, NOTHING);self.nothing.hide();self.box.insertWidget(self.box.indexOf(self.bottom_margin) if self.box.indexOf(self.bottom_margin) >= 0 else self.box.count(), self.nothing)
        self.sections = [];self.app_rows = [];self.signature = None;self.failed = False;self.listing = None;self.graphite_heading.hide()
        self.box.addStretch(1)      # what the search leaves sits at the top; the room below it stays empty

    # the installed apps -----------------------------------------------------------------------------------------------------
    def fill(self):
        """Each opening: the search line empty, the installed apps read again (apps.list; rebuilt only when they changed)."""
        super().fill()
        self.search.line.blockSignals(True);self.search.line.clear();self.search.line.blockSignals(False)
        self.rebuild(listing(self.host));self.apply_search('')

    def rebuild(self, value):
        value = value or {};self.listing = value
        apps = {a['id']: a for a in value.get('apps', ())}
        pins = value.get('pins', ())
        signature = json.dumps([[(a['id'], a['name'], a.get('available'), a.get('reason'), a.get('icon_file'), a.get('group'), a.get('terminal'))
                                 for a in value.get('apps', ())], [g['group'] for g in value.get('groups', ())], pins], sort_keys=True, default=str)
        if signature == self.signature:return False
        self.signature = signature
        for heading, rows in self.sections:
            for w in [heading] + rows:w.hide();w.setParent(None);w.deleteLater()
        self.sections = [];self.app_rows = []
        if pins:
            rows = []
            for p in pins:
                app = p.get('app') or {'id': p.get('id') or p['key'], 'name': p.get('name') or 'Command', 'available': False,
                                       'reason': p.get('reason') or 'its entry is gone', 'glyph': 'window'}
                rows.append(AppRow(self, app, self.installed, pin_key=p['key']))
            self.add_section(YOURS_HEADING, rows)
        for group in value.get('groups', ()):
            rows = [AppRow(self, apps[i], self.installed) for i in group['ids'] if i in apps]
            if rows:self.add_section(group['group'], rows)
        self.restyle_installed()
        return True

    def add_section(self, words, rows):
        heading = Heading(self, words, self.installed);self.installed_box.addWidget(heading)
        for row in rows:self.installed_box.addWidget(row);row.show()
        heading.show();self.sections.append((heading, rows));self.app_rows += rows

    def restyle_installed(self):
        for heading, rows in self.sections:
            heading.updateGeometry()
            for row in rows:row.refont();row.updateGeometry()
        self.installed.updateGeometry()

    def restyle(self):
        before = self.m;super().restyle()
        if self.m != before:self.search.restyle()

    # the search ---------------------------------------------------------------------------------------------------------------
    def graphite_rows(self):
        return list(self.rows_by_key.values()) + [self.explore_row, self.game_row]

    def apply_search(self, text=None):
        """Only the rows holding every word typed; a section's heading only when a row of it is left; the Graphite heading only
        when anything else is in the panel; a quiet line when nothing is left."""
        from .apps_catalog import holds as holds_all, query_words
        text = self.search.line.text() if text is None else text
        words = query_words(text);shown = 0

        def holds(hay):return holds_all(words, hay)
        for heading, rows in self.sections:
            left = 0
            for row in rows:
                v = holds(row.search_words);row.setVisible(v);left += v
            heading.setVisible(left > 0);shown += left
        graphite = 0
        for key, row in self.rows_by_key.items():
            title = str(row.action.property('title') or '') if row.action is not None else ''
            v = (not self.failed) and holds((row.word + ' ' + title + ' ' + key).casefold());row.setVisible(v);graphite += v
        for row in (self.explore_row, self.game_row):
            v = holds((row.word + ' ' + (row.caption or '')).casefold());row.setVisible(v);graphite += v
        self.rule.setVisible(not words)
        self.graphite_heading.setVisible(bool(self.sections) and (graphite > 0 or self.failed))
        self.nothing.setVisible(bool(words) and shown + graphite == 0)
        self.page.updateGeometry()
        return shown + graphite

    def show_unavailable(self, message):
        self.failed = True;super().show_unavailable(message);self.apply_search()

    def show_programs(self):
        self.failed = False;super().show_programs();self.apply_search()

    def first_row(self):
        """The top row left by the search (as laid out now)."""
        self.installed_box.activate();self.box.activate()
        return next((w for w in self.focusables() if isinstance(w, MenuRow)), None)

    def jump(self, text):
        """A letter typed on a row goes to the search line (the panel finds by words, in every section)."""
        self.search.line.setFocus(Qt.OtherFocusReason);self.search.line.insert(text);return None

    def open_menu(self, keyboard=False):
        rect = super().open_menu(keyboard)
        self.search.line.setFocus(Qt.PopupFocusReason)      # the typing goes to the search line, however it opened
        return rect

    def eventFilter(self, obj, event):
        if self.isVisible() and event.type() == QEvent.KeyPress and isinstance(obj, QWidget) and (obj is self or obj.window() is self):
            focus = QApplication.focusWidget();key = event.key()
            if focus is self.search.line:
                if key == Qt.Key_Escape and self.search.line.text():self.search.line.clear();return True
                if key in (Qt.Key_Down, Qt.Key_PageDown):
                    row = self.first_row()
                    if row is not None:row.setFocus(Qt.TabFocusReason)
                    return True
                if key in (Qt.Key_Return, Qt.Key_Enter) and not event.isAutoRepeat():
                    row = self.first_row()
                    if row is not None:row.click()
                    return True
            elif key == Qt.Key_Up and focus is not None and focus is self.first_row():
                self.search.line.setFocus(Qt.TabFocusReason);return True
            elif key == Qt.Key_Backspace and isinstance(focus, MenuRow):
                self.search.line.setFocus(Qt.TabFocusReason);self.search.line.backspace();return True
        return super().eventFilter(obj, event)

    def words(self):
        """The rows' words top to bottom, '—' for the rule (for readers and checks): Yours, the installed apps by section, then
        Graphite's; the headings are not rows and are not said."""
        out = []
        for i in range(self.box.count()):
            w = self.box.itemAt(i).widget()
            if w is None or not w.isVisibleTo(self) or isinstance(w, (Caption, Margin, SearchBar, Heading)):continue
            if w is self.installed:
                out += [r.word for _, rows in self.sections for r in rows if r.isVisibleTo(self)];continue
            out.append('—' if isinstance(w, Rule) else w.word)
        return out

    def sections_words(self):
        """[(heading, [row words])] as shown, Graphite's last (for readers, checks and frames)."""
        out = [(h.word, [r.word for r in rows if r.isVisibleTo(self)]) for h, rows in self.sections if h.isVisibleTo(self)]
        g = [r.word for r in self.graphite_rows() if r.isVisibleTo(self)]
        if g:out.append((GRAPHITE_HEADING, g))
        return out


# ---- the head's ⊕ ---------------------------------------------------------------------------------------------------------------
def install_head(top):
    """shell2's head: ⊕ beside Apps (1.0 S2), "Add an app to the list"."""
    parent = top.programs.parentWidget()
    top.apps_add = PlusButton(top.host, parent, head=True);top.apps_add.show()
    return top.apps_add


def place_head(top, x, h, gap, d):
    """shell2's head placement: ⊕ at the right end, Apps to its left (returns the x Apps ends at)."""
    plus = getattr(top, 'apps_add', None)
    if plus is None:return x
    side = max(24, round(h * 0.62));width = side + round(4 * min(d.scale, 1.4))
    plus.scale = min(d.scale, 1.4);x -= width;plus.setGeometry(x, 0, width, h);plus.show();plus.raise_()
    return x


# ---- the dialogs ----------------------------------------------------------------------------------------------------------------
def _dialog_frame(dialog, title):
    """A dialog on the menus' paper with a hairline round it, its title at its head (the window manager may draw none)."""
    from . import boss_theme as t
    dialog.setWindowTitle(title);dialog.setModal(True);dialog.setAttribute(Qt.WA_DeleteOnClose, True)
    name = dialog.objectName() or 'AppsDialog';dialog.setObjectName(name)
    dialog.setStyleSheet('QDialog#%s {background:%s;border:1px solid %s;} QListWidget {background:%s;border:1px solid %s;}'
                         % (name, t.CARD, t.LINE_STRONG, t.RAISED, t.LINE))
    lay = QVBoxLayout(dialog);lay.setContentsMargins(18, 16, 18, 14);lay.setSpacing(8)
    head = QLabel(title);font = head.font();font.setBold(True);font.setPointSizeF(font.pointSizeF() * 1.15);head.setFont(font);lay.addWidget(head)
    return lay


def _app_item(app, how=''):
    words = app['name'] + ('  ·  default' if how == 'default' else '') + ('' if app.get('available', True) else '  ·  ' + (app.get('reason') or 'cannot start here'))
    item = QListWidgetItem(words);item.setData(Qt.UserRole, app['id']);item.setToolTip(app.get('comment') or app.get('generic') or app['name'])
    icon = app.get('icon_file')
    if icon:item.setIcon(QIcon(icon))
    if not app.get('available', True):item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
    return item


class OpenWithDialog(QDialog):
    """Open with: the apps that take this kind of file (the default first), Show every app, and "Always open <kind> with this"
    (the owner's own mimeapps.list, read back before it is said). Opening starts the app in a session of its own."""
    def __init__(self, host, path, found=None, always=False):
        super().__init__(host if isinstance(host, QWidget) else None);self.host = host;self.path = str(path)
        self.found = found or kind_of(host, path);self.setObjectName('OpenWith')
        lay = _dialog_frame(self, 'Open with')
        name = Path(self.path).name;words = self.found.get('words') or 'this kind of file'
        head = QLabel('%s  ·  %s. Choose the app to open it:' % (name, words[:1].upper() + words[1:]));head.setWordWrap(True);lay.addWidget(head)
        self.list = QListWidget();self.list.setObjectName('OpenWithList');self.list.setMinimumSize(420, 240);lay.addWidget(self.list, 1)
        self.every = QCheckBox('Show every app');self.every.toggled.connect(self.fill);lay.addWidget(self.every)
        self.always = QCheckBox('Always open %s with this' % words);self.always.setChecked(bool(always));lay.addWidget(self.always)
        self.note = QLabel(self.found.get('error', ''));self.note.setWordWrap(True);self.note.setProperty('quiet', True);lay.addWidget(self.note)
        buttons = QDialogButtonBox(QDialogButtonBox.Open | QDialogButtonBox.Cancel);buttons.accepted.connect(self.choose);buttons.rejected.connect(self.reject)
        lay.addWidget(buttons);self.list.itemActivated.connect(lambda item:self.choose())
        self.fill()

    def fill(self):
        self.list.clear()
        if self.every.isChecked():
            for app in listing(self.host).get('apps', ()):self.list.addItem(_app_item(app))
        else:
            for app in self.found.get('apps', ()):self.list.addItem(_app_item(app, app.get('how', '')))
            if not self.found.get('apps'):self.note.setText('No app here says it opens %s. Show every app to choose one.' % (self.found.get('words') or 'this kind of file'))
        for i in range(self.list.count()):
            if self.list.item(i).flags() & Qt.ItemIsEnabled:self.list.setCurrentRow(i);break

    def chosen(self):
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item is not None and item.flags() & Qt.ItemIsEnabled else None

    def choose(self):
        ident = self.chosen()
        if not ident:self.note.setText('Choose an app first.');return
        if self.always.isChecked() and self.found.get('type'):
            result = set_default(self.host, self.found['type'], ident)
            if result is None or not result.get('verified'):
                self.note.setText((result or {}).get('words') or 'The default was not changed.');return
        self.accept();open_app(self.host, ident, [self.path])


class AddDialog(QDialog):
    """Add an app to the list (Apps ⊕): an app on this computer (every one, those kept out of menus too, with why), or a
    command the owner types (a program and its arguments, read with Exec's rules; no shell)."""
    def __init__(self, host):
        super().__init__(host if isinstance(host, QWidget) else None);self.host = host;self.setObjectName('AppsAddDialog')
        lay = _dialog_frame(self, ADD_WORDS)
        lay.addWidget(QLabel('An app on this computer:'))
        self.filter = QLineEdit();self.filter.setPlaceholderText(SEARCH_WORDS);self.filter.textChanged.connect(self.fill);lay.addWidget(self.filter)
        self.list = QListWidget();self.list.setObjectName('AppsAddList');self.list.setMinimumSize(460, 220);lay.addWidget(self.list, 1)
        self.put = QPushButton('Put it on the list');self.put.clicked.connect(self.add_entry);lay.addWidget(self.put, 0, Qt.AlignLeft)
        lay.addSpacing(6)
        lay.addWidget(QLabel('Or a command of your own (a program and its words; no shell reads it):'))
        row = QHBoxLayout();self.name = QLineEdit();self.name.setPlaceholderText('Its name');self.command = QLineEdit()
        self.command.setPlaceholderText('The command, as: kicad  or  /opt/tool/bin/tool %F');row.addWidget(self.name, 1);row.addWidget(self.command, 3)
        lay.addLayout(row)
        self.put_command = QPushButton('Put the command on the list');self.put_command.clicked.connect(self.add_command);lay.addWidget(self.put_command, 0, Qt.AlignLeft)
        self.note = QLabel('');self.note.setWordWrap(True);lay.addWidget(self.note)
        buttons = QDialogButtonBox(QDialogButtonBox.Close);buttons.rejected.connect(self.reject);buttons.accepted.connect(self.accept);lay.addWidget(buttons)
        try:self.every = call(host, 'apps.list', {'every': True}).get('apps', [])
        except ValueError as exc:self.every = [];self.note.setText(str(exc))
        self.fill()

    def fill(self, *_):
        words = [w for w in self.filter.text().casefold().split() if w];self.list.clear()
        for app in self.every:
            hay = ' '.join(str(x) for x in (app['name'], app.get('generic'), app.get('comment'), ' '.join(app.get('keywords') or ()))).casefold()
            if words and not all(w in hay for w in words):continue
            item = _app_item(app)
            if not app.get('listed', True):item.setText(item.text() + '  ·  ' + (app.get('why') or 'not in the list'))
            self.list.addItem(item)
        if self.list.count():self.list.setCurrentRow(0)

    def add_entry(self):
        item = self.list.currentItem()
        if item is None:self.note.setText('Choose an app first.');return
        try:call(self.host, 'apps.pin', {'id': item.data(Qt.UserRole)})
        except ValueError as exc:self.note.setText(str(exc));return
        say(self.host, '%s is on your list in Apps.' % item.text().split('  ·  ')[0]);self.accept()

    def add_command(self):
        command = self.command.text().strip()
        if not command:self.note.setText('Type the command first.');return
        try:row = call(self.host, 'apps.pin', {'name': self.name.text().strip(), 'command': command})['pin']
        except ValueError as exc:self.note.setText(str(exc));return
        say(self.host, '%s is on your list in Apps.' % row.get('name', 'The command'));self.accept()


# ---- the right-click: Open with, and an app's own rows --------------------------------------------------------------------------
def file_of(host, t):
    """A function giving the target's file (read only when a row needs it: opening the right-click reads nothing), or None
    when the target is not one file."""
    from .context_menu import FILE_KINDS
    if t.surface == 'files' and t.kind in FILE_KINDS and t.data.get('kind') not in ('folder', 'smart'):
        root = Path(getattr(t.owner, 'root', '.'));rel = t.data.get('path') or ''
        return lambda:str(root / rel)
    if t.surface == 'finder' and t.kind in FILE_KINDS and t.ident:
        return lambda:str(t.ident)
    if t.surface == 'viewer' and t.ident:
        return lambda:str(t.ident)
    if t.surface == 'cabinet':
        node = (t.data or {}).get('node') or {}
        if node.get('provider') == 'living_nav' and node.get('role') == 'file' and str(node.get('canonical_id', '')).startswith('fileid:'):
            def resolve(ident=node['canonical_id']):
                found = call(host, 'objects.get', {'id': ident})
                return str(Path(found['root']) / found['path'])
            return resolve
    if t.surface == 'field':
        obj = (t.data or {}).get('object');target = getattr(obj, 'target', None)
        if isinstance(target, dict) and target.get('kind') == 'file' and getattr(obj, 'kind', '') != 'folder' and os.path.isabs(str(target.get('path') or '')):
            return lambda path=str(target['path']):path
    return None


def with_entries(host, path_of):
    """Open with's rows, read when it opens: the apps for the file's kind (the default first), Choose another app,
    Always open <kind> with."""
    from .context_menu import Entry
    try:path = path_of()
    except (ValueError, OSError, KeyError) as exc:
        return [Entry('open:with:none', 'This file cannot be found', 'open', enabled=False, reason=str(exc), glyph='info')]
    if not path or not Path(path).is_file():
        return [Entry('open:with:none', 'This file is not where it was', 'open', enabled=False, reason=str(path), glyph='info')]
    found = kind_of(host, path)
    if 'error' in found:return [Entry('open:with:none', 'Open with is not available', 'open', enabled=False, reason=found['error'], glyph='info')]
    out = []
    for app in found.get('apps', ())[:MOST_IN_MENU]:
        out.append(Entry('open:with:' + app['id'], app['name'], 'open', lambda ident=app['id']:open_app(host, ident, [path]),
                         caption='default' if app.get('how') == 'default' else '', enabled=app.get('available', True), reason=app.get('reason') or '',
                         glyph='window', tip='Opens %s in %s, in a window of its own' % (Path(path).name, app['name'])))
    out.append(Entry('open:with:choose', 'Choose another app…', 'open', lambda:OpenWithDialog(host, path, found).open(), glyph='more',
                     tip='Every app that opens %s, or every app on this computer' % found.get('words', 'this kind of file')))
    out.append(Entry('open:with:always', 'Always open %s with…' % found.get('words', 'this kind of file'), 'open',
                     lambda:OpenWithDialog(host, path, found, always=True).open(), glyph='star',
                     tip='The default app for %s, kept in your own settings; asked of you, never chosen for you' % found.get('words', 'this kind of file')))
    return out


def app_entries(host, t):
    """An app's own rows (its right-click in the Apps panel)."""
    from .context_menu import Entry, copy_text
    app = t.data.get('app') or {};ident = app.get('id') or t.ident;pin_key = t.data.get('pin');out = []
    able = app.get('available', True)
    out.append(Entry('open', 'Open', 'open', lambda:open_app(host, ident), enabled=able, reason=app.get('reason') or '', glyph='window', operation='apps.open'))
    if app.get('takes'):
        def files():
            chosen, _ = QFileDialog.getOpenFileNames(host if isinstance(host, QWidget) else None, 'Open files with %s' % app.get('name', 'it'), str(Path.home()))
            if chosen:open_app(host, ident, chosen)
        out.append(Entry('open:files', 'Open files with it…', 'open', files, enabled=able, reason=app.get('reason') or '', glyph='folder', operation='apps.open'))
    if pin_key:
        out.append(Entry('apps:unpin', 'Take it off your list', 'modify', lambda:(call(host, 'apps.unpin', {'key': pin_key}), say(host, '%s is off your list.' % app.get('name', 'It'))),
                         glyph='previous', operation='apps.unpin'))
    elif not str(ident).startswith('pin:'):
        out.append(Entry('apps:pin', 'Keep it on your list', 'modify', lambda:(call(host, 'apps.pin', {'id': ident}), say(host, '%s is on your list in Apps.' % app.get('name', 'It'))),
                         glyph='star', operation='apps.pin'))
    entry = app.get('entry')
    if entry:out.append(Entry('copy:path', 'Copy where its entry is', 'edit', lambda:copy_text(host, entry, 'Copied the path'), glyph='copy'))
    return out


def context_entries(host, t):
    """context_menu's provider (1.0 S2): Open with on one file, and an installed app's own rows."""
    if t.surface == 'apps' and t.kind == 'app':return app_entries(host, t)
    if t.kind in ('files', 'empty', 'folder'):return []
    path_of = file_of(host, t)
    if path_of is None:return []
    from .context_menu import Entry

    def default():
        try:path = path_of()
        except (ValueError, OSError, KeyError) as exc:return say(host, str(exc))
        if not open_default(host, path):say(host, 'Open with is not available here.')
    return [Entry('open:outside', "Open with this computer's app", 'open', default, glyph='window', operation='apps.for, apps.open',
                  tip='Its default app, in a window of its own; with none, Open with asks which'),
            Entry('open:with', 'Open with', 'open', submenu=lambda:with_entries(host, path_of), glyph='window', operation='apps.for',
                  tip='The apps on this computer that open this kind of file')]
