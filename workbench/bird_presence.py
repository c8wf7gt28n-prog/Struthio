"""Quiet, event-driven bird cues. A one-shot pose, never an idle animation loop."""
import time
from PySide6.QtCore import QObject, QTimer, QEvent
from PySide6.QtWidgets import QApplication
from sdk.cli.arc1cli.slate_attention import CueGate


class BirdPresence(QObject):
    def __init__(self, anchor):
        super().__init__(anchor)
        self.anchor = anchor
        self.gate = CueGate()
        self.primed = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(650)
        self.timer.timeout.connect(self.dismiss)
        QApplication.instance().installEventFilter(self)

    @property
    def enabled(self):
        return self.anchor.parentWidget().session.layout.get('stacy_reactions', True)

    def set_enabled(self, value):
        session = self.anchor.parentWidget().session
        session.set_layout(stacy_reactions=bool(value)); session.save()
        if not value:
            self.dismiss()

    def eventFilter(self, obj, event):
        if event.type() not in (QEvent.KeyPress, QEvent.MouseButtonPress, QEvent.Wheel):
            return False
        parent = obj
        while parent is not None:
            if parent is self.anchor.parentWidget():
                self.gate.input(time.monotonic()); self.dismiss(); break
            parent = parent.parent()
        return False

    def cue(self, key, pose='notice'):
        host = self.anchor.parentWidget()
        overlay = getattr(host, 'clip_overlay', None)
        visible = (self.anchor.isVisible() and not host.isMinimized() and
                   not self.anchor.collapsed and not self.anchor._dragging and
                   not (overlay and overlay.isVisible()))
        if not self.gate.admit(key, time.monotonic(), visible=visible,
                enabled=self.enabled, reduced=self.anchor.reduce_motion()):
            return False
        self.anchor.bird_pose = pose
        self.anchor.update(); self.timer.start()
        return True

    def observe(self, state, job):
        if not self.primed:
            self.primed = True
            if job:
                self.gate.seen.append(('job', job.get('id'), state, job.get('finished')))
            return
        if job and state in ('done', 'failed', 'approval', 'paused'):
            self.cue(('job', job.get('id'), state, job.get('finished')),
                     'acknowledge' if state == 'done' else 'notice')

    def command_finished(self, good, stopped, unavailable, label):
        return self.cue(('command', time.monotonic()),
                        'acknowledge' if good and not stopped and not unavailable else 'notice')

    def dismiss(self):
        self.timer.stop(); self.anchor.bird_pose = 'rest'; self.anchor.update()

    def position(self):
        self.anchor.update()
