import subprocess, hashlib, collections, re
root='/home/user/Struthio'; rev='37b78f0'
def git(*a): return subprocess.run(['git','-C',root,*a],capture_output=True).stdout
names=[n for n in git('ls-tree','-r','--name-only',rev).decode().split('\n') if n]
h={}
for n in names:
    h[hashlib.sha256(git('show',rev+':'+n)).hexdigest()]=n
# candidate text files to search for pins
text=[n for n in names if n.endswith(('.py','.json','.md','.txt','.sh','.mjs','.js')) and n not in ('MANIFEST.json','project/stacy_seed/current/manifest.json','project/stacy_seed/current/catalog.json')]
pins=collections.defaultdict(set)
hexre=re.compile(rb'[0-9a-f]{64}')
for n in text:
    raw=git('show',rev+':'+n)
    for m in set(hexre.findall(raw)):
        t=h.get(m.decode())
        if t: pins[n].add(t)
focus=('RIGHTS.md','README.md','RECORD_OF_DIRECTIONS.md','THIRD_PARTY_NOTICES.md','GETTING_STARTED.md','workbench/README.md','branding/stacy/character.json','branding/ux17/catalog.json','workbench/arc_desktop.py','workbench/stacy_foundation.py','workbench/editorial_art.py','workbench/qt_app.py','workbench/view_modules/__init__.py','docs/LEDGER_SLATE_COMPLETE_PROJECT_SPEC_01.md','docs/Ledger_Slate_Complete_Project_Specification_01.docx','docs/BOSS_IMPLEMENTATION_PLAN.md','docs/BOSS_IMPLEMENTATION_PLAN.json','workbench/algorithm_corpus.json','workbench/capability_catalog.py','workbench/tool_atlas.py','games/struthio/index.html','workbench/remote_pwa/manifest.webmanifest')
for n,ts in sorted(pins.items()):
    kinds=collections.Counter(t.rsplit('.',1)[-1] for t in ts)
    f=[t for t in ts if t in focus]
    print(n,'pins',len(ts),'tracked files',dict(kinds),'| focus:',f)
