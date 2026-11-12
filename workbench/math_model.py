"""Bounded typed mathematical IR. No eval, string backend parser or user code.

Values use Fraction in base units. Declared denominators survive cancellation.
The same evaluator supplies calculation, witness checks and sampled graphs.
"""
from __future__ import annotations
import ast
import copy
import re
from fractions import Fraction
from .math_units import unit_spec, rational, bounded, quantity_record, canonical_unit, number_record
from .project_desk import canonical, digest

SCHEMA = 'arc.math-model/1'
RELATIONS = {'eq','ne','lt','le','gt','ge'}


class MathError(ValueError):
    def __init__(self, code, detail):super().__init__(detail); self.code=code


def fail(code, detail):raise MathError(code,detail)


def validate(model):
    if len(canonical(model).encode())>65536:fail('UNSUPPORTED','Model exceeds 64 KiB')
    if not isinstance(model,dict) or set(model)-{'schema','variables','nodes','outputs','constraints','assumptions'} or model.get('schema')!=SCHEMA:
        fail('UNSUPPORTED','Expected a typed mathematical model')
    if not {'variables','nodes','outputs'}<=set(model):fail('UNSUPPORTED','Missing model fields')
    model=copy.deepcopy(model); model.setdefault('constraints',[]);model.setdefault('assumptions',[])
    variables=model['variables']; nodes=model['nodes']
    if not isinstance(variables,dict) or len(variables)>16 or not isinstance(nodes,list) or not 1<=len(nodes)<=128:fail('UNSUPPORTED','At most 16 variables and 128 nodes')
    for name,variable in variables.items():
        if not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,63}',name) or not isinstance(variable,dict) or set(variable)-{'unit','value','domain','lower','upper'} or 'unit' not in variable:
            fail('UNSUPPORTED','Invalid declared variable')
        unit_spec(variable['unit']);variable.setdefault('domain','real')
        if variable['domain'] not in ('real','integer'):fail('UNSUPPORTED','Only real and integer scalar domains are admitted')
        for key in ('value','lower','upper'):
            if key in variable:rational(variable[key])
        if 'lower' in variable and 'upper' in variable and rational(variable['lower'])>rational(variable['upper']):fail('DOMAIN_ERROR','Reversed variable bounds')
        if 'value' in variable:
            value=rational(variable['value'])
            if variable['domain']=='integer' and value.denominator!=1:fail('DOMAIN_ERROR','Integer variable has a fractional value')
            if ('lower' in variable and value<rational(variable['lower'])) or ('upper' in variable and value>rational(variable['upper'])):
                fail('DOMAIN_ERROR','A declared value is outside its domain')
    signatures={}; depths={}; domains=[]
    for node in nodes:
        if not isinstance(node,dict) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,63}',node.get('id','')) or node['id'] in signatures:fail('UNSUPPORTED','Unique ordered node IDs required')
        op=node.get('op'); ident=node['id']; required={'id','op'}; children=[]
        if op=='quantity':
            required|={'value','unit'};rational(node.get('value'));dimension,_=unit_spec(node.get('unit'));unit=node['unit'];degree=0;kind='quantity'
        elif op=='variable':
            required.add('name')
            if node.get('name') not in variables:fail('UNSUPPORTED','Undeclared variable')
            variable=variables[node['name']];dimension,_=unit_spec(variable['unit']);unit=variable['unit'];degree=0 if 'value' in variable else 1;kind='quantity'
        elif op in {'add','sub','mul','div',*RELATIONS}:
            required|={'left','right'};children=[node.get('left'),node.get('right')]
            if any(child not in signatures or signatures[child]['kind']!='quantity' for child in children):fail('UNSUPPORTED','Arithmetic operands must be earlier quantity nodes')
            left,right=[signatures[child] for child in children];a,b=left['dimension'],right['dimension']
            if op in {'add','sub',*RELATIONS} and a!=b:fail('DIMENSION_MISMATCH','Cannot '+op+' incompatible quantities')
            dimension=tuple(x+y if op=='mul' else x-y for x,y in zip(a,b)) if op in ('mul','div') else a
            unit=left['unit'] if op in ('add','sub',*RELATIONS) else canonical_unit(dimension)
            degree=max(left['degree'],right['degree']) if op in ('add','sub',*RELATIONS) else left['degree']+right['degree']
            kind='boolean' if op in RELATIONS else 'quantity'
            if op=='div':domains.append({'node':ident,'denominator':node['right'],'condition':'DENOMINATOR_NONZERO'})
        elif op in ('neg','power'):
            required.add('argument');children=[node.get('argument')]
            if children[0] not in signatures or signatures[children[0]]['kind']!='quantity':fail('UNSUPPORTED','Expected an earlier quantity')
            source=signatures[children[0]];exponent=1
            if op=='power':
                required.add('exponent');exponent=node.get('exponent')
                if type(exponent) is not int or not -4<=exponent<=4:fail('UNSUPPORTED','Integer exponents must be between -4 and 4')
                if exponent<0:domains.append({'node':ident,'denominator':node['argument'],'condition':'DENOMINATOR_NONZERO'})
            dimension=tuple(x*exponent for x in source['dimension']);degree=source['degree']*abs(exponent);unit=canonical_unit(dimension);kind='quantity'
        else:fail('UNSUPPORTED','Unsupported mathematical node: '+str(op))
        if set(node)!=required:fail('UNSUPPORTED','Unexpected node fields')
        depth=1+max((depths[child] for child in children),default=0)
        if depth>24 or degree>4 or any(abs(p)>8 for p in dimension):fail('UNSUPPORTED','Expression depth, degree or dimension bound exceeded')
        # Generated compound units must themselves be representable by this profile.
        unit_spec(unit)
        signatures[ident]={'kind':kind,'dimension':tuple(dimension),'unit':unit,'degree':degree};depths[ident]=depth
    for key,maximum in [('outputs',16),('constraints',32),('assumptions',16)]:
        if not isinstance(model[key],list) or len(model[key])>maximum:fail('UNSUPPORTED','Invalid bounded '+key)
    if not model['outputs'] or any(i not in signatures for i in model['outputs']):fail('UNSUPPORTED','Select existing output nodes')
    if any(i not in signatures or signatures[i]['kind']!='boolean' for i in model['constraints']):fail('UNSUPPORTED','Constraints must reference relation nodes')
    if any(not isinstance(s,str) or not s.strip() or len(s)>1000 for s in model['assumptions']):fail('UNSUPPORTED','Declare meaningful bounded assumptions')
    return {'schema':'arc.validated-math/1','model':model,'model_digest':digest(model),'signatures':signatures,'domain_conditions':domains}


def values(ir, assignments=None):
    assigned=assignments or {};variables=ir['model']['variables']; result={};missing=set()
    if set(assigned)-set(variables):fail('UNSUPPORTED','Assignment to an undeclared variable')
    for node in ir['model']['nodes']:
        op=node['op'];ident=node['id']
        if op=='quantity':value=rational(node['value'])*unit_spec(node['unit'])[1]
        elif op=='variable':
            v=variables[node['name']]; raw=assigned.get(node['name'],v.get('value'))
            if raw is None:value=None;missing.add(node['name'])
            else:
                value=rational(raw)
                if v['domain']=='integer' and value.denominator!=1:fail('DOMAIN_ERROR','Integer domain violated')
                if ('lower' in v and value<rational(v['lower'])) or ('upper' in v and value>rational(v['upper'])):fail('DOMAIN_ERROR','Variable bound violated')
                value*=unit_spec(v['unit'])[1]
        elif op in ('neg','power'):
            a=result[node['argument']]
            if op=='power' and node['exponent']<0 and a==0:fail('DOMAIN_ERROR','Negative power of zero at '+ident)
            value=None if a is None else -a if op=='neg' else a**node['exponent']
        else:
            a,b=result[node['left']],result[node['right']]
            if op=='div' and b==0:fail('DOMAIN_ERROR','Zero denominator at '+ident)
            if a is None or b is None:value=None
            elif op=='add':value=a+b
            elif op=='sub':value=a-b
            elif op=='mul':value=a*b
            elif op=='div':value=a/b
            elif op=='eq':value=a==b
            elif op=='ne':value=a!=b
            elif op=='lt':value=a<b
            elif op=='le':value=a<=b
            elif op=='gt':value=a>b
            elif op=='ge':value=a>=b
        if isinstance(value,Fraction):bounded(value)
        result[ident]=value
    return result,sorted(missing)


def evaluate(ir, assignments=None, output_unit=None):
    try:actual,missing=values(ir,assignments)
    except MathError as exc:return {'state':exc.code,'reason':str(exc),'outputs':[],'domain_conditions':ir['domain_conditions']}
    outputs=[]
    by_id={n['id']:n for n in ir['model']['nodes']}
    for ident in ir['model']['outputs']:
        signature=ir['signatures'][ident]; value=actual[ident]
        row={'node':ident,'kind':signature['kind'],'state':'UNKNOWN' if value is None else 'EXACT'}
        if value is not None:
            if signature['kind']=='quantity':row['value']=quantity_record(value,signature['dimension'],output_unit or signature['unit'])
            else:
                row['value']=value;node=by_id[ident]
                for side in ('left','right'):
                    sig=ir['signatures'][node[side]]
                    row[side]=quantity_record(actual[node[side]],sig['dimension'],output_unit or signature['unit'])
        outputs.append(row)
    constraints=[{'node':i,'value':actual[i]} for i in ir['model']['constraints']]
    state='INFEASIBLE' if any(v['value'] is False for v in constraints) else 'UNKNOWN' if missing else 'FEASIBLE'
    return {'state':state,'outputs':outputs,'constraints':constraints,'missing':missing,
        'assumptions':ir['model']['assumptions'],'domain_conditions':ir['domain_conditions'],
        'model_digest':ir['model_digest'],'arithmetic':'EXACT_RATIONAL','scope':'DECLARED_MODEL_CONSEQUENCE', 'physical_qualification':False}


def compile_expression(expression, variables, assumptions=None, constraint=False):
    if not isinstance(expression,str) or not 1<=len(expression)<=1000:fail('UNSUPPORTED','Expression length bound')
    try:tree=ast.parse(expression,mode='eval')
    except (SyntaxError,RecursionError) as exc:fail('UNSUPPORTED','Use ordinary arithmetic or one comparison')
    if sum(1 for _ in ast.walk(tree))>128:fail('UNSUPPORTED','Expression node bound')
    nodes=[];selected={}
    def add(op,**args):
        ident='n'+str(len(nodes));nodes.append({'id':ident,'op':op,**args});return ident
    def visit(node):
        if isinstance(node,ast.Name):
            if node.id not in variables:fail('MISSING_INPUT','No declared scalar variable named '+node.id)
            selected[node.id]=copy.deepcopy(variables[node.id]);return add('variable',name=node.id)
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):
            raw=ast.get_source_segment(expression,node);rational(raw);return add('quantity',value=raw,unit='1')
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            result=visit(node.operand);return result if isinstance(node.op,ast.UAdd) else add('neg',argument=result)
        if isinstance(node,ast.BinOp):
            if isinstance(node.op,ast.Pow):
                exponent=node.right.value if isinstance(node.right,ast.Constant) and type(node.right.value) is int else -node.right.operand.value if isinstance(node.right,ast.UnaryOp) and isinstance(node.right.op,ast.USub) and isinstance(node.right.operand,ast.Constant) and type(node.right.operand.value) is int else None
                if exponent is None:fail('UNSUPPORTED','Only small integer powers are supported')
                return add('power',argument=visit(node.left),exponent=exponent)
            operations={ast.Add:'add',ast.Sub:'sub',ast.Mult:'mul',ast.Div:'div'}
            if type(node.op) not in operations:fail('UNSUPPORTED','Unsupported arithmetic operator')
            return add(operations[type(node.op)],left=visit(node.left),right=visit(node.right))
        if isinstance(node,ast.Compare) and len(node.ops)==1:
            operations={ast.Eq:'eq',ast.NotEq:'ne',ast.Lt:'lt',ast.LtE:'le',ast.Gt:'gt',ast.GtE:'ge'}
            if type(node.ops[0]) not in operations:fail('UNSUPPORTED','Unsupported comparison')
            return add(operations[type(node.ops[0])],left=visit(node.left),right=visit(node.comparators[0]))
        fail('UNSUPPORTED','Calls, attributes, indexing and executable code are not mathematical nodes')
    output=visit(tree.body)
    return validate({'schema':SCHEMA,'variables':selected,'nodes':nodes,'outputs':[output],
        'constraints':[output] if constraint or nodes[-1]['op'] in RELATIONS else [],'assumptions':assumptions or []})


def affine(ir, free=()):
    """Return base-unit constants and coefficients, or reject outside QF_LIRA."""
    forms={}
    def combine(a,b,sign=1):
        co=dict(a[1])
        for k,v in b[1].items():co[k]=co.get(k,Fraction(0))+sign*v
        return a[0]+sign*b[0],{k:v for k,v in co.items() if v}
    def scale(a,m):return a[0]*m,{k:v*m for k,v in a[1].items() if v*m}
    for n in ir['model']['nodes']:
        op=n['op']
        if op=='quantity':form=(rational(n['value'])*unit_spec(n['unit'])[1],{})
        elif op=='variable':
            v=ir['model']['variables'][n['name']];factor=unit_spec(v['unit'])[1]
            form=(rational(v['value'])*factor,{}) if 'value' in v and n['name'] not in free else (Fraction(0),{n['name']:factor})
        elif op=='neg':form=scale(forms[n['argument']],-1)
        elif op=='power':
            a=forms[n['argument']];power=n['exponent']
            if not a[1]:
                if a[0]==0 and power<0:fail('DOMAIN_ERROR','Zero denominator')
                form=(a[0]**power,{})
            elif power==1:form=a
            elif power==0:form=(Fraction(1),{})
            else:fail('UNSUPPORTED','Z3 fragment admits linear arithmetic only')
        else:
            a,b=forms[n['left']],forms[n['right']]
            if op in ('add','sub',*RELATIONS):form=combine(a,b,-1 if op!='add' else 1)
            elif op=='mul':
                if a[1] and b[1]:fail('UNSUPPORTED','Variable products are outside the linear fragment')
                form=scale(a,b[0]) if not b[1] else scale(b,a[0])
            elif op=='div':
                if b[1]:fail('UNSUPPORTED','A variable denominator is outside the linear fragment')
                if b[0]==0:fail('DOMAIN_ERROR','Zero denominator')
                form=scale(a,1/b[0])
        forms[n['id']]=form
    return forms


def witness_check(ir, assignments):
    try:
        for name,value in assignments.items():
            variable=ir['model']['variables'][name]
            if 'value' in variable and rational(value)!=rational(variable['value']):return False
            exact=rational(value)
            if variable['domain']=='integer' and exact.denominator!=1:return False
            if ('lower' in variable and exact<rational(variable['lower'])) or ('upper' in variable and exact>rational(variable['upper'])):return False
        actual,missing=values(ir,assignments)
        return not missing and all(actual[i] is True for i in ir['model']['constraints'])
    except (ValueError,ZeroDivisionError):return False


def sweep(ir, variable, start, stop, count=81, output_unit=None):
    if variable not in ir['model']['variables'] or type(count) is not int or not 2<=count<=201:fail('UNSUPPORTED','Select a declared variable and 2 to 201 samples')
    start,stop=rational(start),rational(stop)
    if start>=stop:fail('DOMAIN_ERROR','Sweep start must be smaller than end')
    samples=[]
    for i in range(count):
        x=start+(stop-start)*Fraction(i,count-1); answer=evaluate(ir,{variable:str(x)},output_unit)
        rows=answer['outputs']; row=rows[0] if rows else None
        y=row.get('left') if row and row['kind']=='boolean' else row.get('value') if row else None
        samples.append({'input':number_record(x),'state':answer['state'],'value':y,
            'limit':row.get('right') if row else None,'satisfies':row.get('value') if row and row['kind']=='boolean' else None})
    boundaries=[]
    try:
        forms=affine(ir,free=(variable,));nodes={n['id']:n for n in ir['model']['nodes']}
        for output in ir['model']['outputs']:
            node=nodes[output]
            if node['op'] not in RELATIONS:continue
            c,coefficients=forms[output]
            if set(coefficients)!={variable}:continue
            root=-c/coefficients[variable]
            boundaries.append({'node':output,'input':{**number_record(root),'unit':ir['model']['variables'][variable]['unit']},
                'relation':node['op'],'coefficient_sign':1 if coefficients[variable]>0 else -1,
                'within_sample_range':start<=root<=stop,'scope':'DECLARED_ASSUMPTIONS_ONLY'})
    except MathError:pass
    return {'schema':'arc.math-sweep/1','variable':variable,'input_unit':ir['model']['variables'][variable]['unit'],
        'samples':samples,'boundaries':boundaries,'model_digest':ir['model_digest'], 'assumptions':ir['model']['assumptions'],
        'notice':'Sampled graph, not a proof between samples. Exact linear boundaries are reported separately.'}
