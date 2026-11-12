"""Desktop driver for the durable Graphite service cycles behind the System menu's Graphite services On / Off / Restart (HATCH DESK
D2; the cycle's key stays Reboot, the word shown is Restart: it restarts Graphite's own services, never the computer)."""
import re,sqlite3,sys,traceback
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QMessageBox

READ_ERRORS=(ValueError,OSError,sqlite3.Error,KeyError,TypeError)
SHOWN={'On':'On','Off':'Off','Reboot':'Restart'}  # the words the System menu shows for the cycles' keys


class LedgerLifecycle(QObject):
    """The Graphite services' On, Off and Restart (key Reboot), with durable cycles and responsive draining."""
    changed=Signal(object)
    completed=Signal(object)

    def __init__(self,host):
        super().__init__(host);self.host=host;self.receipt=None;self.pending=None;self.paused=[];self.model_before=None;self.busy=False
        self.worker=None;self.last_error=None
        from .service_lifecycle import unavailable
        self.state=unavailable('Graphite service state not read yet')
        self.completed.connect(self.finished)
        self.timer=QTimer(self,interval=1000);self.timer.timeout.connect(self.drain);self.timer.start()

    @property
    def kernel(self):return self.host.ledger_bridge.kernel

    @staticmethod
    def plain(error):
        message=str(error)
        if message.startswith(('SERVICE_','WORK_')) and ': ' in message:message=message.split(': ',1)[1]
        return message

    def refresh(self):
        if not hasattr(self.host,'ledger_bridge') or self.host._closing:return
        from .service_lifecycle import snapshot,unavailable
        try:self.state=snapshot(self.kernel);self.last_error=None
        except READ_ERRORS as exc:
            self.state=unavailable(exc)
            # Say it once on the transition; the 1 s timer must not overwrite later status messages.
            if str(exc)!=self.last_error:self.host.statusBar().showMessage(str(exc),6000)
            self.last_error=str(exc)
        self.changed.emit(self.state);self.resume_paused()

    def resume_timers(self):
        for timer in self.paused:timer.start()
        self.paused.clear()

    def resume_paused(self):
        """Paused Agenda and Study timers return once no cycle is pending and admission is open again
        (Off followed by Settings and Resume); their own gates refuse while services are off."""
        if not self.paused or self.pending or self.busy:return
        if self.state.get('phase')=='UNAVAILABLE' or not self.state.get('admission_enabled') or self.state.get('work_held'):return
        self.resume_timers()

    def request(self,action):
        if self.pending or self.busy:
            self.host.statusBar().showMessage('Graphite services are finishing the current cycle. Stop remains available.');return
        details={
            'On':'Enable Graphite services and release the owner work hold? No cancelled job is replayed. Models and phone access keep their existing controls.',
            'Off':'Save open work, cancel queued jobs and hold new work? Running jobs and provider replies finish before owned model, console, tool and phone services close. The desktop stays open.',
            'Reboot':'Save open work, cancel queued jobs and let running work finish, then restart Graphite services here? A previously running model is requested again. Phone access stays off. The computer is not restarted.'}
        if action not in details:raise ValueError('Unknown menu action')
        if QMessageBox.question(self.host,'Graphite services · '+SHOWN.get(action,action),details[action],
                QMessageBox.Yes|QMessageBox.Cancel,QMessageBox.Cancel)!=QMessageBox.Yes:return
        from .engineering_kernel import operator
        from . import service_lifecycle as services,local_brain
        self.receipt=None
        try:
            if action=='On':self.start();return
            if not self.host.save_all():
                self.host.statusBar().showMessage(action+' not started · save was cancelled or failed',6000);return
            self.host.save_session()
            brain=local_brain.status(self.kernel)
            self.model_before=brain.get('selection') if brain['state']=='READY' else None
            self.receipt=services.begin(self.kernel,action,operator(),self.host.desktop_lease.stem)
            self.pending=action
            for obj in (getattr(self.host,'agenda_runner',None),getattr(self.host,'study_idle',None)):
                timer=getattr(obj,'timer',None)
                if timer is not None and timer.isActive():self.paused.append(timer);timer.stop()
            self.refresh();self.drain()
        except Exception as exc:
            # Without a receipt nothing was recorded (begin() and start() roll back whole); say so instead of "cycle incomplete".
            if self.receipt is None:self.not_started(action,exc)
            else:self.failed(exc)

    def not_started(self,action,error):
        traceback.print_exc();self.model_before=None;self.refresh()
        QMessageBox.warning(self.host,'Graphite services · '+SHOWN.get(action,action)+' not started',self.plain(error)+
            '\nNo service cycle was recorded; admission and running work are unchanged.\nInspect Operations and Work trail, then choose again.')

    def background(self,kind,callback):
        import threading
        self.busy=True
        def run():
            try:result=dict(kind=kind,result=callback(),ok=True)
            except Exception as exc:traceback.print_exc();result=dict(kind=kind,error=str(exc),ok=False)
            self.completed.emit(result)
        self.worker=threading.Thread(target=run,name='ledger-service-cycle',daemon=True);self.worker.start()

    def drain(self):
        self.refresh()
        if self.host._closing or not self.pending or self.busy:return
        from .engineering_kernel import operator
        from . import service_lifecycle as services
        try:
            with self.kernel.db() as db:
                services._guard(db,self.kernel,self.receipt);pending=services.jobs(self.kernel,db)
            if pending['queued']:
                def cancel():
                    for ident in pending['queued']:
                        result=self.kernel.dispatch('jobs.cancel',{'id':ident},operator())
                        if not result.get('ok'):raise ValueError('Queued job cancellation needs reconciliation')
                self.background('cancel',cancel);return
            link=getattr(self.host,'remote_link',None);remote_process=getattr(link,'process',None)
            from PySide6.QtCore import QProcess
            processes=[p for p in self.host.master_stop_controller.processes() if p is not remote_process]
            overlay=getattr(self.host,'clip_overlay',None)
            provider_busy=overlay is not None and (overlay.busy or overlay._requests_inflight)
            if any(pending.values()) or provider_busy or any(p.state()!=QProcess.NotRunning for p in processes):
                stale=len(pending['running'])
                if stale and not pending['live_workers'] and not pending['protected_workers']:
                    # A running record without a worker never drains by itself; name the owner routes that resolve it.
                    self.host.statusBar().showMessage(str(stale)+(' running record has' if stale==1 else ' running records have')+' no live worker · use Master Stop or Work trail → recover')
                else:self.host.statusBar().showMessage('New work held · finishing running jobs, commands and replies. Stop is available.')
                return
            self.receipt=services.stop_gate(self.kernel,self.receipt,operator());self.refresh()
            if link is not None and not getattr(self.kernel,'is_host_client',False):
                link.stop()
                if remote_process is not None and remote_process.state()!=QProcess.NotRunning:raise ValueError('Phone listener exit is not confirmed')
            def close():
                if getattr(self.kernel,'is_host_client',False):return self.kernel.rpc('service_quiesce',{'cycle_id':self.receipt['id']})
                return services.close_owned_services(self.kernel,operator(),self.receipt['id'])
            self.background('close',close)
        except Exception as exc:self.failed(exc)

    def finished(self,result):
        self.busy=False
        if self.host._closing:return # An absent desktop lease makes this cycle interrupted; never replay Reboot.
        if not result['ok']:self.failed(result['error']);return
        if result['kind']=='cancel':self.drain();return
        from .engineering_kernel import operator
        from . import service_lifecycle as services
        try:
            self.receipt=services.stopped(self.kernel,self.receipt,operator());action=self.pending;self.pending=None
            if action=='Reboot':self.start(restore_model=True)
            else:self.host.statusBar().showMessage('Graphite services off · desktop open. System menu → Graphite services → On enables new work.');self.refresh()
        except Exception as exc:self.failed(exc)

    def start(self,restore_model=False):
        from .engineering_kernel import operator
        from . import service_lifecycle as services
        self.receipt=services.start(self.kernel,operator(),self.host.desktop_lease.stem,self.receipt if restore_model else None)
        self.pending=None;self.resume_timers()
        # Reboot revoked phone access during its drain; a plain On changes nothing about it.
        note='New Graphite work enabled. No cancelled jobs replayed; '+('phone access stays off.' if restore_model else self.phone_note())
        if restore_model and self.model_before:note+=' '+self.restore_model()
        self.host.statusBar().showMessage(note,10000);self.model_before=None;self.refresh()

    def phone_note(self):
        """The owned listener's observed state when this desktop runs it; otherwise an action statement, never an inferred 'off'."""
        from PySide6.QtCore import QProcess
        process=getattr(getattr(self.host,'remote_link',None),'process',None)
        if process is None or getattr(self.kernel,'is_host_client',False):return 'phone access is not changed by On.'
        return 'phone listener '+('running' if process.state()!=QProcess.NotRunning else 'off')+'; not changed by On.'

    def restore_model(self):
        """Request the previous model again inside its own guard; a failure here never downgrades the committed ON."""
        from .engineering_kernel import operator
        from . import service_lifecycle as services,ledger_control
        try:
            if not ledger_control.value(self.kernel,'stacy.enabled'):
                self.receipt=services.restore_note(self.kernel,self.receipt,operator(),'SKIPPED_SLATE_OFF');return 'Graphite AI is off; no model reload requested.'
            config=self.model_before.get('config',{});model_id=self.model_before['model_id']
            reply=self.kernel.dispatch('brain.model.use',dict(id=model_id,options={key:config[key] for key in ('context','threads','memory_mb') if key in config}),operator())
            job=(reply.get('result') or {}).get('id') if reply.get('ok') and isinstance(reply.get('result'),dict) else None
            job=job if isinstance(job,str) and re.fullmatch('[a-f0-9]{32}',job) else None
            self.receipt=services.restore_note(self.kernel,self.receipt,operator(),'REQUESTED' if reply.get('ok') else 'FAILED',job_id=job,model_id=model_id)
            return 'Previous model reload requested; inspect Local models.' if reply.get('ok') else 'Previous model reload failed; inspect Local models.'
        except Exception as exc:
            traceback.print_exc()
            try:self.receipt=services.restore_note(self.kernel,self.receipt,operator(),'FAILED')
            except READ_ERRORS:traceback.print_exc()
            return 'Previous model reload could not be requested: '+self.plain(exc)+' Inspect Local models.'

    def failed(self,error):
        from .engineering_kernel import operator
        from . import service_lifecycle as services
        if sys.exc_info()[0] is not None:traceback.print_exc()
        unrecorded=False
        if self.receipt:
            try:services.fail(self.kernel,self.receipt,operator())
            except READ_ERRORS:traceback.print_exc();unrecorded=True
        # The cycle is over either way; the Agenda and Study gates refuse on their own while services are off.
        self.pending=None;self.model_before=None;self.resume_timers();self.refresh()
        message=self.plain(error)
        tail='\nInspect Operations and Work trail before choosing On or Off.'
        if 'automatic restart' not in message:tail='\nNo automatic restart.'+tail
        if unrecorded:tail+='\nThe cycle state could not be recorded; the stored cycle may still read as active.'
        QMessageBox.warning(self.host,'Graphite service cycle incomplete',message+tail)

    def shutdown(self):
        """Desktop close: stop the timer and let a running close thread finish before its QObject goes away."""
        self.timer.stop();worker=self.worker
        if worker is not None and worker.is_alive():worker.join(5)
