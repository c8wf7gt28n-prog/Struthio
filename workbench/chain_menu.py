"""The chain menu: right-click builds a staC pipeline, one link per menu, Fluxbox-style.

It starts from what is under the pointer (a file in Files, or the root menu on an empty place). Each submenu adds one link
(a lens, where, sort, group and total, add a column, join or missing, take) and offers only what the data allows: real
column names, values found in them, the tables in Files. Every item says what it would give ("2 rows"): a pipeline only
reads, so the menu can look before you choose. The pipeline so far is the menu's top line.

A chain ends with "then": show it in the console, save as a sheet, watch it, add it to the Agenda, or keep it. Kept chains
go to a plain text file, ~/Concern/Ledger menu, which you may edit like ~/.fluxbox/menu:

    # comments start with #
    [chain] (Short parts) {@files:stock.csv | rows | add Short = Need - Have | where Short over 0} then sheet
    [submenu] (Bring-up)
      [chain] (Rev C headings) {@files:Rev C notes.md | headings}
    [end]
    [separator]

The file is read, never run: each chain must parse as staC (the same shell guard applies) or it is shown greyed with the
reason. Every submenu can be torn off and left open while you look at things.

HATCH DESK D4: the chain menu is one provider of the right-click menu (workbench/context_menu.py): on a file, "Chain from here"
opens this builder beside its row; on an empty place, "Your chains" lists the menu file's chains and "Start a chain from" the
files to read. The Menu key and Shift+F10 open the right-click menu for what has the keyboard focus (install); Ctrl+Shift+Space
and Tools ▸ Chain Menu still open this builder alone (open_here). Its menus wear the desk's menu numbers (desk_style).
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from uuid import uuid4
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QInputDialog, QMenu

LENS_ORDER = ('rows', 'headings', 'layers', 'texts', 'lines', 'facts')
THEN = (('console', 'show it in the console'), ('sheet', 'save as a sheet'), ('watch', 'watch it'), ('agenda', 'add to the Agenda'))
VALUES = 8
TABLE_KINDS = ('csv', 'spreadsheet')
MENU_FILE = 'Ledger menu'
LINE = re.compile(r'^\[(chain|stock|shell|submenu|end|separator)\]\s*(?:\(([^)]*)\))?\s*(?:\{(.*)\})?\s*(?:then\s+(\w+))?\s*$')
STOCK_METHOD = 'graphite.stock-shortage-method/1'
STOCK_ROLES = ('part', 'required', 'available', 'unit')


# -- reading data ------------------------------------------------------------------------

def run(host, program):
    """Rows for a pipeline, or (None, reason). Read-only: language.run allows read operations only."""
    from .shell2 import call_write
    r = call_write(host, 'language.run', {'text': program})
    if not r.get('ok'):return None, (r.get('error') or {}).get('message', 'did not run')
    return r['result'].get('rows') or [], None


def records(rows):
    return bool(rows) and all(isinstance(r, dict) for r in rows[:20])


def fields_of(rows):
    return list(dict.fromkeys(k for r in rows[:50] if isinstance(r, dict) for k in r))


def numeric(values):
    found = [v for v in values if v not in ('', None)]
    return bool(found) and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in found)


def word(value):
    """A value as staC reads it: words with spaces in quotes."""
    text = str(value)
    return '"%s"' % text.replace('"', '') if re.search(r'\s|\|', text) else text


def rows_words(rows, error=None):
    if error is not None:return 'does not run'
    return '%d row%s' % (len(rows), '' if len(rows) == 1 else 's')


# -- the menu ------------------------------------------------------------------------------

def desk_style(menu, host):
    """The desk's menu numbers on a chain menu (programs_qt.metrics: the row height, the words' size, the margins, the paper and
    the pencil wash under the row in hand), so the builder reads like the right-click menu it opens from. Its submenus are its
    children and take the same sheet."""
    try:
        from .programs_qt import metrics
        from .shell2 import AMBER_EDGE, AMBER_SOFT, GROUND, LINE, MONO, QUIET, TEXT
        m = metrics(host)
    except Exception:return menu
    top = max(0, (m.row - m.line) // 2);bottom = max(0, m.row - m.line - top)
    menu.setStyleSheet('QMenu {background:%s;border:1px solid %s;padding:%dpx 0;font-family:"%s";font-size:%dpx;} '
                       'QMenu::item {padding:%dpx %dpx %dpx %dpx;color:%s;background:transparent;border:0;margin:0;} '
                       'QMenu::item:selected {background:%s;color:%s;} QMenu::item:disabled {color:%s;} '
                       'QMenu::separator {height:1px;background:%s;margin:%dpx %dpx;}'
                       % (GROUND, AMBER_EDGE, m.margin, MONO, m.px, top, m.pad, bottom, m.pad + m.icon_col, TEXT, AMBER_SOFT, TEXT, QUIET, LINE, m.rule // 2, m.pad))
    return menu


class Chain(QMenu):
    """One link of a chain. Its items are worked out when it opens, from the answer so far."""

    def __init__(self, host, program, title=None, parent=None):
        super().__init__(title or program, parent);self.host = host;self.program = program;self.filled = False
        self.setTearOffEnabled(True);self.setToolTipsVisible(True);self.aboutToShow.connect(self.fill)
        if not isinstance(parent, QMenu):desk_style(self, host)  # a submenu takes its parent's sheet

    def fill(self):
        if self.filled:return
        self.filled = True;fill(self, self.host, self.program)


def header(menu, program):
    from .shell2 import mono_font
    top = menu.addAction(program if len(program) < 90 else '…' + program[-88:]);top.setFont(mono_font(13));top.setEnabled(False)
    top.setToolTip('The chain so far. Everything before "then" only reads.')


def link(menu, host, program, label, rows=None, error=None, leaf=False):
    """An item that adds a link: a submenu that keeps building, or (leaf) an item that shows the answer in the console."""
    text = label + ('    ' + rows_words(rows, error) if rows is not None or error is not None else '')
    if error is not None:
        a = menu.addAction(text);a.setEnabled(False);a.setToolTip(str(error)[:200]);return a
    if leaf:
        a = menu.addAction(text);a.triggered.connect(lambda checked=False, p=program:then(host, p, 'console'));return a
    sub = Chain(host, program, text, menu);menu.addMenu(sub);return sub


def fill(menu, host, program):
    """Add the next links for `program` to `menu` (used by Chain and by the Files right-click menu)."""
    header(menu, program)
    from .chain_workbench_qt import stage
    menu.addAction('Build on the desk…').triggered.connect(lambda checked=False:stage(host, program))
    rows, error = run(host, program)
    if error is not None:
        a = menu.addAction('This chain does not run: ' + error[:80]);a.setEnabled(False);return
    if not records(rows) or (len(rows) == 1 and ('view' in rows[0] or 'address' in rows[0])):
        lenses(menu, host, program, rows)
    else:
        shape(menu, host, program, rows)
    menu.addSeparator()
    then_menu = QMenu('then', menu);then_menu.setTearOffEnabled(True)
    for key, label in THEN:then_menu.addAction(label).triggered.connect(lambda checked=False, k=key:then(host, program, k))
    shell = QMenu('shell', then_menu);then_menu.addMenu(shell)
    shell.aboutToShow.connect(lambda m=shell:m.isEmpty() and shell_endings(m, host, program))
    then_menu.addSeparator()
    then_menu.addAction('keep this chain…').triggered.connect(lambda checked=False:keep(host, program))
    then_menu.addAction('copy the line').triggered.connect(lambda checked=False:copy(host, program))
    menu.addMenu(then_menu)
    from .chain_icons import dress
    dress(menu)  # a small picture for each link: what it does, at a glance


def lenses(menu, host, program, rows):
    """What a file can be read as: sheets by name, rows, headings, layers… (only the ones that give something)."""
    offered = 0
    sheets, _ = run(host, program + ' | pick data.sheets')
    if sheets and isinstance(sheets[0], dict):
        for name in list(sheets[0])[:12]:
            p = program + ' | sheet ' + name;r, e = run(host, p)
            if e is None and r:link(menu, host, p, 'sheet ' + name, r);offered += 1
    for lens in LENS_ORDER:
        if offered and lens == 'facts':menu.addSeparator()
        p = program + ' | ' + lens;r, e = run(host, p)
        if e is None and records(r):link(menu, host, p, lens, r);offered += 1
    if not offered:
        a = menu.addAction('Nothing to read as rows here');a.setEnabled(False)


def shape(menu, host, program, rows):
    fields = fields_of(rows)
    where = QMenu('where', menu);where.setTearOffEnabled(True);menu.addMenu(where)
    where.aboutToShow.connect(lambda m=where:m.isEmpty() and where_fields(m, host, program, rows, fields))
    sort = QMenu('sort', menu);sort.setTearOffEnabled(True);menu.addMenu(sort)
    for f in fields[:24]:
        part = QMenu(f, sort)
        link(part, host, program + ' | sort ' + f, 'smallest first');link(part, host, program + ' | sort -' + f, 'largest first')
        sort.addMenu(part)
    group = QMenu('group by', menu);group.setTearOffEnabled(True);menu.addMenu(group)
    numbers = [f for f in fields if numeric([r.get(f) for r in rows[:200] if isinstance(r, dict)])]
    for f in fields[:24]:
        part = QMenu(f, group);base = program + ' | group ' + f
        link(part, host, base + ' | count', 'count')
        for n in numbers[:8]:
            if n == f:continue
            for how in ('sum', 'avg', 'min', 'max'):link(part, host, base + ' | %s %s' % (how, n), '%s %s' % (how, n))
        group.addMenu(part)
    keep_only = QMenu('select', menu);keep_only.setTearOffEnabled(True);menu.addMenu(keep_only)
    for f in fields[:24]:link(keep_only, host, program + ' | select ' + f, 'only ' + f)
    keep_only.addSeparator();keep_only.addAction('choose columns…').triggered.connect(lambda checked=False:choose_columns(host, program, fields))
    menu.addAction('add a column…').triggered.connect(lambda checked=False:add_column(host, program, numbers))
    joins = QMenu('join with', menu);joins.setTearOffEnabled(True);menu.addMenu(joins)
    joins.aboutToShow.connect(lambda m=joins:m.isEmpty() and join_tables(m, host, program, fields))
    take = QMenu('take', menu)
    for n in (5, 10, 20):link(take, host, program + ' | take %d' % n, 'first %d' % n)
    menu.addMenu(take)
    r, e = run(host, program + ' | count');link(menu, host, program + ' | count', 'count', r, e, leaf=True)


def where_fields(menu, host, program, rows, fields):
    for f in fields[:24]:
        values = [r.get(f) for r in rows[:500] if isinstance(r, dict)]
        part = QMenu(f, menu);part.setTearOffEnabled(True);menu.addMenu(part)
        part.aboutToShow.connect(lambda m=part, f=f, v=values:m.isEmpty() and where_values(m, host, program, f, v))


def where_values(menu, host, program, field, values):
    """Comparisons that fit the column, with values found in it. Each says how many rows it keeps."""
    if numeric(values):
        found = sorted({v for v in values if isinstance(v, (int, float))})
        shown = min(VALUES, len(found))  # spread across the values found, smallest to largest
        picks = sorted({found[round(i * (len(found) - 1) / max(1, shown - 1))] for i in range(shown)}) if found else []
        for word_ in ('over', 'under', 'at least', 'at most'):
            part = QMenu(word_, menu)
            for v in picks:
                p = '%s | where %s %s %s' % (program, field, word_, v);r, e = run(host, p);link(part, host, p, str(v), r, e)
            menu.addMenu(part)
        return
    counts = {}
    for v in values:
        if v not in ('', None):counts[str(v)] = counts.get(str(v), 0) + 1
    common = sorted(counts, key=lambda k:-counts[k])[:VALUES]
    for word_ in ('is', 'is not', 'has'):
        part = QMenu(word_, menu)
        for v in common:
            text = v if word_ != 'has' else v[:12]
            p = '%s | where %s %s %s' % (program, field, '=' if word_ == 'is' else word_, word(text));r, e = run(host, p);link(part, host, p, text, r, e)
        menu.addMenu(part)


def join_tables(menu, host, program, fields):
    """Other tables in Files, joined on a column both share: join keeps matches, missing keeps what has none."""
    from .shell2 import call
    found = [e for e in (call(host, 'files.find', {'limit': 60}) or {}).get('records', []) if e.get('kind') in TABLE_KINDS]
    here = program.split('|')[0].strip()
    for e in found[:16]:
        source = '@files:' + e['path']
        if source == here or re.search(r'\s', e['path']):continue  # a joined source is one word
        candidates = [source + ' rows'] if e['kind'] == 'csv' else []
        if e['kind'] == 'spreadsheet':
            sheets, _ = run(host, source + ' | pick data.sheets')
            candidates = [source + ' sheet ' + n for n in (list(sheets[0]) if sheets and isinstance(sheets[0], dict) else [])[:4] if not re.search(r'\s', n)]
        for other in candidates:
            theirs, err = run(host, other.replace(' rows', ' | rows').replace(' sheet ', ' | sheet ', 1))
            shared = [f for f in fields if f in fields_of(theirs or [])] if err is None else []
            if not shared:continue
            part = QMenu(other.replace('@files:', ''), menu)
            for f in shared[:6]:
                p = '%s | join %s on %s' % (program, other, f);r, e2 = run(host, p);link(part, host, p, 'join on ' + f, r, e2)
                p = '%s | missing %s on %s' % (program, other, f);r, e2 = run(host, p);link(part, host, p, 'missing on ' + f, r, e2)
            menu.addMenu(part)
    if menu.isEmpty():
        a = menu.addAction('No other table in Files shares a column');a.setEnabled(False)


def choose_columns(host, program, fields):
    text, ok = QInputDialog.getText(host, 'Choose columns', 'Columns, separated by commas:', text=','.join(fields[:4]))
    if ok and text.strip():then(host, program + ' | select ' + ','.join(f.strip() for f in text.split(',') if f.strip()), 'console')


def add_column(host, program, numbers):
    hint = (' (numbers: ' + ', '.join(numbers[:6]) + ')') if numbers else ''
    text, ok = QInputDialog.getText(host, 'Add a column', 'Name = arithmetic with + - * / and brackets' + hint + ':',
                                    text=('Short = %s - %s' % tuple(numbers[:2])) if len(numbers) >= 2 else '')
    if ok and '=' in text:then(host, program + ' | add ' + text.strip(), 'console')


# -- endings ---------------------------------------------------------------------------------

def then(host, program, how):
    face = host.shell2.face
    if how == 'console':
        from .chain_workbench_qt import stage
        stage(host, program)
        console = host.console;console.set_mode('stac');console.open();console.run_stac(program);return
    if how == 'sheet':
        rows, error = run(host, program)
        if error is not None:host.statusBar().showMessage('Not saved: ' + error, 7000);return
        face.save_rows(program, rows);return
    if how == 'watch':face.watch(program);return
    if how == 'agenda':face.keep_in_agenda(program);return


def shell_lines():
    path = menu_path()
    if not path.is_file():return []
    tree, _ = parse_menu(path.read_text(encoding='utf-8', errors='replace'))
    out = []
    def walk(items):
        for item in items:
            if item[0] == 'shell':out.append(item[1:])
            elif item[0] == 'submenu':walk(item[2])
    walk(tree);return out


def shell_endings(menu, host, program):
    """The one place a chain leaves Ledger: your own command, on the console's Shell page, with the answer as a CSV file
    named in $LEDGER_ANSWER. It is always the last step, it is shown before it runs, and Stop ends it."""
    for name, command in shell_lines():
        a = menu.addAction(name);a.setToolTip(command);a.triggered.connect(lambda checked=False, c=command:to_shell(host, program, c))
    if shell_lines():menu.addSeparator()
    menu.addAction('type a command…').triggered.connect(lambda checked=False:typed_shell(host, program))
    a = menu.addAction('keep commands in your Graphite menu: [shell] (Name) {command}');a.setEnabled(False)


def typed_shell(host, program):
    command, ok = QInputDialog.getText(host, 'then shell', 'A command for your shell. The answer is a CSV file named in $LEDGER_ANSWER:',
                                       text='column -s, -t < "$LEDGER_ANSWER"')
    if ok and command.strip():to_shell(host, program, command.strip())


def to_shell(host, program, command):
    from .shell2 import call_write
    from .files_service import as_csv
    rows, error = run(host, program)
    if error is not None:host.statusBar().showMessage('Not run: ' + error, 7000);return
    r = call_write(host, 'files.write', {'path': 'Slate/answer for the shell.csv', 'text': as_csv(rows)})
    if not r.get('ok'):host.statusBar().showMessage((r.get('error') or {}).get('message', 'Could not write the answer'), 7000);return
    from .shell2 import call
    root = (call(host, 'files.list', {}) or {}).get('root', '')
    answer = str(Path(root) / 'Slate' / 'answer for the shell.csv')
    console = host.console;console.set_mode('shell');console.open()
    console.say('<span style="color:#6c675e;">from the chain: %s · the answer (%d rows) is in $LEDGER_ANSWER</span>' % (program.replace('<', '&lt;'), len(rows)))
    console.run_shell(command, {'LEDGER_ANSWER': answer})


def copy(host, program):
    from PySide6.QtWidgets import QApplication
    QApplication.clipboard().setText(program);host.statusBar().showMessage('Copied: ' + program[:120], 5000)


def menu_path():
    from . import locations
    return locations.concern_home() / MENU_FILE


def keep(host, program, then_word='console', *, stock_unit=None, stock_basis=None):
    title = 'Keep shortage method' if stock_unit is not None else 'Keep this chain'
    name, ok = QInputDialog.getText(host, title, 'A name for it in your Graphite menu:')
    if not ok or not name.strip():return
    path = menu_path();path.parent.mkdir(parents=True, exist_ok=True)
    name = name.strip().replace(')', '')
    if not name:return
    stock = stock_unit
    if stock_basis is not None:
        stock = dict(schema=STOCK_METHOD, id=uuid4().hex, unit=stock_unit, **stock_basis)
    entry = ('[stock] (%s) {%s}\n' % (name, json.dumps(stock)) if stock_unit is not None
             else '[chain] (%s) {%s} then %s\n' % (name, program, then_word))
    with path.open('a', encoding='utf-8') as f:
        f.write((TEMPLATE if f.tell() == 0 else '') + entry)
    host.statusBar().showMessage('Kept in %s. It is plain text: edit it to arrange your menu.' % str(path).replace(str(Path.home()), '~'), 8000)


TEMPLATE = """# Your Graphite menu: chains you keep, shown at the top of the chain menu.
# One chain per line; [submenu] (Name) … [end] groups them; [separator] draws a line.
#   [chain] (Name) {a line} then console|sheet|watch|agenda
#   [stock] (Name) {"pcs"}   a shortage method for selected rows with this exact unit
# Methods kept from a worksheet also record their original source revision and column bindings.
# Graphite reads this file and never runs it: every chain must parse as a line, or it is shown greyed.
#   [shell] (Name) {command}   your own command, offered under then › shell; the answer is a CSV file in $LEDGER_ANSWER
"""


def parse_menu(text):
    """The Ledger menu file as a tree: [('chain', name, program, then) | ('separator',) | ('submenu', name, [...])], plus problems."""
    root = [];stack = [root];problems = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):continue
        m = LINE.match(line)
        if not m:problems.append((number, 'not understood'));continue
        kind, name, program, how = m.groups()
        if kind == 'chain':
            if not name or not program:problems.append((number, 'a chain needs (name) and {line}'));continue
            stack[-1].append(('chain', name.strip(), program.strip(), how if how in dict(THEN) else 'console'))
        elif kind == 'stock':
            try:
                unit, method = parse_stock(json.loads(program or ''))
                if not name or not name.strip():raise ValueError('a stock method needs a name')
            except ValueError as exc:
                problems.append((number, str(exc)));continue
            stack[-1].append(('stock', name.strip(), unit, method))
        elif kind == 'shell':
            if not name or not program:problems.append((number, 'a shell line needs (name) and {command}'));continue
            stack[-1].append(('shell', name.strip(), program.strip()))
        elif kind == 'separator':stack[-1].append(('separator',))
        elif kind == 'submenu':
            items = [];stack[-1].append(('submenu', (name or 'More').strip(), items));stack.append(items)
        elif kind == 'end':
            if len(stack) > 1:stack.pop()
            else:problems.append((number, '[end] without [submenu]'))
    return root, problems


def parse_stock(value):
    if isinstance(value, str) and value.strip() and len(value) <= 80:
        return value, None
    if not isinstance(value, dict) or set(value) != {'schema', 'id', 'unit', 'columns', 'source'}:
        raise ValueError('a stock method needs a unit string or a saved method record')
    unit, columns, source = value['unit'], value['columns'], value['source']
    if (value['schema'] != STOCK_METHOD or not isinstance(value['id'], str)
            or not re.fullmatch(r'[0-9a-f]{32}', value['id'])
            or not isinstance(unit, str) or not unit.strip() or len(unit) > 80
            or not isinstance(columns, dict) or set(columns) != set(STOCK_ROLES)
            or any(not isinstance(name, str) or name.casefold() != role for role, name in columns.items())):
        raise ValueError('invalid saved stock method')
    if (not isinstance(source, dict) or set(source) != {'path', 'sha256', 'sheet', 'rows'}
            or not isinstance(source['path'], str) or not source['path']
            or not isinstance(source['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', source['sha256'])
            or source['sheet'] is not None and not isinstance(source['sheet'], str)
            or not isinstance(source['rows'], list) or not 1 <= len(source['rows']) <= 200
            or any(type(row) is not int or row < 1 for row in source['rows'])):
        raise ValueError('invalid saved stock method source')
    return unit, value


def stock_methods(*, details=False):
    try:tree, _ = parse_menu(menu_path().read_text(encoding='utf-8', errors='replace'))
    except OSError:return []
    found = []
    def walk(items):
        for item in items:
            if item[0] == 'stock':found.append(item[1:] if details else item[1:3])
            elif item[0] == 'submenu':walk(item[2])
    walk(tree)
    return found


def method_runs(method):
    return 'Slate/Chains/Methods/' + method['id']


def my_chains(menu, host):
    path = menu_path()
    if not path.is_file():
        a = menu.addAction('No kept chains yet: end a chain with then › keep this chain…');a.setEnabled(False);return
    tree, problems = parse_menu(path.read_text(encoding='utf-8', errors='replace'))
    from .stacy_language import source
    from sdk.cli.arc1cli import typed_pipeline
    def build(target, items):
        for item in items:
            if item[0] in ('shell', 'stock'):continue
            if item[0] == 'separator':target.addSeparator()
            elif item[0] == 'submenu':
                sub = QMenu(item[1], target);sub.setTearOffEnabled(True);build(sub, item[2]);target.addMenu(sub)
            else:
                _, name, program, how = item
                try:typed_pipeline.parse(source(program)[0]);a = target.addAction(name)
                except ValueError as exc:a = target.addAction(name + '  (does not parse)');a.setEnabled(False);a.setToolTip(str(exc)[:200]);continue
                a.setToolTip(program);a.triggered.connect(lambda checked=False, p=program, h=how:then(host, p, h))
                from .chain_icons import icon as _icon
                a.setIcon(_icon('chain'))  # a chain you kept
    build(menu, tree)
    if problems:
        a = menu.addAction('%d line%s in the menu file not understood' % (len(problems), '' if len(problems) == 1 else 's'));a.setEnabled(False)
        a.setToolTip('\n'.join('line %d: %s' % p for p in problems[:10]))


def root_menu(host, parent=None):
    """The menu on an empty place: your kept chains, then where a chain can start."""
    from .shell2 import call
    menu = QMenu(parent or host);menu.setTearOffEnabled(True)
    menu.addAction('Inquiries…').triggered.connect(lambda checked=False:host.ledger_bridge.show_discovery())
    menu.addAction('Algorithm && Theory Atlas…').triggered.connect(lambda checked=False:host.ledger_bridge.show_algorithms())
    menu.addAction('Tool Atlas…').triggered.connect(lambda checked=False:host.ledger_bridge.show_atlas())
    my_chains(menu, host)
    menu.addSeparator()
    start = QMenu('start from', menu);start.setTearOffEnabled(True);menu.addMenu(start)
    def fill_start(m=start):
        if not m.isEmpty():return
        found = [e for e in (call(host, 'files.find', {'limit': 80}) or {}).get('records', [])
                 if e.get('kind') in TABLE_KINDS + ('markdown', 'dxf', 'stl', 'obj', '3mf', 'text', 'json')]
        for e in found[:30]:m.addMenu(Chain(host, '@files:' + e['path'], e['path'], m))
        if m.isEmpty():
            a = m.addAction('Nothing in Files to read yet');a.setEnabled(False)
    start.aboutToShow.connect(fill_start)
    console = QMenu('writing line', menu)  # HATCH DESK D3/D4: the line's four modes (the old console pages map to them)
    for mode, label in (('slate', 'Assignment'), ('shell', 'Shell'), ('find', 'Search'), ('log', 'Log')):
        console.addAction(label).triggered.connect(lambda checked=False, m=mode:writing_line(host, m))
    menu.addMenu(console)
    menu.addSeparator()
    menu.addAction('edit the Graphite menu…').triggered.connect(lambda checked=False:edit_menu_file(host))
    from .chain_icons import dress
    dress(menu);desk_style(menu, host)
    return menu


def writing_line(host, mode):
    """A mode of the writing line, the working area open (the root menu's old console pages)."""
    bar = getattr(host, 'type_bar', None)
    if bar is None:return host.console.open({'slate': 'stac'}.get(mode, mode))
    bar.set_target(mode, focus=True)
    if host.console.size_level == 0:host.console.set_size(1)
    return bar


def edit_menu_file(host):
    path = menu_path()
    if not path.exists():path.parent.mkdir(parents=True, exist_ok=True);path.write_text(TEMPLATE, encoding='utf-8')
    host.open_document(path)


def open_here(host, pos=None):
    """The Menu key, or Tools › Chain Menu: a chain from what is selected, or the root menu."""
    tab = host.tabs.currentWidget()
    start = tab.chain_start() if hasattr(tab, 'chain_start') else None
    if start:
        menu = QMenu(host);menu.setTearOffEnabled(True);desk_style(menu, host);fill(menu, host, start)
    else:menu = root_menu(host)
    menu.popup(pos or QCursor.pos());return menu


def install(host):
    """HATCH DESK D4: the Menu key and Shift+F10 open the right-click menu for what has the keyboard focus (context_menu.install:
    the router and the two keys); Ctrl+Shift+Space opens the chain builder alone, as before."""
    from PySide6.QtGui import QKeySequence, QShortcut
    from .context_menu import install as install_context
    install_context(host)
    QShortcut(QKeySequence('Ctrl+Shift+Space'), host, activated=lambda:open_here(host))
