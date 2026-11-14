"""0.8.3, Kasandra's column without her picture, and the kp emblem.

The owner, 14 November 2026: "The right column will have more space for kas text. We could revisit that column appearance
because the picture will be gone." and "I attached a new kp icon/logo".

Her column opens with a masthead whose rule is level with the left pane's tab rule (her name once, at the size of her words;
the state of the work; what she speaks with, shortened in the middle; her hand); her words have the room the picture had,
with room between their lines; a line on her card is drawn in the mono face it is measured in (in Graphite too: that was
the bug); her ground is her terminal's. Apps is the owner's emblem, with the monogram and then the words as fallbacks; the
window icon is the emblem's tile. Graphite's column is as it was.
"""
import hashlib
import os
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from tests_integrated.kasandra_window_probe import probe

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'branding' / 'kasandra'


class Column(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wide = probe('kasandra', 1920, 1200, 'column')
        cls.small = probe('kasandra', 1366, 768, 'column')

    def test_the_picture_is_gone_and_the_masthead_is_level_with_the_tabs(self):
        for out in (self.wide, self.small):
            self.assertIsNone(out['portrait']);self.assertEqual(out['face_inks'], 0);self.assertTrue(out['masthead'])
            self.assertEqual(out['rule_y'], out['left_rule_y']);self.assertEqual(out['pane'], 354)
            self.assertEqual(out['name'], ['Kasandra', 'Kasandra Elite'])
            self.assertEqual(out['model_family'], 'Kasandra Elite Mono')
            shown, tip, given = out['model_long']
            self.assertIn('…', shown);self.assertEqual(tip, given);self.assertLess(len(shown), len(given))
            self.assertTrue(shown.startswith(given[:4]) and shown.endswith(given[-4:]), 'shortened in the middle')

    def test_her_words_have_the_room(self):
        for out in (self.wide, self.small):
            self.assertEqual(out['margin'], 4);self.assertGreaterEqual(out['bubble_text_width'], 295, 'about 17 px wider than in 0.8.2')
            self.assertGreaterEqual(out['lead_ratio'], 1.2);self.assertTrue(out['lead_plain'])
            self.assertTrue(out['bubble_plain'].startswith('Ask about what is open.'))
            self.assertNotIn('<p', out['read_last']);self.assertIn('its second line', out['read_last'])
        self.assertEqual(self.wide['scroll'][2:], [322, 869]);self.assertEqual(self.small['scroll'][2:], [322, 437])

    def test_a_line_is_drawn_in_the_mono_face(self):
        family, px, text = self.wide['slab']
        self.assertEqual((family, px), ('Kasandra Elite Mono', 15));self.assertIn('kind=\u200bcsv', text, 'broken at its joints, not mid-word')

    def test_her_ground_is_her_terminals(self):
        """Her terminal's ground is the whole column (0.8.3 review: it was a box inside it, with lighter strips round it)."""
        want = (0x11, 0x13, 0x2c)
        for out in (self.wide, self.small):
            for ground in [out['ground']] + out['ground_round']:
                got = tuple(int(ground[i:i + 2], 16) for i in (1, 3, 5))
                self.assertTrue(all(abs(a - b) <= 2 for a, b in zip(got, want)), (ground, out['ground_round']))

    def test_apps_is_the_emblem_then_the_monogram_then_words(self):
        apps = self.wide['apps']
        self.assertEqual(apps['icon'], [58, 38]);self.assertEqual(apps['name'], 'Apps');self.assertEqual(apps['text'], '')
        self.assertEqual(apps['rect'][2:], [76, 60])
        self.assertEqual(self.wide['apps_monogram'], [36, 36]);self.assertEqual(self.wide['apps_words'], '[#] Apps ▾')
        self.assertEqual(self.wide['icon_source'], 'kasandra')


class Review(unittest.TestCase):
    """The 0.8.3 review's findings in the real window (Kasandra, 1366 by 768)."""

    @classmethod
    def setUpClass(cls):
        cls.out = probe('kasandra', 1366, 768, 'review')

    def test_tooltips_the_documents_page_a_note_and_the_terminal_are_in_her_faces(self):
        out = self.out
        self.assertEqual(out['tooltip'], ['Kasandra Elite', 15])
        self.assertEqual(out['document'], ['Kasandra Elite', 'Kasandra Elite Mono'])
        self.assertEqual(out['markdown'], dict(face=True, mono=True, plex=False))
        self.assertEqual(out['markdown_shown'], dict(words='Kasandra Elite', code=['Kasandra Elite Mono']), 'a note as it reads, its code too')
        self.assertEqual(out['console']['face'], 'Kasandra Elite Mono');self.assertTrue(out['console']['kept'])
        self.assertEqual(out['console']['spacing'][1], 0.0, 'the reading profile\'s prose spacing stays off the Terminal')

    def test_the_font_report_says_her_face_is_the_default(self):
        self.assertEqual(self.out['font_report'], ['APPLIED_WITH_FALLBACK', "Kasandra's face (the default)"])

    def test_a_name_that_fits_a_line_is_never_cut_at_its_end(self):
        fold = self.out['fold']
        self.assertTrue(fold['leaded'] and fold['plain'], fold);self.assertGreaterEqual(fold['room'], 290)
        self.assertGreaterEqual(fold['long_breaks'], 1);self.assertTrue(fold['long_whole'], 'a run longer than a line still breaks, its words kept')

    def test_waiting_on_the_agenda_is_waiting_for_her(self):
        together = self.out['agenda_together']
        self.assertTrue(together['wide'] and together['early'], 'the count and its first word stay together where it costs no line')
        self.assertEqual(self.out['agenda_link'], together['column'], 'her column keeps them together unless that costs it a line')
        self.assertEqual((self.out['current_state'], self.out['column_state'], self.out['masthead_word']), ('idle', 'awaiting_approval', 'waits for you'))

    def test_what_she_speaks_with_says_what_she_learns_from(self):
        tip = self.out['model_tip'].split('\n')
        self.assertEqual(len(tip), 2);self.assertTrue(tip[1].startswith('Learning from '), tip)

    def test_a_face_and_a_size_the_owner_chooses_reach_her_masthead_and_a_shown_line(self):
        default, own, back = self.out['faces_default'], self.out['faces_own'], self.out['faces_back']
        self.assertEqual((default['name'], default['model'], default['slab']), ('Kasandra Elite', 'Kasandra Elite Mono', ['Kasandra Elite Mono', 15]))
        self.assertEqual((own['name'], own['model'], own['slab']), ('DejaVu Serif', 'DejaVu Sans Mono', ['DejaVu Sans Mono', 19]))
        self.assertIn('font-size:18px', own['word']);self.assertEqual(back, default)

    def test_her_cursor_sleeps_with_reduce_motion_and_out_of_sight(self):
        self.assertTrue(self.out['cursor_waiting'])
        self.assertEqual(self.out['cursor_reduce_motion'], [False, 1.0]);self.assertTrue(self.out['cursor_back'])
        self.assertFalse(self.out['cursor_inactive'], 'another program in front: steady')

    def test_a_note_in_the_viewer_keeps_the_desk_and_cuts_no_action(self):
        viewer = self.out['viewer']
        self.assertEqual(viewer['pane'], [354, 354, 354]);self.assertEqual(viewer['cut'], [])
        self.assertEqual(sorted(viewer['shown'] + viewer['behind']), sorted(viewer['wanted']), 'each action shown or behind More…')


class Graphite(unittest.TestCase):
    def test_graphites_column_is_as_it_was(self):
        out = probe('graphite', 1366, 768, 'graphite_column')
        self.assertEqual(out['tabs'], ['IBM Plex Mono'], 'the tabs keep their face (0.8.3 review)')
        self.assertEqual((out['least'], out['need']), (61, 215))
        self.assertEqual(out['portrait'], 'PanelInk');self.assertIsNone(out['masthead']);self.assertEqual(out['margin'], 14)
        self.assertIsNone(out['hologram']);self.assertEqual(out['icon_source'], 'graphite')
        self.assertEqual(out['slab'], ['IBM Plex Mono', 15], 'the line on her card in the mono face it was always meant to have')
        self.assertAlmostEqual(out['delete'][0], 0.8, delta=0.01)


class Emblem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_every_mark_is_recorded(self):
        from workbench import kasandra_art
        readme = (PACK / 'README.md').read_text(encoding='utf-8')
        for name, sha in kasandra_art.MARKS.items():
            self.assertEqual(hashlib.sha256((PACK / name).read_bytes()).hexdigest(), sha, name)
            self.assertIn(sha, readme, name)

    def test_the_cut(self):
        from PySide6.QtCore import QRect
        from PySide6.QtGui import QColor, QImage, QPainter
        master = QImage(str(PACK / 'kp_emblem.png'))
        self.assertEqual((master.width(), master.height()), (737, 482));self.assertTrue(master.hasAlphaChannel())
        self.assertEqual(master.pixelColor(2, 2).alpha(), 0);self.assertLess(abs(master.width() / master.height() - 1.529), 0.02)
        ground = QImage(737, 482, QImage.Format_RGB32);ground.fill(QColor('#070221'))
        p = QPainter(ground);p.drawImage(0, 0, master);p.end()
        source = QImage(str(PACK / 'kp_emblem_source.png')).convertToFormat(QImage.Format_RGB32).copy(QRect(251, 409, 737, 482))
        a, b = bytes(ground.constBits()), bytes(source.constBits())
        errors = sorted(abs(a[i] - b[i]) for i in range(0, len(a)) if i % 4 != 3)
        self.assertLessEqual(sum(errors) / len(errors), 2.5);self.assertLessEqual(errors[int(len(errors) * 0.99)], 16)
        inks = [(254, 241, 227), (242, 62, 107), (253, 54, 108), (118, 53, 254)]
        data = bytes(master.convertToFormat(QImage.Format_ARGB32).constBits())
        for i in range(0, len(data), 4 * 7):      # every seventh pixel
            alpha = data[i + 3]
            if 0.1 * 255 < alpha < 0.9 * 255:
                rgb = (data[i + 2], data[i + 1], data[i])
                self.assertTrue(any(max(abs(x - y) for x, y in zip(rgb, ink)) <= 12 for ink in inks), rgb)

    def test_the_sizes(self):
        from PySide6.QtGui import QImage
        for name, size in (('kp_emblem_38.png', (58, 38)), ('kp_emblem_76.png', (116, 76)), ('kp_tile.png', (256, 256)), ('kp_tile_letters.png', (64, 64))):
            image = QImage(str(PACK / name));self.assertEqual((image.width(), image.height()), size, name)
        tile = QImage(str(PACK / 'kp_tile.png'))
        self.assertEqual(tile.pixelColor(0, 0).alpha(), 0);self.assertEqual(tile.pixelColor(128, 128).alpha(), 255)


    def test_the_small_trace_stands_against_the_band(self):
        """0.8.3 review: the violet trace at 38 px stood about 2:1 against the head band's lit lower edge. Lifted 4 px and
        drawn in a lighter tint of its own violet in the small cut, every solid pixel of it is 3:1 or more against the band
        where it now lies (#1c2642 at its lowest row) and against the band's brightest row it ever reached (#253752)."""
        from PySide6.QtGui import QImage

        def lum(r, g, b):
            ch = lambda v:v / 3294.6 if v <= 10.0164 else ((v / 255 + 0.055) / 1.055) ** 2.4
            return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)
        image = QImage(str(PACK / 'kp_emblem_38.png')).convertToFormat(QImage.Format_ARGB32);data = bytes(image.constBits());violet = []
        for i in range(0, len(data), 4):
            b, g, r, alpha = data[i], data[i + 1], data[i + 2], data[i + 3]
            if alpha >= 250 and b > 200 and b > r + 60 and r > g:violet.append((r, g, b))
        self.assertGreater(len(violet), 5, 'the trace is there')
        for band in ((0x1c, 0x26, 0x42), (0x25, 0x37, 0x52)):
            worst = min((lum(*c) + 0.05) / (lum(*band) + 0.05) for c in violet)
            self.assertGreaterEqual(worst, 3.0, band)


if __name__ == '__main__':
    unittest.main()
