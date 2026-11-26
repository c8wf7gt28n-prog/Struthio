"""0.8.3, Kasandra's hologram in the lower left (workbench/hologram.py, workbench/hologram_qt.py).

The owner, 14 November 2026: "We're going to move the kasandra picture to lower left column where it's boring looking" and
"If you can animate the static a hologram would have that would be very kool."

Pure: where she stands (every row of the plan's table, and a grid of sizes where she never meets a row, DELETE or the pane's
bottom), how she moves (the flicker's bounds, the tears' clock, the still frame). The window (a subprocess, Kasandra, 1920 by
1200): the picture's mark, the cut, the timer's pace and when it sleeps, standing aside when the tree scrolls (at once),
on Settings and on the Clean desk, Reduce motion's still frame, the measured motion of each state, and the paint time.
1.0 P4 no avatar (the owner, 26 Nov 2026: "No kas avatar anymore"): the window's cases now say she does not stand there.
"""
import math
import os
import random
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from workbench import hologram as holo

from tests_integrated.kasandra_window_probe import probe
from pathlib import Path
ROOT_FOR_P4 = Path(__file__).resolve().parents[1]      # 1.0 P4 no avatar

DELETE = lambda foot_top: (218, foot_top + 8, 120, 29)


class Place(unittest.TestCase):
    TABLE = (      # rows_end, foot_top, result (0.8.3 review: on the stage her base has 24 px, so its ring clears DELETE)
        (429, 1025, ('stage', (36, 629, 281, 380), (28, 629, 297, 404))),      # 1920 Files, 13 rows
        (317, 1025, ('stage', (36, 629, 281, 380), (28, 629, 297, 404))),      # 1920 Machine, 9 rows
        (821, 1025, ('corner', (32, 838, 166, 224), (24, 838, 182, 240))),     # 1920 Files, all 27 rows open
        (429, 593, ('corner', (47, 446, 136, 184), (39, 446, 152, 200))),      # 1366 Files, 13 rows
        (373, 593, ('corner', (26, 390, 178, 240), (18, 390, 194, 256))),      # 1366 Files, top level
        (485, 593, ('corner', (67, 502, 95, 128), (59, 502, 111, 144))),       # 1366 Files, 15 rows
        (513, 593, None),                                                     # 1366 Files, 16 rows
        (317, 593, ('stage', (87, 333, 180, 244), (79, 333, 196, 268))),       # 1366 Machine, 9 rows
        (None, 593, None),                                                    # the tree scrolls, or Settings
    )

    def test_every_row_of_the_plan(self):
        for rows_end, foot_top, want in self.TABLE:
            self.assertEqual(holo.place(rows_end, foot_top, DELETE(foot_top), 354, 16, 1.0), want, (rows_end, foot_top))

    def test_she_never_meets_a_row_delete_or_the_bottom(self):
        found = 0
        for s in (1.0, 18 / 14, 20 / 14):
            I = round(16 * s);P = 354
            for H in (646, 800, 1078):
                foot_top = H - round(53 * s);D = (P - I - round(120 * s), foot_top + round(8 * s), round(120 * s), round(29 * s))
                for rows_end in range(100, 994, 7):
                    r = holo.place(rows_end, foot_top, D, P, I, s)
                    if r is None:continue
                    found += 1;stance, (x, y, w, h), (sx, sy, sw, sh) = r
                    self.assertGreaterEqual(y, rows_end + round(holo.GAP * s))
                    self.assertTrue(I <= sx and sx + sw <= P - I, r)
                    self.assertFalse(sx < D[0] + D[2] and sx + sw > D[0] and sy < D[1] + D[3] and sy + sh > D[1], (r, D))
                    self.assertLessEqual(sy + sh, H);self.assertEqual(h % 4, 0)
                    self.assertLess(abs(w - h * holo.ASPECT), 1);self.assertGreaterEqual(h, round(holo.HMIN * s))
        self.assertGreater(found, 100)

    def test_rows_bottom_is_arithmetic(self):
        self.assertEqual(holo.rows_bottom(13, 28, 65, 960), 65 + 13 * 28)
        self.assertIsNone(holo.rows_bottom(40, 28, 65, 960), 'more rows than the viewport: the tree scrolls')


class Mark(unittest.TestCase):
    def test_the_picture_is_shown_only_with_its_own_bytes(self):
        import shutil, tempfile
        from pathlib import Path
        from workbench import kasandra_art
        pack = Path(__file__).resolve().parents[1] / 'branding' / 'kasandra'
        self.assertIsNotNone(kasandra_art.mark(pack, 'hologram.webp'))
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / 'hologram.webp';shutil.copyfile(pack / 'hologram.webp', copy)
            self.assertIsNotNone(kasandra_art.mark(folder, 'hologram.webp'))
            data = bytearray(copy.read_bytes());data[len(data) // 2] ^= 1;copy.write_bytes(bytes(data))
            os.utime(copy, ns=(1, 1))      # a changed file is checked again
            self.assertIsNone(kasandra_art.mark(folder, 'hologram.webp'), 'one byte changed: not shown')
        self.assertIsNone(kasandra_art.mark(pack, 'not_a_mark.png'))


class Motion(unittest.TestCase):
    def test_the_states_and_their_pace(self):
        self.assertIsNone(holo.MOTION['awaiting_approval']['tears']);self.assertIsNone(holo.MOTION['completed']['tears'])
        self.assertLessEqual(sum(holo.FLICKER), 0.05)
        from workbench import pane_qt
        self.assertEqual(holo.MOTION['idle']['period'], pane_qt.BREATH);self.assertEqual(pane_qt.BREATH, 2.8)
        self.assertEqual(holo.FRAME_MS, 83)
        self.assertEqual([holo.look(s)[0] for s in ('idle', 'working', 'awaiting_approval', 'completed', 'blocked', 'viewing')],
                         ['quiet', 'at work', 'waits for you', 'done', 'stopped', 'quiet'])
        self.assertEqual(len({holo.look(s)[1] for s in holo.STATE_LOOK}), 5, 'each state its own colour')

    def test_the_still_frame_never_moves(self):
        for state in holo.STATE_LOOK:
            for i in range(21):
                plan = holo.frame_plan(state, i * 0.5, random.Random(1), True, i * 0.5, 0.1, {})
                self.assertEqual((plan['flicker'], plan['noise_index'], plan['noise_offset'], plan['scan_offset'], plan['tear'],
                                  plan['sweep_y'], plan['write_y'], plan['power'], plan['base_alpha']), (1.0, 0, (0, 0), 0, None, None, None, None, 1.0), state)

    def test_the_flicker_stays_within_five_percent(self):
        values = [holo.flicker('idle', i / 120) for i in range(12000)]
        self.assertLessEqual(max(abs(v - 1) for v in values), 0.05)
        self.assertEqual(holo.flicker('awaiting_approval', 3.3), 1.0)

    def test_the_tears_clock(self):
        starts = holo.tear_starts('idle', 600, random.Random(7))
        gaps = [b - a for a, b in zip(starts, starts[1:])]
        self.assertTrue(gaps and min(gaps) >= holo.TEAR_GAP - 1e-9, gaps[:5])
        self.assertTrue(9 <= sum(gaps) / len(gaps) <= 13, sum(gaps) / len(gaps))
        self.assertEqual(holo.tear_starts('awaiting_approval', 600, random.Random(7)), [])
        self.assertEqual(holo.tear_starts('completed', 600, random.Random(7)), [])
        blocked = holo.tear_starts('blocked', 600, random.Random(7))
        self.assertEqual(len(blocked), 1);self.assertLessEqual(blocked[0], 0.2)

    def test_the_static_is_calm(self):
        """0.8.3 review: the static sparkled as much in the calm states as at rest. It is drawn anew every third frame, from
        six patterns; while something waits for the owner, or the work stopped, it is faint and held still; and the flicker
        changes by under 2% from one frame to the next."""
        self.assertEqual([holo.noise_key('idle', n) for n in range(12)], [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3])
        self.assertEqual({holo.noise_key('idle', n) for n in range(200)}, set(range(holo.NOISE_KEYS)))
        for state in ('awaiting_approval', 'blocked'):
            self.assertEqual({holo.noise_key(state, n) for n in range(200)}, {0}, state)
            self.assertLessEqual(holo.MOTION[state]['static'], 0.10, state)
            plans = [holo.frame_plan(state, 50 + i / holo.FPS, random.Random(1), False, 50 + i / holo.FPS, None) for i in range(36)]
            self.assertEqual({(p['noise_index'], p['noise_offset']) for p in plans}, {(0, holo.noise_offset(0))}, state)
        steps = [abs(holo.flicker('idle', (i + 1) / holo.FPS) - holo.flicker('idle', i / holo.FPS)) for i in range(holo.FPS * 120)]
        self.assertLess(max(steps), 0.02)

    def test_a_frame_is_drawn_the_same_twice(self):
        a = holo.frame_plan('idle', 12.25, random.Random(3), False, 12.0, None)
        b = holo.frame_plan('idle', 12.25, random.Random(9), False, 12.0, None)
        self.assertEqual(a, b, 'without a memo nothing random is drawn: the noise and the scan lines follow the clock')


class Window(unittest.TestCase):
    """1.0 P4 no avatar (the owner, 26 Nov 2026: "No kas avatar anymore"): her hologram no longer stands in the left pane, in
    any look; hologram_qt.install gives None and the pane is as it is without her. Each case below said what she did when she
    stood there; each now says she does not."""
    @classmethod
    def setUpClass(cls):
        cls.out = probe('kasandra', 1920, 1200, 'hologram')

    def test_the_mark_and_the_cut(self):
        self.assertFalse(self.out['installed'], 'no hologram is stood up (1.0 P4 no avatar)')

    def test_she_stands_in_files_and_her_clock_runs(self):
        self.assertFalse(self.out['installed']);self.assertNotIn('files', self.out, 'she does not stand in Files')

    def test_she_stands_aside(self):
        self.assertFalse(self.out['installed']);self.assertNotIn('scrolls_hidden', self.out)

    def test_reduce_motion_lands_on_a_still_frame(self):
        self.assertFalse(self.out['installed']);self.assertNotIn('still_running', self.out, 'nothing of hers moves')

    def test_her_motion_is_calm_and_follows_the_state(self):
        self.assertFalse(self.out['installed']);self.assertNotIn('motion', self.out)

    def test_a_frame_costs_little(self):
        self.assertFalse(self.out['installed']);self.assertNotIn('paint_ms', self.out, 'no frame of hers is drawn')

    def test_the_state_is_one_colour_on_her_base_and_her_cursor(self):
        self.assertFalse(self.out['installed']);self.assertNotIn('states', self.out)


class Asleep(unittest.TestCase):
    """0.8.3 review: her clock under the idle display, a touch while she is asleep, and a picture that will not decode. 1.0 P4
    no avatar: there is no hologram to put to sleep, to touch or to stand up; the decode is still remembered."""

    @classmethod
    def setUpClass(cls):
        cls.out = probe('kasandra', 1366, 768, 'review')

    def test_the_idle_display_puts_her_to_sleep_and_wakes_her(self):
        self.assertNotIn('idle_running', self.out, 'no hologram under the idle display (1.0 P4 no avatar)')

    def test_a_touch_while_asleep_leaves_no_tear(self):
        self.assertNotIn('touch_asleep', self.out, 'no hologram to touch (1.0 P4 no avatar)')

    def test_a_picture_that_will_not_decode_is_not_stood_up(self):
        from types import SimpleNamespace
        from workbench import hologram_qt
        fake = SimpleNamespace(left_pane=object(), root=ROOT_FOR_P4, hologram='before')
        self.assertIsNone(hologram_qt.install(fake));self.assertIsNone(fake.hologram, 'no picture of her is ever stood up (1.0 P4 no avatar)')

    def test_a_failed_decode_is_remembered(self):
        import shutil, tempfile
        from pathlib import Path
        from unittest.mock import patch
        from PySide6.QtGui import QGuiApplication, QImage, QImageReader
        from workbench import kasandra_art
        QGuiApplication.instance() or QGuiApplication([])
        pack = Path(__file__).resolve().parents[1] / 'branding' / 'kasandra'
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / 'hologram.webp';shutil.copyfile(pack / 'hologram.webp', copy)
            reads = []
            with patch.object(QImageReader, 'read', lambda self:reads.append(1) or QImage()):
                for _ in range(5):self.assertTrue(kasandra_art.cutout(copy).isNull())
            self.assertEqual(len(reads), 1, 'read once, not for every frame')
            kasandra_art.forget()


class Absent(unittest.TestCase):
    def test_a_refused_mark_leaves_the_pane_as_it_was(self):
        self.assertIsNone(probe('kasandra', 1366, 768, 'hologram_absent', {'GRAPHITE_083_NO_MARKS': '1'})['hologram'])

    def test_graphite_has_no_hologram(self):
        self.assertIsNone(probe('graphite', 1366, 768, 'hologram_absent')['hologram'])


if __name__ == '__main__':
    unittest.main()
