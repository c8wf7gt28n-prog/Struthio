"""Owned UNO bridge to native Calc/Writer. No source macros or user code."""
from __future__ import annotations
import base64, hashlib, json, os, re, shutil, socket, subprocess, time
from pathlib import Path
from . import office_runtime
PIN=Path(__file__).resolve().parents[1]/'runtimes/office-uno/runtime.json'


def probe():
    engine=office_runtime.probe();java=shutil.which('java');pin=json.loads(PIN.read_text());jar=PIN.parent/pin['jar']
    valid=jar.is_file() and hashlib.sha256(jar.read_bytes()).hexdigest()==pin['sha256'];version=None;compiler=False
    if java:
        run=subprocess.run([java,'--version'],capture_output=True,text=True,timeout=8)
        version=run.stdout.splitlines()[0] if run.returncode==0 and run.stdout else None
        modules=subprocess.run([java,'--list-modules'],capture_output=True,text=True,timeout=8)
        major=re.search(r'(?:openjdk|java) (\d+)',version or '')
        compiler=bool(major and int(major[1])>=pin['java_minimum'] and modules.returncode==0 and any(line.startswith('jdk.compiler@') for line in modules.stdout.splitlines()))
    return {'available':bool(engine['available'] and java and version and compiler and valid),'engine':engine,'java':java,'source_launcher':compiler,
        'java_version':version,'bridge':pin,'jar_verified':valid,'notice':'Presence is not host qualification.'}


def run_owned(stage,operation,source,target,data,result,pdf=None,cancelled=None):
    info=probe()
    if not info['available']:raise ValueError('OFFICE_UNO_PREREQUISITES_MISSING: LibreOffice and Java 17 or newer are required')
    stage=Path(stage).resolve();stage.mkdir(parents=True,exist_ok=False);uri=office_runtime.profile(stage/'profile')
    environment={**os.environ,'LANG':'C.UTF-8','FONTCONFIG_FILE':str(office_runtime.font_config(stage/'fonts'))}
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=[info['engine']['executable'],'-env:UserInstallation='+uri,'--headless','--nologo','--nodefault','--norestore',
        '--nofirststartwizard','--accept=socket,host=127.0.0.1,port='+str(port)+',tcpNoDelay=1;urp;StarOffice.ServiceManager']
    helper=Path(__file__).with_name('LedgerOffice.java');jar=PIN.parent/info['bridge']['jar']
    client=[info['java'],'-Xmx256m','-cp',str(jar),str(helper),str(port),operation,Path(source).resolve().as_uri(),
        Path(target).resolve().as_uri(),str(Path(data).resolve()),str(Path(result).resolve()),Path(pdf).resolve().as_uri() if pdf else '']
    started=time.monotonic();processes=[]
    with (stage/'stdout.log').open('wb') as stdout,(stage/'stderr.log').open('wb') as stderr:
        try:
            # Keep both children in the Kernel tool's process group for Stop.
            processes.append(subprocess.Popen(server,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,env=environment))
            processes.append(subprocess.Popen(client,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,env=environment))
            while processes[1].poll() is None:
                if (cancelled and cancelled()) or time.monotonic()-started>90:raise ValueError('OFFICE_CANCELLED_OR_TIME_LIMIT')
                time.sleep(.04)
            if processes[1].returncode:raise ValueError('OFFICE_UNO_OPERATION_FAILED: '+(stage/'stderr.log').read_text(errors='replace')[-1200:])
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=2)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
    if not all(Path(p).is_file() and 0<Path(p).stat().st_size<=32*1024*1024 for p in [target,result]+([pdf] if pdf else [])):
        raise ValueError('OFFICE_UNO_OUTPUT_INCOMPLETE')
    if probe()!=info:raise ValueError('OFFICE_ENGINE_OR_BRIDGE_CHANGED')
    return {'engine':info['engine'],'java_version':info['java_version'],'bridge_sha256':info['bridge']['sha256'],
        'helper_sha256':hashlib.sha256(helper.read_bytes()).hexdigest(),'isolated_profile':True,
        'source_document_macros':'NEVER_EXECUTE','external_updates':'NO_UPDATE','native_operation':operation,
        'process_outcome':'COMPLETED','elapsed_seconds':time.monotonic()-started}


def calculate(source,target,stage,cells,outputs,cancelled=None):
    from .math_units import number_record,rational
    stage=Path(stage);data=stage.parent/'calc_cells.tsv';result=stage.parent/'calc_measurements.tsv';lines=[]
    for address,cell in cells.items():
        value=cell['value']
        if cell['kind']=='number':
            exact=rational(value)
            if abs(exact)>10**15:raise ValueError('OFFICE_NUMERIC_PRECISION_PROFILE_BOUND')
            value=number_record(exact)['decimal']
        lines.append(address+'\t'+cell['kind']+'\t'+base64.b64encode(value.encode()).decode())
    for address in outputs:lines.append(address+'\tOUTPUT\t')
    data.write_text('\n'.join(lines)+'\n');runtime=run_owned(stage,'CALC',source,target,data,result,cancelled=cancelled);rows=[]
    for line in result.read_text().splitlines():
        fields=line.split('\t')
        if len(fields)!=5:raise ValueError('OFFICE_MEASUREMENT_NOT_PARSED')
        phase,address,formula,value,error=fields;rows.append({'phase':phase,'cell':address,'formula':formula,'value':value,'error':error})
    return runtime,rows


def writer(source,target,pdf,stage,paragraph,cancelled=None):
    stage=Path(stage);data=stage.parent/'writer_append.txt';result=stage.parent/'writer_text.txt';data.write_text(paragraph)
    runtime=run_owned(stage,'WRITER',source,target,data,result,pdf,cancelled);return runtime,result.read_text()
