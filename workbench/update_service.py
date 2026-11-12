"""Approve/stage, close desktop, apply, verify, and restore the last good files."""

import json, os, shutil, subprocess, sys, time
from .engineering_kernel import KernelError, digest


def stage(k, id, p):
    with k.db() as db:
        db.execute("BEGIN IMMEDIATE")
        c = k.record("candidates", id)
        if c["state"] != "Waiting for Approval":
            raise KernelError("Candidate must be submitted for review")
        k.validate_promotion(c)
        dest = k.state / "updates" / id / "staged"
        dest.mkdir(parents=True, exist_ok=True)
        for name, sha in c["changes"].items():
            src = k.safe(name, k.candidate_root(id))
            target = dest / name
            if digest(src.read_bytes()) != sha:
                raise KernelError("Candidate changed after review")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
        c.update(state="Staged", staged_by=p.identity, staged_at=time.time())
        k.save("candidates", c, db)
    return {
        "id": id,
        "state": "Staged",
        "next": "Close Graphite, then python -m workbench.engineering_cli --operator apply-update "
        + id,
        "accepted_source_unchanged": True,
    }


def ensure_closed(k):
    for lease in (k.state / "desktops").glob("*.json"):
        try:
            pid = json.loads(lease.read_text())["pid"]
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        except (ValueError, KeyError):
            raise KernelError(
                "Unreadable desktop lease; verify no running application before recovery"
            )
        raise KernelError("Close the running Graphite desktop before applying an update")
    if any(j["state"] in ("Running", "Queued") for j in k.listing("jobs")):
        raise KernelError(
            "Finish or cancel active engineering jobs before application replacement"
        )


def apply_staged(k, id, p):
    if "approve" not in p.scopes:
        raise KernelError("Operator authority required")
    ensure_closed(k)
    with k.db() as db:
        db.execute("BEGIN IMMEDIATE")
        c = k.record("candidates", id)
        if c["state"] != "Staged":
            raise KernelError("No approved staged update")
        k.validate_promotion(c)
        for name, sha in c["changes"].items():
            src = k.safe(name, k.state / "updates" / id / "staged")
            if digest(src.read_bytes()) != sha:
                raise KernelError("Staged update checksum mismatch")
        for name in c["changes"]:
            target = k.safe(name, must_exist=False)
            backup = k.state / "candidates" / id / "backup" / name
            backup.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.copy2(target, backup)
        (k.state / "recovery.json").write_text(json.dumps(c), encoding="utf-8")
        try:
            for name in c["changes"]:
                target = k.safe(name, must_exist=False)
                target.parent.mkdir(parents=True, exist_ok=True)
                tmp = target.with_name(target.name + ".ledger-tmp")
                shutil.copy2(k.state / "updates" / id / "staged" / name, tmp)
                os.replace(tmp, target)
        except OSError:
            k.restore(c)
            raise
        c["state"] = "Verifying"
        k.save("candidates", c, db)
    reports = []
    success = True
    try:
        for module in ("tests.test_ledger13_kernel", "tests.test_r10_workbench"):
            env = dict(os.environ)
            env["QT_QPA_PLATFORM"] = "offscreen"
            command = [sys.executable, "-m", "unittest", module]
            proc = subprocess.run(
                command,
                cwd=k.root,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            reports.append(
                {
                    "command": command,
                    "exit_status": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                }
            )
            if proc.returncode:
                success = False
                break
    except Exception as exc:
        success = False
        reports.append({"error": str(exc)})
    with k.db() as db:
        db.execute("BEGIN IMMEDIATE")
        if success:
            c.update(state="Accepted", approved_by=p.identity, accepted_at=time.time())
        else:
            k.restore(c)
            c["state"] = "Rolled Back"
        c["update_verification"] = reports
        k.save("candidates", c, db)
    (k.state / "recovery.json").unlink(missing_ok=True)
    k.audit(p.identity, "update.apply", c["state"])
    return {
        "id": id,
        "state": c["state"],
        "verification": reports,
        "last_known_good": str(k.state / "candidates" / id / "backup"),
    }
