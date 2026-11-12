"""Readable work trails and measured host headroom in the existing workspace."""
import json
import time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QLayout, QLabel, QPushButton, QComboBox, QTreeWidget, QTreeWidgetItem, QCheckBox, QPlainTextEdit, QSizePolicy, QHeaderView
from sdk.cli.arc1cli.object_context import principal_key
from . import boss_theme as ink
from .register_tabs import ServiceTab


def readout(text='', name=''):
    label = QLabel(text)
    label.setObjectName(name)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    policy = QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    policy.setHeightForWidth(True)
    label.setSizePolicy(policy)
    return label


def memory_amount(size):
    if size is None:
        return 'Unavailable'
    if size >= 1024 ** 3:
        return f'{size / 1024 ** 3:.2f} GiB'
    return f'{size / 1024 ** 2:.0f} MiB'


class TrafficPanel(QFrame):
    """Separate measured headroom, configured reserve, and owned job waits."""
    def __init__(self):
        super().__init__()
        self.setObjectName('TrafficCop')
        self.setAccessibleName('Shared-memory traffic cop')
        self.setStyleSheet('''
            QFrame#TrafficCop {background:%(PANEL)s; border:1px solid %(LINE)s; border-top-color:%(AMBER_EDGE)s;}
            QFrame#CopMetric {background:%(TERMINAL_GROUND)s; border:1px solid %(LINE)s;}
            QLabel#CopTitle, QLabel#CopState, QLabel#CopMetricName, QLabel#CopMetricValue {font-family:"IBM Plex Mono";}
            QLabel#CopTitle {color:%(AMBER_TEXT)s; font-weight:600;}
            QLabel#CopMetricName, QLabel#CopCaption {color:%(QUIET)s;}
            QLabel#CopMetricValue {color:%(TEXT)s; font-weight:600;}
        ''' % vars(ink))
        box = QVBoxLayout(self)
        box.setContentsMargins(10, 8, 10, 9)
        box.setSpacing(7)
        head = QHBoxLayout()
        head.addWidget(QLabel('[ TRAFFIC COP ]', objectName='CopTitle'))
        self.state = readout(name='CopState')
        self.state.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        head.addWidget(self.state, 1)
        box.addLayout(head)
        self.metrics = {}
        grid = QGridLayout()
        grid.setSpacing(5)
        for i, name in enumerate(('Work headroom', 'Host available', 'Host CPU',
                                  'RAM reserve', 'Future work', 'CPU slots')):
            card = QFrame(objectName='CopMetric')
            body = QVBoxLayout(card)
            body.setContentsMargins(7, 4, 7, 4)
            body.setSpacing(2)
            body.addWidget(readout(name, 'CopMetricName'))
            body.addStretch(1)
            label = readout(name='CopMetricValue')
            label.setAccessibleName(name)
            body.addWidget(label)
            self.metrics[name] = label
            grid.addWidget(card, i // 3, i % 3)
            grid.setColumnStretch(i % 3, 1)
        box.addLayout(grid)
        self.caption = readout(name='CopCaption')
        box.addWidget(self.caption)
        self.waits = readout(name='CopCaption')
        self.waits.setAccessibleName('Owned job admission and forecast')
        box.addWidget(self.waits)
        self.unavailable('Awaiting resource readback')

    def set_state(self, text, colour):
        self.state.setText(text)
        self.state.setStyleSheet('color:%s; font-weight:600;' % colour)

    def unavailable(self, message):
        self.set_state('READBACK UNAVAILABLE', ink.QUIET)
        self.caption.setText(message)
        self.setToolTip('')
        self.waits.clear()
        self.waits.hide()
        for label in self.metrics.values():
            label.setText('Unavailable')
            label.setToolTip('')

    def update_resources(self, value):
        traffic = value.get('traffic') or {}
        cpu, memory = value['cpu'], value['memory']
        available = memory['available_bytes'] if memory['state'] == 'MEASURED' else None
        percent = cpu['percent'] if cpu['status'] == 'MEASURED' else None
        self.metrics['Host CPU'].setText(f'{percent:g}%' if percent is not None else 'Unavailable')
        self.metrics['Host CPU'].setToolTip(' · '.join(filter(None, (cpu['source'], cpu['scope'], cpu.get('reason')))))
        self.metrics['Host available'].setToolTip(memory['scope'])
        for name, amount in (('Host available', available),
                             ('Work headroom', traffic.get('headroom_bytes') if available is not None else None),
                             ('RAM reserve', traffic.get('reserve_bytes')),
                             ('Future work', traffic.get('reserved_future_bytes'))):
            self.metrics[name].setText(memory_amount(amount))
        slots = traffic.get('policy', {}).get('compute_slots')
        self.metrics['CPU slots'].setText(str(slots) if slots is not None else 'Unavailable')
        self.setToolTip('\n'.join(filter(None, (traffic.get('scope'), traffic.get('limits')))))
        state = traffic.get('state')
        if value['gate']['held']:
            self.set_state('WORK HELD', ink.AMBER_TEXT)
            self.caption.setText('Resume work to reopen admission.')
        elif available is None or state is None:
            self.set_state('READBACK UNAVAILABLE', ink.QUIET)
            self.caption.setText('Admission is waiting for a memory observation.' if available is None else 'Awaiting the traffic policy readback.')
        else:
            self.set_state(state.replace('_', ' '), ink.READY if state == 'ACCEPTING' else ink.AMBER_TEXT)
            self.caption.setText('One model turn at a time. Foreground gets the next available turn.')
        lines = []
        for row in traffic.get('jobs', [])[:8]:
            request, wait = row.get('request') or {}, row.get('waiting') or {}
            lines.append(row['tool'] + ' · ' + request.get('priority', 'normal') + ' · ' + (wait.get('reason') or row['state'].lower()))
            forecast = wait.get('memory_forecast') or {}
            if forecast.get('outcome') == 'defer':
                lines.append(f"In {forecast['horizon_seconds']} s · {memory_amount(forecast['projected_headroom_bytes'])} projected · "
                             f"{memory_amount(wait['requested_bytes'])} requested")
        self.waits.setText('\n'.join(lines))
        self.waits.setVisible(bool(lines))


class WorkTrailTab(ServiceTab):
    def __init__(self, bridge):
        super().__init__(bridge.host)
        self.bridge = bridge
        self.actor = principal_key(self.principal)
        self.busy = False
        self.selected_signature = None
        self.rows = {}
        self.last_detail = None
        self.latest_priority = "normal"
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        box = QVBoxLayout(body)
        box.setSizeConstraint(QLayout.SetMinimumSize)
        scroll.setWidget(body)
        self.outer.addWidget(scroll)
        self.traffic = TrafficPanel()
        box.addWidget(self.traffic)
        self.priority = QComboBox()
        self.priority.addItems(["normal", "background"])
        self.priority.setAccessibleName("Existing work CPU priority policy")
        self.priority.setEnabled(False)
        self.refresh_button = QPushButton("Refresh")
        self.resume_button = QPushButton("Resume work")
        self.resume_button.setEnabled(False)
        self.job_button = QPushButton("Inspect job")
        self.job_button.setEnabled(False)
        row = QHBoxLayout()
        for control in (self.refresh_button, self.resume_button, self.job_button, self.priority):
            row.addWidget(control)
        box.addLayout(row)
        work = QLabel('[ RECENT WORK ]')
        work.setProperty('arcRole2', 'section')
        box.addWidget(work)
        self.history = QLabel()
        self.history.setWordWrap(True)
        self.history.setTextFormat(Qt.PlainText)
        box.addWidget(self.history)
        self.intents = QComboBox()
        self.intents.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.intents.setAccessibleName("Recent owner work intents")
        box.addWidget(self.intents)
        self.stages = QTreeWidget()
        self.stages.setHeaderLabels(["Stage", "State", "Observed"])
        self.stages.setRootIsDecorated(False)
        self.stages.setColumnWidth(0, 140)
        self.stages.setColumnWidth(1, 200)
        self.stages.setWordWrap(True)
        self.stages.setMinimumHeight(210)
        self.stages.setAccessibleName("Intent scope work artifacts and outcome")
        box.addWidget(self.stages)
        self.artifacts = QTreeWidget()
        self.artifacts.setHeaderLabels(["Registered artifact", "Byte check"])
        self.artifacts.setRootIsDecorated(False)
        self.artifacts.header().setStretchLastSection(False)
        self.artifacts.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.artifacts.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.artifacts.setMinimumHeight(110)
        self.artifacts.setAccessibleName("Selected work artifact integrity observations")
        box.addWidget(self.artifacts)
        self.limits = QLabel()
        self.limits.setWordWrap(True)
        self.limits.setTextFormat(Qt.PlainText)
        self.limits.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        box.addWidget(self.limits)
        row = QHBoxLayout()
        study = QPushButton("Study limits")
        brain = QPushButton("Brain limits")
        row.addWidget(study)
        row.addWidget(brain)
        box.addLayout(row)
        self.expand = QCheckBox("Technical detail")
        box.addWidget(self.expand)
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMinimumHeight(150)
        self.detail.hide()
        self.expand.toggled.connect(self.detail.setVisible)
        box.addWidget(self.detail)
        self.status.setTextFormat(Qt.PlainText)
        box.addWidget(self.status)
        self.refresh_button.clicked.connect(lambda: self.refresh(True))
        self.resume_button.clicked.connect(self.resume_work)
        self.job_button.clicked.connect(self.open_job)
        self.intents.activated.connect(lambda: self.select(True))
        self.priority.activated.connect(self.set_priority)
        study.clicked.connect(self.open_study)
        brain.clicked.connect(bridge.show_brain)
        self.timer = QTimer(self)
        self.timer.setInterval(1800)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        QTimer.singleShot(0, self.refresh)

    def title(self):
        return "Work trail"

    def wipe(self):
        self.selected_signature = None
        self.rows = {}
        self.last_detail = None
        self.intents.clear()
        self.stages.clear()
        self.artifacts.clear()
        self.detail.clear()
        self.job_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.history.clear()
        self.limits.clear()
        self.traffic.unavailable('Awaiting resource readback')
        self.priority.setEnabled(False)

    def checked(self, operation, args, done, failed=None):
        key = principal_key(self.principal)
        def receive(value):
            if key != principal_key(self.principal):
                self.wipe()
                self.busy = False
                return
            done(value)
        epoch = getattr(self.host, '_operation_epoch', 0)
        worker = self.call(operation, args, receive, failed)
        if worker is not None:
            # Stop epochs suppress stale replies; release polling's local latch.
            worker.finished.connect(lambda: self.finished() if epoch != getattr(self.host, '_operation_epoch', 0) else None)
        else:
            self.finished()
        return worker

    def refresh(self, force=False):
        if self.host._closing or (not force and not self.isVisible()) or self.busy:
            return
        key = principal_key(self.principal)
        if key != self.actor:
            self.wipe()
            self.actor = key
        self.busy = True
        def listed(value):
            previous = self.intents.currentData()
            self.intents.blockSignals(True)
            self.intents.clear()
            self.rows = {r["id"]: r for r in value["intents"]}
            for row in value["intents"]:
                self.intents.addItem(row["label"], row["id"])
            index = self.intents.findData(previous)
            if index >= 0:
                self.intents.setCurrentIndex(index)
            self.intents.blockSignals(False)
            counts = [('seen', 'recorded'), ('pruned', 'older trails trimmed'), ('dropped', 'dropped'),
                      ('recording_gaps_this_process', 'gaps this process'), ('retained_gap_markers', 'retained gap markers')]
            summary = [f'{value[key]} {label}' for key, label in counts if key == 'seen' or value[key]]
            if value['journal_gap']:
                summary.append('Journal gap')
            self.history.setText(' · '.join(summary))
            self.select(force)
            self.checked("ledger.resources", {}, self.resources, self.resources_failed)
        self.checked("ledger.trail.list", {"limit": 20}, listed, self.resources_failed)

    def finished(self):
        self.busy = False

    def resources(self, value):
        self.traffic.update_resources(value)
        held = value["gate"]["held"]
        self.resume_button.setEnabled(held and "approve" in self.principal.scopes)
        self.priority.blockSignals(True)
        self.priority.setCurrentText(value["priority"])
        self.priority.blockSignals(False)
        self.priority.setEnabled("execute" in self.principal.scopes and self.principal.mode != 'Tutor')
        self.latest_priority = value["priority"]
        limits = value["study_limits_for_new_sessions"]
        self.limits.setText("Study defaults for new sessions: " + str(limits["wall_seconds"]) + " s wall · " + str(limits["cpu_seconds"]) + " s CPU · " + str(limits["max_rss_mb"]) + " MiB RSS. Idle " + ("enabled" if value["study_idle_enabled"] else "off") + ".\nAdmission uses measured host availability and advisory owned-worker commitments. Existing hard tool limits remain authoritative.")
        self.finished()

    def resources_failed(self, _error):
        self.traffic.unavailable('Refresh to try the resource read again.')
        self.priority.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.finished()

    def select(self, force=False):
        ident = self.intents.currentData()
        row = self.rows.get(ident)
        if not row:
            self.stages.clear()
            self.artifacts.clear()
            self.detail.clear()
            self.last_detail = None
            self.selected_signature = None
            self.job_button.setEnabled(False)
            self.status.setText("No recorded intents yet. Passive read polling is omitted.")
            return
        signature = json.dumps(row, sort_keys=True)
        if signature == self.selected_signature and not force:
            return
        self.selected_signature = signature
        self.stages.clear()
        self.artifacts.clear()
        self.detail.clear()
        self.last_detail = None
        self.job_button.setEnabled(False)
        self.checked("ledger.trail.inspect", {"id": ident}, lambda value: self.loaded(ident, value), lambda e: setattr(self, 'selected_signature', None))

    def loaded(self, ident, value):
        if self.intents.currentData() != ident:
            return
        self.stages.clear()
        self.artifacts.clear()
        self.last_detail = value
        labels = {'PROCESS_SUCCEEDED': 'Process exited 0', 'PROCESS_FAILED': 'Process failed',
                  'CHECKS_RECORDED': 'Observations', 'BYTES_MATCH': 'Bytes match',
                  'CHANGED': 'Bytes changed', 'NOT_CHECKED_BUDGET': 'Budget exceeded'}
        def readable(state):
            return labels.get(state, state.replace('_', ' ').capitalize())
        for stage in value["stages"]:
            item = QTreeWidgetItem([stage['name'], readable(stage['state']), stage['detail']])
            for col, text in enumerate((stage['name'], stage['state'], stage['detail'])):item.setToolTip(col,text)
            self.stages.addTopLevelItem(item)
        for artifact in value["artifacts"]:
            item = QTreeWidgetItem([artifact['path'], readable(artifact['state'])])
            item.setToolTip(0,artifact['path']);item.setToolTip(1,artifact['state'])
            self.artifacts.addTopLevelItem(item)
        self.job_button.setEnabled(bool(value["jobs"]))
        self.detail.setPlainText(json.dumps(value, ensure_ascii=False, indent=2))
        self.status.setText("Artifact bytes observed " + time.strftime('%H:%M:%S', time.localtime(value['observed_at'])) + ". Refresh checks again. Acceptance remains separate.")

    def set_priority(self):
        self.checked("ledger.settings.set", {"key": "operations.priority", "value": self.priority.currentText(),
                    "expected": self.latest_priority}, lambda value: self.refresh(True))

    def resume_work(self):
        self.checked("ledger.work.resume", {}, lambda value: self.refresh(True))

    def open_job(self):
        if self.last_detail and self.last_detail["jobs"]:
            self.host.select_object({"kind": "job", "target": self.last_detail["jobs"][0]["job_id"]}, self.principal, self)
            self.host.show_object_glass()

    def open_study(self):
        tab = self.bridge.show_memory()
        tab.pages.setCurrentWidget(tab.study_page)

