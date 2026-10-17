"""ARC-1 Workbench shared engineering engine (R10). Importable without Qt.

One place decides what "Build", "Tests" and "Run" mean for the current work.
The Qt shell, the JSON-lines agent (`python arc1 agent`) and any future
JSON-RPC front end all ask this module for a command plan and then run the
same validated `arc1` CLI command, so a visual redesign cannot change what
automation does, and no front end can claim a result the CLI did not report.

Nothing here talks to hardware. Every plan runs on the host.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
GAMES_DIR = 'examples'

# Target id -> how to build and test it. "{project}" is a game project directory.
TARGETS = {
    'f133': {'label': 'F133 firmware', 'kind': 'firmware', 'short': 'F133',
             'build': ['firmware', 'image', '--target', 'f133'], 'test': ['firmware', 'test'],
             'note': 'Link-stage image: NOT BOOTABLE'},
    'd213': {'label': 'D213 firmware', 'kind': 'firmware', 'short': 'D213',
             'build': ['firmware', 'image', '--target', 'd213'], 'test': ['firmware', 'test'],
             'note': 'Link-stage image: NOT BOOTABLE'},
    'lcd': {'label': 'F133 LCD status service', 'kind': 'firmware', 'short': 'LCD',
            'build': ['firmware', 'build', '--target', 'status-lcd'], 'test': ['firmware', 'test'],
            'note': 'Object file only'},
    'game': {'label': 'Host game', 'kind': 'game', 'short': 'Game',
             'build': ['build', '{project}'], 'test': ['test', '{project}'],
             'note': 'Host simulation only'},
}
DEFAULT_TARGET = 'f133'
RUN_FRAMES = 120
RUN_DUMP = '0,30,60,90,119'

# Named operations shared with the agent interface (workbench/agent.py).
AGENT_ACTIONS = {
    'build.f133': TARGETS['f133']['build'],
    'build.d213': TARGETS['d213']['build'],
    'build.both': ['firmware', 'image', '--target', 'all'],
    'build.lcd': TARGETS['lcd']['build'],
    'test.firmware': ['firmware', 'test'],
    'test.game': ['test', 'examples/hello_arc1'],
    'build.game': ['build', 'examples/hello_arc1'],
    'inspect.hardware': ['hw', 'inspect'],
    'inspect.brand': ['brand'],
    'doctor': ['doctor'],
}

# The project navigator: logical areas, not the raw repository root.
NAVIGATOR = [
    ('Firmware', 'firmware', 'F133/D213 firmware sources, stage images and imports'),
    ('SDK', 'sdk', 'C API, host runtime, CLI and schemas'),
    ('FPGA', None, 'No FPGA sources in this project: the R10 RTL lives in the hardware handoff'),
    ('Games', GAMES_DIR, 'Game projects built and simulated on this PC'),
    ('Cartridges', 'cartridges', 'Verified .arc1cart archives'),
    ('Hardware', 'hardware', 'R10 hardware manifest and its cited sources (read-only evidence)'),
    ('Tests', 'tests', 'SDK and Workbench tests'),
    ('Docs', 'docs', 'Guides, interface notes and roadmap'),
]

LANGUAGES = {'.c': 'C11', '.h': 'C11 header', '.s': 'Assembly', '.S': 'Assembly', '.ld': 'Linker script',
             '.py': 'Python', '.md': 'Markdown', '.json': 'JSON', '.txt': 'Text', '.cmd': 'Batch',
             '.sh': 'Shell', '.yaml': 'YAML', '.yml': 'YAML', '.csv': 'CSV', '.sprite': 'Sprite',
             '.replay': 'Replay'}

SKIP_DIRS = {'__pycache__', '.git', 'build', 'reports'}
QUICK_OPEN_LIMIT = 4000


@dataclass
class Plan:
    """A host command the front end should run, and why it was chosen."""
    op: str                     # build | test | run
    target: str                 # key of TARGETS
    argv: list = field(default_factory=list)   # arguments after `arc1`
    project: str | None = None  # game project (relative path) for game plans
    label: str = ''
    reason: str = ''

    def command_line(self):
        return 'arc1 ' + ' '.join(self.argv)

    def process_args(self, root=ROOT):
        return [sys.executable, str(Path(root) / 'arc1'), *self.argv]


def rel(path, root=ROOT):
    return Path(os.path.relpath(Path(path).resolve(), Path(root).resolve())).as_posix()


def inside(path, root=ROOT):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def game_projects(root=ROOT):
    base = Path(root) / GAMES_DIR
    if not base.is_dir():
        return []
    return sorted(rel(p.parent, root) for p in base.glob('*/arc1.game.json') if not p.is_symlink())


def game_for(path, root=ROOT):
    """The game project a file belongs to, e.g. 'examples/hello_arc1', or None."""
    if path is None:
        return None
    path = Path(path) if Path(path).is_absolute() else Path(root) / path
    if not inside(path, root):
        return None
    parts = Path(rel(path, root)).parts
    if len(parts) >= 2 and parts[0] == GAMES_DIR and (Path(root) / parts[0] / parts[1] / 'arc1.game.json').is_file():
        return '%s/%s' % (parts[0], parts[1])
    return None


def plan(op, target='f133', active_path=None, last_game=None, root=ROOT):
    """Decides what Build/Tests/Run do for the current work.

    An open file inside a game project builds and tests that game, whatever
    target is selected; otherwise the selected firmware target is used. Run
    always means the host simulator for a game project."""
    if op not in ('build', 'test', 'run'):
        raise ValueError('unknown operation %r' % op)
    if target not in TARGETS:
        raise ValueError('unknown target %r' % target)
    game = game_for(active_path, root)
    games = game_projects(root)
    if op == 'run' or TARGETS[target]['kind'] == 'game' or game:
        project = game or (last_game if last_game in games else None) or (games[0] if games else None)
        if project is None:
            raise ValueError('no game project exists under %s/' % GAMES_DIR)
        if game:
            why = 'the open file belongs to %s' % project
        elif op == 'run':
            why = 'Run uses the host simulator for a game project'
        else:
            why = 'the Host game target is selected'
        name = Path(project).name
        if op == 'run':
            argv = ['sim', project, '--frames', str(RUN_FRAMES), '--dump', RUN_DUMP]
            label = 'Run %s in the host simulator' % name
        else:
            argv = [a.replace('{project}', project) for a in TARGETS['game'][op]]
            label = '%s host game %s' % ('Build' if op == 'build' else 'Test', name)
        return Plan(op, 'game', argv, project, label, why)
    t = TARGETS[target]
    return Plan(op, target, list(t[op]), None,
                '%s %s' % ('Build' if op == 'build' else 'Test', t['label']),
                'the %s target is selected' % t['label'])


def build_log(plan_, root=ROOT):
    """Where a host-game build writes compiler output (the CLI prints only a summary)."""
    if plan_.target == 'game' and plan_.project:
        return Path(root) / plan_.project / 'build' / 'logs' / 'build.log'
    return None


def collect_output(plan_, cli_output, started_at, root=ROOT):
    """CLI output plus the compiler log a game build wrote during this run."""
    log = build_log(plan_, root)
    text = cli_output
    if log is not None and log.is_file() and log.stat().st_mtime >= started_at - 1:
        try:
            text += '\n--- %s ---\n%s' % (rel(log, root), log.read_text(encoding='utf-8', errors='replace'))
        except OSError:
            pass
    return text


_PATH_TAIL = re.compile(r'[\w./\\:-]+\.(?:c|h|s|S|ld|cpp|hpp)$')


def resolve_problem_path(source, plan_=None, root=ROOT):
    """Maps a compiler's file reference to a file inside the project, or None.

    Compilers report paths relative to their working directory (a game project
    for host builds), absolute paths (firmware builds), or with a prefix the
    CLI adds ("FAIL FW-BUILD compiler returned 1: /abs/file.c")."""
    root = Path(root)
    candidates = [source.strip()]
    m = _PATH_TAIL.search(source.strip())
    if m:
        candidates.append(m.group(0))
    bases = [root]
    if plan_ is not None and plan_.project:
        bases.insert(0, root / plan_.project)
    for cand in candidates:
        p = Path(cand.replace('\\', '/')) if not re.match(r'^[A-Za-z]:\\', cand) else Path(cand)
        options = [p] if p.is_absolute() else [b / p for b in bases]
        for o in options:
            try:
                if o.is_file() and inside(o, root):
                    return o.resolve()
            except OSError:
                continue
    return None


def language_for(path):
    if path is None:
        return ''
    p = Path(path)
    return LANGUAGES.get(p.suffix, LANGUAGES.get(p.suffix.lower(), 'Text'))


def walk_files(root=ROOT, limit=QUICK_OPEN_LIMIT):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.'))
        for f in sorted(filenames):
            if f.startswith('.') or f.endswith('.pyc'):
                continue
            out.append(rel(Path(dirpath) / f, root))
            if len(out) >= limit:
                return out
    return out


def find_files(query, root=ROOT, limit=50, files=None):
    """Quick Open ranking: exact name, name prefix, name substring, path substring."""
    q = query.strip().lower().replace('\\', '/')
    files = files if files is not None else walk_files(root)
    if not q:
        return files[:limit]
    scored = []
    for f in files:
        name = f.rsplit('/', 1)[-1].lower()
        if name == q:
            score = 0
        elif name.startswith(q):
            score = 1
        elif q in name:
            score = 2
        elif q in f.lower():
            score = 3
        else:
            continue
        scored.append((score, len(f), f))
    return [f for _, _, f in sorted(scored)[:limit]]


def device_status():
    """Truthful hardware status for every front end. There is no device transport."""
    return {'connected': False, 'text': 'No physical device connected', 'badge': 'HOST SIM · BOARD OFFLINE'}
