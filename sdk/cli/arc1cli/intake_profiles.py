"""Deterministic admission checks. Parsing and admission never prove hardware behavior."""
from __future__ import annotations
import ast,csv,hashlib,io,json,posixpath,re,zipfile,os,subprocess,sys
from pathlib import PurePosixPath,Path
from xml.etree import ElementTree
from . import record_store as records,intake_files

VERSION='arc.intake-profiles/1'
PROFILES=('text_document','docx_document','pdf_document','structured_json','structured_csv','chip_record','code','cad','image_reference','unclassified')
AUTO_PROFILES=('text_document','docx_document','structured_json','structured_csv','chip_record')
TEXT_LIMIT=2*1024*1024
INDEX_LIMIT=128*1024

def rule_hash():return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
def profile_for(name):
    suffix=PurePosixPath(name).suffix.lower()
    if suffix in ('.md','.txt','.rst'):return 'text_document'
    if suffix=='.docx':return 'docx_document'
    if suffix=='.pdf':return 'pdf_document'
    if suffix=='.json':return 'structured_json'
    if suffix in ('.csv','.tsv'):return 'structured_csv'
    if suffix in ('.c','.h','.cpp','.hpp','.py','.sv','.v','.s','.sh','.ld'):return 'code'
    if suffix in ('.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_mod','.kicad_sym'):return 'cad'
    if suffix in ('.png','.jpg','.jpeg','.webp'):return 'image_reference'
    return 'unclassified'

def dependency(name,relative):
    if not isinstance(relative,str) or not relative or '\\' in relative or relative.startswith('/') or ':' in relative:raise ValueError('DEPENDENCY_PATH_INVALID')
    joined=posixpath.normpath(posixpath.join(posixpath.dirname(name),relative))
    return records.safe_name(joined)

def evaluate(name,raw,available,variants,scope='current'):
    profile=profile_for(name);reasons=[];dependencies=[];text='';structure='NOT_CHECKED';parser='stdlib';facts={}
    def need(relative,expected=None):
        target=dependency(name,relative)
        if target==name:raise ValueError('SELF_DEPENDENCY')
        if len(dependencies)>=100:raise ValueError('DEPENDENCY_LIMIT')
        entry={'path':target,'basis':'DECLARED_OR_FILETYPE_CONTRACT','expected_sha256':expected}
        dependencies.append(entry)
        if target not in available:reasons.append('MISSING_COUNTERPART: '+target)
        elif expected and available[target]['sha256']!=expected:reasons.append('DEPENDENCY_SOURCE_HASH_MISMATCH: '+target)
    try:
        suffix=PurePosixPath(name).suffix.lower()
        if profile in ('text_document','structured_json','structured_csv','code','cad'):
            if len(raw)>TEXT_LIMIT and profile!='cad':return held(profile,'TEXT_PARSER_LIMIT')
            text=raw.decode('utf-8-sig')
            if '\x00' in text:raise ValueError('NUL_IN_TEXT_SOURCE')
        if profile=='text_document':
            if not text.strip():raise ValueError('EMPTY_DOCUMENT')
            structure='UTF8_TEXT_READ'
        elif profile=='structured_json':
            data=records.strict(raw);structure='STRICT_JSON_PARSED'
            if isinstance(data,dict) and data.get('schema')=='arc.intake-chip/1':
                profile='chip_record';required={'schema','part','variant','source','source_sha256'}
                if not required<=set(data) or not all(isinstance(data[k],str) and data[k] for k in required):raise ValueError('CHIP_RECORD_REQUIRED_FIELDS')
                if not re.fullmatch(r'[0-9a-f]{64}',data['source_sha256']):raise ValueError('CHIP_SOURCE_DIGEST_INVALID')
                facts={'part':data['part'],'variant':data['variant']}
                if data['variant'] not in variants:raise ValueError('PART_VARIANT_MISMATCH: '+data['variant'])
                need(data['source'],data['source_sha256']);structure='CHIP_SCHEMA_AND_SOURCE_BINDING_CHECKED'
            if isinstance(data,dict) and 'dependencies' in data:
                if not isinstance(data['dependencies'],list):raise ValueError('DEPENDENCY_DECLARATION_SCHEMA')
                for declared in data['dependencies']:need(declared)
        elif profile=='structured_csv':
            reader=csv.reader(io.StringIO(text),delimiter='\t' if suffix=='.tsv' else ',');header=next(reader,None)
            if not header or len(header)!=len(set(header)) or len(header)>256:raise ValueError('CSV_HEADER_INVALID')
            count=0
            for row in reader:
                if row and len(row)!=len(header):raise ValueError('CSV_ROW_WIDTH_MISMATCH')
                count+=1
                if count>200000:raise ValueError('CSV_ROW_LIMIT')
            structure='CSV_SHAPE_PARSED';facts={'columns':header,'rows':count}
        elif profile=='code':
            if suffix=='.py':ast.parse(text,filename=name);structure='PYTHON_AST_PARSED_NOT_EXECUTED'
            else:structure='UTF8_AND_DECLARED_INCLUDES_ONLY'
            for include in re.findall(r'^\s*#\s*include\s*"([^"\n]+)"',text,re.MULTILINE):need(include)
        elif profile=='cad':
            if len(raw)>16*1024*1024:return held(profile,'CAD_INSPECTION_LIMIT')
            if suffix=='.kicad_pro':records.strict(raw);structure='KICAD_PROJECT_JSON_PARSED'
            else:
                # Reuse Ledger's existing Qt-free inspection parser.
                from workbench import viewer_data
                node=viewer_data.parse(text);expected={'.kicad_pcb':'kicad_pcb','.kicad_sch':'kicad_sch','.kicad_mod':'footprint','.kicad_sym':'kicad_symbol_lib'}[suffix]
                if not node or node[0]!=expected:raise ValueError('CAD_ROOT_TYPE_MISMATCH')
                structure='KICAD_SEXPRESSION_PARSED_NOT_ERC_DRC'
                if suffix in ('.kicad_pcb','.kicad_sch'):
                    need(PurePosixPath(name).stem+('.kicad_sch' if suffix=='.kicad_pcb' else '.kicad_pcb'))
                if suffix=='.kicad_sch':
                    for relative in re.findall(r'\(property\s+"Sheetfile"\s+"([^"\n]+)"',text):
                        relative=relative.replace('${KIPRJMOD}/','')
                        if '${' in relative:reasons.append('UNRESOLVED_CAD_PATH_VARIABLE')
                        else:need(relative)
        elif profile=='docx_document':
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                members=intake_files.checked_zip(archive,package_parts=True);names={member.filename for member in members}
                if not {'[Content_Types].xml','word/document.xml'}<=names:raise ValueError('DOCX_REQUIRED_PARTS_MISSING')
                if any('vbaproject' in name.casefold() or name.endswith('.bin') for name in names):return held(profile,'ACTIVE_DOCUMENT_CONTENT_REQUIRES_SEPARATE_REVIEW')
                document=archive.read('word/document.xml')
                if len(document)>TEXT_LIMIT or b'<!DOCTYPE' in document.upper() or b'<!ENTITY' in document.upper():raise ValueError('DOCX_XML_LIMIT_OR_ENTITY')
                root=ElementTree.fromstring(document)
                if root.tag!='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document':raise ValueError('DOCX_ROOT_INVALID')
                paragraphs=[''.join(p.itertext()) for p in root.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')]
                text='\n'.join(paragraphs);structure='OOXML_DOCUMENT_PARSED';facts={'paragraphs':len(paragraphs)}
        elif profile=='pdf_document':
            try:
                import pypdf
            except ImportError:return held(profile,'PDF_PARSER_UNAVAILABLE')
            parser='pypdf '+pypdf.__version__;reader=pypdf.PdfReader(io.BytesIO(raw),strict=True)
            if reader.is_encrypted:return held(profile,'ENCRYPTED_DOCUMENT_REQUIRES_OWNER_HANDLING')
            root=reader.trailer['/Root']
            action=root.get('/OpenAction');action=action.get_object() if hasattr(action,'get_object') else action
            passive=action is None or isinstance(action,list) or isinstance(action,dict) and action.get('/S')=='/GoTo' and '/Next' not in action
            names=root.get('/Names',{});names=names.get_object() if hasattr(names,'get_object') else names
            if not passive or '/AA' in root or '/JavaScript' in names or '/EmbeddedFiles' in names:return held(profile,'ACTIVE_DOCUMENT_CONTENT_REQUIRES_SEPARATE_REVIEW')
            pages=len(reader.pages)
            if not 1<=pages<=3000:return held(profile,'PDF_PAGE_LIMIT')
            chunks=[]
            for page in list(reader.pages)[:16]:
                content=page.get_contents()
                if content is not None and len(content.get_data())>4*1024*1024:return held(profile,'PDF_CONTENT_STREAM_LIMIT')
                chunks.append(page.extract_text() or '')
            text='\n'.join(chunks);structure='PDF_PAGE_TREE_AND_BOUNDED_TEXT_PARSED';facts={'pages':pages,'text_preview_pages':min(16,pages),'ocr':'NOT_PERFORMED'}
        elif profile=='image_reference':
            try:from PIL import Image
            except ImportError:return held(profile,'IMAGE_PARSER_UNAVAILABLE')
            with Image.open(io.BytesIO(raw)) as image:
                if image.width*image.height>40_000_000:return held(profile,'IMAGE_DIMENSION_LIMIT')
                facts={'width':image.width,'height':image.height,'format':image.format};image.verify()
            structure='IMAGE_CONTAINER_VERIFIED_ARTISTIC_REFERENCE_ONLY'
        else:return held(profile,'UNSUPPORTED_INTAKE_PROFILE')
    except (ValueError,UnicodeError,SyntaxError,ElementTree.ParseError,zipfile.BadZipFile,RecursionError,OverflowError) as exc:
        return {'profile':profile,'eligible':False,'recommendation':'REJECTED','reasons':[str(exc)[:300]],'dependencies':dependencies,
                'qualification':qualification('FAILED_STRUCTURAL_CHECK',parser,scope),'index_text':'','facts':facts}
    except MemoryError:return held(profile,'PARSER_RESOURCE_LIMIT')
    except Exception as exc:
        return held(profile,'PARSER_FAILED: '+type(exc).__name__)
    return {'profile':profile,'eligible':not reasons,'recommendation':'ELIGIBLE' if not reasons else 'HELD','reasons':reasons,
            'dependencies':dependencies,'index_text':text[:INDEX_LIMIT],'index_preview_truncated':len(text)>INDEX_LIMIT,
            'qualification':qualification(structure,parser,scope),'facts':facts,'rule_version':VERSION,'rule_hash':rule_hash()}

def qualification(structure,parser,scope):
    return {'source_identity':'SHA256_BOUND','structural_check':structure,'parser':parser,'native_result':'NOT_RUN',
            'physical_hardware':'NOT_QUALIFIED','source_promotion':'NOT_GRANTED',
            'applicability':'HISTORICAL_REFERENCE' if scope=='historical' else 'CURRENT_REFERENCE_SOURCE_ONLY'}

def held(profile,reason):
    return {'profile':profile,'eligible':False,'recommendation':'HELD','reasons':[reason],'dependencies':[],'index_text':'',
            'qualification':qualification('INCOMPLETE','NOT_QUALIFIED','current'),'facts':{}}

def inspect_optional(name,path,digest,available,variants,scope):
    """Optional binary parsers run outside the Qt/Kernel process with hard limits.

    The initial Windows adapter has no qualified hard memory limiter; it holds
    these optional profiles until a separately measured worker is available.
    """
    profile=profile_for(name)
    if os.name=='nt':return held(profile,'OPTIONAL_BINARY_PARSER_MEMORY_LIMIT_UNQUALIFIED_ON_WINDOWS')
    context={'name':name,'path':str(path),'sha256':digest,'available':{k:{'sha256':v['sha256']} for k,v in available.items()},'variants':variants,'scope':scope}
    try:
        root=Path(__file__).resolve().parents[3]
        env={key:value for key,value in os.environ.items() if key in ('PATH','SystemRoot','WINDIR','TEMP','TMP','LANG')}
        env['PYTHONPATH']=str(root)
        result=subprocess.run([sys.executable,'-m','sdk.cli.arc1cli.intake_profiles','--bounded-worker'],
            input=records.canonical(context),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=12,check=False,cwd=root,env=env)
        if result.returncode or len(result.stdout)>1024*1024:return held(profile,'OPTIONAL_PARSER_FAILED_OR_RESOURCE_LIMIT')
        return records.strict(result.stdout)
    except subprocess.TimeoutExpired:return held(profile,'OPTIONAL_PARSER_TIME_LIMIT')

def main():
    if sys.argv[1:]!=['--bounded-worker']:return 2
    import resource
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
    data=sys.stdin.buffer.read(4*1024*1024+1)
    if len(data)>4*1024*1024:return 2
    context=records.strict(data);raw=intake_files.read_stable(Path(context['path']))
    if hashlib.sha256(raw).hexdigest()!=context['sha256']:return 2
    result=evaluate(context['name'],raw,context['available'],context['variants'],context['scope'])
    sys.stdout.buffer.write(records.canonical(result));return 0

if __name__=='__main__':raise SystemExit(main())
