"""Selection identity, eligibility and passive action discovery boundaries."""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import cabinet,cabinet_actions,ledger_control,stacy_control,discovery_ir
from workbench.engineering_kernel import Kernel,operator,Principal
from workbench.session import Session


class CabinetActionTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name)
        self.root=self.base/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(self.base/'profile'),'ARC_LEDGER_CONCERN':str(self.base/'Concern')})
        env.start();self.addCleanup(env.stop);self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.session=Session(self.base/'profile/session.json',self.root);self.session.save();ledger_control.bind(self.kernel,self.session)

    def call(self,op,args=None,principal=None):
        value=self.kernel.dispatch(op,args or {},principal or self.owner);self.assertTrue(value['ok'],value);return value['result']

    def snapshot(self,ident,principal=None):return self.call('ledger.cabinet.actions',{'id':ident},principal)
    def project(self,title='Power supply'):return self.call('projects.create',{'title':title,'intent':'Keep original intent.'})

    def test_passive_ranking_preserves_saved_work_and_does_not_resolve_bindings(self):
        project=self.project();idea=self.call('ideas.capture',{'text':'A saved question.','project':project['id']})
        inquiry=self.call('discovery.create',{'document':discovery_ir.template(),'project':project['id']})
        with patch('subprocess.Popen',side_effect=AssertionError('No process launch')), \
             patch('workbench.discovery_service.view',side_effect=AssertionError('No automatic binding check')):
            value=self.snapshot('idea:'+idea['id']);question=self.snapshot('inquiry:'+inquiry['id'])
        self.assertEqual([r['id'] for r in value['actions']],['record','workspace:documents','workspace:inquiries','workspace:calculate','workspace:laboratory','explore'])  # an idea offers its page first
        self.assertTrue(all(r['basis']=='SELECTED_RECORD_KIND' for r in value['actions']))
        self.assertEqual(question['actions'][1]['operation'],'discovery.get')
        self.assertNotIn('record',value['context']);self.assertNotIn('document',json.dumps(question))
        self.assertEqual(self.call('ideas.get',{'id':idea['id']}),idea);self.assertEqual(self.kernel.listing('jobs'),[])

    def test_tutor_and_read_scope_can_inspect_but_cannot_prepare_writing(self):
        project=self.project();ident='project:'+project['id']
        for principal in (Principal('owner'),Principal('owner',self.owner.scopes,mode='Tutor')):
            value=self.snapshot(ident,principal);actions={r['id']:r for r in value['actions']}
            self.assertTrue(actions['record']['enabled']);self.assertTrue(actions['workspace:inquiries']['enabled'])
            self.assertFalse(actions['write']['enabled']);self.assertIn('scope',actions['write']['unavailable_reason'])
        own=self.snapshot(ident);writing=next(r for r in own['actions'] if r['id']=='write')
        self.assertTrue(writing['enabled']);self.assertEqual(writing['state'],'NEEDS_INPUT');self.assertNotIn('arguments',writing)

    def test_private_and_missing_records_share_generic_non_disclosing_result(self):
        idea=self.call('ideas.capture',{'text':'Private original'})
        for ident in ('idea:'+idea['id'],'idea:missing'):
            value=self.snapshot(ident,operator('other'))
            self.assertIsNone(value['context']);self.assertIsNone(value['signature']);self.assertEqual(value['actions'],[])
            self.assertNotIn(ident,json.dumps(value));self.assertNotIn('Private original',json.dumps(value))

    def test_reference_actions_preserve_placement_and_target_identity(self):
        first=self.project();second=self.project('Other filing place')
        idea=self.call('ideas.capture',{'text':'One original','project':first['id']})
        linked=self.call('projects.link',{'id':second['id'],'expected_revision':1,'role':'QUESTION','address':'idea:'+idea['id']})
        ref='project-reference:'+second['id']+':'+linked['links'][0]['id'];value=self.snapshot(ref)
        self.assertEqual(value['context']['id'],ref);self.assertEqual(value['context']['canonical_id'],'idea:'+idea['id'])
        read=next(r for r in value['actions'] if r['id']=='check:0')
        self.assertEqual(read['operation'],'ledger.address.read');self.assertEqual(read['arguments'],{'address':'idea:'+idea['id']})
        self.assertEqual(self.call('ideas.get',{'id':idea['id']})['project'],first['id'])

    def test_signature_is_stable_and_changes_with_reference_revision(self):
        project=self.project();ident='project:'+project['id'];before=self.snapshot(ident)
        self.assertEqual(before['signature'],self.snapshot(ident)['signature'])
        self.call('projects.link',{'id':project['id'],'expected_revision':1,'role':'QUESTION','text':'A new question'})
        self.assertNotEqual(before['signature'],self.snapshot(ident)['signature'])

    def test_missing_workspace_is_visible_with_a_specific_reason(self):
        idea=self.call('ideas.capture',{'text':'Inspect a calculation'});original=cabinet_actions.capability_catalog.source
        def source(root,name):
            return {'state':'MISSING_OR_UNSAFE'} if name=='workbench/calculator_qt.py' else original(root,name)
        with patch.object(cabinet_actions.capability_catalog,'source',side_effect=source):value=self.snapshot('idea:'+idea['id'])
        calculation=next(r for r in value['actions'] if r['id']=='workspace:calculate')
        self.assertFalse(calculation['enabled']);self.assertIn('missing or unsafe',calculation['unavailable_reason'])

    def test_separately_versioned_catalog_note_also_invalidates_an_old_action(self):
        from sdk.cli.arc1cli.concern_catalog import Catalog
        catalog=Catalog(cabinet.catalog_file(self.kernel));ident=catalog.create('note','Stable title','projects')
        catalog.save_note(ident,'First saved words',0);before=self.snapshot('catalog:'+ident)
        catalog.save_note(ident,'Changed saved words',1);after=self.snapshot('catalog:'+ident)
        self.assertNotEqual(before['signature'],after['signature'])
        self.assertNotIn('Changed saved words',json.dumps(after))

    def test_provider_cannot_advertise_a_write_as_a_read_or_invalid_read_inputs(self):
        project=self.project();ident='project:'+project['id'];original=cabinet.get(self.kernel,ident,self.owner)
        original['actions']=[dict(label='Unexpected write',operation='ideas.capture',arguments={'text':'Do not save'}),
                             dict(label='Bad read',operation='ideas.get',arguments={})]
        with patch.object(cabinet_actions.cabinet,'get',return_value=original):value=self.snapshot(ident)
        checks=[r for r in value['actions'] if r['id'].startswith('check:')]
        self.assertTrue(all(not r['enabled'] for r in checks));self.assertEqual(self.kernel.listing('jobs'),[])

    def test_schema_bounds_and_cloud_private_rules_apply_to_shared_read(self):
        for args in ({},{'id':''},{'id':'x'*601},{'id':'cabinet:concern','operation':'jobs.submit'}):
            self.assertFalse(self.kernel.dispatch('ledger.cabinet.actions',args,self.owner)['ok'])
        proposal=stacy_control.call('ledger.cabinet.actions',{'id':'cabinet:concern'})
        with self.assertRaises(ValueError):stacy_control.validate_actions([proposal],self.owner,provider=True)
        stacy_control.validate_actions([proposal],self.owner,provider=True,private_local=True)


if __name__=='__main__':unittest.main()
