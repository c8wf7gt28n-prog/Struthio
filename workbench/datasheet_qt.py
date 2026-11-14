"""The page review and calculation entry points for the saved Office workflow."""
from html import escape
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QFormLayout, QFrame, QHeaderView,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
from . import boss_theme as ink
from . import page_light


def words(text):
    label = QLabel(text)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    return label


class SourceCrop(QLabel):
    """The rendered PDF region with a mark around the selected row's source words."""
    def __init__(self, pixmap, region, width):
        super().__init__()
        self.region = region
        self.highlight = QRectF()
        x, y, w, h = region
        cropped = pixmap.copy(round(x * pixmap.width()), round(y * pixmap.height()),
                              max(1, round(w * pixmap.width())), max(1, round(h * pixmap.height())))
        display = cropped.scaled(QSize(width, 720), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(display)
        self.setFixedSize(display.size())
        self.setAccessibleName('Original PDF table region with selected source row')

    def mark(self, words):
        x, y, w, h = self.region
        bounds = QRectF()
        for word in words:
            left, top, width, height = word['rect']
            rect = QRectF((left - x) * self.width() / w, (top - y) * self.height() / h,
                          width * self.width() / w, height * self.height() / h)
            bounds = bounds.united(rect)
        self.highlight = bounds.adjusted(-2, -2, 2, 2).intersected(QRectF(self.rect())) if words else QRectF()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.highlight.isEmpty():return
        painter = QPainter(self)
        glow = QColor(ink.AMBER_EDGE);glow.setAlpha(50)
        painter.fillRect(self.highlight, glow)
        painter.setPen(QPen(QColor(ink.AMBER_EDGE), 2))
        painter.drawRect(self.highlight)
        painter.end()


class EvidenceLink(QWidget):
    def __init__(self, parent, crop, table):
        super().__init__(parent)
        self.crop, self.table = crop, table
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        row = self.table.currentRow()
        mark = self.crop.highlight.intersected(QRectF(self.crop.visibleRegion().boundingRect()))
        if row < 0 or mark.isEmpty():return
        source = self.mapFromGlobal(self.crop.mapToGlobal(QPoint(round(mark.right()), round(mark.center().y()))))
        y = self.table.rowViewportPosition(row) + self.table.rowHeight(row) // 2
        viewport = self.table.viewport()
        if not 0 <= y < viewport.height():return
        target = self.mapFromGlobal(viewport.mapToGlobal(QPoint(0, y)))
        painter = QPainter(self)
        colour = QColor(ink.AMBER_EDGE)
        painter.setPen(QPen(colour, 2))
        elbow = target.x() - 20
        painter.drawLine(source.x(), source.y(), elbow, source.y())
        painter.drawLine(elbow, source.y(), elbow, target.y())
        painter.drawLine(elbow, target.y(), target.x(), target.y())
        painter.setBrush(colour)
        painter.drawEllipse(target, 3, 3)
        painter.end()


class TableReview(QDialog):
    fields = ('parameter', 'value', 'unit', 'conditions')

    def __init__(self, parent, preview, page_image):
        super().__init__(parent)
        self.preview = preview
        self.link = None
        self.setObjectName('PdfEvidenceReview')
        self.setWindowTitle('Review PDF table')
        width = min(1160, max(720, parent.window().width() - 74))
        self.resize(width, min(650, max(460, parent.window().height() - 118)))
        self.setStyleSheet('''
            QDialog#PdfEvidenceReview {background:%(GROUND)s;border:1px solid %(LINE_MID)s;}
            QFrame#EvidencePanel {background:%(PANEL)s;border:1px solid %(LINE)s;border-top:2px solid %(CUE_EDGE)s;}
            QLabel#EvidenceMasthead {color:%(TEXT)s;font-family:"%(MONO)s";font-size:21px;font-weight:600;}
            QLabel#EvidenceTitle {color:%(CUE_TEXT)s;font-family:"%(MONO)s";font-size:14px;font-weight:600;}
            QLabel#EvidenceMeta {color:%(QUIET)s;font-family:"%(MONO)s";font-size:12px;}
            QLabel#EvidenceSelected {color:%(ON_AMBER)s;background:%(AMBER_SOFT)s;border:1px solid %(AMBER_EDGE)s;
                padding:6px 8px;font-family:"%(MONO)s";font-size:12px;}
            QTableWidget#EvidenceRows {background:%(GROUND)s;border:1px solid %(LINE)s;
                selection-background-color:%(AMBER_SOFT)s;selection-color:%(ON_AMBER)s;
                gridline-color:%(LINE)s;font-family:"%(MONO)s";}
            QTableWidget#EvidenceRows QHeaderView::section {background:%(CARD)s;color:%(TEXT)s;border:0;
                border-bottom:1px solid %(LINE_MID)s;border-right:1px solid %(LINE)s;padding:5px 6px;
                font-family:"%(MONO)s";font-weight:600;}
            QLineEdit#EvidenceTitleField {background:%(PANEL)s;border:1px solid %(LINE)s;
                border-radius:0;font-family:"%(MONO)s";padding:5px 8px;}
            QDialogButtonBox QPushButton {background:%(RAISED)s;border:1px solid %(LINE)s;border-radius:0;
                font-family:"%(MONO)s";padding:6px 10px;}
            QPushButton#EvidenceCommit {background:%(CUE_EDGE)s;color:%(TERMINAL_GROUND)s;
                border:1px solid %(CUE_EDGE)s;border-radius:0;font-family:"%(MONO)s";}
        ''' % vars(ink))
        box = QVBoxLayout(self)
        box.setContentsMargins(15, 14, 15, 14)
        box.setSpacing(10)
        source = preview['source']
        heading = words('[ MATERIAL REVIEW ]')
        heading.setObjectName('EvidenceMasthead')
        box.addWidget(heading)
        guide = words('Select a row to trace its evidence. Review the value, unit and conditions before saving.')
        guide.setObjectName('EvidenceMeta')
        box.addWidget(guide)
        self.title = QLineEdit(Path(source['name']).stem + f" · page {source['page_index'] + 1}")
        self.title.setObjectName('EvidenceTitleField')
        self.title.setAccessibleName('Working sheet title')
        self.title.setMaxLength(160)
        name_row = QHBoxLayout()
        name_label = words('[ SHEET NAME ]');name_label.setObjectName('EvidenceTitle')
        name_row.addWidget(name_label);name_row.addWidget(self.title, 1)
        box.addLayout(name_row)
        row = QHBoxLayout()
        row.setSpacing(16)
        self.crop = None
        if not page_image.isNull():
            original = QFrame();original.setObjectName('EvidencePanel')
            left = QVBoxLayout(original)
            left.setContentsMargins(12, 10, 12, 10)
            title = words(f"[ PDF SOURCE · PAGE {source['page_index'] + 1} ]")
            title.setObjectName('EvidenceTitle')
            left.addWidget(title)
            original_name = words(source['name'] + ' · ' + source['layer'].upper())
            original_name.setObjectName('EvidenceMeta')
            left.addWidget(original_name)
            if source.get('source_sha256'):
                digest = words('SHA-256 · ' + source['source_sha256'][:12]);digest.setObjectName('EvidenceMeta')
                digest.setToolTip(source['source_sha256']);left.addWidget(digest)
            # the page beside the rows is shown as the page behind this review is: in the desk's light, or in its own
            self.crop = SourceCrop(page_light.lit(page_image, getattr(getattr(parent, 'canvas', None), 'own_light', False)), source['rect'], round(width * .435))
            self.original_scroll = QScrollArea()
            self.original_scroll.setWidget(self.crop)
            self.original_scroll.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            self.original_scroll.setFrameShape(QFrame.NoFrame)
            left.addWidget(self.original_scroll, 1)
            row.addWidget(original, 1)
        self.table = QTableWidget(len(preview['rows']), 5)
        self.table.setObjectName('EvidenceRows')
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setHorizontalHeaderLabels(['Keep', 'Parameter', 'Value', 'Unit', 'Conditions'])
        self.table.setAccessibleName('Editable source row candidates')
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(43)
        header = self.table.horizontalHeader()
        for column, size in ((0, 54), (2, 74), (3, 64)):
            header.setSectionResizeMode(column, QHeaderView.Fixed)
            self.table.setColumnWidth(column, size)
        for column in (1, 4):
            header.setSectionResizeMode(column, QHeaderView.Stretch)
        for i, value in enumerate(preview['rows']):
            mark = QTableWidgetItem('Review OCR' if value['ocr_uncertain'] else '')
            mark.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            mark.setCheckState(Qt.Checked)
            self.table.setItem(i, 0, mark)
            hint = ' · '.join(['Original row', *value['cells'], *value['gaps']])
            for c, field in enumerate(self.fields, 1):
                cell = QTableWidgetItem(value[field])
                cell.setToolTip('<qt>' + escape(hint) + '</qt>')
                self.table.setItem(i, c, cell)
        candidates = QFrame();candidates.setObjectName('EvidencePanel')
        right = QVBoxLayout(candidates)
        right.setContentsMargins(12, 10, 12, 10)
        title = words('[ COMPARISON SHEET · CANDIDATE ROWS ]')
        title.setObjectName('EvidenceTitle')
        right.addWidget(title)
        right.addWidget(self.table, 1)
        self.evidence = words('')
        self.evidence.setObjectName('EvidenceSelected')
        self.evidence.setAccessibleName('Selected row unit and operating conditions')
        self.evidence.setText('Select a row to review its unit and conditions.')
        right.addWidget(self.evidence)
        row.addWidget(candidates, 1)
        box.addLayout(row, 1)
        self.table.currentCellChanged.connect(self.show_evidence)
        self.table.itemChanged.connect(self.show_evidence)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText('Save reviewed sheet')
        buttons.button(QDialogButtonBox.Ok).setObjectName('EvidenceCommit')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)
        if self.crop is not None:
            self.link = EvidenceLink(self, self.crop, self.table)
            self.link.setGeometry(self.rect())
            self.original_scroll.verticalScrollBar().valueChanged.connect(self.link.update)
            self.original_scroll.horizontalScrollBar().valueChanged.connect(self.link.update)
            self.table.verticalScrollBar().valueChanged.connect(self.link.update)
        if self.table.rowCount():self.table.setCurrentCell(0, 2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.link is not None:
            self.link.setGeometry(self.rect())

    def show_evidence(self, *_):
        row = self.table.currentRow()
        if row < 0:return
        if self.crop is not None:
            self.crop.mark(self.preview['rows'][row]['words'])
            self.original_scroll.ensureVisible(self.crop.width() // 2, round(self.crop.highlight.center().y()), 0, 18)
            self.link.update()
        unit = self.table.item(row, 3).text().strip()
        condition = self.table.item(row, 4).text().strip()
        self.evidence.setText(('Row %d · ' % (row + 1)) + ('Unit ' + unit if unit else '[!] Unit open') +
                              (' · ' + condition if condition else ' · Condition open'))

    def reviewed_rows(self):
        return [{'source_row': value['source_row'], **{field: self.table.item(i, col).text()
                 for col, field in enumerate(self.fields, 1)}} for i, value in enumerate(self.preview['rows'])
                if self.table.item(i, 0).checkState() == Qt.Checked]


def review_pdf_table(tab):
    page = tab.page_result
    if not page or not tab.table_page_job:
        tab.status.setText('Open a current PDF page first.')
        return
    layer = 'ocr' if page.get('ocr') and (tab.views.currentWidget() is tab.ocr_text or not page['native']['words']) else 'native'
    args = {'job': tab.table_page_job, 'rect': list(tab.canvas.region), 'layer': layer}

    def previewed(preview):
        if tab.table_page_job != args['job'] or list(tab.canvas.region) != args['rect']:
            return
        if preview['state'] != 'REVIEW':
            tab.status.setText(preview['message'])
            return
        dialog = TableReview(tab, preview, tab.canvas.image)
        if dialog.exec():
            def saved(value):
                from .office_qt import open_office
                tab.host.concern.rebuild()
                open_office(tab.host, value['id'])
            tab.call('office.datasheet.create', {**args, 'expected_digest': preview['digest'],
                'title': dialog.title.text(), 'rows': dialog.reviewed_rows()}, saved)

    tab.call('office.datasheet.preview', args, previewed)


def calculate_report(panel):
    from .office_qt import invoke
    dialog = QDialog(panel)
    dialog.setWindowTitle('Calculate from this sheet')
    dialog.resize(470, 300)
    form = QFormLayout(dialog)
    form.addRow(words('Name the cells in the Value column. Their units and conditions travel with the result.'))
    expression = QLineEdit()
    expression.setPlaceholderText('voltage * current')
    form.addRow('Expression', expression)
    inputs = QPlainTextEdit()
    inputs.setPlaceholderText('voltage = B2\ncurrent = B3')
    inputs.setMaximumHeight(85)
    form.addRow('Named cells', inputs)
    unit = QLineEdit()
    unit.setPlaceholderText('W')
    form.addRow('Result unit', unit)
    assumption = QLineEdit()
    form.addRow('Assumption', assumption)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.button(QDialogButtonBox.Ok).setText('Write editable report')
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    if not dialog.exec():
        return
    named = {}
    try:
        for line in inputs.toPlainText().splitlines():
            if not line.strip():
                continue
            symbol, equals, address = line.partition('=')
            symbol = symbol.strip()
            if not equals or not symbol or symbol in named:
                raise ValueError('Enter one distinct name and cell per line, such as voltage = B2.')
            named[symbol] = address.strip().upper()
        value = invoke(panel.host, 'datasheet.report', {'id': panel.ident, 'expected_revision': panel.base['revision'],
            'expression': expression.text().strip(), 'inputs': named,
            'output_unit': unit.text().strip(), 'assumption': assumption.text().strip()})
    except (ValueError, OSError) as exc:
        panel.status.setText(str(exc))
        return
    from .document_qt import show
    show(panel.host, value['document']['id'])
