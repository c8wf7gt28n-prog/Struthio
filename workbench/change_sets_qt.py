"""Changes: preview imports, edit drafts, review whole batches and recover updates."""
from __future__ import annotations
from .text_prompts import writing_prompt
import json
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QScrollArea, QSpinBox, QSplitter, QTabWidget, QVBoxLayout, QWidget)
from .shell2 import button, call_write, role


class ChangesTab(QWidget):
    def __init__(self, host):
        super().__init__(); self.host = host; self.workspace = None; self.preview = None; self.file = None; self.proposal = None; self.job = None; self.latest_commit = None
        self.busy = False
        self.setObjectName('LibraryTab'); self.setProperty('ledgerRoom', True)
        outer = QVBoxLayout(self); outer.setContentsMargins(20, 18, 20, 16)
        head = QHBoxLayout(); head.addWidget(role(QLabel('Changes'), 'title'), 1)
        refresh = button('Refresh', 'quiet'); refresh.clicked.connect(self.reload); head.addWidget(refresh); outer.addLayout(head)
        self.message = QLabel('Import a reviewed copy. Freeze changes before applying; originals have a separate update.'); self.message.setWordWrap(True); self.message.setTextFormat(Qt.PlainText); outer.addWidget(self.message)
        split = QSplitter(); outer.addWidget(split, 1)
        side = QWidget(); side_box = QVBoxLayout(side); side_box.addWidget(role(QLabel('WORKING COPIES'), 'section'))
        self.copies = QListWidget(); self.copies.setAccessibleName('Profiled working copies'); self.copies.itemClicked.connect(lambda i: self.open_workspace(i.data(Qt.UserRole))); side_box.addWidget(self.copies, 1)
        open_copy = button('Open working folder', 'quiet'); open_copy.clicked.connect(self.open_folder); side_box.addWidget(open_copy)
        export = button('Export working copy as new ZIP', 'quiet'); export.clicked.connect(self.export); side_box.addWidget(export)
        split.addWidget(side); self.pages = QTabWidget(); split.addWidget(self.pages); split.setStretchFactor(1, 1); split.setSizes([230, 850])
        self.build_import(); self.build_editor(); self.build_review(); self.reload()
        self.timer = QTimer(self); self.timer.setInterval(400); self.timer.timeout.connect(self.poll)

    def title(self): return 'Changes'
    def info(self): return 'Reviewed imports, frozen changes, original updates and recovery'

    def call(self, op, args=None):
        response = call_write(self.host, op, args or {})
        if not response.get('ok'): self.message.setText((response.get('error') or {}).get('message', 'That operation did not complete.')); return None
        return response['result']

    def run(self, op, args, done):
        """Reuse Ledger's existing Qt call worker for bulk disk operations."""
        if self.busy or self.host._closing: return
        from .register_tabs import Call
        from .engine import engineering
        from .engineering_kernel import operator
        from shiboken6 import isValid
        self.busy = True; self.pages.setEnabled(False); self.copies.setEnabled(False)
        self.message.setText('Reading and verifying bytes… The current operation is recorded; do not submit it twice.')
        if not hasattr(self.host, 'service_workers'): self.host.service_workers = []
        epoch = getattr(self.host, '_operation_epoch', 0)
        worker = Call(engineering(self.host.root), op, args, operator(), self.host); self.host.service_workers.append(worker)
        def ready(response):
            if not isValid(self) or self.host._closing: return
            self.busy = False; self.pages.setEnabled(True); self.copies.setEnabled(True)
            if epoch != getattr(self.host, '_operation_epoch', 0): self.message.setText('Stopped. Refresh and inspect the batch journal.'); return
            if not response.get('ok'): self.message.setText((response.get('error') or {}).get('message', 'Inspect the saved record before retrying.')); return
            done(response['result'])
        worker.ready.connect(ready)
        worker.finished.connect(lambda: self.host.service_workers.remove(worker) if worker in self.host.service_workers else None)
        worker.finished.connect(worker.deleteLater); worker.start()

    def build_import(self):
        page = QWidget(); box = QVBoxLayout(page)
        self.source = QLineEdit(); writing_prompt(self.source, 'A project folder or ZIP in your home folder'); box.addWidget(self.source)
        row = QHBoxLayout()
        folder = button('Choose folder', 'quiet'); folder.clicked.connect(self.pick_folder); row.addWidget(folder)
        archive = button('Choose ZIP', 'quiet'); archive.clicked.connect(self.pick_zip); row.addWidget(archive); box.addLayout(row)
        form = QFormLayout(); self.profile = QComboBox()
        for title, key in [('Mixed project', 'MIXED'), ('Notes and documents', 'NOTES'), ('Code and reviewed configuration', 'CODE'), ('Tables and data', 'TABLES'), ('Engineering sources', 'ENGINEERING')]: self.profile.addItem(title, key)
        form.addRow('Import profile', self.profile)
        self.file_limit = QSpinBox(); self.file_limit.setRange(1, 5000); self.file_limit.setValue(2000); form.addRow('Included file limit', self.file_limit)
        self.total_limit = QSpinBox(); self.total_limit.setRange(1, 2048); self.total_limit.setValue(512); form.addRow('Total MiB limit', self.total_limit)
        self.byte_limit = QSpinBox(); self.byte_limit.setRange(1, 256); self.byte_limit.setValue(64); form.addRow('Per-file MiB limit', self.byte_limit)
        box.addLayout(form)
        self.for_slate = QCheckBox('Delegate draft preparation in this copy to Graphite'); box.addWidget(self.for_slate)
        preview = button('Preview what comes in', 'primary'); preview.clicked.connect(self.preview_import); box.addWidget(preview)
        self.import_review = QPlainTextEdit(); self.import_review.setReadOnly(True); self.import_review.setAccessibleName('Included and excluded import files'); box.addWidget(self.import_review, 1)
        accept = button('Accept preview and create working copy', 'primary'); accept.clicked.connect(self.accept_import); box.addWidget(accept)
        self.pages.addTab(page, 'Import')

    def pick_folder(self):
        name = QFileDialog.getExistingDirectory(self, 'Choose project folder')
        if name: self.source.setText(name); self.preview = None

    def pick_zip(self):
        name, _ = QFileDialog.getOpenFileName(self, 'Choose ZIP project', '', 'ZIP archive (*.zip)')
        if name: self.source.setText(name); self.preview = None

    def preview_import(self):
        self.run('imports.preview', {'source': self.source.text(), 'profile': self.profile.currentData(), 'limits': self.limits()}, self.show_import)

    def show_import(self, value):
        self.preview = value
        self.source.setText(value['source'])
        lines = ['%d files · %.2f MiB · originals will remain in place' % (len(value['files']), value['bytes'] / 1048576)]
        for entry in value['entries']:
            lines.append(entry['state'].lower() + ' · ' + entry['path'] + (' · duplicate of ' + entry['duplicate_of'] if entry.get('duplicate_of') else '') + (' · ' + entry['reason'].replace('_', ' ').lower() if entry.get('reason') else ''))
        self.import_review.setPlainText('\n'.join(lines)); self.message.setText('Read the inclusion and exclusion list, then accept this exact preview.')

    def accept_import(self):
        if not self.preview: self.message.setText('Preview this source first.'); return
        if self.source.text() != self.preview['source'] or self.profile.currentData() != self.preview['profile'] or self.limits() != self.preview['limits']:
            self.message.setText('The source or profile changed; preview it again.'); return
        def accepted(result):
            self.open_workspace(result['id']); self.reload(); self.pages.setCurrentIndex(1); self.message.setText('Working copy created. The original was not moved or changed.')
        self.run('imports.accept', {'id': self.preview['id'], 'expected_digest': self.preview['content_digest'], 'for_slate': self.for_slate.isChecked()}, accepted)

    def limits(self):
        return {'files': self.file_limit.value(), 'total_bytes': self.total_limit.value() * 1048576, 'file_bytes': self.byte_limit.value() * 1048576}

    def build_editor(self):
        scroll = QScrollArea(); scroll.setWidgetResizable(True); body = QWidget(); box = QVBoxLayout(body); scroll.setWidget(body)
        self.files = QComboBox(); self.files.setEditable(True); self.files.setAccessibleName('Working file'); box.addWidget(self.files)
        load = button('Open file in draft editor', 'quiet'); load.clicked.connect(self.open_file); box.addWidget(load)
        self.editor = QPlainTextEdit(); self.editor.setAccessibleName('Draft text editor'); self.editor.setMinimumHeight(220); box.addWidget(self.editor, 1)
        row = QHBoxLayout()
        for label, fn in [('Stage text', self.stage_text), ('Add file', self.add_file), ('Remove file', self.remove_file), ('Rename', self.rename_file), ('Cell change', self.cell_change)]:
            b = button(label, 'quiet'); b.clicked.connect(fn); row.addWidget(b)
        box.addLayout(row)
        self.operations = QPlainTextEdit(); self.operations.setAccessibleName('Staged operations'); self.operations.setPlainText('[]'); self.operations.setMaximumHeight(145); box.addWidget(self.operations)
        self.note = QLineEdit(); writing_prompt(self.note, 'Why are these changes useful?'); box.addWidget(self.note)
        freeze = button('Freeze staged changes for review', 'primary'); freeze.clicked.connect(self.freeze); box.addWidget(freeze)
        box.addWidget(role(QLabel('ASK GRAPHITE FOR A TEXT DRAFT'), 'section'))
        self.goal = QPlainTextEdit(); writing_prompt(self.goal, 'Describe the change. No files will be applied by this request.'); self.goal.setMaximumHeight(100); box.addWidget(self.goal)
        self.model_paths = QLineEdit(); writing_prompt(self.model_paths, 'Selected text paths separated by commas (up to eight)'); box.addWidget(self.model_paths)
        ask = button('Ask local Graphite to propose the batch', 'quiet'); ask.clicked.connect(self.ask); box.addWidget(ask)
        stop = button('Stop this draft', 'quiet'); stop.clicked.connect(lambda: self.call('jobs.cancel', {'id': self.job}) if self.job else None); box.addWidget(stop)
        self.model_text = QLabel(); self.model_text.setWordWrap(True); self.model_text.setTextFormat(Qt.PlainText); box.addWidget(self.model_text)
        self.pages.addTab(scroll, 'Draft')

    def open_file(self):
        if not self.workspace: self.message.setText('Select a working copy first.'); return
        value = self.call('changes.file', {'copy': self.workspace['id'], 'path': self.files.currentText()})
        if value:
            self.file = value; self.editor.setPlainText(value.get('text') or '')
            self.editor.setReadOnly(value.get('text') is None)
            self.message.setText(value.get('adapter_limit') or value.get('limits') or 'Edit the draft, then stage it. Saving a proposal does not change this file.')

    def stage(self, operation):
        try: current = json.loads(self.operations.toPlainText())
        except ValueError: self.message.setText('The staged operations must be a JSON list.'); return
        if not isinstance(current, list): self.message.setText('The staged operations must be a list.'); return
        merged = False
        for index, old in enumerate(current):
            if old.get('path') == operation['path'] and old.get('base_sha256') == operation.get('base_sha256'):
                if old.get('op') == operation['op'] == 'CELLS' and old.get('sheet') == operation.get('sheet'):
                    old['cells'].extend(operation['cells']); merged = True; break
                if old.get('op') == operation['op'] == 'WRITE': current[index] = operation; merged = True; break
        if not merged: current.append(operation)
        self.operations.setPlainText(json.dumps(current, ensure_ascii=False, indent=2))
        self.message.setText('Change staged for review. No file changed.')

    def stage_text(self):
        if self.file and self.file.get('text') is not None:
            text = self.editor.toPlainText()
            if '\r\n' in self.file['text'] and '\n' not in self.file['text'].replace('\r\n', ''): text = text.replace('\r\n', '\n').replace('\n', '\r\n')
            self.stage({'op': 'WRITE', 'path': self.file['path'], 'base_sha256': self.file['sha256'], 'text': text})

    def add_file(self):
        path, ok = QInputDialog.getText(self, 'Add text file', 'New relative path:')
        if ok: self.stage({'op': 'CREATE', 'path': path, 'text': self.editor.toPlainText()})

    def remove_file(self):
        if self.file: self.stage({'op': 'DELETE', 'path': self.file['path'], 'base_sha256': self.file['sha256']})

    def rename_file(self):
        if not self.file: return
        path, ok = QInputDialog.getText(self, 'Rename file', 'New relative path:')
        if ok: self.stage({'op': 'RENAME', 'path': self.file['path'], 'base_sha256': self.file['sha256'], 'to': path})

    def cell_change(self):
        if not self.file or not self.workspace or not self.file.get('sheets'): self.message.setText('Open an editable CSV, TSV or supported XLSX first.'); return
        sheet, ok = QInputDialog.getItem(self, 'Change cell', 'Sheet:', self.file['sheets'], 0, False)
        if not ok: return
        cell, ok = QInputDialog.getText(self, 'Change cell', 'Cell address:', text='B2')
        if not ok: return
        value = self.call('changes.cell', {'copy': self.workspace['id'], 'path': self.file['path'], 'sheet': sheet, 'cell': cell})
        if value is None: return
        kind, ok = QInputDialog.getItem(self, 'New cell type', 'Type:', ['TEXT', 'NUMBER', 'BOOLEAN', 'FORMULA', 'EMPTY'], 0, False)
        if not ok: return
        text, ok = QInputDialog.getText(self, 'New cell value', 'Current: ' + json.dumps(value['cell'], ensure_ascii=False) + '\nNew value:', text=value['cell']['value'])
        if ok: self.stage({'op': 'CELLS', 'path': self.file['path'], 'base_sha256': value['sha256'], 'sheet': sheet,
            'cells': [{'cell': cell, 'old': value['cell'], 'new': {'kind': kind, 'value': text if kind != 'EMPTY' else ''}}]})

    def freeze(self):
        if not self.workspace: self.message.setText('Select a working copy first.'); return
        try: operations = json.loads(self.operations.toPlainText())
        except ValueError: self.message.setText('Staged changes are not valid JSON.'); return
        def frozen(value): self.operations.setPlainText('[]'); self.load_review(value['id']); self.reload()
        self.run('changes.propose', {'copy': self.workspace['id'], 'operations': operations, 'note': self.note.text()}, frozen)

    def build_review(self):
        page = QWidget(); box = QVBoxLayout(page)
        self.proposals = QComboBox(); self.proposals.setAccessibleName('Frozen proposal'); box.addWidget(self.proposals)
        load = button('Review selected proposal', 'quiet'); load.clicked.connect(lambda: self.load_review(self.proposals.currentData())); box.addWidget(load)
        self.review_text = QPlainTextEdit(); self.review_text.setReadOnly(True); self.review_text.setAccessibleName('Whole frozen change set'); box.addWidget(self.review_text, 1)
        row = QHBoxLayout()
        for label, fn in [('Read frozen bytes', self.read_frozen), ('Apply to working copy', self.apply), ('Preview original update', self.preview_original), ('Update originals', self.publish)]:
            b = button(label, 'quiet'); b.clicked.connect(fn); row.addWidget(b)
        box.addLayout(row)
        self.commits = QComboBox(); self.commits.setAccessibleName('Batch journal'); box.addWidget(self.commits)
        row = QHBoxLayout()
        for label, fn in [('Inspect recovery', self.inspect_commit), ('Resume selected batch', self.resume), ('Undo or roll back', self.undo)]:
            b = button(label, 'quiet'); b.clicked.connect(fn); row.addWidget(b)
        box.addLayout(row); self.pages.addTab(page, 'Review and recover')

    def reload(self):
        if self.busy: return
        current = self.workspace['id'] if self.workspace else None
        value = self.call('changes.workspaces')
        if value is None: return
        self.copies.clear()
        for w in value['workspaces']:
            item = QListWidgetItem(w['name'] + '\n' + w['profile'].lower()); item.setData(Qt.UserRole, w['id']); self.copies.addItem(item)
            if w['id'] == current: self.copies.setCurrentItem(item)
        if current: self.open_workspace(current)

    def open_workspace(self, ident):
        value = self.call('changes.workspace', {'id': ident})
        if value is None: return
        if not self.workspace or self.workspace['id'] != ident:
            self.file = None; self.editor.clear(); self.operations.setPlainText('[]'); self.proposal = None; self.review_text.clear()
        self.workspace = value; selected_file = self.files.currentText(); self.files.clear(); self.files.addItems(sorted(value['files']))
        if value.get('unavailable'): self.message.setText('Working copy needs attention: ' + value['unavailable'])
        if selected_file in value['files']: self.files.setCurrentText(selected_file)
        self.proposals.clear()
        for p in value['proposals']: self.proposals.addItem(p['target'].lower() + ' · ' + (p['note'][:65] or p['id'][:8]), p['id'])
        records = self.call('changes.commits', {'copy': ident}); self.commits.clear()
        for c in (records or {}).get('commits', []): self.commits.addItem(c['state'].lower() + ' · ' + c['target'].lower() + ' · ' + c['id'][:8], c['id'])

    def open_folder(self):
        if self.workspace:
            from .shell2 import open_destination
            open_destination(self.host, 'files:' + self.workspace['work'])

    def export(self):
        if self.workspace:
            self.run('changes.export', {'copy': self.workspace['id']}, lambda value: self.message.setText('Exported with reviewed configuration: ' + value['export'] + '. Originals unchanged.'))

    def load_review(self, ident):
        if not ident: return
        value = self.call('changes.review', {'id': ident})
        if value is None: return
        self.proposal = value['proposal']; p = self.proposal
        lines = [p['target'] + ' · ' + value['state'], p['note'], 'Origin: ' + p['provenance'].get('origin', 'HUMAN')]
        for change in p['changes']:
            lines += ['', change['operation'] + ' · ' + change['path'], 'Before: ' + str(change['before']), 'After: ' + str(change['after'])]
            if change.get('adapter_report'): lines.append(json.dumps(change['adapter_report'], ensure_ascii=False, indent=2))
            lines.append(change['diff'] or 'Binary or large bytes: use Read frozen bytes to inspect the retained object.')
            if change['diff_cut']: lines.append('Diff display is shortened; the full frozen bytes remain available.')
        lines += ['', 'Checks: ' + json.dumps(p['checks'], ensure_ascii=False), 'Conflicts: ' + ', '.join(value['conflicts']), value['checks_meaning']]
        self.review_text.setPlainText('\n'.join(lines)); self.pages.setCurrentIndex(2)

    def apply(self):
        if self.proposal:
            def applied(value): self.reload(); self.message.setText('Working batch: ' + value['state'] + '. Original files were not updated.')
            self.run('changes.apply', {'id': self.proposal['id'], 'expected_digest': self.proposal['content_digest']}, applied)

    def preview_original(self):
        if self.workspace:
            def previewed(value): self.load_review(value['id']); self.reload(); self.message.setText('Review this separate original-file proposal before updating originals.')
            self.run('changes.original.preview', {'copy': self.workspace['id']}, previewed)

    def publish(self):
        if self.proposal:
            def published(value): self.reload(); self.message.setText('Original update: ' + value['state'] + '. Recovery bytes and journal are retained.')
            self.run('changes.publish', {'id': self.proposal['id'], 'expected_digest': self.proposal['content_digest']}, published)

    def inspect_commit(self):
        if self.commits.currentData():
            value = self.call('changes.commit', {'id': self.commits.currentData()})
            if value: self.detail('Batch journal and observed files', value)

    def resume(self):
        if self.commits.currentData():
            def resumed(value): self.reload(); self.message.setText('Recovery: ' + value['state'])
            self.run('changes.recover', {'id': self.commits.currentData(), 'action': 'RESUME'}, resumed)

    def undo(self):
        if self.commits.currentData():
            def undone(value): self.reload(); self.message.setText('Undo or partial rollback: ' + value['state'])
            self.run('changes.undo', {'id': self.commits.currentData()}, undone)

    def detail(self, title, value):
        dialog = QDialog(self); dialog.setWindowTitle(title); dialog.resize(850, 650); box = QVBoxLayout(dialog)
        text = QPlainTextEdit(); text.setReadOnly(True); text.setPlainText(json.dumps(value, ensure_ascii=False, indent=2)); box.addWidget(text); dialog.exec()

    def read_frozen(self):
        if not self.proposal: return
        path, ok = QInputDialog.getItem(self, 'Read frozen file', 'Path:', [c['path'] for c in self.proposal['changes']], 0, False)
        if not ok: return
        side, ok = QInputDialog.getItem(self, 'Frozen revision', 'Revision:', ['AFTER', 'BEFORE'], 0, False)
        if not ok: return
        dialog = QDialog(self); dialog.setWindowTitle('Frozen bytes · ' + path); dialog.resize(850, 650); box = QVBoxLayout(dialog)
        text = QPlainTextEdit(); text.setReadOnly(True); box.addWidget(text, 1); next_button = button('Read next 64 KiB', 'quiet'); box.addWidget(next_button); offset = 0
        def more():
            nonlocal offset
            value = self.call('changes.content', {'id': self.proposal['id'], 'path': path, 'side': side, 'offset': offset})
            if value is None: return
            text.appendPlainText(value['text'] if value['text'] is not None else 'Binary chunk in base64:\n' + value['base64'])
            offset += value.get('chunk_bytes', 0); next_button.setEnabled(value['has_more'])
        next_button.clicked.connect(more); more(); dialog.exec()

    def ask(self):
        if not self.workspace or self.job: self.message.setText('Select a copy and finish any current reply first.'); return
        paths = [p.strip() for p in self.model_paths.text().split(',') if p.strip()] or [self.files.currentText()]
        value = self.call('changes.ask', {'copy': self.workspace['id'], 'goal': self.goal.toPlainText(), 'paths': paths})
        if value: self.job = value['id']; self.model_text.setText('Drafting locally. No file will be applied.'); self.timer.start()

    def poll(self):
        if self.busy: return
        if not self.job: self.timer.stop(); return
        progress = self.call('slate.progress', {'job': self.job})
        if progress is None: return
        if progress.get('display_text'): self.model_text.setText('Draft · not checked: ' + progress['display_text'])
        if progress.get('job_state', progress['state']) not in ('Completed', 'Failed', 'Cancelled', 'Interrupted'): return
        ident = self.job; self.job = None; self.timer.stop(); result = self.call('slate.result', {'job': ident})
        proposal = ((result or {}).get('result') or {}).get('proposal_id')
        if proposal: self.load_review(proposal); self.reload(); self.model_text.setText('Complete model draft frozen for owner review. No file was applied.')
        else: self.model_text.setText('No complete change set was produced. Inspect the job or adjust the selected files and output budget.')


def show(host):
    host._close_start()
    for i in range(host.tabs.count()):
        tab = host.tabs.widget(i)
        if isinstance(tab, ChangesTab): host.tabs.setCurrentWidget(tab); tab.reload(); return tab
    tab = ChangesTab(host); host.tabs.addTab(tab, tab.title()); host.tabs.setCurrentWidget(tab); return tab
