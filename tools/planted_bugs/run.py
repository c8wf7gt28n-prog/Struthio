#!/usr/bin/env python3
"""Run named planted bugs against the tests that cover them, and count how many the suite catches by behaviour.

For each bug, in a throwaway copy of the tree (never a git checkout):
  1. plant it (plant.py: found by file, function, kind and text, never by line number; the file's own text goes to a marker
     in the copy first);
  2. make the seed current the way packaging does (tools/package_graphite.py --manifest-only), so that no test can fail on
     the seed's source digest alone: a bug counts as caught only when a test fails on what the bug does. The recorded
     registry (docs/GRAPHITE_0.1_REGISTRY.json) is not written again: it records operations, settings and the code serving
     each, not source bytes (a comment changes nothing in it), so a test that finds the live registry changed has found
     behaviour. When packaging refuses the planted tree (a bug in the seed's own code), the modules run on the stale seed
     and every failure counts except the one test whose job is the seed's digest (DIGEST_TESTS);
  3. run the bug's test modules (bugs.json `modules`; a dotted name runs one class or one test), each in its own process at
     nice 19 in a private pid namespace with a fresh HOME and offscreen Qt, failfast, in the order listed, until one fails;
  4. put the file back from the marker and make the seed current again.
Verdicts: caught (a module failed), missed (all passed), timeout (a module ran out of time: counted apart), gone (the code
no longer holds the bug, or its file is gone), error (the bug could not be planted or run: the row says why; a later run
tries it again). A bug packaging refused carries refresh: the reason, beside its verdict; the report lists it apart with
the failing tests, for a person to read (a module that needs a current seed would fail on it too).

Stopping. Ctrl-C (or SIGTERM) stops at once: the tests running are ended, their bugs are put back and not written, and the
run exits with 130; start it again to carry on (bugs already written are skipped). A kill that cannot be caught leaves the
marker; the next run puts that file back and makes the seed current before anything else. A tree that cannot be made
current again stops the run with exit 1 and says why.

    python3 tools/planted_bugs/run.py --tree COPY [--tree COPY2] [--group guarding] [--ids M007 M008] [--out results.jsonl]
    python3 tools/planted_bugs/run.py --report results.jsonl

One worker per --tree (two copies: two processes at most). The results go to --out, by default COPY.planted_bugs.jsonl
beside the first copy. --python names the interpreter with PySide6 (default: this one). --all-modules runs every listed
module even after a catch. --plain drops nice/unshare where unshare is not allowed.
Bugs whose 0.8.2 verdict is `equivalent` (no behaviour can tell them apart) are left out unless named with --ids.
The report gives, per group, the bugs caught of those run (equivalent ones excluded), beside the 0.8.2 verdicts in bugs.json.

Not shipped: tools/package_graphite.py leaves tools/planted_bugs/ out of the kit.
"""
import argparse
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plant  # noqa: E402

REFRESH = (['tools/package_graphite.py', '--manifest-only'],)
REFRESH_SECONDS = 600
# The one test whose job is that the seed is current: on a stale seed it fails by design, so it never counts as a catch.
DIGEST_TESTS = ('tests_integrated.test_project_desk.Seed.test_the_seed_of_this_tree_is_current',)
FAILED_TEST = re.compile(r'^(FAIL|ERROR): (\S+) \((\S+)\)', re.M)
COUNTED = ('caught', 'missed', 'timeout')


class Stop:
    """The run's stop: set by Ctrl-C or SIGTERM (interrupted), or when a tree cannot be made current again (errors). The
    workers look at it between bugs and between modules; setting it also ends the test processes running now."""

    def __init__(self):
        self.event = threading.Event(); self.lock = threading.Lock(); self.children = set()
        self.errors = []; self.interrupted = False

    def is_set(self):
        return self.event.is_set()

    def set(self, error=None):
        with self.lock:
            if error: self.errors.append(error)
            else: self.interrupted = True
            self.event.set(); running = list(self.children)
        for child in running: end(child)

    def started(self, child):
        with self.lock:
            self.children.add(child); late = self.event.is_set()
        if late: end(child)

    def finished(self, child):
        with self.lock: self.children.discard(child)


def end(child):
    """End a test process and everything it started (its own session)."""
    try: os.killpg(child.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError): pass


def refresh(tree, python):
    """Make the seed current. Returns None, or the step that failed. Packaging runs in a session of its own, so a Ctrl-C
    never cuts it off half written."""
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    for step in REFRESH:
        try:
            done = subprocess.run([python, *step], cwd=tree, env=env, capture_output=True, text=True, timeout=REFRESH_SECONDS,
                                  start_new_session=True)
        except subprocess.TimeoutExpired:
            return ' '.join(step) + ': no answer in %d s' % REFRESH_SECONDS
        if done.returncode != 0: return ' '.join(step) + ': ' + (done.stderr or done.stdout)[-400:]
    return None


def run_module(tree, module, args, stop, stale=False):
    home = tempfile.mkdtemp(prefix='planted-home-')
    env = dict(os.environ, HOME=home, QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1')
    for name in ('PYTHONPATH', 'COVERAGE_PROCESS_START'): env.pop(name, None)
    command = [args.python, '-B', '-m', 'unittest'] + ([] if stale else ['-f']) + ['tests_integrated.' + module]
    if not args.plain: command = ['nice', '-n', '19', 'unshare', '--pid', '--fork', '--mount-proc', '--kill-child'] + command
    # In a session of its own (Ctrl-C reaches this run, which ends the test itself), and ended if this run is killed.
    if shutil.which('setpriv'): command = ['setpriv', '--pdeathsig', 'KILL', '--'] + command
    began = time.time()
    try:
        child = subprocess.Popen(command, cwd=tree, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                 start_new_session=True)
        stop.started(child)
        try:
            _, err = child.communicate(timeout=args.timeout)
            failing = ['%s %s' % (kind, test) for kind, _, test in FAILED_TEST.findall(err)]
            counted = [f for f in failing if f.split(' ', 1)[1] not in DIGEST_TESTS] if stale else failing
            verdict = 'passed' if child.returncode == 0 or (stale and failing and not counted) else 'failed'
            tail = err[-600:] if verdict == 'failed' else ''
        except subprocess.TimeoutExpired:
            end(child); child.communicate()
            verdict, failing, tail = 'timeout', [], ''
        finally:
            stop.finished(child)
    finally:
        shutil.rmtree(home, ignore_errors=True)
    return dict(verdict=verdict, sec=round(time.time() - began, 1), failing=failing[:5], tail=tail)


def one(tree, bug, args, stop):
    """Plant one bug, run its modules, put it back. Returns its row, or None when the run was stopped while it ran (its
    verdict would not be one: the bug is put back and tried again by the next run)."""
    row = dict(id=bug['id'], file=bug['file'], func=bug['func'], kind=bug['kind'], group=bug['group'],
               before=bug.get('verdict_0_8_2'), modules={})
    began = time.time()
    path, original, line = plant.plant(tree, bug)
    if line is None:
        return dict(row, verdict='gone', sec=0, why='the file is gone' if original is None else 'the code no longer holds it')
    row['line'] = line
    try:
        failed = refresh(tree, args.python)
        if failed: row['refresh'] = failed
        verdict = 'missed'
        for module in bug['modules']:
            if stop.is_set(): break
            result = run_module(tree, module, args, stop, stale=bool(failed))
            row['modules'][module] = result
            if result['verdict'] == 'failed':
                verdict = 'caught'
                if not args.all_modules: break
            elif result['verdict'] == 'timeout' and verdict == 'missed':
                verdict = 'timeout'
        row['verdict'] = verdict
        interrupted = stop.is_set()  # stopped while it ran (a Ctrl-C, or the other tree's error ended its tests)
    finally:
        plant.restore(tree)
        after = refresh(tree, args.python)
        if after: stop.set('the tree at %s could not be made current again after %s: %s' % (tree, bug['id'], after))
    if interrupted: return None
    row['sec'] = round(time.time() - began, 1)
    return row


def chosen(args):
    bugs = plant.load(args.bugs)
    if args.ids: return [b for b in bugs if b['id'] in set(args.ids)]
    return [b for b in bugs if (args.group == 'all' or b['group'] == args.group) and b.get('verdict_0_8_2') != 'equivalent'
            and (not args.before or b.get('verdict_0_8_2') in args.before)]


def rows_of(path):
    """The rows written so far, the last one for each bug (a bug tried again after an error replaces its row)."""
    rows = {}
    if Path(path).is_file():
        for line in Path(path).read_text().splitlines():
            if line.strip():
                row = json.loads(line); rows[row['id']] = row
    return rows


def report(path, bugs_path=plant.BUGS):
    rows = rows_of(path)
    bugs = {b['id']: b for b in plant.load(bugs_path)}
    out = {}
    for group in sorted({b['group'] for b in bugs.values()}):
        ran = [r for r in rows.values() if r['group'] == group and r['verdict'] in COUNTED and 'refresh' not in r]
        before = [b for b in bugs.values() if b['group'] == group and b.get('verdict_0_8_2') in ('caught', 'gap', 'digest_only')]
        out[group] = dict(
            now=dict(caught=sum(r['verdict'] == 'caught' for r in ran), timeout=sum(r['verdict'] == 'timeout' for r in ran),
                     run=len(ran), missed=sorted(r['id'] for r in ran if r['verdict'] == 'missed'),
                     apart=sorted('%s %s%s' % (r['id'], r['verdict'], (' on a stale seed: ' + '; '.join(
                         f for m in r['modules'].values() for f in m['failing'])[:300]) if 'refresh' in r else
                         (': ' + r.get('error', r.get('why', ''))) if r.get('error') or r.get('why') else '')
                         for r in rows.values() if r['group'] == group and (r['verdict'] not in COUNTED or 'refresh' in r))),
            at_0_8_2=dict(caught=sum(b['verdict_0_8_2'] == 'caught' for b in before), valid=len(before)))
    return out


def prepare(tree, python):
    """Before the first bug: put back what a stopped run left planted, and make the seed current."""
    plant.refuse_checkout(tree)
    put = plant.restore(tree)
    if put: print('put back %s, left planted in %s by a run that was stopped' % (put, tree), flush=True)
    failed = refresh(tree, python)
    if failed: raise SystemExit('the tree at %s cannot be made current, so no bug can be measured in it: %s' % (tree, failed))


def run(args, stop):
    """Run the chosen bugs, one worker per tree; returns the results file."""
    out = Path(args.out)
    done = {i for i, r in rows_of(out).items() if r['verdict'] != 'error'}
    todo = queue.Queue()
    for bug in chosen(args):
        if bug['id'] not in done: todo.put(bug)
    lock = threading.Lock()

    def worker(tree):
        while not stop.is_set():
            try: bug = todo.get_nowait()
            except queue.Empty: return
            try:
                row = one(tree, bug, args, stop)
            except Exception as error:  # a bug that cannot be planted or run is a row of its own, never a dead worker
                row = dict(id=bug['id'], file=bug['file'], func=bug['func'], kind=bug['kind'], group=bug['group'],
                           before=bug.get('verdict_0_8_2'), modules={}, verdict='error', sec=0,
                           error='%s: %s' % (type(error).__name__, error))
                if (Path(tree) / plant.MARKER).exists(): stop.set('%s was left planted in %s: %s' % (bug['id'], tree, row['error']))
            if row is None: return
            with lock:
                with out.open('a') as stream: stream.write(json.dumps(row) + '\n')
                print(row['id'], row['file'].rsplit('/', 1)[-1], row.get('line'), row['verdict'],
                      next((m for m, r in row['modules'].items() if r['verdict'] == 'failed'), ''), row['sec'], flush=True)

    threads = [threading.Thread(target=worker, args=(tree,), daemon=True) for tree in args.tree]
    for thread in threads: thread.start()
    for thread in threads:
        while thread.is_alive(): thread.join(0.5)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--tree', action='append', default=[])
    parser.add_argument('--bugs', default=str(plant.BUGS))
    parser.add_argument('--ids', nargs='*')
    parser.add_argument('--group', default='guarding', choices=('guarding', 'other', 'all'))
    parser.add_argument('--before', nargs='*', help='only bugs with these 0.8.2 verdicts (caught, gap, not_run, void)')
    parser.add_argument('--out', help='the results file (default: COPY.planted_bugs.jsonl beside the first copy)')
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--all-modules', action='store_true')
    parser.add_argument('--plain', action='store_true')
    parser.add_argument('--report')
    args = parser.parse_args(argv)
    if args.report:
        print(json.dumps(report(args.report, args.bugs), indent=1)); return 0
    if not args.tree: parser.error('name at least one --tree: a throwaway copy of the tree')
    first = Path(args.tree[0]).resolve()
    args.out = args.out or str(first.parent / (first.name + '.planted_bugs.jsonl'))
    stop = Stop()

    def stopping(signum, frame):
        if not stop.interrupted:
            print('Stopping: the tests running now are ended, their bugs put back and not written. Start again to carry on.',
                  file=sys.stderr, flush=True)
        stop.set()
    signal.signal(signal.SIGINT, stopping); signal.signal(signal.SIGTERM, stopping)
    for tree in args.tree: prepare(tree, args.python)
    print('results: ' + args.out, flush=True)
    out = run(args, stop)
    if stop.errors:
        for error in stop.errors: print(error, file=sys.stderr)
        return 1
    if stop.interrupted: return 130
    print(json.dumps(report(out, args.bugs), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
