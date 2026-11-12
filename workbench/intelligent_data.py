"""Prepare bounded evidence from the context reader's revision-bound sources."""
from . import math_model, math_units, quantities, tool_selection
from .project_desk import canonical, digest


SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$', 'maxLength': 64}
CALCULATION = {
    'type': 'object', 'additionalProperties': False,
    'properties': {
        'expression': {'type': 'string', 'minLength': 1, 'maxLength': 1000},
        'inputs': {'type': 'array', 'minItems': 1, 'maxItems': 8, 'items': {
            'type': 'object', 'additionalProperties': False,
            'properties': {
                'symbol': {'type': 'string', 'pattern': '^[A-Za-z][A-Za-z0-9_]{0,39}$', 'maxLength': 40},
                'quote': {'type': 'string', 'minLength': 1, 'maxLength': 120},
                'address': {'type': 'string', 'maxLength': 600},
                'passage': SHA,
            }, 'required': ['symbol', 'quote'],
        }},
        'assumptions': {'type': 'array', 'maxItems': 4, 'items': {'type': 'string', 'minLength': 1, 'maxLength': 300}},
        'output_unit': {'type': 'string', 'minLength': 1, 'maxLength': 64},
    }, 'required': ['expression', 'inputs'],
}
READ_TOOLS = frozenset({
    'references.search', 'references.resolve', 'references.facts', 'math.evaluate', 'math.get',
    'math.units', 'reasons.get', 'conditions.get', 'artifacts.get', 'slate.context.passage',
})
MAX_CANDIDATES = 16
MAX_MODEL_BYTES = 2200
SOURCE_TEXT = frozenset({
    'SOURCE_ASSERTION_NOT_INDEPENDENT_PROOF',
    'CURRENT_ADMITTED_REFERENCE_NOT_INDEPENDENT_PROOF',
})


def typed_source(kind, source):
    """Summarize records through their own readers and applicability checks."""
    if kind == 'calculation':
        receipt = source.get('receipt') or {}
        result = receipt.get('snapshot', {})
        if source.get('applicability') == 'CURRENT' and result.get('arithmetic') == 'EXACT_RATIONAL':
            return 'Exact calculation', {
                'action': source['action']['id'], 'receipt': receipt['id'],
                'inputs': source['action'].get('variable_bindings', []), 'result': result,
            }
    if kind == 'reason':
        preview = source.get('preview', {})
        if preview.get('applicability') == 'CURRENT_WITHIN_DECLARED_GRAPH':
            return 'Declared dependency graph', {key: preview[key] for key in (
                'state', 'target', 'coverage', 'assumption_context', 'inactive_atoms', 'observations', 'rule_review')}
    if kind == 'artifact' and source.get('applicability') == 'CURRENT':
        artifact = source['artifact']
        return 'Checked application output', {key: artifact[key] for key in (
            'id', 'type', 'revision', 'sha256', 'parents', 'problem_revision', 'data', 'authority')}
    if kind == 'condition':
        card = source.get('condition', {})
        if card.get('state') == 'CURRENT' and card.get('document_revision') == source.get('document_revision_now'):
            return 'Current condition', {key: card.get(key) for key in (
                'document', 'document_revision', 'inputs', 'expression', 'result', 'method')}
    return None


TYPED_KINDS = frozenset({'calculation', 'reason', 'artifact', 'condition'})


def source_quantities(passage):
    if passage['kind'] != 'SOURCE' or passage.get('binding') is None or passage['authority'] not in SOURCE_TEXT:
        return []
    return quantities.extract(passage['text'])


def observed_calculation(request, corpus, extracted):
    inputs = []
    variables = {}
    gaps = []
    for spec in request['inputs']:
        symbol = spec['symbol']
        matches = []
        for passage in corpus:
            if spec.get('address') and spec['address'] != passage.get('address'):
                continue
            if spec.get('passage') and spec['passage'] != passage['id']:
                continue
            matches.extend((passage, quantity) for quantity in extracted.get(passage['id'], ())
                           if quantity['text'] == spec['quote'])
        if len(matches) != 1:
            message = 'Choose the source or passage for' if matches else 'Find the exact source quote for'
            gaps.append(f'{message} {symbol} ({spec["quote"]}).')
            continue
        passage, quantity = matches[0]
        if quantity['unit'] and quantity['kernel_unit'] is None:
            gaps.append(f'The exact expression engine needs a supported unit for {symbol} ({quantity["unit"]}).')
            continue
        unit = quantity['kernel_unit'] or '1'
        value = math_units.rational(quantity['value']) * math_units.rational(quantity['factor'])
        variables[symbol] = {'value': str(value), 'unit': unit}
        inputs.append({
            'symbol': symbol, 'quote': quantity['text'], 'value': quantity['value'], 'unit': quantity['unit'],
            'passage': passage['id'], 'source_revision': passage.get('source_revision'),
            'span': [quantity['start'], quantity['end']], 'role': 'OWNER_NAMED_INPUT',
        })
    record = {
        'expression': request['expression'], 'inputs': inputs,
        'assumptions': request.get('assumptions', []),
        'source_ids': list(dict.fromkeys(row['passage'] for row in inputs)),
        'state': 'NEEDS_INPUT', 'gaps': gaps,
    }
    if gaps:
        return record
    try:
        model = math_model.compile_expression(request['expression'], variables, record['assumptions'])
        if set(model['model']['variables']) != set(variables):
            raise ValueError('Use each declared input in the expression')
        result = math_model.evaluate(model, output_unit=request.get('output_unit'))
        if not result['outputs'] or any(row['state'] != 'EXACT' for row in result['outputs']):
            raise ValueError(result.get('reason', 'The expression has an unresolved domain condition'))
    except (ValueError, ArithmeticError) as exc:
        record['gaps'].append(str(exc)[:300])
        return record
    return {**record, 'state': 'EXACT', 'result': result, 'method': 'math.evaluate/EXACT_RATIONAL',
            'authority': 'EXACT_CONSEQUENCE_OF_DECLARED_INPUT_ROLES_AND_CONDITIONS'}


def prepare(requests, corpus, question):
    from .addresses import parse
    from .engineering_cli import schemas
    from .engineering_kernel import CAPABILITIES

    if len(requests) > 4:
        raise ValueError('Prepare at most four exact calculations')
    extracted = {p['id']: source_quantities(p) for p in corpus} if requests else {}
    calculations = []
    for request in requests:
        inputs = request['inputs']
        if not 1 <= len(inputs) <= 8 or len(request.get('assumptions', [])) > 4:
            raise ValueError('Use one to eight named inputs and at most four conditions')
        if len({row['symbol'] for row in inputs}) != len(inputs):
            raise ValueError('Calculation symbols must be distinct')
        normalized = []
        for row in inputs:
            if 'address' in row:
                kind, ident = parse(row['address'])
                row = {**row, 'address': f'{kind}:{ident}'}
            normalized.append(row)
        try:
            calculations.append(observed_calculation({**request, 'inputs': normalized}, corpus, extracted))
        except (ValueError, ArithmeticError) as exc:
            calculations.append({'expression': request['expression'], 'state': 'NEEDS_INPUT',
                                 'source_ids': [], 'inputs': [], 'gaps': [str(exc)[:300]]})
    definitions = schemas()
    tools = tool_selection.describe(tool_selection.relevant(question, {
        op: CAPABILITIES[op] for op in sorted(READ_TOOLS) if CAPABILITIES.get(op) == 'read'
    }, definitions, limit=4))
    return {
        'requests': requests, 'calculations': calculations, 'tools': tools,
        'pinned': list(dict.fromkeys(source for row in calculations if row['state'] == 'EXACT'
                                    for source in row['source_ids'])),
    }


def selected_details(selected, bindings):
    candidates = []
    facts = []
    for passage in selected:
        if len(candidates) < MAX_CANDIDATES:
            for value in source_quantities(passage):
                if value['unit'] and len(value['text']) <= 120:
                    candidates.append({key: value[key] for key in ('text', 'value', 'unit', 'dimension', 'start', 'end')}
                                      | {'passage': passage['id'], 'role': 'UNRESOLVED_SOURCE_MENTION'})
                if len(candidates) == MAX_CANDIDATES:
                    break
        if not passage.get('address', '').startswith('packet:') or not passage.get('passage_id'):
            continue
        packet = bindings[passage['binding']]['snapshot']['object']
        for fact in packet['facts']:
            if len(facts) == MAX_CANDIDATES:
                break
            if fact['passage'] == passage['passage_id']:
                facts.append({key: fact[key] for key in ('id', 'subject', 'property', 'variant', 'conditions',
                              'quantity', 'role', 'polarity', 'quote')}
                             | {'source_ids': [passage['id']]})
    return {'quantities': candidates, 'facts': facts}


def for_model(preparation, aliases):
    """Admit complete evidence rows only while their cited passages are supplied."""
    if preparation is None:
        return {}
    alias_for = {passage['id']: alias for alias, passage in aliases.items()}
    data = {}

    def add(group, row):
        rows = data.get(group, []) + [row]
        if len(canonical({**data, group: rows}).encode()) <= MAX_MODEL_BYTES:
            data[group] = rows

    for record in preparation['calculations']:
        if record['state'] != 'EXACT':
            for gap in record['gaps']:
                add('open_conditions', gap)
            continue
        if any(source not in alias_for for source in record['source_ids']):
            add('open_conditions', 'A calculation is omitted because its source passages do not fit this turn.')
            continue
        add('exact_calculations', {
            'expression': record['expression'], 'assumptions': record['assumptions'],
            'inputs': [{'symbol': row['symbol'], 'quote': row['quote'], 'source': alias_for[row['passage']]}
                       for row in record['inputs']],
            'outputs': record['result']['outputs'], 'method': record['method'],
            'scope': 'DECLARED_INPUT_ROLES_AND_CONDITIONS',
        })
    for fact in preparation['facts']:
        if all(source in alias_for for source in fact['source_ids']):
            add('reviewed_source_facts', {key: value for key, value in fact.items() if key not in ('id', 'source_ids')}
                | {'sources': [alias_for[source] for source in fact['source_ids']]})
    for value in preparation['quantities']:
        if value['passage'] in alias_for:
            add('quantities_to_interpret', {'quote': value['text'], 'source': alias_for[value['passage']]})
    for tool in preparation['tools']:
        add('available_read_operations', tool['operation'])
    return data
