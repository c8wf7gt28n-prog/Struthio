"""The Hatch doorway: stored and passive state only, truthful descriptor words, no new authority.

DESKTOP-01 (HT01, HT02, HT03): the six tool groups lead the menu, every row carries the presentation contract, and the
five earlier choices keep their routes, identities and keys in their new places. Kernel-level, plus a few widget-level
cases on an offscreen QApplication with no window.
"""
import hashlib,json,os,re,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from workbench import explore,explore_qt,hatch_qt,capability_catalog,ledger_control
from workbench.engineering_kernel import Kernel,operator,CAPABILITIES,TOOLS
from workbench.session import Session

ROOT=Path(__file__).resolve().parents[1]
# The checks use the existing navigation keys. The operation rooms use program destinations.
PROGRAM_ROUTES={'kicad':'cad','kibot':'kibot','spice':'spice','yosys':'yosys','fpga':'implementation','hdl':'hdl'}
PROGRAM_TITLES={'kicad':'KiCad checks','kibot':'KiBot outputs','spice':'ngspice profiles','yosys':'Yosys synthesis','fpga':'nextpnr & Trellis','hdl':'HDL simulation checks'}
PROGRAM_ROOMS={'mail':'Mail','blender':'Blender','godot':'Godot','transfer':'Transfer','cartridge':'Cartridge Bay',
               'inkscape':'Inkscape','media':'Media Bench','freecad':'FreeCAD',
               'print':'Print Proof','delivery':'Delivery'}
DESTINATIONS=('discovery','algorithms','atlas','organizer','packages','object_glass','trail','settings','commands','activity','home','engineering',
    'brain_link','native_game','orange_book','ledger','arcos','native_pcb','developer_tools','cad','kibot','spice','yosys','implementation','hdl',
    'stacy_knowledge','stacy_awareness','brain','intake','references','memory','office','slate','files','documents','investigations')


def widget_host(kernel,root,ident=None):
    """The least host a HatchButton needs, as a QObject (LedgerLifecycle parents itself to it); no window, no tabs."""
    from PySide6.QtCore import QObject
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    class Host(QObject):pass
    class Tabs:
        def currentWidget(self):return None if ident is None else type('Current',(),{'property':lambda self,name:ident if name=='cabinet_node' else None})()
        def count(self):return 0
        def widget(self,index):return None
    class Status:
        def __init__(self):self.messages=[]
        def showMessage(self,text,*args):self.messages.append(text)
        def currentMessage(self):return self.messages[-1] if self.messages else ''
    host=Host();host.root=root;host.ledger_bridge=type('Bridge',(),{'kernel':kernel})();host._closing=False;host.status=Status()
    host.statusBar=lambda:host.status;host.tabs=Tabs();host.command_palette=lambda:None;host.reading_profile={}
    return host


class LauncherTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ledger-launcher-');self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.root=self.base/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(self.base/'profile'),'ARC_LEDGER_CONCERN':str(self.base/'Concern')})
        env.start();self.addCleanup(env.stop);self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.session=Session(self.base/'profile/session.json',self.root);self.session.save();ledger_control.bind(self.kernel,self.session)

    def call(self,op,args=None,principal=None):
        value=self.kernel.dispatch(op,args or {},principal or self.owner);self.assertTrue(value['ok'],value);return value['result']

    def instruments(self,principal=None,**args):
        return {r['key']:r for r in self.call('ledger.explore',dict(kind='INSTRUMENT',**args),principal)['instruments']}

    def hatch(self,ident=None):
        host=widget_host(self.kernel,self.root,ident);button=hatch_qt.HatchButton(host);button.lifecycle.timer.stop()
        self.addCleanup(button.deleteLater);return button,host

    def missing(self,*names):
        original=capability_catalog.source;paths={'workbench/'+n for n in names}
        def source(root,name):
            return dict(path=name,state='MISSING_OR_UNSAFE',sha256=None) if name in paths else original(root,name)
        return patch.object(capability_catalog,'source',side_effect=source)

    def test_routes_require_every_module_they_open(self):
        with self.missing('problem_qt.py'):rows=self.instruments()
        for key in ('calculate','laboratory'):
            self.assertFalse(rows[key]['view_available']);self.assertEqual(rows[key]['missing_modules'],['workbench/problem_qt.py'])
            self.assertEqual(rows[key]['source']['state'],'MISSING_OR_UNSAFE')
        self.assertTrue(rows['projects']['view_available'])
        with self.missing('calculator_qt.py'):rows=self.instruments()
        self.assertFalse(rows['calculate']['view_available']);self.assertEqual(rows['calculate']['missing_modules'],['workbench/calculator_qt.py'])
        self.assertTrue(rows['laboratory']['view_available']);self.assertEqual(rows['laboratory']['missing_modules'],[])
        self.assertEqual([s['path'] for s in rows['laboratory']['sources']],['workbench/project_desk_qt.py','workbench/problem_qt.py','workbench/lab_qt.py'])

    def test_activity_row_opens_the_work_trail_room(self):
        row=self.instruments()['activity']
        self.assertEqual((row['destination'],row['view_class']),('trail','WorkTrailTab'))
        self.assertEqual(row['source'],dict(path='workbench/work_trail_qt.py',state='PRESENT',sha256=row['source']['sha256']))
        self.assertTrue(row['view_available']);self.assertIn('trail',DESTINATIONS)

    def test_interrupted_jobs_are_counted_separately_and_never_disclosed(self):
        with self.kernel.db() as db:
            for ident,owner,state in [('a','owner','Running'),('b','owner','Queued'),('c','owner','Interrupted'),('d','other','Interrupted')]:
                payload=json.dumps(dict(id=ident,owner=owner,state=state,tool='brain.infer',private='Do not include this payload'))
                db.execute('INSERT INTO jobs VALUES(?,?,?,?)',(ident,owner,state,payload))
        value=self.call('ledger.explore',{'kind':'INSTRUMENT'});brain=next(r for r in value['instruments'] if r['key']=='brain')
        self.assertEqual((brain['running_jobs'],brain['queued_jobs'],brain['active_jobs'],brain['interrupted_jobs']),(1,1,2,1))
        self.assertNotIn('Do not include this payload',json.dumps(value))
        other=self.instruments(operator('other'))['brain']
        self.assertEqual((other['active_jobs'],other['interrupted_jobs']),(0,1))
        self.assertEqual(self.instruments()['projects']['interrupted_jobs'],0)

    def test_setup_needed_names_missing_executables_without_running_anything(self):
        with patch('shutil.which',return_value=None),patch('subprocess.Popen',side_effect=AssertionError('No process launch')):
            value=self.call('ledger.explore',{'kind':'INSTRUMENT'})
        rows={r['key']:r for r in value['instruments']}
        self.assertEqual(value['native_invocations'],0)
        self.assertEqual((rows['spice']['tool_status'],rows['spice']['setup_needed']),('Needs setup',['ngspice']))
        self.assertEqual(rows['fpga']['setup_needed'],['ecppack','nextpnr-ecp5'])
        self.assertEqual(rows['hdl']['setup_needed'],['iverilog','surfer','verilator'])
        self.assertEqual((rows['projects']['tool_status'],rows['projects']['setup_needed']),('Use existing controls',[]))

    def test_programs_rows_use_existing_routes_and_passive_detection(self):
        rows=self.instruments();programs={k:v for k,v in rows.items() if v['group']=='Programs'}
        self.assertEqual(set(programs),PROGRAM_ROUTES.keys() | PROGRAM_ROOMS.keys())
        for key,route in PROGRAM_ROUTES.items():
            self.assertTrue(programs[key]['view_available'],key);self.assertEqual(programs[key]['destination'],route);self.assertIn(route,DESTINATIONS)
            self.assertEqual(programs[key]['qualification'],'UNASSESSED');self.assertGreater(programs[key]['job_tools'],0)
        for key in PROGRAM_ROOMS:
            row=programs[key]
            self.assertTrue(row['view_available'],key);self.assertEqual(row['destination'],'program:'+key)
            self.assertEqual(row['qualification'],'UNASSESSED');self.assertEqual(row['job_tools'],0)
            self.assertGreater(row['operations'],0)
            self.assertTrue(all(op['operation'].startswith('programs.'+key+'.') for op in row['slate_operations']))
        # This disposable workspace carries no program-only marker, so KiCad does not ask for a project; a detached program does.
        self.assertIs(rows['kicad']['project_required'],False)
        with patch.object(explore.project_context,'detached',return_value=True):detached=self.instruments()
        self.assertTrue(detached['kicad']['project_required']);self.assertFalse(any(detached[k]['project_required'] for k in detached if k!='kicad'))
        with patch('shutil.which',return_value=None):rows=self.instruments()
        self.assertTrue(all(rows[k]['tool_status']=='Needs setup' for k in PROGRAM_ROUTES))
        # A real file stands in for every executable: detection stays passive and the words stay guarded.
        with patch('shutil.which',return_value=sys.executable),patch('subprocess.Popen',side_effect=AssertionError('No process launch')):rows=self.instruments()
        for key in ('kicad','kibot','spice','yosys','fpga'):self.assertEqual(rows[key]['tool_status'],'Detected · checks remain',key)
        self.assertEqual(rows['hdl']['tool_status'],'Needs setup');self.assertIn('iverilog',rows['hdl']['setup_needed'])  # Icarus also needs its ivl data directory

    def test_capability_words_are_truthful(self):
        rows=self.instruments();brain=dict(rows['brain'],tool_status='Detected · checks remain',setup_needed=[])  # the runtime archive state is this host's; the words are tested
        self.assertEqual(explore_qt.capability_text(brain,True,{'state':'READY'}),'Local model · open · ready')
        self.assertEqual(explore_qt.capability_text(brain,False,None),'Local model')  # no state read, no word
        self.assertEqual(explore_qt.capability_text(brain,False,{'state':'UNAVAILABLE'}),'Local model · state unavailable')  # a failed read says so
        self.assertNotIn('Local model:',explore_qt.capability_tip(brain,None));self.assertIn('Local model: state unavailable',explore_qt.capability_tip(brain,{'state':'UNAVAILABLE'}))
        with patch.object(explore_qt,'local_brain',create=True):pass
        from workbench import local_brain
        with patch.object(local_brain,'status',side_effect=AttributeError('corrupt row')):self.assertEqual(explore_qt.brain_state(object()),{'state':'UNAVAILABLE'})
        with patch.object(local_brain,'status',return_value={'state':'MODEL_STOPPED'}):self.assertEqual(explore_qt.brain_word(explore_qt.brain_state(object())),'stopped')
        calculate=dict(rows['calculate'],tool_status='Use existing controls',setup_needed=[])
        self.assertEqual(explore_qt.capability_text(calculate,False),'Calculate && compare')
        busy=dict(rows['laboratory'],tool_status='Detected · checks remain',setup_needed=[],running_jobs=2,queued_jobs=0,interrupted_jobs=1)
        self.assertEqual(explore_qt.capability_text(busy,True),'Laboratory · open · 2 running · 1 interrupted')
        self.assertIn('2 running · 1 interrupted for this owner',explore_qt.capability_tip(busy))
        gone=dict(brain,view_available=False,view_state='View unavailable',missing_modules=['workbench/brain_qt.py'])
        self.assertEqual(explore_qt.capability_text(gone,True,{'state':'READY'}),'Local model · unavailable')
        self.assertEqual(explore_qt.capability_tip(gone).split('\n')[1],'View unavailable: workbench/brain_qt.py')
        # Missing setup is in the row words, not only on hover (HT03); the tooltip names the executables.
        spice=dict(rows['spice'],tool_status='Needs setup',setup_needed=['ngspice'])
        self.assertEqual(explore_qt.capability_text(spice,False),'ngspice profiles · needs setup')
        self.assertEqual(explore_qt.capability_text(dict(spice,running_jobs=1),True),'ngspice profiles · needs setup · open · 1 running')
        tip=explore_qt.capability_tip(spice);lines=tip.split('\n')
        self.assertEqual(lines[1],"Opens: Graphite's ngspice checks and controls in a Graphite workspace; ngspice itself is not opened")
        self.assertTrue(lines[2].startswith('Graphite can: spice.'),lines[2]);self.assertEqual(lines[3],'Needs: ngspice')
        self.assertEqual(lines[-4:],['Qualification: not assessed on this host.','Context: none selected','Opening runs no tool.',explore_qt.ROOM_NOTE])
        self.assertIn('Context: My idea · idea',explore_qt.capability_tip(spice,None,{'label':'My idea','role':'idea'}))
        self.assertIn('Context: a thought · working copy',explore_qt.capability_tip(spice,None,{'label':'a thought','role':'working_copy'}))
        self.assertEqual(explore_qt.needs_line(dict(spice,tool_status='Detected · checks remain')),'Prerequisites present (unmeasured)')
        self.assertEqual(explore_qt.needs_line(dict(spice,tool_status='Not assessed')),'Prerequisites: no native profile to check')
        self.assertEqual(explore_qt.needs_line(dict(spice,tool_status='Use existing controls')),'Prerequisites: none beyond Graphite')
        for entry in rows.values():
            tip=explore_qt.capability_tip(entry,{'state':'READY'});text=explore_qt.capability_text(entry,False,{'state':'READY'})
            self.assertIn('Qualification: not assessed on this host.',tip);self.assertIn('Preview and pins are not replaced',tip)
            self.assertIn('Opens: '+entry['presentation'],tip);self.assertIn('\nGraphite can: ',tip);self.assertIn('\nOpening runs no tool.',tip)
            self.assertEqual(text.endswith(' · needs setup') or ' · needs setup · ' in text,entry['tool_status']=='Needs setup',text)
            self.assertNotIn('ready to run',tip)
            for word in (str(len(CAPABILITIES)),str(len(TOOLS)),'registered operations','registered job tools'):self.assertNotIn(word,tip);self.assertNotIn(word,text)
        self.assertIn('Needs an attached project.',explore_qt.capability_tip(dict(rows['kicad'],project_required=True)))
        self.assertNotIn('Needs an attached project.',explore_qt.capability_tip(dict(rows['kicad'],project_required=False)))

    def test_descriptor_fields_follow_the_presentation_contract(self):
        rows=self.instruments();catalogue=dict(CAPABILITIES)
        for key,row in rows.items():
            self.assertIn(row['presentation_kind'],explore.KINDS,key);self.assertEqual(row['view_state'],'Workspace available',key)
            self.assertEqual(row['human_route'],'Menu ▸ '+row['group']+' ▸ '+row['title']+' (also Explore)')
            self.assertLessEqual(len(row['slate_operations']),explore.SLATE_OPERATIONS_SHOWN);self.assertLessEqual(len(row['slate_operations']),row['operations'])
            self.assertEqual(len(row['slate_operations']),min(row['operations'],explore.SLATE_OPERATIONS_SHOWN))
            for op in row['slate_operations']:  # straight from the registry: the same operation names and scopes, never invented
                self.assertEqual(catalogue[op['operation']],op['scope'],op)
                self.assertTrue(op['operation'].startswith(next(v[7] for v in explore.VIEWS if v[0]==key)),op)
        for key,title in PROGRAM_TITLES.items():
            self.assertEqual((rows[key]['title'],rows[key]['presentation_kind']),(title,'checks'))
            self.assertIn(explore.NATIVE_NAMES[key]+' itself is not opened',rows[key]['presentation'])
        for key,title in PROGRAM_ROOMS.items():
            self.assertEqual((rows[key]['title'],rows[key]['presentation_kind']),(title,'operations'))
            self.assertIn('no application window is embedded',rows[key]['presentation'])
        self.assertEqual(rows['office']['presentation_kind'],'operations');self.assertIn('no application window is embedded',rows['office']['presentation'])
        self.assertEqual({k for k,r in rows.items() if r['presentation_kind']=='workspace'},set(rows)-set(PROGRAM_TITLES)-set(PROGRAM_ROOMS)-{'office'})
        self.assertTrue(all(r['presentation']=='Graphite workspace' for k,r in rows.items() if r['presentation_kind']=='workspace'))
        # The explain line in Explore's Kind column has a word for every kind.
        self.assertEqual(set(explore_qt.PRESENTATION_WORDS),set(explore.KINDS))

    def test_session_exit_follows_the_dedicated_session_marker_only(self):
        """Return to Debian in the dedicated session, Exit Graphite elsewhere: both the existing leave (HATCH DESK D2: the
        System menu's row; the old disabled "not in this edition" row is superseded by the owner's brief)."""
        dedicated=hatch_qt.session_exit({'ARC_LEDGER_XSESSION':'1'})
        self.assertEqual(dedicated['label'],'Return to Debian');self.assertTrue(dedicated['dedicated']);self.assertIn('Debian text login',dedicated['tip'])
        self.assertIn('computer stays on',dedicated['tip']);self.assertEqual(dedicated['scope'],'this Graphite session')
        for environ in ({},{'ARC_LEDGER_FULLSCREEN':'1'},{'ARC_LEDGER_XSESSION':'0'}):
            plain=hatch_qt.session_exit(environ)
            self.assertEqual(plain['label'],'Exit Graphite');self.assertFalse(plain['dedicated']);self.assertIn('stays open',plain['tip'])
        with patch.dict(os.environ,{'ARC_LEDGER_XSESSION':'1'}):self.assertEqual(hatch_qt.session_exit()['label'],'Return to Debian')
        self.assertFalse(any(hasattr(hatch_qt,name) for name in ('POWER_ROW','NO_POWER','POWER_WORDS','power_tip')),'the old disabled row is gone')

    def test_the_cat_names_no_os_session_or_power_command(self):
        """The cat opens the programs list and dispatches nothing but the ledger.explore read; leaving and the session and power
        commands are the System menu's, through session_power's one function."""
        import ast
        tree=ast.parse((ROOT/'workbench/hatch_qt.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node,(ast.Module,ast.FunctionDef,ast.ClassDef)) and node.body and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant):node.body[0].value.value=''
        text=ast.unparse(tree)
        for word in ('subprocess','os.system','startDetached','systemctl','loginctl','poweroff','QMenu'):self.assertNotIn(word,text)
        self.assertEqual(len(re.findall(r"dispatch\('",text)),1);self.assertIn("dispatch('ledger.explore'",text)
        self.assertEqual(hatch_qt.ORDER,('programs A to Z','—','Explore the workshop'));self.assertEqual(hatch_qt.HatchButton.NAME,'Open programs')

    def test_the_programs_list_is_flat_sorted_and_holds_every_capability(self):
        """The brief: "a flat, predictable list of available programs and capabilities, like the Programs folder in a Start
        menu ... one plain name and one small graphite icon". Nothing is lost from the Hatch groups: one row per adapter of
        explore.VIEWS (the six groups' rows), A to Z by plain name, then Explore the workshop; creation, recent work, services and
        leaving are not in it."""
        from workbench import programs_qt
        button,host=self.hatch();lst=button.programs
        self.assertTrue(button.prepare());words=lst.words()
        plain=sorted((programs_qt.PLAIN[row[0]] for row in explore.VIEWS),key=str.casefold)
        self.assertEqual(words,plain+['—','Explore the workshop','Game'],'0.7.0: the game is among the programs, last (it was the System menu’s first row)');self.assertEqual(len(plain),len(explore.VIEWS))
        self.assertEqual(set(lst.rows_by_key),{row[0] for row in explore.VIEWS},'every capability of the Hatch groups, once')
        self.assertEqual(set(button.entries),set(lst.rows_by_key));self.assertIs(lst.explore_row.action,button.explore_action)
        self.assertEqual(programs_qt.order(),[k for k in sorted(lst.rows_by_key,key=lambda k:(programs_qt.PLAIN[k].casefold(),k))])
        for gone in ('New Idea','New Project','Services','Graphite services','Exit Graphite','Return to Debian','Log out','Restart','Shut down','Recent'):
            self.assertFalse(any(w.startswith(gone) for w in words),gone)
        objects=list(lst.rows())
        for _ in range(3):self.assertTrue(button.prepare())
        self.assertEqual(lst.rows(),objects,'created once; each opening refills their words')
        icons={row.icon_key for row in objects};self.assertEqual(len(icons),len(objects),'one small icon each');self.assertNotIn('window',icons)
        for key,row in lst.rows_by_key.items():
            tip=row.toolTip();self.assertIn('Opens: ',tip);self.assertIn('Graphite can: ',tip);self.assertIn('Opening runs no tool.',tip)
            self.assertEqual(row.action.property('title'),next(v[1] for v in explore.VIEWS if v[0]==key),'the catalogue\'s own title stays with the row')
        self.assertEqual((button.accessibleName(),button.toolTip(),lst.accessibleName()),('Open programs','Open programs','Programs'))
        self.assertEqual(self.kernel.listing('jobs'),[]);self.assertEqual(host.status.messages,[])

    def test_type_to_select_jumps_to_the_rows_by_their_first_letters(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        button,host=self.hatch();lst=button.programs
        button.open_list(True);self.addCleanup(lst.close_menu)
        focus=lambda:getattr(QApplication.focusWidget(),'word',None)
        self.assertEqual(focus(),'Agenda','a keyboard opening starts at the first row')
        lst.typed_at=0;QTest.keyClick(QApplication.focusWidget(),Qt.Key_K);self.assertEqual(focus(),'KiBot outputs')
        lst.typed_at=0;QTest.keyClick(QApplication.focusWidget(),Qt.Key_K);self.assertEqual(focus(),'KiCad checks','the same letter again: the next row with it')
        lst.typed_at=0;QTest.keyClicks(QApplication.focusWidget(),'ng');self.assertEqual(focus(),'ngspice profiles','letters typed together make one prefix')
        lst.typed_at=0;QTest.keyClick(QApplication.focusWidget(),Qt.Key_E);self.assertEqual(focus(),'Explore the workshop')
        QTest.keyClick(QApplication.focusWidget(),Qt.Key_Down);self.assertEqual(focus(),'Game','the game is the last row (0.7.0)')
        QTest.keyClick(QApplication.focusWidget(),Qt.Key_Down);self.assertEqual(focus(),'Agenda','Down wraps from the last row')
        QTest.keyClick(QApplication.focusWidget(),Qt.Key_Up);self.assertEqual(focus(),'Game','and Up from the first')
        QTest.keyClick(QApplication.focusWidget(),Qt.Key_Home);self.assertEqual(focus(),'Agenda')
        QTest.keyClick(QApplication.focusWidget(),Qt.Key_F1);self.assertTrue(host.status.messages[-1].startswith('Agenda — Open Graphite'),host.status.messages[-1])
        QTest.keyClick(QApplication.focusWidget(),Qt.Key_Escape);self.assertFalse(lst.isVisible())

    def test_the_list_hides_its_rows_behind_one_explained_row_when_the_read_fails(self):
        button,host=self.hatch();lst=button.programs;real=self.kernel.dispatch
        def failing(op,args,principal):
            if op=='ledger.explore':return {'ok':False,'error':{'code':'FIXTURE','message':'Capability view unavailable for this test'}}
            return real(op,args,principal)
        with patch.object(self.kernel,'dispatch',side_effect=failing):self.assertFalse(button.prepare())
        self.assertEqual(lst.words(),['Capabilities unavailable · Capability view unavailable for this test','—','Explore the workshop','Game'])
        self.assertTrue(button.prepare());self.assertNotIn('Capabilities unavailable',' '.join(lst.words()))
        # A missing adapter disables only its row, in words; choosing it opens nothing.
        with self.missing('brain_qt.py'):self.assertTrue(button.prepare())
        local=lst.rows_by_key['brain'];self.assertFalse(local.isEnabled());self.assertEqual(local.caption,'unavailable');self.assertIn('View unavailable: workbench/brain_qt.py',local.toolTip())

    def test_rows_say_needs_setup_and_the_selected_record(self):
        idea=self.call('ideas.capture',{'text':'A thought for the doorway'},operator());button,host=self.hatch('idea:'+idea['id'])  # the desktop reads as operator()
        with patch('shutil.which',return_value=None),patch('subprocess.Popen',side_effect=AssertionError('No process launch')):self.assertTrue(button.prepare())
        rows=button.programs.rows_by_key
        for key in PROGRAM_ROUTES:
            row=rows[key];self.assertTrue(row.isEnabled());self.assertEqual(row.caption,'needs setup',key);self.assertIn('\nNeeds: ',row.toolTip())
        self.assertIn('Needs: kicad-cli',rows['kicad'].toolTip())
        self.assertIn("Opens: Graphite's KiCad checks and controls in a Graphite workspace; KiCad itself is not opened",rows['kicad'].toolTip())
        self.assertTrue(all('Context: A thought for the doorway · idea' in r.toolTip() for r in rows.values()))
        self.assertEqual(self.kernel.listing('jobs'),[])

    def test_explore_word_keeps_discovery_and_suggestions_without_the_groups(self):
        from PySide6.QtWidgets import QMenu
        host=widget_host(self.kernel,self.root);button=explore_qt.ExploreButton(host);self.addCleanup(button.deleteLater)
        button.prepare();texts=['—' if a.isSeparator() else a.text() for a in button.popup.actions()]
        self.assertEqual(texts,['Explore the workshop…','—','Find saved work…']);self.assertEqual(button.popup.accessibleName(),'Explore menu')
        self.assertIn('Opening runs no tool.',button.popup.actions()[0].toolTip())
        for _ in range(5):button.prepare()
        self.assertEqual(button.popup.findChildren(QMenu),[]);self.assertFalse(hasattr(button,'groups'))
        idea=self.call('ideas.capture',{'text':'Could the Explore word stay small?'},operator())
        host=widget_host(self.kernel,self.root,'idea:'+idea['id']);button=explore_qt.ExploreButton(host);self.addCleanup(button.deleteLater);button.prepare()
        texts=['—' if a.isSeparator() else a.text() for a in button.popup.actions()]
        self.assertEqual(texts[:2],['Explore the workshop…','For Could the Explore word stay small?'])
        self.assertEqual([t.split(' · ')[0] for t in texts[2:6]],['Documents','Questions && inquiries','Calculate && compare','Laboratory']);self.assertEqual(texts[6:],['—','Find saved work…'])  # WORKSHOP-01: the page comes first for an idea
        self.assertFalse(button.popup.actions()[1].isEnabled());self.assertTrue(all('Context: Could the Explore word stay small? · idea' in a.toolTip() for a in button.popup.actions()[2:5]))
        self.assertEqual(self.kernel.listing('jobs'),[])

    def test_digest_cache_follows_size_and_modification_time(self):
        path=self.base/'digest.txt';path.write_bytes(b'one');capability_catalog._DIGESTS.clear()
        reads=[];original=Path.read_bytes
        def counting(self):reads.append(str(self));return original(self)
        with patch.object(Path,'read_bytes',counting):
            first=capability_catalog.digest(path);second=capability_catalog.digest(path)
            self.assertEqual(first,second,hashlib.sha256(b'one').hexdigest());self.assertEqual(reads,[str(path)])
            path.write_bytes(b'one+');os.utime(path,ns=(time.time_ns(),time.time_ns()+2_000_000))
            self.assertEqual(capability_catalog.digest(path),hashlib.sha256(b'one+').hexdigest());self.assertEqual(len(reads),2)
            reads.clear();a=capability_catalog.source(self.root,'workbench/explore.py');b=capability_catalog.source(self.root,'workbench/explore.py')
            self.assertEqual(a,b);self.assertEqual(a['state'],'PRESENT');self.assertEqual(len(reads),1)
        for n in range(4100):capability_catalog._DIGESTS[('synthetic',n,n)]='x'
        other=self.base/'other.txt';other.write_bytes(b'two')
        self.assertEqual(capability_catalog.digest(other),hashlib.sha256(b'two').hexdigest());self.assertEqual(len(capability_catalog._DIGESTS),1)
        capability_catalog._DIGESTS.clear()

    def test_explore_contract_is_a_bounded_read(self):
        # Which operations exist, with which schemas and scopes, is the recorded registry's business (tools/check_release.py).
        self.assertEqual(explore.FIELDS,{'ledger.explore':({'query':{'type':'string','maxLength':180},'context':{'type':'string','minLength':1,'maxLength':600},
            'kind':{'type':'string','enum':['ALL','INSTRUMENT','METHOD','OPERATION','JOB_TOOL']},
            'limit':{'type':'integer','minimum':1,'maximum':100},'offset':{'type':'integer','minimum':0,'maximum':10000}},[])})
        self.assertEqual(explore.SCOPES,{'ledger.explore':'read'});self.assertEqual(ledger_control.DESTINATIONS,DESTINATIONS)
        self.assertEqual(CAPABILITIES['ledger.explore'],'read')

    def test_views_are_grouped_and_unique(self):
        expected_views=23+len(PROGRAM_ROOMS)
        self.assertEqual(len(explore.VIEWS),expected_views);self.assertEqual(explore.GROUPS,('Work','Reason','Instruments','Programs','Knowledge','Configuration'))
        self.assertTrue(all(len(row)==10 and row[3] in explore.GROUPS and row[9] in explore.KINDS for row in explore.VIEWS))
        self.assertEqual(len({row[0] for row in explore.VIEWS}),expected_views);self.assertEqual(len({row[1] for row in explore.VIEWS}),expected_views)
        self.assertEqual(sum(row[3]=='Programs' for row in explore.VIEWS),len(PROGRAM_TITLES)+len(PROGRAM_ROOMS));self.assertEqual(sum(row[9]=='checks' for row in explore.VIEWS),6)
        self.assertEqual({row[0] for row in explore.VIEWS if row[3]=='Programs'},PROGRAM_TITLES.keys() | PROGRAM_ROOMS.keys())
        self.assertEqual(set(explore.NATIVE_NAMES),set(PROGRAM_TITLES))
        rows=self.instruments();self.assertEqual(len(rows),expected_views)
        self.assertTrue(all(r['qualification']=='UNASSESSED' and 'setup_needed' in r and 'interrupted_jobs' in r for r in rows.values()))
        self.assertEqual(self.kernel.listing('jobs'),[])


if __name__=='__main__':unittest.main()
