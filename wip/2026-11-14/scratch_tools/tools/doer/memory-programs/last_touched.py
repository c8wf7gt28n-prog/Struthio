"""last_touched(kernel, principal, field) -> {field object id: (time, operation, how)}

READS ONLY. Everything is asked through Kernel.dispatch with observer operations (activity.OBSERVER_OPERATIONS), so calling
it adds nothing to the owner's timeline; the one exception is `office_rows`, which reads the Office store's own event rows
directly because no operation returns them (pass office_rows=False to stay inside the dispatcher). No Qt.
`how` names the record the time came from, so a reader can check it."""
import json, re

def _read(kernel, principal, operation, arguments=None):
    try: answer = kernel.dispatch(operation, arguments or {}, principal)
    except Exception: return None
    return answer['result'] if isinstance(answer, dict) and answer.get('ok') else None

def journal(kernel, principal, after=0, cap=5000):
    """Every journal row after seq `after`, 200 at a time. ledger.journal.read has no time or object filter: 'since T' is this
    plus a comparison on row['at']; 'the last N' is after = head - N (ledger.journal.status gives head)."""
    rows = []; cursor = str(after)
    while len(rows) < cap:
        page = _read(kernel, principal, 'ledger.journal.read', {'after': cursor, 'limit': 200})
        if not page or not page['events']: break
        rows.extend(page['events']); cursor = page['cursor']
        if not page.get('has_more'): break
    return rows

def program_of(operation, views):
    """The shelf key whose operation prefixes (explore.VIEWS row[7]) own this operation name, or None."""
    for key, prefixes in views:
        if operation.startswith(prefixes): return key
    return None

def programs_touched(rows, views):
    """{shelf key: (time, 'operation STATE', seq)}: the last time one of a program's operations finished, from the journal."""
    out = {}
    for e in rows:
        key = program_of(e['operation'], views)
        if key and e['state'] != 'REQUEST_RECEIVED': out[key] = (e['at'], e['operation'] + ' ' + e['state'], e['seq'])
    return out

def last_touched(kernel, principal, field, rows=None, office_rows=True):
    out = {}; ids = {obj.id: obj for obj in field.objects}
    def put(ident, at, operation, how):
        if at is None or ident not in ids: return
        if ident not in out or float(at) > out[ident][0]: out[ident] = (float(at), operation, how)
    rows = journal(kernel, principal) if rows is None else rows
    # 1. jobs: each job says which record it worked on in its request (request_spec), and when it finished
    jobs = _read(kernel, principal, 'jobs.list') or []
    jobs = jobs if isinstance(jobs, list) else jobs.get('jobs', [])
    for job in jobs:
        at = job.get('finished') or job.get('started') or job.get('created')
        put('job:' + job['id'], at, job.get('tool', 'job'), 'jobs.list ' + ('finished' if job.get('finished') else 'created'))
        spec = job.get('request_spec') or {}
        for part in spec.values():
            if isinstance(part, dict) and part.get('item'): put('intake:' + str(part['item']), at, job.get('tool', 'job'), 'jobs.list request_spec item, job ' + job['id'][:8])
    # 2. pages and calculations: documents.list rows carry `updated` and `last_change` (no extra read per page)
    for row in (_read(kernel, principal, 'documents.list', {'limit': 100}) or {}).get('documents', ()):
        change = row.get('last_change') or {}
        put('document:' + row['id'], row.get('updated'), 'documents.save' if row.get('revision', 1) > 1 else 'documents.create',
            'documents.list updated · revision %s · %s %s' % (row.get('revision'), change.get('actor', ''), change.get('words', '')))
    # 3. sources: an item has no time of its own; its batch does
    for space in (_read(kernel, principal, 'intake.namespaces') or {}).get('namespaces', ()):
        batches = {b['id']: b for b in (_read(kernel, principal, 'intake.batches', {'namespace': space['id'], 'limit': 100}) or {}).get('batches', ())}
        for item in (_read(kernel, principal, 'intake.items', {'namespace': space['id'], 'limit': 100}) or {}).get('items', ()):
            batch = batches.get(item.get('batch')) or {}
            put('intake:' + item['id'], batch.get('created'), 'intake.import', 'intake.batches created (the item\'s batch)')
    # 4. findings and questions: when the claim was written; the investigation's own `updated`
    for inv in (_read(kernel, principal, 'investigation.list') or {}).get('investigations', ()):
        put('investigation:' + inv['id'], inv.get('updated'), 'investigation', 'investigation.list updated')
        sheet = _read(kernel, principal, 'investigation.sheet', {'id': inv['id']}) or {}
        for claim in list(sheet.get('unresolved') or ()) + list(sheet.get('learned') or ()):
            put('claim:' + claim['id'], claim.get('created'), 'investigation.claim', 'investigation.sheet claim.created')
    # 5. sheets: the Office store keeps one row per create/save with the object id; no operation returns them
    if office_rows:
        try:
            from workbench import office_service
            with office_service.store().catalog.db() as db:
                for at, operation, ident in db.execute("SELECT at,operation,object_id FROM events WHERE object_id LIKE 'owner:%' ORDER BY seq"):
                    put('office:' + ident, at, operation, 'Office store events row (read directly, not through an operation)')
        except Exception:  # the store is the profile's; a reader never fails on it
            pass
    # 6. staC lines that ran: the instruction matrix keeps each line's text and time, and the text names the record
    for row in (_read(kernel, principal, 'matrix.list', {'limit': 200}) or {}).get('rows', ()):
        text = row.get('program') or ''
        for ident in ids:
            bare = ident.split(':', 1)[1]
            if len(bare) >= 32 and bare in text: put(ident, row.get('updated') or row.get('created'), 'language.run', 'matrix.list row %s (%s)' % (row['id'][:8], row.get('outcome')))
    # 7. what was brought to the front: the journal keeps the tab's title only; it counts when exactly one sheet has that title
    titles = {}
    for obj in field.objects: titles.setdefault(obj.title, []).append(obj.id)
    for e in rows:
        if e['operation'] == 'ledger.view' and e.get('detail'):
            match = titles.get(e['detail'].replace('Preview · ', '').replace('◆ ', ''))
            if match and len(match) == 1: put(match[0], e['at'], 'ledger.view', 'journal seq %d, matched by tab title' % e['seq'])
    return out
