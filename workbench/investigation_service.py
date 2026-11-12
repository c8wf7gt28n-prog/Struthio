"""Frozen, owner-authorized engineering cases in the shared Kernel.

Results are ordinary Kernel artifacts, not a second evidence authority. Source
interpretations, controlled regression cases and physical acceptance differ.
"""
from __future__ import annotations
import argparse, hashlib, os, subprocess, time, uuid
from pathlib import Path
from sdk.cli.arc1cli import engineering_cases as c,record_store as records,knowledge_sources as sources
from . import evidence_compiler as packets,engineering_map as maps,knowledge_service as connections,hdl_tools as hdl,intake_service as intake,memory_service as memory,record_io,activity

ID=intake.ID;SHA=intake.SHA
VARIATION={'type':'object','additionalProperties':False,'properties':{'clock_hz':{'type':'integer','minimum':40000000,'maximum':50000000},'length':{'type':'integer','minimum':64,'maximum':256},'address':{'type':'integer','minimum':0,'maximum':4096}},'required':['clock_hz','length','address']}
PROPS={'packet':ID,'expected_context':SHA,'method':SHA,'case':{'type':'string','enum':['PSRAM_TCEM','USB_MUX']},'variation':VARIATION,'assumed_direct_controller':maps.REF}
REQUIRED=['packet','expected_context','method','case']
OPTIONS={'type':'object','additionalProperties':False,'properties':PROPS,'required':REQUIRED}
FIELDS={'knowledge.investigation.methods':({},[]),'knowledge.investigation.run':({**PROPS,'request_key':intake.TEXT},REQUIRED),
 'knowledge.investigation.list':({},[]),'knowledge.investigation.result':({'job':ID},['job']),
 'knowledge.investigation.export':({'job':ID,'destination':intake.TEXT},['job','destination'])}
SCOPES={op:'approve' if op in ('knowledge.investigation.run','knowledge.investigation.export') else 'read' for op in FIELDS}
JOB_TOOLS={'knowledge.investigate'}
def fingerprint():return hashlib.sha256(Path(__file__).read_bytes()+c.fingerprint().encode()+Path(hdl.__file__).read_bytes()).hexdigest()
def current_packet(kernel,opts,owner):
    p=packets.get(kernel,opts['packet'],owner)
    if p['state']!='CURRENT' or p['context_digest']!=opts['expected_context']:raise ValueError('CASE_PACKET_STALE_OR_CONTEXT_CHANGED')
    return p
def authorize_job(kernel,tool,opts,principal):
    if tool not in JOB_TOOLS or not {'read','execute','approve'}<=principal.scopes:raise ValueError('CASE_REQUIRES_OWNER_READ_EXECUTE_AND_APPROVE')
    from .agent_operations import validate
    validate(opts,OPTIONS)
    if set(opts)-set(PROPS) or not set(REQUIRED)<=set(opts):raise ValueError('CASE_OPTIONS')
    if opts['method']!=fingerprint():raise ValueError('CASE_METHOD_CHANGED_REVIEW_REQUIRED')
    if 'variation' in opts:c.variation(opts['variation'])
    if opts['case']=='USB_MUX' and 'variation' in opts or opts['case']=='PSRAM_TCEM' and 'assumed_direct_controller' in opts:raise ValueError('CASE_OPTIONS_BELONG_TO_ANOTHER_PROFILE')
    value=current_packet(kernel,opts,principal.identity)
    if opts['case']=='PSRAM_TCEM' and value['context']['scope']['mpn']!='APS3204L-3SQNA-SN':raise ValueError('CASE_PSRAM_EXACT_PART_REQUIRED')
def tool_pin(tool):
    if tool['state']!='DETECTED':raise ValueError('CASE_ICARUS_NOT_AVAILABLE_INSTALL_SEPARATELY')
    deps=hdl.dependencies(tool);data=Path(tool['data_directory'])
    rows=[]
    for name,row in deps.items():
        path=Path(name);label='data/'+path.relative_to(data).as_posix() if path.is_relative_to(data) else 'bin/'+path.name
        rows.append({'file':label,**row})
    version=subprocess.run([tool['executable'],'-B',tool['data_directory'],'-V'],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=5)
    if version.returncode or len(version.stdout)+len(version.stderr)>32000:raise ValueError('CASE_HDL_VERSION_UNAVAILABLE')
    first=version.stdout.splitlines()[0] if version.stdout.splitlines() else ''
    if not first.startswith('Icarus Verilog version '):raise ValueError('CASE_HDL_VERSION_PROFILE_UNSUPPORTED')
    return {'engine':'Icarus Verilog','version':first[:150],'files':sorted(rows,key=lambda x:x['file']),'sha256':c.digest(sorted(rows,key=lambda x:x['file']))}
def source(path,raw,needle,before=2,after=3):
    value=c.locate(path,raw,needle,before,after);value['id']=c.digest(value);value['authority']='PRESERVED_REFERENCE_SOURCE_NOT_ACCEPTED_CURRENT_PROJECT';return value
def original_pages(kernel,job,rom,record_id):
    out=[]
    for index in (0,5,25,26):
        connections.check(kernel,job);out.append(connections.original_page(kernel,job,{'id':rom['id'],'record_id':record_id,'page_index':index,'render':False}))
    return out
def simulate(kernel,job,content,out,v,check):
    tool=hdl.discover('icarus');pin=tool_pin(tool)
    for name in (c.CORE,c.MODEL):c.safe_hdl(content[name].decode('utf-8-sig'))
    snapshot=out/'inputs';snapshot.mkdir(parents=True)
    core=snapshot/'controller.sv';model=snapshot/'device_model.sv';core.write_bytes(content[c.CORE]);model.write_bytes(content[c.MODEL]);results=[]
    # Freeze all expected oracle outcomes before starting any experiment.
    experiment={'schema':'arc.case-oracle/1','method':fingerprint(),'variation':v,'matrix':[
      {'name':'loose_controller_loose_oracle','controller_ns':8000,'oracle_ns':8000,'expected':'PASS'},
      {'name':'loose_controller_applicable_oracle','controller_ns':8000,'oracle_ns':3000,'expected':'FAIL'},
      {'name':'strict_controller_applicable_oracle','controller_ns':3000,'oracle_ns':3000,'expected':'PASS'}],
      'scope':'CONTROLLED_REGRESSION_CASE_NOT_A_RECONSTRUCTION_OF_UNAVAILABLE_OLD_REVISION'}
    records.atomic(out/'frozen_oracle.json',records.canonical(experiment))
    for test in experiment['matrix']:
        check();dest=out/test['name'];dest.mkdir();tb=dest/'case.sv';tb.write_text(c.testbench(test['controller_ns'],test['oracle_ns'],v));env=hdl.environment(tool,dest)
        compiled=hdl.invoke_compile(tool,[str(core),str(model),str(tb)],'ledger_psram_case',dest,env);check()
        if compiled['exit_status']!=0:raise ValueError('CASE_NATIVE_HDL_COMPILE_FAILED')
        ran=hdl.invoke_model(tool,dest,'ledger_psram_case',env);check();text=ran['stdout']
        oracle=c.pulse_oracle(text,test['oracle_ns'])
        expected_exit=0 if test['expected']=='PASS' else 1
        matches=oracle['state']==test['expected'] and ran['exit_status']==expected_exit and oracle['written_bytes']==v['length']
        results.append({**test,'oracle':oracle,'matches_frozen_expectation':matches,'native_exit_status':ran['exit_status'],'seconds':round(ran['duration_seconds'],6),
          'testbench_sha256':records.sha(tb),'compile_log':(dest/'stdout.txt').relative_to(kernel.root).as_posix(),'run_log':(dest/'run/stdout.txt').relative_to(kernel.root).as_posix()})
    if tool_pin(hdl.discover('icarus'))!=pin:raise ValueError('CASE_HDL_TOOL_CHANGED_DURING_INVESTIGATION')
    if not all(x['matches_frozen_expectation'] for x in results):raise ValueError('CASE_FROZEN_ORACLE_EXPECTATION_NOT_MET')
    return results,pin,experiment
def run(kernel,job):
    opts=job['request_spec']['investigation'];owner=job['owner'];check=lambda:connections.check(kernel,job);check()
    if opts['method']!=fingerprint():raise ValueError('CASE_METHOD_CHANGED_BEFORE_RUN')
    p=current_packet(kernel,opts,owner);ctx=p['context'];mapid=ctx['scope']['map']
    with kernel.db() as db:row=maps.load(db,owner,mapid)
    baseline,rom,graph=maps.fresh(kernel,row);content,manifest,_=maps.core.read_archive(baseline['path'],baseline['report'],check)
    out=kernel.root/'build/investigations/runs'/job['id'];out.mkdir(parents=True,exist_ok=True)
    excerpts=[];pages=[];tool=None;results=[];frozen=None
    if opts['case']=='PSRAM_TCEM':
        if ctx['scope']['mpn']!='APS3204L-3SQNA-SN' or not any(x['record_id']==c.DOC for x in maps.core.document_candidates(graph['components'][ctx['scope']['component']],sources.header(rom['path'],rom['report']['manifest_sha256'])[1]['records'])):raise ValueError('CASE_VENDOR_SOURCE_NOT_ASSOCIATED')
        pages=original_pages(kernel,job,rom,c.DOC);limits=c.vendor_limits(pages,ctx['scope']['mpn']);parameters=c.parameters(content[c.TOP].decode('utf-8-sig'))
        if parameters['CLK_DIV']!=1 or parameters['BUF_BYTES']!=256:raise ValueError('CASE_CURRENT_WRAPPER_PROFILE_UNSUPPORTED')
        v=opts.get('variation',{'clock_hz':parameters['MCLK_HZ'],'length':256,'address':900});c.variation(v)
        excerpts=[source(c.TOP,content[c.TOP],'.TCEM_NS(',2,9),source(c.CORE,content[c.CORE],'parameter integer TCEM_NS',4,3),source(c.CORE,content[c.CORE],'localparam integer TCEM_CYC',3,8),source(c.BENCH,content[c.BENCH],'.TCEM_NS(',2,2),source(c.MODEL,content[c.MODEL],'module aps6404l_model_r07',0,8)]
        results,tool,frozen=simulate(kernel,job,content,out,v,check)
        selected=parameters['TCEM_NS'];status='ALREADY_CONFIGURED_FOR_STRICT_LIMIT' if selected==3000 else 'CURRENT_WRAPPER_REQUIRES_REVIEW'
        summary='The preserved wrapper already selects 3,000 ns. A controlled loose-limit case passes at 8,000 ns and fails at the applicable 3,000 ns oracle; the strict case passes.' if selected==3000 else 'The preserved wrapper does not select the strict 3,000 ns case profile. Review applicability before proposing a source change.'
        conclusion={'state':status,'summary':summary,'native_wrapper_parameters':parameters,'simulation_parameters':v,'source_limits':limits,'automatic_fix':'NONE',
          'case_outcome':'FROZEN_ORACLE_MATRIX_CONFIRMED','controller_assessment':'CONDITIONAL_HOST_CORE_TIMING_CASE_ONLY','variant_applicability':'SOURCE_INTERPRETATION_PENDING_INDEPENDENT_REVIEW'}
        gaps=['PHYSICAL_FITTED_GRADE_AND_OPERATING_POINT_UNVERIFIED','CURRENT_NATIVE_PROJECT_AND_WRAPPER_ELABORATION_NOT_ACCEPTED','APS6404L_64MBIT_BEHAVIORAL_MODEL_STANDS_IN_FOR_APS3204L_32MBIT_DEVICE','COMMAND_COMPATIBILITY_CAPACITY_AND_PAD_TIMING_REQUIRE_SEPARATE_QUALIFICATION','CONTROLLED_PARAMETER_REGRESSION_NOT_EXACT_OLD_REVISION_REPLAY','WRITES_AND_INITIALIZATION_EXERCISED_READ_DATA_AND_FULL_SYSTEM_NOT_QUALIFIED','INDEPENDENT_CASE_REVIEW_OPEN','PHYSICAL_QUALIFICATION_HOLD']
        citations=[x['id'] for x in excerpts]+[c.digest({'record_id':x['record_id'],'sha256':x['source_sha256'],'page_index':x['page_index']}) for x in pages]
    else:
        part=graph['components'][ctx['scope']['component']];pin=next((x for x in part['pins'] if x['net']=='USBMUX_SEL'),None)
        if pin is None:raise ValueError('CASE_NATIVE_MUX_SELECTOR_NOT_ON_SELECTED_PART')
        endpoints=[x for component in graph['components'].values() for x in component['pins'] if x['net']=='USBMUX_SEL']
        searched={n:raw for n,raw in content.items() if n.startswith(c.ROOT) and n.endswith(('.c','.h'))};classification=c.usb_classification(endpoints,[raw.decode('utf-8-sig') for raw in searched.values()],opts.get('assumed_direct_controller','U20'))
        excerpts=[source(c.LOADER,content[c.LOADER],'if (o->request_internal_mux',3,6),source(c.LOADER,content[c.LOADER],'successful callback cannot',1,6),source(c.HEADER,content[c.HEADER],'Nonzero means true',0,5),source(c.HEADER,content[c.HEADER],'int (*request_internal_mux)',1,4)]
        native={'id':c.digest({'map':mapid,'revision':maps.revision(row),'net':'USBMUX_SEL'}),'authority':'NATIVE_NET_MEMBERSHIP_NOT_SIGNAL_DIRECTION','locator':{'map':mapid,'map_artifact':row['artifact'],'map_sha256':row['graph_sha256'],'net':'USBMUX_SEL'},'endpoints':[{'reference':x['reference'],'pin':x['pin'],'state':x['state'],'pad_uuids':x['pad_uuids']} for x in endpoints]}
        conclusion={**classification,'summary':'Native USBMUX_SEL has '+', '.join(x['reference']+'.'+x['pin'] for x in native['endpoints'])+'. The loader requests and observes the mux through callbacks; its physical board adapter remains unresolved.','native':native,
          'searched_source_manifest':{n:manifest[n] for n in sorted(searched)},'searched_scope':'PRESERVED_R10_C_AND_H_FILES_ONLY'}
        gaps=['BOARD_ADAPTER_GPIO_PIN_AND_POLARITY_NOT_BOUND_TO_NATIVE_NET','INDIRECT_CONTROL_PATH_OR_DRIVER_NOT_PROVEN_BY_NET_MEMBERSHIP','CALLBACK_SUCCESS_NOT_PHYSICAL_MUX_OR_EXTERNAL_HOST_ISOLATION','HISTORICAL_HARD_CODED_GPIO_DEFECT_NOT_ESTABLISHED_IN_REVIEWED_CURRENT_LOADER','INDEPENDENT_CASE_REVIEW_OPEN','PHYSICAL_QUALIFICATION_HOLD'];citations=[native['id'],*[x['id'] for x in excerpts]]
    report={'schema':c.VERSION,'job':job['id'],'case':opts['case'],'method':opts['method'],'request_digest':c.digest(opts),'packet':p['id'],'context_digest':p['context_digest'],'map':mapid,'view_revision':maps.revision(row),
      'state':'INVESTIGATION_RECORDED','conclusion':conclusion,'citations':citations,'source_excerpts':excerpts,'original_pages':[{'id':c.digest({'record_id':x['record_id'],'sha256':x['source_sha256'],'page_index':x['page_index']}),**{k:x[k] for k in ('record_id','source_sha256','page_index','page_label','locator','text')}} for x in pages],
      'experiments':results,'frozen_oracle':frozen,'tool_pin':tool,'gaps':gaps,'review':'INDEPENDENT_REVIEW_OPEN','model_calls':0,'network_calls':0,'physical_qualification':False,'source_changes':[]}
    if len(records.canonical(report))>128*1024:raise ValueError('CASE_REPORT_BUDGET')
    # Repeat the complete packet authority check after native tools and source reads.
    check();current_packet(kernel,opts,owner)
    with kernel.db() as db:live=maps.load(db,owner,mapid)
    maps.fresh(kernel,live)
    if maps.revision(live)!=report['view_revision']:raise ValueError('CASE_SCOPE_CHANGED_DURING_INVESTIGATION')
    for page in pages:sources.original(rom['path'],rom['report'],page['record_id'])
    records.atomic(out/'report.json',records.canonical(report));check()
    with kernel.db() as db:activity.append(db,activity.make_event(owner,'knowledge.investigation','BOUNDED_CASE_RECORDED'))
    return {'state':'INVESTIGATION_RECORDED','case':opts['case'],'report':(out/'report.json').relative_to(kernel.root).as_posix(),'summary':report['conclusion']['summary'],'review':'INDEPENDENT_REVIEW_OPEN','model_calls':0,'source_changes':[],'physical_qualification':False}
def get(kernel,ident,owner):
    job=kernel.record('jobs',ident)
    if job['owner']!=owner or job['tool'] not in JOB_TOOLS:raise ValueError('PRIVATE_INVESTIGATION_NOT_FOUND')
    try:
        _,ev,a,path=maps.artifact(kernel,ident,'build/investigations/runs/'+ident+'/report.json');report=records.load(path);opts=job['request_spec']['investigation']
        if report['job']!=ident or report['method']!=fingerprint() or report['method']!=opts['method'] or report['case']!=opts['case'] or report['packet']!=opts['packet'] or report['request_digest']!=c.digest(opts):raise ValueError('CASE_REPORT_BINDING_CHANGED')
        p=current_packet(kernel,opts,owner)
        if p['context_digest']!=report['context_digest']:raise ValueError('CASE_PACKET_CONTEXT_CHANGED')
        for artifact in ev['artifacts']:maps.artifact(kernel,ident,artifact['path'],artifact['sha256'])
        if report['tool_pin'] is not None and tool_pin(hdl.discover('icarus'))!=report['tool_pin']:raise ValueError('CASE_TOOL_PIN_CHANGED_REQUALIFY')
        with kernel.db() as db:row=maps.load(db,owner,report['map'])
        _,rom,_=maps.fresh(kernel,row)
        for page in report['original_pages']:
            _,original=sources.original(rom['path'],rom['report'],page['record_id'])
            if original['sha256']!=page['source_sha256']:raise ValueError('CASE_ADDITIONAL_ORIGINAL_CHANGED')
        current_packet(kernel,opts,owner)
        return {'state':'AVAILABLE','job':ident,'report':report}
    except (ValueError,OSError,KeyError,TypeError) as exc:return {'state':'STALE_OR_UNAVAILABLE','job':ident,'report':None,'reason':activity.redact(exc),'physical_qualification':False}
def dispatch(kernel,op,args,principal):
    if op=='knowledge.investigation.methods':return {'schema':c.VERSION,'method':fingerprint(),'profiles':['PSRAM_TCEM','USB_MUX'],'icarus':hdl.discover('icarus')['state'],'effects':'OWNER_APPROVED_BOUNDED_HOST_SIM_OR_STATIC_SOURCE_INVESTIGATION','review':'INDEPENDENT_REVIEW_OPEN','physical_qualification':False}
    if op=='knowledge.investigation.run':return kernel.submit({'tool':'knowledge.investigate','investigation':{k:v for k,v in args.items() if k!='request_key'},'request_key':args.get('request_key',uuid.uuid4().hex),'timeout':600},principal)
    if 'read' not in principal.scopes:raise ValueError('CASE_READ_SCOPE_REQUIRED')
    if op=='knowledge.investigation.list':return {'jobs':[{'id':j['id'],'case':j['request_spec']['investigation']['case'],'state':j['state']} for j in kernel.listing('jobs') if j['owner']==principal.identity and j['tool'] in JOB_TOOLS]}
    value=get(kernel,args['job'],principal.identity)
    if op=='knowledge.investigation.result':return value
    if op=='knowledge.investigation.export':
        if value['state']!='AVAILABLE':raise ValueError('CASE_STALE_OR_UNAVAILABLE')
        path=memory.fresh_destination(kernel,args['destination'],'.json');raw=records.canonical(value)
        if get(kernel,args['job'],principal.identity)['state']!='AVAILABLE':raise ValueError('CASE_CHANGED_BEFORE_EXPORT')
        memory.publish(path,raw)
        return {'state':'EXPORTED','path':str(path),'bytes':len(raw),'cloud_disclosure':'NOT_GRANTED'}
    raise ValueError('CASE_OPERATION_UNKNOWN')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--job',required=True);args=parser.parse_args()
    if os.name!='nt':
        import resource
        resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(90,95));resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024**2,8*1024**2))
    from .engineering_kernel import Kernel
    kernel=Kernel(args.root);job=kernel.record('jobs',args.job)
    try:result=run(kernel,job);code=0
    except Exception as exc:result={'state':'FAILED','reason':activity.redact(exc)};code=1
    result.update(schema='arc.investigation-job-result/1',created=time.time(),job_id=job['id'],network_calls=0);result['class']='HOST_SIM' if job['request_spec']['investigation']['case']=='PSRAM_TCEM' else 'STATIC_CHECK'
    record_io.write_json(kernel.root/'build/investigations/runs'/job['id']/'result.json',result);print(records.canonical(result).decode());return code
if __name__=='__main__':raise SystemExit(main())
