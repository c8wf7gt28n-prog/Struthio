"""Inquiry ownership, scoped invalidation and actual-receipt admission boundaries."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from workbench import discovery_ir as ir, discovery_service, math_model, project_desk
from workbench.engineering_kernel import Kernel, operator, Principal


def fixture(kernel, p):
    def call(op, args):
        result = kernel.dispatch(op, args, p)
        if not result['ok']: raise AssertionError(result)
        return result['result']
    files = kernel.root/'Files'; files.mkdir(exist_ok=True)
    for name in ('A', 'B'): (files/(name+'.txt')).write_text('Synthetic source '+name+' v1\n')
    variables = [{'name': n, 'type': 'quantity', 'unit': 'MiB', 'state': 'KNOWN', 'value': value, 'basis': 'Synthetic declared quantity.'}
                 for n, value in [('a','6'), ('b','6'), ('cap','8')]]
    problem = call('problems.create', {'request':'Compare declared quantities.', 'title':'Discovery fixture', 'goals':['Check declared comparisons.'], 'variables':variables, 'sources':[]})
    bound = {'id':problem['id'], 'expected_revision':problem['revision'], 'expected_context_digest':problem['context_digest']}
    document = ir.template(); document['title'] = 'Two conditional checks'
    document['goal'] = {'question':'Which declared checks fit these two branches?', 'stopping_criteria':['Keep the two conditional results and any missing information separate.']}
    actions = {}
    for suffix, expression in [('A','a + b <= cap'), ('B','a <= cap')]:
        action = call('math.prepare', {**bound, 'expression': expression})
        call('math.run', {'action':action['id']}); actions[suffix] = action['id']
        document['sources'].append({'key':'source'+suffix, 'address':'files:'+suffix+'.txt', 'role':'Synthetic context, not numeric provenance.'})
        document['assumptions'].append({'key':'assume'+suffix, 'text':'Declared scenario '+suffix, 'scope':'Only branch '+suffix, 'origin':'HUMAN', 'certainty':'DECLARED'})
        document['constraints'].append({'key':'constraint'+suffix, 'context':{'task':'EVALUATE', 'model':action['model']}, 'depends_on':['source'+suffix, 'assume'+suffix]})
        document['candidate_methods'].append({'key':'method'+suffix, 'algorithm':'dimensional_arithmetic', 'constraint':'constraint'+suffix, 'depends_on':[]})
        document['claims'].append({'key':'claim'+suffix, 'text':'Proposed conditional interpretation '+suffix, 'scope':'Declared numerical comparison only.', 'depends_on':['method'+suffix]})
    document['next_actions'] = [{'key':'reviewA', 'kind':'REVIEW', 'text':'Review the interpretation of branch A.', 'depends_on':['claimA']}]
    return document, actions, bound


def observation(inquiry, action, suffix='A', expected=False):
    return {'id':inquiry['id'], 'expected_revision':inquiry['revision'], 'target':'claim'+suffix, 'method':'method'+suffix,
            'reader':'MATH', 'receipt':action, 'predicate':{'kind':'BOOLEAN_OUTPUT', 'expected':expected, 'output':0}, 'note':'Synthetic bounded predicate only.'}


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        base = Path(temporary.name); root = base/'workspace'; root.mkdir()
        env = patch.dict(os.environ, {'ARC1_WORKBENCH_CONFIG_HOME':str(base/'profile'), 'ARC_LEDGER_CONCERN':str(base/'Concern')})
        env.start(); self.addCleanup(env.stop); self.kernel = Kernel(root); self.p = operator('owner')

    def call(self, operation, args=None, p=None):
        value = self.kernel.dispatch(operation, args or {}, p or self.p)
        self.assertTrue(value['ok'], value); return value['result']

    def create(self):
        document, actions, bound = fixture(self.kernel, self.p)
        inquiry = self.call('discovery.create', {'document':document})
        return document, actions, bound, inquiry

    def test_empty_question_capture_is_versioned_without_tool_execution(self):
        document = ir.template()
        with patch('subprocess.Popen') as spawn:
            inquiry = self.call('discovery.create', {'document':document})
            value = self.call('discovery.get', {'id':inquiry['id']}); spawn.assert_not_called()
        self.assertEqual(value['state'],'DRAFT'); self.assertFalse(value['completion']['allowed'])
        self.assertEqual(self.call('discovery.history', {'id':inquiry['id']})['revisions'][0]['revision'],1)
        with self.kernel.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0],0)
        changed=copy.deepcopy(inquiry['bindings']['protocol']);changed['schema_digest']='0'*64
        with patch.object(discovery_service,'protocol',return_value=changed):
            self.assertEqual(self.call('discovery.get',{'id':inquiry['id']})['state'],'STALE')

    def test_ir_rejects_cycles_dangling_edges_and_claimed_success(self):
        document, _, _ = fixture(self.kernel,self.p)
        cases=[]
        bad=copy.deepcopy(document);bad['claims'][0]['depends_on']=['missing'];cases.append(bad)
        bad=copy.deepcopy(document);bad['candidate_methods'][0]['depends_on']=['claimA'];cases.append(bad)
        bad=copy.deepcopy(document);bad['claims'][0]['status']='CHECKED_FORMAL';cases.append(bad)
        bad=copy.deepcopy(document);bad['observations']=[{'status':'CHECKED_NUMERIC'}];cases.append(bad)
        bad=copy.deepcopy(document);bad['experiments']=[{'key':'exec','method':'methodA','question':'Check','expected':[],'depends_on':[],'operation':'jobs.submit'}];cases.append(bad)
        bad=copy.deepcopy(document);bad['title']=' ';cases.append(bad)
        for bad in cases:self.assertFalse(self.kernel.dispatch('discovery.validate',{'document':bad},self.p)['ok'])

    def test_owner_isolation_includes_sources_history_and_receipts(self):
        document, actions, _, inquiry=self.create();other=operator('other')
        for op in ('discovery.get','discovery.history'):
            self.assertFalse(self.kernel.dispatch(op,{'id':inquiry['id']},other)['ok'])
        self.assertEqual(self.call('discovery.list',p=other)['inquiries'],[])
        idea=self.call('ideas.capture',{'text':'Private source'})
        document['sources'][0]['address']='idea:'+idea['id']
        self.assertFalse(self.kernel.dispatch('discovery.create',{'document':document},other)['ok'])
        own=self.call('discovery.create',{'document':ir.template()},other)
        self.assertFalse(self.kernel.dispatch('discovery.observe',observation(inquiry,actions['A']),other)['ok'])

    def test_compare_and_swap_and_historical_document_are_preserved(self):
        document, _, _, inquiry=self.create();original=copy.deepcopy(inquiry)
        document['title']='New explicit revision'
        updated=self.call('discovery.revise',{'id':inquiry['id'],'expected_revision':1,'document':document})
        self.assertEqual(updated['revision'],2)
        self.assertFalse(self.kernel.dispatch('discovery.revise',{'id':inquiry['id'],'expected_revision':1,'document':document},self.p)['ok'])
        old=self.call('discovery.get',{'id':inquiry['id'],'revision':1})
        self.assertTrue(old['historical_revision']);self.assertEqual(old['inquiry'],original)

    def test_actual_checked_predicate_does_not_promote_free_text(self):
        _, actions, _, inquiry=self.create()
        result=self.call('discovery.observe',observation(inquiry,actions['A'],expected=True))
        self.assertEqual(result['check']['grade'],'CHECKED_NUMERIC');self.assertEqual(result['check']['state'],'MISMATCH')
        view=self.call('discovery.get',{'id':inquiry['id']});claim=next(n for n in view['nodes'] if n['key']=='claimA')
        self.assertEqual(claim['status'],'REVIEW_REQUIRED');self.assertEqual(claim['predicate_summary'],'MISMATCH_PRESENT')
        self.assertFalse(view['completion']['allowed']);self.assertEqual(view['inquiry']['document']['claims'][0]['text'],'Proposed conditional interpretation A')

    def test_source_change_invalidates_only_its_declared_branch(self):
        _, actions, _, inquiry=self.create()
        first=self.call('discovery.observe',observation(inquiry,actions['A']));inquiry['revision']=first['revision']
        self.call('discovery.observe',observation(inquiry,actions['B'],'B',True))
        (self.kernel.root/'Files/A.txt').write_text('Synthetic source A changed')
        value=self.call('discovery.get',{'id':inquiry['id']});nodes={n['key']:n for n in value['nodes']}
        self.assertEqual(nodes['claimA']['status'],'STALE');self.assertEqual(nodes['reviewA']['status'],'STALE')
        self.assertEqual(nodes['claimB']['status'],'REVIEW_REQUIRED');self.assertEqual(nodes['sourceB']['status'],'CURRENT')
        self.assertEqual({o['target']:o['status'] for o in value['observations']},{'claimA':'STALE','claimB':'CURRENT'})

    def test_rebinding_keeps_old_checks_and_accepts_a_new_explicit_link(self):
        document, actions, _, inquiry=self.create()
        old=self.call('discovery.observe',observation(inquiry,actions['A']));inquiry['revision']=old['revision']
        document['assumptions'][0]['text']='Explicit revised scenario A'
        inquiry=self.call('discovery.revise',{'id':inquiry['id'],'expected_revision':inquiry['revision'],'document':document})
        new=self.call('discovery.observe',observation(inquiry,actions['A']))
        value=self.call('discovery.get',{'id':inquiry['id']})
        self.assertEqual(len(value['observations']),2)
        self.assertEqual([o['status'] for o in value['observations']],['STALE','CURRENT'])
        self.assertEqual(next(n for n in value['nodes'] if n['key']=='claimA')['status'],'REVIEW_REQUIRED')
        self.assertNotEqual(old['observation'],new['observation'])

    def test_identical_observation_is_idempotent_and_preparation_is_not_execution(self):
        _, actions, bound, inquiry=self.create();args=observation(inquiry,actions['A'])
        first=self.call('discovery.observe',args);args['expected_revision']=first['revision']
        again=self.call('discovery.observe',args)
        self.assertTrue(again['replayed']);self.assertEqual(again['observation'],first['observation'])
        prepared=self.call('math.prepare',{**bound,'expression':'a + b <= cap'})
        args['receipt']=prepared['id'];args['note']='Not executed'
        response=self.kernel.dispatch('discovery.observe',args,self.p)
        self.assertFalse(response['ok']);self.assertIn('NOT_EXECUTED',response['error']['message'])

    def test_wrong_model_or_unrelated_method_cannot_supply_a_checked_claim(self):
        _, actions, _, inquiry=self.create()
        args=observation(inquiry,actions['B'])
        self.assertFalse(self.kernel.dispatch('discovery.observe',args,self.p)['ok'])
        args['receipt']=actions['A'];args['method']='methodB'
        self.assertFalse(self.kernel.dispatch('discovery.observe',args,self.p)['ok'])

    def test_unknown_values_and_missing_profiles_never_become_success(self):
        document=ir.template();document['constraints']=[{'key':'unknown','context':{'task':'EVALUATE'},'depends_on':[]}]
        document['candidate_methods']=[{'key':'pending','algorithm':'dimensional_arithmetic','constraint':'unknown','depends_on':[]}]
        inquiry=self.call('discovery.create',{'document':document})
        nodes=self.call('discovery.get',{'id':inquiry['id']})['nodes']
        self.assertEqual(next(n for n in nodes if n['key']=='pending')['status'],'NEEDS_INPUT')
        for state in ('UNKNOWN','UNAVAILABLE','UNSUPPORTED','DOMAIN_ERROR'):
            synthetic={'snapshot':{'receipt':{'snapshot':{'state':state,'outputs':[{'state':'EXACT','value':True}]}}}}
            checked=discovery_service.check_predicate(synthetic,'MATH',{'kind':'BOOLEAN_OUTPUT','expected':True,'output':0})
            self.assertEqual(checked['grade'],'OBSERVED_ONLY');self.assertEqual(checked['state'],'UNRESOLVED')

    def test_schedule_links_require_the_admitted_profile_and_current_problem(self):
        from tests_integrated.test_algorithm_atlas import problem_call,resource_context
        problem=problem_call(self.kernel,self.p);context=resource_context(problem)
        document=ir.template();document['constraints']=[{'key':'capacity','context':context,'depends_on':[]}]
        document['candidate_methods']=[{'key':'sweep','algorithm':'interval_capacity','constraint':'capacity','depends_on':[]}]
        document['claims']=[{'key':'fits','text':'Proposed fit statement','scope':'Declared additive half-open model only.','depends_on':['sweep']}]
        inquiry=self.call('discovery.create',{'document':document})
        schedule=self.call('math.schedule',{**context['problem'],'capacity':context['capacity'],'allocations':context['allocations']})
        args={'id':inquiry['id'],'expected_revision':1,'target':'fits','method':'sweep','reader':'SCHEDULE','receipt':schedule['id'],
              'predicate':{'kind':'CAPACITY_FITS','expected':True},'note':'Exact fixture schedule.'}
        result=self.call('discovery.observe',args);self.assertEqual(result['check']['state'],'MATCH')
        document['constraints'][0]['context']['declarations']['interval_semantics']='CLOSED'
        revised=self.call('discovery.revise',{'id':inquiry['id'],'expected_revision':result['revision'],'document':document})
        args['expected_revision']=revised['revision']
        blocked=self.kernel.dispatch('discovery.observe',args,self.p)
        self.assertFalse(blocked['ok']);self.assertIn('NOT_ADMITTED',blocked['error']['message'])
        self.call('problems.revise',{**context['problem'],'title':'Changed owned problem'})
        view=self.call('discovery.get',{'id':inquiry['id']})
        self.assertEqual(next(n for n in view['nodes'] if n['key']=='fits')['status'],'STALE')

    def test_read_scope_can_inspect_but_cannot_save_or_link(self):
        _,actions,_,inquiry=self.create();reader=Principal('owner')
        self.call('discovery.get',{'id':inquiry['id']},reader)
        self.assertFalse(self.kernel.dispatch('discovery.create',{'document':ir.template()},reader)['ok'])
        self.assertFalse(self.kernel.dispatch('discovery.observe',observation(inquiry,actions['A']),reader)['ok'])

    def test_stac_inspection_uses_the_real_principal_and_has_no_execution_stage(self):
        inquiry=self.call('discovery.create',{'document':ir.template()})
        program='inquiry '+inquiry['id']+' | inspect'
        result=self.call('stac.run',{'program':program},Principal('owner'))
        self.assertEqual(result['result']['inquiry']['id'],inquiry['id'])
        self.assertFalse(self.kernel.dispatch('stac.run',{'program':program},Principal('other'))['ok'])
        self.assertFalse(self.kernel.dispatch('stac.run',{'program':program+' | run'},self.p)['ok'])


if __name__=='__main__':unittest.main()
