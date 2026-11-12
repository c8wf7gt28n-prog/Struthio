"""Optional document authoring helper; requires python-docx. Runtime does not call it."""
from pathlib import Path
import re
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/LEDGER_SLATE_COMPLETE_PROJECT_SPEC_01.md'
TARGET=ROOT/'docs/Ledger_Slate_Complete_Project_Specification_01.docx'
lines=SOURCE.read_text().splitlines();doc=Document();section=doc.sections[0]
section.page_width=Inches(8.5);section.page_height=Inches(11)
section.top_margin=Inches(.7);section.bottom_margin=Inches(.7);section.left_margin=Inches(.75);section.right_margin=Inches(.75)
section.header_distance=Inches(.28);section.footer_distance=Inches(.28);section.different_first_page_header_footer=True
styles=doc.styles
for name in ('Normal','Title','Subtitle','Heading 1','Heading 2','Heading 3','Caption'):
 style=styles[name];style.font.name='Arial';style.font.color.rgb=RGBColor(0,0,0)
 style._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Arial')
normal=styles['Normal'];normal.font.size=Pt(12);normal.paragraph_format.line_spacing=1.12;normal.paragraph_format.space_after=Pt(8)
normal.paragraph_format.widow_control=True
for name,size in [('Title',29),('Subtitle',15),('Heading 1',17),('Heading 2',13)]:
 styles[name].font.size=Pt(size)
 styles[name].paragraph_format.keep_with_next=True
 styles[name].paragraph_format.space_before=Pt(15 if name=='Heading 1' else 10)
 styles[name].paragraph_format.space_after=Pt(8)
styles['Title'].paragraph_format.space_before=Pt(18);styles['Title'].paragraph_format.space_after=Pt(10)
styles['Caption'].font.size=Pt(11);styles['Caption'].paragraph_format.space_after=Pt(10)
header=section.header.paragraphs[0];header.text='Ledger and Slate complete project specification';header.style=styles['Normal']
for run in header.runs:run.font.size=Pt(9)
footer=section.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
for text,field in [('Version 1.2   |   ',None),('', 'PAGE'),(' of ',None),('', 'NUMPAGES')]:
 run=footer.add_run(text);run.font.size=Pt(9)
 if field:
  f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),field);run._r.addnext(f)
doc.core_properties.title='Ledger and Slate Complete Project Specification'
doc.core_properties.subject='Complete product goals architecture interface installation and acceptance'
doc.core_properties.author='THE STRUTHIO CONCERN';doc.core_properties.keywords='Ledger Slate staC Debian Hatch specification'
doc.core_properties.comments='Product requirements and current implementation are distinguished throughout.'
doc.add_paragraph('Ledger and Slate\nComplete Project Specification','Title')
doc.add_paragraph('Product goals and requirements for the complete workshop','Subtitle')
doc.add_paragraph('Version 1.2\nNovember 5 2026\nUTC\nProduct owner Ryan Peddycoart\nTHE STRUTHIO CONCERN')
paras=[];buffer=[]
for line in lines[3:]:
 if line.startswith('## '):break
 if line.strip():buffer.append(line)
 elif buffer:paras.append(' '.join(buffer));buffer=[]
if buffer:paras.append(' '.join(buffer))
for text in paras:doc.add_paragraph(text)
doc.add_paragraph('Current checkpoint HATCH INTEGRATION 01\n690 registered operation schemas  112 job tool targets  41 connected settings')
doc.add_page_break();doc.add_paragraph('Contents','Heading 1')
headings=[line[3:] for line in lines if line.startswith('## ')]
for index,title in enumerate(headings):
 p=doc.add_paragraph();p.paragraph_format.space_after=Pt(2);p.paragraph_format.line_spacing=1.0
 link=OxmlElement('w:hyperlink');link.set(qn('w:anchor'),'section'+str(index))
 run=OxmlElement('w:r');rpr=OxmlElement('w:rPr');size=OxmlElement('w:sz');size.set(qn('w:val'),'21');rpr.append(size);run.append(rpr)
 text=OxmlElement('w:t');text.text=title;run.append(text);link.append(run);p._p.append(link)
doc.add_page_break()

def bookmark(p,name,index):
 a=OxmlElement('w:bookmarkStart');a.set(qn('w:id'),str(index));a.set(qn('w:name'),name)
 b=OxmlElement('w:bookmarkEnd');b.set(qn('w:id'),str(index));p._p.insert(0,a);p._p.append(b)

def hyperlink(p,label,url):
 link=OxmlElement('w:hyperlink');link.set(qn('r:id'),p.part.relate_to(url,RT.HYPERLINK,is_external=True))
 run=OxmlElement('w:r');text=OxmlElement('w:t');text.text=label;run.append(text);link.append(run);p._p.append(link)

labels={'https://www.debian.org/releases/trixie/amd64/install.en.html':'Debian trixie installation guide',
'https://www.debian.org/releases/trixie/amd64/ch06s04.en.html':'Debian guidance for loading missing firmware',
'https://packages.debian.org/trixie/xinit':'Debian xinit package and session startup',
'https://manpages.debian.org/trixie/fluxbox/fluxbox.1.en.html':'Fluxbox manual in Debian trixie'}

def table(block):
 rows=[[c.strip() for c in line.strip('|').split('|')] for line in block]
 rows=[r for r in rows if not all(re.fullmatch('[-: ]+',c) for c in r)]
 count=len(rows[0]);t=doc.add_table(rows=1,cols=count);t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
 widths=[1.5,3.05,2.45] if count==3 else [2.0,5.0]
 for i,w in enumerate(widths):t.columns[i].width=Inches(w)
 for ri,record in enumerate(rows):
  cells=t.rows[0].cells if ri==0 else t.add_row().cells
  for ci,(cell,value) in enumerate(zip(cells,record)):
   cell.width=Inches(widths[ci]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   tcPr=cell._tc.get_or_add_tcPr();margins=OxmlElement('w:tcMar')
   for edge in ('top','left','bottom','right'):
    x=OxmlElement('w:'+edge);x.set(qn('w:w'),'100');x.set(qn('w:type'),'dxa');margins.append(x)
   tcPr.append(margins);borders=OxmlElement('w:tcBorders')
   for edge in ('top','left','bottom','right'):
    x=OxmlElement('w:'+edge);x.set(qn('w:val'),'single');x.set(qn('w:sz'),'4');x.set(qn('w:color'),'D9D9D9');borders.append(x)
   tcPr.append(borders);shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'4D4D4D' if ri==0 else 'F4F4F4' if ri%2==0 else 'FFFFFF');tcPr.append(shade)
   p=cell.paragraphs[0];p.paragraph_format.space_after=Pt(2);p.paragraph_format.space_before=Pt(2);p.paragraph_format.line_spacing=1.08
   r=p.add_run(value);r.font.name='Arial';r.font.size=Pt(11);r.bold=ri==0;r.font.color.rgb=RGBColor(255,255,255) if ri==0 else RGBColor(0,0,0)
  if ri==0:
   repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
  cant=OxmlElement('w:cantSplit');t.rows[ri]._tr.get_or_add_trPr().append(cant)
 doc.add_paragraph().paragraph_format.space_after=Pt(2)

start=next(i for i,line in enumerate(lines) if line.startswith('## '));index=0;buf=[];i=start;appendix=False;figure_count=0
while i<len(lines):
 line=lines[i]
 if line.startswith('## '):
  if buf:doc.add_paragraph(' '.join(buf));buf=[]
  title=line[3:]
  if title.startswith('Appendix '):doc.add_page_break();appendix=True
  p=doc.add_paragraph(title,'Heading 1');bookmark(p,'section'+str(index),index);index+=1
 elif line.startswith('### '):
  if buf:doc.add_paragraph(' '.join(buf));buf=[]
  if appendix and figure_count:doc.add_page_break()
  doc.add_paragraph(line[4:],'Heading 2');figure_count+=1
 elif line.startswith('!['):
  if buf:doc.add_paragraph(' '.join(buf));buf=[]
  match=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',line);p=doc.add_paragraph();p.paragraph_format.keep_with_next=True
  picture=p.add_run().add_picture(str((SOURCE.parent/match[2]).resolve()),width=Inches(7.0))
  picture._inline.docPr.set('descr',match[1]);picture._inline.docPr.set('title',match[1])
  doc.add_paragraph(match[1],'Caption')
 elif line.startswith('|'):
  if buf:doc.add_paragraph(' '.join(buf));buf=[]
  block=[]
  while i<len(lines) and lines[i].startswith('|'):block.append(lines[i]);i+=1
  table(block);continue
 elif not line.strip():
  if buf:doc.add_paragraph(' '.join(buf));buf=[]
 elif line.startswith('https://'):
  if buf:doc.add_paragraph(' '.join(buf));buf=[]
  p=doc.add_paragraph();hyperlink(p,labels.get(line,line),line)
 else:buf.append(line)
 i+=1
if buf:doc.add_paragraph(' '.join(buf))
# Remove decorative rules inherited from the stock Word template.
for style in doc.styles:
 for border in list(style._element.xpath('.//w:pBdr')):border.getparent().remove(border)
for border in list(doc._element.xpath('.//w:pBdr')):border.getparent().remove(border)
settings=doc.settings._element
update=OxmlElement('w:updateFields');update.set(qn('w:val'),'true');settings.append(update)
doc.save(TARGET)
print(TARGET)
print('Words',len(SOURCE.read_text().split()),'sections',index,'figures',figure_count)
