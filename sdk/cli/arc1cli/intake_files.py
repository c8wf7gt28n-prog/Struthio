"""Immutable quarantine snapshots over the existing content-addressed record format."""
from __future__ import annotations
import hashlib,io,json,os,stat,unicodedata,zipfile
from pathlib import Path
from . import record_store as records

MAX_FILES=10000
MAX_FILE=64*1024*1024
MAX_BUNDLE=512*1024*1024

def portable(name):return records.safe_name(unicodedata.normalize('NFC',name))

def regular(path):
    path=Path(path).expanduser().absolute()
    if not path.exists() or any(p.is_symlink() for p in (path,*path.parents)):
        raise ValueError('INTAKE_SOURCE_MISSING_OR_LINKED')
    return path

def checked_zip(archive,package_parts=False):
    members=[];seen=set();total=0;directories=set()
    for member in archive.infolist():
        candidate=member.filename.rstrip('/')
        # OOXML relationship parts conventionally use the basename .rels.
        if package_parts and candidate.split('/')[-1]=='.rels':
            portable(candidate[:-5]+'rels');name=candidate
        else:name=portable(candidate)
        key=name.casefold()
        if member.is_dir():
            if stat.S_ISLNK(member.external_attr>>16):raise ValueError('ARCHIVE_LINKED_DIRECTORY')
            if key in seen:raise ValueError('ARCHIVE_FILE_DIRECTORY_COLLISION')
            directories.add(key)
            continue
        if key in seen:raise ValueError('ARCHIVE_PATH_COLLISION')
        seen.add(key)
        if stat.S_ISLNK(member.external_attr>>16) or member.flag_bits&1:raise ValueError('ARCHIVE_LINK_OR_ENCRYPTED_MEMBER')
        if member.file_size>MAX_FILE or member.file_size>max(1,member.compress_size)*1000:raise ValueError('ARCHIVE_MEMBER_RESOURCE_LIMIT')
        total+=member.file_size;members.append(member)
        if len(members)>MAX_FILES or total>MAX_BUNDLE:raise ValueError('ARCHIVE_BUNDLE_RESOURCE_LIMIT')
    for key in seen:
        if key in directories or any('/'.join(key.split('/')[:i]) in seen for i in range(1,len(key.split('/')))):
            raise ValueError('ARCHIVE_FILE_DIRECTORY_COLLISION')
    return members

class Vault:
    def __init__(self,root):self.root=Path(root).resolve();self.root.mkdir(parents=True,mode=0o700,exist_ok=True)
    def path(self,digest):return records.inside(self.root,records.object_name(digest))
    def put(self,raw):
        digest=hashlib.sha256(raw).hexdigest();path=self.path(digest)
        if path.exists():
            if records.sha(path)!=digest:raise ValueError('QUARANTINE_OBJECT_CORRUPT')
        else:records.atomic(path,raw);path.chmod(0o444)
        return {'sha256':digest,'bytes':len(raw)}
    def read(self,digest,maximum=MAX_FILE):
        path=self.path(digest)
        if not path.is_file() or path.stat().st_size>maximum:raise ValueError('QUARANTINE_ORIGINAL_UNAVAILABLE_OR_CHANGED')
        with path.open('rb') as stream:raw=stream.read(maximum+1)
        if len(raw)>maximum or hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('QUARANTINE_ORIGINAL_UNAVAILABLE_OR_CHANGED')
        return raw

def read_stable(path,maximum=MAX_FILE,cancelled=lambda:False):
    path=regular(path)
    if not path.is_file() or path.stat().st_size>maximum:raise ValueError('INTAKE_FILE_RESOURCE_LIMIT')
    before=path.stat();chunks=[];total=0
    with path.open('rb') as stream:
        while raw:=stream.read(1024*1024):
            if cancelled():raise ValueError('INTAKE_CANCELLED')
            total+=len(raw)
            if total>maximum:raise ValueError('INTAKE_FILE_RESOURCE_LIMIT')
            chunks.append(raw)
    after=path.stat()
    if (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('INTAKE_SOURCE_CHANGED_DURING_READ')
    return b''.join(chunks)

def snapshot(source,vault,mode='snapshot',pinned_archive=None,cancelled=lambda:False,program_root=None):
    source=regular(source)
    if mode not in ('snapshot','external'):raise ValueError('INTAKE_SOURCE_MODE')
    if program_root:
        program=Path(program_root).resolve()
        if source.resolve().is_relative_to(program) or program.is_relative_to(source.resolve()):
            raise ValueError('APPLICATION_RUNTIME_DEPENDENCY_RETAINED: choose a data source outside the running program')
    rows=[];retained=[];source_info={'mode':mode,'origin':str(source),'origin_kind':'folder' if source.is_dir() else 'file'}
    def add(name,raw,origin_member=None):
        name=portable(name)
        if len(rows)>=MAX_FILES or sum(row['bytes'] for row in rows)+len(raw)>MAX_BUNDLE:raise ValueError('INTAKE_BUNDLE_RESOURCE_LIMIT')
        record=vault.put(raw);rows.append({'name':name,**record,'archive_member':origin_member})
    if source.is_dir():
        seen=set()
        for path in sorted(source.rglob('*')):
            if cancelled():raise ValueError('INTAKE_CANCELLED')
            if path.is_symlink():raise ValueError('INTAKE_LINKED_SOURCE_ENTRY')
            if not path.is_file():continue
            name=portable(path.relative_to(source).as_posix())
            if name.casefold() in seen:raise ValueError('SOURCE_PATH_COLLISION')
            seen.add(name.casefold());add(name,read_stable(path,cancelled=cancelled))
    else:
        raw=read_stable(source,MAX_BUNDLE,cancelled);source_info.update(vault.put(raw));source_info['archive_sha256']=hashlib.sha256(raw).hexdigest()
        if source.suffix.lower()=='.zip':
            source_info['origin_kind']='zip'
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                members=checked_zip(archive);selection=None;expected={}
                prefix='Ledger_User_Data_Archive/'
                if pinned_archive and source_info['archive_sha256']==pinned_archive:
                    manifest_raw=archive.read(prefix+'ARCHIVE_MANIFEST.json');seal=records.strict(archive.read(prefix+'SEAL.json'))
                    if hashlib.sha256(manifest_raw).hexdigest()!=seal['manifest_sha256']:raise ValueError('ORIGINAL_ARCHIVE_SEAL_MISMATCH')
                    manifest=records.strict(manifest_raw)
                    split=records.strict(archive.read(prefix+'Archive_Review/Separation_inventory.json'))
                    selection={prefix+'Original_Ledger/'+portable(name) for name in split['quarantined_original_paths']}
                    selection.update(member.filename for member in members if member.filename.startswith(prefix+'Planning/'))
                    retained=split['retained_original_paths']
                    expected={prefix+name:row for name,row in manifest['files'].items()}
                    source_info.update(seal='PINNED_ORIGINAL_ARCHIVE_VERIFIED',retained_program_paths=len(retained))
                for member in members:
                    if cancelled():raise ValueError('INTAKE_CANCELLED')
                    if selection is not None and member.filename not in selection:continue
                    data=archive.read(member)
                    if expected:
                        row=expected[member.filename]
                        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('ORIGINAL_ARCHIVE_MEMBER_CHANGED')
                    name=member.filename
                    if selection is not None:
                        name=name.removeprefix(prefix+'Original_Ledger/') if name.startswith(prefix+'Original_Ledger/') else name.removeprefix(prefix)
                    add(name,data,member.filename)
        else:add(source.name,raw)
    if not rows:raise ValueError('INTAKE_SOURCE_EMPTY')
    source_info['manifest_sha256']=hashlib.sha256(records.canonical([{k:row[k] for k in ('name','sha256','bytes')} for row in rows])).hexdigest()
    source_info['files']=len(rows);source_info['bytes']=sum(row['bytes'] for row in rows)
    return {'source':source_info,'items':rows,'runtime_resources_retained':len(retained)}

def verify_source(source,rows,vault):
    if source['mode']=='snapshot':
        if source['origin_kind'] in ('zip','file'):vault.read(source['sha256'],MAX_BUNDLE)
        # Folder snapshots are the immutable per-file originals, rather than live source paths.
        return True
    origin=regular(source['origin'])
    if source['origin_kind'] in ('zip','file'):
        if records.sha(origin)!=source['sha256']:raise ValueError('EXTERNAL_SOURCE_CHANGED_SINCE_REVIEW')
    else:
        for row in rows:
            path=records.inside(origin,row['name'])
            if not path.is_file() or records.sha(path)!=row['sha256']:raise ValueError('EXTERNAL_SOURCE_CHANGED_SINCE_REVIEW')
    return True
