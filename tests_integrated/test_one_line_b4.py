"""1.1 B4, one line, a drop-down Terminal and Command… (PLAN_1.1.md, B4).

Acceptance first: once the bar stands there is no foot in Graphite's window and everything it did is reachable, each in one
place (FOOT_MOVED); the Terminal drops from the top edge (the top 40 %, full width), runs a line and DOS words, keeps Esc for
the shell and goes back up on the same key; Command… on a file shows its line (above Properties in the right-click), with
Copy and Put it in the line; Win+K and Pause from an app open her panel and press HALT without bringing Graphite forward.
Then: the band, graphite-do's words and keys, the foot staying without the bar, the line's rows, the Log's filter, the
meters in the tray.

Offscreen on the Everyday Home (invented: everyday_demo), with the bar made and marked standing by hand (under Xvfb it stands
for real: the builder's smoke). Run alone:  python3 -B -m unittest -v tests_integrated.test_one_line_b4
"""
import importlib.machinery, importlib.util, os, tempfile, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

ROOT = Path(__file__).resolve().parents[1]


class OneLine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='b4-everyday-');base = Path(cls.temp.name)
        from workbench import everyday_demo
        everyday_demo.build(base);cls.home = base / 'home'
        cls.env = patch.dict(os.environ, {'HOME': str(cls.home), 'XDG_CONFIG_HOME': str(cls.home / '.config'), 'GRAPHITE_BAR': '1',
                                          'XDG_CACHE_HOME': str(base / 'cache'), 'XDG_DATA_HOME': str(cls.home / '.local/share')})
        cls.env.start()
        cls.hub = patch('workbench.windows_strip_qt.hub');cls.hub.start()
        from tests_integrated.test_desk_acts import build_window
        cls.store = {};build_window(cls.store, 'b4-window-');cls.w = w = cls.store['w']
        cls.settle(300)
        from workbench import bar_qt, foot_fold_qt as ff
        cls.ff = ff;cls.bq = bar_qt
        cls.before = dict(dock=w.type_dock.isVisible(), folded=ff.folded(w), refused=ff.fold(w))      # no bar yet: the foot stays
        bar = cls.bar = bar_qt.Bar(w);bar.standing = True;bar.setGeometry(0, 1160, 1920, 40);bar.show()
        w.graphite_bar = bar;w.system_dock = bar;cls.settle(200)
        cls.folded_now = ff.fold(w);cls.settle(300)

    @classmethod
    def tearDownClass(cls):
        from tests_integrated.test_desk_acts import close_window
        from workbench import line_finder
        try:
            term = getattr(cls.w, 'drop_terminal', None)
            if term is not None:term.stop_shell();term.hide()
            cls.bar.hide();cls.bar.deleteLater();cls.w.graphite_bar = None
            cls.bq.register_slot('tray', None);line_finder.MORE[:] = []
            close_window(cls.store)
        finally:
            cls.hub.stop();cls.env.stop();cls.temp.cleanup()

    @classmethod
    def settle(cls, ms=120):
        from tests_integrated.test_desk_acts import settle
        settle(cls.store, ms)

    def wait(self, check, seconds=15):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if check():return True
            self.settle(50)
        return check()

    # ---- acceptance --------------------------------------------------------------------------------------------------------------
    def test_a_no_foot_in_the_window_once_the_bar_stands(self):
        w = self.w
        self.assertTrue(self.before['dock'] and not self.before['folded'] and not self.before['refused'], 'before the bar: 1.0\'s foot')
        self.assertTrue(self.folded_now and w.foot_folded)
        self.assertFalse(w.type_dock.isVisible(), 'no foot')
        w.type_dock.show();self.settle(120)
        self.assertFalse(w.type_dock.isVisible(), 'a reset that shows the foot again is undone')
        olds = ' '.join(old for old, _ in self.ff.FOOT_MOVED)
        for job in ('Line', 'Search', 'Web', 'Terminal', 'Log', 'meters', 'Ask Kasandra', 'messages'):
            self.assertIn(job, olds, 'the table says where %s went' % job)

    def test_b_everything_the_foot_did_is_reachable_each_in_one_place(self):
        w = self.w
        with patch('workbench.foot_fold_qt.put_in_line', return_value=True) as put:
            w.a_talk['line'].trigger();w.a_talk['find'].trigger();w.shell2.search();w.a_run_operation.trigger()
        self.assertEqual([c.args[1] for c in put.call_args_list], ['', '', '', '/'], "Line, Search, Ctrl+K and an operation open the bar's line")
        w.a_talk['shell'].trigger();self.settle(80)
        term = w.drop_terminal;self.assertTrue(term.opened, 'Alt+5 drops the Terminal');term.leave();self.settle(300)
        w.a_talk['log'].trigger();self.settle(80)
        self.assertEqual((w.console.mode, w.console.size_level > 0), ('log', True), 'Alt+6 opens the Log in the working area')
        self.assertIsNotNone(getattr(w.log_view, 'b4_line', None), 'the Log has its own Filter line')
        from workbench.head_menus import rows
        menus = {word.text(): rows(word.menu()) for word in w.shell2.top.menu_words()}
        self.assertEqual([words for d, words, _ in menus['View'] if words == 'Log'], ['Log'], 'Log is a row of View')
        writing = [words for d, words, _ in menus['Tools'] if d >= 2 and words in ('Line', 'Terminal', 'Search', 'Log')]
        self.assertNotIn('Log', writing, 'one home: View')
        tray = self.bar.slot('tray');self.assertIsInstance(tray, self.ff.MetersTray, 'the meters are in the tray')
        self.assertIsNotNone(w.type_bar.monitors, 'the foot\'s meters object stays for its callers, out of sight')
        self.assertFalse(w.type_bar.monitors.isVisible(), 'the meters are in one place: the tray')

    def test_c_the_terminal_drops_runs_dos_words_keeps_esc_and_goes_back_up(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from workbench import drop_terminal_qt as dt
        w = self.w;term = dt.terminal(w)
        with patch('workbench.drop_terminal_qt.reduce_motion', return_value=True):
            answer = dt.toggle(w);self.settle(60)
            self.assertTrue(answer['ok'] and term.opened and term.isVisible())
            g = term.geometry();screen = term.screen_rect()
            self.assertEqual((g.x(), g.y(), g.width()), (screen.x(), screen.y(), screen.width()), 'the top edge, the whole width')
            self.assertEqual(g.height(), max(dt.LEAST, round(screen.height() * dt.SHARE)), '40 % of the screen')
            term.run('echo hello-from-the-drop');self.assertTrue(self.wait(lambda: term.process is None and 'hello-from-the-drop' in term.output.toPlainText()))
            term.run('dir');self.assertTrue(self.wait(lambda: term.process is None))
            self.assertIn('ls', term.output.toPlainText(), 'DOS words: the Debian command is shown')
            term.prompt.setText('half typed');QTest.keyClick(term.prompt, Qt.Key_Escape);self.settle(30)
            self.assertEqual(term.prompt.text(), '');self.assertTrue(term.opened, 'Esc is the shell\'s: it never closes the Terminal')
            dt.toggle(w);self.settle(60);self.assertFalse(term.opened or term.isVisible(), 'the same key puts it away')
            dt.toggle(w);self.settle(30);term.run('exit');self.settle(60)
            self.assertFalse(term.opened, 'exit puts it away too')
        dt.toggle(w);self.settle(40)
        self.assertEqual(term.anim.duration(), dt.SLIDE_MS, 'it slides, 200 ms, when motion is not reduced')
        self.assertTrue(self.wait(lambda: term.pos().y() == term.screen_rect().y()))
        dt.toggle(w);self.assertTrue(self.wait(lambda: not term.isVisible()))

    def test_d_command_on_a_file_shows_its_line_above_properties(self):
        from workbench import command_card_qt as cc
        w = self.w;docs = self.home / 'Documents';docs.mkdir(exist_ok=True)
        note = docs / 'shopping list.txt';note.write_text('eggs\nflour\n', encoding='utf-8')
        app = SimpleNamespace(exec='notespad --new-window %f', kind='desktop', name='Notes Pad', icon='', path='', terminal=False, id='notespad.desktop')
        with patch('workbench.app_files.choose', return_value=('app', app, None, 'Notes Pad', '')):
            lines = cc.lines_for(note)
            card = cc.show(w, note)
        self.assertEqual(lines[0]['title'], 'What Open runs')
        self.assertEqual(lines[0]['line'], "notespad --new-window '%s'" % note, 'the exact command Open starts, the file in it')
        self.assertEqual(lines[1]['line'], '@files:"~/Documents/shopping list.txt"', 'the Graphite line it is')
        card.copy(lines[0]['line']);from PySide6.QtWidgets import QApplication
        self.assertEqual(QApplication.clipboard().text(), lines[0]['line'], 'Copy')
        with patch('workbench.foot_fold_qt.put_in_line', return_value=True) as put:
            card.put(lines[0]['line'])
        put.assert_called_once_with(w, lines[0]['line']);self.assertFalse(card.isVisible(), 'Put it in the line: the card goes')
        folder = cc.lines_for(docs);self.assertEqual([r['line'] for r in folder], ['@files:~/Documents', "cd %s" % docs])
        ex = w.explorer;ex.show(str(docs));self.settle(200)
        view = ex.page.view_widget()
        item = next(view.topLevelItem(i) for i in range(view.topLevelItemCount()) if view.topLevelItem(i).text(0).startswith('shopping'))
        point = view.visualItemRect(item).center()
        from PySide6.QtWidgets import QMenu

        class Shown(QMenu):      # the right-click as it would be shown, without waiting for a press
            def exec(self, *args, **kw):return None
        with patch('workbench.explorer_qt.QMenu', Shown):
            menu = ex.menu_at(view, point)
        words = [a.text().split('\t')[0].split(' (')[0] for a in menu.actions() if not a.isSeparator()]      # a key is printed after a row's words
        self.assertEqual(words[-2:], ['Command…', 'Properties'], 'Command… above Properties')

    def test_e_win_k_and_pause_from_an_app(self):
        from workbench import windows_keys_qt as wk
        w = self.w;ctl = w.kas_bar
        with patch.object(wk, 'bring') as bring, patch.object(ctl, 'toggle', return_value=QRectStandIn()) as toggle, \
                patch.object(ctl, 'panel_open', return_value=True), patch.object(ctl, 'pause_key', return_value=True) as pause:
            kas = wk.act(w, 'kas');halt = wk.act(w, 'halt');drop = wk.act(w, 'terminal')
        self.assertEqual((kas['words'], halt['words']), ('Her panel is open.', 'HALT is pressed: all of her work stops.'))
        toggle.assert_called_once_with();pause.assert_called_once_with()
        self.assertFalse(bring.called, 'Graphite is not brought forward')
        self.assertTrue(drop['ok']);w.drop_terminal.leave();self.settle(300)
        with patch.object(ctl, 'pause_key', return_value=False):
            self.assertIn('RESUME is a press', wk.act(w, 'halt')['words'], 'Pause never presses RESUME')

    # ---- the parts ---------------------------------------------------------------------------------------------------------------
    def test_band_is_the_top_forty_percent(self):
        from workbench.drop_terminal_qt import band
        self.assertEqual(band(0, 0, 1920, 1200), ((0, 0, 1920, 480), (0, -480, 1920, 480)))
        self.assertEqual(band(0, 0, 1366, 768)[0], (0, 0, 1366, 307))
        self.assertEqual(band(0, 0, 800, 300)[0][3], 160, 'never shorter than a few lines')

    def test_graphite_do_knows_terminal_kas_and_halt_and_their_keys(self):
        from workbench import windows_keys_qt as wk
        tool = ROOT / 'tools' / 'graphite-do'
        loader = importlib.machinery.SourceFileLoader('graphite_do_b4', str(tool));spec = importlib.util.spec_from_loader(loader.name, loader)
        mod = importlib.util.module_from_spec(spec);loader.exec_module(mod)
        self.assertEqual(tuple(mod.VERBS), tuple(wk.VERBS), 'the tool and the door know the same words')
        with tempfile.TemporaryDirectory() as temp:      # what --write-keys does (no process: the window's holds forbid one)
            mod.write_keys(temp);keys = (Path(temp) / 'keys').read_text()
        for line in ('Mod4 grave :Exec "%s" terminal', 'Control Mod1 t :Exec "%s" terminal', 'Mod4 k :Exec "%s" kas', 'Pause :Exec "%s" halt'):
            self.assertIn(line % tool + '\n', keys)

    def test_without_the_bar_the_foot_stays_and_graphite_foot_keeps_it(self):
        self.assertTrue(self.ff.wanted({}));self.assertFalse(self.ff.wanted({'GRAPHITE_FOOT': '1'}))
        host = SimpleNamespace(type_dock=object(), graphite_bar=None)
        self.assertFalse(self.ff.fold(host), 'no bar: nothing folds')

    def test_the_line_offers_search_inside_files_and_the_web(self):
        from workbench import line_finder as lf
        rows = lf.more_rows('march invoices')
        self.assertEqual([r.title for r in rows], ['Search inside files for “march invoices”', 'Search the web for “march invoices”'])
        self.assertTrue(all(r.verb == 'Open' and callable(r.target) for r in rows), 'each says what Enter does')
        self.assertEqual([r.title for r in lf.more_rows('www.example.org')], ['Search inside files for “www.example.org”'], 'an address is its own Open row')
        with patch('workbench.foot_fold_qt.search_web', return_value=True) as web:rows[1].target()
        web.assert_called_once_with(self.w, 'march invoices')
        saved = list(lf.MORE);lf.MORE[:] = []
        try:self.assertEqual(lf.more_rows('march invoices'), [], 'no rows of the fold where the foot stands')
        finally:lf.MORE[:] = saved

    def test_the_log_filters_from_its_own_line(self):
        w = self.w;line = self.ff.log_line(w);view = w.log_view
        if view.stream != 'events':view.choose('events', remember=False, read=False)
        line.setText('saved');line.returnPressed.emit();self.settle(60)
        self.assertEqual(view.filters['events'], 'saved')
        line.setText('');line.returnPressed.emit()

    def test_the_meters_are_one_tray_item_whose_rows_are_the_doors(self):
        w = self.w;item = self.ff.meters_item(w);self.assertIsNotNone(item)      # 1.1 B5: the Quick Settings button
        read = self.ff.readings(w);self.assertEqual(tuple(read), self.ff.METER_KEYS)
        item.show_words();self.assertIn('Meters: CPU', item.toolTip())
        fly = item.tray.open_panel();self.settle(40)
        rows = fly.sections['meters'].rows;self.assertEqual(list(rows), list(self.ff.METER_KEYS))
        with patch('workbench.meter_cards.open_card', return_value=None) as card:
            rows['RAM'].click();self.settle(40)
        card.assert_called_once_with(w, item, 'RAM')
        with patch('workbench.meter_cards.open_card', return_value=None) as card:
            w.shell2.top.pulse.open_card('CPU')
        card.assert_called_once_with(w, item, 'CPU')      # Ctrl+Alt+Del's card (graphite-do tasks) opens above Quick Settings


class QRectStandIn:
    """What her controller's toggle answers when her panel slides in (a rect)."""


if __name__ == '__main__':
    unittest.main()
