"""Owner-operated master stop over existing Ledger job/session authorities."""
import json
import os
import threading
import sqlite3
import time
from PySide6.QtCore import QObject,QProcess,QTimer,Qt,Signal,QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu,QMessageBox,QToolButton,QWidget
from .engineering_kernel import operator
from . import engine,desktop_services
from .operation_stop import TERMINAL,force_cancel_worker,job_operations,kill_owned,owned_tree,process_identity,stop_advice
from . import operation_priority
from . import locations

STUCK_SCORE=85  # past a recorded time limit (85) or a running worker gone (95): the rules in operation_stop.stop_advice


class StopButton(QToolButton):
    """The controller's own button. Since UI-03 it is hidden: the one visible kill switch is the first row of Nice in the
    Ledger Head (desktop_header_qt.NicePopup.kill), which triggers the same action; the controller's words reach it through
    MasterStop.faces. The object stays so the controller, its tooltip detail and older callers keep one place to look."""
    def __init__(self,host):
        super().__init__(host)
        self.setObjectName('MasterStop')
        self.setIcon(QIcon(str(locations.program(host.root)/'branding/noir/master-stop.svg')))
        self.setIconSize(QSize(32,32));self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setFixedSize(86,58)
        self.setAccessibleName('Master stop: stop or kill all Graphite operations')
        self.setText('Advice 0%')
        self.setStyleSheet('QToolButton#MasterStop {background:transparent;border:1px solid transparent;border-radius:7px;padding:1px;color:#f3d0cc;font-size:10pt;} '
            'QToolButton#MasterStop:hover {background:#39262a;border-color:#ef8b80;} '
            'QToolButton#MasterStop:focus {border:2px solid #ffb05c;} '
            'QToolButton#MasterStop:pressed {background:#601e23;}')


class MasterStop(QObject):
    completed=Signal(object)

    def __init__(self,host,button):
        super().__init__(host);self.host=host;self.button=button;self.kernel=engine.engineering(host.root)
        self.running=False;self.last_report=None;self.advice=stop_advice([])
        self.priority_report=[];self._priority_seen=set()
        self.faces=[];self.detail=''  # UI-03: callables told after every refresh (the kill switch in Nice reads running, stuck and detail)
        self.completed.connect(self.finished)
        self.timer=QTimer(self);self.timer.setInterval(1500);self.timer.timeout.connect(self.refresh);self.timer.start()
        button.clicked.connect(host.a_master_stop.trigger)
        button.setContextMenuPolicy(Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(self.menu)
        QTimer.singleShot(0,self.refresh)

    def contexts(self):
        found={}
        for obj in self.host.findChildren(QWidget):
            kernel=getattr(obj,'kernel',None)
            if kernel is not None:found[id(kernel)]=(kernel,getattr(obj,'principal',operator()))
        return list(found.values())

    def processes(self):
        helper=getattr(self.host,'_taskkill',None)
        return [p for p in self.host.findChildren(QProcess) if p is not helper and p.state()!=QProcess.NotRunning]

    def operations(self):
        rows=job_operations(self.kernel.listing('jobs'))
        for p in self.processes():
            main=p is self.host.process
            label=(getattr(self.host.plan,'label','Command') if self.host.plan else 'Command') if main else type(p.parent()).__name__
            bounded=main and self.host.command_timer.isActive()
            rows.append({'label':label,'active':True,
                         'elapsed':max(0,time.time()-self.host.started_at) if bounded else None,
                         'timeout':120 if bounded else None})
        for kernel,_ in self.contexts():
            for session in list(getattr(kernel,'console_sessions',{}).values()):
                if not session.closed:rows.append({'label':'Virtual console','active':True})
        overlay=getattr(self.host,'clip_overlay',None)
        if overlay is not None and (overlay.busy or overlay._requests_inflight):rows.append({'label':'Provider reply','active':True})
        # Debugger/language transports expose tracked handles, not guessed CPU use.
        for _ in desktop_services.active_processes(self.host.root):rows.append({'label':'Desktop tool','active':True})
        return rows

    def refresh(self):
        if self.host._closing:return
        try:self.advice=stop_advice(self.operations())
        except (OSError,ValueError,RuntimeError) as exc:
            self.advice={'score':None,'active':None,'meaning':'Rule-based recommendation; not a probability.',
                         'coverage':'unavailable','reasons':['Health data unavailable: '+str(exc)]}
        score=self.advice['score'];value='—' if score is None else str(score)+'%'
        self.button.setText('Stopping…' if self.running else ('Stop' if self.button.property('paperFace') else 'Advice '+value))
        # 4.2: Stop turns pink only when recorded signals say something is stuck (past its limit, or its worker is gone).
        stuck=bool(self.running or (score is not None and score>=STUCK_SCORE))
        if bool(self.button.property('stuck'))!=stuck:
            self.button.setProperty('stuck',stuck);self.button.style().unpolish(self.button);self.button.style().polish(self.button)
        detail='Stop advice: '+value+'\n'+self.advice['meaning']+'\n\n'+'\n'.join(self.advice['reasons'])
        if stuck and not self.running:detail='Looks stuck. '+' '.join(r for r in self.advice['reasons'] if 'exceeded' in r or 'exited' in r)+'\n\n'+detail
        detail+='\n\nClick: confirm Stop all · Ctrl+Shift+F12\nRight-click: score details\nSilence alone does not raise the score.'
        try:
            from .work_trail import work_status
            if work_status(self.kernel)['held']:
                detail+='\nNew Kernel jobs are held. Open Work trail for explicit Resume.'
        except (ValueError,OSError,sqlite3.Error):detail+='\nWork admission state unavailable; reconcile before starting jobs.'
        try:
            mode=operation_priority.policy(self.host.root)
            detail+='\nWork CPU priority: '+('background / Be nice' if mode=='background' else 'normal for new work')
            if mode=='background' and not self.running:self.apply_priority()
            denied=sum(r['state'] in ('denied','refused') for r in self.priority_report)
            if denied:detail+='\nPriority changes not applied: '+str(denied)+' (OS refusal; inspect the current work).'
        except (OSError,ValueError) as exc:detail+='\nCPU priority preference unavailable: '+str(exc)
        self.button.setToolTip(detail);self.button.setAccessibleDescription(detail)
        self.host.a_master_stop.setToolTip(detail);self.detail=detail
        for face in list(self.faces):
            try:face(self)
            except RuntimeError:self.faces.remove(face)  # a face whose widget is gone

    def menu(self,point):
        menu=QMenu(self.button)
        menu.addAction('Explain stop advice…',self.explain)
        menu.addSeparator();menu.addSection('CPU scheduling · Graphite work')
        try:current=operation_priority.policy(self.host.root)
        except (OSError,ValueError):current=None
        for mode,label in (('normal','Normal for new work'),('background','Be nice · background CPU priority')):
            action=menu.addAction(label);action.setCheckable(True);action.setChecked(mode==current)
            action.triggered.connect(lambda checked=False,m=mode:self.select_priority(m))
        menu.addSeparator()
        menu.addAction('Open Work trail / Resume…',self.host.ledger_bridge.show_work_trail)
        menu.addAction(self.host.a_master_stop)
        menu.exec(self.button.mapToGlobal(point))

    def priority_roots(self):
        roots=[r.pid for r in owned_tree([os.getpid()],descendants_only=True)]
        for kernel,_ in self.contexts():
            roots += [s.process.pid for s in list(getattr(kernel,'console_sessions',{}).values()) if not s.closed and s.process.poll() is None]
        roots += [p.pid for p in desktop_services.active_processes(self.host.root)]
        for job in self.kernel.listing('jobs'):
            if job['state'] in TERMINAL:continue
            for field,stamp in (('pid','worker_start'),('tool_pid','tool_start')):
                pid=job.get(field);token=job.get(stamp)
                if pid and token and process_identity(pid)==token:roots.append(pid)
        return roots

    def apply_priority(self):
        results=[]
        for ref in owned_tree(self.priority_roots()):
            key=(ref.pid,ref.token)
            if key in self._priority_seen:continue
            result=operation_priority.background_process(self.host.root,ref.pid,ref.token)
            results.append(result)
            if result['state']=='background':self._priority_seen.add(key)
        if results:self.priority_report=results
        return results

    def select_priority(self,mode):
        from .ledger_control import change
        change(self.kernel,'operations.priority',mode,'desktop-owner')
        if mode=='background':
            results=self.apply_priority();denied=sum(r['state'] in ('denied','refused') for r in results)
            message='Be nice: background CPU priority selected for Graphite work.'
            if denied:message+=' '+str(denied)+' priority changes were refused by the OS.'
        else:
            message='Normal priority selected for new work. Existing nice values remain until that work finishes.'
        self.host.statusBar().showMessage(message,12000);self.refresh()

    def explain(self):
        self.refresh();box=QMessageBox(self.host);box.setWindowTitle('Stop advice')
        score=self.advice['score'];box.setText('Insufficient evidence for a percentage' if score is None else str(score)+'% · stop-recommendation score')
        box.setInformativeText(self.advice['meaning']+'\n\n'+'\n'.join(self.advice['reasons'])+
            '\n\nRules: 25% near a recorded deadline; 50% queued over 60 seconds; 85% overdue by over 3 seconds; 95% a running job’s worker has exited. The highest applicable rule wins. This never stops anything automatically.')
        box.exec()

    def request(self):
        if self.running:
            self.host.statusBar().showMessage('Master stop is still checking remaining operations.');return False
        box=QMessageBox(self.host);box.setWindowTitle('Stop all Graphite operations?')
        box.setIcon(QMessageBox.Warning);box.setText('Stop / kill operations for this Graphite project?')
        box.setInformativeText('Cancel project jobs, stop builds and host processes, close console/debugger sessions, and switch off the phone link. Source files and unsaved editor buffers are preserved. A provider request already sent may finish remotely.')
        stop=box.addButton('Stop all',QMessageBox.DestructiveRole)
        cancel=box.addButton(QMessageBox.Cancel);box.setDefaultButton(cancel);box.exec()
        if box.clickedButton() is not stop:return False
        return self.start()

    def start(self):
        if self.running:return False
        w=self.host;self.running=True;self.last_report=None
        from . import work_trail
        self.hold_error=None
        try:
            if getattr(self.kernel,'is_host_client',False):self.kernel.rpc('hold')
            else:work_trail.hold(self.kernel,operator())
        except (ValueError,OSError,sqlite3.Error) as exc:
            self.hold_error="Work hold unavailable; reconcile before restarting work."
            w.statusBar().showMessage(self.hold_error)
        if hasattr(w,'study_idle'):
            try:w.study_idle.inhibit()
            except (ValueError,OSError):w.study_idle.inhibited=True
        from . import activity
        activity.record(w.root,'desktop-owner','operations.master_stop','REQUESTED')
        w._operation_epoch+=1
        from .ledger_control import pending,acknowledge
        for intent in pending(self.kernel):acknowledge(self.kernel,intent,'CANCELLED','Master stop')
        w.after_build=None;w._then=None;w._job_callback=None
        w.workflow_active=False;w._workflow_steps=[];w._stop_requested=True
        w.command_timer.stop();w.sim_trace.pause()
        driver=getattr(w,'agent_driver',None)
        if driver is not None:
            try:driver.pause_all('Master Stop')  # AGENT-01: running assignments pause with the reason; Today offers to resume them
            except Exception as exc:w.statusBar().showMessage('Assignments not paused: '+str(exc),8000)
        watcher=getattr(w,'book_watcher',None)
        if watcher is not None:watcher.active=False;watcher.timer.stop()
        overlay=getattr(w,'clip_overlay',None);provider_pending=bool(overlay is not None and (overlay.busy or overlay._requests_inflight))
        browser_pending=bool(w._browser_opened and w.plan and w.plan.target in ('arcade','ledger'))
        if overlay is not None:overlay.cancel_pending()
        contexts=self.contexts();qprocesses=self.processes()
        roots=[int(p.processId()) for p in qprocesses if p.processId()]
        refs=self.desktop_descendants()
        for p in qprocesses:
            if p.state()==QProcess.Starting:
                epoch=w._operation_epoch
                p.started.connect(lambda p=p,e=epoch:p.kill() if w._operation_epoch==e else None,Qt.SingleShotConnection)
        for obj in w.findChildren(QWidget):
            if getattr(obj,'kernel',None) is None:continue
            for name in ('timer','poll','jobtimer','job_timer'):
                timer=getattr(obj,name,None)
                if isinstance(timer,QTimer):timer.stop()
            for name,value in (('autoboot',False),('after_build',False),('needs_input',False),('pending',False)):
                if hasattr(obj,name):setattr(obj,name,value)
            if hasattr(obj,'held'):obj.held.clear()
            if hasattr(obj,'mask'):obj.mask=0
        for obj in w.findChildren(QWidget):
            if type(obj).__name__=='ProjectSearchTab':obj.shutdown()
        self.refresh();w.statusBar().showMessage('Master stop: cancellation and process checks in progress…')

        def run():
            report={'schema':'arc.master-stop/1','cancel_requested':[],'jobs_pending':[],
                    'sessions_closed':[],'process_results':[],'errors':[],'unverified':[]}
            if self.hold_error:report['errors'].append(self.hold_error)
            try:
                from . import local_brain
                if getattr(self.kernel,'is_host_client',False):
                    service_report=self.kernel.rpc('master_stop',timeout=45)
                    report['service']=service_report
                    report['errors'].extend(service_report['errors'])
                    report['sessions_closed'].extend(service_report['sessions_closed'])
                    if service_report['result']!='STOPPED':report['errors'].append('Background work still needs reconciliation')
                else:
                    local_brain.stop(self.kernel,'MASTER_STOP')
                    from . import worker_boundary
                    report['protected_workers']=worker_boundary.stop_all(self.kernel)
                    if any(not r['stopped'] for r in report['protected_workers']):report['errors'].append('A protected worker unit needs reconciliation')
                # Close the remote admission path first, before taking the job snapshot.
                r=self.kernel.dispatch('remote.disable',{},operator())
                if not r['ok']:report['errors'].append('Phone-link revocation: '+r['error']['message'])
                initial_jobs=self.kernel.listing('jobs')
                for job in initial_jobs:
                    if job['state'] in TERMINAL:continue
                    r=self.kernel.dispatch('jobs.cancel',{'id':job['id']},operator())
                    if r['ok']:report['cancel_requested'].append(job['id'])
                    else:report['errors'].append(job['tool']+': '+r['error']['message'])
                # Keep job workers alive long enough to observe cancellation and
                # write a terminal result, even when their remote server is killed.
                worker_refs=owned_tree([j.get('pid') for j in initial_jobs if j.get('pid') and j['state'] not in TERMINAL])
                worker_pids={ref.pid for ref in worker_refs}
                process_refs=[ref for ref in refs if ref.pid not in worker_pids]
                report['process_results']+=kill_owned(process_refs)
                debug_refs=owned_tree([p.pid for p in desktop_services.active_processes(w.root)])
                try:desktop_services.close_all(w.root)
                except Exception as exc:report['errors'].append('Desktop tools: '+str(exc))
                report['process_results']+=kill_owned(debug_refs)
                requested=set(report['cancel_requested']);closed=set();began=time.monotonic();deadline=began+12
                while True:
                    jobs=self.kernel.listing('jobs')
                    pending=[j for j in jobs if j['state'] not in TERMINAL]
                    for j in pending:
                        if j['id'] in requested:continue
                        r=self.kernel.dispatch('jobs.cancel',{'id':j['id']},operator())
                        requested.add(j['id'])
                        if r['ok']:report['cancel_requested'].append(j['id'])
                        else:report['errors'].append(j['tool']+': '+r['error']['message'])
                    for kernel,principal in contexts:
                        for ident,session in list(getattr(kernel,'console_sessions',{}).items()):
                            key=(id(kernel),ident)
                            if session.closed or key in closed:continue
                            r=kernel.dispatch('console.close',{'id':ident},principal)
                            if r['ok'] and r['result'].get('state')=='CLOSED':
                                report['sessions_closed'].append(ident);closed.add(key)
                            elif not r['ok']:
                                report['errors'].append('Console close: '+r['error']['message']);closed.add(key)
                    pending=[j for j in self.kernel.listing('jobs') if j['state'] not in TERMINAL]
                    if time.monotonic()-began>3 and not getattr(self.kernel,'is_host_client',False):
                        for job in self.kernel.listing('jobs'):
                            if job.get('cancel') and job.get('worker_start'):
                                force_cancel_worker(self.kernel,job)
                        pending=[j for j in self.kernel.listing('jobs') if j['state'] not in TERMINAL]
                    # Also catch a compiler/helper launched by a Python service
                    # that was already in flight when the stop was accepted.
                    current_jobs=self.kernel.listing('jobs')
                    worker_refs=owned_tree([j.get('pid') for j in current_jobs if j.get('pid') and j['state'] not in TERMINAL])
                    protected={r.pid for r in worker_refs}
                    late=[r for r in self.desktop_descendants() if r.pid not in protected]
                    report['process_results']+=kill_owned(late)
                    refs.extend(r for r in late if r not in refs)
                    live_workers=[j for j in current_jobs if j.get('cancel') and j.get('worker_start') and process_identity(j.get('pid'))==j['worker_start']]
                    # A settling interval also catches submissions already in flight
                    # when the stop was pressed. Late UI callbacks are fenced by epoch.
                    if not pending and not live_workers and time.monotonic()>deadline-10:break
                    if time.monotonic()>=deadline:break
                    time.sleep(.1)
                report['jobs_pending']=[{'id':j['id'],'tool':j['tool'],'state':j['state']} for j in pending]
                report['processes_pending']=[ref.pid for ref in refs+debug_refs if process_identity(ref.pid)==ref.token]
                report['workers_pending']=[j['id'] for j in self.kernel.listing('jobs') if j.get('cancel') and j.get('worker_start') and process_identity(j.get('pid'))==j['worker_start']]
                report['consoles_pending']=[ident for kernel,_ in contexts for ident,s in list(getattr(kernel,'console_sessions',{}).items()) if not s.closed]
                if provider_pending:report['unverified'].append('A provider request already sent cannot be recalled; its local reply is discarded.')
                if browser_pending:report['unverified'].append('The local preview server was stopped; an already-open external browser page may continue running.')
                report['result']='STOPPED' if not any((report['jobs_pending'],report['processes_pending'],report['workers_pending'],report['consoles_pending'],report['errors'],report['unverified'])) else 'INCOMPLETE'
            except Exception as exc:
                report['errors'].append(str(exc));report['result']='INCOMPLETE'
            try:self.completed.emit(report)
            except RuntimeError:pass
        self.worker=threading.Thread(target=run,daemon=True,name='ledger-master-stop');self.worker.start()
        return True

    def desktop_descendants(self):
        refs=owned_tree([os.getpid()],descendants_only=True)
        if getattr(self.kernel,'is_host_client',False):
            # A detached service may have been started by this desktop. It is
            # not a desktop command to kill. Its own stop authority handles
            # jobs, models and consoles and keeps the coordinator available.
            try:info=self.kernel.rpc('status',timeout=2)
            except (ValueError,OSError):
                # Without a confirmed service identity, stop only directly
                # tracked GUI commands rather than guessing at descendants.
                return owned_tree([int(p.processId()) for p in self.processes() if p.processId()])
            excluded={r.pid for r in owned_tree([info['pid']])}
            excluded.add(info['pid'])
            refs=[r for r in refs if r.pid not in excluded]
        return refs

    def finished(self,report):
        self.running=False;w=self.host
        for obj in w.findChildren(QWidget):
            ident=getattr(obj,'session_id',None)
            if ident and ident in report['sessions_closed']:
                obj.session_id=None
                if isinstance(getattr(obj,'state',None),dict):obj.state={**obj.state,'state':'CLOSED'}
                if hasattr(obj,'status'):obj.status.setText('Console closed by master stop')
        from .engineering_kernel import CAPABILITIES
        if getattr(getattr(w,'ledger_bridge',None),'busy',False):
            report['unverified'].append('Graphite command service is still finishing; subsequent commands are cancelled.')
            report['result']='INCOMPLETE'
        for worker in list(getattr(w,'service_workers',[])):
            if worker.isRunning() and CAPABILITIES.get(getattr(worker,'op',None)) not in (None,'read'):
                report['unverified'].append('Local service still finishing: '+worker.op);report['result']='INCOMPLETE'
        for p in self.processes():
            # QProcess may still be delivering its exit notification. A live
            # remainder is reported, not relabelled as successfully stopped.
            if p.processId() and process_identity(int(p.processId())) is not None:
                report.setdefault('processes_pending',[]).append(int(p.processId()));report['result']='INCOMPLETE'
        remote=getattr(w,'remote_link',None)
        if remote is not None:
            remote.code='';remote.pairing.clear();remote.status.setText('Phone link disabled by master stop; sessions revoked.')
        self.last_report=report
        from . import activity
        activity.record(w.root,'KERNEL','operations.master_stop',report['result'])
        summary='Master stop: '+('operations stopped' if report['result']=='STOPPED' else 'some work remains unconfirmed')
        w.output.appendPlainText('\n'+summary+'\n'+json.dumps(report,indent=2))
        w.statusBar().showMessage(summary,15000)
        from .record_io import write_json
        write_json(w.root/'.ledger/master-stop/latest.json',report)
        w.clip.presence.dismiss();self.refresh()
