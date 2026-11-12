"""Revision-bound Brain Link services over current native sources."""
from functools import lru_cache
import re
from pathlib import Path
from sdk.cli.arc1cli.relations import NetGraph
from . import record_io as io

BASE='hardware/compact-arc1/R10_WORK/'
NETLIST=BASE+'cad/NETLIST.xml'
PCB=BASE+'cad/ARC1_R10.kicad_pcb'
BINDINGS='project/brain_link.json'
FIELDS={
    'links.catalog':({'query':{'type':'string','maxLength':200},'limit':{'type':'integer','minimum':1,'maximum':1000}},[]),
    'links.inspect':({'component':{'type':'string','maxLength':50},'include_power':{'type':'boolean'},
        'net_kind':{'type':'string','enum':['all','usb-data']},
        'expected_revision':{'type':'string','maxLength':64}},['component']),
    'links.trace':({'start':{'type':'string','maxLength':50},'end':{'type':'string','maxLength':50},
        'net_kind':{'type':'string','enum':['all','usb-data']},
        'include_power':{'type':'boolean'},'expected_revision':{'type':'string','maxLength':64}},['start','end']),
}


def inputs(root):
    names=[NETLIST,PCB,BINDINGS,'workbench/brain_link.py','sdk/cli/arc1cli/relations.py',
           'project/register/bindings.json','docs/ledger2/OPEN_ISSUES.json']
    names += [p.relative_to(root).as_posix() for p in sorted((Path(root)/(BASE+'cad')).glob('*.kicad_sch'))]
    return io.manifest(root,names)


@lru_cache(maxsize=4)
def native(root,netlist_sha):
    data=io.project_path(root,NETLIST).read_bytes();graph=NetGraph(data)
    if graph.sha256!=netlist_sha:raise ValueError('NETLIST_CHANGED_DURING_READ')
    return graph


def bound(root):
    root=Path(root).resolve();manifest=inputs(root)
    graph=native(str(root),manifest[NETLIST]['sha256'])
    return graph,manifest,io.digest(manifest)


def links_for(root,ref,graph):
    cfg=io.load(root,BINDINGS);explicit=cfg.get('objects',{}).get(ref,{})
    component=graph.components[ref];sheet=graph.sheets.get(component['sheet_name'])
    result=[]
    if sheet and Path(sheet).name==sheet:
        result.append({'kind':'native_schematic','path':BASE+'cad/'+sheet,'locator':ref})
    result.extend({'kind':'software_intent','path':n,'locator':ref} for n in explicit.get('sources',[]))
    result.extend([{'kind':'native_netlist','path':NETLIST,'locator':ref},
                   {'kind':'native_pcb','path':PCB,'locator':ref}])
    rows=[]
    for r in result:
        p=io.project_path(root,r['path'],False)
        rows.append({**r,'available':p.is_file(),'sha256':io.sha(p) if p.is_file() else None})
    return rows


def related_records(root,ref):
    cfg=io.load(root,'project/register/bindings.json')
    requirements=[r for r in cfg['requirements'] if 'R10:'+ref in r['object_refs']]
    pattern=re.compile(r'(?<![A-Za-z0-9])'+re.escape(ref)+r'(?![A-Za-z0-9])')
    issues=[r for r in io.load(root,'docs/ledger2/OPEN_ISSUES.json')['issues'] if pattern.search(str(r))]
    return requirements,issues


def dispatch(kernel,operation,args):
    root=kernel.root;graph,manifest,rev=bound(root)
    if args.get('expected_revision') and args['expected_revision']!=rev:
        return {'schema':'arc.brain-link/1','state':'STALE','revision':rev,'expected_revision':args['expected_revision'],
                'message':'Native sources or selection bindings changed. Refresh before cross-probing.','edges':[],
                'source_manifest':manifest,'physical_measurements':False}
    from .cad_export import status as export_status
    export=export_status(root)
    identity={'schema':'arc.brain-link/1','state':'CURRENT' if export['state']=='VERIFIED_EXPORT' else 'UNVERIFIED_EXPORT','revision':rev,'source_manifest':manifest,
              'export_binding':export,
              'relation':'NATIVE_SCHEMATIC_NET','routed_connectivity_verified':False,'physical_measurements':False,
              'board_revision':'R10','fabrication':'HOLD'}
    if operation=='links.catalog':
        query=args.get('query','').casefold();rows=[c for c in graph.components.values() if query in (c['reference']+' '+c['value']).casefold()]
        return {**identity,'components':[{k:c[k] for k in ('reference','value','footprint','native_uuid')} for c in rows[:args.get('limit',200)]],
                'total_components':len(graph.components),'matching_components':len(rows),'nets':len(graph.nets),'pin_entries':graph.pin_count}
    if operation=='links.trace':
        return {**identity,'trace':graph.trace(args['start'],args['end'],include_power=args.get('include_power',False),net_kind=args.get('net_kind','all'))}
    ref=args['component'];ref=ref.removeprefix('R10:')
    if ref not in graph.components:raise ValueError('UNKNOWN_COMPONENT')
    neighbors,total=graph.neighbors(ref,args.get('include_power',False),30,args.get('net_kind','all'))
    requirements,issues=related_records(root,ref)
    component=graph.components[ref]
    if inputs(root)!=manifest:raise ValueError('NATIVE_INPUTS_CHANGED_DURING_READ')
    return {**identity,'component':component,'neighbors':neighbors,'total_neighbors':total,
            'truncated':total>len(neighbors),'source_links':links_for(root,ref,graph),
            'requirements':requirements,'issues':issues,
            'layers':[
                {'id':'schematic','label':'Native schematic net','state':'SOURCE_BOUND'},
                {'id':'copper','label':'Routed copper','state':'INSPECT_IN_NATIVE_PCB'},
                {'id':'airwire','label':'Unrouted airwire','state':'NOT_COMPUTED_FROM_NETLIST'},
                {'id':'intent','label':'Software intent','state':'EXPLICIT_BINDING'},
                {'id':'model','label':'Modeled event','state':'NO_MODEL_TRACE_SELECTED'},
                {'id':'physical','label':'Physical measurement','state':'UNAVAILABLE'}]}
