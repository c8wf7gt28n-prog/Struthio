import os
os.chdir('/home/user/Struthio')
def edit(p, pairs):
    s=open(p).read()
    for a,b in pairs:
        assert s.count(a)==1, (p, s.count(a), a[:80]); s=s.replace(a,b)
    open(p,'w').write(s)

# the exact calculator, asked "what if": the calculation's own recipe with other values, nothing read from the sheet, nothing written
edit('workbench/datasheet_work.py', [
("""def dispatch(kernel, operation, args, principal):
    if operation == 'office.datasheet.preview':""", '''def what_if(document, changes):
    """A calculation's own recipe worked with other values for some of its inputs. Nothing is read from the sheet and nothing
    is written: the inputs are the ones the page recorded, each in its own unit, with `changes` (an input's symbol or its
    cell -> a number as text) laid over them, and the expression is the one the page was worked out with. Returns what the
    page says now, what it would give, and each input with what was set. The unit rules are report()'s own."""
    derivation = document.get('derivation') or {}
    if derivation.get('profile') != REPORT or not derivation.get('recipe'):
        raise ValueError('"What if" works on a calculation that was worked out from a reviewed sheet')
    recipe = derivation['recipe'];named = {}
    for item in derivation['inputs']:
        named[str(item['symbol']).lower()] = item;named[str(item['cell']).lower()] = item
    setting = {}
    for key, value in changes.items():
        item = named.get(str(key).strip().lower())
        if item is None:
            raise ValueError('%s is not an input of this calculation. Its inputs are %s.' % (
                str(key)[:40], ', '.join('%s (%s)' % (i['symbol'], i['cell']) for i in derivation['inputs'])))
        try:
            math_units.rational(str(value).strip())
        except Exception:  # noqa: BLE001 - whatever the number parser says, the owner is told the same plain thing
            raise ValueError('%s needs a plain number, in %s' % (item['symbol'], item['unit'])) from None
        setting[item['symbol']] = str(value).strip()
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
    if operation == 'office.datasheet.preview':'''),
])
edit('workbench/engineering_kernel.py', [
("""from . import network_watch, network_capture  # HATCH DESK D5: network.observe and the headers-only capture, its job tool network.capture (recorded additions)""",
 """from . import network_watch, network_capture  # HATCH DESK D5: network.observe and the headers-only capture, its job tool network.capture (recorded additions)
from . import field_service  # Graphite 0.4.1: the desk as something staC can read (field.read, field.trace, field.whatif: three reads, recorded additions)"""),
("""    **network_watch.SCOPES,
    **native_projects.SCOPES,""", """    **network_watch.SCOPES,
    **field_service.SCOPES,
    **native_projects.SCOPES,"""),
("""        if op in network_watch.FIELDS:return network_watch.dispatch(self,op,a,p)""",
 """        if op in network_watch.FIELDS:return network_watch.dispatch(self,op,a,p)
        if op in field_service.FIELDS:return field_service.dispatch(self,op,a,p)"""),
])
edit('workbench/engineering_cli.py', [
("""    from .network_watch import FIELDS as NETWORK_FIELDS""", """    from .network_watch import FIELDS as NETWORK_FIELDS
    from .field_service import FIELDS as FIELD_FIELDS"""),
("""        **NETWORK_FIELDS,
        **{op: service.FIELDS[op] for op, service in PROGRAM_HANDLERS.items()},""", """        **NETWORK_FIELDS,
        **FIELD_FIELDS,
        **{op: service.FIELDS[op] for op, service in PROGRAM_HANDLERS.items()},"""),
])
edit('workbench/activity.py', [
(""" 'network.observe','network.capture.read'})""", """ 'network.observe','network.capture.read',
 # Graphite 0.4.1: the desk read as records; showing the desk is not an event
 'field.read','field.trace','field.whatif'})"""),
])
print('edits applied')
