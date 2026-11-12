"""Release-parts integrity, atomic extraction, non-executing install plans, truthful final status and the packager round trip."""
import contextlib,hashlib,importlib.util,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile,ZipInfo
import INSTALL_LS as installer
ROOT=Path(__file__).resolve().parents[1]


def load_packager():
    spec=importlib.util.spec_from_file_location('package_release_parts',ROOT/'tools'/'package_release_parts.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class InstallMediaTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name);self.media=self.base/'USB';self.media.mkdir();self.target=self.base/'installed'
    def release(self,mutate=None,chunks=None):
        files={'app.py':b'print("fixture")\n','nested/data.txt':b'fixture data\n'}
        records={name:dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in files.items()}
        payload=json.dumps(dict(files=records)).encode();groups=[{'MANIFEST.json':payload,'app.py':files['app.py']},{'nested/data.txt':files['nested/data.txt']}]
        if mutate:mutate(groups)
        rows=[]
        for index,group in enumerate(groups,1):
            path=self.media/f'fixture_part{index:02}.zip'
            with ZipFile(path,'w') as archive:
                for name,data in group.items():
                    info=ZipInfo(name);info.external_attr=(0o100755 if name.endswith('.py') else 0o100644)<<16;archive.writestr(info,data)
            rows.append(dict(name=path.name,bytes=path.stat().st_size,sha256=installer.digest(path)))
        data=dict(schema='ledger.release-parts/1',payload_manifest_sha256=hashlib.sha256(payload).hexdigest(),parts=rows)
        if chunks is not None:data['file_chunks']=chunks
        (self.media/'RELEASE_PARTS.json').write_text(json.dumps(data));return data
    def split_release(self,mode=0o100644,chunks=None):
        """nested/data.txt travels as two hashed chunks; `chunks` replaces the generated chunk metadata."""
        content=b'fixture data\n';entries=['__LS_RELEASE_CHUNKS__/runtime_01.bin','__LS_RELEASE_CHUNKS__/runtime_02.bin'];blocks=[content[:5],content[5:]]
        def split(groups):
            groups[1].pop('nested/data.txt');groups[1][entries[0]]=blocks[0];groups[1][entries[1]]=blocks[1]
        meta=dict(bytes=len(content),sha256=hashlib.sha256(content).hexdigest(),mode=mode,chunks=[dict(entry=entry,bytes=len(block),sha256=hashlib.sha256(block).hexdigest()) for entry,block in zip(entries,blocks)])
        return self.release(split,{'nested/data.txt':meta} if chunks is None else chunks),content

    def test_all_parts_extract_exact_bytes_and_modes_without_invoking_installer(self):
        self.release()
        with patch.object(installer.subprocess,'run',side_effect=AssertionError('No package installation')):
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(installer.main(['--usb',str(self.media),'--target',str(self.target),'--extract-only']),0)
        self.assertEqual((self.target/'nested/data.txt').read_bytes(),b'fixture data\n');self.assertEqual((self.target/'app.py').stat().st_mode&0o777,0o755)

    def test_split_runtime_restores_exact_original_and_removes_chunk_staging(self):
        data,content=self.split_release()
        installer.extract(self.media,data,self.target)
        self.assertEqual((self.target/'nested/data.txt').read_bytes(),content);self.assertFalse((self.target/'__LS_RELEASE_CHUNKS__').exists())

    def test_missing_or_changed_part_is_refused_before_target_creation(self):
        data=self.release();path=self.media/data['parts'][1]['name'];path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed release part'):installer.extract(self.media,data,self.target)
        self.assertFalse(self.target.exists())
        path.unlink()
        with self.assertRaises(ValueError):installer.extract(self.media,data,self.target)
        self.assertFalse(self.target.exists())

    def test_payload_mismatch_cleans_staging_and_never_installs_partial_release(self):
        data=self.release(lambda groups:groups[1].update({'nested/data.txt':b'changed after manifest'}))
        with self.assertRaisesRegex(ValueError,'Payload mismatch'):installer.extract(self.media,data,self.target)
        self.assertFalse(self.target.exists());self.assertEqual(list(self.base.glob('.ledger-install-*')),[])

    def test_traversal_and_duplicate_entries_cannot_overlay_files(self):
        for change in (lambda groups:groups[1].update({'../outside':b'bad'}),lambda groups:groups[1].update({'app.py':b'bad'})):
            data=self.release(change)
            with self.assertRaisesRegex(ValueError,'Invalid or duplicate archive entry'):installer.extract(self.media,data,self.target)
            self.assertFalse((self.base/'outside').exists());self.assertFalse(self.target.exists())

    def test_existing_installation_is_retained(self):
        data=self.release();self.target.mkdir();file=self.target/'my_work';file.write_bytes(b'keep me')
        with self.assertRaisesRegex(ValueError,'existing folder is retained'):installer.extract(self.media,data,self.target)
        self.assertEqual(file.read_bytes(),b'keep me')

    def test_public_source_requires_https_and_pinned_manifest_and_plan_never_downloads(self):
        for url in ('http://example.org/release.json','https://user:password@example.org/release.json'):
            with self.assertRaises(ValueError):installer.checked_url(url)
        with patch.object(installer,'download',side_effect=AssertionError('Plan cannot download')),contextlib.redirect_stdout(io.StringIO()) as output:
            result=installer.main(['--public-manifest','https://example.org/RELEASE_PARTS.json','--manifest-sha256','a'*64,'--target',str(self.target),'--minimal-session','--plan'])
        self.assertEqual(result,0);plan=json.loads(output.getvalue());self.assertFalse(plan['writes']);self.assertFalse(plan['downloads']);self.assertFalse(self.target.exists())

    def test_missing_offline_cache_fails_before_any_extraction_or_sudo(self):
        self.release()
        with patch.object(installer.os,'geteuid',return_value=1000),patch.object(installer.subprocess,'run',side_effect=AssertionError('No sudo without cache')):
            with self.assertRaisesRegex(ValueError,'no network fallback'):installer.main(['--usb',str(self.media),'--target',str(self.target),'--offline'])
        self.assertFalse(self.target.exists())

    def test_cache_rejects_unlisted_or_changed_dependency_files(self):
        wheels=self.media/'wheels';wheels.mkdir();wheel=wheels/'fixture.whl';wheel.write_bytes(b'fixture wheel bytes')
        data=dict(schema='ledger.offline-files/1',files={'wheels/fixture.whl':dict(bytes=wheel.stat().st_size,sha256=installer.digest(wheel))})
        (self.media/'OFFLINE_FILES.json').write_text(json.dumps(data));self.assertEqual(installer.offline_cache(self.media),(wheels,[]))
        (wheels/'unlisted.whl').write_bytes(b'unknown')
        with self.assertRaisesRegex(ValueError,'unlisted'):installer.offline_cache(self.media)
        (wheels/'unlisted.whl').unlink();wheel.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'checksum mismatch'):installer.offline_cache(self.media)

    # --- INTEGRATION-01 additions -------------------------------------------------------------

    def test_malformed_chunk_metadata_is_a_refusal_before_any_write_not_a_traceback(self):
        good=self.split_release()[0]['file_chunks']['nested/data.txt']
        def without(key):return {k:v for k,v in good.items() if k!=key}
        def chunk_without(key):return dict(good,chunks=[{k:v for k,v in good['chunks'][0].items() if k!=key},good['chunks'][1]])
        variants={'meta is a string':'not a dict','no bytes':without('bytes'),'no mode':without('mode'),'no sha256':without('sha256'),'mode is a string':dict(good,mode='644'),
            'chunks not a list':dict(good,chunks='x'),'chunk without bytes':chunk_without('bytes'),'chunk without entry':chunk_without('entry'),'chunk is a string':dict(good,chunks=['x']),
            'sizes do not add up':dict(good,bytes=good['bytes']+1),'write-only mode':dict(good,mode=0o100200),'repeated entry':dict(good,chunks=[good['chunks'][0],good['chunks'][0]])}
        for label,meta in variants.items():
            with self.subTest(label):
                self.split_release(chunks={'nested/data.txt':meta})
                with self.assertRaisesRegex(ValueError,'(?i)chunk'):installer.main(['--usb',str(self.media),'--target',str(self.target),'--extract-only'])
                self.assertFalse(self.target.exists());self.assertEqual(list(self.base.glob('.ledger-install-*')),[])
        with self.subTest('inventory keyed by a chunk path or a non-string'):
            for groups in ({'__LS_RELEASE_CHUNKS__/x':good},{'../escape':good},{'nested/data.txt':good,'too':good,'many':good}):
                with self.assertRaisesRegex(ValueError,'(?i)chunk'):installer.chunk_inventory(groups)
        self.split_release(chunks={'nested/data.txt':without('mode')}) # the command line maps it to the attention line, with no traceback
        result=subprocess.run([sys.executable,'-I',str(ROOT/'INSTALL_LS.py'),'--usb',str(self.media),'--target',str(self.target),'--extract-only'],capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,1);self.assertTrue(result.stderr.startswith('Installation needs attention: Invalid file chunk metadata: nested/data.txt'),result.stderr);self.assertNotIn('Traceback',result.stderr);self.assertFalse(self.target.exists())
        self.split_release();self.assertEqual(list(installer.manifest(self.media/'RELEASE_PARTS.json')['file_chunks']),['nested/data.txt']) # the well-formed inventory still validates

    def test_unreferenced_chunk_files_are_refused_as_an_incomplete_inventory(self):
        self.split_release(chunks={})
        with self.assertRaisesRegex(ValueError,'Unreferenced chunk files'):installer.main(['--usb',str(self.media),'--target',str(self.target),'--extract-only'])
        self.assertFalse(self.target.exists());self.assertEqual(list(self.base.glob('.ledger-install-*')),[])

    def test_split_file_mode_falls_back_to_owner_readable_0644(self):
        for mode,expected in ((0,0o644),(0o100755,0o755),(0o100640,0o640)):
            with self.subTest(mode=oct(mode)):
                data,content=self.split_release(mode=mode);target=self.base/('restored_%o'%mode)
                installer.extract(self.media,data,target)
                self.assertEqual((target/'nested/data.txt').read_bytes(),content);self.assertEqual((target/'nested/data.txt').stat().st_mode&0o777,expected)
        data,content=self.split_release(mode=0o100200)
        with self.assertRaisesRegex(ValueError,'denies owner read'):installer.extract(self.media,data,self.target)
        self.assertFalse(self.target.exists())

    def test_plan_with_extract_only_lists_one_step_and_no_start_command(self):
        def plan(*flags):
            with contextlib.redirect_stdout(io.StringIO()) as output:self.assertEqual(installer.main(['--usb',str(self.media),'--target',str(self.target),'--minimal-session','--plan',*flags]),0)
            return json.loads(output.getvalue())
        only=plan('--extract-only');full=plan()
        self.assertEqual(len(only['steps']),1);self.assertIn('extract',only['steps'][0]);self.assertIsNone(only['starts_with']);self.assertIsNone(only['prerequisites']);self.assertIn('INSTALL_DEBIAN.sh --quick',only['then']);self.assertTrue(only['extract_only'])
        self.assertEqual(len(full['steps']),3);self.assertEqual(full['starts_with'],'bash START_MINIMAL_DEBIAN.sh');self.assertIn('skipped and reported when no terminal',full['prerequisites']);self.assertFalse(full['extract_only'])
        self.assertIn('--yes',plan('--yes')['prerequisites']);self.assertFalse(self.target.exists());self.assertEqual(sorted(self.base.iterdir()),[self.media])

    def test_failed_installation_removes_the_parent_chain_it_created_and_success_keeps_it(self):
        data=self.release(lambda groups:groups[1].update({'nested/data.txt':b'changed after manifest'}));deep=self.base/'deep'/'er'/'Ledger'
        with self.assertRaisesRegex(ValueError,'Payload mismatch'):installer.extract(self.media,data,deep)
        self.assertFalse((self.base/'deep').exists());self.assertEqual(list(self.base.glob('.ledger-install-*')),[])
        sibling=self.base/'kept';sibling.mkdir();(sibling/'note').write_text('owner file') # an existing folder with content is never removed
        with self.assertRaisesRegex(ValueError,'Payload mismatch'):installer.extract(self.media,data,sibling/'new'/'Ledger')
        self.assertTrue((sibling/'note').exists());self.assertFalse((sibling/'new').exists())
        data=self.release();installer.extract(self.media,data,deep);self.assertTrue((deep/'app.py').is_file())

    def test_unwritable_containing_folder_is_named_before_any_write(self):
        data=self.release()
        with patch.object(installer.os,'access',return_value=False):
            with self.assertRaisesRegex(ValueError,'must be writable: '+str(self.base)):installer.extract(self.media,data,self.target)
        with patch.object(installer.tempfile,'TemporaryDirectory',side_effect=PermissionError(13,'Permission denied')):
            with self.assertRaisesRegex(ValueError,'must be writable: '+str(self.base)):installer.extract(self.media,data,self.target)
        blocker=self.base/'blocker';blocker.write_text('a file')
        with self.assertRaisesRegex(ValueError,'is not a folder'):installer.extract(self.media,data,blocker/'Ledger')
        self.assertFalse(self.target.exists());self.assertEqual(list(self.base.glob('.ledger-install-*')),[])

    def test_final_status_names_what_happened_and_never_says_installed(self):
        def install(flags,returncode,missing,terminal):
            self.release();target=self.base/('target_%d_%d'%(returncode,len(missing)));calls=[]
            def run(options,**kwargs):calls.append(options);return subprocess.CompletedProcess(options,returncode)
            stdin=io.StringIO() if not terminal else type('TTY',(),{'isatty':staticmethod(lambda:True)})()
            with patch.object(installer.os,'geteuid',return_value=1000),patch.object(installer,'debian_host',return_value=True),patch.object(installer,'missing_session_commands',return_value=missing),\
                 patch.object(installer.subprocess,'run',run),patch.object(installer.sys,'stdin',stdin),contextlib.redirect_stdout(io.StringIO()) as output:
                code=installer.main(['--usb',str(self.media),'--target',str(target),*flags])
            return code,output.getvalue(),calls,target
        code,text,calls,target=install(['--minimal-session'],installer.PREREQUISITES_SKIPPED,['startx','Xorg'],terminal=False)
        self.assertEqual(code,0);self.assertEqual(calls[0][:3],['bash',str(target/'INSTALL_DEBIAN.sh'),'--quick']);self.assertNotIn('--yes',calls[0]);self.assertIn('--minimal-session',calls[0])
        self.assertIn('No terminal is attached and --yes was not given',text)
        self.assertIn('Program extracted and verified · Runtime imports verified · Debian prerequisites skipped (no --yes and no terminal for the sudo prompt) · Minimal session prerequisites missing (startx, Xorg) · Owner display and native/model qualification remain separate.',text)
        self.assertIn('Start from an existing desktop with: bash '+str(target/'START_OFFICE.sh'),text);self.assertIn('--minimal-session --quick --yes',text);self.assertNotIn('Installed.',text);self.assertNotIn('Start with: bash',text)
        code,text,calls,target=install(['--minimal-session','--yes'],0,[],terminal=True)
        self.assertIn('--yes',calls[0]);self.assertIn('Debian prerequisites installed · Minimal session prerequisites present',text);self.assertIn('Start with: bash '+str(target/'START_MINIMAL_DEBIAN.sh'),text);self.assertNotIn('No terminal',text)
        code,text,calls,target=install([],installer.PREREQUISITES_SKIPPED,[],terminal=True)
        self.assertIn('Debian prerequisites skipped (declined at the prompt) · Owner display',text);self.assertNotIn('Minimal session',text);self.assertIn('Start with: bash '+str(target/'START_OFFICE.sh'),text)
        with self.assertRaisesRegex(ValueError,'returned status 2; the verified program is retained'):install([],2,[],terminal=True)
        self.assertTrue((self.base/'target_2_0'/'app.py').is_file())

    def test_packager_round_trip_restores_split_files_with_their_modes(self):
        packager=load_packager();files={'README_INTEGRATION_01.txt':(b'start here\n',0o100644),'bin/tool.sh':(b'#!/bin/sh\necho tool\n',0o100755),'runtimes/big.bin':(os.urandom(350_000),0o100755),'docs/small.txt':(b'text\n',0o100644)}
        records={name:dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,(data,mode) in files.items()}
        archive=self.base/'Fixture_Release.zip'
        with ZipFile(archive,'w') as out:
            info=ZipInfo('MANIFEST.json');info.external_attr=0o100644<<16;out.writestr(info,json.dumps(dict(files=records)))
            for name,(data,mode) in files.items():info=ZipInfo(name);info.external_attr=mode<<16;out.writestr(info,data)
        with self.assertRaisesRegex(ValueError,'Name the checkpoint'):packager.package(archive,self.base/'parts0','')
        with self.assertRaises(TypeError):packager.package(archive,self.base/'parts0')
        with patch.object(packager,'LIMIT',400_000),patch.object(packager,'CHUNK',100_000):data=packager.package(archive,self.base/'parts','TEST CHECKPOINT')
        parts=self.base/'parts';self.assertEqual(data['checkpoint'],'TEST CHECKPOINT');self.assertGreaterEqual(len(data['parts']),2)
        self.assertEqual(list(data['file_chunks']),['runtimes/big.bin']);self.assertEqual(len(data['file_chunks']['runtimes/big.bin']['chunks']),4);self.assertEqual(data['file_chunks']['runtimes/big.bin']['mode'],0o100755)
        for row in data['parts']:self.assertLessEqual((parts/row['name']).stat().st_size,400_000)
        with ZipFile(parts/data['parts'][0]['name']) as first:self.assertLessEqual({'MANIFEST.json','README_INTEGRATION_01.txt'},set(first.namelist()))
        self.assertEqual(list(self.base.glob('ledger-parts-*')),[])
        loaded=installer.manifest(parts/'RELEASE_PARTS.json');self.assertEqual(loaded['checkpoint'],'TEST CHECKPOINT') # the shipped installer validates and restores what the packager wrote
        installer.extract(parts,loaded,self.target)
        for name,(content,mode) in files.items():
            self.assertEqual((self.target/name).read_bytes(),content,name);self.assertEqual((self.target/name).stat().st_mode&0o777,mode&0o777,name)
        self.assertFalse((self.target/'__LS_RELEASE_CHUNKS__').exists());self.assertEqual(sorted(p.name for p in parts.iterdir() if not p.name.endswith('.zip')),['RELEASE_PARTS.json'])


if __name__=='__main__':unittest.main()
