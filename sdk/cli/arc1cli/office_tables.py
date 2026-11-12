"""Bounded inert office-table profiles. Exact decimals and identifiers stay text.

Import never calculates. Only the clean projection is eligible for Office use.
"""
from __future__ import annotations
import copy,csv,datetime,hashlib,io,json,posixpath,re,uuid,zipfile
from decimal import Decimal,InvalidOperation
import xml.etree.ElementTree as E
from .kicad_sexpr import parse as sexpr

SCHEMA='arc.office-table/1';MAX_INPUT=16*1024*1024;MAX_MODEL=1792*1024
MAX_ROWS=2048;MAX_COLS=64;MAX_CELLS=20000;MAX_SHEETS=8
S='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
O='urn:oasis:names:tc:opendocument:xmlns:office:1.0'
T='urn:oasis:names:tc:opendocument:xmlns:table:1.0'
X='urn:oasis:names:tc:opendocument:xmlns:text:1.0'
N='urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0';STYLE='urn:oasis:names:tc:opendocument:xmlns:style:1.0'
TYPES=('text','number','boolean','date','duration','error','blank','excel-date-serial')
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(v):return hashlib.sha256(v if isinstance(v,bytes) else canonical(v).encode()).hexdigest()
def text(v,n=16384,empty=True):
    if not isinstance(v,str) or len(v.encode())>n or '\0' in v or any(ord(c)<32 and c not in '\n\r\t' for c in v) or not empty and not v.strip():raise ValueError('OFFICE_TEXT_LIMIT')
    return v
def number(v):
    if not isinstance(v,str) or len(v)>160:raise ValueError('OFFICE_DECIMAL_REQUIRED')
    try:d=Decimal(v)
    except InvalidOperation:raise ValueError('OFFICE_INVALID_DECIMAL') from None
    if not d.is_finite() or abs(d.adjusted())>300:raise ValueError('OFFICE_DECIMAL_RANGE')
    return v
def xy(address):
    m=re.fullmatch(r'([A-Z]{1,3})([1-9][0-9]{0,6})',address or '')
    if not m:raise ValueError('OFFICE_CELL_ADDRESS')
    c=0
    for ch in m[1]:c=c*26+ord(ch)-64
    row=int(m[2])
    if row>MAX_ROWS or c>MAX_COLS:raise ValueError('OFFICE_GRID_LIMIT')
    return row,c
def address(row,col):
    word=''
    while col:col,k=divmod(col-1,26);word=chr(65+k)+word
    return word+str(row)
def cell(typ='text',value='',formula=None,dialect='none',fmt='',unit=''):
    return {'type':typ,'value':value,'formula':formula,'formula_dialect':dialect if formula is not None else 'none','cache_state':'STORED_NOT_RECALCULATED' if formula is not None else 'LITERAL','number_format':fmt,'unit':unit}
def validate(doc):
    if not isinstance(doc,dict) or set(doc)!={'schema','title','sheets'} or doc['schema']!=SCHEMA:raise ValueError('OFFICE_TABLE_SCHEMA')
    text(doc['title'],240,False)
    if not isinstance(doc['sheets'],list) or not 1<=len(doc['sheets'])<=MAX_SHEETS:raise ValueError('OFFICE_SHEET_LIMIT')
    names=set();ids=set();count=0
    for sheet in doc['sheets']:
        if not isinstance(sheet,dict) or set(sheet)!={'id','name','cells'} or not re.fullmatch('[a-f0-9]{32}',sheet['id']):raise ValueError('OFFICE_SHEET_ID')
        name=text(sheet['name'],124,False)
        if len(name)>31 or any(c in name for c in '[]:*?/\\') or name.casefold() in names or sheet['id'] in ids:raise ValueError('OFFICE_SHEET_NAME')
        names.add(name.casefold());ids.add(sheet['id'])
        if not isinstance(sheet['cells'],dict):raise ValueError('OFFICE_CELLS')
        count+=len(sheet['cells'])
        if count>MAX_CELLS:raise ValueError('OFFICE_CELL_LIMIT')
        for a,c in sheet['cells'].items():
            xy(a)
            if not isinstance(c,dict) or set(c)!={'type','value','formula','formula_dialect','cache_state','number_format','unit'} or c['type'] not in TYPES:raise ValueError('OFFICE_CELL_SCHEMA')
            v=c['value'];typ=c['type']
            if typ in ('number','excel-date-serial'):number(v)
            elif typ=='boolean':
                if type(v) is not bool:raise ValueError('OFFICE_BOOLEAN')
            elif typ=='blank':
                if v is not None:raise ValueError('OFFICE_BLANK')
            else:text(v)
            if typ=='date':
                try:datetime.datetime.fromisoformat(v.replace('Z','+00:00'))
                except ValueError:raise ValueError('OFFICE_DATE_ISO') from None
            text(c['number_format'],256);text(c['unit'],120)
            if c['formula'] is not None:
                text(c['formula'],2048,False)
                if c['formula_dialect'] not in ('xlsx-a1','odf-openformula','unsupported') or c['cache_state']!='STORED_NOT_RECALCULATED':raise ValueError('OFFICE_FORMULA_PROVENANCE')
            elif c['formula_dialect']!='none' or c['cache_state']!='LITERAL':raise ValueError('OFFICE_LITERAL_PROVENANCE')
    if len(canonical(doc).encode())>MAX_MODEL:raise ValueError('OFFICE_MODEL_SIZE')
    return doc
def sheet(name,cells=None):return {'id':uuid.uuid4().hex,'name':name,'cells':cells or {}}
def document(name,sheets):return validate({'schema':SCHEMA,'title':name[:160] or 'Working table','sheets':sheets})
def xml(raw):
    if len(raw)>32*1024*1024 or b'\0' in raw or raw.startswith((b'\xff\xfe',b'\xfe\xff')) or re.search(br'<!\s*(DOCTYPE|ENTITY)',raw,re.I):raise ValueError('OFFICE_XML_PROFILE')
    try:return E.fromstring(raw)
    except (E.ParseError,RecursionError):raise ValueError('OFFICE_XML_INVALID') from None
def archive(raw):
    if len(raw)>MAX_INPUT:raise ValueError('OFFICE_INPUT_LIMIT')
    try:z=zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:raise ValueError('OFFICE_ZIP_INVALID') from None
    infos=z.infolist();names=[r.filename for r in infos]
    if len(infos)>256 or len(set(names))!=len(names) or sum(r.file_size for r in infos)>64*1024*1024:raise ValueError('OFFICE_ZIP_LIMIT')
    for r in infos:
        p=r.filename
        if p.startswith('/') or '\\' in p or any(x in ('.','..','') for x in p.rstrip('/').split('/')) or r.flag_bits&1 or (r.external_attr>>16)&0o170000==0o120000:raise ValueError('OFFICE_ZIP_MEMBER')
        if r.file_size>32*1024*1024 or r.file_size>max(1024*1024,r.compress_size*300):raise ValueError('OFFICE_ZIP_EXPANSION')
    return z
def loss(rows,path,reason):
    if len(rows)>=1024:raise ValueError('OFFICE_LOSS_LIMIT')
    item={'path':path,'reason':reason}
    if item not in rows:rows.append(item)
def package_losses(z,rows):
    for name in z.namelist():
        lower=name.lower()
        if any(p in lower for p in ('vba','scripts/','basic/','activex','embeddings/','externallinks/','connections.xml','querytables/','customui/')):loss(rows,name,'ACTIVE_OR_EXTERNAL_PART_RETAINED_ONLY_IN_ORIGINAL')
        if name.endswith('.rels'):
            for r in xml(z.read(name)):
                if r.get('TargetMode')=='External':loss(rows,name,'EXTERNAL_RELATIONSHIP_NOT_LOADED_OR_REEXPORTED')
def parse_csv(raw,name,columns=None,units=None,header_rows=1):
    if len(raw)>MAX_INPUT:raise ValueError('OFFICE_INPUT_LIMIT')
    columns=columns or {};units=units or {};cells={}
    if type(header_rows) is not int or header_rows not in (0,1):raise ValueError('OFFICE_CSV_HEADER_PROFILE')
    for key,typ in columns.items():
        xy(key+'1')
        if typ not in ('text','number','boolean','date'):raise ValueError('OFFICE_CSV_COLUMN_TYPE')
    for k,v in units.items():xy(k+'1');text(v,120)
    try:
        rows=csv.reader(io.StringIO(raw.decode('utf-8-sig')),strict=True)
        for r,row in enumerate(rows,1):
            if r>MAX_ROWS or len(row)>MAX_COLS:raise ValueError('OFFICE_GRID_LIMIT')
            for c,value in enumerate(row,1):
                a=address(r,c);key=re.sub('[0-9]','',a);typ=columns.get(key,'text') if r>header_rows else 'text'
                if typ=='boolean':
                    if value.lower() not in ('true','false'):raise ValueError('OFFICE_CSV_BOOLEAN')
                    value=value.lower()=='true'
                if typ!='text' and value=='':typ='blank';value=None
                cells[a]=cell(typ,value,unit=units.get(key,'') if r>header_rows else '')
    except (UnicodeDecodeError,csv.Error):raise ValueError('OFFICE_CSV_UTF8_PROFILE') from None
    return {'document':document(name,[sheet('Table',cells)]),'losses':[],'profile':'csv-utf8-explicit-types-v1','notice':'Unspecified columns remain exact text; formula-looking CSV strings remain literal.'}
def parse_xlsx(raw,name):
    losses=[];sheets=[]
    with archive(raw) as z:
        package_losses(z,losses);book=xml(z.read('xl/workbook.xml'));rels=xml(z.read('xl/_rels/workbook.xml.rels'))
        paths={r.get('Id'):r.get('Target') for r in rels if r.get('TargetMode')!='External'}
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            for si in xml(z.read('xl/sharedStrings.xml')):strings.append(''.join(t.text or '' for t in si.iter('{'+S+'}t')))
        formats={};style_formats=[]
        if 'xl/styles.xml' in z.namelist():
            styles=xml(z.read('xl/styles.xml'));formats={r.get('numFmtId'):r.get('formatCode','') for r in styles.findall('.//{'+S+'}numFmt')}
            xf=styles.find('{'+S+'}cellXfs');style_formats=[r.get('numFmtId','0') for r in xf] if xf is not None else []
            loss(losses,'xl/styles.xml','STYLES_NOT_ROUNDTRIPPED_NUMBER_FORMATS_RETAINED')
        date1904=book.find('{'+S+'}workbookPr');date1904=date1904 is not None and date1904.get('date1904') in ('1','true')
        for s in book.findall('./{'+S+'}sheets/{'+S+'}sheet'):
            target=paths.get(s.get('{'+R+'}id'))
            if not target:raise ValueError('OFFICE_XLSX_SHEET_RELATIONSHIP')
            target=posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join('xl',target))
            if not target.startswith('xl/') or target not in z.namelist():raise ValueError('OFFICE_XLSX_SHEET_PATH')
            root=xml(z.read(target));cells={}
            if s.get('state','visible')!='visible':loss(losses,s.get('name',''),'HIDDEN_SHEET_BECOMES_VISIBLE_IN_WORKING_PROFILE')
            for n in root.findall('./{'+S+'}sheetData/{'+S+'}row/{'+S+'}c'):
                a=n.get('r');xy(a)
                if a in cells:raise ValueError('OFFICE_DUPLICATE_CELL')
                typ=n.get('t','n');v=n.find('{'+S+'}v');value=v.text if v is not None and v.text is not None else None;f=n.find('{'+S+'}f');formula=f.text or '' if f is not None else None;dialect='xlsx-a1'
                if f is not None and f.get('t') in ('shared','array','dataTable'):
                    loss(losses,s.get('name','')+'!'+a,'SHARED_ARRAY_OR_DATA_TABLE_FORMULA_UNSUPPORTED');dialect='unsupported';formula=E.tostring(f,encoding='unicode')
                if typ=='s':
                    try:value=strings[int(value)]
                    except (ValueError,TypeError,IndexError):raise ValueError('OFFICE_SHARED_STRING_INDEX') from None
                    typ='text'
                elif typ=='inlineStr':value=''.join(t.text or '' for t in n.iter('{'+S+'}t'));typ='text'
                elif typ in ('str','e','d'):typ={'str':'text','e':'error','d':'date'}[typ];value=value or ''
                elif typ=='b':
                    if value not in ('0','1'):raise ValueError('OFFICE_BOOLEAN')
                    typ='boolean';value=value=='1'
                elif typ=='n':typ='number' if value is not None else 'blank'
                else:raise ValueError('OFFICE_XLSX_CELL_TYPE')
                style=n.get('s','0')
                if not style.isdigit() or int(style)>100000:raise ValueError('OFFICE_XLSX_STYLE_INDEX')
                fmtid=style_formats[int(style)] if int(style)<len(style_formats) else '0';fmt=formats.get(fmtid,'builtin:'+fmtid)
                custom_date=fmtid in formats and re.search(r'[yd]',re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', '',fmt),re.I)
                if typ=='number' and (fmtid.isdigit() and int(fmtid) in range(14,23) or custom_date):
                    typ='excel-date-serial';fmt=('1904;' if date1904 else '1900;')+fmt;loss(losses,s.get('name','')+'!'+a,'EXCEL_DATE_SERIAL_RETAINED_WITH_DATE_SYSTEM_NOT_GUESSED')
                cells[a]=cell(typ,value,formula,dialect,fmt)
            for n in root:
                tag=n.tag.rsplit('}',1)[-1]
                if tag not in ('sheetData','dimension','sheetViews','sheetFormatPr','cols','pageMargins','pageSetup','printOptions'):loss(losses,s.get('name',''),tag.upper()+'_NOT_RENDERED_IN_WORKING_PROFILE')
            sheets.append(sheet(s.get('name',''),cells))
        known=('xl/worksheets/','xl/styles.xml','xl/workbook.xml','xl/sharedStrings.xml','xl/_rels/','docProps/','_rels/','[Content_Types].xml')
        for path in z.namelist():
            if not path.endswith('/') and not path.startswith(known):loss(losses,path,'PART_RETAINED_ONLY_IN_ORIGINAL')
    return {'document':document(name,sheets),'losses':losses,'profile':'xlsx-cells-v1'}
def ods_text(n):
    def walk(x):
        if x.tag=='{'+X+'}s':return ' '*min(1000,int(x.get('{'+X+'}c','1')))
        if x.tag=='{'+X+'}tab':return '\t'
        if x.tag=='{'+X+'}line-break':return '\n'
        return (x.text or '')+''.join(walk(c)+(c.tail or '') for c in x)
    return '\n'.join(walk(p) for p in n.findall('{'+X+'}p'))
def parse_ods(raw,name):
    losses=[];sheets=[]
    with archive(raw) as z:
        if z.read('mimetype')!=b'application/vnd.oasis.opendocument.spreadsheet':raise ValueError('OFFICE_ODS_MIMETYPE')
        package_losses(z,losses);root=xml(z.read('content.xml'))
        for table in root.findall('.//{'+O+'}spreadsheet/{'+T+'}table'):
            cells={};r=1;title=table.get('{'+T+'}name','')
            def rows(parent,depth=0):
                if depth>8:raise ValueError('OFFICE_ODS_ROW_GROUP_DEPTH')
                for n in parent:
                    if n.tag=='{'+T+'}table-row':yield n
                    elif n.tag in ('{'+T+'}table-header-rows','{'+T+'}table-row-group','{'+T+'}table-rows'):yield from rows(n,depth+1)
            for row in rows(table):
                repeated=int(row.get('{'+T+'}number-rows-repeated','1'))
                if not 1<=repeated<=1048576:raise ValueError('OFFICE_ODS_REPETITION')
                pending=[];c=1
                for n in row:
                    if n.tag not in ('{'+T+'}table-cell','{'+T+'}covered-table-cell'):continue
                    repeat=int(n.get('{'+T+'}number-columns-repeated','1'))
                    if not 1<=repeat<=16384:raise ValueError('OFFICE_ODS_REPETITION')
                    typ=n.get('{'+O+'}value-type');formula=n.get('{'+T+'}formula');value=None;shown=ods_text(n)
                    if typ in ('float','currency','percentage'):value=n.get('{'+O+'}value');typ='number'
                    elif typ=='boolean':
                        value=n.get('{'+O+'}boolean-value')
                        if value not in ('true','false'):raise ValueError('OFFICE_BOOLEAN')
                        value=value=='true'
                    elif typ=='date':value=n.get('{'+O+'}date-value');typ='date'
                    elif typ=='time':value=n.get('{'+O+'}time-value');typ='duration'
                    elif typ=='string' or shown:value=n.get('{'+O+'}string-value',shown);typ='error' if n.get('{urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0}value-type')=='error' else 'text'
                    elif typ is None:typ='blank';value=None
                    else:raise ValueError('OFFICE_ODS_CELL_TYPE')
                    if typ!='blank' or formula is not None:
                        if r+repeated-1>MAX_ROWS or c+repeat-1>MAX_COLS:raise ValueError('OFFICE_GRID_LIMIT')
                        if repeated*repeat+len(cells)>MAX_CELLS:raise ValueError('OFFICE_CELL_LIMIT')
                        for col in range(c,c+repeat):pending.append((col,cell(typ,value,formula,'odf-openformula' if formula is not None else 'none',n.get('{'+T+'}style-name',''))))
                    if n.get('{'+T+'}number-columns-spanned') or n.tag.endswith('covered-table-cell'):loss(losses,title,'MERGED_CELL_STRUCTURE_RETAINED_ONLY_IN_ORIGINAL')
                    if list(n) and any(child.tag!='{'+X+'}p' for child in n):loss(losses,title,'CELL_ANNOTATIONS_OR_OBJECTS_RETAINED_ONLY_IN_ORIGINAL')
                    c+=repeat
                if pending:
                    for rr in range(r,r+repeated):
                        for cc,v in pending:cells[address(rr,cc)]=copy.deepcopy(v)
                r+=repeated
            loss(losses,title,'ODS_STYLE_AND_LAYOUT_NOT_ROUNDTRIPPED');sheets.append(sheet(title,cells))
        for path in z.namelist():
            if not path.endswith('/') and not path.startswith(('mimetype','content.xml','styles.xml','meta.xml','settings.xml','META-INF/')):loss(losses,path,'PART_RETAINED_ONLY_IN_ORIGINAL')
    return {'document':document(name,sheets),'losses':losses,'profile':'ods-cells-v1'}
def parse(raw,name,columns=None,units=None,header_rows=1):
    suffix=name.rsplit('.',1)[-1].lower();stem=name.rsplit('.',1)[0]
    try:
        if suffix=='csv':return parse_csv(raw,stem,columns,units,header_rows)
        if columns or units:raise ValueError('OFFICE_COLUMN_MAPPING_IS_CSV_ONLY')
        if suffix=='xlsx':return parse_xlsx(raw,stem)
        if suffix=='ods':return parse_ods(raw,stem)
        raise ValueError('OFFICE_TABLE_FILE_PROFILE')
    except (KeyError,zipfile.BadZipFile,OverflowError,TypeError,E.ParseError) as e:raise ValueError('OFFICE_TABLE_INVALID:'+type(e).__name__) from None
def clean_formula(c):
    f=c['formula']
    if f is None:return None
    if c['formula_dialect']=='odf-openformula':
        if not f.startswith('of:='):raise ValueError('OFFICE_FORMULA_DIALECT_UNSUPPORTED')
        f=f[4:];f=re.sub(r'\[\.([A-Z]+[1-9][0-9]*)(?::\.([A-Z]+[1-9][0-9]*))?\]',lambda m:m[1]+(':'+m[2] if m[2] else ''),f);f=f.replace(';',',')
    elif c['formula_dialect']=='xlsx-a1':f=f.lstrip('=')
    else:raise ValueError('OFFICE_FORMULA_DIALECT_UNSUPPORTED')
    f=f.upper().replace('$','')
    if not f or re.search(r'[^A-Z0-9_.,:+\-*/() \t]',f):raise ValueError('OFFICE_FORMULA_NOT_IN_SAFE_PROFILE')
    tokens=re.findall(r'[A-Z_]+[0-9]*',f)
    for token in tokens:
        if re.fullmatch('[A-Z]+[1-9][0-9]*',token):xy(token)
        elif token not in ('SUM','PRODUCT','MIN','MAX','ABS','ROUND','AVERAGE','COUNT'):raise ValueError('OFFICE_FORMULA_NOT_IN_SAFE_PROFILE')
    # Bounds prevent expensive exponentiation or arbitrary-name interpretation.
    if f.count('(')!=f.count(')') or len(tokens)>128:raise ValueError('OFFICE_FORMULA_NOT_IN_SAFE_PROFILE')
    return f
def excel_date(c):
    value=Decimal(c['value']);fmt=c['number_format']
    if value<0 or not fmt.startswith(('1900;','1904;')):raise ValueError('OFFICE_DATE_SERIAL_PROFILE')
    days=int(value)
    if fmt.startswith('1900;') and days==60:raise ValueError('OFFICE_EXCEL_FICTITIOUS_LEAP_DATE')
    base=datetime.datetime(1904,1,1) if fmt.startswith('1904;') else datetime.datetime(1899,12,31) if days<60 else datetime.datetime(1899,12,30)
    micros=int(((value-Decimal(days))*Decimal(86400000000)).to_integral_value())
    result=base+datetime.timedelta(days=days,microseconds=micros)
    return result.date().isoformat() if not micros else result.isoformat()
def projection(doc):
    validate(doc);clean=copy.deepcopy(doc);losses=[]
    if any(c['number_format'] for s in doc['sheets'] for c in s['cells'].values()):loss(losses,'workbook','NUMBER_FORMAT_METADATA_RETAINED_IN_LEDGER_NOT_RECREATED_IN_CLEAN_ODS')
    for s in clean['sheets']:
        for a,c in s['cells'].items():
            if c['formula'] is not None:
                try:c['formula']=clean_formula(c);c['formula_dialect']='xlsx-a1'
                except ValueError:c.update(cell('text',c['formula'],unit=c['unit']));loss(losses,s['name']+'!'+a,'UNSUPPORTED_FORMULA_EXPORTED_AS_INERT_TEXT')
            if c['type']=='excel-date-serial':
                try:c['value']=excel_date(c);c['type']='date';loss(losses,s['name']+'!'+a,'EXCEL_DATE_SERIAL_PROJECTED_TO_CALENDAR_MICROSECOND_PROFILE_ORIGINAL_METADATA_RETAINED')
                except (ValueError,OverflowError):c['type']='number';loss(losses,s['name']+'!'+a,'UNREPRESENTABLE_DATE_SERIAL_EXPORTED_AS_NUMBER_ORIGINAL_METADATA_RETAINED')
            if c['type']=='date' and ('Z' in c['value'] or re.search(r'[+-][0-9]{2}:[0-9]{2}$',c['value'])):loss(losses,s['name']+'!'+a,'EXTERNAL_CALENDAR_PROFILE_DOES_NOT_PRESERVE_TIMEZONE_METADATA')
            if c['type']=='error' and c['formula'] is None:c['type']='text';loss(losses,s['name']+'!'+a,'ERROR_LITERAL_EXPORTED_AS_INERT_TEXT')
    return clean,losses
def check_roundtrip(expected,observed):
    """Reject unexpected engine type loss; retain explicit numeric/lexical changes."""
    validate(expected);validate(observed);after={s['name']:s for s in observed['sheets']};changes=[]
    if set(after)!={s['name'] for s in expected['sheets']}:raise ValueError('OFFICE_ENGINE_SHEET_IDENTITY_CHANGED')
    for sheet in expected['sheets']:
        for loc,before in sheet['cells'].items():
            if before['formula'] is not None or before['type']=='blank':continue
            now=after[sheet['name']]['cells'].get(loc)
            if now is None:
                if before['type']=='text' and before['value']=='':changes.append({'sheet':sheet['name'],'cell':loc,'change':'EMPTY_TEXT_NORMALIZED_TO_BLANK'});continue
                raise ValueError('OFFICE_ENGINE_LITERAL_CELL_MISSING:'+sheet['name']+'!'+loc)
            typ=now['type'];value=now['value']
            if before['type']=='date' and typ=='excel-date-serial':value=excel_date(now);typ='date'
            if typ!=before['type']:raise ValueError('OFFICE_ENGINE_UNEXPECTED_TYPE_CHANGE:'+sheet['name']+'!'+loc)
            if before['type'] in ('text','boolean') and value!=before['value']:raise ValueError('OFFICE_ENGINE_LITERAL_IDENTITY_CHANGED:'+sheet['name']+'!'+loc)
            if value!=before['value']:changes.append({'sheet':sheet['name'],'cell':loc,'type':typ,'before':before['value'],'after':value,'change':'EXPLICIT_ENGINE_NUMERIC_OR_CALENDAR_NORMALIZATION'})
    return changes
def ods_bytes(doc):
    doc,losses=projection(doc)
    for prefix,ns in (('office',O),('table',T),('text',X),('number',N),('style',STYLE)):E.register_namespace(prefix,ns)
    root=E.Element('{'+O+'}document-content',{'{'+O+'}version':'1.3','xmlns:of':'urn:oasis:names:tc:opendocument:xmlns:of:1.2'})
    styles=E.SubElement(root,'{'+O+'}automatic-styles')
    boolean=E.SubElement(styles,'{'+N+'}boolean-style',{'{'+STYLE+'}name':'BooleanFormat'});E.SubElement(boolean,'{'+N+'}boolean')
    date=E.SubElement(styles,'{'+N+'}date-style',{'{'+STYLE+'}name':'DateFormat'})
    for tag in ('year','month','day'):
        if tag!='year':E.SubElement(date,'{'+N+'}text').text='-'
        E.SubElement(date,'{'+N+'}'+tag,{'{'+N+'}style':'long'})
    datetime_style=E.SubElement(styles,'{'+N+'}date-style',{'{'+STYLE+'}name':'DateTimeFormat'})
    for node in date:datetime_style.append(copy.deepcopy(node))
    E.SubElement(datetime_style,'{'+N+'}text').text=' '
    for tag in ('hours','minutes','seconds'):
        if tag!='hours':E.SubElement(datetime_style,'{'+N+'}text').text=':'
        E.SubElement(datetime_style,'{'+N+'}'+tag,{'{'+N+'}style':'long'})
    duration=E.SubElement(styles,'{'+N+'}time-style',{'{'+STYLE+'}name':'DurationFormat','{'+N+'}truncate-on-overflow':'false'})
    for tag in ('hours','minutes','seconds'):
        if tag!='hours':E.SubElement(duration,'{'+N+'}text').text=':'
        E.SubElement(duration,'{'+N+'}'+tag,{'{'+N+'}style':'long'})
    for name in ('Boolean','Date','DateTime','Duration'):E.SubElement(styles,'{'+STYLE+'}style',{'{'+STYLE+'}name':name+'Cell','{'+STYLE+'}family':'table-cell','{'+STYLE+'}data-style-name':name+'Format'})
    body=E.SubElement(root,'{'+O+'}body');spread=E.SubElement(body,'{'+O+'}spreadsheet')
    for s in doc['sheets']:
        t=E.SubElement(spread,'{'+T+'}table',{'{'+T+'}name':s['name']});maxrow=max((xy(a)[0] for a in s['cells']),default=1);maxcol=max((xy(a)[1] for a in s['cells']),default=1)
        for r in range(1,maxrow+1):
            row=E.SubElement(t,'{'+T+'}table-row')
            for col in range(1,maxcol+1):
                c=s['cells'].get(address(r,col),cell('blank',None));attrs={};typ=c['type'];v=c['value']
                if typ=='number':attrs={'{'+O+'}value-type':'float','{'+O+'}value':v}
                elif typ=='boolean':attrs={'{'+O+'}value-type':'boolean','{'+O+'}boolean-value':str(v).lower(),'{'+T+'}style-name':'BooleanCell'}
                elif typ=='date':attrs={'{'+O+'}value-type':'date','{'+O+'}date-value':v,'{'+T+'}style-name':'DateTimeCell' if 'T' in v else 'DateCell'}
                elif typ=='duration':attrs={'{'+O+'}value-type':'time','{'+O+'}time-value':v,'{'+T+'}style-name':'DurationCell'}
                elif typ in ('text','error'):attrs={'{'+O+'}value-type':'string'}
                if c['formula'] is not None:
                    f=re.sub(r'([A-Z]+[1-9][0-9]*)(?::([A-Z]+[1-9][0-9]*))?',lambda m:'[.'+m[1]+(':'+'.'+m[2] if m[2] else '')+']',c['formula']);attrs['{'+T+'}formula']='of:='+f.replace(',',';')
                n=E.SubElement(row,'{'+T+'}table-cell',attrs)
                if v is not None:E.SubElement(n,'{'+X+'}p').text=str(v)
                if c['unit']:loss(losses,s['name']+'!'+address(r,col),'CELL_UNIT_METADATA_NOT_NATIVE_ODS_USE_UNIT_COLUMN_OR_LEDGER_METADATA')
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as z:
        z.writestr('mimetype','application/vnd.oasis.opendocument.spreadsheet',compress_type=zipfile.ZIP_STORED)
        z.writestr('content.xml',E.tostring(root,encoding='utf-8',xml_declaration=True),compress_type=zipfile.ZIP_DEFLATED)
        z.writestr('META-INF/manifest.xml','<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3"><manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/><manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/></manifest:manifest>')
    return output.getvalue(),losses
def csv_bytes(doc,selected):
    validate(doc);s=next((s for s in doc['sheets'] if s['id']==selected),None)
    if s is None:raise ValueError('OFFICE_SHEET_UNAVAILABLE')
    losses=[];out=io.StringIO(newline='');writer=csv.writer(out,lineterminator='\n');maxrow=max((xy(a)[0] for a in s['cells']),default=0);maxcol=max((xy(a)[1] for a in s['cells']),default=0)
    for r in range(1,maxrow+1):
        row=[]
        for col in range(1,maxcol+1):
            a=address(r,col);c=s['cells'].get(a,cell('blank',None));v=c['formula'] if c['formula'] is not None else c['value'];v='' if v is None else str(v).lower() if type(v) is bool else str(v)
            if v.lstrip().startswith(('=','+','-','@','\t','\r')) and c['type']!='number':v="'"+v;loss(losses,s['name']+'!'+a,'CSV_FORMULA_LIKE_TEXT_PREFIXED_FOR_EXTERNAL_OFFICE')
            if c['formula'] is not None:loss(losses,s['name']+'!'+a,'CSV_FORMULA_EXPORTED_AS_INERT_DEFINITION')
            row.append(v)
        writer.writerow(row)
    loss(losses,s['name'],'CSV_SELECTED_SHEET_ONLY_TYPES_FORMATS_AND_UNITS_REQUIRE_LEDGER_METADATA');return out.getvalue().encode(),losses
def align(doc,base):
    doc=copy.deepcopy(doc);names={s['name']:s['id'] for s in base['sheets']}
    for s in doc['sheets']:
        if s['name'] in names:s['id']=names[s['name']]
    doc['title']=base['title'];return validate(doc)
def difference(a,b):
    validate(a);validate(b);left={s['id']:s for s in a['sheets']};right={s['id']:s for s in b['sheets']};rows=[]
    for sid in sorted(set(left)|set(right)):
        x=left.get(sid);y=right.get(sid)
        if not x or not y:rows.append({'sheet':(x or y)['name'],'change':'SHEET_REMOVED' if x else 'SHEET_ADDED'});continue
        if x['name']!=y['name']:rows.append({'sheet':y['name'],'change':'SHEET_RENAMED','before':x['name'],'after':y['name']})
        for loc in sorted(set(x['cells'])|set(y['cells']),key=xy):
            if x['cells'].get(loc)!=y['cells'].get(loc):rows.append({'sheet':y['name'],'cell':loc,'change':'CELL_CHANGED','before':x['cells'].get(loc),'after':y['cells'].get(loc)})
    return rows
def pcb_components(raw):
    if len(raw)>MAX_INPUT:raise ValueError('OFFICE_CAD_SIZE')
    root=sexpr(raw.decode('utf-8'));rows=[];ids=set();refs=set()
    if root[0]!='kicad_pcb':raise ValueError('OFFICE_BOM_KICAD_PCB_PROFILE')
    for n in root:
        if not isinstance(n,list) or not n or n[0] not in ('footprint','module'):continue
        values={x[0]:x[1:] for x in n[2:] if isinstance(x,list) and x};props={x[1]:x[2] for x in n if isinstance(x,list) and len(x)>2 and x[0]=='property'}
        for x in n:
            if isinstance(x,list) and len(x)>2 and x[0]=='fp_text':props.setdefault({'reference':'Reference','value':'Value'}.get(x[1],x[1]),x[2])
        ref=props.get('Reference');native=(values.get('uuid') or values.get('tstamp') or [None])[0]
        if ref is None:continue
        if not native or native in ids or ref in refs:raise ValueError('OFFICE_BOM_AMBIGUOUS_NATIVE_IDENTITY')
        text(ref,120,False);text(native,120,False);ids.add(native);refs.add(ref)
        rows.append({'reference':ref,'native_id':native,'value':props.get('Value',''),'footprint':n[1],'identity_type':'PCB_FOOTPRINT_UUID' if '-' in native else 'LEGACY_PCB_FOOTPRINT_TSTAMP'})
    if not rows or len(rows)>MAX_ROWS-1:raise ValueError('OFFICE_BOM_COMPONENT_LIMIT')
    return sorted(rows,key=lambda r:r['reference'])
def bom_document(name,components):
    cells={};headers=['Reference','Native ID','Value','Footprint','Quantity','Unit']
    for i,v in enumerate(headers,1):cells[address(1,i)]=cell('text',v)
    for r,n in enumerate(components,2):
        for c,v in enumerate([n['reference'],n['native_id'],n['value'],n['footprint'],'1','item'],1):cells[address(r,c)]=cell('number' if c==5 else 'text',v)
    return document(name,[sheet('BOM',cells)])
def bom_rows(doc):
    validate(doc);s=doc['sheets'][0];rows={};headers=['Reference','Native ID','Value','Footprint','Quantity','Unit']
    if any(s['cells'].get(address(1,i),{}).get('value')!=v for i,v in enumerate(headers,1)):raise ValueError('OFFICE_BOM_HEADER_PROFILE')
    end=max((xy(a)[0] for a in s['cells']),default=1)
    for r in range(2,end+1):
        values=[s['cells'].get(address(r,c)) for c in range(1,7)]
        if all(v is None or v['type']=='blank' for v in values):continue
        if any(v is None or v['formula'] is not None for v in values):raise ValueError('OFFICE_BOM_LITERAL_IDENTITIES_REQUIRED')
        ref,native,value,foot,qty,unit=[v['value'] for v in values]
        if any(values[i]['type']!='text' for i in (0,1,2,3,5)) or values[4]['type']!='number' or Decimal(qty)<0:raise ValueError('OFFICE_BOM_TYPES')
        if native in rows:raise ValueError('OFFICE_BOM_DUPLICATE_NATIVE_ID')
        rows[native]={'reference':ref,'native_id':native,'value':value,'footprint':foot,'quantity':qty,'unit':unit,'row':r,'sheet_id':s['id']}
    return rows
def compare_bom(a,b,components,source_sha):
    left=bom_rows(a);right=bom_rows(b);known={r['native_id']:r for r in components};changes=[];unbound=[]
    for native,row in [*left.items(),*right.items()]:
        if native not in known or known[native]['reference']!=row['reference']:unbound.append({'native_id':native,'reference':row['reference'],'state':'UNRESOLVED_COMPONENT_IDENTITY'})
    for native in sorted(set(left)|set(right)):
        old=left.get(native);new=right.get(native)
        fields=[k for k in ('reference','value','footprint','quantity','unit') if (old or {}).get(k)!=(new or {}).get(k)]
        if fields:changes.append({'native_id':native,'source_sha256':source_sha,'component':known.get(native),'change':'REMOVED' if not new else 'ADDED' if not old else 'MODIFIED','fields':fields,'before':old,'after':new})
    return {'schema':'arc.bom-comparison/1','changes':changes,'unresolved':unbound,'link_state':'UNRESOLVED' if unbound else 'EXACT_NATIVE_COMPONENT_IDENTITIES','source_sha256':source_sha,'engineering_acceptance':False,'physical_qualification':False}
