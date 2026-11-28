"""DOS words in the Terminal (Graphite 1.1 W1): a Windows-and-DOS hand types what it knows; Debian runs, and is shown.

PLAN_1.1.md, W1 (e): `dir`, `cd..`, `cd\\`, `cls`, `copy`, `xcopy`, `move`, `del`, `ren`, `md`, `rd`, `type`, `more`, `tree`,
`attrib`, `ver`, `date`, `time`, `set`, `path`, `echo`, `find`, `help`, `exit`, `ipconfig`, `ping`, `tasklist`, `taskkill`,
drive letters (C: is /, the other letters are the mounted drives in order), backslashes and the common switches. Each line
is translated to the Debian command and that command is shown on a line above its output ("dir /s → ls -lR"), so the owner
learns it.

WHAT IS NEVER RUN. `del`, `erase` and `rd /s` go to the bin through the Kernel's files.batch (act delete: your home's own
bin, the freedesktop.org one, with one Undo for all of them); nothing here ever runs rm. `format`, `chkdsk`, `fdisk` and
`diskpart` are explained, never run. Copy, xcopy, move and ren never overwrite unless /y is given (cp -n, mv -n).

WHEN A LINE IS DOS. A word only DOS has (dir, cls, copy, xcopy, move, del, ren, md, rd, attrib, ver, ipconfig, tasklist,
taskkill, path, help, exit, a drive letter) is always DOS. A word Debian has too (echo, find, set, type, more, tree, date,
time, ping, cd, mkdir, rmdir) is DOS only when the line says so: a /switch, a backslash, a drive letter, %NAME%, a quoted
first word for find, a file name for type. Anything else goes to the shell exactly as typed.

The setting (windows_hand.dos_words()): 'on' translates and runs; 'show' shows the Debian command and runs nothing ("show me
only"); 'off' leaves every line to the shell as typed.

translate(line, cwd, drives, which) is pure (tests give the drives and which programs are installed); in_terminal(console,
text) is the Terminal's own use of it (console_qt.Console.run_shell asks it first).
"""
from __future__ import annotations

import glob
import os
import re
import shlex
import shutil
from dataclasses import dataclass, field
from pathlib import Path

ARROW = '\u2192'
# words only DOS has: the line is DOS
DOS_ONLY = frozenset(('dir', 'cls', 'copy', 'xcopy', 'move', 'del', 'erase', 'ren', 'md', 'rd', 'attrib', 'ver', 'ipconfig',
                      'tasklist', 'taskkill', 'path', 'help', 'exit', 'format', 'chkdsk', 'fdisk', 'diskpart', 'findstr'))
# words Debian has as well: DOS only when the line shows it
BOTH = frozenset(('echo', 'find', 'set', 'type', 'more', 'tree', 'date', 'time', 'ping', 'cd', 'chdir', 'mkdir', 'rmdir', 'rename'))
NEVER_RUN = {
    'format': 'format erases a whole drive. On Debian a drive is made new with mkfs (for example mkfs.vfat on the drive\'s '
              'partition), as the system\'s administrator, with the drive not in use. DOS words never run it.',
    'chkdsk': 'chkdsk checks a drive. On Debian that is fsck, run as the system\'s administrator on a drive that is not in use '
              '(for example fsck on the drive\'s partition). DOS words never run it. To see how full the drives are: df -h.',
    'fdisk': 'fdisk changes how a drive is divided. Debian has fdisk too, for the system\'s administrator; DOS words never run it.',
    'diskpart': 'diskpart changes how a drive is divided. On Debian that is fdisk or parted, for the system\'s administrator; '
                'DOS words never run it.',
}
SWITCH = re.compile(r'^/(\?|[a-z](?:[:-]?[a-z])?|pid|im|fi)$', re.I)
DRIVE = re.compile(r'^([A-Za-z]):(.*)$')
VAR = re.compile(r'%([A-Za-z_][A-Za-z0-9_]*)%')
PLAIN = re.compile(r'^[A-Za-z0-9_./*?\[\]+=:,@%^-]+$')
DEBIAN_HELP = {'dir': 'ls', 'copy': 'cp', 'xcopy': 'cp', 'move': 'mv', 'ren': 'mv', 'md': 'mkdir', 'rd': 'rmdir', 'type': 'cat',
               'more': 'more', 'tree': 'tree', 'attrib': 'chmod', 'find': 'grep', 'findstr': 'grep', 'ipconfig': 'ip',
               'ping': 'ping', 'tasklist': 'ps', 'taskkill': 'kill', 'date': 'date', 'time': 'date', 'del': 'gio', 'erase': 'gio'}
HELP_ROWS = (('dir', 'ls -l', 'list a folder'), ('cd.. / cd\\', 'cd .. / cd /', 'up one folder / to the top'),
             ('cls', 'clear', 'clear the Terminal'), ('copy a b', 'cp -n a b', 'copy (never over a file unless /y)'),
             ('xcopy a b /s /e', 'cp -rn a/. b', 'copy a folder and all in it'), ('move a b', 'mv -n a b', 'move'),
             ('del a', 'gio trash a', 'into the bin, with Undo'), ('ren a b', 'mv -n a b', 'rename'),
             ('md a', 'mkdir -p a', 'make a folder'), ('rd a', 'rmdir a', 'take away an empty folder'),
             ('type a', 'cat a', 'show a file'), ('more a', 'more a', 'show a file a page at a time'),
             ('tree', 'tree -d', 'the folders in a tree'), ('attrib +r a', 'chmod a-w a', 'read-only'),
             ('ver', 'uname -sr', 'the system\'s version'), ('date / time', 'date', 'today and the time'),
             ('set', 'env', 'the settings of this Terminal'), ('path', 'echo $PATH', 'where programs are found'),
             ('echo %HOME%', 'echo $HOME', 'say something, or a setting'), ('find "x" a', 'grep -F x a', 'lines that hold x'),
             ('ipconfig', 'ip -brief address', 'this computer\'s network addresses'), ('ping host', 'ping -c 4 host', 'is it there'),
             ('tasklist', 'ps -e', 'what runs'), ('taskkill /pid 12', 'kill 12', 'stop a program'),
             ('C: D: E:', 'cd / and the drives', 'C: is the top of the computer; D: on are the drives plugged in'),
             ('exit', '', 'close the Terminal'))


@dataclass
class Said:
    """One DOS line, translated. kind: run (a Debian command), cd, cls, trash, env, help, explain, exit."""
    dos: str
    kind: str
    command: str = ''          # the Debian command, as shown
    run: str = ''              # what the shell runs (the command itself, always, for kind run)
    words: str = ''            # plain words: what it does, or why it is not run
    target: str = ''           # cd: the folder
    paths: list = field(default_factory=list)   # trash: the patterns, as given (translated)
    recursive: bool = False    # trash: del /s
    ask: bool = False          # trash: *.* without /q asks first
    env: dict = field(default_factory=dict)     # env: NAME -> value

    def shown(self):
        """The line above the output: 'dir /s → ls -lR'."""
        right = self.command or ('explained, not run' if self.kind == 'explain' else self.kind)
        return '%s %s %s' % (self.dos.strip(), ARROW, right)


# ---- the drives ---------------------------------------------------------------------------------------------------------------
def _unescape(text):
    return re.sub(r'\\([0-7]{3})', lambda m: chr(int(m.group(1), 8)), text)


def drives(mounts=None):
    """{'C': '/', 'D': the first mounted drive, ...}: the drives mounted under /media, /run/media or /mnt, in the order they
    were mounted (/proc/mounts). `mounts` is that file's text, for tests."""
    if mounts is None:
        try:mounts = Path('/proc/mounts').read_text(encoding='utf-8', errors='replace')
        except OSError:
            mounts = ''
    out = {'C': '/'};letter = ord('D')
    for line in mounts.splitlines():
        parts = line.split()
        if len(parts) < 2:continue
        point = _unescape(parts[1])
        if not point.startswith(('/media/', '/run/media/', '/mnt/')) or point in out.values():continue
        if letter > ord('Z'):break
        out[chr(letter)] = point;letter += 1
    return out


def drive_of(path, places):
    """The letter whose place holds `path` (the longest), 'C' for anything else."""
    best, size = 'C', 0
    for letter, place in places.items():
        if letter != 'C' and (str(path) == place or str(path).startswith(place.rstrip('/') + '/')) and len(place) > size:best, size = letter, len(place)
    return best


# ---- words ------------------------------------------------------------------------------------------------------------------
def split(line):
    """DOS words: whitespace apart, "quoted words" kept whole. [(text, quoted)]."""
    out, word, quoted, inside, any_quote = [], '', False, False, False
    for ch in line:
        if ch == '"':inside = not inside;any_quote = True;continue
        if ch.isspace() and not inside:
            if word or any_quote:out.append((word, any_quote))
            word, any_quote = '', False;continue
        word += ch
    if word or any_quote:out.append((word, any_quote))
    return out


def q(text):
    """One word for the shell: as it is when it is plain (a pattern keeps its * and ?), quoted when it is not."""
    if text and PLAIN.match(text):return text
    if text.startswith('~/') and PLAIN.match(text[2:] or 'x'):return text
    return shlex.quote(text)


def to_path(text, cwd, places):
    """A DOS path as Debian's: C:\\x is /x, D:\\x the first drive's x, \\x the top of the drive you are on, a\\b is a/b."""
    text = text.replace('\\', '/')
    if text in ('*.*',):return '*'
    if text.endswith('/*.*'):text = text[:-3] + '*'
    m = DRIVE.match(text)
    if m and len(m.group(1)) == 1:
        place = places.get(m.group(1).upper())
        if place is None:raise LookupError(m.group(1).upper())
        rest = m.group(2).lstrip('/')
        if not rest:return place
        return place.rstrip('/') + '/' + rest
    if text.startswith('/'):
        here = places.get(drive_of(cwd, places), '/') if cwd is not None else '/'
        if here == '/' or text == '/':return here if text == '/' else text
        return here.rstrip('/') + text
    return text


def _switches(words):
    """(the switches, lowercased without their slash, and the other words) of a command's words."""
    sw, rest = [], []
    for text, quoted in words:
        if not quoted and text.startswith('/') and len(text) > 1:
            pieces = re.findall(r'/[^/]+', text)
            if pieces and all(SWITCH.match(p) for p in pieces):
                sw += [p[1:].lower() for p in pieces];continue
        rest.append((text, quoted))
    return sw, rest


def _first(line):
    """The command word and what follows, with DOS's glued forms parted: cd.. cd\\ dir/s."""
    stripped = line.strip()
    m = re.match(r'^(cd|chdir)(\.\.?|\\.*)$', stripped.split(' ')[0], re.I)
    if m:return m.group(1).lower(), (m.group(2) + stripped[len(m.group(0)):]).strip()
    m = re.match(r'^([A-Za-z]+)(/.*)?$', stripped.split(' ')[0])
    head = stripped.split(' ')[0]
    if m and m.group(2) and m.group(1).lower() in DOS_ONLY | BOTH:return m.group(1).lower(), (m.group(2) + stripped[len(head):]).strip()
    return head.lower(), stripped[len(head):].strip()


def _marked(word, rest):
    """Whether a word Debian has too is used the DOS way here."""
    words = split(rest)
    sw, _ = _switches(words)
    if re.search(r'>\s*nul\b', rest, re.I):return True      # > nul is DOS's own nothing
    if sw or '\\' in rest or VAR.search(rest) or any(DRIVE.match(t) and len(t) >= 2 and t[1] == ':' for t, _ in words):return True
    if word == 'find':return bool(words) and words[0][1]
    if word == 'type':return bool(words) and all(('.' in t or os.sep in t) for t, _ in words)
    if word == 'set':return not words or '=' in rest or not rest.startswith(('-', '+'))
    if word in ('date', 'time'):return not words or bool(re.match(r'\d', rest))      # alone, or a new date or time
    if word == 'echo':return rest.strip().lower() in ('.', 'off', 'on') or rest.startswith('.')
    if word == 'ping':return bool(words) and not any(t.startswith('-') and t.lower() not in ('-t', '-n', '-l', '-4', '-6', '-w') for t, _ in words)
    if word == 'more':return '<' in rest
    return False


def is_dos(line):
    """Whether this line is DOS words (see the module's note)."""
    for part in _pipeline(line):
        word, rest = _first(part)
        if DRIVE.match(word) and word.endswith(':') and len(word) == 2 and not rest:return True
        if word in DOS_ONLY:return True
        if word in ('cd', 'chdir') and (rest.startswith(('.', '\\')) and part.strip().lower().startswith(('cd.', 'cd\\', 'chdir.', 'chdir\\')) or _marked(word, rest)):return True
        if word in BOTH and word not in ('cd', 'chdir') and _marked(word, rest):return True
    return False


def _pipeline(line):
    """The line's parts between unquoted bars."""
    parts, word, inside = [], '', False
    for ch in line:
        if ch == '"':inside = not inside
        if ch == '|' and not inside:parts.append(word);word = '';continue
        word += ch
    parts.append(word)
    return [p for p in parts]


def _redirect(words, cwd, places):
    """A redirect at the end ('> nul', '>> log.txt'): its Debian words, and the words before it."""
    out = []
    for n, (text, quoted) in enumerate(words):
        if not quoted and text in ('>', '>>', '<') and n + 1 < len(words):
            target = words[n + 1][0]
            target = '/dev/null' if target.lower() == 'nul' else q(to_path(target, cwd, places))
            return words[:n], ' %s %s' % (text, target) + ''.join(' ' + w for w, _ in words[n + 2:])
        if not quoted and text.startswith(('>', '<')) and len(text) > 1 and text not in ('>>',):
            sign = '>>' if text.startswith('>>') else text[0]
            target = text[len(sign):];target = '/dev/null' if target.lower() == 'nul' else q(to_path(target, cwd, places))
            return words[:n], ' %s %s' % (sign, target)
        out.append((text, quoted))
    return out, ''


# ---- each word ----------------------------------------------------------------------------------------------------------------
def translate(line, cwd=None, places=None, which=shutil.which):
    """The Said for one line of DOS words, or None when it is not DOS (the shell takes it as typed)."""
    if not line or not line.strip() or not is_dos(line):return None
    places = drives() if places is None else places
    parts = _pipeline(line)
    if len(parts) > 1:
        said = [_one(p, cwd, places, which, piped=True) for p in parts]
        if any(s.kind != 'run' for s in said):
            return Said(line, 'explain', words='%s cannot be one step of a line joined with |; type it on its own.' % next(s.dos.strip() for s in said if s.kind != 'run'))
        command = ' | '.join(s.command for s in said)
        return Said(line, 'run', command, command)
    return _one(line, cwd, places, which)


def _run(dos, command, words=''):
    return Said(dos, 'run', command, command, words)


def _one(line, cwd, places, which, piped=False):
    word, rest = _first(line)
    dos = line.strip()
    try:
        if DRIVE.match(word) and word.endswith(':') and len(word) == 2 and not rest:
            return Said(dos, 'cd', 'cd ' + q(to_path(word, cwd, places)), target=to_path(word, cwd, places))
        words = split(rest)
        sw, args = _switches(words)
        args, tail = _redirect(args, cwd, places)
        paths = [to_path(t, cwd, places) for t, _ in args]
        if '?' in sw and word not in ('help',):
            debian = DEBIAN_HELP.get(word)
            if debian:return _run(dos, '%s --help' % debian)
            return Said(dos, 'help', words=_help_words(word))
        if word in NEVER_RUN:return Said(dos, 'explain', words=NEVER_RUN[word])
        doer = DOERS.get(word)
        if doer is None:return _run(dos, dos)      # a part of a DOS line that is Debian's already (sort, grep): as typed
        said = doer(dos, sw, args, paths, cwd, places, which)
        if tail and said.kind == 'run':said.command += tail;said.run += tail
        return said
    except LookupError as exc:
        known = ', '.join('%s: (%s)' % (k, v) for k, v in sorted(places.items()))
        return Said(dos, 'explain', words='There is no drive %s: here. The drives are %s.' % (exc.args[0], known))


def _dir(dos, sw, args, paths, cwd, places, which):
    s = 's' in sw;b = 'b' in sw;w = 'w' in sw
    a = any(x.startswith('a') for x in sw)
    target = ' '.join(q(p) for p in paths)
    if s and b:
        pattern = next((p for p in paths if any(c in p for c in '*?')), '')
        where = next((q(p) for p in paths if not any(c in p for c in '*?')), '.')
        return _run(dos, 'find %s%s' % (where, (' -name ' + shlex.quote(Path(pattern).name)) if pattern else ''))
    if 'ad' in sw or 'a:d' in sw:return _run(dos, 'ls -ld %s' % ((target.rstrip('/') + '/*/') if target else '*/'))
    if 'ah' in sw or 'a:h' in sw:return _run(dos, 'ls -ld %s' % ((target.rstrip('/') + '/.*') if target else '.*'))
    flags = '1' if b else '' if w else 'l'
    if a:flags += 'a'
    order = next((x for x in sw if x.startswith('o')), '')
    flags += {'od': 'tr', 'o:d': 'tr', 'o-d': 't', 'os': 'Sr', 'o:s': 'Sr', 'o-s': 'S', 'o-n': 'r'}.get(order, '')
    if s:flags += 'R'
    return _run(dos, ('ls -%s' % flags if flags else 'ls') + (' ' + target if target else ''))


def _cd(dos, sw, args, paths, cwd, places, which):
    if not paths:return _run(dos, 'pwd')
    target = paths[0]
    if target == '':target = '/'
    return Said(dos, 'cd', 'cd ' + q(target), target=target)


def _cls(dos, *_):
    return Said(dos, 'cls', 'clear')


def _copy(dos, sw, args, paths, cwd, places, which):
    if any('+' in t for t, _ in args):
        return Said(dos, 'explain', words='copy with + joins files into one. On Debian: cat a b > c (it writes c over); type it that way if you mean it.')
    if not paths:return Said(dos, 'explain', words='copy needs a file: copy a.txt b.txt, or copy a.txt into a folder.')
    dest = paths[1:] or ['.']
    return _run(dos, '%s %s %s' % ('cp' if 'y' in sw else 'cp -n', q(paths[0]), ' '.join(q(p) for p in dest)),
                '' if 'y' in sw else 'a file already there is never written over (/y writes over it)')


def _xcopy(dos, sw, args, paths, cwd, places, which):
    if not paths:return Said(dos, 'explain', words='xcopy needs a folder: xcopy docs backup /s /e.')
    src = paths[0];dest = paths[1] if len(paths) > 1 else '.'
    deep = 's' in sw or 'e' in sw
    over = 'y' in sw
    if deep and not any(c in src for c in '*?'):
        return _run(dos, 'cp -r%s %s %s' % ('' if over else 'n', q(src.rstrip('/') + '/.'), q(dest)))
    return _run(dos, 'cp%s %s %s' % ('' if over else ' -n', q(src), q(dest)))


def _move(dos, sw, args, paths, cwd, places, which):
    if len(paths) < 2:return Said(dos, 'explain', words='move needs what and where: move a.txt D:\\.')
    return _run(dos, '%s %s' % ('mv' if 'y' in sw else 'mv -n', ' '.join(q(p) for p in paths)))


def _del(dos, sw, args, paths, cwd, places, which):
    if not paths:return Said(dos, 'explain', words='del needs a file: del a.txt, or del *.tmp.')
    everything = any(Path(p).name in ('*', '*.*') for p in paths)
    shown = 'gio trash ' + ' '.join(q(p) for p in paths)
    return Said(dos, 'trash', shown, paths=list(paths), recursive='s' in sw, ask=everything and 'q' not in sw,
                words='into the bin, with Undo; nothing is deleted for good')


def _ren(dos, sw, args, paths, cwd, places, which):
    if len(paths) != 2:return Said(dos, 'explain', words='ren needs the old name and the new: ren a.txt b.txt.')
    old, new = paths
    m1, m2 = re.fullmatch(r'\*\.([^*?/]+)', old), re.fullmatch(r'\*\.([^*?/]+)', new)
    if m1 and m2:
        command = 'for f in *.%s; do mv -n -- "$f" "${f%%.%s}.%s"; done' % (m1.group(1), m1.group(1), m2.group(1))
        return _run(dos, command)
    if any(c in old + new for c in '*?'):return Said(dos, 'explain', words='ren with patterns works here for *.a *.b only; Debian\'s rename takes the rest.')
    return _run(dos, 'mv -n %s %s' % (q(old), q(new)))


def _md(dos, sw, args, paths, cwd, places, which):
    if not paths:return Said(dos, 'explain', words='md needs a name: md Letters.')
    return _run(dos, 'mkdir -p ' + ' '.join(q(p) for p in paths))


def _rd(dos, sw, args, paths, cwd, places, which):
    if not paths:return Said(dos, 'explain', words='rd needs a folder: rd Old.')
    if 's' in sw:
        return Said(dos, 'trash', 'gio trash ' + ' '.join(q(p) for p in paths), paths=list(paths), ask='q' not in sw,
                    words='the folder and all in it into the bin, with Undo; nothing is deleted for good')
    return _run(dos, 'rmdir ' + ' '.join(q(p) for p in paths), 'only an empty folder is taken away')


def _type(dos, sw, args, paths, cwd, places, which):
    if not paths:return Said(dos, 'explain', words='type needs a file: type notes.txt.')
    return _run(dos, 'cat ' + ' '.join(q(p) for p in paths))


def _more(dos, sw, args, paths, cwd, places, which):
    return _run(dos, 'more' + ''.join(' ' + q(p) for p in paths))


def _tree(dos, sw, args, paths, cwd, places, which):
    where = ' '.join(q(p) for p in paths)
    files = 'f' in sw
    if which('tree'):
        return _run(dos, 'tree%s%s%s' % ('' if files else ' -d', ' --charset=ascii' if 'a' in sw else '', (' ' + where) if where else ''))
    return _run(dos, 'find %s%s' % (where or '.', '' if files else ' -type d'))


def _attrib(dos, sw, args, paths, cwd, places, which):
    signs = [t for t, _ in args if re.fullmatch(r'[+-][rhsa]', t, re.I)]
    files = [to_path(t, cwd, places) for t, _ in args if t not in signs]
    if not signs:return _run(dos, 'ls -l' + ''.join(' ' + q(p) for p in files))
    sign = signs[0].lower()
    if sign in ('+h', '-h'):
        return Said(dos, 'explain', words='On Debian a hidden file is one whose name starts with a dot: mv notes.txt .notes.txt hides it. Not done here.')
    if sign in ('+s', '-s', '+a', '-a'):
        return Said(dos, 'explain', words='Debian has no system or archive mark on a file; who may read and change it is what chmod sets.')
    if not files:return Said(dos, 'explain', words='attrib %s needs a file.' % sign)
    return _run(dos, '%s %s' % ('chmod a-w' if sign == '+r' else 'chmod u+w', ' '.join(q(p) for p in files)))


def _ver(dos, *_):
    return _run(dos, 'cat /etc/debian_version && uname -sr')


def _date(dos, sw, args, paths, cwd, places, which):
    if args:return Said(dos, 'explain', words='Setting the date is the system\'s: timedatectl set-time, which asks for the system\'s permission. Not done from DOS words.')
    return _run(dos, "date '+%A %d %B %Y'")


def _time(dos, sw, args, paths, cwd, places, which):
    if args:return Said(dos, 'explain', words='Setting the time is the system\'s: timedatectl set-time, which asks for the system\'s permission. Not done from DOS words.')
    return _run(dos, 'date +%H:%M' if 't' in sw else 'date +%H:%M:%S')


def _set(dos, sw, args, paths, cwd, places, which):
    text = ' '.join(t for t, _ in args)
    if not text:return _run(dos, 'env | sort')
    if '=' in text:
        name, _, value = text.partition('=');name = name.strip()
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):return Said(dos, 'explain', words='A setting\'s name is letters, digits and _.')
        value = VAR.sub(lambda m: '$' + m.group(1), value)
        return Said(dos, 'env', 'export %s=%s' % (name, q(value)), env={name: value}, words='set for the commands of this Terminal')
    return _run(dos, 'env | grep -i ' + shlex.quote('^' + text))


def _path(dos, sw, args, paths, cwd, places, which):
    text = ' '.join(t for t, _ in args)
    if not text:return _run(dos, 'echo $PATH')
    if text.strip() == ';':return Said(dos, 'explain', words='path ; would leave this Terminal with no programs to find; not done.')
    value = ':'.join(to_path(p, cwd, places) for p in text.split(';') if p)
    value = VAR.sub(lambda m: '$' + m.group(1), value)
    return Said(dos, 'env', 'export PATH=%s' % value, env={'PATH': value}, words='set for the commands of this Terminal')


def _echo(dos, sw, args, paths, cwd, places, which):
    raw = dos[4:]
    if raw.strip().lower() in ('off', 'on'):return Said(dos, 'explain', words='Debian\'s shell does not repeat the commands it runs, so there is no echo off.')
    if raw.startswith('.'):return _run(dos, 'echo' + (' ' + raw[1:].strip() if raw[1:].strip() else ''))
    text = VAR.sub(lambda m: '${%s}' % m.group(1), ' '.join(t for t, _ in args))
    return _run(dos, 'echo "%s"' % text.replace('"', '\\"') if '$' in text else 'echo ' + ' '.join(q(t) for t, _ in args))


def _find(dos, sw, args, paths, cwd, places, which):
    if not args:return Said(dos, 'explain', words='find needs the words in quotes: find "invoice" notes.txt.')
    flags = ''.join(f for f, k in (('i', 'i'), ('c', 'c'), ('n', 'n'), ('v', 'v')) if k in sw)
    files = [to_path(t, cwd, places) for t, _ in args[1:]]
    return _run(dos, 'grep -F%s %s%s' % (flags, shlex.quote(args[0][0]), ''.join(' ' + q(p) for p in files)))


def _findstr(dos, sw, args, paths, cwd, places, which):
    fixed = next((s[2:] for s in sw if s.startswith('c:')), None)
    flags = ''.join(f for f, k in (('i', 'i'), ('n', 'n'), ('v', 'v'), ('r', 's')) if k in sw)
    if not args:return Said(dos, 'explain', words='findstr needs the words: findstr invoice *.txt.')
    words = args[0][0];files = [to_path(t, cwd, places) for t, _ in args[1:]]
    return _run(dos, 'grep%s %s%s' % ((' -' + flags) if flags else '', shlex.quote(words), ''.join(' ' + q(p) for p in files)))


def _help(dos, sw, args, paths, cwd, places, which):
    if args:
        word = args[0][0].lower()
        debian = DEBIAN_HELP.get(word)
        if debian:return _run(dos, '%s --help' % debian)
        return Said(dos, 'help', words=_help_words(word))
    return Said(dos, 'help', words=_help_words(''))


def _help_words(word):
    rows = [r for r in HELP_ROWS if not word or r[0].split(' ')[0] == word]
    return '\n'.join('%-18s %-22s %s' % r for r in (rows or HELP_ROWS))


def _exit(dos, *_):
    return Said(dos, 'exit', words='the Terminal closes')


def _ipconfig(dos, sw, args, paths, cwd, places, which):
    if any(s in sw for s in ('release', 'renew')) or any(t.lower() in ('/release', '/renew') for t, _ in args):
        return Said(dos, 'explain', words='A new network address is the network manager\'s: nmcli connection up (the connection\'s name). Not done from DOS words.')
    if any(t.lower() == '/flushdns' for t, _ in args):
        return Said(dos, 'explain', words='On Debian: resolvectl flush-caches, which asks for the system\'s permission. Not done from DOS words.')
    if 'all' in sw or any(t.lower() == '/all' for t, _ in args):return _run(dos, 'ip address')
    return _run(dos, 'ip -brief address')


def _ping(dos, sw, args, paths, cwd, places, which):
    words = [t for t, _ in args];count = '4';forever = False;host = ''
    n = 0
    while n < len(words):
        t = words[n].lower()
        if t == '-t':forever = True
        elif t == '-n' and n + 1 < len(words):count = words[n + 1];n += 1
        elif t in ('-4', '-6'):pass
        elif t in ('-l', '-w') and n + 1 < len(words):n += 1
        else:host = words[n]
        n += 1
    if not host:return Said(dos, 'explain', words='ping needs a name or an address: ping debian.org.')
    if not count.isdigit():count = '4'
    return _run(dos, 'ping %s' % q(host) if forever else 'ping -c %s %s' % (count, q(host)))


def _tasklist(dos, sw, args, paths, cwd, places, which):
    return _run(dos, 'ps -e -o pid,rss,comm --sort=comm')


def _taskkill(dos, sw, args, paths, cwd, places, which):
    words = [t for t, _ in args]
    force = 'f' in sw
    if 'pid' in sw and words and words[0].isdigit():return _run(dos, 'kill%s %s' % (' -9' if force else '', words[0]))
    if 'im' in sw and words:
        name = re.sub(r'\.exe$', '', words[0], flags=re.I)
        return _run(dos, 'pkill%s -x %s' % (' -9' if force else '', q(name)))
    return Said(dos, 'explain', words='taskkill needs /pid and a number, or /im and a name: taskkill /im firefox.exe.')


DOERS = {'dir': _dir, 'cd': _cd, 'chdir': _cd, 'cls': _cls, 'copy': _copy, 'xcopy': _xcopy, 'move': _move, 'del': _del,
         'erase': _del, 'ren': _ren, 'rename': _ren, 'md': _md, 'mkdir': _md, 'rd': _rd, 'rmdir': _rd, 'type': _type,
         'more': _more, 'tree': _tree, 'attrib': _attrib, 'ver': _ver, 'date': _date, 'time': _time, 'set': _set,
         'path': _path, 'echo': _echo, 'find': _find, 'findstr': _findstr, 'help': _help, 'exit': _exit,
         'ipconfig': _ipconfig, 'ping': _ping, 'tasklist': _tasklist, 'taskkill': _taskkill}


# ---- the bin, for del ------------------------------------------------------------------------------------------------------------
def expand(said, cwd):
    """The files a del names, found now in `cwd` (a pattern matched as the shell would; /s through every folder below)."""
    out = []
    for pattern in said.paths:
        base = pattern if os.path.isabs(pattern) else os.path.join(str(cwd), pattern)
        if said.recursive:
            folder, name = os.path.split(base)
            found = sorted(glob.glob(os.path.join(folder, '**', name), recursive=True))
        else:
            found = sorted(glob.glob(base)) if any(c in pattern for c in '*?[') else ([base] if os.path.lexists(base) else [])
        for f in found:
            if said.kind == 'trash' and said.dos.split()[0].lower() in ('del', 'erase') and os.path.isdir(f) and not os.path.islink(f):continue
            if f not in out:out.append(f)
    return out


# ---- in the Terminal ---------------------------------------------------------------------------------------------------------
def in_terminal(console, text, mode=None):
    """console_qt.Console.run_shell asks this first: True when the line was DOS words and is handled here (shown, then run,
    or shown only); False when the shell takes it as typed."""
    from html import escape
    from . import windows_hand
    mode = mode or windows_hand.dos_words()
    if mode == 'off':return False
    cwd = console.working_dir()
    said = translate(text, cwd=cwd)
    if said is None:return False
    console.say('<span style="opacity:0.8;">%s</span>%s' % (escape(said.shown()), ('<br>' + escape(said.words)) if said.words and said.kind != 'help' else ''),
                echo=console.sign_text() + ' ' + text)
    if mode == 'show':
        console.say(escape('Shown only: DOS words are set to "show me only", so nothing was run.'));return True
    if said.kind == 'run':
        inner(console, said.run);return True
    if said.kind == 'cd':
        inner(console, 'cd ' + said.target);return True
    if said.kind == 'cls':
        try:console.output.clear();console.blocks = 0
        except (AttributeError, RuntimeError):pass
        return True
    if said.kind == 'exit':
        for name in ('set_size',):
            if hasattr(console, name):getattr(console, name)(0)
        return True
    if said.kind == 'env':
        env = getattr(console, 'dos_env', None)
        if env is None:env = console.dos_env = {}
        env.update(said.env);return True
    if said.kind == 'help':
        console.say('<pre style="margin:0;">%s</pre>' % escape(said.words));return True
    if said.kind == 'explain':return True
    if said.kind == 'trash':
        files = expand(said, cwd)
        if not files:console.say(escape('Nothing there by that name, so nothing went to the bin (del takes files; rd /s takes a folder).'));return True
        if said.ask:
            console.say('%s %s · %s' % (escape('%d in %s. Put them all in the bin?' % (len(files), cwd)),
                                         console.link('Put them in the bin', lambda: to_bin(console, files)), console.link('not now', lambda: console.say('Nothing was done.'))))
            return True
        to_bin(console, files);return True
    return False


def inner(console, line):
    """The Debian command run as the shell runs any line (its own echo, output and exit), with this Terminal's DOS settings."""
    console._dos_inner = True
    try:console.run_shell(line, extra_env=dict(getattr(console, 'dos_env', None) or {}) or None)
    finally:
        console._dos_inner = False


def to_bin(console, files):
    """del: the files into the bin through the Kernel's batch (files.batch, act delete: your own press), one Undo for all."""
    from html import escape
    kernel = getattr(getattr(console.host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None:console.say(escape('Kas\'s Kernel is not open, so nothing went to the bin.'));return None
    from .engineering_kernel import operator
    answer = kernel.dispatch('files.batch', {'act': 'delete', 'paths': [str(f) for f in files][:1000]}, operator())
    if not answer.get('ok'):
        console.say(escape('Not done: %s' % str((answer.get('error') or {}).get('message') or 'not done')));return answer
    result = answer['result']

    def undo():
        back = kernel.dispatch('files.batch_undo', {'batch': result['batch']}, operator())
        console.say(escape(back['result']['words'] if back.get('ok') else 'Not undone: %s' % (back.get('error') or {}).get('message')))
    console.say('%s %s' % (escape(result['words']), console.link('Undo', undo) if result.get('done') else ''))
    return answer
