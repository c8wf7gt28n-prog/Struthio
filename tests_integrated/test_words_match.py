"""1.1 T2: the words to match. The guides beside the program say what the 1.1 window says: the six head menus (K0's
head_menus.MOVED gives old -> new), the bar along the bottom (B1, in place of 1.0's dock), Start on the Windows key (B2),
Files as an Explorer from Quick access (E1) and the Recycle Bin a new profile shows (E1). And the tiers hold the modules
the 1.1 slices added.

Run: python3 -B -m unittest tests_integrated.test_words_match
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The owner's guides of the current program: the Help pages (guide_pages), Getting Started, the daily guide, the ThinkPad
# page and the README. Release notes and the dated HATCH and BOSS records say what was true when they were written.
GUIDES = ('README.md', 'GETTING_STARTED.md', 'docs/DAILY_GUIDE.md', 'docs/GUIDE_LIVING_DESKTOP.md', 'docs/GUIDE_KASANDRA.md',
          'docs/ACCEPTANCE_1.0.md', 'docs/KAS_MIND_EVENING.md', 'docs/THINKPAD_FIRST_INSTALL.md')


def text(name):
    return (ROOT / name).read_text(encoding='utf-8')


def paragraphs(name):
    return [' '.join(block.split()) for block in re.split(r'\n\s*\n', text(name))]


def old_menus():
    """The 1.0 head menus that 1.1 no longer has, read from head_menus.MOVED (its old places' first words)."""
    from workbench import head_menus
    first = {re.match(r'[A-Za-z]+', old).group(0) for old, _new in head_menus.MOVED}
    return sorted(first - set(head_menus.HEAD) - {'new'})


def old_menu_pattern():
    names = '|'.join(old_menus())
    return re.compile(r'(?<!Tools ▸ )(?<!Tools → )\*{0,2}\b(%s)\*{0,2} ?(▸|→|›)|\b(the|of the) \*{0,2}(%s)\*{0,2} menu\b|'
                      r'\b(Work|Revise) ?[,·] ?(Revise|Tools)\b' % (names, names))


def menu_paths(paragraph):
    """(menu, first row) for each 'Menu ▸ Row' a paragraph names with one of the six head menus."""
    from workbench import head_menus
    heads = '|'.join(head_menus.HEAD)
    return [(m.group(1), m.group(3).strip(' *')) for m in
            re.finditer(r'\b(%s)\*{0,2} (▸|→) \*{0,2}([A-Z](?:[^▸→.,;:()*\n]|\.(?=\d))*?)(?=\*\*| ▸| →|[,;:()]|\.(?!\d)|$)' % heads, paragraph)]


def a_label(words, source):
    """Whether the program writes these words as a whole label: a string of their own (or up to its key or …), or through
    assistant_identity.named(), which reads an older name as Kasandra."""
    return bool(re.search('[\'"]%s[\'"…\t]' % re.escape(words), source)
                or re.search('named\\([\'"]%s[\'"]' % re.escape(words.replace('Kasandra', 'Stacy')), source))


class TheMenusTheGuidesName(unittest.TestCase):
    def test_no_guide_names_a_menu_that_no_longer_exists(self):
        """The acceptance: Work, Revise, Arrange, Commands, Rules, Properties and Guide are gone from the head."""
        pattern = old_menu_pattern(); found = []
        for name in GUIDES:
            for n, line in enumerate(text(name).splitlines(), 1):
                if pattern.search(line):found.append((name, n, line.strip()[:120]))
        self.assertEqual(found, [])

    def test_the_old_menus_are_read_from_head_menus_moved(self):
        self.assertEqual(old_menus(), ['Arrange', 'Commands', 'Guide', 'Properties', 'Revise', 'Rules', 'Work'])
        self.assertTrue(old_menu_pattern().search('choose Arrange ▸ Appearance'))
        self.assertTrue(old_menu_pattern().search('the foot of the **Work** menu'))
        self.assertFalse(old_menu_pattern().search('Tools ▸ Commands ▸ Run an operation…'), 'Commands is a menu of Tools now')

    def test_each_new_place_in_moved_is_a_head_menu(self):
        from workbench import head_menus
        for _old, new in head_menus.MOVED:
            self.assertIn(new.split(' ▸ ')[0], head_menus.HEAD, new)
        self.assertEqual(head_menus.HEAD, ('File', 'Edit', 'View', 'Go', 'Tools', 'Help'))

    def test_a_guide_that_lists_the_head_menus_lists_the_six(self):
        for name in ('GETTING_STARTED.md', 'docs/GUIDE_LIVING_DESKTOP.md', 'docs/DAILY_GUIDE.md'):
            page = ' '.join(text(name).split())
            self.assertTrue(re.search(r'File, Edit, View, Go, Tools,? (and )?Help|File · Edit · View · Go · Tools · Help', page), name)

    def test_every_row_a_guide_names_under_a_head_menu_is_a_row_of_the_program(self):
        """'Help ▸ Try Rail Demo', 'View ▸ Appearance', 'Tools ▸ Kasandra's hand': each row's words are the program's own."""
        source = '\n'.join(p.read_text(encoding='utf-8') for p in sorted((ROOT / 'workbench').glob('*.py')))
        missing = []; seen = 0
        for name in GUIDES:
            for paragraph in paragraphs(name):
                for menu, row in menu_paths(paragraph):
                    seen += 1
                    words = row.rstrip('…').split()      # a row is named with the sentence that follows it: its longest label counts
                    if not any(a_label(' '.join(words[:k]), source) for k in range(len(words), 0, -1)):missing.append((name, menu, row))
        self.assertGreater(seen, 20)
        self.assertEqual(missing, [])

    def test_the_launch_line_sends_the_owner_to_a_menu_that_is_there(self):
        from workbench import head_menus, launch_look
        self.assertIn('View ▸ Appearance', launch_look.LINE)
        self.assertEqual([m for m, _row in menu_paths(launch_look.LINE)], ['View'])
        self.assertIn('View', head_menus.HEAD)


class TheScreenTheGuidesDescribe(unittest.TestCase):
    def test_no_guide_speaks_of_the_dock(self):
        """B1: one bar along the bottom of the screen replaced 1.0's dock across the top."""
        found = [(name, n) for name in GUIDES for n, line in enumerate(text(name).splitlines(), 1) if re.search(r'\bdock\b', line, re.I)]
        self.assertEqual(found, [])
        for name in ('GETTING_STARTED.md', 'docs/GUIDE_LIVING_DESKTOP.md', 'README.md'):
            self.assertRegex(' '.join(text(name).split()), r'bar along the\s+bottom of the screen', name)

    def test_apps_are_never_said_to_be_upper_right(self):
        found = [(name, n) for name in GUIDES for n, line in enumerate(text(name).splitlines(), 1)
                 if re.search(r'Apps[^.\n]{0,12}upper right|\(upper right\)', line)]
        self.assertEqual(found, [])

    def test_start_on_the_windows_key_is_in_the_first_ten_minutes(self):
        page = ' '.join(text('GETTING_STARTED.md').split())
        self.assertIn('**Start** (the Windows key, or Start on the bar)', page)

    def test_where_a_guide_says_delete_it_also_says_recycle_bin(self):
        """E1: a new profile's bin says Recycle Bin; DELETE is what a profile from 1.0 keeps. A paragraph that names the
        can as DELETE says the new word too."""
        found = []
        for name in GUIDES:
            for paragraph in paragraphs(name):
                if re.search(r'\bDELETE\b', paragraph) and 'Recycle Bin' not in paragraph:found.append((name, paragraph[:100]))
        self.assertEqual(found, [])

    def test_files_start_at_quick_access_not_this_computer(self):
        """E1: the tree reads Quick access first; the window starts with Home as a List."""
        for name in ('GETTING_STARTED.md', 'docs/GUIDE_LIVING_DESKTOP.md', 'docs/ACCEPTANCE_1.0.md'):
            page = ' '.join(text(name).split())
            self.assertIn('Quick access', page, name)
            self.assertNotRegex(page, r'start(s|ing)? at \**"?This computer /', name)


class TheTiersHoldTheNewModules(unittest.TestCase):
    def test_the_modules_the_1_1_slices_added_run_in_tier_2(self):
        from tools import check_hatch
        for module in ('test_windows_hand', 'test_bar', 'test_explorer', 'test_start_line', 'test_frame_k0', 'test_words_match'):
            self.assertTrue((ROOT / 'tests_integrated' / (module + '.py')).is_file(), module)
            self.assertIn(module, check_hatch.FOCUSED_MODULES, module)


if __name__ == '__main__':
    unittest.main()
