"""Persistent right-column Operations view (the right pane's Activity) and the original work controls.

D1-fix (the integrator: "keep Activity quiet"): Activity says what Graphite's own work is doing in one printed line (work_words)
with the script note where its order, niceness and Stop are; the work list itself is the System menu's list (Work list opens
it). The embedded list (self.work) and the queue's explanation (self.queue_hint) are kept, fed the same snapshot, out of sight.

UI-03 (the owner's request): the four host monitors stay in the Ledger Head beside Nice (shell2.TopBar.pulse_holder); the
column has no monitors block any more, and host.operations_monitors names the head's holder so older callers and checks
read the truth. The Master Stop controller's own button stays hidden: the one kill switch is the first row of Nice (and of
this panel's embedded work list), bound to that controller.
"""
from PySide6.QtCore import Qt,QTimer,QEvent
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QScrollArea
from .settings_qt import action,STYLE
from .engineering_kernel import operator
from .explore_qt import selected_record


def words(text=''):
    result=QLabel(text);result.setTextFormat(Qt.PlainText);result.setWordWrap(True);result.setMinimumWidth(0);return result


def work_words(agenda,first=None):
    """Activity's one printed line about Graphite's own work (D1-fix): how many jobs run and how many items wait, counted as
    the System menu's list counts them, and the first item through the queue checks when there is one."""
    agenda=agenda or {};jobs=list(agenda.get('now',[]))+[r for r in agenda.get('next',[]) if r.get('kind')=='job']
    running=sum(1 for r in jobs if r.get('state')=='Running')  # a job not yet started waits with the queue
    queued=len(jobs)-running+sum(1 for r in agenda.get('next',[]) if r.get('kind')!='job' and r.get('state') in ('NEXT','PAUSED'))
    line='WORK · '+(' · '.join(part for part in ((str(running)+' running') if running else '',(str(queued)+' queued') if queued else '') if part) or 'nothing running or queued')
    return line+('\nFirst through queue checks: '+str(first['title']) if first else '')


def caption_px(host,base):
    """Right-column metadata follows reading.ui_pt (V-06): the design size at 14 pt, scaled, never below 10 px."""
    from .shell2 import scale_of
    return max(10,round(base*scale_of(host)))


class OperationsPanel(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.model=None;self.busy=False;self._scale=None
        self.setProperty('paperFunctionalInk',True);self.setStyleSheet(STYLE)
        box=QVBoxLayout(self);box.setContentsMargins(0,0,0,0)
        scroll=self.scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.NoFrame);box.addWidget(scroll)
        page=QWidget();col=QVBoxLayout(page);col.setContentsMargins(10,10,10,10);col.setSpacing(10);scroll.setWidget(page);self.col=col
        self.services=words();self.services.setAccessibleName('Graphite service cycle status');col.addWidget(self.services)
        self.services.setToolTip('The one service sentence (service_lifecycle.SUMMARIES); the queue rows and the menu use the same words.')
        col.addWidget(action('Service details',lambda:host.a_host_service.trigger()),0,Qt.AlignLeft)
        self.slate=words();col.addWidget(self.slate)
        from .shell2 import QuietWords  # the quiet-script rule: an explanation you may skip is the Paper script, a status print
        self.selection=QuietWords(host);col.addWidget(self.selection)
        row=QHBoxLayout();row.addWidget(action('Open record',self.open_record));row.addWidget(action('Explore',self.explore));row.addStretch();col.addLayout(row)
        # D1-fix (the integrator: "keep Activity quiet"): the work list (Stop everything, each row's niceness slider, the
        # queue's order, Background CPU, Open Agenda, Work trail and the sliders' explanation) is the System menu's list now,
        # opened by the symbol at the upper right (D2 rebuilds that menu). Activity says what runs and waits in one printed
        # line, where its order, niceness and Stop are in the script, and Work list opens the System menu's list.
        self.jobs=QuietWords(host);self.jobs.setAccessibleName('Graphite work: running and queued');col.addWidget(self.jobs)
        row=QHBoxLayout();self.work_list=action('Work list',self.open_work_list);row.addWidget(self.work_list);row.addStretch();col.addLayout(row)
        self.work_list.setToolTip('The System menu\'s list: Stop everything, what runs and waits, each row\'s niceness and the queue\'s order')
        # Kept for callers, out of the face: the queue's explanation and the embedded list (still fed the same snapshot).
        self.queue_hint=QuietWords(host);self.queue_hint.explain('Agenda order and process CPU priority have separate effects.');self.queue_hint.setParent(page);self.queue_hint.hide()
        from .desktop_header_qt import NicePopup
        self.work=NicePopup(host,host.shell2.top.nice,embedded=True);self.work.setParent(page);self.work.hide()
        self.work.snapshot_refresh=self.refresh
        row=QHBoxLayout();advanced=action('AI admission',self.toggle_admission);row.addWidget(advanced);row.addStretch();col.addLayout(row)
        self.admission=host.shell2.top.slate_switch
        host.shell2.top.right_holder.layout().removeWidget(self.admission);col.addWidget(self.admission);self.admission.hide()
        self.note=words();col.addWidget(self.note);col.addStretch()
        self.timer=QTimer(self);self.timer.setInterval(2000);self.timer.timeout.connect(self.refresh)

    def event(self,event):
        if event.type()==QEvent.StyleChange:QTimer.singleShot(0,self.restyle)  # the interface size changed: the column follows it now
        return super().event(event)

    def showEvent(self,event):
        super().showEvent(event);self.timer.start();QTimer.singleShot(0,self.refresh)

    def hideEvent(self,event):self.timer.stop();super().hideEvent(event)

    def restyle(self):
        """Sizes that are not the reading text follow the interface size; the Services line keeps room for two lines so a
        longer sentence never shifts the column (V-26)."""
        from .shell2 import scale_of
        s=scale_of(self.host)
        if s==self._scale:return
        self._scale=s
        self.services.setMinimumHeight(2*self.services.fontMetrics().lineSpacing()+2)
        self.work.restyle()

    def refresh(self):
        if self.busy or self.host._closing or self.work.adjusting:return
        self.busy=True
        try:
            self.restyle()
            args={'idle':bool(getattr(self.host,'agenda_runner',None) and self.host.agenda_runner.idle())}
            ident=selected_record(self.host)
            if ident:args['context']=ident
            response=self.host.ledger_bridge.kernel.dispatch('ledger.operations',args,operator())
            if not response['ok']:
                self.services.setText('GRAPHITE SERVICES · status unavailable')
                self.note.setText(response['error']['message']);self.work.queue.setEnabled(False);return
            self.model=response['result'];slate=self.model['slate'];selection=self.model['selection']
            services=self.model['services'];counts=services['counts']
            self.services.setText('GRAPHITE SERVICES · '+services['summary']+
                ('\n'+str(counts['running'])+' running · '+str(counts['queued'])+' queued' if services['phase']=='DRAINING' else ''))
            self.services.setToolTip(services['control_plane'])
            phase={'READY':'Local model ready','MODEL_STOPPED':'Local model stopped','NO_MODEL_SELECTED':'No local model selected'}.get(slate['local_state'],'Local state unavailable')
            # V-05: the held state is said once, on the Services line; the Slate line keeps only Slate's own admission switch.
            gates=['New AI activity off'] if not slate['new_ai_enabled'] else []
            self.slate.setText('GRAPHITE · '+phase+('\n'+' · '.join(gates) if gates else ''))
            if selection:self.selection.setText('CABINET SELECTION\n'+selection['label']+'\n'+selection['role'].replace('_',' '))
            else:self.selection.explain('Select saved work in the cabinet to carry its identity here.')
            self.work.render_data(self.model['agenda'])
            first=self.model['first_queue_checks_passed']
            row=next((r for r in self.model['agenda']['next'] if r.get('id')==first),None)
            # The status in print, its explanation under it in the script (the quiet-script rule).
            if row:self.queue_hint.explain('Runtime, model and grant checks still apply.',lead='First through queue checks: '+row['title'])
            else:self.queue_hint.explain('Waiting reasons appear with each item.',lead='No Agenda item currently passes the queue checks.')
            self.jobs.explain('their order, niceness and Stop are in the System menu',lead=work_words(self.model['agenda'],row))
            self.jobs.setToolTip('Agenda order and process CPU priority have separate effects. '+('Runtime, model and grant checks still apply.' if row else 'Waiting reasons appear with each item in the Work list.'))
            self.note.setText(' '.join(self.model['notices']))
        finally:self.busy=False

    def open_work_list(self):
        """The System menu's list, opened from its symbol at the upper right (the same list, Stop everything first)."""
        self.host.shell2.top.nice.open()

    def context_target(self,widget,point):
        """HATCH DESK D4: what a right-click on Activity finds (workbench/context_menu.py asks here first): the cabinet selection's
        words are its record (the cabinet's own actions, Open, Explore); the timeline's lines are found by the menu itself."""
        if widget is not self.selection or not (self.model and self.model.get('selection')):return None
        from .context_menu import Target
        selection=self.model['selection']
        return Target('cabinet',selection['label'],'record · '+str(selection.get('role','')).replace('_',' '),ident=selection['id'],
                      data=dict(node=selection),surface='activity',owner=self)

    def open_record(self):
        if self.model and self.model['selection']:self.host.cabinet_page.open(self.model['selection']['id'])

    def explore(self):
        from .explore_qt import show
        show(self.host,self.model['selection']['id'] if self.model and self.model['selection'] else None)

    def toggle_admission(self):self.admission.setVisible(self.admission.isHidden())


def install(host):
    """Install the Operations view; retain the old object references.

    The monitors are not moved: they stay in the head immediately left of Nice, and host.operations_monitors is that holder
    (the old column note's words are the pulse's tooltip, desktop_header_qt.MONITORS_NOTE). The Master Stop controller's
    button is not shown in the head: the kill switch inside Nice is bound to the controller (one Stop, not two)."""
    shell=host.shell2;top=shell.top
    host.operations_monitors=top.pulse_holder;top.pulse_holder.show();top.pulse.show()
    panel=OperationsPanel(host);host.operations_panel=panel;host.console_pages.addTab(panel,'Operations')
    # HATCH DESK D1b: the panel is the right pane's Activity; its tab is the shell's operations_button (the middle of
    # Conversation · Activity · Context, pane_qt), checked by Shell2.face_changed.
    host.master_stop_button.hide()  # the controller owns it; its words reach the kill switch through MasterStop.faces
    host.console_pages.setCurrentWidget(panel);shell.face_changed()
    return panel
