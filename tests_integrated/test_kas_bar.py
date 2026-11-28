"""1.1 B3, Kas on the bar (PLAN_1.1.md, B3): her chip with her state's word and shape, HALT beside her name, her panel
sliding from the right edge over any app, permission cards rising from her chip; her rules do not move.

Acceptance first: the chip's states; HALT on the bar is halt.press and nothing else, and the head's HALT goes; her panel is
the right column itself, 380 px at the right edge above the bar, closed by Esc; docked in Graphite or not; a card rises
from her chip with the same one press, never takes the keys and is deaf for its first half second; a Kernel refusal
reaches the owner in plain words and its raw text is kept in Log. Then the setting's file, the Pause key, the voice sweep.

Offscreen, with a stand-in window (the whole of it under Xvfb is the builder's smoke). Invented content only.

Run alone:  python3 -B -m unittest -v tests_integrated.test_kas_bar
"""
import json, os, tempfile, time, unittest
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QDockWidget, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget  # noqa: E402

APP = QApplication.instance() or QApplication([])


def pump(n=6, ms=0):
    for _ in range(n):
        APP.processEvents()
        if ms:QTest.qWait(ms)


GRANT = {'words': 'Grant this for this assignment', 'operation': 'grant.give', 'yours': True,
         'grant_words': 'move files inside “Downloads” in Files, for this assignment only',
         'arguments': {'operation': 'files.move', 'scope': 'assignment', 'assignment': 'a' * 32, 'expected_digest': 'd' * 64, 'step': 's2'},
         'then': {'operation': 'assignment.step', 'arguments': {'id': 'a' * 32, 'until': 'end'}}}
AUTHORISE = {'words': 'Authorise step 3', 'operation': 'assignment.plan', 'arguments': {'id': 'b' * 32, 'authorise': ['s3'], 'expected_digest': 'e' * 64}}


class Column:
    """A stand-in for her column: what the chip and the card read of it, and the presses they make through it."""

    def __init__(self, host):
        self.host = host;self.shown_state = 'idle';self.rows = [];self.waits = None;self.ask_line = None;self.steps = [];self.seen_held = False
        self.face = QWidget();self.said = []

    def compact(self):return False

    def take_step(self, step):
        self.steps.append(step);self.say_words('%s: done.' % step['call']['words'])

    def show_journal(self, ident):self.steps.append({'journal': ident})

    def say_words(self, words):self.said.append(words)


class Host(QMainWindow):
    """A stand-in for Graphite's window: a right dock holding the right pane, her column, the head's HALT."""

    def __init__(self, root):
        super().__init__();self.setWindowTitle('Kas');self.resize(1366, 728);self._closing = False;self.root = root
        self.setCentralWidget(QLabel('the work'))
        self.sim_dock = QDockWidget('Console Inspector', self);body = QWidget();lay = QVBoxLayout(body)
        lay.addWidget(QLabel('selection inspector'));self.right_pane = QWidget();self.right_pane.setObjectName('PaneBody')
        QVBoxLayout(self.right_pane).addWidget(QLabel('her column: WAITS FOR YOU, ACTIVE WORK, NEXT STEPS'))
        lay.addWidget(self.right_pane, 1);self.sim_dock.setWidget(body);self.addDockWidget(Qt.RightDockWidgetArea, self.sim_dock)
        self.her_column = Column(self);self.shown = []
        top = QWidget(self);self.shell2 = SimpleNamespace(top=top, show_slate_face=lambda: self.shown.append('slate'))


class KasOnTheBar(unittest.TestCase):

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix='kasbar-');self.env = patch.dict(os.environ, {'XDG_CONFIG_HOME': os.path.join(self.home, 'config')})
        self.env.start()
        self.patches = [patch('workbench.halt.held', return_value=False), patch('workbench.floor.gather', return_value=False),
                        patch('workbench.floor.column_soon', return_value=None), patch('workbench.windows_strip_qt.hub')]
        for p in self.patches:p.start()
        from workbench import bar_qt, halt_qt, kas_panel_qt
        self.b, self.k, self.hq = bar_qt, kas_panel_qt, halt_qt
        self.host = Host(self.home);self.host.show()
        self.head_halt = halt_qt.HaltButton(self.host, self.host.shell2.top);self.host.shell2.top.halt = self.head_halt
        self.ctl = kas_panel_qt.install(self.host)
        self.bar = bar_qt.Bar(self.host);self.bar.setFixedSize(1366, 40);self.bar.move(0, 728);self.bar.show()
        self.bar.standing = True;self.host.graphite_bar = self.bar;self.bar.arrange();pump()
        self.slot = self.bar.slot('kas')

    def tearDown(self):
        self.ctl.timer.stop()
        for w in (self.ctl.panel, self.ctl.card):
            if w is not None:w.hide();w.deleteLater()
        for name in self.b.SLOTS:self.b._FACTORIES.pop(name, None)
        self.bar.hide();self.bar.deleteLater();self.host._closing = True;self.host.hide();self.host.deleteLater()
        from PySide6.QtCore import QEvent
        APP.sendPostedEvents(None, QEvent.DeferredDelete);pump(3)      # no window of ours is left standing for the next test file
        for p in self.patches:p.stop()
        self.env.stop()

    # ---- acceptance ---------------------------------------------------------------------------------------------------------
    def test_her_chip_says_her_state_in_a_word_and_a_shape(self):
        self.assertIsInstance(self.slot, self.k.KasSlot)
        column = self.host.her_column;said = {}
        for state in ('idle', 'working', 'awaiting_approval', 'blocked', 'held', 'completed'):
            column.shown_state = state;said[state] = self.k.chip_state(column)[1:]
        self.assertEqual(said['idle'], ('QUIET', '○'));self.assertEqual(said['working'], ('WORKING', '●'))
        self.assertEqual(said['awaiting_approval'], ('NEEDS YOUR WORD', '◆'));self.assertEqual(said['blocked'], ('STOPPED', '▮▮'))
        self.assertEqual(said['held'], ('HELD', '‖'));self.assertEqual(said['completed'], ('DONE', '✓'))
        column.shown_state = 'awaiting_approval'
        self.assertEqual(self.k.chip_state(column, waiting=2)[1], 'NEEDS YOUR WORD [2]')
        column.shown_state = 'idle';quiet = self.slot.chip.natural(40);column.shown_state = 'awaiting_approval';self.slot.refresh();pump()
        self.assertGreater(self.slot.chip.natural(40), quiet);self.assertEqual(self.slot.width(), self.slot.bar_width(40))
        self.assertIn('NEEDS YOUR WORD', self.slot.chip.toolTip())

    def test_halt_stands_beside_her_name_and_its_press_is_halts_and_nothing_else(self):
        halt = self.slot.halt;pump()
        self.assertIsInstance(halt, self.hq.HaltButton);self.assertEqual(halt.focusPolicy(), Qt.NoFocus)
        self.assertEqual(halt.x(), self.slot.chip.width() + 2);self.assertEqual(halt.text(), 'HALT')
        width = halt.need(40)
        with patch('workbench.halt.press') as press, patch('workbench.halt.release') as release:
            halt.click();pump()
            press.assert_called_once();self.assertIs(press.call_args[0][0], self.host);release.assert_not_called()
            self.assertEqual(halt.text(), 'RESUME');self.assertEqual(halt.need(40), width)      # nothing on the bar moves
            halt.busy = False;halt.click();pump()
            release.assert_called_once();self.assertEqual(press.call_count, 1)      # RESUME lifts the hold; it restarts nothing itself

    def test_the_heads_halt_goes_once_halt_stands_on_the_bar(self):
        self.assertTrue(self.ctl.adopt_halt());pump()
        top = self.host.shell2.top
        self.assertIs(top.halt, self.slot.halt);self.assertTrue(self.ctl.status()['halt_on_bar'])
        before = self.slot.halt.geometry()
        self.hq.place_head(top, SimpleNamespace(scale=1.0, band=40, inset=8, pane=300))      # the head's placement leaves it on the bar
        self.assertEqual(self.slot.halt.geometry(), before);self.assertIs(self.slot.halt.parentWidget(), self.slot)

    def test_her_panel_is_her_column_380_px_at_the_right_edge_above_the_bar_and_esc_closes_it(self):
        pane = self.host.right_pane;holder = pane.parentWidget();index = holder.layout().indexOf(pane)
        with patch.object(self.k, 'reduce_motion', return_value=True), patch.object(self.k.KasBar, 'graphite_in_front', return_value=False):
            rect = self.ctl.toggle();pump()
            panel = self.ctl.panel
            self.assertTrue(self.ctl.panel_open());self.assertIs(pane.parentWidget(), panel)      # the very same widgets
            screen = self.host.screen().geometry()
            self.assertEqual(panel.width(), 380);self.assertEqual(panel.x() + panel.width(), screen.x() + screen.width())
            self.assertEqual(panel.y(), screen.y());self.assertEqual(panel.y() + panel.height(), self.bar.y())      # top of the screen to the bar
            self.assertTrue(panel.windowFlags() & Qt.WindowStaysOnTopHint);self.assertEqual(rect.width(), 380)
            self.assertIn('panel', self.ctl.away.text())      # Graphite's right side says where she is
            self.assertEqual(panel.esc.key().toString(), 'Esc')
            panel.esc.activated.emit();pump()
            self.assertFalse(self.ctl.panel_open());self.assertFalse(panel.isVisible())
            self.assertIs(pane.parentWidget(), holder);self.assertEqual(holder.layout().indexOf(pane), index)      # back in its place
            self.assertFalse(self.ctl.away.isVisible())

    def test_docked_in_graphite_a_press_with_graphite_in_front_shows_her_column_where_it_stands(self):
        self.assertTrue(self.k.read_settings()['docked'])      # on by default
        with patch.object(self.k.KasBar, 'graphite_in_front', return_value=True):
            self.assertEqual(self.ctl.toggle(), 'docked');pump()
        self.assertEqual(self.host.shown, ['slate']);self.assertFalse(self.ctl.panel_open())
        self.assertIsNot(self.host.right_pane.parentWidget(), self.ctl.panel)

    def test_not_docked_her_column_lives_in_her_panel_and_graphites_right_side_is_the_works(self):
        self.ctl.set_docked(False);pump()
        self.assertFalse(json.loads(self.k.settings_file().read_text())['docked'])
        self.assertIs(self.host.right_pane.parentWidget(), self.ctl.panel);self.assertTrue(self.host.sim_dock.isHidden())
        self.host.sim_dock.show();pump(4)      # a caller that shows the right dock (show_slate_face) does not bring it back
        self.assertTrue(self.host.sim_dock.isHidden())
        with patch.object(self.k, 'reduce_motion', return_value=True), patch.object(self.k.KasBar, 'graphite_in_front', return_value=True):
            self.ctl.toggle();pump()
            self.assertTrue(self.ctl.panel_open())      # over Graphite too
            self.ctl.toggle();pump()
            self.assertIs(self.host.right_pane.parentWidget(), self.ctl.panel)      # closed, it stays in her panel
        self.ctl.set_docked(True);pump()
        self.assertIsNot(self.host.right_pane.parentWidget(), self.ctl.panel);self.assertFalse(self.host.sim_dock.isHidden())

    def test_a_permission_card_rises_from_her_chip_with_the_same_one_press_and_never_takes_the_keys(self):
        column = self.host.her_column;column.shown_state = 'awaiting_approval'
        column.rows = [dict(id='a' * 32, title='Tidy Downloads', state_words='needs your grant', line='Step 2 needs your grant', actions=[GRANT]),
                       dict(id='b' * 32, title='Sort the photos', state_words='waiting for your word', line='Step 3 waits for your word', actions=[AUTHORISE])]
        with patch.object(self.k.KasBar, 'graphite_in_front', return_value=False), patch.object(self.k, 'reduce_motion', return_value=True):
            self.ctl.tick();pump()
            card = self.ctl.card
            self.assertTrue(card.isVisible());self.assertLess(card.geometry().bottom(), self.bar.y())      # above the bar
            right = self.slot.mapToGlobal(self.slot.rect().topRight()).x() + 1;screen = self.bar.screen().geometry()
            self.assertEqual(card.x() + card.width(), min(right, screen.x() + screen.width() - 8))      # risen from her chip, inside the screen
            self.assertTrue(card.windowFlags() & Qt.WindowDoesNotAcceptFocus);self.assertTrue(card.testAttribute(Qt.WA_ShowWithoutActivating))
            self.assertTrue(all(b.focusPolicy() == Qt.NoFocus for b in card.findChildren(QPushButton)))
            self.assertEqual(card.head.text(), 'WAITS FOR YOU [2]')
            first = card.rows[0]
            self.assertEqual(first.press.text(), 'Grant this for this assignment')
            self.assertIn('move files inside “Downloads” in Files, for this assignment only', first.words.text())      # the grant, whole
            self.assertEqual(card.rows[1].press.text(), 'Authorise step 3')
            first.pressed();pump()
            self.assertEqual(column.steps, [])      # deaf for its first half second
            QTest.qWait(self.k.DEAF_MS + 60);pump()
            first.press.click();pump()
            self.assertEqual(len(column.steps), 1);self.assertIs(column.steps[0]['call'], GRANT)      # the same press as in her panel
            self.assertIn('done', card.said.text());self.assertTrue(card.said.isVisible())

    def test_no_card_while_her_column_is_in_sight_and_later_puts_it_off_until_what_waits_changes(self):
        column = self.host.her_column
        column.rows = [dict(id='b' * 32, title='Sort the photos', state_words='waiting for your word', line='Step 3', actions=[AUTHORISE])]
        with patch.object(self.k.KasBar, 'graphite_in_front', return_value=True):
            self.ctl.tick();pump()
            self.assertTrue(self.ctl.card is None or not self.ctl.card.isVisible())      # docked, Graphite in front: she is in sight
        with patch.object(self.k.KasBar, 'graphite_in_front', return_value=False), patch.object(self.k, 'reduce_motion', return_value=True):
            self.ctl.tick();pump();self.assertTrue(self.ctl.card.isVisible())
            self.ctl.card.put_off();self.ctl.tick();pump();self.assertFalse(self.ctl.card.isVisible())
            column.rows = column.rows + [dict(id='c' * 32, title='Rename the scans', state_words='waiting for your word', line='Step 1', actions=[AUTHORISE])]
            self.ctl.tick();pump();self.assertTrue(self.ctl.card.isVisible())      # something new waits
            self.ctl.open_panel();pump();self.assertFalse(self.ctl.card.isVisible())      # her panel open: the card goes

    def test_a_kernel_refusal_reaches_the_owner_in_plain_words_and_its_raw_text_is_kept_in_log(self):
        from workbench import activity, her_column_qt, kas_voice
        raw = 'Unknown or missing parameters for grant.give'
        words = kas_voice.refusal(raw, 'grant.give')
        self.assertNotIn('grant.give', words);self.assertTrue(words.startswith('The grant'))
        self.assertIn('nothing changed', words);self.assertIn('Press it once more', words);self.assertIn('Log', words)

        class Kernel:
            def dispatch(self, operation, args, owner):return {'ok': False, 'error': {'code': 'KernelError', 'message': raw}}
        with patch.object(her_column_qt, '_kernel', return_value=(Kernel(), None)):
            done, why = her_column_qt.press(self.host, 'grant.give', {'operation': 'files.move'})
        self.assertIsNone(done);self.assertEqual(why, words)
        kept = activity.recent(self.home, 20)      # Log's Events: the Kernel's own words, with the operation's name
        self.assertTrue(any(e.get('detail') == raw and e.get('state') == 'REFUSED' and e.get('operation') == 'grant.give' for e in kept), kept)

    # ---- the rest ----------------------------------------------------------------------------------------------------------
    def test_a_refusal_loses_its_code_and_every_operation_name(self):
        from workbench import kas_voice
        words = kas_voice.refusal('GRANT_OPERATION: files.write is not a registered operation here')
        self.assertNotIn('GRANT_OPERATION', words);self.assertNotIn('files.write', words);self.assertIn('Log', words)
        scope = kas_voice.refusal('Operation is outside the authorized mode/scope', 'assignment.plan')
        self.assertTrue(scope.startswith('The authorisation is outside'));self.assertNotIn('assignment.plan', scope)
        self.assertNotIn('halt.press', kas_voice.refusal('Unknown operation', 'halt.press'))

    def test_the_pause_key_presses_halt_and_never_resume(self):
        halt = self.slot.halt
        with patch('workbench.halt.press') as press, patch('workbench.halt.release') as release:
            self.assertTrue(self.ctl.pause_key());pump();press.assert_called_once()
            halt.busy = False;self.assertTrue(halt.held)
            self.assertFalse(self.ctl.pause_key());pump();release.assert_not_called();self.assertEqual(press.call_count, 1)
        self.assertEqual(self.ctl.pause.key().toString(), 'Pause');self.assertEqual(self.ctl.pause.context(), Qt.ApplicationShortcut)

    def test_the_setting_is_a_readable_file_on_by_default(self):
        self.assertEqual(self.k.read_settings(), {'docked': True})
        self.k.settings_file().parent.mkdir(parents=True, exist_ok=True);self.k.settings_file().write_text('not json')
        self.assertEqual(self.k.read_settings(), {'docked': True})      # a broken file gives the default
        self.assertEqual(self.k.write_settings(docked=False), {'docked': False});self.assertEqual(self.k.read_settings(), {'docked': False})

    def test_her_new_lines_pass_her_voice_sweep(self):
        from workbench import mind_words
        problems = [p for p in mind_words.check() if p[0] in ('kas_voice', 'her_column_qt')]
        self.assertEqual(problems, [])


if __name__ == '__main__':
    unittest.main()
