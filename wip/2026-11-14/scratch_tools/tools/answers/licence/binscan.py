import subprocess, re, collections, zipfile, io
root='/home/user/Struthio'
names=[n for n in subprocess.run(['git','-C',root,'ls-tree','-r','--name-only','HEAD'],capture_output=True,text=True).stdout.split('\n') if n]
pat=re.compile(rb'copyright|licen[sc]e|all rights reserved|creativecommons|cc:license|dc:rights|rights reserved|GPL-|General Public', re.I)
skip=('runtimes/',)
binext=('.png','.webp','.jpeg','.jpg','.ico','.mp3','.pdf','.ttf','.otf','.sqlite','.gz','.jar','.zip','.docx','.xlsx','.ods','.kicad_pcb','.svg','.csv')
res=collections.defaultdict(list)
for n in names:
    if n.startswith(skip): continue
    if not n.endswith(binext): continue
    raw=subprocess.run(['git','-C',root,'show','HEAD:'+n],capture_output=True).stdout
    found=set()
    for m in pat.finditer(raw):
        s=max(0,m.start()-40); e=min(len(raw),m.end()+90)
        found.add(raw[s:e].decode('latin-1').replace('\n',' ').replace('\r',' '))
    if n.endswith(('.docx','.xlsx','.ods')):
        try:
            z=zipfile.ZipFile(io.BytesIO(raw))
            for i in z.infolist():
                d=z.read(i)
                for m in pat.finditer(d):
                    s=max(0,m.start()-60); e=min(len(d),m.end()+140)
                    found.add('['+i.filename+'] '+d[s:e].decode('utf-8','replace').replace('\n',' '))
                if i.filename.endswith(('core.xml','meta.xml','app.xml')):
                    txt=d.decode('utf-8','replace')
                    for tag in re.findall(r'<(dc:creator|cp:lastModifiedBy|Company|dc:rights|meta:initial-creator|dc:title)>([^<]*)<',txt):
                        found.add('[meta %s] %s=%s'%(i.filename,tag[0],'<redacted name>' if tag[0] in('dc:creator','cp:lastModifiedBy','meta:initial-creator') and tag[1] else tag[1]))
        except Exception as ex: found.add('zip error '+str(ex))
    if found: res[n]=sorted(found)
for n,f in res.items():
    print('##',n,len(f))
    for x in f[:6]: print('    ',x[:260])
print('files scanned', sum(1 for n in names if n.endswith(binext) and not n.startswith(skip)))
