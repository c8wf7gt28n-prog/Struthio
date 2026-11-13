"""The desk as something staC can read.

staC could read every record of the workspace but not the desk that is made of them: what waits, what feeds what, what
changed lately. These operations are reads, so a staC line can start with any of them, and Stacy shows them like any
other read she makes. They change nothing and are not journaled (showing the desk is not an event).

  field.read    read   {}           the Field of this workspace as records: objects, wires, what waits, counts
  field.trace   read   {id}         where one thing comes from and what rests on it, hop by hop along the wires
  field.whatif  read   {id, set}    a calculation worked again with other values for some inputs, changing nothing
  field.doubt   read   {id?}        what a plausible result may hide: one thing cross-examined, or every doubt on the desk
  field.ripple  read   {id, set}    a cell set to another value and followed along the wires: everything that would move
  field.brief   read   {}           the desk written up as one page, line by line, from the records (no model)

One operation here changes something, and so it is not a read and waits for the owner wherever it is offered:

  field.brief.keep  execute  {shown?}   the brief written as a page in Documents; a later one takes its place. `shown` is
                                        the fingerprint field.brief gave: with it, nothing is kept if the desk has changed since

Lines that work:

  field.read | pick waiting | select kind,title,state
  field.read | pick objects | where lately=yes | select kind,title,changed_at
  field.read | pick links | where stale=yes | select from,to,label
  field.trace {"id":"document:<id>"} | pick rows | select way,steps,kind,title,state,by
  field.whatif {"id":"document:<id>","set":{"B3":"320"}} | select says_now,would_be,exact
  field.doubt {"id":"claim:<id>"} | pick rows | select verdict,about,why
  field.doubt | pick rows | where verdict=doubt | select title,about,why
  field.ripple {"id":"office:<id>","set":{"B4":"100"}} | pick rows | select way,kind,title,says_now,would_be,why
  field.brief | pick lines | select text
  field.brief | pick lines | where part=doubt | select text

The reading is the Field's own (workbench/field_source.py), so a line and the picture can never disagree. Yes and no are
written as the words "yes" and "no", which a staC `where` compares without ceremony.
"""
import time

SCHEMA = 'graphite.field/1'
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 200}
FIELDS = {
    'field.read': ({}, []),
    'field.trace': ({'id': TEXT}, ['id']),
    'field.whatif': ({'id': TEXT, 'set': {'type': 'object'}}, ['id', 'set']),
    'field.doubt': ({'id': TEXT}, []),
    'field.ripple': ({'id': TEXT, 'set': {'type': 'object'}}, ['id', 'set']),
    'field.brief': ({}, []),
    'field.brief.keep': ({'shown': {'type': 'string', 'minLength': 64, 'maxLength': 64}}, []),
}
WRITES = ('field.brief.keep',)
SCOPES = {operation: 'execute' if operation in WRITES else 'read' for operation in FIELDS}
OBSERVERS = tuple(operation for operation in FIELDS if operation not in WRITES)
REACH = 8                    # how many hops a trace follows in each direction


def _yes(value):
    return 'yes' if value else 'no'


def _row(obj, now):
    return {'id': obj.id, 'kind': obj.kind, 'title': obj.title, 'state': obj.state, 'role': obj.role, 'facts': list(obj.lines), 'where': obj.where,
            'stac': obj.stac, 'changed_at': time.strftime('%Y-%m-%d %H:%M', time.localtime(obj.touched)) if obj.touched else '',
            'lately': _yes(obj.lately(now)), 'waits': _yes(obj.needs_attention())}


def read(kernel, principal):
    from .field_source import problems, read_field
    field, reader = read_field(kernel, principal)
    now = time.time();name = {obj.id: obj.title for obj in field.objects}
    objects = [_row(obj, now) for obj in field.objects]
    links = [{'source': link.source, 'target': link.target, 'from': name.get(link.source, ''), 'to': name.get(link.target, ''),
              'label': link.label, 'stale': _yes(link.stale)} for link in field.links]
    return {'schema': SCHEMA, 'title': field.title, 'objects': objects, 'links': links,
            'waiting': [row for row in objects if row['waits'] == 'yes'], 'counts': field.census(),
            'moved': [{'was': was, 'now': new, 'calculation': title} for was, new, title in field.moved],
            'left_out': field.note, 'elsewhere': field.aside, 'could_not_read': problems(reader)}


def trace(kernel, principal, ident):
    """Upstream first, farthest first, then the thing itself, then what rests on it, nearest first. `by` is what the wire says
    (the cells, the page); `next` is the thing one hop nearer, so each row reads "<title> —by→ <next>"."""
    from .field_source import read_field
    field, _ = read_field(kernel, principal)
    start = field.get(ident)
    if start is None:
        raise ValueError('Nothing on the desk has the id %s. field.read lists the ids.' % ident[:80])

    def walk(way):
        seen = {ident};edge = [(ident, 0)];out = []
        while edge:
            current, steps = edge.pop(0)
            if steps >= REACH:continue
            for link in (field.fed_by(current) if way == 'from' else field.feeds(current)):
                other = link.source if way == 'from' else link.target
                if other in seen or field.get(other) is None:continue
                seen.add(other);obj = field.get(other)
                out.append({'way': way, 'steps': steps + 1, 'kind': obj.kind, 'title': obj.title, 'state': obj.state, 'by': link.label,
                            'stale': _yes(link.stale), 'next': field.get(current).title, 'id': obj.id, 'stac': obj.stac})
                edge.append((other, steps + 1))
        return out

    up = walk('from');down = walk('to')
    this = {'way': 'this', 'steps': 0, 'kind': start.kind, 'title': start.title, 'state': start.state, 'by': '', 'stale': 'no', 'next': '',
            'id': start.id, 'stac': start.stac}
    return {'schema': SCHEMA, 'id': start.id, 'title': start.title, 'rows': sorted(up, key=lambda row: -row['steps']) + [this] + down,
            'comes_from': [row['title'] for row in up if row['kind'] == 'source'], 'rests_on_it': len(down),
            'stale_on_the_way': [row['title'] for row in up + down if row['stale'] == 'yes']}


def whatif(kernel, principal, ident, changes):
    from . import datasheet_work
    record = ident.split(':', 1)[1] if ident.startswith('document:') else ident
    answer = kernel.dispatch('documents.get', {'id': record}, principal)
    if not answer.get('ok'):
        raise ValueError('That calculation cannot be read: ' + str((answer.get('error') or {}).get('message'))[:160])
    if not isinstance(changes, dict) or not changes or len(changes) > 8 or not all(isinstance(k, str) and isinstance(v, str) and 0 < len(v) <= 40 for k, v in changes.items()):
        raise ValueError('"set" names one to eight inputs, each with a number as text, for example {"B3": "320"}')
    return {'schema': SCHEMA, 'id': 'document:' + record, **datasheet_work.what_if(answer['result']['document'], changes)}


def doubt(kernel, principal, ident=None):
    """One thing cross-examined (workbench/field_doubt.py), worst first; or, with no id, every doubt and every cannot-tell on
    the desk. Exact questions put to the records: no model, nothing changed."""
    from .field_doubt import BY_KIND, desk, doubts_for
    from .field_source import read_field
    field, _ = read_field(kernel, principal)
    if ident:
        obj = field.get(ident)
        if obj is None:
            raise ValueError('Nothing on the desk has the id %s. field.read lists the ids.' % ident[:80])
        found = doubts_for(kernel, principal, obj, field)
        rows = [{'verdict': d.verdict, 'about': d.about, 'why': d.why, 'see': d.see} for d in found]
        return {'schema': SCHEMA, 'id': obj.id, 'title': obj.title, 'kind': obj.kind, 'rows': rows,
                'doubts': sum(1 for d in found if d.verdict == 'doubt'), 'cannot_tell': sum(1 for d in found if d.verdict == 'cannot tell'),
                'holds': sum(1 for d in found if d.verdict == 'holds')}
    found = desk(kernel, principal, field)
    rows = [{'title': obj.title, 'kind': obj.kind, 'id': obj.id, 'verdict': d.verdict, 'about': d.about, 'why': d.why, 'see': d.see} for obj, d in found]
    return {'schema': SCHEMA, 'rows': rows, 'doubts': sum(1 for _, d in found if d.verdict == 'doubt'),
            'cannot_tell': sum(1 for _, d in found if d.verdict == 'cannot tell'), 'looked_at': sum(1 for obj in field.objects if obj.kind in BY_KIND)}


def ripple(kernel, principal, ident, changes):
    """A cell of a sheet (or an input of a calculation) set to another value, and everything downstream said as it is and
    as it would be (workbench/field_ripple.py). A read: nothing is changed."""
    from .field_ripple import ripple as follow
    from .field_source import read_field
    field, _ = read_field(kernel, principal)
    return {'schema': SCHEMA, **follow(kernel, principal, field, ident, changes)}


def brief(kernel, principal):
    """The desk written up from the records (workbench/field_brief.py). A read: this is what the page would say."""
    from .field_brief import compose
    from .field_source import read_field
    field, _ = read_field(kernel, principal)
    return {'schema': SCHEMA, **compose(kernel, principal, field)}


def dispatch(kernel, operation, args, principal):
    if operation == 'field.brief':return brief(kernel, principal)
    if operation == 'field.brief.keep':
        from .field_brief import keep
        return {'schema': SCHEMA, **keep(kernel, principal, args.get('shown'))}
    if operation == 'field.doubt':return doubt(kernel, principal, args.get('id'))
    if operation == 'field.ripple':return ripple(kernel, principal, args['id'], args['set'])
    if operation == 'field.read':return read(kernel, principal)
    if operation == 'field.trace':return trace(kernel, principal, args['id'])
    if operation == 'field.whatif':return whatif(kernel, principal, args['id'], args['set'])
    raise ValueError('Unknown field operation')
