#!/usr/bin/env python3
"""Build STRUTHIO · ARCADE, the Arcade-only demo edition.

    python3 tools/build_demo.py            -> dist/struthio-arcade-demo/ + dist/STRUTHIO_ARCADE_DEMO_<ver>.zip

The demo runs the same app.mjs as the console. Its index.html carries
<meta name="struthio-edition" content="ARCADE_DEMO">, which boots the built-in
engine ROM straight to an Arcade-only title (see DEMO in app.mjs). Everything
else (Campaign, VS, cartridges, Workshop, QR, TCS, manual, source viewer,
developer menu) is left out: those modules are replaced by the empty stubs in
demo/stubs/ and none of their files are copied.
"""
import hashlib, json, re, shutil, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'dist' / 'struthio-arcade-demo'

app = (ROOT / 'app.mjs').read_text()
BUILD = re.search(r"const BUILD_ID='STRUTHIO-CONSOLE-([^']+)'", app).group(1)
DEMO_BUILD = f'STRUTHIO-ARCADE-DEMO-{BUILD}'

KEEP_MODULES = ['episode-loader', 'sprite-profiles', 'modal', 'palette-bridge', 'viewport-shim']
STUB_MODULES = ['cartridge-installer', 'qr-cart', 'vs-ui', 'tcs-cal', 'net-panel']
COPY = [
    'app.mjs', '_headers',
    'console-assets/console-shell.css', 'console-assets/console-machine.css',
    'console-assets/console-moonrise.css', 'console-assets/console-controller.css',
    'console-assets/icon-192.png', 'console-assets/icon-512.png', 'console-assets/apple-touch-icon.png',
    'src/audio/worklet.mjs', 'src/audio/synth.mjs', 'src/audio/presentation.mjs',
]
COPY_DIRS = ['console-assets/arcade', 'episodes/dev-00']  # arcade art + the engine ROM (rules, fonts, save format)


def html_section(html, section_id):
    """Remove <section id="..."> ... </section> (sections are not nested in index.html)."""
    new, n = re.subn(r'<section id="%s"[\s\S]*?</section>\n' % re.escape(section_id), '', html)
    assert n == 1, section_id
    return new


def build_index():
    h = (ROOT / 'index.html').read_text()
    rep = lambda a, b: h.replace(a, b) if a in h else sys.exit(f'index.html: missing {a!r}')
    h = rep('<meta name="build" content="STRUTHIO-CONSOLE-%s">' % BUILD,
            f'<meta name="build" content="{DEMO_BUILD}">\n'
            '<meta name="struthio-edition" content="ARCADE_DEMO">\n'
            '<meta name="struthio-hero" content="demo-assets/hero-art.webp">')
    h = re.sub(r'<meta name="struthio-vs-relay"[^>]*>\n', '', h)
    h = re.sub(r'<meta name="description" content="[^"]*">',
               '<meta name="description" content="STRUTHIO arcade adventure: joust your way up a tower of floating islands to the moon. Free playable demo.">', h)
    h = re.sub(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="STRUTHIO · ARCADE">', h)
    h = re.sub(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="Climb the tower. Take the six rings. Take the gold ring at the moon.">', h)
    h = re.sub(r'<meta property="og:image" content="[^"]*">', '<meta property="og:image" content="./demo-assets/share-card.jpg">', h)
    h = re.sub(r'<meta property="og:image:alt" content="[^"]*">', '<meta property="og:image:alt" content="STRUTHIO box art: a knight on a war bird jousts a rival above floating crystal islands.">', h)
    h = re.sub(r'<title>[^<]*</title>', '<title>STRUTHIO · ARCADE</title>', h)
    h = rep('<link rel="stylesheet" href="./console-assets/console-controller.css">',
            '<link rel="stylesheet" href="./console-assets/console-controller.css">\n<link rel="stylesheet" href="./demo-assets/demo.css">')
    h = rep('<body class="is-booting">', '<body class="is-booting is-demo">')
    h = rep('aria-label="STRUTHIO Console is starting"', 'aria-label="STRUTHIO is starting"')
    h = rep('<span class="boot-kicker">STRUTHIO CONSOLE MACHINE</span>', '<span class="boot-kicker">STRUTHIO · ARCADE</span>')
    h = rep('<p data-boot-status>READING CARTRIDGE BAY</p>', '<p data-boot-status>LOADING</p>')
    h = rep('<small>SAME SKY · NEW WORLDS</small>', '<small>CLIMB TO THE MOON</small>')
    h = rep('<h1>STRUTHIO CONSOLE CANNOT START</h1>', '<h1>STRUTHIO CANNOT START</h1>')
    h = rep('<small>STRUTHIO CONSOLE plays in portrait. The game pauses meanwhile.</small>', '<small>STRUTHIO plays in portrait. The game pauses meanwhile.</small>')
    for sid in ('manual-screen', 'empty-console', 'cartridge-panel'):
        h = html_section(h, sid)
    h = re.sub(r'<form id="dev-code"[\s\S]*?</form>\n', '', h)
    h = re.sub(r'<div class="console-options"[\s\S]*?</div>\n', '', h)
    h = re.sub(r'<button id="home-button"[^>]*>[^<]*</button>\n', '', h)
    h = re.sub(r'<div id="title-machine-bar"[\s\S]*?</div>\n', '', h)
    h = re.sub(r'<p id="title-hint">[^<]*</p>\n', '', h)
    h = re.sub(r'<p id="title-credit">[\s\S]*?</p>\n', '', h)
    h = rep('<h2>CHOOSE A MODE</h2>', '<h2>ARCADE</h2>')
    h = h.replace('<b>STRUTHIO</b><span>CONSOLE</span>', '<b>STRUTHIO</b><span>ARCADE</span>')
    h = rep('alt="Active STRUTHIO cartridge title art."', 'alt="STRUTHIO box art."')
    h = rep('aria-live="polite">CARTRIDGE READY</p>', 'aria-live="polite"></p>')
    for word in ('CARTRIDGE', 'cartridge', 'Campaign', 'CAMPAIGN', 'CONSOLE'):
        if word in h.split('<script')[0]: print('\n'.join(l[:200] for l in h.split('\n') if word in l)); sys.exit(f'demo index still mentions {word}')
    return h


SW = r"""// STRUTHIO · ARCADE demo service worker: precache the demo, serve it offline.
const CACHE='struthio-arcade-demo-__BUILD__';
const CORE=__CORE__;
self.addEventListener('install',(event)=>event.waitUntil((async()=>{
const cache=await caches.open(CACHE);
try{for (const url of CORE){const r=await fetch(url,{cache:'reload'});if (!r.ok) throw new Error(`precache ${url} ${r.status}`);await cache.put(url,r);}}
catch (error){await caches.delete(CACHE);throw error;}
})()));
self.addEventListener('activate',(event)=>event.waitUntil((async()=>{
for (const name of await caches.keys()) if (name!==CACHE&&name.startsWith('struthio-arcade-demo-')) await caches.delete(name);
await self.clients.claim();
})()));
self.addEventListener('message',(event)=>{if (event.data?.type==='SKIP_WAITING') self.skipWaiting();});
self.addEventListener('fetch',(event)=>{
if (event.request.method!=='GET'||new URL(event.request.url).origin!==location.origin) return;
event.respondWith((async()=>{
const cache=await caches.open(CACHE);
if (event.request.mode==='navigate'){const hit=await cache.match('./index.html');if (hit) return hit;return fetch(event.request);}
const hit=await cache.match(event.request,{ignoreSearch:true});
if (hit){
const range=event.request.headers.get('range');
if (!range) return hit;
const body=await hit.arrayBuffer(),m=/bytes=(\d*)-(\d*)/.exec(range)||[];
const start=Number(m[1]||0),end=m[2]?Math.min(Number(m[2]),body.byteLength-1):body.byteLength-1;
return new Response(body.slice(start,end+1),{status:206,headers:{'content-type':hit.headers.get('content-type')||'application/octet-stream','content-range':`bytes ${start}-${end}/${body.byteLength}`,'accept-ranges':'bytes'}});
}
const response=await fetch(event.request);
if (response.ok&&response.status===200) cache.put(event.request,response.clone()).catch(()=>{});
return response;
})());
});
"""


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for f in COPY:
        (OUT / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f, OUT / f)
    for d in COPY_DIRS:
        shutil.copytree(ROOT / d, OUT / d)
    (OUT / 'console').mkdir()
    for m in KEEP_MODULES:
        shutil.copy2(ROOT / 'console' / f'{m}.mjs', OUT / 'console' / f'{m}.mjs')
    for m in STUB_MODULES:
        shutil.copy2(ROOT / 'demo' / 'stubs' / f'{m}.mjs', OUT / 'console' / f'{m}.mjs')
    (OUT / 'demo-assets').mkdir()
    for f in ('demo.css', 'assets/hero-art.webp', 'assets/share-card.jpg'):
        shutil.copy2(ROOT / 'demo' / f, OUT / 'demo-assets' / Path(f).name)
    (OUT / 'index.html').write_text(build_index())
    cfg = json.loads((ROOT / 'console.json').read_text())
    cfg['consoleBuildId'] = DEMO_BUILD
    cfg['activeEpisode'] = None
    (OUT / 'console.json').write_text(json.dumps(cfg, separators=(',', ':')))
    manifest = json.loads((ROOT / 'manifest.webmanifest').read_text())
    manifest.update({'id': './struthio-arcade', 'name': 'STRUTHIO · ARCADE', 'short_name': 'STRUTHIO',
                     'description': 'Joust your way up a tower of floating islands to the moon.'})
    (OUT / 'manifest.webmanifest').write_text(json.dumps(manifest, separators=(',', ':'), sort_keys=True))
    headers = (ROOT / '_headers').read_text()
    headers = re.sub(r'/factory/[^\n]*\n(?:  [^\n]*\n)*', '', headers)
    (OUT / '_headers').write_text(headers)
    files = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file())
    core = ['./'] + ['./' + f for f in files if f not in ('_headers',)]
    (OUT / 'sw.js').write_text(SW.replace('__BUILD__', BUILD).replace('__CORE__', json.dumps(core)))
    files = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file())
    sums = ''.join(f'{hashlib.sha256((OUT / f).read_bytes()).hexdigest()}  {f}\n' for f in files)
    (OUT / 'SHA256SUMS.txt').write_text(sums)
    zpath = ROOT / 'dist' / f'STRUTHIO_ARCADE_DEMO_{BUILD}.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in ['SHA256SUMS.txt'] + files:
            info = zipfile.ZipInfo(f, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED if f.endswith(('.webp', '.png', '.jpg', '.mp3', '.wav')) else zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, (OUT / f).read_bytes())
    total = sum((OUT / f).stat().st_size for f in files)
    print(f'{DEMO_BUILD}: {len(files) + 1} files, {total / 1e6:.2f} MB -> {zpath.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
