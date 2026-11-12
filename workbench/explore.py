"""Passive workshop projection over the canonical operations and method atlases.

Routes describe existing views. Nothing in this module dispatches a candidate,
starts a tool, creates a record, or treats a suggestion as permission.
"""
from __future__ import annotations
import json,re
from . import capability_catalog, algorithm_atlas, cabinet, project_context

TEXT={'type':'string','maxLength':180}
FIELDS={'ledger.explore':({'query':TEXT,'context':cabinet.TEXT,
    'kind':{'type':'string','enum':['ALL','INSTRUMENT','METHOD','OPERATION','JOB_TOOL']},
    'limit':{'type':'integer','minimum':1,'maximum':100},'offset':{'type':'integer','minimum':0,'maximum':10000}},[])}
SCOPES={op:'read' for op in FIELDS}

# Presentation adapters only. Operation IDs, effects, schemas and prerequisites
# always come from the original catalogue; no second capability registry.
# Hatch lists these groups in this order; Explore searches the same rows.
GROUPS=('Work','Reason','Instruments','Programs','Knowledge','Configuration')
# The last field is the presentation kind (INTEGRATION_CONTRACTS capability_presentation, DESKTOP-01 HT02):
#   workspace   a Ledger-built workspace;
#   checks      Ledger's checks, profiles or output controls for a native tool: the tool's own editor never opens;
#   operations  Ledger controls over a restricted set of application operations: no application window is embedded.
KINDS=('workspace','checks','operations')
VIEWS=[
 ('projects','Projects & ideas','Keep an idea, develop a project, or prepare an assignment.','Work','project_desk','project_desk_qt.py','ProjectDeskTab',('projects.','ideas.','assignments.'),'write brainstorm plan intent','workspace'),
 ('inquiries','Questions & inquiries','Develop a question with sources, assumptions and checked observations.','Work','discovery','discovery_qt.py','DiscoveryTab',('discovery.',),'question test idea hypothesis evidence experiment','workspace'),
 ('calculate','Calculate & compare','Use the existing problem sheet, exact calculator and What if graph.','Reason','calculate','calculator_qt.py','ProjectDeskTab',('math.',),'numbers units quantity budget capacity equation graph what if','workspace'),
 ('laboratory','Laboratory','Open the existing protected experiments and connected-work panes.','Reason','laboratory','lab_qt.py','ProjectDeskTab',('lab.','reasons.','methods.'),'python experiment code test idea investigate simulation','workspace'),
 ('methods','Methods & theory','Inspect implemented profiles and clearly marked reference methods.','Reason','algorithms','algorithm_atlas_qt.py','AlgorithmAtlasTab',('algo.',),'algorithm mathematics optimization shortest path statistics proof','workspace'),
 ('tools','Tool Atlas','Inspect registered operation contracts, prerequisites and tool passports.','Instruments','atlas','tool_atlas_qt.py','ToolAtlasTab',('atlas.',),'capability application calc python kicad ngspice verilog','workspace'),
 ('office','Office & incoming work','Open existing receiving, document and working-copy controls.','Work','office','office_building_qt.py','OfficeBuildingTab',('office.','receiving.'),'calc writer spreadsheet document import incoming','operations'),
 ('files','Files & working copies','Read working material and inspect controlled copies and versions.','Work','files','files_qt.py','FilesTab',('files.','copies.'),'file originals master copies export version compare','workspace'),
 ('documents','Documents','Write and format a page; Graphite edits the same page when you ask.','Work','documents','document_qt.py','DocumentsTab',('documents.',),'write document page letter essay bold italic heading format text','workspace'),
 ('investigations','Investigations & assignments','Follow what Graphite is working on: the question, every recorded step, findings, open conditions; pause, resume, stop.','Work','investigations','investigations_qt.py','InvestigationTab',('investigation.','agent.'),'assignment investigation slate working findings steps evidence resume stop','workspace'),
 ('agenda','Operations agenda','Open Graphite’s existing ordered work and priority controls.','Work','agenda','agenda_qt.py','AgendaTab',('agenda.',),'queue priority schedule nice jobs work','workspace'),
 ('brain','Local model','Inspect or configure the existing local inference capability.','Configuration','brain','brain_qt.py','BrainTab',('brain.',),'slate model weights gguf offline inference','workspace'),
 ('knowledge','Sources & knowledge','Search the existing source-linked knowledge records.','Knowledge','sources','knowledge_qt.py','KnowledgeTab',('knowledge.',),'sources study library documents facts','workspace'),
 ('references','References','Open the current reference library and its source-reading controls.','Knowledge','references','reference_qt.py','ReferenceTab',('references.',),'datasheet vendor chinese manual original','workspace'),
 ('memory','Graphite memory','Inspect saved directions, tasks, procedures and learning review.','Knowledge','memory','memory_qt.py','MemoryTab',('memory.',),'remember lessons procedure preference learning','workspace'),
 ('settings','Graphite settings','Open the shared settings hierarchy and its highlighted editors.','Configuration','settings','settings_qt.py','SettingsTab',('ledger.settings',),'settings font appearance rules configuration','workspace'),
 ('activity','Activity & receipts','Inspect the existing work trail, jobs and retained outcomes.','Work','trail','work_trail_qt.py','WorkTrailTab',('ledger.activity','ledger.trail.','jobs.'),'jobs receipts history audit progress','workspace'),
 # Programs open Graphite rooms. Native operations are deliberate actions inside those rooms.
 ('mail','Mail','Read saved mail, prepare a local draft, or open the message in Thunderbird.','Programs','program:mail','program_rooms_qt.py','MailRoom',('programs.mail.',),'email eml attachment correspondence reply thunderbird','operations'),
 ('blender','Blender','Inspect a blend file, check its scenes with Blender, or open the full editor.','Programs','program:blender','program_rooms_qt.py','BlenderRoom',('programs.blender.',),'3d mesh scene modeling enclosure','operations'),
 ('godot','Godot','Inspect a project and choose a scene to play or edit in Godot.','Programs','program:godot','program_rooms_qt.py','GodotRoom',('programs.godot.',),'game scene play editor gdscript','operations'),
 ('transfer','Transfer','List an anonymous FTP directory and retrieve a file into Graphite Files.','Programs','program:transfer','program_rooms_qt.py','TransferRoom',('programs.transfer.',),'ftp curl download network file','operations'),
 ('cartridge','Cartridge Bay','Inspect a local NES cartridge image and start a detected RetroArch core.','Programs','program:cartridge','program_rooms_qt.py','CartridgeRoom',('programs.cartridge.',),'nintendo nes rom emulation retroarch game','operations'),
 ('inkscape','Inkscape','Inspect a self-contained SVG, render a PNG proof, or open the full editor.','Programs','program:inkscape','program_rooms_qt.py','InkscapeRoom',('programs.inkscape.',),'svg vector panel drawing art png export proof','operations'),
 ('media','Media Bench','Inspect audio and video with FFprobe and save a timed excerpt with FFmpeg.','Programs','program:media','program_rooms_qt.py','MediaRoom',('programs.media.',),'audio video wav ffmpeg ffprobe mp4 trim clip playback','operations'),
 ('freecad','FreeCAD','Inspect an FCStd file, measure stored geometry, export a selected shape, or open the editor.','Programs','program:freecad','program_rooms_qt.py','FreeCADRoom',('programs.freecad.',),'cad model solids enclosure step dimensions mechanical','operations'),
 ('print','Print Proof','Turn a local PNG into a Letter or A4 review PDF with a source hash.','Programs','program:print','program_rooms_qt.py','PrintProofRoom',('programs.print.',),'print proof pdf paper a4 letter faceplate review','operations'),
 ('delivery','Delivery','Review selected local files, assemble a ZIP, and verify it against its manifest.','Programs','program:delivery','program_rooms_qt.py','DeliveryRoom',('programs.delivery.',),'package review zip verify manifest handoff archive','operations'),
 ('kicad','KiCad checks','Open the existing KiCad design-rule and qualification checks for the attached project.','Programs','cad','kicad_qt.py','KiCadTab',('cad.',),'kicad pcb drc circuit design rules','checks'),
 ('kibot','KiBot outputs','Open the existing KiBot BOM and fabrication output controls.','Programs','kibot','kibot_qt.py','KiBotTab',('kibot.',),'kibot bom fabrication gerber outputs','checks'),
 ('spice','ngspice profiles','Open the existing ngspice circuit simulation profiles.','Programs','spice','spice_qt.py','SpiceTab',('spice.',),'ngspice spice circuit simulation analog','checks'),
 ('yosys','Yosys synthesis','Open the existing RTL synthesis profiles and support checks.','Programs','yosys','yosys_qt.py','YosysTab',('yosys.',),'yosys rtl synthesis fpga','checks'),
 ('fpga','nextpnr & Trellis','Open the existing nextpnr routing and Trellis packing controls.','Programs','implementation','pnr_qt.py','ImplementationTab',('nextpnr.','trellis.'),'nextpnr trellis fpga place route bitstream pack','checks'),
 ('hdl','HDL simulation checks','Open the existing Icarus, Verilator and Surfer trace controls.','Programs','hdl','hdl_qt.py','HdlTab',('hdl.','icarus.','verilator.','surfer.'),'verilog simulation icarus verilator surfer trace','checks'),
]
# The native program each checks row is about, for the words "its own editor does not open".
NATIVE_NAMES={'kicad':'KiCad','kibot':'KiBot','spice':'ngspice','yosys':'Yosys','fpga':'nextpnr and Trellis','hdl':'Icarus, Verilator and Surfer'}
SLATE_OPERATIONS_SHOWN=6


def presentation(ident,kind):
    """What actually opens, in one truthful sentence (the contract's human_route/presentation mode)."""
    if kind=='checks':
        name=NATIVE_NAMES[ident]
        return "Graphite's %s checks and controls in a Graphite workspace; %s itself is not opened"%(name,name)
    if kind=='operations':return 'Graphite workspace over a restricted set of application operations; no application window is embedded'
    return 'Graphite workspace'
# A route that opens more than its own module is available only when every opened module is present.
REQUIRES={'calculate':('project_desk_qt.py','problem_qt.py','calculator_qt.py'),'laboratory':('project_desk_qt.py','problem_qt.py','lab_qt.py')}
# Views whose factory shows the existing "project required" explanation in a bare program.
PROJECT_REQUIRED=('kicad',)
ACTIVE=('Queued','Running','Waiting for Approval','Paused','Waiting for Agent','Waiting for Execution Approval','Waiting for Provider')
ATTENTION=('Interrupted',)
SETUP_STATES={'MISSING','INVALID','INCOMPATIBLE'}


STOP_WORDS={'i','want','to','a','an','the','my','me','with','for','of','can','how','do','let','lets','would','like','help','what'}


def matches(query,*values):
    text=' '.join(str(value) for value in values).casefold()
    terms=[word for word in re.findall(r'[\w.-]+',query.casefold()) if word not in STOP_WORDS]
    return all(word in text for word in terms)


def job_counts(kernel,principal):
    """Owner-filtered bounded stored counters, never process or job control."""
    jobs=[];partial=False;states=ACTIVE+ATTENTION
    with kernel.db() as db:
        rows=db.execute('SELECT state,length(CAST(payload AS BLOB)),CASE WHEN length(CAST(payload AS BLOB))<=65536 THEN payload ELSE NULL END FROM jobs WHERE owner=? AND state IN ('+
            ','.join('?' for _ in states)+') ORDER BY rowid DESC LIMIT 501',(principal.identity,*states)).fetchall()
        partial=len(rows)>500
        for state,size,payload in rows[:500]:
            if size>65536:partial=True;continue
            try:
                value=json.loads(payload);tool=value.get('tool')
                if isinstance(tool,str):jobs.append((state,tool))
            except (ValueError,AttributeError):partial=True
    return jobs,partial


def selected_context(kernel,ident,principal):
    if not ident:return None,[],None
    try:
        value=cabinet.get(kernel,ident,principal);node=value['node']
    except (ValueError,OSError) as exc:
        # Do not return a guessed private ID or the underlying provider error.
        return None,[],'The selected record is unavailable. Refresh its cabinet view.'
    return {key:node.get(key) for key in ('id','label','role','provider','revision','canonical_id')},value['actions'],None


def suggestions(selected):
    if selected is None:return []
    role=selected['role']
    if role.startswith('memory_'):
        choices=(('memory','Open the existing memory, profile and review controls.'),('settings','Inspect the shared Graphite settings.'))
    elif role=='document':
        choices=(('documents','Open the page and keep writing; Graphite edits it with you.'),('inquiries','Turn the writing into a testable question.'))
    elif role in ('idea','project'):
        choices=(('documents','Write the idea out as a page you and Graphite can edit.'),('inquiries','Turn this saved idea into a testable question.'),('calculate','Give the idea quantities, units and constraints.'),('laboratory','Explore the existing experiment and connected-work controls.'))
    elif role in ('inquiry','investigation'):
        choices=(('methods','Inspect methods and their stated assumptions.'),('tools','Inspect the tools before choosing a check.'))
    elif role=='working_copy':
        choices=(('files','Inspect the existing copy and its versions.'),('office','Use the established document and working-copy controls.'))
    else:
        choices=(('projects','Develop the saved work through the existing project controls.'),('methods','Explore methods that could fit this work.'))
    return [dict(id=ident,reason=reason,basis='SELECTED_RECORD_KIND',record=selected['id']) for ident,reason in choices]


def snapshot(kernel,principal,query='',context=None,kind='ALL',limit=60,offset=0):
    from .tool_atlas import WORDS
    selected,actions,context_notice=selected_context(kernel,context,principal)
    notices=[context_notice] if context_notice else []
    catalogue=capability_catalog.catalogue(kernel,principal)
    jobs,counts_partial=job_counts(kernel,principal)
    if counts_partial:notices.append('Active-job counters are bounded; use the existing job controls for complete records.')
    detached=project_context.detached(kernel.root)
    entries=[];instruments=[]
    for ident,title,description,group,route,module,view_class,prefixes,words,mode in VIEWS:
        operations=[r for r in catalogue['operations'] if r['operation'].startswith(prefixes)]
        tools=[r for r in catalogue['tools'] if r['tool'].startswith(prefixes)]
        sources=[capability_catalog.source(kernel.root,'workbench/'+name) for name in REQUIRES.get(ident,(module,))]
        missing=[s['path'] for s in sources if s['state']!='PRESENT']
        source=next((s for s in sources if s['state']!='PRESENT'),sources[0])
        available=not missing and bool(operations)
        native_states={r['native']['state'] for r in tools}
        tool_status=('Needs setup' if native_states & SETUP_STATES else
                     'Detected · checks remain' if 'DETECTED' in native_states else
                     'Not assessed' if tools else 'Use existing controls')
        setup_needed=sorted({r['native'].get('command') or r['native']['reason'] for r in tools if r['native']['state'] in SETUP_STATES})
        own_jobs=[state for state,tool in jobs if tool.startswith(prefixes)]
        entry=dict(id='instrument:'+ident,key=ident,kind='INSTRUMENT',title=title,description=description,group=group,
            destination=route,view_class=view_class,view_available=available,view_state='Workspace available' if available else 'View unavailable',
            # The presentation contract: what opens, by which human route, and which registered operations Slate has for the family.
            presentation_kind=mode,presentation=presentation(ident,mode),human_route='Menu ▸ '+group+' ▸ '+title+' (also Explore)',
            slate_operations=[dict(operation=r['operation'],scope=r['scope']) for r in operations[:SLATE_OPERATIONS_SHOWN]],
            tool_status=tool_status,setup_needed=setup_needed,operations=len(operations),job_tools=len(tools),
            active_jobs=sum(state in ACTIVE for state in own_jobs),
            running_jobs=sum(state=='Running' for state in own_jobs),queued_jobs=sum(state=='Queued' for state in own_jobs),
            interrupted_jobs=sum(state in ATTENTION for state in own_jobs),
            qualification='UNASSESSED',source=source,sources=sources,missing_modules=missing,
            project_required=ident in PROJECT_REQUIRED and detached,words=words,
            notice='Opening this view does not run a tool. Individual operation checks and permissions still apply.')
        instruments.append(entry)
        if matches(query,title,description,words,*prefixes):entries.append(entry)
    methods=[]
    try:
        result=algorithm_atlas.dispatch(kernel,'algo.lookup',{},principal)
        for method in result['entries']:
            if not matches(query,method['id'],method['title'],method['domain'],method['task']):continue
            implementation=method['implementation']['state']
            row=dict(id='method:'+method['id'],key=method['id'],kind='METHOD',title=method['title'],description=method['domain'],
                implementation=implementation,callable=implementation=='LINKED',qualification='UNASSESSED',
                status={'NOT_IMPLEMENTED':'Reference only','DEPENDENCY_UNAVAILABLE':'Needs dependency',
                        'SOURCE_MISSING':'Source unavailable','CONTRACT_MISSING':'Contract unavailable',
                        'LINKED':'Linked · checks remain'}.get(implementation,'Not assessed'),
                catalog_digest=result['catalog_digest'],operations=method['implementation']['operations'],
                notice='Inspection only. Linked methods retain their declared profiles, admission checks and execution routes.')
            methods.append(row);entries.append(row)
    except (ValueError,OSError,KeyError) as exc:
        notices.append('The method catalogue is unavailable; instruments and registered operations remain accessible.')
    for row in catalogue['operations']:
        op=row['operation'];words=WORDS.get(op.split('.')[0],'')
        if not matches(query,op,words,row['scope']):continue
        entries.append(dict(id='operation:'+op,key=op,kind='OPERATION',title=op,description=words,
            required_scope=row['scope'],assessment=row['assessment'],status=row['summary'],
            required_arguments=row['arguments']['required'],qualification='UNASSESSED',inspect_only=True))
    for row in catalogue['tools']:
        name=row['tool'];words=WORDS.get(name.split('.')[0],'')
        if not matches(query,name,words):continue
        entries.append(dict(id='tool:'+name,key=name,kind='JOB_TOOL',title=name,description=words,
            assessment=row['assessment'],status=row['summary'],native=row['native'],qualification='UNASSESSED',inspect_only=True))
    if kind!='ALL':entries=[row for row in entries if row['kind']==kind]
    # Instrument navigation comes first, then methods, then exact registered contracts.
    rank={'INSTRUMENT':0,'METHOD':1,'OPERATION':2,'JOB_TOOL':3}
    entries.sort(key=lambda r:(rank[r['kind']],r['title'].casefold(),r['id']))
    return dict(schema='ledger.explore/1',entries=entries[offset:offset+limit],matches=len(entries),offset=offset,
        has_more=offset+limit<len(entries),instruments=instruments,context=selected,context_actions=actions,
        suggestions=suggestions(selected),notices=notices,job_counts_partial=counts_partial,
        registered_operations=catalogue['registered_operations'],registered_job_tools=catalogue['registered_job_tools'],
        model_calls=0,network_calls=0,native_invocations=0,
        notice='Suggestions use the selected record kind. They do not infer a method fit, grant permission, or execute work.')


def dispatch(kernel,operation,args,principal):return snapshot(kernel,principal,**args)
