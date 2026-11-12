"""Atomic service gates, stale-cycle refusal, controller lifetime and admission."""
import json,os,sqlite3,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,MagicMock
from workbench import service_lifecycle as services,ledger_control as control,settings_registry,work_trail
from workbench.engineering_kernel import Kernel,operator,Principal
from workbench.session import Session


class ServiceLifecycleTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name);self.root=self.base/'work';self.root.mkdir()
        env=patch.dict(os.environ,dict(ARC1_WORKBENCH_CONFIG_HOME=str(self.base/'profile'),ARC_LEDGER_CONCERN=str(self.base/'Concern')))
        env.start();self.addCleanup(env.stop);self.k=Kernel(self.root);self.p=operator('owner')
        s=Session(self.base/'profile/session.json',self.root);s.save();control.bind(self.k,s)
        self.leases=self.k.state/'desktops';self.leases.mkdir(exist_ok=True);self.lease=self.leases/'first.json';self.lease.write_text('{}')
        launch=patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch'));self.launch=launch.start();self.addCleanup(launch.stop)
    def begin(self,action='Off'):return services.begin(self.k,action,self.p,'first')
    def stop(self,receipt):return services.stop_gate(self.k,receipt,self.p)
    def start(self,receipt=None):return services.start(self.k,self.p,'first',receipt)
    def job(self,state='Running',**extra):
        row=dict(id='a'*32,owner=self.p.identity,state=state,tool='brain.infer',**extra);self.k.save('jobs',row);return row
    def setting(self,value):
        result=self.k.dispatch('ledger.settings.set',dict(key=services.ADMISSION,value=value),self.p);self.assertTrue(result['ok'],result)
    def phase(self):return services.snapshot(self.k)['phase']

    def test_owner_authority_and_live_desktop_precede_any_write(self):
        for p in (Principal('reader'),Principal('Slate',frozenset({'read','execute'})),Principal('tutor',frozenset({'approve','execute'}),mode='Tutor')):
            with self.assertRaises(ValueError):services.begin(self.k,'Off',p,'first')
            with self.assertRaises(ValueError):services.start(self.k,p,'first')
        self.lease.unlink()
        with self.assertRaises(ValueError):self.begin()
        self.assertTrue(control.value(self.k,services.ADMISSION));self.assertEqual(self.phase(),'ADMISSION_ON')

    def test_receipt_and_false_admission_commit_or_rollback_together(self):
        with patch.object(services,'_save',side_effect=sqlite3.OperationalError('Fixture rollback')):
            with self.assertRaises(sqlite3.Error):self.begin()
        self.assertTrue(control.value(self.k,services.ADMISSION))
        self.assertEqual(control.history(self.k)['changes'],[])
        row=self.begin();self.assertEqual(self.phase(),'DRAINING');self.assertFalse(control.value(self.k,services.ADMISSION))
        self.assertFalse(work_trail.work_status(self.k)['held']);self.assertEqual(control.history(self.k)['changes'][0]['after'],False)
        self.assertEqual(row['action'],'Off')

    def test_running_and_queued_work_stays_intact_until_controller_drain(self):
        job=self.job();row=self.begin('Reboot')
        with self.assertRaisesRegex(ValueError,'STILL_ACTIVE'):self.stop(row)
        self.assertEqual(self.k.record('jobs',job['id']),job);self.assertFalse(work_trail.work_status(self.k)['held'])
        self.assertEqual(services.snapshot(self.k)['counts']['running'],1)
        job['state']='Queued';self.k.save('jobs',job)
        with self.assertRaisesRegex(ValueError,'STILL_ACTIVE'):self.stop(row)

    def test_completed_stop_records_only_after_empty_owned_work(self):
        row=self.stop(self.begin());self.assertEqual(self.phase(),'STOPPING');self.assertTrue(work_trail.work_status(self.k)['held'])
        done=services.stopped(self.k,row,self.p);self.assertEqual(self.phase(),'OFF');self.assertEqual(done['id'],row['id'])
        with self.assertRaises(ValueError):services.stopped(self.k,row,self.p)
        self.assertEqual(self.k.listing('jobs'),[]);self.launch.assert_not_called()

    def test_explicit_on_atomically_releases_admission_and_work_hold(self):
        row=services.stopped(self.k,self.stop(self.begin()),self.p)
        with patch.object(services,'_setting',side_effect=sqlite3.OperationalError('Fixture rollback')):
            with self.assertRaises(sqlite3.Error):self.start()
        self.assertTrue(work_trail.work_status(self.k)['held']);self.assertFalse(control.value(self.k,services.ADMISSION));self.assertEqual(self.phase(),'OFF')
        result=self.start();self.assertEqual(result['action'],'On');self.assertEqual(self.phase(),'ON')
        self.assertFalse(work_trail.work_status(self.k)['held']);self.assertTrue(control.value(self.k,services.ADMISSION));self.launch.assert_not_called()

    def test_reboot_refuses_a_newer_master_stop_without_releasing_it(self):
        row=services.stopped(self.k,self.stop(self.begin('Reboot')),self.p);work_trail.hold(self.k,self.p)
        before=work_trail.work_status(self.k)
        with self.assertRaisesRegex(ValueError,'CYCLE_CHANGED'):self.start(row)
        self.assertEqual(work_trail.work_status(self.k),before);self.assertFalse(control.value(self.k,services.ADMISSION))
        services.fail(self.k,row,self.p);self.assertEqual(self.phase(),'CHANGED')

    def test_same_value_admission_change_invalidates_automatic_reboot(self):
        row=services.stopped(self.k,self.stop(self.begin('Reboot')),self.p);self.setting(False)
        with self.assertRaisesRegex(ValueError,'CYCLE_CHANGED'):self.start(row)
        self.assertTrue(work_trail.work_status(self.k)['held']);self.assertEqual(self.phase(),'CHANGED')

    def test_live_second_controller_cannot_replace_pending_cycle(self):
        row=self.begin();(self.leases/'second.json').write_text('{}')
        for action in ('Off','Reboot'):
            with self.assertRaisesRegex(ValueError,'BUSY'):services.begin(self.k,action,self.p,'second')
        with self.assertRaisesRegex(ValueError,'BUSY'):services.start(self.k,self.p,'second')
        self.assertEqual(services.snapshot(self.k)['cycle_id'],row['id'])

    def test_lost_desktop_is_interrupted_and_never_replays_reboot(self):
        row=self.begin('Reboot');self.lease.unlink();self.assertEqual(self.phase(),'INTERRUPTED')
        self.assertFalse(control.value(self.k,services.ADMISSION));self.assertEqual(self.k.listing('jobs'),[])
        (self.leases/'second.json').write_text('{}');new=services.start(self.k,self.p,'second')
        self.assertNotEqual(new['id'],row['id']);services.fail(self.k,row,self.p)
        self.assertEqual(services.snapshot(self.k)['cycle_id'],new['id']);self.assertEqual(self.phase(),'ON')

    def test_held_on_reconciles_queued_or_protected_workers_before_release(self):
        self.job('Queued');self.setting(False);work_trail.hold(self.k,self.p)
        with self.assertRaisesRegex(ValueError,'RECONCILE'):self.start()
        self.assertFalse(control.value(self.k,services.ADMISSION));self.assertTrue(work_trail.work_status(self.k)['held'])

    def test_on_does_not_cancel_current_running_work_when_admission_is_already_open(self):
        row=self.job();self.start();self.assertEqual(self.k.record('jobs',row['id']),row);self.assertEqual(self.phase(),'ON')

    def test_readback_differentiates_admission_only_and_full_stop(self):
        self.setting(False);status=services.snapshot(self.k)
        self.assertEqual(status['phase'],'ADMISSION_HELD');self.assertIn('not confirmed',status['summary'])
        with patch('subprocess.Popen',side_effect=AssertionError('Readback cannot launch')):services.snapshot(self.k)
        self.assertEqual(self.k.listing('jobs'),[])

    def test_restore_state_is_only_a_request_and_never_a_running_claim(self):
        row=services.stopped(self.k,self.stop(self.begin('Reboot')),self.p);row=self.start(row)
        services.restore_note(self.k,row,self.p,'REQUESTED');status=services.snapshot(self.k)
        self.assertEqual(status['model_restore'],'REQUESTED');self.assertEqual(status['phase'],'ON');self.assertEqual(self.k.listing('jobs'),[])
        work_trail.hold(self.k,self.p)
        with self.assertRaises(ValueError):services.restore_note(self.k,row,self.p,'REQUESTED')

    def test_quiesce_requires_own_stop_and_closes_only_tracked_handles(self):
        from workbench import local_brain,desktop_services
        row=self.begin()
        with self.assertRaises(ValueError):services.close_owned_services(self.k,self.p,row['id'])
        row=self.stop(row);console=MagicMock(closed=False);console.close.side_effect=lambda:setattr(console,'closed',True);console.process.poll.return_value=0
        self.k.console_sessions={'fixture':console};remote=MagicMock()
        with patch.object(local_brain,'stop') as stop,patch.object(desktop_services,'close_all') as tools,patch.object(desktop_services,'active_processes',return_value=[]):
            result=services.close_owned_services(self.k,self.p,row['id'],remote)
        self.assertEqual(result['state'],'OWNED_SERVICES_CLOSED');stop.assert_called_once();tools.assert_called_once_with(self.root);remote.assert_called_once();console.close.assert_called_once()

    def test_refused_closure_never_confirms_off_or_auto_restarts(self):
        from workbench import desktop_services
        row=self.stop(self.begin('Reboot'))
        with patch.object(desktop_services,'close_all',side_effect=OSError('Fixture close failed')):
            with self.assertRaises(OSError):services.close_owned_services(self.k,self.p,row['id'])
        services.fail(self.k,row,self.p);self.assertEqual(self.phase(),'FAILED')
        self.assertFalse(control.value(self.k,services.ADMISSION));self.assertTrue(work_trail.work_status(self.k)['held']);self.launch.assert_not_called()

    def test_off_blocks_new_native_console_phone_and_job_work_but_not_reads(self):
        from workbench import desktop_services,console_services,host_service
        self.setting(False)
        with patch.object(desktop_services,'language',side_effect=AssertionError('No native language process')):
            result=self.k.dispatch('desktop.code',dict(path='input.c',line=0,character=0,operation='hover'),self.p)
            self.assertFalse(result['ok']);self.assertIn('LEDGER_SERVICES_OFF',result['error']['message'])
        with patch.object(console_services,'open_session',side_effect=AssertionError('No console process')):
            result=self.k.dispatch('console.open',{},self.p);self.assertFalse(result['ok']);self.assertIn('LEDGER_SERVICES_OFF',result['error']['message'])
        coordinator=object.__new__(host_service.Coordinator);coordinator.kernel=self.k
        with self.assertRaisesRegex(ValueError,'LEDGER_SERVICES_OFF'):coordinator.remote_start({})
        self.assertTrue(self.k.dispatch('ledger.settings',{},self.p)['ok']);self.launch.assert_not_called()

    def test_corrupt_cycle_is_not_replayed_or_replaced_and_other_settings_remain_readable(self):
        with self.k.db() as db:db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(services.KEY,'{"schema":"unsupported"}'))
        with self.assertRaisesRegex(ValueError,'UNAVAILABLE'):self.begin()
        with self.assertRaisesRegex(ValueError,'UNAVAILABLE'):self.start()
        self.assertTrue(control.value(self.k,services.ADMISSION));self.assertEqual(control.history(self.k)['changes'],[])
        self.assertEqual(len(control.settings(self.k)['settings']),len(settings_registry.SPECS));self.launch.assert_not_called()

    def write_row(self,row):
        with self.k.db() as db:db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(services.KEY,json.dumps(row)))
    def journal(self):
        with self.k.db() as db:return [json.loads(raw) for raw, in db.execute('SELECT payload FROM activity_journal ORDER BY seq')]

    def test_partial_or_mistyped_cycle_rows_read_unavailable_before_any_key_error(self):
        complete=self.begin();healthy=services.snapshot(self.k)
        for row in ({'schema':'ledger.service-cycle/1','phase':'OFF','id':'c'*32},{**complete,'gate_epoch':'1'},{**complete,'pid':True},
                    {key:value for key,value in complete.items() if key!='admission_revision'},{**complete,'action':'Reset'},{**complete,'model_restore':'RUNNING'}):
            self.write_row(row)
            with self.k.db() as db:
                with self.assertRaisesRegex(ValueError,'UNAVAILABLE'):services.read(db)
            with self.assertRaisesRegex(ValueError,'UNAVAILABLE'):services.snapshot(self.k)
            with self.assertRaisesRegex(ValueError,'UNAVAILABLE'):self.stop(complete)
            with self.assertRaisesRegex(ValueError,'UNAVAILABLE'):self.start()
        self.write_row(complete);self.assertEqual(self.phase(),'DRAINING')
        shaped=services.unavailable(ValueError('fixture reason'))
        self.assertEqual(set(shaped)-set(healthy),{'error'});self.assertTrue(set(healthy)<=set(shaped));self.assertEqual(set(shaped['counts']),set(healthy['counts']))
        self.assertEqual(shaped['phase'],'UNAVAILABLE');self.assertIn('fixture reason',shaped['error']);self.assertFalse(shaped['admission_enabled']);self.launch.assert_not_called()

    def test_fail_after_committed_off_or_on_journals_without_downgrading_the_phase(self):
        row=services.stopped(self.k,self.stop(self.begin('Reboot')),self.p)
        services.fail(self.k,row,self.p);self.assertEqual(self.phase(),'OFF');self.assertFalse(control.value(self.k,services.ADMISSION))
        row=self.start(row);services.fail(self.k,row,self.p);status=services.snapshot(self.k)
        self.assertEqual(status['phase'],'ON');self.assertTrue(status['admission_enabled']);self.assertFalse(status['work_held']);self.assertEqual(status['model_restore'],'NOT_REQUESTED')
        notes=[e['state'] for e in self.journal() if e['operation']=='ledger.services' and e['state'].startswith('INCOMPLETE_AFTER_')]
        self.assertEqual(notes,['INCOMPLETE_AFTER_OFF','INCOMPLETE_AFTER_ON'])
        active=self.begin();services.fail(self.k,active,self.p);self.assertEqual(self.phase(),'FAILED');self.launch.assert_not_called()

    def test_stale_running_record_is_counted_and_terminal_rows_are_never_probed(self):
        from workbench.operation_stop import process_identity
        token=process_identity(os.getpid())
        self.job(state='Completed',pid=os.getpid(),worker_start=token) # a finished row keeps its pid; it is not a live worker
        self.k.save('jobs',dict(id='b'*32,owner=self.p.identity,state='Running',tool='brain.infer',pid=999999,worker_start='gone'))
        counts=services.snapshot(self.k)['counts']
        self.assertEqual(counts,dict(queued=0,running=1,live_workers=0,protected_workers=0,stale_running=1))
        self.k.save('jobs',dict(id='c'*32,owner=self.p.identity,state='Running',tool='brain.infer',pid=os.getpid(),worker_start=token))
        counts=services.snapshot(self.k)['counts'];self.assertEqual((counts['running'],counts['live_workers'],counts['stale_running']),(2,1,1))
        row=self.begin()
        with self.assertRaisesRegex(ValueError,'STILL_ACTIVE'):self.stop(row)
        with self.k.db() as db:db.execute("DELETE FROM jobs WHERE state='Running'")
        with patch('workbench.service_lifecycle.process_identity',side_effect=AssertionError('terminal rows are not probed')):
            with self.k.db() as db:pending=services.jobs(self.k,db)
        self.assertEqual(pending,dict(queued=[],running=[],live_workers=[],protected_workers=0,stale_running=0));self.launch.assert_not_called()

    def test_history_of_exited_workers_keeps_readback_fast(self):
        clock=time.time()
        with self.k.db() as db:
            for i in range(300):
                ident='%032x'%i;row=dict(id=ident,owner=self.p.identity,state='Completed',tool='lab.python',pid=4000000-i,worker_start='1234567',created=clock,finished=clock)
                db.execute('INSERT INTO jobs VALUES(?,?,?,?)',(ident,self.p.identity,'Completed',json.dumps(row)))
        def timed():
            start=time.perf_counter();services.snapshot(self.k);return time.perf_counter()-start
        timed();best=min(timed() for _ in range(3))
        self.assertLess(best,0.05,best);self.assertEqual(services.snapshot(self.k)['counts']['live_workers'],0)

    def test_restore_display_follows_observation_while_the_stored_note_stays_a_request(self):
        from workbench import local_brain
        row=self.start(services.stopped(self.k,self.stop(self.begin('Reboot')),self.p))
        with self.assertRaises(ValueError):services.restore_note(self.k,row,self.p,'REQUESTED',job_id='not-a-job')
        row=services.restore_note(self.k,row,self.p,'REQUESTED',job_id='d'*32,model_id='m'*64)
        ready={'state':'READY','selection':{'model_id':'m'*64},'worker':{'model_id':'m'*64}}
        with patch.object(local_brain,'status',return_value=ready):status=services.snapshot(self.k)
        self.assertEqual((status['model_restore'],status['model_restore_display']),('REQUESTED','OBSERVED_RUNNING'))
        with patch.object(local_brain,'status',return_value={**ready,'selection':{'model_id':'other'}}):
            self.assertEqual(services.snapshot(self.k)['model_restore_display'],'REQUESTED')
        self.k.save('jobs',dict(id='d'*32,owner=self.p.identity,state='Failed',tool='brain.activate'))
        with patch.object(local_brain,'status',return_value={'state':'MODEL_STOPPED','selection':{'model_id':'m'*64},'worker':None}):
            status=services.snapshot(self.k)
        self.assertEqual((status['model_restore'],status['model_restore_display']),('REQUESTED','REQUEST_FAILED'))
        with self.k.db() as db:stored=services.read(db)
        self.assertEqual((stored['model_restore'],stored['model_restore_job'],stored['model_restore_model']),('REQUESTED','d'*32,'m'*64))
        self.assertEqual(services.snapshot(self.k)['phase'],'ON');self.launch.assert_not_called()

    def test_host_quiesce_rpc_preserves_owner_and_cycle_checks(self):
        import threading
        from workbench.host_service import Coordinator
        c=object.__new__(Coordinator);c.kernel=self.k;c.dispatch_lock=threading.RLock();c.remote_stop=MagicMock()
        with self.assertRaisesRegex(ValueError,'owner'):c.invoke('service_quiesce',{'cycle_id':'a'*32},Principal('reader'))
        with self.assertRaises(ValueError):c.invoke('service_quiesce',{'cycle_id':'a'*32},self.p)
        row=self.stop(self.begin())
        with patch.object(services,'close_owned_services',return_value={'state':'fixture'}) as close:
            self.assertEqual(c.invoke('service_quiesce',{'cycle_id':row['id']},self.p),{'state':'fixture'})
            close.assert_called_once_with(self.k,self.p,row['id'],c.remote_stop)


if __name__=='__main__':unittest.main()
