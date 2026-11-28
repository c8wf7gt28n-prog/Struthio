"""0.8.4: the campaign on Rail Demo, the workspace of invented data kept in the program (workbench/rail_demo.py).

The playable scene P01 and four anchors (A01, A16, A17, A27) were written for the owner's After Hours 07 backup, which is
never shipped: wherever it was not they were Blocked, and their steps never ran. Each now has a twin that runs the same
steps on Rail Demo: DP01a..DP01d (the scene, its names swapped) and DA01, DA16, DA17, DA27 (the same functions, Rail
Demo's own values).

Without a run: since 0.8.5 the scene is written on Rail Demo and names nothing of the owner's workspace; on After Hours 07
each of its names is found there by kind and words (on a stand-in desk of invented names here), the same acts in the
same order, and what the window reads there is said back in the scene's own names, so a run there is judged by the
same checks; the runner's parent, which never imports Graphite, and the program give the same scene; the scene as
written is untouched and its cases on the owner's workspace still need the backup; no anchor or scene case, and no
module of the campaign, holds a record id or a hash of the owner's; the twins need only what a PDF source needs, and
say which part is missing.

The scene case itself, played once in this process as a child of the runner plays it: P01 said in invented names, with
an entry that finds each of them on Rail Demo by the words its After Hours 07 entry uses, so the case finds Rail Demo's
names before the first step, plays the scene in them and meets the scene's own checks with what it read said back.

With a run, exactly as `tools/campaign.py run` makes it (one child per attempt, in its own folder, no fixtures folder):
the four anchors' steps pass on Rail Demo with its values (3 W, 3.6 W at 300 mA, the finding flagged, the source still at
250 mA, read back by a fresh process; a backup made, verified, restored and read; a kill after the write, resumed); P01
is played on Rail Demo by pointer in the Graphite look and in the Kasandra look, whatever look this module was started in;
and the same scene on the owner's workspace is Blocked, not failed, because the backup is not here. A build of Rail
Demo that breaks is a Fail, never Blocked: only what its PDF sources need, when it is missing, blocks a case.

  python -B -m unittest -v tests_integrated.test_rail_demo_campaign
"""
import argparse
import contextlib
import copy
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.campaign_lib import cases_anchor, cases_scene, core, fixture, needs, report, runner
from tests_integrated import seed_hold

ROOT = Path(__file__).resolve().parent.parent
ANCHORS = ['DA01', 'DA16', 'DA17', 'DA27']
SCENES = ['DP01a', 'DP01b', 'DP01c', 'DP01d']
HER_SCENES = ['DP02a', 'DP02b', 'DP02c', 'DP03a', 'DP03b']      # 0.8.6 S0: her door's scenes, written on Rail Demo only
# The names the scene says that its After Hours 07 entry finds there, in the order it lists them: three sheets, two
# calculations, two rows of the Rev B sheet
FOUND = ['Rail Demo bench readings', 'Rail Demo limits Rev A ARCHIVED', 'Rail Demo limits Rev B CURRENT', 'Rail Demo settled power',
         'Rail Demo startup power', 'Startup duration limit', 'Startup power ceiling']
# Invented names for a workspace whose names the program does not hold, as find_names would find them there
ELSEWHERE = dict(zip(FOUND, ['Night bench readings', 'Night limits Rev A ARCHIVED', 'Night limits Rev B CURRENT', 'Night settled power',
                             'Night startup power', 'Peak duration', 'Peak ceiling']))
RAIL_CSV = 'parameter,value,unit\nRail voltage,12,V\nSettled current,250,mA\nStartup current,900,mA\nStartup duration,45,ms\n'
HEX_ID = r'(?<![0-9a-f])(?:[0-9a-f]{32}|[0-9a-f]{64})(?![0-9a-f])'      # a record id or a SHA-256, as Graphite writes them


def arguments(**values):
    base = dict(set=None, case=None, attempts=1, out=None, fixtures=None, mode='sim', model=None, workspace=None,
                skip_hash=False)
    base.update(values)
    return argparse.Namespace(**base)


def run(out, cases, look=None, first_on_path=None):
    """One campaign run into `out` with no fixtures folder, started in the given look (None: the first look, Graphite),
    with a folder put first on the PATH when one is given."""
    environment = {k: v for k, v in os.environ.items() if k != 'GRAPHITE_APPEARANCE'}
    environment['GRAPHITE_APPEARANCE'] = look or 'graphite'      # 1.1 T1: unset, a fresh profile starts in Day (1.0 D1)
    if first_on_path:
        environment['PATH'] = '%s%s%s' % (first_on_path, os.pathsep, environment.get('PATH', ''))
    with mock.patch.dict(os.environ, environment, clear=True), contextlib.redirect_stdout(io.StringIO()):
        code = runner.run(arguments(case=list(cases), out=str(out), fixtures=str(Path(out).parent / 'no-fixtures')))
    results = {r['case_id']: r for r in map(json.loads, (Path(out) / 'results.jsonl').read_text().splitlines())}
    return code, results


class Desk:
    """A workspace's desk as find_names reads it (field.read; office.get of a sheet for its reviewed rows), with invented
    names standing for a workspace the program does not hold."""

    def __init__(self, sheets=None, calculations=None, rows=None):
        self.sheets = sheets if sheets is not None else ['Night bench readings', 'Night limits Rev A ARCHIVED', 'Night limits Rev B CURRENT', 'Night notes']
        self.calculations = calculations if calculations is not None else ['Night settled power · 4.2 W', 'Night startup power · 9 W']
        self.rows = rows if rows is not None else ['Peak duration', 'Peak ceiling', 'Nominal voltage']
        self.asked = []

    def dispatch(self, op, args, principal):
        self.asked.append(op)
        if op == 'field.read':
            return {'ok': True, 'result': {'objects': [{'id': 'office:owner:%d' % n, 'kind': 'sheet', 'title': t} for n, t in enumerate(self.sheets)]
                                           + [{'id': 'document:%d' % n, 'kind': 'calculation', 'title': t} for n, t in enumerate(self.calculations)]
                                           + [{'id': 'claim:1', 'kind': 'finding', 'title': 'Night settled power is 4.2 W.'}]}}
        if op == 'office.get':
            title = self.sheets[int(args['id'].rsplit(':', 1)[1])]
            rows = self.rows if title.endswith('Rev B CURRENT') else ['Other']
            return {'ok': True, 'result': {'origin': {'reviewed_rows': [{'parameter': p, 'value': '1'} for p in rows]}}}
        return {'ok': False, 'error': {'code': 'NOT_ASKED'}}


class TheSceneOnAnotherWorkspace(unittest.TestCase):
    """No run: the scene is written on Rail Demo and names nothing of the owner's workspace; on After Hours 07 each of its
    names is found there by kind and words, and what the window reads there is said back in the scene's own names."""

    def setUp(self):
        from workbench import desk_scene
        self.written = cases_scene.load('P01')
        self.find = self.written['workspaces']['after_hours_07']['find']
        self.there = desk_scene.for_workspace(self.written, 'after_hours_07', ELSEWHERE)

    def test_the_scene_is_written_on_rail_demo_and_names_nothing_of_the_owners_workspace(self):
        self.assertEqual((self.written['seed'], self.written['title']), ('rail_demo', 'Rail Demo, the playable scene'))
        self.assertEqual(cases_scene.for_workspace(self.written, 'rail_demo'), self.written, 'the scene as written is what Rail Demo plays')
        self.assertEqual(list(self.written['workspaces']), ['after_hours_07'])
        self.assertNotIn('names', self.written['workspaces']['after_hours_07'], 'no name of the owner\'s workspace is written')
        self.assertEqual(list(self.find), FOUND)
        said = json.dumps(self.written['steps'])
        for name in FOUND:
            self.assertIn(name, said, 'a name the scene does not say')
        named = {s['args'][k] for s in self.written['steps'] for k in ('title', 'name', 'path') if k in s.get('args', {}) and s['act'] != 'menu.choose'}
        self.assertEqual(named, {'Rail Demo bench readings', 'Rail Demo bench readings.csv', 'Rail Demo limits Rev B CURRENT'})
        self.assertEqual([s['args']['text'] for s in self.written['steps'] if s['act'] == 'hand.write'], [RAIL_CSV], 'Rail Demo\'s readings, invented')
        self.assertEqual([s for s in self.written['steps'] if 'args_by_seed' in s], [], 'the same arguments on every workspace')
        self.assertEqual(re.findall(HEX_ID, json.dumps(self.written)), [])

    def test_on_another_workspace_the_same_acts_with_each_name_found_there(self):
        self.assertEqual([s['act'] for s in self.there['steps']], [s['act'] for s in self.written['steps']])
        self.assertEqual((self.there['seed'], self.there['id'], self.there['runs'], self.there['given']),
                         ('after_hours_07', 'P01', self.written['runs'], self.written['given']))
        self.assertEqual(self.there['title'], 'After Hours 07, the playable scene')
        for was, now in zip(self.written['steps'], self.there['steps']):
            for key in ('args', 'expect', 'expect_by_run', 'expect_by_seed'):
                self.assertEqual(sorted(was.get(key, {})), sorted(now.get(key, {})), (was['act'], key))
        by_act = {s['act']: s for s in self.there['steps']}
        self.assertEqual(by_act['hand.write']['args'], {'path': 'Night bench readings.csv', 'text': RAIL_CSV})
        self.assertEqual(by_act['menu.open']['args'], {'on': 'file', 'name': 'Night bench readings.csv'})
        self.assertEqual(by_act['then.end']['expect']['desk.line.text'], '@files:Night bench readings.csv | rows | where unit=mA | count')
        self.assertEqual(by_act['sheet.compare']['expect'],
                         {'desk.field.revisions.a': 'Night limits Rev A ARCHIVED', 'desk.field.revisions.b': 'Night limits Rev B CURRENT',
                          'desk.field.revisions.changed': {'contains': 'Peak duration'}, 'desk.field.revisions.changed#ceiling': {'contains': 'Peak ceiling'}})
        self.assertEqual(by_act['sheet.trace']['expect_by_seed']['after_hours_07']['desk.field.route.ends'], {'contains': 'Night settled power'})
        said = json.dumps(self.there['steps'])
        for name in FOUND:
            self.assertNotIn(name, said, name)
        self.assertEqual(cases_scene.for_workspace(self.written, 'after_hours_07')['steps'], self.written['steps'],
                         'where the names are not found yet (the runner\'s parent) they stay as the scene says them')

    def test_what_the_window_reads_there_is_said_back_in_the_scenes_own_names(self):
        from workbench import desk_scene
        self.assertEqual(desk_scene.said_back({'ends': ['Night settled power · 4.2 W', 'Night startup power · 9 W'], 'hops': 2, 'other': 'Night notes'}, ELSEWHERE),
                         {'ends': ['Rail Demo settled power · 4.2 W', 'Rail Demo startup power · 9 W'], 'hops': 2, 'other': 'Night notes'})
        self.assertEqual(desk_scene.said_back('Night bench readings.csv', {}), 'Night bench readings.csv')
        for run_name in ('mouse', 'keys', 'mouse_still', 'keys_still'):     # every check, read there as expected, is the scene's own check
            here = cases_scene.flattened(cases_scene.for_workspace(self.written, 'after_hours_07'), run_name, 'after_hours_07')
            there = cases_scene.flattened(self.there, run_name, 'after_hours_07')
            self.assertEqual(sorted(there), sorted(here))
            for path, value in there.items():
                self.assertEqual(desk_scene.said_back(value, ELSEWHERE), here[path], (run_name, path))

    def test_each_name_is_found_once_by_its_kind_and_the_words_it_says(self):
        from workbench import desk_scene
        desk = Desk()
        self.assertEqual(desk_scene.find_names(desk, None, self.written, 'after_hours_07'), ELSEWHERE)
        self.assertEqual(desk.asked.count('field.read'), 1)
        self.assertTrue(set(desk.asked) <= {'field.read', 'office.get'}, 'it only reads')
        self.assertEqual(desk_scene.find_names(desk, None, self.written, 'rail_demo'), {}, 'the scene\'s own workspace: nothing to find')
        for broken, words in ((Desk(sheets=['Night bench readings', 'Day bench readings', 'Night limits Rev A ARCHIVED', 'Night limits Rev B CURRENT']),
                               '2 sheets say "bench readings" (for Rail Demo bench readings)'),
                              # a sheet is one record: two of one title are two, whether a row is found in it or not
                              (Desk(sheets=['Night bench readings', 'Night bench readings', 'Night limits Rev A ARCHIVED', 'Night limits Rev B CURRENT']),
                               '2 sheets say "bench readings" (for Rail Demo bench readings)'),
                              (Desk(sheets=['Night bench readings', 'Night limits Rev A ARCHIVED', 'Night limits Rev B CURRENT', 'Night limits Rev B CURRENT']),
                               '2 sheets say "rev b current" (for Rail Demo limits Rev B CURRENT)'),
                              (Desk(calculations=['Night settled power · 4.2 W']), 'no calculation says "startup power" (for Rail Demo startup power)'),
                              (Desk(rows=['Peak duration ceiling', 'Nominal voltage']), 'Startup duration limit and Startup power ceiling are found as the same row of Night limits Rev B CURRENT'),
                              (Desk(rows=['Nominal voltage']), 'no row of Night limits Rev B CURRENT says "duration" (for Startup duration limit)')):
            with self.assertRaises(ValueError, msg=words) as refused:
                desk_scene.find_names(broken, None, self.written, 'after_hours_07')
            self.assertEqual(str(refused.exception), "The scene P01, workspace 'after_hours_07': " + words)

    def test_the_scene_as_written_is_untouched_and_is_what_its_own_seed_gives(self):
        from workbench import desk_scene
        before = copy.deepcopy(self.written)
        desk_scene.for_workspace(self.written, 'after_hours_07', ELSEWHERE);cases_scene.for_workspace(self.written, 'after_hours_07')
        self.assertEqual(self.written, before, 'a copy is swapped, never the scene')
        self.assertEqual(desk_scene.for_workspace(self.written, 'rail_demo', ELSEWHERE), self.written, 'its own seed: as written')
        with self.assertRaisesRegex(ValueError, "not written for the workspace 'bench'"):
            cases_scene.for_workspace(self.written, 'bench')

    def test_the_runners_parent_and_the_program_give_the_same_scene(self):
        from workbench import desk_scene
        for workspace in ('rail_demo', 'after_hours_07'):
            self.assertEqual(cases_scene.for_workspace(self.written, workspace), desk_scene.for_workspace(self.written, workspace), workspace)
        with self.assertRaises(ValueError):
            desk_scene.for_workspace(self.written, 'bench')
        for run_name in ('mouse', 'keys', 'mouse_still', 'keys_still'):
            flat = cases_scene.flattened(self.written, run_name, 'rail_demo')
            for n, step in enumerate(self.written['steps'], 1):
                for path, value in desk_scene.expected(step, run_name, 'rail_demo').items():
                    self.assertEqual(flat['%d:%s' % (n, path)], value, (run_name, n, path))
        self.assertEqual(desk_scene.check_scene(self.there), [])
        self.assertEqual(desk_scene.check_scene(self.written), [])

    def test_a_malformed_entry_is_said_in_words(self):
        from workbench import desk_scene
        scene = copy.deepcopy(self.written)
        scene['workspaces'] = {'rail_demo': {'names': {'a name the scene says': 7}},
                               'after_hours_07': {'find': {'Rail Demo bench readings': {'kind': 'page', 'says': 'bench'},
                                                           'Startup power ceiling': {'kind': 'row', 'of': 'Rail Demo settled power', 'says': 'ceiling'},
                                                           'Rail Demo settled power': {'kind': 'calculation', 'says': ' '}}}}
        scene['steps'][2]['args_by_seed'] = {'after_hours_07': {'path': ''}}
        scene['steps'][3]['args_by_seed'] = ['after_hours_07']
        problems = desk_scene.check_scene(scene)
        self.assertIn("workspace 'rail_demo': names is not an object of names", problems)
        self.assertIn("workspace 'after_hours_07': 'Rail Demo bench readings' is not found by a kind (sheet, calculation, row) and the words it says", problems)
        self.assertIn("workspace 'after_hours_07': the row 'Startup power ceiling' is not of a sheet the entry finds", problems)
        self.assertIn("workspace 'after_hours_07': 'Rail Demo settled power' is not found by a kind (sheet, calculation, row) and the words it says", problems)
        self.assertIn('step 4: args_by_seed is not an object of objects', problems)
        self.assertTrue([p for p in problems if p.startswith('step 3, on after_hours_07: ')], problems)
        self.assertEqual(len(problems), 6, problems)

    def test_names_the_swap_cannot_use_are_refused_in_words_and_nothing_is_swapped(self):
        from workbench import desk_scene
        for names in ({'': 'x'}, {'Rail Demo bench readings': 7}, ['Rail Demo bench readings'], None):
            scene = copy.deepcopy(self.written)
            scene['workspaces']['after_hours_07']['names'] = names
            for give in (desk_scene.for_workspace, cases_scene.for_workspace):
                with self.assertRaises(ValueError, msg=(names, give.__module__)) as refused:
                    give(scene, 'after_hours_07')
                self.assertEqual(str(refused.exception), "The scene P01, workspace 'after_hours_07': names is not an object of names")
            self.assertIn("workspace 'after_hours_07': names is not an object of names", desk_scene.check_scene(scene))
            if isinstance(names, dict):
                with self.assertRaises(ValueError, msg=names):
                    desk_scene.for_workspace(self.written, 'after_hours_07', names)      # nor names found that it cannot use

    def test_arguments_for_a_seed_add_to_or_replace_the_steps_own(self):
        from workbench import desk_scene
        step = {'act': 'hand.write', 'args': {'path': 'a.csv', 'text': 'one'}, 'args_by_seed': {'there': {'text': 'two'}}}
        self.assertEqual(desk_scene.arguments(step, 'there'), {'path': 'a.csv', 'text': 'two'})
        self.assertEqual(desk_scene.arguments(step, 'elsewhere'), {'path': 'a.csv', 'text': 'one'})
        self.assertEqual(desk_scene.arguments({'act': 'menu.close'}, 'there'), {})
        self.assertEqual(step['args'], {'path': 'a.csv', 'text': 'one'})


class TheSceneCaseWhereItsNamesAreFound(unittest.TestCase):
    """The scene case itself (cases_scene.run_case, as a child of the runner calls it) on a workspace whose names are not the
    scene's, as P01a..P01d are on the owner's backup, which is not here: P01 said in invented names, with an entry that
    finds each of them on Rail Demo by the words its After Hours 07 entry uses. The case finds Rail Demo's names before
    the first step, plays the scene in them, and says what the window read back in the scene's own names, so the scene's
    own checks are met. Played once, in this process, on Rail Demo built as the runner builds it for a child."""

    @classmethod
    def setUpClass(cls):
        from workbench import desk_scene
        written = cases_scene.load('P01')
        find = written['workspaces']['after_hours_07']['find']
        invented = desk_scene.for_workspace(written, 'after_hours_07', ELSEWHERE)      # the same scene, said in invented names
        invented.update(seed='night', workspaces={'rail_demo': {'find': {
            ELSEWHERE[name]: dict(how, **({'of': ELSEWHERE[how['of']]} if 'of' in how else {})) for name, how in find.items()}}})
        cls.invented = invented
        cls.case = core.Case(id='XP01d', set='scenes', title='P01 in invented names, played on Rail Demo', seed='rail_demo', needs=['rail_demo'],
                             inputs={'scene': 'P01', 'run': 'keys_still'}, fn=cases_scene.run_case,
                             expect=cases_scene.flattened(cases_scene.for_workspace(invented, 'rail_demo'), 'keys_still', 'rail_demo'))
        cls.temp = tempfile.TemporaryDirectory(prefix='graphite-scene-case-', ignore_cleanup_errors=True)
        folder = Path(cls.temp.name) / 'attempt'
        fixture.make_folders(folder)
        holds = [mock.patch.dict(os.environ, fixture.attempt_environment(folder)), seed_hold.seed_bound(),
                 mock.patch.object(cases_scene, 'load', lambda scene_id: copy.deepcopy(invented))]
        for hold in holds:hold.start()
        try:
            cls.ctx = core.Attempt(cls.case, folder, 1)
            cls.ctx.kernel, cls.ctx.owner, _ = fixture.rail_demo_workspace(folder)
            cls.case.fn(cls.ctx)
        finally:
            for hold in reversed(holds):hold.stop()
        cls.outcome, cls.scored = core.score(cls.case, cls.ctx.observed)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_the_scene_in_invented_names_names_nothing_of_rail_demo_that_its_entry_finds(self):
        said = json.dumps(self.invented['steps'])
        for name in FOUND:
            self.assertNotIn(name, said, name)
        self.assertEqual(self.case.expect['12:desk.field.selected.title'], 'Night bench readings')

    def test_the_case_finds_each_name_there_and_meets_the_scenes_own_checks(self):
        self.assertEqual(self.outcome, 'Pass', [c for c in self.scored if not c['ok']])
        self.assertEqual(len(self.scored), len(self.case.expect))
        self.assertEqual(self.ctx.notes['found'], sorted(ELSEWHERE.values()), 'which of the scene\'s names were found there')
        self.assertIs(self.ctx.notes['passed'], True)
        self.assertEqual([s['act'] for s in self.ctx.notes['steps']], [s['act'] for s in self.invented['steps']])

    def test_it_was_played_in_the_names_there_and_judged_in_the_scenes_own(self):
        trace = next(s for s in self.ctx.notes['steps'] if s['act'] == 'sheet.trace')
        self.assertEqual(trace['result']['route']['owner_title'], 'Rail Demo bench readings', 'what the window read, as it read it')
        got = self.ctx.observed
        self.assertEqual((got['12:desk.field.selected.title'], got['15:desk.field.revisions.a'], got['15:desk.field.revisions.b'], got['17:act.result.trashed']),
                         ('Night bench readings', 'Night limits Rev A ARCHIVED', 'Night limits Rev B CURRENT', 'Night bench readings.csv'))
        self.assertEqual([name for name in FOUND if name in json.dumps(got)], [], 'every name read there is said back')


class TheCases(unittest.TestCase):
    """No run: the twins are registered, need nothing of the owner's, and the cases on the owner's workspace are as they were."""

    def test_the_scene_has_a_case_for_each_run_on_each_workspace(self):
        every = runner.registry()
        scenes = runner.select('scenes')
        self.assertEqual([c.id for c in scenes], ['P01a', 'P01b', 'P01c', 'P01d'] + SCENES + HER_SCENES)
        written = cases_scene.load('P01')
        for case in scenes[:4]:
            self.assertEqual((case.seed, case.needs, case.start, case.source_case), ('after_hours_07', ['after_hours_07'], {}, None), case.id)
            self.assertEqual(case.expect, cases_scene.flattened(written, case.inputs['run'], 'after_hours_07'), case.id)
            self.assertIn('After Hours 07', case.title)
        for case, original in zip(scenes[4:], scenes[:4]):
            self.assertEqual((case.seed, case.needs, case.source_case), ('rail_demo', ['rail_demo'], original.id + ' on Rail Demo'), case.id)
            self.assertEqual(case.inputs, original.inputs, case.id)
            self.assertEqual(case.expect, original.expect, 'the same checks with the same values: the owner\'s run is judged in the scene\'s own names')
            self.assertEqual((case.budget_s, case.fn), (original.budget_s, original.fn), case.id)
            self.assertIn('Rail Demo (invented data)', case.title)
            self.assertIs(every[case.id], case)
        for case in scenes[8:]:      # 0.8.6 S0: her door's scenes need nothing of the owner's
            self.assertEqual((case.seed, case.needs, case.source_case), ('rail_demo', ['rail_demo'], None), case.id)
            self.assertEqual(case.expect, cases_scene.flattened(cases_scene.load(case.inputs['scene']), case.inputs['run'], 'rail_demo'), case.id)
            self.assertIn('Rail Demo (invented data)', case.title);self.assertIs(every[case.id], case)
        self.assertEqual(scenes[4].expect['13:desk.field.route.hops'], 2)
        self.assertEqual(scenes[4].expect['13:desk.field.route.ends'], {'contains': 'Rail Demo settled power'})
        self.assertEqual(re.findall(HEX_ID, json.dumps([[c.title, c.intent, c.expect, c.inputs] for c in scenes])), [])

    def test_the_demo_set_is_the_four_anchors_steps_with_rail_demos_values(self):
        every = runner.registry()
        demo = runner.select('demo')
        self.assertEqual([c.id for c in demo], ANCHORS)
        self.assertEqual(runner.SETS, ('resource', 'anchors', 'demo', 'selftest', 'real', 'scenes'))
        self.assertEqual([c.id for c in runner.select('all') if c.set == 'demo'], ANCHORS, 'the demo set runs with the default batch')
        for case in demo:
            anchor = every[case.id[1:]]
            self.assertEqual((case.seed, case.needs, case.mode, case.slice, case.situation), ('rail_demo', ['rail_demo'], 'sim', None, None), case.id)
            self.assertEqual(case.source_case, case.id[1:] + ' on Rail Demo')
            self.assertTrue(case.title.startswith('Rail Demo'), case.title)
            self.assertEqual(sorted(set(anchor.expect) - set(case.expect)), [], case.id)
            said = json.dumps([case.title, case.inputs, case.expect, case.start])      # the intent alone says whose steps these are
            self.assertNotIn('After Hours', said, case.id)
            self.assertNotEqual(case.expect, anchor.expect, 'Rail Demo\'s own values, not the owner\'s')
        self.assertIs(every['DA01'].fn, every['A01'].fn);self.assertIs(every['DA16'].fn, every['A16'].fn);self.assertIs(every['DA27'].fn, every['A27'].fn)
        da16 = every['DA16']
        self.assertEqual(da16.inputs['request'], cases_anchor.ASKED % '250')
        self.assertIn('change settled current from 250 mA to 300 mA', da16.inputs['request'])
        self.assertEqual({k: da16.expect[k] for k in ('open_item', 'target_cell', 'was_power_w', 'preview_shows', 'cell_now', 'power_now_w', 'finding_state',
                                                       'finding_says', 'source_row_3', 'reopened:source_row_3', 'reopened:finding_says')},
                         {'open_item': 'Rail Demo bench readings', 'target_cell': 'B3', 'was_power_w': '3', 'preview_shows': ['250 mA', '300 mA'],
                          'cell_now': ['300', 'mA'], 'power_now_w': {'decimal': '3.60'}, 'finding_state': 'recheck', 'finding_says': 'says 3 W; now 3.6 W',
                          'source_row_3': ['250', 'mA'], 'reopened:source_row_3': ['250', 'mA'], 'reopened:finding_says': 'says 3 W; now 3.6 W'})
        self.assertEqual(every['DA01'].expect['power_w'], '3')
        self.assertEqual(every['DA27'].expect['settled_calculations'], ['Rail Demo settled power · 3.6 W'])

    def test_the_anchors_on_the_owners_workspace_find_their_records_and_hold_nothing_of_it(self):
        every = runner.registry()
        for ident in ('A01', 'A16', 'A27'):
            self.assertEqual((every[ident].seed, every[ident].needs), ('after_hours_07', ['after_hours_07']), ident)
        self.assertEqual((every['A17'].seed, every['A17'].needs), ('none', ['after_hours_07']))
        # 0.8.5: no record id, hash or title of the owner's is written; the records are found where the case runs (found())
        self.assertFalse(hasattr(fixture, 'AH07_IDS'))
        self.assertIs(every['A01'].expect['pdf_source_is_the_admitted_one'], True)
        self.assertNotIn('pdf_source_sha', every['A01'].expect)
        self.assertNotIn('open_item', every['A16'].expect, 'the sheet is found by its words: its title is not expected')
        self.assertEqual((every['A16'].expect['was_power_w'], every['A27'].expect['settled_results']), ('84/25', ['3.6 W']))
        for ident in ('A01', 'A16', 'A17', 'A27'):
            said = json.dumps([every[ident].title, every[ident].expect, every[ident].inputs, every[ident].start])
            self.assertEqual(re.findall(HEX_ID, said), [], ident)
        for module in (fixture, cases_anchor, cases_scene):
            self.assertEqual(re.findall(HEX_ID, Path(module.__file__).read_text(encoding='utf-8')), [], module.__name__)
        self.assertEqual(every['A16'].inputs['request'], cases_anchor.REQUEST)
        self.assertNotEqual(cases_anchor.REQUEST, cases_anchor.DEMO_REQUEST)
        for sid, ident in (('S01', 'A01'), ('S16', 'A16'), ('S17', 'A17'), ('S27', 'A27')):
            self.assertEqual(every[ident].expect, cases_anchor.RUNNABLE[sid]['expect'], ident)
            self.assertNotIn('Rail Demo', json.dumps([every[ident].title, every[ident].expect, every[ident].inputs]), ident)
        self.assertEqual([c.id for c in runner.select('anchors')], ['A%02d' % n for n in range(1, 36)])

    def test_the_twins_need_only_what_a_pdf_source_needs_and_say_what_is_missing(self):
        case = runner.registry()['DP01a']
        with tempfile.TemporaryDirectory() as folder:
            here = needs.Probe(fixtures=folder, which=lambda name: '/usr/bin/' + name)
            self.assertEqual(needs.decide(case, here)[0], None)
            met, what, evidence = here.check('rail_demo')
            self.assertEqual((met, evidence), (True, 'pypdf and /usr/bin/pdftotext'))
            bare = needs.Probe(fixtures=folder, which=lambda name: None)
            reason, checked = needs.decide(case, bare)
            self.assertEqual(reason, 'Needs what Rail Demo\'s PDF sources need (pypdf and Poppler) (pdftotext and pdftoppm not found '
                                     '(Debian: apt install poppler-utils; pip install -r requirements-qt.txt)).')
            self.assertEqual([(c['need'], c['met']) for c in checked], [('rail_demo', False)])
            with mock.patch.object(needs.importlib.util, 'find_spec', return_value=None):
                self.assertIn('the pypdf package not found', needs.decide(case, needs.Probe(fixtures=folder, which=lambda name: '/usr/bin/' + name))[0])
            # the scene on the owner's workspace still needs the backup, and says so
            reason, checked = needs.decide(runner.registry()['P01a'], here)
            self.assertIn('the owner\'s After Hours 07 backup (not found under', reason)

    def test_what_builds_rail_demo_is_part_of_every_twins_revision(self):
        from workbench import rail_demo
        identity = fixture.rail_demo_identity()
        self.assertEqual(identity, {'builder': 'workbench/rail_demo.py', 'builder_sha256': fixture.file_sha(ROOT / 'workbench' / 'rail_demo.py'),
                                    'revision': rail_demo.REVISION})
        for ident in ANCHORS + SCENES:
            self.assertEqual(runner.registry()[ident].start, {'workspace': 'Rail Demo, invented data', 'built_by': identity}, ident)
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(fixture.rail_demo_identity(folder), {'builder': 'workbench/rail_demo.py', 'state': 'NOT_FOUND'})
            builder = Path(folder) / 'workbench' / 'rail_demo.py'
            builder.parent.mkdir()
            builder.write_text('REVISION = 7\n')
            changed = fixture.rail_demo_identity(folder)
            self.assertEqual((changed['revision'], changed['builder_sha256']), (7, fixture.file_sha(builder)))
        case = runner.registry()['DA01']
        other = core.Case(**{**{f: getattr(case, f) for f in case.data()}, 'start': {**case.start, 'built_by': changed}}, fn=case.fn)
        self.assertNotEqual(case.revision('x'), other.revision('x'), 'a changed builder is a new revision of the case')


class TheRuns(unittest.TestCase):
    """Two runs, as tools/campaign.py makes them: the twins in the Graphite look, and the scene again in the Kasandra look."""

    @classmethod
    def setUpClass(cls):
        if seed_hold.edited():
            raise unittest.SkipTest(seed_hold.EDITED_REASON)
        cls.temp = tempfile.TemporaryDirectory(prefix='graphite-rail-demo-campaign-')
        cls.out = Path(cls.temp.name) / 'run'
        cls.code, cls.results = run(cls.out, ANCHORS + ['DP01a', 'P01a'])
        cls.kas_out = Path(cls.temp.name) / 'run-kasandra'
        cls.kas_code, cls.kas = run(cls.kas_out, ['DP01a'], look='kasandra')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def checks(self, ident, results=None):
        return {c['check']: c['observed'] for c in (results or self.results)[ident]['checks']}

    def test_every_twin_passes_with_nothing_of_the_owners_here(self):
        self.assertEqual(self.code, 0)
        for ident in ANCHORS + ['DP01a']:
            result = self.results[ident]
            self.assertEqual(result['outcome'], 'Pass', (ident, result.get('reason'), result.get('error')))
            self.assertEqual(result['checks_met'], result['checks_total'], ident)
            self.assertEqual([(n['need'], n['met']) for n in result['needs']], [('rail_demo', True)], ident)
            seeded = result['fixture']
            self.assertEqual((seeded['seed'], seeded['revision'], seeded['notice']),
                             ('rail_demo', fixture.rail_demo_identity()['revision'], 'Invented demonstration data. Nothing here was measured.'), ident)
            self.assertEqual(sorted(seeded['sources_sha256']), ['limits_a', 'limits_b', 'readings'], ident)
        self.assertEqual(len({self.results[i]['fixture']['initial_state_sha256'] for i in ANCHORS + ['DP01a']}), 1,
                         'five builds, one picture: the same tables with the same number of rows')
        self.assertEqual(len({json.dumps(self.results[i]['fixture']['sources_sha256'], sort_keys=True) for i in ANCHORS + ['DP01a']}), 1)
        manifest = json.loads((self.out / 'MANIFEST.json').read_text())
        self.assertEqual(manifest['fixtures']['rail_demo'], fixture.rail_demo_identity())
        self.assertEqual(manifest['fixtures']['after_hours_07']['state'], 'NOT_FOUND')
        self.assertTrue(manifest['repo_ledger_untouched'])
        text = report.summary(self.out)[0]
        identity = fixture.rail_demo_identity()
        self.assertIn('- Rail Demo seed (invented data, built by the program): revision %d, builder SHA-256 %s' % (identity['revision'], identity['builder_sha256'][:16]), text)
        self.assertEqual((report._rail_demo(None), report._rail_demo({'builder': 'workbench/rail_demo.py', 'state': 'NOT_FOUND'})), ('not recorded', 'not recorded'),
                         'a run made before Rail Demo, or without its builder, says so')
        self.assertIn('- demo: Pass 4', text)

    def test_the_trace_of_settled_power_and_the_exact_3_W(self):
        got = self.checks('DA01')
        self.assertEqual(got, {'power_w': '3', 'unit': 'W', 'exact_recomputed': '3', 'inputs_basis': ['REVIEWED_PDF_ROW'], 'traces_to_sheet': True,
                               'traces_to_pdf': True, 'pdf_source_is_the_admitted_one': True})

    def test_250_to_300_mA_is_carried_to_3_6_W_and_read_back_by_a_fresh_process(self):
        got = self.checks('DA16')
        self.assertEqual(len(got), 28)
        self.assertEqual({k: got[k] for k in ('open_item', 'target_cell', 'was_power_w', 'preview_shows', 'cell_now', 'power_now_w', 'power_unit', 'voltage_input',
                                               'current_input', 'exact_check', 'finding_state', 'finding_says', 'startup_calc_state', 'source_row_3',
                                               'source_state', 'source_pdf_unchanged', 'source_link')},
                         {'open_item': 'Rail Demo bench readings', 'target_cell': 'B3', 'was_power_w': '3', 'preview_shows': ['250 mA', '300 mA'],
                          'cell_now': ['300', 'mA'], 'power_now_w': '18/5', 'power_unit': 'W', 'voltage_input': ['12', 'REVIEWED_PDF_ROW'],
                          'current_input': ['300', 'WORKING_SHEET_EDIT'], 'exact_check': True, 'finding_state': 'recheck',
                          'finding_says': 'says 3 W; now 3.6 W', 'startup_calc_state': 'recheck', 'source_row_3': ['250', 'mA'],
                          'source_state': 'CURRENT_PDF_SOURCE', 'source_pdf_unchanged': True, 'source_link': True})
        self.assertEqual({k: v for k, v in got.items() if k.startswith('reopened:')},
                         {'reopened:cell': ['300', 'mA'], 'reopened:same_revision': True, 'reopened:power_w': '18/5', 'reopened:power_unit': 'W',
                          'reopened:finding_state': 'recheck', 'reopened:finding_says': 'says 3 W; now 3.6 W', 'reopened:source_row_3': ['250', 'mA']})
        self.assertEqual({k: v for k, v in got.items() if k.startswith('policy_table:')},
                         {'policy_table:set_waits_for_approval': False, 'policy_table:offered_steps_waiting_for_approval': ['office.datasheet.recheck'],
                          'policy_table:offered_steps_done_without_asking': ['agenda.add']})
        self.assertEqual(self.results['DA16']['notes']['driver'], cases_anchor.SCRIPTED)

    def test_a_backup_of_rail_demo_is_verified_restored_and_read_and_a_changed_copy_is_caught(self):
        got = self.checks('DA17')
        self.assertEqual(got, {'verify': 'VERIFIED', 'restore': 'RESTORED', 'existing_destination': 'REFUSED', 'tampered': 'Changed backup member',
                               'create': 'VERIFIED', 'restored_desk_reads': True,
                               'restored_desk_counts': ['3 sources', '3 sheets', '2 calculations', '1 page', '4 findings', '1 open question'],
                               'restored_desk_is_the_saved_one': True})
        self.assertEqual([f['fault'] for f in self.results['DA17']['injected_faults']], ['one byte changed in a copy of the backup'])

    def test_killed_after_the_write_and_resumed_from_its_checkpoint(self):
        result = self.results['DA27']
        self.assertEqual([p['phase'] for p in result['phases']], ['first', 'resume'])
        self.assertTrue(result['phases'][0]['killed_at_checkpoint'])
        self.assertEqual(self.checks('DA27'), {'resumed_from': 'set', 'completed_change_recognised': True, 'replay_with_old_revision': 'REFUSED',
                                               'power_now_w': '18/5', 'sheet_versions': ['version 2'], 'settled_results': ['3.6 W'],
                                               'settled_calculations': ['Rail Demo settled power · 3.6 W'], 'finding_state': 'recheck'})
        self.assertEqual(result['fixture']['seed'], 'rail_demo')
        self.assertIn('resumed', result['fixture'])
        # 0.8.5: the records are found once, before the write, and the resumed phase works on the ones its checkpoint keeps
        lines = [json.loads(line) for line in (Path(result['folder']) / 'progress.jsonl').read_text().splitlines()]
        reads = {phase: [line['op'] for line in lines if line['step'] == 'op' and line['phase'] == phase] for phase in ('first', 'resume')}
        self.assertIn('intake.items', reads['first'])
        self.assertNotIn('intake.items', reads['resume'])
        self.assertEqual(sorted(json.loads((Path(result['folder']) / 'checkpoint.json').read_text())['records']), ['calc_settled', 'claim_settled', 'sheet'])
        self.assertEqual(set(reads['first'] + reads['resume']) - set(runner.registry()['DA27'].allowed), set(), 'every read is one the case allows')

    def test_p01_is_played_on_rail_demo_in_the_graphite_look_and_in_the_kasandra_look(self):
        self.assertEqual(self.kas_code, 0)
        scene = cases_scene.load('P01')
        for look, results in (('graphite', self.results), ('kasandra', self.kas)):
            result = results['DP01a']
            self.assertEqual(result['outcome'], 'Pass', (look, result.get('reason'), result.get('error')))
            self.assertEqual(result['notes']['appearance'], look)
            self.assertIs(result['notes']['passed'], True, look)
            steps = result['notes']['steps']
            self.assertEqual([s['act'] for s in steps], [s['act'] for s in scene['steps']], look)
            self.assertTrue(all(s['ok'] and s['by'] in ('pointer', 'direct') for s in steps), (look, [(s['act'], s['ok'], s['by']) for s in steps]))
            got = self.checks('DP01a', results)
            self.assertEqual(len(got), len(runner.registry()['DP01a'].expect), look)
            self.assertEqual((got['12:desk.field.selected.title'], got['13:desk.field.route.hops'], got['15:desk.field.revisions.a'], got['15:desk.field.revisions.b']),
                             ('Rail Demo bench readings', 2, 'Rail Demo limits Rev A ARCHIVED', 'Rail Demo limits Rev B CURRENT'), look)
            self.assertEqual(got['17:act.result.trashed'], 'Rail Demo bench readings.csv', look)
            shots = sorted(p.name for p in (Path(result['folder']) / 'shots').glob('*.png'))
            self.assertEqual(shots, ['%02d.png' % n for n in range(1, len(scene['steps']) + 1)], look)

    def test_the_same_scene_on_the_owners_workspace_is_blocked_here_not_failed(self):
        result = self.results['P01a']
        self.assertEqual(result['outcome'], 'Blocked')
        self.assertIn('the owner\'s After Hours 07 backup (not found under', result['reason'])
        self.assertEqual(result['phases'], [], 'nothing was started for it')


class ABuildThatBreaks(unittest.TestCase):
    """Blocked means a prerequisite is missing here. A build of Rail Demo that breaks once its prerequisites are met is a
    fault of the program (or of a tool it was given), and a case that stands on it is a Fail."""

    def test_only_what_the_sources_need_blocks_and_a_build_that_breaks_is_not_caught(self):
        from workbench import rail_demo
        with tempfile.TemporaryDirectory() as folder:
            # what a PDF source needs is not here: Blocked, with the sentence, before anything is made
            with mock.patch.object(rail_demo, 'available', return_value='Rail Demo needs Poppler.'), \
                    mock.patch.object(fixture, 'base_workspace', side_effect=AssertionError('nothing is made')):
                with self.assertRaises(fixture.Blocked) as blocked:
                    fixture.rail_demo_workspace(folder)
            self.assertEqual(str(blocked.exception), 'Rail Demo needs Poppler.')
            # it is here, and the build breaks: the build's own exception, which the runner scores as a Fail
            broke = rail_demo.Unavailable('Rail Demo could not be built: the references.pdf.page job ended Failed (x).')
            with mock.patch.object(rail_demo, 'available', return_value=''), mock.patch.object(fixture, 'base_workspace', return_value=(None, None)), \
                    mock.patch.object(rail_demo, 'build', side_effect=broke):
                with self.assertRaises(rail_demo.Unavailable) as raised:
                    fixture.rail_demo_workspace(folder)
            self.assertIs(raised.exception, broke)
            self.assertNotIsInstance(raised.exception, fixture.Blocked)

    def test_a_run_with_a_poppler_that_does_not_work_is_a_fail_with_the_builds_own_sentence(self):
        with tempfile.TemporaryDirectory(prefix='graphite-rail-demo-broken-') as folder:
            tools = Path(folder) / 'tools'
            tools.mkdir()
            for name in ('pdftotext', 'pdftoppm'):          # present, so the need is met; and they do nothing but fail
                (tools / name).write_text('#!/bin/sh\nexit 1\n')
                (tools / name).chmod(0o755)
            code, results = run(Path(folder) / 'run', ['DA01'], first_on_path=tools)
            result = results['DA01']
            self.assertEqual(result['outcome'], 'Fail', result.get('reason'))
            self.assertEqual([(n['need'], n['met']) for n in result['needs']], [('rail_demo', True)])
            self.assertIn('Unavailable: Rail Demo could not be built: ', result['reason'])
            self.assertIn('case broke after 0 of 7 checks met', result['reason'])
            self.assertIn('Fail 1', report.summary(Path(folder) / 'run')[0])


if __name__ == '__main__':
    unittest.main()
