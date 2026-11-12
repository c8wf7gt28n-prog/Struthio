"""Desktop-owned controls for an owner-hosted phone link; secrets stay private."""
from .text_prompts import writing_prompt
import json
import sys
from pathlib import Path
from PySide6.QtCore import QObject, QProcess, Qt
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QMessageBox, QFormLayout, QFileDialog, QTreeWidget, QTreeWidgetItem)
from .engine import engineering
from .engineering_kernel import operator
from .remote_service import validate_origin


class RemoteLink(QObject):
    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.kernel = engineering(host.root)
        self.process = QProcess(self)
        from .operation_priority import watch_qprocess
        watch_qprocess(self.process,host.root)
        self.code = self.origin = self.buffer = ""
        self.process.setWorkingDirectory(str(host.root))
        self.process.readyReadStandardOutput.connect(self.output)
        self.process.readyReadStandardError.connect(self.error)
        self.process.errorOccurred.connect(lambda *_: self.status.setText("Unable to start. Check the endpoint, certificate and interface."))
        self.process.finished.connect(lambda *_: self.status.setText("Service stopped. Jobs and unexpired same-policy pairings are retained."))
        if not getattr(self.kernel,'is_host_client',False):
            QApplication.instance().aboutToQuit.connect(lambda: self.stop(revoke=False))
        self.config_path = host.root / ".ledger/remote-config.json"
        try:
            config = json.loads(self.config_path.read_text())
        except (OSError, ValueError):
            config = {}
        self.dialog = QDialog(host)
        self.dialog.setWindowTitle("Connect phone · Owner-hosted Graphite")
        self.dialog.resize(680, 720)
        layout = QVBoxLayout(self.dialog)
        title = QLabel("Your Graphite, on your phone")
        title.setStyleSheet("font-size:20px;font-weight:bold")
        layout.addWidget(title)
        info = QLabel("Serve from this computer with your own HTTPS certificate. For access away from home, use a reachable owner endpoint or an owner-operated VPN. Keep the ThinkPad awake. No hosted relay or external login is required.")
        info.setWordWrap(True)
        layout.addWidget(info)
        form = QFormLayout()
        layout.addLayout(form)
        self.address = QLineEdit(config.get("origin", "http://localhost:8765"))
        writing_prompt(self.address, "https://ledger.your-owner-domain:8765")
        form.addRow("Phone address", self.address)
        self.interface = QLineEdit(config.get("bind", "127.0.0.1"))
        form.addRow("Listen on IP", self.interface)
        self.cert = QLineEdit(config.get("cert", ""))
        self.key = QLineEdit(config.get("key", ""))
        for label, field in (("Certificate PEM", self.cert), ("Private key PEM", self.key)):
            row = QHBoxLayout()
            row.addWidget(field)
            button = QPushButton("Choose…")
            button.clicked.connect(lambda checked=False, f=field: self.choose(f))
            row.addWidget(button)
            form.addRow(label, row)
        self.profile = QComboBox()
        for label, value in (("View · sources, jobs and evidence", "view"),
                ("Develop · bounded candidates and registered tests", "develop"),
                ("Owner · review, authorize and revoke", "owner")):
            self.profile.addItem(label, value)
        self.profile.setCurrentIndex(max(0, self.profile.findData(config.get("profile", "develop"))))
        form.addRow("Pairing grant", self.profile)
        hint = QLabel("HTTP localhost is for this computer only. A direct network listener requires a trusted HTTPS certificate. A loopback HTTPS origin may use your own reverse proxy. Certificate trust, router access and iPhone installation still need owner-device checks.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.status = QLabel("Remote access is off.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.pairing = QLineEdit()
        self.pairing.setReadOnly(True)
        writing_prompt(self.pairing, "One-time pairing code · valid for 5 minutes")
        layout.addWidget(self.pairing)
        row = QHBoxLayout()
        for label, fn in (("Start / new pairing code", self.start),
                ("Copy address", lambda: QApplication.clipboard().setText(self.origin)),
                ("Stop & revoke all", self.stop)):
            b = QPushButton(label)
            b.clicked.connect(lambda checked=False, f=fn: f())
            row.addWidget(b)
        layout.addLayout(row)
        self.devices = QTreeWidget()
        self.devices.setHeaderLabels(["Paired device", "Grant", "Identity"])
        self.devices.setMaximumHeight(145)
        layout.addWidget(self.devices)
        row = QHBoxLayout()
        for label, fn in (("Refresh devices", self.refresh_devices), ("Revoke selected device", self.revoke_device)):
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        layout.addLayout(row)
        note = QLabel("Close this dialog or the desktop to keep the background service serving. Restarting this listener with the same address and grant preserves pairings until expiry. Stop & revoke removes access immediately; existing job evidence remains.")
        note.setWordWrap(True)
        layout.addWidget(note)

    def choose(self, field):
        path, _ = QFileDialog.getOpenFileName(self.dialog, "Choose owner TLS file", str(Path.home()), "PEM files (*.pem *.crt *.key);;All files (*)")
        if path:
            field.setText(path)

    def show(self):
        self.refresh_devices()
        if getattr(self.kernel,'is_host_client',False):
            try:
                remote=self.kernel.rpc('status',timeout=2)['remote']
                if remote['listening']:
                    self.origin=remote['origin'];self.status.setText('Background phone listener running at '+self.origin+'. Start / new pairing code to pair another device.')
            except (ValueError,OSError) as exc:self.status.setText(str(exc))
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def start(self):
        from .service_lifecycle import require_admission
        try:require_admission(self.kernel)
        except ValueError as exc:self.status.setText(str(exc));return
        origin = self.address.text().strip().rstrip("/")
        try:
            u = validate_origin(origin)
        except ValueError as e:
            self.status.setText(str(e))
            return
        if self.profile.currentData() == "owner" and QMessageBox.question(self.dialog, "Phone owner authority",
                "This grant can authorize native candidate execution, accept reviewed source and revoke devices. Enable owner authority for this pairing?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.stop(revoke=False)
        self.origin, self.buffer = origin, ""
        self.status.setText("Starting owner-hosted service…")
        port = u.port or (443 if u.scheme == "https" else 80)
        args = ["-m", "workbench.engineering_cli", "--root", str(self.host.root), "--operator", "remote",
                "--origin", origin, "--port", str(port), "--bind", self.interface.text().strip(), "--profile", self.profile.currentData()]
        if self.cert.text().strip() or self.key.text().strip():
            args += ["--cert", self.cert.text().strip(), "--key", self.key.text().strip()]
        config = dict(origin=origin, bind=self.interface.text().strip(), profile=self.profile.currentData(),
                      cert=self.cert.text().strip(), key=self.key.text().strip())
        self.config_path.parent.mkdir(exist_ok=True)
        self.config_path.write_text(json.dumps(config, indent=2))
        self.config_path.chmod(0o600)
        if getattr(self.kernel,'is_host_client',False):
            try:
                result=self.kernel.rpc('remote_start',{'port':port,**config})
                self.code=result['pair_code'];self.pairing.setText(self.code)
                self.status.setText('Ready at '+self.origin+' · pair within 5 minutes. The background listener stays on when the desktop closes.')
                self.refresh_devices()
            except (ValueError,OSError) as exc:self.status.setText(str(exc))
            return
        self.process.start(sys.executable, args)

    def output(self):
        self.buffer += bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        lines = self.buffer.split("\n")
        self.buffer = lines.pop()
        for line in lines:
            if line.startswith("One-time pairing code (5 minutes): "):
                self.code = line.split(": ", 1)[1]
                self.pairing.setText(self.code)
                self.status.setText("Ready at " + self.origin + " · open in Safari and pair within 5 minutes.")
                self.refresh_devices()

    def error(self):
        message = bytes(self.process.readAllStandardError()).decode(errors="replace")
        if message:
            self.status.setText("Service error: " + message[-650:])

    def refresh_devices(self):
        r = engineering(self.host.root).dispatch("remote.sessions", {}, operator())
        self.devices.clear()
        if r["ok"]:
            for row in r["result"]:
                item = QTreeWidgetItem([row["device_name"], row.get("profile") or "legacy", row["identity"]])
                item.setData(0, Qt.UserRole, row["identity"])
                self.devices.addTopLevelItem(item)
        self.devices.resizeColumnToContents(0)

    def revoke_device(self):
        items = self.devices.selectedItems()
        if not items:
            return
        identity = items[0].data(0, Qt.UserRole)
        engineering(self.host.root).dispatch("remote.revoke", {"identity": identity}, operator())
        self.refresh_devices()
        self.status.setText("Selected access revoked. Job records remain available to the owner.")

    def stop(self, revoke=True):
        if getattr(self.kernel,'is_host_client',False):
            try:self.kernel.rpc('remote_stop',{'revoke':revoke})
            except (ValueError,OSError) as exc:
                self.status.setText(str(exc));return
            self.code='';self.pairing.clear()
            self.status.setText('Remote access off; '+('sessions revoked.' if revoke else 'same-policy pairings retained.'))
            return
        if revoke:
            engineering(self.host.root).dispatch("remote.disable", {}, operator())
        if self.process.state() != QProcess.NotRunning:
            self.process.terminate()
            self.process.waitForFinished(2000)
            if self.process.state() != QProcess.NotRunning:
                self.process.kill()
                self.process.waitForFinished(1000)
        self.code = ""
        self.pairing.clear()
        self.status.setText("Remote access off; " + ("sessions revoked." if revoke else "same-policy pairings retained."))
