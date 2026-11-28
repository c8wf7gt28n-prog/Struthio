"""1.1 PK1: Kas as Debian packages (1.1 R1: kas-*, the graphite* names transitional): debian/, tools/debian_pkg.py and the kit's scripts, the doctor's accepted
versions and the payload check of a program split over packages. The chroot install itself is run by
tools/build_repo.sh and recorded in the slice's result; these are the fast checks of the same pieces."""
import json, os, shutil, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

from tools import debian_pkg as pkg
from workbench import accepted_versions, doctor
from workbench.release_integrity import sha, verify
from workbench.version import VERSION

ROOT = pkg.ROOT
HAS_DPKG = shutil.which('dpkg-deb') is not None


def fake_tree(base):
    """A small tree with the parts stage() reads: version.py, a manifest, debian/ and the icon."""
    base = Path(base)
    shutil.copytree(ROOT / 'debian', base / 'debian')
    (base / 'workbench').mkdir(); (base / 'workbench/version.py').write_text("VERSION = '1.1-pre1'\n")
    (base / 'branding/graphite').mkdir(parents=True); shutil.copy(ROOT / 'branding/graphite/graphite_icon_256.png', base / 'branding/graphite/')
    files = {'LS_XSESSION.sh': b'#!/bin/bash\n', 'workbench/a.py': b'x = 1\n',
             'runtimes/llama.cpp/b12359/runtime.json': b'{}', **{name: b'archive' for name in pkg.PARTS['kas-llama-runtime']}}
    for name, data in files.items():
        (base / name).parent.mkdir(parents=True, exist_ok=True); (base / name).write_bytes(data)
    (base / 'MANIFEST.json').write_text(json.dumps({'version': '1.1', 'files': {
        n: {'bytes': len(d), 'sha256': sha(base / n)} for n, d in files.items()}}))
    return base


class Version(unittest.TestCase):
    def test_package_version_comes_from_version_py(self):
        self.assertEqual(pkg.debian_version(pkg.upstream_version()), pkg.debian_version(VERSION))
        self.assertEqual(pkg.debian_version('1.0'), '1.0')
        for preview in ('1.1-pre1', '1.1pre1', '1.1~pre1', '1.1.pre1'):
            self.assertEqual(pkg.debian_version(preview), '1.1~pre1')
        with self.assertRaises(ValueError): pkg.debian_version('one point one')


class Control(unittest.TestCase):
    def test_four_kas_packages_four_transitional_and_their_architectures(self):      # 1.1 R1: kas-* and transitional graphite*
        stanzas = pkg.parse_control((ROOT / 'debian/control').read_text())
        self.assertEqual(stanzas[0]['Source'], 'kas-computer')
        self.assertEqual({s['Package']: s['Architecture'] for s in stanzas[1:]},
                         {'kas-computer': 'all', 'kas-llama-runtime': 'amd64', 'kas-session': 'all', 'kas-desktop': 'all',
                          'graphite': 'all', 'graphite-llama-runtime': 'all', 'graphite-session': 'all', 'graphite-desktop': 'all'})

    def test_graphite_depends_on_debians_own_python_and_pyside6(self):
        text = pkg.binary_control('kas-computer', '1.0', 100)
        depends = next(l for l in text.splitlines() if l.startswith('Depends:'))
        for need in ('python3 (>= 3.11)', 'python3-pyside6.qtcore (>= 6.8.2)', 'python3-pyside6.qttest', 'procps',
                     'python3-cryptography (>= 43)'):
            self.assertIn(need, depends)
        self.assertNotIn('\n ', text.split('Description:')[0], 'relations are folded onto one line')

    def test_session_and_desktop_are_tied_to_the_same_version_and_firmware_is_only_recommended(self):
        session = pkg.binary_control('kas-session', '1.1~pre1', 10)
        self.assertIn('kas-computer (= 1.1~pre1)', session); self.assertIn('fluxbox', session); self.assertIn('xinit', session)
        desktop = dict(line.split(': ', 1) for line in pkg.binary_control('kas-desktop', '1.1~pre1', 10).splitlines() if ': ' in line and not line.startswith(' '))
        self.assertIn('kas-session (= 1.1~pre1)', desktop['Depends'])
        self.assertNotIn('lightdm', desktop['Depends']); self.assertNotIn('firmware', desktop['Depends'])
        self.assertIn('lightdm-gtk-greeter', desktop['Recommends']); self.assertIn('firmware-amd-graphics', desktop['Recommends'])

    def test_login_entries(self):
        xsession = (ROOT / 'debian/graphite-xsession.desktop').read_text()
        self.assertIn('Exec=kas-session\n', xsession); self.assertIn('Type=Application', xsession)  # lintian: desktop-entry-unknown-type for XSession
        self.assertIn('user-session=graphite', (ROOT / 'debian/50-graphite.conf').read_text())
        self.assertIn('Exec=kas-computer\n', (ROOT / 'debian/graphite.desktop').read_text())


class Staging(unittest.TestCase):
    def test_payload_split_gives_every_file_one_package(self):
        names = pkg.payload(ROOT)
        parts = pkg.split_payload(names)
        self.assertEqual(sorted(n for files in parts.values() for n in files), sorted(names))
        self.assertEqual(sorted(parts['kas-llama-runtime']), sorted(pkg.PARTS['kas-llama-runtime']))
        self.assertIn('runtimes/llama.cpp/b12359/runtime.json', parts['kas-computer'])  # a seed input stays with the program
        self.assertIn('LS_XSESSION.sh', parts['kas-computer'])

    def test_stage_each_package_on_a_small_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = fake_tree(Path(tmp) / 'tree')
            pkg.stage('kas-computer', Path(tmp) / 'g', root=tree)
            g = Path(tmp) / 'g'
            self.assertTrue((g / 'usr/lib/graphite/workbench/a.py').is_file())
            self.assertFalse((g / 'usr/lib/graphite' / pkg.PARTS['kas-llama-runtime'][0]).exists())
            self.assertEqual(oct((g / 'usr/lib/graphite/LS_XSESSION.sh').stat().st_mode & 0o777), '0o755')
            self.assertTrue(os.access(g / 'usr/bin/kas-computer', os.X_OK))
            self.assertEqual(os.readlink(g / 'usr/bin/graphite'), 'kas-computer')      # 1.1 R1: the old name, a symlink
            self.assertTrue((g / 'usr/share/applications/graphite.desktop').is_file())
            parts = json.loads((g / 'usr/lib/graphite/PACKAGE_PARTS.json').read_text())
            self.assertEqual(parts['parts']['kas-llama-runtime'], list(pkg.PARTS['kas-llama-runtime']))
            self.assertIn('Version: 1.1~pre1\n', (g / 'DEBIAN/control').read_text())
            pkg.stage('kas-llama-runtime', Path(tmp) / 'r', root=tree)
            self.assertIn('Architecture: amd64', (Path(tmp) / 'r/DEBIAN/control').read_text())
            pkg.stage('kas-session', Path(tmp) / 's', root=tree)
            self.assertTrue((Path(tmp) / 's/usr/share/xsessions/graphite.desktop').is_file())
            self.assertTrue(os.access(Path(tmp) / 's/usr/bin/kas-startx', os.X_OK))
            self.assertEqual(os.readlink(Path(tmp) / 's/usr/bin/graphite-startx'), 'kas-startx')
            pkg.stage('kas-desktop', Path(tmp) / 'd', root=tree)
            self.assertTrue((Path(tmp) / 'd/usr/share/lightdm/lightdm.conf.d/50-graphite.conf').is_file())


class Repository(unittest.TestCase):
    @unittest.skipUnless(HAS_DPKG, 'dpkg-deb is not on this computer')
    def test_index_writes_packages_and_release_with_matching_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = fake_tree(Path(tmp) / 'tree'); repo = Path(tmp) / 'repo'; repo.mkdir()
            pkg.stage('kas-session', Path(tmp) / 's', root=tree)
            subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(Path(tmp) / 's'), str(repo / 'kas-session_1.1~pre1_all.deb')],
                           check=True, capture_output=True)
            self.assertEqual(pkg.index(repo), 1)
            packages = (repo / 'Packages').read_text()
            self.assertIn('Package: kas-session\n', packages); self.assertIn('Filename: ./kas-session_1.1~pre1_all.deb', packages)
            self.assertIn('SHA256: ' + pkg.digest(repo / 'kas-session_1.1~pre1_all.deb', 'sha256'), packages)
            release = (repo / 'Release').read_text()
            self.assertIn(' %s %d Packages\n' % (pkg.digest(repo / 'Packages', 'sha256'), (repo / 'Packages').stat().st_size), release)


class Kit(unittest.TestCase):
    def make(self, tmp):
        repo = Path(tmp) / 'repo'; repo.mkdir()
        (repo / 'big_1.0_all.deb').write_bytes(os.urandom(2_500_000))
        for n in range(6): (repo / ('small%d_1.0_all.deb' % n)).write_bytes(os.urandom(300_000))
        (repo / 'Packages').write_text('Package: big\n')
        return repo

    def test_every_kit_file_is_under_the_limit_and_join_restores_the_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make(tmp); kit = Path(tmp) / 'kit'
            summary = pkg.pack(repo, kit, limit=1_000_000, piece=900_000, fill=800_000)
            self.assertGreater(summary['pieces'], 1)
            self.assertTrue(all(p.stat().st_size < 1_000_000 for p in kit.iterdir()))
            self.assertEqual(pkg.join(kit, Path(tmp) / 'out'), [])
            self.assertEqual((Path(tmp) / 'out/repo/big_1.0_all.deb').read_bytes(), (repo / 'big_1.0_all.deb').read_bytes())
            self.assertFalse(list((Path(tmp) / 'out/repo').glob('*.00[0-9]')))

    def test_real_limit_is_fifteen_million_bytes(self):
        self.assertEqual(pkg.LIMIT, 15_000_000)
        self.assertLess(pkg.PIECE + 4096, pkg.LIMIT); self.assertLess(pkg.ZIP_FILL + 65536, pkg.LIMIT)

    @unittest.skipUnless(shutil.which('sha256sum'), 'needs coreutils')
    def test_join_sh_checks_every_piece_and_refuses_a_changed_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.make(tmp); kit = Path(tmp) / 'kit'
            pkg.pack(repo, kit, limit=1_000_000, piece=900_000, fill=800_000)
            shutil.copy(ROOT / 'debian/kit/JOIN.sh', kit)
            run = subprocess.run(['bash', str(kit / 'JOIN.sh')], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr); self.assertIn('JOINED AND CHECKED: 7 packages', run.stdout)
            self.assertEqual(pkg.digest(kit / 'repo/big_1.0_all.deb', 'sha256'), pkg.digest(repo / 'big_1.0_all.deb', 'sha256'))
            line = (kit / 'PIECES.sha256').read_text().splitlines()[0].split('  ')
            (kit / 'PIECES.sha256').write_text((kit / 'PIECES.sha256').read_text().replace(line[0], '0' * 64, 1))
            run = subprocess.run(['bash', str(kit / 'JOIN.sh')], capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0); self.assertIn('does not match', run.stderr)

    def test_scripts_parse_and_install_refuses_an_ordinary_user(self):
        for script in ('tools/build_deb.sh', 'tools/build_repo.sh', 'tools/build_kit.sh', 'debian/kit/JOIN.sh',
                       'debian/kit/install.sh', 'debian/bin/kas-computer', 'debian/bin/kas-session', 'debian/bin/kas-startx'):
            self.assertEqual(subprocess.run(['bash', '-n', str(ROOT / script)]).returncode, 0, script)
        if os.geteuid() != 0:
            run = subprocess.run(['bash', str(ROOT / 'debian/kit/install.sh'), '--check'], capture_output=True, text=True)
            self.assertEqual(run.returncode, 1); self.assertIn('as root', run.stderr)
        page = (ROOT / 'debian/kit/START_HERE.md').read_text()
        for words in ('kas-startx', 'systemctl disable lightdm', 'apt remove kas-desktop lightdm lightdm-gtk-greeter',
                      '~/Applications/Graphite-1.0', 'Ctrl+Alt+F2'):
            self.assertIn(words, page)


class Doctor(unittest.TestCase):
    def test_debians_own_versions_are_accepted(self):
        state = accepted_versions.state
        self.assertEqual(state('PySide6', '6.8.3'), 'PINNED'); self.assertEqual(state('PySide6', '6.8.2.1'), 'ACCEPTED')
        self.assertEqual(state('PySide6', '6.7.3'), 'DIFFERENT_VERSION'); self.assertEqual(state('PySide6', '6.9.0'), 'DIFFERENT_VERSION')
        self.assertEqual(state('cryptography', '43.0.0'), 'ACCEPTED'); self.assertEqual(state('cryptography', '41.0.7'), 'DIFFERENT_VERSION')
        self.assertEqual(state('cryptography', None), 'MISSING')
        self.assertTrue(accepted_versions.qt_ready('6.8.2')); self.assertTrue(accepted_versions.qt_ready('6.8.3'))
        self.assertFalse(accepted_versions.qt_ready('6.9.0'))
        with patch('importlib.metadata.version', side_effect=lambda name: {'PySide6': '6.8.2.1', 'cryptography': '43.0.0'}[name]):
            rows = doctor.dependencies()
        self.assertEqual([r['state'] for r in rows], ['ACCEPTED', 'ACCEPTED'])
        self.assertEqual(rows[0]['expected'], '6.8.3')


class Payload(unittest.TestCase):
    def test_a_part_not_installed_is_not_damage_but_half_a_part_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = fake_tree(Path(tmp) / 'tree')
            part = pkg.PARTS['kas-llama-runtime']
            self.assertEqual(verify(tree)['state'], 'VERIFIED')
            (tree / part[0]).unlink()
            self.assertEqual(verify(tree)['problems'], [part[0] + ': missing'])  # a folder install: no parts file
            (tree / pkg.PARTS_FILE).write_text(json.dumps({'parts': {'kas-llama-runtime': list(part)}}))
            self.assertEqual(verify(tree)['state'], 'DAMAGED')  # half a part
            (tree / part[1]).unlink()
            result = verify(tree)
            self.assertEqual((result['state'], result['parts_not_installed']), ('VERIFIED', ['kas-llama-runtime']))
            (tree / 'workbench/a.py').unlink()
            self.assertEqual(verify(tree)['problems'], ['workbench/a.py: missing'])


if __name__ == '__main__':
    unittest.main()
