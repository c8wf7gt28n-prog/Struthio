"""Spreadsheets Slate can change: an .xlsx read as a list of cells, and changed cell by cell. Standard library only.

Slate sees a workbook as plain lines (Sheet1!B3 = 16, Sheet1!C2 = "10k", Sheet1!D4 = =B4*C4) and answers with only the cells to
change, in the same form. Ledger applies them to a copy of the workbook: the cell's value is set, any formula in that
cell is replaced, every other byte of the workbook (styles, other sheets, charts) is carried over, and the workbook is
marked to recalculate when it is next opened. As with text, his change lands in a working copy for your review.
"""
from __future__ import annotations
import io
import re
import zipfile
import xml.etree.ElementTree as ET

MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
CELL = re.compile(r'([A-Z]{1,3})([1-9][0-9]{0,6})')
EDIT = re.compile(r'^\s*(?:(?P<sheet>[^!=\n]{1,31})!)?(?P<cell>[A-Za-z]{1,3}[1-9][0-9]{0,6})\s*=\s*(?P<value>.*?)\s*$')
FENCE = '```cells'
MAX_EDITS = 500


def q(tag):
    return '{%s}%s' % (MAIN, tag)


def col_number(letters):
    n = 0
    for ch in letters:n = n * 26 + ord(ch) - 64
    return n


def register_namespaces(raw):
    """Keep every prefix the workbook uses, so the rewritten XML says exactly what it said (mc:Ignorable names them)."""
    for _, (prefix, uri) in ET.iterparse(io.BytesIO(raw), events=('start-ns',)):
        try:ET.register_namespace(prefix, uri)
        except ValueError:pass


def sheet_paths(parts):
    book = ET.fromstring(parts['xl/workbook.xml']);rels = ET.fromstring(parts['xl/_rels/workbook.xml.rels'])
    targets = {r.get('Id'): r.get('Target') for r in rels}
    out = {}
    for s in book.iter(q('sheet')):
        target = targets.get(s.get('{%s}id' % REL), '')
        target = target.lstrip('/');target = target if target.startswith('xl/') else 'xl/' + target
        out[s.get('name')] = target
    return out


def shared(parts):
    if 'xl/sharedStrings.xml' not in parts:return []
    return [''.join(t.text or '' for t in si.iter(q('t'))) for si in ET.fromstring(parts['xl/sharedStrings.xml']).iter(q('si'))]


def read_parts(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if sum(i.file_size for i in z.infolist()) > 200 * 1024 * 1024:raise ValueError('SHEET_TOO_LARGE')
        return {i.filename: z.read(i) for i in z.infolist()}, [i for i in z.infolist()]


def as_text(data, limit=6000):
    """The workbook as lines Slate can read: every filled cell, sheet by sheet, until the limit."""
    parts, _ = read_parts(data);strings = shared(parts);lines = []
    for name, path in sheet_paths(parts).items():
        if path not in parts:continue
        for c in ET.fromstring(parts[path]).iter(q('c')):
            f = c.find(q('f'));v = c.find(q('v'));t = c.get('t')
            if t == 'inlineStr':value = '"%s"' % ''.join(x.text or '' for x in c.iter(q('t')))
            elif t == 's' and v is not None:value = '"%s"' % strings[int(v.text)] if int(v.text) < len(strings) else '""'
            elif t == 'str' and v is not None:value = '"%s"' % (v.text or '')
            else:value = v.text if v is not None else ''
            if f is not None and f.text:value = '=' + f.text + ('   (now %s)' % value if value else '')
            if value != '':lines.append('%s!%s = %s' % (name, c.get('r'), value))
            if sum(len(l) + 1 for l in lines) > limit:lines.append('… (more cells not shown)');return '\n'.join(lines)
    return '\n'.join(lines)


def parse_edits(text, default_sheet):
    """Lines like `Sheet1!B3 = 16`, `C2 = "10k"`, `D4 = =B4*C4`, `E9 =` (empty clears). Anything else is refused."""
    edits = []
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith('#'):continue
        m = EDIT.match(line)
        if not m:raise ValueError('SHEET_EDIT: not a cell change: %s' % line[:120])
        raw = m.group('value');raw = raw.split('   (now ')[0]
        if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:value = raw[1:-1]
        elif raw.startswith('='):value = raw
        elif raw == '':value = None
        else:
            try:value = int(raw) if re.fullmatch(r'-?\d+', raw) else float(raw)
            except ValueError:value = raw
        edits.append({'sheet': (m.group('sheet') or default_sheet).strip().strip("'"), 'cell': m.group('cell').upper(), 'value': value})
    if len(edits) > MAX_EDITS:raise ValueError('SHEET_EDIT: up to %d cells at a time' % MAX_EDITS)
    return edits


def set_cell(sheet, ref, value):
    data = sheet.find(q('sheetData'))
    letters, number = CELL.fullmatch(ref).groups();number = int(number)
    rows = data.findall(q('row'));row = next((r for r in rows if int(r.get('r', 0)) == number), None)
    if row is None:
        if value is None:return
        row = ET.Element(q('row'), {'r': str(number)})
        after = [i for i, r in enumerate(list(data)) if r.tag == q('row') and int(r.get('r', 0)) < number]
        data.insert(after[-1] + 1 if after else 0, row)
    cells = row.findall(q('c'));cell = next((c for c in cells if c.get('r') == ref), None)
    if value is None:
        if cell is not None:row.remove(cell)
        return
    if cell is None:
        cell = ET.Element(q('c'), {'r': ref})
        before = [i for i, c in enumerate(list(row)) if c.tag == q('c') and col_number(CELL.fullmatch(c.get('r')).group(1)) < col_number(letters)]
        row.insert(before[-1] + 1 if before else 0, cell)
    style = cell.get('s');cell.attrib.clear();cell.set('r', ref)
    if style:cell.set('s', style)
    for child in list(cell):cell.remove(child)
    if isinstance(value, str) and value.startswith('='):
        ET.SubElement(cell, q('f')).text = value[1:]
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        ET.SubElement(cell, q('v')).text = repr(value) if isinstance(value, float) else str(value)
    else:
        cell.set('t', 'inlineStr');t = ET.SubElement(ET.SubElement(cell, q('is')), q('t'));t.text = str(value)
        if str(value) != str(value).strip():t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')


def xml(root):
    body = ET.tostring(root, encoding='unicode')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + body).encode('utf-8')


def apply(data, edits):
    """A new workbook with the edits made. Raises ValueError for a sheet or cell that does not exist or cannot be named."""
    parts, infos = read_parts(data);paths = sheet_paths(parts);touched = {}
    for e in edits:
        if e['sheet'] not in paths:raise ValueError('SHEET_EDIT: no sheet called %r' % e['sheet'])
        if not CELL.fullmatch(e['cell']):raise ValueError('SHEET_EDIT: not a cell: %s' % e['cell'])
        path = paths[e['sheet']]
        if path not in touched:register_namespaces(parts[path]);touched[path] = ET.fromstring(parts[path])
        set_cell(touched[path], e['cell'], e['value'])
    for path, root in touched.items():parts[path] = xml(root)
    # Formulas elsewhere may depend on what changed: drop the cached calculation order and ask for a full recalculation.
    register_namespaces(parts['xl/workbook.xml']);book = ET.fromstring(parts['xl/workbook.xml'])
    calc = book.find(q('calcPr'))
    if calc is None:  # its place in the schema: right after sheets, functionGroups, externalReferences and definedNames
        calc = ET.Element(q('calcPr'));kids = list(book)
        before = [i for i, k in enumerate(kids) if k.tag in (q('sheets'), q('functionGroups'), q('externalReferences'), q('definedNames'))]
        book.insert(before[-1] + 1 if before else len(kids), calc)
    calc.set('fullCalcOnLoad', '1')
    parts['xl/workbook.xml'] = xml(book)
    if 'xl/calcChain.xml' in parts:
        del parts['xl/calcChain.xml']
        rels = parts['xl/_rels/workbook.xml.rels'].decode('utf-8')
        parts['xl/_rels/workbook.xml.rels'] = re.sub(r'<Relationship [^>]*Target="/?(?:xl/)?calcChain\.xml"[^>]*/>', '', rels).encode('utf-8')
        types = parts['[Content_Types].xml'].decode('utf-8')
        parts['[Content_Types].xml'] = re.sub(r'<Override [^>]*PartName="/xl/calcChain\.xml"[^>]*/>', '', types).encode('utf-8')
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for info in infos:
            if info.filename in parts:z.writestr(info, parts[info.filename])
    return out.getvalue()


def first_sheet(data):
    parts, _ = read_parts(data)
    return next(iter(sheet_paths(parts)), 'Sheet1')
