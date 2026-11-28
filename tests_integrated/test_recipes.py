"""1.1 KS1, her recipes (PLAN_1.1.md, KS1; the coordinator's note of 28 Nov).

Acceptance first: every recipe loads, dry-runs on an invented Home, and its verifier passes after a run in a throwaway HOME;
the five most used (convert pictures, resize pictures, zip a folder, rename many, sort Downloads) run end to end with Undo.
Then the rules: a dry run changes nothing and lists exactly what would; a press runs only what was shown; a change is never
her own and HALT holds it; what cannot be undone says so and asks twice; a missing program names its Debian package; slots
come only from the owner's words (one question otherwise); with a model the recipe is picked by number and slots only by
the owner's numbered words; the line offers a recipe; her talk shows the dry run, then "Done and verified" with Undo.

Every Home here is invented. A recipe whose program this computer lacks is checked for the refusal that names its package
(the designed answer), and listed in the test's output.

Run alone:  python3 -B -m unittest -v tests_integrated.test_recipes
"""
import json, os, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EXAMPLES = {  # the owner's words for each recipe: her dictionary must pick it from them
    'find-big-files': 'find big files over 1 MB in Downloads', 'free-space': 'free space', 'find-duplicates': 'find duplicate files in my home',
    'changed-since': 'what changed since yesterday', 'recent-downloads': 'recent downloads', 'find-by-name': 'find the file called tide',
    'find-by-words': 'find files containing plover', 'old-files': 'old files in Downloads', 'empty-folders': 'empty folders',
    'file-kinds': 'what kinds of files are in Downloads', 'folder-size': 'how big is Documents', 'memory': 'what uses memory',
    'processor': 'cpu usage', 'updates': 'is the system up to date', 'disk-health': 'disk health', 'autostart': 'startup apps',
    'about': 'about this computer', 'battery': 'battery', 'network': 'my ip address', 'failed-services': 'what failed to start',
    'bin-contents': 'what is in the bin', 'pdf-pages': 'how many pages has Tide tables.pdf', 'zip-contents': 'what is in the zip Survey photos.zip',
    'empty-bin': 'empty the bin', 'convert-pictures': 'convert the pictures in Pictures to png', 'resize-pictures': 'resize the photos in Pictures to 400 px',
    'pictures-for-email': 'make the pictures in Pictures for email', 'thumbnails': 'thumbnails of Pictures', 'merge-pdfs': 'merge the pdfs in Documents',
    'split-pdf': 'split the pdf Tide tables.pdf', 'zip-folder': 'zip Documents', 'unzip': 'unzip Survey photos.zip',
    'backup-folder': 'back up Documents to the drive', 'copy-folder': 'copy the folder Documents into Desktop',
    'rename-many': 'rename files in Downloads: replace “FINAL” with “v2”', 'rename-lower': 'rename all these files in Downloads to lower case',
    'remove-from-names': 'remove “copy” from the names in Documents', 'sort-by-kind': 'sort downloads by kind',
    'bin-duplicates': 'delete duplicates in Downloads', 'bin-old-files': 'delete old downloads'}
SYSTEM_REFUSALS = ('could not ask the system', 'not on this computer')      # a container without systemd or iproute2: said in words


def pdf(path, pages=1):
    """A small valid PDF of blank pages (invented)."""
    objs = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [%s] /Count %d >>' % (' '.join('%d 0 R' % (3 + i) for i in range(pages)), pages)]
    objs += ['<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>'] * pages
    out = b'%PDF-1.4\n';offs = []
    for n, o in enumerate(objs, 1):offs.append(len(out));out += ('%d 0 obj\n%s\nendobj\n' % (n, o)).encode()
    x = len(out);out += ('xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)).encode() + b''.join(('%010d 00000 n \n' % o).encode() for o in offs)
    out += ('trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, x)).encode()
    Path(path).write_bytes(out)


def picture(path, size):
    """An invented picture: ImageMagick when it is here, else a PNG written by hand (a plain colour)."""
    if subprocess.run(['which', 'convert'], capture_output=True).returncode == 0 and str(path).endswith(('.jpg', '.png')):
        subprocess.run(['convert', '-size', size, 'xc:steelblue', str(path)], check=True);return
    import struct, zlib
    w, h = (int(x) for x in size.split('x'))
    raw = b''.join(b'\0' + b'\x46\x82\xb4' * w for _ in range(h))
    chunk = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def snapshot(home):
    return sorted((str(p.relative_to(home)), p.stat().st_size if p.is_file() else -1) for p in home.rglob('*')
                  if not str(p.relative_to(home)).startswith(('.local', '.config')))


class Home(unittest.TestCase):
    """A throwaway HOME with an invented everyday Home in it, a workspace, a Kernel and the owner's principal."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();base = Path(self.temp.name)
        self.home = home = base / 'home';home.mkdir();(base / 'ws').mkdir()
        self.media = base / 'media';self.stick = self.media / 'STICK';self.stick.mkdir(parents=True)
        self.env = patch.dict(os.environ, {'HOME': str(home), 'XDG_DATA_HOME': str(home / '.local/share'), 'XDG_CONFIG_HOME': str(home / '.config')})
        self.env.start()
        d = home / 'Downloads';p = home / 'Pictures';docs = home / 'Documents'
        for f in (d, p, docs, home / 'Desktop', home / 'Old Projects'):f.mkdir()
        for n, size in (('Harbour sunset.png', '640x480'), ('Gull 01.jpg', '1200x900'), ('Gull 02.jpg', '800x1200')):picture(p / n, size)
        pdf(docs / 'Lease part 1.pdf', 2);pdf(docs / 'Lease part 2.pdf', 3);pdf(d / 'Tide tables.pdf', 4)
        (d / 'notes.txt').write_text('the plover nests by the harbour wall\n');(d / 'notes 2.txt').write_text('the plover nests by the harbour wall\n')
        (docs / 'notes copy.txt').write_text('a list of tern colonies\n')
        (d / 'Report FINAL.odt').write_bytes(b'x' * 3000);(d / 'Song.mp3').write_bytes(b'm' * 5000);(d / 'Setup.deb').write_bytes(b'd' * 7000)
        (d / 'Map tiles.iso').write_bytes(b'\0' * (3 << 20))
        with zipfile.ZipFile(d / 'Survey photos.zip', 'w') as z:z.writestr('a.txt', 'alpha');z.writestr('sub/b.txt', 'beta')
        os.utime(d / 'Setup.deb', (1, 1))
        from workbench.engineering_kernel import Kernel, operator
        from workbench import box_ops as bx, recipe_book as rb
        self.bx, self.rb = bx, rb
        self.kernel = Kernel(base / 'ws');self.owner = operator()
        self.drives = patch.multiple(bx, DRIVES=(str(self.media),), drives=lambda: [{'path': str(self.stick), 'name': 'STICK', 'free': 1 << 40}])
        self.drives.start()

    def tearDown(self):
        self.drives.stop();self.env.stop();self.temp.cleanup()

    def call(self, op, args, who=None):
        return self.kernel.dispatch(op, args, who or self.owner)

    def picked(self, words):
        got = self.rb.pick_words(words)
        self.assertIsNotNone(got, words)
        return got

    def dry(self, got):
        answer = self.call('recipes.dry_run', {'recipe': got['recipe'], 'slots': got['values']})
        self.assertTrue(answer['ok'], answer);return answer['result']

    def run_it(self, got, dry=None):
        dry = dry or self.dry(got)
        return self.call('recipes.run', {'recipe': got['recipe'], 'slots': got['values'], 'digest': dry['digest']})


class Acceptance(Home):
    def test_forty_recipes_load_and_every_step_is_a_registered_operation(self):
        from workbench.engineering_kernel import CAPABILITIES
        recipes, refused = self.rb.library()
        self.assertEqual(len(recipes), 40);self.assertEqual(refused, [])
        self.assertEqual(sorted(r.id for r in recipes), sorted(EXAMPLES))
        for r in recipes:
            for step in r.steps:
                self.assertIn(step['op'], CAPABILITIES, r.id)
                if CAPABILITIES[step['op']] != 'read':self.assertIn(step['op'], self.bx.PLANNERS, r.id)
        self.assertEqual(sum(1 for r in recipes if r.reads), 23)
        listed = self.call('recipes.list', {})['result']['recipes']
        self.assertEqual([r['n'] for r in listed], list(range(1, 41)))
        self.assertNotIn('program', json.dumps([r['name'] for r in listed]).lower())

    def test_every_recipe_dry_runs_on_the_invented_home_and_its_verifier_passes_after_a_run(self):
        order = sorted(EXAMPLES, key=lambda k: k == 'empty-bin')      # DELETE is emptied last, once something is in it
        not_here, ran = [], []
        for ident in order:
            got = self.picked(EXAMPLES[ident])
            self.assertEqual(got['recipe'], ident, EXAMPLES[ident]);self.assertEqual(got['missing'], [], (ident, got['slots']))
            before = snapshot(self.home)
            dry = self.dry(got)
            self.assertEqual(snapshot(self.home), before, 'a dry run changes nothing: %s' % ident)
            if dry['reads']:
                answer = self.call('recipes.look', {'recipe': ident, 'slots': got['values']})
                if not answer['ok']:
                    why = answer['error']['message']
                    self.assertTrue(any(w in why for w in SYSTEM_REFUSALS), (ident, why));not_here.append((ident, why.split(': ', 1)[-1][:80]));continue
                self.assertTrue(answer['result']['verified'], (ident, answer['result']['checked']));ran.append(ident);continue
            need = next((n for n in dry['needs'] if not n['found']), None)
            if need:
                self.assertFalse(dry['ok']);self.assertIn(need['package'], json.dumps(dry['pre']));not_here.append((ident, need['package']));continue
            self.assertTrue(dry['ok'], (ident, dry['pre'], [s['words'] for s in dry['steps']]))
            answer = self.run_it(got, dry)
            self.assertTrue(answer['ok'], (ident, answer));v = answer['result']
            self.assertEqual((v['state'], v['verified']), ('done', True), (ident, v['checked']))
            ran.append(ident)
            if v['can_undo'] and ident != 'bin-old-files':      # put back, so the next recipe finds the same Home
                back = self.call('recipes.undo', {'run': v['run']})
                self.assertTrue(back['ok'], back);self.assertTrue(back['result']['verified'], (ident, back['result']))
                self.assertEqual(snapshot(self.home), before, 'Undo put the Home back: %s' % ident)
        print('\n  KS1: %d recipes ran and verified; not on this computer: %s' % (len(ran), not_here or 'none'))
        self.assertGreaterEqual(len(ran), 36)

    def test_the_five_most_used_run_end_to_end_with_undo(self):
        if not self.bx._which('convert') and not self.bx._which('magick'):self.fail('ImageMagick is needed for the picture recipes here')
        before = snapshot(self.home);p = self.home / 'Pictures';d = self.home / 'Downloads'
        cases = [('convert the pictures in Pictures to webp', lambda: [x.name for x in p.glob('*.webp')], ['Gull 01.webp', 'Gull 02.webp', 'Harbour sunset.webp']),
                 ('resize the photos in Pictures to 600x600', lambda: sorted(self.bx.picture_size(x) for x in p.glob('* 600px.*')), [(400, 600), (600, 450), (600, 450)]),
                 ('zip Documents', lambda: sorted(zipfile.ZipFile(self.home / 'Documents.zip').namelist()), ['Documents/Lease part 1.pdf', 'Documents/Lease part 2.pdf', 'Documents/notes copy.txt']),
                 ('rename files in Downloads: replace “FINAL” with “v2”', lambda: (d / 'Report v2.odt').exists() and not (d / 'Report FINAL.odt').exists(), True),
                 ('sort downloads by kind', lambda: sorted(x.name for x in (d / 'Documents').iterdir()), ['Report FINAL.odt', 'Tide tables.pdf', 'notes 2.txt', 'notes.txt'])]
        for words, look, want in cases:
            answer = self.run_it(self.picked(words));self.assertTrue(answer['ok'], (words, answer));v = answer['result']
            self.assertTrue(v['verified'], (words, v['checked']));self.assertEqual(sorted(look()) if isinstance(want, list) else look(), want, words)
            back = self.call('recipes.undo', {'run': v['run']});self.assertTrue(back['result']['verified'], back)
            self.assertEqual(snapshot(self.home), before, 'Undo of “%s” put the Home back' % words)
        again = self.call('recipes.undo', {'run': v['run']});self.assertFalse(again['ok']);self.assertIn('already taken back', again['error']['message'])


class Rules(Home):
    def test_a_dry_run_lists_exactly_what_would_change(self):
        dry = self.dry(self.picked('sort downloads by kind'));step = dry['steps'][0]
        self.assertEqual(step['lines'], ['Map tiles.iso → Archives', 'notes 2.txt → Documents', 'notes.txt → Documents', 'Report FINAL.odt → Documents',
                                         'Setup.deb → Installers', 'Song.mp3 → Music', 'Survey photos.zip → Archives', 'Tide tables.pdf → Documents'])
        self.assertEqual(step['words'], 'Move 8 files in ~/Downloads into folders by kind: Archives 2, Documents 4, Installers 1, Music 1 (each folder made new).')
        (self.home / 'Downloads' / 'Music').mkdir();(self.home / 'Downloads' / 'Music' / 'Song.mp3').write_bytes(b'older')
        again = self.dry(self.picked('sort downloads by kind'))['steps'][0]
        self.assertIn('Song.mp3 → Music/Song 2.mp3', again['lines'], 'a name taken there: a free name, nothing written over')
        self.assertTrue(again['words'].endswith('(new: Archives, Documents, Installers).'), again['words'])
        self.assertEqual(dry['undo'], self.bx.UNDO['box.files.sort']);self.assertEqual(dry['scope'], 'execute')

    def test_the_press_runs_only_what_was_shown(self):
        got = self.picked('sort downloads by kind');dry = self.dry(got)
        (self.home / 'Downloads' / 'Late arrival.pdf').write_bytes(b'%PDF-1.4\n')
        before = snapshot(self.home)
        answer = self.run_it(got, dry)
        self.assertFalse(answer['ok']);self.assertIn('changed since you saw it', answer['error']['message'])
        self.assertEqual(snapshot(self.home), before, 'nothing moved')

    def test_a_change_is_never_her_own_and_halt_holds_it(self):
        from workbench.engineering_kernel import Principal
        got = self.picked('sort downloads by kind');dry = self.dry(got);before = snapshot(self.home)
        hers = Principal('kasandra', frozenset({'read', 'execute'}))      # no approve scope: her work (home_reach.in_her_work)
        answer = self.call('recipes.run', {'recipe': got['recipe'], 'slots': got['values'], 'digest': dry['digest']}, hers)
        self.assertFalse(answer['ok']);self.assertIn('your press only', answer['error']['message'])
        direct = self.call('box.files.sort', {'folder': '~/Downloads', 'expect': dry['steps'][0]['expect']}, hers)
        self.assertFalse(direct['ok']);self.assertIn('your press only', direct['error']['message'])
        reader = Principal('reader', frozenset({'read'}))
        self.assertIn('outside the authorized', self.call('recipes.run', {'recipe': got['recipe'], 'slots': got['values'], 'digest': dry['digest']}, reader)['error']['message'])
        self.assertTrue(self.call('halt.press', {})['ok'])
        held = self.run_it(got, dry);self.assertFalse(held['ok']);self.assertIn('HALT holds my work', held['error']['message'])
        self.assertTrue(self.call('recipes.look', {'recipe': 'free-space', 'slots': {}})['ok'], 'HALT stops her work and nothing else: a read of yours')
        self.assertTrue(self.call('halt.release', {})['ok'])
        self.assertEqual(snapshot(self.home), before)
        self.assertTrue(self.run_it(got, dry)['result']['verified'])

    def test_what_cannot_be_undone_says_so_before_the_press_and_asks_with_approve(self):
        self.assertTrue(self.run_it(self.picked('delete old downloads'))['result']['verified'])      # Setup.deb into DELETE
        got = self.picked('empty the bin');dry = self.dry(got)
        self.assertEqual((dry['can_undo'], dry['undo'], dry['scope']), (False, 'This cannot be undone.', 'approve'))
        self.assertEqual(dry['steps'][0]['lines'], ['Setup.deb (from ~/Downloads)'])
        from workbench.engineering_kernel import Principal
        no_approve = Principal('desk', frozenset({'read', 'execute'}))
        self.assertFalse(self.call('box.bin.empty', {'expect': dry['steps'][0]['expect']}, no_approve)['ok'], 'emptying is approve: the owner only')
        v = self.run_it(got, dry)['result'];self.assertTrue(v['verified']);self.assertFalse(v['can_undo'])
        self.assertEqual(self.call('box.bin.list', {})['result']['words'], 'DELETE is empty.')

    def test_a_missing_program_names_its_debian_package_and_stops(self):
        got = self.picked('convert the pictures in Pictures to png');before = snapshot(self.home)
        with patch.object(self.bx, '_which', lambda name: None):
            dry = self.dry(got)
            self.assertFalse(dry['ok']);self.assertIn('“imagemagick” has it', json.dumps(dry['pre'], ensure_ascii=False))
            answer = self.run_it(got, dry);self.assertFalse(answer['ok']);self.assertIn('imagemagick', answer['error']['message'])
        self.assertEqual(snapshot(self.home), before)

    def test_slots_come_only_from_the_owners_words_and_one_question_asks_the_rest(self):
        got = self.picked('resize the photos in Pictures to 800x600')
        self.assertEqual(got['values'], {'folder': '~/Pictures', 'size': '800x600'})
        self.assertEqual({k: v['basis'] for k, v in got['slots'].items()}, {'folder': 'owner_words', 'size': 'owner_words'})
        self.assertEqual(got['slots']['size']['words'], '800x600')
        zipped = self.picked('zip a folder')
        self.assertEqual(zipped['missing'], ['folder']);self.assertEqual(zipped['question']['words'], 'Which folder?')
        self.assertIn(('Documents', '~/Documents'), zipped['question']['choices'])
        answered = self.rb.answer(zipped, 'folder', '~/Documents')
        self.assertEqual((answered['missing'], answered['slots']['folder']['basis'], answered['title']), ([], 'owner_click', 'Zip Documents'))
        free = self.picked('free space');self.assertEqual((free['title'], free['slots']['folder']['basis']), ('Free space in Home: what takes it', 'recipe_default'))
        self.assertIsNone(self.rb.pick_words('what is on the desk today'));self.assertIsNone(self.rb.pick_words('make a folder called Rev 2'))

    def test_with_a_model_it_picks_by_number_and_fills_slots_only_with_the_owners_numbered_words(self):
        from workbench import turns, grammars
        from workbench.fake_worker import FakeWorker
        words = 'my pictures folder is huge, shrink everything in Pictures to 640 px'
        inputs = self.rb.model_inputs(words)
        n = next(r['n'] for r in inputs['menu'] if r['id'] == 'resize-pictures')
        folder = next(w['w'] for w in inputs['spans'] if w['type'] == 'folder' and w['value'] == '~/Pictures')
        size = next(w['w'] for w in inputs['spans'] if w['type'] == 'picture')
        answer = '%d folder=W%d size=W%d' % (n, folder, size)
        grammar = self.rb._grammar(inputs);self.assertTrue(grammars.matches(grammar, answer), answer)
        self.assertFalse(grammars.matches(grammar, '%d folder="~/Secret"' % n), 'the model cannot write a value')
        got = self.rb.pick(words, turns.TurnRequest(port=FakeWorker([answer], enforce_grammar=True, read_rate=2000)))
        self.assertEqual((got['by'], got['recipe'], got['values']), ('model', 'resize-pictures', {'folder': '~/Pictures', 'size': '640'}))
        self.assertIn('640', got['slots']['size']['words'])
        wrong = '%d folder=W%d size=W%d' % (n, size, folder)      # a W of the wrong type for each slot: refused, then asked
        trimmed = self.rb.pick(words, turns.TurnRequest(port=FakeWorker([wrong], read_rate=2000)))
        self.assertEqual((trimmed['by'], trimmed['values'], trimmed['missing']), ('model', {}, ['folder', 'size']))
        off_menu = self.rb.pick('free space', turns.TurnRequest(port=FakeWorker(['99'], read_rate=2000)))
        self.assertEqual((off_menu['by'], off_menu['recipe']), ('dictionary', 'free-space'), 'a number off the menu: her dictionary answers')
        self.assertEqual(self.rb.pick('free space', turns.TurnRequest())['by'], 'dictionary', 'no model: her dictionary')

    def test_the_owners_own_recipes_are_read_and_a_broken_one_is_refused_in_words(self):
        mine = Path(os.environ['XDG_CONFIG_HOME']) / 'graphite' / 'recipes';mine.mkdir(parents=True)
        (mine / 'odt.json').write_text(json.dumps({'recipe': 'graphite.recipe/1', 'id': 'my-odt-files', 'name': 'My ODT files', 'title': 'ODT files in {folder}',
                                                   'words': ['my odt files'], 'slots': {'folder': {'type': 'folder', 'default': '~'}},
                                                   'steps': [{'op': 'box.files.find', 'args': {'folder': '{folder}', 'how': 'name', 'words': '*.odt'}}]}))
        (mine / 'shell.json').write_text(json.dumps({'recipe': 'graphite.recipe/1', 'id': 'wipe', 'name': 'Wipe', 'words': ['wipe'],
                                                     'steps': [{'op': 'files.delete_for_good', 'args': {'path': '~'}}]}))
        recipes, refused = self.rb.library()
        self.assertEqual((len(recipes), recipes[-1].id, recipes[-1].source), (41, 'my-odt-files', 'yours'))
        self.assertEqual(refused, [{'file': '~/.config/graphite/recipes/shell.json', 'why': 'step “files.delete_for_good” is not one of the box operations a recipe may use'}])
        v = self.call('recipes.look', {'recipe': 'my-odt-files', 'slots': {}})['result']
        self.assertEqual([r['name'] for r in v['steps'][0]['rows']], ['Report FINAL.odt'])


class Window(Home):
    """Her talk, NEXT STEPS and the line, on a stand-in for Graphite's window (offscreen)."""

    def setUp(self):
        super().setUp()
        from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout
        self.app = QApplication.instance() or QApplication([])
        from workbench import recipe_book_qt as rbq
        self.rbq = rbq;rbq.SYNC = True;rbq.STATE.clear()
        test = self

        class Face:
            def __init__(self):self.said = [];self.host = test.host;self.thing = None

            def mine(self, text):self.said.append(('you', text))

            def say(self, text):
                bubble = QFrame();bubble.box = QVBoxLayout(bubble);self.said.append(('her', text, bubble));return bubble
        self.host = type('Host', (), {'root': self.kernel.root, 'her_column': None})()
        self.face = Face()

    def tearDown(self):
        self.rbq.SYNC = False;super().tearDown()

    def links(self, bubble):
        from PySide6.QtWidgets import QLabel
        return {w: k for label in bubble.findChildren(QLabel) for k, (w, _) in (getattr(label, '_actions', None) or {}).items()}

    def press(self, bubble, words):
        from PySide6.QtWidgets import QLabel
        for label in bubble.findChildren(QLabel):
            for k, (w, fn) in (getattr(label, '_actions', None) or {}).items():
                if w == words:fn();return
        self.fail('no “%s” in %s' % (words, list(self.links(bubble))))

    def test_her_talk_shows_the_dry_run_then_done_and_verified_with_undo_and_next_steps_follow(self):
        before = snapshot(self.home)
        self.assertTrue(self.rbq.asked(self.face, 'sort downloads by kind'))
        said = self.face.said[-1];self.assertEqual(said[1], 'Recipe “Sort Downloads by kind”. This is exactly what it would do; nothing has changed yet.')
        from PySide6.QtWidgets import QLabel
        shown = ' '.join(l.text() for l in said[2].findChildren(QLabel))
        self.assertIn('Map tiles.iso → Archives', shown);self.assertIn('Undo puts every file back where it was', shown)
        self.assertIn('Run it (your press)', self.links(said[2]));self.assertEqual(snapshot(self.home), before)
        steps = self.rbq.next_steps(self.host);self.assertEqual([s['words'] for s in steps], ['Run · Sort Downloads by kind'])
        self.assertTrue(self.rbq.take(self.host, steps[0]))
        done = self.face.said[-1];self.assertTrue(done[1].startswith('✓ Done and verified, “Sort Downloads by kind”: 8 files read back'), done[1])
        self.assertEqual([s['words'] for s in self.rbq.next_steps(self.host)], ['Undo · Sort Downloads by kind'])
        self.press(done[2], 'Undo')
        self.assertEqual(self.face.said[-1][1], 'Undone, “Sort Downloads by kind”: 8 things put back where they were.')
        self.assertEqual(snapshot(self.home), before);self.assertEqual(self.rbq.next_steps(self.host), [])

    def test_a_read_runs_at_once_the_list_shows_and_what_cannot_be_undone_asks_once_more(self):
        self.assertTrue(self.rbq.asked(self.face, 'find big files over 1 MB in Downloads'))
        said = self.face.said[-1];self.assertTrue(said[1].startswith('Recipe “Find big files in Downloads”. It only reads, so I ran it. 1 file of 1.0 MB'), said[1])
        self.assertFalse(self.rbq.asked(self.face, 'what is on the desk today'), 'not a recipe: the rest of her chain answers')
        self.assertTrue(self.rbq.asked(self.face, 'show me your recipes'))
        self.assertEqual(len(self.links(self.face.said[-1][2])), 40)
        self.assertTrue(self.run_it(self.picked('delete old downloads'))['result']['verified'])
        self.rbq.asked(self.face, 'empty the bin');offer = self.face.said[-1]
        self.assertIn('Run it (asks once more)', self.links(offer[2]))
        self.press(offer[2], 'Run it (asks once more)')
        self.assertEqual(self.face.said[-1][1], '“Empty DELETE” cannot be undone. Run it anyway?')
        self.assertEqual(len(self.bx.bin_list(self.kernel)['rows']), 1, 'nothing emptied before the second press')
        self.press(self.face.said[-1][2], 'Yes, run it')
        self.assertTrue(self.face.said[-1][1].startswith('✓ Done and verified, “Empty DELETE”'), self.face.said[-1][1])
        self.assertNotIn('Undo', self.links(self.face.said[-1][2]))

    def test_the_line_offers_a_recipe_and_enter_shows_what_it_would_do(self):
        from workbench import line_finder as lf
        rows = lf.rows('free space', lf.Sources(None))
        self.assertEqual((rows[0].title, rows[0].verb, rows[0].enter_words()), ('Recipe: Free space in Home: what takes it', 'Show', 'Enter: shows what it would do; nothing changes'))
        self.assertEqual(rows[-1].kind, 'ask')
        self.assertTrue(all(r.verb in lf.VERBS for r in rows))
        self.assertEqual(lf.rows('zip', lf.Sources(None))[0].detail, 'Enter asks the one thing it needs; nothing changes')
        self.assertFalse(any(r.extra.get('recipe') for r in lf.rows('tern', lf.Sources(None))))
        self.assertEqual(self.rbq.line_rows('free space', None)[0][2](), False, 'no window: nothing is done')

    def test_her_new_lines_pass_the_voice_sweep(self):
        from workbench import mind_words
        self.assertEqual([p for p in mind_words.check() if p[0] == 'kas_voice'], [])


if __name__ == '__main__':
    unittest.main()
