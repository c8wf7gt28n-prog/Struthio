"""The campaign runner end to end: resource cases, a resume, a timeout, a breaking case, honest outcomes, the needs.

Each case runs exactly as `tools/campaign.py run` runs it: one child process per attempt in its own disposable
folder, killed at its budget. The anchors that need the owner's After Hours 07 backup are not run here (it is owner
data, not shipped); A16's reopen checks are scored here on what a fresh process would print instead. Run alone:

  python -B -m unittest -v tests_integrated.test_campaign
"""
import argparse
import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.campaign_lib import cases_anchor, cases_resource, core, fixture, gguf_fixture, needs, report, runner

RUN = ['R01', 'R07', 'R13', 'R17', 'R19', 'R21', 'R22', 'T01', 'T02', 'T03', 'A07']
NO_MODELS = shutil.ignore_patterns('models', '*.gguf')    # the sparse 20 GB fixtures would be copied dense


def copy_run(source, target):
    shutil.copytree(source, target, ignore=NO_MODELS)


def arguments(**values):
    base = dict(set=None, case=None, attempts=1, out=None, fixtures=None, mode='sim', model=None, workspace=None,
                skip_hash=False)
    base.update(values)
    return argparse.Namespace(**base)


class Recorder:
    """What a case reports, without a workspace: enough to score observations."""

    def __init__(self):
        self.observed, self.notes = {}, {}

    def observe(self, name, value):
        self.observed[name] = core._plain(value)

    def note(self, name, value):
        self.notes[name] = value


class CampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='graphite-campaign-test-')
        cls.out = Path(cls.temp.name) / 'run'
        with contextlib.redirect_stdout(io.StringIO()):
            cls.code = runner.run(arguments(case=list(RUN), out=str(cls.out),
                                            fixtures=str(Path(cls.temp.name) / 'no-fixtures')))
        cls.results = {r['case_id']: r for r in map(json.loads, (cls.out / 'results.jsonl').read_text().splitlines())}
        cls.line = report.summary(cls.out)[1]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_resource_cases_pass_on_current_behaviour(self):
        self.assertEqual(self.code, 0)
        for ident in ('R01', 'R07', 'R13', 'R17'):
            result = self.results[ident]
            self.assertEqual(result['outcome'], 'Pass', (ident, result.get('reason')))
            self.assertEqual(result['checks_met'], result['checks_total'])
        # 0.8.1 decided R07's question in the code: Auto takes the owner's model at 39 GiB.
        self.assertFalse(self.results['R07']['spec_question'])
        checks = {c['check']: c['observed'] for c in self.results['R07']['checks']}
        self.assertEqual((checks['auto_submit'], checks['auto_frozen_memory_mb']), ('ACCEPTED', 26013))

    # ---- 1. the summary counts only this run
    def test_run_into_an_existing_folder_moves_the_earlier_run_aside(self):
        stale = Path(self.temp.name) / 'run_stale'
        copy_run(self.out, stale)
        before = report.summary(stale)[1]
        self.assertIn('%d cases' % len(RUN), before)
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            runner.run(arguments(case=['R07'], out=str(stale), fixtures=str(Path(self.temp.name) / 'no-fixtures')))
        self.assertIn('moved aside to previous-1', printed.getvalue())
        line = report.summary(stale)[1]
        self.assertTrue(line.startswith('SUMMARY run_stale: 1 cases, Pass 1,'), line)
        self.assertEqual(sorted(p.name for p in (stale / 'cases').iterdir()), ['R07'])
        self.assertTrue((stale / 'previous-1' / 'cases' / 'R21' / 'attempt-1' / 'result.json').is_file())
        self.assertIn('%d cases' % len(RUN), report.summary(stale / 'previous-1')[1])
        manifest = json.loads((stale / 'MANIFEST.json').read_text())
        self.assertEqual(manifest['earlier_run_moved_to'], 'previous-1')

    def test_a_folder_that_is_not_a_run_is_refused_and_nothing_is_moved(self):
        mine = Path(self.temp.name) / 'mine';(mine / 'Photos').mkdir(parents=True)
        (mine / 'notes.txt').write_text('keep me');(mine / 'Photos' / 'a.jpg').write_bytes(b'x')
        with self.assertRaises(SystemExit) as refused:
            runner.run(arguments(case=['R07'], out=str(mine), fixtures=str(Path(self.temp.name) / 'no-fixtures')))
        self.assertIn('nothing was moved', str(refused.exception))
        self.assertEqual(sorted(p.name for p in mine.iterdir()), ['Photos', 'notes.txt'])
        mixed = Path(self.temp.name) / 'mixed';copy_run(self.out, mixed);(mixed / 'notes.txt').write_text('keep me')
        with self.assertRaises(SystemExit):
            runner.run(arguments(case=['R07'], out=str(mixed), fixtures=str(Path(self.temp.name) / 'no-fixtures')))
        self.assertFalse((mixed / 'previous-1').exists());self.assertTrue((mixed / 'notes.txt').is_file())

    def test_an_out_folder_that_holds_the_program_its_fixtures_home_or_root_is_refused(self):
        from tools.campaign_lib import fixture
        for out in (fixture.REPO.parent, Path.home(), Path('/')):
            with self.assertRaises(SystemExit, msg=str(out)):
                runner.run(arguments(case=['R07'], out=str(out), fixtures=str(Path(self.temp.name) / 'no-fixtures')))
        holder = Path(self.temp.name) / 'holder';(holder / 'fixtures').mkdir(parents=True)
        with self.assertRaises(SystemExit):
            runner.run(arguments(case=['R07'], out=str(holder), fixtures=str(holder / 'fixtures')))
        self.assertEqual([p.name for p in holder.iterdir()], ['fixtures'])

    def test_the_spec_forms_name_what_the_spec_accepts_not_anything_else(self):
        from tools.campaign_lib import cases_resource
        forms = {c.id: c.spec_conflict['expects'] for c in cases_resource.CASES if getattr(c, 'spec_conflict', None)}
        for case, expects in forms.items():
            for name, form in expects.items():
                self.assertNotIn('not', form, '%s %s: "anything but" also accepts a different breakage' % (case, name))
        # R19 and R22 met the spec in 0.8.1: their checks now say what the spec asks, with no conflict left to quote.
        self.assertNotIn('R19', forms)
        self.assertNotIn('R22', forms)

    def test_summary_reads_only_the_attempts_its_manifest_lists(self):
        stray = Path(self.temp.name) / 'run_stray'
        copy_run(self.out, stray)
        copy_run(stray / 'cases' / 'R07' / 'attempt-1', stray / 'cases' / 'R07' / 'attempt-2')
        copy_run(stray / 'cases' / 'R07', stray / 'cases' / 'R99')
        manifest, results = report.load(stray)
        self.assertEqual([(r['case_id'], r['attempt']) for r in results], [(c, 1) for c in RUN])
        self.assertNotIn('reruns', report.summary(stray)[1])

    # ---- 2. honest outcomes
    def test_r19_and_r22_meet_the_spec_and_are_plain_passes(self):
        for ident in ('R19', 'R22'):
            result = self.results[ident]
            self.assertEqual(result['outcome'], 'Pass', (ident, result.get('reason')))
            self.assertFalse(result['spec_conflict'])
        checks = {c['check']: c['observed'] for c in self.results['R19']['checks']}
        self.assertEqual((checks['handover_empty_restore:state'], checks['small_context:reason']),
                         ('MODEL_STOPPED', 'MODEL_CONTEXT_BELOW_SELECTION'))
        checks = {c['check']: c['observed'] for c in self.results['R22']['checks']}
        self.assertEqual((checks['hold:state'], checks['release:state'], checks['writes:held_load_activated']),
                         ('Queued', 'Running', 1))
        self.assertIn('Pass (current code; the spec asks otherwise) 0', self.line)
        self.assertIn('Pass means every check matched the current code, not that the spec is met', self.line)
        self.assertIn('**What Pass means.**', (self.out / 'SUMMARY.md').read_text())

    def test_spec_contradictions_are_counted_apart_from_pass(self):
        # A case whose current behaviour a quoted spec line contradicts is not a plain Pass, and becomes one when the
        # code does what the spec asks (R22 before and after 0.8.1, as data).
        case = core.Case(id='X22', set='x', title='x', expect={'hold:state': 'Cancelled', 'release:jobs_replayed': 0},
                         spec_conflict={'line': 'On release of the hold, continue from the correct step',
                                        'expects': {'hold:state': {'in': ['Queued', 'Held', 'Waiting']}}})
        outcome, checks = core.score(case, {'hold:state': 'Cancelled', 'release:jobs_replayed': 0})
        self.assertEqual(outcome, core.AGAINST_SPEC)
        self.assertFalse({c['check']: c for c in checks}['hold:state']['meets_spec'])
        self.assertEqual(core.score(case, {'hold:state': 'Queued', 'release:jobs_replayed': 0})[0], 'Pass')
        self.assertEqual(core.score(case, {'hold:state': 'Running', 'release:jobs_replayed': 0})[0], 'Partial')

    def test_r17_label_comes_from_graphites_record_and_llvmpipe_does_not_pass(self):
        label = {c['check']: c for c in self.results['R17']['checks']}['offload_label']
        self.assertTrue(label['observed'].startswith('SIMULATED: 41 layers per Graphite'), label)
        t03 = self.results['T03']
        self.assertNotEqual(t03['outcome'], 'Pass', t03.get('reason'))
        label = {c['check']: c for c in t03['checks']}['offload_label']
        self.assertFalse(label['ok'])
        self.assertTrue(label['observed'].startswith('NO_GPU_OFFLOAD'), label)
        self.assertIn('CPU_WORKER_WITH_OFFLOAD_DISABLED', label['observed'])

    # ---- 3. A16 reads everything it claims back from the reopened workspace
    def test_a16_reopen_checks_catch_a_wrong_saved_result(self):
        case = runner.registry()['A16']
        good = {'B3': '300', 'B3_unit': 'mA', 'revision': 'r2', 'power': '18/5', 'power_unit': 'W',
                'finding_state': 'recheck', 'finding_says': 'says 3.36 W; now 3.6 W', 'source_row_3': ['280', 'mA']}
        only = core.Case(id='x', set='x', title='x', expect={k: v for k, v in case.expect.items() if k.startswith('reopened:')})
        self.assertEqual(len(only.expect), 7)
        ctx = Recorder()
        cases_anchor.reopened_observations(ctx, good, 'r2')
        self.assertEqual(core.score(only, ctx.observed)[0], 'Pass')
        wrong = dict(good, power='WRONG', power_unit='kg', finding_state='current')     # the reviewer's perturbation
        ctx = Recorder()
        cases_anchor.reopened_observations(ctx, wrong, 'r2')
        outcome, checks = core.score(only, ctx.observed)
        self.assertEqual(outcome, 'Partial')
        self.assertEqual(sorted(c['check'] for c in checks if not c['ok']),
                         ['reopened:finding_state', 'reopened:power_unit', 'reopened:power_w'])
        for broken in (dict(good, B3_unit='kg'), dict(good, source_row_3=['300', 'mA']), dict(good, revision='r1')):
            ctx = Recorder()
            cases_anchor.reopened_observations(ctx, broken, 'r2')
            self.assertNotEqual(core.score(only, ctx.observed)[0], 'Pass', broken)

    # ---- 4. a case's revision covers the code it runs through
    def test_revision_covers_helpers_and_data_files(self):
        case = runner.registry()['R05']
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / 'campaign_lib'
            shutil.copytree(core.LIBRARY, copy, ignore=shutil.ignore_patterns('__pycache__'))
            first = core.library_digest(copy, core.ENTRY)
            self.assertEqual(first, core.library_digest(core.LIBRARY, core.ENTRY))
            sim_py = copy / 'sim.py'
            sim_py.write_text(sim_py.read_text().replace('total_gib=64', 'total_gib=32'))
            second = core.library_digest(copy, core.ENTRY)
            data = copy / 'data' / 'situations_35.json'
            data.write_text(data.read_text() + ' ')
            third = core.library_digest(copy, core.ENTRY)
        self.assertEqual(len({first, second, third}), 3)
        self.assertNotEqual(case.revision(first), case.revision(second))
        self.assertEqual(case.revision(), case.revision(core.library_digest()))

    def test_a_program_folder_without_git_is_unknown_not_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            identity = fixture.build_identity(Path(folder))
        self.assertIsNone(identity['tracked_changes']);self.assertTrue(identity['git_commit'].startswith('unknown'))

    def test_tracked_changes_counts_untracked_files_and_git_takes_no_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t',
                       GIT_COMMITTER_EMAIL='t@t', GIT_OPTIONAL_LOCKS='0')
            for command in (['init', '-q'], ['-c', 'commit.gpgsign=false', 'commit', '-q', '--allow-empty', '-m', 'x']):
                subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *command], check=True, env=env,
                               capture_output=True)
            self.assertFalse(fixture.build_identity(repo)['tracked_changes'])
            (repo / 'new.py').write_text('x = 1\n')
            identity = fixture.build_identity(repo)
            self.assertTrue(identity['tracked_changes'])
            self.assertEqual(identity['untracked_paths'], 1)
        seen = []
        real_run = subprocess.run

        def spy(argv, *a, **k):
            seen.append((list(argv), (k.get('env') or {}).get('GIT_OPTIONAL_LOCKS')))
            return real_run(argv, *a, **k)
        with mock.patch.object(fixture.subprocess, 'run', side_effect=spy):
            fixture.build_identity()
        self.assertTrue(seen)
        self.assertTrue(all(argv[:2] == ['git', '--no-optional-locks'] and lock == '0' for argv, lock in seen), seen)

    # ---- 5. a case that raises is a Fail
    def test_a_case_that_breaks_is_a_fail_with_its_error(self):
        result = self.results['T02']
        self.assertEqual(result['outcome'], 'Fail')
        self.assertEqual(result['checks_met'], 1)
        self.assertIn('RuntimeError', result['error'])
        self.assertIn('case broke after 1 of 2 checks met', result['reason'])

    # ---- 6. Blocked is decided at run time from checkable needs
    def test_anchor_needs_are_checked_when_the_run_starts(self):
        anchors = runner.select('anchors')
        self.assertEqual([c.situation for c in anchors], ['S%02d' % n for n in range(1, 36)])
        self.assertEqual([c.id for c in anchors], ['A%02d' % n for n in range(1, 36)])
        for case in anchors:
            self.assertTrue(case.intent)
            self.assertFalse(hasattr(case, 'blocked'))
            if case.fn is None:
                self.assertTrue(case.needs, case.id)
                self.assertEqual(case.expect, {})
            else:
                self.assertTrue(case.expect and case.slice, case.id)
        runnable = {c.id for c in anchors if c.fn}
        self.assertEqual(runnable, {'A01', 'A16', 'A17', 'A27', 'A28'})
        self.assertEqual(cases_anchor.RUNNABLE['S16']['expect']['power_now_w'], {'decimal': '3.60'})
        a07 = self.results['A07']
        self.assertEqual(a07['outcome'], 'Blocked')
        self.assertEqual({n['need'] for n in a07['needs']},
                         {'owner:forecast workbook with the subtotal and refund rows', 'app:LibreOffice Calc', 'model', 'ram'})

    def test_needs_follow_the_machine_not_the_case(self):
        case = runner.registry()['A07']
        with tempfile.TemporaryDirectory() as folder:
            bare = needs.Probe(fixtures=folder, environ={}, which=lambda name: None,
                               host={'cpu': 'Intel'}, memory={'available_bytes': 8 * 1024 ** 3, 'basis': 'test'})
            reason, _ = needs.decide(case, bare)
            self.assertIn('LibreOffice Calc (none of localc', reason)
            calc = needs.Probe(fixtures=folder, environ={}, which=lambda name: '/usr/bin/' + name if name == 'soffice' else None,
                               host={'cpu': 'Intel'}, memory={'available_bytes': 8 * 1024 ** 3, 'basis': 'test'})
            reason, _ = needs.decide(case, calc)
            self.assertIn('present here: LibreOffice Calc (/usr/bin/soffice)', reason)
            self.assertNotIn('LibreOffice Calc (none', reason)
            everything = mock.patch.object(needs.Probe, 'check', lambda self, need, situation=None: (True, need, 'here'))
            with everything:
                reason, checked = needs.decide(case, calc)
            self.assertTrue(reason.startswith('steps not written yet; its needs are here'), reason)
            a20 = runner.registry()['A20']
            desktop = needs.Probe(fixtures=folder, environ={'DISPLAY': ':0'}, which=lambda name: '/usr/bin/' + name,
                                  host={'cpu': 'Intel'}, memory={'available_bytes': 0, 'basis': 'test'})
            reason, checked = needs.decide(a20, desktop)
            self.assertTrue(reason.startswith('steps not written yet; its needs are here'), reason)
            owner = Path(folder) / 'S07'
            owner.mkdir()
            (owner / 'forecast.ods').write_bytes(b'x')
            met, what, evidence = needs.Probe(fixtures=folder).check('owner:forecast', 'S07')
            self.assertTrue(met and evidence == str(owner))

    def test_runnable_anchors_are_labelled_baseline_slices(self):
        with tempfile.TemporaryDirectory() as folder:
            run_dir = Path(folder)
            with contextlib.redirect_stdout(io.StringIO()):
                runner.run(arguments(case=['A28'], out=str(run_dir), fixtures=str(run_dir / 'none')))
            text, line = report.summary(run_dir)
        self.assertIn('Pass (baseline slice of S28)', text)
        self.assertIn('1 of the passing cases is an anchor that covers only a baseline slice of its situation', line)

    # ---- 8. smaller ones
    def test_resume_keeps_the_seed_record(self):
        result = self.results['R21']
        self.assertEqual(result['outcome'], 'Pass', result.get('reason'))
        self.assertEqual([p['phase'] for p in result['phases']], ['first', 'resume'])
        self.assertTrue(result['phases'][0]['killed_at_checkpoint'])
        self.assertEqual(result['checkpoint']['step'], 'step1')
        writes = {c['check']: c['observed'] for c in result['checks']}
        self.assertEqual((writes['step1_writes'], writes['step2_writes']), (1, 1))
        self.assertEqual(len(result['fixture']['initial_state_sha256']), 64)
        self.assertEqual(result['fixture']['resumed'], 'reopened from the same attempt folder')

    def test_memory_reads_the_cgroup_when_there_is_one(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'meminfo').write_text('MemTotal:       67108864 kB\nMemAvailable:   41943040 kB\n')
            (root / 'cgroup').write_text('0::/user.slice/app\n')
            group = root / 'fs' / 'user.slice' / 'app'
            group.mkdir(parents=True)
            (group / 'memory.max').write_text(str(32 * 1024 ** 3))
            (group / 'memory.current').write_text(str(12 * 1024 ** 3))
            mem = fixture.memory(root / 'meminfo', root / 'cgroup', root / 'fs')
            self.assertEqual((mem['total_bytes'], mem['available_bytes']), (32 * 1024 ** 3, 20 * 1024 ** 3))
            self.assertEqual(mem['basis'], 'cgroup v2 limit less usage')
            (group / 'memory.max').write_text('max\n')
            mem = fixture.memory(root / 'meminfo', root / 'cgroup', root / 'fs')
            self.assertEqual((mem['available_bytes'], mem['basis']), (40 * 1024 ** 3, '/proc/meminfo MemAvailable'))
            (root / 'cgroup').write_text('4:memory:/box\n0::/\n')
            box = root / 'fs' / 'memory' / 'box'
            box.mkdir(parents=True)
            (box / 'memory.limit_in_bytes').write_text(str(16 * 1024 ** 3))
            (box / 'memory.usage_in_bytes').write_text(str(6 * 1024 ** 3))
            mem = fixture.memory(root / 'meminfo', root / 'cgroup', root / 'fs')
            self.assertEqual((mem['available_bytes'], mem['basis']), (10 * 1024 ** 3, 'cgroup v1 limit less usage'))
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                code = runner.real(arguments(mode='real'), [runner.registry()['M01']], memory=mem)
        self.assertEqual(code, 2)
        self.assertIn('Only 10.0 GiB of RAM is available (cgroup v1 limit less usage)', printed.getvalue())

    def test_timeout_kills_the_attempt_and_keeps_the_partial_result(self):
        result = self.results['T01']
        self.assertEqual(result['outcome'], 'Timeout')
        self.assertTrue(result['phases'][0]['timed_out'])
        self.assertEqual(result['checkpoint']['step'], 'started')
        self.assertEqual(result['last_durable_result']['check'], 'started')
        self.assertLess(result['seconds'], 15)

    def test_manifest_summary_and_isolation(self):
        manifest = json.loads((self.out / 'MANIFEST.json').read_text())
        self.assertEqual([c['id'] for c in manifest['cases']], RUN)
        self.assertTrue(all(len(c['revision']) == 64 for c in manifest['cases']))
        self.assertEqual(manifest['runner_library_sha256'], core.library_digest())
        self.assertEqual(manifest['model']['owner_file']['sha256'], gguf_fixture.OWNER_FILE['sha256'])
        self.assertTrue(manifest['build']['version'])
        self.assertIn('untracked_paths', manifest['build'])
        self.assertTrue(manifest['repo_ledger_untouched'])
        isolation = self.results['R01']['isolation']
        attempt = str(self.out / 'cases' / 'R01' / 'attempt-1')
        self.assertTrue(all(path.startswith(attempt) for path in isolation.values()), isolation)
        text = (self.out / 'SUMMARY.md').read_text()
        self.assertIn('| R21 |', text)
        self.assertIn('Spec questions', text)
        self.assertIn('Timeout 1', self.line)

    def test_real_mode_refuses_without_the_file(self):
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            code = runner.real(arguments(mode='real'), [runner.registry()['M01']])
        self.assertEqual(code, 2)
        self.assertIn('REFUSED', printed.getvalue())
        self.assertIn('Nothing was started', printed.getvalue())

    def test_gguf_fixture_is_sparse_and_inspects_as_the_real_model(self):
        from sdk.cli.arc1cli import gguf_inspect
        with tempfile.TemporaryDirectory() as folder:
            built = gguf_fixture.build(Path(folder) / 'valid.gguf')
            self.assertEqual(built['apparent_bytes'], gguf_fixture.OWNER_FILE['bytes'])
            self.assertLess(built['disk_bytes'], 1024 * 1024)
            found = gguf_inspect.inspect(Path(folder) / 'valid.gguf')
            self.assertEqual((found['architecture'], found['architecture_profile']), ('qwen35moe', 'SUPPORTED_FOR_TRIAL'))
            truncated = gguf_fixture.build(Path(folder) / 'truncated.gguf', 'truncated')
            self.assertEqual(truncated['apparent_bytes'], 20_531_799_903)       # by design, as the docstring says


if __name__ == '__main__':
    unittest.main()
