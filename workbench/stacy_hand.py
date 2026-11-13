"""Stacy's hand: how far she acts by herself, what always asks, and how an act of hers is taken back.

The owner, 13 November 2026: "I want to discuss giving Stacy agency to control all of Graphite just like I can so I can
tell her to do something and an artifact is made just as if I had saved a file. I'm less concerned about her running out
of control." Asked what should still ask: "anything that can't be undone, by rule, would always force" her to ask, such
as emptying the Trash or anything leaving the computer; and "some terminal commands are reasonable for" her "to have
control over". Asked whether she acts unasked: "I kind of want her to be autonomous".

Until 0.5.3 the rule was: she reads freely, and a change waits for Approve. From here it is a dial with three places:

  Ask first      as before: every change waits for the owner's Approve.
  Do and show    she makes the changes the Kernel calls `execute` (a number set, a page kept, a file written) at once,
                 says what she did, and each act is one line in her trail with one Undo where it can be taken back.
                 What the Kernel itself marks `approve` still waits.
  Free hand      she also makes the `approve` changes, and may act on what she notices.

On every place, what cannot be undone asks: that list is ALWAYS_ASKS below, written so the owner can read it and strike
a line. A read never asks. Nothing here runs anything: it answers "is this hers to do now", "why does it ask" and "what
line takes it back"; the window does the rest (shell2.SlateFace.stage).
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

# What cannot be undone always asks, whatever the dial says: (operations it covers, why it asks).
# 0.7.0 widened it after every operation the Kernel has was run against the rule: with a free hand it would have let
# through, had they ever been put up, transfers, mail, pairing, publishing, packet capture, and several kinds of
# forgetting. None could be reached by her then; they are closed here before anything else can reach them.
ALWAYS_ASKS = (
    (('*.send', 'exchange.*', 'pills.*', 'notes.exchange.*', 'remote.*', 'programs.transfer.*', 'programs.mail.*', 'programs.delivery.*',
      '*.pair', '*.unpair', '*.fetch', '*.upload', '*.download', '*.publish'), 'it reaches another computer, or sends something off this one'),
    (('network.capture.*',), 'it listens to what passes on this computer’s network'),
    (('*.delete', '*.remove', '*.purge', '*.erase', '*.wipe', '*.forget', '*.discard', '*.revoke', '*.clear', '*.clear_staging', '*.takeover',
      '*.reset'), 'what it removes cannot be brought back'),
    (('*.empty', 'trash.*'), 'the Trash, once emptied, cannot be brought back'),
    (('power.*', 'session.*'), 'it ends the session or turns this computer off'),
    (('releases.*', 'repairs.*', '*.install'), 'it changes the program itself'),
    (('shell.*', 'terminal.*'), 'a command in the Terminal can do anything'),
)
LEAVES = ('address', 'peer', 'url', 'host', 'recipient')      # an argument by one of these names reaches another computer

# Terminal commands that only read, which she may run herself ("some terminal commands are reasonable"). One command, no
# pipes, no redirection, nothing substituted; and for a few, only their reading forms.
TERMINAL_READS = ('ls', 'pwd', 'cat', 'head', 'tail', 'wc', 'df', 'du', 'free', 'uptime', 'uname', 'whoami', 'id', 'date', 'hostname', 'lsblk', 'lscpu',
                  'lsusb', 'lspci', 'sensors', 'ps', 'which', 'file', 'stat', 'find', 'grep', 'ip', 'journalctl', 'dmesg', 'nproc', 'env', 'printenv')
TERMINAL_MARKS = ('|', '&', ';', '>', '<', '`', '$(', '\n', '\r')
IP_OBJECTS = ('addr', 'address', 'a', 'link', 'l', 'route', 'r', 'neigh', 'neighbor', 'neighbour', 'n', 'rule', 'ru')
IP_FLAGS = ('-4', '-6', '-br', '-brief', '-c', '-color', '-o', '-oneline', '-s', '-stats', '-statistics', '-d', '-details', '-h', '-human',
            '-human-readable', '-j', '-json', '-p', '-pretty', '-r', '-resolve')
IP_CHANGES = ('add', 'del', 'delete', 'set', 'flush', 'change', 'replace', 'append', 'prepend', 'exec', 'save', 'restore', 'update', 'monitor')


def _ip_reads(words):
    """ip only in its showing forms: a known object (addr, link, route, neigh, rule), flags that only change how it prints,
    and no word that changes anything or runs something (ip netns exec and ip vrf exec run any program; -batch runs a file)."""
    rest = words[1:];named = [w for w in rest if not w.startswith('-')]
    return (all(w in IP_FLAGS for w in rest if w.startswith('-')) and (not named or named[0] in IP_OBJECTS)
            and not any(w in IP_CHANGES for w in named))


def _date_reads(words):
    """date only shows: a format (+...), a flag, or the date given to -d / -r. A bare word after date sets the clock."""
    skip = False
    for w in words[1:]:
        if skip:
            skip = False;continue
        if w in ('-d', '--date', '-r', '--reference', '-f', '--file'):
            skip = True;continue
        if w in ('-s', '--set') or w.startswith('--set=') or not w.startswith(('-', '+')):return False
    return True


TERMINAL_ONLY = {'find': lambda words: not any(re.match(r'-(delete|exec|execdir|ok|okdir|fprint|fprint0|fprintf|fls)$', w) for w in words),
                 'date': _date_reads,
                 'ip': _ip_reads,
                 'file': lambda words: not any(w in ('-C', '--compile') or (w.startswith('-') and not w.startswith('--') and 'C' in w) for w in words),
                 'sensors': lambda words: not any(w in ('-s', '--set') for w in words),
                 'dmesg': lambda words: not any(w in ('-C', '-c', '--clear', '--read-clear', '-n', '--console-level', '-D', '-E', '--console-off', '--console-on') for w in words),
                 'journalctl': lambda words: not any(w.startswith(('--vacuum', '--rotate', '--flush', '--sync', '--setup-keys', '--update-catalog',
                                                                   '--relinquish-var', '--smart-relinquish-var')) for w in words),
                 'hostname': lambda words: len(words) == 1 or all(w.startswith('-') and w not in ('-F', '--file', '-b', '--boot') for w in words[1:]),
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
    """Whether, with the dial at `place`, an operation of this Kernel scope is hers to do now without asking."""
    if scope == 'read':return True               # a read never asks
    if why_asks(operation, arguments):return False
    if place == 'show':return scope == 'execute'
    if place == 'free':return scope in ('execute', 'approve')
    return False


MAKE = re.compile(r'^\s*(?:please\s+)?(?:make|create|start|write|save|keep)\s+(?:me\s+)?(?:a|an)\s+(?:new\s+)?(folder|file|page|document|note)\s+(?:called|named)\s+'
                  r'(.+?)(?:\s*,?\s*(?:saying|that\s+says|which\s+says|with\s+the\s+words|containing)\s*:?\s+(.+))?\s*$', re.IGNORECASE | re.DOTALL)
QUOTES = '“”"\'‘’ '


def made(text):
    """“Make a folder called Bracket”, “write a file called plan.txt saying cut the stock first”, “start a page called Bench
    plan”: the thing asked for, as (kind, name, words), or None. kind is 'folder', 'file', 'page' or 'note'. A file with no
    ending is a .txt."""
    asked = MAKE.match(str(text or ''))
    if not asked:return None
    kind = asked.group(1).lower();name = re.sub(r'\s+', ' ', asked.group(2)).strip().strip(QUOTES).rstrip('.').strip();words = (asked.group(3) or '').strip()
    if words[:1] in '“"‘\'' and words[-1:] in '”"’\'':words = words[1:-1].strip()
    if not name or len(name) > 120:return None
    if kind == 'document':kind = 'page'
    if kind == 'file' and '.' not in name.rsplit('/', 1)[-1]:name += '.txt'
    return kind, name, words


def takes_back(operation, arguments, result):
    """The line that takes an act back exactly, or '' when there is none. Only what can be put back as it was is offered:
    a number set on a sheet goes back to what it said, and only if the sheet has not been saved again since."""
    if operation == 'field.set' and isinstance(result, dict) and result.get('was') not in (None, '') and result.get('revision') is not None:
        back = {'id': result.get('id') or (arguments or {}).get('id'), 'cell': result.get('cell') or (arguments or {}).get('cell'),
                'value': str(result['was']), 'expected_revision': result['revision']}
        if back['id'] and back['cell']:return '/field.set ' + json.dumps(back, ensure_ascii=False, separators=(', ', ': '))
    # A file or a folder she made new goes to the Trash, which gives it back: only when nothing was there before (a file
    # written over an earlier one kept a version, and is not hers to trash).
    if operation in ('files.write', 'files.mkdir') and isinstance(result, dict) and result.get('path') and not result.get('kept_version'):
        return '/files.trash ' + json.dumps({'path': str(result['path'])}, ensure_ascii=False, separators=(', ', ': '))
    return ''


def record(state, words, line, undo='', word='', ok=True, now=None):
    """Add one act of hers to the trail kept in the session's state. Returns the entry."""
    entry = {'at': time.strftime('%Y-%m-%d %H:%M', time.localtime(now)), 'words': str(words)[:200], 'line': str(line)[:1200], 'undo': str(undo)[:1200],
             'word': str(word)[:200], 'state': 'done' if ok else 'refused'}
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
    """A trail read from a saved session, kept only in the shape written here."""
    out = []
    for e in value if isinstance(value, list) else []:
        if isinstance(e, dict) and all(isinstance(e.get(k, ''), str) for k in ('at', 'words', 'line', 'undo', 'word', 'state')) and e.get('state') in ('done', 'undone', 'refused'):
            out.append({k: str(e.get(k, ''))[:1200] for k in ('at', 'words', 'line', 'undo', 'word', 'state')})
    return out[-KEPT:]


def terminal_hers(text):
    """Whether a Terminal line is one she may run herself: a single command from TERMINAL_READS, in a form that only reads."""
    text = str(text or '').strip()
    if not text or any(mark in text for mark in TERMINAL_MARKS):return False
    try:words = shlex.split(text)
    except ValueError:return False
    if not words or words[0] not in TERMINAL_READS:return False
    only = TERMINAL_ONLY.get(words[0])
    return bool(only(words)) if only else True
