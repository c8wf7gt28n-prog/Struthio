"""Graphite 1.0 F3 · every keyboard stop has a name a screen reader can say, and Tab reaches the presses of a scrolled page
(the walkthroughs' faults, item 8; X4's session 12).

X4 pressed Tab through the window: seven stops had no name a screen reader could say (a scroll area, a press, three
labels, two of the centre's glyph presses, the Brain room press), and the presses of a page in a scroll area (Storage's
Mount and Eject safely) were never reached: the scroll area took the focus as a whole.

    install(host)     one watcher on the window: when a part takes the keyboard's focus with no name of its own, it is
                      given one from what it shows (its words, its tooltip's first sentence, its placeholder, or what the
                      focused label's link says), never from an internal object name; a scroll area whose page holds
                      presses of its own hands the focus on to them (Tab walks into the page, and the page scrolls to the
                      press in focus).
    name_of(widget)   the name it would be given (also for a reader of the window).

It names and lets Tab through; it never presses anything.
"""
from __future__ import annotations

import re

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (QAbstractButton, QAbstractScrollArea, QApplication, QComboBox, QLabel, QLineEdit, QScrollArea,
                               QTabBar, QTextEdit, QPlainTextEdit, QWidget)

WORDS = {'scroll': 'A scrolled page', 'label': 'A line of words',
         'field': 'A place to type', 'press': 'A press'}
SAYABLE = re.compile(r'[A-Za-z]{2,}')
_FOCUS_IN = QEvent.FocusIn


def _plain(text):
    text = re.sub(r'<[^>]+>', ' ', str(text or ''))
    text = re.sub(r'[←-⯿■-◿☀-➿⌀-⏿]', ' ', text)      # glyphs a reader cannot say
    return ' '.join(text.replace('&', '').split())


def _sentence(text):
    first = re.split(r'(?<=[.:;])\s', _plain(text), maxsplit=1)[0].strip(' .:;')
    return first[:120]


def name_of(widget):
    """A name to say for this part, from what it shows; '' when it shows nothing to say."""
    for source in ((widget.text() if isinstance(widget, (QAbstractButton, QLabel)) else ''),
                   (widget.placeholderText() if isinstance(widget, QLineEdit) else ''),
                   (widget.currentText() if isinstance(widget, QComboBox) else ''),
                   widget.toolTip(), widget.accessibleDescription(), widget.statusTip(), widget.whatsThis()):
        said = _sentence(source)
        if SAYABLE.search(said):return said
    if isinstance(widget, QAbstractScrollArea):return WORDS['scroll']
    if isinstance(widget, QLabel):return WORDS['label']
    if isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit)):return WORDS['field']
    if isinstance(widget, QAbstractButton):return WORDS['press']
    return ''


def _presses_inside(area):
    page = area.widget() if isinstance(area, QScrollArea) else None
    if page is None:return False
    return any(w.focusPolicy() & Qt.TabFocus and w.isVisibleTo(page) for w in page.findChildren(QWidget))


class Namer(QObject):
    """On the application: names a part as it takes the focus; lets Tab into a scrolled page's presses."""

    def __init__(self, host):
        super().__init__(host);self.host = host

    def eventFilter(self, watched, event):
        if event.type() == _FOCUS_IN and isinstance(watched, QWidget):
            try:self.focused(watched, event)
            except RuntimeError:      # a part going away as it is focused
                pass
        return False

    def focused(self, widget, event):
        if widget.window() is not self.host:return
        if isinstance(widget, QScrollArea) and _presses_inside(widget):      # Tab walks into the page, never stops on its frame
            widget.setFocusPolicy(Qt.NoFocus)
            if event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason):
                forward = event.reason() == Qt.TabFocusReason
                page = widget.widget()
                inside = [w for w in page.findChildren(QWidget) if w.focusPolicy() & Qt.TabFocus and w.isVisibleTo(page) and w.isEnabled()]
                if inside:
                    target = inside[0] if forward else inside[-1]
                    target.setFocus(event.reason());widget.ensureWidgetVisible(target)
                    return
        if not widget.accessibleName() or not SAYABLE.search(widget.accessibleName()):
            said = name_of(widget)
            if said:widget.setAccessibleName(said)
        parent = widget.parentWidget()      # a press inside a scrolled page is brought into sight as Tab reaches it
        while parent is not None:
            if isinstance(parent, QScrollArea) and parent.widget() is not None and parent.widget().isAncestorOf(widget):
                parent.ensureWidgetVisible(widget);break
            parent = parent.parentWidget()


def install(host):
    if getattr(host, '_f3_namer', None) is not None:return host._f3_namer
    app = QApplication.instance()
    if app is None:return None
    namer = Namer(host);app.installEventFilter(namer);host._f3_namer = namer
    for tab_bar in host.findChildren(QTabBar):      # the tabs' own bar: its name, as its current tab says
        if not tab_bar.accessibleName():tab_bar.setAccessibleName('Tabs')
    return namer
