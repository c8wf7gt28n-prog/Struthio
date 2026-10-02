#!/usr/bin/env python3
"""STRUTHIO · the small Markdown subset the guides use, to print-ready HTML.

    python3 mdhtml.py IN.md OUT.html [--image PATH[:caption]] ...

Headings, paragraphs, ordered and bulleted lists (nested by indentation, with continuation
paragraphs and code inside items), pipe tables, indented code blocks, **bold**, `code`,
[links](url) and bare https:// links. Images given with --image go under the title.
"""
import base64, html, os, re, sys

def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    t = re.sub(r'(?<!href=")(https://[^\s<)]+[^\s<).,])', r'<a href="\1">\1</a>', t)
    return t

LIST = re.compile(r'^(\d+\.|-)\s+(.*)$')

def indent(line):
    return len(line) - len(line.lstrip(' '))

def parse(lines):
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]
        if not ln.strip(): i += 1; continue
        if indent(ln) >= 4:                                         # code block
            block = []
            while i < n and (not lines[i].strip() or indent(lines[i]) >= 4):
                block.append(lines[i][4:] if lines[i].strip() else ''); i += 1
            while block and not block[-1]: block.pop()
            out.append('<pre>' + html.escape('\n'.join(block)) + '</pre>'); continue
        m = re.match(r'^(#{1,4})\s+(.*)$', ln)
        if m:
            k = len(m.group(1)); out.append(f'<h{k}>{inline(m.group(2))}</h{k}>'); i += 1; continue
        if ln.startswith('|'):
            rows = []
            while i < n and lines[i].startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-{3,}:?', c) for c in cells if c): rows.append(cells)
                i += 1
            head, body = rows[0], rows[1:]
            t = '<table><thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr></thead><tbody>'
            t += ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>' for r in body)
            out.append(t + '</tbody></table>'); continue
        m = LIST.match(ln)
        if m:
            ordered = m.group(1) != '-'; items = []
            while i < n:
                m = LIST.match(lines[i])
                if not m or (m.group(1) != '-') != ordered: break
                ci = len(m.group(1)) + 1 + (len(lines[i]) - len(lines[i].lstrip()) )
                body = [m.group(2)]; i += 1
                while i < n and (not lines[i].strip() or indent(lines[i]) >= 2):
                    if not lines[i].strip() and (i + 1 >= n or (lines[i + 1].strip() and indent(lines[i + 1]) < 2)): break
                    body.append(lines[i][ci:] if indent(lines[i]) >= ci else lines[i].lstrip()); i += 1
                items.append(body)
                while i < n and not lines[i].strip() and i + 1 < n and LIST.match(lines[i + 1]) and (LIST.match(lines[i + 1]).group(1) != '-') == ordered: i += 1
            tag = 'ol' if ordered else 'ul'
            lis = []
            for body in items:
                first, rest = body[0], body[1:]
                # continuation lines of the first paragraph join it; the rest is parsed as blocks
                j = 0
                while j < len(rest) and rest[j].strip() and indent(rest[j]) < 4 and not LIST.match(rest[j]) and not rest[j].startswith('|'):
                    first += ' ' + rest[j].strip(); j += 1
                lis.append('<li>' + inline(first) + parse(rest[j:]) + '</li>')
            out.append(f'<{tag}>' + ''.join(lis) + f'</{tag}>'); continue
        para = []
        while i < n and lines[i].strip() and indent(lines[i]) < 4 and not LIST.match(lines[i]) and not lines[i].startswith(('|', '#')):
            para.append(lines[i].strip()); i += 1
        out.append('<p>' + inline(' '.join(para)) + '</p>')
    return '\n'.join(out)

CSS = """
@page { size: A4; margin: 16mm 15mm 18mm 15mm; }
body { font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 10pt; line-height: 1.42; color: #16202b; }
h1 { font-size: 22pt; color: #0d2a4a; border-bottom: 3px solid #f29a1d; padding-bottom: 4px; margin: 0 0 10px; }
h2 { font-size: 14pt; color: #0d2a4a; margin: 20px 0 6px; border-bottom: 1px solid #c9d3de; padding-bottom: 2px; page-break-after: avoid; }
h3 { font-size: 11.5pt; color: #0d2a4a; margin: 14px 0 4px; page-break-after: avoid; }
p { margin: 5px 0; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 10px; font-size: 9pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th { background: #0d2a4a; color: #fff; text-align: left; padding: 4px 6px; }
td { border-bottom: 1px solid #d7dee6; padding: 4px 6px; vertical-align: top; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.8pt; background: #eef2f6; padding: 0 3px; border-radius: 3px; }
pre { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.6pt; background: #0f1a26; color: #e8eef5; padding: 7px 9px;
      border-radius: 5px; white-space: pre-wrap; page-break-inside: avoid; }
ol, ul { margin: 4px 0 6px; padding-left: 22px; }
li { margin: 3px 0; }
a { color: #1c5fa8; text-decoration: none; }
.figs { display: flex; gap: 10px; justify-content: center; margin: 8px 0 14px; }
.figs figure { margin: 0; text-align: center; font-size: 8.5pt; color: #4a5866; }
.figs img { max-height: 92mm; max-width: 88mm; border-radius: 6px; }
.foot { margin-top: 18px; font-size: 8pt; color: #6b7783; border-top: 1px solid #d7dee6; padding-top: 4px; }
"""

def main():
    args = sys.argv[1:]
    src, dst = args[0], args[1]
    imgs = [args[k + 1] for k in range(len(args)) if args[k] == '--image']
    foot = next((args[k + 1] for k in range(len(args)) if args[k] == '--foot'), '')
    md = open(src, encoding='utf-8').read().split('\n')
    body = parse(md)
    if imgs:
        figs = []
        for spec in imgs:
            path, _, cap = spec.partition(':')
            data = base64.b64encode(open(path, 'rb').read()).decode()
            figs.append(f'<figure><img src="data:image/png;base64,{data}"><figcaption>{html.escape(cap)}</figcaption></figure>')
        body = body.replace('</h1>', '</h1><div class="figs">' + ''.join(figs) + '</div>', 1)
    title = re.sub(r'<[^>]+>', '', re.search(r'<h1>(.*?)</h1>', body).group(1)) if '<h1>' in body else 'STRUTHIO'
    foot_html = f'<div class="foot">{html.escape(foot)}</div>' if foot else ''
    open(dst, 'w', encoding='utf-8').write(f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>'
                                           f'<style>{CSS}</style></head><body>{body}{foot_html}</body></html>')

if __name__ == '__main__':
    main()
