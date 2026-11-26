"""Graphite's own window as it was, kept and put back (Graphite 1.0, F1; the door's rule is hand_door).

When her hand starts on the desk, snapshot() keeps what is yours in the window: the keyboard's focus and the text cursor and
selection in it, the tab chosen in every row of tabs, the current row and the selection in every list and tree, the place of
every scroll bar, and the Field's size and place (its zoom and scroll). restore() puts back the parts asked for and reads each
one back, so it says what came back and what could not ("a step is done only when its effect is verified").

What is in front, the selected sheet and what is over the work are the planner's (her_hand_qt.HerHand.put_back, through her
door, as acts a person would make); this module puts back what a person would put back by hand afterwards, directly, without
acts: none of it changes a record. A widget that is gone, or a row that is no longer there, is said, never guessed.

Only what is shown is kept: a hidden page keeps its own state. Whole numbers are compared (scroll steps, rows, characters);
the Field's zoom and place are compared in thousandths, as whole numbers.
"""
from __future__ import annotations

FOCUS_PARTS = ('focus',)
MOST_LISTS = 40
MOST_SCROLLS = 80
MOST_SELECTED = 200


def _alive(widget):
    try:
        import shiboken6
        return widget is not None and shiboken6.isValid(widget)
    except Exception:  # noqa: BLE001
        return widget is not None


def _name(widget):
    try:
        name = widget.accessibleName() or widget.objectName() or type(widget).__name__
        return name.split(':', 1)[0].strip() or name      # 'Writing line: Line, Terminal, ...' is said as 'Writing line'
    except RuntimeError:
        return 'a part of the window'


def _cursor_of(widget):
    """(position, anchor) of a text widget's cursor, or None."""
    from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QTextEdit
    try:
        if isinstance(widget, QLineEdit):
            start = widget.selectionStart()
            if start >= 0 and widget.hasSelectedText():
                end = start + len(widget.selectedText())
                return (start, end) if widget.cursorPosition() == start else (end, start)
            return (widget.cursorPosition(), widget.cursorPosition())
        if isinstance(widget, (QTextEdit, QPlainTextEdit)):
            c = widget.textCursor()
            return (c.position(), c.anchor())
    except RuntimeError:
        return None
    return None


def _set_cursor(widget, cursor):
    from PySide6.QtGui import QTextCursor
    from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QTextEdit
    position, anchor = cursor
    if isinstance(widget, QLineEdit):
        size = len(widget.text());position = min(position, size);anchor = min(anchor, size)
        if position == anchor:widget.setCursorPosition(position)
        else:widget.setSelection(anchor, position - anchor)
    elif isinstance(widget, (QTextEdit, QPlainTextEdit)):
        c = widget.textCursor();size = len(widget.toPlainText())
        c.setPosition(min(anchor, size));c.setPosition(min(position, size), QTextCursor.KeepAnchor);widget.setTextCursor(c)


def _field_place(view):
    """The Field's size and place, in thousandths (whole numbers), and its own flags."""
    try:
        return {'zoom': int(round(float(view.zoom) * 1000)), 'x': int(round(float(view.scroll_x) * 1000)), 'y': int(round(float(view.scroll_y) * 1000)),
                'fitted': bool(getattr(view, '_fitted', False)), 'auto': bool(getattr(view, 'auto_fit', False))}
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return None


def snapshot(host):
    """What is yours in Graphite's window now. Live widgets are kept under keys that start with '_' (never written anywhere)."""
    from PySide6.QtCore import QPersistentModelIndex
    from PySide6.QtWidgets import QAbstractItemView, QAbstractScrollArea, QApplication, QTabBar
    snap = {'kind': 'desk', 'focus': None, 'tabs': [], 'lists': [], 'scrolls': [], 'field': None}
    focus = QApplication.focusWidget()
    if focus is not None and (focus is host or host.isAncestorOf(focus)):
        snap['focus'] = {'name': _name(focus), 'cursor': _cursor_of(focus)};snap['_focus'] = focus
    tabs = []
    for bar in host.findChildren(QTabBar):
        if bar.isVisible() and bar.count() > 0:
            tabs.append({'_w': bar, 'index': bar.currentIndex(), 'text': bar.tabText(bar.currentIndex()).replace('&', ''), 'count': bar.count()})
    snap['_tabs'] = tabs;snap['tabs'] = [t['text'] for t in tabs]
    lists = []
    for view in host.findChildren(QAbstractItemView):
        if len(lists) >= MOST_LISTS:break
        model = view.model() if view.isVisible() else None
        sel = view.selectionModel() if model is not None else None
        if sel is None:continue
        chosen = [QPersistentModelIndex(i) for i in sel.selectedIndexes()[:MOST_SELECTED]]
        lists.append({'_w': view, 'current': QPersistentModelIndex(view.currentIndex()), 'selected': chosen, 'n': len(chosen), 'name': _name(view)})
    snap['_lists'] = lists;snap['lists'] = [l['name'] for l in lists]
    scrolls = []
    for area in host.findChildren(QAbstractScrollArea):
        if len(scrolls) >= MOST_SCROLLS:break
        if area.isVisible():
            scrolls.append({'_w': area, 'h': area.horizontalScrollBar().value(), 'v': area.verticalScrollBar().value(), 'name': _name(area)})
    snap['_scrolls'] = scrolls;snap['scrolls'] = [[s['name'], s['h'], s['v']] for s in scrolls]
    page = getattr(host, 'field_page', None)
    view = getattr(page, 'view', None) if page is not None else None
    if view is not None and view.isVisible():
        snap['field'] = _field_place(view);snap['_field'] = view
    return snap


def _put_tabs(snap):
    out = {'back': True, 'words': '', 'n': 0}
    for t in snap.get('_tabs') or ():
        bar = t['_w']
        if not _alive(bar) or not bar.isVisible():continue
        if bar.currentIndex() == t['index'] and bar.tabText(t['index']).replace('&', '') == t['text']:continue
        if t['index'] >= bar.count() or bar.tabText(t['index']).replace('&', '') != t['text']:
            out['back'] = False;continue      # that tab is not there now: it is said, never guessed
        bar.setCurrentIndex(t['index']);out['n'] += 1
        if bar.currentIndex() != t['index']:out['back'] = False
    out['words'] = ('%d tab%s chosen again' % (out['n'], '' if out['n'] == 1 else 's')) if out['n'] else ('' if out['back'] else 'a tab could not be chosen again')
    return out


def _put_lists(snap):
    from PySide6.QtCore import QItemSelection, QItemSelectionModel, QModelIndex
    out = {'back': True, 'words': '', 'n': 0}
    for l in snap.get('_lists') or ():
        view = l['_w']
        if not _alive(view) or view.selectionModel() is None:continue
        sel = view.selectionModel()
        want = [QModelIndex(p) for p in l['selected'] if p.isValid()]
        if len(want) != l['n']:out['back'] = False      # a row that was selected is no longer there
        now = set((i.row(), i.column(), i.internalId()) for i in sel.selectedIndexes())
        target = set((i.row(), i.column(), i.internalId()) for i in want)
        current = QModelIndex(l['current']) if l['current'].isValid() else QModelIndex()
        if now == target and view.currentIndex() == current:continue
        block = QItemSelection()
        for i in want:block.select(i, i)
        if current.isValid():sel.setCurrentIndex(current, QItemSelectionModel.NoUpdate)
        sel.select(block, QItemSelectionModel.ClearAndSelect)
        out['n'] += 1
        if set((i.row(), i.column(), i.internalId()) for i in sel.selectedIndexes()) != target:out['back'] = False
    out['words'] = ('the selection is back in %d list%s' % (out['n'], '' if out['n'] == 1 else 's')) if out['n'] else ('' if out['back'] else 'a selection could not come back')
    return out


def _clamped(bar, value):
    return max(bar.minimum(), min(int(value), bar.maximum()))


def _put_scrolls(snap, keep=()):
    """Every scrolled part back where it was, as far as its content now reaches (a list that grew shorter scrolls as far as it
    goes). A part that holds what her hand just said (her card, `keep`) stays where it is, so you can read it."""
    out = {'back': True, 'words': '', 'n': 0, 'not': []}
    kept = [w for w in keep if _alive(w)]
    for s in snap.get('_scrolls') or ():
        area = s['_w']
        if not _alive(area) or not area.isVisible():continue
        if any(area.isAncestorOf(w) for w in kept):continue
        h, v = area.horizontalScrollBar(), area.verticalScrollBar()
        want = (_clamped(h, s['h']), _clamped(v, s['v']))
        if (h.value(), v.value()) == want:continue
        h.setValue(want[0]);v.setValue(want[1]);out['n'] += 1
        if (h.value(), v.value()) != want:out['back'] = False;out['not'].append(s['name'])
    out['words'] = ('%d scrolled part%s back where %s were' % (out['n'], '' if out['n'] == 1 else 's', 'it' if out['n'] == 1 else 'they')) if out['n'] and out['back'] else (
        '' if out['back'] else 'not scrolled back: %s' % ', '.join(out['not'][:3]))
    return out


def _put_field(snap):
    view = snap.get('_field');want = snap.get('field')
    if want is None or not _alive(view) or not view.isVisible():return None
    if _field_place(view) == want:return {'back': True, 'words': ''}
    try:
        view.zoom = want['zoom'] / 1000;view._fitted = want['fitted'];view.auto_fit = want['auto']
        view.scroll_x = want['x'] / 1000;view.scroll_y = want['y'] / 1000
        view._layout();view.scroll_x = want['x'] / 1000;view.scroll_y = want['y'] / 1000;view.update()
    except (AttributeError, RuntimeError):
        return {'back': False, 'words': 'the Field could not be brought back to its size and place'}
    now = _field_place(view)
    ok = now is not None and now['zoom'] == want['zoom'] and abs(now['x'] - want['x']) <= 1000 and abs(now['y'] - want['y']) <= 1000
    return {'back': ok, 'words': 'the Field is at its size and place again' if ok else 'the Field is not at its size and place'}


def _put_focus(snap):
    want = snap.get('focus')
    if want is None:return None
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    widget = snap.get('_focus')
    if not _alive(widget) or not widget.isVisible() or not widget.isEnabled():
        return {'back': False, 'words': 'the place that had your keyboard (%s) is not shown now' % want['name'][:40]}
    widget.setFocus(Qt.OtherFocusReason)
    if want.get('cursor') is not None:
        try:_set_cursor(widget, want['cursor'])
        except RuntimeError:pass
    QApplication.processEvents()
    has = QApplication.focusWidget() is widget or widget.hasFocus()
    cursor_ok = want.get('cursor') is None or _cursor_of(widget) == tuple(want['cursor'])
    if has and cursor_ok:return {'back': True, 'words': 'your keyboard is back in %s%s' % (want['name'][:40], ', the cursor where it was' if want.get('cursor') else '')}
    if has:return {'back': False, 'words': 'your keyboard is back in %s, but its cursor is not where it was' % want['name'][:40]}
    # an offscreen or inactive window keeps no focus widget: what would have the keyboard when the window is in front
    try:
        if widget.window().focusWidget() is widget:return {'back': True, 'words': 'your keyboard is back in %s (when the window is in front)' % want['name'][:40]}
    except RuntimeError:
        pass
    return {'back': False, 'words': 'your keyboard could not go back to %s' % want['name'][:40]}


def restore(host, snap, parts=('focus', 'tabs', 'lists', 'scroll', 'zoom'), keep=()):
    """Put back the parts asked for, each read back: {'back', 'parts': {part: {'back', 'words'}}, 'words'}. The focus last."""
    from PySide6.QtWidgets import QApplication
    if not isinstance(snap, dict) or snap.get('kind') != 'desk':return {'back': None, 'parts': {}, 'words': ''}
    out = {}
    if 'tabs' in parts:out['tabs'] = _put_tabs(snap)
    if 'lists' in parts or 'selection' in parts:out['lists'] = _put_lists(snap)
    QApplication.processEvents()
    if 'zoom' in parts or 'scroll' in parts:
        field = _put_field(snap)
        if field is not None and field.get('words'):out['zoom'] = field
    if 'scroll' in parts:out['scroll'] = _put_scrolls(snap, keep)
    if 'focus' in parts:
        focus = _put_focus(snap)
        if focus is not None:out['focus'] = focus
    quiet = {k: v for k, v in out.items() if v.get('words')}
    back = all(v.get('back') is not False for v in quiet.values())
    return {'back': back, 'parts': quiet, 'words': ''}


def said(out):
    """The words of a restore: what came back, and what did not."""
    parts = (out or {}).get('parts') or {}
    back = [p['words'] for p in parts.values() if p.get('back') and p.get('words')]
    not_back = [p['words'] for p in parts.values() if p.get('back') is False and p.get('words')]
    return '; '.join(back + not_back)
