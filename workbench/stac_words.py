"""The owner's own staC words (no Qt).

A staC line that earned its keep should not have to be typed twice. The owner keeps it under a word of their own, and from
then on the word is the line, wherever a line is typed:

    word waits = field.read | pick waiting | select kind,title,state      keep it
    waits                                                                  run it
    waits | where kind=finding | count                                     go on from it, as from any read
    explain waits                                                          see its plan
    words                                                                  list them
    forget waits                                                           let it go

A word is written out before it runs, so what ran is always the whole line and never a name: the answer, the history and
anything kept from it say the line. A word can only be a staC read (the language's own parser decides; staC refuses
anything that changes something), so a word can never do what a line could not. Words belong to the workspace and are kept
in its records; they do not depend on any model.

    words.list    read      {}              the words of this workspace
    words.keep    execute   {name, line}    keep a line under a word (a second keep under the same word replaces it)
    words.forget  execute   {name}          let a word go

    expand(known, text)   a typed line with its leading word written out; anything else comes back unchanged
    command(text)         `word NAME = LINE`, `forget NAME` and `words` as the operation lines they stand for, or None
"""
import json
import re
import time

NAME = {'type': 'string', 'pattern': '^[a-z][a-z0-9-]{1,23}$'}
LINE = {'type': 'string', 'minLength': 3, 'maxLength': 1200}
FIELDS = {'words.list': ({}, []), 'words.keep': ({'name': NAME, 'line': LINE}, ['name', 'line']), 'words.forget': ({'name': NAME}, ['name'])}
SCOPES = {'words.list': 'read', 'words.keep': 'execute', 'words.forget': 'execute'}
OBSERVERS = ('words.list',)
LIMIT = 200
RESERVED = ('this', 'explain', 'word', 'words', 'forget', 'jobs', 'models', 'activity', 'field', 'help')      # what a line may already start with and mean
LEAD = re.compile(r'^(explain\s+)?([a-z][a-z0-9-]{1,23})(?![\w.-])\s*(\|.*)?$', re.DOTALL)
KEEP = re.compile(r'^word\s+(\S{1,40})\s*=\s*(\S.*)$', re.DOTALL)        # the name is judged by words.keep, which says what a word may be
SHOW = re.compile(r'^word\s+([A-Za-z][A-Za-z0-9-]{1,23})\s*$')
FORGET = re.compile(r'^forget\s+(\S{1,40})\s*$')


def _ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS stac_words(name TEXT PRIMARY KEY, owner TEXT, line TEXT, made REAL, updated REAL)')


def _taken(name):
    """A word that would hide something a line can already start with: an operation's first name, a start word of the older
    query language, or one of the line's own words."""
    if name in RESERVED:return True
    try:
        from .engineering_kernel import CAPABILITIES
        from .stac_bridge import START_WORDS
    except ImportError:
        return False
    return name in START_WORDS or name in CAPABILITIES or any(operation.split('.', 1)[0] == name for operation in CAPABILITIES)


def listing(kernel, principal):
    with kernel.db() as db:
        _ensure(db)
        rows = db.execute('SELECT name, line, made, updated FROM stac_words ORDER BY name').fetchall()
    return {'words': [{'name': name, 'line': line, 'kept': time.strftime('%Y-%m-%d %H:%M', time.localtime(updated or made or 0))} for name, line, made, updated in rows]}


def _named(name):
    """The Kernel checks that a name is text; what a word may be is checked here, for every way of asking."""
    if not isinstance(name, str) or not re.fullmatch(NAME['pattern'], name):
        raise ValueError('A word is 2 to 24 small letters, digits or hyphens, and starts with a letter')
    return name


def keep(kernel, principal, name, line):
    name = _named(name);line = ' '.join(str(line).replace('\u200b', '').split())
    if not 3 <= len(line) <= LINE['maxLength']:
        raise ValueError('A word keeps one staC line, at most %d characters' % LINE['maxLength'])
    if _taken(name):
        raise ValueError('“%s” already means something at the start of a line; choose another word' % name)
    if LEAD.match(line) and LEAD.match(line).group(2) == name:
        raise ValueError('A word cannot be made of itself')
    known = {row['name']: row['line'] for row in listing(kernel, principal)['words']}
    written = expand(known, line)             # a word may be built on another word: it is kept written out, so forgetting one never breaks another
    if not written.lower().startswith(('this', 'explain this')):
        answer = kernel.dispatch('language.parse', {'text': written[len('explain '):] if written.lower().startswith('explain ') else written}, principal)
        if not answer.get('ok'):
            raise ValueError('That is not a staC line I can keep: %s' % str((answer.get('error') or {}).get('message'))[:200])
    with kernel.db() as db:
        _ensure(db)
        if name not in known and len(known) >= LIMIT:
            raise ValueError('There are %d words already; forget one first' % LIMIT)
        now = time.time()
        db.execute('INSERT INTO stac_words(name, owner, line, made, updated) VALUES(?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET line=excluded.line, updated=excluded.updated',
                   (name, getattr(principal, 'identity', ''), written, now, now))
    return {'name': name, 'line': written, 'replaced': name in known, 'words': 'Kept. “%s” now runs: %s' % (name, written)}


def forget(kernel, principal, name):
    name = _named(name)
    with kernel.db() as db:
        _ensure(db)
        gone = db.execute('DELETE FROM stac_words WHERE name=?', (name,)).rowcount
    if not gone:
        raise ValueError('There is no word “%s”. `words` lists them.' % name)
    return {'name': name, 'words': 'Forgotten: “%s”.' % name}


def dispatch(kernel, operation, args, principal):
    if operation == 'words.list':return listing(kernel, principal)
    if operation == 'words.keep':return keep(kernel, principal, args['name'], args['line'])
    if operation == 'words.forget':return forget(kernel, principal, args['name'])
    raise ValueError('Unknown words operation')


# ---- at the writing line ---------------------------------------------------------------------------------------------------
def expand(known, text):
    """A line whose first word is one of the owner's, written out: alone it is the kept line; before a `|` the kept line goes on
    with what follows; after `explain` the kept line is explained. `known` is {name: line}. Anything else is unchanged."""
    found = LEAD.match(str(text).replace('\u200b', '').strip())
    if not found or found.group(2) not in known:return text
    lead = found.group(1) or '';rest = found.group(3)
    return lead + known[found.group(2)] + ('' if rest is None else ' ' + rest.strip())


def command(text):
    """The three things the line says about words themselves, as the lines they stand for: `word NAME = LINE` keeps,
    `forget NAME` lets go (both are operation lines, typed by the owner), `words` lists (a read). None for anything else."""
    text = str(text).replace('\u200b', '').strip()
    kept = KEEP.match(text)
    if kept:
        return '/words.keep ' + json.dumps({'name': kept.group(1).lower(), 'line': ' '.join(kept.group(2).split())}, ensure_ascii=False, separators=(', ', ': '))
    gone = FORGET.match(text)
    if gone:
        return '/words.forget ' + json.dumps({'name': gone.group(1).lower()}, ensure_ascii=False, separators=(', ', ': '))
    shown = SHOW.match(text)
    if shown:                                  # `word waits`: what that word stands for
        return 'words.list | pick words | where name=%s | select name,line' % shown.group(1).lower()
    if text.lower() == 'words':
        return 'words.list | pick words | select name,line'
    return None


def known_to(host, fresh=False):
    """The words of this window's workspace, read through the Kernel and remembered for a few seconds: the writing line asks
    on every keystroke. {name: line}; empty when the records cannot be reached."""
    kept = getattr(host, '_stac_words', None)
    if kept is not None and not fresh and time.monotonic() - kept[0] < 3.0:return kept[1]
    words = {}
    try:
        from .engine import engineering
        from .engineering_kernel import operator
        answer = engineering(host.root).dispatch('words.list', {}, operator())
        if answer.get('ok'):words = {row['name']: row['line'] for row in answer['result']['words']}
    except Exception:  # noqa: BLE001 - a line is never stopped because the words could not be read; it runs as written
        words = {}
    try:host._stac_words = (time.monotonic(), words)
    except Exception:  # noqa: BLE001
        pass
    return words


def written_out(host, text):
    """What the writing line does with a typed line before anything else: a line about words becomes the line it stands for,
    and a line that starts with one of the owner's words is written out. After a line that keeps or forgets a word, the
    words are read fresh the next time."""
    made = command(text)
    if made is not None:
        if made.startswith('/'):
            try:host._stac_words = None
            except Exception:  # noqa: BLE001
                pass
        return made
    return expand(known_to(host), text)
