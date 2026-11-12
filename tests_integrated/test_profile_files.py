"""Files about something (HATCH AGENT-02, WI-C): the second assignment, worked by the resident loop without a model.

A disposable workspace holds a Files folder and an Ingress folder with matching and non-matching files. The request's own words
choose the profile (fits; no model); agent.assign + agent.run work it to DONE through registered operations only: receiving.status,
files.find, ledger.browse (the Ingress listing), files.get (at most four reads, inside Files) and the two document writes.
Nothing here starts a worker, a job, a model or a native tool: Kernel.launch and Kernel.submit are held for every case, and the
model's advice runs only through a patched ask_model / model_answer.
"""
import json,os,re,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from workbench import agent_loop as loop,agent_profiles as profiles,profile_files as pf
from workbench.engineering_kernel import Kernel,operator
from workbench.engineering_cli import schemas

JOB='a'*32
REQUEST='find files about pellets'
ALLOWED={'receiving.status','files.find','ledger.browse','files.get','documents.create','documents.edit'}


class Words(unittest.TestCase):
    def test_fits_and_topic_of_read_explicit_words(self):
        for text,topic in (('find files about pellets','pellets'),('Find files about Pellets.','Pellets'),('what documents do we have on the frame','the frame'),
                           ('which drawings mention the hatch door','the hatch door'),('look for sheets mentioning oyster shell, please','oyster shell'),
                           ('Slate, search files for “grit”','grit'),('show me all the documents about the coop roof?','the coop roof'),
                           ('list drawings named BOM','BOM'),('are there any files about the brooder','the brooder'),('is there a document about pellets for me','pellets'),
                           ('what files do we have about the 2026 feed order','the 2026 feed order'),('do we have any drawings about the hatch door','the hatch door'),
                           ('find anything about the brooder','the brooder'),('search the files for grit','grit'),('search for the document about pellets','pellets'),
                           ('find files about Müller invoices','Müller invoices'),('find files about ñandú','ñandú'),('find files about 鸡蛋','鸡蛋')):
            self.assertEqual(pf.topic_of(text),topic,text);self.assertTrue(pf.fits(text),text);self.assertTrue(pf.PROFILE.fits(text),text)
        for text in ('add up the numbers on this page','write a poem about foxes','find files','find files about','find files about this page',
                     'show me something on this page','what is on this page','find files about it','search for pellets','make these words bold','',None,
                     # pointing at what is open, wherever the words stand: the model path, which is given the page
                     'search this document for pellets','search this sheet for errors','search this drawing for the hatch door','search the document for the word pellet',
                     'search the sheet for totals','find anything on this page about pellets','is there anything about pellets on this sheet',
                     'is there anything about pellets in this file','what documents mention pellets here','which of these documents is about chickens',
                     # everyday questions: “anything” / “something” only after find, look for, search or list, and not with “for”
                     'is there anything about pellets for me','Is there something on my calendar?','Do we have anything for a headache?','Is there anything on TV tonight?',
                     'Can you show me something about Python decorators?','show me something for dinner','find something for dinner','find files about something'):
            self.assertIsNone(pf.topic_of(text),text);self.assertFalse(pf.fits(text),text)
            if text:self.assertNotEqual(loop.request_profile(text),'files_about',text)
        self.assertEqual(len(pf.topic_of('find files about '+'x'*400)),pf.TOPIC_LIMIT)

    def test_request_profile_routes_by_the_profiles_own_words(self):
        self.assertEqual(loop.request_profile(REQUEST),'files_about');self.assertEqual(loop.request_profile('Which drawings mention the hatch door?'),'files_about')
        self.assertEqual(loop.request_profile('add up the numbers on this page'),'numbers_on_page')   # the numbers rule still comes first
        self.assertIsNone(loop.request_profile('write a poem about foxes'));self.assertIsNone(loop.request_profile('find files about this page'))

    def test_needle_and_words_take_plural_endings_off(self):
        self.assertEqual((pf.needle_of('the pellets'),pf.needle_of('Oyster Shells'),pf.needle_of('boxes'),pf.needle_of('batteries'),pf.needle_of('glass'),pf.needle_of('BOM')),
                         ('pellet','oyster shell','box','batter','glass','bom'))
        self.assertEqual(pf.topic_words('the hatch doors'),['hatch','door']);self.assertEqual(pf.longest_word('the hatch doors'),'hatch')
        self.assertTrue(pf.name_matches('Pellets invoice.pdf',['pellet']));self.assertFalse(pf.name_matches('grit receipt.pdf',['pellet']))
        # a word of four letters or fewer stays whole: “new”, “mar”, “len” would match inside almost any name or line
        self.assertEqual([pf.needle_of(w) for w in ('news','Mars','lens','eggs','bolts')],['news','mars','lens','eggs','bolt'])
        # letters of any script are words: “Müller” is not “ller”, so “Keller invoice.pdf” is not a file about Müller invoices
        self.assertEqual(pf.topic_words('Müller invoices'),['müller','invoice']);self.assertFalse(pf.name_matches('Keller invoice.pdf',pf.topic_words('Müller invoices')))
        self.assertTrue(pf.name_matches('Müller invoice.pdf',pf.topic_words('Müller invoices')));self.assertEqual(pf.topic_words('鸡蛋'),['鸡蛋'])

    def test_registered_whichever_module_is_imported_first(self):
        import importlib,sys,workbench
        names=('workbench.agent_profiles','workbench.profile_files','workbench.profile_numbers')
        saved={n:sys.modules[n] for n in names};attrs={n.split('.')[1]:getattr(workbench,n.split('.')[1]) for n in names}
        try:
            for n in names:del sys.modules[n];delattr(workbench,n.split('.')[1])   # a fresh interpreter, as far as these three modules go
            fresh=importlib.import_module('workbench.profile_files');registry=sys.modules['workbench.agent_profiles']   # profile_files first
            self.assertIs(registry.PROFILES['files_about'],fresh.PROFILE);self.assertNotIn('files_about',registry.UNAVAILABLE)
            self.assertIn('numbers_on_page',registry.PROFILES)
        finally:
            sys.modules.update(saved)
            for name,module in attrs.items():setattr(workbench,name,module)
        self.assertIs(profiles.PROFILES['files_about'],pf.PROFILE)

    def test_registered_with_no_needs_and_offered_by_agent_assign(self):
        self.assertIs(profiles.PROFILES['files_about'],pf.PROFILE);self.assertEqual(pf.PROFILE.needs,());self.assertNotIn('files_about',profiles.UNAVAILABLE)
        self.assertIn('files_about',loop.PROFILES);self.assertIn('files_about',schemas()['agent.assign']['properties']['profile']['enum'])
        # the worst case (20 matches, 5 names in Ingress, 4 reads, where, find, the retry, the page and its last line) fits the default budget
        worst=2+1+1+pf.READ_LIMIT+1+pf.FIND_LIMIT+pf.INGRESS_LIMIT+1
        self.assertLessEqual(worst,loop.DEFAULT_BUDGET['max_steps'])


class Assignment(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ledger-files-about-');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(Path(temporary.name)/'profile')});env.start();self.addCleanup(env.stop)
        self.kernel=Kernel(self.root);self.owner=operator('owner')
        for name,words in (('launch','no worker may start'),('submit','no job may be submitted')):
            guard=patch.object(Kernel,name,side_effect=AssertionError(words));guard.start();self.addCleanup(guard.stop)
        from workbench import clip
        provider=patch.object(clip,'_request',side_effect=AssertionError('no provider request'));provider.start();self.addCleanup(provider.stop)
        self.files=self.root/'Files';self.ingress=self.root/'Ingress';(self.files/'Coop').mkdir(parents=True);self.ingress.mkdir()
        old=time.time()-3*86400
        self.put('Coop/pellet_order.md','# Pellet order for November\nTwo bags of layer pellets.\n')
        self.put('feed notes.txt','Grit and oyster shell on Sundays.\nPellets: 12.5 kg a week.\n',old)
        self.put('pellet price.csv','supplier,kg,price\nMill,25,19.50\n')
        self.put('Coop/roof.txt','The coop roof needs new felt.\n')                 # matches nothing
        self.put('Coop/hatch_door_notes.md','Hinges on the left.\n')                # for the word retry
        self.put('Egress/pellets_share.txt','A copy sent out.\n')                      # a copy in Egress: found, ranked last, not read first
        (self.ingress/'Pellets invoice.pdf').write_bytes(b'%PDF-1.4 invoice');(self.ingress/'grit receipt.pdf').write_bytes(b'%PDF-1.4 receipt')
        (self.ingress/'scan.txt').write_text('pellets pellets pellets\n')             # the word is inside, not in the name: Ingress is listed by name only
        (self.ingress/'.pellets-hidden').write_text('x')

    def put(self,rel,text,mtime=None):
        path=self.files/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
        if mtime:os.utime(path,(mtime,mtime))
        return path

    def call(self,op,args=None):
        r=self.kernel.dispatch(op,args or {},self.owner);self.assertTrue(r['ok'],r);return r['result']

    def steps_of(self,investigation):
        with self.kernel.db() as db:
            return [dict(zip(('kind','program','outcome','purpose','summary'),r)) for r in db.execute('SELECT kind,program,outcome,purpose,summary FROM inv_steps WHERE investigation=? ORDER BY seq',(investigation,))]

    def programs(self,investigation):
        return [json.loads(s['program']) for s in self.steps_of(investigation) if s['kind']=='STEP']

    def jobs(self):
        with self.kernel.db() as db:return db.execute('SELECT count(*) FROM jobs').fetchone()[0]

    def assign(self,request=REQUEST,**more):
        out=self.call('agent.assign',{'request':request,**more});return out['assignment']

    def page_of(self,assignment):
        ids=[i['id'] for i in assignment['inspect'] if i['kind']=='document'];self.assertTrue(ids,assignment['inspect'])
        return self.call('documents.get',{'id':ids[-1]})['document']

    def assert_reads_stay_inside_files(self,programs):
        self.assertTrue({p['operation'] for p in programs}<=ALLOWED,{p['operation'] for p in programs})
        for p in programs:
            if p['operation']=='files.get':
                path=(self.files/p['arguments']['path']).resolve();self.assertIn(self.files.resolve(),path.parents)
            if p['operation']=='ledger.browse':self.assertEqual(Path(p['arguments']['path']),self.ingress)
            if p['operation']=='files.find':self.assertNotIn('under',p['arguments'])
        self.assertLessEqual(sum(p['operation']=='files.get' for p in programs),pf.READ_LIMIT)

    def test_the_whole_plan_runs_to_done_without_a_model_and_writes_the_findings_page(self):
        a=self.assign()
        self.assertEqual((a['state'],a['profile'],a['steps_used']),('READY','files_about',0))
        self.assertEqual(self.call('investigation.sheet',{'id':a['investigation']})['objective'],pf.PROFILE.words)
        with patch.object(loop,'ask_model',return_value=None) as asked:   # no model loaded: the default (write the page) is taken
            out=self.call('agent.run',{'id':a['id']})
        row=out['assignment'];self.assertEqual(row['state'],'DONE',row)
        self.assertEqual(row['reason'],'Found 5 files about pellets; the findings page is in Documents');self.assertEqual(row['doing_now'],row['reason'])
        self.assertEqual(asked.call_count,1);self.assertIs(row['model_used'],False)
        keys=[s['key'] for s in out['ran']]
        self.assertEqual(keys[:6],['where','find','ingress','read_1','read_2','write']);self.assertEqual(keys[6:],['lines_%d'%n for n in range(1,7)])
        programs=self.programs(a['investigation']);self.assert_reads_stay_inside_files(programs)
        self.assertEqual(programs[1]['arguments'],{'text':'pellet','limit':pf.FIND_LIMIT})
        self.assertEqual([p['arguments']['path'] for p in programs if p['operation']=='files.get'],['Coop/pellet_order.md','pellet price.csv'])   # name matches, readable first
        choices=[s for s in self.steps_of(a['investigation']) if s['kind']=='CHOICE'];self.assertEqual(len(choices),1)
        self.assertEqual(choices[0]['summary'],'no model loaded; default taken: Write the findings page')
        page=self.page_of(row);texts=[b['text'] for b in page['blocks']]
        self.assertEqual((page['title'],page['revision'],len(texts)),('Files about pellets',7,7))
        self.assertEqual(texts[0],'Request: “find files about pellets” · Graphite searched Files for “pellet”')
        self.assertTrue(texts[1].startswith('pellet_order.md · Files › Coop · ') and 'matched by name' in texts[1] and texts[1].endswith('first line: “# Pellet order for November”'),texts[1])
        self.assertTrue(texts[2].startswith('pellet price.csv · Files · ') and texts[2].endswith('matched by name · Table · columns supplier, kg, price · 1 row'),texts[2])
        self.assertTrue(texts[3].startswith('feed notes.txt · Files · ') and 'matched on line 2: Pellets: 12.5 kg a week.' in texts[3] and 'first line' not in texts[3],texts[3])
        self.assertTrue(texts[4].startswith('pellets_share.txt · Files › Egress · ') and 'matched by name' in texts[4],texts[4])
        self.assertTrue(texts[5].startswith('Pellets invoice.pdf · Ingress · ') and texts[5].endswith('waiting to be received, not read'),texts[5])
        self.assertRegex(texts[6],r'^Looked in Files and Ingress on \d{4}-\d{2}-\d{2} · 5 matches · read 2$')
        self.assertFalse(any('roof' in t or 'grit receipt' in t or 'scan.txt' in t or 'hidden' in t for t in texts),texts)
        found=[f['text'] for f in row['found']]
        self.assertEqual(len(found),4+1+2+1);self.assertEqual(found[-1],'5 files about pellets: 4 in Files, 1 waiting in Ingress; Graphite read the first lines of 2.')
        self.assertIn('First line of pellet_order.md: “# Pellet order for November”',found);self.assertIn('pellet price.csv has no lines to read: Table · columns supplier, kg, price · 1 row',found)
        self.assertEqual(row['needs_you'],[])
        self.assertEqual([i['kind'] for i in row['inspect']],['investigation','document']);self.assertEqual(row['inspect'][1]['id'],page['id'])
        self.assertEqual(self.jobs(),0)

    def test_the_models_advice_reads_more_but_never_more_than_four(self):
        for n in range(4):self.put('Coop/pellet batch %d.txt'%n,'Batch %d of pellets.\n'%n)
        a=self.assign()
        with patch.object(loop,'ask_model',return_value=JOB) as asked,patch.object(loop,'model_answer',return_value={'choice':2,'text':'2','state':'Completed'}):
            out=self.call('agent.run',{'id':a['id']})
        row=out['assignment'];self.assertEqual(row['state'],'DONE',row);self.assertIs(row['model_used'],True)
        programs=self.programs(a['investigation']);self.assert_reads_stay_inside_files(programs)
        self.assertEqual(sum(p['operation']=='files.get' for p in programs),4)   # the model said “read one more” every time; the budget of four held
        model_rows=[s for s in self.steps_of(a['investigation']) if s['kind']=='MODEL_CHOICE'];self.assertEqual(len(model_rows),2);self.assertEqual(asked.call_count,2)
        self.assertTrue(all(s['outcome']=='DONE' for s in model_rows))
        self.assertRegex(self.page_of(row)['blocks'][-1]['text'],r'· 9 matches · read 4$')

    def test_nothing_found_asks_a_question_and_writes_no_page(self):
        a=self.assign('find documents about unicorns')
        with patch.object(loop,'ask_model',side_effect=AssertionError('no choice when nothing matched')):
            row=self.call('agent.run',{'id':a['id']})['assignment']
        self.assertEqual(row['state'],'DONE');self.assertTrue(row['reason'].startswith('Found no files about unicorns in Files or Ingress (looked at '),row['reason'])
        self.assertEqual([n['kind'] for n in row['needs_you']],['QUESTION']);self.assertIn('“unicorn”',row['needs_you'][0]['text'])
        ops=[p['operation'] for p in self.programs(a['investigation'])]
        self.assertEqual(ops,['receiving.status','files.find','ledger.browse']);self.assertEqual([i['kind'] for i in row['inspect']],['investigation'])

    def test_a_match_only_in_ingress_writes_the_page_and_asks_nothing(self):
        a=self.assign('find files about invoices')   # nothing in Files carries “invoice”; Ingress holds “Pellets invoice.pdf”
        with patch.object(loop,'ask_model',side_effect=AssertionError('no choice: nothing in Files to read')):
            row=self.call('agent.run',{'id':a['id']})['assignment']
        self.assertEqual(row['state'],'DONE',row);self.assertEqual(row['reason'],'Found 1 file about invoices; the findings page is in Documents')
        self.assertEqual(row['needs_you'],[])   # the QUESTION waits for Ingress and is not asked when Ingress has the match
        texts=[b['text'] for b in self.page_of(row)['blocks']]
        self.assertTrue(texts[1].startswith('Pellets invoice.pdf · Ingress · ') and texts[1].endswith('waiting to be received, not read'),texts)
        self.assertRegex(texts[-1],r'· 1 match · read 0$')
        self.assertEqual([p['operation'] for p in self.programs(a['investigation'])][:3],['receiving.status','files.find','ledger.browse'])

    def test_nothing_in_files_and_ingress_not_listed_still_asks_the_question(self):
        import shutil
        a=self.assign('find documents about unicorns')
        with patch.object(loop,'ask_model',side_effect=AssertionError('no choice when nothing matched')):
            keys=[self.call('agent.step',{'id':a['id']})['step']['key'] for _ in range(2)];self.assertEqual(keys,['where','find'])
            self.assertEqual(self.call('agent.status',{'id':a['id']})['assignments'][0]['needs_you'],[])   # held back while Ingress is to be listed
            shutil.rmtree(self.ingress)                                                                     # the listing fails
            out=self.call('agent.step',{'id':a['id']})
        self.assertEqual((out['step']['key'],out['step']['outcome'],out['assignment']['state']),('ingress','FAILED','WAITING'))
        needs=[n for n in out['assignment']['needs_you'] if n['kind']=='QUESTION'];self.assertEqual(len(needs),1);self.assertIn('“unicorn”',needs[0]['text'])
        self.assertTrue(out['assignment']['reason'].startswith('Ingress could not be listed'),out['assignment']['reason'])

    def test_a_short_word_is_searched_whole(self):
        a=self.assign('find files about news')   # the roof note says “needs new felt”: “new” must not count as news
        with patch.object(loop,'ask_model',side_effect=AssertionError('no choice when nothing matched')):
            row=self.call('agent.run',{'id':a['id']})['assignment']
        self.assertEqual(row['state'],'DONE');self.assertTrue(row['reason'].startswith('Found no files about news in Files or Ingress'),row['reason'])
        self.assertEqual([p['arguments']['text'] for p in self.programs(a['investigation']) if p['operation']=='files.find'],['news'])

    def test_a_topic_of_several_words_is_searched_again_by_its_longest_word(self):
        a=self.assign('which documents mention the hatch doors?')
        with patch.object(loop,'ask_model',return_value=None):row=self.call('agent.run',{'id':a['id']})['assignment']
        self.assertEqual(row['state'],'DONE',row);self.assertEqual(row['reason'],'Found 1 file about the hatch doors; the findings page is in Documents')
        finds=[p['arguments']['text'] for p in self.programs(a['investigation']) if p['operation']=='files.find'];self.assertEqual(finds,['hatch door','hatch'])
        texts=[b['text'] for b in self.page_of(row)['blocks']]
        self.assertEqual(texts[0],'Request: “which documents mention the hatch doors?” · Graphite searched Files for “hatch door”, then “hatch”')
        self.assertTrue(texts[1].startswith('hatch_door_notes.md · Files › Coop') and 'matched “hatch” by name' in texts[1],texts[1])

    def test_no_ingress_listing_when_ingress_holds_nothing(self):
        for p in self.ingress.iterdir():p.unlink()
        a=self.assign()
        with patch.object(loop,'ask_model',return_value=None):row=self.call('agent.run',{'id':a['id']})['assignment']
        self.assertEqual(row['state'],'DONE');ops=[p['operation'] for p in self.programs(a['investigation'])]
        self.assertNotIn('ledger.browse',ops);self.assertRegex(self.page_of(row)['blocks'][-1]['text'],r'^Looked in Files and Ingress on .* · 4 matches · read 2$')

    def test_a_findings_page_that_moved_on_is_never_merged_resume_writes_a_fresh_page(self):
        a=self.assign()
        with patch.object(loop,'ask_model',return_value=None):
            for _ in range(20):
                out=self.call('agent.step',{'id':a['id']})
                if out['step'] and out['step']['key']=='lines_1':break
            else:self.fail('the first line was never written: %s'%out['assignment'])
            first=self.page_of(out['assignment'])
            self.call('documents.edit',{'id':first['id'],'expected_revision':first['revision'],'selection':{'block':0,'start':0,'end':0},'change':{'append':'The owner wrote here.'},'origin':'HUMAN'})
            out=self.call('agent.step',{'id':a['id']})
            self.assertEqual((out['assignment']['state'],out['step']['outcome']),('WAITING','FAILED'));self.assertEqual(out['assignment']['reason'],pf.PAGE_MOVED)
            self.assertEqual(self.call('agent.resume',{'id':a['id']})['assignment']['state'],'READY')
            row=self.call('agent.run',{'id':a['id']})['assignment']
        self.assertEqual(row['state'],'DONE',row);pages=[i['id'] for i in row['inspect'] if i['kind']=='document'];self.assertEqual(len(pages),2)
        self.assertEqual(pages[1],first['id'])   # inspect lists the page Slate wrote last first, then the earlier one
        kept=self.call('documents.get',{'id':first['id']})['document'];kept_texts=[b['text'] for b in kept['blocks']]
        self.assertIn('The owner wrote here.',kept_texts);self.assertEqual(kept['revision'],3)   # nothing Slate wrote after the owner's edit
        fresh=self.call('documents.get',{'id':pages[0]})['document'];self.assertEqual(len(fresh['blocks']),7);self.assertNotIn('The owner wrote here.',[b['text'] for b in fresh['blocks']])

    def test_a_read_only_budget_finds_and_reads_but_does_not_write(self):
        a=self.assign(budget={'effects':'read'})
        with patch.object(loop,'ask_model',return_value=None):row=self.call('agent.run',{'id':a['id']})['assignment']
        self.assertEqual(row['state'],'WAITING');self.assertTrue(row['reason'].startswith('Step write (Starting the findings page) did not run: '),row['reason'])
        self.assertEqual(sum(p['operation']=='files.get' for p in self.programs(a['investigation'])),2)
        self.assertEqual(self.call('documents.list')['documents'],[])

    def test_assign_from_page_takes_a_files_request_with_no_page_open(self):
        from workbench import agent_qt
        class Driver:
            def __init__(self):self.started=[]
            def start(self,ident):self.started.append(ident);return True
        class Page:
            document_id='b'*32
            def __init__(self):self.flushed=0
            def flush(self):self.flushed+=1;return True
        driver=Driver();host=SimpleNamespace(agent_driver=driver);sent=[]
        def write(h,op,args):
            sent.append((op,args));r=self.kernel.dispatch(op,args,self.owner);self.assertTrue(r['ok'],r);return r
        with patch.object(agent_qt,'call_write',side_effect=write):
            answer=agent_qt.assign_from_page(host,None,REQUEST)                       # no tab at all
            self.assertEqual(answer,agent_qt.WORKING_ANSWER%REQUEST)
            page=Page();agent_qt.assign_from_page(host,page,'what documents do we have on the frame')   # on a page: still context {}, the page is not flushed
            self.assertIsNone(agent_qt.assign_from_page(host,page,'search this document for pellets'))   # the open page: the model path, which is given it
            self.assertIsNone(agent_qt.assign_from_page(host,None,'add up the numbers on this page'))   # the numbers profile still needs a page
            self.assertIsNone(agent_qt.assign_from_page(host,None,'write a poem about foxes'))
        self.assertEqual([(op,args['profile'],args['context']) for op,args in sent],[('agent.assign','files_about',{}),('agent.assign','files_about',{})])
        self.assertEqual(page.flushed,0);self.assertEqual(len(driver.started),2)
        rows=self.call('agent.list')['assignments'];self.assertEqual({r['state'] for r in rows},{'READY'});self.assertEqual({r['profile'] for r in rows},{'files_about'})


if __name__=='__main__':unittest.main()
