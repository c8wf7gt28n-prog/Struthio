"""The Project Desk: durable project, assignment and plan records and their authority boundaries."""
import base64
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
from workbench.baseline import environment
from workbench.engineering_kernel import Kernel, Principal, operator
from workbench import project_desk as desk
from workbench.project_desk_checks import fixture, invoke, plan_arguments, REQUEST



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

class ProjectDesk(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ledger-desk-test-'); self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name); self.root = self.base / 'Office'; self.profile = self.base / 'profile'
        env = patch.dict(os.environ, environment(os.environ, self.root, self.profile)); env.start(); self.addCleanup(env.stop)
        self.owner = operator('owner'); self.kernel, self.project, self.assignment = fixture(self.root, self.owner)

    def call(self, op, args): return invoke(self.kernel, op, args, self.owner)

    def test_original_words_revisions_and_typed_plan_survive_reopen(self):
        initial = self.assignment
        changed = self.call('assignments.revise', {'id': initial['id'], 'expected_revision': 1,
            'interpretation': 'Read and compare each count; retain the exact original request.'})
        planned = self.call('assignments.plan', plan_arguments(changed)); plan = planned['plan']
        self.assertEqual(plan['native']['schema'], 'arc.stacy-action-plan/1')
        self.assertEqual(plan['execution'], 'NOT_RUN'); self.assertEqual(plan['authority'], 'PLAN_IS_NOT_PERMISSION')
        reopened = invoke(Kernel(self.root), 'assignments.reopen', {'id': initial['id']}, self.owner)
        self.assertEqual(reopened['assignment']['original_request'], REQUEST)
        self.assertEqual(reopened['interpretation_history'][0]['interpretation'], initial['interpretation'])
        self.assertEqual(reopened['plans'][0], plan); self.assertFalse(reopened['automatic_resume'])
        self.assertIn('PLAN_FROZEN', [event['action'] for event in reopened['journal']])
        self.assertEqual(reopened['freshness']['state'], 'CURRENT')

    def test_content_changes_detected_even_when_size_and_mtime_are_restored(self):
        planned = self.call('assignments.plan', plan_arguments(self.assignment))
        path = self.root / 'Files' / 'stock.csv'; previous = path.stat()
        original = path.read_bytes(); path.write_bytes(original.replace(b'12,5', b'19,5'))
        os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
        sheet = self.call('assignments.reopen', {'id': self.assignment['id']})
        self.assertEqual(sheet['freshness']['state'], 'REVIEW_REQUIRED')
        self.assertIn('INPUTS_CHANGED_OR_UNAVAILABLE', sheet['unresolved'])
        frozen = planned['plan']['inputs'][0]['snapshot']
        self.assertEqual(base64.b64decode(frozen['exact_bytes_base64']), original)
        rejected = self.kernel.dispatch('assignments.plan', plan_arguments(planned['assignment']), self.owner)
        self.assertFalse(rejected['ok']); self.assertIn('INPUTS_CHANGED', rejected['error']['message'])

    def test_scope_owner_and_address_read_cannot_bypass_privacy(self):
        other = operator('other'); read_only = Principal('owner')
        for op, args in [('projects.get', {'id': self.project['id']}),
                         ('assignments.reopen', {'id': self.assignment['id']}),
                         ('ledger.address.read', {'address': 'assignment:' + self.assignment['id']})]:
            self.assertFalse(self.kernel.dispatch(op, args, other)['ok'], op)
        self.assertEqual(self.kernel.dispatch('assignments.list', {}, other)['result']['records'], [])
        for op, args in [('ideas.capture', {'text': 'No write scope'}), ('assignments.plan', plan_arguments(self.assignment))]:
            self.assertFalse(self.kernel.dispatch(op, args, read_only)['ok'])
        self.assertTrue(self.kernel.dispatch('assignments.get', {'id': self.assignment['id']}, read_only)['ok'])

    def test_stale_editor_cannot_overwrite_or_create_an_orphan_plan(self):
        changed = self.call('assignments.revise', {'id': self.assignment['id'], 'expected_revision': 1, 'questions': ['Which date?']})
        self.assertFalse(self.kernel.dispatch('assignments.plan', plan_arguments(self.assignment), self.owner)['ok'])
        self.assertFalse(self.kernel.dispatch('assignments.revise', {'id': self.assignment['id'], 'expected_revision': 1,
            'interpretation': 'A stale editor'}, self.owner)['ok'])
        sheet = self.call('assignments.reopen', {'id': self.assignment['id']})
        self.assertEqual(sheet['plans'], []); self.assertEqual(sheet['assignment'], changed)

    def test_a_plan_refuses_while_the_program_seed_is_not_current(self):
        # The module hold reads an edited-but-unpackaged seed as bound; the plan gate itself still refuses one that is not.
        stale = {'state': 'STALE', 'seed_id': 'a' * 64, 'changed_sources': ['workbench/project_desk.py'], 'missing_sources': []}
        with patch('workbench.stacy_foundation.seed_status', return_value=stale):
            refused = self.kernel.dispatch('assignments.plan', plan_arguments(self.assignment), self.owner)
        self.assertFalse(refused['ok']); self.assertIn('not current', refused['error']['message'])
        self.assertEqual(self.call('assignments.reopen', {'id': self.assignment['id']})['plans'], [])

    def test_saving_and_reviewing_never_run_a_program_or_create_a_grant(self):
        operations = []; original = self.kernel.dispatch
        def watched(op, args=None, principal=None):
            operations.append(op); return original(op, args, principal)
        with patch.object(self.kernel, 'dispatch', side_effect=watched):
            planned = self.call('assignments.plan', plan_arguments(self.assignment))
            (self.root / 'Files' / 'answer.txt').write_text('R1: 7\n')
            result = self.call('assignments.review', {'id': self.assignment['id'], 'expected_revision': planned['assignment']['revision'],
                'plan': planned['plan']['id'], 'decision': 'ACCEPT', 'note': 'Owner inspected the table and output.',
                'outputs': ['files:answer.txt'], 'unresolved': []})
        self.assertFalse(set(operations) & {'stac.run', 'language.run', 'jobs.submit', 'candidates.accept'})
        self.assertEqual(result['review']['judgment'], 'OWNER_REVIEW_NOT_EXECUTION_OR_PROOF')
        self.assertEqual(result['review']['plan_digest'], planned['plan']['content_digest'])
        self.assertEqual(self.kernel.listing('jobs'), [])
        (self.root / 'Files' / 'answer.txt').write_text('Later overwrite\n')
        saved = self.call('reviews.get', {'id': result['review']['id']})
        self.assertEqual(base64.b64decode(saved['outputs'][0]['snapshot']['exact_bytes_base64']), b'R1: 7\n')
        reopened = self.call('assignments.reopen', {'id': self.assignment['id']})
        self.assertIn('OUTPUTS_CHANGED_OR_UNAVAILABLE', reopened['unresolved'])

    def test_review_requires_owner_scope_current_plan_and_resolved_gaps(self):
        changed = self.call('assignments.revise', {'id': self.assignment['id'], 'expected_revision': 1, 'questions': ['Which date?']})
        planned = self.call('assignments.plan', plan_arguments(changed)); (self.root / 'Files' / 'answer.txt').write_text('An answer')
        args = {'id': changed['id'], 'expected_revision': planned['assignment']['revision'], 'plan': planned['plan']['id'],
                'decision': 'ACCEPT', 'note': 'Review', 'outputs': ['files:answer.txt'], 'unresolved': []}
        self.assertFalse(self.kernel.dispatch('assignments.review', args, self.owner)['ok'])
        args['decision'] = 'DEFER'; args['unresolved'] = ['Which date?']
        worker = Principal('owner', frozenset({'read', 'execute'}))
        self.assertFalse(self.kernel.dispatch('assignments.review', args, worker)['ok'])
        review = self.call('assignments.review', args)
        self.assertEqual(review['review']['unresolved'], ['Which date?'])

    def test_invalid_scope_schema_network_and_expired_plans_are_refused(self):
        cases = []
        for key, value in [('network', True), ('operations', ['jobs.submit']), ('expires', time.time() - 1),
                           ('working_roots', ['Files/../escape'])]:
            args = plan_arguments(self.assignment); args['permissions'][key] = value; cases.append(args)
        args = plan_arguments(self.assignment); args.update(language='CALL', operation='projects.create', arguments={'title': 'Missing intent'})
        args.pop('program'); cases.append(args)
        for args in cases: self.assertFalse(self.kernel.dispatch('assignments.plan', args, self.owner)['ok'])
        planned = self.call('assignments.plan', plan_arguments(self.assignment))
        with patch('workbench.project_desk.time.time', return_value=time.time() + 7200):
            self.assertIn('PLAN_EXPIRED', self.call('assignments.reopen', {'id': self.assignment['id']})['unresolved'])

    def test_native_engineering_ir_stays_distinct_and_reports_unbound_context(self):
        args = plan_arguments(self.assignment); args.update(language='STAC', program='use ARC1@R10 | part U45')
        args['permissions']['operations'] = ['links.inspect']
        planned = self.call('assignments.plan', args)
        self.assertEqual(planned['plan']['native']['kind'], 'ENGINEERING')
        self.assertEqual(planned['plan']['result_type'], 'PartInspection')
        self.assertEqual(planned['plan']['native']['ir']['binding']['state'], 'SYMBOLIC_UNPINNED')
        self.assertTrue(planned['plan']['source_gaps'])

    def test_migration_is_repeatable_preserves_legacy_and_rejects_future_versions(self):
        legacy_root = self.base / 'Legacy'
        legacy_root.mkdir()
        with patch.object(desk, 'ensure', return_value=None): legacy = Kernel(legacy_root)
        with legacy.db() as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='desk_records'").fetchone())
            db.execute('INSERT INTO settings VALUES(?,?)', ('stage-two-sentinel', 'legacy stays'))
        Kernel(legacy_root)
        with legacy.db() as db:
            before = list(db.execute('SELECT version,digest,applied FROM desk_migrations'))
        Kernel(legacy_root); Kernel(legacy_root)
        with legacy.db() as db:
            self.assertEqual(before, list(db.execute('SELECT version,digest,applied FROM desk_migrations')))
            self.assertEqual(db.execute('SELECT value FROM settings WHERE key=?', ('stage-two-sentinel',)).fetchone()[0], 'legacy stays')
            db.execute('INSERT INTO desk_migrations VALUES(?,?,?)', (99, 'unsupported', 0))
        with self.assertRaisesRegex(ValueError, 'MIGRATION_UNSUPPORTED'): Kernel(legacy_root)
        with sqlite3.connect(legacy.dbpath) as db:
            self.assertEqual(db.execute('SELECT value FROM settings WHERE key=?', ('stage-two-sentinel',)).fetchone()[0], 'legacy stays')

    def test_registered_write_is_a_plan_only_and_exact_schema_is_required(self):
        args = plan_arguments(self.assignment); args.pop('program')
        args.update(language='CALL', operation='ideas.capture', arguments={'text': 'A future idea'})
        args['permissions'].update(operations=['ideas.capture'], effects=['execute'])
        before = self.call('ideas.list', {})['records']
        planned = self.call('assignments.plan', args)
        self.assertEqual(self.call('ideas.list', {})['records'], before)
        self.assertEqual(planned['plan']['native']['schema'], 'arc.registered-call/1')
        self.assertEqual(planned['plan']['permissions']['authority'], 'REQUEST_ONLY_NO_GRANT')


if __name__ == '__main__': unittest.main()
