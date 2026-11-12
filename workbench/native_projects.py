"""Bounded native SDK projects through the existing Kernel and C USB model."""
import argparse,json,time,sys
from pathlib import Path
from sdk.cli.arc1cli import native_sdk,console_media,fat_image
from . import console_build,console_services,record_io as io

NAME={'type':'string','pattern':'^[a-z][a-z0-9_]{0,31}$','maxLength':32}
FIELDS={'native.create':({'name':NAME},['name']),'native.inspect':({'name':NAME},['name']),
        'native.open':({'name':NAME},['name'])}
SCOPES={'native.create':'approve','native.inspect':'read','native.open':'execute'}

def project(root,name,exists=True):
    if not isinstance(name,str) or not native_sdk.NAME.fullmatch(name):raise ValueError('INVALID_NATIVE_PROJECT_NAME')
    root=Path(root).resolve();parent=root/'examples';path=parent/name
    if parent.is_symlink() or path.is_symlink() or path.resolve().parent!=parent.resolve():raise ValueError('NATIVE_PROJECT_PATH')
    if exists:
        native_sdk.source_hashes(root,path)
        data=io.strict_json((path/'native.json').read_bytes())
        if data!={'schema':'arc.native-project/1','name':name,'abi':1,'target':'host-only','source':'game.c'}:
            # Descriptive template fields are permitted; execution fields stay fixed.
            if any(data.get(k)!=v for k,v in {'schema':'arc.native-project/1','name':name,'abi':1,'target':'host-only','source':'game.c'}.items()):raise ValueError('NATIVE_PROJECT_CONTRACT')
    return path

def current(root,name):
    root=Path(root).resolve();p=project(root,name);out=p/'.native-build'
    r=io.load(root,'build/native_projects/'+name+'.json')
    if out.is_symlink() or r.get('card',{}).get('artifact')!=name+('.dylib' if sys.platform=='darwin' else '.so'):raise ValueError('NATIVE_ARTIFACT_PATH')
    if r.get('name')!=name or r.get('source_hashes')!=native_sdk.source_hashes(root,p):raise ValueError('STALE_NATIVE_SOURCE: rebuild this native project')
    if r.get('revision')!=console_build.current(root)['revision']:raise ValueError('STALE_NATIVE_CONSOLE: rebuild this native project against the current console')
    for file,sha in r['artifact_hashes'].items():
        if file not in (r['card']['artifact'],'game.arcusb','thumb-drive.fat32.img') or (out/file).is_symlink() or io.sha(out/file)!=sha:raise ValueError('NATIVE_ARTIFACT_CHANGED')
    package=(out/'game.arcusb').read_bytes();card=r['card']
    console_media.inspect(package,target=console_build.current(root)['target'],revision=r['revision'],artifact_sha256=card['sha256'],sources=r['source_hashes'],artifact_name=card['artifact'])
    if (out/'thumb-drive.fat32.img').read_bytes()!=fat_image.pack(package):raise ValueError('NATIVE_FAT_IMAGE_CHANGED')
    return r

def build(root,name):
    root=Path(root).resolve();p=project(root,name);console=console_build.current(root)
    r=native_sdk.build(root,p,console['revision'])
    r.update(name=name,created=time.time(),status='PASS',artifact_hashes={file:io.sha(p/'.native-build'/file) for file in (r['card']['artifact'],'game.arcusb','thumb-drive.fat32.img')})
    io.write_json(root/'build/native_projects'/ (name+'.json'),r);return r

def dispatch(kernel,op,args,principal):
    name=args['name'];p=project(kernel.root,name,op!='native.create')
    if op=='native.create':
        r=native_sdk.new(kernel.root,name,kernel.root/'examples');return {**r,'path':p.relative_to(kernel.root).as_posix()+'/game.c'}
    if op=='native.inspect':
        try:r=current(kernel.root,name);state='CURRENT_INPUTS';reason='Current native source, package and FAT image verified.'
        except (ValueError,OSError,KeyError) as exc:r=None;state='BUILD_REQUIRED';reason=str(exc)
        return {'name':name,'path':p.relative_to(kernel.root).as_posix()+'/game.c','state':state,'reason':reason,'build':r,'class':'HOST_SIM','physical_hardware':False}
    if any(tool not in principal.tools for tool in ('native.build','console.lifecycle')):raise ValueError('Native console execution exceeds delegated tools')
    return console_services.open_session(kernel,principal,'sample',current(kernel.root,name))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--project',required=True)
    a=ap.parse_args();print(json.dumps(build(a.root,a.project)))
