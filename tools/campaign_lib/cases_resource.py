"""The resource simulation set (R01..R22): Graphite's real memory, model and job decisions under injected readings.

R01..R20 follow the twenty cases of the resource map (resources.md section 5). R21 is the resume case and R22
gathers Stop and the holds. Each case runs Graphite's own code: gguf_inspect.inspect/inspect_set through
local_brain.add, local_brain.configuration (at jobs.submit and again at run), resource_control._view, decision
and claim, brain_runtime.probe and parse_devices, local_brain.start_server and run_model_job, brain_worker.supervise.
Only the readings they take from the world are simulated (see sim.py), and every expectation is the decision the
CURRENT code makes. A case whose behaviour a quoted spec line contradicts says so in spec_conflict and counts as
"Pass (current code; the spec asks otherwise)"; none does since the memory rules were fixed (0.8.1), when the
questions R07, R09, R15, R17, R19 and R20 raised were decided in the code:

  R07  Auto takes a model when its estimate, the 2 GiB foreground reserve and 4 GiB headroom fit in what is available.
  R09  unknown installed RAM keeps the full reserve; a request whose reading is lost waits 30 s, then fails saying why.
  R15  one rule (resource_control.budget_room) decides admission, configuration and launch.
  R17  Graphite's own offload evidence says SIMULATED_WORKER_LOAD_LOG when its runtime is a fixture.
  R19  a restored model with an empty reply is not Ready; a worker giving less context than selected is refused.
  R20  a memory-guard stop during a handover stays in brain.status until a model is next Ready.
  R22  a work hold keeps queued work waiting at admission; on release it continues, and completed writes stay single.

Numbers used throughout: the owner's file is 20,542,732,576 bytes; at 4,096 context the code's estimate is
int(bytes*1.3 + KV 167,772,160 + 384 MiB) = 27,275,977,692 bytes (26,013 MiB, 25.40 GiB). Auto needs
26,013 + 2,048 reserve + 4,096 headroom = 32,157 MiB (31.40 GiB) available, and budgets 65% of available, never
below the estimate nor above 32,768 MiB; the foreground reserve with 64 GiB installed is 2 GiB.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
import traceback
import uuid
from contextlib import redirect_stderr
from unittest.mock import patch

from . import gguf_fixture, sim
from .core import Case, code_of

GiB, MiB = sim.GiB, sim.MiB
SIMULATED_LOG = 'llama_model_load: simulated load log'
OFFLOAD_41 = SIMULATED_LOG + '\nload_tensors: offloaded 41/41 layers to GPU\n'


def offload_label(worker):
    """The label for the offload count, read only from Graphite's own worker record.

    SIMULATED when Graphite recorded offloaded layers (backend VULKAN, a positive observed_gpu_layers) and marked its
    evidence as from a fixture runtime (SIMULATED_WORKER_LOAD_LOG); OBSERVED when it recorded them from a real
    runtime's load log (PINNED_WORKER_LOAD_LOG); NO_GPU_OFFLOAD when its record shows none (a CPU fallback, say)."""
    worker = worker or {}
    layers, evidence = worker.get('observed_gpu_layers'), str(worker.get('offload_evidence'))
    simulated = evidence.startswith('SIMULATED_WORKER_LOAD_LOG')
    offloaded = (worker.get('backend') == 'VULKAN' and type(layers) is int and layers > 0
                 and (simulated or evidence.startswith('PINNED_WORKER_LOAD_LOG')))
    if not offloaded:
        return 'NO_GPU_OFFLOAD: Graphite recorded backend %s, %s layers, evidence %s' % (
            worker.get('backend'), layers, evidence)
    return '%s: %d layers per Graphite\'s worker record (%s)' % (
        'SIMULATED' if simulated else 'OBSERVED', layers, evidence)


def message_of(response):
    """The whole refusal text of a dispatch response (code_of keeps only its code)."""
    return ((response or {}).get('error') or {}).get('message')


# ---------------------------------------------------------------- helpers shared by the cases

def defaults(ctx, context=4096, **brain):
    """Saved launch defaults, written as the settings rows the Brain room would write."""
    rows = {'ledger.brain.context': context, **{'ledger.brain.' + k: v for k, v in brain.items()}}
    with ctx.kernel.db() as db:
        for key, value in rows.items():
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (key, json.dumps(value)))
    ctx.progress('defaults', rows=rows)


def where(exc):
    """module:function of the innermost Graphite frame that raised: which check rejected the input."""
    frames = traceback.extract_tb(exc.__traceback__)
    for frame in reversed(frames):
        if '/workbench/' in frame.filename or '/sdk/' in frame.filename:
            return '%s:%s' % (os.path.splitext(os.path.basename(frame.filename))[0], frame.name)
    return frames[-1].name if frames else None


def finish(ctx, ident, state, error=None):
    job = ctx.kernel.record('jobs', ident)
    job.update(state=state, finished=time.time(), error=error)
    ctx.kernel.save('jobs', job)


def register(ctx, variant='valid', name=None):
    """brain.model.add through the Kernel, then the brain.inspect job's own work (local_brain.add) in-process."""
    from workbench import local_brain
    from workbench.engineering_kernel import Principal
    path = ctx.models / (name or variant + '.gguf')
    info = gguf_fixture.build(path, variant)
    ctx.note('gguf:' + path.name, info)
    job = ctx.call('brain.model.add', {'path': str(path)})
    try:
        public = local_brain.add(ctx.kernel, job['request_spec']['brain'], Principal(job['owner']))
    except ValueError as exc:
        finish(ctx, job['id'], 'Failed', str(exc))
        return None, exc, info
    finish(ctx, job['id'], 'Succeeded')
    return local_brain.model(ctx.kernel, public['id']), None, info


def use(ctx, model, key, options=None):
    args = {'id': model['id'], 'request_key': key}
    if options:
        args['options'] = options
    return ctx.try_call('brain.model.use', args)


def claim(ctx, bench, ident, sleeps=3):
    """resource_control.claim until it admits, or until `sleeps` waits have been seen."""
    from workbench import resource_control
    bench.clock.max_sleeps = bench.clock.sleeps + sleeps
    try:
        got = resource_control.claim(ctx.kernel, ident)
    except sim.StopWaiting:
        got = None
    finally:
        bench.clock.max_sleeps = None
    return got, ctx.kernel.record('jobs', ident)


def run_model(ctx, job):
    from workbench import local_brain
    try:
        result = local_brain.run_model_job(ctx.kernel, job)
        finish(ctx, job['id'], 'Succeeded')
        return result, None
    except Exception as exc:  # noqa: BLE001 - the reason is the observation
        finish(ctx, job['id'], 'Failed', str(exc))
        return None, exc


def activate(ctx, bench, model, key, options=None, sleeps=3):
    """Submit, claim and run one model activation; returns (result, error, job)."""
    r = use(ctx, model, key, options)
    if not r['ok']:
        return None, code_of(r), None
    got, job = claim(ctx, bench, r['result']['id'], sleeps)
    if got is None:
        return None, 'NOT_ADMITTED: ' + str(job.get('current_operation')), job
    result, exc = run_model(ctx, got)
    return result, (code_of(exc) if exc else None), got


def put_job(ctx, state, request, pid=None, token=None, tool='native.build'):
    ident = uuid.uuid4().hex
    ctx.kernel.save('jobs', {'id': ident, 'owner': ctx.owner.identity, 'state': state, 'tool': tool, 'goal': tool,
                             'created': time.time(), 'cancel': False, 'pause': False, 'pid': pid, 'worker_start': token,
                             'request_spec': {}, 'resource_request': request, 'current_operation': 'queued',
                             'timeout': 60, 'scope': [], 'candidate': None})
    return ident


def demand(gib, lane='compute', priority='normal'):
    return dict(priority=priority, lane=lane, memory_bytes=int(gib * GiB), basis='CAMPAIGN_DECLARED_REQUEST',
                model_handover=False)


def gib(value):
    return None if value is None else round(value / GiB, 3)


def backends(bench):
    return [argv[argv.index('--backend') + 1] for argv in bench.popen_argv]


def estimate(ctx, model, available_gib=60, memory_mb=None):
    from workbench import local_brain
    options = {'context': 4096, **({'memory_mb': memory_mb} if memory_mb else {})}
    return local_brain.configuration(model, options, ctx.kernel.root)


# ---------------------------------------------------------------- model preflight (R01..R04)

def r01(ctx):
    with sim.Bench(host=sim.FakeHost(60)):
        defaults(ctx)
        model, exc, info = register(ctx)
        ctx.observe('registered', exc is None)
        inspection = model['inspection']
        ctx.observe('architecture', inspection['architecture'])
        ctx.observe('architecture_profile', inspection['architecture_profile'])
        ctx.observe('tensor_types', sorted(inspection['quantization']))
        ctx.observe('tensor_count', inspection['tensor_count'])
        ctx.observe('chat_template_chars', len(model['message_template'] or ''))
        ctx.observe('total_bytes', model['total_bytes'])
        ctx.observe('fixture_disk_under_1_mib', info['disk_bytes'] < MiB)
        ctx.note('identity_in_simulation', 'bounded: size + first 16 MiB + last 1 MiB (%d bytes read at most)'
                 % gguf_fixture.BOUNDED_READ_BYTES)
        config = estimate(ctx, model)
        ctx.observe('estimate_bytes', config['estimated_peak_bytes'])
        ctx.observe('kv_bytes', config['estimated_kv_bytes'])
        r = use(ctx, model, 'use-60')
        ctx.observe('submit', 'ACCEPTED' if r['ok'] else code_of(r))
        ctx.note('fixture', info)


def r02(ctx):
    from workbench import local_brain
    with sim.Bench(host=sim.FakeHost(60)):
        for variant in ('bad_magic', 'truncated'):
            model, exc, info = register(ctx, variant)
            ctx.observe(variant + ':reason', code_of(exc) if exc else 'REGISTERED')
            ctx.observe(variant + ':rejected_by', where(exc) if exc else None)
        ctx.observe('records_written', len(local_brain.models(ctx.kernel)))


def r03(ctx):
    from workbench import local_brain
    with sim.Bench(host=sim.FakeHost(60, graphics='accessible')) as bench:
        defaults(ctx)
        model, exc, info = register(ctx)
        r = use(ctx, model, 'use-changed')
        got, job = claim(ctx, bench, r['result']['id'])
        ctx.observe('planned_backend', local_brain.configuration(model, got['brain_launch']['options'], ctx.kernel.root)['backend'])
        gguf_fixture.change_after_registration(ctx.models / 'valid.gguf', info['data_offset'])
        ctx.fault('model file changed after registration', offset=info['data_offset'])
        result, exc = run_model(ctx, got)
        ctx.observe('reason', code_of(exc))
        ctx.observe('rejected_by', where(exc))
        ctx.observe('workers_started', len(bench.popen_argv))


def r04(ctx):
    from workbench import local_brain
    with sim.Bench(host=sim.FakeHost(60)):
        defaults(ctx)
        for variant in ('unsupported_architecture', 'unsupported_tensor_type', 'no_chat_template'):
            model, exc, info = register(ctx, variant)
            ctx.observe(variant + ':registered', exc is None)
            ctx.observe(variant + ':profile', model['inspection']['architecture_profile'])
            r = use(ctx, model, 'use-' + variant)
            ctx.observe(variant + ':submit', 'ACCEPTED' if r['ok'] else code_of(r))
            try:
                local_brain.configuration(model, {'context': 4096}, ctx.kernel.root)
                ctx.observe(variant + ':rejected_by', None)
            except ValueError as error:
                ctx.observe(variant + ':rejected_by', where(error))
            if variant == 'unsupported_tensor_type':
                ctx.observe('type_label', sorted(k for k in model['inspection']['quantization'] if 'UNSUPPORTED' in k))


# ---------------------------------------------------------------- shared RAM admission (R05..R11)

def _admission(ctx, available, options=None, key='use'):
    with sim.Bench(host=sim.FakeHost(available)) as bench:
        defaults(ctx)
        model, _, _ = register(ctx)
        try:
            config = estimate(ctx, model, available, (options or {}).get('memory_mb'))
            ctx.observe('estimate_bytes', config['estimated_peak_bytes'])
            ctx.observe('cap_mb', config['memory_mb'])
        except ValueError as error:
            ctx.observe('configuration', code_of(error))
        r = use(ctx, model, key, options)
        ctx.observe('submit', 'ACCEPTED' if r['ok'] else code_of(r))
        if not r['ok']:
            return bench, model, None
        ctx.observe('frozen_memory_mb', r['result']['brain_launch']['options']['memory_mb'])
        got, job = claim(ctx, bench, r['result']['id'])
        ctx.observe('admitted', got is not None)
        admission = (got or job).get('resource_admission') or job.get('resource_wait') or {}
        ctx.observe('headroom_gib', gib(admission.get('headroom_bytes')))
        ctx.observe('requested_mib', (admission.get('requested_bytes') or 0) // MiB)
        ctx.observe('reserve_mib', (admission.get('reserve_bytes') or 0) // MiB)
        return bench, model, got


def r05(ctx):
    _admission(ctx, 60)


def r06(ctx):
    _admission(ctx, 40)


def r07(ctx):
    with sim.Bench(host=sim.FakeHost(39)) as bench:
        defaults(ctx)
        model, _, _ = register(ctx)
        config = estimate(ctx, model, 39)
        ctx.observe('estimate_bytes', config['estimated_peak_bytes'])
        ctx.observe('auto_cap_mb', config['memory_mb'])
        auto = use(ctx, model, 'auto-39')
        ctx.observe('auto_submit', 'ACCEPTED' if auto['ok'] else code_of(auto))
        ctx.observe('auto_frozen_memory_mb', auto['result']['brain_launch']['options']['memory_mb'] if auto['ok'] else None)
        got, job = claim(ctx, bench, auto['result']['id'])
        ctx.observe('auto_admitted', got is not None)
        ctx.observe('auto_headroom_gib', gib((got or job).get('resource_admission', {}).get('headroom_bytes')))
        finish(ctx, auto['result']['id'], 'Cancelled', 'campaign: admission seen; the load is R17\'s')
        manual = use(ctx, model, 'manual-39', {'memory_mb': 26100})
        ctx.observe('manual_26100_submit', 'ACCEPTED' if manual['ok'] else code_of(manual))
        got, job = claim(ctx, bench, manual['result']['id'])
        ctx.observe('manual_admitted', got is not None)
        ctx.observe('manual_headroom_gib', gib((got or job).get('resource_admission', {}).get('headroom_bytes')))


def r08(ctx):
    host = sim.FakeHost(30)
    with sim.Bench(host=host):
        defaults(ctx)
        model, _, _ = register(ctx)
        auto = use(ctx, model, 'auto-30')
        ctx.observe('auto_submit', 'ACCEPTED' if auto['ok'] else code_of(auto))
        ctx.observe('auto_refusal', message_of(auto))
        # The smallest availability Auto accepts for this model at 4,096 tokens: 26,013 + 2,048 + 4,096 MiB.
        for mib in (32157, 32156):
            host.available = mib / 1024
            r = use(ctx, model, 'auto-%d' % mib)
            ctx.observe('auto_at_%d_mib' % mib, 'ACCEPTED' if r['ok'] else code_of(r))
        host.available = 30
        manual = use(ctx, model, 'manual-30', {'memory_mb': 26100})
        ctx.observe('manual_26100_submit', 'ACCEPTED' if manual['ok'] else code_of(manual))
        manual = use(ctx, model, 'manual-30-large', {'memory_mb': 29000})
        ctx.observe('manual_29000_submit', 'ACCEPTED' if manual['ok'] else code_of(manual))
        ctx.observe('manual_29000_refusal', message_of(manual))


def r09(ctx):
    from workbench import resource_control
    host = sim.FakeHost(None)
    with sim.Bench(host=host) as bench:
        defaults(ctx)
        model, _, _ = register(ctx)
        r = use(ctx, model, 'none-at-submit')
        ctx.observe('submit_unmeasured', 'ACCEPTED' if r['ok'] else code_of(r))
        host.available = 60
        r = use(ctx, model, 'measured-at-submit')
        host.available = None
        ctx.fault('available RAM reading lost after submit')
        got, job = claim(ctx, bench, r['result']['id'])
        ctx.observe('admitted_unmeasured', got is not None)
        ctx.observe('wait_reason', job.get('current_operation'))
        ctx.observe('wait_saved', (job.get('resource_wait') or {}).get('reason'))
        ctx.observe('state', job['state'])
        began = bench.clock.now
        got, job = claim(ctx, bench, r['result']['id'], sleeps=200)
        ctx.observe('deadline:admitted', got is not None)
        ctx.observe('deadline:state', job['state'])
        ctx.observe('deadline:error', job.get('error'))
        ctx.observe('deadline:waited_s', round(bench.clock.now - began, 1))
        with ctx.kernel.db() as db:
            policy = resource_control.policy(db, {'total_ram_bytes': None, 'logical_cpus': 16})
        ctx.observe('reserve_mib_without_total', policy['reserve_bytes'] // MiB)


def r10(ctx):
    from workbench import local_brain
    with sim.Bench(host=sim.FakeHost(60)):
        defaults(ctx)
        model, _, _ = register(ctx)
        r = use(ctx, model, 'manual-16384', {'memory_mb': 16384})
        ctx.observe('submit', 'ACCEPTED' if r['ok'] else code_of(r))
        ctx.observe('refusal', message_of(r))
        try:
            local_brain.configuration(model, {'context': 4096, 'memory_mb': 16384}, ctx.kernel.root)
        except ValueError as error:
            ctx.observe('rejected_by', where(error))


def r11(ctx):
    from workbench import resource_control
    with sim.Bench(host=sim.FakeHost(40)) as bench:
        job_pid = sim.NOBODY + 11
        token = bench.procs.add(job_pid, rss_bytes=2 * GiB)
        put_job(ctx, 'Running', demand(10, 'io'), job_pid, token, tool='intake.read')
        model_pid = sim.NOBODY + 12
        model_token = bench.procs.add(model_pid, rss_bytes=8 * GiB)
        worker = dict(pid=model_pid, start=model_token, model_id='f' * 64, owner=ctx.owner.identity, job_id='c' * 32,
                      config={'memory_mb': 8192}, key_file=str(ctx.folder / 'none.key'))
        from workbench import local_brain
        local_brain.put(ctx.kernel, 'worker', worker)
        local_brain.put(ctx.kernel, 'trial_worker', worker)
        ctx.fault('one resident model listed in both worker slots')
        with ctx.kernel.db() as db:
            view = resource_control._view(ctx.kernel, db, bench.host(profile=False))
        ctx.observe('available_gib', gib(view['available_bytes']))
        ctx.observe('reserve_gib', gib(view['policy']['reserve_bytes']))
        ctx.observe('future_gib', gib(view['reserved_future_bytes']))
        ctx.observe('headroom_gib', gib(view['headroom_bytes']))
        ctx.observe('commitments', sorted(row['kind'] for row in view['commitments']))


# ---------------------------------------------------------------- competing work (R12..R16)

def _compute(ctx, available, other=None):
    with sim.Bench(host=sim.FakeHost(available)) as bench:
        if other:
            pid = sim.NOBODY + 13
            token = bench.procs.add(pid, rss_bytes=2 * GiB)
            put_job(ctx, 'Running', demand(10, other), pid, token, tool='intake.read' if other == 'io' else 'lab.python')
        ident = put_job(ctx, 'Queued', demand(32))
        got, job = claim(ctx, bench, ident)
        admission = (got or job).get('resource_admission') or job.get('resource_wait') or {}
        return got, job, admission


def r12(ctx):
    got, job, admission = _compute(ctx, 34)
    ctx.observe('admitted', got is not None)
    ctx.observe('headroom_gib', gib(admission.get('headroom_bytes')))
    ctx.observe('requested_gib', gib(admission.get('requested_bytes')))


def r13(ctx):
    got, job, admission = _compute(ctx, 33)
    ctx.observe('admitted', got is not None)
    ctx.observe('reason', job.get('current_operation'))
    ctx.observe('wait_saved', (job.get('resource_wait') or {}).get('reason'))
    ctx.observe('headroom_gib', gib(admission.get('headroom_bytes')))


def r14(ctx):
    got, job, admission = _compute(ctx, 40, other='io')
    ctx.observe('io_other:admitted', got is not None)
    ctx.observe('io_other:reason', job.get('current_operation'))
    ctx.observe('io_other:future_gib', gib(admission.get('reserved_future_bytes')))
    ctx.observe('io_other:headroom_gib', gib(admission.get('headroom_bytes')))
    with ctx.kernel.db() as db:
        db.execute("UPDATE jobs SET state='Cancelled' WHERE state IN ('Queued','Running')")
    got, job, admission = _compute(ctx, 40, other='compute')
    ctx.observe('compute_other:reason', job.get('current_operation'))


def r15(ctx):
    from workbench import local_brain
    host = sim.FakeHost(40)
    with sim.Bench(host=host, workers=[sim.Worker(n_ctx=4096)]) as bench:
        defaults(ctx)
        model, _, _ = register(ctx)
        r = use(ctx, model, 'use-32g', {'memory_mb': 32768})
        ctx.observe('submit_at_40', 'ACCEPTED' if r['ok'] else code_of(r))
        host.available = 34
        ctx.fault('available RAM falls from 40 to 34 GiB after submit')
        got, job = claim(ctx, bench, r['result']['id'])
        ctx.observe('admitted_at_34', got is not None)
        ctx.observe('admission_headroom_gib', gib((got or job).get('resource_admission', {}).get('headroom_bytes')))
        result, exc = run_model(ctx, got)
        ctx.observe('run_reason', code_of(exc) if exc else 'ACTIVATED')
        ctx.observe('workers_started', len(bench.popen_argv))
        ctx.observe('state', local_brain.status(ctx.kernel)['state'])
        local_brain.stop(ctx.kernel)
        # One MiB less room than the budget: admission waits, so launch never meets a request it would refuse.
        r = use(ctx, model, 'use-32g-again', {'memory_mb': 32768})
        host.available = 34 - 1 / 1024
        ctx.fault('available RAM falls to 34 GiB less 1 MiB after the second submit')
        got, job = claim(ctx, bench, r['result']['id'])
        ctx.observe('one_mib_short:admitted', got is not None)
        ctx.observe('one_mib_short:reason', job.get('current_operation'))
        ctx.observe('owned_workers_left', bench.live_workers())


def r16(ctx):
    from workbench import memory_forecast
    clock = sim.FakeClock(start=1000.0)
    host = sim.FakeHost(lambda c: 10 - 0.5 * min(max(c.now - 1000.0, 0), 2), clock=clock)
    with sim.Bench(host=host, clock=clock) as bench:
        with ctx.kernel.db() as db:
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', ('resources.foreground',
                       json.dumps({'owner': ctx.owner.identity, 'until': clock.time() + 2})))
        ctx.fault('desk active for 2 s; available RAM falls 0.5 GiB/s for 2 s then holds at 9 GiB')
        ident = put_job(ctx, 'Queued', demand(6.95, priority='background'))
        seen = []

        def look(c):
            row = ctx.kernel.record('jobs', ident)
            if not seen or seen[-1][1] != row.get('current_operation'):
                seen.append((round(c.now - 1000.0, 2), row.get('current_operation')))
        clock.hooks.append(look)
        got, job = claim(ctx, bench, ident, sleeps=80)
        clock.hooks.clear()
        forecast = ((got or job).get('resource_admission') or {}).get('memory_forecast') or {}
        reasons = [r for _, r in seen]
        ctx.note('reason_timeline', seen)
        ctx.observe('first_reason', reasons[0] if reasons else None)
        ctx.observe('forecast_deferred', memory_forecast.WAIT_REASON in reasons)
        ctx.observe('admitted', got is not None)
        ctx.observe('forecast_outcome', forecast.get('outcome'))
        start = next((t for t, r in seen if r == memory_forecast.WAIT_REASON), None)
        ctx.observe('deferred_seconds', round(clock.now - 1000.0 - start, 1) if start is not None else None)


# ---------------------------------------------------------------- Radeon discovery (R17, R18)

def r17(ctx):
    from workbench import local_brain
    devices = ctx.case.inputs.get('devices', 'radeon')        # the selftest T03 runs the same steps on llvmpipe
    with sim.Bench(host=sim.FakeHost(60, graphics=ctx.case.inputs.get('graphics', 'accessible')), devices=devices,
                   workers=[sim.Worker(log=OFFLOAD_41, n_ctx=4096)]) as bench:
        defaults(ctx)
        model, _, _ = register(ctx)
        result, error, job = activate(ctx, bench, model, 'radeon')
        ctx.observe('result', result['status'] if result else error)
        status = local_brain.status(ctx.kernel)
        worker = status['worker'] or {}
        ctx.observe('state', status['state'])
        ctx.observe('requested_backend', worker.get('requested_backend'))
        ctx.observe('effective_backend', worker.get('backend'))
        ctx.observe('observed_gpu_layers', worker.get('observed_gpu_layers'))
        ctx.observe('offload_evidence', worker.get('offload_evidence'))
        ctx.observe('offload_label', offload_label(worker))
        ctx.observe('offload_evidence_marks_simulated', str(worker.get('offload_evidence')).startswith('SIMULATED_'))
        argv = bench.popen_argv[0]
        ctx.observe('argv_ngl', argv[argv.index('-ngl') + 1])
        ctx.observe('argv_fit', argv[argv.index('--fit') + 1])
        ctx.observe('argv_device', argv[argv.index('--device') + 1])
        probe = local_brain.get(ctx.kernel, 'acceleration_probe', {})
        ctx.observe('probe_state', probe.get('state'))
        ctx.observe('probe_device', (probe.get('devices') or [{}])[0].get('name'))
        local_brain.stop(ctx.kernel)
        ctx.observe('owned_workers_left', bench.live_workers())


def r18(ctx):
    from workbench import local_brain
    host = sim.FakeHost(60, graphics='inaccessible')
    with sim.Bench(host=host, devices='llvmpipe') as bench:
        defaults(ctx)
        model, _, _ = register(ctx)
        config = local_brain.configuration(model, {'context': 4096, 'backend': 'AUTO'}, ctx.kernel.root)
        ctx.observe('inaccessible:backend', config['backend'])
        ctx.observe('inaccessible:reason', config['fallback_reason'])
        host.graphics = 'none'
        ctx.observe('missing:backend', local_brain.configuration(model, {'context': 4096, 'backend': 'AUTO'},
                                                                ctx.kernel.root)['backend'])
        # Software Vulkan only: the probe sees llvmpipe; with fallback the load goes to CPU, without it is refused.
        bench.workers = [sim.Worker(n_ctx=4096)]
        result, error, job = activate(ctx, bench, model, 'llvmpipe', {'backend': 'VULKAN'})
        worker = local_brain.status(ctx.kernel)['worker'] or {}
        ctx.observe('software:probe_state', local_brain.get(ctx.kernel, 'acceleration_probe', {}).get('state'))
        ctx.observe('software:effective_backend', worker.get('backend'))
        ctx.observe('software:fallback_reason', worker.get('fallback_reason'))
        local_brain.stop(ctx.kernel)
        started = len(bench.popen_argv)
        result, error, job = activate(ctx, bench, model, 'llvmpipe-nofallback', {'backend': 'VULKAN', 'cpu_fallback': False})
        ctx.observe('software_no_fallback:reason', error)
        ctx.observe('software_no_fallback:workers_started', len(bench.popen_argv) - started)
        # Physical Radeon, but the load log shows zero offloaded layers, or no offload line at all.
        bench.devices = 'radeon'
        host.graphics = 'accessible'
        for name, log in (('zero_offload', 'load_tensors: offloaded 0/41 layers to GPU\n'), ('missing_offload', 'no offload line\n')):
            local_brain.stop(ctx.kernel)
            started = len(bench.popen_argv)
            bench.workers = [sim.Worker(log=log, n_ctx=4096), sim.Worker(n_ctx=4096)]
            result, error, job = activate(ctx, bench, model, name)
            worker = local_brain.status(ctx.kernel)['worker'] or {}
            ctx.observe(name + ':backends_tried', backends(bench)[started:])
            ctx.observe(name + ':effective_backend', worker.get('backend'))
            ctx.observe(name + ':fallback_reason', worker.get('fallback_reason'))
        local_brain.stop(ctx.kernel)
        ctx.observe('owned_workers_left', bench.live_workers())


# ---------------------------------------------------------------- load and first reply (R19)

def r19(ctx):
    from workbench import local_brain
    with sim.Bench(host=sim.FakeHost(60, graphics='accessible'), devices='radeon') as bench:
        defaults(ctx)
        model, _, _ = register(ctx)
        other, _, _ = register(ctx, 'valid', name='previous.gguf')

        def attempt(name, workers, options=None, stretch=1.0):
            local_brain.stop(ctx.kernel)
            started = len(bench.popen_argv)
            bench.workers = list(workers)
            bench.clock.stretch = stretch
            began = bench.clock.now
            result, error, job = activate(ctx, bench, model, name, options)
            bench.clock.stretch = 1.0
            ctx.observe(name + ':backends_tried', backends(bench)[started:])
            return result, error, bench.clock.now - began

        result, error, waited = attempt('timeout', [sim.Worker(health=False), sim.Worker(health=False)], stretch=12.5)
        ctx.fault('worker never reports healthy (fake clock runs 12.5x during load)')
        ctx.observe('timeout:reason', error)
        ctx.observe('timeout:simulated_seconds_at_least_180', waited >= 180)
        result, error, _ = attempt('driver_exit', [sim.Worker(exit=1, log='ggml_vulkan: ErrorDeviceLost\n'), sim.Worker(n_ctx=4096)])
        worker = local_brain.status(ctx.kernel)['worker'] or {}
        ctx.observe('driver_exit:effective_backend', worker.get('backend'))
        ctx.observe('driver_exit:fallback_reason', (worker.get('fallback_reason') or '')[:48])
        result, error, _ = attempt('empty_reply', [sim.Worker(log=OFFLOAD_41, n_ctx=4096, reply='')])
        ctx.observe('empty_reply:reason', error)
        ctx.observe('empty_reply:state', local_brain.status(ctx.kernel)['state'])
        result, error, _ = attempt('http_500', [sim.Worker(log=OFFLOAD_41, n_ctx=4096, reply='HTTP 500'), sim.Worker(n_ctx=4096)])
        ctx.observe('http_500:qualification', (result or {}).get('qualification', {}).get('state', error))
        result, error, _ = attempt('small_context', [sim.Worker(n_ctx=2048)], {'backend': 'CPU'})
        status = local_brain.status(ctx.kernel)
        ctx.observe('small_context:reason', error)
        ctx.observe('small_context:state', status['state'])
        ctx.observe('small_context:selection_context', status['selection'].get('config', {}).get('context'))
        # The same on Vulkan: an eligible load failure, so one CPU retry, which gives the selected context.
        result, error, _ = attempt('small_context_vulkan', [sim.Worker(log=OFFLOAD_41, n_ctx=2048), sim.Worker(n_ctx=4096)])
        status = local_brain.status(ctx.kernel)
        ctx.observe('small_context_vulkan:state', status['state'])
        ctx.observe('small_context_vulkan:worker_context', (status['worker'] or {}).get('context'))
        ctx.observe('small_context_vulkan:fallback_reason', (status['worker'] or {}).get('fallback_reason'))
        # Ordinary failed handover: the previous model is live, the new one fails to load; the previous comes back.
        local_brain.stop(ctx.kernel)
        bench.workers = [sim.Worker(n_ctx=4096)]
        activate(ctx, bench, other, 'previous-ok', {'backend': 'CPU'})
        for name, restore_reply in (('handover', 'ready'), ('handover_empty_restore', '')):
            started = len(bench.popen_argv)
            bench.workers = [sim.Worker(exit=1, log='load failed\n'), sim.Worker(n_ctx=4096, reply=restore_reply)]
            result, error, job = activate(ctx, bench, model, name, {'backend': 'CPU'})
            status = local_brain.status(ctx.kernel)
            ctx.observe(name + ':reason', error)
            ctx.observe(name + ':workers_started', len(bench.popen_argv) - started)
            ctx.observe(name + ':restored_previous', (status['worker'] or {}).get('model_id') == other['id'])
            ctx.observe(name + ':state', status['state'])
        local_brain.stop(ctx.kernel)
        ctx.observe('owned_workers_left', bench.live_workers())


# ---------------------------------------------------------------- pressure (R20) and Stop (R22)

def r20(ctx):
    from workbench import brain_worker, local_brain
    host = sim.FakeHost(60, graphics='accessible')
    with sim.Bench(host=host, devices='radeon') as bench:
        defaults(ctx)
        model, _, _ = register(ctx)
        other, _, _ = register(ctx, 'valid', name='previous.gguf')
        bench.workers = [sim.Worker(n_ctx=4096)]
        activate(ctx, bench, other, 'previous-ok', {'backend': 'CPU'})
        started = len(bench.popen_argv)
        bench.workers = [sim.Worker(exit=75, log='GRAPHITE_HOST_MEMORY_LIMIT: resident budget or shared-host headroom exhausted\n'),
                         sim.Worker(n_ctx=4096)]
        ctx.fault('worker guard stops the Vulkan load for low shared RAM')
        result, error, job = activate(ctx, bench, model, 'pressure-load')
        status = local_brain.status(ctx.kernel)
        ctx.observe('load:reason', error)
        ctx.observe('load:workers_started', len(bench.popen_argv) - started)
        ctx.observe('load:previous_restored', bool(status['worker']))
        ctx.observe('load:selection_kept', status['selection'].get('model_id') == other['id'])
        ctx.observe('load:previous_qualification_kept', local_brain.model(ctx.kernel, other['id'])['qualification'].get('state'))
        ctx.observe('load:status_resource_stop', status['resource_stop'])
        # Admitted, then another job's growth takes the room before launch: model_room refuses at launch.
        local_brain.stop(ctx.kernel)
        r = use(ctx, model, 'room-shortfall')
        got, job = claim(ctx, bench, r['result']['id'])
        pid = sim.NOBODY + 20
        put_job(ctx, 'Running', demand(10, 'io'), pid, bench.procs.add(pid, rss_bytes=2 * GiB), tool='intake.read')
        host.available = 40
        ctx.fault('after admission: available RAM 40 GiB and another job holds 8 GiB of future growth')
        started = len(bench.popen_argv)
        result, exc = run_model(ctx, got)
        ctx.observe('launch:reason', code_of(exc) if exc else 'ACTIVATED')
        ctx.observe('launch:rejected_by', where(exc) if exc else None)
        ctx.observe('launch:workers_started', len(bench.popen_argv) - started)
        ctx.observe('launch:status_resource_stop', local_brain.status(ctx.kernel)['resource_stop'])
        # The memory notice stays until a model is next Ready, then goes.
        with ctx.kernel.db() as db:
            db.execute("UPDATE jobs SET state='Cancelled' WHERE state IN ('Queued','Running')")
        host.available = 60
        bench.workers = [sim.Worker(n_ctx=4096)]
        result, error, job = activate(ctx, bench, other, 'reload-after-pressure', {'backend': 'CPU'})
        status = local_brain.status(ctx.kernel)
        ctx.observe('reload:state', status['state'])
        ctx.observe('reload:status_resource_stop', status['resource_stop'])
        local_brain.stop(ctx.kernel)
        ctx.observe('owned_workers_left', bench.live_workers())
    # Low RAM while the worker runs: the real supervisor (outside the bench, with a real child) kills it and exits 75.
    samples = iter([(1 * GiB, 64 * GiB, 30 * GiB)] + [(1 * GiB, 64 * GiB, 1 * GiB)] * 100)
    err = io.StringIO()
    began = time.monotonic()
    with patch.object(brain_worker, 'memory_sample', side_effect=lambda pid: next(samples)), redirect_stderr(err):
        code = brain_worker.supervise([sys.executable, '-c', 'import time; time.sleep(30)'], 4096, 'VULKAN', 2048)
    ctx.fault('available RAM falls to 1 GiB while the worker runs')
    ctx.observe('work:supervisor_exit', code)
    ctx.observe('work:marker', 'GRAPHITE_HOST_MEMORY_LIMIT' in err.getvalue())
    ctx.observe('work:stopped_within_s', round(time.monotonic() - began, 1) <= 5)
    # Admission (brain_runtime.host, unpatched here) and the guard read memory the same way: in a cgroup v2 group
    # limited to 32 GiB with 12 GiB used, both see 20 GiB available, though /proc/meminfo says 40.
    from workbench import brain_runtime
    box = ctx.folder / 'cgroup_fixture'
    group = box / 'fs' / 'user.slice' / 'graphite.scope'
    group.mkdir(parents=True)
    (box / 'meminfo').write_text('MemTotal:       67108864 kB\nMemAvailable:   41943040 kB\n')
    (box / 'cgroup').write_text('0::/user.slice/graphite.scope\n')
    (group / 'memory.max').write_text(str(32 * GiB))
    (group / 'memory.current').write_text(str(12 * GiB))
    ctx.fault('this process in a cgroup v2 group limited to 32 GiB, 12 GiB used (fixture files)')
    with patch.object(brain_worker, 'MEMINFO', box / 'meminfo'), patch.object(brain_worker, 'OWN_CGROUP', box / 'cgroup'), \
            patch.object(brain_worker, 'CGROUPS', box / 'fs'):
        ctx.observe('cgroup:admission_available_gib', gib(brain_runtime.host(profile=False)['available_ram_bytes']))
        ctx.observe('cgroup:guard_available_gib', gib(brain_worker.memory_sample(os.getpid())[2]))


def r22(ctx):
    from workbench import local_brain, resource_control, work_trail
    with sim.Bench(host=sim.FakeHost(60), devices='radeon') as bench:
        defaults(ctx)
        model, _, _ = register(ctx)
        other, _, _ = register(ctx, 'valid', name='previous.gguf')
        r = use(ctx, model, 'cancel-queued')
        ctx.call('jobs.cancel', {'id': r['result']['id']})
        ctx.observe('queued_cancel:state', ctx.kernel.record('jobs', r['result']['id'])['state'])

        def cancel_job(ident):
            def hook(b):
                job = ctx.kernel.record('jobs', ident)
                job['cancel'] = True
                ctx.kernel.save('jobs', job)
            return hook
        r = use(ctx, model, 'cancel-loading')
        got, job = claim(ctx, bench, r['result']['id'])
        bench.workers = [sim.Worker(health=False, on_health=cancel_job(got['id']))]
        started = len(bench.popen_argv)
        result, exc = run_model(ctx, got)
        ctx.observe('loading_cancel:reason', code_of(exc))
        ctx.observe('loading_cancel:workers_started', len(bench.popen_argv) - started)
        ctx.observe('loading_cancel:workers_left', bench.live_workers())
        # Owner Stop while a handover is loading, with a previous model live: stopped, nothing restored.
        bench.workers = [sim.Worker(n_ctx=4096)]
        activate(ctx, bench, other, 'previous-ok', {'backend': 'CPU'})
        r = use(ctx, model, 'stop-loading', {'backend': 'CPU'})
        got, job = claim(ctx, bench, r['result']['id'])
        bench.workers = [sim.Worker(health=False, on_health=lambda b: local_brain.stop(ctx.kernel, 'OWNER_STOP')),
                         sim.Worker(n_ctx=4096)]
        started = len(bench.popen_argv)
        ctx.fault('owner presses Stop while the new model is loading')
        result, exc = run_model(ctx, got)
        ctx.observe('running_stop:reason', code_of(exc))
        ctx.observe('running_stop:workers_started', len(bench.popen_argv) - started)
        ctx.observe('running_stop:state', local_brain.status(ctx.kernel)['state'])
        # The desk is active: a background request waits for the foreground turn.
        resource_control.touch(ctx.kernel, ctx.owner.identity)
        ident = put_job(ctx, 'Queued', demand(1, priority='background'))
        got, job = claim(ctx, bench, ident)
        ctx.observe('foreground:reason', job.get('current_operation'))
        # A work hold while two background requests are queued: a calculation, and loading `model` (the next step
        # after `other`'s activation, a write already completed above).
        bench.clock.now += 20     # the lease has expired
        with resource_control.scope('background'):
            load = use(ctx, model, 'held-load', {'backend': 'CPU'})['result']['id']
        work_trail.hold(ctx.kernel, ctx.owner)
        ctx.fault('owner holds work while two background requests are queued')
        started = len(bench.popen_argv)
        got, job = claim(ctx, bench, ident)
        ctx.observe('hold:state', job['state'])
        ctx.observe('hold:error', job.get('error'))
        ctx.observe('hold:reason', job.get('current_operation'))
        got, job = claim(ctx, bench, load)
        ctx.observe('hold:load_state', job['state'])
        ctx.observe('hold:workers_started', len(bench.popen_argv) - started)
        # Release: both continue from the step they waited at; nothing is replayed.
        released = work_trail.resume(ctx.kernel, ctx.owner)
        ctx.fault('owner releases the hold')
        ctx.observe('release:jobs_replayed', released.get('jobs_replayed'))
        ctx.observe('release:jobs_continuing', released.get('jobs_continuing'))
        bench.workers = [sim.Worker(n_ctx=4096)]
        got, job = claim(ctx, bench, load)
        result, exc = run_model(ctx, got) if got else (None, 'NOT_ADMITTED')
        ctx.observe('release:load', result['status'] if result else code_of(exc))
        again, _ = claim(ctx, bench, load)
        ctx.observe('release:load_claimed_again', again is not None)
        ctx.observe('release:workers_started', len(bench.popen_argv) - started)
        got, job = claim(ctx, bench, ident)
        ctx.observe('release:state', job['state'])
        # Completed writes occur once: one activation record each for `other` (before the hold) and `model` (after).
        with ctx.kernel.db() as db:
            events = [json.loads(row[0]) for row in db.execute('SELECT payload FROM activity_journal')]
        activated = [e.get('source_generation') for e in events
                     if e.get('operation') == 'brain.selection' and e.get('state') == 'ACTIVATED']
        ctx.observe('writes:previous_activated', activated.count(other['id']))
        ctx.observe('writes:held_load_activated', activated.count(model['id']))
        local_brain.stop(ctx.kernel)
        ctx.observe('owned_workers_left', bench.live_workers())


# ---------------------------------------------------------------- resume after a kill (R21)

def r21(ctx):
    """Step 1 writes a setting and checkpoints; the runner kills the attempt; the resumed attempt continues."""
    from workbench import ledger_control

    def row(key):
        return next(r for r in ctx.call('ledger.settings')['settings'] if r['key'] == key)

    def changes(key):
        return [c for c in ledger_control.history(ctx.kernel, key, ctx.owner)['changes'] if c.get('key') == key]

    if ctx.phase == 'first':
        before = row('brain.context')
        ctx.call('ledger.settings.set', {'key': 'brain.context', 'value': 4096, 'expected_revision': before['revision']})
        after = row('brain.context')
        ctx.checkpoint('step1', key='brain.context', revision=after['revision'], value=4096)
        ctx.progress('step2', state='started; simulated long job')
        time.sleep(600)          # the runner kills the attempt here
        return
    saved = ctx.read_checkpoint()
    ctx.observe('resumed_from', saved and saved['step'])
    current = row('brain.context')
    ctx.observe('revision_matches_checkpoint', current['revision'] == saved['revision'])
    if current['revision'] != saved['revision'] or current['stored'] != saved['value']:
        ctx.call('ledger.settings.set', {'key': 'brain.context', 'value': 4096, 'expected_revision': current['revision']})
    stale = ctx.try_call('ledger.settings.set', {'key': 'brain.context', 'value': 4096, 'expected_revision': 'stale-revision'})
    ctx.observe('blind_rewrite_refused', not stale['ok'])
    threads = row('brain.threads')
    ctx.call('ledger.settings.set', {'key': 'brain.threads', 'value': 6, 'expected_revision': threads['revision']})
    ctx.observe('step1_writes', len(changes('brain.context')))
    ctx.observe('step2_writes', len(changes('brain.threads')))
    ctx.observe('context_now', row('brain.context')['stored'])
    ctx.observe('threads_now', row('brain.threads')['stored'])


# ---------------------------------------------------------------- the declarations

ALLOWED_MODEL = ['brain.model.add', 'brain.model.use', 'jobs.cancel', 'brain.stop', 'ledger.settings']


def _case(ident, number, title, fn, expect, spec_question=None, faults=(), inputs=None, budget=60, start=None,
          allowed=None, resume=None, spec_conflict=None):
    return Case(id=ident, set='resource', title=title, situation='S28' if number in (11, 12, 13, 14, 16, 20) else None,
                seed='base', start=start or {'workspace': 'empty Office', 'host': 'simulated', 'total_ram_gib': 64,
                                             'context': 4096, 'memory': 'Auto'},
                inputs=inputs or {}, allowed=allowed or ALLOWED_MODEL, faults=list(faults), expect=expect,
                budget_s=budget, mode='sim', spec_question=spec_question, spec_conflict=spec_conflict, resume=resume,
                source_case='resources.md section 5, case %d' % number if number else None, fn=fn)


SPEC = 'spec.txt (35B Simulation Specification, draft 0.2), Resource control'


ESTIMATE = 27_275_977_692
CASES = [
    _case('R01', 1, 'Valid qwen35moe fixture registers and is accepted', r01, {
        'registered': True, 'architecture': 'qwen35moe', 'architecture_profile': 'SUPPORTED_FOR_TRIAL',
        'tensor_types': ['F32', 'Q4_K', 'Q8_0'], 'tensor_count': 733, 'chat_template_chars': 7816,
        'total_bytes': 20_542_732_576, 'fixture_disk_under_1_mib': True,
        'estimate_bytes': ESTIMATE, 'kv_bytes': 167_772_160, 'submit': 'ACCEPTED'},
        inputs={'gguf': 'valid fixture from the real header', 'available_gib': 60}),
    _case('R02', 2, 'Invalid files are rejected by the inspector', r02, {
        'bad_magic:reason': 'GGUF_MAGIC_INVALID', 'bad_magic:rejected_by': 'gguf_inspect:inspect',
        'truncated:reason': 'GGUF_TENSOR_DATA_TRUNCATED', 'truncated:rejected_by': 'gguf_inspect:inspect',
        'records_written': 0}, inputs={'gguf': ['bad_magic', 'truncated']}),
    _case('R03', 3, 'A file changed after registration is refused before load', r03, {
        'reason': 'MODEL_FILE_CHANGED_SINCE_REGISTRATION', 'rejected_by': 'local_brain:recheck',
        'workers_started': 0, 'planned_backend': 'VULKAN'},
        faults=[{'at': 'after claim', 'fault': 'one byte of tensor data changed'}]),
    _case('R04', 4, 'Unsupported architecture, tensor type or missing template fail at submit', r04, {
        'unsupported_architecture:registered': True, 'unsupported_architecture:profile': 'UNSUPPORTED_ARCHITECTURE',
        'unsupported_architecture:submit': 'MODEL_ARCHITECTURE_NOT_IN_SUPPORTED_PROFILE',
        'unsupported_architecture:rejected_by': 'local_brain:configuration',
        'unsupported_tensor_type:registered': True, 'unsupported_tensor_type:profile': 'SUPPORTED_FOR_TRIAL',
        'unsupported_tensor_type:submit': 'MODEL_QUANTIZATION_NOT_IN_INSPECTION_PROFILE',
        'unsupported_tensor_type:rejected_by': 'local_brain:configuration', 'type_label': ['UNSUPPORTED_TYPE_39'],
        'no_chat_template:registered': True, 'no_chat_template:profile': 'SUPPORTED_FOR_TRIAL',
        'no_chat_template:submit': 'MODEL_CHAT_TEMPLATE_MISSING', 'no_chat_template:rejected_by': 'local_brain:configuration'}),
    _case('R05', 5, '60 GiB available: Auto cap 32,768 MiB (the ceiling), admitted', r05, {
        'estimate_bytes': ESTIMATE, 'cap_mb': 32768, 'submit': 'ACCEPTED', 'frozen_memory_mb': 32768, 'admitted': True,
        'headroom_gib': 58.0, 'requested_mib': 32768, 'reserve_mib': 2048}, inputs={'available_gib': 60}),
    _case('R06', 6, '40 GiB available: Auto cap 26,624 MiB (65% of available), admitted; admission asks for 30,109 MiB, '
                    'the estimate with Auto\'s 4,096 MiB headroom, which stays with the budget after submit', r06, {
        'estimate_bytes': ESTIMATE, 'cap_mb': 26624, 'submit': 'ACCEPTED', 'frozen_memory_mb': 26624, 'admitted': True,
        'headroom_gib': 38.0, 'requested_mib': 30109, 'reserve_mib': 2048}, inputs={'available_gib': 40}),
    _case('R07', 7, '39 GiB available: Auto accepts at the estimate (26,013 MiB), and a manual cap is admitted', r07, {
        'estimate_bytes': ESTIMATE, 'auto_cap_mb': 26013, 'auto_submit': 'ACCEPTED', 'auto_frozen_memory_mb': 26013,
        'auto_admitted': True, 'auto_headroom_gib': 37.0,
        'manual_26100_submit': 'ACCEPTED', 'manual_admitted': True, 'manual_headroom_gib': 37.0},
        inputs={'available_gib': 39, 'manual_memory_mb': 26100}),
    _case('R08', 8, '30 GiB available: Auto refuses with its numbers (it needs 31.40 GiB); a manual cap that fits is '
                    'accepted, one that does not is refused', r08, {
        'auto_submit': 'MODEL_MEMORY_BUDGET_TOO_SMALL',
        'auto_refusal': 'MODEL_MEMORY_BUDGET_TOO_SMALL: Auto needs 32,157 MiB available for this model at 4,096 tokens '
                        '(its 26,013 MiB estimate, the 2,048 MiB foreground reserve and 4,096 MiB headroom); '
                        '30,720 MiB is available',
        'auto_at_32157_mib': 'ACCEPTED', 'auto_at_32156_mib': 'MODEL_MEMORY_BUDGET_TOO_SMALL',
        'manual_26100_submit': 'ACCEPTED', 'manual_29000_submit': 'MEMORY_BUDGET_EXCEEDS_AVAILABLE_HOST_RAM',
        'manual_29000_refusal': {'contains': 'the 29,000 MiB cap and the 2,048 MiB foreground reserve need 31,048 MiB; '
                                             '30,720 MiB is available'}},
        inputs={'available_gib': 30, 'manual_memory_mb': [26100, 29000], 'auto_boundary_mib': [32157, 32156]}),
    _case('R09', 9, 'Unavailable RAM reading at submit and after submit: the full reserve, and a 30 s deadline', r09, {
        'submit_unmeasured': 'HOST_MEMORY_COULD_NOT_BE_MEASURED', 'admitted_unmeasured': False,
        'wait_reason': 'Host memory could not be measured', 'wait_saved': 'Host memory could not be measured',
        'state': 'Queued', 'deadline:admitted': False, 'deadline:state': 'Failed',
        'deadline:error': {'startswith': 'HOST_MEMORY_COULD_NOT_BE_MEASURED: available memory could not be read for '
                                         '30 s'},
        'deadline:waited_s': {'between': [30, 31]}, 'reserve_mib_without_total': 2048},
        faults=[{'at': 'after submit', 'fault': 'available RAM reading becomes None'}]),
    _case('R10', 10, 'Too-small manual cap at 60 GiB, refused with its numbers', r10, {
        'submit': 'MODEL_MEMORY_BUDGET_TOO_SMALL',
        'refusal': 'MODEL_MEMORY_BUDGET_TOO_SMALL: the 16,384 MiB cap is below this model\'s 26,013 MiB estimate at '
                   '4,096 tokens',
        'rejected_by': 'local_brain:configuration'},
        inputs={'available_gib': 60, 'manual_memory_mb': 16384}),
    _case('R11', 11, 'Reserve and outstanding commitments are counted once', r11, {
        'available_gib': 40.0, 'reserve_gib': 2.0, 'future_gib': 8.0, 'headroom_gib': 30.0,
        'commitments': ['job', 'model']},
        inputs={'available_gib': 40, 'running_io_job': {'budget_gib': 10, 'rss_gib': 2},
                'resident_model': {'memory_mb': 8192, 'rss_gib': 8, 'listed_in': ['worker', 'trial_worker']}}),
    _case('R12', 12, 'Queued 32 GiB request, idle queue, 34 GiB: admitted', r12, {
        'admitted': True, 'headroom_gib': 32.0, 'requested_gib': 32.0}, inputs={'available_gib': 34, 'request_gib': 32}),
    _case('R13', 13, 'Same request at 33 GiB waits for headroom', r13, {
        'admitted': False, 'reason': 'Waiting for shared-memory headroom',
        'wait_saved': 'Waiting for shared-memory headroom', 'headroom_gib': 31.0},
        inputs={'available_gib': 33, 'request_gib': 32}),
    _case('R14', 14, '40 GiB with another job reserving 8 GiB of future growth', r14, {
        'io_other:admitted': False, 'io_other:reason': 'Waiting for shared-memory headroom',
        'io_other:future_gib': 8.0, 'io_other:headroom_gib': 30.0,
        'compute_other:reason': 'CPU calculation slots are occupied'},
        inputs={'available_gib': 40, 'request_gib': 32, 'other_job': {'budget_gib': 10, 'rss_gib': 2}}),
    _case('R15', 15, 'A 32 GiB model activation admitted at 34 GiB loads (one rule for admission and launch); '
                     '1 MiB short, it waits at admission', r15, {
        'submit_at_40': 'ACCEPTED', 'admitted_at_34': True, 'admission_headroom_gib': 32.0,
        'run_reason': 'ACTIVATED', 'workers_started': 1, 'state': 'READY',
        'one_mib_short:admitted': False, 'one_mib_short:reason': 'Waiting for shared-memory headroom',
        'owned_workers_left': []},
        faults=[{'at': 'after submit', 'fault': 'available RAM 40 -> 34 GiB'},
                {'at': 'after the second submit', 'fault': 'available RAM 34 GiB less 1 MiB'}]),
    _case('R16', 16, 'Background request deferred by the memory forecast, then admitted', r16, {
        'first_reason': 'Foreground interaction has the next turn', 'forecast_deferred': True, 'admitted': True,
        'forecast_outcome': 'wait_budget_elapsed', 'deferred_seconds': {'between': [7.6, 8.8]}},
        faults=[{'at': '0-2 s', 'fault': 'foreground lease; available RAM falls 0.5 GiB/s then holds'}],
        inputs={'request_gib': 6.95, 'priority': 'background'}),
    _case('R17', 17, 'Accessible Radeon: Vulkan with 41 offloaded layers (simulated)', r17, {
        'result': 'ACTIVATED', 'state': 'READY', 'requested_backend': 'AUTO', 'effective_backend': 'VULKAN',
        'observed_gpu_layers': 41,
        'offload_evidence': 'SIMULATED_WORKER_LOAD_LOG: offloaded 41/41 layers to GPU (fixture runtime, not a GPU)',
        'offload_evidence_marks_simulated': True,
        'offload_label': {'startswith': 'SIMULATED: 41 layers'}, 'argv_ngl': 'auto', 'argv_fit': 'on',
        'argv_device': 'Vulkan0', 'probe_state': 'AVAILABLE', 'probe_device': 'AMD Radeon 680M (RADV REMBRANDT)',
        'owned_workers_left': []},
        inputs={'devices': 'radeon', 'graphics': 'accessible'}),
    _case('R18', 18, 'Missing, inaccessible or software Vulkan; zero or missing offload', r18, {
        'inaccessible:backend': 'CPU', 'inaccessible:reason': {'startswith': 'Auto selected CPU'},
        'missing:backend': 'CPU', 'software:probe_state': 'NO_PHYSICAL_VULKAN_DEVICE',
        'software:effective_backend': 'CPU', 'software:fallback_reason': {'startswith': 'Vulkan device discovery'},
        'software_no_fallback:reason': 'VULKAN_UNAVAILABLE', 'software_no_fallback:workers_started': 0,
        'zero_offload:backends_tried': ['VULKAN', 'CPU'], 'zero_offload:effective_backend': 'CPU',
        'zero_offload:fallback_reason': {'contains': 'VULKAN_GPU_OFFLOAD_NOT_OBSERVED'},
        'missing_offload:backends_tried': ['VULKAN', 'CPU'], 'missing_offload:effective_backend': 'CPU',
        'missing_offload:fallback_reason': {'contains': 'VULKAN_GPU_OFFLOAD_NOT_OBSERVED'},
        'owned_workers_left': []}),
    _case('R19', 19, 'Launch timeout, driver failure, empty reply, smaller context refused, failed handover; Ready '
                     'needs a valid reply', r19, {
        'timeout:backends_tried': ['VULKAN', 'CPU'], 'timeout:reason': 'MODEL_LOAD_TIMEOUT',
        'timeout:simulated_seconds_at_least_180': True,
        'driver_exit:backends_tried': ['VULKAN', 'CPU'], 'driver_exit:effective_backend': 'CPU',
        'driver_exit:fallback_reason': {'startswith': 'Vulkan load: MODEL_WORKER_EXITED_DURING_LOAD'},
        'empty_reply:backends_tried': ['VULKAN'], 'empty_reply:reason': 'MODEL_PROBE_RETURNED_NO_TEXT',
        'empty_reply:state': 'MODEL_STOPPED',
        'http_500:backends_tried': ['VULKAN', 'CPU'], 'http_500:qualification': 'CPU_CHAT_QUALIFIED',
        'small_context:backends_tried': ['CPU'], 'small_context:reason': 'MODEL_CONTEXT_BELOW_SELECTION',
        'small_context:state': 'MODEL_STOPPED', 'small_context:selection_context': 4096,
        'small_context_vulkan:backends_tried': ['VULKAN', 'CPU'], 'small_context_vulkan:state': 'READY',
        'small_context_vulkan:worker_context': 4096,
        'small_context_vulkan:fallback_reason': {'startswith': 'Vulkan load: MODEL_CONTEXT_BELOW_SELECTION'},
        'handover:reason': 'MODEL_WORKER_EXITED_DURING_LOAD', 'handover:workers_started': 2,
        'handover:restored_previous': True, 'handover:state': 'READY',
        'handover_empty_restore:reason': 'MODEL_WORKER_EXITED_DURING_LOAD', 'handover_empty_restore:workers_started': 2,
        'handover_empty_restore:restored_previous': False, 'handover_empty_restore:state': 'MODEL_STOPPED',
        'owned_workers_left': []}),
    _case('R20', 20, 'Low RAM during load and during work; launch shortfall; the memory stop stays visible', r20, {
        'load:reason': 'GRAPHITE_HOST_MEMORY_LIMIT', 'load:workers_started': 1, 'load:previous_restored': False,
        'load:selection_kept': True, 'load:previous_qualification_kept': 'CPU_CHAT_QUALIFIED',
        'load:status_resource_stop': {'startswith': 'Stopped to preserve shared host memory'},
        'launch:reason': 'GRAPHITE_HOST_MEMORY_LIMIT', 'launch:rejected_by': 'resource_control:model_room',
        'launch:workers_started': 0,
        'launch:status_resource_stop': {'startswith': 'Stopped to preserve shared host memory'},
        'reload:state': 'READY', 'reload:status_resource_stop': None,
        'work:supervisor_exit': 75, 'work:marker': True, 'work:stopped_within_s': True,
        'cgroup:admission_available_gib': 20.0, 'cgroup:guard_available_gib': 20.0,
        'owned_workers_left': []}),
    _case('R21', 0, 'Resume: killed after a durable write, resumed from its own checkpoint', r21, {
        'resumed_from': 'step1', 'revision_matches_checkpoint': True, 'blind_rewrite_refused': True,
        'step1_writes': 1, 'step2_writes': 1, 'context_now': 4096, 'threads_now': 6},
        start={'workspace': 'empty Office', 'phase': 'first, then resume in the same workspace'},
        allowed=['ledger.settings', 'ledger.settings.set', 'ledger.settings.history'],
        faults=[{'at': 'after checkpoint step1', 'fault': 'attempt process killed (SIGKILL)'}],
        resume={'kill_after': 'step1'}, budget=40),
    _case('R22', 0, 'Stop while queued and running; foreground turn; a work hold holds queued work, which continues '
                    'on release with completed writes once', r22, {
        'queued_cancel:state': 'Cancelled', 'loading_cancel:reason': 'MODEL_OPERATION_CANCELLED',
        'loading_cancel:workers_started': 1, 'loading_cancel:workers_left': [],
        'running_stop:reason': 'MODEL_OPERATION_CANCELLED', 'running_stop:workers_started': 1,
        'running_stop:state': 'MODEL_STOPPED', 'foreground:reason': 'Foreground interaction has the next turn',
        'hold:state': 'Queued', 'hold:error': None,
        'hold:reason': 'Work is held: waiting for the owner to resume work', 'hold:load_state': 'Queued',
        'hold:workers_started': 0,
        'release:jobs_replayed': 0, 'release:jobs_continuing': 2, 'release:load': 'ACTIVATED',
        'release:load_claimed_again': False, 'release:workers_started': 1, 'release:state': 'Running',
        'writes:previous_activated': 1, 'writes:held_load_activated': 1, 'owned_workers_left': []},
        faults=[{'at': 'during the case', 'fault': 'owner holds work while two background requests are queued, then '
                                                   'releases the hold'}]),
]
