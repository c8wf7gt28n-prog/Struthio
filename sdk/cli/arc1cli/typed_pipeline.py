"""Stacy language 1: JSON values through a finite, typed pipeline; no shell/eval."""
import hashlib,json,math,re

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
FIELD=re.compile(r'^[A-Za-z_][A-Za-z0-9_.]{0,79}$')
# Comparison words avoid conflicts with the pipeline's shell-syntax guard.
COMPARE=re.compile(r'^([A-Za-z_][A-Za-z0-9_.]{0,79})(?:\s*(!=|=)\s*|\s+(over|under|at least|at most|has|is not)\s+)(.*)$')
WORDS={'over':'>','under':'<','at least':'>=','at most':'<=','has':'~','is not':'!='}
JOIN=re.compile(r'(@[a-z][a-z0-9_]*:[^\s|]+)\s+(?:(rows|facts|layers|lines|headings|texts|sheet\s+\S+)\s+)?on\s+([A-Za-z_][A-Za-z0-9_.]{0,79})')
# Lenses select a view inside a source before the row transforms run.
LENSES={'sheet':'','rows':'data.rows','facts':'facts','layers':'data.layers','lines':'data.lines','headings':'data.headings','texts':'data.texts'}

def split(source):
    if not isinstance(source,str) or not 1<=len(source)<=8192:raise ValueError('Pipeline text is outside its bound')
    if any(word in source for word in ('`','$(','${',';','>','<','\n','\r','\x00')):raise ValueError('Shell syntax and command substitution are not part of Stacy language')
    result=[];quote=False;escape=False;start=0
    for index,char in enumerate(source):
        if escape:escape=False;continue
        if char=='\\' and quote:escape=True;continue
        if char=='"':quote=not quote
        if char=='|' and not quote:result.append(source[start:index].strip());start=index+1
    if quote:raise ValueError('Unterminated JSON string')
    result.append(source[start:].strip())
    if not all(result) or len(result)>8:raise ValueError('Use one source and at most seven transforms')
    return result

def _arguments(text):
    if not text:
        return {}

    def pairs(items):
        obj={}
        for key,value in items:
            if key in obj:raise ValueError('Duplicate argument member')
            obj[key]=value
        return obj
    def bad(value):raise ValueError('Non-finite argument')
    args=json.loads(text,object_pairs_hook=pairs,parse_constant=bad)
    if not isinstance(args,dict):raise ValueError('Operation arguments must be a JSON object')
    return args


def parse(source):
    stages=split(source);op,_,argument=stages[0].partition(' ')
    op={'jobs':'jobs.list','models':'brain.models','activity':'ledger.journal.read'}.get(op,op)
    if not re.fullmatch(r'[a-z][a-z0-9_.]{0,100}',op):raise ValueError('Expected a registered operation name')
    args=_arguments(argument)
    transforms=[]
    for stage in stages[1:]:
        verb,_,value=stage.partition(' ')
        if verb=='take':
            if not value.isdigit() or not 1<=int(value)<=200:raise ValueError('take accepts 1 through 200')
            transforms.append({'kind':'take','count':int(value)})
        elif verb=='keep':
            match=re.fullmatch(r'rows ([1-9][0-9]{0,3}(?:,[1-9][0-9]{0,3}){0,199})',value)
            if not match:raise ValueError('keep rows accepts up to 200 comma-separated row numbers')
            indices=[int(number)-1 for number in match.group(1).split(',')]
            if len(set(indices))!=len(indices):raise ValueError('Choose each row once')
            transforms.append({'kind':'keep_rows','indices':sorted(indices)})
        elif verb=='select':
            fields=value.split(',')
            if not 1<=len(fields)<=16 or any(not FIELD.fullmatch(name) for name in fields):raise ValueError('select requires comma-separated field names')
            transforms.append({'kind':'select','fields':fields})
        elif verb=='where':
            # Equality preserves the JSON type. Named comparisons have their own coercion rules.
            match=COMPARE.fullmatch(value.strip())
            if not match:raise ValueError('where requires field=value, or: field over|under|at least|at most|has|is not value')
            field=match.group(1);operator=match.group(2) or WORDS[match.group(3)];literal=match.group(4).strip()
            if len(literal)>200:raise ValueError('where requires field=value')
            try:literal=json.loads(literal)
            except json.JSONDecodeError:pass
            if isinstance(literal,(dict,list)) or isinstance(literal,float) and not math.isfinite(literal):raise ValueError('where compares one finite scalar')
            transforms.append({'kind':'where','field':field,'value':literal} if operator=='=' else {'kind':'compare','field':field,'op':operator,'value':literal})
        elif verb in LENSES or verb=='pick':
            path=LENSES.get(verb) if verb!='pick' else value.strip()
            if verb=='sheet':
                if not value.strip() or len(value)>80:raise ValueError('sheet requires a sheet name')
                path='data.sheets.'+value.strip().strip('"')
            if not path or len(path)>200:raise ValueError('pick requires a field path')
            transforms.append({'kind':'pick','path':path})
        elif verb=='sort':
            name=value.strip();descending=name.startswith('-');name=name.lstrip('-')
            if not FIELD.fullmatch(name):raise ValueError('sort requires a field name (prefix - for descending)')
            transforms.append({'kind':'sort','field':name,'descending':descending})
        elif verb=='count' and not value.strip():transforms.append({'kind':'count'})
        elif verb=='group':
            fields=[f.strip() for f in value.split(',')]
            if not 1<=len(fields)<=4 or any(not FIELD.fullmatch(f) for f in fields):raise ValueError('group requires one to four field names')
            transforms.append({'kind':'group','fields':fields})
        elif verb in AGGREGATES:
            if not FIELD.fullmatch(value.strip()):raise ValueError(verb+' requires a field name')
            transforms.append({'kind':'aggregate','how':verb,'field':value.strip()})
        elif verb=='add':
            name,separator,expression=value.partition('=')
            if not separator or not FIELD.fullmatch(name.strip()):raise ValueError('add requires NAME = expression')
            transforms.append({'kind':'add','name':name.strip(),'expression':arithmetic(expression)})
        elif verb in ('join','missing'):
            # join @address [lens [name]] on FIELD: rows of another source, matched on one field (read-only, one level deep)
            match=JOIN.fullmatch(value.strip())
            if not match:raise ValueError(verb+' requires: @address [rows|sheet NAME|layers|lines|headings|texts|facts] on FIELD')
            address,lens,on=match.group(1),(match.group(2) or '').strip(),match.group(3)
            if lens and lens.split()[0] not in LENSES:raise ValueError('Unknown lens '+lens.split()[0][:20])
            transforms.append({'kind':verb,'source':address+(' | '+lens if lens else ''),'on':on})
        else:raise ValueError('Unknown transform; use where, take, keep rows, select, sort, count, group, sum, avg, min, max, add, join, missing, or a lens: sheet, rows, facts, layers, lines, headings, pick')
    return {'schema':'arc.stacy-action-plan/1','language_version':1,'call':{'operation':op,'arguments':args},'transforms':transforms,'text':source}

AGGREGATES=('sum','avg','min','max')
TOKEN=re.compile(r'\s*(?:(\d+(?:\.\d+)?)|([A-Za-z_][A-Za-z0-9_.]{0,79})|(.))')


def arithmetic(text):
    """NAME = EXPR for add: numbers, field names, + - * / and brackets, read into a small postfix list. Never evaluated as code."""
    text=text.strip()
    if not text or len(text)>200:raise ValueError('add needs a short expression')
    out,ops=[],[];prec={'+':1,'-':1,'*':2,'/':2};expect_value=True
    for number,name,symbol in TOKEN.findall(text):
        if (number or name or symbol=='(') and not expect_value:raise ValueError('add: two values need an operator between them')
        if number:out.append(('num',float(number)));expect_value=False
        elif name:out.append(('field',name));expect_value=False
        elif symbol in prec:
            if expect_value and symbol=='-':out.append(('num',0.0))  # a leading minus
            elif expect_value:raise ValueError('add: an operator needs a value before it')
            while ops and ops[-1]!='(' and prec[ops[-1]]>=prec[symbol]:out.append(('op',ops.pop()))
            ops.append(symbol);expect_value=True
        elif symbol=='(':ops.append('(');expect_value=True
        elif symbol==')':
            while ops and ops[-1]!='(':out.append(('op',ops.pop()))
            if not ops:raise ValueError('add: unbalanced brackets')
            ops.pop();expect_value=False
        elif symbol.strip():raise ValueError('add: only numbers, field names, + - * / and brackets')
    while ops:
        if ops[-1]=='(':raise ValueError('add: unbalanced brackets')
        out.append(('op',ops.pop()))
    if expect_value:raise ValueError('add: the expression ends with an operator')
    return out


def calculate(program,row):
    stack=[]
    for kind,value in program:
        if kind=='num':stack.append(value)
        elif kind=='field':
            v=field(row,value)
            if isinstance(v,str):
                try:v=float(v.replace(',',''))
                except ValueError:return None
            if not isinstance(v,(int,float)) or isinstance(v,bool):return None
            stack.append(v)
        else:
            if len(stack)<2:return None
            b,a=stack.pop(),stack.pop()
            if value=='/' and b==0:return None
            stack.append({'+':a+b,'-':a-b,'*':a*b,'/':a/b if b else 0}[value])
    if len(stack)!=1:return None
    result=stack[0]
    return int(result) if isinstance(result,float) and result.is_integer() else round(result,6)


def field(row,path,default=None):
    for part in path.split('.'):
        if not isinstance(row,dict) or part not in row:return default
        row=row[part]
    return row

def pick(value,path):
    """A lens: the value at path, which may name a sheet with spaces (data.sheets.Sheet 1)."""
    if path.startswith('data.sheets.') and isinstance(value,dict):
        sheets=field(value,'data.sheets',{}) or {};name=path[len('data.sheets.'):]
        found=next((rows for key,rows in sheets.items() if key.casefold()==name.casefold()),None)
        if found is None:raise ValueError('No sheet named '+name[:60]+'; sheets: '+', '.join(list(sheets)[:12]))
        return found
    found=field(value,path,None)
    if found is None:raise ValueError('Nothing at '+path[:80]+' for this source')
    return found


def compare(actual,op,expected):
    if op=='~':return actual is not None and str(expected).casefold() in str(actual).casefold()
    if op=='!=':return actual!=expected
    if isinstance(expected,(int,float)) and not isinstance(expected,bool):
        if isinstance(actual,str):
            try:actual=float(actual.replace(',',''))
            except ValueError:return False
        if not isinstance(actual,(int,float)) or isinstance(actual,bool):return False
    elif not isinstance(actual,str) or not isinstance(expected,str):return False
    return {'>':actual>expected,'>=':actual>=expected,'<':actual<expected,'<=':actual<=expected}[op]


def groups(rows,fields):
    found={}
    for row in rows:found.setdefault(tuple(field(row,f) for f in fields),[]).append(row)
    return found


def _sort_rows(rows, name, reverse):
    """Sort numbers and text separately, keeping missing values last."""
    numbers, texts, missing = [], [], []
    for row in rows:
        value = field(row, name)
        if value is None:
            missing.append(row)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            numbers.append((value, row))
        else:
            texts.append((str(value).casefold(), row))
    numbers.sort(key=lambda item: item[0], reverse=reverse)
    texts.sort(key=lambda item: item[0], reverse=reverse)
    return [row for _, row in numbers] + [row for _, row in texts] + missing


def apply(value,transforms,limit=200):
    transforms=list(transforms)
    while transforms and transforms[0]['kind']=='pick':value=pick(value,transforms.pop(0)['path'])  # lenses look inside first
    if isinstance(value,dict):
        for key in ('jobs','models','events','operations','records'):
            if isinstance(value.get(key),list):value=value[key];break
    rows=value if isinstance(value,list) else [value]
    if len(rows)>2000 or len(canonical(rows).encode())>512*1024:raise ValueError('Pipeline source exceeds its row/byte budget; narrow the query')
    grouping=None
    for transform in transforms:
        if transform['kind']=='take':rows=rows[:transform['count']]
        elif transform['kind']=='keep_rows':
            if transform['indices'][-1]>=len(rows):raise ValueError('A selected row is outside this table')
            rows=[rows[index] for index in transform['indices']]
        elif transform['kind']=='where':
            missing=object();expected=transform['value']
            rows=[row for row in rows if (actual:=field(row,transform['field'],missing)) is not missing
                  and type(actual) is type(expected) and actual==expected]
        elif transform['kind']=='select':rows=[{name:field(row,name) for name in transform['fields']} for row in rows]
        elif transform['kind']=='compare':
            missing=object();other=transform['value'][1:] if isinstance(transform['value'],str) and transform['value'].startswith('@') and FIELD.fullmatch(transform['value'][1:]) else None
            rows=[row for row in rows if (actual:=field(row,transform['field'],missing)) is not missing
                  and compare(actual,transform['op'],field(row,other) if other else transform['value'])]  # @Field compares two columns of the same row
        elif transform['kind'] in ('join','missing'):
            if 'rows' not in transform:raise ValueError('A join needs its other source resolved by the Kernel')
            key=lambda v:str(v).strip().casefold()
            index={}
            for other in transform['rows']:
                if isinstance(other,dict) and other.get(transform['on']) not in (None,''):index.setdefault(key(other[transform['on']]),[]).append(other)
            if transform['kind']=='missing':rows=[row for row in rows if key(field(row,transform['on'],'')) not in index]
            else:
                joined=[]
                for row in rows:
                    for other in index.get(key(field(row,transform['on'],'')),[]):
                        merged=dict(row)
                        for k,v in other.items():
                            if k==transform['on']:continue
                            merged[k if k not in merged else 'other_'+k]=v
                        joined.append(merged)
                rows=joined
        elif transform['kind']=='pick':
            rows=pick(rows[0],transform['path']) if len(rows)==1 else [pick(row,transform['path']) for row in rows]
            rows=rows if isinstance(rows,list) else [rows]
        elif transform['kind']=='sort':
            rows=_sort_rows(rows, transform['field'], transform['descending'])
        elif transform['kind']=='count':
            rows=[dict(zip(grouping,key),count=len(members)) for key,members in groups(rows,grouping).items()] if grouping else [{'count':len(rows)}]
            grouping=None
        elif transform['kind']=='group':grouping=transform['fields']
        elif transform['kind']=='aggregate':
            name=transform['how']+'_'+transform['field'].replace('.','_')
            def total(members,how=transform['how'],f=transform['field']):
                values=[v for v in (field(m,f) for m in members) if isinstance(v,(int,float)) and not isinstance(v,bool)]
                if not values:return None
                value={'sum':sum(values),'avg':sum(values)/len(values),'min':min(values),'max':max(values)}[how]
                return int(value) if isinstance(value,float) and value.is_integer() else (round(value,6) if isinstance(value,float) else value)
            rows=[dict(zip(grouping,key),**{name:total(members),'count':len(members)}) for key,members in groups(rows,grouping).items()] if grouping else [{name:total(rows),'count':len(rows)}]
            grouping=None
        elif transform['kind']=='add':rows=[dict(row,**{transform['name']:calculate(transform['expression'],row)}) if isinstance(row,dict) else row for row in rows]
        else:raise ValueError('Unregistered transform')
    if len(rows)>limit:raise ValueError('Output exceeds %d rows; add take'%limit)
    return rows
