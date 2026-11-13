"""Stacy's hand: how far she acts by herself, what always asks, and how an act of hers is taken back.

The owner, 13 November 2026: "I want to discuss giving Stacy agency to control all of Graphite just like I can so I can
tell her to do something and an artifact is made just as if I had saved a file. I'm less concerned about her running out
of control." Asked what should still ask: "anything that can't be undone, by rule, would always force" her to ask, such
as emptying the Trash or anything leaving the computer; and "some terminal commands are reasonable for" her "to have
control over". Asked whether she acts unasked: "I kind of want her to be autonomous".

Until 0.5.3 the rule was: she reads freely, and a change waits for Approve. From here it is a dial with three places:

  Ask first      as before: every change waits for the owner's Approve.
  Do and show    she makes, at once, the ordinary changes named in HERS_SHOW (a number set, a page kept, a file written),
                 says what she did, and each act is one line in her trail with one Undo where it can be taken back.
  Free hand      she also makes the changes named in HERS_FREE (working a calculation again, opening a program on a
                 project), and may act on what she notices.

The rule is an allow-list (since 0.7.0, after other readers went over it): she does by herself only what is named here,
each name an operation whose effect was looked at. Anything not named asks, whatever the dial says, so an operation
added to the program later asks until someone puts it on a list. ALWAYS_ASKS is the second net and the words: what
cannot be undone, or leaves the computer, asks even if it were ever named. A read never asks. Nothing here runs
anything: it answers "is this hers to do now", "why does it ask" and "what line takes it back"; the window does the
rest (shell2.SlateFace.stage).
"""
import fnmatch
import json
import re
import shlex
import time

LEVELS = (('ask', 'Ask first'), ('show', 'Do and show'), ('free', 'Free hand'))
KEY = 'stacy_hand'          # the session's key for the dial
OPENS_WITH = 'show'         # a workspace that has never chosen: she does and shows (the owner asked for agency)
TRAIL = 'stacy_trail'       # the session's key for her trail
KEPT = 40                   # acts kept in the trail
SAYS = {'ask': 'asks before any change', 'show': 'does and shows', 'free': 'has a free hand'}

# What she does by herself, by name. Do and show: what makes or sets something that can be put back or stands beside what
# was there. Free hand adds what the records mark for approval and what opens a program on a project.
HERS_SHOW = ('field.set', 'field.brief.keep', 'files.write', 'files.mkdir', 'files.trash', 'documents.create', 'ideas.capture', 'agenda.add',
             'investigation.refresh', 'investigation.continue', 'conditions.recheck', 'jobs.resume')
HERS_FREE = HERS_SHOW + ('office.datasheet.recheck', 'investigation.claim', 'programs.godot.open', 'programs.godot.play', 'programs.blender.open',
                         'programs.inkscape.open', 'programs.freecad.open')
UNDOES = ('field.set', 'files.trash')      # the only operations an Undo line may name

# What cannot be undone always asks, whatever the dial says: (operations it covers, why it asks).
ALWAYS_ASKS = (
    (('*.send', 'exchange.*', 'pills.*', 'notes.exchange.*', 'remote.*', 'programs.transfer.*', 'programs.mail.*', 'programs.delivery.*',
      '*.pair', '*.unpair', '*.fetch', '*.upload', '*.download', '*.publish', 'research.*', 'deployment.*'), 'it reaches another computer, or sends something off this one'),
    (('network.capture.*',), 'it listens to what passes on this computer’s network'),
    (('*.delete', '*.remove', '*.purge', '*.erase', '*.wipe', '*.forget', '*.discard', '*.revoke', '*.clear', '*.clear_staging', '*.takeover',
      '*.reset'), 'what it removes cannot be brought back'),
    (('*.cancel', '*.stop', '*.retire', '*.review'), 'what it stops or settles cannot be put back'),
    (('*.empty', 'trash.*'), 'the Trash, once emptied, cannot be brought back'),
    (('power.*', 'session.*'), 'it ends the session or turns this computer off'),
    (('releases.*', 'repairs.*', '*.install'), 'it changes the program itself'),
    (('shell.*', 'terminal.*'), 'a command in the Terminal can do anything'),
)
LEAVES = ('address', 'peer', 'url', 'host', 'recipient')      # an argument by one of these names reaches another computer

# Terminal commands that only read, which she may run herself ("some terminal commands are reasonable"). The line is run
# by the owner's shell, so it must mean to the shell exactly what it means here: one command; no pipe, redirection or
# second command; and none of the characters a shell expands or substitutes ($ ` \ { } ( ) ! #), so that the words
# checked are the words run. A command with forms that change something is held to an exact list of its reading
# options (no abbreviations, no options run together), and may carry a pattern (* ? [ ]) only inside quotes, where the
# shell leaves it alone: an expanded file name could otherwise arrive as an option.
TERMINAL_READS = ('ls', 'pwd', 'cat', 'head', 'tail', 'wc', 'df', 'du', 'free', 'uptime', 'uname', 'whoami', 'id', 'date', 'hostname', 'lsblk', 'lscpu',
                  'lsusb', 'lspci', 'sensors', 'ps', 'which', 'file', 'stat', 'find', 'grep', 'ip', 'journalctl', 'dmesg', 'nproc', 'env', 'printenv')
TERMINAL_MARKS = ('|', '&', ';', '>', '<', '`', '$', '\\', '{', '}', '(', ')', '!', '#', '\n', '\r')
PATTERNS = '*?[]'
IP_OBJECTS = ('addr', 'address', 'a', 'link', 'l', 'route', 'r', 'neigh', 'neighbor', 'neighbour', 'n', 'rule', 'ru')
IP_FLAGS = ('-4', '-6', '-br', '-brief', '-c', '-color', '-o', '-oneline', '-s', '-stats', '-statistics', '-d', '-details', '-h', '-human',
            '-human-readable', '-j', '-json', '-p', '-pretty', '-r', '-resolve')
IP_SHOWS = ('show', 'list', 'lst', 'ls')      # written out: ip takes "s" for set, not for show


def _held(words, flags=(), valued=(), others=True, numbers=False, plus=False):
    """Whether every option of a command is one of its reading options, written exactly: `flags` stand alone, `valued`
    take the next word (or --name=value), `numbers` allows -5, `plus` allows +FORMAT; `others`: whether plain words
    (files, names) may follow."""
    skip = False
    for w in words[1:]:
        if skip:
            skip = False;continue
        if w.startswith('-') and len(w) > 1:
            if w in flags:continue
            if w in valued:
                skip = True;continue
            if w.startswith('--') and '=' in w and w.split('=', 1)[0] in valued:continue
            if numbers and re.fullmatch(r'-\d+', w):continue
            return False
        if plus and w.startswith('+'):continue
        if not others:return False
    return True


def _ip_reads(words):
    """ip only in its showing forms: flags that change how it prints, a known object, and then nothing or show / list
    written out. (ip netns exec and ip vrf exec run any program; -batch runs a file; "ip l s" is set.)"""
    rest = words[1:];named = [w for w in rest if not w.startswith('-')]
    return (all(w in IP_FLAGS for w in rest if w.startswith('-')) and (not named or named[0] in IP_OBJECTS)
            and (len(named) < 2 or named[1] in IP_SHOWS))


TERMINAL_ONLY = {
    'find': lambda words: not any(re.match(r'-(delete|exec|ok|fprint|fls)', w) for w in words),
    'date': lambda words: _held(words, flags=('-u', '--utc', '--universal', '-R', '--rfc-email', '-I', '--iso-8601', '--debug'),
                                valued=('-d', '--date', '-r', '--reference', '--iso-8601', '--rfc-3339'), others=False, plus=True),
    'ip': _ip_reads,
    'file': lambda words: _held(words, flags=('-b', '--brief', '-i', '--mime', '--mime-type', '--mime-encoding', '-L', '--dereference', '-h',
                                              '--no-dereference', '-z', '--uncompress', '-k', '--keep-going', '-p', '--preserve-date', '-s',
                                              '--special-files', '-N', '--no-pad', '-0', '--print0', '-E')),
    'sensors': lambda words: _held(words, flags=('-A', '--no-adapter', '-u', '-f', '--fahrenheit', '-j', '--bus-list')),
    'dmesg': lambda words: _held(words, flags=('-T', '--ctime', '-H', '--human', '-k', '--kernel', '-u', '--userspace', '-x', '--decode', '-e',
                                               '--reltime', '-t', '--notime', '-J', '--json'), valued=('-l', '--level', '-f', '--facility'), others=False),
    'journalctl': lambda words: _held(words, flags=('-b', '--boot', '-k', '--dmesg', '-e', '--pager-end', '-r', '--reverse', '-x', '--catalog', '-a',
                                                    '--all', '-q', '--quiet', '--no-pager', '--utc', '--no-hostname', '-m', '--merge', '--system',
                                                    '--user', '--list-boots', '--disk-usage'),
                                      valued=('-n', '--lines', '-u', '--unit', '-p', '--priority', '-S', '--since', '-U', '--until', '-g', '--grep',
                                              '-o', '--output', '-t', '--identifier', '--user-unit'), numbers=True),
    'hostname': lambda words: _held(words, flags=('-f', '--fqdn', '--long', '-s', '--short', '-d', '--domain', '-i', '--ip-address', '-I',
                                                  '--all-ip-addresses', '-A', '--all-fqdns', '-a', '--alias', '-y', '--yp', '--nis'), others=False),
    'tail': lambda words: _held(words, flags=('-q', '--quiet', '--silent', '-v', '--verbose', '-z', '--zero-terminated'),
                                valued=('-n', '--lines', '-c', '--bytes'), numbers=True),      # not -f: a command that never ends holds the Terminal
    'lspci': lambda words: _held(words, flags=('-v', '-vv', '-vvv', '-k', '-n', '-nn', '-nnn', '-t', '-tv', '-tvv', '-D', '-m', '-mm', '-b', '-x'),
                                 valued=('-s', '-d'), others=False),      # not -q / -Q: they ask a server on the network what a device is
    'env': lambda words: len(words) == 1}


def level(host):
    """The dial's place for this workspace: 'ask', 'show' or 'free'."""
    state = getattr(getattr(host, 'session', None), 'state', None) or {}
    return state.get(KEY) if state.get(KEY) in dict(LEVELS) else OPENS_WITH


def choose(host, key):
    """Set the dial. Returns the place it now has."""
    if key in dict(LEVELS) and hasattr(host, 'session'):host.session.state[KEY] = key
    return level(host)


def why_asks(operation, arguments=None):
    """Why this operation asks on every place of the dial, in words; '' when the dial decides."""
    name = str(operation or '')
    for patterns, why in ALWAYS_ASKS:
        if any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns):return why
    if isinstance(arguments, dict) and any(key in arguments for key in LEAVES):return 'it reaches another computer'
    return ''


def hers(place, scope, operation, arguments=None):
    """Whether, with the dial at `place`, an operation of this Kernel scope is hers to do now without asking: a read
    always; otherwise only an operation named on the list for that place, at the scope that place takes, and never one
    that ALWAYS_ASKS covers."""
    if scope == 'read':return True               # a read never asks
    name = str(operation or '')
    if place not in ('show', 'free') or why_asks(name, arguments):return False
    if place == 'show':return scope == 'execute' and name in HERS_SHOW
    return scope in ('execute', 'approve') and name in HERS_FREE


def why_waits(place, scope, operation, arguments=None):
    """In words, why an operation that is not hers now waits for the owner."""
    return (why_asks(operation, arguments) or ('the records mark it for your approval' if scope == 'approve' and str(operation or '') in HERS_FREE
                                                else 'it is not among the things I do by myself'))


MAKE = re.compile(r'^\s*(?:please\s+)?(?:make|create|start|write|save|keep)\s+(?:me\s+)?(?:a|an)\s+(?:new\s+)?(?P<kind>folder|file|page|document|note)\s+(?:called|named)\s+'
                  r'(?:[“"](?P<quoted>[^“”"]+)[”"]|(?P<plain>.+?))(?:\s*,?\s*(?:saying|that\s+says|which\s+says|with\s+the\s+words|containing)\s*:?\s+(?P<words>.+))?\s*$',
                  re.IGNORECASE | re.DOTALL)
QUOTES = '“”"\'‘’ '


def made(text):
    """“Make a folder called Bracket”, “write a file called plan.txt saying cut the stock first”, “start a page called Bench
    plan”: the thing asked for, as (kind, name, words), or None. kind is 'folder', 'file', 'page' or 'note'. A file with no
    ending is a .txt. A name in quotes is the whole of what is between them (“Notes on saying no” is one name); a folder
    holds no words, so everything after "called" is its name."""
    asked = MAKE.match(str(text or ''))
    if not asked:return None
    kind = asked.group('kind').lower();words = (asked.group('words') or '').strip()
    name = asked.group('quoted') if asked.group('quoted') is not None else asked.group('plain')
    if kind == 'folder' and words and asked.group('quoted') is None:      # "a folder called Parts containing lead": that is its name
        name = str(text)[asked.start('plain'):].strip();words = ''
    name = re.sub(r'\s+', ' ', name).strip().strip(QUOTES).rstrip('.').strip()
    if words[:1] in '“"‘\'' and words[-1:] in '”"’\'':words = words[1:-1].strip()
    if not name or len(name) > 120:return None
    if kind == 'document':kind = 'page'
    if kind == 'folder':words = ''
    if kind == 'file' and '.' not in name.rsplit('/', 1)[-1]:name += '.txt'
    return kind, name, words


def takes_back(operation, arguments, result):
    """The line that takes an act back exactly, or '' when there is none. Only what can be put back as it was is offered:
    a number set on a sheet goes back to what it said, and only if the sheet has not been saved again since; a file or a
    folder she made new goes to the Trash (which gives it back), and only while it is still as she made it (guard())."""
    if operation == 'field.set' and isinstance(result, dict) and result.get('was') not in (None, '') and result.get('revision') is not None:
        back = {'id': result.get('id') or (arguments or {}).get('id'), 'cell': result.get('cell') or (arguments or {}).get('cell'),
                'value': str(result['was']), 'expected_revision': result['revision']}
        if back['id'] and back['cell']:return '/field.set ' + json.dumps(back, ensure_ascii=False, separators=(', ', ': '))
    if operation in ('files.write', 'files.mkdir') and isinstance(result, dict) and result.get('path') and not result.get('kept_version'):
        return '/files.trash ' + json.dumps({'path': str(result['path'])}, ensure_ascii=False, separators=(', ', ': '))
    return ''


def guard(operation, arguments, result):
    """What must still be true for the Undo of something she made to run: [{'path', 'sha256'}] for a file (it still holds
    exactly the words she wrote), [{'path', 'items': 0}] for a folder (it is still empty). [] where the Undo line guards
    itself (a number set names the revision it expects)."""
    import hashlib
    if operation == 'files.write' and isinstance(result, dict) and result.get('path') and isinstance((arguments or {}).get('text'), str):
        return [{'path': str(result['path']), 'sha256': hashlib.sha256(arguments['text'].encode('utf-8')).hexdigest()}]
    if operation == 'files.mkdir' and isinstance(result, dict) and result.get('path'):
        return [{'path': str(result['path']), 'items': 0}]
    return []


def undo_allowed(line, guards=None):
    """Whether a line is one an Undo may run: one of the two this module writes (a number set back; something she made
    moved to the Trash), and for the Trash only with a guard that says what she made. A trail read back from a file is
    held to this, so nothing else can be run from it."""
    line = str(line or '').strip()
    if not line.startswith('/'):return False
    name, _, rest = line[1:].partition(' ')
    try:arguments = json.loads(rest) if rest.strip() else {}
    except ValueError:return False
    if name not in UNDOES or not isinstance(arguments, dict):return False
    if name == 'field.set':return set(arguments) == {'id', 'cell', 'value', 'expected_revision'}
    return set(arguments) == {'path'} and isinstance(arguments['path'], str) and bool(clean_guard(guards)) and any(g['path'] == arguments['path'] for g in clean_guard(guards))


def clean_guard(value):
    out = []
    for g in value if isinstance(value, list) else []:
        if not isinstance(g, dict) or not isinstance(g.get('path'), str) or not g['path'] or len(g['path']) > 1000:continue
        if isinstance(g.get('sha256'), str) and re.fullmatch(r'[0-9a-f]{64}', g['sha256']):out.append({'path': g['path'], 'sha256': g['sha256']})
        elif type(g.get('items')) is int and 0 <= g['items'] <= 1000:out.append({'path': g['path'], 'items': g['items']})
    return out[:64]


def record(state, words, line, undo='', word='', ok=True, now=None, guards=None):
    """Add one act of hers to the trail kept in the session's state. Returns the entry. An Undo line is kept only if it is
    one an Undo may run (undo_allowed)."""
    guards = clean_guard(guards)
    entry = {'at': time.strftime('%Y-%m-%d %H:%M', time.localtime(now)), 'words': str(words)[:200], 'line': str(line)[:1200],
             'undo': str(undo)[:1200] if undo_allowed(undo, guards) else '', 'word': str(word)[:200], 'state': 'done' if ok else 'refused', 'guard': guards}
    trail = [e for e in (state.get(TRAIL) or []) if isinstance(e, dict)]
    trail.append(entry);state[TRAIL] = trail[-KEPT:]
    return entry


def trail(state):
    """Her acts, the latest first."""
    return [e for e in reversed(state.get(TRAIL) or []) if isinstance(e, dict)]


def taken_back(state, entry):
    """Mark an act as taken back; its Undo is spent."""
    for e in state.get(TRAIL) or []:
        if isinstance(e, dict) and e.get('state') == 'done' and (e is entry or (e.get('at') == entry.get('at') and e.get('line') == entry.get('line'))):
            e['state'] = 'undone';e['undo'] = '';return True
    return False


def clean(value):
    """A trail read from a saved session, kept only in the shape written here: text fields as text, a state that is one of
    three, a guard in its own shape, and an Undo line only if it is one an Undo may run (anything else is dropped, so a
    damaged or altered file cannot put a line of its own behind "Undo this")."""
    out = []
    for e in value if isinstance(value, list) else []:
        if isinstance(e, dict) and all(isinstance(e.get(k, ''), str) for k in ('at', 'words', 'line', 'undo', 'word', 'state')) and e.get('state') in ('done', 'undone', 'refused'):
            kept = {k: str(e.get(k, ''))[:1200] for k in ('at', 'words', 'line', 'undo', 'word', 'state')};kept['guard'] = clean_guard(e.get('guard'))
            if not undo_allowed(kept['undo'], kept['guard']):kept['undo'] = ''
            out.append(kept)
    return out[-KEPT:]


def unquoted(text):
    """A line without what stands inside its quotes: where a shell would still expand a pattern."""
    return re.sub(r"'[^']*'|\"[^\"]*\"", '', str(text))


def terminal_hers(text):
    """Whether a Terminal line is one she may run herself: a single command from TERMINAL_READS, with no character a shell
    would expand or substitute, in a form that only reads; and, for a command that has changing forms, no pattern outside
    quotes."""
    text = str(text or '').strip()
    if not text or any(mark in text for mark in TERMINAL_MARKS):return False
    try:words = shlex.split(text)
    except ValueError:return False
    if not words or words[0] not in TERMINAL_READS:return False
    only = TERMINAL_ONLY.get(words[0])
    if only is None:return True
    if any(ch in unquoted(text) for ch in PATTERNS):return False
    return bool(only(words))
