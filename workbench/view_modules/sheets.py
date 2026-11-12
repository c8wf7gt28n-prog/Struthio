"""Spreadsheets: Excel (.xlsx, .xlsm) and LibreOffice (.ods) sheets, read with the standard library, shown as tables.

Values are read as stored (the last computed result of a formula, not the formula); nothing is recalculated or changed.
Each sheet is a page with sort (click a column) and a filter that keeps the rows containing what you type.
"""
from __future__ import annotations
from ..text_prompts import writing_prompt
import io
import re
import zipfile
from xml.etree import ElementTree as ET

KINDS = ('spreadsheet',)
MAX_ROWS, MAX_COLUMNS, MAX_SHEETS = 5000, 200, 30
S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
TABLE = '{urn:oasis:names:tc:opendocument:xmlns:table:1.0}'
TEXT = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
OFFICE = '{urn:oasis:names:tc:opendocument:xmlns:office:1.0}'


def claim(source, head):
    if head.startswith(b'PK\x03\x04') and source.suffix in ('.xlsx', '.xlsm', '.ods'):return 'spreadsheet'
    return None


def column_index(ref):
    letters = re.match(r'[A-Z]+', ref).group(0);n = 0
    for c in letters:n = n * 26 + ord(c) - 64
    return n - 1


def xlsx(archive):
    shared = []
    if 'xl/sharedStrings.xml' in archive.namelist():
        for si in ET.fromstring(archive.read('xl/sharedStrings.xml')).iter(S + 'si'):shared.append(''.join(t.text or '' for t in si.iter(S + 't')))
    book = ET.fromstring(archive.read('xl/workbook.xml'))
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
    sheets = []
    for sheet in list(book.iter(S + 'sheet'))[:MAX_SHEETS]:
        target = rels.get(sheet.get(R + 'id'), '').lstrip('/');path = target if target.startswith('xl/') else 'xl/' + target
        if path not in archive.namelist():continue
        rows = []
        for row in ET.fromstring(archive.read(path)).iter(S + 'row'):
            values = {}
            for cell in row.iter(S + 'c'):
                ref = cell.get('r');kind = cell.get('t');v = cell.find(S + 'v')
                if kind == 'inlineStr':text = ''.join(t.text or '' for t in cell.iter(S + 't'))
                elif v is None:continue
                elif kind == 's':text = shared[int(v.text)] if v.text and int(v.text) < len(shared) else ''
                elif kind == 'b':text = 'TRUE' if v.text == '1' else 'FALSE'
                else:text = v.text or ''
                index = column_index(ref) if ref else len(values)
                if index < MAX_COLUMNS:values[index] = text
            if values:
                number = int(row.get('r', len(rows) + 1)) - 1
                while len(rows) < number and len(rows) < MAX_ROWS:rows.append([])
                rows.append([values.get(i, '') for i in range(max(values) + 1)])
            if len(rows) >= MAX_ROWS:break
        sheets.append((sheet.get('name') or 'Sheet', rows))
    return sheets


def ods(archive):
    content = ET.fromstring(archive.read('content.xml'));sheets = []
    for table in list(content.iter(TABLE + 'table'))[:MAX_SHEETS]:
        rows = []
        for row in table.iter(TABLE + 'table-row'):
            repeat = min(int(row.get(TABLE + 'number-rows-repeated', '1')), 1000);values = []
            for cell in row:
                if cell.tag not in (TABLE + 'table-cell', TABLE + 'covered-table-cell'):continue
                text = cell.get(OFFICE + 'value') if cell.get(OFFICE + 'value-type') in ('float', 'percentage', 'currency') else None
                if text is None:text = '\n'.join(''.join(p.itertext()) for p in cell.iter(TEXT + 'p'))
                values += [text] * min(int(cell.get(TABLE + 'number-columns-repeated', '1')), MAX_COLUMNS)
                if len(values) >= MAX_COLUMNS:break
            while values and values[-1] == '':values.pop()
            for _ in range(repeat):
                rows.append(list(values))
                if len(rows) >= MAX_ROWS:break
            if len(rows) >= MAX_ROWS:break
        while rows and not rows[-1]:rows.pop()
        sheets.append((table.get(TABLE + 'name') or 'Sheet', rows))
    return sheets


def describe(source, view):
    archive = zipfile.ZipFile(io.BytesIO(source.all()))
    sheets = ods(archive) if source.suffix == '.ods' else xlsx(archive)
    view['sheets'] = []
    for name, rows in sheets:
        width = max((len(r) for r in rows), default=0)
        view['sheets'].append({'name': name, 'columns': width, 'rows': [r + [''] * (width - len(r)) for r in rows]})
    view['summary'] += [('Sheets', str(len(sheets)))] + [(name, '%d rows · %d columns' % (len(rows), max((len(r) for r in rows), default=0))) for name, rows in sheets[:8]]
    if any(len(rows) >= MAX_ROWS for _, rows in sheets):view['notice'] = 'Shown up to %d rows per sheet.' % MAX_ROWS


DESCRIBERS = {'spreadsheet': describe}


def letters(n):
    out = ''
    while True:
        n, r = divmod(n, 26);out = chr(65 + r) + out
        if n == 0:return out
        n -= 1


def sheet_page(sheet):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
    page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(0, 8, 0, 0)
    search = QLineEdit();writing_prompt(search, 'Keep rows containing…');search.setClearButtonEnabled(True);box.addWidget(search)
    count = QLabel();count.setStyleSheet('color:#6c675e');box.addWidget(count)
    table = QTableWidget(len(sheet['rows']), sheet['columns']);table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setHorizontalHeaderLabels([letters(i) for i in range(sheet['columns'])]);table.setAccessibleName('Sheet ' + sheet['name'])
    for r, row in enumerate(sheet['rows']):
        for c, value in enumerate(row):
            item = QTableWidgetItem()
            try:item.setData(Qt.DisplayRole, float(value) if re.fullmatch(r'-?\d+(\.\d+)?([eE][-+]?\d+)?', value.strip()) else value)
            except ValueError:item.setData(Qt.DisplayRole, value)
            table.setItem(r, c, item)
    table.setSortingEnabled(True);box.addWidget(table, 1)

    def apply(text):
        needle = text.casefold();shown = 0
        for r in range(table.rowCount()):
            hit = not needle or any(needle in (table.item(r, c).text() if table.item(r, c) else '').casefold() for c in range(table.columnCount()))
            table.setRowHidden(r, not hit);shown += hit
        count.setText('%d of %d rows' % (shown, table.rowCount()) + ('' if not needle else ' contain “%s”' % text) + ' · click a column to sort')
    search.textChanged.connect(apply);apply('')
    return page


def pages(tab, view):
    if not view.get('sheets'):return []
    return [(sheet['name'][:24], lambda sheet=sheet:sheet_page(sheet)) for sheet in view['sheets']]


def thumbnail(path, kind, size):
    from ..universal_view import Source
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
    view = {'summary': []};describe(Source.file(path), view)
    rows = view['sheets'][0]['rows'][:8] if view['sheets'] else []
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied);image.fill(QColor('#fffdf8'))
    p = QPainter(image);p.setPen(QPen(QColor('#dad4c8'), 1))
    cell_h = max(8, size // 9);cell_w = max(16, size // 3)
    for i in range(size // cell_h + 1):p.drawLine(0, i * cell_h, size, i * cell_h)
    for j in range(size // cell_w + 1):p.drawLine(j * cell_w, 0, j * cell_w, size)
    f = QFont('IBM Plex Sans');f.setPixelSize(max(6, cell_h - 3));p.setFont(f);p.setPen(QColor('#504d46'))
    for r, row in enumerate(rows):
        for c, value in enumerate(row[:3]):p.drawText(QRectF(c * cell_w + 2, r * cell_h, cell_w - 4, cell_h), Qt.AlignVCenter, str(value)[:10])
    p.end();return image
