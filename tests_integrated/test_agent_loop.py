"""The resident agent loop (HATCH AGENT-01): an assignment is an investigation worked one bounded, recorded step at a time.

Nothing here starts a worker, a job, a model or a native tool: Kernel.launch and Kernel.submit are held for every case, and the
model branch runs only through patched ask_model / model_answer (the live path is not exercised here).
"""
import json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import agent_loop as loop,agent_profiles as profiles,investigations
from workbench.engineering_kernel import Kernel,operator,Principal,CAPABILITIES
from workbench.engineering_cli import schemas

DOC_TEXT='Mass of the frame: 12.5 kg.\nMotor: 3 kg.\nCables: 0.5 kg.'
MISSING='f'*32
JOB='a'*32
FIVE_LINES={'id','investigation','profile','state','reason','working_on','doing_now','found','needs_you','inspect','steps_used','budget','updated','model_used','paused_reason',
            'driver','lease_live','lease_until','service_steps'}   # AGENT-02: who steps it, whether that lease is live and until when, the Ledger service's steps
NUMBERS='add up the numbers on this page'
LOOKS=(('memory','Look at memory'),('storage','Look at storage'),('tools','Look at the tools'))


def seq(*rows):
    return [{'operation':op,'arguments':args,'purpose':purpose} for op,args,purpose in rows]


def looks(n):
    return seq(*[('ledger.machine',{'section':'memory'},'Look %d'%k) for k in range(n)])


class Choosy(profiles.OperationSequence):
    """The given sequence, but after its first step it offers three next looks; which are acceptable is set per case."""
    def __init__(self,acceptable):super().__init__();self.acceptable=acceptable

    def interpret(self,step,result,state,kernel,principal):
        if step['key']!='step1':return {}
        options=[{'key':key,'purpose':purpose,'acceptable':ok,'step':profiles.step(key,purpose,'ledger.machine',{'section':key})} for (key,purpose),ok in zip(LOOKS,self.acceptable)]
        return {'options':options,'situation':'A page with three masses on it'}


class Loop(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ledger-agent-');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(Path(temporary.name)/'profile')});env.start();self.addCleanup(env.stop)
        self.kernel=Kernel(self.root);self.owner=operator('owner')
        for name,words in (('launch','no worker may start'),('submit','no job may be submitted')):
            guard=patch.object(Kernel,name,side_effect=AssertionError(words));guard.start();self.addCleanup(guard.stop)
        self.doc=self.call('documents.create',{'title':'Frame','text':DOC_TEXT})

    def call(self,op,args=None,principal=None):
        r=self.kernel.dispatch(op,args or {},principal or self.owner);self.assertTrue(r['ok'],r);return r['result']

    def refused(self,op,args,principal=None):
        r=self.kernel.dispatch(op,args,principal or self.owner);self.assertFalse(r['ok'],r);return r['error']['message']

    def assign(self,steps,budget=None,request='run the given steps',context=None):
        args={'request':request,'profile':'operation_sequence','context':{'steps':steps,**(context or {})}}
        if budget:args['budget']=budget
        return self.call('agent.assign',args)['assignment']

    def steps_of(self,investigation):
        keys=('seq','kind','purpose','program','outcome','summary','authority','started','finished','inputs','duplicate_of')
        with self.kernel.db() as db:
            return [dict(zip(keys,r)) for r in db.execute('SELECT '+','.join(keys)+' FROM inv_steps WHERE investigation=? ORDER BY seq',(investigation,))]

    def jobs(self):
        with self.kernel.db() as db:return db.execute('SELECT count(*) FROM jobs').fetchone()[0]

    # -- registry -------------------------------------------------------------------------------------------------------------

    def test_registry_records_the_nine_agent_operations_as_cloud_private(self):
        from workbench import activity,stacy_control
        self.assertEqual({op:CAPABILITIES[op] for op in loop.FIELDS},{'agent.assign':'execute','agent.step':'execute','agent.run':'execute','agent.pause':'execute',
                         'agent.resume':'execute','agent.stop':'execute','agent.status':'read','agent.list':'read','agent.release':'execute'})
        definitions=schemas()
        for op in loop.FIELDS:self.assertIn(op,definitions)
        enum=definitions['agent.assign']['properties']['profile']['enum']   # AGENT-02: every registered profile, 'auto' first
        self.assertEqual(enum,['auto']+sorted(profiles.PROFILES));self.assertTrue({'numbers_on_page','operation_sequence'}<=set(enum))
        # AGENT-02: agent.step gained the driver (recorded extension); agent.release {id} is the one added operation
        self.assertEqual(definitions['agent.step']['properties']['driver'],{'type':'string','enum':['desktop','service']});self.assertEqual(definitions['agent.step']['required'],['id'])
        self.assertEqual((set(definitions['agent.release']['properties']),definitions['agent.release']['required']),({'id'},['id']))
        self.assertTrue({'agent.status','agent.list'}<=activity.OBSERVER_OPERATIONS);self.assertNotIn('agent.step',activity.OBSERVER_OPERATIONS);self.assertNotIn('agent.release',activity.OBSERVER_OPERATIONS)
        self.assertTrue(stacy_control.cloud_private('agent.step',{'id':JOB}));self.assertTrue(stacy_control.cloud_private('agent.release',{'id':JOB}))
        self.assertIn('operation_sequence',profiles.PROFILES);self.assertIsInstance(profiles.PROFILES['operation_sequence'],profiles.Profile)
        with self.assertRaises(ValueError):profiles.step('','x','documents.get')
        with self.assertRaises(ValueError):profiles.step('k','x','documents.get',arguments=['not','an','object'])

    # -- the loop -------------------------------------------------------------------------------------------------------------

    def test_sequence_of_reads_runs_to_done_and_every_step_is_on_the_sheet(self):
        a=self.assign(seq(('ledger.machine',{'section':'memory'},'Look at memory'),('documents.get',{'id':self.doc['id']},'Read the page')))
        self.assertEqual((a['state'],a['profile'],a['steps_used'],a['doing_now'],a['model_used']),('READY','operation_sequence',0,'Look at memory',False))
        out=self.call('agent.run',{'id':a['id']})
        self.assertEqual(out['assignment']['state'],'DONE');self.assertIn('Finished: 2 steps ran',out['assignment']['reason'])
        self.assertEqual([(s['operation'],s['outcome'],s['seq']) for s in out['ran']],[('ledger.machine','DONE',1),('documents.get','DONE',2)])
        self.assertTrue(all(isinstance(s['seconds'],float) and s['seconds']>=0 for s in out['ran']))
        rows=self.steps_of(a['investigation']);self.assertEqual([r['kind'] for r in rows],['STEP','STEP'])
        self.assertEqual(json.loads(rows[1]['program']),{'operation':'documents.get','arguments':{'id':self.doc['id']}})
        self.assertEqual({r['authority'] for r in rows},{'execute,read'})  # the owner's approve and candidate scopes never reach a step
        self.assertIn('arguments',json.loads(rows[1]['inputs']));self.assertTrue(all(r['finished']>=r['started'] for r in rows))
        sheet=self.call('investigation.sheet',{'id':a['investigation']})
        self.assertEqual((sheet['question'],sheet['objective']),('run the given steps',profiles.PROFILES['operation_sequence'].words))
        self.assertEqual([s['purpose'] for s in sheet['attempted']],['Look at memory','Read the page']);self.assertEqual(sheet['used']['steps'],2)
        status=self.call('agent.status',{'id':a['id']})['assignments'][0]
        self.assertEqual((status['state'],status['steps_used'],status['model_used'],status['found'],status['needs_you']),('DONE',2,False,[],[]))
        self.assertIn('Finished',status['doing_now'])
        self.assertIsNone(self.call('agent.step',{'id':a['id']})['step'])   # DONE does not step
        self.assertEqual(self.jobs(),0)

    def test_failed_step_waits_with_the_words_and_resume_runs_it_again(self):
        a=self.assign(seq(('documents.get',{'id':MISSING},'Read a page that is not there'),('ledger.machine',{},'Look at the machine')))
        out=self.call('agent.step',{'id':a['id']})
        self.assertEqual((out['assignment']['state'],out['step']['outcome']),('WAITING','FAILED'))
        self.assertIn('Step step1 (Read a page that is not there) did not run: Project Desk record unavailable',out['assignment']['reason'])
        self.assertEqual([n['kind'] for n in out['assignment']['needs_you']],['QUESTION','WAITING'])
        self.assertIn('did not run',out['assignment']['needs_you'][0]['text']);self.assertEqual(out['assignment']['doing_now'],out['assignment']['reason'])
        rows=self.steps_of(a['investigation']);self.assertEqual([(r['outcome'],r['kind']) for r in rows],[('FAILED','STEP')]);self.assertIn('Project Desk',rows[0]['summary'])
        held=self.call('agent.step',{'id':a['id']});self.assertIsNone(held['step']);self.assertIn('Not stepping',held['next']);self.assertEqual(len(self.steps_of(a['investigation'])),1)
        self.assertEqual(self.call('agent.resume',{'id':a['id']})['assignment']['state'],'READY')
        out=self.call('agent.step',{'id':a['id']})
        self.assertEqual((out['assignment']['state'],out['step']['purpose']),('WAITING','Read a page that is not there'))  # the cursor stayed on the failed step
        self.assertEqual(self.call('agent.status',{'id':a['id']})['assignments'][0]['steps_used'],2)

    def test_refusals_are_words_not_exceptions_even_when_a_handler_is_unfinished(self):
        a=self.assign(seq(('helpers.list',{},'List the helpers'),('no.such.operation',{},'Try an unknown operation')))
        out=self.call('agent.run',{'id':a['id']})
        rows=self.steps_of(a['investigation'])
        if rows[0]['outcome']=='DONE':   # WI-B's helpers module is filled in this tree
            self.assertEqual(out['assignment']['state'],'WAITING');self.assertIn('Unknown operation',out['assignment']['reason']);self.assertEqual(len(rows),2)
        else:                            # it still raises NotImplementedError: the loop turns that into WAITING with the words
            self.assertEqual(out['assignment']['state'],'WAITING');self.assertIn('AGENT01_WI_B',out['assignment']['reason']);self.assertEqual(len(rows),1)

    def test_pause_resume_and_stop_transitions(self):
        a=self.assign(looks(3))
        first=self.call('agent.step',{'id':a['id']});self.assertEqual((first['assignment']['state'],first['next']),('RUNNING','Next: Look 1'))
        paused=self.call('agent.pause',{'id':a['id'],'reason':'Ledger closed'})['assignment']
        self.assertEqual((paused['state'],paused['paused_reason'],paused['doing_now']),('PAUSED','Ledger closed','Paused: Ledger closed'))
        held=self.call('agent.step',{'id':a['id']});self.assertIsNone(held['step']);self.assertEqual(held['assignment']['state'],'PAUSED')
        self.assertEqual(len(self.steps_of(a['investigation'])),1)
        self.assertEqual(self.call('agent.run',{'id':a['id']})['ran'],[])
        self.assertIn('ASSIGNMENT_NOT_RUNNING',self.refused('agent.pause',{'id':a['id']}))
        resumed=self.call('agent.resume',{'id':a['id']})['assignment'];self.assertEqual((resumed['state'],resumed['paused_reason'],resumed['doing_now']),('READY',None,'Look 1'))
        second=self.call('agent.step',{'id':a['id']});self.assertEqual((second['assignment']['state'],second['step']['purpose']),('RUNNING','Look 1'))
        stopped=self.call('agent.stop',{'id':a['id'],'reason':'enough'})['assignment'];self.assertEqual((stopped['state'],stopped['reason']),('STOPPED','By you: enough'))
        sheet=self.call('investigation.sheet',{'id':a['investigation']});self.assertEqual((sheet['state'],sheet['reason']),('STOPPED','By you: enough'))
        self.assertIsNone(self.call('agent.step',{'id':a['id']})['step']);self.assertEqual(len(self.steps_of(a['investigation'])),2)
        for op in ('agent.pause','agent.resume','agent.stop'):self.assertIn('ASSIGNMENT_',self.refused(op,{'id':a['id']}))
        listed={r['id']:r for r in self.call('agent.list')['assignments']};self.assertEqual(listed[a['id']]['state'],'STOPPED')

    def test_budget_exhaustion_stops_the_assignment_and_its_investigation(self):
        a=self.assign(looks(3),budget={'max_steps':1})
        out=self.call('agent.run',{'id':a['id']})
        self.assertEqual((out['assignment']['state'],len(out['ran'])),('STOPPED',1));self.assertIn('Budget used: 1 steps',out['assignment']['reason'])
        self.assertEqual(self.call('investigation.sheet',{'id':a['investigation']})['state'],'STOPPED')
        self.assertEqual(out['assignment']['budget'],{'max_steps':1,'max_seconds':600,'effects':'execute'})
        b=self.assign(looks(3),budget={'max_seconds':5})
        with loop.opened(self.kernel) as db:state=loop.load(db,b['id'],'owner');state['seconds']=5.0;loop.store(db,state)   # as if the steps had taken that long
        out=self.call('agent.step',{'id':b['id']});self.assertIsNone(out['step']);self.assertEqual(out['assignment']['state'],'STOPPED');self.assertIn('5.0 seconds',out['assignment']['reason'])

    # -- the right column's five lines ----------------------------------------------------------------------------------------

    def test_status_row_has_the_five_lines_and_the_inspect_list(self):
        a=self.assign(seq(('documents.get',{'id':self.doc['id']},'Read the page')),request='read the frame page',context={'document':self.doc['id']})
        row=self.call('agent.status',{'id':a['id']})['assignments'][0]
        self.assertEqual(set(row),FIVE_LINES)
        self.assertEqual((row['working_on'],row['doing_now'],row['found'],row['needs_you'],row['steps_used'],row['paused_reason']),('read the frame page','Read the page',[],[],0,None))
        self.assertEqual([(i['kind'],i['id']) for i in row['inspect']],[('investigation',a['investigation']),('document',self.doc['id'])])
        self.assertEqual(row['budget'],{'max_steps':40,'max_seconds':600,'effects':'execute'})
        self.assertEqual((row['driver'],row['lease_live'],row['lease_until'],row['service_steps']),(None,False,None,0))   # AGENT-02: nobody has stepped it yet
        self.call('investigation.claim',{'id':a['investigation'],'text':'The frame weighs 16 kg.','role':'FINDING'})
        self.call('investigation.claim',{'id':a['investigation'],'text':'Which unit should the total use?','role':'QUESTION'})
        row=self.call('agent.status',{'id':a['id']})['assignments'][0]
        self.assertEqual([(f['text'],f['evidence_state']) for f in row['found']],[('The frame weighs 16 kg.','UNKNOWN')])
        self.assertEqual([(n['text'],n['kind']) for n in row['needs_you']],[('Which unit should the total use?','QUESTION')])
        self.assertEqual([r['id'] for r in self.call('agent.status')['assignments']],[a['id']])
        listed=self.call('agent.list')['assignments'][0];self.assertEqual((listed['id'],listed['state'],listed['working_on']),(a['id'],'READY','read the frame page'))
        self.assertEqual(self.call('agent.list',{},operator('someone-else'))['assignments'],[])
        self.assertIn('ASSIGNMENT_NOT_FOUND',self.refused('agent.status',{'id':a['id']},operator('someone-else')))
        self.assertIn('ASSIGNMENT_NOT_FOUND',self.refused('agent.step',{'id':a['id']},operator('someone-else')))
        self.assertIn('outside the authorized',self.refused('agent.step',{'id':a['id']},Principal('owner',frozenset({'read'}))))

    # -- profiles without a model ----------------------------------------------------------------------------------------------

    def test_request_profile_reads_the_owners_words(self):
        for text in ('add up the numbers on this page','Total the quantities here','sum the amounts on the page','how much do the values on this page come to',
                     'count the numbers on this page','What do the figures on this page add up to?','Please total the numbers in this document'):
            self.assertEqual(loop.request_profile(text),'numbers_on_page',text)
        for text in ('make these words bold','add a heading to this page','total recall here','the numbers on this page','write a poem about foxes','sum it up here','',None):
            self.assertIsNone(loop.request_profile(text),text)

    def test_auto_without_a_fit_waits_honestly_with_the_request_as_the_question(self):
        out=self.call('agent.assign',{'request':'write a poem about foxes'})
        a=out['assignment'];self.assertEqual((a['state'],a['reason'],a['profile'],a['doing_now']),('WAITING',loop.NO_FIT,'auto',loop.NO_FIT))
        self.assertEqual(out['sheet']['question'],'write a poem about foxes');self.assertEqual([n['text'] for n in a['needs_you']],[loop.NO_FIT])
        self.assertIsNone(self.call('agent.step',{'id':a['id']})['step']);self.assertEqual(self.call('agent.run',{'id':a['id']})['ran'],[])
        self.assertEqual(self.steps_of(a['investigation']),[])
        short=self.call('agent.assign',{'request':'run the given steps','profile':'operation_sequence'})['assignment']   # a profile that cannot plan says why
        self.assertEqual(short['state'],'WAITING');self.assertIn('needs steps',short['reason'])

    def test_auto_numbers_request_routes_to_the_numbers_profile_or_says_it_is_missing(self):
        a=self.call('agent.assign',{'request':'add up the numbers on this page','context':{'document':self.doc['id']}})['assignment']
        self.assertEqual(a['profile'],'numbers_on_page')
        if 'numbers_on_page' in profiles.PROFILES:
            self.assertEqual(a['state'],'READY');self.assertTrue(a['doing_now']);self.assertEqual(a['inspect'][1],{'label':'Document','kind':'document','id':self.doc['id']})
        else:
            self.assertEqual(a['state'],'WAITING');self.assertIn('not available in this build',a['reason']);self.assertIn('numbers_on_page',profiles.UNAVAILABLE)
        self.assertEqual(self.jobs(),0)

    # -- choosing among options ------------------------------------------------------------------------------------------------

    def test_choose_next_takes_the_model_pick_when_acceptable_after_polling(self):
        with patch.dict(profiles.PROFILES,{'operation_sequence':Choosy((True,True,False))}):
            a=self.assign(seq(('ledger.machine',{'section':'processor'},'First look'),('ledger.machine',{'section':'memory'},'Last look')))
            with patch.object(loop,'ask_model',return_value=JOB) as asked,patch.object(loop,'model_answer',side_effect=[None,{'choice':2,'text':'Option 2','state':'Completed'}]) as answered:
                out=self.call('agent.step',{'id':a['id']})
                self.assertEqual((out['step']['purpose'],out['next']),('First look','Asked the model to pick among 3 steps'))
                self.assertEqual(out['assignment']['doing_now'],'Waiting for the model to pick the next step')
                asked.assert_called_once();prompt=asked.call_args[0][2]
                self.assertLess(len(prompt),600);self.assertIn('A page with three masses',prompt);self.assertEqual(asked.call_args[0][3],3)
                self.assertEqual([line[:2] for line in prompt.splitlines()[-3:]],['1.','2.','3.'])
                waiting=self.call('agent.step',{'id':a['id']});self.assertIsNone(waiting['step']);self.assertEqual(waiting['assignment']['state'],'RUNNING');self.assertIn('Waiting for the model',waiting['next'])
                out=self.call('agent.step',{'id':a['id']});self.assertEqual((out['step']['key'],out['step']['purpose']),('storage','Look at storage'))
                self.assertTrue(out['assignment']['model_used']);self.assertEqual(answered.call_count,2);self.assertEqual(answered.call_args[0][2],JOB)
            rows=self.steps_of(a['investigation']);self.assertEqual([r['kind'] for r in rows],['STEP','MODEL_CHOICE','STEP'])
            program=json.loads(rows[1]['program']);self.assertEqual((program['operation'],program['arguments']['job'],program['arguments']['choices'],program['arguments']['mode']),('brain.ask',JOB,3,'choice'))
            self.assertEqual([o['key'] for o in program['arguments']['options']],['memory','storage','tools']);self.assertEqual(rows[1]['summary'],'model chose option 2: Look at storage')
            self.assertEqual(json.loads(rows[1]['inputs']),{'job':JOB});self.assertEqual(rows[1]['outcome'],'DONE')
            self.assertEqual(self.call('investigation.sheet',{'id':a['investigation']})['attempted'][-1]['purpose'],'Look at storage')  # choices are not 'attempted' operations
            done=self.call('agent.run',{'id':a['id']});self.assertEqual((done['assignment']['state'],[s['purpose'] for s in done['ran']]),('DONE',['Last look']))
        self.assertEqual(self.jobs(),0)

    def test_choose_next_default_paths_are_recorded_in_words(self):
        def fresh(acceptable):
            with patch.dict(profiles.PROFILES,{'operation_sequence':Choosy(acceptable)}):
                a=self.assign(seq(('ledger.machine',{'section':'processor'},'First look'),('ledger.machine',{'section':'memory'},'Last look')))
                return a['id'],a['investigation']
        # the model's pick is not acceptable here: the default is taken and the record says so
        ident,inv=fresh((True,True,False))
        with patch.dict(profiles.PROFILES,{'operation_sequence':Choosy((True,True,False))}),patch.object(loop,'ask_model',return_value=JOB),\
             patch.object(loop,'model_answer',return_value={'choice':3,'text':'Option 3','state':'Completed'}):
            self.call('agent.step',{'id':ident});out=self.call('agent.step',{'id':ident})
        self.assertEqual(out['step']['key'],'memory');self.assertTrue(out['assignment']['model_used'])
        choice=self.steps_of(inv)[1];self.assertEqual((choice['kind'],choice['summary'],choice['outcome']),('MODEL_CHOICE','model chose 3, not acceptable here, default taken: Look at memory','DONE'))
        # an answer without a number in range is unusable
        ident,inv=fresh((True,True,False))
        with patch.dict(profiles.PROFILES,{'operation_sequence':Choosy((True,True,False))}),patch.object(loop,'ask_model',return_value=JOB),\
             patch.object(loop,'model_answer',return_value={'choice':None,'text':'I cannot decide','state':'Completed'}):
            self.call('agent.step',{'id':ident});out=self.call('agent.step',{'id':ident})
        self.assertEqual(out['step']['key'],'memory');self.assertEqual(self.steps_of(inv)[1]['summary'],'model answer unusable, default taken: Look at memory')
        # the job ended without an answer: FAILED consultation, default taken, no model turn counted
        ident,inv=fresh((True,True,False))
        with patch.dict(profiles.PROFILES,{'operation_sequence':Choosy((True,True,False))}),patch.object(loop,'ask_model',return_value=JOB),\
             patch.object(loop,'model_answer',return_value={'choice':None,'text':'','state':'Failed'}):
            self.call('agent.step',{'id':ident});out=self.call('agent.step',{'id':ident})
        choice=self.steps_of(inv)[1];self.assertEqual((choice['outcome'],out['step']['key'],out['assignment']['model_used']),('FAILED','memory',False));self.assertIn('ended without an answer',choice['summary'])
        # no model loaded: the default at once, kind CHOICE
        ident,inv=fresh((True,True,False))
        with patch.dict(profiles.PROFILES,{'operation_sequence':Choosy((True,True,False))}),patch.object(loop,'ask_model',return_value=None):
            out=self.call('agent.step',{'id':ident});self.assertEqual(out['next'],'Next: Look at memory')
            out=self.call('agent.step',{'id':ident});self.assertEqual(out['step']['key'],'memory');self.assertFalse(out['assignment']['model_used'])
        choice=self.steps_of(inv)[1];self.assertEqual((choice['kind'],json.loads(choice['program'])['operation']),('CHOICE',loop.CHOICE_OPERATION));self.assertIn('no model loaded; default taken',choice['summary'])
        # one acceptable option: the model is not asked at all; the first acceptable option is the default even when it is not first
        ident,inv=fresh((False,True,False))
        with patch.dict(profiles.PROFILES,{'operation_sequence':Choosy((False,True,False))}),patch.object(loop,'ask_model',side_effect=AssertionError('must not ask')):
            self.call('agent.step',{'id':ident});out=self.call('agent.step',{'id':ident})
        self.assertEqual(out['step']['key'],'storage');self.assertIn('one acceptable option; taken',self.steps_of(inv)[1]['summary'])
        # Stop while the model is being asked: the consultation is recorded as dropped, nothing is taken
        ident,inv=fresh((True,True,False))
        with patch.dict(profiles.PROFILES,{'operation_sequence':Choosy((True,True,False))}),patch.object(loop,'ask_model',return_value=JOB):
            self.call('agent.step',{'id':ident})
        stopped=self.call('agent.stop',{'id':ident})['assignment'];self.assertIn('model choice was dropped',stopped['reason'])
        rows=self.steps_of(inv);self.assertEqual([(r['kind'],r['outcome']) for r in rows],[('STEP','DONE'),('MODEL_CHOICE','DROPPED')])
        self.assertEqual(self.jobs(),0)

    def test_pick_and_the_real_model_functions_without_a_model(self):
        self.assertEqual((loop.pick({'choice':2,'text':'Option 2'},3),loop.pick('Option 3',3),loop.pick({'choice':9,'text':'2'},3),loop.pick('I pick 7',3),loop.pick('none',3),loop.pick(None,3)),(2,3,2,None,None,None))
        self.assertIsNone(loop.ask_model(self.kernel,self.owner,'prompt',3))   # brain.status is not READY here: nothing is asked, nothing submitted
        self.assertEqual(loop.model_answer(self.kernel,self.owner,JOB)['choice'],None)   # no such job: an unusable answer, not an exception
        options=[{'key':k,'purpose':p,'step':profiles.step(k,p,'ledger.machine',{'section':k})} for k,p in LOOKS]
        prompt=loop.choice_prompt('x'*1000,options);self.assertLess(len(prompt),600)
        self.assertEqual(self.jobs(),0)

    # -- authority -----------------------------------------------------------------------------------------------------------

    def test_read_budget_bounds_the_principal_and_approve_never_passes(self):
        edit=('documents.edit',{'id':self.doc['id'],'expected_revision':1,'selection':{'block':0,'start':0,'end':4,'text':'Mass'},'change':{'bold':True}},'Make a word bold')
        read=('documents.get',{'id':self.doc['id']},'Read the page')
        a=self.assign(seq(read,edit),budget={'effects':'read'})
        out=self.call('agent.run',{'id':a['id']})
        self.assertEqual(out['assignment']['state'],'WAITING');self.assertIn('outside the authorized mode/scope',out['assignment']['reason'])
        self.assertEqual([(r['outcome'],r['authority']) for r in self.steps_of(a['investigation'])],[('DONE','read'),('FAILED','read')])
        self.assertEqual(self.call('documents.get',{'id':self.doc['id']})['document']['revision'],1)
        b=self.assign(seq(read,edit))
        out=self.call('agent.run',{'id':b['id']});self.assertEqual(out['assignment']['state'],'DONE')
        self.assertEqual({r['authority'] for r in self.steps_of(b['investigation'])},{'execute,read'})
        self.assertEqual(self.call('documents.get',{'id':self.doc['id']})['document']['revision'],2)
        c=self.assign(seq(('investigation.review',{'claim':MISSING,'decision':'RETIRE'},'Retire a claim')))
        out=self.call('agent.run',{'id':c['id']});self.assertEqual(out['assignment']['state'],'WAITING');self.assertIn('outside the authorized mode/scope',out['assignment']['reason'])
        self.assertEqual(self.jobs(),0)

    def test_record_step_records_without_running_and_withholds_secrets(self):
        sheet=self.call('investigation.create',{'question':'what was read'});reader=Principal('owner',frozenset({'read'}))
        row=investigations.record_step(self.kernel,sheet['id'],'documents.get',{'id':self.doc['id']},reader,'Read','DONE','words',{'a':1},{'document':'abc'},started=10.0,finished=10.5)
        self.assertEqual((row['seq'],row['kind'],row['outcome'],row['authority'],row['duplicate_of'],row['summary']),(1,'STEP','DONE','read',None,'words'))
        self.assertEqual(json.loads(row['program']),{'operation':'documents.get','arguments':{'id':self.doc['id']}});self.assertEqual(json.loads(row['inputs']),{'document':'abc'})
        again=investigations.record_step(self.kernel,sheet['id'],'documents.get',{'id':self.doc['id']},reader,'Read','DONE','words',{'a':1},{'document':'abc'},started=11.0,finished=11.5)
        self.assertEqual((again['seq'],again['duplicate_of']),(2,row['id']))
        other=investigations.record_step(self.kernel,sheet['id'],'documents.get',{'id':self.doc['id']},reader,'Read','DONE','words',{'a':2},{'document':'def'},started=12.0,finished=12.5)
        self.assertIsNone(other['duplicate_of'])
        choice=investigations.record_step(self.kernel,sheet['id'],loop.CHOICE_OPERATION,{'chosen':'x'},reader,'Choose','DONE','taken',None,{},kind='CHOICE')
        self.assertIsNone(choice['result_digest'])
        value=self.call('investigation.sheet',{'id':sheet['id']})
        self.assertEqual((value['used']['steps'],value['used']['seconds'],len(value['attempted'])),(4,1.5,3))   # the CHOICE row is recorded but is not an attempted operation
        self.assertEqual(loop.redact({'password':'x','nested':{'api_key':'y','ok':'z'},'rows':list(range(300))}),{'password':'[withheld]','nested':{'api_key':'[withheld]','ok':'z'},'rows':list(range(200))})
        cut=loop.recorded_arguments({'blocks':[{'text':'w'*100} for _ in range(200)]});self.assertEqual((cut['_truncated'],cut['_keys']),(True,['blocks']))
        self.assertEqual(loop.recorded_arguments({'id':JOB}),{'id':JOB})
        self.assertEqual(self.jobs(),0)

    # -- AGENT-02: work that continues while Ledger is closed -------------------------------------------------------------------

    def numbers(self):
        a=self.call('agent.assign',{'request':NUMBERS,'context':{'document':self.doc['id']}})['assignment']
        self.assertEqual((a['profile'],a['state']),('numbers_on_page','READY'));return a

    def expire(self,ident,owner='owner'):
        """As if the last driver's lease had run out (LEASE_SECONDS ago)."""
        with loop.opened(self.kernel) as db:state=loop.load(db,ident,owner);state['lease_until']=time.time()-1;loop.store(db,state)

    def setting(self,value):
        row=next(r for r in self.call('ledger.settings')['settings'] if r['key']==loop.SETTING)
        self.call('ledger.settings.set',{'key':loop.SETTING,'value':value,'expected_revision':row['revision']})

    def test_lease_rule_desktop_has_priority_and_the_service_waits_for_a_live_desktop_lease(self):
        a=self.assign(looks(4))
        first=self.call('agent.step',{'id':a['id']})   # the default driver is the desktop: it takes the lease
        row=first['assignment'];self.assertEqual((row['state'],row['driver'],row['lease_live'],row['service_steps'],first['step']['driver']),('RUNNING','desktop',True,0,'desktop'))
        with loop.opened(self.kernel) as db:lease=loop.load(db,a['id'],'owner')['lease_until']
        self.assertAlmostEqual(lease-time.time(),loop.LEASE_SECONDS,delta=3)
        words=self.refused('agent.step',{'id':a['id'],'driver':'service'})
        self.assertIn('ASSIGNMENT_DRIVEN_BY_DESKTOP',words);self.assertEqual(len(self.steps_of(a['investigation'])),1)   # nothing ran, nothing recorded
        self.assertEqual(loop.pump(self.kernel),[])   # the service skips what the desktop is driving
        self.expire(a['id'])                          # the desktop stopped stepping (Ledger crashed or the lease ran out)
        out=self.call('agent.step',{'id':a['id'],'driver':'service'});row=out['assignment']
        self.assertEqual((row['driver'],row['lease_live'],row['service_steps'],row['steps_used'],out['step']['driver']),('service',True,1,2,'service'))
        out=self.call('agent.step',{'id':a['id']});row=out['assignment']   # a live service lease never holds the desktop back
        self.assertEqual((row['driver'],row['service_steps'],row['steps_used']),('desktop',1,3))
        inputs=[json.loads(r['inputs']) for r in self.steps_of(a['investigation'])]
        self.assertEqual([i.get('driver') for i in inputs],[None,'service',None])   # the sheet says who stepped
        sheet=self.call('investigation.sheet',{'id':a['investigation']});self.assertEqual(json.loads(sheet['attempted'][1]['inputs'])['driver'],'service')
        self.call('agent.pause',{'id':a['id'],'reason':'by you'})   # a PAUSED assignment does not step for either driver; the lease reads not live
        held=self.call('agent.step',{'id':a['id'],'driver':'service'});self.assertIsNone(held['step']);self.assertFalse(held['assignment']['lease_live'])
        self.refused('agent.step',{'id':a['id'],'driver':'phone'})   # the schema refuses any other driver
        with self.assertRaisesRegex(ValueError,'ASSIGNMENT_DRIVER_UNKNOWN'):loop.step_once(self.kernel,a['id'],self.owner,driver='phone')
        self.assertEqual(self.jobs(),0)

    def test_release_hands_the_work_over_and_refuses_what_is_not_running(self):
        a=self.assign(looks(3))
        out=self.call('agent.release',{'id':a['id']});row=out['assignment']   # READY: the owner asked for it to run, so it is RUNNING for the service
        self.assertEqual((row['state'],row['driver'],row['lease_live'],row['steps_used']),('RUNNING',None,False,0));self.assertIn('Graphite service continues',out['next'])
        self.call('agent.step',{'id':a['id']});row=self.call('agent.release',{'id':a['id']})['assignment']
        self.assertEqual((row['state'],row['driver'],row['lease_live'],row['steps_used']),('RUNNING',None,False,1))
        self.assertEqual([r['id'] for r in loop.pump(self.kernel)],[a['id']])   # released: the service may step it at once
        self.setting(False)
        self.assertIn('is off',self.call('agent.release',{'id':a['id']})['next'])   # the words say nothing will step it
        self.call('agent.pause',{'id':a['id']})
        self.assertIn('ASSIGNMENT_NOT_RUNNING',self.refused('agent.release',{'id':a['id']}))
        self.assertIn('ASSIGNMENT_NOT_FOUND',self.refused('agent.release',{'id':a['id']},operator('someone-else')))
        self.assertIn('outside the authorized',self.refused('agent.release',{'id':a['id']},Principal('owner',frozenset({'read'}))))
        self.assertEqual(self.jobs(),0)

    def test_pump_steps_a_released_numbers_assignment_to_done_in_the_service(self):
        a=self.numbers();self.call('agent.release',{'id':a['id']})
        rounds=[]
        for _ in range(12):
            touched=loop.pump(self.kernel)
            if not touched:break
            rounds.append(touched);self.assertEqual(len(touched),1)   # one step per assignment per call
        self.assertEqual([r[0]['state'] for r in rounds],['RUNNING']*4+['DONE'])
        self.assertTrue(all(r[0]['step']['driver']=='service' for r in rounds))
        row=self.call('agent.status',{'id':a['id']})['assignments'][0]
        self.assertEqual((row['state'],row['driver'],row['service_steps'],row['steps_used'],row['lease_live']),('DONE','service',5,5,False))
        self.assertEqual([f['text'] for f in row['found']],['The 3 quantities on this page total 16 kg.'])
        doc=self.call('documents.get',{'id':self.doc['id']})['document'];self.assertTrue(doc['blocks'][-1]['text'].startswith('Total of the 3 quantities on this page: 16 kg'),doc['blocks'])
        rows=self.steps_of(a['investigation']);self.assertEqual([(r['kind'],json.loads(r['inputs']).get('driver')) for r in rows],[('STEP','service')]*5)
        self.assertEqual({r['authority'] for r in rows},{'execute,read'})   # read and execute only: never approve or candidate
        listed=self.call('agent.list')['assignments'][0];self.assertEqual((listed['driver'],listed['service_steps']),('service',5))
        self.assertEqual(loop.pump(self.kernel),[]);self.assertEqual(self.jobs(),0)

    def test_pump_does_nothing_when_the_setting_is_off_or_work_is_held_and_never_raises(self):
        from workbench import work_trail
        a=self.numbers();self.call('agent.release',{'id':a['id']})
        self.assertTrue(loop.continue_when_closed(self.kernel))   # the default is on
        self.setting(False);self.assertFalse(loop.continue_when_closed(self.kernel))
        self.assertEqual(loop.pump(self.kernel),[]);self.assertEqual(self.steps_of(a['investigation']),[])
        self.setting(True);work_trail.hold(self.kernel,self.owner)
        self.assertEqual(loop.pump(self.kernel),[]);self.assertEqual(self.steps_of(a['investigation']),[])
        work_trail.resume(self.kernel,self.owner)
        with self.kernel.db() as db:db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('ledger.'+loop.SETTING,json.dumps('yes')))
        self.assertFalse(loop.continue_when_closed(self.kernel))   # a stored value that is not a boolean reads as off
        with self.kernel.db() as db:db.execute('DELETE FROM settings WHERE key=?',('ledger.'+loop.SETTING,))
        with patch.object(loop,'step_once',side_effect=RuntimeError('disk gone')):
            out=loop.pump(self.kernel)
        self.assertEqual((out[0]['id'],out[0]['state']),(a['id'],'WAITING'))
        row=self.call('agent.status',{'id':a['id']})['assignments'][0]
        self.assertEqual((row['state'],row['reason']),('WAITING','The Graphite service could not step it: disk gone'))
        self.assertEqual(self.jobs(),0)

    def test_pause_all_pauses_ready_and_running_assignments_of_every_owner(self):
        mine=self.assign(looks(2));running=self.assign(looks(3));self.call('agent.step',{'id':running['id']})
        done=self.assign(looks(1));self.call('agent.run',{'id':done['id']})
        theirs=self.call('agent.assign',{'request':'run the given steps','profile':'operation_sequence','context':{'steps':looks(2)}},operator('someone-else'))['assignment']
        paused=loop.pause_all(self.kernel,'Master Stop')
        self.assertEqual(set(paused),{mine['id'],running['id'],theirs['id']})
        rows={r['id']:r for r in self.call('agent.status')['assignments']}
        self.assertEqual({k:(rows[k]['state'],rows[k]['paused_reason']) for k in (mine['id'],running['id'])},{mine['id']:('PAUSED','Master Stop'),running['id']:('PAUSED','Master Stop')})
        self.assertEqual(rows[done['id']]['state'],'DONE')
        other=self.call('agent.status',{'id':theirs['id']},operator('someone-else'))['assignments'][0];self.assertEqual((other['state'],other['paused_reason']),('PAUSED','Master Stop'))
        self.assertEqual(loop.pause_all(self.kernel,'again'),[]);self.assertEqual(loop.pump(self.kernel),[])
        self.assertEqual(self.jobs(),0)

    def test_an_agent01_record_gains_the_new_columns_once(self):
        old=Path(tempfile.mkdtemp(prefix='ledger-agent-old-'));self.addCleanup(lambda:__import__('shutil').rmtree(old,ignore_errors=True))
        import sqlite3
        db=sqlite3.connect(old/'x.sqlite3');db.row_factory=sqlite3.Row
        db.execute('''CREATE TABLE agent_assignments(id TEXT PRIMARY KEY, investigation TEXT, owner TEXT, profile TEXT, request TEXT,
            context TEXT, plan TEXT, cursor INTEGER, state TEXT, reason TEXT, budget TEXT, created REAL, updated REAL, paused_reason TEXT, model_job TEXT)''')
        db.execute('INSERT INTO agent_assignments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(JOB,MISSING,'owner','operation_sequence','old','{}','{}',0,'PAUSED','',json.dumps({}),1.0,1.0,'Ledger closed',None))
        loop.ensure(db);loop.ensure(db)   # idempotent
        columns=[r[1] for r in db.execute('PRAGMA table_info(agent_assignments)')];self.assertEqual(columns[-4:],['driver','lease_until','service_steps','authority'])
        state=loop.unpack(db.execute('SELECT * FROM agent_assignments').fetchone());db.close()
        self.assertEqual((state['driver'],state['lease_until'],state['service_steps'],state['state'],state['authority']),(None,None,0,'PAUSED',None))
        self.assertEqual(loop.driver_fields(state),{'driver':None,'lease_live':False,'lease_until':None,'service_steps':0})

    # -- AGENT-02 review fixes ---------------------------------------------------------------------------------------------------

    def service_paths(self,principal,ident,release_by=None):
        """The paths the bounded principal of the service's next step carries (the step reads capabilities, which echoes them)."""
        self.call('agent.release',{'id':ident},release_by or principal)
        with patch.object(loop,'dispatch_step',wraps=loop.dispatch_step) as spy:
            out=loop.pump(self.kernel)
        self.assertIn(ident,[r['id'] for r in out]);bounded=[c.args for c in spy.call_args_list if c.args[3]['id']==ident][-1][4]
        self.assertEqual((bounded.identity,sorted(bounded.scopes)),(principal.identity,['execute','read']));return bounded

    def test_the_service_steps_with_no_more_authority_than_the_owner_granted(self):
        steps=[{'operation':'capabilities','arguments':{},'purpose':'What may I touch (%d)'%n} for n in (1,2,3)]
        cli=Principal('local-client',frozenset({'read','execute'}))   # engineering_cli without --operator, an MCP client, the JSONL agent
        a=self.call('agent.assign',{'request':'run the given steps','profile':'operation_sequence','context':{'steps':steps}},cli)['assignment']
        with loop.opened(self.kernel) as db:self.assertEqual(loop.load(db,a['id'],'local-client')['authority'],loop.authority_of(cli))
        self.call('agent.step',{'id':a['id']},cli)   # the owner's own step
        bounded=self.service_paths(cli,a['id'])
        self.assertEqual(bounded.paths,cli.paths);self.assertNotIn('workbench/',bounded.paths)   # never the operator's paths
        self.assertEqual((bounded.tools,bounded.mode),(cli.tools,cli.mode))
        # the desktop owner (operator) keeps its own paths, so the service reaches what the desktop's step reaches
        mine=self.assign([{'operation':'capabilities','arguments':{},'purpose':'Look'}]*2)
        self.assertEqual(self.service_paths(self.owner,mine['id']).paths,self.owner.paths)
        # handing over narrows: released by a narrower principal of the same owner, the service steps with the narrower paths
        narrow=self.assign([{'operation':'capabilities','arguments':{},'purpose':'Look'}]*2)
        self.assertEqual(self.service_paths(self.owner,narrow['id'],release_by=Principal('owner',frozenset({'read','execute'}))).paths,cli.paths)
        # the operator's ceiling (host_ipc.delegation's rule) and read+execute bound whatever is recorded
        p=loop.owner_principal('local-client',{'scopes':['approve','candidate','execute','read'],'paths':['workbench/agent_loop.py','etc/','/root/','software/struthio/x/'],
                                               'tools':['no-such-tool'],'mode':'Root'})
        self.assertEqual((sorted(p.scopes),p.paths,p.tools,p.mode),(['execute','read'],('workbench/agent_loop.py','software/struthio/x/'),(),'Engineer'))
        # a record from before the authority column: the operator's paths only for the desktop owner, the defaults for anyone else
        self.assertEqual(loop.owner_principal('local-client').paths,Principal('local-client').paths)
        self.assertEqual(loop.owner_principal(operator().identity).paths,operator().paths)
        self.assertEqual(loop.narrowed({'scopes':['execute','read'],'paths':['workbench/'],'tools':['t1','t2'],'mode':'Autonomous'},
                                       {'scopes':['read'],'paths':['workbench/x.py','docs/'],'tools':['t2'],'mode':'Engineer'}),
                         {'scopes':['read'],'paths':['workbench/x.py'],'tools':['t2'],'mode':'Autonomous'})
        self.assertEqual(self.jobs(),0)

    def test_pump_checks_the_hold_the_setting_and_stop_again_before_every_step(self):
        from workbench import work_trail
        ids=[self.assign(looks(3))['id'] for _ in range(3)]
        for ident in ids:self.call('agent.release',{'id':ident})
        real=loop.step_once
        def then(effect):
            def step(*args,**kwargs):
                out=real(*args,**kwargs);effect();return out
            return step
        def taken():return sum(len(self.steps_of(self.call('agent.status',{'id':i})['assignments'][0]['investigation'])) for i in ids)
        # Master Stop holds work right after the first step of a batch (before it can take the dispatch lock): the batch ends there
        with patch.object(loop,'step_once',side_effect=then(lambda:work_trail.hold(self.kernel,self.owner))):
            out=loop.pump(self.kernel,guard=__import__('threading').RLock())
        self.assertEqual((len(out),taken()),(1,1));self.assertTrue(work_trail.execution_held(self.kernel))
        self.assertEqual(loop.pump(self.kernel),[]);work_trail.resume(self.kernel,self.owner)
        # the owner turns the setting off during a batch
        with patch.object(loop,'step_once',side_effect=then(lambda:self.setting(False))):out=loop.pump(self.kernel)
        self.assertEqual((len(out),taken()),(1,2));self.setting(True)
        # the service begins to close during a batch (Coordinator passes stop=self.closing.is_set)
        closing=[]
        with patch.object(loop,'step_once',side_effect=then(lambda:closing.append(True))):out=loop.pump(self.kernel,stop=lambda:bool(closing))
        self.assertEqual((len(out),taken()),(1,3))
        self.assertEqual(loop.pump(self.kernel,stop=lambda:True),[]);self.assertEqual(taken(),3)
        self.assertEqual(loop.pump(self.kernel,stop=lambda:1/0),[])   # a stop that cannot answer reads as stop; never raises
        self.assertEqual(len(loop.pump(self.kernel)),3);self.assertEqual(taken(),6)   # nothing held: one step each
        self.assertEqual(self.jobs(),0)

    def qt_driver(self):
        """An AgentDriver for a window attached to the Ledger service; its Kernel calls go to this test's Kernel."""
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        self.app=QApplication.instance() or QApplication([])
        import types
        from workbench import agent_qt
        for name,fn in (('summaries',lambda host:self.call('agent.list')['assignments']),
                        ('step_once',lambda host,ident:self.kernel.dispatch('agent.step',{'id':ident},self.owner)),
                        ('pause_one',lambda host,ident,reason:self.kernel.dispatch('agent.pause',{'id':ident,'reason':reason},self.owner))):
            held=patch.object(agent_qt,name,side_effect=fn);held.start();self.addCleanup(held.stop)
        host=types.SimpleNamespace(ledger_bridge=types.SimpleNamespace(kernel=types.SimpleNamespace(is_host_client=True)),_closing=False)
        driver=agent_qt.AgentDriver(host);self.addCleanup(lambda:driver.timer.stop())   # the closure keeps the driver (and its timer) alive until then
        later=[];timer=patch.object(agent_qt,'QTimer',types.SimpleNamespace(singleShot=lambda ms,context,fn:later.append((ms,fn))))
        timer.start();self.addCleanup(timer.stop)
        return agent_qt,host,driver,later

    def test_a_reopened_window_takes_back_work_a_crashed_window_left_and_today_says_why_it_paused(self):
        agent_qt,host,driver,later=self.qt_driver()
        self.assertEqual(agent_qt.LEASE_MS,loop.LEASE_SECONDS*1000)
        a=self.assign(looks(6));self.call('agent.step',{'id':a['id']})   # an attached window stepped it, then ended without release or pause
        self.assertEqual(driver.adopt(),[])                                # its desktop lease is still live: not taken yet ...
        self.assertEqual(len(later),1);self.assertTrue(loop.LEASE_SECONDS*1000-3000<later[0][0]<=agent_qt.LEASE_MS+agent_qt.ADOPT_MS,later)   # ... but looked at again when it runs out
        self.expire(a['id'])
        self.assertEqual(later[0][1](),[a['id']]);self.assertEqual(driver.running(),[a['id']]);self.assertEqual(len(later),1)
        driver.tick()                                                       # the reopened window's step takes the lease back
        row=self.call('agent.status',{'id':a['id']})['assignments'][0]
        self.assertEqual((row['driver'],row['lease_live'],row['service_steps'],row['steps_used']),('desktop',True,0,2))
        self.assertGreater(row['lease_until'],time.time())
        self.assertEqual(loop.pump(self.kernel),[])                         # the service leaves it to the window
        driver.pause_all('test')
        # a lease another window keeps renewing: adopt looks again at most ADOPT_AGAIN times, then leaves it alone
        b=self.assign(looks(12));self.call('agent.step',{'id':b['id']});later.clear();driver.adopt_tries=0
        for _ in range(agent_qt.ADOPT_AGAIN+2):
            self.call('agent.step',{'id':b['id']});self.assertEqual(driver.adopt(),[])
        self.assertEqual(len(later),agent_qt.ADOPT_AGAIN)
        now=time.time()
        self.assertEqual([agent_qt.adopt_delay([now+5],now),agent_qt.adopt_delay([None],now),agent_qt.adopt_delay([now-3],now),agent_qt.adopt_delay([now+500],now)],
                         [5000+agent_qt.TICK_MS,agent_qt.LEASE_MS+agent_qt.ADOPT_MS,agent_qt.TICK_MS,agent_qt.LEASE_MS+agent_qt.ADOPT_MS])
        # Today: a paused assignment the service stepped says why it paused, as AGENT-01's paused row does
        self.call('agent.release',{'id':b['id']});loop.pump(self.kernel);loop.pump(self.kernel)
        self.call('agent.pause',{'id':b['id'],'reason':'Master Stop'})
        rows=[(t,w) for t,w,_ in agent_qt.today_rows(host) if 'While Graphite was closed' in t]
        self.assertEqual(rows,[('While Graphite was closed, it took 2 steps on “run the given steps” · now paused (Master Stop)','resume')])
        self.assertEqual(agent_qt.closed_words({'service_steps':1,'updated':time.time(),'working_on':'x','state':'DONE','paused_reason':None}),
                         'While Graphite was closed, it took 1 step on “x” · now done')
        self.assertEqual(self.jobs(),0)


if __name__=='__main__':unittest.main()
