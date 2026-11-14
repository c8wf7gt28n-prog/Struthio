"""The model memory rules, fixed in 0.8.1, each against Graphite's own code with simulated readings.

Auto's cap, one rule for admission and launch, the reserve on an unknown machine and the deadline for a lost reading,
Ready meaning a valid reply, a work hold that holds, one memory reading for admission and the worker guard, the memory
stop staying visible, and the simulated offload mark. The readings come from the campaign's simulation seams
(tools/campaign_lib/sim.py); the decisions are Graphite's. Run alone:

  python -B -m unittest -v tests_integrated.test_resource_rules
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.campaign_lib import fixture, gguf_fixture, sim
from workbench import brain_runtime, brain_worker, local_brain, resource_control, work_trail

GiB, MiB = sim.GiB, sim.MiB
OFFLOAD_41 = 'load_tensors: offloaded 41/41 layers to GPU\n'
MEMORY_LOG = 'GRAPHITE_HOST_MEMORY_LIMIT: resident budget or shared-host headroom exhausted\n'


class Workspace(unittest.TestCase):
    """A fresh Office workspace with the owner's model stand-in registered, under simulated hardware."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='graphite-resource-rules-')
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        env = patch.dict(os.environ, {'ARC1_WORKBENCH_CONFIG_HOME': str(self.base / 'profile'),
                                      'ARC_LEDGER_CONCERN': str(self.base / 'Concern')})
        env.start()
        self.addCleanup(env.stop)
        self.kernel, self.owner = fixture.base_workspace(self.base)
        self.host = sim.FakeHost(60)
        self.bench = sim.Bench(host=self.host)
        self.bench.__enter__()
        self.addCleanup(self.bench.__exit__, None, None, None)
        with self.kernel.db() as db:
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', ('ledger.brain.context', json.dumps(4096)))
        self.model = self.register('valid.gguf')

    def register(self, name):
        path = self.base / 'models' / name
        path.parent.mkdir(exist_ok=True)
        gguf_fixture.build(path, 'valid')
        return local_brain.model(self.kernel, local_brain.add(self.kernel, {'path': str(path)}, self.owner)['id'])

    def use(self, model, key, options=None):
        args = {'id': model['id'], 'request_key': key, **({'options': options} if options else {})}
        return self.kernel.dispatch('brain.model.use', args, self.owner)

    def claim(self, ident, sleeps=3):
        clock = self.bench.clock
        clock.max_sleeps = clock.sleeps + sleeps
        try:
            got = resource_control.claim(self.kernel, ident)
        except sim.StopWaiting:
            got = None
        finally:
            clock.max_sleeps = None
        return got, self.kernel.record('jobs', ident)

    def activate(self, model, key, options=None, workers=()):
        """Submit, claim and run one activation; returns the error text, or None when it activated."""
        self.bench.workers = list(workers)
        r = self.use(model, key, options)
        self.assertTrue(r['ok'], r)
        got, job = self.claim(r['result']['id'])
        self.assertIsNotNone(got, job.get('current_operation'))
        try:
            local_brain.run_model_job(self.kernel, got)
            return None
        except ValueError as exc:
            return str(exc)
        finally:
            job = self.kernel.record('jobs', got['id'])
            job['state'] = 'Completed'
            self.kernel.save('jobs', job)

    def configure(self, options=None):
        return local_brain.configuration(self.model, {'context': 4096, **(options or {})}, self.kernel.root)


class AutoCap(Workspace):
    def test_auto_takes_the_owners_model_from_32157_mib_and_says_its_numbers_below(self):
        self.host.available = 39
        config = self.configure()
        self.assertEqual((config['estimated_peak_bytes'], config['memory_mb']), (27_275_977_692, 26013))
        for available, budget in ((40, 26624), (60, 32768)):       # 65% of available, then the ceiling
            self.host.available = available
            self.assertEqual(self.configure()['memory_mb'], budget)
        self.host.available = 32157 / 1024          # the estimate, the 2,048 MiB reserve and 4,096 MiB headroom
        self.assertEqual(self.configure()['memory_mb'], 26013)
        self.host.available = 32156 / 1024
        with self.assertRaises(ValueError) as refused:
            self.configure()
        self.assertEqual(str(refused.exception),
                         'MODEL_MEMORY_BUDGET_TOO_SMALL: Auto needs 32,157 MiB available for this model at 4,096 tokens '
                         '(its 26,013 MiB estimate, the 2,048 MiB foreground reserve and 4,096 MiB headroom); '
                         '32,156 MiB is available')

    def test_auto_keeps_its_ceiling_and_a_manual_cap_follows_the_admission_rule(self):
        larger = dict(self.model, total_bytes=30 * GiB)
        with self.assertRaisesRegex(ValueError, r'^MODEL_MEMORY_BUDGET_TOO_SMALL: .* above the 32,768 MiB Auto gives '
                                                 r'at most; set a memory cap$'):
            local_brain.configuration(larger, {'context': 4096}, self.kernel.root)
        self.host.available = 30
        self.assertEqual(self.configure({'memory_mb': 26100})['memory_mb'], 26100)    # 28,672 MiB of room
        with self.assertRaisesRegex(ValueError, 'MEMORY_BUDGET_EXCEEDS_AVAILABLE_HOST_RAM: the 28,673 MiB cap and the '
                                                '2,048 MiB foreground reserve need 30,721 MiB; 30,720 MiB is available'):
            self.configure({'memory_mb': 28673})
        with self.assertRaisesRegex(ValueError, "the 16,384 MiB cap is below this model's 26,013 MiB estimate"):
            self.configure({'memory_mb': 16384})


class OneRule(Workspace):
    def test_admission_configuration_and_launch_agree_at_the_boundary(self):
        self.host.available = 40
        r = self.use(self.model, 'use-32g', {'memory_mb': 32768, 'backend': 'CPU'})
        self.assertTrue(r['ok'], r)
        job = r['result']
        reserve = resource_control.reserve_setting(self.kernel)
        for available, fits in ((34 - 1 / 1024, False), (34, True), (34 + 1 / 1024, True)):
            self.host.available = available
            with self.kernel.db() as db:
                admitted = resource_control.decision(self.kernel, job, db, brain_runtime.host())['allowed']
            try:
                local_brain.configuration(self.model, job['brain_launch']['options'], self.kernel.root, 0, reserve)
                configured = True
            except ValueError:
                configured = False
            try:
                resource_control.model_room(self.kernel, {'memory_mb': 32768}, job['id'])
                launches = True
            except ValueError:
                launches = False
            self.assertEqual((admitted, configured, launches), (fits, fits, fits), available)

    def test_a_model_admitted_at_34_gib_is_launched_not_refused(self):
        self.host.available = 40
        r = self.use(self.model, 'use-32g', {'memory_mb': 32768, 'backend': 'CPU'})
        self.host.available = 34
        got, job = self.claim(r['result']['id'])
        self.assertIsNotNone(got, job.get('current_operation'))
        self.bench.workers = [sim.Worker(n_ctx=4096)]
        self.assertEqual(local_brain.run_model_job(self.kernel, got)['status'], 'ACTIVATED')
        self.assertEqual(local_brain.status(self.kernel)['state'], 'READY')


class Margins(Workspace):
    """The verifier's two findings on the first fix: Auto's headroom was kept only at submit, and a handover near the limit
    could stop the old model, find its memory not yet back, and lose it."""

    def test_autos_headroom_stays_with_its_budget_at_admission_and_launch(self):
        self.host.available = 39
        r = self.use(self.model, 'auto-39', {'backend': 'CPU'})
        self.assertTrue(r['ok'], r)
        job = r['result']
        self.assertEqual((job['brain_launch']['options']['memory_mb'], job['brain_launch']['auto_headroom_mb']), (26013, 4096))
        config = {'memory_mb': 26013, 'headroom_mb': 4096}
        for available_mib, fits in ((32156, False), (32157, True)):      # 26,013 + 4,096 headroom + 2,048 reserve
            self.host.available = available_mib / 1024
            with self.kernel.db() as db:
                admitted = resource_control.decision(self.kernel, job, db, brain_runtime.host())['allowed']
            try:
                resource_control.model_room(self.kernel, config, job['id'])
                launches = True
            except ValueError:
                launches = False
            self.assertEqual((admitted, launches), (fits, fits), available_mib)
        self.host.available = 60                                          # the ceiling leaves room above the estimate already
        r = self.use(self.model, 'auto-60', {'backend': 'CPU'})
        self.assertEqual((r['result']['brain_launch']['options']['memory_mb'], r['result']['brain_launch']['auto_headroom_mb']), (32768, 0))

    def test_a_handover_waits_for_the_stopped_models_memory_and_a_cancel_ends_the_wait(self):
        tries = []
        def room(kernel, config, ident):
            tries.append(ident)
            if len(tries) < 3:
                raise ValueError('GRAPHITE_HOST_MEMORY_LIMIT: model launch no longer has admitted shared-memory headroom')
            return {'reserve_bytes': 0}
        with patch.object(resource_control, 'model_room', side_effect=room):
            self.assertEqual(resource_control.await_room(self.kernel, {'memory_mb': 1}, 'j'), {'reserve_bytes': 0})
        self.assertEqual(len(tries), 3)
        def cancelled():
            raise ValueError('MODEL_OPERATION_CANCELLED')
        never = ValueError('GRAPHITE_HOST_MEMORY_LIMIT: model launch no longer has admitted shared-memory headroom')
        with patch.object(resource_control, 'model_room', side_effect=never):
            with self.assertRaisesRegex(ValueError, 'MODEL_OPERATION_CANCELLED'):
                resource_control.await_room(self.kernel, {'memory_mb': 1}, 'j', check=cancelled)
            with self.assertRaisesRegex(ValueError, 'no longer has admitted'):      # bounded: it gives up and says why
                resource_control.await_room(self.kernel, {'memory_mb': 1}, 'j', seconds=1)


class Unmeasured(Workspace):
    def test_unknown_installed_ram_keeps_the_full_reserve(self):
        self.assertEqual(resource_control.reserve_bytes(2048, None), 2048 * MiB)
        self.assertEqual(resource_control.reserve_bytes(2048, 4 * GiB), 1024 * MiB)    # a quarter of a small machine
        self.assertEqual(resource_control.reserve_bytes(2048, 64 * GiB), 2048 * MiB)
        with self.kernel.db() as db:
            self.assertEqual(resource_control.policy(db, {'total_ram_bytes': None})['reserve_bytes'], 2048 * MiB)
        self.host.total, self.host.available = None, 31
        with self.assertRaisesRegex(ValueError, 'the 2,048 MiB foreground reserve'):
            self.configure()

    def test_a_reading_lost_after_submit_fails_after_its_deadline(self):
        r = self.use(self.model, 'measured-at-submit')
        self.host.available = None
        got, job = self.claim(r['result']['id'])
        self.assertEqual((got, job['state'], job['current_operation']), (None, 'Queued', resource_control.UNMEASURED))
        began = self.bench.clock.now
        got, job = self.claim(r['result']['id'], sleeps=200)
        self.assertIsNone(got)
        self.assertEqual(job['state'], 'Failed')
        self.assertTrue(job['error'].startswith('HOST_MEMORY_COULD_NOT_BE_MEASURED: available memory could not be read '
                                                'for 30 s'), job['error'])
        self.assertGreaterEqual(self.bench.clock.now - began, resource_control.UNMEASURED_WAIT_SECONDS)
        self.assertLess(self.bench.clock.now - began, resource_control.UNMEASURED_WAIT_SECONDS + 1)


class Ready(Workspace):
    def test_a_restored_model_with_an_empty_reply_is_not_ready(self):
        previous = self.register('previous.gguf')
        self.assertIsNone(self.activate(previous, 'previous', {'backend': 'CPU'}, [sim.Worker(n_ctx=4096)]))
        error = self.activate(self.model, 'fails', {'backend': 'CPU'},
                              [sim.Worker(exit=1, log='load failed\n'), sim.Worker(n_ctx=4096, reply='')])
        self.assertTrue(error.startswith('MODEL_WORKER_EXITED_DURING_LOAD'), error)
        status = local_brain.status(self.kernel)
        self.assertEqual((status['state'], status['worker']), ('MODEL_STOPPED', None))
        self.assertEqual(self.bench.live_workers(), [])
        # With a reply the same restore is Ready.
        self.assertIsNone(self.activate(previous, 'previous-again', {'backend': 'CPU'}, [sim.Worker(n_ctx=4096)]))
        self.activate(self.model, 'fails-again', {'backend': 'CPU'},
                      [sim.Worker(exit=1, log='load failed\n'), sim.Worker(n_ctx=4096, reply='ready')])
        status = local_brain.status(self.kernel)
        self.assertEqual((status['state'], status['worker']['model_id']), ('READY', previous['id']))

    def test_a_worker_giving_less_context_than_selected_is_refused(self):
        error = self.activate(self.model, 'small', {'backend': 'CPU'}, [sim.Worker(n_ctx=2048)])
        self.assertEqual(error, 'MODEL_CONTEXT_BELOW_SELECTION: the worker gives 2,048 tokens; 4,096 were selected')
        self.assertEqual(local_brain.status(self.kernel)['worker'], None)
        self.assertIsNone(self.activate(self.model, 'full', {'backend': 'CPU'}, [sim.Worker(n_ctx=4096)]))
        worker = local_brain.status(self.kernel)['worker']
        self.assertEqual((worker['context'], worker['context_basis']), (4096, 'WORKER_REPORTED_LIMIT'))


class Hold(Workspace):
    def test_a_hold_keeps_queued_work_waiting_and_it_continues_on_release(self):
        with resource_control.scope('background'):
            r = self.use(self.model, 'held', {'backend': 'CPU'})
        work_trail.hold(self.kernel, self.owner)
        got, job = self.claim(r['result']['id'])
        self.assertIsNone(got)
        self.assertEqual((job['state'], job.get('error'), job['current_operation']), ('Queued', None, resource_control.HELD))
        self.assertEqual(self.bench.popen_argv, [])
        released = work_trail.resume(self.kernel, self.owner)
        self.assertEqual((released['jobs_replayed'], released['jobs_continuing']), (0, 1))
        got, job = self.claim(r['result']['id'])
        self.assertEqual(got['state'], 'Running')
        self.bench.workers = [sim.Worker(n_ctx=4096)]
        self.assertEqual(local_brain.run_model_job(self.kernel, got)['status'], 'ACTIVATED')

    def test_cancel_still_ends_held_work_and_running_work_still_blocks_resume(self):
        r = self.use(self.model, 'held')
        self.kernel.save('jobs', dict(self.kernel.record('jobs', r['result']['id']), id='e' * 32, state='Running'))
        work_trail.hold(self.kernel, self.owner)
        self.assertTrue(self.kernel.dispatch('jobs.cancel', {'id': r['result']['id']}, self.owner)['ok'])
        got, job = self.claim(r['result']['id'])
        self.assertEqual((got, job['state']), (None, 'Cancelled'))
        with self.assertRaisesRegex(ValueError, 'WORK_STILL_ACTIVE_RECONCILE_FIRST'):
            work_trail.resume(self.kernel, self.owner)


class MemoryStop(Workspace):
    def test_a_memory_stop_during_a_handover_stays_in_status_until_a_model_is_ready(self):
        previous = self.register('previous.gguf')
        self.assertIsNone(self.activate(previous, 'previous', {'backend': 'CPU'}, [sim.Worker(n_ctx=4096)]))
        error = self.activate(self.model, 'pressure', {'backend': 'CPU'}, [sim.Worker(exit=75, log=MEMORY_LOG)])
        self.assertTrue(error.startswith('GRAPHITE_HOST_MEMORY_LIMIT'), error)
        status = local_brain.status(self.kernel)
        self.assertEqual((status['worker'], status['resource_stop']), (None, local_brain.MEMORY_STOP))
        self.assertIsNone(self.activate(previous, 'reload', {'backend': 'CPU'}, [sim.Worker(n_ctx=4096)]))
        status = local_brain.status(self.kernel)
        self.assertEqual((status['state'], status['resource_stop']), ('READY', None))


class Offload(Workspace):
    def test_offload_evidence_says_simulated_only_for_a_fixture_runtime(self):
        self.host.graphics = 'accessible'
        self.assertIsNone(self.activate(self.model, 'radeon', {'backend': 'VULKAN'}, [sim.Worker(log=OFFLOAD_41, n_ctx=4096)]))
        worker = local_brain.status(self.kernel)['worker']
        self.assertEqual(worker['offload_evidence'],
                         'SIMULATED_WORKER_LOAD_LOG: offloaded 41/41 layers to GPU (fixture runtime, not a GPU)')
        self.assertEqual(worker['observed_gpu_layers'], 41)
        # A real pinned runtime carries no mark, and records exactly what it did before 0.8.1.
        real = lambda root, backend='CPU': (Path('/real/llama-server'), {'build': 'b11669', 'backend': backend})
        with patch.object(brain_runtime, 'prepare', side_effect=real):
            self.assertIsNone(self.activate(self.model, 'radeon-real', {'backend': 'VULKAN'},
                                            [sim.Worker(log=OFFLOAD_41, n_ctx=4096)]))
        worker = local_brain.status(self.kernel)['worker']
        self.assertEqual(worker['offload_evidence'], 'PINNED_WORKER_LOAD_LOG: offloaded 41/41 layers to GPU')


class SharedReading(unittest.TestCase):
    def test_admission_reads_memory_as_the_worker_guard_does(self):
        with tempfile.TemporaryDirectory(prefix='graphite-cgroup-') as folder:
            box = Path(folder)
            group = box / 'fs' / 'user.slice' / 'graphite.scope'
            group.mkdir(parents=True)
            (box / 'meminfo').write_text('MemTotal:       67108864 kB\nMemAvailable:   41943040 kB\n')
            (box / 'cgroup').write_text('0::/user.slice/graphite.scope\n')
            (group / 'memory.max').write_text(str(32 * GiB))
            (group / 'memory.current').write_text(str(12 * GiB))
            with patch.object(brain_worker, 'MEMINFO', box / 'meminfo'), \
                    patch.object(brain_worker, 'OWN_CGROUP', box / 'cgroup'), patch.object(brain_worker, 'CGROUPS', box / 'fs'):
                host = brain_runtime.host(profile=False)
                rss, total, available = brain_worker.memory_sample(os.getpid())
                self.assertEqual((host['total_ram_bytes'], host['available_ram_bytes']), (total, available))
                self.assertEqual((total, available), (32 * GiB, 20 * GiB))
                (group / 'memory.max').write_text('max\n')     # no limit: MemAvailable stands, as for the guard
                self.assertEqual(brain_runtime.host(profile=False)['available_ram_bytes'], 40 * GiB)
                self.assertEqual(brain_worker.memory_sample(os.getpid())[2], 40 * GiB)


if __name__ == '__main__':
    unittest.main()
