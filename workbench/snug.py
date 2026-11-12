"""Snug: a page that overflows by a little is framed to fit, so it never scrolls for the last few lines.

Scrolling stays for what is truly long (a big folder, a long note). When a page is taller than its window by no more than
a quarter of the window, Ledger tightens it instead, a step at a time: the space between blocks first, then the margins,
then writing boxes (Jot it down, Ask Slate) down to a floor. When the window changes size the page is framed afresh
from its own spacing, so it never flickers between two states. Nothing is hidden and no
text gets smaller; only air is taken out.
"""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractScrollArea, QPlainTextEdit, QScrollArea, QTextEdit, QWidget

LEVELS = (1.0, .72, .5, .34, .22)   # the share of each gap kept, step by step
BOX_FLOOR = 64                      # a writing box keeps at least this much height
LIMIT = .25                         # more overflow than this is real length: it scrolls as it should


def layouts(widget):
    out = []
    lay = widget.layout()
    if lay is not None:
        stack = [lay]
        while stack:
            l = stack.pop();out.append(l)
            for i in range(l.count()):
                item = l.itemAt(i)
                if item.layout() is not None:stack.append(item.layout())
                elif item.widget() is not None and item.widget().layout() is not None and not isinstance(item.widget(), QAbstractScrollArea):
                    stack.append(item.widget().layout())
    return out


def remember(page):
    """The page's own spacing, margins and box heights, kept once so every step is measured from the original."""
    if page.property('snugKept'):return page._snug
    kept = {'layouts': [], 'boxes': []}
    for l in layouts(page):
        m = l.contentsMargins();kept['layouts'].append((l, l.spacing(), (m.left(), m.top(), m.right(), m.bottom())))
    for box in page.findChildren(QWidget):
        if isinstance(box, (QPlainTextEdit, QTextEdit)) and box.minimumHeight() > BOX_FLOOR:kept['boxes'].append((box, box.minimumHeight(), box.maximumHeight()))
    page._snug = kept;page.setProperty('snugKept', True);page.setProperty('snugLevel', 0)
    return kept


def apply(page, level):
    kept = remember(page);share = LEVELS[level]
    for l, spacing, (left, top, right, bottom) in kept['layouts']:
        try:
            if spacing > 0:l.setSpacing(max(2, round(spacing * share)))
            l.setContentsMargins(left, max(0, round(top * share)), right, max(0, round(bottom * share)))
        except RuntimeError:pass  # a layout that went with its widget
    box_share = 1.0 if level < 2 else LEVELS[level - 1]  # boxes give way only after the gaps have
    for box, low, high in kept['boxes']:
        try:
            h = max(BOX_FLOOR, round(low * box_share));box.setMinimumHeight(h)
            if high < 16777215:box.setMaximumHeight(max(h, round(high * box_share)))
        except RuntimeError:pass
    page.setProperty('snugLevel', level)


def height(page, width):
    """The page's height at this width, as the scroll area will lay it out (wrapped words included)."""
    lay = page.layout()
    if lay is not None:lay.activate()
    return page.heightForWidth(width) if page.hasHeightForWidth() else page.sizeHint().height()


def fit(area):
    """Frame one scroll area: when its page is taller than the window by a little, take air out until it fits.
    Decided afresh only when the window's size changes or the page grows, so it is steady (never steps back and forth)."""
    page = area.widget() if isinstance(area, QScrollArea) else None
    if page is None or not area.isVisible() or page.property('snugOff') or not area.widgetResizable():return
    view = area.viewport().height();width = area.width() - 2 * area.frameWidth()  # as wide as it is with no scroll bar
    if view < 120:return
    remember(page);level = page.property('snugLevel') or 0
    key = (view, width);over = height(page, width) - view
    if level and over < 0 and -over > getattr(page, '_snug_gain', 0) + 4:page._snug_key = None  # the page got shorter: it fits with its own air again
    if getattr(page, '_snug_key', None) == key and (over <= 0 or getattr(page, '_snug_long', None) == (key, over)):return  # nothing changed: leave it be
    if getattr(page, '_snug_key', None) != key and level:apply(page, 0);level = 0;over = height(page, width) - view  # start from the page's own air
    page._snug_key = key;natural = over + view
    if 0 < over <= view * LIMIT:
        while over > 0 and level + 1 < len(LEVELS):  # all the steps it needs at once: no visible stepping
            level += 1;apply(page, level);over = height(page, width) - view
        if over > 0:apply(page, 0);over = height(page, width) - view  # still too tall: it is long, let it scroll as it was
    if over > 0:page._snug_long = (key, over)
    page._snug_gain = max(0, natural - (over + view))  # the air taken out, to know when it can be given back
    area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff if over <= 0 else Qt.ScrollBarAsNeeded)


def fit_all(host):
    """Every page on show: the desk's tabs, Today, and the right panel."""
    for area in host.findChildren(QScrollArea):
        if area.isVisible() and area.objectName() not in ('RibbonScroll',):
            try:fit(area)
            except RuntimeError:pass
