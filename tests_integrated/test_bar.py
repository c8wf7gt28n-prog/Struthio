"""1.1 B1, the bar (PLAN_1.1.md, B1): one bar along the bottom of the screen, above every app, in its own X window.

Acceptance first: the bar's height at both screen sizes and its strut at the bottom; the windows slot lists Graphite and two
app windows, marks the active one and a press brings one forward; the tray's Quick Settings (1.1 B5) opens above it with the
Machine page's own actions; register_slot fills a slot without editing bar_qt. Then the slots' order, the tray's words, the clock's
month, the toasts above the bar, the head's strip giving way, and why it does not stand where it should not.

Under Xvfb with the stand-in window manager the whole of it is the builder's smoke (it needs an X server, a window manager
and xterm); here it runs offscreen, the X reading given as a snapshot.

Run alone:  python3 -B -m unittest -v tests_integrated.test_bar
"""
import os, unittest
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QPushButton, QSlider, QWidget  # noqa: E402

APP = QApplication.instance() or QApplication([])


def pump(n=6):
    for _ in range(n):APP.processEvents()


def readings():
    """Invented readings of the three sections, shaped as machine_real gives them."""
    from workbench import machine_real as real
    net = dict(id='/wifi/0', ssid='Harbour Lane', strength=72, strength_word='good', security='WPA', active=True, saved=True, device='/dev/0')
    other = dict(net, id='/wifi/1', ssid='Corner Cafe', strength=40, strength_word='fair', security='open', active=False, saved=False)
    wifi = dict(id='/dev/0', kind='Wi-Fi', interface='wlan0', state='connected', state_number=100, networks=[net, other], active_ssid='Harbour Lane')
    return {
        'network': real.section('network', 'an invented NetworkManager', state='connected', state_number=70, enabled=True, wifi=True,
                                wifi_switch=True, devices=[wifi], wifi_devices=[wifi], short='connected (Wi-Fi Harbour Lane)'),
        'sound': real.section('sound', 'an invented wpctl', sinks=[dict(id='41', name='Built-in speakers', default=True)],
                              current=dict(id='41', name='Built-in speakers', default=True), percent=55, muted=False, short='55 %'),
        'power': real.section('power', 'an invented UPower', devices=[], on_battery=True, mains=[dict(name='', online=False)],
                              batteries=[dict(id='/bat0', kind='battery', supply=True, percent=76, state='discharging', online=False,
                                              to_empty=9000, to_full=0, name='Demo Cell')], short='battery 76 %, discharging'),
    }


def row(window, title, program, active=False, minimised=False):
    return dict(window=window, title=title, active=active, minimised=minimised, program=program, dialog=False, listed=True,
                graphite=False, klass=program, instance=program.lower(), protocols=())


class Host(QWidget):
    """A stand-in for Graphite's window: what the bar reads of it."""

    def __init__(self):
        super().__init__();self.setWindowTitle('Kas');self.resize(1366, 728)
        self.her_column = SimpleNamespace(shown_state='idle');self._closing = False


class TheBar(unittest.TestCase):

    def setUp(self):
        from workbench import bar_qt
        self.b = bar_qt;self.read = readings()
        self.patch = patch('workbench.machine_real.read', side_effect=lambda key, bus=None: dict(self.read[key]));self.patch.start()
        self.host = Host();self.bar = bar_qt.Bar(self.host)
        self.bar.setFixedSize(1366, 40);self.bar.move(0, 728);self.bar.show();self.bar.arrange();pump()

    def tearDown(self):
        for name in self.b.SLOTS:self.b._FACTORIES.pop(name, None)
        for fly in list(self.bar.flyouts.values()):fly.close()
        self.bar.hide();self.bar.deleteLater();self.host.deleteLater();pump(3);self.patch.stop()

    # ---- acceptance ---------------------------------------------------------------------------------------------------------
    def test_44_px_at_1920x1200_and_40_at_1366x768_and_its_strut_reserves_the_bottom(self):
        self.assertEqual(self.b.height_for(1920, 1200), 44);self.assertEqual(self.b.height_for(1366, 768), 40)
        strut, partial = self.b.strut_values(0, 1156, 1920, 44, 1200)
        self.assertEqual(strut, [0, 0, 0, 44]);self.assertEqual(partial, [0, 0, 0, 44, 0, 0, 0, 0, 0, 0, 0, 1919])
        strut, partial = self.b.strut_values(1920, 728, 1366, 40, 1200)      # a smaller second screen beside a taller first
        self.assertEqual(strut[3], 472);self.assertEqual(partial[10:], [1920, 3285]);self.assertEqual(partial[2], 0)

    def test_the_windows_slot_lists_graphite_and_two_app_windows_marks_the_active_and_a_press_brings_one_forward(self):
        slot = self.bar.slot('windows');strip = slot.strip
        snap = dict(available=True, active=0x600002, windows=[row(0x600001, 'demo@box: ~', 'XTerm'), row(0x600002, 'demo@box: /tmp', 'XTerm', active=True)])
        strip.show_snapshot(snap);pump();slot.lay();pump()
        entries = sorted((b for b in strip.buttons.values() if b.row is not None and b.isVisible()), key=lambda b: b.x())
        self.assertEqual([b.row['title'] for b in entries], ['demo@box: ~', 'demo@box: /tmp'])
        self.assertEqual([b.active for b in entries], [False, True])
        self.assertLess(slot.graphite.geometry().right(), slot.box.geometry().left())      # Graphite first
        self.assertIn('active', entries[1].accessibleName())
        with patch.object(strip.hub.watcher, 'activate', return_value=dict(asked=True, verified=True, how='_NET_ACTIVE_WINDOW')) as asked:
            entries[0].click();pump()
        asked.assert_called_once_with(0x600001)
        strip.show_snapshot(dict(snap, active=int(self.host.winId())));pump()
        self.assertTrue(slot.graphite.active)
        self.assertIn('Computer (active)', slot.words());self.assertEqual([r['program'] for r in strip.programs], ['XTerm', 'XTerm'])

    def test_the_trays_quick_settings_opens_the_three_sections_above_it_with_the_machine_pages_own_actions(self):
        tray = self.bar.slot('tray')      # 1.1 B5: one Quick Settings button, one panel with the three sections (was three flyouts)
        for key in self.b.TRAY:tray.landed(key, self.read[key])
        self.assertEqual([tray.items[k].word for k in self.b.TRAY], ['Online', '55 %', '76 %'])
        for key in self.b.TRAY:
            fly = self.bar.open_flyout(key, tray.button);pump()
            self.assertTrue(fly.isVisible(), key);self.assertEqual(sorted(fly.rooms), sorted(self.b.TRAY));self.assertEqual(self.bar.open_key, 'quick')
            self.assertLessEqual(fly.geometry().bottom(), self.bar.geometry().top(), key)      # above the bar
            presses = [b.text() for b in fly.findChildren(QPushButton)]
            self.assertIn(self.b.MORE_WORDS, presses)
            self.assertIn('Turn Wi-Fi off', presses);self.assertIn('Disconnect', presses)
            self.assertEqual(fly.findChildren(QSlider)[0].value(), 55)
            self.assertTrue(any('76 %' in w.text() for w in fly.findChildren(__import__('PySide6.QtWidgets', fromlist=['QLabel']).QLabel)))
            fly.close();pump()
            self.assertIsNone(self.bar.open_key)

    def test_register_slot_fills_a_slot_in_a_standing_bar_and_in_bars_made_later(self):
        class Chip(QWidget):
            def bar_width(self, h):return 150
        self.assertEqual(self.b.register_slot('kas', lambda bar: Chip(bar)), 'kas');pump()
        self.assertIsInstance(self.bar.slot('kas'), Chip);self.assertEqual(self.bar.slot('kas').width(), 150)
        later = self.b.Bar(self.host)
        try:self.assertIsInstance(later.slot('kas'), Chip)
        finally:later.deleteLater()
        self.b.register_slot('kas', None);pump()
        self.assertIsInstance(self.bar.slot('kas'), self.b.KasChip)

    # ---- the rest ----------------------------------------------------------------------------------------------------------
    def test_register_slot_refuses_a_slot_it_does_not_have_and_a_factory_that_is_not_callable(self):
        with self.assertRaises(ValueError):self.b.register_slot('programs', lambda bar: QWidget(bar))
        with self.assertRaises(TypeError):self.b.register_slot('line', 'a field')

    def test_a_factory_that_fails_leaves_the_slots_own_and_says_why(self):
        def broken(bar):raise RuntimeError('not today')
        self.b.register_slot('line', broken);pump()
        self.assertIsInstance(self.bar.slot('line'), self.b.LineField)
        self.assertIn('not today', self.bar.status()['slot_errors']['line'])

    def test_the_slots_stand_left_to_right_start_line_windows_kas_tray_clock(self):
        xs = [self.bar.slot(name).geometry() for name in self.b.SLOTS]
        self.assertEqual([g.left() for g in xs], sorted(g.left() for g in xs))
        self.assertEqual(xs[-1].right() + 1, 1366)      # the clock at the right end
        others = sum(g.width() for i, g in enumerate(xs) if self.b.SLOTS[i] != 'windows')
        self.assertGreater(xs[2].width(), 1366 - others - 60)      # the windows take what is left
        self.assertTrue(all(g.height() == 40 for g in xs))
        self.assertEqual(self.bar.status()['slots']['start'], 'StartButton')

    def test_the_trays_words_and_shapes_for_each_state(self):
        words = lambda key, **data: self.b.tray_words(key, dict(self.read[key], **data))
        self.assertEqual(words('network', state_number=20)[0], 'Offline');self.assertEqual(words('network', enabled=False)[2], ('network', 'off'))
        self.assertEqual(words('network', state_number=60)[0], 'Local only')
        self.assertEqual(words('sound', muted=True)[:1], ('Muted',));self.assertEqual(words('sound', muted=True)[2], ('sound', 55, True))
        self.assertEqual(words('sound', sinks=[])[0], 'No output')
        self.assertEqual(words('power', batteries=[], mains=[dict(name='', online=True)])[0], 'Mains')
        gone = self.b.tray_words('power', dict(available=False, why='Not available on this computer: UPower is not running'))
        self.assertEqual(gone[0], 'Unknown');self.assertIn('UPower is not running', gone[1])
        self.assertEqual(self.b.tray_words('sound', None)[0], '…')
        button = self.bar.slot('tray').button;w = button.natural(40)      # 1.1 B5: one button, a fixed width: nothing shifts
        for key in self.b.TRAY:
            self.bar.slot('tray').items[key].show_reading(dict(available=False, why='x'));self.assertEqual(button.natural(40), w)

    def test_the_clock_says_the_time_over_the_date_and_its_month_rises_above_the_bar(self):
        from workbench.dock_clock_qt import words
        clock = self.bar.slot('clock');clock_words = words()
        self.assertTrue(clock.accessibleName().startswith(clock_words[0]))
        month = clock.show_month();pump()
        try:
            self.assertTrue(month.isVisible());self.assertLessEqual(month.geometry().bottom(), self.bar.geometry().top())
        finally:month.close()

    def test_toasts_rise_above_the_bar_the_newest_lowest(self):
        from workbench import notify_qt
        class Toast:
            floating = True
            def __init__(self):self.at = None
            def fit(self, width):return 60
            def move(self, x, y):self.at = (x, y)
            def show(self):pass
            def raise_(self):pass
        shelf = notify_qt.Shelf(self.host, SimpleNamespace(notes=SimpleNamespace(listen=lambda fn: None)))
        old, new = Toast(), Toast();shelf.toasts = {1: old, 2: new};shelf.order = [1, 2]
        self.host.system_dock = self.bar;shelf.place()
        self.assertEqual(new.at[1] + 60, self.bar.geometry().top() - 12)
        self.assertLess(old.at[1], new.at[1])

    def test_the_heads_strip_gives_way_while_the_bar_is_in_sight(self):
        from workbench.windows_strip_qt import WindowStrip, slim
        head = WindowStrip(self.host);head.wanted = True
        self.assertEqual(head.room(1.0), slim(1.0))
        self.host.system_dock = self.bar;self.bar.standing = True
        self.assertEqual(head.room(1.0), 0)
        own = self.bar.slot('windows').strip;own.wanted = True
        self.assertEqual(own.room(1.0), slim(1.0))      # the bar's own strip is never told to give way
        head.deleteLater()

    def test_it_does_not_stand_offscreen_or_when_turned_off_and_says_why(self):
        stand, why = self.b.wanted({'GRAPHITE_BAR': '1'}, 'offscreen')
        self.assertFalse(stand);self.assertIn('not on an X display', why);self.assertIn('The bar does not stand', why)
        self.assertIn('GRAPHITE_BAR is off', self.b.wanted({'GRAPHITE_BAR': '0', 'ARC_LEDGER_XSESSION': '1'}, 'xcb')[1])
        self.assertFalse(self.b.wanted({'GRAPHITE_DOCK': '0', 'ARC_LEDGER_XSESSION': '1'}, 'xcb')[0])
        host = Host()
        try:
            self.assertIsNone(self.b.install(host));self.assertIsNone(host.system_dock)
            self.assertFalse(host.dock_status()['standing'])
        finally:host.deleteLater()

    def test_the_session_full_screen_becomes_maximised_above_the_bar(self):
        made = []
        host = SimpleNamespace(isFullScreen=lambda: True, showMaximized=lambda: made.append('maximised'),
                               a_fullscreen=SimpleNamespace(setChecked=lambda on: made.append(on)))
        self.assertTrue(self.b.leave_full_screen(host, {'ARC_LEDGER_FULLSCREEN': '1'}));self.assertEqual(made, ['maximised', False])
        self.assertFalse(self.b.leave_full_screen(host, {}))


if __name__ == '__main__':
    unittest.main()
