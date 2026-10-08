#!/usr/bin/env python3
"""Build a small deployable copy of the viewer (PWA) from this package.

    python -B CHECKS/build_viewer_bundle.py <output folder>

Writes 7 files: index.html (CSS inlined), studio.js (all scripts and data), R23_REAR_BOARD.svg
(whitespace and number precision trimmed), sw.js, manifest.webmanifest, icon-192.png, icon-512.png.

Nothing in the package is changed. The CASE, ACRYLIC and R3 viewer meshes are packed as
little-endian Int16 coordinates at 0.01 mm (the meshes are tessellated at 0.25-0.45 mm, so the
packing is far below their own resolution) and Uint16 shades at 0.001 (the shades are written
with 3 decimals, some above 1, so they come back exactly), and expanded back
to the original {name, group, color, opacity, triangles:[{p, s}]} structure when the page loads,
so app.js and eye.js run unchanged. The full-precision meshes stay in the package.
"""
from pathlib import Path
import base64, json, re, struct, sys

ROOT = Path(__file__).resolve().parents[1]
SCALE = 100            # 0.01 mm per unit
SHADE = 1000           # shades have 3 decimals
CACHE = 'struthio-studio-r28-viewer-1.1'


def load_global(path, name):
    s = (ROOT / path).read_text()
    pre = f'window.{name}='
    assert s.startswith(pre), path
    return json.loads(s[len(pre):].rstrip().rstrip(';'))


def pack(data):
    out = dict(data)
    parts = []
    for p in data['parts']:
        q = dict(p)
        coords, shades = [], []
        for t in p['triangles']:
            for v in t['p']:
                for c in v:
                    i = round(c * SCALE)
                    assert -32768 <= i <= 32767, c
                    coords.append(i)
            j = round(t['s'] * SHADE)
            assert 0 <= j <= 65535, t['s']
            shades.append(j)
        q.pop('triangles')
        q['q'] = base64.b64encode(struct.pack(f'<{len(coords)}h', *coords)).decode()
        q['qs'] = base64.b64encode(struct.pack(f'<{len(shades)}H', *shades)).decode()
        parts.append(q)
    out['parts'] = parts
    return out


DECODER = """(function(){
var S=%d,H=%d;
function b(s){var r=atob(s),a=new Uint8Array(r.length);for(var i=0;i<r.length;i++)a[i]=r.charCodeAt(i);return a;}
function x(d){d.parts.forEach(function(p){var u=b(p.q),v=new Int16Array(u.buffer,0,u.length/2),w=b(p.qs),sh=new Uint16Array(w.buffer,0,w.length/2),t=[];
for(var i=0,k=0;i<v.length;i+=9,k++){t.push({p:[[v[i]/S,v[i+1]/S,v[i+2]/S],[v[i+3]/S,v[i+4]/S,v[i+5]/S],[v[i+6]/S,v[i+7]/S,v[i+8]/S]],s:sh[k]/H});}
p.triangles=t;delete p.q;delete p.qs;});return d;}
window.STRUTHIO_UNPACK=x;})();
""" % (SCALE, SHADE)


def minify_svg(text):
    text = re.sub(r'(\d+\.\d{3})\d+', r'\1', text)          # 0.001 mm is far below plot resolution
    text = re.sub(r'>\s+<', '><', text)
    text = re.sub(r'[ \t]*\n[ \t]*', '\n', text)
    return text


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1]).resolve()
    if out == ROOT or ROOT in out.parents:
        sys.exit('write the bundle outside the package folder')
    out.mkdir(parents=True, exist_ok=True)

    # studio.js: data first, then the app, in the same order index.html loads them.
    pieces = [DECODER, (ROOT / 'model-data.js').read_text().strip()]
    for path, name in (('case-r3-data.js', 'STRUTHIO_CASE_R3'), ('case-layer-data.js', 'STRUTHIO_CASE_LAYER'),
                       ('acrylic-layer-data.js', 'STRUTHIO_ACRYLIC_LAYER')):
        packed = json.dumps(pack(load_global(path, name)), separators=(',', ':'), ensure_ascii=False)
        pieces.append(f'window.{name}=window.STRUTHIO_UNPACK({packed});')
    pieces += [(ROOT / 'app.js').read_text().strip(), (ROOT / 'eye.js').read_text().strip()]
    (out / 'studio.js').write_text('\n;\n'.join(pieces) + '\n')

    html = (ROOT / 'index.html').read_text()
    css = (ROOT / 'styles.css').read_text() + '\n' + (ROOT / 'eye.css').read_text()
    html = html.replace('<link rel="stylesheet" href="styles.css">\n', '')
    html = html.replace('  <link rel="stylesheet" href="eye.css">\n', f'  <style>\n{css}\n  </style>\n')
    html = html.replace('<link rel="apple-touch-icon" href="icon-180.png">', '<link rel="apple-touch-icon" href="icon-192.png">')
    scripts = re.findall(r'<script src="[^"]+"></script>\n', html)
    assert len(scripts) == 6, scripts
    html = html.replace(''.join(scripts), '<script src="studio.js"></script>\n')
    assert 'styles.css' not in html and 'eye.css' not in html and 'model-data.js' not in html
    (out / 'index.html').write_text(html)

    (out / 'R23_REAR_BOARD.svg').write_text(minify_svg((ROOT / 'R23_REAR_BOARD.svg').read_text()))
    for f in ('icon-192.png', 'icon-512.png', 'manifest.webmanifest'):
        (out / f).write_bytes((ROOT / f).read_bytes())

    assets = ['./', './index.html', './studio.js', './R23_REAR_BOARD.svg', './manifest.webmanifest', './icon-192.png', './icon-512.png']
    (out / 'sw.js').write_text(
        "// Offline cache for the STRUTHIO R28 studio (deploy bundle built by CHECKS/build_viewer_bundle.py).\n"
        f"const CACHE='{CACHE}';\nconst ASSETS={json.dumps(assets)};\n"
        "self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));\n"
        "self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('struthio-studio-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));\n"
        "self.addEventListener('fetch',e=>{if(e.request.method!=='GET'||new URL(e.request.url).origin!==location.origin)return;e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).then(resp=>{if(resp.ok){const copy=resp.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));}return resp;}).catch(()=>e.request.mode==='navigate'?caches.match('./index.html'):Response.error())));});\n")

    files = sorted(p for p in out.iterdir() if p.is_file())
    total = sum(p.stat().st_size for p in files)
    for p in files:
        print(f'{p.stat().st_size:>10,}  {p.name}')
    print(f'{total:>10,}  total, {len(files)} files')


if __name__ == '__main__':
    main()
