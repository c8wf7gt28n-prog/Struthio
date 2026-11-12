"""Host boundaries and owned-runner cleanup, without inference or native Office."""
import contextlib,hashlib,io,json,os,sqlite3,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import hatch_readiness as r


class ReadinessTests(unittest.TestCase):
    def test_registry_selection_is_read_only_and_missing_workspace_stays_absent(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)/'workspace';self.assertIsNone(r.selected_model(root));self.assertFalse(root.exists())
            state=root/'.ledger';state.mkdir(parents=True);database=state/'engineering.sqlite3'
            with contextlib.closing(sqlite3.connect(database)) as db, db:
                db.execute('CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)')
                db.execute('INSERT INTO settings VALUES(?,?)',('brain.selection',json.dumps({'model_id':'abc'})))
                db.execute('INSERT INTO settings VALUES(?,?)',('brain.model.abc',json.dumps({'files':[{'path':'/external/reference.gguf'}]})))
            before=database.read_bytes();self.assertEqual(r.selected_model(root),Path('/external/reference.gguf'));self.assertEqual(database.read_bytes(),before)

    def test_model_pin_rejects_a_different_file_and_accepts_only_matching_test_identity(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)/'sample.gguf';self.assertFalse(r.model_probe(path)['ready']);path.write_bytes(b'GGUF synthetic test bytes')
            self.assertEqual(r.model_probe(path)['state'],'DIFFERENT_MODEL')
            with patch.object(r,'REFERENCE_SHA',hashlib.sha256(path.read_bytes()).hexdigest()):
                self.assertEqual(r.model_probe(path)['state'],'REFERENCE_HASH_VERIFIED')

    def test_blocked_trial_does_not_launch_or_create_fixture(self):
        with tempfile.TemporaryDirectory() as name,patch.object(r.subprocess,'Popen') as process:
            folder=Path(name)
            report={'gates':{'model':{'ready':False,'blockers':['reference_model']},'visible_calc':{'ready':False,'blockers':['connectable_x11']}}}
            for mode in r.MODES:self.assertEqual(r.run_trial(mode,report,folder,1)['state'],'BLOCKED_BEFORE_LAUNCH')
            process.assert_not_called();self.assertEqual(list(folder.iterdir()),[])

    def test_runtime_requires_actual_archive_hash_and_recorded_commit(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);archive=(root/r.brain_runtime.PIN).parent/'runtime.bin';archive.parent.mkdir(parents=True);archive.write_bytes(b'synthetic runtime identity')
            sha=hashlib.sha256(archive.read_bytes()).hexdigest()
            status={'state':'PINNED_CPU_AVAILABLE','build':r.REFERENCE_BUILD,'source_commit':r.REFERENCE_COMMIT,'platform':'linux-x64',
                'pin':{'platforms':{'linux-x64':{'archive':'runtime.bin','sha256':sha}}}}
            with patch.object(r,'ROOT',root),patch.object(r,'REFERENCE_RUNTIME_SHA',sha),patch.object(r.brain_runtime,'status',return_value=status):
                self.assertTrue(r.runtime_probe()['reference_match']);archive.write_bytes(b'changed')
                self.assertFalse(r.runtime_probe()['reference_match'])

    def test_ready_gate_cannot_launch_into_insufficient_trial_disk_space(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as name,patch.object(r.shutil,'disk_usage',return_value=SimpleNamespace(free=0)),patch.object(r.subprocess,'Popen') as process:
            result=r.run_trial('visible-calc',{'gates':{'visible_calc':{'ready':True}}},Path(name),600)
            self.assertEqual(result['state'],'BLOCKED_BEFORE_LAUNCH');process.assert_not_called()

    def test_unconfirmed_descendant_exit_requires_cleanup_even_when_job_table_is_clear(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as name,patch.object(r.shutil,'disk_usage',return_value=SimpleNamespace(free=2*1024**3)),patch.object(r,'supervise',return_value={'state':'BUDGET_EXHAUSTED','runner_descendants_gone':False}),patch.object(r,'cleanup_trial',return_value={'state':'CONFIRMED'}):
            report={'gates':{'model':{'ready':True}},'parts':{'model':{'path':'synthetic-unused-model-path'}}}
            result=r.run_trial('model-diagnostic',report,Path(name),600)
            self.assertEqual(result['state'],'CLEANUP_REQUIRED');self.assertFalse(result['acceptance_promoted'])

    def test_offscreen_is_not_visible_readiness_even_with_display_variable(self):
        with patch.dict(os.environ,{'DISPLAY':':99','QT_QPA_PLATFORM':'offscreen'}),patch.object(r.subprocess,'run') as child:
            self.assertFalse(r.display_probe()['ready']);child.assert_not_called()

    def test_full_family_requires_declared_budget_before_collecting(self):
        with patch.object(r,'collect') as collect,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:r.main(['--run','model-family'])
            self.assertEqual(error.exception.code,2);collect.assert_not_called()

    def test_linked_cleanup_target_is_refused(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);outside=root/'outside';(outside/'.ledger').mkdir(parents=True)
            data=outside/'.ledger/engineering.sqlite3';data.write_bytes(b'untouched')
            trial=root/'trial';trial.mkdir();(trial/'Office').symlink_to(outside,target_is_directory=True)
            self.assertEqual(r.cleanup_trial(trial)['state'],'REFUSED_LINKED_FIXTURE');self.assertEqual(data.read_bytes(),b'untouched')

    @unittest.skipUnless(sys.platform.startswith('linux'),'Owned Linux process identities')
    def test_budget_stops_owned_descendant_and_preserves_unrelated_process(self):
        from workbench.operation_stop import process_identity
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name);record=folder/'child.json'
            code="import signal,time;signal.signal(signal.SIGINT,signal.SIG_IGN);time.sleep(30)"
            launcher='import subprocess,sys,signal,time,json;from pathlib import Path;signal.signal(signal.SIGINT,signal.SIG_IGN);p=subprocess.Popen([sys.executable,"-c",'+repr(code)+'],start_new_session=True);Path('+repr(str(record))+').write_text(json.dumps({"pid":p.pid}));time.sleep(30)'
            control=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
            try:
                result=r.supervise([sys.executable,'-c',launcher],folder,1)
                self.assertEqual(result['state'],'BUDGET_EXHAUSTED');self.assertTrue(result['runner_descendants_gone'])
                self.assertIsNone(process_identity(json.loads(record.read_text())['pid']));self.assertIsNone(control.poll())
            finally:control.terminate();control.wait(timeout=3)


if __name__=='__main__':unittest.main()
