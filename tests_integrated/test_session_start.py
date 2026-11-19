"""0.8.4: Graphite starts on whatever its session file holds, and her column says "Now:" once.

Three faults of 0.8.3, found on 19 November 2026 by a review of code that had been built on it. No test had met them:
every window the suite builds is built on a new profile and without restoring a session.

1. A saved appearance that is not text. The theme reads the session file's 'appearance' when it is first imported, before
   any window. A list or an object there (a damaged or hand-edited file) was looked up among the palettes, which cannot be
   done with a list: TypeError, and Graphite could not start. Now any value that is not one of the looks as text is
   Graphite, in the theme and in the session, and both read one list of looks (presentation_preferences.APPEARANCES), which
   the session reads without importing the theme.

2. A room left open. The window restores its saved tabs while it is being built, before the bridge that opens the Office
   and the Graphite room exists. A session saved with one of them open (the dedicated session's start script opens the
   Office at every start) stopped the next start: "'WorkbenchWindow' object has no attribute 'ledger_bridge'". Now a saved
   tab that is made with the bridge waits, and the rows after it wait with it in their order, until the window is whole;
   and one saved tab that cannot be opened for any other reason is kept in Reopen deferred tabs instead of stopping the
   start. Opening what waited is part of restoring the session: it does not leave Home, which is already in front by then
   when it was in front at leaving. (The first form of this fix left Home for each room and showed it again; the start
   script's opening of the Office, at the first turn of the event loop, then ended inside Qt with no message, at every
   start after leaving with Home in front and a room open. StartScript below makes that start in a process of its own.)
   A room is a room whatever sits beside it: a Preview dragged to its left no longer sets it aside.

   Two more values of the session file were looked up without being text, as the appearance was: the build target and
   the place last shown in the settings. A list in either stopped the start; now only text is looked up.

   And leaving with the Manual open raised while the strip was written down, so that session was not saved at all.

3. "Now: Now: ...". The Agenda's one-line summary began with "Now:" while something was running, and her column, which
   names that line "Now:", said it again. The summary no longer carries the line's name; in every look.
"""
import contextlib
import io
import json
import os
import platform
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from workbench import boss_theme, presentation_preferences
from workbench.session import SCHEMA, Session

ROOT = Path(__file__).resolve().parents[1]
NOT_A_LOOK = (['kasandra'], ['graphite', 'kasandra'], [], {'kasandra': True}, {'key': 'kasandra'}, {}, 7, 1.5, True, None, '', 'Kasandra',
              'pencil', 'kasandra ')
DEEP = 30000      # a value nested this far is past what json reads here (RecursionError, which is not a ValueError), in a file the session still reads (60 KB)


def saved(folder, value):
    path = Path(folder) / 'session-r10.json'
    path.write_text(json.dumps({'schema': SCHEMA, 'appearance': value}), encoding='utf-8');return path


class SavedAppearance(unittest.TestCase):
    def test_a_saved_appearance_that_is_not_one_of_the_looks_as_text_is_graphite(self):
        with tempfile.TemporaryDirectory() as folder:
            for value in NOT_A_LOOK:
                path = saved(folder, value)
                self.assertEqual(boss_theme.chosen_appearance({}, path), 'graphite', value)      # 0.8.3: TypeError for a list or an object
                self.assertNotIn('appearance', Session(path).state, value)
                self.assertIsNone(presentation_preferences.appearance(value), value)
            for key, _ in presentation_preferences.APPEARANCES:
                path = saved(folder, key)
                self.assertEqual(boss_theme.chosen_appearance({}, path), key);self.assertEqual(Session(path).state['appearance'], key)
                self.assertEqual(boss_theme.chosen_appearance({'GRAPHITE_APPEARANCE': key}, saved(folder, ['x'])), key, 'the environment first, whatever the file holds')

    def test_graphite_starts_on_a_session_file_whose_appearance_is_a_list(self):
        """The start itself: the theme chooses the look when it is first imported, which is before any window."""
        env = {k: v for k, v in os.environ.items() if k != 'GRAPHITE_APPEARANCE'}
        code = 'from workbench import boss_theme, assistant_identity;print("LOOK", boss_theme.APPEARANCE)'
        with tempfile.TemporaryDirectory() as folder:
            env['ARC1_WORKBENCH_CONFIG_HOME'] = folder
            for value, look in ((['kasandra'], 'graphite'), ({'look': 'kasandra'}, 'graphite'), ('kasandra', 'kasandra')):
                saved(folder, value)
                done = subprocess.run([sys.executable, '-B', '-c', code], cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=120)
                self.assertEqual((done.returncode, done.stdout.strip()), (0, 'LOOK ' + look), done.stderr[-2000:])

    def test_a_value_nested_past_reading_is_graphite_and_a_new_session(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'session-r10.json'
            path.write_text('{"schema": "%s", "appearance": %s%s}' % (SCHEMA, '[' * DEEP, ']' * DEEP), encoding='utf-8')
            self.assertEqual(boss_theme.chosen_appearance({}, path), 'graphite')      # 0.8.3: RecursionError, from both readers
            session = Session(path)
            self.assertNotIn('appearance', session.state);self.assertEqual(session.state['documents'], [])

    def test_a_saved_target_or_settings_place_that_is_not_text_is_the_default(self):
        """The same fault in two other places of the session file, in 0.8.3 already: a list looked up among the build
        targets, or among the places of the settings."""
        from workbench.engine import DEFAULT_TARGET, TARGETS
        from workbench.settings_registry import nodes
        other = next(key for key in sorted(TARGETS) if key != DEFAULT_TARGET);place = nodes()[0]['id']
        def written(folder, target, selected):
            path = Path(folder) / 'session-r10.json'
            path.write_text(json.dumps({'schema': SCHEMA, 'target': target, 'settings_navigation': {'mode': 'settings', 'selected': selected, 'expanded': []}}), encoding='utf-8')
            return Session(path).state
        with tempfile.TemporaryDirectory() as folder:
            new = Session(Path(folder) / 'none.json').state
            for value in (['f133'], [other], [], {other: True}, {}, 7, 1.5, True, None, ''):
                state = written(folder, value, value)      # 0.8.3: TypeError: unhashable type, for a list or an object
                self.assertEqual(state['target'], DEFAULT_TARGET, value)
                self.assertEqual(state.get('settings_navigation'), new.get('settings_navigation'), value)
            state = written(folder, other, place)
            self.assertEqual((state['target'], state['settings_navigation']['selected']), (other, place), 'text that is one of them is kept, as before')

    def test_there_is_one_list_of_looks_and_the_session_does_not_import_the_theme(self):
        looks = [key for key, _ in presentation_preferences.APPEARANCES]
        self.assertIs(boss_theme.APPEARANCES, presentation_preferences.APPEARANCES)
        self.assertEqual(sorted(looks), sorted(boss_theme.PALETTES), 'a palette for each look, and no palette without one')
        self.assertIn(presentation_preferences.APPEARANCE_DEFAULT, looks);self.assertIn(boss_theme.APPEARANCE, looks)
        from workbench.desk_acts import ACTS
        self.assertEqual(ACTS['look.set'].schema['properties']['appearance']['enum'], looks, 'the act that chooses the look offers the same ones')
        with patch.object(presentation_preferences, 'APPEARANCES', presentation_preferences.APPEARANCES + (('chalk', 'Chalk'),)), \
                tempfile.TemporaryDirectory() as folder:
            path = saved(folder, 'chalk')
            self.assertEqual(Session(path).state['appearance'], 'chalk', 'a look added to the list is kept by the session with no other change')
            self.assertEqual(boss_theme.chosen_appearance({}, path), 'graphite', 'and is Graphite until the theme has a palette for it')
        code = 'import sys;import workbench.session;print("THEME", "workbench.boss_theme" in sys.modules, "PySide6" in sys.modules)'
        done = subprocess.run([sys.executable, '-B', '-c', code], cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        self.assertEqual((done.returncode, done.stdout.strip()), (0, 'THEME False False'), done.stderr[-2000:])


def qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def strip_host():
    """As much of the window as the tab strip asks of it while a session is restored. Its rooms are opened as the window
    opens them: by the bridge, which this host does not have until a test gives it one."""
    qt()
    from PySide6.QtWidgets import QMainWindow, QWidget
    from workbench.workspace_tabs import WorkspaceTabs

    class Host(QMainWindow):
        def __init__(self):
            super().__init__();self.calls = [];self._nav_devices = {};self.root = Path('/nowhere')
            self.tabs = WorkspaceTabs(self);self.setCentralWidget(self.tabs)

        def add(self, name, room=False):
            self.calls.append(name);page = QWidget();page.setObjectName(name);page.setProperty('ledgerRoom', room)
            self.tabs.setCurrentIndex(self.tabs.addTab(page, name));return page

        def show_office(self):return self.ledger_bridge.show_office()

        def show_slate(self):return self.ledger_bridge.show_slate()

        def show_clip_workspace(self):
            self.ledger_bridge.command_finished;return self.add('talk')      # its tab listens to the bridge as it is made

        def show_readiness(self):return self.add('readiness')

        def show_tools(self):return self.add('tools')

        def show_manual(self):raise RuntimeError('this tab cannot be made')

        def close_tab(self, index):self.tabs.removeTab(index);return True

        def bridge(self):
            self.ledger_bridge = SimpleNamespace(show_office=lambda:self.add('office', True), show_slate=lambda:self.add('slate', True), command_finished=None)

        def strip(self):return [self.tabs.widget(i).objectName() for i in range(self.tabs.count())]

    return Host()


def rows(*kinds, pinned=()):
    return [{'kind': kind, 'pinned': kind in pinned} for kind in kinds]


class TabsThatWaitForTheBridge(unittest.TestCase):
    def test_a_room_is_not_opened_before_the_bridge_exists_and_is_opened_once_it_does(self):
        for kind, name in (('OfficeBuildingTab', 'office'), ('SlateRoomTab', 'slate'), ('ClipWorkspaceTab', 'talk')):
            host = strip_host();tabs = host.tabs
            tabs.restore({'tabs': rows(kind), 'active': 0, 'deferred': []})      # 0.8.3: AttributeError, no 'ledger_bridge'
            self.assertEqual((host.calls, host.strip(), tabs.deferred), ([], [], []), kind)
            self.assertEqual([row['kind'] for _, row in tabs.waiting], [kind])
            self.assertEqual(host.statusBar().currentMessage(), '')
            host.bridge();tabs.restore_waiting()
            self.assertEqual((host.calls, host.strip(), tabs.deferred, tabs.waiting), ([name], [name], [], []), kind)
            self.assertEqual(host.statusBar().currentMessage(), '', 'nothing was set aside')

    def test_every_row_keeps_its_turn_its_place_and_what_was_in_front(self):
        host = strip_host();tabs = host.tabs
        # the strip as it was saved: two rooms, then the Preview, which had been dragged before the pin
        state = {'tabs': rows('SlateRoomTab', 'OfficeBuildingTab', 'ToolInventoryTab', 'ReadinessTab', pinned=('ReadinessTab',)), 'active': 1, 'deferred': []}
        tabs.restore(state)
        self.assertEqual(host.calls, ['readiness'], 'the pin has its turn first, as always; the rooms wait, and the Preview behind them')
        self.assertEqual([row['kind'] for _, row in tabs.waiting], ['SlateRoomTab', 'OfficeBuildingTab', 'ToolInventoryTab'])
        host.bridge();tabs.restore_waiting()
        self.assertEqual(host.calls, ['readiness', 'slate', 'office', 'tools'])
        self.assertEqual(host.strip(), ['slate', 'office', 'tools', 'readiness'], 'each where it was saved, not where its turn put it')
        self.assertEqual(tabs.currentWidget().objectName(), 'office', 'the one that was in front')
        self.assertEqual([w.objectName() for w in tabs.pinned()], ['readiness']);self.assertEqual(tabs.preview().objectName(), 'tools')
        self.assertEqual((tabs.deferred, tabs.waiting), ([], []))

    def test_with_the_bridge_already_there_nothing_waits(self):
        host = strip_host();host.bridge()
        host.tabs.restore({'tabs': rows('OfficeBuildingTab', 'ReadinessTab'), 'active': 0, 'deferred': []})
        self.assertEqual((host.strip(), host.tabs.waiting, host.tabs.currentWidget().objectName()), (['office', 'readiness'], [], 'office'))

    def test_a_saved_tab_that_cannot_be_opened_is_kept_and_does_not_stop_the_start(self):
        """The damaged case: whatever one row does, the rows after it open and Graphite starts; the row is kept in Reopen
        deferred tabs and why it failed is printed, not swallowed."""
        host = strip_host();host.bridge();tabs = host.tabs;said = io.StringIO()
        with contextlib.redirect_stderr(said):
            tabs.restore({'tabs': rows('ManualTab', 'OfficeBuildingTab', 'ReadinessTab', pinned=('ManualTab',)), 'active': 1, 'deferred': []})      # 0.8.3: RuntimeError
        self.assertEqual(host.strip(), ['office', 'readiness']);self.assertEqual(tabs.currentWidget().objectName(), 'office')
        self.assertEqual(tabs.deferred, rows('ManualTab', pinned=('ManualTab',)))
        self.assertIn('RuntimeError: this tab cannot be made', said.getvalue())
        self.assertEqual(host.statusBar().currentMessage(), '1 former tabs retained in View → Reopen deferred tabs')

    def test_a_preview_left_of_a_room_does_not_set_the_room_aside(self):
        """A room is neither the Preview nor a pin: a Preview already open at a room's turn (dragged to the left of it
        before leaving) is nothing to the room. It used to set the room aside, at every start from then on."""
        for bridge_first in (True, False):
            host = strip_host();tabs = host.tabs
            host.return_thread = SimpleNamespace(show=lambda host=host:host.add('return', True))      # the Return thread's room, the third room a session can hold
            if bridge_first:host.bridge()
            tabs.restore({'tabs': rows('ToolInventoryTab', 'OfficeBuildingTab', 'SlateRoomTab', 'ReturnTab'), 'active': 1, 'deferred': []})
            if not bridge_first:host.bridge();tabs.restore_waiting()
            self.assertEqual((host.strip(), tabs.deferred, tabs.waiting), (['tools', 'office', 'slate', 'return'], [], []), bridge_first)
            self.assertEqual(tabs.currentWidget().objectName(), 'office');self.assertEqual(tabs.preview().objectName(), 'tools')
            self.assertEqual(host.statusBar().currentMessage(), '', 'nothing was set aside')
        host = strip_host();host.bridge();tabs = host.tabs      # the Preview's place is still one place: a second Preview row is kept for later
        tabs.restore({'tabs': rows('ToolInventoryTab', 'OfficeBuildingTab', 'ReadinessTab'), 'active': 0, 'deferred': []})
        self.assertEqual((host.strip(), tabs.deferred), (['tools', 'office'], rows('ReadinessTab')))

    def test_a_tab_closed_between_the_two_turns_is_not_counted_among_the_restored(self):
        host = strip_host();tabs = host.tabs
        tabs.restore({'tabs': rows('ReadinessTab', 'SlateRoomTab', 'OfficeBuildingTab', pinned=('ReadinessTab',)), 'active': 0, 'deferred': []})
        self.assertEqual(host.strip(), ['readiness']);host.close_tab(0)
        host.bridge();tabs.restore_waiting()
        self.assertEqual(host.strip(), ['slate', 'office'], 'the rooms where they were saved: the place of the closed tab is not kept for it')
        self.assertEqual((tabs.deferred, tabs.waiting, tabs.restored), ([], [], []))

    def test_nothing_is_said_of_a_row_set_aside_while_others_still_wait(self):
        host = strip_host();tabs = host.tabs
        with contextlib.redirect_stderr(io.StringIO()):
            tabs.restore({'tabs': rows('ManualTab', 'OfficeBuildingTab', 'ReadinessTab', pinned=('ManualTab',)), 'active': 1, 'deferred': []})
        self.assertEqual((tabs.deferred, [row['kind'] for _, row in tabs.waiting]), (rows('ManualTab', pinned=('ManualTab',)), ['OfficeBuildingTab', 'ReadinessTab']))
        self.assertEqual(host.statusBar().currentMessage(), '', 'the restore is not over: what was set aside is said once, at its end')
        host.bridge();tabs.restore_waiting()
        self.assertEqual(host.strip(), ['office', 'readiness']);self.assertEqual(tabs.currentWidget().objectName(), 'office', 'what was in front is still known at the second turn')
        self.assertEqual(host.statusBar().currentMessage(), '1 former tabs retained in View → Reopen deferred tabs')

    def test_a_strip_that_was_never_restored_has_nothing_waiting(self):
        host = strip_host();tabs = host.tabs
        self.assertEqual((tabs.waiting, tabs.restored, tabs.deferred, tabs.restore_active), ([], [], [], None))
        tabs.restore_waiting()      # was AttributeError: the strip only had these once a session had been restored
        self.assertEqual((host.strip(), tabs.waiting, tabs.deferred, tabs.snapshot()['deferred']), ([], [], [], []))
        self.assertEqual(host.statusBar().currentMessage(), '')

    def test_a_tab_is_written_down_whatever_it_calls_its_group(self):
        """Leaving writes every open tab down. A device group's tab has a group with a name; the Manual has a chooser
        it calls 'group', which has none: 0.8.3 raised on it, and a session left with the Manual open was not saved."""
        from PySide6.QtWidgets import QComboBox, QWidget
        host = strip_host();tabs = host.tabs
        manual = QWidget();manual.group = QComboBox(manual);device = QWidget();device.group = SimpleNamespace(title='Power')
        self.assertEqual(tabs.descriptor(manual), {'kind': 'QWidget', 'pinned': False})      # 0.8.3: AttributeError: 'QComboBox' object has no attribute 'title'
        self.assertEqual(tabs.descriptor(device), {'kind': 'QWidget', 'pinned': False, 'group': 'Power'})
        tabs.addTab(manual, 'manual');json.dumps(tabs.snapshot())

    def test_a_window_that_never_gets_a_bridge_keeps_the_room_for_later(self):
        host = strip_host();tabs = host.tabs
        tabs.restore({'tabs': rows('OfficeBuildingTab', 'ReadinessTab'), 'active': 0, 'deferred': []})
        with contextlib.redirect_stderr(io.StringIO()) as said:tabs.restore_waiting()
        self.assertEqual((host.strip(), tabs.deferred, tabs.waiting), (['readiness'], rows('OfficeBuildingTab'), []))
        self.assertIn('ledger_bridge', said.getvalue())


class SecondStart(unittest.TestCase):
    """The real window, offscreen, started three times on one profile and one workspace, as on three evenings: every hold
    of the right-click's tests in place (no provider request, no worker launch, no job, no session or power call)."""

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='graphite-084-start-');run = Path(cls.temporary.name)
        cls.env = patch.dict(os.environ, {'ARC_LEDGER_EMBEDDED': '1', 'ARC_LEDGER_DISABLE_BOOK_WATCHER': '1', 'ARC1_WORKBENCH_CONFIG_HOME': str(run / 'profile'),
                                          'ARC_LEDGER_CONCERN': str(run / 'Concern')});cls.env.start()
        os.environ.pop('ARC_LEDGER_XSESSION', None)
        from PySide6.QtWidgets import QMessageBox
        from workbench import clip, locations, session_power
        from workbench.engineering_kernel import Kernel
        from workbench.qt_app import make_app
        cls.holds = [patch.object(clip, '_request', side_effect=AssertionError('No provider request')), patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')),
                     patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')), patch.object(session_power, 'system', side_effect=OSError('no login session (held)')),
                     patch.object(QMessageBox, 'question', return_value=QMessageBox.No)]
        for hold in cls.holds:hold.start()
        cls.app = make_app([]);cls.root = locations.office(run / 'workspace');cls.path = run / 'profile' / 'session.json'

    @classmethod
    def tearDownClass(cls):
        for hold in reversed(cls.holds):hold.stop()
        cls.env.stop();cls.temporary.cleanup()

    def settle(self, w, ms=30):
        from PySide6.QtTest import QTest
        for name in ('agenda_runner', 'study_idle', 'ledger_bridge'):
            timer = getattr(getattr(w, name, None), 'timer', None)
            if timer is not None:timer.stop()
        try:w.type_bar.hatch.lifecycle.timer.stop()
        except AttributeError:pass
        for _ in range(3):self.app.processEvents();QTest.qWait(ms)

    def start(self):
        """One start: the session read from the profile and the window built on it, restoring, as workbench.launch does."""
        from workbench.qt_app import WorkbenchWindow
        w = WorkbenchWindow(self.root, Session(self.path, self.root));platform.processor()
        w.resize(1366, 768);w.show();self.settle(w);return w

    def leave(self, w):
        self.assertTrue(w.close(), 'Graphite closes the ordinary way, which saves the session');self.settle(w)
        w.deleteLater();self.app.processEvents()
        return json.loads(self.path.read_text(encoding='utf-8'))

    def strip(self, w):return [type(w.tabs.widget(i)).__name__ for i in range(w.tabs.count())]

    def views(self):
        from workbench import activity
        return [e['seq'] for e in activity.recent(self.root, 5000) if e.get('operation') == 'ledger.view']

    def test_a_session_left_with_rooms_open_starts_again_and_again(self):
        from workbench.qt_app import WorkbenchWindow
        rooms = ['SlateRoomTab', 'OfficeBuildingTab']
        with patch.object(WorkbenchWindow, '_first_tab') as first_tab:first = self.start()
        first_tab.assert_called_once_with()      # nothing was saved: the tab a workspace with a project opens on has its turn
        first.show_slate();first.show_office();self.settle(first)      # the Office, as the dedicated session's start script opens it
        self.assertEqual(self.strip(first), rooms)
        left = self.leave(first)
        self.assertEqual(([row['kind'] for row in left['workspace']['tabs']], left['workspace']['active']), (rooms, 1))
        seen = self.views();self.assertTrue(seen, 'the owner bringing a room forward is recorded')

        with patch.object(WorkbenchWindow, '_first_tab') as first_tab:second = self.start()      # 0.8.3: AttributeError: 'WorkbenchWindow' object has no attribute 'ledger_bridge'
        first_tab.assert_not_called()      # the saved rooms are still to come: no other tab is opened in their place
        self.assertEqual(self.strip(second), rooms, 'each room is back, where it was')
        self.assertEqual(type(second.tabs.currentWidget()).__name__, 'OfficeBuildingTab', 'and the one that was in front is in front')
        self.assertEqual((second.tabs.deferred, second.tabs.waiting), ([], []))
        self.assertFalse(second._home_active);self.assertIs(second.central_stack.currentWidget(), second.workspace_split)
        self.assertEqual(second.view_preferences['last_surface'], 'workspace')
        self.assertEqual(self.views(), seen, 'a restored tab is not the owner bringing one forward: no view is recorded')
        second.ledger_bridge.navigation()['office']();self.settle(second)      # the start script's opening finds the restored room
        self.assertEqual(self.strip(second), rooms)
        second.show_start();self.settle(second);self.assertTrue(second._home_active)
        left = self.leave(second)
        self.assertEqual(([row['kind'] for row in left['workspace']['tabs']], left['workspace']['deferred']), (rooms, []))
        self.assertEqual(left['view_preferences']['last_surface'], 'home')

        surfaces = [];set_view_preference = WorkbenchWindow.set_view_preference
        def kept(w, **values):
            surfaces.append(values.get('last_surface'));return set_view_preference(w, **values)
        with patch.object(WorkbenchWindow, 'set_view_preference', kept):third = self.start()
        self.assertEqual(self.strip(third), rooms);self.assertEqual((third.tabs.deferred, third.tabs.waiting), ([], []))
        self.assertTrue(third._home_active, 'Home was in front when Graphite was left, and is in front again')
        self.assertIsNot(third.central_stack.currentWidget(), third.workspace_split)
        self.assertEqual(third.view_preferences['last_surface'], 'home')
        self.assertNotIn('workspace', surfaces, 'and it was never left on the way: restoring a room is not the owner opening it')
        third.show_manual();self.settle(third)
        self.assertFalse(third._home_active, 'the owner opening something leaves Home, as ever')
        third.show_start();self.settle(third)
        left = self.leave(third)      # 0.8.3: with the Manual open, writing the strip down raised and the session was not saved
        self.assertEqual(([row['kind'] for row in left['workspace']['tabs']], left['workspace']['deferred']), (rooms + ['ManualTab'], []), 'nothing piles up from one start to the next')
        self.assertEqual(left['view_preferences']['last_surface'], 'home')

        fourth = self.start()
        self.assertEqual(self.strip(fourth), rooms + ['ManualTab'], 'the Preview that was saved behind the rooms waited with them, and is back in its place')
        self.assertEqual((fourth.tabs.deferred, fourth.tabs.waiting), ([], []));self.assertTrue(fourth._home_active)
        self.leave(fourth)

    def test_the_window_opens_what_waited_as_part_of_being_built(self):
        """restore_waiting_tabs by itself, on as much of a window as it touches: the tabs are opened while the window still
        counts as being built, which is what keeps Home in front (an opener's _close_start does nothing then); when none
        of them could be opened the first tab has its turn after all; and with nothing waiting it does nothing."""
        from workbench.qt_app import WorkbenchWindow
        def window(waiting, opens):
            said = []
            def restore_waiting():
                said.append(('restore', w._initializing));WorkbenchWindow._close_start(w);del tabs.waiting[:]      # as each room's opener does
            tabs = SimpleNamespace(waiting=list(waiting), restore_waiting=restore_waiting, count=lambda:opens)
            w = SimpleNamespace(tabs=tabs, _home_active=True, _field_active=False, _initializing=False, _first_tab=lambda:said.append('first tab'))
            WorkbenchWindow.restore_waiting_tabs(w);self.assertFalse(w._initializing)
            self.assertTrue(w._home_active, 'Home is not left for a restored tab');return said
        row = [(0, {'kind': 'OfficeBuildingTab'})]
        self.assertEqual(window(row, opens=1), [('restore', True)])
        self.assertEqual(window(row, opens=0), [('restore', True), 'first tab'])
        self.assertEqual(window([], opens=0), [])


class StartScript(unittest.TestCase):
    """The start the dedicated session's script makes, each in a process of its own (session_start_probe): the window is
    built on the saved session and shown, and the Office is opened at the first turn of the event loop."""

    def test_left_with_home_in_front_and_a_room_open_the_next_starts_open_the_office(self):
        from tests_integrated.session_start_probe import probe
        office = ['OfficeBuildingTab']
        with tempfile.TemporaryDirectory(prefix='graphite-084-script-') as run:
            first = probe(run, 'home')      # a new profile: the script opens the Office, the owner goes Home and leaves
            self.assertEqual((first['opened']['tabs'], first['opened']['current'], first['left']['home']), (office, 'OfficeBuildingTab', True), first)
            self.assertEqual((first['code'], first['closed'], first['saved']['tabs'], first['saved']['last_surface']), (0, True, office, 'home'), first)
            for start in ('the second start', 'the third'):
                again = probe(run, 'home')      # the first form of the fix: ended inside Qt (a segmentation fault) at the script's opening, at every start
                built, opened = again['built'], again['opened']
                self.assertEqual((built['tabs'], built['waiting'], built['deferred']), (office, [], []), start)
                self.assertEqual((built['home'], built['workspace_in_front'], built['last_surface']), (True, False, 'home'), 'Home was in front at leaving, and is when the window is built')
                self.assertEqual((opened['tabs'], opened['current'], opened['home'], opened['workspace_in_front']), (office, 'OfficeBuildingTab', False, True),
                                 "the script's opening brings the restored Office forward")
                self.assertEqual((again['code'], again['closed'], again.get('error')), (0, True, None), start)
                self.assertEqual((again['saved']['tabs'], again['saved']['deferred'], again['saved']['last_surface']), (office, [], 'home'), start)


class NowLine(unittest.TestCase):
    def test_the_summary_does_not_carry_the_lines_name(self):
        qt()
        from workbench import agenda_qt
        running = {'now': [{'title': 'Read the bench readings'}], 'counts': {'next': 2, 'waiting': 1}}
        with patch.object(agenda_qt, 'call', return_value=running):
            self.assertEqual(agenda_qt.summary(None), ('Read the bench readings  ·  2 next  ·  {waiting}  ·  {open}', 1))      # 0.8.3: 'Now: Read ...'
        with patch.object(agenda_qt, 'call', return_value={'now': [], 'counts': {}}):
            self.assertEqual(agenda_qt.summary(None), ('Nothing running  ·  {open}', 0))
        with patch.object(agenda_qt, 'call', return_value=None):self.assertIsNone(agenda_qt.summary(None))

    def test_her_column_says_now_once_in_every_look(self):
        from tests_integrated.kasandra_window_probe import probe
        for look, _ in presentation_preferences.APPEARANCES:
            out = probe(look, 1366, 768, 'now_line')
            self.assertEqual(out['running'], 'Now: Read the bench readings · 2 next · 1 waiting for you · open · activity', look)      # 0.8.3: 'Now: Now: Read ...'
            self.assertEqual(out['idle'], 'Now: Nothing running · open · activity', look)
            for line in out.values():self.assertEqual(line.count('Now'), 1, (look, line))


if __name__ == '__main__':
    unittest.main()
