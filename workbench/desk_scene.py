"""Scenes: scripts of desk acts, run on the live window, each step checked against what the window then reads back.

A scene (graphite.scene/1, a JSON file) names its seed, what the window is given (its size, the appearance, the dial of
Stacy's hand), the runs it is played in (by pointer, by keys, either with less motion), and its steps. Each step is one act
with its arguments and what is expected after it: dotted paths into {"act": the act's envelope, "desk": read.desk all,
taken after the step}, each with a value or a matcher (equal, contains, startswith, in, decimal, gte, lte, between, not;
the same forms and the same answers as the campaign's core.matches). expect_by_run and expect_by_seed add or replace
expectations for one run or one seed.

run_scene() plays one run: it checks the appearance (chosen at start, so a scene for another appearance is blocked, not
failed), sizes the window, sets the dial and the motion, runs each step through desk_doers.run(door='script'), scores it,
and puts the window back as it found it (menus closed, motion as it was). A step that waits for Approve, or that would open
a window that asks, fails unless the scene expects it: an ask the scene did not declare is a finding, not a pass.

Nothing here reaches into a widget: every step is an act, and every check reads what read.desk reads.
"""
import decimal
import fractions
import json
import time
from pathlib import Path

from . import desk_acts

SCHEMA = 'graphite.scene/1'
STYLES = ('pointer', 'keys')
FORMS = ('contains', 'startswith', 'in', 'decimal', 'gte', 'lte', 'between', 'not')
NOT_OBSERVED = '<not observed>'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def matches(want, got):
    """A declared expectation against an observation: tools/campaign_lib/core.matches, the same forms with the same answers."""
    if isinstance(want, dict) and len(want) == 1:
        (form, arg), = want.items()
        if form == 'contains':
            return got is not None and str(arg) in str(got)
        if form == 'startswith':
            return isinstance(got, str) and got.startswith(arg)
        if form == 'in':
            return got in arg
        if form == 'decimal':
            try:
                return fractions.Fraction(str(got)) == fractions.Fraction(decimal.Decimal(str(arg)))
            except (ValueError, ZeroDivisionError, decimal.InvalidOperation):
                return False
        if form == 'gte':
            return isinstance(got, (int, float)) and got >= arg
        if form == 'lte':
            return isinstance(got, (int, float)) and got <= arg
        if form == 'between':
            return isinstance(got, (int, float)) and arg[0] <= got <= arg[1]
        if form == 'not':
            return got != NOT_OBSERVED and not matches(arg, got)
    return want == got


def lookup(tree, path):
    """A dotted path into nested dicts (and lists, by number); NOT_OBSERVED when it is not there. A path may end in #word to
    hold a second expectation on the same place (JSON keeps one value per key)."""
    at = tree
    for part in str(path).split('#', 1)[0].split('.'):
        if isinstance(at, dict) and part in at:at = at[part]
        elif isinstance(at, list) and part.isdigit() and int(part) < len(at):at = at[int(part)]
        else:return NOT_OBSERVED
    return at


def check_scene(scene):
    """What is wrong with a scene, in words ([] when nothing): its schema, its runs, and each step's act and arguments."""
    problems = []
    if not isinstance(scene, dict):return ['a scene is a JSON object']
    if scene.get('schema') != SCHEMA:problems.append('schema is not %s' % SCHEMA)
    if not isinstance(scene.get('id'), str) or not scene.get('id'):problems.append('the scene has no id')
    runs = scene.get('runs')
    if not isinstance(runs, list) or not runs:problems.append('the scene has no runs')
    else:
        names = [r.get('name') for r in runs if isinstance(r, dict)]
        if len(set(names)) != len(runs):problems.append('two runs share a name, or a run has none')
        for r in runs:
            if not isinstance(r, dict) or r.get('style') not in STYLES:problems.append('run %r has no style (pointer or keys)' % (r.get('name') if isinstance(r, dict) else r))
    given = scene.get('given', {})
    if not isinstance(given, dict):problems.append('given is not an object')
    steps = scene.get('steps')
    if not isinstance(steps, list) or not steps:problems.append('the scene has no steps');steps = []
    for n, step in enumerate(steps, 1):
        if not isinstance(step, dict):problems.append('step %d is not an object' % n);continue
        act = step.get('act')
        if act not in desk_acts.ACTS:problems.append('step %d: no act named %r' % (n, act));continue
        try:desk_acts.check(act, step.get('args', {}))
        except desk_acts.Refusal as refusal:problems.append('step %d: %s' % (n, refusal.words))
        for key in ('expect',):
            if not isinstance(step.get(key, {}), dict):problems.append('step %d: %s is not an object' % (n, key))
        for key in ('expect_by_run', 'expect_by_seed'):
            value = step.get(key, {})
            if not isinstance(value, dict) or not all(isinstance(v, dict) for v in value.values()):problems.append('step %d: %s is not an object of objects' % (n, key))
        for path in list(step.get('expect', {})) + [p for v in step.get('expect_by_run', {}).values() for p in v] + [p for v in step.get('expect_by_seed', {}).values() for p in v]:
            if not str(path).startswith(('act.', 'desk.')):problems.append('step %d: %r reads neither act. nor desk.' % (n, path))
    return problems


def expected(step, run_name, seed):
    want = dict(step.get('expect') or {})
    want.update((step.get('expect_by_run') or {}).get(run_name) or {})
    want.update((step.get('expect_by_seed') or {}).get(seed) or {})
    return want


def run_scene(host, scene, run, *, seed, origin, after_step=None):
    """Play one run of a scene on the live window. `run` is a run's name or the run itself. Returns {run, seed, steps: [{n,
    act, ok, by, seconds, words, checks: [{path, want, got, ok}]}], passed} or {blocked: why}."""
    from . import boss_theme, desk_doers
    if isinstance(run, str):run = next((r for r in scene['runs'] if r['name'] == run), None)
    if run is None:return {'blocked': 'the scene has no such run'}
    given = scene.get('given') or {}
    if given.get('appearance') and given['appearance'] != boss_theme.APPEARANCE:
        return {'blocked': 'the appearance is chosen at start', 'run': run['name'], 'seed': seed}
    style = run['style']
    if given.get('size'):host.resize(*given['size'])
    host.show();host.raise_();host.activateWindow();desk_doers.settle(host, 40, 4)
    if given.get('dial'):desk_doers.run(host, 'hand.dial', {'place': given['dial']}, door='script', origin=origin)
    before_motion = None
    if run.get('reduce_motion'):
        changed = desk_doers.run(host, 'look.set', {'motion': 'reduced'}, door='script', origin=origin)
        before_motion = ((changed.get('result') or {}).get('before') or {}).get('motion', 'normal')
    out = {'run': run['name'], 'seed': seed, 'style': style, 'reduce_motion': bool(run.get('reduce_motion')), 'steps': []}
    try:
        for n, step in enumerate(scene['steps'], 1):
            started = time.monotonic();checks = []
            try:
                envelope = desk_doers.run(host, step['act'], step.get('args', {}), door='script', by=style, origin=origin,
                                          word='scene %s step %d' % (scene.get('id', ''), n))
                desk = desk_doers.read_desk(host, 'all')
                tree = {'act': envelope, 'desk': desk}
                want = expected(step, run['name'], seed)
                for path, value in want.items():
                    got = lookup(tree, path);checks.append({'path': path, 'want': value, 'got': got, 'ok': matches(value, got)})
                result = envelope.get('result') if isinstance(envelope.get('result'), dict) else {}
                if result.get('waits') and 'act.result.waits' not in want:      # an ask the scene did not declare
                    checks.append({'path': 'act.result.waits', 'want': False, 'got': True, 'ok': False})
                if not envelope.get('ok') and 'act.ok' not in want and 'act.error.code' not in want:
                    checks.append({'path': 'act.ok', 'want': True, 'got': False, 'ok': False, 'why': envelope.get('words')})
            except Exception as exc:  # noqa: BLE001 - a step that breaks is a failed step with its message, and the run goes on
                envelope = {'ok': False, 'by': None, 'words': '%s: %s' % (type(exc).__name__, exc)}
                checks.append({'path': 'step', 'want': 'no exception', 'got': envelope['words'], 'ok': False})
            row = {'n': n, 'act': step['act'], 'args': step.get('args', {}), 'ok': all(c['ok'] for c in checks) if checks else bool(envelope.get('ok')),
                   'done': bool(envelope.get('ok')), 'by': envelope.get('by'), 'words': envelope.get('words'), 'seconds': round(time.monotonic() - started, 3), 'checks': checks,
                   'result': envelope.get('result')}
            out['steps'].append(row)
            if after_step is not None:
                try:after_step(n, step, row)
                except Exception:  # noqa: BLE001 - a watcher's trouble is not the scene's
                    pass
    finally:
        try:desk_doers.run(host, 'menu.close', {}, door='script', origin=origin)
        except Exception:  # noqa: BLE001
            pass
        if before_motion is not None:
            desk_doers.run(host, 'look.set', {'motion': before_motion}, door='script', origin=origin)
    out['passed'] = bool(out['steps']) and all(s['ok'] for s in out['steps'])
    return out


def failures(out):
    """The checks a run missed, as (step, check) pairs, for a message."""
    return [(s['n'], c) for s in out.get('steps', []) for c in s['checks'] if not c['ok']]
