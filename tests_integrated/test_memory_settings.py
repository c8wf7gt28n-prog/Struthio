"""Owner profile settings, atomic history, precision and sharing boundaries."""
import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import ledger_control,settings_registry,stacy_control,memory_service
from workbench.engineering_kernel import Kernel,operator,Principal
from workbench.session import Session


class MemorySettingsTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name)
        self.root=self.base/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(self.base/'profile'),'ARC_LEDGER_CONCERN':str(self.base/'Concern')})
        env.start();self.addCleanup(env.stop);self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.session=Session(self.base/'profile/session.json',self.root);self.session.save();ledger_control.bind(self.kernel,self.session)
        self.seed=self.base/'seed.json';self.seed.write_text(json.dumps(dict(schema='arc.stacy.owner_personality_seed/1',name='Owner fixture',version='1',
            stacy_expression=dict(default_character='Keep ideas and evidence distinct.',inherit_from_ryan=[],retain_independently=[]))))

    def call(self,op,args=None,principal=None):
        result=self.kernel.dispatch(op,args or {},principal or self.owner);self.assertTrue(result['ok'],result);return result['result']
    def row(self,key,principal=None):return next(r for r in self.call('ledger.settings',principal=principal)['settings'] if r['key']==key)
    def imported(self,principal=None):return self.call('memory.profile.import',{'path':str(self.seed)},principal)
    def set(self,key,value):return self.call('ledger.settings.set',dict(key=key,value=value,expected_revision=self.row(key)['revision']))

    def test_missing_profile_is_not_fabricated_and_other_settings_still_read(self):
        rows=self.call('ledger.settings')['settings'];self.assertEqual(len(rows),len(settings_registry.SPECS))
        private=[r for r in rows if r['key'] in settings_registry.MEMORY_KEYS]
        self.assertEqual(len(private),5);self.assertTrue(all(r['stored'] is None and not r['editable'] and r['application_state']=='PROFILE_NOT_IMPORTED' for r in private))
        self.assertFalse(self.kernel.dispatch('ledger.settings.set',dict(key=private[0]['key'],value=True,expected_revision=private[0]['revision']),self.owner)['ok'])
        self.assertEqual(self.call('memory.profile')['state'],'NOT_IMPORTED')

    def test_existing_profile_is_the_only_value_store_and_original_bytes_are_unchanged(self):
        original=self.imported();before=self.call('memory.profile');key='memory.soft_half_life_days'
        result=self.set(key,135.25);after=self.call('memory.profile')
        self.assertEqual(after['parameters']['soft_half_life_days'],135.25);self.assertEqual(after['parameters']['weights'],before['parameters']['weights'])
        self.assertEqual(after['original_sha256'],original['original_sha256']);self.assertEqual(self.row(key)['effective'],135.25)
        self.assertEqual(self.call('ledger.settings.history',{'key':key})['changes'][0]['id'],result['id'])
        with self.kernel.db() as db:self.assertFalse(db.execute("SELECT 1 FROM settings WHERE key LIKE 'ledger.memory.%'").fetchone())

    def test_direct_legacy_changes_and_away_and_back_invalidate_the_profile_guard(self):
        self.imported();row=self.row('memory.profile.enabled')
        self.call('memory.profile.enable',{'enabled':False});self.call('memory.profile.enable',{'enabled':True})
        result=self.kernel.dispatch('ledger.settings.set',dict(key=row['key'],value=False,expected_revision=row['revision']),self.owner)
        self.assertFalse(result['ok']);self.assertIn('REVISION_CHANGED',result['error']['message'])
        fresh=self.row('memory.weight.owner_statement');parameters=copy.deepcopy(self.call('memory.profile')['parameters']);parameters['soft_half_life_days']=200
        self.call('memory.profile.configure',{'parameters':parameters})
        self.assertFalse(self.kernel.dispatch('ledger.settings.set',dict(key=fresh['key'],value=3,expected_revision=fresh['revision']),self.owner)['ok'])

    def test_undo_and_default_use_current_profile_and_refuse_newer_or_foreign_changes(self):
        self.imported();key='memory.weight.owner_statement';change=self.set(key,3.5)
        self.call('ledger.settings.undo',{'id':change['id']});self.assertEqual(self.row(key)['stored'],2)
        self.set(key,6);self.call('ledger.settings.restore',dict(key=key,expected_revision=self.row(key)['revision']));self.assertEqual(self.row(key)['stored'],2)
        latest=self.set(key,4);self.call('memory.profile.enable',{'enabled':False})
        self.assertFalse(self.call('ledger.settings.history',{'key':key})['changes'][0]['can_undo'])
        self.assertFalse(self.kernel.dispatch('ledger.settings.undo',{'id':latest['id']},self.owner)['ok'])
        self.assertFalse(self.kernel.dispatch('ledger.settings.undo',{'id':latest['id']},operator('other'))['ok'])

    def test_owner_modes_private_history_and_shared_activity_do_not_expose_new_profile_values(self):
        self.imported();change=self.set('memory.soft_half_life_days',321)
        other=self.row('memory.soft_half_life_days',operator('other'));self.assertIsNone(other['stored']);self.assertIsNone(other['latest_change'])
        self.assertNotIn(change['id'],json.dumps(self.call('ledger.settings.history',principal=operator('other'))))
        for principal in (Principal('owner',frozenset({'read','execute'})),Principal('owner',self.owner.scopes,mode='Tutor')):
            row=self.row('memory.profile.enabled',principal)
            self.assertFalse(self.kernel.dispatch('ledger.settings.set',dict(key=row['key'],value=False,expected_revision=row['revision']),principal)['ok'])
        context=self.call('ledger.context');self.assertTrue(settings_registry.MEMORY_KEYS.isdisjoint(context['settings']))
        self.assertTrue(settings_registry.MEMORY_KEYS.isdisjoint(r['key'] for r in context['settings_registry']))
        self.assertEqual(context['settings']['stacy.provider'],'local')

    def test_fractional_precision_bounds_and_disabled_effect_are_truthful(self):
        self.imported();key='memory.weight.owner_confirmed_choice';self.set(key,1e-20)
        self.assertEqual(self.row(key)['stored'],1e-20)
        before=self.call('memory.profile')
        for value in (0,-1,11,True,float('inf')):
            self.assertFalse(self.kernel.dispatch('ledger.settings.set',dict(key=key,value=value,expected_revision=self.row(key)['revision']),self.owner)['ok'])
        self.assertEqual(self.call('memory.profile'),before)
        self.set('memory.profile.enabled',False);row=self.row(key)
        self.assertEqual(row['stored'],1e-20);self.assertIsNone(row['effective']);self.assertEqual(row['application_state'],'PROFILE_DISABLED')

    def test_profile_and_journal_roll_back_together_if_shared_history_commit_fails(self):
        self.imported();before=self.call('memory.profile');row=self.row('memory.soft_half_life_days')
        with patch.object(ledger_control,'_trim_history',side_effect=ValueError('Controlled journal failure')):
            result=self.kernel.dispatch('ledger.settings.set',dict(key=row['key'],value=150,expected_revision=row['revision']),self.owner)
        self.assertFalse(result['ok']);self.assertEqual(self.call('memory.profile'),before)
        self.assertEqual(self.call('ledger.settings.history',{'key':row['key']})['changes'],[])

    def test_corrupt_optional_profile_does_not_block_other_settings_or_get_replaced(self):
        self.imported()
        with self.kernel.db() as db:db.execute("UPDATE stacy_memory SET payload=? WHERE kind='profile' AND owner=?",(b'non-text profile',self.owner.identity))
        rows=self.call('ledger.settings')['settings'];self.assertEqual(len(rows),len(settings_registry.SPECS))
        self.assertTrue(all(not r['editable'] and r['application_state']=='STORE_UNAVAILABLE' for r in rows if r['key'] in settings_registry.MEMORY_KEYS))
        self.assertEqual(next(r for r in rows if r['key']=='stacy.provider')['stored'],'local')

    def test_cloud_proposals_cannot_read_private_settings_through_direct_or_pipeline_routes(self):
        for operation,args in [('ledger.settings',{}),('ledger.settings',{'category':'Slate'}),('ledger.settings.effective',{'key':'memory.profile.enabled'}),('ledger.settings.history',{}),
                               ('language.parse',{'text':'ledger.settings {}'}),
                               ('language.parse',{'text':'ledger.commands {} | join @task:'+('a'*32)+' on id'})]:
            proposal=stacy_control.call(operation,args)
            self.assertTrue(stacy_control.cloud_private(operation,args))
            with self.assertRaises(ValueError):stacy_control.validate_actions([proposal],self.owner,provider=True)
        stacy_control.validate_actions([stacy_control.call('ledger.settings',{'category':'Appearance'})],self.owner,provider=True)
        stacy_control.validate_actions([stacy_control.call('ledger.settings.effective',{'key':'reading.code_pt'})],self.owner,provider=True)


if __name__=='__main__':unittest.main()
