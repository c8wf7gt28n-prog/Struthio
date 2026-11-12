"""Valid ZIP volumes at most 15,000,000 bytes, retaining the complete payload.

Only an individually oversized file becomes hashed chunks. INSTALL_LS restores
it before full payload verification. No existing source/evidence file is dropped.
The checkpoint written into RELEASE_PARTS.json is an argument; there is no default.

    python3 tools/package_release_parts.py OUT/Graphite_0.1_full.zip PARTS_FOLDER "Graphite 0.1"

The volumes are named after the archive without its _full suffix: Graphite_0.1_part_01.zip, Graphite_0.1_part_02.zip, ...
(tools/package_graphite.py writes the archive).
"""
from pathlib import Path
from copy import copy
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
import hashlib,json,os,shutil,sys,tempfile
LIMIT=15_000_000
CHUNK=8_000_000
# Entry points and start-here documents go into the first volume; names absent from the archive are simply not there.
PRIORITY={'MANIFEST.json','INSTALL_LS.py','START_MINIMAL_DEBIAN.sh','LS_XSESSION.sh','INSTALL_DEBIAN.sh','INSTALL_LEDGER.sh',
    'START_OFFICE.sh','README.md','RECORD_OF_DIRECTIONS.md','docs/DAILY_GUIDE.md','docs/MINIMAL_DEBIAN_INSTALL_01.md'}

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def package(archive,destination,checkpoint):
    if not isinstance(checkpoint,str) or not checkpoint.strip():raise ValueError('Name the checkpoint (the release) these parts belong to, for example Graphite 0.1')
    archive=Path(archive);destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    if any(destination.iterdir()):raise ValueError('Choose an empty parts folder')
    chunks={};virtual=[];volumes=[]
    with ZipFile(archive) as original,tempfile.TemporaryDirectory(prefix='ledger-parts-',dir=destination.parent) as temporary:
        temporary=Path(temporary)
        for index,info in enumerate(original.infolist()):
            if info.compress_size+65536<=LIMIT:
                virtual.append(dict(info=copy(info),source=info.filename,path=None,cost=info.compress_size+256+4*len(info.filename.encode())+2*len(info.extra)+len(info.comment)))
                continue
            group=dict(bytes=info.file_size,sha256=None,mode=info.external_attr>>16,chunks=[]);digest=hashlib.sha256()
            with original.open(info) as source:
                sequence=0
                while block:=source.read(CHUNK):
                    sequence+=1;name=f'__LS_RELEASE_CHUNKS__/file{index:04}_chunk{sequence:03}.bin'
                    path=temporary/f'{index}_{sequence}.bin';path.write_bytes(block);digest.update(block)
                    partinfo=ZipInfo(name,date_time=info.date_time);partinfo.external_attr=0o100644<<16
                    virtual.append(dict(info=partinfo,source=None,path=path,cost=int(len(block)*1.002)+512))
                    group['chunks'].append(dict(entry=name,bytes=len(block),sha256=hashlib.sha256(block).hexdigest()))
            group['sha256']=digest.hexdigest();chunks[info.filename]=group
        # Put the entry points and full specification in the first ZIP, then fit
        # larger assets first to avoid mostly empty volumes.
        first=[r for r in virtual if r['info'].filename in PRIORITY or 'COMPLETE_PROJECT_SPEC' in r['info'].filename]
        groups=[dict(cost=sum(r['cost'] for r in first),entries=first)]
        rest=[r for r in virtual if r not in first]
        for row in sorted(rest,key=lambda r:r['cost'],reverse=True):
            group=next((g for g in groups if g['cost']+row['cost']<LIMIT-65536),None)
            if group is None:group=dict(cost=0,entries=[]);groups.append(group)
            group['entries'].append(row);group['cost']+=row['cost']
        for index,group in enumerate(groups,1):
            path=destination/(archive.stem.removesuffix('_full')+f'_part_{index:02}.zip');staging=path.with_suffix('.zip.partial')
            try:
                with ZipFile(staging,'w',ZIP_DEFLATED,compresslevel=6) as out:
                    for row in group['entries']:
                        info=copy(row['info']);info.compress_type=ZIP_DEFLATED
                        with (row['path'].open('rb') if row['path'] else original.open(row['source'])) as source,out.open(info,'w') as target:shutil.copyfileobj(source,target)
                if staging.stat().st_size>LIMIT:raise ValueError('Volume exceeds 15 MB')
                with ZipFile(staging) as check:
                    if check.testzip() is not None:raise ValueError('ZIP volume CRC failure')
                os.replace(staging,path)
            finally:staging.unlink(missing_ok=True)
            volumes.append(dict(name=path.name,bytes=path.stat().st_size,sha256=sha(path)))
        data=dict(schema='ledger.release-parts/1',format='ZIP_VOLUMES_WITH_FILE_CHUNKS',
            checkpoint=checkpoint.strip(),part_limit_bytes=LIMIT,source_archive_bytes=archive.stat().st_size,
            source_archive_sha256=sha(archive),payload_manifest_sha256=hashlib.sha256(original.read('MANIFEST.json')).hexdigest(),
            payload_entries=len(original.namelist()),parts=volumes,file_chunks=chunks,
            installer='INSTALL_LS.py verifies all parts, restores split files, then verifies the complete payload')
        (destination/'RELEASE_PARTS.json').write_text(json.dumps(data,indent=2)+'\n')
    return data


if __name__=='__main__':
    if len(sys.argv)!=4:print('Usage: python3 tools/package_release_parts.py ARCHIVE.zip PARTS_FOLDER "Graphite 0.1"',file=sys.stderr);raise SystemExit(2)
    result=package(sys.argv[1],sys.argv[2],sys.argv[3]);print(json.dumps(dict(checkpoint=result['checkpoint'],parts=result['parts'],split_files=list(result['file_chunks'])),indent=2))
