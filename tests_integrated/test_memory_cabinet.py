"""Private memory filing, source withholding and atomic correction history."""
import hashlib,json,os,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch
from workbench import memory_cabinet,memory_service,ledger_control,stacy_control
from workbench.engineering_kernel import Kernel,operator,Principal
from workbench.session import Session


class MemoryCabinetTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name)
        self.root=self.base/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(self.base/'profile'),'ARC_LEDGER_CONCERN':str(self.base/'Concern')})
        env.start();self.addCleanup(env.stop);self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.session=Session(self.base/'profile/session.json',self.root);self.session.save();ledger_control.bind(self.kernel,self.session)

    def call(self,op,args=None,principal=None):
        result=self.kernel.dispatch(op,args or {},principal or self.owner);self.assertTrue(result['ok'],result);return result['result']

    def direction(self,text='Keep the assumptions visible.',preference='technical_depth',context='general'):
        return self.call('memory.feedback',dict(id=uuid.uuid4().hex,preference=preference,context=context,feedback=1,
            instruction=text,source_reference='Explicit owner test direction',kind='owner_statement',soft=False))

    def detail(self,ident,principal=None):return self.call('ledger.cabinet.get',{'id':'memory:feedback:'+ident},principal)['record']

    def revision(self,old,text='Separate assumptions from measurements.'):
        return dict(id=old['id'],replacement=uuid.uuid4().hex,expected_history=self.detail(old['id'])['history_digest'],instruction=text,reason='Owner clarified the wording.')

    def test_cabinet_uses_existing_private_identities_without_running_or_rechecking_sources(self):
        direction=self.direction();task=self.call('memory.task.create',{'title':'Keep the power study connected'})
        lesson=self.call('memory.lesson.propose',{'title':'A proposed check','body':'PROCEDURE_BODY_SENTINEL','references':[]})
        with patch('subprocess.Popen',side_effect=AssertionError('No process')),patch.object(memory_service,'recheck_references',side_effect=AssertionError('No source recheck')):
            model=self.call('ledger.cabinet');detail=self.call('ledger.cabinet.get',{'id':'memory:lesson:'+lesson['id']})
        ids={row['id'] for row in model['nodes']}
        self.assertTrue({'memory:root','memory:directions','memory:tasks','memory:procedures','memory:feedback:'+direction['id'],'memory:task:'+task['id']}<=ids)
        self.assertIsNone(detail['record']['body']);self.assertEqual(detail['record']['binding_state'],'NOT_RECHECKED')
        self.assertNotIn('PROCEDURE_BODY_SENTINEL',json.dumps(detail));self.assertEqual(self.kernel.listing('jobs'),[])

    def test_checked_procedure_reader_still_withholds_unavailable_text(self):
        lesson=self.call('memory.lesson.propose',{'title':'Saved procedure','body':'PROCEDURE_BODY_SENTINEL','references':[]})
        self.call('memory.lesson.review',{'id':lesson['id'],'approved':True,'reason':'Explicit review'})
        detail=self.call('ledger.cabinet.get',{'id':'memory:lesson:'+lesson['id']});action=detail['actions'][0]
        with patch.object(memory_service,'recheck_references',return_value=([],[{'id':'missing','state':'UNAVAILABLE'}])):
            checked=self.call(action['operation'],action['arguments'])
        self.assertIsNone(checked['lessons'][0]['body']);self.assertEqual(checked['lessons'][0]['applicability'],'SOURCE_GAPS')

    def test_owner_tutor_and_cloud_boundaries_apply_to_reading_and_corrections(self):
        original=self.direction();args=self.revision(original)
        other=self.call('memory.cabinet',principal=operator('other'));self.assertEqual(other['records'],[])
        self.assertFalse(self.kernel.dispatch('ledger.cabinet.get',{'id':'memory:feedback:'+original['id']},operator('other'))['ok'])
        for principal in (Principal('owner'),Principal('owner',self.owner.scopes,mode='Tutor')):
            self.assertFalse(self.detail(original['id'],principal)['editable'])
            self.assertFalse(self.kernel.dispatch('memory.direction.revise',args,principal)['ok'])
        for operation,arguments in [('memory.cabinet',{}),('memory.direction.revise',args)]:
            proposal=stacy_control.call(operation,arguments)
            with self.assertRaises(ValueError):stacy_control.validate_actions([proposal],self.owner,provider=True)

    def test_correction_keeps_all_old_words_and_original_undo_reactivates_them(self):
        first=self.direction();second=self.direction('Be precise without losing the question.')
        changed=self.call('memory.direction.revise',self.revision(second))['record']
        events={row['id']:row for row in self.call('memory.feedback.list')['events']}
        self.assertEqual(events[first['id']],first);self.assertEqual(events[second['id']],second)
        self.assertTrue({first['id'],second['id']}<=set(changed['supersedes']))
        self.assertEqual(changed['kind'],'owner_correction');self.assertFalse(changed['soft'])
        self.assertEqual(self.detail(first['id'])['state'],'SUPERSEDED')
        self.call('memory.feedback.undo',{'id':changed['id']})
        self.assertEqual(self.detail(first['id'])['state'],'ACTIVE');self.assertEqual(self.detail(second['id'])['state'],'ACTIVE')

    def test_competing_family_update_blocks_stale_correction_without_creating_an_event(self):
        first=self.direction();args=self.revision(first);self.direction('Another owner statement for the same context.')
        before=self.call('memory.feedback.list')
        self.assertFalse(self.kernel.dispatch('memory.direction.revise',args,self.owner)['ok'])
        self.assertEqual(self.call('memory.feedback.list'),before)

    def test_an_unrelated_context_does_not_invalidate_the_inspected_history(self):
        first=self.direction();args=self.revision(first);self.direction('Keep exploratory replies brief.',context='creative_exploration')
        self.assertFalse(self.call('memory.direction.revise',args)['duplicate'])

    def test_retry_is_idempotent_and_conflicting_replacement_id_is_refused(self):
        first=self.direction();args=self.revision(first);one=self.call('memory.direction.revise',args);two=self.call('memory.direction.revise',args)
        self.assertTrue(two['duplicate']);self.assertEqual(one['record']['id'],two['record']['id'])
        self.assertEqual(len(self.call('memory.feedback.list')['events']),2)
        args['instruction']='Different request with the same ID'
        self.assertFalse(self.kernel.dispatch('memory.direction.revise',args,self.owner)['ok'])

    def test_forgotten_or_incomplete_history_is_not_reactivated_or_overwritten(self):
        first=self.direction();args=self.revision(first);self.call('memory.feedback.forget',{'id':first['id']})
        detail=self.detail(first['id']);self.assertEqual(detail['state'],'FORGOTTEN');self.assertNotIn(first['instruction'],json.dumps(detail))
        self.assertFalse(self.kernel.dispatch('memory.direction.revise',args,self.owner)['ok'])
        good=self.direction();bad=self.direction('A corrupt event')
        with self.kernel.db() as db:db.execute("UPDATE stacy_memory SET payload=? WHERE id=?",(b'non-text SQLite payload',bad['id']))
        detail=self.detail(good['id']);self.assertEqual(detail['state'],'HISTORY_INCOMPLETE');self.assertFalse(detail['editable'])
        self.assertTrue(self.call('memory.cabinet')['partial'])

    def test_original_feedback_constraints_and_new_input_bounds_still_hold(self):
        first=self.direction();args=self.revision(first)
        for change in ({'instruction':'x'*301},{'instruction':'  '},{'reason':''},{'reason':'x'*201}):
            self.assertFalse(self.kernel.dispatch('memory.direction.revise',{**args,**change},self.owner)['ok'])
        direct=dict(id=uuid.uuid4().hex,preference='technical_depth',context='general',feedback=1,instruction='Invalid soft correction',source_reference='Owner',kind='owner_correction',soft=True)
        self.assertFalse(self.kernel.dispatch('memory.feedback',direct,self.owner)['ok'])
        for limit in (0,1001):self.assertFalse(self.kernel.dispatch('memory.cabinet',{'limit':limit},self.owner)['ok'])
        self.assertEqual(len(self.call('memory.feedback.list')['events']),1)


if __name__=='__main__':unittest.main()
