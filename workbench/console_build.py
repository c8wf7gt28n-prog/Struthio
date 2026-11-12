"""Build the current C virtual-console integration; no target tool is invoked."""
import contextlib, io, shutil, subprocess, sys, time
from pathlib import Path
from . import record_io as record,arcos_tools,federation_rtl
from sdk.cli.arc1cli import console_media,boot_image,fat_image,native_sdk

FW='hardware/compact-arc1/R10_WORK/'
F=FW+'firmware/'
C_SOURCES=[
 'software/arcos/src/host.c','software/arcos/src/launcher.c','software/arcos/src/controller.c',
 'software/arcos/bsp/virtual_console/virtual_boot.c',
 'software/arcos/bsp/virtual_console/federation_consumer.c','software/arcos/bsp/virtual_console/federation_transaction.c','software/arcos/bsp/virtual_console/usb_device_model.c',
 'software/boot/first_stage/ddr/ddr_model.c','software/boot/first_stage/reference/u-boot/dram_sun20i_d1.c','software/boot/first_stage/ddr/dram_candidate.c',
 'software/boot/first_stage/clock/f133_clock.c','software/boot/f133_app_load.c',
 *['sdk/runtime/boot/'+n+'.c' for n in ('io_budget','bounded_io','boot_epoch','load_bounds','usb_control','boot_info','federation')],
 *[F+'f133_bootloader/src/'+n+'.c' for n in ('r10_boot','r10_fpga45','spi_nor','ecp5_cfg','r10_boot_info')],
 *[F+'host_support/src/'+n+'.c' for n in ('crc32','flash_layout','accel_job','fpga_link')],
 F+'host_support/compute/arc1_transform.c',F+'host_support/tests/nor_mock.c',F+'host_support/tests/ecp5_mock.c',
 FW+'f133/graphics_link/src/gfx_link.c',FW+'d213/fpga45_loader/src/d213_fpga45.c',
 F+'d213_flashless_proof/loader/r10_d213_start.c',F+'usb_hub/r10_hub.c',F+'usb_media/r10_usb_media.c',F+'usb_media/r10_fat_port.c',F+'usb_media/fatfs/ff.c']
INCLUDES=['software/arcos/include','software/arcos/bsp/virtual_console','sdk/include','software/boot','software/boot/first_stage','software/boot/first_stage/ddr/include','software/boot/first_stage/reference/u-boot','software/boot/first_stage/clock/include',F+'f133_bootloader/include',F+'host_support/include',F+'host_support/tests',F+'host_support/compute',FW+'f133/graphics_link/include',FW+'d213/fpga45_loader/include',F+'d213_flashless_proof/loader',F+'usb_hub',F+'usb_media',F+'usb_media/fatfs']
OUT='build/virtual_console'


def sources(root):
    root=Path(root);names=set(arcos_tools.sources(root))
    for folder in ('software/boot','sdk/runtime/boot',F+'f133_bootloader',F+'host_support',FW+'f133/graphics_link',FW+'d213/fpga45_loader',F+'d213_flashless_proof/loader',F+'usb_hub',F+'usb_media'):
        for p in (root/folder).rglob('*'):
            if p.is_file() and not any(x in p.relative_to(root).parts for x in ('build','__pycache__')) and (p.suffix in ('.c','.h','.inc','.ld','.json') or p.name=='Makefile'):names.add(p.relative_to(root).as_posix())
    names.update(federation_rtl.SOURCES)
    names.add('workbench/native_projects.py')
    names.update(['workbench/firmware_tools.py','sdk/cli/arc1cli/main.py','sdk/cli/arc1cli/fat_image.py','sdk/cli/arc1cli/native_sdk.py','sdk/templates/native_game/game.c','sdk/templates/native_game/native.json','sdk/templates/native_game/README.md','examples/first_arc_game/game.c','examples/first_arc_game/native.json','examples/first_arc_game/README.md'])
    names.update([FW+'cad/NETLIST.xml',FW+'board/r10_board_plan.json','project/console/profile.json','sdk/cli/arc1cli/console_media.py','sdk/cli/arc1cli/target_plan.py','sdk/cli/arc1cli/boot_image.py','sdk/cli/arc1cli/elf_image.py','workbench/console_build.py','workbench/console_runtime.py','workbench/console_services.py',FW+'memory/R10_nor_partition.csv'])
    return {n:record.sha(record.project_path(root,n)) for n in sorted(names)}


def revision(inputs):return record.digest(inputs)


def current(root,verify=True):
    root=Path(root);r=record.load(root,OUT+'/build.json')
    if r.get('status')!='PASS' or r.get('input_hashes')!=sources(root):raise ValueError('STALE_CONSOLE_BUILD: build the current source')
    if verify:
        for name,sha in r['artifacts'].items():
            if record.sha(record.project_path(root,name))!=sha:raise ValueError('CONSOLE_ARTIFACT_CHANGED: '+name)
    return r


def build(root):
    root=Path(root).resolve();out=record.project_path(root,OUT+'/build.json',False).parent;out.mkdir(parents=True,exist_ok=True)
    if sys.platform not in ('linux','darwin'):raise ValueError('POSIX_HOST_REQUIRED: Linux or macOS C backend; no native Windows claim')
    cc=shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
    if not cc:raise ValueError('C11_COMPILER_REQUIRED')
    initial=sources(root);report={'schema':'arc.virtual-console-build/1','status':'BUILDING','class':'HOST_SIM','physical_hardware':False,'board_boot_qualified':False,'target':arcos_tools.target(),'created':time.time(),'input_hashes':initial,'revision':revision(initial),'commands':[]}
    def command(argv):
        argv=list(map(str,argv));p=subprocess.run(argv,cwd=root,text=True,capture_output=True,timeout=60)
        report['commands'].append({'argv':argv,'exit':p.returncode,'stdout':p.stdout[-8000:],'stderr':p.stderr[-8000:]})
        if p.returncode:raise ValueError('CONSOLE_BUILD_FAILED: '+p.stderr[-4000:])
        return p.stdout
    try:
        with contextlib.redirect_stdout(io.StringIO()):code=arcos_tools.run(root,'build')
        if code:raise ValueError('ARCOS_BUILD_FAILED: inspect build/arcos/build.json')
        report['rtl']=federation_rtl.build(root)
        report['arcos_build']='build/arcos/build.json';report['compiler']=command([cc,'--version']).splitlines()[0]
        flags=[cc,'-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-fno-strict-aliasing','-DARC1_UNIFIED_MODEL','-DARC_VIRTUAL_CONSOLE',*['-I'+str(root/n) for n in INCLUDES]]
        objects=[]
        for i,name in enumerate(C_SOURCES):
            obj=out/('part_%02d.o'%i);extra=['-Dsunxi_dram_init=bounded_sunxi_dram_init'] if name.endswith('/dram_candidate.c') else []
            command([*flags,*extra,'-c',root/name,'-o',obj]);objects.append(obj)
        exe=out/'arc_console_host';command([cc,*objects,'-o',exe,*([] if sys.platform=='darwin' else ['-ldl'])])
        nor=out/'resident.nor';command([exe,'--make-nor',nor,report['revision']])
        card=record.load(root,'build/arcos/struthio.gamecard.json');artifact=(root/'build/arcos'/card['artifact']).read_bytes()
        normal=console_media.pack(card,artifact,report['revision']);(out/'thumb-drive.arcusb').write_bytes(normal)
        (out/'corrupt-drive.arcusb').write_bytes(console_media.pack(card,artifact[:-1]+bytes([artifact[-1]^1]),report['revision']))
        (out/'incompatible-drive.arcusb').write_bytes(console_media.pack({**card,'abi':99},artifact,report['revision']))
        sample=native_sdk.build(root,root/'examples/first_arc_game',report['revision']);report['sample_gamecard']=sample['card']
        media={
            'thumb-drive.fat32.img':normal,
            'corrupt-drive.fat32.img':(out/'corrupt-drive.arcusb').read_bytes(),
            'incompatible-drive.fat32.img':(out/'incompatible-drive.arcusb').read_bytes(),
            'sample-drive.fat32.img':Path(sample['package']).read_bytes()}
        fat_paths=[]
        for name,data in media.items():
            path=out/name;path.write_bytes(fat_image.pack(data));fat_paths.append(path)
        bad=bytearray((out/'thumb-drive.fat32.img').read_bytes());bad[36:40]=(0x200000).to_bytes(4,'little')
        (out/'bad-fat.fat32.img').write_bytes(bad);fat_paths.append(out/'bad-fat.fat32.img')
        # Format fixture uses the exact two instructions in the existing virtual app_probe.
        (out/'virtual-probe.egon').write_bytes(boot_image.pack(bytes.fromhex('1345550567800000'),max_image_bytes=4096))
        names=[exe,nor,out/'thumb-drive.arcusb',out/'corrupt-drive.arcusb',out/'incompatible-drive.arcusb',out/'virtual-probe.egon',root/federation_rtl.ARTIFACT,*fat_paths]
        report['artifacts']={p.relative_to(root).as_posix():record.sha(p) for p in names};report['gamecard']=card
        if sources(root)!=initial:raise ValueError('SOURCE_CHANGED_DURING_BUILD')
        report['status']='PASS'
    except (OSError,ValueError,subprocess.SubprocessError) as exc:report.update(status='FAIL',error=str(exc))
    record.write_json(out/'build.json',report)
    if report['status']!='PASS':raise ValueError(report.get('error','CONSOLE_BUILD_FAILED'))
    return report
