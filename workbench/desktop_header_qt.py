"""Paper desktop monitors, the independent Slate switch, the work list (the System menu's process list) and the System menu's
symbol.

HATCH DESK D1a (the owner's brief of 2026-11-06): "The single erased Graphite symbol at far right replaces Nice." The
symbol (SystemButton, a NiceButton, so host.shell2.top.nice is still the head's control for everything running) is the
sharpened point drawn pale on the head band, named System menu. HATCH DESK D2: it opens the System menu
(system_menu_qt.SystemMenu: Game, Stop all jobs, the process list, Graphite services, then Log out, Return to Debian or Exit
Graphite, Restart, Shut down), and this module's NicePopup is that menu's process list (section mode): the active jobs and the
queue, a niceness slider on every row, the queue's order as its own control (a place number at the left of each queued row,
drag, Earlier and Later). The monitors are four columns of pale band lettering, each value beneath its key word.

UI-03 (the owner's request, AGENT-01): the four monitors (CPU · GPU · RAM · TXT, the context monitor) stand in the Ledger
Head immediately left of the Nice word, and Nice is the one control for everything running. Its popup opens with the kill
switch as the very first row ("■ Stop everything" then; HATCH DESK D2: Stop all jobs, under Game), bound to the existing Master Stop controller (the same confirm dialog,
the same stop thread, the same Ctrl+Shift+F12). Every active job row and every queued row carries a horizontal niceness
slider, left more urgent and right nicer, its value in words; changes go through jobs.nice and agenda.nice and the list
re-reads the truth after each. Queued rows reorder by drag or Earlier / Later (agenda.reorder); active jobs keep the order
they started in, because no registered operation reorders them, and the note says so rather than pretending.
"""
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QSize, Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QFrame, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QPushButton, QSizePolicy, QSlider, QToolButton, QVBoxLayout, QWidget,QMenu)

MONITORS_NOTE = 'Current Graphite host · CPU / GPU / RAM / TXT'   # the old column note's words, now the pulse's tooltip
KILL_WORDS = 'Stop all jobs'                                     # the kill switch: the Master Stop (HATCH DESK D2: the System menu's
                                                                 # second row, under Game, scoped in words to the work Graphite manages)
TIERS = ('now', 'normal', 'background')                          # agenda.NICE left to right: more urgent → nicer
TIER_WORDS = {'now': 'Now · urgent', 'normal': 'Normal', 'background': 'Background · waits for idle'}
NO_REORDER_NOTE = 'Active jobs keep the order they started in: no Graphite operation reorders a running job; their CPU niceness changes on the row.'
RUNNING_CAPTION = 'as they started'           # the active jobs' order, in the script (NO_REORDER_NOTE says why, in the tooltip)
QUEUE_CAPTION = 'drag to reorder'                # the queue's order, in the script (HATCH DESK D2)
SLIDER_CAPTION = 'left more urgent, right nicer'  # the sliders, in the script (the whole explanation is the note's tooltip)
ORDER_NOTE = ('Order: the number at the left of a queued row is its place in the queue; drag the row, or select it and choose Earlier '
              'or Later (agenda.reorder). Niceness is the row\'s slider: left more urgent, right nicer. They are separate.')


def caption_px(host, base):
    """Metadata in the right column follows reading.ui_pt (V-06): the design size at 14 pt, scaled, never below 10 px."""
    from .shell2 import scale_of
    return max(10, round(base * scale_of(host)))


def cpu_nice_words(value, basis=None):
    """A CPU nice value in words beside its number (UI-03: the value shown in words, not only a number). Linux nice 0 is
    normal and 19 yields most: 0 normal · 1–5 a little nicer · 6–12 nicer · 13–18 much nicer · 19 nicest. A value that is
    only a request for the next worker start says so."""
    if value is None:return '—'
    v = int(value)
    word = 'normal' if v <= 0 else 'a little nicer' if v <= 5 else 'nicer' if v <= 12 else 'much nicer' if v <= 18 else 'nicest'
    return '%d · %s' % (v, word) + (' · requested' if basis == 'NEXT_START_REQUEST' else '')


def tier_words(tier):
    """An Agenda tier in words; an unknown tier reads as the stored word so nothing is invented."""
    return TIER_WORDS.get(tier, str(tier).title())


def nice_reason(row):
    """Why a job's niceness cannot be changed from its row, in words, from the job_priority.describe readback."""
    basis = row.get('cpu_priority_basis')
    if basis == 'UNVERIFIED_PROCESS':return 'The running job process is not verified as owned by Graphite, so its niceness is not changed from here.'
    if basis == 'UNSUPPORTED':return 'Per-job niceness needs Linux.'
    if basis == 'UNAVAILABLE':return 'The job process is unavailable: ' + str(row.get('cpu_priority_note') or 'it has exited or changed') + '.'
    if row.get('state') not in ('Queued', 'Running'):return 'This job has finished.'
    return 'Only the owner of a queued or running job can change its niceness here.'


class DesktopMonitors(QWidget):
    """The four monitors in the Ledger Head: CPU, GPU, RAM and TXT (the context monitor). Each is a key word over a reading;
    an unavailable reading is the explicit '—' with the reason in its tooltip, never a substitute number."""
    KEYS = ('CPU', 'GPU', 'RAM', 'TXT')

    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('DesktopMonitors');self._scale = None
        self.setToolTip(MONITORS_NOTE)
        row = QHBoxLayout(self);row.setContentsMargins(0, 0, 0, 0);row.setSpacing(12)
        self.values = {};self.labels = {};self.setProperty('paperFunctionalInk', True)
        for key in self.KEYS:
            col = QVBoxLayout();col.setContentsMargins(0, 0, 0, 0);col.setSpacing(0);col.addStretch(1)  # the pair centred in the band
            label = QLabel(key);value = QLabel('—');value.setMinimumWidth(40)
            value.setObjectName('MonitorReading')
            for word in (label, value):word.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter);word.setProperty('paperFunctionalInk', True)
            # Readable at 1366 by 768 (UI-03): the reading keeps its width; the key word gives way first (elided in elide_keys).
            label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);label.setMinimumWidth(0)
            label.setAccessibleName(key + ' monitor');value.setAccessibleName(key + ' reading')
            col.addWidget(label);col.addWidget(value);col.addStretch(1);row.addLayout(col);self.values[key] = value;self.labels[key] = label
        self.restyle()
        self.previous = None;self.timer = QTimer(self, interval=2000)
        self.timer.timeout.connect(self.refresh);self.timer.start();self.refresh()

    def restyle(self):
        """Scale the monitor labels and readings with the interface size."""
        from .shell2 import scale_of
        from .desk_qt import ERASED_QUIET
        s = scale_of(self.host)
        if s == self._scale:return
        self._scale = s
        for key in self.values:
            self.labels[key].setStyleSheet('font-size:%dpx;color:%s;letter-spacing:1px;background:transparent;' % (caption_px(self.host, 12), ERASED_QUIET))
            self.values[key].setStyleSheet('font-size:%dpx;background:transparent;' % caption_px(self.host, 14))
            self.values[key].setMinimumWidth(max(40, self.values[key].fontMetrics().horizontalAdvance('100%') + 4))  # the numbers never clip
        QTimer.singleShot(0, self.elide_keys)

    def relight(self):
        """A live reading is green, and on the Illustrated and ASCII desks it glows a little, as the pointer and the Field's
        live things do. A reading that is not there ('—') does not glow, and the Clean desk has no glow at all."""
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from . import boss_theme as t
        try:glow = self.host.session.state.get('desk_art', 'illustrated') != 'clean'
        except Exception:  # noqa: BLE001 - a host without a session (a check): no ornament
            glow = False
        for value in self.values.values():
            lit = bool(glow and value.property('liveReading'))
            if lit == (value.graphicsEffect() is not None):continue
            if lit:
                halo = QGraphicsDropShadowEffect(value);halo.setOffset(0, 0);halo.setBlurRadius(14)
                colour = QColor(t.READY);colour.setAlphaF(0.85);halo.setColor(colour);value.setGraphicsEffect(halo)
            else:
                value.setGraphicsEffect(None)

    def elide_keys(self):
        """The key words elide to the room their reading leaves them; the readings (the numbers) keep their width."""
        for key, label in self.labels.items():
            room = self.values[key].width()
            text = label.fontMetrics().elidedText(key, Qt.ElideRight, room) if room > 0 else key
            if label.text() != text:label.setText(text)

    def resizeEvent(self, event):
        super().resizeEvent(event);self.elide_keys()

    def event(self, event):
        if event.type() == QEvent.StyleChange:QTimer.singleShot(0, self.restyle)  # the interface size changed: follow it now, not at the next sample
        return super().event(event)

    def refresh(self):
        from .host_observations import snapshot
        self.render(snapshot())

    def render(self,sample):
        from .host_observations import cpu_percent
        from .pulse_qt import gb
        self.restyle()
        self.sample=sample;now=sample['cpu']['counters'];busy=cpu_percent(self.previous,now);self.previous=now
        self.values['CPU'].setText('—' if busy is None else str(busy)+'%')
        self.values['CPU'].setToolTip('Current host CPU · /proc/stat · measured between valid increasing samples.' if busy is not None else 'CPU utilization unavailable; two valid increasing samples are required.')
        memory=sample['ram']['sample'];self.values['RAM'].setText(str(memory['percent'])+'%' if memory else '—')
        self.values['RAM'].setToolTip(('%s used / %s total · /proc/meminfo' % (gb(memory['used']),gb(memory['total']))) if memory else 'RAM utilization unavailable')
        gpu=sample['gpu']['percent'];self.values['GPU'].setText(str(gpu)+'%' if gpu is not None else '—')
        self.values['GPU'].setToolTip('Current host GPU · busiest reported adapter' if gpu is not None else 'GPU utilization unavailable from this driver')
        self.values['TXT'].setText('—');self.values['TXT'].setToolTip(sample['txt']['reason'])
        for value in self.values.values():
            live = value.text() != '—'
            if value.property('liveReading') != live:
                value.setProperty('liveReading', live)
                value.style().unpolish(value)
                value.style().polish(value)
        self.relight()
        self.setAccessibleDescription('Current Graphite host observation at '+str(sample['sampled_at'])+'; owner-host qualification remains separate.')


class SlateSwitch(QToolButton):
    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('SlateSwitch')
        self.setCheckable(True);self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName('Enable or disable new Graphite AI activity')
        from .shell2 import TEXT, ERASER, AMBER, LINE
        self.setStyleSheet('QToolButton#SlateSwitch {color:%s;background:%s;border:1px solid %s;border-radius:12px;padding:4px 9px;font-size:12px;} '
                           'QToolButton#SlateSwitch:checked {background:%s;}' % (TEXT, ERASER, LINE, AMBER))
        self.clicked.connect(self.change)
        self.timer = QTimer(self, interval=2000);self.timer.timeout.connect(self.refresh);self.timer.start();self.refresh()

    def refresh(self):
        from .ledger_control import value
        try:
            enabled = value(self.host.ledger_bridge.kernel, 'stacy.enabled')
            self.setChecked(enabled);self.setText('AI ON' if enabled else 'AI OFF');self.setEnabled(True)
            self.setToolTip('Allow new Graphite AI requests. Files, tools and staC remain available when OFF. An already running request may finish. ON does not start or download a model.')
        except Exception:
            self.setText('AI —');self.setEnabled(False);self.setToolTip('The Graphite AI setting is unavailable')

    def change(self, enabled):
        from .engineering_kernel import operator
        reply = self.host.ledger_bridge.kernel.dispatch('ledger.settings.set', {'key':'stacy.enabled', 'value':bool(enabled)}, operator())
        if not reply.get('ok'):
            self.host.statusBar().showMessage(reply.get('error', {}).get('message', 'Could not change the Graphite AI setting'))
        self.refresh()


class QueueList(QListWidget):
    """Only pending Agenda work is draggable. The Kernel commits the real order."""
    def __init__(self, popup):
        super().__init__();self.popup = popup
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction);self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAccessibleName('Queued Agenda work · drag to change scheduling order')

    def dropEvent(self, event):
        moved = self.currentItem()
        if moved is None:return
        ident = moved.data(Qt.UserRole)
        super().dropEvent(event)
        for position in range(self.count()):
            if self.item(position).data(Qt.UserRole) == ident:
                self.popup.commit_order(ident, position);break


class NicePopup(QFrame):
    """The work list: the active jobs, the queue, a niceness slider on every row, the queue's order. Three ways it is shown: a
    popup of its own (the old Nice list, kept for callers), embedded (Activity's hidden copy), and (HATCH DESK D2) section=True,
    the System menu's process list: a part of that menu (its Stop all jobs and Game are the menu's own rows, so the section's
    kill switch is hidden and it has no Game word), its words aligned with the menu's rows."""
    def __init__(self, host, anchor,embedded=False,section=False,menu=None):
        super().__init__(host, Qt.Widget if (embedded or section) else Qt.Popup);self.host = host;self.anchor = anchor;self.embedded=embedded;self.section=bool(section);self.menu=menu;self.signature = None;self.active_signature = None;self.adjusting = False
        self.setObjectName('NicePopup');self.setMinimumWidth(0 if (embedded or section) else 410);self.setMaximumWidth(16777215 if (embedded or section) else 540)
        self._scale = None;self._data = None;self._width = None
        from .shell2 import CARD, LINE, TEXT, ERASER
        self.setStyleSheet('QFrame#NicePopup {background:%s;border:1px solid %s;} QListWidget {background:%s;color:%s;border:0;font-size:13px;} '
                           'QListWidget::item {padding:7px;} QListWidget::item:selected {background:%s;color:%s;}' % (CARD, LINE, CARD, TEXT, ERASER, TEXT))
        col = QVBoxLayout(self);col.setContentsMargins(12, 10, 12, 12);col.setSpacing(8);self.col = col
        # UI-03: the very first row is the kill switch, full width, eraser pink: the existing Master Stop (its confirm dialog,
        # its stop thread, its Ctrl+Shift+F12) and nothing else. The old secondary "■ Stop" did the same thing, so it is gone.
        from .shell2 import ERASER_DEEP, ERASER_MARK
        self.kill = QPushButton(KILL_WORDS);self.kill.setObjectName('KillSwitch');self.kill.setCursor(Qt.PointingHandCursor)
        self.kill.setAccessibleName('Stop all jobs: the Master Stop for the work Graphite manages')
        self.kill.setMinimumHeight(40);self.kill.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed);self.kill.setFocusPolicy(Qt.StrongFocus)
        self.kill.setStyleSheet('QPushButton#KillSwitch {background:%s;color:%s;border:0;border-left:5px solid %s;border-radius:0;text-align:left;padding:9px 12px;font-weight:600;text-decoration:none;} '
                                'QPushButton#KillSwitch:hover {background:%s;} QPushButton#KillSwitch:pressed {background:%s;} '
                                'QPushButton#KillSwitch:focus {border:2px solid %s;border-left:5px solid %s;}' % (ERASER, TEXT, ERASER_MARK, ERASER_DEEP, ERASER_MARK, ERASER_MARK, ERASER_MARK))
        self.kill.clicked.connect(self.stop_everything);col.addWidget(self.kill);self.stop = self.kill  # the old attribute, for older callers
        controller = getattr(host, 'master_stop_controller', None)
        if controller is not None and hasattr(controller, 'faces'):controller.faces.append(self.kill_words)  # Stopping… and stuck follow the controller
        self.kill_words(controller)
        self.title = QLabel('NICE · GRAPHITE WORK');top = QHBoxLayout();top.addWidget(self.title, 1);col.addLayout(top)
        # The quiet-script rule (the owner, 2026-11-06): each heading in print, its caption and the note in the Paper script.
        from .shell2 import QuietWords
        self.running_label = QuietWords(host);self.running_label.explain('running and waiting for admission', lead='OWNED JOBS', sep=' · ')
        self.running_label.setToolTip(NO_REORDER_NOTE);col.addWidget(self.running_label)  # HATCH DESK D1a: it wraps in a narrow pane rather than clip
        self.running = QListWidget();self.running.setMaximumHeight(122);self.running.setAccessibleName('Active jobs · in the order they started; each row has a CPU niceness slider');col.addWidget(self.running)
        self.running.setToolTip(NO_REORDER_NOTE)
        # HATCH DESK D2 (the brief: "Carry forward queue reorder and distinguish it from niceness"): the queue's order is its own
        # control: each queued row's place number at its left (ORDER_NOTE), drag, Earlier and Later; niceness is each row's slider.
        self.queued_label = QuietWords(host);self.queued_label.explain(QUEUE_CAPTION, lead='AGENDA QUEUE', sep=' · ');col.addWidget(self.queued_label)
        self.queue = QueueList(self);self.queue.setMinimumHeight(120);self.queue.setMaximumHeight(245);col.addWidget(self.queue)
        self.empty = QLabel('No queued Agenda items');self.empty.setStyleSheet('font-size:13px;');col.addWidget(self.empty)
        order=QHBoxLayout();self.earlier=QPushButton('↑ Earlier');self.later=QPushButton('↓ Later')
        self.earlier.setAccessibleName('Move selected Agenda item earlier');self.later.setAccessibleName('Move selected Agenda item later')
        for b in (self.earlier, self.later):b.setToolTip(ORDER_NOTE)
        self.earlier.clicked.connect(lambda:self.move_selected(-1));self.later.clicked.connect(lambda:self.move_selected(1))
        order.addWidget(self.earlier);order.addWidget(self.later);order.addStretch();col.addLayout(order)
        self.queue.currentRowChanged.connect(self.order_selection);self.order_selection()
        self.note = QuietWords(host);col.addWidget(self.note)  # results and refusals in print; the standing explanation in script (D1-fix: the list's own size, 16 px at 14 pt, not a stray 13)
        self.waiting=QLabel();self.waiting.setTextFormat(Qt.PlainText);self.waiting.setWordWrap(True);col.addWidget(self.waiting)
        self.background = QCheckBox('Be nice to other apps · background CPU priority')
        self.background.clicked.connect(self.priority);col.addWidget(self.background)
        if embedded:self.background.setText('Background CPU for owned work')
        if self.section:  # the System menu's column is narrow at a large text size: the words short, the whole meaning the tooltip
            self.background.setText('Background CPU');self.background.setToolTip('Background CPU priority for the work Graphite owns: be nice to other programs. New processes start at the background priority; existing ones keep theirs until they exit.')
        row = QHBoxLayout();agenda = QPushButton('Open Agenda');agenda.clicked.connect(self.open_agenda);row.addWidget(agenda)
        trail = QPushButton('Work trail');trail.clicked.connect(self.open_trail);row.addWidget(trail)
        if not embedded and not self.section:  # the old popup's Game word; the System menu's Game row is its own (HATCH DESK D2)
            self.game = QPushButton('Game');self.game.setObjectName('GameRow');self.game.clicked.connect(self.open_game)
            self.game.setAccessibleName('Game: STRUTHIO in its offline desk mode, paused at tick zero');self.game.setToolTip('STRUTHIO in its offline desk mode, paused at tick zero')
            row.addWidget(self.game)
        col.addLayout(row)
        self.timer = QTimer(self, interval=2000);self.timer.timeout.connect(self.refresh)
        if embedded:self.setStyleSheet(self.styleSheet()+'QFrame#NicePopup {background:transparent;border:0;} QListWidget {background:transparent;} QCheckBox {color:#885e64;} QPushButton {background:transparent;color:#885e64;border:0;padding:5px 2px;text-decoration:underline;}')
        if self.section:
            # A part of the System menu: on its paper, no frame of its own; its Stop is the menu's Stop all jobs row and its title
            # the menu's own order; its words start where the menu's rows' words start (the icon column), its end at their padding.
            self.kill.hide();self.title.hide()
            self.setStyleSheet(self.styleSheet()+'QFrame#NicePopup {background:transparent;border:0;} QListWidget {background:transparent;}')
            self.align_to_menu()
        self.restyle();self.refresh()

    def align_to_menu(self):
        """Section mode: the words on the menu's word column (its padding and icon column), the end at its padding."""
        m = getattr(self.menu, 'm', None)
        if m is not None:self.col.setContentsMargins(m.pad + m.icon_col, m.margin, m.pad, m.margin);self.col.setSpacing(max(4, m.margin))

    def dismiss(self):
        """Out of the way before a dialog or a room opens: the popup hides itself; as the System menu's section, the menu closes."""
        if self.section and self.menu is not None:self.menu.close_menu(restore=False)
        elif not self.embedded:self.hide()

    def restyle(self):
        """The list, the empty word and the note follow reading.ui_pt (V-06); rows are rebuilt at the new size by render_data."""
        from .shell2 import scale_of
        s = scale_of(self.host)
        if s == self._scale:return
        self._scale = s;px = lambda base:caption_px(self.host, base)
        sheet = self.styleSheet().split('/*scale*/')[0]
        self.setStyleSheet(sheet + '/*scale*/QListWidget {font-size:%dpx;}' % px(14))
        self.empty.setStyleSheet('font-size:%dpx;' % px(14))
        for words in (self.note, self.running_label, self.queued_label):words.restyle()
        self.signature = None;self.active_signature = None

    def rebuild(self):
        if self._data is not None and not self.adjusting:self.signature = None;self.active_signature = None;self.render_data(self._data)

    def event(self, event):
        if event.type() == QEvent.StyleChange:QTimer.singleShot(0, lambda:(self.restyle(), self.rebuild()))  # rows at the new size now
        return super().event(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Rows are elided to the width they have (V-13): a different width rebuilds them from the last data.
        if self._data is not None and self._width != self.queue.viewport().width():QTimer.singleShot(0, self.rebuild)

    def showEvent(self, event):
        super().showEvent(event);self.refresh()
        if not self.embedded:self.timer.start()

    def hideEvent(self, event):
        self.timer.stop();super().hideEvent(event)

    def stop_everything(self):
        """The kill switch: the existing Master Stop through its action (the same confirm dialog, the same stop thread, the
        same shortcut); the popup gets out of the way first so the dialog is what you see."""
        self.dismiss()
        self.host.a_master_stop.trigger()
    stop_work = stop_everything  # the old name, for older callers

    def kill_words(self, controller=None):
        """The kill switch says what the Master Stop controller knows: Stopping… while its thread runs; the controller's detail
        (the advice score, its reasons, the shortcut, the held state) is the tooltip. Nothing here is a second stop."""
        controller = controller if controller is not None else getattr(self.host, 'master_stop_controller', None)
        running = bool(controller is not None and getattr(controller, 'running', False))
        text = 'Stopping…' if running else KILL_WORDS
        if self.kill.text() != text:self.kill.setText(text)
        stuck = bool(controller is not None and controller.button.property('stuck')) if controller is not None and hasattr(controller, 'button') else False
        if bool(self.kill.property('stuck')) != stuck:self.kill.setProperty('stuck', stuck);self.kill.style().unpolish(self.kill);self.kill.style().polish(self.kill)
        detail = str(getattr(controller, 'detail', '') or '') if controller is not None else ''
        self.kill.setToolTip('Stop all jobs Graphite manages: confirm, then every Graphite job, build, console, host tool and the phone link is stopped (Ctrl+Shift+F12). '
                             'Source files and unsaved editor buffers are kept.' + ('\n\n' + detail if detail else ''))

    def open_agenda(self):
        self.dismiss()
        from .shell2 import open_destination
        open_destination(self.host, 'agenda')

    def open_game(self):
        """STRUTHIO in desk mode (workbench.struthio_qt.show), the game the head's mark opened until HATCH DESK D1a."""
        self.dismiss()
        from .struthio_qt import show
        show(self.host)

    def open_trail(self):
        self.dismiss()
        self.host.ledger_bridge.show_work_trail()

    def refresh(self):
        if self.adjusting:return
        self.kill_words()
        if self.embedded and hasattr(self,'snapshot_refresh'):self.snapshot_refresh();return
        from .engineering_kernel import operator
        from .operation_priority import policy
        # D1-fix: the System menu's list is the work list's home now (Activity says it in one line), so it reads the same
        # snapshot Activity's list read: each queued row with its waiting reasons (ledger.operations, a read); agenda.view if not.
        idle = bool(getattr(self.host, 'agenda_runner', None) and self.host.agenda_runner.idle())
        reply = self.host.ledger_bridge.kernel.dispatch('ledger.operations', {'idle':idle}, operator())
        if reply.get('ok'):self.render_data(reply['result']['agenda']);return
        reply = self.host.ledger_bridge.kernel.dispatch('agenda.view', {}, operator())
        if not reply.get('ok'):
            self.queue.setEnabled(False);self.note.setText(reply.get('error', {}).get('message', 'Work list unavailable'));return
        self.render_data(reply['result'])

    def rows_height(self, view, most):
        """A list as tall as its first rows (V-13: computed from the rows, so nothing is clipped and two rows never scroll)."""
        return sum(view.sizeHintForRow(i) for i in range(min(most, view.count()))) + 2 * view.frameWidth() + 4

    def render_data(self,data):
        if self.adjusting:return
        from .operation_priority import policy
        self.restyle();self._data = data;self._width = self.queue.viewport().width()
        self.queue.setEnabled(True)
        pending_jobs = [r for r in data.get('next', []) if r.get('kind') == 'job']
        pending_jobs.sort(key=lambda row:(('foreground','normal','background').index((row.get('resource_request') or {}).get('priority','normal')),row.get('created') or 0,row['id']))
        active = data.get('now', []) + pending_jobs
        signature = [(r['id'],r['state'],r.get('nice'),r.get('cpu_nice'),r.get('cpu_priority_note'),r.get('cpu_priority_basis'),str(r.get('resource_request')),str(r.get('resource_wait'))) for r in active]
        if signature != self.active_signature:
            self.running.clear()
            for row in active:self.job_row(self.running,row)
            if not self.running.count():self.running.addItem('No active jobs')
            self.running.setFixedHeight(self.rows_height(self.running, 99 if self.section else 4))  # the System menu scrolls as one
            self.active_signature = signature
        queued = [r for r in data.get('next', []) if r.get('kind') != 'job' and r.get('state') in ('NEXT', 'PAUSED')]
        signature = [(r['id'], r['title'], r['state'], r['nice'], r.get('position'),str(r.get('schedule_checks')),r.get('reason')) for r in queued]
        if signature != self.signature and self.queue.state() != QAbstractItemView.DraggingState:
            selected = self.queue.currentItem().data(Qt.UserRole) if self.queue.currentItem() else None
            self.queue.clear()
            for row in queued:
                item = self.job_row(self.queue,row)
                if row['id'] == selected:self.queue.setCurrentItem(item)
            self.signature = signature
        self.queue.setVisible(bool(queued));self.empty.setVisible(not queued)
        # 0.5.1 (the owner, with 0.4.6 on the ThinkPad: the System menu "could be simplified"): with nothing queued, the
        # queue's heading, its two dimmed order buttons and the note about sliders said nothing; they are shown when there
        # is a queue to order or a row with a slider, and one line says the queue is empty otherwise.
        for part in (self.queued_label, self.earlier, self.later):part.setVisible(bool(queued))
        self.note.setVisible(bool(queued) or bool(active))
        if queued:self.queue.setFixedHeight(self.rows_height(self.queue, 99 if self.section else 3))  # up to three whole rows, then it scrolls (the System menu: every row, the menu scrolls as one)
        self.queue.setToolTip('No queued Agenda work' if not queued else 'Drag to change persistent Agenda scheduling priority. Crossing a tier adopts that tier; background work waits for idle.')
        self.order_selection()
        waiting=data.get('waiting',[]);self.waiting.setVisible(bool(waiting))
        self.waiting.setText('WAITING\n'+'\n'.join(str(r.get('title','Work'))+' · '+str(r.get('reason') or r.get('state','Waiting')) for r in waiting[:3])+ ('\nOpen Agenda for more.' if len(waiting)>3 else ''))
        try:self.background.setChecked(policy(self.host.root) == 'background')
        except (OSError, ValueError):self.background.setEnabled(False)
        if not self.note.text():
            whole = ('Each row has a niceness slider: left is more urgent, right is nicer. A queued row\'s number is its place in the queue: drag it, or Earlier and Later; a drag across a tier adopts that tier. '
                     + NO_REORDER_NOTE + ' Agenda tier controls scheduling; CPU nice controls an owned job process.')
            # In Activity the note is one line in the script and the whole explanation its tooltip, so what Graphite did (the
            # Timeline's lines below) stays in view; the System menu's list keeps the whole note.
            self.note.explain(SLIDER_CAPTION if self.section else 'Each row\'s slider: left is more urgent, right is nicer.' if self.embedded else whole);self.note.setToolTip(whole)

    def job_row(self, view, row):
        """One row: the title line, the niceness in words, and a full-width slider (UI-03: left more urgent, right nicer).
        Active jobs map Linux CPU nice 0 … 19 left to right through jobs.nice; queued items map the Agenda tiers now → normal
        → background through agenda.nice. A job without a verified owned process keeps the slider disabled with the reason
        in its tooltip. The slider commits on release (or 350 ms after a keyboard step) and the list re-reads the Kernel."""
        from .operations import SERVICES_HELD, PUBLIC_REASONS, tool_words
        px = lambda base:caption_px(self.host, base)
        place = view.count() + 1;queued = view is getattr(self, 'queue', None)
        item = QListWidgetItem();item.setData(Qt.UserRole,row['id']);view.addItem(item)
        widget = QWidget();outer = QHBoxLayout(widget);outer.setContentsMargins(4,3,4,3);outer.setSpacing(8)
        if queued:  # HATCH DESK D2: the queue's order is its own control, the place number at the left; niceness is the slider below
            number = QLabel(str(place));number.setObjectName('QueuePlace');number.setTextFormat(Qt.PlainText);number.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
            number.setStyleSheet('font-size:%dpx;font-weight:600;' % caption_px(self.host, 14));number.setToolTip(ORDER_NOTE)
            number.setAccessibleName('Place %d in the queue' % place);number.setMinimumWidth(number.fontMetrics().horizontalAdvance('00'));outer.addWidget(number)
        aside = (number.minimumWidth() + outer.spacing()) if queued else 0  # the place column's room, out of the title's width
        col = QVBoxLayout();col.setContentsMargins(0,0,0,0);col.setSpacing(2);outer.addLayout(col, 1)
        label = QLabel();label.setTextFormat(Qt.PlainText);label.setStyleSheet('font-size:%dpx;' % px(14))
        job = row.get('kind') == 'job'
        full = tool_words(row['title'], row['state']) if job else '%s · %s' % (row['title'],row['state'])
        if job and row['state']=='Queued':full+=' · '+(row.get('resource_request') or {}).get('priority','normal')
        # V-13: elided to the width the row really has, the whole text in the tooltip.
        label.setText(label.fontMetrics().elidedText(full,Qt.ElideRight,max(120,view.viewport().width()-24-aside)))
        label.setToolTip(full + ('\n' + str(row['title']) if job else ''));col.addWidget(label)
        if job and row['state']=='Queued':
            priority=(row.get('resource_request') or {}).get('priority','normal')
            label.setToolTip(full+'\nAdmission priority: '+priority+'\nRight click for Foreground / Normal / Background; CPU nice remains separate.')
            label.setContextMenuPolicy(Qt.CustomContextMenu)
            label.setFocusPolicy(Qt.StrongFocus)
            def priorities(position):
                menu=QMenu(label)
                for choice in ('foreground','normal','background'):
                    action=menu.addAction(choice.title());action.setCheckable(True);action.setChecked(choice==priority)
                    action.triggered.connect(lambda checked=False,choice=choice:self.commit_priority(row['id'],choice))
                menu.exec(label.mapToGlobal(position))
            label.customContextMenuRequested.connect(priorities)
        from .shell2 import LINE, QUIET, ERASER_MARK, AMBER_EDGE
        reading = QLabel();reading.setTextFormat(Qt.PlainText);reading.setStyleSheet('font-size:%dpx;color:%s;' % (px(13), QUIET));col.addWidget(reading)
        slider = QSlider(Qt.Horizontal);slider.setMinimumWidth(110);slider.setFixedHeight(24);col.addWidget(slider)
        slider.setStyleSheet('QSlider::groove:horizontal {height:4px;background:%s;border-radius:2px;} '
            'QSlider::sub-page:horizontal {background:%s;border-radius:2px;} '
            'QSlider::handle:horizontal {width:12px;background:%s;border:1px solid %s;border-radius:6px;margin:-5px 0;}' % (LINE,AMBER_EDGE,ERASER_MARK,QUIET))
        cpu = job;tiers = TIERS;caption = 'CPU nice · ' if cpu else 'Agenda tier · '
        def words(value):return caption + (cpu_nice_words(value, row.get('cpu_priority_basis')) if cpu else tier_words(tiers[value]))
        if cpu:
            slider.setRange(0,19);current = row.get('cpu_nice');slider.setValue(current if current is not None else 0)
            slider.setEnabled(bool(row.get('can_adjust_nice') and current is not None and 0 <= current <= 19))
            tip = 'Left is more urgent, right is nicer. Linux CPU nice: 0 = normal, 19 = most yielding. Affects the tracked job process and verified descendants. The OS may refuse a return to higher priority. '+row.get('cpu_priority_note','')
            slider.setToolTip(tip if slider.isEnabled() else 'Niceness cannot be changed from here. ' + nice_reason(row) + '\n' + tip)
            reading.setText(words(current))
            reading.setToolTip({'NEXT_START_REQUEST':'Request for the next worker start; not yet applied to a process.','OBSERVED_PROCESS':'Read back from the verified running process.'}.get(row.get('cpu_priority_basis'),'Process priority is unavailable or unverified. ' + nice_reason(row)))
        else:
            slider.setRange(0,2);slider.setValue(tiers.index(row.get('nice','normal')) if row.get('nice','normal') in tiers else 1)
            slider.setToolTip('Left is more urgent, right is nicer. Agenda priority: Now → Normal → Background. Background waits for idle. This changes real scheduling priority, independently of CPU nice.')
            reading.setText(caption + tier_words(row.get('nice','normal')))
            slider.setEnabled(row.get('state') in ('NEXT','PAUSED'))
            if not slider.isEnabled():slider.setToolTip('Only queued or paused Agenda work changes tier here; this item is ' + str(row.get('state','')).lower() + '.')
        checks=row.get('schedule_checks') or {}
        # V-05: the held state is one sentence everywhere; the machine word stands for the service summary beside it.
        reasons=[checks.get('services_summary') or r if r==SERVICES_HELD else PUBLIC_REASONS.get(r,r) for r in (checks.get('reasons') or [])]
        if job and (row.get('resource_wait') or {}).get('reason'):reasons.append(row['resource_wait']['reason'])
        if reasons:
            label.setToolTip(label.toolTip()+'\n'+'\n'.join(reasons))
            label.setText(label.fontMetrics().elidedText(full+' · waiting',Qt.ElideRight,max(120,view.viewport().width()-24-aside)))
            reason=QLabel('\n'.join(reasons[:2]));reason.setTextFormat(Qt.PlainText);reason.setWordWrap(True);reason.setStyleSheet('font-size:%dpx;color:#6c675e;' % px(13));col.addWidget(reason)
        slider.setAccessibleName(('CPU nice for ' if cpu else 'Agenda tier for ')+row['title']+' · left more urgent, right nicer')
        timer = QTimer(widget);timer.setSingleShot(True);timer.setInterval(350)
        def commit():
            if slider.isSliderDown():return
            timer.stop();self.adjusting=False
            self.commit_nice(row['id'],slider.value(),cpu)
        def changed(value):
            reading.setText(words(value));self.adjusting=True;timer.start()  # the words follow the drag; the truth is re-read after the commit
        slider.valueChanged.connect(changed)
        slider.sliderPressed.connect(lambda:setattr(self,'adjusting',True))
        slider.sliderReleased.connect(commit);timer.timeout.connect(commit)
        # The row is as tall as its words at this width and size (the fixed 74/112 px clipped a wrapped reason).
        view.setItemWidget(item,widget);widget.ensurePolished()  # measured in the view, with the inherited style's fonts
        for label_ in widget.findChildren(QLabel):label_.ensurePolished()
        # G-B: elide again with the font the row really has now (measured before polish, a 14 px title was elided as 13 px and clipped).
        label.setText(label.fontMetrics().elidedText(full + (' · waiting' if reasons else ''), Qt.ElideRight, max(120, view.viewport().width() - 24 - aside)))
        width = max(120, view.viewport().width());widget.setFixedWidth(width);outer.activate()
        tall = max(56, widget.sizeHint().height(), widget.heightForWidth(width) if widget.hasHeightForWidth() else 0)
        widget.setMinimumWidth(0);widget.setMaximumWidth(16777215);outer.activate()
        item.setSizeHint(QSize(0, max(tall, widget.sizeHint().height())))
        return item

    def commit_priority(self,ident,priority):
        from .engineering_kernel import operator
        result=self.host.ledger_bridge.kernel.dispatch('jobs.priority',{'id':ident,'priority':priority},operator())
        self.note.setText('Next admission: '+priority+' · CPU nice unchanged' if result.get('ok') else result.get('error',{}).get('message','Could not change admission priority'))
        self.active_signature=None;QTimer.singleShot(0,self.refresh)

    def commit_nice(self, ident, value, cpu):
        from .engineering_kernel import operator
        operation = 'jobs.nice' if cpu else 'agenda.nice'
        arguments = {'id':ident,'value':value} if cpu else {'id':ident,'nice':('now','normal','background')[value]}
        reply = self.host.ledger_bridge.kernel.dispatch(operation,arguments,operator())
        result = reply.get('result') or {}
        message=('CPU nice request saved for the next worker start.' if result.get('state')=='QUEUED' else
                 'CPU nice requested '+str(result.get('requested'))+' · observed '+str(result.get('actual')) if cpu else 'Agenda scheduling tier saved.')
        if result.get('notice'):message+=' '+result['notice']
        self.note.setText(message if reply.get('ok') else reply.get('error',{}).get('message','Could not change niceness'))
        self.signature = None;self.active_signature = None
        QTimer.singleShot(0,self.refresh)

    def commit_order(self, ident, position):
        from .engineering_kernel import operator
        reply = self.host.ledger_bridge.kernel.dispatch('agenda.reorder', {'id':ident, 'position':position}, operator())
        self.note.setText('Agenda order saved · destination tier '+str((reply.get('result') or {}).get('nice','')) if reply.get('ok') else reply.get('error', {}).get('message', 'Could not save scheduling priority'))
        self.signature = None;self.refresh()

    def move_selected(self,direction):
        row=self.queue.currentRow();item=self.queue.currentItem()
        if item is not None:self.commit_order(item.data(Qt.UserRole),max(0,min(self.queue.count()-1,row+direction)))

    def order_selection(self,*_):
        row=self.queue.currentRow();self.earlier.setEnabled(row>0);self.later.setEnabled(row>=0 and row<self.queue.count()-1)

    def priority(self, enabled):
        controller = self.host.master_stop_controller
        try:
            controller.select_priority('background' if enabled else 'normal')
            failed = [r for r in controller.priority_report if r['state'] in ('denied', 'refused')]
            self.note.setText('; '.join(r.get('reason', 'OS priority change refused') for r in failed) if failed and enabled else
                             'Background CPU priority selected.' if enabled else 'Normal CPU priority applies to new processes. Existing lower priorities remain until they exit.')
        except Exception as exc:self.note.setText('Could not change CPU priority: ' + str(exc))
        self.refresh()


class NiceButton(QToolButton):
    """The one head control for everything running (UI-03). Its popup opens with the kill switch first and focused; Enter,
    Return and Space open it from the keyboard; Escape closes it (a popup's own rule), and focus returns to this word."""
    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('NiceButton')
        self.setText('Nice ▾');self.setAccessibleName('Nice · everything running, its order and niceness, and Stop')
        self.setToolTip('Everything running, its order and its niceness, and Stop all jobs: the Master Stop (Ctrl+Shift+F12).')
        self.setCursor(Qt.PointingHandCursor);self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumHeight(34);self.popup = None;self.clicked.connect(self.open)

    def event(self, event):
        if event.type() == QEvent.ShortcutOverride and event.key() in (Qt.Key_Return, Qt.Key_Enter):event.accept();return True
        return super().event(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space, Qt.Key_Select) and not event.isAutoRepeat():self.open();return
        super().keyPressEvent(event)

    def open(self):
        if self.popup is None:self.popup = NicePopup(self.host, self)
        point = self.mapToGlobal(QPoint(self.width(), self.height()))
        self.popup.adjustSize();self.popup.move(point.x() - self.popup.width(), point.y());self.popup.show()
        self.popup.kill.setFocus(Qt.TabFocusReason)  # the kill switch is the first row and the first thing the keyboard reaches


class SystemButton(NiceButton):
    """The single erased Graphite symbol at the far right of the head (HATCH DESK D1a; the owner: it "replaces Nice"). The
    sharpened point drawn pale straight onto the band (graphite_brand.paint_erased_mark), as wide as the button and centred
    in the band's height; tooltip and accessible name System menu. Keyboard focus and hover put a short eraser-pink mark under
    it (an action); while its menu is open the mark is pencil yellow (the active choice). HATCH DESK D2: it opens the System
    menu (system_menu_qt.SystemMenu), downward from the upper right, the point-mirror image of the cat's programs list; Enter,
    Return and Space open it with its first row (Game) under focus, a click with the menu itself holding focus."""
    NAME = 'System menu'

    def __init__(self, host):
        super().__init__(host);self.setObjectName('SystemMenu');self.setText('System ▾');self.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.setAccessibleName(self.NAME);self.setToolTip(self.NAME)
        self.setAccessibleDescription('Game; Stop all jobs (Ctrl+Shift+F12); the process list with its order and niceness; Graphite services On, Off, Restart; '
                                      'Log out, Return to Debian or Exit Graphite, Restart, Shut down')
        self.setProperty('paperIcon', True);self.setProperty('paperFunctionalInk', True);self.setMinimumHeight(0)
        self.setStyleSheet('QToolButton#SystemMenu {background:transparent;border:0;padding:0;margin:0;}')
        self.setAttribute(Qt.WA_Hover, True)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space, Qt.Key_Select) and not event.isAutoRepeat():self.open(True);return
        QToolButton.keyPressEvent(self, event)

    def menu_(self):
        """The System menu, built once on first use."""
        if self.popup is None:
            from .system_menu_qt import SystemMenu
            self.popup = SystemMenu(self.host, self);self.popup.installEventFilter(self)
        return self.popup

    def open(self, keyboard=False):
        """The System menu opens downward from the upper right (programs_qt.place: its right edge the band's inset from the
        window's right edge, its top on the head band's foot); from the keyboard its first row is under focus."""
        menu = self.menu_();menu.open_menu(keyboard=bool(keyboard));self.update();return menu

    def eventFilter(self, obj, event):
        if obj is self.popup and event.type() in (QEvent.Hide, QEvent.Show):self.update()
        return False

    def paintEvent(self, event):
        QToolButton.paintEvent(self, event)
