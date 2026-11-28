"""1.1 E1, the Explorer (PLAN_1.1.md, E1; proposal_familiar.md section 4).

Acceptance first, on the Everyday Home (invented: everyday_demo): the window opens on Quick access; Downloads in List view
sorts by size and by date; a picture folder in Icons view shows thumbnails; Board view of a sheet shows 1.0's board; a
typed path opens. Then Back and Forward through folders, the tree's folders and files, W1's keys over the list, the bin's
name, and the rules without a window (the tree's order, the address, the views, sorting, thumbnails).

Run alone:  python3 -B -m unittest -v tests_integrated.test_explorer
"""
import os, random, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

QUICK = ['Home', 'Desktop', 'Documents', 'Downloads', 'Pictures', 'Music']


class Window(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='e1-everyday-');base = Path(cls.temp.name)
        from workbench import everyday_demo
        everyday_demo.build(base);cls.home = base / 'home'
        cls.env = patch.dict(os.environ, {'HOME': str(cls.home), 'XDG_CONFIG_HOME': str(cls.home / '.config'),
                                          'XDG_CACHE_HOME': str(base / 'cache'), 'XDG_DATA_HOME': str(cls.home / '.local/share')})
        cls.env.start()
        from tests_integrated.test_desk_acts import build_window
        cls.store = {};build_window(cls.store, 'e1-window-');cls.w = cls.store['w'];cls.ex = cls.w.explorer
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

    def wait(self, check, seconds=30):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if check():return True
            self.settle(60)
        return check()

    def row(self, label, parent=None):
        page = self.w.cabinet_page
        for ident, item in page.items.items():
            if item.text(0) == label and (parent is None or (item.parent() is not None and item.parent().text(0) == parent)):return ident, item
        return None, None

    # ---- acceptance --------------------------------------------------------------------------------------------------------
    def test_a_the_everyday_home_opens_on_quick_access(self):
        tree = self.w.cabinet_page.tree
        tops = [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())]
        self.assertEqual(tops[0], 'Quick access');self.assertLess(tops.index('Desk'), tops.index('This computer'))
        quick = tree.topLevelItem(0)
        self.assertEqual([quick.child(i).text(0) for i in range(quick.childCount())], QUICK)
        self.assertTrue(quick.isExpanded())
        current = tree.currentItem()
        self.assertEqual((current.text(0), current.parent().text(0)), ('Home', 'Quick access'), 'it lands on Quick access')
        computer = tree.topLevelItem(tops.index('This computer'))
        self.assertEqual(computer.child(0).text(0), 'System (C:)');self.assertFalse(computer.child(0).isExpanded(), 'the root is one press down')
        self.assertEqual(self.w.trash_can.word, 'Recycle Bin', 'the bin, after them, on a new profile')

    def test_a_the_centre_is_home_in_list_never_blank(self):
        if self.ex.folder != str(self.home):self.ex.show(str(self.home), via='start');self.settle()
        s = self.ex.status()
        self.assertTrue(s['front']);self.assertEqual(s['view'], 'list');self.assertEqual(s['address'], '~')
        self.assertEqual(s['rows'], ['Concern', 'Desktop', 'Documents', 'Downloads', 'Music', 'Pictures'])
        self.assertEqual([self.ex.page.list.headerItem().text(c) for c in range(5)], ['Name', 'Modified', 'Type', 'Size', 'Links'])
        self.assertTrue(s['address_shown']);self.assertEqual(s['switch'], ['list'])

    def test_b_downloads_in_list_view_sorts_by_size_and_by_date(self):
        down = self.home / 'Downloads';files = sorted(p for p in down.iterdir() if p.is_file())
        stamps = list(range(len(files)));random.Random(7).shuffle(stamps)
        for p, n in zip(files, stamps):os.utime(p, (1764000000 + n * 3600, 1764000000 + n * 3600))
        self.assertTrue(self.ex.show(str(down), via='tree', view='list'));self.settle()
        from workbench import explorer as ex
        self.ex.sort_by(3);self.settle()      # Size: the largest first
        by_size = sorted(files, key=lambda p: (p.stat().st_size, ex.natural(p.name)), reverse=True)
        self.assertEqual(self.ex.status()['rows'], [p.name for p in by_size]);self.assertEqual(self.ex.status()['sort'], ['Size', 'down'])
        self.ex.sort_by(3);self.settle()      # again: the smallest first
        self.assertEqual(self.ex.status()['rows'], [p.name for p in reversed(by_size)])
        self.ex.sort_by(1);self.settle()      # Modified: the newest first
        newest = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
        self.assertEqual(self.ex.status()['rows'], [p.name for p in newest]);self.assertEqual(self.ex.status()['sort'], ['Modified', 'down'])
        self.ex.sort_by(0);self.settle()
        self.assertEqual(self.ex.status()['sort'], ['Name', 'up'])

    def test_c_a_picture_folder_in_icons_view_shows_thumbnails(self):
        pictures = self.home / 'Pictures'
        self.assertTrue(self.ex.show(str(pictures), via='tree'));self.settle()
        self.assertEqual(self.ex.status()['view'], 'icons', 'a folder of pictures opens in Icons the first time')
        self.assertTrue(self.wait(lambda: self.ex.status()['thumbnails'] == 12), self.ex.status())
        kept = list((Path(os.environ['XDG_CACHE_HOME']) / 'graphite' / 'thumbs').glob('*.png'))
        self.assertGreaterEqual(len(kept), 12, 'kept in ~/.cache/graphite/thumbs')
        self.ex.set_view('list');self.settle()
        self.ex.show(str(self.home), via='tree');self.ex.show(str(pictures), via='tree');self.settle()
        self.assertEqual(self.ex.status()['view'], 'list', 'each place remembers its view')
        self.ex.set_view('icons');self.settle()

    def test_d_board_view_of_a_sheet_shows_1_0s_board(self):
        living = self.w.living_nav
        sheets = [n for n in living.nodes.values() if n.get('provider') == 'living_nav' and n.get('role') == 'sheet']
        self.assertTrue(sheets, 'the bench seed puts sheets on the Desk')
        sheet = sheets[0];self.ex.show(str(self.home), via='tree');self.settle()
        living.go_node(sheet['id'], via='tree');self.settle(300)      # a press on the sheet in the Desk
        page = self.w.field_page
        self.assertTrue(self.w._field_active);self.assertEqual(page.mode, 'board')
        self.assertEqual(page.board.focus_obj().id, sheet['canonical_id'], "1.0's board, the sheet in its middle")
        self.assertFalse(self.ex.in_front());self.assertTrue(self.ex.switch.isVisibleTo(self.w.one_bar.bar));self.assertEqual(self.ex.status()['switch'], ['board'])
        self.ex.set_view('list');self.settle(200)      # List on the board: the folder again
        self.assertTrue(self.ex.in_front());self.assertFalse(self.w._field_active)

    def test_d_board_view_of_a_file_from_the_list(self):
        docs = self.home / 'Documents';budget = docs / 'Household budget 2026.ods'
        self.assertTrue(self.ex.show(str(docs), via='tree', chosen=[str(budget)], view='list'));self.settle()
        self.assertEqual(self.ex.status()['chosen'], [budget.name])
        self.ex.set_view('board');self.settle(300)
        page = self.w.field_page
        self.assertEqual(page.mode, 'board');self.assertEqual(Path(page.board.focus_obj().title).name, budget.name)
        self.ex.set_view('list');self.settle(200)
        self.assertEqual(self.ex.status()['folder'], str(docs));self.assertEqual(self.ex.status()['chosen'], [budget.name])

    def test_e_a_typed_path_opens(self):
        self.ex.show(str(self.home), via='tree');self.settle()
        for typed, folder in (('~/Documents', self.home / 'Documents'), ('/etc', Path('/etc')), ('C:\\', Path('/')), ('Music', None)):
            self.ex.address.setText(typed);self.ex.go_typed(typed);self.settle()
            self.assertEqual(self.ex.status()['folder'], str(folder) if folder else '/', typed)
            if typed == '/etc':self.ex.show(str(self.home), via='tree');self.settle()
        self.ex.go_typed('~/Downloads/recipe-lentil-soup.txt');self.settle()
        self.assertEqual(self.ex.status()['folder'], str(self.home / 'Downloads'));self.assertEqual(self.ex.status()['chosen'], ['recipe-lentil-soup.txt'])
        self.assertFalse(self.ex.go_typed('~/No such folder'));self.assertEqual(self.ex.status()['folder'], str(self.home / 'Downloads'))

    # ---- around it -----------------------------------------------------------------------------------------------------------
    def test_f_back_and_forward_walk_the_folders(self):
        self.ex.show(str(self.home / 'Documents'), via='tree');self.settle();self.ex.show(str(self.home / 'Music'), via='open');self.settle()
        self.w.living_nav.back();self.settle()
        self.assertEqual(self.ex.status()['folder'], str(self.home / 'Documents'))
        self.w.living_nav.forward();self.settle()
        self.assertEqual(self.ex.status()['folder'], str(self.home / 'Music'))
        self.ex.do('up');self.settle()
        self.assertEqual(self.ex.status()['folder'], str(self.home));self.assertEqual(self.ex.status()['chosen'], ['Music'])

    def test_g_the_tree_opens_folders_and_files_in_the_explorer(self):
        computer = self.w.living_nav.computer
        ident, _ = self.row('Downloads', 'Quick access')
        computer.go(ident, 'tree');self.settle()
        self.assertEqual(self.ex.status()['folder'], str(self.home / 'Downloads'));self.assertTrue(self.ex.in_front())
        letter = str(self.home / 'Documents' / 'Letter to the landlord.odt')
        from workbench.home_files_qt import branch_id
        computer.listed |= {computer.home_id, branch_id(self.home / 'Documents')};self.w.cabinet_page.refresh(force=True);self.settle()
        self.assertIn(branch_id(letter), self.w.living_nav.nodes, 'the letter is a row of Home in the tree')
        computer.go(branch_id(letter), 'tree');self.settle()      # a file chosen in the tree: its folder, with it chosen
        self.assertEqual(self.ex.status()['folder'], str(self.home / 'Documents'));self.assertEqual(self.ex.status()['chosen'], [Path(letter).name])

    def test_h_w1s_keys_copy_paste_and_one_undo_over_the_list(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        down = self.home / 'Downloads';desk = self.home / 'Desktop'
        two = [down / 'recipe-lentil-soup.txt', down / 'budget-template.ods']
        self.ex.show(str(down), via='tree', chosen=[str(p) for p in two], view='list');self.settle()
        self.assertEqual(sorted(self.ex.status()['chosen']), sorted(p.name for p in two))
        view = self.ex.page.list;view.setFocus();QTest.keyClick(view, Qt.Key_C, Qt.ControlModifier);self.settle()
        self.ex.show(str(desk), via='tree', view='list');self.settle()
        QTest.keyClick(self.ex.page.list, Qt.Key_V, Qt.ControlModifier)
        self.assertTrue(self.wait(lambda: all((desk / p.name).exists() for p in two)), 'pasted as one batch')
        self.assertTrue(self.wait(lambda: set(p.name for p in two) <= set(self.ex.status()['rows'])), 'the folder is read again by itself')
        QTest.keyClick(self.ex.page.list, Qt.Key_Z, Qt.ControlModifier)
        self.assertTrue(self.wait(lambda: not any((desk / p.name).exists() for p in two)), 'one Undo takes the whole paste back')
        self.assertTrue(all(p.exists() for p in two), 'the originals stay')

    def test_i_the_bins_name_new_profile_and_1_0_profile(self):
        from workbench.session import Session
        from workbench import explorer_qt
        base = Path(tempfile.mkdtemp(prefix='e1-profile-', dir=self.temp.name))
        self.assertEqual(Session(base / 'new.json').state['bin_word'], 'Recycle Bin')
        old = Session(base / 'old.json');old.state.pop('bin_word', None);old.save()
        self.assertEqual(Session(base / 'old.json').state['bin_word'], 'DELETE', 'a profile that has used 1.0 keeps DELETE')
        explorer_qt.set_bin_word(self.w, 'DELETE');self.assertEqual((self.w.trash_can.word, self.w.trash_can.accessibleName()), ('DELETE', 'DELETE'))
        explorer_qt.set_bin_word(self.w, 'Recycle Bin');self.assertEqual(self.w.trash_can.word, 'Recycle Bin')
        self.assertEqual(self.w.session.state['bin_word'], 'Recycle Bin')


class Rules(unittest.TestCase):
    def test_the_tree_in_the_explorers_order(self):
        from workbench import explorer as ex
        fs = ex.FS;home = '/h'
        n = lambda i, p, role='folder', label=None: ex.node(i, p, role, label or i.rsplit('/', 1)[-1], 'path:' + i)
        rows = [n(ex.COMPUTER, None, 'drawer', 'This computer /'), n(fs + 'home:/h', ex.COMPUTER, label='Home'), n(fs + 'home:/h/Documents', fs + 'home:/h'),
                n(ex.DRIVES, ex.COMPUTER, 'drawer', 'Drives'), n('living:drive:1', ex.DRIVES, 'drive', 'STICK · mounted'), n(fs + 'drive:/media/me/STICK', 'living:drive:1', label='STICK'),
                n(fs + 'root:/etc', ex.COMPUTER), n('cabinet:concern', None, 'drawer', 'Concern'), n(ex.DESK, 'cabinet:concern', 'drawer', 'Desk'),
                n('living:desk:sheets', ex.DESK, 'folder_view', 'Sheets')]
        out, paths = ex.arrange(rows, fs + 'home:/h', [('Home', Path(home)), ('Documents', Path('/h/Documents'))], lambda p: 'path:' + str(p),
                                {'C': '/', 'D': '/media/me/STICK'}, lambda p: '1 GB free of 2 GB')
        tops = [r['label'] for r in out if r['parent'] is None]
        self.assertEqual(tops, ['Quick access', 'Desk', 'This computer', 'Concern'])
        under = lambda parent: [r['label'] for r in out if r['parent'] == parent]
        self.assertEqual(under(ex.QUICK_ID), ['Home', 'Documents']);self.assertEqual(under(ex.COMPUTER), ['System (C:)', 'STICK (D:) · 1 GB free of 2 GB'])
        self.assertEqual(under(ex.SYSTEM_ID), ['etc']);self.assertNotIn(ex.DRIVES, [r['id'] for r in out])
        ids = [r['id'] for r in out]
        for r in out:
            if r['parent']:self.assertLess(ids.index(r['parent']), ids.index(r['id']), 'a row comes after its parent')
        self.assertEqual(paths[ex.SYSTEM_ID], '/');self.assertEqual(paths[fs + 'quick:/h/Documents'], '/h/Documents')

    def test_the_address_takes_home_root_relative_and_dos_paths(self):
        from workbench import explorer as ex
        with tempfile.TemporaryDirectory() as t:
            home = Path(t);(home / 'Documents' / 'Letters').mkdir(parents=True);(home / 'a.txt').write_text('x')
            places = {'C': '/', 'D': str(home / 'Documents')}
            self.assertEqual(ex.address('~/Documents', str(home), home), str(home / 'Documents'))
            self.assertEqual(ex.address('~', '/', home), str(home))
            self.assertEqual(ex.address('Letters', str(home / 'Documents'), home), str(home / 'Documents' / 'Letters'))
            self.assertEqual(ex.address('..', str(home / 'Documents'), home), str(home))
            self.assertEqual(ex.address('D:\\Letters', str(home), home, places), str(home / 'Documents' / 'Letters'))
            self.assertEqual(ex.address('C:\\', str(home), home, places), '/')
            self.assertEqual(ex.address('"%s"' % (home / 'a.txt'), '/', home), str(home / 'a.txt'))
            self.assertEqual(ex.address('~/nothing here', str(home), home), '')
            self.assertEqual(ex.address('Q:\\x', str(home), home, places), '')

    def test_views_sorting_and_words(self):
        from workbench import explorer as ex
        pics = [{'name': 'a.jpg', 'kind': 'file'}, {'name': 'b.png', 'kind': 'file'}, {'name': 'n.txt', 'kind': 'file'}]
        self.assertEqual(ex.view_for('/x', pics, saved={}), 'icons');self.assertEqual(ex.view_for('/x', pics[2:], saved={}), 'list')
        self.assertEqual(ex.view_for('/x', pics, saved={'/x': 'board'}), 'board')
        rows = [{'name': 'b', 'kind': 'folder'}, {'name': 'file10', 'kind': 'file', 'bytes': 5}, {'name': 'file9', 'kind': 'file', 'bytes': 50}, {'name': 'a', 'kind': 'folder'}]
        self.assertEqual([r['name'] for r in ex.ordered(rows, 0)], ['a', 'b', 'file9', 'file10'])
        self.assertEqual([r['name'] for r in ex.ordered(rows, 3, True)], ['b', 'a', 'file9', 'file10'], 'folders stay first')
        self.assertEqual(ex.bytes_words(1536), '1.5 KB');self.assertEqual(ex.bytes_words(3 << 30), '3.0 GB')
        self.assertEqual(ex.in_words('letter.odt is in DELETE (from ~).', 'Recycle Bin'), 'letter.odt is in the Recycle Bin (from ~).')
        self.assertEqual(ex.in_words('letter.odt is in DELETE.', 'DELETE'), 'letter.odt is in DELETE.')
        with tempfile.TemporaryDirectory() as t:
            env = {'XDG_CONFIG_HOME': t}
            ex.remember_view('/x', 'icons', env);self.assertEqual(ex.read(env)['views'], {'/x': 'icons'})

    def test_quick_access_follows_user_dirs(self):
        from workbench import explorer as ex
        with tempfile.TemporaryDirectory() as t:
            home = Path(t)
            for name in ('Desktop', 'Dokumente', 'Downloads', 'Music'):(home / name).mkdir()
            text = 'XDG_DOCUMENTS_DIR="$HOME/Dokumente"\nXDG_PICTURES_DIR="$HOME/Bilder"\n'
            self.assertEqual([label for label, _ in ex.quick_places(home, text)], ['Home', 'Desktop', 'Dokumente', 'Downloads', 'Music'])

    def test_a_thumbnail_is_small_and_kept(self):
        from PySide6.QtGui import QColor, QImage
        from workbench import explorer_qt
        with tempfile.TemporaryDirectory() as t:
            picture = Path(t) / 'big.png';image = QImage(800, 400, QImage.Format_RGB32);image.fill(QColor('#3a7'));image.save(str(picture))
            got = explorer_qt.thumbnail(str(picture), 96, Path(t) / 'thumbs')
            self.assertEqual((got.width(), got.height()), (96, 48))
            self.assertEqual(len(list((Path(t) / 'thumbs').glob('*.png'))), 1)
            again = explorer_qt.thumbnail(str(picture), 96, Path(t) / 'thumbs');self.assertEqual(again.size(), got.size())
            (Path(t) / 'not.png').write_text('not a picture');self.assertIsNone(explorer_qt.thumbnail(str(Path(t) / 'not.png'), 96, Path(t) / 'thumbs'))


if __name__ == '__main__':
    unittest.main()
