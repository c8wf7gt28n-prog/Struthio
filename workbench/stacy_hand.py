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

0.8.7 B1, pick, never write: hers() and why_waits() take the change's basis (owner_words, owner_click, deduction,
model_pick); a change whose only basis is the model's pick is never hers at any place of the dial and comes as a card,
"The model suggests this. Nothing you said asks for it, so it's yours to say."; a change put to the owner carries an
origin on every argument (proposal(), origin()), and none is the model. See the block marked 0.8.7 B1 below.
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
# Her hand's moves on the desk (Kasandra's hand, first slice) are kept apart from the trail of what she changed: a turn can
# take a dozen moves, and forty data acts with an Undo must not be pushed out of reach by navigation.
DESK_TRAIL = 'desk_trail'
DESK_KEPT = 200
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
    (('*.empty', 'trash.*'), 'DELETE, once emptied, cannot be brought back'),
    (('power.*', 'session.*'), 'it ends the session or turns this computer off'),
    (('releases.*', 'repairs.*', '*.install'), 'it changes the program itself'),
    (('shell.*', 'terminal.*'), 'a command in the Terminal can do anything'),
    (('tolerances.set', 'tolerances.set_cell'), 'a tolerance is yours to say: it decides what I conclude'),   # 0.8.6 S1: on a sheet's cell too
    (('word.set', 'rules.set', 'quotes.rebind'), 'it is yours to say: it decides what I conclude'),   # 0.8.6 S3: your word (and S6's rules and quotes)
    (('board.keep',), 'a link kept by your word is recorded: it is yours to say, never mine'),   # 1.0 L2: a possible link becomes recorded only by your word
    (('sandbox.apply', 'sandbox.keep'), 'it changes your real files with what a utility made, or makes a utility a tool of yours: yours to say, every time'),   # 1.0 K6: the utility sandbox; Apply asks at every place of the dial
    (('web.search',), 'it sends your words off this computer, to a search service: shown first, sent only by your press'),   # 1.0 K8: search words always ask, never granted
)
LEAVES = ('address', 'peer', 'url', 'host', 'recipient')      # an argument by one of these names reaches another computer
ARGUMENT_ASKS = []            # 1.0 K9: callables(operation, arguments) -> why it always asks, or '' (a11y_hand: a button named Send, Delete, Install ...)

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
    for check in ARGUMENT_ASKS:      # 1.0 K9: what a press in another program names
        try:why = check(name, arguments)
        except Exception:  # noqa: BLE001 - a check that fails asks: the safe side
            why = 'it could not be told whether it asks'
        if why:return why
    return ''


def hers(place, scope, operation, arguments=None, basis=None):
    """Whether, with the dial at `place`, an operation of this Kernel scope is hers to do now without asking: a read
    always; otherwise only an operation named on the list for that place, at the scope that place takes, and never one
    that ALWAYS_ASKS covers. 0.8.7 B1: `basis` is why the change is on the table (BASES); a change whose only basis is
    the model's pick ('model_pick') is never hers, at any place of the dial. A read is unaffected."""
    if scope == 'read':return True               # a read never asks
    if basis is not None and basis not in BASES:return False      # a basis no one knows is never taken as a good one
    if basis == MODEL_PICK:return False          # 0.8.7 B1: pick, never write
    name = str(operation or '')
    if place not in ('show', 'free') or why_asks(name, arguments):return False
    if place == 'show':return scope == 'execute' and name in HERS_SHOW
    return scope in ('execute', 'approve') and name in HERS_FREE


def why_waits(place, scope, operation, arguments=None, basis=None):
    """In words, why an operation that is not hers now waits for the owner: what always asks, the model's pick alone
    (0.8.7 B1), the records' approval, the dial (at Ask first, an operation she does by herself at another place), or the
    lists."""
    if why_asks(operation, arguments):return why_asks(operation, arguments)
    if scope != 'read' and (basis == MODEL_PICK or (basis is not None and basis not in BASES)):return MODEL_PICK_WHY
    if scope == 'approve' and str(operation or '') in HERS_FREE:return 'the records mark it for your approval'
    if place == 'ask' and hers('free', scope, operation, arguments):return 'my hand is at Ask first'
    return 'it is not among the things I do by myself'


# == 0.8.7 B1 · Pick, never write (design 0.8.7, 5.2 and 3.5) ==========================================================================
# The model proposes; the system disposes. Two rules live here, beside the dial they bind:
#
# THE BASIS RULE. Every change put to her hand says why it is on the table: the owner's words ('owner_words', a change word
# of his outside quotes), his click ('owner_click', a button he pressed), a deduction of the desk's own rule ('deduction',
# what she would have done with no model), or the model's pick ('model_pick'). A change whose only basis is the model's pick
# is never hers at any place of the dial (hers() is False, why_waits() says MODEL_PICK_WHY); it comes as a card with
# MODEL_PICK_CARD, and when the owner takes it the trail says APPROVED_PICK. Reads and navigation are unaffected.
#
# EVERY ARGUMENT SAYS WHERE IT CAME FROM. A change proposed to the owner carries each argument as {value, origin}; the
# origin is one of ORIGINS: OWNER_WORDS (a span of his request), RECORD (a record at a revision, and a cell), SOURCE (a
# source at a revision, a line, and whether the doorway flagged it), DEDUCTION (the proof). There is no MODEL origin:
# arguments come from the option the desk built, never from the model's text, so a destination that appears only in the
# model's words can never be offered. proposal() refuses any argument without an origin, and any origin that is not one of
# the four (MODEL first among them). A destination taken from a file shows that line on the card (card()).
OWNER_WORDS, OWNER_CLICK, DEDUCTION, MODEL_PICK = 'owner_words', 'owner_click', 'deduction', 'model_pick'
BASES = (OWNER_WORDS, OWNER_CLICK, DEDUCTION, MODEL_PICK)
MODEL_PICK_WHY = 'the model suggested this; nothing you said asks for it, so it is yours to say'
MODEL_PICK_CARD = "The model suggests this. Nothing you said asks for it, so it's yours to say."
APPROVED_PICK = 'picked by the model, approved by you'
ORIGINS = ('OWNER_WORDS', 'RECORD', 'SOURCE', 'DEDUCTION')
NEVER_AN_ORIGIN = 'MODEL'
ORIGIN_NEEDS = {'OWNER_WORDS': ('start', 'end'), 'RECORD': ('id', 'rev'), 'SOURCE': ('id', 'rev', 'line', 'flagged'), 'DEDUCTION': ('proof',)}
ORIGIN_MAY = {'OWNER_WORDS': ('text',), 'RECORD': ('cell',), 'SOURCE': ('text',), 'DEDUCTION': ()}


class NoOrigin(ValueError):
    """A change proposed with an argument that does not say where it came from, or says the model."""


def basis_of(origin):
    """The basis of a turn from the origin of its goals (her hand's 0.8.6 words: OWNER, HER, DEDUCED, WORK_ORDER): the goals
    the model picked (HER, after a GOAL turn) are 'model_pick'; the late default is a deduction; the owner's own are his."""
    return {'OWNER': OWNER_WORDS, 'HER': MODEL_PICK, 'DEDUCED': DEDUCTION, 'WORK_ORDER': OWNER_WORDS}.get(str(origin or ''), MODEL_PICK)


def origin(kind, **where):
    """One argument's origin, checked: {'kind': kind, ...where}. OWNER_WORDS {start, end[, text]} (a span of his request,
    whole-number offsets); RECORD {id, rev[, cell]}; SOURCE {id, rev, line, flagged[, text]}; DEDUCTION {proof}. MODEL, or
    any other kind, raises NoOrigin."""
    if kind == NEVER_AN_ORIGIN:raise NoOrigin('ORIGIN_MODEL: no argument of a change comes from the model’s words')
    if kind not in ORIGINS:raise NoOrigin('ORIGIN_UNKNOWN: %s is not where an argument can come from' % str(kind)[:40])
    missing = [k for k in ORIGIN_NEEDS[kind] if k not in where]
    extra = [k for k in where if k not in ORIGIN_NEEDS[kind] + ORIGIN_MAY[kind]]
    if missing or extra:raise NoOrigin('ORIGIN_SHAPE: %s takes %s' % (kind, ', '.join(ORIGIN_NEEDS[kind] + ORIGIN_MAY[kind])))
    if kind == 'OWNER_WORDS':
        if not all(type(where[k]) is int and where[k] >= 0 for k in ('start', 'end')) or where['start'] >= where['end']:
            raise NoOrigin('ORIGIN_SPAN: a span of your words is two whole-number offsets, the start before the end')
    if kind == 'SOURCE':
        if type(where['line']) is not int or where['line'] < 1 or type(where['flagged']) is not bool:
            raise NoOrigin('ORIGIN_LINE: a source line is a whole number from 1, and whether it was flagged is yes or no')
    if kind == 'DEDUCTION' and not (isinstance(where['proof'], str) and where['proof'].strip()):
        raise NoOrigin('ORIGIN_PROOF: a deduction says its proof')
    for k in ('id', 'rev'):
        if k in where and not (isinstance(where[k], (str, int)) and not isinstance(where[k], bool) and str(where[k]).strip()):
            raise NoOrigin('ORIGIN_RECORD: a record or a source is named by its id and its revision')
    return {'kind': kind, **where}


def argued(value, how):
    """One argument with its origin: {'value': value, 'origin': origin(...)} (how: an origin dict, re-checked)."""
    if not isinstance(how, dict):raise NoOrigin('ORIGIN_MISSING: the argument does not say where it came from')
    return {'value': value, 'origin': origin(how.get('kind'), **{k: v for k, v in how.items() if k != 'kind'})}


def proposal(operation, arguments, basis, words=''):
    """A change put to the owner, checked: {'operation', 'arguments': {name: {value, origin}}, 'basis', 'words', 'hers_at'}.
    Every argument must carry an origin from ORIGINS (NoOrigin otherwise, MODEL first); the basis must be one of BASES.
    `hers_at` is the places of the dial where it is hers now, by the operation's Kernel scope (none for a model_pick)."""
    name = str(operation or '')
    if not name:raise NoOrigin('PROPOSAL_OPERATION: a change names its operation')
    if basis not in BASES:raise NoOrigin('PROPOSAL_BASIS: %s is not a basis' % str(basis)[:40])
    if not isinstance(arguments, dict):raise NoOrigin('PROPOSAL_ARGUMENTS: arguments are named')
    checked = {}
    for key, given in arguments.items():
        if not isinstance(given, dict) or set(given) != {'value', 'origin'}:raise NoOrigin('ORIGIN_MISSING: %s does not say where it came from' % str(key)[:60])
        checked[str(key)] = argued(given['value'], given['origin'])
    scope = _scope(name)
    return {'operation': name, 'arguments': checked, 'basis': basis, 'words': str(words)[:300],
            'hers_at': [p for p, _ in LEVELS if hers(p, scope, name, values(checked), basis)]}


def values(arguments):
    """The plain arguments of a proposal's {value, origin} arguments, as the Kernel takes them."""
    return {k: (v['value'] if isinstance(v, dict) and 'value' in v else v) for k, v in (arguments or {}).items()}


def origins_of(found):
    """Every argument's origin kind of a proposal (a dict as proposal() returns it); None where one has none."""
    return {k: ((v.get('origin') or {}).get('kind') if isinstance(v, dict) else None) for k, v in ((found or {}).get('arguments') or {}).items()}


def _scope(operation):
    try:
        from .engineering_kernel import CAPABILITIES
        return CAPABILITIES.get(operation, 'approve')
    except Exception:  # noqa: BLE001 - an operation the registry cannot say is not a read
        return 'approve'


def card(found):
    """A model's pick of a change, as the owner's card: {'lead': MODEL_PICK_CARD, 'what', 'lines': [the source lines its
    destinations were taken from], 'basis', 'buttons'}. The lead is said only for a model_pick; otherwise the dial's words."""
    lines = []
    for key, given in (found.get('arguments') or {}).items():
        where = given.get('origin') or {}
        if where.get('kind') == 'SOURCE':
            lines.append('%s, from line %d of %s%s%s' % (key, where['line'], where['id'], (': “%s”' % where['text']) if where.get('text') else '',
                                                        ' (a line the doorway flagged)' if where['flagged'] else ''))
    lead = MODEL_PICK_CARD if found.get('basis') == MODEL_PICK else ''
    return {'lead': lead, 'what': found.get('words') or found.get('operation'), 'lines': lines, 'basis': found.get('basis'),
            'buttons': ('Do it', 'Leave it')}


# The owner's change words for a page: a request of his that holds one (outside quotes) asks for a change to the page he has
# open, so a page edit the model wrote for it has his words as its basis; a request with none (a question, a summary) does
# not, and the model's edit is a card (design 5.2, App plans pass through the basis rule).
# Verbs only: a word that is also a question's noun (title, heading, style, format, type) or an adjective (bold, clear,
# plain) is left out, so "what is the title?" asks for no change.
CHANGE_WORDS = frozenset((
    'make', 'change', 'set', 'turn', 'put', 'give', 'add', 'append', 'insert', 'write', 'replace', 'swap', 'rewrite', 'reword',
    'rephrase', 'fix', 'correct', 'edit', 'embolden', 'italicise', 'italicize', 'underline', 'highlight', 'emphasise', 'emphasize',
    'restyle', 'reformat', 'remove', 'strip', 'draw', 'move', 'capitalise', 'capitalize', 'shorten', 'lengthen', 'unbold', 'convert'))


def outside_quotes(text):
    """The request without what stands in quotes (straight or curly) or after a colon that starts a pasted block."""
    text = re.sub(r'“[^”]*”|"[^"]*"|‘[^’]*’', ' ', str(text or ''))
    return text.split('\n\n', 1)[0]


def asks_for_change(request):
    """Whether the owner's request holds a change word of his, outside quotes."""
    words = re.findall(r"[a-z]+", outside_quotes(request).casefold())
    return any(w in CHANGE_WORDS for w in words)


def page_edit_basis(request):
    """The basis of a page edit the model wrote for the owner's request: 'owner_words' when his request asks for a change
    (asks_for_change), else 'model_pick' (the edit then waits on its card, at every place of the dial)."""
    return OWNER_WORDS if asks_for_change(request) else MODEL_PICK


def model_pick_sweep(operations, places=('ask', 'show', 'free')):
    """The basis rule over a registry ({operation: scope}): the (place, operation) pairs where a change on the model's pick
    alone would be hers. It must be empty; the reads, hers at every place on any basis, are counted beside it."""
    hers_on_pick = [(p, op) for op, scope in sorted(operations.items()) for p in places if scope != 'read' and hers(p, scope, op, None, MODEL_PICK)]
    reads = sum(1 for op, scope in operations.items() for p in places if scope == 'read' and hers(p, scope, op, None, MODEL_PICK))
    return {'hers_on_pick': hers_on_pick, 'reads_hers': reads}
# == end 0.8.7 B1 ===============================================================================================================


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


def record(state, words, line, undo='', word='', ok=True, now=None, guards=None, basis=None):
    """Add one act of hers to the trail kept in the session's state. Returns the entry. An Undo line is kept only if it is
    one an Undo may run (undo_allowed). 0.8.7 B1: an act the model picked and the owner approved (basis 'model_pick',
    run only after his press) says so in its words: "picked by the model, approved by you"."""
    guards = clean_guard(guards)
    if basis == MODEL_PICK and APPROVED_PICK not in str(words):words = '%s · %s' % (str(words)[:200 - len(APPROVED_PICK) - 3], APPROVED_PICK)
    entry = {'at': time.strftime('%Y-%m-%d %H:%M', time.localtime(now)), 'words': str(words)[:200], 'line': str(line)[:1200],
             'undo': str(undo)[:1200] if undo_allowed(undo, guards) else '', 'word': str(word)[:200], 'state': 'done' if ok else 'refused', 'guard': guards}
    trail = [e for e in (state.get(TRAIL) or []) if isinstance(e, dict)]
    trail.append(entry);state[TRAIL] = trail[-KEPT:]
    return entry


def trail(state):
    """Her acts, the latest first."""
    return [e for e in reversed(state.get(TRAIL) or []) if isinstance(e, dict)]


def record_desk(state, act, args, words, outcome, turn='', now=None):
    """One move of her hand on the desk, in the desk trail (never the data trail): the act, its arguments (words put in the
    writing line are kept by their length only, as the journal keeps them), what was said, and how it ended. No Undo: a
    move is put back by a plan to the window as it was. Returns the entry."""
    args = dict(args or {})
    if 'text' in args:args = {**{k: v for k, v in args.items() if k != 'text'}, 'characters': len(str(args['text']))}
    entry = {'at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now)), 'act': str(act)[:40], 'args': args, 'words': str(words)[:200],
             'state': str(outcome)[:12], 'turn': str(turn)[:40]}
    rows = [e for e in (state.get(DESK_TRAIL) or []) if isinstance(e, dict)]
    rows.append(entry);state[DESK_TRAIL] = rows[-DESK_KEPT:]
    return entry


def desk_trail(state):
    """Her moves on the desk, the latest first."""
    return [e for e in reversed(state.get(DESK_TRAIL) or []) if isinstance(e, dict)]


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
