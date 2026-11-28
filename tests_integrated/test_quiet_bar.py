"""1.1 B5, a quieter bar (PLAN_1.1.md, B5): network, sound and power are one Quick Settings button.

Acceptance first: at 1366x768 three app windows fit on the bar beside Start, the line, Kas with HALT, Quick Settings and the
clock, nothing folded into "more"; one press opens one panel with network, sound, battery and the meters. Then: the button's
words and its fixed width, nothing the tray or the meters did is lost (each section's way to the Machine page, each meter's
card, bar.open_flyout for its callers), a second press closes it, the meters stay in the foot while the foot stays, the head
gives Apps up while the bar stands, and Start carries "Add an app to the list".

Offscreen, with the bar made and marked standing by hand; the readings are invented (test_bar's). Run alone:
python3 -B -m unittest -v tests_integrated.test_quiet_bar
"""
import os, tempfile, unittest
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QSlider, QWidget  # noqa: E402

APP = QApplication.instance() or QApplication([])

from tests_integrated.test_bar import readings, row  # noqa: E402
from tests_integrated.test_kas_bar import Host  # noqa: E402


def pump(n=6):
    for _ in range(n):APP.processEvents()


class QuietBar(unittest.TestCase):

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix='quietbar-')
        self.env = patch.dict(os.environ, {'XDG_CONFIG_HOME': os.path.join(self.home, 'config')});self.env.start()
        self.read = readings()
        self.patches = [patch('workbench.halt.held', return_value=False), patch('workbench.floor.gather', return_value=False),
                        patch('workbench.floor.column_soon', return_value=None),
                        patch('workbench.machine_real.read', side_effect=lambda key, bus=None: dict(self.read[key]))]
        for p in self.patches:p.start()
        from workbench import bar_qt, foot_fold_qt, halt_qt, kas_panel_qt, quick_settings_qt, start_qt
        self.b, self.q, self.ff = bar_qt, quick_settings_qt, foot_fold_qt
        self.host = Host(self.home);self.host.show()
        self.host.shell2.top.halt = halt_qt.HaltButton(self.host, self.host.shell2.top)
        self.ctl = kas_panel_qt.install(self.host)
        bar_qt.register_slot('start', start_qt.StartSlot);bar_qt.register_slot('line', start_qt.LineSlot)
        self.bar = bar_qt.Bar(self.host);self.bar.setFixedSize(1366, 40);self.bar.move(0, 728);self.bar.show()
        self.bar.standing = True;self.host.graphite_bar = self.bar;self.bar.arrange();pump()

    def tearDown(self):
        self.ctl.timer.stop()
        for fly in list(self.bar.flyouts.values()):fly.close()
        for name in self.b.SLOTS:self.b._FACTORIES.pop(name, None)
        self.bar.hide();self.bar.deleteLater();self.host._closing = True;self.host.hide();self.host.deleteLater()
        APP.sendPostedEvents(None, QEvent.DeferredDelete);pump(3)
        for p in self.patches:p.stop()
        self.env.stop()

    def tray(self, meters=True):
        if meters:self.b.register_slot('tray', self.ff.MetersTray);pump()
        tray = self.bar.slot('tray')
        for key in self.b.TRAY:tray.landed(key, self.read[key])
        return tray

    # ---- acceptance ---------------------------------------------------------------------------------------------------------
    def test_a_at_1366_three_app_windows_fit_beside_kas_halt_and_the_clock(self):
        self.tray()
        slot = self.bar.slot('windows');strip = slot.strip
        snap = dict(available=True, active=0x600002, windows=[row(0x600001, 'Notes.txt - Mousepad', 'Mousepad'),
                                                              row(0x600002, 'Invented Shop - Mozilla Firefox', 'Firefox', active=True),
                                                              row(0x600003, 'demo@box: ~/Files', 'XTerm')])
        strip.show_snapshot(snap);pump();self.bar.arrange();slot.lay();pump()
        entries = sorted((b for b in strip.buttons.values() if b.row is not None and b.isVisible()), key=lambda b: b.x())
        self.assertEqual(len(entries), 3, 'three app windows on the bar');self.assertEqual(strip.folded, [], 'none folded into more')
        self.assertFalse(strip.more.isVisible())
        self.assertTrue(all(b.width() >= 110 for b in entries), [b.width() for b in entries])      # each its title, readable
        kas = self.bar.slot('kas');self.assertIsInstance(kas, __import__('workbench.kas_panel_qt', fromlist=['KasSlot']).KasSlot)
        self.assertTrue(kas.halt.isVisible() and kas.halt.width() > 0, 'HALT beside her name')
        clock = self.bar.slot('clock').geometry();self.assertEqual(clock.right() + 1, 1366)
        self.assertLessEqual(entries[-1].mapTo(self.bar, entries[-1].rect().topRight()).x(), kas.geometry().left())
        self.assertLessEqual(self.bar.slot('tray').width(), 90, 'the tray is one button: three glyphs')

    def test_b_one_press_opens_network_sound_battery_and_the_meters(self):
        tray = self.tray();tray.button.click();pump()
        panel = tray.panel;self.assertIsNotNone(panel);self.assertTrue(panel.isVisible())
        self.assertEqual(list(panel.sections), ['network', 'sound', 'power', 'meters'])
        self.assertLessEqual(panel.geometry().bottom(), self.bar.geometry().top(), 'above the bar')
        self.assertGreaterEqual(panel.geometry().top(), 0, 'inside the screen')
        presses = [b.text() for b in panel.findChildren(QPushButton)]
        self.assertIn('Turn Wi-Fi off', presses);self.assertIn('Disconnect', presses)
        self.assertEqual(presses.count(self.b.MORE_WORDS), 3, 'each section its way to the Machine page')
        self.assertEqual(panel.findChildren(QSlider)[0].value(), 55)
        self.assertTrue(any('76 %' in w.text() for w in panel.sections['power'].findChildren(QLabel)))
        self.assertEqual(list(panel.sections['meters'].rows), list(self.ff.METER_KEYS))
        self.assertEqual(self.bar.open_key, self.q.PANEL_KEY)

    # ---- the rest ----------------------------------------------------------------------------------------------------------
    def test_the_button_says_every_word_in_its_tip_and_name_in_a_fixed_width(self):
        tray = self.tray();button = tray.button
        self.assertEqual(button.accessibleName(), 'Quick Settings: network Online, sound 55 %, power 76 %')
        tip = button.toolTip()
        for words in ('Network: connected (Wi-Fi Harbour Lane)', 'Sound: 55 % on Built-in speakers', 'Power: battery', 'Meters: CPU'):
            self.assertIn(words, tip)
        self.assertEqual([tray.items[k].glyph for k in self.b.TRAY], [('network', 'online'), ('sound', 55, False), ('power', 76, False, 'battery')])
        w = button.natural(40)
        tray.landed('power', dict(self.read['power'], available=False, why='UPower is not running', sampled_at=9e12))
        self.assertEqual(button.natural(40), w, 'nothing shifts');self.assertIn('power Unknown', button.accessibleName())
        self.assertGreater(button.natural(44), w)

    def test_nothing_the_tray_or_the_meters_did_is_lost(self):
        tray = self.tray()
        for key in self.b.TRAY:
            panel = tray.open_panel();pump()
            with patch.object(self.bar, 'open_machine', return_value=None) as whole:
                panel.more[key].click();pump()
            whole.assert_called_once_with(key)
        panel = tray.open_panel();pump()
        with patch('workbench.meter_cards.open_card', return_value=None) as card:
            panel.sections['meters'].rows['RAM'].click();pump()
        card.assert_called_once_with(self.host, tray.button, 'RAM')
        self.assertIs(self.ff.meters_item(self.host), tray.button, 'the meters\' cards open above Quick Settings')

    def test_bar_open_flyout_opens_the_one_panel_with_that_section_in_sight(self):
        tray = self.tray();panel = self.bar.open_flyout('sound');pump()
        self.assertIs(panel, tray.panel);self.assertEqual(list(panel.sections), ['network', 'sound', 'power', 'meters'])

    def test_a_second_press_closes_it_and_a_third_opens_it_again(self):
        tray = self.tray();tray.button.click();pump()
        tray.button.click();pump();self.assertIsNone(tray.panel);self.assertIsNone(self.bar.open_key)
        self.assertNotIn(self.q.PANEL_KEY, self.bar.flyouts)
        first = tray.open_panel();first.close();second = tray.open_panel()      # the old one goes after the new one opened
        APP.sendPostedEvents(None, QEvent.DeferredDelete);pump()
        self.assertIsNot(second, first);self.assertIs(self.bar.flyouts.get(self.q.PANEL_KEY), second);self.assertIs(tray.panel, second)

    def test_while_the_foot_stays_the_meters_stay_in_it(self):
        tray = self.tray(meters=False);self.assertIsInstance(tray, self.q.QuickTray);self.assertFalse(tray.with_meters)
        panel = tray.open_panel();pump()
        self.assertEqual(list(panel.sections), ['network', 'sound', 'power']);self.assertNotIn('Meters', tray.button.toolTip())

    def test_the_head_gives_apps_up_while_the_bar_stands(self):
        apps, plus = QWidget(), QWidget();apps.show();plus.show()
        top = SimpleNamespace(host=SimpleNamespace(graphite_bar=SimpleNamespace(standing=True)), programs=apps, apps_add=plus)
        self.assertTrue(self.q.head_free(top));self.assertFalse(apps.isVisible() or plus.isVisible())
        apps.show();top.host.graphite_bar.standing = False
        self.assertFalse(self.q.head_free(top));self.assertTrue(apps.isVisible(), 'without the bar the head keeps Apps')
        self.assertFalse(self.q.head_free(SimpleNamespace(host=SimpleNamespace(graphite_bar=None))))

    def test_start_carries_add_an_app_to_the_list(self):
        from workbench import apps_qt, start_qt
        panel = start_qt.StartPanel(self.host, 'start')
        try:
            self.assertEqual(panel.add_app.accessibleName(), apps_qt.ADD_WORDS)
            with patch.object(apps_qt.AddDialog, 'open', return_value=None):
                panel.show();pump();panel.add_app.click();pump()
            self.assertFalse(panel.isVisible(), 'Start closes; the dialog opens')
        finally:
            panel.close();panel.deleteLater()


if __name__ == '__main__':
    unittest.main()
