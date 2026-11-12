"""Cabinet identity, owner boundaries, passive reads and bounded provider failure."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from workbench import cabinet, ledger_control, discovery_ir, project_desk, stacy_control
from workbench.engineering_kernel import Kernel, operator, Principal
from workbench.session import Session
from sdk.cli.arc1cli.concern_catalog import Catalog


class CabinetTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ledger-cabinet-');self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.root=self.base/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(self.base/'profile'),'ARC_LEDGER_CONCERN':str(self.base/'Concern')})
        env.start();self.addCleanup(env.stop);self.owner=operator('owner');self.other=operator('other')
        self.kernel=Kernel(self.root);self.session=Session(self.base/'profile/session.json',self.root)
        self.session.save();ledger_control.bind(self.kernel,self.session)

    def call(self,op,args=None,principal=None):
        result=self.kernel.dispatch(op,args or {},principal or self.owner)
        self.assertTrue(result['ok'],result);return result['result']

    def project(self,title='Project 2',principal=None):
        return self.call('projects.create',{'title':title,'intent':'Keep the original intent.'},principal)

    def model(self,**args):return self.call('ledger.cabinet',args)
    def detail(self,ident,principal=None):return self.call('ledger.cabinet.get',{'id':ident},principal)
    def nodes(self):return {r['id']:r for r in self.model()['nodes']}
    def catalog(self):return Catalog(cabinet.catalog_file(self.kernel))

    def test_owner_records_are_hidden_and_guessed_detail_is_denied(self):
        project=self.project();idea=self.call('ideas.capture',{'text':'Private original','project':project['id']})
        self.project('Other owner',self.other)
        visible=self.call('ledger.cabinet',principal=self.other)['nodes']
        self.assertNotIn('project:'+project['id'],[r['id'] for r in visible])
        self.assertNotIn('Private original',json.dumps(visible))
        for ident in ('project:'+project['id'],'idea:'+idea['id']):
            self.assertFalse(self.kernel.dispatch('ledger.cabinet.get',{'id':ident},self.other)['ok'])
        self.assertEqual(self.detail('idea:'+idea['id'])['record']['id'],idea['id'])

    def test_natural_and_alphabetical_order_share_stable_identities(self):
        self.project('Project 10');self.project('Project 2');first=self.model()
        self.assertEqual([r['label'] for r in first['nodes'] if r['role']=='project'],['Project 2','Project 10'])
        self.call('ledger.settings.set',{'key':'cabinet.sort','value':'alphabetical'})
        second=self.model();self.assertEqual([r['label'] for r in second['nodes'] if r['role']=='project'],['Project 10','Project 2'])
        self.assertEqual({r['id'] for r in first['nodes']},{r['id'] for r in second['nodes']})
        self.assertNotEqual(first['signature'],second['signature'])
        self.assertEqual(second['signature'],self.model()['signature'])

    def test_project_reference_does_not_reparent_or_duplicate_the_idea(self):
        first=self.project();second=self.project('Project 10')
        idea=self.call('ideas.capture',{'text':'One original idea','project':first['id']})
        linked=self.call('projects.link',{'id':second['id'],'expected_revision':1,'role':'QUESTION','address':'idea:'+idea['id']})
        rows=self.nodes();home=rows['idea:'+idea['id']]
        refs=[r for r in rows.values() if r['role']=='reference' and r['canonical_id']==home['id']]
        self.assertEqual(len(refs),1);self.assertEqual(refs[0]['label'],idea['text'])
        self.assertEqual(refs[0]['canonical_home'],'project:'+first['id'])
        self.assertEqual(sum(r['owning'] and r['canonical_id']==home['id'] for r in rows.values()),1)
        detail=self.detail(refs[0]['id']);self.assertEqual(detail['record']['id'],linked['links'][0]['id'])
        target=self.call(detail['actions'][0]['operation'],detail['actions'][0]['arguments'])
        self.assertIn(idea['id'],json.dumps(target))
        self.assertEqual(self.call('ideas.get',{'id':idea['id']})['project'],first['id'])
        self.assertEqual(self.call('ideas.get',{'id':idea['id']})['revision'],1)

    def test_unassigned_is_explicit_and_bounded_project_absence_is_not_unassigned(self):
        project=self.project();idea=self.call('ideas.capture',{'text':'Assigned','project':project['id']})
        orphan=self.call('ideas.capture',{'text':'No project yet'})
        rows=self.nodes();self.assertEqual(rows['idea:'+orphan['id']]['canonical_home'],'cabinet:unassigned')
        for i in range(12):self.call('ideas.capture',{'text':'Recent '+str(i),'project':project['id']})
        model=self.model(limit=10);self.assertTrue(model['partial'])
        self.assertIn('cabinet:other-projects',{r['id'] for r in model['nodes']})
        self.assertTrue(all(r.get('canonical_home')!='cabinet:unassigned' for r in model['nodes'] if r['role']=='idea'))
        self.assertEqual(self.detail('idea:'+idea['id'])['record']['project'],project['id'])

    def test_catalog_multiple_placements_read_the_same_saved_note_without_writes(self):
        catalog=self.catalog();ident=catalog.create('note','A filed note','projects')
        catalog.link(ident,'part_of','inbox');catalog.save_note(ident,'Exact saved words',0)
        with catalog.db() as db:before=db.execute('SELECT max(seq) FROM events').fetchone()[0]
        model=self.model();rows=[r for r in model['nodes'] if r['canonical_id']=='catalog:'+ident]
        self.assertEqual(len(rows),2);self.assertEqual(sum(r['role']=='reference' for r in rows),1)
        for row in rows:self.assertEqual(self.detail(row['id'])['record']['note']['body'],'Exact saved words')
        with catalog.db() as db:self.assertEqual(db.execute('SELECT max(seq) FROM events').fetchone()[0],before)

    def test_catalog_titles_can_change_without_changing_selection_identity(self):
        catalog=self.catalog();ident=catalog.create('note','Before','projects')
        before=self.nodes()['catalog:'+ident];catalog.rename(ident,'After',1)
        after=self.nodes()['catalog:'+ident];self.assertEqual(before['id'],after['id'])
        self.assertEqual(after['label'],'After');self.assertEqual(after['revision'],2)

    def test_missing_or_unsupported_catalog_never_creates_or_migrates_it(self):
        path=cabinet.catalog_file(self.kernel);self.assertFalse(path.exists())
        self.assertEqual(self.model()['providers']['concern_catalog'],'NOT_PRESENT');self.assertFalse(path.exists())
        path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(path) as db:db.execute('PRAGMA user_version=99')
        project=self.project();model=self.model();self.assertEqual(model['providers']['concern_catalog'],'UNAVAILABLE')
        self.assertTrue(model['notices']);self.assertIn('project:'+project['id'],{r['id'] for r in model['nodes']})
        with sqlite3.connect(path) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],99)

    def test_stored_integrity_failure_is_visible_without_discarding_other_work(self):
        project=self.project();idea=self.call('ideas.capture',{'text':'Integrity fixture'})
        with self.kernel.db() as db:db.execute('UPDATE desk_records SET digest=? WHERE id=?',('0'*64,idea['id']))
        model=self.model();self.assertTrue(model['partial']);self.assertTrue(any('integrity' in x for x in model['notices']))
        self.assertIn('project:'+project['id'],{r['id'] for r in model['nodes']})
        self.assertNotIn('idea:'+idea['id'],{r['id'] for r in model['nodes']})

    def test_snapshot_does_not_refresh_inquiry_sources_or_create_jobs(self):
        project=self.project();document=discovery_ir.template()
        inquiry=self.call('discovery.create',{'document':document,'project':project['id']})
        with patch('workbench.discovery_service.view',side_effect=AssertionError('No automatic freshness check')), \
             patch('subprocess.Popen',side_effect=AssertionError('No process launch')):
            model=self.model();detail=self.detail('inquiry:'+inquiry['id'])
        self.assertIn('inquiry:'+inquiry['id'],{r['id'] for r in model['nodes']})
        self.assertEqual(detail['actions'][0]['operation'],'discovery.get')
        self.assertEqual(detail['record']['id'],inquiry['id'])
        self.assertEqual(self.kernel.listing('jobs'),[])

    def test_legacy_working_copy_metadata_reads_without_hashing_or_schema_migration(self):
        ident='a'*32
        with self.kernel.db() as db:
            db.execute('CREATE TABLE copies(id TEXT PRIMARY KEY,owner TEXT,source TEXT,work TEXT,state TEXT,revision INTEGER,updated REAL)')
            db.execute('INSERT INTO copies VALUES(?,?,?,?,?,?,?)',(ident,'owner','/original/master.txt','/work/copy.txt','WORKING',1,1))
            db.execute('INSERT INTO copies VALUES(?,?,?,?,?,?,?)',('b'*32,'other','/private/secret.txt','/other/copy.txt','WORKING',1,1))
        with patch('workbench.working_copies.sha_of',side_effect=AssertionError('No automatic file hash')):
            nodes=self.nodes();detail=self.detail('copies:'+ident)
        self.assertEqual(nodes['copies:'+ident]['canonical_home'],'cabinet:unassigned')
        self.assertEqual(detail['record']['freshness'],'NOT_RECHECKED');self.assertEqual(detail['record']['kind'],'file')
        self.assertNotIn('copies:'+'b'*32,nodes)
        self.assertFalse(self.kernel.dispatch('ledger.cabinet.get',{'id':'copies:'+ident},self.other)['ok'])
        with self.kernel.db() as db:self.assertNotIn('kind',{r[1] for r in db.execute('PRAGMA table_info(copies)')})

    def test_legacy_investigations_keep_owner_and_distinct_identity(self):
        record=self.call('investigation.create',{'question':'Which check is useful?','objective':'Read first.'})
        nodes=self.nodes();ident='investigation:'+record['id'];self.assertIn(ident,nodes)
        self.assertEqual(self.detail(ident)['record']['id'],record['id'])
        self.assertNotIn(ident,{r['id'] for r in self.call('ledger.cabinet',principal=self.other)['nodes']})
        self.assertEqual(self.detail(ident)['actions'][0]['operation'],'investigation.sheet')

    def test_cycle_and_depth_are_bounded_without_mutating_catalog(self):
        catalog=self.catalog();a=catalog.create('collection','Loop A','projects');b=catalog.create('collection','Loop B',a)
        with catalog.db() as db:db.execute('INSERT INTO relations VALUES(?,?,?)',(a,'part_of',b))
        model=self.model();self.assertTrue(any('cycle' in x for x in model['notices']))
        nodes={r['id']:r for r in model['nodes']};self.assertIn('catalog:'+a,nodes);self.assertIn('catalog:'+b,nodes)
        for row in nodes.values():
            chain=set()
            while row['parent']:
                self.assertNotIn(row['id'],chain);chain.add(row['id']);row=nodes[row['parent']]
        with catalog.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM relations WHERE source=? AND target=?',(a,b)).fetchone()[0],1)

    def test_cloud_and_tutor_boundaries_apply_to_new_read_operations(self):
        worker=Principal('owner',frozenset({'read','execute'}))
        proposal=stacy_control.call('ledger.cabinet',{})
        with self.assertRaises(ValueError):stacy_control.validate_actions([proposal],worker,provider=True)
        stacy_control.validate_actions([proposal],worker,provider=True,private_local=True)
        self.assertTrue(self.kernel.dispatch('ledger.cabinet',{},Principal('owner'))['ok'])
        self.assertFalse(self.kernel.dispatch('ledger.cabinet',{'limit':1001},self.owner)['ok'])
        self.assertFalse(self.kernel.dispatch('ledger.cabinet.get',{'id':'../../private'},self.owner)['ok'])

    def test_session_remembers_valid_presentation_state_and_ignores_malformed_values(self):
        valid=dict(selected='project:'+'a'*32,expanded=['cabinet:concern','cabinet:projects'],legacy=False,scroll=20)
        self.session.state['cabinet_navigation']=valid;self.session.save()
        self.assertEqual(Session(self.session.path,self.root).state['cabinet_navigation'],valid)
        for bad in ({**valid,'legacy':1},{**valid,'scroll':True},{**valid,'expanded':['bad\nnode']},{**valid,'selected':[]}, {**valid,'expanded':['x']*2401}):
            self.session.state['cabinet_navigation']=bad;self.session.save()
            self.assertNotIn('cabinet_navigation',Session(self.session.path,self.root).state)


if __name__=='__main__':unittest.main()
