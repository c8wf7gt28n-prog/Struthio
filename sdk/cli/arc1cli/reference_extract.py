"""Original-bound locators and loss-labelled text derivatives. No Qt or model."""
from __future__ import annotations
import csv,hashlib,io,json,os,re,subprocess,sys,unicodedata,zipfile,importlib.metadata,shutil,tempfile
from pathlib import Path
from xml.etree import ElementTree as ET
from . import record_store as records,intake_files

VERSION='arc.reference-extraction/1'
MAX_TEXT=8*1024*1024
MAX_SEGMENTS=16000
MAX_PAGES=512
CHUNK=1800
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def digest(value):return hashlib.sha256(records.canonical(value)).hexdigest()
def rule_hash():
    try:pdf_version=importlib.metadata.version('pypdf')
    except importlib.metadata.PackageNotFoundError:pdf_version='NOT_INSTALLED'
    return hashlib.sha256(Path(__file__).read_bytes()+records.canonical({'pypdf':pdf_version,'poppler_text':poppler_profile(),'profile':VERSION})).hexdigest()
def poppler_profile():
    found=shutil.which('pdftotext')
    return {'name':'pdftotext','sha256':records.sha(Path(found).resolve())} if found else None
def missing_identity_map(resources,seen=None,depth=0):
    if not resources:return False
    if seen is None:seen=set()
    if depth>8 or len(seen)>2048:raise ValueError('REFERENCE_PDF_RESOURCE_TREE_LIMIT')
    resources=resources.get_object();identity=id(resources)
    if identity in seen:return False
    seen.add(identity);fonts=resources.get('/Font',{});fonts=fonts.get_object() if hasattr(fonts,'get_object') else fonts
    for font in fonts.values():
        font=font.get_object()
        if font.get('/Subtype')=='/Type0' and font.get('/Encoding') in ('/Identity-H','/Identity-V') and not font.get('/ToUnicode'):return True
    objects=resources.get('/XObject',{});objects=objects.get_object() if hasattr(objects,'get_object') else objects
    return any(missing_identity_map(obj.get_object().get('/Resources'),seen,depth+1) for obj in objects.values())
def mapped_pdf_text(raw,page_count):
    executable=shutil.which('pdftotext')
    if not executable:raise ValueError('REFERENCE_PDF_UNICODE_MAP_FALLBACK_UNAVAILABLE')
    executable=Path(executable).resolve();profile=poppler_profile()
    version=subprocess.run([str(executable),'-v'],capture_output=True,text=True,timeout=5)
    if version.returncode:raise ValueError('REFERENCE_PDF_TEXT_TOOL_PROFILE_FAILED')
    with tempfile.TemporaryDirectory(prefix='reference-text-') as tmp:
        source=Path(tmp)/'original.pdf';source.write_bytes(raw)
        result=subprocess.run([str(executable),'-layout','-enc','UTF-8','-eol','unix',str(source),'-'],capture_output=True,timeout=15)
    if result.returncode or len(result.stdout)>MAX_TEXT:raise ValueError('REFERENCE_PDF_TEXT_FALLBACK_FAILED_OR_LIMIT')
    pages=result.stdout.decode('utf-8',errors='strict').split('\f')
    if len(pages)!=page_count+1 or pages[-1].strip():raise ValueError('REFERENCE_PDF_TEXT_FALLBACK_PAGE_ALIGNMENT')
    if poppler_profile()!=profile:raise ValueError('REFERENCE_PDF_TEXT_TOOL_CHANGED')
    return pages[:-1],{**profile,'version':(version.stdout+version.stderr).splitlines()[0][:150]}
def search_text(text):return unicodedata.normalize('NFKC',text).casefold()
def scripts(text):
    found=[]
    if re.search('[\u3400-\u9fff]',text):found.append('HAN_PRESENT_LANGUAGE_NOT_INFERRED')
    if re.search('[A-Za-z]',text):found.append('LATIN_PRESENT')
    return found or ['OTHER_OR_NO_TEXT']

def extract(name,raw):
    if len(raw)>intake_files.MAX_FILE:raise ValueError('REFERENCE_SOURCE_RESOURCE_LIMIT')
    source_sha=hashlib.sha256(raw).hexdigest();segments=[];gaps=[];total=0;parser='Python standard library'
    suffix=Path(name).suffix.lower();metadata={'translation':'NOT_PROVIDED','ocr':'NOT_PERFORMED','source_language':'PRESERVED_NOT_AUTOMATICALLY_INFERRED'}
    def add(locator,text,label):
        nonlocal total
        if not isinstance(text,str):raise ValueError('REFERENCE_TEXT_TYPE')
        if len(text)>CHUNK:
            for offset in range(0,len(text),CHUNK):
                add({**locator,'text_start':offset,'text_end':min(len(text),offset+CHUNK),'offset_basis':'EXTRACTED_DERIVATIVE_CHARACTERS'},text[offset:offset+CHUNK],label+' · text '+str(offset+1))
            return
        if not text.strip():return
        total+=len(text.encode())
        if total>MAX_TEXT or len(segments)>=MAX_SEGMENTS:raise ValueError('REFERENCE_EXTRACTION_RESOURCE_LIMIT')
        locator_id=digest({'source_sha256':source_sha,'locator':locator})
        text_sha=hashlib.sha256(text.encode()).hexdigest()
        segments.append({'id':digest({'locator_id':locator_id,'text_sha256':text_sha}),'locator_id':locator_id,'source_sha256':source_sha,
           'locator':locator,'label':label,'text':text,'text_sha256':text_sha,'scripts':scripts(text),'content_trust':'UNTRUSTED_SOURCE_DATA'})
    def plain_xml(node):
        out=[]
        for child in node.iter():
            if child.tag==W+'t':out.append(child.text or '')
            elif child.tag==W+'tab':out.append('\t')
            elif child.tag==W+'br':out.append('\n')
        return ''.join(out)
    if suffix=='.pdf':
        try:import pypdf
        except ImportError:raise ValueError('REFERENCE_PDF_DEPENDENCY_UNAVAILABLE') from None
        parser='pypdf '+pypdf.__version__;reader=pypdf.PdfReader(io.BytesIO(raw),strict=True)
        if reader.is_encrypted:raise ValueError('REFERENCE_PDF_ENCRYPTED')
        root=reader.trailer['/Root']
        names=root.get('/Names',{});names=names.get_object() if hasattr(names,'get_object') else names
        action=root.get('/OpenAction');action=action.get_object() if hasattr(action,'get_object') else action
        # A passive local destination is normal PDF navigation, not a script.
        # No action is executed. Chained/script/launch actions remain held.
        passive=action is None or isinstance(action,list) or isinstance(action,dict) and action.get('/S')=='/GoTo' and '/Next' not in action
        if not passive or '/AA' in root or '/JavaScript' in names or '/EmbeddedFiles' in names:raise ValueError('REFERENCE_ACTIVE_DOCUMENT_CONTENT')
        if len(reader.pages)>MAX_PAGES:raise ValueError('REFERENCE_PDF_PAGE_LIMIT')
        labels=reader.page_labels;label_basis='PDF_PAGE_LABELS' if '/PageLabels' in root else 'PHYSICAL_PAGE_NUMBER_FALLBACK'
        metadata.update(pages=len(reader.pages),page_labels_basis=label_basis,tables='PAGE_TEXT_ONLY_NOT_CELL_RECONSTRUCTION',text_accuracy='EXTRACTION_NOT_GLYPH_OR_SEMANTIC_PROOF')
        missing_maps=[index for index,page in enumerate(reader.pages) if missing_identity_map(page.get('/Resources'))];mapped=None;mapping_error=None
        if missing_maps:
            try:
                mapped,profile=mapped_pdf_text(raw,len(reader.pages));metadata.update(unicode_map_fallback=profile,fallback_page_indices=missing_maps);parser+=' + Poppler '+profile['version']
            except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
                mapping_error=str(exc) if isinstance(exc,ValueError) else 'REFERENCE_PDF_UNICODE_MAP_FALLBACK_FAILED';metadata['unicode_map_fallback']='UNAVAILABLE_OR_UNQUALIFIED'
        for index,page in enumerate(reader.pages):
            if '/AA' in page:raise ValueError('REFERENCE_ACTIVE_DOCUMENT_CONTENT')
            stream=page.get_contents()
            if stream is not None and len(stream.get_data())>4*1024*1024:raise ValueError('REFERENCE_PDF_CONTENT_LIMIT')
            if index in missing_maps and mapped is None:gaps.append({'kind':mapping_error,'page_index':index});continue
            text=mapped[index] if index in missing_maps else page.extract_text() or ''
            if not text.strip():gaps.append({'kind':'OCR_OR_TEXT_LAYER_REQUIRED','page_index':index});continue
            add({'kind':'pdf_page','page_index':index,'page_label':str(labels[index]),'page_label_basis':label_basis},text,'PDF page '+str(index+1)+' · label '+str(labels[index]))
    elif suffix=='.docx':
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            intake_files.checked_zip(z,package_parts=True)
            if any('vbaproject' in n.casefold() or n.endswith('.bin') for n in z.namelist()):raise ValueError('REFERENCE_ACTIVE_DOCUMENT_CONTENT')
            xml=z.read('word/document.xml')
            if len(xml)>MAX_TEXT or b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():raise ValueError('REFERENCE_XML_LIMIT_OR_ENTITY')
            doc=ET.fromstring(xml);body=doc.find(W+'body')
            if body is None:raise ValueError('REFERENCE_DOCX_BODY_MISSING')
            for index,node in enumerate(body):
                if node.tag==W+'p':add({'kind':'docx_paragraph','part':'word/document.xml','body_index':index},plain_xml(node),'Paragraph '+str(index+1))
                elif node.tag==W+'tbl':
                    for row_index,row in enumerate(node.findall(W+'tr')):
                        for col_index,cell in enumerate(row.findall(W+'tc')):
                            add({'kind':'docx_table_cell','part':'word/document.xml','body_index':index,'row':row_index,'column':col_index,'column_basis':'OOXML_TC_INDEX_NOT_VISUAL_MERGED_GRID_COLUMN'},plain_xml(cell),
                                'Table at body '+str(index+1)+' · row '+str(row_index+1)+' · column '+str(col_index+1))
            metadata.update(pagination='NOT_INFERRED_FROM_OOXML',tables='EXACT_OOXML_CELL_ADDRESS')
    elif suffix in ('.csv','.tsv'):
        rows=csv.reader(io.StringIO(raw.decode('utf-8-sig')),delimiter='\t' if suffix=='.tsv' else ',');header=next(rows,None)
        if not header or len(header)!=len(set(header)) or len(header)>256:raise ValueError('REFERENCE_CSV_HEADER')
        for row_index,row in enumerate(rows,start=1):
            if len(row)!=len(header):raise ValueError('REFERENCE_CSV_WIDTH')
            for col_index,value in enumerate(row):
                add({'kind':'csv_cell','record_index':row_index,'column':col_index,'header':header[col_index]},value,
                    'Record '+str(row_index)+' · '+header[col_index])
        metadata['row_number_basis']='LOGICAL_RECORD_INDEX_HEADER_IS_ZERO'
    elif suffix=='.json':
        data=records.strict(raw)
        def visit(value,pointer='',depth=0):
            if depth>24:raise ValueError('REFERENCE_JSON_DEPTH')
            if isinstance(value,dict):
                for key,child in value.items():visit(child,pointer+'/'+key.replace('~','~0').replace('/','~1'),depth+1)
            elif isinstance(value,list):
                for index,child in enumerate(value):visit(child,pointer+'/'+str(index),depth+1)
            else:add({'kind':'json_pointer','pointer':pointer},value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,allow_nan=False),'JSON '+(pointer or '/'))
        visit(data)
    elif suffix in ('.kicad_sch','.kicad_pcb','.kicad_sym','.kicad_mod'):
        from workbench.viewer_data import parse
        tree=parse(raw.decode('utf-8-sig'));seen=set();visited=0
        def visit(node,path=(),depth=0):
            nonlocal visited
            visited+=1
            if visited>300000 or depth>128:raise ValueError('REFERENCE_CAD_TREE_LIMIT')
            if not isinstance(node,list):return
            uuids=[child[1] for child in node if isinstance(child,list) and len(child)==2 and child[0]=='uuid']
            if uuids:
                ident=str(uuids[0])
                if len(uuids)!=1 or ident in seen:raise ValueError('REFERENCE_CAD_UUID_AMBIGUOUS')
                seen.add(ident)
                properties={str(v[1]):str(v[2]) for v in node if isinstance(v,list) and len(v)>=3 and v[0]=='property'}
                text=json.dumps({'head':node[0],'uuid':ident,'properties':properties},ensure_ascii=False)
                add({'kind':'kicad_object','uuid':ident,'sexp_path':list(path),'head':str(node[0])},text,properties.get('Reference',str(node[0]))+' · '+ident)
            for index,child in enumerate(node):
                if isinstance(child,list):visit(child,path+(index,),depth+1)
        visit(tree);metadata['native_result']='PARSED_SOURCE_OBJECT_IDENTITY_NOT_ERC_DRC_OR_PHYSICAL'
        if not segments:gaps.append({'kind':'NO_NATIVE_UUID_LOCATORS'})
    elif suffix in ('.md','.txt','.rst','.py','.c','.h','.cpp','.hpp','.sv','.v','.s','.sh','.ld','.kicad_pro'):
        text=raw.decode('utf-8-sig')
        if '\x00' in text:raise ValueError('REFERENCE_NUL_TEXT')
        rows=text.splitlines(keepends=True);start=0
        while start<len(rows):
            end=start;size=0
            while end<len(rows) and end-start<16 and (size+len(rows[end])<=CHUNK or end==start):size+=len(rows[end]);end+=1
            add({'kind':'text_lines','line_start':start+1,'line_end':end},''.join(rows[start:end]),'Lines '+str(start+1)+'-'+str(end));start=end
    else:gaps.append({'kind':'OCR_OR_SUPPORTED_TEXT_PROFILE_REQUIRED'})
    if not segments:gaps.append({'kind':'NO_SEARCHABLE_TEXT'})
    return {'schema':'arc.reference-extraction/1','source_sha256':source_sha,'extractor':VERSION,'rule_hash':rule_hash(),'parser':parser,
       'metadata':metadata,'segments':segments,'gaps':gaps,'text_bytes':total,'fact_verification':'NOT_IMPLIED_BY_EXTRACTION'}

def bounded(name,path,digest_expected):
    if os.name=='nt' and Path(name).suffix.lower()=='.pdf':return {'schema':VERSION,'source_sha256':digest_expected,'segments':[],'gaps':[{'kind':'PDF_HARD_MEMORY_LIMIT_UNQUALIFIED_ON_WINDOWS'}],'metadata':{},'parser':'NOT_RUN','rule_hash':rule_hash()}
    root=Path(__file__).resolve().parents[3]
    env={k:v for k,v in os.environ.items() if k in ('PATH','SystemRoot','WINDIR','TEMP','TMP','LANG')};env['PYTHONPATH']=str(root)
    context={'name':name,'path':str(path),'sha256':digest_expected}
    try:
        result=subprocess.run([sys.executable,'-m','sdk.cli.arc1cli.reference_extract','--worker'],input=records.canonical(context),
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=25,cwd=root,env=env)
        if len(result.stdout)>20*1024*1024:raise ValueError('REFERENCE_WORKER_FAILED_OR_RESOURCE_LIMIT')
        if result.returncode:
            try:code=records.strict(result.stdout).get('error','')
            except (ValueError,AttributeError):code=''
            raise ValueError(code if isinstance(code,str) and re.fullmatch(r'REFERENCE_[A-Z0-9_]+',code) else 'REFERENCE_WORKER_FAILED_OR_RESOURCE_LIMIT')
        return records.strict(result.stdout)
    except subprocess.TimeoutExpired:raise ValueError('REFERENCE_EXTRACTION_TIME_LIMIT') from None

def main():
    if sys.argv[1:]!=['--worker']:return 2
    if os.name!='nt':
        import resource
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        inherited=resource.getrlimit(resource.RLIMIT_AS)
        cap=min([1024**3]+[v for v in inherited if v!=resource.RLIM_INFINITY])
        resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
    context=records.strict(sys.stdin.buffer.read(16384));raw=intake_files.read_stable(Path(context['path']))
    if hashlib.sha256(raw).hexdigest()!=context['sha256']:raise ValueError('REFERENCE_ORIGINAL_CHANGED')
    try:result=extract(context['name'],raw)
    except (ValueError,ImportError,OSError) as exc:
        code=str(exc);code=code if re.fullmatch(r'REFERENCE_[A-Z0-9_]+',code) else 'REFERENCE_EXTRACTION_FAILED'
        sys.stdout.buffer.write(records.canonical({'error':code}));return 2
    sys.stdout.buffer.write(records.canonical(result));return 0

if __name__=='__main__':raise SystemExit(main())
