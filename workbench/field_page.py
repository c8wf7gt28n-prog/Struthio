"""The Field in the window: the overview page of the centre, and the way in and out of it.

    show_field(host)     put the Field in front of the workspace (F9, Arrange ▸ Field, or type "field" in the writing line)
    leave_field(host)    put the workspace back; every room opener reaches this through the window's _close_start()
    open_object(host, obj)   open the real editor for one sheet of the Field, through the room's own opener

The Field overlays the workspace as Home does and releases nothing: tabs, unsaved text and the docks stay as they were.
It reads the workspace through Kernel.dispatch (workbench/field_source.py) each time it is shown; it keeps no copy.
Master specification, section 72: "A simple Open or Back action can accompany the transition."
"""
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from .field_qt import FieldView
from .field_source import read_field


class FieldPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName('FieldPage');self.setProperty('paperFunctionalInk', True)
        # Ignored both ways: the centre's stack takes the largest minimum of all its pages, and this one must never widen it.
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout = QVBoxLayout(self);layout.setContentsMargins(0, 0, 0, 0);layout.setSpacing(0)
        self.view = FieldView(self);self.view.setMinimumSize(0, 0);self.view.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout.addWidget(self.view)
        self.view.opened.connect(lambda obj: open_object(self.host, obj))
        self.view.left.connect(lambda: back(self.host))
        self.refused = []

    def minimumSizeHint(self):
        return QSize(0, 0)

    def sizeHint(self):
        return QSize(0, 0)

    def refresh(self):
        """Read the workspace again. A reader that cannot answer leaves the Field empty and says so in the status line."""
        host = self.host
        self.view.texture = host.session.state.get('desk_art', 'illustrated') != 'clean'
        kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
        if kernel is None:
            from .field_model import Field
            self.view.set_field(Field());self.refused = [('kernel', 'not available')];return
        from .engineering_kernel import operator
        field, self.refused = read_field(kernel, operator(), title='')
        if not field.title:
            field.title = host.root.name
        self.view.set_field(field)
        if self.refused and hasattr(host, 'statusBar'):
            host.statusBar().showMessage('Field · %d of its readers did not answer: %s' % (
                len(self.refused), ', '.join(sorted({name for name, _ in self.refused}))), 9000)


def show_field(host):
    """Bring the Field to the front. Coming from Home, Home is closed first so its folded panels return once."""
    from_home = bool(getattr(host, '_home_active', False))
    if from_home:
        host._close_start()
    page = getattr(host, 'field_page', None)
    if page is None:
        page = host.field_page = FieldPage(host)
        host.central_stack.addWidget(page)
    host._field_active = True;host._field_from_home = from_home
    host.central_stack.setCurrentWidget(page)
    host.context_bar.hide();host.doc_info.hide()
    page.refresh()
    host.setWindowTitle('Field — Graphite')
    page.view.setFocus(Qt.OtherFocusReason)
    return page


def leave_field(host):
    """Put the workspace back in the centre. Safe to call when the Field is not showing."""
    if not getattr(host, '_field_active', False):
        return
    host._field_active = False
    host.central_stack.setCurrentWidget(host.workspace_split)
    host.update_document_info()


def back(host):
    """Esc: back to where the owner came from, Home or the work."""
    from_home = bool(getattr(host, '_field_from_home', False))
    leave_field(host)
    if from_home or host.tabs.count() == 0:
        host.show_start()
    elif host.tabs.currentWidget() is not None:
        host.tabs.currentWidget().setFocus(Qt.OtherFocusReason)


def open_object(host, obj):
    """Open the real page for one object of the Field. Each opener is the room's own; each leaves the Field itself."""
    target = getattr(obj, 'target', None) or {}
    kind = target.get('kind') if isinstance(target, dict) else None
    try:
        if kind == 'office':
            from .office_qt import open_office
            return open_office(host, target['id'])
        if kind == 'document':
            from .document_qt import show
            return show(host, target['id'])
        if kind == 'investigation':
            from .investigations_qt import show
            return show(host, target['id'])
        if kind == 'pdf':
            from .pdf_qt import open_pdf
            return open_pdf(host, target['namespace'], target['item'], target.get('sha256'), int(target.get('page_index', 0)))
    except (ValueError, OSError, KeyError) as exc:
        host.statusBar().showMessage('Field · could not open %s: %s' % (obj.title, exc), 9000)
        return None
    host.statusBar().showMessage('Field · %s has no page of its own to open yet' % obj.title, 6000)
    return None
