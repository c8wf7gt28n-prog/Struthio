"""0.8.4: a control is lit only when a press would do something.

The rule is the record's. Its case here is the Paper script for the quieter words, which is off in every look
(shell2.SCRIPT_ON). Two controls still offered it in 0.8.3, and each changed a stored value and nothing on the screen:
the menu toggle "Pleasantries in script", found on 14 November 2026 when the window checks were measured (it stood ticked
in the menus, last under Tools, Engineering, More), and the setting it wrote, appearance.cursive, offered in Settings as
"Script for incidental text". The toggle went first; the setting followed in the release pass (the owner's default,
19 November, in the build record).

The setting is retired the way the code base retires one: its definition leaves the registry (and the recorded registry,
tools/record_registry.py), the desktop's readback and the Session's adapters let it go, and a journal row of it is shown in
the history, never undone (ledger_control.history). A Session file or a journal that still holds the old value loads
without a word and without an error, and the value never comes back on screen.

The real window, offscreen, on a new profile and workspace for each test; no provider request, worker launch, job, or
session or power call.
"""
import json
import os
import platform
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from workbench.session import Session

TOGGLE = 'Pleasantries in script'
KEY = 'appearance.cursive'      # the retired setting
LABEL = 'Script for incidental text'      # its words in Settings until 0.8.4


def menu_words(menu, seen=None):
    """Every entry's words under a menu, through its submenus (a menu met twice is walked once)."""
    seen = set() if seen is None else seen;out = []
    if id(menu) in seen:return out
    seen.add(id(menu))
    for action in menu.actions():
        out.append(action.text().replace('&', ''))
        if action.menu() is not None:out += menu_words(action.menu(), seen)
    return out


def tree_words(tree):
    """Every column's words of every row of a tree, through its branches."""
    out = []
    def visit(item):
        out.extend(item.text(column) for column in range(item.columnCount()))
        for index in range(item.childCount()):visit(item.child(index))
    for index in range(tree.topLevelItemCount()):visit(tree.topLevelItem(index))
    return out


def shown_words(window):
    """The words of every widget shown in the window: labels, buttons, fields, passages, lists and trees."""
    from PySide6.QtWidgets import QAbstractButton, QLabel, QLineEdit, QListWidget, QPlainTextEdit, QTextEdit, QTreeWidget
    out = []
    for widget in window.findChildren(QLabel) + window.findChildren(QAbstractButton) + window.findChildren(QLineEdit):
        if widget.isVisible():out.append(widget.text())
    for widget in window.findChildren(QPlainTextEdit) + window.findChildren(QTextEdit):
        if widget.isVisible():out.append(widget.toPlainText())
    for widget in window.findChildren(QTreeWidget):
        if widget.isVisible():out += tree_words(widget)
    for widget in window.findChildren(QListWidget):
        if widget.isVisible():out += [widget.item(index).text() for index in range(widget.count())]
    return out


class TheScriptControls(unittest.TestCase):
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
        # "Without a word": the message boxes a start could raise are held and counted (none may be raised)
        self.said = []
        for name in ('warning', 'critical', 'information'):
            hold = patch.object(QMessageBox, name, return_value=QMessageBox.Ok);self.said.append(hold.start());self.addCleanup(hold.stop)
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

    def test_no_menu_and_no_action_offers_the_script_toggle(self):
        from PySide6.QtGui import QAction
        w = self.start()
        in_menus = [words for menu in w.menu_groups.values() for words in menu_words(menu)]
        self.assertGreater(len(in_menus), 40, 'the menus were read');self.assertNotIn(TOGGLE, in_menus)
        self.assertNotIn(TOGGLE, [action.text().replace('&', '') for action in w.findChildren(QAction)])      # 0.8.3: there, ticked, under Engineering ▸ More
        self.assertFalse(hasattr(w.shell2, 'script_action'))

    def test_settings_does_not_offer_the_script_setting(self):
        from workbench import ledger_control, settings_registry
        from workbench.engineering_kernel import operator
        self.assertNotIn(KEY, settings_registry.BY_KEY);self.assertNotIn(KEY, [spec['key'] for spec in settings_registry.SPECS])
        self.assertNotIn('setting:' + KEY, [node['id'] for node in settings_registry.nodes()])
        w = self.start();kernel = w.ledger_bridge.kernel
        tab = w.ledger_bridge.show_settings();self.settle(w)
        self.assertNotIn(KEY, [row['key'] for row in ledger_control.settings(kernel)['settings']])
        nav = w.settings_navigator
        self.assertIn('setting:appearance.writing_marker', nav.items, 'the settings tree was read');self.assertNotIn('setting:' + KEY, nav.items)
        self.assertIn('Writing marker', tree_words(nav.tree));self.assertNotIn(LABEL, tree_words(nav.tree))
        self.assertNotEqual(tab.key, KEY);self.assertFalse(any(LABEL in words or KEY in words for words in shown_words(w)))
        # Nor does any door set it: the shared Set refuses it as an unknown setting, and the Session file is left as it was
        w.session.save();before = self.path.read_bytes()
        response = kernel.dispatch('ledger.settings.set', dict(key=KEY, value=False), operator())
        self.assertFalse(response['ok'], response);self.assertEqual(self.path.read_bytes(), before)
        self.assertNotIn('cursive', json.loads(before))
        # The desktop's readback carries no value for it
        w.ledger_bridge.publish_settings_readback()
        with kernel.db() as db:receipt = json.loads(db.execute('SELECT value FROM settings WHERE key=?', ('ledger.settings_runtime.' + w.ledger_bridge.desktop_id,)).fetchone()[0])
        self.assertIn('appearance.writing_marker', receipt['values']);self.assertNotIn(KEY, receipt['values'])

    def test_a_session_file_and_journal_that_hold_the_old_value_load_without_a_word_and_it_stays_off_screen(self):
        from PySide6.QtCore import Qt
        from workbench import ledger_control
        from workbench.engineering_kernel import operator
        # A profile as an earlier Graphite left it: the script switched off, and Settings left open on that setting
        session = Session(self.path, self.root);session.save();data = json.loads(self.path.read_text(encoding='utf-8'))
        data.update(cursive=False, settings_navigation=dict(mode='settings', selected='setting:' + KEY, expanded=['settings:ledger', 'settings:ledger:appearance']))
        self.path.write_text(json.dumps(data), encoding='utf-8')
        loaded = Session(self.path, self.root);self.assertNotIn('cursive', loaded.state)
        self.assertNotEqual(loaded.state.get('settings_navigation', {}).get('selected'), 'setting:' + KEY)
        w = self.start();kernel = w.ledger_bridge.kernel
        self.assertNotIn('cursive', w.session.state);self.assertNotEqual(getattr(w.ledger_bridge.show_settings(), 'key', None), KEY)
        # ... and a journal row of it, as Settings recorded a change of it before 0.8.4
        change = dict(id='retiredscript1', key=KEY, before=True, after=False, actor='desktop-owner', at=time.time(), undone=False, scope='session_profile')
        with kernel.db() as db:db.execute('INSERT INTO settings VALUES(?,?)', ('ledger.change.' + change['id'], json.dumps(change)))
        w.ledger_bridge.sync_profile(force=True);tab = w.ledger_bridge.show_settings(key='appearance.writing_marker');self.settle(w)
        self.assertEqual(tab.key, 'appearance.writing_marker')
        self.assertNotIn(KEY, [row.data(0, Qt.UserRole)['key'] for row in (tab.history.topLevelItem(i) for i in range(tab.history.topLevelItemCount()))])
        self.assertFalse(any(LABEL in words or KEY in words for words in shown_words(w)), 'the retired setting is nowhere on screen')
        # The history shows the row and never undoes it; the old value does not come back
        row = next(r for r in ledger_control.history(kernel)['changes'] if r['id'] == change['id'])
        self.assertTrue(row['orphaned']);self.assertFalse(row['can_undo'])
        self.assertFalse(kernel.dispatch('ledger.settings.undo', {'id': change['id']}, operator())['ok'])
        self.assertFalse(kernel.dispatch('ledger.settings.history', {'key': KEY}, operator())['ok'], 'asked by its key, it is an unknown setting')
        w.session.save();self.assertNotIn('cursive', json.loads(self.path.read_text(encoding='utf-8')), 'the next save leaves the old field out')
        self.assertNotIn('cursive', w.session.state)
        self.assertEqual([box.call_count for box in self.said], [0, 0, 0], 'no message box was raised')


class TheScriptSwitch(unittest.TestCase):
    """The script has one switch, shell2.SCRIPT_ON, off in every look. A pleasantry follows it and never moves it: until
    0.8.4 it asked shell2.cursive_on, which switched the script off as it answered, so a pleasantry drawn while the switch
    was on (as the drawing tests turn it on) left it off for every word drawn after."""
    def test_a_pleasantry_follows_the_switch_and_leaves_it_where_it_was(self):
        from types import SimpleNamespace
        from PySide6.QtGui import QFontDatabase
        from PySide6.QtWidgets import QApplication, QLabel
        from workbench import shell2
        QApplication.instance() or QApplication([])
        QFontDatabase.addApplicationFont(str(Path(__file__).resolve().parents[1] / 'branding/fonts/script/Parisienne-Regular.ttf'))
        self.assertIn(shell2.SCRIPT, QFontDatabase.families(), 'the script face is shipped')
        saved = shell2.SCRIPT_ON[0];self.addCleanup(shell2.SCRIPT_ON.__setitem__, 0, saved)
        host = SimpleNamespace(session=SimpleNamespace(state={'cursive': True}))      # a value an earlier Graphite stored moves nothing
        for on in (True, False, True):
            shell2.SCRIPT_ON[0] = on;label = QLabel('Good evening.');shell2.pleasantry(label, host, 26)
            self.assertIs(shell2.SCRIPT_ON[0], on, 'a pleasantry leaves the switch where it was')
            self.assertEqual(shell2.SCRIPT in label.styleSheet(), on, 'in the script only while the switch is on')


if __name__ == '__main__':
    unittest.main()
