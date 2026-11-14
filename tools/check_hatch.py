"""Graphite's release check (run it through tools/check_release.py, the one entry).

Sections, each with its own state:
- runtime: the payload against MANIFEST.json, the Graphite seed's source bindings and the syntax of every Python file
  (tools/check_stage_one.py in a child interpreter);
- registry, settings, adapters: the live program against the recorded registry docs/GRAPHITE_0.1_REGISTRY.json (written by
  tools/record_registry.py). Any difference fails and is listed in words: an added, removed or rescoped operation, a changed
  argument schema (with the properties that changed), an added, removed or changed job tool, a setting definition added, removed,
  changed (with the fields that changed) or moved, and a changed adapter;
- payload_privacy: every shipped file and every member of a shipped .zip, .xlsx or .docx is scanned for developer home paths
  (the build container's root home and per-session temp root included), private keys, provider keys and GitHub tokens; private
  state folders, logs, compiled files, key files, symlinks and unsafe archive members fail. Only the file and the category are
  reported, never the matched value;
- focused_tests (--self-test): every fast current-behaviour tests_integrated module, one module per child, never discover;
- ui_checks (--ui): the UI gate, the offscreen Qt checks, each writing its captures under build/release_check_ui/<check>.

No job, model, provider or native activity. Nothing is written unless --output is given or --ui is passed. A passing check is
integrity, not readiness or acceptance.
"""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
CHECKER='tools/check_hatch.py'
ENTRY='tools/check_release.py'
RECORD='docs/GRAPHITE_0.1_REGISTRY.json'
RECORDER='tools/record_registry.py'
NOTICE='Registration counts and passing checks are not readiness or acceptance.'

# The focused set, defined once: every fast tests_integrated module that tests current behaviour. Each runs on its own, never discover.
FOCUSED_MODULES=(
 # the menu (the cat's programs list), the System menu and session power (HATCH DESK D2), the service cycle, Operations, Explore and the release check itself
 'test_launcher','test_system_menu','test_service_lifecycle','test_operations','test_explore','test_release_check','test_readiness',
 # settings
 'test_settings_registry','test_continue_setting','test_hardware_settings','test_presentation_settings','test_settings_advanced',
 'test_memory_settings','test_model_settings',
 # install and start
 'test_install_media','test_startup_scripts',
 # the desk, the frame, paper, machine, documents and the Graphite words; the right-click menu (HATCH DESK D4)
 'test_desk','test_frame','test_paper','test_machine','test_documents','test_graphite','test_writing_line','test_context_menu',
 # 0.4.9 and 0.5: the drawn glyphs, a tool's face (words or a glyph), Find in what is open, a page in the desk's light
 'test_faces_find_light',
 # 0.6: Stacy's hand: the dial, what always asks, what takes an act back, her trail
 'test_stacy_hand',
 # 0.6.1: the first journey: a starting project in another program (Godot)
 'test_stacy_start',
 # 0.8.0: the Kasandra appearance: the palette at start, stills by the state of the work, her name
 'test_kasandra',
 # 0.8.0: the 35B test campaign's runner (tools/campaign.py): its cases, outcomes, timeouts, resume and summary
 'test_campaign',
 # 0.8.1: the model's memory rules, each against Graphite's own code with simulated readings
 'test_resource_rules',
 # 0.8.2: desk acts: the registry, her hand's rule, the typed door, the playable scene
 'test_desk_acts','test_desk_scenes',
 # the agent loop, condition cards, quiet connections, the Finder's listing, Ingress and Egress, the model turn, files about;
 # the network capability the agent can inspect (HATCH DESK D5)
 'test_tool_selection','test_agent_loop','test_conditions','test_related','test_browse','test_vocabulary','test_model_turn','test_profile_files',
 'test_network_watch',
 # the cabinet, memory, the return thread, the atlases and discovery
 'test_cabinet','test_cabinet_actions','test_memory_cabinet','test_return_thread','test_tool_atlas','test_algorithm_atlas','test_discovery',
 # problems, exact maths, reasoning graphs, adaptive and joined work
 'test_problem','test_exact_math','test_reasoning_graph','test_adaptive_contract','test_joined_work',
 # backup and restore, the Project Desk, slate reasoning, change sets, continuing work, exchange and updates
 'test_workspace_backup','test_project_desk','test_slate_reasoning','test_change_sets','test_continuing_work','test_deployment')
# Kept and runnable by hand; outside the gate because they need optional dependencies, start real processes or load a model.
ON_DEMAND_MODULES={
 'test_exact_math_solvers':'the SymPy and Z3 solvers in a child worker; needs requirements-math.txt'}
# The UI gate: offscreen Qt checks that hold Kernel.launch, Kernel.submit and clip._request and start nothing.
UI_CHECKS=('tools/check_desk_ui.py','tools/check_context_menu_ui.py','tools/check_frame_ui.py','tools/check_hatch_ui.py','tools/check_head_ui.py','tools/check_graphite_ui.py','tools/check_rename_ui.py',
 'tools/check_finder_ui.py','tools/check_paper_ui.py','tools/check_machine_ui.py','tools/check_document_ui.py','tools/check_agent_ui.py',
 'tools/check_continue_ui.py','tools/check_model_turn_ui.py','tools/check_files_about_ui.py','tools/check_service_integration_ui.py',
 'tools/check_hardware_settings_ui.py')
# Each Qt check's capture folder variable; the gate points every one of them under its own capture root.
UI_CAPTURE_ENV={
 'tools/check_desk_ui.py':'ARC_LEDGER_DESK_CAPTURE_DIR','tools/check_context_menu_ui.py':'ARC_LEDGER_CONTEXT_MENU_CAPTURE_DIR','tools/check_frame_ui.py':'ARC_LEDGER_FRAME_CAPTURE_DIR','tools/check_hatch_ui.py':'ARC_LEDGER_HATCH_CAPTURE_DIR',
 'tools/check_head_ui.py':'ARC_LEDGER_HEAD_CAPTURE_DIR','tools/check_graphite_ui.py':'ARC_LEDGER_GRAPHITE_CAPTURE_DIR',
 'tools/check_rename_ui.py':'ARC_LEDGER_RENAME_CAPTURE_DIR','tools/check_finder_ui.py':'ARC_LEDGER_FINDER_CAPTURE_DIR',
 'tools/check_paper_ui.py':'ARC_LEDGER_PAPER_CAPTURE_DIR','tools/check_machine_ui.py':'ARC_LEDGER_MACHINE_CAPTURE_DIR',
 'tools/check_document_ui.py':'ARC_LEDGER_DOCUMENT_CAPTURE_DIR','tools/check_agent_ui.py':'ARC_LEDGER_AGENT_CAPTURE_DIR',
 'tools/check_continue_ui.py':'ARC_LEDGER_CONTINUE_CAPTURE_DIR','tools/check_model_turn_ui.py':'ARC_LEDGER_MODEL_TURN_CAPTURE_DIR',
 'tools/check_files_about_ui.py':'ARC_LEDGER_FILES_ABOUT_CAPTURE_DIR','tools/check_service_integration_ui.py':'ARC_LEDGER_SERVICE_INTEGRATION_CAPTURE_DIR',
 'tools/check_hardware_settings_ui.py':'ARC_LEDGER_HARDWARE_CAPTURE_DIR',
 # on demand
 'tools/check_cabinet_ui.py':'ARC_LEDGER_CABINET_CAPTURE_DIR','tools/check_cabinet_actions_ui.py':'ARC_LEDGER_ACTIONS_CAPTURE_DIR',
 'tools/check_explore_ui.py':'ARC_LEDGER_EXPLORE_CAPTURE_DIR','tools/check_navigation_ui.py':'ARC_LEDGER_NAVIGATION_CAPTURE_DIR',
 'tools/check_operations_ui.py':'ARC_LEDGER_OPERATIONS_CAPTURE_DIR','tools/check_presentation_settings_ui.py':'ARC_LEDGER_PRESENTATION_CAPTURE_DIR',
 'tools/check_return_thread_ui.py':'ARC_LEDGER_RETURN_CAPTURE_DIR','tools/check_memory_cabinet_ui.py':'ARC_LEDGER_MEMORY_CAPTURE_DIR',
 'tools/check_memory_settings_ui.py':'ARC_LEDGER_SETTINGS03_CAPTURE_DIR','tools/check_model_settings_ui.py':'ARC_LEDGER_MODEL_CAPTURE_DIR',
 'tools/check_settings_ui.py':'ARC_LEDGER_SETTINGS_CAPTURE_DIR','tools/check_settings_02_ui.py':'ARC_LEDGER_SETTINGS_CAPTURE_DIR'}
# Kept checks outside the gate, run by hand when their area changes (each holds the same three calls, except the process checks).
ON_DEMAND_CHECKS={
 'tools/check_cabinet_ui.py':'the logical cabinet','tools/check_cabinet_actions_ui.py':'record actions',
 'tools/check_explore_ui.py':'the Explore workspace','tools/check_navigation_ui.py':'navigation across the cabinet and Settings',
 'tools/check_operations_ui.py':'the Operations panel','tools/check_presentation_settings_ui.py':'favorites and catalogue views',
 'tools/check_return_thread_ui.py':'leaving and returning','tools/check_memory_cabinet_ui.py':'owner memory in the cabinet',
 'tools/check_memory_settings_ui.py':'memory settings','tools/check_model_settings_ui.py':'local model launch defaults',
 'tools/check_settings_ui.py':'the settings editor','tools/check_settings_02_ui.py':'session batches, layout and provider preferences',
 'tools/check_continue_service.py':'the real Graphite service carrying work while the window is closed (starts the service)',
 'python -m workbench.database_checks':'Kernel database concurrency with two writer processes',
 'python -m workbench.adaptive_checks':'the investigation coordinator (--live runs named local weights)',
 'python -m workbench.lab_checks':'WASI experiments and KiCad boards (needs wasmtime and KiCad)',
 'python -m workbench.math_checks':'connected maths with SymPy, Z3 and optionally Office',
 'python -m workbench.joined_checks':'joined application, takeover and visible Calc (native jobs)',
 'python -m workbench.joined_model_checks':'the local-model family trials (loads a model)'}
GOOD_STATES={'PASSED'}
# Findings the privacy scan accepts, each with its reason: (shipped file or archive!member, category).
PRIVACY_ALLOWED={
 ('runtimes/python-wasi/python-wasi.zip!lib/python3.13/_sysconfigdata__wasi_wasm32-wasi.py','developer-machine-path'):
  'the build path of the pinned upstream WASI runtime (/home/runner, the machine that built it); the archive is pinned by its sha256',
 ('runtimes/python-wasi/python-wasi.zip!python.wasm','developer-machine-path'):
  'the build path of the pinned upstream WASI runtime (/home/runner, the machine that built it); the archive is pinned by its sha256'}
PRIVATE_PARTS={'.git','.ledger','.venv','__pycache__','.pytest_cache','passes','recovery'}
FORBIDDEN_SUFFIXES=('.log','.pyc','.key','.pem','.p12','.pfx')
ARCHIVE_SUFFIXES=('.zip','.xlsx','.docx')
# Written with \x2f so this file never matches its own patterns. /home/ledger is the sandbox's own home (workbench/workshop_sandbox.py).
# Developer paths: a workspace, a macOS or Linux home, root's home (a folder inside it), and the build container's per-session temp
# root (tmp, then claude- and the user id), which spells the session's own project path into anything that records a file there.
PATTERNS={
 'developer-machine-path':re.compile(rb'\x2fworkspace\x2f(?:scratch|[^\s/]+)/|\x2fUsers\x2f[A-Za-z0-9_.-]+/|\x2fhome\x2f(?!ledger(?:/|["\']))[A-Za-z0-9_.-]+/'
  rb'|\x2froot\x2f[A-Za-z0-9_.-]+/|\x2ftmp\x2fclaude-\d+/'),
 'private-key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'provider-key':re.compile(rb'(?:AIza[0-9A-Za-z_-]{32,}|sk-(?:proj-|ant-)?[A-Za-z0-9_-]{40,})'),
 'github-token':re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})')}


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def inventory_digest(rows):return hashlib.sha256(canonical(rows).encode()).hexdigest()  # the workbench.doctor.inventory formula
def settings_digest(specs):return hashlib.sha256(json.dumps(specs,sort_keys=True).encode()).hexdigest()
def manifest(root=ROOT):
    try:return json.loads((Path(root)/'MANIFEST.json').read_text())
    except (OSError,ValueError):return {}


def tail_json(text):
    """The last JSON object printed to stdout; Qt check tools print their check labels before the report."""
    offsets=[];position=0
    for line in text.splitlines(keepends=True):
        if line.startswith('{'):offsets.append(position)
        position+=len(line)
    for start in reversed(offsets):
        try:return json.loads(text[start:])
        except ValueError:continue
    return None


def parse_unittest(stderr):
    ran=re.search(r'Ran (\d+) tests? in ([\d.]+)s',stderr);verdicts=re.findall(r'^(OK|FAILED)(?: \(([^)]*)\))?\s*$',stderr,re.M)
    detail=dict(re.findall(r'(failures|errors|skipped)=(\d+)',verdicts[-1][1])) if verdicts else {}
    return {'tests':int(ran[1]) if ran else None,'seconds':float(ran[2]) if ran else None,'verdict':verdicts[-1][0] if verdicts else None,
        'failures':int(detail.get('failures',0)),'errors':int(detail.get('errors',0)),'skipped':int(detail.get('skipped',0))}


def run(command,timeout=60,json_output=True,root=ROOT,env=None):
    """Run a shipped script or unittest module in a child interpreter and read its JSON or its unittest summary."""
    child_env=dict(os.environ if env is None else env);child_env['PYTHONDONTWRITEBYTECODE']='1';child_env.setdefault('QT_QPA_PLATFORM','offscreen')
    try:child=subprocess.run([sys.executable,*command],cwd=root,env=child_env,capture_output=True,text=True,timeout=timeout)
    except (OSError,subprocess.SubprocessError) as exc:return {'state':'FAILED','error':str(exc)}
    if json_output:
        result=tail_json(child.stdout)
        if not isinstance(result,dict):result={'state':'FAILED','error':(child.stderr or child.stdout)[-1500:]}
    else:
        result={'state':'PASSED' if child.returncode==0 else 'FAILED',**parse_unittest(child.stderr)}
        if child.returncode:result['error']=child.stderr[-1500:]
    if child.returncode:result['state']='FAILED'
    return result


# The recorded registry ------------------------------------------------------------------------------------------------------

def _names(values):return ', '.join(values)


def _changed(recorded,live):
    """Keys added, removed and changed between two {name: digest} maps."""
    return (sorted(set(live)-set(recorded)),sorted(set(recorded)-set(live)),sorted(k for k in set(recorded)&set(live) if recorded[k]!=live[k]))


def registry_differences(live,record):
    """Operations, job tools and the schema digest, in words."""
    lines=[];ops_live=live['operations'];ops_record=record.get('operations') or {}
    for name in sorted(set(ops_live)-set(ops_record)):lines.append('operation added: '+name+' ('+ops_live[name]['scope']+')')
    for name in sorted(set(ops_record)-set(ops_live)):lines.append('operation removed: '+name)
    for name in sorted(set(ops_live)&set(ops_record)):
        now,then=ops_live[name],ops_record[name]
        if now.get('scope')!=then.get('scope'):lines.append(name+': scope changed from '+str(then.get('scope'))+' to '+str(now.get('scope')))
        if now.get('arguments')!=then.get('arguments'):
            added,removed,changed=_changed(then.get('properties') or {},now.get('properties') or {});parts=[]
            if added:parts.append('properties added: '+_names(added))
            if removed:parts.append('properties removed: '+_names(removed))
            if changed:parts.append('properties changed: '+_names(changed))
            if not parts:parts.append('required, type or bounds changed')
            lines.append(name+': argument schema changed ('+'; '.join(parts)+')')
    tools_live=live['job_tools'];tools_record=record.get('job_tools') or {}
    for name in sorted(set(tools_live)-set(tools_record)):lines.append('job tool added: '+name+' ('+canonical(tools_live[name])+')')
    for name in sorted(set(tools_record)-set(tools_live)):lines.append('job tool removed: '+name)
    for name in sorted(k for k in set(tools_live)&set(tools_record) if tools_live[k]!=tools_record[k]):
        lines.append('job tool '+name+' now runs '+canonical(tools_live[name])+' (recorded '+canonical(tools_record[name])+')')
    if live['schema_digest']!=record.get('schema_digest') and not lines:lines.append('schema digest differs from the record ('+str(record.get('schema_digest'))+')')
    return lines


def settings_differences(live,record):
    """Setting definitions, their order and the settings digest, in words."""
    lines=[];now=live['settings'];then=record.get('settings') or {}
    for key in [k for k in live['settings_order'] if k not in then]:lines.append('setting added: '+key)
    for key in [k for k in (record.get('settings_order') or sorted(then)) if k not in now]:lines.append('setting removed: '+key)
    for key in live['settings_order']:
        if key in then and now[key]['definition']!=then[key].get('definition'):
            added,removed,changed=_changed(then[key].get('fields') or {},now[key]['fields']);parts=[]
            if changed:parts.append('changed: '+_names(changed))
            if added:parts.append('added: '+_names(added))
            if removed:parts.append('removed: '+_names(removed))
            lines.append('setting '+key+' definition changed ('+'; '.join(parts or ['fields unchanged by name'])+')')
    kept=[k for k in live['settings_order'] if k in then];recorded_kept=[k for k in (record.get('settings_order') or []) if k in now]
    if kept!=recorded_kept:lines.append('setting order changed')
    if live['settings_digest']!=record.get('settings_digest') and not lines:lines.append('settings digest differs from the record ('+str(record.get('settings_digest'))+')')
    return lines


def adapter_differences(live,record):
    """The module serving each operation and the store and adapter of each setting, in words. Added or removed operations and
    settings are reported by their own sections; here only the adapter of an operation or setting present in both."""
    lines=[];now=live['adapters'];then=record.get('adapters') or {}
    ops_now,ops_then=now.get('operations') or {},then.get('operations') or {}
    for name in sorted(set(ops_now)&set(ops_then)):
        if ops_now[name]!=ops_then[name]:lines.append(name+' is now served by '+str(ops_now[name])+' (recorded '+str(ops_then[name])+')')
    set_now,set_then=now.get('settings') or {},then.get('settings') or {}
    for key in sorted(set(set_now)&set(set_then)):
        if set_now[key]!=set_then[key]:lines.append('setting '+key+' now reads and writes '+canonical(set_now[key])+' (recorded '+canonical(set_then[key])+')')
    return lines


def record_sections(live,record):
    """The live registry snapshot (tools/record_registry.snapshot) against the record: the registry, settings and adapters sections."""
    if not isinstance(record,dict):
        absent={'state':'FAILED','record':'ABSENT','record_file':RECORD,'differences':['the record '+RECORD+' is absent or unreadable; write it with python3 '+RECORDER]}
        return {'registry':dict(absent),'settings':dict(absent),'adapters':dict(absent)}
    hint='If the change is meant, write the record again with python3 '+RECORDER+' and review its diff.'
    def section(lines,**counts):
        return {'state':'FAILED' if lines else 'PASSED','record':'MATCHES' if not lines else 'DIFFERS','record_file':RECORD,**counts,
            'differences':lines,**({'next_step':hint} if lines else {})}
    counts=record.get('counts') or {}
    return {
     'registry':section(registry_differences(live,record),operations=len(live['operations']),recorded_operations=counts.get('operations'),
        job_tools=len(live['job_tools']),recorded_job_tools=counts.get('job_tools'),schema_digest=live['schema_digest'],recorded_schema_digest=record.get('schema_digest')),
     'settings':section(settings_differences(live,record),count=len(live['settings']),recorded_count=counts.get('settings'),
        digest=live['settings_digest'],recorded_digest=record.get('settings_digest')),
     'adapters':section(adapter_differences(live,record),operations_served=counts.get('adapters'))}


def readable(sections):
    """The differences as plain lines for a person (printed to stderr when anything differs)."""
    lines=[]
    for name,value in sections.items():
        for line in value.get('differences') or []:lines.append(name+': '+line)
    return lines


# Runtime, privacy, focused tests and the UI gate ----------------------------------------------------------------------------

def runtime_section(root=ROOT,runner=None):
    """Payload against MANIFEST.json, the seed's source bindings and syntax (tools/check_stage_one.py in a child)."""
    value=(runner or (lambda:run(['tools/check_stage_one.py'],180,True,root)))()
    errors=value.get('errors');payload=value.get('payload');problems=payload.get('problems',[]) if isinstance(payload,dict) else []
    if value.get('state')!='PASSED' and isinstance(errors,list) and errors and set(errors)<={'payload','source foundation'} and all(str(p).endswith(': changed') for p in problems):
        value['reading']=('EDITED_SOURCES_NOT_YET_PACKAGED: sources differ from MANIFEST.json or the Graphite seed inputs; packaging rewrites the '
            'manifest and rebuilds the seed. This still fails the release check.')
    if value.get('state')!='PASSED':value['state']='FAILED'
    return value


def _scan(name,raw,findings):
    for category,pattern in PATTERNS.items():
        if pattern.search(raw):findings.append({'file':name,'category':category})


def payload_privacy(root=ROOT,files=None,allowed=PRIVACY_ALLOWED):
    """Every shipped file (MANIFEST.json's list unless files is given), nested archives included. Reports file and category only."""
    root=Path(root);names=sorted(files if files is not None else (manifest(root).get('files') or {}))
    findings=[];problems=[];accepted=[];archives=0
    for name in names:
        parts=PurePosixPath(name).parts;path=root/name
        if set(parts)&PRIVATE_PARTS:problems.append(name+': private or local state folder')
        if name.endswith(FORBIDDEN_SUFFIXES):problems.append(name+': logs, compiled files and keys are not release content')
        if path.is_symlink():problems.append(name+': symlink');continue
        if not path.is_file():problems.append(name+': missing');continue
        raw=path.read_bytes();_scan(name,raw,findings)
        if name.endswith(ARCHIVE_SUFFIXES):
            archives+=1
            try:
                with ZipFile(path) as archive:
                    if archive.testzip() is not None:problems.append(name+': archive CRC');continue
                    for entry in archive.infolist():
                        if entry.is_dir():continue
                        if entry.filename.startswith('/') or '..' in PurePosixPath(entry.filename).parts:problems.append(name+': unsafe member path');continue
                        _scan(name+'!'+entry.filename,archive.read(entry),findings)
            except (BadZipFile,OSError) as exc:problems.append(name+': unreadable archive ('+type(exc).__name__+')')
    kept=[]
    for finding in findings:
        reason=allowed.get((finding['file'],finding['category']))
        if reason:accepted.append({**finding,'reason':reason})
        else:kept.append(finding)
    problems+=[item['file']+': '+item['category'] for item in kept]
    return {'state':'FAILED' if problems or not names else 'PASSED','files_scanned':len(names),'archives_scanned':archives,
        'patterns':sorted(PATTERNS),'findings':kept,'accepted':accepted,'problems':problems if names else ['no shipped file list (MANIFEST.json)'],
        'reading':'Values are never printed: only the file and the category.'}


def focused_tests(modules=FOCUSED_MODULES,runner=None,root=ROOT,timeout=600):
    """Each focused module on its own child; a listed module that is not in the tree is ABSENT and fails the section."""
    runner=runner or (lambda command,limit,json_output:run(command,limit,json_output,root));rows={};tests=failures=errors=0
    for name in modules:
        if not (Path(root)/'tests_integrated'/(name+'.py')).is_file():rows[name]={'state':'ABSENT'};continue
        rows[name]=runner(['-m','unittest','-v','tests_integrated.'+name],timeout,False)
        tests+=rows[name].get('tests') or 0;failures+=rows[name].get('failures') or 0;errors+=rows[name].get('errors') or 0
    present=[name for name in modules if rows[name]['state']!='ABSENT'];absent=[name for name in modules if rows[name]['state']=='ABSENT']
    state='NOTHING_RUN' if not present else 'PASSED' if not absent and all(rows[name]['state']=='PASSED' for name in present) else 'FAILED'
    return {'state':state,'invocation':'python -B -m unittest -v tests_integrated.<module>, one module per child','modules':rows,
        'present':present,'absent':absent,'tests':tests,'failures':failures,'errors':errors,'on_demand':dict(ON_DEMAND_MODULES)}


def ui_checks(scripts=UI_CHECKS,runner=None,root=ROOT,timeout=600,capture_root=None):
    """The UI gate, only when asked. Every check's capture folder variable points under capture_root (build/release_check_ui by default)."""
    capture_root=Path(capture_root) if capture_root else Path(root)/'build/release_check_ui'
    def default_runner(command,limit,json_output,env):return run(command,limit,json_output,root,env)
    runner=runner or default_runner;rows={}
    for script in scripts:
        target=capture_root/Path(script).stem
        if not (Path(root)/script).is_file():rows[script]={'state':'ABSENT'};continue
        env=dict(os.environ);variable=UI_CAPTURE_ENV.get(script)
        if variable:env[variable]=str(target)
        value=runner([script],timeout,True,env)
        rows[script]={'state':value.get('state','FAILED'),'checks':len(value['checks']) if isinstance(value.get('checks'),list) else value.get('checks'),
            'captures':[row.get('file',row) if isinstance(row,dict) else row for row in value['captures']] if isinstance(value.get('captures'),list) else None,
            'capture_variable':variable,'capture_dir':str(target.relative_to(root)) if target.is_relative_to(root) else str(target),
            **({'error':value['error']} if 'error' in value else {})}
    present=[name for name in scripts if rows[name]['state']!='ABSENT'];absent=[name for name in scripts if rows[name]['state']=='ABSENT']
    state='NOTHING_RUN' if not present else 'PASSED' if not absent and all(rows[name]['state']=='PASSED' for name in present) else 'FAILED'
    return {'state':state,'mode':'QT_QPA_PLATFORM=offscreen unless already set','capture_root':str(capture_root),'scripts':rows,
        'absent':absent,'on_demand':dict(ON_DEMAND_CHECKS)}


def release(root=ROOT):
    """What is being checked: the release named by MANIFEST.json and workbench/version.py."""
    value=manifest(root);info={'manifest_release':value.get('graphite_release'),'manifest_version':value.get('version'),'record':RECORD}
    try:
        from workbench import version
        info.update(name=version.NAME,short=version.SHORT,title=version.title())
    except (ImportError,AttributeError) as exc:info['version_error']=str(exc)
    return info


def report(self_test=False,ui=False,root=ROOT):
    result={'state':'PASSED','checker':CHECKER,'entry':ENTRY,'release':release(root),'notice':NOTICE}
    result['runtime']=runtime_section(root)
    try:
        sys.path.insert(0,str(Path(root)/'tools'))
        import record_registry
        live=record_registry.snapshot();record=record_registry.read(root)
        result.update(record_sections(live,record))
    except (OSError,ValueError,KeyError,TypeError,ImportError) as exc:
        for key in ('registry','settings','adapters'):result[key]={'state':'FAILED','reason':type(exc).__name__+': '+str(exc)}
    result['payload_privacy']=payload_privacy(root)
    if self_test:result['focused_tests']=focused_tests(root=root)
    if ui:result['ui_checks']=ui_checks(root=root)
    failed=[name for name,value in result.items() if isinstance(value,dict) and 'state' in value and value['state'] not in GOOD_STATES]
    result['state']='PASSED' if not failed else 'FAILED';result['failed_sections']=failed
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(prog='check_release.py',description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--self-test',action='store_true',help='Also run every focused tests_integrated module, one module per child')
    parser.add_argument('--ui',action='store_true',help='Also run the UI gate offscreen; captures go under build/release_check_ui/<check>')
    parser.add_argument('--runtime',action='store_true',help='Accepted and ignored: runtime integrity is always checked')
    parser.add_argument('--output',type=Path,help='Also write the JSON report to this file')
    args,extras=parser.parse_known_args(argv)
    native=[flag for flag in extras if flag.split('=')[0] in ('--native','--visible','--keep')]
    if native:  # the native and visible trials start real jobs; they are not part of the release check
        print(json.dumps({'state':'FAILED','checker':CHECKER,'native_flags':native,
            'reason':'Native and visible trials start real jobs and are not part of the release check; run python -m workbench.joined_checks '
                '--keep K --output O --visible (or --coordinator-takeover) by hand.'},indent=2));return 1
    if extras:parser.error('unrecognized arguments: '+' '.join(extras))
    result=report(args.self_test,args.ui);text=json.dumps(result,indent=2)
    if args.output:args.output.write_text(text+'\n')
    differences=readable({k:result[k] for k in ('registry','settings','adapters') if isinstance(result.get(k),dict)})
    if differences:print('The live program differs from '+RECORD+':\n  '+'\n  '.join(differences),file=sys.stderr)
    print(text);return 0 if result['state']=='PASSED' else 1


if __name__=='__main__':raise SystemExit(main())
