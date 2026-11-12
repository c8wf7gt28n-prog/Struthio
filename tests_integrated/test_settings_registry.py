"""Settings store, consumer readback, authority and concurrent-edit boundaries."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from workbench import ledger_control, settings_registry, stacy_control
from workbench.engineering_kernel import Kernel, operator, Principal
from workbench.session import Session


class SettingsRegistryTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);base=Path(temporary.name)
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(base/'profile'),'ARC_LEDGER_CONCERN':str(base/'Concern')})
        env.start();self.addCleanup(env.stop);self.root=base/'workspace';self.root.mkdir()
        self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.s=Session(base/'profile/session.json',self.root);self.s.save();ledger_control.bind(self.kernel,self.s)
        self.slate=Principal('Slate:typed',frozenset({'read','execute'}))

    def call(self,op,args=None,principal=None):
        response=self.kernel.dispatch(op,args or {},principal or self.owner)
        self.assertTrue(response['ok'],response);return response['result']

    def row(self,key):return next(r for r in self.call('ledger.settings')['settings'] if r['key']==key)

    def set(self,key,value,principal=None):
        return self.call('ledger.settings.set',dict(key=key,value=value,expected_revision=self.row(key)['revision']),principal)

    def test_human_and_typed_slate_edit_same_store_and_reversible_history(self):
        human=self.set('reading.code_pt',18)
        actions=stacy_control.parse('/set reading.code_pt 19',self.kernel)
        stacy_control.validate_actions(actions,self.slate,provider=True,private_local=True)
        slate=self.call(actions[0]['operation'],actions[0]['arguments'],self.slate)
        saved=Session(self.s.path,self.root);self.assertEqual(saved.state['reading_profile']['code_pt'],19)
        rows=self.call('ledger.settings.history',{'key':'reading.code_pt'})['changes']
        self.assertEqual([r['actor'] for r in rows],['Slate:typed','owner'])
        self.assertFalse(rows[1]['can_undo']);self.assertTrue(rows[0]['can_undo'])
        restored=self.call('ledger.settings.undo',{'id':slate['id']})
        self.assertEqual(restored['restores'],slate['id']);self.assertEqual(self.row('reading.code_pt')['value'],human['after'])
        rows=self.call('ledger.settings.history',{'key':'reading.code_pt'})['changes'];self.assertTrue(rows[1]['undone'])

    def test_revision_detects_change_away_and_back_to_same_value(self):
        opened=self.row('reading.code_pt');self.set('reading.code_pt',18);self.set('reading.code_pt',opened['value'])
        response=self.kernel.dispatch('ledger.settings.set',dict(key=opened['key'],value=20,expected_revision=opened['revision']),self.owner)
        self.assertFalse(response['ok']);self.assertIn('SETTING_REVISION_CHANGED',response['error']['message'])
        self.assertEqual(self.row('reading.code_pt')['value'],opened['value'])

    def test_legacy_expected_value_and_unknown_keys_still_validate(self):
        self.call('ledger.settings.set',{'key':'reading.code_pt','value':18,'expected':14})
        for args in ({'key':'reading.code_pt','value':20,'expected':14},{'key':'imaginary.reply_style','value':'brief'}):
            self.assertFalse(self.kernel.dispatch('ledger.settings.set',args,self.owner)['ok'])

    def test_invalid_values_leave_profile_and_journal_unchanged(self):
        original=self.s.path.read_bytes()
        for key,value in [('reading.code_pt',200),('reading.reduce_motion',1),('reading.family','bad; font'),('stacy.provider','invented')]:
            self.assertFalse(self.kernel.dispatch('ledger.settings.set',dict(key=key,value=value),self.owner)['ok'])
        self.assertEqual(self.s.path.read_bytes(),original);self.assertEqual(self.call('ledger.settings.history')['changes'],[])

    def test_saved_value_is_not_claimed_as_active_without_readback(self):
        self.set('reading.code_pt',18);row=self.row('reading.code_pt')
        self.assertEqual(row['stored'],18);self.assertIsNone(row['effective'])
        self.assertEqual(row['application_state'],'NO_LIVE_DESKTOP_READBACK')

    def test_pending_launch_and_font_fallback_use_consumer_receipts(self):
        self.set('workspace.startup','home');self.set('reading.family','Unavailable Fictional Font')
        leases=self.root/'.ledger/desktops';leases.mkdir(exist_ok=True)
        (leases/'test-consumer.json').write_text(json.dumps({'pid':os.getpid()}))
        ledger_control.publish_settings_runtime(self.kernel,'test-consumer',{
            'workspace.startup':{'requested':'last','effective':'last'},
            'reading.family':{'requested':'Unavailable Fictional Font','effective':'DejaVu Sans'}})
        startup=self.row('workspace.startup');self.assertEqual(startup['effective'],'last')
        self.assertEqual(startup['application_state'],'PENDING_NEXT_LAUNCH')
        self.assertEqual(self.row('reading.family')['application_state'],'APPLIED_WITH_FALLBACK')
        self.assertEqual(self.row('reading.family')['effective'],'DejaVu Sans')
        (leases/'test-consumer.json').unlink()
        self.assertEqual(self.row('reading.family')['application_state'],'NO_LIVE_DESKTOP_READBACK')

    def test_disk_read_is_fresh_when_bound_profile_is_older(self):
        external=Session(self.s.path,self.root);external.state['reading_profile']={'code_pt':22};external.save()
        self.assertEqual(self.row('reading.code_pt')['stored'],22)
        self.assertNotIn('reading_profile',self.s.state)

    def test_restore_uses_real_default_and_revision_guard(self):
        self.set('reading.code_pt',18);opened=self.row('reading.code_pt')
        self.call('ledger.settings.restore',{'key':opened['key'],'expected_revision':opened['revision']})
        self.assertEqual(self.row('reading.code_pt')['value'],14)
        self.assertFalse(self.kernel.dispatch('ledger.settings.restore',{'key':opened['key'],'expected_revision':opened['revision']},self.owner)['ok'])

    def test_restore_and_undo_do_not_bypass_owner_or_provider_boundaries(self):
        for key in ('stacy.provider','stacy.enabled','operations.services_enabled'):
            row=self.row(key);args={'key':key,'expected_revision':row['revision']}
            self.assertFalse(self.kernel.dispatch('ledger.settings.restore',args,self.slate)['ok'])
            with self.assertRaises(ValueError):
                stacy_control.validate_actions([stacy_control.call('ledger.settings.restore',args)],self.slate,provider=True,private_local=True)
        changed=self.set('stacy.enabled',False)
        self.assertFalse(self.kernel.dispatch('ledger.settings.undo',{'id':changed['id']},self.slate)['ok'])
        self.assertFalse(self.kernel.dispatch('ledger.settings.set',{'key':'reading.code_pt','value':18},Principal('reader'))['ok'])

    def test_undo_refuses_a_newer_same_value_revision(self):
        first=self.set('reading.code_pt',18);self.set('reading.code_pt',18)
        self.assertFalse(self.kernel.dispatch('ledger.settings.undo',{'id':first['id']},self.owner)['ok'])
        self.assertEqual(self.row('reading.code_pt')['value'],18)

    def test_external_profile_undo_receipt_recovers_atomic_journal_state(self):
        import time
        first=self.set('reading.code_pt',18)
        profile=Session(self.s.path,self.root);profile.state['reading_profile']['code_pt']=14;profile.save()
        receipt=dict(id='recovery-undo',key='reading.code_pt',before=18,after=14,actor='owner',at=time.time(),
                     undone=False,scope='session_profile',restores=first['id'],profile_hash=ledger_control._profile_hash(self.kernel))
        directory=self.kernel.state/'settings_delivery';directory.mkdir(exist_ok=True)
        (directory/'recovery-undo.json').write_text(json.dumps(receipt))
        self.assertEqual(ledger_control.reconcile_receipts(self.kernel)[0]['state'],'RECONCILED_APPLIED')
        rows=self.call('ledger.settings.history',{'key':'reading.code_pt'})['changes']
        self.assertEqual(rows[0]['id'],'recovery-undo');self.assertTrue(rows[1]['undone'])

    def test_priority_policy_readback_never_claims_running_process_effect(self):
        with patch('os.setpriority',create=True) as priority,patch('subprocess.Popen') as spawn:
            self.set('operations.priority','background');row=self.row('operations.priority')
            self.assertEqual(row['effective'],'background');self.assertEqual(row['application_state'],'NEXT_USE_POLICY')
            self.assertIn('not a claim',row['effective_source']);priority.assert_not_called();spawn.assert_not_called()
        with self.kernel.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0],0)

    def test_scope_is_real_and_navigation_is_separate_from_cabinet(self):
        rows=self.call('ledger.settings')['settings'];nodes=settings_registry.nodes()
        self.assertEqual({(r['id'],r['label']) for r in nodes if r['parent'] is None},{('settings:ledger','Workspace'),('settings:slate','Assistant')})  # GRAPHITE-01: shown as Workspace and Assistant; ids and root keys unchanged
        self.assertEqual({r['target'] for r in nodes if r['role']=='setting'},{r['key'] for r in rows})
        self.assertTrue(all(r['provider']=='shared_settings' for r in nodes))
        for row in rows:self.assertEqual(row['supported_scopes'],[row['scope_id']]);self.assertEqual(row['overrides'],[])
        self.assertEqual(self.row('stacy.provider')['scope_id'],'project_private')
        self.assertEqual(self.row('stacy.reactions')['scope_id'],'session_profile')

    def test_slate_context_preserves_legacy_values_and_effective_metadata(self):
        self.set('reading.code_pt',18)
        context=self.call('ledger.context');rows={r['key']:r for r in context['settings_registry']}
        self.assertEqual(context['settings']['reading.code_pt'],rows['reading.code_pt']['stored'])
        self.assertIsNone(rows['reading.code_pt']['effective'])
        self.assertEqual(rows['reading.code_pt']['scope_id'],'session_profile')
        self.assertNotIn('key',context['settings']);self.assertNotIn('GEMINI_API_KEY',json.dumps(context))

    # -- robustness (INTEGRATION-01) ------------------------------------------------------
    def test_history_tolerates_journal_rows_of_retired_or_foreign_keys(self):
        import time
        orphan=dict(id='orphan1',key='retired.setting',before=1,after=2,actor='owner',at=time.time(),undone=False,scope='session_profile')
        with self.kernel.db() as db:db.execute('INSERT INTO settings VALUES(?,?)',('ledger.change.orphan1',json.dumps(orphan)))
        self.set('reading.code_pt',18)
        rows=self.call('ledger.settings.history')['changes'];foreign=next(r for r in rows if r['id']=='orphan1')
        self.assertTrue(foreign['orphaned']);self.assertFalse(foreign['can_undo']);self.assertTrue(rows[0]['can_undo'])
        self.assertEqual([r['key'] for r in self.call('ledger.settings.history',{'key':'reading.code_pt'})['changes']],['reading.code_pt'])
        self.assertFalse(self.kernel.dispatch('ledger.settings.undo',{'id':'orphan1'},self.owner)['ok'])
        self.assertEqual(self.row('reading.code_pt')['stored'],18)

    def test_corrupt_priority_store_is_one_unavailable_row_that_default_repairs(self):
        path=self.root/'.ledger/master-stop/priority.json';path.parent.mkdir(parents=True,exist_ok=True)
        for broken in ('not json','{"mode":"sideways"}'):
            path.write_text(broken);row=self.row('operations.priority')
            self.assertEqual((row['application_state'],row['editable'],row['value'],row['repairable']),('STORE_UNAVAILABLE',False,None,True))
            self.assertNotIn('sideways',json.dumps(self.call('ledger.context')['settings']));self.assertIsNone(self.call('ledger.context')['settings']['operations.priority'])
            self.assertEqual(path.read_text(),broken)
        self.set('reading.code_pt',18);self.assertEqual(self.row('reading.code_pt')['stored'],18)
        with patch('os.setpriority',create=True) as priority,patch('subprocess.Popen') as spawn:
            self.call('ledger.settings.restore',{'key':'operations.priority','expected_revision':self.row('operations.priority')['revision']})
            priority.assert_not_called();spawn.assert_not_called()
        row=self.row('operations.priority');self.assertEqual((row['stored'],row['editable'],row['application_state']),('normal',True,'NEXT_USE_POLICY'))
        change=self.call('ledger.settings.history',{'key':'operations.priority'})['changes'][0]
        self.assertEqual((change['before'],change['after']),(None,'normal'));self.assertFalse(self.kernel.dispatch('ledger.settings.undo',{'id':change['id']},self.owner)['ok'])

    def test_tampered_kernel_table_value_is_reported_not_read_back_as_a_choice(self):
        with self.kernel.db() as db:
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('ledger.stacy.provider','"invented"'))
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('ledger.stacy.actions','"yes"'))
        for key in ('stacy.provider','stacy.actions'):
            row=self.row(key);self.assertEqual((row['application_state'],row['editable'],row['value'],row['effective'],row['repairable']),('STORE_UNAVAILABLE',False,None,None,True))
        self.assertNotIn('invented',json.dumps(self.call('ledger.context')));self.assertNotIn('invented',json.dumps(self.call('ledger.settings.effective',{'key':'stacy.provider'})))
        self.assertFalse(self.kernel.dispatch('ledger.settings.set',{'key':'stacy.provider','value':'local'},self.slate)['ok'])  # owner boundary unchanged
        self.call('ledger.settings.restore',{'key':'stacy.provider','expected_revision':self.row('stacy.provider')['revision']})
        self.call('ledger.settings.set',{'key':'stacy.actions','value':False,'expected_revision':self.row('stacy.actions')['revision']})
        self.assertEqual((self.row('stacy.provider')['stored'],self.row('stacy.actions')['stored']),('local',False))
        self.assertTrue(all(r['editable'] for r in self.call('ledger.settings')['settings'] if r['key'] in ('stacy.provider','stacy.actions')))

    # -- the shape of the registry --------------------------------------------------------------------
    def test_every_definition_is_listed_once_and_single_key_settings_stay_out_of_the_batch(self):
        # Which definitions exist is the recorded registry's business (tools/check_release.py); here the shape the store relies on.
        keys=[r['key'] for r in settings_registry.SPECS];self.assertEqual(len(keys),len(set(keys)),'duplicate setting key')
        self.assertEqual(sorted(r['key'] for r in self.call('ledger.settings')['settings']),sorted(keys))
        enum=ledger_control.FIELDS['ledger.settings.apply'][0]['changes']['items']['properties']['key']['enum']
        self.assertEqual(set(enum),set(settings_registry.SESSION_BATCH_KEYS));self.assertTrue(set(enum)<=set(keys))
        for key in ('hardware.category_views','appearance.writing_marker','agent.continue_when_closed'):self.assertNotIn(key,enum)  # single-key Set only

    def test_runtime_receipts_of_departed_desktops_are_pruned(self):
        leases=self.root/'.ledger/desktops';leases.mkdir(exist_ok=True)
        for n in range(5):
            (leases/('desk-%d.json'%n)).write_text(json.dumps({'pid':os.getpid()}))
            ledger_control.publish_settings_runtime(self.kernel,'desk-%d'%n,{'reading.family':{'requested':'A','effective':'A'}})
        def count():
            with self.kernel.db() as db:return db.execute("SELECT count(*) FROM settings WHERE key LIKE 'ledger.settings_runtime.%'").fetchone()[0]
        self.assertEqual(count(),5)
        for n in (2,3,4):(leases/('desk-%d.json'%n)).unlink()
        ledger_control.publish_settings_runtime(self.kernel,'desk-0',{'reading.family':{'requested':'A','effective':'A'}})
        self.assertEqual(count(),2);self.assertEqual(len(self.row('reading.family')['desktop_effects']),2)


if __name__=='__main__':unittest.main()
