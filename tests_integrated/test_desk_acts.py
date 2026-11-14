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
right-click's tests in place, nothing starts): every act that navigates, swept, leaves no record, no open outside Graphite
and no program started; an act typed in the writing line runs and is journaled as the owner's; help and ops know the acts;
a change act follows her dial with its card, trail and Undo, and never writes over a file by herself; Approve reports the
card it approved; a right-click row is chosen only when listed, so the rows that change, leave or ask are refused; a
window that asks stops an act, and the refusal says what was done before it; Documents is not started by opening it; a
what-if never asks her model; type.put types any character and never a line break; the head's menus never block; the
command search prints no key; read.desk reads the centre; less motion holds; one journal line per act.

The 0.8.2 review (findings 1 to 11) is what the sweep, the rows and the typing tests hold the acts to.
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
# The tables reading writes to: the journal's own (a read of the journal makes its bookkeeping), the Kernel's audit of
# every request that is not an observer's, and the instruction matrix, which records every line that runs (a read line
# too: Then, a trace, a doubt), as it does when the owner runs one by hand. Measured on runs of reads only; every other
# table must hold as many rows after the navigations as before (a table a read creates empty counts as none).
JOURNAL={'activity_journal','activity_consumers','activity_meta','audit','instruction_matrix'}


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
        # A carriage return is the writing line's Return: type.put would send. No character no one sees goes in either.
        for text in ('rm -rf x\r','a\nb','a\tb','\x01','\x7f','a b','‮evil','zero​width'):
            with self.assertRaises(Refusal) as caught:check('type.put',{'text':text})
            self.assertEqual((caught.exception.code,caught.exception.words),('BAD_ARGUMENTS',desk_acts.REFUSALS['UNSEEN']%'text'),repr(text))
        for text in ('“07”','Ω ≥ 3 · 電流',"Graphite's Agenda",'a b'):self.assertEqual(check('type.put',{'text':text})['text'],text)
        with self.assertRaises(Refusal) as caught:check('sheet.whatif',{'cell':'B3','value':'please'})
        self.assertEqual(caught.exception.words,'value is a number.')
        self.assertEqual(desk_acts.ACTS['type.send'].schema['properties']['by']['enum'],['arrow','keys'],'no key name as an argument value')

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
        # Given the arguments, the act's own rules come first: never a line break in the line, never a row off the lists.
        self.assertEqual(desk_hers('free','type.put',{'text':'rm -rf x\r','by':'keys'}),(False,desk_acts.REFUSALS['UNSEEN']%'text'))
        self.assertEqual(desk_hers('show','type.put',{'text':'hello'}),(True,''))
        for path in ('more/open:outside','more/delivery:stage','more/edit:delete','more/menu:edit','ask','Move to Trash','more/explain','field:ask',
                     'field:whatif/field:whatif:B3/field:whatif:B3:other','field:words/words:new'):
            self.assertFalse(desk_hers('free','menu.choose',{'path':path})[0],path)
        for path in ('more/copy:path','then','field:do/field:do:0','more/field:trace/field:trace:all','step:where/field:unit/where unit=mA'):
            self.assertEqual(desk_hers('show','menu.choose',{'path':path}),(True,''),path)
        self.assertFalse(desk_hers('show','go.field',{'face':'kitchen'})[0])

    def test_menu_rows_are_listed_by_their_keys(self):
        listed=desk_acts.listed
        for key in ('copy:path','field:do:2','field:trace:all','field:face:network','start:seed/a.csv','line:shell','extract:rows','open'):
            self.assertTrue(listed(key,desk_acts.MENU_ROWS),key)
        # The rows the review found changing or leaving with no operation named, and the rows that ask or change
        for key in ('open:outside','delivery:stage','menu:edit','edit:delete','edit:cut','edit:paste','edit:undo','mark:bold','style:h1','notes',
                    'ask','field:ask','explain','adapter:calculate','words:new','import','doc:new','chains:mine','inquiries','trash','rename','agenda'):
            self.assertFalse(listed(key,desk_acts.MENU_ROWS),key)
        for key in ('step:where','field:unit','where unit=mA','where:other','step:count','step:back','back','end:line','end:show'):
            self.assertTrue(listed(key,desk_acts.PANEL_ROWS),key)
        self.assertFalse(listed('end:keep',desk_acts.PANEL_ROWS))
        source=(ROOT/'workbench/context_menu.py').read_text(encoding='utf-8')
        for key in desk_acts.MENU_ROWS+tuple(k for k in desk_acts.PANEL_ROWS if k!='where '):
            self.assertIn("'%s"%key,source,'a listed row the right-click does not make: %s'%key)

    def test_run_needs_its_door(self):
        import inspect
        from workbench.desk_doers import run
        self.assertIs(inspect.signature(run).parameters['door'].default,inspect.Parameter.empty)
        with self.assertRaises(TypeError):run(None,'go.field',{})

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
            self.assertNotIn('by',variant['properties']);self.assertNotIn('arguments',variant['properties'])
            self.assertEqual(variant['required'][0],'act');self.assertIs(variant['additionalProperties'],False)
        self.assertFalse(any('act' in a.schema['properties'] for a in ACTS.values()),'an argument named act would collide in the flat choices')
        self.assertFalse(any('by' in t['arguments']['properties'] for t in desk_acts.tools()),'how the hand moves is never hers to choose')
        for name in exported:self.assertLessEqual(len(desk_acts.compact(ACTS[name].schema)),300,name)
        # The plan's 9,000 bytes: flat choices without `by` measure 6,327 (wrapped in `arguments` with `by` they were 10,940).
        self.assertLessEqual(len(desk_acts.compact(desk_acts.plan_variants())),9000)

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

    def changed(self,before):
        after=self.counts()
        return {t:(before.get(t,0),after.get(t,0)) for t in set(before)|set(after) if before.get(t,0)!=after.get(t,0)}

    def test_every_navigation_changes_nothing(self):
        """Every act that navigates and may one day be hers, swept with the arguments a person would use: no record changes
        (the journal's own tables and the matrix of lines run aside), Files holds the same, nothing is opened outside
        Graphite, no program starts, and each act's own account of what it changed is empty."""
        from PySide6.QtCore import QProcess
        from PySide6.QtGui import QDesktopServices
        from workbench import chain_menu
        w=self.w;left=[];swept=set();refused={}
        holds=[patch.object(QDesktopServices,'openUrl',side_effect=lambda url:left.append(url.toString()) or True),
               patch.object(QProcess,'start',side_effect=lambda *a,**k:left.append(('a program started',a[1:])))]
        for h in holds:h.start()
        try:
            before=self.counts();files_before=self.listing();menu_file=chain_menu.menu_path().exists()

            def go(name,args=None,code=None):
                out=act(name,args or {});swept.add(name)
                self.assertEqual(out['changed'],[],(name,args))
                if code is None:self.assertTrue(out['ok'],(name,args,out['words']))
                elif code!='either':self.assertEqual((out['error'] or {}).get('code'),code,(name,args,out['words']))
                if not out['ok']:refused[(name,json.dumps(args or {}))]=out['error']['code']
                return out
            for menu in desk_acts.HEAD_MENUS+('Apps',):go('head.open',{'menu':menu});go('menu.close')
            go('head.open',{'menu':'Tools','by':'keys'});go('menu.close')
            for menu,rows in desk_acts.HEAD_ROWS.items():
                for row in rows:go('head.row',{'menu':menu,'row':row});go('menu.close')
            for which in ('CPU','GPU','RAM','TXT','equalizer'):go('head.meter',{'which':which});go('menu.close')
            go('head.open',{'menu':'Apps'});keys=list(w.type_bar.hatch.programs.rows_by_key);go('menu.close')
            self.assertGreater(len(keys),20)
            for key in keys:
                # Documents with none starts one as it opens: refused, and nothing made (whichever this window has now)
                go('go.app',{'key':key},'either' if key=='documents' else None);go('menu.close')
            for left_pane,right_pane in (('machine','activity'),('settings','context'),('files','talk')):go('go.pane',{'left':left_pane,'right':right_pane})
            go('go.today',{});go('go.today',{'by':'keys'})
            go('go.files',{'folder':'seed','view':'icons'});go('go.files',{'folder':'seed','view':'list'})
            go('go.open',{'path':'07 Bench readings.csv'});go('go.open',{'tab':0})
            go('go.files',{'folder':'seed','view':'list'})
            for how in ('show','line','copy','rows'):
                go('menu.open',{'on':'file','name':'07 Bench readings.csv'});go('menu.choose',{'path':'then'})
                go('then.keep',{'column':'unit','words':'is mA'});go('then.count');go('then.back');go('then.end',{'how':how})
                w.type_bar.box.clear();w._desk_put='';go('menu.close')
            go('menu.open',{'on':'file','name':'07 Bench readings.csv','by':'keys'});go('menu.choose',{'path':'more/copy:path'});go('menu.close')
            go('menu.open',{'on':'here'});go('menu.close')
            go('go.field',{});go('go.field',{'by':'keys'})
            for to in ('whole','larger','smaller','reading','whole'):go('point.zoom',{'to':to})
            go('point.sheet',{'title':'07 Bench readings','by':'pointer'});go('point.sheet',{'title':'07 Limits Rev B CURRENT','by':'keys'})
            go('point.sheet',{'title':'07 Bench readings'})
            for way in ('first','last','right','left'):go('point.move',{'way':way})
            go('point.sheet',{'title':'07 Bench readings'})
            for by in ('pointer','keys'):
                go('sheet.trace',{'by':by});go('sheet.close',{'by':by});go('sheet.doubt',{'by':by});go('sheet.close',{'by':by})
                go('sheet.steps',{'by':by});go('menu.close');go('sheet.close',{'by':by})
            go('menu.open',{'on':'sheet','name':'07 Bench readings'});go('menu.choose',{'path':'field:do/field:do:0'});go('menu.close');go('sheet.close')
            go('sheet.whatif',{'cell':'B3','value':'300'},'NOT_HERE')      # the bench's sheets hold words, not numbers
            go('point.sheet',{'title':'07 Limits Rev B CURRENT'})
            for by in ('pointer','keys'):go('sheet.compare',{'by':by});go('sheet.close',{'by':by})
            go('go.open',{'sheet':'07 Bench readings'});go('go.field',{'face':'apps'})
            go('point.sheet',{'id':w.field_page.view.field.objects[0].id})
            go('sheet.whatif',{'cell':'B3','value':'300'},'NOT_HERE')
            go('go.field',{'face':'network'});go('go.field',{'face':'work'});go('go.back',{})
            for who in ('terminal','search','web','log','her'):go('type.to',{'who':who})
            go('type.put',{'text':'“07” Ω ≥ 3','by':'keys'});w.type_bar.box.clear();w._desk_put=''
            go('type.put',{'text':'hello'});w.type_bar.box.clear();w._desk_put=''
            for size in ('tall','half','line'):go('type.room',{'size':size})
            go('read.desk',{})
            self.assertEqual(self.changed(before),{})
            self.assertEqual(self.listing(),files_before)
            self.assertEqual(left,[])
            self.assertEqual(chain_menu.menu_path().exists(),menu_file)
            navigations={n for n,a in ACTS.items() if a.mark=='navigates' and a.exported}
            self.assertEqual(len(navigations),30);self.assertEqual(navigations-swept,set())
            self.assertLessEqual(set(refused.values()),{'NOT_HERE','MAKES'},refused)
        finally:
            for h in reversed(holds):h.stop()
            act('menu.close');act('go.pane',{'left':'files','right':'talk'})

    def test_go_app_documents_is_not_started(self):
        from workbench.engineering_kernel import operator
        k=WINDOW['k']
        self.assertEqual(k.dispatch('documents.list',{},operator())['result']['documents'],[],'the bench holds no document yet')
        before=self.counts()
        out=act('go.app',{'key':'documents'})
        self.assertEqual(out['error']['code'],'MAKES');self.assertEqual(out['changed'],[])
        self.assertIn('a new document',out['words'])
        self.assertEqual(self.changed(before),{})
        self.assertEqual(k.dispatch('documents.list',{},operator())['result']['documents'],[])

    def test_dialog_stops_an_act_and_says_what_was_done(self):
        from PySide6.QtWidgets import QApplication,QInputDialog
        from workbench import desk_doers
        from workbench.engineering_kernel import operator
        k=WINDOW['k']

        def writes_then_asks(c):
            k.dispatch('files.write',{'path':'dialog probe.txt','text':'x'},operator())
            QInputDialog.getText(c.host,'Name','Name');return 'never',{}

        def only_asks(c):
            QInputDialog.getText(c.host,'Name','Name');return 'never',{}

        def swallows(c):
            try:QInputDialog.getText(c.host,'Name','Name')
            except Exception:pass      # noqa: BLE001 - as context_menu.perform does
            return 'went on',{}
        with patch.dict(desk_doers.DOERS,{'go.pane':writes_then_asks}):out=act('go.pane',{'left':'files'})
        self.assertEqual(out['error']['code'],'DIALOG')
        self.assertEqual(out['words'],desk_acts.REFUSALS['DIALOG']+' Before that: files.write.')
        self.assertNotIn('nothing was done',out['words']);self.assertEqual(out['changed'],['files.write'])
        self.assertIsNone(QApplication.activeModalWidget())
        for doer in (only_asks,swallows):
            with patch.dict(desk_doers.DOERS,{'go.pane':doer}):out=act('go.pane',{'left':'files'})
            self.assertEqual((out['error']['code'],out['words'],out['changed']),('DIALOG',desk_acts.REFUSALS['DIALOG'],[]),doer.__name__)
            self.assertIsNone(QApplication.activeModalWidget())
        k.dispatch('files.trash',{'path':'dialog probe.txt'},operator())

    def test_hand_write_never_writes_over_a_file(self):
        from workbench.engineering_kernel import operator
        k=WINDOW['k'];path=WINDOW['files']/'owner plan.txt'
        k.dispatch('files.write',{'path':'owner plan.txt','text':'The owner wrote this.'},operator())
        for place in ('show','free'):
            act('hand.dial',{'place':place})
            out=act('hand.write',{'path':'owner plan.txt','text':'Replaced by an act.'})
            self.assertTrue(out['ok'],out['words']);r=out['result']
            self.assertEqual((r['ran'],r['hers'],r['waits']),(None,False,True),place)
            self.assertIn('already something called “owner plan.txt” in Files',r['why'])
            self.assertEqual(path.read_text(),'The owner wrote this.')
        for _ in range(2):      # the owner's Approve writes it, as the owner's
            out=act('hand.approve',{},door='owner',origin='desktop-owner');self.assertIs(out['result']['ran'],True,out['words'])
        self.assertEqual(path.read_text(),'Replaced by an act.')
        k.dispatch('files.trash',{'path':'owner plan.txt'},operator())

    def test_hand_approve_reports_what_it_approved(self):
        from workbench.desk_doers import go_card,waiting_cards
        from workbench.engineering_kernel import operator
        w=self.w;k=WINDOW['k'];page=w.field_page
        act('hand.dial',{'place':'ask'})
        self.assertTrue(act('hand.write',{'path':'approve a.txt','text':'a'})['result']['waits'])
        act('go.field',{});act('point.sheet',{'title':'07 Bench readings'})
        steps=act('sheet.steps',{'by':'keys'})['result']['steps']
        n=next(i for i,s in enumerate(steps,1) if s['kind']=='write')
        self.assertTrue(act('hand.step',{'n':n})['result']['waits']);self.assertTrue(page.view.go)
        watch=go_card(page);self.assertIsNotNone(watch)
        act('hand.write',{'path':'approve b.txt','text':'b'})
        latest=waiting_cards(w)[-1];self.assertIsNot(latest,watch)
        page.view.setFocus();settle()
        # G would approve the go's card, not the latest: the latest's Approve is clicked, and that is the card read back
        out=act('hand.approve',{'by':'keys'},door='owner',origin='desktop-owner')
        self.assertTrue(out['ok'],out['words']);self.assertEqual(out['by'],'pointer')
        self.assertIs(out['result']['ran'],True);self.assertIs(latest.ran,True);self.assertIsNone(watch.ran)
        self.assertTrue((WINDOW['files']/'approve b.txt').exists())
        # the go's card the latest: G is pressed, and the card read back is the one it approved
        act('point.sheet',{'title':'07 Bench readings'});act('sheet.steps',{'by':'keys'})
        self.assertTrue(act('hand.step',{'n':n})['result']['waits'])
        again=go_card(page);self.assertIs(waiting_cards(w)[-1],again)
        page.view.setFocus();settle()
        out=act('hand.approve',{'by':'keys'},door='owner',origin='desktop-owner')
        self.assertTrue(out['ok'],out['words']);self.assertEqual(out['by'],'keys')
        self.assertIsNotNone(again.ran);self.assertEqual(out['result']['ran'],again.ran)
        for _ in range(8):      # what still waits, approved by the owner so that nothing is left waiting
            if not waiting_cards(w):break
            act('hand.approve',{},door='owner',origin='desktop-owner')
        for name in ('approve a.txt','approve b.txt'):k.dispatch('files.trash',{'path':name},operator())
        act('sheet.close');act('go.back',{})

    def test_sheet_whatif_never_asks_her_model(self):
        from workbench import shell2
        w=self.w;face=w.shell2.face;asked=[]
        real=shell2.call
        ready=lambda host,op,args=None:{'state':'READY'} if op=='brain.status' else real(host,op,args)
        before=self.counts()
        with patch.object(type(face),'ask',lambda f,text,about=None:asked.append(text)),patch.object(shell2,'call',ready):
            act('go.field',{'face':'apps'});act('point.sheet',{'id':w.field_page.view.field.objects[0].id})
            out=act('sheet.whatif',{'cell':'B3','value':'300'})
            self.assertEqual(out['error']['code'],'NOT_HERE');self.assertIn('is neither',out['words'])
            act('go.field',{'face':'work'});act('point.sheet',{'title':'07 Bench readings'})
            out=act('sheet.whatif',{'cell':'B3','value':'300'})
            self.assertEqual(out['error']['code'],'NOT_HERE');self.assertEqual(out['changed'],[])
            self.assertEqual(act('sheet.whatif',{'cell':'B3','value':'please'})['error']['code'],'BAD_ARGUMENTS')
        self.assertEqual(asked,[]);self.assertEqual(self.changed(before),{})
        act('sheet.close');act('go.back',{})

    def test_type_put_types_every_character_and_never_sends(self):
        from PySide6.QtCore import QProcess
        w=self.w;box=w.type_bar.box;face=w.shell2.face;started=[];asked=[]
        with patch.object(QProcess,'start',side_effect=lambda *a,**k:started.append(a[1:])),patch.object(type(face),'ask',lambda f,text,about=None:asked.append(text)):
            for who in ('terminal','her','search'):
                act('type.to',{'who':who})
                for text in ('“07” Ω ≥ 3 · 電流',"Graphite's Agenda"):
                    out=act('type.put',{'text':text,'by':'keys'})
                    self.assertTrue(out['ok'],(who,out['words']));self.assertEqual((box.text(),out['result']['text']),(text,text))
                    self.assertEqual(out['presses'],len(text))
                    box.clear();w._desk_put=''
                for text in ('echo PWNED > pwned.txt\r','hello\n','a\x01b','a\x7fb','a b'):
                    for by in ('keys','put'):
                        out=act('type.put',{'text':text,'by':by})
                        self.assertEqual(out['error']['code'],'BAD_ARGUMENTS',(who,repr(text),by));self.assertEqual(box.text(),'')
        self.assertEqual(started,[]);self.assertEqual(asked,[])
        act('type.to',{'who':'her'});act('type.put',{'text':'my private words','by':'keys'})
        last=journal(origin='desk-script:test')[-1]      # the journal keeps that words were put, never the words
        self.assertEqual(last['operation'],'type.put');self.assertNotIn('private',json.dumps(last,ensure_ascii=False))
        box.clear();w._desk_put=''


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

    def test_menu_choose_refuses_rows_off_the_list(self):
        """A right-click row is chosen only when listed. The rows the review found changing or leaving with no operation
        named (Stage in Delivery, Open with this computer's app, Edit the Graphite menu, Delete in a document) are refused
        before they run, as are the rows that change through an operation and the rows that ask."""
        from PySide6.QtCore import QProcess
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from workbench import chain_menu
        from workbench.engineering_kernel import operator
        k=WINDOW['k'];k.dispatch('files.write',{'path':'menu test.csv','text':BENCH},operator())
        left=[];menu_file=chain_menu.menu_path().exists()
        holds=[patch.object(QDesktopServices,'openUrl',side_effect=lambda url:left.append(url.toString()) or True),
               patch.object(QProcess,'start',side_effect=lambda *a,**kw:left.append(a[1:]))]
        for h in holds:h.start()
        try:
            self.assertTrue(act('go.files',{'view':'list'})['ok'])
            before=self.counts();files_before=self.listing()
            for path,code in (('trash','CHANGES_ROW'),('rename','CHANGES_ROW'),('ask','NOT_ALLOWED_ROW'),('more/open:outside','NOT_ALLOWED_ROW'),
                              ('more/delivery:stage','NOT_ALLOWED_ROW'),('more/explain','NOT_ALLOWED_ROW'),('more/adapter:calculate','NOT_ALLOWED_ROW'),
                              ('more/investigate','CHANGES_ROW_YOURS'),('more/copy:to','CHANGES_ROW_YOURS'),('more/export','CHANGES_ROW_YOURS')):
                out=act('menu.open',{'on':'file','name':'menu test.csv'});self.assertTrue(out['ok'],out['words'])
                out=act('menu.choose',{'path':path})
                self.assertEqual(out['error']['code'],code,(path,out['words']));self.assertEqual(out['changed'],[],path)
                if path in ('trash','rename'):self.assertIn('hand.'+path,out['words'])
                self.assertIsNone(QApplication.activeModalWidget())
                act('menu.close')
            act('go.files',{'folder':'','view':'list'});act('menu.open',{'on':'here'})
            out=act('menu.choose',{'path':'more/menu:edit'});self.assertEqual(out['error']['code'],'NOT_ALLOWED_ROW',out['words']);act('menu.close')
            self.assertEqual(chain_menu.menu_path().exists(),menu_file,'the Graphite menu file is not written')
            self.assertIn('menu test.csv',act('read.desk',{'part':'files'})['result']['names'])
            act('menu.open',{'on':'file','name':'menu test.csv'})
            out=act('menu.choose',{'path':'more/copy:path'});self.assertTrue(out['ok'],out['words']);act('menu.close')
            self.assertEqual(self.changed(before),{});self.assertEqual(self.listing(),files_before);self.assertEqual(left,[])
            # A document: Select all may be chosen; Delete, Bold and the rest that change its words may not
            made=k.dispatch('documents.create',{'title':'Menu notes','text':'Keep these words safe.'},operator())['result']['id']
            revision=lambda:k.dispatch('documents.get',{'id':made},operator())['result']['document']
            self.assertTrue(act('go.app',{'key':'documents'})['ok'])
            self.assertTrue(act('menu.open',{'on':'here','by':'keys'})['ok'])
            self.assertTrue(act('menu.choose',{'path':'edit:all'})['ok'])
            for path in ('more/edit:delete','more/edit:cut','mark:bold'):
                self.assertTrue(act('menu.open',{'on':'here','by':'keys'})['ok'])
                out=act('menu.choose',{'path':path});self.assertIn(out['error']['code'],('NOT_ALLOWED_ROW','CHANGES_ROW_YOURS'),(path,out['words']))
                act('menu.close')
            QTest.qWait(1500);settle()      # the page's own save would have run by now
            doc=revision();self.assertEqual((doc.get('revision'),doc['blocks'][0]['text']),(1,'Keep these words safe.'))
        finally:
            for h in reversed(holds):h.stop()
            act('menu.close');k.dispatch('files.trash',{'path':'menu test.csv'},operator());act('go.files',{'view':'list'})

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
            out=act(name,args);self.assertTrue(out['ok'],(name,out['words']))
        self.assertEqual(len(journal(origin='desk-script:test'))-before,9)


if __name__=='__main__':
    unittest.main()
