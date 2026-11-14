"""Extract path-like references from top-level *.md and docs/*.md; compare with MANIFEST.json files keys."""
import json, os, re, sys, collections, posixpath

root = os.path.abspath(sys.argv[1])
missing_list = sys.argv[2]
out_json = sys.argv[3]
man = json.load(open(os.path.join(root, 'MANIFEST.json'), encoding='utf-8'))
files = set(man['files'].keys())
files.add('MANIFEST.json')
dirs = set()
for f in files:
    parts = f.split('/')
    for i in range(1, len(parts)):
        dirs.add('/'.join(parts[:i]))
basenames = collections.defaultdict(list)
for f in files:
    basenames[f.rsplit('/', 1)[-1]].append(f)
in_missing_parts = set()
for line in open(missing_list, encoding='utf-8'):
    m = re.match(r'\s*\d+\s+[0-9a-f]{64}\s+(.*)$', line.rstrip('\n'))
    if m: in_missing_parts.add(m.group(1))

docs = []
for f in sorted(os.listdir(root)):
    if f.endswith('.md'): docs.append(f)
for f in sorted(os.listdir(os.path.join(root, 'docs'))):
    if f.endswith('.md'): docs.append('docs/' + f)

TOPS = sorted({f.split('/')[0] for f in files if '/' in f})
EXT = r'(?:md|json|py|sh|cmd|pdf|docx|txt|png|jpg|jpeg|webp|svg|otf|ttf|gz|zip|sqlite3|mjs|js|html|css|csv|xlsx|ods|odt|gguf|mp3|wav|java|jar|toml|yaml|yml|ini|cfg|log|patch|whl|deb|ron|vcd|kicad_pcb|kicad_sch|step|stl|dxf|c|h|v|sv|vhd|lock|service|desktop|xml|qss)'
tok = re.compile(r'(?<![\w/.\-~$:@])((?:(?:' + '|'.join(map(re.escape, TOPS)) + r')/[\w.\-/+%&]*[\w/])|(?:[\w.\-]+/)*[\w.\-]+\.' + EXT + r')(?![\w/\-])')
mdlink = re.compile(r'\]\(([^)\s]+)\)')
code = re.compile(r'`([^`\n]+)`')

def classify(ref, docdir):
    r = ref.strip().rstrip('.,;:')
    if r.startswith('./'): r = r[2:]
    cands = [r]
    if docdir:
        cands.append(posixpath.normpath(posixpath.join(docdir, r)))
    for c in cands:
        c2 = c.rstrip('/')
        if c2 in files: return ('file', c2)
        if c2 in dirs: return ('dir', c2)
    # trailing fragments like path:line or anchors
    for c in cands:
        c2 = re.sub(r'[#:].*$', '', c).rstrip('/')
        if c2 in files: return ('file', c2)
        if c2 in dirs: return ('dir', c2)
    b = r.rsplit('/', 1)[-1]
    if '/' not in r and b in basenames:
        return ('basename', basenames[b][0])
    return ('absent', r)

absent = collections.defaultdict(lambda: collections.defaultdict(list))  # ref -> doc -> lines
inmissing = collections.defaultdict(lambda: collections.defaultdict(list))
counts = collections.Counter()
for d in docs:
    docdir = posixpath.dirname(d)
    text = open(os.path.join(root, d), encoding='utf-8', errors='replace').read().split('\n')
    for ln, line in enumerate(text, 1):
        found = set()
        for m in mdlink.finditer(line):
            t = m.group(1)
            if re.match(r'[a-z]+://|mailto:|#', t): continue
            found.add(('link', t.split('#')[0]))
        stripped = re.sub(r'https?://\S+', ' ', line)
        for m in tok.finditer(stripped):
            found.add(('tok', m.group(1)))
        for m in code.finditer(line):
            t = m.group(1).strip()
            if ' ' in t and re.fullmatch(r'[\w.\-/+%&() ]+\.' + EXT, t) and '/' in t:
                found.add(('code', t))
        for kind, t in found:
            t = t.strip()
            if not t or any(ch in t for ch in '<>*{}$') or 'NN' in t or t.startswith(('~', '/', 'http')):
                continue
            if re.search(r'/path/to|\bN\.|_0N', t): continue
            k, v = classify(t, docdir)
            counts[k] += 1
            if k == 'file' and v in in_missing_parts:
                inmissing[v][d].append(ln)
            if k == 'absent':
                absent[v][d].append(ln)

print('docs scanned:', len(docs))
print('reference classification counts:', dict(counts))
print('distinct refs to files in missing parts:', len(inmissing))
for k in sorted(inmissing):
    print('  IN-MISSING-PART', k, {d: l[:3] for d, l in inmissing[k].items()})
print('distinct absent refs:', len(absent))
json.dump({k: {d: l for d, l in v.items()} for k, v in absent.items()}, open(out_json, 'w'), indent=1)
by_top = collections.Counter()
for k in absent:
    by_top[k.split('/')[0] if '/' in k else '(bare)'] += 1
print('absent by first segment:', by_top.most_common(40))
