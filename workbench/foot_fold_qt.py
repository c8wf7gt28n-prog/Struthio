"""Graphite 1.1 B4 · One line: the window's foot folds away, and each thing it did has one place.

PLAN_1.1.md, B4. 1.0's foot (typebar_qt: the band of Line, Terminal, Search, Web and Log, its writing line, and the five meters
beside it) and the bar's line did one job twice. Once the bar stands (bar_qt: the dedicated session, or GRAPHITE_BAR=1 on X),
the foot is folded away and FOOT_MOVED says where each of its jobs went; nothing it did is lost. Without the bar (another
desktop, no X, GRAPHITE_BAR=0) the foot stays exactly as 1.0 had it: there its jobs have no other home. GRAPHITE_FOOT=1 keeps
it even with the bar.

The foot's object (host.type_bar) stays for its callers; its doors lead to the new places: Alt+1 and Alt+4 (Line, Search),
Alt+3 (an operation) and Ctrl+K open the bar's line; Alt+5 and Ctrl+Alt+` drop the Terminal; Alt+6 opens the Log.
"""
from __future__ import annotations

import os

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import QLabel, QLineEdit

from . import bar_qt
from .quick_settings_qt import QuickTray      # 1.1 B5

# Old place -> new place (the owner reads this table; the release notes carry it). K0's head_menus.MOVED is its model.
FOOT_MOVED = (
    ('Line: a Kas line, an operation after /, an address, words for Kas (the foot\'s line, Alt+1)',
     "The bar's line (a press on it, Win+R, Win+S, Alt+1): every row says what Enter does; a Kas line is Run on the line "
     'page, an operation is Run on the operations page, an address is Opened, Ask Kas is always its last row'),
    ('Search: names and words across the workspace (Alt+4, Ctrl+K, a leading ?)',
     "The bar's line (Alt+4, Ctrl+K): apps, files, settings, the desk and commands by name; its row 'Search inside files for …' "
     'finds their words too (the results in the working area, as before)'),
    ('Web: an address opened, or words searched for, in your own browser',
     "The bar's line: an address is its Open row; words have 'Search the web for …' (in your own browser; Kas fetches nothing)"),
    ('Terminal: your shell in your Files folder, with DOS words (Alt+5, Ctrl+Alt+`)',
     'The drop-down Terminal, from the top of the screen over any app: Win+` or Ctrl+Alt+T (and Alt+5, Ctrl+Alt+` in Kas); '
     "the line's Terminal and DOS rows run there"),
    ('Log: Events and Network, filtered from the line (Alt+6)',
     'View ▸ Log (Alt+6): the working area\'s Log, with its own Filter line (Enter filters; Ctrl+Enter captures, in Network)'),
    ('The meters CPU, GPU, RAM, TXT and NET at the foot\'s right, each a door to its card',
     'The bar\'s Quick Settings (1.1 B5): every meter in its tip; a press opens its panel, the five its fourth section, each the same door'),
    ('The arrow at the line\'s end, Ctrl+Enter and Ask Kas →', "Enter on the bar's line (its first row), or a press on any row"),
    ('Expand and Collapse (the room above the line)', 'View ▸ Console ▸ One Line, Half, Tall (as before), and Ctrl+`'),
    ('Short messages ("Saved as…") at the line', 'The working area\'s message line, as before (the foot only repeated them)'),
    ('The context word at the line\'s right end (the selected record, else the workspace)',
     "The centre bar's path (it names the same place), and the computer's window title on the bar"),
)
KEEP_ENV = 'GRAPHITE_FOOT'
WAIT_MS, WAIT_TRIES = 200, 60          # how long the fold waits for the bar to stand, at most (12 s)


def wanted(environ=None):
    environ = os.environ if environ is None else environ
    return environ.get(KEEP_ENV, '') != '1'


def bar_standing(host):
    bar = getattr(host, 'graphite_bar', None)
    try:return bool(bar is not None and getattr(bar, 'standing', False) and bar.isVisible())
    except RuntimeError:return False


def folded(host):
    return bool(getattr(host, 'foot_folded', False))


# ---- the bar's line takes Line, Search and Web --------------------------------------------------------------------------------------
def put_in_line(host, text='', tries=6):
    """The bar's line, open, holding `text` (its rows shown). Without the bar: the foot's own line, in Line. True when placed."""
    text = str(text or '')
    if not bar_standing(host):
        box = getattr(getattr(getattr(host, 'shell2', None), 'top', None), 'box', None)
        bar = getattr(host, 'type_bar', None)
        if bar is not None:
            try:type(bar).set_target(bar, 'line', focus=False)
            except Exception:  # noqa: BLE001
                pass
        if box is None:return False
        box.setText(text);box.setFocus();box.end(False);return True
    from .start_qt import open_start, is_open
    if not is_open(host, 'line'):open_start(host, 'line')
    panel = getattr(host, 'start_panel', None)
    try:ready = panel is not None and panel.isVisible() and panel.mode == 'line'
    except RuntimeError:ready = False
    if not ready:
        if tries > 0:QTimer.singleShot(250, lambda: put_in_line(host, text, tries - 1))
        return False
    panel.line.setText(text);panel.line.end(False);panel.line.setFocus();panel.find()
    return True


def search_inside(host, words):
    """'Search inside files for …': 1.0's Search page (names and words across Files, the cabinet, settings, commands and the
    Timeline), its results in the working area."""
    from .shell2 import to_console
    return to_console(host, 'find', words)


def search_web(host, words):
    """'Search the web for …': in this computer's own browser (the foot's Web, typebar_qt.TypeBar.open_web)."""
    bar = getattr(host, 'type_bar', None)
    if bar is not None:return bar.open_web(words)
    from urllib.parse import quote_plus
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    from .typebar_qt import WEB_SEARCH
    return QDesktopServices.openUrl(QUrl(WEB_SEARCH + quote_plus(words)))


def more_rows(host):
    """line_finder.MORE's maker for this window: the two rows the foot's Search and Web gave that the line had not."""
    def rows(words):
        from . import line_finder as lf
        words = lf.clean(words)
        if len(words) < 2 or words[:1] in '=?$>/@':return []
        out = [lf.Row('command', 'Search inside files for “%s”' % lf.short(words, 40),
                      'Names and words across Files, the cabinet, settings, commands and the Timeline: the results in the working area',
                      'Open', lambda w=words: search_inside(host, w), icon='command', tip="1.0's Search (Ctrl+K)")]
        if not lf.is_address(words):
            out.append(lf.Row('command', 'Search the web for “%s”' % lf.short(words, 40),
                              "In this computer's own browser; Kas itself fetches nothing", 'Open',
                              lambda w=words: search_web(host, w), icon='address', tip="1.0's Web"))
        return out
    rows.b4_host = host
    return rows


# ---- the Log under View -----------------------------------------------------------------------------------------------------------
class LogLine(QLineEdit):
    """The Log's own Filter line (the foot's line in Log mode was its filter): Enter filters the stream; Ctrl+Enter in Network
    starts a capture with it (log_qt's own, confirmed first); Esc folds the Log away."""

    def __init__(self, host, view):
        super().__init__(view);self.host = host;self.view = view;self.setObjectName('LogFilterLine')
        self.setPlaceholderText('Filter the Log: words (Events), or host, port, protocol (Network)')
        self.setAccessibleName('Filter the Log');self.setClearButtonEnabled(True);self.setMinimumWidth(220)
        self.returnPressed.connect(self.apply)

    def apply(self):
        errors = self.view.apply_filter(self.text())
        if errors:
            try:self.host.statusBar().showMessage('Filter: ' + '; '.join(errors), 6000)
            except (AttributeError, RuntimeError):pass
        return errors

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and event.modifiers() & Qt.ControlModifier and self.view.stream == 'network':
            self.view.start_capture(self.text());return
        if event.key() == Qt.Key_Escape:
            console = getattr(self.host, 'console', None)
            if console is not None:console.set_size(0)
            self.clearFocus();return
        super().keyPressEvent(event)


def log_line(host):
    """The Log's Filter line, put once into the Log view's head (beside its two stream tabs)."""
    view = getattr(host, 'log_view', None)
    if view is None:return None
    made = getattr(view, 'b4_line', None)
    if made is not None:return made
    head = view.layout().itemAt(0).layout() if view.layout() is not None and view.layout().count() else None
    if head is None:return None
    made = view.b4_line = LogLine(host, view)
    at = head.indexOf(view.filter_words)
    head.insertWidget(at if at >= 0 else head.count(), made, 2)
    return made


def open_log(host, toggle=True):
    """View ▸ Log (Alt+6): the Log in the working area, its Filter line ready; a second press folds it away."""
    console = getattr(host, 'console', None)
    if console is None:return False
    try:
        shown = console.mode == 'log' and console.size_level > 0 and host.isActiveWindow()
    except RuntimeError:
        shown = False
    if toggle and shown:console.set_size(0);return False
    from .start_qt import bring_forward
    bring_forward(host)
    if console.mode != 'log':console.set_mode('log')
    if console.size_level == 0:console.set_size(1)
    line = log_line(host)
    if line is not None:QTimer.singleShot(0, line.setFocus)
    return True


# ---- the meters: the Quick Settings' fourth section -------------------------------------------------------------------------------------
METER_KEYS = ('CPU', 'GPU', 'RAM', 'TXT', 'NET')


def pulse_of(host):
    return getattr(getattr(getattr(host, 'shell2', None), 'top', None), 'pulse', None)


def readings(host):
    """{key: (words, share or None)} as the five meters read now (desktop_header_qt.DesktopMonitors keeps reading them)."""
    pulse = pulse_of(host);out = {}
    for key in METER_KEYS:
        value = (getattr(pulse, 'values', None) or {}).get(key)
        if value is None:out[key] = ('—', None);continue
        try:
            words = value.text() or '—';share = value.value() if key != 'NET' else None
        except (RuntimeError, AttributeError, TypeError):
            words, share = '—', None
        out[key] = (words.replace('%', ' %') if words.endswith('%') and not words.endswith(' %') else words, share)
    return out


def meters_words(read):
    """The item's tip and name: every meter in words."""
    return ', '.join('%s %s' % (key, read.get(key, ('—', None))[0]) for key in METER_KEYS)


# 1.1 B5: B4's MetersItem and MetersFlyout became the Quick Settings panel's fourth section (quick_settings_qt.MetersSection,
# its rows these doors); the one button shows network, sound and power, the meters in its tip.


class DoorWords(QLabel):
    """What a meter's door opens, in words; a press on them opens it too (the row is one door)."""

    def __init__(self, words, fn, parent):
        super().__init__(words, parent);self.fn = fn

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):self.fn();return
        super().mouseReleaseEvent(event)


class MetersTray(QuickTray):
    """The bar's Quick Settings with the meters as its fourth section: their one home once the foot has folded (1.1 B5)."""
    with_meters = True

    def __init__(self, bar):
        super().__init__(bar);self.meters = self.button      # the meters' cards open above the Quick Settings button
        self.setAccessibleName('The tray: Quick Settings (network, sound, power and the meters)');self.button.show_words()


def meters_item(host):
    tray = getattr(getattr(host, 'graphite_bar', None), 'slot', lambda name: None)('tray')
    return getattr(tray, 'meters', None)


# ---- the fold -------------------------------------------------------------------------------------------------------------------
class KeepFolded(QObject):
    """Whatever shows the foot again (a layout reset, a restored state) is undone: the fold is the window's state now."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show and folded(getattr(self, 'host', None)):QTimer.singleShot(0, obj.hide)
        return False


def reroute(host):
    """The foot's doors lead to the new places (the objects stay for their callers)."""
    bar = getattr(host, 'type_bar', None);console = getattr(host, 'console', None)
    if bar is not None:
        original = type(bar).set_target

        def set_target(key, focus=True, bar=bar):
            if not focus or not folded(host):return original(bar, key, focus)
            from .typebar_qt import MAPPED
            mode = MAPPED.get(key, 'line')
            if mode == 'shell':
                from .drop_terminal_qt import toggle
                return toggle(host)
            if mode == 'log':return open_log(host, toggle=False)
            return put_in_line(host, '/' if key == 'kernel' else '')
        bar.set_target = set_target
        bar.search = lambda: put_in_line(host, '')
        bar.run_operation = lambda: put_in_line(host, '/')
    if console is not None:
        opened = type(console).open

        def open_(mode=None, focus=True, console=console):
            if folded(host) and (mode or console.mode) == 'shell':
                from .drop_terminal_qt import terminal
                return terminal(host).drop()
            return opened(console, mode, focus)
        console.open = open_
        focused = type(console).focus_box

        def focus_box(console=console):
            if not folded(host):return focused(console)
            if console.mode == 'log':
                line = log_line(host)
                if line is not None:line.setFocus()
            return None      # no foot: the line is the bar's, and running a line never opens it by itself
        console.focus_box = focus_box
    pulse = pulse_of(host)
    if pulse is not None:
        def open_card(key, pulse=pulse):
            from .meter_cards import open_card as card
            item = meters_item(host)
            try:anchor = item if item is not None and item.isVisible() else pulse.values[key]
            except RuntimeError:anchor = pulse.values[key]
            return card(host, anchor, key)
        pulse.open_card = open_card


def fold(host):
    """The foot folds away (once the bar stands): the Terminal drops, the Log is under View, the meters are in the tray, Search
    and Web are the line's. True when folded now or before."""
    if folded(host):return True
    dock = getattr(host, 'type_dock', None)
    if dock is None or not wanted() or not bar_standing(host):return False
    host.foot_folded = True
    keeper = getattr(host, '_foot_keeper', None)
    if keeper is None:
        keeper = host._foot_keeper = KeepFolded(host);keeper.host = host;dock.installEventFilter(keeper)
    dock.hide()
    reroute(host)
    from . import line_finder as lf
    lf.MORE[:] = [fn for fn in lf.MORE if getattr(fn, 'b4_host', None) is not host] + [more_rows(host)]
    bar_qt.register_slot('tray', MetersTray)
    log_line(host)
    try:
        from . import desk_qt
        QTimer.singleShot(0, lambda: desk_qt.apply(host))
    except Exception:  # noqa: BLE001
        pass
    return True


def key_verb(host, verb):
    """graphite-do's terminal, kas and halt (Win+` / Ctrl+Alt+T, Win+K, Pause) from any app: {ok, words}. None of them brings
    Graphite's window forward; halt only presses HALT, never RESUME."""
    if verb == 'terminal':
        from .drop_terminal_qt import toggle
        return toggle(host)
    ctl = getattr(host, 'kas_bar', None)
    if verb == 'kas':
        if ctl is None:return {'ok': False, 'words': 'Her panel is not on this window.'}
        try:done = ctl.toggle()
        except Exception as exc:  # noqa: BLE001
            return {'ok': False, 'words': 'Her panel did not open: %s' % (str(exc)[:120] or type(exc).__name__)}
        if ctl.panel_open():return {'ok': True, 'words': 'Her panel is open.'}
        if done == 'docked':return {'ok': True, 'words': 'Her column is in front, in Kas.'}
        return {'ok': True, 'words': 'Her panel is closed.'}
    if verb == 'halt':
        from .kas_voice import say as her
        if ctl is not None:pressed = ctl.pause_key()
        else:
            button = getattr(getattr(getattr(host, 'shell2', None), 'top', None), 'halt', None)
            if button is None:pressed = None
            elif button.held:pressed = False
            else:button.act();pressed = True
        if pressed is None:return {'ok': False, 'words': 'HALT is not on this window.'}
        if pressed is False:return {'ok': True, 'words': her('pause_held')}
        return {'ok': True, 'words': 'HALT is pressed: all of her work stops.'}
    return {'ok': False, 'words': 'not known'}


def install(host):
    """shell2, after the bar's install: the Terminal's keys, then the fold once the bar stands (it stands a moment after the
    window shows). Without the bar the foot stays."""
    from . import drop_terminal_qt
    drop_terminal_qt.install(host)
    host.foot_folded = getattr(host, 'foot_folded', False)
    host.fold_foot = lambda: fold(host)
    host.foot_moved = FOOT_MOVED
    if not wanted() or not bar_qt.wanted()[0]:return False
    tries = {'n': 0}

    def look():
        if getattr(host, '_closing', False) or folded(host):return
        if fold(host):return      # Ctrl+Alt+` is 1.0's console key: console.open('shell'), which drops the Terminal now (reroute)
        tries['n'] += 1
        if tries['n'] < WAIT_TRIES:QTimer.singleShot(WAIT_MS, look)
    QTimer.singleShot(0, look)
    return True
