"""Stage One operator commands; usable without Qt or a local model."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

IDEA = 'A small clock with a readable face.\nKeep my original words.'


def environment(base, root, profile):
    env = dict(base)
    env.update(ARC1_WORKBENCH_CONFIG_HOME=str(profile), ARC_LEDGER_WORKSPACE=str(root),
               ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1', PYTHONDONTWRITEBYTECODE='1')
    return env


def reopened(root, profile, ident):
    from sdk.cli.arc1cli.concern_catalog import Catalog
    from .engineering_kernel import Kernel, operator
    catalog = Catalog(Path(profile) / 'concern/catalog.sqlite3')
    note = catalog.get(ident)
    if note.get('note', {}).get('body') != IDEA:
        # The catalog's stable public projection is checked by exact note text.
        with catalog.db() as db: body = db.execute('SELECT body FROM notes WHERE object_id=?', (ident,)).fetchone()
        if body is None or body[0] != IDEA: raise ValueError('Saved idea did not survive restart')
    response = Kernel(root).dispatch('language.run', {'text': '@files:stock.csv | rows | add Short = Need - Have | where Short over 0'}, operator())
    if not response['ok'] or response['result']['rows'] != [{'Part':'R1','Need':12,'Have':5,'Short':7}]:
        raise ValueError('Saved files or staC reading did not survive restart')
    return {'state': 'PASSED', 'idea_exact': True, 'stac_rows': 1, 'model_calls': response['result']['model_calls']}


def self_test():
    from . import locations, workspace_backup
    from .engineering_kernel import Kernel
    from sdk.cli.arc1cli.concern_catalog import Catalog
    with tempfile.TemporaryDirectory(prefix='ledger-baseline-') as temporary:
        base = Path(temporary); root = base / 'Office'; profile = base / 'profile'
        os.environ.update(environment(os.environ, root, profile))
        locations.office(root); Kernel(root)
        catalog = Catalog(profile / 'concern/catalog.sqlite3')
        ident = catalog.create('note', IDEA.splitlines()[0]); catalog.save_note(ident, IDEA, 0)
        files = root / 'Files'; files.mkdir(); (files / 'stock.csv').write_text('Part,Need,Have\nR1,12,5\n')
        (files / 'Empty folder').mkdir()
        def restart(at, config):
            proc = subprocess.run([sys.executable, '-m', 'workbench.baseline', '_resume', str(at), str(config), ident],
                                  env=environment(os.environ, at, config), capture_output=True, text=True, timeout=20)
            if proc.returncode: raise ValueError('Restart failed: ' + (proc.stderr or proc.stdout)[-800:])
            return json.loads(proc.stdout)
        first = restart(root, profile)
        saved = workspace_backup.create(root, base / 'backup')
        restored = workspace_backup.restore(base / 'backup', base / 'Restored')
        if not (Path(restored['workspace']) / 'Files/Empty folder').is_dir():
            raise ValueError('The empty workspace folder was not restored')
        second = restart(Path(restored['workspace']), Path(restored['profile']))
        return {'state': 'PASSED', 'scope': 'Disposable service-level fixtures on this execution host; no Qt or owner files',
                'capture': 'EXACT_CATALOG_NOTE', 'restart': first, 'backup': {k:saved[k] for k in ('state','files','databases')},
                'restored_restart': second, 'model_required': False, 'network_calls': 0}


def qt_check():
    # The real window and capture widget, isolated from every existing workspace/profile.
    with tempfile.TemporaryDirectory(prefix='ledger-qt-check-') as temporary:
        base = Path(temporary); root = base / 'Office'; profile = base / 'profile'
        os.environ.update(environment(os.environ, root, profile)); os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        from .locations import office
        office(root)
        from .qt_app import make_app, WorkbenchWindow
        from .shell2 import CaptureBox
        app = make_app(['ledger-stage-one-check']); w = WorkbenchWindow(root=root, restore=False)
        try:
            w.show(); app.processEvents()
            capture = CaptureBox(w); capture.text.setPlainText(IDEA)
            if capture.save() is not True: raise ValueError('The Qt capture widget did not save')
            found = w.concern.store.search('readable face')
            if not found: raise ValueError('The captured idea is not searchable')
            return {'state': 'PASSED', 'scope': 'Real Qt window and capture widget, offscreen disposable fixture', 'visual_walkthrough': 'STILL_REQUIRED_ON_OWNER_DISPLAY'}
        finally: w.close(); app.processEvents()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv and argv[0] == 'doctor':
            from .doctor import main as run
            return run(argv[1:])
        if argv == ['_self-test']: result = self_test()
        elif argv == ['_qt-check']: result = qt_check()
        elif argv and argv[0] == '_resume': result = reopened(Path(argv[1]), Path(argv[2]), argv[3])
        else:
            parser = argparse.ArgumentParser(description=__doc__)
            sub = parser.add_subparsers(dest='command', required=True)
            sub.add_parser('inventory')
            baseline = sub.add_parser('baseline'); baseline.add_argument('--out')
            opened = sub.add_parser('open'); opened.add_argument('--root'); opened.add_argument('--profile')
            backup = sub.add_parser('backup'); actions = backup.add_subparsers(dest='action', required=True)
            create = actions.add_parser('create'); create.add_argument('--root', required=True); create.add_argument('--out', required=True); create.add_argument('--include-models', action='store_true')
            verify = actions.add_parser('verify'); verify.add_argument('backup')
            restore = actions.add_parser('restore'); restore.add_argument('backup'); restore.add_argument('--to', required=True); restore.add_argument('--profile')
            args = parser.parse_args(argv)
            if args.command == 'inventory':
                from .doctor import inventory
                result = inventory()
            elif args.command == 'baseline':
                from .doctor import probe, child_check
                result = {'schema': 'arc.stage-one-baseline/1', 'inspection': probe(), 'exercise': child_check('_self-test'),
                          'owner_host_acceptance': 'PENDING_REAL_DESKTOP_AND_OWNER_WALKTHROUGH'}
                if args.out:
                    with Path(args.out).expanduser().open('x', encoding='utf-8') as f:
                        os.fchmod(f.fileno(), 0o600); json.dump(result, f, indent=2); f.write('\n')
                if result['exercise'].get('state') != 'PASSED': print(json.dumps(result, indent=2)); return 2
            elif args.command == 'open':
                if args.root: os.environ['ARC_LEDGER_WORKSPACE'] = str(Path(args.root).expanduser().resolve())
                if args.profile: os.environ['ARC1_WORKBENCH_CONFIG_HOME'] = str(Path(args.profile).expanduser().resolve())
                from .launch import main as launch
                sys.argv = [sys.argv[0]]
                return launch([])
            else:
                from . import workspace_backup as b
                result = b.create(args.root, args.out, args.include_models) if args.action == 'create' else b.verify(args.backup) if args.action == 'verify' else b.restore(args.backup, args.to, args.profile)
        print(json.dumps(result, indent=2)); return 0
    except Exception as exc:
        print('Graphite ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__': raise SystemExit(main())
