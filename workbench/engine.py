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

def engineering(root=ROOT):
    """Authoritative durable services used by desktop, JSONL, CLI, MCP and PWA."""
    from .host_client import engineering as shared
    return shared(root)
GAMES_DIR = 'examples'
ARCADE_DIR = 'examples/struthio_arcade'

# One source catalog for the Workbench's own tree and the read-only agent
# inspector. These are navigation targets, not extra command entry points.
WORKBENCH_SOURCE_MAP = (
    ('interface', 'Interface & Layout', ('workbench/qt_app.py', 'workbench/qt_theme.py',
                                       'docs/HARDWARE_STATUS.md',
                                       'docs/handoffs/ARC1_Workbench_v0_5_CODEX_IMPLEMENTATION_HANDOFF.txt')),
    ('source', 'Source', ('workbench/engine.py', 'workbench/fileops.py',
                          'workbench/output_router.py', 'workbench/readiness.py')),
    ('clip', 'Slate', ('workbench/clip.py',)),
    ('tools', 'Tool Integrations', ('workbench/agent.py', 'workbench/arcade_tools.py',
                                   'workbench/board_view.py', 'workbench/nor_staging.py', 'workbench/tool_inventory.py')),
    ('simulator', 'Simulator', ('sdk/cli/arc1cli/systemsim.py',
                               'workbench/dashboard.py')),
    ('tests', 'Tests', ('tests/test_r10_workbench.py', 'tests/test_r10_clip.py',
                          'workbench/tests/test_nor_staging.py',
                          'workbench/tests/test_r1011_discovery_readiness.py')),
    ('settings', 'Settings', ('workbench/session.py',)),
    ('recovery', 'Update & Recovery', ('workbench/setup_arc1.py', 'workbench/launch.py')),
)


def workbench_sections(root=ROOT):
    """Existing, in-project source paths shared by Qt and the agent inspector."""
    root = Path(root).resolve()
    sections = []
    for section_id, label, names in WORKBENCH_SOURCE_MAP:
        paths = [name for name in names if (root / name).is_file()
                 and not (root / name).is_symlink() and inside(root / name, root)]
        if paths:
            sections.append({'id': section_id, 'label': label, 'primary': paths[0], 'files': paths})
    return sections

# Target id -> how to build and test it. "{project}" is a game project directory.
TARGETS = {
    'f133': {'label': 'F133 boot firmware', 'kind': 'compact', 'short': 'F133',
             'build': ['compact', 'check', '--target', 'f133'], 'test': ['compact', 'check', '--target', 'f133'],
             'note': 'R10 host tests and freestanding compile; no bootable image'},
    'd213': {'label': 'D213 graphics firmware', 'kind': 'compact', 'short': 'D213',
             'build': ['compact', 'check', '--target', 'd213'], 'test': ['compact', 'check', '--target', 'd213'],
             'note': 'R10 D213 driver and flashless-start host tests; no physical programming'},
    'usb': {'label': 'F133 USB host + hub', 'kind': 'compact', 'short': 'USB',
            'build': ['compact', 'check', '--target', 'usb'], 'test': ['compact', 'check', '--target', 'usb'],
            'note': 'EHCI0 backend and hub port power on SIMULATED controller models; no USB hardware'},
    'power': {'label': 'Power admission control', 'kind': 'compact', 'short': 'Power',
              'build': ['compact', 'check', '--target', 'power'], 'test': ['compact', 'check', '--target', 'power'],
              'note': 'Load admission on SIMULATED rail observations; rails NOT INSTRUMENTED'},
    'game': {'label': 'Host game', 'kind': 'game', 'short': 'Game',
             'build': ['build', '{project}'], 'test': ['test', '{project}'],
             'note': 'Host simulation only'},
    'arcade': {'label': 'STRUTHIO Arcade 1.8', 'kind': 'browser', 'short': 'Arcade',
               'build': ['build'], 'test': ['test'],
               'note': 'Browser source and localhost preview; no ARC-1 binary'},
    'fpga45': {'label': 'FPGA45 graphics', 'kind': 'compact', 'short': 'FPGA45',
               'build': ['compact', 'check', '--target', 'fpga45'], 'test': ['compact', 'check', '--target', 'fpga45'],
               'note': 'R10 RTL simulation/synthesis; no board programming'},
    'fpga12': {'label': 'FPGA12 support', 'kind': 'compact', 'short': 'FPGA12',
               'build': ['compact', 'check', '--target', 'fpga12'], 'test': ['compact', 'check', '--target', 'fpga12'],
               'note': 'R10 RTL lint/simulation; proxy-package evidence'},
}
# Compact R10 is the current hardware branch surfaced by this Workbench.
DEFAULT_TARGET = 'f133'
RUN_FRAMES = 120
RUN_DUMP = '0,30,60,90,119'

# Named operations shared with the agent interface (workbench/agent.py).
AGENT_ACTIONS = {
    'build.f133': TARGETS['f133']['build'],
    'build.d213': TARGETS['d213']['build'],
    'build.usb': TARGETS['usb']['build'],
    'build.power': TARGETS['power']['build'],
    'build.both': ['compact', 'check', '--target', 'all'],
    'build.fpga45': TARGETS['fpga45']['build'],
    'build.fpga12': TARGETS['fpga12']['build'],
    'test.game': ['test', 'examples/hello_arc1'],
    'build.game': ['build', 'examples/hello_arc1'],
    'inspect.hardware': ['hw', 'inspect'],
    'inspect.brand': ['brand'],
    'doctor': ['doctor'],
}

# The project navigator: logical areas, not the raw repository root.
LANGUAGES = {'.c': 'C11', '.h': 'C11 header', '.s': 'Assembly', '.S': 'Assembly', '.ld': 'Linker script',
             '.py': 'Python', '.md': 'Markdown', '.json': 'JSON', '.txt': 'Text', '.cmd': 'Batch',
             '.sh': 'Shell', '.yaml': 'YAML', '.yml': 'YAML', '.csv': 'CSV', '.sprite': 'Sprite',
             '.js': 'JavaScript', '.mjs': 'JavaScript module', '.css': 'CSS', '.html': 'HTML',
             '.webmanifest': 'Web manifest',
             '.replay': 'Replay', '.sv': 'SystemVerilog', '.v': 'Verilog', '.vh': 'Verilog header'}

SKIP_DIRS = {'__pycache__', '.git', 'build', 'reports', 'checkpoints', 'R05_BASELINE', 'R06_WORK',
             'R07_WORK', 'R08_WORK', 'R85_WORK', 'R85C_WORK'}
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
        if self.target == "development":
            return "python -m workbench.development_cli " + self.op
        if self.target == 'ledger':
            return 'python -m workbench.ledger_tools ' + self.op
        if self.target == 'arcade':
            return 'python workbench/arcade_tools.py ' + self.op
        return 'arc1 ' + ' '.join(self.argv)

    def process_args(self, root=ROOT):
        if self.target == "development":
            return [sys.executable,str(Path(root)/"workbench/development_cli.py"),self.op,"--root",str(Path(root))]
        if self.target == 'ledger':
            return [sys.executable, str(Path(root)/'workbench/ledger_tools.py'), self.op, '--root', str(Path(root))]
        if self.target == 'arcade':
            return [sys.executable, str(Path(root) / 'workbench/arcade_tools.py'),
                    self.op, '--root', str(Path(root))]
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


def arcade_for(path, root=ROOT):
    if path is None or not inside(path if Path(path).is_absolute() else Path(root) / path, root):
        return False
    relative = rel(path if Path(path).is_absolute() else Path(root) / path, root)
    return (relative == ARCADE_DIR or relative.startswith(ARCADE_DIR + '/')) \
        and (Path(root) / ARCADE_DIR / 'index.html').is_file()


def document_path(value):
    """Normalize a real file path; a workspace's path picker is not a document."""
    if not isinstance(value,(str,os.PathLike)):return None
    if isinstance(value,str) and not value.strip():return None
    try:
        path=Path(value)
        return None if '\x00' in str(path) else path
    except (TypeError,ValueError):return None


def context_target(path, root=ROOT):
    """Infer a build context from a real hardware source; GUI and agent share this rule."""
    source=document_path(path)
    if source is None:return None
    if not source.is_absolute():source=Path(root)/source
    try:relative=source.resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:return None
    base='hardware/compact-arc1/R10_WORK/'
    for tid,scopes in {
        'usb':('firmware/f133_ehci/','firmware/usb_hub/'), 'power':('firmware/power_control/',),
        'f133':('f133/','firmware/f133_'), 'd213':('d213/','firmware/d213_'),
        'fpga45':('fpga45/',), 'fpga12':('fpga12/',),
    }.items():
        if any(relative.startswith(base+prefix) for prefix in scopes):return tid
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
    if active_path is not None:
        from .hardware_import import P11
        source = Path(active_path)
        if not source.is_absolute():source = Path(root)/source
        from .development import WORK
        if source.resolve().is_relative_to((Path(root)/WORK/'src').resolve()):
            return development_plan('working',root)
        if source.resolve().is_relative_to((Path(root)/P11/'port').resolve()):
            return ledger_plan('parity',root)
        if source.resolve().is_relative_to((Path(root)/P11/'reference').resolve()):
            return ledger_plan('reference' if op=='run' else 'inspect',root)
    target = context_target(active_path, root) or target
    if arcade_for(active_path, root) or target == 'arcade':
        if not (Path(root) / ARCADE_DIR / 'index.html').is_file():
            raise ValueError('STRUTHIO Arcade 1.8 source is missing')
        label = {'build': 'Check STRUTHIO Arcade source',
                 'test': 'Check STRUTHIO Arcade JavaScript',
                 'run': 'Preview STRUTHIO Arcade in browser'}[op]
        return Plan(op, 'arcade', [op], ARCADE_DIR, label,
                    'the authorized STRUTHIO Arcade 1.8 browser project is selected')
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
            argv = ['sim', project, '--frames', str(RUN_FRAMES), '--dump-every', '1']
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
    # Strip only the known CLI diagnostic prefix, not whitespace inside a path.
    # The older generic tail matcher intentionally excludes spaces, so relying
    # on it alone loses the leading directory of a relocated Mac/Linux project.
    prefixed = re.match(r'^\s*FAIL\s+FW-BUILD\s+compiler returned\s+\d+:\s*(.+)$', source)
    if prefixed:
        candidates.append(prefixed.group(1).strip().strip('"'))
    m = _PATH_TAIL.search(source.strip())
    if m:
        candidates.append(m.group(0))
    bases = [root]
    if plan_ is not None and plan_.project:
        bases.insert(0, root / plan_.project)
    if plan_ is not None and plan_.target in ('f133', 'd213', 'fpga45', 'fpga12'):
        compact = root / 'hardware/compact-arc1/R10_WORK'
        target_bases = {
            'f133': (compact / 'firmware/f133_bootloader', compact / 'f133'),
            'd213': (compact / 'd213/gpu_driver', compact / 'd213'),
            'fpga45': (compact / 'fpga45',),
            'fpga12': (compact / 'fpga12',),
        }
        bases = [*target_bases[plan_.target], *bases]
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
        if Path(dirpath).resolve() == Path(root).resolve():
            dirnames[:] = [d for d in dirnames if d != 'firmware']
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


# R10.12: one validated command planner for GUI and structured agent simulations.
def simulation_plan(operation, project, root=ROOT, frames=RUN_FRAMES, scenario=None, profile=None):
    from .project_services import project_path
    directory = project_path(root, project)
    if not (directory/'arc1.game.json').is_file():
        raise ValueError('Choose a C host game containing arc1.game.json')
    if type(frames) is not int or not 1 <= frames <= 120:
        raise ValueError('Interactive runs support 1–120 frames')
    commands={'host':['sim',project,'--frames',str(frames),'--dump-every','1'],
              'system':['system-sim',project,'--frames',str(frames)],
              'compare':['workload-compare',project,'--frames',str(frames)]}
    if operation not in commands:raise ValueError('Unknown simulation operation')
    args=commands[operation]
    options={'controller_mask':'--controller-mask','nor_fault_frame':'--nor-fault-frame',
             'fpga_fail':'--fpga-fail','power_loss_frame':'--power-loss-frame',
             'cartridge_reload_frame':'--cartridge-reload-frame','usb_detach_frame':'--usb-detach-frame'}
    if scenario:
        if operation!='system' or not isinstance(scenario,dict) or set(scenario)-set(options):
            raise ValueError('Invalid system scenario')
        for key,value in scenario.items():
            if key=='fpga_fail':
                if value not in ('12','45'):raise ValueError('Invalid FPGA fault')
            elif type(value) is not int or value<0 or value>(65535 if key=='controller_mask' else frames-1):
                raise ValueError('Scenario value outside range')
            args.extend([options[key],str(value)])
    if profile is not None:
        if operation!='compare':raise ValueError('Profiles apply to comparison only')
        p=project_path(root,profile)
        if not p.is_file():raise ValueError('Profile not found')
        args.extend(['--profile',profile])
    labels={'host':'Host frame capture','system':'Behavioral system trace','compare':'Hypothetical offload comparison'}
    return Plan('simulation','game',args,project,labels[operation],'Shared host-only simulation service')


def ledger_plan(action, root=ROOT):
    """Fixed host import services shared by the human and agent interfaces."""
    if action not in ('inspect','parity','reference'):
        raise ValueError('Unknown Graphite action')
    from .hardware_import import descriptor
    descriptor(root)
    return Plan(action,'ledger',[],None,
                {'inspect':'Verify hardware import sources','parity':'STRUTHIO C port host checks',
                 'reference':'Original STRUTHIO browser reference'}[action],
                'Hardware P1–P11 handoff; host-only; no physical programming')


def development_plan(mode,root=ROOT):
    if mode not in ('baseline','working','compare'):raise ValueError('Unknown development run mode')
    from .development import descriptor
    descriptor(root)
    return Plan(mode,'development',[],None,'Diagnostic case: '+mode,
                'P10 host diagnostic candidate; source-bound reports; no board access')


def hardware_review_snapshot(root=ROOT):
    from .hardware_review import inspect
    return inspect(root)
