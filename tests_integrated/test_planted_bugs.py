"""0.8.4: tools/planted_bugs, the rerun of planted bugs that measures the tests. It is kept in the tree and never shipped,
so in a kit, which has no tools/planted_bugs, this module says so and does not run.

On an invented tree of its own (one rule, one test of it, and a stand-in for packaging that counts its calls), run.py is
held to what makes its number one to believe: a bug left planted by a run that was killed is put back before the next run
measures anything; a bug whose file is gone is `gone` and the run goes on; Ctrl-C stops at once, writes nothing for the
bug it cut off and leaves the tree as it was; a tree that cannot be made current again stops the run, names the bug and
the tree, and exits with 1."""
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / 'tools/planted_bugs'
RULE = '"""A rule of an invented tree."""\n\n\ndef allowed(count):\n    return count <= 3\n\n\ndef spare(count):\n    return count + 1\n'
TEST = ('import os\nimport time\nimport unittest\nfrom pathlib import Path\nfrom pkg import rule\n\n\n'
        'class Rule(unittest.TestCase):\n    def test_three_is_allowed(self):\n'
        '        if os.environ.get("PLANTED_HOLD"):\n            Path(os.environ["PLANTED_HOLD"]).write_text("running"); time.sleep(60)\n'
        '        self.assertTrue(rule.allowed(3))\n')
PACKAGING = ('import os\nimport sys\nfrom pathlib import Path\ncount = Path("refreshed")\n'
             'n = int(count.read_text()) + 1 if count.exists() else 1\ncount.write_text(str(n))\n'
             'sys.exit(3 if str(n) == os.environ.get("PLANTED_REFRESH_FAILS_AT") else 0)\n')
BUGS = [dict(id='B0', file='pkg/moved.py', func='allowed', kind='cmp', old=' <= ', new=' < '),
        dict(id='B1', file='pkg/rule.py', func='allowed', kind='cmp', old=' <= ', new=' < '),
        dict(id='B2', file='pkg/rule.py', func='spare', kind='num', old='1', new='2')]


def setUpModule():
    if not (TOOLS / 'run.py').is_file():
        raise unittest.SkipTest('tools/planted_bugs is kept in the tree and never shipped; this folder has none')


class Rerun(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='graphite-planted-'); base = Path(self.temp.name)
        self.tree = base / 'copy'; self.out = base / 'rows.jsonl'; self.bugs = base / 'bugs.json'
        for name, text in (('pkg/__init__.py', ''), ('pkg/rule.py', RULE), ('tests_integrated/__init__.py', ''),
                           ('tests_integrated/test_rule.py', TEST), ('tools/package_graphite.py', PACKAGING)):
            (self.tree / name).parent.mkdir(parents=True, exist_ok=True); (self.tree / name).write_text(text)
        self.bugs.write_text(json.dumps({'bugs': [dict(b, group='guarding', modules=['test_rule'], verdict_0_8_2='gap') for b in BUGS]}))

    def tearDown(self):
        self.temp.cleanup()

    def command(self, *ids):
        return [sys.executable, '-B', str(TOOLS / 'run.py'), '--tree', str(self.tree), '--bugs', str(self.bugs), '--out', str(self.out),
                '--plain', '--ids', *ids]

    def run_bugs(self, *ids, **env):
        done = subprocess.run(self.command(*ids), capture_output=True, text=True, timeout=120, env=dict(os.environ, **env))
        return done, self.rows()

    def rows(self):
        return {r['id']: r for r in map(json.loads, self.out.read_text().splitlines())} if self.out.exists() else {}

    def clean(self):
        self.assertEqual((self.tree / 'pkg/rule.py').read_text(), RULE, 'the rule is back as it was')
        self.assertFalse((self.tree / 'tools/planted_bugs/.planted.json').exists(), 'no bug is left marked as planted')

    def test_a_bug_left_planted_by_a_killed_run_is_put_back_before_the_next_run_measures(self):
        spec = importlib.util.spec_from_file_location('planted_bugs_plant', TOOLS / 'plant.py')
        plant = importlib.util.module_from_spec(spec); spec.loader.exec_module(plant)
        plant.plant(self.tree, dict(BUGS[1], group='guarding', modules=['test_rule']))  # and then the run is killed
        self.assertNotEqual((self.tree / 'pkg/rule.py').read_text(), RULE, 'what a killed run leaves')
        done, rows = self.run_bugs('B2')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(rows['B2']['verdict'], 'missed', 'B2 is measured on the rule as it is, not with B1 still in it')
        self.clean()

    def test_a_bug_whose_file_is_gone_is_gone_and_the_run_goes_on(self):
        done, rows = self.run_bugs('B0', 'B1')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual({i: r['verdict'] for i, r in rows.items()}, {'B0': 'gone', 'B1': 'caught'})
        self.clean()

    def test_ctrl_c_stops_at_once_writes_nothing_for_the_bug_it_cut_off_and_puts_it_back(self):
        hold = Path(self.temp.name) / 'running'
        run = subprocess.Popen(self.command('B1', 'B2'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               env=dict(os.environ, PLANTED_HOLD=str(hold)))
        try:
            deadline = time.time() + 60
            while not hold.exists() and run.poll() is None and time.time() < deadline: time.sleep(0.05)
            self.assertTrue(hold.exists(), 'the test of B1 started')
            began = time.time(); run.send_signal(signal.SIGINT); run.communicate(timeout=40)
        finally:
            if run.poll() is None: run.kill(); run.communicate()
        self.assertLess(time.time() - began, 30, 'stopped at once, not when the cut-off test would have ended')
        self.assertEqual(run.returncode, 130)
        self.assertEqual(self.rows(), {}, 'a test cut off proves nothing: no row for B1, and B2 never started')
        self.clean()

    def test_a_tree_that_cannot_be_made_current_again_stops_the_run_and_says_so(self):
        # the stand-in's calls: 1 before the first bug, 2 with B1 planted, 3 with B1 put back
        done, rows = self.run_bugs('B1', 'B2', PLANTED_REFRESH_FAILS_AT='3')
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn('B1', done.stderr); self.assertIn(str(self.tree), done.stderr)
        self.assertEqual({i: r['verdict'] for i, r in rows.items()}, {'B1': 'caught'}, 'B1 was measured; B2 is not run on that tree')
        self.clean()


if __name__ == '__main__':
    unittest.main()
