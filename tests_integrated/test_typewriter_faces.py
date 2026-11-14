"""0.8.3, every face of Kasandra in the typewriter face (tools/derive_typewriter.py; boss_theme FACE, DISPLAY and MONO).

Kasandra Elite, the words face, is Special Elite with a slashed zero, an l on a right foot and tabular figures, every other
letter as it was. Kasandra Elite Mono, the face of what must line up, has every character on Plex Mono's pitch and line, so
a Terminal's columns, a table's figures and every row measured in Plex Mono keep their places; what it lacks (an arrow, a
box-drawing line) comes from Plex Mono at the same width. Graphite keeps Plex.
"""
import ast
import hashlib
import os
import re
import string
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication

from tests_integrated.kasandra_window_probe import probe

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'branding' / 'fonts' / 'typewriter'
APP = QApplication.instance() or QApplication([])


def setUpModule():
    from PySide6.QtGui import QFontDatabase
    from workbench import shell2
    shell2.load_fonts(ROOT)
    for name in ('IBMPlexMono-Regular.ttf', 'IBMPlexSans-Regular.ttf'):QFontDatabase.addApplicationFont(str(ROOT / 'branding/fonts/plex' / name))


def face(family, px):
    from PySide6.QtGui import QFont
    f = QFont(family);f.setPixelSize(px);return f


def metrics(family, px):
    from PySide6.QtGui import QFontMetricsF
    return QFontMetricsF(face(family, px))


def ink(family, ch):
    """The pixels at least half covered when ch is drawn at 64 px from (8, 72)."""
    from PySide6.QtGui import QColor, QImage, QPainter
    image = QImage(120, 100, QImage.Format_Grayscale8);image.fill(0)
    p = QPainter(image);p.setFont(face(family, 64));p.setPen(QColor(255, 255, 255));p.drawText(8, 72, ch);p.end()
    data = bytes(image.constBits());line = image.bytesPerLine()
    return {(x, y) for y in range(100) for x in range(120) if data[y * line + x] >= 128}


class Files(unittest.TestCase):
    def test_the_files_are_the_recorded_ones(self):
        notice = (FONTS / 'NOTICE.md').read_text(encoding='utf-8')
        for name in ('KasandraElite-Regular.ttf', 'KasandraEliteMono-Regular.ttf'):
            sha = hashlib.sha256((FONTS / name).read_bytes()).hexdigest()
            self.assertIn('%s · SHA-256 %s' % (name, sha), notice)
        self.assertIn('Not the Special Elite font; its name is not used for the derived faces.', notice)

    def test_their_families(self):
        from PySide6.QtGui import QFontDatabase
        for name, family in (('KasandraElite-Regular.ttf', 'Kasandra Elite'), ('KasandraEliteMono-Regular.ttf', 'Kasandra Elite Mono')):
            key = QFontDatabase.addApplicationFont(str(FONTS / name))
            self.assertEqual(QFontDatabase.applicationFontFamilies(key), [family])


class Mono(unittest.TestCase):
    def test_it_is_fixed_pitch_and_chosen_as_a_code_face(self):
        from PySide6.QtGui import QFontDatabase
        from workbench import reading_preferences
        self.assertTrue(QFontDatabase.isFixedPitch('Kasandra Elite Mono'))
        self.assertEqual(reading_preferences.family('Kasandra Elite Mono', True), 'Kasandra Elite Mono')

    def test_every_character_on_plex_monos_pitch_and_line(self):
        for px in (12, 13, 14, 16, 18):
            mono, plex = metrics('Kasandra Elite Mono', px), metrics('IBM Plex Mono', px);pitch = plex.horizontalAdvance('M')
            for ch in string.ascii_letters + string.digits + string.punctuation + ' ':
                self.assertAlmostEqual(mono.horizontalAdvance(ch), pitch, delta=0.01, msg='%r at %d px' % (ch, px))
            self.assertAlmostEqual(mono.ascent(), plex.ascent(), delta=0.05);self.assertAlmostEqual(mono.descent(), plex.descent(), delta=0.05)

    def test_what_it_lacks_comes_from_plex_mono_at_the_same_width(self):
        mono, plex = metrics('Kasandra Elite Mono', 16), metrics('IBM Plex Mono', 16)
        for ch in '←─':self.assertAlmostEqual(mono.horizontalAdvance(ch), plex.horizontalAdvance('M'), delta=0.05, msg=ch)


class Words(unittest.TestCase):
    def test_figures_are_tabular_over_every_pair(self):
        words = metrics('Kasandra Elite', 16);zero = words.horizontalAdvance('0')
        for a in string.digits:
            for b in string.digits:self.assertAlmostEqual(words.horizontalAdvance(a + b), 2 * zero, delta=0.01, msg=a + b)

    def test_every_letter_is_special_elites(self):
        words, source = metrics('Kasandra Elite', 16), metrics('Special Elite', 16)
        for text in list(string.ascii_letters + string.punctuation + ' ') + ['DELETE', 'Kasandra', 'Terminal', 'Search', 'Web', 'Log', 'Files', 'Machine', 'Settings']:
            self.assertAlmostEqual(words.horizontalAdvance(text), source.horizontalAdvance(text), delta=0.01, msg=text)
        self.assertEqual(words.height(), 16.0)


class Glyphs(unittest.TestCase):
    def test_l_one_and_zero_are_told_apart(self):
        for family in ('Kasandra Elite', 'Kasandra Elite Mono'):
            fm = metrics(family, 64)
            def foot(ch):
                pixels = ink(family, ch);left = min(x for x, _ in pixels)
                return sum(1 for x, y in pixels if left <= x < left + 0.3 * fm.horizontalAdvance(ch) and 67 <= y < 72)
            def middle(ch):
                pixels = ink(family, ch);xs = [x for x, _ in pixels];ys = [y for _, y in pixels]
                cx, cy = (min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2
                return sum(1 for x, y in pixels if cx - 3 <= x < cx + 3 and cy - 3 <= y < cy + 3)
            self.assertEqual(foot('l'), 0, family + ': the l stands on a right foot');self.assertGreaterEqual(foot('1'), 6, family)
            self.assertGreaterEqual(middle('0'), 8, family + ': the zero is slashed');self.assertEqual(middle('O'), 0, family)


class Wiring(unittest.TestCase):
    def test_kasandra_draws_in_the_typewriter_faces(self):
        out = probe('kasandra', 1366, 768, 'wiring')
        self.assertEqual((out['MONO'], out['shell_mono'], out['FACE'], out['DISPLAY'], out['shell_sans']),
                         ('Kasandra Elite Mono', 'Kasandra Elite Mono', 'Kasandra Elite', 'Kasandra Elite', 'Kasandra Elite'))
        self.assertEqual(out['in_force'], ['Kasandra Elite', 'Kasandra Elite', 'Kasandra Elite Mono'])
        self.assertEqual(out['own'], ['DejaVu Sans', 'DejaVu Serif', 'DejaVu Sans Mono'], 'a face the owner chose is kept')

    def test_graphite_keeps_plex(self):
        out = probe('graphite', 1366, 768, 'wiring')
        self.assertEqual((out['MONO'], out['FACE'], out['DISPLAY']), ('IBM Plex Mono', 'IBM Plex Sans', 'IBM Plex Mono'))
        self.assertEqual(out['in_force'], ['IBM Plex Sans', 'IBM Plex Sans', 'IBM Plex Mono'])

    def test_no_room_names_plex_mono_by_hand(self):
        rooms = ('theme2', 'console_qt', 'log_qt', 'compare_qt', 'finder_qt', 'thumbnails', 'universal_viewer_qt', 'code_rain', 'boss_qt',
                 'idle_display_art', 'chain_menu', 'field_qt', 'investigations_qt', 'datasheet_qt', 'sheet_workbench_qt', 'work_trail_qt',
                 'program_rooms_qt', 'pane_qt', 'hologram_qt', 'kasandra_column')
        for name in rooms:
            tree = ast.parse((ROOT / 'workbench' / (name + '.py')).read_text(encoding='utf-8'))
            found = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and 'IBM Plex Mono' in n.value]
            self.assertEqual(found, [], name)


if __name__ == '__main__':
    unittest.main()
