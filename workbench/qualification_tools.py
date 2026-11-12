"""Fixed real compiler/simulator targets. No shell or caller-provided argv."""

import argparse, hashlib, json, os, shutil, subprocess, time
from pathlib import Path


def run(root, action):
    root = Path(root).resolve()
    out = root / "build/agent_qualification"
    out.mkdir(parents=True, exist_ok=True)
    r = {
        "schema": "arc-ledger.qualification-tool/1",
        "action": action,
        "commands": [],
        "created": time.time(),
        "status": "FAIL",
        "physical_hardware": False,
    }

    def cmd(argv):
        p = subprocess.run(
            list(map(str, argv)),
            cwd=root,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
            stdin=subprocess.DEVNULL,
        )
        r["commands"].append(
            {
                "argv": list(map(str, argv)),
                "cwd": str(root),
                "exit_status": p.returncode,
                "stdout": p.stdout,
                "stderr": p.stderr,
            }
        )
        return p

    src = root / "development/agent_qualification"
    if action == "wait":
        print("Bounded wait task started", flush=True)
        time.sleep(20)
        r["status"] = "PASS"
    elif action in ("build", "test"):
        cc = shutil.which("gcc") or shutil.which("clang")
        if not cc:
            r.update(status="BLOCKED", reason="Native GCC or Clang required")
        else:
            r["compiler_version"] = cmd([cc, "--version"]).stdout
            inputs = [src / "src/credits.c", src / "tests/credits_test.c"]
            r["input_hashes"] = {
                p.relative_to(root).as_posix(): hashlib.sha256(
                    p.read_bytes()
                ).hexdigest()
                for p in inputs
            }
            binary = out / ("credits_test.exe" if os.name == "nt" else "credits_test")
            p = cmd(
                [
                    cc,
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-O2",
                    *inputs,
                    "-o",
                    binary,
                ]
            )
            if p.returncode == 0:
                r["status"] = "PASS"
                if action == "test":
                    p = cmd([binary])
                    r["cases"] = [json.loads(x) for x in p.stdout.splitlines()]
                    r["status"] = "PASS" if p.returncode == 0 else "FAIL"
    elif action == "rtl":
        cc = shutil.which("iverilog")
        sim = shutil.which("vvp")
        if not cc or not sim:
            r.update(
                status="BLOCKED",
                reason="iverilog and vvp required; RTL fixture not simulated",
            )
        else:
            cmd([cc, "-V"])
            cmd([sim, "-V"])
            binary = out / "handshake.vvp"
            p = cmd(
                [
                    cc,
                    "-g2012",
                    "-o",
                    binary,
                    src / "src/handshake.v",
                    src / "tests/handshake_tb.v",
                ]
            )
            if p.returncode == 0:
                r["status"] = "PASS" if cmd([sim, binary]).returncode == 0 else "FAIL"
    (out / (action + ".json")).write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps(r), flush=True)
    return 0 if r["status"] == "PASS" else 3 if r["status"] == "BLOCKED" else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["build", "test", "wait", "rtl"])
    p.add_argument("--root", type=Path, required=True)
    a = p.parse_args()
    raise SystemExit(run(a.root, a.action))
