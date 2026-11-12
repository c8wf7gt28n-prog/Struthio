"""hardware.category_views: one bounded adapter over the existing per-pane Session map (Auto view, Details or Thumbnails per
device/group pane). Single-key Set only; set, undo and default go through the Session field; concurrent writers never resurrect
a stale map; receipts say what is open; the map is presentation-only context; the legacy loader never rewrites bytes."""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import ledger_control as control,settings_registry,stacy_control
from workbench.engineering_kernel import Kernel,operator,Principal
from workbench.session import Session

KEY=settings_registry.VIEW_MODES_KEY


class HardwareSettingsTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name)
        env=patch.dict(os.environ,dict(ARC1_WORKBENCH_CONFIG_HOME=str(self.base/'profile'),ARC_LEDGER_CONCERN=str(self.base/'Concern')))
        env.start();self.addCleanup(env.stop)
        self.root=self.base/'workspace';self.root.mkdir();self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.s=Session(self.base/'profile/session.json',self.root);self.s.save();control.bind(self.kernel,self.s)
        self.slate=Principal('Slate:typed',frozenset({'read','execute'}))
        launcher=patch.object(Kernel,'launch',side_effect=AssertionError('Settings cannot launch jobs'));self.launch=launcher.start();self.addCleanup(launcher.stop)

    def call(self,op,args=None,who=None):
        result=self.kernel.dispatch(op,args or {},who or self.owner);self.assertTrue(result['ok'],result);return result['result']
    def row(self,key=KEY):return next(r for r in self.call('ledger.settings')['settings'] if r['key']==key)
    def set(self,value,who=None):return self.call('ledger.settings.set',dict(key=KEY,value=value,expected_revision=self.row()['revision']),who)
    def refuse(self,op,args,who=None):
        result=self.kernel.dispatch(op,args,who or self.owner);self.assertFalse(result['ok'],result);return result['error']['message']
    def on_disk(self):return Session(self.s.path,self.root).state.get('category_views',{})
    def lease(self,name='test-desktop'):
        leases=self.root/'.ledger/desktops';leases.mkdir(exist_ok=True);path=leases/(name+'.json');path.write_text(json.dumps({'pid':os.getpid()}));return path

    # -- the definition and its plumbing -----------------------------------------------
    def test_contract_single_key_set_only_outside_the_batch_and_session_plumbing(self):
        enum=control.FIELDS['ledger.settings.apply'][0]['changes']['items']['properties']['key']['enum']
        self.assertNotIn(KEY,enum);self.assertEqual(sorted(enum),sorted(settings_registry.SESSION_BATCH_KEYS))
        self.assertIn(KEY,settings_registry.SESSION_KEYS);self.assertNotIn(KEY,settings_registry.SESSION_BATCH_KEYS)
        spec=settings_registry.BY_KEY[KEY]
        self.assertEqual((spec['type'],spec['default'],spec['store'],spec['scope_id'],spec['application'],spec['editor'],spec['maxProperties']),
                         ('object',{},'Session category_views','session_profile','immediate','view_modes',100))
        self.assertEqual(spec['supported_scopes'],['session_profile']);self.assertEqual(spec['root'],'Ledger');self.assertEqual(spec['group'],'Hardware')
        self.assertNotIn(KEY,settings_registry.OWNER_KEYS);self.assertFalse(spec.get('requires_owner'))
        ids={n['id']:n for n in settings_registry.nodes()}
        self.assertEqual(ids['setting:'+KEY]['parent'],'settings:ledger:hardware');self.assertEqual(ids['settings:ledger:hardware']['parent'],'settings:ledger')
        before=self.s.path.read_bytes()
        message=self.refuse('ledger.settings.apply',dict(changes=[dict(key=KEY,value={},expected_revision=self.row()['revision'])]))
        self.assertEqual(self.s.path.read_bytes(),before);self.assertEqual(self.call('ledger.settings.history')['changes'],[])
        self.assertIn(str(len(settings_registry.SPECS))+' ',self.call('ledger.settings')['coverage'])  # the readback counts the live definitions

    # -- the real store ----------------------------------------------------------------
    def test_set_undo_and_default_round_trip_through_the_existing_session_field(self):
        row=self.row();self.assertEqual((row['stored'],row['value'],row['effective'],row['application_state']),({},{},None,'NO_LIVE_DESKTOP_READBACK'))
        first=self.set({'f133/Firmware':'Details'})
        self.assertEqual(self.on_disk(),{'f133/Firmware':'Details'});self.assertEqual(self.row()['stored'],{'f133/Firmware':'Details'})
        second=self.set({'f133/Firmware':'Details','d213/Schematics':'Thumbnails'})
        self.assertEqual(self.on_disk(),{'f133/Firmware':'Details','d213/Schematics':'Thumbnails'})
        history=self.call('ledger.settings.history',{'key':KEY})['changes']
        self.assertEqual([r['id'] for r in history],[second['id'],first['id']]);self.assertTrue(history[0]['can_undo']);self.assertFalse(history[1]['can_undo'])
        self.assertEqual((history[0]['before'],history[0]['after']),({'f133/Firmware':'Details'},{'f133/Firmware':'Details','d213/Schematics':'Thumbnails'}))
        undone=self.call('ledger.settings.undo',dict(id=second['id']));self.assertEqual(undone['restores'],second['id'])
        self.assertEqual(self.on_disk(),{'f133/Firmware':'Details'})
        self.assertFalse(self.kernel.dispatch('ledger.settings.undo',dict(id=first['id']),self.owner)['ok'])
        opened=self.row();self.call('ledger.settings.restore',dict(key=KEY,expected_revision=opened['revision']))
        self.assertEqual(self.on_disk(),{});self.assertEqual(self.row()['stored'],{})
        self.assertFalse(self.kernel.dispatch('ledger.settings.restore',dict(key=KEY,expected_revision=opened['revision']),self.owner)['ok'])
        self.assertEqual(self.kernel.listing('jobs'),[]);self.launch.assert_not_called()

    def test_invalid_maps_are_refused_without_touching_profile_or_journal(self):
        before=self.s.path.read_bytes();good='Details'
        too_many={'device%d/Group'%i:good for i in range(101)}
        cases=[(too_many,'at most 100'),({'f133/Firmware':'Gallery'},'Auto view'),({1:good},'device/group'),({'':good},'device/group'),
               ({'f133/Firm\nware':good},'device/group'),({'x'*300:good},'device/group'),(['f133/Firmware'],'Invalid type'),('Details','Invalid type'),(None,'Invalid type')]
        for value,words in cases:
            message=self.refuse('ledger.settings.set',dict(key=KEY,value=value))
            self.assertIn(words,message,(value,message))
        self.assertEqual(self.s.path.read_bytes(),before);self.assertEqual(self.call('ledger.settings.history')['changes'],[])
        exactly={'device%d/Group'%i:good for i in range(100)};self.set(exactly);self.assertEqual(len(self.on_disk()),100)
        self.set({'x'*299:'Thumbnails','pcb/ERC / DRC evidence':'Details'});self.assertEqual(len(self.on_disk()),2)

    def test_bound_desktop_write_keeps_another_writers_map_and_never_resurrects_a_stale_copy(self):
        # probe 4 shape: another Session saves the map, then the bound desktop writes a different setting.
        other=Session(self.s.path,self.root);other.state['category_views']={'f133/Firmware':'Details'};other.save()
        self.assertNotIn('category_views',self.s.state)
        self.call('ledger.settings.set',dict(key='reading.code_pt',value=18,expected_revision=self.row('reading.code_pt')['revision']))
        self.assertEqual(self.on_disk(),{'f133/Firmware':'Details'});self.assertEqual(self.row()['stored'],{'f133/Firmware':'Details'})
        self.assertEqual(Session(self.s.path,self.root).state['reading_profile']['code_pt'],18)
        # a stale in-memory copy in the bound desktop does not overwrite what the profile holds
        self.s.state['category_views']={'stale/Pane':'Thumbnails'}
        other=Session(self.s.path,self.root);other.state['category_views']={};other.save()
        self.call('ledger.settings.set',dict(key='reading.code_pt',value=19,expected_revision=self.row('reading.code_pt')['revision']))
        self.assertEqual(self.on_disk(),{});self.assertEqual(self.s.state['category_views'],{})
        # a stale expected revision from before the external write is refused and the draft value is not applied
        opened=self.row();other.state['category_views']={'d213/Schematics':'Details'};other.save()
        message=self.refuse('ledger.settings.set',dict(key=KEY,value={'nor/Boot circuitry':'Details'},expected_revision=opened['revision']))
        self.assertIn('SETTING_REVISION_CHANGED',message);self.assertEqual(self.on_disk(),{'d213/Schematics':'Details'})

    def test_pane_patch_helper_merges_one_entry_and_writes_nothing_for_unchanged_choices(self):
        patch_=control.category_view_patch
        self.assertIsNone(patch_({},'f133/Firmware','Auto view'));self.assertIsNone(patch_(None,'f133/Firmware','Auto view'))
        self.assertIsNone(patch_({'f133/Firmware':'Details'},'f133/Firmware','Details'))
        saved={'f133/Firmware':'Details'}
        self.assertEqual(patch_(saved,'f133/Firmware','Auto view'),{});self.assertEqual(saved,{'f133/Firmware':'Details'})
        self.assertEqual(patch_(saved,'d213/Schematics','Thumbnails'),{'f133/Firmware':'Details','d213/Schematics':'Thumbnails'})
        self.assertEqual(patch_(saved,'f133/Firmware','Thumbnails'),{'f133/Firmware':'Thumbnails'})
        # the pane route: a patch is a Set with the row revision, so a concurrent change is detected and the retry merges
        opened=self.row();self.set({'d213/Schematics':'Thumbnails'})
        self.assertIn('SETTING_REVISION_CHANGED',self.refuse('ledger.settings.set',dict(key=KEY,value=patch_(opened['stored'],'f133/Firmware','Details'),expected_revision=opened['revision'])))
        fresh=self.row();self.call('ledger.settings.set',dict(key=KEY,value=patch_(fresh['stored'],'f133/Firmware','Details'),expected_revision=fresh['revision']))
        self.assertEqual(self.on_disk(),{'d213/Schematics':'Thumbnails','f133/Firmware':'Details'})

    # -- consumer receipts ---------------------------------------------------------------
    def test_receipt_states_no_open_pane_applied_and_pending_without_fallback_claims(self):
        lease=self.lease();publish=lambda values:control.publish_settings_runtime(self.kernel,'test-desktop',{KEY:values})
        publish(dict(requested={},effective={},state='NO_OPEN_PANE'))
        row=self.row();self.assertEqual((row['application_state'],row['effective']),('NO_OPEN_PANE',None));self.assertEqual(len(row['desktop_effects']),1)
        self.set({'f133/Firmware':'Details'})
        publish(dict(requested={},effective={},state='NO_OPEN_PANE'));self.assertEqual(self.row()['application_state'],'NO_OPEN_PANE')
        publish(dict(requested={'f133/Firmware':'Details'},effective={'f133/Firmware':'Details','d213/Schematics':'Auto view'},state='OBSERVED'))
        row=self.row();self.assertEqual(row['application_state'],'APPLIED');self.assertEqual(row['effective'],{'f133/Firmware':'Details','d213/Schematics':'Auto view'})
        publish(dict(requested={'f133/Firmware':'Details'},effective={'f133/Firmware':'Thumbnails'},state='OBSERVED'))
        self.assertEqual(self.row()['application_state'],'PENDING_DESKTOP')
        publish(dict(requested={},effective={'f133/Firmware':'Details'},state='OBSERVED'))
        self.assertEqual(self.row()['application_state'],'PENDING_DESKTOP')
        publish(dict(requested={'f133/Firmware':'Details'},effective={'d213/Schematics':'Auto view'},state='OBSERVED'))
        self.assertEqual(self.row()['application_state'],'APPLIED')  # a pane not in the map is Auto view by definition, not a fallback
        lease.unlink();self.assertEqual(self.row()['application_state'],'NO_LIVE_DESKTOP_READBACK')

    # -- sharing and authority ------------------------------------------------------------
    def test_presentation_only_map_is_shareable_context_and_a_cloud_proposal_may_set_it(self):
        self.set({'f133/Firmware':'Details'})
        context=self.call('ledger.context');self.assertEqual(context['settings'][KEY],{'f133/Firmware':'Details'})
        self.assertEqual(next(r for r in context['settings_registry'] if r['key']==KEY)['scope_id'],'session_profile')
        actions=[stacy_control.call('ledger.settings.set',dict(key=KEY,value={'d213/Schematics':'Thumbnails'}))]
        stacy_control.validate_actions(actions,self.slate,provider=True)
        self.assertFalse(stacy_control.cloud_private('ledger.settings.set',actions[0]['arguments']))
        self.assertFalse(self.kernel.dispatch('ledger.settings.set',actions[0]['arguments'],Principal('reader'))['ok'])
        self.call('ledger.settings.set',actions[0]['arguments'],self.slate);self.assertEqual(self.on_disk(),{'d213/Schematics':'Thumbnails'})
        self.assertEqual([r['actor'] for r in self.call('ledger.settings.history',{'key':KEY})['changes']],['Slate:typed','owner'])

    def test_legacy_profile_maps_read_back_through_the_bounded_loader_without_rewriting_bytes(self):
        data=json.loads(self.s.path.read_text());data['category_views']={'pane%03d/Group'%i:'Details' for i in range(120)}
        data['category_views']['bad/Mode']='Gallery';self.s.path.write_text(json.dumps(data));before=self.s.path.read_bytes()
        stored=self.row()['stored'];self.assertEqual(len(stored),100);self.assertNotIn('bad/Mode',stored)
        self.assertEqual(self.s.path.read_bytes(),before)  # reading never migrates
        self.set({});self.assertEqual(self.on_disk(),{})


if __name__=='__main__':unittest.main()
