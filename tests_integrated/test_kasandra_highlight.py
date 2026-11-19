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
        w, c, g = kp_logo.strengths(3.0);self.assertAlmostEqual(w, 3 * kp_logo.WIDE);self.assertAlmostEqual(c, 3 * kp_logo.CLOSE);self.assertAlmostEqual(g, min(kp_logo.GHOST_SETTLED, 3 * kp_logo.GHOST))
        self.assertEqual((kp_logo.size().width(), kp_logo.size().height()), (74, 44))

    def ghost_light(self, level):
        """The light the two ghosts alone lay beside the drawing at Glow `level`: the logo drawn on her band with them, less
        the logo drawn without them, summed over the picture."""
        from unittest.mock import patch
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QColor, QImage, QPainter
        from workbench import kp_logo
        def drawn():
            image = QImage(110, 70, QImage.Format_ARGB32_Premultiplied);image.fill(QColor('#141734'))
            p = QPainter(image);kp_logo.paint(p, QRectF(18, 13, 74, 44), kp_logo.logo(ROOT), level, 1.0, 0.0);p.end();return image
        whole = drawn()
        with patch.object(kp_logo, 'GHOSTS', ()):bare = drawn()
        total = 0
        for y in range(70):
            for x in range(110):
                a, b = whole.pixelColor(x, y), bare.pixelColor(x, y);total += max(0, a.red() - b.red()) + max(0, a.green() - b.green()) + max(0, a.blue() - b.blue())
        return total

    def test_settled_its_ghosts_leave_its_thin_strokes_single_and_the_catch_keeps_its_spread(self):
        # 0.8.4. The review of 0.8.3: at Neon the ghosts (1.5 px away, 0.48) doubled the thin strokes; its edges a fifth softer.
        from unittest.mock import patch
        from workbench import kp_logo
        self.assertEqual(kp_logo.away(), 1.0);self.assertAlmostEqual(kp_logo.away(1.0, 1.0), 3.9, msg='caught, they spread as far as they did (1.5 x 2.6)')
        self.assertAlmostEqual(kp_logo.away(2.0), 2.0, msg='with the interface scale')
        self.assertAlmostEqual(kp_logo.strengths(1.0)[2], 0.16, msg='Soft: as it was');self.assertAlmostEqual(kp_logo.strengths(3.0)[2], 0.3, msg='Neon, settled: 0.48 in 0.8.3')
        self.assertAlmostEqual(kp_logo.strengths(3.0, 1.0)[2], 0.75, msg='caught, they surge as they did')
        self.assertGreater(kp_logo.strengths(3.0, 0.5)[2], kp_logo.strengths(3.0)[2])
        neon = self.ghost_light(3.0);self.assertGreater(neon, 0, 'they are still there');self.assertEqual(self.ghost_light(0.0), 0)
        with patch.multiple(kp_logo, GHOST_AWAY=1.5, GHOST_SETTLED=0.48, SPREAD=2.6):before = self.ghost_light(3.0)      # as 0.8.3 drew them
        self.assertLess(neon, 0.6 * before, 'beside its strokes the ghosts lay less than six tenths of the light they did at Neon: %s of %s' % (neon, before))

    def test_the_drawing_is_kept_small_and_is_the_same_drawing(self):
        # 0.8.4: the file is 1401 x 838, 4.7 MB decoded, for a button 74 x 44. One copy eight times the button's size is kept.
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage
        from workbench import kp_logo
        kept = kp_logo.logo(ROOT);self.assertEqual((kept.width(), kept.height()), (588, 352));self.assertLess(kept.sizeInBytes(), 900_000)
        self.assertEqual(kp_logo.logo(ROOT).cacheKey(), kept.cacheKey(), 'decoded once')
        whole = QImage(str(PACK / kp_logo.NAME)).convertToFormat(QImage.Format_ARGB32_Premultiplied);self.assertGreater(whole.sizeInBytes(), 4_000_000)
        a, b = (i.scaled(74, 44, Qt.IgnoreAspectRatio, Qt.SmoothTransformation) for i in (kept, whole));apart = 0
        for y in range(44):
            for x in range(74):
                p, q = a.pixelColor(x, y), b.pixelColor(x, y);apart += abs(p.red() - q.red()) + abs(p.green() - q.green()) + abs(p.blue() - q.blue()) + abs(p.alpha() - q.alpha())
        self.assertLess(apart / (74 * 44 * 4), 2.0, 'at its size in the head it is the file\'s drawing, to within two levels in 255 on average')

    def test_its_ghosts_are_cyan_left_and_magenta_right(self):
        from workbench import kp_logo
        colours = dict((side, colour) for colour, side in kp_logo.GHOSTS)
        self.assertLess(abs(hue(colours[-1.0]) - 191), 15, 'cyan to the left');self.assertTrue(290 <= hue(colours[1.0]) <= 330, 'magenta to the right')


MARK = 'KASANDRA HIGHLIGHT '

# One child for the small things of 0.8.4, in the look chosen for it: what each draws or says there.
PROBE = r'''
import colorsys, json, re
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication
app = QApplication([])
from workbench import boss_theme as b, chain_icons, datasheet_qt, document_qt, pointer, sheet_workbench_qt
out = dict(look=b.APPEARANCE)
def green(image):
    n = 0
    for y in range(image.height()):
        for x in range(image.width()):
            c = image.pixelColor(x, y);h, l, s = colorsys.rgb_to_hls(c.redF(), c.greenF(), c.blueF())
            n += s >= 0.25 and 70 <= h * 360 <= 170
    return n
def over(pixmap, ground):
    image = QImage(pixmap.size(), QImage.Format_RGB32);image.fill(QColor(ground));p = QPainter(image);p.drawPixmap(0, 0, pixmap);p.end();return image
def pointers():
    counts = {}
    for level in (1.0, 1.9, 3.0):
        b.GLOW[0] = level
        for shape in pointer.SHAPES:
            for ratio in (1.0, 2.0):
                pixmap = pointer.drawn(shape, True, ratio)[0];pixmap.setDevicePixelRatio(1.0)
                for name in ('BAR', 'BAR_EDGE', 'AMBER_SOFT'):counts[name] = counts.get(name, 0) + green(over(pixmap, getattr(b, name)))
    b.GLOW[0] = 3.0
    return counts
out['pointer'] = pointers()
kept = b.VIOLET_PALE;b.VIOLET_PALE = b.READY;out['pointer_haloed_in_ready'] = pointers();b.VIOLET_PALE = kept
def inks(pixmap):
    image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    return sorted({image.pixelColor(x, y).name() for y in range(image.height()) for x in range(image.width()) if image.pixelColor(x, y).alpha() == 255})
out['chain'] = {name: [inks(chain_icons.icon(name).pixmap(36, 36, mode)) for mode in (QIcon.Normal, QIcon.Active, QIcon.Selected)] for name in ('then', 'rows', 'keep')}
page = QPixmap(200, 120);page.fill(QColor('#2aa8ff'))
crop = datasheet_qt.SourceCrop(page, (0.0, 0.0, 1.0, 1.0), 200);crop.mark([{'rect': (0.2, 0.25, 0.5, 0.3)}])
image = crop.grab().toImage();mark = crop.highlight
out['pdf'] = dict(inside=image.pixelColor(int(mark.center().x()), int(mark.center().y())).name(), edge=image.pixelColor(int(mark.left()), int(mark.center().y())).name(),
                  outside=image.pixelColor(4, 4).name())
out['run'] = dict(re.findall(r'QPushButton#RunWorksheetChain:(hover|focus) \{([^}]*)\}', sheet_workbench_qt.SURFACE))
out['run_rest'] = re.findall(r'QPushButton#RunWorksheetChain \{[^}]*border: 1px solid (#[0-9a-f]{6})', sheet_workbench_qt.SURFACE)
out['legacy'] = {old: b.LEGACY.get(old) for old in ('#d4b56a', '#f2a369', '#f8edc9', '#4b2a14', '#ff9a36', '#ffba72')}
yellow = {b.AMBER, b.AMBER_SOFT, b.AMBER_EDGE, b.AMBER_TEXT, b.BAR, b.BAR_EDGE, b.BAND_MARK, b.BAND_PENCIL}
out['to_yellow'] = sorted(old for old, new in b.LEGACY.items() if new in yellow)
out['relit'] = b.relight('QFrame {background:#f8edc9; border-left:3px solid #d4b56a; color:#504d46;}')
out['documents'] = document_qt.PAGE_STYLE.split('QListWidget#DocumentList::item:selected ')[1]
out['chosen_row'] = list(b.chosen_row('#111111', '#222222'))
out['warm'] = [b.warm(share).name() for share in (0.0, 0.08, 0.3, 1.0)]
print(json.dumps(out))
'''


def tally(pixels):
    """Of these (r, g, b): how many there are, how many are warm (hue 25 to 45 degrees, saturation 0.25 or more) and how many
    green (hue 70 to 170, saturation 0.25 or more), hue and saturation as the reviews of 0.8.3 measured them (HLS)."""
    n = warm = green = 0
    for r, g, b in pixels:
        h, _, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255);n += 1
        warm += s >= 0.25 and 25 <= h * 360 <= 45;green += s >= 0.25 and 70 <= h * 360 <= 170
    return dict(n=n, warm=warm, green=green)


def window_report():
    """In the child: the real window on the bench seed, in the look chosen for it. Her keyboard light measured on rendered
    frames (the writing line with the keyboard; the Field's selected sheet with it), and a selected row in the lists that
    have a sheet of their own. The light is what the keyboard changes: each frame is taken with it and without it."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QFrame, QToolButton, QWidget
    from tests_integrated.test_desk_acts import act, build_window, close_window, settle
    from workbench import desktop_header_qt, explore_qt, log_qt
    store = {};build_window(store, 'graphite-highlight-');out = dict(look=boss_theme.APPEARANCE, glow=boss_theme.glow())
    try:
        w = store['w']
        def frames(widget, holder):
            taken = []
            for held in (True, False):
                holder.hasFocus = lambda held=held: held
                widget.update();settle(store);taken.append(widget.grab().toImage().convertToFormat(QImage.Format_RGB32))
            del holder.hasFocus
            return taken
        def lit(with_it, without, spots):
            changed = []
            for x, y in spots:
                p, q = with_it.pixelColor(x, y), without.pixelColor(x, y)
                if abs(p.red() - q.red()) + abs(p.green() - q.green()) + abs(p.blue() - q.blue()) > 24:changed.append((p.red(), p.green(), p.blue()))
            return changed
        act('type.to', {'who': 'her'}, store=store);bar = w.type_bar;r = bar.box.geometry()
        with_it, without = frames(bar, bar.box)      # the eight rows above the line's box and the eight below, inside its columns
        rows = [y for y in list(range(r.top() - 8, r.top())) + list(range(r.bottom() + 1, r.bottom() + 9)) if 0 <= y < bar.height()]
        out['line'] = tally(lit(with_it, without, [(x, y) for x in range(r.left() + 4, r.right() - 3) for y in rows]))
        act('go.field', {'face': 'work'}, store=store);view = w.field_page.view
        act('point.sheet', {'title': next(o.title for o in view.field.objects if getattr(o, 'title', ''))}, store=store)
        with_it, without = frames(view, view)       # round the selected sheet, from just outside its edge to where the light ends
        body = view._layout();at = view._drawn_rect(view.field.selected, body);z = view.zoom
        sheet = QRectF(body.left() + (at.left() - body.left()) * z, body.top() + (at.top() - body.top()) * z, at.width() * z, at.height() * z)
        reach = int(30 * z * view.scale()) + 2;inner = sheet.adjusted(-3, -3, 3, 3)
        spots = [(x, y) for x in range(max(0, int(sheet.left()) - reach), min(view.width(), int(sheet.right()) + reach + 1))
                 for y in range(max(0, int(sheet.top()) - reach), min(view.height(), int(sheet.bottom()) + reach + 1)) if not inner.contains(x, y)]
        out['field'] = tally(lit(with_it, without, spots));act('go.back', store=store)
        act('type.to', {'who': 'log'}, store=store);act('type.room', {'size': 'half'}, store=store);logs = log_qt.view_of(w)
        logs.choose('events', remember=False);settle(store);events = logs.events
        events.setCurrentRow(0);events.scrollToItem(events.item(0));settle(store)
        cell = events.visualItemRect(events.item(0));image = events.viewport().grab().toImage()
        out['log_row'] = [image.pixelColor(cell.left(), cell.center().y()).name(), image.pixelColor(cell.right() - 2, cell.top() + 1).name()]
        act('type.room', {'size': 'line'}, store=store)
        sheets = {'LogView': [logs.styleSheet()]}
        for name, kind, make in (('NicePopup', QFrame, lambda: desktop_header_qt.NicePopup(w, w, embedded=True)), ('SlateSwitch', QToolButton, lambda: desktop_header_qt.SlateSwitch(w))):
            sheets[name] = sorted({x.styleSheet() for x in w.findChildren(kind, name)}) or [make().styleSheet()]
        sheets['LogicalCabinet'] = [w.cabinet_page.styleSheet()]
        explore_qt.show(w);settle(store)
        sheets['ExploreWorkspace'] = sorted({x.styleSheet() for x in w.findChildren(QWidget, 'ExploreWorkspace')})
        out['sheets'] = {name: [re.findall(r'[^{}]*:(?:selected|checked)[^{}]*\{[^{}]*\}', css) for css in found] for name, found in sheets.items()}
    finally:close_window(store)
    print(MARK + json.dumps(out), flush=True)


class Leftovers(unittest.TestCase):
    """0.8.4: what the two reviews of 0.8.3's burnt yellow left open. Each look is asked in a child of its own."""
    probes, windows = {}, {}

    def probe(self, look):
        if look not in self.probes:self.probes[look] = in_appearance(look, PROBE)
        self.assertEqual(self.probes[look]['look'], look);return self.probes[look]

    def window(self, look):
        if look not in self.windows:
            import tempfile
            with tempfile.TemporaryDirectory(prefix='graphite-highlight-home-') as home:
                env = dict(os.environ, GRAPHITE_APPEARANCE=look, QT_QPA_PLATFORM='offscreen', HOME=home)
                for key in ('ARC1_WORKBENCH_CONFIG_HOME', 'ARC_LEDGER_CONCERN', 'ARC_LEDGER_XSESSION'):env.pop(key, None)
                done = subprocess.run([sys.executable, '-B', '-m', 'tests_integrated.test_kasandra_highlight', '--window'], cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=400)
            line = next((l for l in reversed(done.stdout.splitlines()) if l.startswith(MARK)), None)
            self.assertIsNotNone(line, 'no window in %s (exit %s): %s' % (look, done.returncode, (done.stderr or done.stdout)[-3000:]))
            self.windows[look] = json.loads(line[len(MARK):])
        self.assertEqual(self.windows[look]['look'], look);return self.windows[look]

    def test_her_keyboard_light_is_warm_on_a_rendered_frame_and_never_green(self):
        # The review: yellow added as light to her blue came out grey (the line's edge at saturation 0.07 to 0.17, the Field's
        # outer rings at 0.08). Asked: ring pixels at saturation 0.25 or more and hue 25 to 45, and still no green.
        k = self.window('kasandra');self.assertEqual(k['glow'], 3.0, 'at Neon, as the desk opens')
        for where, least in (('line', 3000), ('field', 8000)):
            seen = k[where];self.assertGreaterEqual(seen['n'], least, (where, 'the light is there'))
            self.assertEqual(seen['green'], 0, where);self.assertGreaterEqual(seen['warm'] / seen['n'], 0.9, (where, seen))
        g = self.window('graphite')
        for where in ('line', 'field'):self.assertGreater(g[where]['n'], 1000, 'Graphite: its amber light is where it was')

    def test_a_selected_row_is_her_highlight_in_the_lists_with_a_sheet_of_their_own(self):
        k, g = self.window('kasandra'), self.window('graphite')
        self.assertEqual(k['log_row'], ['#e2a72e', '#5a3f0c'], 'the Log, drawn: her edge, then her fill');self.assertEqual(g['log_row'][1], '#202520', 'Graphite: its raised row')
        hers = 'background:#5a3f0c;color:#ffd27a;'
        was = {'LogView': 'background:#202520;color:#f4e8ce;', 'NicePopup': 'background:#493225;color:#f4e8ce;', 'LogicalCabinet': 'background:#493225;color:#eee9dd;',
               'ExploreWorkspace': 'background:#f3e3e2;', 'SlateSwitch': 'background:#4b2a14;'}
        for name, before in was.items():
            for look, value, said in (('kasandra', k, hers), ('graphite', g, before)):
                found = [rule for rules in value['sheets'][name] for rule in rules];self.assertTrue(found, (look, name))
                for rule in found:self.assertEqual(rule.split('{')[1].rstrip('}').strip().replace(' ', '')[:len(said)], said, (look, name, rule))
        switch = k['sheets']['SlateSwitch'][0][0];self.assertIn('border:1px solid #e2a72e', switch, 'switched on: her highlight whole, its edge too')
        p = self.probe('kasandra');self.assertEqual(p['documents'], '{background:#5a3f0c;color:#ffd27a;}');self.assertEqual(p['chosen_row'], ['#5a3f0c', '#ffd27a'])
        p = self.probe('graphite');self.assertEqual(p['documents'], '{background:#593a29;color:#f4e8ce;}');self.assertEqual(p['chosen_row'], ['#111111', '#222222'])

    def test_the_pointers_glow_is_never_green_over_her_yellow(self):
        # The window system lays the pointer over the row it is on, and that row is her solid yellow bar: no window grab shows
        # it. Laid over BAR, BAR_EDGE and AMBER_SOFT, every shape at every glow and at 1x and 2x: no pixel at hue 70 to 170
        # with saturation 0.25 or more. Haloed in her cyan, as 0.8.3's first cut was, the same count finds the green.
        p = self.probe('kasandra')
        self.assertEqual(p['pointer'], {'BAR': 0, 'BAR_EDGE': 0, 'AMBER_SOFT': 0})
        self.assertGreater(p['pointer_haloed_in_ready']['BAR'], 100, 'the count sees what the review saw')

    def test_chain_menu_pictures_are_in_the_bars_ink_on_the_row_you_are_on(self):
        k, g = self.probe('kasandra'), self.probe('graphite')
        for name, (rest, on_bar, chosen) in k['chain'].items():
            self.assertEqual((on_bar, chosen), (['#171b3c'], ['#171b3c']), name);self.assertNotIn('#171b3c', rest, name);self.assertTrue(rest, name)
        for name, (rest, on_bar, chosen) in g['chain'].items():self.assertNotIn('#171b3c', on_bar + chosen, 'Graphite: as it drew them')

    def test_the_pdf_evidence_mark_is_an_opaque_edge_with_nothing_seen_through(self):
        k, g = self.probe('kasandra'), self.probe('graphite')
        self.assertEqual((k['pdf']['inside'], k['pdf']['edge'], k['pdf']['outside']), ('#2aa8ff', '#e2a72e', '#2aa8ff'), 'the page as it is inside the mark, and her edge whole')
        self.assertNotEqual(g['pdf']['inside'], '#2aa8ff', 'Graphite: its amber wash inside the mark, as before');self.assertEqual(g['pdf']['edge'], '#ff9a36')

    def test_the_sheets_run_button_holds_the_keyboard_in_her_yellow(self):
        k, g = self.probe('kasandra'), self.probe('graphite')
        self.assertEqual(k['run'], {'hover': 'background: #b9f4ff;', 'focus': 'background: #ffd27a; border-color: #e2a72e;'}, 'the pointer in her cyan, the keyboard in her yellow')
        self.assertEqual(g['run'], {'hover': 'background: #ffba72;', 'focus': 'background: #ffba72; border-color: #ff9a36;'});self.assertEqual(g['run_rest'], ['#ff9a36'], 'Graphite: the edge it had')

    def test_the_old_colours_that_became_her_yellow_are_each_decided(self):
        k, g = self.probe('kasandra'), self.probe('graphite')
        self.assertEqual(k['legacy'], {'#d4b56a': '#e2a72e', '#f2a369': '#ffd27a', '#f8edc9': '#1d3d63', '#4b2a14': '#1d3d63', '#ff9a36': '#83eaff', '#ffba72': '#b9f4ff'})
        self.assertEqual(k['to_yellow'], ['#d4b56a', '#f2a369'], 'the chosen one\'s marks, and no other: an old colour that is to be her yellow is decided in boss_theme')
        self.assertEqual(k['relit'], 'QFrame {background:#1d3d63; border-left:3px solid #e2a72e; color:#e3e3ff;}')
        self.assertEqual(g['relit'], 'QFrame {background:#4b2a14; border-left:3px solid #ff9a36; color:#f4e8ce;}', 'Graphite: what it always made of them')
        self.assertEqual(g['legacy']['#4b2a14'], None, 'Graphite maps none of its own colours')

    def test_her_light_is_a_warm_tone_at_every_strength(self):
        tones = self.probe('kasandra')['warm'];self.assertEqual((tones[0], tones[-1]), ('#261c0e', '#e2a72e'))
        for tone in tones:
            h, _, s = colorsys.rgb_to_hls(*[int(tone[i:i + 2], 16) / 255 for i in (1, 3, 5)]);self.assertTrue(25 <= h * 360 <= 45 and s >= 0.25, tone)
        self.assertLess(abs(lum(tones[0]) - lum('#171b3c')), 0.005, 'where it is almost gone it is as dark as her ground')


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
    if sys.argv[1:2] == ['--window']:window_report()
    else:unittest.main()
