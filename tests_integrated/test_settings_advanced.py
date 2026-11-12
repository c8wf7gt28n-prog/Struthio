"""Existing-store adapters, shared profile batches and credential preservation."""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from workbench import clip,ledger_control,stacy_control
from workbench.engineering_kernel import Kernel,operator,Principal
from workbench.session import Session


class AdvancedSettingsTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);base=Path(temporary.name)
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(base/'profile'),'ARC_LEDGER_CONCERN':str(base/'Concern')})
        env.start();self.addCleanup(env.stop);self.base=base;self.root=base/'workspace';self.root.mkdir()
        self.kernel=Kernel(self.root);self.owner=operator('owner');self.slate=Principal('Slate:typed',frozenset({'read','execute'}))
        self.session=Session(base/'profile/session.json',self.root);self.session.save();ledger_control.bind(self.kernel,self.session)

    def call(self,op,args=None,principal=None):
        response=self.kernel.dispatch(op,args or {},principal or self.owner)
        self.assertTrue(response['ok'],response);return response['result']

    def row(self,key):return next(r for r in self.call('ledger.settings')['settings'] if r['key']==key)
    def set(self,key,value,principal=None):return self.call('ledger.settings.set',dict(key=key,value=value,expected_revision=self.row(key)['revision']),principal)
    def batch(self,values):return [dict(key=k,value=v,expected_revision=self.row(k)['revision']) for k,v in values.items()]

    def test_cursive_reopens_and_undo_restores_actual_existing_field(self):
        change=self.set('appearance.cursive',False,self.slate)
        self.assertFalse(Session(self.session.path,self.root).state['cursive'])
        self.call('ledger.settings.undo',{'id':change['id']})
        self.assertTrue(Session(self.session.path,self.root).state['cursive'])

    def test_integer_layout_ranges_and_page_names_validate_without_writes(self):
        original=self.session.path.read_bytes()
        for key,value in [('layout.navigator_width',159),('layout.navigator_width',285.5),('layout.output_height',True),('layout.output_tab','Imaginary page')]:
            self.assertFalse(self.kernel.dispatch('ledger.settings.set',dict(key=key,value=value),self.owner)['ok'])
        self.assertEqual(self.session.path.read_bytes(),original)
        self.set('layout.navigator_width',420);self.set('layout.output_tab','Problems')
        fresh=Session(self.session.path,self.root);self.assertEqual(fresh.layout['navigator_width'],420);self.assertEqual(fresh.layout['output_tab'],'Problems')

    def test_batch_checks_every_revision_before_a_single_profile_write(self):
        changes=self.batch({'reading.code_pt':18,'reading.prose_pt':20})
        self.set('reading.prose_pt',22)
        before=self.session.path.read_bytes();history=self.call('ledger.settings.history')['changes']
        response=self.kernel.dispatch('ledger.settings.apply',{'changes':changes},self.owner)
        self.assertFalse(response['ok']);self.assertIn('SETTING_REVISION_CHANGED',response['error']['message'])
        self.assertEqual(self.session.path.read_bytes(),before);self.assertEqual(self.call('ledger.settings.history')['changes'],history)
        self.assertEqual(self.row('reading.code_pt')['stored'],14)

    def test_valid_batch_writes_once_and_keeps_per_key_undo_with_shared_batch(self):
        changes=self.batch({'reading.code_pt':18,'reading.prose_pt':20})
        with patch.object(self.session,'save',wraps=self.session.save) as save:
            result=self.call('ledger.settings.apply',{'changes':changes});self.assertEqual(save.call_count,1)
        records=result['changes'];self.assertEqual({r['batch'] for r in records},{result['batch']})
        self.assertEqual([r['after'] for r in records],[18,20])
        self.call('ledger.settings.undo',{'id':records[0]['id']})
        self.assertEqual(self.row('reading.code_pt')['stored'],14);self.assertEqual(self.row('reading.prose_pt')['stored'],20)

    def test_batch_rejects_duplicate_keys_and_cannot_bypass_provider_authority(self):
        changes=self.batch({'reading.code_pt':18});self.assertFalse(self.kernel.dispatch('ledger.settings.apply',{'changes':changes*2},self.owner)['ok'])
        changes=[dict(key='gemini.include_file',value=True,expected_revision=self.row('gemini.include_file')['revision'])]
        self.assertFalse(self.kernel.dispatch('ledger.settings.apply',{'changes':changes},self.slate)['ok']);self.assertFalse(clip.settings_path().exists())

    def receipt(self,partial=False):
        records=[]
        for ident,key,before,after in [('batch-a','reading.code_pt',14,18),('batch-b','reading.prose_pt',16,20)]:
            records.append(dict(id=ident,key=key,before=before,after=after,actor='owner',at=time.time(),undone=False,scope='session_profile',batch='delivery-batch'))
        fresh=Session(self.session.path,self.root);fresh.state['reading_profile']={'code_pt':18,'prose_pt':16 if partial else 20};fresh.save()
        document=dict(schema='arc.settings-delivery-batch/1',id='delivery-batch',changes=records,profile_hash=ledger_control._profile_hash(self.kernel))
        directory=self.kernel.state/'settings_delivery';directory.mkdir(exist_ok=True);path=directory/'delivery-batch.json';path.write_text(json.dumps(document));return path

    def test_completed_profile_delivery_recovers_all_batch_history(self):
        path=self.receipt();result=ledger_control.reconcile_receipts(self.kernel)
        self.assertEqual(result,[dict(id='delivery-batch',state='RECONCILED_APPLIED')]);self.assertFalse(path.exists())
        self.assertEqual(len(self.call('ledger.settings.history')['changes']),2)

    def test_mixed_profile_delivery_is_preserved_for_review_without_replay(self):
        path=self.receipt(partial=True);before=self.session.path.read_bytes()
        result=ledger_control.reconcile_receipts(self.kernel)
        self.assertEqual(result,[dict(id='delivery-batch',state='CONFLICT')]);self.assertTrue(path.exists())
        self.assertEqual(self.session.path.read_bytes(),before);self.assertEqual(self.call('ledger.settings.history')['changes'],[])

    def test_provider_adapter_retains_credential_bytes_without_decrypting_or_exposing_them(self):
        path=clip.settings_path();path.parent.mkdir(exist_ok=True)
        opaque={'dpapi':'opaque-fixture-secret'};path.write_text(json.dumps({'schema':clip.SCHEMA,'key':opaque,'model':'old-model','include_file':False}))
        with patch.object(clip,'open_key',side_effect=AssertionError('Registry must not open credentials')):
            changed=self.set('gemini.model','preferred-model');self.set('gemini.include_file',True)
            visible=json.dumps([self.call('ledger.settings'),self.call('ledger.settings.history'),self.call('ledger.context')])
        self.assertEqual(json.loads(path.read_text())['key'],opaque);self.assertNotIn('opaque-fixture-secret',visible)
        self.assertEqual(self.row('gemini.model')['application_state'],'NEXT_USE_POLICY')
        with self.kernel.db() as db:self.assertEqual(db.execute("SELECT count(*) FROM settings WHERE key LIKE 'ledger.gemini.%'").fetchone()[0],0)
        if os.name!='nt':self.assertEqual(path.stat().st_mode&0o777,0o600)

    def test_provider_set_default_undo_and_proposals_keep_owner_boundary(self):
        changed=self.set('gemini.include_file',True)
        for operation,args in [('ledger.settings.set',dict(key='gemini.include_file',value=False)),
            ('ledger.settings.restore',dict(key='gemini.include_file',expected_revision=self.row('gemini.include_file')['revision'])),
            ('ledger.settings.undo',dict(id=changed['id']))]:
            self.assertFalse(self.kernel.dispatch(operation,args,self.slate)['ok'])
            with self.assertRaises(ValueError):stacy_control.validate_actions([stacy_control.call(operation,args)],self.owner,provider=True,private_local=True)
        self.call('ledger.settings.undo',{'id':changed['id']});self.assertFalse(self.row('gemini.include_file')['stored'])

    def test_cross_project_provider_change_away_and_back_still_conflicts(self):
        self.set('gemini.model','first-model');opened=self.row('gemini.model')
        other=self.base/'other';other.mkdir();kernel=Kernel(other)
        for value in ('second-model','first-model'):
            result=kernel.dispatch('ledger.settings.set',dict(key='gemini.model',value=value),self.owner);self.assertTrue(result['ok'],result)
        response=self.kernel.dispatch('ledger.settings.set',dict(key='gemini.model',value='stale-draft',expected_revision=opened['revision']),self.owner)
        self.assertFalse(response['ok']);self.assertEqual(self.row('gemini.model')['stored'],'first-model')

    def test_older_credential_editor_merges_untouched_preferences_and_refuses_conflicting_model(self):
        original=clip.Settings(key='fixture-key',model='original');original.save()
        cached=clip.Settings.load();self.set('gemini.model','new-model');self.set('gemini.include_file',True)
        cached.key='rotated-fixture-key';cached.save()
        current=clip.Settings.load();self.assertEqual((current.key,current.model,current.include_file),('rotated-fixture-key','new-model',True))
        cached=clip.Settings.load();self.set('gemini.model','owner-model');cached.model='stale-editor-model'
        with self.assertRaises(OSError):cached.save()
        self.assertEqual(clip.preferences()['model'],'owner-model')

    def test_provider_delivery_recovers_only_with_matching_written_revision(self):
        import sqlite3
        with patch.object(ledger_control,'_trim_history',side_effect=sqlite3.OperationalError('Fixture rollback')):
            response=self.kernel.dispatch('ledger.settings.set',dict(key='gemini.model',value='delivered-model'),self.owner)
        self.assertFalse(response['ok']);self.assertEqual(clip.preferences()['model'],'delivered-model')
        self.assertEqual(self.call('ledger.settings.history')['changes'],[])
        self.assertEqual(ledger_control.reconcile_receipts(self.kernel)[0]['state'],'RECONCILED_APPLIED')
        self.assertEqual(self.call('ledger.settings.history')['changes'][0]['after'],'delivered-model')

    def test_noop_provider_delivery_failure_is_not_falsely_recovered_as_applied(self):
        with patch.object(clip,'update_preferences',side_effect=OSError('Fixture before write')):
            response=self.kernel.dispatch('ledger.settings.set',dict(key='gemini.include_file',value=False),self.owner)
        self.assertFalse(response['ok']);self.assertEqual(ledger_control.reconcile_receipts(self.kernel)[0]['state'],'NOT_APPLIED')
        self.assertEqual(self.call('ledger.settings.history')['changes'],[])

    def test_unavailable_optional_provider_store_does_not_block_other_settings_or_overwrite_bytes(self):
        path=clip.settings_path();path.write_text('invalid configuration fixture')
        row=self.row('gemini.model');self.assertEqual(row['application_state'],'STORE_UNAVAILABLE');self.assertFalse(row['editable'])
        self.set('reading.code_pt',18);self.assertEqual(self.row('reading.code_pt')['stored'],18)
        response=self.kernel.dispatch('ledger.settings.set',dict(key='gemini.model',value='new-model'),self.owner)
        self.assertFalse(response['ok']);self.assertEqual(path.read_text(),'invalid configuration fixture')
        for invalid in ({'model':24,'include_file':False},{'model':'valid-model','include_file':'false'}):
            document={'schema':clip.SCHEMA,**invalid};path.write_text(json.dumps(document))
            self.assertEqual(self.row('gemini.model')['application_state'],'STORE_UNAVAILABLE')
            self.assertEqual(json.loads(path.read_text()),document)

    def test_desktop_fields_written_on_every_save_are_restored_with_bounds(self):
        # INTEGRATION-01: library_open, type_target, console.mode/history and pill_link were dumped but never read back.
        data=json.loads(self.session.path.read_text())
        data.update(library_open={'Files':False,'Tools':True,'':True,'Bad':'no',**{'s%d'%i:True for i in range(60)}},type_target='kernel',
                    console={'mode':'shell','history':{'shell':['ls %d'%i for i in range(200)],'kernel':['x',3],'bogus':['y']},'junk':1},pill_link='10.77.0.1:7717')
        self.session.path.write_text(json.dumps(data));s=Session(self.session.path,self.root)
        self.assertEqual((s.state['type_target'],s.state['pill_link'],s.state['console']['mode']),('kernel','10.77.0.1:7717','shell'))
        self.assertIs(s.state['library_open'].get('Files'),False);self.assertNotIn('',s.state['library_open']);self.assertNotIn('Bad',s.state['library_open'])
        self.assertLessEqual(len(s.state['library_open']),50)
        self.assertEqual(len(s.state['console']['history']['shell']),50);self.assertEqual(s.state['console']['history']['shell'][-1],'ls 199')
        self.assertEqual(s.state['console']['history']['kernel'],['x']);self.assertNotIn('bogus',s.state['console']['history']);self.assertNotIn('junk',s.state['console'])
        data.update(type_target='rm -rf /',pill_link='http://host/x',console={'mode':'root','history':[]},library_open=['Files'])
        self.session.path.write_text(json.dumps(data));s=Session(self.session.path,self.root)
        for field in ('type_target','pill_link','console','library_open'):self.assertNotIn(field,s.state)
        self.assertEqual(Session(self.session.path,self.root).state.get('category_views',{}),{})
        # The live console keeps its 200 lines in memory; the profile on disk keeps 50 per page.
        s.state['console']={'mode':'shell','history':{'shell':['cmd %d'%i for i in range(200)]}};s.save()
        self.assertEqual(len(json.loads(self.session.path.read_text())['console']['history']['shell']),50)
        self.assertEqual(len(s.state['console']['history']['shell']),200)
        self.assertEqual(json.loads(self.session.path.read_text())['console']['history']['shell'][0],'cmd 150')


if __name__=='__main__':unittest.main()
