"""Bounded, original-bound PDF page derivatives. No Qt, network or authority.

Poppler positions retain page context; they do not infer table semantics. OCR
is an explicit derivative with engine scores, never an accepted transcription.
"""
from __future__ import annotations
import base64,csv,hashlib,io,json,math,os,re,shutil,struct,subprocess,sys,tempfile
from pathlib import Path
from xml.etree import ElementTree as ET
from . import intake_files,record_store as records,reference_extract as legacy

VERSION='arc.pdf-evidence/1'
MAX_PAGES=512
MAX_IMAGE=6*1024*1024
MAX_TEXT=8*1024*1024
MAX_WORDS=6000
LANGUAGES=('eng','chi_sim','chi_tra','eng+chi_sim','eng+chi_tra')

class PDFError(ValueError):pass

def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest(value):return sha(records.canonical(value))
def page_id(source_sha,index):return digest({'schema':'arc.pdf-page/1','source_sha256':source_sha,'page_index':index})
def citation(namespace,item,source_sha,index,region=None):
    if not all(isinstance(v,str) and re.fullmatch(r'[a-f0-9]{32}',v) for v in (namespace,item)) or not re.fullmatch(r'[a-f0-9]{64}',source_sha) or type(index) is not int or not 0<=index<MAX_PAGES:raise PDFError('PDF_CITATION_INVALID')
    return {'schema':'arc.pdf-citation/1','namespace':namespace,'item':item,'source_sha256':source_sha,'page_index':index,'rect':rect(region or [0,0,1,1])}
def rect(value):
    if not isinstance(value,list) or len(value)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in value):raise PDFError('PDF_REGION_INVALID')
    x,y,w,h=map(float,value)
    if min(x,y)<0 or w<=0 or h<=0 or x+w>1.000001 or y+h>1.000001:raise PDFError('PDF_REGION_OUTSIDE_PAGE')
    return [round(v,6) for v in (x,y,w,h)]

def tool(name):
    found=shutil.which(name)
    if not found:raise PDFError('PDF_TOOL_UNAVAILABLE_'+name.upper())
    path=Path(found).resolve()
    result=subprocess.run([str(path),'--version' if name=='tesseract' else '-v'],capture_output=True,timeout=5)
    if result.returncode:raise PDFError('PDF_TOOL_PROFILE_FAILED')
    version=(result.stdout+result.stderr).decode('utf-8',errors='replace').splitlines()[0][:180]
    return {'name':name,'executable_sha256':records.sha(path),'version':version},path

def unchanged(profile,path):
    if records.sha(path)!=profile['executable_sha256']:raise PDFError('PDF_TOOL_CHANGED_DURING_READ')

def profile():
    import pypdf
    result={'schema':VERSION,'pypdf':pypdf.__version__,'tools':{},'ocr_languages':[]}
    for name in ('pdftotext','pdftoppm','tesseract'):
        try:result['tools'][name]=tool(name)[0]
        except (PDFError,OSError,subprocess.SubprocessError):result['tools'][name]={'state':'UNAVAILABLE'}
    if result['tools']['tesseract'].get('state')!='UNAVAILABLE':
        try:
            _,path=tool('tesseract');run=subprocess.run([str(path),'--list-langs'],capture_output=True,text=True,timeout=5)
            result['ocr_languages']=[v for v in run.stdout.splitlines() if v in ('eng','chi_sim','chi_tra')]
        except (OSError,subprocess.SubprocessError):pass
    return result

def reader(raw):
    try:import pypdf
    except ImportError:raise PDFError('PDF_PARSER_UNAVAILABLE') from None
    if len(raw)>intake_files.MAX_FILE or not raw.startswith(b'%PDF-'):raise PDFError('PDF_SOURCE_INVALID_OR_LIMIT')
    try:r=pypdf.PdfReader(io.BytesIO(raw),strict=True)
    except Exception:raise PDFError('PDF_CORRUPT_OR_UNSUPPORTED') from None
    if r.is_encrypted:raise PDFError('PDF_RESTRICTED_ENCRYPTED')
    root=r.trailer['/Root'];names=root.get('/Names',{});names=names.get_object() if hasattr(names,'get_object') else names
    action=root.get('/OpenAction');action=action.get_object() if hasattr(action,'get_object') else action
    passive=action is None or isinstance(action,list) or isinstance(action,dict) and action.get('/S')=='/GoTo' and '/Next' not in action
    if not passive or '/AA' in root or '/JavaScript' in names or '/EmbeddedFiles' in names:raise PDFError('PDF_ACTIVE_CONTENT_HELD')
    form=root.get('/AcroForm');form=form.get_object() if hasattr(form,'get_object') else form
    if form and '/XFA' in form:raise PDFError('PDF_ACTIVE_CONTENT_HELD')
    if not 1<=len(r.pages)<=MAX_PAGES:raise PDFError('PDF_PAGE_COUNT_LIMIT')
    for page in r.pages:
        if '/AA' in page:raise PDFError('PDF_ACTIVE_CONTENT_HELD')
        for annotation in page.get('/Annots',[]):
            obj=annotation.get_object();action=obj.get('/A');action=action.get_object() if hasattr(action,'get_object') else action
            if '/AA' in obj or obj.get('/Subtype') in ('/RichMedia','/Movie','/Sound','/FileAttachment') or action and (action.get('/S') not in ('/GoTo','/URI') or '/Next' in action):raise PDFError('PDF_ACTIVE_CONTENT_HELD')
        stream=page.get_contents()
        if stream is not None and len(stream.get_data())>4*1024*1024:raise PDFError('PDF_PAGE_STREAM_LIMIT')
    return r

def inspect(raw):
    r=reader(raw);source_sha=sha(raw);labels=r.page_labels;labelled='/PageLabels' in r.trailer['/Root']
    pages=[]
    for index,p in enumerate(r.pages):
        box=list(map(float,p.cropbox));rotation=int(p.get('/Rotate',0))%360
        if rotation not in (0,90,180,270) or any(not math.isfinite(v) for v in box) or not 0<box[2]-box[0]<=14400 or not 0<box[3]-box[1]<=14400:raise PDFError('PDF_PAGE_GEOMETRY_UNSUPPORTED')
        pages.append({'page_index':index,'physical_page':index+1,'page_id':page_id(source_sha,index),
            'pdf_label':str(labels[index])[:120] if labelled else None,'pdf_label_basis':'PDF_METADATA' if labelled else 'NOT_DECLARED',
            'printed_page':'NOT_ESTABLISHED','crop_box_points':box,'rotation':rotation})
    return {'schema':VERSION,'source_sha256':source_sha,'pages':pages,'page_count':len(pages),
        'pagination':'PHYSICAL_INDEX_AND_PDF_LABEL_ARE_SEPARATE_FROM_PRINTED_TEXT','active_content':'NOT_EXECUTED',
        'external_links':'INERT_NOT_FOLLOWED','parser':'pypdf '+__import__('pypdf').__version__}

def native_pages(raw):
    info=inspect(raw);measured,path=tool('pdftotext')
    with tempfile.TemporaryDirectory(prefix='ledger-pdf-text-') as temp:
        source=Path(temp)/'source.pdf';target=Path(temp)/'text.txt';source.write_bytes(raw)
        run=subprocess.run([str(path),'-layout','-cropbox','-enc','UTF-8','-eol','unix',str(source),str(target)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
        if run.returncode or not target.is_file() or target.stat().st_size>MAX_TEXT:raise PDFError('PDF_NATIVE_TEXT_FAILED_OR_LIMIT')
        text=target.read_text(encoding='utf-8');pages=text.split('\f')
    unchanged(measured,path)
    if len(pages)!=info['page_count']+1 or pages[-1].strip():raise PDFError('PDF_NATIVE_PAGE_ALIGNMENT_FAILED')
    return info,pages[:-1],measured

def extraction(raw):
    info,pages,measured=native_pages(raw);segments=[];gaps=[];total=0
    for page,text in zip(info['pages'],pages):
        index=page['page_index'];label=page['pdf_label'] or str(index+1)
        loc={'kind':'pdf_page','page_index':index,'page_label':label,'page_label_basis':'PDF_PAGE_LABELS' if page['pdf_label'] is not None else 'PHYSICAL_PAGE_NUMBER_FALLBACK'}
        if not text.strip():gaps.append({'kind':'OCR_OR_TEXT_LAYER_REQUIRED','page_index':index});continue
        for offset in range(0,len(text),legacy.CHUNK):
            body=text[offset:offset+legacy.CHUNK]
            if not body.strip():continue
            locator={**loc,**({'text_start':offset,'text_end':min(len(text),offset+legacy.CHUNK),'offset_basis':'EXTRACTED_DERIVATIVE_CHARACTERS'} if len(text)>legacy.CHUNK else {})}
            locator_id=legacy.digest({'source_sha256':info['source_sha256'],'locator':locator});text_sha=sha(body.encode())
            segments.append({'id':legacy.digest({'locator_id':locator_id,'text_sha256':text_sha}),'locator_id':locator_id,
                'source_sha256':info['source_sha256'],'locator':locator,'label':'PDF physical page '+str(index+1)+' · PDF label '+(page['pdf_label'] or 'not declared'),
                'text':body,'text_sha256':text_sha,'scripts':legacy.scripts(body),'content_trust':'UNTRUSTED_SOURCE_DATA'})
            total+=len(body.encode())
            if len(segments)>legacy.MAX_SEGMENTS or total>MAX_TEXT:raise PDFError('PDF_TEXT_BUDGET')
    if not segments:gaps.append({'kind':'NO_SEARCHABLE_TEXT'})
    return {'schema':legacy.VERSION,'source_sha256':info['source_sha256'],'extractor':VERSION,'rule_hash':rule_hash(),
        'parser':'Poppler '+measured['version'],'metadata':{'pages':info['page_count'],'physical_pages':info['pages'],
        'translation':'NOT_PROVIDED','ocr':'NOT_PERFORMED','tables':'POSITIONED_PAGE_CONTEXT_NOT_SEMANTIC_CELL_RECONSTRUCTION',
        'native_tool':measured,'printed_pagination':'NOT_INFERRED_FROM_PDF_LABELS'},'segments':segments,'gaps':gaps,'text_bytes':total,'fact_verification':'NOT_IMPLIED_BY_EXTRACTION'}

def word_layout(path,page_index,rotation=0):
    measured,exe=tool('pdftotext');target=path.parent/'layout.xhtml'
    run=subprocess.run([str(exe),'-f',str(page_index+1),'-l',str(page_index+1),'-bbox-layout','-cropbox','-enc','UTF-8',str(path),str(target)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
    if run.returncode or not target.is_file() or target.stat().st_size>MAX_TEXT:raise PDFError('PDF_NATIVE_LAYOUT_FAILED_OR_LIMIT')
    raw=target.read_bytes()
    if b'<!ENTITY' in raw.upper():raise PDFError('PDF_LAYOUT_ENTITY_HELD')
    xml=ET.fromstring(raw);node=next((n for n in xml.iter() if n.tag.rsplit('}',1)[-1]=='page'),None)
    if node is None:raise PDFError('PDF_LAYOUT_PAGE_MISSING')
    width=float(node.attrib['width']);height=float(node.attrib['height'])
    # Poppler bbox word coordinates include page rotation, while the XHTML
    # page attributes retain the unrotated crop dimensions. Raster output is
    # rotated. Normalize against that same visible page, not the attributes.
    if rotation in (90,270):width,height=height,width
    if not all(math.isfinite(v) and v>0 for v in (width,height)):raise PDFError('PDF_LAYOUT_GEOMETRY_INVALID')
    words=[];lines=[];omitted=0
    for line in (n for n in node.iter() if n.tag.rsplit('}',1)[-1]=='line'):
        ids=[]
        for word in (n for n in line if n.tag.rsplit('}',1)[-1]=='word'):
            text=''.join(word.itertext());x0,y0,x1,y1=[float(word.attrib[k]) for k in ('xMin','yMin','xMax','yMax')]
            if not text or not all(math.isfinite(v) for v in (x0,y0,x1,y1)) or x1<=x0 or y1<=y0:continue
            if x0<-.01 or y0<-.01 or x1>width+.01 or y1>height+.01:omitted+=1;continue
            box=rect([max(0,x0)/width,max(0,y0)/height,(min(width,x1)-max(0,x0))/width,(min(height,y1)-max(0,y0))/height])
            ids.append(len(words));words.append({'text':text,'rect':box})
            if len(words)>MAX_WORDS:raise PDFError('PDF_WORD_COUNT_LIMIT')
        if ids:lines.append(ids)
    unchanged(measured,exe)
    text='\n'.join(' '.join(words[i]['text'] for i in line) for line in lines)
    return {'text':text,'words':words,'lines':lines,'tool':measured,'outside_crop_words_omitted':omitted,
        'coordinates':'NORMALIZED_TOP_LEFT_CROPPED_RENDER','status':'NATIVE_TEXT' if words else 'NO_NATIVE_TEXT',
        'limitations':['WORD_POSITIONS_NOT_TABLE_CELL_SEMANTICS','CHECK_READING_ORDER_AGAINST_IMAGE']}

def ocr_image(image,width,height,language):
    if language not in LANGUAGES:raise PDFError('PDF_OCR_LANGUAGE_UNSUPPORTED')
    measured,exe=tool('tesseract');available=subprocess.run([str(exe),'--list-langs'],capture_output=True,text=True,timeout=5)
    langs=available.stdout.splitlines();missing=[v for v in language.split('+') if v not in langs]
    if missing:raise PDFError('PDF_OCR_LANGUAGE_UNAVAILABLE_'+missing[0].upper())
    match=re.search(r'in "([^"]+)"',available.stdout+available.stderr)
    if not match:raise PDFError('PDF_OCR_TRAINEDDATA_PROFILE_UNAVAILABLE')
    directory=Path(match[1]);models={}
    for name in language.split('+'):
        data=directory/(name+'.traineddata')
        if not data.is_file() or data.stat().st_size>64*1024*1024:raise PDFError('PDF_OCR_TRAINEDDATA_UNAVAILABLE')
        models[name]=records.sha(data)
    target=image.parent/'ocr'
    run=subprocess.run([str(exe),str(image),str(target),'-l',language,'--psm','3','tsv'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=25)
    output=target.with_suffix('.tsv')
    if run.returncode or not output.is_file() or output.stat().st_size>MAX_TEXT:raise PDFError('PDF_OCR_FAILED_OR_LIMIT')
    words=[];lines={}
    for row in csv.DictReader(io.StringIO(output.read_text(encoding='utf-8')),delimiter='\t'):
        if row.get('level')!='5' or not row.get('text','').strip():continue
        score=float(row['conf']);x,y,w,h=[int(row[k]) for k in ('left','top','width','height')]
        if not math.isfinite(score) or not 0<=score<=100 or w<=0 or h<=0:continue
        box=rect([x/width,y/height,w/width,h/height]);key=tuple(row[k] for k in ('block_num','par_num','line_num'))
        lines.setdefault(key,[]).append(len(words));words.append({'text':row['text'],'rect':box,'engine_confidence':round(score,3),'uncertain':score<85})
        if len(words)>MAX_WORDS:raise PDFError('PDF_OCR_WORD_LIMIT')
    unchanged(measured,exe)
    for name,old in models.items():
        if records.sha(directory/(name+'.traineddata'))!=old:raise PDFError('PDF_OCR_TRAINEDDATA_CHANGED')
    return {'text':'\n'.join(' '.join(words[i]['text'] for i in indices) for indices in lines.values()),'words':words,
        'language':language,'tool':{**measured,'traineddata_sha256':models},'uncertain_words':sum(v['uncertain'] for v in words),
        'all_text_unverified':True,'score_meaning':'ENGINE_SCORE_NOT_PROBABILITY_OF_CORRECTNESS','threshold':85,
        'status':'OCR_DERIVATIVE' if words else 'NO_TEXT_RECOGNIZED'}

def render_page(raw,index,ocr=False,language='eng'):
    info=inspect(raw)
    if type(index) is not int or not 0<=index<info['page_count']:raise PDFError('PDF_PHYSICAL_PAGE_OUT_OF_RANGE')
    measured,exe=tool('pdftoppm')
    with tempfile.TemporaryDirectory(prefix='ledger-pdf-page-') as temp:
        folder=Path(temp);source=folder/'source.pdf';source.write_bytes(raw)
        run=subprocess.run([str(exe),'-f',str(index+1),'-l',str(index+1),'-singlefile','-cropbox','-scale-to','2000','-png',str(source),str(folder/'page')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20)
        image=folder/'page.png'
        if run.returncode or not image.is_file() or image.stat().st_size>MAX_IMAGE:raise PDFError('PDF_RENDER_FAILED_OR_LIMIT')
        image_raw=image.read_bytes()
        if not image_raw.startswith(b'\x89PNG\r\n\x1a\n') or image_raw[12:16]!=b'IHDR':raise PDFError('PDF_RENDER_IMAGE_INVALID')
        width,height=struct.unpack('!II',image_raw[16:24])
        if not 0<width<=2000 or not 0<height<=2000:raise PDFError('PDF_RENDER_DIMENSION_LIMIT')
        native=word_layout(source,index,info['pages'][index]['rotation']);ocr_result=ocr_image(image,width,height,language) if ocr else None
    unchanged(measured,exe)
    return {'schema':VERSION,'source_sha256':info['source_sha256'],'page':info['pages'][index],'page_count':info['page_count'],
        'image_sha256':sha(image_raw),'image_width':width,'image_height':height,'image_b64':base64.b64encode(image_raw).decode(),
        'render_tool':measured,'native':native,'ocr':ocr_result,'image_is_derivative':True,
        'fact_verification':'NOT_IMPLIED_BY_READING','coordinate_basis':'NORMALIZED_TOP_LEFT_CROPPED_RENDER'}

def select_text(result,region,kind='native'):
    x,y,w,h=rect(region);words=(result.get(kind) or {}).get('words',[])
    return ' '.join(v['text'] for v in words if x<=v['rect'][0]+v['rect'][2]/2<=x+w and y<=v['rect'][1]+v['rect'][3]/2<=y+h)

def rule_hash():
    try:import pypdf;version=pypdf.__version__
    except ImportError:version='UNAVAILABLE'
    try:measured=tool('pdftotext')[0]
    except (PDFError,OSError,subprocess.SubprocessError):measured='UNAVAILABLE'
    return sha(Path(__file__).read_bytes()+records.canonical({'profile':VERSION,'pypdf':version,'native':measured}))

def bounded(action,path,expected_sha,page_index=0,ocr=False,language='eng'):
    context={'action':action,'path':str(Path(path).resolve()),'sha256':expected_sha,'page_index':page_index,'ocr':ocr,'language':language}
    root=Path(__file__).resolve().parents[3];env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','SYSTEMROOT')};env['PYTHONPATH']=str(root)
    try:
        run=subprocess.run([sys.executable,'-m','sdk.cli.arc1cli.pdf_evidence','--worker'],input=records.canonical(context),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd=root,env=env,timeout=15 if action=='inspect' else 55)
        if len(run.stdout)>12*1024*1024:raise PDFError('PDF_WORKER_RESPONSE_LIMIT')
        result=records.strict(run.stdout)
        if run.returncode:raise PDFError(result.get('error','PDF_READER_FAILED_OR_LIMIT'))
        return result
    except subprocess.TimeoutExpired:raise PDFError('PDF_READER_TIME_LIMIT') from None
    except (ValueError,UnicodeError) as exc:
        if isinstance(exc,PDFError):raise
        raise PDFError('PDF_READER_FAILED_OR_LIMIT') from None

def main():
    if sys.argv[1:]!=['--worker']:return 2
    import resource
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(1536*1024**2,1536*1024**2));resource.setrlimit(resource.RLIMIT_FSIZE,(intake_files.MAX_FILE,intake_files.MAX_FILE))
    try:
        c=records.strict(sys.stdin.buffer.read(16384));raw=intake_files.read_stable(Path(c['path']))
        if sha(raw)!=c['sha256']:raise PDFError('PDF_ORIGINAL_CHANGED')
        if c['action']=='inspect':result=inspect(raw)
        elif c['action']=='extract':result=extraction(raw)
        elif c['action']=='page':result=render_page(raw,c['page_index'],c['ocr'],c['language'])
        else:raise PDFError('PDF_ACTION_UNKNOWN')
        sys.stdout.buffer.write(records.canonical(result));return 0
    except Exception as exc:
        code=str(exc) if isinstance(exc,PDFError) and re.fullmatch(r'PDF_[A-Z0-9_]+',str(exc)) else 'PDF_READER_FAILED_OR_LIMIT'
        sys.stdout.buffer.write(records.canonical({'error':code}));return 2

if __name__=='__main__':raise SystemExit(main())
