"""Where Ledger's program is, separately from the workspace it works in.

A *workspace* is the folder Ledger opens. It holds the project's files (if one
is attached) and Ledger's live state in ``.ledger``. The *program* is Ledger's
own code, documents, art and pinned engine.

One rule keeps the historic layout working: a root that contains the program is
also the program (the program-only edition and every copied test tree). Any
other root is a workspace in the concern folder, and the program is the
installed Ledger folder this module was imported from.

  python3 -m workbench.locations status
  python3 -m workbench.locations create [FOLDER]
  python3 -m workbench.locations office [FOLDER]
  python3 -m workbench.locations move-state [--to FOLDER]
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

PACKAGE = Path(__file__).resolve().parents[1]
MARKER = 'LEDGER_WORKSPACE.json'
SCHEMA = 'arc.ledger-workspace/1'
KINDS = ('NO_PROJECT', 'PROJECT')


def contains_program(root):
    return (Path(root) / 'workbench' / 'engineering_kernel.py').is_file()


def program(root=None):
    """The program folder that serves ``root``."""
    if root is not None and contains_program(root):return Path(root).resolve()
    return PACKAGE


def child_env(root, base=None):
    """Environment for a Ledger child process run from ``root``: the program stays importable."""
    env = dict(os.environ if base is None else base)
    entries = [str(program(root))] + [p for p in env.get('PYTHONPATH', '').split(os.pathsep) if p and p != str(program(root))]
    env['PYTHONPATH'] = os.pathsep.join(entries)
    return env


def concern_home():
    return Path(os.environ.get('ARC_LEDGER_CONCERN') or Path.home() / 'Concern')


def default_root():
    """The folder Ledger opens when none is named.

    Once the concern workspace exists it always wins, so state that a check or
    test creates beside the program can never pull a moved installation back.
    An installation that has not moved yet keeps its state beside the program;
    nothing is relocated implicitly.
    """
    named = os.environ.get('ARC_LEDGER_WORKSPACE')
    if named:return Path(named).resolve()
    if os.environ.get('ARC_LEDGER_EDITION') == 'office':return office()
    home = concern_home() / 'Ledger'
    if (home / MARKER).is_file():return home.resolve()
    if (PACKAGE / '.ledger').is_dir():return PACKAGE
    return ensure_workspace(home)


INGRESS, OLDER_INGRESS = 'Ingress', ('Arrived', 'Inbox')  # AGENT-01 (owner, D28): files come in through "Ingress"; "Arrived" (4.2) and "Inbox" (4.1) were its earlier names
ARRIVED, OLD_ARRIVED = INGRESS, OLDER_INGRESS[0]  # kept for callers written against the 4.2 names


def move_once(old, new):
    """Move an older folder's contents under the new name once; nothing is overwritten or lost: a name already present
    stays in the old folder, which is kept until it is empty. Returns False when the move could not be made."""
    if not (old.is_dir() and not old.is_symlink()):return True
    try:
        if not new.exists():old.rename(new)
        else:
            for item in sorted(old.iterdir()):
                if not (new / item.name).exists():item.rename(new / item.name)
            if not any(old.iterdir()):old.rmdir()
    except OSError:return new.is_dir()
    return True


def ingress(root, create=False):
    """The folder where files come in (the owner's word: Ingress). An earlier "Arrived" or "Inbox" is moved here once."""
    root = Path(root);new = root / INGRESS
    for name in OLDER_INGRESS:
        if not move_once(root / name, new) and not new.is_dir():return root / name  # could not move it: keep using the old folder rather than lose sight of it
    if create:new.mkdir(mode=0o700, exist_ok=True)
    return new


arrived = ingress  # the 4.2 name of the same function


def office(path=None):
    """The empty Office: a workspace with no project and an Ingress folder for the files that come in."""
    root = ensure_workspace(Path(path) if path else concern_home() / 'Office', name='Office')
    ingress(root, create=True)
    return root


def marker(root):
    path = Path(root) / MARKER
    if not path.is_file():return None
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema') != SCHEMA or value.get('kind') not in KINDS:
        raise ValueError('Unsupported Graphite workspace marker: ' + str(path))
    return value


def ensure_workspace(path, kind='NO_PROJECT', name=None):
    path = Path(path).resolve()
    if any(contains_program(p) for p in (path, *path.parents)) or path.is_relative_to(PACKAGE):
        raise ValueError('A workspace must be outside the Graphite program folder')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if marker(path) is None:
        record = {'schema': SCHEMA, 'kind': kind, 'name': name or path.name}
        temporary = path / (MARKER + '.tmp')
        temporary.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, path / MARKER)
    return path


def status(root=None):
    root = Path(root).resolve() if root else default_root()
    value = None if contains_program(root) else marker(root)
    return {'schema': 'arc.ledger-locations/1', 'workspace': str(root), 'program': str(program(root)),
            'layout': 'PROGRAM_AND_WORKSPACE_TOGETHER' if contains_program(root) else 'SEPARATE_WORKSPACE',
            'workspace_kind': value['kind'] if value else None, 'state': str(root / '.ledger'),
            'state_present': (root / '.ledger').is_dir(), 'concern_home': str(concern_home())}


def move_state(target=None):
    """Move live state from beside the program into a workspace, via a verified backup."""
    from . import state_backup
    source = PACKAGE
    if not (source / '.ledger').is_dir():raise ValueError('No live state beside the program; nothing to move')
    target = ensure_workspace(Path(target) if target else concern_home() / 'Ledger')
    if (target / '.ledger').exists():raise ValueError('The workspace already has live state: ' + str(target / '.ledger'))
    backup = state_backup.create(source)
    restored = state_backup.restore(backup['backup'], target, areas=('ledger',))
    aside = source / '.ledger'
    retired = aside.with_name('.ledger.moved-to-workspace')
    aside.rename(retired)
    return {'state': 'MOVED', 'workspace': str(target), 'backup': backup['backup'],
            'previous_state_kept_at': str(retired), 'restore': restored}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status').add_argument('--root')
    sub.add_parser('create').add_argument('folder', nargs='?')
    sub.add_parser('office').add_argument('folder', nargs='?')
    sub.add_parser('move-state').add_argument('--to')
    args = parser.parse_args(argv)
    try:
        if args.command == 'status':result = status(args.root)
        elif args.command == 'create':result = status(ensure_workspace(args.folder or concern_home() / 'Ledger'))
        elif args.command == 'office':result = status(office(args.folder))
        else:result = move_state(args.to)
    except (ValueError, OSError) as exc:
        print('Graphite locations: ' + str(exc), file=sys.stderr); return 1
    print(json.dumps(result, indent=2)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
