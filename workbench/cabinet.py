"""Typed logical filing over existing stores. No file walk, copy or new store.

Display placements and record identities are separate. A project link is a
reference; it never changes the target's project, owner or physical location.
"""
from __future__ import annotations
import hashlib
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3

SCHEMA='ledger.cabinet/1'
MAX_NODES=2400
MAX_BYTES=4*1024*1024
TEXT={'type':'string','minLength':1,'maxLength':600}
FIELDS={'ledger.cabinet':({'limit':{'type':'integer','minimum':10,'maximum':1000}},[]),
        'ledger.cabinet.get':({'id':TEXT},['id'])}
SCOPES={op:'read' for op in FIELDS}
DESK_KINDS={'project','idea','assignment','discovery_inquiry','document'}
DESK_OPS={'project':'projects.get','idea':'ideas.get','assignment':'assignments.get','discovery_inquiry':'discovery.get','document':'documents.get'}
LINK_GROUPS={'SOURCE':'Sources','QUESTION':'Questions','DECISION':'Decisions','ALTERNATIVE':'Alternatives',
             'TASK':'Tasks','WORKING_COPY':'Working copies','OUTPUT':'Outputs'}
TRANSFERS=[dict(id='transfer:import',label='Import',direction='IMPORT',destination='office',
                description='Inspect incoming material using the existing receiving controls.'),
           dict(id='transfer:export',label='Export',direction='EXPORT',destination='files:Egress',
                description='Open Egress, the folder outgoing copies leave from; export remains an explicit file action.')]


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def natural(value):
    return tuple((1,int(part)) if part.isdigit() else (0,part.casefold()) for part in re.split(r'(\d+)',value))


def caption(value,limit=110):
    return re.sub(r'\s+',' ',str(value)).strip()[:limit] or 'Untitled record'


def catalog_file(kernel):
    from .ledger_control import session
    return session(kernel).path.parent/'concern/catalog.sqlite3'


def catalog_rows(kernel,limit):
    """Read the existing personal catalogue without creating or migrating it."""
    path=catalog_file(kernel)
    if not path.is_file():return dict(objects=[],relations=[],state='NOT_PRESENT',partial=False)
    try:
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory=sqlite3.Row;db.execute('BEGIN')
            if db.execute('PRAGMA user_version').fetchone()[0]!=1:raise ValueError('Catalogue version is unsupported')
            rows=[dict(r) for r in db.execute('SELECT * FROM objects ORDER BY id LIMIT ?', (limit+1,))]
            if not any(r['id']=='concern' for r in rows):
                root=db.execute("SELECT * FROM objects WHERE id='concern'").fetchone()
                if root:rows.insert(0,dict(root))
            partial=len(rows)>limit;rows=rows[:limit]
            ids={r['id'] for r in rows}
            relation_rows=db.execute('SELECT * FROM relations ORDER BY source,kind,target LIMIT ?', (MAX_NODES*2+1,)).fetchall()
            partial=partial or len(relation_rows)>MAX_NODES*2
            relations=[dict(r) for r in relation_rows[:MAX_NODES*2] if r['source'] in ids and r['target'] in ids]
            return dict(objects=rows,relations=relations,state='AVAILABLE',partial=partial)
    except (sqlite3.Error,ValueError) as exc:
        return dict(objects=[],relations=[],state='UNAVAILABLE',partial=False,reason=str(exc))


def records(kernel,principal,limit):
    """Bounded stored metadata; no source hashes, solver calls or binding checks."""
    from . import project_desk as desk
    result=[];copies=[];investigations=[];partial=False;notices=[];size=0
    with kernel.db() as db:
        db.execute('BEGIN')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'desk_records' in tables:
            rows=db.execute("SELECT id,kind,length(CAST(payload AS BLOB)) FROM desk_records WHERE owner=? AND kind IN ('project','idea','assignment','discovery_inquiry','document') ORDER BY rowid DESC LIMIT ?",(principal.identity,limit+1)).fetchall()
            partial=len(rows)>limit
            for ident,kind,length in rows[:limit]:
                if length>MAX_BYTES or size+length>MAX_BYTES:
                    partial=True;notices.append('Stored record budget reached; existing workspaces retain access.');continue
                size+=length
                try:result.append(desk.read(db,kind,ident,principal))
                except ValueError:notices.append('A stored Desk record failed integrity checking.');partial=True
        if 'copies' in tables:
            # Copies have a real owner but no project-membership field. Do not
            # infer membership from a source path or a project reference.
            kind='kind' if any(r[1]=='kind' for r in db.execute('PRAGMA table_info(copies)')) else "'file' AS kind"
            rows=db.execute('SELECT id,owner,source,work,state,revision,'+kind+' FROM copies WHERE owner=? ORDER BY updated DESC LIMIT ?',
                            (principal.identity,limit+1)).fetchall()
            partial=partial or len(rows)>limit
            copies=[dict(zip(('id','owner','source','work','state','revision','kind'),r)) for r in rows[:limit]]
        if 'inv_investigations' in tables:
            rows=db.execute('SELECT id,question,state,updated,steps_used FROM inv_investigations WHERE owner=? ORDER BY updated DESC LIMIT ?',
                            (principal.identity,limit+1)).fetchall()
            partial=partial or len(rows)>limit
            investigations=[dict(zip(('id','question','state','updated','steps_used'),r)) for r in rows[:limit]]
    return result,copies,investigations,partial,sorted(set(notices))


def snapshot(kernel,principal,limit=300):
    from .ledger_control import value
    from sdk.cli.arc1cli.concern_catalog import shown  # GRAPHITE-01: an untouched pre-rename seed title reads in Graphite words
    policy=value(kernel,'cabinet.sort');catalog=catalog_rows(kernel,limit)
    stored,copies,investigations,partial,notices=records(kernel,principal,limit)
    partial=partial or catalog['partial'];nodes=[];by_id={};home={}
    if catalog['state']=='UNAVAILABLE':notices.append('The existing catalogue is unavailable; other providers remain visible.')
    def add(ident,parent,role,label,provider,target=None,scope='owner_private',canonical=None,owning=False,**extra):
        nonlocal partial
        if len(nodes)>=MAX_NODES:partial=True;return None
        if ident in by_id:raise ValueError('CABINET_NODE_COLLISION')
        row=dict(id=ident,parent=parent,role=role,label=caption(label),target=target,
                 scope=scope,provider=provider,canonical_id=canonical or ident,owning=owning,**extra)
        nodes.append(row);by_id[ident]=row;return row
    root=add('cabinet:concern',None,'cabinet','Concern','cabinet',scope='mixed')
    objects={r['id']:r for r in catalog['objects']}
    if 'concern' in objects:
        root.update(target=dict(kind='catalog',id='concern'),canonical_id='catalog:concern',provider='concern_catalog',
                    scope='connected_profile',description=objects['concern']['title'])
    projects_id='catalog:projects' if 'projects' in objects else 'cabinet:projects'
    if projects_id=='cabinet:projects':add(projects_id,root['id'],'drawer','Projects','cabinet')
    parents={}
    for row in catalog['relations']:
        if row['source']=='concern' or row['kind'] not in ('part_of','maintained_by'):continue
        parents.setdefault(row['source'],[]).append((0 if row['kind']=='part_of' else 1,row['target'],row['kind']))
    chosen={ident:sorted(choices)[0] for ident,choices in parents.items()}
    def catalog_parent(ident):
        relation=chosen.get(ident)
        if relation is None or relation[1]=='concern':return root['id']
        seen={ident};parent=relation[1]
        while parent in chosen:
            if parent in seen:
                notices.append('A catalogue relation cycle is shown at the cabinet root.');return root['id']
            seen.add(parent);parent=chosen[parent][1]
        return 'catalog:'+relation[1]
    for ident,obj in objects.items():
        if ident=='concern':continue
        add('catalog:'+ident,catalog_parent(ident),'drawer' if obj['kind'] in ('collection','office') else 'catalog_record',
            shown(ident,obj['title']),'concern_catalog',dict(kind='catalog',id=ident),scope='connected_profile',
            canonical='catalog:'+ident,revision=obj['version'],state=obj['state'],record_kind=obj['kind'],
            relation=chosen.get(ident,(None,None,None))[2],description='Existing catalogue identity; filing relations do not confer permissions.')
    for relation in catalog['relations']:
        source=relation['source'];target=relation['target']
        if source=='concern' or relation['kind'] not in ('part_of','maintained_by','related_to') or source not in objects:continue
        if chosen.get(source)==(0 if relation['kind']=='part_of' else 1,target,relation['kind']):continue
        parent=root['id'] if target=='concern' else 'catalog:'+target
        ident='catalog-reference:'+digest([source,relation['kind'],target])[:32]
        add(ident,parent,'reference',shown(source,objects[source]['title']),'concern_catalog',dict(kind='catalog',id=source),
            scope='connected_profile',canonical='catalog:'+source,relation=relation['kind'],
            canonical_home=catalog_parent(source),description='An additional declared catalogue placement of the same identity.')
    projects={r['id']:r for r in stored if r['kind']=='project'}
    for record in projects.values():
        ident='project:'+record['id'];home[ident]=projects_id
        add(ident,projects_id,'project',record['title'],'project_desk',dict(kind='desk',record_kind='project',id=record['id']),
            canonical=ident,owning=True,revision=record['revision'],description=record['original_intent'][:240])
    unassigned='cabinet:unassigned';other='cabinet:other-projects'
    def container(ident,label):
        if ident not in by_id:add(ident,root['id'],'drawer',label,'cabinet')
        return ident
    def folder(parent,key,label):
        ident='folder:'+parent+':'+key
        if ident not in by_id:add(ident,parent,'folder_view',label,'cabinet',description='A view of existing records; no physical folder is created.')
        return ident
    for record in stored:
        kind=record['kind']
        if kind=='project':continue
        project=record.get('project')
        parent='project:'+project if project in projects else container(other,'Other project work') if project else container(unassigned,'Unassigned')
        group={'idea':('ideas','Ideas'),'assignment':('assignments','Assignments'),'discovery_inquiry':('questions','Questions'),'document':('documents','Documents')}[kind]
        placement=folder(parent,*group)
        role='inquiry' if kind=='discovery_inquiry' else kind
        label=record['text'] if kind=='idea' else record['original_request'] if kind=='assignment' else record['title'] if kind=='document' else record['document']['title']
        ident=role+':'+record['id'];home[ident]='project:'+project if project else unassigned
        add(ident,placement,role,label,'project_desk',dict(kind='desk',record_kind=kind,id=record['id']),
            canonical=ident,owning=True,revision=record['revision'],canonical_home=home[ident],state=record.get('state'),
            description='Current saved record. '+('Project membership is declared by its provider.' if project else 'No project membership has been assigned.'))
    for record in copies:
        parent=folder(container(unassigned,'Unassigned'),'copies','Working copies');ident='copies:'+record['id'];home[ident]=unassigned
        add(ident,parent,'working_copy',Path(record['source']).name,'working_copies',dict(kind='copy',id=record['id']),
            canonical=ident,owning=True,revision=record['revision'],state=record['state'],canonical_home=unassigned,
            description='Existing working copy. No project membership is inferred; source and content freshness have not been rechecked.')
    for record in investigations:
        parent=folder(container(unassigned,'Unassigned'),'questions','Questions');ident='investigation:'+record['id'];home[ident]=unassigned
        add(ident,parent,'investigation',record['question'],'investigations',dict(kind='investigation',id=record['id']),
            canonical=ident,owning=True,state=record['state'],canonical_home=unassigned,
            description='Existing investigation, kept alongside saved inquiries without merging their records.')
    for project in projects.values():
        for link in project.get('links',[]):
            source=link.get('source') or {};address=source.get('address');canonical=(address or '').removeprefix('@')
            parent=folder('project:'+project['id'],link['role'].lower(),LINK_GROUPS.get(link['role'],link['role'].title()))
            label=link.get('text') or (by_id[canonical]['label'] if canonical in by_id else
                                      canonical.partition(':')[2].rpartition('/')[2] if canonical else 'Linked record')
            ident='project-reference:'+project['id']+':'+link['id']
            add(ident,parent,'reference',label,'project_desk',dict(kind='project_link',project=project['id'],link=link['id']),
                canonical=canonical or ident,canonical_home=home.get(canonical),binding_revision=source.get('revision'),
                description='A saved project reference. Its target, project membership and master file are unchanged.')
    from . import memory_cabinet
    remembered=memory_cabinet.snapshot(kernel,principal,limit)
    partial=partial or remembered['partial'];notices.extend(remembered['notices'])
    memory_root=add('memory:root','catalog:ledger' if 'catalog:ledger' in by_id else root['id'],
        'drawer','Graphite memory','slate_memory',description='Existing private directions, task memory and procedures. Stored memory is not engineering proof.')
    if memory_root is not None:
        groups={'feedback':('directions','Directions'),'task':('tasks','Task memory'),'lesson':('procedures','Procedures')}
        for key,label in groups.values():add('memory:'+key,memory_root['id'],'folder_view',label,'slate_memory')
        found_profile=False
        for row in remembered['records']:
            kind=row['kind'];ident='memory:'+kind+':'+row['id'];found_profile=found_profile or kind=='profile'
            parent=memory_root['id'] if kind=='profile' else 'memory:'+groups[kind][0]
            role={'feedback':'memory_direction','task':'memory_task','lesson':'memory_procedure','profile':'memory_profile'}[kind]
            add(ident,parent,role,row['label'],'slate_memory',dict(kind='memory',record_kind=kind,id=row['id']),
                canonical=ident,owning=True,state=row['state'],description=row['origin']+'. Stored owner memory; current source bindings are not inferred.')
        if not found_profile:
            add('memory:profile:current',memory_root['id'],'memory_profile','Personality reference','slate_memory',
                dict(kind='memory',record_kind='profile',id='current'),description='Inspect the existing profile state and open the established import/enable controls.')
    # Normalize missing/limited parents without pretending those records became unassigned.
    for row in nodes:
        if row['parent'] is not None and row['parent'] not in by_id:
            row['parent']=root['id'];row['placement_notice']='Parent outside this bounded projection.';partial=True
    children={row['id']:[] for row in nodes}
    for row in nodes:
        if row['parent'] is not None:children[row['parent']].append(row['id'])
    key=lambda ident:((natural(by_id[ident]['label']) if policy=='natural' else by_id[ident]['label'].casefold()),ident)
    ordered=[];seen=set()
    def visit(ident,depth=0):
        nonlocal partial
        if ident in seen or depth>24:partial=True;return
        seen.add(ident);ordered.append(by_id[ident])
        for child in sorted(children[ident],key=key):visit(child,depth+1)
    visit(root['id'])
    if len(seen)!=len(nodes):partial=True;notices.append('Some placements exceed the bounded hierarchy; existing views remain available.')
    result=dict(schema=SCHEMA,nodes=ordered,root=root['id'],sort_policy=policy,partial=partial,limit=limit,
        notices=sorted(set(notices)),providers=dict(concern_catalog=catalog['state'],project_desk='OWNER_SCOPED',copies='OWNER_SCOPED_STORED_METADATA',
            investigations='OWNER_SCOPED_STORED_METADATA',slate_memory='OWNER_SCOPED_STORED_METADATA'),transfers=TRANSFERS,
        notice='Logical filing only. Source freshness, native execution, jobs and permissions are not inferred from placement.')
    result['signature']=digest(result)
    return result


def catalog_record(kernel,ident):
    path=catalog_file(kernel)
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row;db.execute('BEGIN')
        row=db.execute('SELECT * FROM objects WHERE id=?',(ident,)).fetchone()
        if row is None:raise ValueError('Catalogue record is no longer available')
        note=db.execute('SELECT body,version FROM notes WHERE object_id=?',(ident,)).fetchone()
        return {**dict(row),'note':dict(note) if note else {'body':'','version':0},
                'sources':[dict(r) for r in db.execute('SELECT * FROM sources WHERE object_id=? ORDER BY root,path LIMIT 100',(ident,))]}


def get(kernel,ident,principal):
    from . import project_desk as desk
    model=snapshot(kernel,principal,1000);nodes={r['id']:r for r in model['nodes']}
    if ident not in nodes:raise ValueError('Cabinet record is unavailable in this caller’s bounded view; use the existing workspaces')
    node=nodes[ident];target=node['target'];record=None;actions=[]
    if target is None:
        record={'kind':node['role'],'title':node['label'],'description':node.get('description','Logical filing view.')}
    elif target['kind']=='catalog':record=catalog_record(kernel,target['id'])
    elif target['kind'] in ('desk','project_link'):
        with kernel.db() as db:
            record=desk.read(db,target.get('record_kind','project'),target.get('id',target.get('project')),principal)
        if len(desk.canonical(record).encode())>MAX_BYTES:raise ValueError('Record exceeds the cabinet detail budget; open its existing workspace')
        if target['kind']=='desk' and target['record_kind']=='discovery_inquiry':
            actions.append(dict(label='Check inquiry bindings',operation='discovery.get',arguments={'id':target['id']}))
        if target['kind']=='project_link':
            link=next((r for r in record['links'] if r['id']==target['link']),None)
            if link is None:raise ValueError('Project reference changed; refresh the cabinet')
            record={'kind':'project_reference','project':record['id'],'project_revision':record['revision'],**link}
            address=(link.get('source') or {}).get('address')
            if address:actions.append(dict(label='Read current target',operation='ledger.address.read',arguments={'address':address}))
    elif target['kind']=='copy':
        with kernel.db() as db:
            db.row_factory=sqlite3.Row
            kind='kind' if any(r[1]=='kind' for r in db.execute('PRAGMA table_info(copies)')) else "'file' AS kind"
            row=db.execute('SELECT id,owner,source,work,state,revision,'+kind+' FROM copies WHERE id=? AND owner=?',(target['id'],principal.identity)).fetchone()
            if row is None:raise ValueError('Working copy unavailable to this caller')
            record=dict(row);record['freshness']='NOT_RECHECKED'
        actions.append(dict(label='Recheck working copy',operation='copies.get',arguments={'id':target['id']}))
    elif target['kind']=='memory':
        from . import memory_cabinet
        record,actions=memory_cabinet.detail(kernel,principal,target['record_kind'],target['id'])
    elif target['kind']=='investigation':
        with kernel.db() as db:
            db.row_factory=sqlite3.Row;row=db.execute('SELECT * FROM inv_investigations WHERE id=? AND owner=?',(target['id'],principal.identity)).fetchone()
            if row is None:raise ValueError('Investigation unavailable to this caller')
            record=dict(row)
        actions.append(dict(label='Read investigation sheet',operation='investigation.sheet',arguments={'id':target['id']}))
    return dict(schema='ledger.cabinet-record/1',node=node,record=record,
                children=[r for r in model['nodes'] if r['parent']==ident],actions=actions,
                notice='This reads the existing identity. References do not move or overwrite a master.')


def dispatch(kernel,operation,args,principal):
    return snapshot(kernel,principal,args.get('limit',300)) if operation=='ledger.cabinet' else get(kernel,args['id'],principal)
