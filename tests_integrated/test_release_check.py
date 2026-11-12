"""Graphite's release check: the recorded registry and its readable differences, runtime integrity, the payload privacy scan,
the focused set, the UI gate and the one entry (tools/check_release.py). Fixtures for every rule; the live tree against the record."""
import contextlib,copy,io,json,os,re,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from tools import check_hatch as checker
from tools import record_registry as recorder

ROOT=checker.ROOT


def op(name,scope='execute',properties=None,required=()):
    return {'operation':name,'scope':scope,'arguments':{'type':'object','properties':copy.deepcopy(properties or {}),'required':list(required),'additionalProperties':False}}


def inventory(rows):
    rows=sorted(copy.deepcopy(rows),key=lambda row:row['operation'])
    return {'operations':rows,'operation_count':len(rows),'schema_digest':checker.inventory_digest(rows)}


NAV=op('ledger.navigate',properties={'destination':{'type':'string','enum':['home','settings']}},required=['destination'])
SET=op('ledger.settings.set',properties={'key':{'type':'string'},'value':{}},required=['key','value'])
PLAIN=op('ledger.context',scope='read')
ROWS=[NAV,SET,PLAIN]
TOOLS={'brain.activate':('workbench.local_brain',),'kicad.drc':('workbench.kicad_tools',)}
HANDLERS={'ledger.navigate':{'path':'workbench/engineering_kernel.py','symbol':'Kernel._dispatch'},
    'ledger.settings.set':{'path':'workbench/ledger_control.py','symbol':'dispatch'},'ledger.context':{'path':'workbench/engineering_kernel.py','symbol':'Kernel._dispatch'}}
SPECS=[{'key':'reading.code_pt','label':'Code text (pt)','type':'integer','default':14,'root':'Ledger','store':'Session reading_profile'},
    {'key':'catalog.view','label':'Existing catalogue view','type':'string','default':'works','root':'Slate','store':'Existing Concern catalogue preferences.view'}]


def sources(rows=ROWS,tools=TOOLS,handlers=HANDLERS,specs=SPECS):
    return inventory(rows),copy.deepcopy(tools),copy.deepcopy(handlers),copy.deepcopy(specs)


def compare(record,**live):
    return checker.record_sections(recorder.snapshot(sources(**live)),record)


class RecordedRegistry(unittest.TestCase):
    def setUp(self):self.record=recorder.snapshot(sources())

    def test_an_identical_tree_matches_the_record_in_every_section(self):
        value=compare(self.record)
        self.assertEqual({k:(v['state'],v['record'],v['differences']) for k,v in value.items()},
            {k:('PASSED','MATCHES',[]) for k in ('registry','settings','adapters')})
        self.assertEqual((value['registry']['operations'],value['registry']['recorded_operations'],value['settings']['count']),(3,3,2))
        self.assertEqual(checker.readable(value),[])

    def test_the_record_is_deterministic_and_holds_digests_not_schemas(self):
        again=recorder.snapshot(sources());self.assertEqual(recorder.text(self.record),recorder.text(again))
        row=self.record['operations']['ledger.navigate']
        self.assertEqual(set(row),{'scope','arguments','properties'});self.assertEqual(set(row['properties']),{'destination'})
        self.assertEqual(row['arguments'],recorder.sha(NAV['arguments']));self.assertNotIn('enum',recorder.text(self.record))
        self.assertEqual(self.record['schema_digest'],checker.inventory_digest(inventory(ROWS)['operations']))
        self.assertEqual(self.record['settings_digest'],checker.settings_digest(SPECS));self.assertEqual(self.record['settings_order'],['reading.code_pt','catalog.view'])
        self.assertEqual(self.record['adapters']['operations']['ledger.settings.set'],'workbench/ledger_control.py#dispatch')
        self.assertEqual(self.record['job_tools'],{'brain.activate':['workbench.local_brain'],'kicad.drc':['workbench.kicad_tools']})
        self.assertEqual(set(self.record),{'schema','release','generated_by','formulas','counts','schema_digest','settings_digest','operations','job_tools',
            'settings_order','settings','adapters'})  # no time stamp: an unchanged tree writes the same bytes

    def test_a_changed_argument_schema_fails_and_names_the_property(self):
        nav=copy.deepcopy(NAV);nav['arguments']['properties']['destination']['enum'].append('atlas')
        value=compare(self.record,rows=[nav,SET,PLAIN])
        self.assertEqual(value['registry']['state'],'FAILED');self.assertEqual(value['registry']['record'],'DIFFERS')
        self.assertEqual(value['registry']['differences'],['ledger.navigate: argument schema changed (properties changed: destination)'])
        self.assertIn('tools/record_registry.py',value['registry']['next_step'])
        self.assertEqual((value['settings']['state'],value['adapters']['state']),('PASSED','PASSED'))
        nav=copy.deepcopy(NAV);nav['arguments']['properties']['note']={'type':'string'}
        self.assertEqual(compare(self.record,rows=[nav,SET,PLAIN])['registry']['differences'],['ledger.navigate: argument schema changed (properties added: note)'])
        nav=copy.deepcopy(NAV);nav['arguments']['required']=[]
        self.assertEqual(compare(self.record,rows=[nav,SET,PLAIN])['registry']['differences'],['ledger.navigate: argument schema changed (required, type or bounds changed)'])
        setting=copy.deepcopy(SET);del setting['arguments']['properties']['value']
        self.assertIn('properties removed: value',compare(self.record,rows=[NAV,setting,PLAIN])['registry']['differences'][0])

    def test_added_removed_and_rescoped_operations_and_job_tools_fail(self):
        value=compare(self.record,rows=ROWS+[op('ledger.machine',scope='read')])['registry']
        self.assertEqual((value['state'],value['differences']),('FAILED',['operation added: ledger.machine (read)']))
        self.assertEqual(compare(self.record,rows=[NAV,SET])['registry']['differences'],['operation removed: ledger.context'])
        changed=copy.deepcopy(PLAIN);changed['scope']='execute'
        self.assertEqual(compare(self.record,rows=[NAV,SET,changed])['registry']['differences'],['ledger.context: scope changed from read to execute'])
        self.assertEqual(compare(self.record,tools={**TOOLS,'new.tool':('workbench.x',)})['registry']['differences'],['job tool added: new.tool (["workbench.x"])'])
        self.assertEqual(compare(self.record,tools={'brain.activate':TOOLS['brain.activate']})['registry']['differences'],['job tool removed: kicad.drc'])
        self.assertEqual(compare(self.record,tools={**TOOLS,'kicad.drc':('workbench.other',)})['registry']['differences'],
            ['job tool kicad.drc now runs ["workbench.other"] (recorded ["workbench.kicad_tools"])'])

    def test_a_removed_changed_added_or_moved_setting_fails_and_names_the_fields(self):
        value=compare(self.record,specs=SPECS[:1])['settings']
        self.assertEqual((value['state'],value['differences']),('FAILED',['setting removed: catalog.view']))
        changed=copy.deepcopy(SPECS);changed[0]['label']='Code text';changed[0]['default']=15
        self.assertEqual(compare(self.record,specs=changed)['settings']['differences'],['setting reading.code_pt definition changed (changed: default, label)'])
        changed=copy.deepcopy(SPECS);changed[1]['choices']=['works']
        self.assertEqual(compare(self.record,specs=changed)['settings']['differences'],['setting catalog.view definition changed (added: choices)'])
        added=copy.deepcopy(SPECS)+[{'key':'appearance.writing_marker','label':'Writing marker','type':'boolean','default':True,'root':'Ledger','store':'Session writing_marker'}]
        self.assertEqual(compare(self.record,specs=added)['settings']['differences'],['setting added: appearance.writing_marker'])
        self.assertEqual(compare(self.record,specs=list(reversed(SPECS)))['settings']['differences'],['setting order changed'])
        self.assertEqual(compare(self.record,specs=added)['registry']['state'],'PASSED')

    def test_a_changed_adapter_fails_and_says_what_serves_it_now(self):
        handlers=copy.deepcopy(HANDLERS);handlers['ledger.context']={'path':'workbench/project_context.py','symbol':'dispatch'}
        value=compare(self.record,handlers=handlers)
        self.assertEqual(value['adapters']['differences'],['ledger.context is now served by workbench/project_context.py#dispatch (recorded workbench/engineering_kernel.py#Kernel._dispatch)'])
        self.assertEqual((value['registry']['state'],value['settings']['state']),('PASSED','PASSED'))
        specs=copy.deepcopy(SPECS);specs[0]['store']='Kernel settings: ledger.reading.code_pt'
        value=compare(self.record,specs=specs)
        self.assertEqual(value['adapters']['differences'],['setting reading.code_pt now reads and writes {"adapter":null,"store":"Kernel settings: ledger.reading.code_pt"} (recorded {"adapter":null,"store":"Session reading_profile"})'])
        self.assertEqual(value['settings']['state'],'FAILED')  # the store is part of the definition too
        self.assertEqual(checker.readable(value)[0][:10],'settings: ')

    def test_an_absent_record_fails_every_section_with_the_way_to_write_it(self):
        value=checker.record_sections(recorder.snapshot(sources()),None)
        self.assertTrue(all(v['state']=='FAILED' and v['record']=='ABSENT' and 'python3 tools/record_registry.py' in v['differences'][0] for v in value.values()))
        with tempfile.TemporaryDirectory() as temp:
            self.assertIsNone(recorder.read(temp));path=recorder.write(temp,self.record)
            self.assertEqual(path,Path(temp)/recorder.RECORD);self.assertEqual(recorder.read(temp),json.loads(recorder.text(self.record)))
            path.write_text('{not json');self.assertIsNone(recorder.read(temp))


class LiveRecord(unittest.TestCase):
    """The shipped record and the live tree. When an operation, job tool, setting definition or adapter changes on purpose, write
    the record again with python3 tools/record_registry.py; this test and the release check read the record, never a pinned digest."""
    def test_the_live_tree_equals_the_recorded_graphite_registry(self):
        record=recorder.read(ROOT);self.assertIsNotNone(record,recorder.RECORD+' is missing')
        self.assertEqual((record['schema'],record['release'],checker.RECORD),(recorder.SCHEMA,recorder.RELEASE,recorder.RECORD))
        value=checker.record_sections(recorder.snapshot(),record)
        self.assertEqual(checker.readable(value),[],'the live tree differs from the record; if that is meant, run python3 tools/record_registry.py')

    def test_the_record_agrees_with_itself(self):
        record=recorder.read(ROOT)
        self.assertEqual(record['counts'],{'operations':len(record['operations']),'job_tools':len(record['job_tools']),'settings':len(record['settings']),
            'adapters':sum(1 for v in record['adapters']['operations'].values() if v)})
        self.assertEqual(sorted(record['settings_order']),sorted(record['settings']));self.assertEqual(len(set(record['settings_order'])),len(record['settings_order']))
        self.assertEqual(set(record['adapters']['operations']),set(record['operations']));self.assertEqual(set(record['adapters']['settings']),set(record['settings']))
        self.assertTrue(all(isinstance(row['scope'],str) and row['scope'] and len(row['arguments'])==64 for row in record['operations'].values()))


class Runtime(unittest.TestCase):
    """A broken payload, a stale seed and a syntax error each fail the runtime section; nothing reads a pass as readiness."""
    def stage_one(self,payload_state='VERIFIED',seed_state='VERIFIED_SOURCE_BINDINGS',source='x = 1\n'):
        from tools import check_stage_one
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp)/'module.py').write_text(source);out=io.StringIO()
            payload={'state':payload_state,'files':1,'problems':[] if payload_state=='VERIFIED' else ['workbench/x.py: changed']}
            with patch.object(check_stage_one,'ROOT',Path(temp)),patch.object(sys,'argv',['check_stage_one.py']),\
                 patch('workbench.release_integrity.verify',return_value=payload),\
                 patch('workbench.stacy_foundation.seed_status',return_value={'state':seed_state}),contextlib.redirect_stdout(out):
                code=check_stage_one.main()
        return code,json.loads(out.getvalue())

    def test_check_stage_one_fails_a_damaged_payload_a_stale_seed_and_a_syntax_error(self):
        self.assertEqual(self.stage_one()[1]['errors'],[]);self.assertEqual(self.stage_one()[0],0)
        code,value=self.stage_one(payload_state='DAMAGED');self.assertEqual((code,value['state'],value['errors']),(1,'FAILED',['payload']))
        code,value=self.stage_one(seed_state='STALE');self.assertEqual((code,value['state'],value['errors']),(1,'FAILED',['source foundation']))
        code,value=self.stage_one(source='def broken(:\n');self.assertEqual((code,value['state']),(1,'FAILED'));self.assertTrue(value['errors'][0].startswith('module.py: '))

    def test_a_damaged_manifest_payload_is_found_by_the_verifier_the_runtime_section_runs(self):
        from workbench.release_integrity import verify
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'a.txt').write_bytes(b'one')
            row={'bytes':3,'sha256':recorder.hashlib.sha256(b'one').hexdigest()}
            (root/'MANIFEST.json').write_text(json.dumps({'files':{'a.txt':row,'gone.txt':row}}))
            self.assertEqual(verify(root)['problems'],['gone.txt: missing'])
            (root/'gone.txt').write_bytes(b'two');self.assertEqual(verify(root)['problems'],['gone.txt: changed'])

    def test_runtime_section_keeps_any_failure_failed_and_explains_unpackaged_edits(self):
        edited={'state':'FAILED','errors':['payload','source foundation'],'payload':{'state':'DAMAGED','problems':['workbench/x.py: changed']},'foundation':'STALE'}
        value=checker.runtime_section(runner=lambda:copy.deepcopy(edited))
        self.assertEqual(value['state'],'FAILED');self.assertTrue(value['reading'].startswith('EDITED_SOURCES_NOT_YET_PACKAGED'))
        missing={'state':'FAILED','errors':['payload'],'payload':{'state':'DAMAGED','problems':['workbench/x.py: missing']}}
        value=checker.runtime_section(runner=lambda:copy.deepcopy(missing));self.assertEqual(value['state'],'FAILED');self.assertNotIn('reading',value)
        self.assertEqual(checker.runtime_section(runner=lambda:{'state':'PASSED','errors':[]})['state'],'PASSED')
        self.assertEqual(checker.runtime_section(runner=lambda:{'error':'child crashed'})['state'],'FAILED')


class PayloadPrivacy(unittest.TestCase):
    def tree(self,temp):
        root=Path(temp);(root/'docs').mkdir();(root/'.git').mkdir()
        home=b'/'+b'home/alice/'
        (root/'clean.txt').write_bytes(b'nothing to see')
        (root/'docs/notes.md').write_bytes(b'built in '+home+b'project')
        # the build container's own paths: root's home and the per-session temp root, as a model trial records its model file
        (root/'trial.json').write_bytes(b'{"model_file": "/'+b'tmp/claude-0/-home-user-Project/abc/scratchpad/models/m.gguf"}')
        (root/'proxy.txt').write_bytes(b'CA bundle at /'+b'root/.ccr/ca-bundle.crt')
        (root/'paths.py').write_bytes(b"BLOCKED = ['/"+b"root/', '/"+b"tmp/']  # bare roots name no one's files")
        (root/'sandbox.py').write_bytes(b'HOME = "/'+b'home/ledger/"')  # the sandbox's own home is allowed
        (root/'key.txt').write_bytes(b'-----BEGIN '+b'PRIVATE KEY-----\nabc')
        (root/'provider.txt').write_bytes(b'AIza'+b'x'*35)
        (root/'token.txt').write_bytes(b'ghp_'+b'A'*36)
        (root/'run.log').write_text('log');(root/'.git/config').write_text('[core]')
        os.symlink(root/'clean.txt',root/'link.txt')
        with zipfile.ZipFile(root/'bundle.zip','w',zipfile.ZIP_DEFLATED) as archive:  # compressed: only the member's bytes say it
            archive.writestr('inner/readme.txt','fine');archive.writestr('inner/config.py',b'path = "'+home+b'x"')
        with zipfile.ZipFile(root/'escape.zip','w') as archive:archive.writestr('../outside.txt','x')
        return root

    def test_every_rule_reports_the_file_and_category_never_the_value(self):
        with tempfile.TemporaryDirectory() as temp:
            root=self.tree(temp)
            files=['clean.txt','docs/notes.md','trial.json','proxy.txt','paths.py','sandbox.py','key.txt','provider.txt','token.txt','run.log',
                '.git/config','link.txt','bundle.zip','escape.zip','absent.txt']
            value=checker.payload_privacy(root,files=files,allowed={})
            self.assertEqual(value['state'],'FAILED');self.assertEqual((value['files_scanned'],value['archives_scanned']),(15,2))
            self.assertEqual({(f['file'],f['category']) for f in value['findings']},{('docs/notes.md','developer-machine-path'),
                ('trial.json','developer-machine-path'),('proxy.txt','developer-machine-path'),('key.txt','private-key'),
                ('provider.txt','provider-key'),('token.txt','github-token'),('bundle.zip!inner/config.py','developer-machine-path')})
            for expected in ('run.log: logs, compiled files and keys are not release content','.git/config: private or local state folder',
                'link.txt: symlink','escape.zip: unsafe member path','absent.txt: missing','trial.json: developer-machine-path',
                'proxy.txt: developer-machine-path'):self.assertIn(expected,value['problems'])
            text=json.dumps(value);self.assertNotIn('alice',text);self.assertNotIn('xxxxxxxx',text);self.assertNotIn('AAAAAAAA',text)
            self.assertNotIn('scratchpad',text);self.assertNotIn('.ccr',text)
            allowed={('bundle.zip!inner/config.py','developer-machine-path'):'pinned upstream build path'}
            value=checker.payload_privacy(root,files=['clean.txt','paths.py','sandbox.py','bundle.zip'],allowed=allowed)
            self.assertEqual((value['state'],value['problems']),('PASSED',[]));self.assertEqual(value['accepted'][0]['reason'],'pinned upstream build path')

    def test_no_file_list_is_a_failure_and_the_checker_source_never_matches_itself(self):
        with tempfile.TemporaryDirectory() as temp:self.assertEqual(checker.payload_privacy(temp)['state'],'FAILED')
        for path in (ROOT/'tools/check_hatch.py',Path(__file__)):
            raw=path.read_bytes();self.assertEqual([c for c,p in checker.PATTERNS.items() if p.search(raw)],[],path.name)
        self.assertTrue(all(name.startswith('runtimes/python-wasi/python-wasi.zip!') for name,_ in checker.PRIVACY_ALLOWED))


class FocusedSet(unittest.TestCase):
    def test_every_test_module_is_in_the_focused_set_or_named_on_demand(self):
        modules=checker.FOCUSED_MODULES;self.assertIsInstance(modules,tuple);self.assertEqual(len(modules),len(set(modules)),'duplicate module')
        shipped={path.stem for path in (ROOT/'tests_integrated').glob('test_*.py')}
        self.assertEqual(shipped-set(modules)-set(checker.ON_DEMAND_MODULES),set(),'a test module nothing runs')
        self.assertEqual(set(modules)-shipped,set(),'a listed module is not in tests_integrated');self.assertEqual(set(checker.ON_DEMAND_MODULES)-shipped,set())
        self.assertFalse(set(modules)&set(checker.ON_DEMAND_MODULES))
        self.assertEqual([p.name for p in ROOT.glob('tests_stage_*')],[],'one test folder: tests_integrated')

    def test_each_module_runs_in_its_own_child_and_an_absent_module_fails(self):
        calls=[]
        def runner(command,timeout,json_output):
            calls.append((command,json_output));return {'state':'PASSED','tests':3,'failures':0,'errors':0,'skipped':0}
        value=checker.focused_tests(modules=('test_release_check','test_not_shipped_fixture'),runner=runner)
        self.assertEqual(calls,[(['-m','unittest','-v','tests_integrated.test_release_check'],False)])
        self.assertEqual((value['state'],value['tests'],value['present'],value['absent']),('FAILED',3,['test_release_check'],['test_not_shipped_fixture']))
        self.assertEqual(value['modules']['test_not_shipped_fixture'],{'state':'ABSENT'})
        self.assertEqual(checker.focused_tests(modules=('test_release_check',),runner=runner)['state'],'PASSED')
        failing=checker.focused_tests(modules=('test_release_check',),runner=lambda c,t,j:{'state':'FAILED','tests':3,'failures':1,'errors':0,'error':'x'})
        self.assertEqual((failing['state'],failing['failures']),('FAILED',1))
        self.assertEqual(checker.focused_tests(modules=('test_not_shipped_fixture',),runner=runner)['state'],'NOTHING_RUN')

    def test_unittest_summary_and_tool_json_parsing(self):
        self.assertEqual(checker.parse_unittest('test_a ... ok\n\nRan 14 tests in 1.250s\n\nOK\n'),{'tests':14,'seconds':1.25,'verdict':'OK','failures':0,'errors':0,'skipped':0})
        value=checker.parse_unittest('Ran 1 test in 0.001s\n\nFAILED (failures=1, errors=2)\n');self.assertEqual((value['tests'],value['verdict'],value['failures'],value['errors']),(1,'FAILED',1,2))
        self.assertEqual(checker.parse_unittest('Traceback\nModuleNotFoundError')['tests'],None)
        self.assertEqual(checker.tail_json('Label one\nLabel {two}\n{\n  "state": "PASSED",\n  "checks": ["a"]\n}\n'),{'state':'PASSED','checks':['a']})
        self.assertEqual(checker.tail_json('{"state": "A"}\n{"state": "B"}\n'),{'state':'B'});self.assertIsNone(checker.tail_json('no json here'))


# A hold refuses the call: patch.object(<target>,'<name>',side_effect=AssertionError(...)). check_model_settings_ui lifts the
# launch and submit holds for its one Reload step only (a recording launch; the queued row is the behaviour it checks).
HOLDS={'Kernel.launch':re.compile(r"patch\.object\(\s*Kernel\s*,\s*'launch'\s*,\s*side_effect=AssertionError\("),
    'Kernel.submit':re.compile(r"patch\.object\(\s*Kernel\s*,\s*'submit'\s*,\s*side_effect=AssertionError\("),
    'clip._request':re.compile(r"patch\.object\(\s*clip\s*,\s*'_request'\s*,\s*side_effect=AssertionError\(")}


class UiGate(unittest.TestCase):
    def test_every_qt_check_is_in_the_gate_or_on_demand_and_holds_the_three_calls(self):
        checks={'tools/'+path.name for path in (ROOT/'tools').glob('check_*_ui.py')}
        self.assertEqual(checks-set(checker.UI_CHECKS)-set(checker.ON_DEMAND_CHECKS),set(),'a Qt check nothing names')
        self.assertEqual(set(checker.UI_CHECKS)-checks,set());self.assertFalse(set(checker.UI_CHECKS)&set(checker.ON_DEMAND_CHECKS))
        for name in ('finder','head','agent','document','graphite','rename','frame','hatch','paper','machine'):self.assertIn('tools/check_'+name+'_ui.py',checker.UI_CHECKS)
        for script in sorted(checks):
            text=(ROOT/script).read_text()
            missing=[call for call,pattern in HOLDS.items() if not pattern.search(text)]
            self.assertEqual(missing,[],script+' does not hold '+', '.join(missing))

    def test_every_check_writes_its_captures_where_the_gate_says(self):
        for script,variable in checker.UI_CAPTURE_ENV.items():
            self.assertTrue((ROOT/script).is_file(),script);self.assertIn("os.environ.get('"+variable+"'",(ROOT/script).read_text(),script)
        self.assertTrue(set(checker.UI_CHECKS)<=set(checker.UI_CAPTURE_ENV))
        for script in checker.UI_CHECKS:self.assertNotRegex((ROOT/script).read_text(),r"build/(?:desktop|workshop|agent|integration)0\d_ui",script)
        seen=[];before=dict(os.environ)
        def runner(command,timeout,json_output,env):
            seen.append((command[0],env.get(checker.UI_CAPTURE_ENV[command[0]])));return {'state':'PASSED','checks':['a','b'],'captures':[{'file':'x.png'}]}
        with tempfile.TemporaryDirectory() as temp:
            value=checker.ui_checks(scripts=('tools/check_frame_ui.py','tools/check_not_shipped_ui.py'),runner=runner,capture_root=Path(temp)/'rerun')
            self.assertEqual(seen,[('tools/check_frame_ui.py',str(Path(temp)/'rerun/check_frame_ui'))])
        self.assertEqual((value['state'],value['absent'],value['scripts']['tools/check_frame_ui.py']['checks']),('FAILED',['tools/check_not_shipped_ui.py'],2))
        self.assertEqual(value['scripts']['tools/check_frame_ui.py']['capture_variable'],'ARC_LEDGER_FRAME_CAPTURE_DIR')
        self.assertEqual(dict(os.environ),before)  # each child gets its own environment; this process's is untouched


class ShippedRoute(unittest.TestCase):
    def test_check_release_is_the_one_entry_and_routes_nowhere_else(self):
        text=(ROOT/'tools/check_release.py').read_text()
        self.assertIn("'check_hatch.py'",text)
        for gone in ('integrated_pass','delivery_stage','check_i0','check_stage_','check_release_legacy','MANIFEST'):self.assertNotIn(gone,text)
        for gone in ('check_i01.py','check_i02.py','check_i03.py','check_i04.py','check_i05.py','check_stage_two.py','check_stage_three.py','check_stage_four.py',
                'check_stage_five.py','check_stage_six.py','check_release_legacy.py','check_integration01_ui.py','check_service_lifecycle_ui.py'):
            self.assertFalse((ROOT/'tools'/gone).exists(),gone)
        self.assertTrue((ROOT/'tools/check_stage_one.py').is_file())  # the engine of the runtime section

    def test_native_flags_get_a_json_answer_and_runtime_is_accepted(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):code=checker.main(['--native','--keep','/nonexistent'])
        value=json.loads(out.getvalue());self.assertEqual((code,value['state'],value['native_flags']),(1,'FAILED',['--native','--keep']))
        self.assertIn('python -m workbench.joined_checks',value['reason'])
        with patch.object(checker,'report',return_value={'state':'PASSED','failed_sections':[]}) as report,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(checker.main(['--runtime']),0);report.assert_called_once_with(False,False)

    def test_check_release_reports_every_section_against_the_record(self):
        child=subprocess.run([sys.executable,'-B','tools/check_release.py'],cwd=ROOT,capture_output=True,text=True,timeout=600)
        result=json.loads(child.stdout)
        self.assertEqual((result['checker'],result['entry'],result['notice']),('tools/check_hatch.py','tools/check_release.py',checker.NOTICE))
        self.assertEqual(result['release']['name'],'Graphite');self.assertEqual(result['release']['record'],checker.RECORD)
        # runtime and privacy read the shipped payload; while sources are edited (packaging rewrites the manifest and rebuilds the seed)
        # they can read FAILED, so their structure is asserted here and their state by the packaged release.
        self.assertTrue({'state','payload','foundation','capabilities','schema_digest','python_files_parsed','errors'}<=set(result['runtime']))
        self.assertTrue({'state','files_scanned','findings','problems','accepted'}<=set(result['payload_privacy']))
        for name in ('registry','settings','adapters'):
            self.assertEqual((result[name]['state'],result[name]['differences']),('PASSED',[]),name)
        self.assertEqual(result['registry']['schema_digest'],recorder.read(ROOT)['schema_digest'])
        self.assertNotIn('focused_tests',result);self.assertNotIn('ui_checks',result)
        for gone in ('acceptance','historical_i05_comparison','checkpoint'):self.assertNotIn(gone,result)
        self.assertEqual(child.returncode,0 if result['state']=='PASSED' else 1)
        self.assertEqual(result['state']=='PASSED',result['failed_sections']==[])
        self.assertEqual(set(result['failed_sections'])-{'runtime','payload_privacy'},set())


if __name__=='__main__':unittest.main()
