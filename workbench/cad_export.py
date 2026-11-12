"""Verify a native KiCad export in build/; never overwrite CAD inputs."""
import argparse,json,shutil,subprocess,time
from pathlib import Path
from . import record_io as io,brain_link
from sdk.cli.arc1cli.relations import NetGraph

REPORT='build/links/export.json'


def inputs(root):
    cad=Path(root)/brain_link.BASE/'cad'
    return io.manifest(root,[brain_link.NETLIST,*[p.relative_to(root).as_posix() for p in cad.glob('*.kicad_sch')]])


def topology(graph):
    return {'components':{ref:{k:c[k] for k in ('value','footprint','native_uuid')} for ref,c in graph.components.items()},
        'nets':{name:sorted((p['reference'],p['pin']) for p in net['pins']) for name,net in graph.nets.items()}}


def status(root):
    path=Path(root)/REPORT
    if not path.is_file():path=Path(root)/'project/brain_link_export.json'
    if not path.is_file():return {'state':'UNVERIFIED_EXPORT','reason':'Run registered links.export to compare current native CAD and the saved export.'}
    report=io.load(root,path.relative_to(root).as_posix())
    if report.get('inputs')!=inputs(root):return {'state':'STALE_EXPORT','reason':'Native CAD/export changed since verification.'}
    return {k:report[k] for k in ('state','reason','tool_version') if k in report}


def verify(root):
    root=Path(root).resolve();before=inputs(root);out=root/'build/links';out.mkdir(parents=True,exist_ok=True)
    report={'class':'STATIC_CHECK','created':time.time(),'inputs':before,'state':'BLOCKED','physical_measurements':False,'reason':''}
    command=shutil.which('kicad-cli')
    if command is None:report['reason']='kicad-cli is not installed; native export correspondence is unverified.'
    else:
        try:
            version=subprocess.run([command,'--version'],capture_output=True,text=True,timeout=10)
            report['tool_version']=version.stdout.strip();report['tool_sha256']=io.sha(Path(command).resolve())
            argv=[command,'sch','export','netlist','--format','kicadxml','--output',str(out/'native.xml'),str(root/brain_link.BASE/'cad/ARC1_R10.kicad_sch')]
            p=subprocess.run(argv,capture_output=True,text=True,timeout=90,cwd=root)
            report.update(argv=argv,exit_status=p.returncode,stdout=p.stdout[-4000:],stderr=p.stderr[-4000:])
            if p.returncode:report['reason']='Native KiCad export failed; inspect the recorded diagnostic.'
            elif inputs(root)!=before:report.update(state='STALE_EXPORT',reason='Native inputs changed during export.')
            else:
                actual=topology(NetGraph((out/'native.xml').read_bytes()));saved=topology(NetGraph((root/brain_link.NETLIST).read_bytes()))
                same=actual==saved;report.update(state='VERIFIED_EXPORT' if same else 'EXPORT_MISMATCH',
                    reason='Native component identities and complete pin/net membership '+('match.' if same else 'differ.'),
                    components=len(actual['components']),nets=len(actual['nets']),export_sha256=io.sha(out/'native.xml'))
        except (OSError,ValueError,subprocess.SubprocessError) as exc:report['reason']=str(exc)
    io.write_json(root/REPORT,report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=verify(a.root)
    print(json.dumps(r));raise SystemExit(0 if r['state']=='VERIFIED_EXPORT' else 1)
