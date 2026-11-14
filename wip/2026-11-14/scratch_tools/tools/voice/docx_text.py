import sys, zipfile, re
from xml.etree import ElementTree as ET
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
for p in sys.argv[1:]:
    print('#### FILE', p)
    with zipfile.ZipFile(p) as z:
        data = z.read('word/document.xml')
    root = ET.fromstring(data)
    body = root.find(W + 'body')
    def para_text(par):
        out = []
        for node in par.iter():
            if node.tag == W + 't':
                out.append(node.text or '')
            elif node.tag == W + 'tab':
                out.append('\t')
            elif node.tag == W + 'br':
                out.append('\n')
        return ''.join(out)
    for par in body.iter(W + 'p'):
        t = para_text(par)
        style = ''
        ppr = par.find(W + 'pPr')
        if ppr is not None:
            ps = ppr.find(W + 'pStyle')
            if ps is not None:
                style = ps.get(W + 'val') or ''
        if t.strip():
            print(('[' + style + '] ' if style else '') + t)
