"""0.8.3, Kasandra's column without her picture, and the kp emblem.

The owner, 14 November 2026: "The right column will have more space for kas text. We could revisit that column appearance
because the picture will be gone." and "I attached a new kp icon/logo".

Her column opens with a masthead whose rule is level with the left pane's tab rule (her name once, at the size of her words;
the state of the work; what she speaks with, shortened in the middle; her hand); her words have the room the picture had,
with room between their lines; a line on her card is drawn in the mono face it is measured in (in Graphite too: that was
the bug); her ground is her terminal's. Apps is the owner's neon kp logo (0.8.3: "New logo for our upper right progman.exe
menu"), its neon drawn round it by the Glow dial, with the words as its fallback; the window icon is Graphite's sharpened
point in both appearances. Graphite's column is as it was.
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

    def test_apps_is_the_neon_logo_then_words(self):
        for out, size in ((self.wide, 1920), (self.small, 1366)):
            apps = out['apps']
            self.assertEqual(apps['kind'], 'AppsButton');self.assertTrue(apps['logo'], size)
            self.assertEqual(apps['icon'], [74, 44], 'about 44 px tall and 74 wide at 14 pt');self.assertEqual(apps['name'], 'Apps')
            self.assertEqual(apps['text'], '');self.assertIn('apps', apps['tip'].lower())
            x, y, w, h = apps['rect'];self.assertEqual((w, h), (92, apps['band']));self.assertEqual(y, 0)
            self.assertLessEqual(x + w, size, 'in the head, at its right end');self.assertGreater(x + w, size - 40)
            lx, ly, lw, lh = apps['logo_rect'];self.assertEqual((lw, lh), (74.0, 44.0));self.assertGreaterEqual(ly, 4, 'clear of the band\'s rule')
            self.assertEqual(out['apps_words'], '[#] Apps \u25be');self.assertFalse(out['apps_words_logo'], 'a logo whose bytes differ is not shown')
            self.assertTrue(out['window_icon_graphite'], 'the window keeps Graphite\'s sharpened point')

    def test_its_neon_follows_the_glow_dial_and_is_none_on_the_clean_desk(self):
        light = self.wide['apps_light']
        self.assertGreater(light['neon'], light['bright']);self.assertGreater(light['bright'], light['soft']);self.assertGreater(light['soft'], 0)
        self.assertEqual(light['zero'], 0.0, 'no glow at 0');self.assertEqual(light['clean'], 0.0, 'none on the Clean desk')
        self.assertEqual(self.wide['clean_level'], 0.0)

    def test_it_catches_as_apps_opens_and_is_still_with_reduce_motion(self):
        out = self.wide
        self.assertTrue(out['catch_anchor']);self.assertTrue(out['catch_on_open']);self.assertTrue(out['catch_settled'])
        self.assertFalse(out['catch_reduce_motion'])


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
        self.assertIsNone(out['hologram'])
        apps = out['apps']      # 0.8.3: Graphite's Apps keeps its words; the window its sharpened point
        self.assertFalse(apps['apps']['logo']);self.assertEqual(apps['apps']['text'], '[#] Apps \u25be');self.assertTrue(apps['window_icon_graphite'])
        self.assertEqual(out['slab'], ['IBM Plex Mono', 15], 'the line on her card in the mono face it was always meant to have')
        self.assertAlmostEqual(out['delete'][0], 0.8, delta=0.01)


class Logo(unittest.TestCase):
    """The neon kp logo's file: verified, recorded, and the only kp mark."""

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
        self.assertIn('kp_neon.png', kasandra_art.MARKS)
        self.assertIn('70efb67742cf2ccf4bf29e08621bac5e58ceb86bd8328b1fbdf58638dad1956e', readme, 'the owner\'s file, by its SHA-256')

    def test_the_drawing_is_trimmed_to_itself(self):
        from PySide6.QtGui import QImage
        image = QImage(str(PACK / 'kp_neon.png')).convertToFormat(QImage.Format_ARGB32);w, h = image.width(), image.height()
        alpha = bytes(image.constBits())[3::4]
        rows = [any(alpha[y * w:(y + 1) * w]) for y in (0, h - 1)];cols = [any(alpha[x::w]) for x in (0, w - 1)]
        self.assertEqual(rows + cols, [True] * 4, 'the drawing reaches every edge: nothing round it')
        self.assertLess(abs(w / h - 1401 / 838), 0.001)


if __name__ == '__main__':
    unittest.main()
