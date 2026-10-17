"""Freestanding RISC-V link-stage validation, *not* qualified bootable images."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'firmware'/'stage'
OUTPUT=ROOT/'firmware'/'build'/'stage'
TARGETS=('f133','d213')

def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build(target='all'):
    if target not in (*TARGETS,'all'):
        raise ValueError('target must be f133, d213, or all')
    clang=shutil.which('clang'); lld=shutil.which('ld.lld'); objcopy=shutil.which('llvm-objcopy')
    if not all((clang,lld,objcopy)):
        raise RuntimeError('Required LLVM tools unavailable: clang, ld.lld, llvm-objcopy (Windows install LLVM and add to PATH)')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    built=[]
    for board in (TARGETS if target=='all' else (target,)):
        out=OUTPUT/board
        out.mkdir(exist_ok=True)
        common=['--target=riscv64-unknown-elf','-march=rv64gc','-mabi=lp64d','-ffreestanding','-nostdlib','-fno-builtin','-ffunction-sections','-fdata-sections','-O1','-Wall','-Wextra','-Werror']
        sources=[STAGE/'entry.S',STAGE/(board+'_stage.c')]
        if board=='f133':sources.extend(ROOT/'firmware'/'f133'/'src'/file for file in ('lcd_status.c','boot_monitor.c','serlcd_i2c.c'))
        objects=[]
        for idx,src in enumerate(sources):
            obj=out/('entry.o' if idx==0 else ('main.o' if idx==1 else src.stem+'.o'))
            command=[clang,*common,'-I',str(ROOT/'firmware'/'include'),'-I',str(ROOT/'firmware'/'f133'/'include'),'-c',str(src),'-o',str(obj)]
            proc=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=40)
            if proc.returncode: raise RuntimeError(proc.stderr or proc.stdout)
            objects.append(obj)
        elf=out/(board+'.elf'); image=out/(board+'.bin'); linkmap=out/(board+'.map')
        cmd=[lld,'-m','elf64lriscv','-T',str(STAGE/'link_stage.ld'),'-Map='+str(linkmap),'--no-undefined','-o',str(elf),*(str(o) for o in objects)]
        proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=40)
        if proc.returncode: raise RuntimeError('link '+board+': '+(proc.stderr or proc.stdout))
        proc=subprocess.run([objcopy,'-O','binary',str(elf),str(image)],cwd=ROOT,capture_output=True,text=True,timeout=40)
        if proc.returncode: raise RuntimeError('objcopy '+board+': '+(proc.stderr or proc.stdout))
        if not image.stat().st_size or image.stat().st_size>0x20000:
            raise RuntimeError('invalid link-stage image size')
        if b'LINK_TEST_ONLY NOT_BOOTABLE' not in image.read_bytes():
            raise RuntimeError('non-bootable safety marker missing from image')
        built.append({'target':board,'elf':str(elf.relative_to(ROOT)).replace('\\','/'),
                      'binary':str(image.relative_to(ROOT)).replace('\\','/'),
                      'map':str(linkmap.relative_to(ROOT)).replace('\\','/'),
                      'binary_bytes':image.stat().st_size,'sha256':_sha(image),
                      'artifact_class':'LINK_TEST_ONLY','board_bootable':False,'flash_approved':False})
    manifest={'schema':'arc1.firmware.linkstage/1','toolchain':'clang + ld.lld + llvm-objcopy',
              'notice':'STAGED LINK TESTS, NOT REAL BOOT FIRMWARE',
              'link_base':'0x00020000 PROVISIONAL, NOT BOARD-VALIDATED',
              'images':built}
    dest=OUTPUT/'manifest.json'
    dest.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    import sys
    print(json.dumps(build(sys.argv[1] if len(sys.argv)>1 else 'all'),indent=2))
