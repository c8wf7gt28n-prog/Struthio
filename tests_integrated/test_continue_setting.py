"""agent.continue_when_closed: whether a running assignment continues in the Graphite service when the window closes. A Kernel
settings boolean, project private, owner only, default on, outside the session batch; the agent loop reads the same row."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from workbench import agent_loop, ledger_control, settings_registry
from workbench.engineering_kernel import Kernel, operator, Principal
from workbench.session import Session

KEY='agent.continue_when_closed'


class ContinueWhenClosedSetting(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);base=Path(temporary.name)
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(base/'profile'),'ARC_LEDGER_CONCERN':str(base/'Concern')})
        env.start();self.addCleanup(env.stop);self.root=base/'workspace';self.root.mkdir()
        for name,word in (('launch','no worker may start'),('submit','no job may be submitted')):
            held=patch.object(Kernel,name,side_effect=AssertionError(word));held.start();self.addCleanup(held.stop)
        self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.session=Session(base/'profile/session.json',self.root);self.session.save();ledger_control.bind(self.kernel,self.session)
        self.assistant=Principal('Slate:typed',frozenset({'read','execute'}))

    def call(self,op,args=None,principal=None):
        response=self.kernel.dispatch(op,args or {},principal or self.owner)
        self.assertTrue(response['ok'],response);return response['result']

    def row(self):return next(r for r in self.call('ledger.settings')['settings'] if r['key']==KEY)

    def test_the_definition_is_a_project_private_owner_only_boolean_outside_the_batch(self):
        self.assertEqual(settings_registry.CONTINUE_KEY,KEY);row=self.row()
        self.assertEqual((row['type'],row['default'],row['stored'],row['root'],row['group'],row['scope_id'],row['store'],row['requires_owner']),
                         ('boolean',True,True,'Slate','Assignments','project_private','Kernel settings: ledger.'+KEY,True))
        enum=ledger_control.FIELDS['ledger.settings.apply'][0]['changes']['items']['properties']['key']['enum'];self.assertNotIn(KEY,enum)
        self.assertIn(KEY,settings_registry.OWNER_KEYS)

    def test_only_the_owner_sets_it_and_the_agent_loop_reads_the_same_row(self):
        self.assertTrue(agent_loop.continue_when_closed(self.kernel))
        refused=self.kernel.dispatch('ledger.settings.set',{'key':KEY,'value':False},self.assistant);self.assertFalse(refused['ok'])
        self.assertTrue(self.row()['stored']);self.assertTrue(agent_loop.continue_when_closed(self.kernel))
        self.call('ledger.settings.set',{'key':KEY,'value':False,'expected_revision':self.row()['revision']})
        self.assertEqual((self.row()['stored'],agent_loop.continue_when_closed(self.kernel)),(False,False))
        self.call('ledger.settings.set',{'key':KEY,'value':True,'expected_revision':self.row()['revision']})
        self.assertEqual((self.row()['stored'],agent_loop.continue_when_closed(self.kernel)),(True,True))


if __name__=='__main__':unittest.main()
