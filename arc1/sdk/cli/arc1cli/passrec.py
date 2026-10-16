"""`arc1 pass validate`: the SDK Evolution Covenant and pass-protocol checker.

Implements the checks sketched in Appendix A.2 of ARC1-SDK-ER-002 v0.2.
Every finding carries the requirement code it enforces. A PASS verdict means
"the record is complete and consistent for its declared state, and its
evidence files match their digests" — never that hardware works.

A committed, unmodified pass record is checked against the commit that last
recorded it, so later passes cannot retroactively break it. An uncommitted or
locally edited record (or --no-git) is checked against the working tree.
"""

import fnmatch
import hashlib
import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from .core import (LOCK_FILE, SCHEMA_REVISION, SDK_ROOT, UsageError, bounded, digest_files,
                   display_path, load_json, schema_validator, scrubbed_env, sha256_file)

POLICY_FILE = SDK_ROOT / "policy" / "protected_paths.json"
STATES_WITH_RESULTS = ("VERIFYING", "REVIEW", "COMPLETE")
COVENANT_SHARE = Fraction(5, 100)


def _git_raw(args, cwd):
    git = shutil.which("git")
    if not git:
        return None, "git not available"
    try:
        p = subprocess.run([git] + args, cwd=str(cwd), env=scrubbed_env(), timeout=30,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    if p.returncode != 0:
        return None, p.stderr.decode("utf-8", "replace").strip()
    return p.stdout, None


def _git(args, cwd):
    out, err = _git_raw(args, cwd)
    return (out.decode("utf-8", "replace") if out is not None else None), err


class Tree:
    """Read-only view of files under root: the working tree, or a commit."""

    def __init__(self, root, commit=None, top=None):
        self.root = Path(root).resolve()
        self.commit = commit
        self.top = top

    def _spec(self, path):
        return "%s:%s" % (self.commit, path.relative_to(self.top).as_posix())

    def exists(self, rel, what="path"):
        p = bounded(self.root, rel, what)
        if self.commit is None:
            return p.exists()
        return _git_raw(["cat-file", "-e", self._spec(p)], self.top)[1] is None

    def read(self, rel, what="path"):
        """Bytes of a file, or None if it is absent."""
        p = bounded(self.root, rel, what)
        if self.commit is None:
            return p.read_bytes() if p.is_file() else None
        out, err = _git_raw(["show", self._spec(p)], self.top)
        return out if err is None else None


def _open_tree(root, record_path, warnings):
    """Returns (tree, git top-level or None)."""
    top, err = _git(["rev-parse", "--show-toplevel"], SDK_ROOT)
    if top is None:
        warnings.append("git checks not run: %s" % err)
        warnings.append("without git history the record is checked against the current files; an earlier pass "
                        "whose artifacts later passes changed will fail here, so check it from a git clone")
        return Tree(root), None
    top = Path(top.strip()).resolve()
    record = str(Path(record_path).resolve())
    log, _ = _git(["log", "-1", "--format=%H", "--", record], top)
    dirty, _ = _git(["status", "--porcelain", "--", record], top)
    root = Path(root).resolve()
    if log and log.strip() and dirty is not None and not dirty.strip() \
            and (root == top or top in root.parents):
        return Tree(root, log.strip(), top), top
    return Tree(root), top


def _protected_patterns():
    return load_json(POLICY_FILE, "protected path policy")["protected"]


def check_pass(doc, root, record_path, git_checks=True):
    """Returns (findings, warnings). findings: list of (code, pointer, message)."""
    errs = [("SCHEMA", p, m) for p, m in schema_validator("pass.schema.json").errors(doc)]
    if errs:
        return errs, []
    warnings = []
    f = errs.append
    state = doc["state"]
    if git_checks:
        tree, top = _open_tree(root, record_path, warnings)
    else:
        tree, top = Tree(root), None
        warnings.append("git checks skipped (--no-git): base commit and protected-path disclosure not verified")
    if tree.commit:
        warnings.append("checked as recorded at commit %s" % tree.commit[:12])

    # PASS-002 immutable input reference.
    if doc["inputs"]["sdk_schema"] != SCHEMA_REVISION:
        f(("PASS-002", "/inputs/sdk_schema", "record targets schema %s, validator is %s"
           % (doc["inputs"]["sdk_schema"], SCHEMA_REVISION)))
    if doc["inputs"]["toolchain_lock_sha256"] != sha256_file(LOCK_FILE):
        warnings.append("PASS-002: toolchain lock differs from the one this pass declared")

    # COV-001 budget declaration, COV-006 deferral.
    effort = doc["effort"]
    planned = Fraction(str(effort["planned_total"]))
    reserved = Fraction(str(effort["sdk_reserved"]))
    deferral = doc["deferral"]
    if reserved < COVENANT_SHARE * planned:
        if deferral is None:
            f(("COV-001", "/effort/sdk_reserved", "SDK allocation %s is below 5%% of planned total %s"
               % (effort["sdk_reserved"], effort["planned_total"])))
        elif not deferral["approved_by"]:
            f(("COV-006", "/deferral/approved_by", "a deferral needs a recorded approver; unapproved omissions fail"))
        elif deferral["approved_by"] == doc["owner"]:
            f(("COV-006", "/deferral/approved_by", "the pass owner cannot approve their own deferral"))
        else:
            warnings.append("COV-006: SDK work deferred (%s units) until %s"
                            % (deferral["deferred_units"], deferral["remediation"]["due"]))
    if effort["actual_sdk"] is not None and effort["actual_total"] is not None \
            and effort["actual_sdk"] > effort["actual_total"]:
        f(("COV-001", "/effort/actual_sdk", "actual SDK effort exceeds actual total"))

    # COV-002 / COV-004 artifact requirement.
    sdk = doc["sdk_change"]
    if deferral is None:
        if not sdk["reusable"]:
            f(("COV-002", "/sdk_change/reusable", "the SDK change must be reusable beyond this feature"))
        names = [Path(p).name.upper() for p in sdk["paths"]]
        if all(n.startswith(("CHANGELOG", "HISTORY", "NEWS")) for n in names):
            f(("COV-004", "/sdk_change/paths", "a changelog edit alone is not an SDK improvement"))
        if set(sdk["paths"]) <= set(doc["main_change"]["paths"]):
            f(("COV-002", "/sdk_change/paths", "SDK change must be separately identifiable from the main change"))
    for i, rel in enumerate(sdk["paths"] + doc["main_change"]["paths"]):
        ptr = "/sdk_change/paths" if i < len(sdk["paths"]) else "/main_change/paths"
        try:
            if not tree.exists(rel, "changed path"):
                f(("COV-002", ptr, "changed path does not exist: %s" % rel))
        except UsageError as e:
            f(("CLI-003", ptr, str(e)))

    # PASS-004 evidence record; contradiction checks (section 4.1, CLI-002).
    ids = {}
    for i, v in enumerate(doc["validation"]):
        where = "/validation/%d" % i
        if v["id"] in ids:
            f(("PASS-004", where + "/id", "duplicate validation id %r" % v["id"]))
        ids[v["id"]] = v
        executed = v["result"] in ("pass", "fail")
        if executed:
            if not v["command"]:
                f(("PASS-004", where + "/command", "an executed check must record its command"))
            if not v["report"]:
                f(("PASS-004", where + "/report", "an executed check must preserve its report"))
            if v["reason"]:
                warnings.append("%s: reason given for an executed check" % v["id"])
        elif not v["reason"]:
            f(("PASS-004", where + "/reason", "%s checks must state why" % v["result"]))
        if v["level"] == "BOARD_TEST" and executed and not (v["board_id"] and v["equipment"]):
            f(("CLI-002", where, "a BOARD_TEST result requires board_id and equipment"))
        if v["level"] != "BOARD_TEST" and (v["board_id"] or v["equipment"]):
            f(("CLI-002", where, "board_id/equipment given for a non-board evidence level"))
        if v["report"]:
            _check_report(v, where, tree, f)

    # COV-002 acceptance evidence for the SDK change.
    if state in STATES_WITH_RESULTS and deferral is None:
        for t in sdk["acceptance_tests"]:
            v = ids.get(t)
            if v is None:
                f(("COV-002", "/sdk_change/acceptance_tests", "acceptance test %r is not in validation" % t))
            elif v["result"] != "pass":
                f(("COV-002", "/sdk_change/acceptance_tests", "acceptance test %r did not pass" % t))
    if state == "COMPLETE":
        for i, v in enumerate(doc["validation"]):
            if v["result"] == "fail":
                f(("PASS-004", "/validation/%d/result" % i, "COMPLETE pass has a failing check"))

    # Artifact digests (PASS-004, REP-003).
    for i, a in enumerate(doc["artifacts"]):
        _check_digest(a, "/artifacts/%d" % i, tree, f)

    # COV-003 independent gates.
    review = doc["review"]
    if review["sdk_accepted_by"] and review["sdk_accepted_by"] == doc["owner"]:
        f(("COV-003", "/review/sdk_accepted_by", "the owner cannot accept their own SDK change"))
    if review["state"] == "accepted" and not (review["sdk_accepted_by"] and review["evidence"]):
        f(("COV-003", "/review", "accepted review needs reviewer identity and evidence"))
    if review["state"] != "accepted" and review["sdk_accepted_by"]:
        f(("COV-003", "/review", "reviewer named but review state is %s" % review["state"]))
    if state == "COMPLETE" and review["state"] != "accepted":
        f(("COV-003", "/review/state", "COMPLETE requires an accepted independent review"))
    if state == "REVIEW" and review["state"] == "pending":
        warnings.append("COV-003: awaiting independent review; the owner cannot self-accept")

    # Blockers.
    if state == "BLOCKED" and not doc["blockers"]:
        f(("PASS-005", "/blockers", "BLOCKED pass must list blockers with a recovery action"))
    if state == "COMPLETE" and doc["blockers"]:
        f(("PASS-005", "/blockers", "COMPLETE pass still lists blockers"))

    # PASS-005 reproducible handoff.
    try:
        data = tree.read(doc["handoff"], "handoff path")
        if data is None or b"## Reproduce" not in data:
            f(("PASS-005", "/handoff", "handoff missing or lacks a '## Reproduce' section"))
    except UsageError as e:
        f(("CLI-003", "/handoff", str(e)))

    # PASS-002 base commit, TST-003 / SEC-002 disclosure of sensitive changes.
    if top is not None:
        _git_checks(doc, top, tree.commit, f, warnings)
    return errs, warnings


def _check_digest(a, where, tree, f):
    try:
        data = tree.read(a["path"], "artifact path")
    except UsageError as e:
        f(("CLI-003", where, str(e)))
        return None
    if data is None:
        f(("PASS-004", where, "artifact missing: %s" % a["path"]))
        return None
    if hashlib.sha256(data).hexdigest() != a["sha256"]:
        f(("PASS-004", where, "digest mismatch for %s" % a["path"]))
        return None
    return data


def _check_report(v, where, tree, f):
    data = _check_digest(v["report"], where + "/report", tree, f)
    if data is None or not v["report"]["path"].endswith(".json"):
        return
    try:
        rep = json.loads(data.decode("utf-8"))
    except ValueError:
        f(("PASS-004", where + "/report", "report is not valid JSON"))
        return
    if not isinstance(rep, dict) or rep.get("schema_version") != "arc1.tool-result/0.2":
        return  # foreign evidence: digest checked, content not interpreted
    errs = schema_validator("tool-result.schema.json").errors(rep)
    if errs:
        f(("CLI-001", where + "/report", "report violates tool-result schema: %s" % (errs[0],)))
        return
    if rep["evidence_level"] != v["level"]:
        f(("CLI-002", where + "/level", "record claims %s but report evidence is %s"
           % (v["level"], rep["evidence_level"])))
    expect = {"pass": "PASS", "fail": "FAIL", "not_available": "NOT_AVAILABLE", "not_run": "NOT_RUN"}[v["result"]]
    if rep["verdict"] != expect:
        f(("PASS-004", where + "/result", "record says %s but report verdict is %s" % (v["result"], rep["verdict"])))


def _git_checks(doc, top, end_commit, f, warnings):
    base = doc["base_commit"]
    if _git(["cat-file", "-e", base + "^{commit}"], top)[1] is not None:
        shallow, _ = _git(["rev-parse", "--is-shallow-repository"], top)
        if (shallow or "").strip() == "true":
            warnings.append("PASS-002: base commit not in this shallow clone; not verified")
        else:
            f(("PASS-002", "/base_commit", "base commit %s is not in this repository" % base))
        return
    # Paths relative to the SDK root, where the protected-path policy applies.
    end = [end_commit] if end_commit else []
    out, err = _git(["diff", "--name-status", "--no-renames", "--relative", base] + end + ["--", "."], SDK_ROOT)
    if out is None:
        warnings.append("TST-003 disclosure check not run: %s" % err)
        return
    patterns = _protected_patterns()
    disclosed = {s["path"] for s in doc["sensitive_changes"]}
    for line in out.splitlines():
        status, _, rel = line.partition("\t")
        if status not in ("M", "D", "T"):
            continue  # additions do not reduce an existing baseline
        if any(fnmatch.fnmatch(rel, pat) for pat in patterns) and rel not in disclosed:
            f(("TST-003", "/sensitive_changes", "undisclosed %s of protected file %s"
               % ("deletion" if status == "D" else "modification", rel)))


def validate(result, record_arg, root_arg=None, git_checks=True):
    record = Path(record_arg)
    if record.is_dir():
        record = record / "pass.json"
    record = record.resolve()
    root = Path(root_arg).resolve() if root_arg else SDK_ROOT
    result.command = "arc1 pass validate %s" % display_path(record)
    doc = load_json(record, "pass record")
    result.input_digest = digest_files(record.parent, [p for p in record.parent.rglob("*") if p.is_file()])
    errs, warnings = check_pass(doc, root, record, git_checks)
    for code, ptr, msg in errs:
        result.fail(code, "%s: %s" % (ptr, msg), display_path(record))
    for w in warnings:
        result.warn(w)
    result.warn("Pass validation is STATIC_CHECK evidence; it does not assert physical hardware")
    if isinstance(doc, dict):
        result.extra["details"] = {"pass_id": doc.get("pass_id"), "state": doc.get("state"),
                                   "findings": len(errs)}
