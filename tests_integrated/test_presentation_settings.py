"""Favorites/Existing views persistence, concurrency, receipts and authority."""
import json,os,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from sdk.cli.arc1cli.command_bar import DEFAULTS,session_favorites
from sdk.cli.arc1cli.concern_catalog import Catalog,view_preference
from workbench import ledger_control as control,catalog_settings,settings_registry
from workbench.engineering_kernel import Kernel,operator,Principal
from workbench.session import Session


class PresentationSettingsTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name)
        env=patch.dict(os.environ,dict(ARC1_WORKBENCH_CONFIG_HOME=str(self.base/'profile'),ARC_LEDGER_CONCERN=str(self.base/'Concern')))
        env.start();self.addCleanup(env.stop)
        self.root=self.base/'workspace';self.root.mkdir();self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.s=Session(self.base/'profile/session.json',self.root);self.s.save();control.bind(self.kernel,self.s)
        self.catalog=Catalog(catalog_settings.path(self.kernel))
        launcher=patch.object(Kernel,'launch',side_effect=AssertionError('Settings cannot launch jobs'));self.launch=launcher.start();self.addCleanup(launcher.stop)

    def call(self,op,args=None,who=None):
        result=self.kernel.dispatch(op,args or {},who or self.owner);self.assertTrue(result['ok'],result);return result['result']
    def row(self,key):return next(r for r in self.call('ledger.settings')['settings'] if r['key']==key)
    def set(self,key,value):return self.call('ledger.settings.set',dict(key=key,value=value,expected_revision=self.row(key)['revision']))
    def refuse(self,key,value,**extra):
        result=self.kernel.dispatch('ledger.settings.set',dict(key=key,value=value,**extra),self.owner)
        self.assertFalse(result['ok']);return result

    def test_favorite_set_reopen_order_empty_and_undo_use_original_fields(self):
        first=self.set('favorites.file',['save_all','open'])
        fresh=Session(self.s.path,self.root);self.assertEqual(fresh.state['toolbar_favorites']['File'],['save_all','open'])
        self.assertEqual(fresh.state['toolbar_favorites_version'],2)
        empty=self.set('favorites.file',[]);self.assertEqual(self.row('favorites.file')['stored'],[])
        self.call('ledger.settings.undo',dict(id=empty['id']));self.assertEqual(self.row('favorites.file')['stored'],['save_all','open'])
        self.assertFalse(self.kernel.dispatch('ledger.settings.undo',dict(id=first['id']),self.owner)['ok'])
        self.assertEqual(self.kernel.listing('jobs'),[]);self.launch.assert_not_called()

    def test_reject_bad_groups_duplicates_wrong_type_and_four_slots_without_writes(self):
        before=self.s.path.read_bytes()
        for value in (['save','save'],['no_such_action'],['run'],['new','open','save','save_all'],'save',[None],[[1]]):
            self.refuse('favorites.file',value)
        self.assertEqual(self.s.path.read_bytes(),before);self.assertEqual(self.call('ledger.settings.history')['changes'],[])

    def test_old_default_migration_and_explicit_old_choices_remain_distinct(self):
        old=json.loads(self.s.path.read_text());old.pop('toolbar_favorites_version',None)
        old['toolbar_favorites']={'File':['desk','open','save'],'Help':['orange_book','keys','readiness']}
        self.s.path.write_text(json.dumps(old));before=self.s.path.read_bytes()
        self.assertEqual(self.row('favorites.file')['stored'],list(DEFAULTS['File']))
        self.assertEqual(self.s.path.read_bytes(),before) # reading never migrates bytes
        self.set('favorites.file',['desk','open','save'])
        self.assertEqual(self.row('favorites.file')['stored'],['desk','open','save'])
        self.assertEqual(self.row('favorites.help')['stored'],list(DEFAULTS['Help']))
        self.set('favorites.help',['orange_book','keys','readiness'])
        self.assertEqual(session_favorites(Session(self.s.path,self.root).state)['Help'],['orange_book','keys','readiness'])

    def test_stale_favorite_editor_refused_and_other_groups_merge(self):
        opened=self.row('favorites.edit');other=Session(self.s.path,self.root)
        other.state['toolbar_favorites']={'File':['new'],'Edit':['redo']};other.save()
        self.refuse('favorites.edit',['undo'],expected_revision=opened['revision'])
        self.set('favorites.view',[])
        fresh=Session(self.s.path,self.root);self.assertEqual(fresh.state['toolbar_favorites']['File'],['new'])
        self.assertEqual(fresh.state['toolbar_favorites']['Edit'],['redo'])

    def test_read_only_and_slate_share_existing_authority_and_no_execution(self):
        args=dict(key='favorites.options',value=['run','tests'])
        self.assertFalse(self.kernel.dispatch('ledger.settings.set',args,Principal('reader'))['ok'])
        self.call('ledger.settings.set',args,Principal('Slate:typed',frozenset({'read','execute'})))
        self.assertEqual(self.row('favorites.options')['stored'],['run','tests'])
        self.assertEqual(self.kernel.listing('jobs'),[]);self.launch.assert_not_called()

    def test_public_batch_contract_is_unchanged_and_rejects_new_favorites(self):
        enum=control.FIELDS['ledger.settings.apply'][0]['changes']['items']['properties']['key']['enum']
        self.assertEqual(len(enum),17);self.assertFalse(any(k.startswith('favorites.') for k in enum))
        result=self.kernel.dispatch('ledger.settings.apply',dict(changes=[dict(key='favorites.file',value=[],expected_revision=self.row('favorites.file')['revision'])]),self.owner)
        self.assertFalse(result['ok']);self.assertEqual(self.row('favorites.file')['stored'],list(DEFAULTS['File']))

    def test_favorite_profile_written_but_journal_rollback_reconciles_without_replay(self):
        with patch.object(control,'_trim_history',side_effect=sqlite3.OperationalError('Fixture journal failure')):
            self.refuse('favorites.file',['new'])
        self.assertEqual(self.row('favorites.file')['stored'],['new']);self.assertEqual(self.call('ledger.settings.history')['changes'],[])
        before=self.s.path.read_bytes();self.assertEqual(control.reconcile_receipts(self.kernel)[0]['state'],'RECONCILED_APPLIED')
        self.assertEqual(self.s.path.read_bytes(),before);self.assertEqual(len(self.call('ledger.settings.history')['changes']),1)

    def test_effective_favorites_require_consumer_receipt_and_pending_is_honest(self):
        self.set('favorites.file',['new']);self.assertIsNone(self.row('favorites.file')['effective'])
        leases=self.root/'.ledger/desktops';leases.mkdir(exist_ok=True);lease=leases/'test.json';lease.write_text('{}')
        control.publish_settings_runtime(self.kernel,'test',{'favorites.file':dict(requested=['open'],effective=['open'])})
        self.assertEqual(self.row('favorites.file')['application_state'],'PENDING_DESKTOP')
        control.publish_settings_runtime(self.kernel,'test',{'favorites.file':dict(requested=['new'],effective=['new'])})
        self.assertEqual(self.row('favorites.file')['application_state'],'APPLIED');lease.unlink()
        self.assertIsNone(self.row('favorites.file')['effective'])

    def test_catalogue_set_default_undo_reopens_existing_store_and_retains_records(self):
        snapshot=self.catalog.snapshot();first=self.set('catalog.view','offices')
        self.assertEqual(self.catalog.preference('view'),'offices');self.assertEqual(self.catalog.snapshot(),snapshot)
        self.assertEqual(self.row('catalog.view')['scope_id'],'catalog_profile');self.assertIsNone(self.row('catalog.view')['effective'])
        self.call('ledger.settings.undo',dict(id=first['id']));self.assertEqual(self.catalog.preference('view'),'works')
        self.set('catalog.view','archive');opened=self.row('catalog.view')
        self.call('ledger.settings.restore',dict(key='catalog.view',expected_revision=opened['revision']))
        self.assertEqual(self.catalog.preference('view'),'works');self.launch.assert_not_called()

    def test_legacy_catalogue_away_and_back_and_same_value_invalidate_undo(self):
        changed=self.set('catalog.view','offices');opened=self.row('catalog.view')
        for view in ('work','offices'):self.catalog.set_preference('view',view)
        self.refuse('catalog.view','archive',expected_revision=opened['revision'])
        self.assertFalse(self.kernel.dispatch('ledger.settings.undo',dict(id=changed['id']),self.owner)['ok'])
        opened=self.row('catalog.view');self.catalog.set_preference('view','offices')
        self.assertNotEqual(opened['revision'],self.row('catalog.view')['revision'])

    def test_cross_workspace_catalogue_revision_is_shared_but_journals_remain_local(self):
        first=self.set('catalog.view','work');opened=self.row('catalog.view')
        otherroot=self.base/'other';otherroot.mkdir();other=Kernel(otherroot)
        other_session=Session(self.s.path.parent/'other.json',otherroot);other_session.save();control.bind(other,other_session)
        for view in ('archive','work'):
            result=other.dispatch('ledger.settings.set',dict(key='catalog.view',value=view),self.owner);self.assertTrue(result['ok'],result)
        self.refuse('catalog.view','offices',expected_revision=opened['revision'])
        self.assertEqual([r['id'] for r in self.call('ledger.settings.history')['changes']],[first['id']])

    def test_catalogue_cas_rechecks_at_actual_write_against_legacy_writer(self):
        original=catalog_settings.write
        def intervene(kernel,value,expected_revision,revision_token):
            self.catalog.set_preference('view','archive');return original(kernel,value,expected_revision,revision_token)
        with patch.object(catalog_settings,'write',side_effect=intervene):self.refuse('catalog.view','offices')
        self.assertEqual(self.catalog.preference('view'),'archive');self.assertEqual(self.call('ledger.settings.history')['changes'],[])
        self.assertEqual(control.reconcile_receipts(self.kernel)[0]['state'],'CONFLICT')

    def test_catalogue_delivered_but_journal_failed_recovers_exact_revision_once(self):
        with patch.object(control,'_trim_history',side_effect=sqlite3.OperationalError('Fixture journal failure')):
            self.refuse('catalog.view','offices')
        receipt=next((self.kernel.state/'settings_delivery').glob('*.json'))
        if os.name!='nt':self.assertEqual(receipt.stat().st_mode&0o777,0o600)
        before=catalog_settings.read(self.kernel)
        self.assertEqual(control.reconcile_receipts(self.kernel)[0]['state'],'RECONCILED_APPLIED')
        self.assertEqual(catalog_settings.read(self.kernel),before);self.assertEqual(control.reconcile_receipts(self.kernel),[])
        self.assertEqual(self.call('ledger.settings.history')['changes'][0]['after'],'offices')

    def test_catalogue_same_value_write_not_applied_and_later_change_not_replayed(self):
        with patch.object(catalog_settings,'write',side_effect=OSError('Fixture before write')):self.refuse('catalog.view','works')
        self.assertEqual(control.reconcile_receipts(self.kernel)[0]['state'],'NOT_APPLIED')
        with patch.object(control,'_trim_history',side_effect=sqlite3.OperationalError('Fixture journal failure')):self.refuse('catalog.view','offices')
        for view in ('work','offices'):self.catalog.set_preference('view',view)
        before=catalog_settings.read(self.kernel);self.assertEqual(control.reconcile_receipts(self.kernel)[0]['state'],'CONFLICT')
        self.assertEqual(catalog_settings.read(self.kernel),before);self.assertEqual(self.call('ledger.settings.history')['changes'],[])

    def test_missing_or_corrupt_catalogue_does_not_create_store_or_block_other_settings(self):
        target=catalog_settings.path(self.kernel);target.unlink()
        row=self.row('catalog.view');self.assertFalse(row['editable']);self.assertEqual(row['application_state'],'STORE_UNAVAILABLE')
        self.set('favorites.file',[]);self.assertFalse(target.exists())
        target.write_bytes(b'corrupt catalogue fixture');before=target.read_bytes()
        self.refuse('catalog.view','offices');self.set('reading.code_pt',18)
        self.assertEqual(target.read_bytes(),before);self.assertEqual(self.row('reading.code_pt')['stored'],18)
        self.assertEqual(len(self.call('ledger.settings')['settings']),len(settings_registry.SPECS))

    def test_receipt_for_disconnected_catalogue_retained_without_replay(self):
        with patch.object(control,'_trim_history',side_effect=sqlite3.OperationalError('Fixture journal failure')):self.refuse('catalog.view','work')
        self.s=Session(self.base/'different/session.json',self.root);self.s.save();control.bind(self.kernel,self.s)
        self.assertEqual(control.reconcile_receipts(self.kernel)[0]['state'],'PROFILE_NOT_CONNECTED')
        self.assertEqual(self.catalog.preference('view'),'work')


if __name__=='__main__':unittest.main()
