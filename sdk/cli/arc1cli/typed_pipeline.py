"""Stacy language 1: JSON values through a finite, typed pipeline; no shell/eval."""
import decimal,fractions,hashlib,json,math,re,sys

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
FIELD=re.compile(r'^[A-Za-z_][A-Za-z0-9_.]{0,79}$')
# Comparison words avoid conflicts with the pipeline's shell-syntax guard.
COMPARE=re.compile(r'^([A-Za-z_][A-Za-z0-9_.]{0,79})(?:\s*(!=|=)\s*|\s+(over|under|at least|at most|has|is not)\s+)(.*)$')
WORDS={'over':'>','under':'<','at least':'>=','at most':'<=','has':'~','is not':'!='}
JOIN=re.compile(r'(@[a-z][a-z0-9_]*:[^\s|]+)\s+(?:(rows|facts|layers|lines|headings|texts|sheet\s+\S+)\s+)?on\s+([A-Za-z_][A-Za-z0-9_.]{0,79})')
# Lenses select a view inside a source before the row transforms run.
LENSES={'sheet':'','rows':'data.rows','facts':'facts','layers':'data.layers','lines':'data.lines','headings':'data.headings','texts':'data.texts'}
SHELL='Shell syntax and command substitution are not part of Stacy language'
# One rule for values, held by every step that compares, gathers, joins, orders or adds them (number, same, compare below).
# Exactly a number means JSON's own form (12, -0.5, 3e6) or whole thousands marked with commas (1,200), in at most 40
# characters: no spaces, no plus sign, no leading zero (0805 is a part size, 007 a code), nothing before or after. A whole
# number is held exactly at any length. A decimal is held as a float, so one written with more digits than a float keeps
# (1234567890123456.78, 1e-400) is not exactly a number: it stays the text it is, and two such texts never count as one value.
RULE=('Text that is exactly a number (12, -0.5, 3e6, 1,200) counts as that number; true and false never do; all other text is taken exactly as written. '
      'A decimal too long to be held exactly (more than about 15 digits) stays text.')
NUMBER=re.compile(r'-?(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?')
KEYS='Keys match exactly as written: capitals and spaces count, and text that is exactly a number is that number.'
TOTAL='%s FIELD. Numbers are used, and text that is exactly a number; a row with nothing there is counted as blank; anything else stops the step, which says how many it could not use. '
WORKED='The answer is worked out exactly from the numbers as written (0.1 and 0.2 make 0.3) and is never rounded: a whole number stays whole, anything else is given to the digits a number holds (about 15).'
HELD='The answer is a number one of the rows holds, as it is.'
# Each step's own help words: what it does with values. A step written wrongly answers with them.
HELP={'where':'where FIELD=VALUE, or FIELD over|under|at least|at most|has|is not VALUE. '+RULE+' A number is never over or under a text. has finds the text anywhere, in any case. '
              '@NAME as the VALUE is another field of the same row; in double quotes ("@NAME") it is that text. '
              'A row without the FIELD has nothing there: is not keeps it, and so does =null.',
      'select':'select FIELD[, FIELD…]: one to sixteen field names with commas between them; spaces beside a comma do not matter.',
      'sort':'sort FIELD, or sort -FIELD for largest first. Numbers come first, by value, a number written as text among them; then other text; then rows without the field.',
      'group':'group FIELD[, FIELD…] (one to four), then count, sum, avg, min or max. Equal numbers share a group however they are written (1, 1.0, "1"); true and 1 stay apart; other text gathers exactly as written.',
      'sum':TOTAL%'sum'+WORKED,'avg':TOTAL%'avg'+WORKED,'min':TOTAL%'min'+HELD,'max':TOTAL%'max'+HELD,
      'add':'add NAME = numbers, field names, + - * / and brackets; a minus may stand before a value (2*-3). A field counts when it is a number or text that is exactly a number; otherwise that row gets no value. '
            'It is worked out exactly from the numbers as written (0.1*3 is 0.3) and never rounded. A division by zero gives no value, and so does an answer too large or too small for a number. '
            'A field already named NAME is replaced.',
      'join':'join @address [rows|sheet NAME|layers|lines|headings|texts|facts] on FIELD. '+KEYS+' A field both sides have keeps its name, and the other source\'s comes as other_NAME (then other_NAME_2, and so on): nothing is overwritten.',
      'missing':'missing @address [rows|sheet NAME|layers|lines|headings|texts|facts] on FIELD keeps the rows whose key the other source does not have. '+KEYS}

def form(step):
    """The refusal of a step written wrongly: its own help words, once, with the form first."""
    return ValueError('Write it as: '+HELP[step])


def split(source):
    if not isinstance(source,str) or not 1<=len(source)<=8192:raise ValueError('Pipeline text is outside its bound')
    # A semicolon, like a bar, is data inside double quotes and refused outside them. The other signs are refused wherever
    # they stand: ` $( and ${ run inside a shell's double quotes too, and < and > stay out of every line as before.
    if any(word in source for word in ('`','$(','${','>','<','\n','\r','\x00')):raise ValueError(SHELL)
    result=[];quote=False;escape=False;start=0
    for index,char in enumerate(source):
        if escape:escape=False;continue
        if char=='\\' and quote:escape=True;continue
        if char=='"':quote=not quote
        if char==';' and not quote:raise ValueError(SHELL)
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
            match=re.fullmatch(r'rows\s+([1-9][0-9]{0,3}(?:\s*,\s*[1-9][0-9]{0,3}){0,199})',value.strip())
            if not match:raise ValueError('keep rows accepts up to 200 comma-separated row numbers')
            indices=[int(row)-1 for row in match.group(1).split(',')]
            if len(set(indices))!=len(indices):raise ValueError('Choose each row once')
            transforms.append({'kind':'keep_rows','indices':sorted(indices)})
        elif verb=='select':
            fields=[name.strip() for name in value.split(',')]
            if not 1<=len(fields)<=16 or any(not FIELD.fullmatch(name) for name in fields):raise form('select')
            transforms.append({'kind':'select','fields':fields})
        elif verb=='where':
            # = and the named comparisons hold one rule for a value (RULE): =1 keeps what over 0 and under 2 both keep.
            match=COMPARE.fullmatch(value.strip())
            if not match:raise form('where')
            field=match.group(1);operator=match.group(2) or WORDS[match.group(3)];raw=match.group(4).strip()
            if len(raw)>200:raise ValueError('where requires field=value')
            try:literal=json.loads(raw)
            except json.JSONDecodeError:literal=raw
            if isinstance(literal,(dict,list)) or isinstance(literal,float) and not math.isfinite(literal):raise ValueError('where compares one finite scalar')
            # A decimal too long to be held exactly is compared as the text it is written as (RULE), never as the float nearest to it.
            if isinstance(literal,float) and number(raw) is None:literal=raw
            step={'kind':'where','field':field,'value':literal} if operator=='=' else {'kind':'compare','field':field,'op':operator,'value':literal}
            # @NAME names another field of the same row (reference). Written in double quotes it is that text, and the plan says so.
            if isinstance(literal,str) and literal!=raw and literal.startswith('@'):step['text']=True
            transforms.append(step)
        elif verb in LENSES or verb=='pick':
            path=LENSES.get(verb) if verb!='pick' else value.strip()
            if verb=='sheet':
                if not value.strip() or len(value)>80:raise ValueError('sheet requires a sheet name')
                path='data.sheets.'+value.strip().strip('"')
            if not path or len(path)>200:raise ValueError('pick requires a field path')
            transforms.append({'kind':'pick','path':path})
        elif verb=='sort':
            name=value.strip();descending=name.startswith('-');name=name.lstrip('-')
            if not FIELD.fullmatch(name):raise form('sort')
            transforms.append({'kind':'sort','field':name,'descending':descending})
        elif verb=='count' and not value.strip():transforms.append({'kind':'count'})
        elif verb=='group':
            fields=[f.strip() for f in value.split(',')]
            if not 1<=len(fields)<=4 or any(not FIELD.fullmatch(f) for f in fields):raise form('group')
            transforms.append({'kind':'group','fields':fields})
        elif verb in AGGREGATES:
            if not FIELD.fullmatch(value.strip()):raise form(verb)
            transforms.append({'kind':'aggregate','how':verb,'field':value.strip()})
        elif verb=='add':
            name,separator,expression=value.partition('=')
            if not separator or not FIELD.fullmatch(name.strip()):raise form('add')
            transforms.append({'kind':'add','name':name.strip(),'expression':arithmetic(expression)})
        elif verb in ('join','missing'):
            # join @address [lens [name]] on FIELD: rows of another source, matched on one field (read-only, one level deep)
            match=JOIN.fullmatch(value.strip())
            if not match:raise form(verb)
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
    # 'neg' is a minus that stands before a value (2*-3, -(a+b), 2--3): it binds tighter than * and / and is written into
    # the list as 0 value -, so the list keeps its three words (num, field, op) and its four operators.
    out,ops=[],[];prec={'+':1,'-':1,'*':2,'/':2,'neg':3};expect_value=True
    def emit():out.append(('op','-' if ops[-1]=='neg' else ops[-1]));ops.pop()
    for digits,name,symbol in TOKEN.findall(text):
        if (digits or name or symbol=='(') and not expect_value:raise ValueError('add: two values need an operator between them')
        if digits:
            # The plan holds a float, as it always has; a number written longer than a float keeps is refused, never shortened.
            if not exactly(float(digits),digits):raise ValueError('add: %s has more digits than a number holds exactly (about 15); write it shorter'%digits[:40])
            out.append(('num',float(digits)));expect_value=False
        elif name:out.append(('field',name));expect_value=False
        elif symbol in ('+','-','*','/'):
            if expect_value and symbol=='-':out.append(('num',0.0));ops.append('neg');continue
            if expect_value:raise ValueError('add: an operator needs a value before it')
            while ops and ops[-1]!='(' and prec[ops[-1]]>=prec[symbol]:emit()
            ops.append(symbol);expect_value=True
        elif symbol=='(':ops.append('(');expect_value=True
        elif symbol==')':
            if expect_value:raise ValueError('add: a bracket closes after a value')
            while ops and ops[-1]!='(':emit()
            if not ops:raise ValueError('add: unbalanced brackets')
            ops.pop();expect_value=False
        elif symbol.strip():raise ValueError('add: only numbers, field names, + - * / and brackets')
    while ops:
        if ops[-1]=='(':raise ValueError('add: unbalanced brackets')
        emit()
    if expect_value:raise ValueError('add: the expression ends with an operator')
    return out


WHOLE=2**53  # below this a float counts every whole number, so a whole answer is given as an integer


def exactly(found,text):
    """Whether the float found holds exactly what text says: writing it back gives the same number (0.1 does, 1e-400 does not)."""
    return math.isfinite(found) and decimal.Decimal(repr(found))==decimal.Decimal(text)


def written(value):
    """A number as the decimal it is written as, for working out exactly: 0.1 is one tenth, not the binary fraction nearest
    to it, so 0.1 and 0.2 make 0.3. A whole number is itself."""
    if isinstance(value,int):return value
    if value.is_integer() and abs(value)<WHOLE:return int(value)
    return fractions.Fraction(decimal.Decimal(repr(value)))


def given(result):
    """An exact answer as a row holds it, never rounded to fewer digits than a number has: a whole number as an integer (at
    any length when only whole numbers made it), anything else as the float nearest to it. OverflowError when no float can
    say it: too large, or so small that it would be given as 0 or as another number."""
    if isinstance(result,int):return result
    if result.denominator==1 and abs(result.numerator)<WHOLE:return result.numerator
    found=float(result)
    if abs(found)<sys.float_info.min and written(found)!=result:raise OverflowError('too small')
    return found


def calculate(program,row):
    """The value the list gives for one row, or None where it has none: a field that is not a number (RULE), a division by
    zero, an answer too large or too small to say. It is worked out exactly from the numbers as written (written, given):
    only the operation asked for is done, and nothing is rounded."""
    stack=[]
    try:
        for kind,value in program:
            if kind=='num':stack.append(written(value))
            elif kind=='field':
                v=number(field(row,value))
                if v is None:return None
                stack.append(written(v))
            else:
                if len(stack)<2:return None
                b,a=stack.pop(),stack.pop()
                if value=='+':stack.append(a+b)
                elif value=='-':stack.append(a-b)
                elif value=='*':stack.append(a*b)
                elif b==0:return None
                else:stack.append(a//b if isinstance(a,int) and isinstance(b,int) and a%b==0 else fractions.Fraction(a,b))
        return given(stack[0]) if len(stack)==1 else None
    except OverflowError:return None


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


def number(value):
    """The number a value stands for, or None: a number itself (never true or false), or text that is exactly a number (RULE).
    A whole number is held at any length; a decimal only when a float holds exactly what is written, so two different
    texts never stand for one number."""
    if isinstance(value,bool):return None
    if isinstance(value,int):return value
    if isinstance(value,float):return value if math.isfinite(value) else None
    if not isinstance(value,str) or len(value)>40 or not NUMBER.fullmatch(value):return None
    text=value.replace(',','')
    if text.lstrip('-').isdigit():return int(text)
    found=float(text)
    return found if exactly(found,text) else None


def identity(value):
    """What makes two values the same value, for where, is not, group, join and missing: a number by its value however it is
    written (1, 1.0, "1"); a list or an object by its JSON; anything else by its type and itself (true is not 1, "a" is not "A")."""
    found=number(value)
    if found is not None:return ('number',found)
    if isinstance(value,(dict,list)):return ('json',canonical(value))
    return (type(value).__name__,value)


def same(a,b):return identity(a)==identity(b)


def reference(transform):
    """The other field a comparison names with @NAME, or None: where a=@b, a is not @b and a over @b all compare two fields
    of the same row. Written in double quotes ("@b") it is that text, and the plan says text."""
    value=transform['value']
    if transform.get('text') or not isinstance(value,str) or not value.startswith('@') or not FIELD.fullmatch(value[1:]):return None
    return value[1:]


def compare(actual,op,expected):
    """One comparison of a where step, by RULE. has (~) finds the text anywhere, in any case. = and is not ask whether the two
    are the same value. over, under, at least and at most order two numbers by value, or two texts that are not numbers by
    their characters, and hold for nothing else: a number is never over or under a text, true, false or nothing."""
    if op=='~':return actual is not None and str(expected).casefold() in str(actual).casefold()
    if op=='=':return same(actual,expected)
    if op=='!=':return not same(actual,expected)
    a,b=number(actual),number(expected)
    if a is None and b is None and isinstance(actual,str) and isinstance(expected,str):a,b=actual,expected
    elif a is None or b is None:return False
    return {'>':a>b,'>=':a>=b,'<':a<b,'<=':a<=b}[op]


def groups(rows,fields):
    """The rows gathered by what fields hold, in the order first seen: [(the values as the first row wrote them, its rows)].
    Two rows share a group when each field holds the same value (identity): 1 with "1.0", never true with 1."""
    found={}
    for row in rows:
        values=tuple(field(row,f) for f in fields)
        found.setdefault(tuple(identity(v) for v in values),(values,[]))[1].append(row)
    return list(found.values())


def own(grouping,names):
    """A count or a total names its own fields. A group field of the same name would be overwritten, so it is refused."""
    for name in names:
        if name in (grouping or ()):
            raise ValueError('group: a field named %s cannot be gathered by here: the answer has its own %s and would overwrite it. '
                             'Give it another name first (for a number: add NAME = %s)'%(name,name,name))


def join_names(rows,others,on):
    """The name each field of a joined source takes. A field this side does not have keeps its name. One that both sides have
    keeps its name on this side and comes from the other as other_NAME; where that is taken too, other_NAME_2, other_NAME_3
    and so on. The names are settled once for the whole join, from every row of both sides, so a name means one thing in
    every row and no field is ever overwritten."""
    here={k for row in rows if isinstance(row,dict) for k in row}
    theirs=list(dict.fromkeys(k for other in others if isinstance(other,dict) for k in other if k!=on))
    names={k:k for k in theirs if k not in here};taken=here|set(names)
    for k in theirs:
        if k in names:continue
        name,n='other_'+k,1
        while name in taken:n+=1;name='other_%s_%d'%(k,n)
        names[k]=name;taken.add(name)
    return names


def _sort_rows(rows, name, reverse):
    """Sort numbers (a number written as text among them, by its value) and other text separately, keeping missing values last."""
    numbers, texts, missing = [], [], []
    for row in rows:
        value = field(row, name)
        found = number(value)
        if value is None:
            missing.append(row)
        elif found is not None:
            numbers.append((found, row))
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
        elif transform['kind'] in ('where','compare'):
            # One step in two spellings (= is kept as where in the plan). @NAME compares with another field of the same row.
            # A row without the field has nothing there, as group, sort and a total take it: is not keeps it, and so does =null.
            op=transform.get('op','=');expected=transform['value'];other=reference(transform)
            rows=[row for row in rows if compare(field(row,transform['field']),op,field(row,other) if other else expected)]
        elif transform['kind']=='select':rows=[{name:field(row,name) for name in transform['fields']} for row in rows]
        elif transform['kind'] in ('join','missing'):
            if 'rows' not in transform:raise ValueError('A join needs its other source resolved by the Kernel')
            # Keys match as written (identity): no trimming, no folding of capitals; a row with no key matches nothing.
            on=transform['on'];index={}
            for other in transform['rows']:
                if isinstance(other,dict) and field(other,on) not in (None,''):index.setdefault(identity(field(other,on)),[]).append(other)
            if transform['kind']=='missing':rows=[row for row in rows if identity(field(row,on,'')) not in index]
            else:
                names=join_names(rows,transform['rows'],on);joined=[]
                for row in rows:
                    for other in index.get(identity(field(row,on,'')),[]):
                        merged=dict(row)
                        for k,v in other.items():
                            if k!=on:merged[names[k]]=v
                        joined.append(merged)
                rows=joined
        elif transform['kind']=='pick':
            rows=pick(rows[0],transform['path']) if len(rows)==1 else [pick(row,transform['path']) for row in rows]
            rows=rows if isinstance(rows,list) else [rows]
        elif transform['kind']=='sort':
            rows=_sort_rows(rows, transform['field'], transform['descending'])
        elif transform['kind']=='count':
            own(grouping,('count',))
            rows=[dict(zip(grouping,key),count=len(members)) for key,members in groups(rows,grouping)] if grouping else [{'count':len(rows)}]
            grouping=None
        elif transform['kind']=='group':grouping=transform['fields']
        elif transform['kind']=='aggregate':
            # A total uses numbers and text that is exactly a number (RULE). A row with nothing there (no field, null, empty
            # text) has nothing to use and is counted under blank. Anything else stops the step: no value is skipped in silence.
            # min and max give a number a row holds; sum and avg are worked out exactly from the numbers as written (written,
            # given) and never rounded. An answer no number can say stops the step too.
            how,f=transform['how'],transform['field'];name=how+'_'+f.replace('.','_')
            held=[field(row,f) for row in rows];refused=[v for v in held if v is not None and v!='' and number(v) is None]
            if refused:
                long=' A decimal of more than about 15 digits cannot be held exactly, so it is not used as a number.' if any(isinstance(v,str) and NUMBER.fullmatch(v) for v in refused) else ''
                raise ValueError('%s %s refused: in %d of %d rows the value is not a number (the first is %s). Nothing is left out in silence: '
                                 'take those rows out or correct them first.%s'%(how,f,len(refused),len(held),canonical(refused[0])[:60],long))
            blank=any(v is None or v=='' for v in held)
            def total(members):
                values=[n for n in (number(field(m,f)) for m in members) if n is not None];made={name:None,'count':len(members)}
                if blank:made['blank']=len(members)-len(values)
                if not values:return made
                if how in ('min','max'):
                    value=min(values) if how=='min' else max(values)
                    made[name]=int(value) if isinstance(value,float) and value.is_integer() and abs(value)<WHOLE else value
                    return made
                value=sum(map(written,values));n=len(values)
                if how=='avg':value=value//n if isinstance(value,int) and value%n==0 else fractions.Fraction(value,n)
                try:made[name]=given(value)
                except OverflowError:raise ValueError('%s %s refused: the answer is too large or too small to give as a number here'%(how,f)) from None
                return made
            own(grouping,(name,'count','blank') if blank else (name,'count'))
            rows=[dict(zip(grouping,key),**total(members)) for key,members in groups(rows,grouping)] if grouping else [total(rows)]
            grouping=None
        elif transform['kind']=='add':rows=[dict(row,**{transform['name']:calculate(transform['expression'],row)}) if isinstance(row,dict) else row for row in rows]
        else:raise ValueError('Unregistered transform')
    if len(rows)>limit:raise ValueError('Output exceeds %d rows; add take'%limit)
    return rows
