"""1.1 B2, Start and the line (PLAN_1.1.md, B2): the Windows key opens Start (apps by kind, recent, power); the line finds and
does everything (apps, files, settings, commands, sums, Ask Kasandra), and every row says what Enter will do.

Acceptance first: the Windows key's binding and its word open Start with the cursor in the line, and close it again; Start
shows the apps by kind from their own desktop entries, the recent files and the leave group's five; the line's rows for an
app, a file, a sum and Ask Kasandra each say what Enter does, and Enter does it. Then the sum's exactness, DOS words with the
Debian word beside, Windows words, operations by name, power through 1.0's leave group, Esc, the slots filled through
register_slot, and that typing alone does nothing. Every app, file and desk here is invented.

Run alone:  python3 -B -m unittest -v tests_integrated.test_start_line
"""
import os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

ROOT = Path(__file__).resolve().parents[1]
AREA = Path(tempfile.mkdtemp(prefix='b2-start-'))
HOME = AREA / 'home'
ENTRIES = {'tern-browser.desktop': ('Tern Browser', 'Web Browser', 'Network;WebBrowser;', 'web;internet;'),
           'harbour-notes.desktop': ('Harbour Notes', 'Text Editor', 'Utility;TextEditor;', 'text;notes;'),
           'gull-sheets.desktop': ('Gull Sheets', 'Spreadsheet', 'Office;Spreadsheet;', 'table;calc;'),
           'plover-paint.desktop': ('Plover Paint', 'Image Editor', 'Graphics;2DGraphics;', 'paint;drawing;')}


def setUpModule():
    (HOME / 'Documents').mkdir(parents=True, exist_ok=True)
    apps = AREA / 'share' / 'applications';apps.mkdir(parents=True, exist_ok=True);(AREA / 'none').mkdir(exist_ok=True)
    for name, (title, generic, cats, words) in ENTRIES.items():
        (apps / name).write_text('[Desktop Entry]\nType=Application\nName=%s\nGenericName=%s\nCategories=%s\nKeywords=%s\nExec=true %%U\n'
                                 % (title, generic, cats, words), encoding='utf-8')
    report = HOME / 'Documents' / 'harbour-survey-report.ods';report.write_bytes(b'invented')
    (AREA / 'share' / 'recently-used.xbel').write_text(
        '<?xml version="1.0"?>\n<xbel version="1.0"><bookmark href="file://%s" modified="2026-11-20T10:00:00Z"/></xbel>\n' % report,
        encoding='utf-8')
    os.environ.update(HOME=str(HOME), XDG_DATA_HOME=str(AREA / 'share'), XDG_DATA_DIRS=str(AREA / 'none'), XDG_CONFIG_HOME=str(AREA / 'config'))


def tearDownModule():
    shutil.rmtree(AREA, ignore_errors=True)


from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMainWindow  # noqa: E402

APP = QApplication.instance() or QApplication([])


def pump(n=8):
    for _ in range(n):APP.processEvents()


class Host(QMainWindow):
    """A stand-in for Graphite's window: what Start reads of it."""

    def __init__(self):
        super().__init__();self.setWindowTitle('Graphite');self.resize(1366, 728);self._closing = False;self.graphite_bar = None
        self.her_column = SimpleNamespace(shown_state='idle');self.statusBar()


def rows_for(text):
    from workbench import line_finder as lf
    return lf.rows(text, lf.Sources(None))


def typed(panel, text):
    panel.line.setText(text);panel.timer.stop();return panel.find()


class Acceptance(unittest.TestCase):

    def tearDown(self):
        for w in QApplication.topLevelWidgets():
            if w.objectName() == 'GraphiteStart':w.close()
        pump()

    def test_the_windows_key_opens_start_with_the_cursor_in_the_line_and_closes_it_again(self):
        tool = ROOT / 'tools' / 'graphite-do'
        with tempfile.TemporaryDirectory() as temp:
            out = subprocess.run([sys.executable, '-B', str(tool), '--write-keys', temp], capture_output=True, text=True, timeout=30)
            self.assertEqual(out.returncode, 0, out.stderr);keys = (Path(temp) / 'keys').read_text()
        for line in ('Super_L :Exec "%s" start' % tool, 'Super_R :Exec "%s" start' % tool, 'Mod4 r :Exec "%s" line' % tool):
            self.assertIn(line + '\n', keys)
        self.assertNotIn('Super_L :Exec "%s" apps' % tool, keys)
        from workbench import windows_keys_qt as wk
        host = Host()
        answer = wk.act(host, 'start');pump()
        panel = host.start_panel
        self.assertEqual(answer, {'ok': True, 'words': 'Start is open.'})
        self.assertTrue(panel.isVisible());self.assertEqual(panel.mode, 'start')
        self.assertIs(APP.focusWidget(), panel.line, 'the cursor is already in the line')
        self.assertFalse(host.isVisible(), 'Start rises over whichever app is in front; Graphite is not brought forward')
        self.assertEqual(wk.act(host, 'start')['words'], 'Start is closed.');pump();self.assertFalse(panel.isVisible())

    def test_start_shows_apps_by_kind_recent_files_and_the_leave_groups_five(self):
        from workbench import start_qt
        host = Host();start_qt.open_start(host);pump();panel = host.start_panel
        headings = [panel.apps.item(i).data(start_qt.ROLE) for i in range(panel.apps.count()) if isinstance(panel.apps.item(i).data(start_qt.ROLE), str)]
        self.assertEqual(headings, ['Accessories', 'Graphics', 'Internet', 'Office'], 'apps by kind, from their own desktop entries')
        names = [r.title for r in panel.app_rows];self.assertEqual(names, ['Harbour Notes', 'Plover Paint', 'Tern Browser', 'Gull Sheets'])
        self.assertTrue(all(r.verb == 'Open' for r in panel.app_rows))
        self.assertEqual([r.title for r in panel.recent_rows], ['harbour-survey-report.ods'])
        self.assertEqual([b.word for b in panel.power_buttons.values()], ['Lock', 'Suspend', 'Log out', 'Restart', 'Shut down'])
        words = ' '.join(l.text() for l in panel.findChildren(start_qt.QLabel)) + ' ' + start_qt.START_TIP
        self.assertIn('Apps', words);self.assertNotIn('Programs', words)

    def test_the_lines_rows_for_an_app_a_file_a_sum_and_ask_kasandra_say_what_enter_does(self):
        from workbench import line_finder as lf
        app = rows_for('tern');self.assertEqual((app[0].kind, app[0].title, app[0].verb), ('app', 'Tern Browser', 'Open'))
        self.assertEqual(app[0].enter_words(), 'Enter: Open Tern Browser')
        found = rows_for('survey');self.assertEqual((found[0].kind, found[0].title, found[0].verb), ('file', 'harbour-survey-report.ods', 'Open'))
        self.assertTrue(found[0].detail.startswith('Recent · ~/Documents'), found[0].detail)
        total = rows_for('12*7');self.assertEqual((total[0].kind, total[0].title, total[0].verb), ('sum', '12 × 7 = 84', 'Calculate'))
        ask = rows_for('what is on the desk today')
        self.assertEqual((ask[0].kind, ask[0].verb), ('ask', 'Ask Kasandra'), 'a request: Ask Kasandra first')
        for text in ('tern', 'survey', '12*7', 'what is on the desk today', 'dir', 'control panel', '/apps.list'):
            for row in rows_for(text):self.assertIn(row.verb, lf.VERBS, (text, row))
            self.assertEqual(rows_for(text)[-1].kind, 'ask', 'Ask Kasandra is always offered: %s' % text)

    def test_enter_does_what_the_chosen_row_says_and_start_leaves(self):
        from workbench import start_qt
        host = Host();start_qt.open_start(host);pump();panel = host.start_panel
        with patch('workbench.apps_qt.open_app', return_value='Started.') as opened:
            typed(panel, 'tern');self.assertIn('Enter: Open Tern Browser', panel.hint.text())
            QTest.keyClick(panel.line, Qt.Key_Return);pump()
        opened.assert_called_once_with(host, 'tern-browser.desktop');self.assertFalse(panel.isVisible())
        start_qt.open_start(host);pump();panel = host.start_panel
        with patch('workbench.foot_line.ask_kasandra', return_value=True) as asked:
            typed(panel, 'what is on the desk today');QTest.keyClick(panel.line, Qt.Key_Return);pump()
        asked.assert_called_once_with(host, 'what is on the desk today')


class TheLine(unittest.TestCase):

    def test_a_sum_is_exact_as_the_one_maths_core_answers_and_enter_puts_it_in_the_line(self):
        from workbench import line_finder as lf, start_qt
        for text, answer in (('1/3 + 1/6', '0.5'), ('0.1+0.2', '0.3'), ('2 x 3.5', '7'), ('= 2^3', '8'), ('(3+4)*2', '14'),
                             ('10/3', '3.333 (exact 10/3)'), ('123456789*1000', '123456789000')):
            self.assertEqual(lf.sum_of(text)[1], answer, text)
        self.assertIsNone(lf.sum_of('42'), 'a number alone is no sum');self.assertIsNone(lf.sum_of('route 66'))
        self.assertEqual(rows_for('= 1/0')[0].verb, 'Edit', 'a sum the core cannot answer is said, and left to edit')
        host = Host();start_qt.open_start(host);pump();panel = host.start_panel
        typed(panel, '10/3');QTest.keyClick(panel.line, Qt.Key_Return);pump()
        self.assertEqual(panel.line.text(), '10/3', 'the exact answer, as a fraction');self.assertEqual(APP.clipboard().text(), '10/3')
        self.assertTrue(panel.isVisible(), 'the sum can go on');panel.close()

    def test_dos_words_run_in_the_terminal_with_the_debian_word_beside_and_format_never_runs(self):
        row = rows_for('dir')[0];self.assertEqual((row.kind, row.verb, row.beside), ('dos', 'Run', 'ls -l'))
        self.assertEqual(rows_for('ipconfig')[0].beside, 'ip -brief address')
        never = rows_for('format c:')[0];self.assertEqual((never.kind, never.verb), ('dos', 'Explain'));self.assertIn('never run', never.title)
        with patch('workbench.shell2.to_console') as console:
            from workbench import start_qt
            start_qt.do(Host(), row)
        console.assert_called_once();self.assertEqual(console.call_args[0][1:], ('shell', 'dir'))

    def test_windows_words_find_their_place_here_with_the_windows_word_beside(self):
        panel = rows_for('control panel')[0];self.assertEqual((panel.kind, panel.title, panel.beside), ('place', 'Settings', 'Control Panel in Windows'))
        notes = rows_for('notepad')[0];self.assertEqual((notes.kind, notes.title, notes.beside), ('app', 'Harbour Notes', 'Notepad in Windows'))
        self.assertEqual(rows_for('cmd')[0].title, 'Terminal')
        registry = rows_for('regedit')[0];self.assertEqual((registry.kind, registry.verb), ('explain', 'Explain'));self.assertIn('no registry', registry.detail)

    def test_operations_by_name_and_the_leads(self):
        op = rows_for('/apps.list')[0];self.assertEqual((op.kind, op.verb, op.target), ('operation', 'Run', '/apps.list'))
        self.assertIn('it reads', op.detail)
        self.assertEqual(rows_for('apps.list')[0].kind, 'operation')
        self.assertEqual([r.kind for r in rows_for('?tern')], ['ask'], '? is for Kasandra alone')
        self.assertEqual(rows_for('$ ls -l')[0].kind, 'terminal')
        self.assertEqual(rows_for('https://example.org')[0].kind, 'address')
        self.assertEqual(rows_for('tern')[-1].kind, 'ask', 'a name found: Ask Kasandra is the last row, chosen')

    def test_typing_alone_does_nothing(self):
        from workbench import start_qt
        host = Host();start_qt.open_start(host);pump();panel = host.start_panel
        with patch('workbench.apps_qt.open_app') as opened, patch('workbench.foot_line.ask_kasandra') as asked, patch('workbench.shell2.to_console') as console:
            for text in ('tern', 'dir', 'what is on today', '12*7'):
                for ch in text:QTest.keyClick(panel.line, ch)
                panel.timer.stop();panel.find();pump();panel.line.clear()
        for fake in (opened, asked, console):fake.assert_not_called()
        self.assertTrue(panel.isVisible());panel.close()


class StartItself(unittest.TestCase):

    def test_power_goes_through_1_0s_leave_group(self):
        from workbench import start_qt
        host = Host()
        with patch('workbench.session_power.run_action', return_value={}) as action, patch('workbench.session_power.run_lock', return_value={}) as lock, \
                patch('workbench.session_power.availability', return_value={k: {'available': k != 'suspend', 'reason': 'not offered here'} for k in start_qt.lf.POWER}):
            start_qt.open_start(host);pump();panel = host.start_panel
            for _ in range(20):
                pump(2)
                if not panel._power_poll.isActive():break
                QTest.qWait(20)
            self.assertEqual(panel.power_buttons['suspend'].reason, 'not offered here');self.assertIn('Unavailable here', panel.power_buttons['suspend'].toolTip())
            panel.power_buttons['restart'].click();pump();QTest.qWait(120);pump()
            action.assert_called_once_with(host, 'restart');self.assertFalse(panel.isVisible())
            start_qt.open_start(host);pump();panel = host.start_panel
            for _ in range(2):QTest.keyClick(panel.line, Qt.Key_Tab)      # the apps, the recent files, the power row
            self.assertEqual(panel.part, 'power');self.assertIn('Enter: Lock', panel.hint.text())
            QTest.keyClick(panel.line, Qt.Key_Return);pump();QTest.qWait(200);pump()
            lock.assert_called_once_with(host)

    def test_esc_closes_start_and_win_e_still_opens_files(self):
        from workbench import start_qt
        host = Host();start_qt.open_start(host);pump();panel = host.start_panel
        QTest.keyClick(panel.line, Qt.Key_Escape);pump();self.assertFalse(panel.isVisible())
        start_qt.open_start(host);pump();panel = host.start_panel
        with patch('workbench.windows_keys_qt.act', return_value={'ok': True}) as act:
            QTest.keyClick(panel.line, Qt.Key_E, Qt.MetaModifier);pump()
        act.assert_called_once_with(host, 'files');self.assertFalse(panel.isVisible())

    def test_start_and_the_line_fill_the_bars_slots_through_register_slot_and_rise_above_it(self):
        from workbench import bar_qt, start_qt
        host = Host();host.show();pump()
        try:
            start_qt.install(host)
            bar = bar_qt.Bar(host);bar.setGeometry(0, 728, 1366, 40);bar.show();host.graphite_bar = bar;pump()
            self.assertIsInstance(bar.slot('start'), start_qt.StartSlot);self.assertIsInstance(bar.slot('line'), start_qt.LineSlot)
            self.assertEqual(bar.slot_errors, {})
            bar.slot('line').click();pump();panel = host.start_panel
            self.assertEqual(panel.mode, 'line');self.assertTrue(panel.isVisible())
            self.assertLess(panel.geometry().bottom(), bar.y(), 'the rows rise above the bar')
            self.assertEqual(panel.x(), bar.slot('line').mapToGlobal(bar.slot('line').rect().topLeft()).x())
            panel.close();pump()
            bar.slot('start').click();pump();self.assertEqual(host.start_panel.mode, 'start');self.assertLess(host.start_panel.geometry().bottom(), bar.y())
            host.start_panel.close();bar.close()
        finally:
            bar_qt.register_slot('start', None);bar_qt.register_slot('line', None);host.close()


if __name__ == '__main__':
    unittest.main()
