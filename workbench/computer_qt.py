"""Tools › This Computer: what this machine offers for confining programs, in words. A look only."""
from __future__ import annotations
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget, QFrame
from .shell2 import QUIET, call, role, sentence


class ComputerTab(QWidget):
    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('LibraryTab');self.setProperty('ledgerRoom', True)
        outer = QVBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame);outer.addWidget(self.scroll);self.reload()

    def title(self):return 'This computer'

    def reload(self):
        value = call(self.host, 'system.supports') or {'rows': [], 'note': 'Could not look.'}
        page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(40, 26, 40, 20);box.setSpacing(12)
        box.addWidget(role(QLabel('This computer'), 'title'))
        lead = QLabel(value.get('note', ''));lead.setWordWrap(True);lead.setStyleSheet('color:%s' % QUIET);box.addWidget(lead)
        # Two columns of short entries, not one long list: the whole look fits on one screen without scrolling.
        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout();grid.setHorizontalSpacing(32);grid.setVerticalSpacing(16)
        for i, row in enumerate(value.get('rows', [])):
            cell = QWidget();col = QVBoxLayout(cell);col.setContentsMargins(0, 0, 0, 0);col.setSpacing(2)
            head = QLabel('%s  ·  %s' % (row['what'], row['state']));head.setStyleSheet('font-weight:600');col.addWidget(head)
            words = QLabel('%s. %s' % (str(row['found']).rstrip('.'), row['why']));words.setWordWrap(True);words.setStyleSheet('color:%s' % QUIET);col.addWidget(words)
            grid.addWidget(cell, i // 2, i % 2)
        grid.setColumnStretch(0, 1);grid.setColumnStretch(1, 1);box.addLayout(grid)
        box.addWidget(sentence('{again}', {'again': ('look again', self.reload)}));box.addStretch(1);self.scroll.setWidget(page)

    def inspector(self):
        rows = (call(self.host, 'system.supports') or {}).get('rows', [])
        return 'This computer', [(r['what'], r['state']) for r in rows]


def show(host):
    host._close_start()
    for i in range(host.tabs.count()):
        if isinstance(host.tabs.widget(i), ComputerTab):host.tabs.setCurrentIndex(i);host.tabs.widget(i).reload();return host.tabs.widget(i)
    tab = ComputerTab(host);host.tabs.addTab(tab, tab.title());host.tabs.setCurrentWidget(tab);return tab
