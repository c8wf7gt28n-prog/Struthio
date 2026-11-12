"""Stage Three checks without weights: context, ranking, process restart and restore.

--runtime probes the pinned executable, not model inference. --ui needs PySide6.
Real-model task quality is measured separately in Brain's task trials.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def fixture(root, principal):
    from .project_desk_checks import fixture as projects, invoke
    kernel, project, assignment = projects(root, principal)
    (root / 'Files' / 'clock.txt').write_text('Clock design note\nThe clock uses a 330 ohm resistor and a 3 volt supply.\n')
    assignment = invoke(kernel, 'assignments.revise', {'id': assignment['id'], 'expected_revision': assignment['revision'],
        'inputs': ['files:clock.txt'], 'interpretation': 'Read the clock design note and preserve its source.'}, principal)
    context = invoke(kernel, 'slate.context.create', {'assignment': assignment['id'], 'question': 'What resistor does the clock use?',
        'include_seed': False, 'char_budget': 2000}, principal)
    if not any('330' in p['text'] and p['kind'] == 'SOURCE' for p in context['selection']['selected']):
        raise ValueError('The reference passage was not selected')
    return kernel, project, assignment, context


def resumed(root, profile, ident, expected):
    from .baseline import environment
    os.environ.update(environment(os.environ, root, profile))
    from .engineering_kernel import Kernel, operator
    from .project_desk_checks import invoke
    principal = operator('stage-three-check'); kernel = Kernel(root)
    value = invoke(kernel, 'slate.context.get', {'id': ident}, principal)
    state = invoke(kernel, 'slate.context.check', {'id': ident}, principal)
    rebuilt = invoke(kernel, 'slate.context.rebuild', {'id': ident}, principal)
    if value['content_digest'] != expected or not state['usable'] or not rebuilt['matches_frozen_selection']:
        raise ValueError('Frozen context or rebuilt ranking did not survive restart/restore')
    return {'state': 'PASSED', 'context_digest_preserved': True, 'sources_current': True,
            'derivative_index_rebuilt': True, 'selected_passages': len(value['selection']['selected']), 'model_started': False}


def self_test():
    from .baseline import environment
    from .engineering_kernel import operator
    from . import workspace_backup
    with tempfile.TemporaryDirectory(prefix='ledger-stage-three-') as temporary:
        base = Path(temporary); root = base / 'Office'; profile = base / 'profile'
        os.environ.update(environment(os.environ, root, profile))
        kernel, _, _, context = fixture(root, operator('stage-three-check'))
        def restart(at, config):
            child = subprocess.run([sys.executable, '-m', 'workbench.slate_checks', '--resume', str(at), str(config), context['id'], context['content_digest']],
                env=environment(os.environ, at, config), capture_output=True, text=True, timeout=40)
            if child.returncode: raise ValueError('Context reopen failed: ' + (child.stderr or child.stdout)[-1000:])
            return json.loads(child.stdout)
        first = restart(root, profile)
        saved = workspace_backup.create(root, base / 'backup')
        restored = workspace_backup.restore(base / 'backup', base / 'Restored')
        second = restart(Path(restored['workspace']), Path(restored['profile']))
        return {'state': 'PASSED', 'scope': 'Disposable source-retrieval and recovery fixtures; no model inference',
            'restart': first, 'backup': {k: saved[k] for k in ('state', 'files', 'databases')},
            'restored_restart': second, 'model_calls': 0, 'external_network_calls': 0,
            'model_quality': 'NOT_MEASURED_WITHOUT_OWNER_GGUF', 'semantic_embeddings': 'NOT_ENABLED'}


def runtime_test():
    from .baseline import environment
    from .brain_runtime import prepare
    with tempfile.TemporaryDirectory(prefix='ledger-runtime-probe-') as temporary:
        base = Path(temporary); root = base / 'Office'; root.mkdir(); profile = base / 'profile'
        os.environ.update(environment(os.environ, root, profile))
        executable, identity = prepare(root)
        child = subprocess.run([str(executable), '--version'], capture_output=True, text=True, timeout=20)
        if child.returncode: raise ValueError('Pinned CPU executable did not start: ' + (child.stderr or child.stdout)[-500:])
        return {'state': 'PASSED', 'runtime': identity, 'version_output': (child.stdout + child.stderr)[-2000:],
                'scope': 'Pinned executable launch on this execution host only; no weights or generation', 'model_quality': 'NOT_MEASURED'}


def ui_test():
    from .baseline import environment
    with tempfile.TemporaryDirectory(prefix='ledger-stage-three-ui-') as temporary:
        base = Path(temporary); root = base / 'Office'; profile = base / 'profile'
        os.environ.update(environment(os.environ, root, profile)); os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from .locations import office
        office(root)
        from .qt_app import make_app, WorkbenchWindow
        from .project_desk_qt import show
        from PySide6.QtTest import QTest
        app = make_app(['ledger-stage-three-check']); host = WorkbenchWindow(root=root, restore=False)
        try:
            host.show(); tab = show(host); pane = tab.reasoning
            pane.question.setPlainText('What is Ledger?'); pane.assemble()
            deadline = time.monotonic() + 10
            while pane.preparing and time.monotonic() < deadline:
                QTest.qWait(20)
            if not pane.context or 'Selected' not in pane.sources.toPlainText(): raise ValueError('Context widgets did not assemble sources')
            pane.ask(); app.processEvents()
            if pane.job or 'Choose and start a local model' not in pane.notice.text():
                raise ValueError('Source question did not report the empty model slot')
            brain = host.ledger_bridge.show_brain()
            if brain.list.count() or 'No model registered' not in brain.summary.toPlainText():
                raise ValueError('Brain did not present the empty local model slot')
            return {'state': 'PASSED', 'scope': 'Real Qt source assembly and empty Brain panel; no GGUF inference',
                    'model_slot': 'EMPTY', 'owner_display_walkthrough': 'PENDING'}
        finally: host.close(); app.processEvents()


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--runtime', action='store_true'); parser.add_argument('--ui', action='store_true')
    parser.add_argument('--resume', nargs=4); args = parser.parse_args()
    try:
        value = resumed(Path(args.resume[0]), Path(args.resume[1]), args.resume[2], args.resume[3]) if args.resume else runtime_test() if args.runtime else ui_test() if args.ui else self_test()
        print(json.dumps(value, indent=2)); return 0
    except (ValueError, OSError, ImportError, subprocess.SubprocessError) as exc:
        print(json.dumps({'state': 'FAILED', 'error': str(exc)}, indent=2)); return 1


if __name__ == '__main__': raise SystemExit(main())
