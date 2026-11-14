"""A retained working surface for the existing read-only staC chain builder.

Preview, run, and save use the Kernel's existing language and Files operations.
Source fingerprints stop a displayed preview silently becoming a different sheet.
"""
import hashlib
import json
import os
import time
from uuid import uuid4
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QMenu,
                              QPushButton, QScrollArea, QSizePolicy, QTableWidget, QTableWidgetItem,
                              QToolButton, QVBoxLayout, QWidget)
from . import boss_theme as colours


def call(host, operation, args):
    from .context_menu import dispatch, message
    response = dispatch(host, operation, args)
    if not response.get('ok'):raise ValueError(message(response))
    return response['result']


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str,
                                    separators=(',', ':')).encode()).hexdigest()


def source_calls(program):
    from .stacy_language import source
    from sdk.cli.arc1cli.typed_pipeline import parse
    plan = parse(source(program)[0]);out = [plan['call']]
    for transform in plan['transforms']:
        if transform['kind'] in ('join', 'missing'):
            out.extend(source_calls(transform['source']))
    # The language already bounds joins; avoid duplicate source reads.
    return list({json.dumps(c, sort_keys=True):c for c in out}.values())


def sources_now(host, program):
    sources = []
    for c in source_calls(program):
        value = call(host, c['operation'], c['arguments'])
        obj = value.get('object', value) if isinstance(value,dict) else value
        bounded = False
        if isinstance(obj,dict):
            data = obj.get('data')
            data = data if isinstance(data,dict) else {}
            collections = [data.get('rows'),data.get('lines'),data.get('texts')]
            sheets = data.get('sheets')
            if isinstance(sheets,dict):collections += list(sheets.values())
            bounded = any(isinstance(rows,list) and len(rows) >= 2000 for rows in collections)
            view = obj.get('view');view = view if isinstance(view,dict) else {}
            notice = str(view.get('notice') or '').lower()
            bounded = bounded or 'first ' in notice or bool(obj.get('text_truncated'))
        sources.append(dict(operation=c['operation'],arguments=c['arguments'],
                            digest=fingerprint(value),source_view_limit=bounded))
    return sources


class ChainTrace(QWidget):
    track_y = 6

    def __init__(self, tray, strip):
        super().__init__(tray)
        self.tray, self.strip = tray, strip
        self.setFixedHeight(14)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        strip.horizontalScrollBar().valueChanged.connect(self.update)

    def paintEvent(self, event):
        left = self.mapFromGlobal(self.strip.viewport().mapToGlobal(QPoint())).x()
        right = left + self.strip.viewport().width()
        anchors = []
        for item in (self.tray.chips.itemAt(i) for i in range(self.tray.chips.count())):
            chip = item.widget()
            if isinstance(chip, QPushButton):
                x = self.mapFromGlobal(chip.mapToGlobal(chip.rect().center())).x()
                if left <= x < right:anchors.append(x)
        run = self.tray.controls['sheet']
        anchors.append(self.mapFromGlobal(run.mapToGlobal(run.rect().center())).x())
        painter = QPainter(self)
        colour = QColor(colours.CUE_EDGE)
        painter.setPen(QPen(colour, 2, Qt.DashLine))
        painter.drawLine(min(anchors), self.track_y, anchors[-1], self.track_y)
        for x in anchors:
            painter.drawLine(x, self.track_y, x, self.height() - 1)
            painter.fillRect(x - 2, self.track_y - 2, 4, 4, colour)
        painter.end()


class ChainTray(QFrame):
    changed = Signal()

    def __init__(self, host, result_layout=None, format_rows=None):
        super().__init__();self.host = host;self.program = '';self.rows = None;self.sources = None;self.seed = None
        self.in_worksheet = result_layout is not None
        self.saved_receipt = None
        self.method = None
        self.format_rows = format_rows
        self.setObjectName('BossChainTray');self.setProperty('paperFunctionalInk', True)
        self.setMinimumWidth(0)
        box = QVBoxLayout(self);box.setContentsMargins(12, 8, 12, 8);box.setSpacing(6)
        head = QHBoxLayout();self.heading = QLabel('Constructed chain');head.addWidget(self.heading, 1)
        if self.in_worksheet:self.heading.setObjectName('WorksheetChainTitle')
        self.controls = {}
        for key, words, fn in (('preview','Preview',self.preview), ('run','Run',self.run_chain),
                               ('sheet','[>] Run chain' if self.in_worksheet else 'Save sheet',
                                lambda:self.save_sheet(open_folder=not self.in_worksheet)), ('keep','Keep method',self.keep),
                               ('edit','Edit in strip',self.edit_in_strip), ('close','×',self.hide)):
            button = QPushButton(words);button.setAccessibleName('Chain: ' + words)
            button.clicked.connect(lambda checked=False, f=fn:f());self.controls[key] = button
            if key not in ('keep','edit') and not (self.in_worksheet and key in ('run','sheet')):head.addWidget(button)
            else:button.setParent(self);button.hide()
        more = QToolButton();more.setText('⋯');more.setAccessibleName('More chain choices')
        more.setPopupMode(QToolButton.InstantPopup);choices = QMenu(more);more.setMenu(choices)
        choices.addAction('Keep as a method…',self.keep);choices.addAction('Edit in the writing strip',self.edit_in_strip)
        if self.in_worksheet:
            choices.addAction('Show result in Terminal console', self.run_chain)
            self.controls['sheet'].setAccessibleName('Run chain and save a new sheet')
            self.controls['sheet'].setObjectName('RunWorksheetChain')
        head.insertWidget(head.count()-1,more);self.controls['more'] = more
        box.addLayout(head)
        strip = QScrollArea();strip.setWidgetResizable(True);strip.setFrameShape(QFrame.NoFrame)
        strip.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff);strip.setFixedHeight(46)
        strip.setMinimumWidth(0);chip_host = QWidget();self.chips = QHBoxLayout(chip_host)
        self.chips.setContentsMargins(0,0,0,0);self.chips.setSpacing(4);strip.setWidget(chip_host)
        if self.in_worksheet:
            self.track = ChainTrace(self, strip)
            box.addWidget(self.track)
            flow = QHBoxLayout();flow.addWidget(strip, 1);flow.addWidget(self.controls['sheet'])
            box.addLayout(flow)
        else:box.addWidget(strip)
        self.words = QLabel();self.words.setTextFormat(Qt.PlainText);self.words.setWordWrap(True)
        self.words.setMinimumWidth(0);self.words.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.words.setAccessibleName('Chain source or command details');box.addWidget(self.words)
        self.words.setVisible(not self.in_worksheet)
        self.table = QTableWidget();self.table.setObjectName('ChainPreview')
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.setMinimumWidth(0)
        self.table.setAccessibleName('Actual chain preview rows');self.table.setMaximumHeight(170)
        outcome = result_layout if self.in_worksheet else box
        outcome.addWidget(self.table)
        self.status = QLabel();self.status.setTextFormat(Qt.PlainText);self.status.setWordWrap(True);self.status.setMinimumWidth(0)
        if self.in_worksheet:self.status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.status.setAccessibleName('Chain outcome');outcome.addWidget(self.status)
        self.table.hide()
        self.setStyleSheet('QFrame#BossChainTray {background:%s;border-top:1px solid %s;} '
                          'QLabel {color:%s;} QTableWidget {background:%s;color:%s;}'
                          % (colours.PANEL,colours.CUE_EDGE,colours.TEXT,colours.CARD,colours.TEXT))
        self.hide()

    def note(self, text, ready=False):
        self.status.setText(str(text))
        self.status.setStyleSheet('color:%s;' % (colours.READY if ready else colours.QUIET))
        if not self.in_worksheet:self.host.statusBar().showMessage(str(text), 8000)
        self.changed.emit()

    def clear_chips(self):
        while self.chips.count():
            item = self.chips.takeAt(0)
            if item.widget():item.widget().deleteLater()

    def stage(self, program, display_labels=None, *, method=None):
        self.program = str(program).strip();self.rows = None;self.sources = None;self.seed = None
        self.method = method
        self.saved_receipt = None
        self.status.setToolTip('')
        self.heading.setText('Constructed chain');self.words.setText(self.program);self.table.hide();self.clear_chips()
        self.words.setFont(self.host.shell2.top.path.font())
        # The parser supplies the transforms. Display-only labels must not reinterpret quoted pipe characters.
        try:
            from .stacy_language import source
            from sdk.cli.arc1cli.typed_pipeline import parse, split
            plan = parse(source(self.program)[0])
            self.words.setToolTip(json.dumps(plan, ensure_ascii=False, indent=2))
            parts = split(self.program)
            labels = ['Input'] + [part if len(part) < 38 else part[:35]+'…' for part in parts[1:]]
        except ValueError:
            labels = ['Inspect source'];parts = [self.program]
        steps = list(enumerate(labels)) if display_labels is None else display_labels
        for position, (index, text) in enumerate(steps):
            button = QPushButton(text);button.setToolTip('Continue building this read-only chain')
            prefix = ' | '.join(parts[:index+1])
            button.setToolTip(prefix)
            if self.in_worksheet:
                from .context_menu import inspect_in_line
                button.setObjectName('WorksheetChainStep')
                button.clicked.connect(lambda checked=False,p=prefix:inspect_in_line(self.host,p))
            else:button.clicked.connect(lambda checked=False,p=prefix:self.continue_building(p))
            self.chips.addWidget(button)
            if position != len(steps)-1:
                if self.in_worksheet:self.chips.addStretch(1)
                self.chips.addWidget(QLabel('→' if self.in_worksheet else '›'))
                if self.in_worksheet:self.chips.addStretch(1)
        if not self.in_worksheet:self.chips.addStretch(1)
        for key, control in self.controls.items():
            control.setVisible(key not in ('keep','edit') and not (self.in_worksheet and key == 'run'))
        self.note('Prepared · nothing has run. Preview reads the current sources.');self.show()
        return self

    def reset(self, reason):
        self.program = '';self.rows = None;self.sources = None;self.seed = None
        self.saved_receipt = None
        self.method = None
        self.status.setToolTip('')
        self.table.hide();self.clear_chips();self.hide()
        self.note(reason)

    def inspect_command(self, text):
        self.program = '';self.rows = None;self.sources = None;self.clear_chips()
        self.method = None
        self.status.setToolTip('')
        self.heading.setText('Command inspector');self.words.setText(text);self.table.hide()
        for key, control in self.controls.items():control.setVisible(key == 'close')
        self.note('Inspecting the existing command. Its original action and authority rules are retained.');self.show()
        return self

    def continue_building(self, program=None):
        if not self.program:return
        from .chain_menu import Chain
        menu = Chain(self.host, program or self.program, parent=self.host)
        self._builder = menu
        menu.popup(self.mapToGlobal(self.rect().topLeft()))

    def preview(self):
        if not self.program:return False
        try:
            plan = call(self.host, 'language.parse', {'text':self.program})
            before = sources_now(self.host, self.program)
            result = call(self.host, 'language.run', {'text':self.program, 'expected_seed':plan['seed_id']})
            after = sources_now(self.host, self.program)
            if after != before:raise ValueError('A source changed during the preview. Preview again before using these rows.')
            self.rows = result.get('rows') or [];self.sources = after;self.seed = plan['seed_id']
            if self.method:self.plan_id = result['plan']['plan_id']
            self.render_rows()
            limit = len(self.rows) >= 200 or any(s['source_view_limit'] for s in after)
            self.controls['sheet'].setEnabled(not limit)
            self.controls['sheet'].setToolTip('A pipeline or source-view limit was reached; use a full-data capability before exporting this result.' if limit else 'Create a new CSV and a source receipt in Files/Slate/Chains')
            if self.method and not limit:
                current = after[0]['arguments']
                previous = self.method['source']
                changed = current['expected_sha256'] != previous['sha256'] or current['path'] != previous['path']
                message = ' · new source revision' if changed else ''
                self.status.setToolTip(self.program)
                self.note('[+] %s · preview on %s%s' % (self.method['name'], current['expected_sha256'][:10], message), True)
            elif self.in_worksheet and not limit:
                self.note('[+] Preview ready · %d rows' % len(self.rows), True)
            else:
                self.note('%d rows returned · current sources recorded%s' % (len(self.rows),
                          ' · pipeline or source-view limit reached; saving a partial sheet is disabled' if limit else ''), not limit)
            return True
        except (ValueError, OSError, TypeError) as exc:
            self.rows = None;self.sources = None;self.table.hide();self.note('Preview unavailable: ' + str(exc));return False

    def render_rows(self):
        rows = self.format_rows(self.rows or []) if self.format_rows is not None else self.rows or []
        fields = list(dict.fromkeys(key for row in rows if isinstance(row,dict) for key in row))
        if not fields:fields = ['value'];rows = [dict(value=row) for row in rows]
        fields = fields[:20];shown = rows[:100]
        self.table.clear();self.table.setColumnCount(len(fields));self.table.setHorizontalHeaderLabels(fields)
        self.table.setRowCount(len(shown))
        for i, row in enumerate(shown):
            for j, key in enumerate(fields):
                value = row.get(key,'') if isinstance(row,dict) else row
                item = QTableWidgetItem(str(value));item.setToolTip(str(value))
                if self.in_worksheet and j > 0:item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i,j,item)
        if self.in_worksheet and len(fields) <= 3:
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.table.verticalHeader().hide()
        else:
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            self.table.resizeColumnsToContents()
        if self.in_worksheet:
            size = self.table.horizontalHeader().sizeHint().height() + self.table.verticalHeader().defaultSectionSize() * len(shown) + 4
            self.table.setFixedHeight(min(180, size))
        self.table.show()
        self.table.setToolTip('Display: first 100 returned rows and 20 columns. Save uses all returned rows, up to the pipeline limit.')

    def current_preview(self):
        if self.rows is None and not self.preview():return False
        try:
            current = call(self.host,'language.parse',{'text':self.program})
            if current['seed_id'] != self.seed or self.method and current['plan_id'] != self.plan_id:
                self.rows = None;self.note('Program sources changed · preview again.');return False
            if sources_now(self.host,self.program) != self.sources:
                self.rows = None;self.sources = None;self.table.hide()
                self.note('Source changed · preview again before running or saving.');return False
        except (OSError,ValueError) as exc:
            self.rows = None;self.sources = None;self.table.hide()
            self.note(str(exc));return False
        return True

    def run_chain(self):
        if not self.current_preview():return False
        # The inspected result is the result shown: no second inference or application action is hidden here.
        from .console_qt import table_html
        console = self.host.console;console.set_mode('stac');console.open()
        console.say(table_html(self.rows));console.last_program = self.program
        self.host.type_bar.box.setText(self.program)
        self.note('Read-only chain result opened in the console · sources retained.', True)
        return True

    def save_sheet(self, open_folder=True):
        if not self.current_preview():return None
        if len(self.rows) >= 200 or any(s['source_view_limit'] for s in self.sources):
            self.note('A pipeline or source-view limit was reached. Use a full-data capability before exporting.');return None
        from .files_service import as_csv
        from .chain_menu import method_runs
        folder = method_runs(self.method) if self.method else 'Slate/Chains'
        stem = folder + '/chain-' + uuid4().hex
        receipt = dict(schema='graphite.chain-result/1',program=self.program, sources=self.sources,
                       seed=self.seed, rows=len(self.rows), output=stem+'.csv', created=time.time(),
                       authority='READ_ONLY_KERNEL_PIPELINE', execution='LOCAL_NO_MODEL')
        csv = as_csv([r if isinstance(r,dict) else {'value':r} for r in self.rows])
        if self.method:
            receipt.update(method=self.method, plan_id=self.plan_id,
                           output_sha256=hashlib.sha256(csv.replace('\n', os.linesep).encode('utf-8')).hexdigest())
        try:
            call(self.host,'files.write',{'path':stem+'.csv','text':csv})
            call(self.host,'files.write',{'path':stem+'.json','text':json.dumps(receipt,ensure_ascii=False,indent=2)})
        except (OSError,ValueError) as exc:
            self.note('Not fully saved: '+str(exc));return None
        if self.in_worksheet:
            self.saved_receipt = receipt
            self.status.setToolTip(stem+'.json\n'+self.program)
            suffix = ' · source ' + self.sources[0]['arguments']['expected_sha256'][:10] if self.method else ''
            self.note('[+] Saved %d rows with their source receipt%s' % (len(self.rows), suffix),True)
        else:self.note('Saved %d rows · %s.csv · source receipt beside it' % (len(self.rows),stem),True)
        if open_folder:
            from .shell2 import open_destination
            open_destination(self.host,'files:'+folder)
        return receipt

    def keep(self):
        if not self.program:return
        from .chain_menu import keep
        keep(self.host,self.program)

    def edit_in_strip(self):
        if not self.program:return
        from .context_menu import inspect_in_line
        return inspect_in_line(self.host,self.program)


def tray(host):
    existing = getattr(host,'chain_tray',None)
    if existing is not None:return existing
    existing = ChainTray(host);host.chain_tray = existing
    central = host.centralWidget();layout = central.layout()
    layout.insertWidget(layout.indexOf(host.central_stack)+1,existing)
    return existing


def stage(host, program):
    return tray(host).stage(program)
