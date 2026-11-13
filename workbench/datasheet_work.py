"""Review a PDF table into the existing Office store and calculate a native report."""
from statistics import median

from sdk.cli.arc1cli import office_tables as tables, pdf_evidence as pdf
from . import math_model, math_units, pdf_service, project_desk as records, quantities

SHEET = 'reviewed-pdf-table-v1'
REPORT = 'pdf-sheet-calculation-v1'
MAX_ROWS = 60
HEADERS = ('Parameter', 'Value', 'Unit', 'Conditions', 'PDF page', 'Extraction')
TEXT = {'type': 'string', 'maxLength': 512}
SHA = {'type': 'string', 'minLength': 64, 'maxLength': 64}
SOURCE = {'job': records.ID, 'rect': pdf_service.REGION, 'layer': {'type': 'string', 'enum': ['native', 'ocr']}}
ROW = {'source_row': {'type': 'integer', 'minimum': 0, 'maximum': MAX_ROWS - 1},
       'parameter': TEXT, 'value': TEXT, 'unit': {'type': 'string', 'maxLength': 64}, 'conditions': TEXT}
FIELDS = {
    'office.datasheet.preview': (SOURCE, list(SOURCE)),
    'office.datasheet.create': ({**SOURCE, 'expected_digest': SHA, 'title': records.TITLE,
        'rows': {'type': 'array', 'maxItems': MAX_ROWS, 'items': {
            'type': 'object', 'additionalProperties': False, 'properties': ROW, 'required': list(ROW)}}},
        [*SOURCE, 'expected_digest', 'title', 'rows']),
    'office.datasheet.report': ({
        'id': {'type': 'string', 'minLength': 38, 'maxLength': 38}, 'expected_revision': SHA,
        'expression': {'type': 'string', 'minLength': 1, 'maxLength': 1000},
        'inputs': {'type': 'object'}, 'output_unit': {'type': 'string', 'maxLength': 64},
        'assumption': TEXT}, ['id', 'expected_revision', 'expression', 'inputs']),
    'office.datasheet.recheck': ({'id': records.ID, 'expected_revision': records.REV},
        ['id', 'expected_revision']),
}


def lines_in_region(words, region):
    x, y, width, height = region
    selected = []
    for word in words:
        left, top, w, h = word['rect']
        middle = top + h / 2
        if x <= left + w / 2 <= x + width and y <= middle <= y + height:
            selected.append((middle, left, word))
    if not selected:
        return []
    if len(selected) > 1500:
        raise ValueError('Select a smaller table region on the page')
    row_gap = median(word['rect'][3] for _, _, word in selected) * .65
    column_gap = max(.012, median(word['rect'][2] / max(1, len(word['text']))
                                 for _, _, word in selected) * 3)
    rows = []
    for middle, _, word in sorted(selected, key=lambda value: value[:2]):
        if not rows or middle - rows[-1][0] > row_gap:
            rows.append((middle, []))
        rows[-1][1].append(word)
    if len(rows) > MAX_ROWS + 1:
        raise ValueError('Select up to 60 rows on one PDF page')
    result = []
    for _, row in rows:
        cells = []
        right = -1
        for word in sorted(row, key=lambda value: value['rect'][0]):
            left, _, w, _ = word['rect']
            if not cells or left - right > column_gap:
                cells.append([])
            cells[-1].append(word['text'])
            right = max(right, left + w)
        result.append({
            'cells': [' '.join(cell) for cell in cells],
            'words': [{'text': word['text'], 'rect': word['rect']} for word in row],
            'ocr_uncertain': any(word.get('uncertain', False) for word in row),
        })
    return result


def candidate(cells):
    parameter, value, unit, conditions = (cells[0], '', '', '')
    if len(cells) == 4:
        parameter, value, unit, conditions = cells
    elif len(cells) in (2, 3):
        value = cells[1]
        matches = quantities.extract(value)
        if len(matches) == 1 and matches[0]['text'] == value and matches[0]['unit']:
            value, unit = matches[0]['value'], matches[0]['unit']
            conditions = cells[2] if len(cells) == 3 else ''
        elif len(cells) == 3:
            if quantities.resolve(cells[2]) or cells[2] == '1':
                unit = cells[2]
            else:
                conditions = cells[2]
    gaps = []
    if not value: gaps.append('Confirm the row layout and value.')
    if not unit: gaps.append('Check the unit on the original.')
    if not conditions: gaps.append('No operating condition recorded.')
    return {'parameter': parameter, 'value': value, 'unit': unit,
            'conditions': conditions, 'gaps': gaps}


def preview(kernel, args, principal):
    page = pdf_service.result(kernel, {'job': args['job']}, principal)['result'] or {}
    if page.get('status') != 'RENDERED':
        raise ValueError('Render a current admitted PDF page first')
    region = pdf.rect(args['rect'])
    layer = page.get(args['layer']) or {}
    if not layer.get('words'):
        state = 'NEEDS_OCR' if args['layer'] == 'native' else 'NO_OCR_WORDS'
        return {'state': state, 'rows': [], 'message': 'Run OCR on the page and review the recognized words against the image.'}
    rows = lines_in_region(layer['words'], region)
    if rows and [cell.casefold() for cell in rows[0]['cells']] == ['parameter', 'value', 'unit', 'conditions']:
        rows.pop(0)
    if not rows:
        raise ValueError('Select the part of the page containing the table')
    if len(rows) > MAX_ROWS:
        raise ValueError('Select up to 60 data rows')
    source = {key: page[key] for key in ('namespace', 'item', 'source_sha256', 'decision', 'name')}
    source.update(page_index=page['page']['page_index'], rect=region, layer=args['layer'], job=args['job'])
    result = {'state': 'REVIEW', 'source': source,
              'rows': [{**row, **candidate(row['cells']), 'source_row': i} for i, row in enumerate(rows)],
              'ocr_review_required': args['layer'] == 'ocr'}
    return {**result, 'digest': records.digest(result)}


def require_source(kernel, principal, source):
    with kernel.db() as db:
        _, _, _, decision = pdf_service.original(db, source, principal.identity)
    if decision['id'] != source['decision']:
        raise ValueError('PDF source review changed. Reopen its current page.')


def sheet_state(kernel, principal, origin):
    try:
        require_source(kernel, principal, origin['pdf'])
    except (ValueError, OSError):
        return {'state': 'PDF_SOURCE_REVIEW_REQUIRED', 'source_sha256': origin['pdf']['source_sha256']}
    return {'state': 'CURRENT_PDF_SOURCE', 'source_sha256': origin['pdf']['source_sha256']}


def create_sheet(kernel, args, principal):
    from .office_service import store
    prepared = preview(kernel, args, principal)
    if prepared.get('digest') != args['expected_digest']:
        raise ValueError('The PDF table preview changed. Review it again.')
    rows = args['rows']
    if not 1 <= len(rows) <= MAX_ROWS or len({r['source_row'] for r in rows}) != len(rows):
        raise ValueError('Choose distinct reviewed source rows')
    cells = {tables.address(1, i): tables.cell(value=value) for i, value in enumerate(HEADERS, 1)}
    source = prepared['source']
    reviewed = []
    for n, row in enumerate(rows, 2):
        i = row['source_row']
        if i >= len(prepared['rows']) or not row['parameter'].strip():
            raise ValueError('A reviewed row needs its source row and a parameter name')
        value = row['value'].strip()
        try:
            numeric = tables.cell('number', tables.number(value), unit=row['unit'].strip())
        except ValueError:
            numeric = tables.cell(value=value)
        data = [tables.cell(value=row['parameter']), numeric, tables.cell(value=row['unit'].strip()),
                tables.cell(value=row['conditions']), tables.cell('number', str(source['page_index'] + 1)),
                tables.cell(value='Reviewed OCR' if source['layer'] == 'ocr' else 'Reviewed native text')]
        cells.update({tables.address(n, col): cell for col, cell in enumerate(data, 1)})
        original = prepared['rows'][i]
        reviewed.append({**row, 'sheet_row': n, 'original_cells': original['cells'],
                         'source_words': original['words'], 'ocr_uncertain': original['ocr_uncertain']})
    require_source(kernel, principal, source)
    document = tables.document(args['title'], [tables.sheet('Reviewed PDF data', cells)])
    return store().create(document, origin={'profile': SHEET, 'pdf': source, 'reviewed_rows': reviewed})


def report_state(kernel, principal, derivation):
    from .office_service import store
    try:
        saved = store().get(derivation['sheet'])
        if saved['origin']['profile'] != SHEET:
            raise ValueError('The report source sheet is unavailable')
        if sheet_state(kernel, principal, saved['origin'])['state'] != 'CURRENT_PDF_SOURCE':
            return {'state': 'PDF_SOURCE_REVIEW_REQUIRED'}
        if saved['revision'] != derivation['sheet_revision']:
            return {'state': 'RECHECK_SHEET_CHANGED', 'current_revision': saved['revision']}
    except (ValueError, OSError, KeyError):
        return {'state': 'SHEET_UNAVAILABLE'}
    return {'state': 'CURRENT', 'current_revision': saved['revision']}


def report(kernel, args, principal, prior=None, replaces=None):
    from . import documents
    from .office_service import store
    saved = store().get(args['id'])
    if saved['revision'] != args['expected_revision'] or saved['origin']['profile'] != SHEET:
        raise ValueError('Choose the current reviewed PDF sheet revision')
    origin = saved['origin']
    require_source(kernel, principal, origin['pdf'])
    if not 1 <= len(args['inputs']) <= 8:
        raise ValueError('Name one to eight inputs from the Value column')
    cells = saved['document']['sheets'][0]['cells']
    source_rows = {row['sheet_row']: row for row in origin['reviewed_rows']}
    variables = {}; inputs = []
    for symbol, address in args['inputs'].items():
        if not isinstance(address, str):
            raise ValueError('An input needs a Value-column cell such as B2')
        row, column = tables.xy(address)
        if column != 2 or row not in source_rows:
            raise ValueError('Choose a source row in the Value column')
        cell = cells.get(address, {})
        if cell.get('type') != 'number' or cell.get('formula') is not None:
            raise ValueError(f'{address} needs a reviewed literal number')
        parameter = cells.get(f'A{row}', {}).get('value', '')
        if not isinstance(parameter, str) or not parameter.strip():
            raise ValueError(f'{address} needs a named parameter in the same row')
        if prior and next(item['parameter'] for item in prior['inputs'] if item['symbol'] == symbol) != parameter:
            raise ValueError(f'{address} now names a different parameter. Open the sheet and choose inputs again.')
        unit = str(cells.get(f'C{row}', {}).get('value') or '').strip()
        if not unit:
            raise ValueError(f'{address} has no reviewed unit. Fill the Unit column or enter 1 for a dimensionless value.')
        try:
            math_units.unit_spec(unit)
            factor, kernel_unit = '1', unit
        except ValueError:
            spec = quantities.resolve(unit)
            if not spec or not spec['kernel_unit']:
                raise ValueError(f'{address} needs a unit supported by the exact calculator') from None
            factor, kernel_unit = spec['factor'], spec['kernel_unit']
        conditions = str(cells.get(f'D{row}', {}).get('value') or '').strip()
        approved = source_rows[row]
        same = all(str(actual).strip() == str(approved[key]).strip() for key, actual in (
            ('parameter', parameter), ('value', cell['value']), ('unit', unit), ('conditions', conditions)))
        variables[symbol] = {'value': str(math_units.rational(cell['value']) * math_units.rational(factor)), 'unit': kernel_unit}
        inputs.append({'symbol': symbol, 'cell': address, 'parameter': parameter, 'value': cell['value'],
                       'unit': unit, 'conditions': conditions, 'basis': 'REVIEWED_PDF_ROW' if same else 'WORKING_SHEET_EDIT',
                       'source_row': approved['source_row'], 'original_cells': approved['original_cells']})
    assumptions = [args['assumption']] if args.get('assumption') else []
    expression = math_model.compile_expression(args['expression'], variables, assumptions)
    if set(expression['model']['variables']) != set(variables):
        raise ValueError('Use each named input in the calculation')
    result = math_model.evaluate(expression, output_unit=args.get('output_unit') or None)
    value = result['outputs'][0]['value'] if result['outputs'] else None
    if not isinstance(value, dict):
        raise ValueError(result.get('reason') or 'The report needs an exact numeric result')
    if store().get(saved['id'])['revision'] != saved['revision']:
        raise ValueError('The working sheet changed during calculation. Recheck it.')
    require_source(kernel, principal, origin['pdf'])
    source = origin['pdf']
    lines = [f"{args['expression']} = {value['decimal']} {value['unit']}",
             f"Exact value {value['rational']} {value['unit']}", '',
             f"Source {source['name']} · PDF page {source['page_index']+1} · reviewed {source['layer']}",
             f"Sheet {saved['document']['title']} · revision {saved['revision'][:12]}", '']
    for item in inputs:
        basis = 'reviewed row' if item['basis'] == 'REVIEWED_PDF_ROW' else 'working sheet edit'
        lines.append(f"{item['symbol']} · {item['cell']} · {item['parameter']} · {item['value']} {item['unit']} · {basis}")
        lines.append('Condition · ' + (item['conditions'] or 'Still open. Check the original and intended operating point.'))
    lines.extend(['', *('Assumption · ' + line for line in assumptions),
                  'The result applies to the named working values and declared conditions.'])
    derivation = {'profile': REPORT, 'sheet': saved['id'], 'sheet_revision': saved['revision'],
        'pdf': source, 'inputs': inputs, 'calculation': result,
        'recipe': {key: args[key] for key in ('expression', 'inputs', 'output_unit', 'assumption') if key in args}}
    title = saved['document']['title'] + ' · calculation'
    if replaces:
        # A recheck is the same calculation brought up to date, so the new page keeps the owner's name for it; where that
        # name carried the old result ("07 Settled power · 3.36 W") it carries the new one. The page it replaces is named
        # in the derivation, so a reader shows the current one and does not leave the old one waiting for ever.
        derivation['replaces'] = replaces['id'];title = replaces['title'] or title
        was = ((prior or {}).get('calculation') or {}).get('outputs') or []
        was = was[0].get('value') if was and isinstance(was[0], dict) else None
        if isinstance(was, dict) and was.get('decimal') is not None:
            said = '%s %s' % (was['decimal'], was.get('unit') or '')
            if said.strip() and said in title:title = title.replace(said, '%s %s' % (value['decimal'], value['unit']))
    document = documents.create(kernel, {'title': title,
        'text': '\n'.join(lines), 'origin': 'IMPORTED'}, principal, derivation=derivation)
    return {'document': document, 'calculation': result}


def what_if(document, changes):
    """A calculation's own recipe worked with other values for some of its inputs. Nothing is read from the sheet and nothing
    is written: the inputs are the ones the page recorded, each in its own unit, with `changes` (an input's symbol or its
    cell -> a number as text) laid over them, and the expression is the one the page was worked out with. Returns what the
    page says now, what it would give, and each input with what was set. The unit rules are report()'s own."""
    derivation = document.get('derivation') or {}
    if derivation.get('profile') != REPORT or not derivation.get('recipe'):
        raise ValueError('"What if" works on a calculation that was worked out from a reviewed sheet')
    recipe = derivation['recipe'];by_symbol = {};by_cell = {}
    for item in derivation['inputs']:
        by_symbol[str(item['symbol']).lower()] = [item];by_cell.setdefault(str(item['cell']).lower(), []).append(item)
    setting = {}
    for key, value in changes.items():
        # A symbol names one input. A cell names every input that reads it: two symbols on one cell move together.
        items = by_symbol.get(str(key).strip().lower()) or by_cell.get(str(key).strip().lower())
        if not items:
            raise ValueError('%s is not an input of this calculation. Its inputs are %s.' % (
                str(key)[:40], ', '.join('%s (%s)' % (i['symbol'], i['cell']) for i in derivation['inputs'])))
        try:
            math_units.rational(str(value).strip())
        except Exception:  # noqa: BLE001 - whatever the number parser says, the owner is told the same plain thing
            raise ValueError('%s needs a plain number, in %s' % (items[0]['symbol'], items[0]['unit'])) from None
        for item in items:setting[item['symbol']] = str(value).strip()
    variables = {};inputs = []
    for item in derivation['inputs']:
        unit = item['unit'];value = setting.get(item['symbol'], item['value'])
        try:
            math_units.unit_spec(unit)
            factor, kernel_unit = '1', unit
        except ValueError:
            spec = quantities.resolve(unit)
            if not spec or not spec['kernel_unit']:
                raise ValueError('%s needs a unit supported by the exact calculator' % item['cell']) from None
            factor, kernel_unit = spec['factor'], spec['kernel_unit']
        variables[item['symbol']] = {'value': str(math_units.rational(value) * math_units.rational(factor)), 'unit': kernel_unit}
        inputs.append({'input': item['symbol'], 'cell': item['cell'], 'parameter': item['parameter'], 'value': item['value'],
                       'set': setting.get(item['symbol'], ''), 'unit': unit})
    assumptions = [recipe['assumption']] if recipe.get('assumption') else []
    expression = math_model.compile_expression(recipe['expression'], variables, assumptions)
    result = math_model.evaluate(expression, output_unit=recipe.get('output_unit') or None)
    value = result['outputs'][0]['value'] if result['outputs'] else None
    if not isinstance(value, dict):
        raise ValueError(result.get('reason') or 'That gives no exact numeric result')
    was = (((derivation.get('calculation') or {}).get('outputs') or [{}])[0] or {}).get('value') or {}
    return {'calculation': document.get('title') or '', 'expression': recipe['expression'],
            'says_now': ('%s %s' % (was.get('decimal'), was.get('unit'))) if was.get('decimal') is not None else '',
            'would_be': '%s %s' % (value['decimal'], value['unit']), 'exact': '%s %s' % (value['rational'], value['unit']),
            'set': ', '.join('%s = %s %s' % (row['input'], row['set'], row['unit']) for row in inputs if row['set']),
            'rows': inputs, 'changed': 'nothing'}


def dispatch(kernel, operation, args, principal):
    if operation == 'office.datasheet.preview':
        return preview(kernel, args, principal)
    if operation == 'office.datasheet.create':
        return create_sheet(kernel, args, principal)
    if operation == 'office.datasheet.report':
        return report(kernel, args, principal)
    from . import documents
    from .office_service import store
    with kernel.db() as db:
        doc = documents.load(db, args['id'], principal)
    prior = doc.get('derivation', {})
    if doc['revision'] != args['expected_revision'] or prior.get('profile') != REPORT:
        raise ValueError('Open the current calculation report revision first')
    sheet = store().get(prior['sheet'])
    recipe = {**prior['recipe'], 'inputs': {item['symbol']: item['cell'] for item in prior['inputs']}}
    return report(kernel, {'id': sheet['id'], 'expected_revision': sheet['revision'], **recipe},
                  principal, prior=prior, replaces={'id': doc['id'], 'title': doc.get('title') or ''})
