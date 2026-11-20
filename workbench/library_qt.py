"""The Library on screen (0.8.7 W7, the window wiring): Ask the Library, tables that check themselves and cross-references,
in the reference view and in her column.

0.8.7 C3, C6a and C6b work through the Kernel (library.ask, library.table, library.links); here is where they show:

  Ask the Library   in the reference view (its tab "Ask the Library"), and from the writing line when you ask a question
                    of the Library ("ask the library how long does the landlord have ..."; or any question while the
                    reference view is in front; or "Ask the Library" under her no-model card). Her answer shows, in her
                    order: her lines; the desk's own cut quote with the words the model pointed at lit (a model's pointing
                    carries its mark line, "read by the model, checked against your desk", and the fold "What I asked
                    the model"); the places, each as file · page · label, its words with your words lit, and why it
                    matched; the places that refer to it (crossrefs.into), each on a wire; and the legal footer.
  Read this table   on a page with a table (tables.find_tables), the table cut into columns, each column's role and who
                    named it, its rows, and the closing line ("rows close: 1,204.17 − 1,143.24 + 2,610.40 = 2,671.33, the
                    closing balance.").
  Cross-references  drawn on the page in the reference view (beside each place that refers to another, a quiet wire and
                    the target; beside a place referred to, who refers to it), with their state against the earlier
                    revision (current, to recheck, missing).

Lit words are bold and underlined (a shape, never a colour alone); a wire is an arrow with its words; a state is a word.
Every word of hers here is a template registered with mind_words (WORDS), or the Kernel's own lines as it said them.
No model is asked here: library.ask asks it, through the turn contract, only when one is live and its switch is on.
"""
from __future__ import annotations

import html
import re

from . import mind_words

WORDS = {
    'asking': 'Asking the Library: {query}',
    'asked': 'Your question for the Library: {query}',
    'places': 'Places that may say it',
    'why_matched': 'why: {why}',
    'wire_out': 'refers to {target} · {state}',
    'wire_in': 'referred to by {sources}',
    'wires_head': 'Cross-references on this page: {count}.',
    'state_CURRENT': 'current',
    'state_RECHECK': 'to recheck',
    'state_MISSING': 'missing from this file',
    'open_place': 'Open this place',
    'table_head': 'What the desk read in this table',
    'role_by': '{role}, named {by}',
    'by_HEADER': 'by its header',
    'by_CLOSURES': 'by the closures',
    'by_CELLS': 'by its cells',
    'by_MODEL': 'by the model, checked',
    'by_NONE': 'not named',
    'state_CLOSES': 'Closes',
    'state_DISAGREES': 'Disagrees',
    'state_NO_CLOSURE': 'In pencil',
    'state_CANNOT_TELL': 'Cannot tell',
    'state_NO_CARD': 'Not named',
    'no_table': 'No table on this page.',
    'reading_table': 'Reading this table…',
    'could_not': 'I could not read this: {why}',
    'ask_library': 'Ask the Library',
}
NUMBERS = {'wires_head': {'count': 'library.links: the wires on this page'}}
mind_words.register('library_qt', WORDS, kind='sentence', numbers=NUMBERS)

STATE_MARK = {'CLOSES': '✓', 'DISAGREES': '✗', 'CANNOT_TELL': '?', 'NO_CLOSURE': '·', 'NO_CARD': '·'}      # a shape beside the word

# How a question of the Library is said on the writing line (fixed and short; anything else goes the way it always went)
ASKED = (re.compile(r'^\s*(?:please\s+)?ask\s+(?:the|my)\s+library\b\s*(?:[:,–—-]\s*)?(?:about\s+|whether\s+|if\s+)?(?P<q>.+)$', re.I),
         re.compile(r'^\s*library\s*[:,]\s*(?P<q>.+)$', re.I),
         re.compile(r'^\s*(?:what|where)\s+(?:does|do)\s+(?:the|my)\s+(?:library|papers|admitted\s+pages)\s+say\s+(?:about\s+)?(?P<q>.+)$', re.I))
QUESTION = re.compile(r'\?\s*$|^\s*(?:how|what|when|where|which|who|whom|whose|why|does|do|did|is|are|was|can|could|may|must|shall|will)\b', re.I)


def say(key, **slots):
    return WORDS[key].format(**slots)


def _bt(name, default):
    from . import boss_theme as bt
    return getattr(bt, name, default)


def esc(value):
    return html.escape(str(value), quote=False)


def soft(name):
    """A file name escaped, with a place to break after each underscore, dot and hyphen (her column is narrow)."""
    return re.sub(r'([_.\-])', '\\1\u200b', esc(name))


# ============================================================================================================== the lit words
def _lit_terms(text, matched):
    """`text` escaped, each word whose term is one of `matched` bold and underlined (places.terms reads both alike)."""
    from . import places
    want = set(matched or ())
    out, at = [], 0
    for m in re.finditer(r'[A-Za-z0-9§()]+(?:[\'’][A-Za-z]+)?', text):
        out.append(esc(text[at:m.start()]));word = m.group(0)
        hit = want and any(t in want for t in places.terms(word))
        out.append('<b><u>%s</u></b>' % esc(word) if hit else esc(word));at = m.end()
    out.append(esc(text[at:]))
    return ''.join(out)


def _lit_span(text, lit):
    """`text` escaped with [start, end) bold and underlined: the words the model pointed at, in the desk's own cut."""
    if not lit or len(lit) != 2:return esc(text)
    a, b = int(lit[0]), int(lit[1])
    if not (0 <= a < b <= len(text)):return esc(text)
    return esc(text[:a]) + '<b><u>%s</u></b>' % esc(text[a:b]) + esc(text[b:])


# ============================================================================================================== Ask the Library
def _hit_line(hit, row):
    from .library_service import WORDS as LIB
    if hit.get('label'):return LIB['says'].format(label=hit['label'], page=row.get('page_label'), quote=hit['quote'])
    return LIB['says_unlabelled'].format(name=row.get('name') or 'an admitted file', page=row.get('page_label'), quote=hit['quote'])


def answer_parts(found):
    """Her answer as parts, in her own order: [(kind, text, extra)], kind one of 'line' (her sentence), 'title', 'quote'
    (the desk's cut, the pointed words lit), 'place' (with the place), 'wire', 'footer', 'mark' (the model's mark line)."""
    if not isinstance(found, dict):return []
    places_ = list(((found.get('places') or {}).get('places')) or ())
    by_words = {p.get('words'): p for p in places_}
    wires = set(found.get('links') or ())
    footer = found.get('footer') or ''
    answer = found.get('answer') or {}
    row = answer.get('page') or {}
    hits = {_hit_line(h, row): h for h in answer.get('hits') or ()}
    from .library_service import WORDS as LIB
    out, marked = [], False
    for line in found.get('said') or ():
        if line in hits:
            if not marked:out.append(('mark', 'CHECKED', None));marked = True
            out.append(('quote', line, hits[line]))
        elif line in by_words:out.append(('place', line, by_words[line]))
        elif line in wires:out.append(('wire', line, None))
        elif footer and line == footer:out.append(('footer', line, None))
        elif line == LIB['title'] + ':':out.append(('title', line, None))
        else:out.append(('line', line, None))
    return out


def answer_html(found, links=True):
    """Her answer to a question of the Library as rich text (her column's label, the reference view's browser). Places are
    links 'place:<n>' (n: the place's index in found['places']['places'])."""
    quiet = _bt('QUIET', '#8a8a8a');faint = _bt('FAINT', '#9a9a9a')
    places_ = list(((found or {}).get('places') or {}).get('places') or ())
    out = []
    for kind, text, extra in answer_parts(found):
        if kind == 'mark':
            from .model_words import MARKS
            out.append('<p style="margin:2px 0;color:%s"><i>%s</i></p>' % (quiet, esc(MARKS['CHECKED'])))
        elif kind == 'quote':
            hit = extra;head = (hit.get('label') or '') + ', page ' + str(((found.get('answer') or {}).get('page') or {}).get('page_label') or '')
            out.append('<p style="margin:4px 0 0 0">%s:</p><blockquote style="margin:2px 0 6px 14px">“%s”</blockquote>'
                       % (esc(head.strip(', ')), _lit_span(hit.get('quote') or '', hit.get('lit'))))
        elif kind == 'place':
            p = extra;n = places_.index(p) if p in places_ else -1
            where = ' · '.join(x for x in (soft(p.get('name') or 'an admitted file'), esc('page %s' % (p.get('page_label') or '?')), esc(p.get('label') or '')) if x)
            title = ('<a href="place:%d">%s</a>' % (n, where)) if links and n >= 0 else where
            out.append('<p style="margin:6px 0 0 0">%s. %s</p>' % (esc(p.get('rank', '')), title))
            out.append('<p style="margin:1px 0 0 14px">“%s”</p>' % _lit_terms(p.get('text') or '', p.get('matched')))
            if p.get('why'):out.append('<p style="margin:1px 0 0 14px;color:%s"><small>%s</small></p>' % (faint, esc(say('why_matched', why=p['why']))))
        elif kind == 'wire':
            out.append('<p style="margin:3px 0 0 14px;color:%s">⤷ %s</p>' % (quiet, esc(text)))
        elif kind == 'footer':
            out.append('<p style="margin:8px 0 0 0;color:%s"><small>%s</small></p>' % (faint, esc(text)))
        elif kind == 'title':
            out.append('<p style="margin:6px 0 0 0"><b>%s</b></p>' % esc(say('places')))
        else:
            out.append('<p style="margin:3px 0">%s</p>' % esc(text))
    return ''.join(out)


def asked(face, text):
    """The writing line: a question of the Library? ("ask the library ...", "library: ...", "what does the library say
    about ...", or a question while the reference view is in front). If so, her column asks it and True is returned."""
    query = None
    for pattern in ASKED:
        m = pattern.match(text or '')
        if m and m.group('q').strip():query = m.group('q').strip();break
    if query is None:
        host = getattr(face, 'host', None)
        front = getattr(getattr(host, 'tabs', None), 'currentWidget', lambda: None)()
        if type(front).__name__ == 'ReferenceTab' and QUESTION.search(text or ''):query = text.strip()
    if not query:return False
    face.thing = None
    face.mine(text)
    ask(face, query)
    return True


def ask(face, query, namespace=None):
    """Ask the Library from her column: her card says what she asks, then her answer (answer_html) when the Kernel has it.
    The read runs off the window's thread (library.ask may ask the model one short ASK turn per page)."""
    from .register_tabs import Call
    from .engine import engineering
    from .engineering_kernel import operator
    host = face.host
    card = face.say(say('asking', query=query))
    args = {'query': query[:300], **({'namespace': namespace} if namespace else {})}
    worker = Call(engineering(host.root), 'library.ask', args, operator(), host)
    if not hasattr(host, 'service_workers'):host.service_workers = []
    host.service_workers.append(worker)
    worker.ready.connect(lambda r: answered(face, card, r))
    worker.finished.connect(lambda: host.service_workers.remove(worker) if worker in host.service_workers else None)
    worker.finished.connect(worker.deleteLater)
    worker.start()
    card.library_worker = worker
    return card


def answered(face, card, r):
    """Her answer on her card: the answer itself, the model's fold for each page it was asked about."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel, QSizePolicy
    try:
        if not r.get('ok'):
            card.set_text(say('could_not', why=str((r.get('error') or {}).get('message') or '')[:200]));return None
        found = r['result']
        card.set_text(say('asked', query=found.get('query') or ''))
        label = QLabel(answer_html(found));label.setObjectName('KasLibraryAnswer');label.setTextFormat(Qt.RichText);label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(False);label.setAccessibleName(say('ask_library'))
        places_ = list((found.get('places') or {}).get('places') or ())
        label.linkActivated.connect(lambda href: open_place(face.host, places_[int(href.split(':', 1)[1])]) if href.startswith('place:') else None)
        card.box.addWidget(label);card.library = found
        turns_ = [p.get('turn') for p in found.get('pages') or () if p.get('turn')]
        if turns_:
            from . import model_marks_qt
            from .model_marks_qt import Fold, kernel_of
            try:
                kernel, principal = kernel_of(face.host)
                for ident in turns_:card.box.addWidget(Fold.for_turn(face.host, ident, kernel, principal))
            except Exception:  # noqa: BLE001 - a fold that cannot be read never takes her card down
                card.box.addWidget(model_marks_qt.Fold(None, None, 'it could not be read'))
        return label
    except RuntimeError:  # her card left the column meanwhile
        return None


def open_place(host, place):
    """A place opened in the reference view: its library chosen, its page resolved (and drawn with its wires)."""
    bridge = getattr(host, 'ledger_bridge', None)
    if bridge is None or not place:return None
    tab = bridge.show_references()
    opener = getattr(tab, 'open_place', None)
    if opener is not None:opener(place)
    return tab


# ============================================================================================================== Read this table
def has_table(text, title=''):
    """Whether a page has a table the desk can cut (tables.find_tables, through the doorway; pure, no model)."""
    if not text:return False
    try:
        from . import page_marks, tables
        return bool(tables.find_tables(page_marks.Page(text, title)))
    except Exception:  # noqa: BLE001 - a page that cannot be cut has no table to read
        return False


def table_html(found):
    """library.table's answer as rich text: per table its state (a word and a shape), the columns with their roles and who
    named them, the rows as cut, and her lines (the closing line among them)."""
    quiet = _bt('QUIET', '#8a8a8a');line = _bt('LINE_STRONG', '#999999')
    tables_ = list((found or {}).get('tables') or ())
    if not tables_:return '<p>%s</p>' % esc(say('no_table'))
    out = ['<p><b>%s</b></p>' % esc(say('table_head'))]
    for t in tables_:
        state = t.get('state') or ''
        out.append('<p style="margin:6px 0 2px 0"><b>%s %s</b></p>' % (esc(STATE_MARK.get(state, '·')), esc(WORDS.get('state_' + state, state.lower()))))
        for said in t.get('said') or ():      # her lines first: the closing line is what the table is read for
            closing = said.startswith('rows close:') or said.startswith('the total closes:')
            out.append('<p style="margin:2px 0">%s</p>' % (('<b>%s</b>' % esc(said)) if closing else esc(said)))
        cols = t.get('columns') or ()
        head = ''.join('<th align="left" style="padding:6px 8px 0 8px">%s</th>' % esc(c.get('header') or 'C%s' % c.get('c')) for c in cols)
        roles = ''.join('<td style="padding:0 8px 3px 8px;border-bottom:1px solid %s;color:%s"><small>%s</small></td>' % (
            line, quiet, esc(say('role_by', role=str(c['role']).replace('_', ' '), by=WORDS.get('by_' + str(c.get('named_by') or 'NONE'), '')))
            if c.get('role') else esc(WORDS['by_NONE'])) for c in cols)
        body = ''
        for row in t.get('rows') or ():
            body += '<tr>' + ''.join('<td style="padding:1px 8px">%s</td>' % esc(v) for v in list(row.get('cells') or ())) + '</tr>'
        out.append('<table cellspacing="0"><tr>%s</tr><tr>%s</tr>%s</table>' % (head, roles, body))
    return ''.join(out)


# ============================================================================================================== cross-references
def wires_on_page(links, text, page_index=0):
    """{line: [her notes]} for the wires of one page of a file (library.links' answer for that file): beside each place that
    refers to another, 'refers to § 12(a) · current'; beside the first line of a place referred to, 'referred to by
    § 12(b), § 12(c)'. Lines are the page's own numbers (doorway's)."""
    from .library_service import page_places
    out = {}
    if not isinstance(links, dict):return out
    try:places_ = page_places(text or '')
    except Exception:  # noqa: BLE001 - a page whose places cannot be cut draws no wires
        places_ = []
    first = {p.get('label'): p.get('first') for p in places_ if p.get('label')}
    into = {}
    for f in links.get('files') or ():
        for link in f.get('links') or ():
            if int(link.get('page') or 0) != int(page_index or 0):continue
            state = WORDS.get('state_' + str(link.get('state')), str(link.get('state') or '').lower())
            out.setdefault(int(link.get('line') or 0), []).append(say('wire_out', target=link.get('target') or '', state=state))
            if link.get('found') and link.get('target') in first:into.setdefault(first[link['target']], []).append(link.get('source') or '')
    for n, sources in into.items():
        out.setdefault(int(n or 0), []).append(say('wire_in', sources=', '.join(dict.fromkeys(sources))))
    return out


def wires_count(links, page_index=0):
    return sum(1 for f in (links or {}).get('files') or () for link in f.get('links') or () if int(link.get('page') or 0) == int(page_index or 0))
