"""0.8.4: both panes come back to their width after a larger interface size.

At 0.8.3, on a fresh window at 1920 by 1200, the interface size raised to 28 pt and set back to 14 pt left both panes 415 px
wide where a fresh window has 326 (479 where it has 354 in the Kasandra look), until Graphite was started again. A pane counts
the least width of every face, shown or not (pane_qt.PaneBody.content_minimum), and Qt measures a layout again only when its
widget shows: a face out of sight through the change kept the least width that 28 pt had given it. Now a pane measures its
faces out of sight again at each new size (pane_qt.remeasure), and asks the window again whenever its least width changes.

Found by the review of the window checks: the frame's window check, retired in 0.8.4, went up to 28 pt; its step in
tools/check_finder_ui.py (14) goes there again.

The real window, offscreen, on a new profile and workspace for each test; no provider request, worker launch, job, or
session or power call.
"""
import os
import platform
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from workbench.session import Session


class FacesOutOfSight(unittest.TestCase):
    """Bare widgets: what Qt does to a face out of sight, and what remeasure does about it."""

    def test_a_face_out_of_sight_keeps_its_old_least_width_until_it_is_measured_again(self):
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QApplication, QLayout, QPushButton, QStackedWidget, QVBoxLayout, QWidget
        from workbench import pane_qt
        app = QApplication.instance() or QApplication([])
        stack = QStackedWidget();self.addCleanup(stack.deleteLater);stack.addWidget(QWidget())
        face = QWidget();box = QVBoxLayout(face);box.setSizeConstraint(QLayout.SetMinimumSize)
        button = QPushButton('A word the size of the interface');box.addWidget(button);stack.addWidget(face)
        def size(px):
            font = QFont(button.font());font.setPixelSize(px);button.setFont(font);app.processEvents()
        stack.setCurrentWidget(face);stack.show();size(36);large = face.minimumWidth()
        stack.setCurrentIndex(0);size(12);app.processEvents()
        self.assertEqual(face.minimumWidth(), large, 'out of sight, the face keeps the width the larger size gave it (as at 0.8.3)')
        pane_qt.remeasure(stack)
        self.assertLess(face.minimumWidth(), large);self.assertEqual(face.minimumWidth(), box.minimumSize().width())


class PanesAfterALargerSize(unittest.TestCase):
    def setUp(self):
        from PySide6.QtWidgets import QMessageBox
        from workbench import clip, locations, session_power
        from workbench.engineering_kernel import Kernel
        from workbench.qt_app import make_app
        temporary = tempfile.TemporaryDirectory(prefix='graphite-084-panes-');self.addCleanup(temporary.cleanup);run = Path(temporary.name)
        env = patch.dict(os.environ, {'ARC_LEDGER_EMBEDDED': '1', 'ARC_LEDGER_DISABLE_BOOK_WATCHER': '1', 'ARC1_WORKBENCH_CONFIG_HOME': str(run / 'profile'),
                                      'ARC_LEDGER_CONCERN': str(run / 'Concern')})
        env.start();self.addCleanup(env.stop);os.environ.pop('ARC_LEDGER_XSESSION', None)
        for hold in (patch.object(clip, '_request', side_effect=AssertionError('No provider request')), patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')),
                     patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')), patch.object(session_power, 'system', side_effect=OSError('no login session (held)')),
                     patch.object(QMessageBox, 'question', return_value=QMessageBox.No)):
            hold.start();self.addCleanup(hold.stop)
        self.app = make_app([]);self.root = locations.office(run / 'workspace');self.path = run / 'profile' / 'session.json'

    def settle(self, w, ms=30):
        from PySide6.QtTest import QTest
        for name in ('agenda_runner', 'study_idle', 'ledger_bridge'):
            timer = getattr(getattr(w, name, None), 'timer', None)
            if timer is not None:timer.stop()
        try:w.type_bar.hatch.lifecycle.timer.stop()
        except AttributeError:pass
        for _ in range(3):self.app.processEvents();QTest.qWait(ms)

    def align(self, w):
        for _ in range(3):w.type_bar.align();self.settle(w)

    def start(self):
        from workbench.qt_app import WorkbenchWindow
        w = WorkbenchWindow(self.root, Session(self.path, self.root), restore=False);platform.processor()
        w.resize(1920, 1200);w.show();self.settle(w, 60);self.align(w)
        def close():
            w.close();self.settle(w);w.deleteLater();self.app.processEvents()
        self.addCleanup(close);return w

    def interface_size(self, w, points):
        from workbench import ledger_control
        from workbench.engineering_kernel import operator
        row = next(r for r in ledger_control.settings(w.ledger_bridge.kernel)['settings'] if r['key'] == 'reading.ui_pt')
        response = w.ledger_bridge.kernel.dispatch('ledger.settings.set', dict(key='reading.ui_pt', value=float(points), expected_revision=row['revision']), operator())
        self.assertTrue(response['ok'], response);w.ledger_bridge.sync_profile(force=True);self.settle(w);self.align(w)

    def panes(self, w):return [w.nav_dock.width(), w.sim_dock.width()]

    def test_both_panes_come_back_to_their_width_from_28_pt(self):
        w = self.start();fresh = self.panes(w);least = [w.left_pane.minimumSizeHint().width(), w.right_pane.minimumSizeHint().width()]
        self.assertEqual(fresh[0], fresh[1]);self.assertEqual(fresh[0], w.desk.pane)
        self.interface_size(w, 28);wide = self.panes(w)
        self.assertEqual(wide[0], wide[1]);self.assertGreater(wide[0], fresh[0], 'at 28 pt both panes are wider')
        self.interface_size(w, 14)
        self.assertEqual(self.panes(w), fresh, 'back at 14 pt both panes are as a fresh window has them')      # 0.8.3: 415 where fresh is 326
        self.assertEqual([w.left_pane.minimumSizeHint().width(), w.right_pane.minimumSizeHint().width()], least, 'and each pane needs what it needed')


if __name__ == '__main__':
    unittest.main()
