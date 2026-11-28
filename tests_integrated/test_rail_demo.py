"""0.8.4: Rail Demo (workbench/rail_demo.py), the workspace of invented data kept in the program.

Scenes, campaign cases and tests used to stand on the owner's own workspace, restored from a backup that is never shipped,
so wherever the backup was not they did not run. Rail Demo has the same shape and is built by the program itself, through
the Kernel's own operations: a 12 V rail on a bench, its readings in a PDF that was admitted and reviewed into a sheet, two
revisions of its limits, two exact calculations, four findings bound to what they rest on, a page and an open question.
Every number in it is invented, and it says so.

Here: the sources are the same bytes every time; a workspace built by rail_demo.workspace() holds every record and every
link, each read back through Graphite's operations; nothing of it is outside the folder it was given; it is built through
Kernel.dispatch alone; the campaign finds its records by what each is, past more intake rows than one list gives and past
a calculation it cannot read, and A01 tells the sheet's own record of its source from the hash its PDF was admitted with;
changing the settled current from 250 mA to 300 mA gives 3.6 W exactly and sends what rests on it to
recheck while the reviewed source keeps its reading; and the playable scene P01 is played on it on the live window, by
pointer and by keys, each again with less motion, in the look this module was started in (run it once more with
GRAPHITE_APPEARANCE=kasandra for the other; tests_integrated.test_rail_demo_campaign plays it in both from one run).

  python -B -m unittest -v tests_integrated.test_rail_demo
"""
import collections,hashlib,json,os,tempfile,time,traceback,unittest
from pathlib import Path
from unittest.mock import NonCallableMock,patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from tests_integrated.test_desk_acts import P01,build_window,close_window,settle
from tests_integrated.seed_hold import seed_bound
from workbench import rail_demo

# The three sources as the program writes them (rail_demo.REVISION 2). A source changed on purpose changes its line here and
# the revision with it; a line that changes by itself means the sources are no longer the same bytes every time.
SOURCE_SHA256={'readings':'883346624682ddd87b8779b8c0176689d6481c615a340108aa2c5859bb8356c1',
               'limits_a':'34a9b7e3028c1945645664894ceab4e3d4202daac236b2dfbc54884ad3fb358e',
               'limits_b':'53afd3d8d9beaa672b0ff41969dae647c43a1ff3c415776b1d4a2010c63cba1c'}
READINGS,REV_A,REV_B='Rail Demo bench readings','Rail Demo limits Rev A ARCHIVED','Rail Demo limits Rev B CURRENT'
PDF,PDF_A,PDF_B='Rail_Demo_Bench_Readings.pdf','Rail_Demo_Limits_Rev_A.pdf','Rail_Demo_Limits_Rev_B.pdf'
SETTLED,STARTUP='Rail Demo settled power · 3 W','Rail Demo startup power · 10.8 W'
HOLDS='Settled power is 3 W, inside the Rev B limit of 4 W.'
DOES_NOT_HOLD='Startup is inside the Rev B limit of 40 ms.'
CHANGED='The startup limit was 60 ms in Rev A and is 40 ms in Rev B.'
KEEPS='The Rev B sheet carries the 40 ms startup limit.'
OPEN='Why does startup take longer than 40 ms?'
DESK='Rail Demo (invented data)'
# kind, title, state, role, facts, where: everything on the desk, as field.read gives it
OBJECTS={('source',PDF,'current','admitted source',(),'Rail Demo sources'),
         ('source',PDF_A,'current','admitted source',(),'Rail Demo sources'),
         ('source',PDF_B,'current','admitted source',(),'Rail Demo sources'),
         ('sheet',READINGS,'current','reviewed sheet',('reviewed from page 1','version 1'),PDF),
         ('sheet',REV_A,'current','reviewed sheet',('reviewed from page 1','version 1'),PDF_A),
         ('sheet',REV_B,'current','reviewed sheet',('reviewed from page 1','version 1'),PDF_B),
         ('calculation',SETTLED,'current','exact result',('cells B2, B3','revision 2'),READINGS),
         ('calculation',STARTUP,'current','exact result',('cells B2, B4','revision 2'),READINGS),
         ('document','Rail Demo summary','','page',('revision 1',),''),
         ('finding',HOLDS,'current','from '+DESK,('supported',),DESK),
         ('finding',DOES_NOT_HOLD,'refuted','from '+DESK,('the evidence speaks against it',),DESK),
         ('finding',CHANGED,'current','from '+DESK,('supported',),DESK),
         ('finding',KEEPS,'current','from '+DESK,('supported',),DESK),
         ('question',OPEN,'open','from '+DESK,(),DESK)}
# from, to, the wire's words: every link on the desk
LINKS={(PDF,READINGS,'page 1'),(PDF_A,REV_A,'page 1'),(PDF_B,REV_B,'page 1'),
       (READINGS,SETTLED,'cells B2, B3'),(READINGS,STARTUP,'cells B2, B4'),
       (PDF,HOLDS,'supports'),(PDF_B,HOLDS,'supports'),
       (PDF,DOES_NOT_HOLD,'opposes'),(READINGS,DOES_NOT_HOLD,'did not hold'),
       (PDF_A,CHANGED,'supports'),(PDF_B,CHANGED,'supports'),
       (REV_B,KEEPS,'check passed')}
COUNTS=['3 sources','3 sheets','2 calculations','1 page','4 findings','1 open question']
CSV='Rail Demo bench readings.csv'      # what the scene writes in Files on Rail Demo, and takes back
CSV_TEXT='parameter,value,unit\nRail voltage,12,V\nSettled current,250,mA\nStartup current,900,mA\nStartup duration,45,ms\n'
# What build() asks of the Kernel that changes the workspace, and how often: the doors a person uses, in the order a person
# would (put the sources in Files, bring them in, admit each, index them, open each page, review its table into a sheet,
# calculate twice and name the result, write a page, open the investigation, add its sources, findings, evidence and
# checks, the question, run the checks, leave a note on the readings).
WRITES={'files.write':3,'intake.namespace.create':1,'intake.import':1,'intake.decide':3,'references.index':1,'references.pdf.page':3,
        'office.datasheet.create':3,'office.datasheet.report':2,'documents.save':2,'documents.create':1,'investigation.create':1,
        'investigation.add_source':3,'investigation.claim':5,'investigation.evidence':5,'investigation.check':2,'investigation.continue':1,
        'references.pdf.annotation.save':1}
READS={'intake.namespaces','files.list','jobs.get','intake.items','intake.item','office.datasheet.preview','office.get','office.list',
       'documents.list','documents.get','investigation.list','investigation.sheet'}
WINDOW={}


class Watched:
    """rail_demo.build with a watch on the Kernel while it runs: the operations build() itself called, in order, and every
    time the Kernel's database was opened from outside an operation or a job (never, when it is built through the doors)."""

    def __init__(self):
        self.build=rail_demo.build;self.operations=[];self.outside=[];self.depth=0

    def __call__(self,kernel,principal):
        from workbench.engineering_kernel import Kernel
        real={name:getattr(Kernel,name) for name in ('dispatch','run_job','db')}

        def inside(name):
            def call(k,*a,**kw):
                if name=='dispatch' and not self.depth:self.operations.append(a[0])
                self.depth+=1
                try:return real[name](k,*a,**kw)
                finally:self.depth-=1
            return call

        def db(k,*a,**kw):
            if not self.depth:self.outside.append(''.join(traceback.format_stack(limit=3)))
            return real['db'](k,*a,**kw)
        with patch.object(Kernel,'dispatch',inside('dispatch')),patch.object(Kernel,'run_job',inside('run_job')),patch.object(Kernel,'db',db):
            return self.build(kernel,principal)


class Workspace:
    """Rail Demo in a temporary folder of its own (rail_demo.workspace), and the environment put back afterwards."""

    def __init__(self,prefix):
        self.temporary=tempfile.TemporaryDirectory(prefix=prefix);self.base=Path(self.temporary.name)
        self.env=patch.dict(os.environ);self.env.start();self.watched=Watched()
        self.seed=seed_bound();self.seed.start()
        try:
            with patch.object(rail_demo,'build',self.watched):self.k,self.p,self.made=rail_demo.workspace(self.base)
        except BaseException:
            self.close();raise

    def call(self,operation,arguments=None):
        answer=self.k.dispatch(operation,arguments or {},self.p)
        assert answer['ok'],(operation,answer)
        return answer['result']

    def desk(self):
        """The desk as field.read gives it: (objects by title, the set of objects, the set of links by title, the read)."""
        field=self.call('field.read')
        return {o['title']:o for o in field['objects']},pictured(field)[0],pictured(field)[1],field

    def close(self):
        self.seed.stop();self.env.stop();self.temporary.cleanup()


class Elsewhere:
    """The workspace's kernel answering as a restored backup might: more intake rows than one list gives (invented, and
    listed before the PDF), calculations on the desk that cannot be read (an invented one, or one of Rail Demo's), or the
    sheet's own record of its source's SHA-256 other than the hash its PDF was admitted with. Reads only."""

    def __init__(self,kernel,more_items=0,unreadable=(),sheet_sha=None):
        self.kernel,self.more_items,self.unreadable,self.sheet_sha=kernel,more_items,set(unreadable),sheet_sha

    def dispatch(self,operation,arguments,principal):
        if operation=='documents.get' and 'document:'+arguments['id'] in self.unreadable:
            return {'ok':False,'error':{'code':'DOCUMENT_NOT_READABLE','message':'DOCUMENT_NOT_READABLE'}}
        if operation=='intake.items' and self.more_items:
            real=self.kernel.dispatch(operation,dict(arguments,limit=200,offset=0),principal)['result']['items']
            rows=[{'id':'invented-%03d'%n,'name':'A note %03d.txt'%n,'sha256':''} for n in range(self.more_items)]+real
            offset=arguments.get('offset',0)
            return {'ok':True,'result':{'total':len(rows),'items':rows[offset:offset+arguments.get('limit',100)]}}
        answer=self.kernel.dispatch(operation,arguments,principal)
        if operation=='field.read' and answer['ok']:
            answer=json.loads(json.dumps(answer))
            on_desk={o['id'] for o in answer['result']['objects']}
            answer['result']['objects']+=[{'id':ident,'kind':'calculation','title':'Another calculation · 1 W'} for ident in sorted(self.unreadable-on_desk)]
        if operation=='office.get' and answer['ok'] and self.sheet_sha:
            answer=json.loads(json.dumps(answer));answer['result']['source_state']['source_sha256']=self.sheet_sha
        return answer


def pictured(field):
    """What a read of the desk holds, without ids and times: (the set of objects, the set of links by title)."""
    return ({(o['kind'],o['title'],o['state'],o['role'],tuple(o['facts']),o['where']) for o in field['objects']},
            {(l['from'],l['to'],l['label']) for l in field['links']})


class TheSources(unittest.TestCase):
    """No workspace: the three PDFs are written by the program, the same bytes every time, and say what they are."""

    def test_the_sources_are_the_same_bytes_every_time(self):
        first,second=rail_demo.sources(),rail_demo.sources()
        self.assertEqual(list(first),['readings','limits_a','limits_b'])
        for key,item in first.items():
            self.assertEqual(item['bytes'],second[key]['bytes'],key)
            self.assertEqual(item['sha256'],hashlib.sha256(item['bytes']).hexdigest(),key)
        self.assertEqual(rail_demo.REVISION,2,'a new revision: bring SOURCE_SHA256 up to date with it')
        self.assertEqual({key:item['sha256'] for key,item in first.items()},SOURCE_SHA256)

    def test_every_source_says_it_is_invented_and_carries_the_rail_demo_name(self):
        self.assertEqual(rail_demo.NAME,'Rail Demo')
        self.assertEqual(rail_demo.NOTICE,'Invented demonstration data. Nothing here was measured.')
        for key,item in rail_demo.sources().items():
            self.assertTrue(item['bytes'].startswith(b'%PDF-1.4\n') and item['bytes'].endswith(b'%%EOF\n'),key)
            self.assertIn(rail_demo.NOTICE.encode('ascii'),item['bytes'],key)
            self.assertIn(b'(Rail Demo: ',item['bytes'],key)
            self.assertTrue(item['name'].startswith('Rail_Demo_') and item['title'].startswith('Rail Demo '),key)
        self.assertIn('invented data',rail_demo.QUESTION)
        self.assertIn(rail_demo.NOTICE,rail_demo.PAGE_TEXT);self.assertIn(rail_demo.NOTICE,rail_demo.NOTE)

    def test_the_readings_are_the_ones_the_calculations_need(self):
        rows={row[0]:row[1:3] for row in rail_demo.READINGS}
        self.assertEqual(rows,{'Rail voltage':('12','V'),'Settled current':('250','mA'),'Startup current':('900','mA'),'Startup duration':('45','ms')})
        self.assertEqual({row[0]:row[1:3] for row in rail_demo.LIMITS_A},{'Settled power limit':('5','W'),'Startup duration limit':('60','ms'),'Startup power ceiling':('12','W'),'Nominal voltage':('12','V')})
        self.assertEqual({row[0]:row[1:3] for row in rail_demo.LIMITS_B},{'Settled power limit':('4','W'),'Startup duration limit':('40','ms'),'Startup power ceiling':('12','W'),'Nominal voltage':('12','V')})

    def test_what_is_missing_is_said_in_a_sentence_and_nothing_is_built(self):
        self.assertEqual(rail_demo.available(),'')
        with patch.object(rail_demo.shutil,'which',return_value=None):
            why=rail_demo.available()
            self.assertIn('Poppler',why);self.assertIn('pdftotext and pdftoppm not found',why)
            with self.assertRaises(rail_demo.Unavailable) as refused:rail_demo.build(None,None)      # nothing is touched: no Kernel is needed to say so
            self.assertEqual(str(refused.exception),why)

    def test_the_builder_reaches_the_workspace_through_the_kernels_operations_only(self):
        source=Path(rail_demo.__file__).read_text(encoding='utf-8')
        for direct in ('.db(','.save(','sqlite','.execute(','write_bytes','write_text'):self.assertNotIn(direct,source,direct)
        self.assertEqual(source.count('.dispatch('),1,'one place calls the Kernel: _Desk.call')
        self.assertEqual(source.count('.run_job('),1,'and one runs a job the Kernel was given through its own operation')


class StandIn:
    """A Kernel as far as a job of the build knows one: an operation that queues a job and hands it to launch, the runner
    (which waits while the job is not admitted, as the Kernel's does), jobs.get and jobs.cancel. Anything else is refused."""

    def __init__(self,admitted=True):
        self.admitted=admitted;self.jobs={};self.ran=[];self.asked=[]

    def launch(self,ident):
        raise AssertionError('No worker launch')

    def dispatch(self,operation,arguments,principal):
        self.asked.append(operation)
        if operation=='work.start':
            self.jobs['j1']={'id':'j1','tool':'work.tool','state':'Queued','current_operation':'Waiting for shared-memory headroom'}
            self.launch('j1');return {'ok':True,'result':{'id':'j1'}}
        if operation not in ('jobs.get','jobs.cancel'):return {'ok':False,'error':{'message':'no such thing here'}}
        job=self.jobs[arguments['id']]
        if operation=='jobs.cancel' and job['state']=='Queued':job['state']='Cancelled'
        return {'ok':True,'result':dict(job)}

    def run_job(self,ident):
        self.ran.append(ident);job=self.jobs[ident]
        while not self.admitted and job['state']=='Queued':time.sleep(.02)
        if job['state']=='Queued':job['state']='Completed'


class WhatStopsIt(unittest.TestCase):
    """What a build, a read or a change says when it cannot go on, and what it leaves behind."""

    def test_a_job_of_the_build_runs_here_and_puts_back_the_hold_it_found_on_the_kernel(self):
        k=StandIn();hold=lambda ident:self.fail('the hold was asked to start %s'%ident);k.launch=hold
        done=rail_demo._Desk(k,None).job('work.start',{})
        self.assertEqual((done['state'],k.ran),('Completed',['j1']))
        self.assertIs(vars(k).get('launch'),hold,'the hold the caller had put on this Kernel is still on it')
        bare=StandIn();rail_demo._Desk(bare,None).job('work.start',{})
        self.assertNotIn('launch',vars(bare),'and a Kernel that had none has none')

    def test_a_job_that_is_not_started_in_time_is_cancelled_and_the_build_says_what_it_waited_for(self):
        k=StandIn(admitted=False);started=time.monotonic()
        with patch.object(rail_demo,'JOB_WAIT',.3),self.assertRaises(rail_demo.Unavailable) as stopped:rail_demo._Desk(k,None).job('work.start',{})
        self.assertEqual(str(stopped.exception),'Rail Demo could not be built: the work.tool job was not started in 0.3 s (Waiting for shared-memory headroom).')
        self.assertEqual(k.jobs['j1']['state'],'Cancelled','cancelled through its own operation: nothing is left waiting')
        self.assertLess(time.monotonic()-started,10)
        self.assertNotIn('launch',vars(k))

    def test_a_build_that_graphite_does_not_admit_for_want_of_memory_stops_with_the_reason(self):
        # the real Kernel, on a host that says 600 MiB is free (as with a large model loaded): its runner waits for memory
        from workbench import brain_runtime
        from workbench.engineering_kernel import operator
        real=brain_runtime.host

        def short(*a,**kw):
            host=dict(real(*a,**kw))
            for key in host:
                if 'avail' in key and type(host[key]) is int:host[key]=600*1024*1024
            return host
        with tempfile.TemporaryDirectory(prefix='graphite-rail-demo-no-memory-') as folder,patch.dict(os.environ),patch.object(brain_runtime,'host',short),patch.object(rail_demo,'JOB_WAIT',2):
            started=time.monotonic()
            with self.assertRaisesRegex(rail_demo.Unavailable,r'^Rail Demo could not be built: the [a-z.]+ job was not started in 2 s \(Waiting for shared-memory headroom\)\.$'):
                rail_demo.workspace(Path(folder))
            self.assertLess(time.monotonic()-started,30)
            from workbench.engineering_kernel import Kernel
            from workbench.locations import office
            jobs=Kernel(office(Path(folder)/'workspace')).dispatch('jobs.list',{},operator())['result']
            rows=jobs if isinstance(jobs,list) else jobs.get('jobs') or []
            self.assertTrue(rows);self.assertEqual({j['state'] for j in rows},{'Cancelled'},'nothing is left queued or running behind the build')

    def test_a_refusal_says_what_was_being_done(self):
        k=StandIn()
        with self.assertRaises(rail_demo.Unavailable) as refused:rail_demo.find(k,None)
        self.assertEqual(str(refused.exception),'Rail Demo could not be read: intake.namespaces was refused (no such thing here).')
        with self.assertRaises(rail_demo.Unavailable) as refused:rail_demo._Desk(k,None).call('files.write')
        self.assertEqual(str(refused.exception),'Rail Demo could not be built: files.write was refused (no such thing here).')

    def test_a_window_whose_seed_cannot_be_made_leaves_nothing_behind(self):
        from workbench.engineering_kernel import Kernel
        before=dict(os.environ)
        for early in (True,False):
            store={};seen=[]

            def broken(k,p):
                seen.append(Path(k.dispatch('files.list',{},p)['result']['root']));self.assertTrue(seen[0].exists())
                self.assertIs(isinstance(Kernel.submit,NonCallableMock),not early,'the holds are in place for a seed that is not early')
                raise rail_demo.Unavailable('this seed cannot be made')
            with self.assertRaisesRegex(rail_demo.Unavailable,'this seed cannot be made'):build_window(store,'graphite-rail-demo-no-seed-',seed=broken,early=early)
            self.assertEqual(store,{},early);self.assertEqual(dict(os.environ),before,early)
            self.assertFalse(seen[0].exists(),'the folder it was made in is gone')
            self.assertNotIsInstance(Kernel.submit,NonCallableMock,'no hold is left in place')
            self.assertNotIsInstance(Kernel.launch,NonCallableMock)


class TheRecords(unittest.TestCase):
    """One workspace, read only: every record and every link, read back through Graphite's operations."""

    @classmethod
    def setUpClass(cls):
        cls.ws=Workspace('graphite-rail-demo-records-')

    @classmethod
    def tearDownClass(cls):
        cls.ws.close()

    def test_the_desk_holds_every_record_and_every_link(self):
        by_title,objects,links,field=self.ws.desk()
        self.assertEqual(objects,OBJECTS)
        self.assertEqual(len(field['objects']),14,'no title twice')
        self.assertEqual(links,LINKS)
        self.assertEqual(len(field['links']),12)
        self.assertEqual({link['stale'] for link in field['links']},{'no'})
        ids={o['id'] for o in field['objects']}
        self.assertTrue(all(link['source'] in ids and link['target'] in ids for link in field['links']),'every link joins two things on the desk')
        self.assertEqual([c for c in field['counts'] if 'lately' not in c],COUNTS)
        self.assertTrue(field['title'].startswith(DESK),field['title'])
        self.assertEqual([w['title'] for w in field['waiting']],[OPEN])
        self.assertEqual((field['moved'],field['could_not_read']),([],''))

    def test_it_was_built_through_the_kernels_operations_the_doors_a_person_uses(self):
        watched=self.ws.watched
        self.assertEqual(watched.outside,[],'the Kernel\'s database was opened from outside an operation')
        self.assertEqual(set(watched.operations)-READS-set(WRITES),set(),'an operation this test does not know')
        self.assertEqual(dict(collections.Counter(op for op in watched.operations if op not in READS)),WRITES)
        writes=[op for op in watched.operations if op in WRITES]
        self.assertEqual(writes[:3],['files.write']*3);self.assertEqual(writes[-1],'references.pdf.annotation.save')
        self.assertLess(writes.index('intake.import'),writes.index('intake.decide'));self.assertLess(writes.index('intake.decide'),writes.index('references.pdf.page'))
        self.assertLess(writes.index('office.datasheet.create'),writes.index('office.datasheet.report'))

    def test_everything_on_the_desk_is_named_as_rail_demo_or_stands_under_its_title(self):
        by_title,objects,links,field=self.ws.desk()
        for kind,title,state,role,facts,where in objects:
            if kind in ('finding','question'):self.assertEqual(where,DESK,title)
            else:self.assertTrue(title.startswith(('Rail Demo ','Rail_Demo_')),title)

    def test_the_campaign_finds_the_same_records_by_what_each_is(self):
        # 0.8.5: the anchor cases write no record id of the owner's: they find what they work on by kind and words
        # (cases_anchor.found), on the owner's backup as here; here it finds what build() made
        from tools.campaign_lib import cases_anchor
        made=self.ws.made
        self.assertEqual(cases_anchor.found(self.ws.k,self.ws.p),
                         {'sheet':made['sheets']['readings'],'calc_settled':made['calculations']['settled_power'],'calc_startup':made['calculations']['startup_power'],
                          'claim_settled':made['findings']['settled_holds'],'pdf_item':made['sources']['readings']['item'],'pdf_sha256':made['sources']['readings']['sha256']})

    def test_the_campaign_finds_them_past_one_list_and_past_a_calculation_it_cannot_read(self):
        # 0.8.5: found() asks the intake rows a page at a time, and passes over a calculation it cannot read, naming it when
        # what it looks for is then not there
        from tools.campaign_lib import cases_anchor
        want=cases_anchor.found(self.ws.k,self.ws.p)
        for what,elsewhere in (('more intake rows than one list gives',Elsewhere(self.ws.k,more_items=101)),
                               ('a calculation it cannot read',Elsewhere(self.ws.k,unreadable=['document:unread']))):
            with self.subTest(what):
                self.assertEqual(cases_anchor.found(elsewhere,self.ws.p),want)
        with self.assertRaises(LookupError) as refused:
            cases_anchor.found(Elsewhere(self.ws.k,unreadable=['document:'+want['calc_settled']]),self.ws.p)
        self.assertEqual(str(refused.exception),'The restored workspace holds no standing calculation of that sheet\'s B2 and B3 (settled power) '
                                                '(1 calculation could not be read: %s).'%SETTLED)

    def test_a01_says_whether_the_sheets_source_is_the_admitted_pdf_and_keeps_no_hash(self):
        # 0.8.5: the sheet's own record of its source is compared with the hash the PDF was admitted with (its intake row),
        # never with itself; neither hash is kept as an observation; what found() reads is logged with the case's own calls
        from tools.campaign_lib import cases_anchor,core,runner
        case=runner.registry()['DA01']
        for sheet_sha,admitted in ((None,True),('0'*64,False)):
            with tempfile.TemporaryDirectory(prefix='graphite-rail-demo-a01-') as folder:
                ctx=core.Attempt(case,folder,1);ctx.kernel,ctx.owner=Elsewhere(self.ws.k,sheet_sha=sheet_sha),self.ws.p
                case.fn(ctx)
                self.assertIs(ctx.observed['pdf_source_is_the_admitted_one'],admitted,sheet_sha)
                self.assertEqual(sorted(ctx.observed),sorted(case.expect),'nothing observed beyond the checks')
                ops=[line['op'] for line in map(json.loads,(Path(folder)/'progress.jsonl').read_text().splitlines()) if line['step']=='op']
                self.assertTrue(set(cases_anchor.FINDS)<=set(ops),ops)
                self.assertEqual(set(ops)-set(case.allowed),set(),'every read is one the case allows')
        self.assertEqual(runner.registry()['A01'].allowed,case.allowed)

    def test_build_returns_what_find_reads_back(self):
        made=self.ws.made
        self.assertEqual(made,rail_demo.find(self.ws.k,self.ws.p))
        self.assertEqual((made['name'],made['notice'],made['revision']),('Rail Demo',rail_demo.NOTICE,rail_demo.REVISION))
        self.assertEqual({key:(source['name'],source['sha256']) for key,source in made['sources'].items()},
                         {'readings':(PDF,SOURCE_SHA256['readings']),'limits_a':(PDF_A,SOURCE_SHA256['limits_a']),'limits_b':(PDF_B,SOURCE_SHA256['limits_b'])})
        by_title=self.ws.desk()[0]
        self.assertEqual({key:'office:'+ident for key,ident in made['sheets'].items()},{'readings':by_title[READINGS]['id'],'limits_a':by_title[REV_A]['id'],'limits_b':by_title[REV_B]['id']})
        self.assertEqual({key:'document:'+ident for key,ident in made['calculations'].items()},{'settled_power':by_title[SETTLED]['id'],'startup_power':by_title[STARTUP]['id']})
        self.assertEqual({key:'claim:'+ident for key,ident in made['findings'].items()},
                         {'settled_holds':by_title[HOLDS]['id'],'startup_holds':by_title[DOES_NOT_HOLD]['id'],'limit_changed':by_title[CHANGED]['id'],'sheet_keeps':by_title[KEEPS]['id']})
        self.assertEqual('claim:'+made['question'],by_title[OPEN]['id'])
        self.assertEqual('document:'+made['page'],by_title['Rail Demo summary']['id'])

    def test_the_sources_were_put_in_files_brought_in_and_admitted_as_written(self):
        made=self.ws.made
        listed=self.ws.call('files.list',{'path':'Rail Demo sources'})
        self.assertEqual(sorted(e['name'] for e in listed['entries']),[PDF,PDF_A,PDF_B])
        for key,source in made['sources'].items():
            on_disk=Path(listed['root'])/'Rail Demo sources'/source['name']
            self.assertEqual(hashlib.sha256(on_disk.read_bytes()).hexdigest(),SOURCE_SHA256[key],key)
            item=self.ws.call('intake.item',{'id':source['item']})
            self.assertEqual(item['sha256'],SOURCE_SHA256[key],key)
            self.assertEqual((item['name'],item['admission'],item['profile']),(source['name'],'ACCEPTED','pdf_document'),key)
        spaces=[s for s in self.ws.call('intake.namespaces')['namespaces'] if s['name']=='Rail Demo sources']
        self.assertEqual([s['id'] for s in spaces],[made['collection']])
        self.assertEqual(len(self.ws.call('intake.items',{'namespace':made['collection']})['items']),3)

    def test_the_readings_sheet_is_the_reviewed_table_of_its_source(self):
        made=self.ws.made;sheet=self.ws.call('office.get',{'id':made['sheets']['readings']})
        cells=sheet['document']['sheets'][0]['cells']
        self.assertEqual([cells[c]['value'] for c in ('A1','B1','C1','D1')],['Parameter','Value','Unit','Conditions'])
        got={cells['A%d'%row]['value']:(cells['B%d'%row]['value'],cells['B%d'%row]['unit'],cells['B%d'%row]['type']) for row in range(2,6)}
        self.assertEqual(got,{'Rail voltage':('12','V','number'),'Settled current':('250','mA','number'),
                              'Startup current':('900','mA','number'),'Startup duration':('45','ms','number')})
        self.assertNotIn('A6',cells)
        self.assertEqual(sheet['source_state'],{'state':'CURRENT_PDF_SOURCE','source_sha256':SOURCE_SHA256['readings']})
        origin=sheet['origin']
        self.assertEqual((origin['pdf']['item'],origin['pdf']['name'],origin['pdf']['page_index'],origin['pdf']['source_sha256']),
                         (made['sources']['readings']['item'],PDF,0,SOURCE_SHA256['readings']))
        self.assertEqual([(r['sheet_row'],tuple(r['original_cells'])) for r in origin['reviewed_rows']],
                         [(n,row) for n,row in enumerate(rail_demo.READINGS,2)])
        self.assertEqual(rail_demo.SETTLED_CELL,'B3')

    def test_the_two_revisions_of_the_limits_are_sheets_of_their_own_sources(self):
        made=self.ws.made
        for key,title,name,rows in (('limits_a',REV_A,PDF_A,rail_demo.LIMITS_A),('limits_b',REV_B,PDF_B,rail_demo.LIMITS_B)):
            sheet=self.ws.call('office.get',{'id':made['sheets'][key]})
            self.assertEqual(sheet['document']['title'],title)
            cells=sheet['document']['sheets'][0]['cells']
            self.assertEqual([tuple(cells['%s%d'%(c,n)]['value'] for c in 'ABCD') for n in range(2,2+len(rows))],[tuple(row) for row in rows],key)
            self.assertEqual(len(rows),4,key)
            self.assertEqual(sheet['source_state'],{'state':'CURRENT_PDF_SOURCE','source_sha256':SOURCE_SHA256[key]})
            self.assertEqual((sheet['origin']['pdf']['item'],sheet['origin']['pdf']['name']),(made['sources'][key]['item'],name))
        # what the two revisions say differently, and what they say alike
        a,b={r[0]:r[1:] for r in rail_demo.LIMITS_A},{r[0]:r[1:] for r in rail_demo.LIMITS_B}
        self.assertEqual(sorted(a),sorted(b))
        self.assertEqual(sorted(name for name in a if a[name]!=b[name]),['Settled power limit','Startup duration limit','Startup power ceiling'])
        self.assertEqual([name for name in a if a[name]==b[name]],['Nominal voltage'],'one row is the same in both: a comparison has something to leave out')

    def test_the_calculations_are_exact_and_read_reviewed_rows(self):
        made=self.ws.made
        for key,title,rational,decimal,cells in (('settled_power',SETTLED,'3','3',('B2','B3')),('startup_power',STARTUP,'54/5','10.8',('B2','B4'))):
            got=self.ws.call('documents.get',{'id':made['calculations'][key]})
            page=got['document'];value=page['derivation']['calculation']['outputs'][0]
            self.assertEqual(page['title'],title)
            self.assertEqual((value['state'],value['value']['rational'],value['value']['decimal'],value['value']['unit']),('EXACT',rational,decimal,'W'),key)
            self.assertEqual(value['value']['decimal'],{'settled_power':rail_demo.SETTLED_POWER,'startup_power':rail_demo.STARTUP_POWER}[key],'what the module says the result is, is what Graphite worked out')
            self.assertEqual([(i['cell'],i['basis']) for i in page['derivation']['inputs']],[(cell,'REVIEWED_PDF_ROW') for cell in cells],key)
            self.assertEqual(got['source_state']['state'],'CURRENT',key)
            trace=json.dumps(self.ws.call('field.trace',{'id':'document:'+made['calculations'][key]}))
            self.assertIn('office:'+made['sheets']['readings'],trace,key);self.assertIn('intake:'+made['sources']['readings']['item'],trace,key)
        settled=self.ws.call('documents.get',{'id':made['calculations']['settled_power']})['document']
        self.assertEqual([(i['parameter'],i['value'],i['unit']) for i in settled['derivation']['inputs']],[('Rail voltage','12','V'),('Settled current','250','mA')])

    def test_one_finding_holds_one_does_not_and_each_is_bound_to_what_it_rests_on(self):
        made=self.ws.made;sheet=self.ws.call('investigation.sheet',{'id':made['investigation']})
        checked={c['claim_text']:(c['last_outcome'],bool(c['refutes']),c['expect']) for c in sheet['checked']}
        self.assertEqual(checked,{DOES_NOT_HOLD:('CHECK_FAILED',True,'NONEMPTY'),KEEPS:('PASSED',False,'NONEMPTY')})
        programs={c['claim_text']:c['program'] for c in sheet['checked']}
        self.assertTrue(programs[DOES_NOT_HOLD].startswith('@office:'+made['sheets']['readings']+' | '),programs)
        self.assertTrue(programs[KEEPS].startswith('@office:'+made['sheets']['limits_b']+' | '),programs)
        by_title,objects,links,field=self.ws.desk()
        self.assertEqual((by_title[HOLDS]['state'],by_title[DOES_NOT_HOLD]['state']),('current','refuted'))
        for finding in (HOLDS,DOES_NOT_HOLD,CHANGED,KEEPS):
            self.assertTrue([link for link in links if link[1]==finding],'%r rests on nothing'%finding)
        self.assertEqual(sheet['next']['kind'],'QUESTION');self.assertIn(OPEN,sheet['next']['text'])

    def test_the_page_and_the_note_say_they_are_invented(self):
        made=self.ws.made
        page=self.ws.call('documents.get',{'id':made['page']})['document']
        words='\n'.join(block['text'] for block in page['blocks'])
        self.assertIn(rail_demo.NOTICE,words);self.assertIn('250 mA, which is 3 W',words)
        self.assertFalse(page.get('derivation'),'a plain page, not a calculation')

    def test_nothing_of_it_is_outside_the_folder_it_was_given(self):
        from workbench import session
        base=self.ws.base.resolve()
        self.assertIn(base,session.config_dir().resolve().parents)
        self.assertIn(base,Path(self.ws.k.root).resolve().parents)
        self.assertEqual(sorted(p.name for p in base.iterdir() if p.name!='Concern'),['profile','workspace'])
        self.assertTrue(list((base/'profile').rglob('*')),'the reviewed sheets are kept in the profile beside the workspace')

    def test_a_second_build_in_the_same_workspace_is_refused(self):
        before=self.ws.desk()[1]
        with self.assertRaisesRegex(rail_demo.Unavailable,'already in this workspace'):rail_demo.build(self.ws.k,self.ws.p)
        self.assertEqual(self.ws.desk()[1],before)

    def test_find_says_when_rail_demo_is_not_there(self):
        from workbench import locations
        from workbench.engineering_kernel import Kernel,operator
        with tempfile.TemporaryDirectory(prefix='graphite-rail-demo-empty-') as folder,patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(Path(folder)/'profile'),'ARC_LEDGER_CONCERN':str(Path(folder)/'Concern')}):
            kernel=Kernel(locations.office(Path(folder)/'workspace'))
            with self.assertRaisesRegex(rail_demo.Unavailable,'Rail Demo is not in this workspace'):
                rail_demo.find(kernel,operator())
            from tools.campaign_lib import cases_anchor          # 0.8.5: nor does the campaign find records that are not there
            with self.assertRaisesRegex(LookupError,'The restored workspace holds no reviewed sheet whose title says "bench readings"'):
                cases_anchor.found(kernel,operator())


class TheChange(unittest.TestCase):
    """A workspace of its own: the one change Rail Demo is made for. The tests run in name order: the change from 250 mA
    first, on the workspace as it was built; the others take the workspace as they find it."""

    @classmethod
    def setUpClass(cls):
        cls.ws=Workspace('graphite-rail-demo-change-')

    @classmethod
    def tearDownClass(cls):
        cls.ws.close()

    def test_250_to_300_mA_gives_3_6_W_and_sends_what_rests_on_it_to_recheck(self):
        ws=self.ws;made=ws.made;sheet_id='office:'+made['sheets']['readings']
        # what would move, before anything is changed
        preview=ws.call('field.ripple',{'id':sheet_id,'set':{'B3':'300'}})
        would={row['title']:(row['says_now'],row['would_be'],row['moves']) for row in preview['rows'] if row['kind'] in ('cell','calculation','finding')}
        self.assertEqual(would['“Rail Demo bench readings” B3 (Settled current)'],('250 mA','300 mA','yes'))
        self.assertEqual(would[SETTLED],('3 W','3.6 W','yes'));self.assertEqual(would[STARTUP],('10.8 W','10.8 W','no'))
        self.assertEqual(would[HOLDS],('3 W','3.6 W','yes'))
        self.assertEqual(ws.desk()[1],OBJECTS,'a what-if changes nothing')
        # the change
        changed=rail_demo.set_settled_current(ws.k,ws.p,'300')
        self.assertEqual({k:changed[k] for k in ('was','now','unit','power','exact','power_unit')},
                         {'was':'250','now':'300','unit':'mA','power':'3.6','exact':'18/5','power_unit':'W'})
        self.assertNotEqual(changed['calculation'],made['calculations']['settled_power'],'the settled power worked again is a new page')
        # the sheet says 300 mA; the reviewed source still says 250 mA
        sheet=ws.call('office.get',{'id':made['sheets']['readings']})
        cell=sheet['document']['sheets'][0]['cells']['B3']
        self.assertEqual((cell['value'],cell['unit'],sheet['revision']),('300','mA',changed['sheet_revision']))
        row=next(r for r in sheet['origin']['reviewed_rows'] if r['sheet_row']==3)
        self.assertEqual((row['parameter'],row['value'],row['unit']),('Settled current','250','mA'))
        self.assertEqual(sheet['source_state'],{'state':'CURRENT_PDF_SOURCE','source_sha256':SOURCE_SHA256['readings']})
        on_disk=Path(ws.call('files.list',{})['root'])/'Rail Demo sources'/PDF
        self.assertEqual(hashlib.sha256(on_disk.read_bytes()).hexdigest(),SOURCE_SHA256['readings'])
        # settled power is 3.6 W exactly, from 12 V as reviewed and 300 mA as edited, and it replaces the 3 W page
        page=ws.call('documents.get',{'id':changed['calculation']})['document'];value=page['derivation']['calculation']['outputs'][0]['value']
        self.assertEqual((page['title'],value['rational'],value['decimal'],value['unit']),('Rail Demo settled power · 3.6 W','18/5','3.6','W'))
        self.assertEqual({i['cell']:(i['value'],i['unit'],i['basis']) for i in page['derivation']['inputs']},
                         {'B2':('12','V','REVIEWED_PDF_ROW'),'B3':('300','mA','WORKING_SHEET_EDIT')})
        self.assertEqual(page['derivation']['replaces'],made['calculations']['settled_power'])
        now=rail_demo.find(ws.k,ws.p)
        self.assertEqual(now['calculations'],{'settled_power':changed['calculation'],'startup_power':made['calculations']['startup_power']})
        self.assertEqual({k:v for k,v in now.items() if k!='calculations'},{k:v for k,v in made.items() if k!='calculations'})
        # what rests on it waits for a recheck: the finding that still says 3 W, and the other calculation of the sheet
        by_title,objects,links,field=ws.desk()
        self.assertEqual((by_title[HOLDS]['state'],by_title[HOLDS]['facts'][0]),('recheck','says 3 W; now 3.6 W'))
        self.assertEqual(by_title[STARTUP]['state'],'recheck')
        self.assertEqual(by_title['Rail Demo settled power · 3.6 W']['state'],'current')
        self.assertNotIn(SETTLED,by_title,'the 3 W page left the desk when the 3.6 W page replaced it')
        self.assertEqual(by_title[READINGS]['facts'],['reviewed from page 1','version 2'])
        self.assertEqual(field['moved'],[{'was':'3 W','now':'3.6 W','calculation':'Rail Demo settled power · 3.6 W'}])
        self.assertEqual([c for c in field['counts'] if 'lately' not in c],COUNTS+['2 to recheck'])
        self.assertEqual({(l['from'],l['to']):l['stale'] for l in field['links'] if l['label'].startswith('cells ')},
                         {(READINGS,'Rail Demo settled power · 3.6 W'):'no',(READINGS,STARTUP):'yes'})
        # nothing else moved: the other sheets, the sources, the other findings and the question are as they were
        unchanged={o for o in OBJECTS if o[1] not in (HOLDS,SETTLED,STARTUP,READINGS)}
        self.assertEqual({o for o in objects if o[1] in {u[1] for u in unchanged}},unchanged)

    def test_310_mA_written_and_stopped_before_the_recheck_is_carried_on_by_asking_again(self):
        ws=self.ws;made=rail_demo.find(ws.k,ws.p)
        standing=ws.call('documents.get',{'id':made['calculations']['settled_power']})['document']
        read=next(i['value'] for i in standing['derivation']['inputs'] if i['cell']=='B3')
        sheet=ws.call('office.get',{'id':made['sheets']['readings']})
        self.assertNotEqual(sheet['document']['sheets'][0]['cells']['B3']['value'],'310')
        # the cell is written and nothing more: the stop
        written=ws.call('field.set',{'id':'office:'+sheet['id'],'cell':'B3','value':'310','expected_revision':sheet['revision']})
        self.assertEqual(rail_demo.find(ws.k,ws.p)['calculations'],made['calculations'],'nothing was worked again yet')
        # asked again with the same value: the cell is left as it is, the power is worked from it
        carried=rail_demo.set_settled_current(ws.k,ws.p,'310')
        self.assertEqual({k:carried[k] for k in ('was','now','unit','sheet_revision','power','exact','power_unit')},
                         {'was':read,'now':'310','unit':'mA','sheet_revision':written['revision'],'power':'3.72','exact':'93/25','power_unit':'W'})
        self.assertEqual(ws.call('office.get',{'id':made['sheets']['readings']})['revision'],written['revision'],'the sheet was not saved a second time')
        page=ws.call('documents.get',{'id':carried['calculation']})['document']
        self.assertEqual((page['title'],page['derivation']['replaces']),('Rail Demo settled power · 3.72 W',made['calculations']['settled_power']))
        # once it is whole, the same value again is refused in words, and it says what was being done
        with self.assertRaises(rail_demo.Unavailable) as refused:rail_demo.set_settled_current(ws.k,ws.p,'310')
        self.assertEqual(str(refused.exception),'The settled current of Rail Demo could not be changed: field.set was refused (B3 already says 310).')
        self.assertEqual(rail_demo.find(ws.k,ws.p)['calculations']['settled_power'],carried['calculation'])

    def test_a_value_that_is_not_a_number_is_refused_in_words_and_nothing_moves(self):
        ws=self.ws;before=rail_demo.find(ws.k,ws.p)
        for value in ('abc','300 mA',''):
            with self.assertRaisesRegex(rail_demo.Unavailable,r'^The settled current of Rail Demo could not be changed: field\.set was refused \('):
                rail_demo.set_settled_current(ws.k,ws.p,value)
        self.assertEqual(rail_demo.find(ws.k,ws.p),before)

    def test_rail_demo_is_found_among_more_pages_than_one_list_gives(self):
        ws=self.ws;before=rail_demo.find(ws.k,ws.p)
        for n in range(rail_demo.PAGE+1):ws.call('documents.create',{'title':'Another page %03d'%n,'text':'A page that is not of Rail Demo.','origin':'HUMAN'})
        self.assertGreater(len(ws.call('documents.list',{'limit':rail_demo.PAGE,'offset':rail_demo.PAGE})['documents']),0,'more pages than one list gives')
        self.assertEqual(rail_demo.find(ws.k,ws.p),before)


class ThePlayableSceneOnRailDemo(unittest.TestCase):
    """P01 on the live window on Rail Demo: the same acts in the same order as on the owner's workspace, each name swapped.
    The window is built once, on a workspace Rail Demo was built in before any hold was in place (reading a source in is a
    job); from then on nothing starts, as in the right-click's tests."""

    @classmethod
    def setUpClass(cls):
        build_window(WINDOW,'graphite-rail-demo-scene-',seed=rail_demo.build,early=True)

    @classmethod
    def tearDownClass(cls):
        close_window(WINDOW);WINDOW.clear()

    def setUp(self):
        from workbench.desk_doers import run
        from workbench.engineering_kernel import operator
        w=WINDOW['w']
        for name,args in (('menu.close',{}),('hand.dial',{'place':'show'})):run(w,name,args,door='script',origin='desk-script:setup')
        if getattr(w,'_field_active',False):run(w,'go.back',{'by':'pointer'},door='script',origin='desk-script:setup')
        if (WINDOW['files']/CSV).exists():WINDOW['k'].dispatch('files.trash',{'path':CSV},operator())
        if w.type_bar.box.text():w.type_bar.box.clear()
        w._desk_put='';settle(WINDOW)

    def play(self,run,size=None):
        from workbench import desk_scene
        scene=desk_scene.load(P01)
        if size:scene['given']['size']=list(size)
        wrote=[]

        def after(n,step,row):
            if step['act']=='hand.write':wrote.append((WINDOW['files']/CSV).read_text(encoding='utf-8'))      # read in Files, while it is there
        out=desk_scene.run_scene(WINDOW['w'],scene,run,seed='rail_demo',origin='desk-script:P01',after_step=after)      # the scene as it is written: the seed is the switch
        self.assertNotIn('blocked',out)
        # what the doer was given is what the scene says: the file it wrote holds Rail Demo's readings (0.8.5: the scene is written with them)
        self.assertEqual(wrote,[CSV_TEXT])
        self.assertEqual([s['args'] for s in out['steps'] if s['act']=='hand.write'],[{'path':CSV,'text':CSV_TEXT}],'and the row says what the doer was given')
        self.assertTrue(out['passed'],desk_scene.failures(out))
        self.assertEqual(len(out['steps']),len(scene['steps']))
        self.assertEqual([s['act'] for s in out['steps']],[s['act'] for s in scene['steps']],'the same acts in the same order')
        self.assertFalse((WINDOW['files']/CSV).exists(),'the scene takes back what it wrote')
        return out

    def test_the_window_stands_on_rail_demo_and_the_scene_names_nothing_else(self):
        from workbench import desk_scene
        from workbench.engineering_kernel import operator
        made=WINDOW['seeded']
        self.assertEqual(made,rail_demo.find(WINDOW['k'],operator()))
        field=WINDOW['k'].dispatch('field.read',{},operator())['result']
        self.assertTrue(field['title'].startswith(DESK));self.assertEqual([c for c in field['counts'] if 'lately' not in c],COUNTS)
        written=desk_scene.load(P01);scene=desk_scene.for_workspace(written,'rail_demo')
        self.assertEqual(scene,written,'0.8.5: the scene is written on Rail Demo')
        self.assertEqual(desk_scene.check_scene(scene),[])
        said=json.dumps([[desk_scene.arguments(step,'rail_demo'),desk_scene.expected(step,run['name'],'rail_demo')] for step in scene['steps'] for run in scene['runs']])
        self.assertNotIn('After Hours',said)

    def test_p01_as_played_on_the_owners_workspace_finds_each_name_here_and_passes(self):
        # 0.8.5: the scene's After Hours 07 entry finds each name by its kind and the words it says. On Rail Demo they are
        # Rail Demo's own, so the scene as it is played on the owner's workspace (find_names, the swap) is played here.
        from workbench import desk_scene
        from workbench.engineering_kernel import operator
        written=desk_scene.load(P01)
        found=desk_scene.find_names(WINDOW['k'],operator(),written,'after_hours_07')
        self.assertEqual(found,{name:name for name in written['workspaces']['after_hours_07']['find']})
        out=desk_scene.run_scene(WINDOW['w'],written,'keys_still',seed='after_hours_07',origin='desk-script:P01')
        self.assertNotIn('blocked',out)
        self.assertEqual((out['seed'],out['found']),('after_hours_07',found))
        self.assertTrue(out['passed'],desk_scene.failures(out))
        self.assertEqual(len(out['steps']),len(written['steps']))
        self.assertFalse((WINDOW['files']/CSV).exists(),'the scene takes back what it wrote')

    def test_p01_by_mouse(self):
        out=self.play('mouse')
        self.assertTrue(all(s['by'] in ('pointer','direct') for s in out['steps']),[(s['act'],s['by']) for s in out['steps']])
        by_act={s['act']:s for s in out['steps']}
        self.assertEqual(by_act['hand.write']['args']['path'],CSV)
        self.assertIn('Settled current,250,mA',by_act['hand.write']['args']['text'])
        route=by_act['sheet.trace']['result']['route']
        self.assertEqual((route['owner_title'],route['hops']),(READINGS,2))
        self.assertTrue({SETTLED,STARTUP}<=set(route['ends']),route)
        revisions=by_act['sheet.compare']['result']['revisions']
        self.assertEqual((revisions['a'],revisions['b'],revisions['changed']),(REV_A,REV_B,['Settled power limit','Startup duration limit','Startup power ceiling']))

    def test_p01_by_mouse_on_a_small_window(self):
        out=self.play('mouse',(1366,768))
        self.assertEqual((WINDOW['w'].width(),WINDOW['w'].height()),(1366,768))
        self.assertTrue(all(s['by'] in ('pointer','direct') for s in out['steps']),[(s['act'],s['by']) for s in out['steps']])

    def test_p01_by_keys(self):
        out=self.play('keys')
        by={s['act']:s['by'] for s in out['steps']}
        for name in ('go.files','menu.open','menu.choose','then.keep','then.count','then.end','go.field','point.sheet','sheet.trace','sheet.compare','sheet.close'):
            self.assertEqual(by[name],'keys',name)
        self.assertIs(out['steps'][0]['result']['keyboard_route'],False)

    def test_p01_by_keys_reduced_motion(self):
        out=self.play('keys_still')
        by={s['act']:s['by'] for s in out['steps']}
        for name in ('go.files','menu.open','menu.choose','then.keep','then.count','then.end','go.field','point.sheet','sheet.trace','sheet.compare','sheet.close'):
            self.assertEqual(by[name],'keys',name)
        trace=next(s for s in out['steps'] if s['act']=='sheet.trace')
        self.assertIs(trace['result']['route']['animating'],False)

    def test_p01_by_mouse_reduced_motion(self):
        out=self.play('mouse_still')
        trace=next(s for s in out['steps'] if s['act']=='sheet.trace')
        self.assertIs(trace['result']['route']['animating'],False)
        from workbench import menu_catch, boss_theme
        still_look=boss_theme.glow()<=0      # 1.1 T2: Day and Night draw no glow, so they are always calm (1.0 P4)
        self.assertIs(menu_catch.calm(WINDOW['w']),still_look,'the motion is put back as the scene found it')

    def test_the_scene_leaves_the_records_of_rail_demo_as_it_found_them(self):
        from workbench.engineering_kernel import operator
        def desk():
            return pictured(WINDOW['k'].dispatch('field.read',{},operator())['result'])
        before=desk();self.assertEqual(before,(OBJECTS,LINKS))
        self.play('mouse_still')
        self.assertEqual(desk(),before)


if __name__=='__main__':
    unittest.main()
