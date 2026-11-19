"""0.8.4: a control is lit only when a press would do something.

The rule is the record's. Its case here is the menu toggle "Pleasantries in script", found on 14 November 2026 when the
window checks were measured. It stood ticked in the menus (last under Tools, Engineering, More) and wrote the setting
appearance.cursive; but the script it named is off in every look (shell2.cursive_on answers no, whatever is stored), so a
press changed a stored value and nothing on the screen. The toggle and its menu entry are gone.

The setting itself stays where it was, in the registry and in the session file: a value saved by an earlier Graphite is read
as before, Settings can still change it, and neither changes anything on the screen.

The real window, offscreen, on a new profile and workspace for each test; no provider request, worker launch, job, or
session or power call.
"""
import os
import platform
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from workbench.session import Session

TOGGLE = 'Pleasantries in script'


def menu_words(menu, seen=None):
    """Every entry's words under a menu, through its submenus (a menu met twice is walked once)."""
    seen = set() if seen is None else seen;out = []
    if id(menu) in seen:return out
    seen.add(id(menu))
    for action in menu.actions():
        out.append(action.text().replace('&', ''))
        if action.menu() is not None:out += menu_words(action.menu(), seen)
    return out


class TheScriptToggle(unittest.TestCase):
    def setUp(self):
        from PySide6.QtWidgets import QMessageBox
        from workbench import clip, locations, session_power
        from workbench.engineering_kernel import Kernel
        from workbench.qt_app import make_app
        temporary = tempfile.TemporaryDirectory(prefix='graphite-084-lit-');self.addCleanup(temporary.cleanup);run = Path(temporary.name)
        env = patch.dict(os.environ, {'ARC_LEDGER_EMBEDDED': '1', 'ARC_LEDGER_DISABLE_BOOK_WATCHER': '1', 'ARC1_WORKBENCH_CONFIG_HOME': str(run / 'profile'),
                                      'ARC_LEDGER_CONCERN': str(run / 'Concern')})
        env.start();self.addCleanup(env.stop);os.environ.pop('ARC_LEDGER_XSESSION', None)
        for hold in (patch.object(clip, '_request', side_effect=AssertionError('No provider request')), patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')),
                     patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')), patch.object(session_power, 'system', side_effect=OSError('no login session (held)')),
                     patch.object(QMessageBox, 'question', return_value=QMessageBox.No)):
            hold.start();self.addCleanup(hold.stop)
        self.app = make_app([]);self.root = locations.office(run / 'workspace');self.path = run / 'profile' / 'session.json'

    def settle(self, w, ms=30):
        from PySide6.QtTest import QTest
        for name in ('agenda_runner', 'study_idle', 'ledger_bridge'):
            timer = getattr(getattr(w, name, None), 'timer', None)
            if timer is not None:timer.stop()
        try:w.type_bar.hatch.lifecycle.timer.stop()
        except AttributeError:pass
        for _ in range(3):self.app.processEvents();QTest.qWait(ms)

    def start(self):
        from workbench.qt_app import WorkbenchWindow
        w = WorkbenchWindow(self.root, Session(self.path, self.root), restore=False);platform.processor()
        w.resize(1366, 768);w.show();self.settle(w)
        def close():
            w.close();self.settle(w);w.deleteLater();self.app.processEvents()
        self.addCleanup(close);return w

    def row(self, w):
        from workbench import ledger_control
        return next(r for r in ledger_control.settings(w.ledger_bridge.kernel)['settings'] if r['key'] == 'appearance.cursive')

    def test_no_menu_and_no_action_offers_the_script_toggle(self):
        from PySide6.QtGui import QAction
        w = self.start()
        in_menus = [words for menu in w.menu_groups.values() for words in menu_words(menu)]
        self.assertGreater(len(in_menus), 40, 'the menus were read');self.assertNotIn(TOGGLE, in_menus)
        self.assertNotIn(TOGGLE, [action.text().replace('&', '') for action in w.findChildren(QAction)])      # 0.8.3: there, ticked, under Engineering ▸ More
        self.assertFalse(hasattr(w.shell2, 'script_action'))

    def test_a_saved_choice_is_read_as_before_and_changes_nothing_on_screen(self):
        from workbench import shell2
        from workbench.engineering_kernel import operator
        session = Session(self.path, self.root);session.state['cursive'] = False;session.save()      # as an earlier Graphite left it, the toggle off
        w = self.start();row = self.row(w)
        self.assertIs(w.session.state['cursive'], False);self.assertIs(row['stored'], False)
        self.assertIs(shell2.cursive_on(w), False);self.assertIs(shell2.SCRIPT_ON[0], False)
        # Settings still changes the stored value, and the window follows the change without the toggle it used to tick
        response = w.ledger_bridge.kernel.dispatch('ledger.settings.set', dict(key=row['key'], value=True, expected_revision=row['revision']), operator())
        self.assertTrue(response['ok'], response);w.ledger_bridge.sync_profile(force=True);self.settle(w)
        self.assertIs(self.row(w)['stored'], True);self.assertIs(Session(self.path, self.root).state['cursive'], True)
        self.assertIs(shell2.cursive_on(w), False);self.assertIs(shell2.SCRIPT_ON[0], False, 'the script is off in every look, whatever is stored')


if __name__ == '__main__':
    unittest.main()
