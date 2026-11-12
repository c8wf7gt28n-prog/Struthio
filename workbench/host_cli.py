"""Local background-service controls and a Debian systemd user-unit generator."""
from __future__ import annotations
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys
import time
from .host_client import HostClient, HostUnavailable, ensure


def quoted(value):
    text = str(value)
    if any(ord(c) < 32 or ord(c) == 127 for c in text):
        raise ValueError('Control characters are not supported in a service path')
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%').replace('$', '$$') + '"'


def user_unit(root, python=None, profile=None):
    from .session import config_dir
    root = Path(root).resolve()
    python = Path(python or sys.executable).absolute()
    profile = Path(profile or config_dir()).absolute()
    return '\n'.join((
        '[Unit]', 'Description=Ledger background coordinator',
        'StartLimitIntervalSec=60', 'StartLimitBurst=5', '', '[Service]', 'Type=exec',
        'WorkingDirectory=' + str(root).replace('%', '%%'),
        'ExecStart=' + quoted(python) + ' -m workbench.host_service --root ' + quoted(root),
        'Environment=' + quoted('ARC1_WORKBENCH_CONFIG_HOME=' + str(profile)),
        'Environment=' + quoted('PYTHONPATH=' + str(__import__('workbench.locations',fromlist=['program']).program(root))),
        'Environment=ARC_LEDGER_SUPERVISION=systemd-user',
        'Restart=on-failure', 'RestartSec=2', 'TimeoutStopSec=45',
        'KillMode=mixed', 'UMask=0077', 'NoNewPrivileges=yes', '',
        '[Install]', 'WantedBy=default.target', ''))


def wait_stopped(client, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try: client.rpc('status', timeout=.5)
        except HostUnavailable:
            if not client.endpoint_path.exists(): return
        time.sleep(.04)
    raise HostUnavailable('Service has not confirmed shutdown; inspect it before continuing')


def offline_update(client, ident, principal):
    """Existing staged update, after client closure and exclusive service exit."""
    from . import update_service
    from .engineering_kernel import Kernel
    update_service.ensure_closed(client)
    client.rpc('shutdown', principal=principal)
    wait_stopped(client)
    fd = os.open(client.state / 'service/coordinator.lock', os.O_RDWR | os.O_NOFOLLOW)
    previous = os.environ.get('ARC_LEDGER_EMBEDDED')
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.environ['ARC_LEDGER_EMBEDDED'] = '1'
        return update_service.apply_staged(Kernel(client.root), ident, principal)
    finally:
        if previous is None: os.environ.pop('ARC_LEDGER_EMBEDDED', None)
        else: os.environ['ARC_LEDGER_EMBEDDED'] = previous
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=None)
    parser.add_argument('command', choices=('start', 'status', 'stop', 'master-stop', 'unit'))
    parser.add_argument('--output', type=Path, help='Create a new unit file; never overwrite an existing file')
    args = parser.parse_args(argv)
    if args.root is None:
        from .locations import default_root
        args.root = default_root()
    try:
        if args.command == 'unit':
            text = user_unit(args.root)
            if args.output:
                with args.output.open('x', encoding='utf-8') as stream: stream.write(text)
                args.output.chmod(0o600)
            else: print(text, end='')
            return 0
        client = ensure(args.root) if args.command == 'start' else HostClient(args.root)
        if args.command in ('start', 'status'): result = client.rpc('status')
        elif args.command == 'master-stop': result = client.rpc('master_stop', timeout=45)
        else:
            result = client.rpc('shutdown'); wait_stopped(client)
            from .work_trail import work_status
            result = {**result, 'state': 'STOPPED', 'work_remains_held': work_status(client)['held']}
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({'state': 'UNAVAILABLE', 'message': str(exc)})); return 1


if __name__ == '__main__':
    raise SystemExit(main())
