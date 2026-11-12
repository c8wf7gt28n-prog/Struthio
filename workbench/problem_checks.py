"""I01 disposable real-read, stale-binding, restart and legacy-authority checks.

python3 -m workbench.problem_checks [--ui] [--output PATH]
No model call, hardware qualification or original publication is performed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
from . import clock_lab, project_desk as records


def invoke(kernel, op, args, principal):
    result = kernel.dispatch(op, args, principal)
    if not result['ok']: raise ValueError(op + ': ' + result['error']['message'])
    return result['result']


def bound(problem):
    return {'id': problem['id'], 'expected_revision': problem['revision'],
            'expected_context_digest': problem['context_digest']}


def resume(root, profile, expected_path):
    from .baseline import environment
    os.environ.update(environment(os.environ, root, profile))
    from .engineering_kernel import Kernel, operator
    expected = json.loads(Path(expected_path).read_text())
    kernel = Kernel(root); principal = operator()
    sheet = invoke(kernel, 'problems.get', {'id': expected['problem']['id']}, principal)
    if sheet['problem'] != expected['problem']: raise ValueError('Problem changed across restart')
    if sheet['receipts'] != expected['receipts']: raise ValueError('Actual read bytes or bindings changed across restart')
    if sheet['freshness']['state'] != 'CURRENT': raise ValueError('Restored sources are not current')
    if sheet['unknowns'] != ['lifetime_A', 'lifetime_B', 'lifetime_workspace']: raise ValueError('An unknown was silently resolved')
    if sheet['automatic_resume']: raise ValueError('Reopening scheduled work')
    return {'state': 'PASSED', 'exact_problem': True, 'exact_receipts': True, 'unknowns_preserved': True,
            'automatic_resume': False, 'problem_revision': sheet['problem']['revision']}


def self_test():
    from .baseline import environment
    from .engineering_kernel import Kernel, Principal, operator, CAPABILITIES, TOOLS
    from .engineering_cli import schemas
    from . import locations
    with tempfile.TemporaryDirectory(prefix='ledger-i01-') as temporary:
        base = Path(temporary); home = base / 'Home'; home.mkdir(); root = base / 'Office'; profile = base / 'profile'
        with patch.dict(os.environ, {**environment(os.environ, root, profile), 'HOME': str(home)}), patch.object(Path, 'home', return_value=home):
            source = clock_lab.copy_inputs(home / 'Clock_Lab_I01')
            locations.office(root); kernel = Kernel(root); principal = operator()
            started = clock_lab.start(kernel, source, principal); problem = started['problem']
            events = []; original = kernel.dispatch
            def traced(op, args=None, p=None):
                events.append(op); return original(op, args, p)
            with patch.object(kernel, 'dispatch', side_effect=traced):
                action = invoke(kernel, 'problems.prepare', {**bound(problem), 'source': 0}, principal)
                if 'work.read' in events: raise ValueError('Preparing an action executed it')
                result = invoke(kernel, 'problems.run', {'action': action['id']}, principal)
            if events.count('work.read') != 1: raise ValueError('No single registered source read occurred')
            receipt = result['receipt']; actual = (source / 'requirements.md').read_text()
            if receipt['snapshot']['text'] != actual: raise ValueError('Receipt differs from actual source bytes')
            if receipt['snapshot']['sha256'] != hashlib.sha256(actual.encode()).hexdigest(): raise ValueError('Source digest differs')
            if receipt['output_digest'] != records.digest(receipt['snapshot']): raise ValueError('Output digest differs')
            events.clear()
            with patch.object(kernel, 'dispatch', side_effect=traced): replay = invoke(kernel, 'problems.run', {'action': action['id']}, principal)
            if not replay['replayed'] or 'work.read' in events: raise ValueError('Replayed receipt executed another read')
            candidate = invoke(kernel, 'problems.prepare', {**bound(problem), 'source': 0}, principal)
            work = root / 'Files' / started['copy']['work'] / 'requirements.md'
            old = work.stat(); work.write_bytes(work.read_bytes().replace(b'16 MiB', b'18 MiB'))
            os.utime(work, ns=(old.st_atime_ns, old.st_mtime_ns))
            stale_source = kernel.dispatch('problems.run', {'action': candidate['id']}, principal)
            if stale_source['ok'] or 'PROBLEM_SOURCE_CHANGED' not in stale_source['error']['message']: raise ValueError('Changed bytes were accepted')
            changed = invoke(kernel, 'problems.get', {'id': problem['id']}, principal)
            if changed['freshness']['state'] != 'REVIEW_REQUIRED' or len(changed['receipts']) != 1: raise ValueError('A failed read became evidence')
            work.write_text(actual)
            revised = invoke(kernel, 'problems.revise', {**bound(problem), 'questions': problem['questions'] + ['What is the intended lifetime schedule?']}, principal)
            stale_revision = kernel.dispatch('problems.run', {'action': candidate['id']}, principal)
            if stale_revision['ok'] or 'PROBLEM_REVISION_CHANGED' not in stale_revision['error']['message']: raise ValueError('A stale problem action ran')
            if kernel.dispatch('problems.revise', {**bound(problem), 'title': 'Stale editor'}, principal)['ok']: raise ValueError('Stale editor overwrote the problem')
            reader = Principal(principal.identity)
            for op, args in [('problems.prepare', {**bound(revised), 'source': 0}), ('problems.run', {'action': candidate['id']}),
                             ('problems.revise', {**bound(revised), 'title': 'Outside read scope'})]:
                if kernel.dispatch(op, args, reader)['ok']: raise ValueError('Read-only principal gained action authority')
            stranger = operator('another-owner')
            if kernel.dispatch('problems.get', {'id': problem['id']}, stranger)['ok']: raise ValueError('Another owner read a private problem')
            if invoke(kernel, 'problems.list', {}, stranger)['records']: raise ValueError('Another owner listed a private problem')
            history = invoke(kernel, 'problems.history', {'id': problem['id']}, principal)['records']
            if len(history) != 2 or any(v['original_request'] != problem['original_request'] for v in history): raise ValueError('Original request/history changed')
            discovery = invoke(kernel, 'problems.tools', {'id': problem['id']}, principal)
            if len(discovery['operations']) != 6: raise ValueError('Relevant discovery is not bounded')
            if set(CAPABILITIES) != set(schemas()): raise ValueError('Capability and schema registry differ')
            from .slate_reasoning import READ_PROPOSALS
            if 'problems.run' in READ_PROPOSALS or 'problems.prepare' in READ_PROPOSALS: raise ValueError('Legacy model PLAN gained effects')
            sheet = invoke(kernel, 'problems.get', {'id': problem['id']}, principal)
            expected_path = base / 'expected.json'; expected_path.write_text(records.canonical({'problem': sheet['problem'], 'receipts': sheet['receipts']}))
            proc = subprocess.run([sys.executable, '-m', 'workbench.problem_checks', '_resume', str(root), str(profile), str(expected_path)],
                                  capture_output=True, text=True, env=locations.child_env(root), timeout=30)
            if proc.returncode: raise ValueError('Fresh-process reopen failed: ' + (proc.stderr or proc.stdout)[-1200:])
            restarted = json.loads(proc.stdout)
            if (source / 'requirements.md').read_text() != actual: raise ValueError('Original exercise changed')
            return {'state': 'PASSED', 'pass': 'I01', 'scope': 'Disposable service fixture on this execution host',
                'real_registered_operation': 'work.read', 'actual_bytes': receipt['snapshot']['bytes'],
                'source_sha256': receipt['snapshot']['sha256'], 'output_digest': receipt['output_digest'],
                'prepare_does_not_execute': True, 'replay_does_not_execute': True,
                'changed_same_size_and_mtime_refused': True, 'stale_problem_refused': True,
                'owner_and_read_only_scope_preserved': True, 'legacy_plan_authority_unchanged': True,
                'history_revisions': len(history), 'relevant_operations': len(discovery['operations']),
                'registered_operations': len(CAPABILITIES), 'registered_job_tools': len(TOOLS),
                'fresh_process_reopen': restarted, 'model_calls': 0, 'native_invocations': 0,
                'thinkpad_qualification': 'NOT_PERFORMED', 'increased_model_intelligence': 'NOT_MEASURED'}


def ui_check():
    """Exercise the real widgets offscreen, when the Qt runtime is installed."""
    try:
        from PySide6.QtWidgets import QApplication, QLabel
    except ImportError:
        return {'state': 'UNAVAILABLE', 'reason': 'PySide6 is not installed on this execution host', 'owner_display': 'PENDING'}
    from .baseline import environment
    from .engineering_kernel import Kernel, operator
    from . import locations
    from .problem_qt import ProblemPane
    with tempfile.TemporaryDirectory(prefix='ledger-i01-ui-') as temporary:
        base = Path(temporary); home = base / 'Home'; home.mkdir(); root = base / 'Office'; profile = base / 'profile'
        with patch.dict(os.environ, {**environment(os.environ, root, profile), 'HOME': str(home), 'QT_QPA_PLATFORM': 'offscreen'}), patch.object(Path, 'home', return_value=home):
            locations.office(root); kernel = Kernel(root)
            result = clock_lab.start(kernel, clock_lab.copy_inputs(home / 'Clock_Lab_I01'), operator())
            from types import SimpleNamespace
            app = QApplication.instance() or QApplication(['ledger-i01-ui'])
            desk = SimpleNamespace(host=SimpleNamespace(root=root), project=result['project'], assignment=result['assignment'], message=QLabel())
            pane = ProblemPane(desk)
            try:
                pane.resize(1180, 820); pane.show(); pane.reload(result['problem']['id']); app.processEvents()
                if pane.variables.rowCount() != 10: raise ValueError('Variable table missing rows')
                pane.sources.setCurrentIndex(0); pane.read_source(); app.processEvents()
                if 'Allocation lifetimes' not in pane.result.toPlainText(): raise ValueError('Real tool output is not visible')
                pane.goals.appendPlainText('Retain the evidence.'); pane.save(); app.processEvents()
                if pane.current['revision'] != 2: raise ValueError('UI edit was not saved')
                pane.open(pane.current['id']); app.processEvents()
                if pane.results.count() != 1: raise ValueError('UI lost the prior-revision observation')
                return {'state': 'PASSED', 'scope': 'Real Qt problem sheet, offscreen', 'owner_display': 'PENDING'}
            finally: pane.close(); app.processEvents()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == '_resume': print(json.dumps(resume(*argv[1:]))); return 0
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--ui', action='store_true'); parser.add_argument('--output')
    args = parser.parse_args(argv)
    result = ui_check() if args.ui else self_test()
    raw = json.dumps(result, indent=2) + '\n'
    if args.output: Path(args.output).write_text(raw)
    print(raw, end='')
    return 0 if result['state'] == 'PASSED' else 2


if __name__ == '__main__': raise SystemExit(main())
