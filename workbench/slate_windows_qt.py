"""Small owner controls for the logical-window registry inside Object Glass."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout
from sdk.cli.arc1cli.object_context import principal_key


class WindowsPanel(QGroupBox):
    def __init__(self, host):
        super().__init__("Graphite Windows")
        self.host = host
        self.controller = host.object_glass
        self.serial = 0
        self.rows = {}
        box = QVBoxLayout(self)
        self.enabled = QCheckBox("Enable resumable windows")
        self.enabled.setAccessibleName("Enable Graphite logical windows for this owner")
        box.addWidget(self.enabled)
        self.controls = QGroupBox()
        controls = QVBoxLayout(self.controls)
        self.saved = QComboBox()
        self.saved.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.saved.setAccessibleName("Saved logical windows")
        self.devices = QComboBox()
        self.devices.setStyleSheet("QComboBox { min-width: 0px; }")
        self.devices.setMinimumWidth(80)
        self.devices.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.devices.setAccessibleName("Explicit paired-device publication recipient")
        self.devices.addItem("Reload to find paired devices", None)
        controls.addWidget(self.saved)
        self.keep, self.reload, self.restore = [QPushButton(t) for t in ("Keep view", "Reload", "Restore")]
        self.refresh, self.close = [QPushButton(t) for t in ("Refresh", "Close")]
        self.publish, self.revoke = [QPushButton(t) for t in ("Publish overview", "Revoke")]
        for button, label in ((self.keep, "Keep selected view as a logical window"), (self.refresh, "Refresh saved logical window"), (self.close, "Close saved logical window")):
            button.setAccessibleName(label)
            button.setToolTip(label)
        for buttons in ((self.keep, self.reload, self.restore), (self.refresh, self.close), (self.devices, self.publish, self.revoke)):
            row = QHBoxLayout()
            for button in buttons:
                row.addWidget(button)
            controls.addLayout(row)
        box.addWidget(self.controls)
        self.content = QPushButton('Preview / share content')
        controls.addWidget(self.content)
        self.content.clicked.connect(self.content_view)
        self.notice = QLabel("Saved windows start disabled. Content sharing needs a reviewed preview and a specific paired device.")
        self.notice.setWordWrap(True)
        self.notice.setTextFormat(Qt.PlainText)
        self.notice.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        box.addWidget(self.notice)
        self.controls.hide()
        self.enabled.toggled.connect(lambda value: self.request("ledger.windows.configure", {"enabled": value}, lambda r: self.load()))
        self.keep.clicked.connect(self.keep_view)
        self.reload.clicked.connect(self.load)
        self.restore.clicked.connect(self.restore_view)
        self.refresh.clicked.connect(self.refresh_view)
        self.close.clicked.connect(lambda: self.current_call("ledger.windows.close", {}, lambda r: self.load()))
        self.publish.clicked.connect(self.publish_view)
        self.revoke.clicked.connect(lambda: self.current_call("ledger.windows.revoke", {"device": self.devices.currentData()}, lambda r: self.message("Publication revoked.")) if self.devices.currentData() else None)
        self.controller.changed.connect(self.changed)
        self.changed(self.controller.data)
        self.load()

    def message(self, text):
        self.notice.setText(text)

    def changed(self, data):
        self.keep.setEnabled(data.get("state") == "AVAILABLE" and "approve" in self.controller.caller().scopes)
        self.enabled.setEnabled("approve" in self.controller.caller().scopes)
        for button in (self.refresh, self.close, self.publish, self.revoke, self.content):
            button.setEnabled("approve" in self.controller.caller().scopes)
        # Remove private window labels immediately when the effective caller changes.
        key = principal_key(self.controller.caller())
        if getattr(self, "caller_key", key) != key:
            self.serial += 1
            self.rows = {}
            self.saved.clear()
            self.devices.clear()
            self.controls.hide()
            self.message("Caller changed. Reload saved windows.")
        self.caller_key = key

    def request(self, operation, args, done):
        self.controller.check_authority()
        self.serial += 1
        serial = self.serial
        key = principal_key(self.controller.caller())
        epoch = getattr(self.host, "_operation_epoch", 0)
        def loaded(envelope):
            if self.host._closing or serial != self.serial or key != principal_key(self.controller.caller()) or epoch != getattr(self.host, "_operation_epoch", 0):
                return
            if not envelope.get("ok"):
                self.message("Window unavailable. Check the selection, sources and current permissions.")
                return
            done(envelope["result"])
        self.controller.request(operation, args, loaded)

    def load(self):
        def status(data):
            self.enabled.blockSignals(True)
            self.enabled.setChecked(data["enabled"])
            self.enabled.blockSignals(False)
            self.controls.setVisible(data["enabled"])
            if data["enabled"]:
                self.request("ledger.windows.list", {}, self.listed)
            else:
                self.rows = {}
                self.saved.clear()
                self.devices.clear()
                self.message("Disabled. Jobs and existing PWA behavior are preserved; publication grants are removed.")
        self.request("ledger.windows.status", {}, status)

    def listed(self, data):
        previous = self.saved.currentData()
        self.saved.clear()
        self.rows = {r["window_id"]: r for r in data["windows"]}
        for ident, row in self.rows.items():
            self.saved.addItem(row.get("title", "Needs owner refresh") + " · " + ident[:11], ident)
        index = self.saved.findData(previous)
        if index >= 0:
            self.saved.setCurrentIndex(index)
        self.message(str(len(self.rows)) + " saved view(s). Content sharing requires its own reviewed preview.")
        def paired(rows):
            self.devices.clear()
            self.devices.addItem("Choose a paired device", None)
            for row in rows:
                self.devices.addItem((row.get("device_name") or "Paired device") + " · " + row["identity"], row["identity"])
        self.request("remote.sessions", {}, paired)

    def keep_view(self):
        data = self.controller.data
        if data.get("state") != "AVAILABLE":
            return
        self.request("ledger.windows.open", {"selector": data["selector"], "expected_revision": data["revision"], "expected_object_id": data["object_id"]}, lambda r: self.load())

    def current_call(self, op, args, done):
        ident = self.saved.currentData()
        if ident:
            self.request(op, {"window_id": ident, **args}, done)

    def restore_view(self):
        original = self.controller.guard.current
        def restored(value):
            if value.get("state") != "AVAILABLE":
                self.message(value.get("summary", "Saved view needs owner refresh."))
            elif self.controller.guard.current == original:
                if value['object']['kind']=='pdf':
                    from .window_views_qt import show_content
                    show_content(self.host,value['window_id'],self.controller.caller());return
                self.controller.select(value["object"], entry={"object_id": value["object_id"], "revision": value["source_revision"]})
        self.current_call("ledger.windows.snapshot", {}, restored)

    def refresh_view(self):
        row = self.rows.get(self.saved.currentData(), {})
        revision = row.get("source_revision", row.get("expected_revision"))
        if revision:
            self.current_call("ledger.windows.refresh", {"expected_revision": revision}, lambda r: self.load())
        else:
            self.message("Restore the original selection and keep a freshly checked view, or close this stale window.")

    def publish_view(self):
        row = self.rows.get(self.saved.currentData(), {})
        if row.get("source_revision") and self.devices.currentData():
            self.current_call("ledger.windows.publish", {"device": self.devices.currentData(), "expected_revision": row["source_revision"]},
                              lambda r: self.message("Overview published to " + r["published_to"] + ". No engineering execution granted."))

    def content_view(self):
        if self.saved.currentData():
            from .window_views_qt import show_content
            return show_content(self.host,self.saved.currentData(),self.controller.caller())

