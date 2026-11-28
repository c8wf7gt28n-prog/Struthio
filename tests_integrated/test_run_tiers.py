"""0.8.4: the checks in tiers (tools/run_tiers.py, its lists in tools/tiers.json; docs/CHECKS.md).

The lists: every test module is in tier 2, in both looks, and tier 0 is a part of it, with the modules that guard the
owner, each entry saying why; tier 2 runs the window checks the gate lists and the scene in each look. The import map on
a tree of its own: a test is chosen by a file it imports or names, or that its own helpers import or name; a file that is
not Python by the Python that names it as a whole word; a moved file under both its names; the map is kept, read again
only where a file changed, and made again when damaged. The runner on a tree of its own: each module in a child with an
empty home, the look given (Graphite's: nothing set) and none of the program's own variables from the shell; a failing
module fails the run with its message, one that ends mid-test or crashes is a failure, skipped tests are counted and
named; a module that outlives its time limit is stopped, with what it started, and is a failure, and what a module
started is stopped at its end too; window checks, the scene, the release check's sections and the sweep are read from
what they report; an interrupted run stops what runs at once and writes what it has; the result file and the last
line. No window is made.
"""
import ast
import contextlib
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import check_hatch
from tools import run_tiers as tiers

ROOT = tiers.ROOT


def write(root, files):
    for name, text in files.items():
        path = Path(root) / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(textwrap.dedent(text))


class TheLists(unittest.TestCase):
    def setUp(self):
        self.cfg = tiers.config()

    def test_every_test_module_is_in_tier_2_in_both_looks_and_tier_0_is_a_part_of_it(self):
        shipped = {path.stem for path in (ROOT / 'tests_integrated').glob('test_*.py')}
        units, _ = tiers.plan(2, tiers.LOOKS, self.cfg)
        two = {u['name'] for u in units if u['kind'] == 'module'}
        self.assertEqual(shipped - two, set(), 'a test module tier 2 does not run')
        self.assertEqual(two - shipped, set(), 'tier 2 names a module that is not there')
        once = self.cfg['2']['once']
        for name in two:
            self.assertEqual(sorted(u['look'] for u in units if u['kind'] == 'module' and u['name'] == name),
                             [tiers.LOOKS[0]] if name in once else sorted(tiers.LOOKS), name)
        zero = [row['module'] for row in self.cfg['0']['modules']]
        self.assertEqual(len(zero), len(set(zero)), 'a module twice in tier 0'); self.assertLessEqual(set(zero), two)
        for row in self.cfg['0']['modules']:
            self.assertGreater(len(row.get('why', '')), 20, row['module'])
            if row.get('classes'):        # a part of a module: the classes must be there, or tier 0 would run nothing of it
                tree = ast.parse((ROOT / 'tests_integrated' / (row['module'] + '.py')).read_text())
                self.assertLessEqual(set(row['classes']), {n.name for n in tree.body if isinstance(n, ast.ClassDef)}, row['module'])
        for reason in once.values():
            self.assertIn('both looks', reason)

    def test_tier_0_always_holds_what_guards_the_owner(self):
        zero = {row['module'] for row in self.cfg['0']['modules']}
        # her hand's rules, the memory rules, release integrity, the seed being current, one name, the Kernel's scopes
        for name in ('test_stacy_hand', 'test_resource_rules', 'test_release_check', 'test_project_desk', 'test_one_name', 'test_network_watch'):
            self.assertIn(name, zero)

    def test_tier_2_runs_the_gates_window_checks_and_the_scene_in_each_look_and_the_sweep_once(self):
        units, _ = tiers.plan(2, tiers.LOOKS, self.cfg)
        for look in tiers.LOOKS:
            self.assertEqual([u['name'] for u in units if u['kind'] == 'check' and u['look'] == look], list(check_hatch.UI_CHECKS))
            self.assertEqual([u['name'] for u in units if u['kind'] == 'scene' and u['look'] == look], ['DP01a,DP01b,DP01c,DP01d'])
        self.assertEqual([(u['kind'], u['name']) for u in units if u['kind'] in ('sweep', 'integrity')],
                         [('integrity', 'tools/check_release.py'), ('sweep', 'tools/name_sweep.py')])
        one, _ = tiers.plan(2, ['kasandra'], self.cfg)
        self.assertEqual({u['look'] for u in one}, {'kasandra'})
        self.assertEqual(len([u for u in one if u['kind'] == 'module']), len({u['name'] for u in units if u['kind'] == 'module'}))

    def test_tier_1_is_tier_0_when_nothing_changed_and_adds_what_imports_a_change(self):
        zero, _ = tiers.plan(0, ['graphite'], self.cfg)
        same, chosen = tiers.plan(1, ['graphite'], self.cfg, [], imports={})
        self.assertEqual((same, chosen), (zero, {}))
        imports = tiers.import_map(ROOT, cache=False)
        units, chosen = tiers.plan(1, ['graphite'], self.cfg, ['tools/run_tiers.py', 'MANIFEST.json'], imports=imports)
        # 1.1 T1: test_tiers_green holds the runner's looks too
        self.assertEqual(chosen, {'tests_integrated/test_run_tiers.py': ['tools/run_tiers.py'], 'tests_integrated/test_tiers_green.py': ['tools/run_tiers.py']},
                         'MANIFEST.json follows the source: tier 0 reads it')
        self.assertEqual(units[:len(zero)], zero)
        self.assertEqual(sorted(u['name'] for u in units[len(zero):]), ['test_run_tiers', 'test_tiers_green'])
        # a module tier 0 runs a part of runs whole when a change imports it
        units, _ = tiers.plan(1, ['graphite'], self.cfg, ['tests_integrated/test_one_name.py'], imports=imports)
        self.assertEqual([u for u in units if u['name'] == 'test_one_name'], [{'kind': 'module', 'name': 'test_one_name', 'classes': [], 'look': 'graphite'}])


class TheImportMap(unittest.TestCase):
    TREE = {
        'workbench/__init__.py': '',
        'workbench/alpha.py': 'from . import beta\nVALUE = beta.VALUE\n',
        'workbench/beta.py': 'VALUE = 7\n',
        'workbench/gamma.py': 'from pathlib import Path\nWORDS = Path(__file__).parent / "data" / "words.json"\n',
        'workbench/data/words.json': '[]\n',
        'tools/helper.py': 'from workbench import gamma\n',
        'tests_integrated/test_a.py': 'import unittest\nfrom workbench import alpha\n',
        'tests_integrated/test_b.py': 'import unittest\nfrom tools import helper\n',
        'tests_integrated/test_c.py': 'import unittest\nfrom unittest.mock import patch\nPATCHED = patch("workbench.beta.VALUE", 8)\n',
        'tests_integrated/test_d.py': 'import unittest\nimport subprocess\nRUN = ["python3", "workbench/beta.py"]\nGUIDE = "docs/WINDOW_CHECKS.md"\n',
        'tests_integrated/test_e.py': 'def broken(:\n',
        'docs/CHECKS.md': '', 'docs/WINDOW_CHECKS.md': '',
        'wip/notes.md': 'workbench/alpha.py\n'}
    UNITS = ['tests_integrated/test_%s.py' % x for x in 'abcde']

    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); self.root = Path(temp.name); write(self.root, self.TREE)
        self.imports = tiers.import_map(self.root, cache=False)

    def chosen(self, *changed, ignored=()):
        return {Path(unit).stem: hit for unit, hit in tiers.dependents(list(changed), self.UNITS, self.root, self.imports, ignored).items()}

    def test_a_test_is_chosen_by_what_it_imports_or_names_and_by_what_its_helpers_do(self):
        self.assertEqual(tiers.direct('workbench/alpha.py', self.imports, set(self.imports)), {'workbench/__init__.py', 'workbench/beta.py'}, 'from . import beta')
        self.assertEqual(self.chosen('workbench/alpha.py'), {'test_a': ['workbench/alpha.py']})
        # beta is imported by alpha, a file of the program: following the program's own imports would choose every module
        self.assertEqual(self.chosen('workbench/beta.py'), {'test_c': ['workbench/beta.py'], 'test_d': ['workbench/beta.py']})
        self.assertEqual(self.chosen('workbench/gamma.py'), {'test_b': ['workbench/gamma.py']}, 'through its helper in tools/')
        self.assertEqual(self.chosen('tools/helper.py'), {'test_b': ['tools/helper.py']})
        self.assertEqual(self.chosen('tests_integrated/test_e.py'), {'test_e': ['tests_integrated/test_e.py']}, 'a file that does not parse still counts as itself')
        self.assertEqual(self.chosen('workbench/__init__.py'), {'test_a': ['workbench/__init__.py'], 'test_b': ['workbench/__init__.py'], 'test_c': ['workbench/__init__.py']})

    def test_a_file_that_is_not_python_is_followed_to_the_python_that_names_it_and_the_ignored_are_not(self):
        self.assertEqual(self.chosen('workbench/data/words.json'), {'test_b': ['workbench/data/words.json']})
        self.assertEqual(self.chosen('docs/WINDOW_CHECKS.md'), {'test_d': ['docs/WINDOW_CHECKS.md']})
        self.assertEqual(self.chosen('docs/CHECKS.md'), {}, 'a name inside a longer name is not that name')
        self.assertEqual(self.chosen('wip/notes.md', 'MANIFEST.json', ignored=('wip/', 'MANIFEST.json')), {})
        self.assertEqual(self.chosen(), {})

    def test_the_map_is_kept_and_read_again_only_where_a_file_changed(self):
        cache = self.root.parent / (self.root.name + '-map.json'); self.addCleanup(lambda: cache.unlink(missing_ok=True))
        first = tiers.import_map(self.root, cache=cache); self.assertEqual(first, self.imports)
        self.assertEqual(json.loads(cache.read_text())['files']['tests_integrated/test_a.py']['names'], ['unittest', 'workbench', 'workbench.alpha'])
        with patch.object(tiers, 'references', side_effect=AssertionError('read again')):
            self.assertEqual(tiers.import_map(self.root, cache=cache), first, 'nothing changed: nothing is read again')
        (self.root / 'tests_integrated/test_d.py').write_text('from workbench import gamma\n')
        read = []; real = tiers.references
        with patch.object(tiers, 'references', side_effect=lambda name, text: read.append(name) or real(name, text)):
            again = tiers.import_map(self.root, cache=cache)
        self.assertEqual(read, ['tests_integrated/test_d.py']); self.assertIn('workbench.gamma', again['tests_integrated/test_d.py']['names'])
        stat = (self.root / 'tests_integrated/test_a.py').stat()
        for damaged in ('not json', '[1, 2]', '{"format": 1, "files": []}', '{"format": 1, "files": "x"}',
                        json.dumps({'format': 1, 'files': {'tests_integrated/test_a.py': {'stamp': [stat.st_mtime_ns, stat.st_size]}}})):
            cache.write_text(damaged); self.assertEqual(tiers.import_map(self.root, cache=cache), again, 'a damaged map is made again: ' + damaged)

    def test_the_changed_files_are_what_differs_from_the_commit_and_what_git_does_not_know(self):
        git = ['git', '-C', str(self.root), '-c', 'user.name=tester', '-c', 'user.email=tester@example.invalid', '-c', 'commit.gpgsign=false']
        for args in (['init', '-q'], ['add', '-A'], ['commit', '-q', '-m', 'tree']):
            subprocess.run(git + args, check=True, capture_output=True)
        (self.root / 'workbench/beta.py').write_text('VALUE = 8\n'); (self.root / 'workbench/delta.py').write_text('')
        (self.root / 'tests_integrated/test_e.py').unlink()
        self.assertEqual(tiers.changed_files('HEAD', self.root), ['tests_integrated/test_e.py', 'workbench/beta.py', 'workbench/delta.py'])
        # a file moved counts under both names: the test that imports the old one is the one the move breaks
        subprocess.run(git + ['mv', 'workbench/alpha.py', 'workbench/omega.py'], check=True, capture_output=True)
        changed = tiers.changed_files('HEAD', self.root)
        self.assertEqual(changed, ['tests_integrated/test_e.py', 'workbench/alpha.py', 'workbench/beta.py', 'workbench/delta.py', 'workbench/omega.py'])
        self.assertIn('tests_integrated/test_a.py', tiers.dependents(changed, self.UNITS, self.root, tiers.import_map(self.root, cache=False)))
        with self.assertRaises(SystemExit):
            tiers.changed_files('no-such-commit', self.root)


SLOW_CHILD = 'import sys, time\nfrom pathlib import Path\ntime.sleep(float(sys.argv[2]))\nPath(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)\nPath(sys.argv[1]).write_text("outlived")\n'
FAKE = {
    'tests_integrated/slow.py': '''
        import os, subprocess, sys
        from pathlib import Path
        def start_slow(name):
            """Start a process and leave it: it writes a mark if it outlives the delay it is given."""
            marks = Path(os.environ.get('TIER_TEST_MARKS') or Path(__file__).parents[2] / 'marks')
            subprocess.Popen([sys.executable, str(Path(__file__).with_name('slow_child.py')), str(marks / name), os.environ.get('TIER_TEST_DELAY', '4')])
        ''',
    'tests_integrated/test_pass.py': '''
        import os, unittest
        class Pass(unittest.TestCase):
            def test_its_own_empty_home_offscreen(self):
                self.assertEqual(os.listdir(os.environ['HOME']), []); self.assertEqual(os.environ['QT_QPA_PLATFORM'], 'offscreen')
            def test_nothing_of_the_programs_own_passes_from_the_shell(self):
                own = ('ARC_LEDGER_', 'ARC1_WORKBENCH_', 'LEDGER_', 'GRAPHITE_')
                self.assertEqual([k for k in os.environ if k.startswith(own) and k != 'GRAPHITE_APPEARANCE'], [])
        ''',
    'tests_integrated/test_look.py': '''
        import os, unittest
        class Kas(unittest.TestCase):
            def test_the_look_it_was_given(self):
                self.assertEqual(os.environ.get('GRAPHITE_APPEARANCE'), 'kasandra')
        class Default(unittest.TestCase):
            def test_graphite_is_named_too(self):      # 1.1 T1: unset, a fresh profile starts in Day (1.0 D1), so Kas is named
                self.assertEqual(os.environ.get('GRAPHITE_APPEARANCE'), 'graphite')
        ''',
    'tests_integrated/test_fail.py': '''
        import unittest
        class Fail(unittest.TestCase):
            def test_one_passes(self):
                pass
            def test_seven(self):
                """A docstring's first line is printed above the traceback."""
                self.assertEqual(7, 6, 'seven is not six')
        ''',
    'tests_integrated/test_slow.py': '''
        import time, unittest
        from tests_integrated.slow import start_slow
        class Slow(unittest.TestCase):
            def test_waits_too_long(self):
                start_slow('slow'); time.sleep(60)
        ''',
    'tests_integrated/test_sleep.py': '''
        import time, unittest
        class Sleep(unittest.TestCase):
            def test_waits_too_long(self):
                time.sleep(60)
        ''',
    'tests_integrated/test_leaves.py': '''
        import unittest
        from tests_integrated.slow import start_slow
        class Leaves(unittest.TestCase):
            def test_starts_a_process_and_ends(self):
                start_slow('left')
        ''',
    'tests_integrated/test_exits.py': '''
        import os, unittest
        class Exits(unittest.TestCase):
            def test_ends_the_process_mid_test(self):
                os._exit(0)
        ''',
    'tests_integrated/test_nested.py': '''
        import sys, unittest
        class Nested(unittest.TestCase):
            def test_prints_a_summary_of_its_own(self):
                sys.stderr.write('\\nRan 99 tests in 0.001s\\n\\nOK\\n')
        ''',
    'tests_integrated/test_skips.py': '''
        import unittest
        class Skips(unittest.TestCase):
            @unittest.skip('needs a solver this machine lacks')
            def test_one(self):
                pass
            @unittest.skip('needs a solver this machine lacks')
            def test_two(self):
                pass
        ''',
    'tests_integrated/test_broken.py': 'import no_such_module_here\n',
    # the other kinds of unit: window checks, the scene, the release check's sections and the sweep
    # (named window_*, not as the gate's checks are: test_release_check holds every such name in the tests to a real check)
    'tools/window_good.py': 'import json\nprint(json.dumps({"state": "PASSED", "checks": ["a", "b"]}))\n',
    'tools/window_silent.py': 'print("the window opened")\n',
    'tools/window_narrow.py': 'import json\nprint(json.dumps({"state": "FAILED", "error": "Apps needs 96 px, has 79", "checks": ["a"]}))\n',
    'tools/campaign.py': '''
        import json, sys
        from pathlib import Path
        cases = sys.argv[sys.argv.index('--case') + 1].split(','); out = Path(sys.argv[sys.argv.index('--out') + 1]); out.mkdir(parents=True, exist_ok=True)
        rows = [{'case': cases[0], 'outcome': 'Pass'}, {'case': cases[1], 'outcome': 'Blocked', 'reason': 'the model is not there'}]
        (out / 'results.jsonl').write_text(''.join(json.dumps(row) + '\\n' for row in rows))
        ''',
    'tools/check_release.py': 'raise SystemExit("the payload could not be read")\n',
    'tools/name_sweep.py': 'import sys\nprint("an earlier name in workbench/x.py")\nsys.exit(1)\n'}
# tools/run_tiers.py's own main() on the fake tree, in a process of its own, so that it can be interrupted
INTERRUPTIBLE = '''
import json, signal, sys
from pathlib import Path
signal.signal(signal.SIGINT, signal.default_int_handler)       # as at a terminal, whatever the test's own process ignores
sys.path.insert(0, sys.argv[1])
from tools import run_tiers as tiers
tiers.ROOT = Path(sys.argv[2]); cfg = json.loads(sys.argv[3]); tiers.config = lambda root=None: cfg
sys.exit(tiers.main(['0', '--look', 'kasandra', '--out', sys.argv[4]]))
'''


class TheRunner(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); self.base = Path(temp.name)
        self.root = self.base / 'tree'; self.out = self.base / 'out'; self.marks = self.base / 'marks'; write(self.root, FAKE)
        (self.root / 'tests_integrated/slow_child.py').write_text(SLOW_CHILD)
        self.cfg = {'timeout_seconds': {'module': 60}, 'seconds': {'test_slow': 90}}

    def unit(self, name, look='kasandra', classes=()):
        return {'kind': 'module', 'name': name, 'classes': list(classes), 'look': look}

    def outlived(self):
        return sorted(path.name for path in self.marks.glob('*'))

    def test_each_module_in_a_child_of_its_own_a_failure_with_its_message_and_a_time_limit_is_a_failure(self):
        units = [self.unit(n) for n in ('test_pass', 'test_fail', 'test_slow', 'test_broken', 'test_exits', 'test_nested', 'test_skips', 'test_leaves')]
        units += [self.unit('test_look', 'kasandra', ['Kas']), self.unit('test_look', 'graphite', ['Default'])]
        elsewhere = str(self.base / 'elsewhere')         # what the shell that starts a run may hold: none of it reaches a test
        shell = {'GRAPHITE_APPEARANCE': 'kasandra', 'ARC_LEDGER_WORKSPACE': elsewhere, 'ARC1_WORKBENCH_CONFIG_HOME': elsewhere,
                 'ARC_LEDGER_EDITION': 'service', 'LEDGER_QUALIFICATION_SECRET': 'not for tests', 'GRAPHITE_CAMPAIGN_FIXTURES': elsewhere}
        began = time.monotonic()
        with patch.dict(os.environ, shell):
            rows = tiers.run_all(units, self.root, self.out, self.cfg, workers=2, timeout=3)
        self.assertLess(time.monotonic() - began, 40)
        self.assertEqual([(r['module'], r['look'], r['ran'], r['failed'], r['skipped'], r['state']) for r in rows],
                         [('test_pass', 'kasandra', 2, 0, 0, 'PASSED'), ('test_fail', 'kasandra', 2, 1, 0, 'FAILED'),
                          ('test_slow', 'kasandra', 0, 1, 0, 'TIMEOUT'), ('test_broken', 'kasandra', 1, 1, 0, 'FAILED'),
                          ('test_exits', 'kasandra', 0, 1, 0, 'FAILED'),     # it ended mid-test, with exit 0 and no word of unittest's
                          ('test_nested', 'kasandra', 1, 0, 0, 'PASSED'),    # the 'Ran 99 tests' it printed is not the count
                          ('test_skips', 'kasandra', 2, 0, 2, 'PASSED'), ('test_leaves', 'kasandra', 1, 0, 0, 'PASSED'),
                          ('test_look (Kas)', 'kasandra', 1, 0, 0, 'PASSED'), ('test_look (Default)', 'graphite', 1, 0, 0, 'PASSED')])
        self.assertTrue(all(isinstance(r['seconds'], float) and (self.out / r['log']).is_file() for r in rows))
        failure = rows[1]['failures']
        self.assertEqual(len(failure), 1); self.assertIn('test_fail.Fail.test_seven', failure[0]['test'])
        self.assertIn('AssertionError: 7 != 6 : seven is not six', failure[0]['message'])
        self.assertLess(rows[2]['seconds'], 15); self.assertEqual(rows[2]['failures'][0]['message'], 'stopped at its time limit')
        self.assertIn('no_such_module_here', rows[3]['failures'][0]['message'])
        self.assertFalse((self.base / 'elsewhere').exists())
        time.sleep(5)
        self.assertEqual(self.outlived(), [], 'what a module started was stopped with it, at its time limit and at its end')
        self.assertEqual(tiers.last_line(rows), '4 failing: kasandra test_fail; kasandra test_slow; kasandra test_broken; kasandra test_exits; '
                                                '2 skipped: kasandra test_skips (2)')
        self.assertEqual(tiers.last_line(rows[:1]), '0 failing')
        self.assertIn(' skipped ', tiers.table(rows)[0])

    def test_without_a_process_namespace_the_process_group_is_stopped_whole_at_the_limit_and_at_the_end(self):
        # where unshare cannot make a namespace (a normal user on most machines), the child leads a process group of its own
        with patch.dict(tiers._ISOLATION, {'prefix': [], 'kind': 'process group'}, clear=True):
            rows = tiers.run_all([self.unit('test_slow'), self.unit('test_leaves')], self.root, self.out, self.cfg, workers=2, timeout=2)
        self.assertEqual([(r['state'], r['failed']) for r in rows], [('TIMEOUT', 1), ('PASSED', 0)]); self.assertLess(rows[0]['seconds'], 12)
        time.sleep(5)
        self.assertEqual(self.outlived(), [], 'what a module started was stopped with it, at its time limit and at its end')

    def test_the_window_checks_the_scene_the_release_sections_and_the_sweep_are_read_from_what_they_report(self):
        self.out.mkdir(parents=True)        # an earlier run's report in the same folder, all passed: it is not this run's
        (self.out / 'release_check.json').write_text(json.dumps({'state': 'PASSED', 'failed_sections': [], 'payload': {'state': 'PASSED'}}))
        units = [{'kind': 'check', 'name': 'tools/window_%s.py' % name, 'look': 'kasandra'} for name in ('good', 'silent', 'narrow')]
        units += [{'kind': 'scene', 'name': 'P01a,P01b,P01c', 'look': 'kasandra'}, {'kind': 'integrity', 'name': 'tools/check_release.py', 'look': 'kasandra'},
                  {'kind': 'sweep', 'name': 'tools/name_sweep.py', 'look': 'kasandra'}]
        rows = tiers.run_all(units, self.root, self.out, self.cfg, workers=2, timeout=60)
        self.assertEqual([(r['ran'], r['failed'], r['state']) for r in rows],
                         [(2, 0, 'PASSED'), (0, 1, 'FAILED'), (1, 1, 'FAILED'), (2, 2, 'FAILED'), (0, 1, 'FAILED'), (1, 1, 'FAILED')])
        said = [[(f['test'], f['message']) for f in r['failures']] for r in rows]
        self.assertEqual(said[1], [('tools/window_silent.py', 'no report: the window opened')])
        self.assertEqual(said[2], [('tools/window_narrow.py', 'Apps needs 96 px, has 79')])
        self.assertEqual(said[3][0], ('P01b', 'Blocked: the model is not there'), 'Blocked is not passed')
        self.assertIn('2 of 3 cases reported', said[3][1][1])
        self.assertEqual(said[4], [('tools/check_release.py', 'no report')]); self.assertFalse((self.out / 'release_check.json').exists())
        self.assertEqual(said[5], [('tools/name_sweep.py', 'an earlier name in workbench/x.py')])
        # the runner's own fault (a full disk, say) is a failing row that says so, not a lost one
        with patch.object(tiers, 'read_result', side_effect=OSError(28, 'No space left on device')):
            row, = tiers.run_all([self.unit('test_pass')], self.root, self.out, self.cfg, workers=1, timeout=60)
        self.assertEqual((row['state'], row['failed']), ('FAILED', 1)); self.assertIn('No space left on device', row['failures'][0]['message'])

    def test_an_interrupted_run_stops_what_runs_with_what_it_started_and_says_what_was_not_run(self):
        zero = {'modules': [{'module': 'test_slow', 'why': ''}, {'module': 'test_sleep', 'why': ''}, {'module': 'test_pass', 'why': ''}]}
        runs = []
        # once and twice: Ctrl-C at a terminal; killed: the run itself killed outright, its children end at their limit anyway
        for name, signals in (('once', [signal.SIGINT]), ('twice', [signal.SIGINT, signal.SIGINT]), ('killed', [signal.SIGKILL])):
            cfg = {'0': zero, 'timeout_seconds': {'module': 2 if name == 'killed' else 60}, 'timeout_grace_seconds': 1}
            folder = self.base / name; (folder / 'tmp').mkdir(parents=True)
            env = {**os.environ, 'TMPDIR': str(folder / 'tmp'), 'TIER_TEST_MARKS': str(folder / 'marks'), 'TIER_TEST_DELAY': '5'}
            child = subprocess.Popen([sys.executable, '-B', '-c', INTERRUPTIBLE, str(ROOT), str(self.root), json.dumps(cfg), str(folder / 'out')],
                                     env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            self.addCleanup(lambda c=child: c.poll() is None and os.killpg(c.pid, signal.SIGKILL))
            deadline = time.monotonic() + 30
            while len(list((folder / 'tmp').glob('graphite-tier-*'))) < 2 and child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)        # each unit's own home folder is made just before it starts
            time.sleep(0.4); began = time.monotonic()
            for number in signals:
                child.send_signal(number); time.sleep(0.3)
            runs.append((name, folder, child, began))
        for name, folder, child, began in runs:
            if name == 'killed':
                child.wait(timeout=30); continue
            printed, said = child.communicate(timeout=30)
            self.assertLess(time.monotonic() - began, 15, 'the run stops at once, not when its units end')
            self.assertEqual(child.returncode, 130, said[-600:]); self.assertNotIn('Traceback', said)
            result = json.loads((folder / 'out' / 'tier0.json').read_text())
            self.assertEqual((result['state'], result['not_run']), ('INTERRUPTED', 1))
            self.assertEqual([(r['module'], r['state'], r['failed']) for r in result['rows']],
                             [('test_slow', 'INTERRUPTED', 1), ('test_sleep', 'INTERRUPTED', 1), ('test_pass', 'NOT RUN', 0)])
            self.assertEqual(result['rows'][0]['failures'][0]['message'], 'stopped: the run was interrupted')
            self.assertTrue(printed.splitlines()[-1].startswith('interrupted, 1 of 3 not run; 2 failing: '), printed[-300:])
            self.assertEqual(list((folder / 'tmp').glob('graphite-tier-*')), [], 'each child\'s home and temporary folder is removed')
        time.sleep(max(0.0, runs[-1][3] + 7 - time.monotonic()))
        for name, folder, child, began in runs:
            self.assertEqual(list((folder / 'marks').glob('*')), [], '%s: what a stopped module started was stopped with it' % name)

    def test_the_run_writes_its_result_file_prints_one_table_and_fails_when_a_module_fails(self):
        def run(names, out):
            printed = io.StringIO()
            with patch.object(tiers, 'ROOT', self.root), patch.object(tiers, 'config', return_value=self.cfg), \
                    patch.object(tiers, 'plan', return_value=([self.unit(n) for n in names], {})), \
                    contextlib.redirect_stdout(printed), contextlib.redirect_stderr(io.StringIO()):
                code = tiers.main(['0', '--look', 'kasandra', '--out', str(out), '--timeout', '30'])
            return code, printed.getvalue().splitlines(), json.loads((out / 'tier0.json').read_text())
        code, lines, result = run(['test_pass', 'test_fail'], self.out / 'one')
        self.assertEqual((code, lines[-1], result['state'], result['failing'], result['tests_run']), (1, '1 failing: kasandra test_fail', 'FAILED', 1, 4))
        self.assertEqual([{k: r[k] for k in ('module', 'look', 'ran', 'failed')} for r in result['rows']],
                         [{'module': 'test_pass', 'look': 'kasandra', 'ran': 2, 'failed': 0}, {'module': 'test_fail', 'look': 'kasandra', 'ran': 2, 'failed': 1}])
        self.assertTrue(lines[0].startswith('look ')); self.assertTrue(any('seven is not six' in line for line in lines))
        code, lines, result = run(['test_pass'], self.out / 'two')
        self.assertEqual((code, lines[-1], result['state']), (0, '0 failing', 'PASSED'))
        link = self.base / 'link'; link.symlink_to(self.root, target_is_directory=True)
        for inside in (self.root / 'build' / 'run', self.base / 'other' / '..' / 'tree' / 'build', link / 'build'):
            with patch.object(tiers, 'ROOT', self.root), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit, msg=str(inside)):
                tiers.main(['0', '--out', str(inside)])
        self.assertFalse((self.root / 'build').exists(), 'a run writes nothing into the program folder, by any way of naming it')

    def test_a_change_of_message_is_a_difference_and_the_same_failure_is_not(self):
        row = {'module': 'test_fail', 'look': 'graphite', 'ran': 2, 'failed': 1, 'state': 'FAILED', 'failures': [{'test': 'FAIL t', 'message': 'Apps needs 96 px, has 79'}]}
        self.assertEqual(tiers.differences([row], [row]), [])
        moved = {**row, 'failures': [{'test': 'FAIL t', 'message': 'Apps needs 96 px, has 60'}]}
        self.assertEqual(tiers.differences([row], [moved]), ['graphite test_fail: FAIL t now says: Apps needs 96 px, has 60'])
        fixed = {**row, 'failed': 0, 'state': 'PASSED', 'failures': []}
        self.assertEqual(tiers.differences([row], [fixed]), ['graphite test_fail: passed, was failed'])
        self.assertEqual(tiers.differences([], [fixed]), ['graphite test_fail: new, passed']); self.assertEqual(tiers.differences([row], []), ['graphite test_fail: not run this time'])


if __name__ == '__main__':
    unittest.main()
