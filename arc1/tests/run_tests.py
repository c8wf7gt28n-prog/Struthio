#!/usr/bin/env python3
"""ARC-1 SDK self-tests (gates G0 and G1). Standard library only.

    python3 tests/run_tests.py            # whole suite
    python3 tests/run_tests.py -k pass    # unittest name filter

Every validator here has negative controls (TST-001): fixtures that are known
to be invalid must be rejected with the specific requirement code.
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sdk" / "cli"))

from arc1cli import assets, hardware, passrec, project  # noqa: E402
from arc1cli.core import (SCHEMA_DIR, Result, find_cc, schema_validator,  # noqa: E402
                          sha256_file)
from arc1cli.jsonschema_lite import SchemaError, Validator  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
HELLO = ROOT / "examples" / "hello_arc1"

try:  # optional independent cross-check; never required
    import jsonschema as reference_jsonschema
except ImportError:  # pragma: no cover
    reference_jsonschema = None


def arc1(*args, env=None):
    """Runs the CLI exactly as a user would. Returns (exit code, stdout, stderr)."""
    full_env = dict(os.environ)
    full_env.update(env or {})
    p = subprocess.run([sys.executable, str(ROOT / "arc1")] + [str(a) for a in args],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=full_env, timeout=300)
    return p.returncode, p.stdout.decode(), p.stderr.decode()


def arc1_json(*args, env=None):
    code, out, err = arc1(*(list(args) + ["--json"]), env=env)
    try:
        data = json.loads(out)
    except ValueError:
        raise AssertionError("no JSON from arc1 %s (exit %s): %s %s" % (args, code, out, err))
    assert not schema_validator("tool-result.schema.json").errors(data), data
    return code, data


def apply_ops(doc, base_dir, ops):
    for op in ops:
        if op["op"] == "write":
            (base_dir / op["file"]).parent.mkdir(parents=True, exist_ok=True)
            (base_dir / op["file"]).write_text(op["text"], encoding="utf-8")
            continue
        parts = [p for p in op["path"].split("/")[1:]]
        node = doc
        for p in parts[:-1]:
            node = node[int(p)] if isinstance(node, list) else node[p]
        last = parts[-1]
        if isinstance(node, list):
            last = int(last)
        if op["op"] == "set":
            node[last] = op["value"]
        elif op["op"] == "remove":
            del node[last]
        else:
            raise ValueError(op)
    return doc


def load_cases(name):
    return json.loads((FIX / name / "cases.json").read_text(encoding="utf-8"))


def codes(findings):
    return {c for c, _, _ in findings}


# --------------------------------------------------------------------- G0

class SchemaValidatorTests(unittest.TestCase):
    def test_all_schemas_load(self):
        names = sorted(p.name for p in SCHEMA_DIR.glob("*.schema.json"))
        self.assertGreaterEqual(len(names), 7)
        for n in names:
            schema_validator(n)

    def test_unsupported_keyword_fails_closed(self):
        with self.assertRaises(SchemaError):
            Validator({"type": "object", "properties": {"a": {"format": "email"}}})
        with self.assertRaises(SchemaError):
            Validator({"$ref": "https://example.com/remote.json"})

    def test_keywords(self):
        v = Validator({"type": "object", "required": ["n"], "additionalProperties": False,
                       "properties": {"n": {"type": "integer", "minimum": 1},
                                      "s": {"type": "string", "pattern": "^a"},
                                      "l": {"type": "array", "items": {"enum": [1, 2]}, "uniqueItems": True}}})
        self.assertEqual(v.errors({"n": 1, "s": "abc", "l": [1, 2]}), [])
        self.assertTrue(v.errors({}))
        self.assertTrue(v.errors({"n": 0}))
        self.assertTrue(v.errors({"n": True}))  # booleans are not integers
        self.assertTrue(v.errors({"n": 1, "s": "b"}))
        self.assertTrue(v.errors({"n": 1, "l": [1, 1]}))
        self.assertTrue(v.errors({"n": 1, "l": [3]}))
        self.assertTrue(v.errors({"n": 1, "x": 1}))

    @unittest.skipIf(reference_jsonschema is None, "reference jsonschema package not installed")
    def test_agrees_with_reference_implementation(self):
        """Independent cross-check: every fixture document gets the same
        valid/invalid schema verdict from the reference validator."""
        checked = 0
        for name, schema_file in (("pass", "pass.schema.json"), ("hardware", "hardware.schema.json"),
                                  ("package", "game-package.schema.json")):
            cases = load_cases(name)
            base_doc = self._base_doc(name, cases)
            schema = json.loads((SCHEMA_DIR / schema_file).read_text())
            ref = reference_jsonschema.Draft202012Validator(schema)
            for case in cases["negative"] + cases["positive"]:
                with tempfile.TemporaryDirectory() as tmp:
                    doc = apply_ops(copy.deepcopy(base_doc), Path(tmp), case["ops"])
                ours = not schema_validator(schema_file).errors(doc)
                theirs = ref.is_valid(doc)
                self.assertEqual(ours, theirs, "%s/%s" % (name, case["id"]))
                checked += 1
        for p in [ROOT / "tools/lock/toolchain.lock.json"]:
            schema = json.loads((SCHEMA_DIR / "toolchain-lock.schema.json").read_text())
            self.assertTrue(reference_jsonschema.Draft202012Validator(schema).is_valid(json.loads(p.read_text())))
        self.assertGreater(checked, 30)

    @staticmethod
    def _base_doc(name, cases):
        if name == "pass":
            return json.loads((FIX / "pass" / cases["base"] / "pass.json").read_text())
        base = (FIX / name / cases["base"]).resolve()
        if name == "package":
            base = base / "arc1.game.json"
        return json.loads(base.read_text())


class LockAndPolicyTests(unittest.TestCase):
    def test_lock_valid(self):
        lock = json.loads((ROOT / "tools/lock/toolchain.lock.json").read_text())
        self.assertEqual(schema_validator("toolchain-lock.schema.json").errors(lock), [])

    def test_protected_policy_covers_schemas_and_goldens(self):
        pats = json.loads((ROOT / "policy/protected_paths.json").read_text())["protected"]
        import fnmatch
        for path in ("sdk/schemas/pass.schema.json", "examples/hello_arc1/tests/golden/steer.json",
                     "hardware/manifests/arc1-r10.hw.json", "AGENTS.md"):
            self.assertTrue(any(fnmatch.fnmatch(path, p) for p in pats), path)


class HardwareManifestTests(unittest.TestCase):
    def test_shipped_manifests_valid(self):
        for p in sorted(hardware.MANIFEST_DIR.glob("*.json")):
            self.assertEqual(hardware.check_manifest(json.loads(p.read_text())), [], p.name)

    def test_memory_pools_independent_and_total(self):
        doc = json.loads(hardware.DEFAULT_BOARD.read_text())
        s = hardware.summarize(doc)
        self.assertEqual(s["memory_total_bytes"], 228 * 1024 * 1024)
        self.assertFalse(s["unified_address_space"])
        self.assertEqual(doc["claims"]["physical_boot"], "not_tested")
        self.assertIn("f133.power_domain", s["unknown_safety_critical"])

    def test_cases(self):
        cases = load_cases("hardware")
        base = json.loads((FIX / "hardware" / cases["base"]).resolve().read_text())
        for case in cases["negative"]:
            with self.subTest(case=case["id"]):
                doc = apply_ops(copy.deepcopy(base), None, case["ops"])
                self.assertIn(case["expect"], codes(hardware.check_manifest(doc)))
        for case in cases["positive"]:
            with self.subTest(case=case["id"]):
                doc = apply_ops(copy.deepcopy(base), None, case["ops"])
                self.assertEqual(hardware.check_manifest(doc), [])

    def test_cli_rejects_corrupted_manifest(self):
        """Required deliverable: corrupt a manifest and show non-zero failing validation."""
        code, data = arc1_json("hw", "inspect")
        self.assertEqual((code, data["verdict"], data["evidence_level"]), (0, "PASS", "DESIGN"))
        with tempfile.TemporaryDirectory() as tmp:
            doc = json.loads(hardware.DEFAULT_BOARD.read_text())
            doc["chips"][0]["memory"][0]["shared_address_space"] = True
            bad = Path(tmp) / "corrupt.hw.json"
            bad.write_text(json.dumps(doc))
            code, data = arc1_json("hw", "inspect", "--manifest", bad)
            self.assertEqual((code, data["verdict"]), (1, "FAIL"))
            self.assertIn("HW-002", [f["code"] for f in data["failure_reasons"]])
            bad.write_text("{ not json")
            code, _, err = arc1("hw", "inspect", "--manifest", bad)
            self.assertEqual(code, 2)
            self.assertIn("not valid JSON", err)

    def test_cli_chip_query(self):
        code, data = arc1_json("hw", "inspect", "--chip", "gpu45")
        self.assertEqual(code, 0)
        chip = data["details"]["facts"]["chip"]
        self.assertEqual(chip["part"], "LFE5U-45F-6BG381C")
        self.assertEqual(data["details"]["facts"]["links"][0]["state"], "proposed_unverified")


class PackageManifestTests(unittest.TestCase):
    def test_cases(self):
        cases = load_cases("package")
        for case in cases["negative"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp) / "p"
                shutil.copytree(HELLO, dest, ignore=shutil.ignore_patterns("build", "reports"))
                doc = apply_ops(json.loads((dest / "arc1.game.json").read_text()), dest, case["ops"])
                found = codes(project.check_package(project.Project(dest), doc))
                self.assertIn(case["expect"], found)

    def test_shipped_package_valid(self):
        p = project.Project(HELLO)
        self.assertEqual(project.check_package(p, p.manifest()), [])


class AssetTests(unittest.TestCase):
    def test_parse(self):
        w, h, px = assets.parse_sprite("size 2 1\n.f\n")
        self.assertEqual((w, h, px), (2, 1, [0, 15]))

    def test_rejects_malformed(self):
        for text in ("2 1\n..\n", "size 2 1\n...\n", "size 2 1\n.g\n", "size 2 2\n..\n", "size 65 1\n"):
            with self.subTest(text=text), self.assertRaises(assets.AssetError):
                assets.parse_sprite(text)


# --------------------------------------------------------------------- pass records (M3 preview)

class PassValidatorTests(unittest.TestCase):
    def _run(self, ops):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "fx"
            shutil.copytree(FIX / "pass" / "complete", dest)
            doc = json.loads((dest / "pass.json").read_text())
            doc = apply_ops(doc, dest, ops)
            return passrec.check_pass(doc, dest, dest / "pass.json", git_checks=False)

    def test_complete_fixture_passes(self):
        findings, _ = self._run([])
        self.assertEqual(findings, [])

    def test_negative_cases(self):
        cases = load_cases("pass")
        self.assertGreaterEqual(len(cases["negative"]), 15)
        for case in cases["negative"]:
            with self.subTest(case=case["id"]):
                findings, _ = self._run(case["ops"])
                self.assertIn(case["expect"], codes(findings), findings)

    def test_positive_cases(self):
        for case in load_cases("pass")["positive"]:
            with self.subTest(case=case["id"]):
                findings, _ = self._run(case["ops"])
                self.assertEqual(findings, [])

    def test_cli_exit_codes(self):
        fx = FIX / "pass" / "complete"
        code, data = arc1_json("pass", "validate", fx, "--root", fx, "--no-git")
        self.assertEqual((code, data["verdict"]), (0, "PASS"))
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "fx"
            shutil.copytree(fx, dest)
            doc = json.loads((dest / "pass.json").read_text())
            doc["sdk_change"]["acceptance_tests"] = ["missing"]
            (dest / "pass.json").write_text(json.dumps(doc))
            code, data = arc1_json("pass", "validate", dest, "--root", dest, "--no-git")
            self.assertEqual((code, data["verdict"]), (1, "FAIL"))

    @unittest.skipIf(shutil.which("git") is None, "git not installed")
    def test_unknown_base_commit_rejected(self):
        top = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT,
                             stdout=subprocess.PIPE).stdout.decode().strip()
        if top != "false":
            self.skipTest("not a full git clone")
        findings, _ = self._run([{"op": "set", "path": "/base_commit", "value": "f" * 40}])
        self.assertEqual(findings, [])  # git checks are off in _run
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "fx"
            shutil.copytree(FIX / "pass" / "complete", dest)
            doc = json.loads((dest / "pass.json").read_text())
            doc["base_commit"] = "f" * 40
            findings, _ = passrec.check_pass(doc, dest, dest / "pass.json", git_checks=True)
            self.assertIn("PASS-002", codes(findings))

    def test_repository_pass_records_validate(self):
        records = sorted((ROOT / "passes").glob("ARC1-PASS-*/pass.json"))
        self.assertTrue(records)
        for rec in records:
            with self.subTest(record=rec.parent.name):
                doc = json.loads(rec.read_text())
                findings, _ = passrec.check_pass(doc, ROOT, rec, git_checks=False)
                self.assertEqual(findings, [])


# --------------------------------------------------------------------- G1 host SDK

class CliContractTests(unittest.TestCase):
    def test_help_and_version(self):
        for args in ([], ["doctor"], ["new"], ["build"], ["sim"], ["test"], ["hw", "inspect"],
                     ["pass", "validate"], ["fpga", "check"], ["device", "deploy"]):
            code, out, _ = arc1(*(args + ["--help"]))
            self.assertEqual(code, 0, args)
            self.assertIn("usage: arc1", out)
            if args:
                self.assertIn("Exit codes", out)
        code, out, _ = arc1("--version")
        self.assertEqual(code, 0)
        self.assertRegex(out, r"^arc1 \S+ \(schema 0\.2\)")

    def test_usage_error_exit_code(self):
        self.assertEqual(arc1("sim", "--frames", "0")[0], 2)
        self.assertEqual(arc1("no-such-command")[0], 2)
        self.assertEqual(arc1("build", "/nonexistent/project")[0], 2)

    def test_device_deploy_never_simulates_success(self):
        code, data = arc1_json("device", "deploy", HELLO)
        self.assertEqual((code, data["verdict"], data["evidence_level"], data["board_id"]),
                         (3, "NOT_AVAILABLE", "NONE", None))
        self.assertEqual(data["artifacts"], [])

    def test_fpga_check_not_run(self):
        code, data = arc1_json("fpga", "check")
        self.assertEqual((code, data["verdict"]), (3, "NOT_RUN"))

    def test_doctor(self):
        code, data = arc1_json("doctor")
        self.assertEqual(code, 0, data["failure_reasons"])
        statuses = {c["check"]: c["status"] for c in data["details"]["checks"]}
        self.assertEqual(statuses["physical_board"], "NOT_AVAILABLE")
        self.assertEqual(statuses["c_compiler"], "ok")

    def test_json_flag_before_subcommand(self):
        code, out, _ = arc1("--json", "fpga", "check")
        self.assertEqual(json.loads(out)["verdict"], "NOT_RUN")

    def test_result_contract_rejects_missing_artifact(self):
        r = Result("arc1 test", "HOST_SIM")
        r.artifact(ROOT / "does-not-exist.txt")
        data = r.to_dict()
        self.assertEqual(data["verdict"], "FAIL")
        self.assertEqual(data["failure_reasons"][0]["code"], "CLI-001")


class HostSdkTests(unittest.TestCase):
    """hello_arc1 end to end, plus the ways the golden tests must fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.proj = Path(cls.tmp.name) / "hello_arc1"
        shutil.copytree(HELLO, cls.proj, ignore=shutil.ignore_patterns("build", "reports"))
        code, data = arc1_json("build", cls.proj)
        assert code == 0, data

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def fresh_copy(self):
        dest = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "hello_arc1"
        shutil.copytree(self.proj, dest)
        return dest

    def test_golden_suite_passes_and_is_reproducible(self):
        code, first = arc1_json("test", self.proj)
        self.assertEqual(code, 0, first["failure_reasons"])
        self.assertEqual((first["test_count"], first["failed_count"]), (4, 0))
        self.assertIn("Physical ARC-1 was not used", first["warnings"])
        report1 = (self.proj / "reports" / "test.json").read_bytes()
        arc1_json("test", self.proj)
        self.assertEqual(report1, (self.proj / "reports" / "test.json").read_bytes())

    def test_sim_produces_frames(self):
        code, data = arc1_json("sim", self.proj, "--frames", "30", "--dump", "0,29")
        self.assertEqual(code, 0)
        self.assertEqual(data["evidence_level"], "HOST_SIM")
        ppms = [a for a in data["artifacts"] if a["path"].endswith(".ppm")]
        self.assertEqual(len(ppms), 2)
        self.assertTrue(data["details"]["hardware_descriptor"]["simulation_only"])

    def test_tampered_golden_trace_fails(self):
        p = self.fresh_copy()
        g = p / "tests/golden/steer.trace"
        lines = g.read_text().splitlines()
        lines[57] = lines[57][:-1] + ("0" if lines[57][-1] != "0" else "1")
        g.write_text("\n".join(lines) + "\n")
        code, data = arc1_json("test", p)
        self.assertEqual(code, 1)
        self.assertIn("does not match its recorded digest", json.dumps(data["failure_reasons"]))

    def test_behaviour_change_reports_divergent_frame(self):
        p = self.fresh_copy()
        src = p / "src/main.c"
        src.write_text(src.read_text().replace("y -= 2;", "y -= 3;"))
        code, data = arc1_json("test", p)
        self.assertEqual((code, data["failure_reasons"][0]["code"]), (1, "BUILD_STALE"))
        self.assertEqual(arc1_json("build", p)[0], 0)
        code, data = arc1_json("test", p)
        self.assertEqual(code, 1)
        text = json.dumps(data["failure_reasons"])
        self.assertIn("steer-golden", text)
        self.assertIn("first divergent frame 10", text)  # UP is first held at frame 10
        self.assertNotIn("idle-golden", text)

    def test_changed_replay_without_new_golden_fails(self):
        p = self.fresh_copy()
        (p / "tests/replays/steer.replay").write_text("0 NONE\n10 DOWN\n")
        code, data = arc1_json("test", p, "--only", "steer-golden")
        self.assertEqual(code, 1)
        self.assertIn("replay input differs", json.dumps(data["failure_reasons"]))

    def test_negative_control_detects_blind_golden(self):
        p = self.fresh_copy()
        plan = json.loads((p / "tests/arc1.tests.json").read_text())
        for t in plan["tests"]:
            if t["kind"] == "must_differ":
                t["golden"] = "tests/golden/idle.json"
                t["frames"] = 180
        (p / "tests/arc1.tests.json").write_text(json.dumps(plan))
        code, data = arc1_json("test", p, "--only", "input-reaches-frames")
        self.assertEqual(code, 1)
        self.assertIn("negative control", json.dumps(data["failure_reasons"]))

    def test_update_golden_is_flagged_sensitive(self):
        p = self.fresh_copy()
        code, data = arc1_json("test", p, "--update-golden", "--only", "idle-golden")
        self.assertEqual(code, 0)
        self.assertTrue(any("TST-003" in w for w in data["warnings"]))
        self.assertEqual(data["details"]["sensitive_events"], ["tests/golden/idle.json"])

    def test_sim_requires_build(self):
        p = self.fresh_copy()
        shutil.rmtree(p / "build")
        code, data = arc1_json("sim", p)
        self.assertEqual((code, data["failure_reasons"][0]["code"]), (1, "BUILD_STALE"))

    def test_replay_path_cannot_escape_project(self):
        code, _, err = arc1("sim", self.proj, "--replay", "../../../etc/hostname")
        self.assertEqual(code, 2)
        self.assertIn("escapes", err)

    def test_compilers_agree(self):
        """Same frames from every available locked compiler (host determinism)."""
        traces = {}
        for cc in ("gcc", "clang"):
            if shutil.which(cc) is None:
                continue
            p = self.fresh_copy()
            env = {"ARC1_CC": cc}
            self.assertEqual(arc1_json("build", p, env=env)[0], 0)
            code, data = arc1_json("sim", p, "--replay", "tests/replays/steer.replay", env=env)
            self.assertEqual(code, 0)
            traces[cc] = data["details"]["trace_sha256"]
        if len(traces) < 2:
            self.skipTest("needs both gcc and clang")
        self.assertEqual(len(set(traces.values())), 1, traces)


class NewProjectTests(unittest.TestCase):
    def test_new_build_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, data = arc1_json("new", "demo", "--dir", tmp)
            self.assertEqual(code, 0, data["failure_reasons"])
            demo = Path(tmp) / "demo"
            self.assertEqual(json.loads((demo / "arc1.game.json").read_text())["name"], "demo")
            self.assertEqual(arc1_json("build", demo)[0], 0)
            code, data = arc1_json("test", demo)
            self.assertEqual(code, 0, data["failure_reasons"])
            self.assertEqual(data["test_count"], 3)
            self.assertEqual(arc1("new", "demo", "--dir", tmp)[0], 2)  # refuses to overwrite

    def test_bad_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("Demo", "1demo", "../x", "a" * 40):
                self.assertEqual(arc1("new", name, "--dir", tmp)[0], 2, name)


class ConformanceTests(unittest.TestCase):
    def test_c_api_conformance(self):
        cc, _ = find_cc()
        if cc is None:
            self.skipTest("no C compiler")
        lock = json.loads((ROOT / "tools/lock/toolchain.lock.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "conformance"
            subprocess.run([cc, "-std=c11"] + lock["c_compiler"]["flags"] +
                           ["-I", str(ROOT / "sdk/include"), str(ROOT / "tests/conformance/api_conformance.c"),
                            str(ROOT / "sdk/runtime/host/arc1_host.c"), "-o", str(exe)], check=True)
            p = subprocess.run([str(exe), "--frames", "2"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out = p.stdout.decode()
            self.assertIn("CONFORMANCE OK", out, out)
            # The test deliberately misuses the lifecycle; the harness must notice.
            self.assertEqual(p.returncode, 70, p.stderr.decode())
            bad = Path(tmp) / "bad.replay"
            bad.write_text("0 JUMP\n")
            self.assertEqual(subprocess.run([str(exe), "--replay", str(bad)],
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode, 66)
            bad.write_text("5 A\n3 B\n")
            self.assertEqual(subprocess.run([str(exe), "--replay", str(bad)],
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode, 66)


if __name__ == "__main__":
    unittest.main(verbosity=2)
