"""Graphite's checks in tiers: one command for a change, a commit and a release (docs/CHECKS.md).

  python3 tools/run_tiers.py 0 [--look graphite|kasandra|both] [--out DIR]
  python3 tools/run_tiers.py 1 [--changed REF] [--look ...] [--out DIR]
  python3 tools/run_tiers.py 2 [--look ...] [--out DIR] [--against EARLIER.json]

Tier 0, at every change, in under a minute: the fast modules that guard the most, and always the ones that guard the
owner (the Kernel's scopes, her hand's rules, the memory rules, release integrity, the seed being current, one name).
Tier 1, before a commit: tier 0, and every test module that imports a file changed since REF (default HEAD; files not
yet added to git count as changed), with the window checks that do. Tier 2, at a release: every test module, the window
checks (tools/check_hatch.py UI_CHECKS, read when the run starts), the playable scene on Rail Demo four ways
(tools/campaign.py), the name sweep over the code and the release check's integrity sections, in both looks.

The lists are in tools/tiers.json; tier 2's modules are tools/check_hatch.py's FOCUSED_MODULES and ON_DEMAND_MODULES,
the list every new test module joins. Each module, check or scene runs in a process of its own with its own empty HOME
and temporary folder, at the lowest priority and in a process namespace of its own where the machine allows one (so
nothing it starts outlives it), two at a time, and is killed at its time limit; a limit reached is a failure. When a
child ends, its process group is killed too. The run writes tier<N>.json (one row per module and look: ran, failed,
skipped, seconds, state, the failing tests and their messages) and each one's output under --out (a new temporary folder
by default; never inside the program folder), prints one table and a last line, "0 failing" or what failed (and what was
skipped), and exits 0 only when nothing failed. Ctrl-C stops a run: what runs is killed with what it started, the
result is written with what was stopped and what was not run, and the exit is 130.
"""
import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
TIERS = 'tools/tiers.json'
LOOKS = ('graphite', 'kasandra')
# Where the program's Python lives (wip/ is development notes, never run), and the folders a bare import is found in:
# the program folder, tools/ (the tools put it on sys.path) and sdk/cli (the line's language, arc1cli).
SOURCES = ('workbench', 'tools', 'tests_integrated', 'sdk', 'pillkit', 'examples')
IMPORT_ROOTS = ('', 'tools/', 'sdk/cli/')
NAMED = re.compile(r'\b(?:workbench|tools|tests_integrated|sdk|pillkit)(?:\.[A-Za-z_]\w*)+')
PATHS = re.compile(r'\b(?:workbench|tools|tests_integrated|sdk|pillkit|docs|project|branding)/[\w./-]*\w')
CACHE_FORMAT = 1


# The import map --------------------------------------------------------------------------------------------------------

def python_files(root=ROOT):
    """Every Python file of the program, its tools and its tests, as paths relative to root."""
    root = Path(root); found = [p.name for p in root.glob('*.py')]
    for folder in SOURCES:
        for dirpath, dirnames, filenames in os.walk(root / folder):
            dirnames[:] = sorted(d for d in dirnames if d != '__pycache__' and not d.startswith('.'))
            found += [Path(dirpath, name).relative_to(root).as_posix() for name in filenames if name.endswith('.py')]
    return sorted(found)


def _package(relative):
    return relative[:-3].split('/')[:-1]      # workbench/x.py and workbench/__init__.py are both in the package workbench


def references(relative, text):
    """What one file names: the modules it imports (wherever the import stands, absolute names) and the modules and
    files its strings name (a patch target 'workbench.x.y', a path 'tools/campaign.py' or 'docs/X.md')."""
    names = set(); paths = set()
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return {'names': [], 'paths': []}
    package = _package(relative)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[:len(package) - node.level + 1] if node.level <= len(package) + 1 else []
                module = '.'.join(base + ([node.module] if node.module else []))
            else:
                module = node.module or ''
            if module:
                names.add(module)
            names.update((module + '.' + alias.name) if module else alias.name for alias in node.names if alias.name != '*')
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            names.update(NAMED.findall(node.value)); paths.update(PATHS.findall(node.value))
    return {'names': sorted(names), 'paths': sorted(paths)}


def _cache_file(root):
    base = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    return base / 'graphite-tiers' / (hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:16] + '.json')


def import_map(root=ROOT, cache=None):
    """{file: {'names': [...], 'paths': [...]}} for every Python file, read again only where a file's size or time
    changed since the cached map (cache: a JSON file; None for the user's cache folder, False for none)."""
    root = Path(root); cache = _cache_file(root) if cache is None else cache; kept = {}
    if cache:
        try:
            stored = json.loads(Path(cache).read_text())
            kept = stored.get('files') if isinstance(stored, dict) and stored.get('format') == CACHE_FORMAT else {}
        except (OSError, ValueError):
            kept = {}
        kept = kept if isinstance(kept, dict) else {}           # a map of another shape is made again, never trusted
    found = {}; fresh = False
    for relative in python_files(root):
        stat = (root / relative).stat(); stamp = [stat.st_mtime_ns, stat.st_size]; row = kept.get(relative)
        if not (isinstance(row, dict) and row.get('stamp') == stamp and isinstance(row.get('names'), list) and isinstance(row.get('paths'), list)):
            row = {'stamp': stamp, **references(relative, (root / relative).read_text(encoding='utf-8', errors='replace'))}; fresh = True
        found[relative] = row
    if cache and (fresh or set(found) != set(kept)):
        try:
            Path(cache).parent.mkdir(parents=True, exist_ok=True)
            Path(cache).write_text(json.dumps({'format': CACHE_FORMAT, 'root': str(root), 'files': found}))
        except OSError:
            pass
    return {relative: {'names': row['names'], 'paths': row['paths']} for relative, row in found.items()}


def resolve(name, files):
    """The file a dotted name is, the longest part of it that is a module ('workbench.x.CONSTANT' is workbench/x.py)."""
    parts = name.split('.')
    for end in range(len(parts), 0, -1):
        stem = '/'.join(parts[:end])
        for base in IMPORT_ROOTS:
            for candidate in (base + stem + '.py', base + stem + '/__init__.py'):
                if candidate in files:
                    return candidate
    return None


def direct(relative, imports, files):
    """The files one file imports or names, itself left out."""
    row = imports.get(relative) or {'names': [], 'paths': []}
    out = {resolve(name, files) for name in row['names']} | {path for path in row['paths'] if path in files}
    for name in row['names']:          # importing workbench.x runs workbench/__init__.py first
        parts = name.split('.')
        for end in range(1, len(parts)):
            package = resolve('.'.join(parts[:end]), files)
            if package and package.endswith('__init__.py'):
                out.add(package)
    out.discard(None); out.discard(relative)
    return out


def changed_files(ref='HEAD', root=ROOT):
    """The files that differ from REF in the working tree (staged or not, deleted ones too), and the files git does not
    know yet. A file moved or renamed counts under both its names: git would give only the new one, and the tests that
    import the old name are the ones the move breaks. Paths are relative to the program folder."""
    def git(*args):
        child = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
        if child.returncode:
            raise SystemExit('tier 1 needs the program folder to be a git checkout and %s a commit: %s' % (ref, child.stderr.strip()[-300:]))
        return [line for line in child.stdout.splitlines() if line]
    return sorted(set(git('diff', '--name-only', '--no-renames', '--relative', ref, '--')) | set(git('ls-files', '--others', '--exclude-standard')))


def dependents(changed, units, root=ROOT, imports=None, ignored=()):
    """{unit file: [the changed files it depends on]} for each unit file (a test module or a window check). A unit depends on
    itself, on what it imports or names, and on what its own helpers in tests_integrated/ and tools/ import or name; a
    program file counts when a test or a helper names it (following every import of the program would choose every module,
    as the window imports most of it). A changed file that is not Python is followed to the Python files that name it, by
    its file name as a whole word ('CHECKS.md' is not named by 'WINDOW_CHECKS.md')."""
    imports = import_map(root) if imports is None else imports; files = set(imports)
    changed = [c for c in changed if not any(c == i or (i.endswith('/') and c.startswith(i)) for i in ignored)]
    touched = {c: {c} for c in changed if c.endswith('.py')}
    others = {c: re.compile(r'(?<![\w.-])%s(?![\w-])' % re.escape(Path(c).name)) for c in changed if not c.endswith('.py')}
    if others:
        for relative in sorted(files):
            try:
                text = (Path(root) / relative).read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            for other, named in others.items():
                if named.search(text):
                    touched.setdefault(relative, set()).add(other)
    found = {}; known = files | set(changed)       # a deleted file is still a name a test imports
    for unit in units:
        seen = {unit}; todo = [unit]
        while todo:
            for dependency in direct(todo.pop(), imports, known):
                if dependency not in seen:
                    seen.add(dependency)
                    if dependency.startswith(('tests_integrated/', 'tools/')):
                        todo.append(dependency)
        hit = sorted({c for f in seen & set(touched) for c in touched[f]})
        if hit:
            found[unit] = hit
    return found


# The tiers ---------------------------------------------------------------------------------------------------------------

def config(root=ROOT):
    return json.loads((Path(root) / TIERS).read_text(encoding='utf-8'))


def every_module():
    """Tier 2's modules: the focused set and the modules kept on demand (tools/check_hatch.py), read when the run starts."""
    from tools import check_hatch
    return list(check_hatch.FOCUSED_MODULES) + [m for m in check_hatch.ON_DEMAND_MODULES if m not in check_hatch.FOCUSED_MODULES]


def window_checks():
    """The window checks of the gate (tools/check_hatch.py UI_CHECKS) and the folder variable each writes its captures to."""
    from tools import check_hatch
    return list(check_hatch.UI_CHECKS), dict(check_hatch.UI_CAPTURE_ENV)


def tier0_units(cfg):
    return [{'kind': 'module', 'name': row['module'], 'classes': list(row.get('classes') or [])} for row in cfg['0']['modules']]


def plan(tier, looks, cfg, changed=None, root=ROOT, modules=None, checks=None, imports=None):
    """What a tier runs, as units ({kind, name, look, ...}), and for tier 1 why each chosen one is chosen."""
    looks = list(looks); units = []; chosen = {}
    def each_look(unit, only_first=False):
        for look in looks[:1] if only_first else looks:
            units.append({**unit, 'look': look})
    if tier in (0, 1):
        base = tier0_units(cfg)
        if tier == 1:
            modules = every_module() if modules is None else modules
            checks = window_checks()[0] if checks is None else checks
            files = ['tests_integrated/%s.py' % m for m in modules] + list(checks)
            chosen = dependents(changed or [], files, root, imports, cfg['1'].get('ignored', {}))
            whole = {Path(f).stem for f in chosen if f.startswith('tests_integrated/')}
            base = [u for u in base if u['name'] not in whole] + [{'kind': 'module', 'name': m, 'classes': []} for m in modules if m in whole]
            base += [{'kind': 'check', 'name': c} for c in checks if c in chosen]
        for unit in base:
            each_look(unit)
        return units, chosen
    two = cfg['2']; modules = every_module() if modules is None else modules
    checks = window_checks()[0] if checks is None else checks; once = two.get('once', {})
    units.append({'kind': 'integrity', 'name': 'tools/check_release.py', 'look': looks[0]})
    units.append({'kind': 'sweep', 'name': 'tools/name_sweep.py', 'look': looks[0]})
    for module in modules:
        each_look({'kind': 'module', 'name': module, 'classes': [], **({'note': once[module]} if module in once else {})}, module in once)
    for check in checks:
        each_look({'kind': 'check', 'name': check})
    each_look({'kind': 'scene', 'name': ','.join(two['scene'])})
    return units, chosen


# Running ------------------------------------------------------------------------------------------------------------------

_ISOLATION = {}
DROPPED = ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME', 'PYTHONPATH', 'GRAPHITE_APPEARANCE')
# The program's own variables say where its state is and how it runs (the workspace a switch chose, the service's edition
# and supervision, a capture folder, the campaign's fixtures): none passes from the shell that started the run.
DROPPED_PREFIXES = ('ARC_LEDGER_', 'ARC1_WORKBENCH_', 'LEDGER_', 'GRAPHITE_')
UNSHARE = ('--pid', '--fork', '--mount-proc', '--kill-child')
STOPPED_AT_LIMIT = 'stopped at its time limit'
STOPPED_BY_RUN = 'stopped: the run was interrupted'


def isolation():
    """The command put in front of each child: nice 19, and a process namespace of its own where unshare can make one (as
    root, or where the machine allows it); otherwise a process group of its own, killed whole at the time limit."""
    if not _ISOLATION:
        prefix = ['nice', '-n', '19'] if shutil.which('nice') else []; kind = 'process group'
        unshare = shutil.which('unshare')
        if unshare and sys.platform.startswith('linux'):
            try:
                if subprocess.run([unshare, *UNSHARE, 'true'], capture_output=True, timeout=30).returncode == 0:
                    prefix += [unshare, *UNSHARE]; kind = 'process namespace'
            except (OSError, subprocess.SubprocessError):
                pass
        _ISOLATION.update(prefix=prefix, kind=kind + (', nice 19' if prefix[:1] == ['nice'] else ''))
    return _ISOLATION['prefix'], _ISOLATION['kind']


def backstop(limit, grace):
    """`timeout` in front of the child, a little after the run's own limit: should the run itself be killed outright, each
    child still ends, with its process group, at its limit and the grace."""
    found = shutil.which('timeout')
    return [found, '-s', 'KILL', '%g' % (limit + grace)] if found and limit else []


def stop_group(child):
    """Kill a child with its process group: what it started goes with it (a namespace's first process takes the rest)."""
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except (OSError, AttributeError):
        try:
            child.kill()
        except OSError:
            pass


class Stop:
    """How a run is stopped before its end: Ctrl-C, SIGTERM or SIGHUP (a second one changes nothing). Nothing more is
    begun, every child running is killed with what it started, and its unit is a failure. A signal ignored by the shell
    that started the run (nohup) stays ignored."""
    SIGNALS = ('SIGINT', 'SIGTERM', 'SIGHUP')

    def __init__(self):
        self.lock = threading.RLock(); self.event = threading.Event(); self.children = {}; self.stopped = set(); self.signal = None

    def is_set(self):
        return self.event.is_set()

    def now(self, signum=None, frame=None):
        with self.lock:
            if signum and self.signal is None:
                self.signal = signum
            self.event.set(); children = list(self.children.values()); self.stopped.update(child.pid for child in children)
        for child in children:
            stop_group(child)

    def started(self, child):
        with self.lock:
            self.children[child.pid] = child
            late = self.event.is_set()
            if late:
                self.stopped.add(child.pid)
        if late:
            stop_group(child)

    def finished(self, child):
        """True when the run's stop ended the child, not the child itself or its limit."""
        with self.lock:
            self.children.pop(child.pid, None)
            return child.pid in self.stopped

    def catch(self):
        caught = {}
        if threading.current_thread() is threading.main_thread():
            for name in self.SIGNALS:
                number = getattr(signal, name, None)
                if number is not None and signal.getsignal(number) is not signal.SIG_IGN:
                    caught[number] = signal.signal(number, self.now)
        return caught

    @staticmethod
    def release(caught):
        for number, handler in caught.items():
            signal.signal(number, signal.SIG_DFL if handler is None else handler)


def child_environment(look, scratch, extra=None):
    """The child's variables: the shell's, without the program's own and the folders of its state; its own HOME and
    temporary folder, offscreen. Graphite's look is the default one, the variable unset, as the owner starts it."""
    env = {k: v for k, v in os.environ.items() if k not in DROPPED and not k.startswith(DROPPED_PREFIXES)}
    env.update(HOME=str(Path(scratch) / 'home'), TMPDIR=str(Path(scratch) / 'tmp'), QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1',
               **(extra or {}))
    if look != LOOKS[0]:
        env['GRAPHITE_APPEARANCE'] = look
    return env


def label(unit):
    if unit['kind'] == 'module' and unit.get('classes'):
        return '%s (%s)' % (unit['name'], ', '.join(unit['classes']))
    return unit['name']


def command(unit, out, capture_env=None):
    """The child's arguments and any variables of its own."""
    python = [sys.executable, '-B']
    if unit['kind'] == 'module':
        names = ['tests_integrated.%s.%s' % (unit['name'], c) for c in unit.get('classes') or []] or ['tests_integrated.' + unit['name']]
        return python + ['-m', 'unittest', '-v', *names], {}
    if unit['kind'] == 'check':
        variable = (capture_env or {}).get(unit['name'])
        return python + [unit['name']], ({variable: str(out / unit['look'] / 'window' / Path(unit['name']).stem)} if variable else {})
    if unit['kind'] == 'scene':
        return python + ['tools/campaign.py', 'run', '--case', unit['name'], '--out', str(out / unit['look'] / 'scene')], {}
    if unit['kind'] == 'integrity':
        return python + ['tools/check_release.py', '--output', str(out / 'release_check.json')], {}
    return python + [unit['name']], {}


FAILURE = re.compile(r'^(FAIL|ERROR): (\S+) \(([^)]*)\)(.*)$')
RULE = re.compile(r'^(?:=|-){60,}$')


def unittest_failures(stderr):
    """Each failing or erroring test, and the last line of what it raised: the message is compared, not only the place."""
    found = []; lines = stderr.splitlines(); index = 0
    while index < len(lines):
        match = FAILURE.match(lines[index]); index += 1
        if not match:
            continue
        while index < len(lines) and not lines[index].startswith('-' * 60):      # the first line of the test's docstring, if it has one
            index += 1
        block = []; index += 1
        while index < len(lines) and not lines[index].startswith(('=' * 60, '-' * 60)):
            block.append(lines[index]); index += 1
        frames = [n for n, line in enumerate(block) if line.startswith('  File ')]
        tail = [line.strip() for line in block[(frames[-1] + 1 if frames else 0):] if line.strip() and not line.startswith(('    ', '  File ')) and not RULE.match(line)]
        found.append({'test': '%s %s%s' % (match.group(1), match.group(3), match.group(4)), 'message': ' '.join(tail)[:400]})
    return found


def _last(text, rc):
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return lines[-1][:400] if lines else 'exit %s' % rc


def read_result(unit, rc, stopped, out_text, err_text, out):
    """ran, failed, what failed and how many were skipped, from what the child printed or wrote. stopped: why the run
    stopped the child (its time limit, or the run interrupted), or nothing."""
    from tools import check_hatch
    skipped = 0
    if unit['kind'] == 'module':
        summary = check_hatch.parse_unittest(err_text); counts = re.findall(r'^Ran (\d+) tests? in ', err_text, re.M)
        ran = int(counts[-1]) if counts else 0              # the last: a test may print a summary of its own on the way
        failures = unittest_failures(err_text); failed = summary['failures'] + summary['errors']; skipped = summary['skipped']
        if (rc or summary['verdict'] != 'OK') and not failed:   # it died, or ended mid-test, without a word of unittest's
            failed = 1; failures = failures or [{'test': 'the module', 'message': _last(err_text, rc)}]
    elif unit['kind'] == 'check':
        value = check_hatch.tail_json(out_text); value = value if isinstance(value, dict) else {}
        ran = len(value['checks']) if isinstance(value.get('checks'), list) else 0
        failed = 0 if (rc == 0 and value.get('state') == 'PASSED') else 1
        said = _last(err_text, rc) if err_text.strip() else _last(out_text, rc)
        message = _last(str(value['error']), rc) if value.get('error') else (said if value else 'no report: ' + said)
        failures = [{'test': unit['name'], 'message': message}] if failed else []
    elif unit['kind'] == 'scene':
        rows = []; cases = unit['name'].split(',')
        try:
            rows = [json.loads(line) for line in (out / unit['look'] / 'scene' / 'results.jsonl').read_text().splitlines() if line.strip()]
        except (OSError, ValueError):
            pass
        ran = len(rows)
        failures = [{'test': str(row.get('case') or row.get('id') or '?'), 'message': '%s: %s' % (row.get('outcome'), str(row.get('reason') or '')[:300])}
                    for row in rows if not str(row.get('outcome', '')).startswith('Pass')]
        if rc or ran < len(cases):
            failures.append({'test': 'the scene run', 'message': 'exit %s, %d of %d cases reported; %s' % (rc, ran, len(cases), _last(err_text, rc))})
        failed = len(failures)
    elif unit['kind'] == 'integrity':
        value = {}
        try:
            value = json.loads((out / 'release_check.json').read_text())
        except (OSError, ValueError):
            pass
        ran = sum(1 for v in value.values() if isinstance(v, dict) and 'state' in v); named = value.get('failed_sections') or []
        failures = [{'test': name, 'message': '; '.join(str(x) for x in (value[name].get('differences') or value[name].get('problems') or value[name].get('errors') or [value[name].get('state')])[:3])[:400]}
                    for name in named if isinstance(value.get(name), dict)]
        if not value or rc and not failures:
            failures.append({'test': unit['name'], 'message': 'no report' if not value else _last(err_text, rc)})
        failed = len(failures)
    else:
        ran = 1; failures = [{'test': unit['name'], 'message': _last(out_text + '\n' + err_text, rc)}] if rc else []; failed = len(failures)
    if stopped:
        failed = max(failed, 1); failures = [{'test': label(unit), 'message': STOPPED_AT_LIMIT if stopped is True else stopped}] + failures
    return ran, failed, failures, skipped


def row_of(unit, state, ran=0, failed=0, skipped=0, seconds=0.0, rc=None, failures=(), log=None):
    return {'module': label(unit), 'look': unit['look'], 'kind': unit['kind'], 'ran': ran, 'failed': failed, 'skipped': skipped,
            'seconds': round(seconds, 1), 'state': state, 'exit': rc, 'failures': list(failures), 'log': log,
            **({'note': unit['note']} if unit.get('note') else {})}


def run_unit(unit, root, out, timeout, capture_env=None, stop=None, grace=30):
    """One unit in a child of its own: its own empty HOME and temporary folder (removed after), the look given, offscreen.
    When it ends, by itself, at its limit or by the run's stop, its process group is killed: nothing it started outlives it."""
    prefix, _ = isolation(); argv, extra = command(unit, out, capture_env)
    logs = out / 'logs' / unit['look']; logs.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r'[^\w.-]+', '_', label(unit).replace('tools/', '')).strip('_')
    if unit['kind'] == 'integrity':          # an earlier run's report in the same folder is never read as this one's
        (out / 'release_check.json').unlink(missing_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix='graphite-tier-')); (scratch / 'home').mkdir(); (scratch / 'tmp').mkdir()
    env = child_environment(unit['look'], scratch, extra)
    began = time.monotonic(); stopped = None
    try:
        with open(logs / (stem + '.out'), 'w') as stdout, open(logs / (stem + '.err'), 'w') as stderr:
            child = subprocess.Popen(backstop(timeout, grace) + prefix + argv, cwd=str(root), env=env, stdout=stdout, stderr=stderr,
                                     stdin=subprocess.DEVNULL, start_new_session=True)
            if stop is not None:
                stop.started(child)
            try:
                rc = child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                stopped = STOPPED_AT_LIMIT; stop_group(child); rc = child.wait()
            stop_group(child)               # what it started and left running when it ended
            if stop is not None and stop.finished(child):
                stopped = STOPPED_BY_RUN
        seconds = time.monotonic() - began
        out_text = (logs / (stem + '.out')).read_text(errors='replace'); err_text = (logs / (stem + '.err')).read_text(errors='replace')
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    ran, failed, failures, skipped = read_result(unit, rc, stopped, out_text, err_text, out)
    state = {STOPPED_AT_LIMIT: 'TIMEOUT', STOPPED_BY_RUN: 'INTERRUPTED'}.get(stopped) or ('FAILED' if failed else 'PASSED')
    return row_of(unit, state, ran, failed, skipped, seconds, rc, failures, (logs / stem).relative_to(out).as_posix() + '.out')


def expected(unit, cfg):
    """Seconds a unit took when measured (tools/tiers.json), to start the longest first; a guess for the rest."""
    known = cfg.get('seconds', {}); keys = (label(unit),) if unit.get('classes') else (unit['name'], Path(unit['name']).stem, unit['kind'])
    return next((known[key] for key in keys if key in known), 5)


def run_all(units, root, out, cfg, workers=2, timeout=None, report=None, stop=None):
    """Every unit, `workers` at a time, the longest expected first; rows in the order the units were given. A unit the
    runner itself could not run (a full disk, say) is a failure that says why. When the run is stopped (Ctrl-C, SIGTERM,
    SIGHUP, or stop.now()), the units running are killed with what they started and are failures, and the rest are
    'not run'."""
    capture_env = window_checks()[1] if any(u['kind'] == 'check' for u in units) else {}
    stop = Stop() if stop is None else stop; grace = cfg.get('timeout_grace_seconds', 30)
    pending = sorted(range(len(units)), key=lambda i: -expected(units[i], cfg)); rows = [None] * len(units)
    lock = threading.Lock(); done = [0]
    def worker():
        while True:
            with lock:
                if not pending or stop.is_set():
                    return
                index = pending.pop(0)
            unit = units[index]; limit = timeout or cfg.get('timeout_seconds', {}).get(unit['kind'], 900)
            try:
                row = run_unit(unit, root, out, limit, capture_env, stop, grace)
            except Exception as exc:
                row = row_of(unit, 'FAILED', failed=1, failures=[{'test': label(unit), 'message': 'the runner could not run it: %s: %s' % (type(exc).__name__, exc)}])
            with lock:
                rows[index] = row; done[0] += 1
                if report:
                    report('[%d/%d] %-9s %-44s %6.1fs  %s' % (done[0], len(units), row['look'], row['module'][:44], row['seconds'], row['state'].lower()))
    caught = stop.catch(); threads = [threading.Thread(target=worker, daemon=True) for _ in range(max(1, workers))]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        if any(thread.is_alive() for thread in threads):      # cut short by a fault of the run's own: stop what runs
            stop.now()
            for thread in threads:
                thread.join()
        stop.release(caught)
    return [row or row_of(unit, 'NOT RUN') for unit, row in zip(units, rows)]


# The report -----------------------------------------------------------------------------------------------------------------

def failing(rows):
    return [row for row in rows if row['failed']]


def interrupted(rows):
    return any(row['state'] in ('INTERRUPTED', 'NOT RUN') for row in rows)


def table(rows):
    lines = ['%-9s %-9s %-52s %5s %6s %7s %8s  %s' % ('look', 'kind', 'module, check or scene', 'ran', 'failed', 'skipped', 'seconds', 'state')]
    for row in rows:
        lines.append('%-9s %-9s %-52s %5d %6d %7d %8.1f  %s' % (row['look'], row['kind'], row['module'][:52], row['ran'], row['failed'],
                                                                row.get('skipped', 0), row['seconds'], row['state'].lower()))
    return lines


def last_line(rows):
    """'0 failing', or how many and where; the tests skipped, named, after it; 'interrupted' first when the run was."""
    bad = failing(rows); skipped = [row for row in rows if row.get('skipped')]
    line = '%d failing: %s' % (sum(row['failed'] for row in bad), '; '.join('%s %s' % (row['look'], row['module']) for row in bad)) if bad else '0 failing'
    if skipped:
        line += '; %d skipped: %s' % (sum(row['skipped'] for row in skipped), '; '.join('%s %s (%d)' % (row['look'], row['module'], row['skipped']) for row in skipped))
    if interrupted(rows):
        line = 'interrupted, %d of %d not run; %s' % (sum(1 for row in rows if row['state'] == 'NOT RUN'), len(rows), line)
    return line


def differences(before, after):
    """What changed between two runs, unit by unit and look by look: the state, the number run, and each failing test with
    its message (a failure whose words changed is a change, not 'the same failure')."""
    def keyed(rows):
        return {(row['look'], row['module']): row for row in rows}
    then, now = keyed(before), keyed(after); lines = []
    for key in sorted(set(then) | set(now)):
        a, b = then.get(key), now.get(key)
        if a is None:
            lines.append('%s %s: new, %s' % (key[0], key[1], b['state'].lower())); continue
        if b is None:
            lines.append('%s %s: not run this time' % key); continue
        if a['state'] != b['state']:
            lines.append('%s %s: %s, was %s' % (key[0], key[1], b['state'].lower(), a['state'].lower()))
        elif a['ran'] != b['ran']:
            lines.append('%s %s: ran %d, was %d' % (key[0], key[1], b['ran'], a['ran']))
        old = {(f['test'], f['message']) for f in a.get('failures') or []}
        for f in b.get('failures') or []:
            if (f['test'], f['message']) not in old:
                lines.append('%s %s: %s now says: %s' % (key[0], key[1], f['test'], f['message']))
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(prog='run_tiers.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('tier', type=int, choices=(0, 1, 2), help='0 at every change, 1 before a commit, 2 at a release')
    parser.add_argument('--look', choices=(*LOOKS, 'both'), help='the look the tests run in (tiers 0 and 1: the look in force; tier 2: both)')
    parser.add_argument('--changed', metavar='REF', help='tier 1: the commit the change is measured from (default HEAD)')
    parser.add_argument('--out', type=Path, help='the folder for tier<N>.json and the logs (default: a new temporary folder)')
    parser.add_argument('--against', type=Path, metavar='EARLIER', help='an earlier tier<N>.json: say what changed since')
    parser.add_argument('--timeout', type=float, help='seconds each module, check or scene may take (default: tools/tiers.json)')
    parser.add_argument('--workers', type=int, default=2, help='how many run at once (default 2, for four cores)')
    args = parser.parse_args(argv)
    if args.changed and args.tier != 1:
        parser.error('--changed belongs to tier 1')
    out = (args.out or Path(tempfile.mkdtemp(prefix='graphite-tier%d-' % args.tier))).expanduser().resolve(); program = ROOT.resolve()
    if out == program or program in out.parents:      # resolved: neither '..' nor a link leads a run into the program
        parser.error('choose an --out folder outside the program folder (%s): a run writes nothing into the program' % ROOT)
    out.mkdir(parents=True, exist_ok=True)
    cfg = config(); in_force = os.environ.get('GRAPHITE_APPEARANCE', '').strip().lower()
    look = args.look or ('both' if args.tier == 2 else (in_force if in_force in LOOKS else LOOKS[0]))
    looks = list(LOOKS) if look == 'both' else [look]
    changed = changed_files(args.changed or 'HEAD') if args.tier == 1 else None
    units, chosen = plan(args.tier, looks, cfg, changed)
    _, kind = isolation(); began = time.monotonic(); started = time.strftime('%Y-%m-%dT%H:%M:%S')
    print('tier %d: %d runs in %s, %d at a time (%s); logs under %s' % (args.tier, len(units), ' and '.join(looks), args.workers, kind, out),
          file=sys.stderr, flush=True)
    stop = Stop()
    rows = run_all(units, ROOT, out, cfg, args.workers, args.timeout, report=lambda line: print(line, file=sys.stderr, flush=True), stop=stop)
    wall = round(time.monotonic() - began, 1); cut = interrupted(rows)
    result = {'tier': args.tier, 'looks': looks, 'started': started, 'wall_seconds': wall, 'workers': args.workers, 'isolation': kind,
              'state': 'INTERRUPTED' if cut else ('FAILED' if failing(rows) else 'PASSED'), 'failing': sum(row['failed'] for row in rows),
              'not_run': sum(1 for row in rows if row['state'] == 'NOT RUN'), 'skipped': sum(row['skipped'] for row in rows),
              'tests_run': sum(row['ran'] for row in rows if row['kind'] == 'module'), 'rows': rows}
    lines = table(rows)
    if args.tier == 1:
        result.update(changed_since=args.changed or 'HEAD', changed=changed, chosen_by_change=chosen)
        lines.append('changed since %s: %d files; chosen by them: %s' % (args.changed or 'HEAD', len(changed),
                     ', '.join('%s (%s)' % (Path(f).stem, ', '.join(c)) for f, c in sorted(chosen.items())) or 'nothing beyond tier 0'))
    if args.against:
        try:
            result['against'] = {'file': str(args.against), 'differences': differences(json.loads(args.against.read_text())['rows'], rows)}
        except (OSError, ValueError, KeyError) as exc:
            result['against'] = {'file': str(args.against), 'error': type(exc).__name__ + ': ' + str(exc)}
        lines += ['since %s:' % args.against] + ['  ' + line for line in result['against'].get('differences') or [result['against'].get('error') or 'no difference']]
    for row in failing(rows):
        lines += ['%s %s:' % (row['look'], row['module'])] + ['  %s: %s' % (f['test'], f['message']) for f in row['failures'][:8]]
    lines.append('tier %d: %d runs, %d tests, %dm %02ds wall, %s' % (args.tier, len(rows), result['tests_run'], *divmod(int(wall), 60), ' and '.join(looks)))
    lines.append(last_line(rows))
    (out / ('tier%d.json' % args.tier)).write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n')
    print('\n'.join(lines))
    if cut:
        return 128 + (stop.signal or signal.SIGINT)
    return 1 if failing(rows) else 0


if __name__ == '__main__':
    raise SystemExit(main())
