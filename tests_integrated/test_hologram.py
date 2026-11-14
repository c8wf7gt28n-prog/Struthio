"""0.8.3, Kasandra's hologram in the lower left (workbench/hologram.py, workbench/hologram_qt.py).

The owner, 14 November 2026: "We're going to move the kasandra picture to lower left column where it's boring looking" and
"If you can animate the static a hologram would have that would be very kool."

Pure: where she stands (every row of the plan's table, and a grid of sizes where she never meets a row, DELETE or the pane's
bottom), how she moves (the flicker's bounds, the tears' clock, the still frame). The window (a subprocess, Kasandra, 1920 by
1200): the picture's mark, the cut, the timer's pace and when it sleeps, standing aside when the tree scrolls (at once),
on Settings and on the Clean desk, Reduce motion's still frame, the measured motion of each state, and the paint time.
"""
import math
import os
import random
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from workbench import hologram as holo

from tests_integrated.kasandra_window_probe import probe

DELETE = lambda foot_top: (218, foot_top + 8, 120, 29)


class Place(unittest.TestCase):
    TABLE = (      # rows_end, foot_top, result
        (429, 1025, ('stage', (36, 637, 281, 380), (28, 637, 297, 396))),      # 1920 Files, 13 rows
        (317, 1025, ('stage', (36, 637, 281, 380), (28, 637, 297, 396))),      # 1920 Machine, 9 rows
        (821, 1025, ('corner', (32, 838, 166, 224), (24, 838, 182, 240))),     # 1920 Files, all 27 rows open
        (429, 593, ('corner', (47, 446, 136, 184), (39, 446, 152, 200))),      # 1366 Files, 13 rows
        (373, 593, ('corner', (26, 390, 178, 240), (18, 390, 194, 256))),      # 1366 Files, top level
        (485, 593, ('corner', (67, 502, 95, 128), (59, 502, 111, 144))),       # 1366 Files, 15 rows
        (513, 593, None),                                                     # 1366 Files, 16 rows
        (317, 593, ('stage', (84, 333, 186, 252), (76, 333, 202, 268))),       # 1366 Machine, 9 rows
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

    def test_a_frame_is_drawn_the_same_twice(self):
        a = holo.frame_plan('idle', 12.25, random.Random(3), False, 12.0, None)
        b = holo.frame_plan('idle', 12.25, random.Random(9), False, 12.0, None)
        self.assertEqual(a, b, 'without a memo nothing random is drawn: the noise and the scan lines follow the clock')


class Window(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = probe('kasandra', 1920, 1200, 'hologram')

    def test_the_mark_and_the_cut(self):
        self.assertTrue(self.out['installed'])
        self.assertEqual(self.out['cutout'], dict(alpha=True, corner=0, same=True))

    def test_she_stands_in_files_and_her_clock_runs(self):
        files = self.out['files']
        self.assertTrue(files['visible']);self.assertEqual(files['stance'], 'stage');self.assertEqual(files['interval'], 83)
        self.assertEqual(files['figure'], [36, 698, 281, 380])
        if self.out['active']:self.assertTrue(files['running'])
        self.assertEqual(self.out['meets_rows'], 0);self.assertFalse(self.out['meets_delete'])
        self.assertFalse(self.out['inactive_running'], 'asleep while another program is in front')

    def test_she_stands_aside(self):
        self.assertTrue(self.out['scrolls_hidden_at_once'], 'hidden in the same signal that made the tree scroll')
        self.assertGreater(self.out['scroll_range'], 0);self.assertTrue(self.out['scrolls_hidden']);self.assertTrue(self.out['back'])
        self.assertTrue(self.out['settings_hidden']);self.assertFalse(self.out['settings_running'])
        self.assertEqual(self.out['clean'], dict(hidden=True, layers=True, running=False));self.assertTrue(self.out['illustrated_back'])

    def test_reduce_motion_lands_on_a_still_frame(self):
        self.assertFalse(self.out['still_running']);self.assertTrue(self.out['still_same'])

    def test_her_motion_is_calm_and_follows_the_state(self):
        m = self.out['motion'];idle, working, waiting, still = m['idle'][0], m['working'][0], m['awaiting_approval'][0], m['still'][0]
        self.assertTrue(2.5 <= idle <= 8.0, m);self.assertTrue(4.0 <= working <= 10.0 and working > idle, m)
        self.assertTrue(1.0 <= waiting <= idle, m);self.assertEqual(still, 0.0, m)
        self.assertTrue(all(v[1] <= 0.02 for v in m.values()), 'the stage\'s brightness changes by 2 percent at most: ' + repr(m))

    def test_a_frame_costs_little(self):
        self.assertEqual(self.out['size'], [297, 396]);self.assertLess(self.out['paint_ms'], 3.0)

    def test_the_state_is_one_colour_on_her_base_and_her_cursor(self):
        for state, seen in self.out['states'].items():
            self.assertEqual(seen['word'], holo.look(state)[0], state)
            self.assertEqual(seen['cursor'], seen['role'], state);self.assertEqual(seen['base'], seen['role'], state)


class Absent(unittest.TestCase):
    def test_a_refused_mark_leaves_the_pane_as_it_was(self):
        self.assertIsNone(probe('kasandra', 1366, 768, 'hologram_absent', {'GRAPHITE_083_NO_MARKS': '1'})['hologram'])

    def test_graphite_has_no_hologram(self):
        self.assertIsNone(probe('graphite', 1366, 768, 'hologram_absent')['hologram'])


if __name__ == '__main__':
    unittest.main()
