"""Registered malformed-command reproducer against the actual compiled host."""
import argparse,json,subprocess,time
from pathlib import Path
from . import arcos_tools,record_io as io
from . import locations

FIXTURE='tests/fixtures/arcos_host_commands.json'


def probe(root):
    root=Path(root).resolve();out=root/'build/arcos';out.mkdir(parents=True,exist_ok=True)
    # Compile the actual host through the existing ARC-OS build path.
    import contextlib,io as streams
    with contextlib.redirect_stdout(streams.StringIO()):code=arcos_tools.run(root,'build')
    if code:raise ValueError('ARC-OS build failed before command probing')
    inputs={**arcos_tools.sources(root),FIXTURE:io.sha(root/FIXTURE),'workbench/host_parser.py':io.sha(locations.program(root)/'workbench/host_parser.py')}
    report={'schema':'arc.arcos-command-probe/1','created':time.time(),'class':'HOST_SIM','source_inputs':inputs,'cases':[],
        'physical_hardware':False,'source_path':'software/arcos/src/host.c','source_sha256':io.sha(root/'software/arcos/src/host.c')}
    for case in io.load(root,FIXTURE)['cases']:
        command=case['command'];raw=(command+'\ndiagnostics\nquit\n').encode()
        process=subprocess.run([str(out/'arc_os_host')],input=raw,capture_output=True,timeout=5)
        try:frames=[json.loads(line) for line in process.stdout.decode().splitlines()]
        except (ValueError,UnicodeError):frames=[]
        observed=frames[1] if len(frames)>=3 else None
        if case['expected']=='VALID':
            passed=observed is not None and observed['error'] not in ('INVALID_COMMAND','INVALID_CONTROLLER')
        else:
            passed=observed is not None and observed['error']==case['expected'] and observed['tick']==frames[0]['tick']
        passed=passed and process.returncode==0
        report['cases'].append({'id':case['id'],'expected':case['expected'],'passed':bool(passed),
            'observed_error':observed['error'] if observed else 'HOST_EXITED_OR_BAD_FRAME',
            'observed_tick':observed['tick'] if observed else None,'frame_count':len(frames)})
    report['status']='PASS' if all(c['passed'] for c in report['cases']) else 'FAIL'
    report['passed']=sum(c['passed'] for c in report['cases']);report['total']=len(report['cases'])
    io.write_json(out/'command-parser.json',report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    result=probe(a.root);print(json.dumps(result));raise SystemExit(0 if result['status']=='PASS' else 1)
