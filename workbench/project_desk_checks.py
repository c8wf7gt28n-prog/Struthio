"""Disposable Stage Two walkthrough, real process restart, and complete restore.

Run: python3 -m workbench.project_desk_checks [--ui]
No user workspace, model, network or execution grants are used.
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

REQUEST = 'Help me see which parts are short.\nKeep my original wording — please.  '


def invoke(kernel, operation, arguments, principal):
    response = kernel.dispatch(operation, arguments, principal)
    if not response['ok']: raise ValueError(operation + ': ' + response['error']['message'])
    return response['result']


def fixture(root, principal):
    from . import locations
    from .engineering_kernel import Kernel
    locations.office(root); kernel = Kernel(root)
    files = root / 'Files'; files.mkdir(exist_ok=True)
    (files / 'stock.csv').write_text('Part,Need,Have\nR1,12,5\nR2,3,8\n')
    idea = invoke(kernel, 'ideas.capture', {'text': REQUEST}, principal)
    promoted = invoke(kernel, 'ideas.promote', {'id': idea['id'], 'expected_revision': 1, 'title': 'Parts desk'}, principal)
    project = promoted['project']
    assignment = invoke(kernel, 'assignments.create', {'project': project['id'], 'request': REQUEST,
        'interpretation': 'Read the stock table and list shortages.', 'intended_output': 'A reviewed shortage note',
        'inputs': ['files:stock.csv'], 'questions': [], 'success': ['The note names the short parts and counts.'],
        'stop': ['Stop if the input table changes or a column is missing.']}, principal)
    return kernel, project, assignment


def plan_arguments(assignment):
    from .project_desk import DEFAULT_BUDGET
    return {'id': assignment['id'], 'expected_revision': assignment['revision'], 'language': 'QUERY',
        'program': '@files:stock.csv | rows | add Short = Need - Have | where Short over 0',
        'permissions': {'operations': ['ledger.address.read'], 'effects': ['read'], 'working_roots': [],
                        'network': False, 'expires': time.time() + 3600}, 'budget': dict(DEFAULT_BUDGET)}


def resume(root, profile, expected):
    from .baseline import environment
    os.environ.update(environment(os.environ, root, profile))
    from .engineering_kernel import Kernel, operator
    sheet = invoke(Kernel(root), 'assignments.reopen', {'id': expected['assignment']}, operator('stage-two-check'))
    if sheet['assignment']['original_request'] != REQUEST: raise ValueError('Original request changed across restart')
    if sheet['plans'][0]['content_digest'] != expected['plan_digest']: raise ValueError('Frozen plan changed across restart')
    if sheet['reviews'][0]['id'] != expected['review']: raise ValueError('Review disappeared across restart')
    if sheet['freshness']['state'] != 'CURRENT': raise ValueError('Restored input bytes do not match the frozen revision')
    if sheet['reviews'][0]['outputs'][0]['snapshot']['exact_bytes_base64'] != expected['output_bytes']:
        raise ValueError('Frozen output bytes changed')
    if sheet['restart'] != 'REOPENED_WITHOUT_EXECUTION' or sheet['automatic_resume']: raise ValueError('Unexpected execution')
    return {'state': 'PASSED', 'exact_original_words': True, 'plan_digest_preserved': True,
            'output_bytes_preserved': True, 'input_revisions_current': True, 'automatic_resume': False,
            'history_revisions': len(sheet['interpretation_history']), 'journal_events': len(sheet['journal'])}


def self_test():
    from .baseline import environment
    from .engineering_kernel import operator
    from . import workspace_backup
    with tempfile.TemporaryDirectory(prefix='ledger-stage-two-') as temporary:
        base = Path(temporary); root = base / 'Office'; profile = base / 'profile'
        os.environ.update(environment(os.environ, root, profile)); principal = operator('stage-two-check')
        kernel, project, assignment = fixture(root, principal)
        planned = invoke(kernel, 'assignments.plan', plan_arguments(assignment), principal)
        # This is an explicit read action in the test, separate from plan saving.
        actual = invoke(kernel, 'language.run', {'text': planned['plan']['program']}, principal)
        if actual['rows'] != [{'Part': 'R1', 'Need': 12, 'Have': 5, 'Short': 7}]: raise ValueError('Unexpected query result')
        (root / 'Files' / 'shortages.md').write_text('R1 is short by 7.\n')
        reviewed = invoke(kernel, 'assignments.review', {'id': assignment['id'],
            'expected_revision': planned['assignment']['revision'], 'plan': planned['plan']['id'], 'decision': 'ACCEPT',
            'note': 'Compared the shortage note with the actual read result.', 'outputs': ['files:shortages.md'], 'unresolved': []}, principal)
        expected = {'assignment': assignment['id'], 'plan_digest': planned['plan']['content_digest'],
            'review': reviewed['review']['id'], 'output_bytes': reviewed['review']['outputs'][0]['snapshot']['exact_bytes_base64']}
        def restart(at, config):
            command = [sys.executable, '-m', 'workbench.project_desk_checks', '--resume', str(at), str(config), json.dumps(expected)]
            child = subprocess.run(command, env=environment(os.environ, at, config), capture_output=True, text=True, timeout=40)
            if child.returncode: raise ValueError('Reopen failed: ' + (child.stderr or child.stdout)[-1200:])
            return json.loads(child.stdout)
        first = restart(root, profile)
        saved = workspace_backup.create(root, base / 'backup')
        restored = workspace_backup.restore(base / 'backup', base / 'Restored')
        second = restart(Path(restored['workspace']), Path(restored['profile']))
        return {'state': 'PASSED', 'scope': 'Disposable shared-Kernel workflow on this execution host',
            'workflow': 'Idea → project → assignment → frozen query plan → explicit read → owner review',
            'restart': first, 'backup': {key: saved[key] for key in ('state', 'files', 'databases')},
            'restored_restart': second, 'model_calls': 0, 'network_calls': 0,
            'qt': 'SEPARATE_CHECK', 'physical_qualification': False}


def ui_test():
    from .baseline import environment
    with tempfile.TemporaryDirectory(prefix='ledger-stage-two-ui-') as temporary:
        base = Path(temporary); root = base / 'Office'; profile = base / 'profile'
        os.environ.update(environment(os.environ, root, profile)); os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from .locations import office
        office(root)
        from .qt_app import make_app, WorkbenchWindow
        from .project_desk_qt import show
        app = make_app(['ledger-stage-two-check']); host = WorkbenchWindow(root=root, restore=False)
        try:
            host.show(); tab = show(host); app.processEvents()
            tab.idea_text.setPlainText(REQUEST); tab.capture_idea()
            if tab.ideas.count() != 1: raise ValueError('Idea widget did not save through the Kernel')
            tab.project_title.setText('UI project'); tab.project_intent.setPlainText(REQUEST); tab.create_project()
            if not tab.project: raise ValueError('Project widget did not save')
            tab.request.setPlainText(REQUEST); tab.interpretation.setPlainText('Read the selected project title.')
            tab.output.setText('A note about the project'); tab.success.setPlainText('The project title is returned.')
            tab.stop.setPlainText('Stop if the selected project cannot be read.'); tab.save_assignment()
            if not tab.assignment: raise ValueError('Assignment widget did not save')
            tab.freeze_plan(); app.processEvents()
            if not tab.assignment.get('plan'): raise ValueError('Plan widget did not freeze the query')
            if tab.request.toPlainText() != REQUEST or not tab.request.isReadOnly(): raise ValueError('Original request widget changed')
            if show(host) is not tab: raise ValueError('Project Desk navigation opened a duplicate tab')
            return {'state': 'PASSED', 'scope': 'Real Qt window and Project Desk widgets, offscreen disposable fixture',
                    'visual_walkthrough': 'STILL_REQUIRED_ON_OWNER_DISPLAY'}
        finally: host.close(); app.processEvents()


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--ui', action='store_true')
    parser.add_argument('--resume', nargs=3, metavar=('WORKSPACE', 'PROFILE', 'EXPECTED_JSON')); args = parser.parse_args()
    try:
        result = resume(Path(args.resume[0]), Path(args.resume[1]), json.loads(args.resume[2])) if args.resume else ui_test() if args.ui else self_test()
        print(json.dumps(result, indent=2)); return 0
    except (ValueError, OSError, ImportError, subprocess.SubprocessError) as exc:
        print(json.dumps({'state': 'FAILED', 'error': str(exc)}, indent=2)); return 1


if __name__ == '__main__': raise SystemExit(main())
