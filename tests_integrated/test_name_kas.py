"""1.1 R1 · Kas, only Kas (the owner, 28 Nov 2026: "No more graphite. I hate that public name" and "No more anything it's
kas. All of it. kas only kas. The other thing if there must be something else is computer").

The word sweep: no word the program shows says "Graphite" or "Struthio", and none says "Kasandra" where Kas is meant.
Where the desktop must be told apart from her it is "computer": the bar's first window entry is Computer, and Graphite's
window is the computer's window. What is kept on purpose is listed in KEPT (an identifier is compatibility, not a public
name, as at the 0.1 rename): lowercase names (module names, settings keys, ~/.config/graphite, /usr/lib/graphite, the
workspace folders, GRAPHITE_* variables), file names, the font Kasandra Elite, the model's own prompts (never shown), a
lock written before the rename, the lineage's old release notes, and the owner's game STRUTHIO (its own title, in capitals).
"""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = re.compile(r'(?:(?<=\\n)|(?<=\\t)|\b)(Graphite|GRAPHITE|Struthio|Kasandra|KASANDRA)\b')
CODE_FOLDERS = ('workbench', 'sdk')
# (file, the literal's first words) -> why its name is not a shown name. An empty start is the whole file.
KEPT = {
    ('workbench/version.py', ''): 'the lineage: what each release was, in the words of its day (NAME is checked below)',
    ('workbench/judgment.py', 'You choose the next step for Kasandra'): "the model's own prompt, never shown",
    ('workbench/i05_arms.py', "You choose Kasandra"): "the model's own prompt, never shown",
    ('workbench/library_service.py', 'You '): "the model's own prompt, never shown",
    ('workbench/page_marks.py', 'You mark useful places'): "the model's own prompt, never shown",
    ('workbench/tables.py', 'You name the columns'): "the model's own prompt, never shown",
    ('workbench/office_bridge.py', 'Kasandra'): 'HER_NAME_EARLIER: a lock file written before the rename is still hers',
    ('workbench/office_bridge.py', '(Graphite)'): 'HER_NAME_EARLIER: a lock file written before the rename is still hers',
    ('workbench/boss_qt.py', 'Struthio rider.png'): "a picture's file name (branding/), never shown as words",
}
# The program's own text files shown on screen (the phone's pages, her character's starter, a drawn plate).
TEXT_FILES = ('workbench/remote_pwa/app.js', 'workbench/remote_pwa/deck.js', 'workbench/remote_pwa/index.html',
              'workbench/remote_pwa/manifest.webmanifest', 'workbench/kasandra/character_starter.md',
              'branding/boss/night-signal.svg')


def identity(text, start, end):
    """A name that is part of a file name or an identifier (joined by - _ . or /), or the font Kasandra Elite."""
    after, before = text[end:end + 12], text[max(0, start - 1):start]
    return bool(re.match(r'[-_]|\.[A-Za-z0-9]', after)) or (before != '' and before in '-_./') or after.startswith(' Elite')


def shown_names(text):
    """The names in a text that are not identifiers: [(name, the words round it)]."""
    return [(m.group(1), text[max(0, m.start() - 30):m.end() + 30]) for m in NAMES.finditer(text) if not identity(text, m.start(1), m.end(1))]


def code_sweep(root=ROOT, folders=CODE_FOLDERS, kept=None):
    """Every string in the program's code (documentation strings aside: the builder's words) that names Graphite,
    Struthio or Kasandra outside KEPT -> [(file, line, name, words)]."""
    kept = KEPT if kept is None else kept
    out = []
    for folder in folders:
        for path in sorted((Path(root) / folder).rglob('*.py')):
            file = path.relative_to(root).as_posix()
            if (file, '') in kept:continue
            source = path.read_text(encoding='utf-8')
            if not NAMES.search(source):continue
            tree = ast.parse(source);docs = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
                    first = node.body[0]
                    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):docs.add(id(first.value))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
                    if any(f == file and node.value.startswith(start) for f, start in kept):continue
                    out += [(file, node.lineno, name, words) for name, words in shown_names(node.value)]
    return out


class TheWordSweep(unittest.TestCase):
    def test_acceptance_no_shown_graphite_struthio_or_kasandra_in_the_code(self):
        found = code_sweep()
        self.assertEqual(found, [], '\n'.join('%s:%d %s in %r' % row for row in found[:40]))

    def test_the_sweep_catches_a_shown_name_and_keeps_an_identifier(self):
        self.assertEqual([n for n, _ in shown_names("About Graphite\nGraphite's window")], ['Graphite', 'Graphite'])
        self.assertEqual([n for n, _ in shown_names('Ask Kasandra · the Struthio bird')], ['Kasandra', 'Struthio'])
        self.assertEqual(shown_names('graphite-session ~/.config/graphite GRAPHITE_BAR GRAPHITE-MANIFEST.json Kasandra Elite Mono'), [])
        self.assertEqual(shown_names('STRUTHIO Arcade 1.9'), [], "the owner's game keeps its title")

    def test_acceptance_the_programs_text_files_say_kas(self):
        for name in TEXT_FILES:
            with self.subTest(name):
                self.assertEqual(shown_names((ROOT / name).read_text(encoding='utf-8')), [])


class TheNames(unittest.TestCase):
    def test_the_public_name_is_kas_and_the_number_is_unchanged(self):
        from workbench import version
        self.assertEqual(version.NAME, 'Kas')
        self.assertEqual(version.title(), 'Kas ' + version.SHORT)
        self.assertRegex(version.VERSION, r'^\d+\.\d+')

    def test_her_shown_name_is_kas(self):
        from workbench import assistant_identity
        self.assertEqual(assistant_identity.NAME, 'Kas')
        self.assertEqual(assistant_identity.named('Stacy is writing · STACY'), 'Kas is writing · KAS')

    def test_the_bars_first_window_entry_is_computer(self):
        from workbench import bar_qt
        self.assertEqual(bar_qt.GraphiteButton.WORD, 'Computer')
        source = Path(bar_qt.__file__).read_text(encoding='utf-8')
        self.assertIn("Computer: bring the computer\\'s window forward", source)
        self.assertIn("'Open windows and Computer'", source)

    def test_the_looks_once_named_graphite_and_kasandra_keep_their_keys(self):
        from workbench import presentation_preferences as pp
        self.assertEqual(pp.APPEARANCES, (('graphite', 'Pencil'), ('kasandra', 'Indigo'), ('day', 'Day'), ('night', 'Night')))
        self.assertEqual(pp.appearance('kasandra'), 'kasandra', 'a saved look keeps its key')

    def test_the_guide_menu_names_kas(self):
        from workbench import guide_pages
        words = [w for _, w, _, _ in guide_pages.PAGES]
        self.assertIn('Kas, the Ghost in the Shell', words)
        self.assertEqual([w for w in words if shown_names(w)], [])

    def test_her_lock_from_before_the_rename_is_still_hers(self):
        from workbench import office_bridge as ob
        self.assertEqual(ob.HER_NAME[0], 'Kas')
        self.assertEqual(ob.HER_NAME_EARLIER, ('Kasandra', '(Graphite)'))

    def test_internal_identifiers_stay(self):
        """Compatibility, not a public name: the module names, the settings folder, the env names, the program folder."""
        for module in ('workbench/graphite_brand.py', 'workbench/kasandra/character_starter.md'):
            self.assertTrue((ROOT / module).exists(), module)
        self.assertIn("'GRAPHITE_BAR'", (ROOT / 'workbench/bar_qt.py').read_text(encoding='utf-8'))
        self.assertIn('GRAPHITE_APPEARANCE', (ROOT / 'workbench/boss_theme.py').read_text(encoding='utf-8'))


GUIDES = ('README.md', 'GETTING_STARTED.md', 'docs/WORKSHOP.md', 'docs/GUIDE_LIVING_DESKTOP.md', 'docs/GUIDE_KASANDRA.md',
          'docs/KAS_MIND_EVENING.md', 'docs/ACCEPTANCE_1.0.md', 'docs/DAILY_GUIDE.md', 'docs/THINKPAD_FIRST_INSTALL.md',
          'debian/kit/START_HERE.md', 'debian/kit/install.sh', 'debian/kit/JOIN.sh')
RENAME_SAID = re.compile(r'once named|formerly|were called')      # a line that says the rename names the old name on purpose
FOLDERS_KEPT = re.compile(r'Graphite demos')                       # a workspace folder's name, as it is on disk


def guide_names(text):
    return [(n, w) for line in text.splitlines() if not RENAME_SAID.search(line)
            for n, w in shown_names(FOLDERS_KEPT.sub('', line))]


class ThePackagesAndCommands(unittest.TestCase):
    def setUp(self):
        from tools import debian_pkg
        self.pkg = debian_pkg
        self.stanzas = {s['Package']: s for s in debian_pkg.parse_control((ROOT / 'debian/control').read_text())[1:]}

    def test_acceptance_four_kas_packages_never_a_bare_kas_each_moving_its_graphite_name(self):
        self.assertNotIn('kas', self.stanzas, 'Debian 13 has an unrelated package "kas" with a higher version')
        for new, old in (('kas-computer', 'graphite'), ('kas-llama-runtime', 'graphite-llama-runtime'),
                         ('kas-session', 'graphite-session'), ('kas-desktop', 'graphite-desktop')):
            with self.subTest(new):
                s = self.stanzas[new]
                self.assertEqual(self.pkg.relation(s['Provides']), '%s (= @VERSION@)' % old)
                self.assertEqual(self.pkg.relation(s['Replaces']), '%s (<< @VERSION@)' % old)
                self.assertEqual(self.pkg.relation(s['Breaks']), '%s (<< @VERSION@)' % old)
                t = self.stanzas[old]      # transitional: no files, depends on the new name, so `apt upgrade` moves across
                self.assertEqual((t['Section'], t['Architecture'], self.pkg.relation(t['Depends'])), ('oldlibs', 'all', '%s (= @VERSION@)' % new))
                self.assertIn('transitional', t['Description'])
        self.assertEqual(self.pkg.PACKAGES, ('kas-computer', 'kas-llama-runtime', 'kas-session', 'kas-desktop'))

    def test_acceptance_the_commands_are_kas_and_the_old_names_say_the_new_one(self):
        self.assertEqual(sorted(p.name for p in (ROOT / 'debian/bin').iterdir()), ['kas-computer', 'kas-do', 'kas-doctor', 'kas-session', 'kas-startx'])
        self.assertEqual(self.pkg.OLD_COMMANDS, {'graphite': 'kas-computer', 'graphite-doctor': 'kas-doctor', 'graphite-session': 'kas-session',
                                                 'graphite-startx': 'kas-startx', 'graphite-do': 'kas-do'})
        import subprocess
        for old, new in self.pkg.OLD_COMMANDS.items():
            with self.subTest(old):
                # only the script's notice line is run (sh -c LINE NAME sets $0): the script itself would start the program
                line = next(l for l in (ROOT / 'debian/bin' / new).read_text().splitlines() if l.startswith('case "${0##*/}"'))
                said = subprocess.run(['sh', '-c', line, '/usr/bin/' + old], capture_output=True, text=True, timeout=30).stderr
                self.assertIn('%s is now %s' % (old, new), said)
                said = subprocess.run(['sh', '-c', line, '/usr/bin/' + new], capture_output=True, text=True, timeout=30).stderr
                self.assertEqual(said, '', 'the new name says nothing of the old one')

    def test_the_session_entries_say_kas_and_keep_their_files(self):
        xsession = (ROOT / 'debian/graphite-xsession.desktop').read_text()
        self.assertIn('Name=Kas\n', xsession);self.assertIn('Exec=kas-session\n', xsession)
        self.assertIn('user-session=graphite', (ROOT / 'debian/50-graphite.conf').read_text(), 'a saved login choice still finds the session')
        app = (ROOT / 'debian/graphite.desktop').read_text()
        self.assertIn('Name=Kas\n', app);self.assertIn('Exec=kas-computer\n', app)

    def test_acceptance_the_kit_and_the_guides_say_kas(self):
        for name in GUIDES:
            with self.subTest(name):
                self.assertEqual(guide_names((ROOT / name).read_text(encoding='utf-8')), [])
        install = (ROOT / 'debian/kit/install.sh').read_text()
        self.assertIn("packages='kas-computer kas-session'", install);self.assertIn("packages='kas-desktop'", install)
        self.assertIn('for z in KAS_*.zip', (ROOT / 'debian/kit/JOIN.sh').read_text())
        self.assertIn('kas-startx', (ROOT / 'debian/kit/START_HERE.md').read_text())


if __name__ == '__main__':
    unittest.main()
