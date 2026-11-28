"""1.1 K0, the frame (PLAN_1.1.md, K0; DESIGN_DIRECTION_1.1.md sections 2 and 4).

Acceptance first, on the Everyday Home (invented: everyday_demo): the head reads File, Edit, View, Go, Tools, Help; every row
the eight 1.0 menus carried is still on a head menu, with its key beside it; Kas's rules and the stop keep their rows and HALT
and Apps stay in the head; the details pane is off, comes with Alt+P at the right of the centre, and shows a file (List,
Icons) and a board tile with their preview, facts and connections; the chrome at 1920x1200 is about 116 px. Then the tokens
and the tables without a window.

Run alone:  python3 -B -m unittest -v tests_integrated.test_frame_k0
"""
import os, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

HEAD = ['File', 'Edit', 'View', 'Go', 'Tools', 'Help']
# Every row of the eight 1.0 menus (Work, Revise, Tools, Arrange, Commands, Rules, Properties, Guide), as 1.0 showed them.
ROWS_1_0 = {
    'Work': ['New File…', 'New Idea…', 'New Project…', 'Open…', 'Open in Universal Viewer…', 'Find a File…', 'Open Recent', 'Receive Files…',
             'Import (Ingress)…', 'Export (Egress)…', 'Work on a Copy of a File…', 'Save', 'Save All', 'Close', 'Recover Unsaved Work…',
             'Lock', 'Suspend', 'Log out', 'Restart', 'Shut down', 'Exit Graphite'],
    'Revise': ['Undo', 'Redo', 'Cut', 'Copy', 'Paste', 'Select All', 'Find…', 'Find Next', 'Replace…', 'Go to Line…'],
    'Arrange': ['Today', 'Field', 'Files', 'Library', 'Project Desk', 'Changes', 'Continuing work', 'Exchange & deployment', "Graphite's Agenda",
                'Kasandra', 'Console', 'Cabinet', 'Refresh Machine View', 'Full Screen', 'Reading and Layout…', 'Appearance', 'Larger prose',
                'Smaller prose', 'Word Wrap', 'Split Editor / Close Split', 'Pin / Unpin workspace', 'Reopen deferred tabs', 'Reset Window Layout'],
    'Tools': ['Explore capabilities…', 'Inquiries…', 'Algorithm & Theory Atlas…', 'Tool Atlas…', 'A Utility on Copies…', 'System Check',
              'STOP / KILL all Graphite operations…', 'Engineering'],
    'Commands': ['Graphite Commands…', 'Run an operation…', 'Chain Menu', 'Constructed chain', 'Writing Line', 'Command Palette…', 'Favorite commands'],
    'Rules': ['Graphite Settings…', 'Desk artwork', 'Buttons', "Kasandra's hand", 'Show keys', 'DOS words', "The bin's name"],
    'Properties': ['Inspector', 'This Computer…', 'Pills and Paired Computers…'],
    'Guide': ['Getting Started', "What's New in", 'The Living Desktop', 'Kasandra, the Ghost in the Shell', 'Your First Evening with 1.0',
              "An Evening with Kas's Mind", 'Try Rail Demo', 'Try Home Demo', 'Keyboard Shortcuts', 'Installation Guide', 'The Orange Book',
              'About Graphite'],
}
WHERE = {'Work': ('File',), 'Revise': ('Edit',), 'Arrange': ('Go', 'View'), 'Tools': ('Tools',), 'Commands': ('Tools',),
         'Rules': ('Tools', 'View'), 'Properties': ('View', 'Tools'), 'Guide': ('Help',)}      # head_menus.MOVED
KEYS = {('File', 'Open…'): 'Ctrl+O', ('Edit', 'Undo'): 'Ctrl+Z', ('Go', 'Today'): 'Ctrl+Alt+1', ('Go', 'Field'): 'F9',
        ('View', 'Full Screen'): 'F11', ('View', 'Details pane'): 'Alt+P', ('Tools', 'Graphite Settings…'): 'Ctrl+,',
        ('Tools', 'STOP / KILL all Graphite operations…'): 'Ctrl+Shift+F12', ('Help', 'Keyboard Shortcuts'): 'F1'}


class Window(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='k0-everyday-');base = Path(cls.temp.name)
        from workbench import everyday_demo
        everyday_demo.build(base);cls.home = base / 'home'
        cls.env = patch.dict(os.environ, {'HOME': str(cls.home), 'XDG_CONFIG_HOME': str(cls.home / '.config'),
                                          'XDG_CACHE_HOME': str(base / 'cache'), 'XDG_DATA_HOME': str(cls.home / '.local/share')})
        cls.env.start()
        from tests_integrated.test_desk_acts import build_window
        cls.store = {};build_window(cls.store, 'k0-window-');cls.w = cls.store['w'];cls.ex = cls.w.explorer
        cls.settle(400)

    @classmethod
    def tearDownClass(cls):
        from tests_integrated.test_desk_acts import close_window
        try:close_window(cls.store)
        finally:
            cls.env.stop();cls.temp.cleanup()

    @classmethod
    def settle(cls, ms=120):
        from tests_integrated.test_desk_acts import settle
        settle(cls.store, ms)

    def wait(self, check, seconds=20):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if check():return True
            self.settle(60)
        return check()

    def head_rows(self):
        from workbench.head_menus import rows
        return {word.text(): rows(word.menu()) for word in self.w.shell2.top.menu_words()}

    def details(self, on):
        a = self.w.a_details
        if a.isChecked() != on:a.trigger()
        pane = getattr(self.w, 'details_pane', None)
        self.assertTrue(self.wait(lambda: (pane or self.w.details_pane).open_width == (320 if on else 0)), 'the pane finished its slide')
        self.settle(150)
        return self.w.details_pane

    # ---- acceptance --------------------------------------------------------------------------------------------------------
    def test_a_the_head_reads_file_edit_view_go_tools_help(self):
        top = self.w.shell2.top;words = top.menu_words()
        self.assertEqual([w.text() for w in words], HEAD)
        self.assertTrue(all(w.isVisible() for w in words), 'all six in the open at 1920x1200')
        self.assertEqual(top.height(), 32, 'the head is 32 px')
        self.assertEqual([self.w.command_menus[k].text() for k in HEAD], HEAD, 'the old ribbon headings say the same')

    def test_b_nothing_the_eight_menus_carried_is_lost(self):
        head = self.head_rows()

        def shown(menu):      # the rows in sight: Engineering (and its More) is out of sight without a project
            out, hidden = set(), None
            for depth, words, _ in head[menu]:
                if hidden is not None and depth > hidden:continue
                hidden = depth if words == 'Engineering' else None
                out.add(words)
            return out
        for menu, rows in ROWS_1_0.items():
            found = set().union(*(shown(m) for m in WHERE[menu]))
            for row in rows:
                ok = row in found or any(f.startswith(row) for f in found)
                self.assertTrue(ok, '1.0 %s ▸ %s is on %s' % (menu, row, ' or '.join(WHERE[menu])))

    def test_c_keys_are_shown_beside_rows_and_show_keys_lives_in_view(self):
        from PySide6.QtCore import QCoreApplication, Qt
        rows = self.head_rows()
        for (menu, row), keys in KEYS.items():
            action = next((a for _, words, a in rows[menu] if words == row), None)
            self.assertIsNotNone(action, '%s ▸ %s in %s' % (menu, row, [words for _, words, _ in rows[menu]]))
            self.assertEqual(action.shortcut().toString(), keys, '%s ▸ %s shows %s' % (menu, row, keys))
            self.assertTrue(action.isShortcutVisibleInContextMenu(), 'keys shown by default (W1)')
        show = next(a for d, words, a in rows['View'] if words == 'Show keys' and d == 0)
        self.assertFalse(any(words == 'Show keys' for m in ('File', 'Edit', 'Go', 'Tools', 'Help') for _, words, _ in rows[m]), 'one home: View')
        show.trigger();self.settle()
        try:
            self.assertTrue(QCoreApplication.testAttribute(Qt.AA_DontShowShortcutsInContextMenus))
            self.assertFalse(self.w.a_details.isShortcutVisibleInContextMenu(), 'Show keys off: no key printed')
        finally:
            show.trigger();self.settle()
        self.assertTrue(self.w.a_details.isShortcutVisibleInContextMenu())

    def test_d_her_rules_the_stop_halt_and_apps_keep_their_places(self):
        rows = self.head_rows();tools = [words for d, words, _ in rows['Tools'] if d == 0]
        self.assertIn("Kasandra's hand", tools, 'her rules: a row of their own')
        self.assertIn('STOP / KILL all Graphite operations…', tools)
        top = self.w.shell2.top
        halt = getattr(top, 'halt', None);self.assertIsNotNone(halt)
        self.assertTrue(halt.isVisible() and halt.geometry().bottom() < 32, 'HALT in the head')
        self.assertTrue(top.programs.isVisible() and top.programs.geometry().bottom() < 32, 'Apps in the head')

    def test_e_her_head_acts_name_the_new_menus(self):
        from workbench import desk_acts
        self.assertEqual(list(desk_acts.HEAD_MENUS), HEAD)
        rows = self.head_rows()
        for menu, allowed in desk_acts.HEAD_ROWS.items():
            self.assertIn(menu, HEAD)
            shown = {desk_acts.row_words(a.text()) for d, _, a in rows[menu] if d == 0}
            for row in allowed:self.assertIn(row, shown, '%s ▸ %s is where her act looks for it' % (menu, row))

    def test_f_the_details_pane_is_off_then_comes_with_alt_p_at_the_right_of_the_centre(self):
        self.ex.show(str(self.home / 'Documents'), via='tree');self.settle(300)
        pane = getattr(self.w, 'details_pane', None)
        self.assertTrue(pane is None or not pane.isVisible(), 'off by default')
        self.assertEqual(self.w.a_details.shortcut().toString(), 'Alt+P')
        pane = self.details(True);stack = self.w.central_stack
        self.assertTrue(pane.isVisible());self.assertEqual(pane.width(), 320)
        self.assertEqual(pane.geometry().right(), stack.width() - 1, 'at the right edge of the centre')
        self.assertEqual(stack.contentsMargins().right(), 320, 'the centre makes room: nothing is covered')
        self.assertLessEqual(self.ex.page.width(), stack.width() - 320)
        self.details(False);self.assertFalse(self.w.details_pane.isVisible());self.assertEqual(stack.contentsMargins().right(), 0)

    def test_g_the_details_pane_on_a_file_in_list_and_icons(self):
        budget = self.home / 'Documents' / 'Household budget 2026.ods'
        self.ex.show(str(budget.parent), via='tree', chosen=[str(budget)], view='list');self.settle(300)
        pane = self.details(True)
        try:
            self.assertEqual(pane.title.text(), budget.name)
            self.assertIn('Spreadsheet', pane.facts.text());self.assertIn('Size', pane.facts.text());self.assertIn('Modified', pane.facts.text())
            self.assertIn('ODS', pane.preview.text(), 'the kind in a box: a shape and a word')
            self.assertTrue(pane.links_note.text() or pane.links.count(), 'connections, or a line that says why there are none')
            self.ex.set_view('icons');self.settle(300)
            self.assertEqual(pane.title.text(), budget.name, 'the same thing in Icons')
            listing = self.home / 'Desktop' / 'Shopping list.txt'
            self.ex.show(str(listing.parent), via='tree', chosen=[str(listing)], view='list');self.settle(400)
            self.assertEqual(pane.title.text(), listing.name);self.assertTrue(pane.preview.text().startswith('Shopping list'), 'its first lines')
            pictures = sorted(p for p in (self.home / 'Pictures').iterdir() if p.suffix.lower() in ('.png', '.jpg'))
            self.ex.show(str(pictures[0].parent), via='tree', chosen=[str(pictures[0])]);self.settle(400)
            self.assertEqual(pane.title.text(), pictures[0].name);self.assertFalse(pane.preview.pixmap().isNull(), 'a picture shows itself')
        finally:
            self.details(False)

    def test_h_the_details_pane_on_a_board_tile_lists_its_neighbours(self):
        living = self.w.living_nav
        sheets = [n for n in living.nodes.values() if n.get('provider') == 'living_nav' and n.get('role') == 'sheet']
        self.ex.show(str(self.home), via='tree');self.settle()
        living.go_node(sheets[0]['id'], via='tree');self.settle(400)
        pane = self.details(True)
        try:
            board = self.w.field_page.board;focus = board.board.focus
            self.assertIn('ON THE BOARD', pane.caption.text());self.assertEqual(pane.title.text(), focus.title)
            shown = [t for t in board.board.tiles if t.id != '…' and not t.group]
            self.assertEqual(pane.links.count(), min(len(shown), 12), "the board's neighbours as rows")
            for i in range(pane.links.count()):
                text = pane.links.item(i).text()
                self.assertTrue(text[0] in '─┄' and ('recorded' in text or 'possible' in text), 'a mark and its word: %s' % text)
        finally:
            self.details(False)

    def test_i_the_chrome_at_1920x1200_is_about_116(self):
        self.ex.show(str(self.home), via='tree');self.settle(300)
        top = self.w.shell2.top.height();foot = self.w.type_bar.height();bar = self.w.one_bar.bar.height()
        self.assertEqual((top, foot), (32, 48))
        self.assertFalse(self.w.context_bar.isVisible(), 'the context row is a code tab\'s, not the Explorer\'s')
        self.assertLessEqual(top + bar + foot, 120, 'chrome %d + %d + %d' % (top, bar, foot))

    def test_j_under_reduce_motion_the_pane_appears_at_once(self):
        from workbench import details_pane_qt
        with patch.object(details_pane_qt, 'reduce_motion', return_value=True):
            self.w.a_details.trigger()
            try:
                self.assertEqual(self.w.details_pane.open_width, 320, 'no slide');self.assertIsNone(self.w.details_pane.anim)
            finally:
                self.w.a_details.trigger()
            self.assertEqual(self.w.details_pane.open_width, 0)


class Rules(unittest.TestCase):
    """Tokens 1.1 and the tables, without a window."""

    def test_tokens_1_1(self):
        from workbench import design_tokens as t
        self.assertEqual(t.chrome(1.0, 1200), (32, 48));self.assertEqual(t.chrome(1.0, 728), (32, 44))
        head, foot = t.chrome(1.0, 1200);self.assertLessEqual(head + 34 + foot, 116, 'head + centre bar + foot')
        for look in ('day', 'night', 'graphite', 'kasandra'):self.assertGreaterEqual(t.head_px(look), t.LEAST_PX)
        self.assertGreaterEqual(min(px for px, *_ in t.TYPE.values()), 11, 'nothing under 11 px')
        self.assertTrue(all(160 <= ms <= 240 for ms in t.MOTION.values()));self.assertEqual(t.GLOW, 0, 'elevation, not glow')
        self.assertEqual(t.DETAILS['width'], 320);self.assertEqual(t.FONT['ui'], 'Inter');self.assertEqual(t.FONT['mono'], 'IBM Plex Mono')

    def test_the_six_titles_and_the_table_of_moves(self):
        from workbench import head_menus, menus2
        from sdk.cli.arc1cli.command_bar import GROUP_LABELS
        self.assertEqual(list(head_menus.HEAD), HEAD);self.assertEqual(list(menus2.DISPLAY_TITLES.values()), HEAD)
        self.assertTrue(set(GROUP_LABELS.values()) <= set(HEAD), 'the favorites say the head\'s words')
        olds = ' '.join(old for old, _ in head_menus.MOVED)
        for menu in ROWS_1_0:self.assertIn(menu, olds, 'the table says where %s went' % menu)
        self.assertTrue(all(new.split(' ')[0] in HEAD for _, new in head_menus.MOVED))

    def test_link_words_carry_their_kind(self):
        from workbench.details_pane_qt import said, kind_letters, text_lines
        self.assertEqual(said(True, 'input'), 'recorded · input');self.assertEqual(said(False, 'possible: both name it'), 'possible: both name it')
        self.assertEqual(kind_letters('a.ods'), 'ODS');self.assertEqual(kind_letters('x', folder=True), 'FOLDER')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'n.txt';p.write_text('one\ntwo\n');self.assertEqual(text_lines(p), ['one', 'two'])
            b = Path(d) / 'b.bin';b.write_bytes(b'\0\1\2');self.assertIsNone(text_lines(b))


if __name__ == '__main__':
    unittest.main()
