import subprocess, re, collections
root='/home/user/Struthio'
names=subprocess.run(['git','-C',root,'ls-tree','-r','--name-only','HEAD'],capture_output=True,text=True).stdout.split('\n')
ext=('.py','.mjs','.js','.sh','.java','.css','.html','.cmd','.c','.h','.svg')
pat=re.compile(rb'SPDX|copyright|licen[sc]e|\(c\)\s*(19|20)\d\d|\xc2\xa9|all rights|GPL|permission is hereby|redistribut', re.I)
tot=collections.Counter(); hits=collections.defaultdict(list); anywhere=collections.defaultdict(list)
for n in names:
    if not n: continue
    e=next((x for x in ext if n.endswith(x)),None)
    if n in ('arc1',): e='(script)'
    if not e: continue
    raw=subprocess.run(['git','-C',root,'show','HEAD:'+n],capture_output=True).stdout
    tot[e]+=1
    head=b'\n'.join(raw.split(b'\n')[:20])
    if pat.search(head): hits[e].append(n)
    if pat.search(raw): anywhere[e].append(n)
print('source files by type:',dict(tot),'total',sum(tot.values()))
print('files whose first 20 lines match a licence/copyright pattern:')
for e,l in hits.items():
    for n in l:
        raw=subprocess.run(['git','-C',root,'show','HEAD:'+n],capture_output=True).stdout.split(b'\n')[:20]
        for i,line in enumerate(raw,1):
            if pat.search(line): print('  ',n,i,line[:200].decode('utf-8','replace'))
print('files matching anywhere (count by type):',{e:len(l) for e,l in anywhere.items()})
# first-line shape of .py
shape=collections.Counter()
for n in names:
    if n.endswith('.py'):
        raw=subprocess.run(['git','-C',root,'show','HEAD:'+n],capture_output=True).stdout
        first=raw.split(b'\n',1)[0][:40]
        if first.startswith(b'#!'): shape['shebang']+=1
        elif first.startswith(b'"""') or first.startswith(b"'''") or first.startswith(b'r"""'): shape['docstring']+=1
        elif first.startswith(b'#'): shape['comment']+=1
        elif first.startswith(b'from') or first.startswith(b'import'): shape['import']+=1
        elif not first.strip(): shape['blank']+=1
        else: shape['other']+=1
print('.py first-line shapes:',dict(shape))
