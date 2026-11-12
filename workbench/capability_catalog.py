"""One passive capability view for GUI, CLI and Slate; not an execution gate."""
from __future__ import annotations
import hashlib
from pathlib import Path
import shutil
from sdk.cli.arc1cli import capability_catalog as contract
from . import project_context

TEXT={'type':'string','maxLength':180}
FIELDS={'ledger.capabilities.catalog':({'query':TEXT},[])}
SCOPES={op:'read' for op in FIELDS}

# Tool dependencies describe job execution, not the read-only inspect command.
# No executable is invoked while building a catalogue.
NATIVE={'math':'soffice','cad':'kicad-cli','kibot':'kibot','spice':'ngspice','yosys':'yosys',
        'nextpnr':'nextpnr-ecp5','trellis':'ecppack','surfer':'surfer',
        'icarus':'iverilog','verilator':'verilator'}


# Digests are remembered by path, size and modification time; any change recomputes.
# Only the hash is cached: every state word is decided afresh on each call.
_DIGESTS={}


def digest(path):
    path=Path(path);stat=path.stat();key=(str(path),stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns,stat.st_ino)  # a restored mtime cannot forge ctime or inode
    value=_DIGESTS.get(key)
    if value is None:
        if len(_DIGESTS)>4096:_DIGESTS.clear()
        value=_DIGESTS[key]=hashlib.sha256(path.read_bytes()).hexdigest()
    return value


def source(root,name):
    from .stacy_foundation import project_file
    try:
        path=project_file(root,name)
        return {'path':name,'state':'PRESENT','sha256':digest(path)}
    except (OSError,ValueError):
        return {'path':name,'state':'MISSING_OR_UNSAFE','sha256':None}


def native(root,family):
    if family=='python-wasi':
        from .experiment_runtime import status
        value=status()
        return {'state':'DETECTED' if value['available'] else 'MISSING','reason':'PINNED_WASI_RUNTIME_VERIFIED_NOT_EXECUTED' if value['available'] else value['reason'],
                'version':value.get('python'),'licence':'PSF-2.0; WASMTIME-APACHE-2.0-WITH-LLVM-EXCEPTION','compatibility':'HOST_QUALIFICATION_REQUIRED'}
    if family=='brain':
        from . import brain_runtime
        try:
            info=brain_runtime.status(root)
            if info['state']!='PINNED_CPU_AVAILABLE':
                return {'state':'INCOMPATIBLE' if info['state']=='RUNTIME_PLATFORM_UNAVAILABLE' else 'MISSING',
                        'reason':info['state'],'version':None,'licence':'UNASSESSED'}
            pin=info['pin'];entry=pin['platforms'][info['platform']]
            if pin.get('schema')!='arc.pinned-llama-runtime/1':
                return {'state':'INCOMPATIBLE','reason':'RUNTIME_PIN_SCHEMA_UNSUPPORTED','version':None,'licence':'UNASSESSED'}
            from .stacy_foundation import project_file
            relative=(Path(brain_runtime.PIN).parent/entry['archive']).as_posix()
            path=project_file(root,relative,128*1024*1024)
            if digest(path)!=entry['sha256']:
                return {'state':'INVALID','reason':'PINNED_RUNTIME_ARCHIVE_CHANGED','version':None,'licence':'UNASSESSED'}
            return {'state':'DETECTED','reason':'PINNED_ARCHIVE_VERIFIED_NOT_EXECUTED',
                    'version':pin['build'],'source_commit':pin['source_commit'],
                    'platform':info['platform'],'licence':pin.get('licence','UNASSESSED'),
                    'compatibility':'NATIVE_LOADING_AND_MODEL_NOT_CHECKED'}
        except (OSError,ValueError,KeyError,TypeError):
            return {'state':'INVALID','reason':'RUNTIME_PIN_OR_ARCHIVE_INVALID','version':None,'licence':'UNASSESSED'}
    if family not in NATIVE:
        return {'state':'UNASSESSED','reason':'NO_NATIVE_DEPENDENCY_PROFILE','version':None,'licence':'UNASSESSED'}
    executable=NATIVE[family]
    try:
        detected=shutil.which(executable)
        if family=='icarus' and detected:
            from .hdl_tools import discover
            info=discover('icarus')
            return {'state':'DETECTED' if info['state']=='DETECTED' else 'MISSING',
                    'reason':info['state'],'command':executable,'version':None,'licence':'UNASSESSED',
                    'compatibility':'VERSION_UNMEASURED'}
        return {'state':'DETECTED' if detected else 'MISSING','command':executable,
                'reason':'EXECUTABLE_ON_PATH' if detected else 'EXECUTABLE_NOT_FOUND',
                'version':None,'licence':'UNASSESSED','compatibility':'VERSION_UNMEASURED'}
    except (OSError,ValueError):
        return {'state':'INVALID','reason':'PASSIVE_DISCOVERY_FAILED','version':None,'licence':'UNASSESSED'}


def catalogue(kernel,principal,query='',include_tools=True):
    from .engineering_kernel import CAPABILITIES,TOOLS
    from .engineering_cli import schemas
    from .stacy_foundation import handler_map,prerequisites
    if not isinstance(query,str) or len(query)>180:raise ValueError('CAPABILITY_QUERY_BOUND')
    definitions=schemas();handlers=handler_map();attached=not project_context.detached(kernel.root)
    sources={};runtimes={}
    def bound(name):
        if name not in sources:sources[name]=source(kernel.root,name)
        return sources[name]
    def runtime(family):
        if family not in runtimes:runtimes[family]=native(kernel.root,family)
        return runtimes[family]
    rows=[]
    for op,scope in sorted(CAPABILITIES.items()):
        if query.casefold() not in (op+' '+scope).casefold():continue
        handler=handlers.get(op);src=bound(handler['path']) if handler else None
        eligible=scope in principal.scopes and not (principal.mode=='Tutor' and scope!='read')
        inputs=prerequisites(kernel.root,op)
        # Inspect and result reads must continue to work when native tools are
        # absent. Execution prerequisites belong to the selected job below.
        assessment=contract.assess(declared=True,source_present=(src['state']=='PRESENT') if src else None,
            required_inputs=inputs,project_attached=attached or not project_context.requires_project(op,{}),
            scope_eligible=eligible,requires_arguments=bool(definitions[op]['required']),mode=principal.mode)
        rows.append({'operation':op,'scope':scope,'arguments':definitions[op],
                     'handler':handler,'source':src,'adapter':handler['path'] if handler else None,
                     'adapter_version':src['sha256'] if src else None,
                     'licence':'PROJECT_SOURCE_LICENCES_APPLY_NOT_REVIEWED_BY_CATALOGUE',
                     'assessment':assessment,'summary':contract.summary(assessment)})
    tools=[]
    if include_tools:
        for name,target in sorted(TOOLS.items()):
            if query.casefold() not in (name+' execute').casefold():continue
            family='python-wasi' if name in ('lab.qualify','lab.python') else 'cad' if name=='lab.board' else name.split('.')[0];module=target[0]
            path=module.replace('.','/')+'.py' if module.startswith('workbench.') else None
            src=bound(path) if path else None
            rt=runtime(family)
            approve=name in ('brain.inspect','brain.activate','brain.qualify','knowledge.investigate')
            eligible='execute' in principal.scopes and principal.mode!='Tutor' and name in principal.tools and (not approve or 'approve' in principal.scopes)
            assessment=contract.assess(declared=True,source_present=(src['state']=='PRESENT') if src else None,
                required_inputs=[],project_attached=attached or not project_context.requires_project('jobs.submit',{'tool':name}),
                scope_eligible=eligible,native_state=rt['state'],requires_arguments=True,mode=principal.mode)
            tools.append({'tool':name,'source':src,'native':rt,'assessment':assessment,
                          'summary':contract.summary(assessment),'execution':'jobs.submit',
                          'notice':'Tool, candidate, owner, request options and source checks remain authoritative.'})
    return {'schema':'arc.capability-catalog/1','assistant':'Slate','operations':rows,'tools':tools,
            'assessment_sources':[bound('workbench/capability_catalog.py'),bound('sdk/cli/arc1cli/capability_catalog.py')],
            'registered_operations':len(CAPABILITIES),'registered_job_tools':len(TOOLS),
            'query':query,'effects':['read'],'model_calls':0,'network_calls':0,'native_invocations':0,
            'notice':'Passive prerequisite snapshot only. Dispatch rechecks actual arguments and authority. Qualification is unassessed until a checked evidence adapter exists.'}


def by_operation(kernel,principal,query=''):
    return {r['operation']:r for r in catalogue(kernel,principal,query,include_tools=False)['operations']}


def dispatch(kernel,op,args,principal):
    if op not in FIELDS:raise ValueError('Unknown catalogue operation')
    return catalogue(kernel,principal,args.get('query',''))
