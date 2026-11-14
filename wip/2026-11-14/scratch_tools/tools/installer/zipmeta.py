import sys,stat,json,hashlib
from zipfile import ZipFile
from collections import Counter
seen=Counter()
for p in sys.argv[1:]:
    with ZipFile(p) as z:
        infos=z.infolist()
        dirs=[i.filename for i in infos if i.is_dir()]
        modes=Counter(oct((i.external_attr>>16)) for i in infos)
        links=[i.filename for i in infos if stat.S_ISLNK(i.external_attr>>16)]
        bad=[i.filename for i in infos if i.filename.startswith('/') or '..' in i.filename.split('/') or '\\' in i.filename]
        tops=Counter(i.filename.split('/')[0] for i in infos)
        print(p.split('/')[-1],'entries',len(infos),'dirs',len(dirs),'symlinks',len(links),'bad',len(bad),'uncompressed',sum(i.file_size for i in infos))
        print('   modes',dict(modes))
        print('   top-level',dict(tops))
        for i in infos:seen[i.filename]+=1
print('duplicate names across given zips:',[n for n,c in seen.items() if c>1][:10])
