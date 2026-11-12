"""The model turn applied to a real page (HATCH AGENT-02, owner decision D19): decide() and words() without Qt, then the
page's apply_model_edit offscreen against a disposable store.

Nothing here starts a model, a worker or a job: the proposals are written out by hand (one is the 1.5B model's own
proposal from the AGENT-01 live trial), Kernel.launch and Kernel.submit are held, and the page runs offscreen.
"""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import model_turn as M,documents as D
from workbench.engineering_kernel import Kernel,operator

DOC='0123456789abcdef0123456789abcdef'
OTHER='fedcba9876543210fedcba9876543210'
TEXT='The quick brown fox jumps over the lazy dog.'
SELECTED={'block':0,'start':4,'end':15,'text':'quick brown'}


def page(**extra):
    base=M.page_of(DOC,2,1,0,dict(SELECTED),[TEXT]);base.update(extra);return base


def edit(**arguments):
    return {'operation':'documents.edit','arguments':arguments}


class Decide(unittest.TestCase):
    def test_a_complete_edit_for_the_open_page_applies_as_the_model(self):
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection=dict(SELECTED),change={'bold':True}),page())
        self.assertTrue(verdict['apply'],verdict);self.assertEqual(verdict['notes'],[])
        self.assertEqual(verdict['arguments'],{'id':DOC,'expected_revision':2,'selection':SELECTED,'change':{'bold':True},'origin':M.ORIGIN})
        self.assertEqual(verdict['corrections'],[])
        self.assertIn(M.ORIGIN,getattr(D,'EDIT_ORIGINS',D.ORIGINS))   # an origin the store accepts today (SLATE until SLATE_MODEL is added)

    def test_the_live_trial_proposal_lands_on_the_selected_words(self):
        # Qwen2.5-1.5B, AGENT-01 live trial (build/agent01_ui/model_trial): right words and offsets, paragraph 4 instead of 0, origin HUMAN
        live=edit(id=DOC,expected_revision=2,selection={'block':4,'start':4,'end':15,'text':'quick brown'},change={'bold':True},origin='HUMAN')
        verdict=M.decide(live,page())
        self.assertTrue(verdict['apply'],verdict);self.assertEqual(verdict['arguments']['selection'],SELECTED)
        self.assertEqual(verdict['arguments']['origin'],M.ORIGIN)
        self.assertTrue(any('paragraph 5' in n and 'your selection in paragraph 1 is used' in n for n in verdict['notes']),verdict['notes'])
        self.assertTrue(any('not HUMAN' in n for n in verdict['notes']),verdict['notes'])
        # both corrections are said aloud (words() puts them in Slate's sentence and on the card)
        self.assertEqual(verdict['corrections'],['the model named paragraph 5, words 4–15, which do not hold “quick brown”; your selection in paragraph 1 is used',
                                                 'recorded as Graphite’s model, not HUMAN'])

    def test_a_place_that_holds_the_quoted_words_is_kept_over_the_owners_selection(self):
        # “make the fox in the first paragraph bold” with the second paragraph's “fox” selected: the model's place holds
        # “fox”, so the edit lands there, not on the owner's selection (review finding, AGENT-02 fix pass)
        texts=['The quick brown fox jumps.','A second fox sleeps.'];owner={'block':1,'start':9,'end':12,'text':'fox'}
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection={'block':0,'start':16,'end':19,'text':'fox'},change={'bold':True}),M.page_of(DOC,2,2,1,owner,texts))
        self.assertTrue(verdict['apply'],verdict);self.assertEqual(verdict['arguments']['selection'],{'block':0,'start':16,'end':19,'text':'fox'})
        self.assertEqual((verdict['notes'],verdict['corrections']),([],[]))
        # the same words at offsets where they are not (a paragraph the page has): the owner's selection, said aloud
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection={'block':0,'start':10,'end':13,'text':'fox'},change={'bold':True}),M.page_of(DOC,2,2,1,owner,texts))
        self.assertTrue(verdict['apply'],verdict);self.assertEqual(verdict['arguments']['selection'],owner)
        self.assertEqual(verdict['corrections'],['the model named paragraph 1, words 10–13, which do not hold “fox”; your selection in paragraph 2 is used'])
        # without the page's words the paragraph count decides; the store checks the quoted words against the saved revision
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection={'block':0,'start':16,'end':19,'text':'fox'},change={'bold':True}),M.page_of(DOC,2,2,1,owner))
        self.assertEqual(verdict['arguments']['selection']['block'],0)
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection={'block':7,'start':16,'end':19,'text':'fox'},change={'bold':True}),M.page_of(DOC,2,2,1,owner))
        self.assertEqual(verdict['arguments']['selection'],owner);self.assertEqual(len(verdict['corrections']),1)
        # a model selection holding no words and quoting other words is not swapped for the owner's: it is refused
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection={'block':0,'start':3,'end':3,'text':'dog'},change={'bold':True}),M.page_of(DOC,2,2,1,owner,texts))
        self.assertFalse(verdict['apply'],verdict)

    def test_keeps_places_only_for_marks_clear_and_style(self):
        for change in ({'bold':True},{'italic':False,'underline':True},{'clear':True},{'style':'Heading2'},{'bold':True,'style':'Heading1'}):
            self.assertTrue(M.keeps_places(change),change)
        for change in ({'replace':'slow'},{'append':'x'},{'style':'Heading1','append':'x'},{'bold':True,'replace':'x'},{},None,'bold'):
            self.assertFalse(M.keeps_places(change),change)

    def test_missing_revision_id_and_selection_are_filled_from_the_page(self):
        verdict=M.decide(edit(change={'italic':True}),page())
        self.assertTrue(verdict['apply'],verdict)
        self.assertEqual((verdict['arguments']['id'],verdict['arguments']['expected_revision'],verdict['arguments']['selection']),(DOC,2,SELECTED))
        self.assertEqual(len(verdict['notes']),3)

    def test_a_paragraph_change_without_selection_uses_the_caret_paragraph(self):
        verdict=M.decide(edit(id=DOC,expected_revision=2,change={'style':'Heading2'}),page(selection=None,caret_block=0))
        self.assertTrue(verdict['apply'],verdict);self.assertEqual(verdict['arguments']['selection'],{'block':0,'start':0,'end':0})
        verdict=M.decide(edit(id=DOC,change={'append':'Total: 16 kg','append_style':'Normal'}),page(selection=None))
        self.assertTrue(verdict['apply'],verdict)

    def test_a_stale_revision_is_not_applied_and_says_so(self):
        verdict=M.decide(edit(id=DOC,expected_revision=1,selection=dict(SELECTED),change={'bold':True}),page(revision=3))
        self.assertFalse(verdict['apply']);self.assertIsNone(verdict['arguments'])
        self.assertIn('made for revision 1',verdict['reason']);self.assertIn('revision 3',verdict['reason']);self.assertIn('stale',verdict['reason'])

    def test_another_document_or_no_document_is_not_applied(self):
        self.assertIn('another document',M.decide(edit(id=OTHER,expected_revision=2,selection=dict(SELECTED),change={'bold':True}),page())['reason'])
        self.assertIn('no document is open',M.decide(edit(change={'bold':True}),{'document':None})['reason'])

    def test_other_operations_keep_the_review_words(self):
        for action in ({'operation':'files.find','arguments':{'text':'fox'}},{'operation':'agenda.add','arguments':{'title':'x'}},
                       {'operation':'documents.save','arguments':{'id':DOC,'expected_revision':2,'blocks':[]}}):
            verdict=M.decide(action,page());self.assertFalse(verdict['apply']);self.assertIn('waits for Run',verdict['reason'])
        self.assertFalse(M.decide('documents.edit',page())['apply']);self.assertFalse(M.decide({'operation':'documents.edit'},page())['apply'])

    def test_an_unknown_change_or_argument_is_not_applied(self):
        for change,words in (({'colour':'red'},'does not know'),({},'no change'),({'bold':'yes'},'on or off'),({'clear':False},'clear'),
                             ({'style':'Fancy'},'style'),({'replace':'two\nlines'},'one line'),({'append_style':'Code'},'does not add'),('bold','no change')):
            verdict=M.decide(edit(id=DOC,expected_revision=2,selection=dict(SELECTED),change=change),page())
            self.assertFalse(verdict['apply'],change);self.assertIn(words,verdict['reason'])
        self.assertIn('does not take',M.decide(edit(id=DOC,expected_revision=2,selection=dict(SELECTED),change={'bold':True},force=True),page())['reason'])

    def test_a_paragraph_the_page_does_not_have_or_words_that_are_not_there(self):
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection={'block':4,'start':0,'end':3,'text':'The'},change={'bold':True}),page(selection=None))
        self.assertFalse(verdict['apply']);self.assertIn('paragraph 5 and the page has 1',verdict['reason'])
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection={'block':0,'start':4,'end':9,'text':'slow!'},change={'bold':True}),page(selection=None))
        self.assertFalse(verdict['apply']);self.assertIn('not at that place',verdict['reason'])
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection={'block':0,'start':4,'end':99},change={'bold':True}),page(selection=None))
        self.assertFalse(verdict['apply']);self.assertIn('reaches past',verdict['reason'])
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection={'block':0,'start':9,'end':4},change={'bold':True}),page())
        self.assertFalse(verdict['apply']);self.assertIn('not a paragraph and two offsets',verdict['reason'])

    def test_words_changes_need_words(self):
        verdict=M.decide(edit(id=DOC,expected_revision=2,change={'bold':True}),page(selection=None))
        self.assertFalse(verdict['apply']);self.assertIn('no words are selected',verdict['reason'])
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection={'block':0,'start':3,'end':3},change={'underline':True}),page(selection=None))
        self.assertFalse(verdict['apply']);self.assertIn('select the words first',verdict['reason'])
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection={'block':0,'start':3,'end':3},change={'underline':True}),page())
        self.assertTrue(verdict['apply']);self.assertEqual(verdict['arguments']['selection'],SELECTED)   # “these words” are the owner's selection
        self.assertEqual(verdict['corrections'],['the model named no words; your selected words “quick brown” are used'])

    def test_quoted_words_are_bound_when_the_model_left_them_out(self):
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection={'block':0,'start':4,'end':15},change={'bold':True}),page())
        self.assertEqual(verdict['arguments']['selection']['text'],'quick brown')
        verdict=M.decide(edit(id=DOC,expected_revision=2,selection={'block':0,'start':0,'end':3},change={'bold':True}),page(selection=None))
        self.assertTrue(verdict['apply']);self.assertEqual(verdict['arguments']['selection']['text'],'The')

    def test_words_name_the_change_the_revision_undo_and_the_model(self):
        result={'document':{'revision':3},'applied':{'words':'made “quick brown” bold','block':0,'start':4,'end':15}}
        said=M.words(result,edit(),'bd5b55329ac2cfbd86bef1915ddf599c5f6a1cca484c156e00f54094308b0dae')
        self.assertEqual(said,'Changed on the page: made “quick brown” bold · revision 3 · Ctrl Z or “undo” takes it back · proposed by the model bd5b5532')
        self.assertTrue(M.words(result).endswith('proposed by the model'))
        self.assertIn('so Ctrl Z does not reach it',M.words(result,undoable=False))
        self.assertEqual(M.words(result,model_id='m',corrections=['one','two']),
                         'Changed on the page: made “quick brown” bold · revision 3 · Ctrl Z or “undo” takes it back · proposed by the model m · one; two')
        self.assertEqual(M.model_short('Qwen2.5 1.5B Instruct'),'Qwen2.5 1.5B Instruct')
        self.assertIn('Not applied by itself: it is stale.',M.not_applied_words({'reason':'it is stale'}))

    def test_request_words_and_changed_range(self):
        recorded=M.request_words('make the fox words bold','bd5b55329ac2cfbd86bef1915ddf599c5f6a1cca484c156e00f54094308b0dae')
        self.assertTrue(recorded.startswith('make the fox words bold'));self.assertLessEqual(len(M.request_words('x'*900,'a'*64)),D.MAX_REQUEST)
        if M.ORIGIN=='SLATE':self.assertTrue(recorded.endswith('proposed by the model bd5b5532'))
        self.assertEqual(M.changed_range({'applied':{'block':0,'start':4,'end':15}}),{'block':0,'start':4,'end':15})
        self.assertEqual(M.changed_range({'applied':{'block':2,'start':0,'end':0}}),{'block':2,'start':0,'end':None})
        self.assertEqual(M.changed_range({'applied':{'block':0,'start':0,'end':0,'appended_index':1}}),{'block':1,'start':0,'end':None})


class Page(unittest.TestCase):
    """DocumentsTab.apply_model_edit offscreen: the store, the undo stack, the fading wash, a stale proposal."""
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def open_page(self,text):
        """A DocumentsTab offscreen on a disposable store, holding ``text`` saved as revision 2; launch and submit held."""
        from PySide6.QtTest import QTest
        temporary=tempfile.TemporaryDirectory(prefix='ledger-model-turn-qt-');self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)/'workspace';root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(Path(temporary.name)/'profile')});env.start();self.addCleanup(env.stop)
        held=[patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')),patch.object(Kernel,'submit',side_effect=AssertionError('No job submission'))]
        for h in held:h.start();self.addCleanup(h.stop)
        kernel=Kernel(root)
        from workbench import document_qt as page_qt,engine
        engineering=patch.object(engine,'engineering',return_value=kernel);engineering.start();self.addCleanup(engineering.stop)
        class Session:state={}
        class Host:
            def __init__(self):self.root=root;self.session=Session();self.reading_profile=None;self.messages=[]
            def statusBar(self):
                host=self
                class Bar:
                    def showMessage(self,text,ms=0):host.messages.append(text)
                return Bar()
        host=Host();tab=page_qt.DocumentsTab(host);QTest.qWait(50)   # the first polish rebuilds the page (refont) before any edit
        tab.page.setPlainText(text);self.assertTrue(tab.flush());self.assertEqual(tab.revision,2)
        self.addCleanup(lambda:(tab.clear_flash(),tab.deleteLater()))
        def stored():return [(b['text'],b['style'],b['marks']) for b in kernel.dispatch('documents.get',{'id':tab.document_id},operator())['result']['document']['blocks']]
        return tab,host,stored

    def test_one_undo_takes_a_whole_combined_change_back(self):
        # review finding (AGENT-02 fix pass): a change with append was two undo steps, so “undo” left half of it saved
        # AGENT-02 integration (the live page trial): a change mixing kinds no longer applies by itself at all; it leaves the
        # page and the store as they were and waits for Run. A one-kind change with several keys is still one undo step.
        tab,host,stored=self.open_page('The quick brown fox.\nSecond line.')
        for change,selection in (({'style':'Heading1','append':'Added.'},{'block':0,'start':0,'end':0}),
                                 ({'replace':'slow','append':'Added.'},{'block':0,'start':4,'end':9,'text':'quick'}),
                                 ({'bold':True,'style':'Heading1'},{'block':0,'start':4,'end':9,'text':'quick'})):
            before=stored();revision=tab.revision
            said=tab.apply_model_edit({'id':tab.document_id,'expected_revision':revision,'selection':selection,'change':change},'combined')
            self.assertFalse(tab.model_edit['applied'],(change,said));self.assertIn('mixes several kinds of change',said)
            self.assertEqual(stored(),before,change);self.assertEqual(tab.revision,revision)
        from PySide6.QtGui import QTextCursor
        tab.page.setTextCursor(QTextCursor(tab.page.document().findBlockByNumber(1)))   # the owner is in paragraph 2
        cases=(({'append':'Third.','append_style':'Code'},{'block':1,'start':0,'end':0}),)   # one kind, two keys: one undo step
        for change,selection in cases:
            before=stored();revision=tab.revision
            said=tab.apply_model_edit({'id':tab.document_id,'expected_revision':revision,'selection':selection,'change':change},'combined')
            self.assertTrue(tab.model_edit['applied'] and tab.model_edit['undoable'],(change,said));self.assertIn('Ctrl Z or “undo” takes it back',said)
            self.assertNotEqual(stored(),before,change);self.assertEqual(tab.revision,revision+1)
            answer=tab.slate_request('undo');self.assertIn('Took the last change back (revision %d)'%(revision+2),answer)
            self.assertEqual(stored(),before,change);self.assertEqual(tab.revision,revision+2)

    def test_a_second_edit_of_the_same_proposal_follows_only_when_places_are_kept(self):
        # review finding (AGENT-02 fix pass): the second edit was moved onto the first one's revision even after a replace or
        # an append had shifted its paragraph or offsets, so it landed on the wrong paragraph or words
        from workbench.shell2 import SlateFace
        tab,host,stored=self.open_page('First paragraph.\nSecond paragraph.')
        host.tabs=type('Tabs',(),{'currentWidget':lambda _self:tab})()
        face=type('Face',(),{})();face.host=host
        def run(actions):
            chain={};return [SlateFace.apply_on_page(face,a,'m','r',chain) for a in actions]   # one proposal: one chain
        def act(revision,selection,change):return {'operation':'documents.edit','arguments':{'id':tab.document_id,'expected_revision':revision,'selection':selection,'change':change}}
        # append, then a paragraph style written for revision 2's paragraph 2: stale, not moved, the page keeps the heading off
        first,second=run([act(2,{'block':0,'start':0,'end':0},{'append':'Inserted line.'}),act(2,{'block':1,'start':0,'end':0},{'style':'Heading2'})])
        self.assertTrue(first['applied']);self.assertFalse(second['applied'])
        self.assertIn('made for revision 2 and the page is at revision 3 now, so it is stale',second['words']);self.assertIn('earlier edit in this proposal changed',second['words'])
        self.assertEqual(stored(),[('First paragraph.','Normal',[]),('Inserted line.','Normal',[]),('Second paragraph.','Normal',[])])
        # replace, then a mark by offsets alone (meaning “fox” at the revision the model saw): stale, no mark lands
        tab.page.setPlainText('The quick brown fox jumps.');self.assertTrue(tab.flush());revision=tab.revision
        first,second=run([act(revision,{'block':0,'start':4,'end':9,'text':'quick'},{'replace':'very slow'}),act(revision,{'block':0,'start':16,'end':19},{'bold':True})])
        self.assertTrue(first['applied']);self.assertFalse(second['applied']);self.assertEqual(stored(),[('The very slow brown fox jumps.','Normal',[])])
        # a missing revision on the second edit is the proposal's revision, not the page's newer one
        tab.page.setPlainText('The quick brown fox jumps.');self.assertTrue(tab.flush());revision=tab.revision
        later=act(revision,{'block':0,'start':16,'end':19},{'bold':True});del later['arguments']['expected_revision']
        first,second=run([act(revision,{'block':0,'start':4,'end':9,'text':'quick'},{'replace':'slow'}),later])
        self.assertTrue(first['applied']);self.assertFalse(second['applied']);self.assertEqual(stored(),[('The slow brown fox jumps.','Normal',[])])
        # marks only: places are kept, so the second edit follows onto the first one's revision and lands where it was meant;
        # the owner's selection (the second fox) does not pull the first fox's edit away from the first paragraph
        tab.page.setPlainText('The quick brown fox jumps.\nA second fox sleeps.');self.assertTrue(tab.flush());revision=tab.revision
        from PySide6.QtGui import QTextCursor
        block=tab.page.document().findBlockByNumber(1);cursor=tab.page.textCursor();cursor.setPosition(block.position()+9);cursor.setPosition(block.position()+12,QTextCursor.KeepAnchor);tab.page.setTextCursor(cursor)
        first,second=run([act(revision,{'block':0,'start':16,'end':19,'text':'fox'},{'bold':True}),act(revision,{'block':1,'start':9,'end':12,'text':'fox'},{'bold':True})])
        self.assertTrue(first['applied'] and second['applied'],(first['words'],second['words']));self.assertEqual(tab.revision,revision+2)
        self.assertEqual(stored(),[('The quick brown fox jumps.','Normal',[{'start':16,'end':19,'bold':True}]),('A second fox sleeps.','Normal',[{'start':9,'end':12,'bold':True}])])
        self.assertNotIn('your selection',first['words'])

    def test_a_model_edit_lands_visibly_and_undoes(self):
        from PySide6.QtGui import QTextCursor
        from PySide6.QtTest import QTest
        temporary=tempfile.TemporaryDirectory(prefix='ledger-model-turn-qt-');self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)/'workspace';root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(Path(temporary.name)/'profile')});env.start();self.addCleanup(env.stop)
        held=[patch.object(Kernel,'launch',side_effect=AssertionError('No worker launch')),patch.object(Kernel,'submit',side_effect=AssertionError('No job submission'))]
        for h in held:h.start();self.addCleanup(h.stop)
        kernel=Kernel(root)
        from workbench import document_qt as page_qt,engine
        class Session:state={}
        class Host:
            def __init__(self):self.root=root;self.session=Session();self.reading_profile=None;self.messages=[]
            def statusBar(self):
                host=self
                class Bar:
                    def showMessage(self,text,ms=0):host.messages.append(text)
                return Bar()
        host=Host()
        with patch.object(engine,'engineering',return_value=kernel):
            tab=page_qt.DocumentsTab(host);ident=tab.document_id;QTest.qWait(50)   # the first polish rebuilds the page (refont) before any edit
            tab.page.setPlainText('');tab.page.insertPlainText(TEXT);self.assertTrue(tab.flush());self.assertEqual(tab.revision,2)
            cursor=tab.page.textCursor();cursor.setPosition(4);cursor.setPosition(15,QTextCursor.KeepAnchor);tab.page.setTextCursor(cursor)
            self.assertEqual(tab.model_page()['selection'],SELECTED);self.assertEqual(tab.model_page()['texts'],[TEXT])
            hint=tab.slate_context().split('\n')[-1]
            self.assertTrue(hint.startswith('To change this page use documents.edit with id %s, expected_revision 2'%ident),hint);self.assertLess(len(hint),200)
            live={'id':ident,'expected_revision':2,'selection':{'block':4,'start':4,'end':15,'text':'quick brown'},'change':{'bold':True},'origin':'HUMAN'}
            said=tab.apply_model_edit(live,'make the fox words bold','bd5b55329ac2cfbd86bef1915ddf599c5f6a1cca484c156e00f54094308b0dae')
            self.assertEqual(said,'Changed on the page: made “quick brown” bold · revision 3 · Ctrl Z or “undo” takes it back · proposed by the model bd5b5532'
                                  ' · the model named paragraph 5, words 4–15, which do not hold “quick brown”; your selection in paragraph 1 is used; recorded as Graphite’s model, not HUMAN')
            stored=kernel.dispatch('documents.get',{'id':ident},operator())['result']
            self.assertEqual(stored['document']['blocks'][0]['marks'],[{'start':4,'end':15,'bold':True}])
            self.assertEqual(stored['document']['last_change']['actor'],M.ORIGIN);self.assertTrue(stored['document']['last_change']['request'].startswith('make the fox words bold'))
            self.assertEqual(stored['events'][0]['action'],'DOCUMENT_EDITED_BY_'+M.ORIGIN)
            self.assertEqual(page_qt.from_qt(tab.page.document())[0]['marks'],[{'start':4,'end':15,'bold':True}]);self.assertEqual(tab.revision,3);self.assertFalse(tab.dirty)
            # the wash: an ExtraSelection over the changed words, never a format in the document, gone after about 1.5 s
            washes=tab.page.extraSelections();self.assertEqual(len(washes),1)
            self.assertEqual((washes[0].cursor.selectionStart(),washes[0].cursor.selectionEnd()),(4,15))
            self.assertEqual(tab.flash_record[-1]['range'],[4,15]);self.assertNotIn('background',str(stored['document']['blocks'][0]))
            QTest.qWait(page_qt.FLASH_MS+400);self.assertEqual(tab.page.extraSelections(),[]);self.assertTrue(tab.flash_record[-1]['cleared'])
            # one undo stack: “undo” typed to Slate takes the model's change back as a new revision
            answer=tab.slate_request('undo');self.assertIn('Took the last change back',answer)
            stored=kernel.dispatch('documents.get',{'id':ident},operator())['result']['document'];self.assertEqual((stored['blocks'][0]['marks'],stored['revision']),([],4))
            # a proposal made for an older revision is not applied, and the page is not touched
            said=tab.apply_model_edit({'id':ident,'expected_revision':2,'selection':dict(SELECTED),'change':{'italic':True}},'italic please')
            self.assertTrue(said.startswith('Not applied by itself: it was made for revision 2 and the page is at revision 4'),said)
            self.assertEqual(kernel.dispatch('documents.get',{'id':ident},operator())['result']['document']['revision'],4)
            # a paragraph added after the selected one lands through the undo stack too (same block ids as the store)
            said=tab.apply_model_edit({'id':ident,'expected_revision':4,'selection':{'block':0,'start':0,'end':0},'change':{'append':'It slept.'}},'add a line')
            self.assertIn('added the paragraph “It slept.” after paragraph 1',said);self.assertEqual(tab.page.toPlainText(),TEXT+'\nIt slept.')
            self.assertTrue(tab.page.document().isUndoAvailable());self.assertEqual(tab.revision,5)
            self.assertEqual(tab.block_ids,[b['id'] for b in kernel.dispatch('documents.get',{'id':ident},operator())['result']['document']['blocks']])



class StoreReadback(unittest.TestCase):
    """AGENT-02 integration: a model-proposed edit is stored as the model's (origin SLATE_MODEL on documents.edit alone), reads
    back basis MODEL_PROPOSAL_CHECKED_AND_APPLIED with model_used True, and completes its PROPOSED row in the instruction matrix."""

    def setUp(self):
        import os, tempfile
        from pathlib import Path
        from unittest.mock import patch
        from workbench.engineering_kernel import Kernel, operator
        temporary = tempfile.TemporaryDirectory(prefix='ledger-model-turn-store-'); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'workspace'; self.root.mkdir()
        env = patch.dict(os.environ, {'ARC1_WORKBENCH_CONFIG_HOME': str(Path(temporary.name) / 'profile')}); env.start(); self.addCleanup(env.stop)
        for name in ('launch', 'submit'):
            held = patch.object(Kernel, name, side_effect=AssertionError('no job in this test')); held.start(); self.addCleanup(held.stop)
        self.kernel = Kernel(self.root); self.owner = operator('owner')

    def call(self, op, args):
        r = self.kernel.dispatch(op, args, self.owner)
        self.assertTrue(r['ok'], r.get('error')); return r['result']

    def test_origin_readback_and_matrix_link(self):
        from workbench import documents, instruction_matrix, model_turn
        self.assertEqual(documents.ORIGINS, ('HUMAN', 'SLATE', 'IMPORTED'))          # create and save keep their origins
        self.assertIn('SLATE_MODEL', documents.EDIT_ORIGINS); self.assertEqual(model_turn.ORIGIN, 'SLATE_MODEL')
        doc = self.call('documents.create', {'title': 'Fox', 'text': 'The quick brown fox.'})   # the record itself
        refused = self.kernel.dispatch('documents.save', {'id': doc['id'], 'expected_revision': doc['revision'], 'blocks': doc['blocks'], 'origin': 'SLATE_MODEL'}, self.owner)
        self.assertFalse(refused['ok'])                                                 # only documents.edit takes the model origin
        action = {'operation': 'documents.edit', 'arguments': {'id': doc['id'], 'expected_revision': doc['revision'],
                  'selection': {'block': 0, 'start': 4, 'end': 15, 'text': 'quick brown'}, 'change': {'bold': True}}}
        instruction_matrix.propose(self.kernel, self.owner.identity, 'make quick brown bold', [action], 'model-id')
        page = model_turn.page_of(doc['id'], doc['revision'], len(doc['blocks']), 0, None, [b['text'] for b in doc['blocks']])
        verdict = model_turn.decide(action, page); self.assertTrue(verdict['apply'], verdict)
        out = self.call('documents.edit', {**verdict['arguments'], 'origin': model_turn.ORIGIN, 'request': 'make quick brown bold'})
        self.assertEqual((out['actor'], out['basis'], out['model_used']), ('SLATE_MODEL', 'MODEL_PROPOSAL_CHECKED_AND_APPLIED', True))
        direct = self.call('documents.edit', {'id': doc['id'], 'expected_revision': out['document']['revision'], 'selection': {'block': 0, 'start': 16, 'end': 19, 'text': 'fox'},
                                              'change': {'italic': True}, 'origin': 'SLATE'})
        self.assertEqual((direct['basis'], direct['model_used']), ('EXPLICIT_RULES_NO_MODEL', False))   # the rule route reads as before
        with self.kernel.db() as db:
            rows = db.execute("SELECT outcome,reason FROM instruction_matrix WHERE owner=? AND operation='documents.edit'", (self.owner.identity,)).fetchall()
        self.assertEqual([tuple(r) for r in rows], [('SUCCESS', 'applied on the page')])   # the proposal completed; the rule edit added no row


class LiveTrialShapes(unittest.TestCase):
    """AGENT-02: the exact change objects Qwen2.5 1.5B and 0.5B proposed in the live page trial (build/agent02_ui/model_trial).
    Under schema-constrained decoding they filled every optional key; none of these may delete or add words by itself."""
    TEXTS = ['The quick brown fox jumps over the lazy dog.', 'A second paragraph about the crate: 12.5 kg, 3 kg and 0.5 kg.', 'Third paragraph, plain words.']

    def page(self, selection=None):
        from workbench import model_turn
        return model_turn.page_of('a' * 32, 1, 3, 0, selection, self.TEXTS)

    def action(self, change, selection, origin=None):
        args = {'id': 'a' * 32, 'expected_revision': 1, 'selection': selection, 'change': change}
        if origin: args['origin'] = origin
        return {'operation': 'documents.edit', 'arguments': args}

    def test_the_1_5b_bold_proposal_no_longer_deletes_the_words(self):
        from workbench import model_turn
        sel = {'block': 0, 'start': 4, 'end': 15, 'text': 'quick brown'}
        live = {'bold': True, 'italic': False, 'underline': False, 'style': 'Normal', 'replace': '', 'append': '', 'append_style': 'Normal'}
        verdict = model_turn.decide(self.action(live, sel, 'HUMAN'), self.page(sel))
        self.assertFalse(verdict['apply']); self.assertIn('mixes several kinds of change (marks, replace)', verdict['reason'])
        tidy, dropped = model_turn.tidy_change(live, 'quick brown')
        self.assertEqual(tidy, {'bold': True, 'replace': ''}); self.assertEqual(len(dropped), 3)

    def test_the_0_5b_replace_proposal_waits_for_run(self):
        from workbench import model_turn
        sel = {'block': 0, 'start': 35, 'end': 39, 'text': 'lazy'}
        live = {'bold': True, 'italic': True, 'underline': True, 'style': 'Normal', 'replace': 'Normal', 'append': 'Normal'}
        verdict = model_turn.decide(self.action(live, {'block': 35, 'start': 35, 'end': 39, 'text': 'lazy'}), self.page(sel))
        self.assertFalse(verdict['apply']); self.assertIn('mixes several kinds of change', verdict['reason'])

    def test_one_kind_still_applies_and_says_what_was_set_aside(self):
        from workbench import model_turn
        sel = {'block': 0, 'start': 4, 'end': 15, 'text': 'quick brown'}
        verdict = model_turn.decide(self.action({'bold': True, 'italic': False, 'style': 'Normal', 'append': ''}, sel), self.page(sel))
        self.assertTrue(verdict['apply'], verdict); self.assertEqual(verdict['arguments']['change'], {'bold': True})
        self.assertTrue(any(c.startswith('set aside: ') for c in verdict['corrections']), verdict['corrections'])
        replaced = model_turn.decide(self.action({'replace': 'sleepy'}, {'block': 0, 'start': 35, 'end': 39, 'text': 'lazy'}), self.page())
        self.assertTrue(replaced['apply'], replaced); self.assertEqual(replaced['arguments']['change'], {'replace': 'sleepy'})
        nothing = model_turn.decide(self.action({'replace': 'quick brown', 'append': ''}, sel), self.page(sel))
        self.assertFalse(nothing['apply']); self.assertIn('changes nothing', nothing['reason'])
        delete = model_turn.decide(self.action({'replace': ''}, {'block': 0, 'start': 35, 'end': 39, 'text': 'lazy'}), self.page())
        self.assertFalse(delete['apply']); self.assertIn('delete words you did not select', delete['reason'])

    def test_a_style_the_paragraph_already_has_is_no_change(self):
        # the 1.5B model, after the fix, kept proposing {style: Normal} for body text; Slate must not report it as a change
        from workbench import model_turn
        sel = {'block': 0, 'start': 4, 'end': 15, 'text': 'quick brown'}
        page = model_turn.page_of('a' * 32, 1, 3, 0, sel, self.TEXTS, ['Normal', 'Normal', 'Heading1'])
        same = model_turn.decide(self.action({'style': 'Normal'}, sel), page)
        self.assertFalse(same['apply']); self.assertIn('paragraph 1 is already body text', same['reason'])
        heading = model_turn.decide(self.action({'style': 'Heading1'}, {'block': 0, 'start': 0, 'end': 0}), page)
        self.assertTrue(heading['apply'], heading)
        back = model_turn.decide(self.action({'style': 'Normal'}, {'block': 2, 'start': 0, 'end': 0}),
                                 model_turn.page_of('a' * 32, 1, 3, 2, None, self.TEXTS, ['Normal', 'Normal', 'Heading1']))
        self.assertTrue(back['apply'], back)   # a heading made body text again is a real change

    def test_the_model_is_offered_one_kind_of_change_and_no_origin(self):
        from workbench import local_brain
        page = ('make the words bold\n\n(About the open item: document “Fox” (id ' + 'a' * 32 + ', revision 1) · no words selected · caret in paragraph 1 '
                '(block index 0)\n' + local_brain.PAGE_HINT + ' with id ' + 'a' * 32 + ', expected_revision 1, selection {block, start, end, text} and change {bold}.)')
        schema, reference, chosen = local_brain.proposal_profile(page)   # only a request about an open page is offered the edit
        form = reference['documents.edit']
        self.assertNotIn('origin', form['properties']); self.assertNotIn('request', form['properties'])
        kinds = form['properties']['change']['oneOf']
        self.assertEqual(len(kinds), 7)   # bold, italic, underline, style, replace, append, clear: one each, that one required
        for kind in kinds:
            self.assertFalse(kind['additionalProperties']); self.assertEqual(len(kind['required']), 1)
        for key in ('replace', 'append'):
            form_of = next(k for k in kinds if k['required'] == [key])
            self.assertEqual(form_of['properties'][key]['minLength'], 1)   # a deletion never comes from the model's form
        variant = next(v for v in schema['properties']['actions']['items']['oneOf'] if v['properties']['operation'].get('const') == 'documents.edit')
        self.assertEqual(variant['properties']['arguments'], form)


class ReviewOfTheFix(unittest.TestCase):
    """AGENT-02: the independent review of the live-trial fix found these, measured with the small models; each must wait for Run."""
    TEXTS = LiveTrialShapes.TEXTS + ['Fourth paragraph.']

    def page(self, selection=None, caret=0):
        from workbench import model_turn
        return model_turn.page_of('a' * 32, 1, 4, caret, selection, self.TEXTS, ['Normal'] * 4)

    def action(self, change, selection):
        return {'operation': 'documents.edit', 'arguments': {'id': 'a' * 32, 'expected_revision': 1, 'selection': selection, 'change': change}}

    def test_words_other_than_the_owners_selection_are_never_deleted_or_replaced_by_themselves(self):
        from workbench import model_turn
        lazy = {'block': 0, 'start': 35, 'end': 39, 'text': 'lazy'}; quick = {'block': 0, 'start': 4, 'end': 15, 'text': 'quick brown'}
        for change in ({'replace': ''}, {'replace': ' '}, {'replace': 'sleepy'}):
            copied = model_turn.decide(self.action(change, quick), self.page(lazy))       # a worked example's selection, copied
            self.assertFalse(copied['apply'], (change, copied))
            offsets = model_turn.decide(self.action(change, {'block': 1, 'start': 35, 'end': 39}), self.page(lazy))
            self.assertFalse(offsets['apply'], (change, offsets))
        blank = model_turn.decide(self.action({'replace': ' '}, {'block': 2, 'start': 0, 'end': 5, 'text': 'Third'}), self.page())
        self.assertFalse(blank['apply'])                                                      # whitespace is a deletion too
        own = model_turn.decide(self.action({'replace': ''}, lazy), self.page(lazy))
        self.assertTrue(own['apply'], own)                                                    # the owner's own words may go
        mine = model_turn.decide(self.action({'replace': 'sleepy'}, lazy), self.page(lazy))
        self.assertTrue(mine['apply'], mine)

    def test_one_mark_at_a_time(self):
        from workbench import model_turn
        lazy = {'block': 0, 'start': 35, 'end': 39, 'text': 'lazy'}
        for change in ({'bold': True, 'italic': True, 'underline': True}, {'bold': False, 'italic': False, 'underline': False}):
            verdict = model_turn.decide(self.action(change, lazy), self.page(lazy))
            self.assertFalse(verdict['apply']); self.assertIn('several marks at once', verdict['reason'])
        self.assertTrue(model_turn.decide(self.action({'bold': False}, lazy), self.page(lazy))['apply'])

    def test_a_paragraph_change_belongs_to_the_owners_paragraph(self):
        from workbench import model_turn
        for change in ({'style': 'Heading1'}, {'append': 'Total: 16 kg'}):
            wrong = model_turn.decide(self.action(change, {'block': 3, 'start': 0, 'end': 0}), self.page(caret=2))
            self.assertFalse(wrong['apply']); self.assertIn('you are in paragraph 3', wrong['reason'])
            right = model_turn.decide(self.action(change, {'block': 2, 'start': 0, 'end': 0}), self.page(caret=2))
            self.assertTrue(right['apply'], right)

    def test_a_page_request_fits_the_default_context(self):
        import json
        from workbench import local_brain
        message = ('Make the words I picked stand out.\n\n(About the open item: document “Fox page” (id ' + 'a' * 32 + ', revision 2) · selected words '
                   '4–15 of paragraph 1 (block index 0): “quick brown”\nTo change this page use documents.edit with id ' + 'a' * 32 +
                   ', expected_revision 2, selection {block, start, end, text} and change {bold|italic|underline|style|replace|append}.)')
        schema, reference, chosen = local_brain.proposal_profile(message)
        self.assertEqual(list(reference)[:2], ['documents.get', 'documents.edit']); self.assertLessEqual(len(chosen), 2)
        # about 3.3 characters per token for this JSON: under ~900 tokens of schema leaves room in 2,048 for the rest and the answer
        self.assertLess(len(json.dumps(reference, separators=(',', ':'))), 3000)


if __name__=='__main__':unittest.main()
