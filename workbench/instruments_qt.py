"""Compact five-tab ARC-1 system instruments plus persistent Slate dock (Qt).

Hardware instrumentation is driven exclusively by the verified JSONL host
behavioral trace. The engine is never replaced by a UI animation.
"""
from __future__ import annotations
from .assistant_identity import named
from .text_prompts import writing_prompt

from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QProgressBar,
                               QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
                               QSizePolicy,QComboBox,QToolButton,QStyle)
from . import system_instruments


class _InstrumentRow(QWidget):
    def __init__(self, label):
        super().__init__()
        box = QVBoxLayout(self)
        box.setContentsMargins(5, 5, 5, 7)
        box.setSpacing(3)
        line = QHBoxLayout()
        title = QLabel(label)
        title.setWordWrap(True)
        title.setStyleSheet('font-weight: 600; color: #d4d9de;')
        self.value = QLabel('Not instrumented')
        self.value.setWordWrap(True)
        self.value.setProperty('arcRole','metadata')
        self.value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        line.addWidget(title, 1)
        box.addLayout(line)
        box.addWidget(self.value)
        self.bar = QProgressBar()
        self.bar.setObjectName('instrumentMeter')
        self.bar.setFixedHeight(9)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setVisible(False)  # unavailable is not 0%
        self.bar.setStyleSheet('QProgressBar { border: 1px solid #3b4249; background: #20252a; '
                               'border-radius: 3px; } QProgressBar::chunk { background: #c27845; border-radius: 2px; }')
        box.addWidget(self.bar)
        self.unknown_track = QLabel('—  NOT INSTRUMENTED  —')
        self.unknown_track.setAlignment(Qt.AlignCenter)
        self.unknown_track.setStyleSheet('color: #b5bec8; '
                                         'background: #242930; border: 1px solid #384048; '
                                         'border-radius: 3px;')
        box.addWidget(self.unknown_track)

    def set_metric(self, item):
        self.arc_metric=item
        self.value.setText(item['value'])
        self.setToolTip(item['detail'] + ' · ' + item['evidence'])
        has_bar = item['percent'] is not None
        self.bar.setVisible(has_bar)
        self.unknown_track.setVisible(not has_bar and item['value']=='Not instrumented')
        self.unknown_track.setToolTip(item['detail'])
        if has_bar:
            self.bar.setValue(item['percent'])
            self.bar.setToolTip(item['detail'])


class InstrumentTabs(QWidget):
    """Persistent source-labelled simulation meters; no separate simulator window."""
    def __init__(self, controller, open_trace):
        super().__init__()
        self.controller = controller
        self.devices = {}
        self.missing_controls={}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(5, 6, 5, 3)
        outer.setSpacing(5)
        heading = QHBoxLayout()
        title = QLabel('Recorded instruments')
        title.setWordWrap(True)
        title.setStyleSheet('font-weight: 700; color: #e5e7e9;')
        heading.addWidget(title, 1)
        self.state = QLabel('IDLE')
        self.state.setStyleSheet('color: #d49a73;')
        heading.addWidget(self.state)
        outer.addLayout(heading)
        self.context = QLabel('SELECTED · ARC-1 CONSOLE')
        self.context.setProperty('arcRole','metadata')
        self.context.setWordWrap(True)
        self.context.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(self.context)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setObjectName('InstrumentTabs')
        self.tabs.setStyleSheet('QTabBar::tab { padding: 5px 6px; }')
        for tab, definitions in system_instruments.ROWS.items():
            page = QWidget()
            page.setObjectName("InstrumentPage")
            page.setStyleSheet("QWidget#InstrumentPage { background: #14171b; }")
            v = QVBoxLayout(page)
            v.setContentsMargins(2, 5, 2, 2)
            v.setSpacing(0)
            rows = {}
            missing=QToolButton();missing.setCheckable(True)
            missing.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            missing.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
            missing.setToolTip('Expand unavailable instruments; missing measurements are never zero')
            missing.toggled.connect(self._refresh_missing)
            v.addWidget(missing);self.missing_controls[tab]=missing
            for key, name in definitions:
                widget = _InstrumentRow(name)
                v.addWidget(widget)
                rows[key] = widget
            v.addStretch(1)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { background: #14171b; border: 0; }")
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setWidget(page)
            index=self.tabs.addTab(scroll, {'Compute':'Load','Links':'Links','Memory':'RAM','Timing':'Time','Events':'Events'}[tab])
            self.tabs.setTabToolTip(index,tab+' · recorded instruments')
            self.devices[tab] = rows
        outer.addWidget(self.tabs, 1)
        self.provenance = QLabel('NO TRACE · Hardware measurements unavailable')
        self.provenance.setWordWrap(True)
        self.provenance.setProperty('arcRole','metadata')
        self.provenance.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(self.provenance)
        controls = QHBoxLayout()
        self.buttons = {}
        for label, callback in [('Run', controller.start), ('Pause', controller.pause),
                                ('Step', controller.step), ('Reset', controller.reset),
                                ('Trace…', open_trace)]:
            b = QToolButton()
            b.setText(label)
            b.setAccessibleName(label+' recorded host trace')
            b.setIcon(self.style().standardIcon({'Run':QStyle.SP_MediaPlay,
                'Pause':QStyle.SP_MediaPause,'Step':QStyle.SP_MediaSkipForward,
                'Reset':QStyle.SP_BrowserReload,'Trace…':QStyle.SP_FileDialogDetailedView}[label]))
            b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon if label=='Trace…' else Qt.ToolButtonIconOnly)
            b.setToolTip(('Playback of recorded host trace' if label != 'Trace…' else
                          'Open detailed host trace in center workspace'))
            b.clicked.connect(callback)
            controls.addWidget(b)
            self.buttons[label] = b
        outer.addLayout(controls)
        self.snapshot()

    def _refresh_missing(self, *_):
        for tab,rows in self.devices.items():
            control=self.missing_controls[tab]
            missing=[widget for widget in rows.values()
                     if getattr(widget,'arc_metric',{}).get('value','Not instrumented')=='Not instrumented']
            control.setVisible(bool(missing))
            control.setText('Not instrumented (%s)'%len(missing))
            control.setArrowType(Qt.DownArrow if control.isChecked() else Qt.RightArrow)
            for widget in rows.values():
                widget.setVisible(widget not in missing or control.isChecked())

    def set_hardware_context(self, name):
        self.context.setText('SELECTED · ' + name.upper())

    def native_snapshot(self, state):
        for widget in getattr(self,'virtual_rows',{}).values():widget.hide()
        """Host measurements are separate from every physical processor row."""
        self.context.setText('SELECTED · STRUTHIO NATIVE HOST')
        self.state.setText('C HOST')
        self.provenance.setText('HOST-MEASURED · tick %s · C step %.3f µs CPU · state %s bytes · hardware Not instrumented' % (
            state['tick'],state['step_cpu_us'],state['state_bytes']))
        for rows in self.devices.values():
            for widget in rows.values():widget.set_metric({'value':'Not instrumented','percent':None,'detail':'Native host metrics do not measure physical ARC-1 processors','evidence':'NOT_INSTRUMENTED'})
        if not hasattr(self,'native_rows'):
            self.native_rows={}
            for tab,label in [('Compute','Host C step CPU time'),('Memory','Host C state size'),('Timing','Deterministic simulation tick'),('Events','Host C events')]:
                index=self.tabs.indexOf(self.tabs.widget(list(self.devices).index(tab)))
                page=self.tabs.widget(index).widget();widget=_InstrumentRow(label);page.layout().insertWidget(0,widget);self.native_rows[tab]=widget
        values={'Compute':'%.3f µs'%state['step_cpu_us'],'Memory':'%s bytes'%state['state_bytes'],
                'Timing':'%s / 60 Hz'%state['tick'],'Events':str(state['events'])}
        for tab,value in values.items():
            self.native_rows[tab].show()
            self.native_rows[tab].set_metric({'value':value,'percent':None,'detail':'Reported by the compiled native C host','evidence':'HOST_MEASURED'})
        self._refresh_missing()

    def arcos_snapshot(self, state):
        for widget in getattr(self,'virtual_rows',{}).values():widget.hide()
        self.context.setText('SELECTED · ARC-OS NATIVE HOST')
        self.state.setText('C HOST')
        self.provenance.setText('HOST-MEASURED · tick %s · state %s + %s bytes · %s tone events · CPU time Not instrumented' %
            (state['tick'],state['host_state_bytes'],state['game_state_bytes'],state['audio_events']))
        for widget in getattr(self,'native_rows',{}).values():widget.hide()
        for rows in self.devices.values():
            for widget in rows.values():
                widget.set_metric({'value':'Not instrumented','percent':None,'detail':'ARC-OS host does not measure physical processors','evidence':'NOT_INSTRUMENTED'})
        self._refresh_missing()

    def virtual_snapshot(self,state):
        self.context.setText('SELECTED · FUNCTIONAL VIRTUAL CONSOLE')
        self.state.setText('HOST + RTL MODEL')
        frame=state['frame'];m=state['metrics']
        self.provenance.setText('HOST_SIM · source '+state['revision'][:12]+' · logical tick '+str(frame['tick'])+' · no board timing or physical telemetry')
        for widget in getattr(self,'native_rows',{}).values():widget.hide()
        for rows in self.devices.values():
            for widget in rows.values():widget.set_metric({'value':'Not instrumented','percent':None,'detail':'Functional host execution does not measure physical processors','evidence':'NOT_INSTRUMENTED'})
        if not hasattr(self,'virtual_rows'):
            self.virtual_rows={}
            for tab,label in [('Compute','Executed firmware model stages'),('Links','Modeled hub and configuration traffic'),('Memory','Native host state'),('Timing','Logical game clock'),('Events','Current console state')]:
                page=self.tabs.widget(list(self.devices).index(tab)).widget();widget=_InstrumentRow(label);page.layout().insertWidget(0,widget);self.virtual_rows[tab]=widget
        values={'Compute':str(m.get('boot_steps',0))+' stage receipts · '+str(m.get('rtl_transactions',0))+' RTL transaction · epoch '+str(m.get('federation_generation',0)),
                'Links':str(m.get('usb_control_calls',0))+' USB control / '+str(m.get('usb_bulk_transfers',0))+' bulk transfers · '+str(m.get('usb_block_reads',0))+' block reads\n'+str(m.get('hub_ep0_requests',0))+' hub EP0 requests · '+str(m.get('graphics_packets',0))+' graphics-link packets / '+str(m.get('graphics_frames',0))+' frames\n'+str(m.get('fpga12_spi_bytes',0))+' / '+str(m.get('fpga45_spi_bytes',0))+' FPGA configuration SPI bytes · modeled',
                'Memory':str(frame['host_state_bytes'])+' host + '+str(frame['game_state_bytes'])+' game bytes',
                'Timing':str(frame['tick'])+' / 60 logical ticks · board cycles unavailable',
                'Events':frame['screen']+' · '+str(m.get('logical_controller_changes',0))+' logical controller changes'}
        for tab,value in values.items():
            self.virtual_rows[tab].show();self.virtual_rows[tab].set_metric({'value':value,'percent':None,'detail':'C protocol/model receipts plus an actual 12F RTL slice; no physical bus traffic or board timing','evidence':'HOST_SIM'})
        for button in self.buttons.values():button.setEnabled(False)
        self._refresh_missing()

    def snapshot(self, row=None):
        for widget in getattr(self,'virtual_rows',{}).values():widget.hide()
        for widget in getattr(self,'native_rows',{}).values():widget.hide()
        model = system_instruments.snapshot(row, self.controller.trace_path, self.controller.trace_sha256)
        for tab, items in model['tabs'].items():
            for item in items:
                self.devices[tab][item['id']].set_metric(item)
        if model['frame'] is not None:
            count = len(self.controller.rows)
            assumption = isinstance(row, dict) and isinstance(row.get('workload'), dict) and row['workload'].get('evidence') == 'SCENARIO_ASSUMPTION'
            label = 'SCENARIO_ASSUMPTION · modeled budgets, NOT hardware telemetry' if assumption else 'HOST_SIM_BEHAVIORAL · NOT live hardware'
            self.provenance.setText('%s · frame %s · %s/%s' % (
                                    label, model['frame'], self.controller.cursor + 1, count))
        else:
            self.provenance.setText('NO VERIFIED HOST TRACE · no board detected')
        self.update_state()
        self._refresh_missing()

    def update_state(self, state=None):
        if state is None:
            state = self.controller.playback_state()
        self.state.setText(state.upper())
        self.buttons['Run'].setEnabled(bool(self.controller.rows) and state not in ('Running', 'Completed'))
        self.buttons['Pause'].setEnabled(state == 'Running')
        self.buttons['Step'].setEnabled(bool(self.controller.rows))
        self.buttons['Reset'].setEnabled(bool(self.controller.rows))


class ClipDock(QWidget):
    """Compact persistent entry point; existing ClipOverlay owns chat/provider state."""
    def __init__(self, submit, expand):
        super().__init__()
        self.submit = submit
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(5)
        title_row = QHBoxLayout()
        self.avatar_slot = QWidget()
        self.avatar_slot.setFixedSize(112, 134)
        title_row.addWidget(self.avatar_slot)
        summary=QVBoxLayout()
        self.context_id='root';self.active_job=None;self.latest_job=None;self.busy=False
        self.context=QLabel('ARC-1 Console');self.context.setWordWrap(True)
        self.context.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        self.context.setTextInteractionFlags(Qt.TextSelectableByMouse)
        summary.addWidget(self.context)
        self.status=QLabel('No active job');self.status.setWordWrap(True)
        self.status.setProperty('arcRole','metadata')
        self.status.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        summary.addWidget(self.status)
        title_row.addLayout(summary,1)
        layout.addLayout(title_row)
        entry=QHBoxLayout()
        conversation=QPushButton(named('Ask Stacy…'));conversation.clicked.connect(expand)
        conversation.setAccessibleName(named('Open the conversation with Stacy'));entry.addWidget(conversation,1)
        self.advanced=QToolButton();self.advanced.setText('More');self.advanced.setCheckable(True)
        self.advanced.setToolTip('Expand existing Graphite modes, job controls and message input')
        entry.addWidget(self.advanced);layout.addLayout(entry)
        details=QWidget();details.setObjectName('ClipDetails')
        detail_layout=QVBoxLayout(details);detail_layout.setContentsMargins(0,0,0,0)
        details.hide();layout.addWidget(details)
        self.advanced.toggled.connect(details.setVisible)
        self.advanced_widgets=[details]
        layout=detail_layout
        self.primary=QPushButton('Plan next check');self.primary.clicked.connect(self.next_action);layout.addWidget(self.primary)
        self.mode=QComboBox();self.mode.addItems(['Tutor · conversation','Engineer · candidate review','Autonomous · bounded task'])
        self.mode.currentIndexChanged.connect(self.select_mode);layout.addWidget(self.mode)
        self.progress = QProgressBar()
        self.progress.setFixedHeight(7)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.hide()  # hide, rather than invent fractional task completion
        layout.addWidget(self.progress)
        row = QHBoxLayout()
        self.input = QLineEdit()
        writing_prompt(self.input, named('Ask Stacy about this project…'))
        self.input.setAccessibleName('Message to Graphite')
        self.input.returnPressed.connect(self.send)
        row.addWidget(self.input, 1)
        button = QPushButton('Send')
        self.send_button = button
        button.clicked.connect(self.send)
        row.addWidget(button)
        layout.addLayout(row)
        more = QPushButton('Open conversation')
        more.clicked.connect(lambda: self.window().show_clip_workspace())
        layout.addWidget(more)
        self.job_controls = QPushButton('Jobs, scope & candidate review →')
        self.job_controls.clicked.connect(lambda: self.window().show_engineering())
        layout.addWidget(self.job_controls)
        controls = QHBoxLayout()
        self.control_buttons=[]
        for label, action in (('Pause', 'pause'), ('Stop', 'cancel')):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, op=action: self.control_job(op))
            controls.addWidget(button)
            self.control_buttons.append(button);button.setEnabled(False)
        layout.addLayout(controls)
        note = QLabel('Local plans · explicit cloud consent in conversation settings')
        note.setProperty('arcRole','metadata')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Maximum)
        self.job_timer=QTimer(self);self.job_timer.setInterval(1500);self.job_timer.timeout.connect(self.refresh_task);self.job_timer.start()

    def set_context(self,title,identity):
        self.context_id=identity;self.context.setText(title)
        self.context.setToolTip('Selection guides the next plan. An approved job retains its own source binding.')

    def next_action(self):
        tab=self.window().show_engineering()
        if self.active_job:
            tab.selected_job=self.active_job['id'];return
        template='arcos-service' if self.context_id=='arcos' else 'struthio-parity' if self.context_id=='arcade' else 'hardware-coverage'
        index=tab.guide_template.findData(template)
        if index>=0:tab.guide_template.setCurrentIndex(index)
        tab.show_guidance('tasks.plan');tab.pages.setCurrentWidget(tab.guide_result.parentWidget())

    def refresh_task(self):
        if getattr(self.window(),'_closing',False):return
        if not hasattr(self.window(),'root') or self.busy:return
        from .engine import engineering
        jobs=engineering(self.window().root).listing('jobs')
        active=[j for j in jobs if j['state'] in ('Queued','Running','Paused','Waiting for Approval','Interrupted','Waiting for Agent','Waiting for Execution Approval')]
        self.active_job=active[0] if active else None
        self.latest_job=jobs[0] if jobs else None  # newest first; Stacy's companion reads real states only
        if self.active_job:
            j=self.active_job;self.status.setText(j['state']+' · '+j['tool']+'\n'+j['id'][:12]+' · '+j.get('current_operation','')+'\nBound revision '+j.get('revision','unknown')[:12])
            self.primary.setText('Open current job')
        else:
            self.status.setText('No active job');self.primary.setText('Plan next check')
        for b in self.control_buttons:b.setEnabled(bool(self.active_job))

    def send(self):
        message = self.input.text().strip()
        if message:
            self.input.clear()
            self.submit(message)

    def select_mode(self,index):
        if index:
            tab=self.window().show_engineering()
            if index==2:tab.pages.setCurrentWidget(tab.clip_page)

    def control_job(self, action):
        if not self.active_job:return
        from .engine import engineering
        from .engineering_kernel import operator
        r=engineering(self.window().root).dispatch('jobs.'+action,{'id':self.active_job['id']},operator())
        if not r['ok']:
            from .ux_polish import readable_error
            self.status.setText(readable_error(r['error']['message'],self.window().root))
        else:self.refresh_task()

    def set_busy(self, busy):
        self.busy=busy
        self.status.setText('Waiting for Gemini response…' if busy else 'Idle · Graphite ready (Gemini setup may be required)')
        self.progress.setVisible(bool(busy))
        self.input.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        if busy:
            self.progress.setRange(0, 0)  # indeterminate; actual progress not provided by API
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
