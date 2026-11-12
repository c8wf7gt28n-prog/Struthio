"""Shipped diagnostics. Ordinary inspection creates no workspace and starts no services or models."""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys
import time
from . import locations


def chosen_root(value=None):
    if value: return Path(value).expanduser().resolve()
    if os.environ.get('ARC_LEDGER_WORKSPACE'): return Path(os.environ['ARC_LEDGER_WORKSPACE']).expanduser().resolve()
    home = locations.concern_home()
    if os.environ.get('ARC_LEDGER_EDITION') == 'office': return (home / 'Office').resolve()
    if (home / 'Ledger' / locations.MARKER).is_file(): return (home / 'Ledger').resolve()
    if (locations.PACKAGE / '.ledger').is_dir(): return locations.PACKAGE
    return (home / 'Office').resolve()


def inventory():
    from .engineering_kernel import CAPABILITIES, TOOLS
    from .engineering_cli import schemas
    definitions = schemas()
    if set(definitions) != set(CAPABILITIES): raise ValueError('Capability registry and CLI schemas differ')
    rows = [{'operation': op, 'scope': scope, 'arguments': definitions[op]} for op, scope in sorted(CAPABILITIES.items())]
    raw = json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()
    return {'schema': 'arc.baseline-inventory/1', 'operations': rows, 'job_tools': sorted(TOOLS),
            'operation_count': len(rows), 'schema_digest': hashlib.sha256(raw).hexdigest(),
            'storage': {'workspace': 'LEDGER_WORKSPACE.json; Files/; Arrived/; .ledger/',
                        'kernel': '.ledger/engineering.sqlite3', 'catalog': 'PROFILE/concern/catalog.sqlite3',
                        'profile': 'Selected session profile; settings, catalogs, notes and model registration',
                        'external': 'Original files and externally registered model weights are separate'},
            'qualification': 'Registry and schemas only; no operation is executed.'}


def database(path):
    if not path.exists(): return {'state': 'NOT_CREATED'}
    if path.is_symlink() or not path.is_file(): return {'state': 'INVALID_PATH'}
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)
    deadline = time.monotonic() + 5
    db.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 1000)
    try:
        check = db.execute('PRAGMA quick_check').fetchone()[0]
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {'state': 'OK' if check == 'ok' else 'DAMAGED', 'quick_check': check,
                'user_version': db.execute('PRAGMA user_version').fetchone()[0], 'tables': tables}
    finally: db.close()


def dependencies():
    rows = []
    for name, pin in (('PySide6', '6.8.3'), ('cryptography', '50.0.2')):
        try: version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: version = None
        rows.append({'package': name, 'expected': pin, 'installed': version,
                     'state': 'PINNED' if version == pin else 'MISSING' if version is None else 'DIFFERENT_VERSION'})
    return rows


def probe(root=None):
    from . import brain_runtime, stacy_foundation
    from .session import config_dir
    from .release_integrity import verify
    from .version import VERSION
    root = chosen_root(root); profile = config_dir().expanduser().resolve()
    rows, errors = {}, []
    def ranked_search():
        with closing(sqlite3.connect(':memory:')) as db, db:
            db.execute('CREATE VIRTUAL TABLE terms USING fts5(text)')
            db.execute('INSERT INTO terms VALUES(?)', ('Ledger sources',))
            score = db.execute('SELECT bm25(terms) FROM terms WHERE terms MATCH ?', ('Ledger',)).fetchone()[0]
        return {'state': 'AVAILABLE', 'engine': 'SQLITE_FTS5_BM25', 'sample_score': score, 'persistent_files': 0}
    for label, action in (
        ('payload', lambda: verify(locations.PACKAGE)),
        ('foundation', lambda: stacy_foundation.seed_status(locations.PACKAGE)),
        ('inventory', inventory),
        ('ranked_search', ranked_search),
        ('kernel_database', lambda: database(root / '.ledger/engineering.sqlite3')),
        ('catalog_database', lambda: database(profile / 'concern/catalog.sqlite3')),
    ):
        try: rows[label] = action()
        except Exception as exc: rows[label] = {'state': 'ERROR', 'reason': str(exc)[:350]}; errors.append(label)
    if 'inventory' in rows and 'operations' in rows['inventory']:
        value = rows['inventory']; rows['inventory'] = {k: value[k] for k in ('schema', 'operation_count', 'schema_digest', 'storage')}
    deps = dependencies()
    if not (3, 11) <= sys.version_info[:2] < (3, 14): errors.append('python_version')
    if any(r['state'] != 'PINNED' for r in deps): errors.append('desktop_dependencies')
    if rows['payload'].get('state') != 'VERIFIED': errors.append('payload')
    if rows['foundation'].get('state') != 'VERIFIED_SOURCE_BINDINGS': errors.append('foundation')
    if rows['ranked_search'].get('state') != 'AVAILABLE': errors.append('ranked_search')
    for name in ('kernel_database', 'catalog_database'):
        if rows[name].get('state') not in ('OK', 'NOT_CREATED'): errors.append(name)
    try:
        from .confine import status
        confinement = {**status(), 'tested_by_this_report': False,
                       'notice': 'Availability report only. A protected run may still be refused on this host.'}
    except Exception as exc: confinement = {'available': False, 'reason': str(exc)[:200], 'tested_by_this_report': False}
    existing = root
    while not existing.exists() and existing != existing.parent: existing = existing.parent
    return {'schema': 'arc.ledger-doctor/1', 'version': VERSION,
            'state': 'READY_FOR_DESKTOP_CHECK' if not errors else 'NEEDS_ATTENTION', 'attention': sorted(set(errors)),
            'workspace': str(root), 'workspace_exists': root.is_dir(), 'profile': str(profile),
            'python': platform.python_version(), 'dependencies': deps, **rows,
            'host': brain_runtime.host(), 'free_bytes': shutil.disk_usage(existing).free,
            'runtime': {k:v for k,v in brain_runtime.status(locations.PACKAGE).items() if k != 'pin'},
            'model': {'state': 'NOT_STARTED_OR_QUALIFIED_BY_DOCTOR', 'required_for_idea_capture': False},
            'confinement': confinement, 'physical_hardware': 'NOT_QUALIFIED',
            'owner_host': 'NOT_ASSUMED_THIS_IS_THE_OWNER_HOST', 'network_calls': 0,
            'desktop': 'NOT_OPENED', 'note': 'Inspection starts no model, service, or engineering job.'}


def child_check(command, timeout=45):
    env = dict(os.environ); env['PYTHONDONTWRITEBYTECODE'] = '1'
    try:
        p = subprocess.run([sys.executable, '-m', 'workbench.baseline', command], cwd=locations.PACKAGE,
                           env=env, capture_output=True, text=True, timeout=timeout)
        if p.returncode == 0: return json.loads(p.stdout)
        return {'state': 'FAILED', 'exit': p.returncode, 'reason': (p.stderr or p.stdout)[-1800:]}
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        return {'state': 'FAILED', 'reason': str(exc)[:400]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root'); parser.add_argument('--json', action='store_true')
    parser.add_argument('--self-test', action='store_true', help='Use only disposable workspace and profile fixtures')
    parser.add_argument('--qt-check', action='store_true', help='Exercise the real Qt capture widget in a disposable offscreen window')
    parser.add_argument('--out', help='Write a NEW JSON report file')
    args = parser.parse_args(argv)
    try:
        result = probe(args.root)
        if args.self_test: result['self_test'] = child_check('_self-test')
        if args.qt_check: result['desktop'] = child_check('_qt-check', 60)
        if args.out:
            with Path(args.out).expanduser().open('x', encoding='utf-8') as f:
                os.fchmod(f.fileno(), 0o600); json.dump(result, f, indent=2); f.write('\n')
        if args.json: print(json.dumps(result, indent=2))
        else:
            print('Graphite ' + result['version'] + ' · ' + result['state'])
            for name in ('payload', 'foundation', 'kernel_database', 'catalog_database'):
                print(name.replace('_', ' ') + ': ' + result[name]['state'])
            print('Registered operations: ' + str(result['inventory'].get('operation_count', 'unavailable')))
            print('Ranked local search: ' + result['ranked_search']['state'])
            for d in result['dependencies']: print(d['package'] + ': ' + d['state'] + ' (expected ' + d['expected'] + ')')
            if args.self_test: print('Disposable save / restart / restore: ' + result['self_test']['state'])
            if args.qt_check: print('Disposable Qt check: ' + result['desktop']['state'])
            print('No model or physical hardware was qualified. Use --json for measurements and details.')
        failed = any(result.get(k, {}).get('state') != 'PASSED' for k in ('self_test',) if k in result)
        if args.qt_check and result['desktop'].get('state') != 'PASSED': failed = True
        return 2 if failed or result['attention'] else 0
    except (ValueError, OSError, KeyError) as exc:
        print('Graphite doctor: ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__': raise SystemExit(main())
