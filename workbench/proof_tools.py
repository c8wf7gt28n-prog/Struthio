"""Fixed background tool entry points dispatched by Ledger's existing job runner."""
import argparse, copy, json, os, platform, shutil, subprocess, sys, time
from pathlib import Path
from .hardware_proof import report, bind, sha, BASE, FAULTS, graph
from . import proof_checks as checks

REFERENCE_POWER = 'development/hardware_proof/reference_power_fixture.json'


def execute(argv,cwd,commands,stdin=None,timeout=50):
    start=time.monotonic()
    p=subprocess.run([str(x) for x in argv],cwd=cwd,input=stdin,text=True,capture_output=True,timeout=timeout,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    commands.append(dict(argv=[str(x) for x in argv],cwd=str(cwd),stdin=stdin,exit_status=p.returncode,
        stdout=p.stdout,stderr=p.stderr,duration_seconds=time.monotonic()-start))
    return p


def qualify(root,out):
    r=report(root);commands=[];cases=[];blockers=[];tools={'python':sys.version};results=[]
    def check(id,observed,expected,fixture):
        cases.append(dict(id=id,expected=expected,observed=observed['status'],passed=observed['status']==expected,
            result=observed,fixture=fixture))
    pin=copy.deepcopy(next(f for f in r['findings'] if f['id']=='PIN-01')['details']['package']['fixture'])
    check('pin_known_source_proposal',checks.pins(pin),'VALID',pin)
    for kind in ('duplicate','illegal','bank'):
        mutated=copy.deepcopy(pin)
        if kind=='duplicate':mutated['assignments'][1]['pin']=mutated['assignments'][0]['pin']
        elif kind=='illegal':mutated['assignments'][0]['pin']='999'
        else:mutated['banks'][str(mutated['pads'][mutated['assignments'][0]['pin']]['bank'])]='1V8'
        check('pin_'+kind,checks.pins(mutated),'INVALID',mutated)
    # Checker correctness uses a frozen oracle with a known VALID result; the current design's own status is a
    # finding (PWR-01), not a qualification expectation, so a real design blocker cannot read as a broken checker.
    reference=json.loads((root/REFERENCE_POWER).read_text())
    for model in reference['models']:
        fixture=dict(case=model['case'],limits=model['limits'],allowance_v=0)
        check('dc_positive_ideal_reference_'+model['case']['fpga'],checks.power(**fixture),'VALID',fixture)
        bad=copy.deepcopy(fixture);bad['allowance_v']=.005
        check('dc_insufficient_5mv_reference_'+model['case']['fpga'],checks.power(**bad),'INVALID',bad)
    models=next(f for f in r['findings'] if f['id']=='PWR-01')['details']['models']
    for model in models:
        fixture=dict(case=model['case'],limits=model['limits'],allowance_v=0)
        bad=copy.deepcopy(fixture);bad['allowance_v']=.005
        check('dc_insufficient_5mv_'+model['case']['fpga'],checks.power(**bad),'INVALID',bad)
        bad=copy.deepcopy(fixture);bad['case']['feedback_top_ohm']*=2
        check('dc_overvoltage_'+model['case']['fpga'],checks.power(**bad),'INVALID',bad)
        low=[k for k,v in model['result']['margins_v'].items() if v<=0]
        if low:blockers.append('PWR-01 %s: current dividers leave non-positive ideal DC headroom (%s); design blocker, not a checker fault'
                                % (model['case']['fpga'],', '.join('%s %.3f mV'%(k,model['result']['margins_v'][k]*1000) for k in low)))
    cc=shutil.which('gcc') or shutil.which('clang') or shutil.which('cc')
    binary=out/('power_reference.exe' if os.name=='nt' else 'power_reference')
    if cc:
        v=execute([cc,'--version'],root,commands);tools['C']=v.stdout+v.stderr
        compiled=execute([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror',root/'development/hardware_proof/power_reference.c','-o',binary],root,commands)
        if compiled.returncode==0:
            for prefix,expected_margins in (('independent_C_',lambda m:m['result']['margins_v']),
                                            ('independent_C_reference_',lambda m:m['margins_v'])):
                for model in (models if prefix=='independent_C_' else reference['models']):
                    c=model['case'];l=model['limits'];expect=expected_margins(model)
                    values=[c[k] for k in ('feedback_top_ohm','feedback_bottom_ohm','sense_top_ohm','sense_bottom_ohm')]+[l[k] for k in ('resistor_tolerance','fb_min','fb_max','sense_min','sense_max','hysteresis_max','bias_abs_a','core_min','core_max')]
                    p=execute([binary],root,commands,' '.join(map(str,values))+'\n')
                    observed=json.loads(p.stdout) if p.returncode==0 else {}
                    match=p.returncode==0 and all(abs(observed[k]-v)<1e-12 for k,v in expect.items())
                    results.append(dict(id=prefix+c['fpga'],passed=match,observed=observed,python_decimal=expect,evidence='HOST-TESTED'))
            data=binary.read_bytes();digest=sha(binary)
            for claim,expected in [('HOST_EXECUTABLE','VALID'),('ROM_BOOTABLE','INVALID')]:
                check('artifact_'+claim,checks.boot_artifact(data,claim,digest,digest),expected,
                    dict(path=binary.relative_to(root).as_posix(),sha256=digest,claim=claim))
            check('artifact_corrupt_hash',checks.boot_artifact(data,'HOST_EXECUTABLE','0'*64,digest),'INVALID',dict(path=binary.relative_to(root).as_posix(),sha256='0'*64))
        else:results.append(dict(id='independent_C_compile',passed=False))
        # Execute existing C sources without writing into their protected directories.
        hw=root/BASE;loader=hw/'firmware/d213_flashless_proof/loader';video=hw/'firmware/d213_video_diag'
        cases_c=[('startup_video', [hw/'closure_p9/test_host_sequence.c',loader/'r10_d213_start.c',video/'r10_video_diag.c',video/'r10_video_start.c',video/'r10_adv7513.c'],[loader,video]),
                 ('d213_negative_paths',[loader/'test_r10_d213_start.c',loader/'r10_d213_start.c'],[loader])]
        for name,files,includes in cases_c:
            target=out/(name+('.exe' if os.name=='nt' else ''))
            p=execute([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror',*[f'-I{x}' for x in includes],*files,'-o',target],root,commands)
            ran=execute([target],root,commands) if p.returncode==0 else None
            results.append(dict(id=name,passed=p.returncode==0 and ran.returncode==0,evidence='HOST-TESTED',scope='Actual firmware C linked to host mocks; not target boot'))
        make=shutil.which('make')
        if make:
            v=execute([make,'--version'],root,commands);tools['make']=v.stdout.splitlines()[0]
            p=execute([make,'-C',hw/'firmware/f133_bootloader','test','OUT='+str(out/'boot_tests'),'CC='+cc],root,commands,timeout=90)
            results.append(dict(id='existing_bootloader_negative_paths',passed=p.returncode==0,evidence='HOST-TESTED'))
        else:blockers.append('GNU Make absent: existing F133 bootloader suite not run')
    else:blockers.append('C compiler absent: independent C check and host executable/boot rejection not run')
    # Optional native tools are real invocations or explicit missing-tool records.
    kicad=shutil.which('kicad-cli')
    if kicad:
        tools['kicad-cli']=execute([kicad,'version'],root,commands).stdout.strip()
        for name,args in [('drc',['pcb','drc','--format','json','--output',str(out/'native-drc.json'),str(root/BASE/'cad/ARC1_R10.kicad_pcb')]),
                          ('erc',['sch','erc','--format','json','--output',str(out/'native-erc.json'),str(root/BASE/'cad/ARC1_R10.kicad_sch')])]:
            p=execute([kicad,*args],root,commands)
            blockers.append('Native '+name+' exit '+str(p.returncode)+': inspect current report; no automatic manufacturing signoff')
    else:blockers.append('kicad-cli absent: fresh native ERC/DRC BLOCKED; archived counts remain historical')
    # Use existing bounded RTL fixture command; missing simulator is not a pass.
    if shutil.which('iverilog') and shutil.which('vvp'):
        p=execute([sys.executable,'-m','workbench.qualification_tools','rtl','--root',str(root)],root,commands)
        results.append(dict(id='rtl_qualification_fixture',passed=p.returncode==0,evidence='RTL-SIMULATED',scope='Qualification fixture only, no package or board timing proof'))
    else:blockers.append('Icarus/vvp absent: RTL simulation BLOCKED')
    blockers.append('Exact FPGA vendor implementation/timing and physical board tools are not qualified')
    fault_results={name:graph(r,root,name)['fault'] for name in FAULTS if name!='none'}
    now=bind(root)
    if now!=r['source_hashes']:raise ValueError('Protected/source inputs changed during qualification')
    passed=all(c['passed'] for c in cases) and all(x['passed'] for x in results)
    required_ids={'artifact_ROM_BOOTABLE','pin_duplicate','pin_illegal','pin_bank','dc_insufficient_5mv_F12',
                  'dc_positive_ideal_reference_F12'}
    complete=required_ids<={c['id'] for c in cases} and any(x['id']=='independent_C_F12' and x['passed'] for x in results)
    r.update(status='PASS' if passed and complete else 'BLOCKED' if passed else 'FAIL',
        qualification_scope='Checker correctness and host regressions only; not board feasibility closure',
        cases=cases,independent_checks=results,commands=commands,tool_versions=tools,blockers=blockers,negative_dependency_scenarios=fault_results,
        native_artifacts=[dict(path=p.relative_to(root).as_posix(),sha256=sha(p)) for p in out.rglob('*') if p.is_file() and p.suffix not in ('.json',)])
    return r


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['inspect','qualify','coverage']);p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();out=root/'build/hardware_proof';out.mkdir(parents=True,exist_ok=True);started=time.time()
    try:
        if a.action=='coverage':
            from .hardware_coverage import inspect
            r=inspect(root)
        else:r=qualify(root,out) if a.action=='qualify' else report(root)
    except Exception as exc:r=dict(status='FAIL',error=str(exc),fabrication='HOLD',source_hashes=bind(root))
    r.update(created=started,duration_seconds=time.time()-started,environment={'platform':platform.platform(),'python':sys.version,'physical_hardware':False})
    file=out/(a.action+'.json')
    for index,f in enumerate(r.get('findings',[])):f['run_artifact']=file.relative_to(root).as_posix()+'#/findings/'+str(index)
    file.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r))
    return 1 if r.get('status')=='FAIL' else 3 if r.get('status')=='BLOCKED' else 0

if __name__=='__main__':raise SystemExit(main())
