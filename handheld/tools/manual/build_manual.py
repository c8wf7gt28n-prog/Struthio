#!/usr/bin/env python3
# STRUTHIO HANDHELD · builds the handheld manual (.docx) for the C port.
#
# The page design (styles, theme, header, footer, numbering) and the
# industrial-design figures are taken from the v0.4 manual, so v0.6 reads as
# the same document; the text is in manual_content.py.
#   python3 tools/manual/build_manual.py <STRUTHIO_ESP32_HANDHELD_v0.4.docx> [out.docx]
import os
import re
import struct
import sys
import zipfile
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import manual_content as C  # noqa: E402

FONT, DISPLAY, MONO = 'Aptos', 'Aptos Display', 'Consolas'
INK, GREY, DARK, GOLD, CYAN = '17191C', '60656C', '2A2D31', 'E2A93F', '20C4D7'
PAGE_W_EMU = 6_550_000            # text width: 12240 - 2 * 893 twips


def rpr(font=FONT, bold=False, color=INK, size=19, italic=False):
    b = '<w:b/>' if bold else '<w:b w:val="0"/>'
    i = '<w:i/>' if italic else ''
    return f'<w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}"/>{b}{i}<w:color w:val="{color}"/><w:sz w:val="{size}"/></w:rPr>'


def runs(text, **kw):
    """Text with **bold** and `code` spans."""
    out = []
    for part in re.split(r'(\*\*[^*]+\*\*|`[^`]+`)', text):
        if not part:
            continue
        if part.startswith('**'):
            out.append(f'<w:r>{rpr(**{**kw, "bold": True})}<w:t xml:space="preserve">{escape(part[2:-2])}</w:t></w:r>')
        elif part.startswith('`'):
            k = {**kw, 'font': MONO, 'size': max(kw.get('size', 19) - 2, 14)}
            out.append(f'<w:r>{rpr(**k)}<w:t xml:space="preserve">{escape(part[1:-1])}</w:t></w:r>')
        else:
            out.append(f'<w:r>{rpr(**kw)}<w:t xml:space="preserve">{escape(part)}</w:t></w:r>')
    return ''.join(out)


class Doc:
    def __init__(self):
        self.x = []
        self.images = []          # (rid, path)
        self.pic = 0

    def raw(self, s):
        self.x.append(s)

    def gap(self):
        self.raw('<w:p><w:pPr><w:spacing w:after="0"/></w:pPr></w:p>')

    def page_break(self):
        self.raw('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def h1(self, t, new_page=False):
        pb = '<w:pageBreakBefore/>' if new_page else ''
        self.raw(f'<w:p><w:pPr><w:pStyle w:val="Heading1"/><w:keepNext/>{pb}<w:spacing w:before="200" w:after="80"/></w:pPr><w:r><w:t xml:space="preserve">{escape(t)}</w:t></w:r></w:p>')

    def h2(self, t):
        self.raw(f'<w:p><w:pPr><w:pStyle w:val="Heading2"/><w:keepNext/><w:spacing w:before="120" w:after="80"/></w:pPr><w:r><w:t xml:space="preserve">{escape(t)}</w:t></w:r></w:p>')

    def p(self, t, size=19, color=INK, italic=False, center=False):
        jc = '<w:jc w:val="center"/>' if center else ''
        self.raw(f'<w:p><w:pPr><w:spacing w:after="84" w:line="254" w:lineRule="auto"/>{jc}</w:pPr>{runs(t, size=size, color=color, italic=italic)}</w:p>')

    def label(self, t):
        self.raw(f'<w:p><w:pPr><w:spacing w:before="240" w:after="100"/></w:pPr>{runs(t, font=DISPLAY, bold=True, color=GREY, size=19)}</w:p>')

    def bullets(self, items):
        for t in items:
            self.raw(f'<w:p><w:pPr><w:pStyle w:val="ListBullet"/><w:spacing w:after="44" w:line="247" w:lineRule="auto"/><w:ind w:left="288" w:hanging="187"/></w:pPr>{runs(t, size=18)}</w:p>')

    def steps(self, items):
        for n, t in enumerate(items, 1):
            self.raw(f'<w:p><w:pPr><w:spacing w:after="60" w:line="254" w:lineRule="auto"/><w:ind w:left="360" w:hanging="360"/></w:pPr>{runs(f"{n}.  " + t, size=19)}</w:p>')

    def callout(self, title, text, fill='EAF4F4', bar=CYAN):
        body = ''.join(f'<w:p><w:pPr><w:spacing w:after="{40 if i < len(text) - 1 else 0}" w:line="250" w:lineRule="auto"/></w:pPr>{runs(t, size=18)}</w:p>'
                       for i, t in enumerate(text if isinstance(text, list) else [text]))
        self.raw('<w:tbl><w:tblPr><w:tblW w:type="auto" w:w="0"/><w:jc w:val="center"/><w:tblLayout w:type="fixed"/></w:tblPr>'
                 '<w:tblGrid><w:gridCol w:w="10080"/></w:tblGrid><w:tr><w:tc><w:tcPr><w:tcW w:type="dxa" w:w="10080"/>'
                 f'<w:tcBorders><w:left w:val="single" w:sz="22" w:color="{bar}"/></w:tcBorders>'
                 f'<w:shd w:fill="{fill}"/><w:tcMar><w:top w:w="140" w:type="dxa"/><w:start w:w="160" w:type="dxa"/><w:bottom w:w="140" w:type="dxa"/><w:end w:w="160" w:type="dxa"/></w:tcMar></w:tcPr>'
                 f'<w:p><w:pPr><w:spacing w:after="60"/></w:pPr>{runs(title, font=DISPLAY, bold=True, size=21)}</w:p>{body}</w:tc></w:tr></w:tbl>')
        self.gap()

    def gold(self, title, text):
        self.callout(title, text, fill='F0EFE7', bar=GOLD)

    def warn(self, title, text):
        self.callout(title, text, fill='FBEFEA', bar='D9643A')

    def code(self, lines):
        rs = []
        for i, line in enumerate(lines):
            br = '<w:br/>' if i < len(lines) - 1 else ''
            rs.append(f'<w:r>{rpr(font=MONO, color="E9E7DE", size=16)}<w:t xml:space="preserve">{escape(line)}</w:t>{br}</w:r>')
        self.raw('<w:tbl><w:tblPr><w:tblW w:type="auto" w:w="0"/><w:jc w:val="center"/><w:tblLayout w:type="fixed"/></w:tblPr>'
                 '<w:tblGrid><w:gridCol w:w="10080"/></w:tblGrid><w:tr><w:tc><w:tcPr><w:tcW w:type="dxa" w:w="10080"/><w:shd w:fill="202226"/>'
                 '<w:tcMar><w:top w:w="110" w:type="dxa"/><w:start w:w="130" w:type="dxa"/><w:bottom w:w="110" w:type="dxa"/><w:end w:w="130" w:type="dxa"/></w:tcMar></w:tcPr>'
                 f'<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>{"".join(rs)}</w:p></w:tc></w:tr></w:tbl>')
        self.gap()

    def table(self, head, rows, widths):
        total = sum(widths)
        ws = [round(10080 * w / total) for w in widths]
        mar = '<w:tcMar><w:top w:w="85" w:type="dxa"/><w:start w:w="90" w:type="dxa"/><w:bottom w:w="85" w:type="dxa"/><w:end w:w="90" w:type="dxa"/></w:tcMar>'

        def cell(t, w, header, shade):
            fill = f'<w:shd w:fill="{DARK}"/>' if header else (f'<w:shd w:fill="F4F4F1"/>' if shade else '')
            r = runs(t, bold=header, color='FFFFFF' if header else INK, size=17 if header else 16)
            return f'<w:tc><w:tcPr><w:tcW w:type="dxa" w:w="{w}"/>{fill}{mar}<w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr><w:spacing w:after="0"/></w:pPr>{r}</w:p></w:tc>'
        grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in ws)
        trs = ['<w:tr><w:trPr><w:tblHeader w:val="true"/></w:trPr>' + ''.join(cell(t, w, True, False) for t, w in zip(head, ws)) + '</w:tr>']
        for i, row in enumerate(rows):
            trs.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>' + ''.join(cell(t, w, False, i % 2) for t, w in zip(row, ws)) + '</w:tr>')
        self.raw('<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:type="auto" w:w="0"/><w:jc w:val="center"/><w:tblLayout w:type="fixed"/>'
                 '<w:tblLook w:firstColumn="1" w:firstRow="1" w:lastColumn="0" w:lastRow="0" w:noHBand="0" w:noVBand="1" w:val="04A0"/></w:tblPr>'
                 f'<w:tblGrid>{grid}</w:tblGrid>{"".join(trs)}</w:tbl>')
        self.gap()

    def figure(self, path, caption, width=1.0):
        with open(path, 'rb') as f:
            head = f.read(24)
        w, h = struct.unpack('>II', head[16:24])
        cx = int(PAGE_W_EMU * width)
        cy = int(cx * h / w)
        self.pic += 1
        rid = f'rIdImg{self.pic}'
        self.images.append((rid, path))
        self.raw('<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="60"/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
                 '<wp:inline xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
                 f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{100 + self.pic}" name="Figure {self.pic}"/>'
                 '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
                 '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
                 f'<pic:nvPicPr><pic:cNvPr id="0" name="{escape(os.path.basename(path))}"/><pic:cNvPicPr/></pic:nvPicPr>'
                 f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
                 f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"/></pic:spPr>'
                 '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
        self.raw(f'<w:p><w:pPr><w:spacing w:after="160"/><w:jc w:val="center"/></w:pPr>{runs(caption, bold=False, size=17, color=GREY)}</w:p>')

    def cover(self, title, subtitle, line, version_title, version_text):
        self.raw(f'<w:p><w:pPr><w:spacing w:before="1080" w:after="80"/></w:pPr>{runs(title, font=DISPLAY, bold=True, color=GOLD, size=68)}</w:p>')
        self.raw(f'<w:p><w:pPr><w:spacing w:after="160"/></w:pPr>{runs(subtitle, font=DISPLAY, bold=True, size=44)}</w:p>')
        self.raw(f'<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="14" w:space="3" w:color="{CYAN}"/></w:pBdr><w:spacing w:after="320"/></w:pPr>{runs(line, color=DARK, size=26)}</w:p>')
        self._version = (version_title, version_text)

    def cover_end(self):
        t, v = self._version
        self.raw(f'<w:p><w:pPr><w:spacing w:before="260" w:after="60"/><w:jc w:val="center"/></w:pPr>{runs(t, font=DISPLAY, bold=True, color=GREY, size=22)}</w:p>')
        self.raw(f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr>{runs(v, size=18, color=GREY)}</w:p>')
        self.page_break()


def build(template, out):
    import tempfile
    d = Doc()
    zin = zipfile.ZipFile(template)
    tmp = tempfile.mkdtemp(prefix='struthio_manual_')
    for n in zin.namelist():
        if n.startswith('word/media/'):
            with open(os.path.join(tmp, os.path.basename(n)), 'wb') as f:
                f.write(zin.read(n))
    C.write(d, ROOT, lambda name: os.path.join(tmp, name))
    names = zin.namelist()
    doc = zin.read('word/document.xml').decode('utf-8')
    head = doc[:doc.index('<w:body>')]
    sect = ('<w:sectPr><w:headerReference w:type="default" r:id="rIdHdr"/><w:footerReference w:type="default" r:id="rIdFtr"/>'
            '<w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="893" w:right="893" w:bottom="893" w:left="893" w:header="317" w:footer="346" w:gutter="0"/>'
            '<w:cols w:space="720"/><w:docGrid w:linePitch="360"/></w:sectPr>')
    body = '<w:body>' + ''.join(d.x) + sect + '</w:body></w:document>'
    # images: v0.4 figures by their media name, others from the repository
    rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    for rid, typ, tgt in [('rIdSty', 'styles', 'styles.xml'), ('rIdSet', 'settings', 'settings.xml'), ('rIdWeb', 'webSettings', 'webSettings.xml'),
                          ('rIdFnt', 'fontTable', 'fontTable.xml'), ('rIdThm', 'theme', 'theme/theme1.xml'), ('rIdNum', 'numbering', 'numbering.xml'),
                          ('rIdHdr', 'header', 'header1.xml'), ('rIdFtr', 'footer', 'footer1.xml')]:
        rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{typ}" Target="{tgt}"/>')
    media = {}
    for k, (rid, path) in enumerate(d.images, 1):
        name = f'media/fig{k}.png'
        media['word/' + name] = path
        rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{name}"/>')
    rels.append('</Relationships>')
    zout = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED)
    for n in names:
        if n.startswith('word/media/') or n in ('word/document.xml', 'word/_rels/document.xml.rels') or n.startswith('customXml') \
                or n == 'docProps/thumbnail.jpeg':
            continue
        data = zin.read(n)
        if n == 'word/footer1.xml':
            s = data.decode('utf-8').replace('Prototype Path v0.1', C.FOOTER_VERSION).replace('2026-09-28', C.DATE)
            data = s.encode('utf-8')
        elif n == 'word/header1.xml':
            data = data.decode('utf-8').replace('STRUTHIO  /  ESP32-S3 HANDHELD PROTOTYPE', C.HEADER).encode('utf-8')
        elif n == 'docProps/core.xml':
            s = data.decode('utf-8')
            s = re.sub(r'<dc:title>.*?</dc:title>', f'<dc:title>{escape(C.TITLE)}</dc:title>', s)
            s = re.sub(r'<dc:subject>.*?</dc:subject>', f'<dc:subject>{escape(C.SUBJECT)}</dc:subject>', s)
            s = re.sub(r'<dc:description>.*?</dc:description>', f'<dc:description>{escape(C.DESCRIPTION)}</dc:description>', s)
            s = re.sub(r'(<dcterms:(created|modified)[^>]*>).*?(</dcterms:)', rf'\g<1>{C.DATE}T00:00:00Z\g<3>', s)
            data = s.encode('utf-8')
        elif n == '[Content_Types].xml':
            s = data.decode('utf-8')
            s = re.sub(r'<Override PartName="/customXml[^>]*/>', '', s)
            s = s.replace('<Default Extension="jpeg" ContentType="image/jpeg"/>', '')
            data = s.encode('utf-8')
        elif n == '_rels/.rels':
            s = data.decode('utf-8')
            s = re.sub(r'<Relationship [^>]*thumbnail[^>]*/>', '', s)
            data = s.encode('utf-8')
        zout.writestr(n, data)
    zout.writestr('word/document.xml', head + body)
    zout.writestr('word/_rels/document.xml.rels', ''.join(rels))
    for name, path in media.items():
        zout.write(path, name)
    zout.close()
    print(f'{out}: {len(d.x)} blocks, {len(d.images)} figures')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('usage: build_manual.py STRUTHIO_ESP32_HANDHELD_v0.4.docx [out.docx]')
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'docs', C.FILENAME))
