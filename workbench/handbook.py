"""Current Orange Book content, source binding and document export.

The reader and exported documents consume the same chapters and live register.
Generated files and local paths stay in build/, outside release payloads.
"""
from contextlib import contextmanager
import html
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import tempfile
import time
import uuid
from . import record_io as io

CONTRACT = 'arc-ledger.orange-book/1'
SOURCE = 'docs/orange_book/chapters.json'
FIELDS = {
    'book.status': ({}, []),
    'book.contents': ({}, []),
    'book.read': ({'page': {'type':'string','maxLength':100}}, ['page']),
}
CSS = """body{font-family:'DejaVu Sans',Arial,sans-serif;font-size:15px;line-height:1.55;color:#e5e8eb;background:#171b20;margin:24px}h1{font-size:25px;color:#ff9a54}h2{font-size:20px}p{margin:12px 0}table{border-collapse:collapse;width:100%;margin:14px 0}td,th{border:1px solid #56606c;padding:8px;text-align:left}a{color:#ffc08f}.note{color:#b9c2cb}code{font-family:monospace}li{margin:7px 0}.page{page-break-after:always}"""


def input_state(root):
    from .engineering_register import snapshot
    data = snapshot(root)
    sources = dict(data['input_manifest'])
    sources.update(io.manifest(root,[SOURCE,'workbench/handbook.py','sdk/cli/arc1cli/office_documents.py','sdk/cli/arc1cli/office_tables.py','workbench/office_runtime.py','branding/fonts/NotoSansCJKsc-Regular.otf']))
    return data, sources


def fingerprint(root):
    data, sources = input_state(root)
    return io.digest({'register':data['snapshot_id'],'source':sources})


def watch_signature(root):
    from .engineering_register import binding_paths
    paths = set(binding_paths(root)) | {SOURCE,'workbench/handbook.py','build/register/power_analysis.json'}
    rows = []
    for name in sorted(paths):
        path = io.project_path(root,name,False)
        st = path.stat() if path.is_file() else None
        rows.append((name,st.st_mtime_ns if st else None,st.st_size if st else None))
    return io.digest(rows)


def table(headers, rows):
    def cell(value): return html.escape(str(value))
    return ('<table><tr>'+''.join('<th>'+cell(v)+'</th>' for v in headers)+'</tr>'+
        ''.join('<tr>'+''.join('<td>'+cell(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</table>')


def ensure(root):
    root = Path(root).resolve()
    data, sources = input_state(root)
    stamp = io.digest({'register':data['snapshot_id'],'source':sources})
    folder = io.project_path(root,'build/orange_book/current/manifest.json',False).parent
    target = folder/'manifest.json'
    if target.is_file():
        old = io.strict_json(target.read_bytes())
        if old.get('input_fingerprint') == stamp and old.get('root_binding') == str(root) and all(
                io.project_path(root,n,False).is_file() and io.sha(root/n) == digest
                for n,digest in old.get('generated_hashes',{}).items()) and old.get('generated_hashes'):
            return old
    chapters = io.load(root,SOURCE)
    if chapters.get('schema') != 'arc-ledger.handbook-chapters/1':
        raise ValueError('BOOK_CHAPTER_SCHEMA')
    pages = chapters['pages']
    ids = [p['id'] for p in pages]
    if not pages or len(pages)>100 or len(set(ids))!=len(ids) or any(
            not re.fullmatch(r'[a-z0-9-]{1,100}',i) for i in ids):
        raise ValueError('BOOK_CHAPTER_ID')
    live = {'id':'engineering-status','title':'Current engineering status','html':
        '<h1>Current engineering status</h1><p>Source-linked results from this project. A completed computation, a passing outcome and independent acceptance are separate facts.</p>'+
        table(['Check','Outcome','Currency','Target'],[[r['check_plan_id'],r.get('outcome') or 'Not run',r['currency'],r['target_status']] for r in data['evidence']])+
        '<p>Fabrication and physical programming remain on hold. Missing inputs remain missing; this book does not infer approval from them.</p>'}
    pages = pages+[live]
    generation = folder/'generations'/stamp
    generation.mkdir(parents=True,exist_ok=True)
    document = '<!doctype html><html lang="en"><meta charset="utf-8"><title>The Orange Book</title><style>'+CSS+'</style><body>'
    document += '<h1>The Orange Book</h1><p>ARC-1 · The Silicon Federation workshop</p><nav>'
    document += '<br>'.join('<a href="#'+p['id']+'">'+html.escape(p['title'])+'</a>' for p in pages)+'</nav>'
    document += ''.join('<section class="page" id="'+p['id']+'">'+p['html']+'</section>' for p in pages)+'</body></html>'
    io.write_json(generation/'pages.json',pages)
    io.atomic(generation/'Orange_Book.html',document)
    if fingerprint(root) != stamp:
        raise ValueError('BOOK_SOURCE_DRIFT_DURING_REFRESH')
    result = {'schema':CONTRACT,'input_fingerprint':stamp,'snapshot_id':data['snapshot_id'],
        'source_catalog_revision':data['source_catalog_revision'],'root_binding':str(root),
        'updated_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'pages_file':(generation/'pages.json').relative_to(root).as_posix(),
        'html':(generation/'Orange_Book.html').relative_to(root).as_posix(),
        'retained_pages':0,'live_sections':len(pages),'editorial_review':'CURRENT_WORKSHOP_GUIDE',
        'chapter_review':{'state':'SOURCE_BOUND','changed':[]},'fabrication':'HOLD'}
    result['generated_hashes']={p.relative_to(root).as_posix():io.sha(p) for p in generation.iterdir() if p.is_file()}
    io.write_json(target,result)
    return result


def exports_intact(root, exported):
    files = exported.get('files',[])
    try:
        return bool(files) and any(r['path'].endswith('.docx') for r in files) and all(
            io.sha(io.project_path(root,r['path']))==r['sha256'] for r in files)
    except (OSError,ValueError,KeyError):
        return False


def dispatch(kernel, operation, args):
    status = ensure(kernel.root)
    if operation == 'book.status':
        target = kernel.root/'build/orange_book/exports/manifest.json'
        exports = io.strict_json(target.read_bytes()) if target.is_file() else None
        current = bool(exports and exports.get('input_fingerprint')==status['input_fingerprint'] and exports_intact(kernel.root,exports))
        return dict(status,exports=exports,exports_current=current,docx_current=current,
                    pdf_current=bool(current and exports.get('pdf_state')=='GENERATED'))
    pages = io.strict_json(io.project_path(kernel.root,status['pages_file']).read_bytes())
    if operation == 'book.contents':
        return {'input_fingerprint':status['input_fingerprint'],'pages':[{'id':p['id'],'title':p['title']} for p in pages]}
    page = next((p for p in pages if p['id']==args['page']),None)
    if page is None:
        raise ValueError('UNKNOWN_BOOK_PAGE')
    return {'input_fingerprint':status['input_fingerprint'],'page':page,'css':CSS,'review':status['chapter_review']}


def request_refresh(root):
    io.write_json(io.project_path(root,'build/orange_book/refresh_requested.json',False),
                  {'requested':time.time(),'reason':'engineering source or evidence changed'})


class WordContent(HTMLParser):
    """Convert the handbook's small HTML vocabulary into plain Word paragraphs."""
    def __init__(self):
        super().__init__(); self.rows=[]; self.parts=[]; self.style=None
    def flush(self):
        text=' '.join(''.join(self.parts).split())
        if text:self.rows.append((self.style,text))
        self.parts=[]; self.style=None
    def handle_starttag(self,tag,attrs):
        if tag in ('h1','h2','h3','p','li','tr'):
            self.flush(); self.style={'h1':'Heading1','h2':'Heading2','h3':'Heading3'}.get(tag)
            if tag=='li':self.parts.append('• ')
        elif tag in ('td','th') and self.parts:self.parts.append(' | ')
        elif tag=='br':self.parts.append(' ')
    def handle_endtag(self,tag):
        if tag in ('h1','h2','h3','p','li','tr'):self.flush()
    def handle_data(self,data):self.parts.append(data)


def write_docx(path,pages):
    from sdk.cli.arc1cli import office_documents as editable
    raw,profile=editable.docx_bytes(editable.from_pages('The Orange Book',pages))
    Path(path).write_bytes(raw)
    return profile


@contextmanager
def export_lock(root):
    from .execution_lock import ExecutionLock
    lock=ExecutionLock(Path(root)/'build/orange_book/exports')
    if not lock.acquire():raise ValueError('BOOK_EXPORT_ALREADY_RUNNING')
    try:yield
    finally:lock.release()


def export_book(root,render_pdf=True):
    root=Path(root).resolve(); status=ensure(root); stamp=status['input_fingerprint']
    pages=io.strict_json((root/status['pages_file']).read_bytes())
    parent=root/'build/orange_book/exports'; parent.mkdir(parents=True,exist_ok=True)
    with export_lock(root),tempfile.TemporaryDirectory(prefix='book-stage-',dir=parent) as tmp:
        stage=Path(tmp); docx=stage/'ARC_Orange_Book.docx';writer_profile=write_docx(docx,pages)
        from . import office_runtime
        renderer=office_runtime.probe() if render_pdf else {'available':False}
        render_profile=None
        pdf_state='NOT_AVAILABLE' if render_pdf else 'NOT_REQUESTED'
        if render_pdf and renderer['available']:
            converted,render_profile=office_runtime.convert(docx,stage/'converted','pdf')
            shutil.copyfile(converted,stage/'ARC_Orange_Book.pdf')
            pdf_state='GENERATED'
        if fingerprint(root)!=stamp:raise ValueError('BOOK_SOURCE_DRIFT_DURING_EXPORT')
        generation=parent/(stamp+'-'+uuid.uuid4().hex[:12]);generation.mkdir()
        for path in stage.iterdir():
            if path.suffix in ('.docx','.pdf'):io.atomic(generation/path.name,path.read_bytes())
        files=[{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':io.sha(p)} for p in sorted(generation.iterdir())]
        exported={'schema':CONTRACT,'input_fingerprint':stamp,'snapshot_id':status['snapshot_id'],
            'files':files,'pdf_state':pdf_state,'docx_profile':writer_profile,'renderer_profile':render_profile,'review_state':'GENERATED_REQUIRES_EDITORIAL_REVIEW','fabrication':'HOLD'}
        io.write_json(parent/'manifest.json',exported)
        return exported
