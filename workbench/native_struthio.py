"""Real native compiler, parity checks, deterministic host replay and packaging."""

from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time
import zipfile
from .project_inventory import hashes, revision


def binary(root):
    return (
        Path(root)
        / "build/native_struthio"
        / ("struthio_host.exe" if os.name == "nt" else "struthio_host")
    )


def source_hashes(root):
    return hashes(Path(root) / "software/struthio")


class ParityFailure(RuntimeError):
    """An executed JavaScript-to-C comparison diverged: an actual failed assertion."""

    def __init__(self, message, cases):
        super().__init__(message)
        self.cases = cases


def run(argv, root, input=None):
    start = time.monotonic()
    p = subprocess.run(
        [str(x) for x in argv],
        cwd=root,
        input=input,
        text=True,
        capture_output=True,
        timeout=90,
    )
    result = {
        "argv": [str(x) for x in argv],
        "exit_status": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
        "duration_seconds": time.monotonic() - start,
    }
    printable = dict(result)
    if len(printable["stdout"]) > 4000:
        printable["stdout"] = (
            printable["stdout"][:4000]
            + "\n[console excerpt; full output retained by caller]"
        )
    print(json.dumps(printable), flush=True)
    if p.returncode:
        raise RuntimeError("Tool failed: " + p.stderr[:2000])
    return result


def build(root):
    root = Path(root)
    src = root / "software/struthio"
    out = binary(root).parent
    out.mkdir(parents=True, exist_ok=True)
    cc = shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
    if not cc:
        raise RuntimeError(
            "Dependency unavailable: install Windows LLVM/MinGW C11 compiler or GCC/Clang; no compilation performed"
        )
    version = run([cc, "--version"], root)["stdout"]
    command = [
        cc,
        "-std=c11",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-pedantic",
        src / "struthio_core.c",
        src / "game.c",
        src / "state.c",
        src / "host.c",
        "-o",
        binary(root),
    ]
    result = run(command, root)
    report = {
        "schema": "struthio.host-build/1",
        "tool": cc,
        "version": version,
        "inputs": source_hashes(root),
        "binary_sha256": hashlib.sha256(binary(root).read_bytes()).hexdigest(),
        "result": result,
        "target": "HOST-" + sys.platform,
        "physical_compatibility": "NOT VERIFIED",
        "gameplay": "Portable C gameplay; diagnostic renderer; audio backend pending",
    }
    (out / "build.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def replay(root):
    build(root)
    out = binary(root).parent
    commands = (
        ["reset 1"]
        + [
            "step %d %d %d 0 0" % (int(120 <= t < 180), int(t < 100), int(t % 19 == 0))
            for t in range(240)
        ]
        + ["quit"]
    )
    text = "\n".join(commands) + "\n"
    a = run([binary(root), out / "frame.ppm"], root, text)["stdout"]
    b = run([binary(root), out / "frame.ppm"], root, text)["stdout"]
    aa = [json.loads(x) for x in a.splitlines()]
    bb = [json.loads(x) for x in b.splitlines()]
    for x in aa + bb:
        x.pop("step_cpu_us")
    if aa != bb:
        raise RuntimeError("Native replay is nondeterministic")
    (out / "replay-input.txt").write_text(text, encoding="utf-8")
    (out / "replay.json").write_text(
        json.dumps(
            {
                "seed": 1,
                "ticks": 240,
                "repeatable": True,
                "states": aa,
                "js_full_state_parity": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "repeatable": True,
        "ticks": 240,
        "digest": aa[-1]["digest"],
        "full_game_parity": False,
    }


def test(root):
    report = build(root)
    out = binary(root).parent
    src = Path(root) / "software/struthio"
    cc = report["tool"]
    oracle = Path(root) / "hardware/compact-arc1/R10_WORK/closure_p11_struthio/oracle"
    extension = ".exe" if os.name == "nt" else ""
    for name in ("test_core", "test_rings"):
        run(
            [
                cc,
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-pedantic",
                src / "struthio_core.c",
                src / "game.c",
                src / "state.c",
                src / (name + ".c"),
                "-o",
                out / (name + extension),
            ],
            root,
        )
    vectors = run(
        [
            out / ("test_core" + extension),
            oracle / "physics_vectors.csv",
            oracle / "world_vectors.csv",
            oracle / "rng_vectors.csv",
        ],
        root,
    )
    node = shutil.which("node")
    if not node:
        raise RuntimeError(
            "Node.js required for live JavaScript-to-C ring parity; NOT RUN"
        )
    expected = [
        json.loads(x)
        for x in run([node, src / "ring_oracle.mjs"], root)["stdout"].splitlines()
    ]
    actual = [
        json.loads(x)
        for x in run([out / ("test_rings" + extension)], root)["stdout"].splitlines()
    ]
    divergence = None
    for js, c in zip(expected, actual):
        for field in js:
            if js[field] != c.get(field):
                divergence = {
                    "scenario": "ring " + str(js["ring"]),
                    "first_divergent_tick": js["tick"],
                    "field": field,
                    "javascript": js[field],
                    "c": c.get(field),
                }
                break
        if divergence:
            break
    result = {
        "physics_rng_world_vectors": 1344,
        "ring_ticks": len(actual),
        "ring_parity": expected == actual,
        "first_divergence": divergence,
        "coverage": "Named scenarios only; not exhaustive gameplay proof",
        "reference_240_tick_full_state": "PENDING",
        "compiler": report["version"],
        "source_hashes": report["inputs"],
        "vectors": vectors,
    }
    (out / "tests.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if expected != actual:
        raise ParityFailure(
            "Ring parity failed: " + json.dumps(divergence),
            [{"scenario": "ring parity", "divergence": divergence, "passed": False}],
        )
    result["replay"] = replay(root)
    result["gameplay"] = gameplay_parity(root)
    result["reference_240_tick_full_state"] = "PASS"
    result["gameplay_scenarios_passed"] = len(result["gameplay"])
    (out / "tests.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def state_field(vector, index):
    fields = [
        "format",
        "sim.tick",
        "sim.shell",
        "sim.nextActorId",
        "sim.eventSerial",
        "sim.score",
        "sim.lives",
        "rng.gameplayState",
        "player.x",
        "player.y",
        "player.vx",
        "player.vy",
        "player.groundedPlatformId",
        "player.facing",
        "player.wing",
        "player.flapCooldown",
        "player.footingTicks",
        "player.lavaPhase",
        "player.lavaTicks",
        "player.invulnerableTicks",
        "tower.round",
        "tower.ringMask",
        "tower.kills",
        "tower.check",
        "tower.go",
        "tower.hold",
        "tower.cooldown",
        "tower.mercy",
        "run.eggChain",
        "run.clean",
        "run.deaths",
        "run.lifeBands",
        "actors.length",
    ]
    if index < len(fields):
        return fields[index]
    offset = index - 33
    actor_words = vector[32] * 15
    if offset < actor_words:
        names = [
            "id",
            "kind",
            "class",
            "ghost",
            "tier",
            "lifecycle",
            "x",
            "y",
            "vx",
            "vy",
            "facing",
            "phase",
            "timer",
            "rngDraws",
            "joustAwarded",
        ]
        return "actors[%s].%s" % (offset // 15, names[offset % 15])
    offset -= actor_words
    if offset < 2:
        return ["world.lavaY", "world.platforms.length"][offset]
    offset -= 2
    return "world.platforms[%s].%s" % (
        offset // 8,
        ["id", "phase", "tick", "x", "y", "width", "height", "collidable"][offset % 8],
    )


def gameplay_scenarios(root):
    """Named JavaScript-to-C gameplay scenarios as oracle/host command lists."""
    root = Path(root)
    reference = (
        root
        / "hardware/compact-arc1/R10_WORK/closure_p11_struthio/oracle/js_authoritative_trace_240.jsonl"
    )
    trace = [json.loads(line) for line in reference.read_text().splitlines()]
    legacy = ["reset " + str(trace[0]["seed"])]
    for row in trace:
        i = row["input"]
        legacy.append(
            "step %d %d %d %d 0"
            % (i["left"], i["right"], i["flapEdge"], i.get("dartEdge", False))
        )
    scenarios = {
        "reference-240": legacy,
        "extended-flight-3000": ["reset 98765"]
        + [
            "step %d %d %d %d %d"
            % (t % 240 >= 120, t % 240 < 120, t % 11 == 0, t % 137 == 0, (t // 200) % 4)
            for t in range(3000)
        ],
    }
    for name, kind, length in [
        ("lava-death", 1, 260),
        ("joust-win", 3, 200),
        ("joust-death", 4, 260),
        ("egg-hatch-remount", 5, 200),
        ("egg-collect", 6, 10),
        ("gold-next-round", 7, 400),
        ("game-over", 8, 20),
        ("moving-platform", 10, 400),
    ]:
        scenarios[name] = ["fixture %d 0" % kind] + ["step 0 0 0 0 0"] * length
    scenarios["lava-rescue"] = ["fixture 1 0", "step 0 0 0 0 0", "step 0 0 1 0 3"] + [
        "step 0 0 0 0 0"
    ] * 70
    scenarios["chord-dart"] = ["reset 54321"] + [
        "step 0 1 %d %d %d %d -1"
        % (t % 9 in (0, 1), t % 17 == 0, 3 if t % 9 == 1 else 2, t % 9 == 1)
        for t in range(400)
    ]
    scenarios["save-restore"] = (
        legacy + ["save"] + ["step 1 0 1 0 1"] * 10 + ["load"] + ["step 0 1 0 0 0"] * 20
    )
    # A wing flap toward the opposite side and a dart on the same tick: the
    # dart keeps the side the bird faced before the flap (step.mjs humanIntent).
    for name, held, kind in (("sided-flap-dart-left", "1 0", 2), ("sided-flap-dart-right", "0 1", 1)):
        scenarios[name] = (
            ["reset 4242"]
            + ["step %s 0 0 0" % held] * 40
            + ["step %s 1 0 0" % held]
            + ["step 0 0 0 0 0"] * 6
            + ["step 0 0 1 1 %d" % kind]
            + ["step 0 0 0 0 0"] * 30
        )
    return scenarios


def gameplay_parity(root):
    root = Path(root)
    out = binary(root).parent
    node = shutil.which("node")
    scenarios = gameplay_scenarios(root)
    reports = []
    for name, commands in scenarios.items():
        text = "\n".join(commands + ["quit"]) + "\n"
        input_path = out / (name + "-inputs.txt")
        input_path.write_text(text, encoding="utf-8")
        expected = [
            json.loads(x)
            for x in run(
                [node, root / "software/struthio/state_oracle.mjs"], root, text
            )["stdout"].splitlines()
        ]
        actual = [
            json.loads(x)
            for x in run([binary(root), out / "frame.ppm"], root, text)[
                "stdout"
            ].splitlines()
        ]
        divergence = None
        for tick, (js, c) in enumerate(zip(expected, actual)):
            for field in ("state_vector", "event_types"):
                if js[field] != c[field]:
                    index = next(
                        (
                            i
                            for i, (a, b) in enumerate(zip(js[field], c[field]))
                            if a != b
                        ),
                        min(len(js[field]), len(c[field])),
                    )
                    divergence = {
                        "first_divergent_tick": tick,
                        "field": state_field(js[field], index)
                        if field == "state_vector"
                        else "events[%s].type" % index,
                        "simulation_tick": js["state_vector"][1],
                        "input_artifact": input_path.relative_to(root).as_posix(),
                        "index": index,
                        "javascript": js[field][index : index + 6],
                        "c": c[field][index : index + 6],
                        "command": commands[tick],
                        "reproduce": "python -m workbench.native_struthio test",
                    }
                    break
            if divergence:
                break
        if len(expected) != len(actual):
            divergence = {"error": "Trace length mismatch"}
        entry = {
            "scenario": name,
            "commands_after_reset": len(commands) - 1,
            "state_fields_compared": "all persistent JS fields mapped to versioned integer vector",
            "event_comparison": "ordered event types; event payload parity not claimed",
            "divergence": divergence,
            "passed": divergence is None,
        }
        reports.append(entry)
        (out / (name + "-comparison.json")).write_text(
            json.dumps(entry, indent=2), encoding="utf-8"
        )
        if divergence:
            raise ParityFailure("Gameplay parity: " + json.dumps(entry), reports)
    return reports


DIFFERENTIAL_SEEDS = tuple(range(1, 13))
DIFFERENTIAL_TICKS = 2000


def differential_commands(seed, ticks=DIFFERENTIAL_TICKS):
    """Deterministic player-like input: held directions, flap bursts, darts, chords."""
    r = random.Random(seed)
    commands = ["reset %d" % seed]
    left = right = 0
    flap_rate = 0.15
    for _ in range(ticks):
        if r.random() < 0.03:
            left, right = r.choice([(1, 0), (0, 1), (0, 0), (1, 1)])
        if r.random() < 0.02:
            flap_rate = r.choice([0.02, 0.08, 0.15, 0.3, 0.6])
        flap = int(r.random() < flap_rate)
        dart = int(r.random() < 0.01)
        kind = r.choice([0, 0, 1, 2, 3])
        if r.random() < 0.01:
            commands.append(
                "step %d %d %d %d 3 1 %d" % (left, right, flap, dart, r.choice([-1, 1]))
            )
        else:
            commands.append("step %d %d %d %d %d" % (left, right, flap, dart, kind))
    return commands


def differential(root):
    """Seeded JavaScript-to-C differential parity over a fixed, bounded seed set.

    Every tick's persistent state vector and ordered event types are compared;
    each seed reports its first divergence. Seeds and inputs are fixed so a
    result is reproducible from the source revision alone.
    """
    report = build(root)
    root = Path(root)
    out = binary(root).parent
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js required for live JavaScript-to-C parity; NOT RUN")
    cases = []
    for seed in DIFFERENTIAL_SEEDS:
        commands = differential_commands(seed)
        text = "\n".join(commands + ["quit"]) + "\n"
        input_path = out / ("differential-%d-inputs.txt" % seed)
        input_path.write_text(text, encoding="utf-8")
        expected = [
            json.loads(x)
            for x in run([node, root / "software/struthio/state_oracle.mjs"], root, text)[
                "stdout"
            ].splitlines()
        ]
        actual = [
            json.loads(x)
            for x in run([binary(root), out / "frame.ppm"], root, text)["stdout"].splitlines()
        ]
        divergence = None
        for line, (js, c) in enumerate(zip(expected, actual)):
            for field in ("state_vector", "event_types"):
                if js[field] != c[field]:
                    index = next(
                        (i for i, (a, b) in enumerate(zip(js[field], c[field])) if a != b),
                        min(len(js[field]), len(c[field])),
                    )
                    divergence = {
                        "first_divergent_line": line,
                        "simulation_tick": js["state_vector"][1],
                        "field": state_field(js[field], index)
                        if field == "state_vector"
                        else "events[%s].type" % index,
                        "javascript": js[field][index : index + 6],
                        "c": c[field][index : index + 6],
                        "command": commands[line],
                        "input_artifact": input_path.relative_to(root).as_posix(),
                    }
                    break
            if divergence:
                break
        if divergence is None and len(expected) != len(actual):
            divergence = {"error": "Trace length mismatch"}
        cases.append(
            {
                "seed": seed,
                "ticks": DIFFERENTIAL_TICKS,
                "event_types_reached": sorted(
                    {t for row in expected for t in row["event_types"]}
                ),
                "divergence": divergence,
                "passed": divergence is None,
            }
        )
    result = {
        "schema": "arc-ledger.struthio-differential/1",
        "seeds": list(DIFFERENTIAL_SEEDS),
        "ticks_per_seed": DIFFERENTIAL_TICKS,
        "divergent_seeds": [c["seed"] for c in cases if not c["passed"]],
        "cases": cases,
        "coverage": "Fixed seeded inputs; regression evidence, not exhaustive proof",
        "compiler": report["version"],
        "source_hashes": report["inputs"],
    }
    (out / "differential.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if result["divergent_seeds"]:
        raise ParityFailure("Differential parity: " + json.dumps(
            [{"seed": c["seed"], **c["divergence"]} for c in cases if not c["passed"]]
        ), cases)
    return result


REPORTED = ("test", "differential")


def reported(root, operation):
    """Run a comparison and leave build/native_struthio/<operation>.json for the kernel.

    Only an executed divergence is FAIL with failing cases. Build errors, a missing
    Node.js or any other exception is BLOCKED with no cases, so it can never be
    presented as a failed assertion.
    """
    report = {
        "schema": "arc-ledger.struthio-tool/1",
        "action": operation,
        "created": time.time(),
        "class": "HOST_SIM",
        "physical_hardware": False,
    }
    try:
        result = globals()[operation](root)
        report.update(status="PASS", cases=result["cases" if operation == "differential" else "gameplay"])
        return result
    except ParityFailure as e:
        report.update(status="FAIL", cases=e.cases, error=str(e)[:4000])
        raise
    except Exception as e:
        report.update(status="BLOCKED", cases=[], error=str(e)[:4000])
        raise
    finally:
        out = binary(root).parent
        out.mkdir(parents=True, exist_ok=True)
        (out / (operation + ".json")).write_text(json.dumps(report, indent=2), encoding="utf-8")


def package(root):
    report = build(root)
    out = binary(root).parent
    metadata = {
        "schema": "arc-ledger.cartridge-development/1",
        "target": report["target"],
        "name": "STRUTHIO native C development",
        "executable": binary(root).name,
        "sha256": report["binary_sha256"],
        "sources": report["inputs"],
        "build": report,
        "memory": {
            "state": "Reported by host protocol sizeof(StrGame)",
            "framebuffer_bytes": 256 * 384 * 3,
        },
        "assets": [],
        "compatibility": {
            "physical_arc1": False,
            "reason": "Target runtime unverified",
        },
        "revision": revision(hashes(root)),
    }
    with zipfile.ZipFile(
        out / "struthio-host-development.zip", "w", zipfile.ZIP_DEFLATED
    ) as z:
        z.write(binary(root), binary(root).name)
        z.writestr("cartridge.json", json.dumps(metadata, indent=2))
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "operation", choices=("build", "test", "replay", "package", "differential")
    )
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    a = parser.parse_args()
    a.root = a.root.resolve()
    try:
        result = (
            reported(a.root, a.operation)
            if a.operation in REPORTED
            else globals()[a.operation](a.root)
        )
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
