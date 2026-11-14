"""The disposable workspace each attempt runs in, and the identity of everything a run depends on.

Every attempt gets its own folder with its own HOME, XDG folders, Graphite profile (ARC1_WORKBENCH_CONFIG_HOME),
Concern folder, workspace root and kernel database. The attempt's child process starts from a small, clean
environment (not the caller's), so nothing it does can reach the real user profile, the repository's .ledger or
the main checkout. Reset is "delete and rebuild": a new attempt never reuses an earlier attempt's folders.

Two seeds exist:
  base            an empty Office workspace built by Graphite itself (locations.office + Kernel + Session);
  after_hours_07  the owner's After Hours 07 backup, verified and restored with Graphite's own backup code.
The After Hours 07 backup is owner data and is not shipped: it is found under --fixtures (or the
GRAPHITE_CAMPAIGN_FIXTURES variable, or ~/Graphite_Campaign/fixtures), as a Graphite_Backup folder or the zip.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE_REVISION = 1   # bump when the way a seed is built changes
AH07_IDS = {
    'sheet': 'owner:db5f669f863d4c71b89fa7ba348957da',
    'calc_settled': '0e39bf65e24740a29a504a6be6e00885',
    'calc_startup': '500cd60ebe49411bb9b9e5bbe0570214',
    'claim_settled': 'f2a610f24ca84112a400e02d6ad04869',
    'pdf_item': 'c1d3fc85730d57bc35404c6065dbe1dc',
    'pdf_sha256': '2c60377d8dcf9c821c7d458d4ae944ddd84566c325114700c19ddcd76bbc375b',
}
KEEP_ENV = ('PATH', 'LANG', 'LC_ALL', 'TZ', 'TERM', 'GRAPHITE_APPEARANCE')      # the appearance a run starts in (0.8.2: a scene in Kasandra)


class Blocked(Exception):
    """A prerequisite the case needs is not present here; the message says which, in one sentence."""


# ---------------------------------------------------------------- the attempt's folders and environment

def attempt_environment(attempt):
    """A clean environment whose every per-user location is inside the attempt folder."""
    attempt = Path(attempt).absolute()
    home = attempt / 'home'
    env = {k: os.environ[k] for k in KEEP_ENV if k in os.environ}
    env.update(
        HOME=str(home), USER='campaign', LOGNAME='campaign',
        XDG_CONFIG_HOME=str(attempt / 'xdg/config'), XDG_DATA_HOME=str(attempt / 'xdg/data'),
        XDG_STATE_HOME=str(attempt / 'xdg/state'), XDG_CACHE_HOME=str(attempt / 'xdg/cache'),
        XDG_RUNTIME_DIR=str(attempt / 'xdg/runtime'), TMPDIR=str(attempt / 'tmp'),
        ARC1_WORKBENCH_CONFIG_HOME=str(attempt / 'profile'), ARC_LEDGER_CONCERN=str(home / 'Concern'),
        ARC_LEDGER_WORKSPACE=str(attempt / 'ws'), ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
        PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(REPO), QT_QPA_PLATFORM='offscreen', PYTHONHASHSEED='0')
    return env


def make_folders(attempt):
    attempt = Path(attempt)
    for sub in ('home', 'xdg/config', 'xdg/data', 'xdg/state', 'xdg/cache', 'xdg/runtime', 'tmp'):
        (attempt / sub).mkdir(parents=True, exist_ok=True)
    os.chmod(attempt / 'xdg/runtime', 0o700)


def check_isolation(attempt):
    """Run in the child before any Graphite import: every per-user path must sit inside the attempt."""
    attempt = Path(attempt).resolve()
    from workbench import locations, session
    found = {'config_dir': session.config_dir(), 'concern_home': locations.concern_home(),
             'home': Path.home(), 'workspace': Path(os.environ['ARC_LEDGER_WORKSPACE'])}
    outside = {k: str(v) for k, v in found.items() if attempt not in Path(v).resolve().parents}
    if outside:
        raise RuntimeError('ISOLATION_BROKEN: ' + json.dumps(outside))
    if REPO in attempt.parents or attempt == REPO:
        raise RuntimeError('ISOLATION_BROKEN: the attempt folder is inside the program folder')
    return {k: str(v) for k, v in found.items()}


# ---------------------------------------------------------------- seeds (run inside the attempt's child)

def base_workspace(attempt):
    """An empty Office workspace made by Graphite's own code; returns (kernel, owner principal)."""
    from workbench import ledger_control, locations
    from workbench.engineering_kernel import Kernel, operator
    from workbench.session import Session
    root = locations.office(Path(attempt) / 'ws')
    kernel = Kernel(root)
    session = Session(Path(attempt) / 'profile/session.json', root)
    session.save()
    ledger_control.bind(kernel, session)
    return kernel, operator()


def ah07_workspace(attempt, backup):
    """Verify and restore the After Hours 07 backup into the attempt's fresh workspace and profile."""
    from workbench import workspace_backup
    from workbench.engineering_kernel import Kernel, operator
    if backup is None:
        raise Blocked('The After Hours 07 backup (Graphite_After_Hours_07.zip or its Graphite_Backup folder) '
                      'was not found under --fixtures.')
    verified = workspace_backup.verify(Path(backup))
    restored = workspace_backup.restore(Path(backup), Path(attempt) / 'ws', Path(attempt) / 'profile')
    return Kernel(Path(restored.get('workspace', Path(attempt) / 'ws'))), operator(), {
        'verify_state': verified.get('state') if isinstance(verified, dict) else str(verified),
        'restore_state': restored.get('state')}


def state_digest(kernel):
    """Row counts per table and the sorted settings keys: a deterministic picture of a fresh seed."""
    with kernel.db() as db:
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        counts = {t: db.execute('SELECT count(*) FROM "%s"' % t).fetchone()[0] for t in tables}
        keys = [r[0] for r in db.execute('SELECT key FROM settings ORDER BY key')]
    picture = {'counts': counts, 'settings_keys': keys}
    return hashlib.sha256(json.dumps(picture, sort_keys=True).encode()).hexdigest(), picture


# ---------------------------------------------------------------- finding the owner's seed (run in the parent)

def fixtures_dir(arg=None):
    if arg:
        return Path(arg).expanduser().absolute()
    if os.environ.get('GRAPHITE_CAMPAIGN_FIXTURES'):
        return Path(os.environ['GRAPHITE_CAMPAIGN_FIXTURES']).expanduser().absolute()
    return Path.home() / 'Graphite_Campaign' / 'fixtures'


def ah07_available(folder):
    """Where the After Hours 07 backup is under `folder` (a Graphite_Backup folder or the zip), without unpacking."""
    folder = Path(folder)
    if not folder.is_dir():
        return None
    for candidate in [folder / 'after_hours_07' / 'Graphite_Backup', folder / 'Graphite_Backup',
                      *sorted(folder.glob('*/After_Hours_07/Graphite_Backup')),
                      *sorted(folder.glob('*/*/After_Hours_07/Graphite_Backup'))]:
        if (candidate / 'BACKUP.json').is_file():
            return candidate
    zips = sorted(folder.glob('*After_Hours_07*.zip'))
    return zips[0] if zips else None


def find_ah07(folder, unpack_into):
    """The Graphite_Backup folder of After Hours 07 under `folder`, unzipping the case zip once if needed."""
    folder = Path(folder)
    if not folder.is_dir():
        return None
    for candidate in [folder / 'after_hours_07' / 'Graphite_Backup', folder / 'Graphite_Backup',
                      *sorted(folder.glob('*/After_Hours_07/Graphite_Backup')),
                      *sorted(folder.glob('*/*/After_Hours_07/Graphite_Backup'))]:
        if (candidate / 'BACKUP.json').is_file():
            return candidate
    zips = sorted(folder.glob('*After_Hours_07*.zip'))
    if zips:
        target = Path(unpack_into)
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zips[0]) as z:
            for member in z.infolist():
                name = Path(member.filename)
                if name.is_absolute() or '..' in name.parts:
                    raise ValueError('unsafe path in the After Hours 07 zip: ' + member.filename)
            z.extractall(target)
        for candidate in sorted(target.rglob('Graphite_Backup')):
            if (candidate / 'BACKUP.json').is_file():
                return candidate
    return None


def tree_hash(folder):
    """SHA-256 over every file's relative path and content, in sorted order."""
    digest = hashlib.sha256()
    folder = Path(folder)
    for path in sorted(p for p in folder.rglob('*') if p.is_file()):
        digest.update(str(path.relative_to(folder)).encode() + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------- build, runtime and host identity

def _git(*args, repo=None):
    """git, read-only: --no-optional-locks (and GIT_OPTIONAL_LOCKS=0) so `status` never takes the index lock."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    try:
        return subprocess.run(['git', '--no-optional-locks', '-C', str(repo or REPO), *args], capture_output=True,
                              text=True, timeout=20, env=env).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def build_identity(repo=None):
    """The program's identity: commit, branch, version, and whether anything differs from the commit.

    tracked_changes is true when any path differs from the commit, untracked files included (a new file the
    commit does not hold changes what runs as much as an edited one)."""
    repo = Path(repo or REPO)
    version_py = repo / 'workbench/version.py'
    text = version_py.read_text() if version_py.is_file() else ''
    version = re.search(r"^VERSION\s*=\s*'([^']+)'", text, re.M)
    commit = _git('rev-parse', 'HEAD', repo=repo)
    raw = _git('status', '--porcelain', '--untracked-files=all', repo=repo) if commit else None
    if not commit or raw is None:      # no git, a folder outside one, or git timed out: unknown, never "unchanged"
        known = None;status = [];untracked = []
    else:
        status = raw.splitlines();untracked = [line for line in status if line.startswith('??')];known = bool(status)
    return {'git_commit': commit or 'unknown (no git history here)',
            'git_branch': _git('rev-parse', '--abbrev-ref', 'HEAD', repo=repo) if commit else None,
            'tracked_changes': known, 'changed_paths': len(status) - len(untracked) if known is not None else None,
            'untracked_paths': len(untracked) if known is not None else None, 'version': version[1] if version else None,
            'version_py_sha256': file_sha(version_py) if version_py.is_file() else None, 'program_folder': str(repo)}


def runtime_identity():
    try:
        from importlib.metadata import version
        pyside = version('PySide6')
    except Exception:  # noqa: BLE001 - recorded, not fatal
        pyside = None
    return {'python': sys.version.split()[0], 'python_executable': sys.executable, 'pyside6': pyside}


def memory(meminfo='/proc/meminfo', self_cgroup='/proc/self/cgroup', cgroup_root='/sys/fs/cgroup'):
    """Total and available RAM as this process can use it.

    Like workbench/brain_worker.memory_sample: start from /proc/meminfo, then let the process's own cgroup (and the
    cgroup root) lower both, cgroup v2 memory.max - memory.current. A cgroup v1 memory controller
    (memory.limit_in_bytes - memory.usage_in_bytes) is read the same way. Returns bytes and the basis used."""
    values = {}
    try:
        for line in Path(meminfo).read_text().splitlines():
            key, value = line.split(':', 1)
            if key in ('MemTotal', 'MemAvailable'):
                values[key] = int(value.split()[0]) * 1024
    except (OSError, ValueError):
        pass
    total, available = values.get('MemTotal'), values.get('MemAvailable')
    basis = ['/proc/meminfo MemAvailable'] if available is not None else []
    groups = {}
    try:
        for line in Path(self_cgroup).read_text().splitlines():
            number, controllers, path = line.split(':', 2)
            if number == '0' and controllers == '':
                groups['v2'] = path
            elif 'memory' in controllers.split(','):
                groups['v1'] = path
    except (OSError, ValueError):
        pass
    root = Path(cgroup_root)
    candidates = []
    if 'v2' in groups and '..' not in Path(groups['v2']).parts:
        candidates.append((root / groups['v2'].lstrip('/'), 'memory.max', 'memory.current', 'cgroup v2'))
    candidates.append((root, 'memory.max', 'memory.current', 'cgroup v2'))
    if 'v1' in groups and '..' not in Path(groups['v1']).parts:
        candidates.append((root / 'memory' / groups['v1'].lstrip('/'), 'memory.limit_in_bytes', 'memory.usage_in_bytes',
                           'cgroup v1'))
    source = Path(meminfo) if available is not None else None
    for folder, limit_name, usage_name, kind in candidates:
        try:
            limit = (folder / limit_name).read_text().strip()
            if not limit.isdigit() or int(limit) >= 2 ** 60:         # 'max', or v1's "no limit"
                continue
            room = max(0, int(limit) - int((folder / usage_name).read_text().strip()))
        except (OSError, ValueError):
            continue
        total = int(limit) if total is None else min(total, int(limit))
        if available is None or room < available:
            available, source = room, folder
            basis.append('%s limit less usage' % kind)
    return {'total_bytes': total, 'available_bytes': available, 'basis': basis[-1] if basis else 'NOT_MEASURED',
            'source': str(source) if source else None}


def host_summary():
    mem = memory()
    cpu = platform.processor() or platform.machine()
    try:
        cpu = next((l.split(':', 1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines()
                    if l.startswith('model name')), cpu)
    except OSError:
        pass
    limit = Path('/sys/fs/cgroup/memory.max')
    return {'system': platform.system(), 'release': platform.release(), 'machine': platform.machine(),
            'node_hash': hashlib.sha256(platform.node().encode()).hexdigest()[:12], 'cpu': cpu,
            'logical_cpus': os.cpu_count(), 'mem_total_bytes': mem['total_bytes'],
            'mem_available_bytes': mem['available_bytes'], 'mem_available_basis': mem['basis'],
            'mem_available_source': mem['source'],
            'cgroup_memory_max': limit.read_text().strip() if limit.is_file() else None}


def repo_ledger_stamp():
    """What the repository's own .ledger looks like, to show afterwards that a run did not touch it."""
    folder = REPO / '.ledger'
    if not folder.exists():
        return {'exists': False}
    files = sorted(p for p in folder.rglob('*') if p.is_file())
    return {'exists': True, 'files': len(files),
            'stamp': hashlib.sha256(json.dumps([[str(p.relative_to(folder)), p.stat().st_size, p.stat().st_mtime_ns]
                                                for p in files]).encode()).hexdigest()}
