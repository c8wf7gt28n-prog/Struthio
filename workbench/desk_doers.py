"""Desk acts on the live window: one doer per act of desk_acts.ACTS, the guard that keeps every act from opening a window
that asks, the read-back of what the window shows, and the one record each act leaves.

run(host, name, args, door=..., by, origin, word) is the one entry; the door is always named. It checks the arguments
(desk_acts.check), runs the act's doer inside no_dialogs() and watching(), lets the window settle (a row of a second popup
acts on a zero timer), and answers with an envelope: {act, door, ok, by, words, result, error, changed, seconds}. Then it
writes one line in Graphite's journal (activity.record), except for read.desk: reading is not an event.

A right-click row is chosen only when it is listed (desk_acts.MENU_ROWS, PANEL_ROWS): the 0.8.2 review found rows that name
no operation and still change or leave Graphite. Words are typed one character at a time (type_text), never with
QTest.keyClicks, which ends the window on a character outside Latin-1.

The doers do what a person does. The pointer form sends real mouse events (a press and a release, a right-click's
ContextMenu event) to the widget under the thing; the keys form sends the keys a person would press, to where the keyboard
is, and first checks that the keyboard is there. Where no keyboard route exists the pointer form is used and the envelope
says so (by: "pointer"). A change goes through Stacy's hand (shell2.SlateFace.stage, asked=True), so her dial decides as it
does for "set B3 to 300" said to her: done at once with its card, its trail entry and its Undo, or a card that waits for
Approve. What always asks still asks.

Qt is imported when an act runs, never when this module is imported.
"""
import contextlib
import time

from . import desk_acts, stacy_hand
from .assistant_identity import named
from .desk_acts import ACTS, REFUSALS, Refusal, row_words


class _Qt:
    """Qt's names, looked up when first used (this module is imported by the line's door before any act runs)."""
    def __getattr__(self, name):
        from PySide6 import QtCore, QtGui, QtTest, QtWidgets
        for module in (QtCore, QtGui, QtWidgets, QtTest):
            if hasattr(module, name):
                value = getattr(module, name);setattr(self, name, value);return value
        raise AttributeError(name)


Q = _Qt()
WHO = {'her': 'slate', 'terminal': 'shell', 'search': 'find', 'web': 'web', 'log': 'log'}      # the line's modes by whom they go to
WHO_OF = {mode: who for who, mode in WHO.items()}
ROOMS = ('line', 'half', 'tall')
HAND_ACTS = {'files.trash': 'hand.trash', 'files.rename': 'hand.rename', 'files.write': 'hand.write', 'field.set': 'hand.cell'}
FACE_OF = {'work': 'work', 'apps': 'programs', 'network': 'network'}
FACE_WORD = {'work': 'work', 'programs': 'apps', 'network': 'network'}


class DialogReached(Exception):
    """A window that asks was about to open inside an act."""


class Ctx:
    """One act as its doer sees it."""
    def __init__(self, host, name, args, door, word, origin, by):
        self.host = host;self.name = name;self.args = args;self.door = door;self.word = word;self.origin = origin;self.by = by
        self.presses = 0;self.card = None


# -- settling and waiting -------------------------------------------------------------------------------------------------------

def settle(host=None, ms=30, n=3):
    """Let the window do what it queued: deferred rows, layouts, the zero timers of a second popup."""
    app = Q.QApplication.instance()
    for _ in range(n):
        if app is not None:app.processEvents()
        Q.QTest.qWait(ms)


def wait_until(predicate, ms=2000, step=20):
    """Settle until `predicate()` holds or `ms` passes; whether it held."""
    end = time.monotonic() + ms / 1000.0
    while True:
        try:
            if predicate():return True
        except RuntimeError:return False
        if time.monotonic() >= end:return False
        settle(None, step, 1)


def alive(widget):
    try:return widget is not None and widget.isVisible()
    except RuntimeError:return False


# -- the guard: no act ever opens a window that asks ----------------------------------------------------------------------------

GUARDED = (('QInputDialog', ('getText', 'getItem', 'getInt', 'getDouble', 'getMultiLineText')),
           ('QFileDialog', ('getOpenFileName', 'getOpenFileNames', 'getSaveFileName', 'getExistingDirectory', 'exec')),
           ('QMessageBox', ('question', 'information', 'warning', 'critical', 'exec')),
           ('QDialog', ('exec',)), ('QMenu', ('exec',)))


def _swap(cls, name, value, static=False):
    """Put `value` in place of a class's attribute; returns what puts it back (an attribute the class only inherits is removed
    again rather than copied down)."""
    own = name in cls.__dict__;before = cls.__dict__.get(name) if own else None
    setattr(cls, name, staticmethod(value) if static else value)

    def back():
        if own:setattr(cls, name, before)
        else:
            try:delattr(cls, name)
            except AttributeError:pass
    return back


@contextlib.contextmanager
def watching():
    """Inside it, every Kernel operation that is not a read, every open handed to the computer (an address, or a file in the
    computer's own app) and every program started is written down, and still done. It is the act's own account of what it
    changed or left (the envelope's `changed`), so that no answer says nothing was done when something was. Work in the
    background can land here too while the window settles: the list says what happened during the act."""
    from .engineering_kernel import CAPABILITIES, Kernel
    seen = [];backs = []
    classes = [Kernel]
    try:
        from .host_client import HostClient
        classes.append(HostClient)
    except Exception:  # noqa: BLE001 - no host client in this build: the Kernel itself is the only door
        pass
    for cls in classes:
        if 'dispatch' not in cls.__dict__:continue
        original = cls.__dict__['dispatch']

        def dispatch(self, operation, params=None, principal=None, _original=original):
            if CAPABILITIES.get(operation, 'approve') != 'read':seen.append(str(operation))
            return _original(self, operation, params, principal)
        backs.append(_swap(cls, 'dispatch', dispatch))
    opener = Q.QDesktopServices.openUrl

    def open_url(url, _opener=opener):
        seen.append('opened outside Graphite: ' + url.toString()[:200]);return _opener(url)
    backs.append(_swap(Q.QDesktopServices, 'openUrl', open_url, static=True))
    for name in ('start', 'startDetached'):
        started = getattr(Q.QProcess, name)

        def start(*args, _started=started, **kwargs):
            seen.append('a program started');return _started(*args, **kwargs)
        backs.append(_swap(Q.QProcess, name, start))
    try:
        yield seen
    finally:
        for back in reversed(backs):back()


@contextlib.contextmanager
def no_dialogs():
    """Inside it, every call that would open a window that asks (an input box, a file chooser, a message, a dialog's or a
    menu's own loop) records its name and raises DialogReached instead. Callers look these up when they call them, so the
    class attribute is the place to hold them. The record survives a caller that swallows the exception (context_menu.perform
    does), so the act still knows a dialog was reached."""
    reached = [];saved = []
    for class_name, names in GUARDED:
        cls = getattr(Q, class_name)
        for name in names:
            own = name in cls.__dict__;before = cls.__dict__.get(name) if own else None

            def raiser(*args, _label='%s.%s' % (class_name, name), **kwargs):
                reached.append(_label);raise DialogReached(_label)
            saved.append((cls, name, own, before))
            setattr(cls, name, staticmethod(raiser) if class_name != 'QDialog' and name != 'exec' else raiser)
    try:
        yield reached
    finally:
        for cls, name, own, before in reversed(saved):
            if own:setattr(cls, name, before)
            else:
                try:delattr(cls, name)
                except AttributeError:pass


# -- where things are -------------------------------------------------------------------------------------------------------------

def surface(host):
    """What the centre shows: 'field', 'home' or 'workspace' (read from the central stack, never from the tabs: the tabs keep
    their page while the Field is in front)."""
    page = getattr(host, 'field_page', None);stack = getattr(host, 'central_stack', None)
    if page is not None and stack is not None and stack.currentWidget() is page:return 'field'
    if getattr(host, '_home_active', False):return 'home'
    return 'workspace'


def the_field(host):
    """(page, view) when the Field is in front; refused otherwise."""
    if surface(host) != 'field':raise Refusal('NOT_HERE', 'The Field is not in front.')
    page = host.field_page;return page, page.view


def chosen(view):
    obj = view.selected()
    if obj is None:raise Refusal('NOT_HERE', 'Nothing is selected in the Field.')
    return obj


def find_sheet(view, title=None, ident=None):
    """A sheet of this face of the Field by its id, or by its title: exact first, else the one whose title holds the words."""
    if ident:
        obj = view.field.get(ident)
        if obj is None:raise Refusal('NOT_HERE', 'No sheet with the id “%s” is on this face of the Field.' % ident)
        return obj
    want = str(title).casefold().strip()
    exact = [o for o in view.field.objects if o.title.casefold().strip() == want]
    if len(exact) == 1:return exact[0]
    near = exact or [o for o in view.field.objects if want in o.title.casefold()]
    if not near:raise Refusal('NOT_HERE', 'No sheet named “%s” is on this face of the Field.' % title)
    if len(near) > 1:raise Refusal('NOT_HERE', 'Two sheets are named like “%s”: %s.' % (title, ', '.join(o.title for o in near[:4])))
    return near[0]


def sheet_point(view, ident):
    """The middle of a sheet as it is seen; refused when it is out of sight."""
    body = view._layout();rect = view.sheet_rect(ident, body)
    if rect is None or not body.contains(rect.center()):
        raise Refusal('NOT_HERE', 'That sheet is out of sight; point.zoom with to=whole brings the whole desk in.')
    return rect.center()


def files_tab(host):
    from .files_qt import FilesTab
    tab = host.tabs.currentWidget() if getattr(host, 'tabs', None) is not None else None
    if not isinstance(tab, FilesTab) or surface(host) != 'workspace':raise Refusal('NOT_HERE', 'Files is not in front.')
    return tab


def file_items(tab):
    """[(entry, item)] of the folder shown, in the view that shows it."""
    if tab.mode == 'list':
        view = tab.table;return view, [(view.topLevelItem(i).data(0, Q.Qt.UserRole), view.topLevelItem(i)) for i in range(view.topLevelItemCount())]
    view = tab.icons;return view, [(view.item(i).data(Q.Qt.UserRole), view.item(i)) for i in range(view.count())]


def file_item(tab, name):
    view, items = file_items(tab)
    found = next((item for entry, item in items if entry and (entry.get('name') == name or entry.get('path') == name)), None)
    if found is None:raise Refusal('NOT_HERE', 'No file named “%s” is in this folder of Files.' % name)
    return view, found


def current_entry(view):
    item = view.currentItem()
    if item is None:return None
    return item.data(0, Q.Qt.UserRole) if isinstance(view, Q.QTreeWidget) else item.data(Q.Qt.UserRole)


# -- sending what a person sends ----------------------------------------------------------------------------------------------------

def mouse(widget, pos, button=None, release=True):
    """A press (and its release) of a mouse button at `pos` in `widget`, as the window system delivers it."""
    button = button if button is not None else Q.Qt.LeftButton
    at = Q.QPointF(pos);gp = Q.QPointF(widget.mapToGlobal(at.toPoint()))
    Q.QApplication.sendEvent(widget, Q.QMouseEvent(Q.QEvent.MouseButtonPress, at, gp, button, button, Q.Qt.NoModifier))
    if release:Q.QApplication.sendEvent(widget, Q.QMouseEvent(Q.QEvent.MouseButtonRelease, at, gp, button, Q.Qt.NoButton, Q.Qt.NoModifier))


def right_click(widget, pos):
    """A right-click's ContextMenu event at `pos` in `widget` (the router opens Graphite's menu for what is there)."""
    at = Q.QPoint(int(round(pos.x())), int(round(pos.y())))
    Q.QApplication.sendEvent(widget, Q.QContextMenuEvent(Q.QContextMenuEvent.Mouse, at, widget.mapToGlobal(at)))


def key(c, widget, code, modifiers=None, times=1):
    """Press a key on `widget` (where the keyboard is), `times` times; each press is counted."""
    for _ in range(times):
        Q.QTest.keyClick(widget, code, modifiers if modifiers is not None else Q.Qt.NoModifier);c.presses += 1;settle(None, 10, 1)


def type_text(c, widget, text):
    """Type words on `widget` (where the keyboard is) one character at a time, as a keyboard sends each: a press and a
    release carrying the character. Never QTest.keyClicks: with the pinned Qt it ends the whole window on any character
    outside Latin-1 (the curly quotes Graphite writes everywhere, Ω, ≥), and it reads a carriage return as Return."""
    for ch in str(text):
        for kind in (Q.QEvent.KeyPress, Q.QEvent.KeyRelease):
            Q.QApplication.sendEvent(widget, Q.QKeyEvent(kind, 0, Q.Qt.NoModifier, ch))
        c.presses += 1
    settle(c.host)


def sequence(c, widget, seq):
    """A key sequence read from an action (never written here): its first combination pressed on `widget`."""
    if seq.isEmpty():return False
    combo = seq[0];key(c, widget, combo.key(), combo.keyboardModifiers());return True


def keyboard_on(widget):
    return Q.QApplication.focusWidget() is widget


def field_keys(c, view, codes):
    """Keys to the Field, after checking the keyboard is there."""
    if not keyboard_on(view):raise Refusal('NOT_HERE', 'The keyboard is not on the Field.')
    for code in codes:
        if isinstance(code, tuple):key(c, view, code[0], code[1])
        else:key(c, view, code)


WAY_KEY = {'left': 'Key_Left', 'right': 'Key_Right', 'up': 'Key_Up', 'down': 'Key_Down', 'first': 'Key_Home', 'last': 'Key_End',
           'next_waiting': 'Key_A', 'before': 'Key_Backspace'}


def way_key(way):
    return getattr(Q.Qt, WAY_KEY[way])


# -- the head's menus and the line's search ---------------------------------------------------------------------------------------

def head_word(host, menu):
    for word in host.shell2.top.menu_words():
        if word.text() == menu:return word
    raise Refusal('NOT_HERE', 'No menu named “%s” is across the head.' % menu)


def head_popup(host, menu):
    """A head menu opened as a click on its word opens it (popup at the word's foot; never the word's own nested loop)."""
    word = head_word(host, menu);m = word.menu()
    m.popup(word.mapToGlobal(Q.QPoint(0, word.height())));settle(host)
    return word, m


def menu_rows(m):
    return [row_words(a.text()) for a in m.actions() if not a.isSeparator() and a.isVisible() and a.text()]


def click_menu_row(c, m, row):
    """Click a row of an open QMenu at its middle; True when its action fired."""
    action = next((a for a in m.actions() if not a.isSeparator() and row_words(a.text()) == row), None)
    if action is None:raise Refusal('NOT_HERE', 'No row “%s” is on that menu.' % row)
    fired = []

    def heard(*_):fired.append(1)
    action.triggered.connect(heard)
    try:
        Q.QTest.mouseClick(m, Q.Qt.LeftButton, Q.Qt.NoModifier, m.actionGeometry(action).center());settle(c.host)
    finally:
        try:action.triggered.disconnect(heard)
        except (RuntimeError, TypeError):pass
    if not fired:raise Refusal('FAILED', REFUSALS['FAILED'] % 'the row did not answer the click')
    return action


def head_row(c, menu, row, by):
    """Choose an allowed row of a head menu: by pointer, the menu opened at its word and the row clicked; by keys, the line's
    search for the row's words, its COMMANDS row reached with the arrows, and Enter. Returns the form used."""
    allowed = desk_acts.HEAD_ROWS.get(menu, ())
    if row not in allowed:raise Refusal('NOT_ALLOWED_ROW', REFUSALS['NOT_ALLOWED_ROW'])
    if by == 'keys' and by_search(c, row):return 'keys'
    _, m = head_popup(c.host, menu)
    click_menu_row(c, m, row)
    return 'pointer'


def unsent(host):
    """Words in the writing line that no act put there: the owner's, not to be lost."""
    text = host.type_bar.box.text().strip()
    return bool(text) and text != str(getattr(host, '_desk_put', '') or '').strip()


def by_search(c, words):
    """The line's search, as a person reaches a command by keys: the search key (read from its shortcut), the words typed,
    the arrows down to the COMMANDS row that says them, and Enter. False when no such row is offered (the caller then uses
    the pointer)."""
    host = c.host;bar = host.type_bar;box = bar.box
    if unsent(host):raise Refusal('UNSENT', REFUSALS['UNSENT'])
    key(c, host, Q.Qt.Key_K, Q.Qt.ControlModifier)      # the search's own key (shell2.Shell2.install)
    if bar.target != 'find' or not keyboard_on(box):return False
    type_text(c, box, words)
    popup = box.popup;rows = popup.list
    want = str(words).casefold()

    def label(item):return item.text().strip().casefold()
    targets = [i for i in range(rows.count()) if rows.item(i).flags() & Q.Qt.ItemIsEnabled and label(rows.item(i)) == want]
    if not targets:
        targets = [i for i in range(rows.count()) if rows.item(i).flags() & Q.Qt.ItemIsEnabled and label(rows.item(i)).endswith(' ' + want)]
    if not popup.isVisible() or not targets:
        box.clear();host._desk_put = '';return False
    for _ in range(rows.count()):
        if rows.currentRow() == targets[0]:break
        key(c, box, Q.Qt.Key_Down)
    if rows.currentRow() != targets[0]:
        box.clear();return False
    key(c, box, Q.Qt.Key_Return);settle(host)
    host._desk_put = ''
    return True


# -- the right-click menu ---------------------------------------------------------------------------------------------------------

def root_menu(host):
    m = getattr(host, 'context_menu', None)
    return m if alive(m) else None


def deepest(host):
    m = root_menu(host)
    if m is None:return None
    while getattr(m, 'child', None) is not None and alive(m.child):m = m.child
    return m


def line_panel(host):
    from .context_menu import LinePanel
    m = deepest(host)
    while m is not None and not isinstance(m, LinePanel):m = m.parent_menu
    if m is None:raise Refusal('NOT_HERE', 'No line panel is open; choose Then first.')
    return m


def find_row(menu, seg):
    """The row on this screen whose key or words are `seg`; or (the row of a folded group that holds it, None)."""
    want = str(seg).casefold().strip()
    for row in list(menu.rows_by_key.values()):
        try:
            if row.entry.key.casefold() == want or row_words(row.word).casefold() == want or row_words(row.entry.label).casefold() == want:return row, None
        except RuntimeError:continue
    for row in list(menu.rows_by_key.values()):      # a long screen folds its largest group (or its tail) behind one row
        entry = row.entry
        if entry.key.startswith(('group:', 'page:next')) and callable(entry.submenu):
            try:inner = entry.submenu()
            except Exception:  # noqa: BLE001 - a group that cannot be read hides nothing
                continue
            if any(e.key.casefold() == want or row_words(e.label).casefold() == want for e in inner):return None, row
    return None, None


def changing_row(entry):
    """Whether a row changes something (its operation is not a read, or it asks first): (True, the act that does it through
    her hand or None)."""
    from .engineering_kernel import CAPABILITIES
    operations = [o.strip() for o in str(entry.operation or '').split(',') if o.strip()]
    changing = [o for o in operations if CAPABILITIES.get(o, 'approve') != 'read']
    if changing or entry.caption == 'asks' or entry.asks:
        return True, next((HAND_ACTS[o] for o in changing if o in HAND_ACTS), None)
    return False, None


def row_refusal(entry, in_panel):
    """Why an act may not choose this row, as a Refusal, or None. A row is chosen only when it is listed (desk_acts.MENU_ROWS;
    PANEL_ROWS in the line panel), names no operation that changes and does not ask first: a row that names nothing can
    still change or leave, so naming nothing is never enough."""
    changes, act = changing_row(entry)
    if changes and act:return Refusal('CHANGES_ROW', REFUSALS['CHANGES_ROW'] % act)
    if changes:return Refusal('CHANGES_ROW_YOURS', REFUSALS['CHANGES_ROW_YOURS'])
    if not desk_acts.listed(entry.key, desk_acts.PANEL_ROWS if in_panel else desk_acts.MENU_ROWS):
        return Refusal('NOT_ALLOWED_ROW', REFUSALS['NOT_ALLOWED_ROW'])
    return None


def keys_to(c, menu, row, last):
    """The keysprobe walk: from where the keyboard is in this menu, Down or Up to the row, then `last` (Right opens a deeper
    screen, Enter chooses)."""
    rows = menu.focusables()
    if row not in rows:raise Refusal('FAILED', REFUSALS['FAILED'] % 'that row cannot be reached by keys')
    focus = Q.QApplication.focusWidget();at = rows.index(focus) if focus in rows else -1
    steps = rows.index(row) - at
    for _ in range(abs(steps)):
        focus = Q.QApplication.focusWidget()
        key(c, focus if focus in menu.focusables() else menu, Q.Qt.Key_Down if steps > 0 else Q.Qt.Key_Up)
    if Q.QApplication.focusWidget() is not row:raise Refusal('FAILED', REFUSALS['FAILED'] % 'the keys did not reach the row')
    key(c, row, last)


def choose_row(c, menu, row, by):
    """One row chosen, by a click or by the keys; the window settles after (a second popup's rows act on a zero timer)."""
    if by == 'keys':keys_to(c, menu, row, Q.Qt.Key_Right if row.sub() else Q.Qt.Key_Return)
    else:Q.QTest.mouseClick(row, Q.Qt.LeftButton);settle(c.host)
    settle(c.host)


def walk(c, segments, by, guard=True):
    """Choose the rows of a path in the open menu, each on the screen the one before opened. The last row, when it acts, is
    checked first: a row that changes something is refused (and names the act that does it through her hand)."""
    from .context_menu import LinePanel
    host = c.host;chosen_row = None;outcome = None
    for n, seg in enumerate(segments):
        menu = deepest(host)
        if menu is None:raise Refusal('NOT_HERE', 'No menu is open.')
        row, group = find_row(menu, seg)
        if row is None and group is not None:
            choose_row(c, menu, group, by);menu = deepest(host);row, _ = find_row(menu, seg)
        if row is None:
            shown = [r.word for r in menu.rows_by_key.values()][:12]
            raise Refusal('NOT_HERE', 'No row “%s” is on this menu; it shows: %s.' % (seg, ', '.join(shown)))
        if not row.isEnabled():raise Refusal('NOT_HERE', 'That row cannot act now: %s.' % (row.entry.reason or 'it is dim'))
        last = n == len(segments) - 1
        if not row.sub():
            if not last:raise Refusal('BAD_ARGUMENTS', 'The row “%s” does not open further rows.' % seg)
            if guard:
                refusal = row_refusal(row.entry, isinstance(menu, LinePanel))
                if refusal is not None:raise refusal
            host._context_last = None;host._context_said = None      # what the row says now, not what an earlier one said
        chosen_row = row.entry.key;is_then = row.entry.key == 'then';was = deepest(host)
        depth = len(getattr(was, 'stack', []) or []);line = getattr(was, 'line', None)
        in_panel = isinstance(menu, LinePanel) and not (row.entry.key.startswith('end:') or row.entry.group == 'then')
        choose_row(c, menu, row, by)
        moved = lambda: deepest(host) is not was or not alive(was) or len(was.stack) != depth or getattr(was, 'line', None) != line
        if is_then:
            wait_until(lambda: isinstance(deepest(host), LinePanel) and deepest(host).ready, 2000)
        elif row.sub() or in_panel:
            wait_until(moved, 1000)
        if last and not row.sub() and not in_panel:
            wait_until(lambda: getattr(host, '_context_last', None) is not None, 1000)
            outcome = getattr(host, '_context_last', None)
    return chosen_row, outcome


def menu_said(host):
    """What the open menu shows: its target, its first level's keys, its words, and the line Then carries."""
    root = root_menu(host)
    if root is None:return {'open': False}
    then = root.row('then')
    out = {'open': True, 'target': root.target.label if root.target is not None else '', 'first': root.first_keys(), 'words': root.words(),
           'then_line': then.entry.line if then is not None else None}
    m = deepest(host)
    if m is not root:out['child'] = {'title': getattr(m, 'title', ''), 'keys': [r.entry.key for r in m.rows_by_key.values()]}
    try:out['panel'] = panel_said(line_panel(host))
    except Refusal:out['panel'] = None
    return out


def panel_said(panel):
    return {'line': panel.line, 'count': panel.count_words(), 'preview': panel.preview_rows(), 'ready': bool(panel.ready)}


# -- reading back ---------------------------------------------------------------------------------------------------------------------

def _plain(value):
    if isinstance(value, dict):return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):return [_plain(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:return value
    return str(value)


def sheet_said(obj):
    return None if obj is None else {'id': obj.id, 'title': obj.title, 'kind': obj.kind, 'state': obj.state}


def whole(view):
    """Whether the whole desk is in sight at the zoom it has now."""
    view._layout();wide, tall = view._surface;room_w, room_h = view.room()
    return bool(wide <= room_w + 0.5 and tall <= room_h + 0.5)


def route_said(view):
    route = getattr(view, '_route', None)
    if not route:return None
    title = lambda ident: getattr(view.field.get(ident), 'title', ident)
    return {'owner_title': title(route.get('owner')), 'hops': route.get('hops'), 'ends': [title(e) for e in route.get('ends') or []],
            'animating': view.surge_elapsed() is not None}


def revisions_said(view):
    cmp = getattr(view, 'revisions', None)
    if not cmp:return None
    return {'a': cmp.get('a'), 'b': cmp.get('b'), 'a_rev': cmp.get('a_rev'), 'b_rev': cmp.get('b_rev'),
            'changed': [row.get('parameter') for row in cmp.get('rows') or [] if row.get('changed')]}


def popups(host):
    """The kinds of what is open over the window now."""
    out = []
    from .context_menu import LinePanel
    root = root_menu(host)
    if root is not None:
        out.append('menu')
        if isinstance(deepest(host), LinePanel):out.append('panel')
    top = getattr(getattr(host, 'shell2', None), 'top', None)
    for word in (getattr(top, 'bar_menus', None) or []):
        try:
            if word.menu() is not None and word.menu().isVisible():out.append('head:' + word.text())
        except RuntimeError:pass
    programs = getattr(getattr(getattr(host, 'type_bar', None), 'hatch', None), 'programs', None)
    if alive(programs):out.append('apps')
    if alive(getattr(host, '_meter_card', None)):out.append('meter')
    if alive(getattr(getattr(top, 'equalizer', None), 'card', None)):out.append('equalizer')
    other = Q.QApplication.activePopupWidget()
    if other is not None and not out:out.append(type(other).__name__)
    return out


def read_desk(host, part='all'):
    """What the window shows now, read from the widgets themselves: where, the Field, the menu, Files, the line, Talk, the
    look and its motion, and the last act. `part` one of these, or 'all'."""
    parts = {}
    want = lambda name: part in ('all', name)
    if want('where'):
        tabs = getattr(host, 'tabs', None);tab = tabs.currentWidget() if tabs is not None else None
        nav = getattr(host, 'settings_navigator', None);pages = getattr(host, 'console_pages', None);shell = getattr(host, 'shell2', None)
        try:address = shell.top.path.friendly()
        except Exception:  # noqa: BLE001 - an address that cannot be read is said as none
            address = ''
        right = None
        if pages is not None and shell is not None:
            now = pages.currentWidget()
            right = 'talk' if now is shell.face else 'activity' if now is getattr(host, 'operations_panel', None) else 'context' if now is getattr(host, 'arc_inspector', None) else None
        try:left = {'cabinet': 'files'}.get(nav.current_view(), nav.current_view()) if nav is not None else None
        except Exception:  # noqa: BLE001
            left = None
        parts['where'] = {'surface': surface(host), 'title': host.windowTitle(),
                          'tab': {'type': type(tab).__name__, 'text': tabs.tabText(tabs.currentIndex()).replace('&', '')} if tab is not None else None,
                          'address': address, 'left': left, 'right': right, 'popups': popups(host)}
    if want('field'):
        page = getattr(host, 'field_page', None)
        if page is None:parts['field'] = {'shown': False}
        else:
            v = page.view
            parts['field'] = {'shown': surface(host) == 'field', 'face': FACE_WORD.get(page.face, page.face), 'selected': sheet_said(v.selected()),
                              'count': len(v.field.objects), 'zoom': round(float(v.zoom), 3), 'whole': whole(v), 'gliding': v._gliding is not None,
                              'reading': (v.reading or {}).get('title'), 'steps': [{'words': w, 'kind': k} for w, k in (v.steps or ())],
                              'go': v.go, 'would': v.would_said, 'problem': v.problem, 'pending': page.pending is not None,
                              'route': route_said(v), 'revisions': revisions_said(v)}
    if want('menu'):parts['menu'] = menu_said(host)
    if want('files'):
        from .files_qt import FilesTab
        tab = getattr(host, 'tabs', None) and host.tabs.currentWidget()
        if isinstance(tab, FilesTab):
            view, items = file_items(tab)
            parts['files'] = {'folder': tab.folder, 'view': tab.mode, 'names': [e.get('name') for e, _ in items if e],
                              'selected': [e.get('name') for e in tab.selected() if e]}
        else:parts['files'] = None
    if want('line'):
        bar = host.type_bar;popup = bar.box.popup
        results = [popup.list.item(i).text() for i in range(popup.list.count())] if popup.isVisible() else []
        console = getattr(host, 'console', None)
        parts['line'] = {'target': WHO_OF.get(bar.target, bar.target), 'text': bar.box.text(), 'results': results,
                         'room': ROOMS[getattr(console, 'size_level', 0)] if console is not None else None,
                         'last_program': getattr(console, 'last_program', None)}
    if want('talk'):
        face = host.shell2.face;latest = (stacy_hand.trail(host.session.state) or [None])[0]
        cards = [face.lines.itemAt(i).widget() for i in range(face.lines.count())]
        cards = [w for w in cards if w is not None and w is not getattr(face, 'fold', None)]
        last = ''
        if cards:
            labels = cards[-1].findChildren(Q.QLabel)
            last = next((l.text() for l in labels if l.text().strip()), '').replace('\u200b', '')
        parts['talk'] = {'cards': len(cards), 'last': last[:300], 'hand': stacy_hand.level(host),
                         'trail': {k: latest.get(k) for k in ('words', 'line', 'undo', 'state')} if latest else None}
    if want('look'):parts['look'] = look_now(host)
    if want('motion'):
        from . import menu_catch
        page = getattr(host, 'field_page', None)
        still = None
        if page is not None:
            try:still = bool(page.view.still())
            except Exception:  # noqa: BLE001
                still = None
        parts['motion'] = {'still': still, 'calm': bool(menu_catch.calm(host))}
    if want('last'):parts['last'] = {'act': getattr(host, '_desk_last', None), 'context': getattr(host, '_context_last', None)}
    out = _plain(parts)
    return out if part == 'all' else out.get(part)


def look_now(host):
    from . import boss_qt, boss_theme, tool_faces
    from .document_qt import profile_of
    state = host.session.state
    return {'appearance': boss_theme.APPEARANCE, 'next': boss_qt.chosen_look(host), 'glow': state.get('glow', boss_theme.GLOW_OPENS),
            'art': state.get('desk_art', 'illustrated'), 'buttons': tool_faces.STATE['mode'],
            'motion': 'reduced' if profile_of(host).get('reduce_motion') else 'normal'}


# -- a change, through her hand ------------------------------------------------------------------------------------------------------

def stage_change(c, title, words, operation, arguments, why, asked=True):
    """One Kernel change put to Stacy's hand as a change asked of her is (asked=True): done at once when it is hers, with its
    card, trail entry and Undo; else a card that waits for Approve. asked=False puts it up to wait whatever her dial says.
    Returns the card."""
    from .engineering_kernel import CAPABILITIES
    from .field_do import Step, op
    face = c.host.shell2.face
    card = face.stage(title, Step(words, 'write', op(operation, **arguments), why, CAPABILITIES[operation]), asked=asked, word=c.word)
    c.card = card
    return card


def card_said(c, card, operation=None, arguments=None):
    """A staged change's result: whether it ran, whether it was hers, whether it waits and why, its Undo line, what it said."""
    ran = card.ran;place = stacy_hand.level(c.host)
    notes = [w.text().replace('\u200b', '') for w in card.findChildren(Q.QLabel) if w.text().strip()]
    said = next((t for t in reversed(notes) if t.startswith(('Done', 'It was refused'))), '') if ran is not None else ''
    out = {'ran': ran, 'hers': bool(getattr(card, 'hers', False)), 'waits': ran is None, 'undo': (card.entry or {}).get('undo', '') if getattr(card, 'entry', None) else '',
           'said': said}
    if ran is None:
        from .engineering_kernel import CAPABILITIES
        from .field_do import call
        try:operation, arguments = call(card.step.line)
        except Exception:  # noqa: BLE001
            pass
        out['why'] = stacy_hand.why_waits(place, CAPABILITIES.get(operation, 'approve'), operation, arguments)
    else:out['why'] = ''
    return out


def change_words(result, what):
    if result['waits']:return 'Waits for your Approve in Talk: %s.' % result['why']
    if result['ran']:return named('Done by Stacy\'s hand: %s.') % what + (' It can be taken back.' if result['undo'] else '')
    return result['said'] or 'It was refused, and nothing was changed.'


# -- the doers -------------------------------------------------------------------------------------------------------------------------

def go_field(c):
    host = c.host;face = c.args.get('face')
    if c.by == 'keys':
        action = getattr(host, 'a_field', None)
        if surface(host) != 'field':
            if action is None or not sequence(c, host, action.shortcut()):raise Refusal('FAILED', REFUSALS['FAILED'] % 'the Field has no key here')
    elif surface(host) != 'field':
        head_row(c, 'Arrange', 'Field', 'pointer')
    settle(host)
    page, view = the_field(host)
    if face and page.face != FACE_OF[face]:
        if c.by == 'keys':
            letter = dict(page.view.faces).get(FACE_OF[face])
            field_keys(c, view, [getattr(Q.Qt, 'Key_' + letter.upper())])
        else:
            box = next((b for b, name in view._face_boxes if name == FACE_OF[face]), None)
            if box is not None:mouse(view, box.center())
            else:page.show_face(FACE_OF[face])
        settle(host)
    shown = FACE_WORD.get(page.face, page.face)
    return 'The Field is in front, its %s face.' % {'apps': 'Apps', 'work': 'work', 'network': 'network'}[shown], {'surface': surface(host), 'face': shown}


def go_today(c):
    host = c.host
    if c.by == 'keys' and getattr(host, 'a_home', None) is not None and sequence(c, host, host.a_home.shortcut()):pass
    else:c.by = head_row(c, 'Arrange', 'Today', 'pointer')
    settle(host)
    return 'Today is in front.', {'surface': surface(host)}


def go_files(c):
    host = c.host;folder = c.args.get('folder');wanted = c.args.get('view')
    c.by = head_row(c, 'Arrange', 'Files', c.by)
    settle(host)
    tab = files_tab(host)
    if folder is not None and folder != tab.folder:tab.go(folder);settle(host)
    if wanted and tab.mode != wanted:tab.toggle_view();settle(host)
    names = [e.get('name') for e, _ in file_items(tab)[1] if e]
    return 'Files is in front%s, as %s.' % ((', in “%s”' % tab.folder) if tab.folder else '', 'a list' if tab.mode == 'list' else 'icons'), \
        {'surface': surface(host), 'folder': tab.folder, 'view': tab.mode, 'names': names}


def tab_said(host):
    tab = host.tabs.currentWidget()
    return {'type': type(tab).__name__, 'text': host.tabs.tabText(host.tabs.currentIndex()).replace('&', '')} if tab is not None else None


def go_open(c):
    host = c.host;a = c.args
    if 'tab' in a:
        if not 0 <= a['tab'] < host.tabs.count():raise Refusal('NOT_HERE', 'There is no tab %d; %d are open.' % (a['tab'], host.tabs.count()))
        host._close_start();host.tabs.setCurrentIndex(a['tab']);c.by = 'pointer';settle(host)
        return 'The tab “%s” is in front.' % tab_said(host)['text'], {'tab': tab_said(host)}
    if 'sheet' in a:
        page, view = the_field(host);obj = find_sheet(view, a['sheet'])
        if c.by == 'keys':
            point_by_keys(c, view, obj.id);field_keys(c, view, [Q.Qt.Key_Return])
        else:
            mouse(view, sheet_point(view, obj.id))
        settle(host, 60, 6)       # the opening click's guard lets go a moment after
        return 'The page for “%s” is open.' % obj.title, {'tab': tab_said(host)}
    tab = files_tab(host);view, item = file_item(tab, a['path'])
    if c.by == 'keys':
        view.setCurrentItem(item);view.setFocus();settle(host)
        if not keyboard_on(view):raise Refusal('NOT_HERE', 'The keyboard is not on Files.')
        key(c, view, Q.Qt.Key_Return)
    else:
        view.scrollToItem(item);at = view.visualItemRect(item).center()
        Q.QTest.mouseDClick(view.viewport(), Q.Qt.LeftButton, Q.Qt.NoModifier, at)
    settle(host, 60, 4)
    return '“%s” is open.' % a['path'], {'tab': tab_said(host)}


def go_app(c):
    host = c.host;hatch = host.type_bar.hatch;c.by = 'pointer'
    if c.args['key'] == 'documents':      # Documents with no document starts one as it opens (DocumentsTab): a record, the owner's to make
        from .context_menu import dispatch
        listing = dispatch(host, 'documents.list', {})
        if listing.get('ok') and not (listing.get('result') or {}).get('documents'):
            raise Refusal('MAKES', REFUSALS['MAKES'] % 'a new document, since Documents holds none yet')
    if not alive(hatch.programs):host.shell2.top.programs.click();settle(host)
    row = hatch.programs.rows_by_key.get(c.args['key'])
    if row is None or not alive(row) or not row.isEnabled():
        why = ('No app “%s” is in the Apps list.' % c.args['key']) if row is None or not alive(row) else ('That app cannot open now: %s' % (row.toolTip() or 'it is unavailable'))
        hatch.programs.close_menu();raise Refusal('NOT_HERE', why)      # the list it opened goes again
    Q.QTest.mouseClick(row, Q.Qt.LeftButton);settle(host, 60, 4)
    return '%s is open.' % row.word, {'tab': tab_said(host)}


def go_back(c):
    host = c.host;page, view = the_field(host)
    if c.by == 'keys':
        if view.steps or view.go or view.would or view.reading is not None or view.revisions is not None:
            raise Refusal('NOT_HERE', 'Something is shown over the work; sheet.close puts it away first.')
        field_keys(c, view, [Q.Qt.Key_Escape])
    else:
        from .field_page import back
        back(host)
    settle(host)
    return 'The Field has stepped aside.', {'surface': surface(host)}


def go_pane(c):
    host = c.host;a = c.args;c.by = 'pointer'
    if 'left' in a:
        nav = host.settings_navigator;button = nav.bar.buttons[('files', 'machine', 'settings').index(a['left'])]
        Q.QTest.mouseClick(button, Q.Qt.LeftButton);settle(host)
    if 'right' in a:
        shell = host.shell2
        {'talk': shell.show_slate_face, 'activity': shell.show_operations_face, 'context': shell.show_context_face}[a['right']]()
        settle(host)
    where = read_desk(host, 'where')
    return 'The left pane shows %s; the right, %s.' % (where['left'], where['right']), {'left': where['left'], 'right': where['right']}


def point_by_keys(c, view, ident):
    """Select a sheet with the keys a person would press: the fewest, found over the Field's own moves."""
    path = desk_acts.key_path(view.field, view.field.selected, ident)
    if path is None:raise Refusal('NOT_HERE', 'No key reaches that sheet from here.')
    field_keys(c, view, [way_key(way) for way in path])
    return path


def point_sheet(c):
    host = c.host;page, view = the_field(host)
    obj = find_sheet(view, c.args.get('title'), c.args.get('id'))
    by = c.args.get('by', 'direct' if c.by not in ('pointer', 'keys') else c.by);c.by = by
    if by == 'keys':point_by_keys(c, view, obj.id)
    elif by == 'pointer':
        for _ in range(2):      # the right button selects and opens nothing; a press beside a page shown over the work first puts it away
            mouse(view, sheet_point(view, obj.id), Q.Qt.RightButton);settle(host)
            if view.field.selected == obj.id:break
    else:
        view.field.select(obj.id);view._layout();view._reveal();view._describe();view.update()
    settle(host)
    if view.field.selected != obj.id:raise Refusal('FAILED', REFUSALS['FAILED'] % 'the selection did not move there')
    return '“%s” is selected.' % obj.title, {'selected': sheet_said(view.selected()), 'presses': c.presses}


def point_move(c):
    host = c.host;page, view = the_field(host);c.by = 'keys'
    field_keys(c, view, [way_key(c.args['way'])] * int(c.args.get('times', 1)))
    obj = view.selected()
    return ('“%s” is selected.' % obj.title) if obj is not None else 'Nothing is selected.', {'selected': sheet_said(obj)}


def point_zoom(c):
    host = c.host;page, view = the_field(host);to = c.args['to']
    spot = lambda test: next((box for box, k, _, said in view._hot if test(k, said)), None)
    if to in ('whole', 'reading'):
        # Z goes between the whole desk and the reading size; the strip's size words are a place to click that does what Z
        # does, drawn only while the desk is not at its reading size or runs beyond the window.
        if to == 'whole':need = not whole(view) and abs(view.zoom - view.fit()) >= 1e-6;keys = [Q.Qt.Key_Z]
        else:need = abs(view.zoom - 1.0) >= 1e-6;keys = [Q.Qt.Key_Z] if view._fitted else [(Q.Qt.Key_0, Q.Qt.ControlModifier)]
        if need:
            z = spot(lambda k, said: k == Q.Qt.Key_Z) if c.by == 'pointer' and keys == [Q.Qt.Key_Z] else None
            if z is not None:mouse(view, z.center())
            else:c.by = 'keys';field_keys(c, view, keys)
    else:
        words = 'Larger' if to == 'larger' else 'Smaller';plus = spot(lambda k, said: callable(k) and said == words) if c.by == 'pointer' else None
        if plus is not None:mouse(view, plus.center())
        else:c.by = 'keys';field_keys(c, view, [Q.Qt.Key_Plus if to == 'larger' else Q.Qt.Key_Minus])
    wait_until(lambda: view._gliding is None, 1500)
    settle(host)
    seen = whole(view)
    return 'The desk is seen at %d%%%s.' % (round(view.zoom * 100), ', all of it' if seen else ''), {'zoom': round(float(view.zoom), 3), 'whole': seen}


def head_open(c):
    host = c.host;menu = c.args['menu'];top = host.shell2.top
    if menu == 'Apps':
        c.by = 'pointer';top.programs.click();settle(host)
        programs = host.type_bar.hatch.programs
        rows = [w for w in programs.words() if w != '—']
        return 'The Apps list is open.', {'title': 'Apps', 'rows': rows, 'open': alive(programs), 'keyboard_route': False}
    if c.by == 'keys':
        # No keyboard route to the head's words exists (they are not in the Tab chain, and no key opens them). The word is
        # given the keyboard and Space pressed, as a keyboard would if it could reach it; the word's menu runs its own loop,
        # so a timer inside that loop reads the rows and closes it.
        word = head_word(host, menu);seen = {}

        def read():
            m = word.menu();seen.update(rows=menu_rows(m), open=m.isVisible());m.hide()
        word.setFocus();settle(host)
        Q.QTimer.singleShot(250, read)
        key(c, word, Q.Qt.Key_Space);settle(host)
        if not seen:raise Refusal('FAILED', REFUSALS['FAILED'] % 'the menu did not open')
        return 'The %s menu was opened and read; no key reaches it by itself.' % menu, \
            {'title': menu, 'rows': seen['rows'], 'open': seen['open'], 'keyboard_route': False}
    started = time.monotonic();_, m = head_popup(host, menu)
    return 'The %s menu is open.' % menu, {'title': menu, 'rows': menu_rows(m), 'open': m.isVisible(), 'keyboard_route': False,
                                           'seconds': round(time.monotonic() - started, 2)}


def head_row_act(c):
    host = c.host;c.by = head_row(c, c.args['menu'], c.args['row'], c.by);settle(host)
    return '%s › %s.' % (c.args['menu'], c.args['row']), {'triggered': c.args['row'], 'surface': surface(host), 'tab': tab_said(host)}


def head_meter(c):
    host = c.host;which = c.args['which'];top = host.shell2.top;c.by = 'pointer'
    if which == 'equalizer':
        card = top.equalizer.show_card()
        if not card.isVisible():card = top.equalizer.show_card()
        settle(host)
        return 'The equalizer says what each group reads now.', {'which': which, 'words': dict(getattr(top.equalizer, 'words', {}) or {})}
    card = top.pulse.open_card(which);settle(host)
    words = list(getattr(card, 'words', {}) or {}) if card is not None else []
    return 'The %s card is open.' % which, {'which': which, 'words': words}


def menu_open(c):
    host = c.host;on = c.args['on'];name = c.args.get('name')
    before = getattr(host, 'context_menu', None)
    if on in ('file', 'sheet') and not name:raise Refusal('BAD_ARGUMENTS', 'menu.open on a %s needs its name.' % on)
    if on == 'file':
        tab = files_tab(host);view, item = file_item(tab, name)
        if c.by == 'keys':
            view.setFocus();settle(host)
            if not keyboard_on(view):raise Refusal('NOT_HERE', 'The keyboard is not on Files.')
            key(c, view, Q.Qt.Key_Home)
            _, items = file_items(tab)
            for _ in range(len(items)):
                if view.currentItem() is item:break
                key(c, view, Q.Qt.Key_Down)
            if view.currentItem() is not item:raise Refusal('FAILED', REFUSALS['FAILED'] % 'the keys did not reach the file')
            from .context_menu import open_at_focus
            open_at_focus(host);c.presses += 1        # the Menu key's own call
        else:
            view.scrollToItem(item);settle(host);at = view.visualItemRect(item).center()
            right_click(view.viewport(), at)
    elif on == 'sheet':
        page, view = the_field(host);obj = find_sheet(view, name)
        if c.by == 'keys':
            if view.field.selected != obj.id:point_by_keys(c, view, obj.id)
            if not keyboard_on(view):raise Refusal('NOT_HERE', 'The keyboard is not on the Field.')
            view.press_key(Q.Qt.Key_Menu);c.presses += 1
        else:right_click(view, sheet_point(view, obj.id))
    else:
        from .context_menu import open_at_focus
        if c.by == 'keys':open_at_focus(host);c.presses += 1
        else:
            widget, at = here_point(host)
            right_click(widget, at)
    settle(host)
    menu = root_menu(host)
    if menu is None or menu is before:
        own = Q.QApplication.activePopupWidget()
        if isinstance(own, Q.QMenu):      # the keyboard is in a place with a menu of its own (a text field): that one opened
            own.hide();raise Refusal('NOT_HERE', 'The keyboard is on a place that keeps its own menu, such as a text field; nothing of Graphite\'s opened.')
        raise Refusal('FAILED', REFUSALS['FAILED'] % 'no menu opened there')
    said = menu_said(host)
    return 'The menu for “%s” is open.' % said['target'], {k: said[k] for k in ('target', 'first', 'words', 'then_line')}


def here_point(host):
    """An empty place under the pointer: in the Field, a place no sheet covers; in Files, a place no file covers; else the
    workspace's middle."""
    where = surface(host)
    if where == 'field':
        view = host.field_page.view;body = view._layout()
        for fx in (0.97, 0.03, 0.5):
            for fy in (0.9, 0.1, 0.5):
                at = Q.QPointF(body.left() + body.width() * fx, body.top() + body.height() * fy)
                if view._hit(at) is None:return view, at
        return view, Q.QPointF(body.right() - 4, body.bottom() - 30)
    from .files_qt import FilesTab
    tab = host.tabs.currentWidget()
    if isinstance(tab, FilesTab) and where == 'workspace':
        view = tab.table if tab.mode == 'list' else tab.icons;port = view.viewport()
        for fx, fy in ((0.9, 0.95), (0.5, 0.95), (0.95, 0.5)):
            at = Q.QPointF(port.width() * fx, port.height() * fy)
            if view.itemAt(at.toPoint()) is None:return port, at
    target = host.tabs if where == 'workspace' else host.central_stack.currentWidget()
    return target, Q.QPointF(target.width() / 2, target.height() / 2)


def menu_choose(c):
    host = c.host
    if root_menu(host) is None:raise Refusal('NOT_HERE', 'No menu is open.')
    segments = [s for s in c.args['path'].split('/') if s.strip()]
    chosen_key, outcome = walk(c, segments, c.by)
    m = deepest(host)
    child = {'title': getattr(m, 'title', ''), 'keys': [r.entry.key for r in m.rows_by_key.values()]} if m is not None else None
    out = {'chosen': c.args['path'], 'child': child, 'outcome': _plain(outcome), 'presses': c.presses}
    if outcome is not None and not outcome.get('ok'):
        raise Refusal('FAILED', REFUSALS['FAILED'] % (outcome.get('words') or 'the row was refused'))
    return ('Chose %s.' % c.args['path']) + ((' ' + str(outcome.get('words'))) if outcome and outcome.get('words') else ''), out


def menu_close(c):
    host = c.host;closed = []
    for _ in range(10):
        kinds = popups(host)
        if not kinds:break
        top = deepest(host) if root_menu(host) is not None else Q.QApplication.activePopupWidget()
        if top is None:
            top = next((w for w in (getattr(host.type_bar.hatch, 'programs', None), getattr(host, '_meter_card', None),
                                    getattr(host.shell2.top.equalizer, 'card', None)) if alive(w)), None)
        if top is None:
            for word in host.shell2.top.bar_menus:
                if alive(word.menu()):top = word.menu();break
        if top is None:break
        closed.append(kinds[0])
        if c.by == 'keys':
            focus = Q.QApplication.focusWidget()
            key(c, focus if focus is not None and focus.window() is top else top, Q.Qt.Key_Escape)
        else:
            mouse(top, Q.QPointF(top.mapFromGlobal(outside(host))), release=False)      # a press outside: a popup's rule is to close
        settle(host)
    left = popups(host)
    if left:raise Refusal('FAILED', REFUSALS['FAILED'] % ('still open: ' + ', '.join(left)))
    return ('Closed: %s.' % ', '.join(closed)) if closed else 'Nothing was open.', {'closed': closed}


def outside(host):
    """A place in the window that no open popup covers (a corner of the window), as a global point."""
    opened = [w for w in Q.QApplication.topLevelWidgets() if alive(w) and w.windowType() == Q.Qt.Popup]
    for x, y in ((6, 6), (host.width() - 6, 6), (6, host.height() - 6), (host.width() - 6, host.height() - 6)):
        at = host.mapToGlobal(Q.QPoint(x, y))
        if not any(w.frameGeometry().contains(at) for w in opened):return at
    return host.mapToGlobal(Q.QPoint(6, 6))


def then_walk(c, segments):
    host = c.host;panel = line_panel(host)
    if panel.stack:                                   # back to the panel's first screen
        walk(c, ['back'], c.by, guard=False)
    walk(c, segments, c.by)
    panel = line_panel(host)
    wait_until(lambda: panel.ready, 1000)
    said = panel_said(panel)
    return 'The line now reads %s · %s.' % (said['line'], said['count']), said


def then_keep(c):
    panel = line_panel(c.host)
    if panel.row('step:where') is None and not panel.stack:raise Refusal('NOT_HERE', 'This line panel offers no rows to keep.')
    return then_walk(c, ['step:where', 'field:' + c.args['column'], c.args['words']])


def then_count(c):
    return then_walk(c, ['step:count'])


def then_back(c):
    host = c.host;panel = line_panel(host)
    if panel.line == panel.base:raise Refusal('NOT_HERE', 'The line has no step to take off.')
    if c.by == 'keys':
        focus = Q.QApplication.focusWidget()
        key(c, focus if focus is not None and focus.window() is panel else panel, Q.Qt.Key_Backspace);settle(host)
        said = panel_said(line_panel(host))
        return 'The line now reads %s · %s.' % (said['line'], said['count']), said
    return then_walk(c, ['step:back'])


def then_end(c):
    host = c.host;how = c.args['how']
    panel = line_panel(host)
    if how == 'line':
        if unsent(host):raise Refusal('UNSENT', REFUSALS['UNSENT'])
        if getattr(getattr(host, 'console', None), 'pending_approval', None):raise Refusal('PENDING', REFUSALS['PENDING'])
    if panel.stack:walk(c, ['back'], c.by, guard=False)
    line = panel.line
    _, outcome = walk(c, ['end:' + how], c.by)
    if how == 'line':host._desk_put = host.type_bar.box.text()
    words = {'show': 'The line ran; its answer is in the working area.', 'line': 'The line is in the writing line: %s' % line,
             'copy': 'The line is copied.', 'rows': 'The rows are copied.'}[how]
    if outcome is not None and not outcome.get('ok'):raise Refusal('FAILED', REFUSALS['FAILED'] % (outcome.get('words') or 'the ending was refused'))
    return words, {'outcome': _plain(outcome), 'line': host.type_bar.box.text()}


def sheet_menu_walk(c, view, obj, path):
    """By pointer: the sheet's own right-click menu, then the rows of `path`."""
    if alive(root_menu(c.host)):root_menu(c.host).close_menu(restore=False);settle(c.host)
    right_click(view, sheet_point(view, obj.id));settle(c.host)
    if root_menu(c.host) is None:raise Refusal('FAILED', REFUSALS['FAILED'] % 'the sheet\'s menu did not open')
    return walk(c, path, 'pointer')


def sheet_trace(c):
    host = c.host;page, view = the_field(host);obj = chosen(view)
    if c.by == 'keys':field_keys(c, view, [Q.Qt.Key_T])
    else:sheet_menu_walk(c, view, obj, ['more', 'field:trace', 'field:trace:all'] if page.face == 'work' else ['more', 'field:trace'])
    settle(host, 40, 4)
    route = route_said(view)
    if route is None:raise Refusal('FAILED', REFUSALS['FAILED'] % 'no trace was drawn')
    return 'Traced “%s”: %d hop%s.' % (obj.title, route['hops'], '' if route['hops'] == 1 else 's'), {'route': route}


def sheet_doubt(c):
    host = c.host;page, view = the_field(host);obj = chosen(view)
    if c.by == 'keys':field_keys(c, view, [Q.Qt.Key_X])
    else:sheet_menu_walk(c, view, obj, ['field:doubt', 'field:doubt:all'] if page.face == 'work' else ['field:doubt'])
    settle(host, 40, 4)
    return 'Doubting “%s”.' % obj.title, {'reading': (view.reading or {}).get('title')}


def sheet_compare(c):
    from .field_page import revision_sibling
    host = c.host;page, view = the_field(host);obj = chosen(view)
    if page.face != 'work' or revision_sibling(view, obj) is None:raise Refusal('NO_SIBLING', REFUSALS['NO_SIBLING'])
    if c.by == 'keys':
        if not keyboard_on(view):raise Refusal('NOT_HERE', 'The keyboard is not on the Field.')
        view.press_key(Q.Qt.Key_Menu);c.presses += 1;settle(host)
        if root_menu(host) is None:raise Refusal('FAILED', REFUSALS['FAILED'] % 'the sheet\'s menu did not open')
        walk(c, ['more', 'field:revisions'], 'keys')
    else:sheet_menu_walk(c, view, obj, ['more', 'field:revisions'])
    settle(host)
    said = revisions_said(view)
    if said is None:raise Refusal('FAILED', REFUSALS['FAILED'] % 'the two revisions were not shown')
    return 'Rev %s and Rev %s side by side: %s changed.' % (said['a_rev'], said['b_rev'], ', '.join(said['changed']) or 'nothing'), {'revisions': said}


def over(view):
    return view.revisions is not None or view.reading is not None or bool(view.steps) or bool(view.go) or bool(view.would)


def beside(view, inner):
    """A place in the Field to click beside `inner` (the comparison or the page shown over the work), on no clickable spot:
    the middle of the widest margin around it first. A click there closes what is shown, whatever lies under it (the
    view's press reads its clickable spots, then what is shown over the work, before anything else). None when every
    margin is covered. Found from the shown rectangle itself, since on a small window it leaves only a few pixels free."""
    wide, high = float(view.width()), float(view.height())
    margins = [Q.QRectF(0, 0, inner.left(), high), Q.QRectF(inner.right(), 0, wide - inner.right(), high),
               Q.QRectF(0, 0, wide, inner.top()), Q.QRectF(0, inner.bottom(), wide, high - inner.bottom())]
    margins = sorted((m for m in margins if m.width() >= 3 and m.height() >= 3), key=lambda m: -min(m.width(), m.height()))
    for m in margins:
        for f in (0.5, 0.3, 0.7, 0.15, 0.85):
            at = Q.QPointF(m.center().x(), m.top() + m.height() * f) if m.height() >= m.width() else Q.QPointF(m.left() + m.width() * f, m.center().y())
            if not inner.contains(at) and view._hot_at(at) is None:return at
    return None


def sheet_close(c):
    host = c.host;page, view = the_field(host)
    if not over(view):return 'Nothing was shown over the work.', {'over': None}
    if c.by == 'pointer' and (view.revisions is not None or view.reading is not None):
        inner = view._rev_rect if view.revisions is not None else view._reading_rect(view._layout())
        spot = beside(view, inner)
        if spot is not None:mouse(view, spot);settle(host)
    if over(view):                                    # what no click puts away (the steps, a what-if): its key
        c.by = 'keys'
        for _ in range(5):
            if not over(view):break
            field_keys(c, view, [Q.Qt.Key_Escape])
    settle(host)
    if over(view):raise Refusal('FAILED', REFUSALS['FAILED'] % 'something is still shown over the work')
    return 'The work is in sight again.', {'over': None, 'surface': surface(host)}


def sheet_whatif(c):
    host = c.host;page, view = the_field(host);obj = chosen(view);c.by = 'direct'
    if obj.kind not in ('sheet', 'calculation') or not isinstance(obj.target, dict):
        raise Refusal('NOT_HERE', 'A what-if sets a number of a sheet or an input of a calculation; “%s” is neither.' % obj.title)
    face = host.shell2.face;text = 'what if %s were %s' % (c.args['cell'], c.args['value'])
    # The face's own what-if, never her ask: ask hands whatever the what-if cannot read to her model, and an act never asks it.
    thing = face.what_if(text)
    if thing is None:raise Refusal('NOT_HERE', '“%s” has no number a what-if can set.' % obj.title)
    if thing.get('refusal'):raise Refusal('NOT_HERE', thing['refusal'])
    face.thing = None;face.mine(text);face.answer_in_stac(thing, thing.get('intro'))      # Talk answers as it does when she is asked
    if surface(host) == 'field':view.setFocus(Q.Qt.OtherFocusReason)
    settle(host, 40, 4)
    said = view.would_said or ''
    return (said[:1].upper() + said[1:] if said else 'Nothing would move') + '; nothing is changed.', \
        {'would': said, 'moves': sorted(getattr(view.field.get(i), 'title', i) for i in view.would), 'sheet': obj.title}


def sheet_steps(c):
    host = c.host;page, view = the_field(host);obj = chosen(view)
    if c.by == 'keys':
        field_keys(c, view, [Q.Qt.Key_D]);settle(host)
        steps = [{'words': w, 'kind': k} for w, k in (view.steps or ())]
    else:
        sheet_menu_walk(c, view, obj, ['field:do'])
        menu = deepest(host)
        steps = [{'words': r.word, 'kind': 'write' if r.entry.caption == 'asks' else 'read'} for r in menu.rows_by_key.values() if r.entry.key.startswith('field:do:') and r.isEnabled()]
    return '%d step%s can be taken about “%s”.' % (len(steps), '' if len(steps) == 1 else 's', obj.title), {'steps': steps}


def type_to(c):
    host = c.host;bar = host.type_bar;mode = WHO[c.args['who']]
    action = (getattr(host, 'a_talk', {}) or {}).get(mode)
    if c.by == 'keys' and action is not None and sequence(c, host, action.shortcut()):pass
    else:
        c.by = 'pointer';Q.QTest.mouseClick(bar.targets[mode], Q.Qt.LeftButton)
    settle(host)
    if bar.target != mode:raise Refusal('FAILED', REFUSALS['FAILED'] % 'the line did not turn')
    return 'The writing line goes to %s.' % named({'her': 'Stacy', 'terminal': 'the Terminal', 'search': 'Search', 'web': 'the Web', 'log': 'the Log'}[c.args['who']]), \
        {'target': c.args['who']}


def line_results(box):
    popup = box.popup
    return [popup.list.item(i).text() for i in range(popup.list.count())] if popup.isVisible() else []


def type_put(c):
    from .context_menu import inspect_in_line
    host = c.host;bar = host.type_bar;box = bar.box;text = c.args['text']
    if unsent(host):raise Refusal('UNSENT', REFUSALS['UNSENT'])
    if getattr(getattr(host, 'console', None), 'pending_approval', None):raise Refusal('PENDING', REFUSALS['PENDING'])
    by = c.args.get('by', 'keys' if c.by == 'keys' else 'put');c.by = by
    if by == 'keys':
        box.clear();box.setFocus();settle(host)
        type_text(c, box, text)
    else:inspect_in_line(host, text, bar.target if bar.target != 'web' else 'slate')
    settle(host)
    if box.text() != text:      # what the line holds is what was asked, or the act says it failed and leaves nothing half put
        box.clear();host._desk_put = ''
        raise Refusal('FAILED', REFUSALS['FAILED'] % 'the writing line did not take those words as they are')
    host._desk_put = box.text()
    return 'The writing line holds: %s' % box.text(), {'text': box.text(), 'target': WHO_OF.get(bar.target, bar.target), 'results': line_results(box)}


def type_send(c):
    host = c.host;bar = host.type_bar;box = bar.box;text = box.text().strip()
    if not text:raise Refusal('NOT_HERE', 'The writing line is empty.')
    if bar.target == 'web' or (bar.target == 'shell' and not stacy_hand.terminal_hers(text)):raise Refusal('LEAVES_OR_SHELL', REFUSALS['LEAVES_OR_SHELL'])
    by = c.args.get('by', 'keys' if c.by == 'keys' else 'arrow');c.by = by
    if by == 'keys':box.setFocus();settle(host);key(c, box, Q.Qt.Key_Return)
    else:bar.submit_line()
    settle(host, 40, 4)
    host._desk_put = ''
    console = getattr(host, 'console', None)
    tail = console.output.toPlainText()[-400:] if console is not None else ''
    return 'Sent.', {'target': WHO_OF.get(bar.target, bar.target), 'output_tail': tail}


def type_room(c):
    host = c.host;c.by = 'direct';host.console.set_size(ROOMS.index(c.args['size']));settle(host)
    return 'The working area is %s.' % {'line': 'one line', 'half': 'half the window', 'tall': 'tall'}[c.args['size']], {'room': ROOMS[host.console.size_level]}


def hand_write(c):
    from .context_menu import dispatch
    from .stacy_start import reserved
    path, text = c.args['path'], c.args['text'];c.by = 'direct'
    if reserved(path):raise Refusal('NOT_HERE', '“%s” begins with a name Graphite keeps for a folder of its own.' % path)
    # Her own rule for a file asked of her (shell2.made_asked): she never writes over what is there by herself, and an
    # overwrite has no exact Undo. So a path that is taken is put up to wait for the owner's Approve, whatever her dial says.
    taken = bool(dispatch(c.host, 'files.get', {'path': path}).get('ok'))
    card = stage_change(c, path, 'Write “%s” in Files' % path, 'files.write', {'path': path, 'text': text},
                        'it writes over what is there now' if taken else 'a file written at your word', asked=not taken)
    settle(c.host);result = card_said(c, card)
    if taken and result['waits']:
        result['why'] = 'there is already something called “%s” in Files, and I do not write over what is there by myself' % path
    return change_words(result, 'wrote “%s” in Files' % path), result


def hand_rename(c):
    path, name = c.args['path'], c.args['name'];c.by = 'direct'
    card = stage_change(c, path, 'Rename “%s” to “%s”' % (path, name), 'files.rename', {'path': path, 'name': name}, 'a file renamed at your word')
    settle(c.host);result = card_said(c, card)
    return change_words(result, 'renamed “%s” to “%s”' % (path, name)), result


def hand_trash(c):
    path = c.args['path'];c.by = 'direct'
    card = stage_change(c, path, 'Move “%s” to the Trash' % path, 'files.trash', {'path': path}, 'the Trash keeps it and gives it back')
    settle(c.host);result = card_said(c, card)
    return change_words(result, 'moved “%s” to the Trash' % path), result


def hand_cell(c):
    from .field_page import stage_set
    host = c.host;page, view = the_field(host);obj = chosen(view);c.by = 'direct'
    card = stage_set(host, obj, c.args['cell'], c.args['value'], c.word)
    if card is None:raise Refusal('FAILED', REFUSALS['FAILED'] % 'that sheet has no number there')
    c.card = card;settle(host);result = card_said(c, card);result['go'] = view.go
    return change_words(result, 'set %s to %s' % (c.args['cell'], c.args['value'])), result


def hand_step(c):
    from . import field_page
    host = c.host;page, view = the_field(host);obj = chosen(view);c.by = 'direct'
    offered = field_page.do(host, obj);n = c.args['n']
    if n > len(offered):raise Refusal('BAD_ARGUMENTS', 'There %s only %d step%s offered for “%s”.' % ('is' if len(offered) == 1 else 'are', len(offered), '' if len(offered) == 1 else 's', obj.title))
    step = offered[n - 1]
    card = field_page.take(host, obj, n - 1)
    settle(host)
    if step.kind == 'read':return 'Read: %s.' % step.words, {'kind': 'read', 'ran': True, 'hers': True, 'waits': False, 'undo': '', 'why': '', 'said': step.words}
    if card is None or not hasattr(card, 'ran'):
        return 'Put up in Talk: %s.' % step.words, {'kind': 'write', 'ran': None, 'hers': False, 'waits': True, 'undo': '', 'why': 'several changes go together', 'said': ''}
    c.card = card;result = card_said(c, card);result['kind'] = 'write'
    return change_words(result, step.words[:1].lower() + step.words[1:]), result


def waiting_cards(host):
    """The cards in Talk that wait for Approve, oldest first: in the order Talk holds them, never by where they are drawn
    (a card folded behind "show them" is hidden, and a hidden card keeps no place on the screen)."""
    face = host.shell2.face
    order = {}
    for i in range(face.lines.count()):
        w = face.lines.itemAt(i).widget()
        if w is not None:order[id(w)] = i

    def place(card):
        w = card
        while w is not None and id(w) not in order:w = w.parentWidget()
        return order.get(id(w), -1) if w is not None else -1
    cards = [w for w in face.findChildren(Q.QFrame) if getattr(w, 'ran', 'x') is None and getattr(w, 'run', None) is not None
             and w.run.isVisibleTo(w) and w.run.isEnabled()]
    cards.sort(key=place)
    return cards


def go_card(page):
    """The card the Field's go (G) approves: the one its Run was made for (field_page keeps that Run as a closure over its
    card), or None when it cannot be told."""
    run = getattr(page, 'pending', None)
    for cell in getattr(run, '__closure__', None) or ():
        try:value = cell.cell_contents
        except ValueError:continue
        if getattr(value, 'run', None) is not None and hasattr(value, 'ran'):return value
    return None


def hand_approve(c):
    host = c.host;cards = waiting_cards(host)
    if not cards:raise Refusal('NOTHING_WAITS', REFUSALS['NOTHING_WAITS'])
    card = cards[-1]
    page = getattr(host, 'field_page', None)
    # G approves what the Field's go was put up for, which need not be the latest card; the act approves the latest, so G
    # is pressed only when the two are the same card (else its Approve is clicked), and the card read back is the one approved.
    if c.by == 'keys' and surface(host) == 'field' and page.view.go and keyboard_on(page.view) and go_card(page) is card:
        field_keys(c, page.view, [Q.Qt.Key_G])
    else:
        c.by = 'pointer';face = host.shell2.face
        if not card.isVisible():face.unfold()      # an earlier card folded behind "show them" is shown first, as a person would
        face.scroll.ensureWidgetVisible(card.run);settle(host)
        Q.QTest.mouseClick(card.run, Q.Qt.LeftButton)
    settle(host, 40, 4)
    result = card_said(c, card)
    return ('Approved: ' + (result['said'] or 'done.')) if result['ran'] else ('It was refused: ' + (result['said'] or 'nothing changed.')), {'ran': result['ran'], 'said': result['said']}


def hand_undo(c):
    host = c.host;c.by = 'direct'
    entry = next((e for e in stacy_hand.trail(host.session.state) if e.get('state') == 'done' and e.get('undo')), None)
    if entry is None:raise Refusal('NOTHING_TO_UNDO', REFUSALS['NOTHING_TO_UNDO'])
    line = entry['undo']      # read first: taking an act back spends its Undo line
    card = host.shell2.face.undo_entry(entry);settle(host)
    after = next((e for e in stacy_hand.trail(host.session.state) if e.get('at') == entry.get('at') and e.get('line') == entry.get('line')), entry)
    from .field_do import call
    try:operation, arguments = call(line)
    except Exception:  # noqa: BLE001
        operation, arguments = '', {}
    said = getattr(getattr(card, 'text', None), 'text', lambda: '')().replace('\u200b', '')
    out = {'state': after.get('state'), 'trashed': arguments.get('path') if operation == 'files.trash' else None, 'said': said}
    if after.get('state') != 'undone':raise Refusal('FAILED', said or REFUSALS['FAILED'] % 'it could not be taken back')
    return said or 'Taken back.', out


def hand_dial(c):
    host = c.host;c.by = 'direct'
    place = stacy_hand.choose(host, c.args['place'])
    try:host.session.save()
    except Exception:  # noqa: BLE001 - the dial is set; a session that could not be written is said nowhere else either
        pass
    host.shell2.face.show_hand()
    return named('Stacy %s.') % stacy_hand.SAYS[place], {'place': place, 'said': named('Stacy %s.') % stacy_hand.SAYS[place]}


def look_set(c):
    from . import boss_qt, boss_theme, reading_preferences, tool_faces
    from .document_qt import profile_of
    host = c.host;a = c.args;c.by = 'direct'
    before = look_now(host)
    if 'appearance' in a:boss_qt.choose_appearance(host, a['appearance'], ask=False)      # in force from the next start; never the restart question
    if 'glow' in a:boss_qt.choose_glow(host, a['glow'])
    if 'art' in a:boss_qt.choose_art(host, a['art'])
    if 'buttons' in a:tool_faces.choose(host, a['buttons'])
    if 'motion' in a:
        # persist: menu_catch.calm reads the session's profile, so it must hold the choice too
        reading_preferences.apply(host, {**profile_of(host), 'reduce_motion': a['motion'] == 'reduced'}, persist=True)
    settle(host)
    now = look_now(host)
    return 'The look is set%s.' % (('; the appearance is %s from the next start' % now['next']) if 'appearance' in a and now['next'] != boss_theme.APPEARANCE else ''), \
        {'before': before, 'now': now, 'in_force': boss_theme.APPEARANCE, 'next': boss_qt.chosen_look(host)}


def read_desk_act(c):
    c.by = 'direct'
    return 'What the window shows now.', read_desk(c.host, c.args.get('part', 'all'))


DOERS = {'go.field': go_field, 'go.today': go_today, 'go.files': go_files, 'go.open': go_open, 'go.app': go_app, 'go.back': go_back, 'go.pane': go_pane,
         'point.sheet': point_sheet, 'point.move': point_move, 'point.zoom': point_zoom,
         'head.open': head_open, 'head.row': head_row_act, 'head.meter': head_meter,
         'menu.open': menu_open, 'menu.choose': menu_choose, 'menu.close': menu_close,
         'then.keep': then_keep, 'then.count': then_count, 'then.back': then_back, 'then.end': then_end,
         'sheet.trace': sheet_trace, 'sheet.doubt': sheet_doubt, 'sheet.compare': sheet_compare, 'sheet.close': sheet_close,
         'sheet.whatif': sheet_whatif, 'sheet.steps': sheet_steps,
         'type.to': type_to, 'type.put': type_put, 'type.send': type_send, 'type.room': type_room,
         'hand.write': hand_write, 'hand.rename': hand_rename, 'hand.trash': hand_trash, 'hand.cell': hand_cell, 'hand.step': hand_step,
         'hand.approve': hand_approve, 'hand.undo': hand_undo, 'hand.dial': hand_dial, 'look.set': look_set, 'read.desk': read_desk_act}


# -- the one entry ----------------------------------------------------------------------------------------------------------------------

def form_for(act, args, style):
    """The form an act runs in: the one its arguments name, else the run's style where the act has it, else its own."""
    spec = act.schema['properties'].get('by')
    if spec is None:return 'keys' if act.forms == 'K' else 'pointer' if style in (None, 'pointer', 'keys') else style
    if 'by' in args:return args['by']
    choices = spec['enum']
    if style is None:return choices[0] if choices[0] in ('direct', 'put', 'arrow') else 'pointer'
    if style in choices:return style
    if style == 'keys':return 'keys' if 'keys' in choices else choices[0]
    return {'put': 'put', 'arrow': 'arrow'}.get(choices[0], 'pointer' if 'pointer' in choices else choices[0])


def run(host, name, args=None, *, door, by=None, origin=None, word=''):
    """Run one act on the live window. `door` is always named ('owner', 'script'; 'her' is refused): a caller that forgot it
    must not get the owner's acts by default. Returns {act, door, ok, by, words, result, error: {code, words} or None,
    changed, seconds, presses}; `changed` is what watching() saw done during the act (a changing operation, an open handed
    to the computer, a program started)."""
    started = time.monotonic()
    envelope = {'act': str(name), 'door': door, 'ok': False, 'by': None, 'words': '', 'result': None, 'error': None, 'changed': []}
    c = None
    origin = origin or ('desktop-owner' if door == 'owner' else 'desk-script:script')
    try:
        if door == 'her':raise Refusal('NOT_OFFERED', REFUSALS['NOT_OFFERED'])
        if door not in ('owner', 'script'):raise Refusal('NOT_OFFERED', 'Acts come through the writing line or a script.')
        clean = desk_acts.check(name, args)
        act = ACTS[name]
        c = Ctx(host, name, clean, door, word or ('the act %s' % name), origin, form_for(act, clean, by))
        with watching() as seen, no_dialogs() as reached:
            try:
                try:words, result = DOERS[name](c)
                except Exception:
                    settle(host)
                    if reached:words, result = None, None
                    else:raise
                settle(host)
            finally:
                envelope['changed'] = list(seen)
        if reached:      # stopped at the window that asks; what it did before that, if anything, is said, never denied
            raise Refusal('DIALOG', REFUSALS['DIALOG'] + (' Before that: %s.' % ', '.join(dict.fromkeys(seen)) if seen else ''))
        envelope.update(ok=True, words=words, result=_plain(result), by=c.by)
    except Refusal as refusal:
        envelope.update(error={'code': refusal.code, 'words': refusal.words}, words=refusal.words, by=c.by if c is not None else None)
    except Exception as exc:  # noqa: BLE001 - an act that breaks is said as a refusal, never raised into the window
        words = REFUSALS['FAILED'] % (str(exc)[:240] or type(exc).__name__)
        envelope.update(error={'code': 'FAILED', 'words': words, 'kind': type(exc).__name__}, words=words, by=c.by if c is not None else None)
    envelope['seconds'] = round(time.monotonic() - started, 3)
    envelope['presses'] = c.presses if c is not None else 0
    host._desk_last = {k: envelope.get(k) for k in ('act', 'door', 'by', 'ok', 'words', 'result')}
    if name != 'read.desk':record(host, envelope, origin, c)
    return envelope


def record(host, envelope, origin, c):
    """One line in Graphite's journal per act (reading is not an event, so read.desk writes none)."""
    from . import activity
    if not envelope['ok']:state = 'REFUSED'
    elif isinstance(envelope.get('result'), dict) and envelope['result'].get('waits'):state = 'WAITING'
    else:state = 'DONE'
    reply = getattr(getattr(c, 'card', None), 'reply', None) if c is not None else None
    correlation = reply.get('correlation_id') if isinstance(reply, dict) else None
    words = desk_acts.said(envelope)
    if envelope['act'] == 'type.put' and envelope['ok']:      # the line's words stay the owner's: the journal says only that some were put
        words = 'Words were put in the writing line (%d characters); nothing was sent.' % len(str((envelope.get('result') or {}).get('text') or ''))
    try:activity.record(host.root, origin, envelope['act'], state, words, correlation_id=correlation)
    except Exception:  # noqa: BLE001 - the act is done and said; a journal that cannot be written is said by the journal itself
        pass
