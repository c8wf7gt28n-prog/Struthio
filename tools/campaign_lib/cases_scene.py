"""The scenes set (P01a..P01d, DP01a..DP01d): the owner's playable scene, played on a live offscreen window by desk acts alone.

P01 (data/scenes/P01.json): open a menu across the head; Then over a CSV in Files (keep rows where unit is mA, count, put it
in the writing line); back to the Field; trace the bench readings; compare the two revisions of the limits; take back what
Stacy's hand wrote. Four cases, one per run of the scene: by pointer (P01a), by keys (P01b), and each with less motion
(P01c, P01d), in the After Hours 07 workspace, restored with Graphite's own backup code.

0.8.5: the scene is written on Rail Demo, the workspace of invented data the program builds itself (workbench/rail_demo.py),
and names nothing of the owner's workspace. DP01a..DP01d play it as written: they need nothing from the owner and play
anywhere. The After Hours 07 backup is the owner's and is never shipped, so P01a..P01d are Blocked wherever it is not;
where it is, the scene's "after_hours_07" entry says how each name is found there (its kind and the words it says), and
the case finds them in the restored workspace before the first step (desk_scene.find_names). The window's readings are
then said back in the scene's own names (desk_scene.said_back), so each case is judged against the scene as written, by
the same checks as its twin.

The case builds the window behind the same holds as the right-click's tests (no provider request, no job, no worker, no
session or power call, no process start), stops the window's own timers, and plays the run through
workbench.desk_scene.run_scene with origin "desk-script:P01". Each step is reported as it ends (progress "act"), each check
is an observation named "<step>:<path>", and a picture of the window is kept for each step under shots/. The expected
values are the scene's own, flattened for the case's seed and the run; every step also expects its act to be done.
No model runs: the acts are the script.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from .core import Case

SCENES = Path(__file__).resolve().parent / 'data' / 'scenes'
SEED = 'after_hours_07'
DEMO = 'rail_demo'
RUNS = (('P01a', 'mouse'), ('P01b', 'keys'), ('P01c', 'mouse_still'), ('P01d', 'keys_still'))


def load(scene_id):
    return json.loads((SCENES / ('%s.json' % scene_id)).read_text(encoding='utf-8'))


def for_workspace(scene, workspace):
    """The scene as it is played on another workspace: workbench.desk_scene.for_workspace, the same swap with the same answer
    (the runner's parent decides what a case expects without importing Graphite). The names an entry finds ("find") are
    found only where the scene is played: here they stay as the scene says them, as the child says back what it read."""
    if workspace == scene.get('seed'):return copy.deepcopy(scene)
    there = (scene.get('workspaces') or {}).get(workspace)
    if not isinstance(there, dict):raise ValueError('The scene %s is not written for the workspace %r' % (scene.get('id', ''), workspace))
    names = there.get('names', {})
    if not isinstance(names, dict) or not all(isinstance(k, str) and k and isinstance(v, str) for k, v in names.items()):
        raise ValueError('The scene %s, workspace %r: names is not an object of names' % (scene.get('id', ''), workspace))
    said = re.compile('|'.join(re.escape(name) for name in sorted(names, key=len, reverse=True))) if names else None

    def swap(value):
        if isinstance(value, str):return said.sub(lambda found: names[found.group(0)], value) if said else value
        if isinstance(value, list):return [swap(v) for v in value]
        if isinstance(value, dict):return {key: swap(v) for key, v in value.items()}
        return value
    out = copy.deepcopy(scene)
    out['steps'] = swap(out.get('steps') or [])
    out['seed'] = workspace
    for key in ('title', 'intent'):
        if there.get(key):out[key] = there[key]
    return out


def flattened(scene, run_name, seed=SEED):
    """The scene's expectations for one run and one seed, as campaign checks: '<n>:<path>' -> value; and '<n>:act.ok' True
    for each step that does not expect a refusal."""
    out = {}
    for n, step in enumerate(scene['steps'], 1):
        want = dict(step.get('expect') or {})
        want.update((step.get('expect_by_run') or {}).get(run_name) or {})
        want.update((step.get('expect_by_seed') or {}).get(seed) or {})
        if 'act.ok' not in want and 'act.error.code' not in want:want['act.ok'] = True
        for path, value in want.items():out['%d:%s' % (n, path)] = value
    return out


def run_case(ctx):
    """Build the window on the case's workspace (restored, or built by the program), play the run, report every check."""
    import os
    import platform
    import subprocess
    from unittest.mock import patch
    from . import fixture
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.pop('ARC_LEDGER_XSESSION', None)
    from PySide6.QtCore import QProcess
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QMessageBox
    from workbench import boss_theme, clip, desk_scene, session_power
    from workbench.engineering_kernel import Kernel, operator
    from workbench.qt_app import WorkbenchWindow, make_app
    from workbench.session import Session
    written = load(ctx.case.inputs['scene'])
    found = desk_scene.find_names(ctx.kernel, operator(), written, ctx.case.seed) if ctx.case.seed != written.get('seed') else {}
    ctx.note('found', sorted(found))          # which of the scene's names were found there (not what they are called there)
    scene = desk_scene.for_workspace(written, ctx.case.seed, found);run_name = ctx.case.inputs['run']
    if (scene.get('given') or {}).get('appearance', boss_theme.APPEARANCE) != boss_theme.APPEARANCE:
        raise fixture.Blocked('The scene is for the %s appearance, and the appearance is chosen when Graphite starts.' % scene['given']['appearance'])

    def no_logind(request):
        raise OSError('No session or power call in a campaign case')
    holds = [patch.object(clip, '_request', side_effect=AssertionError('No provider request')),
             patch.object(Kernel, 'launch', side_effect=AssertionError('a scene case must not start a job worker')),
             patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')),
             patch.object(session_power, 'system', side_effect=no_logind),
             patch.object(QMessageBox, 'question', return_value=QMessageBox.No)]
    for hold in holds:hold.start()
    late = []
    shots = Path(ctx.folder) / 'shots';shots.mkdir(exist_ok=True)
    try:
        app = make_app([])
        session = Session(Path(ctx.folder) / 'profile' / 'session.json', ctx.kernel.root)
        w = WorkbenchWindow(ctx.kernel.root, session, restore=False);platform.processor()
        late = [patch.object(subprocess, 'Popen', side_effect=AssertionError('No process start')),
                patch.object(os, 'system', side_effect=AssertionError('No shell command')),
                patch.object(QProcess, 'startDetached', side_effect=AssertionError('No detached program'))]
        for hold in late:hold.start()
        width, height = (scene.get('given') or {}).get('size') or (1920, 1200)      # the scene's own window, as given
        w.resize(int(width), int(height));w.show()

        def settle(ms=30):
            for name in ('agenda_runner', 'study_idle'):
                timer = getattr(getattr(w, name, None), 'timer', None)
                if timer is not None:timer.stop()
            for _ in range(3):app.processEvents();QTest.qWait(ms)
        settle(60);w.ledger_bridge.timer.stop()
        try:w.type_bar.hatch.lifecycle.timer.stop()
        except AttributeError:pass
        settle()

        def after(n, step, row):
            settle()
            ctx.progress('act', n=n, act=step['act'], ok=row['ok'], by=row['by'], seconds=row['seconds'])
            for check in row['checks']:ctx.observe('%d:%s' % (n, check['path']), desk_scene.said_back(check['got'], found))
            # done, and no ask or refusal the scene did not declare (run_scene adds those as checks of its own)
            unasked = [c for c in row['checks'] if c['path'] in ('act.ok', 'act.result.waits', 'step') and not c['ok']]
            ctx.observe('%d:act.ok' % n, bool(row['done']) and not unasked)
            try:w.grab().save(str(shots / ('%02d.png' % n)))
            except Exception:  # noqa: BLE001 - a picture that cannot be kept is not a failed step
                pass
        out = desk_scene.run_scene(w, scene, run_name, seed=ctx.case.seed, origin='desk-script:%s' % scene['id'], after_step=after)
        if out.get('blocked'):raise fixture.Blocked(out['blocked'])
        ctx.note('steps', [{k: s[k] for k in ('n', 'act', 'ok', 'by', 'seconds', 'words', 'result')} for s in out['steps']])
        ctx.note('passed', out['passed'])
        ctx.note('appearance', boss_theme.APPEARANCE)      # the appearance it was played in
        try:w.close();settle()
        except RuntimeError:pass
    finally:
        for hold in reversed(late + holds):hold.stop()


def _cases():
    from . import fixture
    written = load('P01');out = []
    for prefix, seed, where, need in (('', SEED, 'in After Hours 07', 'after_hours_07'), ('D', DEMO, 'on Rail Demo (invented data)', 'rail_demo')):
        scene = for_workspace(written, seed)
        start = {'workspace': 'Rail Demo, invented data', 'built_by': fixture.rail_demo_identity()} if seed == DEMO else {}
        for case_id, run_name in RUNS:
            run = next(r for r in scene['runs'] if r['name'] == run_name)
            words = {'mouse': 'by pointer', 'keys': 'by keys', 'mouse_still': 'by pointer, with less motion', 'keys_still': 'by keys, with less motion'}[run_name]
            out.append(Case(id=prefix + case_id, set='scenes', title='P01, the playable scene %s, %s' % (where, words), seed=seed,
                            intent=scene.get('intent', scene['title']), needs=[need], budget_s=240, start=start,
                            source_case=('%s on Rail Demo' % case_id) if seed == DEMO else None,
                            inputs={'scene': 'P01', 'run': run_name, 'style': run['style'], 'reduce_motion': bool(run.get('reduce_motion'))},
                            expect=flattened(scene, run_name, seed), fn=run_case))
    return out


CASES = _cases()
