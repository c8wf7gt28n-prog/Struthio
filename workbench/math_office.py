"""Auditable Calc cells and Writer findings from one validated math result."""
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from sdk.cli.arc1cli import office_tables as tables,office_documents as documents
from . import math_model as core,office_math_runtime as native
from .math_units import unit_spec,canonical_unit,rational,number_record


def workbook(ir, assignments, output_unit=None):
    actual,missing=core.values(ir,assignments)
    if missing:raise ValueError('OFFICE_MISSING_MODEL_VALUES')
    cells={};row=5;variables={};locations={};measurements={}
    def set_cell(address,kind,value):cells[address]={'kind':kind,'value':str(value)}
    set_cell('A1','text','Declared model calculation')
    set_cell('A2','text','Assumptions: '+'; '.join(ir['model']['assumptions']))
    for name,variable in ir['model']['variables'].items():
        value=assignments.get(name,variable.get('value'))
        if value is None:raise ValueError('OFFICE_MISSING_MODEL_VALUES')
        set_cell('A'+str(row),'text',name);set_cell('B'+str(row),'number',value);set_cell('C'+str(row),'text',variable['unit'])
        variables[name]='B'+str(row);row+=1
    row+=2
    for node in ir['model']['nodes']:
        ident=node['id'];op=node['op'];address='B'+str(row);locations[ident]=address;sig=ir['signatures'][ident]
        set_cell('A'+str(row),'text',ident+' '+(node.get('name') or op));set_cell('C'+str(row),'text','boolean' if sig['kind']=='boolean' else canonical_unit(sig['dimension']))
        if op=='quantity':set_cell(address,'number',str(rational(node['value'])*unit_spec(node['unit'])[1]))
        elif op=='variable':set_cell(address,'formula',variables[node['name']]+'*('+str(unit_spec(ir['model']['variables'][node['name']]['unit'])[1])+')')
        elif op=='neg':set_cell(address,'formula','-'+locations[node['argument']])
        elif op=='power':set_cell(address,'formula','('+locations[node['argument']]+')^('+str(node['exponent'])+')')
        else:
            operator={'add':'+','sub':'-','mul':'*','div':'/','eq':'=','ne':'<>','lt':'<','le':'<=','gt':'>','ge':'>='}[op]
            set_cell(address,'formula','('+locations[node['left']]+')'+operator+'('+locations[node['right']]+')')
        row+=1
    row+=2;nodes={n['id']:n for n in ir['model']['nodes']}
    for ident in ir['model']['outputs']:
        sig=ir['signatures'][ident];unit=output_unit or sig['unit']
        targets=[(ident,ident,unit)] if sig['kind']=='quantity' else [(ident,ident,'boolean'),(ident+' left',nodes[ident]['left'],unit),(ident+' right',nodes[ident]['right'],unit)]
        for label,target,unit in targets:
            address='B'+str(row);set_cell('A'+str(row),'text','Result '+label);set_cell('C'+str(row),'text',unit)
            factor=Fraction(1) if unit=='boolean' else unit_spec(unit)[1]
            value=actual[target]
            expected=Fraction(int(value)) if type(value) is bool else value/factor
            set_cell(address,'formula',locations[target]+'/('+str(factor)+')')
            measurements[address]={'expected':str(expected),'unit':unit,'label':label,'formula':'='+cells[address]['value']};row+=1
    return cells,measurements


def check_measurements(rows,expected):
    if len(rows)!=2*len(expected):raise ValueError('OFFICE_MEASUREMENT_COVERAGE')
    seen=set();checked=[]
    for row in rows:
        key=(row['phase'],row['cell'])
        if key in seen or row['phase'] not in ('CALCULATED','REOPENED') or row['cell'] not in expected:raise ValueError('OFFICE_MEASUREMENT_BINDING')
        seen.add(key);target=expected[row['cell']]
        if row['error']!='0' or row['formula'].replace(' ','').upper()!=target['formula'].replace(' ','').upper():raise ValueError('OFFICE_FORMULA_ERROR_OR_IDENTITY_CHANGED')
        observed=Decimal(row['value']);desired=Decimal(number_record(rational(target['expected']))['decimal'])
        tolerance=max(Decimal('0.0000000001'),abs(desired)*Decimal('0.000000000001'))
        if not observed.is_finite() or abs(observed-desired)>tolerance:raise ValueError('OFFICE_RESULT_DISAGREES_WITH_EXACT_MODEL')
        checked.append({**row,**target,'absolute_tolerance':str(tolerance),'check':'AGREES_WITH_EXACT_IR'})
    return checked


def findings(problem,action,receipt,measurements):
    model=action['model'];result=receipt['snapshot'];evaluation=result.get('evaluation',result)
    paragraphs=[documents.paragraph('These findings apply to the declared model and assumptions. Unanswered questions remain listed below.'),
        documents.paragraph('Question','Heading1'),documents.paragraph(problem['original_request']),
        documents.paragraph('Declared assumptions','Heading1')]
    paragraphs.extend(documents.paragraph(text) for text in model['assumptions'])
    paragraphs.append(documents.paragraph('Results','Heading1'))
    rows=[['Output','Value','Unit or condition']]
    for output in evaluation.get('outputs',[]):
        if output['kind']=='quantity' and output.get('value'):
            v=output['value'];label='Modeled power' if v['dimension']=={'voltage':1,'current':1} else 'Calculated quantity'
            rows.append([label,v['decimal'] if v['decimal_exact'] else v['rational'],v['unit']])
        elif output['kind']=='boolean' and 'value' in output:
            left,right=output.get('left',{}),output.get('right',{})
            label='Memory condition' if left.get('dimension')=={'memory':1} else 'Declared condition'
            rows.append([label,'Met' if output['value'] else 'Not met',left.get('decimal','')+' '+left.get('unit','')+' compared with '+right.get('decimal','')+' '+right.get('unit','')])
    paragraphs.append(documents.table(rows))
    paragraphs.append(documents.paragraph('Open questions','Heading1'))
    paragraphs.extend(documents.paragraph(text) for text in problem['questions'])
    paragraphs.append(documents.paragraph('Observation','Heading1'))
    paragraphs.append(documents.paragraph('Calc explicitly recalculated the declared cells and the saved workbook was reopened. '+str(len(measurements))+' formula measurements agreed with the exact model within the recorded precision.'))
    paragraphs.append(documents.paragraph('Problem revision '+str(problem['revision'])+'. Calculation receipt '+receipt['id']+'. Source-bound records retain the complete digests.'))
    return documents.document(problem['title']+' findings',paragraphs)


def run(folder,problem,action,receipt,cancelled=None):
    folder=Path(folder);stage=folder/'math-office';stage.mkdir();ir=core.validate(action['model'])
    result=receipt['snapshot'];assignments=result.get('assignments',{});evaluation=core.evaluate(ir,assignments,action.get('output_unit'))
    if evaluation['state'] not in ('FEASIBLE','INFEASIBLE'):raise ValueError('OFFICE_REQUIRES_COMPLETE_VALID_MODEL_VALUES')
    cells,expected=workbook(ir,assignments,action.get('output_unit'))
    clean=tables.document('Declared calculation',[tables.sheet('Calculation',{'A1':tables.cell('text','Declared model calculation')})])
    source=stage/'Input.ods';source.write_bytes(tables.ods_bytes(clean)[0]);calc=folder/'Calculation.ods'
    calc_runtime,rows=native.calculate(source,calc,stage/'calc-native',cells,list(expected),cancelled)
    checked=check_measurements(rows,expected)
    reopened=tables.parse(calc.read_bytes(),calc.name)['document']
    parsed=reopened['sheets'][0]['cells']
    for address in expected:
        if address not in parsed or not parsed[address]['formula']:raise ValueError('OFFICE_SAVED_FORMULA_MISSING')
    document=findings(problem,action,receipt,checked);raw,projection=documents.docx_bytes(document)
    draft=stage/'Findings-input.docx';draft.write_bytes(raw);writer=folder/'Findings.docx';pdf=folder/'Findings.pdf'
    appended='Native Writer saved and reopened these findings after the checked Calc calculation.'
    writer_runtime,text=native.writer(draft,writer,pdf,stage/'writer-native',appended,cancelled)
    if appended not in text or problem['original_request'] not in text:raise ValueError('WRITER_NATIVE_REOPEN_CONTENT_CHANGED')
    saved=documents.parse(writer.read_bytes(),writer.name)
    expected_tables=[b['rows'] for b in document['blocks'] if b['kind']=='table']
    if [b['rows'] for b in saved['document']['blocks'] if b['kind']=='table']!=expected_tables:raise ValueError('WRITER_REOPEN_TABLE_CHANGED')
    return {'calc_runtime':calc_runtime,'writer_runtime':writer_runtime,'measurement':checked,
        'writer_reopened':True,'writer_table_reopened':True,'losses':projection['losses']+saved['losses']+[
            {'path':'calculation','reason':'CALC_BINARY_FLOATING_POINT_CHECKED_WITH_ABSOLUTE_OR_RELATIVE_TOLERANCE'},
            {'path':'workbook','reason':'GENERATED_DECLARED_CELL_PROFILE_NOT_A_LOSSLESS_IMPORT_OF_ARBITRARY_WORKBOOKS'}],
        'files':[{'name':p.name,'sha256':tables.sha(p.read_bytes()),'bytes':p.stat().st_size} for p in (calc,writer,pdf)],
        'evaluation':evaluation,'process_outcome':'COMPLETED','check_verdict':'AGREES_ON_DECLARED_CASE',
        'applicability':'SOURCE_BOUND_MODEL_ONLY','physical_qualification':False}
