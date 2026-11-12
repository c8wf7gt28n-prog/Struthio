"""Files about something (HATCH AGENT-02, WI-C): the second assignment the resident loop works without a model.

The owner asks in plain words ("find files about pellets", "what documents do we have on the frame", "which drawings mention
the hatch door") and Slate looks through Files and Ingress, reads the first lines of the best matches and writes a findings
page. Explicit words choose the profile (fits(); never a model); the model, when one is loaded, only advises between reading
one more match and writing the page (owner decision 6). The steps, each one registered operation:

  where      receiving.status {}                  the Ingress folder's path and how many names wait there (kept in the context;
                                                  Ingress files are listed by name only, never opened)
  find       files.find {text, limit: 20}         files inside Files whose name or words carry the topic: a FINDING per match
                                                  (name · place · size · changed · how it matched). The text is the topic without
                                                  a leading article and with a plural's ending taken off ("the pellets" ->
                                                  "pellet"), because files.find is a plain substring search
  find_word  files.find {text: word, limit: 20}   only when a topic of several words matched nothing: once more with its longest
                                                  word ("hatch door" -> "hatch"); the findings say which word matched
  ingress    ledger.browse {path: Ingress}        only when Ingress holds something: names that carry every topic word are a
                                                  FINDING each, "waiting to be received, not read". Nothing in Files and nothing
                                                  here: a QUESTION and done, no page (the QUESTION waits for this listing)
  read_k     files.get {path}                     the first line of a best match (a name match first, then readable kinds, newest
                                                  first; a copy in Egress last): two at first, then, while matches remain unread
                                                  and fewer than four files were read, a choice between writing the page and
                                                  reading one more (both acceptable; the model advises; the default is to write)
  write      documents.create {title, text}       the page "Files about <topic>", its first paragraph the request and the words
                                                  searched for
  lines_k    documents.edit {change: {append}}    one paragraph per finding, then "Looked in Files and Ingress on <date> · N
                                                  matches · read M", each bound to the revision the previous write returned
  done       'Found N files about <topic>; the findings page is in Documents' (inspect opens it; nothing opens by itself)

Reads happen only through receiving.status, files.find and files.get (both inside Files) and ledger.browse (the Ingress
listing); at most four files are read; the two document writes are the only writes. Nothing here starts a worker, a model
or a native tool. A findings page that moved on while Slate wrote it is never merged: Resume writes a fresh page. The worst
case (20 matches, 5 in Ingress, 4 reads, the retry) is 35 steps, inside the default budget of 40.
"""
from __future__ import annotations
import re
import time
from . import agent_profiles as base

FIND_LIMIT = 20          # matches files.find returns (and findings written for Files)
INGRESS_LIMIT = 5        # names in Ingress written as findings
READ_FIRST = 2           # files read before the first choice
READ_LIMIT = 4           # files read at most, whatever the model advises
LISTING_LIMIT = 500
TOPIC_LIMIT = 180
READABLE = ('markdown', 'text', 'code')                         # files.get gives their lines as data.lines
TEXTUAL = READABLE + ('json', 'csv', 'kicad', 'dxf')            # the kinds files.find searches by words
LINE_WORDS = 160
TABLE_ROWS = 2000        # files_service.DATA_ROWS: the rows files.get gives of a table at most
STOP = frozenset(('the', 'a', 'an', 'of', 'and', 'or', 'to', 'in', 'on', 'for', 'my', 'our', 'his', 'her', 'their', 'this', 'that', 'these',
                  'those', 'some', 'any', 'all', 'me', 'us', 'you', 'it', 'them', 'with', 'from', 'at', 'by', 'is', 'are'))
PURPOSES = {'where': 'Asking where Ingress is', 'find': 'Looking through Files', 'find_word': 'Looking through Files for the word “%s”',
            'ingress': 'Listing Ingress by name', 'read': 'Reading the first lines of %s', 'write': 'Starting the findings page',
            'lines': 'Writing line %d of %d on the findings page'}
NO_TOPIC = 'Say what the files should be about, like “find files about pellets”.'
PAGE_MOVED = 'The findings page changed while Graphite was writing it; Resume writes a fresh page instead of merging.'

# The owner's words: a verb, a noun, a link word and the topic, in that order. Up to three words may come before the verb
# ("please", "Slate,") and up to four between the verb and the noun ("me all the", "any recent"). A kind of file (files,
# documents, drawings, sheets) may follow any verb, the questions included ("are there any files about…", "what documents do
# we have on…"); "anything" / "something" only follow find, look for, search or list, and never with "for", so everyday
# questions ("is there anything on TV tonight", "do we have anything for a headache", "show me something about Python")
# stay with the model.
_VERB = r'(?:find|look\s+for|look\s+up|look\s+through|search(?:\s+for|\s+through)?|show(?:\s+me)?|list|what|which|do\s+we\s+have|have\s+we\s+got|are\s+there|is\s+there)'
_KIND = r'(?:files?|documents?|docs|drawings?|sheets?|spreadsheets?)'
_ASK = r'(?:find|look\s+for|search(?:\s+for|\s+through)?|list)'             # the verbs “anything” / “something” may follow
_VAGUE = r'(?:anything|something)'
_LINK = r'(?:about|on|for|mentioning|mentions?|called|named|regarding|concerning)'
_VAGUE_LINK = r'(?:about|on|mentioning|mentions?|called|named|regarding|concerning)'
_FILL = r'(?:\s+(?:do|does|did|we|have|has|got|are|is|there|you|i|all|any|some|the|our|my|me|please|that|here))*'
REQUEST = re.compile(r'^(?:\S+\s+){0,3}?(?:' + _VERB + r'\b(?:\s+\S+){0,4}?\s+' + _KIND + r'\b' + _FILL + r'\s+' + _LINK +
                     r'|' + _ASK + r'\b(?:\s+\S+){0,4}?\s+' + _VAGUE + r'\b' + _FILL + r'\s+' + _VAGUE_LINK + r')\s+(?P<topic>.+?)\s*$', re.I)
_TRAIL = re.compile(r'(?:[\s,]+(?:please|for\s+me|slate|now|thanks|thank\s+you|in\s+ledger))+$', re.I)
_LEAD = re.compile(r'^(?:the|a|an|my|our|some|any|all|these|those)\s+', re.I)
# A request that points at what is on screen belongs to another procedure (or the model, which is given the open page), wherever
# the pointing words stand: "search this document for pellets", "find anything on this page about pellets", "is there anything
# about pellets in this file", "which of these documents…", "…here". Searching one page, sheet or drawing ("search the document
# for the word pellet", "search the sheet for totals") is a search of what is open, not of Files.
_SCREEN = re.compile(r'\b(?:this|that|these|those)\s+(?:pages?|documents?|docs?|sheets?|spreadsheets?|drawings?|files?|ones?|screen)\b|'
                     r'\bhere$|\bon\s+(?:the\s+)?screen$', re.I)
_CONTAINER = re.compile(r'^(?:\S+\s+){0,3}?(?:search(?:\s+through|\s+in)?|look\s+(?:through|in)|go\s+through)\s+(?:the|this|that|my|our)\s+'
                        r'(?:(?:current|open)\s+)?(?:page|document|doc|sheet|spreadsheet|drawing|file)\s+for\b', re.I)
# a topic that only points at what is on screen, or names nothing, rather than naming a subject
_HERE = re.compile(r'^(?:(?:this|that|these|those|the|my|our)\s+)?(?:pages?|documents?|docs?|sheets?|spreadsheets?|drawings?|files?|ones?|screen)$|'
                   r'^(?:here|there|it|this|that|these|those|them|something|anything|everything)$|'
                   r'\b(?:this|that|the)\s+(?:page|document|doc|sheet|spreadsheet|drawing|screen)$', re.I)


def normal(text):
    return ' '.join(str(text or '').replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"').split())


def plain(text):
    return normal(text).casefold()


def words_in(text):
    """Letters and digits of any script ("Müller" stays one word, "鸡蛋" is a word); punctuation and underscores split."""
    return re.findall(r'[^\W_]+', plain(text))


def significant(text):
    """The topic's words of two letters or more (one letter of a script that is not Latin, like 蛋, is a word) that are not
    stop words."""
    return [w for w in words_in(text) if (len(w) >= 2 or not w.isascii()) and w not in STOP]


def clean_topic(text):
    topic = str(text or '').strip()
    for _ in range(3):
        topic = topic.rstrip('.?!…,;:').strip()
        topic = _TRAIL.sub('', topic).strip()
        topic = topic.strip('"\'«»').strip()
    return topic


def topic_of(text):
    """The topic in a request that fits ("find files about Pellets" -> "Pellets"), or None. The owner's own letters are kept;
    trailing punctuation, quotes and polite words are dropped; at least one word that is not a stop word must remain; a request
    that points at the screen anywhere ("search this document for…", "…on this page about…", "…here") or searches one page,
    sheet or drawing ("search the sheet for totals") does not fit, nor a topic that only points ("this page", "it") or names
    nothing ("something"); at most 180 characters are kept (the title has room)."""
    words = normal(text)
    if not words: return None
    whole = clean_topic(words)
    if _SCREEN.search(whole) or _CONTAINER.match(whole): return None
    found = REQUEST.match(words)
    if not found: return None
    topic = clean_topic(found.group('topic'))
    if not topic or _HERE.search(topic) or not significant(topic): return None
    return topic[:TOPIC_LIMIT]


def fits(text):
    """Explicit words choose this profile: a verb + a noun + a link word + a topic. No model."""
    return topic_of(text) is not None


def stem(word):
    """A plural's ending taken off, so a substring search finds the singular and the plural alike ("pellets" -> "pellet",
    "boxes" -> "box", "batteries" -> "batter"). Words ending in ss, us or is stay as they are, and so does a word of four
    letters or fewer ("news", "Mars", "lens", "eggs"): its three-letter remainder ("new", "mar") would match inside almost any
    name or line, and files.find is a plain substring search."""
    w = str(word)
    if len(w) - 3 >= 4 and w.endswith('ies'): return w[:-3]
    if len(w) - 2 >= 3 and (w.endswith(('ches', 'shes')) or (w.endswith('es') and w[-3:-2] in ('s', 'x', 'z'))): return w[:-2]
    if len(w) >= 5 and w.endswith('s') and not w.endswith(('ss', 'us', 'is')): return w[:-1]
    return w


def needle_of(topic):
    """What files.find looks for: the topic without a leading article, each word's plural ending taken off (“the pellets” ->
    “pellet”), within files.find's 200 characters."""
    text = _LEAD.sub('', normal(topic)) or normal(topic)
    return ' '.join(stem(w) for w in text.casefold().split())[:200]


def topic_words(topic):
    """The words a name in Ingress must carry (every one of them) to count as a match, plural endings taken off."""
    return [stem(w) for w in (significant(topic) or words_in(topic))]


def longest_word(topic):
    words = topic_words(topic)
    return max(words, key=len) if words else ''


def name_matches(name, words):
    low = plain(name)
    return bool(words) and all(w in low for w in words)


def one_line(text, limit=32000):
    return ' '.join(str(text or '').split())[:limit]


def size_words(size):
    if size is None: return 'size unknown'
    size = float(size)
    for unit in ('bytes', 'KB', 'MB', 'GB'):
        if size < 1024 or unit == 'GB': return ('%d %s' % (size, unit)) if unit == 'bytes' else ('%.1f %s' % (size, unit))
        size /= 1024
    return str(size)


def day_words(stamp):
    try: return time.strftime('%Y-%m-%d', time.localtime(float(stamp)))
    except (TypeError, ValueError, OverflowError): return 'date unknown'


def place_words(rel):
    parent = str(rel or '').rsplit('/', 1)[0] if '/' in str(rel or '') else ''
    return 'Files › ' + parent if parent else 'Files'


def compact(row, word=None):
    """A files.find row as the context keeps it (small, storable, enough for the page)."""
    out = {'name': row.get('name'), 'path': row.get('path'), 'kind': row.get('kind'), 'kind_words': row.get('kind_words') or str(row.get('kind') or 'file').title(),
           'size': row.get('size'), 'modified': row.get('modified'), 'found': row.get('found') or 'name', 'place': place_words(row.get('path'))}
    if word: out['word'] = word
    return out


def match_words(m):
    how = 'matched by name' if m.get('found') == 'name' else 'matched on ' + str(m.get('found') or 'its words')
    if m.get('word'): how = how.replace('matched', 'matched “%s”' % m['word'], 1)
    return one_line('%s · %s · %s · changed %s · %s' % (m['name'], m['place'], size_words(m.get('size')), day_words(m.get('modified')), how))


def ingress_words(m):
    return one_line('%s · Ingress · %s · changed %s · waiting to be received, not read' % (m['name'], size_words(m.get('size')), day_words(m.get('modified'))))


def first_line_of(result):
    """What files.get showed of the file: its first non-empty line, or what kind of file it is when it has no lines."""
    data = result.get('data') if isinstance(result.get('data'), dict) else {}
    for row in data.get('lines') or []:
        text = one_line((row or {}).get('text') if isinstance(row, dict) else row)
        if text: return {'line': text[:LINE_WORDS] + ('…' if len(text) > LINE_WORDS else '')}
    facts = result.get('facts') if isinstance(result.get('facts'), dict) else {}
    view = result.get('view') if isinstance(result.get('view'), dict) else {}
    kind = result.get('kind_words') or str(result.get('kind') or 'file').title()
    rows = data.get('rows')
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):   # a table or a sheet: its columns say what it holds
        columns = ', '.join(str(k) for k in rows[0]); count = '%d+' % len(rows) if len(rows) >= TABLE_ROWS else str(len(rows))   # files.get gives at most 2000
        return {'about': one_line('%s · columns %s · %s row%s' % (kind, columns[:LINE_WORDS], count, '' if len(rows) == 1 else 's'), 300)}
    texts = [t for t in (data.get('texts') or []) if isinstance(t, dict) and one_line(t.get('text'))]
    if texts: return {'about': one_line('%s · first text “%s”' % (kind, one_line(texts[0]['text'])[:LINE_WORDS]), 300)}
    if facts: return {'about': one_line('%s · %s' % (kind, ', '.join('%s %s' % (k, v) for k, v in list(facts.items())[:3])), 300)}
    if isinstance(view.get('summary'), str): return {'about': one_line('%s · %s' % (kind, view['summary']), 300)}
    return {'about': kind}


def read_words(name, first):
    if first.get('line'): return one_line('First line of %s: “%s”' % (name, first['line']))
    return one_line('%s has no lines to read: %s' % (name, first.get('about') or 'a file'))


def rank(m, words=()):
    """Best first: a copy in Egress last; every topic word in the name or the matched line first (after a word search); a name
    match before a word match; readable kinds before others; newest first."""
    from .files_service import EXPORTS
    path = str(m.get('path') or ''); seen = plain(str(m.get('name') or '') + ' ' + str(m.get('found') or ''))
    return (1 if path.startswith(EXPORTS + '/') else 0, 0 if all(w in seen for w in words) else 1, 0 if m.get('found') == 'name' else 1,
            0 if m.get('kind') in READABLE else (1 if m.get('kind') in TEXTUAL else 2), -float(m.get('modified') or 0))


def best(matches, words=()):
    return sorted(matches or [], key=lambda m: rank(m, words))


def follow(out, more):
    """out with what comes next (after_reading) added: its claims join out's claims instead of replacing them."""
    more = dict(more or {}); claims = list(out.get('claims') or []) + list(more.pop('claims', None) or [])
    out.update(more)
    if claims: out['claims'] = claims
    return out


class FilesAbout(base.Profile):
    name = 'files_about'
    title = 'Files about something'
    words = 'Looks through Files and Ingress for files whose names or words match, reads the first lines of the best matches and writes a findings page.'
    needs = ()

    # -- the words that choose it -----------------------------------------------------------------------------------------------
    def fits(self, words): return fits(words)
    def topic_of(self, words): return topic_of(words)

    def topic(self, state):
        """The topic from the request's words; when the profile was named outright with free words, the words themselves."""
        context = state.get('context') or {}
        if context.get('topic'): return context['topic']
        request = normal(state.get('request'))
        return topic_of(request) or clean_topic(request)[:TOPIC_LIMIT]

    # -- planning -----------------------------------------------------------------------------------------------------------------
    def plan(self, context, kernel, principal):
        return [base.step('where', PURPOSES['where'], 'receiving.status', {}), base.step('find', PURPOSES['find'], 'files.find', {})]

    def read_step(self, m, number):
        return base.step('read_%d' % number, PURPOSES['read'] % m['name'], 'files.get', {'path': m['path']}, name=m['name'])

    def write_step(self):
        return base.step('write', PURPOSES['write'], 'documents.create', {})

    def line_steps(self, context, state):
        matches = best(context.get('matches'), topic_words(self.topic(state))); read = {r['path']: r for r in context.get('read') or []}
        ingress = list(context.get('ingress_matches') or [])
        rows = []   # best first: the same order the findings and the reads follow
        for m in matches:
            text = match_words(m); got = read.get(m['path'])
            if got: text += ' · ' + ('first line: “%s”' % got['first']['line'] if got['first'].get('line') else got['first'].get('about', ''))
            rows.append(text)
        rows += [ingress_words(m) for m in ingress]
        where = 'Files and Ingress' if context.get('ingress_path') else 'Files'
        count = len(matches) + len(ingress)
        rows.append('Looked in %s on %s · %d match%s · read %d' % (where, time.strftime('%Y-%m-%d'), count, '' if count == 1 else 'es', len(read)))
        total = len(rows)
        return [base.step('lines_%d' % (n + 1), PURPOSES['lines'] % (n + 1, total), 'documents.edit', {}, text=one_line(text)) for n, text in enumerate(rows)]

    def question(self, context, state):
        """The one QUESTION when nothing matched: written only once Ingress (when it is listed) has nothing either."""
        searched = context.get('searched') or [needle_of(self.topic(state))]
        return {'role': 'QUESTION', 'text': 'No file in Files has %s in its name or words (looked at %d). Is it spelt differently, or kept somewhere else?'
                % (' or '.join('“%s”' % s for s in searched), int(context.get('looked_at') or 0))}

    def after_reading(self, context, state):
        """What comes after the reads: done with the QUESTION when nothing was found anywhere; a choice (write, or read one
        more) while matches remain unread and the read budget allows; otherwise the write."""
        matches = list(context.get('matches') or []); read_paths = {r['path'] for r in context.get('read') or []}
        topic = self.topic(state)
        if not matches and not context.get('ingress_matches'):
            where = 'Files or Ingress' if context.get('ingress_path') else 'Files'
            return {'done': True, 'claims': [self.question(context, state)],
                    'reason': 'Found no files about %s in %s (looked at %d files)' % (topic, where, int(context.get('looked_at') or 0))}
        unread = [m for m in best(matches, topic_words(topic)) if m['path'] not in read_paths]
        if unread and len(read_paths) < READ_LIMIT:
            number = len(read_paths) + 1
            options = [{'key': 'write', 'purpose': 'Write the findings page', 'step': self.write_step(), 'acceptable': True},
                       {'key': 'read_%d' % number, 'purpose': 'Read one more match: ' + str(unread[0]['name'])[:120], 'step': self.read_step(unread[0], number), 'acceptable': True}]
            situation = '%d files about %s in Files, %d read so far, %d not read; the page can be written now' % (len(matches), topic, len(read_paths), len(unread))
            return {'options': options, 'situation': situation}
        return {'steps': [self.write_step()]}

    # -- arguments as known now --------------------------------------------------------------------------------------------------
    def arguments(self, step, state, kernel, principal):
        context = state.get('context') or {}; key = step['key']
        if key == 'where': return {}
        if key == 'find':
            needle = needle_of(self.topic(state))
            if not needle: raise ValueError(NO_TOPIC)
            return {'text': needle, 'limit': FIND_LIMIT}
        if key == 'find_word':
            word = step.get('word') or longest_word(self.topic(state))
            if not word: raise ValueError(NO_TOPIC)
            return {'text': word, 'limit': FIND_LIMIT}
        if key == 'ingress':
            if not context.get('ingress_path'): raise ValueError('No Ingress folder is known for this workspace.')
            return {'path': context['ingress_path'], 'limit': LISTING_LIMIT}
        if key.startswith('read_'): return dict(step.get('arguments') or {})
        if key == 'write':
            topic = self.topic(state); searched = context.get('searched') or [needle_of(topic)]
            text = 'Request: “%s” · Graphite searched Files for %s' % (one_line(state.get('request'), 1000), ', then '.join('“%s”' % s for s in searched))
            return {'title': one_line('Files about ' + topic, 200), 'text': text, 'origin': 'SLATE'}
        if key.startswith('lines_'):
            if context.get('document_revision') is None or not context.get('document'): raise ValueError('Start the findings page first: no page is known yet.')
            return {'id': context['document'], 'expected_revision': context['document_revision'], 'selection': {'block': int(context.get('last_index') or 0), 'start': 0, 'end': 0},
                    'change': {'append': one_line(step.get('text'))}, 'origin': 'SLATE', 'request': one_line(state.get('request'), 400)}
        return dict(step.get('arguments') or {})

    # -- reading the results ----------------------------------------------------------------------------------------------------
    def found(self, step, result, state, word=None):
        """The answer of files.find (the topic, or its longest word on the retry) as findings, the Ingress listing and the first reads."""
        context = state.get('context') or {}; topic = self.topic(state)
        matches = best([compact(r, word) for r in (result.get('records') or []) if isinstance(r, dict) and r.get('path')][:FIND_LIMIT], topic_words(topic))
        searched = list(context.get('searched') or []) + [word or needle_of(topic)]
        updates = {'matches': matches, 'looked_at': int(result.get('looked_at') or 0), 'read': [], 'searched': searched,
                   'ingress_matches': list(context.get('ingress_matches') or [])}
        if not matches and word is None and len(topic_words(topic)) > 1 and longest_word(topic):
            retry = longest_word(topic)   # a topic of several words matched nothing as a phrase: once more with its longest word
            return {'context_updates': updates, 'steps': [base.step('find_word', PURPOSES['find_word'] % retry, 'files.find', {}, word=retry)]}
        # nothing in Files: the QUESTION waits for the Ingress listing (after_reading asks it only when Ingress has nothing either)
        out = {'context_updates': updates, 'claims': [{'role': 'FINDING', 'text': match_words(m)} for m in matches]}
        steps = [base.step('ingress', PURPOSES['ingress'], 'ledger.browse', {})] if context.get('ingress_path') and context.get('ingress_waiting') else []
        steps += [self.read_step(m, n + 1) for n, m in enumerate(best(matches, topic_words(topic))[:READ_FIRST])]
        if steps: out['steps'] = steps
        else: follow(out, self.after_reading({**context, **updates}, state))
        return out

    def interpret(self, step, result, state, kernel, principal):
        context = state.get('context') or {}; key = step['key']; result = result if isinstance(result, dict) else {}
        if key == 'where':
            inbox = result.get('inbox')
            return {'context_updates': {'topic': self.topic(state), 'ingress_path': str(inbox) if inbox else None, 'ingress_waiting': len(result.get('inbox_waiting') or [])}}
        if key == 'find': return self.found(step, result, state)
        if key == 'find_word': return self.found(step, result, state, step.get('word') or longest_word(self.topic(state)))
        if key == 'ingress':
            words = topic_words(self.topic(state))
            entries = [e for e in (result.get('entries') or []) if isinstance(e, dict) and e.get('kind') == 'file' and not e.get('hidden')]
            found = [{'name': e['name'], 'size': e.get('bytes'), 'modified': e.get('modified'), 'place': 'Ingress'} for e in entries if name_matches(e.get('name'), words)][:INGRESS_LIMIT]
            updates = {'ingress_matches': found, 'ingress_listed': len(entries)}
            out = {'context_updates': updates, 'claims': [{'role': 'FINDING', 'text': ingress_words(m)} for m in found]}
            following = self.next(state)
            if following is None or not str(following.get('key', '')).startswith('read_'): follow(out, self.after_reading({**context, **updates}, state))
            return out
        if key.startswith('read_'):
            path = (step.get('arguments') or {}).get('path'); name = step.get('name') or result.get('name') or path
            first = first_line_of(result)
            read = [r for r in (context.get('read') or []) if r.get('path') != path] + [{'path': path, 'name': name, 'first': first, 'kind': result.get('kind')}]
            updates = {'read': read}
            out = {'context_updates': updates, 'claims': [{'role': 'FINDING', 'text': read_words(name, first)}]}
            following = self.next(state)
            if following is None or not str(following.get('key', '')).startswith('read_'): follow(out, self.after_reading({**context, **updates}, state))
            return out
        if key == 'write':
            doc = result.get('document') if isinstance(result.get('document'), dict) else result
            if not doc.get('id'): return {'waiting': 'The findings page was not created; ask again.'}
            updates = {'document': doc['id'], 'document_revision': doc.get('revision', 1), 'last_index': max(len(doc.get('blocks') or []) - 1, 0),
                       'documents': list(dict.fromkeys(list(context.get('documents') or []) + [doc['id']])), 'document_title': doc.get('title')}
            return {'context_updates': updates, 'steps': self.line_steps({**context, **updates}, state)}
        if key.startswith('lines_'):
            applied = result.get('applied') or {}; doc = result.get('document') or {}
            if not applied.get('appended_block'): return {'waiting': 'The findings page did not take the line; ask again.'}
            updates = {'document_revision': doc.get('revision', (context.get('document_revision') or 0) + 1), 'last_index': applied.get('appended_index', int(context.get('last_index') or 0) + 1)}
            following = self.next(state)
            if following is not None and str(following.get('key', '')).startswith('lines_'): return {'context_updates': updates}
            matches = list(context.get('matches') or []); ingress = list(context.get('ingress_matches') or []); read = list(context.get('read') or [])
            topic = self.topic(state); total = len(matches) + len(ingress)
            summary = '%d file%s about %s: %d in Files, %d waiting in Ingress; Graphite read the first lines of %d.' % (total, '' if total == 1 else 's', topic, len(matches), len(ingress), len(read))
            return {'context_updates': updates, 'claims': [{'role': 'FINDING', 'text': summary}], 'done': True,
                    'reason': 'Found %d file%s about %s; the findings page is in Documents' % (total, '' if total == 1 else 's', topic)}
        return {}

    def failed(self, step, error, state, kernel, principal):
        """After a refused or failed step the loop replaces what came after it with these steps and waits for the owner."""
        key = step['key']; words = str(error); plan = state.get('plan') or []; cursor = state.get('cursor', 0); context = state.get('context') or {}
        rest = [dict(s) for s in plan[cursor + 1:]]
        if key == 'where':
            out = {'waiting': 'Graphite could not ask where Ingress is (%s). Resume goes on with Files alone.' % words}
            if rest: out['steps'] = rest
            return out
        if key == 'ingress':
            out = {'waiting': 'Ingress could not be listed (%s). Resume goes on with Files alone.' % words}
            if rest: out['steps'] = rest
            elif context.get('matches'): out['steps'] = [self.write_step()]
            else: out['claims'] = [self.question(context, state)]   # Files had nothing either: the QUESTION held back for Ingress
            return out
        if key.startswith('read_'):
            name = step.get('name') or (step.get('arguments') or {}).get('path')
            return {'waiting': 'Graphite could not read %s (%s). Resume goes on without it.' % (name, words), 'steps': rest or [self.write_step()]}
        if key.startswith('lines_') and 'REVISION_CHANGED' in words: return {'waiting': PAGE_MOVED, 'steps': [self.write_step()]}
        return {'waiting': 'Step %s (%s) did not run: %s' % (key, step.get('purpose') or key, words)}

    def done(self, state):
        """Finished only when interpret says so (the last line written, or nothing found anywhere). The plan often ends on a read
        whose interpret offers the next steps as options (write the page, or read one more); the loop checks done(state) before
        it takes options, so the default rule (the cursor is past the plan) would finish the assignment before the page exists.
        Should the plan ever run out without that word, agent.step still completes it ('Finished: N steps ran')."""
        return False

    def describe(self, state):
        if state.get('state') in ('WAITING', 'DONE') and state.get('reason'): return str(state['reason'])
        current = self.next(state)
        if current is None: return super().describe(state)
        plan = state.get('plan') or []; purpose = current['purpose']
        if current['key'] == 'find': purpose = 'Looking through Files for “%s”' % needle_of(self.topic(state))
        return '%s (step %d of %d)' % (purpose, min(state.get('cursor', 0) + 1, len(plan)), len(plan))


PROFILE = FilesAbout()
# agent_profiles registers this profile when it imports this module. When this module is imported first, agent_profiles runs
# in the middle of that import and finds no PROFILE yet (it marks the profile unavailable); registering here puts it right.
if base.PROFILES.get(PROFILE.name) is not PROFILE: base.register(PROFILE)
