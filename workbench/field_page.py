"""The Field in the window: the overview page of the centre, and the way in and out of it.

    show_field(host)     put the Field in front of the workspace (F9, Arrange ▸ Field, or type "field" in the writing line)
    leave_field(host)    put the workspace back; every room opener reaches this through the window's _close_start()
    open_object(host, obj)   open the real editor for one sheet of the Field, through the room's own opener

The Field overlays the workspace as Home does and releases nothing: tabs, unsaved text and the docks stay as they were,
and Esc gives the keyboard back to whatever had it. It reads the workspace through Kernel.dispatch
(workbench/field_source.py) and keeps the reading until something changes: the workspace's journal says whether anything
was recorded since, so coming back with F9 is immediate when nothing was. R reads again whatever the journal says.
Master specification, section 72: "A simple Open or Back action can accompany the transition."
"""
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QApplication, QSizePolicy, QVBoxLayout, QWidget

from .field_model import Field
from .field_qt import FieldView
from .field_source import problems, read_field, read_network

FACES = (('work', 'w'), ('network', 'n'))     # the faces of the Field and the key that shows each


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
        self.view.face_chosen.connect(self.show_face)
        self.view.look_again.connect(lambda: self.refresh(force=True))
        self.view.stac_line.connect(lambda obj: stac_in_line(self.host, obj))
        self.view.stac_run.connect(lambda obj: stac_run(self.host, obj))
        self.view.faces = FACES;self.face = self.view.face = 'work'
        self.problem = ''            # what the last reading could not read, in words
        self.unread = set()          # records that refused: not asked again until the owner looks again
        self._read_at = None         # the journal's head when the work face was last read

    def minimumSizeHint(self):
        return QSize(0, 0)

    def sizeHint(self):
        return QSize(0, 0)

    def show_face(self, name):
        if name in dict(FACES) and name != self.face:
            self.face = self.view.face = name
            self.view.field.selected = ''          # another face holds other objects: start where that face starts
            self.refresh(force=True)

    def _journal_head(self, kernel, principal):
        """How far the workspace's journal has got. Showing the Field records nothing, so an unchanged head means an unchanged
        workspace as far as Graphite knows. None when it cannot be asked."""
        try:
            answer = kernel.dispatch('ledger.journal.status', {}, principal)
            return answer['result'].get('head') if answer.get('ok') else None
        except Exception:  # noqa: BLE001
            return None

    def refresh(self, force=False):
        """Read the workspace, unless nothing was recorded since the last reading. A reading that could not reach the records
        says so on the surface and in the status line; it never shows an empty workspace in their place."""
        host = self.host
        from .locations import program
        self.view.art_mode = host.session.state.get('desk_art', 'illustrated')     # Arrange ▸ Desk art: Illustrated, ASCII or Clean
        self.view.art_folder = program(host.root) / 'branding' / 'boss'
        self.view.texture = self.view.art_mode != 'clean'
        kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
        if kernel is None:
            self.problem = self.view.problem = 'Graphite\'s records are not available in this window'
            self.view.set_field(Field());self._read_at = None
            host.statusBar().showMessage('Field · ' + self.problem, 9000);return
        from .engineering_kernel import operator
        principal = operator()
        if self.face == 'network':                 # the network is read at every look: it is now, not a record
            field, reader = read_network(kernel, principal);self._read_at = None
        else:
            head = self._journal_head(kernel, principal)
            if not force and head is not None and head == self._read_at and self.view.field.objects:
                self.view._reveal_pending = True;self.view.update();return
            if force:self.unread = set()
            field, reader = read_field(kernel, principal, title='', skip=self.unread)
            self.unread |= set(reader.unread)
            if not field.title:field.title = host.root.name
            self._read_at = self._journal_head(kernel, principal)
        self.problem = self.view.problem = problems(reader)
        self.view.set_field(field)
        if self.problem:host.statusBar().showMessage('Field · ' + self.problem + ' · R looks again', 9000)


def show_field(host):
    """Bring the Field to the front. Coming from Home, Home is closed first so its folded panels return once. Asked for while
    it is already in front, it only takes the keyboard: nothing is read again and where the owner came from is kept."""
    page = getattr(host, 'field_page', None)
    if getattr(host, '_field_active', False) and page is not None:
        page.view.setFocus(Qt.OtherFocusReason);return page
    from_home = bool(getattr(host, '_home_active', False))
    focus = QApplication.focusWidget()
    if from_home:
        host._close_start()
    if page is None:
        page = host.field_page = FieldPage(host)
        host.central_stack.addWidget(page)
    host._field_active = True;host._field_from_home = from_home
    host._field_focus = focus if focus is not None and focus is not page.view else None
    host.central_stack.setCurrentWidget(page)
    host.context_bar.hide();host.doc_info.hide();host.workspace_status.hide()      # the Field has the whole centre
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
    """Esc: back to where the owner came from, Home or the work, with the keyboard where it was."""
    from_home = bool(getattr(host, '_field_from_home', False))
    focus = getattr(host, '_field_focus', None);host._field_focus = None
    leave_field(host)
    if from_home or host.tabs.count() == 0:
        host.show_start();return
    try:
        alive = focus is not None and focus.isVisible() and focus.window() is host
    except RuntimeError:             # the widget that had the keyboard is gone
        alive = False
    if alive:
        focus.setFocus(Qt.OtherFocusReason)
    elif host.tabs.currentWidget() is not None:
        tab = host.tabs.currentWidget()
        (tab.focusProxy() or tab).setFocus(Qt.OtherFocusReason)


def stac_in_line(host, obj):
    """S: the object's staC line in the writing strip, in Assignment, for the owner to read or change. Nothing runs; Ctrl+Enter
    there runs it. The Field stays where it is."""
    from .context_menu import inspect_in_line
    return inspect_in_line(host, obj.stac)


def stac_run(host, obj):
    """Shift+Enter: run the object's staC line through its normal path (the working area's staC page, through Kernel.dispatch).
    It is a read; a refusal is said as one. The Field stays in front and the answer opens beside it in the working area."""
    from .context_menu import Refused, run_stac
    try:
        ran = run_stac(host, obj.stac)
    except Refused as exc:
        host.statusBar().showMessage('Field · %s' % exc, 9000);return None
    page = getattr(host, 'field_page', None)
    if page is not None and getattr(host, '_field_active', False):
        page.view.setFocus(Qt.OtherFocusReason)        # the keyboard stays in the Field: the next arrow moves, the next Shift+Enter asks again
    return ran


def open_network(host, words):
    """Detail for the network face is the Log's Network stream, filtered to the chosen thing: the writing line goes to Log, the
    stream to Network, and the filter is the words the Log's own grammar takes (a host, a port, a program name)."""
    leave_field(host)
    bar = getattr(host, 'type_bar', None)
    if bar is None:
        return None
    bar.set_target('log')
    console = getattr(host, 'console', None)
    if console is not None and hasattr(console, 'set_size') and getattr(console, 'size_level', 1) == 0:
        console.set_size(1)                        # a one-line strip shows no stream: open it to half
    log = getattr(host, 'log_view', None)
    if log is not None and hasattr(log, 'choose'):
        log.choose('network')
        if words and hasattr(log, 'apply_filter'):log.apply_filter(words)
    return log


def open_object(host, obj):
    """Open the real page for one object of the Field, through its room's own opener. Whatever the opener did (a new tab, or a
    tab that was already there), the Field steps aside so the page is what the owner sees."""
    target = getattr(obj, 'target', None) or {}
    kind = target.get('kind') if isinstance(target, dict) else None
    opened = None
    try:
        if kind == 'office':
            from .office_qt import open_office
            opened = open_office(host, target['id'])
        elif kind == 'document':
            from .document_qt import show
            opened = show(host, target['id'])
        elif kind == 'investigation':
            from .investigations_qt import show
            opened = show(host, target['id'])
        elif kind == 'pdf':
            from .pdf_qt import open_pdf
            opened = open_pdf(host, target['namespace'], target['item'], target.get('sha256'), int(target.get('page_index', 0)))
        elif kind == 'network':
            return open_network(host, target.get('filter', ''))
        elif kind == 'job':
            from .context_menu import show_job
            opened = show_job(host, target['id'])
        else:
            host.statusBar().showMessage('Field · %s has no page of its own to open yet' % obj.title, 6000);return None
    except (ValueError, OSError, KeyError) as exc:
        reason = str(exc).strip().strip('\'"').replace('_', ' ').lower()[:120]
        host.statusBar().showMessage('Field · %s could not be opened%s' % (obj.title, ' (%s)' % reason if reason else ''), 9000)
        return None
    if opened is not None:
        leave_field(host)            # an opener that found its tab already open does not call the window's _close_start itself
    return opened
