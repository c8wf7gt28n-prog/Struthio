"""1.1 N1: Night is a phosphor monitor (Amber, Green), with CRT effects (Off, Subtle, Full).

The acceptance first: every text brightness of both phosphors is 4.5:1 or more on the ground it is laid on, and the setting
switches. Then the rest of the slice's truth: one hue, inverse video, the fixed-width chrome, the xterm's colours, and each
CRT effect off under Off and each moving one off under Reduce motion. Day is unchanged.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from workbench import design_tokens as dt  # noqa: E402
from workbench import night_phosphor as np_  # noqa: E402


def _lin(v):
    v /= 255.0;return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def luminance(colour):
    r, g, b = dt.rgb(colour);return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def ratio(a, b):
    x, y = sorted((luminance(a), luminance(b)));return (y + 0.05) / (x + 0.05)


def darker(colour, alpha):
    return dt.over((0, 0, 0, alpha), colour)


class Acceptance(unittest.TestCase):
    def test_every_text_brightness_of_both_phosphors_is_at_least_4_5_to_1_on_its_ground(self):
        for tone in dt.PHOSPHORS:
            c = dt.colours('night-' + tone)
            for ink, ground, where in dt.NIGHT_PAIRS:
                with self.subTest(phosphor=tone, ink=ink, ground=ground):
                    self.assertGreaterEqual(ratio(c[ink], c[ground]), 4.5, '%s %s on %s (%s)' % (tone, ink, ground, where))
            for ink in ('text', 'secondary', 'tertiary'):self.assertGreaterEqual(ratio(c[ink], c['window']), 6.0, (tone, ink))

    def test_the_setting_switches_between_amber_and_green(self):
        from workbench import boss_qt

        class Host:
            def __init__(self):
                self.session = type('S', (), {'state': {'appearance': 'day'}, 'save': lambda s: None})()
                self.said = []
                self.statusBar = lambda: type('B', (), {'showMessage': lambda b, words, ms=0: self.said.append(words)})()
        host = Host()
        self.assertTrue(boss_qt.choose_appearance(host, 'night', ask=False, phosphor='green'))
        self.assertEqual((host.session.state['appearance'], host.session.state['phosphor']), ('night', 'green'))
        self.assertIn('Night: Green', host.said[-1])
        self.assertTrue(boss_qt.choose_appearance(host, 'night', ask=False, phosphor='amber'))
        self.assertEqual(host.session.state['phosphor'], 'amber');self.assertEqual(boss_qt.chosen_phosphor(host), 'amber')
        self.assertFalse(boss_qt.choose_appearance(host, 'night', ask=False, phosphor='violet'), 'no third phosphor')
        self.assertTrue(boss_qt.choose_crt(host, 'full'));self.assertEqual(boss_qt.chosen_crt(host), 'full')
        self.assertFalse(boss_qt.choose_crt(host, 'max'))

    def test_the_look_in_force_follows_the_phosphor_asked_for(self):
        code = ('from workbench import boss_theme as t, design_tokens as d;'
                'print(t.APPEARANCE, t.PHOSPHOR, t.TEXT, t.GROUND, t.FACE, d.face(), t.CRT)')
        for env, said in (({'GRAPHITE_APPEARANCE': 'night-green'}, 'night green #33ff66 #0a0a08 IBM Plex Mono IBM Plex Mono subtle'),
                          ({'GRAPHITE_APPEARANCE': 'night', 'GRAPHITE_CRT': 'off'}, 'night amber #ffb000 #0a0a08 IBM Plex Mono IBM Plex Mono off'),
                          ({'GRAPHITE_APPEARANCE': 'day', 'GRAPHITE_PHOSPHOR': 'green'}, 'day  #1d1d1f #f5f5f7 Inter Inter subtle')):
            with tempfile.TemporaryDirectory() as home:
                run = dict(os.environ, HOME=home, XDG_CONFIG_HOME=home, **env);run.pop('ARC1_WORKBENCH_CONFIG_HOME', None)
                run.pop('GRAPHITE_PHOSPHOR', None) if 'GRAPHITE_PHOSPHOR' not in env else None
                out = subprocess.run([sys.executable, '-B', '-c', code], cwd=str(ROOT), env=run, capture_output=True, text=True, timeout=120)
                self.assertEqual(out.stdout.strip(), said, out.stderr[-800:])


class OnePhosphor(unittest.TestCase):
    def test_hierarchy_is_the_brightness_of_one_hue(self):
        for tone in dt.PHOSPHORS:
            c = dt.colours('night-' + tone);full = dt.PHOSPHOR_INK[tone][0]
            self.assertEqual(c['window'], dt.NIGHT_GROUND);self.assertEqual(c['text'], full)
            steps = [luminance(c[k]) for k in ('text', 'secondary', 'tertiary', 'disabled')]
            self.assertEqual(steps, sorted(steps, reverse=True), tone)
            for k in ('accent', 'live', 'waiting', 'danger', 'accent_fill'):self.assertEqual(c[k], full, (tone, k))      # no other hue
            for k in ('secondary', 'tertiary', 'disabled', 'surface', 'raised', 'recheck'):
                share = next(a for a in range(256) if dt.over(full, dt.NIGHT_GROUND, a) == c[k])      # the phosphor over the ground
                self.assertLess(share, 256, (tone, k))

    def test_selected_row_pressed_button_active_window_and_halt_are_inverse_video(self):
        for tone in dt.PHOSPHORS:
            c = dt.colours('night-' + tone)
            self.assertEqual((c['active_plate'], c['on_active']), (c['text'], dt.NIGHT_GROUND))
            self.assertEqual(dt.marks('night-' + tone)['HALT'], c['text'])
        sheet = dt.sheet('night')
        self.assertIn('QTreeView::item:selected, QListView::item:selected {background:%s; color:%s;}' % (dt.colours('night')['accent_fill'], dt.NIGHT_GROUND), sheet)
        self.assertIn('QMenu::item:selected {background:%s; color:%s;' % (dt.colours('night')['accent_fill'], dt.NIGHT_GROUND), sheet)
        self.assertNotIn('QPushButton:pressed, QPushButton:checked', dt.sheet('day'), 'Day is unchanged')

    def test_the_chrome_is_fixed_width_in_night_and_day_is_unchanged(self):
        self.assertEqual(dt.face('night'), 'IBM Plex Mono');self.assertEqual(dt.face('night-green'), 'IBM Plex Mono');self.assertEqual(dt.face('day'), 'Inter')
        self.assertEqual(dt.palette('night-amber')['FACE'], 'IBM Plex Mono');self.assertEqual(dt.palette('day')['FACE'], 'Inter')
        self.assertIn('QWidget {font-family:"IBM Plex Mono";}', dt.sheet('night'))
        day = dt.colours('day')
        self.assertEqual((day['window'], day['text'], day['accent'], day['live'], day['active_plate']), ('#f5f5f7', '#1d1d1f', '#0a66d8', '#18773f', day['selection_side']))

    def test_the_drop_down_terminal_follows_the_phosphor(self):
        from workbench import real_terminal_qt
        for tone in dt.PHOSPHORS:
            look = 'night-' + tone;sixteen = real_terminal_qt.phosphor_colours(look);ground = dt.colours(look)['terminal']
            self.assertEqual(len(sixteen), 16)
            for n, colour in enumerate(sixteen[1:], 1):self.assertGreaterEqual(ratio(colour, ground), 4.5, (tone, n))

    def test_the_choice_is_read_from_the_session_and_a_damaged_one_is_amber_and_subtle(self):
        with tempfile.TemporaryDirectory() as home:
            path = os.path.join(home, 'session.json');env = {}
            self.assertEqual((np_.chosen_phosphor(env, path), np_.chosen_crt(env, path)), ('amber', 'subtle'), 'no file: the defaults')
            for saved, said in (({'phosphor': 'green', 'crt': 'full'}, ('green', 'full')), ({'phosphor': ['green'], 'crt': 7}, ('amber', 'subtle'))):
                Path(path).write_text(json.dumps(saved), encoding='utf-8')
                self.assertEqual((np_.chosen_phosphor(env, path), np_.chosen_crt(env, path)), said)
            self.assertEqual(np_.chosen_phosphor({'GRAPHITE_PHOSPHOR': 'amber'}, path), 'amber', 'the environment wins')


class CrtEffects(unittest.TestCase):
    def test_each_effect_is_off_under_off_and_each_moving_one_under_reduce_motion(self):
        from workbench import crt_qt
        off = crt_qt.effects('off')
        self.assertFalse(any(off.values()), off)
        self.assertFalse(any(crt_qt.effects('full', night=False).values()), 'nothing outside Night')
        for level in ('subtle', 'full'):
            on, still = crt_qt.effects(level), crt_qt.effects(level, reduce_motion=True)
            for name in crt_qt.MOVING:self.assertTrue(on[name], (level, name));self.assertFalse(still[name], (level, name, 'Reduce motion'))
            for name in ('burn_in', 'scanlines', 'block_cursor'):self.assertTrue(still[name], (level, name, 'still: it does not move'))
        full, subtle = crt_qt.effects('full'), crt_qt.effects('subtle')
        self.assertTrue(full['vignette'] and full['bloom']);self.assertFalse(subtle['vignette'] or subtle['bloom'])
        self.assertTrue(120 <= full['afterglow'] <= 200);self.assertTrue(full['warm_up'] <= 450)
        for level in ('subtle', 'full'):self.assertTrue(8 <= crt_qt.BURN[level] <= 16, '3 to 6 % of the phosphor')

    def test_the_effects_never_cost_legibility(self):
        from workbench import crt_qt
        full = crt_qt.effects('full')
        for tone in dt.PHOSPHORS:
            c = dt.colours('night-' + tone)
            for ink, ground, _ in dt.NIGHT_PAIRS:      # under the scanline and the vignette's very corner, both laid at once
                shade = full['scanlines'] + full['vignette']
                self.assertGreaterEqual(ratio(darker(c[ink], shade), darker(c[ground], shade)), 4.5, (tone, ink, ground))
            ghost = dt.over(c['text'], c['surface'], crt_qt.BURN['full'])      # the burn-in lifts only what is darker than it
            for ink in ('text', 'secondary', 'tertiary'):self.assertGreaterEqual(ratio(c[ink], ghost), 4.5, (tone, ink))

    def test_the_screen_and_the_line_switch_off(self):
        from PySide6.QtWidgets import QApplication, QLineEdit, QWidget
        from workbench import crt_qt
        app = QApplication.instance() or QApplication([])
        window = QWidget();window.resize(400, 300)
        screen = crt_qt.Screen(window, 'window', crt_qt.effects('off'));self.assertFalse(screen.isVisibleTo(window))
        self.assertFalse(screen.warm_up(), 'no warm-up under Off')
        screen.set_effects(crt_qt.effects('full', reduce_motion=True));self.assertTrue(screen.isVisibleTo(window))
        self.assertFalse(screen.warm_up(), 'no warm-up under Reduce motion')
        self.assertIsNotNone(screen.burnt());self.assertIsNotNone(screen.vignette())
        screen.set_effects(crt_qt.effects('full'));self.assertTrue(screen.warm_up())
        edit = QLineEdit(window);still = crt_qt.Persistence(edit, crt_qt.effects('subtle', reduce_motion=True))
        self.assertFalse(still.blink.isActive(), 'a steady cursor under Reduce motion')
        edit.setText('READY.');self.assertIsNone(still.ghost, 'no afterglow under Reduce motion')
        moving = crt_qt.Persistence(QLineEdit(window), crt_qt.effects('subtle'));self.assertTrue(moving.blink.isActive())
        window.deleteLater();app.processEvents()


if __name__ == '__main__':
    unittest.main()
