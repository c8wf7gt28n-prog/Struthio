"""Fixed ARC-OS host targets, invoked by the existing engineering job worker.

Native game modules are trusted local code. Hash/ABI validation detects stale or
incompatible development artifacts; it is not a sandbox or a signature system.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile
from . import locations

ACTIONS = ("build", "test", "replay", "package", "dependencies", "kernel_probe")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources(root):
    result = {}
    for prefix in ("software/arcos", "software/struthio", "sdk/include"):
        for p in sorted((Path(root) / prefix).rglob("*")):
            if p.is_file():
                result[p.relative_to(root).as_posix()] = sha(p)
    result["workbench/arcos_tools.py"] = sha(Path(root) / "workbench/arcos_tools.py")
    return result


def target():
    return "host-" + sys.platform + "-" + platform.machine()


def validate_card(root, card):
    root = Path(root).resolve()
    if card.get("schema") != "arc-os.gamecard/1" or card.get("abi") != 1:
        raise ValueError("GameCard schema/ABI rejected")
    if card.get("target") != target() or card.get("physical_boot") is not False:
        raise ValueError("GameCard is not a compatible host development artifact")
    name = card.get("artifact", "")
    if not isinstance(name, str) or name not in ("pulse.so", "struthio.so", "pulse.dylib", "struthio.dylib"):
        raise ValueError("GameCard artifact path rejected")
    out = root / "build/arcos"
    original = out / name
    artifact = original.resolve()
    if artifact.parent != out.resolve() or not artifact.is_file() or original.is_symlink():
        raise ValueError("GameCard artifact missing or outside build directory")
    if sha(artifact) != card.get("sha256") or card.get("sources") != sources(root):
        raise ValueError("GameCard source/artifact hashes are stale")
    magic = artifact.read_bytes()[:4]
    allowed = (b"\x7fELF",) if sys.platform == "linux" else (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf")
    if magic not in allowed:
        raise ValueError("GameCard executable format rejected")
    return artifact


def launch_argv(root, game):
    root = Path(root).resolve()
    out = root / "build/arcos"
    report = json.loads((out / "build.json").read_text())
    executable = out / "arc_os_host"
    if report.get("input_hashes") != sources(root) or report.get("launcher_sha256") != sha(executable):
        raise ValueError("Rebuild ARC-OS: launcher or source hashes are stale")
    args = [str(executable)]
    if game != "none":
        card = json.loads((out / (game + ".gamecard.json")).read_text())
        args.append(str(validate_card(root, card)))
    return args


def run(root, action):
    root = Path(root).resolve()
    src = root / "software/arcos"
    out = root / "build/arcos"
    out.mkdir(parents=True, exist_ok=True)
    report = {"schema": "arc-ledger.arcos-tool/1", "action": action, "created": time.time(),
              "status": "FAIL", "class": "HOST_SIM", "physical_hardware": False,
              "target": target(), "commands": [], "checks": [], "input_hashes": sources(root)}

    def cmd(argv, input=None, timeout=45):
        started = time.monotonic()
        p = subprocess.run(list(map(str, argv)), cwd=root, input=input, text=True,
                           capture_output=True, timeout=timeout)
        report["commands"].append({"argv": list(map(str, argv)), "cwd": str(root),
                                  "exit_status": p.returncode, "stdout": p.stdout,
                                  "stderr": p.stderr, "duration_seconds": time.monotonic()-started})
        if p.returncode:
            raise RuntimeError(p.stderr or p.stdout or "Tool failed")
        return p.stdout

    def check(name, condition):
        report["checks"].append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    def session(game, lines):
        raw = cmd(launch_argv(root, game), "\n".join(lines + ["quit", ""]))
        return [json.loads(x) for x in raw.splitlines()]

    try:
        if action == "dependencies":
            from .arcos_dependencies import inspect
            report.update(inspect(root))
            report["status"] = "PASS"
        elif action == "kernel_probe":
            from .arcos_kernel_probe import probe
            report.update(probe(root, cmd))
        else:
            if sys.platform not in ("linux", "darwin"):
                report.update(status="BLOCKED", reason="ARC-OS POSIX host backend requires macOS or Linux")
                raise NotImplementedError(report["reason"])
            cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
            if not cc:
                report.update(status="BLOCKED", reason="Install a C11 compiler: Debian build-essential or macOS Command Line Tools")
                raise NotImplementedError(report["reason"])
            report["compiler_version"] = cmd([cc, "--version"])
            flags = [cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                     "-I" + str(src / "include"), "-I" + str(locations.program(root) / "sdk/include"),
                     "-I" + str(root / "software/struthio")]
            cmd([*flags, src/"src/host.c", src/"src/launcher.c", src/"src/controller.c", "-o", out/"arc_os_host",
                 *([] if sys.platform == "darwin" else ["-ldl"])])
            cmd([*flags, src/"tests/test_launcher.c", src/"src/launcher.c",
                 src/"src/controller.c", "-o", out/"test_launcher"])
            suffix = ".dylib" if sys.platform == "darwin" else ".so"
            shared = "-dynamiclib" if sys.platform == "darwin" else "-shared"
            core = [root/"software/struthio"/name for name in ("struthio_core.c", "game.c", "state.c")]
            for name, files in (("pulse", [src/"games/pulse.c"]),
                                ("struthio", [src/"games/struthio_bridge.c", *core])):
                artifact = out / (name + suffix)
                cmd([*flags, "-fPIC", shared, *files, "-o", artifact])
                card = {"schema": "arc-os.gamecard/1", "abi": 1, "name": name,
                        "target": target(), "artifact": artifact.name, "sha256": sha(artifact),
                        "sources": report["input_hashes"], "physical_boot": False,
                        "memory": {"state_bytes": "measured in host frames", "target_heap_bytes": None,
                                   "target_stack_bytes": None},
                        "trust": "local native code; same host account; not sandboxed",
                        "assets": ["built-in accent.rgb"], "dependencies": ["ARC-OS host ABI 1"]}
                (out/(name+".gamecard.json")).write_text(json.dumps(card, indent=2)+"\n")
            report["launcher_sha256"] = sha(out/"arc_os_host")
            report["status"] = "PASS"
            (out/"build.json").write_text(json.dumps(report, indent=2)+"\n")
            if action in ("test", "replay"):
                check("C launcher, HID normalization and versioned mock command tests",
                      json.loads(cmd([out/"test_launcher"]))["launcher_states"])
                no_card = session("none", ["input 16", "input 0"])
                check("NO CARD blocks launch", not no_card[-1]["card"] and no_card[-1]["screen"] == "MENU")
                health=session("none",["probe missing_asset","diagnostics","probe audio_device","input 16","input 0"])
                check("health identifies actual host substitutions",health[1]['health']['backend']=='posix-host' and not health[1]['health']['physical_drivers'])
                check("missing asset gives persistent bounded diagnostic",health[1]['error']=='ASSET_UNAVAILABLE' and health[2]['health']['last_error']=='ASSET_UNAVAILABLE')
                check("unsupported audio device is explicit",health[3]['error']=='AUDIO_DEVICE_UNSUPPORTED')
                check("absent media gives visible error and recoverable menu",health[4]['error']=='MEDIA_UNAVAILABLE' and health[5]['screen']=='MENU')
                lifecycle=session("pulse",["input 16","input 0","input 64","input 0","input 16","input 0","media 0","media 1","input 16"])
                check("launch return relaunch removal reinsertion",[lifecycle[i]['screen'] for i in (1,3,5,7,9)]==['GAME','MENU','GAME','MENU','GAME'])
                (out/'health-lifecycle.json').write_text(json.dumps(dict(health=health,lifecycle=lifecycle,environment='HOST_SIM',input_hashes=report['input_hashes']),indent=2)+'\n')
                # A starts the game; release, movement, A save/tone, Start return.
                inputs = ["input 16", "input 0"] + ["input 8"]*25 + ["input 16", "input 0", "input 64"]
                frames = session("pulse", inputs)
                check("separate mini-game launch and clean return",
                      frames[1]["screen"] == "GAME" and frames[-1]["screen"] == "MENU")
                check("SDK asset, save round-trip and tone events", frames[-2]["save_bytes"] == 4 and frames[-2]["audio_events"] >= 1)
                check("deterministic mini-game replay", frames == session("pulse", inputs))
                removed = session("pulse", ["input 16", "media 0"])
                check("media removal returns safely", removed[-1]["screen"] == "MENU" and not removed[-1]["card"])
                demo = session("none", ["demo", "input 0", "input 64"])
                check("system demo and return", demo[1]["screen"] == "SYSTEM_DEMO" and bool(demo[1]["rects"]) and demo[-1]["screen"] == "MENU")
                check("invalid host command reported", session("none", ["nonsense"])[-1]["error"] == "INVALID_COMMAND")
                for field, value in (("abi",99), ("artifact","../../etc/passwd"),
                                     ("target","f133-rom"), ("physical_boot",True), ("sha256","0"*64),
                                     ("sources",{})):
                    card = json.loads((out/"pulse.gamecard.json").read_text())
                    card[field] = value
                    try:
                        validate_card(root, card)
                    except ValueError:
                        check("reject invalid card "+field, True)
                    else:
                        check("reject invalid card "+field, False)
                # Same 120 input ticks: compare adapter against direct unchanged C core.
                cmd([*flags, src/"tests/struthio_direct.c", *core, "-o", out/"struthio_direct"])
                masks = [16] + [8 if i%30 < 15 else 0 for i in range(119)]
                direct = [int(x) for x in cmd([out/"struthio_direct"], "\n".join(map(str,masks))+"\n").splitlines()]
                adapted = session("struthio", ["input "+str(x) for x in masks])[1:]
                check("STRUTHIO adapter equals direct core every tick",
                      direct == [x["game_digest"] for x in adapted] and len(direct) == 120)
                (out/"replay.json").write_text(json.dumps({"pulse": frames, "struthio": adapted}, indent=2)+"\n")
                report["replay_sha256"] = sha(out/"replay.json")
            if action == "package":
                with zipfile.ZipFile(out/"arc_os_host_gamecards.zip", "w", zipfile.ZIP_DEFLATED) as z:
                    for name in ("pulse", "struthio"):
                        card = json.loads((out/(name+".gamecard.json")).read_text())
                        artifact = validate_card(root, card)
                        z.write(artifact, artifact.name)
                        z.write(out/(name+".gamecard.json"), name+".gamecard.json")
                    z.write(out/"arc_os_host", "arc_os_host")
                    z.write(out/"build.json", "build.json")
                report["package_sha256"] = sha(out/"arc_os_host_gamecards.zip")
    except NotImplementedError:
        pass
    except (OSError, ValueError, RuntimeError, AssertionError, subprocess.TimeoutExpired) as e:
        report.update(status="FAIL", error=str(e))
    report["finished"] = time.time()
    (out/(action+".json")).write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report), flush=True)
    return 0 if report["status"] == "PASS" else 3 if report["status"] == "BLOCKED" else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=(*ACTIONS, "serve"))
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--game", choices=("pulse", "struthio", "none"), default="pulse")
    a = p.parse_args()
    if a.action == "serve":
        # Inherit stdin/stdout for the desktop's managed QProcess, no shell.
        try:
            raise SystemExit(subprocess.call(launch_argv(a.root, a.game), cwd=a.root))
        except (OSError, ValueError, KeyError) as e:
            print(str(e), file=sys.stderr)
            raise SystemExit(3)
    raise SystemExit(run(a.root, a.action))
