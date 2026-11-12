"""What can be done about one thing, said by the records (no Qt).

The owner asked for "a doer, not a chatbot". This module is the part that knows what there is to do: for one object of the
Field it asks the records how the object stands and returns the steps that fit, in the order they would be taken. Nothing
here decides, and no model is asked: the steps come from the object's own record (its kind, its state, its revision, what
feeds it), and each one is an exact line:

    a staC line                      a read; it runs at once and changes nothing
    /operation {"argument": ...}     an operation line; a read runs at once, anything that changes something waits for the owner

Every line can be put in the writing strip, changed and run again, so what Graphite did is always something the owner can
read and repeat. The steps are the operations the program already has (docs: the Kernel's registry); this module adds none.

    steps_for(kernel, principal, obj, field)   the steps for one object
    sweep(kernel, principal, field)            every object that waits, with why and its steps, and what was read to find out
    call(line)                                 (operation, arguments) of a line, for whoever runs it
"""
import hashlib
import json
from dataclasses import dataclass


@dataclass
class Step:
    words: str              # what the step does, in a few plain words
    kind: str = 'read'      # 'read': runs at once, changes nothing · 'write': changes something, so it waits for the owner
    line: str = ''          # the exact line
    why: str = ''           # why the records offer it, or what it will leave behind
    scope: str = 'read'     # the Kernel's scope for it: read, execute, approve
    settles: bool = False   # taking it is what brings the thing back to current (so "settle the desk" may include it)


def op(operation, **arguments):
    """An operation line, as the writing strip takes it."""
    return '/' + operation + ' ' + json.dumps(arguments, ensure_ascii=False, separators=(', ', ': '))


def js(**arguments):
    """Arguments inside a staC line: compact JSON."""
    return json.dumps(arguments, ensure_ascii=False, separators=(',', ':'))


def call(line):
    """(operation, arguments) for a line: an operation line as written, a staC line through the language's own router."""
    line = line.strip()
    if line.startswith('/'):
        name, _, rest = line[1:].partition(' ')
        return name, (json.loads(rest) if rest.strip() else {})
    from .stac_bridge import route_program
    return route_program(line)


def _read(kernel, principal, operation, arguments):
    try:
        answer = kernel.dispatch(operation, arguments, principal)
    except Exception:  # noqa: BLE001 - a record that cannot be read offers no step; it never stops the others
        return None
    return answer['result'] if answer.get('ok') else None


def _watch(title, line):
    return Step('Watch it', 'write', op('agenda.add', title='Watch: ' + str(title)[:120], program=line, watch=True),
                'Graphite asks again every few hours and speaks only when the answer is different', 'execute')


def _calculation(kernel, principal, obj, field):
    ident = obj.target['id'];got = _read(kernel, principal, 'documents.get', {'id': ident})
    out = [Step('See what went into it', 'read', obj.stac)]
    if not got:return out
    state = (got.get('source_state') or {}).get('state');document = got.get('document') or {};derivation = document.get('derivation') or {}
    cells = [str(i.get('cell')) for i in derivation.get('inputs', ()) if i.get('cell')];sheet = derivation.get('sheet')
    agrees = 'documents.get %s | pick source_state | select state' % js(id=ident)
    if state == 'RECHECK_SHEET_CHANGED':
        if sheet and cells:
            out.append(Step('See its cells now', 'read',
                            '@office:%s | pick document.sheets | select %s' % (sheet, ','.join('cells.%s.value' % c for c in cells)),
                            'its sheet was changed after this was worked out'))
        out.append(Step('Bring it up to date', 'write',
                        op('office.datasheet.recheck', id=ident, expected_revision=document.get('revision')),
                        'the same calculation, worked again from the sheet as it is now; the new page takes its place and this one is kept in Documents', 'approve', True))
    elif state == 'PDF_SOURCE_REVIEW_REQUIRED':
        if sheet:
            out.append(Step('See its sheet’s source', 'read', 'office.get %s | select source_state.state,origin.pdf.name,origin.pdf.page_index' % js(id=sheet),
                            'the source of its sheet was decided again; the sheet has to be reviewed from its page before this can be worked again'))
    else:
        out.append(Step('Check it still agrees', 'read', agrees, 'with the sheet it was worked out from'))
    out.append(_watch(obj.title, agrees))
    return out


def _sheet(kernel, principal, obj, field):
    ident = obj.target['id'];got = _read(kernel, principal, 'office.get', {'id': ident})
    out = [Step('See where it came from', 'read', obj.stac)]
    if not got:return out
    state = (got.get('source_state') or {}).get('state');pdf = (got.get('origin') or {}).get('pdf') or {}
    if state == 'PDF_SOURCE_REVIEW_REQUIRED' and pdf.get('namespace') and pdf.get('item'):
        out.append(Step('See its source now', 'read',
                        'intake.items %s | pick items | where id=%s | select name,admission,decision_id' % (js(namespace=pdf['namespace']), pdf['item']),
                        'its source was decided again after this sheet was reviewed from it'))
    for link in (field.feeds(obj.id) if field is not None else ()):      # from the sheet, what it feeds can be brought up to date
        fed = field.get(link.target)
        if fed is None or fed.kind != 'calculation' or fed.state != 'recheck':continue
        calc = _read(kernel, principal, 'documents.get', {'id': fed.target['id']})
        if calc and (calc.get('source_state') or {}).get('state') == 'RECHECK_SHEET_CHANGED':
            out.append(Step('Bring “%s” up to date' % fed.title, 'write',
                            op('office.datasheet.recheck', id=fed.target['id'], expected_revision=calc['document'].get('revision')),
                            'it was worked out from this sheet before the sheet changed', 'approve'))
    if obj.stac:out.append(_watch(obj.title, obj.stac))
    return out


def _claim(kernel, principal, obj, field):
    inv = obj.target.get('id');claim = obj.id.split(':', 1)[1] if obj.id.startswith('claim:') else None
    finding = obj.kind == 'finding'
    out = [Step('See why it stands' if finding else 'See what is still open', 'read', obj.stac)] if obj.stac else []
    if not inv:return out
    sheet = _read(kernel, principal, 'investigation.sheet', {'id': inv}) or {}
    path = _read(kernel, principal, 'investigation.path', {'claim': claim}) if claim and finding else None
    out.append(Step('See what comes next', 'read', 'investigation.sheet %s | pick next | select kind,text' % js(id=inv)))
    if not finding:                           # an open question: look for what could answer it
        spaces = sorted({o.target.get('namespace') for o in (field.objects if field is not None else ()) if o.kind == 'source' and isinstance(o.target, dict) and o.target.get('namespace')})
        words = ' '.join(w for w in str(obj.title).replace('?', ' ').split() if len(w) > 3)[:80]
        if spaces and words:
            out.append(Step('Search the sources for its words', 'read', op('intake.search', namespace=spaces[0], query=words)))
    out.append(Step('Look at its sources again', 'write', op('investigation.refresh', id=inv),
                    'marks what changed since the findings were recorded; decides nothing', 'execute'))
    due = [c for c in sheet.get('checked', ()) if c.get('last_outcome') in ('NOT_RUN', 'FAILED', 'STALE')]
    if due or (sheet.get('next') or {}).get('kind') == 'CHECK':
        out.append(Step('Run its due checks (%d)' % len(due) if due else 'Run its due checks', 'write', op('investigation.continue', id=inv),
                        'each check is a read with an expectation; what passes counts as support', 'execute', True))
    quoted = next(((was, now, name) for was, now, name in (field.moved if field is not None else ()) if was in obj.title and now not in obj.title), None) if finding else None
    if quoted:                                # its words carry a result that has since been worked again
        was, now, name = quoted
        out.append(Step('Write it again with %s' % now, 'write', op('investigation.claim', id=inv, text=str(obj.title).replace(was, now), role='FINDING'),
                        'a new finding with the number “%s” gives now; it stands on nothing until its sources are cited for it' % name, 'execute'))
        if not (path and path.get('review') == 'NEEDS_REVIEW'):
            out.append(Step('Retire this one', 'write', op('investigation.review', claim=claim, decision='RETIRE'),
                            'it is taken out of what is known; its words say %s' % was, 'approve'))
    if path and path.get('review') == 'NEEDS_REVIEW':
        out.append(Step('Accept the change', 'write', op('investigation.review', claim=claim, decision='ACCEPT_CHANGE'),
                        'something it stands on changed; this says the finding still holds on the changed source', 'approve'))
        out.append(Step('Retire the finding', 'write', op('investigation.review', claim=claim, decision='RETIRE'),
                        'it is taken out of what is known; it can be written again', 'approve'))
    return out


def _source(kernel, principal, obj, field):
    target = obj.target;out = [Step('See what it is', 'read', obj.stac)] if obj.stac else []
    if target.get('namespace') and target.get('item'):
        out.append(Step('See what depends on it', 'read', op('references.impact', namespace=target['namespace'], item=target['item'])))
        out.append(Step('Read its text', 'read', op('intake.read', id=target['item'])))
    if obj.stac:out.append(_watch(obj.title, obj.stac))
    return out


def _condition(kernel, principal, obj, field):
    ident = obj.id.split(':', 1)[1]
    out = [Step('See why it is out of date', 'read', 'conditions.get %s | pick condition | select state,reason,result' % js(id=ident))]
    got = _read(kernel, principal, 'conditions.get', {'id': ident}) or {}
    if (got.get('condition') or {}).get('state') == 'STALE':
        out.append(Step('Bring the total up to date', 'write', op('conditions.recheck', id=ident),
                        'the page is read again, the numbers added, and the result paragraph rewritten', 'execute', True))
    return out


def _job(kernel, principal, obj, field):
    ident = obj.target.get('id');out = [Step('See how it stands', 'read', op('jobs.get', id=ident))]
    if obj.state in ('paused', 'interrupted'):
        out.append(Step('Carry on with it', 'write', op('jobs.resume', id=ident), '', 'execute'))
    if obj.state in ('waiting', 'paused', 'interrupted', 'running'):
        out.append(Step('Cancel it', 'write', op('jobs.cancel', id=ident), 'it stops; what it already wrote is kept', 'execute'))
    return out


def _page(kernel, principal, obj, field):
    ident = obj.target['id']
    return [Step('Read its words', 'read', 'documents.get %s | pick document.blocks | select text' % js(id=ident)),
            Step('See its history', 'read', 'documents.get %s | pick events | select revision,actor,action,at' % js(id=ident))]


BY_KIND = {'calculation': _calculation, 'sheet': _sheet, 'finding': _claim, 'question': _claim, 'source': _source,
           'condition': _condition, 'job': _job, 'document': _page}


def steps_for(kernel, principal, obj, field=None):
    """The steps the records offer for one object, most useful first. A kind with nothing special to do still offers its own
    read, so D never answers with nothing for a thing that can be read."""
    target = obj.target if isinstance(obj.target, dict) else {}
    made = BY_KIND.get(obj.kind)
    try:
        steps = made(kernel, principal, obj, field) if made and (target or obj.kind == 'condition') else []
    except (KeyError, TypeError, ValueError, AttributeError):
        steps = []
    if not steps and obj.stac:
        steps = [Step('See what the records say about it', 'read', obj.stac)]
    return [step for step in steps if step.line][:9]


def settling(waiting):
    """From a checked desk, the changes that would bring things back to current, one for each thing that has one, in the
    order the desk lists them: [(object, step)]. What only the owner can decide (a review, an open question) is not here."""
    plan = [];seen = set()
    for obj, _, steps in waiting:
        step = next((step for step in steps if step.kind == 'write' and step.settles), None)
        if step is not None and step.line not in seen:
            plan.append((obj, step));seen.add(step.line)
    return plan


def sweep(kernel, principal, field):
    """Check the desk: every object that waits for the owner, with why, and its steps. Findings are checked without writing:
    each source an investigation recorded is read again and its digest compared, which is what investigation.refresh would
    report, so a change is noticed here before anything is marked. Returns (waiting, lines): waiting is a list of
    (object, why, steps); lines are the reads that were made, each an exact line."""
    waiting = [];lines = [];seen = set()
    for obj in field.objects:
        if obj.needs_attention():
            why = obj.state
            if obj.kind == 'finding':
                quoted = next(((was, now, name) for was, now, name in field.moved if was in obj.title and now not in obj.title), None)
                if quoted:why = 'its words say %s; “%s” now gives %s' % (quoted[0], quoted[2], quoted[1])
            waiting.append((obj, why, steps_for(kernel, principal, obj, field)));seen.add(obj.id)
    by_inv = {}
    for obj in field.objects:
        if obj.kind in ('finding', 'question') and isinstance(obj.target, dict) and obj.target.get('id'):
            by_inv.setdefault(obj.target['id'], []).append(obj)
    for inv, claims in by_inv.items():
        sheet = _read(kernel, principal, 'investigation.sheet', {'id': inv});lines.append('investigation.sheet %s | pick read | select address,state' % js(id=inv))
        if not sheet:continue
        moved = []
        for row in sheet.get('read', ()):
            if row.get('state') != 'CURRENT' or not row.get('address'):continue
            now = _read(kernel, principal, 'ledger.address.read', {'address': row['address']});lines.append(op('ledger.address.read', address=row['address']))
            digest = hashlib.sha256(json.dumps((now or {}).get('object'), sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest() if now else 'UNAVAILABLE'
            if digest != row.get('digest'):moved.append(row['address'])
        if moved:
            names = ', '.join((field.get(address).title if field.get(address) else address) for address in moved[:3])
            for obj in claims:
                if obj.id in seen or obj.kind != 'finding':continue
                waiting.append((obj, 'a source changed since it was recorded: ' + names, steps_for(kernel, principal, obj, field)));seen.add(obj.id)
    for obj in field.objects:
        if obj.stac and obj.kind not in ('finding', 'question'):lines.append(obj.stac)
    return waiting, lines
