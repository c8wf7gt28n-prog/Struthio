"""The Field's reader: the real records of one workspace as FieldObjects and FieldLinks.

Everything is read through Kernel.dispatch with operations that already exist; nothing is written, no job is submitted,
no worker or child process is started (the operations used here read the workspace's own records only). An operation
that is absent or refuses leaves its kind out of the Field; it never stops the rest from being shown.

    material      intake.namespaces, intake.items, references.sources     the admitted source files
    tables        office.list, office.get                                 reviewed sheets and where each was read from
    calculations  documents.list, documents.get (with a derivation)       exact results and the cells they used
    pages         documents.list, documents.get (without one)             ordinary pages
    findings      investigation.list, investigation.sheet, .path          what was learned, and what is still unknown
    open          the unresolved claims of an investigation; conditions.list for conditions that no longer hold

There is no table of links in the program: each link is a field inside a record (a sheet's origin, a report's
derivation, a claim's path), so the links are derived here, kind by kind. A FieldObject's `target` is a small dict the
page's opener understands: {'kind': 'office' | 'document' | 'investigation' | 'pdf', 'id': …}.
"""
from .field_model import Field, FieldLink, FieldObject, STATE_CURRENT, STATE_HELD, STATE_OPEN, STATE_RECHECK

# Record states that mean "this still agrees with what it came from". Anything else on a derived record asks for a recheck.
AGREES = ('CURRENT', 'CURRENT_PDF_SOURCE', 'CURRENT_SOURCE', 'SUPPORTED', 'PASSED', 'NO_SOURCE', '')
UNAVAILABLE = 'unavailable'      # the record's own word for a source it has located but cannot read now: quiet ink, not an alarm


def _short(value, limit=12):
    text = str(value or '')
    return text if len(text) <= limit else text[:limit]


class Reader:
    def __init__(self, kernel, principal):
        self.kernel = kernel;self.principal = principal
        self.objects = [];self.links = [];self.refused = [];self.names = {}

    def call(self, operation, arguments=None):
        try:
            answer = self.kernel.dispatch(operation, arguments or {}, self.principal)
        except Exception as exc:  # noqa: BLE001 - a reader never takes the window down
            self.refused.append((operation, str(exc)));return None
        if not isinstance(answer, dict) or not answer.get('ok'):
            self.refused.append((operation, str((answer or {}).get('error') if isinstance(answer, dict) else answer)));return None
        return answer.get('result')

    def add(self, obj):
        self.objects.append(obj);self.names[obj.id] = obj.title;return obj

    def link(self, source, target, label='', stale=False):
        self.links.append(FieldLink(source, target, label, stale))

    # ---- one kind at a time ----------------------------------------------------------------------------------------
    def material(self):
        spaces = self.call('intake.namespaces') or {}
        for space in spaces.get('namespaces', ()):
            here = {}
            for row in (self.call('references.sources', {'namespace': space['id']}) or {}).get('sources', ()):
                here[row.get('item')] = row.get('state', '')
            for item in (self.call('intake.items', {'namespace': space['id']}) or {}).get('items', ()):
                readable = here.get(item['id'], '')
                facts = [str(item.get('admission', '')).lower()] if item.get('admission') else []
                if readable and readable not in AGREES:
                    facts.append(readable.lower().replace('_', ' '))
                self.add(FieldObject('intake:' + item['id'], 'source', item.get('name') or item['id'], 'admitted source',
                                     STATE_CURRENT if readable in AGREES else UNAVAILABLE, tuple(facts), space.get('name', ''),
                                     {'kind': 'pdf', 'namespace': space['id'], 'item': item['id'], 'sha256': item.get('sha256')}))

    def tables(self):
        for row in (self.call('office.list') or {}).get('documents', ()):
            sheet = self.call('office.get', {'id': row['id']}) or {}
            state = (sheet.get('source_state') or {}).get('state', '')
            pdf = (sheet.get('origin') or {}).get('pdf') or {}
            facts = []
            if pdf:facts.append('reviewed from page %d' % (int(pdf.get('page_index', 0)) + 1))
            if sheet.get('revision'):facts.append('revision ' + _short(sheet['revision']))
            ident = 'office:' + row['id']
            self.add(FieldObject(ident, 'sheet', row.get('title') or row['id'], 'reviewed sheet' if pdf else 'sheet',
                                 STATE_CURRENT if state in AGREES else STATE_RECHECK, tuple(facts),
                                 self.names.get('intake:' + str(pdf.get('item')), ''), {'kind': 'office', 'id': row['id']}))
            if pdf.get('item'):
                self.link('intake:' + pdf['item'], ident, 'page %d' % (int(pdf.get('page_index', 0)) + 1), state not in AGREES)

    def pages(self):
        for row in (self.call('documents.list') or {}).get('documents', ()):
            got = self.call('documents.get', {'id': row['id']}) or {}
            derivation = (got.get('document') or {}).get('derivation')
            state = (got.get('source_state') or {}).get('state', '')
            ident = 'document:' + row['id'];facts = [];cells = '';where = ''
            if derivation:
                cells = ', '.join(str(i.get('cell')) for i in derivation.get('inputs', ()) if i.get('cell'))
                if cells:facts.append('cells ' + cells)
                where = self.names.get('office:' + str(derivation.get('sheet')), '')
            if row.get('revision') is not None:facts.append('revision %s' % row['revision'])
            self.add(FieldObject(ident, 'calculation' if derivation else 'document', row.get('title') or row['id'],
                                 'exact result' if derivation else 'page',
                                 STATE_CURRENT if state in AGREES else STATE_RECHECK, tuple(facts), where, {'kind': 'document', 'id': row['id']}))
            if derivation and derivation.get('sheet'):
                self.link('office:' + derivation['sheet'], ident, ('cells ' + cells) if cells else '', state not in AGREES)
            elif derivation and (derivation.get('pdf') or {}).get('item'):
                self.link('intake:' + derivation['pdf']['item'], ident, 'source page', state not in AGREES)

    def findings(self):
        titles = []
        for row in (self.call('investigation.list') or {}).get('investigations', ()):
            sheet = self.call('investigation.sheet', {'id': row['id']}) or {}
            titles.append((row.get('question') or '', row.get('state') or ''))
            unresolved = list(sheet.get('unresolved', ()))
            for claim in list(sheet.get('learned', ())) + unresolved:
                ident = 'claim:' + claim['id'];unknown = claim in unresolved
                evidence = claim.get('evidence_state', '');review = claim.get('review', '')
                if unknown:state = STATE_OPEN
                elif evidence in AGREES and review in AGREES:state = STATE_CURRENT
                elif evidence in ('CONTRADICTED', 'REFUTED', 'CONFLICT'):state = STATE_HELD
                else:state = STATE_RECHECK
                words = ' · '.join(w.lower().replace('_', ' ') for w in (evidence, review) if w)
                self.add(FieldObject(ident, 'question' if unknown else 'finding', claim.get('text') or claim['id'],
                                     'from ' + (row.get('question') or 'an investigation'), state, (words,) if words else (),
                                     row.get('question', ''), {'kind': 'investigation', 'id': row['id']}))
                for step in (self.call('investigation.path', {'claim': claim['id']}) or {}).get('path', ()):
                    if step.get('kind') == 'SOURCE' and step.get('address'):
                        self.link(step['address'], ident, str(step.get('direction', '')).lower(), state == STATE_RECHECK)
                    else:
                        for word in str(step.get('program', '')).split():
                            if word.startswith('@'):
                                self.link(word[1:], ident, 'checked ' + str(step.get('outcome', '')).lower(), state == STATE_RECHECK)
        return titles

    def conditions(self):
        for row in (self.call('conditions.list') or {}).get('conditions', ()):
            state = str(row.get('state', ''))
            if state in AGREES or state in ('HOLDS', 'MET'):continue       # a condition that holds is not something to look at
            ident = 'condition:' + row['id']
            self.add(FieldObject(ident, 'question', str(row.get('result') or row.get('text') or 'A condition no longer holds'),
                                 'condition', STATE_RECHECK, (state.lower().replace('_', ' '),), '',
                                 {'kind': 'document', 'id': str(row.get('document', ''))}))
            if row.get('document'):self.link('document:' + str(row['document']), ident, 'condition', True)


def read_field(kernel, principal, title=''):
    """The Field of one workspace. Returns (Field, refused) where refused lists the operations that did not answer."""
    reader = Reader(kernel, principal)
    reader.material();reader.tables();reader.pages()
    investigations = reader.findings()
    reader.conditions()
    if not title and len(investigations) == 1:
        question, state = investigations[0]
        title = question + ('  ·  ' + state.lower().replace('_', ' ') if state else '')
    return Field(reader.objects, reader.links, title), reader.refused
