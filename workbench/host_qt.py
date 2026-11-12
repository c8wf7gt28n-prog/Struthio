"""Small native service status surface; lifetime controls stay explicit."""
import sqlite3
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QScrollArea, QFrame
from .engine import engineering

ROOM_NAME = 'Service details'  # one name for this room: the Hatch row's tooltip, the Operations link, the tab and the heading (V-12)


class HostPanel(QWidget):
    def __init__(self, host):
        super().__init__(); self.host = host; self.kernel = engineering(host.root)
        self.setObjectName('LedgerBackgroundService')
        from .settings_qt import STYLE
        self.setProperty('paperFunctionalInk',True);self.setStyleSheet(STYLE)
        self.setProperty('concern_context','ledger')
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        content = QWidget(); scroll.setWidget(content); box = QVBoxLayout(content); box.setContentsMargins(22,18,22,18); box.setSpacing(12)
        title = QLabel(ROOM_NAME); title.setProperty('arcReadingRole','heading')  # the chrome's heading size, scaled with the interface size
        box.addWidget(title)
        self.setProperty('ledgerRoom',True)
        self.cycle=QLabel();self.cycle.setWordWrap(True);self.cycle.setTextFormat(Qt.PlainText);box.addWidget(self.cycle)
        self.status = QLabel(); self.status.setWordWrap(True); self.status.setTextFormat(Qt.PlainText)
        self.status.setAccessibleName('Background service status'); box.addWidget(self.status)
        # V-12: words in one row at their own width (theme2.as_words), never 585 px hit areas; the two host-client controls are
        # shown only when a background service is attached, because in the embedded desktop they do nothing.
        attached = bool(getattr(self.kernel, 'is_host_client', False))
        row = QHBoxLayout(); row.setSpacing(18); box.addLayout(row); self.words = {}
        from .settings_qt import action
        for label, fn, needs_host in (('Refresh', self.refresh, False), ('Reconnect', self.reconnect, True),
                          ('Master Stop…', host.master_stop_all, False), ('Resume work', self.resume, False),
                          ('Stop service…', self.stop, True)):
            button = action(label,fn);row.addWidget(button);self.words[label]=button
            if needs_host and not attached:
                button.setVisible(False);button.setToolTip(label.rstrip('…')+' applies to an attached background service; this desktop owns its embedded services.')
        row.addStretch(1)
        note = QLabel(('Shared jobs and the selected model keep running when this window closes. ' if attached else 'This development desktop owns its embedded services; Reconnect and Stop service apply only to an attached background service. ')+'Master Stop holds new work and switches off phone access. Resume is always explicit.')
        note.setWordWrap(True); box.addWidget(note)
        setup = QLabel('The Debian service guide covers startup at login or boot. Keep this computer awake for phone access. Device and home-connection checks are not part of this edition.')
        setup.setWordWrap(True); box.addWidget(setup); box.addStretch(1)
        self.refresh()

    def title(self): return ROOM_NAME

    def refresh(self):
        from .service_lifecycle import snapshot
        try:
            service=snapshot(self.kernel);counts=service['counts'];stale=counts.get('stale_running',0)
            # The display state follows observation; the stored note stays a request.
            restore={'REQUESTED':'Previous model reload requested; inspect Local models.','FAILED':'Previous model reload failed; inspect Local models.',
                'OBSERVED_RUNNING':'Previous model reload requested; the same model is now observed running.',
                'REQUEST_FAILED':'Previous model reload was requested but its job did not complete; inspect Local models.'
                }.get(service.get('model_restore_display',service['model_restore']))
            self.cycle.setText('GRAPHITE SERVICES · '+service['summary']+'\n'+str(counts['running'])+' running jobs · '+str(counts['queued'])+' queued jobs'+
                ('\n'+str(stale)+(' running record has' if stale==1 else ' running records have')+' no live worker · use Master Stop or Work trail → recover' if stale else '')+
                '\n'+service['control_plane']+('\n'+restore if restore else ''))
        except (ValueError,OSError,sqlite3.Error,KeyError,TypeError) as exc:self.cycle.setText('GRAPHITE SERVICES · status unavailable\n'+str(exc))
        if not getattr(self.kernel, 'is_host_client', False):
            self.status.setText('Embedded development mode. This desktop owns its local Kernel.'); return
        try:
            info = self.kernel.rpc('status', timeout=2)
            active = sum(j['state'] in ('Queued', 'Running') for j in info['jobs'])
            lifetime = 'Background service running\nStartup managed by systemd' if info['supervision'] == 'systemd-user' else 'Background service running\nBoot startup not set up by this connection'
            self.status.setText(lifetime + '\n' + ('New work held · use Resume deliberately' if info['work']['held'] else 'Accepting new authorized work')
                + '\n' + str(active) + ' active jobs · model ' + info['model'].replace('_', ' ').lower()
                + '\nPhone listener ' + ('running' if info['remote']['listening'] else 'off')
                + ('\n' + info['recovery_error'] if info['recovery_error'] else ''))
        except (ValueError, OSError) as exc: self.status.setText(str(exc))

    def reconnect(self):
        try:
            from .host_client import reconnect
            self.kernel = reconnect(self.host.root); self.refresh()
        except (ValueError, OSError) as exc: self.status.setText(str(exc))

    def resume(self):
        from .engineering_kernel import operator
        reply = self.kernel.dispatch('ledger.work.resume', {}, operator())
        if reply['ok']: self.refresh()
        else: self.status.setText(reply['error']['message'])

    def stop(self):
        if not getattr(self.kernel, 'is_host_client', False): return
        if QMessageBox.question(self, 'Stop background service?',
                'Cancel shared work, stop the local model, revoke phone access and stop the background service? The desktop and unsaved notes stay open.',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return
        try:
            self.kernel.rpc('shutdown', timeout=2)
            self.status.setText('Stopping background service. Use Refresh to check; use Reconnect and then Resume when ready.')
        except (ValueError, OSError) as exc: self.status.setText(str(exc))


def install(host):
    def show():
        for index in range(host.tabs.count()):
            if isinstance(host.tabs.widget(index), HostPanel):
                host.tabs.setCurrentIndex(index); host.tabs.widget(index).refresh(); return
        host._close_start()
        panel = HostPanel(host); host.tabs.addTab(panel, panel.title()); host.tabs.setCurrentWidget(panel)
    action = QAction('Background service…', host)
    action.setToolTip('Check background work, reconnect, or stop the shared Graphite service')
    action.triggered.connect(show)
    host.a_host_service = action
    # The visible shell uses these existing menus through its compact toolbar;
    # a new hidden native menu bar would be unreachable in that presentation.
    host.menu_groups['Options'].insertAction(host.a_remote_link,action)
    host.favorite_actions['background_service'] = action
