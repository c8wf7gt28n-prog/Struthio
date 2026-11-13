"""The centre's small bar: the few controls that carry across whatever is open in the centre.

The owner's whole-build specification: "A familiar toolbar. Use a small fixed group for the actions that carry across
views. Start with Field, Find, Zoom, and Actions. Show Undo, Redo, and Save in consistent places when the active view
supports them ... Aim for roughly ten controls, with fewer where useful." And, for the mouse: "Make Field, Back, Actions ...
reachable with visible controls."

This is the first slice of that bar, and it is made of what the program already does: each control presses an action
Graphite has had for a long time (F9, Ctrl+F, Ctrl+Z, Ctrl+S, the Menu key), so the mouse, the keys and Stacy still do one
thing by one road. What is new is that the controls are visible, always in the same place above the work, and honest: a
control the open view cannot serve is dimmed and its tip says why, instead of being absent in one view and present in the
next.

    ‹ Field   the name of what is open, and whether it is saved      Find   −  +   Undo  Redo   Save
    (and, while something is being looked for, the line Find opens: centre_find)

(0.4.9, the audit of what repeats what: there was an Actions control here that opened the chain menu, which has nothing to
do with what is open. It is gone until it can show what can be done with the open thing; the Menu key and the right
button still open the menus they always did. And Save is lit only when there is something to save.)

It shows while the work is in the centre, and steps aside for the Field and for Home, which have the whole centre.
Nothing here runs on a clock: the controls are looked at again when the open page changes, a moment after the keyboard
moves (never from inside the move: see focus_moved), and when the pointer comes onto the bar.
"""
from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSizePolicy, QTableWidget,
                               QTextEdit, QVBoxLayout, QWidget)

from . import boss_theme as t
from .centre_find import FindLine, subject as find_subject
from .tool_faces import start as start_faces, wear

SIZES = (-4, 12)                # how far the size of one view may be taken from the desk's own, in points
MARK = '/*centre-size*/'        # the piece of a view's own style sheet that carries its size, so it can be replaced


class CentreBar(QWidget):
    def __init__(self, host):
        super().__init__(host)
        self.host = host;self.setObjectName('CentreBar');self.setAccessibleName('The centre’s controls');self._looking = False
        whole = QVBoxLayout(self);whole.setContentsMargins(0, 0, 0, 0);whole.setSpacing(0)      # the controls, and under them the line Find opens
        row = QHBoxLayout();row.setContentsMargins(10, 4, 10, 4);row.setSpacing(6);whole.addLayout(row)

        def control(words, name, does, key='', glyph='', tone=None):
            button = QPushButton(words);button.setObjectName(name);button.setCursor(Qt.PointingHandCursor)
            button.setFocusPolicy(Qt.TabFocus)      # a click leaves the keyboard where it is: Undo is for the page being typed in
            button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed);button.setProperty('key', key)
            button.clicked.connect(lambda: (does(), self.sync()))
            return wear(button, glyph, tone)        # words on a plate, or its glyph when the owner chooses Icons (tool_faces)

        self.field = control('‹ Field', 'CentreField', self.to_field, 'F9', 'field', 'live')
        self.title = QLabel();self.title.setObjectName('CentreTitle');self.title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.title.setTextFormat(Qt.PlainText);self.title.setCursor(Qt.PointingHandCursor);self.title.installEventFilter(self)      # a click on the name gives its address
        self.find = control('Find', 'CentreFind', self.open_find, 'Ctrl+F', 'find')
        self.smaller = control('−', 'CentreSmaller', lambda: self.resize_view(-1), glyph='smaller')
        self.larger = control('+', 'CentreLarger', lambda: self.resize_view(1), glyph='larger')
        self.undo = control('Undo', 'CentreUndo', lambda: self.in_place('undo'), 'Ctrl+Z', 'undo')
        self.redo = control('Redo', 'CentreRedo', lambda: self.in_place('redo'), 'Ctrl+Y', 'redo')
        self.save = control('Save', 'CentreSave', lambda: self.host.a_save.trigger(), 'Ctrl+S', 'save')
        # The name of what is open, and whether it is saved, is said here, once. (0.5.0 moved it to the head of the window;
        # 0.5.3 brought it back: the owner wanted the head's middle left free.)
        row.addWidget(self.field);row.addSpacing(8);row.addWidget(self.title, 1)
        for group in ((self.find,), (self.smaller, self.larger), (self.undo, self.redo), (self.save,)):
            row.addSpacing(8)
            for button in group:row.addWidget(button)
        self.finder = FindLine(self);whole.addWidget(self.finder);self._found_on = None
        self.restyle()
        host.tabs.currentChanged.connect(lambda _=0: self.sync())
        host.central_stack.currentChanged.connect(lambda _=0: self.sync())
        app = QApplication.instance()
        if app is not None:app.focusChanged.connect(self.focus_moved)
        self.sync()

    # ---- how it looks ------------------------------------------------------------------------------------------------
    def restyle(self):
        """Plates, not bare words and not bright outlines: on this bar a control is told from the name beside it by a ground a
        shade lighter and a quiet edge. Under the pointer it answers in the pointer's green, as everything on the desk does;
        without its plate, and dim, when the open view cannot serve it."""
        self.setStyleSheet(
            'QWidget#CentreBar {background:%(GROUND)s;border-bottom:1px solid %(LINE)s;} '
            'QWidget#CentreBar QPushButton {color:%(TEXT)s;background:%(RAISED)s;border:1px solid %(LINE)s;border-radius:0;padding:3px 11px;text-align:center;} '
            'QWidget#CentreBar QPushButton:hover {background:%(TEAL_SOFT)s;border:1px solid %(TEAL_EDGE)s;color:%(TEAL_TEXT)s;} '
            'QWidget#CentreBar QPushButton:focus {border:1px solid %(AMBER_EDGE)s;} '
            'QWidget#CentreBar QPushButton:disabled {color:%(LINE_MID)s;background:transparent;border:1px solid %(LINE)s;} '
            'QWidget#CentreBar QPushButton#CentreField {background:%(TEAL_SOFT)s;border:1px solid %(TEAL_EDGE)s;color:%(TEAL_TEXT)s;} '
            'QWidget#CentreBar QLabel#CentreTitle {color:%(QUIET)s;background:transparent;} '
            'QWidget#CentreBar QLabel#CentreFindSays, QWidget#CentreBar QLabel#CentreFindCount {color:%(QUIET)s;background:transparent;} '
            'QWidget#CentreBar QLabel#CentreFindCount[none="true"] {color:%(AMBER_TEXT)s;} '
            'QWidget#CentreBar QLineEdit#CentreFindWords {color:%(TEXT)s;background:%(TERMINAL_GROUND)s;border:1px solid %(LINE)s;border-radius:0;padding:3px 8px;} '
            'QWidget#CentreBar QLineEdit#CentreFindWords:focus {border:1px solid %(AMBER_EDGE)s;padding:3px 8px;}'
            % {name: getattr(t, name) for name in ('GROUND', 'LINE', 'LINE_MID', 'RAISED', 'TEXT', 'TEAL_SOFT', 'TEAL_TEXT', 'AMBER_EDGE', 'AMBER_TEXT', 'TEAL_EDGE', 'QUIET', 'TERMINAL_GROUND')})

    # ---- Find ----------------------------------------------------------------------------------------------------------
    def find_subject(self):
        """What Find would search in the page that is open, or None."""
        try:return find_subject(self.page(), self.host.current_editor())
        except RuntimeError:
            return None

    def open_find(self):
        """Open the line under the controls on what is open. False when this page shows nothing that can be searched."""
        what = self.find_subject()
        if what is None:return False
        self._found_on = self.page();self.finder.open(what);return True

    # ---- what is open, and what it can do ------------------------------------------------------------------------------
    def page(self):
        """The page in the centre, or None when the Field or Home has the centre."""
        host = self.host
        if getattr(host, '_field_active', False) or getattr(host, '_home_active', False):return None
        if host.central_stack.currentWidget() is not getattr(host, 'workspace_split', None):return None
        return host.tabs.currentWidget()

    def typed_in(self, page):
        """The place being typed in on this page: the text file itself, or the line or passage of it that has the keyboard."""
        editor = self.host.current_editor()
        if editor is not None:return editor
        at = QApplication.focusWidget()
        if page is not None and isinstance(at, (QLineEdit, QPlainTextEdit, QTextEdit)) and (at is page or page.isAncestorOf(at)):return at
        return None

    def sized(self, page):
        """The part of this page whose size the − and + change: the page itself when it offers that, else its largest table
        or passage of writing. None when it has neither."""
        if page is None:return None
        if callable(getattr(page, 'centre_size', None)):return page
        if isinstance(page, (QPlainTextEdit, QTextEdit)):return page
        views = [view for kind in (QTableWidget, QPlainTextEdit, QTextEdit) for view in page.findChildren(kind) if view.isVisible() and view.width() > 120 and view.height() > 80]
        return max(views, key=lambda view: view.width() * view.height()) if views else None

    def sync(self):
        """Look at the open page again: show or hide the bar, name what is open, and dim what it cannot serve (saying why)."""
        page = self.page();self.setVisible(page is not None)
        if page is None:return
        host = self.host;editor = host.current_editor();place = self.typed_in(page)
        index = host.tabs.currentIndex();name = host.tabs.tabText(index).replace('&', '') if index >= 0 else ''
        waiting = getattr(getattr(host, 'concern', None), 'current_attention', None)
        if waiting and waiting.get('title'):name = str(waiting['title'])
        if callable(getattr(page, 'centre_title', None)):      # a page that holds several things says which one is open
            try:name = str(page.centre_title()) or name
            except Exception:  # noqa: BLE001 - a name is never worth an error
                pass
        unsaved = bool(getattr(page, 'is_dirty', None) and page.is_dirty()) or bool(editor is not None and editor.document().isModified())
        can_save = callable(getattr(page, 'save_concern_note', None)) or hasattr(page, 'can_close_pdf') or (editor is not None and not editor.isReadOnly())
        knows = callable(getattr(page, 'is_dirty', None)) or editor is not None      # the view can say whether it has changes
        itself = bool(getattr(page, 'saves_itself', False))                           # the view saves as it goes
        said = name.rstrip(' •') + ('  ·  read only' if editor is not None and editor.isReadOnly() else '  ·  not saved yet' if unsaved else '')
        self._said = said;self._name = name.rstrip(' •');self.fit_title()

        def offer(button, on, what, why):
            button.setEnabled(bool(on));key = button.property('key')
            button.setToolTip(what if on else why)      # 0.5.2: no key beside the words; the key still works

        offer(self.field, True, 'Back to the Field: your work as tiles and wires, at the tile this was opened from', '')
        if self.finder.isVisible() and page is not self._found_on:self.finder.close_line()     # another page came to the front: its words are not these
        offer(self.find, self.find_subject() is not None, 'Find in what is open', 'This page shows nothing that can be searched.')
        view = self.sized(page)
        offer(self.smaller, view is not None, 'Smaller: this view only', 'This view has nothing whose size can be changed here.')
        offer(self.larger, view is not None, 'Larger: this view only', 'This view has nothing whose size can be changed here.')
        undo = redo = False
        if isinstance(place, QLineEdit):undo, redo = place.isUndoAvailable(), place.isRedoAvailable()
        elif place is not None:undo, redo = place.document().isUndoAvailable(), place.document().isRedoAvailable()
        nowhere = 'Undo and Redo work where you are typing: click in the text first.' if place is None else 'Nothing to take back here.'
        offer(self.undo, undo, 'Take back the last change where you are typing', nowhere)
        offer(self.redo, redo, 'Put back what was taken back', nowhere if place is None else 'Nothing to put back here.')
        # Save is lit when a press would save something: never to be pressed "to be sure".
        why = ('This view has nothing to save: what it shows is a record.' if not can_save else
               'This page saves itself as you write; there is nothing to press.' if itself and not unsaved else
               'Nothing to save: no changes since the last save.')
        offer(self.save, can_save and (unsaved or not knows) and not (itself and not unsaved), 'Save this: it has changes that are not saved' if unsaved else 'Save this', why)
        self.save.setText('Save •' if can_save and unsaved else 'Save')

    def fit_title(self):
        words = getattr(self, '_said', '')
        shown = words if self.title.isHidden() else QFontMetrics(self.title.font()).elidedText(words, Qt.ElideMiddle, max(40, self.title.width() - 4))
        self.title.setText(shown);self.title.setToolTip((words + '\nClick for its address.') if words else '')

    def eventFilter(self, watched, event):
        """A click on the name of what is open brings up its address at the head of the window, ready to copy or type over."""
        if watched is getattr(self, 'title', None) and event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            path = getattr(getattr(getattr(self.host, 'shell2', None), 'top', None), 'path', None)
            if path is not None:path.edit_location()
            return True
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event);self.fit_title()

    def enterEvent(self, event):
        self.sync();super().enterEvent(event)       # the pointer is coming for a control: it should say what is true now

    def focus_moved(self, old, new):
        """The keyboard moved: look at the open page again, but not from inside the move. A page may be taking its old parts
        away at this very moment (a finding replaces its whole sheet, and the keyboard leaves a button as that button is
        destroyed). Reading the page then reads parts that are half gone, and Qt ends the program. So the look waits until
        the move is over; several moves in one breath are one look."""
        if self._looking:return
        self._looking = True
        QTimer.singleShot(0, self.look_again)

    def look_again(self):
        self._looking = False
        try:
            if self.isVisible():self.sync()
        except RuntimeError:                         # the window is closing
            pass

    def event(self, event):
        if event.type() == QEvent.FontChange:self.fit_title()
        return super().event(event)

    # ---- what the controls do ------------------------------------------------------------------------------------------
    def to_field(self):
        action = getattr(self.host, 'a_field', None)
        if action is not None:action.trigger()

    def in_place(self, what):
        """Undo or redo in the place being typed in: the same place the control's state was read from, so it never offers
        what it would not do. (Ctrl+Z and Ctrl+Y go to that place by themselves.)"""
        place = self.typed_in(self.page())
        if place is not None and callable(getattr(place, what, None)):getattr(place, what)()

    def resize_view(self, step):
        """Make the open view's table or writing one point larger or smaller. Only this view: the desk's own reading size is
        in Settings. The size is carried in the view's own style sheet, because the desk's sheet sets sizes and would win
        over a font set by hand."""
        page = self.page();view = self.sized(page)
        if view is None:return
        if callable(getattr(view, 'centre_size', None)):
            view.centre_size(step);self.sync();return
        moved = int(view.property('centreSize') or 0)
        base = view.property('centreBase')
        if base is None:
            base = view.fontInfo().pointSizeF() or 12.0;view.setProperty('centreBase', float(base))
        moved = max(SIZES[0], min(SIZES[1], moved + step));view.setProperty('centreSize', moved)
        sheet = view.styleSheet().split(MARK)[0].rstrip()
        own = '' if not moved else ' %s * {font-size:%.1fpt;}' % (MARK, float(base) + moved)
        view.setStyleSheet(sheet + own)
        if isinstance(view, QTableWidget):
            view.verticalHeader().setDefaultSectionSize(max(24, view.fontMetrics().height() + 14))
            for at in range(view.rowCount()):view.setRowHeight(at, view.verticalHeader().defaultSectionSize())


def install(host):
    """Put the bar above the work, once. Returns it."""
    bar = getattr(host, 'centre_bar', None)
    if bar is None:
        start_faces(host)       # Words or Icons: read before the first tool is made
        from .boss_qt import set_glow
        set_glow(host)          # and how strongly this desk glows
        bar = host.centre_bar = CentreBar(host)
        layout = host.center_layout;layout.insertWidget(max(0, layout.indexOf(host.central_stack)), bar)
        bar.sync()
    return bar
