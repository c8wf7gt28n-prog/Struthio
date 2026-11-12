"""Explore is metadata and navigation intent, never a second execution path."""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import explore,ledger_control,stacy_control
from workbench.engineering_kernel import Kernel,operator,Principal,CAPABILITIES,TOOLS
from workbench.session import Session


class ExploreTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ledger-explore-');self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.root=self.base/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(self.base/'profile'),'ARC_LEDGER_CONCERN':str(self.base/'Concern')})
        env.start();self.addCleanup(env.stop);self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.session=Session(self.base/'profile/session.json',self.root);self.session.save();ledger_control.bind(self.kernel,self.session)

    def call(self,op,args=None,principal=None):
        value=self.kernel.dispatch(op,args or {},principal or self.owner);self.assertTrue(value['ok'],value);return value['result']

    def snapshot(self,**args):return self.call('ledger.explore',args)

    def test_complete_registry_is_pageable_without_duplicate_or_invented_contracts(self):
        operations=[];tools=[]
        for kind,expected in [('OPERATION',set(CAPABILITIES)),('JOB_TOOL',set(TOOLS))]:
            entries=[];offset=0
            while True:
                page=self.snapshot(kind=kind,limit=100,offset=offset);entries+=page['entries']
                if not page['has_more']:break
                offset+=100
            self.assertEqual({r['key'] for r in entries},expected);self.assertEqual(len(entries),len(expected))
            self.assertTrue(all(r['inspect_only'] and r['qualification']=='UNASSESSED' for r in entries))

    def test_lookup_and_selection_metadata_never_launch_or_write_work(self):
        with self.kernel.db() as db:before=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
        with patch('subprocess.Popen',side_effect=AssertionError('No process launch')):
            value=self.snapshot(query='Python')
        self.assertTrue(value['entries']);self.assertEqual(value['native_invocations'],0)
        idea_search=self.snapshot(query='I want to test an idea',kind='INSTRUMENT')
        self.assertIn('inquiries',{r['key'] for r in idea_search['entries']})
        self.assertEqual(value['model_calls'],0);self.assertEqual(value['network_calls'],0)
        with self.kernel.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0],before)

    def test_suggestions_use_owned_record_kind_without_rewriting_or_claiming_a_fit(self):
        idea=self.call('ideas.capture',{'text':'A question worth developing.'})
        value=self.snapshot(context='idea:'+idea['id']);self.assertEqual(value['context']['canonical_id'],'idea:'+idea['id'])
        self.assertEqual([r['id'] for r in value['suggestions']],['documents','inquiries','calculate','laboratory'])
        self.assertTrue(all(r['basis']=='SELECTED_RECORD_KIND' for r in value['suggestions']))
        self.assertNotIn('record',value['context']);self.assertNotIn('text',value['context'])
        self.assertEqual(self.call('ideas.get',{'id':idea['id']}),idea)

    def test_private_or_stale_context_is_not_disclosed_to_another_caller(self):
        idea=self.call('ideas.capture',{'text':'Private birthday idea'})
        ident='idea:'+idea['id'];value=self.call('ledger.explore',{'context':ident},operator('other'))
        self.assertIsNone(value['context']);self.assertEqual(value['suggestions'],[]);self.assertEqual(value['context_actions'],[])
        self.assertNotIn(ident,json.dumps(value));self.assertNotIn(idea['text'],json.dumps(value));self.assertTrue(value['notices'])

    def test_active_job_counts_are_owner_scoped_and_do_not_expose_payloads(self):
        with self.kernel.db() as db:
            for ident,owner,state,tool in [('a','owner','Running','lab.python'),('b','owner','Queued','lab.python'),('c','other','Running','lab.python')]:
                payload=json.dumps(dict(id=ident,owner=owner,state=state,tool=tool,private='Do not include this payload'))
                db.execute('INSERT INTO jobs VALUES(?,?,?,?)',(ident,owner,state,payload))
        value=self.snapshot();lab=next(r for r in value['instruments'] if r['key']=='laboratory')
        self.assertEqual((lab['running_jobs'],lab['queued_jobs'],lab['active_jobs']),(1,1,2))
        self.assertNotIn('Do not include this payload',json.dumps(value))
        other=self.call('ledger.explore',{},operator('other'));lab=next(r for r in other['instruments'] if r['key']=='laboratory')
        self.assertEqual(lab['active_jobs'],1)

    def test_large_job_payload_is_omitted_with_an_explicit_bounded_counter_notice(self):
        with self.kernel.db() as db:db.execute('INSERT INTO jobs VALUES(?,?,?,?)',('huge','owner','Running',json.dumps({'tool':'lab.python','body':'x'*70000})))
        value=self.snapshot();self.assertTrue(value['job_counts_partial']);self.assertTrue(value['notices'])
        self.assertEqual(next(r for r in value['instruments'] if r['key']=='laboratory')['active_jobs'],0)

    def test_missing_view_remains_visible_and_cannot_be_advertised_openable(self):
        original=explore.capability_catalog.source
        def source(root,name):
            return dict(path=name,state='MISSING_OR_UNSAFE',sha256=None) if name=='workbench/brain_qt.py' else original(root,name)
        with patch.object(explore.capability_catalog,'source',side_effect=source):value=self.snapshot()
        entry=next(r for r in value['instruments'] if r['key']=='brain')
        self.assertFalse(entry['view_available']);self.assertEqual(entry['view_state'],'View unavailable')
        # Availability is a state word, not the action word (DESKTOP-01 V-17): the button says Open workspace, the row says available.
        self.assertTrue(all(r['view_state']=='Workspace available' for r in value['instruments'] if r['view_available']))
        self.assertNotIn('Open workspace',{r['view_state'] for r in value['instruments']})

    def test_unimplemented_methods_remain_reference_only(self):
        value=self.snapshot(kind='METHOD',query='shortest')
        self.assertEqual(len(value['entries']),1);entry=value['entries'][0]
        self.assertEqual(entry['key'],'shortest_path');self.assertEqual(entry['status'],'Reference only')
        self.assertFalse(entry['callable']);self.assertEqual(entry['operations'],[])

    def test_method_catalog_failure_keeps_instruments_and_exact_operations_available(self):
        with patch.object(explore.algorithm_atlas,'dispatch',side_effect=ValueError('Unreadable method corpus')):
            value=self.snapshot(kind='INSTRUMENT')
        self.assertEqual(len(value['entries']),len(explore.VIEWS));self.assertTrue(value['notices'])
        self.assertEqual(value['registered_operations'],len(CAPABILITIES))

    def test_missing_method_source_is_unavailable_rather_than_labeled_linked(self):
        original=explore.capability_catalog.source
        def source(root,name):
            return dict(path=name,state='MISSING_OR_UNSAFE',sha256=None) if name=='workbench/math_units.py' else original(root,name)
        with patch.object(explore.capability_catalog,'source',side_effect=source):value=self.snapshot(kind='METHOD',query='dimensional')
        self.assertEqual(len(value['entries']),1);entry=value['entries'][0]
        self.assertEqual(entry['implementation'],'SOURCE_MISSING');self.assertEqual(entry['status'],'Source unavailable');self.assertFalse(entry['callable'])

    def test_tutor_can_inspect_but_scope_is_not_execution_authority(self):
        tutor=Principal('owner',frozenset({'read'}),mode='Tutor')
        value=self.call('ledger.explore',{'kind':'OPERATION','query':'ideas.capture'},tutor)
        self.assertEqual(len(value['entries']),1);row=value['entries'][0]
        self.assertEqual(row['assessment']['permitted']['state'],'OUTSIDE_SCOPE');self.assertTrue(row['inspect_only'])
        self.assertFalse(self.kernel.dispatch('ideas.capture',{'text':'No write scope'},tutor)['ok'])

    def test_cloud_proposals_cannot_read_private_context_through_explore(self):
        proposal=stacy_control.call('ledger.explore',{})
        with self.assertRaises(ValueError):stacy_control.validate_actions([proposal],self.owner,provider=True)
        stacy_control.validate_actions([proposal],self.owner,provider=True,private_local=True)

    def test_query_is_literal_and_bounds_are_enforced(self):
        self.assertEqual(self.snapshot(query='; DROP TABLE jobs --')['entries'],[])
        for args in ({'query':'x'*181},{'limit':101},{'offset':-1},{'context':'x'*601},{'kind':'EXECUTE'}):
            self.assertFalse(self.kernel.dispatch('ledger.explore',args,self.owner)['ok'])
        self.assertEqual(self.kernel.listing('jobs'),[])


if __name__=='__main__':unittest.main()
