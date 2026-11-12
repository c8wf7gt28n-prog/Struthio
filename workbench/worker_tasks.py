"""Standalone data-only parser/check and one-shot native model tasks.

Runs in a private filesystem/PID/network namespace and capped cgroup. It has no
Ledger database, host endpoint, user HOME, grant, source writable mount or keys.
"""
import ast
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from urllib.request import Request, ProxyHandler, build_opener
sys.path.insert(0,str(Path(__file__).resolve().parent))


def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def table(raw,suffix):
    text=raw.decode('utf-8-sig'); rows=list(csv.reader(io.StringIO(text,newline=''),delimiter='\t' if suffix=='.tsv' else ','))
    if sum(len(r) for r in rows)>200000:raise ValueError('Table cell limit')
    return rows


def inspect_one(name,raw):
    suffix=Path(name).suffix.casefold(); result={'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    if suffix=='.json':
        json.loads(raw);result.update(kind='JSON',check='PARSE_ONLY')
    elif suffix in ('.csv','.tsv'):
        rows=table(raw,suffix);result.update(kind='TABLE',rows=len(rows),columns=max((len(r) for r in rows),default=0))
    elif suffix=='.xlsx':
        from cell_edits import describe
        result.update(kind='SIMPLE_XLSX',**describe(raw,suffix))
    elif suffix=='.gguf':
        # Header inspection is explicitly not a full tensor/model qualification.
        if raw[:4]!=b'GGUF' or len(raw)<24:raise ValueError('Invalid GGUF header')
        result.update(kind='GGUF_HEADER_ONLY',version=int.from_bytes(raw[4:8],'little'))
    else:
        text=raw.decode('utf-8')
        if '\x00' in text:raise ValueError('Opaque format; use its native application')
        result.update(kind='UTF8_TEXT',characters=len(text))
    return result


def data_task(request,check=False):
    results=[]
    for item in request['files']:
        raw=Path('/inputs/'+item['input']).read_bytes()
        if len(raw)>16*1024*1024 or hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('Input identity/size changed')
        name=item['path']; kind=request.get('check')
        if check and kind=='PYTHON':
            ast.parse(raw); result={'path':name,'check':'PYTHON_PARSE_NO_EXECUTION','passed':True}
        elif check and kind=='PARTS':
            rows=table(raw,Path(name).suffix.casefold())
            if not rows or not {'Part','Need','Have'}<=set(rows[0]):raise ValueError('Parts table needs Part, Need and Have columns')
            from decimal import Decimal, InvalidOperation
            indexes={k:rows[0].index(k) for k in ('Part','Need','Have')};shortages=[]
            for row in rows[1:]:
                if not row:continue
                if len(row)<=max(indexes.values()):raise ValueError('Short parts row')
                need=Decimal(row[indexes['Need']]);have=Decimal(row[indexes['Have']])
                if not need.is_finite() or not have.is_finite() or min(need,have)<0:raise ValueError('Parts amounts must be finite and nonnegative')
                if need>have:shortages.append({'part':row[indexes['Part']],'shortage':str(need-have)})
            result={'path':name,'check':'PARTS_COUNTS_NO_ENGINEERING_PROOF','passed':not shortages,'shortages':shortages}
        else:
            result=inspect_one(name,raw)
            if check:
                expected={'JSON':'JSON','TABLE':'TABLE','TEXT':'UTF8_TEXT'}[kind]
                if result['kind']!=expected:raise ValueError('File is outside the selected check format')
                result.update(check=kind+'_PARSE_ONLY',passed=True)
        results.append(result)
    return {'checks':results,'passed':all(r.get('passed',True) for r in results),'execution':'DATA_PARSE_ONLY_NO_PROJECT_CODE_EXECUTION'}


def model_task(request):
    # Loopback exists only inside this worker's private network namespace.
    port=18719; key=Path('/scratch/key');key.write_text(os.urandom(24).hex());key.chmod(0o600)
    argv=['/runtime/'+request['executable'],'--model','/weights/'+request['weights'],'--host','127.0.0.1','--port',str(port),
        '--api-key-file',str(key),'--ctx-size',str(request['context']),'--threads',str(request['threads']),'-ngl','0','--parallel','1',
        '--threads-http','1','--batch-size','128','--ubatch-size','64','--cache-ram','0','--ctx-checkpoints','0',
        '--no-cache-idle-slots','--fit','off','--no-webui','--no-ui-mcp-proxy','--no-slots','--no-context-shift','--no-warmup']
    began=time.monotonic();token=key.read_text();opener=build_opener(ProxyHandler({}))
    def call(path,payload=None,timeout=5):
        body=json.dumps(payload).encode() if payload is not None else None
        req=Request('http://127.0.0.1:'+str(port)+path,data=body,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with opener.open(req,timeout=timeout) as response:
            raw=response.read(2097153)
            if len(raw)>2097152:raise ValueError('Model response limit')
            return json.loads(raw)
    with Path('/scratch/native.log').open('wb') as log:
        server=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        try:
            until=time.monotonic()+min(90,request['seconds']*.6)
            while time.monotonic()<until:
                if server.poll() is not None:raise ValueError('Native worker exited during model load')
                try:
                    if call('/health',timeout=.3).get('status')=='ok':break
                except Exception:time.sleep(.05)
            else:raise ValueError('Model load timeout')
            load=time.monotonic()-began
            messages=request['messages'];options={'enable_thinking':False}
            prompt=call('/apply-template',{'messages':messages,'add_generation_prompt':True,'chat_template_kwargs':options})['prompt']
            count=len(call('/tokenize',{'content':prompt,'add_special':False})['tokens'])
            if count+request['max_tokens']+32>request['context']:raise ValueError('Model context budget exceeded; bases were not clipped')
            start=time.monotonic()
            answer=call('/v1/chat/completions',{'messages':messages,'max_tokens':request['max_tokens'],'temperature':0,'stream':False,
                'cache_prompt':False,'chat_template_kwargs':options,'response_format':{'type':'json_schema',
                'json_schema':{'name':'ledger_changes','strict':True,'schema':request['output_schema']}}},timeout=max(1,request['seconds']-(time.monotonic()-began)))
            choice=answer['choices'][0]
            if choice.get('finish_reason')!='stop':raise ValueError('Incomplete model output')
            text=choice['message'].get('content')
            if not isinstance(text,str) or len(text)>65536:raise ValueError('Model output type/size')
            return {'candidate':json.loads(text),'finish_reason':'stop','prompt_tokens_measured':count,'usage':answer.get('usage',{}),
                'load_seconds':load,'generation_seconds':time.monotonic()-start,'native_executable':'PINNED_CPU_SERVER',
                'context':request['context'],'max_tokens':request['max_tokens']}
        finally:
            if server.poll() is None:server.kill()
            server.wait(timeout=3)


def probe(request):
    mode=request['mode']
    if mode=='boundary':
        checks={}
        def denied(fn):
            try:fn();return False
            except OSError:return True
        checks['outside_read_denied']=denied(lambda:Path(request['outside']).read_bytes())
        checks['outside_write_denied']=denied(lambda:Path(request['outside']).write_text('forbidden'))
        checks['input_write_denied']=denied(lambda:Path('/inputs/read.txt').write_text('forbidden'))
        checks['input_read_allowed']=Path('/inputs/read.txt').read_text()=='admitted'
        Path('/scratch/result').write_text('scratch');checks['scratch_write_allowed']=True
        for kind,expected in request['namespaces'].items():checks[kind+'_namespace_private']=os.readlink('/proc/self/ns/'+kind)!=expected
        status=Path('/proc/self/status').read_text();checks['no_new_privs']='NoNewPrivs:\t1' in status
        checks['capabilities_dropped']='CapEff:\t0000000000000000' in status
        try:
            with socket.create_connection(('127.0.0.1',request['tcp']),timeout=.3):checks['host_tcp_denied']=False
        except OSError:checks['host_tcp_denied']=True
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
            udp.sendto(b'ledger-worker-probe',('127.0.0.1',request['udp']))
        return {'checks':checks}
    if mode=='tasks':
        children=[];denied=False
        try:
            for _ in range(24):
                try:pid=os.fork()
                except OSError:denied=True;break
                if pid==0:time.sleep(4);os._exit(0)
                children.append(pid)
        finally:
            # Keep the hit cgroup observable long enough for the broker's poll.
            if denied:time.sleep(.3)
            for pid in children:
                try:os.kill(pid,signal.SIGKILL)
                except ProcessLookupError:pass
            for pid in children:os.waitpid(pid,0)
        return {'task_limit_observed':denied,'children_created':len(children)}
    if mode=='memory':
        code='import time; x=bytearray(60*1024*1024); time.sleep(4)'
        children=[subprocess.Popen(['/usr/bin/python3','-I','-S','-c',code]) for _ in range(2)]
        for child in children:child.wait()
        return {'unexpected_survival':True}
    if mode=='termination':
        pid=os.fork()
        if pid==0:os.setsid();time.sleep(20);os._exit(0)
        print('LEDGER_DESCENDANT_STARTED',flush=True);time.sleep(20)
    if mode=='version':
        child=subprocess.run(['/runtime/'+request['executable'],'--version'],capture_output=True,text=True,timeout=8)
        return {'exit':child.returncode,'version':(child.stdout+child.stderr)[:1000]}
    raise ValueError('Unknown probe')


def main():
    mode=sys.argv[1];request=json.loads(Path('/inputs/request.json').read_text())
    try:
        value=model_task(request) if mode=='model' else probe(request) if mode=='probe' else data_task(request,mode=='check')
        print(canonical({'ok':True,'result':value}),flush=True)
    except Exception as exc:
        # Input errors are bounded; there is no host-path/log/credential reflection.
        print(canonical({'ok':False,'error':type(exc).__name__+': '+str(exc)[:300]}),flush=True);raise SystemExit(2)


if __name__=='__main__':main()
