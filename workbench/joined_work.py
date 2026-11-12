"""Source → native Calc → protected Python → native Writer, on Kernel jobs."""
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
import hashlib, json, os, time
from . import project_desk as records, problem_service as problems, math_service, schedule_math
from . import typed_artifacts as artifacts, office_math_runtime as native, experiment_runtime
from . import math_units as units, lab_service
from sdk.cli.arc1cli import office_tables as tables, office_documents as documents

FIELDS = {
    'joined.prepare': ({'receipt': records.ID, 'copy': records.ID, 'method_job': records.ID}, ['receipt', 'copy']),
    'joined.run': (math_service.OPTIONS['properties'], math_service.OPTIONS['required']),
    'joined.result': ({'job': records.ID}, ['job']),
    'joined.list': ({'problem': records.ID}, ['problem']),
    'joined.explain': ({'job': records.ID}, ['job']),
}
SCOPES = {op: 'execute' if op in ('joined.prepare', 'joined.run') else 'read' for op in FIELDS}


def components():
    names = ('joined_work.py', 'typed_artifacts.py', 'checked_methods.py', 'native_sessions.py',
        'LedgerSession.java', 'math_service.py', 'schedule_math.py', 'office_math_runtime.py',
        'LedgerOffice.java', 'experiment_runtime.py', 'engineering_kernel.py', 'engineering_cli.py','project_context.py')
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in names}


def read(kernel, kind, ident, p):
    with kernel.db() as db:
        return records.read(db, kind, ident, p)


def schedule(kernel, ident, p):
    value = schedule_math.dispatch(kernel, 'math.schedule.get', {'id': ident}, p)
    if value['applicability'] != 'CURRENT' or value['receipt']['snapshot']['state'] not in ('FEASIBLE', 'INFEASIBLE'):
        raise ValueError('JOINED_NEEDS_CURRENT_COMPLETE_SCHEDULE_RECEIPT')
    return value['receipt']


def check_action(kernel, action, p):
    from . import native_sessions, checked_methods, office_math_runtime
    if action['components'] != components():
        raise ValueError('JOINED_IMPLEMENTATION_CHANGED')
    receipt = schedule(kernel, action['schedule'], p)
    problem = math_service.current(kernel, action['problem'], p)
    problems.check_bound(problem, {'expected_revision': action['problem_revision'],
                                  'expected_context_digest': action['context_digest']})
    if records.digest(receipt) != action['schedule_digest']:
        raise ValueError('JOINED_SCHEDULE_RECEIPT_CHANGED')
    lab_service.delegated(kernel, action['copy'], p)
    native_sessions.guard_copies(kernel, [action['copy']], p)
    if action.get('method'):
        checked_methods.require_accepted(kernel, action['method'], p)
    if office_math_runtime.probe() != action['office'] or experiment_runtime.status() != action['python']:
        raise ValueError('JOINED_ENGINE_IDENTITY_CHANGED')
    if not lab_service.qualification(kernel, p)['qualified']:
        raise ValueError('JOINED_PYTHON_QUALIFICATION_REQUIRED')
    return problem, receipt


def prepare(kernel, args, p, method_ref=None):
    from . import checked_methods
    receipt = schedule(kernel, args['receipt'], p)
    problem = math_service.current(kernel, receipt['problem'], p)
    lab_service.delegated(kernel, args['copy'], p)
    if args['copy'] not in {s['copy'] for s in problem['sources']}:
        raise ValueError('JOINED_COPY_MUST_BE_A_BOUND_PROBLEM_SOURCE')
    office = native.probe(); python = experiment_runtime.status()
    if not office['available'] or not python['available'] or not lab_service.qualification(kernel, p)['qualified']:
        raise ValueError('JOINED_REQUIRES_OFFICE_AND_QUALIFIED_PYTHON')
    method = method_ref
    if args.get('method_job'):
        applied = checked_methods.result(kernel, args['method_job'], p)
        if applied['state'] != 'AVAILABLE' or applied['receipt']['receipt'] != receipt['id']:
            raise ValueError('JOINED_METHOD_RESULT_BINDING')
        method = applied['receipt']['method']
    value = records.new('joined_action', p, schema='arc.tool-action/1', profile='ledger.joined-applications/1',
        project=problem.get('project'), problem=problem['id'], problem_revision=problem['revision'],
        context_digest=problem['context_digest'], schedule=receipt['id'], schedule_digest=records.digest(receipt),
        copy=args['copy'], method=method, office=office, python=python, components=components(),
        effects=['read', 'owned_output_write'], output_names=['Working/Calculation.ods', 'Python/result.json', 'Working/Findings.docx', 'Working/Findings.pdf'])
    value['binding_digest'] = records.digest(value)
    check_action(kernel, value, p)
    with kernel.db() as db:
        return records.write(db, value, p, 'JOINED_APPLICATION_CHAIN_PREPARED_NO_EXECUTION')


def authorize(kernel, options, p):
    value = read(kernel, 'joined_action', options['action'], p)
    if value['binding_digest'] != options['expected_digest']:
        raise ValueError('JOINED_ACTION_DIGEST')
    check_action(kernel, value, p)
    return value


def calc_profile(receipt):
    snap = receipt['snapshot']; unit = snap['capacity']['unit']; cells = {}; expected = {}; inputs = {}
    def add(address, kind, value, target=None, role=None):
        cells[address] = {'kind': kind, 'value': str(value)}
        if target is not None:
            expected[address] = {'expected': str(target), 'unit': role['unit'] if role else unit, 'kind': kind,
                'formula': '=' + str(value) if kind == 'formula' else None}
        if role: inputs[address] = role
    add('A1', 'text', 'Capacity over time — declared inputs')
    add('A2', 'text', 'Source receipt ' + receipt['id'])
    add('A4', 'text', receipt['arguments']['capacity']); add('C4', 'text', unit)
    add('B4', 'number', snap['capacity']['rational'], snap['capacity']['rational'],
        {'kind': 'quantity', 'name': receipt['arguments']['capacity'], 'unit': unit})
    quantity_rows = []; row = 6
    for value in snap['inputs']:
        q, start, stop = 'B'+str(row), 'B'+str(row+1), 'B'+str(row+2)
        for address, label, number, role in [
            (q, value['quantity'], value['amount']['rational'], {'kind': 'quantity', 'name': value['quantity'], 'unit': unit}),
            (start, value['quantity']+' start', value['start'], {'kind': 'interval', 'name': value['lifetime'], 'field': 'start', 'unit': 's'}),
            (stop, value['quantity']+' stop', value['stop'], {'kind': 'interval', 'name': value['lifetime'], 'field': 'stop', 'unit': 's'})]:
            add('A'+address[1:], 'text', label); add('C'+address[1:], 'text', role['unit'])
            add(address, 'number', number, number, role)
        quantity_rows.append({'quantity': value['quantity'], 'lifetime': value['lifetime'], 'amount': q, 'start': start, 'stop': stop})
        row += 3
    row += 2; first = row
    for segment in snap['segments']:
        at = '('+segment['start']+')'
        formula = '+'.join('IF(AND('+x['start']+'<='+at+';'+x['stop']+'>'+at+');'+x['amount']+';0)' for x in quantity_rows)
        add('A'+str(row), 'text', 'Demand ['+segment['start']+','+segment['stop']+') s')
        add('B'+str(row), 'formula', formula, segment['demand']['rational']); add('C'+str(row), 'text', unit); row += 1
    peak = 'B'+str(row+1); fits = 'B'+str(row+2)
    add('A'+str(row+1), 'text', 'Peak'); add('C'+str(row+1), 'text', unit)
    add(peak, 'formula', 'MAX(B'+str(first)+':B'+str(row-1)+')', snap['peak']['rational'])
    add('A'+str(row+2), 'text', 'Fits within capacity'); add(fits, 'formula', peak+'<=B4', int(snap['fits']))
    expected[fits]['unit'] = '1'; add('C'+str(row+2), 'text', 'boolean')
    return cells, expected, {'inputs': inputs, 'allocations': quantity_rows, 'capacity': 'B4', 'peak': peak, 'fits': fits, 'unit': unit}


def checked_rows(rows, expected):
    checked = []; seen = set()
    if len(rows) != 2*len(expected): raise ValueError('JOINED_CALC_MEASUREMENT_COVERAGE')
    for row in rows:
        key = (row['phase'], row['cell'])
        if key in seen or row['phase'] not in ('CALCULATED', 'REOPENED') or row['cell'] not in expected:
            raise ValueError('JOINED_CALC_MEASUREMENT_BINDING')
        seen.add(key); want = expected[row['cell']]
        if row['error'] != '0': raise ValueError('JOINED_CALC_FORMULA_ERROR')
        if want['formula'] and row['formula'].replace(' ', '').upper() != want['formula'].replace(' ', '').upper():
            raise ValueError('JOINED_CALC_FORMULA_CHANGED')
        if not want['formula'] and row['formula'].startswith('='):
            raise ValueError('JOINED_INPUT_MUST_BE_A_SCALAR')
        observed = Decimal(row['value']); exact = Decimal(units.number_record(units.rational(want['expected']))['decimal'])
        tolerance = max(Decimal('1e-10'), abs(exact)*Decimal('1e-12'))
        if not observed.is_finite() or abs(observed-exact) > tolerance:
            raise ValueError('JOINED_CALC_DISAGREES_WITH_EXACT_RECEIPT')
        checked.append({**row, 'unit': want['unit'], 'check': 'AGREES_WITH_EXACT_SOURCE_RECEIPT', 'tolerance': str(tolerance)})
    return checked


EXPERIMENT = '''import json, sys, hashlib
from fractions import Fraction as F
p=json.load(open(sys.argv[1])); b=json.load(open('/inputs/bridge.json'))
assert hashlib.sha256(open('/inputs/Calculation.ods','rb').read()).hexdigest()==b['parent']['sha256']
v={k:F(x) for k,x in b['values'].items()}; a=b['profile']['allocations']; times=sorted({v[x[k]] for x in a for k in ('start','stop')})
peak=max(sum((v[x['amount']] for x in a if v[x['start']]<=t<v[x['stop']]),F(0)) for t in times[:-1])
capacity=v[b['profile']['capacity']]; native_peak=v[b['profile']['peak']]
agrees=abs(peak-native_peak)<=max(F(1,10**10),abs(peak)/10**12)
out={'schema':'ledger.experiment-output/1','measurements':[
 {'name':'resource_peak','value':str(peak),'unit':b['profile']['unit']},
 {'name':'resource_fits','value':peak<=capacity,'unit':'1'},
 {'name':'calc_agrees','value':agrees,'unit':'1'}],
 'assumptions':['Additive demand; fixed capacity; half-open known lifetimes.','Actual reopened Calc values; parent artifact '+b['parent']['id']+' revision '+str(b['parent']['revision'])]}
open(sys.argv[2]+'/result.json','w').write(json.dumps(out)); print('Checked actual Calc output in protected Python; peak =',peak)
'''


def progress(folder, stage, **data):
    value = {'stage': stage, **data}; temp = folder/'progress.tmp'; temp.write_text(records.canonical(value)); os.replace(temp, folder/'progress.json')
    print(json.dumps({'stage': stage}), flush=True)


def work(kernel, job, p):
    from . import work_trail
    options = job['request_spec']['calculation']; action = authorize(kernel, options, p)
    problem, receipt = check_action(kernel, action, p); folder = kernel.state/'jobs'/job['id']
    stage = folder/'Staging'; working = folder/'Working'; stage.mkdir(); working.mkdir()
    def cancelled(): return bool(kernel.record('jobs', job['id']).get('cancel') or work_trail.execution_held(kernel))
    def gate():
        if cancelled(): raise ValueError('JOINED_CANCELLED_BEFORE_COMMIT')
        check_action(kernel, action, p)
    cells, expected, profile = calc_profile(receipt)
    clean = tables.document('Declared capacity model', [tables.sheet('Capacity', {'A1': tables.cell('text', 'Declared inputs')})])
    source = stage/'Input.ods'; source.write_bytes(tables.ods_bytes(clean)[0])
    progress(folder, 'Calc recalculating declared inputs')
    calc_runtime, rows = native.calculate(source, working/'Calculation.ods', stage/'calc-native', cells, list(expected), cancelled)
    checked = checked_rows(rows, expected); gate()
    calc = artifacts.create(kernel, p, job=job['id'], file='Working/Calculation.ods', type='CALC_QUANTITY_TABLE',
        problem=problem, copy=action['copy'], method=action['method'],
        data={'profile': profile, 'measurements': checked, 'source_schedule': receipt['id'], 'source_digest': records.digest(receipt),
              'precision': 'Native binary floating point checked against exact source quantities with recorded tolerance.'})
    progress(folder, 'Calc saved and reopened', artifact=artifacts.reference(calc))
    selected = folder/'selected-inputs'; selected.mkdir()
    bridge = {'parent': artifacts.reference(calc), 'profile': profile,
              'values': {r['cell']: r['value'] for r in checked if r['phase'] == 'REOPENED'}}
    (selected/'bridge.json').write_text(records.canonical(bridge))
    (selected/'Calculation.ods').write_bytes(artifacts.path(kernel, calc).read_bytes())
    (selected/'parameters.json').write_text('{}'); (selected/'experiment.py').write_text(EXPERIMENT)
    gate(); artifacts.require_current(kernel, calc, p)
    progress(folder, 'Python checking actual Calc values')
    execution = experiment_runtime.Runner(experiment_runtime.unpack(folder)).execute(selected, folder/'Python')
    if execution['exit_code'] != 0 or execution['trap']: raise ValueError('JOINED_PYTHON_EXECUTION_FAILED: '+str(execution))
    parsed = lab_service.parse_output(folder/'Python/result.json'); values = {x['name']: x for x in parsed['measurements']}
    snap = receipt['snapshot']
    if set(values) != {'resource_peak', 'resource_fits', 'calc_agrees'} or values['calc_agrees']['value'] is not True:
        raise ValueError('JOINED_PYTHON_DID_NOT_CHECK_CALC')
    actual = units.rational(values['resource_peak']['value']); exact = units.rational(snap['peak']['rational'])
    if values['resource_peak']['unit'] != snap['peak']['unit'] or abs(actual-exact) > max(Fraction(1,10**10), abs(exact)/10**12) or values['resource_fits']['value'] != snap['fits']:
        raise ValueError('JOINED_PYTHON_DISAGREES_WITH_SOURCE_RECEIPT')
    gate(); artifacts.require_current(kernel, calc, p)
    python = artifacts.create(kernel, p, job=job['id'], file='Python/result.json', type='PYTHON_QUANTITY_OBSERVATION',
        problem=problem, copy=action['copy'], method=action['method'], parents=[calc], data={'parsed': parsed, 'execution': execution})
    progress(folder, 'Python observation checked', artifact=artifacts.reference(python))
    blocks = [documents.paragraph(problem['title'], 'Title'), documents.paragraph(problem['original_request']),
        documents.paragraph('Conditional finding', 'Heading1'),
        documents.paragraph('Under the declared inputs and supplied lifetimes, demand '+('fits' if snap['fits'] else 'does not fit')+' within capacity.'),
        documents.table([['Checked quantity', 'Value', 'Unit'], ['Peak demand', values['resource_peak']['value'], values['resource_peak']['unit']],
            ['Capacity', snap['capacity']['rational'], snap['capacity']['unit']], ['Fits', str(snap['fits']), 'boolean']]),
        documents.paragraph('Assumptions', 'Heading1')]
    blocks += [documents.paragraph(x) for x in snap['assumptions']]
    blocks += [documents.paragraph('Why', 'Heading1'), documents.paragraph('Source schedule '+receipt['id']+'; problem revision '+str(problem['revision'])+'.'),
        documents.paragraph('Calc artifact '+calc['id']+' revision '+str(calc['revision'])+' SHA-256 '+calc['sha256']+'.'),
        documents.paragraph('Python artifact '+python['id']+' revision '+str(python['revision'])+' SHA-256 '+python['sha256']+'.')]
    if problem['questions']:
        blocks += [documents.paragraph('What is missing', 'Heading1')]+[documents.paragraph(x) for x in problem['questions']]
    document = documents.document(problem['title']+' findings', blocks)
    draft = stage/'Findings-input.docx'; draft.write_bytes(documents.docx_bytes(document)[0])
    gate(); artifacts.require_current(kernel, python, p)
    progress(folder, 'Writer preparing checked findings')
    writer_runtime, text = native.writer(draft, working/'Findings.docx', working/'Findings.pdf', stage/'writer-native',
        'These findings cite actual Calc and protected Python observations for this declared case.', cancelled)
    saved = documents.parse((working/'Findings.docx').read_bytes(), 'Findings.docx')['document']
    if [b['rows'] for b in saved['blocks'] if b['kind']=='table'] != [b['rows'] for b in document['blocks'] if b['kind']=='table'] or python['id'] not in text or problem['original_request'] not in text:
        raise ValueError('JOINED_WRITER_REOPEN_BINDING_OR_CONTENT_CHANGED')
    gate(); artifacts.require_current(kernel, python, p)
    writer = artifacts.create(kernel, p, job=job['id'], file='Working/Findings.docx', type='WRITER_CHECKED_FINDINGS',
        problem=problem, copy=action['copy'], method=action['method'], parents=[python], data={'reopened': True, 'tables_checked': True})
    pdf = artifacts.create(kernel, p, job=job['id'], file='Working/Findings.pdf', type='FINDINGS_PDF',
        problem=problem, copy=action['copy'], method=action['method'], parents=[writer], data={'format': 'PDF'})
    gate()
    value = records.new('joined_result', p, id=job['id'], schema='ledger.joined-result/1', action=action['id'],
        problem=problem['id'], problem_revision=problem['revision'], context_digest=problem['context_digest'],
        schedule=receipt['id'], method=action['method'], artifacts=[artifacts.reference(x) for x in [calc, python, writer, pdf]],
        snapshot=snap, calc_runtime=calc_runtime, writer_runtime=writer_runtime,
        process_outcome='COMPLETED', check_verdict='CHECKED_APPLICATION_CHAIN', physical_qualification=False)
    with kernel.db() as db: records.write(db, value, p, 'CONNECTED_APPLICATION_CHAIN_CHECKED')
    progress(folder, 'Checked findings ready', artifact=artifacts.reference(writer))
    print(json.dumps({'outcome': 'PASS', 'artifacts': 4, 'verdict': snap['state']}))


def result(kernel, ident, p):
    from . import record_access
    job = record_access.read(kernel, 'jobs', ident, p)
    if job['tool'] != 'math.joined': raise ValueError('Not a joined application job')
    folder = kernel.state/'jobs'/ident; status = {}
    if (folder/'progress.json').exists(): status = json.loads((folder/'progress.json').read_text())
    if job['state'] != 'Completed': return {'job': ident, 'state': job['state'], 'progress': status, 'error': job.get('error'), 'files': []}
    value = read(kernel, 'joined_result', ident, p); outputs = []
    try:
        authorize(kernel, job['request_spec']['calculation'], p)
        for ref in value['artifacts']:
            artifact = artifacts.read(kernel, ref['id'], p)
            if artifacts.reference(artifact) != ref: raise ValueError('JOINED_ARTIFACT_REVISION_CHANGED')
            artifacts.require_current(kernel, artifact, p)
        state, reason = 'AVAILABLE', None
    except (ValueError, OSError) as exc:
        state, reason = 'STALE', str(exc)
    for ref in value['artifacts']:
        row = artifacts.read(kernel, ref['id'], p)
        outputs.append({'name': row['file'], 'sha256': ref['sha256'], 'bytes': row['bytes'], 'artifact': ref})
    return {'state': state, 'reason': reason, 'job': ident, 'receipt': value, 'snapshot': value['snapshot'],
            'progress': status, 'files': outputs, 'directory': str(folder)}


def dispatch(kernel, op, args, p):
    if op == 'joined.prepare': return prepare(kernel, args, p)
    if op == 'joined.run':
        authorize(kernel, args, p)
        return records.result_of(kernel, 'jobs.submit', {'tool': 'math.joined', 'calculation': args,
            'request_key': 'math-office:'+args['action'], 'timeout': 220}, p)
    if op == 'joined.result': return result(kernel, args['job'], p)
    if op == 'joined.list':
        with kernel.db() as db:
            problem = problems.load(db, args['problem'], p)
            actions = problems.related(db, problem, 'joined_action', p)
            schedules = problems.related(db, problem, 'math_schedule_result', p)
        ids = {a['id'] for a in actions}
        return {'jobs': [j for j in kernel.listing('jobs') if j['owner']==p.identity and j['tool']=='math.joined' and j.get('request_spec',{}).get('calculation',{}).get('action') in ids],
                'schedules':[s for s in schedules if s['context_digest']==problem['context_digest']]}
    value = result(kernel, args['job'], p)
    if value['state'] not in ('AVAILABLE', 'STALE'): return value
    problem = read(kernel, 'problem', value['receipt']['problem'], p); snap = value['snapshot']
    return {**value, 'finding': 'Under these declared lifetimes, peak demand is '+snap['peak']['rational']+' '+snap['peak']['unit']+
        ' against '+snap['capacity']['rational']+' '+snap['capacity']['unit']+' capacity: '+snap['state']+'.',
        'why': [artifacts.view(kernel, artifacts.read(kernel, ref['id'], p), p) for ref in value['receipt']['artifacts']],
        'alternatives': problem['candidates'], 'missing': [v['name'] for v in problem['variables'] if v['state']=='UNKNOWN'],
        'what_if': 'A changed source or lifetime requires a new checked result. Accepted methods recheck explicit preconditions before reuse.'}
