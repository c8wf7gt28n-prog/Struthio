"""Startup scripts: dedicated-session marker and exit-status readback, argument refusal, X server check, launch error log placement.

Everything runs against copies of the scripts in disposable folders with stub fluxbox, startx and
START_OFFICE.sh; no X server, window manager or Ledger window is started. The root refusals stay in the
scripts: when the suite itself runs as root, the root-refusing script is exercised as uid 1000 through
setpriv (skipped when that is not possible).
"""
import contextlib,io,json,os,pwd,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=('LS_XSESSION.sh','START_MINIMAL_DEBIAN.sh','START_OFFICE.sh','INSTALL_DEBIAN.sh','INSTALL_LEDGER.sh','LEDGER.sh','START_LEDGER.sh','HATCH_CHECK.sh')
UID=1000
SYSTEM_PATH='/usr/local/bin:/usr/bin:/bin'
OFFICE_STUB='''#!/usr/bin/env bash
echo "office pid=$$ XSESSION=${ARC_LEDGER_XSESSION:-unset} FULLSCREEN=${ARC_LEDGER_FULLSCREEN:-unset} args=$*" >> "$STUB_LOG"
if [[ -n "${STUB_WRITE_LOG:-}" ]]; then mkdir -p "$(dirname "$STUB_WRITE_LOG")"; echo traceback > "$STUB_WRITE_LOG"; fi
exit "${STUB_EXIT:-0}"
'''
FLUXBOX_STUB='''#!/usr/bin/env bash
echo "$$" > "$STUB_FLUXPID"; echo "fluxbox args: $*" >> "$STUB_LOG"; trap 'echo "fluxbox got TERM" >> "$STUB_LOG"; exit 0' TERM; while :; do sleep 0.2; done
'''
STARTX_STUB='''#!/usr/bin/env bash
echo "startx args: $*" >> "$STUB_LOG"
if [[ -n "${STUB_RECORD:-}" ]]; then mkdir -p "$XDG_STATE_HOME/ledger-slate"; printf '%s\\n' "$STUB_RECORD" > "$XDG_STATE_HOME/ledger-slate/last-session.json"; fi
exit "${STUB_STARTX_RC:-0}"
'''


def stub(path,body):
    path.write_text(body);path.chmod(0o755);return path


class StartupScriptTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='ledger-startup-');self.addCleanup(temp.cleanup);self.base=Path(temp.name)
        self.prog=self.base/'prog';self.bin=self.base/'bin';self.home=self.base/'home';self.state=self.base/'state'
        for folder in (self.prog,self.bin,self.home,self.state):folder.mkdir()
        for name in ('LS_XSESSION.sh','START_MINIMAL_DEBIAN.sh'):shutil.copy(ROOT/name,self.prog/name);(self.prog/name).chmod(0o755)
        stub(self.prog/'START_OFFICE.sh',OFFICE_STUB);stub(self.bin/'fluxbox',FLUXBOX_STUB);stub(self.bin/'startx',STARTX_STUB)
        for name in ('dbus-run-session','Xorg'):stub(self.bin/name,'#!/usr/bin/env bash\nexit 0\n')
        self.log=self.base/'log.txt';self.record=self.state/'ledger-slate'/'last-session.json'

    def environment(self,**extra):
        env=dict(PATH=str(self.bin)+':'+SYSTEM_PATH,HOME=str(self.home),XDG_STATE_HOME=str(self.state),STUB_LOG=str(self.log),STUB_FLUXPID=str(self.base/'flux.pid'))
        env.update({k:str(v) for k,v in extra.items()});return env

    def run_script(self,name,*args,**extra):
        return subprocess.run(['bash',str(self.prog/name),*args],env=self.environment(**extra),capture_output=True,text=True,timeout=60,stdin=subprocess.DEVNULL)

    def run_unprivileged(self,name,*args,**extra):
        """START_MINIMAL_DEBIAN.sh refuses root, so under a root test run it is exercised as uid 1000; otherwise it simply runs."""
        command=['bash',str(self.prog/name),*args]
        if os.geteuid()==0:
            try:pwd.getpwuid(UID)
            except KeyError:self.skipTest('uid %d does not exist on this host'%UID)
            if not shutil.which('setpriv'):self.skipTest('setpriv is not available to drop privileges')
            os.chmod(self.base,0o755)
            for path in self.base.rglob('*'):os.chown(path,UID,UID)
            os.chown(self.base,UID,UID)
            probe=subprocess.run(['setpriv','--reuid=%d'%UID,'--regid=%d'%UID,'--clear-groups','test','-r',str(self.prog/name)],timeout=30)
            if probe.returncode!=0:self.skipTest('uid %d cannot traverse the temporary folder (TMPDIR chain is private)'%UID)
            command=['setpriv','--reuid=%d'%UID,'--regid=%d'%UID,'--clear-groups']+command
        return subprocess.run(command,env=self.environment(**extra),capture_output=True,text=True,timeout=60,stdin=subprocess.DEVNULL)

    def logged(self):
        return self.log.read_text() if self.log.exists() else ''

    def test_every_startup_script_parses(self):
        for name in SCRIPTS:
            result=subprocess.run(['bash','-n',str(ROOT/name)],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,name+': '+result.stderr)

    def test_dedicated_session_marker_is_exported_only_by_the_session_client(self):
        session=(ROOT/'LS_XSESSION.sh').read_text();minimal=(ROOT/'START_MINIMAL_DEBIAN.sh').read_text()
        self.assertIn('ARC_LEDGER_XSESSION=1',session);self.assertIn('ARC_LEDGER_FULLSCREEN=1',session)
        self.assertNotIn('ARC_LEDGER_XSESSION',minimal);self.assertIn('export ARC_LEDGER_FULLSCREEN=1',minimal)
        self.assertNotIn('exec startx',minimal);self.assertIn('last-session.json',minimal)
        quick=(ROOT/'INSTALL_LEDGER.sh').read_text()
        self.assertIn('Minimal session prerequisites not found',quick);self.assertIn('command -v Xorg',quick)

    def test_session_client_runs_office_once_propagates_status_terminates_fluxbox_and_records(self):
        for status in (0,3):
            with self.subTest(status=status):
                self.log.unlink(missing_ok=True)
                result=self.run_script('LS_XSESSION.sh',DISPLAY=':0',DBUS_SESSION_BUS_ADDRESS='stub',STUB_EXIT=status)
                self.assertEqual(result.returncode,status,result.stderr)
                lines=self.logged().splitlines()
                office=[line for line in lines if line.startswith('office ')]
                self.assertEqual(len(office),1,lines);self.assertIn('XSESSION=1 FULLSCREEN=1 args=',office[0])
                self.assertIn('fluxbox args: -no-slit -no-toolbar',lines);self.assertIn('fluxbox got TERM',lines)
                pid=int((self.base/'flux.pid').read_text())
                with self.assertRaises(ProcessLookupError):os.kill(pid,0)
                record=json.loads(self.record.read_text())
                self.assertEqual(record['status'],status);self.assertIsNone(record['log']);self.assertRegex(record['utc'],r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')

    def test_session_client_names_only_a_launch_error_log_from_this_session(self):
        log=self.state/'ledger-slate'/'launch-error.log'
        result=self.run_script('LS_XSESSION.sh',DISPLAY=':0',DBUS_SESSION_BUS_ADDRESS='stub',STUB_EXIT=1,STUB_WRITE_LOG=log)
        self.assertEqual(result.returncode,1);record=json.loads(self.record.read_text())
        self.assertEqual(record['status'],1);self.assertEqual(record['log'],str(log))
        stale=log.stat().st_mtime-30;os.utime(log,(stale,stale)) # The same file from an earlier session is not this session's record.
        result=self.run_script('LS_XSESSION.sh',DISPLAY=':0',DBUS_SESSION_BUS_ADDRESS='stub',STUB_EXIT=0)
        self.assertEqual(result.returncode,0);record=json.loads(self.record.read_text());self.assertEqual(record['status'],0);self.assertIsNone(record['log'])

    def test_session_client_exit_status_survives_an_unrecordable_state_folder(self):
        blocker=self.base/'blocker';blocker.write_text('a file, not a folder') # mkdir -p fails here for every uid, root included.
        result=self.run_script('LS_XSESSION.sh',DISPLAY=':0',DBUS_SESSION_BUS_ADDRESS='stub',STUB_EXIT=3,XDG_STATE_HOME=blocker/'state')
        self.assertEqual(result.returncode,3,result.stderr);self.assertFalse(self.record.exists());self.assertIn('fluxbox got TERM',self.logged())

    def test_session_client_requires_a_display(self):
        result=self.run_script('LS_XSESSION.sh');self.assertEqual(result.returncode,1);self.assertIn('text login',result.stderr);self.assertEqual(self.logged(),'')

    def test_text_login_start_reads_back_the_recorded_status_and_exits_with_it(self):
        record=json.dumps(dict(status=3,utc='2026-11-03T00:00:00Z',log=str(self.state/'ledger-slate'/'launch-error.log')))
        result=self.run_unprivileged('START_MINIMAL_DEBIAN.sh',STUB_RECORD=record)
        self.assertEqual(result.returncode,3,result.stderr);self.assertIn('Graphite ended with status 3 · details: '+str(self.state/'ledger-slate'/'launch-error.log'),result.stdout)
        self.assertIn('startx args: '+str(self.prog/'LS_XSESSION.sh')+' --',self.logged())
        result=self.run_unprivileged('START_MINIMAL_DEBIAN.sh',STUB_RECORD=json.dumps(dict(status=0,utc='2026-11-03T00:00:00Z',log=None)))
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('Graphite ended with status 0\n',result.stdout);self.assertNotIn('details',result.stdout)

    def test_text_login_start_removes_a_stale_record_and_says_when_nothing_was_recorded(self):
        self.record.parent.mkdir(parents=True);self.record.write_text(json.dumps(dict(status=7,utc='old',log=None)))
        result=self.run_unprivileged('START_MINIMAL_DEBIAN.sh')
        self.assertEqual(result.returncode,1);self.assertIn('status not recorded (startx returned 0)',result.stderr);self.assertNotIn('status 7',result.stdout+result.stderr)
        result=self.run_unprivileged('START_MINIMAL_DEBIAN.sh',STUB_STARTX_RC=5)
        self.assertEqual(result.returncode,5);self.assertIn('startx returned 5',result.stderr)
        result=self.run_unprivileged('START_MINIMAL_DEBIAN.sh',STUB_RECORD='{"status":"not a number"}')
        self.assertEqual(result.returncode,1);self.assertIn('status not recorded',result.stderr)

    def test_text_login_start_refuses_arguments_and_names_the_desktop_route(self):
        result=self.run_unprivileged('START_MINIMAL_DEBIAN.sh','--doctor')
        self.assertEqual(result.returncode,1);self.assertIn('takes no arguments (got: --doctor)',result.stderr);self.assertIn('START_OFFICE.sh --doctor',result.stderr)
        self.assertEqual(self.logged(),'') # neither startx nor the Office stub ran

    def test_existing_display_branch_forwards_arguments_without_the_marker_or_startx(self):
        result=self.run_unprivileged('START_MINIMAL_DEBIAN.sh','--version',DISPLAY=':0')
        self.assertEqual(result.returncode,0,result.stderr);lines=self.logged().splitlines()
        self.assertEqual(len(lines),1);self.assertIn('XSESSION=unset FULLSCREEN=1 args=--version',lines[0])

    def test_text_login_start_checks_the_session_commands_and_an_x_server(self):
        # Keep real X servers outside the stub PATH even on a graphical host.
        for command in ('bash','dirname','rm','mkdir','python3','setpriv'):
            system_command=shutil.which(command,path=SYSTEM_PATH)
            if system_command:(self.bin/command).symlink_to(system_command)
        environment=dict(PATH=str(self.bin))
        (self.bin/'Xorg').unlink()
        result=self.run_unprivileged('START_MINIMAL_DEBIAN.sh',**environment);self.assertEqual(result.returncode,1);self.assertIn('Missing an X server (Xorg)',result.stderr);self.assertEqual(self.logged(),'')
        stub(self.bin/'X','#!/usr/bin/env bash\nexit 0\n') # the X wrapper name is accepted too
        result=self.run_unprivileged('START_MINIMAL_DEBIAN.sh',STUB_RECORD=json.dumps(dict(status=0,utc='x',log=None)),**environment);self.assertEqual(result.returncode,0,result.stderr)
        (self.bin/'startx').unlink()
        result=self.run_unprivileged('START_MINIMAL_DEBIAN.sh',**environment);self.assertEqual(result.returncode,1);self.assertIn('Missing startx',result.stderr)

    def test_root_is_still_refused_by_the_text_login_start(self):
        if os.geteuid()!=0:self.skipTest('the suite is not running as root; the refusal text is checked instead')
        result=self.run_script('START_MINIMAL_DEBIAN.sh');self.assertEqual(result.returncode,1);self.assertIn('not root',result.stderr);self.assertEqual(self.logged(),'')

    def test_debian_entry_point_reports_skipped_prerequisites_with_exit_3(self):
        if not Path('/etc/debian_version').is_file() or not shutil.which('apt-get'):self.skipTest('INSTALL_DEBIAN.sh only runs on a Debian host')
        folder=self.base/'deb';folder.mkdir();shutil.copy(ROOT/'INSTALL_DEBIAN.sh',folder/'INSTALL_DEBIAN.sh')
        stub(folder/'INSTALL_LEDGER.sh','#!/usr/bin/env bash\necho "runtime installer args: $*"; exit "${STUB_LEDGER_RC:-0}"\n')
        def run(*args,rc=0):
            return subprocess.run(['bash',str(folder/'INSTALL_DEBIAN.sh'),*args],env=dict(PATH=SYSTEM_PATH,HOME=str(self.home),STUB_LEDGER_RC=str(rc)),capture_output=True,text=True,timeout=60,stdin=subprocess.DEVNULL)
        result=run('--quick','--minimal-session') # no --yes and no terminal: apt is skipped and said so
        self.assertEqual(result.returncode,3,result.stderr);self.assertIn('PREREQUISITES_SKIPPED',result.stdout);self.assertIn('System packages skipped (no --yes and no terminal',result.stdout)
        self.assertIn('runtime installer args: --quick\n',result.stdout);self.assertIn('xserver-xorg xinit fluxbox',result.stdout);self.assertNotIn('apt-get',result.stdout)
        result=run('--quick',rc=2);self.assertEqual(result.returncode,2);self.assertNotIn('PREREQUISITES_SKIPPED',result.stdout) # a runtime failure is not reported as skipped
        wheels=self.base/'wheels';wheels.mkdir()
        result=run('--quick','--offline',str(wheels));self.assertEqual(result.returncode,0);self.assertNotIn('PREREQUISITES_SKIPPED',result.stdout);self.assertIn('--offline '+str(wheels),result.stdout)
        result=run('--check-only');self.assertEqual(result.returncode,0);self.assertNotIn('PREREQUISITES_SKIPPED',result.stdout)

    def test_launch_error_log_prefers_the_state_folder_and_names_only_a_written_file(self):
        sys.path.insert(0,str(ROOT));self.addCleanup(lambda:sys.path.remove(str(ROOT)))
        import workbench.launch as launch
        self.assertEqual(launch.error_log_candidates({'XDG_STATE_HOME':str(self.state)})[0],self.state/'ledger-slate'/'launch-error.log')
        self.assertEqual(launch.error_log_candidates({'XDG_STATE_HOME':str(self.state)})[-1],launch.INSTALL.parent/'launch-error.log')
        blocker=self.base/'blocker';blocker.write_text('a file');unwritable=blocker/'state'/'launch-error.log';writable=self.state/'ledger-slate'/'launch-error.log'
        self.assertEqual(launch.write_error_log('trace',[unwritable,writable]),writable);self.assertEqual(writable.read_text(),'trace')
        self.assertIsNone(launch.write_error_log('trace',[unwritable]))
        alerts=[];cwd=os.getcwd();self.addCleanup(os.chdir,cwd)
        class Broken:
            @staticmethod
            def prepare(app):raise RuntimeError('fixture failure before any window')
        with patch.dict(os.environ,{'XDG_STATE_HOME':str(self.state)}),patch.dict(sys.modules,{'prepare_release':Broken}),patch.object(launch,'alert',lambda title,text:alerts.append((title,text))),contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(launch.main([]),1)
        self.assertEqual(alerts[0][0],'Graphite could not start');self.assertIn('Details: '+str(writable),alerts[0][1]);self.assertIn('fixture failure before any window',writable.read_text());self.assertIn('RuntimeError: fixture failure',err.getvalue())
        alerts.clear()
        with patch.dict(os.environ,{'XDG_STATE_HOME':str(blocker/'state')}),patch.dict(sys.modules,{'prepare_release':Broken}),patch.object(launch,'alert',lambda title,text:alerts.append((title,text))),patch.object(launch,'INSTALL',blocker/'install.json'),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launch.main([]),1)
        self.assertIn('No log file could be written',alerts[0][1]);self.assertNotIn('Details:',alerts[0][1])


if __name__=='__main__':unittest.main()
