"""0.8.3: Kasandra's highlight in her burnt yellow, and the neon kp logo as the only kp mark.

The owner, 14 November 2026: "I'm kinda thinking that highlighting should be in our burnt yellow??? Like especially in
menus???", "You measure what is visually pleasing", "we have to be careful how that makes the graphite not look green";
and "New logo for our upper right progman.exe menu ;) ... Omg I love it", "Retire any other kp icon".

Kasandra only: the row you are on in a menu is a solid bar (#e2a72e, dark ink #171b3c, a 2 px #ffd27a edge); every other
highlight is the edge and words (#e2a72e, #ffd27a) on an opaque fill (#5a3f0c); burnt yellow is added as light, never mixed
over her cyan. Graphite keeps every colour and every rule of its sheets. The neon logo is verified before it is shown, its
neon is in proportion to the Glow dial and none at 0, and no file of the marks it retires, nor any word of them, is left.
"""
import colorsys
import hashlib
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'branding' / 'kasandra'
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from workbench import boss_theme  # noqa: E402

# Graphite's palette as it was before 0.8.3, by key: none of these may move.
GRAPHITE_PINNED = dict(
    GROUND='#0b0e0d', PANEL='#111513', CARD='#151a17', RAISED='#202520', TERMINAL_GROUND='#080a09',
    LINE='#474436', LINE_STRONG='#bcac8e', LINE_MID='#6b6550', TEXT='#f4e8ce', QUIET='#c8baa0', FAINT='#a89b84',
    AMBER='#4b2a14', AMBER_SOFT='#4b2a14', AMBER_EDGE='#ff9a36', AMBER_TEXT='#ffba72',
    PENCIL_DEEP='#443527', ERASER='#493225', ERASER_DEEP='#593a29', ERASER_MARK='#dd854b',
    TEAL='#c3ed74', TEAL_SOFT='#1b2817', TEAL_EDGE='#789654', TEAL_TEXT='#cbf08b', READY='#c3ed74', STOP='#ff9a36',
    OWNER='#ff9a36', ON_OWNER='#0b0e0d', RECHECK='#ff9a36', BAND=(12, 15, 14), ERASED='#efeae0', ERASED_QUIET='#b0bcb9',
    BAND_MARK='#dd854b', BAND_PENCIL='#f2a369', DESK_LIGHT='#8c826b', VEIL='#000000', DISPLAY='IBM Plex Mono', FACE='IBM Plex Sans',
    MONO='IBM Plex Mono', HONEY='#f2a369', VIOLET='#c8baa0', VIOLET_DEEP='#474436', VIOLET_PALE='#f4e8ce', VIOLET_SOFT='#4b2a14',
    ROYAL='#cbf08b', ROYAL_SOFT='#1b2817', ROYAL_INK='#cbf08b', ROYAL_TEXT='#cbf08b', RED='#ff9a36', ON_RED='#0b0e0d')


def lum(colour):
    c = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True);return (la + 0.05) / (lb + 0.05)


def hue(colour):
    return colorsys.rgb_to_hls(*[int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)])[0] * 360


def mix(top, under, share):
    """`share` of `top` laid over `under` (paint), as #rrggbb."""
    a = [int(top[i:i + 2], 16) for i in (1, 3, 5)];b = [int(under[i:i + 2], 16) for i in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(round(x * share + y * (1 - share)) for x, y in zip(a, b))


def screen(top, under, share):
    """`share` of `top` added to `under` as light (Screen)."""
    a = [int(top[i:i + 2], 16) * share / 255 for i in (1, 3, 5)];b = [int(under[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(round(255 * (1 - (1 - x) * (1 - y))) for x, y in zip(a, b))


def in_appearance(appearance, code):
    """Run `code` in a child with this appearance chosen at its start; the JSON on its last line."""
    env = dict(os.environ, GRAPHITE_APPEARANCE=appearance, QT_QPA_PLATFORM='offscreen', HOME=os.environ.get('HOME', '/tmp'))
    done = subprocess.run([sys.executable, '-B', '-c', code], cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=180)
    lines = [line for line in done.stdout.splitlines() if line.startswith('{')]
    if not lines:raise AssertionError(done.stderr[-3000:])
    return json.loads(lines[-1])


class Tokens(unittest.TestCase):
    def test_kasandras_highlight_is_burnt_yellow_and_reads(self):
        k = boss_theme.PALETTES['kasandra']
        self.assertEqual((k['BAR'], k['ON_BAR'], k['BAR_EDGE']), ('#e2a72e', '#171b3c', '#ffd27a'))
        self.assertEqual((k['AMBER'], k['AMBER_SOFT'], k['AMBER_EDGE'], k['AMBER_TEXT']), ('#5a3f0c', '#5a3f0c', '#e2a72e', '#ffd27a'))
        self.assertGreaterEqual(contrast(k['ON_BAR'], k['BAR']), 7.0, 'the bar\'s ink')
        self.assertGreaterEqual(contrast(k['AMBER_TEXT'], k['AMBER_SOFT']), 6.5, 'the words on a highlight')
        self.assertGreaterEqual(contrast(k['AMBER_EDGE'], k['GROUND']), 7.0, 'the edge on her ground')
        self.assertGreaterEqual(contrast(k['ON_BAR_QUIET'], k['BAR']), 4.5, 'a row that says why it cannot act, on the bar')
        self.assertGreaterEqual(contrast(k['ON_AMBER'], k['AMBER_SOFT']), 6.5)
        for name in ('BAR', 'BAR_EDGE', 'AMBER_SOFT', 'AMBER_EDGE', 'AMBER_TEXT', 'BAND_MARK', 'BAND_PENCIL'):
            self.assertTrue(30 <= hue(k[name]) <= 45, (name, hue(k[name])))
        self.assertEqual(boss_theme.PALETTES['kasandra']['READY'], '#83eaff', 'her cyan stays what is ready')
        self.assertEqual((k['CUE'], k['CUE_EDGE'], k['CUE_TEXT']), ('#1d3d63', '#83eaff', '#b9f4ff'), 'what is not a selection keeps her cyan')

    def test_graphite_keeps_every_colour(self):
        g = boss_theme.PALETTES['graphite']
        for name, value in GRAPHITE_PINNED.items():
            self.assertEqual(g[name], value, name)
        # its new names are what each place already drew: its amber, its menus' wash and inks, no edge
        self.assertEqual((g['CUE'], g['CUE_EDGE'], g['CUE_TEXT']), (g['AMBER'], g['AMBER_EDGE'], g['AMBER_TEXT']))
        self.assertEqual((g['BAR'], g['ON_BAR'], g['BAR_EDGE'], g['ON_BAR_QUIET'], g['ON_AMBER']), (g['AMBER_SOFT'], g['TEXT'], g['AMBER_SOFT'], g['QUIET'], g['TEXT']))
        self.assertEqual(set(g), set(boss_theme.PALETTES['kasandra']))

    def test_every_highlight_fill_is_opaque(self):
        for appearance, p in boss_theme.PALETTES.items():
            for name in ('AMBER', 'AMBER_SOFT', 'AMBER_EDGE', 'AMBER_TEXT', 'BAR', 'BAR_EDGE', 'ON_BAR', 'ON_AMBER', 'BAND_MARK', 'BAND_PENCIL'):
                self.assertRegex(p[name], r'^#[0-9a-f]{6}$', (appearance, name))
        out = in_appearance('kasandra', 'import json;from workbench import boss_theme as b, theme2 as t;print(json.dumps(dict(h=b.HIGHLIGHTS, m=b.MENU_BAR_CSS, qss=t.QSS2)))')
        sheet = out['h']
        self.assertIn('QMenu::item:selected {background:#e2a72e; color:#171b3c; border:0; border-left:2px solid #ffd27a;', sheet)
        self.assertIn('QListWidget#OneBoxList::item:selected {background:#e2a72e; color:#171b3c;', sheet, 'the writing line\'s results')
        self.assertIn('QTreeView::item:selected, QListView::item:selected {background:#5a3f0c; color:#ffd27a; border-left:2px solid #e2a72e;}', sheet)
        self.assertIn('QTabBar::tab:selected {background:#5a3f0c; color:#ffd27a; border-bottom:2px solid #e2a72e;}', sheet)
        for rule in re.findall(r'[^{}]*:(?:selected|checked|focus)[^{}]*\{[^{}]*\}', sheet):
            self.assertNotIn('rgba', rule);self.assertNotIn('transparent', rule.split('{')[1])
        self.assertTrue(out['qss'].endswith(sheet.strip() + '\n') or sheet.strip() in out['qss'], 'the window\'s sheet carries them')
        graphite = in_appearance('graphite', 'import json;from workbench import boss_theme as b;print(json.dumps(dict(h=b.HIGHLIGHTS, m=b.MENU_BAR_CSS)))')
        self.assertEqual(graphite, dict(h='', m=''), 'Graphite\'s sheets gain nothing')

    def test_yellow_is_light_added_never_mixed_over_her_cyan(self):
        yellow, cyan, blue, indigo = '#e2a72e', '#83eaff', '#1d3d63', '#171b3c'
        for under in (cyan, blue):      # why: mixed, yellow and cyan make green
            self.assertTrue(any(70 < hue(mix(yellow, under, share)) < 170 for share in (0.3, 0.4, 0.5)), under)
            for share in (0.1, 0.3, 0.5, 0.7, 1.0):      # added as light, never green
                self.assertFalse(70 < hue(screen(yellow, under, share)) < 170, (under, share, screen(yellow, under, share)))
        for share in (0.3, 0.5):self.assertTrue(25 <= hue(mix(yellow, indigo, share)) <= 45, 'over her indigo it stays warm')
        code = ('import json;from PySide6.QtGui import QImage, QPainter;from workbench import boss_theme as b;i=QImage(4,4,QImage.Format_ARGB32);'
                'p=QPainter(i);b.lays_light(p);m=p.compositionMode();p.end();print(json.dumps(dict(mode=m.name)))')
        self.assertEqual(in_appearance('kasandra', code)['mode'], 'CompositionMode_Screen', 'light added, in Kasandra')
        self.assertEqual(in_appearance('graphite', code)['mode'], 'CompositionMode_SourceOver', 'Graphite: as it always was')


PAINT = r'''
import json
from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter
from PySide6.QtWidgets import QApplication
app = QApplication([])
from workbench import boss_theme as b, programs_qt, tool_faces
image = QImage(120, 30, QImage.Format_RGB32);image.fill(QColor(b.CARD));p = QPainter(image);programs_qt.paint_bar(p, image.rect());p.end()
bar = [image.pixelColor(0, 15).name(), image.pixelColor(1, 15).name(), image.pixelColor(2, 15).name(), image.pixelColor(60, 15).name()]
glyph = tool_faces.icon('find').pixmap(40, 40, QIcon.Active).toImage().convertToFormat(QImage.Format_ARGB32)
inks = set()
for y in range(glyph.height()):
    for x in range(glyph.width()):
        c = glyph.pixelColor(x, y)
        if c.alpha() == 255:inks.add(c.name())
print(json.dumps(dict(bar=bar, glyph=sorted(inks))))
'''


class Painted(unittest.TestCase):
    def test_the_row_you_are_on_is_a_solid_bar_and_its_glyph_reads_on_it(self):
        k = in_appearance('kasandra', PAINT)
        self.assertEqual(k['bar'], ['#ffd27a', '#ffd27a', '#e2a72e', '#e2a72e'], 'a 2 px edge, then the bar, opaque')
        self.assertEqual(k['glyph'], ['#171b3c'], 'its glyph in the bar\'s dark ink, unlit')
        g = in_appearance('graphite', PAINT)
        self.assertEqual(g['bar'], ['#4b2a14'] * 4, 'Graphite: its amber wash, no edge')
        self.assertNotIn('#171b3c', g['glyph']);self.assertTrue(g['glyph'], 'Graphite: its lit glyph as before')


class NeonLogo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_it_is_verified_before_it_is_shown(self):
        import shutil
        import tempfile
        from workbench import kasandra_art, kp_logo
        self.assertEqual(hashlib.sha256((PACK / kp_logo.NAME).read_bytes()).hexdigest(), kasandra_art.MARKS[kp_logo.NAME])
        self.assertIsNotNone(kasandra_art.mark(PACK, kp_logo.NAME))
        self.assertFalse(kp_logo.logo(ROOT).isNull())
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / 'kasandra';shutil.copytree(PACK, copy)
            data = bytearray((copy / kp_logo.NAME).read_bytes());data[-100] ^= 0xFF;(copy / kp_logo.NAME).write_bytes(bytes(data))
            kasandra_art.forget()
            self.assertIsNone(kasandra_art.mark(copy, kp_logo.NAME), 'changed bytes: not shown')
        kasandra_art.forget()

    def light(self, level, surge=0.0):
        """The logo drawn on her band at Glow `level`: how much light lies outside the drawing (luminance above the band's)."""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QColor, QImage, QPainter
        from workbench import kp_logo
        image = QImage(110, 70, QImage.Format_ARGB32_Premultiplied);image.fill(QColor('#141734'))
        p = QPainter(image);used = kp_logo.paint(p, QRectF(18, 13, 74, 44), kp_logo.logo(ROOT), level, 1.0, surge);p.end()
        band = QColor('#141734');total = 0.0
        for y in range(image.height()):
            for x in list(range(0, 16)) + list(range(94, 110)):
                c = image.pixelColor(x, y);total += max(0, c.red() - band.red()) + max(0, c.green() - band.green()) + max(0, c.blue() - band.blue())
        return total, used

    def test_its_neon_is_in_proportion_to_the_glow_dial_and_none_at_zero(self):
        from workbench import kp_logo
        none, used = self.light(0.0)
        self.assertEqual(none, 0.0);self.assertEqual(used, (0.0, 0.0, 0.0))
        soft, bright, neon = self.light(1.0)[0], self.light(1.9)[0], self.light(3.0)[0]
        self.assertGreater(soft, 0);self.assertGreater(bright, soft);self.assertGreater(neon, bright)
        self.assertGreater(self.light(3.0, surge=1.0)[0], neon, 'it surges as it catches')
        w, c, g = kp_logo.strengths(3.0);self.assertAlmostEqual(w, 3 * kp_logo.WIDE);self.assertAlmostEqual(c, 3 * kp_logo.CLOSE);self.assertAlmostEqual(g, 3 * kp_logo.GHOST)
        self.assertEqual((kp_logo.size().width(), kp_logo.size().height()), (74, 44))

    def test_its_ghosts_are_cyan_left_and_magenta_right(self):
        from workbench import kp_logo
        colours = dict((side, colour) for colour, side in kp_logo.GHOSTS)
        self.assertLess(abs(hue(colours[-1.0]) - 191), 15, 'cyan to the left');self.assertTrue(290 <= hue(colours[1.0]) <= 330, 'magenta to the right')


class Retired(unittest.TestCase):
    """The neon logo is the only kp mark: no file of the marks it retires, and no word of them in the program, its tools, its
    tests or its records of now (the release notes and the version's lineage are history and keep theirs)."""
    NAMES = ('kp_' + 'monogram', 'kp_' + 'emblem', 'kp_' + 'tile', 'cut_kp_' + 'emblem', 'mono' + 'gram')

    def test_no_file_is_left(self):
        left = sorted(p.name for p in PACK.iterdir() if p.name.startswith('kp_') and p.name != 'kp_neon.png')
        self.assertEqual(left, []);self.assertFalse((ROOT / 'tools' / ('cut_kp_' + 'emblem.py')).exists())

    def test_no_reference_is_left(self):
        places = [ROOT / 'workbench', ROOT / 'tools', ROOT / 'tests_integrated', ROOT / 'branding', ROOT / 'docs']
        files = [ROOT / 'MANIFEST.json', ROOT / 'README.md', ROOT / 'RECORD_OF_DIRECTIONS.md', ROOT / 'GETTING_STARTED.md']
        for place in places:
            files += [p for p in place.rglob('*') if p.is_file() and p.suffix in ('.py', '.md', '.json', '.txt', '.sh', '.cmd')]
        history = {ROOT / 'workbench' / 'version.py', Path(__file__).resolve()}
        found = []
        for path in files:
            if path in history or path.name.startswith('RELEASE_NOTES_'):continue
            text = path.read_text(encoding='utf-8', errors='replace')
            found += ['%s: %s' % (path.relative_to(ROOT), name) for name in self.NAMES if name in text]
        self.assertEqual(found, [])


if __name__ == '__main__':
    unittest.main()
