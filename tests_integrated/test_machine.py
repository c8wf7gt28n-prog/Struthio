"""Machine observations are read-only, bounded and honest; ledger.machine is a bounded read with a fixed schema, a recorded
registry row (docs/GRAPHITE_0.1_REGISTRY.json) and its own handler route."""
import json,os,platform,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workbench import machine_overview as machine,doctor,stacy_foundation,capability_catalog,ledger_control
from workbench.engineering_cli import schemas
from workbench.engineering_kernel import Kernel,operator,Principal,CAPABILITIES,TOOLS
from workbench.session import Session

PROGRAM=Path(__file__).resolve().parents[1]
platform.processor()  # Python answers this once through uname; from here on no process may start in these tests
CPUINFO='''processor\t: 0
vendor_id\t: GenuineIntel
model\t\t: 142
model name\t: Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz
physical id\t: 0
siblings\t: 2
cpu cores\t: 2

processor\t: 1
vendor_id\t: GenuineIntel
model\t\t: 142
model name\t: Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz
physical id\t: 0
siblings\t: 2
cpu cores\t: 2
'''
MEMINFO='MemTotal:       16000000 kB\nMemFree:         4000000 kB\nMemAvailable:    8000000 kB\nSwapTotal:       2000000 kB\nSwapFree:        1500000 kB\n'
MOUNTS='''proc /proc proc rw,relatime 0 0
sysfs /sys sysfs rw 0 0
/dev/sda2 / ext4 rw,relatime 0 0
/dev/sda1 /boot/efi vfat rw,relatime 0 0
tmpfs /run tmpfs rw,nosuid 0 0
/dev/loop3 /snap/core/1 squashfs ro,nodev 0 0
/dev/sdb1 /media/owner/USB\\040STICK vfat rw,nosuid 0 0
'''
def clock():return 1700000000.0


def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)


def fake_host(base):
    """A /proc and /sys shaped tree with the attributes the readers use; nothing in it is a device."""
    proc=base/'proc';sys_root=base/'sys'
    write(proc/'cpuinfo',CPUINFO);write(proc/'loadavg','0.50 0.25 0.10 2/345 6789\n');write(proc/'meminfo',MEMINFO);write(proc/'mounts',MOUNTS)
    write(proc/'sys/kernel/osrelease','6.1.0-fixture\n');write(proc/'sys/kernel/hostname','fixture\n')
    write(proc/'bus/input/devices',''.join('I: Bus=0003 Vendor=046d\nN: Name="Device %d"\nH: Handlers=kbd event%d\n\n'%(n,n) for n in range(100)))
    for name,size,rotational,model,vendor,removable in (('sda',1000215216,0,'Samsung SSD 980','ATA',0),('sdb',62333952,1,'USB Stick',None,1),('nvme0n1',2000409264,0,'KXG60ZNV1T02',None,0)):
        folder=sys_root/'block'/name;write(folder/'size',str(size)+'\n');write(folder/'queue/rotational',str(rotational)+'\n')
        write(folder/'removable',str(removable)+'\n');write(folder/'ro','0\n');write(folder/'device/model',model+'\n')
        if vendor:write(folder/'device/vendor',vendor+'\n')
    for part,size in (('sda1','1048576'),('sda2','999166640'),('sdb1','62331904')):write(sys_root/'block'/part[:3]/part/'size',size+'\n')
    for name in ('loop0','loop1','ram0','zram0'):write(sys_root/'block'/name/'size','8192\n')
    net=sys_root/'class/net'
    write(net/'lo/operstate','unknown\n');write(net/'lo/type','772\n');write(net/'lo/mtu','65536\n')
    write(net/'eth0/operstate','up\n');write(net/'eth0/carrier','1\n');write(net/'eth0/type','1\n');(net/'eth0/device').mkdir(parents=True)
    write(net/'wlan0/operstate','down\n');write(net/'wlan0/type','1\n');(net/'wlan0/wireless').mkdir(parents=True);(net/'wlan0/device').mkdir(parents=True)
    for n in range(70):write(net/('xveth%d'%n)/'operstate','down\n');write(net/('xveth%d'%n)/'type','1\n')  # sort after wlan0 so the bound cuts the virtual tail
    usb=sys_root/'bus/usb/devices'
    for key,value in (('idVendor','046d'),('idProduct','c52b'),('product','USB Receiver'),('manufacturer','Logitech'),('busnum','1'),('devnum','3'),('speed','12'),('bDeviceClass','00')):
        write(usb/'1-1'/key,value+'\n')
    write(usb/'1-1:1.0/bInterfaceClass','03\n')
    for key,value in (('idVendor','1d6b'),('idProduct','0002'),('product','xHCI Host Controller'),('manufacturer','Linux xhci_hcd'),('busnum','1'),('devnum','1'),('speed','480'),('bDeviceClass','09')):
        write(usb/'usb1'/key,value+'\n')
    drm=sys_root/'class/drm'
    write(drm/'card1-eDP-1/status','connected\n');write(drm/'card1-eDP-1/modes','1920x1200\n1600x1000\n');write(drm/'card1-eDP-1/enabled','enabled\n')
    write(drm/'card1-HDMI-A-1/status','disconnected\n');write(drm/'card1/dev','226:1\n')
    write(sys_root/'fs/cgroup/memory.max','4294967296\n');write(sys_root/'fs/cgroup/memory.current','1000\n')
    return proc,sys_root


class ReaderTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ledger-machine-');self.addCleanup(temporary.cleanup);self.base=Path(temporary.name)
        guard=patch.object(subprocess,'Popen',side_effect=AssertionError('No process may start while the machine is observed'));guard.start();self.addCleanup(guard.stop)

    def section(self,value,ident):return next(s for s in value['sections'] if s['id']==ident)

    def test_missing_proc_and_sys_are_honest_unavailable_states(self):
        empty=self.base/'empty';empty.mkdir()
        value=machine.observe(program=self.base,workspace=self.base,proc=str(empty/'proc'),sys_root=str(empty/'sys'),clock=clock)
        json.dumps(value)  # serialisable, bounded
        for ident in ('memory','connections','devices'):
            section=self.section(value,ident);self.assertEqual(section['state'],'UNAVAILABLE',ident);self.assertEqual(section['items'],[])
            self.assertTrue(any('not present' in note for note in section['notes']),section['notes'])
        processor=self.section(value,'processor')
        self.assertEqual([r['id'] for r in processor['items'] if r['state']=='OBSERVED'],['processor:online'])
        self.assertTrue(any('cpuinfo' in note for note in processor['notes']))
        storage=self.section(value,'storage');self.assertTrue(any('block' in note for note in storage['notes']) and any('mounts' in note for note in storage['notes']))
        self.assertEqual([r['kind'] for r in storage['items']],['ledger_path','ledger_path'])
        self.assertIsNone(value['host']['kernel']);self.assertEqual((value['model_calls'],value['network_calls'],value['native_invocations'],value['subprocesses']),(0,0,0,0))
        self.assertEqual(value['basis'],'CURRENT_LEDGER_HOST_NOT_OWNER_HOST_QUALIFICATION')
        self.assertEqual(machine.network_up(str(empty/'sys')),(None,[]))

    def test_fixture_host_is_read_from_proc_and_sys_with_bounds_and_natural_order(self):
        proc,sys_root=fake_host(self.base)
        value=machine.observe(program=self.base/'program',workspace=self.base/'work',proc=str(proc),sys_root=str(sys_root),clock=clock)
        self.assertEqual(len(json.dumps(value))<512*1024,True)
        processor=self.section(value,'processor');model=next(r for r in processor['items'] if r['id']=='processor:model')
        self.assertEqual(model['values']['model'],'Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz');self.assertEqual((model['values']['cores'],model['values']['threads']),(2,2))
        self.assertEqual(model['source'],str(proc/'cpuinfo'));self.assertEqual(model['sampled_at'],clock())
        load=next(r for r in processor['items'] if r['id']=='processor:load');self.assertEqual(load['values']['runnable'],2)
        memory=self.section(value,'memory');ram=next(r for r in memory['items'] if r['id']=='memory:ram')
        self.assertEqual((ram['values']['total'],ram['values']['used'],ram['values']['percent']),(16000000*1024,8000000*1024,50))
        self.assertEqual(next(r for r in memory['items'] if r['id']=='memory:swap')['values']['used'],500000*1024)
        self.assertEqual(next(r for r in memory['items'] if r['id']=='memory:ceiling')['values']['limit'],4294967296)
        storage=self.section(value,'storage');devices=[r for r in storage['items'] if r['kind']=='block_device']
        self.assertEqual([r['id'] for r in devices],['storage:device:nvme0n1','storage:device:sda','storage:device:sdb'])  # loop, ram and zram excluded; natural order
        sda=devices[1];self.assertEqual(sda['values']['partitions'],['sda1','sda2']);self.assertEqual(sda['values']['size'],1000215216*512)
        self.assertIn('Samsung SSD 980',sda['label']);self.assertIn('solid state',sda['label']);self.assertIn('removable',devices[2]['label'])
        mounts={r['values']['mountpoint']:r for r in storage['items'] if r['kind']=='mount'}
        self.assertEqual(sorted(mounts),['/','/boot/efi','/media/owner/USB STICK'])  # plumbing and loop mounts excluded, octal escapes decoded
        self.assertIn('holds the program folder and the workspace',mounts['/']['label'])
        self.assertTrue(all(r['values']['free'] is not None or r['state']=='PARTIAL' for r in mounts.values()))
        self.assertEqual([r['kind'] for r in storage['items'][:2]],['ledger_path','ledger_path'])
        connections=self.section(value,'connections');self.assertEqual(connections['state'],'PARTIAL');self.assertEqual(connections['count'],machine.BOUND)
        labels=[r['label'] for r in connections['items']];self.assertEqual(labels,sorted(labels,key=machine.natural))
        self.assertLess(labels.index('xveth9 · virtual · down'),labels.index('xveth10 · virtual · down'))
        eth=next(r for r in connections['items'] if r['id']=='connections:eth0');self.assertEqual((eth['values']['kind'],eth['values']['carrier'],eth['values']['addresses']),('ethernet',1,'NOT_READ'))
        wlan=next(r for r in connections['items'] if r['id']=='connections:wlan0');self.assertEqual((wlan['values']['kind'],wlan['values']['carrier']),('wireless',None))
        self.assertEqual(machine.network_up(str(sys_root)),(True,['eth0']))
        devices=self.section(value,'devices');kinds={r['kind']:[] for r in devices['items']}
        for row in devices['items']:kinds[row['kind']].append(row)
        self.assertEqual([r['label'] for r in kinds['usb']],['Linux xhci_hcd · xHCI Host Controller · hub · 480 Mb/s','Logitech · USB Receiver · 12 Mb/s'])  # natural order of the label
        self.assertEqual(len(kinds['input']),machine.BOUND);self.assertTrue(devices['partial']);self.assertEqual(kinds['input'][0]['values']['handlers'],['kbd','event0'])
        self.assertEqual([r['label'] for r in kinds['display']],['eDP-1 · connected · 1920x1200 · enabled','HDMI-A-1 · disconnected'])
        self.assertEqual(value['host'],{'kernel':'6.1.0-fixture','hostname':'fixture','source':str(proc/'sys/kernel')})
        self.assertTrue(all('source' in r and 'sampled_at' in r and r['state'] in ('OBSERVED','PARTIAL','UNAVAILABLE') for s in value['sections'] for r in s['items']))
        self.assertEqual(machine.observe(section='memory',proc=str(proc),sys_root=str(sys_root),clock=clock)['sections'][0]['id'],'memory')
        with self.assertRaises(ValueError):machine.observe(section='weather',proc=str(proc),sys_root=str(sys_root))

    def test_tools_section_reuses_the_catalogue_families_without_running_anything(self):
        families=set(capability_catalog.NATIVE)|{'brain','python-wasi'}
        with patch.object(machine.shutil,'which',return_value=None),patch.object(capability_catalog.shutil,'which',return_value=None):
            section=machine.tools(PROGRAM,clock)
        rows={r['values']['family']:r for r in section['items']};self.assertEqual(set(rows),families)
        for family,command in capability_catalog.NATIVE.items():
            self.assertEqual((rows[family]['values']['state'],rows[family]['values']['command'],rows[family]['values']['path']),('MISSING',command,None))
            self.assertTrue(rows[family]['label'].endswith(' · not found on PATH'),rows[family]['label'])
        self.assertTrue(all(r['values']['measured']=='NOTHING_RUN' and r['values']['version'] in (None,r['values']['version']) for r in section['items']))
        labels=[r['label'] for r in section['items']];self.assertEqual(labels,sorted(labels,key=machine.natural))
        with patch.object(machine.shutil,'which',return_value='/usr/bin/tool'),patch.object(capability_catalog.shutil,'which',return_value='/usr/bin/tool'):
            detected={r['values']['family']:r for r in machine.tools(PROGRAM,clock)['items']}
        self.assertEqual((detected['cad']['values']['state'],detected['cad']['values']['path']),('DETECTED','/usr/bin/tool'));self.assertTrue(detected['cad']['label'].endswith(' · on PATH'))
        self.assertIn(detected['brain']['values']['state'],('DETECTED','MISSING','INVALID','INCOMPATIBLE'))  # the pinned archive is verified by hash, never extracted or run

    def test_short_model_and_sizes_are_words_not_guesses(self):
        self.assertEqual(machine.short_model('AMD Ryzen 7 PRO 5850U with Radeon Graphics'),'AMD Ryzen 7 PRO 5850U')
        self.assertEqual(machine.short_model('Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz'),'Intel Core i7-8650U')
        self.assertEqual(machine.short_model('AMD Ryzen 9 7950X 16-Core Processor'),'AMD Ryzen 9 7950X')
        self.assertEqual(machine.short_model(None),'')
        self.assertEqual((machine.human(None),machine.human(512),machine.human(64*1024**3)),('not observed','512 B','64.0 GiB'))
        space=machine.space(self.base);self.assertEqual(set(space),{'total','free','source'});self.assertIsNone(machine.space(self.base/'missing'))


class OperationTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='ledger-machine-op-');self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.root=self.base/'workspace';self.root.mkdir()
        env=patch.dict(os.environ,{'ARC1_WORKBENCH_CONFIG_HOME':str(self.base/'profile'),'ARC_LEDGER_CONCERN':str(self.base/'Concern')})
        env.start();self.addCleanup(env.stop);self.kernel=Kernel(self.root);self.owner=operator('owner')
        self.session=Session(self.base/'profile/session.json',self.root);self.session.save();ledger_control.bind(self.kernel,self.session)

    def test_ledger_machine_is_a_bounded_read_for_owner_and_read_only_callers(self):
        with self.kernel.db() as db:jobs=db.execute('SELECT count(*) FROM jobs').fetchone()[0]
        with patch.object(subprocess,'Popen',side_effect=AssertionError('No process launch')):
            value=self.kernel.dispatch('ledger.machine',{},self.owner);self.assertTrue(value['ok'],value);result=value['result']
            reader=self.kernel.dispatch('ledger.machine',{'section':'storage'},Principal('Slate:reader',frozenset({'read'})))
        self.assertEqual([s['id'] for s in result['sections']],list(machine.SECTIONS));self.assertEqual(result['schema'],'ledger.machine/1')
        self.assertEqual(result['workspace'],str(self.root));self.assertTrue(result['program_folder'])
        self.assertTrue(reader['ok'],reader);self.assertEqual([s['id'] for s in reader['result']['sections']],['storage'])
        self.assertLess(len(json.dumps(result)),512*1024)
        self.assertFalse(self.kernel.dispatch('ledger.machine',{'section':'weather'},self.owner)['ok'])
        self.assertFalse(self.kernel.dispatch('ledger.machine',{'verbose':True},self.owner)['ok'])
        with self.kernel.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0],jobs)
        self.assertEqual(CAPABILITIES['ledger.machine'],'read');self.assertNotIn('ledger.machine',TOOLS)
        self.assertEqual(schemas()['ledger.machine'],{'type':'object','properties':{'section':{'type':'string','enum':list(machine.SECTIONS)}},'required':[],'additionalProperties':False})

    def test_ledger_machine_follows_the_recorded_registry_and_has_its_own_handler_route(self):
        # The whole registry is compared with the record by tools/check_release.py; this module checks its own operation's row.
        from tools import record_registry
        record=record_registry.read(PROGRAM);self.assertIsNotNone(record,record_registry.RECORD)
        live=record_registry.snapshot()['operations']['ledger.machine']
        self.assertEqual(record['operations']['ledger.machine'],live);self.assertEqual(live['scope'],'read');self.assertEqual(CAPABILITIES['ledger.machine'],'read')
        self.assertEqual(record['adapters']['operations']['ledger.machine'],'workbench/machine_overview.py#dispatch')
        self.assertEqual(stacy_foundation.handler_map()['ledger.machine'],{'path':'workbench/machine_overview.py','symbol':'dispatch','basis':'DECLARED_FIELDS_ROUTE'})


if __name__=='__main__':unittest.main()
