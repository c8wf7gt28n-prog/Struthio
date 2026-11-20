"""Scenes: scripts of desk acts, run on the live window, each step checked against what the window then reads back.

A scene (graphite.scene/1, a JSON file) names its seed, what the window is given (its size, the appearance, the dial of
Stacy's hand), the runs it is played in (by pointer, by keys, either with less motion), and its steps. Each step is one act
with its arguments and what is expected after it: dotted paths into {"act": the act's envelope, "desk": read.desk all,
taken after the step}, each with a value or a matcher (equal, contains, startswith, in, decimal, gte, lte, between, not;
the same forms and the same answers as the campaign's core.matches). expect_by_run and expect_by_seed add or replace
expectations for one run or one seed; args_by_seed adds or replaces arguments for one seed.

A scene is written for one workspace (its seed) and names what is there: a file, a sheet, a row. `workspaces` lets the
same scene be played on another one: {workspace: {"names": {a name the scene uses: the name there}, "find": {a name the
scene uses: how to find the name there}, "title", "intent"}}. for_workspace() gives the scene as it is played there: the
same acts in the same order, each name swapped wherever it is said (an argument, an expectation), the seed set to that
workspace. "find" is for a workspace whose names the program must not hold: each name is found there when the scene is
played, by its kind and the words it says (find_names()), and what the window reads there can be said back in the scene's
own names (said_back()). run_scene() does all of this itself when its seed is a workspace the scene has an entry for.
0.8.5: P01 is written on Rail Demo, the invented workspace kept in the program (workbench/rail_demo.py), so it plays
anywhere; its "after_hours_07" entry finds its names in the owner's backup, which is never shipped, and names nothing of it.

run_scene() plays one run: it checks the appearance (chosen at start, so a scene for another appearance is blocked, not
failed), sizes the window, sets the dial and the motion, runs each step through desk_doers.run(door='script'), scores it,
and puts the window back as it found it (menus closed, motion as it was). A step that waits for Approve, or that would open
a window that asks, fails unless the scene expects it: an ask the scene did not declare is a finding, not a pass.

Nothing here reaches into a widget: every step is an act, and every check reads what read.desk reads.
"""
import copy
import decimal
import fractions
import json
import re
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


def for_workspace(scene, workspace, found=None):
    """The scene as it is played on another workspace (scene['workspaces'][workspace]): a copy with the same steps, every
    name of the scene swapped for the name there wherever a step says it, the longest name first and each place once; the
    seed, and the title and intent when given, are that workspace's. The scene's own seed gives the scene as written.
    `found` is what find_names() found there for an entry that says how to find its names ("find"); without it those names
    stay as the scene says them."""
    if workspace == scene.get('seed'):return copy.deepcopy(scene)
    there = (scene.get('workspaces') or {}).get(workspace)
    if not isinstance(there, dict):raise ValueError('The scene %s is not written for the workspace %r' % (scene.get('id', ''), workspace))
    if not _names(there.get('names', {})) or not _names(found or {}):
        raise ValueError('The scene %s, workspace %r: names is not an object of names' % (scene.get('id', ''), workspace))
    names = {**dict(there.get('names') or {}), **dict(found or {})}
    out = copy.deepcopy(scene)
    out['steps'] = _swapped(out.get('steps') or [], names)
    out['seed'] = workspace
    for key in ('title', 'intent'):
        if there.get(key):out[key] = there[key]
    return out


def said_back(value, found):
    """A value read on the workspace whose names were found (find_names), with each name found there put back as the scene
    says it: what the window read, in the scene's own words, so that a run is judged against the scene as written. A name
    the window read that was not found stays as it is."""
    return _swapped(value, {there: name for name, there in (found or {}).items()})


def _swapped(value, names):
    """The value with every name of `names` swapped for its own wherever a string says it, the longest name first and each
    place once; lists and objects are swapped through, their keys kept."""
    said = re.compile('|'.join(re.escape(name) for name in sorted(names, key=len, reverse=True))) if names else None

    def swap(value):
        if isinstance(value, str):return said.sub(lambda hit: names[hit.group(0)], value) if said else value
        if isinstance(value, list):return [swap(v) for v in value]
        if isinstance(value, dict):return {key: swap(v) for key, v in value.items()}
        return value
    return swap(value)


def _names(names):
    """Whether a workspace's names are what the swap can use: an object of name -> name, no name empty (an empty name
    would be found between every two letters)."""
    return isinstance(names, dict) and all(isinstance(k, str) and k and isinstance(v, str) for k, v in names.items())


FIND_KINDS = ('sheet', 'calculation', 'row')


def _find(find):
    """What is wrong with a workspace's "find" ([] when nothing): {a name the scene says: {"kind": sheet, calculation or row,
    "says": the words to look for, and for a row "of": the name of a sheet found by the same entry}}."""
    if not isinstance(find, dict):return ['find is not an object']
    problems = []
    for name, how in find.items():
        if not isinstance(how, dict) or how.get('kind') not in FIND_KINDS or not isinstance(how.get('says'), str) or not how['says'].strip():
            problems.append('%r is not found by a kind (%s) and the words it says' % (name, ', '.join(FIND_KINDS)));continue
        if how['kind'] == 'row' and (find.get(how.get('of')) or {}).get('kind') != 'sheet':
            problems.append('the row %r is not of a sheet the entry finds' % name)
    return problems


def find_names(kernel, principal, scene, workspace):
    """The names the scene's entry for `workspace` says to find there ("find"), found in that workspace by kind and by the
    words each says, capitals aside: {a name the scene says: the name there}, {} when the entry finds none. A sheet or a
    calculation is one on the desk (field.read; a calculation's name is its title before its result, "<name> · 3 W"); a
    row is a row of a sheet found here (its reviewed rows' parameter, office.get). Each must be found exactly once, or
    ValueError says which, in words: a sheet as one record (the scene points at it by its title, and its rows are read
    from it, so two sheets of one title are two), a calculation or a row as one name. Reads only. This is how a scene is played on a workspace whose names the program does
    not hold: P01 on the owner's After Hours 07, which is never shipped."""
    there = (scene.get('workspaces') or {}).get(workspace)
    find = there.get('find') if isinstance(there, dict) else None
    if not find:return {}
    head = 'The scene %s, workspace %r: ' % (scene.get('id', ''), workspace)
    problems = _find(find)
    if problems:raise ValueError(head + problems[0])

    def call(op, args):
        r = kernel.dispatch(op, args, principal)
        if not r.get('ok'):raise ValueError(head + 'the workspace could not be read (%s was refused)' % op)
        return r['result']
    objects = call('field.read', {}).get('objects') or []
    out, offices = {}, {}
    for name, how in sorted(find.items(), key=lambda item: item[1]['kind'] == 'row'):     # a row is found in a sheet found before it
        says = how['says'].strip().casefold()
        if how['kind'] == 'row':
            rows = (call('office.get', {'id': offices[how['of']]}).get('origin') or {}).get('reviewed_rows') or []
            there_names = sorted({str(row.get('parameter') or '') for row in rows if isinstance(row, dict) and says in str(row.get('parameter') or '').casefold()})
            what, whats = 'row of %s' % out[how['of']], 'rows of %s' % out[how['of']]
        else:
            hits = [o for o in objects if o.get('kind') == how['kind'] and says in str(o.get('title') or '').casefold()]
            if how['kind'] == 'sheet':there_names = [str(o['title']) for o in hits]       # one per record
            else:there_names = sorted({str(o['title']).split(' · ')[0] for o in hits})     # a calculation's name, before its result
            what, whats = how['kind'], how['kind'] + 's'
        if len(there_names) != 1:
            raise ValueError(head + ('no %s says "%s"' % (what, how['says']) if not there_names else
                                     '%d %s say "%s"' % (len(there_names), whats, how['says'])) + ' (for %s)' % name)
        if there_names[0] in out.values():      # two names found as one could not be told apart in what the window reads
            raise ValueError(head + '%s and %s are found as the same %s' % (next(k for k, v in out.items() if v == there_names[0]), name, what))
        if how['kind'] == 'sheet':offices[name] = str(hits[0]['id']).split(':', 1)[1]
        out[name] = there_names[0]
    return out


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
    workspaces = scene.get('workspaces', {})
    if not isinstance(workspaces, dict):problems.append('workspaces is not an object');workspaces = {}
    for name, there in workspaces.items():
        if not isinstance(there, dict) or not _names(there.get('names', {})):
            problems.append('workspace %r: names is not an object of names' % name)
        elif 'find' in there:
            problems.extend('workspace %r: %s' % (name, problem) for problem in _find(there['find']))
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
        for key in ('expect_by_run', 'expect_by_seed', 'args_by_seed'):
            value = step.get(key, {})
            if not isinstance(value, dict) or not all(isinstance(v, dict) for v in value.values()):
                problems.append('step %d: %s is not an object of objects' % (n, key));step = {**step, key: {}}
        for seed in step.get('args_by_seed', {}):
            try:desk_acts.check(act, arguments(step, seed))
            except desk_acts.Refusal as refusal:problems.append('step %d, on %s: %s' % (n, seed, refusal.words))
        for path in list(step.get('expect', {})) + [p for v in step.get('expect_by_run', {}).values() for p in v] + [p for v in step.get('expect_by_seed', {}).values() for p in v]:
            if not str(path).startswith(('act.', 'desk.')):problems.append('step %d: %r reads neither act. nor desk.' % (n, path))
    return problems


def arguments(step, seed):
    """A step's arguments on one seed: its own, with what args_by_seed gives for that seed added or put in their place."""
    return {**(step.get('args') or {}), **((step.get('args_by_seed') or {}).get(seed) or {})}


def expected(step, run_name, seed):
    want = dict(step.get('expect') or {})
    want.update((step.get('expect_by_run') or {}).get(run_name) or {})
    want.update((step.get('expect_by_seed') or {}).get(seed) or {})
    return want


def run_scene(host, scene, run, *, seed, origin, after_step=None):
    """Play one run of a scene on the live window. `run` is a run's name or the run itself. A seed the scene has a
    `workspaces` entry for is played as that workspace has it (for_workspace), its names to find found first in the window's
    workspace (find_names; ValueError, in words, when one is not there). Returns {run, seed, found: {a name the scene says:
    the name found there}, steps: [{n, act, ok, by, seconds, words, checks: [{path, want, got, ok}]}], passed} or
    {blocked: why}."""
    from . import boss_theme, desk_doers
    found = {}
    if seed != scene.get('seed') and seed in (scene.get('workspaces') or {}):
        from .engineering_kernel import operator
        found = find_names(host.ledger_bridge.kernel, operator(), scene, seed)
        scene = for_workspace(scene, seed, found)
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
    out = {'run': run['name'], 'seed': seed, 'found': found, 'style': style, 'reduce_motion': bool(run.get('reduce_motion')), 'steps': []}
    try:
        for n, step in enumerate(scene['steps'], 1):
            started = time.monotonic();checks = []
            args = arguments(step, seed)          # worked out once: what the doer is given is what the row says it was given
            try:
                envelope = desk_doers.run(host, step['act'], args, door='script', by=style, origin=origin,
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
            row = {'n': n, 'act': step['act'], 'args': args, 'ok':all(c['ok'] for c in checks) if checks else bool(envelope.get('ok')),
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
