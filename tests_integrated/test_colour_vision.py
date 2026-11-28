"""0.8.4: the colour-vision check (tools/colour_vision.py).

Every colour that carries a meaning also has a word or a shape. This asks it of every look's palette: each pair of meaning
colours is taken as weak red (protan) and weak green (deutan) sight take it (Machado, Oliveira and Fernandes 2009, at
severity 0.6 and 1.0), their difference is measured (CIEDE2000), and a pair under the threshold must be in the reviewed
table of what tells the two apart on screen. No window is made: the palettes, the published matrices and arithmetic.
"""
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import colour_vision  # noqa: E402

from workbench import boss_theme  # noqa: E402

LOOKS = tuple(boss_theme.PALETTES)


class TheMeasure(unittest.TestCase):
    def test_ciede2000_gives_the_published_differences(self):
        # Sharma, Wu and Dalal (2005), their test data: pairs 1, 2, 3 and 17 to 20 (CIELAB one, CIELAB two, the difference).
        for one, two, said in (((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425), ((50.0, 3.1571, -77.2803), (50.0, 0.0, -82.7485), 2.8615),
                               ((50.0, -1.3802, -84.2814), (50.0, 0.0, -82.7485), 1.0000), ((50.0, 2.5, 0.0), (73.0, 25.0, -18.0), 27.1492),
                               ((50.0, 2.5, 0.0), (61.0, -5.0, 29.0), 22.8977), ((50.0, 2.5, 0.0), (56.0, -27.0, -3.0), 31.9030), ((50.0, 2.5, 0.0), (58.0, 24.0, 15.0), 19.4535)):
            self.assertAlmostEqual(colour_vision.ciede2000(one, two), said, places=4, msg=str((one, two)))
            self.assertAlmostEqual(colour_vision.ciede2000(two, one), said, places=4, msg='the same either way round')
        self.assertEqual(colour_vision.difference('#83eaff', '#83eaff'), 0.0)
        white = colour_vision.lab('#ffffff');self.assertAlmostEqual(white[0], 100.0, places=3);self.assertLess(abs(white[1]) + abs(white[2]), 0.001)
        self.assertAlmostEqual(colour_vision.lab('#000000')[0], 0.0, places=6)

    def test_the_matrices_keep_white_and_grey_and_take_red_from_green_as_those_eyes_do(self):
        self.assertEqual(sorted(colour_vision.MACHADO), [('deutan', 0.6), ('deutan', 1.0), ('protan', 0.6), ('protan', 1.0)])
        for key, matrix in colour_vision.MACHADO.items():
            for row in matrix:self.assertAlmostEqual(sum(row), 1.0, places=5, msg=str(key))      # white stays white
            for grey in ('#ffffff', '#808080', '#202020', '#000000'):
                seen = colour_vision.simulate(grey, *key);self.assertLessEqual(max(abs(int(seen[i:i + 2], 16) - int(grey[i:i + 2], 16)) for i in (1, 3, 5)), 1, (key, grey, seen))
        self.assertEqual(colour_vision.simulate('#E2A72E'), '#e2a72e');self.assertEqual(colour_vision.simulate('#e2a72e', 'protan', 0), '#e2a72e')
        red, green = '#e02020', '#20a020'      # a red and a green of like lightness: far apart to full sight
        apart = lambda sight, severity: colour_vision.difference(colour_vision.simulate(red, sight, severity), colour_vision.simulate(green, sight, severity))
        full = colour_vision.difference(red, green);self.assertGreater(full, 60)
        for sight in ('protan', 'deutan'):
            self.assertLess(apart(sight, 0.6), full, sight);self.assertLess(apart(sight, 1.0), apart(sight, 0.6), sight + ': the weaker the cone, the nearer they come')
            self.assertLess(apart(sight, 1.0), full / 2, sight)
        dark = colour_vision.lab(colour_vision.simulate('#ff0000', 'protan', 1.0))[0]
        self.assertLess(dark, colour_vision.lab('#ff0000')[0] - 10, 'to weak red sight a red is dark')
        self.assertGreater(colour_vision.lab(colour_vision.simulate('#ff0000', 'deutan', 1.0))[0], dark, 'to weak green sight it is not')


class EveryLook(unittest.TestCase):
    def test_every_meaning_has_a_colour_in_every_palette_and_a_sign_of_its_own(self):
        self.assertEqual(set(colour_vision.MEANINGS), set(colour_vision.SIGNS));self.assertGreaterEqual(len(colour_vision.MEANINGS), 12)
        for meaning, (names, says) in colour_vision.MEANINGS.items():
            for look in LOOKS:
                worn = colour_vision.colours_of(meaning, look, boss_theme.PALETTES[look]);self.assertEqual(len(worn), len(names), (look, meaning))
                for colour in worn:self.assertRegex(colour, r'^#[0-9a-f]{6}$', (look, meaning))
            sign, where = colour_vision.SIGNS[meaning];self.assertGreater(len(sign), 20, meaning);self.assertGreater(len(where), 8, meaning);self.assertTrue(says)
        signs = [sign for sign, _ in colour_vision.SIGNS.values()];self.assertEqual(len(set(signs)), len(signs), 'no two meanings share one sign')
        for meaning in ('chosen', 'ready', 'waits', 'fails', 'recheck', 'stopped', 'held', 'cue'):self.assertIn(meaning, colour_vision.MEANINGS)
        # 0.8.4's review: what is chosen is also the menu's bar, what is ready also the pointer's halo (pale violet in her look)
        self.assertIn('BAR', colour_vision.MEANINGS['chosen'][0]);self.assertEqual(colour_vision.MEANINGS['cue'][0], ('CUE_EDGE',))
        hers, his = boss_theme.PALETTES['kasandra'], boss_theme.PALETTES['graphite']
        self.assertEqual(colour_vision.colours_of('ready', 'kasandra', hers), [hers['READY'], hers['VIOLET_PALE']])
        self.assertEqual(colour_vision.colours_of('ready', 'graphite', his), [his['READY'], his['READY']])

    def test_every_pair_under_the_threshold_is_told_apart_by_a_reviewed_word_or_shape(self):
        self.assertEqual(colour_vision.THRESHOLD, 10.0);self.assertEqual(set(colour_vision.REVIEWED), set(LOOKS), 'every look is checked')
        for look in LOOKS:
            with self.subTest(look=look):
                rows = colour_vision.table(look);self.assertEqual(len(rows), len(colour_vision.MEANINGS) * (len(colour_vision.MEANINGS) - 1) // 2)
                for row in rows:self.assertEqual(set(row['seen']), {'full', 'weak red 0.6', 'weak red 1.0', 'weak green 0.6', 'weak green 1.0'})
                left = ['%s / %s: %s and %s are %.1f apart in %s' % (*row['pair'], *row['colours'], row['least'], row['sight']) for row in colour_vision.unreviewed(look)]
                self.assertEqual(left, [], 'give the pair a word or a shape on screen, then say so in tools/colour_vision.REVIEWED; do not move the colour to pass')
                close = {frozenset(row['pair']) for row in rows if row['least'] < colour_vision.THRESHOLD}
                listed = {frozenset(pair) for pair in colour_vision.REVIEWED[look]}
                self.assertEqual(listed - close, set(), 'the table lists only pairs that are close today')
                for pair, by in colour_vision.REVIEWED[look].items():
                    self.assertEqual(len(set(pair)), 2);self.assertGreater(len(by), 40, pair)
                    self.assertTrue(any(mark in by for mark in ('"', 'square', 'edge', 'curve', 'bar', 'cross', 'DELETE', 'capitals', 'name', 'words')), (pair, 'names a word or a shape'))

    def test_what_the_two_looks_leave_to_the_sign(self):
        # The findings, pinned: Graphite has one amber for five meanings; to weak red sight Kasandra's cyan is her plain ink.
        close = lambda look: {row['pair']: row for row in colour_vision.table(look) if row['least'] < colour_vision.THRESHOLD}
        g, k = close('graphite'), close('kasandra')
        self.assertEqual(len(g), 32);self.assertEqual(len(k), 15)
        self.assertEqual(sum(row['seen']['full'] == 0.0 for row in g.values()), 16, 'Kas: fifteen pairs of its one amber (the cue too), and its quiet ink')
        hers = boss_theme.PALETTES['kasandra'];self.assertGreater(colour_vision.difference(hers['READY'], hers['TEXT']), 20)
        ready = k[('ready', 'words')];self.assertLess(ready['seen']['weak red 1.0'], 2.0);self.assertEqual(ready['sight'], 'weak red 1.0')
        self.assertEqual(k[('ready', 'cue')]['least'], 0.0, 'her cue is her old cyan, the colour of what is ready')
        self.assertEqual(k[('ready', 'recheck')]['colours'], (hers['VIOLET_PALE'], hers['RECHECK']), 'the pointer\'s halo is the nearer of her two')
        self.assertNotIn(('chosen', 'ready'), k, 'her yellow and her cyan stay apart in every sight');self.assertIn(('chosen', 'ready'), g)
        self.assertNotIn(('chosen', 'waits'), k, 'and so do her yellow and her pink, which Kas gives one amber');self.assertEqual(g[('chosen', 'waits')]['least'], 0.0)

    def test_a_palette_that_moves_two_meanings_together_or_a_meaning_with_no_sign_fails(self):
        hers = dict(boss_theme.PALETTES['kasandra']);self.assertEqual(colour_vision.unreviewed('kasandra', hers), [])
        moved = dict(hers, HONEY=hers['RECHECK'])      # hers in the colour of a recheck: nobody has looked at that pair
        self.assertEqual([row['pair'] for row in colour_vision.unreviewed('kasandra', moved) if row['least'] == 0.0], [('recheck', 'hers')])
        near = dict(hers, RED='#f04a70')               # red a step from her pink: close in full sight too, and reviewed (their words differ)
        barred = dict(hers, BAR=hers['RECHECK'])       # the menu's bar is what is chosen too: moved onto a recheck's colour, it is seen
        self.assertEqual([row['pair'] for row in colour_vision.unreviewed('kasandra', barred) if row['least'] == 0.0], [('chosen', 'recheck')])
        self.assertNotIn(('waits', 'stopped'), [row['pair'] for row in colour_vision.unreviewed('kasandra', near)])
        with patch.dict(colour_vision.SIGNS, clear=False) as signs:
            del signs['waits']
            self.assertIn(('waits', 'fails'), [row['pair'] for row in colour_vision.unreviewed('kasandra')], 'reviewed, but one of the two has no sign any more')
        with patch.dict(colour_vision.SIGNS, {'fails': colour_vision.SIGNS['waits']}):
            self.assertIn(('waits', 'fails'), [row['pair'] for row in colour_vision.unreviewed('kasandra')], 'one sign for both tells nothing apart')

    def test_the_tool_prints_both_looks_and_says_when_a_pair_is_left(self):
        done = subprocess.run([sys.executable, '-B', str(ROOT / 'tools' / 'colour_vision.py')], cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout[-2000:] + done.stderr[-2000:])
        for words in ('graphite: 13 meanings, 78 pairs', 'kasandra: 13 meanings, 78 pairs', 'ready / words', 'told apart by:', 'COLOUR VISION: 0 pairs under 10 not reviewed'):
            self.assertIn(words, done.stdout)
        self.assertNotIn('NOT REVIEWED', done.stdout)
        with patch.dict(colour_vision.REVIEWED, {'kasandra': {}}):
            self.assertEqual(len(colour_vision.unreviewed('kasandra')), 15);self.assertIn('NOT REVIEWED', '\n'.join(colour_vision.printed('kasandra')))


if __name__ == '__main__':
    unittest.main()
