import sys, os, re, zipfile, io
root = sys.argv[1]
pats = {
 'email': rb'[A-Za-z0-9._%+-]{2,}@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
 'home_path': rb'/(?:home|Users)/[A-Za-z0-9._-]+',
 'root_path': rb'/root/[A-Za-z0-9._/-]+',
 'workspace_path': rb'/workspace/[A-Za-z0-9._/-]+',
 'win_path': rb'[A-Z]:\\\\?Users\\\\?[A-Za-z0-9._-]+',
 'github_token': rb'gh[pousr]_[A-Za-z0-9]{30,}',
 'openai_key': rb'sk-[A-Za-z0-9_-]{20,}',
 'anthropic_key': rb'sk-ant-[A-Za-z0-9_-]{20,}',
 'aws_key': rb'AKIA[0-9A-Z]{16}',
 'private_key': rb'-----BEGIN [A-Z ]*PRIVATE KEY-----',
 'bearer': rb'[Bb]earer\s+[A-Za-z0-9._-]{20,}',
 'ipv4': rb'(?<![0-9.])(?:\d{1,3}\.){3}\d{1,3}(?![0-9.])',
 'hostname_kv': rb'"(?:hostname|host|node|user|username|login|machine)"\s*:\s*"[^"]{1,80}"',
 'url': rb'https?://[A-Za-z0-9._~:/?#\[\]@!$&\'()*+,;=%-]{4,}',
 'password_kv': rb'(?i)"(?:password|passwd|secret|api[_-]?key|token)"\s*:\s*"[^"]{1,200}"',
 'mac': rb'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}',
}
from collections import defaultdict
hits = defaultdict(lambda: defaultdict(set))
def scan(name, data):
    for k, p in pats.items():
        for m in re.finditer(p, data):
            v = m.group(0)
            hits[k][v[:120]].add(name)
for dp, dn, fn in os.walk(root):
    for n in fn:
        p = os.path.join(dp, n)
        rel = os.path.relpath(p, root)
        data = open(p, 'rb').read()
        scan(rel, data)
        if n.lower().endswith('.zip'):
            z = zipfile.ZipFile(io.BytesIO(data))
            for i in z.infolist():
                if not i.is_dir(): scan(rel + '!' + i.filename, z.read(i))
for k in pats:
    vals = hits.get(k, {})
    print(f'## {k}: {len(vals)} distinct')
    for v, files in sorted(vals.items(), key=lambda kv: -len(kv[1]))[:25]:
        if k in ('github_token','openai_key','anthropic_key','aws_key','private_key','bearer','password_kv'):
            shown = '<redacted len %d>' % len(v)
        else:
            shown = v.decode('utf-8', 'replace')
        print('   ', shown, '| files:', len(files), sorted(files)[:2])
