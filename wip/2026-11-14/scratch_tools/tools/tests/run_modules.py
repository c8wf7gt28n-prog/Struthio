"""Orchestrator's runner: each focused test module of a Graphite tree in its own child process (as the project's release
check does), recording the exit status and the exact failing test ids, so two trees can be compared test by test."""
import json, os, re, subprocess, sys, time
from pathlib import Path
ROOT = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]); PY = sys.argv[3]
src = (ROOT / 'tools/check_hatch.py').read_text()
import ast
modules = next(list(ast.literal_eval(node.value)) for node in ast.parse(src).body
               if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'FOCUSED_MODULES' for t in node.targets))
env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1')
rows = {}
for name in modules:
    t = time.time()
    try:
        r = subprocess.run([PY, '-B', '-m', 'unittest', '-v', 'tests_integrated.' + name], cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
        text = r.stderr + r.stdout; code = r.returncode
    except subprocess.TimeoutExpired as exc:
        text = (exc.stderr or '') if isinstance(exc.stderr, str) else ''; code = 'timeout'
    ran = re.search(r'^Ran (\d+) tests?', text, re.M)
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\S+ \(\S+\))', text, re.M)))
    rows[name] = {'code': code, 'tests': int(ran.group(1)) if ran else None, 'bad': bad, 'seconds': round(time.time() - t, 1)}
    OUT.write_text(json.dumps(rows, indent=1))
    print(name, code, rows[name]['tests'], len(bad), rows[name]['seconds'], flush=True)
print('DONE', len(rows))
