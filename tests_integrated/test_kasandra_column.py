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
        ground = self.wide['ground'];want = (0x11, 0x13, 0x2c)
        got = tuple(int(ground[i:i + 2], 16) for i in (1, 3, 5))
        self.assertTrue(all(abs(a - b) <= 2 for a, b in zip(got, want)), ground)

    def test_apps_is_the_emblem_then_the_monogram_then_words(self):
        apps = self.wide['apps']
        self.assertEqual(apps['icon'], [58, 38]);self.assertEqual(apps['name'], 'Apps');self.assertEqual(apps['text'], '')
        self.assertEqual(apps['rect'][2:], [76, 60])
        self.assertEqual(self.wide['apps_monogram'], [36, 36]);self.assertEqual(self.wide['apps_words'], '[#] Apps ▾')
        self.assertEqual(self.wide['icon_source'], 'kasandra')


class Graphite(unittest.TestCase):
    def test_graphites_column_is_as_it_was(self):
        out = probe('graphite', 1366, 768, 'graphite_column')
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


if __name__ == '__main__':
    unittest.main()
