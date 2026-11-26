"""Graphite 1.0 S2 · Apps from what is installed: the programs on this computer, read from their desktop entries, how each
is started, and which program opens which kind of file.

The owner's paper, section 2: "Its Apps launcher should discover installed applications ... The owner needs access to ...
file associations ... without leaving Graphite." Nothing here needs Qt; the Apps panel (apps_qt) and the Kernel's apps.*
operations both read this module.

  the catalogue   scan() reads the XDG desktop entries (the Desktop Entry Specification) from the owner's own folder
                  ($XDG_DATA_HOME/applications, ~/.local/share/applications) and then the system's ($XDG_DATA_DIRS, by default
                  /usr/local/share and /usr/share, each with applications/ under it). An entry's id is its path under
                  applications/ with '/' turned into '-'; the first folder that has an id decides it (so an entry the owner
                  keeps hides the system's of the same id, and Hidden=true there hides it altogether). Only Type=Application
                  with a Name and an Exec (or a D-Bus start, which Graphite cannot use: said so) is an app. Listed in Apps:
                  not NoDisplay, not Hidden, its TryExec found, and OnlyShowIn / NotShowIn respected loosely: an entry made
                  only for other desktops (OnlyShowIn without Graphite and without the session's XDG_CURRENT_DESKTOP) or
                  kept away from this one (NotShowIn naming it) is left out of the list, and stays reachable by Open with.
                  Names, generic names, comments and keywords in the owner's language (LANGUAGE, LC_ALL, LC_MESSAGES, LANG;
                  lang_COUNTRY@MODIFIER, lang_COUNTRY, lang@MODIFIER, lang, then the plain key). Each app has one group, from
                  the first of the specification's main categories it names (GROUPS, in plain words), else Other.
  the icons       icon_path(): an absolute Icon used as it is; a name looked up in the icon themes (the owner's GTK theme
                  when one is set, then Adwaita, then what they inherit, then hicolor; their index.theme folders, the
                  Applications ones first; the nearest size at or above the size asked, a scalable one when there is no
                  exact size), then the pixmaps folder. None when there is none: the window draws Graphite's own glyph.
  starting it     command() turns Exec into argv with the field codes, never through a shell: %f one file (one start per
                  file when there are several), %F the files each as an argument of its own, %u one address, %U the
                  addresses (a local file as a file:// address), %i '--icon' and the Icon when there is one, %c the name,
                  %k the entry's own path, %% a percent sign; the deprecated %d %D %n %N %v %m and unknown codes are dropped.
                  Exec's quoting is the specification's (double quotes, with \\ escaping " ` $ and \\ inside them; single
                  quotes and a backslash outside quotes are taken as a shell would take them, without a shell). A field
                  code inside a quoted argument is NOT filled: that argument may be read by a shell (sh -c "...") and a
                  file's name must never become a command; such an entry is said not to take files. Terminal=true runs
                  in the computer's terminal (x-terminal-emulator, else xterm and the others in TERMINALS) with its own
                  argv after -e. launch() starts each argv through session_launch.launch (1.0 S1): a session and process
                  group of its own, so a Graphite restart leaves it open; never sudo, pkexec, su or doas.
  kinds of file   mime_of(): the type of a file from the shared MIME database's globs2 (literal names, then the longest
                  extension, then the other patterns, by weight), else Python's mimetypes, else a look at its first bytes
                  (text or not). parents(): its aliases and the types it is a kind of (subclasses; every text/* is a kind of
                  text/plain). default_for(): the default program from the mimeapps.list files in the specification's
                  order ($XDG_CONFIG_HOME, $XDG_CONFIG_DIRS, then the data folders' applications/; a desktop's own
                  <desktop>-mimeapps.list before the plain one; the old defaults.list last), honouring [Removed
                  Associations]; else the type's parent's. apps_for(): "Open with": the default first, then [Added
                  Associations], then every app whose MimeType names the type, then those for its parent types.
                  set_default(): writes the owner's own $XDG_CONFIG_HOME/mimeapps.list only ([Default Applications], the
                  app first in [Added Associations], and out of [Removed Associations]), keeping every other line, whole
                  or not at all, then reads it back: verified only when the default the files now give is the one chosen.
                  An empty id takes the owner's line back out (the system's default again).
  Graphite's own  pins(): the apps the owner put on the list with Apps ⊕ ("Add an app to the list": an entry by its id, or a
  list            command the owner typed, read with Exec's rules, no shell), kept in Graphite's profile folder (apps.json).

Kernel operations (one block in engineering_kernel.py and engineering_cli.py, commented 1.0 S2):
    apps.list    {query?, every?}           read     the apps (listed ones; with every, all of them with why each is
                                                     not listed), their groups, Graphite's pins
    apps.for     {path? | type?}            read     a file's type in words, its default program and the apps that open it
    apps.open    {id, files?, urls?}        execute  start an app (or a pinned command, id 'pin:...') with files or
                                                     addresses; each start through session_launch; done when it began
    apps.default {type, id}                 approve  the default program for a type (the owner's mimeapps.list); only the
                                                     owner's press: her principal never has approve
    apps.pin     {id? | name, command}      execute  put an app or a command on Graphite's own list (Yours)
    apps.unpin   {key}                      execute  take one off it
apps.list and apps.for are observers (activity.OBSERVER_OPERATIONS): the panel reads them each time it opens.
"""
from __future__ import annotations

import configparser
import fnmatch
import hashlib
import json
import mimetypes
import os
import re
import shutil
import tempfile
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA = 'graphite.apps/1'
PINS_SCHEMA = 'graphite.apps.pins/1'
PINS_FILE = 'apps.json'
OUR_DESKTOP = 'graphite'           # the name Graphite answers to in OnlyShowIn and NotShowIn
ENTRY = 'Desktop Entry'
# The specification's main categories, in plain words (the Apps panel's headings). An app's group is the first of these it
# names; Audio and Video are AudioVideo's.
GROUPS = {'AudioVideo': 'Sound and video', 'Audio': 'Sound and video', 'Video': 'Sound and video', 'Development': 'Development',
          'Education': 'Education', 'Game': 'Games', 'Graphics': 'Graphics', 'Network': 'Internet', 'Office': 'Office',
          'Science': 'Science', 'Settings': 'Settings', 'System': 'System', 'Utility': 'Accessories'}
OTHER = 'Other'
# Graphite's own glyph for an app with no icon of its own, by its group (programs_qt's small graphite icons).
GROUP_GLYPH = {'Office': 'documents', 'Graphics': 'inkscape', 'Science': 'laboratory', 'Development': 'hdl', 'Internet': 'transfer',
               'Sound and video': 'media', 'Education': 'references', 'Games': 'game', 'Accessories': 'calculate', 'System': 'brain',
               'Settings': 'settings', OTHER: 'window'}
DEPRECATED_CODES = set('dDnNvm')
TERMINALS = (('x-terminal-emulator', ('-e',)), ('xterm', ('-e',)), ('uxterm', ('-e',)), ('urxvt', ('-e',)), ('alacritty', ('-e',)),
             ('konsole', ('-e',)), ('xfce4-terminal', ('-x',)), ('mate-terminal', ('-x',)), ('gnome-terminal', ('--',)),
             ('kitty', ()), ('foot', ()))
ICON_SUFFIXES = ('.png', '.svg', '.xpm')
NEVER = frozenset({'sudo', 'pkexec', 'su', 'doas', 'run0'})
TYPE = re.compile(r'^[A-Za-z0-9][\w.+-]{0,126}/[\w.+-]{1,127}$')
DESKTOP_ID = re.compile(r'^[\w][\w.+@-]{0,250}\.desktop$')
# A few kinds of file in the owner's words ("Always open PDF files with this"); any other is said by its extension.
TYPE_WORDS = {'application/pdf': 'PDF files', 'text/plain': 'plain text files', 'text/markdown': 'Markdown files', 'text/csv': 'CSV tables',
              'text/html': 'web pages', 'image/png': 'PNG pictures', 'image/jpeg': 'JPEG pictures', 'image/svg+xml': 'SVG drawings',
              'image/gif': 'GIF pictures', 'image/webp': 'WebP pictures', 'image/tiff': 'TIFF pictures', 'audio/mpeg': 'MP3 sound',
              'audio/x-wav': 'WAV sound', 'audio/flac': 'FLAC sound', 'video/mp4': 'MP4 video', 'application/zip': 'ZIP archives',
              'application/json': 'JSON files', 'application/xml': 'XML files', 'text/x-python': 'Python files', 'text/x-python3': 'Python files',
              'application/vnd.oasis.opendocument.text': 'OpenDocument texts', 'application/vnd.oasis.opendocument.spreadsheet': 'OpenDocument spreadsheets',
              'application/vnd.oasis.opendocument.presentation': 'OpenDocument presentations',
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word documents',
              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel workbooks', 'application/msword': 'Word documents',
              'application/vnd.ms-excel': 'Excel workbooks', 'inode/directory': 'folders', 'application/x-kicad-pcb': 'KiCad boards',
              'application/x-kicad-schematic': 'KiCad schematics', 'application/x-blender': 'Blender scenes', 'model/stl': 'STL models',
              'x-scheme-handler/http': 'web addresses', 'x-scheme-handler/https': 'web addresses', 'x-scheme-handler/mailto': 'mail addresses'}


# ---- the folders ------------------------------------------------------------------------------------------------------------
def _env(env):
    return os.environ if env is None else env


def _home(env):
    return Path(_env(env).get('HOME') or str(Path.home()))


def data_home(env=None):
    value = _env(env).get('XDG_DATA_HOME')
    return Path(value) if value and os.path.isabs(value) else _home(env) / '.local' / 'share'


def data_dirs(env=None):
    value = _env(env).get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share'
    return [Path(p) for p in value.split(':') if p and os.path.isabs(p)]


def config_home(env=None):
    value = _env(env).get('XDG_CONFIG_HOME')
    return Path(value) if value and os.path.isabs(value) else _home(env) / '.config'


def config_dirs(env=None):
    value = _env(env).get('XDG_CONFIG_DIRS') or '/etc/xdg'
    return [Path(p) for p in value.split(':') if p and os.path.isabs(p)]


def application_dirs(env=None):
    """The applications/ folders in their order of precedence: the owner's own first."""
    out = []
    for base in [data_home(env)] + data_dirs(env):
        folder = base / 'applications'
        if folder not in out:out.append(folder)
    return out


def desktops(env=None):
    """The names this session answers to in OnlyShowIn and NotShowIn, lower case: XDG_CURRENT_DESKTOP's, and Graphite."""
    named = [d.strip().lower() for d in (_env(env).get('XDG_CURRENT_DESKTOP') or '').split(':') if d.strip()]
    return named + ([OUR_DESKTOP] if OUR_DESKTOP not in named else [])


def languages(env=None):
    """The locale keys to try, most particular first (the specification's order), from LANGUAGE and the locale."""
    env = _env(env)
    locale = env.get('LC_ALL') or env.get('LC_MESSAGES') or env.get('LANG') or ''
    wanted = []
    if locale and locale not in ('C', 'POSIX') and not locale.startswith('C.'):
        wanted = [w for w in (env.get('LANGUAGE') or '').split(':') if w] + [locale]
    out = []
    for value in wanted:
        value = value.split('.', 1)[0] if '@' not in value else value.split('.', 1)[0] + '@' + value.split('@', 1)[1]
        lang, _, modifier = value.partition('@');lang, _, country = lang.partition('_')
        if not lang:continue
        for key in ((lang + '_' + country + '@' + modifier) if country and modifier else '', (lang + '_' + country) if country else '',
                    (lang + '@' + modifier) if modifier else '', lang):
            if key and key not in out:out.append(key)
    return out


# ---- reading an entry -------------------------------------------------------------------------------------------------------
def unescape(value):
    """The specification's escapes in a string value: \\s \\n \\t \\r \\\\ (any other backslash is kept)."""
    out = [];i = 0
    while i < len(value):
        c = value[i]
        if c == '\\' and i + 1 < len(value):
            nxt = value[i + 1];table = {'s': ' ', 'n': '\n', 't': '\t', 'r': '\r', '\\': '\\'}
            if nxt in table:out.append(table[nxt]);i += 2;continue
        out.append(c);i += 1
    return ''.join(out)


def string_list(value):
    """A list value: items separated by ';' (an escaped '\\;' is a semicolon in an item), each unescaped."""
    out = [];item = [];i = 0
    while i < len(value):
        c = value[i]
        if c == '\\' and i + 1 < len(value) and value[i + 1] == ';':item.append(';');i += 2;continue
        if c == ';':out.append(''.join(item));item = [];i += 1;continue
        item.append(c);i += 1
    if item:out.append(''.join(item))
    return [unescape(x).strip() for x in out if x.strip()]


def read_groups(path):
    """A desktop entry (or any key file) as {group: {key: raw value}}; comments and blank lines skipped, the first of a
    repeated key kept. Unreadable or not UTF-8: {}."""
    try:text = Path(path).read_bytes().decode('utf-8')
    except (OSError, UnicodeDecodeError):return {}
    groups = {};current = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):continue
        if line.startswith('[') and line.endswith(']'):
            current = groups.setdefault(line[1:-1], {});continue
        if current is None or '=' not in line:continue
        key, _, value = line.partition('=')
        current.setdefault(key.strip(), value.strip())
    return groups


def localized(group, key, langs):
    for lang in langs:
        value = group.get('%s[%s]' % (key, lang))
        if value is not None:return value
    return group.get(key)


def _bool(value):
    return str(value or '').strip().lower() == 'true'


def which(program, env=None):
    """The program's file: an absolute path when it is an executable file; else found on the session's PATH."""
    if not program:return None
    if '/' in program:
        return program if os.path.isfile(program) and os.access(program, os.X_OK) else None
    return shutil.which(program, path=_env(env).get('PATH') or os.defpath)


@dataclass
class App:
    """One desktop entry. listed: shown in Apps; why: the plain reason when it is not; available: it can be started here;
    reason: why not. kind: 'entry' (a desktop entry) or 'pin' (a command the owner put on the list)."""
    id: str
    path: str
    name: str
    generic: str = ''
    comment: str = ''
    keywords: tuple = ()
    categories: tuple = ()
    group: str = OTHER
    icon: str = ''
    exec: str = ''
    try_exec: str = ''
    terminal: bool = False
    mime_types: tuple = ()
    workdir: str = ''
    no_display: bool = False
    hidden: bool = False
    only_show_in: tuple = ()
    not_show_in: tuple = ()
    dbus: bool = False
    wm_class: str = ''
    listed: bool = True
    why: str = ''
    available: bool = True
    reason: str = ''
    program: str = ''
    takes: str = ''
    kind: str = 'entry'
    argv: tuple = ()

    def words(self):
        """Everything search looks in, lower case."""
        return ' '.join((self.name, self.generic, self.comment, ' '.join(self.keywords), ' '.join(self.categories), self.group,
                         Path(self.exec_program()).name)).casefold()

    def exec_program(self):
        try:parts = split_exec(unescape(self.exec)) if self.exec else []
        except ValueError:parts = []
        return parts[0][0] if parts else (self.argv[0] if self.argv else '')

    def as_dict(self):
        return {'id': self.id, 'name': self.name, 'generic': self.generic, 'comment': self.comment, 'keywords': list(self.keywords),
                'categories': list(self.categories), 'group': self.group, 'glyph': GROUP_GLYPH.get(self.group, 'window'), 'icon': self.icon,
                'terminal': self.terminal, 'mime_types': list(self.mime_types), 'listed': self.listed, 'why': self.why,
                'available': self.available, 'reason': self.reason, 'program': self.program, 'takes': self.takes, 'kind': self.kind,
                'entry': self.path}


def group_of(categories):
    for c in categories:
        if c in GROUPS:return GROUPS[c]
    return OTHER


def parse_entry(path, ident, env=None, langs=None, ours=None):
    """One desktop entry as an App, or None when it is not an application (Type, Name and Exec or a D-Bus start)."""
    groups = read_groups(path);g = groups.get(ENTRY)
    if not g:return None
    langs = languages(env) if langs is None else langs
    if g.get('Type', 'Application') != 'Application':return None
    hidden = _bool(g.get('Hidden'))
    name = unescape(localized(g, 'Name', langs) or '')
    if not name and not hidden:return None
    exec_ = g.get('Exec', '');dbus = _bool(g.get('DBusActivatable'))
    if not exec_ and not dbus and not hidden:return None
    categories = tuple(string_list(g.get('Categories', '')))
    app = App(id=ident, path=str(path), name=name, generic=unescape(localized(g, 'GenericName', langs) or ''),
              comment=unescape(localized(g, 'Comment', langs) or ''), keywords=tuple(string_list(localized(g, 'Keywords', langs) or '')),
              categories=categories, group=group_of(categories), icon=unescape(g.get('Icon', '')), exec=exec_,
              try_exec=unescape(g.get('TryExec', '')), terminal=_bool(g.get('Terminal')), mime_types=tuple(string_list(g.get('MimeType', ''))),
              workdir=unescape(g.get('Path', '')), no_display=_bool(g.get('NoDisplay')), hidden=hidden,
              only_show_in=tuple(s.lower() for s in string_list(g.get('OnlyShowIn', ''))),
              not_show_in=tuple(s.lower() for s in string_list(g.get('NotShowIn', ''))), dbus=dbus, wm_class=g.get('StartupWMClass', ''))
    judge(app, env, desktops(env) if ours is None else ours)
    return app


def judge(app, env=None, ours=()):
    """Whether it is listed (and why not) and whether it can be started here (and why not)."""
    whys = []
    if app.hidden:whys.append('its entry says it is deleted')
    if app.no_display:whys.append('its entry asks not to be shown in menus')
    if app.only_show_in and not set(app.only_show_in) & set(ours):whys.append('made for %s only' % ', '.join(app.only_show_in))
    if app.not_show_in and set(app.not_show_in) & set(ours):whys.append('its entry keeps it out of this desktop')
    if app.try_exec and not which(app.try_exec, env):whys.append('%s is not installed' % app.try_exec)
    app.listed = not whys;app.why = '; '.join(whys)
    if not app.exec:
        app.available = False;app.reason = '%s starts only through D-Bus, which Graphite does not use to start apps.' % app.name;return app
    try:parts = split_exec(unescape(app.exec))
    except ValueError as exc:
        app.available = False;app.reason = 'Its command line cannot be read: %s.' % exc;return app
    if not parts:
        app.available = False;app.reason = 'Its command line is empty.';return app
    program = parts[0][0];found = which(program, env)
    app.takes = takes(parts)
    if Path(program).name in NEVER:
        app.available = False;app.reason = 'Graphite never starts a program through %s.' % Path(program).name
    elif found is None:
        app.available = False;app.reason = '%s is not installed on this computer.' % program
    else:
        app.program = found;app.available = True;app.reason = ''
    return app


# ---- the catalogue ----------------------------------------------------------------------------------------------------------
@dataclass
class Catalog:
    """Every app by id (the first folder that has an id decides it), in the order read."""
    apps: dict = field(default_factory=dict)
    dirs: tuple = ()
    signature: str = ''
    read_at: float = 0.0

    def get(self, ident):
        return self.apps.get(ident)

    def listed(self):
        """The apps shown in Apps, A to Z by name."""
        return sorted((a for a in self.apps.values() if a.listed), key=lambda a:(a.name.casefold(), a.id))

    def every(self):
        return sorted(self.apps.values(), key=lambda a:(a.name.casefold(), a.id))

    def groups(self):
        """[(group words, [apps])] for the listed apps: groups A to Z, Other last."""
        found = {}
        for app in self.listed():found.setdefault(app.group, []).append(app)
        return sorted(found.items(), key=lambda kv:(kv[0] == OTHER, kv[0].casefold()))

    def search(self, query, every=False):
        """The apps where every word of the query starts a word of their name, generic name, comment, keywords, categories
        or program."""
        words = query_words(query)
        pool = self.every() if every else self.listed()
        if not words:return pool
        return [a for a in pool if holds(words, a.words())]


def query_words(query):
    """The words typed, lower case (anything not a letter or a digit separates them)."""
    return re.findall(r'\w+', str(query or '').casefold())


def holds(words, hay):
    """Every word typed starts a word of `hay` ('pdf' finds Rail PDF Viewer, 'rail' does not find Work trail)."""
    tokens = set(re.findall(r'\w+', str(hay).casefold()))
    return all(any(t.startswith(w) for t in tokens) for w in words)


def _entries(env=None):
    """(id, path) of every .desktop file in the applications folders, the owner's first; and a signature of their names,
    sizes and times (the catalogue is read again only when it changes)."""
    out = [];h = hashlib.sha256()
    for folder in application_dirs(env):
        if not folder.is_dir():continue
        for dirpath, dirnames, filenames in os.walk(folder):
            dirnames.sort()
            for name in sorted(filenames):
                if not name.endswith('.desktop'):continue
                path = Path(dirpath) / name
                try:st = path.stat()
                except OSError:continue
                rel = path.relative_to(folder).as_posix()
                out.append((rel.replace('/', '-'), path))
                h.update(('%s\0%d\0%d\n' % (path, st.st_size, st.st_mtime_ns)).encode('utf-8', 'surrogateescape'))
    return out, h.hexdigest()


_catalogs = {}


def scan(env=None, fresh=False):
    """The catalogue for this environment's folders and language, read again only when an entry was added, removed or
    changed since the last reading."""
    found, signature = _entries(env)
    key = (tuple(str(d) for d in application_dirs(env)), tuple(languages(env)), tuple(desktops(env)), _env(env).get('PATH', ''))
    kept = _catalogs.get(key)
    if kept is not None and kept.signature == signature and not fresh:return kept
    langs = languages(env);ours = desktops(env);apps = {};seen = set()
    for ident, path in found:
        if ident in seen:continue      # the first folder with this id decides it: a Hidden entry, or one that is no app, hides the rest
        seen.add(ident)
        app = parse_entry(path, ident, env, langs, ours)
        if app is not None and not app.hidden:apps[ident] = app
    catalog = Catalog(apps, tuple(str(d) for d in application_dirs(env)), signature, time.time())
    _catalogs[key] = catalog
    return catalog


# ---- Exec and the field codes -----------------------------------------------------------------------------------------------
def split_exec(text):
    """Exec's arguments as [(argument, quoted)]: double quotes with \\ escaping " ` $ \\ inside them; single quotes kept
    literally; a backslash outside quotes takes the next character as it is. Unbalanced quotes: ValueError."""
    out = [];arg = [];quoted = False;started = False;i = 0;n = len(text)
    while i < n:
        c = text[i]
        if c in ' \t\n':
            if started:out.append((''.join(arg), quoted));arg = [];quoted = False;started = False
            i += 1;continue
        if c == '"':
            started = True;quoted = True;i += 1
            while True:
                if i >= n:raise ValueError('a double quote is not closed')
                c = text[i]
                if c == '\\' and i + 1 < n and text[i + 1] in '"`$\\':arg.append(text[i + 1]);i += 2;continue
                if c == '"':i += 1;break
                arg.append(c);i += 1
            continue
        if c == "'":
            started = True;quoted = True;end = text.find("'", i + 1)
            if end < 0:raise ValueError('a single quote is not closed')
            arg.append(text[i + 1:end]);i = end + 1;continue
        if c == '\\' and i + 1 < n:arg.append(text[i + 1]);started = True;i += 2;continue
        arg.append(c);started = True;i += 1
    if started:out.append((''.join(arg), quoted))
    return out


def takes(parts):
    """What the command line takes: 'files' (%F), 'file' (%f), 'urls' (%U), 'url' (%u), or '' (nothing), from its unquoted
    arguments only."""
    for arg, quoted in parts:
        if quoted:continue
        for code, kind in (('%F', 'files'), ('%U', 'urls'), ('%f', 'file'), ('%u', 'url')):
            if code in arg.replace('%%', ''):return kind
    return ''


def file_url(path):
    return 'file://' + urllib.parse.quote(str(Path(path).absolute()), safe='/')


def _expand(arg, single, name, icon, location):
    """One unquoted argument with its codes filled: %f/%u by `single` ('' leaves them out), %c, %k, %%; %F %U %i handled
    by the caller when they stand alone."""
    out = [];i = 0
    while i < len(arg):
        c = arg[i]
        if c == '%' and i + 1 < len(arg):
            code = arg[i + 1];i += 2
            if code == '%':out.append('%')
            elif code in 'fuFU':out.append(single)
            elif code == 'c':out.append(name)
            elif code == 'k':out.append(location)
            elif code == 'i':out.append(icon)
            continue      # deprecated and unknown codes are dropped
        out.append(c);i += 1
    return ''.join(out)


def _no_codes(arg):
    """A quoted argument with its field codes taken out (%% stays a percent sign)."""
    out = [];i = 0
    while i < len(arg):
        if arg[i] == '%' and i + 1 < len(arg):
            if arg[i + 1] == '%':out.append('%')
            i += 2;continue
        out.append(arg[i]);i += 1
    return ''.join(out)


def command(exec_text, files=(), urls=(), name='', icon='', location=''):
    """The argv lists to start: one, or one per file when the command takes a single file (%f or %u) and several are
    given. files: local paths; urls: addresses (a local file given to %u/%U becomes a file:// address). Never a shell.
    ValueError when its command line cannot be read."""
    parts = split_exec(unescape(exec_text)) if isinstance(exec_text, str) else list(exec_text)
    if not parts:raise ValueError('the command line is empty')
    kind = takes(parts)
    files = [str(f) for f in files];urls = [str(u) for u in urls]
    if kind in ('file', 'files'):items = files + [u for u in urls]
    else:items = [file_url(f) for f in files] + urls
    runs = [[]] if kind in ('files', 'urls', '') or len(items) <= 1 else [[] for _ in items]
    for r, run in enumerate(runs):
        single = items[r] if kind in ('file', 'url') and items else ''
        for arg, quoted in parts:
            if quoted:
                run.append(_no_codes(arg))      # never a file, a name or a path inside quotes: a shell may read them
                continue
            if arg in ('%F', '%U'):run.extend(items);continue
            if arg in ('%f', '%u'):
                if single:run.append(single)
                continue
            if arg == '%i':
                if icon:run.extend(['--icon', icon])
                continue
            value = _expand(arg, single, name, icon, location)
            if value or arg == '':run.append(value)
    return runs


def terminal_argv(argv, env=None):
    """argv run in the computer's terminal, or None when there is none."""
    for program, flag in TERMINALS:
        found = which(program, env)
        if found:return [found, *flag, *argv]
    return None


def launch_app(app, files=(), urls=(), env=None, launcher=None):
    """Start an app with files or addresses: dict(ok, argvs, started:[{pid, reason}], reason). Each argv starts through
    session_launch.launch (its own session and process group), unless `launcher` is given (a stand-in for checks)."""
    if not app.available:return dict(ok=False, argvs=[], started=[], reason=app.reason or '%s cannot be started here.' % app.name)
    files = [os.path.abspath(str(f)) for f in files];urls = [str(u) for u in urls]      # whole paths: a file is never read as an option
    for f in files:
        if not os.path.exists(f):return dict(ok=False, argvs=[], started=[], reason='%s is not there.' % f)
    if any(u.startswith('-') for u in urls):return dict(ok=False, argvs=[], started=[], reason='An address cannot start with a dash.')
    if (files or urls) and not app.takes:
        return dict(ok=False, argvs=[], started=[], reason='%s does not take files: its entry gives it no place for them.' % app.name)
    try:
        if app.kind == 'pin':argvs = command([(a, False) for a in app.argv], files, urls, app.name, app.icon, '')
        else:argvs = command(app.exec, files, urls, app.name, app.icon, app.path)
    except ValueError as exc:
        return dict(ok=False, argvs=[], started=[], reason='Its command line cannot be read: %s.' % exc)
    if app.terminal:
        wrapped = [terminal_argv(a, env) for a in argvs]
        if any(w is None for w in wrapped):
            return dict(ok=False, argvs=argvs, started=[], reason='%s runs in a terminal, and no terminal is installed (xterm would do).' % app.name)
        argvs = wrapped
    if launcher is None:
        from .session_launch import launch as launcher
    started = [];cwd = app.workdir if app.workdir and os.path.isdir(app.workdir) else None
    for argv in argvs:
        started.append(launcher(argv, cwd=cwd, name=app.name))
    ok = bool(started) and all(s.get('ok') for s in started)
    reason = '%s started in a session of its own.' % app.name if ok else next((s.get('reason') for s in started if not s.get('ok')), 'It did not start.')
    if ok and len(started) > 1:reason = '%s started %d times, once for each file.' % (app.name, len(started))
    return dict(ok=ok, argvs=argvs, started=[{'pid': s.get('pid'), 'ok': bool(s.get('ok')), 'reason': s.get('reason', '')} for s in started], reason=reason)


# ---- icons ------------------------------------------------------------------------------------------------------------------
def icon_bases(env=None):
    out = [_home(env) / '.icons', data_home(env) / 'icons'] + [d / 'icons' for d in data_dirs(env)]
    seen = [];[seen.append(p) for p in out if p not in seen]
    return seen


def pixmap_dirs(env=None):
    return [d / 'pixmaps' for d in data_dirs(env)] + [Path('/usr/share/pixmaps')]


def chosen_theme(env=None):
    """The owner's icon theme: GTK's setting when there is one, else Adwaita when it is installed, else hicolor alone."""
    for name in ('gtk-4.0', 'gtk-3.0'):
        ini = config_home(env) / name / 'settings.ini'
        try:
            parser = configparser.ConfigParser(interpolation=None);parser.read(ini, encoding='utf-8')
            theme = parser.get('Settings', 'gtk-icon-theme-name', fallback='').strip().strip('"')
            if theme:return theme
        except (OSError, configparser.Error, UnicodeDecodeError):pass
    return 'Adwaita'


_themes = {}


def _theme(name, env=None):
    """(the theme's folders [(base path, [(subdir, size, min, max, kind, scale, apps)])], what it inherits)."""
    key = (name, tuple(str(b) for b in icon_bases(env)))
    if key in _themes:return _themes[key]
    places = [];inherits = []
    for base in icon_bases(env):
        root = base / name;index = root / 'index.theme'
        if not index.is_file():continue
        groups = read_groups(index);head = groups.get('Icon Theme', {})
        if not inherits:inherits = [x.strip() for x in head.get('Inherits', '').split(',') if x.strip()]
        subdirs = []
        for sub in [x.strip() for x in (head.get('Directories', '') + ',' + head.get('ScaledDirectories', '')).split(',') if x.strip()]:
            g = groups.get(sub, {})
            try:size = int(g.get('Size', '0'));scale = int(g.get('Scale', '1'))
            except ValueError:continue
            kind = g.get('Type', 'Threshold')
            try:low = int(g.get('MinSize', size));high = int(g.get('MaxSize', size));threshold = int(g.get('Threshold', '2'))
            except ValueError:low, high, threshold = size, size, 2
            if kind == 'Threshold':low, high = size - threshold, size + threshold
            apps = g.get('Context', '') == 'Applications' or '/apps' in sub or sub.startswith('apps')
            subdirs.append((sub, size, low, high, kind, scale, apps))
        places.append((root, subdirs))
    _themes[key] = (places, inherits)
    return _themes[key]


def _distance(size, low, high, kind, want):
    if low <= want <= high:return 0
    return low - want if want < low else want - high


def icon_path(name, size=32, env=None, theme=None):
    """The file for an Icon value: an absolute path as it is (when there); else the nearest-sized file in the theme chain
    (Applications folders first), then the pixmaps; None when there is none."""
    if not name:return None
    if os.path.isabs(name):return name if os.path.isfile(name) else None
    key = (name, int(size), theme, tuple(str(b) for b in icon_bases(env)), str(config_home(env)))
    if key not in _icons:
        _icons[key] = _icon_lookup(name, size, env, theme)
        while len(_icons) > 512:_icons.pop(next(iter(_icons)))
    return _icons[key]


_icons = {}


def _icon_lookup(name, size, env, theme):
    stem = name
    for suffix in ICON_SUFFIXES:
        if stem.endswith(suffix):stem = stem[:-len(suffix)]
    chain = [];todo = [theme or chosen_theme(env)]
    while todo:
        t = todo.pop(0)
        if t in chain:continue
        chain.append(t);todo.extend(_theme(t, env)[1])
    if 'hicolor' not in chain:chain.append('hicolor')
    for t in chain:
        places = _theme(t, env)[0];best = None
        for apps_first in (True, False):
            for root, subdirs in places:
                for sub, s, low, high, kind, scale, apps in subdirs:
                    if apps != apps_first:continue
                    for suffix in ICON_SUFFIXES:
                        path = root / sub / (stem + suffix)
                        if path.is_file():
                            d = _distance(s, low, high, kind, size)
                            rank = (d, 0 if suffix == '.svg' and kind == 'Scalable' else 1, -s if s < size else s, scale != 1)
                            if best is None or rank < best[0]:best = (rank, str(path))
            if best is not None:return best[1]
    for folder in pixmap_dirs(env):
        for suffix in ICON_SUFFIXES:
            path = folder / (stem + suffix)
            if path.is_file():return str(path)
    return None


# ---- kinds of file ----------------------------------------------------------------------------------------------------------
_mime = {}


def _mime_db(env=None):
    """(literal names, extensions, other patterns, subclasses, aliases) from the shared MIME database, read once per set
    of folders (the owner's first)."""
    bases = [data_home(env)] + data_dirs(env);key = tuple(str(b) for b in bases)
    if key in _mime:return _mime[key]
    literal, ext, other, parents, aliases = {}, {}, [], {}, {}
    for base in reversed(bases):      # the more important folder last, so it wins
        folder = base / 'mime'
        try:lines = (folder / 'globs2').read_text(encoding='utf-8').splitlines()
        except (OSError, UnicodeDecodeError):lines = []
        for line in lines:
            if not line or line.startswith('#'):continue
            bits = line.split(':')
            if len(bits) < 3:continue
            try:weight = int(bits[0])
            except ValueError:continue
            mime, glob = bits[1], bits[2];cs = len(bits) > 3 and 'cs' in bits[3].split(',')
            if not any(ch in glob for ch in '*?['):
                k = glob if cs else glob.lower();known = literal.get(k)
                if known is None or weight >= known[0]:literal[k] = (weight, mime)
            elif glob.startswith('*.') and not any(ch in glob[2:] for ch in '*?['):
                k = glob[2:] if cs else glob[2:].lower();known = ext.get(k)
                if known is None or weight >= known[0]:ext[k] = (weight, mime)
            else:other.append((weight, mime, glob, cs))
        for name, table in (('subclasses', parents), ('aliases', aliases)):
            try:rows = (folder / name).read_text(encoding='utf-8').splitlines()
            except (OSError, UnicodeDecodeError):rows = []
            for row in rows:
                bits = row.split()
                if len(bits) != 2:continue
                if name == 'subclasses':table.setdefault(bits[0], []).append(bits[1])
                else:table[bits[0]] = bits[1]
    _mime[key] = (literal, ext, other, parents, aliases)
    return _mime[key]


def mime_of(path, env=None):
    """The type of a file: a folder is inode/directory; else by name (the MIME database's globs, then Python's table), else by
    its first bytes (plain text, or application/octet-stream; an empty file is application/x-zerosize)."""
    p = Path(path)
    if p.is_dir():return 'inode/directory'
    name = p.name;literal, ext, other, _, aliases = _mime_db(env)
    found = literal.get(name) or literal.get(name.lower())
    if found:return aliases.get(found[1], found[1])
    parts = name.split('.')
    for i in range(1, len(parts)):
        k = '.'.join(parts[i:])
        hit = ext.get(k) or ext.get(k.lower())
        if hit:return aliases.get(hit[1], hit[1])
    best = None
    for weight, mime, glob, cs in other:
        if (fnmatch.fnmatchcase(name, glob) if cs else fnmatch.fnmatchcase(name.lower(), glob.lower())) and (best is None or weight > best[0]):best = (weight, mime)
    if best:return aliases.get(best[1], best[1])
    guessed, _ = mimetypes.guess_type(name, strict=False)
    if guessed:return aliases.get(guessed, guessed)
    try:
        with open(p, 'rb') as stream:head = stream.read(4096)
    except OSError:return 'application/octet-stream'
    if not head:return 'application/x-zerosize'
    if b'\0' not in head:
        try:head.decode('utf-8');return 'text/plain'
        except UnicodeDecodeError:pass
    return 'application/octet-stream'


def canonical(mime, env=None):
    return _mime_db(env)[4].get(mime, mime)


def parents(mime, env=None):
    """The types this one is a kind of, nearest first (subclasses, then text/plain for any text/*), without itself."""
    table = _mime_db(env)[3];out = [];todo = [canonical(mime, env)]
    while todo:
        t = todo.pop(0)
        for p in table.get(t, []) + (['text/plain'] if t.startswith('text/') and t != 'text/plain' else []):
            p = canonical(p, env)
            if p != mime and p not in out:out.append(p);todo.append(p)
    return out


def type_words(mime, name=''):
    """A kind of file in the owner's words: 'PDF files'; else by the file's extension ('.kicad_pro files'); else by the
    type's own last word."""
    if mime in TYPE_WORDS:return TYPE_WORDS[mime]
    suffix = Path(name).suffix if name else ''
    if suffix:return suffix.lower() + ' files'
    sub = mime.split('/', 1)[-1]
    for prefix in ('x-', 'vnd.'):
        if sub.startswith(prefix):sub = sub[len(prefix):]
    return sub.replace('+xml', '').upper() + ' files' if len(sub) <= 5 else sub + ' files'


# ---- mimeapps.list ----------------------------------------------------------------------------------------------------------
def mimeapps_files(env=None):
    """The mimeapps.list files in the specification's order, most important first: (path, is the owner's own)."""
    ours = desktops(env);out = []
    for base, mine in [(config_home(env), True)] + [(d, False) for d in config_dirs(env)]:
        out += [(base / ('%s-mimeapps.list' % d), mine) for d in ours] + [(base / 'mimeapps.list', mine)]
    for base, mine in [(data_home(env), True)] + [(d, False) for d in data_dirs(env)]:
        out += [(base / 'applications' / ('%s-mimeapps.list' % d), mine) for d in ours] + [(base / 'applications' / 'mimeapps.list', mine)]
    return out


def _lists(env=None):
    """[(path, {'default': {type: [ids]}, 'added': {...}, 'removed': {...}})] for the files that are there, most important
    first, and the old defaults.list files last (defaults only)."""
    out = []
    for path, _ in mimeapps_files(env):
        if not path.is_file():continue
        groups = read_groups(path)
        out.append((path, {'default': {k: string_list(v) for k, v in groups.get('Default Applications', {}).items()},
                           'added': {k: string_list(v) for k, v in groups.get('Added Associations', {}).items()},
                           'removed': {k: string_list(v) for k, v in groups.get('Removed Associations', {}).items()}}))
    for base in [data_home(env)] + data_dirs(env):
        path = base / 'applications' / 'defaults.list'
        if path.is_file():
            groups = read_groups(path)
            out.append((path, {'default': {k: string_list(v) for k, v in groups.get('Default Applications', {}).items()}, 'added': {}, 'removed': {}}))
    return out


def _usable(catalog, ident):
    app = catalog.get(ident)
    return app is not None and app.available


def default_for(mime, catalog=None, env=None, parents_too=True):
    """(the default app's id or None, the file that says so or ''): the first installed app named for the type in
    [Default Applications], file by file in order, not removed by [Removed Associations] in that file or a more
    important one; else the same for its alias and its parent types."""
    catalog = catalog or scan(env);lists = _lists(env)
    wanted = [mime] + ([canonical(mime, env)] if canonical(mime, env) != mime else []) + (parents(mime, env) if parents_too else [])
    for t in wanted:
        removed = set()
        for path, table in lists:
            removed |= set(table['removed'].get(t, []))
            for ident in table['default'].get(t, []):
                if ident not in removed and _usable(catalog, ident):return ident, str(path)
    return None, ''


def apps_for(mime, catalog=None, env=None):
    """'Open with': [(app, how)] for a type, the default first ('default'), then [Added Associations] ('added'), then the apps
    whose MimeType names it ('declared'), then those for the types it is a kind of ('for <parent>'). An app removed by
    [Removed Associations] for the type is left out unless it is the default."""
    catalog = catalog or scan(env);lists = _lists(env);mime_c = canonical(mime, env)
    removed = set()
    for _, table in lists:removed |= set(table['removed'].get(mime, [])) | set(table['removed'].get(mime_c, []))
    out = [];seen = set()

    def take(ident, how):
        if ident in seen or not _usable(catalog, ident):return
        seen.add(ident);out.append((catalog.get(ident), how))
    default, _ = default_for(mime, catalog, env)
    if default:take(default, 'default')
    for _, table in lists:
        for ident in table['added'].get(mime, []) + table['added'].get(mime_c, []):
            if ident not in removed:take(ident, 'added')
    every = catalog.every()
    for app in every:
        types = {canonical(t, env) for t in app.mime_types}
        if mime_c in types and app.id not in removed:take(app.id, 'declared')
    for parent in parents(mime, env):
        for app in every:
            if parent in {canonical(t, env) for t in app.mime_types} and app.id not in removed:take(app.id, 'for ' + parent)
    return out


def _set_list(lines, section, key, value):
    """lines with `key=value` in [section] (value None takes the key out); the section is added at the end when missing."""
    out = [];inside = False;done = False;found_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            if inside and not done and value is not None:out.append('%s=%s' % (key, value));done = True
            inside = stripped[1:-1] == section;found_section = found_section or inside
            out.append(line);continue
        if inside and '=' in stripped and not stripped.startswith('#') and stripped.partition('=')[0].strip() == key:
            if not done and value is not None:out.append('%s=%s' % (key, value));done = True
            continue
        out.append(line)
    if inside and not done and value is not None:out.append('%s=%s' % (key, value));done = True
    if not found_section and value is not None:
        while out and not out[-1].strip():out.pop()
        if out:out.append('')
        out += ['[%s]' % section, '%s=%s' % (key, value)]
    return out


def set_default(mime, ident, env=None, catalog=None):
    """The owner's default program for a type, in the owner's own mimeapps.list (written whole, then put in place), then read
    back: dict(type, id, was, was_effective, now, file, verified). An empty id takes the owner's line back out."""
    if not TYPE.match(mime or ''):raise ValueError('APPS_TYPE: not a kind of file: %r' % str(mime)[:80])
    catalog = catalog or scan(env)
    if ident:
        if not DESKTOP_ID.match(ident):raise ValueError('APPS_ID: not an app: %r' % str(ident)[:80])
        app = catalog.get(ident)
        if app is None:raise ValueError('APPS_UNKNOWN: %s is not installed here' % ident)
        if not app.available:raise ValueError('APPS_UNAVAILABLE: ' + app.reason)
    target = config_home(env) / 'mimeapps.list'
    try:text = target.read_text(encoding='utf-8')
    except FileNotFoundError:text = ''
    except (OSError, UnicodeDecodeError) as exc:raise ValueError('APPS_UNREADABLE: %s: %s' % (target, exc))
    was = string_list(read_groups(target).get('Default Applications', {}).get(mime, '')) if text else []
    was_effective, _ = default_for(mime, catalog, env, parents_too=False)
    lines = text.splitlines()
    if ident:
        groups = read_groups(target) if text else {}
        added = [ident] + [x for x in string_list(groups.get('Added Associations', {}).get(mime, '')) if x != ident]
        removed = [x for x in string_list(groups.get('Removed Associations', {}).get(mime, '')) if x != ident]
        lines = _set_list(lines, 'Default Applications', mime, ident)
        lines = _set_list(lines, 'Added Associations', mime, ';'.join(added) + ';')
        lines = _set_list(lines, 'Removed Associations', mime, (';'.join(removed) + ';') if removed else None)
    else:
        lines = _set_list(lines, 'Default Applications', mime, None)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, staged = tempfile.mkstemp(prefix='.mimeapps-', dir=str(target.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:out.write('\n'.join(lines).rstrip('\n') + '\n')
        try:os.chmod(staged, 0o644)
        except OSError:pass
        os.replace(staged, target)
    finally:
        if os.path.exists(staged):os.unlink(staged)
    now, said_by = default_for(mime, catalog, env, parents_too=False)
    verified = (now == ident) if ident else (string_list(read_groups(target).get('Default Applications', {}).get(mime, '')) == [])
    return {'type': mime, 'id': ident, 'was': was[0] if was else None, 'was_effective': was_effective, 'now': now, 'said_by': said_by,
            'file': str(target), 'verified': bool(verified),
            'words': (('%s now open with %s.' % (type_words(mime), catalog.get(ident).name)) if ident and verified else
                      ('%s: your own choice is taken out.' % type_words(mime)) if not ident and verified else
                      'Written, but %s still says otherwise.' % (said_by or 'another file'))}


# ---- Graphite's own list (Apps ⊕) -------------------------------------------------------------------------------------------
def pins_path(env=None):
    env = _env(env);named = env.get('ARC1_WORKBENCH_CONFIG_HOME')
    if named:return Path(named) / PINS_FILE
    return config_home(env) / 'arc1-workbench' / PINS_FILE


def read_pins(env=None):
    try:value = json.loads(pins_path(env).read_text(encoding='utf-8'))
    except (OSError, ValueError):return []
    rows = value.get('pins') if isinstance(value, dict) else None
    return [r for r in (rows or []) if isinstance(r, dict) and isinstance(r.get('key'), str)]


def _write_pins(rows, env=None):
    path = pins_path(env);path.parent.mkdir(parents=True, exist_ok=True)
    fd, staged = tempfile.mkstemp(prefix='.apps-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:json.dump({'schema': PINS_SCHEMA, 'pins': rows}, out, indent=1, ensure_ascii=False)
        os.replace(staged, path)
    finally:
        if os.path.exists(staged):os.unlink(staged)


def pin_app(row, catalog=None, env=None):
    """The App a pin stands for: the entry it names (None when it is gone), or the owner's command as an App ('pin:...')."""
    if row.get('id'):
        app = (catalog or scan(env)).get(row['id'])
        return app
    argv = tuple(str(a) for a in row.get('argv') or ())
    app = App(id=row['key'], path='', name=str(row.get('name') or (argv[0] if argv else 'Command')), comment='A command you put on the list',
              group='Yours', kind='pin', argv=argv, terminal=bool(row.get('terminal')))
    app.takes = takes([(a, False) for a in argv])
    found = which(argv[0], env) if argv else None
    if not argv:app.available, app.reason = False, 'There is no command.'
    elif Path(argv[0]).name in NEVER:app.available, app.reason = False, 'Graphite never starts a program through %s.' % Path(argv[0]).name
    elif found is None:app.available, app.reason = False, '%s is not installed on this computer.' % argv[0]
    else:app.program = found
    return app


def pins(catalog=None, env=None):
    """[(pin row, App or None)] in the order the owner put them on the list."""
    catalog = catalog or scan(env)
    return [(row, pin_app(row, catalog, env)) for row in read_pins(env)]


def pin(ident='', name='', command_line='', env=None, catalog=None):
    """Put an entry (by id) or a command (with its name) on Graphite's own list. Returns the pin row."""
    rows = read_pins(env)
    if ident:
        catalog = catalog or scan(env)
        if catalog.get(ident) is None:raise ValueError('APPS_UNKNOWN: %s is not installed here' % ident)
        row = {'key': 'entry:' + ident, 'id': ident}
    else:
        name = str(name or '').strip()
        try:parts = split_exec(str(command_line or '').strip())
        except ValueError as exc:raise ValueError('APPS_COMMAND: the command cannot be read: %s' % exc)
        if not parts:raise ValueError('APPS_COMMAND: there is no command')
        if any(q and '%' in a for a, q in parts):raise ValueError('APPS_COMMAND: a file code inside quotes would be read by a shell; take the quotes away')
        argv = [a for a, _ in parts]
        if Path(argv[0]).name in NEVER:raise ValueError('APPS_COMMAND: Graphite never starts a program through %s' % Path(argv[0]).name)
        if which(argv[0], env) is None:raise ValueError('APPS_COMMAND: %s is not installed on this computer' % argv[0])
        row = {'key': 'pin:' + hashlib.sha256(json.dumps(argv).encode('utf-8')).hexdigest()[:16], 'name': name or Path(argv[0]).name, 'argv': argv}
    rows = [r for r in rows if r['key'] != row['key']] + [row]
    _write_pins(rows, env)
    return row


def unpin(key, env=None):
    rows = read_pins(env);kept = [r for r in rows if r['key'] != key]
    if len(kept) == len(rows):raise ValueError('APPS_NOT_PINNED: %s is not on your list' % str(key)[:80])
    _write_pins(kept, env)
    return {'key': key, 'left': len(kept)}


def find_app(ident, catalog=None, env=None):
    """An app by its id, or a pinned command by its key ('pin:...')."""
    catalog = catalog or scan(env)
    if str(ident).startswith('pin:'):
        row = next((r for r in read_pins(env) if r['key'] == ident), None)
        return pin_app(row, catalog, env) if row else None
    return catalog.get(ident)


# ---- the Kernel's operations ------------------------------------------------------------------------------------------------
TEXT = {'type': 'string', 'maxLength': 4096}
FIELDS = {
    'apps.list': ({'query': {'type': 'string', 'maxLength': 200}, 'every': {'type': 'boolean'}}, []),
    'apps.for': ({'path': TEXT, 'type': {'type': 'string', 'maxLength': 255}}, []),
    'apps.open': ({'id': {'type': 'string', 'minLength': 1, 'maxLength': 300}, 'files': {'type': 'array', 'items': TEXT},
                   'urls': {'type': 'array', 'items': {'type': 'string', 'maxLength': 4096}}}, ['id']),
    'apps.default': ({'type': {'type': 'string', 'minLength': 3, 'maxLength': 255}, 'id': {'type': 'string', 'maxLength': 300}}, ['type', 'id']),
    'apps.pin': ({'id': {'type': 'string', 'maxLength': 300}, 'name': {'type': 'string', 'maxLength': 120},
                  'command': {'type': 'string', 'maxLength': 2000}}, []),
    'apps.unpin': ({'key': {'type': 'string', 'minLength': 1, 'maxLength': 320}}, ['key']),
}
SCOPES = {'apps.list': 'read', 'apps.for': 'read', 'apps.open': 'execute', 'apps.default': 'approve', 'apps.pin': 'execute', 'apps.unpin': 'execute'}


def listing(query='', every=False, env=None):
    catalog = scan(env)
    apps = catalog.search(query, every=every)
    rows = [dict(a.as_dict(), icon_file=icon_path(a.icon, 32, env)) for a in apps];chosen = {a.id for a in apps}
    groups = []
    for words, members in catalog.groups():
        ids = [a.id for a in members if a.id in chosen]
        if ids:groups.append({'group': words, 'ids': ids})
    pinned = [{'key': row['key'], 'id': row.get('id'), 'name': app.name if app else row.get('name') or row.get('id'),
               'available': bool(app and app.available), 'reason': (app.reason if app else 'its entry is gone'),
               'app': dict(app.as_dict(), icon_file=icon_path(app.icon, 32, env)) if app else None} for row, app in pins(catalog, env)]
    hidden = sum(1 for a in catalog.apps.values() if not a.listed)
    return {'schema': SCHEMA, 'apps': rows, 'groups': groups, 'pins': pinned, 'not_listed': hidden, 'folders': list(catalog.dirs),
            'desktops': desktops(env)}


def for_file(path='', mime='', env=None):
    if not path and not mime:raise ValueError('APPS_ASK: give a path or a type')
    name = ''
    if path:
        p = Path(path)
        if not p.exists():raise ValueError('APPS_NOT_FOUND: %s is not there' % p.name)
        mime = mime_of(p, env);name = p.name
    if not TYPE.match(mime):raise ValueError('APPS_TYPE: not a kind of file: %r' % mime[:80])
    catalog = scan(env);default, said_by = default_for(mime, catalog, env)
    found = apps_for(mime, catalog, env)
    return {'schema': SCHEMA, 'type': mime, 'words': type_words(mime, name), 'parents': parents(mime, env), 'default': default,
            'said_by': said_by, 'apps': [dict(app.as_dict(), how=how, icon_file=icon_path(app.icon, 32, env)) for app, how in found]}


def dispatch(kernel, op, args, principal):
    """The Kernel's apps.* operations (the scopes are checked by the Kernel before this is called)."""
    if op == 'apps.list':return listing(args.get('query', ''), bool(args.get('every')))
    if op == 'apps.for':return for_file(args.get('path', ''), args.get('type', ''))
    if op == 'apps.open':
        app = find_app(args['id'])
        if app is None:raise ValueError('APPS_UNKNOWN: %s is not installed here' % args['id'][:120])
        files = [str(Path(f)) for f in args.get('files') or []]
        if any(not os.path.isabs(f) for f in files):raise ValueError('APPS_PATH: give whole paths for the files')
        result = launch_app(app, files, args.get('urls') or [])
        return dict(result, id=app.id, name=app.name, schema=SCHEMA, done=result['ok'],
                    verified='started' if result['ok'] else 'not started')
    if op == 'apps.default':return dict(set_default(args['type'], args['id']), schema=SCHEMA)
    if op == 'apps.pin':
        row = pin(args.get('id', ''), args.get('name', ''), args.get('command', ''))
        return {'schema': SCHEMA, 'pin': row}
    if op == 'apps.unpin':return dict(unpin(args['key']), schema=SCHEMA)
    raise ValueError('Unknown apps operation')
