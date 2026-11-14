"""0.8.2: desk acts (workbench/desk_acts.py, desk_doers.py): one named act for each thing a person can do in the window.

The owner, 14 November 2026: "a pass that builds as much capabilities of Kasandra to control the graphite interface ...
eventually we're going to do that, and that opens up more testing options and simulating options".

Pure rules (no window): the forty acts and their marks (navigates or changes); no act is a Kernel operation or could be taken
for one; no argument reaches another computer; the arguments checked with words; her hand's rule for acts (a read never
asks, a navigation is offered at Ask first and done otherwise, a change follows her hand on its Kernel operation, what
always asks still asks, an owner's act is never hers); the export is there but nothing offers it to her model; no word
prints a key or names the line language; the Field's keys search; the scene matchers give the campaign's answers; the
first scene is well formed.

The live window, offscreen, built once on a bench seed made through Graphite's own operations (every hold of the
right-click's tests in place, nothing starts): navigation leaves no record behind; an act typed in the writing line runs
and is journaled as the owner's; help and ops know the acts; a change act follows her dial with its card, trail and Undo;
the right-click's change rows and dialogs are refused; the head's menus never block; the command search prints no key;
read.desk reads the centre; less motion holds; one journal line per act.
"""
import json,os,platform,re,subprocess,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from workbench import desk_acts,stacy_hand
from workbench.desk_acts import ACTS,Refusal,check,desk_hers

ROOT=Path(__file__).resolve().parent.parent
P01=ROOT/'tools/campaign_lib/data/scenes/P01.json'
WINDOW={}
BENCH='parameter,value,unit\nRail voltage,12,V\nSettled current,280,mA\nStartup current,650,mA\nStartup duration,110,ms\n'
REV_A='parameter,value,unit,conditions\nPulse duration,120,ms,\nPulse ceiling,,,Up to 120 ms\n'
REV_B='parameter,value,unit,conditions\nPulse duration,80,ms,\nPulse ceiling,,,Up to 80 ms\n'
SEED=(('07 Bench readings.csv',BENCH),('07 Limits Rev A ARCHIVED.csv',REV_A),('07 Limits Rev B CURRENT.csv',REV_B))
OWNER_ONLY={'hand.approve','hand.undo','hand.dial','look.set','type.send'}
# The tables reading writes to: the journal's own (a read of the journal makes its bookkeeping) and the Kernel's audit of
# every request that is not an observer's. Measured once on a run of reads only; every other table must hold as many rows
# after the navigations as before (a table a read creates empty counts as none).
JOURNAL={'activity_journal','activity_consumers','activity_meta','audit'}


def no_logind(request):
    if request[0]=='logind':raise OSError('Caller does not belong to any known session')
    raise AssertionError('No session or power call: %r'%(request,))


def build_window(store,prefix):
    """One window for a module, every hold of the right-click's tests in place before it is built, on the bench seed: the
    bench readings and two revisions of the limits, written and imported through Graphite's own operations."""
    temporary=tempfile.TemporaryDirectory(prefix=prefix);run=Path(temporary.name)
    env=patch.dict(os.environ,{'ARC_LEDGER_EMBEDDED':'1','ARC_LEDGER_DISABLE_BOOK_WATCHER':'1','ARC1_WORKBENCH_CONFIG_HOME':str(run/'profile'),
                               'ARC_LEDGER_CONCERN':str(run/'Concern')});env.start()
    os.environ.pop('ARC_LEDGER_XSESSION',None)
    from PySide6.QtCore import QProcess
    from PySide6.QtWidgets import QMessageBox
    from workbench import clip,locations,session_power
    from workbench.engineering_kernel import Kernel,operator
    from workbench.qt_app import WorkbenchWindow,make_app
    from workbench.session import Session
    holds=[patch.object(clip,'_request',side_effect=AssertionError('No provider request')),patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')),
           patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')),patch.object(session_power,'system',side_effect=no_logind),
           patch.object(QMessageBox,'question',return_value=QMessageBox.No)]
    for h in holds:h.start()
    app=make_app([]);root=locations.office(run/'workspace');session=Session(run/'profile/session.json',root)
    k=Kernel(root);p=operator()
    files_root=Path(k.dispatch('files.list',{},p)['result']['root'])
    for name,text in SEED:
        assert k.dispatch('files.write',{'path':'seed/'+name,'text':text},p)['ok']
        plan=k.dispatch('office.import.preview',{'path':str(files_root/'seed'/name)},p)['result']
        assert k.dispatch('office.import.commit',{'plan':plan['id'],'expected_digest':plan['digest']},p)['ok']
    w=WorkbenchWindow(root,session,restore=False);platform.processor()
    late=[patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')),patch.object(os,'system',side_effect=AssertionError('No shell command')),
          patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program'))]
    for h in late:h.start()
    w.resize(1920,1200);w.show()
    store.update(app=app,w=w,k=w.ledger_bridge.kernel,temporary=temporary,holds=holds+late,env=env,files=files_root)
    settle(store,60);w.ledger_bridge.timer.stop()
    try:w.type_bar.hatch.lifecycle.timer.stop()
    except AttributeError:pass
    w.activateWindow();settle(store)


def close_window(store):
    w=store.get('w')
    if w is not None:
        try:w.close();settle(store)
        except RuntimeError:pass
    for h in reversed(store.get('holds',[])):h.stop()
    if store.get('env'):store['env'].stop()
    if store.get('temporary'):store['temporary'].cleanup()


def settle(store=None,ms=30):
    from PySide6.QtTest import QTest
    store=store if store is not None else WINDOW
    w=store.get('w');app=store.get('app')
    for name in ('agenda_runner','study_idle'):
        obj=getattr(w,name,None)
        if obj is not None and hasattr(obj,'timer'):obj.timer.stop()
    for _ in range(3):app.processEvents();QTest.qWait(ms)


def act(name,args=None,store=None,**kw):
    from workbench.desk_doers import run
    store=store if store is not None else WINDOW
    kw.setdefault('door','script');kw.setdefault('origin','desk-script:test')
    out=run(store['w'],name,args or {},**kw);settle(store);return out


def journal(store=None,origin=None):
    from workbench import activity
    store=store if store is not None else WINDOW
    events=activity.tail(store['w'].root,limit=2000).get('events',[])
    return [e for e in events if origin is None or e.get('origin')==origin]


def setUpModule():
    build_window(WINDOW,'graphite-desk-acts-')


def tearDownModule():
    close_window(WINDOW)


class PureRules(unittest.TestCase):
    def test_forty_acts_and_their_marks(self):
        from workbench.engineering_kernel import CAPABILITIES
        self.assertTrue(30<=len(ACTS)<=40,len(ACTS))
        self.assertEqual(len(ACTS),40)
        for name,a in ACTS.items():
            self.assertIn(a.mark,('navigates','changes'),name)
            self.assertEqual(a.schema['type'],'object',name);self.assertIs(a.schema['additionalProperties'],False,name)
            self.assertLessEqual(set(a.schema.get('required',[])),set(a.schema['properties']),name)
            if a.kernel:self.assertNotEqual(CAPABILITIES[a.kernel],'read',name)
            if a.mark=='changes':self.assertTrue(a.kernel or a.owner_only or a.line_decides,name)
        self.assertEqual({n for n in ACTS if ACTS[n].mark=='changes'},{n for n in ACTS if n.startswith(('hand.','look.'))})
        self.assertEqual({n for n in ACTS if ACTS[n].owner_only},OWNER_ONLY)

    def test_no_act_is_a_kernel_name(self):
        from workbench.engineering_kernel import CAPABILITIES
        self.assertFalse(set(ACTS)&set(CAPABILITIES))
        self.assertTrue(set(desk_acts.ACT_HEADS).isdisjoint({o.split('.')[0] for o in CAPABILITIES}))
        recorded=json.loads((ROOT/'docs/GRAPHITE_0.1_REGISTRY.json').read_text())['operations']
        self.assertFalse(set(ACTS)&set(recorded))
        self.assertTrue(all(desk_acts.looks_like_act(n) for n in ACTS))
        self.assertFalse(any(desk_acts.looks_like_act(o) for o in CAPABILITIES))

    def test_no_argument_leaves(self):
        self.assertFalse({p for a in ACTS.values() for p in a.schema['properties']}&set(stacy_hand.LEAVES))

    def test_check(self):
        self.assertEqual(check('go.field',{'face':'apps'}),{'face':'apps'})
        self.assertEqual(check('sheet.whatif',{'cell':'B4','value':100}),{'cell':'B4','value':'100'})
        for args,code,words in (({'face':'kitchen'},'BAD_ARGUMENTS','face is one of work, apps, network.'),
                                ({'colour':'x'},'BAD_ARGUMENTS','go.field takes face, by; it was given colour.')):
            with self.assertRaises(Refusal) as caught:check('go.field',args)
            self.assertEqual((caught.exception.code,caught.exception.words),(code,words))
        with self.assertRaises(Refusal) as caught:check('go.open',{})
        self.assertEqual(caught.exception.words,'go.open needs one of sheet, path, tab.')
        with self.assertRaises(Refusal) as caught:check('go.feild',{})
        self.assertEqual(caught.exception.code,'UNKNOWN_ACT');self.assertIn('There is no act named “go.feild”',caught.exception.words)
        with self.assertRaises(Refusal) as caught:check('type.put',{'text':'x'*4001})
        self.assertEqual(caught.exception.words,'text is too long.')
        with self.assertRaises(Refusal):check('go.pane',{})

    def test_desk_hers(self):
        places=('ask','show','free')
        self.assertEqual([desk_hers(p,'read.desk')[0] for p in places],[True,True,True])
        self.assertEqual([desk_hers(p,'go.field')[0] for p in places],[False,True,True])
        self.assertEqual(desk_hers('ask','go.field')[1],'it moves your window, and my hand is at Ask first')
        self.assertEqual([desk_hers(p,'hand.write',{'path':'a','text':'b'})[0] for p in places],[False,True,True])
        self.assertEqual([desk_hers(p,'hand.rename',{'path':'a','name':'b'})[0] for p in places],[False,False,False])
        self.assertEqual(desk_hers('show','hand.rename',{'path':'a','name':'b'})[1],'it is not among the things I do by myself')
        self.assertEqual(desk_hers('free','hand.step',{'n':1},line='/trash.empty {}'),(False,'the Trash, once emptied, cannot be brought back'))
        for name in OWNER_ONLY:
            self.assertEqual([desk_hers(p,name)[0] for p in places],[False,False,False],name)
        self.assertEqual(desk_acts.HAND_RULE['navigates'],{'ask':'offered','show':'done','free':'done'})

    def test_exported_but_not_offered(self):
        from workbench import local_brain,tool_selection
        exported={t['name'] for t in desk_acts.tools()}
        self.assertEqual(len(exported),35);self.assertTrue(exported.isdisjoint(OWNER_ONLY))
        self.assertTrue(exported.isdisjoint(local_brain.DIRECT_OPERATIONS));self.assertTrue(exported.isdisjoint(local_brain.CORE_OPERATIONS))
        for message in ('open the field','trace the bench readings','put it in the writing line','zoom out'):
            schema=local_brain.proposal_profile(message)[0]
            offered={v['properties']['operation']['const'] for v in schema['properties']['actions']['items']['oneOf']}
            self.assertTrue(offered.isdisjoint(set(ACTS)),message)
        self.assertLessEqual({'ledger.navigate','ledger.open'},tool_selection.DENY)
        for variant in desk_acts.plan_variants():
            self.assertIn('act',variant['properties']);self.assertNotIn('operation',variant['properties'])
        for name in exported:self.assertLessEqual(len(desk_acts.compact(ACTS[name].schema)),300,name)
        # The plan's 9,000 bytes were not reachable: the 35 wrappers alone are about 4,200. Measured: 10,940.
        self.assertLessEqual(len(desk_acts.compact(desk_acts.plan_variants())),11000)

    def test_words_print_no_key_and_never_name_the_language(self):
        from tests_integrated.test_context_menu import key_literals
        self.assertEqual(key_literals(['workbench/desk_acts.py','workbench/desk_doers.py','workbench/desk_scene.py']),[])
        words=[a.words for a in ACTS.values()]+list(desk_acts.REFUSALS.values())+[json.dumps(desk_acts.HAND_RULE)]
        for text in words:self.assertIsNone(re.search(r'(?i)\bstac\b|stacy language|\bprograms\b',text),text)

    def test_key_path(self):
        from workbench.field_model import Field,FieldLink,FieldObject
        objects=[FieldObject('a','source','A'),FieldObject('b','source','B'),FieldObject('c','sheet','C'),FieldObject('d','sheet','D'),
                 FieldObject('e','calculation','E')]
        f=Field(objects,[FieldLink('b','e')])
        import itertools

        def replay(start,ways):
            f.selected=start
            for way in ways:
                {'first':lambda:f.select(f.first()),'last':lambda:f.select(f.last()),'next_waiting':f.next_attention}.get(way,lambda w=way:f.move(w))()
            return f.selected
        self.assertEqual(desk_acts.key_path(f,'a','a'),[])
        for start,goal in (('a','e'),('e','a'),('c','b'),('d','a')):
            f.select('a');path=desk_acts.key_path(f,start,goal)
            self.assertEqual(f.selected,'a','the search puts the selection back')
            self.assertIsNotNone(path,(start,goal))
            self.assertEqual(replay(start,path),goal,(start,goal,path))
            for length in range(len(path)):      # nothing shorter reaches it
                for ways in itertools.product(desk_acts.WAYS,repeat=length):self.assertNotEqual(replay(start,ways),goal,(start,goal,ways))
        f.select('a')

    def test_matches_mirror_the_campaign(self):
        from tools.campaign_lib import core
        from workbench import desk_scene
        pairs=[(3,3),('a','b'),({'contains':'x'},['ax']),({'contains':'q'},'abc'),({'startswith':'/f'},'/files'),({'startswith':'x'},3),
               ({'in':[1,2]},2),({'in':[1,2]},5),({'decimal':'3.60'},'18/5'),({'decimal':'1'},'x'),({'gte':2},3),({'lte':2},'1'),
               ({'between':[1,3]},2),({'not':{'contains':'Programs'}},['Apps'])]
        self.assertEqual(len(pairs),14)
        for want,got in pairs:self.assertEqual(desk_scene.matches(want,got),core.matches(want,got),(want,got))
        self.assertFalse(desk_scene.matches({'not':1},desk_scene.NOT_OBSERVED))

    def test_p01_is_well_formed(self):
        from workbench import desk_scene
        scene=desk_scene.load(P01)
        self.assertEqual(desk_scene.check_scene(scene),[])
        for step in scene['steps']:
            self.assertIn(step['act'],ACTS);check(step['act'],step.get('args',{}))
        self.assertEqual([r['name'] for r in scene['runs']],['mouse','keys','mouse_still','keys_still'])
        self.assertEqual(desk_scene.check_scene({'schema':'graphite.scene/1','id':'x','runs':[{'name':'a','style':'pointer'}],
                                                 'steps':[{'act':'go.nowhere'}]}),["step 1: no act named 'go.nowhere'"])


class LiveActs(unittest.TestCase):
    def setUp(self):
        self.w=WINDOW['w'];act('menu.close');act('hand.dial',{'place':'show'})
        box=self.w.type_bar.box
        if box.text():box.clear()
        self.w._desk_put=''

    def counts(self):
        from tools.campaign_lib import fixture
        counts=fixture.state_digest(WINDOW['k'])[1]['counts']
        return {t:n for t,n in counts.items() if t not in JOURNAL}

    def listing(self):
        from workbench.engineering_kernel import operator
        k=WINDOW['k'];p=operator()
        names=sorted(e['path'] for e in k.dispatch('files.list',{'all':True},p)['result']['entries'])
        office=k.dispatch('office.list',{},p)['result']
        return names,json.dumps(office,sort_keys=True,default=str)

    def test_navigation_changes_no_record(self):
        before=self.counts();files_before=self.listing()
        steps=[('go.field',{}),('point.sheet',{'title':'07 Bench readings','by':'direct'}),('point.sheet',{'title':'07 Limits Rev B CURRENT','by':'pointer'}),
               ('point.sheet',{'title':'07 Bench readings','by':'keys'}),('point.zoom',{'to':'whole'}),('go.files',{}),('head.open',{'menu':'Tools'}),
               ('menu.close',{}),('go.today',{}),('go.pane',{'left':'machine','right':'activity'}),('read.desk',{})]
        for name,args in steps:
            out=act(name,args)
            self.assertTrue(out['ok'],(name,out['words']))
        after=self.counts()
        self.assertEqual({t:(before.get(t,0),after.get(t,0)) for t in set(before)|set(after) if before.get(t,0)!=after.get(t,0)},{})
        self.assertEqual(self.listing(),files_before)
        act('go.pane',{'left':'files','right':'talk'})

    def test_typed_act_in_the_writing_line(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from tests_integrated.test_context_menu import KEY_TEXT
        w=self.w;box=w.type_bar.box
        w.type_bar.set_target('slate',focus=True);settle()
        box.setFocus();QTest.keyClicks(box,'/go.field face=apps');settle()
        rows=[box.popup.list.item(i).text() for i in range(box.popup.list.count())]
        self.assertTrue(any(r.startswith('Act') for r in rows),rows)
        QTest.keyClick(box,Qt.Key_Return);settle(ms=60)
        self.assertTrue(w._field_active);self.assertEqual(w.field_page.face,'programs')
        output=w.console.output.toPlainText()
        self.assertIn('graphite › go.field face=apps',output)
        tail=output[output.rfind('graphite › go.field face=apps'):]
        self.assertNotIn('refused',tail)
        last=journal()[-1]
        self.assertEqual((last['operation'],last['origin'],last['state']),('go.field','desktop-owner','DONE'))
        w.console.run_kernel('go.feild');settle()
        output=w.console.output.toPlainText()
        self.assertIn('There is no act named “go.feild”',output)
        self.assertIsNone(re.search(KEY_TEXT,output[output.rfind('graphite › go.field'):]))
        self.assertIsNone(re.search(r'(?i)\bstac\b',output[output.rfind('graphite › go.field'):]))
        act('go.field',{'face':'work'})

    def test_help_and_ops(self):
        console=self.w.console
        def said(line):
            console.run_kernel(line);settle();out=console.output.toPlainText();return out[out.rfind('graphite › '+line):]
        text=said('help go.field');self.assertIn('navigates',text);self.assertIn('face',text)
        self.assertIn('files.write',said('help hand.write'))
        self.assertIn('yours only',said('help hand.undo'))
        text=said('ops sheet.');self.assertIn('sheet.trace',text);self.assertIn('sheet.compare',text)
        text=said('help acts');self.assertEqual(sum(1 for name in ACTS if re.search(r'(?m)^%s\b'%re.escape(name),text)),40)
        console.prompt.setText('go.fi');console.mode='kernel';console.complete()
        self.assertIn(console.prompt.text(),('go.field','go.fi'))

    def test_change_acts_follow_her_dial(self):
        state=self.w.session.state
        act('hand.dial',{'place':'show'})
        out=act('hand.write',{'path':'hand test.txt','text':'x'})
        self.assertTrue(out['ok'],out['words'])
        r=out['result'];self.assertEqual((r['ran'],r['hers']),(True,True))
        self.assertEqual(r['undo'],'/files.trash {"path": "hand test.txt"}')
        self.assertTrue(stacy_hand.trail(state)[0]['line'].startswith('/files.write'))
        out=act('hand.undo');self.assertTrue(out['ok'],out['words'])
        self.assertEqual(stacy_hand.trail(state)[0]['state'],'undone')
        act('hand.dial',{'place':'ask'})
        out=act('hand.write',{'path':'hand test 2.txt','text':'x'})
        self.assertTrue(out['ok'],out['words']);self.assertTrue(out['result']['waits'])
        self.assertEqual(journal(origin='desk-script:test')[-1]['state'],'WAITING')
        from workbench.desk_doers import waiting_cards
        self.assertIsNone(waiting_cards(self.w)[-1].ran)
        length=len(stacy_hand.trail(state))
        out=act('hand.approve',{},door='owner',origin='desktop-owner')
        self.assertTrue(out['ok'],out['words']);self.assertTrue(out['result']['ran'])
        self.assertEqual(len(stacy_hand.trail(state)),length,'the owner\'s Approve is not her act')
        act('hand.dial',{'place':'show'})
        out=act('hand.rename',{'path':'hand test 2.txt','name':'renamed.txt'})
        self.assertTrue(out['result']['waits'])
        self.assertEqual(out['result']['why'],stacy_hand.why_waits('show','execute','files.rename'))
        out=act('hand.approve',{},door='her')
        self.assertEqual(out['error']['code'],'NOT_OFFERED')
        from workbench.engineering_kernel import operator
        WINDOW['k'].dispatch('files.trash',{'path':'hand test 2.txt'},operator())

    def test_menu_choose_refuses_change_rows_and_dialogs(self):
        from PySide6.QtWidgets import QApplication
        from workbench.engineering_kernel import operator
        k=WINDOW['k'];k.dispatch('files.write',{'path':'menu test.csv','text':BENCH},operator())
        self.assertTrue(act('go.files',{'view':'list'})['ok'])
        for path,code in (('trash','CHANGES_ROW'),('ask','DIALOG')):
            out=act('menu.open',{'on':'file','name':'menu test.csv'});self.assertTrue(out['ok'],out['words'])
            out=act('menu.choose',{'path':path})
            self.assertEqual(out['error']['code'],code,out['words'])
            if code=='CHANGES_ROW':self.assertIn('hand.trash',out['words'])
            self.assertIsNone(QApplication.activeModalWidget())
            act('menu.close')
        self.assertIn('menu test.csv',act('read.desk',{'part':'files'})['result']['names'])
        act('menu.open',{'on':'file','name':'menu test.csv'})
        out=act('menu.choose',{'path':'more/copy:path'});self.assertTrue(out['ok'],out['words'])
        act('menu.close');k.dispatch('files.trash',{'path':'menu test.csv'},operator())

    def test_head_acts_never_block(self):
        from workbench.tool_faces import named
        started=time.monotonic();out=act('head.open',{'menu':'Tools','by':'pointer'})
        self.assertLess(time.monotonic()-started,2.0)
        self.assertTrue(out['ok']);self.assertTrue(out['result']['open']);self.assertIn('System Check',out['result']['rows'])
        act('menu.close')
        out=act('head.open',{'menu':'Apps'});self.assertTrue(self.w.type_bar.hatch.programs.isVisible())
        self.assertNotIn('Programs',out['result']['rows'])
        act('menu.close')
        out=act('head.row',{'menu':'Work','row':'Log out'});self.assertEqual(out['error']['code'],'NOT_ALLOWED_ROW')
        top=self.w.shell2.top
        for menu,rows in desk_acts.HEAD_ROWS.items():
            word=next(b for b in top.menu_words() if b.text()==menu);words={desk_acts.row_words(a.text()) for a in word.menu().actions()}
            for row in rows:self.assertIn(row,words,(menu,row))
        self.assertEqual(act('read.desk',{'part':'where'})['result']['popups'],[])

    def test_command_search_prints_no_key(self):
        bar=self.w.type_bar;box=bar.box
        bar.set_target('find',focus=True);settle()
        from PySide6.QtTest import QTest
        QTest.keyClicks(box,'field');settle()
        rows=[box.popup.list.item(i).text() for i in range(box.popup.list.count())]
        self.assertTrue(rows)
        for row in rows:
            self.assertIsNone(re.search(r'\s(F\d{1,2}|Alt\+\d|Ctrl\+\w)\s*$',row),row);self.assertNotIn('\t',row)
        box.clear();box.popup.hide();bar.set_target('slate',focus=False)

    def test_read_desk_reads_the_centre(self):
        self.assertTrue(act('go.files',{})['ok'])
        self.assertTrue(act('go.field',{})['ok'])
        from workbench.files_qt import FilesTab
        self.assertIsInstance(self.w.tabs.currentWidget(),FilesTab)
        self.assertEqual(act('read.desk',{'part':'where'})['result']['surface'],'field')

    def test_look_set_motion(self):
        from workbench import boss_theme,menu_catch
        act('go.field',{})
        out=act('look.set',{'motion':'reduced'},door='owner',origin='desktop-owner')
        self.assertTrue(out['ok'],out['words'])
        self.assertIs(self.w.field_page.view.still(),True);self.assertIs(menu_catch.calm(self.w),True)
        self.assertIs(self.w.session.state['reading_profile']['reduce_motion'],True)
        self.assertEqual(out['result']['before']['motion'],'normal')
        out=act('look.set',{'appearance':'kasandra'},door='owner',origin='desktop-owner')
        self.assertEqual(out['result']['next'],'kasandra');self.assertEqual(out['result']['in_force'],boss_theme.APPEARANCE)
        act('look.set',{'appearance':'graphite','motion':'normal'},door='owner',origin='desktop-owner')
        self.assertIs(menu_catch.calm(self.w),False)

    def test_one_record_per_act(self):
        before=len(journal(origin='desk-script:test'))
        for name,args in (('go.field',{}),('point.zoom',{'to':'whole'}),('point.sheet',{'title':'07 Bench readings'}),('read.desk',{}),
                          ('point.move',{'way':'first'}),('go.files',{}),('head.open',{'menu':'Guide'}),('menu.close',{}),('go.today',{}),
                          ('go.open',{'tab':0})):
            act(name,args)
        self.assertEqual(len(journal(origin='desk-script:test'))-before,9)


if __name__=='__main__':
    unittest.main()
