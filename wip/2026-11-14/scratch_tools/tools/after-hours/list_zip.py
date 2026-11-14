import sys, zipfile, hashlib, os, json
zp = sys.argv[1]; srcdir = sys.argv[2]
print('zip sha256', hashlib.sha256(open(zp,'rb').read()).hexdigest(), os.path.getsize(zp))
z = zipfile.ZipFile(zp)
print('comment', z.comment)
for i in z.infolist():
    data = z.read(i) if not i.is_dir() else b''
    print(f"{i.file_size:>9} {i.compress_size:>9} {i.date_time} {hashlib.sha256(data).hexdigest()[:64]} {i.filename}")
print('testzip', z.testzip())
print('--- Sources')
for n in sorted(os.listdir(srcdir)):
    b = open(os.path.join(srcdir,n),'rb').read()
    print(len(b), hashlib.sha256(b).hexdigest(), n)
# print small text members
for i in z.infolist():
    if i.is_dir(): continue
    if i.file_size < 20000 and not i.filename.lower().endswith(('.pdf','.png')):
        print('=====', i.filename)
        try:
            print(z.read(i).decode('utf-8'))
        except Exception as e:
            print('binary', e)
