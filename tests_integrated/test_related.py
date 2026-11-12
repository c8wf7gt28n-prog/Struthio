"""Quiet connections and the right column (HATCH AGENT-01, WI-C).

Related scoring and bounds, the page's own exclusion, the two-word minimum, the sources that are not filled yet, the
Related block's dismissed rows, the driver's tick with a held step function (no window), the assignment route from the
typing strip, and the page's stale line and recheck through the undo stack. No model, no job, no worker: Kernel.launch
and Kernel.submit are held; the Qt parts run offscreen without a window.
"""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import related as R,agent_loop
from workbench.engineering_kernel import Kernel,operator,CAPABILITIES
from workbench.tool_selection import tokens

ID='f'*32
OTHER='e'*32


def cand(ident,words,kind='idea',label=None,open_='project_desk'):
    return {'id':ident,'kind':kind,'label':label or ident,'open':open_,'tokens':set(words)}


class Scoring(unittest.TestCase):
    """The pure part: shared words, rarity, bounds."""

    def test_shared_words_count_a_word_once_whatever_its_spelling(self):
        self.assertEqual(R.shared_words({'numbers','number','page'},{'number','numbers','page'}),['numbers','page'])
        self.assertEqual(R.shared_words(tokens('the quantities on this page'),tokens('one quantity per page')),['page','quantity'])
        self.assertEqual(R.shared_words(tokens('the quantities on this page'),tokens('the quantities per page')),['page','quantities'])
        self.assertEqual(R.shared_words(tokens('writing a page'),tokens('write the page')),['page','write'])
        self.assertEqual(R.shared_words({'ostrich'},{'feed'}),[])

    def test_rank_orders_by_shared_words_and_rarer_words_weigh_more(self):
        page=tokens('ostrich feed pellets')
        rows=R.rank(page,[cand('idea:a',{'ostrich','feed','pellets','pellet','grit'}),cand('idea:b',{'ostrich','garden'}),
                          cand('idea:c',{'garden','gate','hinge'}),cand('idea:d',{'feed','ostrich','birds','bird'})])
        self.assertEqual([r['id'] for r in rows],['idea:a','idea:d'])          # b shares one word, c none
        self.assertEqual(rows[0]['words'],['feed','ostrich','pellets']);self.assertGreater(rows[0]['score'],rows[1]['score'])
        self.assertEqual((rows[0]['kind'],rows[0]['open'],rows[0]['label']),('idea','project_desk','idea:a'))
        # rarity: 'feed' is carried by one record, 'garden' by three; two shared words each, the rarer pair scores higher
        rows=R.rank(tokens('ostrich feed garden'),[cand('x',{'ostrich','feed'}),cand('y',{'ostrich','garden'}),cand('z1',{'ostrich','garden','gate'}),
                                                   cand('z2',{'ostrich','garden','hinge'}),cand('z3',{'ostrich','wire'})])
        self.assertEqual(rows[0]['id'],'x');self.assertEqual({r['id'] for r in rows},{'x','y','z1','z2'})
        self.assertTrue(all(rows[0]['score']>r['score'] for r in rows[1:]))

    def test_rank_bounds_and_the_two_word_minimum(self):
        page=tokens('ostrich feed pellets grit')
        many=[cand('idea:%d'%i,{'ostrich','feed'}) for i in range(14)]
        self.assertEqual(len(R.rank(page,many,limit=50)),10);self.assertEqual(len(R.rank(page,many,limit=3)),3);self.assertEqual(len(R.rank(page,many,limit=0)),1)
        self.assertEqual(R.rank(page,[cand('one',{'ostrich','sand'})]),[])                       # one shared word is not a connection
        self.assertEqual(R.rank({'numbers','number'},[cand('same',{'number','numbers'})]),[])      # the same word twice is still one word
        self.assertEqual(R.rank(set(),many),[]);self.assertEqual(R.rank(page,[]),[])
        self.assertEqual(R.label_of('  a   long   '+'x'*100)[-1],'…');self.assertEqual(R.label_of('short words'),'short words')


class Route(unittest.TestCase):
    """ledger.related through the Kernel over the owner's own records."""
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ledger-related-');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(Path(temporary.name)/'profile')});env.start();self.addCleanup(env.stop)
        self.kernel=Kernel(self.root);self.owner=operator('owner')
        for name in ('launch','submit'):
            held=patch.object(Kernel,name,side_effect=AssertionError('no '+name));held.start();self.addCleanup(held.stop)

    def call(self,op,args=None,principal=None):
        r=self.kernel.dispatch(op,args or {},principal or self.owner);self.assertTrue(r['ok'],r);return r['result']

    def test_related_excludes_the_page_and_names_cabinet_identities(self):
        page=self.call('documents.create',{'title':'Feed this week','text':'Pellets 12.5 kg, grit 3 kg and oyster shell 0.5 kg for the ostrich feed this week.'})
        other=self.call('documents.create',{'title':'Gate','text':'The garden gate hinge squeaks.'})
        idea=self.call('ideas.capture',{'text':'Ostrich feed: weigh the pellets and the grit each week so the total is known.'})
        project=self.call('projects.create',{'title':'Ostrich pen','intent':'Feed pellets and grit weekly; keep the birds well.'})
        inv=self.call('investigation.create',{'question':'How many kg of pellets do the ostriches eat each week?'})
        text='\n'.join(b['text'] for b in page['blocks'])
        value=self.call('ledger.related',{'text':text,'exclude':['document:'+page['id']]})
        ids={r['id']:r for r in value['related']}
        self.assertEqual(value['basis'],'WORD_MATCH_NO_MODEL')
        self.assertIn('idea:'+idea['id'],ids);self.assertIn('project:'+project['id'],ids);self.assertIn('investigation:'+inv['id'],ids)
        self.assertNotIn('document:'+page['id'],ids);self.assertNotIn('document:'+other['id'],ids)
        self.assertEqual(ids['idea:'+idea['id']]['open'],'project_desk');self.assertEqual(ids['investigation:'+inv['id']]['open'],'investigations')
        self.assertTrue(all(len(r['words'])>=2 and r['score']>0 for r in value['related']))
        self.assertEqual(value['related'],sorted(value['related'],key=lambda r:(-r['score'],-len(r['words']),r['label'],r['id'])))
        self.assertEqual((value['searched']['ideas'],value['searched']['projects'],value['searched']['documents'],value['searched']['investigations']),(1,1,1,1))
        self.assertEqual(value['searched']['candidates'],4)   # the page itself was excluded before counting
        # a second document that shares the words is found, and opens as a document
        twin=self.call('documents.create',{'title':'Feed last week','text':'Pellets 11 kg and grit 2 kg: the ostrich feed last week.'})
        value=self.call('ledger.related',{'text':text,'exclude':[page['id']],'limit':2})
        self.assertEqual(len(value['related']),2);self.assertIn('document:'+twin['id'],{r['id'] for r in self.call('ledger.related',{'text':text,'exclude':[page['id']]})['related']})
        found=next(r for r in self.call('ledger.related',{'text':text,'exclude':[page['id']]})['related'] if r['id']=='document:'+twin['id']);self.assertEqual(found['open'],'documents:'+twin['id'])
        # fewer than two words: nothing is read
        short=self.call('ledger.related',{'text':'kg'});self.assertEqual(short['related'],[]);self.assertIn('nothing was read',short['searched']['note'])
        # another owner sees none of these records
        self.assertEqual(self.call('ledger.related',{'text':text},operator('someone-else'))['related'],[])

    def test_registry_and_sources_not_filled_yet_are_skipped_in_words(self):
        self.assertEqual(CAPABILITIES['ledger.related'],'read')
        from workbench import activity,stacy_control
        self.assertIn('ledger.related',activity.OBSERVER_OPERATIONS);self.assertTrue(stacy_control.cloud_private('ledger.related',{'text':'a b'}))
        self.call('ideas.capture',{'text':'Ostrich feed pellets and grit'})
        with patch.object(agent_loop,'dispatch',side_effect=NotImplementedError('AGENT01_WI_A: agent.list')):
            value=self.call('ledger.related',{'text':'ostrich feed pellets'})
        self.assertEqual(len(value['related']),1);self.assertTrue(value['searched']['skipped']['assignments'].startswith('not available yet'))
        value=self.call('ledger.related',{'text':'ostrich feed pellets'})   # whatever state WI-A is in, the call answers
        self.assertTrue('assignments' in value['searched'] or 'assignments' in value['searched']['skipped'])
        with self.assertRaises(ValueError):R.dispatch(self.kernel,'ledger.unrelated',{},self.owner)


class Column(unittest.TestCase):
    """The right column's widgets and the driver, offscreen, without a window."""
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def host(self,**extra):
        class Session:
            def __init__(self):self.state={};self.saved=0
            def save(self):self.saved+=1
        class Host:
            def __init__(self):self.session=Session();self.tabs=None;self._home_active=False;self._closing=False;self.root=Path('/nonexistent/ledger');self.messages=[]
            def statusBar(self):
                host=self
                class Bar:
                    def showMessage(self,text,ms=0):host.messages.append(text)
                return Bar()
        host=Host()
        for key,value in extra.items():setattr(host,key,value)
        return host

    def test_related_block_hides_dismissed_rows_and_keeps_five(self):
        from workbench.agent_qt import RelatedBlock,RELATED_LIMIT
        host=self.host();block=RelatedBlock(host);block.timer.stop()
        def close_block(block=block):   # AGENT-02: a parentless block and its rows' deferred deletions must not outlive this test (they crashed Qt in the next one)
            from PySide6.QtCore import QCoreApplication, QEvent
            block.set_rows([]);QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);block.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
        self.addCleanup(close_block)
        rows=[{'id':'idea:%d'%i,'kind':'idea','label':'Idea %d'%i,'words':['ostrich','feed'],'score':2.0,'open':'project_desk'} for i in range(7)]
        shown=block.set_rows(rows) or block.visible_rows()
        self.assertEqual(len(block.visible_rows()),RELATED_LIMIT);self.assertEqual(block.list.count(),RELATED_LIMIT);self.assertFalse(block.isHidden())
        block.dismiss('idea:0');block.dismiss('idea:3')
        self.assertEqual(host.session.state['related_dismissed'],['idea:0','idea:3']);self.assertEqual(host.session.saved,2)
        self.assertEqual([r['id'] for r in block.visible_rows()],['idea:1','idea:2','idea:4','idea:5','idea:6']);self.assertEqual(block.list.count(),5)
        block.set_rows(rows[:2]);self.assertEqual([r['id'] for r in block.visible_rows()],['idea:1']);self.assertEqual(block.list.count(),1)
        block.set_rows([]);self.assertTrue(block.isHidden());self.assertIsNone(block.page())   # no page open: nothing to relate
        self.assertEqual(block.query('kg'),[])                                                  # one word: no read, no rows

    def test_driver_ticks_until_the_assignment_leaves_running(self):
        from workbench import agent_qt
        states=iter(['RUNNING','RUNNING','DONE'])
        calls=[]
        def step(host,ident):calls.append(ident);return {'ok':True,'result':{'assignment':{'id':ident,'state':next(states)},'step':{},'next':None}}
        host=self.host()
        with patch.object(agent_qt,'step_once',side_effect=step):
            driver=agent_qt.AgentDriver(host);self.assertEqual(driver.running(),[]);self.assertFalse(driver.timer.isActive())
            self.assertTrue(driver.start(ID));self.assertTrue(driver.timer.isActive());self.assertEqual(driver.running(),[ID])
            driver.tick();driver.tick();self.assertEqual(driver.running(),[ID]);self.assertEqual(driver.states[ID],'RUNNING')
            driver.tick();self.assertEqual(driver.running(),[]);self.assertFalse(driver.timer.isActive());self.assertEqual(driver.states[ID],'DONE')
            self.assertEqual((driver.ticks,calls),(3,[ID,ID,ID]))
            driver.tick();self.assertEqual(len(calls),3)   # nothing RUNNING: a tick steps nothing
        # a refused step (the operation not filled yet, or outside the budget) drops the assignment and keeps the words
        with patch.object(agent_qt,'step_once',return_value={'ok':False,'error':{'message':'AGENT01_WI_A: agent.step'}}):
            driver.start(OTHER);driver.tick()
            self.assertEqual(driver.running(),[]);self.assertFalse(driver.timer.isActive());self.assertIn('AGENT01_WI_A',driver.last_error[OTHER])
        # closing: no step runs
        host._closing=True
        with patch.object(agent_qt,'step_once',side_effect=AssertionError('must not step while closing')):
            driver.start(ID);driver.tick();self.assertEqual(driver.running(),[ID])

    def test_driver_pause_all_pauses_what_it_drives_and_what_else_runs(self):
        from workbench import agent_qt
        paused=[];host=self.host()
        with patch.object(agent_qt,'summaries',return_value=[{'id':OTHER,'state':'RUNNING','request':'x'},{'id':'d'*32,'state':'DONE'}]),\
             patch.object(agent_qt,'pause_one',side_effect=lambda h,i,reason:(paused.append((i,reason)),{'ok':True,'result':{'assignment':{'id':i,'state':'PAUSED'}}})[1]),\
             patch.object(agent_qt,'step_once',return_value={'ok':True,'result':{'assignment':{'id':ID,'state':'RUNNING'}}}):
            driver=agent_qt.AgentDriver(host);driver.start(ID);driver.tick()
            self.assertEqual(driver.pause_all('Ledger closed'),[ID,OTHER])
            self.assertEqual(paused,[(ID,'Ledger closed'),(OTHER,'Ledger closed')]);self.assertEqual(driver.running(),[]);self.assertFalse(driver.timer.isActive())
            self.assertEqual(driver.states[ID],'PAUSED')
            # resume brings it back under the driver; stop takes it out
            with patch.object(agent_qt,'resume_one',return_value={'ok':True,'result':{'assignment':{'id':ID,'state':'READY'}}}):
                driver.resume(ID);self.assertEqual(driver.running(),[ID]);self.assertTrue(driver.timer.isActive())
            with patch.object(agent_qt,'stop_one',return_value={'ok':True,'result':{'assignment':{'id':ID,'state':'STOPPED'}}}):
                driver.stop(ID);self.assertEqual(driver.running(),[]);self.assertFalse(driver.timer.isActive());self.assertEqual(driver.states[ID],'STOPPED')
        rows=agent_qt.today_rows(host) if False else None   # today_rows reads the Kernel; covered below with held summaries
        with patch.object(agent_qt,'summaries',return_value=[{'id':ID,'state':'PAUSED','request':'add up the numbers on this page','paused_reason':'Ledger closed'},
                                                             {'id':OTHER,'state':'WAITING','request':'count the values here'},{'id':'d'*32,'state':'DONE','request':'done'}]):
            rows=agent_qt.today_rows(host)
        self.assertEqual([(t,w) for t,w,_ in rows],[('Graphite paused: add up the numbers on this page (Ledger closed)','resume'),('Graphite needs you: count the values here','assignment')])  # a reason stored before the rename reads as written

    def test_assignment_route_from_the_typing_strip(self):
        from workbench import agent_qt
        class Tab:
            document_id='a'*32
            def __init__(self):self.flushed=0
            def flush(self):self.flushed+=1;return True
        class Driver:
            def __init__(self):self.started=[]
            def start(self,ident):self.started.append(ident);return True
        tab=Tab();driver=Driver();host=self.host(agent_driver=driver);sent=[]
        def write(h,op,args):sent.append((op,args));return {'ok':True,'result':{'assignment':{'id':ID,'state':'READY','request':args['request']},'sheet':{}}}
        with patch.object(agent_loop,'request_profile',return_value='numbers_on_page'),patch.object(agent_qt,'call_write',side_effect=write):
            answer=agent_qt.assign_from_page(host,tab,'add up the numbers on this page')
        self.assertEqual(answer,'Working on it: add up the numbers on this page. Watch the Work lines above; Stop is there.')
        self.assertEqual(sent,[('agent.assign',{'request':'add up the numbers on this page','profile':'numbers_on_page','context':{'document':'a'*32}})])
        self.assertEqual((tab.flushed,driver.started),(1,[ID]))
        with patch.object(agent_loop,'request_profile',return_value=None),patch.object(agent_qt,'call_write',side_effect=AssertionError('no call')):
            self.assertIsNone(agent_qt.assign_from_page(host,tab,'write a sonnet'))                  # no profile: the model path is next
        with patch.object(agent_loop,'request_profile',side_effect=NotImplementedError('AGENT01_WI_A')):
            self.assertIsNone(agent_qt.assign_from_page(host,tab,'add up the numbers on this page'))  # WI-A not landed: no exception
        with patch.object(agent_loop,'request_profile',return_value='numbers_on_page'):
            self.assertIsNone(agent_qt.assign_from_page(host,object(),'add up the numbers on this page'))   # no page open
            with patch.object(agent_qt,'call_write',return_value={'ok':False,'error':{'message':'AGENT01_WI_A: agent.assign'}}):
                self.assertEqual(agent_qt.assign_from_page(host,tab,'add up the numbers on this page'),'I could not take that on: AGENT01_WI_A: agent.assign')
        self.assertEqual(driver.started,[ID])

    def test_stale_sentence(self):
        from workbench.document_qt import stale_sentence
        asked=[]
        html,actions=stale_sentence([{'id':ID,'state':'STALE','reason':'the words at 12.5 kg changed'}],lambda ids:asked.append(ids))
        self.assertEqual(html,'A result on this page is stale: the words at 12.5 kg changed · {recheck}');self.assertEqual(actions['recheck'][0],'recheck')
        actions['recheck'][1]();self.assertEqual(asked,[[ID]])
        html,_=stale_sentence([{'id':ID,'state':'BROKEN'}],lambda ids:None);self.assertTrue(html.startswith('A result paragraph on this page was removed'))
        html,actions=stale_sentence([{'id':ID,'state':'STALE'},{'id':OTHER,'state':'STALE'},{'id':'d'*32,'state':'BROKEN'}],lambda ids:asked.append(ids))
        self.assertEqual(html,'3 results on this page are stale · {recheck}');actions['recheck'][1]();self.assertEqual(asked[-1],[ID,OTHER,'d'*32])
        self.assertEqual(stale_sentence([],lambda ids:None),('',{}))

    def test_page_stale_line_recheck_and_sync_through_the_undo_stack(self):
        temporary=tempfile.TemporaryDirectory(prefix='ledger-related-qt-');self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)/'workspace';root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(Path(temporary.name)/'profile')});env.start();self.addCleanup(env.stop)
        kernel=Kernel(root)
        for name in ('launch','submit'):
            held=patch.object(Kernel,name,side_effect=AssertionError('no '+name));held.start();self.addCleanup(held.stop)
        from workbench import document_qt as page,engine
        host=self.host(root=root,reading_profile=None)
        with patch.object(engine,'engineering',return_value=kernel):
            tab=page.DocumentsTab(host);ident=tab.document_id
            def close_page(tab=tab):   # AGENT-02: the page is closed and deleted before the next test, so no deferred refont or timer of a
                from PySide6.QtCore import QCoreApplication, QEvent   # page whose store is gone runs inside another test (it crashed Qt there)
                tab.save_timer.stop();tab.flash_timer.stop();tab.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
            self.addCleanup(close_page)
            tab.page.setPlainText('');tab.page.insertPlainText('Pellets 12.5 kg, grit 3 kg and oyster shell 0.5 kg.');self.assertTrue(tab.flush());self.assertEqual(tab.revision,2)
            self.assertEqual(tab.related_text(),'Pellets 12.5 kg, grit 3 kg and oyster shell 0.5 kg.\nPellets 12.5 kg, grit 3 kg and oyster shell 0.5 kg.')
            self.assertTrue(tab.stale.isHidden());self.assertEqual(tab.stale_ids,[])      # conditions.list not readable or empty: no line, no exception
            # Slate's assignment appends its result in the store; the page follows through its undo stack
            r=kernel.dispatch('documents.edit',{'id':ident,'expected_revision':2,'selection':{'block':0,'start':0,'end':0},'change':{'append':'Total of the 3 quantities on this page: 16 kg · checked by Slate'},'origin':'SLATE','request':'add up the numbers on this page'},operator())
            self.assertTrue(r['ok'],r);stored=r['result']['document'];self.assertEqual(stored['revision'],3)
            self.assertTrue(tab.sync());self.assertEqual(tab.revision,3);self.assertFalse(tab.dirty)
            self.assertEqual(tab.page.toPlainText(),'Pellets 12.5 kg, grit 3 kg and oyster shell 0.5 kg.\nTotal of the 3 quantities on this page: 16 kg · checked by Slate')
            self.assertTrue(tab.page.document().isUndoAvailable());self.assertEqual(page.from_qt(tab.page.document(),tab.block_ids),stored['blocks'])
            self.assertFalse(tab.sync())    # nothing newer: nothing happens
            # the stale line: a card on this page reads STALE; the word rechecks it and the rewritten paragraph lands on the page
            cards=[{'id':ID,'state':'STALE','document':ident,'reason':'the words at 3 kg changed'}];original_call=page.call;original_write=page.call_write
            def reading(h,op,args=None):
                if op=='conditions.list':self.assertEqual(args,{'document':ident});return {'conditions':cards}
                return original_call(h,op,args)
            def writing(h,op,args):
                if op=='conditions.recheck':
                    self.assertEqual(args,{'id':ID});doc=kernel.dispatch('documents.get',{'id':ident},operator())['result']['document']
                    blocks=[dict(b) for b in doc['blocks']];blocks[-1]['text']='Total of the 3 quantities on this page: 17 kg · checked by Slate'
                    cards.clear();return {'ok':True,'result':{'condition':{'id':ID,'state':'CURRENT','result_block':blocks[-1]['id']},'document':{**doc,'blocks':blocks,'revision':doc['revision']+1},'words':'rewrote the total'}}
                return original_write(h,op,args)
            with patch.object(page,'call',side_effect=reading),patch.object(page,'call_write',side_effect=writing):
                self.assertEqual(tab.refresh_conditions(),[ID]);self.assertFalse(tab.stale.isHidden())
                self.assertIn('A result on this page is stale',tab.stale.text());self.assertIn('recheck',tab.stale.text())
                self.assertTrue(tab.recheck())
                self.assertTrue(tab.page.toPlainText().endswith('17 kg · checked by Slate'));self.assertEqual(tab.revision,4);self.assertFalse(tab.dirty)
                self.assertTrue(tab.foot.text().startswith('Rechecked · rewrote the total'));self.assertTrue(tab.stale.isHidden());self.assertEqual(tab.stale_ids,[])
                tab.page.undo();self.assertTrue(tab.page.toPlainText().endswith('16 kg · checked by Slate'))   # Slate's rewrite is one undo step
            with patch.object(page,'call_write',return_value={'ok':False,'error':{'message':'AGENT01_WI_B: conditions.recheck'}}):
                tab.stale_ids=[ID];tab.dirty=False;self.assertFalse(tab.recheck());self.assertTrue(tab.foot.text().startswith('Not rechecked: AGENT01_WI_B'))


if __name__=='__main__':unittest.main()
