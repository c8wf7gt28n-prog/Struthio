"""HATCH DESK D2: the System menu, session and power, the two launch menus' one design, and the cat's colours.

The owner's brief of 2026-11-06: the System menu from the Graphite symbol (Game first, Stop all jobs beneath it, the ordered
process list with a niceness slider on every row and the queue's reorder distinct from niceness, then Log out, Return to Debian,
Restart and Shut down in a separated group, with session and machine scope clear); the cat's programs list as its point-mirror
image. Every session and power request goes through session_power.system, which these tests replace with a fake logind: nothing
here logs out, restarts or powers off, starts a process or talks to a real D-Bus. Offscreen, with a bare host, no window.
"""
import os,re,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from workbench import session_power as power
from workbench.engineering_kernel import Kernel,operator
from workbench.session import Session
from workbench import ledger_control


class FakeLogind:
    """Answers session_power.system as logind would and records every request; starts nothing. `missing` names programs not
    installed; `at_run` is called at the moment a command would start (what was already done then)."""
    def __init__(self,session='7',reboot='yes',poweroff='yes',ok=True,reason='',events=None,missing=(),at_run=None):
        self.session=session;self.answers={'CanReboot':reboot,'CanPowerOff':poweroff};self.ok=ok;self.reason=reason
        self.requests=[];self.runs=[];self.events=events if events is not None else [];self.missing=set(missing);self.at_run=at_run;self.seen=None

    def __call__(self,request):
        self.requests.append(request)
        if request[0]=='logind':
            path,interface,method=request[1:4]
            if method=='Get':
                if self.session is None:raise OSError('Caller does not belong to any known session')
                assert path==power.SELF and request[4:]==('org.freedesktop.login1.Session','Id'),request
                return self.session
            assert path==power.MANAGER[0] and interface==power.MANAGER[1],request
            return self.answers[method]
        if request[0]=='where':
            assert request[1] in power.PROGRAMS,request
            return None if request[1] in self.missing else '/usr/bin/'+request[1]
        if request[0]=='run':
            self.runs.append(tuple(request[1]));self.events.append(('run',tuple(request[1])))
            if self.at_run is not None:self.seen=self.at_run()
            return dict(ok=self.ok,code=0 if self.ok else 1,reason=self.reason)
        raise AssertionError(request)


def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class AvailabilityTests(unittest.TestCase):
    def test_availability_comes_from_logind_and_names_the_reason(self):
        with patch.object(power,'system',FakeLogind(reboot='yes',poweroff='challenge')):states=power.availability('linux')
        self.assertTrue(all(states[a]['available'] for a in power.ACTIONS),states)
        self.assertIn('challenge',states['shutdown']['reason']);self.assertEqual(states['logout']['session'],'7')
        for value,words in (('na','does not offer it'),('no','may not do it here')):
            with patch.object(power,'system',FakeLogind(reboot=value,poweroff=value)):states=power.availability('linux')
            for action in ('restart','shutdown'):
                self.assertFalse(states[action]['available'],(value,action));self.assertIn(words,states[action]['reason']);self.assertIn('logind: '+value,states[action]['reason'])
            self.assertTrue(states['logout']['available'],'Log out needs only the session')

    def test_challenge_is_offered_only_where_the_system_can_ask(self):
        """D2-fix: 'challenge' means the system asks for permission itself. The dedicated session starts no permission agent and
        the command has no terminal, so nothing could answer: there it is unavailable with the way that works (else Graphite
        would close the ordinary way and the command would then fail)."""
        with patch.object(power,'system',FakeLogind(reboot='challenge',poweroff='challenge')):
            elsewhere=power.availability('linux',environ={});dedicated=power.availability('linux',environ={'ARC_LEDGER_XSESSION':'1'})
        self.assertTrue(elsewhere['restart']['available'] and elsewhere['shutdown']['available'])
        self.assertFalse(dedicated['restart']['available'] or dedicated['shutdown']['available'])
        self.assertIn('no permission prompt',dedicated['restart']['reason']);self.assertIn('systemctl reboot at the text login',dedicated['restart']['reason'])
        self.assertIn('systemctl poweroff',dedicated['shutdown']['reason']);self.assertTrue(dedicated['logout']['available'],'Log out of one\'s own session asks no permission')
        with patch.object(power,'system',FakeLogind(reboot='yes',poweroff='yes')):
            self.assertTrue(power.availability('linux',environ={'ARC_LEDGER_XSESSION':'1'})['restart']['available'])

    def test_no_logind_session_makes_every_action_unavailable_with_that_reason(self):
        fake=FakeLogind(session=None)
        with patch.object(power,'system',fake):states=power.availability('linux')
        self.assertTrue(all(not s['available'] and s['reason'].startswith(power.NO_SESSION) for s in states.values()),states)
        self.assertEqual([r[3] for r in fake.requests],['Get'],'nothing else is asked without a session');self.assertEqual(fake.runs,[])
        with patch.object(power,'system',FakeLogind(session='not a session id; rm')):states=power.availability('linux')
        self.assertTrue(all(not s['available'] for s in states.values()))
        states=power.availability('darwin');self.assertTrue(all(s['reason']==power.NOT_LINUX for s in states.values()))

    def test_the_commands_are_the_systems_own_and_never_sudo(self):
        state=dict(available=True,session='7')
        self.assertEqual(power.command('logout',state),('loginctl','terminate-session','7'))
        self.assertEqual(power.command('restart',state),('systemctl','reboot'));self.assertEqual(power.command('shutdown',state),('systemctl','poweroff'))
        import subprocess
        with patch.object(subprocess,'run',side_effect=AssertionError('nothing may start')) as ran:
            for argv in (('sudo','systemctl','reboot'),('systemctl','reboot','sudo'),('bash','-c','reboot'),('pkexec','systemctl','poweroff'),()):
                with self.assertRaises(ValueError,msg=argv):power.system(('run',argv))
            for program in ('sudo','bash','reboot'):
                with self.assertRaises(ValueError,msg=program):power.system(('where',program))
            ran.assert_not_called()
        self.assertEqual(power.PROGRAMS,('loginctl','systemctl'));self.assertEqual(power.SCOPES['restart'],power.SCOPES['shutdown'],'this computer')
        self.assertEqual((power.SCOPES['logout'],power.SCOPES['leave'],power.SCOPES['restart']),('this login session','this Graphite session','this computer'))

    def test_one_function_issues_every_command(self):
        """session_power.system is the only place a session or power command can start; the menus and the cat name none."""
        root=Path(__file__).resolve().parents[1]/'workbench'
        text=(root/'session_power.py').read_text()
        self.assertEqual(text.count('subprocess.run('),1);self.assertNotIn('shell=True',text);self.assertNotIn('os.system',text)
        import ast
        def code(path):
            """The module's code without its docstrings and comments (what runs, not what explains it)."""
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node,(ast.Module,ast.FunctionDef,ast.ClassDef)) and node.body and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant):
                    node.body[0].value.value=''
            return ast.unparse(tree)
        for name in ('hatch_qt.py','programs_qt.py','system_menu_qt.py','desktop_header_qt.py'):
            source=code(root/name)
            for word in ('subprocess','os.system','startDetached','systemctl','loginctl','QDBus'):self.assertNotIn(word,source,(name,word))


class ChecksHoldTheOneFunctionTests(unittest.TestCase):
    """D2-fix (the review: check_desk_ui and check_head_ui opened the System menu with session_power.system unpatched, so they
    asked the real system bus; they passed only where there is none). Every Qt check that opens or builds the System menu holds
    the one function at its holds, for the whole run (module level, started), so no check asks the real logind or could start a
    session or power command, on any computer. A run of every check with a probe on session_power's real paths found eight
    that reached them (D2-fix evidence, reach_probe/before)."""
    TOOLS=Path(__file__).resolve().parents[1]/'tools'
    OPENS=re.compile(r"top\.nice\.(open|menu_|popup)|\bnice\.(open|menu_)\(|\bnice\.popup|\bsym\.(open|popup)|session_rows|SystemMenu\(|work_list\.click\(|QTest\.key\w*\((nice|sym)\b")
    HELD=re.compile(r"^[A-Za-z_]\w*\s*=\s*patch\.object\(\s*session_power\s*,\s*'system'\s*,[^\n]*\)\.start\(\)",re.M)

    def test_every_check_that_opens_the_system_menu_holds_session_power_system(self):
        openers=[];unheld=[]
        for path in sorted(self.TOOLS.glob('check_*.py')):
            text=path.read_text()
            if self.OPENS.search(text):
                openers.append(path.name)
                if not self.HELD.search(text):unheld.append(path.name)
        self.assertGreaterEqual(len(openers),9,openers)
        self.assertEqual(unheld,[],'these checks open the System menu without holding session_power.system')


class Host:
    """The least window run_action needs: the leave flow is patched or faked, close is counted (`refuse` makes the window's own
    close refuse, as when a working area will not close)."""
    def __init__(self,events,refuse=False):
        self.events=events;self.closed=0;self.messages=[];self.return_thread=SimpleNamespace(skip_keep_once=False);self.refuse=refuse
    def statusBar(self):return SimpleNamespace(showMessage=lambda text,*a:self.messages.append(text))
    def close(self):
        self.events.append(('close',self.return_thread.skip_keep_once))
        if self.refuse:return False
        self.closed+=1;return True


class RunActionTests(unittest.TestCase):
    """D2-fix: the questions, then the confirmation (nothing stopped before it), then the ordinary close, then the command."""
    def setUp(self):app()

    def run_with(self,action,fake,leave=True,confirm=True,keep=True,refuse=False):
        events=fake.events;host=Host(events,refuse);told=[];ended=[]
        left=dict(keep=keep,discarded=[],owned=[]) if leave else None
        def steps(h):events.append(('leave',));return left
        def ask(h,a):events.append(('confirm',a));return confirm
        with patch.object(power,'system',fake),patch.object(power,'leave_steps',side_effect=steps),patch.object(power,'confirm',side_effect=ask),\
             patch.object(power,'tell',side_effect=lambda h,title,text:told.append((title,text))),patch.object(power,'_end',side_effect=ended.append):
            result=power.run_action(host,action,platform='linux')
        self.assertTrue(app().quitOnLastWindowClosed(),'the application\'s own quit rule is restored')
        return result,host,events,told,ended

    def test_the_questions_then_the_confirmation_then_the_close_then_the_command(self):
        result,host,events,told,ended=self.run_with('restart',FakeLogind())
        self.assertEqual(result['state'],'STARTED');self.assertEqual(result['argv'],['systemctl','reboot']);self.assertTrue(result['closed'])
        self.assertEqual([e[0] for e in events],['leave','confirm','close','run'],events)
        self.assertEqual(events[2],('close',False),'keep: the close takes the return copy itself, as Keep and close does')
        self.assertFalse(host.return_thread.skip_keep_once);self.assertEqual(told,[]);self.assertEqual(ended,[app()],'the application ends as after any close')
        result,host,events,told,ended=self.run_with('logout',FakeLogind(session='c2'),keep=False)
        self.assertEqual(result['argv'],['loginctl','terminate-session','c2']);self.assertEqual(events[2:],[('close',True),('run',('loginctl','terminate-session','c2'))])
        result,host,events,told,ended=self.run_with('shutdown',FakeLogind(poweroff='challenge'))
        self.assertEqual(result['state'],'STARTED');self.assertEqual(result['argv'],['systemctl','poweroff'])

    def test_the_close_holds_the_applications_quit_until_the_command_has_answered(self):
        """Qt quits when the last window closes; a last message after the close would swallow that quit and leave Graphite running
        with no window (qt_quit_probe in the D2-fix evidence). So the quit is held across the close and the command."""
        fake=FakeLogind(at_run=lambda:app().quitOnLastWindowClosed())
        self.run_with('restart',fake);self.assertIs(fake.seen,False)

    def test_with_no_session_nothing_is_asked_or_issued(self):
        fake=FakeLogind(session=None)
        for action in power.ACTIONS:
            result,host,events,told,ended=self.run_with(action,fake)
            self.assertEqual(result['state'],'UNAVAILABLE');self.assertTrue(result['reason'].startswith(power.NO_SESSION))
            self.assertEqual(events,[],'no leave flow, no confirmation, no close, no command');self.assertEqual(host.closed,0)
            self.assertIn('Graphite stays open',told[0][1]);self.assertEqual(ended,[])
        self.assertEqual(fake.runs,[])

    def test_an_unavailable_action_is_refused_with_the_reason(self):
        result,host,events,told,ended=self.run_with('restart',FakeLogind(reboot='no'))
        self.assertEqual(result['state'],'UNAVAILABLE');self.assertEqual(events,[]);self.assertIn('logind: no',told[0][1])

    def test_cancelling_stops_nothing_issues_nothing_and_graphite_stays_open(self):
        result,host,events,told,ended=self.run_with('restart',FakeLogind(),leave=False)
        self.assertEqual((result['state'],result['step']),('CANCELLED','leave'));self.assertEqual([e[0] for e in events],['leave'])
        result,host,events,told,ended=self.run_with('shutdown',FakeLogind(),confirm=False)
        self.assertEqual((result['state'],result['step']),('CANCELLED','confirm'));self.assertEqual([e[0] for e in events],['leave','confirm'])
        self.assertEqual(host.closed,0);self.assertIn('Graphite stays open',host.messages[-1]);self.assertIn('nothing was stopped',host.messages[-1]);self.assertEqual(ended,[])

    def test_a_refused_close_issues_nothing_and_graphite_stays_open(self):
        result,host,events,told,ended=self.run_with('restart',FakeLogind(),refuse=True)
        self.assertEqual((result['state'],result['step'],result['closed']),('CANCELLED','close',False));self.assertEqual([e[0] for e in events],['leave','confirm','close'])
        self.assertIn('nothing was issued',host.messages[-1]);self.assertEqual(ended,[])

    def test_a_missing_program_is_found_before_the_close(self):
        fake=FakeLogind(missing=('systemctl',))
        result,host,events,told,ended=self.run_with('shutdown',fake)
        self.assertEqual((result['state'],result['closed']),('FAILED',False));self.assertEqual([e[0] for e in events],['leave','confirm'])
        self.assertEqual(told[0][0],'Shut down cannot start');self.assertIn('systemctl is not installed',told[0][1]);self.assertIn('Graphite stays open; nothing was stopped',told[0][1])
        self.assertEqual(fake.runs,[]);self.assertEqual(host.closed,0)

    def test_a_command_refused_after_the_close_says_why(self):
        """The system's own permission prompt declined, say: Graphite has closed the ordinary way already (it must, before the
        session or the computer ends), so it says why in a last message and the application ends."""
        fake=FakeLogind(ok=False,reason='Failed to reboot system via logind: Interactive authentication required.')
        result,host,events,told,ended=self.run_with('restart',fake)
        self.assertEqual((result['state'],result['closed']),('FAILED',True));self.assertEqual([e[0] for e in events],['leave','confirm','close','run'])
        self.assertEqual(told[0][0],'Restart did not start');self.assertIn('Interactive authentication required',told[0][1])
        self.assertIn('Graphite had already closed the ordinary way',told[0][1]);self.assertEqual(ended,[app()])

    def test_availability_is_asked_again_after_the_questions(self):
        """The session or the permission may change while the questions are open: nothing is stopped or issued then."""
        fake=FakeLogind()
        def steps(h):fake.answers['CanReboot']='no';return dict(keep=True,discarded=[],owned=[])
        told=[];host=Host([])
        with patch.object(power,'system',fake),patch.object(power,'leave_steps',side_effect=steps),patch.object(power,'confirm',return_value=True),\
             patch.object(power,'tell',side_effect=lambda h,title,text:told.append(title)):
            result=power.run_action(host,'restart',platform='linux')
        self.assertEqual(result['state'],'UNAVAILABLE');self.assertEqual(fake.runs,[]);self.assertEqual(host.closed,0)


class LeaveStepsTests(unittest.TestCase):
    """The existing leave flow's questions, in its order, without closing the window and without stopping anything."""
    def setUp(self):app()

    def host(self,answer=1,save='discard',capture=True,running=True):
        from PySide6.QtCore import QProcess
        events=[]
        class CodeEditor:
            def __init__(self,name):
                self.path=Path('/tmp/workspace/'+name);self.disk_sha256='0'*64;self.recovery_owned=True;self.modified=True
                self.document=lambda:SimpleNamespace(isModified=lambda:self.modified,setModified=lambda v:setattr(self,'modified',v))
            def toPlainText(self):return 'edited'
        editor=CodeEditor('notes.py')
        tabs=SimpleNamespace(count=lambda:1,widget=lambda i:editor,setCurrentWidget=lambda w:None)
        thread=SimpleNamespace(skip_keep_once=False,exit_dialog=lambda:SimpleNamespace(exec=lambda:(events.append(('return copy',answer)),answer)[1]),
                               capture=lambda for_exit=False:(events.append(('keep',for_exit)),capture)[1])
        kernel=SimpleNamespace(is_host_client=False,dispatch=lambda op,args,principal:(events.append(('dispatch',op)),{'ok':True})[1])
        process=SimpleNamespace(state=lambda:QProcess.Running if running else QProcess.NotRunning,waitForFinished=lambda ms:True)
        host=SimpleNamespace(return_thread=thread,tabs=tabs,ledger_bridge=SimpleNamespace(kernel=kernel),process=process,root=Path('/tmp/workspace'),
            ask_save=lambda name:(events.append(('ask',name)),save)[1],save_document=lambda ed:(events.append(('save',ed.path.name)),True)[1],
            recovery=SimpleNamespace(put=lambda rel,text,sha:events.append(('recovery',rel))),_kill_command_tree=lambda:events.append(('kill',)),
            statusBar=lambda:SimpleNamespace(showMessage=lambda *a:None),close=lambda:events.append(('close',thread.skip_keep_once)) or True)
        return host,events,editor

    def test_the_questions_in_the_leave_flows_order_stop_nothing(self):
        """D2-fix: the questions only. The model, the tracked command and the return copy are the close's, after the owner
        confirms (the review: Cancel at the confirmation had already lost a running command and unloaded the model)."""
        from workbench import engine
        host,events,editor=self.host()
        with patch.object(engine,'rel',side_effect=lambda path,root:path.name):left=power.leave_steps(host)
        self.assertEqual(left['keep'],True);self.assertEqual(left['discarded'],[editor]);self.assertEqual(left['owned'],[True])
        self.assertEqual(events,[('return copy',1),('ask','notes.py'),('recovery','notes.py')],'no return copy taken, no brain.stop, no kill')
        self.assertFalse(editor.recovery_owned,'a discarded file keeps its recovery copy, as on close');self.assertTrue(editor.modified,'its buffer is as it was')
        power.quiet_close(host,left);self.assertEqual(events[-1],('close',False),'keep: the close takes the return copy')
        self.assertFalse(editor.modified);self.assertFalse(host.return_thread.skip_keep_once)

    def test_cancel_puts_back_what_the_questions_set_aside(self):
        from workbench import engine
        host,events,editor=self.host()
        with patch.object(engine,'rel',side_effect=lambda path,root:path.name):left=power.leave_steps(host)
        power.undo_leave(left);self.assertTrue(editor.recovery_owned and editor.modified,'the file is as before the question')
        host,events,editor=self.host();host.close=lambda:False
        with patch.object(engine,'rel',side_effect=lambda path,root:path.name):left=power.leave_steps(host)
        self.assertFalse(power.quiet_close(host,left));self.assertTrue(editor.modified,'a refused close: the discarded buffer counts as edited again')

    def test_continue_working_or_a_failed_save_stops_the_flow(self):
        host,events,editor=self.host(answer=0);self.assertIsNone(power.leave_steps(host));self.assertEqual(events,[('return copy',0)])
        host,events,editor=self.host(save='cancel');self.assertIsNone(power.leave_steps(host));self.assertNotIn(('dispatch','brain.stop'),events)
        host,events,editor=self.host(answer=2,save='save',running=False);left=power.leave_steps(host)
        self.assertFalse(left['keep']);self.assertNotIn(('keep',True),events,'skip: no new return copy');self.assertIn(('save','notes.py'),events)
        power.quiet_close(host,left);self.assertEqual(events[-1],('close',True),'skip: the close takes none')


class RealWindowLeaveTests(unittest.TestCase):
    """D2-fix, on the real window (offscreen; Kernel.launch, Kernel.submit, the provider request, subprocess.Popen, os.system and
    QProcess.startDetached held; session_power.system a fake logind). The review found that Log out issued its command before
    the window's close (logind then ends the process: the close never ran) and that the leave flow stopped the model and the
    tracked command before the confirmation."""
    def setUp(self):
        import platform,subprocess
        from PySide6.QtCore import QProcess
        from PySide6.QtWidgets import QMessageBox
        from workbench import clip,locations
        from workbench.qt_app import WorkbenchWindow,make_app
        temporary=tempfile.TemporaryDirectory(prefix='graphite-leave-');self.addCleanup(temporary.cleanup);run=Path(temporary.name)
        env=patch.dict(os.environ,{'ARC_LEDGER_EMBEDDED':'1','ARC_LEDGER_DISABLE_BOOK_WATCHER':'1','ARC1_WORKBENCH_CONFIG_HOME':str(run/'profile'),'ARC_LEDGER_CONCERN':str(run/'Concern')})
        env.start();self.addCleanup(env.stop);os.environ.pop('ARC_LEDGER_XSESSION',None)
        for h in (patch.object(clip,'_request',side_effect=AssertionError('No provider request')),patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')),
                  patch.object(Kernel,'submit',side_effect=AssertionError('No job submission'))):h.start();self.addCleanup(h.stop)
        self.app=make_app([]);root=locations.office(run/'workspace');self.session_file=run/'profile/session.json'
        w=WorkbenchWindow(root,Session(self.session_file,root),restore=False);platform.processor()
        for h in (patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')),patch.object(os,'system',side_effect=AssertionError('No shell command')),
                  patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program'))):h.start();self.addCleanup(h.stop)
        w.resize(1366,768);w.show();self.settle();w.ledger_bridge.timer.stop();w.type_bar.hatch.lifecycle.timer.stop()
        self.w=w;self.done=[];kernel=w.ledger_bridge.kernel;real=kernel.dispatch
        kernel.dispatch=lambda op,args,principal,*a,**kw:(self.done.append(op),real(op,args,principal,*a,**kw))[1]
        for owner,name in ((w,'save_session'),(w,'_kill_command_tree'),(w.agent_driver,'pause_all'),(w.agent_driver,'release_all'),
                           (w.type_bar.hatch.lifecycle,'shutdown'),(w.return_thread,'capture')):
            method=getattr(owner,name);setattr(owner,name,lambda *a,_m=method,_n=name,**kw:(self.done.append(_n),_m(*a,**kw))[1])
        w.return_thread.exit_dialog=lambda:SimpleNamespace(exec=lambda:1)  # Keep and close
        self.question=patch.object(QMessageBox,'question',return_value=QMessageBox.Yes);self.question.start();self.addCleanup(self.question.stop)
        def close_window():
            if w.isVisible():w.close();self.settle()
        self.addCleanup(close_window)

    def settle(self):
        from PySide6.QtTest import QTest
        for _ in range(3):self.app.processEvents();QTest.qWait(20)

    def at_run(self):
        w=self.w;return dict(visible=w.isVisible(),closing=bool(getattr(w,'_closing',False)),done=list(self.done),session_saved=self.session_file.is_file(),
                             lease=w.desktop_lease.exists(),quit_held=not self.app.quitOnLastWindowClosed())

    def test_log_out_closes_graphite_the_ordinary_way_before_its_command(self):
        fake=FakeLogind(session='c2',at_run=self.at_run)
        with patch.object(power,'system',fake),patch.object(power,'_end') as ended:result=power.run_action(self.w,'logout',platform='linux')
        self.assertEqual(result['state'],'STARTED');self.assertEqual(fake.runs,[('loginctl','terminate-session','c2')])
        seen=fake.seen;self.assertFalse(seen['visible'],seen);self.assertTrue(seen['closing'],seen)
        for step in ('capture','pause_all','shutdown','brain.stop','save_session'):self.assertIn(step,seen['done'],(step,seen['done']))
        self.assertTrue(seen['session_saved'] and not seen['lease'] and seen['quit_held'],seen)
        ended.assert_called_once_with(self.app);self.assertTrue(self.app.quitOnLastWindowClosed())

    def test_cancel_at_the_confirmation_stops_nothing(self):
        from PySide6.QtWidgets import QMessageBox
        fake=FakeLogind()
        with patch.object(power,'system',fake),patch.object(QMessageBox,'question',return_value=QMessageBox.Cancel):result=power.run_action(self.w,'restart',platform='linux')
        self.assertEqual((result['state'],result['step']),('CANCELLED','confirm'));self.assertEqual(fake.runs,[])
        self.assertTrue(self.w.isVisible() and not getattr(self.w,'_closing',False))
        self.assertEqual([d for d in self.done if d in ('brain.stop','_kill_command_tree','capture','pause_all','release_all','shutdown','save_session')],[],self.done)
        self.assertIn('nothing was stopped',self.w.statusBar().currentMessage())


class MenuTests(unittest.TestCase):
    """The System menu and the programs list on a bare host: the order, the scope words, availability, Stop all jobs, Game, the
    services' rules, and Symmetry rule 6's placement and width."""
    def setUp(self):
        app();temporary=tempfile.TemporaryDirectory(prefix='graphite-system-menu-');self.addCleanup(temporary.cleanup)
        base=Path(temporary.name);self.root=base/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(base/'profile'),'ARC_LEDGER_CONCERN':str(base/'Concern')});env.start();self.addCleanup(env.stop)
        os.environ.pop('ARC_LEDGER_XSESSION',None)
        self.kernel=Kernel(self.root);session=Session(base/'profile/session.json',self.root);session.save();ledger_control.bind(self.kernel,session)
        self.fake=FakeLogind(reboot='yes',poweroff='na');p=patch.object(power,'system',self.fake);p.start();self.addCleanup(p.stop)

    def window(self):
        from PySide6.QtCore import QObject,Signal
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QWidget
        class Life(QObject):
            changed=Signal(object)
            def __init__(self):super().__init__();self.state=dict(phase='ON',admission_enabled=True,work_held=False,summary='New work enabled');self.requests=[]
            def refresh(self):self.changed.emit(self.state)
            def request(self,key):self.requests.append(key)
        host=QWidget();host.root=self.root;host.ledger_bridge=SimpleNamespace(kernel=self.kernel);host.reading_profile={};host._closing=False
        host.messages=[];host.statusBar=lambda:SimpleNamespace(showMessage=lambda text,*a:host.messages.append(text))
        host.a_master_stop=QAction('Master stop',host);host.stops=[];host.a_master_stop.triggered.connect(lambda:host.stops.append(1))
        host.life=Life();host.type_bar=SimpleNamespace(hatch=SimpleNamespace(lifecycle=host.life))
        self.addCleanup(host.deleteLater);return host

    def menu(self,host=None):
        from workbench.system_menu_qt import SystemMenu
        host=host or self.window();menu=SystemMenu(host,None);self.addCleanup(menu.deleteLater);return menu,host

    def settle(self):
        from PySide6.QtTest import QTest
        for _ in range(3):app().processEvents();QTest.qWait(10)

    def test_the_system_menus_order_scope_words_and_availability(self):
        menu,host=self.menu()
        self.assertEqual(self.fake.requests,[],'building the menu asks the system nothing (D2-fix): logind is asked when it opens')
        menu.fill()
        self.assertEqual(menu.words(),['Game','Stop all jobs','—','processes','—','Graphite services','—','Log out','Exit Graphite','Restart','Shut down'])
        self.assertIs(menu.items()[0],menu.game,'Game first');self.assertIs(menu.items()[1],menu.kill,'Stop all jobs directly beneath')
        self.assertEqual(menu.kill.caption,'work Graphite manages');self.assertIn('Programs Graphite does not manage keep running',menu.kill.toolTip())
        rows=menu.session_rows
        self.assertEqual({k:r.caption for k,r in rows.items()},{'logout':'this login session','leave':'this Graphite session','restart':'this computer','shutdown':'this computer · unavailable'})
        self.assertEqual({k:r.unavailable for k,r in rows.items()},{'logout':'','leave':'','restart':'','shutdown':'Shut down is unavailable: this computer does not offer it (logind: na).'})
        self.assertTrue(all(r.isEnabled() for r in rows.values()),'an unavailable row stays reachable: it says why')
        self.assertIn('logind: na',rows['shutdown'].toolTip());self.assertIn('Scope: this computer.',rows['restart'].toolTip())
        self.assertIn('First Graphite asks about your open work',rows['restart'].toolTip());self.assertIn('Nothing is stopped before you confirm',rows['restart'].toolTip())
        self.assertEqual(self.fake.runs,[],'opening and reading start nothing')
        with patch.dict(os.environ,{'ARC_LEDGER_XSESSION':'1'}):dedicated,_=self.menu()
        self.assertEqual(dedicated.session_rows['leave'].word,'Return to Debian');self.assertIn('Debian text login',dedicated.session_rows['leave'].toolTip())
        with patch.object(power,'system',FakeLogind(session=None)):menu.availability()
        self.assertTrue(all(rows[k].unavailable.startswith(power.NO_SESSION) and rows[k].caption.endswith('· unavailable') for k in power.ACTIONS));self.assertFalse(rows['leave'].unavailable)
        self.assertIn('No login session',rows['restart'].toolTip())

    def test_an_unavailable_row_says_why_to_the_keyboard_and_a_screen_reader(self):
        """D2-fix (the review: the reason could be read only from a hovered tooltip; the keyboard skipped the rows, F1 could not
        reach them, the accessible description had no reason): the rows stay in the keyboard's order, F1 reads the whole reason,
        the accessible description carries it, and choosing one says why in a dialog and issues nothing."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        menu,host=self.menu();host.resize(1366,768);menu.open_menu(keyboard=True);self.settle()
        rows=menu.session_rows;self.assertIn(rows['shutdown'],menu.focusables())
        QTest.keyClick(QApplication.focusWidget(),Qt.Key_End);self.settle();self.assertIs(QApplication.focusWidget(),rows['shutdown'],'End reaches the last row, unavailable or not')
        QTest.keyClick(rows['shutdown'],Qt.Key_F1);self.settle()
        self.assertTrue(host.messages[-1].startswith('Shut down · this computer · unavailable'),host.messages[-1]);self.assertIn('Unavailable: Shut down is unavailable: this computer does not offer it (logind: na).',host.messages[-1])
        self.assertIn('Unavailable: Shut down is unavailable: this computer does not offer it (logind: na).',rows['shutdown'].accessibleDescription())
        self.assertNotIn('Unavailable',rows['restart'].accessibleDescription())
        told=[]
        with patch.object(power,'tell',side_effect=lambda h,title,text:told.append((title,text))):QTest.keyClick(rows['shutdown'],Qt.Key_Return);self.settle()
        self.assertEqual(told[0][0],'Shut down is unavailable');self.assertIn('logind: na',told[0][1]);self.assertEqual(self.fake.runs,[])
        self.assertFalse(any(r[0]=='where' for r in self.fake.requests),'refused before anything else')

    def test_a_resting_pointer_takes_no_row_until_it_moves(self):
        """D2-fix (found when the unavailable rows became reachable: check_desk_ui's pointer rested where Restart opens and took the
        keyboard's first row): as a QMenu does, a pointer resting where the menu opens takes no row; its first movement does."""
        from PySide6.QtCore import QPoint
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        menu,host=self.menu();menu.open_menu(keyboard=True);self.settle();restart=menu.session_rows['restart'];shutdown=menu.session_rows['shutdown']
        QTest.mouseMove(restart,restart.rect().center());self.settle();QTest.mouseMove(restart,restart.rect().center()+QPoint(4,0));self.settle()
        self.assertIs(QApplication.focusWidget(),restart,'a moving pointer takes its row')
        menu.close_menu();self.settle();menu.open_menu(keyboard=True);self.settle()
        self.assertIs(QApplication.focusWidget(),menu.game,'the pointer rests over Restart: the keyboard\'s first row keeps its focus')
        self.assertFalse(restart.active(),'and the resting pointer\'s row is not washed')
        QTest.mouseMove(shutdown,shutdown.rect().center());self.settle();self.assertIs(QApplication.focusWidget(),shutdown,'its first movement takes the row')

    def test_the_services_restart_names_its_scope_when_read_without_its_row(self):
        """D2-fix (the review: two words Restart, the services' and the computer's): the services' choice reads 'Graphite services:
        Restart' to F1, a screen reader and the keyboard's order; the computer's row reads Restart · this computer."""
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        menu,host=self.menu();menu.open_menu(keyboard=True);self.settle();restart=menu.service_actions['Reboot']
        self.assertEqual((restart.text(),restart.word,restart.accessibleName()),('Restart','Graphite services: Restart','Graphite services: Restart'))
        restart.setFocus(Qt.TabFocusReason);self.settle();QTest.keyClick(restart,Qt.Key_F1);self.settle()
        self.assertTrue(host.messages[-1].startswith('Graphite services: Restart — '),host.messages[-1]);self.assertIn('The computer is not restarted',host.messages[-1])
        self.assertTrue(menu.descriptor(menu.session_rows['restart']).startswith('Restart · this computer'))

    def test_order_and_niceness_are_distinct_controls_in_the_process_list(self):
        for title in ('First','Second'):self.kernel.dispatch('agenda.add',{'title':title,'program':'@files:x.txt','nice':'normal'},operator())
        menu,host=self.menu();menu.work.refresh()
        from PySide6.QtWidgets import QLabel,QSlider
        self.assertEqual(menu.queue.count(),2)
        for i in range(2):
            widget=menu.queue.itemWidget(menu.queue.item(i))
            place=widget.findChild(QLabel,'QueuePlace');self.assertEqual(place.text(),str(i+1));self.assertIn('Order:',place.toolTip())
            slider=widget.findChild(QSlider);self.assertIn('left more urgent, right nicer',slider.accessibleName());self.assertIn('Agenda tier',slider.accessibleName())
        self.assertEqual((menu.earlier.text(),menu.later.text()),('↑ Earlier','↓ Later'));self.assertIn('They are separate',menu.earlier.toolTip())
        self.assertTrue(menu.work.section and menu.work.kill.isHidden() and not hasattr(menu.work,'game'),'its Stop and Game are the menu\'s own rows')

    def test_stop_all_jobs_reaches_the_master_stop_and_game_opens_struthio(self):
        menu,host=self.menu();menu.open_menu(keyboard=True);self.settle()
        from PySide6.QtWidgets import QApplication
        self.assertIs(QApplication.focusWidget(),menu.game,'a keyboard opening starts at the first row')
        menu.kill.click();self.settle()
        self.assertEqual(host.stops,[1]);self.assertFalse(menu.isVisible(),'the menu gets out of the way of the confirm dialog')
        from workbench import struthio_qt
        with patch.object(struthio_qt,'show') as game:menu.open_menu();self.settle();menu.game.click();self.settle()
        game.assert_called_once_with(host)

    def test_graphite_services_follow_the_cycles_rules(self):
        menu,host=self.menu();on,off,restart=(menu.service_actions[k] for k in ('On','Off','Reboot'))
        self.assertEqual([c.text() for c in menu.services.choices],['On','Off','Restart'])
        self.assertFalse(on.isEnabled());self.assertTrue(off.isEnabled() and restart.isEnabled())
        menu.render_services(dict(phase='ON',admission_enabled=False,work_held=True,summary='New work held'));self.assertTrue(on.isEnabled())
        menu.render_services(dict(phase='OFF',admission_enabled=False,work_held=True,summary='Off'));self.assertFalse(off.isEnabled());self.assertIn('already off',off.toolTip())
        menu.render_services(dict(phase='DRAINING',admission_enabled=True,work_held=False,summary='Draining'));self.assertFalse(any(c.isEnabled() for c in (on,off,restart)))
        menu.render_services(dict(phase='ON',admission_enabled=True,work_held=False,summary='New work enabled'))
        self.assertIn('The computer is not restarted',restart.toolTip());self.assertIn('never on the computer',menu.services.toolTip())
        restart.click();self.settle();self.assertEqual(host.life.requests,['Reboot'],'Restart is the services\' existing Reboot cycle')

    def test_the_session_rows_go_through_session_power(self):
        menu,host=self.menu();menu.fill()
        with patch.object(power,'run_action') as run,patch.object(power,'leave') as leave:
            for key in ('logout','restart','shutdown'):menu.session_rows[key].click();self.settle()
            menu.session_rows['leave'].click();self.settle()
        self.assertEqual([c.args[1] for c in run.call_args_list],['logout','restart','shutdown']);leave.assert_called_once_with(host)
        told=[]
        with patch.object(power,'tell',side_effect=lambda h,title,text:told.append(title)):menu.session_rows['shutdown'].click();self.settle()
        self.assertEqual(told,['Shut down is unavailable']);self.assertEqual(self.fake.runs,[],'an unavailable row only says why')

    def test_the_two_menus_are_point_mirror_images(self):
        """Symmetry rule 6 by numbers: the same inset from the side edge, the same band from the top or the bottom, one width,
        one row height, one icon column."""
        from PySide6.QtCore import QPoint
        from workbench import programs_qt,desk_qt
        host=self.window();host.resize(1366,768)
        host.desk=desk_qt.desk(1366,1.0,22);host.ribbon_dock=SimpleNamespace(height=lambda:host.desk.band,isVisible=lambda:True);host.type_dock=host.ribbon_dock
        class Probe:
            def sizeHint(self):from PySide6.QtCore import QSize;return QSize(10,500)
        lower=programs_qt.place(host,Probe(),'lower-left');upper=programs_qt.place(host,Probe(),'upper-right');origin=host.mapToGlobal(QPoint(0,0))
        d=host.desk
        self.assertEqual(lower.x()-origin.x(),d.inset);self.assertEqual(origin.x()+1366-(upper.x()+upper.width()),d.inset)
        self.assertEqual(origin.y()+768-(lower.y()+lower.height()),d.band);self.assertEqual(upper.y()-origin.y(),d.band)
        self.assertEqual(lower.size(),upper.size());self.assertEqual(lower.width(),programs_qt.menu_width(host))
        from workbench.system_menu_qt import words_need
        m=programs_qt.metrics(host);self.assertEqual(programs_qt.menu_width(host),max(d.pane-2*d.inset,programs_qt.programs_need(m),words_need(m)))
        self.assertEqual(programs_qt.menu_width(host),d.pane-2*d.inset,'the panes\' content column at 14 pt')
        tall=SimpleNamespace(sizeHint=lambda:__import__('PySide6.QtCore',fromlist=['QSize']).QSize(10,5000))
        self.assertEqual(programs_qt.place(host,tall,'lower-left').height(),768-2*d.band,'never over either band')

    def test_the_programs_list_and_the_system_menu_share_their_numbers(self):
        from workbench.hatch_qt import HatchButton
        menu,host=self.menu();host.tabs=SimpleNamespace(currentWidget=lambda:None,count=lambda:0,widget=lambda i:None);host.cabinet_page=None
        cat=HatchButton(host);cat.lifecycle.timer.stop();self.addCleanup(cat.deleteLater)
        programs=cat.programs;self.assertIs(programs.m,programs.m);self.assertEqual(programs.m,menu.m)
        rows=programs.rows()+menu.rows()
        self.assertEqual({r.sizeHint().height() for r in rows},{menu.m.row},'one row height')
        self.assertEqual({(r.icon_rect().x(),r.icon_rect().width(),r.word_x()) for r in rows},{(menu.m.pad,menu.m.icon,menu.m.pad+menu.m.icon_col)},'one icon column')
        for m in (programs,menu):m.adjustSize();m.page.adjustSize()
        self.assertEqual({programs.top_margin.sizeHint().height(),programs.bottom_margin.sizeHint().height(),menu.top_margin.sizeHint().height(),menu.bottom_margin.sizeHint().height()},{menu.m.margin})
        self.assertEqual((programs.box.itemAt(0).widget(),menu.box.itemAt(menu.box.count()-1).widget()),(programs.top_margin,menu.bottom_margin))
        self.assertIsInstance(programs.items()[0],type(menu.caption),'the caption at the far end: the list\'s top')
        self.assertIs(menu.items()[-1],menu.caption,'and the System menu\'s foot')


class CatColourTests(unittest.TestCase):
    """The owner's colours carry the cat's state; the coat is the band's brightest value, a step above its lettering."""
    def setUp(self):app()

    def test_the_colours_are_named_constants_and_the_coat_is_warm_paper(self):
        from workbench import graphite_brand as g,shell2,desk_qt
        self.assertEqual((g.CAT_COAT,g.CAT_DETAIL,g.CAT_IRIS,g.CAT_NOSE,g.CAT_FOCUS),(shell2.CARD,shell2.TEXT,shell2.AMBER_EDGE,shell2.ERASER_MARK,shell2.ERASER_MARK))
        self.assertNotEqual(g.CAT_COAT.lower(),'#ffffff','warm paper, never a cold white')
        rgb=lambda c:tuple(int(c[i:i+2],16) for i in (1,3,5));mean=desk_qt.grain_report()['mean_tone']
        coat=desk_qt.contrast(rgb(g.CAT_COAT),mean);letters=desk_qt.contrast(rgb(desk_qt.ERASED),mean)
        self.assertGreaterEqual(coat,9.0);self.assertGreater(coat,letters)
        self.assertGreater(sum(rgb(g.CAT_COAT)),sum(rgb(desk_qt.ERASED)),'brighter than the band\'s lettering')

    def test_yellow_irises_only_when_awake_to_you(self):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QColor,QImage,QPainter
        from workbench import graphite_brand as g
        f=lambda pose:dict(zip(g.FIELDS,g.POSES[pose]))
        self.assertEqual([f(p)['iris'] for p in ('rest','hover','open','sleepy')],[0,1,1,0])
        def colours(pose):
            image=QImage(208,108,QImage.Format_ARGB32);image.fill(QColor('#4a4741'));p=QPainter(image);g.paint_cat(p,QRectF(0,0,208,108),g.POSES[pose]);p.end()
            yellow=QColor(g.CAT_IRIS);pink=QColor(g.CAT_NOSE);coat=QColor(g.CAT_COAT);counts=dict(yellow=0,pink=0,coat=0)
            for y in range(108):
                for x in range(208):
                    c=image.pixelColor(x,y)
                    for name,ref in (('yellow',yellow),('pink',pink),('coat',coat)):
                        if abs(c.red()-ref.red())+abs(c.green()-ref.green())+abs(c.blue()-ref.blue())<=12:counts[name]+=1
            return counts
        seen={pose:colours(pose) for pose in g.POSES}
        self.assertEqual(seen['rest']['yellow'],0);self.assertEqual(seen['sleepy']['yellow'],0)
        self.assertGreater(seen['hover']['yellow'],60);self.assertGreater(seen['open']['yellow'],60)
        self.assertTrue(all(seen[p]['pink']>40 for p in g.POSES),seen)
        self.assertTrue(all(seen[p]['coat']>3000 for p in g.POSES),seen)
        self.assertEqual(g.mix('#000000','#ffffff',0.5).name(),'#808080')


if __name__=='__main__':unittest.main()
