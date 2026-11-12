"""Quantities, condition cards, retained helpers and the numbers profile (HATCH AGENT-01, WI-B).

Nothing here starts a worker, a model or a job: Kernel.launch and Kernel.submit are held with AssertionError, the exact
calculator is math.evaluate in process, and the profile's steps are driven by hand exactly as the loop dispatches them.
"""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import quantities as Q,conditions as C,helpers as H,agent_profiles,profile_numbers,math_model
from workbench.engineering_kernel import Kernel,Principal,operator,CAPABILITIES


class Extraction(unittest.TestCase):
    def one(self,text):
        rows=Q.extract(text);self.assertEqual(len(rows),1,(text,rows));return rows[0]

    def test_spellings_owners_write(self):
        for text,value,unit,dimension,kernel in (('12.5 kg','12.5','kg','mass',None),('3 A','3','A','current','A'),('3.3V','3.3','V','voltage','V'),
                                                 ('47k ohm','47','kohm','resistance',None),('4.7 µF','4.7','uF','capacitance',None),('100 mm','100','mm','length',None),
                                                 ('1,250 W','1250','W','power','W'),('-5 °C','-5','°C','temperature',None),('50 %','50','%','ratio',None),('5%','5','%','ratio',None),
                                                 ('500 mA','500','mA','current','mA'),('2 hours','2','h','time','s'),('10 MB','10','MB','memory','MB'),('12,5 kg','12.5','kg','mass',None),
                                                 ('.25 kg','0.25','kg','mass',None),('12.50 kg','12.50','kg','mass',None),('3 kilograms','3','kg','mass',None),('1.5 kWh','1.5','kWh','energy',None)):
            row=self.one(text)
            self.assertEqual((row['text'],row['value'],row['unit_canonical'],row['dimension'],row['kernel_unit']),(text,value,unit,dimension,kernel),text)
            self.assertEqual((row['start'],row['end']),(0,len(text)))
        rows=Q.extract('2 h 30 min');self.assertEqual([(r['text'],r['unit_canonical'],r['factor']) for r in rows],[('2 h','h','3600'),('30 min','min','60')])
        rows=Q.extract('It took 2 h 30 min, at 3 A.');self.assertEqual([(r['start'],r['end'],r['text']) for r in rows],[(8,11,'2 h'),(12,18,'30 min'),(23,26,'3 A')])

    def test_micro_and_ohm_forms_read_the_same(self):
        for text in ('4.7 µF','4.7 μF','4.7 uF','4.7µF'):self.assertEqual((self.one(text)['unit_canonical'],self.one(text)['factor']),('uF','0.000001'),text)
        for text in ('47 kΩ','47 kΩ','47 kohm','47k ohm','47 k ohm','47 kohms'):self.assertEqual((self.one(text)['unit_canonical'],self.one(text)['dimension']),('kohm','resistance'),text)
        for text in ('470 Ω','470 ohm','470 ohms'):self.assertEqual(self.one(text)['unit_canonical'],'ohm',text)
        self.assertEqual(self.one('3 µs')['kernel_unit'],'us');self.assertEqual(self.one('3 µA')['kernel_unit'],'uA')
        self.assertEqual((self.one('2 kV')['kernel_unit'],self.one('2 kV')['factor']),('V','1000'))

    def test_numbers_without_units_and_mixed_text_are_handled_honestly(self):
        row=self.one('about 42');self.assertEqual((row['text'],row['value'],row['unit'],row['unit_canonical'],row['dimension']),('42','42',None,None,None))
        self.assertEqual([r['text'] for r in Q.extract('3 apples and 47k and 3rd place v2 at 14:30 on 2026-11-05, 3/4 done, range 3-5 kg, 5 pm')],['3','5'])
        rows=Q.extract('Bought 3 apples, 2 kg flour and 500 g sugar for $12.50.')
        self.assertEqual([(r['text'],r['unit_canonical']) for r in rows],[('3',None),('2 kg','kg'),('500 g','g'),('12.50',None)])
        chosen,left,note=Q.choose(rows);self.assertEqual([q['text'] for q in chosen],['2 kg','500 g']);self.assertEqual(len(left),2);self.assertIn('2 plain numbers',note)
        chosen,left,note=Q.choose(Q.extract('3 and 4 and 5'));self.assertEqual(len(chosen),3);self.assertEqual(left,[]);self.assertIn('count',note)
        self.assertEqual(Q.choose([]),([],[],''))
        self.assertEqual(Q.extract(''),[]);self.assertEqual(Q.extract('no numbers here'),[])
        with self.assertRaises(ValueError):Q.extract(None)

    def test_bounds_hold(self):
        rows=Q.extract(' '.join('%d kg'%i for i in range(300)));self.assertEqual(len(rows),Q.MAX_MATCHES)
        self.assertEqual(len(Q.extract('1 2 3 4 5',limit=2)),2)
        many=[Q.extract('%d kg'%i)[0] for i in range(Q.MAX_SUM+1)]
        with self.assertRaisesRegex(ValueError,'TOO_MANY_TO_ADD'):Q.sum_model(many)
        with self.assertRaisesRegex(ValueError,'NOTHING_TO_ADD'):Q.sum_model([])
        model=Q.sum_model(many[:Q.MAX_SUM]);ir=math_model.validate(model)       # 127 nodes, balanced: inside the IR's node and depth bounds
        self.assertEqual(len(model['nodes']),2*Q.MAX_SUM-1);self.assertEqual(math_model.evaluate(ir)['state'],'FEASIBLE')
        spellings=Q.accepted_spellings();self.assertIn('kg',spellings['symbols']);self.assertIn('ohm',spellings['symbols']);self.assertIn('kilograms',spellings['words'])


class Fixture(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ledger-conditions-');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(Path(temporary.name)/'profile')});env.start();self.addCleanup(env.stop)
        self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.bounded=Principal(self.owner.identity,frozenset({'read','execute'}),self.owner.paths,self.owner.tools,self.owner.mode)   # the budget's effects: execute
        launch=patch.object(Kernel,'launch',side_effect=AssertionError('no worker'));launch.start();self.addCleanup(launch.stop)
        submit=patch.object(Kernel,'submit',side_effect=AssertionError('no job'));submit.start();self.addCleanup(submit.stop)

    def call(self,op,args=None,principal=None):
        r=self.kernel.dispatch(op,args or {},principal or self.owner);self.assertTrue(r['ok'],r);return r['result']

    def refused(self,op,args,principal=None):
        r=self.kernel.dispatch(op,args,principal or self.owner);self.assertFalse(r['ok']);return r['error']['message']

    def page(self,text='Flour 12.5 kg for the loaves.\nSalt 3 kg in the store.\nYeast 0.5 kg left.\nNo numbers in this line.'):
        return self.call('documents.create',{'title':'Stores','text':text})

    def run_profile(self,document,principal=None,request='add up the numbers on this page',context=None):
        """Drive the profile exactly as agent_loop will: plan, then per step arguments -> dispatch or local -> interpret or failed, merging context and inserted steps."""
        principal=principal or self.bounded;profile=agent_profiles.PROFILES['numbers_on_page']
        context={'document':document,**(context or {})};plan=profile.plan(context,self.kernel,principal)
        state={'id':'a'*32,'investigation':'b'*32,'profile':profile.name,'request':request,'state':'RUNNING','reason':'','cursor':0,
               'budget':{'max_steps':40,'max_seconds':600,'effects':'execute'},'context':context,'plan':plan}
        ran=[];claims=[]
        while state['cursor']<len(state['plan']) and len(ran)<40:
            step=profile.next(state);doing=profile.describe(state)
            try:
                args=profile.arguments(step,state,self.kernel,principal)
                if step['operation'].startswith('helpers:'):result=profile.local(step,state,self.kernel,principal);ok=True
                else:
                    envelope=self.kernel.dispatch(step['operation'],args,principal);ok=envelope['ok'];result=envelope['result'] if ok else envelope['error']['message']
            except ValueError as exc:ok=False;result=str(exc)
            step['outcome']='DONE' if ok else 'FAILED';state['cursor']+=1
            out=profile.interpret(step,result,state,self.kernel,principal) if ok else profile.failed(step,result,state,self.kernel,principal)
            state['context'].update(out.get('context_updates') or {});claims+=out.get('claims') or []
            if out.get('steps'):state['plan'][state['cursor']:state['cursor']]=out['steps']
            ran.append({'key':step['key'],'ok':ok,'doing':doing,'result':result,'out':out})
            if out.get('waiting'):state['state']='WAITING';state['reason']=out['waiting'];break
            if out.get('done'):state['state']='DONE';break
        return state,ran,claims


class Sum(Fixture):
    def test_sum_model_through_math_evaluate_gives_the_total_and_unit(self):
        for texts,total,unit in ((('12.5 kg','3 kg','0.5 kg'),'16 kg','kg'),(('3 A','500 mA'),'3.5 A','A'),(('2 h','30 min'),'2.5 h','h'),(('47k ohm','470 ohm'),'47.47 kohm','kohm'),
                                 (('4.7 µF','100 nF'),'4.8 uF','uF'),(('3','4','5'),'12',None),(('12 %','30 %'),'42%','%'),(('1,250 W','0.5 kW'),'1750 W','W'),(('-5 °C','20 °C'),'15 °C','°C'),(('7 kg',),'7 kg','kg')):
            rows=[Q.extract(t)[0] for t in texts];model=Q.sum_model(rows)
            evaluation=self.call('math.evaluate',{'model':model});self.assertEqual(evaluation['state'],'FEASIBLE',texts)
            got=Q.total_of(evaluation,rows);self.assertEqual((got['text'],got['unit'],got['count']),(total,unit,len(texts)),texts);self.assertTrue(got['exact'])
        model=Q.sum_model([Q.extract(t)[0] for t in ('12.5 kg','3 kg','0.5 kg')])
        self.assertEqual(model['schema'],'arc.math-model/1');self.assertEqual([n['op'] for n in model['nodes']],['quantity']*3+['add','add'])
        self.assertEqual([(n['value'],n['unit']) for n in model['nodes'][:3]],[('12500','1'),('3000','1'),('500','1')])   # grams, dimensionless in the Kernel; the assumption says so
        self.assertTrue(any('outside the Kernel unit algebra' in a for a in model['assumptions']))
        model=Q.sum_model([Q.extract(t)[0] for t in ('3 A','500 mA')]);self.assertEqual([(n['value'],n['unit']) for n in model['nodes'][:2]],[('3','A'),('500','mA')])
        self.assertEqual(self.call('math.evaluate',{'model':model})['outputs'][0]['value']['unit'],'A')
        self.assertEqual(self.call('math.evaluate',{'model':model,'output_unit':'mA'})['outputs'][0]['value']['decimal'],'3500')

    def test_dimension_mismatch_names_both_quantities(self):
        with self.assertRaisesRegex(ValueError,r'UNITS_DIFFER: 12.5 kg \(kg\) and 3 A \(A\) cannot be added'):Q.sum_model([Q.extract('12.5 kg')[0],Q.extract('3 A')[0]])
        with self.assertRaisesRegex(ValueError,r'12.5 kg \(kg\) and 7 \(no unit\)'):Q.sum_model([Q.extract('12.5 kg')[0],Q.extract('7')[0]])
        with self.assertRaisesRegex(ValueError,r'2 h \(h\) and 3 Hz \(Hz\)'):Q.sum_model([Q.extract('2 h')[0],Q.extract('3 Hz')[0]])
        try:Q.sum_model([Q.extract('12.5 kg')[0],Q.extract('3 A')[0]])
        except ValueError as exc:self.assertEqual(C.mismatch_question(exc),'The quantities use different units: 12.5 kg (kg) and 3 A (A); which should be summed?')
        with self.assertRaisesRegex(ValueError,'°C.*°F'):Q.sum_model([Q.extract('-5 °C')[0],Q.extract('20 °F')[0]])
        with self.assertRaisesRegex(ValueError,'SUM_NOT_EVALUATED'):Q.total_of({'state':'DIMENSION_MISMATCH','reason':'x','outputs':[]},[Q.extract('3 A')[0]])


class Helpers(Fixture):
    def test_registry_scopes_and_observers(self):
        self.assertEqual({op:CAPABILITIES[op] for op in ('conditions.list','conditions.get','conditions.recheck','helpers.list','helpers.get')},
                         {'conditions.list':'read','conditions.get':'read','conditions.recheck':'execute','helpers.list':'read','helpers.get':'read'})
        from workbench import activity
        self.assertTrue({'conditions.list','conditions.get','helpers.list','helpers.get'}<=activity.OBSERVER_OPERATIONS);self.assertNotIn('conditions.recheck',activity.OBSERVER_OPERATIONS)
        self.assertIn('numbers_on_page',agent_profiles.PROFILES);self.assertIs(agent_profiles.PROFILES['numbers_on_page'],profile_numbers.PROFILE)
        self.assertEqual(profile_numbers.PROFILE.needs,('document',))

    def test_ensure_is_idempotent_and_record_use_counts(self):
        description=dict(purpose='Count the words',inputs='text',outputs='a number',limits='none',source={'kind':'module','ref':'workbench.documents:word_count'})
        first=H.ensure_helper(self.kernel,self.owner,'word_count',**description);again=H.ensure_helper(self.kernel,self.owner,'word_count',**description)
        self.assertEqual((first['id'],first['revision'],again['revision'],first['schema'],first['kind']),(again['id'],1,1,'ledger.helper/1','helper'))
        self.assertEqual((first['uses'],first['successes'],first['failures'],first['effectiveness'],first['last_used'],first['created_by']),(0,0,0,None,None,'LEDGER'))
        changed=H.ensure_helper(self.kernel,self.owner,'word_count',**{**description,'limits':'paragraphs under 32 KiB'})
        self.assertEqual((changed['id'],changed['revision'],changed['limits']),(first['id'],2,'paragraphs under 32 KiB'))
        used=H.record_use(self.kernel,self.owner,'word_count',True,'counted 7 words');self.assertEqual((used['uses'],used['successes'],used['failures'],used['effectiveness'],used['last_note']),(1,1,0,1.0,'counted 7 words'))
        used=H.record_use(self.kernel,self.owner,'word_count',False,'empty page');used=H.record_use(self.kernel,self.owner,'word_count',True)
        self.assertEqual((used['uses'],used['successes'],used['failures'],used['effectiveness'],used['revision']),(3,2,1,0.6667,5));self.assertIsNotNone(used['last_used'])
        with self.assertRaisesRegex(ValueError,'HELPER_UNKNOWN'):H.record_use(self.kernel,self.owner,'nobody',True)
        with self.assertRaisesRegex(ValueError,'HELPER_NAME'):H.ensure_helper(self.kernel,self.owner,'Word Count',**description)
        with self.assertRaisesRegex(ValueError,'HELPER_SOURCE'):H.ensure_helper(self.kernel,self.owner,'x',**{**description,'source':{'kind':'shell','ref':'rm'}})
        rows=self.call('helpers.list')['helpers'];self.assertEqual([r['name'] for r in rows],['word_count']);self.assertEqual(rows[0]['uses'],3)
        self.assertEqual(self.call('helpers.get',{'id':first['id']})['helper']['name'],'word_count')
        self.assertEqual(self.refused('helpers.get',{'id':first['id']},operator('someone-else')),'Project Desk record unavailable to this caller')
        built=H.ensure_built_in(self.kernel,self.owner);self.assertEqual(set(built),{'quantities_from_text','sum_model','condition_card'})
        self.assertIn('kg',built['quantities_from_text']['limits']['accepted_spellings']['symbols']);self.assertEqual(built['sum_model']['source'],{'kind':'module','ref':'workbench.quantities:sum_model'})
        self.assertEqual(len(self.call('helpers.list')['helpers']),4);self.assertEqual(H.ensure_built_in(self.kernel,self.owner)['sum_model']['revision'],1)


class Lifecycle(Fixture):
    def test_profile_steps_by_hand_write_the_total_and_bind_the_card(self):
        doc=self.page();state,ran,claims=self.run_profile(doc['id'])
        self.assertEqual([(r['key'],r['ok']) for r in ran],[('read',True),('extract',True),('sum',True),('write',True),('card',True)]);self.assertEqual(state['state'],'DONE')
        self.assertEqual([r['doing'] for r in ran],['Reading the page (step 1 of 5)','Finding the numbers with units on the page (step 2 of 5)','Adding them up with the exact calculator (step 3 of 5)',
                                                    'Writing the total under the page (step 4 of 5)','Binding the total to the words it came from (step 5 of 5)'])
        self.assertEqual(claims,[{'role':'FINDING','text':'The 3 quantities on this page total 16 kg.'}])
        context=state['context'];self.assertEqual((context['total']['text'],context['found'],context['left_out'],context['document_revision']),('16 kg',3,0,2))
        self.assertEqual(profile_numbers.PROFILE.describe(state),'Finished: The 3 quantities on this page total 16 kg.')
        saved=self.call('documents.get',{'id':doc['id']})['document'];self.assertEqual(saved['revision'],2);self.assertEqual(len(saved['blocks']),5)
        result=saved['blocks'][4];self.assertEqual(result['id'],context['result_block']);self.assertTrue(result['text'].startswith('Total of the 3 quantities on this page: 16 kg · checked by Graphite '),result['text'])
        self.assertTrue(result['text'].endswith('· from: 12.5 kg, 3 kg, 0.5 kg'));self.assertEqual(saved['last_change']['actor'],'SLATE');self.assertEqual(saved['last_change']['request'],'add up the numbers on this page')
        card=self.call('conditions.get',{'id':context['conditions'][0]});self.assertEqual(card['document_revision_now'],2);card=card['condition']
        self.assertEqual((card['state'],card['reason'],card['expression'],card['document'],card['document_revision'],card['result_block'],card['assignment'],card['origin'],card['schema'],card['kind']),
                         ('CURRENT','','sum',doc['id'],2,result['id'],'a'*32,'SLATE','ledger.condition/1','condition'))
        self.assertEqual(card['result'],{'value':'16','unit':'kg','text':'16 kg'});self.assertEqual(card['method'],['quantities_from_text','sum_model'])
        self.assertEqual([(i['block'],i['index'],i['start'],i['end'],i['text'],i['value'],i['unit']) for i in card['inputs']],
                         [(doc['blocks'][0]['id'],0,6,13,'12.5 kg','12.5','kg'),(doc['blocks'][1]['id'],1,5,9,'3 kg','3','kg'),(doc['blocks'][2]['id'],2,6,12,'0.5 kg','0.5','kg')])
        rows=self.call('conditions.list',{'document':doc['id']})['conditions'];self.assertEqual([(r['id'],r['state'],r['inputs'],r['result']['text']) for r in rows],[(card['id'],'CURRENT',3,'16 kg')])
        self.assertEqual(self.call('conditions.list')['conditions'][0]['id'],card['id']);self.assertEqual(self.refused('conditions.get',{'id':card['id']},operator('someone-else')),'Project Desk record unavailable to this caller')
        helpers={h['name']:h for h in self.call('helpers.list')['helpers']}
        self.assertEqual((helpers['quantities_from_text']['uses'],helpers['sum_model']['uses'],helpers['condition_card']['uses'],helpers['condition_card']['effectiveness']),(1,1,1,1.0))
        self.assertIn('3 quantities on page',helpers['quantities_from_text']['last_note'])

    def test_editing_an_input_marks_the_card_stale_and_recheck_rewrites_the_result(self):
        doc=self.page();state,_,_=self.run_profile(doc['id']);card_id=state['context']['conditions'][0];result_block=state['context']['result_block']
        edited=self.call('documents.edit',{'id':doc['id'],'expected_revision':2,'selection':{'block':1,'start':5,'end':9,'text':'3 kg'},'change':{'replace':'4 kg'},'origin':'HUMAN'})
        self.assertEqual(edited['conditions_stale'],[card_id]);self.assertEqual(edited['document']['revision'],3)
        card=self.call('conditions.get',{'id':card_id})['condition'];self.assertEqual((card['state'],card['reason'],card['document_revision'],card['seen_revision']),('STALE','The words “3 kg” now read “4 kg”.',2,3))
        self.assertEqual(card['result']['text'],'16 kg')                 # the old result stays readable until a recheck
        saved=self.call('documents.save',{'id':doc['id'],'expected_revision':3,'blocks':edited['document']['blocks']+[{'text':'A new line.'}]})
        self.assertEqual(saved['conditions_stale'],[card_id])            # still stale on the next save, so the page's quiet line can follow the truth
        rechecked=self.call('conditions.recheck',{'id':card_id});card=rechecked['condition']
        self.assertEqual((card['state'],card['reason'],card['document_revision'],card['rechecks'],card['result']['text']),('CURRENT','',5,1,'17 kg'))
        self.assertEqual([i['text'] for i in card['inputs']],['12.5 kg','4 kg','0.5 kg']);self.assertEqual(rechecked['words'],'Rechecked: the 3 quantities on this page total 17 kg; the result paragraph was rewritten.')
        page=rechecked['document'];self.assertEqual((page['revision'],len(page['blocks']),page['blocks'][4]['id']),(5,6,result_block))
        self.assertTrue(page['blocks'][4]['text'].startswith('Total of the 3 quantities on this page: 17 kg · checked by Graphite '));self.assertTrue(page['blocks'][4]['text'].endswith('from: 12.5 kg, 4 kg, 0.5 kg'))
        self.assertEqual(page['last_change']['actor'],'SLATE');self.assertEqual([b['text'] for b in page['blocks'][:4]],[b['text'] for b in edited['document']['blocks'][:4]])   # only the result paragraph was rewritten
        bold=self.call('documents.edit',{'id':doc['id'],'expected_revision':5,'selection':{'block':3,'start':0,'end':2,'text':'No'},'change':{'bold':True}});self.assertEqual(bold['conditions_stale'],[])
        self.assertEqual(self.call('conditions.get',{'id':card_id})['condition']['state'],'CURRENT')
        moved=self.call('documents.edit',{'id':doc['id'],'expected_revision':6,'selection':{'block':1,'start':0,'end':4,'text':'Salt'},'change':{'replace':'Sea salt'}})
        self.assertEqual(moved['conditions_stale'],[card_id]);self.assertEqual(self.call('conditions.get',{'id':card_id})['condition']['reason'],'The words “4 kg” moved within their paragraph.')
        back=self.call('documents.edit',{'id':doc['id'],'expected_revision':7,'selection':{'block':1,'start':0,'end':8,'text':'Sea salt'},'change':{'replace':'Salt'}})
        self.assertEqual(back['conditions_stale'],[]);self.assertEqual(self.call('conditions.get',{'id':card_id})['condition']['state'],'CURRENT')   # the words came back exactly: current again

    def test_recheck_with_different_units_says_why_and_stays_stale(self):
        doc=self.page();state,_,_=self.run_profile(doc['id']);card_id=state['context']['conditions'][0]
        edited=self.call('documents.edit',{'id':doc['id'],'expected_revision':2,'selection':{'block':1,'start':5,'end':9,'text':'3 kg'},'change':{'replace':'3 A'},'origin':'HUMAN'})
        self.assertEqual(edited['conditions_stale'],[card_id])
        rechecked=self.call('conditions.recheck',{'id':card_id});card=rechecked['condition']
        self.assertEqual((card['state'],card['document_revision']),('STALE',4));self.assertIn('12.5 kg (kg) and 3 A (A)',card['reason'])
        self.assertTrue(rechecked['document']['blocks'][4]['text'].startswith('The quantities on this page cannot be added as they stand: 12.5 kg (kg) and 3 A (A) cannot be added · checked by Graphite '))
        self.assertIn('cannot be added as they stand',rechecked['words']);self.assertEqual(card['result']['text'],'16 kg')
        fixed=self.call('documents.edit',{'id':doc['id'],'expected_revision':4,'selection':{'block':1,'start':5,'end':8,'text':'3 A'},'change':{'replace':'3 kg'},'origin':'HUMAN'})
        self.assertEqual(fixed['conditions_stale'],[card_id])
        card=self.call('conditions.recheck',{'id':card_id})['condition'];self.assertEqual((card['state'],card['result']['text'],card['rechecks']),('CURRENT','16 kg',2))
        helpers={h['name']:h for h in self.call('helpers.list')['helpers']};self.assertEqual((helpers['sum_model']['uses'],helpers['sum_model']['failures']),(3,1))

    def test_deleting_the_result_paragraph_breaks_the_card(self):
        doc=self.page();state,_,_=self.run_profile(doc['id']);card_id=state['context']['conditions'][0]
        page=self.call('documents.get',{'id':doc['id']})['document'];without=page['blocks'][:4]
        saved=self.call('documents.save',{'id':doc['id'],'expected_revision':2,'blocks':without});self.assertEqual(saved['conditions_stale'],[card_id])
        card=self.call('conditions.get',{'id':card_id})['condition'];self.assertEqual((card['state'],card['reason']),('BROKEN','The result paragraph is no longer on the page.'))
        rechecked=self.call('conditions.recheck',{'id':card_id});self.assertEqual(rechecked['condition']['state'],'BROKEN');self.assertIn('ask Stacy for the total again',rechecked['words'])
        self.assertEqual(self.call('documents.get',{'id':doc['id']})['document']['revision'],3)     # a broken card never writes the page
        undone=self.call('documents.save',{'id':doc['id'],'expected_revision':3,'blocks':page['blocks']});self.assertEqual(undone['conditions_stale'],[])
        self.assertEqual(self.call('conditions.get',{'id':card_id})['condition']['state'],'CURRENT')   # the paragraph came back with its id: current again
        emptied=[*page['blocks'][:4],{**page['blocks'][4],'text':'','marks':[]}]
        self.call('documents.save',{'id':doc['id'],'expected_revision':4,'blocks':emptied});self.assertEqual(self.call('conditions.recheck',{'id':card_id})['condition']['state'],'BROKEN')

    def test_zero_quantities_wait_kindly_and_result_paragraphs_are_not_counted(self):
        empty=self.page('Just words here.\nAnd more words.');state,ran,claims=self.run_profile(empty['id'])
        self.assertEqual((state['state'],state['reason'],claims),('WAITING',profile_numbers.NO_NUMBERS,[]));self.assertEqual([r['key'] for r in ran],['read','extract'])
        self.assertEqual([s['key'] for s in state['plan']],['read','extract','read','extract','sum','write','card']);self.assertEqual(state['cursor'],2)
        self.assertEqual(profile_numbers.PROFILE.describe(state),profile_numbers.NO_NUMBERS);self.assertEqual(self.call('documents.get',{'id':empty['id']})['document']['revision'],1)
        doc=self.page();first,_,_=self.run_profile(doc['id']);second,ran,claims=self.run_profile(doc['id'])
        self.assertEqual((second['state'],second['context']['found'],claims[0]['text']),('DONE',3,'The 3 quantities on this page total 16 kg.'))   # the first total is not an input of the second
        self.assertEqual(ran[1]['result']['excluded_result_paragraphs'],1);self.assertEqual(len(self.call('conditions.list',{'document':doc['id']})['conditions']),2)
        mixed=self.page('Flour 12.5 kg.\nCurrent 3 A.\nA count of 7.');state,ran,claims=self.run_profile(mixed['id'])
        self.assertEqual(state['state'],'WAITING');self.assertEqual(claims,[{'role':'QUESTION','text':'The quantities use different units: 12.5 kg (kg) and 3 A (A); which should be summed?'}])
        self.assertEqual(state['reason'],claims[0]['text']);self.assertEqual([r['key'] for r in ran],['read','extract']);self.assertEqual(self.call('documents.get',{'id':mixed['id']})['document']['revision'],1)
        plain=self.page('Chairs 4.\nTables 2.\nLamps 3.');state,_,claims=self.run_profile(plain['id'])
        self.assertEqual((state['state'],state['context']['total']['text'],claims[0]['text']),('DONE','9','The 3 quantities on this page total 9.'))
        self.assertIn('plain numbers without a unit; the total is a count',self.call('documents.get',{'id':plain['id']})['document']['blocks'][3]['text'])

    def test_bounded_principal_and_a_page_that_moved_on(self):
        doc=self.page();reader=Principal(self.owner.identity,frozenset({'read'}),self.owner.paths,self.owner.tools,self.owner.mode)
        state,ran,_=self.run_profile(doc['id'],principal=reader)
        self.assertEqual([(r['key'],r['ok']) for r in ran],[('read',True),('extract',True),('sum',True),('write',False)]);self.assertEqual(state['state'],'WAITING')
        self.assertIn('outside the authorized mode/scope',state['reason']);self.assertEqual(self.call('documents.get',{'id':doc['id']})['document']['revision'],1)
        profile=profile_numbers.PROFILE;context={'document':doc['id']};plan=profile.plan(context,self.kernel,self.bounded)
        state={'id':'a'*32,'request':'add up the numbers on this page','state':'RUNNING','reason':'','cursor':0,'context':context,'plan':plan,'budget':{}}
        out=profile.interpret(plan[0],self.call('documents.get',{'id':doc['id']}),state,self.kernel,self.bounded);context.update(out['context_updates'])
        self.call('documents.save',{'id':doc['id'],'expected_revision':1,'blocks':[{'text':'Rewritten 1 kg.'}]});state['cursor']=1
        with self.assertRaisesRegex(ValueError,'changed while Graphite was working'):profile.local(plan[1],state,self.kernel,self.bounded)
        out=profile.failed(plan[1],profile_numbers.PAGE_MOVED+' (revision 1 is now 2)',state,self.kernel,self.bounded)   # the loop replaces what follows a failed step: the whole procedure again
        self.assertEqual((out['waiting'],[s['key'] for s in out['steps']]),(profile_numbers.PAGE_MOVED,['read','extract','sum','write','card']))
        out=profile.failed(plan[3],'REVISION_CHANGED: the document moved on; reopen before editing',state,self.kernel,self.bounded)
        self.assertEqual((out['waiting'],[s['key'] for s in out['steps']]),(profile_numbers.PAGE_MOVED,['read','extract','sum','write','card']))
        with self.assertRaisesRegex(ValueError,'needs the page'):profile.plan({},self.kernel,self.bounded)
        last=self.call('documents.get',{'id':doc['id']})['document']['blocks'][-1]['id'];good=dict(expression='sum',result={'value':'1','unit':'kg','text':'1 kg'},method=['x'],assignment=None)
        with self.assertRaisesRegex(ValueError,'CONDITION_RESULT_BLOCK'):C.create(self.kernel,self.bounded,document=doc['id'],inputs=[{'block':last,'index':0,'start':10,'end':14,'text':'1 kg','value':'1','unit':'kg'}],result_block='0'*32,**good)
        with self.assertRaisesRegex(ValueError,'CONDITION_INPUT_NOT_ON_PAGE'):C.create(self.kernel,self.bounded,document=doc['id'],inputs=[{'block':'0'*32,'index':0,'start':0,'end':4,'text':'Rewr','value':'1','unit':None}],result_block=last,**good)
        with self.assertRaisesRegex(ValueError,'CONDITION_INPUT_NOT_ON_PAGE'):C.create(self.kernel,self.bounded,document=doc['id'],inputs=[{'block':last,'index':0,'start':10,'end':14,'text':'2 kg','value':'2','unit':'kg'}],result_block=last,**good)
        with self.assertRaisesRegex(ValueError,'CONDITION_INPUT_IS_THE_RESULT'):C.create(self.kernel,self.bounded,document=doc['id'],inputs=[{'block':last,'index':0,'start':10,'end':14,'text':'1 kg','value':'1','unit':'kg'}],result_block=last,**good)
        with self.assertRaisesRegex(ValueError,'outside the authorized'):C.create(self.kernel,reader,document=doc['id'],inputs=[],result_block=last,**good)

    def test_refresh_is_quiet_cheap_and_never_writes_the_page(self):
        doc=self.page();state,_,_=self.run_profile(doc['id']);card_id=state['context']['conditions'][0]
        page=self.call('documents.get',{'id':doc['id']});events=len(page['events']);revision=page['document']['revision']
        self.assertEqual(C.refresh_document(self.kernel,page['document'],self.owner),[])
        self.assertEqual(C.refresh_document(self.kernel,{**page['document'],'blocks':page['document']['blocks'][:4]},self.owner),[card_id])   # judged from the record it is given
        self.assertEqual(C.refresh_document(self.kernel,page['document'],self.owner),[])
        again=self.call('documents.get',{'id':doc['id']});self.assertEqual((again['document']['revision'],len(again['events'])),(revision,events))   # the page was never written
        self.assertEqual(C.refresh_document(self.kernel,page['document'],operator('someone-else')),[])
        self.assertEqual(C.refresh_document(self.kernel,{'id':'0'*32,'revision':1,'blocks':[]},self.owner),[])
        with self.kernel.db() as db:history=db.execute('SELECT count(*) FROM desk_history WHERE id=?',(card_id,)).fetchone()[0]
        self.assertEqual(history,3)   # created, marked BROKEN, marked CURRENT: a write only when the state moved

    def test_through_the_loop_when_it_is_filled(self):
        from workbench import agent_loop
        try:agent_loop.request_profile('add up the numbers on this page')
        except NotImplementedError:self.skipTest('agent_loop (WI-A) is not filled in this tree yet; the steps are driven by hand above')
        doc=self.page()
        assigned=self.call('agent.assign',{'request':'add up the numbers on this page','profile':'numbers_on_page','context':{'document':doc['id']}})
        ran=self.call('agent.run',{'id':assigned['assignment']['id']})
        self.assertEqual(ran['assignment']['state'],'DONE',ran)
        status=self.call('agent.status',{'id':assigned['assignment']['id']})['assignments'][0]
        self.assertIn('The 3 quantities on this page total 16 kg.',[c['text'] if isinstance(c,dict) else c for c in status['found']])
        page=self.call('documents.get',{'id':doc['id']})['document'];self.assertIn('16 kg',page['blocks'][4]['text'])
        self.assertEqual(self.call('conditions.list',{'document':doc['id']})['conditions'][0]['state'],'CURRENT')


if __name__=='__main__':unittest.main()
