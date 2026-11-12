"""Bounded, repeatable firmware/boot experiments and host-only image tooling."""
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
from . import boot_loading as boot
from .simulation_tools import host_firmware
from . import locations


def output_file(root, relative):
    root = Path(root).resolve()
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError("Boot output must stay inside the project: " + str(relative))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def campaign(root):
    root = Path(root).resolve()
    started = time.time()
    inspected = boot.inspect(root)
    output = output_file(root,"build/boot_loading/campaign.json").parent
    if any(p.is_symlink() for p in output.rglob("*")):
        raise ValueError("Boot build area must not contain symlinks")
    commands, cases = [], []
    def run(name, argv, cwd=root, timeout=60, extra_env=None):
        p = subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=timeout,
                           env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1",**(extra_env or {})})
        commands.append(dict(id=name,argv=[str(a) for a in argv],cwd=str(cwd),
                             exit_status=p.returncode,stdout=p.stdout[:40000],stderr=p.stderr[:20000],
                             environment_overrides=extra_env or {}))
        cases.append(dict(id=name,status="PASS" if p.returncode==0 else "FAIL",evidence="HOST_SIM"))
        return p
    compiler = shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
    make = shutil.which("make")
    if not compiler or not make:
        cases.append(dict(id="host-toolchain",status="BLOCKED",reason="Host C compiler and make required"))
    else:
        run("compiler",[compiler,"--version"])
        cases[-1]["evidence"]="STATIC_CHECK"
        run("image-format-and-readiness",[sys.executable,"-m","unittest","-v","tests.test_boot_loading","tests.test_boot_handoff"])
        run("f133-app-load-and-sanitizers",[make,"-f","software/boot/Makefile","app-test","app-sanitize",
                                          "CC="+compiler,"OUT="+str(output/"app")],timeout=120)
        sys.path.insert(0,str(locations.program(root)/"sdk/cli"))
        from arc1cli import boot_image
        fixture = output_file(root,"build/boot_loading/sanitizer-fixture.egon")
        fixture.write_bytes(boot_image.pack(b"host diagnostic data, not boot code",max_image_bytes=512))
        sanitized = output_file(root,"build/boot_loading/egon_bounds")
        built = run("egon-sanitizer-build",[compiler,"-std=c11","-O1","-g","-Wall","-Wextra","-Werror",
                     "-Wpedantic","-Wconversion","-Wshadow","-fsanitize=address,undefined",
                     "-fno-sanitize-recover=all","-fno-omit-frame-pointer",
                     root/"software/boot/tests/egon_bounds.c",root/"software/boot/egon_validate.c","-o",sanitized])
        if built.returncode==0:
            # LSan task enumeration is unavailable under this hosted tracer.
            # Address/undefined-behavior checks stay enabled; no leak-clean claim.
            run("egon-bounds-sanitized",[sanitized,fixture],extra_env={"ASAN_OPTIONS":"detect_leaks=0"})
        fw = root / boot.BASE / "firmware/f133_bootloader"
        # Existing make tests compile into this job's build area; no layout regeneration.
        run("f133-update-recovery",[make,"test","freestanding","CC="+compiler,"OUT="+str(output/"f133")],fw,120)
        loader = host_firmware(root,output)
        commands.extend(loader["commands"])
        cases.extend(loader["cases"])
    run("f133-source-inventory",[sys.executable,"-I",str(root/boot.BASE/"firmware/f133_bootloader/tools/r10_readiness.py")])
    cases[-1]["evidence"]="STATIC_CHECK"
    status = "FAIL" if any(c["status"]=="FAIL" for c in cases) else "BLOCKED" if any(c["status"]=="BLOCKED" for c in cases) else "PASS"
    if boot.input_hashes(root) != inspected["input_hashes"]:
        raise ValueError("Boot inputs changed during execution")
    report = dict(inspected,evidence="HOST_SIM",created=started,experiment_status=status,cases=cases,commands=commands)
    output_file(root,"build/boot_loading/campaign.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(experiment_status=status,target_status="BLOCKED",fabrication="HOLD",flashing="HOLD",
                          report="build/boot_loading/campaign.json",cases=cases),indent=2))
    return 1 if status=="FAIL" else 3 if status=="BLOCKED" else 0


def image_action(args):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"sdk/cli"))
    from arc1cli import boot_image
    source = args.input.resolve()
    if source.stat().st_size > boot_image.HOST_RESOURCE_LIMIT:
        raise ValueError("Input exceeds 16 MiB host tool ceiling")
    data = source.read_bytes()
    if args.action == "pack":
        target = args.output
        if target.is_symlink() or target.resolve()==source:
            raise ValueError("Use a distinct regular output file")
        data = boot_image.pack(data,max_image_bytes=args.load_limit)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    result = boot_image.inspect(data,max_image_bytes=args.load_limit)
    result.update(evidence="HOST_SIM",sha256=hashlib.sha256(data).hexdigest(),target_status="BLOCKED",flashing="HOLD")
    print(json.dumps(result,indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action",required=True)
    for action in ("campaign","inspect"):
        sub.add_parser(action).add_argument("--root",type=Path,default=Path.cwd())
    for action in ("pack","check-image"):
        p = sub.add_parser(action)
        p.add_argument("input",type=Path)
        if action=="pack": p.add_argument("output",type=Path)
        p.add_argument("--load-limit",type=int,required=True,help="Explicit caller load limit in bytes; no board default")
    args = parser.parse_args()
    try:
        if args.action=="inspect": print(json.dumps(boot.inspect(args.root),indent=2)); return 0
        if args.action=="campaign": return campaign(args.root)
        return image_action(args)
    except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
        print(json.dumps(dict(status="FAIL",reason=str(exc),fabrication="HOLD",flashing="HOLD")))
        return 1


if __name__=="__main__":
    raise SystemExit(main())
