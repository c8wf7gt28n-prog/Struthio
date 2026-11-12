"""Private return copies, optimistic revisions, bounds and integrity refusal."""
import json,os,tempfile,unittest,hashlib
from pathlib import Path
from unittest.mock import patch
from workbench import return_thread,ledger_control,stacy_control
from workbench.engineering_kernel import Kernel,operator,Principal
from workbench.session import Session


class ReturnThreadTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name)
        self.root=self.base/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(self.base/'profile'),'ARC_LEDGER_CONCERN':str(self.base/'Concern')})
        env.start();self.addCleanup(env.stop);self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.session=Session(self.base/'profile/session.json',self.root);self.session.save();ledger_control.bind(self.kernel,self.session)

    def call(self,op,args=None,principal=None):
        result=self.kernel.dispatch(op,args or {},principal or self.owner);self.assertTrue(result['ok'],result);return result['result']

    def keep(self,note='Return to the evidence.',drafts=None,revision=0,principal=None):
        return self.call('ledger.session.keep',dict(expected_revision=revision,note=note,drafts=drafts or []),principal)

    def read(self,principal=None):return self.call('ledger.session.read',principal=principal)

    def test_empty_read_does_not_create_a_return_table(self):
        self.assertEqual(self.read()['revision'],0)
        with self.kernel.db() as db:self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='session_handoffs'").fetchone())

    def test_restart_restores_exact_writing_without_executing_or_creating_a_record(self):
        draft=dict(id='project:unavailable',title='Évidence',text='@files:literal | do not execute this writing')
        with patch('subprocess.Popen',side_effect=AssertionError('No process launch')):
            first=self.keep(note='Start with the original question.\npoem',drafts=[draft])
            second=Kernel(self.root).dispatch('ledger.session.read',{},self.owner)
        self.assertTrue(second['ok']);self.assertEqual(second['result']['drafts'],[draft])
        self.assertEqual(first['note'],second['result']['note']);self.assertEqual(self.kernel.listing('jobs'),[])
        with self.kernel.db() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='desk_records'").fetchone():self.assertEqual(db.execute('SELECT count(*) FROM desk_records').fetchone()[0],0)

    def test_owner_workspace_and_mode_boundaries_hold(self):
        first=self.keep();other=self.read(operator('other'));self.assertEqual(other['revision'],0);self.assertEqual(other['note'],'')
        other_root=self.base/'other';other_root.mkdir();self.assertEqual(Kernel(other_root).dispatch('ledger.session.read',{},self.owner)['result']['revision'],0)
        for principal in (Principal('owner'),Principal('owner',self.owner.scopes,mode='Tutor')):
            self.assertEqual(self.read(principal)['note'],first['note'])
            self.assertFalse(self.kernel.dispatch('ledger.session.keep',dict(expected_revision=1,note='Denied',drafts=[]),principal)['ok'])
        self.assertEqual(self.read()['note'],first['note'])

    def test_stale_keep_cannot_overwrite_another_session(self):
        initial=self.read();self.keep(note='A newer return thread.')
        response=Kernel(self.root).dispatch('ledger.session.keep',dict(expected_revision=initial['revision'],note='Stale',drafts=[]),self.owner)
        self.assertFalse(response['ok']);self.assertIn('changed in another session',response['error']['message'])
        self.assertEqual(self.read()['note'],'A newer return thread.')

    def test_identical_keeps_do_not_churn_revisions_and_explicit_empty_copy_clears_writing(self):
        first=self.keep(drafts=[dict(id='cabinet:concern',title='',text='Retained writing')])
        again=self.keep(drafts=first['drafts'],revision=1);self.assertEqual(again['revision'],1);self.assertFalse(again['changed'])
        cleared=self.keep(note='',revision=1);self.assertEqual(cleared['revision'],2);self.assertEqual(cleared['drafts'],[])

    def test_budget_or_duplicate_failure_leaves_the_whole_saved_copy_unchanged(self):
        before=self.keep()
        cases=[[dict(id='project:'+str(i),title='',text='é'*60000) for i in range(3)],
               [dict(id='cabinet:concern',title='',text='First'),dict(id='cabinet:concern',title='',text='Second')],
               [dict(id='project:'+str(i),title='',text='Draft') for i in range(41)]]
        for drafts in cases:
            result=self.kernel.dispatch('ledger.session.keep',dict(expected_revision=1,note='Do not partly save',drafts=drafts),self.owner)
            self.assertFalse(result['ok']);self.assertEqual(self.read(),{k:v for k,v in before.items() if k!='changed'})

    def test_corrupt_saved_copy_is_not_read_or_overwritten_even_with_matching_revision(self):
        self.keep()
        for raw in ('changed',b'non-text SQLite payload'):
            with self.kernel.db() as db:db.execute('UPDATE session_handoffs SET payload=? WHERE owner=?',(raw,self.owner.identity))
            for operation,args in [('ledger.session.read',{}),('ledger.session.keep',dict(expected_revision=1,note='No replacement',drafts=[]))]:
                result=self.kernel.dispatch(operation,args,self.owner);self.assertFalse(result['ok']);self.assertIn('integrity',result['error']['message'])
            with self.kernel.db() as db:self.assertEqual(db.execute('SELECT payload FROM session_handoffs').fetchone()[0],raw)

    def test_valid_digest_does_not_make_an_invalid_saved_shape_acceptable(self):
        self.keep();raw=json.dumps(dict(note='Unexpected',drafts=[],context=None,execute='jobs.submit'))
        with self.kernel.db() as db:db.execute('UPDATE session_handoffs SET payload=?,digest=?',(raw,hashlib.sha256(raw.encode()).hexdigest()))
        self.assertFalse(self.kernel.dispatch('ledger.session.read',{},self.owner)['ok'])

    def test_shared_schemas_and_cloud_private_rules_reject_unexpected_writes(self):
        for args in ({'expected_revision':False,'note':'Invalid','drafts':[]},
                     {'expected_revision':0,'note':'x'*8001,'drafts':[]},
                     {'expected_revision':0,'note':'Bad key','drafts':[dict(id='project:x',title='',text='x',operation='jobs.submit')]}):
            self.assertFalse(self.kernel.dispatch('ledger.session.keep',args,self.owner)['ok'])
        for operation,args in [('ledger.session.read',{}),('ledger.session.keep',dict(expected_revision=0,note='x',drafts=[]))]:
            proposal=stacy_control.call(operation,args)
            with self.assertRaises(ValueError):stacy_control.validate_actions([proposal],self.owner,provider=True)
            stacy_control.validate_actions([proposal],self.owner,provider=True,private_local=True)


if __name__=='__main__':unittest.main()
