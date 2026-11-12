"""The Finder's listing (HATCH AGENT-01, UI-04): ledger.browse reads a real folder and nothing else.

Ordering (folders first, natural names), the hidden filter, the 500/2000 bound with a truthful count, a symlink that is
shown as a link and never followed, the plain words for an unreadable folder, a file and a missing path, the result
through Kernel.dispatch with the read principal, and the observer treatment (no audit row for a successful read).
Disposable temp folders; Kernel.launch and Kernel.submit are held; no process starts.
"""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import browse as B,activity
from workbench.engineering_kernel import Kernel,operator,Principal,CAPABILITIES


class Listing(unittest.TestCase):
    """The pure part over a disposable folder."""

    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ledger-browse-');self.addCleanup(temporary.cleanup);self.folder=Path(temporary.name)/'place';self.folder.mkdir()
        for name in ('zeta.txt','file10.txt','file2.txt','Alpha.txt','.hidden.txt'):(self.folder/name).write_text(name)
        for name in ('beta','.secret','10 plates','9 plates'):(self.folder/name).mkdir()
        (self.folder/'.secret'/'inside.txt').write_text('x')
        (self.folder/'pointer.txt').symlink_to(self.folder/'zeta.txt')
        (self.folder/'elsewhere').symlink_to(self.folder/'beta')

    def names(self,**kw):return [e['name'] for e in B.listing(str(self.folder),**kw)['entries']]

    def test_folders_first_then_natural_names(self):
        self.assertEqual(self.names(),['9 plates','10 plates','beta','Alpha.txt','elsewhere','file2.txt','file10.txt','pointer.txt','zeta.txt'])
        value=B.listing(str(self.folder))
        self.assertEqual(value['count'],9);self.assertFalse(value['truncated']);self.assertEqual(value['path'],str(self.folder));self.assertEqual(value['parent'],str(self.folder.parent))
        self.assertEqual(value['basis'],B.BASIS);self.assertIn('THIS_HOST',value['basis'])
        self.assertTrue(all(set(e)=={'name','kind','bytes','modified','hidden','symlink','readable'} for e in value['entries']))
        self.assertTrue(all(e['kind'] in B.KINDS for e in value['entries']))
        by={e['name']:e for e in value['entries']}
        self.assertEqual((by['beta']['kind'],by['beta']['bytes']),('folder',None));self.assertEqual((by['zeta.txt']['kind'],by['zeta.txt']['bytes']),('file',len('zeta.txt')))
        self.assertTrue(all(e['readable'] for e in value['entries']));self.assertTrue(all(isinstance(e['modified'],float) for e in value['entries']))
        self.assertIsInstance(value['free_bytes'],int);self.assertIsInstance(value['total_bytes'],int);self.assertGreaterEqual(value['total_bytes'],value['free_bytes'])
        self.assertTrue(value['mount'] is None or str(self.folder).startswith(value['mount']))

    def test_hidden_only_with_all(self):
        self.assertFalse(any(n.startswith('.') for n in self.names()))
        all_names=self.names(show_all=True);self.assertEqual(all_names[:4],['9 plates','10 plates','.secret','beta']);self.assertIn('.hidden.txt',all_names)   # the house natural order: a leading number before letters
        value=B.listing(str(self.folder),show_all=True);self.assertEqual(value['count'],11)
        self.assertEqual([e['hidden'] for e in value['entries'] if e['name'] in ('.secret','.hidden.txt')],[True,True])

    def test_limit_bounds_the_entries_and_the_count_stays_truthful(self):
        value=B.listing(str(self.folder),limit=3)
        self.assertEqual([e['name'] for e in value['entries']],['9 plates','10 plates','beta']);self.assertEqual(value['count'],9);self.assertTrue(value['truncated'])
        self.assertEqual(len(B.listing(str(self.folder),limit=5000)['entries']),9)   # above the maximum the maximum applies
        self.assertEqual(len(B.listing(str(self.folder),limit=0)['entries']),1)      # below one, one
        big=self.folder/'many';big.mkdir()
        for i in range(600):(big/('row%03d.txt'%i)).write_text('')
        value=B.listing(str(big));self.assertEqual((len(value['entries']),value['count'],value['truncated']),(500,600,True))
        value=B.listing(str(big),limit=2000);self.assertEqual((len(value['entries']),value['count'],value['truncated']),(600,600,False))
        with patch.object(B,'SCAN_BOUND',50):
            value=B.listing(str(big));self.assertTrue(value['truncated']);self.assertEqual(value['count'],50)

    def test_a_symlink_is_a_link_and_never_followed(self):
        by={e['name']:e for e in B.listing(str(self.folder))['entries']}
        self.assertEqual(by['pointer.txt']['kind'],'link');self.assertTrue(by['pointer.txt']['symlink'])
        self.assertEqual(by['pointer.txt']['bytes'],len(str(self.folder/'zeta.txt')))   # the link's own size, not the target's
        self.assertEqual(by['elsewhere']['kind'],'link');self.assertFalse(by['beta']['symlink'])
        self.assertEqual(sorted(by),sorted(n for n in os.listdir(self.folder) if not n.startswith('.')))   # the target folder's contents are not merged in
        with self.assertRaises(ValueError) as caught:B.listing(str(self.folder/'pointer.txt'))
        self.assertIn('link, not a folder',str(caught.exception))
        self.assertEqual(B.listing(str(self.folder/'elsewhere'))['count'],0)   # a link to a folder, named by the owner, lists that folder

    def test_plain_words_for_what_cannot_be_listed(self):
        with self.assertRaises(ValueError) as caught:B.listing(str(self.folder/'zeta.txt'))
        self.assertEqual(str(caught.exception),'That is a file, not a folder: '+str(self.folder/'zeta.txt'))
        with self.assertRaises(ValueError) as caught:B.listing(str(self.folder/'nowhere'))
        self.assertEqual(str(caught.exception),'There is no folder at '+str(self.folder/'nowhere'))
        with self.assertRaises(ValueError) as caught:B.listing('relative/place')
        self.assertIn('from the root of this computer',str(caught.exception))
        for bad in ('',None,'  '):
            with self.assertRaises(ValueError):B.listing(bad)
        with patch.object(os,'scandir',side_effect=PermissionError(13,'Permission denied')):
            with self.assertRaises(ValueError) as caught:B.listing(str(self.folder))
        self.assertEqual(str(caught.exception),'That folder cannot be read: '+str(self.folder))
        with patch.object(os,'lstat',side_effect=PermissionError(13,'Permission denied')):
            with self.assertRaises(ValueError) as caught:B.listing(str(self.folder))
        self.assertIn('cannot be read',str(caught.exception))
        self.assertEqual(B.listing('/')['parent'],None)
        with self.assertRaises(ValueError):B.dispatch(None,'ledger.unknown',{},None)


class Route(unittest.TestCase):
    """ledger.browse through the Kernel: a read, an observer, plain words on refusal, nothing started."""

    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ledger-browse-route-');self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(Path(temporary.name)/'profile')});env.start();self.addCleanup(env.stop)
        self.kernel=Kernel(self.root);self.reader=Principal('reader')   # the read scope only
        for name in ('launch','submit'):
            held=patch.object(Kernel,name,side_effect=AssertionError('no '+name));held.start();self.addCleanup(held.stop)
        self.place=Path(temporary.name)/'place';self.place.mkdir();(self.place/'note.txt').write_text('words');(self.place/'sub').mkdir();(self.place/'.dot').write_text('')

    def audit_rows(self):
        with self.kernel.db() as db:return db.execute('SELECT count(*) FROM audit').fetchone()[0]

    def test_read_principal_observer_and_words(self):
        self.assertEqual(CAPABILITIES['ledger.browse'],'read');self.assertIn('ledger.browse',activity.OBSERVER_OPERATIONS);self.assertIn('ledger.browse',B.OBSERVERS)
        from workbench import stacy_control
        self.assertTrue(stacy_control.cloud_private('ledger.browse',{'path':'/'}))
        before=self.audit_rows()
        r=self.kernel.dispatch('ledger.browse',{'path':str(self.place)},self.reader);self.assertTrue(r['ok'],r)
        value=r['result'];self.assertEqual([e['name'] for e in value['entries']],['sub','note.txt']);self.assertEqual(value['count'],2);self.assertFalse(value['truncated'])
        self.assertEqual(self.audit_rows(),before,'a successful read is an observer: no audit row')
        r=self.kernel.dispatch('ledger.browse',{'path':str(self.place),'all':True,'limit':1},operator());self.assertTrue(r['ok'],r)
        self.assertEqual(([e['name'] for e in r['result']['entries']],r['result']['count'],r['result']['truncated']),(['sub'],3,True))
        r=self.kernel.dispatch('ledger.browse',{'path':str(self.place/'note.txt')},self.reader)
        self.assertFalse(r['ok']);self.assertEqual(r['error']['message'],'That is a file, not a folder: '+str(self.place/'note.txt'));self.assertNotIn('Traceback',str(r))
        r=self.kernel.dispatch('ledger.browse',{'path':str(self.place/'gone')},self.reader);self.assertFalse(r['ok']);self.assertIn('There is no folder at',r['error']['message'])
        r=self.kernel.dispatch('ledger.browse',{'path':str(self.place),'limit':9000},self.reader);self.assertFalse(r['ok'])   # the schema bounds the limit
        self.assertEqual(self.kernel.listing('jobs'),[])
        self.assertEqual(os.listdir(self.place).__len__(),3)   # nothing was written there
