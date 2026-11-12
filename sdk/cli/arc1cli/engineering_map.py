"""Source-bound relationships over a sealed reference snapshot; no execution authority.

NetGraph remains the common netlist engine. Native PCB pads corroborate each
reported endpoint. Software associations are declarations, never electrical nets.
"""
from __future__ import annotations
import hashlib,json,re,zipfile
from pathlib import Path
from . import knowledge_sources as sources,record_store as records
from .relations import NetGraph,is_power
from .kicad_sexpr import parse

VERSION='arc.engineering-map/1'
CAD='hardware/compact-arc1/R10_WORK/cad/'
NETLIST=CAD+'NETLIST.xml';PCB=CAD+'ARC1_R10.kicad_pcb'
MAX_GRAPH=8*1024*1024
def fingerprint():
    return sources.digest({p.name:records.sha(p) for p in (Path(__file__),Path(__file__).with_name('relations.py'),Path(__file__).with_name('kicad_sexpr.py'))})
def parts(node,name):return [x for x in node[1:] if isinstance(x,list) and x and x[0]==name]
def one(node,name):
    found=parts(node,name)
    if len(found)>1:raise ValueError('MAP_AMBIGUOUS_'+name.upper())
    return found[0] if found else []
def value(node,index=1):return node[index] if len(node)>index and isinstance(node[index],str) else ''
def properties(node):
    out={}
    for child in parts(node,'property'):
        key=value(child);val=value(child,2)
        if key in out:raise ValueError('MAP_DUPLICATE_PROPERTY')
        out[key]=val
    return out
def read_archive(path,report,check=None):
    path=sources.regular(path);expected=report['archive_sha256']
    if path.stat().st_size>sources.MAX_ARCHIVE or records.sha(path)!=expected:raise ValueError('MAP_ARCHIVE_CHANGED')
    content={};manifest={};total=0
    with zipfile.ZipFile(path) as z:
        infos=z.infolist();names=[i.filename for i in infos]
        if len(names)>5000 or len(names)!=len(set(names)) or sum(i.file_size for i in infos)>sources.MAX_EXPANDED:raise ValueError('MAP_ZIP_LIMIT')
        prefix='Ledger_User_Data_Archive/';mp=prefix+'ARCHIVE_MANIFEST.json';raw=z.read(mp)
        if hashlib.sha256(raw).hexdigest()!=report['archive_manifest_sha256']:raise ValueError('MAP_ARCHIVE_MANIFEST_CHANGED')
        m=records.strict(raw)
        for name,row in sorted(m['files'].items()):
            if not name.startswith('Original_Ledger/'):continue
            rel=name.removeprefix('Original_Ledger/');records.safe_name(rel)
            wanted=(rel.startswith(CAD) and rel.endswith(('.kicad_sch','.kicad_pcb','.xml')) or rel.startswith('hardware/compact-arc1/R10_WORK/') and rel.endswith(('.c','.h','.v','.sv')) or rel in ('project/brain_link.json','project/brain_link_export.json','project/register/bindings.json'))
            if not wanted:continue
            sources.interrupted(check);entry=z.getinfo(prefix+name)
            if entry.file_size>16*1024*1024 or entry.is_dir() or entry.flag_bits&1 or (entry.external_attr>>16)&0o170000==0o120000:raise ValueError('MAP_UNSAFE_MEMBER')
            total+=entry.file_size
            if total>64*1024*1024:raise ValueError('MAP_INPUT_BUDGET')
            raw=z.read(entry)
            if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('MAP_MEMBER_CHANGED')
            content[rel]=raw;manifest[rel]={'bytes':len(raw),'sha256':row['sha256']}
        # Only identities are retained for declared software links; source bytes remain outside Ledger.
        all_files={n.removeprefix('Original_Ledger/'):r for n,r in m['files'].items() if n.startswith('Original_Ledger/')}
    if records.sha(path)!=expected:raise ValueError('MAP_ARCHIVE_CHANGED_DURING_READ')
    return content,manifest,all_files
def build(path,report,check=None):
    content,manifest,all_files=read_archive(path,report,check)
    graph=NetGraph(content[NETLIST]);tree=parse(content[PCB].decode('utf-8-sig'))
    if not tree or tree[0]!='kicad_pcb':raise ValueError('MAP_EXPECTED_NATIVE_BOARD')
    pcbs={}
    for fp in parts(tree,'footprint'):
        props=properties(fp);ref=props.get('Reference')
        if not ref:continue
        if ref in pcbs:raise ValueError('MAP_DUPLICATE_BOARD_REFERENCE')
        pads={}
        for pad in parts(fp,'pad'):
            pin=value(pad);net=one(pad,'net');name=value(net,2)
            if not pin:continue
            pads.setdefault(pin,[]).append({'uuid':value(one(pad,'uuid')),'net':name})
        pcbs[ref]={'uuid':value(one(fp,'uuid')),'footprint':value(fp),'properties':props,'pads':pads}
    symbols={}
    for path,raw in content.items():
        if not path.endswith('.kicad_sch'):continue
        sources.interrupted(check);sch=parse(raw.decode('utf-8-sig'))
        if not sch or sch[0]!='kicad_sch':raise ValueError('MAP_EXPECTED_NATIVE_SCHEMATIC')
        for sym in parts(sch,'symbol'):
            ident=value(one(sym,'uuid'));props=properties(sym)
            if not ident:continue
            if ident in symbols:raise ValueError('MAP_DUPLICATE_SYMBOL_UUID')
            symbols[ident]={'path':path,'uuid':ident,'properties':props}
    receipt=records.strict(content.get('project/brain_link_export.json',b'{}'))
    recorded=receipt.get('inputs',{});export_current=receipt.get('state')=='VERIFIED_EXPORT' and bool(recorded) and all(manifest.get(n)==r for n,r in recorded.items())
    cfg=records.strict(content.get('project/brain_link.json',b'{}'));requirements=records.strict(content.get('project/register/bindings.json',b'{}')).get('requirements',[])
    wanted={ref.casefold() for ref in graph.components}|{n.casefold() for n in graph.nets if not is_power(n) and not n.startswith('unconnected-')}
    mentions={}
    for path,raw in sorted(content.items()):
        if not path.endswith(('.c','.h','.v','.sv')):continue
        sources.interrupted(check)
        for number,line in enumerate(raw.decode('utf-8-sig').splitlines(),1):
            for token in {t.casefold() for t in re.findall(r'[A-Za-z_][A-Za-z0-9_]*',line)}&wanted:
                found=mentions.setdefault(token,[])
                if len(found)<8:found.append({'path':path,'line':number,'identifier':token,'sha256':manifest[path]['sha256'],'origin':'LEXICAL_IDENTIFIER_MENTION','implementation_mapping_review':'UNREVIEWED'})
    components={};mismatches=[]
    for ref,c in sorted(graph.components.items()):
        sources.interrupted(check);pcb=pcbs.get(ref);sym=symbols.get(c['native_uuid']);gaps=[];pins=[]
        if pcb is None:gaps.append('NO_MATCHING_NATIVE_FOOTPRINT')
        if sym is None or sym['properties'].get('Reference')!=ref:gaps.append('NATIVE_SYMBOL_IDENTITY_UNRESOLVED')
        elif sym['properties'].get('Value')!=c['value'] or sym['properties'].get('Footprint')!=c['footprint']:gaps.append('NATIVE_SYMBOL_FIELDS_DISAGREE')
        if pcb and (pcb['properties'].get('Value')!=c['value'] or pcb['footprint']!=c['footprint']):gaps.append('NATIVE_BOARD_FIELDS_DISAGREE')
        for pin in c['pins']:
            pads=pcb['pads'].get(pin['pin'],[]) if pcb else []
            unconnected=pin['net'].startswith('unconnected-') and bool(pads) and all(not p['net'] for p in pads)
            matched=bool(pads) and all(p['net']==pin['net'] for p in pads)
            if not matched and not unconnected:mismatches.append({'reference':ref,'pin':pin['pin'],'net':pin['net']})
            pins.append({**pin,'pad_uuids':[p['uuid'] for p in pads],'state':'NATIVE_PAD_NET_MATCH' if matched else 'NATIVE_UNCONNECTED_PIN' if unconnected else 'PAD_NET_DISAGREEMENT','method':'NETLIST_TO_NATIVE_PCB_PAD','physical_verified':False})
        software=[]
        for name in sorted(set(cfg.get('objects',{}).get(ref,{}).get('sources',[]))):
            records.safe_name(name);r=all_files.get(name);software.append({'path':name,'sha256':r.get('sha256') if r else None,'origin':'ARCHIVED_EXPLICIT_BINDING','state':'DECLARED_ASSOCIATION' if r else 'MISSING_SOURCE','electrical_relationship':False})
        candidate_tokens={ref.casefold()}|{p['net'].casefold() for p in c['pins'] if not is_power(p['net']) and not p['net'].startswith('unconnected-')}
        code_candidates=[];seen_candidates=set()
        for token in sorted(candidate_tokens):
            for item in mentions.get(token,[]):
                key=(item['path'],item['line'],token)
                if key not in seen_candidates and len(code_candidates)<24:seen_candidates.add(key);code_candidates.append(item)
        selected_requirements=[r for r in requirements if 'R10:'+ref in r.get('object_refs',[])]
        components[ref]={**c,'id':sources.digest({'kind':'native_component','board_sha256':manifest[PCB]['sha256'],'symbol_uuid':c['native_uuid']})[:32],
          'mpn':pcb['properties'].get('MPN','') if pcb else '', 'manufacturer':pcb['properties'].get('Manufacturer','') if pcb else '',
          'package':c['footprint'],'grade':'UNVERIFIED','operating_conditions':'UNVERIFIED','symbol':sym,'pcb_uuid':pcb['uuid'] if pcb else None,
          'pins':pins,'gaps':gaps,'software':software,'code_candidates':code_candidates,'requirements':selected_requirements,'review_state':'REFERENCE_SOURCE_IDENTITY_ONLY'}
    body={'schema':VERSION,'reader':fingerprint(),'source_manifest':manifest,'archive_sha256':report['archive_sha256'],'working_version':'V1',
      'components':components,'nets':graph.nets,'pin_count':graph.pin_count,'pad_net_disagreements':mismatches,
      'native_export':{'state':'ARCHIVED_EXPORT_RECEIPT_MATCHES_INPUTS' if export_current else 'UNVERIFIED_EXPORT','tool_version':receipt.get('tool_version'),'fresh_export_performed':False,'independent_review':receipt.get('independent_review','UNKNOWN')},
      'authority':'REFERENCE_SNAPSHOT_NOT_ACCEPTED_CURRENT_PROJECT','routed_copper_verified':False,'physical_qualification':False}
    body['source_digest']=sources.digest(manifest);body['graph_digest']=sources.digest(body)
    if len(records.canonical(body))>MAX_GRAPH:raise ValueError('MAP_OUTPUT_BUDGET')
    return body
def trace(graph,start,end,net_prefix=None):
    # Reuse the existing graph traversal over the same verified native netlist.
    g=NetGraph.__new__(NetGraph);g.components=graph['components'];g.nets={n:r for n,r in graph['nets'].items() if net_prefix is None or n.startswith(net_prefix)};g.members={ref:{p['net'] for p in c['pins'] if p['net'] in g.nets} for ref,c in g.components.items()}
    result=g.trace(start,end,max_hops=12,include_power=False)
    for edge in result['edges']:
        edge['endpoints']=[p for ref in (edge['from'],edge['to']) for p in graph['components'][ref]['pins'] if p['net'] in edge['nets']]
        edge['state']='NATIVE_ENDPOINTS_CORROBORATED' if all(p['state']=='NATIVE_PAD_NET_MATCH' for p in edge['endpoints']) else 'NATIVE_DISAGREEMENT'
    result['net_name_prefix']=net_prefix
    result['scope']='COMPONENT_GRAPH_PATH_NOT_ELECTRICAL_CONDUCTION'
    return result
def document_candidates(component,documents):
    mpn=component['mpn']
    if not mpn:return []
    pattern=re.compile(r'(?<![A-Za-z0-9])'+re.escape(mpn)+r'(?![A-Za-z0-9])',re.I)
    return [{'record_id':n,'source_sha256':r['sha256'],'title':r['title'],'match':'EXACT_MPN_IN_ARCHIVE_METADATA','review':'DOCUMENT_APPLICABILITY_UNREVIEWED',
       'variant':r.get('metadata',{}).get('variant','UNKNOWN'),'revision':r.get('metadata',{}).get('revision','UNKNOWN')}
       for n,r in sorted(documents.items()) if n.lower().endswith('.pdf') and r['kind']=='vendor-original' and pattern.search(r['title']+' '+json.dumps(r.get('metadata',{}),ensure_ascii=False))]

def compile_read(program):
    """Finite source/map syntax, lowered to the very same Kernel read operations."""
    import shlex
    if not isinstance(program,str) or not 1<=len(program.encode())<=4096 or any(x in program for x in ('\n','\r','\x00')):raise ValueError('MAP_PROGRAM_BOUND')
    lexer=shlex.shlex(program,posix=True,punctuation_chars='|');lexer.whitespace_split=True;lexer.commenters='';stages=[[]]
    for token in lexer:
        if token=='|':stages.append([])
        else:stages[-1].append(token)
    if not 2<=len(stages)<=3 or len(stages[0])!=2:raise ValueError('MAP_READ_SYNTAX')
    kind,ident=stages[0];command=stages[1];presentation=None;limit=5;expected=None
    if kind=='map' and '@' in ident:ident,expected=ident.split('@',1)
    if not re.fullmatch('[0-9a-f]{32}',ident) or expected is not None and not re.fullmatch('[0-9a-f]{64}',expected):raise ValueError('MAP_READ_IDENTITY')
    if len(stages)==3:
        if kind=='source' and len(stages[2])==2 and stages[2][0]=='take' and stages[2][1].isdigit():
            limit=int(stages[2][1])
            if not 1<=limit<=40:raise ValueError('MAP_READ_LIMIT')
        elif kind=='map' and stages[2] in (['why'],['gaps']):presentation=stages[2][0]
        else:raise ValueError('MAP_READ_PRESENTATION')
    args={'id':ident}
    if kind=='source':
        if len(command)==2 and command[0]=='search':operation='knowledge.search';args.update(query=command[1],limit=limit)
        elif command==['originals'] and len(stages)==2:operation='knowledge.sources'
        else:raise ValueError('MAP_SOURCE_READ_SYNTAX')
    elif kind=='map':
        if expected:args['expected_revision']=expected
        if len(command)==2 and command[0]=='part':operation='knowledge.map.part';args['component']=command[1]
        elif len(command)==2 and command[0]=='net':operation='knowledge.map.net';args['net']=command[1]
        elif len(command) in (3,5) and command[0]=='trace':
            operation='knowledge.map.trace';args.update(start=command[1],end=command[2])
            if len(command)==5:
                if command[3]!='on':raise ValueError('MAP_TRACE_FILTER_SYNTAX')
                args['net_prefix']=command[4]
        elif len(command) in (1,2) and command[0]=='evidence':
            operation='knowledge.map.evidence'
            if len(command)==2:args['component']=command[1]
        elif command==['status']:operation='knowledge.map.get'
        else:raise ValueError('MAP_READ_OPERATION_UNSUPPORTED')
    else:raise ValueError('MAP_READ_CONTEXT_UNSUPPORTED')
    body={'schema':'arc.stac.map-ir/1','operation':operation,'arguments':args,'effects':['read'],'presentation':presentation}
    return {**body,'program_id':sources.digest(body),'authority':'EXISTING_CALLER_PRINCIPAL_REQUIRED'}
