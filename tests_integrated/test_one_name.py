"""0.8.4, one name: she is Kasandra in every look (the owner, 19 November 2026: "Just kas. Otherwise we have too many
people"). Until 0.8.3 the first look showed her as Stacy.

What is held here:
  the name     assistant_identity.NAME and named() give Kasandra whatever the look.
  the code     every sentence in the program's code that carries her earlier name goes through named(), or is on the short
               list of what is not a shown name (tools/name_sweep.CODE_KEPT: records, object names, file names); the
               phone page and the guide pages the program opens say no earlier name either.
  the window   in each look a child process builds the window on the bench seed (test_desk_acts.build_window) and walks it
               (tools/name_sweep.walk: the head's menus, the meters' cards, both panes, Files and the Field with their
               right-clicks, the writing line, her hand; a brain event in Activity, pinned in the Log and in Search; About
               Graphite; her art plate opened). No word read there, shown or waiting in a hidden widget, says Stacy or
               names the language; her name is on the strip and in her column, whole, at 1920 by 1200 and at 1366 by 768.
  history      an agenda row written under Stacy reads back as it was written, and a row written now says Kasandra. An
               event keeps the actor it was written with ('STACY') and is read with her name.

Run alone:  python3 -B -m unittest -v tests_integrated.test_one_name
"""
import json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from tools import name_sweep

ROOT=Path(__file__).resolve().parents[1]
LOOKS=('graphite','kasandra')
MARK='ONE NAME '
OLD_REASON="Waiting for Stacy's brain: choose a model in Brain, and she will take it up."      # as 0.6.0 to 0.8.3 wrote it


def child(arguments,look,timeout=600):
    """A fresh Python in one look, in the program's folder, with its own empty home."""
    with tempfile.TemporaryDirectory(prefix='graphite-one-name-home-') as home:
        env=dict(os.environ,GRAPHITE_APPEARANCE=look,QT_QPA_PLATFORM='offscreen',HOME=home)
        for key in ('ARC1_WORKBENCH_CONFIG_HOME','ARC_LEDGER_CONCERN','ARC_LEDGER_XSESSION'):env.pop(key,None)
        return subprocess.run([sys.executable,'-B',*arguments],cwd=str(ROOT),env=env,capture_output=True,text=True,timeout=timeout)


def window_report():
    """In the child: the window on the bench seed, swept on its walk, and how her name stands at two sizes."""
    sys.path.insert(0,str(ROOT/'tools'))
    import ui_fit
    from PySide6.QtWidgets import QAbstractButton,QLabel
    from tests_integrated.test_desk_acts import act,build_window,close_window,settle
    from workbench import assistant_identity,boss_theme
    store={};build_window(store,'graphite-one-name-')
    try:
        w=store['w'];out=name_sweep.walk(w,lambda:settle(store))
        out.update(look=boss_theme.APPEARANCE,name=assistant_identity.NAME,sizes={})
        for size in ((1920,1200),(1366,768)):
            w.resize(*size);settle(store,60)
            for name,args in (('menu.close',{}),('go.today',{}),('go.pane',{'right':'talk'})):act(name,args,store=store)
            face=w.shell2.face;strip=w.type_bar.targets['line']      # 1.0 D1: Line in her place at the foot
            named=lambda:[x for x in [w]+w.findChildren(QLabel)+w.findChildren(QAbstractButton) if x.isVisible() and assistant_identity.NAME in ui_fit.plain(x)]
            cut=lambda:ui_fit.describe([f for f in ui_fit.whole_words(w) if assistant_identity.NAME in str(f.get('text',''))])
            row={'window':[w.width(),w.height()],'strip':strip.text(),'strip_shown':strip.isVisible(),'said':len(named()),'clipped':cut()}
            # her own look says her name on her masthead; the first look has her face there, and her name on the strip
            row['column']=[face.masthead.name.text(),face.masthead.name.isVisible()] if face.masthead is not None else None
            column=getattr(w,'her_column',None)      # 1.0 P1: in every look her name is said at the head of her column
            if column is not None:row['column']=[column.head.name.text(),column.head.name.isVisible()]
            act('go.pane',{'right':'activity'},store=store)      # the pane's title is the way back to her, by her name, in both looks
            title=getattr(w.shell2,'title_word',None)
            row['back']=[ui_fit.plain(title),title.isVisible(),ui_fit.describe(ui_fit.whole_words(title))] if title is not None else None
            row['clipped_back']=cut()
            act('go.pane',{'right':'talk'},store=store)
            out['sizes']['%dx%d'%size]=row
    finally:close_window(store)
    print(MARK+json.dumps(out,ensure_ascii=False),flush=True)


class TheName(unittest.TestCase):
    def test_she_is_kasandra_whatever_the_look(self):
        code=('from workbench import assistant_identity as a,boss_theme as t,typebar_qt as bar;'
              'print(t.APPEARANCE);print(a.NAME);print(__import__("workbench.foot_line").foot_line.ASK.split()[1]);print(a.named("Ask Stacy about this"));print(a.named("TEXT · WHAT STACY HOLDS"))')      # 1.0 D1
        for look in LOOKS:
            with self.subTest(look=look):
                out=child(['-c',code],look,120);self.assertEqual(out.returncode,0,out.stderr[-2000:])
                self.assertEqual(out.stdout.split('\n')[:5],[look,'Kasandra','Kasandra','Ask Kasandra about this','TEXT · WHAT KASANDRA HOLDS'])

    def test_named_leaves_what_is_not_text_alone(self):
        from workbench.assistant_identity import named
        self.assertIsNone(named(None));self.assertEqual(named(7),7);self.assertEqual(named('Terminal'),'Terminal')
        self.assertEqual(named("Stacy's hand: STACY"),"Kasandra's hand: KASANDRA")


class TheSweepItself(unittest.TestCase):
    def test_what_counts_as_a_name(self):
        said=name_sweep.named_in
        self.assertEqual(said('Ask Stacy about this'),['stacy']);self.assertEqual(said('TEXT · WHAT STACY HOLDS'),['stacy'])
        self.assertEqual(said('a staC line'),['language']);self.assertEqual(said('stac ›'),['language'])
        for words in ('Ask Kasandra about this','the call stack','stacy.hand','stacy_hand','arc.stacy-trail/1','stac.compile','Files/Slate'):
            self.assertEqual(said(words),[],words)
        self.assertEqual(said('stacy.hand set by Stacy'),['stacy'],'an identity is set aside, a name beside it is not')
        # an event printed whole as it is stored keeps its actor; words made from it for reading do not (name_sweep's note)
        self.assertEqual(said(json.dumps({'origin':'STACY','operation':'brain.worker','state':'READY'},indent=2)),[])
        for words in ('origin STACY','at 12:00:01   operation brain.worker   state READY   origin STACY','"detail": "STACY is ready"','Stacy · brain.worker'):
            self.assertEqual(said(words),['stacy'],words)

    def test_a_key_named_in_the_programs_own_words_is_found_and_programs_is(self):
        # 0.8.4: no keyboard shortcut is printed on screen, and the list is "Apps". These were tips of 0.8.3.
        said=name_sweep.named_in
        for words in ('Build the target for the work in front of you (F7)','Click: confirm Stop all · Ctrl+Shift+F12','Console\tCtrl+`','Run an operation…\tAlt+3',
                      "words in Graphite's events  ·  Enter filters",'words and Enter filter them','Tab completes, Enter runs','Enter opens one, Esc comes back',
                      'Right or Enter opens the rows.','Move the pointer or press a key to return to work.','Select related files with Ctrl or Shift.','Ctrl Z takes it back',
                      'Arrow keys navigate, Z selects','Fill the display; F11 returns to the previous window',
                      # the review of 0.8.4: a key in brackets, another verb, a hyphen, the Mac's sign, keys by their own names
                      'Show or hide the preview (Space)','Hide Graphite  (Esc)','Select a row and hit Enter','Save the page with Ctrl-S','Save the page with ⌘S',
                      'Backspace goes up a folder','PgUp scrolls the surface','Choose a row with the pointer or Return'):
            for kind in ('toolTip','statusTip','accessibleDescription','whatsThis','text'):
                self.assertEqual(said(words,kind),['key'],(kind,words))
            self.assertEqual(said(words),['key'],words)
            for kind in ('row','row tip','toPlainText'):self.assertEqual(said(words,kind),[],'a row and the text of a page are the owner\'s data')
        for words in ('Enter one named quote per line.','Return to the files and rooms you had open','Close Tab','Open in a new tab','Shift the column left',
                      'Type to filter the tree','the keys of a record','Alt text for a picture','F12a connector','Space for one more row','Keep it, and it goes to Notes exactly as written',
                      # names and words that are not keys (the review of 0.8.4 found the first two read as keys)
                      'Matching F45 / F12 curves overlap.','Escape sequences are shown as typed.','net F3 / F4','the F7 net','Delete the row','Return to the list',
                      'Hit rate 92 %','Tap water','Shift-register outputs','Space (2 TB free)'):
            self.assertEqual(said(words,'toolTip'),[],words)
        self.assertEqual(said('Programs Graphite does not manage keep running','toolTip'),['programs']);self.assertEqual(said('Programs','row'),['programs'])
        for words in ('Apps','the programs installed here','programs.mail.read','ProgramsList'):self.assertEqual(said(words),[],words)
        for kept,why in name_sweep.KEYS_KEPT:      # reviewed: a key that must be pressed, with nothing to click in its place
            self.assertTrue(name_sweep.KEYS.search(kept),kept);self.assertEqual(said('Open apps · '+kept,'accessibleDescription'),[],kept);self.assertGreater(len(why),20)

    def test_the_sweep_finds_a_key_in_a_tip_a_status_tip_a_description_and_whats_this(self):
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QApplication,QListWidget,QPushButton,QVBoxLayout,QWidget
        app=QApplication.instance() or QApplication([])
        window=QWidget();layout=QVBoxLayout(window)
        save=QPushButton('Save');save.setToolTip('Save the page (Ctrl+S)');save.setStatusTip('Press Enter to save');layout.addWidget(save)
        find=QPushButton('Find');find.setAccessibleDescription('Find in the page; F3 goes to the next');find.setWhatsThis('Esc closes it');layout.addWidget(find)
        line=QAction('Output   (F10)',window);line.setWhatsThis('Shift+F10 opens it');window.addAction(line)
        rows=QListWidget();rows.addItem('typed: press F5 to run, then Ctrl+C');layout.addWidget(rows)
        found=name_sweep.sweep(window,'a test window')
        self.assertEqual(sorted((f['widget'],f['kind'],f['words']) for f in found if f['name']=='key'),
                         [('QAction','text','Output   (F10)'),('QAction','toolTip','Output   (F10)'),('QAction','whatsThis','Shift+F10 opens it'),
                          ('QPushButton','accessibleDescription','Find in the page; F3 goes to the next'),('QPushButton','statusTip','Press Enter to save'),
                          ('QPushButton','toolTip','Save the page (Ctrl+S)'),('QPushButton','whatsThis','Esc closes it')])
        import shiboken6
        shiboken6.delete(window);app.processEvents()      # gone now: the next sweep reads every window there is

    def test_the_guide_pages_shown_in_the_program_name_no_key_and_say_apps(self):
        self.assertEqual(name_sweep.in_guides(ROOT),[])
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp)/'GUIDE.md').write_text('Open the Field.\nSearch commands with Ctrl+Shift+P.\nThe Programs list is at the upper right.\n'+name_sweep.KEYS_KEPT[-1][0]+'\n',encoding='utf-8')
            # 1.1 W1: a Guide page may name a key now (keys are shown; "Show keys" hides them in menus and tips); Programs is still Apps
            self.assertEqual([(page,number) for page,number,_ in name_sweep.in_guides(temp,('GUIDE.md',))],[('GUIDE.md',3)])
            self.assertEqual([(page,number) for page,number,_ in name_sweep.in_guides(temp,('GUIDE.md',),keys=True)],[('GUIDE.md',2),('GUIDE.md',3)])

    def test_the_code_sweep_reads_sentences_and_not_documentation(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'workbench';folder.mkdir()
            (folder/'page.py').write_text('"""Stacy answers here."""\nfrom .assistant_identity import named\n'
                                          'class Page:\n    """Stacy\'s page."""\n    def words(self):\n        """What Stacy says."""\n'
                                          '        return [named(\'Ask Stacy\'), named(\'Tell %s\') % \'x\', \'Ask Stacy to plan\', self.tr("STACY HOLDS")]\n'
                                          'ACTOR = \'STACY\'      # a record\n',encoding='utf-8')
            found=name_sweep.in_code(temp,('workbench',),kept={})
            self.assertEqual([(f,line,words) for f,line,words in found],[('workbench/page.py',7,'Ask Stacy to plan'),('workbench/page.py',7,'STACY HOLDS'),('workbench/page.py',8,'STACY')])
            kept={('workbench/page.py','STACY'):'a record'}
            self.assertEqual([words for _,_,words in name_sweep.in_code(temp,('workbench',),kept=kept)],['Ask Stacy to plan'],'what is kept is kept by its file and its first words')

    def test_the_code_sweep_for_keys_reads_sentences_and_not_a_keys_own_name(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'workbench';folder.mkdir()
            (folder/'page.py').write_text('"""Esc closes the page."""\nfrom PySide6.QtGui import QKeySequence\n'
                                          'def words(button, action):\n    """Ctrl+S saves it."""\n'
                                          '    button.setToolTip(\'Show the preview (Space)\')      # Esc in a comment\n'
                                          '    action.setShortcut(QKeySequence(\'Ctrl+Shift+N, Esc closes\'));A(\'New\', None, \'Ctrl+N\', shortcut=\'Esc closes it\')\n'
                                          '    return [\'Run an operation…\\tAlt+3\', \'F7 or Ctrl+Shift+B\', \'PgUp  PgDn\', \'Saved · Ctrl Z takes it back\', \'Esc  close\']\n',encoding='utf-8')
            found=name_sweep.keys_in_code(temp,kept={})
            self.assertEqual([(line,words) for f,line,words in found],[(5,'Show the preview (Space)'),(7,'Saved · Ctrl Z takes it back'),(7,'Esc  close')])
            kept={('workbench/page.py','Esc  close'):'a key label you click'}
            self.assertEqual([words for _,_,words in name_sweep.keys_in_code(temp,kept=kept)],['Show the preview (Space)','Saved · Ctrl Z takes it back'])
            self.assertEqual(name_sweep.keys_in_code(temp,kept={('workbench/page.py',''):'the whole file'}),[])

    def test_the_sweep_reads_a_widget_that_is_hidden_and_a_menu_line(self):
        from PySide6.QtWidgets import QApplication,QLabel,QMenu,QPushButton,QVBoxLayout,QWidget
        app=QApplication.instance() or QApplication([])
        window=QWidget();layout=QVBoxLayout(window)
        hidden=QLabel('Ask Stacy');layout.addWidget(hidden);hidden.hide()
        button=QPushButton('Terminal');button.setToolTip('Stacy: ask in your own words');button.setAccessibleName('a staC line');layout.addWidget(button)
        menu=QMenu('Rules',window);menu.addAction("Stacy's hand");layout.addWidget(QLabel('Kasandra'))
        read=set();found=name_sweep.sweep(window,'a test window',read=read)
        self.assertEqual(sorted((f['name'],f['widget'],f['kind'],f['words']) for f in found),
                         [('language','QPushButton','accessibleName','a staC line'),('stacy','QAction','text',"Stacy's hand"),('stacy','QAction','toolTip',"Stacy's hand"),
                          ('stacy','QLabel','text','Ask Stacy'),('stacy','QPushButton','toolTip','Stacy: ask in your own words')])
        self.assertTrue({'Kasandra','Terminal','Rules'}<=read,read)
        self.assertEqual({f['where'] for f in found},{'a test window'})
        window.deleteLater();app.processEvents()


class TheCode(unittest.TestCase):
    def test_every_sentence_with_her_earlier_name_goes_through_named(self):
        left=name_sweep.in_code(ROOT)
        self.assertEqual(left,[],'these words would be read as Stacy; put them through assistant_identity.named(), or say in tools/name_sweep.CODE_KEPT why they are not a shown name')

    def test_what_is_kept_is_still_in_the_code(self):
        # an entry of CODE_KEPT whose words are gone would let the same words back in unseen
        everything=name_sweep.in_code(ROOT,kept={})
        for (file,start),why in name_sweep.CODE_KEPT.items():
            self.assertTrue(any(f==file and words.startswith(start[:160]) for f,_,words in everything),(file,start));self.assertTrue(why.strip(),(file,start))

    def test_keys_are_shown_in_menus_and_tips_and_show_keys_hides_them(self):
        # 1.1 W1 moves this test to the new truth (PLAN_1.1.md section 6, reversing the owner's rule of 13 Nov): a sentence in the
        # code may name a key, menus print a line's key beside it, and the one setting "Show keys" turns every printed key off.
        # The finder still finds them (keys_in_code: a list to read), and KEYS_CODE_KEPT's reviewed entries still stand.
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QApplication,QMenu
        from workbench import tool_faces,windows_hand
        app=QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp:
            env={'XDG_CONFIG_HOME':temp}
            with patch.dict(os.environ,env):
                for shown in (True,False):
                    windows_hand.write(show_keys=shown)
                    menu=QMenu();line=QAction('Copy',menu);line.setShortcut('Ctrl+C');menu.addAction(line);tab=menu.addAction('Run\tAlt+3')
                    tool_faces.dress(menu)
                    self.assertEqual(line.isShortcutVisibleInContextMenu(),shown)
                    self.assertEqual(tab.text(),'Run\tAlt+3' if shown else 'Run')
                    self.assertEqual(windows_hand.keyed('Rename','F2'),'Rename (F2)' if shown else 'Rename')
                    self.assertEqual(name_sweep.named_in('Rename (F2)','toolTip',keys=not windows_hand.show_keys()),[] if shown else ['key'])
                    menu.deleteLater()
        app.processEvents()
        self.assertTrue(name_sweep.keys_in_code(ROOT,kept={}),'the finder still finds the keys the code names')
        everything=name_sweep.keys_in_code(ROOT,kept={})
        for (file,start),why in name_sweep.KEYS_CODE_KEPT.items():
            self.assertTrue((ROOT/file).exists(),file);self.assertGreater(len(why),20,(file,start))
            if start:self.assertTrue(any(f==file and words.startswith(start) for f,_,words in everything),(file,start))

    def test_tips_and_notes_the_walk_does_not_reach_name_no_key(self):
        # 0.8.4: put right with the ones the walk reads. Each named a key where there is something to click in its place.
        from workbench import log_qt,system_menu_qt
        for words in list(log_qt.HINTS.values())+list(log_qt.NOTES.values())+[system_menu_qt.STOP_TIP]:
            self.assertEqual(name_sweep.named_in(words,'toolTip'),[],words)
        for file,mark in (('workbench/home_qt.py','self.startup.setToolTip('),('workbench/hardware_overview.py','items · double-click'),('workbench/spice_qt.py','exact native samples'),
                          ('workbench/log_qt.py','No capture is running'),('workbench/arc_desktop.py','host.global_search.setToolTip('),('workbench/arc_desktop.py','host.tree_search.setToolTip('),('workbench/qt_app.py','self.global_search.setToolTip(')):
            lines=[line for line in (ROOT/file).read_text(encoding='utf-8').splitlines() if mark in line]
            self.assertTrue(lines,(file,mark))
            for line in lines:self.assertEqual(name_sweep.named_in(line,'toolTip'),[],(file,line.strip()[:140]))

    def test_the_phone_page_says_no_earlier_name(self):
        # workbench/remote_pwa is served to the owner's phone as it stands; '/stacy.png' is a picture's address, not a word
        pattern=name_sweep.NEVER['stacy'][0];said=[]
        for path in sorted((ROOT/'workbench/remote_pwa').iterdir()):
            if path.suffix in ('.js','.html','.css','.webmanifest','.json'):
                said+=[(path.name,n,line.strip()[:160]) for n,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1) if pattern.search(line)]
        self.assertEqual(said,[])

    def test_the_guide_pages_say_her_name(self):
        # Guide ▸ Getting Started and Installation Guide open the first two in the program: they say no earlier name.
        pattern=name_sweep.NEVER['stacy'][0]
        for name in ('GETTING_STARTED.md','docs/WORKSHOP.md'):
            self.assertEqual([line for line in (ROOT/name).read_text(encoding='utf-8').splitlines() if pattern.search(line)],[],name)
        self.assertIn('Ask Kasandra in her column',(ROOT/'GETTING_STARTED.md').read_text(encoding='utf-8'))      # 1.0 X2: the foot has no Kasandra mode (D1)
        # The owner's guides beside the program say what the window says. A line may still say Stacy where it says what
        # changed (it then says Kasandra too) or points to the legal note (RIGHTS.md keeps Stacy as a name the owner holds).
        for name in ('README.md','docs/DAILY_GUIDE.md','docs/THINKPAD_FIRST_INSTALL.md'):
            lines=[line[:160] for line in (ROOT/name).read_text(encoding='utf-8').splitlines() if pattern.search(line) and 'Kasandra' not in line and 'RIGHTS.md' not in line]
            self.assertEqual(lines,[],name)


class TheWindow(unittest.TestCase):
    def report(self,look):
        out=child(['-m','tests_integrated.test_one_name','--window'],look)
        line=next((l for l in reversed(out.stdout.splitlines()) if l.startswith(MARK)),None)
        self.assertIsNotNone(line,'the window was not swept in %s (exit %s): %s'%(look,out.returncode,(out.stderr or out.stdout)[-3000:]))
        return json.loads(line[len(MARK):])

    def test_no_word_on_screen_says_stacy_in_either_look(self):
        for look in LOOKS:
            with self.subTest(look=look):
                value=self.report(look)
                self.assertEqual((value['look'],value['name']),(look,'Kasandra'))
                self.assertEqual([p['where'] for p in value['places'] if not p['done']],[],'every place of the walk was reached')
                self.assertGreaterEqual(len(value['places']),50);self.assertGreater(value['words'],800,'the sweep read the window')
                for place in ('the right pane: activity','the Log: a brain event pinned','Search: a brain event in its timeline','Guide: About Graphite','Rules: the art plates, none of her'):      # 1.1 T1: no plate of her since 1.0 P4
                    self.assertIn(place,[p['where'] for p in value['places']])
                self.assertGreater(value['named'],20,'her name is read on the desk')
                self.assertEqual(['%s · %s · %s %s: %s'%(f['name'],f['where'],f['widget'],f['kind'],f['words']) for f in value['found']],[])
                for size,row in value['sizes'].items():
                    self.assertEqual(row['window'],[int(n) for n in size.split('x')])
                    self.assertEqual((row['strip'],row['strip_shown']),('Line',True),size)      # 1.0 D1: her name is not at the foot
                    self.assertEqual((row['clipped'],row['clipped_back']),('',''),'%s: her name is whole wherever it is shown'%size)
                    self.assertGreaterEqual(row['said'],1,size)
                    self.assertEqual(row['back'],['‹ Kasandra  ·  Activity',True,''],size)
                    self.assertEqual(row['column'],['Kasandra',True],size)      # 1.0 P1: her column's head, in every look


class History(unittest.TestCase):
    def setUp(self):
        from workbench import ledger_control
        from workbench.engineering_kernel import Kernel,operator
        from workbench.session import Session
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);base=Path(temporary.name)
        root=base/'work';root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(base/'profile'),'ARC_LEDGER_CONCERN':str(base/'Concern')})
        env.start();self.addCleanup(env.stop);self.kernel=Kernel(root);self.owner=operator('owner')
        self.session=Session(base/'profile/session.json',root);self.session.save();ledger_control.bind(self.kernel,self.session)

    def call(self,op,args=None):
        response=self.kernel.dispatch(op,args or {},self.owner);self.assertTrue(response['ok'],response);return response['result']

    def reasons(self):
        view=self.call('agenda.view');return {r['id']:r.get('reason') for part in ('now','next','later','done') for r in view[part] if r.get('id')}

    def test_an_agenda_row_written_under_stacy_reads_back_with_that_name(self):
        from workbench import agenda
        old=self.call('agenda.add',{'title':'What should I check first?'})
        with agenda.opened(self.kernel) as db:      # the row as 0.8.3 left it: waiting for her brain, due again in a while
            db.execute('UPDATE agenda_items SET due=?, reason=? WHERE id=?',(time.time()+3600,OLD_REASON,old['id']))
        self.assertEqual(self.reasons()[old['id']],OLD_REASON)
        new=self.call('agenda.add',{'title':'And what after that?'})
        ran=self.call('agenda.run_next')      # no model here: the item in words waits for her brain, and says so now
        self.assertIsNone(ran.get('ran'),ran)
        reasons=self.reasons()
        self.assertEqual(reasons[new['id']],"Waiting for Kasandra's brain: choose a model in Brain, and she will take it up.")
        self.assertEqual(reasons[old['id']],OLD_REASON,'what was written under Stacy keeps the name it was written with')

    def test_a_brain_event_keeps_its_actor_and_is_read_with_her_name(self):
        # 0.8.4 as first built still read "Stacy · brain.worker" in the Log, in Search's timeline and in Activity: the row's
        # words were made from the stored actor. The record keeps it; the words say her name.
        from workbench import activity,local_brain,log_qt,tail_words
        local_brain.put(self.kernel,'worker',{'model_id':'bench-model'},'READY')      # as the program writes every brain event
        events=[e for e in activity.tail(self.kernel.root)['events'] if e.get('operation')=='brain.worker']
        self.assertEqual([(e['origin'],e['state']) for e in events],[('STACY','READY')],'the record keeps the actor it was written with')
        event=events[0]
        self.assertEqual(tail_words.readable(event),'Kasandra · brain.worker')
        self.assertTrue(log_qt.event_line(event).endswith('  Kasandra · brain.worker'),log_qt.event_line(event))
        rows=dict(log_qt.details({'kind':'event','stream':'events','event':event}))
        self.assertEqual((rows['origin'],rows['operation'],rows['state']),('KASANDRA','brain.worker','READY'))
        self.assertEqual(name_sweep.named_in(tail_words.readable(event)+' '+' '.join('%s %s'%row for row in rows.items())),[])
        # whoever else acted is read as before, and the owner's own acts name nobody
        self.assertEqual(tail_words.readable(activity.make_event('REMOTE','files.write','COMPLETED')),'Remote · Wrote a file')
        self.assertEqual(tail_words.readable(activity.make_event('GUI','files.write','COMPLETED')),'Wrote a file')
        self.assertEqual(tail_words.shown_origin(None),'')

    def test_her_trail_and_the_activity_actor_keep_what_was_written(self):
        # A guard, not a test of the change: it passed before 0.8.4 too. Her trail never carried her name (the row below is
        # an invented shape), and the actor was never rewritten. It holds that nothing rewrites either from now on.
        from workbench import activity,stacy_hand
        from workbench.session import Session
        entry={'at':'2026-11-13 21:04','words':'Stacy wrote “notes.txt” in Files','line':'/files.write {"path":"notes.txt","text":"x"}','undo':'','word':'write notes','state':'done','guard':[]}
        self.session.state[stacy_hand.TRAIL]=[entry];self.session.save()
        again=Session(self.session.path,self.kernel.root)
        self.assertEqual([e['words'] for e in stacy_hand.trail(again.state)],['Stacy wrote “notes.txt” in Files'])
        activity.record(self.kernel.root,'STACY','brain.load','LOADED','as 0.8.3 recorded it')
        events=[e for e in activity.tail(self.kernel.root)['events'] if e.get('operation')=='brain.load']
        self.assertEqual([(e['origin'],e['detail']) for e in events],[('STACY','as 0.8.3 recorded it')])
        from workbench import local_brain
        import inspect
        self.assertIn("'STACY'",inspect.getsource(local_brain),'the actor is still written as it always was: a record, not a shown name')


if __name__=='__main__':
    if sys.argv[1:2]==['--window']:window_report()
    else:unittest.main()
