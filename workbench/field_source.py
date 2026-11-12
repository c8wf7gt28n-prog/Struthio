"""The Field's reader: the real records of one workspace as FieldObjects and FieldLinks.

Everything is read through Kernel.dispatch with operations that already exist and that are reads which refresh a view
(activity.OBSERVER_OPERATIONS), so showing the Field adds nothing to the owner's timeline. Nothing is written, no job is
submitted, no worker or child process is started. An operation that refuses leaves its kind out of the Field; a single
record that cannot be read is drawn as "not read", never as current, and is not asked for again until the owner looks again.

    material      intake.namespaces, intake.items                         the files admitted to this workspace's collections
    tables        office.list, office.get                                 sheets and written documents, and where each came from
    calculations  documents.list, documents.get (with a derivation)       exact results and the cells they used
    pages         documents.list, documents.get (without one)             ordinary pages
    findings      investigation.list, investigation.sheet, .path          what was learned, what must be rechecked, what is unknown
    totals        conditions.list                                         a total bound to a page's words that no longer holds
    work          jobs.list                                               jobs that are not finished: running, waiting, failed

There is no table of links in the program: each link is a field inside a record (a sheet's origin, a report's
derivation, a claim's path), so the links are derived here, kind by kind. A FieldObject's `target` is a small dict the
page's opener understands: {'kind': 'office' | 'document' | 'investigation' | 'pdf' | 'job', 'id': …}.

States follow the records' own words. A derived record asks for a recheck only when its record says its source changed
(STALE_…, …_REVIEW_REQUIRED, NEEDS_REVIEW, a path step that no longer counts); "unavailable" is the record saying it
cannot reach its source; everything else agrees. A plain page has no source and so no state.

Sheets live in the owner's profile, not in a workspace, so a sheet is shown only when it belongs here: it was read from
a source admitted here, its original lies under this workspace, a page or finding here refers to it, or this workspace
is the profile's own Office.

Every object carries its staC line (`stac`): the read-only pipeline that reads that object through the same Kernel, exact and
ready for the writing line. staC is Graphite's command language, said "Stacy"; in the Field it is Stacy's rail that shows it.

The network face (read_network) is one look through network.observe, the observer operation the Log's Network stream
uses: this computer's interfaces with their rates, the programs that hold connections, and the places they reach or the
ports they wait on. It reads /proc and /sys only, starts no capture, and nothing it shows leaves the computer.
"""
from pathlib import Path

from .field_model import Field, FieldLink, FieldObject, STATE_CURRENT, STATE_HELD, STATE_OPEN, STATE_RECHECK

UNAVAILABLE = 'unavailable'      # the record cannot reach its source now: quiet ink, not an alarm
NOT_READ = 'not read'            # the record itself could not be read this time
# Each record costs one Kernel read on the window's own thread, so a face reads at most this many of a kind (the newest
# first where the list says when) and the Field says how many it left out. The owner's desk stays quick in a large workspace.
CEILING = 60
PAGES_CEILING = 300              # pages are cheap to read, and the older ones hold the calculations: they are not the first to go
ELSEWHERE = 'elsewhere'          # a sheet of the owner's Office whose source lives in another workspace: quiet, not an alarm
REFUTED = 'refuted'              # a finding the evidence speaks against: settled, and never drawn with the mark of one that stands
CHECK_WORDS = {'PASSED': 'check passed', 'CHECK_FAILED': 'did not hold', 'FAILED': 'did not hold', 'STALE': 'check is out of date',
               'NOT_RUN': 'check not run'}
CLAIMS_CEILING = 40              # per investigation
PAGE = 100                       # rows a list operation returns at most in one answer


def source_word(state):
    """A record's source state in the Field's three words: '' (agrees), STATE_RECHECK (its source changed), UNAVAILABLE."""
    word = str(state or '').upper()
    if word.endswith('UNAVAILABLE'):return UNAVAILABLE
    if word.startswith('STALE') or word.startswith('RECHECK') or word.endswith('REVIEW_REQUIRED') or word in ('CHANGED', 'NEEDS_REVIEW'):
        return STATE_RECHECK
    return ''


def stac_json(**arguments):
    """Operation arguments as staC writes them: compact JSON, keys in order."""
    import json
    return json.dumps(arguments, sort_keys=True, separators=(',', ':'))


def words(code):
    """A record's code word as people read it: CHECK_FAILED becomes 'check failed'."""
    return str(code or '').lower().replace('_', ' ').strip()


class Reader:
    def __init__(self, kernel, principal, skip=()):
        self.kernel = kernel;self.principal = principal
        self.objects = [];self.links = [];self.names = {}
        self.refused = []            # (operation, reason): a whole list that did not answer
        self.unread = []             # ids of single records that could not be read this time
        self.items_here = set()      # every file ever brought into this workspace's collections, whatever its admission
        self.elsewhere = 0           # sheets of the owner's Office that are not shown here because their home is not this workspace
        self.skip = set(skip)        # ids that could not be read last time: not asked again until the owner looks again
        self.left_out = []

    def call(self, operation, arguments=None, record=None):
        """One Kernel read. `record` names the single record being read, so a refusal is counted against it and not the kind."""
        if record is not None and record in self.skip:
            self.unread.append(record);return None
        try:
            answer = self.kernel.dispatch(operation, arguments or {}, self.principal)
        except Exception as exc:  # noqa: BLE001 - a reader never takes the window down
            answer = {'ok': False, 'error': str(exc)}
        if not isinstance(answer, dict) or not answer.get('ok'):
            if record is not None:self.unread.append(record)
            else:self.refused.append((operation, str((answer or {}).get('error') if isinstance(answer, dict) else answer)))
            return None
        return answer.get('result')

    def pages(self, operation, key, arguments=None):
        """Every row of a paged list: asked a page at a time until a short page comes back."""
        rows = [];offset = 0
        while offset < 20000:
            answer = self.call(operation, dict(arguments or {}, limit=PAGE, offset=offset))
            if answer is None:break
            page = list(answer.get(key, ()));rows.extend(page);offset += PAGE
            if len(page) < PAGE:break
        return rows

    def newest(self, rows, what, ceiling=CEILING):
        """At most `ceiling` rows, the most recently changed first when the rows say when; the rest is counted, not hidden."""
        rows = list(rows)
        if rows and all(isinstance(row, dict) and row.get('updated') is not None for row in rows):
            rows.sort(key=lambda row: row['updated'], reverse=True)
        if len(rows) > ceiling:
            self.left_out.append('%d more %s' % (len(rows) - ceiling, what));rows = rows[:ceiling]
        return rows

    def add(self, obj):
        self.objects.append(obj);self.names[obj.id] = obj.title;return obj

    def link(self, source, target, label='', stale=False):
        self.links.append(FieldLink(source, target, label, stale))

    # ---- one kind at a time ----------------------------------------------------------------------------------------
    def material(self):
        """What was brought in and admitted. A file still waiting for the owner's review says so; a rejected or revoked one is
        not material."""
        spaces = self.call('intake.namespaces') or {}
        for space in spaces.get('namespaces', ()):
            items = self.pages('intake.items', 'items', {'namespace': space['id']})
            self.items_here |= {'intake:' + str(item['id']) for item in items}
            items = [item for item in items if str(item.get('admission', '')).upper() not in ('REJECTED', 'REVOKED')]
            for item in self.newest(items, 'sources'):
                admission = str(item.get('admission', '')).upper()
                if admission == 'ACCEPTED':state, role = STATE_CURRENT, 'admitted source'
                elif admission == 'HELD':state, role = STATE_HELD, 'held at review'
                else:state, role = 'waiting', 'waiting for your review'
                self.add(FieldObject('intake:' + item['id'], 'source', item.get('name') or item['id'], role, state, (), space.get('name', ''),
                                     {'kind': 'pdf', 'namespace': space['id'], 'item': item['id'], 'sha256': item.get('sha256')},
                                     stac='intake.items %s | pick items | where id=%s | select name,admission,bytes' % (stac_json(namespace=space['id']), item['id'])))

    def tables(self):
        """Sheets and written documents. The sheets are read first and kept aside: which of them belong to this workspace is
        only known once the pages and findings that refer to them have been read (settle_tables)."""
        self.sheets = {}
        for row in self.newest((self.call('office.list') or {}).get('documents', ()), 'sheets'):
            ident = 'office:' + row['id']
            sheet = self.call('office.get', {'id': row['id']}, record=ident)
            self.sheets[ident] = (row, sheet)
            self.names[ident] = row.get('title') or row['id']

    def settle_tables(self):
        root = Path(getattr(self.kernel, 'root', '.')).resolve()
        try:
            from .locations import concern_home
            office = (concern_home() / 'Office').resolve() == root
        except Exception:  # noqa: BLE001
            office = False
        referred = {link.source for link in self.links} | {link.target for link in self.links}
        here = {obj.id for obj in self.objects}
        for ident, (row, sheet) in self.sheets.items():
            origin = (sheet or {}).get('origin') or {};pdf = origin.get('pdf') or {};source = origin.get('source') or {}
            under = False
            if source.get('path'):
                try:under = Path(source['path']).resolve().is_relative_to(root)
                except (OSError, ValueError):under = False
            pdf_here = bool(pdf.get('item')) and 'intake:' + str(pdf['item']) in self.items_here      # admitted here once, even if since withdrawn
            foreign = bool(pdf.get('item')) and not pdf_here            # read from a source that another workspace holds
            belongs = ident in referred or under or pdf_here or office
            if not belongs:
                self.elsewhere += 1
                self.links = [link for link in self.links if ident not in (link.source, link.target)];continue
            written = str(row.get('kind', 'table')) == 'document'
            target = {'kind': 'office', 'id': row['id']}
            code = 'office.get %s | select source_state.state%s' % (stac_json(id=row['id']), ',origin.pdf.page_index' if pdf else '')
            if sheet is None:
                self.add(FieldObject(ident, 'document' if written else 'sheet', row.get('title') or row['id'], 'could not be read', NOT_READ, (), '', target,
                                     'WRITING' if written else '', code));continue
            state = source_word((sheet.get('source_state') or {}).get('state'))
            facts = []
            if foreign:                  # the Office cannot see another workspace's sources: that is not a change, so not an alarm
                state = ELSEWHERE;facts.append('its source is in another workspace')
            elif pdf and 'intake:' + str(pdf['item']) not in here and state == STATE_RECHECK:
                facts.append('its source was withdrawn from the material')
            if pdf:facts.append('reviewed from page %d' % (int(pdf.get('page_index', 0)) + 1))
            elif source.get('path'):facts.append('from ' + Path(str(source['path'])).name)
            if row.get('version') is not None:facts.append('version %s' % row['version'])
            if state == UNAVAILABLE:facts.append('its source cannot be reached')
            self.add(FieldObject(ident, 'document' if written else 'sheet', row.get('title') or row['id'],
                                 'written document' if written else ('reviewed sheet' if pdf else 'sheet'),
                                 state or STATE_CURRENT, tuple(facts), self.names.get('intake:' + str(pdf.get('item')), ''), target,
                                 'WRITING' if written else '', code))
            if pdf.get('item') and 'intake:' + str(pdf['item']) in here:
                self.link('intake:' + pdf['item'], ident, 'page %d' % (int(pdf.get('page_index', 0)) + 1), state == STATE_RECHECK)

    def pages_and_calculations(self):
        for row in self.newest(self.pages('documents.list', 'documents'), 'pages', PAGES_CEILING):
            ident = 'document:' + row['id'];target = {'kind': 'document', 'id': row['id']}
            got = self.call('documents.get', {'id': row['id']}, record=ident)
            page_code = 'documents.list | pick documents | where id=%s | select title,revision,words' % row['id']
            if got is None:
                self.add(FieldObject(ident, 'document', row.get('title') or row['id'], 'could not be read', NOT_READ, (), '', target, stac=page_code));continue
            derivation = (got.get('document') or {}).get('derivation')
            facts = [];cells = '';where = ''
            if row.get('revision') is not None:facts.append('revision %s' % row['revision'])
            if not derivation:       # a plain page comes from nothing, so it has nothing to agree with: no state
                self.add(FieldObject(ident, 'document', row.get('title') or row['id'], 'page', '', tuple(facts), '', target, stac=page_code));continue
            state = source_word((got.get('source_state') or {}).get('state'))
            cells = ', '.join(str(i.get('cell')) for i in derivation.get('inputs', ()) if i.get('cell'))
            if cells:facts.insert(0, 'cells ' + cells)
            if state == UNAVAILABLE:facts.append('its sheet cannot be reached')
            where = self.names.get('office:' + str(derivation.get('sheet')), '')
            self.add(FieldObject(ident, 'calculation', row.get('title') or row['id'], 'exact result', state or STATE_CURRENT, tuple(facts), where, target,
                                 stac='documents.get %s | pick document.derivation.inputs | select symbol,parameter,cell,conditions' % stac_json(id=row['id'])))
            if derivation.get('sheet'):
                self.link('office:' + derivation['sheet'], ident, ('cells ' + cells) if cells else '', state == STATE_RECHECK)
            elif (derivation.get('pdf') or {}).get('item'):
                self.link('intake:' + derivation['pdf']['item'], ident, 'source page', state == STATE_RECHECK)

    def findings(self):
        """Each claim once. A question is a question; a finding stays a finding whatever its state: its source changed (recheck),
        its evidence conflicts (held), it has no evidence yet (open), or it stands."""
        titles = []
        rows = self.newest((self.call('investigation.list') or {}).get('investigations', ()), 'investigations', 6)
        for row in rows:
            sheet = self.call('investigation.sheet', {'id': row['id']}, record='investigation:' + row['id'])
            titles.append((row.get('question') or '', row.get('state') or ''))
            if sheet is None:            # its findings cannot be read: said in their place, not left out
                self.add(FieldObject('investigation:' + row['id'], 'finding', row.get('question') or 'An investigation', 'its findings could not be read',
                                     NOT_READ, (), '', {'kind': 'investigation', 'id': row['id']}, 'INVESTIGATION',
                                     'investigation.list | pick investigations | where id=%s | select question,state,reason' % row['id']));continue
            claims = {}
            for claim in list(sheet.get('unresolved') or ()) + list(sheet.get('learned') or ()):      # what waits is read first
                claims.setdefault(claim['id'], claim)
            for claim in self.newest(claims.values(), 'findings', CLAIMS_CEILING):
                ident = 'claim:' + claim['id'];question = str(claim.get('role', '')).upper() == 'QUESTION'
                evidence = str(claim.get('evidence_state', '')).upper();review = str(claim.get('review', '')).upper()
                answer = self.call('investigation.path', {'claim': claim['id']}, record=ident)
                path = (answer or {}).get('path') or ()
                changed = review == 'NEEDS_REVIEW' or any(step.get('counts') is False or source_word(step.get('source_state')) == STATE_RECHECK
                                                          or str(step.get('outcome', '')).upper() == 'STALE' for step in path)
                if question:state = STATE_OPEN
                elif answer is None:state = NOT_READ          # what it stands on could not be read: it is not drawn as standing
                elif changed:state = STATE_RECHECK
                elif evidence == 'CONFLICT':state = STATE_HELD
                elif evidence == 'REFUTED':state = REFUTED
                elif evidence == 'SUPPORTED':state = STATE_CURRENT
                else:state = STATE_OPEN
                facts = [w for w in (words(evidence) if evidence not in ('REFUTED',) else 'the evidence speaks against it',
                                     'needs your review' if review == 'NEEDS_REVIEW' else '') if w and w != 'unknown']
                if not question and evidence == 'UNKNOWN':facts.append('no evidence yet')
                if answer is None and not question:facts = ['what it stands on could not be read']
                self.add(FieldObject(ident, 'question' if question else 'finding', claim.get('text') or claim['id'],
                                     'from ' + (row.get('question') or 'an investigation'), state, (' · '.join(facts),) if facts else (),
                                     row.get('question', ''), {'kind': 'investigation', 'id': row['id']},
                                     stac=('investigation.sheet %s | pick unresolved | select text,evidence_state,review' % stac_json(id=row['id'])) if question else
                                          ('investigation.path %s | pick path | select kind,address,direction,source_state,outcome' % stac_json(claim=claim['id']))))
                for step in path:
                    if step.get('kind') == 'SOURCE' and step.get('address'):
                        stale = step.get('counts') is False or source_word(step.get('source_state')) == STATE_RECHECK
                        self.link(str(step['address']).lstrip('@'), ident, words(step.get('direction')), stale)
                    elif step.get('kind') == 'CHECK':
                        outcome = str(step.get('outcome', '')).upper()
                        addresses = list(step.get('inputs') or ()) or [w[1:] for w in str(step.get('program', '')).split() if w.startswith('@')]
                        for address in addresses:      # a check that no longer counts (its sheet changed) is a wire to recheck, whatever it once said
                            self.link(str(address).lstrip('@'), ident, CHECK_WORDS.get(outcome, words(outcome) or 'check'),
                                      outcome == 'STALE' or step.get('counts') is False)
        return titles

    def totals(self):
        """A total bound to a page's words that no longer holds (a condition card). One that holds is not something to look at."""
        for row in (self.call('conditions.list') or {}).get('conditions', ()):
            state = str(row.get('state', '')).upper()
            if state in ('', 'CURRENT', 'HOLDS', 'MET', 'OK'):continue
            ident = 'condition:' + row['id'];result = row.get('result')
            title = (result.get('text') if isinstance(result, dict) else str(result or '')) or 'A total on a page'
            facts = [str(row['reason'])] if row.get('reason') else [words(state)]
            self.add(FieldObject(ident, 'condition', title, 'a total bound to the words of a page', STATE_RECHECK, tuple(facts),
                                 self.names.get('document:' + str(row.get('document')), ''), {'kind': 'document', 'id': str(row.get('document', ''))},
                                 stac='conditions.list | pick conditions | where id=%s | select state,reason' % row['id']))
            if row.get('document'):self.link('document:' + str(row['document']), ident, 'its words changed', True)

    def jobs(self):
        """Work that is not finished. A finished job is history (Activity has it); one that runs, waits or failed is the owner's."""
        rows = self.call('jobs.list') or []
        rows = rows if isinstance(rows, list) else rows.get('jobs', ())
        unfinished = [row for row in rows if str(row.get('state', '')) not in ('Completed', 'Cancelled', 'Done', '')]
        for row in self.newest(unfinished, 'jobs', 20):
            state = str(row.get('state', ''));word = state.lower()
            if word.startswith('waiting') or word == 'queued':word = 'waiting'
            facts = [state] if state.lower() != word else []
            goal = str(row.get('goal') or '');tool = str(row.get('tool') or '')
            if ' ' not in goal:          # no sentence of the owner's: say the tool in the Timeline's own words, not its internal name
                try:
                    from .tail_words import WORDS as SAID
                except Exception:  # noqa: BLE001
                    SAID = {}
                goal = SAID.get(tool) or SAID.get(tool.rsplit('.', 1)[0]) or (words(tool.replace('.', ' ')).capitalize() if tool else 'A job')
            self.add(FieldObject('job:' + row['id'], 'job', goal, 'work Graphite holds',
                                 word, tuple(facts), '', {'kind': 'job', 'id': row['id']}, stac='jobs | where id=%s | select tool,state,goal' % row['id']))


def _left_out(reader):
    """What the ceilings kept back, one count per kind: '440 more sheets, 90 more findings'."""
    totals = {}
    for entry in reader.left_out:
        count, _, what = entry.partition(' more ')
        totals[what] = totals.get(what, 0) + int(count)
    return ('not shown: ' + ', '.join('%d more %s' % (count, what) for what, count in totals.items())) if totals else ''


def problems(reader):
    """What could not be read, in the owner's words (never an operation name): one sentence for the status line, or ''."""
    kinds = {'intake.namespaces': 'the sources', 'intake.items': 'the sources', 'office.list': 'the sheets', 'documents.list': 'the pages',
             'investigation.list': 'the findings', 'conditions.list': 'the totals', 'jobs.list': 'the jobs', 'network.observe': 'the network'}
    whole = []
    for operation, _ in reader.refused:
        name = kinds.get(operation, 'some records')
        if name not in whole:whole.append(name)
    parts = []
    if whole:parts.append(', '.join(whole) + ' could not be read')
    drawn = {obj.id for obj in reader.objects if obj.state == NOT_READ}      # a record of another workspace is not this Field's to report
    if drawn:
        parts.append('%d record%s could not be read' % (len(drawn), '' if len(drawn) == 1 else 's'))
    return ' · '.join(parts)


def _rate(bits):
    """Bits per second in the Log's own words; '—' before the second look, when there is no rate yet."""
    if bits is None:return '—'
    bits = float(bits)
    if bits < 1000:return '%d bit/s' % bits
    if bits < 1000000:return '%.1f kbit/s' % (bits / 1000)
    return '%.2f Mbit/s' % (bits / 1000000)


def read_network(kernel, principal):
    """The network face of the Field. Returns (Field, reader)."""
    reader = Reader(kernel, principal)
    seen = reader.call('network.observe') or {}
    for row in seen.get('interfaces', ()):
        name = str(row.get('name', '?'));up = bool(row.get('up', True))
        reader.add(FieldObject('interface:' + name, 'interface', name, 'network interface of this computer', 'up' if up else 'down',
                               ('in %s' % _rate(row.get('rx_bps')), 'out %s' % _rate(row.get('tx_bps'))), '', {'kind': 'network', 'filter': ''},
                               stac='network.observe | pick interfaces | where name=%s | select name,up,rx_bps,tx_bps' % name))
    programs = {};places = {}
    for row in seen.get('connections', ()):
        program = str(row.get('process') or 'a program not named')
        key = 'program:' + program
        if key not in programs:programs[key] = {'name': program, 'user': row.get('user'), 'count': 0}
        programs[key]['count'] += 1
        waiting = str(row.get('state', '')).upper() == 'LISTEN'
        if waiting:
            ident = 'port:%s:%s' % (row.get('proto'), row.get('lport'))
            place = places.setdefault(ident, {'title': 'port %s' % row.get('lport'), 'state': 'listening', 'role': 'waits for connections here',
                                              'facts': [], 'filter': 'port %s' % row.get('lport')})
            fact = '%s on %s' % (row.get('proto'), row.get('local'))
        else:
            ident = 'place:%s' % row.get('remote')
            place = places.setdefault(ident, {'title': str(row.get('remote')), 'state': 'connected', 'role': 'reached from this computer',
                                              'facts': [], 'filter': 'host %s' % row.get('remote')})
            word = words(row.get('state'))
            if word and word != 'established':place['state'] = word
            fact = '%s %s' % (row.get('rservice') or row.get('proto'), row.get('rport'))
        if fact not in place['facts']:place['facts'].append(fact)
        place.setdefault('links', set()).add((key, str(row.get('proto') or '')))
    if len(places) > CEILING:        # a busy machine: the busiest places stay, the rest is counted
        reader.left_out.append('%d more places' % (len(places) - CEILING))
        places = dict(sorted(places.items(), key=lambda kv: -len(kv[1].get('links', ())))[:CEILING])
    for key, program in programs.items():
        facts = ['%d connection%s' % (program['count'], '' if program['count'] == 1 else 's')]
        if program.get('user'):facts.append('user %s' % program['user'])
        named = program['name'] != 'a program not named' and ' ' not in program['name']
        reader.add(FieldObject(key, 'program', program['name'], 'program on this computer', 'up', tuple(facts), '',
                               {'kind': 'network', 'filter': program['name'] if program['name'] != 'a program not named' else ''},
                               stac=('network.observe | pick connections | where process=%s | select remote,rport,state' % program['name']) if named else
                                    'network.observe | pick connections | select process,remote,rport,state'))
    for ident, place in places.items():
        listening = place['state'] == 'listening'
        reader.add(FieldObject(ident, 'endpoint', place['title'], place['role'], place['state'], tuple(place['facts'][:3]), '',
                               {'kind': 'network', 'filter': place['filter']}, 'PORT' if listening else 'PLACE',
                               ('network.observe | pick connections | where lport=%s | select process,local,state' % ident.rsplit(':', 1)[-1]) if listening else
                               ('network.observe | pick connections | where remote=%s | select process,rport,state' % place['title'])))
        for key, proto in sorted(place.get('links', ())):
            reader.link(key, ident, proto)
    capture = (seen.get('capture') or {}).get('state', '')
    title = 'This computer'
    if capture:title += '  ·  capture ' + words(capture)
    return Field(reader.objects, reader.links, title, verbs=('held by', 'reaches'), note=_left_out(reader)), reader


def read_field(kernel, principal, title='', skip=()):
    """The Field of one workspace. Returns (Field, reader); reader.refused and reader.unread say what did not answer."""
    reader = Reader(kernel, principal, skip)
    reader.material();reader.tables();reader.pages_and_calculations()
    investigations = reader.findings()
    reader.settle_tables();reader.totals();reader.jobs()
    if not title and len(investigations) == 1:
        question, state = investigations[0]
        title = question + ('  ·  ' + words(state) if state else '')
    aside = ''
    if reader.elsewhere:
        aside = '%d sheet%s of your Office %s not shown here' % (reader.elsewhere, '' if reader.elsewhere == 1 else 's', 'is' if reader.elsewhere == 1 else 'are')
    return Field(reader.objects, reader.links, title, note=_left_out(reader), aside=aside), reader


# ---- the programs face: every program and room Graphite can open, as a shelf --------------------------------------------------
# The columns are set by hand and do not move, so the hands learn where a thing is. A program the shelf does not know yet
# (a new one) takes the last column. The names are the programs list's own (programs_qt.PLAIN).
SHELF = (('WORK', ('projects', 'inquiries', 'documents', 'office', 'files', 'investigations', 'agenda')),
         ('THINK', ('calculate', 'laboratory', 'methods', 'knowledge', 'references', 'memory', 'activity')),
         ('MAKE', ('blender', 'freecad', 'godot', 'inkscape', 'media', 'print', 'mail')),
         ('BUILD', ('kicad', 'kibot', 'spice', 'yosys', 'fpga', 'hdl')),
         ('MOVE', ('transfer', 'delivery', 'cartridge')),
         ('SET UP', ('brain', 'settings', 'tools')))
PROGRAMS_READ = 'ledger.explore {"kind":"INSTRUMENT"} | pick instruments'


def read_programs(kernel, principal, open_classes=()):
    """The programs face of the Field: one sheet for each program and room, from the same read the programs list uses
    (ledger.explore). Opening one is the programs list's own opening; nothing runs by being shown. Returns (Field, reader)."""
    from .programs_qt import PLAIN
    reader = Reader(kernel, principal)
    seen = reader.call('ledger.explore', {'kind': 'INSTRUMENT'}) or {}
    rows = {row.get('key'): row for row in seen.get('instruments', ()) if row.get('key')}
    place = {key: (column, at) for column, (_, keys) in enumerate(SHELF) for at, key in enumerate(keys)}
    last = len(SHELF) - 1
    for key in sorted(rows, key=lambda k: place.get(k, (last, 99, k))):
        row = rows[key];name = PLAIN.get(key) or row.get('title') or key
        running = int(row.get('running_jobs') or 0);waiting = int(row.get('queued_jobs') or 0) + int(row.get('interrupted_jobs') or 0)
        if not row.get('view_available', True):state = UNAVAILABLE
        elif running:state = 'running'
        elif waiting:state = 'waiting'
        elif row.get('setup_needed'):state = 'needs setup'
        elif row.get('view_class') in open_classes:state = 'in use'
        else:state = ''
        facts = [str(row.get('description') or '').strip()]
        if row.get('setup_needed'):facts.append('needs: ' + ', '.join(str(x) for x in row['setup_needed'])[:120])
        if running or waiting:facts.append('%d running, %d waiting' % (running, waiting))
        reader.add(FieldObject('app:' + key, 'app', name, str(row.get('description') or ''), state, tuple(f for f in facts if f), str(row.get('human_route') or ''),
                               {'kind': 'program', 'key': key, 'entry': row}, column=place.get(key, (last, 0))[0],
                               stac=PROGRAMS_READ + ' | where key=%s | select title,description,view_state,tool_status,setup_needed,operations,running_jobs' % key))
    first = reader.objects[0].id if reader.objects else ''        # the shelf starts at its first program, top left
    return Field(reader.objects, [], title='Programs', selected=first, heads=tuple(head for head, _ in SHELF), compact=True), reader
