"""Assistant reasoning (slate.context, slate.ask, the stream): ranked context and its invalidation, streaming that publishes
only validated text, citations and proposals that create no evidence, exact edit drafts, replay and scope limits, separate
qualification receipts and additive record migration. The model is the protocol double in protocol_fixture.py, not inference."""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from workbench.baseline import environment
from workbench.engineering_kernel import Kernel, Principal, operator
from workbench import local_brain as brain, project_desk as desk, slate_context, slate_reasoning as slate, slate_stream
from workbench.project_desk_checks import invoke
from workbench.slate_checks import fixture
from tests_integrated.protocol_fixture import ProtocolWorker



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

class Reasoning(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ledger-reasoning-test-'); self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name); self.root = self.base / 'Office'; self.profile = self.base / 'profile'
        env = patch.dict(os.environ, environment(os.environ, self.root, self.profile)); env.start(); self.addCleanup(env.stop)
        self.owner = operator('owner'); self.kernel, self.project, self.assignment, self.context = fixture(self.root, self.owner)

    def call(self, op, args, principal=None): return invoke(self.kernel, op, args, principal or self.owner)

    def ask(self, task='ANSWER', **args): return self.call('slate.ask', {'context': self.context['id'], 'task': task, **args})

    def test_ranked_context_records_exclusions_locations_and_rebuilds_privately(self):
        (self.root / 'Files' / 'noisy.txt').write_text('Clock ' + 'unrelated material ' * 100)
        value = self.call('slate.context.create', {'question': 'Clock resistor 330', 'addresses': ['files:clock.txt', 'files:noisy.txt'],
            'char_budget': 512, 'include_seed': False, 'include_procedures': False})
        self.assertIn('330', value['selection']['selected'][0]['text'])
        self.assertTrue(any(p['reason'] == 'CHARACTER_BUDGET' for p in value['selection']['excluded']))
        selected = value['selection']['selected'][0]
        self.assertEqual(selected['source_sha256'], hashlib.sha256((self.root / 'Files' / 'clock.txt').read_bytes()).hexdigest())
        self.assertEqual(selected['locator']['first_line'], 1)
        self.assertTrue(self.call('slate.context.rebuild', {'id': value['id']})['matches_frozen_selection'])
        self.assertFalse(self.kernel.dispatch('slate.context.get', {'id': value['id']}, operator('other'))['ok'])
        self.assertFalse(self.kernel.dispatch('slate.context.create', {'question': 'Clock'}, Principal('owner'))['ok'])
        table = self.call('slate.context.create', {'question': 'Which components are short?', 'addresses': ['files:stock.csv'],
            'include_seed': False, 'include_procedures': False})
        self.assertTrue(any('Need,Have' in p['text'] and p['bm25'] is None for p in table['selection']['selected']))

    def test_equal_size_source_changes_and_assignment_revisions_invalidate_context(self):
        path = self.root / 'Files' / 'clock.txt'; original = path.stat(); path.write_text(path.read_text().replace('330', '470'))
        os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
        self.assertFalse(self.call('slate.context.check', {'id': self.context['id']})['usable'])
        changed = self.call('slate.context.create', {'assignment': self.assignment['id'], 'question': 'Clock resistor', 'include_seed': False})
        self.assertTrue(changed['unavailable']); self.assertFalse(any(p['kind'] == 'SOURCE' for p in changed['selection']['selected']))
        self.call('assignments.revise', {'id': self.assignment['id'], 'expected_revision': self.assignment['revision'], 'questions': ['Which clock?']})
        state = self.call('slate.context.check', {'id': self.context['id']})
        self.assertIn('ASSIGNMENT_CHANGED', state['reasons'])

    def test_context_refuses_and_goes_stale_while_the_program_seed_is_not_current(self):
        # The module hold reads an edited-but-unpackaged seed as bound; both context gates still refuse one that is not.
        stale = {'state': 'STALE', 'seed_id': self.context['seed_id'], 'changed_sources': ['workbench/slate_context.py'], 'missing_sources': []}
        with patch('workbench.stacy_foundation.seed_status', return_value=stale):
            refused = self.kernel.dispatch('slate.context.create', {'question': 'Clock resistor', 'addresses': ['files:clock.txt'],
                'include_seed': False}, self.owner)
            state = self.call('slate.context.check', {'id': self.context['id']})
        self.assertFalse(refused['ok']); self.assertIn('not current', refused['error']['message'])
        self.assertFalse(state['usable']); self.assertIn('PROGRAM_SOURCE_CHANGED', state['reasons'])
        self.assertTrue(self.call('slate.context.check', {'id': self.context['id']})['usable'])

    def test_authenticated_stream_retains_only_provisional_prose_until_validated(self):
        with ProtocolWorker(self.kernel, self.base) as worker:
            job = self.ask(); result = slate.run_job(self.kernel, job)
            self.assertEqual(result['status'], 'DRAFT_VALIDATED'); self.assertEqual(result['candidate']['state'], 'ANSWER')
            self.assertEqual(result['validation']['citations'][0]['source_sha256'], hashlib.sha256((self.root / 'Files' / 'clock.txt').read_bytes()).hexdigest())
            self.assertEqual(self.call('slate.progress', {'job': job['id']})['state'], 'VALIDATED')
            self.assertTrue(result['metrics']['stream_complete']); self.assertGreaterEqual(result['metrics']['first_token_seconds'], 0)
            self.assertTrue(any(path == '/v1/chat/completions' and body['stream'] for path, body in worker.requests))
            self.assertFalse(self.kernel.dispatch('slate.progress', {'job': job['id']}, operator('other'))['ok'])
            self.assertFalse(self.kernel.dispatch('brain.result', {'id': job['id']}, operator('other'))['ok'])
        self.assertEqual(slate_stream.preview('{"actions":[{"arguments":{"text":"hidden"}}]'), '')
        self.assertEqual(slate_stream.preview('{"text":"Hi\\nthere'), 'Hi\nthere')

    def test_action_attempt_invalidates_the_prepared_source_slot(self):
        from workbench import slate_action

        with ProtocolWorker(self.kernel, self.base) as worker:
            model = brain.model(self.kernel, worker.worker['model_id'])
            worker.worker.update(context_reuse='PINNED_SINGLE_SLOT', verified_files=brain.file_stamps(model))
            brain.put(self.kernel, 'worker', worker.worker)

            def answer():
                return slate.run_job(self.kernel, self.ask())['metrics']['prefix_reuse_requested']

            self.assertFalse(answer())
            self.assertTrue(answer())

            # A stream that started and failed may already have occupied the slot.
            # Use an incomplete ACTION selection so no proposal or tool can run.
            request = {'frame': {'active_frontier': ['clock'], 'problem': {'variables': []}, 'catalogue': [],
                'finish_observations': [], 'finish_policy': 'Direct response permitted'},
                'messages': [], 'max_tokens': 192, 'seconds': 5}
            job = self.ask()
            worker.override = '{}'
            worker.finish = 'length'
            with patch.object(slate_action.contexts, 'load', return_value=request), patch.object(slate_action, 'live_request'):
                with self.assertRaisesRegex(ValueError, 'LOCAL_RESPONSE_INCOMPLETE'):
                    slate_action.run_job(self.kernel, job)
            self.assertEqual(brain.get(self.kernel, 'prepared_context', {}), {})

            worker.override = None
            worker.finish = 'stop'
            self.assertFalse(answer())
            worker.worker['start'] = 'replacement-fixture'
            brain.put(self.kernel, 'worker', worker.worker)
            self.assertFalse(answer())

    def test_truncation_missing_terminator_and_cancellation_never_publish_results(self):
        with ProtocolWorker(self.kernel, self.base) as worker:
            worker.finish = 'length'; job = self.ask()
            with self.assertRaisesRegex(ValueError, 'INCOMPLETE'): slate.run_job(self.kernel, job)
            self.assertEqual(self.call('slate.progress', {'job': job['id']})['state'], 'REJECTED')
            worker.finish = 'stop'; worker.done = False; job = self.ask()
            with self.assertRaisesRegex(ValueError, 'INCOMPLETE'): slate.run_job(self.kernel, job)
            worker.done = True; job = self.ask()
            with self.kernel.db() as db:
                record = self.kernel.record('jobs', job['id']); record['cancel'] = True; self.kernel.save('jobs', record, db)
            with self.assertRaisesRegex(ValueError, 'CANCELLED'): slate.run_job(self.kernel, record)
            self.assertFalse((self.root / 'build' / 'brain' / 'runs' / job['id'] / 'result.json').exists())
        with self.assertRaisesRegex(ValueError, 'INVALID_FRAME'):
            list(slate_stream.events(io.BytesIO(b'garbage\n'), lambda: False, time.monotonic() + 5))

    def test_sources_changed_during_inference_are_rejected_after_stream(self):
        with ProtocolWorker(self.kernel, self.base) as worker:
            job = self.ask(); path = self.root / 'Files' / 'clock.txt'; before = path.stat()
            def alter():
                path.write_text(path.read_text().replace('330', '470')); os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
            worker.after_delta = alter
            with self.assertRaisesRegex(ValueError, 'CONTEXT_CHANGED_DURING_INFERENCE'): slate.run_job(self.kernel, job)
            self.assertEqual(self.call('slate.progress', {'job': job['id']})['state'], 'REJECTED')

    def test_citations_procedures_and_write_proposals_do_not_create_evidence_or_actions(self):
        source = self.context['selection']['selected'][0]
        candidate = {'state': 'ANSWER', 'text': 'A claim', 'citations': ['S9']}
        with self.assertRaises(ValueError): slate.validate_result('ANSWER', candidate, {'S1': source})
        procedure = {**source, 'kind': 'PROCEDURE_SUCCESS'}
        with self.assertRaises(ValueError): slate.validate_result('ANSWER', {**candidate, 'citations': ['S1']}, {'S1': procedure})
        write = {'text': 'Write', 'interpretation': 'Change a file', 'questions': [], 'actions': [{'operation': 'files.write', 'arguments': {'path': 'clock.txt', 'text': 'changed'}}]}
        with self.assertRaisesRegex(ValueError, 'READ_PROPOSAL'): slate.validate_result('PLAN', write, {})
        with ProtocolWorker(self.kernel, self.base) as worker:
            before = (self.root / 'Files' / 'clock.txt').read_bytes(); job = self.ask(task='PLAN'); result = slate.run_job(self.kernel, job)
            self.assertEqual(result['validation']['execution'], 'NOT_RUN')
            self.assertEqual((self.root / 'Files' / 'clock.txt').read_bytes(), before)
            self.assertEqual(len(self.kernel.listing('jobs')), 1)
        lesson = self.call('memory.lesson.propose', {'title': 'Clock resistor procedure', 'body': 'Read the clock resistor source first.', 'references': []})
        self.assertFalse(any(p['kind'] == 'OWNER_PROCEDURE' for p in self.call('slate.memory.search', {'question': 'clock resistor'})['records']))
        self.call('memory.lesson.review', {'id': lesson['id'], 'approved': True, 'reason': 'Useful procedure, not technical proof.'})
        self.assertTrue(any(p['kind'] == 'OWNER_PROCEDURE' for p in self.call('slate.memory.search', {'question': 'clock resistor'})['records']))
        context = self.call('slate.context.create', {'question': 'Clock resistor', 'addresses': ['files:clock.txt'], 'include_seed': False})
        self.call('memory.lesson.review', {'id': lesson['id'], 'approved': False, 'reason': 'Retired by the owner.'})
        self.assertIn('PROCEDURE_MEMORY_CHANGED', self.call('slate.context.check', {'id': context['id']})['reasons'])

    def test_exact_edit_is_a_draft_and_rejects_stale_or_ambiguous_ranges(self):
        path = self.root / 'Files' / 'hands.txt'; base = 'Clock needs blue hands.\n'; path.write_text(base)
        self.context = self.call('slate.context.create', {'question': 'Replace blue with black.', 'addresses': ['files:hands.txt'], 'include_seed': False})
        with ProtocolWorker(self.kernel, self.base):
            job = self.ask(task='EDIT', target_address='files:hands.txt'); result = slate.run_job(self.kernel, job)
            self.assertEqual(result['validation']['proposed_text'], 'Clock needs black hands.\n')
            self.assertFalse(result['validation']['applied']); self.assertEqual(path.read_text(), base)
            wrong = {**result['candidate'], 'base_sha256': '0' * 64}
            with self.assertRaisesRegex(ValueError, 'BASE_MISMATCH'): slate.validate_result('EDIT', wrong, {}, base=base)
            wrong = {**result['candidate'], 'edits': result['candidate']['edits'] * 2}
            with self.assertRaisesRegex(ValueError, 'AMBIGUOUS'): slate.validate_result('EDIT', wrong, {}, base=base)

    def test_request_replay_scope_ceiling_and_persistent_work_hold(self):
        from workbench import work_trail
        with ProtocolWorker(self.kernel, self.base):
            first = self.ask(request_key='one'); again = self.ask(request_key='one'); self.assertEqual(first['id'], again['id'])
            self.assertFalse(self.kernel.dispatch('slate.ask', {'context': self.context['id'], 'task': 'PLAN', 'request_key': 'one'}, self.owner)['ok'])
            limited = Principal('owner', frozenset({'read', 'execute'}), tools=('brain.respond',))
            self.assertFalse(self.kernel.dispatch('slate.ask', {'context': self.context['id'], 'task': 'ANSWER'}, limited)['ok'])
            self.assertFalse(self.kernel.dispatch('slate.qualify', {'model_id': 'a' * 64}, limited)['ok'])
            self.assertFalse(self.kernel.dispatch('jobs.submit', {'tool': 'brain.reason', 'brain': {'conversation': 'f' * 32}}, self.owner)['ok'])
            work_trail.hold(self.kernel, self.owner)
            self.assertFalse(self.kernel.dispatch('slate.ask', {'context': self.context['id'], 'task': 'ANSWER'}, self.owner)['ok'])

    def test_task_trials_are_separate_receipts_and_cannot_claim_real_model_quality(self):
        with ProtocolWorker(self.kernel, self.base):
            job = self.call('slate.qualify', {'model_id': 'a' * 64}); result = slate.run_job(self.kernel, job)
            receipt = result['qualification']; self.assertEqual(receipt['state'], 'PASSED')
            self.assertEqual([r['task'] for r in receipt['tasks']], list(slate.TASKS))
            self.assertEqual(receipt['runtime']['build'], 'PROTOCOL_TEST_DOUBLE_NOT_GGUF_INFERENCE')
            self.assertEqual(self.call('slate.qualification.get', {'id': receipt['id']}), receipt)
            self.assertFalse(self.kernel.dispatch('slate.qualification.get', {'id': receipt['id']}, operator('other'))['ok'])
            self.assertEqual(self.call('slate.qualifications', {})['records'][0]['id'], receipt['id'])
            self.assertEqual(brain.get(self.kernel, 'model.' + 'a' * 64).get('qualification'), None)

    def test_existing_records_survive_additive_migration_and_unknown_versions_are_refused(self):
        from workbench.project_desk_checks import fixture as previous_fixture
        legacy_root = self.base / 'Legacy'
        with patch.object(slate_context, 'ensure', return_value=None): legacy, _, assignment = previous_fixture(legacy_root, self.owner)
        with legacy.db() as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='slate_records'").fetchone())
        Kernel(legacy_root); Kernel(legacy_root)
        saved = invoke(Kernel(legacy_root), 'assignments.get', {'id': assignment['id']}, self.owner)
        self.assertEqual(saved, assignment)
        with legacy.db() as db: db.execute('INSERT INTO slate_migrations VALUES(?,?,?)', (99, 'unsupported', 0))
        with self.assertRaisesRegex(ValueError, 'SLATE_MIGRATION_UNSUPPORTED'): Kernel(legacy_root)


if __name__ == '__main__': unittest.main()
