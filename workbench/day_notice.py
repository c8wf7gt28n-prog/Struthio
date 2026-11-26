"""She notices an old value in written words (Graphite 1.0, X1: the day of the paper's section 18).

The owner's paper, section 18: "You change a current value. The worksheet updates. Graphite recognizes the changed revision
and identifies calculations or reports that may depend on it. Kasandra notices that the previously written summary still
contains an older value. She proposes reviewing the report. You approve the operation."

What was there before this module: a saved change to a sheet sends the calculations that read it to RECHECK (the board and
NEXT STEPS say so), and field.ripple (field_ripple.py) can say, for a value set on a sheet, every page and finding whose words
carry a number that would move. Nothing joined the two after the save, so the summary that still said the old value was for
the owner to find. This module joins them, by the records, with no model:

    for each calculation the desk marks RECHECK:
      the cells it reads, at the values the sheet holds now      (documents.get: its derivation; office.get: the cells)
      field.ripple on that sheet with those values               (a read: the calculation worked again with its own recipe
                                                                  gives its new result; every page and finding whose words
                                                                  carry the old one is named)
      each Writer document in Files whose sentence carries the old result
                                                                 (read directly, office_bridge.read_odf: no LibreOffice runs)

and says it once in her column ("“Rail Demo summary” still says 3 W; worked from the saved sheet, the settled power is 3.6 W"),
with one NEXT STEP, Update, that asks for the plan in the owner's words of the desk (K4: recheck the quantity, update the page,
update the report). The press only asks for the plan: it is offered in ACTIVE WORK and nothing changes until the owner
authorises it, step by step, as every plan of hers.

    notices(read)    -> [{'key', 'calculation', 'quantity', 'old', 'new', 'pages': [(title, says)], 'documents': [(title, says)],
                          'objective'}]       read: callable(operation, arguments) -> result or None (the Kernel, read-only)
    words(notice)    -> her sentence (a fixed template, registered with mind_words)

No floating point: values are compared as the records' decimal text, through field_doubt.measure (exact).
"""
from __future__ import annotations

import hashlib
import re

WORDS = {
    'noticed': '“{page}” still says {old}; worked from the saved sheet, the {quantity} is {new}. I can recheck it and update {what}: '
               'NEXT STEPS, Update. Nothing changes until you authorise it.',
    'button': 'Update',
    'object': '“{page}” still says {old}',
    'tip': 'Asks for the plan: recheck the {quantity}, then update {what}. It is offered in ACTIVE WORK; nothing changes until you authorise it.',
    'and': ' and ',
}
try:
    from . import mind_words
    mind_words.register('day_notice', WORDS, kind='sentence',
                        numbers={'noticed': {'old': 'the calculation page as it stands (documents.get)', 'new': 'field.ripple: the calculation worked again'},
                                 'object': {'old': 'the calculation page as it stands (documents.get)'}})
except Exception:  # noqa: BLE001 - the words stand without the register
    pass

MOST_CALCULATIONS = 4        # calculations followed in one look, at most
MOST_DOCUMENTS = 12          # Writer documents in Files read in one look, at most
MOST_PAGES = 40              # Graphite's own pages read in one look, at most


def _plain(value):
    return ' '.join(str(value or '').split())


def _result_words(calc):
    """A calculation's result as its page says it ("3 W"), and its title without it."""
    title = _plain(calc.get('title'))
    name, _, said = title.partition(' · ')
    return name.strip(), said.strip()


def _quantity(name, sheet_title):
    try:
        from .objective_plan import _quantity as q
        return q(name, sheet_title)
    except Exception:  # noqa: BLE001
        return name


def _same_quantity(text, old):
    """Whether these words carry the quantity `old` ("3 W"): the same kind of quantity and the same exact number."""
    from .field_doubt import measure, said_quantities, _same
    parts = old.split()
    if len(parts) < 2:return False
    base, scaled = measure(parts[0], ' '.join(parts[1:]))
    text = re.sub(r'(?<=[A-Za-zΩ°%])[:;](?=\s|$)', ' ', str(text or ''))      # "which is 3 W: inside ..." (the reader takes "W:" for no unit)
    return any(b == base and _same(s, scaled) for _, _, b, s in said_quantities(text))


def _writer_documents(read, old, most=MOST_DOCUMENTS):
    """Writer documents in Files with a sentence that carries `old`: [(title, the sentence)]. Read directly (no LibreOffice)."""
    out = []
    try:
        from . import office_bridge
        from .objective_plan import Desk
        desk = read('__desk__', None)
        things = [t for t in (desk.things if isinstance(desk, Desk) else []) if t.kind == 'document' and str(t.title).lower().endswith('.odt')]
    except Exception:  # noqa: BLE001
        return out
    for thing in things[:most]:
        try:
            path = read('__path__', thing.id)
            doc = office_bridge.read_odf(path) if path else {}
        except Exception:  # noqa: BLE001
            continue
        for paragraph in doc.get('paragraphs') or ():
            hit = next((s for s in office_bridge.sentences(paragraph) if _same_quantity(s, old)), None)
            if hit:
                out.append((thing.title, hit));break
    return out


def _pages(read, desk, old, most=MOST_PAGES):
    """Graphite's own pages on the desk with a sentence that carries `old`, read block by block: [(title, the sentence)].
    (field.ripple reads a page's plain line, which holds its title; the sentences are in its blocks.)"""
    out = []
    for row in [r for r in desk.get('objects') or () if r.get('kind') == 'document'][:most]:
        ident = str(row['id']).split(':', 1)[1] if ':' in str(row['id']) else row['id']
        doc = (read('documents.get', {'id': ident}) or {}).get('document') or {}
        for block in doc.get('blocks') or ():
            text = _plain((block or {}).get('text'))
            hit = next((s for s in _sentences(text) if _same_quantity(s, old)), None) if text else None
            if hit:
                out.append((_plain(doc.get('title') or row.get('title')), hit));break
    return out


def _sentences(text):
    try:
        from .office_bridge import sentences
        return sentences(text)
    except Exception:  # noqa: BLE001
        return [text]


def notices(read):
    """What still carries an old value, for each calculation the desk marks RECHECK (see the module's words)."""
    desk = read('field.read', {}) or {}
    waiting = [row for row in desk.get('objects') or () if row.get('kind') == 'calculation' and str(row.get('state')) == 'recheck']
    objects = {row['id']: row for row in desk.get('objects') or ()}
    out = []
    for calc in waiting[:MOST_CALCULATIONS]:
        ident = str(calc['id']).split(':', 1)[1] if ':' in str(calc['id']) else calc['id']
        doc = (read('documents.get', {'id': ident}) or {}).get('document') or {}
        derivation = doc.get('derivation') or {}
        sheet = derivation.get('sheet')
        cells_read = sorted({str(i.get('cell')) for i in derivation.get('inputs') or () if i.get('cell')})
        if not sheet or not cells_read:continue
        record = read('office.get', {'id': sheet}) or {}
        cells = ((record.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
        setting = {c: _plain((cells.get(c) or {}).get('value')) for c in cells_read if _plain((cells.get(c) or {}).get('value'))}
        if not setting:continue
        rippled = read('field.ripple', {'id': 'office:' + str(sheet), 'set': setting}) or {}
        rows = rippled.get('rows') or ()
        mine = next((r for r in rows if r.get('way') == 'reads it' and r.get('id') == calc['id'] and r.get('moves') == 'yes'), None)
        if mine is None:continue
        old, new = _plain(mine.get('says_now')), _plain(mine.get('would_be'))
        pages = [(_plain(r['title']), _plain(r.get('says_now'))) for r in rows if r.get('way') == 'says it' and r.get('kind') == 'page' and old in _plain(r.get('says_now')).split('; ')]
        pages += [p for p in _pages(read, desk, old) if p[0] not in {t for t, _ in pages}]
        documents = _writer_documents(read, old)
        if not pages and not documents:continue
        name, _ = _result_words(calc)
        sheet_title = _plain((objects.get('office:' + str(sheet)) or {}).get('title') or (record.get('document') or {}).get('title'))
        quantity = _quantity(name, sheet_title)
        clauses = ['recheck the %s' % quantity] + ['update the %s' % _named(title, 'page') for title, _ in pages[:2]] + ['update the %s' % _named(title, 'report') for title, _ in documents[:1]]
        objective = ', '.join(clauses[:-1]) + ' and ' + clauses[-1] if len(clauses) > 1 else clauses[0]
        key = hashlib.sha256(('%s|%s|%s|%s' % (calc['id'], old, new, sorted(setting.items()))).encode()).hexdigest()[:16]
        out.append({'key': key, 'calculation': calc['id'], 'quantity': quantity, 'old': old, 'new': new, 'pages': pages, 'documents': documents,
                    'objective': objective})
    return out


def _named(title, kind):
    """A thing's name as the owner would say it, its kind word last ("Rail Demo summary page", "Rail Demo summary report"):
    the desk's planner (objective_plan.Desk.find) takes the title's words and the kind word, so a page and a report of the
    same name are told apart without quotes."""
    name = _plain(title)
    stem, dot, ext = name.rpartition('.')
    if dot and stem and ext.lower() in ('odt', 'ods', 'docx', 'xlsx', 'txt', 'md', 'pdf'):name = stem
    return name if name.lower().split()[-1:] == [kind] else '%s %s' % (name, kind)


def what(notice):
    names = ['“%s”' % t for t, _ in notice['pages'][:2]] + ['the report “%s”' % t for t, _ in notice['documents'][:1]]
    return WORDS['and'].join(names) if len(names) < 3 else ', '.join(names[:-1]) + WORDS['and'] + names[-1]


def first(notice):
    return (notice['pages'] or notice['documents'])[0][0]


def words(notice):
    return WORDS['noticed'].format(page=first(notice), old=notice['old'], quantity=notice['quantity'], new=notice['new'], what=what(notice))


def step(notice):
    """Her NEXT STEP for a notice: one press, which asks for the plan in the desk's words (K4)."""
    obj = WORDS['object'].format(page=first(notice), old=notice['old'])
    return {'words': '%s · %s' % (WORDS['button'], obj), 'verb': WORDS['button'], 'object': obj, 'kind': 'notice', 'title': obj,
            'objective': notice['objective'], 'key': notice['key'],
            'tip': WORDS['tip'].format(quantity=notice['quantity'], what=what(notice))}


def reader(kernel, principal):
    """read(operation, arguments) for notices(): the Kernel's reads, the desk of K4 and a Files path."""
    def read(operation, arguments):
        if operation == '__desk__':
            from .objective_plan import Desk
            return Desk.read(kernel, principal)
        if operation == '__path__':
            from . import files_service
            return files_service.resolve(kernel, arguments, must_exist=True)
        try:
            got = kernel.dispatch(operation, arguments or {}, principal)
        except Exception:  # noqa: BLE001 - a record that cannot be read is left out
            return None
        return got.get('result') if got.get('ok') else None
    return read
