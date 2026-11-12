"""Launch-default consumers, frozen requests and original model safety boundaries."""
import copy,json,os,tempfile,unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from workbench import ledger_control,local_brain as brain,model_settings,settings_registry,stacy_control
from workbench.engineering_kernel import Kernel,operator,Principal
from workbench.session import Session

HOST=dict(logical_cpus=8,available_ram_bytes=8*1024**3,total_ram_bytes=16*1024**3,backend='CPU')


def fixture_model(ident='a'*64):
    return dict(id=ident,role='chat',message_template='A disposable configuration fixture; never an actual model.',
        total_bytes=1024*1024,files=[dict(name='fixture.gguf',path='/not-a-model/fixture.gguf',sha256='e'*64,bytes=1024*1024)],
        qualification='NOT_TESTED',storage='CONFIGURATION_FIXTURE',declared_license='FIXTURE',origin='BOUNDARY_TEST',
        inspection=dict(metadata={'general.name':'Configuration fixture','llama.context_length':8192,'llama.block_count':2,
            'llama.embedding_length':128,'llama.attention.head_count':4,'llama.attention.head_count_kv':2},
            architecture='llama',architecture_profile='SUPPORTED_FOR_TRIAL',quantization=['Q4_0'],parameter_count=1024,
            file='fixture.gguf',tensor_count=0,tensor_preview_truncated=False,tensor_preview=[]))


class ModelSettingsTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='ledger-model-settings-');self.addCleanup(temp.cleanup);self.base=Path(temp.name)
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(self.base/'profile'),'ARC_LEDGER_CONCERN':str(self.base/'Concern')});env.start();self.addCleanup(env.stop)
        self.root=self.base/'workspace';self.root.mkdir();self.k=Kernel(self.root);self.owner=operator('owner')
        session=Session(self.base/'profile/session.json',self.root);session.save();ledger_control.bind(self.k,session)
        self.host=patch('workbench.brain_runtime.host',return_value=HOST);self.host.start();self.addCleanup(self.host.stop)
        self.launch=patch.object(self.k,'launch');self.launch_mock=self.launch.start();self.addCleanup(self.launch.stop)
        for ident in ('a'*64,'b'*64):brain.put(self.k,'model.'+ident,fixture_model(ident))

    def call(self,op,args=None,principal=None):
        r=self.k.dispatch(op,args or {},principal or self.owner);self.assertTrue(r['ok'],r);return r['result']
    def row(self,key):return next(r for r in self.call('ledger.settings')['settings'] if r['key']==key)
    def set(self,key,value):return self.call('ledger.settings.set',dict(key=key,value=value,expected_revision=self.row(key)['revision']))
    def request(self,ident='b'*64,key='load',options=None,operation='brain.model.use'):
        args=dict(id=ident,request_key=key)
        if options is not None:args['options']=options
        return self.call(operation,args)
    def selected(self):
        old=dict(model_id='a'*64,config=dict(context=1024,threads=2,memory_mb=2048),owner='owner')
        brain.put(self.k,'selection',old);return old
    def worker(self,selection,pid=91):
        return dict(owner='owner',model_id=selection['model_id'],config=copy.deepcopy(selection['config']),context=selection['config']['context'],
                    pid=pid,start='fixture-start',job_id='c'*32,runtime={},started=1.0,key_file='/private/worker.key',port=12345)

    def test_saved_defaults_undo_default_revision_and_atomic_history(self):
        changed=self.set('brain.context',4096)
        self.assertEqual(model_settings.preferences(self.k)['context'],4096)
        self.call('ledger.settings.undo',{'id':changed['id']});self.assertEqual(self.row('brain.context')['stored'],2048)
        stale=self.row('brain.threads');self.set('brain.threads',6);self.set('brain.threads',4)
        self.assertFalse(self.k.dispatch('ledger.settings.set',dict(key='brain.threads',value=7,expected_revision=stale['revision']),self.owner)['ok'])
        self.set('brain.memory_mb',2048);self.call('ledger.settings.restore',dict(key='brain.memory_mb',expected_revision=self.row('brain.memory_mb')['revision']))
        self.assertEqual(self.row('brain.memory_mb')['stored'],0)
        with patch.object(ledger_control,'_trim_history',side_effect=ValueError('Journal fixture refuses commit')):
            self.assertFalse(self.k.dispatch('ledger.settings.set',dict(key='brain.context',value=6144),self.owner)['ok'])
        self.assertEqual(self.row('brain.context')['stored'],2048);self.launch_mock.assert_not_called()

    def test_bounds_owner_tutor_and_cloud_activity_boundary(self):
        for key,values in [('brain.context',[511,8193,True]),('brain.threads',[0,33,False]),('brain.memory_mb',[-1,1,511,262145,True])]:
            for value in values:self.assertFalse(self.k.dispatch('ledger.settings.set',dict(key=key,value=value),self.owner)['ok'],(key,value))
        denied=Principal('Slate',frozenset({'read','execute'}))
        tutor=Principal('owner',frozenset({'read','execute','approve'}),mode='Tutor')
        for p in (denied,tutor):self.assertFalse(self.k.dispatch('ledger.settings.set',dict(key='brain.context',value=4096),p)['ok'])
        self.assertFalse(self.k.dispatch('brain.model.use',{'id':'a'*64},denied)['ok'])
        self.assertFalse(self.k.dispatch('jobs.submit',dict(tool='brain.activate',brain={'model_id':'a'*64}),denied)['ok'])
        self.assertTrue(settings_registry.MODEL_KEYS.isdisjoint(self.call('ledger.context')['settings']))
        for op,args in [('ledger.settings.effective',{'key':'brain.context'}),('ledger.settings.history',{'key':'brain.threads'}),
                        ('ledger.settings.set',{'key':'brain.context','value':4096})]:
            self.assertTrue(stacy_control.cloud_private(op,args))
            with self.assertRaises(ValueError):stacy_control.validate_actions([stacy_control.call(op,args)],self.owner,provider=True)
        self.launch_mock.assert_not_called()

    def test_new_requests_freeze_defaults_auto_and_keep_idempotency_after_defaults_change(self):
        self.set('brain.context',4096);self.set('brain.threads',6)
        job=self.request();frozen=job['brain_launch']['options']
        self.assertEqual((frozen['context'],frozen['threads']),(4096,6));self.assertGreaterEqual(frozen['memory_mb'],512)
        self.assertEqual(job['request_spec']['brain'],{'model_id':'b'*64})
        self.set('brain.context',6144);self.set('brain.memory_mb',2048)
        retry=self.request();self.assertEqual(retry['id'],job['id']);self.assertEqual(retry['brain_launch'],job['brain_launch'])
        self.assertEqual(self.launch_mock.call_count,1)
        direct=self.call('jobs.submit',dict(tool='brain.activate',request_key='direct',brain={'model_id':'a'*64}))
        self.assertEqual(model_settings.config(direct['brain_launch']['options']),dict(context=6144,threads=6,memory_mb=2048))

    def test_explicit_request_and_restore_override_launch_defaults(self):
        self.set('brain.context',6144);self.set('brain.threads',8);self.set('brain.memory_mb',4096)
        direct=self.request(options=dict(context=2048,threads=3,memory_mb=2048))
        self.assertEqual(model_settings.config(direct['brain_launch']['options']),dict(context=2048,threads=3,memory_mb=2048))
        previous=dict(model_id='a'*64,config=dict(context=1024,threads=2,memory_mb=2048),owner='owner')
        brain.put(self.k,'previous',previous)
        restored=self.call('brain.restore',{'request_key':'restore'})
        self.assertEqual(model_settings.config(restored['brain_launch']['options']),previous['config'])
        qualified=self.request(key='qualify',operation='brain.model.qualify')
        self.assertEqual(qualified['tool'],'brain.qualify');self.assertEqual(qualified['brain_launch']['options']['context'],6144)

    def test_legacy_requests_are_not_reinterpreted_and_corrupt_frozen_options_fail_closed(self):
        legacy=dict(request_spec={'brain':{'model_id':'a'*64,'context':1024}})
        self.set('brain.context',8192);self.assertEqual(model_settings.job_options(legacy),legacy['request_spec']['brain'])
        job=self.request();bad=copy.deepcopy(job);bad['brain_launch']['options']['model_id']='a'*64
        with self.assertRaises(ValueError):model_settings.job_options(bad)
        bad=copy.deepcopy(job);del bad['brain_launch']['options']['threads']
        with self.assertRaises(ValueError):model_settings.job_options(bad)
        bad=copy.deepcopy(job);bad['brain_launch']['schema']='unknown'
        with self.assertRaises(ValueError):model_settings.job_options(bad)

    def test_stored_selection_is_not_running_and_unverified_worker_never_supplies_effective_values(self):
        old=self.selected();row=self.row('brain.context');self.assertEqual(row['stored'],2048);self.assertIsNone(row['effective'])
        self.assertEqual(row['application_state'],'MODEL_STOPPED')
        brain.put(self.k,'worker',self.worker(old))
        with patch.object(brain,'worker_live',return_value=False):self.assertIsNone(self.row('brain.threads')['effective'])

    def test_worker_requested_saved_and_other_owner_records_are_separate_without_credentials(self):
        old=self.selected();brain.put(self.k,'worker',self.worker(old));self.set('brain.context',4096);job=self.request()
        other=copy.deepcopy(job);other.update(id='d'*32,owner='other');self.k.save('jobs',other)
        with patch.object(brain,'worker_live',return_value=True):
            row=self.row('brain.context');self.assertEqual((row['stored'],row['requested'],row['effective']),(4096,4096,1024))
            public=json.dumps(row);self.assertNotIn('/private/worker.key',public);self.assertNotIn('"port":',public)
            self.assertNotIn('d'*32,public)
            outsider=self.call('ledger.settings',principal=operator('other'))
            value=next(r for r in outsider['settings'] if r['key']=='brain.context')
            self.assertIsNone(value['effective']);self.assertIsNone(value['model_runtime']['selection'])

    def test_bad_optional_defaults_leave_the_other_settings_available_and_bytes_untouched(self):
        with self.k.db() as db:db.execute('INSERT INTO settings VALUES(?,?)',('ledger.brain.context','"invalid fixture"'))
        rows=self.call('ledger.settings')['settings'];self.assertEqual(len(rows),len(settings_registry.SPECS))
        self.assertTrue(all(not r['editable'] for r in rows if r['key'] in settings_registry.MODEL_KEYS))
        self.assertTrue(next(r for r in rows if r['key']=='reading.family')['editable'])
        with self.k.db() as db:self.assertEqual(db.execute('SELECT value FROM settings WHERE key=?',('ledger.brain.context',)).fetchone()[0],'"invalid fixture"')
        self.assertFalse(self.k.dispatch('brain.model.use',{'id':'b'*64},self.owner)['ok']);self.launch_mock.assert_not_called()

    def transaction(self,mode='restore',cancel=False,reply=False):
        old=self.selected();worker=self.worker(old);brain.put(self.k,'worker',worker)
        job=self.request();job['state']='Running';job['cancel']=cancel;self.k.save('jobs',job)
        if reply:self.k.save('jobs',dict(id='e'*32,owner='owner',tool='brain.respond',state='Running'))
        alive={91};calls=[]
        def terminate(kernel,value,reason):alive.discard(value['pid'])
        def start(kernel,value,config,ident,*args,**kwargs):
            calls.append(value['id'])
            if value['id']=='b'*64 or mode=='fail':raise ValueError('Controlled candidate load failure')
            restored=self.worker(dict(model_id=value['id'],config=config),pid=92);restored['job_id']=ident;alive.add(92);return restored
        with ExitStack() as stack:
            stack.enter_context(patch.object(brain,'worker_live',side_effect=lambda value:bool(value and value.get('pid') in alive)))
            stack.enter_context(patch.object(brain,'terminate',side_effect=terminate))
            stack.enter_context(patch.object(brain,'start_server',side_effect=start))
            stack.enter_context(patch.object(brain,'completion',return_value={'text':'ready','usage':{},'memory':{}}))
            with self.assertRaises(ValueError):brain.run_model_job(self.k,job)
            job.update(state='Cancelled' if cancel else 'Failed');self.k.save('jobs',job)
            snap=model_settings.snapshot(self.k,'owner')
        self.assertEqual(brain.get(self.k,'selection'),old);self.assertIsNone(brain.get(self.k,'handover'));return snap,calls,alive

    def test_failed_activation_retains_original_restore_and_reports_owned_restored_worker(self):
        snap,calls,alive=self.transaction()
        self.assertEqual(calls,['b'*64,'a'*64]);self.assertIn(92,alive);self.assertEqual(snap['state'],'RESTORED_PREVIOUS')
        self.assertEqual(snap['worker_config'],dict(context=1024,threads=2,memory_mb=2048))
        self.assertEqual(snap['last_operation']['state'],'Failed');self.assertTrue(snap['restored_after_job'])

    def test_failed_restore_never_claims_running_or_restored_values(self):
        snap,calls,alive=self.transaction(mode='fail')
        self.assertFalse(alive);self.assertIsNone(snap['worker_config']);self.assertIsNone(snap['restored_after_job'])
        self.assertEqual(snap['state'],'MODEL_STOPPED')

    def test_owner_cancellation_stays_stopped_and_never_automatically_restores(self):
        snap,calls,alive=self.transaction(cancel=True)
        self.assertEqual(calls,['b'*64]);self.assertFalse(alive);self.assertIsNone(snap['worker_config'])
        self.assertEqual(snap['last_operation']['state'],'Cancelled')

    def test_running_reply_refuses_handover_without_stopping_the_original_worker(self):
        snap,calls,alive=self.transaction(reply=True)
        self.assertEqual(calls,[]);self.assertEqual(alive,{91});self.assertIsNotNone(snap['worker_config'])
        self.assertIsNone(snap['restored_after_job'])

    def test_worker_uses_frozen_options_even_after_saved_defaults_change(self):
        self.set('brain.context',4096);self.set('brain.threads',6);job=self.request()
        self.set('brain.context',6144);self.set('brain.threads',8)
        observed=[]
        def start(kernel,value,config,ident,*args,**kwargs):
            observed.append(config)
            return dict(owner='owner',model_id=value['id'],context=config['context'],config=config,
                        pid=93,start='fixture-start',runtime={},load_seconds=.01,job_id=ident)
        with patch.object(brain,'start_server',side_effect=start),patch.object(brain,'completion',return_value={'text':'ready','usage':{},'memory':{}}),patch.object(brain,'recheck'),patch.object(brain,'worker_live',side_effect=lambda w:bool(w and w.get('pid')==93)):
            result=brain.run_model_job(self.k,job);row=self.row('brain.context')
        self.assertEqual(result['status'],'ACTIVATED');self.assertEqual(observed[0]['context'],4096)
        self.assertEqual((row['stored'],row['effective']),(6144,4096));self.assertEqual(observed[0]['threads'],6)
