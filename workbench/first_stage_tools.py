"""Cross-build and execute RV64 loader experiments on QEMU virt, never hardware."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from .boot_tools import output_file
from .console_simulation import safe_file, fingerprint
from . import locations

FILES = (
    'workbench/first_stage_tools.py', 'workbench/boot_tools.py', 'workbench/console_simulation.py',
    'workbench/engineering_kernel.py', 'sdk/cli/arc1cli/elf_image.py',
    'software/boot/f133_app_load.c', 'software/boot/f133_app_load.h', 'software/boot/Makefile',
    'sdk/runtime/boot/load_bounds.c', 'sdk/include/arc1/load_bounds.h',
    'software/boot/tests/test_f133_app_load.c', 'tests/test_first_stage.py', 'tests/test_clock_start.py',
    'sdk/include/arc1/bounded_io.h', 'sdk/runtime/boot/bounded_io.c',
    'sdk/include/arc1/io_budget.h','sdk/runtime/boot/io_budget.c','tests/test_ddr_start.py',
    'sdk/include/arc1/boot_epoch.h','sdk/runtime/boot/boot_epoch.c','tests/test_unified_boot.py',
    'sdk/include/arc1/boot_info.h','sdk/runtime/boot/boot_info.c',
    'sdk/include/arc1/diag_service.h','sdk/runtime/boot/diag_service.c',
    'sdk/include/arc1/bounded_arena.h','sdk/runtime/boot/bounded_arena.c','tests/test_arcos_diagnostic.py',
)
FW = 'hardware/compact-arc1/R10_WORK/firmware'
SOURCES = (
    'software/boot/f133_app_load.c', 'sdk/runtime/boot/load_bounds.c',
    FW+'/f133_bootloader/src/r10_boot.c', FW+'/f133_bootloader/src/spi_nor.c',
    FW+'/f133_bootloader/src/ecp5_cfg.c',
    FW+'/host_support/src/crc32.c', FW+'/host_support/src/flash_layout.c',
    FW+'/host_support/tests/nor_mock.c',
    'software/boot/first_stage/runtime.c', 'software/boot/first_stage/start.S',
    'sdk/runtime/boot/bounded_io.c','software/boot/first_stage/clock/f133_clock.c',
    'software/boot/first_stage/clock/clock_model.c',
    'software/boot/first_stage/reference/xboot/sys-clock.c',
    'sdk/runtime/boot/io_budget.c','sdk/runtime/boot/boot_epoch.c','software/boot/first_stage/ddr/ddr_model.c',
    'software/boot/first_stage/reference/u-boot/dram_sun20i_d1.c',
    'software/boot/first_stage/ddr/dram_candidate.c',
    'software/boot/first_stage/diagnostic_model.c',
    'sdk/runtime/boot/boot_info.c','sdk/runtime/boot/diag_service.c','sdk/runtime/boot/bounded_arena.c',
    'software/arcos/diagnostic/model_services.c','software/arcos/diagnostic/diagnostic.c',
)
REGIONS = ((0x80000000, 0x200000), (0x82000000, 0x4000000)) # virtual ONLY
SCENARIOS = (
    ('load-and-call',0,0,'COPIED_PAYLOAD_EXECUTED_OK'),
    ('readback-corruption',1,0,'LOAD_REJECTED_NO_JUMP_OK'),
    ('memory-not-ready',2,0,'LOAD_REJECTED_NO_JUMP_OK'),
    ('illegal-instruction',3,70,'mcause=0x0000000000000002'),
    ('unmapped-load',4,70,'mcause=0x0000000000000005'),
    ('missing-f133-peripheral',5,3,'F133_PERIPHERAL_MODEL_UNAVAILABLE'),
    ('existing-loader-contract',6,0,'EXISTING_229_CONTRACT_CHECKS_RV64_OK'),
    ('clock-load-and-call',7,0,'COPIED_PAYLOAD_EXECUTED_OK'),
    ('upstream-write-argument-defect',8,80,'UNMODELED_REGISTER_WRITE'),
    ('cpu-pll-never-locks',9,0,'CLOCK_FAILURE_BOUNDED_NO_HANDOFF'),
    ('peripheral-pll-never-locks',10,0,'CLOCK_FAILURE_BOUNDED_NO_HANDOFF'),
    ('clock-io-failure',11,0,'CLOCK_FAILURE_BOUNDED_NO_HANDOFF'),
    ('clock-time-frozen',12,0,'CLOCK_FAILURE_BOUNDED_NO_HANDOFF'),
    ('clock-recovery-failure',13,0,'CLOCK_RECOVERY_FAILURE_REPORTED'),
    ('clock-register-model-missing',14,0,'CLOCK_RECOVERY_FAILURE_REPORTED'),
    ('clock-ready-ddr-absent',15,3,'DDR_MODEL_UNAVAILABLE_NO_HANDOFF'),
    ('peripheral-preenabled-unlocked',16,0,'CLOCK_SEQUENCE_MODEL_OK'),
    ('ddr-upstream-source',17,0,'DDR_SOURCE_AND_MEMORY_CONTRACT_OK'),
    ('ddr-upstream-unbounded-wait',18,84,'DDR_REFERENCE_BUDGET_STOP'),
    ('ddr-bounded-source',19,0,'DDR_SOURCE_AND_MEMORY_CONTRACT_OK'),
    ('ddr-pll-stall',20,0,'DDR_FAILURE_RETURNED_MASTERS_DISABLED'),
    ('ddr-training-stall',21,0,'DDR_FAILURE_RETURNED_MASTERS_DISABLED'),
    ('ddr-normal-status-stall',22,0,'DDR_FAILURE_RETURNED_MASTERS_DISABLED'),
    ('ddr-zq-error',23,0,'DDR_FAILURE_RETURNED_MASTERS_DISABLED'),
    ('ddr-memory-mismatch',24,0,'DDR_FAILURE_RETURNED_MASTERS_DISABLED'),
    ('ddr-upstream-error-cleanup',25,0,'UPSTREAM_FAILURE_LEFT_MASTERS_ENABLED'),
    ('ddr-register-unmodeled',26,85,'DDR_REGISTER_OR_MEMORY_UNMODELED'),
    ('ddr-time-frozen',27,0,'DDR_FAILURE_RETURNED_MASTERS_DISABLED'),
    ('ddr-memory-unmodeled',28,85,'DDR_REGISTER_OR_MEMORY_UNMODELED'),
    ('clock-ddr-load-and-call',29,0,'COPIED_PAYLOAD_EXECUTED_OK'),
    ('ddr-silicon-qualification-absent',30,3,'F133_DDR_SILICON_QUALIFICATION_MISSING'),
    ('ddr-wrong-timing',31,86,'DDR_ORDER_OR_TIMING_REJECTED'),
    ('ddr-masters-premature',32,86,'DDR_ORDER_OR_TIMING_REJECTED'),
    ('unified-load-and-call',33,0,'UNIFIED_DDR_TESTED_STORAGE_CONTAINS_PAYLOAD_OK'),
    ('unified-no-clock',34,0,'UNIFIED_DDR_BEFORE_CLOCK_REJECTED'),
    ('unified-cpu-pll-stall',35,0,'UNIFIED_CLOCK_FAILURE_NO_DDR_OR_LOAD'),
    ('unified-ddr-stall',36,0,'UNIFIED_DDR_FAILURE_NO_LOAD'),
    ('unified-clock-lost',37,0,'UNIFIED_LATE_FAULT_REJECTED_NO_JUMP_OK'),
    ('unified-training-lost',38,0,'UNIFIED_LATE_FAULT_REJECTED_NO_JUMP_OK'),
    ('unified-reset-during-load',39,0,'UNIFIED_LATE_FAULT_REJECTED_NO_JUMP_OK'),
    ('unified-payload-corrupt',40,0,'UNIFIED_LATE_FAULT_REJECTED_NO_JUMP_OK'),
    ('unified-stale-completion',41,0,'UNIFIED_STALE_COMPLETION_NO_JUMP_OK'),
    ('unified-ddr-clobbers-cpu',42,86,'DDR_ORDER_OR_TIMING_REJECTED'),
    ('unified-ddr-gate-lost',43,0,'UNIFIED_LATE_FAULT_REJECTED_NO_JUMP_OK'),
    ('unified-ddr-pll-lost',44,0,'UNIFIED_LATE_FAULT_REJECTED_NO_JUMP_OK'),
    ('diagnostic-boot', 45, 0, 'ARCOS_DIAGNOSTIC_LOADED_AND_RETURNED_OK'),
    ('diagnostic-old-abi', 46, 0, 'ARCOS_BAD_HANDOFF_REJECTED'),
    ('diagnostic-short-abi', 47, 0, 'ARCOS_BAD_HANDOFF_REJECTED'),
    ('diagnostic-reserved-overlap', 48, 0, 'ARCOS_BAD_HANDOFF_REJECTED'),
    ('diagnostic-stale-generation', 49, 0, 'ARCOS_BAD_HANDOFF_REJECTED'),
    ('diagnostic-ddr-absent', 50, 3, 'ARCOS_DDR_ABSENT_NO_ENTRY'),
    ('diagnostic-timer-timeout', 51, 0, 'ARCOS_SERVICE_FAILURE_BOUNDED_NO_GAME_LAUNCH'),
    ('diagnostic-controller-error', 52, 0, 'ARCOS_SERVICE_FAILURE_BOUNDED_NO_GAME_LAUNCH'),
    ('diagnostic-no-thumb-drive', 53, 0, 'ARCOS_SERVICE_FAILURE_BOUNDED_NO_GAME_LAUNCH'),
    ('diagnostic-unplug-drive', 54, 0, 'ARCOS_SERVICE_FAILURE_BOUNDED_NO_GAME_LAUNCH'),
    ('diagnostic-corrupt-game', 55, 0, 'ARCOS_CORRUPT_GAME_REJECTED'),
    ('diagnostic-interrupted-save', 56, 0, 'ARCOS_SERVICE_FAILURE_BOUNDED_NO_GAME_LAUNCH'),
    ('diagnostic-recovery-data-mode', 57, 0, 'ARCOS_SERVICE_FAILURE_BOUNDED_NO_GAME_LAUNCH'),
    ('diagnostic-d213-required', 58, 0, 'ARCOS_SERVICE_FAILURE_BOUNDED_NO_GAME_LAUNCH'),
    ('diagnostic-fpga-required', 59, 0, 'ARCOS_SERVICE_FAILURE_BOUNDED_NO_GAME_LAUNCH'),
    ('diagnostic-watchdog-restart', 60, 0, 'ARCOS_WATCHDOG_REBOOT_OK'),
    ('diagnostic-interrupted-import', 61, 0, 'ARCOS_SERVICE_FAILURE_BOUNDED_NO_GAME_LAUNCH'),
    ('diagnostic-map-overflow', 62, 0, 'ARCOS_BAD_HANDOFF_REJECTED'),
    ('diagnostic-abi-checksum', 63, 0, 'ARCOS_BAD_HANDOFF_REJECTED'),
    ('diagnostic-response-overrun', 64, 0, 'ARCOS_SERVICE_FAILURE_BOUNDED_NO_GAME_LAUNCH'),
    ('diagnostic-late-service-success', 65, 0, 'ARCOS_SERVICE_FAILURE_BOUNDED_NO_GAME_LAUNCH'),
    ('diagnostic-usb-route-loss', 66, 0, 'ARCOS_SERVICE_FAILURE_BOUNDED_NO_GAME_LAUNCH'),
    ('diagnostic-arena-exhaustion', 67, 0, 'ARCOS_ARENA_EXHAUSTION_BOUNDED'),
    ('diagnostic-service-abi', 68, 0, 'ARCOS_BAD_HANDOFF_REJECTED'),
    ('diagnostic-entry-outside-image', 69, 0, 'ARCOS_BAD_HANDOFF_REJECTED'),
    ('diagnostic-capability-spoof', 70, 0, 'ARCOS_BAD_HANDOFF_REJECTED'),
    ('diagnostic-bss-mutant', 71, 0, 'ARCOS_BSS_MUTANT_REJECTED'),

)


def input_hashes(root):
    root=Path(root).resolve()
    paths=set(FILES)|set(SOURCES)
    folders=('software/boot/first_stage','software/arcos/diagnostic',FW+'/f133_bootloader/include',FW+'/host_support/include',FW+'/host_support/tests')
    for name in folders:
        for path in (root/name).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                paths.add(path.relative_to(root).as_posix())
    # Additional headers used transitively by the actual boot source.
    for name in ('f133/graphics_link/include','d213/fpga45_loader/include'):
        for path in (root/'hardware/compact-arc1/R10_WORK'/name).glob('*.h'):
            paths.add(path.relative_to(root).as_posix())
    return {p:hashlib.sha256(safe_file(root,p).read_bytes()).hexdigest() for p in sorted(paths)}


def inspect(root):
    root=Path(root).resolve(); inputs=input_hashes(root)
    latest=None; name='build/first_stage/campaign.json'
    if (root/name).exists() or (root/name).is_symlink():
        report=json.loads(safe_file(root,name).read_text())
        latest={k:report.get(k) for k in ('experiment_status','model_cpu_execution','cases')}
        current=report.get('input_hashes')==inputs
        latest.update(source_current=current,evidence_eligible=current)
    return dict(schema='arc-ledger.first-stage/1',status='BLOCKED',evidence='STATIC_CHECK',
                input_hashes=inputs,source_fingerprint=fingerprint(inputs),latest=latest,
                model='QEMU virt / generic RV64; not F133 or D213',
                board_boot_qualified=False,target_image_qualified=False,
                f133_soc_execution=False,clock_register_contract_model=True,ddr_register_memory_contract_model=True,unified_boot_contract_model=True,arcos_diagnostic_model=True,ddr_model=False,usb_model=False,
                fabrication='HOLD',flashing='HOLD',estimated_first_boot_probability=None)


def campaign(root):
    root=Path(root).resolve(); started=time.time(); initial=inspect(root)
    out=output_file(root,'build/first_stage/campaign.json').parent
    if any(p.is_symlink() for p in out.rglob('*')):
        raise ValueError('First-stage build area must not contain symlinks')
    sys.path.insert(0,str(locations.program(root)/'sdk/cli'))
    from arc1cli.elf_image import inspect as inspect_elf
    report=dict(initial,created=started,evidence='HOST_SIM',execution_class='TARGET_EMU / generic RV64 model',
                model_cpu_execution=False,experiment_status='BLOCKED',commands=[],cases=[],artifacts={},tool_versions={})
    def run(label,argv,*,expected=0,token=None,timeout=60):
        argv=[str(x) for x in argv]
        def limits():
            import resource
            resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024*1024,8*1024*1024))
            resource.setrlimit(resource.RLIMIT_CPU,(timeout,timeout))
        try:
            p=subprocess.run(argv,cwd=root,text=True,capture_output=True,stdin=subprocess.DEVNULL,timeout=timeout,
                             env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','SOURCE_DATE_EPOCH':'0'},
                             preexec_fn=limits if os.name=='posix' and label.endswith('-execute') else None)
            code=p.returncode; stdout=p.stdout; stderr=p.stderr
        except subprocess.TimeoutExpired as exc:
            code=None; stdout=str(exc.stdout or '')[-20000:]; stderr='TIMEOUT '+str(exc)
        ok=code==expected and (token is None or token in stdout+stderr)
        report['commands'].append(dict(id=label,argv=argv,exit_status=code,expected_exit=expected,
                                        stdout=stdout[:40000],stderr=stderr[:20000]))
        if not ok: raise ValueError(label+' failed: '+stderr[-3000:]+' '+stdout[-1000:])
        return stdout+stderr
    def case(name,**kw): report['cases'].append(dict(id=name,status='PASS',**kw))
    try:
        names=('riscv64-unknown-elf-gcc','riscv64-unknown-elf-objcopy','riscv64-unknown-elf-objdump','qemu-system-riscv64')
        paths=[shutil.which(n) for n in names]
        if not all(paths):
            report['cases'].append(dict(id='toolchain',status='BLOCKED',reason='Missing '+', '.join(n for n,p in zip(names,paths) if not p)))
        else:
            cc,objcopy,objdump,qemu=paths
            lock=json.loads(safe_file(root,'software/boot/first_stage/toolchain.lock.json').read_text())
            for name,path,version in zip(('gcc','binutils','qemu'),(cc,objdump,qemu),(lock['gcc_version'],lock['binutils_version'],lock['qemu_version'])):
                text=run(name+'-version',[path,'--version'])
                if version not in text.splitlines()[0]: raise ValueError('Tool version differs from reviewed lock: '+name)
                report['tool_versions'][name]=text.splitlines()[0]
            flags=['-march='+lock['isa'],'-mabi='+lock['abi'],'-mcmodel=medany','-mno-relax','-msmall-data-limit=0',
                   '-O2','-g','-DARC1_MODEL_REFERENCE','-DARC1_UNIFIED_MODEL','-ffreestanding','-fno-builtin','-fno-strict-aliasing','-fno-stack-protector','-fno-pic',
                   '-ffunction-sections','-fdata-sections','-Wall','-Wextra','-Werror','-Wno-unused-function',
                   '-ffile-prefix-map='+str(root)+'=.']
            inc=['software/arcos/diagnostic','software/boot/first_stage/ddr/include','software/boot/first_stage/reference/u-boot','software/boot/first_stage/clock/include','software/boot/first_stage/clock','software/boot/first_stage/include','software/boot/first_stage','software/boot','sdk/include',
                 FW+'/f133_bootloader/include',FW+'/host_support/include',FW+'/host_support/tests',
                 'hardware/compact-arc1/R10_WORK/f133/graphics_link/include',
                 'hardware/compact-arc1/R10_WORK/d213/fpga45_loader/include']
            flags += [arg for d in inc for arg in ('-I',d)]
            report['compiler_flags']=flags
            # Python acceptance includes the existing ELF checks and new clock host contract.
            run('elf-inspector-tests',[sys.executable,'-m','unittest','-v','tests.test_first_stage','tests.test_clock_start','tests.test_ddr_start','tests.test_unified_boot','tests.test_arcos_diagnostic'])
            # Compile a separate freestanding application at the QEMU-only APP
            # coordinates. It is embedded into NOR and copied by the real loader.
            diag_sources=('software/arcos/diagnostic/entry.S','software/arcos/diagnostic/diagnostic.c',
                'software/arcos/diagnostic/memory.c','sdk/runtime/boot/boot_info.c',
                'sdk/runtime/boot/load_bounds.c','sdk/runtime/boot/diag_service.c','sdk/runtime/boot/bounded_arena.c')
            diag_objects=[]
            for i,source in enumerate(diag_sources):
                obj=out/('diagnostic_'+str(i)+'.o')
                run('diagnostic-compile-'+str(i),[cc,*flags,'-c',source,'-o',obj]);diag_objects.append(obj)
            diag_link=['-nostdlib','-nostartfiles','-Wl,--gc-sections,--build-id=none,--no-relax',
                       '-T','software/arcos/diagnostic/qemu_diagnostic.ld']
            for name,bad in (('arcos_diagnostic',False),('arcos_diagnostic_no_bss',True)):
                objs=list(diag_objects)
                if bad:
                    obj=out/'diagnostic_bad_entry.o'
                    run('diagnostic-bss-mutant-compile',[cc,*flags,'-DARC1_DIAG_NO_BSS','-c',diag_sources[0],'-o',obj]);objs[0]=obj
                elf=out/(name+'.elf');binary=out/(name+'.bin');mapfile=out/(name+'.map')
                args=[cc,*flags,*diag_link,'-Wl,-Map='+str(mapfile),*objs,'-o',elf]
                run(name+'-link',args);run(name+'-binary',[objcopy,'-O','binary',elf,binary])
                before=hashlib.sha256(elf.read_bytes()+binary.read_bytes()).hexdigest()
                run(name+'-relink',args);run(name+'-rebinary',[objcopy,'-O','binary',elf,binary])
                if before!=hashlib.sha256(elf.read_bytes()+binary.read_bytes()).hexdigest():raise ValueError('Diagnostic image not reproducible')
                if binary.stat().st_size>16384:raise ValueError('Diagnostic exceeds explicit virtual policy')
                plan=inspect_elf(elf.read_bytes(),allowed_regions=((0x80400000,16384),))
                (out/(name+'.elf.json')).write_text(json.dumps(plan,indent=2)+'\n')
                p=subprocess.run([objdump,'-d',str(elf)],capture_output=True,text=True,check=True,timeout=30)
                (out/(name+'.dis')).write_text(p.stdout)
            diag_embed=out/'diagnostic_embed.S'
            diag_embed.write_text('.section .rodata.diagnostic,"a",@progbits\n.global diag_payload_start,diag_payload_end,diag_bad_start,diag_bad_end\ndiag_payload_start:\n.incbin "'+(out/'arcos_diagnostic.bin').as_posix()+'"\ndiag_payload_end:\ndiag_bad_start:\n.incbin "'+(out/'arcos_diagnostic_no_bss.bin').as_posix()+'"\ndiag_bad_end:\n')
            payload=out/'app_probe.o'
            run('payload-compile',[cc,*flags,'-c','software/boot/first_stage/payload.S','-o',payload])
            run('payload-binary',[objcopy,'-O','binary','--only-section=.text',payload,out/'app_probe.bin'])
            embed=out/'payload_embed.S'
            embed.write_text('.section .rodata.probe,"a",@progbits\n.global payload_start,payload_end\npayload_start:\n.incbin "'+(out/'app_probe.bin').as_posix()+'"\npayload_end:\n')
            objects=[]
            for i,source in enumerate((*SOURCES,'software/boot/tests/test_f133_app_load.c',str(embed),str(diag_embed))):
                obj=out/('source_'+str(i)+'.o'); extra=['-Dmain=app_contract_main'] if source.endswith('test_f133_app_load.c') else []
                if source.endswith('ddr/dram_candidate.c'):
                    extra += ['-Dsunxi_dram_init=bounded_sunxi_dram_init']
                if source.endswith('dram_sun20i_d1.c') or source.endswith('ddr/dram_candidate.c'):
                    extra += ['-Wno-unused-parameter','-Wno-sign-compare']
                run('compile-'+str(i),[cc,*flags,*extra,'-c',source,'-o',obj]);objects.append(obj)
            linkflags=['-nostdlib','-nostartfiles','-Wl,--gc-sections,--build-id=none,--no-relax',
                       '-T','software/boot/first_stage/qemu_virt.ld']
            # Recompile/link twice at stable paths: ELF and BIN must match.
            for name,scenario,expected,token in SCENARIOS:
                obj=out/'scenario.o';elf=out/(name+'.elf');binary=out/(name+'.bin');mapfile=out/(name+'.map')
                run(name+'-compile',[cc,*flags,'-DSCENARIO='+str(scenario),'-c','software/boot/first_stage/model.c','-o',obj])
                argv=[cc,*flags,*linkflags,'-Wl,-Map='+str(mapfile),*objects,obj,'-o',elf]
                run(name+'-link',argv)
                run(name+'-binary',[objcopy,'-O','binary',elf,binary])
                before={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (elf,binary)}
                run(name+'-relink',argv)
                run(name+'-rebinary',[objcopy,'-O','binary',elf,binary])
                after={p.suffix:hashlib.sha256(p.read_bytes()).hexdigest() for p in (elf,binary)}
                if before!=after: raise ValueError('Non-reproducible link: '+name)
                plan=inspect_elf(elf.read_bytes(),allowed_regions=REGIONS)
                (out/(name+'.elf.json')).write_text(json.dumps(plan,indent=2)+'\n')
                dis=run(name+'-disassemble',[objdump,'-d',elf])
                # Command log is bounded; preserve the complete disassembly separately.
                p=subprocess.run([objdump,'-d',str(elf)],capture_output=True,text=True,check=True,timeout=30)
                (out/(name+'.dis')).write_text(p.stdout)
                trace=out/(name+'.trace')
                argv=[qemu,'-machine','virt','-cpu','rv64','-smp','1','-m','128M','-bios','none',
                      '-kernel',elf,'-display','none','-serial','none','-monitor','none','-nic','none',
                      '-semihosting-config','enable=on,target=native','-d','in_asm','-D',trace]
                text=run(name+'-execute',argv,expected=expected,token=token,timeout=90)
                if 'STARTUP_RV64_MODEL_OK' not in text: raise ValueError('Startup qualification absent')
                if scenario==4 and 'mtval=0x00000000dead0000' not in text: raise ValueError('Wrong fault address')
                if scenario>=45 and scenario!=50 and 'ARCOS_DIAGNOSTIC {' not in text:raise ValueError('Diagnostic machine-readable result absent')
                if scenario==6 and '229 checks 0 failed' not in text: raise ValueError('Contract suite did not complete')
                if scenario==8 and 'unmodeled_write=0x0000000000000000' not in text:
                    raise ValueError('Reference defect did not reach expected invalid address')
                case(name,execution='RV64 instructions on QEMU virt',expected_exit=expected,
                     expected_fault=scenario in (3,4,8,18,26,28,31,32,42),models=('loaded ARC-OS diagnostic plus logical services, shared startup bus/RAM' if scenario>=45 else 'shared clock/DDR bus, reset generation and 32 KiB DDR/loader QEMU storage' if scenario>=33 else 'legacy isolated contract fixtures')+'; no complete SoC or analog DDR model')
                report['model_cpu_execution']=True
            # These mutants must be caught by executed startup observations,
            # rather than relying on QEMU's already-zeroed RAM or a source scan.
            obj=out/'scenario.o'
            run('startup-negative-model',[cc,*flags,'-DSCENARIO=0','-c','software/boot/first_stage/model.c','-o',obj])
            startup=safe_file(root,'software/boot/first_stage/start.S').read_text()
            for name,text,expected in (
                ('bss-clear-disabled',startup.replace('2:  la t0, __bss_start','2:  j 4f\n    la t0, __bss_start'),75),
                ('stack-misaligned',startup.replace('    la sp, __stack_top','    la sp, __stack_top\n    addi sp, sp, -8'),74),
            ):
                path=out/(name+'.S');path.write_text(text);bad=out/(name+'.o');elf=out/(name+'.elf')
                run(name+'-compile',[cc,*flags,'-c',path,'-o',bad])
                # Find the start object by source identity, never a fragile fixed index.
                mutated=[bad if i==SOURCES.index('software/boot/first_stage/start.S') else source for i,source in enumerate(objects)]
                run(name+'-link',[cc,*flags,*linkflags,*mutated,obj,'-o',elf])
                run(name+'-execute',[qemu,'-machine','virt','-cpu','rv64','-smp','1','-m','128M','-bios','none',
                     '-kernel',elf,'-display','none','-serial','none','-monitor','none','-nic','none',
                     '-semihosting-config','enable=on,target=native'],expected=expected)
                case(name,execution='executed startup negative mutant',expected_exit=expected)
            # Deliberately too-small loader region must fail the linker.
            script=out/'overflow.ld'
            script.write_text(safe_file(root,'software/boot/first_stage/qemu_virt.ld').read_text().replace('LENGTH = 2M','LENGTH = 1K'))
            p=subprocess.run([cc,*flags,'-nostdlib','-Wl,--gc-sections,--build-id=none', '-T',str(script),*objects,obj,'-o',str(out/'must_not_link.elf')],cwd=root,capture_output=True,text=True,timeout=30)
            report['commands'].append(dict(id='link-overflow-negative',exit_status=p.returncode,stderr=p.stderr))
            if p.returncode==0 or 'overflow' not in p.stderr: raise ValueError('Overflow did not fail explicitly')
            case('link-overflow-rejected',execution='linker negative test')
            report['experiment_status']='PASS'
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        report['experiment_status']='FAIL';report['cases'].append(dict(id='campaign-error',status='FAIL',reason=str(exc)))
    if input_hashes(root)!=initial['input_hashes']:
        report['experiment_status']='FAIL';report['cases'].append(dict(id='source-drift',status='FAIL'))
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name!='campaign.json':
            report['artifacts'][p.name]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
    output_file(root,'build/first_stage/campaign.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('experiment_status','status','model_cpu_execution','board_boot_qualified','cases')},indent=2))
    return {'PASS':0,'BLOCKED':3,'FAIL':1}[report['experiment_status']]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    for action in ('campaign','inspect'):sub.add_parser(action).add_argument('--root',type=Path,default=Path.cwd())
    args=parser.parse_args()
    try:
        if args.action=='inspect':print(json.dumps(inspect(args.root),indent=2));return 0
        return campaign(args.root)
    except (ValueError,OSError) as exc:
        print(json.dumps(dict(status='FAIL',reason=str(exc),fabrication='HOLD',flashing='HOLD')));return 1
if __name__=='__main__':raise SystemExit(main())
