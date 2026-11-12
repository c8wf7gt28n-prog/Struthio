"""Reasoning graphs: finite evidence decides nothing beyond what was observed, and exact lab outputs are parsed strictly."""
import copy,json,tempfile,unittest
from pathlib import Path
from workbench import reason_graph,lab_service
from workbench.reason_service import memory_graph


class ReasonGraphTests(unittest.TestCase):
    def setUp(self):
        self.graph=memory_graph('1'*32,'2'*32)
        self.observations={n:{'state':'OBSERVED','applicability':'CURRENT','value':False} for n in ('exact','experiment')}

    def test_lost_alternative_changes_reasons_without_verdict(self):
        before=reason_graph.compute(self.graph,self.observations)
        self.observations['experiment'].update(applicability='STALE')
        after=reason_graph.compute(self.graph,self.observations)
        self.assertEqual((before['state'],after['state']),('SUPPORTED','SUPPORTED'))
        self.assertEqual((len(before['paths']['positive']),len(after['paths']['positive'])),(2,1))
        self.assertNotEqual(before['reason_digest'],after['reason_digest'])

    def test_disagreement_preserves_both_directions(self):
        self.observations['experiment']['value']=True
        value=reason_graph.compute(self.graph,self.observations)
        self.assertEqual(value['state'],'CONFLICT')
        self.assertTrue(value['paths']['positive'] and value['paths']['negative'])

    def test_no_observations_does_not_establish_no_impact(self):
        for obs in self.observations.values():obs.update(state='UNAVAILABLE',applicability='NOT_ASSESSED')
        value=reason_graph.compute(self.graph,self.observations)
        self.assertEqual(value['state'],'UNKNOWN')
        self.assertEqual(value['coverage']['outside_graph'],'UNKNOWN')
        self.assertTrue(value['coverage']['missing_dependency_excludes_no_impact_claim'])

    def test_cycles_and_dangling_premises_refused(self):
        graph=copy.deepcopy(self.graph);graph['rules'][0]['premises'][0]['id']='conclusion'
        with self.assertRaisesRegex(ValueError,'CYCLE'):reason_graph.validate(graph)
        graph=copy.deepcopy(self.graph);graph['rules'][0]['premises'][0]['id']='unrecorded'
        with self.assertRaisesRegex(ValueError,'UNKNOWN_PREMISE'):reason_graph.validate(graph)

    def test_undeclared_assumptions_and_attestation_fields_refused(self):
        graph=copy.deepcopy(self.graph);graph['assumptions']=['Another scenario']
        with self.assertRaises(ValueError):reason_graph.validate(graph)
        graph=copy.deepcopy(self.graph);graph['nodes'][0]['reviewed']=True
        with self.assertRaises(ValueError):reason_graph.validate(graph)


class ExactOutputTests(unittest.TestCase):
    def test_svg_engineering_output_keeps_other_profile_boundaries(self):
        from workbench.import_profiles import eligibility
        self.assertIsNone(eligibility('Experiments/Results/run/board.svg','ENGINEERING'))
        self.assertEqual(eligibility('board.svg','CODE'),'OUTSIDE_SELECTED_PROFILE')
        for path in ('credentials.json','.env','id_rsa','private.key'):
            self.assertIsNotNone(eligibility(path,'ENGINEERING'))

    def parse(self,raw):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'result.json';path.write_text(raw);return lab_service.parse_output(path)

    def test_units_exact_values_and_duplicate_keys_checked(self):
        valid={'schema':'ledger.experiment-output/1','measurements':[{'name':'x','value':'5/4','unit':'W'}],'assumptions':['Declared current.']}
        self.assertEqual(self.parse(json.dumps(valid)),valid)
        for measurement in ({'name':'x','value':1.25,'unit':'W'},{'name':'x','value':'1','unit':'unicorn'},{'name':'x','value':True,'unit':'V'}):
            value={**valid,'measurements':[measurement]}
            with self.assertRaises((ValueError,TypeError)):self.parse(json.dumps(value))
        with self.assertRaises(ValueError):self.parse('{"schema":"wrong","schema":"ledger.experiment-output/1","measurements":[],"assumptions":[]}')


if __name__=='__main__':unittest.main()
