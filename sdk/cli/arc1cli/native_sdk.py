"""Minimal native ARC-OS project route. Standard library, provider neutral.

Explicit local builds execute the owner's C compiler using the current account.
Generated modules are trusted native code, not a sandbox or board executables.
"""
from pathlib import Path
import hashlib,json,platform,re,shutil,subprocess,sys
from . import console_media,fat_image
NAME=re.compile(r'[a-z][a-z0-9_]{0,31}\Z')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def new(root,name,parent):
    if not NAME.fullmatch(name):raise ValueError('Native project name must match [a-z][a-z0-9_]{0,31}')
    dest=Path(parent).resolve()/name
    if dest.exists():raise ValueError('Native project already exists; refusing to overwrite')
    template=Path(root)/'sdk/templates/native_game';dest.mkdir(parents=True)
    for name in ('game.c','native.json','README.md'):(dest/name).write_text((template/name).read_text().replace('{{name}}',dest.name))
    return {'schema':'arc.native-project-created/1','project':str(dest),'physical_boot':False}

def source_hashes(root,project):
    root=Path(root).resolve();project=Path(project).resolve()
    result={}
    for name in ('game.c','native.json'):
        p=project/name
        if p.is_symlink() or not p.is_file() or p.stat().st_size>60000:raise ValueError('Native project source missing, symlinked or too large')
        result['project/'+name]=sha(p)
    result['software/arcos/include/arc_sdk.h']=sha(root/'software/arcos/include/arc_sdk.h')
    for p in sorted((root/'sdk/include').rglob('*.h')):result[p.relative_to(root).as_posix()]=sha(p)
    result['sdk/cli/arc1cli/native_sdk.py']=sha(root/'sdk/cli/arc1cli/native_sdk.py')
    return result

def build(root,project,revision=None):
    root=Path(root).resolve();project=Path(project).resolve();sources=source_hashes(root,project)
    data=json.loads((project/'native.json').read_text());name=data.get('name','')
    if data.get('schema')!='arc.native-project/1' or not NAME.fullmatch(name) or data.get('source')!='game.c' or data.get('abi')!=1 or data.get('target')!='host-only':raise ValueError('Native project contract rejected')
    if sys.platform not in ('linux','darwin'):raise ValueError('Native ARC-OS sample currently needs POSIX host')
    compiler=shutil.which('cc')
    if not compiler:raise ValueError('A local C11 compiler is required')
    out=project/'.native-build'
    if out.is_symlink():raise ValueError('Native build directory must not be a symlink')
    out.mkdir(exist_ok=True);suffix='.dylib' if sys.platform=='darwin' else '.so';artifact=out/(name+suffix)
    for filename in (artifact.name,'game.arcusb','thumb-drive.fat32.img','gamecard.json','build.json'):
        if (out/filename).is_symlink():raise ValueError('Native output must not be a symlink')
    argv=[compiler,'-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fPIC','-dynamiclib' if sys.platform=='darwin' else '-shared',
        '-I'+str(root/'software/arcos/include'),'-I'+str(root/'sdk/include'),str(project/'game.c'),'-o',str(artifact)]
    p=subprocess.run(argv,cwd=project,capture_output=True,text=True,timeout=45)
    if p.returncode:raise ValueError('Native sample build failed: '+p.stderr[-4000:])
    if source_hashes(root,project)!=sources:raise ValueError('Native project source changed during build')
    revision=revision or hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest()
    card={'schema':'arc-os.gamecard/1','abi':1,'name':name,'artifact':artifact.name,'target':'host-'+sys.platform+'-'+platform.machine(),
        'sha256':sha(artifact),'sources':sources,'physical_boot':False}
    package=console_media.pack(card,artifact.read_bytes(),revision);(out/'game.arcusb').write_bytes(package)
    (out/'thumb-drive.fat32.img').write_bytes(fat_image.pack(package));(out/'gamecard.json').write_text(json.dumps(card,indent=2)+'\n')
    report={'schema':'arc.native-build/1','class':'HOST_SIM','project':str(project),'card':card,'revision':revision,
        'artifact':str(artifact),'package':str(out/'game.arcusb'),'fat_image':str(out/'thumb-drive.fat32.img'),'argv':argv,
        'stdout':p.stdout,'stderr':p.stderr,'source_hashes':sources,'physical_boot':False,'os_sandbox':False}
    (out/'build.json').write_text(json.dumps(report,indent=2)+'\n');return report
