"""The Concern's founding record and evidence, inside the existing Qt workspace."""
from .text_prompts import writing_prompt
from datetime import datetime, timedelta, timezone
import html
import json
from pathlib import Path
import threading

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog,
    QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSplitter, QTabWidget, QTextBrowser,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
from sdk.cli.arc1cli.genesis import CANONICAL_SHA256, FOUNDER, GenesisStore, TRUST, instant, read_bytes, utc_now


class Results(QObject):
    completed = Signal(object, object)


def label(value):
    result = QLabel(value)
    result.setWordWrap(True)
    result.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return result


class RecordDialog(QDialog):
    def __init__(self, host, kind):
        super().__init__(host)
        self.host = host; self.kind = kind; self.controls = {}; self.sources = []
        self.setWindowTitle({'work':'Register a work', 'rights':'Record written contribution rights',
                             'delegation':'Record written delegation', 'execution':'Record an execution copy'}[kind])
        self.resize(620, 650 if kind in ('rights', 'delegation') else 440)
        outer = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        body = QWidget(); self.form = QFormLayout(body)
        self.form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        scroll.setWidget(body); outer.addWidget(scroll)
        if kind == 'work':
            self.add_text('title', 'Work title')
            self.add_combo('kind', 'Kind', ['Hardware', 'Software', 'Firmware', 'Game', 'Artwork', 'Document'])
            self.add_sources()
        elif kind == 'rights':
            self.add_text('contributor', 'Contributor')
            self.add_combo('basis', 'Rights basis', ['License', 'Assignment', 'Founder declaration'])
            self.add_text('scope', 'Rights and permitted uses', multiline=True)
            self.add_sources()
            self.add_file('instrument', 'Written instrument')
        elif kind == 'delegation':
            self.add_text('recipient', 'Recipient')
            self.add_text('scope', 'Purpose / project / scope', multiline=True)
            self.add_text('limits', 'Approval limits', multiline=True)
            self.add_text('effective', 'Effective (with timezone)', utc_now())
            self.add_text('expires', 'Expires (with timezone)',
                          (datetime.now(timezone.utc) + timedelta(days=30)).replace(microsecond=0).isoformat())
            self.controls['subdelegation'] = QCheckBox('Written instrument permits subdelegation')
            self.form.addRow(self.controls['subdelegation'])
            self.add_file('instrument', 'Written delegation')
        else:
            self.add_file('path', 'Execution PDF', 'PDF documents (*.pdf)')
            self.add_text('declared_date', 'Stated execution time (optional)')
        self.add_text('actor', 'Recorded by', FOUNDER)
        note = ('Records the supplied document and its exact fingerprint. A filename or local name entry does not verify a signature or identity.'
                if kind == 'execution' else
                'Record the actual written instrument and its scope. This records your declaration; it grants no Graphite account permissions.'
                if kind == 'delegation' else
                'This records a source edition for review. Written rights and explicit owner review are required before recording acceptance.'
                if kind == 'work' else
                'The instrument stays in your local Concern record. Recording it does not decide whether its terms are legally adequate.')
        outer.addWidget(label(note))
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); outer.addWidget(buttons)

    def add_text(self, key, title, default='', multiline=False):
        field = QPlainTextEdit() if multiline else QLineEdit()
        if multiline:
            field.setMaximumHeight(92); field.setPlainText(default)
        else:
            field.setText(default)
        field.setAccessibleName(title); self.controls[key] = field; self.form.addRow(title, field)

    def add_combo(self, key, title, values):
        field = QComboBox(); field.addItems(values); field.setAccessibleName(title)
        self.controls[key] = field; self.form.addRow(title, field)

    def add_sources(self):
        box = QWidget(); row = QVBoxLayout(box); row.setContentsMargins(0, 0, 0, 0)
        self.source_view = QPlainTextEdit(); self.source_view.setReadOnly(True); self.source_view.setMaximumHeight(92)
        self.source_view.setAccessibleName('Source files in this edition')
        button = QPushButton('Choose project files…'); button.clicked.connect(self.choose_sources)
        row.addWidget(self.source_view); row.addWidget(button); self.form.addRow('Exact source edition', box)

    def choose_sources(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Select project source files', str(self.host.root))
        try:
            names = [str(Path(p).resolve().relative_to(self.host.root.resolve())).replace('\\', '/') for p in paths]
            if names:
                self.sources = names; self.source_view.setPlainText('\n'.join(names))
        except ValueError:
            QMessageBox.information(self, 'Project source files', 'Choose files inside this Graphite project.')

    def add_file(self, key, title, types='Documents (*)'):
        field = QLineEdit(); field.setReadOnly(True); field.setAccessibleName(title)
        button = QPushButton('Choose…')
        def choose():
            name, _ = QFileDialog.getOpenFileName(self, title, '', types)
            if name:
                field.setText(name)
        button.clicked.connect(choose)
        box = QWidget(); row = QHBoxLayout(box); row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(field, 1); row.addWidget(button); self.controls[key] = field
        self.form.addRow(title, box)

    def values(self):
        result = {}
        for key, field in self.controls.items():
            result[key] = (field.isChecked() if isinstance(field, QCheckBox) else field.currentText()
                           if isinstance(field, QComboBox) else field.toPlainText()
                           if isinstance(field, QPlainTextEdit) else field.text())
        if self.kind in ('work', 'rights'):
            result['sources'] = self.sources
        return result


class GenesisTab(QWidget):
    def __init__(self, host):
        super().__init__(); self.host = host; self.store = GenesisStore(host.root)
        self.report = None; self.busy = False; self.actions = []
        outer = QVBoxLayout(self); outer.setSpacing(7)
        heading = label('ARC CONCERN  /  THE BEGINNING')
        heading.setStyleSheet('font-weight:700;color:#ffad67;'); outer.addWidget(heading)
        subtitle = label('ARC-GENESIS-0001 · R. A. Peddycoart · 25 October 2026')
        subtitle.setProperty('arcRole', 'metadata'); outer.addWidget(subtitle)
        self.summary = label('Checking the founding record…'); self.summary.setAccessibleName('Genesis evidence status')
        outer.addWidget(self.summary)
        toolbar = QHBoxLayout()
        self.button(toolbar, 'Verify', self.verify_record)
        self.button(toolbar, 'Export…', self.export_evidence)
        self.button(toolbar, 'Declaration', lambda:self.open_file('originals/seal/ARC_Genesis_Founder_Seal.pdf'))
        toolbar.addStretch(); outer.addLayout(toolbar)
        self.pages = QTabWidget(); outer.addWidget(self.pages, 1)
        self.build_charter(); self.build_proof(); self.build_register(); self.build_files()
        self.notice = label(''); self.notice.setProperty('arcRole', 'metadata'); outer.addWidget(self.notice)
        self.signals = Results(host); self.signals.completed.connect(self._completed)
        self.load_static()
        QTimer.singleShot(0, self.verify_record)

    def title(self):
        return 'ARC Concern · Genesis'

    def button(self, row, title, callback):
        button = QPushButton(title); button.clicked.connect(callback); row.addWidget(button)
        self.actions.append(button); return button

    def build_charter(self):
        page = QWidget(); layout = QVBoxLayout(page)
        split = QSplitter(Qt.Horizontal)
        art = QWidget(); art_layout = QVBoxLayout(art)
        self.poster = QLabel(); self.poster.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.poster.setAccessibleName('Original founding charter poster')
        self.poster.setMinimumWidth(140); self.poster.setMaximumWidth(220)
        art_layout.addWidget(self.poster, 1)
        button = QPushButton('Open poster PDF'); button.clicked.connect(lambda:self.open_file('originals/complete/ARC_GENESIS_0001_Charter_Poster_11x17.pdf'))
        art_layout.addWidget(button)
        self.charter = QTextBrowser(); self.charter.setAccessibleName('Read-only canonical founding charter')
        split.addWidget(art); split.addWidget(self.charter); split.setSizes([180, 600]); layout.addWidget(split, 1)
        fingerprint = label('SHA-256  ' + CANONICAL_SHA256)
        fingerprint.setProperty('arcRole', 'metadata'); layout.addWidget(fingerprint)
        self.pages.addTab(page, 'Charter')

    def build_proof(self):
        page = QWidget(); layout = QVBoxLayout(page)
        self.proof = QTextBrowser(); self.proof.setAccessibleName('Independent timestamp and execution evidence')
        layout.addWidget(self.proof, 1)
        row = QHBoxLayout(); self.target = QComboBox(); self.target.setAccessibleName('Document to timestamp')
        row.addWidget(self.target, 1)
        self.button(row, 'Timestamp…', self.timestamp)
        self.button(row, 'Save request…', self.save_request)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.button(row, 'Import receipt…', self.import_receipt)
        self.button(row, 'Import execution PDF…', lambda:self.add_record('execution'))
        row.addStretch(); layout.addLayout(row)
        layout.addWidget(label('The certified receipt time, founding clock entry, execution copy and signer identity are separate records.'))
        self.pages.addTab(page, 'Proof / execution')

    def build_register(self):
        page = QWidget(); layout = QVBoxLayout(page)
        row = QHBoxLayout()
        for kind, title in [('work', 'Work…'), ('rights', 'Rights…'), ('delegation', 'Delegation…')]:
            self.button(row, title, lambda _=False, k=kind:self.add_record(k))
        layout.addLayout(row)
        split = QSplitter(Qt.Vertical)
        self.records = QTreeWidget(); self.records.setHeaderLabels(['Record', 'Title / recipient', 'State'])
        self.records.setRootIsDecorated(False); self.records.setAlternatingRowColors(True)
        self.records.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.records.setAccessibleName('Concern works, rights and delegations')
        self.records.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.records.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.records.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.records.currentItemChanged.connect(self.describe_record)
        self.record_detail = QPlainTextEdit(); self.record_detail.setReadOnly(True)
        self.record_detail.setAccessibleName('Selected Concern record details')
        split.addWidget(self.records); split.addWidget(self.record_detail); split.setSizes([290, 150]); layout.addWidget(split, 1)
        row = QHBoxLayout()
        self.button(row, 'Accept work…', self.accept_work)
        self.button(row, 'Revoke…', self.revoke)
        self.button(row, 'Save copy…', self.save_object)
        layout.addLayout(row)
        layout.addWidget(label('Source editions are fingerprinted. Acceptance records require written rights for the same bytes. Graphite account and source-merge approvals use their existing controls.'))
        self.pages.addTab(page, 'Concern register')

    def build_files(self):
        page = QWidget(); layout = QVBoxLayout(page)
        self.files = QTreeWidget(); self.files.setHeaderLabels(['Original / evidence file', 'Check', 'Bytes'])
        self.files.setRootIsDecorated(False); self.files.setAlternatingRowColors(True)
        self.files.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.files.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.files.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.files.setAccessibleName('Founding packet fingerprint checks')
        self.files.itemDoubleClicked.connect(lambda item,_:self.open_file(item.data(0, Qt.UserRole)))
        layout.addWidget(self.files, 1)
        row = QHBoxLayout()
        self.button(row, 'Open selected', self.open_selected)
        self.button(row, 'Save selected copy…', self.save_public)
        row.addStretch(); layout.addLayout(row)
        layout.addWidget(label('Original packet files are preserved byte for byte. The old preparation-status files remain historical inputs; Proof / execution shows current verification.'))
        self.pages.addTab(page, 'Files')

    def load_static(self):
        try:
            charter = self.store.charter()
            self.charter.setPlainText(charter)
            image = QPixmap(str(self.store.public_file('originals/complete/ARC_GENESIS_0001_Poster_Preview.png')))
            self.poster.setPixmap(image.scaled(190, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.refresh_registry()
        except (OSError, ValueError) as exc:
            self.notice.setText(str(exc))

    def _run(self, operation, verification=False):
        if self.busy:
            return
        self.busy = True
        for button in self.actions:
            button.setEnabled(False)
        if verification:
            self.report = None; self.summary.setText('Checking original bytes and signed timestamp evidence…')
        self.notice.setText('Working…')
        signals = self.signals
        def execute():
            try:
                value, error = operation(), None
            except Exception as exc:
                value, error = None, str(exc)
            try:
                signals.completed.emit(value, error)
            except RuntimeError:
                pass  # The owner closed the window; no UI object survives.
        threading.Thread(target=execute, daemon=True, name='arc-genesis-operation').start()

    def _completed(self, value, error):
        self.busy = False
        for button in self.actions:
            button.setEnabled(True)
        if error:
            self.notice.setText(error)
            if self.report is None:
                self.summary.setText('Verification unavailable · inspect the reported error')
            return
        if isinstance(value, dict) and value.get('schema') == 'arc.genesis-verification/1':
            self.report = value; self.show_report(value)
        else:
            self.verify_record()
        self.refresh_registry()
        if not self.busy:
            self.notice.setText('Checked locally · ' + utc_now())
        if hasattr(self.host, 'arc_inspector'):
            self.host.arc_inspector.refresh()

    def verify_record(self):
        self._run(self.store.verify, verification=True)

    def show_report(self, report):
        good = report['integrity']['ok']; stamped = report['timestamp_verified']
        self.summary.setText('<span style="color:' + ('#b7d5ac' if good else '#ffb3a6') + '">' +
                             ('Original bytes match' if good else 'ORIGINAL EVIDENCE MISMATCH') + '</span> · ' +
                             '<span style="color:' + ('#b7d5ac' if stamped else '#ffb3a6') + '">' +
                             ('Independent timestamp verified' if stamped else 'Timestamp not verified') + '</span> · ' +
                             '<span style="color:#efbd83">Founder execution unverified</span>')
        self.summary.setStyleSheet('')
        self.files.clear()
        for row in report['integrity']['files']:
            item = QTreeWidgetItem([row['path'], 'Matches' if row['ok'] else 'FAILED', str(row.get('bytes', ''))])
            item.setData(0, Qt.UserRole, row['path']); item.setToolTip(0, row.get('sha256', row.get('error', '')))
            self.files.addTopLevelItem(item)
        parts = ['<h2>Two times, two different kinds of evidence</h2>',
                 '<p><b>Recorded founding instant:</b> 25 October 2026, 01:52:34 Arizona / 08:52:34 UTC.<br>Original local-clock entry; not independently certified.</p>']
        for receipt in report['receipts']:
            if not receipt.get('verified'):
                parts.append('<h3>Timestamp could not be verified</h3><p>' + html.escape(receipt.get('error', 'Unknown error')) + '</p>')
                continue
            local = instant(receipt['issued_at']).astimezone(timezone(timedelta(hours=-7)))
            parts.append('<h3>' + html.escape(receipt['name']) + ' · verified RFC 3161 receipt</h3><p><b>Certified issue:</b> ' +
                         html.escape(receipt['issued_at']) + '<br>Arizona: ' + local.strftime('%d %B %Y, %H:%M:%S') +
                         '<br>Document fingerprint: matched<br>Original request / nonce: matched<br>Signature and pinned certificate chain: verified</p><p>' +
                         html.escape(receipt['trust_scope']) + '<br>' + html.escape(receipt['revocation']) + '</p>')
        parts.append('<h3>Founder execution</h3><p>The supplied declaration has a signature line. No verified founder signature or identity is claimed. Sign a separate execution copy yourself, then import that PDF here. You can timestamp its exact bytes separately.</p>')
        self.proof.setHtml(''.join(parts))

    def refresh_registry(self):
        selected = self.selected_record(); old_id = selected['id'] if selected else None
        current_target = self.target.currentData()
        self.target.clear(); self.target.addItem('Original canonical charter', 'canonical')
        self.records.clear()
        try:
            records = self.store.registry()
            for record in records:
                p = record['payload']; kind = record['type']
                title = p.get('title', p.get('recipient', p.get('contributor', p.get('filename', ''))))
                item = QTreeWidgetItem([kind.split('.')[0].title(), title, record['status']])
                item.setData(0, Qt.UserRole, record); self.records.addTopLevelItem(item)
                if record['id'] == old_id:
                    self.records.setCurrentItem(item)
                if kind == 'execution.copy':
                    self.target.addItem('Execution copy · ' + p['filename'], record['id'])
            if self.records.topLevelItemCount() == 0:
                self.record_detail.setPlainText('No local Concern records yet. Register a source work, record a written rights instrument, or record a scoped delegation. Nothing has been accepted automatically.')
        except (OSError, ValueError) as exc:
            self.record_detail.setPlainText(str(exc))
        index = self.target.findData(current_target)
        if index >= 0:
            self.target.setCurrentIndex(index)

    def selected_record(self):
        item = self.records.currentItem()
        return item.data(0, Qt.UserRole) if item else None

    def describe_record(self, item, _=None):
        if item:
            self.record_detail.setPlainText(json.dumps(item.data(0, Qt.UserRole), indent=2, ensure_ascii=False))

    def open_file(self, name):
        try:
            self.host.open_document(self.store.public_file(name), remember=False)
        except (OSError, ValueError) as exc:
            self.notice.setText(str(exc))

    def open_selected(self):
        item = self.files.currentItem()
        if item:
            self.open_file(item.data(0, Qt.UserRole))

    def save_public(self):
        item = self.files.currentItem()
        if not item:
            return
        try:
            source = self.store.public_file(item.data(0, Qt.UserRole))
            path, _ = QFileDialog.getSaveFileName(self, 'Save verified copy', source.name)
            if path:
                with Path(path).open('xb') as output:
                    output.write(read_bytes(source))
        except (OSError, ValueError) as exc:
            self.notice.setText(str(exc))

    def save_request(self):
        path, _ = QFileDialog.getSaveFileName(self, 'New timestamp request', 'ARC_GENESIS_0001.tsq', 'Timestamp request (*.tsq)')
        if path:
            target = self.target.currentData(); self._run(lambda:self.store.make_request(path, target))

    def timestamp(self):
        target = self.target.currentData(); provider = 'freetsa'
        try:
            fingerprint = __import__('hashlib').sha256(read_bytes(self.store.target(target))).hexdigest()
        except (OSError, ValueError) as exc:
            self.notice.setText(str(exc)); return
        answer = QMessageBox.question(self, 'Request an independent timestamp',
            'Send this SHA-256 fingerprint and a fresh request nonce to FreeTSA?\n\n' + fingerprint +
            '\n\nThe document itself stays on this computer.\n' + TRUST[provider]['endpoint'])
        if answer == QMessageBox.Yes:
            self._run(lambda:self.store.issue_timestamp(provider, FOUNDER, target))

    def import_receipt(self):
        response, _ = QFileDialog.getOpenFileName(self, 'Choose timestamp response', '', 'Timestamp response (*.tsr *.tst);;All files (*)')
        if not response:
            return
        request, _ = QFileDialog.getOpenFileName(self, 'Choose its original timestamp request', '', 'Timestamp request (*.tsq)')
        if request:
            target = self.target.currentData()
            self._run(lambda:self.store.import_receipt(response, request, 'freetsa', FOUNDER, target))

    def add_record(self, kind):
        dialog = RecordDialog(self.host, kind)
        if dialog.exec() != QDialog.Accepted:
            return
        values = dialog.values()
        operation = {'work':self.store.register_work, 'rights':self.store.register_rights,
                     'delegation':self.store.register_delegation, 'execution':self.store.execution_copy}[kind]
        self._run(lambda:operation(**values))

    def accept_work(self):
        record = self.selected_record()
        if not record or record['type'] != 'work.registered':
            self.notice.setText('Select a registered work first.'); return
        dialog = QDialog(self); dialog.setWindowTitle('Record founder acceptance'); dialog.resize(580, 450)
        layout = QVBoxLayout(dialog)
        layout.addWidget(label('Select the written-rights records you reviewed for this exact source edition.'))
        choices = QListWidget(); layout.addWidget(choices, 1)
        for row in self.store.registry():
            if row['type'] != 'rights.recorded':
                continue
            item = QListWidgetItem(row['payload']['contributor'] + ' · ' + row['payload']['basis'])
            item.setData(Qt.UserRole, row['id']); item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked); choices.addItem(item)
        note = QPlainTextEdit(); writing_prompt(note, 'Record your review of ownership, permitted uses and any limits.'); layout.addWidget(note)
        consent = QCheckBox('I reviewed these instruments and record acceptance of this source edition.'); layout.addWidget(consent)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
        if dialog.exec() != QDialog.Accepted:
            return
        if not consent.isChecked():
            self.notice.setText('Explicit owner review is required.'); return
        rights = [choices.item(i).data(Qt.UserRole) for i in range(choices.count()) if choices.item(i).checkState() == Qt.Checked]
        statement = note.toPlainText()
        self._run(lambda:self.store.accept_work(record['id'], rights, statement, FOUNDER))

    def revoke(self):
        record = self.selected_record()
        if not record or record['type'] != 'delegation.recorded':
            self.notice.setText('Select a recorded delegation first.'); return
        reason, ok = QInputDialog.getMultiLineText(self, 'Record delegation revocation', 'Reason / scope of revocation')
        if ok:
            self._run(lambda:self.store.revoke_delegation(record['id'], reason, FOUNDER))

    def save_object(self):
        record = self.selected_record()
        if not record:
            return
        payload = record['payload']; obj = payload.get('instrument', payload.get('document'))
        if not obj:
            self.notice.setText('Select a rights instrument, delegation, or execution copy.'); return
        path, _ = QFileDialog.getSaveFileName(self, 'Save recorded evidence copy', payload.get('filename', 'evidence.pdf'))
        if path:
            try:
                raw = read_bytes(self.store.object_file(obj))
                with Path(path).open('xb') as stream:
                    stream.write(raw)
                self.notice.setText('Saved a fingerprint-checked copy.')
            except (OSError, ValueError) as exc:
                self.notice.setText(str(exc))

    def export_evidence(self):
        dialog = QDialog(self); dialog.setWindowTitle('Export Genesis evidence')
        layout = QVBoxLayout(dialog)
        layout.addWidget(label('Export original packets, exact-byte fingerprints, receipt, certificates and a standalone verifier.'))
        include = QCheckBox('Also include my local register and private execution / agreement documents')
        include.setChecked(False); layout.addWidget(include)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
        if dialog.exec() != QDialog.Accepted:
            return
        path, _ = QFileDialog.getSaveFileName(self, 'New evidence archive', 'ARC_Genesis_Evidence.zip', 'ZIP archive (*.zip)')
        if path:
            selected = include.isChecked(); self._run(lambda:self.store.export(path, selected))
