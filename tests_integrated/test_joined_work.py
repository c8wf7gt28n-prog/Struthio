"""Joined and method work: producer identity, result scope and stable recovery keys; a saved checked preview continues only to its
exact preparation (the saved step is the fixture joined_work_case.json)."""
import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import adaptive_work as controller,adaptive_contract as contract,clock_lab,checked_methods,slate_action


class JoinedAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.problem={**clock_lab.specification(),'id':'a'*32,'revision':1,'context_digest':'b'*64}
        self.copy='c'*32;self.job='d'*32;self.schedule='e'*32
        self.result={'job':self.job,'state':'AVAILABLE','receipt':{'id':self.job,'kind':'method_result',
            'receipt':self.schedule,'action':'f'*32,'method':{'id':'1'*32,'revision':2,'digest':'2'*64},
            'snapshot':{'state':'FEASIBLE','peak':{'rational':'9','unit':'A'},'fits':True}}}
        self.plan={'operations':['joined.prepare','joined.result','methods.result'],'copies':[self.copy]}
        self.state={'frontier':[{'key':'b1','status':'PROPOSED'}],'observations':['observation']}

    def call(self,operation,arguments):
        with patch.object(controller,'foundations',return_value=self.problem),patch.object(controller,'observation',return_value={'result':self.result}):
            return controller.validate_call(None,self.plan,self.state,{'candidate':'b1','operation':operation,'arguments':arguments},None)

    def test_method_summary_can_continue_only_with_its_actual_producer(self):
        prepared={'schema':'arc.tool-action/1','id':'7'*32,'kind':'method_action','binding_digest':'8'*64}
        self.assertEqual(controller.classify(prepared),'PREPARED')
        self.assertFalse(controller.summarize(prepared)['execution_started'])
        self.assertEqual(controller.classify(self.result),'OBSERVED')
        self.assertEqual(controller.classify({**self.result,'state':'STALE'}),'FAILURE')
        shown=controller.summarize(self.result)
        args={'receipt':shown['receipt'],'method_job':shown['job'],'copy':self.copy}
        self.assertEqual(self.call('joined.prepare',args)[0],args)
        for changed in ({**args,'receipt':self.job},{**args,'method_job':'3'*32},{k:v for k,v in args.items() if k!='method_job'}):
            with self.assertRaises(ValueError):self.call('joined.prepare',changed)

    def test_new_result_readers_cannot_select_another_owned_job(self):
        for operation in ('joined.result','methods.result'):
            self.assertEqual(self.call(operation,{'job':self.job})[0],{'job':self.job})
            with self.assertRaisesRegex(ValueError,'JOB_OUTSIDE_GRANT'):self.call(operation,{'job':'4'*32})

    def test_recovery_lookup_uses_the_submission_namespace(self):
        for operation in ('joined.run','methods.run','math.office.run'):
            self.assertEqual(controller.pending_key({'operation':operation,'arguments':{'action':'5'*32}}),'math-office:'+'5'*32)
        self.assertEqual(controller.pending_key({'operation':'experiments.run','arguments':{'action':'5'*32}}),'lab:'+'5'*32)
        self.assertEqual(controller.pending_key({'operation':'slate.action','request':'6'*32}),'slate-action:'+'6'*32)

    def test_readiness_requires_actual_preparation_and_schedule_producers(self):
        plan={'operations':['methods.run','joined.prepare','joined.result'],'copies':[self.copy]}
        catalogue=lambda:contract.catalogue(plan,self.problem)
        empty=controller.producer_readiness(catalogue(),[])
        self.assertFalse(any(row['available_now'] for row in empty))
        prepared={'id':'7'*32,'kind':'method_action','binding_digest':'8'*64}
        rows=controller.producer_readiness(catalogue(),[{'operation':'methods.instantiate','result':prepared}])
        self.assertEqual(rows[0]['arguments']['properties']['action']['enum'],[prepared['id']])
        self.assertTrue(rows[0]['available_now']);self.assertFalse(rows[1]['available_now'])
        rows=controller.producer_readiness(catalogue(),[{'operation':'methods.run','result':self.result}])
        self.assertEqual(rows[1]['arguments']['properties']['receipt']['enum'],[self.schedule])
        self.assertIn('method_job',rows[1]['arguments']['required'])
        rows=controller.producer_readiness(catalogue(),[{'operation':'methods.instantiate','result':prepared},
            {'operation':'methods.run','arguments':{'action':prepared['id']},'result':self.result}])
        self.assertFalse(rows[0]['available_now']);self.assertTrue(rows[1]['available_now'])

    def test_completion_requires_current_checked_outputs_or_verified_precondition(self):
        plan={'adaptive':{'completion':contract.APPLICATION_COMPLETION}}
        state={'observations':['o1'],'problem':{'expected_context_digest':self.problem['context_digest']}}
        row={'context_digest':self.problem['context_digest'],'operation':'methods.run','result':self.result,'arguments':{}}
        with patch.object(controller,'observation',return_value=row):
            self.assertFalse(controller.completion_evidence(None,plan,state,None)['satisfied'])

        row.update(operation='joined.run',result={'job':self.job,'receipt':{'kind':'joined_result'}})
        live={'state':'AVAILABLE','receipt':{'artifacts':[{'type':kind} for kind in contract.APPLICATION_TYPES]}}
        with patch.object(controller,'observation',return_value=row),patch('workbench.joined_work.result',return_value=live):
            self.assertEqual(controller.completion_evidence(None,plan,state,None)['finish_observations'],['O1'])
            live['state']='STALE';self.assertFalse(controller.completion_evidence(None,plan,state,None)['satisfied'])
        row.update(operation='methods.preview',result={'precondition_rejected':True,'state':'UNSUPPORTED'})
        with patch.object(controller,'observation',return_value=row),patch('workbench.checked_methods.dispatch',return_value=row['result']):
            self.assertTrue(controller.completion_evidence(None,plan,state,None)['satisfied'])
            row['result']['precondition_rejected']=False
            self.assertFalse(controller.completion_evidence(None,plan,state,None)['satisfied'])

    def test_stale_preview_remains_unsupported_without_proving_a_precondition(self):
        checked={'kind':'method_preview','state':'SUPPORTED','binding_current':True,'precondition_rejected':False}
        self.assertEqual(controller.classify(checked),'OBSERVED');self.assertTrue(controller.summarize(checked)['check_completed'])
        self.assertFalse(controller.summarize(checked)['method_execution_started'])
        args={'id':self.problem['id'],'expected_revision':9,'expected_context_digest':self.problem['context_digest'],
            'method':'1'*32,'method_revision':2,'declarations':{**checked_methods.EXPECTED,'basis':'Declared synthetic inputs'},
            'capacity':'memory_limit','allocations':[{'quantity':'buffer_A','lifetime':'lifetime_A'}]}
        with patch.object(checked_methods.math_service,'current',return_value=self.problem):
            result=checked_methods.dispatch(None,'methods.preview',args,None)
        self.assertEqual(result['state'],'UNSUPPORTED');self.assertFalse(result['binding_current']);self.assertFalse(result['precondition_rejected'])


class CheckedMappingReplayTests(unittest.TestCase):
    def setUp(self):
        case=json.loads((Path(__file__).resolve().parent/'joined_work_case.json').read_text())  # one saved methods.preview step, fixed
        saved=case['saved_observation'];preview=saved['result']
        problem={'id':preview['problem'],'revision':preview['problem_revision'],'context_digest':preview['context_digest'],
            'variables':[{'name':v['name'],'type':v['type'],'state':'KNOWN'} for v in case['variables']]}
        catalogue=contract.catalogue({'operations':['methods.preview','methods.instantiate'],'copies':[]},problem)
        for row in catalogue:row['arguments']['properties']['method']={'type':'string','enum':[preview['method_id']]}
        self.args={k:v for k,v in saved['arguments'].items() if k not in ('id','expected_revision','expected_context_digest')}
        self.frame={'problem':problem,'catalogue':catalogue,'accepted_methods':[case['qualifying_method']],
            'observations':[{'alias':'O1','operation':saved['operation'],'arguments':copy.deepcopy(self.args),
                'outcome':saved['outcome'],'tested_branch':'b1','problem_revision':problem['revision'],
                'current_context':True,'actual':controller.summarize(preview)}],
            'frontier':case['frontier'],'active_frontier':['b1'],'working_files':{},
            'remaining_steps':29,'used':case['used'],'limits':case['limits'],
            'finish_policy':'Current checked application outputs required.','finish_observations':[],
            'pending_adverse':[],'adverse_targets':{}}

    def test_saved_repeated_preview_has_exact_checked_preparation_continuation(self):
        before=copy.deepcopy(self.frame)
        selected=slate_action.phase_view(self.frame)
        step=selected['checked_method_continuations'][0]
        self.assertEqual((step['from_observation'],step['operation']),('O1','methods.instantiate'))
        self.assertNotIn('arguments',step)  # SELECT stays small; ARGUMENTS gets the actual mapping.
        details=slate_action.phase_view(self.frame,'methods.instantiate')
        mapped=details['checked_method_continuations'][0]['arguments']
        self.assertEqual(mapped,self.args)
        contract.validate_schema(mapped,details['tool']['arguments'])
        self.assertEqual(details['current_finish_citations'],[])
        self.assertEqual(before,self.frame)
        self.assertTrue(all(tool['available_now'] for tool in selected['tools']))

    def test_stale_unsupported_unaccepted_and_unavailable_mappings_are_not_continuations(self):
        for change in (
            lambda f:f['observations'][0].update(current_context=False),
            lambda f:f['observations'][0].update(outcome='FAILURE'),
            lambda f:f['observations'][0]['actual'].update(state='UNSUPPORTED'),
            lambda f:f['observations'][0]['actual'].update(check_completed=False),
            lambda f:f['observations'][0]['actual'].update(method_revision=99),
            lambda f:f.update(accepted_methods=[]),
            lambda f:f['accepted_methods'][0].update(revision=99),
            lambda f:f['catalogue'][1].update(available_now=False),
            lambda f:f['catalogue'].pop(),
            lambda f:f['observations'][0]['arguments'].update(capacity='invented_variable'),
        ):
            frame=copy.deepcopy(self.frame);change(frame)
            with self.subTest(frame=frame):self.assertEqual(slate_action.method_continuations(frame),[])

    def test_already_attempted_preparation_does_not_offer_duplicate_but_other_mapping_remains(self):
        frame=copy.deepcopy(self.frame)
        frame['observations'].append({**frame['observations'][0],'alias':'O2','operation':'methods.instantiate','outcome':'PREPARED'})
        self.assertEqual(slate_action.method_continuations(frame),[])
        frame['observations'][-1]['outcome']='FAILURE'
        self.assertEqual(slate_action.method_continuations(frame),[])
        frame['observations'][-1]['arguments']={**self.args,'capacity':'heater'}
        self.assertEqual(slate_action.method_continuations(frame)[0]['arguments'],self.args)


if __name__=='__main__':unittest.main()
