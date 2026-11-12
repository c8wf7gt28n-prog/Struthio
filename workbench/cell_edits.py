"""Typed CSV/TSV and conservative XLSX cell adapters. No formula evaluation.

CSV preserves cell strings and newline style, but reserializes quoting. XLSX
retains every unmodified ZIP part byte-for-byte. Only a declared simple workbook
profile is editable; unsupported packages remain importable opaque originals.
"""
from __future__ import annotations
import csv
from decimal import Decimal, InvalidOperation, localcontext
import io
import math
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET

MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
XML = 'http://www.w3.org/XML/1998/namespace'
NS = {'s': MAIN}; Q = lambda name: '{' + MAIN + '}' + name
VALUE = {'type': 'object', 'additionalProperties': False, 'properties': {
    'kind': {'type': 'string', 'enum': ['TEXT', 'NUMBER', 'BOOLEAN', 'FORMULA', 'EMPTY']},
    'value': {'type': 'string', 'maxLength': 32767}}, 'required': ['kind', 'value']}
CELL = {'type': 'object', 'additionalProperties': False, 'properties': {
    'cell': {'type': 'string', 'minLength': 2, 'maxLength': 12}, 'old': VALUE, 'new': VALUE}, 'required': ['cell', 'old', 'new']}
FUNCTIONS = frozenset({'SUM', 'AVERAGE', 'MIN', 'MAX', 'COUNT', 'COUNTA', 'IF', 'AND', 'OR', 'NOT', 'ROUND', 'ABS', 'TRUE', 'FALSE'})


def coordinates(cell):
    match = re.fullmatch(r'([A-Z]{1,3})([1-9][0-9]{0,6})', cell)
    if not match: raise ValueError('Use an uppercase cell address such as B2')
    column = 0
    for char in match[1]: column = column * 26 + ord(char) - 64
    row = int(match[2])
    if column > 16384 or row > 1048576: raise ValueError('Cell is outside spreadsheet bounds')
    return row, column


def typed(kind, value=''):
    if not isinstance(value, str) or len(value) > 32767 or any(ord(c) < 32 and c not in '\t\n\r' for c in value): raise ValueError('Invalid cell value')
    if kind == 'EMPTY':
        if value: raise ValueError('Empty cells have an empty value')
    elif kind == 'NUMBER':
        if len(value) > 80: raise ValueError('Numeric cell bound')
        try: number = Decimal(value)
        except InvalidOperation: raise ValueError('Invalid numeric cell') from None
        if not number.is_finite() or abs(number.adjusted()) > 1000: raise ValueError('Nonfinite or extreme numeric cell')
        with localcontext() as context:
            context.prec = 100
            normal = number.normalize()
            value = format(normal, 'f') if -20 <= normal.adjusted() <= 40 else str(normal)
    elif kind == 'BOOLEAN':
        if value not in ('true', 'false'): raise ValueError('Boolean values are true or false')
    elif kind == 'FORMULA':
        value = value.removeprefix('=')
        if not value or len(value) > 8192 or any(c in value for c in ('[', ']', '|', '\\', '\n', '\r')) or '://' in value:
            raise ValueError('Only local formulas are supported')
        names = re.findall(r'([A-Za-z_][A-Za-z0-9_.]*)\s*\(', value)
        if any(name.upper() not in FUNCTIONS for name in names): raise ValueError('Formula function is outside the supported local profile')
        if value.count('(') != value.count(')'): raise ValueError('Formula parentheses are unbalanced')
    elif kind != 'TEXT': raise ValueError('Unsupported cell kind')
    return {'kind': kind, 'value': value}


def csv_table(raw, suffix):
    if len(raw) > 16 * 1024 * 1024: raise ValueError('CSV adapter supports up to 16 MiB')
    bom = raw.startswith(b'\xef\xbb\xbf'); text = raw.decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(text, newline=''), delimiter='\t' if suffix == '.tsv' else ',', strict=True))
    if sum(len(row) for row in rows) > 200000: raise ValueError('CSV cell count bound')
    return rows, bom, '\r\n' if '\r\n' in text else '\n', text.endswith(('\r', '\n'))


def xml(raw):
    if len(raw) > 8 * 1024 * 1024 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): raise ValueError('Unsupported or oversized XML')
    return ET.fromstring(raw)


def supported_xml(raw):
    root = xml(raw)
    for node in root.iter():
        for name in [node.tag, *node.attrib]:
            if name.startswith('{') and name[1:].split('}', 1)[0] not in (MAIN, REL, XML):
                raise ValueError('Workbook extensions exceed this adapter\'s preservation profile')
    return root


def package(raw):
    if len(raw) > 16 * 1024 * 1024: raise ValueError('XLSX adapter supports up to 16 MiB')
    archive = zipfile.ZipFile(io.BytesIO(raw)); entries = archive.infolist(); parts = {}; info = {}
    if len(entries) > 2000 or sum(e.file_size for e in entries) > 64 * 1024 * 1024: raise ValueError('XLSX expansion bound')
    for entry in entries:
        name = entry.filename
        if name in parts or name.startswith('/') or '..' in name.split('/') or '\\' in name or entry.flag_bits & 1:
            raise ValueError('Unsafe or duplicate XLSX package part')
        if entry.file_size > max(1048576, entry.compress_size * 200): raise ValueError('XLSX expansion ratio bound')
        if any(word in name.casefold() for word in ('vba', 'activex', 'externallink', '_xmlsignatures', 'calcchain', 'embeddings/')):
            raise ValueError('Macro, linked, signed, chained or embedded workbook requires a native application')
        parts[name] = archive.read(entry); info[name] = entry
        if name.endswith('.rels'):
            relationships = xml(parts[name])
            if any(node.get('TargetMode', '').casefold() == 'external' for node in relationships):
                raise ValueError('External workbook relationships are not editable in this profile')
    archive.close()
    workbook = supported_xml(parts['xl/workbook.xml'])
    if workbook.find(Q('definedNames')) is not None: raise ValueError('Named-range workbooks require a native application in this profile')
    if b'macroenabled' in parts.get('[Content_Types].xml', b'').lower(): raise ValueError('Macro-enabled workbook refused')
    relationships = xml(parts['xl/_rels/workbook.xml.rels'])
    targets = {node.get('Id'): posixpath.normpath('xl/' + node.get('Target', '')) if not node.get('Target', '').startswith('/') else node.get('Target').lstrip('/') for node in relationships}
    sheets = []
    for sheet in workbook.findall('s:sheets/s:sheet', NS):
        target = targets.get(sheet.get('{' + REL + '}id'))
        if not target or not target.startswith('xl/worksheets/') or target not in parts: raise ValueError('Worksheet target is outside the workbook')
        tree = supported_xml(parts[target])
        if tree.find(Q('mergeCells')) is not None: raise ValueError('Merged-cell workbooks require a native application in this profile')
        seen_cells = set(); seen_rows = set()
        for row in tree.findall('s:sheetData/s:row', NS):
            row_number = int(row.get('r', '0'))
            if not 1 <= row_number <= 1048576 or row_number in seen_rows: raise ValueError('Ambiguous worksheet rows')
            seen_rows.add(row_number)
            for cell in row.findall(Q('c')):
                address = cell.get('r', ''); cell_row, _ = coordinates(address)
                if address in seen_cells or cell_row != row_number: raise ValueError('Ambiguous worksheet cell address')
                seen_cells.add(address)
        if len(seen_cells) > 200000: raise ValueError('Worksheet cell count bound')
        for formula in tree.iter(Q('f')):
            if formula.attrib: raise ValueError('Shared, array and table formulas require a native application')
            typed('FORMULA', formula.text or '')
        sheets.append((sheet.get('name'), target, tree))
    shared = []
    if 'xl/sharedStrings.xml' in parts:
        shared = [''.join(node.itertext()) for node in xml(parts['xl/sharedStrings.xml']).findall(Q('si'))]
    return parts, info, workbook, sheets, shared


def xlsx_value(cell, shared):
    if cell is None: return typed('EMPTY')
    formula = cell.find(Q('f'))
    if formula is not None: return {'kind': 'FORMULA', 'value': formula.text or ''}
    value = cell.findtext(Q('v')); kind = cell.get('t')
    if kind == 'inlineStr': return typed('TEXT', ''.join(cell.find(Q('is')).itertext()) if cell.find(Q('is')) is not None else '')
    if kind == 's': return typed('TEXT', shared[int(value)])
    if kind == 'b': return typed('BOOLEAN', 'true' if value == '1' else 'false')
    if kind in ('str', 'e'): return typed('TEXT', value or '')
    return typed('EMPTY') if value is None else typed('NUMBER', value)


def describe(raw, suffix, sheet=None, cell=None):
    if suffix in ('.csv', '.tsv'):
        rows, _, _, _ = csv_table(raw, suffix)
        value = None
        if cell:
            r, c = coordinates(cell)
            if r > len(rows) or c > len(rows[r - 1]): raise ValueError('CSV cell is outside existing rows/columns')
            value = typed('TEXT', rows[r - 1][c - 1])
        return {'adapter': 'CSV_STRINGS_V1', 'sheets': ['Table'], 'rows': len(rows), 'cell': value,
            'limits': 'Quoting is reserialized; cell strings, BOM and newline style are preserved. No formula evaluation.'}
    parts, _, _, sheets, shared = package(raw)
    value = None
    if cell:
        coordinates(cell); selected = next((tree for name, _, tree in sheets if name == sheet), None)
        if selected is None: raise ValueError('Choose an existing sheet')
        value = xlsx_value(next((node for node in selected.iter(Q('c')) if node.get('r') == cell), None), shared)
    return {'adapter': 'XLSX_SIMPLE_LOCAL_CELLS_V1', 'sheets': [name for name, _, _ in sheets], 'cell': value,
            'limits': 'Simple local cells only. Unmodified ZIP parts retained. Cached formula results cleared; recalculate externally.'}


def apply(raw, suffix, edits, sheet=None):
    if not 1 <= len(edits) <= 200: raise ValueError('Use one to 200 distinct cell changes')
    if len({e['cell'] for e in edits}) != len(edits): raise ValueError('Duplicate cell edits')
    changes = []
    if suffix in ('.csv', '.tsv'):
        rows, bom, newline, trailing = csv_table(raw, suffix)
        for edit in edits:
            r, c = coordinates(edit['cell'])
            if r > len(rows) or c > len(rows[r - 1]): raise ValueError('CSV edits target existing cells only')
            old = typed('TEXT', rows[r - 1][c - 1]); expected = typed(**edit['old']); new = typed(**edit['new'])
            if old != expected: raise ValueError('Cell base value changed')
            if new['kind'] == 'FORMULA': raise ValueError('CSV formula edits are not supported')
            rows[r - 1][c - 1] = new['value']; changes.append({'cell': edit['cell'], 'old': old, 'new': new})
        stream = io.StringIO(newline=''); writer = csv.writer(stream, delimiter='\t' if suffix == '.tsv' else ',', lineterminator=newline)
        writer.writerows(rows); value = stream.getvalue()
        if not trailing and value.endswith(newline): value = value[:-len(newline)]
        return (b'\xef\xbb\xbf' if bom else b'') + value.encode(), {'adapter': 'CSV_STRINGS_V1', 'cells': changes, 'recalculated': False, 'quoting_reserialized': True}
    if suffix != '.xlsx': raise ValueError('Cell editing supports CSV, TSV and the simple XLSX profile')
    parts, infos, workbook, sheets, shared = package(raw)
    selected = next(((name, path, tree) for name, path, tree in sheets if name == sheet), None)
    if selected is None: raise ValueError('Choose an existing sheet')
    _, path, tree = selected; data = tree.find(Q('sheetData'))
    if data is None: raise ValueError('Worksheet has no cell data')
    for edit in edits:
        r, c = coordinates(edit['cell']); row = next((n for n in data if n.get('r') == str(r)), None)
        if row is None:
            row = ET.Element(Q('row'), {'r': str(r)}); position = next((i for i, n in enumerate(data) if int(n.get('r', '0')) > r), len(data)); data.insert(position, row)
        cell = next((n for n in row if n.get('r') == edit['cell']), None)
        old = xlsx_value(cell, shared); expected = typed(**edit['old']); new = typed(**edit['new'])
        if old != expected: raise ValueError('Cell base value changed')
        if cell is None:
            cell = ET.Element(Q('c'), {'r': edit['cell']}); position = next((i for i, n in enumerate(row) if coordinates(n.get('r'))[1] > c), len(row)); row.insert(position, cell)
        for child in list(cell): cell.remove(child)
        cell.attrib.pop('t', None)
        if new['kind'] == 'TEXT':
            cell.set('t', 'inlineStr'); inline = ET.SubElement(cell, Q('is')); text = ET.SubElement(inline, Q('t'), {'{' + XML + '}space': 'preserve'}); text.text = new['value']
        elif new['kind'] == 'FORMULA': ET.SubElement(cell, Q('f')).text = new['value']
        elif new['kind'] != 'EMPTY':
            if new['kind'] == 'BOOLEAN': cell.set('t', 'b')
            ET.SubElement(cell, Q('v')).text = ('1' if new['value'] == 'true' else '0') if new['kind'] == 'BOOLEAN' else new['value']
        changes.append({'sheet': sheet, 'cell': edit['cell'], 'old': old, 'new': new})
    # Invalidate caches throughout the workbook; do not invent calculated values.
    cleared = 0
    ET.register_namespace('', MAIN); ET.register_namespace('r', REL)
    for _, sheet_path, sheet_tree in sheets:
        changed = sheet_path == path
        for cell in sheet_tree.iter(Q('c')):
            if cell.find(Q('f')) is not None:
                cached = cell.find(Q('v'))
                if cached is not None: cell.remove(cached); cleared += 1; changed = True
        if changed:
            addresses = [node.get('r') for node in sheet_tree.iter(Q('c')) if node.get('r')]
            if addresses:
                dimension = sheet_tree.find(Q('dimension'))
                if dimension is not None:
                    points = [coordinates(address) for address in addresses]
                    def address(r, c):
                        word = ''
                        while c: c, rem = divmod(c - 1, 26); word = chr(65 + rem) + word
                        return word + str(r)
                    dimension.set('ref', address(min(r for r, _ in points), min(c for _, c in points)) + ':' +
                                  address(max(r for r, _ in points), max(c for _, c in points)))
            parts[sheet_path] = ET.tostring(sheet_tree, encoding='utf-8', xml_declaration=True)
    calc = workbook.find(Q('calcPr'))
    if calc is None: calc = ET.SubElement(workbook, Q('calcPr'))
    calc.set('fullCalcOnLoad', '1'); calc.set('forceFullCalc', '1'); calc.set('calcMode', 'auto')
    parts['xl/workbook.xml'] = ET.tostring(workbook, encoding='utf-8', xml_declaration=True)
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as archive:
        for name, info in infos.items(): archive.writestr(info, parts[name])
    return out.getvalue(), {'adapter': 'XLSX_SIMPLE_LOCAL_CELLS_V1', 'cells': changes, 'cached_formula_values_cleared': cleared,
                            'recalculated': False, 'preservation': 'UNMODIFIED_PACKAGE_PART_BYTES_RETAINED'}
