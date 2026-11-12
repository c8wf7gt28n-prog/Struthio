"""Source-bound, private context assembly. FTS5 indexes are disposable derivatives.

The existing intake, reference, memory and Project Desk readers retain authority.
Every passage keeps its original revision, locator and extraction rule. Ranking
never admits a source, turns a preference into evidence, or grants an action.
"""
from __future__ import annotations
import base64
from contextlib import closing
import json
import re
import sqlite3
import time
import uuid
from . import project_desk as desk
from . import intelligent_data as arrangement

RULE = 'arc.slate-extraction/1'
QUESTION = {'type': 'string', 'minLength': 1, 'maxLength': 2000}
FIELDS = {
    'slate.context.create': ({'question': QUESTION, 'assignment': desk.ID, 'project': desk.ID,
        'addresses': desk.INPUTS, 'namespaces': {'type': 'array', 'items': desk.ID},
        'char_budget': {'type': 'integer', 'minimum': 512, 'maximum': 32000},
        'passage_limit': {'type': 'integer', 'minimum': 1, 'maximum': 16},
        'include_procedures': {'type': 'boolean'}, 'include_seed': {'type': 'boolean'},
        'calculations': {'type': 'array', 'maxItems': 4, 'items': arrangement.CALCULATION}}, ['question']),
    'slate.context.get': ({'id': desk.ID}, ['id']),
    'slate.context.check': ({'id': desk.ID}, ['id']),
    'slate.context.rebuild': ({'id': desk.ID}, ['id']),
    'slate.context.passage': ({'id': desk.ID, 'passage': arrangement.SHA}, ['id', 'passage']),
    'slate.context.focus': ({'id': desk.ID, 'passage': arrangement.SHA, 'question': QUESTION,
        'char_budget': {'type': 'integer', 'minimum': 512, 'maximum': 32000}}, ['id', 'passage', 'question']),
    'slate.memory.search': ({'question': QUESTION, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 20}}, ['question']),
}
SCOPES = {op: 'execute' if op in ('slate.context.create', 'slate.context.focus') else 'read' for op in FIELDS}
STOP_WORDS = frozenset('a an and are as at be by can do does for from how i in is it me my of on or please tell that the their these this to was what when where which who with would you'.split())
MIGRATIONS = [(1, (
    'CREATE TABLE slate_records(id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL)',
    'CREATE INDEX slate_owner_kind ON slate_records(owner,kind)',
    'CREATE TABLE slate_requests(owner TEXT NOT NULL, request_key TEXT NOT NULL, id TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(owner,request_key))',
    'CREATE TABLE slate_streams(job TEXT PRIMARY KEY, owner TEXT NOT NULL, sequence INTEGER NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL)',
))]


def ensure(db):
    if not db.in_transaction: db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS slate_migrations(version INTEGER PRIMARY KEY, digest TEXT NOT NULL, applied REAL NOT NULL)')
    applied = dict(db.execute('SELECT version,digest FROM slate_migrations'))
    known = {v: desk.digest(sql) for v, sql in MIGRATIONS}
    if sorted(applied) != list(range(1, len(applied) + 1)) or any(known.get(v) != sha for v, sha in applied.items()):
        raise ValueError('SLATE_MIGRATION_UNSUPPORTED')
    for version, sql in MIGRATIONS:
        if version in applied: continue
        for statement in sql: db.execute(statement)
        db.execute('INSERT INTO slate_migrations VALUES(?,?,?)', (version, known[version], time.time()))


def save(db, owner, kind, value):
    raw = desk.canonical(value)
    if len(raw.encode()) > 3 * 1024 * 1024: raise ValueError('SLATE_RECORD_SIZE_LIMIT')
    db.execute('INSERT INTO slate_records VALUES(?,?,?,?,?)', (value['id'], owner, kind, raw, desk.digest(value)))
    return json.loads(raw)


def load(db, owner, kind, ident):
    from .engineering_kernel import identifier
    identifier(ident)
    row = db.execute('SELECT payload,digest FROM slate_records WHERE id=? AND owner=? AND kind=?', (ident, owner, kind)).fetchone()
    if not row: raise ValueError('Graphite record unavailable to this caller')
    value = json.loads(row[0])
    if desk.digest(value) != row[1]: raise ValueError('SLATE_RECORD_DAMAGED')
    return value


def terms_of(question):
    terms = [t.casefold() for t in re.findall(r'[^\W_]+(?:_[^\W_]+)*', question, re.UNICODE)]
    return list(dict.fromkeys(t for t in terms if t not in STOP_WORDS and len(t) <= 80))[:24]


def rank(passages, question):
    """A per-context corpus: no cross-owner BM25 statistics or persistent cache."""
    terms = terms_of(question)
    if not terms: return [], 'QUERY_HAS_NO_SEARCH_TERMS'
    with closing(sqlite3.connect(':memory:')) as db, db:
        try: db.execute('CREATE VIRTUAL TABLE excerpts USING fts5(title,text,tokenize="unicode61")')
        except sqlite3.OperationalError as exc: raise ValueError('SQLite FTS5 is required for Graphite ranked retrieval') from exc
        db.executemany('INSERT INTO excerpts(rowid,title,text) VALUES(?,?,?)',
                       [(i + 1, p['title'], p['text']) for i, p in enumerate(passages)])
        query = ' OR '.join('"' + term.replace('"', '""') + '"' for term in terms)
        scored = list(db.execute('SELECT rowid,bm25(excerpts,2.0,1.0) FROM excerpts WHERE excerpts MATCH ? ORDER BY 2,1', (query,)))
    # Unicode61 does not segment unspaced CJK. Preserve a declared literal fallback.
    found = {i for i, _ in scored}
    for i, passage in enumerate(passages, 1):
        if i not in found and any(re.search('[\u3400-\u9fff]', t) and t in passage['text'].casefold() for t in terms): scored.append((i, 0.0))
    result = []
    for index, score in scored:
        passage = passages[index - 1]
        matched = [term for term in terms if term in (passage['title'] + '\n' + passage['text']).casefold()]
        result.append({**passage, 'rank': len(result) + 1, 'bm25': score, 'matched_terms': matched,
                       'why': 'Lexical match in the selected corpus: ' + ', '.join(matched)})
    return result, 'SQLITE_FTS5_BM25_WITH_LITERAL_CJK_FALLBACK'


def choose(passages, question, budget, limit, pinned=()):
    ranked, method = rank(passages, question); selected = []; excluded = []; used = 0
    # A user-selected table may say "Need,Have" while the question says "short
    # parts". Keep one labelled opening passage per explicit source even without
    # lexical overlap; this is source selection, not invented semantic ranking.
    by_id = {p['id']: p for p in passages}
    if pinned:
        pinned = list(dict.fromkeys(pinned))
        ranked = [{**by_id[ident], 'rank': i + 1, 'bm25': None, 'matched_terms': [],
                   'why': 'Requested source or dependency of an exact calculation.'}
                  for i, ident in enumerate(pinned)] + [p for p in ranked if p['id'] not in pinned]
        ranked = [{**p, 'rank': i + 1} for i, p in enumerate(ranked)]
    found = {p['id'] for p in ranked}; represented = set()
    for p in passages:
        if not p.get('selected_source') or p['binding'] in represented: continue
        represented.add(p['binding'])
        if p['id'] not in found:
            ranked.append({**p, 'rank': len(ranked) + 1, 'bm25': None, 'matched_terms': [],
                           'why': 'Opening passage of an explicitly selected source; no lexical match was required.'})
    matched = {p['id'] for p in ranked}
    for passage in ranked:
        reason = 'PASSAGE_LIMIT' if len(selected) >= limit else 'CHARACTER_BUDGET' if used + len(passage['text']) > budget else None
        if reason:
            excluded.append({key: passage[key] for key in ('id', 'title', 'locator', 'kind', 'rank')}
                            | {'reason': reason, 'characters': len(passage['text'])})
        else:
            selected.append(passage); used += len(passage['text'])
    for passage in passages:
        if passage['id'] not in matched: excluded.append({key: passage[key] for key in ('id', 'title', 'locator', 'kind')} | {'reason': 'NO_LEXICAL_MATCH'})
    return {'selected': selected, 'excluded': excluded, 'characters_used': used, 'char_budget': budget,
            'passage_limit': limit, 'method': method,
            'selection_policy': 'PINNED_DEPENDENCIES_AND_RANKED_PASSAGES' if pinned else 'RANKED_PLUS_EXPLICIT_SOURCE_OPENING_PASSAGES',
            'semantic_search': 'NOT_ENABLED', 'index': 'DISPOSABLE_IN_MEMORY_FTS5'}


def passage(text, title, locator, kind, binding=None, **extra):
    value = {'text': text, 'title': title, 'locator': locator, 'kind': kind, 'binding': binding,
             'extraction_rule': RULE, 'text_sha256': desk.digest(text), **extra}
    return {'id': desk.digest(value), **value}


def text_chunks(text, title, kind, binding, **extra):
    # Exact character spans into retained source text; no invented page numbers.
    result = []; start = 0
    while start < len(text) and len(result) < 128:
        end = min(start + 1200, len(text))
        if end < len(text):
            newline = text.rfind('\n', start + 400, end)
            if newline > start: end = newline + 1
        result.append(passage(text[start:end], title,
            {'kind': 'CHARACTER_SPAN', 'start': start, 'end': end,
             'first_line': text.count('\n', 0, start) + 1, 'last_line': text.count('\n', 0, max(start, end - 1)) + 1}, kind, binding, **extra))
        start = end
    return result, start < len(text)


def from_binding(binding, index, role=None):
    snap = binding['snapshot']; address = binding.get('address') or binding['operation']
    kind = role or ('ENGINEERING_EVIDENCE' if address.startswith('evidence:') else 'JOB_RECEIPT' if address.startswith('job:') else 'SOURCE')
    if binding['operation'] == 'desk.sources.read':
        raw = snap.get('exact_bytes_base64')
        if raw is not None:
            try:
                text = base64.b64decode(raw, validate=True).decode('utf-8')
                if '\x00' in text: raise UnicodeError('binary file')
            except (ValueError, UnicodeError): text = None
            if text is not None:
                return text_chunks(text, address, kind, index, address=address, source_sha256=snap['sha256'],
                    source_revision=binding['revision'], selected_source=True, authority='SOURCE_ASSERTION_NOT_INDEPENDENT_PROOF')
        # Non-text data stays a labelled reader projection, not claimed full extraction.
        visible = snap['projection']['object']; data = visible.get('data')
        if data is None: return [], True
        text = desk.canonical(data)
        return text_chunks(text, address, kind, index, address=address, source_sha256=snap['sha256'],
            source_revision=binding['revision'], selected_source=True, authority='READER_PROJECTION_NOT_FULL_ORIGINAL')
    obj = snap.get('object', snap) if isinstance(snap, dict) else snap
    address_kind = address.partition(':')[0]
    if address_kind == 'document':
        return text_chunks(obj['plain'], obj['document']['title'], 'SOURCE', index, address=address,
                           source_revision=binding['revision'], source_sha256=desk.digest(obj['plain']),
                           selected_source=True, authority='SOURCE_ASSERTION_NOT_INDEPENDENT_PROOF')
    if address_kind in arrangement.TYPED_KINDS:
        typed = arrangement.typed_source(address_kind, obj)
        if typed is None:
            return [], True
        title, observation = typed
        return text_chunks(desk.canonical(observation), title + ' · ' + address, 'ENGINEERING_EVIDENCE', index,
                           address=address, source_revision=binding['revision'], source_sha256=desk.digest(observation),
                           selected_source=True, authority='CURRENT_OBSERVATION_WITH_DECLARED_SCOPE')
    if address_kind == 'packet':
        if obj.get('state') != 'CURRENT':
            return [], True
        return [passage(row['text'], row['name'], row['locator'], 'SOURCE', index,
                        address=address, passage_id=row['id'], source_sha256=row['source_sha256'],
                        source_revision=binding['revision'], selected_source=True,
                        authority=row.get('authority', 'CURRENT_ADMITTED_REFERENCE_NOT_INDEPENDENT_PROOF'))
                for row in obj['passages']], False
    if isinstance(obj, dict) and (obj.get('class') == 'LOCAL_INFERENCE' or str(obj.get('tool', '')).startswith('brain.')):
        kind = 'JOB_RECEIPT'  # A model job completing is not engineering support.
    text = desk.canonical(obj)
    return text_chunks(text, address, kind, index, address=address, source_revision=binding['revision'],
                       source_sha256=desk.digest(obj), selected_source=True, authority='READER_RECORD_SCOPE_ONLY')


def procedures(kernel, principal, question):
    from . import instruction_matrix
    with kernel.db() as db: examples = instruction_matrix.examples(db, principal.identity, question)
    result = []
    for key, kind in (('worked', 'PROCEDURE_SUCCESS'), ('failed', 'PROCEDURE_FAILURE')):
        for example in examples[key][:8]:
            text = desk.canonical(example)
            result.append(passage(text, 'Past procedure: ' + key, {'kind': 'INSTRUCTION_MATRIX', 'id': desk.digest(example)}, kind,
                                   authority='PAST_OUTCOME_NOT_TECHNICAL_EVIDENCE'))
    # The existing reader uses substring matching, so retrieve by individual
    # terms before the common BM25 pass. Do not mislabel proposed/rejected text.
    lessons = {}
    for term in (terms_of(question)[:4] or ['']):
        rows = desk.result_of(kernel, 'memory.lessons', {'query': term}, principal)
        for lesson in rows.get('lessons', [])[:64]: lessons[lesson['id']] = lesson
    for lesson in list(lessons.values())[:128]:
        if lesson.get('review') != 'OWNER_REVIEWED_PROCEDURE': continue
        available = lesson.get('applicability') == 'CURRENT'
        result.append(passage(desk.canonical(lesson) if available else '', lesson.get('title', 'Owner-reviewed lesson'),
            {'kind': 'MEMORY_LESSON', 'id': lesson['id']}, 'OWNER_PROCEDURE',
            availability='CURRENT' if available else 'SOURCE_GAPS', authority='RECOLLECTION_NOT_INDEPENDENT_PROOF'))
    return result


def assemble(kernel, args, principal):
    began = time.monotonic()
    question = args['question']
    if not question.strip(): raise ValueError('Ask a meaningful question')
    desk.bounded(args.get('addresses', []), 16); desk.bounded(args.get('namespaces', []), 4)
    bindings = []; corpus = []; unavailable = []; task = None; project = None
    addresses = list(args.get('addresses', [])); prior = []
    namespaces = list(args.get('namespaces', []))
    if args.get('assignment'):
        task = desk.result_of(kernel, 'assignments.get', {'id': args['assignment']}, principal)
        if args.get('project') and args['project'] != task['project']:
            raise ValueError('The assignment belongs to a different project')
        corpus.append(passage(desk.canonical({key: task[key] for key in ('original_request', 'interpretation', 'intended_output', 'questions', 'success', 'stop')}),
            'Current assignment', {'kind': 'ASSIGNMENT_REVISION', 'id': task['id'], 'revision': task['revision']},
            'TASK_STATE', authority='TASK_INTENT_NOT_EVIDENCE'))
        prior.extend(task['inputs'])
    project_id = task['project'] if task else args.get('project')
    if project_id:
        project = desk.result_of(kernel, 'projects.get', {'id': project_id}, principal)
        for link in project['links']:
            if link.get('source'): prior.append(link['source'])
            elif link.get('text'):
                corpus.append(passage(link['text'], 'Project ' + link['role'].lower(), {'kind': 'PROJECT_LINK', 'id': link['id']},
                    'OWNER_DECISION', authority='OWNER_STATEMENT_NOT_INDEPENDENT_PROOF'))
    if len(prior) + len(addresses) > 32: raise ValueError('Select at most 32 context source bindings')
    seen = set()
    for old in prior:
        if (old.get('address') or '').startswith('collection:'):
            namespaces.append(old['address'].partition(':')[2])
            continue  # A project link selects the collection. Individual passages freeze exact revisions below.
        key = desk.digest({'operation': old['operation'], 'arguments': old['arguments']})
        if key in seen: continue
        seen.add(key)
        state = desk.freshness(kernel, [old], principal)
        if state['state'] != 'CURRENT':
            unavailable.append({'address': old.get('address'), 'reason': 'SELECTED_REVISION_CHANGED_OR_UNAVAILABLE'}); continue
        bindings.append(old)
    for address in addresses:
        try:
            bound = desk.snapshots(kernel, [address], principal)[0]
            key = desk.digest({'operation': bound['operation'], 'arguments': bound['arguments']})
            if key not in seen: bindings.append(bound); seen.add(key)
        except (ValueError, OSError): unavailable.append({'address': address, 'reason': 'SOURCE_UNAVAILABLE_TO_THIS_CALLER'})
    for index, binding in enumerate(bindings):
        if (binding.get('address') or '').startswith('collection:'):
            namespaces.append(binding['address'].partition(':')[2])
            continue
        chunks, gap = from_binding(binding, index); corpus.extend(chunks)
        if gap:
            kind = (binding.get('address') or '').partition(':')[0]
            reason = 'SOURCE_OBSERVATION_UNAVAILABLE_OR_STALE' if not chunks and (
                kind in arrangement.TYPED_KINDS or kind == 'packet') else 'EXTRACTION_OR_CHUNK_BOUND_REACHED'
            unavailable.append({'address': binding.get('address'), 'reason': reason})
    namespaces = list(dict.fromkeys(namespaces))
    desk.bounded(namespaces, 4)
    for namespace in namespaces:
        # Existing intake eligibility and original-byte checks run in this reader.
        try:
            collection = desk.call_binding(kernel, 'references.collection', {'namespace': namespace}, principal)
            bindings.append(collection)
            if not collection['snapshot']['index_current']:
                unavailable.append({'namespace': namespace, 'address': collection['snapshot']['name'],
                                    'reason': 'INDEX_ADMITTED_COLLECTION_FIRST'})
                continue
            hits = desk.result_of(kernel, 'references.search', {'namespace': namespace, 'query': question[:300], 'limit': 12}, principal)
        except (ValueError, OSError):
            unavailable.append({'namespace': namespace, 'reason': 'REFERENCE_SEARCH_UNAVAILABLE'})
            continue
        for hit in hits.get('hits', []):
            try:
                bound = desk.call_binding(kernel, 'references.resolve',
                    {'namespace': namespace, 'id': hit['id'], 'item': hit['item']}, principal)
                source = bound['snapshot']
                if source['state'] != 'CURRENT':
                    raise ValueError('Reference passage is no longer current')
            except (ValueError, OSError):
                unavailable.append({'namespace': namespace, 'reason': 'REFERENCE_PASSAGE_UNAVAILABLE'})
                continue
            index = len(bindings); bindings.append(bound)
            corpus.append(passage(source['text'], source['name'], source['locator'], 'SOURCE', index,
                source_sha256=source['source_sha256'], source_revision=bound['revision'], passage_id=source['id'],
                authority='CURRENT_ADMITTED_REFERENCE_NOT_INDEPENDENT_PROOF'))
        unavailable.extend({'namespace': namespace, **row} for row in hits.get('unavailable', []))
    recalled = procedures(kernel, principal, question) if args.get('include_procedures', True) else None
    if recalled is not None:
        corpus.extend(p for p in recalled if p.get('availability', 'CURRENT') == 'CURRENT')
        unavailable.extend({'address': p['locator']['id'], 'reason': 'REVIEWED_PROCEDURE_SOURCE_GAPS'}
            for p in recalled if p.get('availability') == 'SOURCE_GAPS')
    if args.get('include_seed', True):
        found = desk.result_of(kernel, 'stacy.seed.search', {'query': question[:180], 'limit': 3}, principal)
        for record in found.get('records', []):
            bound = desk.call_binding(kernel, 'stacy.seed.record', {'id': record['id']}, principal)
            index = len(bindings); bindings.append(bound)
            chunks, gap = text_chunks(desk.canonical(bound['snapshot']), record.get('title', record['id']), 'LEDGER_SOURCE', index,
                source_revision=bound['revision'], source_sha256=desk.digest(bound['snapshot']), authority='LEDGER_SELF_KNOWLEDGE_NOT_HARDWARE_PROOF')
            corpus.extend(chunks[:4])
            if gap or len(chunks) > 4: unavailable.append({'address': 'seed:' + record['id'], 'reason': 'SEED_EXCERPT_BOUND'})
    if len(corpus) > 512: raise ValueError('Context exceeds 512 passages; select fewer sources')
    if len(desk.canonical(bindings).encode()) > 2097152: raise ValueError('Context source snapshots exceed 2 MiB')
    corpus = list({p['id']: p for p in corpus}.values())
    prepared = arrangement.prepare(args.get('calculations', []), corpus, question)
    selection = choose(corpus, question, args.get('char_budget', 6000), args.get('passage_limit', 8), prepared['pinned'])
    prepared.update(arrangement.selected_details(selection['selected'], bindings))
    from .stacy_foundation import seed_status
    seed = seed_status(kernel.root)
    if seed['state'] != 'VERIFIED_SOURCE_BINDINGS': raise ValueError('Program source foundation is not current')
    value = {'schema': 'arc.slate-context/1', 'id': uuid.uuid4().hex, 'owner': principal.identity, 'created': time.time(),
        'question': question, 'assignment': task['id'] if task else None, 'assignment_revision': task['revision'] if task else None,
        'project': project['id'] if project else None, 'project_revision': project['revision'] if project else None,
        'plan': task.get('plan') if task else None, 'bindings': bindings, 'corpus': corpus, 'selection': selection,
        'preparation': prepared,
        'unavailable': unavailable, 'extraction_rule': RULE, 'seed_id': seed['seed_id'],
        'procedure_digest': desk.digest(recalled) if recalled is not None else None,
        'metrics': {'assembly_seconds': time.monotonic() - began, 'passages_considered': len(corpus),
                    'selected_characters': selection['characters_used']},
        'authority': 'DATA_ONLY_NO_PERMISSION', 'memory_classes': 'PREFERENCES_TASKS_PROCEDURES_EVIDENCE_REMAIN_DISTINCT'}
    value['content_digest'] = desk.digest(value)
    with kernel.db() as db: return save(db, principal.identity, 'context', value)


def check(kernel, value, principal):
    fresh = desk.freshness(kernel, value['bindings'], principal); reasons = []
    if fresh['state'] != 'CURRENT': reasons.append('SOURCES_CHANGED_OR_UNAVAILABLE')
    procedure_question = value.get('procedure_question', value['question'])
    if value.get('procedure_digest') is not None and desk.digest(procedures(kernel, principal, procedure_question)) != value['procedure_digest']:
        reasons.append('PROCEDURE_MEMORY_CHANGED')
    if value['assignment']:
        current = desk.result_of(kernel, 'assignments.get', {'id': value['assignment']}, principal)
        if current['revision'] != value['assignment_revision'] or current.get('plan') != value['plan']: reasons.append('ASSIGNMENT_CHANGED')
    if value.get('project'):
        project = desk.result_of(kernel, 'projects.get', {'id': value['project']}, principal)
        if project['revision'] != value['project_revision']: reasons.append('PROJECT_CHANGED')
    from .stacy_foundation import seed_status
    seed = seed_status(kernel.root)
    if seed['state'] != 'VERIFIED_SOURCE_BINDINGS' or seed['seed_id'] != value['seed_id']: reasons.append('PROGRAM_SOURCE_CHANGED')
    gaps = [gap for row in (value.get('preparation') or {}).get('calculations', []) for gap in row['gaps']]
    state = 'STALE' if reasons else 'CURRENT_WITH_GAPS' if value['unavailable'] or gaps else 'CURRENT'
    return {'state': state, 'reasons': reasons, 'freshness': fresh, 'unavailable': value['unavailable'],
            'calculation_gaps': gaps, 'usable': not reasons}


def current_passage(kernel, value, ident, principal):
    source = next((row for row in value['corpus'] if row['id'] == ident and row.get('binding') is not None), None)
    if source is None:
        raise ValueError('Choose a bound passage from this context')
    if not check(kernel, value, principal)['usable']:
        raise ValueError('Sources changed. Prepare evidence again to read the current passage.')
    return source


def focus(kernel, value, args, principal):
    began = time.monotonic()
    question = args['question']
    if not question.strip():
        raise ValueError('Ask a meaningful question')
    source = current_passage(kernel, value, args['passage'], principal)
    budget = args.get('char_budget', value['selection']['char_budget'])
    if len(source['text']) > budget:
        raise ValueError('Increase context characters to fit the selected passage')
    previous = value.get('preparation') or {}
    prepared = arrangement.prepare(previous.get('requests', []), value['corpus'], question)
    pinned = [source['id'], *prepared['pinned']]
    selection = choose(value['corpus'], question, budget, value['selection']['passage_limit'], pinned)
    prepared.update(arrangement.selected_details(selection['selected'], value['bindings']))
    focused = {**value, 'id': uuid.uuid4().hex, 'created': time.time(), 'question': question,
               'procedure_question': value.get('procedure_question', value['question']), 'parent_context': value['id'],
               'focus_passage': source['id'], 'selection': selection, 'preparation': prepared,
               'metrics': {'assembly_seconds': time.monotonic() - began, 'passages_considered': len(value['corpus']),
                           'selected_characters': selection['characters_used']}}
    focused.pop('content_digest', None)
    focused['content_digest'] = desk.digest(focused)
    with kernel.db() as db:
        return save(db, principal.identity, 'context', focused)


def dispatch(kernel, op, args, principal):
    if op == 'slate.context.create': return assemble(kernel, args, principal)
    if op == 'slate.memory.search':
        recalled = procedures(kernel, principal, args['question'])
        ranked, method = rank([p for p in recalled if p.get('availability', 'CURRENT') == 'CURRENT'], args['question'])
        return {'records': ranked[:args.get('limit', 10)], 'ranking': method,
                'unavailable': [{'title': p['title'], 'locator': p['locator'], 'reason': 'SOURCE_GAPS'} for p in recalled if p.get('availability') == 'SOURCE_GAPS'],
                'semantic_search': 'NOT_ENABLED', 'authority': 'RECOLLECTION_NOT_PROOF'}
    with kernel.db() as db: value = load(db, principal.identity, 'context', args['id'])
    if op == 'slate.context.get': return value
    if op == 'slate.context.check': return check(kernel, value, principal)
    if op == 'slate.context.passage':
        return {'context': value['id'], 'source': current_passage(kernel, value, args['passage'], principal)}
    if op == 'slate.context.focus':
        return focus(kernel, value, args, principal)
    pinned = (value.get('preparation') or {}).get('pinned', [])
    if value.get('focus_passage'):
        pinned = [value['focus_passage'], *pinned]
    selection = choose(value['corpus'], value['question'], value['selection']['char_budget'], value['selection']['passage_limit'], pinned)
    return {'state': 'REBUILT', 'selection': selection, 'matches_frozen_selection': selection == value['selection'],
            'index': 'DISPOSABLE_IN_MEMORY_FTS5', 'semantic_search': 'NOT_ENABLED'}
