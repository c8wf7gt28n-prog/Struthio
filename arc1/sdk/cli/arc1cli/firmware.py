"""Firmware workbench — edit sources, compile objects, run host tests. No flash writes."""
import shutil
from pathlib import Path
from .core import SDK_ROOT, run_tool, find_cc, display_path

BASE = SDK_ROOT / "firmware"
F133 = BASE / "f133"
GRAPHICS = BASE / "imports" / "r10" / "f133_graphics_link"

def status(result):
    result.extra["details"] = {
        "source_root": "firmware/",
        "editable": ["firmware/f133/", "firmware/imports/r10/", "firmware/include/"],
        "working_targets": ["status-lcd", "graphics-link", "f133-stage", "d213-stage"],
        "target_binary_linked": False,
        "linked_stage_artifacts_available": (BASE / "build" / "stage" / "manifest.json").exists(),
        "linked_stage_class": "LINK_TEST_ONLY / NOT_BOOTABLE",
        "device_flash_enabled": False,
        "f133_d213_bsp_bound": False,
        "imported_source_notice": "Imported R10 code is preserved, not yet fully bound to target BSPs.",
    }
    result.artifact(BASE / "README.md")
    result.artifact(F133 / "src" / "lcd_status.c")
    result.artifact(GRAPHICS / "src" / "gfx_link.c")
    result.warn("C objects and host tests are not executable firmware images; no board validation")

def _toolchain(toolchain, result):
    if toolchain == "host":
        cc, description = find_cc()
        if not cc: result.verdict="NOT_AVAILABLE"; result.failures.append({"code":"FW-CC", "message":description}); return None, []
        return cc, []
    cc = shutil.which("clang")
    if not cc:
        result.verdict="NOT_AVAILABLE"
        result.failures.append({"code":"FW-RISCV", "message":"Clang with RISC-V target is not installed; no target objects built"})
        return None, []
    return cc, ["--target=riscv64-unknown-elf", "-march=rv64gc", "-mabi=lp64d"]

def build(result, target, toolchain):
    if toolchain == "riscv-clang" and target != "status-lcd":
        result.verdict="NOT_AVAILABLE"
        result.failures.append({"code":"FW-SYSROOT", "message":"R10 graphics link requires a qualified RISC-V target libc/sysroot and BSP"})
        return
    cc, architecture = _toolchain(toolchain,result)
    if not cc: return
    if target == "status-lcd":
        source=F133 / "src" / "lcd_status.c"
        includes=[BASE / "include",F133 / "include"]
    else:
        source=GRAPHICS / "src" / "gfx_link.c"
        includes=[GRAPHICS / "include"]
    out=BASE / "build" / toolchain
    out.mkdir(parents=True,exist_ok=True)
    obj=out / (target+".o")
    argv=[cc,*architecture,"-std=c11","-ffreestanding","-Wall","-Wextra","-Werror",*(arg for inc in includes for arg in ("-I",str(inc))),"-c",str(source),"-o",str(obj)]
    code, message=run_tool(argv,SDK_ROOT,120)
    if code != 0:
        result.fail("FW-BUILD", "compiler returned %s: %s"%(code,message[-1200:]),display_path(source))
        return
    result.artifact(obj)
    result.extra["details"]={"target":target,"compiler":cc,"toolchain":toolchain,"artifact_kind":"relocatable object, NOT a bootable or flashable firmware image"}
    result.warn("Object-only build. Linking, BSP, reset vectors and board qualification remain outstanding.")

def test(result):
    cc, desc=find_cc()
    if not cc:
        result.verdict="NOT_AVAILABLE"
        result.failures.append({"code":"FW-CC", "message":desc})
        return
    tests=[
        ("status-lcd", [F133/"src"/"lcd_status.c",F133/"tests"/"test_lcd_status.c"],[BASE/"include",F133/"include"]),
        ("graphics-link",[GRAPHICS/"src"/"gfx_link.c",GRAPHICS/"tests"/"test_gfx.c"],[GRAPHICS/"include"]),
        ("boot-monitor",[F133/"src"/"lcd_status.c",F133/"src"/"boot_monitor.c",F133/"tests"/"test_boot_monitor.c"],[BASE/"include",F133/"include"]),
        ("serlcd-i2c",[F133/"src"/"lcd_status.c",F133/"src"/"serlcd_i2c.c",F133/"tests"/"test_serlcd_i2c.c"],[BASE/"include",F133/"include"]),
    ]
    out=BASE/"build"/"host-tests"
    out.mkdir(parents=True,exist_ok=True)
    complete=0
    for name,sources,includes in tests:
        binary=out/(name+(".exe" if __import__("os").name=="nt" else ""))
        cmd=[cc,"-std=c11","-O2","-Wall","-Wextra","-Werror",*(arg for inc in includes for arg in ("-I",str(inc))),*(str(p) for p in sources),"-o",str(binary)]
        code,log=run_tool(cmd,SDK_ROOT,120)
        if code != 0:
            result.fail("FW-TEST-BUILD", "%s compile failed: %s"%(name,log[-1500:])); continue
        code,log=run_tool([str(binary)],SDK_ROOT,120)
        if code != 0:
            result.fail("FW-TEST", "%s run failed: %s"%(name,log[-1500:])); continue
        complete += 1
        result.artifact(binary)
    result.extra["test_count"]=len(tests)
    result.extra["failed_count"]=len(tests)-complete
    result.warn("Tests use host mocks; target HAL, hardware LCD transport and device deployment are not proven")
