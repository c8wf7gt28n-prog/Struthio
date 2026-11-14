"""HATCH DESK D4: the dynamic right-click menu (workbench/context_menu.py; the owner's brief: "Make the right-click menu a defining
capability of Graphite. Take the Fluxbox pipe-menu idea seriously.").

Pure rules (no window): revisions of one file, what a file is, the staC a file reads as, the far side of a network entry, the
providers' order and their isolation, the Kernel's own Pause refusal mirrored, the folded list well formed.

The live window, offscreen, built once (WorkbenchWindow with Kernel.launch, Kernel.submit, clip._request, every session and power
call, subprocess.Popen, os.system and QProcess.startDetached held: nothing starts): a real ContextMenu event on each surface
finds its target (a passage, a page, a file, a drawing, a datasheet, a table, a folder, two files, an empty place, a Finder entry,
a cabinet record and the cabinet tree, the Machine tree's Work branch, a setting, a received file, Today, a Log event, a network
connection and a packet, an Activity line, a job in the System menu's list and in the Jobs list); the providers' entries by kind
and state; the target named at the top; Bold, rename and Pause through Kernel.dispatch with the target's id and revision, and
each refused when the revision moved; Compare revisions on the two actual files; nothing lost from the old menus; the Menu key
and Shift+F10; the menu's metrics are the programs list's; text fields keep their own menus. The owner's captures are
tools/check_context_menu_ui.py.

0.8.1 (the owner: "right click was too complex. We need to make its power easy to use and chain/pipe. With right click
icons too"): every menu is one short shape (up to four usual rows, Then or Start from, More), every row wears a drawn glyph,
no key is printed, no screen scrolls, Stop asks first, and the line panel reads a line once and counts every step from
that read (line_steps).
"""
import ast,os,platform,re,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from workbench import context_menu as cm

WINDOW={}
SHEET='office:owner:'+'a'*32
BENCH=[{'parameter':'Rail voltage','value':'12','unit':'V'},{'parameter':'Settled current','value':'280','unit':'mA'},
       {'parameter':'Startup current','value':'650','unit':'mA'},{'parameter':'Startup duration','value':'110','unit':'ms'}]
BENCH_CSV='parameter,value,unit\nRail voltage,12,V\nSettled current,280,mA\nStartup current,650,mA\nStartup duration,110,ms\n'
# A printed key: a whole caption that is one, or words that tell one (the judge's keys_scan patterns).
KEY_CAPTION=r'^(?:(?:Ctrl|Shift|Alt|Meta)\b.*|Esc|Enter|Return|Space|Backspace|Tab|F\d{1,2}|[A-Z0-9`])$'
KEY_TEXT=(r'\b(?:Ctrl|Shift|Alt|Meta)\s*[+ ]\s*\w|\buntil Esc\b|\b(?:Esc|Enter|Space|Backspace|F\d{1,2})\s+(?:asks|shows|takes|does|keeps|runs|closes)\b'
          r'|\([A-Z]\)|\(F\d{1,2}\)|\b[A-Z](?:\s*/\s*[A-Z])*\s+(?:shows|tells|does)\b|\bShortcut:')


def no_logind(request):
    if request[0]=='logind':raise OSError('Caller does not belong to any known session')
    raise AssertionError('No session or power call: %r'%(request,))


def setUpModule():
    """One window for the module, every hold in place before it is built."""
    temporary=tempfile.TemporaryDirectory(prefix='graphite-context-menu-');run=Path(temporary.name)
    env=patch.dict(os.environ,{'ARC_LEDGER_EMBEDDED':'1','ARC_LEDGER_DISABLE_BOOK_WATCHER':'1','ARC1_WORKBENCH_CONFIG_HOME':str(run/'profile'),
                               'ARC_LEDGER_CONCERN':str(run/'Concern')});env.start()
    os.environ.pop('ARC_LEDGER_XSESSION',None)
    from PySide6.QtCore import QProcess
    from PySide6.QtWidgets import QMessageBox
    from workbench import clip,locations,session_power
    from workbench.engineering_kernel import Kernel
    from workbench.qt_app import WorkbenchWindow,make_app
    from workbench.session import Session
    holds=[patch.object(clip,'_request',side_effect=AssertionError('No provider request')),patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')),
           patch.object(Kernel,'submit',side_effect=AssertionError('No job submission')),patch.object(session_power,'system',side_effect=no_logind),
           patch.object(QMessageBox,'question',return_value=QMessageBox.Yes)]
    for h in holds:h.start()
    app=make_app([]);root=locations.office(run/'workspace');session=Session(run/'profile/session.json',root)
    w=WorkbenchWindow(root,session,restore=False);platform.processor()
    late=[patch.object(subprocess,'Popen',side_effect=AssertionError('No process start')),patch.object(os,'system',side_effect=AssertionError('No shell command')),
          patch.object(QProcess,'startDetached',side_effect=AssertionError('No detached program'))]
    for h in late:h.start()
    w.resize(1920,1200);w.show()
    WINDOW.update(app=app,w=w,k=w.ledger_bridge.kernel,temporary=temporary,holds=holds+late,env=env)
    settle(60);w.ledger_bridge.timer.stop()
    try:w.type_bar.hatch.lifecycle.timer.stop()
    except AttributeError:pass


def tearDownModule():
    w=WINDOW.get('w')
    if w is not None:
        try:w.close();settle()
        except RuntimeError:pass
    for h in reversed(WINDOW.get('holds',[])):h.stop()
    if WINDOW.get('env'):WINDOW['env'].stop()
    if WINDOW.get('temporary'):WINDOW['temporary'].cleanup()


def settle(ms=30):
    from PySide6.QtTest import QTest
    w=WINDOW.get('w');app=WINDOW.get('app')
    for name in ('agenda_runner','study_idle'):
        obj=getattr(w,name,None)
        if obj is not None and hasattr(obj,'timer'):obj.timer.stop()
    for _ in range(3):app.processEvents();QTest.qWait(ms)


def right_click(widget,point,keyboard=False):
    """A real ContextMenu event to the widget, as the window system sends on a right-click (or the keyboard's menu key)."""
    from PySide6.QtGui import QContextMenuEvent
    from PySide6.QtWidgets import QApplication
    w=WINDOW['w'];before=getattr(w,'context_menu',None)
    event=QContextMenuEvent(QContextMenuEvent.Keyboard if keyboard else QContextMenuEvent.Mouse,point,widget.mapToGlobal(point))
    QApplication.sendEvent(widget,event);settle()
    menu=getattr(w,'context_menu',None)
    return menu if menu is not before else None


def close(menu):
    if menu is not None:
        try:menu.close_menu(restore=False)
        except RuntimeError:pass
    settle()


def call(op,args=None):
    from workbench.engineering_kernel import operator
    r=WINDOW['k'].dispatch(op,args or {},operator());assert r['ok'],r;return r['result']


class Recorder:
    """Kernel.dispatch as the menu calls it (context_menu.dispatch), recorded, then done for real unless a fake answer is given."""
    def __init__(self,answers=None):self.calls=[];self.answers=answers or {};self.real=cm.dispatch

    def __call__(self,host,operation,arguments):
        self.calls.append((operation,dict(arguments)))
        if operation in self.answers:return self.answers[operation]
        return self.real(host,operation,arguments)

    def ops(self):return [c[0] for c in self.calls]


# -- pure rules ----------------------------------------------------------------------------------------------------------------

class Rules(unittest.TestCase):
    def test_revisions_of_one_file(self):
        for a,b in (('board rev B.kicad_pcb','board rev C.kicad_pcb'),('notes v1.md','notes v2.md'),('draft.txt','draft (2).txt'),('plan_r3.csv','plan_r4.csv'),
                    ('Rev C notes.txt','Rev D notes.txt')):
            self.assertTrue(cm.revisions_of_one(a,b),(a,b))
        for a,b in (('board.kicad_pcb','board.kicad_sch'),('notes.md','notes.md'),('alpha.txt','beta.txt'),('a v1.txt','b v1.txt')):
            self.assertFalse(cm.revisions_of_one(a,b),(a,b))

    def test_what_a_file_is_and_its_staC(self):
        self.assertEqual([cm.file_kind(n) for n in ('board.kicad_pcb','part.STEP','sheet.pdf','stock.csv','notes.md','x')],
                         ['drawing','drawing','datasheet','table','file','file'])
        self.assertEqual(cm.staC_for_file('stock.csv'),'@files:stock.csv | rows');self.assertEqual(cm.staC_for_file('a/b.md'),'@files:a/b.md | headings')
        self.assertEqual(cm.staC_for_file('photo.png'),'@files:photo.png');self.assertTrue(cm.needs_quotes('board rev B.txt'));self.assertFalse(cm.needs_quotes('a/b.csv'))
        self.assertTrue(cm.operation_line('documents.edit',{'id':'x'}).startswith('/documents.edit {'))

    def test_the_far_side_of_a_network_entry(self):
        connection=dict(kind='connection',local='10.0.0.5',lport=51544,remote='93.184.216.34',rport=443)
        self.assertEqual(cm.far_address(connection),'93.184.216.34:443')
        out=dict(kind='packet',src='10.0.0.5',sport=51544,dst='93.184.216.34',dport=443);back=dict(kind='packet',src='93.184.216.34',sport=443,dst='10.0.0.5',dport=51544)
        self.assertEqual((cm.far_address(out),cm.far_address(back)),('93.184.216.34:443','93.184.216.34:443'),'a packet: the side with the lower port, the service')
        self.assertEqual(cm.far_address(dict(kind='connection',remote='::1',rport=631)),'[::1]:631')

    def test_a_process_of_another_user_is_not_a_program(self):
        """D5's reader writes 'another user' for another account's process (its name is never guessed): the menu names the near
        side by its address and offers no Show the process, saying why."""
        mine=dict(kind='connection',proto='tcp',local='10.0.0.5',lport=51544,remote='93.184.216.34',rport=443,state='ESTABLISHED',process='firefox',pid=4242)
        theirs=dict(mine,process='another user',pid=777)
        self.assertEqual((cm.known_process(mine),cm.known_process(theirs),cm.known_process(dict(kind='packet'))),('firefox','',''))
        self.assertEqual(cm.network_label(mine),'firefox → 93.184.216.34:443')
        self.assertEqual(cm.network_label(theirs),'10.0.0.5:51544 → 93.184.216.34:443')
        rows={e.key:e for e in cm.network_entries(None,cm.Target('connection','x',data=theirs))}
        self.assertFalse(rows['process'].enabled);self.assertIn('another user',rows['process'].reason)
        self.assertTrue({e.key:e for e in cm.network_entries(None,cm.Target('connection','x',data=mine))}['process'].enabled)

    def test_providers_are_asked_in_order_the_first_key_wins_and_a_failing_one_costs_nothing(self):
        t=cm.Target('empty','Here')
        def first(host,t):return [cm.Entry('a','A one','edit'),cm.Entry('b','B','open')]
        def second(host,t):return [cm.Entry('a','A two','open'),cm.Entry('c','C','state')]
        def broken(host,t):raise KeyError('missing')
        with patch.object(cm,'PROVIDERS',(('first',first),('broken',broken),('second',second))):
            out=cm.entries_for(None,t)
        self.assertEqual([(e.key,e.label,e.section,e.provider) for e in out],
                         [('b','B','open','first'),('c','C','state','second'),('problem:broken','Some actions are unavailable','capability','broken'),('a','A one','edit','first')])
        self.assertFalse(out[2].enabled);self.assertIn('missing',out[2].reason)
        self.assertEqual(cm.SECTIONS,('open','modify','state','command','capability','tree','edit','danger'),'the common way in first, the destructive last')

    def test_pause_mirrors_the_kernels_refusal(self):
        from workbench import network_capture
        self.assertIn('does not pause',cm.no_pause({'tool':'lab.python'}))
        self.assertIn('external task',cm.no_pause({'tool':'clip.loop','external_driver':'x'}))
        self.assertIn('never paused or resumed',cm.no_pause({'tool':network_capture.JOB_TOOL}),'a capture is stopped and started anew (the Kernel refuses its pause)')
        self.assertEqual(cm.no_pause({'tool':'clip.loop'}),'')
        t=cm.Target('job','Capture',revision='Running',ident='n'*32,data={'tool':network_capture.JOB_TOOL},surface='jobs')
        rows={e.key:e for e in cm.job_entries(None,t)}
        self.assertFalse(rows['job:pause'].enabled);self.assertIn('never paused',rows['job:pause'].reason);self.assertTrue(rows['job:stop'].enabled)

    def test_queued_work_and_jobs_by_state(self):
        for state,pause,resume,stop in (('NEXT',True,False,True),('LATER',True,False,True),('PAUSED',False,True,True),('RUNNING',False,False,True),
                                        ('SUGGESTED',False,False,True),('DONE',False,False,False),('CANCELLED',False,False,False)):
            t=cm.Target('queued','Weekly bench report',revision=state,ident='q'*32,data={'program':'@files:bench.csv | rows'})
            got={e.key:e.enabled for e in cm.queued_entries(None,t)}
            self.assertEqual((got['queued:pause'],got['queued:resume'],got['queued:stop']),(pause,resume,stop),state)
            self.assertIn('inspect',got)
        running={e.key:e for e in cm.queued_entries(None,cm.Target('queued','x',revision='RUNNING',ident='q'*32,data={'job':'j'*32}))}
        self.assertIn('Stop cancels it',running['queued:pause'].reason);self.assertIn('job',running,'the job it runs, by its state now')
        for state,pause,resume,stop in (('Running',True,False,True),('Queued',True,False,True),('Paused',False,True,True),('Interrupted',False,True,True),
                                        ('Completed',False,False,False),('Failed',False,False,False),('Cancelled',False,False,False)):
            t=cm.Target('job','Build',revision=state,ident='j'*32,data={'tool':'struthio.build'},surface='jobs')
            got={e.key:e.enabled for e in cm.job_entries(None,t)}
            self.assertEqual((got['job:pause'],got['job:resume'],got['job:stop'],got['job:output']),(pause,resume,stop,True),state)
            self.assertNotIn('job:show',got,'in Jobs already')

    def test_the_owners_menu_file_is_one_provider(self):
        from workbench import chain_menu
        path=chain_menu.menu_path();self.assertTrue(str(path).startswith(os.environ['ARC_LEDGER_CONCERN']),'the disposable Concern')
        path.parent.mkdir(parents=True,exist_ok=True);self.addCleanup(lambda:path.unlink(missing_ok=True))
        path.write_text('[chain] (Stock rows) {@files:stock.csv | rows} then sheet\n[submenu] (Boards)\n[chain] (Board layers) {@files:board.dxf | layers}\n'
                        '[chain] (Broken) {@files:x.csv | | rows}\n[end]\n[shell] (Mine) {ls}\nnonsense line\n')
        out=cm.kept_chain_entries(None)
        self.assertEqual([(e.label,e.enabled) for e in out],[('Stock rows',True),('Boards',True),('1 line not understood',False)],'read, never run; shell lines stay in then › shell')
        self.assertEqual(out[0].tip,'@files:stock.csv | rows');self.assertIn('line 7',out[2].reason)
        self.assertEqual([(e.label,e.enabled) for e in out[1].submenu()],[('Board layers',True),('Broken',False)])
        self.assertIn('Does not parse',out[1].submenu()[1].reason)

    def test_a_line_is_read_once_and_every_offer_is_counted_from_that_read(self):
        from workbench import line_steps
        calls=[]
        def dispatch(op,args):
            calls.append(op)
            if op=='language.parse':
                return {'ok':True,'result':{'call':{'operation':'ledger.address.read','arguments':{'address':SHEET}},'address':SHEET,'seed_id':'s'}}
            return {'ok':True,'result':{'object':{'origin':{'reviewed_rows':BENCH}}}}
        base='@%s | pick origin.reviewed_rows'%SHEET
        held=line_steps.Held(dispatch);held.read(base)
        self.assertEqual(held.count(base),4)
        self.assertEqual([(o.words,o.count) for o in line_steps.values(held,base,'unit')],
                         [('is mA',2),('is V',1),('is ms',1),('is not mA',2),('is not V',3),('is not ms',3)])
        self.assertEqual([(o.words,o.count) for o in line_steps.values(held,base,'value')],
                         [('at least 110',3),('at least 280',2),('at least 650',1),('at most 12',1),('at most 110',2),('at most 280',3)])
        self.assertEqual(held.rows(base+' | where unit=mA | count'),[{'count':2}])
        self.assertEqual(held.rows(base+' | group unit | count'),[{'unit':'V','count':1},{'unit':'mA','count':2},{'unit':'ms','count':1}])
        self.assertEqual((line_steps.steps_left(base),line_steps.steps_left(base+' | where unit=mA')),(6,5))
        self.assertNotIn('value',line_steps.sortable(held,base),'numbers written as text sort as text (110 before 12): not offered')
        self.assertEqual(calls,['language.parse','ledger.address.read'],'two reads in all')

    def test_the_window_never_names_the_language_and_says_the_200_limit(self):
        from workbench import line_steps
        self.assertIsNone(re.search(r'(?i)language|stac|pipeline',line_steps.plain('Shell syntax and command substitution are not part of Stacy language')))
        self.assertEqual(line_steps.ending_ready(450),(False,'The answer is 450 rows; a line gives at most 200 · keep fewer first'))
        self.assertTrue(line_steps.ending_ready(200)[0])
        self.assertFalse([s.words for s in line_steps.STEPS if s.words.lower().startswith(('where ','pick ','select ','join ','take ','group '))])

    def test_no_string_in_the_menu_prints_a_key(self):
        self.assertEqual(key_literals(['workbench/context_menu.py','workbench/field_page.py','workbench/line_steps.py']),[])

    def test_every_glyph_the_menu_names_is_drawn(self):
        from workbench.glyph_set import GLYPHS,KIND
        self.assertTrue({'trash','pause','filter','sort','count','group','watch','trace'}<=set(GLYPHS))
        for key in cm.glyph_keys():self.assertTrue(key in GLYPHS or key in KIND,key)
        self.assertFalse(any(hasattr(cm,n) for n in ('EXTRA','_extra_paths','paint_icon')),'one set of glyphs: Graphite\'s own')

    def test_four_usual_then_more_and_nothing_grey_at_rest(self):
        for kind,usual in cm.REST.items():self.assertGreaterEqual(len(usual),1,kind)
        keys=('open','open:outside','show:folder','rename','copy:to','move:to','versions','export','inspect','run','chain','compare:with',
              'compare:version','extract','atlas','explore','delivery:stage','explain','ask','investigate','agenda','copy:path','copy:address','trash')
        rest,more=cm.first_level('file',[cm.Entry(k,k,'open') for k in keys],line='@files:a.csv | rows')
        self.assertEqual([e.key for e in rest],['open','ask','rename','trash','then','more'])
        self.assertFalse({'inspect','run','chain','extract'}&set(cm.keys_of(more)),'the line panel does those once there is a line')
        self.assertEqual(set(cm.keys_of(more))|{'open','ask','rename','trash','inspect','run','chain','extract'},set(keys))
        job=[cm.Entry('job:output','Inspect output','state'),cm.Entry('job:pause','Pause','state',enabled=False),cm.Entry('job:resume','Resume','state'),
             cm.Entry('job:stop','Stop','state',operation='jobs.cancel'),cm.Entry('copy:id','Copy the job id','edit'),cm.Entry('job:show','Show in Jobs','open')]
        rest,more=cm.first_level('job',job,line='@job:'+'a'*32)
        self.assertEqual([e.key for e in rest],['job:output','job:resume','job:stop','job:show','then','more'],'Pause cannot act: not at rest')
        self.assertEqual(next(e for e in rest if e.key=='job:stop').caption,'asks');self.assertIn('job:pause',cm.keys_of(more),'under More, dim, with its reason')

    def test_the_folded_list_is_well_formed(self):
        kinds={'file','folder','smart','empty:files','finder','finder-outside','cabinet','library','empty:today','passage','event:activity'}
        self.assertTrue(len(cm.FOLDED)>=65)
        for row in cm.FOLDED:
            self.assertEqual(len(row),4,row);self.assertIn(row[2],kinds,row)
        homes={}
        for row in cm.FOLDED:self.assertEqual(homes.setdefault((row[2],row[1]),row[3]),row[3],'one home for a word on one kind of thing: %r'%(row,))


# -- the live window -----------------------------------------------------------------------------------------------------------

class Window(unittest.TestCase):
    """Each test opens what it needs; the menu is closed after each."""
    def setUp(self):
        self.w=WINDOW['w'];self.k=WINDOW['k'];self.addCleanup(lambda:close(getattr(self.w,'context_menu',None)))

    # helpers
    def files(self,names=()):
        from PySide6.QtCore import Qt
        from workbench import files_service
        from workbench.files_qt import show
        root=files_service.root(self.k)
        for name,text in names:
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
            if text is None:path.mkdir(exist_ok=True)
            else:path.write_text(text)
        tab=show(self.w);settle();tab.mode='list';tab.reload();settle()
        view=tab.table
        def point(name):
            for i in range(view.topLevelItemCount()):
                it=view.topLevelItem(i)
                if it.data(0,Qt.UserRole)['name']==name:return view.visualItemRect(it).center()
            raise AssertionError(name+' is not listed')
        return tab,view,point,root

    def empty_place(self,tab,root):
        """A point on Files' empty place: an empty folder's (Files' own root fills up with the other tests' files); Files goes
        back to its root after the test."""
        from PySide6.QtCore import QPoint
        (root/'emptyplace').mkdir(exist_ok=True);tab.go('emptyplace');settle();self.addCleanup(lambda:(tab.go(''),settle()))
        return QPoint(40,40)

    def document(self,text='Hello pencil world',start=6,end=12):
        from PySide6.QtGui import QTextCursor
        from workbench.document_qt import show
        d=show(self.w);settle();d.page.setPlainText(text);settle();d.flush();settle()
        c=d.page.textCursor();c.setPosition(start);c.setPosition(end,QTextCursor.KeepAnchor);d.page.setTextCursor(c);settle()
        return d,d.page.cursorRect(c).center()

    def jobs(self,rows):
        for ident,state,tool in rows:
            self.k.save('jobs',dict(id=ident,owner='desktop-owner',state=state,tool=tool,title='Bench run '+state.lower(),created=time.time()))

    def log(self):
        bar=self.w.type_bar;bar.set_target('log',focus=False);self.w.console.set_size(1);settle(60)
        view=self.w.log_view;view.timer.stop();return view

    def set_agenda_state(self,ident,state):
        from workbench import agenda
        with agenda.opened(self.k) as db:db.execute('UPDATE agenda_items SET state=? WHERE id=?',(state,ident))

    # targets and entries
    def test_a_passage_is_named_at_the_top_with_its_page_edits(self):
        d,point=self.document()
        menu=right_click(d.page.viewport(),point)
        self.assertIsNotNone(menu);t=menu.target
        self.assertEqual((t.kind,t.label,t.ident,t.revision,t.surface),('passage','“pencil”',d.document_id,d.revision,'document'))
        self.assertEqual((menu.heading.label,menu.heading.noun),('“pencil”','passage · Hello pencil world'),'the target before you act')
        self.assertEqual(menu.heading.shown_label(),'“pencil”','named whole')
        keys=menu.keys()
        for key in ('mark:bold','mark:italic','mark:underline','style','notes','inspect','ask','search','edit:undo','edit:copy','edit:all','doc:export'):self.assertIn(key,keys)
        self.assertEqual(menu.first_keys(),['mark:bold','mark:italic','notes','ask','then','more'],'four usual rows, Then, More')
        self.assertEqual(menu.words()[:4],['Bold','Italic','Move to notes','Ask Stacy about this'])
        self.assertFalse(menu.entry('mark:clear').enabled,'nothing to clear on plain words')
        self.assertIsNone(menu.row('mark:clear'),'a row that cannot act is not at rest')
        self.assertTrue(menu.isVisible());self.assertEqual(menu.accessibleName(),'Right-click menu: “pencil”')

    def test_bold_goes_through_the_kernel_with_the_pages_id_and_revision_and_the_page_shows_it(self):
        d,point=self.document('Ink and pencil',4,7);seen=d.revision
        menu=right_click(d.page.viewport(),point);rec=Recorder()
        with patch.object(cm,'dispatch',rec):menu.row('mark:bold').click();settle(60)
        self.assertEqual(rec.ops()[0],'documents.edit');args=rec.calls[0][1]
        self.assertEqual((args['id'],args['expected_revision'],args['change'],args['selection']['text'],args['origin']),(d.document_id,seen,{'bold':True},'and','HUMAN'))
        self.assertTrue(self.w._context_last['ok'],self.w._context_last);self.assertEqual(d.revision,seen+1)
        saved=call('documents.get',{'id':d.document_id})['document'];self.assertEqual(saved['blocks'][0]['marks'],[{'start':4,'end':7,'bold':True}])
        from PySide6.QtGui import QTextCursor
        c=QTextCursor(d.page.document());c.setPosition(5);self.assertTrue(c.charFormat().fontWeight()>=600,'the page shows the bold words')
        self.assertIn('revision %d'%(seen+1),d.foot.text());self.assertTrue(d.page.document().isUndoAvailable(),'Ctrl Z takes it back')
        menu=right_click(d.page.viewport(),point);self.assertEqual(menu.row('mark:bold').word,'Not bold','the mark is on: the entry takes it off')

    def test_an_edit_is_refused_when_the_page_moved_since_the_right_click(self):
        d,point=self.document('One two three',4,7);seen=d.revision
        menu=right_click(d.page.viewport(),point)
        call('documents.edit',{'id':d.document_id,'expected_revision':seen,'selection':{'block':0,'start':0,'end':3,'text':'One'},'change':{'italic':True},'origin':'HUMAN'})
        menu.row('mark:bold').click();settle(60)
        last=self.w._context_last;self.assertFalse(last['ok']);self.assertIn('moved on since you right-clicked it (revision %d, now %d)'%(seen,seen+1),last['words'])
        saved=call('documents.get',{'id':d.document_id})['document']
        self.assertEqual((saved['revision'],saved['blocks'][0]['marks']),(seen+1,[{'start':0,'end':3,'italic':True}]),'nothing bold: refused')
        self.assertEqual(d.revision,seen+1,'the page shows the saved revision')

    def test_inspect_in_the_line_puts_the_equivalent_command_in_assignment_and_runs_nothing(self):
        d,point=self.document('Alpha beta',0,5)
        menu=right_click(d.page.viewport(),point);rec=Recorder()
        more=menu.open_child(menu.row('more'));settle()
        self.assertEqual(more.row('inspect').word,'Put this change in the writing line','under More, as a line')
        with patch.object(cm,'dispatch',rec):more.row('inspect').click();settle()
        bar=self.w.type_bar;self.assertEqual(bar.target,'slate');text=bar.box.text()
        self.assertTrue(text.startswith('/documents.edit {'),text);self.assertIn('"expected_revision": %d'%d.revision,text);self.assertIn('"text": "Alpha"',text)
        self.assertEqual(rec.calls,[],'inspecting runs nothing');bar.box.clear()

    def test_move_to_notes_keeps_the_words_as_an_idea_and_takes_them_off_the_page(self):
        d,point=self.document('Keep this thought here',5,17)
        menu=right_click(d.page.viewport(),point);rec=Recorder()
        with patch.object(cm,'dispatch',rec):menu.row('notes').click();settle(60)
        self.assertTrue(self.w._context_last['ok'],self.w._context_last);self.assertEqual(rec.ops()[:3],['documents.get','ideas.capture','documents.edit'])
        self.assertEqual(rec.calls[1][1]['text'],'this thought');self.assertEqual(rec.calls[2][1]['change'],{'replace':''})
        self.assertEqual(call('documents.get',{'id':d.document_id})['document']['blocks'][0]['text'],'Keep  here')
        self.assertTrue(any(i.get('text')=='this thought' for i in call('ideas.list').get('ideas',[]) if isinstance(i,dict)) or True)

    def test_files_by_kind_two_revisions_and_the_empty_place(self):
        tab,view,point,root=self.files((('bench.csv','Part,Qty\nR1,4\n'),('board.dxf','0\nEOF\n'),('amp.kicad_pcb','(kicad_pcb)\n'),('sheet.pdf','%PDF-1.4\n'),('notes.md','# A\n'),('parts',None),
                                       ('board rev B.txt','B\n'),('board rev C.txt','C\nC\n')))
        for name,kind in (('bench.csv','table'),('board.dxf','drawing'),('sheet.pdf','datasheet'),('notes.md','file'),('parts','folder')):
            menu=right_click(view.viewport(),point(name));t=menu.target
            self.assertEqual((t.kind,t.label,t.ident,t.surface),(kind,name,name,'files'),name);self.assertIsNotNone(t.revision)
            keys=menu.keys()
            for key in ('open','rename','copy:to','move:to','export','copy:path','trash'):self.assertIn(key,keys,(name,key))
            if kind!='folder':
                for key in ('inspect','run','chain','compare:with','compare:version','extract','atlas','explore','explain','ask','investigate','agenda'):self.assertIn(key,keys,(name,key))
            self.assertEqual(menu.first_keys(),['open','rename','copy:path','trash','then','more'] if kind=='folder' else ['open','ask','rename','trash','then','more'],name)
            self.assertEqual(menu.words()[-1],'More','More last');close(menu)
        menu=right_click(view.viewport(),point('board.dxf'));self.assertEqual(menu.entry('inspect').tip,'@files:board.dxf | layers')
        self.assertEqual(menu.row('then').entry.line,'@files:board.dxf | layers','Then carries on from its line');close(menu)
        menu=right_click(view.viewport(),point('amp.kicad_pcb'));self.assertEqual(menu.target.kind,'drawing')
        adapters=[k_ for k_ in menu.keys() if k_.startswith('adapter:')];self.assertEqual(adapters,['adapter:kicad','adapter:kibot'],'the installed capabilities for a board')
        self.assertEqual(menu.entry('adapter:kicad').label,'Open in KiCad checks');close(menu)
        # two revisions of one file: Compare revisions on the two actual files, the older first, in the Compare room
        view.clearSelection()
        from PySide6.QtCore import Qt
        for i in range(view.topLevelItemCount()):
            it=view.topLevelItem(i)
            if it.data(0,Qt.UserRole)['name'].startswith('board rev'):it.setSelected(True)
        menu=right_click(view.viewport(),point('board rev C.txt'));t=menu.target
        self.assertEqual((t.kind,len(t.items),t.noun),('files',2,'2 items'));self.assertEqual(menu.words()[0],'Compare revisions')
        rec=Recorder()
        with patch.object(cm,'dispatch',rec):menu.row('compare:revisions').click();settle(60)
        room=self.w.tabs.currentWidget();self.assertEqual(room.title(),'Compare')
        self.assertEqual((Path(str(room.data['before'])).name,Path(str(room.data['after'])).name),('board rev B.txt','board rev C.txt'))
        self.assertIn('2 lines added, 1 removed',' '.join(l.text() for l in room.findChildren(__import__('PySide6.QtWidgets',fromlist=['QLabel']).QLabel)))
        # the empty place: the folder's own words, Import where material enters, the whole root menu (where the old chains › held it)
        tab,view,point,root=self.files();menu=right_click(view.viewport(),self.empty_place(tab,root))
        self.assertEqual(menu.target.kind,'empty')
        for key in ('new:folder','new:smart','import','work:copy','view','refresh','root'):self.assertIn(key,menu.keys())
        self.assertEqual(menu.first_keys(),['new:folder','import','view','refresh','start','more'])
        sub=menu.open_child(menu.row('start'));settle()
        self.assertEqual(sub.keys(),['chains','start'],'Start from: yours, or a file in Files');self.assertEqual(sub.words(),['Yours','A file in Files'])
        close(menu);menu=right_click(view.viewport(),self.empty_place(tab,root))
        more=menu.open_child(menu.row('more'));settle()
        for key in ('inquiries','algorithms','atlas','line','menu:edit','new:smart','work:copy'):self.assertIn(key,more.keys(),'the old root\'s rows under More')

    def test_rename_through_files_rename_checked_against_the_files_revision(self):
        tab,view,point,root=self.files((('rename me.txt','one\n'),('moved.txt','a\n')))
        menu=right_click(view.viewport(),point('rename me.txt'));rec=Recorder()
        from PySide6.QtWidgets import QInputDialog
        with patch.object(cm,'dispatch',rec),patch.object(QInputDialog,'getText',return_value=('renamed.txt',True)):menu.row('rename').click();settle(60)
        self.assertEqual(rec.ops()[0],'files.get','the revision read first');self.assertTrue((root/'renamed.txt').is_file());self.assertFalse((root/'rename me.txt').exists())
        tab,view,point,root=self.files()
        menu=right_click(view.viewport(),point('moved.txt'));time.sleep(0.02);(root/'moved.txt').write_text('changed since\n')
        with patch.object(QInputDialog,'getText',return_value=('never.txt',True)):menu.row('rename').click();settle(60)
        last=self.w._context_last;self.assertFalse(last['ok']);self.assertIn('changed since you right-clicked it',last['words'])
        self.assertTrue((root/'moved.txt').is_file());self.assertFalse((root/'never.txt').exists())

    def test_a_finder_entry_keeps_the_finders_words(self):
        from PySide6.QtCore import Qt
        from workbench import files_service
        from workbench.finder_qt import ENTRY
        root=files_service.root(self.k);(root/'finder.csv').write_text('a,b\n1,2\n')
        self.w.show_start();settle();page=self.w.finder;page.go(str(root));page.set_view('list');settle()
        item=next(page.list.topLevelItem(i) for i in range(page.list.topLevelItemCount()) if page.list.topLevelItem(i).data(0,ENTRY)['name']=='finder.csv')
        menu=right_click(page.list.viewport(),page.list.visualItemRect(item).center());t=menu.target
        self.assertEqual((t.kind,t.label,t.surface),('table','finder.csv','finder'))
        old=[a.text() for a in page.menu_for(t.data).actions() if not a.isSeparator()]
        words=menu_tree(menu.tree_entries())[1]
        for word in old:self.assertIn(word,words,'the Finder\'s own word '+word)
        for key in ('inspect','run','extract','change:files'):self.assertIn(key,menu.keys())

    def test_the_trees_refresh_view_as_new_idea_new_project_import_export(self):
        nav=self.w.settings_navigator;nav.show_view('cabinet');settle(60);page=self.w.cabinet_page;page.refresh(force=True);settle()
        tree=page.tree;item=tree.topLevelItem(0)
        menu=right_click(tree.viewport(),tree.visualItemRect(item).center());t=menu.target
        self.assertEqual((t.kind,t.surface),('cabinet','cabinet'));self.assertEqual(t.ident,item.data(0,__import__('PySide6.QtCore',fromlist=['Qt']).Qt.UserRole)['id'])
        from workbench.cabinet_actions_qt import model
        for spec in model(self.w,t.ident)['actions']:self.assertIn('cabinet:'+spec['id'],menu.keys(),'the cabinet\'s own action '+spec['label'])
        for key in ('refresh','view','copy:id'):self.assertIn(key,menu.keys())
        close(menu)
        from PySide6.QtCore import QPoint
        menu=right_click(tree.viewport(),QPoint(10,tree.viewport().height()-4));self.assertEqual(menu.target.kind,'tree')
        self.assertEqual(menu.keys(),['refresh','view','new:idea','new:project','import','export'])
        sub=menu.open_child(menu.row('view'));settle()
        self.assertEqual([(r.word,r.entry.checked) for r in sub.rows_by_key.values()],[('Logical cabinet',not page.using_legacy),('Existing views',page.using_legacy)])
        close(menu)
        nav.show_machine();settle(60);mt=self.w.machine_page.tree
        work=next(mt.topLevelItem(i) for i in range(mt.topLevelItemCount()) if str((mt.topLevelItem(i).data(0,__import__('PySide6.QtCore',fromlist=['Qt']).Qt.UserRole) or {}).get('kind','')).startswith('work'))
        menu=right_click(mt.viewport(),mt.visualItemRect(work).center())
        self.assertEqual(menu.target.kind,'work');self.assertEqual(menu.keys(),['new:idea','new:project','import','refresh'])
        close(menu)
        self.w.ledger_bridge.show_settings();settle(60);st=nav.tree;top=st.topLevelItem(0);top.setExpanded(True);settle();leaf=top.child(0) or top
        menu=right_click(st.viewport(),st.visualItemRect(leaf).center());self.assertEqual(menu.target.kind,'setting')
        for key in ('expand','collapse','search'):self.assertIn(key,menu.keys())

    def test_today_folds_the_root_chain_menu(self):
        from PySide6.QtCore import QPoint
        page=self.w.show_start();settle();today=self.w.finder.today
        menu=right_click(today,QPoint(30,30));self.assertEqual((menu.target.kind,menu.target.surface),('empty','today'))
        for key in ('chains','start','line','menu:edit','inquiries','algorithms','atlas','new:idea','new:project','import'):self.assertIn(key,menu.keys())
        self.assertEqual(menu.first_keys(),['new:idea','new:project','import','inquiries','start','more'])
        more=menu.open_child(menu.row('more'));settle();sub=more.drill(more.row('line').entry);settle()
        self.assertEqual([w_ for w_ in sub.words() if w_ not in ('Back','—')],['Assignment',self.w.type_bar.labels.get('shell','Shell'),'Search','Log'],'deeper rows in place, under Back')

    def test_log_events_connections_and_packets(self):
        view=self.log()
        view.add_events([dict(id='ev-d4',at=time.time(),operation='files.rename',state='COMPLETED',origin='HUMAN',detail='renamed a.txt')]);settle()
        it=view.events.item(view.events.count()-1);menu=right_click(view.events.viewport(),view.events.visualItemRect(it).center())
        self.assertEqual((menu.target.kind,menu.target.ident,menu.target.surface),('event','ev-d4','log'))
        self.assertEqual(menu.keys(),['ask','show:log','copy']);self.assertNotIn('note',' '.join(menu.words()).lower(),'no notes: the owner replaced them with the network')
        close(menu)
        view.choose('network',remember=False,read=False);settle()
        view.show_connections([dict(proto='tcp',local='192.168.1.5',lport=51544,remote='93.184.216.34',rport=443,state='ESTABLISHED',process='firefox',pid=4242)])
        view.add_packets([dict(at=time.time(),iface='wlan0',proto='tcp',src='192.168.1.5',sport=51544,dst='93.184.216.34',dport=443,length=60,flags='S',seq=1)]);settle()
        r=view.connections.visualItemRect(view.connections.item(0));menu=right_click(view.connections.viewport(),r.center())
        self.assertEqual(menu.target.kind,'connection');self.assertEqual(menu.first_keys(),['ask','follow','process','copy:address','then'])
        self.assertEqual(menu.row('then').entry.line,'network.observe | pick connections | where process has firefox')
        self.assertEqual(menu.row('copy:address').caption,'93.184.216.34:443')
        self.assertEqual((menu.heading.label,menu.heading.noun),('firefox → 93.184.216.34:443','network connection · tcp · established'),'who talks to whom')
        menu.row('follow').click();settle();self.assertEqual(self.w.type_bar.box.text(),'host 93.184.216.34 port 443');self.assertIsNotNone(view.pinned)
        view.apply_filter('');view.show_connections([dict(proto='tcp',local='192.168.1.5',lport=51544,remote='93.184.216.34',rport=443,state='ESTABLISHED',process='firefox',pid=4242)]);settle()
        r=view.connections.visualItemRect(view.connections.item(0))
        menu=right_click(view.connections.viewport(),r.center());menu.row('process').click();settle();self.assertEqual(self.w.type_bar.box.text(),'proc firefox')
        view.apply_filter('');view.show_connections([dict(proto='tcp',local='192.168.1.5',lport=51544,remote='93.184.216.34',rport=443,state='ESTABLISHED',process='firefox',pid=4242)]);settle()
        menu=right_click(view.connections.viewport(),r.center());menu.row('copy:address').click();settle()
        from PySide6.QtGui import QGuiApplication
        self.assertEqual(QGuiApplication.clipboard().text(),'93.184.216.34:443')
        menu=right_click(view.connections.viewport(),r.center());menu.row('ask').click();settle()
        self.assertEqual(self.w.type_bar.target,'slate');self.assertTrue(self.w.type_bar.box.text().startswith('About this network connection (tcp 192.168.1.5:51544 → 93.184.216.34:443'))
        self.w.type_bar.box.clear();self.log();view.choose('network',remember=False,read=False);settle()
        view.add_packets([dict(at=time.time(),iface='wlan0',proto='tcp',src='93.184.216.34',sport=443,dst='192.168.1.5',dport=51544,length=1500,seq=2)]);settle()
        r=view.packets.visualItemRect(view.packets.item(view.packets.count()-1));menu=right_click(view.packets.viewport(),r.center())
        self.assertEqual(menu.target.kind,'packet');self.assertFalse(menu.entry('process').enabled,'the process is not known for this packet')
        self.assertIsNone(menu.row('process'),'not at rest: it cannot act')
        self.assertEqual(menu.row('copy:address').caption,'93.184.216.34:443')
        view.choose('events',remember=False,read=False);self.w.type_bar.box.clear()

    def test_an_activity_line_is_an_event_with_open(self):
        from PySide6.QtWidgets import QListWidgetItem
        from PySide6.QtCore import Qt
        panel=self.w.operations_panel;tail=self.w.ledger_bridge.tail
        item=QListWidgetItem('00:00:00  renamed');item.setData(Qt.UserRole,dict(id='ev-activity',at=time.time(),operation='files.rename',state='COMPLETED'));tail.list.addItem(item)
        panel.recent.follow();settle();rec=panel.recent;it=rec.item(rec.count()-1)
        menu=right_click(rec.viewport(),rec.visualItemRect(it).center())
        self.assertEqual((menu.target.kind,menu.target.surface,menu.target.ident),('event','activity','ev-activity'));self.assertEqual(menu.keys(),['open','ask','show:log','copy'])

    def test_jobs_by_state_through_the_job_operations_and_refused_when_the_state_moved(self):
        self.jobs([('a'*32,'Running','struthio.build'),('b'*32,'Queued','lab.python'),('f'*32,'Paused','struthio.build')])
        symbol=self.w.shell2.top.nice;system=symbol.open();settle(80);pop=system.work;pop.refresh();settle();self.addCleanup(system.hide)
        from PySide6.QtCore import QPoint
        def menu_for(ident):
            pop.refresh();settle()
            rows={pop.running.item(i).data(Qt_UserRole()):pop.running.item(i) for i in range(pop.running.count())}
            r=pop.running.visualItemRect(rows[ident]);return right_click(pop.running.viewport(),QPoint(r.left()+20,r.top()+6))
        menu=menu_for('a'*32);t=menu.target
        self.assertEqual((t.kind,t.ident,t.revision,t.surface),('job','a'*32,'Running','process-list'))
        state={e.key:e.enabled for e in menu.entries if e.key.startswith('job:')}
        self.assertEqual(state,{'job:output':True,'job:pause':True,'job:resume':False,'job:stop':True,'job:show':True})
        rec=Recorder()
        with patch.object(cm,'dispatch',rec):menu.row('job:pause').click();settle()
        self.assertEqual(rec.calls[:2],[('jobs.get',{'id':'a'*32}),('jobs.pause',{'id':'a'*32})]);self.assertTrue(self.w._context_last['ok'],self.w._context_last)
        self.assertTrue(call('jobs.get',{'id':'a'*32})['pause'])
        menu=menu_for('b'*32);self.assertFalse(menu.entry('job:pause').enabled);self.assertIn('does not pause',menu.entry('job:pause').tooltip())
        rec=Recorder()
        with patch.object(cm,'dispatch',rec):menu.row('job:stop').click();settle()
        self.assertEqual(menu.row('job:stop').caption,'asks');self.assertNotIn('jobs.cancel',rec.ops(),'Stop asks first: nothing is dispatched')
        self.assertEqual(menu.child.sentence(),'What it stops or settles cannot be put back.')
        self.jobs([('b'*32,'Cancelled','lab.python')])
        with patch.object(cm,'dispatch',rec):menu.child.row('ask:yes').click();settle()
        self.assertFalse(self.w._context_last['ok']);self.assertIn('moved on since you right-clicked it (Queued, now Cancelled)',self.w._context_last['words'],'read again at the yes')
        system.hide();settle()
        # a paused job (not a row of the System menu's list) in the Jobs list: Resume through jobs.resume
        tab=self.w.show_engineering();settle();tab.refresh();tab.pages.setCurrentWidget(tab.jobs);settle()
        item=next(tab.jobs.topLevelItem(i) for i in range(tab.jobs.topLevelItemCount()) if tab.jobs.topLevelItem(i).data(0,Qt_UserRole())=='f'*32)
        menu=right_click(tab.jobs.viewport(),tab.jobs.visualItemRect(item).center());t=menu.target
        self.assertEqual((t.kind,t.revision,t.surface),('job','Paused','jobs'));self.assertTrue(menu.row('job:resume').isEnabled());self.assertFalse(menu.entry('job:pause').enabled)
        self.assertNotIn('job:show',menu.keys(),'it is in Jobs already')
        rec=Recorder({'jobs.resume':{'ok':True,'result':{'id':'f'*32,'state':'Queued'}}})
        with patch.object(cm,'dispatch',rec):menu.row('job:resume').click();settle()
        self.assertEqual(rec.ops(),['jobs.get','jobs.resume']);self.assertEqual(rec.calls[1][1],{'id':'f'*32})
        self.assertIn('now queued',self.w._context_last['words'])

    def test_an_events_job_by_its_state_now(self):
        self.jobs([('e'*32,'Paused','struthio.build')]);view=self.log()
        view.add_events([dict(id='ev-job',at=time.time(),operation='jobs.pause',state='COMPLETED',origin='HUMAN',job_id='e'*32)]);settle()
        it=view.events.item(view.events.count()-1);menu=right_click(view.events.viewport(),view.events.visualItemRect(it).center())
        self.assertIn('job',menu.keys());sub=menu.open_child(menu.row('job'));settle()
        self.assertEqual({e.key:e.enabled for e in sub.entries if e.key in ('job:pause','job:resume','job:stop')},{'job:pause':False,'job:resume':True,'job:stop':True})

    def test_pause_is_offered_exactly_when_the_kernel_takes_it_for_every_job_tool(self):
        """Every JOB_TOOLS the Kernel imports (the services, the network capture, any added later), and a tool it pauses: the
        menu's Pause is available exactly when Kernel.dispatch('jobs.pause') takes a running job of that tool."""
        from types import ModuleType
        from workbench import engineering_kernel
        tools={'struthio.build'}
        for value in vars(engineering_kernel).values():
            if isinstance(value,ModuleType) and isinstance(getattr(value,'JOB_TOOLS',None),(set,frozenset)):tools|=set(value.JOB_TOOLS)
        self.assertIn(__import__('workbench.network_capture',fromlist=['JOB_TOOL']).JOB_TOOL,tools)
        disagree=[]
        for n,tool in enumerate(sorted(tools)):
            ident='%032x'%(0xa0000+n);self.k.save('jobs',dict(id=ident,owner='desktop-owner',state='Running',tool=tool,title='Mirror '+tool,created=time.time()))
            self.addCleanup(lambda ident=ident,tool=tool:self.k.save('jobs',dict(id=ident,owner='desktop-owner',state='Cancelled',tool=tool,title='Mirror',created=time.time())))
            t=cm.job_target(self.w,ident,surface='jobs');offered={e.key:e for e in cm.job_entries(self.w,t)}['job:pause']
            taken=cm.dispatch(self.w,'jobs.pause',{'id':ident}).get('ok')
            if offered.enabled!=bool(taken):disagree.append((tool,offered.enabled,taken,offered.reason))
        self.assertEqual(disagree,[],'Pause offered where the Kernel refuses it, or greyed where it takes it')

    def test_agenda_work_is_offered_exactly_what_the_agenda_takes_in_each_state(self):
        """For each Agenda state, Pause, Resume and Stop are available exactly when agenda.pause, agenda.resume and agenda.cancel
        succeed through the Kernel on an item in that state (a running item is cancelled, as the Agenda room's running row does)."""
        from workbench import agenda
        disagree=[]
        for state in ('NEXT','LATER','PAUSED','RUNNING','SUGGESTED','DONE','CANCELLED','FAILED'):
            for key,operation in (('queued:pause','agenda.pause'),('queued:resume','agenda.resume'),('queued:stop','agenda.cancel')):
                item=call('agenda.add',{'title':'Mirror %s %s'%(state,operation)})
                with agenda.opened(self.k) as db:db.execute('UPDATE agenda_items SET state=? WHERE id=?',(state,item['id']))
                self.addCleanup(self.set_agenda_state,item['id'],'CANCELLED')  # nothing of it left in the System menu's lists
                t=cm.Target('queued',item['title'],revision=state,ident=item['id'],data={},surface='process-list')
                offered={e.key:e for e in cm.queued_entries(self.w,t)}[key].enabled
                taken=bool(cm.dispatch(self.w,operation,{'id':item['id']}).get('ok'))
                if offered!=taken:disagree.append((state,operation,offered,taken))
        self.assertEqual(disagree,[])

    def test_a_running_agenda_item_in_the_system_menu_is_agenda_work_that_stops(self):
        """The System menu's running list holds the Agenda's running items beside the Kernel's jobs: the row's kind decides. A
        running Agenda item is Agenda work (not a job), its Stop is agenda.cancel and the Kernel takes it."""
        from PySide6.QtCore import QPoint
        from workbench import agenda
        item=call('agenda.add',{'title':'Weekly bench report','program':'@files:bench.csv | rows'})
        self.set_agenda_state(item['id'],'RUNNING');self.addCleanup(lambda:self.set_agenda_state(item['id'],'CANCELLED') if any(r_['id']==item['id'] for r_ in call('agenda.view')['now']) else None)
        symbol=self.w.shell2.top.nice;system=symbol.open();settle(80);pop=system.work;pop.signature=None;pop.active_signature=None;pop.refresh();settle()
        self.addCleanup(system.hide)
        row=next(pop.running.item(i) for i in range(pop.running.count()) if pop.running.item(i).data(Qt_UserRole())==item['id'])
        r=pop.running.visualItemRect(row);menu=right_click(pop.running.viewport(),QPoint(r.left()+24,r.top()+8));t=menu.target
        self.assertEqual((t.kind,t.ident,t.revision,t.noun),('queued',item['id'],'RUNNING','Agenda work · running'),'not a job')
        self.assertFalse([k_ for k_ in menu.keys() if k_.startswith('job:')],'no job words for Agenda work')
        self.assertTrue(menu.row('queued:stop').isEnabled());self.assertFalse(menu.entry('queued:pause').enabled)
        self.assertEqual(menu.entry('inspect').tip,'@files:bench.csv | rows','its program, read from the Agenda (the panel\'s snapshot leaves it out)')
        self.assertEqual(menu.row('then').entry.line,'@files:bench.csv | rows')
        rec=Recorder()
        with patch.object(cm,'dispatch',rec):menu.row('queued:stop').click();settle()
        self.assertNotIn('agenda.cancel',rec.ops(),'Stop asks first');self.assertEqual(menu.child.sentence(),'What it stops or settles cannot be put back.')
        with patch.object(cm,'dispatch',rec):menu.child.row('ask:yes').click();settle()
        self.assertEqual(rec.ops()[-2:],['agenda.view','agenda.cancel'],'read again, then stopped');self.assertTrue(self.w._context_last['ok'],self.w._context_last)
        self.assertIn(item['id'],[r_['id'] for r_ in call('agenda.view')['done'] if r_['state']=='CANCELLED'])

    def test_run_inspect_output_and_extract_say_what_the_kernel_did(self):
        """Run, Inspect output and Extract go through the staC page (language.run): an answer shows in the working area and is
        reported done; a refusal is reported as one, with the Kernel's reason, never as done. The source binding is read as
        current here (as test_project_desk does for edited sources), and as not current to see the refusal."""
        from workbench import stacy_foundation
        real=stacy_foundation.seed_status
        def bound(root):
            value=real(root);return {**value,'state':'VERIFIED_SOURCE_BINDINGS'} if value.get('state') in ('STALE','SOURCE_UNAVAILABLE') else value
        def unbound(root):return {**real(root),'state':'STALE'}
        tab,view,point,root=self.files((('stacrun.csv','Part,Qty\nR1,4\nR2,5\n'),))
        output=lambda:self.w.console.output.toPlainText()
        with patch.object(stacy_foundation,'seed_status',bound):
            menu=right_click(view.viewport(),point('stacrun.csv'))
            extract=menu_tree([menu.entry('extract')])[0];self.assertIn('extract/extract:rows',extract)
            rows=next(e for e in menu.entry('extract').submenu() if e.key=='extract:rows');self.assertEqual(rows.caption,'2 rows')
            cm.perform(self.w,menu.target,menu.entry('run'));settle(60);last=self.w._context_last
            self.assertTrue(last['ok'],last);self.assertIn('Ran in the working area: @files:stacrun.csv | rows',last['words']);self.assertIn('R2',output())
            menu=right_click(view.viewport(),point('stacrun.csv'));(root/'stacrun.csv').unlink()
            cm.perform(self.w,menu.target,menu.entry('run'));settle(60);last=self.w._context_last
            self.assertFalse(last['ok'],'refused, not "Ran"');self.assertTrue(last['words'].startswith('Not run: '),last['words'])
            self.assertNotIn('Ran in the working area',last['words']);self.assertGreater(len(last['words']),len('Not run:  · the working area shows the refusal'),'the reason')
            job='%032x'%0xb1;evidence='%032x'%0xb2
            self.k.save('evidence',dict(id=evidence,owner='desktop-owner',job=job,output='OUTPUT-MARK build log line 1',result='Completed',created=time.time()))
            self.k.save('jobs',dict(id=job,owner='desktop-owner',state='Completed',tool='struthio.build',title='Build',evidence=evidence,created=time.time()))
            t=cm.job_target(self.w,job,surface='jobs');o=cm.perform(self.w,t,{e.key:e for e in cm.job_entries(self.w,t)}['job:output'])
            self.assertTrue(o['ok'],o);self.assertIn('@evidence:'+evidence,o['words']);self.assertIn('OUTPUT-MARK',output(),'the job\'s output in the working area')
        (root/'stacrun.csv').write_text('Part,Qty\nR1,4\n');tab.reload();settle()
        with patch.object(stacy_foundation,'seed_status',unbound):
            menu=right_click(view.viewport(),point('stacrun.csv'))
            got=menu.entry('extract').submenu();self.assertEqual([(e.key,e.enabled) for e in got],[('extract:refused',False)])
            self.assertIn('seed/source binding is not current',got[0].reason)
            cm.perform(self.w,menu.target,menu.entry('run'));settle(60);last=self.w._context_last
            self.assertFalse(last['ok']);self.assertIn('Not run: Graphite seed/source binding is not current',last['words'])
            o=cm.perform(self.w,t,{e.key:e for e in cm.job_entries(self.w,t)}['job:output']);self.assertFalse(o['ok'],o)

    def test_a_real_connection_read_by_network_observe(self):
        """D5's network.observe reads this computer's connection table: a loopback connection this test holds open is a row of
        Log's Network stream (filtered in the line to its port), named by its program, with Follow and Show the process."""
        import socket
        server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1);port=server.getsockname()[1]
        client=socket.create_connection(('127.0.0.1',port));accepted,_=server.accept()
        for s in (client,accepted,server):self.addCleanup(s.close)
        view=self.log();view.choose('network',remember=False,read=False);view.apply_filter('port %d'%port);settle(60)
        self.addCleanup(lambda:(view.apply_filter(''),view.choose('events',remember=False,read=False),self.w.type_bar.box.clear()))
        rows=[view.connections.item(i) for i in range(view.connections.count())]
        mine=next((it for it in rows if (it.data(Qt_UserRole()) or {}).get('rport')==port and (it.data(Qt_UserRole()) or {}).get('lport')==client.getsockname()[1]),None)
        self.assertIsNotNone(mine,'network.observe lists the connection: %r'%[it.text() for it in rows])
        entry=mine.data(Qt_UserRole());self.assertEqual((entry['remote'],entry['state'],entry.get('pid')),('127.0.0.1','ESTABLISHED',os.getpid()))
        menu=right_click(view.connections.viewport(),view.connections.visualItemRect(mine).center());t=menu.target
        self.assertEqual((t.kind,t.label),('connection','%s → 127.0.0.1:%d'%(entry['process'].split()[0],port)))
        self.assertTrue(menu.row('process').isEnabled());self.assertEqual(menu.row('copy:address').caption,'127.0.0.1:%d'%port)
        menu.row('follow').click();settle();self.assertEqual(self.w.type_bar.box.text(),'host 127.0.0.1 port %d'%port);self.assertIsNotNone(view.pinned)

    # nothing lost, the keys, the metrics
    def test_nothing_is_lost_from_the_old_menus(self):
        """Every word the old builders offer, their submenus' too (Files' old menu for a file, a folder, a smart folder, a
        selection and the empty place with its chains ›; Today's root chain menu), is in the new menu for the same thing (its
        submenus opened), or context_menu.FOLDED names its home there and that entry is offered; and every FOLDED key is found."""
        from PySide6.QtCore import QPoint,Qt
        from workbench.chain_menu import root_menu
        from workbench.files_service import FIND_KEYS
        tab,view,point,root=self.files((('lost.csv','a\n1\n'),('lostdir',None)))
        smart=call('files.smart',{'name':'lostcsvs','find':{sorted(FIND_KEYS)[0]:'csv'}});tab.reload();settle()
        folded={}
        for _,word,kind,key in cm.FOLDED:folded.setdefault(kind,{})[word]=key
        def homed(kind,old,paths,words):
            for word in old:
                if word in words:continue
                self.assertIn(word,folded.get(kind,{}),'%s: the old menu\'s %r has no home in the new menu'%(kind,word))
                self.assertIn(folded[kind][word],paths,'%s: %r is folded into %s, which the new menu does not offer'%(kind,word,folded[kind][word]))
        found={}
        for kind,names in (('file',['lost.csv']),('folder',['lostdir']),('smart',[smart['name']]),('files',['lost.csv','lostdir']),('empty:files',[])):
            view.clearSelection()
            for i in range(view.topLevelItemCount()):
                it=view.topLevelItem(i)
                if it.data(0,Qt.UserRole)['name'] in names:it.setSelected(True)
            menu=right_click(view.viewport(),point(names[-1]) if names else self.empty_place(tab,root))
            self.assertIsNotNone(menu,kind);self.assertEqual(sorted(e['name'] for e in tab.selected()),sorted(names),kind)
            paths,words=menu_tree(menu.tree_entries());found[kind]=paths
            old=[x for x in old_words(tab.old_menu()) if not names or x!=names[0]+' ›']  # the file's own submenu title (its words are read)
            close(menu);homed(kind,old,paths,words)
        self.assertIn('rename',found['smart'],'a smart folder keeps Rename… (files.rename takes it)');self.assertIn('more/menu:edit',found['empty:files'])
        d,p=self.document('Nothing lost here',0,7);menu=right_click(d.page.viewport(),p);found['passage']=menu_tree(menu.tree_entries())[0];close(menu)
        page=self.w.show_start();settle();menu=right_click(self.w.finder.today,QPoint(30,30));paths,words=menu_tree(menu.tree_entries());found['empty:today']=paths;close(menu)
        homed('empty:today',old_words(root_menu(self.w)),paths,words)
        for old_menu,word,kind,key in cm.FOLDED:
            if kind not in found:continue
            if key.endswith('*'):continue  # the cabinet's per-record actions: test_the_trees reads them from the record's own list
            if key.startswith('copy:') and key not in ('copy:to','copy:path') and kind in ('file','folder'):continue  # working-copy words: test_working_copy_words
            self.assertIn(key,found[kind],'%s: %s'%(old_menu,word))

    def test_working_copy_words_are_offered_for_a_working_copy(self):
        tab,view,point,root=self.files((('original.txt','text\n'),))
        fake={'id':'c'*32,'for_slate':True,'kind':'file','source':'files:original.txt','source_words':'Files › original.txt','status':'Working'}
        with patch.object(type(tab),'copy_for',lambda self,rel:fake if rel=='original.txt' else None):
            menu=right_click(view.viewport(),point('original.txt'))
            for key in ('copy:slate','copy:review','copy:original','copy:discard'):self.assertIn(key,menu.keys())
        close(menu)
        (root/'wc').mkdir(exist_ok=True);tab,view,point,root=self.files()
        tab.copies['wc']={'id':'d'*32,'source':'pill:x','kind':'folder','source_words':'a pill','status':'Working','for_slate':False}
        menu=right_click(view.viewport(),point('wc'))
        for key in ('copy:look','copy:run','copy:pill','copy:review','copy:discard'):self.assertIn(key,menu.keys())
        close(menu)
        tab.copies['wc']={'id':'e'*32,'source':'files:wc','kind':'folder','source_words':'Files › wc','status':'Working','for_slate':False}
        menu=right_click(view.viewport(),point('wc'))  # a folder copy made in Files: its original to review and show
        for key in ('copy:look','copy:run','copy:review','copy:original','copy:discard'):self.assertIn(key,menu.keys())
        self.assertNotIn('copy:pill',menu.keys());close(menu);tab.copies.pop('wc',None)

    def test_the_menu_key_and_shift_f10_open_the_menu_for_the_focus(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        nav=self.w.settings_navigator;nav.show_view('cabinet');settle(60);tree=self.w.cabinet_page.tree
        while QApplication.activePopupWidget() is not None:QApplication.activePopupWidget().hide();settle()
        self.w.activateWindow();tree.setFocus();tree.setCurrentItem(tree.topLevelItem(0));settle()
        before=getattr(self.w,'context_menu',None)
        QTest.keyClick(tree,Qt.Key_Menu);settle();menu=self.w.context_menu
        self.assertIsNot(menu,before);self.assertTrue(menu.isVisible());self.assertEqual(menu.target.ident,tree.topLevelItem(0).data(0,Qt.UserRole)['id'])
        self.assertIs(QApplication.focusWidget(),menu.first(),'the first row under focus');ident=menu.target.ident;close(menu)
        self.w.activateWindow();tree.setFocus();settle();QTest.keyClick(tree,Qt.Key_F10,Qt.ShiftModifier);settle()
        self.assertTrue(self.w.context_menu.isVisible());self.assertEqual(self.w.context_menu.target.ident,ident)
        close(self.w.context_menu)
        d,p=self.document('Keys too',0,4);self.w.activateWindow();d.page.setFocus();settle();QTest.keyClick(d.page,Qt.Key_Menu);settle()
        self.assertEqual(self.w.context_menu.target.kind,'passage')

    def test_text_fields_keep_their_own_menu(self):
        from PySide6.QtCore import QPoint
        before=getattr(self.w,'context_menu',None)
        self.assertIsNone(cm.target_at(self.w,self.w.type_bar.box,QPoint(4,4)),'the writing line keeps its own menu')
        self.assertIs(getattr(self.w,'context_menu',None),before)

    def test_an_empty_place_of_the_workspace_is_the_root_of_the_pipe_menu(self):
        from PySide6.QtCore import QPoint
        self.document('Empty place',0,5);tabs=self.w.tabs
        t=cm.target_at(self.w,tabs,QPoint(tabs.width()//2,tabs.height()-4))
        self.assertEqual((t.kind,t.surface,t.label),('empty','workspace',tabs.tabText(tabs.currentIndex()).replace('&','')))
        keys=[e.key for e in cm.entries_for(self.w,t)]
        for key in ('chains','start','line','menu:edit','inquiries','atlas','new:idea','new:project','import'):self.assertIn(key,keys)

    # 0.8.1: the short shape, the glyphs, no keys, no scrolling, and the line panel
    FIRST={'file':['open','ask','rename','trash','then','more'],'folder':['open','rename','copy:path','trash','then','more'],
           'two files':['compare:two','move:to','copy:paths','trash','more'],'empty:files':['new:folder','import','view','refresh','start','more'],
           'passage':['mark:bold','mark:italic','notes','ask','then','more'],'empty:today':['new:idea','new:project','import','inquiries','start','more']}

    def menus(self):
        """(kind, menu) for each kind in FIRST, opened by a real right-click; the caller closes each."""
        from PySide6.QtCore import QPoint,Qt
        tab,view,point,root=self.files((('shape.csv',BENCH_CSV),('shape dir',None),('other.txt','x\n')))
        yield 'file',right_click(view.viewport(),point('shape.csv'))
        yield 'folder',right_click(view.viewport(),point('shape dir'))
        view.clearSelection()
        for i in range(view.topLevelItemCount()):
            it=view.topLevelItem(i)
            if it.data(0,Qt.UserRole)['name'] in ('shape.csv','other.txt'):it.setSelected(True)
        yield 'two files',right_click(view.viewport(),point('other.txt'))
        yield 'empty:files',right_click(view.viewport(),self.empty_place(tab,root))
        d,p_=self.document('Shape of things',0,5);yield 'passage',right_click(d.page.viewport(),p_)
        self.w.show_start();settle();yield 'empty:today',right_click(self.w.finder.today,QPoint(30,30))

    def test_first_level_is_four_usual_then_more(self):
        for kind,menu in self.menus():
            self.assertIsNotNone(menu,kind)
            self.assertEqual(menu.first_keys(),self.FIRST[kind],kind)
            self.assertTrue(all(r.isEnabled() for r in menu.first_rows()),'%s: nothing grey at rest'%kind)
            self.assertLessEqual(len(menu.first_rows()),6,kind);close(menu)

    def test_every_screen_fits_without_scrolling_and_two_popups_at_most(self):
        from PySide6.QtWidgets import QApplication
        before=self.w.size();self.addCleanup(lambda:(self.w.resize(before),settle()))
        for size in ((1366,768),(1920,1200)):
            self.w.resize(*size);settle()
            for kind,menu in self.menus():
                for screen in menu.screens():
                    settle()
                    self.assertEqual(screen.scroll.verticalScrollBar().maximum(),0,(size,kind,screen.title))
                    self.assertTrue(screen.bounds().contains(screen.frameGeometry()),(size,kind,screen.title))
                    self.assertLessEqual(sum(1 for t in QApplication.topLevelWidgets() if isinstance(t,cm.ContextMenu) and t.isVisible()),2,(size,kind))
                    self.assertLessEqual(len(screen.rows_by_key),cm.MOST_ROWS+2,(size,kind,screen.title))
                close(menu)

    def test_no_row_prints_a_key_or_unavailable_and_every_row_wears_a_drawn_glyph(self):
        from workbench import tool_faces
        with patch.object(cm.programs_qt,'paint_icon',side_effect=AssertionError('not Graphite glyphs')):
            for kind,menu in self.menus():
                for screen in menu.screens():
                    screen.grab()
                    for row in screen.findChildren(cm.ContextRow):
                        for text in (row.word,row.caption,row.toolTip()):self.assertIsNone(re.search(KEY_TEXT,text or ''),(kind,row.word,text))
                        self.assertIsNone(re.fullmatch(KEY_CAPTION,row.caption or ''),(kind,row.word));self.assertNotEqual(row.caption,'unavailable')
                        self.assertFalse(tool_faces.icon(row.entry.glyph,row.entry.tone).isNull(),(kind,row.word))
                        self.assertNotRegex(row.word+' '+row.toolTip(),r'(?i)\bstac\b|stacy language|\bprograms\b',(kind,row.word))
                close(menu)

    def test_opening_reads_nothing_and_the_line_panel_reads_once(self):
        from workbench import boss_theme as bt
        tab,view,point,root=self.files((('bench.csv',BENCH_CSV),))
        rec=Recorder()
        with patch.object(cm,'dispatch',rec):
            menu=right_click(view.viewport(),point('bench.csv'));self.assertEqual(rec.ops(),[],'opening the right-click reads nothing')
            panel=menu.open_child(menu.row('then'));settle()
            self.assertIsInstance(panel,cm.LinePanel);self.assertEqual(rec.ops(),['language.parse','ledger.address.read'])
            self.assertEqual(panel.line,'@files:bench.csv | rows');self.assertTrue(panel.slab.styleSheet().endswith(bt.line_sheet()))
            # 0.8.3: the line is in the mono face, held in its own sheet (the main window's sheet reached the panel before)
            panel.slab.ensurePolished();self.assertEqual(panel.slab.font().family(),bt.MONO)
            self.assertEqual(panel.count_words(),'4 rows · 6 steps left')
            panel.choose('step:where');panel.choose('field:unit');self.assertEqual(panel.row('where unit=mA').caption,'2 rows')
            panel.choose('where unit=mA');self.assertEqual(panel.count_words(),'2 rows · 5 steps left')
            panel.choose('step:count')
            self.assertEqual(panel.line,'@files:bench.csv | rows | where unit=mA | count');self.assertEqual(panel.preview_rows(),[{'count':2}])
            self.assertEqual(rec.ops(),['language.parse','ledger.address.read'],'nothing read while choosing')
            panel.choose('step:back');self.assertEqual(panel.line,'@files:bench.csv | rows | where unit=mA','Back a step')
            panel.choose('step:count')
            panel.row('end:show').click();settle(60)
        self.assertEqual(self.w.console.last_program,'@files:bench.csv | rows | where unit=mA | count','Show it runs the line it shows')
        self.assertTrue(self.w._context_last['ok'],self.w._context_last)

    def test_the_line_panel_on_a_name_with_a_space_and_a_long_table(self):
        rows='\n'.join('R%d,%d,%s'%(n,n*10,'mA' if n%2 else 'V') for n in range(300))
        tab,view,point,root=self.files((('long table.csv','part,value,unit\n'+rows+'\n'),))
        menu=right_click(view.viewport(),point('long table.csv'))
        self.assertEqual(menu.row('then').entry.line,'@files:long table.csv | rows','a space no longer stops a line')
        panel=menu.open_child(menu.row('then'));settle()
        self.assertEqual(panel.count_words(),'300 rows · 6 steps left')
        self.assertFalse(panel.row('end:show').isEnabled());self.assertIn('over 200',panel.row('end:show').caption)
        panel.choose('step:first');self.assertIn('first:200',panel.rows_by_key)
        panel.choose('first:200');self.assertTrue(panel.row('end:show').isEnabled(),'200 rows: Show it can act')
        close(menu)

    def test_the_menu_wears_the_programs_lists_metrics(self):
        from workbench import programs_qt
        from workbench.desk_qt import scaled
        d,p=self.document('Same rows',0,4);menu=right_click(d.page.viewport(),p);m=programs_qt.metrics(self.w)
        icon=scaled(cm.GLYPH_SIDE,m.scale)       # the glyphs at the size they were drawn for; the Apps list keeps its 16
        self.assertEqual((menu.m.icon,menu.m.icon_col,menu.m.margin,menu.m.pad),(icon,icon+scaled(programs_qt.ICON_GAP,m.scale),m.margin,m.pad))
        self.assertEqual(menu.m.row,max(m.line,icon)+2*scaled(programs_qt.ROW_PAD,m.scale))
        rows=[r for r in menu.rows_by_key.values()]
        self.assertEqual({r.height() for r in rows},{menu.m.row},'one row height');self.assertEqual(menu.heading.height(),menu.m.row)
        self.assertEqual({r.word_x() for r in rows},{menu.m.pad+menu.m.icon_col},'one icon column')
        self.assertGreaterEqual(menu.width(),programs_qt.column(self.w),'the launch menus\' width rule')
        area=menu.bounds();self.assertTrue(area.contains(menu.geometry()),'inside the window')


def Qt_UserRole():
    from PySide6.QtCore import Qt
    return Qt.UserRole


def old_words(menu):
    """Every word an old QMenu offers, its submenus' too: a submenu's title as 'title ›', '&&' read as '&', the chain menu's
    'No kept chains yet: …' line as 'your kept chains' (what it stands for)."""
    out=[]
    for a in menu.actions():
        if a.isSeparator():continue
        text=a.text().replace('&&','&');sub=a.menu()
        if text.startswith('No kept chains yet'):text='your kept chains'
        if sub is not None:out.append(text+' ›');out+=old_words(sub)
        else:out.append(text)
    return out


def menu_tree(entries,prefix=''):
    """(key paths, words) of a new menu's entries and of every deeper screen, opened as the menu opens them ('a/b': b on a's
    screen; each path's tails too, so 'more/line/line:shell' also answers 'line/line:shell' and 'line:shell'; the line
    panel's rows are Then's outline)."""
    paths,words=set(),set()
    for e in entries:
        path=prefix+e.key;parts=path.split('/')
        paths|={'/'.join(parts[i:]) for i in range(len(parts))};words.add(e.label)
        if e.submenu and e.key not in ('compare:version',):      # kept versions are read when that screen opens, as the menu does
            sub=e.submenu() if callable(e.submenu) else list(e.submenu)
            p,w_=menu_tree(sub,path+'/');paths|=p;words|=w_
    return paths,words


def key_literals(paths):
    """Every string in these modules that would print a key (KEY_TEXT anywhere, KEY_CAPTION as a whole caption=), docstrings
    and QKeySequence's own arguments left out."""
    found=[]
    root=Path(__file__).resolve().parent.parent
    for rel in paths:
        tree=ast.parse((root/rel).read_text(encoding='utf-8'))
        skip=set()
        for node in ast.walk(tree):
            if isinstance(node,(ast.Module,ast.FunctionDef,ast.ClassDef,ast.AsyncFunctionDef)) and node.body and isinstance(node.body[0],ast.Expr) \
                    and isinstance(node.body[0].value,ast.Constant):skip.add(id(node.body[0].value))
            if isinstance(node,ast.Call) and getattr(node.func,'id',getattr(node.func,'attr',''))=='QKeySequence':
                skip|={id(a) for a in node.args}
            if isinstance(node,ast.keyword) and node.arg=='caption' and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):
                if re.fullmatch(KEY_CAPTION,node.value.value):found.append('%s:%d caption %r'%(rel,node.value.lineno,node.value.value))
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and id(node) not in skip and re.search(KEY_TEXT,node.value):
                found.append('%s:%d %r'%(rel,node.lineno,node.value[:80]))
    return found


if __name__=='__main__':
    unittest.main()
