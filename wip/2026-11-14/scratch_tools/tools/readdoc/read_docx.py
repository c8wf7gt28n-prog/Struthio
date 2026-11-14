import sys, zipfile, re
from xml.etree import ElementTree as ET
path = sys.argv[1]
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
with zipfile.ZipFile(path) as z:
    names = z.namelist()
    print('parts:', [n for n in names if not n.startswith('word/theme')][:30])
    media = [n for n in names if n.startswith('word/media/')]
    print('media:', [(n, z.getinfo(n).file_size) for n in media])
    root = ET.fromstring(z.read('word/document.xml'))
    body = root.find(W + 'body')
    def text_of(el):
        out = []
        for node in el.iter():
            if node.tag == W + 't': out.append(node.text or '')
            elif node.tag in (W + 'tab',): out.append('\t')
            elif node.tag in (W + 'br', W + 'cr'): out.append('\n')
        return ''.join(out)
    n = 0
    for child in body:
        if child.tag == W + 'p':
            style = child.find(W + 'pPr/' + W + 'pStyle')
            t = text_of(child)
            if t.strip() or True:
                n += 1; print(('[%s] ' % style.get(W + 'val') if style is not None else '') + t)
        elif child.tag == W + 'tbl':
            for row in child.iter(W + 'tr'):
                print(' | '.join(text_of(c).strip() for c in row.findall(W + 'tc')))
    print('--- paragraphs:', n)
