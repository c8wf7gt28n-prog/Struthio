"""Tools › Pills: this Ledger's card, paired computers, a pill opened from Files, and every pill in and out."""
from __future__ import annotations
import json
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QFrame, QGridLayout, QInputDialog, QLabel, QMessageBox, QScrollArea, QVBoxLayout, QWidget
from .shell2 import QUIET, call, call_write, escape_text, role, sentence


def quiet(text):
    label = QLabel(text);label.setWordWrap(True);label.setStyleSheet('color:%s' % QUIET);return label


class PillsTab(QWidget):
    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('LibraryTab');self.setProperty('ledgerRoom', True);self.opened = None
        outer = QVBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame);outer.addWidget(self.scroll);self.reload()

    def title(self):return 'Pills'

    def reload(self):
        page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(40, 26, 40, 20);box.setSpacing(10)
        box.addWidget(role(QLabel('Pills'), 'title'))
        box.addWidget(quiet('Work travels between computers as pills: signed, self-describing packages. A pill asks; this '
                            'Graphite decides. Nothing in a pill is run, and its original stays on the computer that sent it.'))
        if self.opened:self.show_pill(box)
        info = call(self.host, 'pills.identity') or {'card': {}, 'peers': []};card = info['card']
        grid = QGridLayout();grid.setHorizontalSpacing(36);grid.setVerticalSpacing(8)
        left = QVBoxLayout();left.addWidget(role(QLabel('THIS GRAPHITE'), 'section'))
        left.addWidget(QLabel('%s · key %s' % (escape_text(card.get('name', 'Graphite')), card.get('key', '?'))))
        left.addWidget(sentence('{save} to give to your workstation', {'save': ('Save this Graphite\'s card', self.save_card)}))
        right = QVBoxLayout();right.addWidget(role(QLabel('PAIRED COMPUTERS'), 'section'))
        for peer in info['peers']:
            right.addWidget(sentence('%s · code %s · {forget}' % (escape_text(peer['name']), peer['code']), {'forget': ('forget', lambda k=peer['key'], n=peer['name']:self.unpair(k, n))}))
        if not info['peers']:right.addWidget(quiet('None yet.'))
        right.addWidget(sentence('{pair}', {'pair': ('Pair with a computer\'s card…', self.pair)}))
        grid.addLayout(left, 0, 0);grid.addLayout(right, 0, 1);grid.setColumnStretch(0, 1);grid.setColumnStretch(1, 1);box.addLayout(grid)
        box.addWidget(role(QLabel('PILLS IN AND OUT'), 'section'))
        rows = (call(self.host, 'pills.list') or {}).get('pills', [])
        asked = {r['id']: r['sender_name'] for r in rows if r['kind'] == 'request'}
        for r in rows[:12]:
            way = 'from %s' % r['sender_name'] if r['kind'] == 'request' else 'the result, for %s' % asked.get(r['answers'], 'the computer that asked')
            box.addWidget(QLabel('%s · %s · %s' % (escape_text(r['title']), way, r['words'])))
        if not rows:box.addWidget(quiet('None yet. Open a .pill file in Files, or with {open}.'.replace('{open}', 'the word below')))
        box.addWidget(sentence('{open}  ·  {fetch}  ·  {send}', {'open': ('Open a pill…', self.choose), 'fetch': ('Fetch over the link…', self.fetch),
                                                              'send': ('Send over the link…', self.send)}))
        box.addWidget(quiet('The link is optional: this Graphite connects out to your workstation\'s pill service and never listens. '
                            'Pills fetched this way wait in Files › Received › Pills until you open and accept them.'))
        box.addStretch(1);self.scroll.setWidget(page)

    def show_pill(self, box):
        path = self.opened
        from .engine import engineering
        from .engineering_kernel import operator
        r = engineering(self.host.root).dispatch('pills.open', {'path': str(path)}, operator())  # a refusal is shown, in words
        box.addWidget(role(QLabel('THE PILL OPENED'), 'section'))
        if not r.get('ok'):
            box.addWidget(QLabel('Refused: ' + escape_text(r['error']['message'])));box.addWidget(quiet('Nothing was kept. ' + escape_text(str(path))));return
        v = r['result'];p = v['pill']
        box.addWidget(QLabel('<b>%s</b> · a %s from %s' % (escape_text(p['task']['title']), p['kind'], escape_text(p['from']))))
        if v.get('purpose'):box.addWidget(quiet(escape_text(v['purpose'])))
        box.addWidget(quiet('%d file(s) of %s · asks to %s · checked: %s.' % (p['files'], escape_text(p['source']), ', '.join(w.replace('_', ' ') for w in p['requested']) or 'nothing',
                                                                              '; '.join(v['checks']))))
        if p['kind'] != 'request':box.addWidget(quiet('A result is applied on the computer that asked, not here.'));return
        if not v.get('new'):box.addWidget(quiet('Already accepted here.'));return
        if not v.get('permitted'):box.addWidget(QLabel(escape_text(v.get('why_not', 'Not permitted.'))));return
        box.addWidget(sentence('{mine} · {slate}', {'mine': ('Accept as my working copy', lambda:self.accept(False)),
                                                    'slate': ('Accept and assign it to Graphite', lambda:self.accept(True))}))

    def accept(self, for_slate):
        r = call_write(self.host, 'pills.accept', {'path': str(self.opened), 'for_slate': for_slate})
        if not r.get('ok'):QMessageBox.warning(self, 'Pill', r['error']['message']);return
        self.opened = None;self.reload()
        from .shell2 import open_destination
        tab = open_destination(self.host, 'files:Working copies')
        _ = tab

    def address(self):
        last = self.host.session.state.get('pill_link', '') if hasattr(self.host, 'session') else ''
        text, ok = QInputDialog.getText(self, 'The pill link', 'Your workstation\'s pill service (host:port), e.g. 10.77.0.1:7717:', text=last)
        if not ok or not text.strip():return None
        if hasattr(self.host, 'session'):self.host.session.state['pill_link'] = text.strip()
        return text.strip()

    def fetch(self):
        address = self.address()
        if not address:return
        r = call_write(self.host, 'pills.fetch', {'address': address})
        if not r.get('ok'):QMessageBox.warning(self, 'Fetch', r['error']['message']);return
        v = r['result'];QMessageBox.information(self, 'Fetch', '%d new pill(s) from %s.\n%s' % (len(v['saved']), v['from'], v['note']))
        if v['saved']:
            from .engine import engineering
            from . import files_service
            self.opened = files_service.root(engineering(self.host.root)) / v['saved'][0]
        self.reload()

    def send(self):
        from .engine import engineering
        from . import files_service
        start = files_service.root(engineering(self.host.root)) / files_service.EXPORTS / 'Pills'
        name, _ = QFileDialog.getOpenFileName(self, 'Send a result pill', str(start), 'Pills (*.pill)')
        if not name:return
        address = self.address()
        if not address:return
        try:rel = files_service.rel_of(engineering(self.host.root), Path(name))
        except ValueError:QMessageBox.warning(self, 'Send', 'Send pills from Files (Egress › Pills).');return
        r = call_write(self.host, 'pills.send', {'path': rel, 'address': address})
        if not r.get('ok'):QMessageBox.warning(self, 'Send', r['error']['message']);return
        QMessageBox.information(self, 'Send', 'Sent to %s. It decides, there, whether to apply it.' % r['result']['to'])

    def choose(self):
        name, _ = QFileDialog.getOpenFileName(self, 'Open a pill', str(Path.home()), 'Pills (*.pill)')
        if name:self.opened = Path(name);self.reload()

    def save_card(self):
        card = (call(self.host, 'pills.identity') or {}).get('card')
        name, _ = QFileDialog.getSaveFileName(self, 'Save this Graphite\'s card', str(Path.home() / 'ledger-card.json'), 'Cards (*.json)')
        if name and card:Path(name).write_text(json.dumps(card, indent=1))

    def pair(self):
        name, _ = QFileDialog.getOpenFileName(self, 'A computer\'s pill card', str(Path.home()), 'Cards (*.json)')
        if not name:return
        try:card = json.loads(Path(name).read_text())
        except (OSError, ValueError):QMessageBox.warning(self, 'Pair', 'That is not a pill card.');return
        r = call_write(self.host, 'pills.pair', {'name': str(card.get('name', 'Computer'))[:80], 'public': str(card.get('public', ''))})
        if not r.get('ok'):QMessageBox.warning(self, 'Pair', r['error']['message']);return
        got = r['result']
        if QMessageBox.question(self, 'Pair', 'Pairing code: %s\n\nDoes %s show the same code? If not, choose No and nothing is kept.' % (got['code'], got['name'])) != QMessageBox.Yes:
            call_write(self.host, 'pills.unpair', {'key': got['key']})
        self.reload()

    def unpair(self, key, name):
        if QMessageBox.question(self, 'Forget', 'Forget %s? Its pills will be refused until you pair again.' % name) == QMessageBox.Yes:
            call_write(self.host, 'pills.unpair', {'key': key});self.reload()

    def inspector(self):
        info = call(self.host, 'pills.identity') or {'card': {}, 'peers': []}
        return 'Pills', [('This Graphite', info['card'].get('key', '?')[:12])] + [(p['name'], 'paired') for p in info['peers']]


def show(host, path=None):
    host._close_start()
    for i in range(host.tabs.count()):
        if isinstance(host.tabs.widget(i), PillsTab):
            tab = host.tabs.widget(i);host.tabs.setCurrentIndex(i);tab.opened = Path(path) if path else tab.opened;tab.reload();return tab
    tab = PillsTab(host);tab.opened = Path(path) if path else None;tab.reload();host.tabs.addTab(tab, tab.title());host.tabs.setCurrentWidget(tab);return tab


def return_copy(host, copy, parent=None):
    """Return a pill's working copy: your findings in words, then the result pill in Egress › Pills."""
    text, ok = QInputDialog.getMultiLineText(parent, 'Return as a pill', 'Findings for %s (what was done and why):' % copy.get('name', 'the workstation'), '')
    if not ok:return None
    r = call_write(host, 'pills.return', {'copy': copy['id'], 'findings': text})
    if not r.get('ok'):QMessageBox.warning(parent, 'Return as a pill', r['error']['message']);return None
    v = r['result']
    QMessageBox.information(parent, 'Return as a pill', 'Result pill for %s, with %d change(s):\n%s\n\nCarry it back; the workstation decides whether to apply it.' % (v['to'], v['changes'], v['path']))
    return v
