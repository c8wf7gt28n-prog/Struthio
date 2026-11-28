"""1.1 KS3, the system door (PLAN_1.1.md, KS3; the coordinator's note of 28 Nov).

Acceptance first: an install is shown before anything is asked (what it pulls in, its size, "The system will ask for your
password", what Undo does); the owner's press asks the system through its own prompt (the interactive flag on the call)
and the install is verified by reading it back; Undo removes what it pulled in; a service restarted is verified by its new
start; the time zone, network time, the computer's name and a new standard account are each verified and undone.

Then the rules: names are validated before anything is asked (a package, a unit, a zone, a login); the door never runs as
her step, never under a standing grant, and HALT holds it (and cancels a PackageKit transaction still waiting); the
prompt's no changes nothing and is said; a plan that changed since it was shown is not asked; with no prompt agent nothing
is asked; offer(argv) maps root command lines for the command tool; her talk, NEXT STEPS and the line show it.

There is no system bus here, no systemd, no PackageKit and no polkit: every service is a fake on a private dbus-daemon
(FakeSystem below) that keeps invented state and answers on the wire as the real services do; its "prompt" says yes, no,
or cannot open. What a real polkit agent, PackageKit's apt backend and systemd do on Debian 13 is not exercised here.

Run alone:  python3 -B -m unittest -v tests_integrated.test_system_door
"""
import os, re, subprocess, sys, tempfile, threading, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from workbench import system_bus as sb  # noqa: E402
from workbench import system_door as sd  # noqa: E402

PK_PATH, SD_PATH, TD_PATH, HN_PATH, AC_PATH = sd.PK_PATH, sd.SD_PATH, sd.TD_PATH, sd.HN_PATH, sd.AC_PATH
NAMES = (sd.PK, sd.SD, sd.TD, sd.HN, sd.AC)
FLAG = sb.INTERACTIVE


def unit_path(name):
    return SD_PATH + '/unit/' + re.sub(r'[^A-Za-z0-9]', lambda c: '_%02x' % ord(c.group()), name)


class FakeSystem:
    """Invented services on a private bus: PackageKit, systemd, timedated, hostnamed, accountsservice. `answer` is what the
    system's prompt says (yes, no, none: no prompt could open); `delay` is how long the owner takes at it. `asked` lists
    every call that needed the prompt, with whether it carried the interactive flag."""

    def __init__(self):
        self.dir = tempfile.mkdtemp()
        self.daemon = subprocess.Popen(['dbus-daemon', '--session', '--nofork', '--print-address=1', '--address=unix:path=%s/bus' % self.dir],
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        self.addr = self.daemon.stdout.readline().strip()
        self.answer, self.delay, self.asked, self.pending, self.stop, self.tx = 'yes', 0.0, [], [], False, 0
        self.archive = {'gimp': ('3.0.4-1', 'GNU Image Manipulation Program', ['gimp-data', 'libgimp3.0-0', 'libbabl-0.1-0'], 9_000_000, 30_000_000),
                        'gimp-data': ('3.0.4-1', 'data files for GIMP', [], 11_000_000, 40_000_000),
                        'libgimp3.0-0': ('3.0.4-1', 'libraries for GIMP', [], 1_000_000, 4_000_000),
                        'libbabl-0.1-0': ('1:0.1.112-1', 'dynamic pixel format library', [], 1_000_000, 3_000_000),
                        'nano': ('8.4-2', 'small editor', [], 700_000, 2_800_000), 'tern-tools': ('1.2-1', 'invented field tools', ['nano'], 50_000, 200_000)}
        self.installed = {'nano': '8.4-1', 'tern-tools': '1.2-1'}
        self.units = {'cups.service': dict(desc='CUPS Scheduler', active='active', sub='running', file='enabled', entered=1_000),
                      'tern-sync.service': dict(desc='Tern sync (invented)', active='inactive', sub='dead', file='disabled', entered=0),
                      'dbus.service': dict(desc='D-Bus System Message Bus', active='active', sub='running', file='static', entered=5)}
        self.time = dict(Timezone='Europe/Berlin', NTP=True, CanNTP=True, NTPSynchronized=True)
        self.host = 'harbour-desk'
        self.users = {'kit': [1000, 'Kit Tern', 0]}
        ready = threading.Event()
        self.thread = threading.Thread(target=self.serve, args=(ready,), daemon=True);self.thread.start();ready.wait(10)

    def close(self):
        self.stop = True;self.thread.join(5);self.daemon.terminate();self.daemon.wait(5)

    def passwd(self, login):
        u = self.users.get(login)
        return SimpleNamespace(pw_uid=u[0], pw_dir='/home/' + login) if u else None

    # -- the loop
    def serve(self, ready):
        b = self.bus = sb.Bus(self.addr)
        for name in NAMES:b.own(name)
        ready.set()
        while not self.stop:
            due = min([p[0] for p in self.pending], default=time.monotonic() + 0.05)
            try:m = b.next_call(min(due, time.monotonic() + 0.05))
            except TimeoutError:
                m = None
            now = time.monotonic()
            for p in [p for p in self.pending if p[0] <= now]:
                self.pending.remove(p);p[1]()
            if m is None:continue
            try:self.handle(m)
            except Exception as exc:  # noqa: BLE001 - a fake's own fault, said on the wire
                b.fail(m, 'org.freedesktop.DBus.Error.Failed', repr(exc))

    def prompt(self, m, then, no='org.freedesktop.DBus.Error.AccessDenied', sig='', args=()):
        """The system's own prompt (polkit) in front of a method that answers after it."""
        self.asked.append((m.member, bool(m.flags & FLAG)))
        if self.answer == 'none' or not m.flags & FLAG:
            return self.bus.fail(m, 'org.freedesktop.DBus.Error.InteractiveAuthorizationRequired', 'Interactive authentication required.')

        def answer():
            if self.answer == 'no':return self.bus.fail(m, no, 'Access denied')
            got = then();self.bus.reply(m, sig, got if got is not None else args)
        self.pending.append((time.monotonic() + self.delay, answer))

    def handle(self, m):
        b = self.bus
        if m.interface == 'org.freedesktop.DBus.Properties':
            props = self.props(m.path, m.body[0])
            if m.member == 'GetAll':return b.reply(m, 'a{sv}', (props,))
            if m.body[1] not in props:return b.fail(m, 'org.freedesktop.DBus.Error.UnknownProperty', m.body[1])
            return b.reply(m, 'v', (props[m.body[1]],))
        if m.destination == sd.PK or m.interface in (sd.PK, sd.PK_TX):return self.packagekit(m)
        if m.interface == sd.SD_MGR:return self.systemd(m)
        if m.interface == sd.TD:return self.timedate(m)
        if m.interface == sd.HN:
            return self.prompt(m, lambda: setattr(self, 'host', m.body[0])) if m.member == 'SetStaticHostname' else b.fail(m, 'org.freedesktop.DBus.Error.UnknownMethod')
        if m.interface in (sd.AC, sd.AC_USER):return self.accounts(m)
        b.fail(m, 'org.freedesktop.DBus.Error.UnknownMethod', m.member or '')

    def props(self, path, iface):
        if path == PK_PATH:return {'VersionMajor': ('u', 1)}
        if path == SD_PATH:return {'Version': ('s', '257.9-1')}
        if path.startswith(SD_PATH + '/unit/'):
            name = next((n for n in list(self.units) + [getattr(self, 'loaded', '')] if unit_path(n) == path), '')
            u = self.units.get(name)
            if u is None:return {'Id': ('s', name), 'LoadState': ('s', 'not-found'), 'ActiveState': ('s', 'inactive'), 'SubState': ('s', 'dead'),
                                 'Description': ('s', name), 'UnitFileState': ('s', ''), 'ActiveEnterTimestamp': ('t', 0)}
            return {'Id': ('s', name), 'LoadState': ('s', 'loaded'), 'ActiveState': ('s', u['active']), 'SubState': ('s', u['sub']),
                    'Description': ('s', u['desc']), 'UnitFileState': ('s', u['file']), 'ActiveEnterTimestamp': ('t', u['entered'])}
        if path == TD_PATH:return {k: ('s' if k == 'Timezone' else 'b', v) for k, v in self.time.items()} | {'TimeUSec': ('t', int(time.time() * 1e6))}
        if path == HN_PATH:return {'Hostname': ('s', self.host), 'StaticHostname': ('s', self.host), 'PrettyHostname': ('s', '')}
        if path == AC_PATH:return {'DaemonVersion': ('s', '23.13.9')}
        login = next((n for n, u in self.users.items() if path == AC_PATH + '/User%d' % u[0]), None)
        if login:
            u = self.users[login]
            return {'UserName': ('s', login), 'RealName': ('s', u[1]), 'AccountType': ('i', u[2]), 'Uid': ('t', u[0])}
        return {}

    # -- PackageKit: transactions answer by signals
    def pid(self, name, installed=False):
        version = self.installed[name] if installed else self.archive[name][0]
        return '%s;%s;amd64;%s' % (name, version, 'installed:debian-trixie-main' if installed else 'debian-trixie-main')

    def emit(self, path, member, sig, *args):
        self.bus.emit(path, sd.PK_TX, member, sig, args)

    def finish(self, path, exit=1):
        self.emit(path, 'Finished', 'uu', exit, 10)

    def packagekit(self, m):
        b, path, body = self.bus, m.path, m.body
        if m.member == 'CreateTransaction':
            self.tx += 1;return b.reply(m, 'o', ('/%d_tern' % self.tx,))
        if m.member in ('SetHints',):return b.reply(m)
        if m.member == 'Cancel':
            for p in [p for p in self.pending if getattr(p[1], 'tx', None) == path]:self.pending.remove(p)
            b.reply(m);self.emit(path, 'ErrorCode', 'us', 17, 'The task was stopped successfully');return self.finish(path, sd.EXIT_CANCELLED)
        b.reply(m)
        simulate = bool(body and isinstance(body[0], int) and body[0] & sd.SIMULATE) if m.member != 'RefreshCache' else False
        names = [i.split(';')[0] for i in (body[1] if m.member in ('InstallPackages', 'RemovePackages', 'UpdatePackages') else [])]
        if m.member == 'Resolve':
            for n in body[1]:
                if n in self.installed and body[0] & (sd.FILTER_NONE | sd.FILTER_INSTALLED):self.emit(path, 'Package', 'uss', sd.INSTALLED, self.pid(n, True), self.archive[n][1])
                elif n in self.archive and n not in self.installed and body[0] & (sd.FILTER_NONE | sd.FILTER_NOT_INSTALLED):
                    self.emit(path, 'Package', 'uss', sd.AVAILABLE, self.pid(n), self.archive[n][1])
            return self.finish(path)
        if m.member == 'GetDetails':
            for i in body[0]:
                a = self.archive[i.split(';')[0]]
                self.emit(path, 'Details', 'a{sv}', {'package-id': ('s', i), 'summary': ('s', a[1]), 'size': ('t', a[4]), 'download-size': ('t', a[3])})
            return self.finish(path)
        if m.member == 'GetUpdates':
            for n, v in self.installed.items():
                if self.archive[n][0] != v:self.emit(path, 'Package', 'uss', 5, self.pid(n), self.archive[n][1])
            return self.finish(path)
        if m.member == 'RemovePackages':
            needed = [o for o in self.installed if o not in names and any(n in self.archive[o][2] for n in names)]
            if needed and not body[2]:
                self.emit(path, 'ErrorCode', 'us', sd.PK_DEPS, '%s is needed by %s' % (names[0], needed[0]));return self.finish(path, 2)
        if simulate:
            if m.member == 'InstallPackages':
                for n in names + [d for d in self.archive[names[0]][2] if d not in self.installed]:self.emit(path, 'Package', 'uss', sd.INSTALLING, self.pid(n), self.archive[n][1])
            elif m.member == 'RemovePackages':self.emit(path, 'Package', 'uss', sd.REMOVING, self.pid(names[0], True), '')
            else:self.emit(path, 'Package', 'uss', sd.UPDATING, self.pid(names[0]), '')
            return self.finish(path)
        self.asked.append((m.member, bool(m.flags & FLAG)))

        def done():
            if self.answer in ('no', 'none'):
                self.emit(path, 'ErrorCode', 'us', sd.PK_NOT_AUTHORIZED, 'Failed to obtain authentication.');return self.finish(path, 2)
            if m.member == 'InstallPackages':
                for n in names + list(self.archive[names[0]][2]):self.installed.setdefault(n, self.archive[n][0])
            elif m.member == 'RemovePackages':
                for n in names:self.installed.pop(n, None)
            elif m.member == 'UpdatePackages':
                self.installed[names[0]] = self.archive[names[0]][0]
            self.finish(path)
        done.tx = path
        self.pending.append((time.monotonic() + self.delay, done))

    # -- systemd, timedated, accountsservice: the prompt in front of the answer
    def systemd(self, m):
        b, name = self.bus, (m.body[0] if m.body else '')
        if m.member == 'LoadUnit':self.loaded = name;return b.reply(m, 'o', (unit_path(name),))
        if m.member == 'GetUnitFileState':
            if name not in self.units:return b.fail(m, 'org.freedesktop.systemd1.NoSuchUnit', 'No such file')
            return b.reply(m, 's', (self.units[name]['file'],))
        u = self.units.get(name if isinstance(name, str) else name[0])
        if m.member in ('StartUnit', 'RestartUnit'):
            return self.prompt(m, lambda: u.update(active='active', sub='running', entered=u['entered'] + 1_000_000), sig='o', args=(SD_PATH + '/job/7',))
        if m.member == 'StopUnit':return self.prompt(m, lambda: u.update(active='inactive', sub='dead'), sig='o', args=(SD_PATH + '/job/8',))
        if m.member == 'EnableUnitFiles':return self.prompt(m, lambda: u.update(file='enabled'), sig='ba(sss)', args=(True, [('symlink', '/etc/x', '/usr/lib/x')]))
        if m.member == 'DisableUnitFiles':return self.prompt(m, lambda: u.update(file='disabled'), sig='a(sss)', args=([('unlink', '/etc/x', '')],))
        b.fail(m, 'org.freedesktop.DBus.Error.UnknownMethod', m.member)

    def timedate(self, m):
        if m.member == 'SetTimezone':return self.prompt(m, lambda: self.time.update(Timezone=m.body[0]))
        if m.member == 'SetNTP':return self.prompt(m, lambda: self.time.update(NTP=m.body[0]))
        if m.member == 'SetTime':
            if self.time['NTP']:return self.bus.fail(m, 'org.freedesktop.timedate1.AutomaticTimeSyncEnabled', 'Automatic time synchronization is enabled')
            return self.prompt(m, lambda: None)
        self.bus.fail(m, 'org.freedesktop.DBus.Error.UnknownMethod', m.member)

    def accounts(self, m):
        b, no = self.bus, 'org.freedesktop.Accounts.Error.PermissionDenied'
        if m.member == 'ListCachedUsers':return b.reply(m, 'ao', ([AC_PATH + '/User%d' % u[0] for u in self.users.values()],))
        if m.member == 'FindUserByName':
            u = self.users.get(m.body[0])
            return b.reply(m, 'o', (AC_PATH + '/User%d' % u[0],)) if u else b.fail(m, 'org.freedesktop.Accounts.Error.Failed', 'Failed to look up user')
        if m.member == 'CreateUser':
            def add():
                uid = 1000 + len(self.users);self.users[m.body[0]] = [uid, m.body[1], m.body[2]];return (AC_PATH + '/User%d' % uid,)
            return self.prompt(m, add, no, sig='o')
        if m.member == 'DeleteUser':
            return self.prompt(m, lambda: [self.users.pop(n) for n, u in list(self.users.items()) if u[0] == m.body[0]] and None, no)
        if m.member == 'SetRealName':
            login = next(n for n, u in self.users.items() if m.path == AC_PATH + '/User%d' % u[0])
            return self.prompt(m, lambda: self.users[login].__setitem__(1, m.body[0]), no)
        b.fail(m, 'org.freedesktop.DBus.Error.UnknownMethod', m.member)


AGENT = dict(running=True, name='lxpolkit', pid=4242, words='Permission prompts are answered by lxpolkit (process 4242), started with this session.')


class Door(unittest.TestCase):
    """A throwaway HOME, a workspace, a Kernel, the owner's principal, and the fake system on DBUS_SYSTEM_BUS_ADDRESS."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();base = Path(self.temp.name)
        (base / 'home').mkdir();(base / 'ws').mkdir();units = base / 'units';units.mkdir()
        for name in ('cups.service', 'tern-sync.service', 'dbus.service'):(units / name).write_text('[Unit]\n')
        self.fake = FakeSystem()
        self.env = patch.dict(os.environ, {'HOME': str(base / 'home'), 'DBUS_SYSTEM_BUS_ADDRESS': self.fake.addr});self.env.start()
        self.patches = [patch.object(sd, 'prompt_agent', lambda: dict(AGENT)), patch.object(sd, '_passwd', self.fake.passwd),
                        patch.object(sd, 'UNIT_DIRS', (str(units),)), patch.object(sd, 'UNIT_SECONDS', 3)]
        for p in self.patches:p.start()
        from workbench.engineering_kernel import Kernel, operator
        self.kernel = Kernel(base / 'ws');self.owner = operator()

    def tearDown(self):
        for p in self.patches:p.stop()
        self.env.stop();self.fake.close();self.temp.cleanup()

    def call(self, op, args, who=None):
        return self.kernel.dispatch(op, args, who or self.owner)

    def plan(self, action, target='', value=''):
        answer = self.call('system.door.plan', {'action': action, 'target': target, 'value': value})
        self.assertTrue(answer['ok'], answer);return answer['result']

    def press(self, action, target='', value='', p=None, who=None):
        p = p or self.plan(action, target, value)
        return self.call('system.door.run', {'action': action, 'target': target, 'value': value, 'digest': p['digest']}, who)


class Acceptance(Door):
    def test_an_install_is_shown_first_with_what_it_pulls_in_and_its_size_and_nothing_is_asked(self):
        p = self.plan('package.install', 'gimp')
        self.assertEqual((p['title'], p['ok'], p['nothing'], p['can_undo']), ('Install GIMP', True, False, True))
        self.assertEqual(p['words'], 'This will install gimp 3.0.4-1 (GNU Image Manipulation Program) and 3 packages it needs: gimp-data, '
                                     'libgimp3.0-0, libbabl-0.1-0. Download 21.0 MB. About 73.4 MB on disk.')
        self.assertEqual(p['asks'], 'The system will ask for your password.')
        self.assertEqual(p['undo'], 'Undo removes it and the packages it pulled in.')
        self.assertIn('gimp-data 3.0.4-1 · data files for GIMP', p['lines'])
        self.assertEqual(self.fake.asked, [], 'a plan asks the system for nothing')
        self.assertNotIn('gimp', self.fake.installed)

    def test_the_press_installs_through_the_system_prompt_is_verified_and_undo_removes_what_it_pulled_in(self):
        v = self.press('package.install', 'gimp')['result']
        self.assertEqual((v['state'], v['verified'], v['can_undo']), ('done', True, True), v)
        self.assertEqual(v['checked'], 'gimp 3.0.4-1 is installed (PackageKit read it back)')
        self.assertEqual(self.fake.asked, [('InstallPackages', True)], 'one fixed action, asked once, with the interactive flag')
        self.assertEqual(sorted(self.fake.installed), ['gimp', 'gimp-data', 'libbabl-0.1-0', 'libgimp3.0-0', 'nano', 'tern-tools'])
        back = self.call('system.door.undo', {'run': v['run']})['result']
        self.assertEqual((back['state'], back['verified']), ('done', True), back)
        self.assertEqual(sorted(self.fake.installed), ['nano', 'tern-tools'])
        self.assertEqual(self.fake.asked[-1], ('RemovePackages', True))
        self.assertIn('already taken back', self.call('system.door.undo', {'run': v['run']})['error']['message'])
        runs = self.call('system.door.runs', {})['result']['runs']
        self.assertEqual([(r['title'], r['state'], bool(r['undone'])) for r in runs], [('Install GIMP', 'done', True)])

    def test_a_service_restarted_is_verified_by_its_new_start_and_start_stop_enable_disable_undo(self):
        v = self.press('service.restart', 'cups')['result']
        self.assertEqual((v['title'], v['state'], v['verified'], v['can_undo']), ('Restart cups.service', 'done', True, False), v)
        self.assertEqual(v['checked'], 'cups.service is active (running), started again')
        self.assertEqual(self.plan('service.restart', 'cups')['undo'], 'A restart cannot be undone; it only restarted.')
        for action, after, undone in (('service.start', 'active', 'inactive'), ('service.enable', 'enabled', 'disabled')):
            v = self.press(action, 'tern-sync')['result'];self.assertTrue(v['verified'], v)
            key = 'active' if action == 'service.start' else 'file'
            self.assertEqual(self.fake.units['tern-sync.service'][key], after)
            self.assertTrue(self.call('system.door.undo', {'run': v['run']})['result']['verified'])
            self.assertEqual(self.fake.units['tern-sync.service'][key], undone)
        self.assertTrue(self.plan('service.stop', 'tern-sync')['nothing'], 'stopping what is not running asks nothing')
        self.assertTrue(all(flag for _, flag in self.fake.asked))

    def test_the_time_zone_network_time_the_name_and_an_account_are_each_verified_and_undone(self):
        p = self.plan('time.zone', 'europe/lisbon')
        self.assertEqual(p['target'], 'Europe/Lisbon');self.assertTrue(p['words'].startswith('This will set the time zone to Europe/Lisbon (it is Europe/Berlin now).'))
        cases = (('time.zone', 'Europe/Lisbon', '', lambda: self.fake.time['Timezone'], 'Europe/Lisbon', 'Europe/Berlin'),
                 ('time.ntp', 'off', '', lambda: self.fake.time['NTP'], False, True),
                 ('host.name', 'tern-lab', '', lambda: self.fake.host, 'tern-lab', 'harbour-desk'),
                 ('user.add', 'ana', 'Ana Plover', lambda: 'ana' in self.fake.users, True, False),
                 ('user.realname', 'kit', 'Kit Plover', lambda: self.fake.users['kit'][1], 'Kit Plover', 'Kit Tern'))
        for action, target, value, read, after, before in cases:
            v = self.press(action, target, value)['result']
            self.assertEqual((v['state'], v['verified']), ('done', True), (action, v));self.assertEqual(read(), after, action)
            back = self.call('system.door.undo', {'run': v['run']})['result']
            self.assertEqual((back['state'], back['verified']), ('done', True), (action, back));self.assertEqual(read(), before, action)
        self.assertEqual(self.fake.users.get('ana'), None)
        self.assertIn('It has no password yet', self.plan('user.add', 'ana')['words'])


class Rules(Door):
    def test_names_are_validated_before_anything_is_asked(self):
        refused = {('package.install', 'Gimp!'): 'is not a Debian package name', ('service.start', 'cu ps'): 'is not a service name',
                   ('time.zone', 'Mars/Olympus'): 'there is no time zone “Mars/Olympus”', ('service.stop', 'dbus'): 'keeps this session',
                   ('package.remove', 'packagekit'): 'keeps this session', ('host.name', '-tern'): 'cannot be a computer’s name',
                   ('user.add', 'Ana Plover'): 'cannot be an account name'}
        for (action, target), words in refused.items():
            answer = self.call('system.door.plan', {'action': action, 'target': target})
            self.assertFalse(answer['ok'], (action, target));self.assertIn(words, answer['error']['message'])
        nope = {('package.install', 'gimpp'): 'Debian’s archive here has no package called “gimpp”', ('service.start', 'plover'): 'there is no service called plover.service',
                ('user.add', 'kit'): 'the name “kit” is taken', ('package.remove', 'nano'): 'other installed software needs nano'}
        for (action, target), words in nope.items():
            p = self.plan(action, target);self.assertFalse(p['ok'], p);self.assertIn(words, p['why'])
        self.assertEqual(self.plan('package.install', 'nano')['words'], 'nano is installed already (version 8.4-1).')
        self.assertEqual(self.fake.asked, [])

    def test_never_her_step_never_under_a_grant_and_halt_holds_it_and_cancels_a_waiting_transaction(self):
        from workbench.engineering_kernel import Principal
        from workbench.grants import _PERMIT
        p = self.plan('package.install', 'gimp')
        hers = Principal('kasandra', frozenset({'read', 'execute'}))
        self.assertIn('outside the authorized', self.press('package.install', 'gimp', p=p, who=hers)['error']['message'])
        token = _PERMIT.set(object())
        try:said = self.press('package.install', 'gimp', p=p)['error']['message']
        finally:_PERMIT.reset(token)
        self.assertIn('never under a standing grant', said)
        self.assertTrue(self.call('halt.press', {})['ok'])
        self.assertIn('HALT holds my work', self.press('package.install', 'gimp', p=p)['error']['message'])
        self.assertTrue(self.call('system.door.plan', {'action': 'package.install', 'target': 'gimp'})['ok'], 'HALT stops her work and nothing else')
        self.assertTrue(self.call('halt.release', {})['ok'])
        self.assertEqual(self.fake.asked, []);self.assertNotIn('gimp', self.fake.installed)
        p = sd.plan('package.install', 'gimp');self.fake.delay = 5.0;t0 = time.monotonic()
        s = sd.System(halt=lambda: time.monotonic() - t0 > 0.4)
        try:
            with self.assertRaises(sd.Refused) as caught:sd.do(s, p)
        finally:s.close()
        self.assertIn('DOOR_CANCELLED', str(caught.exception));self.assertLess(time.monotonic() - t0, 4)
        self.assertNotIn('gimp', self.fake.installed)

    def test_the_prompt_saying_no_changes_nothing_and_says_so_and_a_changed_plan_is_not_asked(self):
        self.fake.answer = 'no'
        v = self.press('package.install', 'gimp')['result']
        self.assertEqual((v['state'], v['verified'], v['can_undo'], v['checked']), ('refused at the prompt', False, False, 'gimp is not installed'))
        v = self.press('time.zone', 'Europe/Lisbon')['result']
        self.assertEqual((v['state'], self.fake.time['Timezone']), ('refused at the prompt', 'Europe/Berlin'))
        self.fake.answer = 'none'
        self.assertEqual(self.press('service.start', 'tern-sync')['result']['state'], 'no prompt')
        self.fake.answer = 'yes'
        p = self.plan('package.install', 'gimp');self.fake.archive['gimp'] = ('3.0.4-2',) + self.fake.archive['gimp'][1:]
        said = self.press('package.install', 'gimp', p=p)['error']['message']
        self.assertIn('changed since you saw it', said);self.assertNotIn('gimp', self.fake.installed)

    def test_with_no_prompt_agent_nothing_is_asked(self):
        with patch.object(sd, 'prompt_agent', lambda: dict(running=False, words='No permission prompt agent is running in this session.')):
            p = self.plan('service.restart', 'cups')
            self.assertEqual((p['ok'], p['why']), (False, 'No permission prompt agent is running in this session.'))
            self.assertIn('No permission prompt agent is running', self.press('service.restart', 'cups', p=p)['error']['message'])
        self.assertEqual(self.fake.asked, [])

    def test_offer_maps_root_command_lines_to_one_fixed_action_for_the_command_tool(self):
        o = sd.offer(['sudo', 'apt', 'install', 'gimp'])
        self.assertEqual((o['action'], o['target'], o['title'], o['asks']), ('package.install', 'gimp', 'Install GIMP', 'asks for your password'))
        self.assertTrue(o['words'].startswith('That is the system door: Install GIMP'))
        cases = {('systemctl', 'restart', 'cups'): ('service.restart', 'cups.service'), ('apt-get', 'install', '-y', 'vlc'): ('package.install', 'vlc'),
                 ('sudo', 'apt', 'update'): ('packages.refresh', ''), ('apt', 'remove', 'gimp'): ('package.remove', 'gimp'),
                 ('apt', 'install', '--only-upgrade', 'nano'): ('package.update', 'nano'), ('service', 'cups', 'stop'): ('service.stop', 'cups.service'),
                 ('timedatectl', 'set-timezone', 'Europe/Lisbon'): ('time.zone', 'Europe/Lisbon'), ('timedatectl', 'set-ntp', 'false'): ('time.ntp', 'off'),
                 ('hostnamectl', 'set-hostname', 'tern-lab'): ('host.name', 'tern-lab'), ('sudo', 'adduser', 'ana'): ('user.add', 'ana')}
        for argv, (action, target) in cases.items():
            o = sd.offer(list(argv));self.assertEqual((o['action'], o['target']), (action, target), argv)
        for argv in (('apt', 'install', 'gimp', 'vlc'), ('sudo', '-u', 'kit', 'apt', 'install', 'gimp'), ('apt', 'purge', 'gimp'), ('passwd', 'ana'),
                     ('sudo', 'sh', '-c', 'apt install gimp'), ('systemctl', 'enable', '--now', 'cups'), ('apt', 'upgrade'), ('dpkg', '-i', 'x.deb'), ()):
            self.assertIsNone(sd.offer(list(argv)), argv)

    def test_her_words_name_the_action_and_a_service_only_when_its_unit_is_on_this_computer(self):
        words = {'install gimp': ('package.install', 'gimp', ''), 'please uninstall VLC': ('package.remove', 'vlc', ''),
                 'restart cups': ('service.restart', 'cups.service', ''), 'enable the tern-sync service at boot': ('service.enable', 'tern-sync.service', ''),
                 'set the time zone to europe/lisbon': ('time.zone', 'europe/lisbon', ''), 'turn off network time': ('time.ntp', 'off', ''),
                 'rename this computer to tern-lab': ('host.name', 'tern-lab', ''), 'add a user called ana named Ana Plover': ('user.add', 'ana', 'Ana Plover'),
                 'refresh the software lists': ('packages.refresh', '', ''), 'sudo apt install gimp': ('package.install', 'gimp', '')}
        for text, want in words.items():
            got = sd.read_words(text);self.assertEqual((got['action'], got['target'], got['value']), want, text)
        for text in ('start the model', 'restart godot', 'stop it', 'install', 'what is on the desk today', 'remove the file notes.txt', 'start a Godot project called Tern'):
            self.assertIsNone(sd.read_words(text), text)


class Window(Door):
    """Her talk, NEXT STEPS, the line and the Settings page, on a stand-in for Graphite's window (offscreen)."""

    def setUp(self):
        super().setUp()
        from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout
        self.app = QApplication.instance() or QApplication([])
        from workbench import system_door_qt as q
        self.q = q;q.SYNC = True;q.STATE.clear()
        test = self

        class Face:
            def __init__(self):self.said = [];self.host = test.host;self.thing = None

            def mine(self, text):self.said.append(('you', text))

            def say(self, text):
                bubble = QFrame();bubble.box = QVBoxLayout(bubble);self.said.append(('her', text, bubble));return bubble
        self.host = type('Host', (), {'root': self.kernel.root, 'her_column': None})()
        self.face = Face()

    def tearDown(self):
        self.q.SYNC = False;super().tearDown()

    def links(self, bubble):
        from PySide6.QtWidgets import QLabel
        return {w: fn for label in bubble.findChildren(QLabel) for k, (w, fn) in (getattr(label, '_actions', None) or {}).items()}

    def test_her_talk_shows_the_plan_then_asks_the_system_then_done_and_verified_with_undo_and_next_steps_follow(self):
        from PySide6.QtWidgets import QLabel
        self.assertTrue(self.q.asked(self.face, 'install gimp'))
        said = self.face.said[-1];self.assertEqual(said[1], 'Install GIMP. This is what the system will do; nothing has changed yet.')
        shown = ' '.join(l.text() for l in said[2].findChildren(QLabel))
        self.assertIn('3 packages it needs: gimp-data', shown);self.assertIn('Undo removes it and the packages it pulled in.', shown)
        self.assertIn('The system will ask for your password. Type it into the system’s own prompt, never here.', shown)
        self.assertEqual(sorted(self.links(said[2])), ['Install (the system asks)', 'Not now'])
        self.assertEqual([s['words'] for s in self.q.next_steps(self.host)], ['Install GIMP · asks for your password'])
        self.assertEqual(self.fake.asked, [])
        self.assertTrue(self.q.take(self.host, self.q.next_steps(self.host)[0]))
        self.assertEqual(self.face.said[-2][1], 'Asking the system now: “Install GIMP”. Its own prompt is on your screen; I never see the password.')
        done = self.face.said[-1]
        self.assertEqual(done[1], '✓ Done and verified, “Install GIMP”: gimp 3.0.4-1 is installed (PackageKit read it back).')
        self.assertEqual([s['words'] for s in self.q.next_steps(self.host)], ['Undo · Install GIMP · asks for your password'])
        self.links(done[2])['Undo (the system asks)']()
        self.assertEqual(self.face.said[-1][1], 'Undone and verified, “Install GIMP”: gimp is no longer installed (PackageKit read it back).')
        self.assertEqual(self.q.next_steps(self.host), [])
        self.assertTrue(self.q.asked(self.face, 'restart cups'));self.links(self.face.said[-1][2])['Restart (the system asks)']()
        self.assertEqual(self.face.said[-1][1], '✓ Done and verified, “Restart cups.service”: cups.service is active (running), started again.')
        self.fake.answer = 'no';self.q.asked(self.face, 'set the time zone to Europe/Lisbon');self.links(self.face.said[-1][2])['Set it (the system asks)']()
        self.assertEqual(self.face.said[-1][1], 'The system’s prompt was cancelled or refused, so nothing changed: the time zone is Europe/Berlin (timedated read it back).')
        self.assertFalse(self.q.asked(self.face, 'what is on the desk today'), 'not the door: the rest of her chain answers')

    def test_the_line_offers_install_gimp_asks_for_your_password_and_the_settings_page_draws(self):
        from workbench import line_finder as lf
        rows = lf.rows('install gimp', lf.Sources(None));door = [r for r in rows if r.extra.get('door')]
        self.assertEqual((door[0].title, door[0].verb, door[0].enter_words()), ('Install GIMP, asks for your password', 'Show', 'Enter: shows what the system will do; nothing changes'))
        self.assertTrue(all(r.verb in lf.VERBS for r in rows))
        self.assertFalse(any(r.extra.get('door') for r in lf.rows('tern', lf.Sources(None))))
        self.assertEqual(self.q.line_rows('install gimp', None)[0][2](), False, 'no window: nothing is done')
        from PySide6.QtWidgets import QLabel, QTabWidget
        self.host.tabs = QTabWidget()
        page = self.q.show_page(self.host)
        text = ' '.join(l.text() for l in page.findChildren(QLabel))
        for words in ('READY', 'Permission prompts are answered by lxpolkit', 'PackageKit answers', 'Time zone Europe/Berlin', 'NETWORK TIME ON', 'harbour-desk', 'kit · Kit Tern'):
            self.assertIn(words, text)
        from workbench import system_settings_qt as ss
        self.assertIn(('system:door', 'System changes'), [(n['id'], n['label']) for n in ss.nodes()])

    def test_her_new_lines_pass_the_voice_sweep(self):
        from workbench import mind_words
        self.assertEqual([p for p in mind_words.check() if p[0] == 'kas_voice'], [])


if __name__ == '__main__':
    unittest.main()
