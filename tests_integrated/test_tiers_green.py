"""1.1 T1: the tiers green. The real faults the 27 November tier runs found, each held by the smallest test of its own, and
the tier runner's looks. Offscreen; no model, no network, nothing outside a temporary folder.

The faults: the keyboard-grab crash (test_desk_acts died with exit -11: an icon engine made in Python was freed while Qt
still painted it on a tab), the door's Kernel operations named like a desk act, her mode in the desk acts still called
'slate', the Settings view lost at the next start when it named one of this computer's rows, the owner's last request
taken from words Graphite made, a launch that left Home or a room in front opening the board instead, the plan for one
message grown past the smallest model's context, Day and Night never put through the colour-vision check, and the
campaign's simulated worker launch taking every other program started meanwhile.
"""
import gc
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT, ROOT / 'tools'):
    if str(folder) not in sys.path:sys.path.insert(0, str(folder))
from tools import run_tiers as tiers


def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class TheCrash(unittest.TestCase):
    def test_a_packed_icon_on_a_tab_still_paints_after_python_lets_go_of_it(self):
        """The exit -11: QTabBar painting a tab whose icon engine Python had already freed (ux_assets.PackedIcon)."""
        app()
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QTabBar
        from workbench import ux_assets
        bar = QTabBar();bar.resize(400, 40)
        names = [n for n in ('export', 'import', 'search', 'save', 'refresh') if not ux_assets.icon(ROOT, n).isNull()]
        self.assertTrue(names, 'the asset pack gives icons')
        for name in names:
            icon = ux_assets.icon(ROOT, name);bar.addTab(QIcon(icon), name)      # a copy: QIcon clones the engine on change
            del icon
        gc.collect()
        for _ in range(3):
            image = bar.grab().toImage();gc.collect()
        self.assertFalse(image.isNull())
        self.assertTrue(all(not bar.tabIcon(i).isNull() for i in range(bar.count())))

    def test_the_engines_qt_holds_are_held(self):
        app()
        from shiboken6 import Shiboken
        from workbench import ux_assets
        icon = ux_assets.icon(ROOT, 'search')
        if icon.isNull():self.skipTest('no search icon in this asset pack')
        held = ux_assets._HELD[-1];self.assertIsInstance(held, ux_assets.PackedIcon)
        gc.collect();self.assertTrue(Shiboken.isValid(held), 'kept while the icon holds it')


class Names(unittest.TestCase):
    def test_no_kernel_operation_looks_like_a_desk_act(self):
        from workbench import desk_acts
        from workbench.engineering_kernel import CAPABILITIES
        self.assertEqual([o for o in CAPABILITIES if desk_acts.looks_like_act(o)], [])
        self.assertLessEqual({'door.state', 'door.continue', 'door.stop'}, set(CAPABILITIES))
        self.assertFalse({'hand.door', 'hand.door.continue', 'hand.door.stop'} & set(CAPABILITIES))

    def test_type_to_her_turns_the_line_to_its_mode_line_and_reads_back_her(self):
        from workbench import desk_doers, typebar_qt
        self.assertEqual(desk_doers.WHO['her'], 'line')
        self.assertIn(desk_doers.WHO['her'], dict(typebar_qt.MODES))
        self.assertEqual(desk_doers.WHO_OF['line'], 'her')
        self.assertLessEqual(set(desk_doers.WHO.values()), set(dict(typebar_qt.MODES)))


class TheLooks(unittest.TestCase):
    def test_day_and_night_join_the_looks_and_every_look_is_named_to_the_child(self):
        self.assertEqual(tiers.LOOKS, ('graphite', 'kasandra', 'day', 'night'))
        with tempfile.TemporaryDirectory() as scratch:
            for look in tiers.LOOKS:
                self.assertEqual(tiers.child_environment(look, scratch)['GRAPHITE_APPEARANCE'], look)

    def test_look_lists(self):
        self.assertEqual(tiers.looks_of('both'), ['graphite', 'kasandra'])
        self.assertEqual(tiers.looks_of('all'), list(tiers.LOOKS))
        self.assertEqual(tiers.looks_of('graphite, Day,graphite'), ['graphite', 'day'])
        with self.assertRaises(Exception):tiers.looks_of('noir')

    def test_only_runs_what_it_names(self):
        units, _ = tiers.plan(2, ['graphite', 'day'], tiers.config(), modules=['test_a', 'test_b'], checks=['tools/check_x_ui.py'])
        kept = tiers.only(units, ['test_b', 'check_x_ui.py'])
        self.assertEqual(sorted((u['name'], u['look']) for u in kept),
                         [('test_b', 'day'), ('test_b', 'graphite'), ('tools/check_x_ui.py', 'day'), ('tools/check_x_ui.py', 'graphite')])


class Remembered(unittest.TestCase):
    def test_a_settings_view_on_one_of_this_computers_rows_is_read_back(self):
        app()
        from workbench.session import SCHEMA, Session
        from workbench.system_settings_qt import nodes
        row = next(n['id'] for n in nodes() if n['parent'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'session-r10.json'
            view = {'mode': 'settings', 'selected': row, 'expanded': [nodes()[0]['id'], 'settings:ledger']}
            path.write_text(json.dumps({'schema': SCHEMA, 'settings_navigation': view}))
            self.assertEqual(Session(path).state.get('settings_navigation'), view)
            path.write_text(json.dumps({'schema': SCHEMA, 'settings_navigation': dict(view, selected='system:nowhere')}))
            self.assertNotIn('settings_navigation', Session(path).state, 'a row that is not there is still refused')


class TheOwnersWords(unittest.TestCase):
    def test_a_trace_or_a_doubt_is_not_noted_as_the_owners_request(self):
        from workbench import field_page
        asked = []
        shell = SimpleNamespace(face=SimpleNamespace(thing=None), ask=lambda text, about=None, request=True:asked.append((text, request)))
        host = SimpleNamespace(shell2=shell, _field_active=False)
        obj = SimpleNamespace(id='a' * 32, title='Bench readings')
        with patch.object(field_page, 'thing_of', return_value={}):
            field_page.trace(host, obj);field_page.doubt(host, obj)
        self.assertEqual([r for _, r in asked], [False, False])

    def test_a_launch_with_home_or_a_room_in_front_and_nothing_on_the_desk_stays_there(self):
        from workbench import field_page
        empty = (SimpleNamespace(objects=[]), None)
        shown = []
        for home, tabs, opens in ((True, 0, False), (False, 1, False), (False, 0, True)):
            host = SimpleNamespace(ledger_bridge=SimpleNamespace(kernel=object()), _field_active=False, _home_active=home,
                                   tabs=SimpleNamespace(count=lambda tabs=tabs:tabs))
            shown.clear()
            with patch.object(field_page, 'read_field', return_value=empty), \
                 patch.object(field_page, 'show_field', side_effect=lambda h, reading=None:shown.append(h) or SimpleNamespace()), \
                 patch('workbench.board_qt.to_board', return_value=None):
                field_page.open_on_work(host)
            self.assertEqual(bool(shown), opens, (home, tabs))


class Budgets(unittest.TestCase):
    def test_the_plan_for_one_message_stays_under_the_smallest_models_context(self):
        from workbench import local_brain
        for message in ('plot the voltage against time from the csv', 'open the price list sheet', 'show the network traffic rate today',
                        'what can I spend each week and stay under the monthly budget'):
            _, direct, chosen = local_brain.proposal_profile(message)
            self.assertLess(len(json.dumps(direct, separators=(',', ':'))), local_brain.PLAN_TOOL_LIMIT, message)
            self.assertEqual(len(direct), len(local_brain.CORE_OPERATIONS) + len(chosen))


class Sight(unittest.TestCase):
    def test_day_and_night_leave_no_close_pair_without_a_word_or_a_shape(self):
        import colour_vision
        for look in ('day', 'night'):
            self.assertEqual(colour_vision.unreviewed(look), [], look)
            close = {frozenset(r['pair']) for r in colour_vision.table(look) if r['least'] < colour_vision.THRESHOLD}
            self.assertEqual({frozenset(p) for p in colour_vision.REVIEWED[look]} - close, set(), look)

    def test_a_button_that_paints_a_mark_has_no_word_to_cut(self):
        app()
        import ui_fit
        from workbench.apps_qt import PlusButton
        plus = PlusButton(SimpleNamespace(root=ROOT));plus.resize(8, 24)
        self.assertFalse(ui_fit._shows_words(plus))


class TheBench(unittest.TestCase):
    def test_only_a_model_worker_is_scripted(self):
        from campaign_lib import sim
        bench = sim.Bench.__new__(sim.Bench);bench.popen_argv = [];bench.workers = [];bench.by_pid = {}
        bench.procs = SimpleNamespace(spawn=lambda:4242)
        popen = bench._model_popen()
        done = popen([sys.executable, '-c', 'print(7)'], stdout=subprocess.PIPE)
        self.assertEqual(done.communicate()[0].strip(), b'7');self.assertEqual(bench.popen_argv, [])
        popen([sys.executable, '-m', 'workbench.brain_worker', '--backend', 'CPU'])
        self.assertEqual(len(bench.popen_argv), 1)


if __name__ == '__main__':
    unittest.main()
