"""The writing marker (VS03, HATCH DESKTOP-01): a small graphite X in the page margin beside the line being written on.

Margin form, carried from the UI-02 prototype review (MK-01…MK-13): the X sits in the page's own margin, left of the
yellow passage, on the caret's line; the passage itself is never touched (no viewport margin, no child widget, no extra
selection), so insertion, selection, undo and the click-to-caret area are exactly what they were. It is drawn from the
page's own paint event through an event filter, so the accessible tree gains nothing (MK-12). One controller per window
holds the enabled flag (the genuine setting `appearance.writing_marker`, Session field `writing_marker`), one 2 s blink
timer that runs only while an opted-in passage has keyboard focus, and one mark per passage. Under
`reading.reduce_motion` the X stands still with no timer (quiet motion wins over the setting). Passages opt in
explicitly; the source editor is refused (MK-08).
"""
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractScrollArea, QLineEdit, QPlainTextEdit, QWidget
from shiboken6 import isValid
from .shell2 import TEXT

KEY = 'appearance.writing_marker'   # the registry key
FIELD = 'writing_marker'            # the Session profile field it adapts
PERIOD_MS = 2000                    # one slow blink: 1 s shown, 1 s hidden (the caret flashes at 1 s)
INK = TEXT                          # graphite; 7.6:1 on the page, 7.2:1 on the yellow passage (measured, MK-03)
MIN_GLYPH = 7


def enabled_in(state):
    """The saved choice; True when the profile field is absent (older profiles, or a loader not yet present)."""
    value = state.get(FIELD, True) if isinstance(state, dict) else True
    return value if type(value) is bool else True


def motion_state(enabled, reduce_motion):
    """Words for readback: what a focused passage shows. Reduce motion wins over the setting's blink."""
    if not enabled:return 'off'
    return 'static' if reduce_motion else 'blinking'


def glyph_for(x_height):
    """The X scales with the passage font: 1.25 times the x-height (12 px on 14 pt Plex Mono, 10 px on Plex Sans)."""
    return max(MIN_GLYPH, round(float(x_height) * 1.25))


def geometry(room, glyph):
    """Pure placement. `room` is the page margin left of the passage edge, `glyph` the wanted X size.
    Returns (offset of the X centre left of the passage edge, drawn glyph size, form). The margin form keeps the X in a
    strip of glyph+8 px; when the margin is narrower (200 % text on a fixed 22 px margin, MK-07) the X shrinks to the
    margin instead of entering the passage, and the form is reported as `narrow`."""
    strip = glyph + 8
    if room >= strip:return strip / 2.0, glyph, 'margin'
    drawn = max(MIN_GLYPH, min(glyph, room - 4))
    return max(drawn / 2.0 + 1.0, room / 2.0), drawn, 'narrow'


def accepts(widget):
    """Only typed passages: a line or a plain text sheet; never the source editor (its gutter already marks the line)."""
    if not isinstance(widget, (QLineEdit, QPlainTextEdit)):return False
    if type(widget).__name__ == 'CodeEditor' or widget.objectName() == 'sourceEditor':return False
    return True


def draw_x(painter, centre, size, width):
    half = size / 2.0
    pen = QPen(QColor(INK), width);pen.setCapStyle(Qt.RoundCap)
    painter.setRenderHint(QPainter.Antialiasing, True);painter.setPen(pen)
    cx, cy = centre.x(), centre.y()
    painter.drawLine(QPointF(cx - half, cy - half), QPointF(cx + half, cy + half))
    painter.drawLine(QPointF(cx + half, cy - half), QPointF(cx - half, cy + half))


class PagePainter(QObject):
    """Paints every visible mark of one page from that page's own paint event. Parented to the page, so it goes with it."""

    def __init__(self, page):
        super().__init__(page);self.page = page;self.marks = [];self.paints = 0;self.painted_area = 0
        page.installEventFilter(self)

    def eventFilter(self, obj, event):
        page = getattr(self, 'page', None)
        if page is None or not isValid(page):return False
        if obj is page and event.type() == QEvent.Paint:
            # The page's own painting first (styled background, auto-fill), then the marks on top; Qt is told the event
            # is handled so the page is not painted twice. A mark whose passage is gone is dropped here.
            obj.paintEvent(event)
            self.marks = [m for m in self.marks if isValid(m) and isValid(m.widget)]
            shown = [m for m in self.marks if m.visible()]
            if shown:
                self.paints += 1;self.painted_area += event.rect().width() * event.rect().height()
                painter = QPainter(obj)
                for mark in shown:mark.paint(painter)
                painter.end()
            return True
        return False


class MarginMark(QObject):
    """One passage's X. Parented to the passage; listens to its caret, text, scrolling, focus and geometry."""

    def __init__(self, controller, widget):
        super().__init__(widget);self.controller = controller;self.widget = widget
        self.plain = isinstance(widget, QPlainTextEdit);self.page = None;self.page_child = None
        self.last_rect = QRect();self.clamped = False;self.form = 'margin';self.requests = 0
        widget.installEventFilter(self)
        if self.plain:
            widget.viewport().installEventFilter(self);widget.verticalScrollBar().valueChanged.connect(self.changed)
        widget.cursorPositionChanged.connect(self.changed);widget.textChanged.connect(self.changed)

    # ---- state ----------------------------------------------------------------------------------------------------
    def active(self):
        w = self.widget
        return isValid(w) and w.hasFocus() and not w.isReadOnly() and w.isEnabled() and w.isVisible()

    def visible(self):
        c = self.controller
        return c.enabled and self.active() and (c.on or c.reduce_motion())

    def glyph(self):return glyph_for(self.widget.fontMetrics().xHeight())

    def pen_width(self, glyph=None):return max(1.5, (glyph or self.glyph()) / 7.0)

    # ---- geometry -------------------------------------------------------------------------------------------------
    def resolve_page(self):
        """The nearest ancestor whose own margin left of the passage holds the strip; failing that, the ancestor with
        the widest free margin, where the X is drawn in the narrow form. An ancestor's room is the space between its
        left edge and the child on the way to the passage, counted only when no visible sibling of that child covers
        it (a dock beside the centre is a sibling, not a margin). The walk never leaves the scrolling page the passage
        sits on, so the X scrolls and clips with the page it points into."""
        need = self.glyph() + 8;child = self.widget;anc = child.parentWidget();best = (None, None, -1)
        while anc is not None:
            room = child.mapTo(anc, QPoint(0, 0)).x()
            if room > 0 and self.free_margin(anc, child, min(room, need)):
                if room >= need:return anc, child
                if room > best[2]:best = (anc, child, room)
            parent = anc.parentWidget()
            if anc.isWindow() or (isinstance(parent, QAbstractScrollArea) and anc is parent.viewport()):break
            child = anc;anc = parent
        return best[0], best[1]

    @staticmethod
    def free_margin(anc, child, width):
        """True when the strip of `width` px left of `child` on `anc` is anc's own surface: no visible sibling covers it."""
        left = child.mapTo(anc, QPoint(0, 0));strip = QRect(left.x() - width, left.y(), width, max(1, child.height()))
        for sibling in anc.children():
            if (isinstance(sibling, QWidget) and sibling is not child and not sibling.isWindow() and sibling.isVisible()
                    and sibling.geometry().intersects(strip)):return False
        return True

    def ensure_page(self):
        page, child = self.resolve_page()
        if page is not self.page:
            if self.page is not None and isValid(self.page):
                old = self.controller.painter(self.page)
                if self in old.marks:old.marks.remove(self)
                if self.last_rect.isValid():self.page.update(self.last_rect)
            self.page = page;self.page_child = child;self.last_rect = QRect()
            if page is not None:
                painter = self.controller.painter(page)
                if self not in painter.marks:painter.marks.append(self)
        return page

    def anchor(self):
        """Centre of the X in page coordinates; None when the caret line is scrolled out of the passage's view."""
        page = self.ensure_page()
        if page is None or not isValid(self.widget):return None, 0
        w = self.widget;rect = w.cursorRect()
        if self.plain and not w.viewport().rect().adjusted(0, -1, 0, 1).contains(rect.center()):return None, 0
        source = w.viewport() if self.plain else w
        caret = source.mapTo(page, rect.center())
        edge = self.page_child.mapTo(page, QPoint(0, 0)).x()
        offset, drawn, form = geometry(edge, self.glyph())
        self.form = form;self.clamped = form == 'narrow'
        return QPointF(edge - offset, caret.y()), drawn

    def mark_rect(self):
        centre, drawn = self.anchor()
        if centre is None:return QRect()
        pad = drawn + 4
        return QRect(int(centre.x() - pad / 2.0), int(centre.y() - pad / 2.0), pad, pad)

    def request(self):
        """Repaint the X's own small patch of the page (old and new place), nothing else."""
        page = self.ensure_page()
        if page is None or not isValid(page):return
        rect = self.mark_rect().adjusted(-2, -2, 2, 2);self.requests += 1
        page.update(rect.united(self.last_rect) if self.last_rect.isValid() else rect);self.last_rect = rect

    def changed(self, *_):self.request()

    def paint(self, painter):
        centre, drawn = self.anchor()
        if centre is not None:draw_x(painter, centre, drawn, self.pen_width(drawn))

    # ---- events ---------------------------------------------------------------------------------------------------
    def eventFilter(self, obj, event):
        widget = getattr(self, 'widget', None)   # a passage being destroyed can still deliver events while its mark is torn down
        if widget is None or not isValid(widget):return False
        t = event.type()
        if obj is widget:
            if t == QEvent.FocusIn:self.controller.focus_changed(self, True)
            elif t == QEvent.FocusOut:self.controller.focus_changed(self, False)
            elif t in (QEvent.Resize, QEvent.Move, QEvent.Show, QEvent.Hide, QEvent.FontChange, QEvent.StyleChange):self.request()
        elif self.plain and obj is widget.viewport() and t in (QEvent.Resize, QEvent.Move):self.request()
        return False

    def detach(self):
        w = self.widget
        if isValid(w):
            w.removeEventFilter(self)
            if self.plain:
                w.viewport().removeEventFilter(self)
                try:w.verticalScrollBar().valueChanged.disconnect(self.changed)
                except (RuntimeError, TypeError):pass
            for signal in (w.cursorPositionChanged, w.textChanged):
                try:signal.disconnect(self.changed)
                except (RuntimeError, TypeError):pass
            w.setProperty('writingMark', None)
        if self.page is not None and isValid(self.page):
            painter = self.controller.painter(self.page)
            if self in painter.marks:painter.marks.remove(self)
            if self.last_rect.isValid():self.page.update(self.last_rect)
        self.setParent(None);self.deleteLater()

    # ---- for checks (MK-13) ---------------------------------------------------------------------------------------
    def mark_rect_global(self):
        page = self.ensure_page();rect = self.mark_rect()
        if page is None or rect.isNull():return QRect()
        return QRect(page.mapToGlobal(rect.topLeft()), rect.size())

    def caret_rect_global(self):
        w = self.widget;rect = w.cursorRect()
        if self.plain:return QRect(w.viewport().mapToGlobal(rect.topLeft()), rect.size())
        return QRect(w.mapToGlobal(QPoint(rect.x() + 5, rect.y())), rect.size())


class WritingMarker(QObject):
    """The window's marker controller: the setting's consumer, the shared blink, the marks and their page painters."""

    def __init__(self, host):
        super().__init__(host if isinstance(host, QObject) else None);self.host = host
        self.marks = [];self.painters = {};self.on = True;self.ticks = 0
        self.enabled = enabled_in(getattr(getattr(host, 'session', None), 'state', None))
        self.timer = QTimer(self);self.timer.setInterval(PERIOD_MS // 2);self.timer.timeout.connect(self.tick)

    # ---- the setting and quiet motion -----------------------------------------------------------------------------
    def reduce_motion(self):
        profile = getattr(self.host, 'reading_profile', None) or {}
        return bool(profile.get('reduce_motion', False))

    def set_enabled(self, value):
        value = bool(value)
        if value == self.enabled:return
        self.enabled = value;self.on = True
        for mark in self.live():mark.request()
        self.refresh_timer()

    def motion_changed(self):
        """Called after a reading-profile change so the first moment after Reduce motion is already quiet."""
        self.refresh_timer();self.repaint_focused()

    # ---- marks ----------------------------------------------------------------------------------------------------
    def live(self):
        self.marks = [m for m in self.marks if isValid(m) and isValid(m.widget)]
        return list(self.marks)

    def mark_for(self, widget):
        return next((m for m in self.live() if m.widget is widget), None)

    def attach(self, widget):
        if not accepts(widget):return None
        existing = self.mark_for(widget)
        if existing is not None:return existing
        mark = MarginMark(self, widget);self.marks.append(mark);widget.setProperty('writingMark', True)
        if mark.active():self.focus_changed(mark, True)
        return mark

    def detach(self, widget):
        mark = self.mark_for(widget)
        if mark is not None:
            self.marks.remove(mark);mark.detach();self.refresh_timer()

    def painter(self, page):
        self.painters = {p: painter for p, painter in self.painters.items() if isValid(p) and isValid(painter)}
        painter = self.painters.get(page)
        if painter is None:painter = self.painters[page] = PagePainter(page)
        return painter

    def focused(self):
        return next((m for m in self.live() if m.active()), None)

    # ---- the blink ------------------------------------------------------------------------------------------------
    def focus_changed(self, mark, gained):
        if gained:self.on = True
        mark.request();self.refresh_timer()

    def refresh_timer(self):
        want = self.enabled and not self.reduce_motion() and self.focused() is not None
        if want and not self.timer.isActive():self.timer.start()
        elif not want and self.timer.isActive():self.timer.stop()
        if not want and not self.on:self.on = True;self.repaint_focused()

    def repaint_focused(self):
        mark = self.focused()
        if mark is not None:mark.request()

    def tick(self):
        self.ticks += 1
        if self.reduce_motion():
            self.refresh_timer();return   # static: the timer stops; nothing is repainted unless the X was hidden
        self.on = not self.on;self.repaint_focused()

    def set_phase(self, on):
        """For checks: force the shown or hidden phase before a grab. The blink restarts from this moment, so the forced
        phase holds for a full half-period instead of flipping under a grab taken a few milliseconds later."""
        self.on = bool(on)
        if self.timer.isActive():self.timer.start()
        self.repaint_focused()

    # ---- readback -------------------------------------------------------------------------------------------------
    def readback(self):
        """The consumer receipt for ledger.settings: requested is the saved choice, effective what passages show."""
        saved = enabled_in(getattr(getattr(self.host, 'session', None), 'state', None))
        return dict(requested=saved, effective=self.enabled, motion=motion_state(self.enabled, self.reduce_motion()),
                    passages=len(self.live()), period_ms=PERIOD_MS)

    def stats(self):
        focused = self.focused()
        return dict(ticks=self.ticks, timer_active=self.timer.isActive(), timer_interval_ms=self.timer.interval(), enabled=self.enabled,
                    on=self.on, reduce_motion=self.reduce_motion(), passages=len(self.live()), pages=len(self.painters),
                    focused=(focused.widget.objectName() or type(focused.widget).__name__) if focused else None,
                    page_paints=sum(p.paints for p in self.painters.values() if isValid(p)),
                    page_painted_area_px=sum(p.painted_area for p in self.painters.values() if isValid(p)))


def install(host):
    controller = getattr(host, 'writing_marker', None)
    if controller is None or not isValid(controller):
        controller = WritingMarker(host)
        try:host.writing_marker = controller
        except AttributeError:pass
    return controller


def attach(host, widget):
    """Opt a passage in. Safe before the controller exists (it is created on first use) and idempotent."""
    if host is None or not isinstance(widget, QWidget):return None
    return install(host).attach(widget)
