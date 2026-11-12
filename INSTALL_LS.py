#!/usr/bin/env python3
"""Install Graphite: verified ZIP parts from USB or a pinned public HTTPS release.

This is the Graphite installer; its file name, INSTALL_LS.py, is kept because scripts, tests and release notes call it.

Runs on Python 3.11-3.13 in an existing Debian installation. Does not partition
or install Debian, rewrite login files, download models or launch native trials.
The final line names what actually happened: program extracted and verified,
runtime imports verified, Debian prerequisites installed or skipped, minimal
session commands present or missing. Owner display and native/model
qualification remain separate; nothing here claims them.
"""
import argparse,errno,hashlib,json,os,platform,re,shutil,ssl,stat,subprocess,sys,tempfile
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit,urljoin
from urllib.request import HTTPSHandler,HTTPRedirectHandler,Request,build_opener
from zipfile import BadZipFile,ZipFile

LIMIT=15_000_000
HEX64='[a-f0-9]{64}'
PREREQUISITES_SKIPPED=3 # INSTALL_DEBIAN.sh: runtime verified, apt prerequisites skipped (no --yes and no terminal, or declined).
SESSION_COMMANDS=('startx','fluxbox','dbus-run-session') # plus an X server, as START_MINIMAL_DEBIAN.sh checks.

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def checked_url(url):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Use a public HTTPS URL without embedded credentials')
    return url


class HTTPSRedirect(HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        checked_url(newurl)
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def download(url,path,limit):
    opener=build_opener(HTTPSHandler(context=ssl.create_default_context()),HTTPSRedirect())
    total=0
    with opener.open(Request(checked_url(url),headers={'User-Agent':'Ledger-Slate-Installer/1'}),timeout=60) as response,path.open('xb') as target:
        checked_url(response.geturl())
        while block:=response.read(1024*1024):
            total+=len(block)
            if total>limit:raise ValueError('Download exceeds declared size')
            target.write(block)


def chunk_mode(mode):
    """Restored mode of a split file: the recorded permission bits, else 0644."""
    return (mode&0o777) or 0o644


def set_mode(path,mode):
    """Restore a file's permission bits; media that cannot hold them (FAT, exFAT) is named instead of a bare errno."""
    try:os.chmod(path,mode)
    except PermissionError as exc:
        if exc.errno==errno.EPERM:raise ValueError('The folder that will contain the installation cannot hold the program file permissions (FAT or exFAT media?); choose a folder on the computer') from exc
        raise


def chunk_inventory(groups):
    """Validate the file_chunks inventory before any write (a damaged manifest is a refusal, not a traceback)."""
    if not isinstance(groups,dict) or len(groups)>128:raise ValueError('Invalid file chunk inventory')
    entries=set()
    for name,meta in groups.items():
        relative=PurePosixPath(name) if isinstance(name,str) else None
        if relative is None or relative.is_absolute() or '..' in relative.parts or '\\' in name or not relative.parts or relative.parts[0]=='__LS_RELEASE_CHUNKS__':
            raise ValueError('Invalid split file path in the chunk inventory')
        if not isinstance(meta,dict) or type(meta.get('bytes')) is not int or meta['bytes']<=0 or not re.fullmatch(HEX64,str(meta.get('sha256'))) or type(meta.get('mode')) is not int:
            raise ValueError('Invalid file chunk metadata: '+name)
        if not chunk_mode(meta['mode'])&0o400:raise ValueError('Split file chunk mode denies owner read: '+name)
        chunks=meta.get('chunks')
        if not isinstance(chunks,list) or not 1<=len(chunks)<=256:raise ValueError('Invalid file chunk list: '+name)
        for chunk in chunks:
            entry=chunk.get('entry') if isinstance(chunk,dict) else None
            if not isinstance(entry,str) or not re.fullmatch(r'__LS_RELEASE_CHUNKS__/[A-Za-z0-9_.-]+',entry) or entry in entries:raise ValueError('Invalid or repeated chunk entry: '+name)
            if type(chunk.get('bytes')) is not int or not 0<chunk['bytes']<=LIMIT or not re.fullmatch(HEX64,str(chunk.get('sha256'))):raise ValueError('Invalid chunk entry metadata: '+entry)
            entries.add(entry)
        if sum(chunk['bytes'] for chunk in chunks)!=meta['bytes']:raise ValueError('Chunk sizes do not add up to the split file: '+name)
    return groups


def manifest(path,expected=None):
    path=Path(path)
    if path.stat().st_size>1024*1024:raise ValueError('Release manifest is too large')
    if expected and digest(path)!=expected:raise ValueError('Release manifest checksum does not match the pinned value')
    data=json.loads(path.read_text())
    if not isinstance(data,dict) or data.get('schema')!='ledger.release-parts/1' or not isinstance(data.get('parts'),list) or not 1<=len(data['parts'])<=64:
        raise ValueError('Unsupported release manifest')
    names=set()
    for row in data['parts']:
        name=row.get('name','') if isinstance(row,dict) else ''
        if not re.fullmatch(r'[A-Za-z0-9_.-]+\.zip',name) or name in names:raise ValueError('Invalid or duplicate part name')
        if type(row.get('bytes')) is not int or not 0<row['bytes']<=LIMIT:raise ValueError('A ZIP part exceeds 15 MB')
        if not re.fullmatch(HEX64,str(row.get('sha256'))):raise ValueError('Missing part checksum')
        names.add(name)
    if not re.fullmatch(HEX64,str(data.get('payload_manifest_sha256'))):raise ValueError('Missing payload manifest checksum')
    chunk_inventory(data.get('file_chunks',{}))
    return data


def verify_part(path,row):
    if not path.is_file() or path.is_symlink() or path.stat().st_size!=row['bytes'] or digest(path)!=row['sha256']:
        raise ValueError('Missing or changed release part: '+row['name'])



def restore_chunks(stage,data):
    groups=chunk_inventory(data.get('file_chunks',{}))
    for name,meta in groups.items():
        target=stage.joinpath(*PurePosixPath(name).parts)
        if target.exists():raise ValueError('Split file conflicts with an archive entry: '+name)
        target.parent.mkdir(parents=True,exist_ok=True);paths=[]
        with target.open('xb') as out:
            for chunk in meta['chunks']:
                source=stage/chunk['entry']
                if not source.is_file() or source.is_symlink() or source.stat().st_size!=chunk['bytes'] or digest(source)!=chunk['sha256']:
                    raise ValueError('Missing or changed file chunk: '+chunk['entry'])
                with source.open('rb') as stream:shutil.copyfileobj(stream,out)
                paths.append(source)
        if target.stat().st_size!=meta['bytes'] or digest(target)!=meta['sha256']:raise ValueError('Reassembled file checksum mismatch: '+name)
        set_mode(target,chunk_mode(meta['mode']))
        for source in paths:source.unlink()
    folder=stage/'__LS_RELEASE_CHUNKS__'
    if folder.exists():
        if any(folder.iterdir()):raise ValueError('Unreferenced chunk files in the release parts')
        folder.rmdir()


def containing_folder(target):
    """Check the folder that will hold the installation before the first write; return the ancestors this run must create, deepest first."""
    anchor=target.parent;missing=[]
    while not anchor.exists() and anchor.parent!=anchor:missing.append(anchor);anchor=anchor.parent
    if not anchor.is_dir():raise ValueError('The folder that will contain the installation is not a folder: '+str(anchor))
    if not os.access(anchor,os.W_OK|os.X_OK):raise ValueError('The folder that will contain the installation must be writable: '+str(anchor))
    return missing


def extract(parts,data,target):
    target=Path(target).expanduser().absolute()
    if target.exists():raise ValueError('Choose a new installation folder; the existing folder is retained')
    for row in data['parts']:verify_part(Path(parts)/row['name'],row)
    created=containing_folder(target)
    try:
        try:
            target.parent.mkdir(parents=True,exist_ok=True);temporary=tempfile.TemporaryDirectory(prefix='.ledger-install-',dir=target.parent)
        except OSError as exc:
            if exc.errno in (errno.EACCES,errno.EPERM,errno.EROFS):raise ValueError('The folder that will contain the installation must be writable: '+str(target.parent)) from exc
            raise
        with temporary:
            stage=Path(temporary.name)/'program';stage.mkdir();seen=set();total=0
            for row in data['parts']:
                with ZipFile(Path(parts)/row['name']) as archive:
                    for info in archive.infolist():
                        name=info.filename;relative=PurePosixPath(name);mode=info.external_attr>>16
                        if relative.is_absolute() or '..' in relative.parts or '\\' in name or name in seen or stat.S_ISLNK(mode):
                            raise ValueError('Invalid or duplicate archive entry: '+name)
                        seen.add(name);total+=info.file_size
                        if total>2*1024**3:raise ValueError('Release exceeds the installation size budget')
                        path=stage.joinpath(*relative.parts)
                        if info.is_dir():path.mkdir(parents=True,exist_ok=True);continue
                        path.parent.mkdir(parents=True,exist_ok=True)
                        with archive.open(info) as source,path.open('xb') as out:shutil.copyfileobj(source,out)
                        set_mode(path,(mode&0o777) or 0o644)
            restore_chunks(stage,data)
            payload=stage/'MANIFEST.json'
            if not payload.is_file() or digest(payload)!=data['payload_manifest_sha256']:raise ValueError('Payload manifest checksum mismatch')
            records=json.loads(payload.read_text());records=records.get('files') if isinstance(records,dict) else None
            if not isinstance(records,dict):raise ValueError('Unsupported payload manifest')
            actual={p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()}
            if actual!=set(records)|{'MANIFEST.json'}:raise ValueError('Incomplete release: every ZIP part is required')
            for name,meta in records.items():
                path=stage/name
                if path.stat().st_size!=meta['bytes'] or digest(path)!=meta['sha256']:raise ValueError('Payload mismatch: '+name)
            os.replace(stage,target)
    except BaseException:
        for folder in created: # Leave no empty folder chain behind after a refused or failed installation.
            try:folder.rmdir()
            except OSError:break
        raise
    return target


def offline_cache(folder):
    """A complete dependency cache is a separate, owner-prepared USB asset."""
    folder=Path(folder).resolve();index=folder/'OFFLINE_FILES.json'
    if not index.is_file():raise ValueError('Offline USB needs OFFLINE_FILES.json plus matching Debian packages and Python wheels; no network fallback')
    data=json.loads(index.read_text());rows=data.get('files',{})
    if data.get('schema')!='ledger.offline-files/1' or not isinstance(rows,dict):raise ValueError('Invalid offline dependency inventory')
    platform_target=data.get('target')
    if platform_target is not None:
        host=host_preflight(False)
        debian=(host['debian_release'] or '').split('.',1)[0]
        if not isinstance(platform_target,dict) or platform_target.get('debian_major')!=debian or platform_target.get('architecture')!=host['architecture']:
            raise ValueError('The offline dependency cache targets a different Debian release or architecture')
    wheels=[];debs=[]
    for name,meta in rows.items():
        relative=PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name:raise ValueError('Invalid dependency path')
        path=folder.joinpath(*relative.parts)
        if not path.resolve().is_relative_to(folder) or path.is_symlink():raise ValueError('Dependency path leaves the USB bundle')
        if not path.is_file() or path.stat().st_size!=meta['bytes'] or digest(path)!=meta['sha256']:raise ValueError('Offline dependency checksum mismatch: '+name)
        if relative.parts[0]=='wheels' and path.suffix=='.whl':wheels.append(path)
        elif relative.parts[0]=='debs' and path.suffix=='.deb':debs.append(path)
        else:raise ValueError('Offline inventory accepts wheels/ and debs/ only')
    actual={p.relative_to(folder).as_posix() for sub in ('wheels','debs') for p in (folder/sub).rglob('*')
            if p.is_file() and p.name!='.DS_Store' and not p.name.startswith('._')}
    if actual!=set(rows) or not wheels:raise ValueError('Offline cache is incomplete or has unlisted files')
    return folder/'wheels',debs


def debian_host():
    return Path('/etc/debian_version').is_file()


def install_offline_debian(debs, *, sudo=False):
    """Let APT acquire verified local files with all repository sources disabled."""
    with tempfile.TemporaryDirectory(prefix='graphite-apt-local-') as temporary:
        empty = Path(temporary)
        (empty / 'sources.list').touch()
        for folder in ('sources.list.d', 'lists'):
            (empty / folder).mkdir()
        command = ['sudo'] if sudo else []
        command.extend(['apt-get', '-o', f'Dir::Etc::sourcelist={empty / "sources.list"}',
                        '-o', f'Dir::Etc::sourceparts={empty / "sources.list.d"}',
                        '-o', f'Dir::State::lists={empty / "lists"}', '--no-remove',
                        '-y', '--no-install-recommends', 'install'])
        subprocess.run(command + [str(path) for path in debs], check=True)


def missing_session_commands():
    """The commands START_MINIMAL_DEBIAN.sh needs from a text login that are absent here."""
    missing=[name for name in SESSION_COMMANDS if not shutil.which(name)]
    if not (shutil.which('Xorg') or shutil.which('X')):missing.append('Xorg')
    return missing


def host_preflight(minimal_session):
    """Report observations available before extraction, including from a root console."""
    try:
        debian_release = Path('/etc/debian_version').read_text(encoding='utf-8').strip()
    except (OSError, UnicodeError):
        debian_release = None
    return {
        'debian_release': debian_release,
        'kernel': platform.release(),
        'architecture': platform.machine(),
        'python': platform.python_version(),
        'root_shell': hasattr(os, 'geteuid') and os.geteuid() == 0,
        'apt_available': bool(shutil.which('apt-get')),
        'sudo_available': bool(shutil.which('sudo')),
        'missing_session_commands': missing_session_commands() if minimal_session else None,
        'office_launcher_available': bool(shutil.which('libreoffice') or shutil.which('soffice')),
        'drm_render_nodes': sorted(node.name for node in Path('/dev/dri').glob('renderD*')),
    }


def status_line(prerequisites,minimal_session,missing):
    parts=['Program extracted and verified','Runtime imports verified',prerequisites]
    if minimal_session:parts.append('Minimal session prerequisites present' if not missing else 'Minimal session prerequisites missing ('+', '.join(missing)+')')
    parts.append('Owner display and native/model qualification remain separate')
    return ' · '.join(parts)+'.'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True);source.add_argument('--usb',type=Path);source.add_argument('--public-manifest')
    parser.add_argument('--manifest-sha256');parser.add_argument('--target',type=Path)
    parser.add_argument('--offline',action='store_true');parser.add_argument('--profile',choices=('desktop','suite'),default='desktop')
    parser.add_argument('--minimal-session',action='store_true');parser.add_argument('--yes',action='store_true')
    parser.add_argument('--calc',action='store_true',help='Add LibreOffice Calc for the worksheet handoff')
    parser.add_argument('--vulkan',action='store_true',help='Add maintained Debian 13 Vulkan/Radeon dependencies; model/device qualification stays separate')
    parser.add_argument('--extract-only',action='store_true');parser.add_argument('--plan',action='store_true')
    system=parser.add_mutually_exclusive_group()
    system.add_argument('--system-only',action='store_true',help='Install only verified offline Debian packages from a root console')
    system.add_argument('--system-ready',action='store_true',help='Use the offline wheels after installing system packages separately')
    args=parser.parse_args(argv)
    if not args.system_only and args.target is None:parser.error('Installation requires --target')
    if (args.system_only or args.system_ready) and (not args.offline or args.extract_only):
        parser.error('The system package phases require an offline USB install')
    if args.offline and not args.usb:parser.error('Offline installation requires --usb')
    if args.public_manifest:
        checked_url(args.public_manifest)
        if not re.fullmatch(HEX64,args.manifest_sha256 or ''):parser.error('Public downloads require --manifest-sha256 from a trusted release source')
    if args.plan:
        result=dict(mode='USB_OFFLINE' if args.offline else 'USB_WITH_PUBLIC_DEPENDENCIES' if args.usb else 'PUBLIC_HTTPS',
            target=str(args.target.expanduser()) if args.target else None,profile=args.profile,minimal_session=args.minimal_session,vulkan=args.vulkan,extract_only=args.extract_only,
            calc=args.calc or args.profile=='suite',host=host_preflight(args.minimal_session),
            steps=['Verify every release ZIP and extract into a new folder','Install declared Debian prerequisites and pinned Python dependencies','Verify runtime imports, package and source bindings'],
            offline_requirements='OFFLINE_FILES.json, complete matching debs/ and wheels/' if args.offline else None,
            prerequisites='installed with sudo (--yes)' if args.yes else 'from the offline cache' if args.offline else 'asked at a terminal prompt; skipped and reported when no terminal is attached',
            starts_with='bash START_MINIMAL_DEBIAN.sh' if args.minimal_session else 'bash START_OFFICE.sh',
            does_not_install='Debian OS, models or native/runtime qualifications'+('' if args.vulkan else ', or firmware'),writes=False,downloads=False)
        if args.vulkan:result['vulkan_dependencies']='Maintained Debian 13 packages; a complete offline cache must supply these dependencies when --offline is used'
        if args.extract_only:result.update(steps=result['steps'][:1],prerequisites=None,starts_with=None,then='Nothing is installed; run bash INSTALL_DEBIAN.sh --quick in the new folder when ready')
        if args.system_only:
            result.update(mode='USB_OFFLINE_SYSTEM_ONLY',target=None,steps=['Verify the offline dependency inventory','Install its local Debian packages as root'],starts_with=None)
        elif args.system_ready:
            result.update(prerequisites='Already installed separately; install the pinned Python wheels from the offline cache')
        print(json.dumps(result,indent=2));return 0
    if args.system_only:
        if not debian_host() or not hasattr(os,'geteuid') or os.geteuid()!=0:
            raise ValueError('Run the offline system package phase from a Debian root console')
        _, debs=offline_cache(args.usb)
        if not debs:raise ValueError('The offline cache contains no Debian system packages')
        install_offline_debian(debs)
        print('Verified offline Debian packages installed. Continue as your ordinary user with --offline --system-ready.')
        return 0
    if not args.extract_only and hasattr(os,'geteuid') and os.geteuid()==0:raise ValueError('Run as your ordinary Debian user; only prerequisite installation uses sudo')
    cache=None
    if args.offline and not args.extract_only:cache=offline_cache(args.usb) # Refuse incomplete offline media before any installation write.
    with tempfile.TemporaryDirectory(prefix='ledger-release-') as temporary:
        parts=Path(temporary) if args.public_manifest else args.usb.resolve()
        if args.public_manifest:
            path=parts/'RELEASE_PARTS.json';download(args.public_manifest,path,1024*1024);data=manifest(path,args.manifest_sha256)
            for row in data['parts']:download(urljoin(args.public_manifest,row['name']),parts/row['name'],row['bytes'])
        else:data=manifest(parts/'RELEASE_PARTS.json',args.manifest_sha256)
        target=extract(parts,data,args.target)
    print('Verified program extracted to '+str(target),flush=True)
    if args.extract_only:print('Program extracted and verified · nothing installed · next: bash '+str(target/'INSTALL_DEBIAN.sh')+' --quick');return 0
    if not debian_host():raise ValueError('This installer targets Debian; use the existing platform runtime installer')
    options=['bash',str(target/'INSTALL_DEBIAN.sh'),'--quick']
    if args.yes:options.append('--yes')
    if args.profile=='suite':options+=['--engineering','--workers','--math','--experiments']
    if args.minimal_session:options.append('--minimal-session')
    if args.calc and args.profile!='suite':options.append('--calc')
    if args.vulkan:options.append('--vulkan')
    if cache:
        wheels,debs=cache
        if debs and not args.system_ready:install_offline_debian(debs, sudo=True)
        options+=['--offline',str(wheels)]
    terminal=bool(sys.stdin and sys.stdin.isatty())
    if not cache and not args.yes and not terminal:print('No terminal is attached and --yes was not given: Debian prerequisites will be skipped (add --yes to install them with sudo).',flush=True)
    result=subprocess.run(options,cwd=target)
    if result.returncode==PREREQUISITES_SKIPPED:prerequisites='Debian prerequisites skipped ('+('declined at the prompt' if terminal else 'no --yes and no terminal for the sudo prompt')+')'
    elif result.returncode==0:
        prerequisites = ('Debian system packages supplied separately' if args.system_ready else
                         'Debian prerequisites installed from the offline cache' if cache and cache[1] else
                         'Debian prerequisites skipped (the offline cache lists no .deb packages)' if cache else
                         'Debian prerequisites installed')
    else:raise ValueError('Dependency installation returned status %d; the verified program is retained at %s for inspection. Re-run: %s'%(result.returncode,target,' '.join(options)))
    missing=missing_session_commands() if args.minimal_session else []
    print(status_line(prerequisites,args.minimal_session,missing),flush=True)
    if args.minimal_session and missing:
        print('Start from an existing desktop with: bash '+str(target/'START_OFFICE.sh'))
        calc_flag = ' --calc' if args.calc else ''
        if args.offline:
            print('Complete the offline system package phase from the USB before starting the dedicated session.')
        else:
            print('Before the dedicated text-login session, install its prerequisites: bash '+str(target/'INSTALL_DEBIAN.sh')+' --minimal-session --quick --yes'+calc_flag)
    else:print('Start with: bash '+str(target/('START_MINIMAL_DEBIAN.sh' if args.minimal_session else 'START_OFFICE.sh')))
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,KeyError,TypeError,AttributeError,BadZipFile,subprocess.CalledProcessError) as exc:
        print('Installation needs attention: '+('missing field %s in a release file'%exc if isinstance(exc,KeyError) else str(exc)),file=sys.stderr);raise SystemExit(1)
