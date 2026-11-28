"""The command tool (Graphite 1.1 KS2): any command as an argv, never a shell string, through a classifier.

PLAN_1.1.md, KS2: "Any command as argv, never a shell string, through a classifier that knows which forms only read,
change, destroy, need root or reach the network, and refuses what it cannot classify; reads run sealed and their output is
data; changes show "this will … / the command: …" and wait for the press." Built on KS1 (box_ops: programs found only in
/usr/local/bin, /usr/bin, /bin; a change takes `expect`, the digest of its dry run; a change is never her own step; HALT).

THE LINE. The owner types a line ("run: df -h", in her line or the bar's); tokens() reads it as words the way a shell would
quote them, and refuses, with the exact line shown, anything a shell would do instead of the program: a pipe, ; or &&,
$( ) and backticks, a variable, redirection, a pattern the shell expands (* ? [ ] outside quotes), braces, a backslash, a
comment, a second line, a variable set before the command. `~` and `~/…` at the start of a word mean your home (the tool
expands them itself; no shell does). The model proposes only an argv (a JSON list of words); her dictionary maps plain
words to a known form ("what is using my disk" -> du -xh --max-depth=1 ~). Every argv, from any of the three, goes through
classify() against command_forms.TABLE; what is not there, a flag it does not know, an operand of a kind no form takes:
refused in plain words, never run.

WHAT EACH CLASS DOES.
  read      runs at once, sealed (command_seal: no network, nothing writable but its own scratch folder, only the system's
            folders and the paths it names readable), with no input, in your home, for a bounded time. Its output is data:
            cleaned of control characters, every line through the doorway (doorway.scan), so a line written to an
            assistant is marked and never read as a request; kept in the run's record and shown as data.
  network   a read that reaches another computer (ping -c, dig, host, curl -s, wget -q -O -): it waits for your press
            (nothing leaves the computer without asking), refuses while the network is down, NET says "Kas: <host>" while it
            runs, and its output is data as a read's.
  change    shows "This will … / The command: …", what Undo does, and waits for your press (command.run, execute scope, with
            `expect`, the digest of its plan: what changed since you saw it is refused). It runs sealed too, writable only in
            the folders it was shown to write in, and lands only in your home (box_ops.Reach: never Files, Graphite's own
            records or DELETE's folder). After, it is verified on the disk (the file is there, its size, its mode), and has
            Undo (mkdir, touch, cp -n, mv -n, ln -s, chmod, tar c and x, rename).
  destroy   rm and rmdir are offered as "to the bin" (1.0's bin, home_trash, which Undo takes back); rm itself never runs.
            shred, dd, mkfs, wipefs and the like are refused.
  root      sudo, pkexec, su, apt install, systemctl start ... : refused here, "the system door" (KS3).
A change, a bin or a network read is never her own step: dispatched in her work (a grant's permit, her hand, a principal
without approve) it is refused (home_reach.in_her_work). HALT holds every run (none starts) and stops one that is running.

Kernel operations (one block in engineering_kernel.py and engineering_cli.py, commented 1.1 KS2):
  command.classify {line? | argv?, by?}   read     the words read, the class, what it would do; nothing runs
  command.read     {argv, by?}            read     a read run sealed; its output as data
  command.plan     {argv, by?}            read     a change's (or a network read's) plan: This will …, Undo's words, the digest
  command.run      {argv, expect, by?}    execute  your press: a change, a bin or a network read, verified after
  command.undo     {run}                  approve  your press: Undo of a run
  command.runs     {limit?}               read     the runs, newest first
  command.output   {run}                  read     one run's output: your view (flagged lines marked) and the model's (fenced)
No floating point in what is said: sizes are bytes, times whole milliseconds.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import uuid
from pathlib import Path

from . import box_ops as bx
from . import command_forms as cf
from . import home_reach as hr

KINDS = ('read', 'network', 'change', 'bin', 'refused')
BY = ('owner', 'dictionary', 'model')
OUTPUT_KEPT = 256 << 10           # bytes of a run's output kept in its record
MOST_WALK = 20000                 # entries a change's plan or verifier walks, at most
SEAL_FILE = str(Path(__file__).resolve().with_name('command_seal.py'))
PRIVATE = ('.ssh', '.gnupg', '.local/share/keyrings', '.password-store', '.mozilla', '.thunderbird', '.config/chromium',
           '.config/google-chrome', '.pki', '.netrc', '.git-credentials')      # a model's proposal never reads here
CLASS_WORDS = {'read': 'only reads', 'network': 'reaches the network', 'change': 'changes something', 'bin': 'to the bin', 'refused': 'refused'}
_RUNNING = {}                     # pid -> root: runs in flight, stopped by HALT
_LOCK = threading.Lock()

ARGV = {'type': 'array', 'minItems': 1, 'maxItems': 64, 'items': {'type': 'string', 'minLength': 1, 'maxLength': 1000}}
FIELDS = {
    'command.classify': ({'line': {'type': 'string', 'minLength': 1, 'maxLength': 2000}, 'argv': ARGV, 'by': {'type': 'string', 'enum': list(BY)}}, []),
    'command.read': ({'argv': ARGV, 'by': {'type': 'string', 'enum': list(BY)}}, ['argv']),
    'command.plan': ({'argv': ARGV, 'by': {'type': 'string', 'enum': list(BY)}}, ['argv']),
    'command.run': ({'argv': ARGV, 'expect': bx.EXPECT, 'by': {'type': 'string', 'enum': list(BY)}}, ['argv', 'expect']),
    'command.undo': ({'run': bx.ID}, ['run']),
    'command.runs': ({'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100}}, []),
    'command.output': ({'run': bx.ID}, ['run']),
}
SCOPES = {'command.classify': 'read', 'command.read': 'read', 'command.plan': 'read', 'command.run': 'execute', 'command.undo': 'approve',
          'command.runs': 'read', 'command.output': 'read'}


class Refused(ValueError):
    """CODE: what and why, in plain words. Nothing ran."""


# ---- the line ---------------------------------------------------------------------------------------------------------------
SHELL_WORDS = {'|': 'a pipe (|)', ';': 'a second command (;)', '&': 'a background or second command (&)', '>': 'a redirection (>)',
               '<': 'a redirection (<)', '`': 'a command inside backticks', '$': 'a variable or a command inside $( )', '(': 'a subshell ( )',
               ')': 'a subshell ( )', '{': 'braces the shell expands', '}': 'braces the shell expands', '\\': 'a backslash escape',
               '#': 'a comment (#)', '!': 'the shell’s history (!)', '\n': 'a second line', '\r': 'a second line',
               '*': 'a pattern the shell would expand (*)', '?': 'a pattern the shell would expand (?)', '[': 'a pattern the shell would expand ([ ])',
               ']': 'a pattern the shell would expand ([ ])'}


def tokens(line):
    """The words of a line as a shell would quote them, or Refused: anything a shell would do instead of the program."""
    text = str(line or '').strip()
    if not text:raise Refused('COMMAND_EMPTY: there is no command in the line')
    if '\0' in text:raise Refused('COMMAND_SHELL: the line holds a NUL character')
    words, word, quote, started = [], [], None, False
    for ch in text:
        if quote == "'":
            if ch == "'":quote = None
            else:word.append(ch)
            continue
        if quote == '"':
            if ch == '"':quote = None
            elif ch in '$`\\!':raise Refused('COMMAND_SHELL: %s, inside double quotes' % SHELL_WORDS[ch])
            else:word.append(ch)
            continue
        if ch in "'\"":
            quote = ch;started = True;continue
        if ch in ' \t':
            if started:words.append(''.join(word));word, started = [], False
            continue
        if ch in SHELL_WORDS:
            if ch == '#' and started:word.append(ch);continue      # a # inside a word is a letter to the shell
            raise Refused('COMMAND_SHELL: %s' % SHELL_WORDS[ch])
        word.append(ch);started = True
    if quote:raise Refused('COMMAND_SHELL: a quote that is never closed')
    if started:words.append(''.join(word))
    if words and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*=.*', words[0]):raise Refused('COMMAND_SHELL: a variable set before the command')
    for w in words:
        if re.match(r'~[^/]', w):raise Refused('COMMAND_SHELL: another user’s home (%s)' % w.split('/')[0])
    return words


def line_of(argv):
    """The exact line that runs, as a shell would read it (each word quoted where it needs to be)."""
    return shlex.join([str(a) for a in argv])


# ---- the table -------------------------------------------------------------------------------------------------------------
_OPTS = {}


def options(form):
    """(short: {letter: kind or None}, long: {name: kind or None}, numbers) from a form's `opts`."""
    key = form.get('opts', '')
    if key in _OPTS:return _OPTS[key]
    short, long_, numbers = {}, {}, False
    for tok in key.split():
        if tok == '-#':numbers = True;continue
        name, _, kind = tok.partition('=')
        if name.startswith('--'):long_[name] = kind or None
        elif len(name) == 2:short[name[1]] = kind or None
        else:long_[name] = kind or None      # a single-dash word option (unused by the table but kept exact)
    _OPTS[key] = (short, long_, numbers)
    return _OPTS[key]


def _forms(program):
    if program in cf.TABLE:return program, cf.TABLE[program]
    for prefix, name in cf.PREFIXES.items():
        if program.startswith(prefix):return name, cf.TABLE[name]
    return program, None


def _value_ok(kind, value):
    value = str(value)
    if any(ord(c) < 32 for c in value):return False
    if kind == 'N':return bool(re.fullmatch(r'\+?\d{1,9}', value))
    if kind == 'I':
        m = re.fullmatch(r'(\d{1,2})(?:\.(\d{1,3}))?', value)
        return bool(m) and (int(m.group(1)) * 1000 + int((m.group(2) or '0').ljust(3, '0'))) in range(200, 60001)
    if kind == 'C':return bool(re.fullmatch(r'[A-Za-z0-9_,%:+=.-]{1,200}', value))
    if kind == 'H':return bool(re.fullmatch(r'[A-Za-z0-9]([A-Za-z0-9.-]{0,250})|\[?[0-9a-fA-F:.]{2,45}\]?', value)) and '..' not in value
    if kind == 'U':
        from urllib.parse import urlsplit
        try:parts = urlsplit(value)
        except ValueError:
            return False
        return parts.scheme in ('http', 'https') and bool(parts.hostname) and _value_ok('H', parts.hostname)
    if kind == 'M':return _mode_ok(value)
    if kind == 'K':return bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+_@:\\-]{0,127}', value))
    if kind == 'X':return value == '-'
    if kind == 'O':return value in ('none', 'none-fail')      # cp --update: only the forms that never write over
    return 0 < len(value) <= 1000      # T, P, W, Q, D


def _mode_ok(value):
    if re.fullmatch(r'[0-7]?[0-7]{3}', value):return True
    return bool(re.fullmatch(r'[ugoa]*[-+=][rwxXst]*(,[ugoa]*[-+=][rwxXst]*)*', value))


def _special(mode):
    return (len(mode) == 4 and mode[0] in '1234567') or bool(re.search(r'[st]', mode) and not mode.isdigit())


def _match_ops(pattern, operands):
    """Operands against a pattern ('P+ Q', 'T P*', 'H T?'): [(kind, word)] or None."""
    parts = pattern.split()
    if not parts:return [] if not operands else None
    need = [0 if p[-1:] in '*?' else 1 for p in parts]
    out, i = [], 0
    for n, p in enumerate(parts):
        kind, rep = (p[:-1], p[-1]) if p[-1:] in '*+?' else (p, '')
        rest = sum(need[n + 1:])
        if rep in ('*', '+'):take = max(0, len(operands) - i - rest)
        elif rep == '?':take = 1 if len(operands) - i - rest > 0 else 0
        else:take = 1
        if rep == '+' and take < 1:return None
        if i + take > len(operands):return None
        out += [(kind, w) for w in operands[i:i + take]];i += take
    return out if i == len(operands) else None


class _Fail(Exception):
    def __init__(self, depth, why):
        super().__init__(why);self.depth = depth;self.why = why


def parse(program, form, words):
    """One form against the words after the program: {opts: [(name, value)], operands: [(kind, word)]} or _Fail(depth, why)."""
    short, long_, numbers = options(form)
    opts, operands, unknown, end = [], [], [], False
    i = 0
    while i < len(words):
        w = words[i];i += 1
        if not end and w == '--':
            end = True;continue
        if not end and w.startswith('--') and len(w) > 2:
            name, eq, value = w.partition('=')
            if name not in long_:unknown.append(name);continue
            kind = long_[name]
            if kind is None:
                if eq:raise _Fail(2, '%s takes no value' % name)
                opts.append((name, None));continue
            if not eq:
                if i >= len(words):raise _Fail(2, '%s needs a value' % name)
                value = words[i];i += 1
            if not _value_ok(kind, value):raise _Fail(2, '“%s” is not a value %s takes' % (value, name))
            opts.append((name, value));continue
        if not end and numbers and re.fullmatch(r'-\d{1,9}', w):
            opts.append(('-#', w[1:]));continue
        if not end and w.startswith('-') and len(w) > 1:
            j = 1
            while j < len(w):
                c = w[j]
                if c not in short:unknown.append('-' + c);j += 1;continue
                kind = short[c]
                if kind is None:opts.append(('-' + c, None));j += 1;continue
                value = w[j + 1:]
                if not value:
                    if i >= len(words):raise _Fail(2, '-%s needs a value' % c)
                    value = words[i];i += 1
                if not _value_ok(kind, value):raise _Fail(2, '“%s” is not a value -%s takes' % (value, c))
                opts.append(('-' + c, value));break
            continue
        operands.append(w)
    sub = list(form.get('sub') or ())
    if sub and operands[:len(sub)] != sub:raise _Fail(0, 'not this form')
    operands = operands[len(sub):]
    names = {n for n, _ in opts} | set(unknown)
    for name in sorted(names):
        why = (form.get('refused') or {}).get(name)
        if why:raise _Fail(5, '%s: %s' % (name, cf.WHY[why]))
    for group in form.get('must') or ():
        if not names & set(group):
            why = form.get('must_why')
            raise _Fail(1, cf.WHY[why] if why else 'that form of %s is not one I know' % program)
    if unknown:raise _Fail(2, 'the flag %s is not one I know for %s' % (unknown[0], program))
    pattern = form.get('ops', '')
    if form.get('pattern_by') and names & set(form['pattern_by']):pattern = pattern.replace('T ', '', 1)
    matched = _match_ops(pattern, operands)
    if matched is None:
        if form.get('too_many') and len(operands) > len(pattern.split()):raise _Fail(3, cf.WHY[form['too_many']])
        raise _Fail(3, '%s takes %s here' % (program, _ops_words(pattern)))
    for kind, w in matched:
        if not _value_ok(kind, w):raise _Fail(3, '“%s” is not %s' % (w, _KIND_WORDS.get(kind, 'a value it takes')))
    return {'opts': opts, 'operands': matched}


_KIND_WORDS = {'P': 'a path', 'W': 'a new path', 'Q': 'a place', 'D': 'a folder', 'T': 'words', 'N': 'a whole number', 'H': 'a host name',
               'U': 'a web address (http or https)', 'M': 'a mode such as 644 or u+x', 'K': 'a name', 'C': 'a list', 'I': 'an interval'}


def _ops_words(pattern):
    if not pattern:return 'no operands'
    out = []
    for p in pattern.split():
        kind, rep = (p[:-1], p[-1]) if p[-1:] in '*+?' else (p, '')
        words = _KIND_WORDS.get(kind, 'a value')
        out.append({'*': 'any number of %s' % words.replace('a ', '', 1) + 's', '+': 'one or more of %s' % words.replace('a ', '', 1) + 's',
                    '?': 'perhaps %s' % words}.get(rep, words))
    return ', then '.join(out)


# ---- the classifier ----------------------------------------------------------------------------------------------------------
def _place(word):
    """An operand as a path: ~ is your home, a relative path is from your home (the run's folder)."""
    w = str(word)
    if w == '~' or w.startswith('~/'):w = str(hr.home()) + w[1:]
    return Path(os.path.normpath(os.path.join(str(hr.home()), w)))


def _private(path):
    h = hr.home()
    return any(hr.within(path, h / p) for p in PRIVATE)


def classify(argv, by='owner'):
    """The class of an argv and what it would do; never runs anything. {ok, kind, classes, argv, line, program, says, reads,
    writes, host, sockets, why, ...}."""
    argv = [str(a) for a in argv]
    out = {'ok': False, 'kind': 'refused', 'classes': [], 'argv': argv, 'line': line_of(argv) if argv else '', 'by': by, 'program': argv[0] if argv else '',
           'says': '', 'reads': [], 'writes': [], 'host': '', 'sockets': 'none', 'why': '', 'code': '', 'plan': None, 'seconds': 30}
    if not argv:out.update(why='there is no command', code='COMMAND_EMPTY');return out
    if any('\0' in a or '\n' in a or '\r' in a for a in argv):out.update(why='a word holds a control character', code='COMMAND_SHELL');return out
    program = argv[0]
    if '/' in program:
        out.update(why='say the program by its name (ls, not a path to it); I find it in the system’s own folders', code='COMMAND_PATH');return out
    name, forms = _forms(program)
    if forms is None:
        out.update(why='I do not know %s, so I do not run it' % program, code='COMMAND_UNKNOWN');return out
    words = _bsd(name, [_tilde(w) for w in argv[1:]])
    out['argv'] = argv = [program] + words;out['line'] = line_of(argv)
    best, catch = None, None
    for form in forms:
        if form.get('refuse'):
            catch = catch or form;continue
        try:
            check = form.get('check')
            got = {'opts': [], 'operands': []} if check in WHOLE_CHECKS else parse(program, form, words)
            if check:CHECKS[check](form, got, words)
        except _Fail as fail:
            if best is None or fail.depth > best[0].depth:best = (fail, form)
            continue
        return _verdict(out, name, form, got, by)
    if catch is not None and (best is None or best[0].depth < 2):
        out.update(classes=list(catch['classes']), why=cf.WHY[catch['refuse']], code='COMMAND_' + catch['refuse'].upper());return out
    fail, form = best
    out.update(classes=list(form['classes']), why=fail.why, code='COMMAND_FORM');return out


def _tilde(word):
    """~ and ~/… mean your home (no shell expands them: the tool does, the same for a typed line and a model's argv);
    also after the = of a long option (--file=~/x)."""
    w = str(word)
    if w == '~' or w.startswith('~/'):return str(hr.home()) + w[1:]
    m = re.match(r'^(--[A-Za-z0-9-]+=)(~(?:/.*)?)$', w)
    if m:return m.group(1) + str(hr.home()) + m.group(2)[1:]
    return w


def _bsd(name, words):
    """tar's old letters (tar xzf a.tgz) read as options (-xzf)."""
    if name == 'tar' and words and re.fullmatch(r'[ctxvzjJfkpa]+', words[0]) and not words[0].startswith('-'):
        return ['-' + words[0]] + words[1:]
    return words


def _verdict(out, name, form, got, by):
    classes = list(got.get('classes') or form['classes'])      # rsync to a host is a network read
    reads, writes, host, texts, names, modes, lands = [], [], '', [], [], [], []
    for kind, w in got['operands']:
        if kind == 'P':reads.append(_place(w))
        elif kind in ('W',):writes.append(_place(w))
        elif kind in ('Q', 'D'):lands.append(_place(w))
        elif kind == 'H':host = host or w
        elif kind == 'U':
            from urllib.parse import urlsplit
            host = host or urlsplit(w).hostname or ''
        elif kind == 'K':names.append(w)
        elif kind == 'M':modes.append(w)
        else:texts.append(w)
    for opt, value in got['opts']:
        kind = (options(form)[1].get(opt) if opt.startswith('--') else options(form)[0].get(opt[1:])) if value is not None else None
        if kind == 'P':reads.append(_place(value))
        elif kind == 'W':writes.append(_place(value))
        elif kind == 'D':lands.append(_place(value))
        elif kind == 'H':host = host or value
    host = got.get('host') or host
    if 'P' in form.get('ops', '') or form.get('check') == 'find':
        reads += [_place(p) for p in got.get('paths', ())]
    if form.get('implicit') == 'home' and not reads:reads.append(hr.home())
    if by == 'model':
        for p in reads + writes + lands:
            if _private(p):
                out.update(classes=classes, why='%s is a private place (keys, passwords, a browser’s data); a model’s line never reads there' % hr.tilde(p),
                           code='COMMAND_PRIVATE');return out
    if any(_special(m) for m in modes):
        out.update(classes=classes, why=cf.WHY['special_bits'], code='COMMAND_SPECIAL');return out
    kind = 'network' if 'network' in classes else 'bin' if form.get('plan') == 'bin' else 'change' if 'change' in classes else 'read'
    fill = {'P': _list(reads), 'W': _list(writes), 'Q': _list(lands or ([hr.home()] if form.get('plan') == 'tar_x' else [])), 'H': host, 'T': ' '.join(texts),
            'N': ', '.join(names) or 'the services', 'M': ', '.join(modes), 'A': texts[0] if texts else '', 'B': texts[1] if len(texts) > 1 else ''}
    says = re.sub(r'\{(\w)\}', lambda m: fill.get(m.group(1), ''), form.get('says', 'run it'))
    out.update(ok=True, kind=kind, classes=classes, says=says, reads=[str(p) for p in reads], writes=[str(p) for p in writes],
               lands=[str(p) for p in lands], host=host, sockets='network' if 'network' in classes else form.get('sockets', 'none'), plan=form.get('plan'), seconds=form.get('seconds', 30),
               needs=list(form.get('needs') or ()), opts=[list(o) for o in got['opts']], operands=[list(o) for o in got['operands']],
               texts=texts, names=names, modes=modes, form=name)
    return out


def _list(paths, most=4):
    shown = [hr.tilde(p) for p in paths[:most]]
    if len(paths) > most:shown.append('%d more' % (len(paths) - most))
    return ', '.join(shown)


# ---- the checks a form names ------------------------------------------------------------------------------------------------
FIND_ARITY = {'-name': 1, '-iname': 1, '-type': 1, '-size': 1, '-mtime': 1, '-mmin': 1, '-atime': 1, '-amin': 1, '-ctime': 1, '-cmin': 1,
              '-newer': 1, '-maxdepth': 1, '-mindepth': 1, '-path': 1, '-ipath': 1, '-wholename': 1, '-iwholename': 1, '-regex': 1, '-iregex': 1,
              '-regextype': 1, '-user': 1, '-group': 1, '-uid': 1, '-gid': 1, '-perm': 1, '-links': 1, '-inum': 1, '-samefile': 1, '-lname': 1,
              '-ilname': 1, '-fstype': 1, '-printf': 1, '-used': 1, '-empty': 0, '-print': 0, '-print0': 0, '-ls': 0, '-xdev': 0, '-mount': 0,
              '-not': 0, '-a': 0, '-o': 0, '-and': 0, '-or': 0, '!': 0, '(': 0, ')': 0, ',': 0, '-prune': 0, '-readable': 0, '-writable': 0,
              '-executable': 0, '-quit': 0, '-depth': 0, '-daystart': 0, '-nouser': 0, '-nogroup': 0, '-true': 0, '-false': 0, '-noleaf': 0,
              '-ignore_readdir_race': 0, '-follow': 0}
FIND_REFUSED = {'-delete': 'destroy', '-exec': 'runs_program', '-execdir': 'runs_program', '-ok': 'runs_program', '-okdir': 'runs_program',
                '-fprint': 'writes_file', '-fprint0': 'writes_file', '-fprintf': 'writes_file', '-fls': 'writes_file'}


def _check_find(form, got, words):
    i, paths = 0, []
    while i < len(words) and words[i] in ('-H', '-L', '-P'):i += 1
    while i < len(words) and not words[i].startswith('-') and words[i] not in ('!', '(', ')', ','):
        paths.append(words[i]);i += 1
    while i < len(words):
        w = words[i]
        if w in FIND_REFUSED:raise _Fail(5, '%s: %s' % (w, cf.WHY[FIND_REFUSED[w]]))
        if w not in FIND_ARITY:raise _Fail(2, '%s is not a test of find I know' % w)
        n = FIND_ARITY[w]
        if i + n >= len(words) + (0 if n else 1) and n:raise _Fail(2, '%s needs a value' % w)
        if w in ('-newer', '-samefile') and n:paths_read = words[i + 1];got.setdefault('also', []).append(paths_read)
        i += 1 + n
    got['paths'] = paths + got.get('also', [])
    got['operands'] = [('P', p) for p in paths]


PS_BSD = set('auxefwjlrTSHhcmnvgxXZ')


def _check_ps(form, got, words):
    i = 0
    while i < len(words):
        w = words[i];i += 1
        if w in ('-e', '-A', '-f', '-F', '-l', '-y', '-H', '-w', '-ww', '-c', '-L', '-T', '-a', '-d', '-N', '--forest', '--no-headers', '-j', '-M', '-Z'):continue
        if w in ('-o', '-O', '-p', '-u', '-U', '-C', '-G', '-g', '-t', '--sort', '--pid', '--ppid', '--user', '-q'):
            if i >= len(words) or not _value_ok('C', words[i].lstrip('+-')):raise _Fail(2, '%s needs a list' % w)
            i += 1;continue
        if re.fullmatch(r'--(sort|format|pid|ppid|user|cols|columns|width|lines|rows)=[A-Za-z0-9_,%:+=.-]{1,200}', w):continue
        m = re.fullmatch(r'-([eAfFlyHwcLTadNjMZ]*)([oOpuUCGgtq])(.*)', w)
        if m:
            value = m.group(3)
            if not value:
                if i >= len(words):raise _Fail(2, '%s needs a list' % w)
                value = words[i];i += 1
            if not _value_ok('C', value.lstrip('+-')):raise _Fail(2, '“%s” is not a list ps takes' % value)
            continue
        if re.fullmatch(r'-[eAfFlyHwcLTadNjMZ]+', w):continue
        if not w.startswith('-') and set(w) <= PS_BSD:continue
        raise _Fail(2, 'the flag %s is not one I know for ps' % w)
    got['operands'] = []


def _check_ip(form, got, words):
    from . import stacy_hand
    if not stacy_hand._ip_reads(['ip'] + list(words)):raise _Fail(1, 'not a showing form of ip')
    got['operands'] = []


def _check_date(form, got, words):
    for kind, w in got['operands']:
        if not w.startswith('+'):raise _Fail(1, 'date with a time sets the clock')


def _check_hostname(form, got, words):
    if got['operands']:raise _Fail(1, 'hostname with a name sets it')


def _check_sysctl(form, got, words):
    for kind, w in got['operands']:
        if '=' in w:raise _Fail(1, 'a setting with = changes the kernel')
    if any(n in ('-w', '--write', '-p', '--load', '--system') for n, _ in got['opts']):raise _Fail(1, 'it changes the kernel')


def _check_dig(form, got, words):
    host = ''
    types = {'A', 'AAAA', 'MX', 'NS', 'TXT', 'SOA', 'CNAME', 'PTR', 'SRV', 'CAA', 'ANY', 'DS', 'DNSKEY', 'HTTPS', 'SVCB'}
    for kind, w in got['operands']:
        if w.startswith('@'):
            if not _value_ok('H', w[1:]):raise _Fail(3, '“%s” is not a name server' % w)
        elif w.startswith('+'):
            if not re.fullmatch(r'\+(no)?[a-z]{2,20}(=\d{1,3})?', w):raise _Fail(3, '“%s” is not a dig option I know' % w)
        elif w.upper() in types and host:continue
        elif _value_ok('H', w):host = host or w
        else:raise _Fail(3, '“%s” is not a name' % w)
    for opt, value in got['opts']:
        if opt == '-x':host = host or value
    if not host:raise _Fail(3, 'dig needs a name to ask about')
    got['host'] = host


def _check_rsync(form, got, words):
    paths = [w for _, w in got['operands']]
    remote = [w for w in paths if re.match(r'^[A-Za-z0-9._@-]+:', w)]
    if remote:
        host = remote[0].split(':', 1)[0].split('@')[-1]
        if not _value_ok('H', host):raise _Fail(3, '“%s” is not a host' % host)
        form_classes = ('read', 'network')
        got['host'] = host;got['classes'] = form_classes
    got['operands'] = [('P', w) for w in paths if w not in remote] + [('T', w) for w in remote]


def _check_apt_get(form, got, words):
    names = [w for _, w in got['operands']]
    if not names or names[0] not in ('upgrade', 'dist-upgrade', 'full-upgrade', 'install', 'remove', 'purge', 'autoremove'):
        raise _Fail(1, cf.WHY['root'])


def _check_perl(form, got, words):
    expr = got['operands'][0][1]
    if not re.fullmatch(r's/([A-Za-z0-9 ._-]+)/([A-Za-z0-9 ._-]*)/g?', expr):raise _Fail(5, cf.WHY['perl_code'])


def _check_empty(form, got, words):
    for kind, w in got['operands']:
        p = _place(w)
        if p.is_dir() and not p.is_symlink():
            try:
                if any(os.scandir(p)):raise _Fail(3, '%s is not empty; rmdir takes only an empty folder' % hr.tilde(p))
            except OSError:
                pass


WHOLE_CHECKS = ('find', 'ps', 'ip')      # these read the words themselves (find's expression, ps's BSD words, ip's objects)
CHECKS = {'find': _check_find, 'ps': _check_ps, 'ip': _check_ip, 'date': _check_date, 'hostname': _check_hostname, 'sysctl': _check_sysctl, 'dig': _check_dig,
          'rsync': _check_rsync, 'apt_get': _check_apt_get, 'perl_subst': _check_perl, 'empty_dirs': _check_empty}


def from_line(line, by='owner'):
    """A typed line: its words, then the classifier. A refusal of the line itself keeps the line as it was typed."""
    try:words = tokens(line)
    except Refused as exc:
        code, _, why = str(exc).partition(': ')
        return {'ok': False, 'kind': 'refused', 'classes': [], 'argv': [], 'line': ' '.join(str(line).split()), 'by': by, 'program': '',
                'says': '', 'why': why + ': I run one program with its words, never a shell', 'code': code, 'plan': None}
    return classify(words, by)


# ---- her dictionary (no model) -------------------------------------------------------------------------------------------------
_DICT = None


def _normal(text):
    t = str(text or '').lower().replace('what’s', 'whats').replace("what's", 'whats')
    t = ' '.join(re.sub(r'[?!,;“”"\'’]+|[.:]+(?=\s|$)', ' ', t).split())
    changed = True
    while changed:
        changed = False
        for lead in cf.LEADS:
            if t.startswith(lead + ' '):t = t[len(lead) + 1:];changed = True
    return t


def dictionary(text):
    """The form her dictionary maps the words to: {argv, words} or None. Only short requests that are the phrase entirely."""
    global _DICT
    if _DICT is None:_DICT = [(re.compile(r'(?:the |my )?(?:%s)' % p), argv) for p, argv in cf.DICTIONARY]
    t = _normal(text)
    if not t or len(t.split()) > 12:return None
    for rx, argv in _DICT:
        m = rx.fullmatch(t)
        if not m:continue
        word = (m.groupdict().get('x') or m.groupdict().get('y') or '')
        return {'argv': [a.replace('{x}', word) for a in argv], 'words': t}
    return None


# ---- the seal --------------------------------------------------------------------------------------------------------------
def seal_words():
    """How this computer seals a run, in words; '' when it cannot (and then nothing runs)."""
    from . import command_seal
    level = command_seal.abi()
    if level <= 0 or not command_seal.available():return ''
    return 'Landlock (ABI %d) and seccomp' % level


def _roots(v):
    reads = list(v.get('reads') or [])
    for key in v.get('needs') or ():
        reads += list(cf.NEEDS.get(key, ()))
    out = []
    for p in reads:
        try:real = os.path.realpath(p)
        except OSError:
            continue
        if os.path.exists(real) and real not in out:out.append(real)
        if os.path.isfile(real) and os.path.dirname(real) not in out and v.get('kind') == 'change':out.append(os.path.dirname(real))
    return out


def run_sealed(kernel, argv, reads=(), writes=(), sockets='none', seconds=30, env=None):
    """argv, sealed (command_seal): {exit, out, err, cut, killed, ms, sealed}. Refused when the program is missing, when this
    computer cannot seal, or while HALT holds."""
    program = bx._which(argv[0])
    if not program:
        package = cf.PACKAGES.get(argv[0], 'coreutils')
        raise Refused('COMMAND_NEEDS_PROGRAM: %s is not on this computer. Debian’s package “%s” has it; nothing ran.' % (argv[0], package))
    from . import command_seal
    if not command_seal.available():raise Refused('COMMAND_NO_SEAL: this computer has no Landlock, so nothing runs: never unsealed')
    _halt(kernel)
    scratch = tempfile.mkdtemp(prefix='graphite-command-')
    plan = {'program': program, 'argv': [str(a) for a in argv], 'cwd': str(hr.home()), 'scratch': scratch, 'read': list(reads), 'write': list(writes),
            'sockets': sockets, 'env': env or {}, 'limits': {'cpu_seconds': max(10, seconds)}}
    started = time.monotonic_ns()
    try:
        proc = subprocess.Popen([sys.executable, '-I', '-S', '-B', SEAL_FILE, json.dumps(plan)], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, start_new_session=True, cwd=scratch, env={'PATH': bx.PROGRAM_PATH, 'LANG': 'C.UTF-8'})
        with _LOCK:_RUNNING[proc.pid] = str(getattr(kernel, 'root', ''))
        killed = ''
        try:
            out, err = proc.communicate(timeout=seconds)
        except subprocess.TimeoutExpired:
            killed = 'it took longer than %d seconds, so it was stopped' % seconds;_stop(proc.pid);out, err = proc.communicate()
        finally:
            with _LOCK:_RUNNING.pop(proc.pid, None)
        if proc.returncode in (-signal.SIGKILL, -signal.SIGTERM) and not killed:killed = 'HALT stopped it' if _held(kernel) else 'it was stopped'
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    err_text = err[:OUTPUT_KEPT].decode('utf-8', 'replace')
    seal_note = next((l for l in err_text.splitlines() if l.startswith(command_seal.NOTE)), '')
    return {'exit': proc.returncode, 'out': clean(out[:OUTPUT_KEPT].decode('utf-8', 'replace')), 'err': clean(err_text),
            'cut': len(out) > OUTPUT_KEPT, 'killed': killed, 'ms': (time.monotonic_ns() - started) // 1_000_000,
            'sealed': '' if seal_note else seal_words(), 'seal_note': seal_note}


def _stop(pid):
    try:os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def halt_stop(kernel, principal):
    """HALT's stop hook: every run in flight for this workspace ends now."""
    key = str(getattr(kernel, 'root', ''))
    with _LOCK:pids = [pid for pid, root in _RUNNING.items() if root == key]
    for pid in pids:_stop(pid)
    return ('%d command stopped' % len(pids)) if pids else ''


def _held(kernel):
    try:
        from . import halt_gate
        return bool(halt_gate.held(kernel))
    except Exception:  # noqa: BLE001 - without the gate nothing holds
        return False


def _halt(kernel):
    if _held(kernel):raise Refused('COMMAND_HALT: HALT holds my work, so nothing ran. Press RESUME, then ask again.')


try:
    from . import halt_gate as _hg
    _hg.register_stop('commands', halt_stop)
except Exception:  # noqa: BLE001
    pass

_ESC = re.compile(r'\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-Z\\-_]|[\x00-\x08\x0b-\x1f\x7f]')


def clean(text):
    """Output as text: terminal escapes and control characters taken out (tabs and new lines kept)."""
    return _ESC.sub('', str(text or '').replace('\r\n', '\n'))


def as_data(text, title=''):
    """Output as data, through the doorway: {lines: [{n, text, flagged, reasons}], flagged, model_page}."""
    from . import doorway
    door = doorway.scan(text)
    held = set(door.withheld())
    lines = [{'n': r['n'], 'text': r['text'], 'flagged': r['n'] in held, 'reasons': door.reasons(r['n'])} for r in door.lines]
    return {'lines': lines, 'flagged': sorted(held), 'model_page': doorway.page_message(door, title or 'the output of a command')}


# ---- the records --------------------------------------------------------------------------------------------------------------
def ensure(db):
    db.execute('''CREATE TABLE IF NOT EXISTS command_runs(id TEXT PRIMARY KEY, owner TEXT, at INTEGER, argv TEXT, kind TEXT, by TEXT,
                  state TEXT, exit INTEGER, verified INTEGER, checked TEXT, out TEXT, err TEXT, plan TEXT, record TEXT, undone INTEGER)''')


def _keep(kernel, ident, principal, v, state, result=None, plan=None, record=None, verified=False, checked=''):
    from . import files_service
    result = result or {}
    with files_service.opened(kernel) as db:
        ensure(db)
        db.execute('INSERT OR REPLACE INTO command_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)',
                   (ident, getattr(principal, 'identity', ''), bx._now_ms(), json.dumps(v['argv']), v['kind'], v.get('by', 'owner'), state,
                    result.get('exit'), 1 if verified else 0, checked[:1000], result.get('out', ''), result.get('err', '')[:20000],
                    json.dumps(plan or {}, default=str), json.dumps(record or {}, default=str)))


def load(kernel, ident):
    from . import files_service
    with files_service.opened(kernel) as db:
        ensure(db)
        row = db.execute('SELECT * FROM command_runs WHERE id=?', (ident,)).fetchone()
    if row is None:raise Refused('COMMAND_UNKNOWN_RUN: no such run')
    return {k: row[k] for k in row.keys()}


# ---- reads ------------------------------------------------------------------------------------------------------------------
def read(kernel, args, principal):
    """A read, run sealed now; its output as data. A network read, a change or a refusal is not run here."""
    v = classify(args['argv'], args.get('by', 'owner'))
    if not v['ok']:raise Refused('%s: %s' % (v['code'], v['why']))
    if v['kind'] != 'read':raise Refused('COMMAND_NOT_A_READ: it %s, so it waits for your press' % CLASS_WORDS[v['kind']])
    got = run_sealed(kernel, v['argv'], _roots(v), (), v['sockets'], v['seconds'])
    return _finish_read(kernel, principal, v, got)


def _finish_read(kernel, principal, v, got):
    ok_codes = (0, 1) if v['program'] in ('grep', 'diff', 'cmp', 'pgrep', 'systemctl', 'which', 'comm') else (0,)
    sealed = bool(got['sealed'])
    verified = sealed and got['exit'] in ok_codes and not got['killed']
    if not sealed:checked = 'the seal did not take, so it did not run: %s' % got['seal_note'].split(': ', 1)[-1]
    elif got['killed']:checked = got['killed']
    else:checked = 'it ran inside the seal (%s) and ended with exit code %d' % (got['sealed'], got['exit'])
    data = as_data(got['out'], v['line'])
    ident = uuid.uuid4().hex
    _keep(kernel, ident, principal, v, 'done' if verified else 'not verified', got, verified=verified, checked=checked)
    return {'run': ident, 'line': v['line'], 'kind': v['kind'], 'says': v['says'], 'exit': got['exit'], 'verified': verified, 'checked': checked,
            'lines': data['lines'], 'flagged': data['flagged'], 'err': got['err'][-2000:], 'cut': got['cut'], 'ms': got['ms'], 'sealed': got['sealed'],
            'host': v.get('host', '')}


# ---- changes: plan, act, verify, undo ----------------------------------------------------------------------------------------
def _opt(v, *names):
    return [val for n, val in v.get('opts') or () if n in names]


def _has(v, *names):
    return any(n in names for n, _ in v.get('opts') or ())


def _lst(path):
    st = os.lstat(path)
    return {'ino': st.st_ino, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns, 'mode': st.st_mode & 0o7777, 'dir': os.path.isdir(path) and not os.path.islink(path)}


def _new_ok(reach, path):
    if os.path.lexists(path):raise Refused('COMMAND_THERE: %s is already there; nothing is written over' % hr.tilde(path))
    reach.new_in(path.parent);reach.check(path)


def _exists(path):
    if not os.path.lexists(path):raise Refused('COMMAND_NOT_FOUND: %s is not there' % hr.tilde(path))


def plan(kernel, v):
    """What a change (or a network read) would do, exactly: {items, lines, undo, can_undo, writes, expect}. Nothing changes."""
    reach = bx.Reach(kernel);items, lines, writes = [], [], []
    kind = v['plan']
    if v['kind'] == 'network':
        lines = ['It reaches %s, and only it; its answer is shown as data.' % v['host']]
        found = {'items': [], 'lines': lines, 'undo': 'It changes nothing here, so there is nothing to undo.', 'can_undo': True, 'writes': []}
    elif kind == 'mkdir':
        parents = _has(v, '-p', '--parents')
        for p in map(Path, v['writes']):
            if os.path.lexists(p):
                if parents and os.path.isdir(p):
                    lines.append('%s (there already: left as it is)' % hr.tilde(p));continue
                raise Refused('COMMAND_THERE: %s is already there' % hr.tilde(p))
            chain = [p]
            while not os.path.lexists(chain[-1].parent):
                if not parents:raise Refused('COMMAND_NOT_FOUND: %s is not there (mkdir -p makes it too)' % hr.tilde(chain[-1].parent))
                chain.append(chain[-1].parent)
            base = chain[-1].parent
            if not os.path.isdir(base):raise Refused('COMMAND_NOT_A_FOLDER: %s is not a folder' % hr.tilde(base))
            reach.new_in(base)
            for q in reversed(chain):
                if any(i['path'] == str(q) for i in items):continue
                reach.check(q);items.append({'what': 'dir', 'path': str(q)});lines.append('%s (a new folder)' % hr.tilde(q))
            writes.append(str(base))
        undo = 'Undo takes the new folders away again, while they are empty.'
    elif kind == 'touch':
        for p in map(Path, v['writes']):
            if os.path.lexists(p):
                if not os.path.isfile(p) or os.path.islink(p):raise Refused('COMMAND_NOT_A_FILE: %s is not a file' % hr.tilde(p))
                reach.check(p);st = os.stat(p)
                items.append({'what': 'touch', 'path': str(p), 'ino': st.st_ino, 'atime_ns': st.st_atime_ns, 'mtime_ns': st.st_mtime_ns, 'size': st.st_size})
                lines.append('%s (there already: its time set to now)' % hr.tilde(p));writes.append(str(p))
            elif _has(v, '-c', '--no-create'):
                lines.append('%s (not there, and -c makes nothing)' % hr.tilde(p))
            else:
                if not p.parent.is_dir():raise Refused('COMMAND_NOT_FOUND: %s is not there' % hr.tilde(p.parent))
                _new_ok(reach, p);items.append({'what': 'file', 'path': str(p)});lines.append('%s (a new, empty file)' % hr.tilde(p))
                writes.append(str(p.parent))
        undo = 'Undo puts a new file in DELETE, and gives a file that was there its old time back.'
    elif kind in ('cp', 'mv'):
        srcs = [Path(p) for p in v['reads']];dest = Path(v['lands'][0])
        into = os.path.isdir(dest) and not _has(v, '-T', '--no-target-directory')
        if len(srcs) > 1 and not into:raise Refused('COMMAND_NOT_A_FOLDER: %s is not a folder, and several things go into one' % hr.tilde(dest))
        folder = dest if into else dest.parent
        if not os.path.isdir(folder):raise Refused('COMMAND_NOT_FOUND: %s is not there' % hr.tilde(folder))
        reach.new_in(folder)
        for s in srcs:
            _exists(s)
            land = folder / s.name if into else dest
            _new_ok(reach, land)
            if hr.within(land, s):raise Refused('COMMAND_INTO_ITSELF: %s cannot go inside itself' % hr.tilde(s))
            st = _lst(s)
            if kind == 'cp':
                if st['dir'] and not _has(v, '-r', '-R', '--recursive', '-a', '--archive'):
                    raise Refused('COMMAND_A_FOLDER: %s is a folder; cp copies a folder with -r' % hr.tilde(s))
                count, size = _tally(s)
                items.append({**st, 'what': 'copy', 'from': str(s), 'to': str(land), 'count': count, 'size': size})
                lines.append('%s → %s (%s)' % (hr.tilde(s), hr.tilde(land), bx.count_words(count, 'file') + ', ' + bx.size_words(size) if st['dir'] else bx.size_words(st['size'])))
            else:
                reach.check(s)
                if os.lstat(s).st_dev != os.stat(folder).st_dev:raise Refused('COMMAND_OTHER_DRIVE: %s is on another drive; mv would copy and delete. Use cp -n.' % hr.tilde(s))
                items.append({'what': 'move', 'from': str(s), 'to': str(land), **st});lines.append('%s → %s' % (hr.tilde(s), hr.tilde(land)))
                writes.append(str(s.parent))
        writes.append(str(folder))
        undo = ('Undo puts what it copied in DELETE; the originals are never touched.' if kind == 'cp' else
                'Undo moves each one back where it was, while its old place is free.')
    elif kind == 'ln':
        link = Path(v['writes'][0]);target = v['texts'][0]
        if not link.parent.is_dir():raise Refused('COMMAND_NOT_FOUND: %s is not there' % hr.tilde(link.parent))
        _new_ok(reach, link);items.append({'what': 'link', 'path': str(link), 'target': target})
        lines.append('%s → %s (a link)' % (hr.tilde(link), target));writes.append(str(link.parent))
        undo = 'Undo takes the link away; what it points to is never touched.'
    elif kind == 'chmod':
        mode = v['modes'][0]
        for p in map(Path, v['reads']):
            _exists(p)
            if os.path.islink(p):raise Refused('COMMAND_A_LINK: %s is a link; chmod would change what it points to. Name the file.' % hr.tilde(p))
            st = os.lstat(p)
            if st.st_uid != os.getuid():raise Refused('COMMAND_NOT_YOURS: %s is not your own file' % hr.tilde(p))
            reach.check(p)
            old = st.st_mode & 0o7777;new = new_mode(mode, old, os.path.isdir(p))
            if new & 0o7000:raise Refused('COMMAND_SPECIAL: %s' % cf.WHY['special_bits'])
            if new == old:lines.append('%s (already %04o: left as it is)' % (hr.tilde(p), old));continue
            items.append({'what': 'mode', 'path': str(p), 'ino': st.st_ino, 'old': old, 'new': new})
            lines.append('%s: %s → %s' % (hr.tilde(p), mode_words(old), mode_words(new)))
        undo = 'Undo gives each file its old mode back.'
    elif kind == 'tar_c':
        archive = Path(v['writes'][0]);srcs = [Path(p) for p in v['reads']]
        if not archive.parent.is_dir():raise Refused('COMMAND_NOT_FOUND: %s is not there' % hr.tilde(archive.parent))
        _new_ok(reach, archive)
        total, size = 0, 0
        for s in srcs:
            _exists(s);n, b = _tally(s);total += n;size += b
        items.append({'what': 'archive', 'path': str(archive), 'count': total, 'size': size, 'from': [str(s) for s in srcs]})
        lines.append('%s (new: %s, %s, from %s)' % (hr.tilde(archive), bx.count_words(total, 'file'), bx.size_words(size), _list(srcs)))
        writes.append(str(archive.parent))
        undo = 'Undo puts the new archive in DELETE; what it holds is never touched.'
    elif kind == 'tar_x':
        archive = Path(v['reads'][0]);dest = Path(v['lands'][0]) if v.get('lands') else hr.home()
        _exists(archive)
        if not dest.is_dir():raise Refused('COMMAND_NOT_FOUND: %s is not there' % hr.tilde(dest))
        reach.new_in(dest)
        members = _members(archive, v['texts'])
        tops = []
        for m in members:
            land = dest / m['name']
            if os.path.lexists(land):
                if m['dir'] and os.path.isdir(land):continue
                raise Refused('COMMAND_THERE: %s is already there; nothing is written over' % hr.tilde(land))
            reach.check(land)
            top = land
            while top.parent != dest and not os.path.lexists(top.parent):top = top.parent
            if str(top) not in tops:tops.append(str(top))
            items.append({'what': 'unpack', 'path': str(land), 'dir': m['dir'], 'size': m['size']})
        for t in tops[:bx.MOST_ROWS]:lines.append('%s (new)' % hr.tilde(t))
        writes.append(str(dest))
        found_tops = tops
        undo = 'Undo puts what it unpacked in DELETE; the archive is never touched.'
    elif kind in ('rename_ul', 'rename_perl'):
        if kind == 'rename_ul':old, new = v['texts'][0], v['texts'][1]
        else:
            m = re.fullmatch(r's/([^/]+)/([^/]*)/(g?)', v['texts'][0]);old, new = m.group(1), m.group(2)
        last = _has(v, '-l', '--last');every = kind == 'rename_perl' and v['texts'][0].endswith('/g')
        for p in map(Path, v['reads']):
            _exists(p)
            if old not in p.name:lines.append('%s (no “%s” in its name: left as it is)' % (hr.tilde(p), old));continue
            name = p.name.replace(old, new) if every else (p.name[::-1].replace(old[::-1], new[::-1], 1)[::-1] if last else p.name.replace(old, new, 1))
            if not name or name in ('.', '..'):raise Refused('COMMAND_NAME: %s would have no name' % hr.tilde(p))
            to = p.parent / name
            reach.check(p);_new_ok(reach, to)
            items.append({'what': 'move', 'from': str(p), 'to': str(to), **_lst(p)});lines.append('%s → %s' % (hr.tilde(p), name))
            writes.append(str(p.parent))
        undo = 'Undo gives every file its old name back.'
    elif kind == 'bin':
        for p in map(Path, v['reads']):
            _exists(p);reach.check(p)
            if os.path.isdir(p) and not os.path.islink(p) and v['program'] == 'rm' and not _has(v, '-r', '-R', '--recursive', '-d', '--dir'):
                raise Refused('COMMAND_A_FOLDER: %s is a folder; rm takes a folder with -r (it goes to the bin whole)' % hr.tilde(p))
            st = _lst(p);count, size = _tally(p)
            items.append({'what': 'bin', 'path': str(p), **st})
            lines.append('%s (%s)' % (hr.tilde(p), (bx.count_words(count, 'file') + ', ' + bx.size_words(size)) if st['dir'] else bx.size_words(st['size'])))
        undo = 'Undo takes each one back out of DELETE, to where it was.'
    else:
        raise Refused('COMMAND_NO_PLAN: %s has no plan here' % v['program'])
    if v['kind'] != 'network':
        found = {'items': items, 'lines': lines, 'undo': undo, 'can_undo': True, 'writes': sorted(set(writes))}
        if kind == 'tar_x':found['tops'] = found_tops
    found['expect'] = bx.digest({'argv': v['argv'], 'items': items, 'host': v.get('host', '')})
    return found


def _tally(path):
    """(files, bytes) under a path (a file: 1 and its size); links not followed; bounded."""
    path = Path(path)
    if not path.is_dir() or path.is_symlink():
        try:return 1, os.lstat(path).st_size
        except OSError:
            return 1, 0
    n, size, seen = 0, 0, 0
    for root, dirs, files in os.walk(path):
        for f in files:
            seen += 1
            if seen > MOST_WALK:raise Refused('COMMAND_TOO_MANY: %s holds more than %d things; that is more than one press here' % (hr.tilde(path), MOST_WALK))
            try:size += os.lstat(os.path.join(root, f)).st_size;n += 1
            except OSError:
                pass
    return n, size


def _members(archive, only=()):
    """An archive's members, read by Python's tarfile: refused when one is a link, a device, absolute, or climbs with '..'."""
    try:
        with tarfile.open(archive) as t:
            got = []
            for m in t:
                if len(got) >= MOST_WALK:raise Refused('COMMAND_TOO_MANY: the archive holds more than %d things' % MOST_WALK)
                name = m.name.rstrip('/')
                if m.issym() or m.islnk() or m.isdev() or m.isfifo():
                    raise Refused('COMMAND_ARCHIVE_LINK: %s in the archive is a link or a device; it is not unpacked here' % name)
                if name.startswith('/') or '..' in Path(name).parts or not name:
                    raise Refused('COMMAND_ARCHIVE_PATH: %s in the archive would land outside its folder' % name)
                if only and not any(name == o.rstrip('/') or name.startswith(o.rstrip('/') + '/') for o in only):continue
                got.append({'name': name, 'dir': m.isdir(), 'size': m.size})
            return got
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise Refused('COMMAND_ARCHIVE: %s could not be read as an archive (%s)' % (hr.tilde(archive), str(exc)[:80])) from None


def new_mode(text, old, is_dir):
    """chmod's mode: octal, or symbolic (u+x,go-w; with no who, as chmod does: the umask's bits left alone)."""
    if re.fullmatch(r'[0-7]?[0-7]{3}', text):return int(text, 8)
    mask = os.umask(0);os.umask(mask)
    mode = old
    for part in text.split(','):
        m = re.fullmatch(r'([ugoa]*)([-+=])([rwxX]*)', part)
        who, op, perms = m.group(1), m.group(2), m.group(3)
        bits = 0
        for scope, shift in (('u', 6), ('g', 3), ('o', 0)):
            if who and scope not in who and 'a' not in who:continue
            b = 0
            if 'r' in perms:b |= 4
            if 'w' in perms:b |= 2
            if 'x' in perms or ('X' in perms and (is_dir or old & 0o111)):b |= 1
            bits |= b << shift
        if not who:bits &= ~mask
        if op == '+':mode |= bits
        elif op == '-':mode &= ~bits
        else:
            clear = 0
            for scope, shift in (('u', 6), ('g', 3), ('o', 0)):
                if not who or scope in who or 'a' in who:clear |= 7 << shift
            mode = (mode & ~clear) | bits
    return mode & 0o7777


def mode_words(mode):
    out = ''
    for shift in (6, 3, 0):
        b = (mode >> shift) & 7
        out += ('r' if b & 4 else '-') + ('w' if b & 2 else '-') + ('x' if b & 1 else '-')
    return '%04o (%s)' % (mode, out)


def run(kernel, args, principal):
    """Your press: plan again, compare with what you were shown, run (sealed, or into the bin), verify on the disk, record Undo."""
    v = classify(args['argv'], args.get('by', 'owner'))
    if not v['ok']:raise Refused('%s: %s' % (v['code'], v['why']))
    if v['kind'] == 'read':return read(kernel, args, principal)
    if hr.in_her_work(principal):
        raise Refused('COMMAND_YOUR_PRESS: it %s, so it runs on your press only, never as my own step' % CLASS_WORDS[v['kind']])
    _halt(kernel)
    found = plan(kernel, v)
    if found['expect'] != args['expect']:raise Refused('COMMAND_PLAN_CHANGED: what it would do is not what you were shown (things changed since). Look at it again.')
    if v['kind'] == 'network':return _network(kernel, principal, v)
    if not found['items']:raise Refused('COMMAND_NOTHING: there is nothing for it to do: %s' % '; '.join(found['lines'][:3]))
    ident = uuid.uuid4().hex;record = {'made': [], 'made_dirs': [], 'moves': [], 'trashed': [], 'modes': [], 'times': [], 'links': []}
    _keep(kernel, ident, principal, v, 'running', plan=found, record=record)
    got = {}
    try:
        if v['plan'] == 'bin':got = _bin(found, record)
        else:
            reads = _roots({**v, 'kind': 'change', 'reads': v['reads'] + found['writes']})
            got = run_sealed(kernel, v['argv'], reads, found['writes'], 'none', max(60, v['seconds']))
            if not got['sealed']:raise Refused('COMMAND_SEAL: the seal did not take, so it did not run: %s' % got['seal_note'].split(': ', 1)[-1])
        verified, checked = VERIFY[v['plan']](found, record, got)
        state = 'done' if verified else 'not verified'
    except Refused as exc:
        verified, checked, state = False, str(exc).split(': ', 1)[-1], 'stopped'
    _keep(kernel, ident, principal, v, state, got, plan=found, record=record, verified=verified, checked=checked)
    return {'run': ident, 'line': v['line'], 'kind': v['kind'], 'state': state, 'verified': verified, 'checked': checked, 'says': v['says'],
            'can_undo': found['can_undo'] and state != 'stopped' or bool(record['made'] or record['moves'] or record['trashed'] or record['modes']),
            'undo': found['undo'], 'out': (got.get('out') or '')[-2000:], 'err': (got.get('err') or '')[-2000:], 'exit': got.get('exit')}


def _network(kernel, principal, v):
    from . import network_governed as ng
    reading = ng.state(getattr(kernel, 'root', None), fresh=True)
    if reading['state'] != 'online':raise Refused('COMMAND_OFFLINE: %s. Nothing left this computer.' % ng.needs_words(reading))
    where = {'host': v['host'], 'site': v['host']}
    with ng._fetching(kernel, where, 'command'):      # NET says "Kas: <host>" while it runs
        got = run_sealed(kernel, v['argv'], _roots(v), (), 'network', v['seconds'])
    return _finish_read(kernel, principal, v, got)


def _bin(found, record):
    from . import home_trash
    for item in found['items']:
        put = home_trash.put(item['path'])
        record['trashed'].append({'name': put['name'], 'original': put['original'], 'stored': put['stored'], 'ino': item['ino']})
    return {}


def _verify_bin(found, record, got):
    bad = [t['original'] for t in record['trashed'] if os.path.lexists(t['original']) or not os.path.lexists(t['stored'])]
    if bad:return False, '%s is still there' % hr.tilde(bad[0])
    return True, 'in DELETE now, gone from its place: %s' % _list([t['original'] for t in record['trashed']])


def _verify_mkdir(found, record, got):
    for i in found['items']:
        if not os.path.isdir(i['path']) or os.path.islink(i['path']):return False, '%s is not a folder' % hr.tilde(i['path'])
        record['made_dirs'].append({'path': i['path'], 'ino': os.lstat(i['path']).st_ino})
    return True, '%s there, read back' % ('a folder is' if len(found['items']) == 1 else bx.count_words(len(found['items']), 'folder') + ' are')


def _verify_touch(found, record, got):
    for i in found['items']:
        p = i['path']
        if not os.path.isfile(p):return False, '%s is not there' % hr.tilde(p)
        st = os.lstat(p)
        if i['what'] == 'file':
            if st.st_size != 0:return False, '%s is not empty' % hr.tilde(p)
            record['made'].append({'path': p, 'ino': st.st_ino, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns})
        else:
            if st.st_mtime_ns < i['mtime_ns']:return False, '%s kept its old time' % hr.tilde(p)
            record['times'].append({'path': p, 'ino': st.st_ino, 'atime_ns': i['atime_ns'], 'mtime_ns': i['mtime_ns'], 'set_ns': st.st_mtime_ns})
    return True, '%s read back on the disk' % bx.count_words(len(found['items']), 'file')


def _walk_made(top, record):
    if os.path.isdir(top) and not os.path.islink(top):
        record['made_dirs'].append({'path': top, 'ino': os.lstat(top).st_ino})
        for root, dirs, files in os.walk(top):
            for d in dirs:
                q = os.path.join(root, d);record['made_dirs'].append({'path': q, 'ino': os.lstat(q).st_ino})
            for f in files:
                q = os.path.join(root, f);st = os.lstat(q)
                record['made'].append({'path': q, 'ino': st.st_ino, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns})
    elif os.path.lexists(top):
        st = os.lstat(top);record['made'].append({'path': top, 'ino': st.st_ino, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns})


def _verify_cp(found, record, got):
    files = 0
    for i in found['items']:
        if not os.path.lexists(i['to']):return False, '%s is not there' % hr.tilde(i['to'])
        _walk_made(i['to'], record)
        n, size = _tally(i['to'])
        if (n, size) != (i['count'], i['size']):return False, '%s holds %s of %s, not %s' % (hr.tilde(i['to']), bx.count_words(n, 'file'), bx.size_words(size), bx.size_words(i['size']))
        files += n
    return True, '%s read back at their sizes' % bx.count_words(files, 'file')


def _verify_mv(found, record, got):
    for i in found['items']:
        try:ok = os.lstat(i['to']).st_ino == i['ino'] and not os.path.lexists(i['from'])
        except OSError:
            ok = False
        if not ok:return False, '%s is not where it was to go' % hr.tilde(i['from'])
        record['moves'].append({'from': i['from'], 'to': i['to'], 'ino': i['ino']})
    return True, '%s read back in its new place' % bx.count_words(len(found['items']), 'thing')


def _verify_ln(found, record, got):
    i = found['items'][0]
    if not os.path.islink(i['path']) or os.readlink(i['path']) != i['target']:return False, '%s is not the link' % hr.tilde(i['path'])
    record['links'].append({'path': i['path'], 'target': i['target'], 'ino': os.lstat(i['path']).st_ino})
    return True, '%s is a link to %s, read back' % (hr.tilde(i['path']), i['target'])


def _verify_chmod(found, record, got):
    for i in found['items']:
        st = os.lstat(i['path'])
        if st.st_ino != i['ino'] or st.st_mode & 0o7777 != i['new']:return False, '%s has %s' % (hr.tilde(i['path']), mode_words(st.st_mode & 0o7777))
        record['modes'].append({'path': i['path'], 'ino': i['ino'], 'old': i['old'], 'new': i['new']})
    return True, 'the mode read back on %s' % bx.count_words(len(found['items']), 'file')


def _verify_tar_c(found, record, got):
    i = found['items'][0]
    if not os.path.isfile(i['path']):return False, '%s is not there' % hr.tilde(i['path'])
    _walk_made(i['path'], record)
    try:
        with tarfile.open(i['path']) as t:names = [m.name for m in t if m.isfile()]
    except (tarfile.TarError, OSError, EOFError) as exc:
        return False, '%s could not be read back (%s)' % (hr.tilde(i['path']), str(exc)[:60])
    if len(names) != i['count']:return False, 'it holds %s, not %s' % (bx.count_words(len(names), 'file'), bx.count_words(i['count'], 'file'))
    return True, '%s, read back: %s in it' % (hr.tilde(i['path']), bx.count_words(len(names), 'file'))


def _verify_tar_x(found, record, got):
    for i in found['items']:
        p = i['path']
        if (i['dir'] and not os.path.isdir(p)) or (not i['dir'] and (not os.path.isfile(p) or os.lstat(p).st_size != i['size'])):
            return False, '%s is not there as the archive has it' % hr.tilde(p)
    for t in found.get('tops') or ():_walk_made(t, record)
    return True, '%s read back at their sizes' % bx.count_words(sum(1 for i in found['items'] if not i['dir']), 'file')


VERIFY = {'bin': _verify_bin, 'mkdir': _verify_mkdir, 'touch': _verify_touch, 'cp': _verify_cp, 'mv': _verify_mv, 'ln': _verify_ln,
          'chmod': _verify_chmod, 'tar_c': _verify_tar_c, 'tar_x': _verify_tar_x, 'rename_ul': _verify_mv, 'rename_perl': _verify_mv}


def undo(kernel, args, principal):
    """Undo one run: each thing put back only when it is as the run left it; what changed since is named, never forced."""
    from . import home_trash
    found = load(kernel, args['run'])
    if found['undone']:raise Refused('COMMAND_UNDONE: already taken back')
    if found['kind'] in ('read', 'network'):raise Refused('COMMAND_NOTHING_TO_UNDO: it only read, so there is nothing to take back')
    record = json.loads(found['record'] or '{}');back, left = [], []
    for t in reversed(record.get('trashed') or []):
        if os.path.lexists(t['original']):left.append('%s: its place is taken now' % hr.tilde(t['original']));continue
        try:home_trash.restore(t['name']);back.append(hr.tilde(t['original']))
        except ValueError as exc:
            left.append('%s: %s' % (hr.tilde(t['original']), str(exc).split(': ', 1)[-1]))
    for m in reversed(record.get('moves') or []):
        try:ok = os.lstat(m['to']).st_ino == m['ino']
        except OSError:
            ok = False
        if not ok:left.append('%s: not where it was left' % hr.tilde(m['to']));continue
        if os.path.lexists(m['from']):left.append('%s: its old name is taken now' % hr.tilde(m['from']));continue
        os.rename(m['to'], m['from']);back.append(hr.tilde(m['from']))
    for m in record.get('modes') or []:
        st = os.lstat(m['path'])
        if st.st_ino != m['ino'] or st.st_mode & 0o7777 != m['new']:left.append('%s: its mode changed since' % hr.tilde(m['path']));continue
        os.chmod(m['path'], m['old']);back.append(hr.tilde(m['path']))
    for m in record.get('times') or []:
        st = os.lstat(m['path'])
        if st.st_ino != m['ino'] or st.st_mtime_ns != m['set_ns']:left.append('%s: changed since' % hr.tilde(m['path']));continue
        os.utime(m['path'], ns=(m['atime_ns'], m['mtime_ns']));back.append(hr.tilde(m['path']))
    for m in record.get('links') or []:
        if os.path.islink(m['path']) and os.readlink(m['path']) == m['target']:os.unlink(m['path']);back.append(hr.tilde(m['path']))
        else:left.append('%s: not the link it made' % hr.tilde(m['path']))
    made, dirs = record.get('made') or [], record.get('made_dirs') or []
    plan_ = json.loads(found['plan'] or '{}')
    if all(i.get('what') == 'dir' for i in plan_.get('items') or []) and dirs and not made:      # mkdir: empty folders taken away
        for d in sorted(dirs, key=lambda d: -len(d['path'])):
            try:os.rmdir(d['path']);back.append(hr.tilde(d['path']))
            except OSError:
                if os.path.lexists(d['path']):left.append('%s: not empty now, so it stays' % hr.tilde(d['path']))
    else:
        top = [d for d in dirs if not any(hr.within(d['path'], o['path']) and d['path'] != o['path'] for o in dirs)]
        inside = [m for m in made if any(hr.within(m['path'], d['path']) for d in top)]
        for d in top:
            mine = [m for m in inside if hr.within(m['path'], d['path'])]
            if any(not bx._same(m['path'], m) for m in mine if os.path.lexists(m['path'])) or bx._extra(d['path'], mine, dirs):
                left.append('%s: holds something changed or added since' % hr.tilde(d['path']));continue
            if os.path.lexists(d['path']):home_trash.put(d['path']);back.append(hr.tilde(d['path']))
        for m in made:
            if m in inside:continue
            if bx._same(m['path'], m):home_trash.put(m['path']);back.append(hr.tilde(m['path']))
            elif os.path.lexists(m['path']):left.append('%s: changed since it was made' % hr.tilde(m['path']))
    from . import files_service
    with files_service.opened(kernel) as db:
        ensure(db);db.execute('UPDATE command_runs SET undone=? WHERE id=?', (bx._now_ms(), args['run']))
    return {'run': args['run'], 'back': back, 'left': left, 'verified': not left,
            'words': ('%s put back.' % bx.count_words(len(back), 'thing') if back else 'Nothing needed putting back.') +
                     (' Left as it is: %s.' % '; '.join(left[:4]) if left else '')}


def runs(kernel, args, principal):
    from . import files_service
    with files_service.opened(kernel) as db:
        ensure(db)
        rows = db.execute('SELECT id, at, argv, kind, by, state, exit, verified, checked, undone FROM command_runs ORDER BY at DESC LIMIT ?',
                          (int(args.get('limit') or 30),)).fetchall()
    return {'runs': [{'run': r['id'], 'at': r['at'], 'line': line_of(json.loads(r['argv'])), 'kind': r['kind'], 'by': r['by'], 'state': r['state'],
                      'exit': r['exit'], 'verified': bool(r['verified']), 'checked': r['checked'], 'undone': bool(r['undone'])} for r in rows]}


def output(kernel, args, principal):
    found = load(kernel, args['run'])
    line = line_of(json.loads(found['argv']))
    data = as_data(found['out'] or '', line)
    return {'run': found['id'], 'line': line, 'lines': data['lines'], 'flagged': data['flagged'], 'model_page': data['model_page'],
            'state': found['state'], 'verified': bool(found['verified']), 'checked': found['checked']}


def dispatch(kernel, op, args, principal):
    try:
        if op == 'command.classify':
            if args.get('line'):return from_line(args['line'], args.get('by', 'owner'))
            if args.get('argv'):return classify(args['argv'], args.get('by', 'owner'))
            raise Refused('COMMAND_EMPTY: give a line or an argv')
        if op == 'command.plan':
            v = classify(args['argv'], args.get('by', 'owner'))
            if not v['ok']:raise Refused('%s: %s' % (v['code'], v['why']))
            if v['kind'] == 'read':raise Refused('COMMAND_A_READ: it only reads, so it runs at once (command.read)')
            return {**plan(kernel, v), 'line': v['line'], 'says': v['says'], 'kind': v['kind'], 'host': v.get('host', '')}
        if op == 'command.read':return read(kernel, args, principal)
        if op == 'command.run':return run(kernel, args, principal)
        if op == 'command.undo':return undo(kernel, args, principal)
        if op == 'command.runs':return runs(kernel, args, principal)
        if op == 'command.output':return output(kernel, args, principal)
    except bx.Refused as exc:
        raise Refused(str(exc).replace('BOX_', 'COMMAND_', 1)) from None
    raise ValueError('COMMAND_UNKNOWN_OPERATION')


# ---- the model proposes an argv (the COMMAND turn kind) -------------------------------------------------------------------------
def _brief():
    return ('You propose one command for the owner\'s request, as a JSON list of words: the program, then each argument. '
            'There is no shell: no pipe, no redirection, no variable, no pattern for a shell to expand. Use only the programs '
            'listed. Answer [] when no single command does it. Nothing runs from your answer: a classifier checks it and the '
            'owner sees the exact line first.')


def _stable(i):
    return 'Programs that only read: %s\nPrograms that change files (they wait for the owner): %s' % (', '.join(i['reads']), ', '.join(i['changes']))


def _last(i):
    return 'Request: “%s”' % i['request']


def _grammar(i):
    word = r'"\"" [^"\\]{1,60} "\""'
    return '\n'.join(['root ::= "[]" | "[" w ( ", " w ){0,11} "]"', 'w ::= ' + word])


def parse_model(said):
    """The model's answer as an argv, or model_words.Invalid: a JSON list of short strings, and nothing else."""
    from . import model_words
    text = said.for_check().strip() if isinstance(said, model_words.ModelSaid) else str(said).strip()
    try:value = json.loads(text)
    except ValueError:
        raise model_words.Invalid('COMMAND_SHAPE') from None
    if not isinstance(value, list) or not all(isinstance(w, str) and 0 < len(w) <= 200 for w in value) or len(value) > 24:
        raise model_words.Invalid('COMMAND_SHAPE')
    return value


def check_model(argv, i=None):
    """The desk disposes: the model's argv through the classifier (as the model's: never a private place). A Verdict."""
    from . import turns
    if not argv:return turns.Verdict('UNSETTLED', value=None, why=('COMMAND_NONE',), checks=(('argv', True, '[]'),))
    v = classify(argv, 'model')
    if not v['ok']:return turns.Verdict('REFUSED', why=('COMMAND_REFUSED',), checks=(('argv', False, v['line']), ('why', False, v['why'])))
    return turns.Verdict('TAKEN', value={'argv': v['argv'], 'line': v['line'], 'kind': v['kind']}, checks=(('argv', True, v['line']),))


def _fallback(i):
    from . import turns
    return turns.Fallback('PATTERNS', i['desk']) if i.get('desk') else turns.Fallback('CANNOT_TELL', None)


def _kind():
    from . import turns
    return turns.register(turns.TurnKind(name='COMMAND', version=1, switch='choosing', brief=_brief, stable=_stable, last=_last,
                                         grammar=_grammar, caps=turns.Caps(new_tokens=1600, answer_tokens=320, deadline_ms=20000),
                                         parse=lambda said, i: parse_model(said), check=lambda obj, i: check_model(obj, i), fallback=_fallback, paper=''))


def model_inputs(text):
    reads = sorted(n for n, forms in cf.TABLE.items() if any(not f.get('refuse') and f['classes'] == (cf.R,) for f in forms))
    changes = sorted(n for n, forms in cf.TABLE.items() if any(not f.get('refuse') and cf.C in f['classes'] for f in forms))
    return {'request': ' '.join(str(text).split())[:400], 'reads': reads, 'changes': changes, 'desk': dictionary(text)}


def propose(text, request):
    """With a live model: (argv or None, the refusal's words or '', by). The model's line passed the classifier, else
    her dictionary's (or nothing)."""
    from . import turns
    got = turns.ask(_kind(), model_inputs(text), request)
    if got.by_model:return (got.value['argv'] if got.value else None), '', 'model'
    refused = ''
    verdict = getattr(got, 'verdict', None)
    if verdict is not None and getattr(verdict, 'state', '') == 'REFUSED':
        checks = dict((k, w) for k, _, w in verdict.checks)
        refused = '%s (%s)' % (checks.get('argv', ''), checks.get('why', ''))
    desk = got.value
    return (desk['argv'] if desk else None), refused, 'dictionary'
