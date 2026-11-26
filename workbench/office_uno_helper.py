"""LibreOffice from the inside, the helper (Graphite 1.0, K5): the one piece of the bridge that speaks LibreOffice's own
interface (UNO).

It runs under a Python that has LibreOffice's uno module (on Debian, the system's /usr/bin/python3 with python3-uno), never
under Graphite's own Python, which cannot import uno. workbench/office_bridge.py starts it as a script (python3 -I -B this
file), beside a headless LibreOffice of her own that listens on a private pipe, and talks to it in JSON lines:

    in   {"id": n, "op": "...", "args": {...}}          one request per line, on stdin
    out  {"id": n, "ok": true, "result": {...}}         one answer per line, on stdout
         {"id": n, "ok": false, "error": "..."}

The first line it writes, before any request, is {"ok": true, "hello": {...}} (or the reason uno cannot be imported).

What it can do (nothing else is reachable through it):
    connect    {pipe, timeout_ms}                  the private pipe of her own LibreOffice; the product's name and version
    open       {url, read_only}                    load a document hidden, macros never run, links never updated
    blocks     {doc}                               Writer: the body's paragraphs and tables, in order
    cells      {doc, sheet?, range?}               Calc: the sheet names and the cells of one sheet (as typed, as shown)
    find       {doc, text}                         where a passage is (Writer: its paragraphs; Calc: its cells)
    replace    {doc, find, replace, expect}        Writer: the passage replaced where it is, only when it is in exactly
                                                   `expect` places (otherwise nothing is changed)
    set_cell   {doc, sheet?, cell, value, kind}    Calc: a value cell set to a number or a text (a formula is refused)
    store      {doc}                               save the document in its own format, where it is
    close      {doc}                               close it (unsaved changes are dropped)
    terminate  {}                                  end her LibreOffice; the helper ends after answering

It never does arithmetic: values travel as the text LibreOffice gives (a cell's formula as typed, its string as shown). The
check that a change was made is not done here: the bridge reads the saved file back itself.
"""
import json
import os
import sys
import time

DOCS = {}
STATE = {'ctx': None, 'desktop': None, 'n': 0}
LIMIT_BLOCKS = 20000
LIMIT_CELLS = 50000
LIMIT_TEXT = 20000


def _prop(name, value):
    from com.sun.star.beans import PropertyValue
    p = PropertyValue()
    p.Name = name
    p.Value = value
    return p


def _why(exc):
    message = getattr(exc, 'Message', '') or str(exc) or ''
    return '%s: %s' % (type(exc).__name__, message.strip()[:600])


def connect(args):
    import uno
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', local)
    url = 'uno:pipe,name=%s;urp;StarOffice.ComponentContext' % args['pipe']
    deadline = time.monotonic() + int(args.get('timeout_ms') or 60000) / 1000
    last = ''
    while True:
        try:
            ctx = resolver.resolve(url)
            break
        except Exception as exc:  # noqa: BLE001 - NoConnectException until her LibreOffice listens
            last = _why(exc)
            if time.monotonic() > deadline:
                raise RuntimeError('her LibreOffice did not answer on its private pipe (%s)' % last)
            time.sleep(0.2)
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
    STATE.update(ctx=ctx, desktop=desktop)
    product = ''
    try:
        provider = smgr.createInstanceWithContext('com.sun.star.configuration.ConfigurationProvider', ctx)
        access = provider.createInstanceWithArguments('com.sun.star.configuration.ConfigurationAccess',
                                                      (_prop('nodepath', '/org.openoffice.Setup/Product'),))
        product = '%s %s' % (access.getByName('ooName'), access.getByName('ooSetupVersionAboutBox'))
    except Exception:  # noqa: BLE001 - the product's name is a courtesy
        product = 'LibreOffice'
    return {'connected': True, 'product': product.strip()}


def _doc(args):
    doc = DOCS.get(args.get('doc'))
    if doc is None:
        raise ValueError('no such open document')
    return doc


def _kind(doc):
    if doc.supportsService('com.sun.star.text.TextDocument'):
        return 'writer'
    if doc.supportsService('com.sun.star.sheet.SpreadsheetDocument'):
        return 'calc'
    return 'other'


def open_document(args):
    desktop = STATE['desktop']
    if desktop is None:
        raise ValueError('not connected')
    props = (_prop('Hidden', True), _prop('ReadOnly', bool(args.get('read_only'))), _prop('MacroExecutionMode', 0),
             _prop('UpdateDocMode', 0))
    doc = desktop.loadComponentFromURL(args['url'], '_blank', 0, props)
    if doc is None:
        raise ValueError('LibreOffice could not open it')
    STATE['n'] += 1
    handle = 'd%d' % STATE['n']
    DOCS[handle] = doc
    modified = False
    try:
        modified = bool(doc.isModified())
    except Exception:  # noqa: BLE001
        pass
    return {'doc': handle, 'kind': _kind(doc), 'modified': modified}


def blocks(args):
    doc = _doc(args)
    if _kind(doc) != 'writer':
        raise ValueError('not a Writer document')
    out = []
    n = 0
    enum = doc.getText().createEnumeration()
    while enum.hasMoreElements() and len(out) < LIMIT_BLOCKS:
        element = enum.nextElement()
        if element.supportsService('com.sun.star.text.TextTable'):
            cells = {}
            for name in element.getCellNames():
                cells[name] = element.getCellByName(name).getString()[:LIMIT_TEXT]
            out.append({'kind': 'table', 'name': element.getName(), 'cells': cells})
        elif element.supportsService('com.sun.star.text.Paragraph'):
            n += 1
            style = ''
            try:
                style = element.ParaStyleName
            except Exception:  # noqa: BLE001
                pass
            out.append({'kind': 'paragraph', 'n': n, 'text': element.getString()[:LIMIT_TEXT], 'style': style})
    return {'blocks': out}


def _column(col):
    name = ''
    col += 1
    while col:
        col, rest = divmod(col - 1, 26)
        name = chr(65 + rest) + name
    return name


def _sheet(doc, name):
    sheets = doc.getSheets()
    if name:
        if not sheets.hasByName(name):
            raise ValueError('there is no sheet "%s"' % name)
        return sheets.getByName(name)
    return sheets.getByIndex(0)


def _cell_view(cell):
    kind = cell.getType().value
    return {'type': kind.lower(), 'formula': cell.getFormula()[:LIMIT_TEXT], 'text': cell.getString()[:LIMIT_TEXT]}


def cells(args):
    doc = _doc(args)
    if _kind(doc) != 'calc':
        raise ValueError('not a Calc spreadsheet')
    names = list(doc.getSheets().getElementNames())
    sheet = _sheet(doc, args.get('sheet'))
    if args.get('range'):
        area = sheet.getCellRangeByName(args['range']).getRangeAddress()
        first_col, first_row, last_col, last_row = area.StartColumn, area.StartRow, area.EndColumn, area.EndRow
    else:
        cursor = sheet.createCursor()
        cursor.gotoEndOfUsedArea(False)
        area = cursor.getRangeAddress()
        first_col, first_row, last_col, last_row = 0, 0, area.EndColumn, area.EndRow
    out = {}
    for row in range(first_row, last_row + 1):
        for col in range(first_col, last_col + 1):
            cell = sheet.getCellByPosition(col, row)
            view = _cell_view(cell)
            if view['type'] == 'empty':
                continue
            out['%s%d' % (_column(col), row + 1)] = view
            if len(out) >= LIMIT_CELLS:
                break
        if len(out) >= LIMIT_CELLS:
            break
    return {'sheets': names, 'sheet': sheet.getName(), 'cells': out}


def _descriptor(searchable, text):
    descriptor = searchable.createSearchDescriptor()
    descriptor.SearchString = text
    descriptor.SearchCaseSensitive = True
    descriptor.SearchRegularExpression = False
    descriptor.SearchWords = False
    return descriptor


def _paragraph_of(found):
    cursor = found.getText().createTextCursorByRange(found)
    cursor.gotoStartOfParagraph(False)
    cursor.gotoEndOfParagraph(True)
    return cursor.getString()[:LIMIT_TEXT]


def _writer_found(doc, text):
    found = doc.findAll(_descriptor(doc, text))
    return [found.getByIndex(i) for i in range(found.getCount())] if found is not None else []


def find(args):
    doc = _doc(args)
    text = args['text']
    if _kind(doc) == 'writer':
        return {'kind': 'writer', 'places': [{'paragraph': _paragraph_of(r)} for r in _writer_found(doc, text)]}
    if _kind(doc) == 'calc':
        places = []
        sheets = doc.getSheets()
        for name in sheets.getElementNames():
            sheet = sheets.getByName(name)
            found = sheet.findAll(_descriptor(sheet, text))
            if found is None:
                continue
            enum = found.getCells().createEnumeration()
            while enum.hasMoreElements():
                cell = enum.nextElement()
                address = cell.getCellAddress()
                places.append({'sheet': name, 'cell': '%s%d' % (_column(address.Column), address.Row + 1), **_cell_view(cell)})
        return {'kind': 'calc', 'places': places}
    raise ValueError('neither a Writer document nor a Calc spreadsheet')


def replace(args):
    doc = _doc(args)
    if _kind(doc) != 'writer':
        raise ValueError('a passage is replaced in a Writer document')
    ranges = _writer_found(doc, args['find'])
    expect = int(args.get('expect') or 1)
    before = [_paragraph_of(r) for r in ranges]
    if len(ranges) != expect:
        return {'replaced': 0, 'found': len(ranges), 'paragraphs': before}
    for found in ranges:
        found.setString(args['replace'])
    after = [_paragraph_of(r) for r in ranges]
    return {'replaced': len(ranges), 'found': len(ranges), 'paragraphs': before, 'now': after,
            'modified': bool(doc.isModified())}


def set_cell(args):
    doc = _doc(args)
    if _kind(doc) != 'calc':
        raise ValueError('a cell is set in a Calc spreadsheet')
    sheet = _sheet(doc, args.get('sheet'))
    cell = sheet.getCellRangeByName(args['cell']).getCellByPosition(0, 0)
    was = _cell_view(cell)
    if was['type'] == 'formula':
        return {'set': False, 'was': was, 'why': 'it holds a formula'}
    if args.get('kind') == 'number':
        cell.setFormula(args['value'])
        if cell.getType().value != 'VALUE':
            cell.setFormula(was['formula'] if was['type'] != 'empty' else '')
            return {'set': False, 'was': was, 'why': 'LibreOffice did not take "%s" as a number' % args['value'][:40]}
    else:
        cell.setString(args['value'])
    try:
        doc.calculateAll()
    except Exception:  # noqa: BLE001 - a sheet that cannot be recalculated whole recalculates itself as it goes
        pass
    return {'set': True, 'was': was, 'now': _cell_view(cell), 'sheet': sheet.getName(), 'modified': bool(doc.isModified())}


def store(args):
    doc = _doc(args)
    doc.store()
    return {'stored': True, 'modified': bool(doc.isModified())}


def close(args):
    doc = DOCS.pop(args.get('doc'), None)
    if doc is None:
        return {'closed': False}
    try:
        doc.close(True)
    except Exception:  # noqa: BLE001 - a document that will not close is disposed of
        doc.dispose()
    return {'closed': True}


def terminate(args):
    for handle in list(DOCS):
        try:
            close({'doc': handle})
        except Exception:  # noqa: BLE001
            pass
    desktop = STATE['desktop']
    ended = False
    if desktop is not None:
        try:
            ended = bool(desktop.terminate())
        except Exception:  # noqa: BLE001 - the bridge goes away as LibreOffice ends
            ended = True
    return {'terminated': ended}


HANDLERS = {'connect': connect, 'open': open_document, 'blocks': blocks, 'cells': cells, 'find': find, 'replace': replace,
            'set_cell': set_cell, 'store': store, 'close': close, 'terminate': terminate}


def main():
    # The answers go out on a private copy of stdout; anything else written to stdout (a library's notice) goes to stderr.
    channel = os.fdopen(os.dup(1), 'w', encoding='utf-8')
    os.dup2(2, 1)

    def answer(value):
        channel.write(json.dumps(value, ensure_ascii=False) + '\n')
        channel.flush()

    try:
        import uno  # noqa: F401
    except Exception as exc:  # noqa: BLE001 - the reason is the answer
        answer({'ok': False, 'error': 'NO_UNO: this Python cannot import LibreOffice\'s uno module (%s)' % _why(exc)})
        return 2
    answer({'ok': True, 'hello': {'python': sys.version.split()[0], 'executable': sys.executable, 'pid': os.getpid()}})
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        ident = None
        request = {}
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                request = {}
                raise ValueError('a request is an object')
            ident = request.get('id')
            handler = HANDLERS.get(request.get('op'))
            if handler is None:
                raise ValueError('unknown request')
            answer({'id': ident, 'ok': True, 'result': handler(request.get('args') or {})})
        except Exception as exc:  # noqa: BLE001 - every failure is an answer with its reason
            answer({'id': ident, 'ok': False, 'error': _why(exc)})
        if request.get('op') == 'terminate':
            break
    return 0


if __name__ == '__main__':
    sys.exit(main())
