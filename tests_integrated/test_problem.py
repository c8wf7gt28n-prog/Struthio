"""Risk-focused I01 checks. No model, native app or host qualification claims."""
import csv
from decimal import Decimal
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from workbench.engineering_kernel import Kernel, operator
from workbench import clock_lab, locations, problem_service
from workbench.baseline import environment
from workbench.problem_checks import bound, invoke


class ProblemBindings(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ledger-i01-test-'); self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name); self.home = base / 'Home'; self.home.mkdir(); self.root = base / 'Office'
        self.env = patch.dict(os.environ, {**environment(os.environ, self.root, base / 'profile'), 'HOME': str(self.home)})
        self.env.start(); self.addCleanup(self.env.stop)
        self.home_patch = patch.object(Path, 'home', return_value=self.home); self.home_patch.start(); self.addCleanup(self.home_patch.stop)
        locations.office(self.root); self.kernel = Kernel(self.root); self.p = operator()
        self.started = clock_lab.start(self.kernel, clock_lab.copy_inputs(self.home / 'Clock_Lab_I01'), self.p)
        self.problem = self.started['problem']; self.copy = self.started['copy']

    def call(self, op, args): return invoke(self.kernel, op, args, self.p)

    def test_unknown_cannot_acquire_a_value_implicitly_or_zero(self):
        variables = json.loads(json.dumps(self.problem['variables'])); variables[4]['value'] = '0'
        response = self.kernel.dispatch('problems.revise', {**bound(self.problem), 'variables': variables}, self.p)
        self.assertFalse(response['ok']); self.assertIn('unknown variable', response['error']['message'])
        self.assertEqual(self.call('problems.get', {'id': self.problem['id']})['problem'], self.problem)

    def test_context_and_operation_contract_changes_stop_before_read(self):
        wrong = {**bound(self.problem), 'expected_context_digest': '0' * 64, 'source': 0}
        self.assertFalse(self.kernel.dispatch('problems.prepare', wrong, self.p)['ok'])
        action = self.call('problems.prepare', {**bound(self.problem), 'source': 0})
        binding = problem_service.operation_binding(); binding['handler_sha256'] = 'f' * 64
        original = self.kernel.dispatch; seen = []
        def watched(op, args=None, p=None): seen.append(op); return original(op, args, p)
        with patch.object(problem_service, 'operation_binding', return_value=binding), patch.object(self.kernel, 'dispatch', side_effect=watched):
            response = self.kernel.dispatch('problems.run', {'action': action['id']}, self.p)
        self.assertFalse(response['ok']); self.assertIn('ACTION_CONTRACT_CHANGED', response['error']['message'])
        self.assertNotIn('work.read', seen)

    def test_explicit_rebinding_retains_old_evidence_and_history(self):
        action = self.call('problems.prepare', {**bound(self.problem), 'source': 0})
        old = self.call('problems.run', {'action': action['id']})['receipt']
        work = self.root / 'Files' / self.copy['work'] / 'requirements.md'
        work.write_text(work.read_text().replace('16 MiB', '18 MiB'))
        sources = [{k: s[k] for k in ('copy', 'path', 'label')} for s in self.problem['sources']]
        updated = self.call('problems.revise', {**bound(self.problem), 'sources': sources})
        self.assertNotEqual(updated['context_digest'], self.problem['context_digest'])
        self.assertNotEqual(updated['sources'][0]['sha256'], self.problem['sources'][0]['sha256'])
        sheet = self.call('problems.get', {'id': self.problem['id']})
        self.assertEqual(sheet['receipts'], [old]); self.assertEqual(sheet['freshness']['state'], 'CURRENT')
        self.assertEqual(old['problem_revision'], 1)
        self.assertEqual(len(self.call('problems.history', {'id': self.problem['id']})['records']), 2)

    def test_delegation_is_rechecked_and_paths_cannot_escape(self):
        action = self.call('problems.prepare', {**bound(self.problem), 'source': 0})
        with self.kernel.db() as db: db.execute('UPDATE copies SET for_slate=0 WHERE id=?', (self.copy['id'],))
        self.assertFalse(self.kernel.dispatch('problems.run', {'action': action['id']}, self.p)['ok'])
        with self.kernel.db() as db: db.execute('UPDATE copies SET for_slate=1 WHERE id=?', (self.copy['id'],))
        for path in ('../requirements.md', '/etc/passwd', 'a/../../requirements.md'):
            response = self.kernel.dispatch('problems.revise', {**bound(self.problem), 'sources': [
                {'copy': self.copy['id'], 'path': path, 'label': 'Invalid'}]}, self.p)
            self.assertFalse(response['ok'], path)

    def test_retained_receipt_survives_missing_source(self):
        action = self.call('problems.prepare', {**bound(self.problem), 'source': 0})
        saved = self.call('problems.run', {'action': action['id']})['receipt']
        (self.root / 'Files' / self.copy['work'] / 'requirements.md').unlink()
        sheet = self.call('problems.get', {'id': self.problem['id']})
        self.assertEqual(sheet['freshness']['state'], 'REVIEW_REQUIRED'); self.assertEqual(sheet['receipts'], [saved])
        self.assertEqual(sheet['freshness']['sources'][0]['state'], 'UNAVAILABLE')

    def test_read_wrapper_cannot_accept_arbitrary_commands_or_effects(self):
        for extra in ({'operation': 'jobs.submit'}, {'effects': ['execute']}, {'arguments': {'command': 'sh'}}):
            response = self.kernel.dispatch('problems.prepare', {**bound(self.problem), 'source': 0, **extra}, self.p)
            self.assertFalse(response['ok'])
        response = self.kernel.dispatch('problems.revise', {**bound(self.problem), 'request': 'Replace original words'}, self.p)
        self.assertFalse(response['ok'])


class FixtureOracle(unittest.TestCase):
    def test_independent_integer_and_decimal_oracles_match_frozen_inputs(self):
        # Only evaluator tests load this file. It is outside model-visible inputs.
        oracle = json.loads((Path(__file__).parent / 'clock_lab_oracle.json').read_text())
        with (clock_lab.FIXTURE / 'memory.csv').open() as stream: memory = list(csv.DictReader(stream))
        sizes = [int(r['Size']) * 2**20 for r in memory[:3]]
        self.assertEqual(sum(sizes), oracle['simultaneous_bytes'])
        self.assertEqual(16 * 2**20, oracle['limit_bytes'])
        self.assertTrue(all(r['Lifetime_state'] == 'UNKNOWN' and not r['Start'] and not r['End'] for r in memory[:3]))
        # A separately specified half-open lifetime variant, not the initial task.
        events = [(0, sizes[0]), (10, -sizes[0]), (0, sizes[1]), (10, -sizes[1]), (10, sizes[2]), (20, -sizes[2])]
        by_time = {}
        for t, delta in events: by_time[t] = by_time.get(t, 0) + delta
        live = 0; peak = 0
        for t in sorted(by_time): live += by_time[t]; peak = max(peak, live)
        self.assertEqual(peak, oracle['explicit_nonoverlap_peak_bytes'])
        with (clock_lab.FIXTURE / 'power.csv').open() as stream: currents = [Decimal(r['Typical_current']) for r in csv.DictReader(stream)]
        typical = sum(currents) / Decimal(1000)
        self.assertEqual(str(Decimal(5) * typical), oracle['assumed_typical_watts'])
        self.assertEqual(str(Decimal(5) * Decimal('0.300')), oracle['declared_limit_watts'])
        manifest = json.loads((clock_lab.FIXTURE.parent / 'INPUTS.json').read_text())
        self.assertNotIn('clock_lab_oracle.json', manifest['files'])


if __name__ == '__main__': unittest.main()
