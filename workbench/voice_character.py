"""Her character file (0.8.7 C5, "Kas's mind with the model, interwoven", lane C).

A plain-text file in your workspace, <workspace>/kasandra/character.md, that you edit in any App. It starts from the starter
shipped with Graphite (workbench/kasandra/character_starter.md, marked "a starter, not yet yours"); your own draft goes
under its "Your own words" heading, kept word for word and never read into her character. It holds:

  Registers      which register each kind of work is spoken in: plain (engineering), formal (contracts), warm (money, home)
  Manner         a short line per register: how she sounds in it
  Joining words  the words the model may put between the desk's clauses, per register (words only: no digit, no sign)
  Never say      phrases and marks she never writes ("As an AI", "!", "safe" about anything not proven)
  Lengths        the most words in a sentence and the most sentences in an answer, per register

The compile is exact: headings (##) and dash bullets only, no model; the same bytes always give the same character and
the same card. Any other line is your notes. What it cannot read is said in plain words, with the line it is on.

It governs every sentence she says, with or without a model: 0.8.6's style rules (mind_words) read the character in
force, so a never-say phrase in any registered template fails the sweep (mind_words.check) and in any finished card
(mind_words.scan_text); the voice gate (voice_gate, C4) takes its never-say list and its lengths from here (never_say(),
budgets()); FRAME's system message carries card(), at most CARD_MOST tokens: held to it by the bundled tokenizer's exact
count when the caller passes one (count=), else by grammars.estimate, an upper estimate (the starter's card: 155 by the
estimate, 120 by the 4B's tokenizer, so the estimate leaves little room for additions). The file adds to her floor and never lifts
it: the exclamation mark and the 0.8.6 banned words stay banned, and a sentence is never allowed more than mind_words'
MAX_WORDS.

Admitted with revisions. A version of the file is in force only once you admit it (voice.character.admit, approve):
admitting keeps its exact bytes as a numbered revision under <workspace>/kasandra/.revisions/ and an index there. An
edit you have not admitted changes nothing; a file that does not compile cannot be admitted, and the revision in force
stays. Taking an earlier revision back is a new revision that points at the same bytes; your file itself is never
written by Graphite, except once, when it does not exist yet and you start it from the starter (voice.character.start).
Before anything is admitted, the starter is in force.

  voice.character        {}                                  read      the character in force, the file now, plain words
  voice.character.start  {}                                  execute   write the starter where no file is; revision 1
  voice.character.admit  {expected_sha256} or {revision}     approve   admit the file as it is now (the bytes you read),
                                                                       or take an earlier revision back

The kit ships only character_starter.md. Your character.md and its revisions are private: the release check's privacy
scan fails a payload or an archive member named character.md or held in kasandra/.revisions (PRIVATE_NAME, private_in).

Pure Python: no Qt, no model, no network, no float.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from . import mind_words

SCHEMA = 'voice.character/1'
INDEX_SCHEMA = 'ledger.character/1'
FOLDER = 'kasandra'
NAME = 'character.md'
REVISIONS = '.revisions'
STARTER = Path(__file__).resolve().parent / 'kasandra' / 'character_starter.md'
STARTER_MARK = 'a starter, not yet yours'
REGISTERS = ('plain', 'formal', 'warm')
SECTIONS = ('Registers', 'Manner', 'Joining words', 'Never say', 'Lengths')
REQUIRED = ('Registers', 'Never say', 'Lengths')
CARD_MOST = 160                          # tokens, by the bundled tokenizer (FRAME's system message, 0.8.7 section 3.2)
MOST_BYTES = 65536
MANNER_MOST = 120                        # letters in one Manner line
# The three women are a manner only: her character file describes the manner and never names them (0.8.7 section 7.2).
NOT_NAMED = ('curie', 'elizabeth ii', 'queen elizabeth', 'roosevelt')
# The private files: your character file and its kept revisions, wherever they sit in a payload or an archive.
PRIVATE_NAME = re.compile(r'(?:^|[/!\\])(?:character\.md|\.revisions[/\\][0-9a-f]{64}\.md)$', re.IGNORECASE)

ORIGINS = ('STARTER', 'YOUR_FILE', 'TAKEN_BACK')
_HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
_BULLET = re.compile(r'^\s{0,3}[-*]\s+(.*\S)\s*$')
_KEYED = re.compile(r'^([A-Za-z]+)\s*:\s*(.*\S)\s*$')
_QUOTED = re.compile(r'^(?:"([^"]*)"|“([^”]*)”)\s*(.*)$')
_LENGTH = re.compile(r'^at most (\d{1,3}) (words?|sentences?)\.?$', re.IGNORECASE)
_WORDS_ONLY = re.compile(r"^[A-Za-z][A-Za-z' -]*$")
_DIGIT = re.compile(r'\d')

# -- her plain words (registered with mind_words, so the sweep reads them too) -----------------------------------------------
WORDS = {
    'not_text': 'The character file is not plain text. Save it as plain text and admit it again.',
    'too_long': 'The character file is longer than {most} letters. Keep it shorter and admit it again.',
    'no_section': 'The file has no “{heading}” heading. Her character needs one.',
    'twice': 'The heading “{heading}” is there twice, on line {first} and line {line}. Keep one of them.',
    'not_understood': 'Line {line}: “{text}” is not understood. Write it as {example}.',
    'unknown_register': 'Line {line}: “{name}” is not one of her registers. Hers are plain, formal and warm.',
    'register_twice': 'Line {line}: the {name} register is given a line twice under “{heading}”. Keep one.',
    'register_missing': 'Under “{heading}”, the {name} register has no line.',
    'domain_twice': 'Line {line}: “{word}” is already given to the {name} register.',
    'words_only': 'Line {line}: joining words are words only, with no digit and no sign.',
    'empty_quote': 'Line {line}: the quotation marks hold nothing to never say.',
    'over_floor': 'Line {line}: a sentence may have at most {most} words. That is her floor, and this file can only make it shorter.',
    'at_least_one': 'Line {line}: a length is at least one.',
    'manner_long': 'Line {line}: a manner is one short line of at most {most} letters.',
    'named': 'Line {line}: her manner is described, never named. Write the manner, not the person.',
    'no_never': 'Under “Never say”, write at least one thing she never says.',
    'card_long': 'Her card would be about {tokens} tokens, and it may have at most {most}. Shorten Manner, Joining words or Never say.',
    'starter': 'Her character file is a starter, not yet yours. Edit it in any App, then admit it.',
    'in_force': 'Revision {revision} of your character file is in force.',
    'not_started': 'You have no character file yet. She speaks by the starter until you start one.',
    'changed': 'Your character file has changed since revision {revision}. Admit it to use it.',
    'broken_now': 'Your character file as it is now cannot be admitted. Revision {revision} stays in force.',
    'damaged': 'The kept copy of revision {revision} is damaged. She speaks by the starter until you admit the file again.',
    'gone': 'Your character file is not in your workspace now. Revision {revision} stays in force.',
    'kept': 'Revision {revision} is kept and in force.',
    'same': 'That is already the revision in force. Nothing changed.',
    'started': 'Your character file is started from the starter, as revision {revision}.',
    'already': 'Your character file is already there. Nothing was written.',
}
EXAMPLES = {
    'Registers': '“- plain: engineering, maths”',
    'Manner': '“- plain: exact; the answer first”',
    'Joining words': '“- plain: so, because, but”',
    'Never say': '“- "As an AI"”',
    'Lengths': '“- plain: at most 3 sentences” or “- sentence: at most 30 words”',
}
mind_words.register('voice_character', WORDS)


def _say(key, **slots):
    return WORDS[key].format(**slots)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


# -- the compile -------------------------------------------------------------------------------------------------------------
def _section_name(title):
    plain = ' '.join(title.split()).rstrip(':').lower()
    for name in SECTIONS:
        if plain == name.lower():return name
    return None


def _domain_key(word):
    """A kind of work as matched: lower case, '_' as a space, a plural s dropped from each word."""
    words = str(word).replace('_', ' ').replace('-', ' ').lower().split()
    return ' '.join(w[:-1] if len(w) > 3 and w.endswith('s') and not w.endswith('ss') else w for w in words)


def compile_text(text, count=None):
    """(character, errors): her character compiled from the file's text, exactly, or None with every error in plain words.
    `text` is the file's bytes or its text. `count`, when given, is the bundled tokenizer (text -> number of tokens, as a
    turn port's /tokenize gives it): the card is held to CARD_MOST by its exact count. Without it, the card is held to
    CARD_MOST by grammars.estimate, an upper estimate, so a card admitted either way is at most CARD_MOST tokens."""
    if isinstance(text, (bytes, bytearray)):
        if len(text) > MOST_BYTES:return None, [_say('too_long', most=MOST_BYTES)]
        try:text = bytes(text).decode('utf-8')
        except UnicodeDecodeError:return None, [_say('not_text')]
    if len(text.encode('utf-8')) > MOST_BYTES:return None, [_say('too_long', most=MOST_BYTES)]
    if '\x00' in text:return None, [_say('not_text')]
    if text.startswith('﻿'):text = text[1:]
    errors = []
    seen = {}                                                  # section -> first line
    lines = {name: [] for name in SECTIONS}                    # section -> [(line number, bullet text)]
    notes = []
    section = None
    starter = False
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if ' '.join(line.split()).lower().rstrip('.') == STARTER_MARK:starter = True   # the mark is a line of its own
        heading = _HEADING.match(line)
        if heading:
            name = _section_name(heading.group(2)) if len(heading.group(1)) == 2 else None
            if name and name in seen:
                errors.append(_say('twice', heading=name, first=seen[name], line=number));section = None;continue
            if name:seen[name] = number
            elif len(heading.group(1)) == 2:notes.append(' '.join(heading.group(2).split()))
            section = name
            continue
        bullet = _BULLET.match(line)
        if bullet and section:lines[section].append((number, ' '.join(bullet.group(1).split())))
    for name in REQUIRED:
        if name not in seen:errors.append(_say('no_section', heading=name))
    registers, owner = {}, {}
    for number, item in lines['Registers']:
        keyed = _KEYED.match(item)
        if not keyed:errors.append(_say('not_understood', line=number, text=item[:80], example=EXAMPLES['Registers']));continue
        name, rest = keyed.group(1).lower(), keyed.group(2)
        if name not in REGISTERS:errors.append(_say('unknown_register', line=number, name=keyed.group(1)[:40]));continue
        if name in registers:errors.append(_say('register_twice', line=number, name=name, heading='Registers'));continue
        domains = []
        for word in (w.strip() for w in rest.rstrip('.').split(',')):
            if not word:continue
            if not _WORDS_ONLY.match(word):
                errors.append(_say('not_understood', line=number, text=item[:80], example=EXAMPLES['Registers']));domains = None;break
            key = _domain_key(word)
            if key in owner and owner[key] != name:errors.append(_say('domain_twice', line=number, word=word, name=owner[key]));continue
            owner[key] = name
            if word not in domains:domains.append(word)
        if domains is not None:registers[name] = domains
    manner = {}
    for number, item in lines['Manner']:
        keyed = _KEYED.match(item)
        if not keyed:errors.append(_say('not_understood', line=number, text=item[:80], example=EXAMPLES['Manner']));continue
        name, rest = keyed.group(1).lower(), keyed.group(2).rstrip('.')
        if name not in REGISTERS:errors.append(_say('unknown_register', line=number, name=keyed.group(1)[:40]));continue
        if name in manner:errors.append(_say('register_twice', line=number, name=name, heading='Manner'));continue
        if len(rest) > MANNER_MOST:errors.append(_say('manner_long', line=number, most=MANNER_MOST));continue
        if any(n in rest.lower() for n in NOT_NAMED):errors.append(_say('named', line=number));continue
        manner[name] = rest
    joining = {}
    for number, item in lines['Joining words']:
        keyed = _KEYED.match(item)
        if not keyed:errors.append(_say('not_understood', line=number, text=item[:80], example=EXAMPLES['Joining words']));continue
        name, rest = keyed.group(1).lower(), keyed.group(2).rstrip('.')
        if name not in REGISTERS:errors.append(_say('unknown_register', line=number, name=keyed.group(1)[:40]));continue
        if name in joining:errors.append(_say('register_twice', line=number, name=name, heading='Joining words'));continue
        words = [' '.join(w.split()) for w in rest.split(',') if w.strip()]
        if not words or not all(_WORDS_ONLY.match(w) for w in words):errors.append(_say('words_only', line=number));continue
        joining[name] = list(dict.fromkeys(words))
    never = []
    for number, item in lines['Never say']:
        quoted = _QUOTED.match(item)
        if not quoted:errors.append(_say('not_understood', line=number, text=item[:80], example=EXAMPLES['Never say']));continue
        phrase = ' '.join((quoted.group(1) if quoted.group(1) is not None else quoted.group(2)).split())
        if not phrase:errors.append(_say('empty_quote', line=number));continue
        if any(n['phrase'].lower() == phrase.lower() for n in never):continue
        never.append({'phrase': phrase, 'mark': not any(c.isalpha() for c in phrase), 'note': quoted.group(3).strip()})
    if 'Never say' in seen and not lines['Never say']:errors.append(_say('no_never'))
    sentence_words, sentences = mind_words.MAX_WORDS, {}
    for number, item in lines['Lengths']:
        keyed = _KEYED.match(item)
        length = _LENGTH.match(keyed.group(2)) if keyed else None
        name = keyed.group(1).lower() if keyed else ''
        unit = length.group(2).lower().rstrip('s') if length else ''
        if not length or name not in ('sentence',) + REGISTERS or (name == 'sentence') != (unit == 'word'):
            if keyed and length and name not in ('sentence',) + REGISTERS:
                errors.append(_say('unknown_register', line=number, name=keyed.group(1)[:40]))
            else:errors.append(_say('not_understood', line=number, text=item[:80], example=EXAMPLES['Lengths']))
            continue
        most = int(length.group(1))
        if most < 1:errors.append(_say('at_least_one', line=number));continue
        if name == 'sentence':
            if most > mind_words.MAX_WORDS:errors.append(_say('over_floor', line=number, most=mind_words.MAX_WORDS));continue
            sentence_words = most
        elif name in sentences:errors.append(_say('register_twice', line=number, name=name, heading='Lengths'))
        else:sentences[name] = most
    for heading, given in (('Registers', registers), ('Lengths', sentences)):
        if heading not in seen:continue
        refused = {n for n in REGISTERS for number, item in lines[heading] if item.lower().startswith(n)}
        errors.extend(_say('register_missing', heading=heading, name=n) for n in REGISTERS if n not in given and n not in refused)
    if errors:return None, errors
    character = {'schema': SCHEMA, 'registers': registers, 'manner': manner, 'joining': joining, 'never_say': never,
                 'lengths': {'sentence_words': sentence_words, 'sentences': sentences}, 'starter': starter, 'notes': notes}
    character['card'] = card(character)
    character['card_tokens_estimate'] = _estimate(character['card'])
    if count is not None:
        exact = int(count(character['card']))
        character['card_tokens'], character['card_counted_by'] = exact, 'the bundled tokenizer'
    else:
        character['card_tokens'], character['card_counted_by'] = character['card_tokens_estimate'], 'an upper estimate'
    if character['card_tokens'] > CARD_MOST:
        return None, [_say('card_long', tokens=character['card_tokens'], most=CARD_MOST)]
    content = {k: v for k, v in character.items() if k not in ('card_tokens', 'card_tokens_estimate', 'card_counted_by')}
    character['digest'] = sha256(json.dumps(content, sort_keys=True, separators=(',', ':')).encode('utf-8'))   # what she is, not how it was counted
    return character, []


def _estimate(text):
    """An upper estimate of the card's tokens (grammars.estimate, checked against the 4B's vocabulary); the bundled
    tokenizer's exact count is never above it."""
    from . import grammars
    return grammars.estimate(text)


def card(character):
    """Her card, the short text FRAME's system message carries: per register, its manner, its joining words and its length;
    then what holds in every register. Which kinds of work go to which register is the desk's choice (register_for), so it
    is not on the card. The same character always gives the same bytes."""
    parts = []
    for name in REGISTERS:
        said = [character['manner'][name]] if name in character['manner'] else []
        if name in character['joining']:said.append('joins with ' + ', '.join(character['joining'][name]))
        if said:parts.append('%s: %s.' % (name.capitalize(), '; '.join(said)))
    lengths = character['lengths']
    parts.append('Most sentences: %s; most words a sentence: %d.' % (
        ', '.join('%s %d' % (name, lengths['sentences'][name]) for name in REGISTERS), lengths['sentence_words']))
    parts.append('Never: %s.' % ', '.join(('"%s" %s' % (x['phrase'], x['note'])).strip() for x in character['never_say']))
    return ' '.join(parts)


# -- the character in force for this process (0.8.6's style rules read it) ---------------------------------------------------
_STARTER = None
_CURRENT = None
_CACHE = {}                   # sha256 -> compiled character


def starter():
    """The starter's compiled character (it always compiles; the build's smoke checks it)."""
    global _STARTER
    if _STARTER is None:
        character, errors = compile_text(STARTER.read_bytes())
        if errors:raise ValueError('CHARACTER_STARTER_BROKEN: ' + errors[0])
        _STARTER = character
    return _STARTER


def current():
    """The character in force in this process: the one use() last set, else the starter. None only when the starter cannot
    be read, so the style rules fall back to their own floor."""
    if _CURRENT is not None:return _CURRENT
    try:return starter()
    except (OSError, ValueError):return None


def never_say(character=None):
    """Her never-say list: [{'phrase', 'mark', 'note'}], a mark being a phrase with no letter (such as "!")."""
    character = character or current()
    return [dict(x) for x in character['never_say']] if character else []


def register_for(kind):
    """The register a kind of work is spoken in: 'formal' for a CONTRACT or a lease, 'warm' for money, 'plain' otherwise.
    `kind` is a word or a rule sort (STATUTE_TEXT is a statute)."""
    character = current()
    key = _domain_key(kind)
    if character and key:
        first = key.split()[0]
        for name in REGISTERS:
            for word in character['registers'].get(name, ()):
                if _domain_key(word) in (key, first):return name
    return 'plain'


def budgets(register='plain'):
    """{'sentences', 'words'}: the most sentences an answer in this register has and the most words in a sentence."""
    character = current()
    if register not in REGISTERS:raise ValueError('CHARACTER_REGISTER: one of %s' % ', '.join(REGISTERS))
    if not character:return {'sentences': 3, 'words': mind_words.MAX_WORDS}
    return {'sentences': character['lengths']['sentences'][register],
            'words': min(mind_words.MAX_WORDS, character['lengths']['sentence_words'])}


def scan(text, register=None):
    """Everything in a finished answer that her character refuses: 0.8.6's banned words and style rules (fed by this file's
    never-say list and sentence length) and, with a register, more sentences than it allows."""
    problems = list(mind_words.scan_text(text))
    if register:
        most = budgets(register)['sentences']
        count = len(mind_words.sentences(mind_words.unquoted(text)))
        if count > most:problems.append('%d sentences, and the %s register allows %d' % (count, register, most))
    return problems


# -- the file in your workspace, admitted with revisions ---------------------------------------------------------------------
def _folder(root):
    folder = Path(root) / FOLDER
    if folder.is_symlink():raise ValueError('CHARACTER_LINK: the kasandra folder is a link; it is not followed')
    return folder


def _file(root):
    path = _folder(root) / NAME
    if path.is_symlink():raise ValueError('CHARACTER_LINK: character.md is a link; it is not followed')
    return path


def _index_path(root):
    return _folder(root) / REVISIONS / 'index.json'


def index(root):
    """The revisions kept: {'schema', 'revisions': [{'revision', 'sha256', 'origin', 'at', 'digest', 'from'?}]}."""
    try:value = json.loads(_index_path(root).read_text(encoding='utf-8'))
    except (OSError, ValueError):return {'schema': INDEX_SCHEMA, 'revisions': []}
    if not isinstance(value, dict) or value.get('schema') != INDEX_SCHEMA or not isinstance(value.get('revisions'), list):
        return {'schema': INDEX_SCHEMA, 'revisions': []}
    return value


def _write_atomic(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.%s.partial' % path.name)
    with open(temporary, 'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary, path)


def _kept(root, sha):
    return _folder(root) / REVISIONS / (sha + '.md')


def _compiled(raw, count=None):
    """The compile of these bytes. With the bundled tokenizer (count) the compile is not cached: it is the admission's own."""
    if count is not None:return compile_text(raw, count)
    sha = sha256(raw)
    if sha not in _CACHE:_CACHE[sha] = compile_text(raw)
    return _CACHE[sha]


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def in_force(root):
    """(character, revision row or None, words): what governs her words for this workspace now."""
    rows = index(root)['revisions']
    if not rows:return starter(), None, _say('not_started')
    row = rows[-1]
    try:raw = _kept(root, row['sha256']).read_bytes()
    except (OSError, KeyError):raw = b''
    if sha256(raw) != row.get('sha256'):character, errors = None, ['damaged']
    else:
        character, errors = _compiled(raw)
        if errors and row.get('card_counted_by') == 'the bundled tokenizer' and isinstance(row.get('card_tokens'), int):
            # admitted by its exact count: read back with the count recorded at admission (the bytes are the same)
            character, errors = _compiled(raw, lambda card, n=row['card_tokens']:n)
    if errors:return starter(), row, _say('damaged', revision=row.get('revision'))
    return character, row, _say('starter') if character['starter'] else _say('in_force', revision=row['revision'])


def use(root):
    """Put this workspace's character in force for this process (0.8.6's style rules and the voice gate read it)."""
    global _CURRENT
    _CURRENT = in_force(root)[0]
    return _CURRENT


def state(root):
    """The character in force and the file as it is now, in plain data with plain words."""
    character, row, words = in_force(root)
    path = _file(root)
    now = {'path': '%s/%s' % (FOLDER, NAME), 'exists': path.is_file()}
    said = [words]
    if now['exists']:
        raw = path.read_bytes();compiled, errors = _compiled(raw)
        now.update(sha256=sha256(raw), bytes=len(raw), errors=errors, compiles=not errors,
                   admitted=bool(row and row['sha256'] == sha256(raw)))
        if row and not now['admitted']:said.append(_say('broken_now', revision=row['revision']) if errors else
                                                   _say('changed', revision=row['revision']))
    elif row:said.append(_say('gone', revision=row['revision']))
    return {'schema': SCHEMA, 'revision': row, 'origin': 'STARTER' if row is None else row['origin'],
            'starter': character['starter'], 'card': character['card'], 'card_tokens': character['card_tokens'],
            'card_counted_by': character['card_counted_by'], 'card_most': CARD_MOST, 'registers': character['registers'], 'manner': character['manner'],
            'joining': character['joining'], 'never_say': never_say(character), 'lengths': character['lengths'],
            'digest': character['digest'], 'file': now, 'revisions': len(index(root)['revisions']), 'words': said}


def _admit_raw(root, raw, origin, taken_from=None, count=None):
    value = index(root)
    rows = value['revisions']
    sha = sha256(raw)
    if rows and rows[-1]['sha256'] == sha:return {'changed': False, 'revision': rows[-1], 'words': [_say('same')]}
    character, errors = _compiled(raw, count)
    if errors:raise ValueError('CHARACTER_DOES_NOT_COMPILE: ' + ' '.join(errors))
    kept = _kept(root, sha)
    if not kept.is_file() or sha256(kept.read_bytes()) != sha:_write_atomic(kept, raw)
    row = {'revision': len(rows) + 1, 'sha256': sha, 'origin': origin, 'at': _now(), 'digest': character['digest'],
           'card_tokens': character['card_tokens'], 'card_counted_by': character['card_counted_by']}
    if taken_from is not None:row['from'] = taken_from
    rows.append(row)
    _write_atomic(_index_path(root), json.dumps(value, indent=1, sort_keys=True).encode('utf-8'))
    use(root)
    return {'changed': True, 'revision': row, 'words': [_say('kept', revision=row['revision'])]}


def start(root):
    """Write the starter where you have no character file, and admit it as the first revision. Never overwrites."""
    path = _file(root)
    if path.exists():return {'changed': False, 'words': [_say('already')], 'state': state(root)}
    raw = STARTER.read_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'xb') as stream:stream.write(raw)
    done = _admit_raw(root, raw, 'STARTER')
    done['words'] = [_say('started', revision=done['revision']['revision'])]
    done['state'] = state(root)
    return done


def admit(root, expected_sha256=None, revision=None, count=None):
    """Admit your file as it is now (only when its bytes are the ones you read: expected_sha256), or take an earlier
    revision back (a new revision with the same bytes). A file that does not compile is refused and nothing changes."""
    if (expected_sha256 is None) == (revision is None):raise ValueError('CHARACTER_ADMIT: give expected_sha256 or revision')
    if revision is not None:
        rows = index(root)['revisions']
        if not 1 <= revision <= len(rows):raise ValueError('CHARACTER_NO_SUCH_REVISION: there is no revision %d' % revision)
        row = rows[revision - 1]
        raw = _kept(root, row['sha256']).read_bytes()
        if sha256(raw) != row['sha256']:raise ValueError('CHARACTER_KEPT_COPY_DAMAGED: ' + _say('damaged', revision=revision))
        done = _admit_raw(root, raw, 'TAKEN_BACK', taken_from=revision, count=count)
    else:
        path = _file(root)
        if not path.is_file():raise ValueError('CHARACTER_NO_FILE: there is no kasandra/character.md in this workspace')
        raw = path.read_bytes()
        if sha256(raw) != expected_sha256:
            raise ValueError('CHARACTER_FILE_CHANGED: the file changed after you read it; read it again before admitting')
        done = _admit_raw(root, raw, 'YOUR_FILE', count=count)
    done['state'] = state(root)
    return done


# -- the kit: only the starter ships ------------------------------------------------------------------------------------------
def private_in(names):
    """The names (shipped paths, or archive!member) that are your character file or its kept revisions."""
    return [name for name in names if PRIVATE_NAME.search(str(name))]


# -- the Kernel's operations (0.8.7 C5) ---------------------------------------------------------------------------------------
_SHA = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
FIELDS = {
    'voice.character': ({}, []),
    'voice.character.start': ({}, []),
    'voice.character.admit': ({'expected_sha256': _SHA, 'revision': {'type': 'integer', 'minimum': 1, 'maximum': 100000}}, []),
}
SCOPES = {'voice.character': 'read', 'voice.character.start': 'execute', 'voice.character.admit': 'approve'}


def dispatch(kernel, op, args, principal):
    root = kernel.root
    if op == 'voice.character':
        use(root);return state(root)
    if op == 'voice.character.start':return start(root)
    if op == 'voice.character.admit':return admit(root, args.get('expected_sha256'), args.get('revision'))
    raise ValueError('Unknown character operation')
