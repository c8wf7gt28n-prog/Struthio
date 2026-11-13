"""Find, in whatever is open in the centre.

Until 0.5, Find worked in a text file only, through a dialog, and the bar's Find was dimmed on every other page with
the words "This view has no find of its own yet". The owner, 13 November 2026: "If there is anything that you want to
add or subtract or change in the program ... don't hold back." This is the first thing added: a control that is dimmed
on most pages is a hole in the bar.

One line under the bar's controls. It searches what the open page shows: a passage of writing, the cells of a table,
the rows of a list, the lines of a finding, the text of a PDF page. Enter (or ›) goes to the next place, Shift+Enter
(or ‹) to the one before, Esc closes and gives the keyboard back to the page. It says how many places there are and
which one this is. Finding changes nothing: it selects and scrolls, and that is all.

A page may name what is searched (centre_find_in, returning one of its views); otherwise the largest view of writing or
of rows that the page is showing is searched, and a page made of lines of words (a finding) is searched line by line.
"""
import re

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPlainTextEdit, QPushButton,
                               QScrollArea, QStackedWidget, QTableView, QTabWidget, QTextEdit, QTreeWidget, QTreeWidgetItemIterator, QWidget)

from . import boss_theme as t

MOST = 2000             # places counted; past this the count says so instead of counting on
CELLS = 300000          # cells of a table looked at for one search
TAGS = re.compile(r'<[^>]+>')
WRITING = (QPlainTextEdit, QTextEdit)
ROWS = (QTableView, QTreeWidget, QListWidget)


def words_of(label):
    """The words a label shows, without the marks that shape them."""
    text = label.text()
    return TAGS.sub('', text) if '<' in text else text


def lines_of(page):
    return [label for label in page.findChildren(QLabel) if label.isVisible() and words_of(label).strip()]


def subject(page, editor=None):
    """What Find searches on this page, or None when the page shows nothing that can be searched."""
    if page is None:return None
    if editor is not None:return editor                     # a text file: the file itself
    named = getattr(page, 'centre_find_in', None)
    if callable(named):
        try:
            view = named()
            if view is not None:return view
        except Exception:  # noqa: BLE001 - a page that cannot say is searched like any other
            pass
    if isinstance(page, WRITING + ROWS):return page
    views = [view for kind in WRITING + ROWS for view in page.findChildren(kind) if view.isVisible() and view.width() > 120 and view.height() > 80]
    if views:return max(views, key=lambda view: view.width() * view.height())
    return page if lines_of(page) else None


def places(what, needle):
    """Every place the words are, in the order a reader meets them, and whether there were more than were counted."""
    found = [];needle = needle.lower()
    if isinstance(what, WRITING):
        document = what.document();cursor = document.find(needle, 0)
        while not cursor.isNull() and len(found) < MOST:
            found.append((cursor.selectionStart(), cursor.selectionEnd()));cursor = document.find(needle, cursor)
        return found, not cursor.isNull()
    if isinstance(what, QTreeWidget):
        walk = QTreeWidgetItemIterator(what)
        while walk.value() is not None and len(found) < MOST:
            item = walk.value()
            if any(needle in item.text(column).lower() for column in range(item.columnCount())):found.append(item)
            walk += 1
        return found, walk.value() is not None
    if isinstance(what, QListWidget):
        found = [what.item(row) for row in range(what.count()) if needle in what.item(row).text().lower()]
        return found[:MOST], len(found) > MOST
    if isinstance(what, QTableView):
        model = what.model()
        if model is None:return [], False
        rows, columns = model.rowCount(), model.columnCount();looked = 0
        for row in range(rows):
            if what.isRowHidden(row):continue
            for column in range(columns):
                looked += 1
                if looked > CELLS or len(found) >= MOST:return found, True
                value = model.index(row, column).data()
                if value is not None and needle in str(value).lower():found.append((row, column))
        return found, False
    found = [label for label in lines_of(what) if needle in words_of(label).lower()]
    return found[:MOST], len(found) > MOST


def reveal(view):
    """Bring a view to the front if it sits on a tab of its page that is not the one showing."""
    at = view
    while at is not None:
        up = at.parentWidget()
        if isinstance(up, QStackedWidget) and isinstance(up.parentWidget(), QTabWidget) and up.currentWidget() is not at:
            up.parentWidget().setCurrentWidget(at)
        at = up


class FindLine(QWidget):
    """The line itself. It belongs to the bar above the work and is shown only while something is being looked for."""

    def __init__(self, bar):
        super().__init__(bar)
        self.bar = bar;self.what = None;self.found = [];self.at = -1;self.more = False;self.back_to = None;self.mark = None
        self.setObjectName('CentreFindLine')
        row = QHBoxLayout(self);row.setContentsMargins(10, 0, 10, 5);row.setSpacing(6)
        self.says = QLabel('Find');self.says.setObjectName('CentreFindSays')
        self.line = QLineEdit();self.line.setObjectName('CentreFindWords');self.line.setAccessibleName('Find in what is open')
        self.line.setPlaceholderText('words to find');self.line.setClearButtonEnabled(False);self.line.setMaximumWidth(420)
        self.count = QLabel('');self.count.setObjectName('CentreFindCount');self.count.setMinimumWidth(96)
        from .tool_faces import wear

        def control(words, tip, does, glyph):
            button = QPushButton(words);button.setCursor(Qt.PointingHandCursor);button.setFocusPolicy(Qt.TabFocus);button.setToolTip(tip)
            button.clicked.connect(does);return wear(button, glyph)

        self.before = control('‹ Before', 'The place before', lambda: self.step(-1), 'previous')
        self.after = control('Next ›', 'The next place', lambda: self.step(1), 'next')
        self.shut = control('Close', 'Close Find', self.close_line, '')
        for part in (self.says, self.line, self.before, self.after, self.count):row.addWidget(part)
        row.addStretch(1);row.addWidget(self.shut)
        self.wait = QTimer(self);self.wait.setSingleShot(True);self.wait.setInterval(140);self.wait.timeout.connect(self.search)
        self.line.textChanged.connect(lambda _='': self.wait.start())
        self.line.installEventFilter(self);self.hide()

    # ---- opening and closing -----------------------------------------------------------------------------------------
    def open(self, what):
        from PySide6.QtWidgets import QApplication
        if self.isHidden():self.back_to = QApplication.focusWidget()
        self.what = what;self.show()
        chosen = ''
        try:
            if isinstance(what, WRITING):chosen = what.textCursor().selectedText()
        except RuntimeError:
            pass
        if chosen and ' ' not in chosen and len(chosen) < 80:self.line.setText(chosen)
        self.line.setFocus(Qt.ShortcutFocusReason);self.line.selectAll();self.search()

    def close_line(self):
        if self.isHidden():return
        self.wait.stop();self.unmark();self.hide();self.found = [];self.at = -1
        back = self.back_to;self.back_to = None;self.what = None
        try:
            if back is not None and back.isVisible():back.setFocus(Qt.OtherFocusReason)
        except RuntimeError:      # what had the keyboard is gone
            pass

    def eventFilter(self, watched, event):
        if watched is self.line and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self.close_line();return True
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self.wait.stop()
                if self.found and self._searched == self.line.text():self.step(-1 if event.modifiers() & Qt.ShiftModifier else 1)
                else:self.search()
                return True
        return False

    # ---- looking -----------------------------------------------------------------------------------------------------
    _searched = None

    def search(self):
        words = self.line.text();self._searched = words;self.unmark()
        if not words.strip() or self.what is None:
            self.found = [];self.at = -1;self.more = False;self.say();return
        try:
            self.found, self.more = places(self.what, words)
        except RuntimeError:      # the page replaced what was being searched: look at the page as it is now
            self.what = self.bar.find_subject();self.found, self.more = (places(self.what, words) if self.what is not None else ([], False))
        self.at = -1
        if self.found:self.step(1)
        else:self.say()

    def step(self, way):
        if not self.found:
            self.search() if self.line.text().strip() and self._searched != self.line.text() else None;return
        self.at = (self.at + way) % len(self.found)
        try:
            self.go(self.found[self.at])
        except RuntimeError:      # a row or a line that was found is gone: search again, once
            self.what = self.bar.find_subject();self.found, self.more = (places(self.what, self.line.text()) if self.what is not None else ([], False))
            self.at = 0 if self.found else -1
            if self.found:
                try:self.go(self.found[0])
                except RuntimeError:
                    self.found = [];self.at = -1
        self.say()

    def go(self, place):
        what = self.what;reveal(what)
        if isinstance(what, WRITING):
            cursor = what.textCursor();cursor.setPosition(place[0]);cursor.setPosition(place[1], QTextCursor.KeepAnchor)
            what.setTextCursor(cursor);what.ensureCursorVisible()
            host = self.bar.host
            if hasattr(host, 'find_text'):host.find_text = self.line.text()      # F3 goes on from here when the line is closed
        elif isinstance(what, QTableView):
            index = what.model().index(place[0], place[1]);what.setCurrentIndex(index);what.scrollTo(index, QAbstractItemView.PositionAtCenter)
        elif isinstance(what, (QTreeWidget, QListWidget)):
            what.setCurrentItem(place);what.scrollToItem(place, QAbstractItemView.PositionAtCenter)
        else:
            self.mark_line(place)

    def mark_line(self, label):
        """A line of a page of words: brought into view, with an amber rule round it."""
        at = label.parentWidget()
        while at is not None and not isinstance(at, QScrollArea):
            holder = at.parentWidget()
            if isinstance(holder, QScrollArea) or (holder is not None and isinstance(holder.parentWidget(), QScrollArea)):
                area = holder if isinstance(holder, QScrollArea) else holder.parentWidget()
                area.ensureWidgetVisible(label, 40, 80);break
            at = holder
        self.unmark()
        frame = QFrame(label.parentWidget());frame.setObjectName('CentreFindMark');frame.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        frame.setStyleSheet('QFrame#CentreFindMark {background:transparent;border:1px solid %s;}' % t.AMBER_EDGE)
        frame.setGeometry(label.geometry().adjusted(-3, -2, 3, 2));frame.show();frame.raise_();self.mark = frame

    def unmark(self):
        mark = self.mark;self.mark = None
        if mark is not None:
            try:mark.hide();mark.deleteLater()
            except RuntimeError:  # its page went first
                pass

    def say(self):
        words = self.line.text().strip();n = len(self.found)
        self.count.setText('' if not words else 'not here' if not n else '%d of %d%s' % (self.at + 1, n, '+' if self.more else ''))
        self.count.setProperty('none', bool(words) and not n)
        for button in (self.before, self.after):button.setEnabled(n > 1)
        style = self.count.style();style.unpolish(self.count);style.polish(self.count)
