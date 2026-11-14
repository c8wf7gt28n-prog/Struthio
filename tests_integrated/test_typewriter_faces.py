"""0.8.3, every face of Kasandra in the typewriter face (tools/derive_typewriter.py; boss_theme FACE, DISPLAY and MONO).

Kasandra Elite, the words face, is Special Elite with a slashed zero, a sloped one, a tailed l and tabular figures, every other
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

    def test_the_program_loads_only_the_recorded_bytes(self):
        """shell2.load_fonts loads a typewriter face only when its SHA-256 is the recorded one (0.8.3 review: they were loaded
        unchecked); the record there is the files' and NOTICE.md's."""
        from workbench import shell2
        notice = (FONTS / 'NOTICE.md').read_text(encoding='utf-8')
        self.assertEqual(set(shell2.TYPEWRITER), {'KasandraElite-Regular.ttf', 'KasandraEliteMono-Regular.ttf', 'SpecialElite-Regular.ttf'})
        for name, sha in shell2.TYPEWRITER.items():
            self.assertEqual(hashlib.sha256((FONTS / name).read_bytes()).hexdigest(), sha, name);self.assertIn('%s · SHA-256 %s' % (name, sha), notice)

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
            self.assertEqual(foot('l'), 0, family + ': the l has no foot to its left');self.assertGreaterEqual(foot('1'), 6, family)
            self.assertGreaterEqual(middle('0'), 8, family + ': the zero is slashed');self.assertEqual(middle('O'), 0, family)

    def test_l_and_one_differ_at_reading_sizes_as_much_as_in_plex_mono(self):
        """0.8.3 review: at 13 to 18 px "A1" read as "Al". How far apart l and 1 are drawn (the grey of one against the
        other, at the same pen position: 0 the same picture, 1 nothing shared) is at least Plex Mono's at 13, 15 and 18 px,
        and with an underline (a link) too."""
        from PySide6.QtGui import QColor, QImage, QPainter

        def picture(family, px, ch, under):
            image = QImage(4 * px, 2 * px, QImage.Format_Grayscale8);image.fill(0)
            f = face(family, px);f.setUnderline(under)
            p = QPainter(image);p.setFont(f);p.setPen(QColor(255, 255, 255));p.drawText(px, int(1.4 * px), ch);p.end()
            return bytes(image.constBits())

        def apart(family, px, under=False):
            a, b = picture(family, px, 'l', under), picture(family, px, '1', under)
            return sum(abs(x - y) for x, y in zip(a, b)) / max(1, sum(a) + sum(b))
        for px in (13, 15, 18):
            for under in (False, True):
                plex = apart('IBM Plex Mono', px, under)
                for family in ('Kasandra Elite', 'Kasandra Elite Mono'):
                    self.assertGreaterEqual(apart(family, px, under), plex, '%s at %d px%s' % (family, px, ' underlined' if under else ''))


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
