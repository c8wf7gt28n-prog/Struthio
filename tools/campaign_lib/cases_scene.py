"""The scenes set (P01a..P01d): the owner's playable scene, played on a live offscreen window by desk acts alone.

P01 (data/scenes/P01.json) runs in the After Hours 07 workspace, restored with Graphite's own backup code: open a menu across
the head; Then over a CSV in Files (keep rows where unit is mA, count, put it in the writing line); back to the Field; trace
07 Bench readings; compare the two revisions of the limits; take back what Stacy's hand wrote. Four cases, one per run of
the scene: by pointer (P01a), by keys (P01b), and each with less motion (P01c, P01d).

The case builds the window behind the same holds as the right-click's tests (no provider request, no job, no worker, no
session or power call, no process start), stops the window's own timers, and plays the run through
workbench.desk_scene.run_scene with origin "desk-script:P01". Each step is reported as it ends (progress "act"), each check
is an observation named "<step>:<path>", and a picture of the window is kept for each step under shots/. The expected
values are the scene's own, flattened for the After Hours 07 seed and the run; every step also expects its act to be done.
No model runs: the acts are the script.
"""
from __future__ import annotations

import json
from pathlib import Path

from .core import Case

SCENES = Path(__file__).resolve().parent / 'data' / 'scenes'
SEED = 'after_hours_07'
RUNS = (('P01a', 'mouse'), ('P01b', 'keys'), ('P01c', 'mouse_still'), ('P01d', 'keys_still'))


def load(scene_id):
    return json.loads((SCENES / ('%s.json' % scene_id)).read_text(encoding='utf-8'))


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
    """Build the window on the restored workspace, play the run, report every check."""
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
    from workbench.engineering_kernel import Kernel
    from workbench.qt_app import WorkbenchWindow, make_app
    from workbench.session import Session
    scene = load(ctx.case.inputs['scene']);run_name = ctx.case.inputs['run']
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
            for check in row['checks']:ctx.observe('%d:%s' % (n, check['path']), check['got'])
            # done, and no ask or refusal the scene did not declare (run_scene adds those as checks of its own)
            unasked = [c for c in row['checks'] if c['path'] in ('act.ok', 'act.result.waits', 'step') and not c['ok']]
            ctx.observe('%d:act.ok' % n, bool(row['done']) and not unasked)
            try:w.grab().save(str(shots / ('%02d.png' % n)))
            except Exception:  # noqa: BLE001 - a picture that cannot be kept is not a failed step
                pass
        out = desk_scene.run_scene(w, scene, run_name, seed=SEED, origin='desk-script:%s' % scene['id'], after_step=after)
        if out.get('blocked'):raise fixture.Blocked(out['blocked'])
        ctx.note('steps', [{k: s[k] for k in ('n', 'act', 'ok', 'by', 'seconds', 'words', 'result')} for s in out['steps']])
        ctx.note('passed', out['passed'])
        ctx.note('appearance', boss_theme.APPEARANCE)      # the appearance it was played in
        try:w.close();settle()
        except RuntimeError:pass
    finally:
        for hold in reversed(late + holds):hold.stop()


def _cases():
    scene = load('P01');out = []
    for case_id, run_name in RUNS:
        run = next(r for r in scene['runs'] if r['name'] == run_name)
        words = {'mouse': 'by pointer', 'keys': 'by keys', 'mouse_still': 'by pointer, with less motion', 'keys_still': 'by keys, with less motion'}[run_name]
        out.append(Case(id=case_id, set='scenes', title='P01, the playable scene in After Hours 07, %s' % words, seed=SEED,
                        intent=scene.get('intent', scene['title']), needs=['after_hours_07'], budget_s=240,
                        inputs={'scene': 'P01', 'run': run_name, 'style': run['style'], 'reduce_motion': bool(run.get('reduce_motion'))},
                        expect=flattened(scene, run_name), fn=run_case))
    return out


CASES = _cases()
