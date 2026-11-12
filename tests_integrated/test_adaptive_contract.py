"""Adaptive contract: exact interval semantics and the ACTION and legacy PLAN authority boundaries."""
import copy,json,unittest
from workbench import clock_lab,schedule_math,slate_action,adaptive_contract as contract,slate_reasoning


class ScheduleTests(unittest.TestCase):
    def setUp(self):self.problem=clock_lab.specification()
    def values(self,overlap=False):
        for v in self.problem['variables']:
            if v['name'].startswith('lifetime_'):
                start='9' if overlap and v['name']=='lifetime_workspace' else '10' if v['name']=='lifetime_workspace' else '0'
                stop='20' if v['name']=='lifetime_workspace' else '10'
                v.update(state='KNOWN',value=json.dumps({'start':start,'stop':stop,'unit':'s'}))
    def run_schedule(self):
        return schedule_math.evaluate(self.problem,'memory_limit',[{'quantity':'buffer_A','lifetime':'lifetime_A'},{'quantity':'buffer_B','lifetime':'lifetime_B'},{'quantity':'workspace','lifetime':'lifetime_workspace'}])
    def test_unknown_lifetimes_are_not_zero(self):
        result=self.run_schedule();self.assertEqual(result['state'],'UNKNOWN');self.assertEqual(len(result['missing']),3)
    def test_release_before_allocate_changes_peak(self):
        self.values();result=self.run_schedule();self.assertEqual(result['state'],'FEASIBLE');self.assertEqual(result['peak']['rational'],'12')
        self.values(True);result=self.run_schedule();self.assertEqual(result['state'],'INFEASIBLE');self.assertEqual(result['peak']['rational'],'17')
    def test_invalid_intervals_and_units_refused(self):
        self.values();v=next(v for v in self.problem['variables'] if v['name']=='lifetime_A')
        for x in ({'start':'1','stop':'1','unit':'s'},{'start':'-1','stop':'1','unit':'s'},{'start':'0','stop':'1','unit':'W'}):
            v['value']=json.dumps(x)
            with self.assertRaises(ValueError):self.run_schedule()


class ActionTests(unittest.TestCase):
    def frame(self,outcome='FAILURE'):
        cat=[{'operation':'work.read','arguments':contract.obj({'copy':{'type':'string','enum':['1'*32]},'path':contract.text(100)})}]
        return {'frontier':[{'key':'b1'}],'limits':{'frontier':3},'observations':[{'alias':'O1','outcome':outcome}],
            'catalogue':cat,'problem':{'variables':[{'name':'lifetime_A','state':'UNKNOWN'}]},
            'response_schema':contract.response_schema(cat,['O1'],['b1'])}
    def proposal(self):
        return {'text':'Check the saved input.','uncertainty':'What does it declare?','expected':['The file states the allocation.'],
            'alternatives':[],'updates':[],'next':{'kind':'CALL','candidate':'b1','operation':'work.read','arguments':{'copy':'1'*32,'path':'memory.csv'}}}
    def test_tool_failure_cannot_be_hypothesis_refutation(self):
        candidate=self.proposal();candidate['updates']=[{'candidate':'b1','disposition':'REJECT','reason':'It failed.','observations':['O1']}]
        with self.assertRaisesRegex(ValueError,'CANNOT_REFUTE'):slate_action.validate(candidate,self.frame())
        candidate['next']={'kind':'FINISH','text':'The recorded conditional check is adverse.','observations':['O1']}
        self.assertEqual(slate_action.validate(candidate,self.frame('ADVERSE'))['state'],'ACTION_PROPOSAL_VALIDATED')
    def test_schema_cannot_grant_or_select_another_copy(self):
        for mutate in (lambda c:c.update(reviewed=True),lambda c:c['next'].update(operation='changes.publish'),lambda c:c['next']['arguments'].update(copy='2'*32)):
            candidate=self.proposal();mutate(candidate)
            with self.assertRaises(ValueError):slate_action.validate(candidate,self.frame())
    def test_question_names_real_unknown_and_direct_answer_allowed(self):
        candidate=self.proposal();candidate['next']={'kind':'ASK','candidate':'b1','question':'When is A live?','missing':['lifetime_A']}
        self.assertEqual(slate_action.validate(candidate,self.frame())['state'],'ACTION_PROPOSAL_VALIDATED')
        candidate['next']['missing']=['invented']
        with self.assertRaises(ValueError):slate_action.validate(candidate,self.frame())
        candidate['next']={'kind':'FINISH','text':'A short title for this project.','observations':[]}
        slate_action.validate(candidate,self.frame())
    def test_legacy_plan_stays_read_only(self):
        self.assertNotIn('ACTION',slate_reasoning.TASKS)
        candidate={'text':'Propose it.','interpretation':'Edit a working copy.','questions':[],
            'actions':[{'operation':'changes.apply','arguments':{'id':'1'*32,'expected_digest':'a'*64}}]}
        with self.assertRaises(ValueError):slate_reasoning.validate_result('PLAN',candidate,{})

    def test_historical_or_rejected_branch_cannot_be_next_action(self):
        for mark in ({'historical':True},{'status':'REJECTED_FOR_RECORDED_CASE'}):
            frame=self.frame();frame['frontier'][0].update(mark)
            with self.assertRaisesRegex(ValueError,'INACTIVE_SELECTED_BRANCH'):slate_action.validate(self.proposal(),frame)

    def test_rejecting_branch_and_selecting_it_in_same_response_refused(self):
        candidate=self.proposal();candidate['updates']=[{'candidate':'b1','disposition':'REJECT','reason':'The recorded condition was false.','observations':['O1']}]
        with self.assertRaisesRegex(ValueError,'INACTIVE_SELECTED_BRANCH'):slate_action.validate(candidate,self.frame('ADVERSE'))

    def test_pending_adverse_observation_requires_model_interpretation(self):
        frame=self.frame('ADVERSE');frame['pending_adverse']=['O1'];candidate=self.proposal()
        with self.assertRaisesRegex(ValueError,'NEEDS_INTERPRETATION'):slate_action.validate(candidate,frame)
        candidate['updates']=[{'candidate':'b1','disposition':'REFINE','reason':'This conditional result needs another assumption checked.','observations':['O1']}]
        slate_action.validate(candidate,frame)

    def test_schedule_grammar_uses_declared_names_instead_of_copied_values(self):
        problem=clock_lab.specification();problem.update(id='a'*32,revision=1,context_digest='b'*64)
        for variable in problem['variables']:
            if variable['type']=='interval':variable.update(state='KNOWN',value=json.dumps({'start':'0','stop':'10','unit':'s'}))
        row=contract.catalogue({'operations':['math.schedule'],'copies':[]},problem)[0]
        validate=contract.validate_schema
        args={'capacity':'memory_limit','allocations':[{'quantity':'buffer_A','lifetime':'lifetime_A'}]}
        validate(args,row['arguments']);args['capacity']='16'
        with self.assertRaises(ValueError):validate(args,row['arguments'])
        args['capacity']='memory_limit';args['allocations'][0]['lifetime']=json.dumps({'start':'0','stop':'10','unit':'s'})
        with self.assertRaises(ValueError):validate(args,row['arguments'])

    def test_full_action_schema_rejects_unknown_kind_and_extra_next_fields(self):
        for change in (lambda c:c['next'].update(kind='INVENTED'),lambda c:c['next'].update(owner_approved=True)):
            candidate=self.proposal();change(candidate)
            with self.assertRaises(ValueError):slate_action.validate(candidate,self.frame())

    def test_schema_enforces_citation_bounds_duplicates_and_required_finish_receipt(self):
        frame=self.frame('ADVERSE');frame['observations'].append({'alias':'O2','outcome':'OBSERVED'})
        frame['response_schema']=contract.response_schema(frame['catalogue'],['O1','O2'],['b1'],allow_direct=False,finish_aliases=['O1','O2'])
        for refs in ([],['O1','O1']):
            candidate=self.proposal();candidate['next']={'kind':'FINISH','text':'The recorded conditional result.','observations':refs}
            with self.assertRaises(ValueError):slate_action.validate(candidate,frame)

    def test_adverse_feedback_must_address_the_branch_actually_tested(self):
        frame=self.frame('ADVERSE');frame['frontier'].append({'key':'b2'});frame['adverse_targets']={'O1':'b1'}
        frame['response_schema']=contract.response_schema(frame['catalogue'],['O1'],['b1','b2'])
        candidate=self.proposal();candidate['updates']=[{'candidate':'b2','disposition':'RETAIN','reason':'Another explanation is still possible.','observations':['O1']}]
        with self.assertRaisesRegex(ValueError,'TESTED_BRANCH_NEEDS_INTERPRETATION'):slate_action.validate(candidate,frame)


if __name__=='__main__':unittest.main()
