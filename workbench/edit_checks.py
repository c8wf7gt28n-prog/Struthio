"""Disposable import → edit → crash → recover → original undo → backup/restore.

No model, network or owner files are used. A child process exits after the first
real rename, with only the durable intent journal available to the next process.
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


def invoke(kernel, op, args, principal):
    value = kernel.dispatch(op, args, principal)
    if not value['ok']: raise ValueError(op + ': ' + value['error']['message'])
    return value['result']


def fixture(base, identity='stage-four-check'):
    from .baseline import environment
    from .locations import office
    from .engineering_kernel import Kernel, operator
    base = Path(base); home = base / 'Home'; source = home / 'Clock'; source.mkdir(parents=True)
    (source / 'note.txt').write_text('Clock needs blue hands.\n')
    (source / 'parts.csv').write_text('Part,Need,Have\nR1,12,5\n')
    (source / 'old.txt').write_text('Retain this version.\n')
    (source / '.editorconfig').write_text('root = true\n'); (source / '.gitignore').write_text('build/\n')
    (source / '.env').write_text('not copied\n'); (source / 'Empty').mkdir()
    root = base / 'Office'; profile = base / 'profile'; os.environ.update(environment(os.environ, root, profile)); office(root)
    kernel = Kernel(root); principal = operator(identity)
    with patch('pathlib.Path.home', return_value=home):
        preview = invoke(kernel, 'imports.preview', {'source': str(source), 'profile': 'MIXED'}, principal)
        workspace = invoke(kernel, 'imports.accept', {'id': preview['id'], 'expected_digest': preview['content_digest'], 'for_slate': True}, principal)
    return kernel, principal, home, source, workspace


def frozen_changes(kernel, principal, workspace):
    note = invoke(kernel, 'changes.file', {'copy': workspace['id'], 'path': 'note.txt'}, principal)
    table = invoke(kernel, 'changes.file', {'copy': workspace['id'], 'path': 'parts.csv'}, principal)
    old = invoke(kernel, 'changes.file', {'copy': workspace['id'], 'path': 'old.txt'}, principal)
    return invoke(kernel, 'changes.propose', {'copy': workspace['id'], 'note': 'Clock draft and parts update', 'operations': [
        {'op': 'PATCH', 'path': 'note.txt', 'base_sha256': note['sha256'], 'edits': [{'start': 12, 'end': 16, 'old': 'blue', 'new': 'black'}]},
        {'op': 'CELLS', 'path': 'parts.csv', 'base_sha256': table['sha256'], 'cells': [{'cell': 'B2', 'old': {'kind': 'TEXT', 'value': '12'}, 'new': {'kind': 'TEXT', 'value': '15'}}]},
        {'op': 'CREATE', 'path': 'draft.md', 'text': '# Clock draft\nOriginals change only after review.\n'},
        {'op': 'RENAME', 'path': 'old.txt', 'base_sha256': old['sha256'], 'to': 'archive/old.txt'},
    ]}, principal)


def child(root, profile, home, mode, expected):
    from .baseline import environment
    os.environ.update(environment(os.environ, root, profile))
    from .engineering_kernel import Kernel, operator
    from . import change_sets
    principal = operator('stage-four-check'); kernel = Kernel(root)
    with patch('pathlib.Path.home', return_value=home):
        if mode == 'crash':
            change_sets.CRASH_AT = 'MUTATED'
            try: invoke(kernel, 'changes.publish', {'id': expected['original_proposal'], 'expected_digest': expected['original_digest']}, principal)
            except change_sets.Crash: os._exit(77)
            raise ValueError('The fault checkpoint was not reached')
        if mode == 'recover':
            commits = invoke(kernel, 'changes.commits', {'copy': expected['copy']}, principal)['commits']
            interrupted = next(c for c in commits if c['target'] == 'ORIGINAL')
            observed = invoke(kernel, 'changes.commit', {'id': interrupted['id']}, principal)
            if not any(e['state'] == 'APPLIED' and e['journal_stage'] == 'INTENT' for e in observed['observed']):
                raise ValueError('The durable-intent/rename interruption was not observable')
            if not any(e['before'] and e['after'] and o['temporary'] == e['before'] and o['state'] == 'APPLIED'
                       for e, o in zip(observed['entries'], observed['observed'])):
                raise ValueError('The replacement exchange did not retain displaced original bytes')
            recovered = invoke(kernel, 'changes.recover', {'id': interrupted['id'], 'action': 'RESUME'}, principal)
            if recovered['state'] != 'DONE': raise ValueError('Original publish did not recover')
            source = Path(expected['source'])
            if (source / 'note.txt').read_text() != 'Clock needs black hands.\n': raise ValueError('Recovered original bytes differ')
            undone = invoke(kernel, 'changes.undo', {'id': recovered['id']}, principal)
            if undone['state'] != 'DONE' or (source / 'note.txt').read_text() != 'Clock needs blue hands.\n' or not (source / 'old.txt').is_file():
                raise ValueError('Original undo did not restore exact earlier files')
            return {'state': 'PASSED', 'interruption_observed': True, 'resume_without_repeating_done_effect': True,
                    'replacement_exchange_observed': True, 'displaced_original_bytes_retained': True,
                    'original_undo': True, 'source_environment_file_untouched': (source / '.env').read_text() == 'not copied\n'}
        workspace = invoke(kernel, 'changes.workspace', {'id': expected['copy']}, principal)
        review = invoke(kernel, 'changes.review', {'id': expected['working_proposal']}, principal)
        if review['proposal']['content_digest'] != expected['working_digest']: raise ValueError('Frozen proposal changed during restore')
        from .files_service import root as files
        work = files(kernel) / workspace['work']
        if (work / 'note.txt').read_text() != 'Clock needs black hands.\n' or not (work / '.editorconfig').is_file() or (work / '.env').exists():
            raise ValueError('Working bytes, reviewed configuration or exclusion policy did not survive restore')
        return {'state': 'PASSED', 'frozen_proposal_preserved': True, 'working_bytes_preserved': True, 'reviewed_config_preserved': True, 'excluded_credentials_absent': True}


def self_test():
    from .baseline import environment
    from . import workspace_backup
    with tempfile.TemporaryDirectory(prefix='ledger-stage-four-') as temporary:
        base = Path(temporary); kernel, principal, home, source, workspace = fixture(base)
        proposal = frozen_changes(kernel, principal, workspace)
        invoke(kernel, 'changes.apply', {'id': proposal['id'], 'expected_digest': proposal['content_digest']}, principal)
        if (source / 'note.txt').read_text() != 'Clock needs blue hands.\n': raise ValueError('A working update changed an original')
        with patch('pathlib.Path.home', return_value=home): original = invoke(kernel, 'changes.original.preview', {'copy': workspace['id']}, principal)
        expected = {'copy': workspace['id'], 'source': str(source), 'working_proposal': proposal['id'], 'working_digest': proposal['content_digest'],
                    'original_proposal': original['id'], 'original_digest': original['content_digest']}
        def restart(root, profile, mode, code=0):
            process = subprocess.run([sys.executable, '-m', 'workbench.edit_checks', '--child', mode, str(root), str(profile), str(home), json.dumps(expected)],
                env=environment(os.environ, root, profile), capture_output=True, text=True, timeout=60)
            if process.returncode != code: raise ValueError('Child check failed: ' + (process.stderr or process.stdout)[-1200:])
            return json.loads(process.stdout) if code == 0 else {'exit_code': code}
        crash = restart(kernel.root, base / 'profile', 'crash', 77)
        recovered = restart(kernel.root, base / 'profile', 'recover')
        saved = workspace_backup.create(kernel.root, base / 'backup')
        restored = workspace_backup.restore(base / 'backup', base / 'Restored')
        readback = restart(Path(restored['workspace']), Path(restored['profile']), 'readback')
        return {'state': 'PASSED', 'scope': 'Disposable local files; actual Linux rename interruption and new-process recovery',
            'working_updates_leave_masters_unchanged': True, 'crash': crash, 'recovery_and_undo': recovered,
            'complete_backup': {k: saved[k] for k in ('state', 'files', 'databases')}, 'restored_restart': readback,
            'model_calls': 0, 'network_calls': 0, 'power_loss_qualification': 'NOT_PERFORMED'}


def ui_test():
    from .baseline import environment
    with tempfile.TemporaryDirectory(prefix='ledger-stage-four-ui-') as temporary:
        base = Path(temporary); root = base / 'Office'; profile = base / 'profile'
        os.environ.update(environment(os.environ, root, profile)); os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from .locations import office
        office(root)
        from .qt_app import make_app, WorkbenchWindow
        from .change_sets_qt import show
        app = make_app(['ledger-stage-four-check']); host = WorkbenchWindow(root=root, restore=False)
        try:
            host.show(); tab = show(host); app.processEvents()
            if tab.workspace is not None: raise ValueError('UI smoke fixture unexpectedly imported user data')
            return {'state': 'PASSED', 'scope': 'Real Qt Changes screen opens without a model or file import', 'owner_display_walkthrough': 'PENDING'}
        finally: host.close(); app.processEvents()


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--child', nargs=5); parser.add_argument('--ui', action='store_true'); args = parser.parse_args()
    try:
        if args.child:
            mode, root, profile, home, expected = args.child; result = child(Path(root), Path(profile), Path(home), mode, json.loads(expected))
        else: result = ui_test() if args.ui else self_test()
        print(json.dumps(result, indent=2)); return 0
    except (ValueError, OSError, ImportError, subprocess.SubprocessError) as exc:
        print(json.dumps({'state': 'FAILED', 'error': str(exc)}, indent=2)); return 1


if __name__ == '__main__': raise SystemExit(main())
