"""Retained helpers (HATCH AGENT-01): the small procedures Slate uses, kept with their purpose, inputs, outputs, limits and record of use.

CONTRACT (registered by the integrator; the implementer fills this module without changing names, arguments or shapes).

A helper is a Project Desk record (kind 'helper', schema ledger.helper/1): name (unique per owner), purpose, inputs, outputs,
limits, source {kind: 'module' | 'sandboxed_python', ref}, uses, successes, failures, last_used, last_note, effectiveness
(successes / uses, None until used), created_by ('LEDGER' for built-in helpers, 'SLATE' for ones he writes later).
This pass ships module helpers only (Python functions in the tree, named by module:function); sandboxed Python helpers
written by Slate come when the model turn exists, and the record shape already allows them. The owner asked that
effective helpers be reused and improved: the record of use is what makes that possible (tool_selection and the Tool
Atlas can rank by it later).

Operations:
  helpers.list {}    -> {helpers:[records]}   read
  helpers.get  {id}  -> {helper}              read
Functions used by other modules:
  ensure_helper(kernel, principal, name, *, purpose, inputs, outputs, limits, source) -> record (idempotent by name)
  record_use(kernel, principal, name, ok, note='') -> record (increments uses and successes/failures, sets last_used)

Implementation notes (WI-B). Records live in the existing desk store (desk_records, desk_history, desk_events); every use
is a revision, so the record of use is as durable and inspectable as any other desk record. ``BUILT_IN`` describes the
module helpers this pass ships (the quantity finder, the sum model and the condition card); ``ensure_built_in`` keeps them
for an owner, idempotently, so the numbers profile and conditions.recheck can record their use. A helper's name is a
lowercase identifier; a description that changes is written as a new revision of the same record, never a second record.
"""
from __future__ import annotations
import json
import re
import time
from . import project_desk as records

KIND = 'helper'
SCHEMA = 'ledger.helper/1'
SOURCE_KINDS = ('module', 'sandboxed_python')
CREATORS = ('LEDGER', 'SLATE', 'HUMAN')
NAME = re.compile(r'[a-z][a-z0-9_]{0,63}')
MAX_NOTE = 300
MAX_DESCRIPTION = 65536
FIELDS = {
    'helpers.list': ({}, []),
    'helpers.get': ({'id': records.ID}, ['id']),
}
SCOPES = {op: 'read' for op in FIELDS}
OBSERVERS = ('helpers.list', 'helpers.get')


def built_in():
    """The module helpers this pass ships, described once here so every record says the same thing."""
    from . import quantities
    spellings = quantities.accepted_spellings()
    return {
        'quantities_from_text': {
            'purpose': 'Find the numbers with units in one paragraph, exactly where they are written, without arithmetic.',
            'inputs': 'text: one paragraph (a string; the first 200,000 characters are read)',
            'outputs': 'quantities: [{start, end, text, value (decimal string), unit (as written), unit_canonical, dimension, kernel_unit, factor, base_unit}]',
            'limits': {'matches': 'the first %d numbers of a paragraph' % quantities.MAX_MATCHES, 'accepted_spellings': spellings,
                       'plain_numbers': 'returned with unit None; currency amounts count as plain numbers',
                       'no_eval': 'a fixed pattern and a spelling table; nothing is evaluated'},
            'source': {'kind': 'module', 'ref': 'workbench.quantities:extract'}},
        'sum_model': {
            'purpose': 'Build the exact-arithmetic model that adds quantities of one dimension, for math.evaluate, and read the total back in the first unit.',
            'inputs': 'quantities: the records quantities_from_text returns, all of one dimension',
            'outputs': 'an arc.math-model/1 model (quantity nodes and a balanced tree of add nodes); total_of(evaluation, quantities) -> {value, unit, text, rational, exact}',
            'limits': {'count': 'at most %d quantities in one sum' % quantities.MAX_SUM,
                       'dimensions': 'refuses two different dimensions by name, naming both quantities; plain numbers add only with plain numbers',
                       'units_outside_the_kernel': 'mass, length, resistance, capacitance, inductance, temperature, energy, volume, pressure, force and percent are carried '
                                                   'in their base unit as dimensionless numbers and the unit is restored on the result; the model assumptions say so',
                       'meaning': 'adds what is written; whether a sum of temperatures or percentages means anything is the owner\'s call'},
            'source': {'kind': 'module', 'ref': 'workbench.quantities:sum_model'}},
        'condition_card': {
            'purpose': 'Bind a written result to the exact words it was calculated from, so an edit to those words marks the result stale.',
            'inputs': 'document, the input spans (block id, offsets, quoted words), the result, the result paragraph\'s block id',
            'outputs': 'a condition record (ledger.condition/1) in state CURRENT',
            'limits': {'inputs': 'at most %d spans; each must still read the same words at the same place on the saved revision' % quantities.MAX_MATCHES,
                       'expressions': 'sum only in this pass'},
            'source': {'kind': 'module', 'ref': 'workbench.conditions:create'}},
    }


def _rows(db, owner):
    """Every helper record of this owner, newest first: one query over the desk store."""
    out = []
    for raw, sha in db.execute('SELECT payload,digest FROM desk_records WHERE kind=? AND owner=? ORDER BY rowid DESC', (KIND, owner)):
        value = json.loads(raw)
        if records.digest(value) != sha: raise ValueError('PROJECT_DESK_RECORD_DAMAGED')
        if value.get('schema') == SCHEMA: out.append(value)
    return out


def _by_name(db, owner, name):
    return next((row for row in _rows(db, owner) if row.get('name') == name), None)


def check_description(name, fields):
    if not isinstance(name, str) or not NAME.fullmatch(name): raise ValueError('HELPER_NAME: a lowercase identifier, at most 64 characters')
    for key in ('purpose', 'inputs', 'outputs', 'limits'):
        value = fields.get(key)
        if value is None or (isinstance(value, str) and not value.strip()) or not isinstance(value, (str, list, dict)):
            raise ValueError('HELPER_' + key.upper() + '_REQUIRED: words, a list or an object')
    source = fields.get('source')
    if not isinstance(source, dict) or source.get('kind') not in SOURCE_KINDS or not isinstance(source.get('ref'), str) or not source['ref'].strip():
        raise ValueError('HELPER_SOURCE: {kind: module | sandboxed_python, ref}')
    if len(records.canonical(fields).encode()) > MAX_DESCRIPTION: raise ValueError('HELPER_DESCRIPTION_BOUND')


def ensure_helper(kernel, principal, name, *, purpose, inputs, outputs, limits, source, created_by='LEDGER'):
    """The helper record with this name for this owner: kept now when missing, re-described when the words changed, otherwise returned as is."""
    fields = {'purpose': purpose, 'inputs': inputs, 'outputs': outputs, 'limits': limits, 'source': source}
    check_description(name, fields)
    if created_by not in CREATORS: raise ValueError('HELPER_CREATED_BY: LEDGER, SLATE or HUMAN')
    fields = json.loads(records.canonical(fields))
    with kernel.db() as db:
        records.ensure(db)
        found = _by_name(db, principal.identity, name)
        if found is not None:
            if all(found.get(key) == value for key, value in fields.items()): return found
            previous = found['revision']; records.edit(found, previous); found.update(fields); found['described'] = time.time()
            return records.write(db, found, principal, 'HELPER_DESCRIBED', expected=previous)
        row = records.new(KIND, principal, schema=SCHEMA, name=name, **fields, uses=0, successes=0, failures=0, last_used=None, last_note='',
                          effectiveness=None, created_by=created_by, described=time.time())
        return records.write(db, row, principal, 'HELPER_KEPT')


def ensure_built_in(kernel, principal, names=None):
    """Keep the shipped module helpers for this owner; returns {name: record}."""
    described = built_in()
    return {name: ensure_helper(kernel, principal, name, **described[name]) for name in (names or described)}


def record_use(kernel, principal, name, ok, note=''):
    """One use, counted: uses, successes or failures, last_used, last_note and effectiveness move; the record gets a revision."""
    with kernel.db() as db:
        records.ensure(db)
        found = _by_name(db, principal.identity, name)
        if found is None: raise ValueError('HELPER_UNKNOWN: no helper named ' + str(name) + ' is kept for this owner')
        previous = found['revision']; records.edit(found, previous)
        found['uses'] = int(found.get('uses') or 0) + 1
        key = 'successes' if ok else 'failures'
        found[key] = int(found.get(key) or 0) + 1
        found['last_used'] = time.time(); found['last_note'] = ' '.join(str(note or '').split())[:MAX_NOTE]
        found['effectiveness'] = round(int(found.get('successes') or 0) / found['uses'], 4)
        return records.write(db, found, principal, 'HELPER_USED', expected=previous)


def listing(kernel, principal):
    with kernel.db() as db:
        records.ensure(db)
        return {'helpers': _rows(db, principal.identity)[:100]}


def get(kernel, ident, principal):
    with kernel.db() as db:
        records.ensure(db)
        row = records.read(db, KIND, ident, principal)
    if row.get('schema') != SCHEMA: raise ValueError('HELPER_SCHEMA_UNSUPPORTED')
    return {'helper': row}


def dispatch(kernel, op, args, principal):
    if op == 'helpers.list': return listing(kernel, principal)
    if op == 'helpers.get': return get(kernel, args['id'], principal)
    raise ValueError('Unknown helper operation')
