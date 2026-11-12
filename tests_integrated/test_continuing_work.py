"""Continuing work and the Agenda: grants, budgets, the Master Stop epoch, outside edits, no-progress stops, recurrences, crash
reconciliation, procedures and worker refusal; no model or isolation emulation."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from workbench.engineering_kernel import Kernel,Principal,operator
from workbench import locations,continuing_work as flow,work_trail,worker_boundary as workers,change_sets,edit_storage



HOLDS=[]


def setUpModule():
    # Nothing here may start a worker, submit a job or send a provider request (Graphite's test rule). The one exception is a
    # kernel whose own launch the protocol double has replaced (protocol_fixture.ProtocolWorker): it may queue a job row, which
    # the test then runs in this process against the loopback double; no worker can start from it.
    from workbench import clip, stacy_foundation
    from workbench.engineering_kernel import Kernel as HeldKernel
    real_submit=HeldKernel.submit
    def submit(kernel,*args,**kwargs):
        if 'launch' not in vars(kernel):raise AssertionError('No job submission')
        return real_submit(kernel,*args,**kwargs)
    # Whether the packaged Graphite seed is current is the release check's runtime section, not these behaviour tests: a seed
    # whose own files verify but whose declared sources were edited or left out since packaging (STALE, SOURCE_UNAVAILABLE)
    # reads as bound here, with its real seed_id. An absent or broken seed still refuses.
    real_seed=stacy_foundation.seed_status
    def seed_status(root):
        value=real_seed(root)
        return {**value,'state':'VERIFIED_SOURCE_BINDINGS'} if value.get('state') in ('STALE','SOURCE_UNAVAILABLE') else value
    for held in (patch.object(HeldKernel,'launch',side_effect=AssertionError('No worker launch')),patch.object(HeldKernel,'submit',submit),
            patch.object(clip,'_request',side_effect=AssertionError('No provider request')),patch.object(stacy_foundation,'seed_status',seed_status)):
        held.start();HOLDS.append(held)


def tearDownModule():
    while HOLDS:HOLDS.pop().stop()

class Continuing(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ledger-work-test-');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.home=self.base/'User';self.home.mkdir()
        self.source=self.home/'Clock';self.source.mkdir();(self.source/'note.md').write_text('blue\n')
        (self.source/'parts.csv').write_text('Part,Need,Have\nClock,2,1\n')
        self.root=self.base/'Office';self.profile=self.base/'profile'
        self.env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(self.profile),'ARC_LEDGER_WORKSPACE':str(self.root),'ARC_LEDGER_EMBEDDED':'1'})
        self.env.start();self.addCleanup(self.env.stop)
        self.homedir=patch.object(Path,'home',return_value=self.home);self.homedir.start();self.addCleanup(self.homedir.stop)
        locations.office(self.root);self.kernel=Kernel(self.root);self.p=operator()
        self.copy=self.import_copy()
        project=self.call('projects.create',{'title':'Clock','intent':'Make a working clock'})
        self.assignment=self.call('assignments.create',{'project':project['id'],'request':'Use black hands',
            'interpretation':'Prepare a revised working note','intended_output':'A reviewed note','success':['Note says black'],
            'stop':['Changed inputs'],'inputs':['files:'+self.copy['work']+'/note.md']})

    def import_copy(self):
        pre=self.call('imports.preview',{'source':str(self.source),'profile':'CODE'})
        return self.call('imports.accept',{'id':pre['id'],'expected_digest':pre['content_digest'],'for_slate':True})

    def call(self,op,args=None,p=None,ok=True):
        result=self.kernel.dispatch(op,args or {},p or self.p)
        self.assertEqual(result['ok'],ok,result)
        return result['result'] if ok else result['error']['message']

    def steps(self,verify=False):
        result=[{'key':'Read','operation':'work.read','arguments':{'copy':self.copy['id'],'path':'note.md'},'after':[]},
            {'key':'Draft','operation':'changes.propose','arguments':{'copy':self.copy['id'],'operations':[{'op':'WRITE','path':'note.md',
                'base_sha256':{'$step':'Read','path':['sha256']},'text':'black\n'}]},'after':['Read']},
            {'key':'Apply','operation':'changes.apply','arguments':{'id':{'$step':'Draft','path':['id']},
                'expected_digest':{'$step':'Draft','path':['content_digest']}},'after':['Draft']}]
        if verify:result.append({'key':'ReadBack','operation':'work.read','arguments':{'copy':self.copy['id'],'path':'note.md'},'after':['Apply'],
            'require':[{'path':['text'],'equals':'black\n'}]})
        return result

    def create(self,steps=None,budget=None):
        return self.call('work.create',{'title':'Clock preparation','assignment':self.assignment['id'],'copies':[self.copy['id']],
            'steps':steps or self.steps(),'budget':{'seconds':300,'steps':10,'tokens':0,'memory_mb':128,'output_bytes':1048576,'files':10,**(budget or {})},
            'expires':time.time()+600})

    def authorize(self,w):
        return self.call('work.authorize',{'id':w['plan']['id'],'expected_digest':w['content_digest']})

    def run_step(self,w):return self.call('work.advance',{'id':w['plan']['id']})
    def get(self,w):return self.call('work.get',{'id':w['plan']['id']})

    def test_authorized_agenda_advances_fixed_plan_and_leaves_originals_unchanged(self):
        w=self.create(self.steps(True));self.assertEqual(self.run_step(w)['ran'],None)
        self.assertEqual(self.get(w)['state']['used']['steps'],0)
        self.authorize(w)
        for _ in range(4):flow.pump(self.kernel)
        result=self.get(w);self.assertEqual(result['state']['state'],'REVIEW')
        self.assertTrue(all(s['state']=='DONE' for s in result['steps']))
        self.assertEqual((self.source/'note.md').read_text(),'blue\n')
        self.assertEqual((self.root/'Files'/self.copy['work']/'note.md').read_text(),'black\n')
        self.assertEqual(len(result['state']['source_successors']),1)
        used=result['state']['used']['steps'];self.run_step(w)
        self.assertEqual(self.get(w)['state']['used']['steps'],used)
        self.assertTrue(any(r.get('kind')=='work' for r in self.call('agenda.view')['waiting']))

    def test_grant_is_private_exact_immutable_and_cannot_authorize_original_or_network_work(self):
        w=self.create();ident=w['plan']['id'];reader=Principal(self.p.identity);stranger=operator('another-owner')
        self.call('work.get',{'id':ident},stranger,False)
        self.call('work.authorize',{'id':ident,'expected_digest':w['content_digest']},reader,False)
        self.call('work.authorize',{'id':ident,'expected_digest':'0'*64},ok=False)
        bad=self.steps();bad[1]['operation']='changes.publish'
        self.call('work.create',{'title':'Invalid','assignment':self.assignment['id'],'copies':[self.copy['id']],'steps':bad,
            'budget':w['plan']['budget'],'expires':time.time()+500},ok=False)
        self.authorize(w)
        with self.kernel.db() as db:
            raw=db.execute('SELECT payload FROM flow_grants WHERE work=?',(ident,)).fetchone()[0]
            g=json.loads(raw);g['budget']['files']=1000
            db.execute('UPDATE flow_grants SET payload=? WHERE work=?',(json.dumps(g),ident))
        result=self.run_step(w);self.assertEqual(result['reason'],'WORK_GRANT_DAMAGED')
        self.assertEqual(self.get(w)['state']['used']['steps'],0)

    def test_dependencies_and_typed_result_references_cannot_hide_an_outside_copy(self):
        steps=self.steps();steps[1]['after']=[]
        args={'title':'Bad dependency','assignment':self.assignment['id'],'copies':[self.copy['id']],'steps':steps,
            'budget':{'seconds':300,'steps':10,'tokens':0,'memory_mb':128,'output_bytes':1048576,'files':10},'expires':time.time()+500}
        self.call('work.create',args,ok=False)
        other=self.import_copy();steps=self.steps();steps[0]['arguments']['copy']=other['id'];args['steps']=steps
        self.call('work.create',args,ok=False)
        steps=self.steps();steps[0]['after']=['Apply'];args['steps']=steps
        self.call('work.create',args,ok=False)

    def test_failed_success_check_blocks_dependents_and_does_not_claim_completion(self):
        steps=self.steps();steps[0]['require']=[{'path':['text'],'equals':'green\n'}]
        w=self.create(steps);self.authorize(w);self.run_step(w)
        r=self.get(w);self.assertEqual(r['state']['state'],'WAITING')
        self.assertEqual(r['steps'][0]['state'],'FAILED');self.assertEqual(r['steps'][1]['state'],'PENDING')
        self.call('work.resume',{'id':w['plan']['id']},ok=False)
        self.assertEqual(self.run_step(w)['ran'],None)

    def test_file_token_output_and_attempt_budgets_persist_before_effects(self):
        w=self.create(budget={'files':0});self.authorize(w)
        self.run_step(w);self.run_step(w);result=self.run_step(w)
        self.assertEqual(result['reason'],'BUDGET_FILES')
        self.kernel=Kernel(self.root);self.assertEqual(self.get(w)['state']['used']['steps'],2)
        self.assertEqual((self.root/'Files'/self.copy['work']/'note.md').read_text(),'blue\n')
        self.call('work.revoke',{'id':w['plan']['id'],'reason':'Done with this test'})
        native=[{'key':'Model','operation':'workers.draft','arguments':{'copy':self.copy['id'],'paths':['note.md'],'goal':'Change blue',
            'model':'a'*64,'context':2048},'after':[]}]
        w=self.create(native);self.authorize(w)
        with patch.object(workers,'run_raw',side_effect=AssertionError('Native work must not start')):
            self.assertEqual(self.run_step(w)['reason'],'BUDGET_TOKENS')
        w=self.create([self.steps()[0]],{'output_bytes':1});self.authorize(w);self.run_step(w)
        self.assertEqual(self.get(w)['state']['state'],'LIMIT')
        step=self.steps()[0];step['retries']=1
        w=self.create([step],{'steps':1});self.authorize(w)
        with patch.object(flow,'read_file',side_effect=OSError('READ_FIXTURE_FAILURE')):
            self.assertEqual(self.run_step(w)['state'],'RETRY')
        retry=self.get(w)['state']['retry_at']
        with patch('time.time',return_value=retry+1):self.assertEqual(self.run_step(w)['reason'],'BUDGET_STEPS')

    def test_model_protocol_fixture_freezes_only_complete_current_exact_patches(self):
        from workbench import local_brain,brain_runtime
        base=hashlib.sha256(b'blue\n').hexdigest()
        candidate={'text':'Use black hands','changes':[{'path':'note.md','base_sha256':base,
            'edits':[{'start':0,'end':4,'old':'blue','new':'black'}]}]}
        run={'receipt':{'id':'1'*32,'state':'COMPLETED','fixture':'PROTOCOL_ONLY_NOT_CONTAINMENT'},
            'stdout':json.dumps({'ok':True,'result':{'candidate':candidate,'finish_reason':'length'}})}
        model={'id':'a'*64,'owner':self.p.identity,'files':[{'path':str(self.base/'fixture.gguf'),'name':'fixture.gguf','role':'weights'}]}
        args={'copy':self.copy['id'],'paths':['note.md'],'goal':'Use black hands','model':'a'*64}
        with patch.object(workers,'require_qualified'),patch.object(workers,'run_raw',return_value=run),\
             patch.object(local_brain,'model',return_value=model),patch.object(local_brain,'configuration',return_value={'threads':1}),\
             patch.object(local_brain,'recheck'),patch.object(brain_runtime,'prepare',return_value=(self.base/'llama-server',{'fixture':'PIN_PROTOCOL_ONLY'})):
            self.call('workers.draft',args,ok=False)
            payload=json.loads(run['stdout']);payload['result']['finish_reason']='stop';run['stdout']=json.dumps(payload)
            reply=self.call('workers.draft',args)
            review=self.call('changes.review',{'id':reply['proposal_id']})
            self.assertEqual(review['proposal']['changes'][0]['before'],base)
            self.assertEqual((self.root/'Files'/self.copy['work']/'note.md').read_text(),'blue\n')
            def stale(*a,**kw):
                (self.root/'Files'/self.copy['work']/'note.md').write_text('pink\n');return run
            with patch.object(workers,'run_raw',side_effect=stale):self.call('workers.draft',args,ok=False)

    def test_master_stop_epoch_requires_global_and_order_resume_and_revocation_stays_revoked(self):
        w=self.create();self.authorize(w);self.run_step(w)
        work_trail.hold(self.kernel,self.p);self.kernel=Kernel(self.root)
        self.assertEqual(self.run_step(w)['ran'],None)
        self.call('work.resume',{'id':w['plan']['id']},ok=False)
        self.call('ledger.work.resume')
        self.assertEqual(self.run_step(w)['reason'],'WORK_HELD_OR_EPOCH_CHANGED')
        self.call('work.resume',{'id':w['plan']['id']});self.run_step(w)
        self.call('work.revoke',{'id':w['plan']['id'],'reason':'Stop this plan'})
        self.call('work.resume',{'id':w['plan']['id']},ok=False)
        self.call('agenda.resume',{'id':self.get(w)['agenda']},ok=False)
        self.assertEqual(self.get(w)['state']['state'],'REVOKED')

    def test_same_size_preserved_mtime_outside_edit_and_expiry_block_continuation(self):
        w=self.create();self.authorize(w);self.run_step(w)
        path=self.root/'Files'/self.copy['work']/'note.md';before=path.stat();path.write_text('pink\n');os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
        result=self.run_step(w);self.assertIn(result['reason'],('WORKING_COPY_CHANGED','SOURCE_CHANGED_OR_UNAVAILABLE'))
        self.assertEqual(self.get(w)['state']['used']['steps'],1)
        path.write_text('blue\n');self.call('work.revoke',{'id':w['plan']['id'],'reason':'Expired test next'})
        w=self.create();self.authorize(w)
        with patch('time.time',return_value=w['plan']['expires']+1):self.assertEqual(self.run_step(w)['reason'],'GRANT_EXPIRED')

    def test_no_progress_rounds_stop_and_missed_legacy_recurrence_does_not_backfill(self):
        steps=[{'key':'Read'+str(i),'operation':'work.read','arguments':{'copy':self.copy['id'],'path':'note.md'},'after':[] if i==0 else ['Read'+str(i-1)]} for i in range(4)]
        w=self.create(steps);self.authorize(w)
        for _ in range(3):self.run_step(w)
        r=self.get(w);self.assertEqual(r['state']['reason'],'NO_PROGRESS_LIMIT');self.assertEqual(r['state']['used']['steps'],3)
        from workbench import agenda
        a=self.call('agenda.add',{'title':'Missed read','program':'work.read '+json.dumps({'copy':self.copy['id'],'path':'note.md'}),
            'when':{'at':time.time()-100000,'every_hours':1}})
        with agenda.opened(self.kernel) as db:
            db.execute("UPDATE agenda_items SET state='LATER' WHERE id=?",(a['id'],))
        self.call('agenda.view');self.call('agenda.run_next')
        with agenda.opened(self.kernel) as db:row=agenda.owned(db,a['id'],self.p.identity)
        self.assertEqual(row['rounds_used'],1);self.assertEqual(row['state'],'LATER');self.assertGreater(row['due'],time.time())

    def test_crash_after_application_reconciles_done_effect_without_reapplication(self):
        w=self.create(self.steps(True));self.authorize(w);self.run_step(w);self.run_step(w)
        with patch.object(flow,'CRASH_AT','EFFECT'):
            with self.assertRaises(flow.Crash):self.kernel.dispatch('work.advance',{'id':w['plan']['id']},self.p)
        self.kernel=Kernel(self.root);flow.pump(self.kernel)
        self.assertEqual(self.get(w)['state']['reason'],'INTERRUPTED_STEP_REQUIRES_EXPLICIT_RESUME')
        with patch.object(change_sets,'staged_file',side_effect=AssertionError('Completed mutation was repeated')):
            self.call('work.resume',{'id':w['plan']['id']});self.run_step(w)
        r=self.get(w);self.assertEqual(r['state']['state'],'REVIEW');self.assertTrue(r['steps'][2]['recovered'])
        self.assertEqual(r['state']['used']['steps'],4)

    def test_interrupted_proposal_is_reused_and_working_copy_revocation_stops_between_files(self):
        w=self.create();self.authorize(w);self.run_step(w)
        with patch.object(flow,'CRASH_AT','EFFECT'):
            with self.assertRaises(flow.Crash):self.kernel.dispatch('work.advance',{'id':w['plan']['id']},self.p)
        with self.kernel.db() as db:count=db.execute("SELECT count(*) FROM edit_records WHERE kind='proposal'").fetchone()[0]
        flow.pump(self.kernel);self.call('work.resume',{'id':w['plan']['id']});self.run_step(w)
        with self.kernel.db() as db:self.assertEqual(db.execute("SELECT count(*) FROM edit_records WHERE kind='proposal'").fetchone()[0],count)
        self.call('work.revoke',{'id':w['plan']['id'],'reason':'New batch next'})
        # A two-file application is stopped at the next boundary, with a recoverable retained batch.
        steps=self.steps();steps[1]['arguments']['operations'].append({'op':'CREATE','path':'draft.md','text':'new\n'})
        w=self.create(steps);self.authorize(w);self.run_step(w);self.run_step(w)
        original=change_sets.staged_file
        def revoke_after_one(*args,**kwargs):
            result=original(*args,**kwargs)
            self.call('work.revoke',{'id':w['plan']['id'],'reason':'Stop between files'})
            return result
        with patch.object(change_sets,'staged_file',side_effect=revoke_after_one):self.run_step(w)
        self.assertEqual(self.get(w)['state']['state'],'REVOKED')
        self.assertFalse((self.root/'Files'/self.copy['work']/'draft.md').exists())
        self.assertEqual((self.source/'note.md').read_text(),'blue\n')

    def test_procedure_parameters_make_new_ungranted_instances_and_keep_types(self):
        w=self.create();self.authorize(w)
        for _ in range(3):self.run_step(w)
        self.call('procedures.save',{'work':w['plan']['id'],'title':'Recolor','parameters':{}},ok=False)
        self.call('work.review',{'id':w['plan']['id'],'decision':'ACCEPT','note':'Reviewed the black note'})
        p=self.call('procedures.save',{'work':w['plan']['id'],'title':'Recolor','parameters':{
            'color':{'step':'Draft','path':['operations','0','text'],'type':'string'}}})
        second=self.import_copy()
        values={'id':p['id'],'assignment':self.assignment['id'],'copies':[second['id']],'values':{'color':'green\n'},'title':'New instance',
            'budget':w['plan']['budget'],'expires':time.time()+600}
        new=self.call('procedures.instantiate',values)
        self.assertEqual(new['state']['state'],'DRAFT');self.assertIsNone(new['grant'])
        self.assertEqual(new['plan']['steps'][1]['arguments']['copy'],second['id'])
        values['values']['color']=12;self.call('procedures.instantiate',values,ok=False)

    def test_worker_refusal_is_not_containment_and_unknown_migrations_are_refused(self):
        with patch.object(workers,'run_raw',side_effect=ValueError('BOUNDARY_UNAVAILABLE_TEST_FIXTURE')) as launch:
            q=self.call('workers.qualify',{'profile':'CHECK'})
        self.assertEqual(q['state'],'UNAVAILABLE_OR_FAILED');self.assertFalse(q['checks'])
        self.assertFalse(self.call('workers.status')['profiles']['CHECK']['qualified'])
        with patch('subprocess.Popen',side_effect=AssertionError('No unconfined fallback')):
            self.call('workers.check',{'copy':self.copy['id'],'paths':['parts.csv'],'check':'PARTS'},ok=False)
        from workbench import workspace_backup,state_backup
        with self.kernel.db() as db:
            db.execute('INSERT INTO worker_runs VALUES(?,?,?,?,?,?)',('2'*32,self.p.identity,'CHECK','ledger-worker-'+'3'*8+'-'+'2'*32+'.service','CLEANUP_REQUIRED','{}'))
        work_trail.hold(self.kernel,self.p);self.call('ledger.work.resume',ok=False)
        with self.assertRaises(state_backup.StateBusy):workspace_backup.create(self.root,self.base/'blocked-backup')
        self.assertFalse((self.base/'blocked-backup').exists())
        with self.kernel.db() as db:db.execute("INSERT INTO flow_migrations VALUES(2,'unknown',0)")
        with self.assertRaisesRegex(ValueError,'WORK_MIGRATION_UNSUPPORTED'):Kernel(self.root)


if __name__=='__main__':unittest.main()
