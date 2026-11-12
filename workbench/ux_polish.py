"""Shared presentation helpers: workspace overlines, empty-table hints and readable errors.

Presentation only. Nothing here changes data, permissions or what an operation reports;
error text keeps its meaning and drops only machine-local noise such as absolute paths.
"""
import html
import re
from pathlib import Path
from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractItemView, QLabel

ORANGE = '#ff9a32'
MUTED = '#b5bec8'


def overline(title, subtitle=''):
    """A workspace heading in Home's style: spaced orange title, optional quiet subtitle."""
    text = '<span style="color:%s;font-weight:700;letter-spacing:2px">%s</span>' % (ORANGE, html.escape(title.upper()))
    if subtitle:
        text += '<span style="color:%s">&nbsp;&nbsp;·&nbsp;&nbsp;%s</span>' % (MUTED, html.escape(subtitle))
    label = QLabel(text)
    label.setObjectName('workspaceOverline')
    label.setTextFormat(Qt.RichText)
    label.setWordWrap(bool(subtitle))  # a bare title never breaks across lines
    label.setAccessibleName(title + (' · ' + subtitle if subtitle else ''))
    return label


_ERRNO_MISSING = re.compile(r"\[Errno 2\] No such file or directory: '([^']+)'")


def readable_error(message, root=None):
    """Say what is missing in project terms; never hide the original meaning."""
    text = str(message or 'Operation failed')
    prefix = str(Path(root).resolve()) + '/' if root else None
    missing = _ERRNO_MISSING.search(text)
    if missing:
        path = missing.group(1)
        if prefix and path.startswith(prefix):path = path[len(prefix):]
        return 'Missing input · %s is not present in this project copy' % path
    if prefix:text = text.replace(prefix, '')
    if text.startswith('KeyError: '):return 'Missing field · ' + text[len('KeyError: '):].strip("'")
    return text


class _EmptyHint(QObject):
    def __init__(self, view, text):
        super().__init__(view)
        self.view, self.text = view, text
        view.viewport().installEventFilter(self)
        model = view.model()
        for signal in (model.rowsInserted, model.rowsRemoved, model.modelReset, model.layoutChanged):
            signal.connect(view.viewport().update)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Paint and self.view.model().rowCount() == 0 and self.text:
            self.view.viewportEvent(event)  # the view paints first; the hint sits on top
            painter = QPainter(obj)
            painter.setPen(QColor(MUTED))
            rect = obj.rect().adjusted(24, 18, -24, -18)
            painter.drawText(rect, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.text)
            painter.end()
            return True
        return False


def empty_hint(view, text):
    """Show a quiet sentence in an empty table or list; replaces any earlier hint."""
    if not isinstance(view, QAbstractItemView):return None
    hint = getattr(view, '_empty_hint', None)
    if hint is None:
        hint = _EmptyHint(view, text);view._empty_hint = hint
    else:
        hint.text = text
    view.viewport().update()
    return hint
