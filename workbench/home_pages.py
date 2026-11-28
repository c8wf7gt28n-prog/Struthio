"""Her reading of a document of your home: its pages, as data (Graphite 1.0 K10).

Found by the everyday walkthrough (X3, session 13): asked "is there anything in this manual about the machine draining
slowly?" with the manual in focus, she read the file's record (its name, kind and size) and her model said the records hold
nothing about it, while page 3 of the manual says what to do. Her read of a file of your home was its record, never its
pages. Now:

  "what does the manual say about draining slowly?"          "is there anything in this manual about the filter?"
  "does the lease say anything about repairs?"               "what does my budget say about groceries?"

  1. The document is the one the words name among the documents of your home (Documents, Desktop, Downloads and the folders
     in them: a PDF, a Writer or Calc file, a text file), or the one in focus when they point at it ("this manual", "it").
     Two that fit equally are said, never guessed.
  2. Its pages are read through the readers the Library already uses for a source (sdk document_extract: the PDF reader with
     Poppler's page text, the plain text reader; office_bridge.read_odf for an OpenDocument file), never a second reader.
  3. Each page goes through the same doorway as a source (page_marks.Page, doorway.scan): a line written to an assistant,
     a line with hidden characters or look-alike letters is withheld, from the model and from her quote, and said.
  4. The places that carry the words of the question are ranked by the Library's one rule (library_service.source_rows and
     rank, places.score). With her model here, the Library's ASK turn is asked about the best page (the model may only point
     at a line and copy a few of its words; the desk checks them on the page and cuts the quote itself). With no model, or
     when the model is late or points at nothing, the desk's best place stands.
  5. Her answer names the page it came from: “Washing machine manual.pdf”, page 3: “If the machine drains slowly, …”. "The
     pages say nothing" only when no line of them carries the words, and the model (when it is here) pointed at none.

It is a read: the registry's tool 27 (file.pages), used through tools.use like any tool, so her answer carries its receipt
(dispatched, then verified: the file's digest is the same before and after the read). The Kernel operation:

  file.pages   {path, question?}   read   the document's pages read as data, through the doorway; with a question, the
                                          places that answer it and her answer (at most one ASK turn per page, three pages)

No floating point in anything checked: places are ranked by exact Fractions (places.score), revisions are digests.
"""
from __future__ import annotations

import hashlib
import os
import re
import threading
from pathlib import Path

SCHEMA = 'graphite.file-pages/1'
TOOL = 27                     # the registry's number for file.pages (1.0 K10)
TEXT_READS = ('.pdf', '.txt', '.md', '.docx', '.csv', '.tsv')     # through sdk document_extract (the Library's readers)
ODF_READS = ('.odt', '.ods')                                       # through office_bridge.read_odf (K5's direct reader)
READS = TEXT_READS + ODF_READS
LOOKED = ('Documents', 'Desktop', 'Downloads')                     # where a named document is looked for first
MOST_FILES = 400              # documents of your home looked at for the one the words name
MOST_DEPTH = 3                # folders below your home looked into
MOST_PAGES = 64               # pages (or sheets) read of one document
MOST_ASKED = 3                # pages her model is asked about, at most (the request's ceiling decides too)
POINTING = ('this', 'it', 'that', 'this one', 'that one', 'this file', 'this document', 'the file', 'the document', 'this page')
LEAD = r'^\s*(?:(?:kas|kasandra)\s*[,:]\s*)?(?:(?:please|can\s+you|could\s+you)\s+)*'
END = r'\s*[?.!]*\s*$'
ASKED = (
    re.compile(LEAD + r'(?:what|where)\s+(?:does|do|did)\s+(?P<doc>.+?)\s+say\s+(?:to\s+do\s+)?(?:about|on|regarding|if|when|for)\s+'
               r'(?P<topic>.+?)' + END, re.I),
    re.compile(LEAD + r'(?:is|are)\s+there\s+(?:anything|something|a\s+word|a\s+line|a\s+passage|a\s+page)\s+in\s+(?P<doc>.+?)\s+'
               r'(?:about|on|regarding|for)\s+(?P<topic>.+?)' + END, re.I),
    re.compile(LEAD + r'(?:does|do|did)\s+(?P<doc>.+?)\s+(?:say\s+anything\s+(?:about|on)|mention|cover|talk\s+about)\s+(?P<topic>.+?)' + END, re.I),
    re.compile(LEAD + r'(?:which|what)\s+(?:page|part)\s+of\s+(?P<doc>.+?)\s+(?:is\s+about|says\s+anything\s+about|covers|talks\s+about|mentions)\s+'
               r'(?P<topic>.+?)' + END, re.I),
    re.compile(LEAD + r'(?:look|search)\s+in\s+(?P<doc>.+?)\s+for\s+(?P<topic>.+?)' + END, re.I),
)
SMALL = frozenset(('the', 'my', 'our', 'your', 'this', 'that', 'a', 'an', 'its', 'his', 'her', 'their', 'in', 'of'))
KIND_WORDS = {'.pdf': ('pdf',), '.odt': ('letter', 'document', 'writer'), '.ods': ('spreadsheet', 'sheet', 'calc', 'workbook'),
              '.txt': ('text', 'note', 'list'), '.md': ('text', 'note'), '.docx': ('document', 'word'), '.csv': ('table',), '.tsv': ('table',)}

# ---- her words (fixed templates; numbers through named slots) -------------------------------------------------------------
WORDS = {
    'reading': 'I am reading the pages of “{file}” for {topic}.',
    'says': '“{file}”, {where}: “{quote}”',
    'pointed': 'My model pointed at line {line} there; the desk found its words on that line and cut the quote itself.',
    'not_used': 'My model was not used ({why}); the place is the desk’s own find.',
    'nothing': 'I read “{file}” ({count} {unit}): it says nothing about {topic}. No line in it carries those words.',
    'nothing_model': 'I read “{file}” ({count} {unit}): it says nothing about {topic}. No line in it carries those words, and my '
                     'model, asked about its pages, pointed at none.',
    'withheld': '{count} lines of it are written to an assistant or hide characters. I withheld them: not read to the model, '
                'not quoted.',      # 1.1 KV
    'withheld_one': 'One line of it is written to an assistant or hides characters. I withheld it: not read to the model, '
                    'not quoted.',
    'read_how': 'Read as data ({count} {unit}, revision {revision}), every line checked at the doorway.',
    'receipt': 'Receipt: {tool}, {where}, {complete}, {status}.',
    'not_read': 'I could not read “{file}”: {why}',
    'which': 'Two documents could be meant, “{one}” and “{two}”: say which, or put the one you mean in focus.',
    'no_text': '“{file}” has no text I can read: {why}.',
}
NUMBERS = {'nothing': {'count': 'file.pages: the pages (lines, paragraphs, sheets) read'}, 'nothing_model': {'count': 'file.pages: the pages read'},
           'withheld': {'count': 'file.pages: the lines the doorway withheld'}, 'read_how': {'count': 'file.pages: the pages read'},
           'pointed': {'line': 'brain.turn/1 ASK: the line, checked on the page'}}
try:
    from . import mind_words
    mind_words.register('home_pages', WORDS, kind='sentence', numbers=NUMBERS)
except Exception:  # noqa: BLE001 - the words stand without the check
    pass


def say(key, **slots):
    return WORDS[key].format(**slots)


# ---------------------------------------------------------------- the readers (the Library's own; nothing new)
def readable(path):
    path = Path(path)
    return path.suffix.lower() in READS and path.is_file()


def _sha(path):
    sha = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):sha.update(block)
    return sha.hexdigest()


def _odf_pages(path):
    """An OpenDocument file as pages: a Writer text is one page of paragraphs (each its own place, said "paragraph n"); each
    sheet of a Calc file is a page of rows (each its own place, said "sheet S, row n")."""
    from . import office_bridge
    doc = office_bridge.read_odf(path)
    pages = []
    if doc.get('kind') == 'text':
        lines, units = [], {}
        for n, para in enumerate(p for p in doc.get('paragraphs') or () if str(p).strip()):
            if lines:lines.append('')
            units[len(lines) + 1] = 'paragraph %d' % (n + 1)
            lines.append(' '.join(str(para).split()))
        pages.append({'segment': 'text', 'locator': {'kind': 'odf_text'}, 'text': '\n'.join(lines), 'label': 'the text', 'units': units})
        return pages, 'paragraphs', 'OpenDocument, read directly'
    for sheet in (doc.get('sheets') or ())[:MOST_PAGES]:
        rows = {}
        for ref, cell in (sheet.get('cells') or {}).items():
            m = re.match(r'^([A-Z]{1,3})(\d{1,7})$', ref)
            if m and str(cell.get('text') or '').strip():rows.setdefault(int(m.group(2)), []).append((len(m.group(1)), m.group(1), str(cell['text']).strip()))
        lines, units = [], {}
        for row in sorted(rows):
            if lines:lines.append('')
            units[len(lines) + 1] = 'sheet %s, row %d' % (sheet.get('name') or '?', row)
            lines.append(' · '.join(text for _, _, text in sorted(rows[row])))
        pages.append({'segment': 'sheet:' + str(sheet.get('name')), 'locator': {'kind': 'ods_sheet', 'sheet': sheet.get('name')},
                      'text': '\n'.join(lines), 'label': 'sheet %s' % (sheet.get('name') or '?'), 'units': units})
    return pages, 'sheets', 'OpenDocument, read directly'


def pages_of(path, sha=None):
    """(pages, unit, reader, gaps): a document's pages as the Library's readers give them. pages: [{'segment', 'locator',
    'text', 'label', 'units': {raw line: its place's name}}]. Raises ValueError when it cannot be read."""
    path = Path(path);suffix = path.suffix.lower()
    if suffix in ODF_READS:
        pages, unit, reader = _odf_pages(path)
        return pages, unit, reader, []
    if suffix not in TEXT_READS:raise ValueError('%s is not a kind of document I read (%s)' % (path.name, ', '.join(READS)))
    from sdk.cli.arc1cli import document_extract
    got = document_extract.bounded(path.name, path, sha or _sha(path))
    by_page, order = {}, []
    for segment in got.get('segments') or ():
        loc = segment.get('locator') or {}
        if loc.get('kind') == 'pdf_page':
            key = ('page', int(loc.get('page_index') or 0))
            label = 'page %s' % (loc.get('page_label') or int(loc.get('page_index') or 0) + 1)
        elif loc.get('kind') == 'text_lines':
            key = ('lines', int(loc.get('line_start') or 1));label = 'lines %s to %s' % (loc.get('line_start'), loc.get('line_end'))
        else:
            key = ('part', len(order));label = str(segment.get('label') or 'part %d' % (len(order) + 1))
        if key not in by_page:
            by_page[key] = {'segment': segment.get('id') or str(key), 'locator': loc, 'text': '', 'label': label, 'units': {}}
            order.append(key)
        by_page[key]['text'] += segment.get('text') or ''
    pages = [by_page[k] for k in order][:MOST_PAGES]
    for page in pages:      # a text file's lines are named as lines of the file, not of the piece
        loc = page['locator']
        if loc.get('kind') == 'text_lines':
            start = int(loc.get('line_start') or 1)
            page['units'] = {n: 'line %d' % (start + n - 1) for n in range(1, page['text'].count('\n') + 2)}
    unit = 'pages' if any(p['locator'].get('kind') == 'pdf_page' for p in pages) else 'parts'
    if pages and all(p['locator'].get('kind') == 'text_lines' for p in pages):unit = 'lines'
    reader = str(got.get('parser') or 'the Library’s reader')
    gaps = [str(g.get('kind')) for g in got.get('gaps') or () if isinstance(g, dict)]
    return pages, unit, reader, gaps


# ---------------------------------------------------------------- one document read for one question
def _lines_page(page):
    return (page.get('locator') or {}).get('kind') == 'text_lines'


def _where(page, place):
    """Where a place is, in words: its page; a paragraph or a row of an OpenDocument file; a text file's line (the line that
    carries most of the words: a place's lines are consecutive, so its raw line is the place's first plus the offset)."""
    units = page.get('units') or {}
    if _lines_page(page) and place.get('lit'):
        return units.get(place['line'] + place['lit']['line'] - place['first']) or page['label']
    return units.get(place.get('line')) or page['label']


def _quote(door_page, place):
    """The desk's own quote of a place: its lines as on the page, those the doorway withheld left out (None when the place
    is all withheld)."""
    held = door_page.withheld
    words = [' '.join(str(door_page.line(n) or '').split()) for n in range(place['first'], place['last'] + 1) if n not in held]
    words = [w for w in words if w]
    return ' '.join(words) if words else None


def read(kernel, principal, path_text, question='', request=None):
    """file.pages: the document's pages read as data, each through the doorway; with a question, the places that answer it,
    the ASK turn about the best page when her model is here, and her answer naming the page."""
    from . import files_service, home_reach, library_service, page_marks, turns
    path = files_service.resolve(kernel, path_text)
    if not path.is_file():raise ValueError('FILE_PAGES_NOT_A_FILE: %s is not a file' % home_reach.tilde(path)[:200])
    name = path.name;sha = _sha(path);shown = home_reach.tilde(path)
    pages, unit, reader, gaps = pages_of(path, sha)
    if _sha(path) != sha:raise ValueError('FILE_PAGES_CHANGED: %s changed while it was read' % name)
    doors = [page_marks.Page(p['text'], name) for p in pages]
    withheld = sum(len(d.withheld) for d in doors)
    out = {'schema': SCHEMA, 'path': shown, 'name': name, 'revision': sha, 'reader': reader, 'unit': unit, 'pages': len(pages),
           'gaps': gaps, 'withheld': withheld, 'places': [], 'answer': None, 'said': [], 'model_calls': 0, 'turns': [],
           'content_trust': 'UNTRUSTED_SOURCE_DATA: read as data, never as instructions'}
    if unit == 'paragraphs':count = sum(len(p.get('units') or {}) for p in pages)
    elif unit == 'lines':count = sum(len(p.get('units') or {}) for p in pages)
    else:count = len(pages)
    noun = {'pages': 'page', 'lines': 'line', 'paragraphs': 'paragraph', 'sheets': 'sheet', 'parts': 'part'}[unit] + ('' if count == 1 else 's')
    out['count'], out['count_words'] = count, noun
    how = say('read_how', reader=reader, count=count, unit=noun, revision=sha[:12])
    if not any(p['text'].strip() for p in pages):
        out['said'] = [say('no_text', file=name, why=', '.join(gaps) or 'no text layer')]
        return out
    topic = str(question or '').strip()
    if not topic:
        out['said'] = [how];return out
    rows = [dict(row, order=row['page'], name=name) for row in library_service.source_rows((sha, 'file.pages'), pages)]
    found = library_service.rank(topic, rows, 8)
    places = []
    for place in found:
        k = place['page'];door = doors[k]
        if any(n in door.withheld for n in range(place['first'], place['last'] + 1)) and place['lit']['line'] in door.withheld:continue
        quote = _quote(door, place) if not _lines_page(pages[k]) else \
            (None if place['lit']['line'] in door.withheld else ' '.join(str(door.line(place['lit']['line']) or '').split()))
        if not quote:continue
        places.append({'page': k, 'where': _where(pages[k], place), 'quote': quote, 'matched': place['matched'],
                       'first': place['first'], 'last': place['last'], 'score': place['score']})
    out['places'] = places[:4]
    answer = None;asked = 0;note = ''
    if request is None:
        try:request = turns.request_for(kernel, principal)
        except Exception:  # noqa: BLE001 - no model to ask: the desk's places stand
            request = None
    order = list(dict.fromkeys(p['page'] for p in places)) or list(range(len(pages)))
    for k in order[:MOST_ASKED]:
        if request is None:break
        door = doors[k]
        if not door.open_lines():continue
        try:
            if request.ceiling()['reached'] or request.turns_used >= request.foreground_turns:break
        except Exception:  # noqa: BLE001 - a request that cannot say: asked no further
            break
        its = [p for p in places if p['page'] == k]
        got = turns.ask(library_service.ASK, {'page': door, 'question': topic, 'expect': library_service.expects(topic), 'places': its}, request)
        if got.turn:out['model_calls'] += 1;out['turns'].append(got.turn)
        if not got.by_model:
            if got.outcome == 'NOT_SENT' and got.why in ('OVER_CAP', 'OVER_CONTEXT'):continue      # this page only: the next is asked
            if got.outcome != 'NOT_SENT':note = say('not_used', why=str(got.outcome).lower().replace('_', ' '))
            break
        asked += 1
        hits = (got.value or {}).get('hits') or []
        if hits:
            hit = hits[0]
            stands = next((p for p in library_service.page_places(door.text) if p['first'] <= hit['line'] <= p['last']), None)
            where = _where(pages[k], {'line': stands['line'], 'first': stands['first'], 'lit': {'line': hit['line']}}) if stands else pages[k]['label']
            answer = {'by': 'model', 'page': k, 'where': where, 'quote': hit['quote'], 'line': hit['line'], 'words': hit['value'],
                      'turn': got.turn, 'outcome': got.outcome}
            break
    if answer is None and places:
        top = places[0]
        answer = {'by': 'desk', 'page': top['page'], 'where': top['where'], 'quote': top['quote'], 'matched': top['matched']}
    said = []
    if answer is not None:
        said.append(say('says', file=name, where=answer['where'], quote=answer['quote']))
        if answer['by'] == 'model':
            said.append(say('pointed', line=answer['line'], words=answer['words']))
        elif note:
            said.append(note)      # her model was asked and not used: said; with no model the receipt says how it was read
    else:
        said.append(say('nothing_model' if asked else 'nothing', count=count, unit=noun, file=name, topic=topic))
        if note and not asked:said.append(note.replace(', so the place is the desk’s own find', ''))
    if withheld:said.append(say('withheld', count=withheld) if withheld > 1 else say('withheld_one'))
    said.append(how)
    out['answer'] = answer;out['said'] = said
    return out


# ---------------------------------------------------------------- the registry's tool 27 and its check (K2's door)
def _check_class():
    from . import assignments as _asg

    class PagesRead(_asg.Check):
        """file.pages: a read of a document's pages; its digest on disk the same before and after."""
        kind = 'file';effect = 'nothing (a read)';standin_ms = 3000;repeatable = True
        how = 'its digest on disk is the same before and after its pages were read'
        expected = 'its pages, read at the digest it has on disk, each line through the doorway'

        def prepare(self, kernel, read_, arguments):
            from . import files_service
            path = files_service.resolve(kernel, arguments['path'])
            if not path.is_file():raise _asg.Blocked('%s is not a file' % arguments['path'])
            return {'path': arguments['path'], 'sha256': _sha(path)}

        def find(self, kernel, read_, arguments, prepared):
            return None

        def verify(self, kernel, read_, arguments, result, prepared, step):
            from . import files_service
            now = _sha(files_service.resolve(kernel, prepared['path']))
            if now != prepared['sha256'] or (result or {}).get('revision') != now:raise _asg.NotVerified('the file changed while its pages were read')
            answer = (result or {}).get('answer') or {}
            complete = not (result or {}).get('gaps')
            return {'object': 'files:' + prepared['path'], 'revision': now, 'by': 'sha256', 'complete': complete, 'how': 'observed',
                    'path': prepared['path'], **({'page': answer['where']} if answer.get('where') else {}),
                    'words': 'read %s %s at the digest %s, every line checked at the doorway%s' % (
                        (result or {}).get('count'), (result or {}).get('count_words'), now[:12],
                        (', %d withheld' % result['withheld']) if (result or {}).get('withheld') else '')}

        def still(self, kernel, read_, step):
            from . import files_service
            try:now = _sha(files_service.resolve(kernel, step['prepared']['path']))
            except (ValueError, OSError):return 'it is no longer there'
            return '' if now == (step['observation'] or {}).get('revision') else 'it has changed since its pages were read'
    return PagesRead


def _join():
    """Tool 27 (file.pages) into the registry, its check into the assignments' checks. Guarded: a number or a key already
    taken is never taken over."""
    from . import assignments as _asg
    try:
        _asg.CHECKS.setdefault('file.pages', _check_class()())
        _asg.TOOL_WORDS.setdefault('file', 'Files')
        from . import tools_registry as tr
    except Exception:  # noqa: BLE001 - K1 or K2 is not in this Graphite
        return False
    if 'file.pages' in tr.TOOLS or TOOL in tr.BY_NUMBER:return 'file.pages' in tr.TOOLS
    tool = tr.Tool(TOOL, 'file.pages', "Read a document's pages (a PDF, a Writer or Calc file, a text file) through the Library's own "
                   'readers, as data: every line through the doorway, a line written to an assistant withheld.', 'files', 'read',
                   ('file.pages',), arguments=(tr.Arg('path', 'the document, in your home or in Files', tr.READ_FROM),
                                              tr.Arg('question', 'the words it is read for', tr.READ_FROM, required=False)),
                   preconditions=('the file is there and the account can read it',), effects='nothing: a read', undone='nothing to undo',
                   verify='its digest on disk is the same before and after the read')
    tr.TOOLS[tool.key] = tool;tr.BY_NUMBER[tool.number] = tool
    tr.KEY_OF.setdefault('file.pages', tool.key)
    return True


JOINED = _join()


# ---------------------------------------------------------------- the Kernel's operation
FIELDS = {'file.pages': ({'path': {'type': 'string', 'minLength': 1, 'maxLength': 1000},
                          'question': {'type': 'string', 'maxLength': 300}}, ['path'])}
SCOPES = {'file.pages': 'read'}


def dispatch(kernel, op, args, principal):
    if op == 'file.pages':return read(kernel, principal, args['path'], args.get('question', ''))
    raise ValueError('Unknown file.pages operation')


# ---------------------------------------------------------------- which document the words name
def _terms(text):
    from .places import terms
    return [t for t in terms(text) if t not in SMALL]


def documents(limit=MOST_FILES):
    """The documents of your home Graphite reads pages of: Documents, Desktop and Downloads first, then the other folders,
    MOST_DEPTH deep, dot-names and Graphite's own folders left out. Each with its tier: 0 your own papers (the home folder,
    Documents, Desktop), 1 Downloads, 2 the rest."""
    from . import home_reach
    home = home_reach.home();out = []
    if not home.is_dir():return out
    first = [home / n for n in LOOKED if (home / n).is_dir()]
    rest = sorted((p for p in home.iterdir() if p.is_dir() and not p.name.startswith('.') and p not in first), key=lambda p: p.name.casefold())
    for top in [home] + first + rest:
        depth_top = len(top.relative_to(home).parts)
        for folder, dirs, names in os.walk(top):
            here = Path(folder)
            if top == home or len(here.relative_to(home).parts) - depth_top >= MOST_DEPTH:dirs[:] = []      # the home folder's own files only (its folders come after)
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d != 'Concern')
            for name in sorted(names):
                if name.startswith('.') or Path(name).suffix.lower() not in READS:continue
                out.append(here / name)
                if len(out) >= limit:return out
    return out


def tier(path):
    from . import home_reach
    try:first = Path(path).relative_to(home_reach.home()).parts
    except ValueError:
        return 2
    if len(first) == 1 or first[0] in ('Documents', 'Desktop'):return 0
    return 1 if first[0] == 'Downloads' else 2


def find_document(words, focus=None):
    """(path, '') for the document the words name, (None, her words why not) when two fit equally, (None, '') when none."""
    said = ' '.join(str(words or '').split()).strip().strip('“”"\'')
    low = said.casefold()
    if focus is not None and readable(focus):
        if low in POINTING:return focus, ''
        named = _terms(said)
        if low.startswith(('this ', 'that ')) and (not named or set(named) & set(_terms(focus.stem) + list(KIND_WORDS.get(focus.suffix.lower(), ())))):
            return focus, ''
    named = _terms(said)
    if not named:return None, ''
    scored = []
    for path in documents():
        have = set(_terms(path.stem)) | set(KIND_WORDS.get(path.suffix.lower(), ()))
        hits = sum(1 for w in named if w in have)
        if hits:scored.append((hits, -tier(path), path))
    if not scored:return None, ''
    scored.sort(key=lambda s: (-s[0], -s[1], str(s[2])))      # the most of their words, then your own papers before Downloads
    if len(scored) > 1 and scored[0][:2] == scored[1][:2] and scored[0][2].name != scored[1][2].name:
        return None, say('which', one=scored[0][2].name, two=scored[1][2].name)
    if scored[0][0] * 2 < len(named):return None, ''        # fewer than half of the words fit: not this
    return scored[0][2], ''


def asked(face, text):
    """Shell2's ask: True when the words ask what a document of your home says; the pages are read off the window's thread
    and her answer replaces her "I am reading" line."""
    m = next((p.match(text or '') for p in ASKED if p.match(text or '')), None)
    if m is None:return False
    from .everyday_desk import _focused_path
    host = face.host
    path, why = find_document(m.group('doc'), _focused_path(host))
    if path is None and not why:return False
    face.thing = None;face.mine(text)
    if path is None:
        face.say(why);return True
    from PySide6.QtCore import QTimer
    from . import home_reach
    from .engineering_kernel import Kernel, operator
    topic = m.group('topic').strip()
    card = face.say(say('reading', file=path.name, topic=topic))
    try:root = host.ledger_bridge.kernel.root
    except AttributeError:
        from .locations import default_root
        root = default_root()
    shown = home_reach.tilde(path);result = {}
    face.her_reading = True          # 1.0 K10: her state word says WORKING while she reads for you (her work), never for Graphite's own reads

    def work():
        try:
            used = Kernel(root).dispatch('tools.use', {'number': TOOL, 'arguments': {'path': shown, 'question': topic[:300]},
                                                        'origins': {'path': {'kind': 'DEDUCTION', 'proof': 'the document your words name, or the one in focus'}}},
                                         operator())
            result['used'] = used
        except Exception as exc:  # noqa: BLE001 - said in her words, never raised into the window
            result['used'] = {'ok': False, 'error': {'message': str(exc)}}
    thread = threading.Thread(target=work, name='her-home-pages', daemon=True);thread.start()

    def done():
        if thread.is_alive():
            QTimer.singleShot(150, done);return
        face.her_reading = False
        face.last_pages = answer = words_of(result.get('used') or {}, path.name)
        try:card.set_text(answer)
        except Exception:  # noqa: BLE001 - the card went: said again
            card_ = face.say(answer)
        else:
            card_ = card
        QTimer.singleShot(120, lambda: _show_start(face, card_))
    QTimer.singleShot(150, done)
    return True


def _show_start(face, card):
    """Her answer from its start (the document, the page and the quote), not its receipt, when it is taller than her exchange."""
    try:
        from PySide6.QtCore import QPoint
        scroll = face.scroll;top = card.mapTo(scroll.widget(), QPoint(0, 0)).y()
        bar = scroll.verticalScrollBar()
        if top + card.height() > bar.value() + scroll.viewport().height():bar.setValue(max(0, top - 6))
    except Exception:  # noqa: BLE001 - the card went, or the exchange has no scroll: left as it is
        pass


def words_of(used, name):
    """Her answer from a tools.use of tool 27: her lines, then the receipt of the read."""
    if not used.get('ok'):
        return say('not_read', file=name, why=str((used.get('error') or {}).get('message') or 'refused')[:200])
    got = used['result'];value = got.get('result') or {}
    if got.get('status') != 'verified':
        return say('not_read', file=name, why=str(got.get('words') or 'the read was not verified')[:200])
    lines = list(value.get('said') or ())
    last = (got.get('receipts') or [{}])[-1]
    answer = value.get('answer') or {}
    receipt = say('receipt', tool='%s (tool %s)' % (last.get('tool', 'file.pages'), last.get('number', TOOL)), where=answer.get('where') or 'every page',
                  complete='complete' if last.get('complete') else 'partial', status=last.get('status_words') or last.get('status', ''))
    if lines:lines[-1] = lines[-1] + ' ' + receipt      # the read and its receipt on one line
    else:lines.append(receipt)
    return '\n'.join(lines)
