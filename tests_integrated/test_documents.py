"""Documents: the shared page's store, its revision binding, Slate's rule-based edits and the Qt page round trip.

Nothing here starts a model, a worker or a job: the direct edits are explicit rules, and the Qt part runs offscreen.
"""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import documents as D,cabinet,explore
from workbench.engineering_kernel import Kernel,operator,CAPABILITIES
from workbench.engineering_cli import schemas

PROGRAM=Path(__file__).resolve().parents[1]
OPERATIONS=('documents.create','documents.list','documents.get','documents.save','documents.edit','documents.interpret','documents.render')


class Model(unittest.TestCase):
    def test_marks_normalise_to_sorted_runs_and_union_overlaps(self):
        marks=[{'start':10,'end':19,'italic':True},{'start':4,'end':15,'bold':True},{'start':2,'end':2,'bold':True},{'start':5,'end':6,'bold':False}]
        self.assertEqual(D.normalize_marks(marks,30),[{'start':4,'end':10,'bold':True},{'start':10,'end':15,'bold':True,'italic':True},{'start':15,'end':19,'italic':True}])
        self.assertEqual(D.normalize_marks([{'start':0,'end':3,'bold':True},{'start':3,'end':6,'bold':True}],6),[{'start':0,'end':6,'bold':True}])
        for bad in ([{'start':0,'end':40,'bold':True}],[{'start':3,'end':2,'bold':True}],[{'start':0,'end':2,'colour':'red'}],[{'start':0,'end':2,'bold':'yes'}],'x'):
            with self.assertRaises(ValueError):D.normalize_marks(bad,30)

    def test_blocks_keep_ids_and_refuse_breaks_and_unknown_styles(self):
        rows=D.normalize_blocks([{'text':'One','style':'Heading1'},{'text':'Two'}])
        self.assertEqual([r['style'] for r in rows],['Heading1','Normal']);self.assertTrue(all(len(r['id'])==32 for r in rows))
        self.assertEqual(len(D.normalize_blocks([])),1);self.assertEqual(D.normalize_blocks([])[0]['text'],'')
        for bad in ([{'text':'a\nb'}],[{'text':'a','style':'Fancy'}],[{'text':1}],[{'text':'a','id':'short'}],[{'id':'a'*32,'text':'a'},{'id':'a'*32,'text':'b'}]):
            with self.assertRaises(ValueError):D.normalize_blocks(bad)

    def test_apply_change_binds_the_quoted_words(self):
        blocks=D.normalize_blocks(D.from_text('The quick brown fox jumps.'))
        out,applied=D.apply_change(blocks,{'block':0,'start':4,'end':15,'text':'quick brown'},{'bold':True})
        self.assertEqual(out[0]['marks'],[{'start':4,'end':15,'bold':True}]);self.assertEqual(applied['words'],'made “quick brown” bold')
        with self.assertRaisesRegex(ValueError,'SELECTION_CHANGED'):D.apply_change(blocks,{'block':0,'start':4,'end':15,'text':'quick brawn'},{'bold':True})
        with self.assertRaisesRegex(ValueError,'SELECTION_CHANGED'):D.apply_change(blocks,{'block':3,'start':0,'end':1},{'bold':True})
        with self.assertRaisesRegex(ValueError,'SELECTION_CHANGED'):D.apply_change(blocks,{'block':0,'start':0,'end':99},{'bold':True})
        with self.assertRaisesRegex(ValueError,'SELECTION_REQUIRED'):D.apply_change(blocks,{'block':0,'start':3,'end':3},{'bold':True})
        with self.assertRaises(ValueError):D.apply_change(blocks,{'block':0,'start':0,'end':3},{'colour':'red'})
        out,_=D.apply_change(out,{'block':0,'start':10,'end':15,'text':'brown'},{'bold':False})
        self.assertEqual(out[0]['marks'],[{'start':4,'end':10,'bold':True}])
        out,applied=D.apply_change(out,{'block':0,'start':0,'end':0},{'style':'Heading2'})
        self.assertEqual(out[0]['style'],'Heading2');self.assertEqual(applied['words'],'made the paragraph a subheading')
        out,applied=D.apply_change(out,{'block':0,'start':4,'end':9,'text':'quick'},{'replace':'slow and steady'})
        self.assertEqual(out[0]['text'],'The slow and steady brown fox jumps.');self.assertEqual(applied['end'],4+len('slow and steady'))
        self.assertEqual(out[0]['marks'],[{'start':19,'end':20,'bold':True}])  # the bold space after the replaced word is still there, shifted
        out,_=D.apply_change(out,{'block':0,'start':0,'end':3,'text':'The'},{'italic':True,'underline':True})
        self.assertEqual(out[0]['marks'][0],{'start':0,'end':3,'italic':True,'underline':True})
        out,_=D.apply_change(out,{'block':0,'start':0,'end':3,'text':'The'},{'clear':True});self.assertEqual(out[0]['marks'],[{'start':19,'end':20,'bold':True}])

    def test_render_keeps_words_and_marks(self):
        doc={'title':'Page','blocks':D.normalize_blocks([{'text':'The quick fox','marks':[{'start':4,'end':9,'bold':True}]},{'text':'x = 1','style':'Code'},{'text':'Sub','style':'Heading2'}])}
        self.assertIn('The **quick** fox',D.render({'title':'P','blocks':D.normalize_blocks([{'text':'The quick fox','marks':[{'start':4,'end':10,'bold':True}]}])},'markdown'))  # the space stays outside the markers
        md=D.render(doc,'markdown');self.assertIn('The **quick** fox',md);self.assertIn('```\nx = 1\n```',md);self.assertIn('### Sub',md)
        html=D.render(doc,'html');self.assertIn('<strong>quick</strong>',html);self.assertIn('<pre>x = 1</pre>',html);self.assertIn('<h3>Sub</h3>',html)
        self.assertEqual(D.render(doc,'plain'),'The quick fox\nx = 1\nSub')
        with self.assertRaises(ValueError):D.render(doc,'pdf')


class Interpreter(unittest.TestCase):
    def reading(self,text,selected=None):
        value=D.interpret(text,selected);return (value['change'],value['needs_selection']) if value['recognized'] else None

    def test_formatting_requests_resolve_without_a_model(self):
        self.assertEqual(self.reading('make these words bold'),({'bold':True},True))
        self.assertEqual(self.reading('Bold, please.'),({'bold':True},True))
        self.assertEqual(self.reading('italic and underline'),({'italic':True,'underline':True},True))
        self.assertEqual(self.reading('make it a heading'),({'style':'Heading1'},False))
        self.assertEqual(self.reading('heading 2'),({'style':'Heading2'},False))
        self.assertEqual(self.reading('heading level three'),({'style':'Heading3'},False))
        self.assertEqual(self.reading('make this the title'),({'style':'Heading1'},False))
        self.assertEqual(self.reading('body text'),({'style':'Normal'},False))
        self.assertEqual(self.reading('as code'),({'style':'Code'},False))
        self.assertEqual(self.reading('plain'),({'clear':True},True))
        self.assertEqual(self.reading('clear the formatting'),({'clear':True},True))
        self.assertEqual(self.reading('remove bold'),({'bold':False},True))
        self.assertEqual(self.reading('unbold'),({'bold':False},True))
        self.assertEqual(self.reading('not italic'),({'italic':False},True))
        self.assertEqual(D.interpret('remove bold')['words'],'remove bold from the selection')
        self.assertEqual(D.interpret('make these words bold')['words'],'make the selection bold')
        self.assertEqual(D.interpret('make it a heading')['basis'],'EXPLICIT_RULES_NO_MODEL')

    def test_unknown_words_leave_the_request_to_the_model(self):
        for text in ('write a poem about foxes','capitalise it','bold the second sentence and fix the grammar','summarise this','','x'*500,'make it better'):
            self.assertIsNone(self.reading(text),text)

    def test_replace_narrows_to_the_words_inside_the_selection(self):
        value=D.interpret('replace fox with cat','the quick brown fox')
        self.assertEqual((value['change'],value['narrow'],value['needs_selection']),({'replace':'cat'},(16,19),True))
        value=D.interpret('change "quick brown" to slow','the quick brown fox');self.assertEqual(value['narrow'],(4,15))
        value=D.interpret('replace dog with cat','the quick brown fox');self.assertTrue(value['recognized']);self.assertIn('do not contain',value['problem'])
        value=D.interpret('replace fox with cat');self.assertTrue(value['recognized']);self.assertIsNone(value['narrow'])


class Store(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ledger-documents-');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(Path(temporary.name)/'profile')});env.start();self.addCleanup(env.stop)
        self.kernel=Kernel(self.root);self.owner=operator('owner')
        launch=patch.object(Kernel,'launch',side_effect=AssertionError('no worker'));launch.start();self.addCleanup(launch.stop)
        submit=patch.object(Kernel,'submit',side_effect=AssertionError('no job'));submit.start();self.addCleanup(submit.stop)

    def call(self,op,args=None,principal=None):
        r=self.kernel.dispatch(op,args or {},principal or self.owner);self.assertTrue(r['ok'],r);return r['result']

    def refused(self,op,args,principal=None):
        r=self.kernel.dispatch(op,args,principal or self.owner);self.assertFalse(r['ok']);return r['error']['message']

    def test_the_seven_document_operations_their_scopes_and_privacy(self):
        self.assertEqual(sorted(op for op in CAPABILITIES if op.startswith('documents.')),sorted(OPERATIONS))
        self.assertEqual({op:CAPABILITIES[op] for op in OPERATIONS},{'documents.create':'execute','documents.list':'read','documents.get':'read','documents.save':'execute','documents.edit':'execute','documents.interpret':'read','documents.render':'read'})
        definitions=schemas()
        for op in OPERATIONS:self.assertIn(op,definitions)
        from workbench import activity,stacy_control,ledger_control
        self.assertTrue({'documents.list','documents.get','documents.interpret','documents.render'}<=activity.OBSERVER_OPERATIONS)
        self.assertNotIn('documents.edit',activity.OBSERVER_OPERATIONS)
        self.assertTrue(stacy_control.cloud_private('documents.get',{'id':'a'*32}))
        self.assertIn('documents',ledger_control.DESTINATIONS);self.assertIn('documents',definitions['ledger.navigate']['properties']['destination']['enum'])

    def test_create_save_edit_and_history_round_trip(self):
        doc=self.call('documents.create',{'title':'Fox page','text':'The quick brown fox.\nSecond line.'})
        self.assertEqual((doc['revision'],doc['title'],len(doc['blocks']),doc['kind'],doc['document_schema']),(1,'Fox page',2,'document',D.SCHEMA))
        edited=self.call('documents.edit',{'id':doc['id'],'expected_revision':1,'selection':{'block':0,'start':4,'end':15,'text':'quick brown'},'change':{'bold':True},'origin':'SLATE','request':'make these words bold'})
        self.assertEqual(edited['document']['revision'],2);self.assertEqual(edited['document']['blocks'][0]['marks'],[{'start':4,'end':15,'bold':True}])
        self.assertEqual((edited['actor'],edited['model_used'],edited['basis']),('SLATE',False,'EXPLICIT_RULES_NO_MODEL'))
        self.assertEqual(edited['document']['last_change']['request'],'make these words bold')
        self.assertIn('REVISION_CHANGED',self.refused('documents.edit',{'id':doc['id'],'expected_revision':1,'selection':{'block':0,'start':4,'end':15},'change':{'italic':True}}))
        self.assertIn('SELECTION_CHANGED',self.refused('documents.edit',{'id':doc['id'],'expected_revision':2,'selection':{'block':0,'start':4,'end':15,'text':'other words'},'change':{'italic':True}}))
        blocks=edited['document']['blocks']+[{'text':'Third','style':'Code','marks':[]}]
        saved=self.call('documents.save',{'id':doc['id'],'expected_revision':2,'blocks':blocks,'title':'Renamed'})
        self.assertTrue(saved['saved']);self.assertEqual((saved['document']['revision'],saved['document']['title'],len(saved['document']['blocks'])),(3,'Renamed',3))
        self.assertEqual(saved['document']['blocks'][0]['id'],doc['blocks'][0]['id'])  # ids survive a save
        again=self.call('documents.save',{'id':doc['id'],'expected_revision':3,'blocks':saved['document']['blocks']});self.assertEqual((again['saved'],again['reason']),(False,'UNCHANGED'))
        self.assertIn('REVISION_CHANGED',self.refused('documents.save',{'id':doc['id'],'expected_revision':1,'blocks':[{'text':'late'}]}))
        got=self.call('documents.get',{'id':doc['id']});self.assertEqual(got['summary']['revision'],3);self.assertEqual(got['plain'],'The quick brown fox.\nSecond line.\nThird')
        self.assertEqual([e['action'] for e in got['events']][:3],['DOCUMENT_SAVED','DOCUMENT_EDITED_BY_SLATE','DOCUMENT_CREATED'])
        rows=self.call('documents.list',{})['documents'];self.assertEqual([r['title'] for r in rows],['Renamed']);self.assertEqual(rows[0]['words'],7)
        md=self.call('documents.render',{'id':doc['id'],'format':'markdown'})['text'];self.assertIn('The **quick brown** fox.',md)
        self.assertEqual(self.refused('documents.get',{'id':doc['id']},operator('someone-else')),'Project Desk record unavailable to this caller')
        self.assertEqual(self.call('documents.interpret',{'text':'make these words bold'})['change'],{'bold':True})

    def test_untitled_documents_take_their_first_words(self):
        doc=self.call('documents.create',{'text':'A thought about ostriches\nmore'});self.assertEqual(doc['title'],'A thought about ostriches')
        empty=self.call('documents.create',{});self.assertEqual((empty['title'],empty['blocks'][0]['text']),('Untitled document',''))
        saved=self.call('documents.save',{'id':empty['id'],'expected_revision':1,'blocks':[{'text':'Now it says something'}]});self.assertEqual(saved['document']['title'],'Now it says something')

    def test_documents_file_in_the_cabinet_and_the_doorway(self):
        project=self.call('projects.create',{'title':'Ostrich','intent':'Keep the bird alive.'})
        doc=self.call('documents.create',{'title':'Feeding notes','project':project['id']})
        nodes={n['id']:n for n in cabinet.snapshot(self.kernel,self.owner)['nodes']}
        node=nodes['document:'+doc['id']];self.assertEqual((node['label'],node['role'],node['target']['record_kind']),('Feeding notes','document','document'))
        self.assertEqual(nodes[node['parent']]['label'],'Documents');self.assertEqual(node['canonical_home'],'project:'+project['id'])
        detail=cabinet.get(self.kernel,'document:'+doc['id'],self.owner);self.assertEqual(detail['record']['title'],'Feeding notes')
        self.assertEqual([v[0] for v in explore.VIEWS if v[0]=='documents'],['documents'])
        row=next(v for v in explore.VIEWS if v[0]=='documents');self.assertEqual((row[3],row[5],row[6],row[7],row[9]),('Work','document_qt.py','DocumentsTab',('documents.',),'workspace'))
        self.assertEqual(explore.suggestions({'role':'document','id':'document:x'})[0]['id'],'documents')
        self.assertEqual(explore.suggestions({'role':'idea','id':'idea:x'})[0]['id'],'documents')
        self.assertEqual(cabinet.DESK_OPS['document'],'documents.get')


class Page(unittest.TestCase):
    """The Qt page: load, edit, read back, Slate's turn through the same undo stack. Offscreen, no window chrome."""
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def test_model_and_page_agree_both_ways(self):
        from PySide6.QtGui import QFont,QTextDocument
        from workbench import document_qt as page
        prose=QFont('DejaVu Sans',12);code=QFont('DejaVu Sans Mono',11)
        doc={'blocks':D.normalize_blocks([{'text':'The quick brown fox','marks':[{'start':4,'end':15,'bold':True},{'start':10,'end':19,'italic':True}]},{'text':'print(1)','style':'Code'},{'text':'','style':'Normal'},{'text':'Title','style':'Heading1'}])}
        text_document=QTextDocument();page.to_qt(doc,text_document,prose,code)
        self.assertEqual(text_document.blockCount(),4);self.assertFalse(text_document.isUndoAvailable())
        back=page.from_qt(text_document,[b['id'] for b in doc['blocks']])
        self.assertEqual(back,doc['blocks'])

    def test_slate_turn_lands_in_the_store_and_the_undo_stack(self):
        from PySide6.QtGui import QTextCursor
        temporary=tempfile.TemporaryDirectory(prefix='ledger-documents-qt-');self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)/'workspace';root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(Path(temporary.name)/'profile')});env.start();self.addCleanup(env.stop)
        kernel=Kernel(root)
        from workbench import document_qt as page,shell2
        class Session:state={}
        class Host:
            def __init__(self):self.root=root;self.session=Session();self.reading_profile=None;self.messages=[]
            def statusBar(self):
                host=self
                class Bar:
                    def showMessage(self,text,ms=0):host.messages.append(text)
                return Bar()
        host=Host()
        with patch.object(shell2,'engineering',create=True) as fake:
            fake.return_value=kernel
            from workbench import engine
            with patch.object(engine,'engineering',return_value=kernel):
                tab=page.DocumentsTab(host)
                self.assertIsNotNone(tab.document_id);first=tab.document_id
                tab.page.setPlainText('');tab.page.insertPlainText('The quick brown fox jumps over the lazy dog.')
                self.assertTrue(tab.dirty);self.assertTrue(tab.flush());self.assertEqual(tab.revision,2)
                cursor=tab.page.textCursor();cursor.setPosition(4);cursor.setPosition(15,QTextCursor.KeepAnchor);tab.page.setTextCursor(cursor)
                self.assertEqual(tab.slate_selection(),{'block':0,'start':4,'end':15,'text':'quick brown'})
                self.assertIn('selected words 4–15',tab.slate_context())
                answer=tab.slate_request('make these words bold')
                self.assertTrue(answer.startswith('Done: made “quick brown” bold · revision 3'),answer);self.assertIn('no model',answer)
                stored=kernel.dispatch('documents.get',{'id':first},operator())['result']['document']
                self.assertEqual(stored['blocks'][0]['marks'],[{'start':4,'end':15,'bold':True}]);self.assertEqual(stored['last_change']['actor'],'SLATE')
                self.assertEqual(page.from_qt(tab.page.document())[0]['marks'],[{'start':4,'end':15,'bold':True}]);self.assertFalse(tab.dirty);self.assertEqual(tab.revision,3)
                self.assertTrue(tab.page.document().isUndoAvailable())
                self.assertIsNone(tab.slate_request('write a sonnet about foxes'))     # left to the model path
                self.assertTrue(tab.page.textCursor().hasSelection())                  # the owner's selection survives Slate's turn
                cursor=tab.page.textCursor();cursor.clearSelection();tab.page.setTextCursor(cursor)
                self.assertIn('Select the words first',tab.slate_request('underline'))
                answer=tab.slate_request('undo');self.assertIn('Took the last change back',answer)
                stored=kernel.dispatch('documents.get',{'id':first},operator())['result']['document'];self.assertEqual(stored['blocks'][0]['marks'],[]);self.assertEqual(stored['revision'],4)
                answer=tab.slate_request('make it a heading');self.assertIn('made the paragraph a heading',answer)
                self.assertEqual(page.from_qt(tab.page.document())[0]['style'],'Heading1')
                # reopen: a second page over the same store shows the saved revision
                second=page.DocumentsTab(host);second.open_document(first)
                self.assertEqual((second.revision,page.from_qt(second.page.document())[0]['style'],second.page.toPlainText()),(5,'Heading1','The quick brown fox jumps over the lazy dog.'))
                # a stale page cannot overwrite newer writing: it reloads instead
                tab.page.insertPlainText(' Late words.');tab.dirty=True;self.assertTrue(tab.flush())   # tab holds revision 6 now
                second.page.insertPlainText(' Older page.');second.dirty=True;self.assertFalse(second.flush())
                self.assertEqual(second.revision,6);self.assertIn('Late words.',second.page.toPlainText());self.assertNotIn('Older page.',second.page.toPlainText())
                self.assertTrue(any('newer revision' in m for m in host.messages))


if __name__=='__main__':unittest.main()
