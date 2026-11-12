"""Declared editable paragraph/table DOCX projection; originals are separate."""
import copy,io,json,uuid
from html.parser import HTMLParser
from . import office_tables as tab

SCHEMA='arc.office-document/1';W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def paragraph(value='',style='Normal'):
    return {'id':uuid.uuid4().hex,'kind':'paragraph','style':style,'text':value}
def table(rows,header=True):return {'id':uuid.uuid4().hex,'kind':'table','header':bool(header),'rows':rows}
def validate(doc):
    if not isinstance(doc,dict) or set(doc)!={'schema','title','blocks'} or doc['schema']!=SCHEMA:raise ValueError('OFFICE_DOCUMENT_SCHEMA')
    tab.text(doc['title'],240,False)
    if not isinstance(doc['blocks'],list) or len(doc['blocks'])>5000:raise ValueError('OFFICE_DOCUMENT_BLOCK_LIMIT')
    seen=set();cells=0
    for b in doc['blocks']:
        import re
        if not isinstance(b,dict) or not re.fullmatch('[a-f0-9]{32}',b.get('id','')) or b['id'] in seen:raise ValueError('OFFICE_DOCUMENT_BLOCK_ID')
        seen.add(b['id'])
        if b.get('kind')=='paragraph':
            if set(b)!={'id','kind','style','text'} or b['style'] not in ('Title','Heading1','Heading2','Heading3','Normal','Code'):raise ValueError('OFFICE_DOCUMENT_PARAGRAPH')
            tab.text(b['text'],32768)
        elif b.get('kind')=='table':
            if set(b)!={'id','kind','header','rows'} or type(b['header']) is not bool or not isinstance(b['rows'],list) or not b['rows'] or len(b['rows'])>2048:raise ValueError('OFFICE_DOCUMENT_TABLE')
            width=len(b['rows'][0])
            if not 1<=width<=16 or any(not isinstance(r,list) or len(r)!=width for r in b['rows']):raise ValueError('OFFICE_DOCUMENT_TABLE_WIDTH')
            cells+=sum(len(r) for r in b['rows'])
            for row in b['rows']:
                for value in row:tab.text(value,16384)
        else:raise ValueError('OFFICE_DOCUMENT_BLOCK_KIND')
    if cells>20000 or len(tab.canonical(doc).encode())>tab.MAX_MODEL:raise ValueError('OFFICE_DOCUMENT_SIZE')
    return doc
def document(title,blocks):return validate({'schema':SCHEMA,'title':title[:160] or 'Working document','blocks':blocks})
def visible(n):
    out=[]
    for x in n.iter():
        if x.tag=='{'+W+'}t':out.append(x.text or '')
        elif x.tag=='{'+W+'}tab':out.append('\t')
        elif x.tag in ('{'+W+'}br','{'+W+'}cr'):out.append('\n')
    return ''.join(out)
def parse(raw,name):
    losses=[];blocks=[];title=None
    with tab.archive(raw) as z:
        tab.package_losses(z,losses)
        root=tab.xml(z.read('word/document.xml'));body=root.find('{'+W+'}body')
        if body is None:raise ValueError('OFFICE_DOCX_BODY')
        for i,n in enumerate(body):
            loc='body/'+str(i)
            if n.tag=='{'+W+'}p':
                p=n.find('./{'+W+'}pPr/{'+W+'}pStyle');style=p.get('{'+W+'}val','Normal') if p is not None else 'Normal';style=style.replace(' ','')
                if style not in ('Title','Heading1','Heading2','Heading3','Normal','Code'):tab.loss(losses,loc,'PARAGRAPH_STYLE_NOT_PRESERVED');style='Normal'
                value=visible(n)
                if style=='Title' and title is None and not blocks:title=value
                else:blocks.append(paragraph(value,style))
                if any(x.tag.rsplit('}',1)[-1] in ('drawing','pict','fldChar','instrText','del','ins','hyperlink','footnoteReference','endnoteReference') for x in n.iter()):tab.loss(losses,loc,'VISIBLE_TEXT_ONLY_FIELDS_LINKS_REVISIONS_OR_OBJECTS_NOT_REEXPORTED')
            elif n.tag=='{'+W+'}tbl':
                rows=[]
                for row in n.findall('{'+W+'}tr'):
                    values=[]
                    for cell in row.findall('{'+W+'}tc'):
                        values.append('\n'.join(visible(p) for p in cell.findall('{'+W+'}p')))
                        if cell.find('{'+W+'}tbl') is not None or cell.find('.//{'+W+'}gridSpan') is not None or cell.find('.//{'+W+'}vMerge') is not None:tab.loss(losses,loc,'NESTED_OR_MERGED_TABLE_STRUCTURE_NOT_PRESERVED')
                    rows.append(values)
                if rows:
                    width=max(map(len,rows));rows=[r+['']*(width-len(r)) for r in rows];header=n.find('./{'+W+'}tr/{'+W+'}trPr/{'+W+'}tblHeader') is not None;blocks.append(table(rows,header))
            elif n.tag!='{'+W+'}sectPr':tab.loss(losses,loc,'UNSUPPORTED_BODY_ELEMENT_RETAINED_IN_ORIGINAL')
        for path in z.namelist():
            if path.startswith(('word/header','word/footer','word/footnotes','word/endnotes','word/comments','word/media/')):tab.loss(losses,path,'PART_RETAINED_ONLY_IN_ORIGINAL')
    tab.loss(losses,'document','PLAIN_EDITABLE_PARAGRAPH_TABLE_PROFILE_ORIGINAL_FORMATTING_AND_PAGINATION_NOT_ROUNDTRIPPED')
    return {'document':document(title or name.rsplit('.',1)[0],blocks),'losses':losses,'profile':'docx-paragraph-table-v1'}
def docx_bytes(doc,source=None):
    validate(doc)
    try:
        import docx
        from docx import Document
        from docx.shared import Inches,Pt,RGBColor
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
    except ImportError:raise ValueError('OFFICE_DOCX_DEPENDENCY_MISSING: install requirements-office.txt') from None
    output=io.BytesIO();d=Document()
    for border in list(d.styles.element.xpath('.//w:pBdr')):border.getparent().remove(border)
    for border in list(d.element.xpath('.//w:pBdr')):border.getparent().remove(border)
    section=d.sections[0];section.page_width=Inches(8.5);section.page_height=Inches(11)
    section.top_margin=section.bottom_margin=Inches(.7);section.left_margin=section.right_margin=Inches(.7)
    for name in ('Normal','Title','Heading 1','Heading 2','Heading 3'):
        style=d.styles[name];style.font.name='DejaVu Sans';style.font.color.rgb=RGBColor(0,0,0);style.font.size=Pt(11 if name=='Normal' else 20 if name=='Title' else 15 if name=='Heading 1' else 13)
        style.paragraph_format.space_after=Pt(7);style.paragraph_format.line_spacing=1.15
        fonts=style.element.get_or_add_rPr().find(qn('w:rFonts'))
        if fonts is not None:fonts.set(qn('w:eastAsia'),'Noto Sans CJK SC')
    d.add_paragraph(doc['title'],'Title')
    styles={'Heading1':'Heading 1','Heading2':'Heading 2','Heading3':'Heading 3','Normal':'Normal','Title':'Heading 1','Code':'Normal'}
    for b in doc['blocks']:
        if b['kind']=='paragraph':
            p=d.add_paragraph(b['text'],styles[b['style']])
            if b['style']=='Code':
                for run in p.runs:run.font.name='DejaVu Sans Mono';run.font.size=Pt(10)
            continue
        rows=b['rows'];width=len(rows[0]);t=d.add_table(rows=0,cols=width);t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
        weights=[max(4,min(45,max(len(r[i]) for r in rows[:100]))) for i in range(width)];total=sum(weights)
        for i,c in enumerate(t.columns):c.width=Inches(7.1*weights[i]/total)
        borders=OxmlElement('w:tblBorders')
        for side in ('top','left','bottom','right','insideH','insideV'):
            el=OxmlElement('w:'+side);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');borders.append(el)
        t._tbl.tblPr.append(borders)
        for ri,values in enumerate(rows):
            row=t.add_row()
            if ri==0 and b['header']:
                repeat=OxmlElement('w:tblHeader');row._tr.get_or_add_trPr().append(repeat)
            for ci,v in enumerate(values):
                c=row.cells[ci];c.width=Inches(7.1*weights[ci]/total);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER;c.text=v
                pr=c._tc.get_or_add_tcPr();margins=OxmlElement('w:tcMar')
                for side in ('top','left','bottom','right'):
                    n=OxmlElement('w:'+side);n.set(qn('w:w'),'90');n.set(qn('w:type'),'dxa');margins.append(n)
                pr.append(margins)
                if ri==0 and b['header'] or ri%2:
                    shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E5E7EB' if ri==0 else 'F7F8FA');pr.append(shade)
                for p in c.paragraphs:
                    p.paragraph_format.space_after=Pt(2);p.paragraph_format.line_spacing=1.1
                    for run in p.runs:run.font.size=Pt(10.5);run.bold=ri==0 and b['header']
        d.add_paragraph()
    if source:
        d.add_paragraph('Source and revision','Heading 1')
        for key,value in source.items():d.add_paragraph(str(key).replace('_',' ').capitalize()+': '+(tab.canonical(value) if isinstance(value,(dict,list)) else str(value)))
    d.core_properties.title=doc['title'];d.core_properties.author='';d.core_properties.last_modified_by='';d.save(output)
    return output.getvalue(),{'writer':'python-docx '+docx.__version__,'profile':'docx-paragraph-table-v1','pagination':'DEFINED_BY_ACTUAL_RENDERER','losses':[{'path':'document','reason':'PLAIN_EDITABLE_PROJECTION_ORIGINAL_EXTENDED_FORMATTING_NOT_RECREATED'}]}
class HTMLBlocks(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.blocks=[];self.parts=[];self.style='Normal';self.rows=None;self.row=None;self.cell=None;self.header=False
    def flush(self):
        value=''.join(self.parts);self.parts=[]
        if value.strip():self.blocks.append(paragraph(' '.join(value.split()) if self.style!='Code' else value,self.style))
        self.style='Normal'
    def handle_starttag(self,tag,attrs):
        if tag=='table':self.flush();self.rows=[];self.header=False
        elif tag=='tr' and self.rows is not None:self.row=[]
        elif tag in ('td','th') and self.row is not None:self.cell=[];self.header=self.header or tag=='th'
        elif self.rows is None and tag in ('h1','h2','h3','p','li','pre'):
            self.flush();self.style={'h1':'Heading1','h2':'Heading2','h3':'Heading3','pre':'Code'}.get(tag,'Normal')
            if tag=='li':self.parts.append('• ')
        elif tag=='br':self.handle_data('\n')
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:self.row.append(''.join(self.cell).strip());self.cell=None
        elif tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None
        elif tag=='table' and self.rows is not None:
            if self.rows:
                width=max(map(len,self.rows));self.blocks.append(table([r+['']*(width-len(r)) for r in self.rows],self.header))
            self.rows=None
        elif self.rows is None and tag in ('h1','h2','h3','p','li','pre'):self.flush()
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
        elif self.rows is None:self.parts.append(data)
def from_pages(title,pages):
    blocks=[]
    for page in pages:
        p=HTMLBlocks();p.feed(page['html']);p.flush();blocks.extend(p.blocks)
    return document(title,blocks)
def align(doc,base):
    doc=copy.deepcopy(doc);doc['title']=base['title'];return validate(doc)
def difference(a,b):
    validate(a);validate(b);rows=[]
    for i in range(max(len(a['blocks']),len(b['blocks']))):
        old=a['blocks'][i] if i<len(a['blocks']) else None;new=b['blocks'][i] if i<len(b['blocks']) else None
        x={k:v for k,v in (old or {}).items() if k!='id'};y={k:v for k,v in (new or {}).items() if k!='id'}
        if x!=y:rows.append({'position':i,'change':'BLOCK_CHANGED','before':old,'after':new})
    return rows
