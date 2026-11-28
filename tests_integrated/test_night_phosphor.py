"""1.1 N1: Night is a phosphor monitor (Amber, Green), with CRT effects (Off, Subtle, Full). 1.1 N1duo: Night: Duo, green
for the computer, amber for Kas and the owner's word, grey for the past, is the default Night (class Duo, the acceptance).

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
                          ({'GRAPHITE_APPEARANCE': 'night', 'GRAPHITE_CRT': 'off'}, 'night duo #33ff66 #0a0a08 IBM Plex Mono IBM Plex Mono off'),      # N1duo: Duo
                          ({'GRAPHITE_APPEARANCE': 'night-amber'}, 'night amber #ffb000 #0a0a08 IBM Plex Mono IBM Plex Mono subtle'),
                          ({'GRAPHITE_APPEARANCE': 'day', 'GRAPHITE_PHOSPHOR': 'green'}, 'day  #1d1d1f #f5f5f7 Inter Inter subtle')):
            with tempfile.TemporaryDirectory() as home:
                run = dict(os.environ, HOME=home, XDG_CONFIG_HOME=home, **env);run.pop('ARC1_WORKBENCH_CONFIG_HOME', None)
                run.pop('GRAPHITE_PHOSPHOR', None) if 'GRAPHITE_PHOSPHOR' not in env else None
                out = subprocess.run([sys.executable, '-B', '-c', code], cwd=str(ROOT), env=run, capture_output=True, text=True, timeout=120)
                self.assertEqual(out.stdout.strip(), said, out.stderr[-800:])


class OnePhosphor(unittest.TestCase):
    def test_hierarchy_is_the_brightness_of_one_hue(self):
        for tone in dt.MONO_PHOSPHORS:      # N1duo: Amber and Green; Duo has two phosphors and a grey (class Duo)
            c = dt.colours('night-' + tone);full = dt.PHOSPHOR_INK[tone][0]
            self.assertEqual(c['window'], dt.NIGHT_GROUND);self.assertEqual(c['text'], full)
            steps = [luminance(c[k]) for k in ('text', 'secondary', 'tertiary', 'disabled')]
            self.assertEqual(steps, sorted(steps, reverse=True), tone)
            for k in ('accent', 'live', 'waiting', 'danger', 'accent_fill'):self.assertEqual(c[k], full, (tone, k))      # no other hue
            for k in ('secondary', 'tertiary', 'disabled', 'surface', 'raised', 'recheck'):
                share = next(a for a in range(256) if dt.over(full, dt.NIGHT_GROUND, a) == c[k])      # the phosphor over the ground
                self.assertLess(share, 256, (tone, k))

    def test_selected_row_pressed_button_active_window_and_halt_are_inverse_video(self):
        for tone in dt.MONO_PHOSPHORS:      # N1duo: Duo's block is amber, not its words' green (class Duo)
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

    def test_the_choice_is_read_from_the_session_and_a_damaged_one_is_duo_and_subtle(self):      # N1duo: Duo is the default
        with tempfile.TemporaryDirectory() as home:
            path = os.path.join(home, 'session.json');env = {}
            self.assertEqual((np_.chosen_phosphor(env, path), np_.chosen_crt(env, path)), ('duo', 'subtle'), 'no file: the defaults')
            for saved, said in (({'phosphor': 'green', 'crt': 'full'}, ('green', 'full')), ({'phosphor': ['green'], 'crt': 7}, ('duo', 'subtle')), ({'phosphor': 'amber'}, ('amber', 'subtle'))):
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
        for level in ('subtle', 'full'):self.assertTrue(8 <= crt_qt.BURN[level] <= 24, '3 to 9 % of the phosphor (the owner, after 1.1.4: more burnt grey)')

    def test_the_effects_never_cost_legibility(self):
        from workbench import crt_qt
        full = crt_qt.effects('full')
        for tone in dt.PHOSPHORS:
            c = dt.colours('night-' + tone)
            for ink, ground, _ in dt.NIGHT_PAIRS:      # under the scanline and the vignette's very corner, both laid at once
                shade = full['scanlines'] + full['vignette']
                self.assertGreaterEqual(ratio(darker(c[ink], shade), darker(c[ground], shade)), 4.5, (tone, ink, ground))
            ghost = dt.over(c['burn'], c['surface'], crt_qt.BURN['full'])      # the burn-in lifts only what is darker than it (N1duo: its own colour)
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


class Duo(unittest.TestCase):
    """1.1 N1duo, the acceptance: Duo is the default; Kas's chip and HALT read amber; a list row reads green; the burn-in reads
    grey; and each of them 4.5:1 or more on its ground."""
    GREEN, AMBER, GREY = dt.DUO_INK['computer'], dt.DUO_INK['kas'], dt.DUO_INK['past']

    def test_duo_is_the_default_night_and_amber_and_green_stay_choices(self):
        self.assertEqual((dt.PHOSPHOR_DEFAULT, np_.PHOSPHOR_DEFAULT), ('duo', 'duo'))
        self.assertEqual(np_.PHOSPHORS, (('duo', 'Night: Duo'), ('amber', 'Night: Amber'), ('green', 'Night: Green'), ('paper', 'Night: Paper')))      # 1.1 HX: Paper, a fourth
        with tempfile.TemporaryDirectory() as home:
            self.assertEqual(np_.chosen_phosphor({}, os.path.join(home, 'none.json')), 'duo')
        self.assertEqual(np_.chosen_phosphor({'GRAPHITE_APPEARANCE': 'night-duo'}, '/nonexistent'), 'duo')
        self.assertEqual(dt.look_of('night-duo'), 'night');self.assertEqual(dt.phosphor('night-duo'), 'duo')
        from workbench import boss_qt
        self.assertIn('night-duo', boss_qt.APPEARANCE_WORDS)

    def test_kas_chip_her_cards_and_halt_read_amber(self):
        from workbench import kas_panel_qt
        c = dt.colours('night-duo')
        self.assertEqual((c['kas_text'], c['waiting'], c['accent_fill'], c['active_plate'], c['on_accent']), (self.AMBER,) * 4 + (dt.NIGHT_GROUND,))
        for state in ('working', 'awaiting_approval', 'completed', 'blocked', 'held'):
            self.assertEqual(kas_panel_qt.shape_colour(state, c), self.AMBER, state)      # the shape, not the colour, says the state
        self.assertEqual(dt.marks('night-duo')['HALT'], self.AMBER);self.assertEqual(dt.palette('night-duo')['AMBER_EDGE'], self.AMBER)
        for ink in ('kas_text', 'kas_quiet'):
            for ground in ('window', 'sidebar', 'kas_ground', 'waiting_tint'):self.assertGreaterEqual(ratio(c[ink], c[ground]), 4.5, (ink, ground))
        self.assertGreaterEqual(ratio(c['on_accent'], c['accent_fill']), 4.5, 'HALT and the selected row: inverse video in amber')
        from workbench import night_duo      # her column, through her tube: its words amber, the grey of the past its own
        theme = type('Theme', (), dict(PHOSPHOR='duo', TEXT=self.GREEN, FAINT=self.GREY, LAUNCH=True))
        tube = night_duo.her_theme(theme);self.assertEqual((tube.TEXT, tube.READY, tube.FAINT, tube.LAUNCH), (self.AMBER, self.AMBER, self.GREY, True))
        day_theme = type('Theme', (), dict(PHOSPHOR=''));self.assertIs(night_duo.her_theme(day_theme), day_theme)
        from PySide6.QtWidgets import QApplication, QLabel, QWidget
        app = QApplication.instance() or QApplication([])
        panel = QWidget();words = QLabel('ACTIVE WORK', panel);words.setStyleSheet('font-size:12px;color:%s;' % self.GREEN);words.setProperty('herInk', words.styleSheet())
        self.assertEqual(night_duo.amber_words(panel, dt.colours('day')), 0, 'nothing outside Duo')
        self.assertEqual(night_duo.amber_words(panel, c), 1);self.assertIn(self.AMBER, words.styleSheet());self.assertIn(self.AMBER, words.property('herInk'))
        panel.deleteLater();app.processEvents()
        day = dt.colours('day');self.assertEqual((day['kas_text'], day['halt']), (day['text'], day['live']), 'Day is unchanged')
        self.assertEqual(kas_panel_qt.shape_colour('working', day), day['live'])

    def test_a_list_row_the_terminal_and_the_meters_read_green(self):
        from workbench import real_terminal_qt
        c = dt.colours('night-duo');sheet = dt.sheet('night-duo')
        self.assertEqual((c['text'], c['live']), (self.GREEN, self.GREEN));self.assertIn('QWidget {color:%s;}' % self.GREEN, sheet)
        self.assertIn('QTreeView::item:selected, QListView::item:selected {background:%s; color:%s;}' % (self.AMBER, dt.NIGHT_GROUND), sheet)
        self.assertIn('QProgressBar::chunk {background:%s;}' % self.GREEN, sheet)
        marks = dt.marks('night-duo');self.assertEqual((marks['EQ_MID'], marks['EQ_HIGH'], marks['EQ_HOT']), (self.GREEN, self.GREEN, self.AMBER))
        self.assertEqual(real_terminal_qt.phosphor_colours('night-duo')[7], self.GREEN)
        self.assertGreaterEqual(ratio(c['text'], c['window']), 14.0);self.assertGreaterEqual(ratio(c['secondary'], c['surface']), 4.5)

    def test_the_burn_in_disabled_tertiary_and_lines_read_grey_and_the_name_burnt_is_kas(self):
        from PySide6.QtWidgets import QApplication, QWidget
        from workbench import crt_qt
        c = dt.colours('night-duo')
        grey = lambda colour: max(dt.rgb(colour)) - min(dt.rgb(colour)) <= 12      # no hue: neither phosphor
        for key in ('burn', 'tertiary', 'disabled', 'hairline', 'stroke', 'stroke_strong', 'surface', 'raised'):self.assertTrue(grey(c[key]), (key, c[key]))
        self.assertEqual(c['burn'], self.GREY);self.assertGreaterEqual(ratio(c['tertiary'], c['pressed']), 4.5)
        ghost = dt.over(c['burn'], c['surface'], crt_qt.BURN['full'])
        for ink in ('text', 'secondary', 'tertiary', 'kas_text'):self.assertGreaterEqual(ratio(c[ink], ghost), 4.5, ink)
        self.assertEqual(crt_qt.BURN_NAME, 'kas', 'the centre burns the public name, one constant')
        self.assertFalse(any('GRAPHITE' in row.upper() for row in crt_qt.OLD_LISTING))
        self.assertNotIn("'GRAPHITE'", (ROOT / 'workbench' / 'crt_qt.py').read_text(encoding='utf-8'), 'no old name burns')
        app = QApplication.instance() or QApplication([])
        window = QWidget();window.resize(640, 400)
        screen = crt_qt.Screen(window, 'window', crt_qt.effects('full'));self.assertEqual(screen.phosphor.name(), self.GREY)
        self.assertEqual(screen.line.name(), self.GREEN, 'the green tube warms up green');self.assertIsNotNone(screen.burnt())
        tube = crt_qt.Screen(window, 'kas', crt_qt.effects('subtle'))
        self.assertEqual((tube.line.name(), tube.ground.name()), (self.AMBER, c['kas_ground']), 'her tube: amber, its ground a shade warmer')
        self.assertIsNotNone(tube.burnt());self.assertTrue(crt_qt.KAS_TUBE_DELAY > 0)
        window.deleteLater();app.processEvents()


class HeroExtras(unittest.TestCase):
    """1.1 HX, the acceptance: the clock draws seven-segment digits in Night; her words type out, but at once under Reduce
    motion, CRT effects Off, a click or a card; the peak mark holds and falls slowly; Night: Paper's every text 4.5:1."""
    AMBER, GREEN, PAPER = dt.DUO_INK['kas'], dt.DUO_INK['computer'], dt.DUO_INK['paper']

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        from workbench import boss_theme
        cls.bt = boss_theme;cls.was = getattr(boss_theme, 'PHOSPHOR', '')

    def tearDown(self):
        self.bt.PHOSPHOR = self.was

    def lit(self, image, colour):
        from PySide6.QtGui import QColor
        want = QColor(colour).rgb() & 0xffffff
        return sum(1 for y in range(image.height()) for x in range(image.width()) if image.pixel(x, y) & 0xffffff == want)

    def test_the_clock_draws_seven_segment_digits_in_night_and_day_keeps_its_clock(self):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QColor, QImage, QPainter
        from PySide6.QtWidgets import QWidget
        from workbench import bar_qt, night_hero
        c = dt.colours('night-duo');image = QImage(120, 30, QImage.Format_RGB32);image.fill(QColor(c['window']))
        p = QPainter(image);box = night_hero.paint_clock(p, QRectF(0, 0, 120, 30), c, '14:05');p.end()
        self.assertGreater(self.lit(image, self.AMBER), 60, 'the digits are amber bars');self.assertGreater(box.height(), 10)
        unlit = dt.over(c['kas_text'], c['window'], night_hero.UNLIT);self.assertGreater(self.lit(image, unlit), 4, 'the unlit bars of 88:88')
        bar = QWidget();bar.resize(200, 44)
        self.bt.PHOSPHOR = 'duo';clock = bar_qt.BarClock(bar);clock.resize(clock.natural(44), 44);clock.grab()
        self.assertIsNotNone(getattr(clock, 'segments', None), 'Night: seven segments');self.assertGreaterEqual(clock.natural(44), night_hero.clock_width(44))
        self.assertIn(':', clock.accessibleName(), 'the time is said in words')
        self.bt.PHOSPHOR = '';day = bar_qt.BarClock(bar);day.resize(80, 44);day.grab()
        self.assertIsNone(getattr(day, 'segments', None), 'Day keeps its clock')
        bar.deleteLater();self.app.processEvents()

    def bubble(self, words='All checks run. Nothing waits for you.'):
        from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout
        b = QFrame();b.box = QVBoxLayout(b);b.text = QLabel(words);b.box.addWidget(b.text);b.mine = b.code = False;b.resize(300, 80)
        return b

    def face(self, fx):
        return type('Face', (), {'host': type('Host', (), {'crt_fx': fx})(), 'fold_earlier': lambda s: None})()

    def test_her_words_type_out_behind_a_block_cursor_and_a_click_shows_them_whole(self):
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from workbench import crt_qt, night_hero
        self.assertEqual(night_hero.TYPE_CPS, 600);self.assertAlmostEqual(night_hero.type_ms(60), 100.0)
        self.assertEqual(night_hero.type_ms(5000), 800.0, 'never longer than 0.8 s');self.assertEqual(night_hero.shown_at(5000, 800), 5000)
        self.assertEqual(night_hero.shown_at(600, 500), 375);self.assertEqual(night_hero.shown_at(600, 0), 0)
        self.bt.PHOSPHOR = 'duo';b = self.bubble();full = b.text.text()
        typing = night_hero.type_out(self.face(crt_qt.effects('subtle')), b)
        self.assertIsNotNone(typing);self.assertNotEqual(b.text.text(), full);self.assertIn(self.AMBER, b.text.text(), 'the amber block')
        typing.show(10, 50.0);self.assertIn(full[:10], b.text.text());self.assertIn('background', b.text.text(), 'the afterglow behind it')
        press = QMouseEvent(QEvent.MouseButtonPress, QPointF(5, 5), QPointF(5, 5), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        self.app.sendEvent(b.text, press)
        self.assertTrue(typing.done);self.assertEqual(b.text.text(), full);self.assertNotEqual(b.text.textFormat(), Qt.RichText)

    def test_typing_is_instant_under_reduce_motion_with_crt_off_and_outside_night(self):
        from workbench import crt_qt, night_hero
        self.bt.PHOSPHOR = 'duo'
        for fx in (crt_qt.effects('subtle', reduce_motion=True), crt_qt.effects('full', reduce_motion=True), crt_qt.effects('off')):
            b = self.bubble();full = b.text.text()
            self.assertIsNone(night_hero.type_out(self.face(fx), b), fx);self.assertEqual(b.text.text(), full)
        self.bt.PHOSPHOR = ''
        self.assertFalse(night_hero.typing_on(self.face(crt_qt.effects('subtle')).host), 'Day, Pencil, Indigo: at once')

    def test_a_card_that_waits_for_the_owners_press_appears_whole(self):
        from PySide6.QtWidgets import QPushButton
        from workbench import crt_qt, night_hero
        self.bt.PHOSPHOR = 'duo';b = self.bubble('Shall I move the two notes? Waits for you.');full = b.text.text()
        b.box.addWidget(QPushButton('Move them'))
        self.assertIsNone(night_hero.type_out(self.face(crt_qt.effects('full')), b));self.assertEqual(b.text.text(), full)
        late = self.bubble('A card whose buttons come after its words.');full = late.text.text()
        typing = night_hero.type_out(self.face(crt_qt.effects('full')), late);late.box.addWidget(QPushButton('Run'))
        typing.tick();self.assertTrue(typing.done);self.assertEqual(late.text.text(), full, 'a card is shown whole at once')

    def test_the_peak_mark_holds_the_last_few_seconds_then_falls_slowly(self):
        from workbench import night_hero as h
        mark = h.Peak();self.assertFalse(mark.feed(0.9, now=100.0))
        self.assertTrue(mark.feed(0.2, now=101.0));self.assertEqual(mark.value, 0.9)
        self.assertTrue(mark.feed(0.2, now=100.0 + h.PEAK_HOLD_S - 0.01));self.assertEqual(mark.value, 0.9, 'held')
        mark.feed(0.2, now=100.0 + h.PEAK_HOLD_S + 1.0);self.assertAlmostEqual(mark.value, 0.9 - h.PEAK_FALL, places=6)
        self.assertLessEqual(h.PEAK_FALL, 0.34, 'slowly');self.assertTrue(2.0 <= h.PEAK_HOLD_S <= 5.0, 'the last few seconds')
        mark.feed(0.2, now=200.0);self.assertEqual(mark.value, 0.2, 'never under the value now')
        self.assertFalse(mark.feed(0.95, now=200.1));self.assertEqual(mark.value, 0.95, 'a new high is taken at once')

    def test_in_duo_the_bars_are_green_and_the_peak_mark_amber(self):
        from PySide6.QtGui import QColor, QImage, QPainter
        from workbench import night_hero
        c = dt.colours('night-duo');marks = dt.marks('night-duo')
        self.assertEqual((c['peak'], marks['EQ_MID'], marks['EQ_HIGH']), (self.AMBER, self.GREEN, self.GREEN))
        self.assertEqual(dt.colours('night-green')['peak'], dt.colours('night-green')['text'], 'one hue in a single phosphor')
        q = dict(rest=QColor(c['raised']), mid=QColor(self.GREEN), hot=QColor(self.AMBER), peak=QColor(self.AMBER))
        image = QImage(100, 12, QImage.Format_RGB32);image.fill(QColor(c['window']));meter = type('M', (), {})()
        p = QPainter(image);night_hero.paint_meter_peak(p, meter, q, 0.7, 0, 100, 5);held = night_hero.paint_meter_peak(p, meter, q, 0.3, 0, 100, 5);p.end()
        self.assertEqual(held, 0.7, 'the mark holds the higher reading');self.assertGreater(self.lit(image, self.GREEN), 40)
        self.assertGreater(self.lit(image, self.AMBER), 6, 'the amber mark')

    def test_night_paper_is_a_fourth_choice_one_white_phosphor_every_text_4_5_to_1(self):
        from workbench import boss_qt
        self.assertIn(('paper', 'Night: Paper'), np_.PHOSPHORS);self.assertIn('night-paper', boss_qt.APPEARANCE_WORDS)
        self.assertEqual(np_.chosen_phosphor({'GRAPHITE_APPEARANCE': 'night-paper'}, '/nonexistent'), 'paper')
        self.assertEqual(dt.phosphor('night-paper'), 'paper');self.assertEqual(dt.look_of('night-paper'), 'night')
        c = dt.colours('night-paper');self.assertEqual((c['text'], c['accent'], c['peak'], c['kas_text']), (self.PAPER,) * 4)
        for ink, ground, where in dt.NIGHT_PAIRS:
            self.assertGreaterEqual(ratio(c[ink], c[ground]), 4.5, (ink, ground, where))
        steps = [luminance(c[k]) for k in ('text', 'secondary', 'tertiary', 'disabled')];self.assertEqual(steps, sorted(steps, reverse=True))
        self.assertGreater(steps[0], steps[1] * 1.15, 'brightness steps a reader can see')


if __name__ == '__main__':
    unittest.main()
