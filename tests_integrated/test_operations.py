"""Operation observations, privacy, queue prerequisites and priority readback."""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import operations,host_observations,agenda,ledger_control,job_priority,stacy_control
from workbench.engineering_kernel import Kernel,operator,Principal
from workbench.session import Session


class OperationsTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name)
        self.root=self.base/'work';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(self.base/'profile'),'ARC_LEDGER_CONCERN':str(self.base/'Concern')})
        env.start();self.addCleanup(env.stop);self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.s=Session(self.base/'profile/session.json',self.root);self.s.save();ledger_control.bind(self.kernel,self.s)

    def call(self,op,args=None,principal=None):
        response=self.kernel.dispatch(op,args or {},principal or self.owner);self.assertTrue(response['ok'],response);return response['result']

    def item(self,title,**extra):return self.call('agenda.add',dict(title=title,program='@files:input.txt',**extra))
    def snapshot(self,**args):return self.call('ledger.operations',args)

    def job(self,ident='a'*32,owner='owner',state='Queued',tool='brain.infer',**extra):
        row=dict(id=ident,owner=owner,state=state,tool=tool,**extra);self.kernel.save('jobs',row);return row

    def test_host_counter_missing_or_reset_never_becomes_a_stale_percentage(self):
        self.assertEqual(host_observations.cpu_percent([10,100],[20,140]),25)
        for before,after in [(None,[1,10]),([5,10],None),([10,100],[2,40]),([10,100],[11,100]),([10,100],[90,110])]:
            self.assertIsNone(host_observations.cpu_percent(before,after))
        with patch('builtins.open',side_effect=OSError('No host counters')):
            self.assertIsNone(host_observations.cpu());self.assertIsNone(host_observations.memory())
        with patch('pathlib.Path.glob',side_effect=OSError('No GPU driver access')):self.assertIsNone(host_observations.gpu())

    def test_txt_is_unavailable_even_when_model_capacity_is_declared(self):
        with patch('workbench.local_brain.status',return_value={'state':'READY','selection':{'model_id':'example'},'worker':{'context':6144}}):
            value=self.snapshot()
        self.assertEqual(value['slate']['local_state'],'READY');self.assertIsNone(value['host']['txt']['percent'])
        self.assertEqual(value['host']['txt']['state'],'UNAVAILABLE')

    def test_operations_reads_preserve_records_and_never_launch_a_job(self):
        row=self.item('Read the saved input')
        with patch('subprocess.Popen',side_effect=AssertionError('No process launch')):
            value=self.snapshot()
        self.assertEqual(value['jobs_submitted'],0);self.assertEqual(self.kernel.listing('jobs'),[])
        self.assertEqual(value['agenda']['next'][0]['id'],row['id']);self.assertNotIn('program',value['agenda']['next'][0])

    def test_private_jobs_and_record_context_are_filtered_before_display(self):
        self.job(owner='other');self.job(ident='b'*32,owner='owner')
        idea=self.call('ideas.capture',{'text':'Private selection words'})
        value=self.call('ledger.operations',{'context':'idea:'+idea['id']},operator('other'))
        self.assertIsNone(value['selection']);self.assertNotIn(idea['text'],json.dumps(value));self.assertNotIn(idea['id'],json.dumps(value))
        own=self.snapshot();ids={r['id'] for r in own['agenda']['next']}
        self.assertIn('b'*32,ids);self.assertNotIn('a'*32,ids)
        direct=self.call('agenda.view');self.assertNotIn('a'*32,{r.get('id') for r in direct['next']})

    def test_dependency_and_idle_checks_share_the_existing_queue_readiness(self):
        first=self.item('First input');dependent=self.item('Then dependent',when={'after':first['id']});background=self.item('Idle work',nice='background')
        value=self.snapshot();rows={r['id']:r for r in value['agenda']['next']}
        self.assertEqual(value['first_queue_checks_passed'],first['id'])
        self.assertTrue(any('After First input' in reason for reason in rows[dependent['id']]['schedule_checks']['reasons']))
        self.assertIn('Waits for idle time',rows[background['id']]['schedule_checks']['reasons'])
        with agenda.opened(self.kernel) as db:
            for ident in (first['id'],dependent['id'],background['id']):
                stored=agenda.owned(db,ident,'owner');self.assertEqual(agenda.ready(db,stored,False,value['sampled_at']),rows[ident]['schedule_checks']['state']=='PASSED')
        idle=self.snapshot(idle=True);self.assertEqual(next(r for r in idle['agenda']['next'] if r['id']==background['id'])['schedule_checks']['state'],'PASSED')

    def test_other_owner_dependency_cannot_release_an_item(self):
        other=self.call('agenda.add',{'title':'Other private input','program':'@files:input.txt'},operator('other'))
        row=self.item('Our input')
        with agenda.opened(self.kernel) as db:
            db.execute("UPDATE agenda_items SET state='DONE' WHERE id=?",(other['id'],));db.execute('UPDATE agenda_items SET after=? WHERE id=?',(other['id'],row['id']))
            self.assertFalse(agenda.ready(db,agenda.owned(db,row['id'],'owner'),True,10**12))
        value=self.snapshot();self.assertIn('Dependency unavailable',value['agenda']['next'][0]['schedule_checks']['reasons'])
        self.assertNotIn('Other private input',json.dumps(value))

    def test_reorder_commits_order_and_adopts_tier_without_changing_cpu_priority(self):
        first=self.item('First',nice='now');second=self.item('Second',nice='normal')
        with patch('os.setpriority',create=True) as cpu:
            changed=self.call('agenda.reorder',{'id':second['id'],'position':0})
        cpu.assert_not_called();self.assertEqual(changed['nice'],'now')
        rows=[r for r in self.snapshot()['agenda']['next'] if r.get('kind')!='job']
        self.assertEqual([r['id'] for r in rows],[second['id'],first['id']])

    def test_paused_and_services_off_stay_visible_with_reasons(self):
        row=self.item('Paused work');self.call('agenda.pause',{'id':row['id']})
        self.call('ledger.settings.set',{'key':'operations.services_enabled','value':False})
        value=self.snapshot();reasons=value['agenda']['next'][0]['schedule_checks']['reasons']
        self.assertIn('Paused by owner',reasons);self.assertIn('Ledger services off',reasons);self.assertIsNone(value['first_queue_checks_passed'])

    def test_queued_cpu_nice_is_a_next_start_request_not_an_os_observation(self):
        row=self.job(pid=12345,worker_start='old-process')
        with patch('os.setpriority',create=True) as cpu,patch('os.getpriority',create=True) as observed:
            changed=self.call('jobs.nice',{'id':row['id'],'value':10});value=self.snapshot()
        cpu.assert_not_called();observed.assert_not_called();self.assertEqual(changed['state'],'QUEUED')
        shown=next(r for r in value['agenda']['next'] if r['id']==row['id'])
        self.assertEqual(shown['cpu_priority_basis'],'NEXT_START_REQUEST');self.assertEqual(shown['cpu_nice'],10)

    def test_another_running_agenda_item_and_owner_hold_prevent_a_next_claim(self):
        running=self.item('Already running');self.item('Wait for this turn')
        with agenda.opened(self.kernel) as db:db.execute("UPDATE agenda_items SET state='RUNNING' WHERE id=?",(running['id'],))
        value=self.snapshot();self.assertIsNone(value['first_queue_checks_passed'])
        self.assertIn('Another Agenda item is running',value['agenda']['next'][0]['schedule_checks']['reasons'])
        from workbench.work_trail import hold
        hold(self.kernel,self.owner);value=self.snapshot();self.assertTrue(value['slate']['work_held']);self.assertIsNone(value['first_queue_checks_passed'])

    def test_unverified_running_process_never_claims_a_live_nice_value(self):
        row=self.job(state='Running',pid=12345,worker_start='expected',cpu_nice=4)
        with patch('workbench.job_priority.process_identity',return_value='different'),patch('os.setpriority',create=True) as change:
            value=job_priority.describe(self.kernel,row,self.owner)
            self.assertFalse(self.kernel.dispatch('jobs.nice',{'id':row['id'],'value':12},self.owner)['ok'])
        self.assertIsNone(value['cpu_nice']);self.assertFalse(value['can_adjust_nice']);change.assert_not_called()

    def test_os_priority_refusal_preserves_actual_readback_and_reports_refusal(self):
        row=self.job(state='Running',pid=12345,worker_start='known',cpu_nice=10)
        with patch('workbench.job_priority.process_identity',return_value='known'),patch('workbench.job_priority.owned_tree',return_value=[]), \
             patch('os.setpriority',side_effect=PermissionError('OS refused')),patch('os.getpriority',return_value=10):
            value=self.call('jobs.nice',{'id':row['id'],'value':0})
        self.assertEqual(value['state'],'PARTIAL_OR_REFUSED');self.assertEqual(value['actual'],10);self.assertIn('OS refused',value['notice'])

    def test_unreadable_cycle_row_keeps_operations_readable_with_an_unavailable_service_block(self):
        from workbench import service_lifecycle as services
        row=self.item('Still visible');healthy=self.snapshot()
        for raw in ('{"schema":"unsupported"}',json.dumps(dict(schema='ledger.service-cycle/1',phase='OFF',id='c'*32))):
            with self.kernel.db() as db:db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(services.KEY,raw))
            with patch('subprocess.Popen',side_effect=AssertionError('No process launch')):value=self.snapshot()
            self.assertEqual(set(value),set(healthy));self.assertEqual(set(value['services'])-set(healthy['services']),{'error'})
            self.assertEqual(value['services']['phase'],'UNAVAILABLE');self.assertIn('UNAVAILABLE',value['services']['error'])
            self.assertEqual(value['agenda']['next'][0]['id'],row['id']);self.assertTrue(value['slate']['services_enabled']);self.assertFalse(value['slate']['work_held'])
            self.assertEqual(value['services']['counts']['running'],0);self.assertEqual(value['jobs_submitted'],0)
        with self.kernel.db() as db:db.execute('DELETE FROM settings WHERE key=?',(services.KEY,))
        self.assertEqual(self.snapshot()['services']['phase'],'ADMISSION_ON');self.assertEqual(self.kernel.listing('jobs'),[])

    def test_nice_slider_words_follow_the_registry_tiers_and_the_linux_scale(self):
        # UI-03: every row's slider reads left more urgent, right nicer; the value is said in words beside its number.
        from workbench.desktop_header_qt import TIERS,tier_words,cpu_nice_words,nice_reason,KILL_WORDS,MONITORS_NOTE
        self.assertEqual(TIERS,agenda.NICE,'the queued slider maps the existing tiers in the existing order')
        self.assertEqual([tier_words(t) for t in TIERS],['Now · urgent','Normal','Background · waits for idle']);self.assertEqual(tier_words('later'),'Later')
        self.assertEqual(cpu_nice_words(0),'0 · normal');self.assertEqual(cpu_nice_words(19),'19 · nicest');self.assertEqual(cpu_nice_words(None),'—')
        self.assertEqual(cpu_nice_words(10,'NEXT_START_REQUEST'),'10 · nicer · requested')
        bands=[cpu_nice_words(v).split(' · ')[1] for v in range(20)]
        self.assertEqual((bands.index('a little nicer'),bands.index('nicer'),bands.index('much nicer'),bands.index('nicest')),(1,6,13,19))
        self.assertEqual(bands,sorted(bands,key=['normal','a little nicer','nicer','much nicer','nicest'].index),'the words never go back as the number rises')
        self.assertIn('not verified',nice_reason({'cpu_priority_basis':'UNVERIFIED_PROCESS'}));self.assertIn('Linux',nice_reason({'cpu_priority_basis':'UNSUPPORTED'}))
        self.assertIn('exited',nice_reason({'cpu_priority_basis':'UNAVAILABLE'}));self.assertIn('finished',nice_reason({'state':'Completed'}))
        self.assertEqual(KILL_WORDS,'Stop all jobs')  # HATCH DESK D2: the System menu's second row, scoped to the work Graphite manages;self.assertEqual(MONITORS_NOTE,'Current Graphite host · CPU / GPU / RAM / TXT')

    def test_the_queued_slider_mapping_round_trips_through_agenda_nice_and_view(self):
        from workbench.desktop_header_qt import TIERS
        row=self.item('Slider work')
        for position in (2,0,1):  # right, left, middle: the slider's index is the tier's place in the registry order
            with patch('os.setpriority',create=True) as cpu:changed=self.call('agenda.nice',{'id':row['id'],'nice':TIERS[position]})
            cpu.assert_not_called();self.assertEqual(changed['nice'],TIERS[position])
            shown=next(r for r in self.call('agenda.view')['next'] if r.get('id')==row['id']);self.assertEqual(TIERS.index(shown['nice']),position)
        self.assertEqual(self.kernel.listing('jobs'),[])

    def test_read_only_owner_cannot_adjust_priority_and_cloud_is_private(self):
        row=self.job();reader=Principal('owner',frozenset({'read'}))
        self.assertFalse(job_priority.describe(self.kernel,row,reader)['can_adjust_nice'])
        self.assertFalse(self.kernel.dispatch('jobs.nice',{'id':row['id'],'value':10},reader)['ok'])
        with self.assertRaises(ValueError):stacy_control.validate_actions([stacy_control.call('ledger.operations',{})],self.owner,provider=True)
        self.assertTrue(self.kernel.dispatch('ledger.operations',{},reader)['ok'])


if __name__=='__main__':unittest.main()
