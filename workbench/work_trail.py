"""Private work metadata over the existing Kernel, jobs and evidence."""
from __future__ import annotations
from contextvars import ContextVar
import json
import hashlib
import os
import re
import sqlite3
import time
import threading
from sdk.cli.arc1cli import work_trail as c
from sdk.cli.arc1cli.host_cpu import HostCpuSampler
from sdk.cli.arc1cli.job_evidence import describe
from . import activity, record_access, record_io as io, operation_priority

FIELDS = {
    "ledger.trail.list": ({"limit": {"type": "integer", "minimum": 1, "maximum": 50}}, []),
    "ledger.trail.inspect": ({"id": {"type": "string", "minLength": 32, "maxLength": 32}}, ["id"]),
    "ledger.trail.job": ({"id": {"type": "string", "minLength": 32, "maxLength": 32}}, ["id"]),
    "ledger.resources": ({}, []), "ledger.resources.observation": ({}, []),
    "ledger.work.status": ({}, []), "ledger.work.resume": ({}, []),
}
SCOPES = {op: "approve" if op == "ledger.work.resume" else "read" for op in FIELDS}
_CURRENT = ContextVar("ledger_work_trail", default=())
_GAPS = {}
_CPU = {}
_CPU_LOCK = threading.Lock()


def ensure(db):
    db.execute("CREATE TABLE IF NOT EXISTS ledger_trail(id TEXT PRIMARY KEY,owner TEXT,payload TEXT,sha256 TEXT)")
    db.execute("CREATE INDEX IF NOT EXISTS ledger_trail_owner ON ledger_trail(owner)")
    db.execute("CREATE TABLE IF NOT EXISTS ledger_trail_jobs(intent TEXT,job TEXT,PRIMARY KEY(intent,job))")
    db.execute("CREATE TABLE IF NOT EXISTS ledger_trail_counts(owner TEXT PRIMARY KEY,seen INTEGER,pruned INTEGER,dropped INTEGER)")
    db.execute("CREATE INDEX IF NOT EXISTS ledger_trail_gap_events ON activity_journal(json_extract(payload,'$.operation'),json_extract(payload,'$.correlation_id'))")


def put(db, owner, row):
    raw = io.canonical(row)
    if len(raw) > 4096:
        raise ValueError("TRAIL_METADATA_LIMIT")
    db.execute("INSERT OR REPLACE INTO ledger_trail VALUES(?,?,?,?)", (row["id"], owner, raw.decode(), io.digest(row)))


def get(db, owner, ident):
    c.ident(ident)
    row = db.execute("SELECT payload,sha256 FROM ledger_trail WHERE id=? AND owner=?", (ident, owner)).fetchone()
    if not row or len(row[0].encode()) > 4096:
        raise ValueError("TRAIL_UNAVAILABLE")
    value = io.strict_json(row[0])
    if io.digest(value) != row[1]:
        raise ValueError("TRAIL_UNAVAILABLE")
    return value


def presented(row):
    if row["state"] in ("RECEIVED", "DISPATCHING"):
        from .operation_stop import process_identity, UNKNOWN
        token = process_identity(row.get("pid"))
        if token not in (UNKNOWN, row.get("process_start")):
            return {**row, "state": "REQUEST_INTERRUPTED"}
    return row


def gap(kernel, owner):
    key = (str(kernel.root), owner)
    _GAPS[key] = _GAPS.get(key, 0) + 1
    if _GAPS[key] == 1:
        activity._failed(kernel.root, activity.make_event(owner, "ledger.trail", "GAP", correlation_id=hashlib.sha256(owner.encode()).hexdigest()), ValueError("Work-trail metadata delivery incomplete; reconcile before assuming complete history"))


def enter(kernel, operation, principal, ident, scope):
    # Passive reads never feed the recorder back into itself.
    if scope == "read":
        return None
    stack = _CURRENT.get()
    owner = principal.identity
    parent = next((x[2] for x in reversed(stack) if x[:2] == (str(kernel.root), owner)), None)
    from .operation_stop import process_identity
    row = {"id": ident, "operation": operation, "scope": scope, "created": time.time(),
           "state": "RECEIVED", "scope_check": "NOT_CHECKED", "parent": parent,
           "pid": os.getpid(), "process_start": process_identity(os.getpid())}
    try:
        with kernel.db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR IGNORE INTO ledger_trail_counts VALUES(?,0,0,0)", (owner,))
            count = db.execute("SELECT count(*) FROM ledger_trail WHERE owner=?", (owner,)).fetchone()[0]
            if count >= c.MAX_INTENTS:
                old = next(((r[0],) for r in db.execute("SELECT id,payload FROM ledger_trail WHERE owner=? ORDER BY rowid", (owner,))
                            if presented(io.strict_json(r[1]))['state'] not in ('RECEIVED','DISPATCHING')), None)
                if old:
                    db.execute("DELETE FROM ledger_trail_jobs WHERE intent=?", old)
                    db.execute("DELETE FROM ledger_trail WHERE id=?", old)
                    db.execute("UPDATE ledger_trail_counts SET pruned=pruned+1 WHERE owner=?", (owner,))
                else:
                    db.execute("UPDATE ledger_trail_counts SET dropped=dropped+1 WHERE owner=?", (owner,))
                    return None
            put(db, owner, row)
            db.execute("UPDATE ledger_trail_counts SET seen=seen+1 WHERE owner=?", (owner,))
    except (ValueError, OSError, sqlite3.Error):
        gap(kernel, owner)
        return None
    return _CURRENT.set((*stack, (str(kernel.root), owner, ident)))


def update(kernel, principal, state, scope_checked=False):
    current = next((x for x in reversed(_CURRENT.get()) if x[:2] == (str(kernel.root), principal.identity)), None)
    if not current:
        return
    try:
        with kernel.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = get(db, principal.identity, current[2])
            row["state"] = state
            if scope_checked:
                row["scope_check"] = "PASSED"
            elif state == "DENIED":
                row["scope_check"] = "DENIED"
            if state not in ("RECEIVED", "DISPATCHING"):
                row["returned"] = time.time()
            put(db, principal.identity, row)
    except (ValueError, OSError, sqlite3.Error):
        gap(kernel, principal.identity)


def leave(token):
    if token is not None:
        _CURRENT.reset(token)


def bind(db, kernel, owner, job):
    for root, actor, ident in _CURRENT.get()[-c.MAX_LINKS:]:
        if (root, actor) != (str(kernel.root), owner):
            continue
        if not db.execute("SELECT 1 FROM ledger_trail WHERE id=? AND owner=?", (ident, owner)).fetchone():
            continue
        count = db.execute("SELECT count(*) FROM ledger_trail_jobs WHERE intent=?", (ident,)).fetchone()[0]
        if count < c.MAX_LINKS:
            db.execute("INSERT OR IGNORE INTO ledger_trail_jobs VALUES(?,?)", (ident, job))


def work_status(kernel, db=None):
    def read(conn):
        row = conn.execute("SELECT value FROM settings WHERE key='ledger.work_gate'").fetchone()
        value = io.strict_json(row[0]) if row else {"held": False, "epoch": 0}
        if type(value.get("held")) is not bool or type(value.get("epoch")) is not int:
            raise ValueError("WORK_GATE_UNAVAILABLE")
        return value
    if db is not None:
        return read(db)
    with kernel.db() as conn:
        return read(conn)


def hold(kernel, principal):
    if "approve" not in principal.scopes or principal.mode == "Tutor":
        raise ValueError("WORK_HOLD_REQUIRES_OWNER")
    with kernel.db() as db:
        db.execute("BEGIN IMMEDIATE")
        state = work_status(kernel, db)
        state = {"held": True, "epoch": state["epoch"] + 1}
        db.execute("INSERT OR REPLACE INTO settings VALUES('ledger.work_gate',?)", (json.dumps(state),))
        activity.append(db, activity.make_event(principal.identity, "ledger.work.hold", "HELD"))
    return state


def accepting(kernel, db=None):
    if work_status(kernel, db)["held"]:
        raise ValueError("WORK_HELD_USE_EXPLICIT_RESUME")


def execution_held(kernel):
    # A worker must stop if it cannot establish that admission is open.
    try:
        return work_status(kernel)['held']
    except (ValueError, OSError, sqlite3.Error):
        return True


def resume(kernel, principal):
    with kernel.db() as db:
        db.execute("BEGIN IMMEDIATE")
        # Queued work waited at its admission step during the hold (resource_control.claim) and continues from there;
        # nothing is replayed. Work that was running must have stopped first.
        if db.execute("SELECT 1 FROM jobs WHERE state='Running' LIMIT 1").fetchone():
            raise ValueError("WORK_STILL_ACTIVE_RECONCILE_FIRST")
        if db.execute("SELECT 1 FROM worker_runs WHERE state IN ('STARTING','RUNNING','CLEANUP_REQUIRED') LIMIT 1").fetchone():
            raise ValueError('PROTECTED_WORKER_RECONCILIATION_REQUIRED: inspect workers.runs and workers.stop first')
        waiting = db.execute("SELECT count(*) FROM jobs WHERE state='Queued'").fetchone()[0]
        state = work_status(kernel, db)
        state = {"held": False, "epoch": state["epoch"] + 1}
        db.execute("INSERT OR REPLACE INTO settings VALUES('ledger.work_gate',?)", (json.dumps(state),))
        activity.append(db, activity.make_event(principal.identity, "ledger.work.resume", "ACCEPTING_NEW_WORK"))
    return {**state, "jobs_replayed": 0, "jobs_continuing": waiting, "idle_rearmed": False, "remote_reenabled": False}


def job_view(kernel, principal, ident, check_artifacts=False, budget=None):
    try:
        job = record_access.read(kernel, "jobs", c.ident(ident), principal)
    except (ValueError, TypeError):
        raise ValueError("TRAIL_UNAVAILABLE") from None
    if job["owner"] != principal.identity:
        raise ValueError("TRAIL_UNAVAILABLE")
    evidence = record_access.read(kernel, "evidence", job["evidence"], principal) if job.get("evidence") else None
    if evidence and (evidence.get("job") != job["id"] or evidence.get("id") != job.get("evidence")):
        raise ValueError("TRAIL_EVIDENCE_LINK_CHANGED")
    facts = {k: activity.redact(v, 160) if isinstance(v, str) else v for k, v in describe(job, evidence).items()}
    revision = job.get("revision")
    result = {"job_id": job["id"], "tool": activity.redact(job["tool"], 160), **facts,
              "source_revision": revision if isinstance(revision, str) and re.fullmatch("[a-f0-9]{64}", revision) else None,
              "deadline_seconds": job.get("timeout"), "record_digest": io.digest([job, evidence])}
    artifacts = []
    if check_artifacts:
        rows = (evidence or {}).get("artifacts", [])
        budget = budget if budget is not None else {"files": c.MAX_ARTIFACTS, "bytes": c.MAX_ARTIFACT_BYTES}
        for artifact in rows[:budget['files']]:
            size = artifact.get("bytes")
            status = "NOT_CHECKED_BUDGET"
            if type(size) is int and 0 <= size <= budget['bytes']:
                budget['bytes'] -= size
                try:
                    path = kernel.safe(artifact["path"])
                    # Bound actual bytes read too, even if a file grows after stat.
                    with path.open('rb') as stream:
                        raw = stream.read(size + 1)
                    status = "BYTES_MATCH" if len(raw) == size and hashlib.sha256(raw).hexdigest() == artifact["sha256"] else "CHANGED"
                except (ValueError, OSError, KeyError):
                    status = "MISSING_OR_UNAVAILABLE"
            budget['files'] -= 1
            artifacts.append({"path": activity.redact(artifact.get("path", ""), 250),
                              "sha256": artifact.get("sha256") if isinstance(artifact.get("sha256"),str) and re.fullmatch("[a-f0-9]{64}",artifact["sha256"]) else None,
                              "bytes": artifact.get("bytes"), "state": status})
        result["artifact_count"] = len(rows)
        result["artifact_checks_omitted"] = max(0, len(rows) - len(artifacts))
    return result, artifacts


def list_trails(kernel, principal, limit=20):
    with kernel.db() as db:
        ids = [r[0] for r in db.execute("SELECT id FROM ledger_trail WHERE owner=? ORDER BY rowid DESC LIMIT ?", (principal.identity, limit))]
        rows = [get(db, principal.identity, ident) for ident in ids]
        links = {row["id"]: [v[0] for v in db.execute("SELECT job FROM ledger_trail_jobs WHERE intent=? LIMIT ?", (row["id"], c.MAX_LINKS))] for row in rows}
        count = db.execute("SELECT seen,pruned,dropped FROM ledger_trail_counts WHERE owner=?", (principal.identity,)).fetchone() or (0, 0, 0)
        markers = db.execute("SELECT count(*) FROM activity_journal WHERE json_extract(payload,'$.operation')='ledger.trail' AND json_extract(payload,'$.state')='GAP' AND json_extract(payload,'$.correlation_id')=?", (hashlib.sha256(principal.identity.encode()).hexdigest(),)).fetchone()[0]
    views = []
    for row in rows:
        jobs = []
        for ident in links[row["id"]]:
            try:
                jobs.append(job_view(kernel, principal, ident)[0])
            except (ValueError, KeyError, OSError):
                pass
        views.append(c.summary(presented(row), jobs))
    return {"schema": c.VERSION, "intents": views, "retention": c.MAX_INTENTS,
            "seen": count[0], "pruned": count[1], "dropped": count[2],
            "recording_gaps_this_process": _GAPS.get((str(kernel.root), principal.identity), 0),
            "retained_gap_markers": markers,
            "scope": "THIS_OWNER_ONLY", "read_polling_recorded": False,
            "journal_gap": activity.status(kernel.root)["state"] == "INCOMPLETE"}


def inspect(kernel, principal, ident):
    with kernel.db() as db:
        row = get(db, principal.identity, ident)
        links = [r[0] for r in db.execute("SELECT job FROM ledger_trail_jobs WHERE intent=? LIMIT ?", (ident, c.MAX_LINKS))]
    jobs, artifacts = [], []
    budget = {"files": c.MAX_ARTIFACTS, "bytes": c.MAX_ARTIFACT_BYTES}
    for job in links:
        value, files = job_view(kernel, principal, job, True, budget)
        jobs.append(value)
        artifacts.extend(files)
    # Scope/grant changes are checked again before publication.
    with kernel.db() as db:
        if get(db, principal.identity, ident) != row:
            raise ValueError("TRAIL_CHANGED_REFRESH")
    for value in jobs:
        if job_view(kernel, principal, value["job_id"])[0]["record_digest"] != value["record_digest"]:
            raise ValueError("TRAIL_WORK_CHANGED_REFRESH")
    row = presented(row)
    return {"schema": c.VERSION, "intent": row, "jobs": jobs, "artifacts": artifacts,
            "observed_at": time.time(),
            "stages": c.stages(row, jobs, artifacts), "physical_qualification": False,
            "contents": "METADATA_ONLY_NO_ARGUMENTS_SOURCE_OR_OUTPUT_TEXT"}


def resources(kernel, principal):
    from . import brain_runtime, study_service,resource_control
    with _CPU_LOCK:
        cpu = _CPU.setdefault(str(kernel.root), HostCpuSampler()).snapshot()
    host = brain_runtime.host(profile=False)      # memory alone: opening the Work trail starts no process
    with kernel.db() as db:
        study = study_service.settings(db, principal.identity)
        jobs = [json.loads(r[0]) for r in db.execute("SELECT payload FROM jobs WHERE owner=? AND state IN ('Running','Queued') LIMIT 4", (principal.identity,))]
    return {"schema": "arc.work-resources/1", "cpu": cpu,
            "memory": {"state": "MEASURED" if host["available_ram_bytes"] is not None else "NOT_INSTRUMENTED",
                       "available_bytes": host["available_ram_bytes"], "total_bytes": host["total_ram_bytes"],
                       "scope": "Current host availability; Linux container ceiling respected when present"},
            "priority": operation_priority.policy(kernel.root),
            "gate": work_status(kernel), "study_limits_for_new_sessions": study["limits"],
            "study_idle_enabled": study["idle_enabled"],
            "active_job_limits": [{"job_id": j["id"], "timeout_seconds": j.get("timeout")} for j in jobs],
            "global_cpu_memory_cap": "NOT_CONFIGURED; tool-specific limits remain authoritative",
            "per_job_cpu_rss": "OWNED_TREE_RSS_IN_TRAFFIC_COMMITMENTS; CPU_TIME_NOT_INSTRUMENTED",
            "controls": {"priority": "ledger.settings.set", "study": "study.configure", "brain": "Existing Brain qualification/activation options"},
            "traffic":resource_control.snapshot(kernel,principal,host),
            "physical_qualification": False}


def dispatch(kernel, op, args, principal):
    if op == "ledger.trail.list":
        return list_trails(kernel, principal, **args)
    if op == "ledger.trail.inspect":
        return inspect(kernel, principal, args["id"])
    if op == "ledger.trail.job":
        return {"schema": c.VERSION, "job": job_view(kernel, principal, args["id"], True),
                "notice": "Historical work may have no retained intent; no history is rewritten."}
    if op == "ledger.resources":
        return resources(kernel, principal)
    if op == "ledger.resources.observation":
        from .resource_control import observation
        return observation(kernel)
    if op == "ledger.work.status":
        return work_status(kernel)
    if op == "ledger.work.resume":
        return resume(kernel, principal)
    raise ValueError("Unknown work trail operation")

