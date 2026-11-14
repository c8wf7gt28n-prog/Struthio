"""The Office building: one place to receive work, read it as staC, ask the brain and watch it learn.

Rooms use the shared Kernel only: ``receiving.*`` for deliveries, ``language.run`` /
``stac.run`` for staC, ``brain.*`` for the replaceable local model and
``matrix.*`` for the instruction matrix. Drop files anywhere to receive them;
drop a GGUF file or model folder to replace the brain.
"""
from .assistant_identity import named
from .text_prompts import writing_prompt
import json
import uuid
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget)
from .register_tabs import ServiceTab
from .stac_bridge import route_program

ACCEPT_REASON = 'Owner received these files through the Office'
STAGE_WORDS = {'SCANNING': 'Snapshotting files', 'REVIEWING': 'Reading each file', 'REVIEWED': 'Waiting for you to accept',
               'INDEXING': 'Building the catalog', 'CATALOGED': 'Cataloged', 'FAILED': 'Stopped'}
MOVING = ('SCANNING', 'REVIEWING', 'INDEXING')


def short_path(path):
    """A path as people say it: ~/Concern/Office/Ingress rather than the full path from the root of the disk."""
    path = Path(path)
    try:return '~/' + path.relative_to(Path.home()).as_posix()
    except ValueError:return str(path)


def is_brain(path):
    path = Path(path)
    return path.suffix.lower() == '.gguf' or path.is_dir() and any(path.glob('*.gguf'))


def readable_result(value):
    """The answer first: rows or hits as plain lines; the raw result follows below."""
    rows = value.get('rows') if isinstance(value, dict) else None
    hits = (value.get('result') or {}).get('hits') if isinstance(value, dict) and isinstance(value.get('result'), dict) else None
    if rows is not None:
        if not rows:return 'No rows.'
        lines = []
        for row in rows[:50]:
            if isinstance(row, dict):lines += [k + ': ' + (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))[:2000] for k, v in row.items()] + ['']
            else:lines.append(str(row)[:2000])
        return '\n'.join(lines).strip() + ('\n… %d more rows' % (len(rows) - 50) if len(rows) > 50 else '')
    if hits is not None:
        if not hits:return 'Nothing found.'
        return '\n\n'.join('%s · %s\n%s' % (h.get('item', '')[:8], h.get('label', ''), (h.get('text') or '').strip()[:600]) for h in hits[:20])
    if isinstance(value, dict) and value.get('state') == 'BLOCKED':return 'Blocked: ' + str(value.get('reason'))
    if isinstance(value, dict) and isinstance(value.get('object'), dict):
        # An address read: show what the object says, not the envelope.
        obj = value['object']
        if isinstance(obj.get('text'), str):return ((obj.get('name') or value.get('address', '')) + '\n\n' + obj['text'].strip()[:4000]).strip()
        return '\n'.join(k + ': ' + (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))[:300] for k, v in list(obj.items())[:12])
    return 'Done.'


def pretty(value):
    return json.dumps(value, indent=2, ensure_ascii=False)


class OfficeBuildingTab(ServiceTab):
    """The Office room: receive files and read them as staC."""
    HEADING = 'Office'
    LEAD = 'Drop files anywhere here to receive them. Originals are never changed; nothing leaves this computer.'
    PAGES = (('receiving_room', 'Receiving'), ('catalog_room', 'Catalog · lines'))

    def __init__(self, host):
        super().__init__(host)
        self.setAcceptDrops(True);self.setProperty('ledgerRoom', True)
        self.deliveries = [];self.cards = [];self.brain_job = None;self.plan_job = None;self.proposal = None;self._models = []
        title = QLabel(self.HEADING);title.setProperty('arcRole', 'section');title.setStyleSheet('font-size:18px;color:#edaa69;font-weight:bold')
        lead = QLabel(self.LEAD);lead.setWordWrap(True);lead.setStyleSheet('color:#b5bec8')
        head = QHBoxLayout();head.addWidget(title);head.addWidget(lead, 1);self.outer.addLayout(head);self.outer.addWidget(self.status)
        self.rooms = QTabWidget();self.rooms.setAccessibleName(self.HEADING + ' rooms');self.outer.addWidget(self.rooms, 1)
        for builder, label in self.PAGES:self.rooms.addTab(getattr(self, builder)(), label)
        self.timer = QTimer(self);self.timer.setInterval(1000);self.timer.timeout.connect(self.tick);self.timer.start()
        self.refresh()

    def title(self):return self.HEADING

    def info(self):return ' · '.join(label for _, label in self.PAGES)

    def has(self, name):return hasattr(self, name)

    def inspector(self):
        """What the Inspector shows for this room: the selected delivery or card, or the room's state."""
        sections = []
        if self.has('delivery_tree'):
            waiting = len(getattr(self, '_inbox_waiting', []))
            moving = [d for d in self.deliveries if d['stage'] in MOVING]
            reviewed = [d for d in self.deliveries if d['stage'] == 'REVIEWED']
            sections.append(('Ingress', ('%d new' % waiting) if waiting else 'Nothing new'))
            sections.append(('Deliveries', '%d in progress · %d waiting for you · %d cataloged' % (
                len(moving), len(reviewed), sum(1 for d in self.deliveries if d['stage'] == 'CATALOGED'))))
            page = self.rooms.currentIndex()
            item = self.card_list.currentItem() if page == 1 else None
            card = next((c for c in self.cards if item and c['address'] == item.data(0, Qt.UserRole)), None)
            if card:
                sections += [('Selected file', card['name']), ('Address', '@' + card['address']),
                             ('Programs', '\n'.join(p['program'] for p in card['programs'])), ('Summary', card['summary'] or '(no text)')]
            else:
                d = next((x for x in self.deliveries if x['id'] == self.selected_delivery_id()), None)
                if d:
                    sections += [('Selected delivery', d['label']), ('Stage', STAGE_WORDS.get(d['stage'], d['stage'])),
                                 ('Files', '%d accepted · %d held · %d not accepted' % (len(d['accepted']), len(d['held']), len(d['rejected'])))]
                    if d.get('error'):sections.append(('Problem', d['error']))
        if self.has('brain_state'):
            sections.append(('Brain', self.brain_state.text().replace('Brain: ', '')))
            if getattr(self, 'proposal', None):
                sections.append(('Proposal', '\n'.join(a['operation'] for a in self.proposal.get('actions', [])) or 'No program proposed'))
        if self.has('matrix_state'):
            sections.append(('Instruction matrix', self.matrix_state.text().split('. ')[0]))
            item = self.row_tree.currentItem()
            if item:sections.append(('Selected instruction', (item.text(2) or '(a direct line)') + '\n' + item.text(3) + '\n' + item.text(0) + (' · ' + item.text(4) if item.text(4) else '')))
        sections.append(('Privacy', 'On this computer · cloud calls 0'))
        return self.HEADING, sections

    def tell_inspector(self):
        inspector = getattr(self.host, 'arc_inspector', None)
        if inspector is not None and self.host.tabs.currentWidget() is self:inspector.refresh()

    # Rooms --------------------------------------------------------------

    def receiving_room(self):
        page = QWidget();box = QVBoxLayout(page)
        # 4.1: one sentence instead of a row of buttons; the words are the actions.
        from .shell2 import sentence
        box.addWidget(sentence('Receive {files}, a {folder}, or {inbox}.',
                               {'files': ('files', self.pick_files), 'folder': ('folder', self.pick_folder), 'inbox': ('everything that arrived', self.receive_inbox)}))
        self.inbox_label = QLabel();self.inbox_label.setWordWrap(True);box.addWidget(self.inbox_label)
        self.auto_accept = QCheckBox('Accept reviewed files on arrival')
        self.auto_accept.setToolTip('Files that pass review and only wait for your decision are accepted into the catalog. '
                                    'Files with problems stay held for you.')
        box.addWidget(self.auto_accept)
        split = QSplitter(Qt.Vertical)
        self.delivery_tree = QTreeWidget();self.delivery_tree.setHeaderLabels(['Delivery', 'Stage', 'Files', 'Accepted', 'Held']);self.delivery_tree.setRootIsDecorated(False)
        self.delivery_tree.setColumnWidth(0, 230);self.delivery_tree.setAccessibleName('Deliveries');self.delivery_tree.itemSelectionChanged.connect(self.show_delivery)
        split.addWidget(self.delivery_tree)
        self.delivery_detail = QPlainTextEdit();self.delivery_detail.setReadOnly(True);self.delivery_detail.setAccessibleName('Delivery details');split.addWidget(self.delivery_detail)
        box.addWidget(split, 1)
        # The delivery's actions appear under it only when one is selected, and only those that apply.
        actions = QHBoxLayout()
        self.accept_button = accept = QPushButton('Accept reviewed files');accept.setProperty('arcButton', 'primary');accept.clicked.connect(self.accept_selected);actions.addWidget(accept)
        self.again_button = again = QPushButton('Receive again');again.setToolTip('Receive the selected delivery\'s original files again, for example after a restart stopped it.')
        again.clicked.connect(self.receive_again);actions.addWidget(again);actions.addStretch(1);box.addLayout(actions)
        accept.hide();again.hide()
        return page

    def catalog_room(self):
        page = QWidget();box = QVBoxLayout(page)
        row = QHBoxLayout();self.card_source = QComboBox();self.card_source.setAccessibleName('Delivery to read');row.addWidget(self.card_source, 1)
        load = QPushButton('Show reading cards');load.clicked.connect(self.load_cards);row.addWidget(load)
        view = QPushButton('View file');view.setToolTip('Open the selected file in the universal viewer');view.clicked.connect(self.view_card);row.addWidget(view)
        box.addLayout(row)
        split = QSplitter(Qt.Horizontal)
        self.card_list = QTreeWidget();self.card_list.setHeaderLabels(['File', 'Characters']);self.card_list.setColumnWidth(0, 230)
        self.card_list.setAccessibleName('Reading cards');self.card_list.itemSelectionChanged.connect(self.show_card);split.addWidget(self.card_list)
        right = QWidget();rbox = QVBoxLayout(right);rbox.setContentsMargins(0, 0, 0, 0)
        self.card_view = QPlainTextEdit();self.card_view.setReadOnly(True);self.card_view.setAccessibleName('Reading card');rbox.addWidget(self.card_view, 1)
        self.program = QLineEdit();writing_prompt(self.program, 'A line, for example @intake:… | select text');self.program.setAccessibleName('Line')
        self.program.returnPressed.connect(self.run_program);rbox.addWidget(self.program)
        prow = QHBoxLayout()
        self.card_programs = QComboBox();self.card_programs.setAccessibleName('Programs on this card');self.card_programs.currentIndexChanged.connect(self.pick_program);prow.addWidget(self.card_programs, 1)
        run = QPushButton('Run the line');run.clicked.connect(self.run_program);prow.addWidget(run);rbox.addLayout(prow)
        mrow = QHBoxLayout()
        for label, mark in (('Result was right', 'GOOD'), ('Result was wrong', 'BAD')):
            button = QPushButton(label);button.clicked.connect(lambda checked=False, m=mark:self.mark_last(m));mrow.addWidget(button)
        rbox.addLayout(mrow)
        self.run_view = QPlainTextEdit();self.run_view.setReadOnly(True);self.run_view.setAccessibleName('Result');rbox.addWidget(self.run_view, 1)
        split.addWidget(right);box.addWidget(split, 1)
        return page

    def brain_room(self):
        page = QWidget();box = QVBoxLayout(page)
        self.brain_state = QLabel('Brain: checking…');self.brain_state.setWordWrap(True);box.addWidget(self.brain_state)
        swap = QLabel('Graphite inspects a dropped model first and switches only when it loads. "Restore previous" goes back.')
        swap.setWordWrap(True);box.addWidget(swap)
        row = QHBoxLayout()
        for label, fn in (('Choose model file…', self.pick_model), ('Restore previous', self.restore_brain), ('Stop brain', self.stop_brain), ('Open Brain panel', self.open_brain)):
            button = QPushButton(label);button.clicked.connect(fn);row.addWidget(button)
        box.addLayout(row)
        ask = QLabel('Ask in plain words. Graphite proposes a line from what worked before; nothing runs until you choose Run proposal.');ask.setWordWrap(True);box.addWidget(ask)
        self.request = QLineEdit();writing_prompt(self.request, 'For example: show the text of the memo I received');self.request.setAccessibleName('Request for Graphite')
        self.request.returnPressed.connect(self.ask_plan);box.addWidget(self.request)
        arow = QHBoxLayout()
        plan = QPushButton(named('Ask Stacy to plan'));plan.clicked.connect(self.ask_plan);arow.addWidget(plan)
        self.run_plan_button = QPushButton('Run proposal');self.run_plan_button.setEnabled(False);self.run_plan_button.clicked.connect(self.run_proposal);arow.addWidget(self.run_plan_button)
        box.addLayout(arow)
        self.plan_view = QPlainTextEdit();self.plan_view.setReadOnly(True);self.plan_view.setAccessibleName('Graphite proposal');box.addWidget(self.plan_view, 1)
        return page

    def matrix_room(self):
        page = QWidget();box = QVBoxLayout(page)
        self.matrix_state = QLabel();self.matrix_state.setWordWrap(True);box.addWidget(self.matrix_state)
        split = QSplitter(Qt.Vertical)
        self.pattern_tree = QTreeWidget();self.pattern_tree.setHeaderLabels(['Pattern', 'Tries', 'Worked', 'Empty', 'Failed', 'Rate', 'Main failure'])
        self.pattern_tree.setColumnWidth(0, 300);self.pattern_tree.setAccessibleName('Instruction patterns');split.addWidget(self.pattern_tree)
        self.row_tree = QTreeWidget();self.row_tree.setHeaderLabels(['Outcome', 'Mark', 'Instruction', 'Program', 'Reason'])
        self.row_tree.setColumnWidth(2, 220);self.row_tree.setColumnWidth(3, 260);self.row_tree.setAccessibleName('Recent instructions');split.addWidget(self.row_tree)
        self.row_tree.itemSelectionChanged.connect(self.tell_inspector)
        box.addWidget(split, 1)
        grid = QGridLayout()
        for index, (label, fn) in enumerate((('Refresh', self.refresh_matrix), ('Mark selected right', lambda:self.mark_selected('GOOD')),
                                             ('Mark selected wrong', lambda:self.mark_selected('BAD')), ('Promote pattern to lesson…', self.promote),
                                             ('Export training set…', self.export_matrix), ('Forget everything…', self.forget_matrix))):
            button = QPushButton(label);button.clicked.connect(fn);grid.addWidget(button, index // 3, index % 3)
        box.addLayout(grid)
        return page

    # Receiving ----------------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and all(u.isLocalFile() for u in event.mimeData().urls()):event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        event.acceptProposedAction()
        for path in paths:
            if is_brain(path):self.slate_room().replace_brain(path)
            else:self.office_room().receive(path)

    def slate_room(self):
        return self if self.has('brain_state') else self.host.ledger_bridge.navigation()['slate']()

    def office_room(self):
        return self if self.has('delivery_tree') else self.host.ledger_bridge.navigation()['office']()

    def pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Receive files', str(Path.home()))
        for path in files:self.receive(path)

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Receive folder', str(Path.home()))
        if folder:self.receive(folder)

    def receive_inbox(self):
        if not getattr(self, 'inbox', None):self.status.setText('This workspace has no Ingress folder. Receive files or a folder instead.');return
        if not any(Path(self.inbox).iterdir()):self.status.setText('Nothing new has come in: ' + self.inbox);return
        self.receive(self.inbox, 'Ingress')

    def receive(self, path, label=None):
        self.status.setText('Receiving ' + Path(path).name + '…')
        args = {'path': str(path), 'request_key': uuid.uuid4().hex}
        if label:args['label'] = label
        self.call('receiving.receive', args, lambda value:(self.status.setText('Received ' + value['label'] + ' · ' + str(len(value['revived'])) + ' files'), self.refresh()))

    def refresh(self):
        if self.has('delivery_tree'):
            self.call('receiving.status', {}, self.show_status)
            self.call('receiving.deliveries', {'limit': 50}, self.show_deliveries)
        if self.has('brain_state'):self.refresh_brain()
        if self.has('matrix_state'):self.refresh_matrix()

    def show_status(self, value):
        self.inbox = value.get('inbox')
        waiting = value.get('inbox_waiting') or [];self._inbox_waiting = waiting
        self.host._status_inbox = len(waiting)
        from .shell2 import sentence
        sentence((('Ingress  ' + short_path(self.inbox).replace('&', '&amp;').replace('<', '&lt;') + ('  ·  %d new' % len(waiting) if waiting else '  ·  nothing new')) if self.inbox
                  else 'This workspace shares a folder with the program; receive files by the words above or by dropping them.') + '  ·  {again}',
                 {'again': ('look again', self.refresh)}, self.inbox_label)
        self.inbox_label.setToolTip(self.inbox or '');self.tell_inspector()

    def show_deliveries(self, value):
        self.deliveries = value['deliveries'];selected = self.selected_delivery_id()
        self.delivery_tree.clear();self.card_source.blockSignals(True);current = self.card_source.currentData();self.card_source.clear()
        for d in self.deliveries:
            item = QTreeWidgetItem([d['label'], d['stage'], str(d.get('files', len(d['revived']))), str(len(d['accepted'])), str(len(d['held']))])
            item.setData(0, Qt.UserRole, d['id']);self.delivery_tree.addTopLevelItem(item)
            if d['id'] == selected:self.delivery_tree.setCurrentItem(item)
            if d['accepted']:self.card_source.addItem(d['label'] + ' · ' + str(len(d['accepted'])) + ' files', d['id'])
        index = self.card_source.findData(current)
        if index >= 0:self.card_source.setCurrentIndex(index)
        self.card_source.blockSignals(False)

    def selected_delivery_id(self):
        item = self.delivery_tree.currentItem()
        return item.data(0, Qt.UserRole) if item else None

    def show_delivery(self):
        ident = self.selected_delivery_id();d = next((x for x in self.deliveries if x['id'] == ident), None)
        if hasattr(self, 'accept_button'):
            self.accept_button.setVisible(bool(d) and d['stage'] == 'REVIEWED' and any(h['reasons'] == ['OWNER_REVIEW_REQUIRED'] for h in d['held']))
            self.again_button.setVisible(bool(d) and d['stage'] not in MOVING)
        if not d:return
        lines = [d['label'] + ' · ' + d['stage'], 'From: ' + d['source']]
        if d.get('error'):lines.append('Problem: ' + d['error'])
        if d.get('filed'):lines.append('Filed from Arrived to: ' + d['filed'])
        if d.get('accept_problem'):lines.append('Some files could not be accepted: ' + d['accept_problem'])
        changed = [r for r in d['revived'] if r['action'] != 'COPIED']
        if changed:lines += ['', 'Revived:'] + ['  ' + r['name'] + ' · ' + r['action'] + (' · ' + str(r.get('members')) + ' files' if 'members' in r else '') +
                                                (' · from ' + r['from'] if 'from' in r else '') + (' · ' + r['reason'] if 'reason' in r else '') for r in changed]
        if d['held']:lines += ['', 'Waiting for you:'] + ['  ' + h['name'] + ' · ' + ', '.join(h['reasons']) for h in d['held']]
        if d['rejected']:lines += ['', 'Not accepted:'] + ['  ' + h['name'] + ' · ' + ', '.join(h['reasons']) for h in d['rejected']]
        if d.get('revived_originals'):lines += ['', 'Kept as delivered (their revived copies carry on):'] + ['  ' + h['name'] for h in d['revived_originals']]
        self.delivery_detail.setPlainText('\n'.join(lines));self.tell_inspector()

    def receive_again(self):
        d = next((x for x in self.deliveries if x['id'] == self.selected_delivery_id()), None)
        if not d:self.status.setText('Select a delivery first.');return
        source = d.get('filed') or d['source']  # deliveries from Arrived were filed under Received/
        if not Path(source).exists():self.status.setText('The original files are no longer at ' + source);return
        self.receive(source, d['label'])

    def accept_selected(self):
        ident = self.selected_delivery_id()
        if not ident:self.status.setText('Select a delivery first.');return
        reason, ok = QInputDialog.getText(self, 'Accept reviewed files', 'Reason for accepting', text=ACCEPT_REASON)
        if ok and reason.strip():self.call('receiving.advance', {'id': ident, 'accept': True, 'reason': reason.strip()}, lambda value:self.refresh())

    def tick(self):
        if self.host._closing or self.busy_delivering():return
        if not self.has('auto_accept'):
            if self.brain_job or self.plan_job:self.poll_jobs()
            return
        for d in self.deliveries:
            accept = self.auto_accept.isChecked() and d['stage'] == 'REVIEWED' and any(h['reasons'] == ['OWNER_REVIEW_REQUIRED'] for h in d['held'])
            if d['stage'] in MOVING or accept:
                args = {'id': d['id']}
                if accept:args.update(accept=True, reason=ACCEPT_REASON)
                self._advancing = True
                self.call('receiving.advance', args, self.advanced, failed=lambda error:setattr(self, '_advancing', False));return
        if self.brain_job or self.plan_job:self.poll_jobs()

    def busy_delivering(self):return getattr(self, '_advancing', False)

    def advanced(self, value):
        self._advancing = False
        for i, d in enumerate(self.deliveries):
            if d['id'] == value['id']:self.deliveries[i] = value
        self.show_deliveries({'deliveries': self.deliveries});self.show_delivery()
        if value['stage'] == 'CATALOGED':self.status.setText(value['label'] + ' is cataloged · ' + str(len(value['accepted'])) + ' files have reading cards')

    # Catalog and staC ---------------------------------------------------

    def load_cards(self):
        ident = self.card_source.currentData()
        if not ident:self.status.setText('No delivery has accepted files yet.');return
        self.call('receiving.cards', {'id': ident}, self.show_cards)

    def view_card(self):
        item = self.card_list.currentItem()
        card = next((c for c in self.cards if item and c['address'] == item.data(0, Qt.UserRole)), None)
        delivery = next((d for d in self.deliveries if d['id'] == self.card_source.currentData()), None)
        if not card or not delivery:self.status.setText('Select a card first.');return
        # The received copy lives in this workspace's state; the stored path is only a fallback (it changes after a move or restore).
        here = Path(self.host.root) / '.ledger' / 'receiving' / delivery['id'] / 'delivery' / card['catalog_path']
        path = here if here.is_file() else Path(delivery['staging']) / card['catalog_path']
        if not path.is_file():self.status.setText('The received copy is no longer available: ' + str(path));return
        if hasattr(self.host, 'open_in_viewer'):self.host.open_in_viewer(path)

    def show_cards(self, value):
        self.cards = value['cards'];self.card_list.clear()
        for card in self.cards:
            item = QTreeWidgetItem([card['name'], str(card['characters'])]);item.setData(0, Qt.UserRole, card['address']);self.card_list.addTopLevelItem(item)
        self.status.setText(str(len(self.cards)) + ' reading cards')

    def show_card(self):
        item = self.card_list.currentItem()
        card = next((c for c in self.cards if item and c['address'] == item.data(0, Qt.UserRole)), None)
        if not card:return
        self.card_view.setPlainText('\n'.join(['@' + card['address'], card['name'] + ' · ' + str(card['profile']), 'sha256 ' + card['sha256'], '', card['summary'], '', 'Line:'] +
                                              ['  ' + p['program'] + '    # ' + p['purpose'] + ('' if p['valid'] else ' · ' + p.get('error', 'invalid')) for p in card['programs']]))
        self.card_programs.blockSignals(True);self.card_programs.clear()
        for p in card['programs']:self.card_programs.addItem(p['purpose'], p)
        self.card_programs.blockSignals(False);self.pick_program();self.tell_inspector()

    def pick_program(self):
        p = self.card_programs.currentData()
        if p:self.program.setText(p['program'])

    def run_program(self):
        op, args = route_program(self.program.text())
        if not (args.get('program') or args.get('text')):return
        def shown(value):self.run_view.setPlainText(readable_result(value) + '\n\n──── full result ────\n' + pretty(value));self.refresh_matrix()
        self.call(op, args, shown, failed=lambda error:(self.run_view.setPlainText('Failed: ' + error.get('message', '')), self.refresh_matrix()))

    def mark_last(self, mark):
        def marked(value):
            rows = value['rows']
            if not rows:self.status.setText('Run a line first.');return
            self.call('matrix.mark', {'id': rows[0]['id'], 'mark': mark}, lambda v:(self.status.setText('Marked ' + mark.lower() + ': ' + v['program'][:80]), self.refresh_matrix()))
        self.call('matrix.list', {'limit': 1}, marked)

    # Brain --------------------------------------------------------------

    def refresh_brain(self):
        if not self.has('brain_state'):return
        def shown(value):
            model = value.get('selection', {}).get('model_id')
            name = next((next((f['name'] for f in m.get('files', []) if f.get('role') == 'weights'), m['id'][:12]) for m in self._models if m['id'] == model),
                        model[:12] if model else None) if model else None
            words = {'READY': 'ready', 'MODEL_STOPPED': 'stopped', 'NO_MODEL_SELECTED': 'no model yet'}.get(value['state'], value['state'].replace('_', ' ').lower())
            self.brain_state.setText('Brain: ' + words + (' · ' + name if name else '') + ' · ' + str(value['registered_models']) + ' registered · engine '
                                     + str(value['runtime'].get('build') or 'unavailable') + ' · on this computer')
            self.host._status_brain = words + (' · ' + name if name else '');self.tell_inspector()
        def models(value):self._models = value['models'];self.call('brain.status', {}, shown)
        self._models = getattr(self, '_models', [])
        self.call('brain.models', {}, models)

    def pick_model(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose model', str(Path.home()), 'GGUF models (*.gguf)')
        if path:self.replace_brain(path)

    def replace_brain(self, path):
        if self.brain_job:self.status.setText('A brain change is already running.');return
        self.status.setText('Inspecting ' + Path(path).name + '. Nothing is loaded until it passes.')
        self.call('brain.model.add', {'path': str(path), 'managed_copy': False}, lambda job:self.follow_brain(job, 'add', path))

    def follow_brain(self, job, step, path=None):
        self.brain_job = {'id': job['id'], 'step': step, 'path': path}

    def poll_jobs(self):
        for name in ('brain_job', 'plan_job'):
            watched = getattr(self, name)
            if watched:self.call('jobs.get', {'id': watched['id']}, lambda job, n=name:self.job_changed(n, job))

    def job_changed(self, name, job):
        watched = getattr(self, name)
        if not watched or watched['id'] != job['id'] or job['state'] not in ('Completed', 'Failed', 'Cancelled', 'Interrupted'):return
        setattr(self, name, None)
        if job['state'] != 'Completed':
            self.status.setText(('Brain change' if name == 'brain_job' else 'Graphite') + ' stopped: ' + job['state'] + (' · ' + job['error'] if job.get('error') else ''))
            self.refresh_brain();return
        if name == 'plan_job':self.call('brain.result', {'id': job['id']}, self.show_plan);return
        if watched['step'] == 'add':
            def chosen(value):
                found = [m for m in value['models'] if any(Path(f.get('name', '')).name == Path(watched['path']).name for f in m.get('files', []))] or value['models'][-1:]
                if not found:self.status.setText('The model was inspected but is not registered.');return
                self.status.setText('Switching the brain to ' + Path(watched['path']).name + '…')
                self.call('brain.model.use', {'id': found[-1]['id'], 'request_key': uuid.uuid4().hex}, lambda j:self.follow_brain(j, 'use'))
            self.call('brain.models', {}, chosen)
        else:
            self.status.setText('The new brain is running.');self.refresh_brain()

    def restore_brain(self):self.call('brain.restore', {}, lambda job:self.follow_brain(job, 'use'))

    def stop_brain(self):self.call('brain.stop', {}, lambda value:self.refresh_brain())

    def open_brain(self):self.host.ledger_bridge.show_brain()

    def ask_plan(self):
        text = self.request.text().strip()
        if not text or self.plan_job:return
        self.proposal = None;self.run_plan_button.setEnabled(False);self.plan_view.setPlainText('Graphite is reading the instruction matrix and planning…')
        self.call('brain.ask', {'message': text, 'mode': 'plan', 'request_key': uuid.uuid4().hex}, lambda job:setattr(self, 'plan_job', {'id': job['id']}))

    def show_plan(self, value):
        result = value.get('result') or {};self.proposal = result.get('proposal')
        actions = (self.proposal or {}).get('actions') or []
        self.plan_view.setPlainText((result.get('text') or '') + '\n\n' + ('Proposed:\n' + '\n'.join('  ' + a['operation'] + ' ' + json.dumps(a['arguments'], ensure_ascii=False) for a in actions)
                                                                       if actions else 'No program was proposed. This is recorded so Graphite can learn from it.'))
        self.run_plan_button.setEnabled(bool(actions));self.refresh_matrix();self.tell_inspector()

    def run_proposal(self):
        actions = (self.proposal or {}).get('actions') or []
        if not actions:return
        answer = QMessageBox.question(self, 'Run proposal', 'Run these ' + str(len(actions)) + ' read-only calls with your permissions?\n\n' +
                                      '\n'.join(a['operation'] for a in actions))
        if answer != QMessageBox.Yes:return
        self.run_plan_button.setEnabled(False);results = []
        def next_action(index=0):
            if index >= len(actions):self.plan_view.appendPlainText('\n' + '\n\n'.join(results));self.refresh_matrix();return
            a = actions[index]
            def done(value):results.append(a['operation'] + ' → ' + pretty(value)[:1500]);next_action(index + 1)
            def failed(error):results.append(a['operation'] + ' → failed: ' + error.get('message', ''));next_action(index + 1)
            self.call(a['operation'], a['arguments'], done, failed=failed)
        next_action()

    # Matrix -------------------------------------------------------------

    def refresh_matrix(self):
        if not self.has('matrix_state'):return
        def status(value):
            c = value['counts']
            self.matrix_state.setText('Worked %d · empty %d · blocked %d · failed %d · waiting to run %d · marked by you %d. '
                                      'Graphite learns from these as examples; its weights never change.' %
                                      (c['SUCCESS'], c['EMPTY'], c['BLOCKED'], c['FAILED'], c['PROPOSED'], value['owner_marked']))
        def patterns(value):
            self.pattern_tree.clear()
            for p in value['patterns']:
                item = QTreeWidgetItem([p['shape'], str(p['tries']), str(p['success']), str(p['empty']), str(p['failed'] + p['blocked']),
                                        '%d%%' % round(100 * p['success_rate']), p['reasons'][0]['reason'] if p['reasons'] else ''])
                item.setData(0, Qt.UserRole, p['shape']);self.pattern_tree.addTopLevelItem(item)
        def rows(value):
            self.row_tree.clear()
            for r in value['rows']:
                item = QTreeWidgetItem([r['outcome'], '' if r['mark'] == 'NONE' else r['mark'], r['intent'] or '', r['program'], r['reason'] or ''])
                item.setData(0, Qt.UserRole, r['id']);self.row_tree.addTopLevelItem(item)
        self.call('matrix.status', {}, status);self.call('matrix.patterns', {'limit': 50}, patterns);self.call('matrix.list', {'limit': 100}, rows)

    def mark_selected(self, mark):
        item = self.row_tree.currentItem()
        if not item:self.status.setText('Select an instruction first.');return
        self.call('matrix.mark', {'id': item.data(0, Qt.UserRole), 'mark': mark}, lambda value:self.refresh_matrix())

    def promote(self):
        item = self.pattern_tree.currentItem()
        if not item:self.status.setText('Select a pattern first.');return
        title, ok = QInputDialog.getText(self, 'Promote to lesson', 'Lesson title', text='Line: ' + item.text(0)[:60])
        if ok and title.strip():
            self.call('matrix.promote', {'shape': item.data(0, Qt.UserRole), 'title': title.strip()[:120]},
                      lambda value:self.status.setText('Lesson proposed. Review it in Memory before Graphite relies on it.'))

    def export_matrix(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Export training set', str(Path.home() / 'slate-instruction-matrix.jsonl'), 'JSON lines (*.jsonl)')
        if path:self.call('matrix.export', {'destination': path}, lambda value:self.status.setText('Exported ' + str(value['rows']) + ' rows to ' + value['path']))

    def forget_matrix(self):
        if QMessageBox.question(self, 'Forget the instruction matrix', 'Delete every recorded instruction and outcome? Lessons you reviewed stay.') == QMessageBox.Yes:
            self.call('matrix.forget', {'all': True}, lambda value:(self.status.setText('Forgot ' + str(value['rows']) + ' rows.'), self.refresh_matrix()))


class SlateRoomTab(OfficeBuildingTab):
    """The Slate room: the replaceable local brain, planning in staC, and the instruction matrix it learns from."""
    HEADING = 'Graphite'
    LEAD = 'Drop a GGUF model here to change the brain. Graphite proposes a line; you run it; the matrix remembers what worked.'
    PAGES = (('brain_room', 'Brain · ask'), ('matrix_room', 'Instruction matrix'))
