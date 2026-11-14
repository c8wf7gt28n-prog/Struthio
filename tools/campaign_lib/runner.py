"""Running cases: one child process per attempt, killed at its budget, with a manifest and per-attempt results.

The parent never imports Graphite's workspace code. For each attempt it first checks what the case needs from the
machine (needs.py): an attempt whose needs are not met, or whose steps are not written yet, is Blocked with the
reason, decided now and never written into the case. Otherwise it makes a fresh folder, starts
`campaign.py --child <folder>` in its own process group with an isolated environment (fixture.py), and waits for
the case's time budget. A child that runs over is killed (SIGTERM, then SIGKILL); its progress.jsonl and
checkpoint.json stay, and the parent writes a Timeout result naming the last durable step. A case that raises is a
Fail with the error, whatever checks it met before.

A resume case runs twice in the same folder: the first child is killed as soon as its checkpoint names the step the
case declares, and a second child (phase "resume") continues from that checkpoint. The seed record the first child
wrote (fixture.json) is kept in the result.

A run counts only itself: `run` into a folder that holds an earlier run first moves that run aside, whole, into
previous-<n>/, and the summary reads only the cases and attempts this run's MANIFEST.json lists.

Real mode (--mode real) only checks prerequisites and prints the plan it would run on the ThinkPad.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

from . import cases_anchor, cases_resource, cases_scene, fixture, gguf_fixture, needs
from .core import Attempt, Case, _plain, library_digest, score

CAMPAIGN = fixture.REPO / 'tools' / 'campaign.py'
SETS = ('resource', 'anchors', 'selftest', 'real', 'scenes')      # scenes: desk acts played on a live window (cases_scene)
REAL_MIN_AVAILABLE = needs.REAL_MIN_AVAILABLE
PREVIOUS = re.compile(r'previous-(\d+)')


# ---------------------------------------------------------------- the selftest and real-mode declarations

def _overrun(ctx):
    ctx.checkpoint('started', note='this case runs past its budget on purpose')
    ctx.observe('started', True)
    time.sleep(120)


def _breaks(ctx):
    ctx.observe('first', True)
    raise RuntimeError('this case breaks on purpose after meeting its first check')


SELFTEST = [
    Case(id='T01', set='selftest', title='Timeout: a case that overruns its budget is killed, partial result kept',
         seed='none', budget_s=3, expect={'started': True, 'finished': True}, fn=_overrun,
         faults=[{'at': 'start', 'fault': 'case sleeps 120 s against a 3 s budget'}]),
    Case(id='T02', set='selftest', title='A case that raises after meeting a check is a Fail, with the error',
         seed='none', budget_s=10, expect={'first': True, 'second': True}, fn=_breaks,
         faults=[{'at': 'after the first check', 'fault': 'the case raises RuntimeError'}]),
    Case(id='T03', set='selftest', title='R17\'s steps and checks on software Vulkan (llvmpipe): must not pass',
         seed='base', budget_s=60, fn=cases_resource.r17,
         expect=dict(next(c for c in cases_resource.CASES if c.id == 'R17').expect),
         inputs={'devices': 'llvmpipe', 'graphics': 'accessible'},
         faults=[{'at': 'start', 'fault': 'the only Vulkan device is llvmpipe; Auto falls back to CPU'}]),
]
REAL = [
    Case(id='M01', set='real', mode='real', seed='base', budget_s=900,
         title='Exact 35B on CPU: register, load and first reply (8 threads, 4,096 context, Auto memory)',
         inputs={'backend': 'CPU', 'threads': 8, 'context': 4096, 'memory': 'Auto',
                 'message': 'Reply with the word ready.'},
         allowed=['brain.model.add', 'brain.model.use', 'brain.ask', 'brain.status', 'brain.stop'],
         expect={'registered_sha256': gguf_fixture.OWNER_FILE['sha256'], 'state': 'READY', 'reply_nonempty': True}),
    Case(id='M02', set='real', mode='real', seed='base', budget_s=1200,
         title='Exact 35B on Vulkan Auto-fit: load, offload count, first reply',
         inputs={'backend': 'AUTO', 'threads': 8, 'context': 4096, 'memory': 'Auto', 'gpu_layers': -1},
         allowed=['brain.model.add', 'brain.model.use', 'brain.ask', 'brain.status', 'brain.stop'],
         expect={'effective_backend': 'VULKAN', 'observed_gpu_layers': {'gte': 1}, 'state': 'READY'}),
]


def registry():
    cases = cases_resource.CASES + cases_anchor.CASES + SELFTEST + REAL + cases_scene.CASES
    return {c.id: c for c in cases}


def select(set_name=None, ids=None):
    every = registry()
    if ids:
        missing = [i for i in ids if i not in every]
        if missing:
            raise SystemExit('Unknown case id: ' + ', '.join(missing))
        return [every[i] for i in ids]
    if set_name in (None, 'all'):
        return [c for c in every.values() if c.set in ('resource', 'anchors')]
    if set_name not in SETS:
        raise SystemExit('Unknown set: %s (choose resource, anchors, all, selftest, real or scenes)' % set_name)
    return [c for c in every.values() if c.set == set_name]


# ---------------------------------------------------------------- the child: one attempt, inside its own folder

def child_main(folder):
    folder = Path(folder)
    spec = json.loads((folder / 'spec.json').read_text())
    case = registry()[spec['case']]
    ctx = Attempt(case, folder, spec['attempt'], spec['phase'])
    ctx.backup = spec.get('backup')
    result = dict(case_id=case.id, attempt=spec['attempt'], phase=spec['phase'], pid=os.getpid())
    error = None
    try:
        ctx.progress('start', case=case.id)
        result['isolation'] = fixture.check_isolation(folder)
        ctx.models.mkdir(exist_ok=True)
        if spec['phase'] == 'resume':
            from workbench.engineering_kernel import Kernel, operator
            ctx.kernel, ctx.owner = Kernel(folder / 'ws'), operator()
            seeded = folder / 'fixture.json'
            record = json.loads(seeded.read_text()) if seeded.is_file() else {'seed': case.seed, 'state': 'NOT_RECORDED'}
            result['fixture'] = dict(record, resumed='reopened from the same attempt folder')
        else:
            if case.seed == 'base':
                ctx.kernel, ctx.owner = fixture.base_workspace(folder)
                digest, picture = fixture.state_digest(ctx.kernel)
                record = {'seed': 'base', 'revision': fixture.FIXTURE_REVISION, 'initial_state_sha256': digest,
                          'tables': len(picture['counts'])}
            elif case.seed == 'after_hours_07':
                ctx.kernel, ctx.owner, info = fixture.ah07_workspace(folder, ctx.backup)
                digest, picture = fixture.state_digest(ctx.kernel)
                record = {'seed': 'after_hours_07', 'backup_json_sha256': spec.get('backup_json_sha256'),
                          'initial_state_sha256': digest, **info}
            else:
                record = {'seed': 'none'}
            _write(folder / 'fixture.json', record)        # durable: a resumed phase keeps it
            result['fixture'] = record
        ctx.progress('seeded', seed=case.seed)
        case.fn(ctx)
        outcome, checks = score(case, ctx.observed)
        reason = 'all declared checks met' if outcome == 'Pass' else _first_miss(checks, outcome)
    except fixture.Blocked as blocked:
        outcome, checks, reason = 'Blocked', [], str(blocked)
    except Exception as exc:  # noqa: BLE001 - a case that raises is a Fail, whatever it met before
        error = traceback.format_exc(limit=8)
        checks = score(case, ctx.observed)[1]
        outcome = 'Fail'
        reason = 'case broke after %d of %d checks met: %s: %s' % (
            sum(c['ok'] for c in checks), len(checks), type(exc).__name__, str(exc)[:300])
    result.update(outcome=outcome, reason=reason, checks=checks, notes=ctx.notes, injected_faults=ctx.faults,
                  spec_question=ctx.spec_question, spec_conflict=case.spec_conflict, error=error,
                  child_seconds=round(time.monotonic() - ctx.t0, 3))
    _write(folder / 'child_result.json', result)
    ctx.progress('end', outcome=outcome)
    return 0


def _first_miss(checks, outcome=None):
    against = [c for c in checks if 'meets_spec' in c and not c['meets_spec']]
    if outcome and outcome.startswith('Pass') and against:
        return 'all declared checks met on current code; %d against the quoted spec line, first: %s observed %s' % (
            len(against), against[0]['check'], json.dumps(against[0]['observed'])[:80])
    missed = [c for c in checks if not c['ok']]
    if not missed:
        return 'no checks declared'
    c = missed[0]
    return '%d of %d checks missed; first: %s expected %s, observed %s' % (
        len(missed), len(checks), c['check'], json.dumps(c['expected'])[:80], json.dumps(c['observed'])[:120])


def _write(path, data):
    temporary = Path(str(path) + '.part')
    temporary.write_text(json.dumps(_plain(data), indent=1, ensure_ascii=False))
    os.replace(temporary, path)


# ---------------------------------------------------------------- the parent: attempts, timeouts, resume

def _progress(folder):
    path = Path(folder) / 'progress.jsonl'
    if not path.is_file():
        return []
    lines = []
    for raw in path.read_text().splitlines():
        try:
            lines.append(json.loads(raw))
        except ValueError:
            pass
    return lines


def _last_durable(lines):
    durable = [l for l in lines if l.get('step') in ('checkpoint', 'op', 'seeded', 'observe')]
    return durable[-1] if durable else None


def _kill(proc):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=2)
            return
        except subprocess.TimeoutExpired:
            continue


def _spawn(folder, case, number, phase, backup, budget):
    spec = dict(case=case.id, attempt=number, phase=phase, backup=str(backup) if backup else None,
                backup_json_sha256=fixture.file_sha(Path(backup) / 'BACKUP.json') if backup else None)
    _write(folder / 'spec.json', spec)
    env = fixture.attempt_environment(folder)
    with (folder / ('child-%s.log' % phase)).open('ab') as log:
        proc = subprocess.Popen([sys.executable, '-B', str(CAMPAIGN), '--child', str(folder)], cwd=folder, env=env,
                                stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    began = time.monotonic()
    kill_after = (case.resume or {}).get('kill_after') if phase == 'first' else None
    killed_at_checkpoint = timed_out = False
    while proc.poll() is None:
        if kill_after:
            try:
                saved = json.loads((folder / 'checkpoint.json').read_text())
            except (OSError, ValueError):
                saved = None
            if saved and saved.get('step') == kill_after:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                killed_at_checkpoint = True
                break
        if time.monotonic() - began > budget:
            _kill(proc)
            timed_out = True
            break
        time.sleep(0.05)
    return dict(phase=phase, returncode=proc.returncode, seconds=round(time.monotonic() - began, 3),
                killed_at_checkpoint=killed_at_checkpoint, timed_out=timed_out)


def run_attempt(run_dir, case, number, backup, probe=None, library=None):
    folder = Path(run_dir) / 'cases' / case.id / ('attempt-%d' % number)
    if folder.exists():
        shutil.rmtree(folder)            # reset: an attempt never reuses an earlier one's state
    folder.mkdir(parents=True)
    started_wall, started = time.time(), time.monotonic()
    probe = probe or needs.Probe(backup=backup)
    blocked, checked = needs.decide(case, probe)
    base = dict(case_id=case.id, set=case.set, situation=case.situation, title=case.title, attempt=number,
                case_revision=case.revision(library), mode=case.mode, budget_s=case.budget_s,
                started_wall=datetime.datetime.fromtimestamp(started_wall).isoformat(timespec='seconds'),
                started_monotonic=round(started, 3), folder=str(folder), spec_question=case.spec_question,
                spec_conflict=case.spec_conflict, slice=case.slice, needs=checked)
    if blocked:
        result = dict(base, outcome='Blocked', reason=blocked, checks=[], injected_faults=[], phases=[],
                      last_durable_result=None, seconds=round(time.monotonic() - started, 3),
                      ended_wall=base['started_wall'])
        _write(folder / 'result.json', result)
        return result
    fixture.make_folders(folder)
    phases = [_spawn(folder, case, number, 'first', backup, case.budget_s)]
    if case.resume and phases[0]['killed_at_checkpoint']:
        remaining = max(5.0, case.budget_s - phases[0]['seconds'])
        phases.append(_spawn(folder, case, number, 'resume', backup, remaining))
    lines = _progress(folder)
    child = None
    if (folder / 'child_result.json').is_file():
        child = json.loads((folder / 'child_result.json').read_text())
    if phases[-1]['timed_out'] or child is None:
        observed = {l['check']: l.get('value') for l in lines if l.get('step') == 'observe'}
        outcome_checks = score(case, observed)[1]
        child = dict(outcome='Timeout' if phases[-1]['timed_out'] else 'Fail',
                     reason=('budget of %ss ran out; the attempt was killed' % case.budget_s) if phases[-1]['timed_out']
                     else 'the attempt process ended without a result (exit %s)' % phases[-1]['returncode'],
                     checks=outcome_checks, injected_faults=[l for l in lines if l.get('step') == 'fault'])
        if (folder / 'fixture.json').is_file():
            child['fixture'] = json.loads((folder / 'fixture.json').read_text())
    ended = time.monotonic()
    checkpoint = folder / 'checkpoint.json'
    result = dict(base, **{k: v for k, v in child.items() if k not in base or k in ('spec_question', 'spec_conflict')},
                  phases=phases, seconds=round(ended - started, 3), ended_monotonic=round(ended, 3),
                  ended_wall=datetime.datetime.fromtimestamp(time.time()).isoformat(timespec='seconds'),
                  last_durable_result=_last_durable(lines),
                  checkpoint=json.loads(checkpoint.read_text()) if checkpoint.is_file() else None)
    result['checks_met'] = sum(c['ok'] for c in result.get('checks', []))
    result['checks_total'] = len(result.get('checks', []))
    _write(folder / 'result.json', result)
    return result


def manifest(run_dir, cases, attempts, backup, args, probe=None, library=None):
    every_fault = [{'case': c.id, **f} for c in cases for f in c.faults]
    header = gguf_fixture.HEADER_JSON
    library = library or library_digest()
    probe = probe or needs.Probe(backup=backup)
    seeds = {'base': {'revision': fixture.FIXTURE_REVISION, 'builder_sha256': fixture.file_sha(Path(fixture.__file__))}}
    if backup:
        seeds['after_hours_07'] = {'backup': str(backup), 'backup_json_sha256': fixture.file_sha(Path(backup) / 'BACKUP.json'),
                                   'backup_tree_sha256': fixture.tree_hash(backup)}
    else:
        seeds['after_hours_07'] = {'backup': None, 'state': 'NOT_FOUND', 'looked_in': str(fixture.fixtures_dir(args.fixtures))}
    return {
        'schema': 'graphite.campaign-manifest/2', 'run': Path(run_dir).name,
        'created': datetime.datetime.now().isoformat(timespec='seconds'), 'command': sys.argv,
        'attempts_per_case': attempts,
        'build': fixture.build_identity(), 'runtime': fixture.runtime_identity(), 'host': fixture.host_summary(),
        'runner_library_sha256': library,
        'model': {'owner_file': gguf_fixture.OWNER_FILE, 'header_fixture': str(header.relative_to(fixture.REPO)),
                  'header_fixture_sha256': fixture.file_sha(header),
                  'identity_in_simulation': 'bounded SHA-256 of size + first 16 MiB + last 1 MiB (gguf_fixture.bounded_identity)'},
        'fixtures': seeds,
        'cases': [{'id': c.id, 'set': c.set, 'situation': c.situation, 'title': c.title, 'revision': c.revision(library),
                   'mode': c.mode, 'seed': c.seed, 'budget_s': c.budget_s, 'allowed': c.allowed, 'faults': c.faults,
                   'needs': needs.decide(c, probe)[1], 'steps_written': c.fn is not None, 'slice': c.slice,
                   'source_case': c.source_case, 'definition': c.data()} for c in cases],
        'fault_schedule': every_fault,
    }


RUN_ENTRIES = ('MANIFEST.json', 'results.jsonl', 'SUMMARY.md', 'cases', 'fixtures')    # what a run writes in its folder


def set_aside(run_dir):
    """Move an earlier run in `run_dir` into a new previous-<n>/: only a run's own entries, and only when the folder holds
    a run (its MANIFEST.json). A folder that holds anything else is refused, never moved (a verifier found that the first
    version moved whatever was there: with --out ~ it would have moved the home folder)."""
    run_dir = Path(run_dir)
    present = [p for p in run_dir.iterdir() if not PREVIOUS.fullmatch(p.name)]
    if not present:
        return None
    others = sorted(p.name for p in present if p.name not in RUN_ENTRIES)
    if not (run_dir / 'MANIFEST.json').is_file() or others:
        raise SystemExit('%s is not an empty folder or an earlier run (it holds %s). Choose a new or empty --out folder; '
                         'nothing was moved.' % (run_dir, ', '.join(others[:5]) or 'files that are not a run'))
    earlier = sorted(p for p in present if p.name in RUN_ENTRIES)
    taken = [int(PREVIOUS.fullmatch(p.name)[1]) for p in run_dir.iterdir() if PREVIOUS.fullmatch(p.name)]
    target = run_dir / ('previous-%d' % (max(taken, default=0) + 1))
    target.mkdir()
    for path in earlier:
        os.replace(path, target / path.name)
    return target


def run(args):
    from . import report
    cases = select(args.set, args.case)
    if any(c.mode == 'real' for c in cases) or args.mode == 'real':
        return real(args, [c for c in cases if c.mode == 'real'] or [registry()['M01']])
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    run_dir = Path(args.out).expanduser().absolute() if args.out else Path(tempfile.gettempdir()) / 'graphite-campaign' / stamp
    if fixture.REPO == run_dir or fixture.REPO in run_dir.parents:
        raise SystemExit('Choose an --out folder outside the program folder (%s).' % fixture.REPO)
    if run_dir in fixture.REPO.parents or run_dir in (Path.home().absolute(), Path(run_dir.anchor)):
        raise SystemExit('Choose an --out folder of its own: %s holds the program folder or is your home or the root.' % run_dir)
    fixtures = fixture.fixtures_dir(args.fixtures)
    if fixtures is not None and Path(fixtures).exists() and (Path(fixtures).absolute() == run_dir or run_dir in Path(fixtures).absolute().parents):
        raise SystemExit('Choose an --out folder that does not hold the fixtures folder (%s).' % fixtures)
    run_dir.mkdir(parents=True, exist_ok=True)
    moved = set_aside(run_dir)
    if moved:
        print('An earlier run in %s was moved aside to %s; this run counts only itself.' % (run_dir, moved.name), flush=True)
    backup = None
    if any('after_hours_07' in c.needs or c.seed == 'after_hours_07' for c in cases):
        backup = fixture.find_ah07(fixtures, run_dir / 'fixtures' / 'after_hours_07')
    probe = needs.Probe(fixtures=fixtures, workspace=getattr(args, 'workspace', None), backup=backup, mode='sim')
    library = library_digest()
    record = manifest(run_dir, cases, args.attempts, backup, args, probe, library)
    record['earlier_run_moved_to'] = moved.name if moved else None
    record['repo_ledger_before'] = fixture.repo_ledger_stamp()
    _write(run_dir / 'MANIFEST.json', record)
    results = []
    with (run_dir / 'results.jsonl').open('w') as stream:
        for case in cases:
            for number in range(1, args.attempts + 1):
                result = run_attempt(run_dir, case, number, backup, probe, library)
                results.append(result)
                stream.write(json.dumps(_plain(result), ensure_ascii=False) + '\n')
                stream.flush()
                print('%-4s attempt %d  %-8s %6.1fs  %s' % (case.id, number, result['outcome'], result['seconds'],
                                                          (result.get('reason') or '')[:90]), flush=True)
    record['repo_ledger_after'] = fixture.repo_ledger_stamp()
    record['repo_ledger_untouched'] = record['repo_ledger_before'] == record['repo_ledger_after']
    record['finished'] = datetime.datetime.now().isoformat(timespec='seconds')
    _write(run_dir / 'MANIFEST.json', record)
    text, line = report.summary(run_dir)
    print(line)
    print('Run folder: %s' % run_dir)
    return 0


# ---------------------------------------------------------------- real mode: the ThinkPad's prerequisites and plan

def _registered(workspace):
    """Models registered in a workspace, read from its kernel database without changing it."""
    return needs.registered(workspace)


def real(args, cases, memory=None):
    """Check the ThinkPad's prerequisites in order (file, size, architecture, RAM, then the full SHA-256) and print
    the plan. Refuses (exit 2) at the first missing prerequisite; never downloads anything.

    Available RAM is what this process can use: its cgroup's limit less its usage when there is one, else
    /proc/meminfo (fixture.memory, as workbench/brain_worker.memory_sample reads it)."""
    owner = gguf_fixture.OWNER_FILE
    problems, found = [], {}
    host = fixture.host_summary()
    mem = memory or fixture.memory()
    available = mem.get('available_bytes') or 0
    path = None
    if args.model:
        path = Path(args.model).expanduser().absolute()
        if not path.is_file():
            problems.append('The model file is not here: %s.' % path)
        else:
            from sdk.cli.arc1cli import gguf_inspect
            size = path.stat().st_size
            found = {'path': str(path), 'bytes': size}
            if size != owner['bytes']:
                problems.append('The file is %d bytes; the owner\'s file is %d bytes.' % (size, owner['bytes']))
            try:
                found['architecture'] = gguf_inspect.inspect(path)['architecture']
            except ValueError as error:
                problems.append('Graphite\'s inspector rejects the file: %s.' % error)
    elif args.workspace:
        matches = [m for m in _registered(args.workspace) if any(f.get('sha256') == owner['sha256'] for f in m.get('files', []))]
        if not matches:
            problems.append('No model registered in %s has the owner\'s SHA-256.' % args.workspace)
        else:
            found = {'model_id': matches[0]['id'], 'path': matches[0]['files'][0].get('path'), 'sha256': owner['sha256'],
                     'identity': 'REGISTERED_SHA256_MATCHES'}
    else:
        problems.append('The owner\'s model file is not here: give --model /path/to/%s, or --workspace with it registered.'
                        % owner['name'])
    if available < REAL_MIN_AVAILABLE:
        problems.append('Only %.1f GiB of RAM is available (%s); a real 35B run needs at least 24 GiB.'
                        % (available / 1024 ** 3, mem.get('basis')))
    if path is not None and not problems:
        if args.skip_hash:
            found['identity'] = 'SIZE_AND_ARCHITECTURE_ONLY (registration will hash it)'
        else:
            from sdk.cli.arc1cli import gguf_inspect
            print('Hashing %s to confirm it is the owner\'s file (1-3 minutes on the ThinkPad)...' % path.name, flush=True)
            found['sha256'] = gguf_inspect.identity(path)['sha256']
            found['identity'] = 'FULL_SHA256_MATCHES' if found['sha256'] == owner['sha256'] else 'DIFFERENT_FILE'
            if found['sha256'] != owner['sha256']:
                problems.append('The file\'s SHA-256 is %s, not the owner\'s file.' % found['sha256'])
    print('Real-model run (ThinkPad only). Cases: %s' % ', '.join(c.id for c in cases))
    print('Owner\'s file: %s, %d bytes, SHA-256 %s' % (owner['name'], owner['bytes'], owner['sha256']))
    print('Host: %s, %s logical CPUs, %.1f GiB available (%s)' % (host['cpu'], host['logical_cpus'],
                                                                 available / 1024 ** 3, mem.get('basis')))
    print('It would run, in a fresh disposable workspace and profile under --out:')
    for case in cases:
        options = {k: case.inputs[k] for k in ('context', 'threads', 'backend', 'gpu_layers') if k in case.inputs}
        print('  %s  %s' % (case.id, case.title))
        print('      1. brain.model.add {"path": "%s"}   (full SHA-256 check, 1-3 min)' % (found.get('path') or '<model path>'))
        print('      2. brain.model.use {"id": <registered id>, "options": %s}' % json.dumps(options))
        print('      3. the load probe "Reply with the word ready." then brain.ask {"message": "Reply with the word ready."}')
        print('      4. record load time, first-reply time, effective backend, offload count and peak RSS; brain.stop')
    if problems:
        print('REFUSED:')
        for problem in problems:
            print('  - ' + problem)
        print('Nothing was started and nothing was downloaded.')
        return 2
    print('Prerequisites met: %s' % json.dumps(found))
    print('The real-model execution is the next deliverable; nothing was started.')
    return 3
