"""Graphite 1.1 B2 · The line finds and does: what a line typed on the bar (or in Start) offers, each row saying what Enter
will do. No Qt here; start_qt draws the rows and does what the chosen one says.

PLAN_1.1.md, B2; the design direction's section 1 (Calm's graft: "the line on the bar finds and does everything, and every
row says what Enter will do"); the proposal "Familiar", section 6. It reuses 1.0's line machinery and adds no rule of its own:

  a sum                12*7, = 1/3 + 1/6, 2 × 3.5: the one maths core (math_model, exact fractions, no float); the answer is
                       exact (its decimal when that ends, else four figures with the exact fraction beside)    Calculate
  an address           https://..., www..., localhost:8080 (typebar_qt's reading, as the foot's Web)            Open
  DOS words            dir, ipconfig, copy a b (W1's dos_words): run in the Terminal, the Debian command beside  Run
  apps                 the apps' own desktop entries (apps_catalog, as 1.0's Apps reads them), every word starting
                       a word of the name, the generic name, the keywords or the program; a Windows word finds
                       its Debian app with the Windows word beside ("notepad" -> Text Editor · Notepad in Windows) Open
  settings             Graphite's settings by label or key (console_qt.setting_rows, Search's own match)          Open
  files                recent files (Graphite's and the desktop's recently-used list), then your home by name
                       (search_reach.home_names, the walk with a budget)                                         Open
  the desk             the cabinet's records and the desk's objects by every word (search_reach.records)          Open
  commands             Graphite's places and the window's own commands by their words (shell2's OneBox.commands)  Run / Open
  operations by name   /files.list, or a name with a dot (apps.list): the Kernel's operation, on the operations
                       page, an approve-scope one asking there for a second press (1.0's / lines)                Run
  a Graphite line      @files: | count, this | ...: run on the line page as the foot runs it (foot_line)           Run
  a program            a first word that is a program on this computer: run in the Terminal                      Run
  Ask Kasandra         always the last row: the words into her column's ask line (foot_line.ask_kasandra), where
                       she plans or answers; she changes nothing without the owner's press                       Ask Kasandra

Leads, for sure hands: = a sum (or a Graphite line), ? Kasandra, $ or > the Terminal, / an operation or a place, @ a line.

Enter takes the first row. Ask Kasandra is first only when the words read as a request to her (a question, K4's objective
reading, a '?' lead) or nothing else was found; otherwise it is the last row, chosen. Nothing is done by typing: only the
owner's Enter or press on a row does what that row says.
"""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

ASK = 'Ask Kasandra'
VERBS = ('Open', 'Run', 'Calculate', ASK, 'Explain', 'Edit', 'Show')      # 1.1 KS1: Show (a recipe: what it would do, nothing changes)
SECTIONS = ('APPS', 'SETTINGS', 'FILES', 'DESK', 'COMMANDS')
MOST = dict(APPS=6, SETTINGS=4, FILES=6, DESK=4, COMMANDS=5)
QUESTION = re.compile(r"^(what|whats|what's|how|why|when|who|where|which|can|could|should|would|will|is|are|was|were|do|does|did|"
                      r"please|tell|explain|help|show me|find out|remind|summarise|summarize|compare|write|draft|plan)\b", re.I)
SUM = re.compile(r'^[\d\s.+\-*/()×÷·^]+$')
OPERATOR = re.compile(r'\d\s*[)]*\s*[+\-*/×÷·^]+\s*[(]*\s*[\d.]')
OPERATION = re.compile(r'^/?([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)(?:\s+(.*))?$')
SHOW = 56                      # a title's longest words before they are shortened

# Windows words: what a Windows hand types, what it finds here, and the Windows word shown beside the match.
#   ('apps', words)     the apps that hold every word of one of these ('a|b c': a, or b and c); the first two are offered
#   ('do', verb)        one of graphite-do's words (windows_keys_qt.act): files, tasks
#   ('settings', '')    Graphite's settings
#   ('terminal', '')    the Terminal (Graphite's console, its shell page; DOS words work there)
#   ('explain', words)  said, not done
WINDOWS = (
    (('control panel', 'control', 'settings', 'system settings', 'pc settings'), 'settings', '', 'Control Panel in Windows'),
    (('cmd', 'command prompt', 'powershell', 'dos', 'terminal', 'console'), 'terminal', '', 'cmd in Windows'),
    (('notepad', 'wordpad'), 'apps', 'text editor|word processor', 'Notepad in Windows'),
    (('paint', 'mspaint'), 'apps', 'paint|drawing|image editor|raster', 'Paint in Windows'),
    (('calc', 'calculator'), 'apps', 'calculator', 'Calculator in Windows'),
    (('explorer', 'file explorer', 'my computer', 'this pc', 'windows explorer'), 'do', 'files', 'File Explorer in Windows'),
    (('task manager', 'taskmgr'), 'do', 'tasks', 'Task Manager in Windows'),
    (('regedit', 'registry', 'registry editor'), 'explain', 'There is no registry here: settings are plain files, most of them in '
                                                            'the hidden folder .config in your home. Graphite\'s own are in Settings.',
     'Registry Editor in Windows'),
)
WINDOWS_TITLES = {'settings': 'Settings', 'terminal': 'Terminal', 'files': 'Files', 'tasks': 'What runs'}


@dataclass
class Row:
    """One row under the line. verb: what Enter (or a press) does with it; target: what the doer needs (an app's id, a path, a
    setting's key, a command, the words); beside: the other name shown beside it (the Debian command beside a DOS word, the
    Windows word beside what it found here)."""
    kind: str
    title: str
    detail: str = ''
    verb: str = 'Open'
    target: object = None
    beside: str = ''
    section: str = ''
    tip: str = ''
    icon: str = ''
    extra: dict = field(default_factory=dict)

    def enter_words(self):
        """What Enter does on this row, in words: "Enter: Open Firefox"."""
        name = self.title if len(self.title) <= 40 else self.title[:38] + '…'
        if self.kind == 'sum':return 'Enter: Calculate · puts %s in the line and copies it' % self.extra.get('answer', '')
        if self.kind == 'ask':return 'Enter: Ask Kasandra · in her column; she proposes, you decide'
        if self.extra.get('recipe'):return self.detail.replace('Enter ', 'Enter: ', 1)      # 1.1 KS1: a recipe's row shows what it would do
        return 'Enter: %s %s' % (self.verb, name)


def clean(text):
    return str(text or '').replace('​', '').strip()


def short(text, most=SHOW):
    text = str(text);return text if len(text) <= most else text[:most - 1] + '…'


def home_words(path):
    """A path as the owner reads it: ~ for the home."""
    text = str(path);home = str(Path.home())
    return '~' + text[len(home):] if text == home or text.startswith(home + os.sep) else text


# ---- a sum ------------------------------------------------------------------------------------------------------------------------
def sum_of(text):
    """(the expression as asked, the exact answer in words, the answer's record) for a sum, or None. The one maths core answers
    it (math_model: exact fractions, no float); 'x' and '×' are times, '÷' divides, '^' raises."""
    words = clean(text)
    led = words.startswith('=')
    if led:words = words[1:].strip()
    words = re.sub(r'(?<=[\d)])\s*[xX]\s*(?=[\d(])', ' × ', words)      # 2 x 3: times, as a Windows hand writes it
    if not words or not SUM.match(words) or not (OPERATOR.search(words) or led):return None
    expression = words.replace('×', '*').replace('·', '*').replace('÷', '/').replace('^', '**')
    try:
        from fractions import Fraction
        from . import math_answers, math_model
        ir = math_model.compile_expression(expression, {})
        result = math_model.evaluate(ir)
        value = (result.get('outputs') or [{}])[0].get('value') or {}
        if result.get('state') != 'FEASIBLE' or 'rational' not in value:return ('refused', words, result.get('reason') or 'no answer')
        exact = Fraction(value['rational'])
        said = math_answers.exactly(exact, '1') if value.get('decimal_exact') else math_answers.figure(exact, '1')
        plain = math_answers.exactly(exact, '1') if value.get('decimal_exact') else value['rational']
        return (words, said, dict(value, plain=plain))
    except (ValueError, ZeroDivisionError, ArithmeticError) as exc:
        return ('refused', words, str(exc) or type(exc).__name__)


def sum_rows(text):
    found = sum_of(text)
    if found is None:return []
    if found[0] == 'refused':
        if not clean(text).startswith('='):return []
        return [Row('explain', 'Not a sum the maths can answer: %s' % short(found[1], 40), str(found[2])[:120], 'Edit', clean(text),
                    tip='The one maths core takes + - * / ( ), small whole powers and exact decimals.', icon='sum')]
    asked, said, value = found
    asked = re.sub(r'\s*[*×·]\s*', ' × ', asked.replace('**', '^'))      # 12*7 shown as 12 × 7
    return [Row('sum', '%s = %s' % (short(asked, 40), said), 'Exact, by the one maths core', 'Calculate', value['plain'],
                tip='Enter puts %s in the line and copies it.' % value['plain'], icon='sum', extra=dict(answer=value['plain'], rational=value['rational']))]


# ---- an address, DOS words, a program, an operation, a Graphite line ---------------------------------------------------------------
def is_address(text):
    words = clean(text)
    if not words or ' ' in words:return False
    try:
        from .typebar_qt import TypeBar
        return bool(TypeBar.plain_address(words))
    except Exception:  # noqa: BLE001 - the plain reading below
        return bool(re.match(r'^(https?://\S+|www\.\S+\.\S+|localhost(:\d+)?(/\S*)?)$', words, re.I))


def address_rows(text):
    words = clean(text)
    if not is_address(words):return []
    return [Row('address', 'Open %s' % short(words), "In this computer's own browser", 'Open', words, icon='address')]


def dos_rows(text, cwd=None):
    """DOS words: run in the Terminal, the Debian command beside; format, chkdsk, fdisk and diskpart are explained, never run."""
    from . import dos_words
    words = clean(text).lstrip('$>').strip()
    try:said = dos_words.translate(words, cwd=cwd or str(Path.home()))
    except Exception:  # noqa: BLE001 - not read as DOS words
        said = None
    if said is None:return []
    if said.kind == 'explain':
        return [Row('dos', '%s is explained in the Terminal, never run' % short(words, 30), short(said.words or 'DOS words never run it', 120),
                    'Explain', words, 'explained, not run', icon='terminal')]
    debian = said.command or {'cd': 'cd', 'cls': 'clear', 'trash': 'gio trash', 'env': 'export', 'help': 'help', 'exit': 'exit'}.get(said.kind, said.kind)
    return [Row('dos', 'Run %s in the Terminal' % short(words, 40), 'DOS words · Debian runs: %s' % short(debian, 60), 'Run', words,
                debian, tip=said.shown(), icon='terminal')]


def program_of(text, which=shutil.which):
    first = clean(text).lstrip('$>').strip().split(' ', 1)[0]
    if not first or '/' in first and not first.startswith(('/', './', '~/')):return ''
    try:return first if which(os.path.expanduser(first)) else ''
    except (OSError, ValueError):return ''


def terminal_rows(text, which=shutil.which, led=False):
    words = clean(text).lstrip('$>').strip()
    if not words or (not led and not program_of(words, which)):return []
    return [Row('terminal', 'Run %s in the Terminal' % short(words, 40), 'A command of this computer, in Graphite\'s Terminal', 'Run', words, icon='terminal')]


def operation_rows(text):
    """An operation of the Kernel by its name (/files.list path=Slate, or apps.list): run on the operations page as 1.0's /
    lines run (an approve-scope one asks there for a second press)."""
    words = clean(text)
    found = OPERATION.match(words)
    if not found:return []
    try:from .engineering_kernel import CAPABILITIES
    except Exception:  # noqa: BLE001
        return []
    name = found.group(1)
    names = [name] if name in CAPABILITIES else ([n for n in sorted(CAPABILITIES) if n.startswith(name)][:3] if words.startswith('/') else [])
    rows = []
    for n in names:
        line = '/' + n + ((' ' + found.group(2)) if found.group(2) and n == name else '')
        scope = CAPABILITIES[n]
        rows.append(Row('operation', 'Run the operation %s' % short(line.lstrip('/'), 44), 'An operation of Graphite\'s Kernel · %s' % SCOPE_WORDS.get(scope, scope),
                        'Run', line, section='COMMANDS', icon='command',
                        tip='On the operations page; one that needs your approval asks there for a second press.'))
    return rows


SCOPE_WORDS = {'read': 'it reads', 'execute': 'it does', 'approve': 'it asks for your approval', 'admin': 'for the administrator'}


def line_rows(text, reading=''):
    words = clean(text)
    if reading != 'line' and not words.startswith('@'):return []
    return [Row('line', 'Run the line %s' % short(words, 44), 'A Graphite line: it reads, on the line page', 'Run', words, icon='command')]


# ---- apps, settings, files, the desk, commands -----------------------------------------------------------------------------------
def query_words(text):
    return re.findall(r'\w+', clean(text).casefold())


def holds(words, hay):
    tokens = set(re.findall(r'\w+', str(hay).casefold()))
    return bool(words) and all(any(t.startswith(w) for t in tokens) for w in words)


def app_words(app):
    return ' '.join(str(x) for x in (app.get('name'), app.get('generic'), app.get('comment'), ' '.join(app.get('keywords') or ()),
                                     ' '.join(app.get('categories') or ()), app.get('group'), Path(str(app.get('program') or '')).name))


def windows_word(text):
    """The Windows words this line is, if any: (kind, target, beside)."""
    said = ' '.join(query_words(text))
    for words, kind, target, beside in WINDOWS:
        if said in words:return kind, target, beside
    return None


def app_row(app, beside=''):
    group = app.get('group') or 'Other'
    detail = 'App · %s' % group + (' · in a terminal' if app.get('terminal') else '')
    if app.get('generic') and app.get('generic') != app.get('name'):detail = '%s · %s' % (app['generic'], detail)
    row = Row('app', app.get('name') or app.get('id'), detail, 'Open', app.get('id'), beside, 'APPS', icon=app.get('icon_file') or '',
              extra=dict(group=group, available=app.get('available', True), reason=app.get('reason') or ''))
    if not app.get('available', True):row.tip = app.get('reason') or 'It cannot start here.'
    return row


def app_rows(text, apps, most=MOST['APPS']):
    words = query_words(text)
    if not words:return []
    rows = [];seen = set()
    windows = windows_word(text)
    if windows and windows[0] == 'apps':
        for app in apps:
            if any(holds(alt.split(), app_words(app)) for alt in windows[1].split('|')) and app.get('id') not in seen:
                rows.append(app_row(app, windows[2]));seen.add(app.get('id'))
                if len(rows) >= 2:break
    named = [a for a in apps if a.get('id') not in seen and holds(words, app_words(a))]
    named.sort(key=lambda a: (not str(a.get('name', '')).casefold().startswith(words[0]), str(a.get('name', '')).casefold()))
    rows += [app_row(a) for a in named]
    return rows[:most]


def windows_rows(text):
    """A Windows word that names a place here (Control Panel, cmd, File Explorer, Task Manager, the registry)."""
    found = windows_word(text)
    if not found or found[0] == 'apps':return []
    kind, target, beside = found
    if kind == 'explain':return [Row('explain', 'Settings are files here', target, 'Explain', target, beside, icon='settings')]
    title = WINDOWS_TITLES.get(target or kind, target or kind)
    detail = {'settings': "Graphite's settings", 'terminal': 'Graphite\'s Terminal: DOS words work there',
              'do': {'files': 'Your files, the Explorer of this computer', 'tasks': 'The programs that run, and Kasandra\'s work'}.get(target, '')}[kind]
    return [Row('place', title, detail, 'Open', (kind, target), beside, '', icon={'settings': 'settings', 'terminal': 'terminal'}.get(kind, 'command'))]


def setting_rows(found, most=MOST['SETTINGS']):
    return [Row('setting', label, 'Setting · %s' % target, 'Open', target, section='SETTINGS', icon='settings') for label, target in found[:most]]


def file_rows(text, recent, home, most=MOST['FILES']):
    """Recent files by name first, then your home's files and folders by name; each once."""
    words = query_words(text)
    rows = [];seen = set()
    for item in recent:
        path = item[0]
        if holds(words, Path(path).name) and path not in seen:
            seen.add(path);rows.append(file_row(path, 'Recent · ' + home_words(Path(path).parent), item[1] if len(item) > 1 else 'file'))
    for path, folder in home:
        path = str(path)
        if path in seen:continue
        seen.add(path);rows.append(file_row(path, ('Folder · ' if folder else 'File · ') + home_words(Path(path).parent), 'folder' if folder else 'file'))
    return rows[:most]


def file_row(path, detail, how='file'):
    return Row('file', Path(path).name, detail, 'Open', str(path), section='FILES', icon='folder' if how == 'folder' else 'file', extra=dict(how=how))


def desk_rows(found, most=MOST['DESK']):
    return [Row('desk', label, 'On the desk · %s' % str(role).replace('_', ' '), 'Open', ident, section='DESK', icon='desk') for label, role, ident in found[:most]]


def command_rows(found, most=MOST['COMMANDS']):
    rows = []
    for label, fn in found[:most]:
        verb = 'Open' if label.startswith(('Go to', 'Open', 'Project', 'Files', 'Settings')) else 'Run'
        rows.append(Row('command', label, 'A command of Graphite', verb, fn, section='COMMANDS', icon='command'))
    return rows


def recipe_rows(text, sources):
    """1.1 KS1 (recipes): a row for the recipe her dictionary reads in the words (recipe_book_qt.line_rows); Enter shows its
    answer or its dry run in her talk, and nothing changes."""
    try:
        from .recipe_book_qt import line_rows
        return [Row('command', title, detail, 'Show', do, section='COMMANDS', icon='command', extra=dict(recipe=True))
                for title, detail, do in line_rows(text, getattr(sources, 'host', None))]
    except Exception:  # noqa: BLE001 - no recipe read: no row
        return []


def ask_row(text):
    return Row('ask', '%s: %s' % (ASK, short(clean(text).lstrip('?').strip(), 44)), 'Your words go to her column; she proposes, you decide',
               ASK, clean(text).lstrip('?').strip(), icon='ask')


def reads_as_hers(text, reading=''):
    """Whether the words read as a request to her: a '?' lead, a question or a request's first word, or K4's objective reading."""
    words = clean(text)
    if words.startswith('?') or words.endswith('?'):return True
    if QUESTION.match(words):return True
    if reading == 'hers' and len(words.split()) >= 4:return True
    try:
        from .objective_plan import reads_as_objective
        return bool(reads_as_objective(words))
    except Exception:  # noqa: BLE001
        return False


# ---- the sources: what the line reads, from the window when there is one -------------------------------------------------------
class Sources:
    """What the rows are made from. Each reads the window when there is one, and the computer when not; a source that cannot
    be read gives nothing (its row is not shown), never an error."""

    def __init__(self, host=None, environ=None, which=shutil.which):
        self.host = host;self.environ = environ;self.which = which;self._apps = None

    def apps(self):
        if self._apps is None:
            try:
                if self.host is not None:
                    from .apps_qt import listing
                    found = listing(self.host)
                else:
                    from .apps_catalog import listing
                    found = listing(env=self.environ)
                self._apps = list(found.get('apps') or [])
            except Exception:  # noqa: BLE001 - no apps read: none offered
                self._apps = []
        return self._apps

    def recent(self, limit=12):
        return recent_files(self.host, limit, self.environ)

    def home(self, text):
        if len(clean(text)) < 2:return []
        try:
            from .search_reach import home_names
            return home_names(self.host, text, limit=8)[0]
        except Exception:  # noqa: BLE001
            return []

    def settings(self, text):
        try:
            from .console_qt import setting_rows as found
            return [(n['label'], n['target']) for n in found(text, MOST['SETTINGS'])]
        except Exception:  # noqa: BLE001
            return []

    def desk(self, text):
        if self.host is None or len(clean(text)) < 2:return []
        try:
            from .search_reach import records
            return [(n.get('label', ''), n.get('role', ''), n.get('id')) for n in records(self.host, text, MOST['DESK'])]
        except Exception:  # noqa: BLE001
            return []

    def commands(self, text):
        box = getattr(getattr(getattr(self.host, 'shell2', None), 'top', None), 'box', None)
        if box is None or len(clean(text)) < 2:return []
        try:return [(label, fn) for label, _hint, fn in box.commands(clean(text))]
        except Exception:  # noqa: BLE001
            return []

    def reading(self, text):
        try:
            from .foot_line import reading
            return reading(self.host, text)
        except Exception:  # noqa: BLE001
            return ''


def recent_files(host=None, limit=12, environ=None):
    """[(path, how)] newest first: what Graphite's viewer showed, Graphite's recent documents, then the desktop's own list of
    recently used files (~/.local/share/recently-used.xbel, as other apps keep it); only files that are still there."""
    out = [];seen = set()

    def add(path, how):
        path = str(path)
        if path in seen or len(out) >= limit:return
        try:
            if not Path(path).is_file():return
        except OSError:
            return
        seen.add(path);out.append((path, how))
    for path in list(getattr(host, '_viewer_recent', []) or [])[:limit]:add(path, 'viewer')
    try:
        root = Path(getattr(host, 'root', ''))
        for rel in list(host.session.state.get('recent', []))[:limit]:add(root / rel, 'document')
    except Exception:  # noqa: BLE001 - no session: none from it
        pass
    for path in desktop_recent(environ, limit):add(path, 'system')
    return out


def desktop_recent(environ=None, limit=12):
    """The desktop's recently used files (freedesktop.org's recently-used.xbel), newest first, local files only."""
    import urllib.parse
    from xml.etree import ElementTree
    env = os.environ if environ is None else environ
    folder = Path(env.get('XDG_DATA_HOME') or Path(env.get('HOME') or Path.home()) / '.local' / 'share')
    try:
        tree = ElementTree.parse(str(folder / 'recently-used.xbel'))
    except (OSError, ElementTree.ParseError):
        return []
    rows = []
    for bookmark in tree.getroot().iter('bookmark'):
        href = bookmark.get('href') or ''
        if not href.startswith('file://'):continue
        rows.append((bookmark.get('modified') or bookmark.get('visited') or '', urllib.parse.unquote(href[7:])))
    rows.sort(reverse=True)
    return [path for _, path in rows[:limit * 2]]


# ---- the rows ---------------------------------------------------------------------------------------------------------------------
def rows(text, sources=None):
    """Every row the line offers for `text`, the first being what Enter takes. Each row's verb says what Enter does on it."""
    sources = sources or Sources()
    words = clean(text)
    if not words:return []
    lead = words[:1]
    if lead == '?':return [ask_row(words)]
    if lead in ('$', '>') and len(words) > 1:
        return dos_rows(words) or terminal_rows(words, sources.which, led=True) + [ask_row(words[1:])]
    first = []
    first += sum_rows(words)
    if first and first[0].kind == 'sum':return first + [ask_row(words)]
    reading = sources.reading(words)
    first += address_rows(words)
    first += operation_rows(words)      # an operation's own name (apps.list, /files.list path=Slate) before the line reading it
    if not first:first += line_rows(words, reading)
    first += dos_rows(words)
    first += recipe_rows(words, sources)      # 1.1 KS1 (recipes): "Recipe: Free space in Home", Enter shows what it would do
    if lead == '/':
        place = Path(os.path.expanduser(words))
        if not first and place.exists():first.append(file_row(str(place), 'A place on this computer', 'folder' if place.is_dir() else 'file'))
        if first:return first + [ask_row(words)]
    found = []
    found += app_rows(words, sources.apps())
    found += setting_rows(sources.settings(words))
    found += file_rows(words, sources.recent(), sources.home(words))
    found += desk_rows(sources.desk(words))
    found += command_rows(sources.commands(words))
    found = windows_rows(words) + in_sections(found)      # a Windows word's own place first, then the sections
    last = [] if any(r.kind in ('dos', 'terminal') for r in first) else terminal_rows(words, sources.which)
    last += more_rows(words)  # 1.1 B4: rows a window adds (the folded foot's Search inside files and Search the web)
    ask = ask_row(words)
    if reads_as_hers(words, reading) and not first:return [ask] + found + last
    out = first + found + last + [ask]
    return out


MORE = []  # 1.1 B4: callables (words) -> [Row]: rows a window adds after the found ones (foot_fold_qt, once the foot folds)


def more_rows(words):  # 1.1 B4
    out = []
    for fn in list(MORE):
        try:out += list(fn(words) or [])
        except Exception:  # noqa: BLE001 - 1.1 B4: a window's own rows never cost the line its rows
            continue
    return out


def in_sections(found):
    """The rows found by name, in the design's order: Apps, Settings, Files, the desk, Commands (each section's own order kept)."""
    order = {s: i for i, s in enumerate(SECTIONS)}
    return sorted(found, key=lambda r: order.get(r.section, len(order)))


# ---- Start: apps by kind, recent files, power --------------------------------------------------------------------------------------
def apps_by_kind(listed):
    """[(kind words, [app dicts])] for Start: what the owner pinned first ("Pinned"), then the kinds A to Z, Other last, each
    A to Z by name (apps_catalog's groups, from the apps' own desktop entries)."""
    apps = {a['id']: a for a in listed.get('apps') or []}
    out = []
    pinned = [p.get('app') for p in listed.get('pins') or [] if p.get('app')]
    if pinned:out.append(('Pinned', pinned))
    for group in listed.get('groups') or []:
        members = [apps[i] for i in group.get('ids') or [] if i in apps]
        if members:out.append((group['group'], members))
    if not listed.get('groups') and apps:
        found = {}
        for a in sorted(apps.values(), key=lambda a: str(a.get('name', '')).casefold()):found.setdefault(a.get('group') or 'Other', []).append(a)
        out += sorted(found.items(), key=lambda kv: (kv[0] == 'Other', kv[0].casefold()))
    return out


POWER = ('lock', 'suspend', 'logout', 'restart', 'shutdown')      # session_power.GROUP's own order, without the leave


def power_words():
    """[(key, word, scope)] of Start's power row, in 1.0's leave group's words."""
    from . import session_power as power
    return [(key, power.WORDS[key], power.SCOPES[key]) for key in POWER]
