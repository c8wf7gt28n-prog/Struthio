"""Risk-focused admission checks; solver examples are a separate bounded receipt."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from workbench import algorithm_atlas as atlas, capability_catalog, checked_methods, project_desk, stac_bridge
from workbench.engineering_kernel import Kernel, Principal, operator
from workbench.engineering_cli import schemas


def variables(unit='MiB'):
    return [
        {'name': name, 'type': 'quantity', 'unit': unit, 'value': amount, 'state': 'KNOWN', 'basis': 'Synthetic declared example.'}
        for name, amount in [('cap', '8'), ('a', '6'), ('b', '6')]
    ] + [
        {'name': name, 'type': 'interval', 'unit': 's', 'value': json.dumps({'start': start, 'stop': stop, 'unit': 's'}),
         'state': 'KNOWN', 'basis': 'Synthetic half-open interval.'}
        for name, start, stop in [('ta', '0', '10'), ('tb', '10', '20')]
    ]


def problem_call(kernel, principal, supplied=None):
    result = kernel.dispatch('problems.create', {'request': 'Check declared capacity.', 'title': 'Atlas fixture',
        'goals': ['Compare declared peak with fixed capacity.'], 'variables': supplied or variables(), 'sources': []}, principal)
    if not result['ok']: raise AssertionError(result)
    return result['result']


def resource_context(problem):
    return {'task': 'RESOURCE_PEAK', 'problem': {'id': problem['id'], 'expected_revision': problem['revision'],
        'expected_context_digest': problem['context_digest']}, 'capacity': 'cap',
        'allocations': [{'quantity': 'a', 'lifetime': 'ta'}, {'quantity': 'b', 'lifetime': 'tb'}],
        'declarations': {**checked_methods.EXPECTED, 'basis': 'Synthetic additive model, not measured physical behavior.'}}


class AlgorithmAtlasTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        base = Path(temporary.name); root = base/'workspace'; root.mkdir()
        environment = patch.dict(os.environ, {'ARC1_WORKBENCH_CONFIG_HOME': str(base/'profile'), 'ARC_LEDGER_CONCERN': str(base/'Concern')})
        environment.start(); self.addCleanup(environment.stop)
        self.kernel = Kernel(root); self.owner = operator('owner')

    def call(self, operation, args=None, principal=None):
        response = self.kernel.dispatch(operation, args or {}, principal or self.owner)
        self.assertTrue(response['ok'], response); return response['result']

    def check(self, context, algorithm=None, principal=None):
        args = {'context': context}
        if algorithm: args['algorithm'] = algorithm
        return self.call('algo.find_applicable', args, principal)['candidates'][0]

    def test_corpus_links_exact_contracts_and_preserves_planned_boundary(self):
        result = self.call('algo.lookup'); entries = result['entries']
        self.assertEqual(len(entries), 12)
        self.assertEqual(sum(bool(e['implementation']['operations']) for e in entries), 7)
        for entry in entries:
            self.assertTrue(entry['references']); self.assertTrue(entry['preconditions']); self.assertTrue(entry['counterexample'])
            self.assertEqual(entry['implementation']['qualification'], 'NOT_CURRENT_HOST_QUALIFIED')
            for operation in entry['implementation']['operations']:
                self.assertEqual(operation['arguments'], schemas()[operation['operation']])
            if not entry['implementation']['operations']:
                self.assertEqual(entry['implementation']['state'], 'NOT_IMPLEMENTED')
                self.assertEqual(self.check({'task': entry['task']})['applicability']['state'], 'NOT_IMPLEMENTED')

    def test_documented_valid_and_invalid_examples_never_launch_solver(self):
        entries = self.call('algo.lookup')['entries']
        with patch('subprocess.run') as launched:
            for entry in entries:
                for example in entry['examples']:
                    with self.subTest(method=entry['id'], example=example['label']):
                        value = self.check(example['context'], entry['id'])
                        self.assertEqual(value['applicability']['state'], example['expected_state'])
                        self.assertFalse(value['runtime_authorization'])
            launched.assert_not_called()

    def test_resource_profile_reuses_exact_units_and_refuses_false_transfer(self):
        for unit in ('MiB', 'mA'):
            problem = problem_call(self.kernel, self.owner, variables(unit)); context = resource_context(problem)
            self.assertEqual(self.check(context)['applicability']['state'], 'MATCH_WITH_OBLIGATIONS')
            for key, value in [('additive', False), ('interval_semantics', 'CLOSED'), ('overhead', 'PRESENT')]:
                bad = copy.deepcopy(context); bad['declarations'][key] = value
                self.assertEqual(self.check(bad)['applicability']['state'], 'REJECTED_INPUT')
        mixed = variables(); mixed[1]['unit'] = 'A'
        context = resource_context(problem_call(self.kernel, self.owner, mixed))
        self.assertIn('DIMENSION_MISMATCH', self.check(context)['applicability']['reasons'][0])
        unknown = variables(); unknown[-1].update(state='UNKNOWN'); unknown[-1].pop('value')
        context = resource_context(problem_call(self.kernel, self.owner, unknown))
        self.assertEqual(self.check(context)['applicability']['state'], 'NEEDS_INPUT')

    def test_owned_revision_checks_are_not_relabelled_as_mathematical_failure(self):
        problem = problem_call(self.kernel, self.owner); context = resource_context(problem)
        other = self.kernel.dispatch('algo.find_applicable', {'context': context}, operator('other'))
        self.assertFalse(other['ok'])
        changed = self.call('problems.revise', {**context['problem'], 'title': 'Changed revision'})
        self.assertFalse(self.kernel.dispatch('algo.find_applicable', {'context': context}, self.owner)['ok'])
        context['problem'].update(expected_revision=changed['revision'], expected_context_digest=changed['context_digest'])
        self.assertEqual(self.check(context)['applicability']['state'], 'MATCH_WITH_OBLIGATIONS')

    def test_cancellation_domain_guard_is_retained(self):
        entry = self.call('algo.get', {'id': 'rational_normalization'})['entry']
        symbolic = self.check(entry['examples'][0]['context'])['applicability']
        self.assertTrue(any('denominator' in text for text in symbolic['obligations']))
        zero = self.check(entry['examples'][1]['context'])['applicability']
        self.assertEqual(zero['state'], 'REJECTED_INPUT'); self.assertIn('denominator', zero['reasons'][0].lower())

    def test_matched_equation_can_still_lack_its_runtime_dependency(self):
        entry = self.call('algo.get', {'id': 'linear_equalities'})['entry']
        absent = {k: {'installed': None, 'required': pin, 'state': 'MISSING'} for k, pin in atlas.math_backend.PINS.items()}
        with patch.object(atlas.math_backend, 'status', return_value=absent):
            candidate = self.check(entry['examples'][0]['context'])
        self.assertEqual(candidate['applicability']['state'], 'MATCH_WITH_OBLIGATIONS')
        self.assertEqual(candidate['implementation']['state'], 'DEPENDENCY_UNAVAILABLE')
        self.assertFalse(candidate['runtime_authorization'])

    def test_catalog_change_refuses_an_old_selection_digest(self):
        digest = self.call('algo.lookup')['catalog_digest']; original = capability_catalog.source
        def changed(root, name):
            value = original(root, name)
            return {**value, 'sha256': '0'*64} if name == 'workbench/math_model.py' else value
        with patch.object(capability_catalog, 'source', side_effect=changed):
            result = self.kernel.dispatch('algo.get', {'id': 'linear_equalities', 'expected_catalog_digest': digest}, self.owner)
        self.assertFalse(result['ok']); self.assertIn('CATALOG_CHANGED', result['error']['message'])

    def test_read_admission_cannot_write_method_results_or_issue_permission(self):
        problem = problem_call(self.kernel, self.owner); context = resource_context(problem)
        with self.kernel.db() as db: before = db.execute('SELECT count(*) FROM desk_records').fetchone()[0]
        candidate = self.check(context, principal=Principal('owner'))
        self.assertTrue(all(not op['scope_eligible'] for op in candidate['implementation']['operations'] if op['scope'] != 'read'))
        with self.kernel.db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM desk_records').fetchone()[0], before)
            self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)
        self.assertFalse(self.kernel.dispatch('math.schedule', {**context['problem'], 'capacity': 'cap', 'allocations': context['allocations']}, Principal('owner'))['ok'])

    def test_context_fields_and_task_signatures_are_not_guessed(self):
        entry = self.call('algo.get', {'id': 'dimensional_arithmetic'})['entry']
        context = copy.deepcopy(entry['examples'][0]['context']); context['graph'] = {}
        self.assertEqual(self.check(context)['applicability']['state'], 'REJECTED_INPUT')
        context['unregistered_field'] = True
        self.assertFalse(self.kernel.dispatch('algo.find_applicable', {'context': context}, self.owner)['ok'])
        self.assertEqual(self.check({'task': 'EVALUATE'}, 'linear_equalities')['applicability']['state'], 'TASK_MISMATCH')

    def test_stac_read_routes_are_finite_and_forward_the_principal(self):
        program = 'algorithms | method interval_capacity'
        self.assertEqual(stac_bridge.compile_program(program)['ir']['operation'], 'algo.get')
        value = self.call('stac.run', {'program': program}, Principal('reader'))
        self.assertEqual(value['result']['entry']['id'], 'interval_capacity')
        for program in ('algorithms | method interval_capacity | execute', 'algorithms | shell "anything"'):
            self.assertFalse(self.kernel.dispatch('stac.run', {'program': program}, self.owner)['ok'])


if __name__ == '__main__': unittest.main()
