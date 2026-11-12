"""Words are whole (HATCH GRAPHITE-01, G-B): one small helper the offscreen checks share.

    whole_words(root)        every visible QLabel and QAbstractButton under `root` (and `root` itself) whose text, as
                             plain words, is wider than the room the widget really gives it: the contents rect the style
                             draws the words in, less what an ancestor clips away (a scroll viewport, a squeezed cell).
                             A wrapped label only needs its longest word to fit. A word squeezed to no width, or cut
                             off wholly sideways by an ancestor, is a finding (one scrolled below the fold is not). The
                             visible section titles of a QHeaderView are measured against their section's label room.
                             Returns a list of findings; empty is whole.
    regions(window, *parts)  the same over the window, split into findings inside the given parts and findings elsewhere.
    unexplained(findings)    the findings not on PENDING (known words awaiting edits in other files; see below).
    no_side_scroll(area)     True when a scroll area shows no horizontal scroll bar (none visible, or nothing to scroll).
    side_scrolls(root, allow) the scroll areas under `root` that scroll sideways, minus the ones that do by design.
    describe(findings)       the findings in one line each, for an assertion message.

Reads only: it measures what is on screen and changes nothing. Used by check_finder_ui and check_frame_ui; any other check
takes it the same way (sys.path.insert(0, str(PROGRAM / 'tools')); import ui_fit), e.g. check_graphite_ui and the rename's.
Checked push buttons are measured bold: theme2 draws every checked QPushButton at weight 600 but Qt sizes it at 400.
"""
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QFont, QFontMetrics, QTextDocument
from PySide6.QtGui import Qt as GuiQt  # mightBeRichText lives in QtGui's half of the Qt namespace
from PySide6.QtWidgets import (QAbstractButton, QAbstractScrollArea, QCheckBox, QHeaderView, QLabel, QPushButton, QRadioButton,
                               QStyle, QStyleOptionButton, QStyleOptionHeader, QToolButton, QWidget)

TOLERANCE = 1  # a pixel of rounding between the font's advance and the style's rect
ELIDES = ('StripLabel',)  # labels that paint their own ellipsis to the column and keep the whole line as their text and accessible text
# Known and not yet fixed: none. The checked words drawn bold but sized regular now keep their bold room (finder_qt.keep_bold_room
# in settings_qt, cabinet_qt, operations_qt and typebar_qt; V01 W1), so the whole-window assertion has no exceptions.
PENDING, PENDING_SLACK = (), 8


def plain(widget):
    """The words a widget shows, without markup or mnemonic marks ('&&' is one '&')."""
    text = widget.text() if hasattr(widget, 'text') else ''
    if not isinstance(text, str) or not text:return ''
    if isinstance(widget, QLabel):
        rich = widget.textFormat() == Qt.RichText or (widget.textFormat() == Qt.AutoText and GuiQt.mightBeRichText(text))
        if rich:
            doc = QTextDocument();doc.setHtml(text);text = doc.toPlainText()
        return text.replace('\u2029', '\n')  # a rich label's paragraphs are lines
    return text.replace('&&', '\0').replace('&', '').replace('\0', '&')


def name_of(widget):
    words = widget.accessibleName() or widget.objectName() or ''
    return type(widget).__name__ + (':' + words if words else '')


def _icon_room(button):
    """What an icon beside the words takes from their room."""
    if button.icon().isNull():return 0
    if isinstance(button, QToolButton):
        style = button.toolButtonStyle()
        if style == Qt.ToolButtonIconOnly or style == Qt.ToolButtonTextUnderIcon:return 0
    return button.iconSize().width() + 4


def _shows_words(widget):
    if isinstance(widget, QToolButton) and widget.toolButtonStyle() == Qt.ToolButtonIconOnly and not widget.icon().isNull():return False
    return True


def own_room(widget):
    """The width the style draws the words in, inside the widget's own rect. A band word drawn by its ink (desk_qt.InkWord:
    no padding, its box the ink and air each side) has its whole box."""
    if widget.property('inkWord'):return widget.contentsRect().width()
    if isinstance(widget, QLabel):
        room = widget.contentsRect().width() - 2 * widget.margin()
        if widget.indent() > 0:room -= widget.indent()
        return room
    if isinstance(widget, (QCheckBox, QRadioButton)):
        option = QStyleOptionButton();widget.initStyleOption(option)
        element = QStyle.SE_CheckBoxContents if isinstance(widget, QCheckBox) else QStyle.SE_RadioButtonContents
        return widget.style().subElementRect(element, option, widget).width() - _icon_room(widget)
    if isinstance(widget, QPushButton):
        option = QStyleOptionButton();widget.initStyleOption(option)
        room = widget.style().subElementRect(QStyle.SE_PushButtonContents, option, widget).width()
        if widget.menu() is not None:room -= widget.style().pixelMetric(QStyle.PM_MenuButtonIndicator, option, widget)
        return room - _icon_room(widget)
    if isinstance(widget, QToolButton):
        # The tool button's own chrome (padding, border, a menu arrow) as the style measures it in the size hint.
        natural = widget.fontMetrics().horizontalAdvance(plain(widget)) + _icon_room(widget)
        chrome = max(0, widget.sizeHint().width() - natural)
        return widget.contentsRect().width() - chrome
    return widget.contentsRect().width()


def need_of(widget, text):
    metrics = widget.fontMetrics()
    if isinstance(widget, QPushButton) and widget.isChecked() and not widget.property('inkWord'):  # theme2 draws every checked push button at weight 600, sized at 400 (a band word, desk_qt.InkWord, is drawn regular)
        font = QFont(widget.font());font.setWeight(QFont.DemiBold);metrics = QFontMetrics(font)
    lines = text.split('\n')
    if isinstance(widget, QLabel) and widget.wordWrap():  # a wrapped label breaks at spaces and at zero-width break points
        return max((metrics.horizontalAdvance(word) for line in lines for word in line.replace('\u200b', ' ').split()), default=0)
    return max((metrics.horizontalAdvance(line) for line in lines), default=0)


def outside_sideways(widget):
    """True when an ancestor cuts the widget off wholly to its left or right (pushed past a clipping edge sideways)."""
    parent, x = widget.parentWidget(), widget.x()
    while parent is not None:
        if x >= parent.width() or x + widget.width() <= 0:return True
        if parent.isWindow():return False
        x += parent.x();parent = parent.parentWidget()
    return False


def clipped_away(widget):
    """How much of the widget's width an ancestor hides (a scroll viewport, a cell narrower than the widget). A widget out
    of sight is None when it is above or below the fold (not a clipped word) and its whole width when an ancestor cuts it
    off sideways (a word that has vanished is not whole)."""
    seen = widget.visibleRegion().boundingRect()
    if seen.isEmpty():return widget.width() if outside_sideways(widget) else None
    return max(0, widget.width() - seen.width())


def _header_findings(root, skip=()):
    """The visible section titles of every QHeaderView (a list's column words), measured against the room the style
    gives a section's label (its rect less the stylesheet's padding and the sort arrow)."""
    for header in [root] + root.findChildren(QHeaderView):
        if not isinstance(header, QHeaderView) or header in skip or not header.isVisible() or header.window() is not root.window():continue
        model = header.model()
        if model is None:continue
        for logical in range(header.count()):
            if header.isSectionHidden(logical) or header.sectionSize(logical) <= 0:continue
            text = model.headerData(logical, header.orientation(), Qt.DisplayRole)
            if not isinstance(text, str) or not text.strip():continue
            option = QStyleOptionHeader();header.initStyleOptionForIndex(option, logical)
            option.rect = QRect(0, 0, header.sectionSize(logical), header.height()) if header.orientation() == Qt.Horizontal else QRect(0, 0, header.width(), header.sectionSize(logical))
            room = header.style().subElementRect(QStyle.SE_HeaderLabel, option, header).width();need = header.fontMetrics().horizontalAdvance(text.strip())
            if need > room + TOLERANCE:
                yield dict(widget=name_of(header) + ':section', text=text.strip()[:80], need=need, room=room, width=header.sectionSize(logical), clipped=0), header


def _findings(root, skip=()):
    for widget in [root] + root.findChildren(QWidget):
        if not isinstance(widget, (QLabel, QAbstractButton)) or widget in skip or type(widget).__name__ in ELIDES:continue
        if not widget.isVisible() or widget.height() <= 0 or not _shows_words(widget):continue
        if widget.window() is not root.window():continue
        text = plain(widget).strip()
        if not text:continue
        need = need_of(widget, text)
        if widget.width() <= 0:  # squeezed to nothing: the word has vanished
            yield dict(widget=name_of(widget), text=text[:80], need=need, room=widget.width(), width=widget.width(), clipped=0), widget;continue
        hidden = clipped_away(widget)
        if hidden is None:continue
        room = own_room(widget) - hidden
        if need > room + TOLERANCE:
            yield dict(widget=name_of(widget), text=text[:80], need=need, room=room, width=widget.width(), clipped=hidden), widget
    yield from _header_findings(root, skip)


def whole_words(root, skip=()):
    """Every visible label or button under root whose words do not fit the room it is given (empty list: all whole)."""
    return [finding for finding, _ in _findings(root, skip)]


def cut_lines(root):
    """Every visible wrapped label under root given less height than its words need at its width (the integration of the desk
    items: Log's capture reason, five lines, was given two in a narrow window), in whole_words' shape (need and room in px of
    height). A label in a scroll area of its own is as tall as its words, and so whole."""
    from PySide6.QtWidgets import QLabel
    out = []
    for label in [root] + root.findChildren(QLabel):
        if not isinstance(label, QLabel) or not label.isVisible() or not label.wordWrap() or not label.text().strip():continue
        need = label.heightForWidth(label.width())
        if need > label.height() + 1:out.append(dict(widget=name_of(label), text=label.text()[:80], need=need, room=label.height(), width=label.width(), clipped='lines'))
    return out


def regions(window, *parts):
    """whole_words for the window split in two: findings inside the given parts (widgets, e.g. the head and the centre) and
    findings elsewhere, so a check asserts its own parts and still records what it saw in the rest of the window."""
    mine, elsewhere = [], []
    for finding, widget in _findings(window):
        (mine if any(part is widget or part.isAncestorOf(widget) for part in parts if part is not None) else elsewhere).append(finding)
    return mine, elsewhere


def unexplained(findings):
    """The findings that are not on the PENDING list (or are more than its bold shortfall short): a check asserts none."""
    return [f for f in findings if f.get('widget') not in PENDING or f['need'] - f['room'] > PENDING_SLACK]


def no_side_scroll(area):
    """True when the scroll area shows no horizontal scroll bar (or has nothing to scroll sideways)."""
    bar = area.horizontalScrollBar()
    return not (bar.isVisible() and bar.maximum() > 0)


def side_scrolls(root, allow=()):
    """The visible scroll areas under root that scroll sideways, except the ones listed as sideways by design."""
    out = []
    for area in [root] + root.findChildren(QAbstractScrollArea):
        if not isinstance(area, QAbstractScrollArea) or area in allow or not area.isVisible():continue
        if not no_side_scroll(area):out.append(dict(area=name_of(area), maximum=area.horizontalScrollBar().maximum(), width=area.width()))
    return out


def describe(findings):
    return '; '.join('%s %r needs %d px, has %d' % (f['widget'], f['text'], f['need'], f['room']) if 'text' in f else
                     '%s scrolls sideways by %d px' % (f['area'], f['maximum']) for f in findings)
